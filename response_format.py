"""Shared helpers for legacy and instrumented benchmark response records."""

from __future__ import annotations

from typing import Any


def entry_question(entry: dict[str, Any]) -> str:
    if "question" in entry and "response" in entry:
        return str(entry.get("question") or "")
    if not entry:
        return ""
    return str(next(iter(entry.keys())))


def entry_response(entry: dict[str, Any]) -> str:
    if "question" in entry and "response" in entry:
        return str(entry.get("response") or "")
    if not entry:
        return ""
    return str(next(iter(entry.values())))


def entry_metrics(entry: dict[str, Any]) -> dict[str, float | int | None]:
    if "question" in entry and "response" in entry:
        return {
            "latency_s": entry.get("latency_s"),
            "prompt_tokens": entry.get("prompt_tokens"),
            "completion_tokens": entry.get("completion_tokens"),
            "cost_usd": entry.get("cost_usd"),
        }
    return {
        "latency_s": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "cost_usd": None,
    }


def make_result_entry(
    question: str,
    response: str,
    *,
    latency_s: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
) -> dict[str, Any]:
    return {
        "question": question,
        "response": response,
        "latency_s": round(float(latency_s), 4),
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "cost_usd": round(float(cost_usd or 0.0), 8),
    }
