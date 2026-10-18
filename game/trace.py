"""Append-only JSONL traces for live model calls (harness debugging)."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DIR = _ROOT / "responses" / "game_traces"


def trace_dir() -> Path:
    override = os.getenv("FAMILY_FEUD_TRACE_DIR")
    path = Path(override) if override else _DEFAULT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_path() -> Path:
    """One file per process (host session)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pid = os.getpid()
    return trace_dir() / f"live_{stamp}_{pid}.jsonl"


_SESSION_FILE: Path | None = None


def _file() -> Path:
    global _SESSION_FILE
    if _SESSION_FILE is None:
        _SESSION_FILE = session_path()
    return _SESSION_FILE


def log_event(kind: str, **payload: Any) -> Path:
    """Append one JSON object. Returns the session file path."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        **payload,
    }
    path = _file()
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    return path
