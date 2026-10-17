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
from typing import Callable

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
)

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
}


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


def call_openai(model: str, question: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        max_completion_tokens=128,
    )
    return clean_answer(response.choices[0].message.content)


def call_anthropic(model: str, question: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=64,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text"))
    return clean_answer(text)


def call_google(model: str, question: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
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


def call_fireworks(model: str, question: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url="https://api.fireworks.ai/inference/v1",
    )
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


def run_model(
    spec: ModelSpec,
    questions: list[dict],
    *,
    sleep_s: float,
) -> list[dict[str, str]]:
    caller = CALLERS[spec.provider]
    responses: list[dict[str, str]] = []
    for index, item in enumerate(questions, start=1):
        question = item.get("question")
        if not question:
            continue
        try:
            answer = caller(spec.model, question)
        except Exception as exc:  # noqa: BLE001 - keep the run going
            answer = f"ERROR: {type(exc).__name__}: {exc}"
        print(f"[{spec.key} {index}/{len(questions)}] {question} -> {answer}")
        responses.append({question: answer})
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

    print(f"questions={len(questions)} source={source}")
    print("models=" + ", ".join(spec.key for spec in models))

    results: dict[str, list[dict[str, str]]] = {}
    for spec in models:
        results[spec.key] = run_model(spec, questions, sleep_s=args.sleep)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=4) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
