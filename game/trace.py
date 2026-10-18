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


def to_jsonable(value: Any) -> Any:
    """Best-effort convert SDK objects (OpenAI/Anthropic/Gemini) to JSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    # Pydantic v2
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            return to_jsonable(dump(mode="json"))
        except TypeError:
            try:
                return to_jsonable(dump())
            except Exception:  # noqa: BLE001
                pass
    # Pydantic v1
    dump_v1 = getattr(value, "dict", None)
    if callable(dump_v1):
        try:
            return to_jsonable(dump_v1())
        except Exception:  # noqa: BLE001
            pass
    json_method = getattr(value, "model_dump_json", None)
    if callable(json_method):
        try:
            return json.loads(json_method())
        except Exception:  # noqa: BLE001
            pass
    # google-genai / protobuf-ish
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return to_jsonable(to_dict())
        except Exception:  # noqa: BLE001
            pass
    if hasattr(value, "__dict__"):
        try:
            return {
                k: to_jsonable(v)
                for k, v in vars(value).items()
                if not k.startswith("_")
            }
        except Exception:  # noqa: BLE001
            pass
    return repr(value)


def log_event(kind: str, **payload: Any) -> Path:
    """Append one JSON object. Returns the session file path."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        **{k: to_jsonable(v) for k, v in payload.items()},
    }
    path = _file()
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    return path
