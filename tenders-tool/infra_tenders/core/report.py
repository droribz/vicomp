"""בניית report.html — דוח סיכום נוח לצפייה (כולל בנייד)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .index import IndexRow

# מכרז שהדדליין שלו בתוך כך וכך ימים — מודגש כ"מתקרב".
APPROACHING_DAYS = 7

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def write_report(path: Path, rows: list[IndexRow], *, run_day: date,
                 summary: dict) -> None:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")

    enriched = []
    for r in sorted(rows, key=_sort_key):
        days_left = _days_left(r.submission_deadline, run_day)
        enriched.append({
            "row": r,
            "days_left": days_left,
            "approaching": days_left is not None and 0 <= days_left <= APPROACHING_DAYS,
            "is_new": r.is_new == "כן",
            "paid": r.status in ("paid", "partial"),
        })

    html = template.render(
        tenders=enriched,
        run_day=run_day.isoformat(),
        summary=summary,
        approaching_days=APPROACHING_DAYS,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _days_left(deadline_iso: str, run_day: date) -> int | None:
    try:
        return (date.fromisoformat(deadline_iso) - run_day).days
    except ValueError:
        return None


def _sort_key(r: IndexRow):
    try:
        return (0, date.fromisoformat(r.submission_deadline))
    except ValueError:
        return (1, date.max)
