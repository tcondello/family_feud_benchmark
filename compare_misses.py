#!/usr/bin/env python3
"""Compare Family Feud misses / disagreements across models.

Reads scored details (or scores on the fly) and writes:
  - per-model miss counts
  - pairwise disagreement matrix (hit vs miss)
  - question-level rows where models diverge
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from score_benchmark import load_questions, score_model


def load_or_build_scores(
    *,
    scores_path: str | None,
    responses_path: str,
    questions_path: str,
) -> dict[str, dict[str, Any]]:
    if scores_path and Path(scores_path).exists():
        data = json.loads(Path(scores_path).read_text(encoding="utf-8"))
        # Ensure details exist; rebuild if missing.
        if data and all("details" in v for v in data.values()):
            return data

    boards = load_questions(questions_path)
    responses = json.loads(Path(responses_path).read_text(encoding="utf-8"))
    if isinstance(responses, list):
        responses = {"legacy": responses}
    return {
        model: score_model(model, items, boards)
        for model, items in responses.items()
    }


def build_question_table(
    scores: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """question -> model -> detail row."""
    table: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for model, summary in scores.items():
        for detail in summary.get("details", []):
            question = detail.get("question")
            if not question:
                continue
            table[question][model] = detail
    return table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--responses",
        default="responses/multi_provider_all_questions.json",
    )
    parser.add_argument(
        "--questions",
        default="questions/all_questions.json",
    )
    parser.add_argument(
        "--scores",
        default=None,
        help="Optional precomputed scores JSON (with details)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Optional subset of model keys to compare",
    )
    parser.add_argument(
        "--output-json",
        default="responses/miss_comparison.json",
    )
    parser.add_argument(
        "--output-csv",
        default="responses/miss_comparison.csv",
    )
    parser.add_argument(
        "--only-disagreements",
        action="store_true",
        help="CSV/JSON rows only where models disagree on hit/miss",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max disagreement rows to print to stdout",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scores = load_or_build_scores(
        scores_path=args.scores,
        responses_path=args.responses,
        questions_path=args.questions,
    )
    if args.models:
        selected = set(args.models)
        scores = {k: v for k, v in scores.items() if k in selected}

    models = sorted(scores.keys())
    if len(models) < 2:
        raise SystemExit("Need at least two models to compare.")

    table = build_question_table(scores)

    # Per-model miss summary (only on questions answered by that model).
    print("PER-MODEL MISSES")
    for model in models:
        details = scores[model].get("details", [])
        total = len(details)
        misses = sum(1 for d in details if not d.get("hit"))
        print(f"  {model}: misses={misses}/{total} ({(misses/total if total else 0):.1%})")

    # Pairwise disagreement on overlapping questions.
    print("\nPAIRWISE HIT/MISS DISAGREEMENTS")
    print(f"{'model_a':<32} {'model_b':<32} overlap  disagree  rate")
    pairwise = {}
    for i, a in enumerate(models):
        for b in models[i + 1 :]:
            overlap = 0
            disagree = 0
            for question, row in table.items():
                if a not in row or b not in row:
                    continue
                overlap += 1
                if bool(row[a].get("hit")) != bool(row[b].get("hit")):
                    disagree += 1
            rate = disagree / overlap if overlap else 0.0
            pairwise[f"{a}__vs__{b}"] = {
                "model_a": a,
                "model_b": b,
                "overlap": overlap,
                "disagree": disagree,
                "disagree_rate": round(rate, 4),
            }
            print(
                f"{a:<32} {b:<32} {overlap:7d}  {disagree:8d}  {rate:5.1%}"
            )

    # Question-level comparison rows.
    rows: list[dict[str, Any]] = []
    for question, model_rows in table.items():
        present = [m for m in models if m in model_rows]
        if len(present) < 2:
            continue
        hits = [m for m in present if model_rows[m].get("hit")]
        misses = [m for m in present if not model_rows[m].get("hit")]
        disagree = bool(hits) and bool(misses)
        if args.only_disagreements and not disagree:
            continue
        row: dict[str, Any] = {
            "question": question,
            "models_present": present,
            "hit_models": hits,
            "miss_models": misses,
            "disagreement": disagree,
            "all_miss": len(hits) == 0,
            "all_hit": len(misses) == 0,
        }
        for model in models:
            detail = model_rows.get(model)
            if not detail:
                row[f"{model}::response"] = None
                row[f"{model}::hit"] = None
                row[f"{model}::matched"] = None
                row[f"{model}::score"] = None
                continue
            row[f"{model}::response"] = detail.get("response")
            row[f"{model}::hit"] = detail.get("hit")
            row[f"{model}::matched"] = detail.get("matched")
            row[f"{model}::score"] = detail.get("score")
        rows.append(row)

    disagreements = [r for r in rows if r["disagreement"]]
    all_miss = [r for r in rows if r["all_miss"]]
    print(
        f"\nquestions_compared={len(rows)} disagreements={len(disagreements)} "
        f"all_models_miss={len(all_miss)}"
    )

    # Sample disagreements to stdout.
    sample = disagreements[: args.limit] if args.limit is not None else disagreements[:15]
    if sample:
        print("\nSAMPLE DISAGREEMENTS")
        for row in sample:
            print(f"- {row['question']}")
            print(f"  hit: {', '.join(row['hit_models']) or '(none)'}")
            print(f"  miss: {', '.join(row['miss_models']) or '(none)'}")
            for model in row["models_present"]:
                print(
                    f"    {model}: {row.get(f'{model}::response')!r} "
                    f"(matched={row.get(f'{model}::matched')!r}, "
                    f"score={row.get(f'{model}::score')})"
                )

    out_json = {
        "models": models,
        "pairwise": pairwise,
        "summary": {
            "questions_compared": len(rows),
            "disagreements": len(disagreements),
            "all_models_miss": len(all_miss),
            "all_models_hit": sum(1 for r in rows if r["all_hit"]),
        },
        "per_model_misses": {
            model: {
                "misses": sum(
                    1 for d in scores[model].get("details", []) if not d.get("hit")
                ),
                "total": len(scores[model].get("details", [])),
            }
            for model in models
        },
        "rows": rows,
    }
    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(out_json, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {json_path}")

    csv_path = Path(args.output_csv)
    fieldnames = [
        "question",
        "disagreement",
        "all_miss",
        "all_hit",
        "hit_models",
        "miss_models",
    ]
    for model in models:
        fieldnames.extend(
            [
                f"{model}::response",
                f"{model}::hit",
                f"{model}::matched",
                f"{model}::score",
            ]
        )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            flat["hit_models"] = "|".join(row["hit_models"])
            flat["miss_models"] = "|".join(row["miss_models"])
            writer.writerow(flat)
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
