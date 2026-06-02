import sys
from pathlib import Path

# מאפשר ייבוא של infra_tenders ו-scan מתוך שורש הפרויקט.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
