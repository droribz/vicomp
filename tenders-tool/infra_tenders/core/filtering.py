"""מנוע סיווג 'תשתית' לפי מילות המפתח שב-config/keywords.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import MatchConfidence


@dataclass
class Keywords:
    infrastructure: list[str]
    execution: list[str]
    exclude: list[str]

    @classmethod
    def load(cls, path: str | Path) -> "Keywords":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            infrastructure=[_norm(k) for k in data.get("infrastructure", [])],
            execution=[_norm(k) for k in data.get("execution", [])],
            exclude=[_norm(k) for k in data.get("exclude", [])],
        )


@dataclass
class MatchResult:
    include: bool
    confidence: MatchConfidence
    reason: str   # הסבר קצר ללוג


def classify(text: str, kw: Keywords) -> MatchResult:
    """מסווג טקסט (כותרת + קטגוריה) למכרז תשתיות רלוונטי או לא.

    לוגיקה:
      - יש מילת ביצוע?  has_exec
      - יש מילת תשתית?  has_infra
      - יש מילת החרגה?  has_exclude
      כלל: אם has_exclude ואין has_exec ואין has_infra חזק -> לא לכלול.
           מילת execution גוברת על exclude (כדי לא לפספס "תכנון וביצוע").
      ביטחון: high אם has_infra וגם has_exec, אחרת low.
    """
    t = _norm(text)
    matched_infra = [k for k in kw.infrastructure if k and k in t]
    matched_exec = [k for k in kw.execution if k and k in t]
    matched_excl = [k for k in kw.exclude if k and k in t]

    has_infra = bool(matched_infra)
    has_exec = bool(matched_exec)
    has_excl = bool(matched_excl)

    # 1) מילת ביצוע + תשתית גוברת על החרגה (Design-Build / "תכנון וביצוע").
    if has_exec and has_infra:
        return MatchResult(True, MatchConfidence.HIGH,
                           f"תשתית={matched_infra} ביצוע={matched_exec}")

    # 2) מילת החרגה (ללא ביצוע) = רעש (ייעוץ/תכנון/פיקוח/מאגר וכו') — לא לכלול.
    if has_excl:
        return MatchResult(False, MatchConfidence.LOW, f"הוחרג: {matched_excl}")

    # 3) תשתית בלבד (בלי ביצוע ובלי החרגה) — כולל בביטחון נמוך לבדיקה ידנית.
    if has_infra:
        return MatchResult(True, MatchConfidence.LOW,
                           f"תשתית={matched_infra} ללא מילת ביצוע")

    return MatchResult(False, MatchConfidence.LOW, "אין מילת תשתית")


def _norm(text: str) -> str:
    if not text:
        return ""
    text = text.replace("׳", "'").replace("״", '"')
    return " ".join(text.split()).lower()
