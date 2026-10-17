# Family Feud LLM Benchmark

Benchmarks LLMs on Family Feud survey questions: ask for a top answer, grade it
against the survey board, and score survey points.

The runner follows the same pattern as
[TriBonds](https://github.com/tcondello/TriBonds): `config.json` models,
`.env` API keys, async multi-provider queries, CSV checkpoint/resume.

## Question sources

| Source | Path |
| --- | --- |
| Buzzfeed | `questions/buzzfeed/` |
| ProtoQA | `questions/protoqa/` |
| TV transcriptions (mstiescott) | `questions/mstiescott/` |
| Combined | `questions/all_questions.json` |

See [`questions/README.md`](questions/README.md) for refresh commands.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or pip).

```bash
uv sync
# or: pip install -r requirements.txt

cp .env.example .env
# Add OPENAI_API_KEY and FIREWORKS_API_KEY
```

### Cloud Agents

Add secrets named `OPENAI_API_KEY` and `FIREWORKS_API_KEY` in the environment
settings, then **start a new agent** so they are injected. Existing sessions do
not pick up secrets added after boot.

## Configuration

### Models — `config.json`

Toggle providers/models with `"enabled"`. `limit` caps how many questions run
(use a small number for smoke tests; set `null` for the full file).

```json
{
  "models": [
    { "provider": "openai", "model": "gpt-4o-mini", "enabled": true },
    { "provider": "fireworks", "model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "enabled": true }
  ],
  "limit": 10,
  "questions": {
    "input_file": "questions/buzzfeed/question_list.json",
    "output_file": "responses/results.csv"
  }
}
```

### Prompt — `prompt.json`

Edit the system/user templates used for every survey question.

## Running

```bash
uv run main.py
# or: python main.py
```

Interrupted runs resume from `responses/results.csv` (completed model columns
are skipped).

Legacy single-model script: `python openAI_family_feud.py`

## Supported providers

| Provider | Env variable |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `fireworks` | `FIREWORKS_API_KEY` (+ optional `FIREWORKS_BASE_URL`) |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
