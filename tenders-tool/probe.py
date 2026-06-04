#!/usr/bin/env python3
"""כלי אבחון לאתרי SPA / iframe — מגלה איפה ובאיזה מבנה יושבים המכרזים.

פותח דפדפן גלוי, ממתין לטעינה, ואז:
  1. מקליט תגובות רשת (XHR/fetch) ומזהה כאלה שהן JSON (API אפשרי).
  2. עובר על כל ה-frames (כולל iframe) ומאתר את זה שמכיל מכרזים.
  3. מדפיס את כתובת ה-frame הפנימי, סלקטור מועמד לשורת-מכרז, וה-HTML
     של שורה אחת לדוגמה — כך אפשר לבנות מתאם מדויק.

שימוש:
    python probe.py                          # עמוד המכרזים של נתיבי ישראל
    python probe.py https://some.site/page   # כתובת אחרת
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

DEFAULT_URL = "https://www.iroads.co.il/מכרזים/מכרזים/"
WAIT_SECONDS = 30

# סימנים לכך ש-frame מכיל רשימת מכרזים.
TENDER_MARKERS = ["מספר מכרז", "להגשת הצעות", "מועד הגשה", "להגשה",
                  "סטטוס", "פתוח", "מכרז פומבי"]

# סלקטורים מועמדים לשורת/כרטיס מכרז (לפי סדר ניסיון).
CANDIDATE_SELECTORS = [
    "table tbody tr", "tbody tr", "tr",
    "[class*=tender]", "[class*=Tender]", "[class*=michraz]",
    "[class*=row] ", "[class*=card]", "[class*=item]",
    "ul li", "div.row", "li",
]


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    out = Path("tenders/_logs/probe")
    out.mkdir(parents=True, exist_ok=True)

    xhr: list[dict] = []
    json_hits: list[dict] = []

    def on_response(resp):
        try:
            rtype = resp.request.resource_type
            if rtype not in ("xhr", "fetch"):
                return
            ct = resp.headers.get("content-type", "")
            rec = {"method": resp.request.method, "status": resp.status,
                   "ct": ct, "url": resp.url,
                   "post": resp.request.post_data}
            xhr.append(rec)
            body = resp.text()
            data = json.loads(body)  # ינסה JSON ללא תלות ב-content-type
            n = _max_array_len(data)
            json_hits.append({**rec, "data": data, "body": body, "arr": n})
        except Exception:
            pass

    print(f"פותח דפדפן וטוען: {url}")
    print(f"ממתין {WAIT_SECONDS} שניות... (אל תסגור את הדפדפן)\n")
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

        # --- ניתוח frames ---
        frames = page.frames
        print("=" * 64)
        print(f"נמצאו {len(frames)} frames בעמוד:")
        tender_frame = None
        for i, fr in enumerate(frames):
            try:
                txt = fr.evaluate("document.body ? document.body.innerText : ''")
            except Exception:
                txt = ""
            has = sum(1 for m in TENDER_MARKERS if m in txt)
            print(f"  [{i}] markers={has:<2} url={fr.url[:90]}")
            if has >= 3 and tender_frame is None:
                tender_frame = fr

        # --- ניתוח ה-frame עם המכרזים ---
        if tender_frame is not None:
            print("\n" + "=" * 64)
            print(f"frame המכרזים: {tender_frame.url}")
            print("=" * 64)
            try:
                (out / "tender_frame.html").write_text(
                    tender_frame.content(), encoding="utf-8")
            except Exception:
                pass
            _analyze_frame(tender_frame, out)
        else:
            print("\nלא זוהה frame עם מכרזים. שומר את כל ה-frames לבדיקה.")
            for i, fr in enumerate(frames):
                try:
                    (out / f"frame_{i}.html").write_text(
                        fr.content(), encoding="utf-8")
                except Exception:
                    pass

        browser.close()

    # --- ניתוח רשת ---
    print("\n" + "=" * 64)
    print(f"תגובות XHR/fetch: {len(xhr)}  |  מתוכן JSON: {len(json_hits)}")
    print("=" * 64)
    for r in xhr[:25]:
        print(f"  {r['method']} {r['status']} {r['ct'][:25]:<25} {r['url'][:90]}")
    if json_hits:
        best = max(json_hits, key=lambda x: x["arr"])
        (out / "best_api.json").write_text(best["body"], encoding="utf-8")
        print(f"\nAPI מועמד: {best['method']} {best['url']}  (מערך~{best['arr']})")
        if best["post"]:
            print(f"  POST body: {str(best['post'])[:200]}")
        item = _first_array_item(best["data"])
        if isinstance(item, dict):
            print("  שדות:", list(item.keys()))
        print(json.dumps(item, ensure_ascii=False, indent=2)[:1500])

    print("\nכל הקבצים נשמרו ב:", out.resolve())
    print("\n>>> העתק לי את כל מה שמודפס למעלה <<<")


def _analyze_frame(fr, out: Path) -> None:
    """מנסה סלקטורים, מדפיס ספירות ואת ה-HTML של שורה אחת לדוגמה."""
    best_sel, best_count, best_html = None, 0, ""
    for sel in CANDIDATE_SELECTORS:
        try:
            els = fr.query_selector_all(sel.strip())
        except Exception:
            continue
        count = len(els)
        if count:
            print(f"  סלקטור '{sel.strip():<18}' -> {count} אלמנטים")
        # מחפש סלקטור עם מספר שורות סביר (5..200) שמכיל טקסט של מכרז.
        if 3 <= count <= 300 and count > best_count:
            try:
                sample = els[0].evaluate("e => e.outerHTML")
            except Exception:
                sample = ""
            if any(m in sample for m in TENDER_MARKERS) or "/" in sample:
                best_sel, best_count, best_html = sel.strip(), count, sample

    if best_sel:
        print(f"\nסלקטור מועמד לשורת-מכרז: '{best_sel}'  ({best_count} שורות)")
        print("HTML של שורה אחת לדוגמה (מקוצר):")
        print(best_html[:2500])
        (out / "sample_row.html").write_text(best_html, encoding="utf-8")


def _max_array_len(data, depth: int = 0) -> int:
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
    if depth > 6:
        return None
    if isinstance(data, list) and data:
        deeper = _first_array_item(data[0], depth + 1) if isinstance(data[0], (dict, list)) else None
        return deeper if isinstance(deeper, dict) else data[0]
    if isinstance(data, dict):
        best_len, best_item = 0, None
        for v in data.values():
            n = _max_array_len(v, depth + 1)
            if n > best_len:
                best_len, best_item = n, _first_array_item(v, depth + 1)
        return best_item
    return None


if __name__ == "__main__":
    main()
