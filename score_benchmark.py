#!/usr/bin/env python3
"""Score Family Feud benchmark responses against survey boards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from response_format import entry_metrics, entry_question, entry_response


# Common Family Feud-style equivalents survey respondents treat as the same answer.
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"bike", "bicycle", "bicycles", "bikes"}),
    frozenset({"car", "cars", "automobile", "automobiles", "auto", "autos"}),
    frozenset({"tv", "television", "televisions"}),
    frozenset({"phone", "telephone", "phones", "telephones"}),
    frozenset({"mom", "mother", "mama", "mum"}),
    frozenset({"dad", "father", "papa", "pop"}),
    frozenset({"kid", "kids", "child", "children"}),
    frozenset({"job", "jobs", "occupation", "occupations", "career", "careers"}),
    frozenset({"money", "cash", "dollars", "dollar"}),
    frozenset({"plane", "airplane", "aeroplane", "aircraft"}),
)


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for prefix in ("a ", "an ", "the ", "my ", "your ", "his ", "her ", "their "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text


def _stem_token(token: str) -> str:
    """Light English plural/inflection folding for survey matching."""
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        base = token[:-3]
        # shopping -> shop, running -> run (double consonant)
        if len(base) > 2 and base[-1] == base[-2] and base[-1] not in "aeiou":
            base = base[:-1]
        return base
    if token.endswith(("sses", "xes", "zes", "ches", "shes")):
        return token[:-2]
    if token.endswith("ves") and len(token) > 4:
        return token[:-3] + "f"
    if token.endswith("ees") and len(token) > 4:
        return token[:-1]
    if token.endswith("es") and len(token) > 4 and token[-3] not in "aeiou":
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _compact(text: str) -> str:
    return re.sub(r"[\s/]+", "", text)


def _forms(text: str) -> set[str]:
    """Normalized / compacted / stemmed variants of an answer phrase.

    Multi-word answers keep phrase-level forms only (not bare tokens like
    "get"), so "get married" does not match "get hitched".
    """
    base = normalize(text)
    if not base:
        return set()
    parts = [p.strip() for p in base.split("/") if p.strip()] or [base]
    forms: set[str] = set()
    for part in parts:
        forms.add(part)
        forms.add(_compact(part))
        tokens = [_stem_token(t) for t in part.split() if t]
        if not tokens:
            continue
        stemmed = " ".join(tokens)
        forms.add(stemmed)
        forms.add(_compact(stemmed))
        forms.add("".join(tokens))
        # Single-token answers also keep the stemmed token itself.
        if len(tokens) == 1:
            forms.add(tokens[0])
    return {f for f in forms if f}

_CANON: dict[str, str] = {}
for _group in _SYNONYM_GROUPS:
    _rep = sorted(_group, key=len)[0]
    for _word in _group:
        _CANON[_word] = _rep


def _canonicalize_phrase(text: str) -> tuple[str, str]:
    tokens = [
        _CANON.get(_stem_token(t), _stem_token(t))
        for t in normalize(text).replace("/", " ").split()
        if t
    ]
    spaced = " ".join(tokens)
    return spaced, "".join(tokens)


def _compact_related(a: str, b: str) -> bool:
    """Allow only trivial suffix differences on compact forms (patch/patches)."""
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < 4:
        return False
    if not longer.startswith(shorter):
        return False
    return longer[len(shorter) :] in {"s", "es", "ed", "er", "ing"}


def _ff_contains(a: str, b: str) -> bool:
    """Word-aware containment (shop↔shopping, dress↔formal dress) without phone↔telephone."""
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < 4:
        return False
    # Inflection of a single token first (shop/shopping).
    _INFLECT = {"s", "es", "ed", "er", "ing"}
    for tok in longer.split():
        if tok.startswith(shorter) and tok[len(shorter) :] in _INFLECT:
            return True
        if shorter.startswith(tok) and shorter[len(tok) :] in _INFLECT:
            return True
    # Whole-word hit inside a multi-word phrase (gaga in lady gaga).
    # Skip when shorter is the entire other side after synonym collapse would
    # already be handled by equality; require longer to have 2+ tokens.
    if " " in longer and re.search(rf"(^| ){re.escape(shorter)}( |$)", longer):
        return True
    return False


def answers_match(llm_answer: str, board_answer: str) -> bool:
    """Family Feud soft match: plurals, compounds, slash alternatives, common synonyms."""
    left = _forms(llm_answer)
    right = _forms(board_answer)
    # Slash alternatives are independent acceptable board answers.
    for part in normalize(board_answer).split("/"):
        if part.strip():
            right |= _forms(part)
    for part in normalize(llm_answer).split("/"):
        if part.strip():
            left |= _forms(part)

    if not left or not right:
        return False
    if left & right:
        return True

    # Classic FF containment on lexical forms only (not synonym-collapsed).
    for a in left:
        for b in right:
            if _ff_contains(a, b) or _compact_related(_compact(a), _compact(b)):
                return True

    # Synonyms / light modifiers: compare canonicalized phrases only.
    left_space, left_join = _canonicalize_phrase(llm_answer)
    right_space, right_join = _canonicalize_phrase(board_answer)
    if left_join and right_join and left_join == right_join:
        return True
    if left_space and right_space and left_space == right_space:
        return True
    _MODIFIERS = {
        "new",
        "old",
        "big",
        "little",
        "small",
        "giant",
        "red",
        "blue",
        "green",
        "black",
        "white",
        "hot",
        "cold",
        "fresh",
    }
    if left_space and right_space:
        lt = set(left_space.split())
        rt = set(right_space.split())
        if lt and rt:
            if lt <= rt and (rt - lt) <= _MODIFIERS:
                return True
            if rt <= lt and (lt - rt) <= _MODIFIERS:
                return True
    # Synonym on slash parts (bike ↔ bicycle as a board alternative).
    for part in normalize(board_answer).split("/"):
        if not part.strip():
            continue
        p_space, p_join = _canonicalize_phrase(part)
        if left_join and p_join and left_join == p_join:
            return True
        if left_space and p_space and left_space == p_space:
            return True
    return False


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
        board_raw = str(entry.get("answer", ""))
        if not board_raw.strip():
            continue
        if answers_match(llm_answer, board_raw):
            score = int(entry.get("score") or 0)
            if score >= best_score:
                best_score = score
                best_answer = board_raw
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


def load_question_meta(path: str) -> dict[str, dict[str, Any]]:
    """question text -> {id, source, source_ref}."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    questions = data.get("questions") if isinstance(data, dict) else data
    meta: dict[str, dict[str, Any]] = {}
    for item in questions:
        question = item.get("question")
        if not question:
            continue
        meta[question] = {
            "id": item.get("id") or "",
            "source": item.get("source") or "unknown",
            "source_ref": item.get("source_ref") or "",
        }
    return meta


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
