"""מתאם נתיבי ישראל (iroads).

⚠️  הערה חשובה: המתאם נכתב בצורה *הגנתית* כי לא ניתן היה לבדוק את ה-DOM
    החי של האתר מסביבת הפיתוח (האתר חוסם גישה משם). הסלקטורים והאסטרטגיות
    כתובים כך שיהיה קל לכוונן אחרי הרצה ראשונה במחשב שלך:
      1. הרץ:  python scan.py --source iroads --dry-run
      2. אם לא נמצאו מכרזים — פתח את עמוד המכרזים בדפדפן, בדוק את מבנה ה-HTML
         (F12), והתאם את SELECTORS / DATE_FALLBACK בראש הקובץ.
    הלוגיקה הגנרית (טבלה / כרטיסים) אמורה לתפוס את רוב המבנים ללא שינוי.

    לוגיקת הפענוח מופרדת לפונקציות טהורות (parse_list_html / parse_detail_html)
    שנבדקות ב-tests על HTML שמור, בלי צורך בדפדפן.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core.dates import is_expired, parse_hebrew_date
from ..core.models import Tender, TenderFile
from .base import AdapterBlocked, BaseAdapter

log = logging.getLogger(__name__)

# --- כוונון (ניתן לעריכה אחרי בדיקת האתר החי) -------------------------------
SELECTORS = {
    # קונטיינרים אפשריים של פריט-מכרז בודד, לפי סדר עדיפות.
    "row_containers": ["table tbody tr", "tr", "li.tender", "div.tender",
                       "article", "div.card"],
    # אינדיקציה טקסטואלית לסטטוס סגור (אם מופיע — מדלגים).
    "closed_markers": ["סגור", "הסתיים", "נסגר", "בוטל", "לא פעיל"],
    "open_markers": ["פתוח", "פעיל"],
}

# סיומות קבצים שנחשבות "מסמך מכרז" להורדה.
DOC_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar",
           ".dwg", ".dwf", ".ppt", ".pptx", ".rtf")

# זיהוי מספר מכרז בטקסט.
_NUM_RE = re.compile(r"מכרז\s*(?:מס['׳]?\.?\s*)?([0-9][0-9/\-.]{1,20})")
_NUM_FALLBACK_RE = re.compile(r"\b(\d{1,4}[/\-]\d{2,4}(?:[/\-]\d{1,4})?)\b")


class IroadsAdapter(BaseAdapter):
    name = "iroads"
    publisher = "נתיבי ישראל"

    def fetch_open_tenders(self, page, client) -> list[Tender]:
        if page is None:
            raise RuntimeError("מתאם iroads דורש דפדפן Playwright")

        tenders: list[Tender] = []
        for url in self.config.urls:
            log.info("[iroads] טוען עמוד רשימה: %s", url)
            try:
                html = self._render(page, url)
            except AdapterBlocked:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("[iroads] כשל בטעינת %s: %s", url, exc)
                continue

            candidates = parse_list_html(html, base_url=url)
            log.info("[iroads] נמצאו %d פריטים בעמוד", len(candidates))

            for c in candidates:
                if c.get("closed"):
                    continue  # סגור במפורש
                deadline = parse_hebrew_date(c.get("deadline_text"))
                if is_expired(deadline):
                    continue  # מועד עבר
                t = self._build_tender(page, c, deadline)
                if t:
                    tenders.append(t)

        return tenders

    # --- רינדור עמוד עם Playwright ------------------------------------------
    def _render(self, page, url: str) -> str:
        page.goto(url, wait_until="networkidle", timeout=60000)
        content = page.content()
        low = content.lower()
        if "captcha" in low or "אני לא רובוט" in content or "are you human" in low:
            raise AdapterBlocked(f"זוהה CAPTCHA/חסימת בוט ב-{url}")
        return content

    # --- בניית Tender מלא (כולל קבצים מעמוד הפרטים) -------------------------
    def _build_tender(self, page, c: dict, deadline) -> Tender | None:
        detail_url = c.get("detail_url")
        files: list[TenderFile] = []
        if detail_url:
            try:
                detail_html = self._render(page, detail_url)
                files = parse_detail_html(detail_html, base_url=detail_url)
            except AdapterBlocked:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("[iroads] כשל בטעינת עמוד מכרז %s: %s",
                            detail_url, exc)

        return Tender(
            source=self.name,
            publisher=self.publisher,
            tender_number=c.get("number"),
            title=c.get("title") or "ללא כותרת",
            submission_deadline=deadline,
            publication_date=parse_hebrew_date(c.get("publication_text")),
            source_url=detail_url or c.get("list_url", ""),
            files=files,
        )


# ===========================================================================
#  פונקציות פענוח טהורות — נבדקות ב-tests על HTML שמור.
# ===========================================================================
def parse_list_html(html: str, *, base_url: str) -> list[dict]:
    """מפענח עמוד רשימת מכרזים. מחזיר רשימת dict לכל פריט שזוהה.

    שדות: title, number, deadline_text, publication_text, detail_url,
          list_url, closed (bool).
    גנרי: עובר על קונטיינרים אפשריים ובוחר את אלה שמכילים קישור + טקסט.
    """
    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for selector in SELECTORS["row_containers"]:
        found = soup.select(selector)
        if found:
            rows = found
            log.debug("[iroads] משתמש בסלקטור '%s' (%d פריטים)",
                      selector, len(found))
            break

    items: list[dict] = []
    seen_urls: set[str] = set()
    for row in rows:
        text = " ".join(row.get_text(" ", strip=True).split())
        if not text:
            continue

        link = _best_link(row, base_url)
        # פריט בלי קישור וגם בלי תאריך — כנראה כותרת/header, מדלגים.
        deadline_text = _extract_deadline(text)
        if not link and not deadline_text:
            continue
        if link and link in seen_urls:
            continue
        if link:
            seen_urls.add(link)

        items.append({
            "title": _extract_title(row, text),
            "number": _extract_number(text),
            "deadline_text": deadline_text,
            "publication_text": text,
            "detail_url": link,
            "list_url": base_url,
            "closed": _is_closed(text),
        })

    return items


def parse_detail_html(html: str, *, base_url: str) -> list[TenderFile]:
    """מפענח עמוד מכרז ומחזיר את כל קישורי הקבצים להורדה."""
    soup = BeautifulSoup(html, "html.parser")
    files: list[TenderFile] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url, href)
        low = abs_url.lower().split("?")[0]
        is_doc = low.endswith(DOC_EXT) or "download" in href.lower()
        if not is_doc or abs_url in seen:
            continue
        seen.add(abs_url)
        label = " ".join(a.get_text(" ", strip=True).split()) or None
        files.append(TenderFile(url=abs_url, label=label))
    return files


# --- עוזרי פענוח ------------------------------------------------------------
def _best_link(row, base_url: str) -> str | None:
    """בוחר את הקישור הסביר ביותר לעמוד המכרז מתוך שורה."""
    for a in row.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        return urljoin(base_url, href)
    return None


def _extract_title(row, text: str) -> str:
    # עדיפות לכותרת בתוך תגית כותרת/קישור.
    for sel in ["h1", "h2", "h3", "h4", "a"]:
        el = row.select_one(sel)
        if el:
            t = " ".join(el.get_text(" ", strip=True).split())
            if len(t) > 3:
                return t
    return text[:120]


def _extract_number(text: str) -> str | None:
    m = _NUM_RE.search(text)
    if m:
        return m.group(1).strip(" .")
    m = _NUM_FALLBACK_RE.search(text)
    return m.group(1) if m else None


def _extract_deadline(text: str) -> str | None:
    """מנסה לבודד את הקטע של מועד ההגשה. מחזיר טקסט לפענוח ב-dates.parse."""
    # מחפש ביטוי קרוב למילים "מועד הגשה"/"להגשה"/"עד".
    m = re.search(r"(?:מועד\s*הגשה|להגשה|הגשה\s*עד|עד\s*ל?תאריך)[:\s]*"
                  r"([^\n,;|]{0,40})", text)
    if m:
        return m.group(1)
    return text  # נופלים לטקסט המלא — parse_hebrew_date יחפש תאריך בתוכו


def _is_closed(text: str) -> bool:
    has_closed = any(m in text for m in SELECTORS["closed_markers"])
    has_open = any(m in text for m in SELECTORS["open_markers"])
    return has_closed and not has_open
