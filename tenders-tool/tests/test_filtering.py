from pathlib import Path

from infra_tenders.core.filtering import Keywords, classify
from infra_tenders.core.models import MatchConfidence

KW = Keywords.load(Path(__file__).resolve().parent.parent / "config" / "keywords.yaml")


def test_infra_with_execution_is_high():
    r = classify("ביצוע עבודות סלילה והרחבת כביש 6", KW)
    assert r.include is True
    assert r.confidence == MatchConfidence.HIGH


def test_infra_without_execution_is_low():
    r = classify("גשר מעל נחל הירקון", KW)
    assert r.include is True
    assert r.confidence == MatchConfidence.LOW


def test_pure_consulting_excluded():
    r = classify("שירותי ייעוץ משפטי וליווי חוזי", KW)
    assert r.include is False


def test_design_build_included():
    # "תכנון וביצוע" — מילת ביצוע גוברת על "תכנון", חייב להיכלל.
    r = classify("מכרז לתכנון וביצוע מחלף", KW)
    assert r.include is True


def test_supervision_only_excluded():
    r = classify("ניהול ופיקוח על עבודות", KW)
    assert r.include is False


def test_non_infra_excluded():
    r = classify("רכש ציוד משרדי וריהוט", KW)
    assert r.include is False
