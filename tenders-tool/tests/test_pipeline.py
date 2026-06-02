"""בדיקת אינטגרציה של הליבה: תיוק -> גרסאות -> ארכוב -> אינדקס -> דוח.

משתמש ב-StubClient שכותב קבצים מקומית במקום הורדת רשת, כדי לבדוק את כל
מסלול התיוק בלי תלות באתרים חיצוניים.
"""
from datetime import date
from pathlib import Path

from infra_tenders.core import index as index_mod
from infra_tenders.core import report
from infra_tenders.core.archive import archive_expired
from infra_tenders.core.models import (MatchConfidence, Tender, TenderFile,
                                        TenderStatus)
from infra_tenders.core.storage import TenderStore


class StubClient:
    """מחקה PoliteClient: כותב תוכן דמה במקום להוריד מהרשת."""

    def allowed(self, url):  # robots — תמיד מותר בבדיקה
        return True

    def download(self, url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = f"DUMMY CONTENT FOR {url}".encode("utf-8")
        dest.write_bytes(data)
        return len(data)


def _tender(files):
    return Tender(
        source="iroads", publisher="נתיבי ישראל", tender_number="12/2025",
        title="ביצוע עבודות סלילה והרחבת כביש 6",
        submission_deadline=date(2026, 12, 30),
        source_url="https://www.iroads.co.il/tenders/12-2025",
        files=[TenderFile(url=u, label=l) for u, l in files],
        match_confidence=MatchConfidence.HIGH,
    )


def test_full_pipeline(tmp_path):
    root = tmp_path / "tenders"
    store = TenderStore(root, StubClient())

    t = _tender([
        ("https://x/booklet.pdf", "חוברת המכרז"),
        ("https://x/specs.pdf", "מפרט טכני"),
    ])

    # --- הורדה ראשונה: גרסה v1 + meta.json + קבצים ---
    out1 = store.store(t)
    assert out1.status == "new"
    assert out1.version.startswith("v1_")
    v1_dir = out1.dir / out1.version
    assert len(list(v1_dir.glob("*"))) == 2
    assert (out1.dir / "meta.json").exists()

    # --- הרצה חוזרת ללא שינוי: אידמפוטנטי, מדלג ---
    out2 = store.store(t)
    assert out2.status == "unchanged"

    # --- עדכון (נספח חדש): גרסה v2, לא דורס את v1 ---
    t2 = _tender([
        ("https://x/booklet.pdf", "חוברת המכרז"),
        ("https://x/specs.pdf", "מפרט טכני"),
        ("https://x/appendix.pdf", "נספח 1"),
    ])
    out3 = store.store(t2)
    assert out3.status == "updated"
    assert out3.version.startswith("v2_")
    assert (out1.dir / out1.version).exists()  # v1 עדיין קיים
    assert (out3.dir / out3.version).exists()

    # --- אינדקס + דוח נכתבים ---
    row = index_mod.IndexRow(
        publisher=t.publisher, title=t.title, tender_number="12/2025",
        submission_deadline="2026-12-30", publication_date="",
        source_url=t.source_url, sources="iroads", local_path=str(out3.dir),
        status="free", match_confidence="high", is_new="כן",
        last_version=out3.version, download_date="2026-06-02",
    )
    index_mod.write_index(root / "_index.csv", [row])
    report.write_report(root / "report.html", [row], run_day=date(2026, 6, 2),
                        summary={"total": 1, "new": 1, "paid": 0, "low": 0})
    assert (root / "_index.csv").exists()
    assert (root / "report.html").exists()
    assert "כביש 6" in (root / "report.html").read_text(encoding="utf-8")


def test_archive_expired(tmp_path):
    root = tmp_path / "tenders"
    store = TenderStore(root, StubClient())

    expired = _tender([("https://x/a.pdf", "חוברת")])
    expired.submission_deadline = date(2020, 1, 1)
    out = store.store(expired)
    assert out.dir.exists()

    moved = archive_expired(root, run_day=date(2026, 6, 2))
    assert moved == 1
    assert not out.dir.exists()                          # הוסר מהפעיל
    archived = root / "_archive" / "נתיבי ישראל"
    assert any(archived.iterdir())                       # קיים בארכיב
