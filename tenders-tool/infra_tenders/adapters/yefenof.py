"""מתאם יפה נוף (yefenof) — חיפה.

אתר Webflow עם רשימת מכרזים מרונדרת בצד השרת (אין iframe/API).
מבנה שורה (li.tenders_item):
    div.tenders_info_block.num     → מספר מכרז (למשל 02-2026)
    a.tenders_info_block[href]     → /Tender?tenderID=N  (עמוד המכרז)
    h4.tender_list_name            → כותרת
    div.tendet_status              → "פתוח" / "סגור"

הרשימה לא כוללת מועד הגשה — אותו (וגם הקבצים) שולפים מעמוד המכרז.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core.dates import is_expired, parse_hebrew_date
from ..core.models import Tender
from .generic import GenericAdapter, extract_files

log = logging.getLogger(__name__)

BASE = "https://www.yefenof.co.il"

# חיפוש מועד הגשה בעמוד המכרז (best-effort).
_DEADLINE_RE = re.compile(
    r"(?:מועד\s*(?:אחרון)?\s*(?:להגשת?\s*(?:הצעות)?|הגשה)|הגשה\s*עד)"
    r"[^0-9]{0,30}(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})")


class YefenofAdapter(GenericAdapter):
    name = "yefenof"
    publisher = "יפה נוף"
    LIST_URL = BASE + "/Tenders"

    def list_open_tenders(self, page, client) -> list[Tender]:
        if page is None:
            raise RuntimeError("מתאם yefenof דורש דפדפן Playwright")

        log.info("[yefenof] טוען רשימת מכרזים")
        html = self._render(page, self.LIST_URL)
        rows = parse_yefenof_list(html, base_url=BASE)
        open_rows = [r for r in rows if not r["closed"]]
        log.info("[yefenof] %d מכרזים ברשימה, %d פתוחים",
                 len(rows), len(open_rows))

        # הרשימה לא כוללת מועד הגשה — הסטטוס פתוח/סגור קובע; המועד נשלף בשלב 2.
        return [Tender(
            source=self.name, publisher=self.publisher,
            tender_number=r["number"], title=r["title"],
            submission_deadline=None,
            source_url=r["detail_url"] or self.LIST_URL, files=[])
            for r in open_rows]

    def fetch_files(self, page, client, tender):
        if not tender.source_url:
            return []
        try:
            html = self._render(page, tender.source_url)
        except Exception as exc:  # noqa: BLE001
            log.warning("[yefenof] כשל בעמוד מכרז %s: %s",
                        tender.source_url, exc)
            return []
        # מועד ההגשה מופיע רק בעמוד המכרז — מעדכנים אותו על ה-Tender.
        deadline = _find_deadline(html)
        if deadline:
            tender.submission_deadline = deadline
        return extract_files(html, base_url=tender.source_url,
                             doc_ext=self.DOC_EXT)


def parse_yefenof_list(html: str, *, base_url: str = BASE) -> list[dict]:
    """מפענח את רשימת המכרזים. dict לכל מכרז: title, number, status,
    detail_url, closed."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    for li in soup.select("li.tenders_item"):
        a = li.select_one("a[href*='Tender']") or li.select_one("a[href]")
        detail_url = urljoin(base_url, a["href"]) if a and a.has_attr("href") else None

        title_el = li.select_one("h4.tender_list_name")
        title = _clean(title_el.get_text()) if title_el else _clean(li.get_text())[:120]

        status_el = li.select_one(".tendet_status")
        status = _clean(status_el.get_text()) if status_el else ""

        number = _extract_number(li)
        closed = "סגור" in status or "closed" in status.lower()
        items.append({"title": title, "number": number, "status": status,
                      "detail_url": detail_url, "closed": closed})
    return items


def _extract_number(li) -> str | None:
    num_block = li.select_one(".tenders_info_block.num") or li.select_one(".num")
    if not num_block:
        return None
    for d in num_block.find_all(["div", "span"]):
        classes = d.get("class") or []
        if "jobs_mob_label" in classes:
            continue
        txt = _clean(d.get_text())
        # מקבלים רק "מספר" אמיתי שמכיל ספרה — לא טקסט כמו "קול קורא להצטרפות
        # למאגר" שמופיע באותה עמודה ומכווץ מכרזים שונים לאותו מפתח זיהוי.
        if txt and txt != "מספר" and any(c.isdigit() for c in txt):
            return txt
    return None


def _find_deadline(html: str):
    text = " ".join(BeautifulSoup(html, "html.parser").get_text(" ").split())
    m = _DEADLINE_RE.search(text)
    return parse_hebrew_date(m.group(1)) if m else None


def _clean(text: str) -> str:
    return " ".join((text or "").split())
