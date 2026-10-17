#!/usr/bin/env python3
"""Run the Family Feud benchmark across providers — TriBonds-style concurrency.

All enabled models run in parallel (one worker pool per model). Within each
model, multiple questions can be in flight at once. Results checkpoint to JSON
and are resume-safe.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
_CLIENT_LOCK = threading.Lock()
_RESULTS_LOCK = threading.Lock()


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
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if lines:
        cleaned = lines[-1]
    cleaned = re.sub(r"^(answer|response)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = cleaned.strip().strip('"').strip("'")
    if cleaned.endswith(".") and cleaned.count(" ") <= 4:
        cleaned = cleaned[:-1]
    return cleaned


def extract_message_answer(content: str | None, reasoning: str | None = None) -> str:
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


def _cached_client(name: str, factory: Callable[[], Any]) -> Any:
    with _CLIENT_LOCK:
        if name not in _CLIENTS:
            _CLIENTS[name] = factory()
        return _CLIENTS[name]


def get_openai_client():
    def factory():
        from openai import OpenAI

        return OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    return _cached_client("openai", factory)


def get_anthropic_client():
    def factory():
        import anthropic

        return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    return _cached_client("anthropic", factory)


def get_google_client():
    def factory():
        from google import genai

        return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    return _cached_client("google", factory)


def get_fireworks_client():
    def factory():
        from openai import OpenAI

        return OpenAI(
            api_key=os.environ["FIREWORKS_API_KEY"],
            base_url="https://api.fireworks.ai/inference/v1",
        )

    return _cached_client("fireworks", factory)


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
            print(
                f"retry {attempt}/{attempts} after {name}: sleeping {delay:.1f}s",
                flush=True,
            )
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
            max_completion_tokens=256,
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


def run_model_parallel(
    spec: ModelSpec,
    questions: list[dict],
    *,
    sleep_s: float,
    existing: list[dict[str, str]] | None,
    workers: int,
    results: dict[str, list[dict[str, str]]],
    output_path: Path,
) -> list[dict[str, str]]:
    """Fill answers for one model with in-flight concurrency (TriBonds-style)."""
    caller = CALLERS[spec.provider]
    start_index = len(existing or [])
    total = len(questions)
    # Pre-size slot list so out-of-order worker completions stay ordered.
    slots: list[dict[str, str] | None] = [None] * total
    for i, item in enumerate(existing or []):
        slots[i] = item

    pending_indices = list(range(start_index, total))
    if start_index:
        print(
            f"[{spec.key}] resuming at {start_index + 1}/{total} "
            f"(workers={workers})",
            flush=True,
        )
    else:
        print(f"[{spec.key}] starting 1/{total} (workers={workers})", flush=True)

    if not pending_indices:
        print(f"[{spec.key}] already complete ({total} answers)", flush=True)
        return [s for s in slots if s is not None]

    done_since_checkpoint = 0
    completed = start_index
    lock = threading.Lock()

    def answer_one(index: int) -> tuple[int, dict[str, str]]:
        item = questions[index]
        question = item.get("question") or ""
        if not question:
            return index, {"": ""}
        try:
            answer = caller(spec.model, question)
        except Exception as exc:  # noqa: BLE001
            answer = f"ERROR: {type(exc).__name__}: {exc}"
        if sleep_s > 0:
            time.sleep(sleep_s)
        return index, {question: answer}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(answer_one, idx): idx for idx in pending_indices}
        for future in as_completed(futures):
            index, payload = future.result()
            question, answer = next(iter(payload.items()))
            with lock:
                slots[index] = payload
                completed += 1
                done_since_checkpoint += 1
                print(
                    f"[{spec.key} {completed}/{total}] {question} -> {answer}",
                    flush=True,
                )
                if (
                    done_since_checkpoint >= CHECKPOINT_EVERY
                    or completed == total
                ):
                    snapshot = [s for s in slots if s is not None]
                    # Only checkpoint contiguous prefix so resume stays correct.
                    contiguous: list[dict[str, str]] = []
                    for slot in slots:
                        if slot is None:
                            break
                        contiguous.append(slot)
                    with _RESULTS_LOCK:
                        results[spec.key] = contiguous
                        write_results(output_path, results)
                    print(
                        f"checkpoint {spec.key}: {len(contiguous)}/{total} "
                        f"-> {output_path}",
                        flush=True,
                    )
                    done_since_checkpoint = 0

    contiguous = []
    for slot in slots:
        if slot is None:
            break
        contiguous.append(slot)
    with _RESULTS_LOCK:
        results[spec.key] = contiguous
        write_results(output_path, results)
    print(f"finished {spec.key}: {len(contiguous)} answers", flush=True)
    return contiguous


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
        help="Optional delay after each request (seconds)",
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
        "--workers",
        type=int,
        default=8,
        help="In-flight requests per model (default: 8)",
    )
    parser.add_argument(
        "--sequential-models",
        action="store_true",
        help="Run models one after another instead of all providers in parallel",
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
    print(
        f"concurrency: models_parallel={not args.sequential_models} "
        f"workers_per_model={args.workers}",
        flush=True,
    )
    if args.resume and results:
        print(
            "resume counts="
            + ", ".join(f"{k}:{len(v)}" for k, v in sorted(results.items())),
            flush=True,
        )

    def run_one(spec: ModelSpec) -> None:
        existing = results.get(spec.key) if args.resume else None
        if existing and len(existing) >= len(questions):
            print(
                f"[{spec.key}] already complete ({len(existing)} answers)",
                flush=True,
            )
            return
        run_model_parallel(
            spec,
            questions,
            sleep_s=args.sleep,
            existing=existing,
            workers=args.workers,
            results=results,
            output_path=output_path,
        )

    if args.sequential_models:
        for spec in models:
            run_one(spec)
    else:
        # TriBonds pattern: hit every provider at once.
        with ThreadPoolExecutor(max_workers=len(models)) as pool:
            list(pool.map(run_one, models))

    write_results(output_path, results)
    print(f"wrote {output_path}", flush=True)
    print(
        "final counts="
        + ", ".join(f"{k}:{len(v)}" for k, v in sorted(results.items())),
        flush=True,
    )


if __name__ == "__main__":
    main()
