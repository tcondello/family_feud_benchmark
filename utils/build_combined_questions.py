"""Merge all question sources into one de-duplicated benchmark file."""

from __future__ import annotations

import json
from pathlib import Path


def load_questions(path: Path) -> tuple[dict | None, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "questions" in data:
        return data.get("source"), data["questions"]
    if isinstance(data, list):
        return None, data
    raise ValueError(f"Unrecognized schema in {path}")


def iter_source_files(questions_dir: Path) -> list[Path]:
    files = [questions_dir / "buzzfeed" / "question_list.json"]
    files.extend(sorted((questions_dir / "protoqa").glob("*.json")))
    files.extend(sorted((questions_dir / "mstiescott").glob("season_*.json")))
    # Prefer granular source files; skip prebuilt aggregates if present.
    return [path for path in files if path.exists() and path.name not in {"all.json", "all_seasons.json"}]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    questions_dir = root / "questions"
    source_files = iter_source_files(questions_dir)

    combined = []
    seen = set()
    sources = []
    for path in source_files:
        source, items = load_questions(path)
        sources.append({"path": str(path.relative_to(root)), "source": source, "count": len(items)})
        before = len(combined)
        for item in items:
            key = item["question"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append({"question": item["question"], "answers": item["answers"]})
        print(f"{path.name}: +{len(combined) - before} new / {len(items)} total")

    out = questions_dir / "all_questions.json"
    out.write_text(
        json.dumps(
            {
                "source": {
                    "name": "combined",
                    "description": "De-duplicated union of Buzzfeed, ProtoQA, and mstiescott sources.",
                    "inputs": sources,
                },
                "questions": combined,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(combined)} questions)")


if __name__ == "__main__":
    main()
