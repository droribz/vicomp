"""ניקוי וקיצור שמות לתיקיות/קבצים — שמירה על עברית קריאה."""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

# תווים אסורים בשמות קבצים ב-Windows + תווי בקרה
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTISPACE = re.compile(r"\s+")

MAX_TITLE_LEN = 60   # קיצור כותרות ארוכות בשם התיקייה


def sanitize(name: str, *, max_len: int | None = None) -> str:
    """מנקה מחרוזת לשימוש כשם תיקייה/קובץ. שומר עברית, אותיות, ספרות."""
    if not name:
        return "ללא-שם"
    name = _ILLEGAL.sub(" ", name)
    name = name.replace("‏", "").replace("‎", "")  # סימוני כיווניות
    name = _MULTISPACE.sub(" ", name).strip(" .")
    if max_len and len(name) > max_len:
        name = name[:max_len].rstrip(" .") + "…"
    return name or "ללא-שם"


def tender_dirname(*, deadline_iso: str, number: str | None, title: str) -> str:
    """שם תיקיית מכרז: <YYYY-MM-DD>__<מספר>__<כותרת מקוצרת>."""
    parts = [
        deadline_iso or "ללא-מועד",
        sanitize(number) if number else "ללא-מספר",
        sanitize(title, max_len=MAX_TITLE_LEN),
    ]
    return "__".join(parts)


def filename_from_url(url: str, label: str | None = None) -> str:
    """גוזר שם קובץ מ-URL. אם יש label משמעותי — משלב אותו לקריאוּת."""
    path = urlparse(url).path
    base = unquote(path.rstrip("/").split("/")[-1]) or "file"
    if "." not in base:
        base += ".pdf"  # ברירת מחדל סבירה למסמכי מכרז
    stem, _, ext = base.rpartition(".")
    if label:
        return sanitize(f"{label}__{stem}", max_len=MAX_TITLE_LEN) + f".{ext}"
    return sanitize(base)
