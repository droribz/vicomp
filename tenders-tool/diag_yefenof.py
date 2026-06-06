"""אבחון פענוח רשימת יפה נוף — מדפיס את השורות שפוענחו ומפתחות הזיהוי,
כדי לאתר למה איחוד הכפילויות מכווץ יותר מדי. לא מוריד כלום."""
from __future__ import annotations

from collections import Counter

from infra_tenders.adapters.base import browser_session
from infra_tenders.adapters.yefenof import BASE, parse_yefenof_list
from infra_tenders.core.models import Tender

URL = BASE + "/Tenders"

with browser_session(headless=True) as page:
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)
    html = page.content()

rows = parse_yefenof_list(html, base_url=BASE)
print("סה\"כ שורות שפוענחו:", len(rows))

nums = Counter(repr(r["number"]) for r in rows)
print("מספרים ייחודיים:", len(nums), "מתוך", len(rows))
print("מספרים שחוזרים יותר מפעם:",
      [(n, c) for n, c in nums.most_common(8) if c > 1])

# מפתחות זיהוי של המכרזים הפתוחים
keys = Counter()
for r in rows:
    if r["closed"]:
        continue
    t = Tender(source="yefenof", publisher="יפה נוף",
               tender_number=r["number"], title=r["title"],
               source_url=r["detail_url"] or URL)
    keys[t.identity_key()] += 1
print("\nמפתחות זיהוי ייחודיים (פתוחים):", len(keys))
print("מפתחות שחוזרים:", [(k, c) for k, c in keys.most_common(5) if c > 1])

print("\n--- 15 שורות ראשונות ---")
for r in rows[:15]:
    print(f"  num={r['number']!r:12} closed={r['closed']!s:5} "
          f"title={(r['title'] or '')[:45]!r}")
