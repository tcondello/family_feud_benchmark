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

`openAI_family_feud.py` currently reads `question_list.json` from the working
directory; point it at `questions/all_questions.json` (or copy/symlink) to use
the expanded set.

## Host TUI

Step through a Family Feud episode as host. Locked rules:

- **Contestants:** each model alone (Opus, Ember, gpt-5.5, Flash, Kimi, Qwen)
- **Wrong buzz:** lockout only (no strike)
- **Main round:** Mode B — classic 3 strikes, then one steal attempt
- **Question pool:** BuzzFeed 115 (`questions/question_list.json`)
- **Board:** host always sees answers (dimmed until revealed)

```bash
pip install -r requirements.txt

# Mock buzz (no API keys) — practice pacing
python -m game

# Live models (needs runtime secrets / .env)
python -m game --live
```

| Key | Action |
|-----|--------|
| `Enter` | Select highlighted question |
| `Space` | Advance (buzz → control → guess / steal → next Q) |
| `r` | Host-reveal next answer (no points) |
| `/` | Focus question filter |
| `n` | Back to question picker |
| `q` | Quit |
