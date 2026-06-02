"""ארכוב אוטומטי: מכרזים שמועד ההגשה שלהם עבר עוברים ל-_archive/."""
from __future__ import annotations

import json
import logging
import shutil
from datetime import date
from pathlib import Path

from .dates import is_expired

log = logging.getLogger(__name__)


def archive_expired(root: Path, *, run_day: date) -> int:
    """סורק את tenders/ (לא כולל תיקיות מערכת) ומעביר מכרזים פגי-תוקף.

    מזהה מכרז לפי קיום meta.json. קורא את submission_deadline ממנו.
    מעביר את כל תיקיית המכרז ל-_archive/<מפרסם>/... (לא מוחק).
    מחזיר כמה הועברו.
    """
    archive_root = root / "_archive"
    moved = 0

    for publisher_dir in root.iterdir():
        if not publisher_dir.is_dir() or publisher_dir.name.startswith("_"):
            continue
        for tdir in list(publisher_dir.iterdir()):
            if not tdir.is_dir():
                continue
            meta_path = tdir / "meta.json"
            if not meta_path.exists():
                continue
            deadline = _read_deadline(meta_path)
            if not is_expired(deadline, run_day=run_day):
                continue

            dest = archive_root / publisher_dir.name / tdir.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # כבר קיים בארכיב (הרצה קודמת) — מסירים את הפעיל הכפול.
                shutil.rmtree(tdir)
            else:
                shutil.move(str(tdir), str(dest))
            moved += 1
            log.info("ארכוב: %s (מועד %s עבר)", tdir.name, deadline)

    return moved


def _read_deadline(meta_path: Path) -> date | None:
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        raw = data.get("submission_deadline")
        return date.fromisoformat(raw) if raw else None
    except (json.JSONDecodeError, OSError, ValueError):
        return None
