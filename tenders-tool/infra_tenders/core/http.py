"""לקוח HTTP להורדות ישירות + בדיקת robots.txt + השהיות מנומסות."""
from __future__ import annotations

import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

DEFAULT_DELAY = 1.5  # שניות בין בקשות לאותו מקור (התנהגות מנומסת)


class PoliteClient:
    """עוטף httpx עם השהיה, User-Agent קבוע, וכיבוד robots.txt."""

    def __init__(self, delay: float = DEFAULT_DELAY, timeout: float = 60.0):
        self.delay = delay
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request = 0.0

    # --- robots.txt ---------------------------------------------------------
    def allowed(self, url: str) -> bool:
        """האם robots.txt מתיר ל-User-Agent שלנו לגשת ל-URL."""
        try:
            parsed = urlparse(url)
            root = f"{parsed.scheme}://{parsed.netloc}"
            rp = self._robots.get(root)
            if rp is None:
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(urljoin(root, "/robots.txt"))
                try:
                    rp.read()
                except Exception:
                    # אם robots.txt לא נגיש — מניחים מותר, אך מנומסים.
                    rp = None
                self._robots[root] = rp  # type: ignore[assignment]
            if rp is None:
                return True
            return rp.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    # --- בקשות --------------------------------------------------------------
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.monotonic()

    def get(self, url: str, **kwargs) -> httpx.Response:
        self._throttle()
        return self._client.get(url, **kwargs)

    def download(self, url: str, dest: Path) -> int:
        """מוריד קובץ ל-dest. מחזיר מספר בייטים. זורק חריגה בכישלון."""
        self._throttle()
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        # timeout נדיב לקבצים ענקיים (תוכניות/שרטוטים): עד 5 דקות בין מקטעים.
        timeout = httpx.Timeout(connect=30.0, read=300.0, write=300.0, pool=30.0)
        tmp = dest.with_suffix(dest.suffix + ".part")  # קובץ זמני עד סיום מלא
        try:
            with self._client.stream("GET", url, timeout=timeout) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        fh.write(chunk)
                        size += len(chunk)
            tmp.replace(dest)  # שינוי שם אטומי — הקובץ הסופי קיים רק אם הושלם
        finally:
            if tmp.exists():
                tmp.unlink()  # מנקה שארית במקרה כישלון
        return size

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
