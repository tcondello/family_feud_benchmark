#!/usr/bin/env python3
"""Score Family Feud benchmark responses against survey boards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from response_format import entry_metrics, entry_question, entry_response


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for prefix in ("a ", "an ", "the "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text


def board_answers(item: dict) -> list[dict]:
    answers = item.get("answers")
    if answers is None:
        answers = item.get("answer")
    if not isinstance(answers, list):
        return []
    return [a for a in answers if isinstance(a, dict) and "answer" in a]


def match_score(llm_answer: str, answers: list[dict]) -> tuple[int, str | None]:
    if llm_answer.startswith("ERROR:"):
        return 0, None
    needle = normalize(llm_answer)
    if not needle:
        return 0, None

    best_score = 0
    best_answer = None
    for entry in answers:
        board = normalize(str(entry.get("answer", "")))
        if not board:
            continue
        if needle == board or needle in board or board in needle:
            score = int(entry.get("score") or 0)
            if score >= best_score:
                best_score = score
                best_answer = str(entry.get("answer"))
    return best_score, best_answer


def load_questions(path: str) -> dict[str, list[dict]]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    questions = data.get("questions") if isinstance(data, dict) else data
    by_question: dict[str, list[dict]] = {}
    for item in questions:
        question = item.get("question")
        if question:
            by_question[question] = board_answers(item)
    return by_question


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def score_model(
    model_key: str, items: list[dict[str, Any]], boards: dict[str, list[dict]]
) -> dict[str, Any]:
    total = 0
    hits = 0
    points = 0
    details = []
    latencies: list[float] = []
    prompt_tokens = 0
    completion_tokens = 0
    cost_usd = 0.0
    instrumented = 0

    for item in items:
        if not isinstance(item, dict) or not item:
            continue
        question = entry_question(item)
        answer = entry_response(item)
        metrics = entry_metrics(item)
        answers = boards.get(question, [])
        score, matched = match_score(str(answer), answers)
        total += 1
        if score > 0:
            hits += 1
            points += score
        detail = {
            "question": question,
            "response": answer,
            "matched": matched,
            "score": score,
            "hit": score > 0,
        }
        if metrics["latency_s"] is not None:
            detail["latency_s"] = metrics["latency_s"]
            latencies.append(float(metrics["latency_s"]))
            instrumented += 1
        if metrics["prompt_tokens"] is not None:
            detail["prompt_tokens"] = metrics["prompt_tokens"]
            prompt_tokens += int(metrics["prompt_tokens"] or 0)
        if metrics["completion_tokens"] is not None:
            detail["completion_tokens"] = metrics["completion_tokens"]
            completion_tokens += int(metrics["completion_tokens"] or 0)
        if metrics["cost_usd"] is not None:
            detail["cost_usd"] = metrics["cost_usd"]
            cost_usd += float(metrics["cost_usd"] or 0.0)
        details.append(detail)

    summary: dict[str, Any] = {
        "questions": total,
        "hits": hits,
        "hit_rate": round(hits / total, 4) if total else 0.0,
        "points": points,
        "avg_points": round(points / total, 2) if total else 0.0,
        "instrumented_answers": instrumented,
        "avg_latency_s": _mean(latencies),
        "prompt_tokens": prompt_tokens or None,
        "completion_tokens": completion_tokens or None,
        "cost_usd": round(cost_usd, 6) if instrumented else None,
        "details": details,
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--responses",
        default="responses/multi_provider_response_list.json",
    )
    parser.add_argument(
        "--questions",
        default="questions/all_questions.json",
    )
    parser.add_argument(
        "--output",
        default="responses/multi_provider_scores.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    boards = load_questions(args.questions)
    with open(args.responses, encoding="utf-8") as handle:
        responses = json.load(handle)

    if isinstance(responses, list):
        responses = {"legacy": responses}

    summary: dict[str, dict] = {}
    for model_key, items in responses.items():
        model_summary = score_model(model_key, items, boards)
        summary[model_key] = model_summary
        extra = ""
        if model_summary["avg_latency_s"] is not None:
            extra += f" avg_latency={model_summary['avg_latency_s']:.2f}s"
        if model_summary["cost_usd"] is not None:
            extra += f" cost=${model_summary['cost_usd']:.4f}"
        print(
            f"{model_key}: hits={model_summary['hits']}/{model_summary['questions']} "
            f"({model_summary['hit_rate']:.1%}) "
            f"points={model_summary['points']} avg={model_summary['avg_points']}"
            f"{extra}"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
