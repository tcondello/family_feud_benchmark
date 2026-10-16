"""Wrap the existing Buzzfeed question list with explicit source metadata."""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = {
    "name": "buzzfeed",
    "description": (
        "Family Feud questions compiled in BuzzFeed's "
        "'115 Family Feud Questions To Liven Up Game Night' list."
    ),
    "homepage": "https://www.buzzfeed.com/kellyrissman/family-feud-questions",
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "questions" / "question_list.json"
    dst_dir = root / "questions" / "buzzfeed"
    dst_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(src.read_text(encoding="utf-8"))
    payload = {"source": SOURCE, "questions": data["questions"]}
    out = dst_dir / "question_list.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(payload['questions'])} questions)")


if __name__ == "__main__":
    main()
