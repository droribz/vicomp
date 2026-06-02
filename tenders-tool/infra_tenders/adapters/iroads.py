"""מתאם נתיבי ישראל (iroads).

הודות לתשתית הגנרית (generic.py), המתאם הזה כמעט קונפיגורציה בלבד —
ברירות המחדל הגנריות (טבלה/כרטיסים) תופסות את מבנה האתר.

⚠️  הסלקטורים לא נבדקו מול ה-DOM החי (האתר חוסם גישה מסביבת הפיתוח).
    בהרצה הראשונה במחשב שלך:
      1. python scan.py --source iroads --dry-run
      2. אם לא נמצאו מכרזים — פתח את עמוד המכרזים בדפדפן (F12), בדוק את
         מבנה ה-HTML, והתאם את ROW_SELECTORS למטה (או את ברירות המחדל
         ב-generic.py אם זה רלוונטי לכלל המקורות).

פונקציות הפענוח (parse_list_html / parse_detail_html) נחשפות לתאימות עם
ה-tests ומאצילות ל-generic.
"""
from __future__ import annotations

from . import generic
from .generic import GenericAdapter


class IroadsAdapter(GenericAdapter):
    name = "iroads"
    publisher = "נתיבי ישראל"

    # ברירות המחדל הגנריות מתאימות; דרוס כאן רק אם בדיקת האתר החי תדרוש זאת.
    # ROW_SELECTORS = ["table.tenders tbody tr"]


# --- תאימות לאחור עבור ה-tests / שימוש ישיר ---------------------------------
def parse_list_html(html: str, *, base_url: str):
    return generic.extract_list(html, base_url=base_url)


def parse_detail_html(html: str, *, base_url: str):
    return generic.extract_files(html, base_url=base_url)
