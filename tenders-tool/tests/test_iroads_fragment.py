"""בדיקות למתאם iroads — על קטע ה-HTML האמיתי מה-endpoint."""
from datetime import date

from conftest import FIXTURES

from infra_tenders.adapters.iroads import parse_tender_list
from infra_tenders.core.dates import parse_hebrew_date


def _rows():
    html = (FIXTURES / "iroads_fragment.html").read_text(encoding="utf-8")
    return parse_tender_list(html, base_url="https://www.iroads.co.il")


def test_parses_all_three_tenders():
    assert len(_rows()) == 3


def test_fields_of_first_tender():
    r = _rows()[0]
    assert r["number"] == "65/26"
    assert r["category"] == "פיתוח"
    assert "בן גוריון" in r["title"]
    assert r["detail_url"].startswith("https://www.iroads.co.il/מכרזים/")
    assert r["closed"] is False


def test_entities_decoded_in_title():
    # &#x27; -> ' , &quot; -> " , &#x2B; -> +
    title = _rows()[0]["title"]
    assert "'" in title and '"' in title
    assert "&" not in title  # אין ישויות HTML שלא פוענחו


def test_status_open_vs_closed():
    rows = _rows()
    assert rows[0]["closed"] is False      # פתוח/open
    assert rows[2]["closed"] is True       # סגור/closed


def test_deadline_text_is_parseable():
    r = _rows()[0]
    assert parse_hebrew_date(r["deadline_text"]) == date(2026, 7, 13)


def test_railway_category_extracted():
    assert _rows()[2]["category"] == "רכבתיים"
