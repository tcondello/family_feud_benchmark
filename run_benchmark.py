#!/usr/bin/env python3
"""Run the Family Feud benchmark across the latest models for each configured provider."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "I am going to ask you a series of questions. When you answer I want you to "
    "say just the answer. For example Question: name something with 4 wheels "
    "Response: car"
)

QUESTION_PATHS = (
    "questions/all_questions.json",
    "questions/question_list.json",
    "question_list.json",
)

CHECKPOINT_EVERY = 25


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    label: str

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.label}"


# Latest working chat models verified against the injected runtime secrets.
LATEST_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("openai", "gpt-5.5", "gpt-5.5"),
    ModelSpec("anthropic", "claude-opus-4-6", "claude-opus-4-6"),
    ModelSpec("google", "gemini-pro-latest", "gemini-pro-latest"),
    ModelSpec(
        "fireworks",
        "accounts/fireworks/models/qwen3p8-max",
        "qwen3p8-max",
    ),
    ModelSpec(
        "fireworks",
        "accounts/fireworks/models/ember-1",
        "ember-1",
    ),
    ModelSpec(
        "fireworks",
        "accounts/fireworks/models/kimi-k3",
        "kimi-k3",
    ),
)

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
}

_CLIENTS: dict[str, Any] = {}


def load_questions(path: str | None) -> tuple[list[dict], str]:
    candidates = (path,) if path else QUESTION_PATHS
    for candidate in candidates:
        if not candidate:
            continue
        try:
            with open(candidate, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            continue
        questions = data.get("questions") if isinstance(data, dict) else data
        if not isinstance(questions, list):
            raise ValueError(f"Unexpected question format in {candidate}")
        return questions, candidate
    raise FileNotFoundError(f"No question file found in {candidates}")


def clean_answer(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text.strip().strip('"').strip("'")
    # Prefer the last non-empty line for chatty / reasoning-style models.
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if lines:
        cleaned = lines[-1]
    cleaned = re.sub(r"^(answer|response)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = cleaned.strip().strip('"').strip("'")
    # Drop trailing period for short survey answers.
    if cleaned.endswith(".") and cleaned.count(" ") <= 4:
        cleaned = cleaned[:-1]
    return cleaned


def extract_message_answer(content: str | None, reasoning: str | None = None) -> str:
    """Prefer visible content; fall back to short quoted spans in reasoning traces."""
    direct = clean_answer(content)
    if direct and len(direct.split()) <= 8:
        return direct
    if direct:
        return direct
    reasoning = reasoning or ""
    quotes = re.findall(r'"([^"\n]{1,40})"', reasoning)
    if quotes:
        return clean_answer(quotes[-1])
    return ""


def get_openai_client():
    if "openai" not in _CLIENTS:
        from openai import OpenAI

        _CLIENTS["openai"] = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _CLIENTS["openai"]


def get_anthropic_client():
    if "anthropic" not in _CLIENTS:
        import anthropic

        _CLIENTS["anthropic"] = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
    return _CLIENTS["anthropic"]


def get_google_client():
    if "google" not in _CLIENTS:
        from google import genai

        _CLIENTS["google"] = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _CLIENTS["google"]


def get_fireworks_client():
    if "fireworks" not in _CLIENTS:
        from openai import OpenAI

        _CLIENTS["fireworks"] = OpenAI(
            api_key=os.environ["FIREWORKS_API_KEY"],
            base_url="https://api.fireworks.ai/inference/v1",
        )
    return _CLIENTS["fireworks"]


def with_retries(fn: Callable[[], str], *, attempts: int = 5) -> str:
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            name = type(exc).__name__
            retryable = name in {
                "RateLimitError",
                "APIConnectionError",
                "APITimeoutError",
                "InternalServerError",
                "ServiceUnavailableError",
                "ResourceExhausted",
                "TooManyRequests",
                "ClientError",
                "ServerError",
            } or "429" in str(exc) or "500" in str(exc) or "503" in str(exc)
            if not retryable or attempt == attempts:
                raise
            print(f"retry {attempt}/{attempts} after {name}: sleeping {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
    raise RuntimeError(f"unreachable retry loop: {last_exc}")


def call_openai(model: str, question: str) -> str:
    client = get_openai_client()

    def _call() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_completion_tokens=128,
        )
        return clean_answer(response.choices[0].message.content)

    return with_retries(_call)


def call_anthropic(model: str, question: str) -> str:
    client = get_anthropic_client()

    def _call() -> str:
        response = client.messages.create(
            model=model,
            max_tokens=64,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        return clean_answer(text)

    return with_retries(_call)


def call_google(model: str, question: str) -> str:
    from google.genai import types

    client = get_google_client()

    def _call() -> str:
        # gemini-pro-latest uses mandatory thinking tokens; keep headroom so the
        # visible answer is not truncated to an empty / partial string.
        response = client.models.generate_content(
            model=model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1024,
            ),
        )
        return clean_answer(getattr(response, "text", None))

    return with_retries(_call)


def call_fireworks(model: str, question: str) -> str:
    client = get_fireworks_client()

    def _call() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_tokens=512,
            temperature=0,
        )
        message = response.choices[0].message
        return extract_message_answer(
            message.content,
            getattr(message, "reasoning_content", None),
        )

    return with_retries(_call)


CALLERS: dict[str, Callable[[str, str], str]] = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "google": call_google,
    "fireworks": call_fireworks,
}


def available_models(selected: set[str] | None = None) -> list[ModelSpec]:
    models: list[ModelSpec] = []
    for spec in LATEST_MODELS:
        if selected and spec.provider not in selected and spec.label not in selected:
            continue
        env_name = PROVIDER_ENV[spec.provider]
        if not os.getenv(env_name):
            print(f"skip {spec.key}: missing {env_name}")
            continue
        models.append(spec)
    return models


def load_existing_results(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def write_results(path: Path, results: dict[str, list[dict[str, str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(results, indent=4) + "\n", encoding="utf-8")
    tmp.replace(path)


def run_model(
    spec: ModelSpec,
    questions: list[dict],
    *,
    sleep_s: float,
    existing: list[dict[str, str]] | None,
    on_checkpoint: Callable[[list[dict[str, str]]], None] | None = None,
) -> list[dict[str, str]]:
    caller = CALLERS[spec.provider]
    responses = list(existing or [])
    start_index = len(responses)
    if start_index:
        print(f"[{spec.key}] resuming at {start_index + 1}/{len(questions)}")

    for index, item in enumerate(questions, start=1):
        if index <= start_index:
            continue
        question = item.get("question")
        if not question:
            continue
        try:
            answer = caller(spec.model, question)
        except Exception as exc:  # noqa: BLE001 - keep the run going
            answer = f"ERROR: {type(exc).__name__}: {exc}"
        print(f"[{spec.key} {index}/{len(questions)}] {question} -> {answer}", flush=True)
        responses.append({question: answer})
        if on_checkpoint and (index % CHECKPOINT_EVERY == 0 or index == len(questions)):
            on_checkpoint(responses)
        if sleep_s > 0:
            time.sleep(sleep_s)
    return responses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        help="Question JSON path (default: prefer questions/all_questions.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N questions",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=None,
        help="Subset of providers or model labels to run",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional delay between requests (seconds)",
    )
    parser.add_argument(
        "--output",
        default="responses/multi_provider_response_list.json",
        help="Where to write the combined response JSON",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing --output checkpoint if present",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print the configured latest models and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = set(args.providers) if args.providers else None
    models = available_models(selected)

    if args.list_models:
        for spec in models:
            print(f"{spec.key} ({PROVIDER_ENV[spec.provider]})")
        return

    if not models:
        raise SystemExit("No provider secrets available for the requested models.")

    questions, source = load_questions(args.questions)
    if args.limit is not None:
        questions = questions[: args.limit]

    output_path = Path(args.output)
    results = load_existing_results(output_path) if args.resume else {}

    print(f"questions={len(questions)} source={source}", flush=True)
    print("models=" + ", ".join(spec.key for spec in models), flush=True)
    if args.resume and results:
        print(
            "resume counts="
            + ", ".join(f"{k}:{len(v)}" for k, v in results.items()),
            flush=True,
        )

    for spec in models:
        existing = results.get(spec.key) if args.resume else None
        if existing and len(existing) >= len(questions):
            print(f"[{spec.key}] already complete ({len(existing)} answers)", flush=True)
            continue

        def checkpoint(responses: list[dict[str, str]], key: str = spec.key) -> None:
            results[key] = responses
            write_results(output_path, results)
            print(f"checkpoint {key}: {len(responses)}/{len(questions)} -> {output_path}", flush=True)

        results[spec.key] = run_model(
            spec,
            questions,
            sleep_s=args.sleep,
            existing=existing,
            on_checkpoint=checkpoint,
        )
        write_results(output_path, results)
        print(f"finished {spec.key}: {len(results[spec.key])} answers", flush=True)

    write_results(output_path, results)
    print(f"wrote {output_path}", flush=True)


if __name__ == "__main__":
    main()
