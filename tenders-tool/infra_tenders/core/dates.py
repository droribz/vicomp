"""פענוח תאריכים ישראליים ועבודה באזור זמן Asia/Jerusalem.

תומך בפורמטים נפוצים: DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY, חודשים בעברית,
עם או בלי שעה. אם לא ניתן לפענח — מחזיר None (הקורא יסמן match_confidence=low).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

JERUSALEM = ZoneInfo("Asia/Jerusalem")

# שמות חודשים בעברית -> מספר חודש
_HE_MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "מרס": 3, "אפריל": 4,
    "מאי": 5, "יוני": 6, "יולי": 7, "אוגוסט": 8, "ספטמבר": 9,
    "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}

# DD/MM/YYYY או DD.MM.YYYY או DD-MM-YYYY (שנה 2 או 4 ספרות)
_NUMERIC_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b")

# "12 בינואר 2025" / "12 ינואר 2025" / "12 בינואר, 2025"
_HE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+ב?(" + "|".join(_HE_MONTHS) + r")[,\s]+(\d{4})\b"
)


def today_il() -> date:
    """התאריך של 'היום' באזור זמן ירושלים."""
    return datetime.now(JERUSALEM).date()


def parse_hebrew_date(text: str | None) -> date | None:
    """מפענח תאריך מתוך טקסט חופשי. מחזיר None אם נכשל."""
    if not text:
        return None
    text = text.strip()

    # פורמט עברי טקסטואלי
    m = _HE_TEXT_RE.search(text)
    if m:
        day, month_name, year = int(m.group(1)), m.group(2), int(m.group(3))
        month = _HE_MONTHS[month_name]
        return _safe_date(year, month, day)

    # פורמט מספרי DD/MM/YYYY
    m = _NUMERIC_RE.search(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:                       # שנה דו-ספרתית
            year += 2000
        # היוריסטיקה: אם היום > 12 ברור שזה DD/MM. אם החודש > 12 — הפוך.
        if month > 12 and day <= 12:
            day, month = month, day
        return _safe_date(year, month, day)

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def is_expired(deadline: date | None, *, run_day: date | None = None) -> bool:
    """האם מועד ההגשה כבר עבר. מכרז ללא תאריך מוכר — לא נחשב פג (נשמר לבדיקה)."""
    if deadline is None:
        return False
    run_day = run_day or today_il()
    return deadline < run_day
