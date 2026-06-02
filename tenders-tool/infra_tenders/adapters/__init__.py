"""רישום (registry) של המתאמים. הוספת מקור = הוספת מתאם + רישום כאן."""
from __future__ import annotations

from .base import BaseAdapter
from .iroads import IroadsAdapter

# מיפוי name -> מחלקת מתאם. השם חייב להתאים ל-name ב-config/sources.yaml.
ADAPTERS: dict[str, type[BaseAdapter]] = {
    "iroads": IroadsAdapter,
    # מתאמים נוספים יתווספו כאן: "nta": NtaAdapter, ...
}


def get_adapter(name: str) -> type[BaseAdapter] | None:
    return ADAPTERS.get(name)
