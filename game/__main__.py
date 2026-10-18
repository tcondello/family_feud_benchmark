"""python -m game — launch the Family Feud host TUI."""

from __future__ import annotations

import argparse
from pathlib import Path

from game.tui import DEFAULT_QUESTIONS, run


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Family Feud host TUI — Mode B (3 strikes + steal), "
            "solo models, lockout buzz, BuzzFeed 115"
        )
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help="Question JSON (default: questions/question_list.json = BuzzFeed 115)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on loaded questions",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call real model APIs for buzz-in / main play / steal",
    )
    parser.add_argument(
        "--contestants",
        nargs="+",
        default=None,
        help="Optional subset of display names (e.g. Opus Flash Ember)",
    )
    args = parser.parse_args()
    run(
        args.questions,
        limit=args.limit,
        live=args.live,
        contestants=args.contestants,
    )


if __name__ == "__main__":
    main()
