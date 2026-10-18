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
    MAX_TOKENS_BY_PROVIDER,
    PROVIDER_ENV,
    REPAIR_SYSTEM,
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


def _max_tokens(provider: str) -> int:
    return int(MAX_TOKENS_BY_PROVIDER.get(provider, 64))


def _finish_reason(response: Any) -> str | None:
    try:
        data = to_jsonable(response)
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices and isinstance(choices[0], dict):
                return choices[0].get("finish_reason") or choices[0].get("finishReason")
            # Anthropic / Gemini shapes
            return data.get("stop_reason") or data.get("finish_reason")
    except Exception:  # noqa: BLE001
        return None
    return None


def _looks_truncated(text: str, finish_reason: str | None) -> bool:
    if finish_reason in {"length", "max_tokens", "MAX_TOKENS"}:
        return True
    text = (text or "").rstrip()
    if not text:
        return False
    # Mid-list / mid-sentence cutoffs common when Fireworks CoT hits the cap.
    if text.endswith((",", ";", ":", "-", "—")):
        return True
    if text.lower().endswith((" the", " a", " an", " and", " or", " with", " for")):
        return True
    return False


def _call_openai(model: str, system: str, user: str) -> ProviderResult:
    from openai import OpenAI

    max_tok = _max_tokens("openai")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    request = {
        "provider": "openai",
        "endpoint": "chat.completions.create",
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": max_tok,
    }
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=request["messages"],
        max_completion_tokens=max_tok,
    )
    latency = time.perf_counter() - start
    text = (response.choices[0].message.content or "").strip()
    return ProviderResult(text=text, latency_s=latency, request=request, response=response)


def _call_anthropic(model: str, system: str, user: str) -> ProviderResult:
    import anthropic

    max_tok = _max_tokens("anthropic")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    request = {
        "provider": "anthropic",
        "endpoint": "messages.create",
        "model": model,
        "max_tokens": max_tok,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=max_tok,
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

    max_tok = _max_tokens("google")
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    request = {
        "provider": "google",
        "endpoint": "models.generate_content",
        "model": model,
        "contents": user,
        "config": {
            "system_instruction": system,
            "max_output_tokens": max_tok,
        },
    }

    def once() -> ProviderResult:
        start = time.perf_counter()
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tok,
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

    max_tok = _max_tokens("fireworks")
    client = OpenAI(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url="https://api.fireworks.ai/inference/v1",
    )
    # Higher budget than OpenAI/Anthropic: Ember/Qwen often write CoT into content.
    # Still capped; `_clean` + repair retry strip to a short survey phrase.
    request = {
        "provider": "fireworks",
        "endpoint": "chat.completions.create",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tok,
        "temperature": 0,
    }
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=request["messages"],
        max_tokens=max_tok,
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


_META_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "with",
    "for",
    "most",
    "common",
    "answer",
    "answers",
    "rhymes",
    "rhyme",
    "user",
    "wants",
    "need",
    "needs",
    "already",
    "revealed",
    "family",
    "feud",
    "survey",
    "short",
    "words",
    "word",
    "final",
    "choose",
    "only",
}


def _clean(text: str, *, forbidden: set[str] | None = None) -> str:
    """Collapse model output to a short survey phrase.

    Reasoning models (esp. Ember/Qwen on Fireworks) often return a monologue
    that *mentions* candidates. Prefer the last usable candidate that is not
    in the forbidden set (revealed / wrong / question echo).
    """
    import re

    forbidden_n = {
        re.sub(r"\s+", " ", f.lower().strip()) for f in (forbidden or set()) if f
    }

    def ok(candidate: str) -> bool:
        c = candidate.strip().strip('"').strip("'").strip(",")
        if not c or len(c.split()) > 4 or len(c) > 40:
            return False
        key = re.sub(r"\s+", " ", c.lower())
        if key in forbidden_n:
            return False
        toks = re.findall(r"[a-z0-9]+", key)
        if not toks:
            return False
        # Reject meta / instruction fragments ("Rhymes with election").
        if any(t in _META_WORDS for t in toks):
            return False
        return True

    text = (text or "").strip().strip('"').strip("'")
    if not text:
        return ""

    # Priority buckets: explicit finals > comma-list items > quotes > other.
    priority: list[str] = []
    secondary: list[str] = []

    for pattern in (
        r"(?is)\bfinal(?:\s+answer)?\s*:\s*([^\n.]+)",
        r"(?is)\b(?:your\s+)?(?:one\s+)?(?:new\s+)?answer\s*:\s*([^\n.]+)",
        r"(?is)\bchoose\s*[\"']?([A-Za-z][^\"'\n.]{0,40})",
    ):
        for match in re.finditer(pattern, text):
            priority.append(match.group(1).strip())

    # Comma/semicolon lists after a colon (Ember CoT rhyme lists).
    for match in re.finditer(r":\s*([A-Za-z][A-Za-z ,/\-]{2,240})", text):
        for part in re.split(r"[,;/]", match.group(1)):
            priority.append(part.strip())

    secondary.extend(re.findall(r"[\"']([^\"']{1,40})[\"']", text))
    secondary.extend(
        re.findall(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,3})\b", text)
    )
    lines = [ln.strip().strip('"').strip("'") for ln in text.splitlines() if ln.strip()]
    if lines:
        secondary.append(lines[-1])

    for cand in reversed(priority + secondary):
        cand = re.sub(r"(?i)\s*(ensure only|only answer words|final).*$", "", cand).strip()
        if cand.endswith(".") and len(cand.split()) <= 5:
            cand = cand[:-1]
        if ok(cand):
            return cand

    if ok(text):
        return text if not text.endswith(".") else text[:-1]
    return ""


def _is_question_echo(answer: str, question: str) -> bool:
    """True when the answer is just words lifted from the question (e.g. election)."""
    import re

    q = {t for t in re.findall(r"[a-z0-9]+", question.lower()) if len(t) > 2}
    a = [t for t in re.findall(r"[a-z0-9]+", answer.lower()) if len(t) > 2]
    return bool(a) and all(tok in q for tok in a)


def _needs_repair(
    cleaned: str,
    raw: str,
    *,
    finish_reason: str | None,
    forbidden: set[str],
    question: str,
) -> str | None:
    """Return repair reason or None if the cleaned answer is usable."""
    if _looks_truncated(raw, finish_reason):
        return "truncated"
    if not cleaned:
        return "empty_after_clean"
    if _is_question_echo(cleaned, question):
        return "question_echo"
    key = cleaned.lower().strip()
    if key in {f.lower().strip() for f in forbidden if f}:
        return "forbidden_repeat"
    if len(cleaned.split()) > 5:
        return "too_long"
    return None


def query_contestant(
    name: str,
    system: str,
    user: str,
    *,
    phase: str = "unknown",
    question: str = "",
    forbidden: list[str] | None = None,
) -> tuple[str, float]:
    provider, model = CONTESTANT_MODELS[name]
    if not os.getenv(PROVIDER_ENV[provider]):
        raise RuntimeError(f"Missing {PROVIDER_ENV[provider]} for {name}")

    forbid = set(forbidden or [])
    total_latency = 0.0
    last_cleaned = ""
    attempts = [
        (system, user, "primary"),
        (
            REPAIR_SYSTEM,
            (
                f"{user}\n\n"
                f"Forbidden (do not say these): "
                f"{', '.join(sorted(forbid)) if forbid else '(none)'}.\n"
                "Reply with ONLY one new 1-4 word survey answer."
            ),
            "repair",
        ),
    ]

    for sys_prompt, user_prompt, attempt_name in attempts:
        request_preview = {
            "provider": provider,
            "model": model,
            "system": sys_prompt,
            "user": user_prompt,
            "max_tokens": _max_tokens(provider),
            "attempt": attempt_name,
        }
        try:
            result = _CALLERS[provider](model, sys_prompt, user_prompt)
        except Exception as exc:  # noqa: BLE001
            log_event(
                "model_error",
                phase=phase,
                contestant=name,
                provider=provider,
                model=model,
                system=sys_prompt,
                user=user_prompt,
                request=request_preview,
                attempt=attempt_name,
                error=f"{type(exc).__name__}: {exc}",
                error_body=to_jsonable(
                    getattr(exc, "body", None)
                    or getattr(exc, "response", None)
                    or str(exc)
                ),
            )
            raise

        total_latency += result.latency_s
        finish = _finish_reason(result.response)
        cleaned = _clean(result.text, forbidden=forbid)
        last_cleaned = cleaned
        reason = _needs_repair(
            cleaned,
            result.text,
            finish_reason=finish,
            forbidden=forbid,
            question=question or user_prompt,
        )
        log_event(
            "model_call",
            phase=phase,
            contestant=name,
            provider=provider,
            model=model,
            system=sys_prompt,
            user=user_prompt,
            request=to_jsonable(result.request),
            response=to_jsonable(result.response),
            raw=result.text,
            cleaned=cleaned,
            finish_reason=finish,
            attempt=attempt_name,
            repair_reason=reason,
            latency_s=round(result.latency_s, 4),
            max_tokens=_max_tokens(provider),
        )
        if reason is None:
            return cleaned, total_latency
        # One repair attempt only.
        if attempt_name == "repair":
            break
        if cleaned:
            forbid.add(cleaned)

    return last_cleaned, total_latency


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
                name,
                FACE_OFF_SYSTEM,
                question,
                phase="face_off",
                question=question,
                forbidden=[],
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
    forbidden = list(dict.fromkeys([*revealed, *wrong_guesses]))
    revealed_s = ", ".join(revealed) if revealed else "(none yet)"
    wrong_s = ", ".join(wrong_guesses) if wrong_guesses else "(none yet)"
    user = (
        f"Survey question: {question}\n"
        f"Already revealed on the board (do not repeat): {revealed_s}\n"
        f"Already tried and WRONG / strikes (do not repeat): {wrong_s}\n"
        "Give ONE new short survey answer that is not in either list above."
    )
    return query_contestant(
        name,
        MAIN_PLAY_SYSTEM,
        user,
        phase="main_or_steal",
        question=question,
        forbidden=forbidden,
    )


def make_buzz_fn(*, live: bool):
    return live_buzz if live else mock_buzz


def make_answer_fn(*, live: bool):
    if live:
        return live_answer
    return None  # engine uses built-in mock main-play answers
