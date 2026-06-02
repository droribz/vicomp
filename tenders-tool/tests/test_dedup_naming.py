from datetime import date

from infra_tenders.adapters import get_adapter
from infra_tenders.core import naming
from infra_tenders.core.dedup import merge_duplicates
from infra_tenders.core.models import Tender, TenderFile


def _t(source, number=None, title="ביצוע סלילת כביש", files=0, deadline=date(2026, 12, 30)):
    return Tender(
        source=source, publisher="נתיבי ישראל", tender_number=number,
        title=title, submission_deadline=deadline,
        source_url=f"https://{source}/x",
        files=[TenderFile(url=f"https://{source}/f{i}.pdf") for i in range(files)],
    )


def test_dedup_merges_same_number():
    a = _t("iroads", number="12/2025", files=5)
    b = _t("jobiz", number="12/2025", files=1)
    merged = merge_duplicates([a, b])
    assert len(merged) == 1
    # המקור הישיר (iroads) מנצח על האגרגטור (jobiz).
    assert merged[0].source == "iroads"
    assert set(merged[0].sources) == {"iroads", "jobiz"}


def test_dedup_fallback_key_without_number():
    a = _t("iroads", number=None, title="עבודות ניקוז", files=2)
    b = _t("iroads", number=None, title="עבודות ניקוז", files=2)
    assert len(merge_duplicates([a, b])) == 1


def test_dedup_keeps_distinct():
    a = _t("iroads", number="12/2025")
    b = _t("iroads", number="99/2025")
    assert len(merge_duplicates([a, b])) == 2


def test_sanitize_removes_illegal_chars():
    assert "/" not in naming.sanitize('כביש 6 / מקטע א:ב')
    assert naming.sanitize("") == "ללא-שם"


def test_tender_dirname_format():
    name = naming.tender_dirname(deadline_iso="2026-12-30", number="12/2025",
                                 title="ביצוע סלילת כביש 6")
    assert name.startswith("2026-12-30__")
    assert "ללא-מספר" not in name


def test_registry_has_iroads():
    assert get_adapter("iroads") is not None
    assert get_adapter("nonexistent") is None
