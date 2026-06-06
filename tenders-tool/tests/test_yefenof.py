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


def test_number_requires_digit():
    # עמודת "מספר" שמכילה טקסט בלי ספרה (קול קורא) -> אין מספר, כדי שלא
    # יכווץ מכרזים שונים לאותו מפתח זיהוי.
    html = """<ul><li class="tenders_item">
        <div class="tenders_info_block num"><div class="jobs_mob_label">מספר</div>
        <div>קול קורא הצטרפות למאגר</div></div>
        <a href="/Tender?tenderID=9"><h4 class="tender_list_name">מאגר יועצים</h4>
        <div class="tendet_status"><div>פתוח</div></div></a></li></ul>"""
    rows = parse_yefenof_list(html, base_url="https://www.yefenof.co.il")
    assert rows[0]["number"] is None


def test_consultant_roster_excluded():
    from infra_tenders.core.filtering import Keywords, classify
    kw = Keywords.load(FIXTURES.parent.parent / "config" / "keywords.yaml")
    # מאגרי יועצים/מתכננים/מפקחים — מוחרגים למרות אזכור תחום תשתית.
    assert classify("קול קורא הצטרפות למאגר יועצי חשמל ותאורה", kw).include is False
    assert classify("קול קורא הצטרפות למאגר מתכנני הידרולוגיה וניקוז", kw).include is False
    assert classify("קול קורא לסוקרי גשרים ומבני דרך", kw).include is False
    # אבל "קול קורא" עם ביצוע/הקמה כן נכלל (Design-Build):
    assert classify("קול קורא לתכנון והקמת גשר", kw).include is True


def test_registered():
    assert get_adapter("yefenof") is not None
