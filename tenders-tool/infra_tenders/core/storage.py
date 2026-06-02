"""תיוק והורדה: מבנה תיקיות, גרסאות, meta.json, אידמפוטנטיות."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import naming
from .dates import today_il
from .http import PoliteClient
from .models import Tender, TenderStatus

log = logging.getLogger(__name__)


@dataclass
class FileOutcome:
    label: str | None
    filename: str
    url: str
    bytes: int = 0
    ok: bool = True
    error: str | None = None


@dataclass
class StoreOutcome:
    """מה קרה למכרז יחיד בתיוק."""

    status: str            # "new" / "updated" / "unchanged" / "dry-run"
    dir: Path
    version: str | None = None
    files: list[FileOutcome] = field(default_factory=list)


class TenderStore:
    """אחראי על תיקיית tenders/ ועל כל פעולות ההורדה והגרסאות."""

    def __init__(self, root: Path, client: PoliteClient, *, dry_run: bool = False):
        self.root = root
        self.client = client
        self.dry_run = dry_run

    # --- מיקום תיקיית מכרז --------------------------------------------------
    def tender_dir(self, tender: Tender, *, archived: bool = False) -> Path:
        base = self.root / "_archive" if archived else self.root
        deadline_iso = (tender.submission_deadline.isoformat()
                        if tender.submission_deadline else "ללא-מועד")
        dirname = naming.tender_dirname(
            deadline_iso=deadline_iso,
            number=tender.tender_number,
            title=tender.title,
        )
        return base / naming.sanitize(tender.publisher) / dirname

    # --- תיוק מכרז יחיד -----------------------------------------------------
    def store(self, tender: Tender) -> StoreOutcome:
        """מתייק מכרז: יוצר/מעדכן תיקייה, מוריד קבצים, כותב meta.json.

        אידמפוטנטי: אם קיים ולא השתנה — לא מוריד שוב.
        עדכון (סט קבצים שונה) — יוצר גרסה חדשה, לא דורס.
        """
        tdir = self.tender_dir(tender)
        meta = self._read_meta(tdir)

        current_urls = sorted(f.url for f in tender.files)
        prev_urls = meta.get("last_file_urls", []) if meta else []

        # --- אידמפוטנטיות: קיים וללא שינוי ---
        if meta and current_urls == prev_urls:
            log.info("  ↳ ללא שינוי, מדלג: %s", tender.title)
            return StoreOutcome(status="unchanged", dir=tdir,
                                version=meta.get("last_version"))

        is_new = meta is None
        version_num = 1 if is_new else int(meta.get("last_version_num", 1)) + 1
        version = f"v{version_num}_{today_il().isoformat()}"

        if self.dry_run:
            log.info("  ↳ [dry-run] %s — היה יורד %d קבצים לגרסה %s",
                     "חדש" if is_new else "עדכון", len(tender.files), version)
            return StoreOutcome(status="dry-run", dir=tdir, version=version)

        version_dir = tdir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        outcomes = self._download_files(tender, version_dir)
        self._write_meta(tdir, tender, version, version_num, current_urls,
                         outcomes, is_new=is_new, prev_meta=meta)

        status = "new" if is_new else "updated"
        log.info("  ↳ %s: %s (גרסה %s, %d קבצים)",
                 "חדש" if is_new else "עודכן", tender.title, version,
                 sum(1 for o in outcomes if o.ok))
        return StoreOutcome(status=status, dir=tdir, version=version,
                            files=outcomes)

    # --- הורדת קבצים --------------------------------------------------------
    def _download_files(self, tender: Tender, version_dir: Path) -> list[FileOutcome]:
        outcomes: list[FileOutcome] = []
        used_names: set[str] = set()
        for f in tender.files:
            fname = f.filename or naming.filename_from_url(f.url, f.label)
            fname = _dedupe_name(fname, used_names)
            dest = version_dir / fname
            try:
                if not self.client.allowed(f.url):
                    raise PermissionError("robots.txt חוסם")
                n = self.client.download(f.url, dest)
                outcomes.append(FileOutcome(f.label, fname, f.url, n, ok=True))
                log.debug("    הורד %s (%d bytes)", fname, n)
            except Exception as exc:  # noqa: BLE001 — נכשל קובץ בודד, ממשיכים
                outcomes.append(FileOutcome(f.label, fname, f.url, 0,
                                            ok=False, error=str(exc)))
                log.warning("    כשל בהורדת %s: %s", f.url, exc)
        return outcomes

    # --- meta.json ----------------------------------------------------------
    def _read_meta(self, tdir: Path) -> dict | None:
        mp = tdir / "meta.json"
        if not mp.exists():
            return None
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_meta(self, tdir: Path, tender: Tender, version: str,
                    version_num: int, file_urls: list[str],
                    outcomes: list[FileOutcome], *, is_new: bool,
                    prev_meta: dict | None) -> None:
        history = (prev_meta or {}).get("versions", [])
        history.append({
            "version": version,
            "date": today_il().isoformat(),
            "files": [
                {"label": o.label, "filename": o.filename, "url": o.url,
                 "bytes": o.bytes, "ok": o.ok, "error": o.error}
                for o in outcomes
            ],
        })
        meta = {
            "title": tender.title,
            "tender_number": tender.tender_number,
            "publisher": tender.publisher,
            "submission_deadline": (tender.submission_deadline.isoformat()
                                    if tender.submission_deadline else None),
            "publication_date": (tender.publication_date.isoformat()
                                 if tender.publication_date else None),
            "source_url": tender.source_url,
            "sources": tender.sources or [tender.source],
            "status": tender.status.value,
            "match_confidence": tender.match_confidence.value,
            "created_at": (prev_meta or {}).get("created_at",
                                                 today_il().isoformat()),
            "updated_at": today_il().isoformat(),
            "last_version": version,
            "last_version_num": version_num,
            "last_file_urls": file_urls,
            "versions": history,
        }
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _dedupe_name(name: str, used: set[str]) -> str:
    """מונע דריסה כששני קבצים מקבלים אותו שם."""
    if name not in used:
        used.add(name)
        return name
    stem, dot, ext = name.rpartition(".")
    i = 2
    while True:
        candidate = f"{stem}_{i}.{ext}" if dot else f"{name}_{i}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1
