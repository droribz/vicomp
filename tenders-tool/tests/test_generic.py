"""בדיקות לתשתית הגנרית — מאמתות שהיא עובדת על מבנה אתר שונה מ-iroads
(כרטיסי div במקום טבלה), כדי להוכיח שימוש חוזר."""
from conftest import FIXTURES

from infra_tenders.adapters import generic
from infra_tenders.core.dates import is_expired, parse_hebrew_date
from infra_tenders.core.filtering import Keywords, classify

KW = Keywords.load(FIXTURES.parent.parent / "config" / "keywords.yaml")


def test_generic_handles_card_layout():
    html = (FIXTURES / "generic_cards.html").read_text(encoding="utf-8")
    items = generic.extract_list(html, base_url="https://www.yefenof.co.il/tenders")
    assert len(items) == 3
    first = items[0]
    assert first["number"] == "07/2026"
    assert first["detail_url"].endswith("/Tender?tenderID=1201")
    assert "ביוב" in first["title"]


def test_generic_end_to_end_filtering():
    """הצינור הגנרי: רשימה -> תאריך -> פילטור תשתיות. אמור להשאיר 1 מתוך 3."""
    html = (FIXTURES / "generic_cards.html").read_text(encoding="utf-8")
    items = generic.extract_list(html, base_url="https://x/")
    kept = []
    for c in items:
        if c["closed"]:
            continue
        dl = parse_hebrew_date(c["deadline_text"])
        if is_expired(dl, run_day=__import__("datetime").date(2026, 6, 2)):
            continue  # מסנן את 09/2026 (מועד 2020)
        if not classify(c["title"], KW).include:
            continue  # מסנן את "ניהול ופיקוח"
        kept.append(c["number"])
    assert kept == ["07/2026"]  # רק קו הביוב נשאר


def test_generic_doc_extension_override():
    html = '<a href="/f.pdf">א</a><a href="/g.txt">ב</a><a href="/h.zip">ג</a>'
    only_pdf = generic.extract_files(html, base_url="https://x/", doc_ext=(".pdf",))
    assert len(only_pdf) == 1
    assert only_pdf[0].url.endswith(".pdf")
