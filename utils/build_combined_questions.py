"""Merge all question sources into one de-duplicated benchmark file."""

from __future__ import annotations

import json
import re
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
    return [
        path
        for path in files
        if path.exists() and path.name not in {"all.json", "all_seasons.json"}
    ]


def source_group(source: dict | None, path: Path) -> str:
    name = (source or {}).get("name") or ""
    if "buzzfeed" in name or path.parts[-2] == "buzzfeed":
        return "buzzfeed"
    if "protoqa" in name or path.parts[-2] == "protoqa":
        return "protoqa"
    if "mstiescott" in name or path.parts[-2] == "mstiescott":
        return "mstiescott"
    return "other"


def source_ref(source: dict | None, path: Path, group: str) -> str:
    if group == "mstiescott":
        season = (source or {}).get("season")
        if season is None:
            m = re.search(r"season_(\d+)", path.name)
            season = int(m.group(1)) if m else None
        return f"season {season}" if season is not None else path.stem
    if group == "protoqa":
        split = (source or {}).get("split") or path.stem
        return str(split)
    if group == "buzzfeed":
        return "buzzfeed list"
    return path.stem


def make_id(group: str, source: dict | None, path: Path, index: int) -> str:
    if group == "mstiescott":
        season = (source or {}).get("season")
        if season is None:
            m = re.search(r"season_(\d+)", path.name)
            season = int(m.group(1)) if m else 0
        return f"ms-s{int(season):02d}-{index:04d}"
    if group == "protoqa":
        split = (source or {}).get("split") or path.stem
        slug = re.sub(r"[^a-z0-9]+", "", str(split).lower())[:16] or "pq"
        return f"pq-{slug}-{index:04d}"
    if group == "buzzfeed":
        return f"bf-{index:04d}"
    return f"other-{index:04d}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    questions_dir = root / "questions"
    source_files = iter_source_files(questions_dir)

    combined = []
    seen = set()
    sources = []
    for path in source_files:
        source, items = load_questions(path)
        group = source_group(source, path)
        ref = source_ref(source, path, group)
        sources.append(
            {
                "path": str(path.relative_to(root)),
                "source": source,
                "group": group,
                "count": len(items),
            }
        )
        before = len(combined)
        local_idx = 0
        for item in items:
            key = item["question"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            local_idx += 1
            combined.append(
                {
                    "id": make_id(group, source, path, local_idx),
                    "source": group,
                    "source_ref": ref,
                    "question": item["question"],
                    "answers": item["answers"],
                }
            )
        print(f"{path.name}: +{len(combined) - before} new / {len(items)} total ({group})")

    out = questions_dir / "all_questions.json"
    out.write_text(
        json.dumps(
            {
                "source": {
                    "name": "combined",
                    "description": (
                        "De-duplicated union of Buzzfeed, ProtoQA, and mstiescott "
                        "sources. Each question carries id + source for filtering."
                    ),
                    "inputs": sources,
                    "groups": {
                        "buzzfeed": "BuzzFeed compiled list",
                        "mstiescott": "TV episode board transcriptions (Steve Harvey-era wording)",
                        "protoqa": "ProtoQA research set (fan surveys + crowdsourced clusters)",
                    },
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
