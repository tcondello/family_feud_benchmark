#!/usr/bin/env python3
"""Tail live Family Feud harness traces (JSONL).

Usage:
  python3 -m game.watch_traces
  python3 -m game.watch_traces --contestant Ember
  python3 -m game.watch_traces --file responses/game_traces/live_….jsonl
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

try:
    from game.trace import trace_dir
except ImportError:  # running as `python3 game/watch_traces.py`
    from trace import trace_dir  # type: ignore


def _newest(directory: Path) -> Path | None:
    files = sorted(directory.glob("live_*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _fmt(row: dict, *, verbose: bool, dump_json: bool) -> str | None:
    kind = row.get("kind", "?")
    ts = str(row.get("ts", ""))[11:19]
    if dump_json and kind in {"model_call", "model_error"}:
        slim = {
            "ts": row.get("ts"),
            "kind": kind,
            "contestant": row.get("contestant"),
            "provider": row.get("provider"),
            "model": row.get("model"),
            "phase": row.get("phase"),
            "latency_s": row.get("latency_s"),
            "cleaned": row.get("cleaned"),
            "raw": row.get("raw"),
            "request": row.get("request"),
            "response": row.get("response"),
            "error": row.get("error"),
            "error_body": row.get("error_body"),
        }
        return json.dumps(slim, ensure_ascii=False, indent=2, default=str)

    if kind == "face_off_start":
        return (
            f"{ts} ▶ FACE-OFF  {row.get('question')!r}  "
            f"contestants={row.get('contestants')}"
        )
    if kind == "model_error":
        err = str(row.get("error") or "")[:160]
        line = f"{ts} ✗ ERROR   {row.get('contestant')}: {err}"
        if verbose and row.get("request"):
            line += "\n    request: " + json.dumps(row["request"], ensure_ascii=False)[:500]
        if verbose and row.get("error_body"):
            line += "\n    error_body: " + json.dumps(row["error_body"], ensure_ascii=False)[:500]
        return line
    if kind == "model_call":
        who = row.get("contestant", "?")
        phase = row.get("phase", "?")
        lat = row.get("latency_s")
        lat_s = f"{lat:.2f}s" if isinstance(lat, (int, float)) else "?"
        cleaned = row.get("cleaned")
        line = f"{ts} · {who:<8} {phase:<14} {lat_s:>6}  → {cleaned!r}"
        if verbose:
            bits = [line]
            if row.get("request"):
                bits.append("    request:")
                bits.append(
                    "      "
                    + json.dumps(row["request"], ensure_ascii=False, indent=2).replace(
                        "\n", "\n      "
                    )
                )
            if row.get("response") is not None:
                bits.append("    response:")
                bits.append(
                    "      "
                    + json.dumps(row["response"], ensure_ascii=False, indent=2, default=str).replace(
                        "\n", "\n      "
                    )[:4000]
                )
            raw = row.get("raw")
            if raw and raw != cleaned:
                bits.append(f"    raw_text: {raw!r}"[:500])
            return "\n".join(bits)
        return line
    return f"{ts} · {kind}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Trace directory (default: responses/game_traces)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Specific JSONL file (default: newest live_*.jsonl)",
    )
    parser.add_argument(
        "--contestant",
        default=None,
        help="Only show this contestant (e.g. Ember)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show request/response JSON + raw text",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="dump_json",
        help="Pretty-print each model_call/model_error as JSON (request+response)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print current file and exit (no follow)",
    )
    args = parser.parse_args()

    directory = args.dir or trace_dir()
    path = args.file or _newest(directory)
    if path is None or not path.exists():
        print(f"No traces yet in {directory}")
        if args.once:
            return
        print("Waiting for a live_*.jsonl …")
        while path is None or not path.exists():
            time.sleep(0.5)
            path = _newest(directory)
    assert path is not None

    print(f"Watching {path}")
    if args.contestant:
        print(f"Filter: contestant={args.contestant}")
    print("—")

    offset = 0
    current = path
    while True:
        # Switch to a newer session file if one appears.
        newest = _newest(directory)
        if newest and newest != current and newest.stat().st_mtime >= current.stat().st_mtime:
            if newest.stat().st_size > 0 and newest != current:
                current = newest
                offset = 0
                print(f"\nWatching {current}\n—")

        with current.open("r", encoding="utf-8") as handle:
            handle.seek(offset)
            chunk = handle.read()
            offset = handle.tell()

        for line in chunk.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if args.contestant:
                who = row.get("contestant")
                if who and who != args.contestant:
                    continue
                if row.get("kind") == "face_off_start" and args.contestant not in (
                    row.get("contestants") or []
                ):
                    # still show face-off headers for context
                    pass
            text = _fmt(row, verbose=args.verbose, dump_json=args.dump_json)
            if text:
                print(text, flush=True)
                if args.dump_json:
                    print("—", flush=True)

        if args.once:
            break
        time.sleep(0.35)


if __name__ == "__main__":
    main()
