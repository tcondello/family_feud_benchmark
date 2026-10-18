# Family Feud LLM Benchmark

Benchmark LLMs against Family Feud survey questions: ask a model for a top
answer, then score it against the survey board.

## Question sources

The original dataset was a single BuzzFeed list. The repo now also includes:

1. **BuzzFeed** – [115 Family Feud Questions To Liven Up Game Night](https://www.buzzfeed.com/kellyrissman/family-feud-questions)
2. **TV episode transcriptions** – [mstiescott neocities](https://mstiescott.neocities.org/) boards copied from broadcast episodes
3. **ProtoQA** – [iesl/protoqa-data](https://github.com/iesl/protoqa-data), the research “Family Feud” QA dataset

See [`questions/README.md`](questions/README.md) for schema details and refresh
commands. Use `questions/all_questions.json` for the combined set, or a file
under `questions/buzzfeed/`, `questions/mstiescott/`, or `questions/protoqa/`
for one source.

## Quick start

```bash
pip install -r requirements.txt
# set OPENAI_API_KEY in .env
python openAI_family_feud.py
```

<<<<<<< HEAD
`openAI_family_feud.py` currently reads `question_list.json` from the working
directory; point it at `questions/all_questions.json` (or copy/symlink) to use
the expanded set.
=======
### Latest models used

| Provider   | Model                                      | Secret               |
|------------|--------------------------------------------|----------------------|
| OpenAI     | `gpt-5.5`                                  | `OPENAI_API_KEY`     |
| Anthropic  | `claude-opus-4-6`                          | `ANTHROPIC_API_KEY`  |
| Google     | `gemini-flash-latest`                        | `GOOGLE_API_KEY`     |
| Fireworks  | `accounts/fireworks/models/qwen3p8-max`    | `FIREWORKS_API_KEY`  |
| Fireworks  | `accounts/fireworks/models/ember-1`        | `FIREWORKS_API_KEY`  |
| Fireworks  | `accounts/fireworks/models/kimi-k3`        | `FIREWORKS_API_KEY`  |

```bash
python run_benchmark.py --list-models
python run_benchmark.py --providers openai anthropic --limit 10

# Full combined set — TriBonds-style concurrency:
# all providers in parallel + multiple in-flight requests per model
python run_benchmark.py \
  --questions questions/all_questions.json \
  --output responses/multi_provider_all_questions.json \
  --resume \
  --workers 8
```

Wall-clock time tracks the slowest provider, not the sum of every model.
Use `--sequential-models` only for the old one-at-a-time behavior.

Re-query blank/empty answers in place:

```bash
python run_benchmark.py \
  --questions questions/all_questions.json \
  --output responses/multi_provider_all_questions.json \
  --refill-blanks \
  --providers gpt-5.5 qwen3p8-max \
  --workers 8
```

Instrumented answers (latency, tokens, estimated USD from `pricing.json`) are
stored on new results. Compare misses across models:

```bash
python score_benchmark.py \
  --responses responses/multi_provider_all_questions.json \
  --questions questions/all_questions.json \
  --output responses/multi_provider_all_scores.json

python compare_misses.py \
  --responses responses/multi_provider_all_questions.json \
  --questions questions/all_questions.json \
  --only-disagreements \
  --output-json responses/miss_comparison.json \
  --output-csv responses/miss_comparison.csv
```

### Host TUI (Phase 1)

Step through a Family Feud round as host. Pick a question, Space to mock
buzz-in, then Space again to award control and reveal the board. No live
API calls yet — pacing only.

```bash
pip install -r requirements.txt
python -m game
# or: python -m game --questions questions/test_questions.json
```

| Key | Action |
|-----|--------|
| `Enter` | Select highlighted question |
| `Space` | Advance (buzz → control → reveal) |
| `r` | Host-reveal next answer (no points) |
| `/` | Focus question filter |
| `n` | Back to question picker |
| `q` | Quit |

### Interactive hit/miss explorer

Browse questions all models missed, hard disagreements, solo hits, and
per-model unique misses:

```bash
python build_question_explorer.py
# opens responses/question_explorer.html (also copied to artifacts)
```

Each question shows its **id** (e.g. `ms-s20-0464`) and **source**
(`buzzfeed` / `mstiescott` / `protoqa`). Filter by source — `mstiescott` is
real TV board wording (often spicy Steve Harvey-era answers like “Pop Some
Spawn”); `protoqa` is research fan/crowd surveys; `buzzfeed` is a compiled
list. Soft-match follows Family Feud-style rules (plurals, compounds like
eye patch ↔ Eyepatches, synonyms like bike ↔ bicycle).

`openAI_family_feud.py` remains as a single-provider OpenAI helper (now on
`gpt-5.5`). Prefer `run_benchmark.py` for multi-provider runs.
>>>>>>> f2a413b (Add Phase 1 Family Feud host TUI with mock buzz-in)
