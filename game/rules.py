"""Locked Family Feud host rules (v1).

Contestants: each model alone (not team families)
Wrong buzz: lockout only (misses the face-off; no strike from buzzing wrong)
Main round: Mode B — classic 3 strikes, then one steal attempt
Question pool: BuzzFeed 115 (`questions/question_list.json`)
Hidden board: host always sees answers (dimmed until revealed)
"""

from __future__ import annotations

STRIKES_TO_STEAL = 3

# Display name → provider/model id used for live buzz.
CONTESTANT_MODELS: dict[str, tuple[str, str]] = {
    "Opus": ("anthropic", "claude-opus-4-6"),
    "Ember": ("fireworks", "accounts/fireworks/models/ember-1"),
    "gpt-5.5": ("openai", "gpt-5.5"),
    "Flash": ("google", "gemini-flash-latest"),
    "Kimi": ("fireworks", "accounts/fireworks/models/kimi-k3"),
    "Qwen": ("fireworks", "accounts/fireworks/models/qwen3p8-max"),
}

DEFAULT_CONTESTANTS: tuple[str, ...] = tuple(CONTESTANT_MODELS.keys())

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
}

# Structured JSON answers keep budgets small — thinking stays out of `content`
# when providers honor response_format / output_config / response_schema.
MAX_TOKENS_BY_PROVIDER: dict[str, int] = {
    "openai": 64,
    "anthropic": 64,
    "google": 64,
    "fireworks": 96,
}

# Shared schema for every provider call. Models must return exactly this JSON.
ANSWER_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Short Family Feud survey answer (1-4 words).",
            "maxLength": 40,
        }
    },
    "required": ["answer"],
    "additionalProperties": False,
}

FACE_OFF_SYSTEM = (
    "You are a contestant on Family Feud. Respond with JSON only matching "
    '{"answer":"<1-4 word survey phrase>"}. No other keys. Do not put reasoning '
    "in the JSON. Do not repeat words from the question itself. "
    'Example: {"answer":"car"}'
)

MAIN_PLAY_SYSTEM = (
    "You are playing Family Feud and have control of the board. Respond with "
    'JSON only matching {"answer":"<1-4 word survey phrase>"}. Never reuse '
    "anything listed as already revealed or already tried/wrong. No reasoning "
    "inside the JSON."
)

REPAIR_SYSTEM = (
    "Your previous reply was invalid. Respond with JSON only matching "
    '{"answer":"<1-4 word NEW survey phrase>"}. Do not repeat forbidden words. '
    "No reasoning."
)
