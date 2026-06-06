#!/usr/bin/env python3
"""כלי סריקה והורדה של מכרזי תשתיות בישראל — נקודת כניסה (CLI).

שימוש:
    python scan.py --all                 סריקת כל המקורות הפעילים
    python scan.py --source iroads       סריקת מקור בודד
    python scan.py --list-sources        הצגת המקורות הזמינים והסטטוס שלהם
    python scan.py --all --dry-run        הצגה בלבד, בלי הורדה בפועל
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from infra_tenders.adapters import get_adapter
from infra_tenders.adapters.base import (AdapterBlocked, LoginRequired,
                                         SourceConfig, browser_session)
from infra_tenders.core import dedup, filtering, index as index_mod, report
from infra_tenders.core.archive import archive_expired
from infra_tenders.core.dates import is_expired, today_il
from infra_tenders.core.http import PoliteClient
from infra_tenders.core.logging_setup import setup_logging
from infra_tenders.core.models import (MatchConfidence, ScanResult, Tender,
                                       TenderStatus)
from infra_tenders.core.state import State
from infra_tenders.core.storage import TenderStore

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "tenders"

log = logging.getLogger("scan")


# ---------------------------------------------------------------------------
def load_sources() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    return data.get("sources", [])


def credentials_for(name: str) -> dict:
    """שולף אישורי גישה מ-.env לפי קונבנציית <NAME>_USERNAME/<NAME>_PASSWORD."""
    prefix = name.upper()
    user = os.getenv(f"{prefix}_USERNAME")
    pwd = os.getenv(f"{prefix}_PASSWORD")
    if user and pwd:
        return {"username": user, "password": pwd}
    return {}


# ---------------------------------------------------------------------------
def cmd_list_sources() -> None:
    print("\nמקורות זמינים:\n" + "-" * 60)
    for s in load_sources():
        status = []
        status.append("פעיל" if s.get("enabled") else "כבוי")
        if s.get("requires_login"):
            have = "✓ יש פרטים" if credentials_for(s["name"]) else "✗ חסר .env"
            status.append(f"דורש התחברות ({have})")
        impl = "ממומש" if get_adapter(s["name"]) else "טרם מומש"
        print(f"  {s['name']:<14} {s['publisher']:<22} "
              f"[{', '.join(status)}] [{impl}]")
    print()


# ---------------------------------------------------------------------------
def scan_source(s: dict, page, client: PoliteClient,
                kw: filtering.Keywords, *, debug_dir: Path | None = None
                ) -> tuple[list[Tender], ScanResult, object | None]:
    """שלב 1 למקור בודד: רשימה + סינון תשתיות. מחזיר (מכרזים, תוצאה, מתאם).

    איסוף הקבצים עצמו נעשה בשלב 2 (run), רק למכרזים הסופיים שנבחרו —
    כך --limit מהיר ולא נכנסים לעמודים של מכרזים שייפסלו.
    """
    name = s["name"]
    result = ScanResult(source=name, publisher=s["publisher"])

    adapter_cls = get_adapter(name)
    if adapter_cls is None:
        result.error = "מתאם לא ממומש"
        log.warning("[%s] מתאם לא ממומש — מדלג", name)
        return [], result, None

    creds = credentials_for(name)
    if s.get("requires_login") and not creds:
        result.blocked = True
        result.error = "דורש התחברות ואין פרטים ב-.env"
        log.warning("[%s] דורש התחברות ואין פרטים ב-.env — מדלג בצורה נקייה", name)
        return [], result, None

    cfg = SourceConfig(name=name, publisher=s["publisher"],
                       urls=s.get("urls", []),
                       requires_login=s.get("requires_login", False))
    adapter = adapter_cls(cfg, credentials=creds)
    if debug_dir is not None:
        adapter.debug_dir = debug_dir / name

    try:
        raw = adapter.list_open_tenders(page, client)
    except AdapterBlocked as exc:
        result.blocked = True
        result.error = str(exc)
        log.warning("[%s] נחסם: %s — מדלג", name, exc)
        return [], result, None
    except LoginRequired as exc:
        result.blocked = True
        result.error = str(exc)
        log.warning("[%s] %s", name, exc)
        return [], result, None
    except Exception as exc:  # noqa: BLE001 — נפילת מקור לא מפילה את הסריקה
        result.error = str(exc)
        log.exception("[%s] שגיאה בסריקה: %s", name, exc)
        return [], result, None

    # --- פילטור תשתיות + מועד הגשה ---
    kept: list[Tender] = []
    for t in raw:
        if is_expired(t.submission_deadline):
            continue
        # מסווגים לפי כותרת + קטגוריה (הקטגוריה במקור היא אות תשתית חזק).
        match = filtering.classify(f"{t.title} {t.category}", kw)
        if not match.include:
            log.debug("[%s] לא תשתית: %s (%s)", name, t.title, match.reason)
            continue
        t.match_confidence = match.confidence
        # מכרז ללא מועד מפוענח — שומרים אבל מסמנים low לבדיקה.
        if t.submission_deadline is None:
            t.match_confidence = MatchConfidence.LOW
        kept.append(t)

    result.found = len(kept)
    log.info("[%s] %d מכרזי תשתיות פתוחים (מתוך %d פריטים)",
             name, len(kept), len(raw))
    return kept, result, adapter


# ---------------------------------------------------------------------------
def run(selected: list[dict], *, dry_run: bool, debug: bool = False,
        limit: int | None = None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = setup_logging(OUTPUT_DIR / "_logs")
    run_day = today_il()
    log.info("התחלת סריקה · תאריך %s · dry-run=%s · debug=%s · limit=%s",
             run_day, dry_run, debug, limit)
    debug_dir = (OUTPUT_DIR / "_logs" / "debug") if debug else None

    # 1) ארכוב אוטומטי של מכרזים שמועדם עבר (לא ב-dry-run).
    if not dry_run:
        moved = archive_expired(OUTPUT_DIR, run_day=run_day)
        if moved:
            log.info("הועברו לארכיב %d מכרזים שמועדם עבר", moved)

    state = State(OUTPUT_DIR / "_state.json")
    results: list[ScanResult] = []
    all_tenders: list[Tender] = []
    adapters: dict[str, object] = {}
    rows: list[index_mod.IndexRow] = []
    new_count = 0

    with PoliteClient() as client:
        # דפדפן משותף לכל הסריקה. במצב דיבאג — גלוי.
        with browser_session(headless=not debug) as page:
            # 2) שלב 1: רשימה + סינון לכל מקור (שגיאה במקור אחד לא מפילה).
            for s in selected:
                tenders, result, adapter = scan_source(
                    s, page, client, KEYWORDS, debug_dir=debug_dir)
                all_tenders.extend(tenders)
                results.append(result)
                if adapter is not None:
                    adapters[s["name"]] = adapter

            # 3) איחוד כפילויות בין מקורות.
            merged = dedup.merge_duplicates(all_tenders)
            log.info("לאחר איחוד כפילויות: %d מכרזים ייחודיים", len(merged))

            # 4) הגבלת כמות לכל מקור (--limit, להדגמה/POC).
            if limit:
                merged = _apply_limit(merged, limit)
                log.info("הגבלת --limit %d לכל מקור: %d מכרזים להורדה",
                         limit, len(merged))

            # 5) שלב 2: רק עבור הנבחרים — שליפת קבצים מעמוד המכרז + תיוק.
            store = TenderStore(OUTPUT_DIR, client, dry_run=dry_run)
            for t in merged:
                key = t.identity_key()
                is_new = state.is_new(key)
                if is_new:
                    new_count += 1
                state.mark_seen(key)

                if not dry_run:
                    adapter = adapters.get(t.source)
                    if adapter is not None:
                        t.files = adapter.fetch_files(page, client, t)
                        log.info("[%s] %s — %d קבצים", t.source,
                                 t.tender_number or t.title[:30], len(t.files))

                outcome = store.store(t)
                _tally(results, t.source, outcome.status)
                rows.append(_to_row(t, outcome, is_new=is_new))

    # 6) אינדקס + דוח + מצב.
    if not dry_run:
        index_mod.write_index(OUTPUT_DIR / "_index.csv", rows)
        report.write_report(
            OUTPUT_DIR / "report.html", rows, run_day=run_day,
            summary=_summary(rows, new_count),
        )
        state.save()

    _print_terminal_summary(results, rows, new_count, log_path, dry_run)


# ---------------------------------------------------------------------------
def _apply_limit(tenders: list[Tender], n: int) -> list[Tender]:
    """משאיר עד n מכרזים לכל מקור (לפי סדר הופעתם). ל-POC/הדגמה."""
    counts: dict[str, int] = {}
    out: list[Tender] = []
    for t in tenders:
        c = counts.get(t.source, 0)
        if c < n:
            out.append(t)
            counts[t.source] = c + 1
    return out


def _tally(results: list[ScanResult], source: str, status: str) -> None:
    r = next((x for x in results if x.source == source), None)
    if not r:
        return
    if status in ("new", "updated", "dry-run", "retried"):
        r.downloaded += 1
    elif status == "unchanged":
        r.skipped += 1


def _to_row(t: Tender, outcome, *, is_new: bool) -> index_mod.IndexRow:
    return index_mod.IndexRow(
        publisher=t.publisher,
        title=t.title,
        tender_number=t.tender_number or "",
        submission_deadline=(t.submission_deadline.isoformat()
                             if t.submission_deadline else ""),
        publication_date=(t.publication_date.isoformat()
                          if t.publication_date else ""),
        source_url=t.source_url,
        sources=";".join(t.sources or [t.source]),
        local_path=str(outcome.dir),
        status=t.status.value,
        match_confidence=t.match_confidence.value,
        is_new="כן" if is_new else "לא",
        last_version=outcome.version or "",
        download_date=today_il().isoformat(),
    )


def _summary(rows, new_count: int) -> dict:
    return {
        "total": len(rows),
        "new": new_count,
        "paid": sum(1 for r in rows if r.status in ("paid", "partial")),
        "low": sum(1 for r in rows if r.match_confidence == "low"),
    }


def _print_terminal_summary(results, rows, new_count, log_path, dry_run) -> None:
    print("\n" + "=" * 60)
    print(f"  סיכום סריקה {'(dry-run)' if dry_run else ''}")
    print("=" * 60)
    print(f"  סה\"כ מכרזים פתוחים: {len(rows)}")
    print(f"  חדשים בהרצה זו:      {new_count}")

    by_pub: dict[str, int] = {}
    for r in rows:
        by_pub[r.publisher] = by_pub.get(r.publisher, 0) + 1
    if by_pub:
        print("\n  פילוח לפי מפרסם:")
        for pub, n in sorted(by_pub.items(), key=lambda x: -x[1]):
            print(f"    {pub:<24} {n}")

    problems = [r for r in results if r.blocked or r.error]
    if problems:
        print("\n  מקורות שנחסמו/נכשלו:")
        for r in problems:
            tag = "נחסם" if r.blocked else "נכשל"
            print(f"    [{tag}] {r.publisher}: {r.error}")

    if not dry_run:
        print(f"\n  אינדקס: {OUTPUT_DIR / '_index.csv'}")
        print(f"  דוח:    {OUTPUT_DIR / 'report.html'}")
    print(f"  לוג:    {log_path}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="סריקה והורדה של מכרזי תשתיות פתוחים בישראל")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="סרוק את כל המקורות הפעילים")
    g.add_argument("--source", metavar="NAME", help="סרוק מקור בודד לפי שם")
    g.add_argument("--list-sources", action="store_true",
                   help="הצג מקורות זמינים וסטטוס")
    parser.add_argument("--dry-run", action="store_true",
                        help="הצג מה היה יורד בלי להוריד בפועל")
    parser.add_argument("--debug", action="store_true",
                        help="דפדפן גלוי + שמירת HTML וצילום מסך לכל עמוד (לאבחון)")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="הורד עד N מכרזים מכל מקור (להדגמה/POC)")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")

    if args.list_sources:
        cmd_list_sources()
        return 0

    sources = load_sources()
    if args.source:
        selected = [s for s in sources if s["name"] == args.source]
        if not selected:
            print(f"מקור לא נמצא: {args.source}. הרץ --list-sources לרשימה.")
            return 2
    else:  # --all
        selected = [s for s in sources if s.get("enabled")]
        if not selected:
            print("אין מקורות פעילים ב-config/sources.yaml.")
            return 2

    run(selected, dry_run=args.dry_run, debug=args.debug, limit=args.limit)
    return 0


# נטען פעם אחת — קובץ מילות המפתח.
KEYWORDS = filtering.Keywords.load(CONFIG_DIR / "keywords.yaml")


if __name__ == "__main__":
    sys.exit(main())
