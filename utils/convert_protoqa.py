"""Convert the ProtoQA ("Family Feud") research dataset into benchmark schema.

Source: https://github.com/iesl/protoqa-data
Paper: https://arxiv.org/abs/2005.00771

ProtoQA scrapes Family Feud fan-site surveys and also includes crowdsourced
answer clusters. This converter maps cluster labels + counts into the local
`{question, answers: [{answer, score}]}` format.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/iesl/protoqa-data/master"
DEFAULT_FILES = {
    "train": f"{RAW_BASE}/data/train/train.jsonl",
    "dev_scraped": f"{RAW_BASE}/data/dev/dev.scraped.jsonl",
    "dev_crowdsourced": f"{RAW_BASE}/data/dev/dev.crowdsourced.jsonl",
}
USER_AGENT = "family-feud-benchmark/1.0 (research; +https://github.com/tcondello/family_feud_benchmark)"


def fetch_jsonl(url: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        text = response.read().decode("utf-8")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def convert_row(row: dict) -> dict | None:
    question = (row.get("question") or {}).get("original") or (row.get("question") or {}).get(
        "normalized"
    )
    if not question:
        return None
    question = " ".join(question.split()).strip()

    answers_block = row.get("answers") or {}
    clusters = answers_block.get("clusters") or {}
    answers = []
    for cluster in clusters.values():
        labels = cluster.get("answers") or []
        count = cluster.get("count")
        if not labels or count is None:
            continue
        # Scraped ProtoQA clusters typically have one board label.
        label = labels[0].strip()
        if not label:
            continue
        answers.append({"answer": label, "score": int(count)})

    if not answers:
        return None

    answers.sort(key=lambda item: item["score"], reverse=True)
    metadata = row.get("metadata") or {}
    return {
        "question": question,
        "answers": answers,
        "id": metadata.get("id"),
        "protoqa_source": metadata.get("source"),
    }


def convert_file(name: str, url: str) -> dict:
    rows = fetch_jsonl(url)
    questions = []
    for row in rows:
        converted = convert_row(row)
        if converted:
            # Keep only fields used by the benchmark runner; stash provenance lightly.
            questions.append(
                {
                    "question": converted["question"],
                    "answers": converted["answers"],
                }
            )
    return {
        "source": {
            "name": "protoqa",
            "split": name,
            "description": (
                "ProtoQA Family Feud-style questions from iesl/protoqa-data "
                "(scraped fan-site surveys and/or crowdsourced clusters)."
            ),
            "homepage": "https://github.com/iesl/protoqa-data",
            "paper": "https://arxiv.org/abs/2005.00771",
            "url": url,
        },
        "questions": questions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("questions/protoqa"),
        help="Directory for converted ProtoQA JSON files.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=sorted(DEFAULT_FILES),
        default=["train", "dev_scraped", "dev_crowdsourced"],
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    combined: list[dict] = []
    seen: set[str] = set()
    for split in args.splits:
        payload = convert_file(split, DEFAULT_FILES[split])
        out_path = args.output_dir / f"{split}.json"
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path} ({len(payload['questions'])} questions)")
        for item in payload["questions"]:
            key = item["question"].lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)

    combined_path = args.output_dir / "all.json"
    combined_path.write_text(
        json.dumps(
            {
                "source": {
                    "name": "protoqa",
                    "description": "Combined ProtoQA splits converted for this benchmark.",
                    "homepage": "https://github.com/iesl/protoqa-data",
                    "splits": args.splits,
                },
                "questions": combined,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {combined_path} ({len(combined)} questions)")


if __name__ == "__main__":
    main()
