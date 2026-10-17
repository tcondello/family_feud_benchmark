"""Family Feud LLM benchmark — TriBonds-style multi-provider runner.

Reads survey questions from JSON, queries enabled models concurrently, grades
each reply against the survey board, and checkpoints results to CSV.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass

import nltk
import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from nltk.stem import WordNetLemmatizer

load_dotenv()

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

_lemmatizer = WordNetLemmatizer()
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@dataclass
class QueryResult:
    text: str
    latency_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class GradeResult:
    grade: str  # hit | miss | error
    matched_answer: str
    score: int


def new_session_key(prefix: str = "family-feud") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def extract_answer(text: str) -> str:
    """Normalize a free-form model reply into a short survey-style answer."""
    text = _THINK.sub("", text or "").strip()
    if "<|close|>think" in text:
        text = text.split("<|close|>think")[-1].strip()
    if not text:
        return ""
    # Keep first line; strip quotes / trailing punctuation.
    first_line = text.splitlines()[0].strip().strip("\"'`")
    first_line = re.sub(r"[.!?]+$", "", first_line).strip()
    return first_line


def normalize(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s/'&-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def lemma_phrase(value: str) -> str:
    return " ".join(_lemmatizer.lemmatize(tok, pos="n") for tok in normalize(value).split())


def answer_aliases(answer: str) -> list[str]:
    """Expand board labels like 'Judge/Justice' or 'Bat/Equipment'."""
    parts = [answer]
    for chunk in re.split(r"[/]", answer):
        chunk = chunk.strip()
        if chunk and chunk not in parts:
            parts.append(chunk)
    return parts


def grade_response(response: str, answers: list[dict]) -> GradeResult:
    if response.startswith("ERROR:") or response == "TIMEOUT":
        return GradeResult(grade="error", matched_answer="", score=0)

    candidates = [normalize(response), lemma_phrase(response)]
    best: GradeResult | None = None

    for item in answers:
        board = str(item.get("answer", "")).strip()
        score = int(item.get("score", 0))
        for alias in answer_aliases(board):
            alias_norms = {normalize(alias), lemma_phrase(alias)}
            if any(c in alias_norms or c == normalize(alias) for c in candidates):
                result = GradeResult(grade="hit", matched_answer=board, score=score)
                if best is None or result.score > best.score:
                    best = result
            # Soft match: response contains alias or alias contains response (short phrases).
            for c in candidates:
                a = normalize(alias)
                if not c or not a:
                    continue
                if (c in a or a in c) and min(len(c), len(a)) >= 3:
                    result = GradeResult(grade="hit", matched_answer=board, score=score)
                    if best is None or result.score > best.score:
                        best = result

    return best or GradeResult(grade="miss", matched_answer="", score=0)


def build_llm(model_cfg: dict, prompt_cache_affinity: bool = True):
    provider = model_cfg["provider"]
    model = model_cfg["model"]
    reasoning_effort = model_cfg.get("reasoning_effort")

    if provider == "fireworks":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError(
                f"Provider 'fireworks' is enabled for model '{model}', "
                "but FIREWORKS_API_KEY is not set in environment or .env"
            )
        base_url = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
        extra_body = {}
        default_headers = {}
        if prompt_cache_affinity:
            session_key = new_session_key()
            extra_body["prompt_cache_key"] = session_key
            default_headers["x-session-affinity"] = session_key
        if reasoning_effort:
            extra_body["reasoning_effort"] = reasoning_effort
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=64,
            extra_body=extra_body or None,
            default_headers=default_headers or None,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                f"Provider 'openai' is enabled for model '{model}', "
                "but OPENAI_API_KEY is not set in environment or .env"
            )
        kwargs = {"model": model, "api_key": api_key, "max_tokens": 64}
        extra_body = {}
        if reasoning_effort and reasoning_effort != "none":
            extra_body["reasoning_effort"] = reasoning_effort
        if not (model.startswith("gpt-6") or model.startswith("o")):
            kwargs["temperature"] = 0
        if extra_body:
            kwargs["extra_body"] = extra_body
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                f"Provider 'anthropic' is enabled for model '{model}', "
                "but ANTHROPIC_API_KEY is not set in environment or .env"
            )
        kwargs = {"model": model, "api_key": api_key, "max_tokens": 64}
        if not ("-5-5" in model or "-5.5" in model or "-5-" in model):
            kwargs["temperature"] = 0
        return ChatAnthropic(**kwargs)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                f"Provider 'google' is enabled for model '{model}', "
                "but GOOGLE_API_KEY is not set in environment or .env"
            )
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=0, max_output_tokens=64
        )

    raise ValueError(f"Unknown provider: {provider!r}")


async def query_model_async(
    llm,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    max_retries: int,
    backoff_base: float,
    label: str = "",
) -> QueryResult:
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    for attempt in range(max_retries + 1):
        try:
            start = time.perf_counter()
            response = await asyncio.wait_for(llm.ainvoke(messages), timeout=timeout)
            latency = time.perf_counter() - start

            content = response.content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "thinking":
                            continue
                        text_parts.append(part.get("text", str(part)))
                    elif hasattr(part, "text"):
                        text_parts.append(part.text)
                    else:
                        text_parts.append(str(part))
                content = " ".join(text_parts)

            meta = getattr(response, "response_metadata", {}) or {}
            usage = (
                getattr(response, "usage_metadata", {})
                or meta.get("token_usage", {})
                or meta.get("usage", {})
                or {}
            )
            prompt_tok = (
                usage.get("prompt_tokens")
                or usage.get("input_tokens")
                or usage.get("prompt_token_count")
                or 0
            )
            comp_tok = (
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or usage.get("candidates_token_count")
                or 0
            )
            return QueryResult(
                text=extract_answer(str(content)),
                latency_s=latency,
                prompt_tokens=prompt_tok,
                completion_tokens=comp_tok,
            )
        except asyncio.TimeoutError:
            if attempt < max_retries:
                wait = backoff_base * (2**attempt)
                print(
                    f"    [{label}] timeout — retrying in {wait:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(wait)
            else:
                return QueryResult(text="TIMEOUT", latency_s=float(timeout))
        except Exception as exc:  # noqa: BLE001 - surface provider errors into CSV
            if attempt < max_retries:
                wait = backoff_base * (2**attempt)
                print(
                    f"    [{label}] error ({exc}) — retrying in {wait:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(wait)
            else:
                return QueryResult(text=f"ERROR: {exc}", latency_s=0.0)
    return QueryResult(text="TIMEOUT", latency_s=float(timeout))


def col_prefix(provider: str, model: str) -> str:
    short_model = model.split("/")[-1] if "/" in model else model
    safe = re.sub(r"[^a-zA-Z0-9]", "_", short_model)
    return f"{provider}_{safe}"


def load_questions(path: str, limit: int | None) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    questions = data["questions"] if isinstance(data, dict) else data
    if limit is not None and limit > 0:
        questions = questions[:limit]
    return questions


async def main():
    with open("config.json", encoding="utf-8") as handle:
        config = json.load(handle)
    with open("prompt.json", encoding="utf-8") as handle:
        prompt_cfg = json.load(handle)

    system_prompt = prompt_cfg["system_prompt"]
    user_template = prompt_cfg["user_prompt"]

    input_file = config["questions"]["input_file"]
    output_file = config["questions"]["output_file"]
    timeout = config.get("model_timeout_seconds", 60)
    max_retries = config.get("max_retries", 3)
    backoff_base = config.get("backoff_base_seconds", 3)
    prompt_cache_affinity = config.get("prompt_cache_affinity", True)
    row_delay = config.get("row_delay_seconds", 0.25)
    limit = config.get("limit")

    questions = load_questions(input_file, limit)
    total = len(questions)

    active_models = [m for m in config["models"] if m.get("enabled", True)]
    if not active_models:
        print("No enabled models in config.json — nothing to do.")
        sys.exit(1)

    prefixes = [col_prefix(m["provider"], m["model"]) for m in active_models]
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    existing_records: dict[str, dict] = {}
    existing_cols: list[str] = []
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            existing_df = pd.read_csv(output_file)
            existing_cols = list(existing_df.columns)
            for _, row in existing_df.iterrows():
                key = row.get("question")
                if pd.notna(key):
                    existing_records[str(key).strip()] = row.to_dict()
            print(f"Loaded existing results: {len(existing_records)} rows found.")
        except Exception as exc:  # noqa: BLE001
            print(f"Could not load existing {output_file}: {exc}")

    all_fieldnames = (
        list(existing_cols)
        if existing_cols
        else ["question", "top_answer", "top_score", "board_answers"]
    )
    for prefix in prefixes:
        for suffix in ("_response", "_grade", "_matched", "_score", "_latency_s"):
            col = f"{prefix}{suffix}"
            if col not in all_fieldnames:
                all_fieldnames.append(col)

    llms = {}
    for model_cfg in active_models:
        short_id = model_cfg["model"].split("/")[-1]
        print(f"Loading model: {model_cfg['provider']}/{short_id}")
        llms[(model_cfg["provider"], model_cfg["model"])] = build_llm(
            model_cfg, prompt_cache_affinity=prompt_cache_affinity
        )

    new_count = 0
    results_rows: list[dict] = []

    for index, item in enumerate(questions):
        question = str(item["question"]).strip()
        answers = item.get("answers") or []
        ranked = sorted(answers, key=lambda a: int(a.get("score", 0)), reverse=True)
        top_answer = ranked[0]["answer"] if ranked else ""
        top_score = int(ranked[0]["score"]) if ranked else 0
        board_answers = " | ".join(
            f"{a['answer']} ({a['score']})" for a in ranked
        )

        existing_row = existing_records.get(question, {})
        result_row = dict(existing_row)
        result_row["question"] = question
        result_row["top_answer"] = top_answer
        result_row["top_score"] = top_score
        result_row["board_answers"] = board_answers

        models_to_query = []
        for model_cfg in active_models:
            prefix = col_prefix(model_cfg["provider"], model_cfg["model"])
            resp_val = existing_row.get(f"{prefix}_response")
            grade_val = existing_row.get(f"{prefix}_grade")
            is_done = (
                pd.notna(resp_val)
                and str(resp_val).strip() != ""
                and not str(resp_val).startswith("ERROR:")
                and pd.notna(grade_val)
                and str(grade_val) in {"hit", "miss"}
            )
            if is_done:
                result_row[f"{prefix}_response"] = resp_val
                result_row[f"{prefix}_grade"] = grade_val
                result_row[f"{prefix}_matched"] = existing_row.get(f"{prefix}_matched")
                result_row[f"{prefix}_score"] = existing_row.get(f"{prefix}_score")
                result_row[f"{prefix}_latency_s"] = existing_row.get(
                    f"{prefix}_latency_s"
                )
            else:
                models_to_query.append(model_cfg)

        if not models_to_query:
            results_rows.append(result_row)
            continue

        user_prompt = user_template.format(question=question)
        to_query_names = ", ".join(m["model"].split("/")[-1] for m in models_to_query)
        print(
            f"\n[{index + 1}/{total}] {question}  →  top: {top_answer} "
            f"(querying: {to_query_names})"
        )

        tasks = [
            query_model_async(
                llms[(m["provider"], m["model"])],
                system_prompt,
                user_prompt,
                timeout,
                max_retries,
                backoff_base,
                label=f"{m['provider']}/{m['model'].split('/')[-1]}",
            )
            for m in models_to_query
        ]
        responses = await asyncio.gather(*tasks)

        for model_cfg, res in zip(models_to_query, responses):
            prefix = col_prefix(model_cfg["provider"], model_cfg["model"])
            graded = grade_response(res.text, answers)
            result_row[f"{prefix}_response"] = res.text
            result_row[f"{prefix}_grade"] = graded.grade
            result_row[f"{prefix}_matched"] = graded.matched_answer
            result_row[f"{prefix}_score"] = graded.score
            result_row[f"{prefix}_latency_s"] = f"{res.latency_s:.2f}"
            short_id = model_cfg["model"].split("/")[-1]
            print(
                f"  {model_cfg['provider']}/{short_id}: {res.text!r} → "
                f"{graded.grade} matched={graded.matched_answer!r} "
                f"score={graded.score} ({res.latency_s:.2f}s)"
            )

        results_rows.append(result_row)
        new_count += 1

        checkpoint_df = pd.DataFrame(results_rows)
        for col in all_fieldnames:
            if col not in checkpoint_df.columns:
                checkpoint_df[col] = None
        checkpoint_df[all_fieldnames].to_csv(output_file, index=False)

        if row_delay > 0:
            await asyncio.sleep(row_delay)

    final_df = pd.DataFrame(results_rows)
    for col in all_fieldnames:
        if col not in final_df.columns:
            final_df[col] = None
    final_df[all_fieldnames].to_csv(output_file, index=False)

    print(f"\n{'=' * 75}")
    print(f"{'RESULTS SUMMARY':^75}")
    print(f"{'=' * 75}")
    print(f"New / updated rows this run: {new_count}")
    print(f"{'-' * 75}")
    print(f"{'Model':<42} | {'Hit rate':<14} | {'Avg board pts':<14} | {'Avg Latency'}")
    print(f"{'-' * 75}")

    results_df = pd.read_csv(output_file)
    count = len(results_df)
    grade_cols = [c for c in results_df.columns if c.endswith("_grade")]
    for grade_col in grade_cols:
        prefix = grade_col[:-6]
        lat_col = f"{prefix}_latency_s"
        score_col = f"{prefix}_score"
        hits = (results_df[grade_col] == "hit").sum()
        pct = hits / count * 100 if count else 0
        avg_score = (
            pd.to_numeric(results_df[score_col], errors="coerce").mean()
            if score_col in results_df.columns
            else None
        )
        lat_mean = (
            pd.to_numeric(results_df[lat_col], errors="coerce").mean()
            if lat_col in results_df.columns
            else None
        )
        score_str = f"{avg_score:.1f}" if pd.notna(avg_score) else "N/A"
        lat_str = f"{lat_mean:.2f}s" if pd.notna(lat_mean) else "N/A"
        print(f"{prefix:<42} | {hits}/{count} ({pct:5.1f}%) | {score_str:<14} | {lat_str}")

    print(f"{'=' * 75}")
    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
