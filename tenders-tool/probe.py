#!/usr/bin/env python3
"""כלי אבחון לאתרי מכרזים — מגלה איפה ובאיזה מבנה יושבים המכרזים.

פותח דפדפן גלוי, ממתין לטעינה, ואז:
  1. מקליט תגובות רשת (XHR/fetch) ומזהה JSON (API אפשרי).
  2. עובר על כל ה-frames, מנקד כל אחד לפי סימני-מכרז וקישורי-מכרז,
     ובוחר את ה-frame הרלוונטי ביותר (גם אם יש רק רמז אחד).
  3. מדפיס סלקטור מועמד לשורת-מכרז + ה-HTML של שורה אחת לדוגמה,
     ושומר את ה-HTML המלא — כך אפשר לבנות מתאם מדויק.

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

TENDER_MARKERS = ["מספר מכרז", "להגשת הצעות", "מועד הגשה", "להגשה", "מכרז פומבי",
                  "מכרז מס", "תאריך אחרון", "סטאטוס", "סטטוס", "מכרזים"]

# תבנית קישור שמרמזת על עמוד מכרז (href).
TENDER_HREF = ["tender", "michraz", "מכרז", "tenderid"]

CANDIDATE_SELECTORS = [
    "li.tender-item", "[class*=tender]", "[class*=Tender]", "[class*=michraz]",
    "table tbody tr", "tbody tr", "tr",
    "[class*=item]", "[class*=card]", "[class*=row]",
    "article", "ul li", "li", "div.row",
]


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    out = Path("tenders/_logs/probe")
    out.mkdir(parents=True, exist_ok=True)

    xhr: list[dict] = []
    json_hits: list[dict] = []

    def on_response(resp):
        try:
            if resp.request.resource_type not in ("xhr", "fetch"):
                return
            u = resp.url
            if any(s in u for s in ("analytics", "google", "gtm", "cdn-cgi/rum")):
                return
            ct = resp.headers.get("content-type", "")
            body = ""
            try:
                body = resp.text()
            except Exception:
                pass
            markers = sum(1 for m in TENDER_MARKERS if m in body)
            rec = {"method": resp.request.method, "status": resp.status,
                   "ct": ct, "url": u, "post": resp.request.post_data,
                   "body": body, "markers": markers}
            xhr.append(rec)
            try:
                json_hits.append({**rec, "data": json.loads(body),
                                  "arr": _max_array_len(json.loads(body))})
            except Exception:
                pass
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

        # --- בחירת ה-frame הרלוונטי ביותר ---
        frames = page.frames
        print("=" * 64)
        print(f"נמצאו {len(frames)} frames:")
        best_frame, best_score = None, -1
        for i, fr in enumerate(frames):
            try:
                txt = fr.evaluate("document.body ? document.body.innerText : ''")
            except Exception:
                txt = ""
            markers = sum(1 for m in TENDER_MARKERS if m in txt)
            links = _count_tender_links(fr)
            score = markers + links
            print(f"  [{i}] markers={markers:<2} tender-links={links:<3} "
                  f"url={fr.url[:80]}")
            if score > best_score:
                best_frame, best_score = fr, score

        if best_frame is not None:
            print("\n" + "=" * 64)
            print(f"מנתח frame: {best_frame.url}")
            print("=" * 64)
            try:
                (out / "tender_frame.html").write_text(
                    best_frame.content(), encoding="utf-8")
            except Exception:
                pass
            _analyze_frame(best_frame, out)

        browser.close()

    # --- ניתוח רשת ---
    print("\n" + "=" * 64)
    print(f"תגובות XHR/fetch: {len(xhr)}  |  JSON: {len(json_hits)}")
    print("=" * 64)
    for r in xhr[:25]:
        print(f"  {r['method']} {r['status']} markers={r['markers']:<2} "
              f"{r['ct'][:22]:<22}\n      {r['url']}")
        if r["post"]:
            print(f"      POST: {str(r['post'])[:200]}")
    data_recs = sorted([r for r in xhr if r["markers"] >= 2],
                       key=lambda x: -x["markers"])
    if data_recs:
        rec = data_recs[0]
        (out / "tenders_fragment.html").write_text(rec["body"], encoding="utf-8")
        print("\nתגובת נתונים (HTML עם מכרזים):", rec["url"])
        print(rec["body"][:3000])
    if json_hits:
        best = max(json_hits, key=lambda x: x["arr"])
        print(f"\nAPI מועמד: {best['url']} (מערך~{best['arr']})")
        print(json.dumps(_first_array_item(best["data"]),
                         ensure_ascii=False, indent=2)[:1200])

    print("\nכל הקבצים נשמרו ב:", out.resolve())
    print("\n>>> העתק לי את כל מה שמודפס למעלה <<<")


def _count_tender_links(fr) -> int:
    try:
        hrefs = fr.evaluate(
            "() => Array.from(document.querySelectorAll('a[href]'))"
            ".map(a => a.getAttribute('href'))")
    except Exception:
        return 0
    return sum(1 for h in hrefs if h and any(t in h.lower() for t in TENDER_HREF))


def _analyze_frame(fr, out: Path) -> None:
    # 1) ספירת סלקטורים מועמדים.
    for sel in CANDIDATE_SELECTORS:
        try:
            n = len(fr.query_selector_all(sel))
        except Exception:
            n = 0
        if n:
            print(f"  סלקטור '{sel:<18}' -> {n}")

    # 2) זיהוי שורת-מכרז לפי קישור *ספציפי* לעמוד מכרז (tenderID / Tender?id).
    js = """() => {
        const links = Array.from(document.querySelectorAll('a[href]'));
        const re = /(tenderid=|tender\\?|michraz|מכרז-)/i;
        const matches = links.filter(x => re.test(x.getAttribute('href')||''));
        const a = matches.find(x => !/\\/tenders\\/?$/i.test(x.getAttribute('href')||''))
                  || matches[0];
        if(!a) return {found:false, count:0};
        return {found:true, count:matches.length,
                href:a.getAttribute('href'),
                self:a.outerHTML,
                parent:a.parentElement ? a.parentElement.outerHTML : '',
                grand:(a.parentElement&&a.parentElement.parentElement)
                      ? a.parentElement.parentElement.outerHTML : ''};
    }"""
    try:
        res = fr.evaluate(js)
    except Exception:
        res = {"found": False}

    if res.get("found"):
        print(f"\nקישורי מכרז ספציפיים: {res.get('count')}")
        print("href לדוגמה:", res.get("href"))
        (out / "sample_row.html").write_text(
            res.get("grand") or res.get("parent") or res.get("self"),
            encoding="utf-8")
        print("\n--- הקישור עצמו (a) ---")
        print((res.get("self") or "")[:1400])
        print("\n--- ההורה (parent) ---")
        print((res.get("parent") or "")[:2000])
        print("\n--- הסבא (grandparent, מקוצר) ---")
        print((res.get("grand") or "")[:1500])
    else:
        print("\nלא זוהתה שורת-מכרז לפי קישור. בדוק את tender_frame.html שנשמר.")


def _max_array_len(data, depth=0):
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


def _first_array_item(data, depth=0):
    if depth > 6:
        return None
    if isinstance(data, list) and data:
        deeper = _first_array_item(data[0], depth + 1) if isinstance(data[0], (dict, list)) else None
        return deeper if isinstance(deeper, dict) else data[0]
    if isinstance(data, dict):
        bl, bi = 0, None
        for v in data.values():
            n = _max_array_len(v, depth + 1)
            if n > bl:
                bl, bi = n, _first_array_item(v, depth + 1)
        return bi
    return None


if __name__ == "__main__":
    main()
