"""הקמת לוגינג — גם לקונסולה וגם לקובץ לוג ייעודי לכל סריקה."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def setup_logging(logs_dir: Path, *, verbose: bool = True) -> Path:
    """מקים לוגר שכותב לקונסולה ולקובץ _logs/scan_<timestamp>.log."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = logs_dir / f"scan_{stamp}.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%H:%M:%S")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    return log_path
