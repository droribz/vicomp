"""מתאם נתיבי ישראל (iroads).

האתר בנוי על Umbraco ומציג את רשימת המכרזים דרך endpoint שמחזיר קטע HTML:
    /umbraco/Surface/TendersLobbySurface/FilterCameras?tabId=1866
        &parentID=all-tenders&itemsPerPage=N
המתאם פונה לכתובת זו (עם itemsPerPage גבוה כדי לקבל הכל בבקשה אחת), מפענח
את השורות, מסנן מכרזים סגורים/שפג מועדם, ולכל מכרז פתוח נכנס לעמוד המכרז
ואוסף את קישורי הקבצים.

מבנה שורת מכרז (li.tender-item):
    a.link[href]               → עמוד המכרז
    h3.subTitle                → קטגוריה (פיתוח / רכבתיים / ...)
    h3.title                   → כותרת מלאה
    div.info > .topText/.bottomText  → "מספר מכרז" / "סטאטוס" / "תאריך אחרון..."

פונקציית הפענוח parse_tender_list נבדקת ב-tests על קטע HTML אמיתי שמור.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core.dates import is_expired, parse_hebrew_date
from ..core.models import Tender
from .generic import GenericAdapter, extract_files

log = logging.getLogger(__name__)

BASE = "https://www.iroads.co.il"


class IroadsAdapter(GenericAdapter):
    name = "iroads"
    publisher = "נתיבי ישראל"

    # endpoint רשימת המכרזים. itemsPerPage גבוה = כל המכרזים בבקשה אחת.
    LIST_ENDPOINT = (
        BASE + "/umbraco/Surface/TendersLobbySurface/FilterCameras"
        "?tabId=1866&parentID=all-tenders&itemsPerPage=2000")

    def fetch_open_tenders(self, page, client) -> list[Tender]:
        if page is None:
            raise RuntimeError("מתאם iroads דורש דפדפן Playwright")

        log.info("[iroads] טוען רשימת מכרזים")
        html = self._render(page, self.LIST_ENDPOINT)
        rows = parse_tender_list(html, base_url=BASE)
        log.info("[iroads] %d מכרזים ברשימה (כולל סגורים)", len(rows))

        # שלב 1: סינון לפתוחים שלא פג מועדם (לפני כניסה לעמודי הפרטים).
        open_rows = []
        for r in rows:
            if r["closed"]:
                continue
            deadline = parse_hebrew_date(r["deadline_text"])
            if is_expired(deadline):
                continue
            r["deadline"] = deadline
            open_rows.append(r)
        log.info("[iroads] %d מכרזים פתוחים שלא פגו — אוסף קבצים", len(open_rows))

        # שלב 2: לכל מכרז פתוח — כניסה לעמוד המכרז ואיסוף קבצים.
        if not self.collect_files:
            log.info("[iroads] תצוגה מהירה (dry-run) — מדלג על איסוף קבצים")

        tenders = []
        for i, r in enumerate(open_rows, 1):
            files = []
            if self.collect_files and r["detail_url"]:
                try:
                    detail_html = self._render(page, r["detail_url"])
                    files = extract_files(detail_html, base_url=r["detail_url"],
                                          doc_ext=self.DOC_EXT)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[iroads] כשל בעמוד מכרז %s: %s",
                                r["detail_url"], exc)
                log.info("[iroads]   (%d/%d) %s — %d קבצים",
                         i, len(open_rows), r["number"] or "?", len(files))
            tenders.append(Tender(
                source=self.name,
                publisher=self.publisher,
                tender_number=r["number"],
                title=r["title"],
                category=r["category"],
                submission_deadline=r["deadline"],
                source_url=r["detail_url"] or self.LIST_ENDPOINT,
                files=files,
            ))
        return tenders


# ===========================================================================
#  פענוח טהור — נבדק ב-tests על קטע HTML אמיתי.
# ===========================================================================
def parse_tender_list(html: str, *, base_url: str = BASE) -> list[dict]:
    """מפענח את קטע ה-HTML של רשימת המכרזים. dict לכל מכרז.

    שדות: title, number, category, status, deadline_text, detail_url, closed.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    for li in soup.select("li.tender-item"):
        a = li.select_one("a[href]")
        detail_url = urljoin(base_url, a["href"]) if a else None

        title_el = li.select_one("h3.title")
        title = _clean(title_el.get_text()) if title_el else _clean(li.get_text())[:120]
        cat_el = li.select_one("h3.subTitle")
        category = _clean(cat_el.get_text()) if cat_el else ""

        number = status = deadline_text = None
        for info in li.select("div.info"):
            top = info.select_one(".topText")
            bottom = info.select_one(".bottomText")
            label = _clean(top.get_text()) if top else ""
            value = _clean(bottom.get_text()) if bottom else ""
            if "מספר" in label:
                number = value
            elif "סטא" in label or "סטט" in label or "status" in label.lower():
                status = value
            elif "תאריך" in label or "הגש" in label:
                deadline_text = value

        closed = bool(status) and ("סגור" in status or "closed" in status.lower())
        items.append({
            "title": title, "number": number, "category": category,
            "status": status, "deadline_text": deadline_text,
            "detail_url": detail_url, "closed": closed,
        })
    return items


def _clean(text: str) -> str:
    return " ".join((text or "").split())


# --- תאימות לאחור עבור ה-tests של ה-scraper הגנרי ---------------------------
def parse_list_html(html: str, *, base_url: str):
    from . import generic
    return generic.extract_list(html, base_url=base_url)


def parse_detail_html(html: str, *, base_url: str):
    from . import generic
    return generic.extract_files(html, base_url=base_url)
