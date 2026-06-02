"""בניית _index.csv — אינדקס מרכזי של מכרזים פתוחים בלבד."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class IndexRow:
    publisher: str
    title: str
    tender_number: str
    submission_deadline: str
    publication_date: str
    source_url: str
    sources: str            # מופרד ב-";"
    local_path: str
    status: str             # free / paid / partial
    match_confidence: str   # high / low
    is_new: str             # כן / לא
    last_version: str
    download_date: str


_HEADERS_HE = [
    ("publisher", "מפרסם"),
    ("title", "כותרת"),
    ("tender_number", "מספר מכרז"),
    ("submission_deadline", "מועד הגשה"),
    ("publication_date", "תאריך פרסום"),
    ("source_url", "קישור מקור"),
    ("sources", "מקורות"),
    ("local_path", "נתיב מקומי"),
    ("status", "סטטוס"),
    ("match_confidence", "ביטחון התאמה"),
    ("is_new", "חדש"),
    ("last_version", "גרסה אחרונה"),
    ("download_date", "תאריך הורדה"),
]


def write_index(path: Path, rows: list[IndexRow]) -> None:
    """כותב את האינדקס. ממוין לפי מועד הגשה (הקרוב ביותר ראשון)."""
    rows_sorted = sorted(rows, key=_deadline_sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:  # BOM ל-Excel
        writer = csv.writer(fh)
        writer.writerow([he for _, he in _HEADERS_HE])
        for r in rows_sorted:
            writer.writerow([getattr(r, key) for key, _ in _HEADERS_HE])


def _deadline_sort_key(r: IndexRow):
    try:
        return (0, date.fromisoformat(r.submission_deadline))
    except ValueError:
        return (1, date.max)  # מכרזים ללא מועד — בסוף
