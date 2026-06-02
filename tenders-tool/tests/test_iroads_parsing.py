from conftest import FIXTURES

from infra_tenders.adapters.iroads import parse_detail_html, parse_list_html


def test_parse_list_extracts_rows():
    html = (FIXTURES / "iroads_list.html").read_text(encoding="utf-8")
    items = parse_list_html(html, base_url="https://www.iroads.co.il/מכרזים/מכרזים/")
    # 5 שורות בגוף הטבלה (ה-thead לא נספר).
    assert len(items) == 5


def test_parse_list_extracts_number_and_link():
    html = (FIXTURES / "iroads_list.html").read_text(encoding="utf-8")
    items = parse_list_html(html, base_url="https://www.iroads.co.il/x/")
    first = items[0]
    assert first["number"] == "12/2025"
    assert first["detail_url"].endswith("/tenders/12-2025")
    assert "סלילה" in first["title"]


def test_parse_list_detects_closed():
    html = (FIXTURES / "iroads_list.html").read_text(encoding="utf-8")
    items = parse_list_html(html, base_url="https://x/")
    closed = [i for i in items if i["closed"]]
    assert any("ניקוז" in i["title"] for i in closed)


def test_parse_list_deadline_text_parseable():
    from infra_tenders.core.dates import parse_hebrew_date
    html = (FIXTURES / "iroads_list.html").read_text(encoding="utf-8")
    items = parse_list_html(html, base_url="https://x/")
    deadlines = [parse_hebrew_date(i["deadline_text"]) for i in items]
    # לפחות רוב השורות עם מועד שניתן לפענח.
    assert sum(d is not None for d in deadlines) >= 4


def test_parse_detail_collects_only_documents():
    html = (FIXTURES / "iroads_detail.html").read_text(encoding="utf-8")
    files = parse_detail_html(html, base_url="https://www.iroads.co.il/tenders/12-2025")
    urls = [f.url for f in files]
    # 5 מסמכים (pdf/xlsx/docx/zip), בלי "צור קשר" ו"חזרה למעלה".
    assert len(files) == 5
    assert all(any(u.lower().endswith(ext) for ext in
                   (".pdf", ".xlsx", ".docx", ".zip")) for u in urls)
    assert any("חוברת" in (f.label or "") for f in files)
