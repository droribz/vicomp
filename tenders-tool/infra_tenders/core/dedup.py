"""איחוד כפילויות בין מקורות — אותו מכרז מכמה אתרים -> רשומה אחת."""
from __future__ import annotations

import logging

from .models import Tender

log = logging.getLogger(__name__)

# מקורות שהם אגרגטורים — מפסידים למקור הישיר כמקור הורדה.
AGGREGATOR_SOURCES = {"jobiz"}


def merge_duplicates(tenders: list[Tender]) -> list[Tender]:
    """ממזג מכרזים בעלי אותו identity_key.

    כלל ניצחון מקור ההורדה: מקור ישיר (אתר המפרסם) גובר על אגרגטור.
    בשוויון — מנצח מי שיש לו יותר קבצים. עמודת sources צוברת את כל המקורות.
    """
    by_key: dict[str, Tender] = {}
    for t in tenders:
        key = t.identity_key()
        existing = by_key.get(key)
        if existing is None:
            t.sources = sorted(set(t.sources) | {t.source})
            by_key[key] = t
            continue

        # מיזוג מקורות
        merged_sources = sorted(set(existing.sources) | set(t.sources)
                                | {existing.source, t.source})
        winner = _pick_winner(existing, t)
        winner.sources = merged_sources
        by_key[key] = winner
        log.debug("איחוד כפילות: %s (%s)", winner.title, merged_sources)

    return list(by_key.values())


def _pick_winner(a: Tender, b: Tender) -> Tender:
    a_agg = a.source in AGGREGATOR_SOURCES
    b_agg = b.source in AGGREGATOR_SOURCES
    if a_agg != b_agg:
        return b if a_agg else a               # המקור הישיר מנצח
    return a if len(a.files) >= len(b.files) else b  # יותר קבצים מנצח
