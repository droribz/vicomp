"""בדיקות למתאם יפה נוף — על מבנה ה-HTML האמיתי."""
from conftest import FIXTURES

from infra_tenders.adapters import get_adapter
from infra_tenders.adapters.yefenof import _find_deadline, parse_yefenof_list


def _rows():
    html = (FIXTURES / "yefenof_list.html").read_text(encoding="utf-8")
    return parse_yefenof_list(html, base_url="https://www.yefenof.co.il")


def test_parses_all_rows():
    assert len(_rows()) == 3


def test_fields_first_row():
    r = _rows()[0]
    assert r["number"] == "02-2026"
    assert r["detail_url"] == "https://www.yefenof.co.il/Tender?tenderID=1170"
    assert "ראיית חשבון" in r["title"]
    assert r["closed"] is False


def test_number_skips_label():
    # לוודא שלא תפסנו את המילה "מספר" כמספר המכרז.
    assert all(r["number"] != "מספר" for r in _rows())


def test_open_vs_closed():
    rows = _rows()
    assert rows[0]["closed"] is False    # פתוח
    assert rows[2]["closed"] is True     # סגור


def test_find_deadline_best_effort():
    html = "<p>מועד אחרון להגשת הצעות: 15/07/2026 בשעה 12:00</p>"
    from datetime import date
    assert _find_deadline(html) == date(2026, 7, 15)
    assert _find_deadline("<p>אין כאן תאריך</p>") is None


def test_registered():
    assert get_adapter("yefenof") is not None
