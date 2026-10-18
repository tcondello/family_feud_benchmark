"""Face-off and main-play model calls (mock or live)."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from dotenv import load_dotenv

from game.engine import (
    BuzzEvent,
    MatchState,
    apply_face_off_results,
    grade_against_board,
    mock_buzz,
)
from game.rules import (
    CONTESTANT_MODELS,
    FACE_OFF_SYSTEM,
    MAIN_PLAY_SYSTEM,
    PROVIDER_ENV,
)
from game.trace import log_event, to_jsonable

load_dotenv()


@dataclass
class ProviderResult:
    """Exact client I/O for harness traces."""

    text: str
    latency_s: float
    request: dict[str, Any]
    response: Any = None


def available_contestants() -> list[str]:
    """Contestants whose provider API keys are present (or all in mock)."""
    names = []
    for name, (provider, _model) in CONTESTANT_MODELS.items():
        env = PROVIDER_ENV[provider]
        if os.getenv(env):
            names.append(name)
    return names


def _call_openai(model: str, system: str, user: str) -> ProviderResult:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    request = {
        "provider": "openai",
        "endpoint": "chat.completions.create",
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": 64,
    }
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=request["messages"],
        max_completion_tokens=64,
    )
    latency = time.perf_counter() - start
    text = (response.choices[0].message.content or "").strip()
    return ProviderResult(text=text, latency_s=latency, request=request, response=response)


def _call_anthropic(model: str, system: str, user: str) -> ProviderResult:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    request = {
        "provider": "anthropic",
        "endpoint": "messages.create",
        "model": model,
        "max_tokens": 64,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=64,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    latency = time.perf_counter() - start
    text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    ).strip()
    return ProviderResult(text=text, latency_s=latency, request=request, response=response)


def _is_rate_limited(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return (
        "429" in text
        or "resource_exhausted" in text
        or "rate limit" in text
        or "too many requests" in text
    )


def _call_with_retries(
    fn: Callable[[], ProviderResult],
    *,
    attempts: int = 4,
    base_delay_s: float = 1.5,
) -> ProviderResult:
    """Retry transient provider rate limits (esp. Gemini free-tier 429s)."""
    last: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not _is_rate_limited(exc) or attempt >= attempts - 1:
                raise
            delay = base_delay_s * (2**attempt) + (0.1 * attempt)
            time.sleep(delay)
    assert last is not None
    raise last


def _call_google(model: str, system: str, user: str) -> ProviderResult:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    request = {
        "provider": "google",
        "endpoint": "models.generate_content",
        "model": model,
        "contents": user,
        "config": {
            "system_instruction": system,
            "max_output_tokens": 64,
        },
    }

    def once() -> ProviderResult:
        start = time.perf_counter()
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=64,
            ),
        )
        latency = time.perf_counter() - start
        text = (getattr(response, "text", None) or "").strip()
        return ProviderResult(
            text=text, latency_s=latency, request=request, response=response
        )

    return _call_with_retries(once, attempts=5, base_delay_s=2.0)


def _call_fireworks(model: str, system: str, user: str) -> ProviderResult:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url="https://api.fireworks.ai/inference/v1",
    )
    # Keep completions tiny — Qwen/Kimi otherwise dump chain-of-thought into content.
    request = {
        "provider": "fireworks",
        "endpoint": "chat.completions.create",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 48,
        "temperature": 0,
    }
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=request["messages"],
        max_tokens=48,
        temperature=0,
    )
    latency = time.perf_counter() - start
    message = response.choices[0].message
    text = (message.content or "").strip()
    if not text:
        text = (getattr(message, "reasoning_content", None) or "").strip()
    return ProviderResult(text=text, latency_s=latency, request=request, response=response)


_CALLERS: dict[str, Callable[[str, str, str], ProviderResult]] = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "google": _call_google,
    "fireworks": _call_fireworks,
}


def _clean(text: str) -> str:
    """Collapse model output to a short survey phrase.

    Reasoning models (esp. Qwen on Fireworks) often return a monologue that
    *mentions* board answers. Feeding that whole blob back as a wrong-guess
    — or grading with substring match — creates infinite strike loops.
    """
    import re

    text = (text or "").strip().strip('"').strip("'")
    if not text:
        return ""

    # Prefer explicit final-answer markers.
    for pattern in (
        r"(?is)\bfinal(?:\s+answer)?\s*:\s*(.+)$",
        r"(?is)\banswer\s*:\s*(.+)$",
        r"(?is)\bchoose\s*[\"']?([A-Za-z][^\"'\n.]{0,40})",
    ):
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()
            break

    # Last quoted short phrase wins (common in CoT dumps).
    quotes = re.findall(r"[\"']([^\"']{1,40})[\"']", text)
    short_quotes = [q.strip() for q in quotes if 0 < len(q.split()) <= 5]
    if short_quotes and (
        len(text.split()) > 6 or "need" in text.lower() or "final" in text.lower()
    ):
        text = short_quotes[-1]

    lines = [ln.strip().strip('"').strip("'") for ln in text.splitlines() if ln.strip()]
    if lines:
        text = lines[-1]

    # Drop trailing meta.
    text = re.sub(r"(?i)\s*(ensure only|only answer words|final).*$", "", text).strip()
    if text.endswith(".") and len(text.split()) <= 5:
        text = text[:-1]

    # If still a monologue, refuse to treat it as an answer (empty → strike,
    # but short enough that we won't pollute the next prompt).
    words = text.split()
    if len(words) > 8 or len(text) > 60:
        # Last ditch: take a trailing Capitalized phrase of ≤4 words.
        trail = re.findall(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,3})\b", text)
        if trail:
            text = trail[-1]
        else:
            return ""
        if len(text.split()) > 5:
            return ""
    return text


def query_contestant(
    name: str,
    system: str,
    user: str,
    *,
    phase: str = "unknown",
) -> tuple[str, float]:
    provider, model = CONTESTANT_MODELS[name]
    if not os.getenv(PROVIDER_ENV[provider]):
        raise RuntimeError(f"Missing {PROVIDER_ENV[provider]} for {name}")
    request_preview = {
        "provider": provider,
        "model": model,
        "system": system,
        "user": user,
    }
    try:
        result = _CALLERS[provider](model, system, user)
    except Exception as exc:  # noqa: BLE001
        log_event(
            "model_error",
            phase=phase,
            contestant=name,
            provider=provider,
            model=model,
            system=system,
            user=user,
            request=request_preview,
            error=f"{type(exc).__name__}: {exc}",
            error_body=to_jsonable(getattr(exc, "body", None) or getattr(exc, "response", None) or str(exc)),
        )
        raise
    cleaned = _clean(result.text)
    log_event(
        "model_call",
        phase=phase,
        contestant=name,
        provider=provider,
        model=model,
        system=system,
        user=user,
        request=to_jsonable(result.request),
        response=to_jsonable(result.response),
        raw=result.text,
        cleaned=cleaned,
        latency_s=round(result.latency_s, 4),
    )
    return cleaned, result.latency_s


def live_buzz(state: MatchState) -> MatchState:
    """Buzz all contestants concurrently; first board-hit wins; misses lock out."""
    if state.question is None:
        state.message = "Pick a question first."
        return state

    question = state.question.text
    slots = state.question.slots
    events: list[BuzzEvent] = []

    log_event(
        "face_off_start",
        question=question,
        contestants=list(state.contestants),
    )

    def one(name: str) -> BuzzEvent:
        try:
            text, latency = query_contestant(
                name, FACE_OFF_SYSTEM, question, phase="face_off"
            )
        except Exception as exc:  # noqa: BLE001
            return BuzzEvent(
                model=name,
                text=f"ERROR: {type(exc).__name__}: {exc}",
                latency_s=0.0,
                hit=False,
            )
        hit, matched, points = grade_against_board(text, slots)
        return BuzzEvent(
            model=name,
            text=text,
            latency_s=round(latency, 3),
            hit=hit,
            matched=matched,
            points=points,
        )

    with ThreadPoolExecutor(max_workers=max(1, len(state.contestants))) as pool:
        futures = {pool.submit(one, name): name for name in state.contestants}
        for future in as_completed(futures):
            events.append(future.result())

    return apply_face_off_results(state, events)


def live_answer(
    name: str,
    question: str,
    revealed: list[str],
    wrong_guesses: list[str] | None = None,
) -> tuple[str, float]:
    """Main-play / steal prompt — must include strikes so models don't repeat misses."""
    wrong_guesses = wrong_guesses or []
    revealed_s = ", ".join(revealed) if revealed else "(none yet)"
    wrong_s = ", ".join(wrong_guesses) if wrong_guesses else "(none yet)"
    user = (
        f"Survey question: {question}\n"
        f"Already revealed on the board (do not repeat): {revealed_s}\n"
        f"Already tried and WRONG / strikes (do not repeat): {wrong_s}\n"
        "Give ONE new short survey answer that is not in either list above."
    )
    return query_contestant(name, MAIN_PLAY_SYSTEM, user, phase="main_or_steal")


def make_buzz_fn(*, live: bool):
    return live_buzz if live else mock_buzz


def make_answer_fn(*, live: bool):
    if live:
        return live_answer
    return None  # engine uses built-in mock main-play answers
