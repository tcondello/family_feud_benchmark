#!/usr/bin/env python3
"""Score Family Feud benchmark responses against survey boards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Drop leading articles for soft matching.
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

    # Support both legacy list format and multi-provider dict format.
    if isinstance(responses, list):
        responses = {"legacy": responses}

    summary: dict[str, dict] = {}
    for model_key, items in responses.items():
        total = 0
        hits = 0
        points = 0
        details = []
        for item in items:
            if not isinstance(item, dict) or not item:
                continue
            question, answer = next(iter(item.items()))
            answers = boards.get(question, [])
            score, matched = match_score(str(answer), answers)
            total += 1
            if score > 0:
                hits += 1
                points += score
            details.append(
                {
                    "question": question,
                    "response": answer,
                    "matched": matched,
                    "score": score,
                }
            )
        summary[model_key] = {
            "questions": total,
            "hits": hits,
            "hit_rate": round(hits / total, 4) if total else 0.0,
            "points": points,
            "avg_points": round(points / total, 2) if total else 0.0,
            "details": details,
        }
        print(
            f"{model_key}: hits={hits}/{total} "
            f"({summary[model_key]['hit_rate']:.1%}) "
            f"points={points} avg={summary[model_key]['avg_points']}"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
