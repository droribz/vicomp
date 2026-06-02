"""ממשק אחיד לכל המתאמים + ניהול דפדפן Playwright משותף.

כל מתאם מחזיר רשימת Tender (מכרזים פתוחים) מתוך מקור אחד.
הליבה (scan.py) דואגת לפילטור תשתיות, איחוד כפילויות, תיוק והורדה —
המתאם אחראי רק על *גילוי* המכרזים והקבצים באתר הספציפי.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass

from ..core.http import USER_AGENT, PoliteClient
from ..core.models import Tender

log = logging.getLogger(__name__)


class AdapterBlocked(Exception):
    """מורם כשמקור חוסם אוטומציה / CAPTCHA — גורם לדילוג נקי (לא נפילה)."""


class LoginRequired(Exception):
    """מורם כשמקור דורש התחברות ואין אישורי גישה ב-.env."""


@dataclass
class SourceConfig:
    name: str
    publisher: str
    urls: list[str]
    requires_login: bool = False


class BaseAdapter:
    """בסיס לכל מתאם. יורשים מממשים את fetch_open_tenders()."""

    #: מזהה — חייב להתאים ל-name ב-sources.yaml ול-mapping ב-adapters/__init__.py
    name: str = "base"
    publisher: str = ""

    def __init__(self, config: SourceConfig, *, credentials: dict | None = None):
        self.config = config
        self.credentials = credentials or {}

    def fetch_open_tenders(self, page, client: PoliteClient) -> list[Tender]:
        """מחזיר את כל המכרזים הפתוחים מהמקור.

        Args:
            page: עמוד Playwright (לאתרים כבדי-JS / התחברות). יכול להיות None
                  אם המתאם משתמש רק ב-httpx.
            client: PoliteClient להורדות/בקשות ישירות.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
#  ניהול דפדפן Playwright משותף — נפתח פעם אחת לכל הסריקה.
# ---------------------------------------------------------------------------
@contextmanager
def browser_session(*, headless: bool = True):
    """מנהל הקשר שמספק עמוד Playwright. יוצר דפדפן אחד וסוגר בסוף.

    אם Playwright לא מותקן/לא הוקמו דפדפנים — מרים שגיאה ברורה.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright לא מותקן. הרץ: pip install -r requirements.txt && "
            "python -m playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="he-IL",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()
