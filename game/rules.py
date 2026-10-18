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

FACE_OFF_SYSTEM = (
    "You are a contestant on Family Feud. Answer with ONLY a short survey-style "
    "phrase. No explanation. Example: name something with 4 wheels → car"
)

MAIN_PLAY_SYSTEM = (
    "You are playing Family Feud and have control of the board. Give ONE new "
    "short survey answer that is NOT in the already-revealed list. Reply with "
    "only the answer words."
)
