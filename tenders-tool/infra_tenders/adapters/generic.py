"""scraper גנרי לשימוש חוזר — לב הפענוח המשותף לכל המתאמים.

רוב אתרי המכרזים בנויים אותו דבר עקרונית: עמוד רשימה עם שורות/כרטיסים
(כל אחד = מכרז עם קישור, מספר, מועד הגשה, סטטוס), ועמוד מכרז עם קישורי קבצים.
מודול זה ממש את הלוגיקה הזו פעם אחת:

  • extract_list(html, ...)  — פענוח עמוד רשימה -> list[dict].
  • extract_files(html, ...) — פענוח עמוד מכרז -> list[TenderFile].
  • GenericAdapter           — מתאם בסיס שמרנדר עם Playwright ומשתמש בשתיהן.

הוספת מקור חדש = יצירת תת-מחלקה של GenericAdapter עם כמה תכונות בלבד
(ROW_SELECTORS / מילות סטטוס / FOLLOW_DETAIL). אין צורך לכתוב פענוח מחדש.

הפונקציות הטהורות (extract_*) נבדקות ב-tests על HTML שמור — בלי דפדפן.
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

# --- ברירות מחדל (תת-מחלקות יכולות לדרוס) ----------------------------------
DEFAULT_ROW_SELECTORS = ["table tbody tr", "tr", "li.tender", "div.tender",
                         "article", "div.card", "li", "div.row"]
DEFAULT_CLOSED_MARKERS = ["סגור", "הסתיים", "נסגר", "בוטל", "לא פעיל"]
DEFAULT_OPEN_MARKERS = ["פתוח", "פעיל"]

# סיומות קבצים שנחשבות "מסמך מכרז" להורדה.
DEFAULT_DOC_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar",
                   ".dwg", ".dwf", ".ppt", ".pptx", ".rtf")

# זיהוי מספר מכרז בטקסט.
_NUM_RE = re.compile(r"מכרז\s*(?:מס['׳]?\.?\s*)?([0-9][0-9/\-.]{1,20})")
_NUM_FALLBACK_RE = re.compile(r"\b(\d{1,4}[/\-]\d{2,4}(?:[/\-]\d{1,4})?)\b")
_DEADLINE_RE = re.compile(
    r"(?:מועד\s*הגשה|להגשה|הגשה\s*עד|עד\s*ל?תאריך)[:\s]*([^\n,;|]{0,40})")


# ===========================================================================
#  פונקציות פענוח טהורות
# ===========================================================================
def extract_list(html: str, *, base_url: str,
                 row_selectors: list[str] | None = None,
                 closed_markers: list[str] | None = None,
                 open_markers: list[str] | None = None) -> list[dict]:
    """מפענח עמוד רשימת מכרזים. מחזיר dict לכל פריט שזוהה.

    שדות: title, number, deadline_text, publication_text, detail_url,
          list_url, closed (bool).
    גנרי: עובר על הסלקטורים לפי סדר, בוחר את הראשון שמחזיר פריטים.
    """
    row_selectors = row_selectors or DEFAULT_ROW_SELECTORS
    closed_markers = closed_markers or DEFAULT_CLOSED_MARKERS
    open_markers = open_markers or DEFAULT_OPEN_MARKERS

    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for selector in row_selectors:
        found = soup.select(selector)
        if found:
            rows = found
            log.debug("משתמש בסלקטור '%s' (%d פריטים)", selector, len(found))
            break

    items: list[dict] = []
    seen_urls: set[str] = set()
    for row in rows:
        text = " ".join(row.get_text(" ", strip=True).split())
        if not text:
            continue

        link = _best_link(row, base_url)
        deadline_text = _extract_deadline(text)
        # פריט בלי קישור וגם בלי תאריך — כנראה כותרת/header, מדלגים.
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
            "closed": _is_closed(text, closed_markers, open_markers),
        })

    return items


def extract_files(html: str, *, base_url: str,
                  doc_ext: tuple[str, ...] = DEFAULT_DOC_EXT) -> list[TenderFile]:
    """מפענח עמוד מכרז ומחזיר את כל קישורי הקבצים להורדה."""
    soup = BeautifulSoup(html, "html.parser")
    files: list[TenderFile] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url, href)
        low = abs_url.lower().split("?")[0]
        is_doc = low.endswith(doc_ext) or "download" in href.lower()
        if not is_doc or abs_url in seen:
            continue
        seen.add(abs_url)
        label = " ".join(a.get_text(" ", strip=True).split()) or None
        files.append(TenderFile(url=abs_url, label=label))
    return files


# --- עוזרי פענוח ------------------------------------------------------------
def _best_link(row, base_url: str) -> str | None:
    for a in row.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        return urljoin(base_url, href)
    return None


def _extract_title(row, text: str) -> str:
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
    m = _DEADLINE_RE.search(text)
    if m:
        return m.group(1)
    return text  # נופלים לטקסט המלא — parse_hebrew_date יחפש תאריך בתוכו


def _is_closed(text: str, closed_markers: list[str],
               open_markers: list[str]) -> bool:
    has_closed = any(m in text for m in closed_markers)
    has_open = any(m in text for m in open_markers)
    return has_closed and not has_open


# ===========================================================================
#  מתאם בסיס גנרי — רינדור + אורקסטרציה. תת-מחלקות מגדירות רק תכונות.
# ===========================================================================
class GenericAdapter(BaseAdapter):
    """בסיס למתאמים מבוססי טבלה/כרטיסים. דורס תכונות לפי הצורך באתר ספציפי."""

    # סלקטורים ומילות סטטוס — None = ברירות המחדל של המודול.
    ROW_SELECTORS: list[str] | None = None
    CLOSED_MARKERS: list[str] | None = None
    OPEN_MARKERS: list[str] | None = None
    DOC_EXT: tuple[str, ...] = DEFAULT_DOC_EXT
    #: האם להיכנס לעמוד הפרטים של כל מכרז כדי לאסוף קבצים (אחרת — קבצים מהרשימה).
    FOLLOW_DETAIL: bool = True
    WAIT_UNTIL: str = "networkidle"

    def fetch_open_tenders(self, page, client) -> list[Tender]:
        if page is None:
            raise RuntimeError(f"מתאם {self.name} דורש דפדפן Playwright")

        tenders: list[Tender] = []
        for url in self.config.urls:
            log.info("[%s] טוען עמוד רשימה: %s", self.name, url)
            try:
                html = self._render(page, url)
            except AdapterBlocked:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("[%s] כשל בטעינת %s: %s", self.name, url, exc)
                continue

            candidates = extract_list(
                html, base_url=url, row_selectors=self.ROW_SELECTORS,
                closed_markers=self.CLOSED_MARKERS,
                open_markers=self.OPEN_MARKERS)
            log.info("[%s] נמצאו %d פריטים בעמוד", self.name, len(candidates))

            for c in candidates:
                if c.get("closed"):
                    continue
                deadline = parse_hebrew_date(c.get("deadline_text"))
                if is_expired(deadline):
                    continue
                t = self._build_tender(page, c, deadline)
                if t:
                    tenders.append(t)

        return tenders

    # --- רינדור עמוד עם Playwright + זיהוי חסימה ----------------------------
    def _render(self, page, url: str) -> str:
        page.goto(url, wait_until=self.WAIT_UNTIL, timeout=60000)
        content = page.content()
        low = content.lower()
        if "captcha" in low or "אני לא רובוט" in content or "are you human" in low:
            raise AdapterBlocked(f"זוהה CAPTCHA/חסימת בוט ב-{url}")
        return content

    # --- בניית Tender מלא ---------------------------------------------------
    def _build_tender(self, page, c: dict, deadline) -> Tender | None:
        detail_url = c.get("detail_url")
        files: list[TenderFile] = []
        if self.FOLLOW_DETAIL and detail_url:
            try:
                detail_html = self._render(page, detail_url)
                files = extract_files(detail_html, base_url=detail_url,
                                      doc_ext=self.DOC_EXT)
            except AdapterBlocked:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("[%s] כשל בטעינת עמוד מכרז %s: %s",
                            self.name, detail_url, exc)

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
