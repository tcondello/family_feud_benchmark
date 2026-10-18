"""python -m game — launch the Family Feud host TUI."""

from __future__ import annotations

import argparse
from pathlib import Path

from game.tui import DEFAULT_QUESTIONS, run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Family Feud host TUI (Phase 1: mock buzz)"
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help="Question JSON (default: questions/question_list.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on loaded questions",
    )
    args = parser.parse_args()
    run(args.questions, limit=args.limit)


if __name__ == "__main__":
    main()
