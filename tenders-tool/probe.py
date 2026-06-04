#!/usr/bin/env python3
"""כלי אבחון לאתרי SPA — מאתר את ה-API שמזין את רשימת המכרזים.

פותח דפדפן גלוי, מקליט את כל תגובות הרשת בזמן טעינת העמוד, ומדפיס את
כתובות ה-JSON שזוהו + דוגמה מהנתונים. כך אפשר לבנות מתאם שמושך ישירות
מה-API (יציב ומהיר) במקום לפענח HTML מרונדר ושברירי.

שימוש:
    python probe.py                          # ברירת מחדל: עמוד המכרזים של נתיבי ישראל
    python probe.py https://some.site/page   # כתובת אחרת

הפלט (כתובות API + דוגמת JSON) נשמר גם לקובץ, וגם ה-HTML המרונדר.
העתק לי את מה שמודפס בטרמינל.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

DEFAULT_URL = "https://www.iroads.co.il/מכרזים/מכרזים/"
WAIT_SECONDS = 30  # זמן המתנה לטעינת תוכן ה-JS


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    out = Path("tenders/_logs/probe")
    out.mkdir(parents=True, exist_ok=True)

    captured: list[dict] = []

    def on_response(resp):
        try:
            ct = resp.headers.get("content-type", "").lower()
            if "json" not in ct:
                return
            body = resp.text()
            data = json.loads(body)
            captured.append({
                "method": resp.request.method,
                "url": resp.url,
                "status": resp.status,
                "post": resp.request.post_data,
                "data": data,
                "body": body,
            })
        except Exception:
            pass

    print(f"פותח דפדפן וטוען: {url}")
    print(f"ממתין {WAIT_SECONDS} שניות לטעינת התוכן... (אל תסגור את הדפדפן)\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, locale="he-IL",
                                  timezone_id="Asia/Jerusalem")
        page = ctx.new_page()
        page.on("response", on_response)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
        except Exception as exc:
            print("אזהרה בטעינה:", exc)
        page.wait_for_timeout(WAIT_SECONDS * 1000)
        try:
            (out / "rendered.html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        browser.close()

    # --- ניתוח ---
    print("=" * 64)
    print(f"נלכדו {len(captured)} תגובות JSON")
    print("=" * 64)

    best = None
    for i, c in enumerate(captured):
        n = _max_array_len(c["data"])
        (out / f"resp_{i}.json").write_text(c["body"], encoding="utf-8")
        print(f"[{i}] {c['method']} {c['status']}  מערך~{n}  {c['url'][:110]}")
        if c["post"]:
            print(f"      POST body: {str(c['post'])[:200]}")
        if best is None or n > best[0]:
            best = (n, i, c)

    if best and best[0] > 0:
        n, i, c = best
        print("\n" + "=" * 64)
        print(f"המועמד הטוב ביותר: [{i}]  {c['url']}")
        print(f"שיטה: {c['method']}   פריטים במערך: {n}")
        print("=" * 64)
        item = _first_array_item(c["data"])
        if isinstance(item, dict):
            print("שדות בפריט בודד:", list(item.keys()))
        print("\nדוגמת פריט בודד:")
        print(json.dumps(item, ensure_ascii=False, indent=2)[:1800])
    else:
        print("\nלא נמצא API עם רשימה — ייתכן שהנתונים מרונדרים בצד השרת.")
        print("נשמר HTML מרונדר ל: tenders/_logs/probe/rendered.html")

    print("\nכל הקבצים נשמרו ב:", out.resolve())
    print("\n>>> העתק לי את כל מה שמודפס למעלה <<<")


def _max_array_len(data, depth: int = 0) -> int:
    """מוצא את אורך המערך הגדול ביותר בכל מבנה ה-JSON (רקורסיבי)."""
    if depth > 6:
        return 0
    best = 0
    if isinstance(data, list):
        best = len(data)
        for v in data[:3]:
            best = max(best, _max_array_len(v, depth + 1))
    elif isinstance(data, dict):
        for v in data.values():
            best = max(best, _max_array_len(v, depth + 1))
    return best


def _first_array_item(data, depth: int = 0):
    """מחזיר פריט לדוגמה מתוך המערך הגדול ביותר."""
    if depth > 6:
        return None
    if isinstance(data, list) and data:
        # אם זה מערך של אובייקטים — החזר את הראשון.
        if isinstance(data[0], (dict, str, int)):
            # בדוק אם יש מערך עמוק יותר וגדול יותר
            deeper = _first_array_item(data[0], depth + 1)
            return deeper if isinstance(deeper, dict) else data[0]
        return data[0]
    if isinstance(data, dict):
        best_len, best_item = 0, None
        for v in data.values():
            n = _max_array_len(v, depth + 1)
            if n > best_len:
                best_len = n
                best_item = _first_array_item(v, depth + 1)
        return best_item
    return None


if __name__ == "__main__":
    main()
