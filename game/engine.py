"""Pure Family Feud match state machine (UI-free).

Phase 1: host picks a question, runs a mock face-off, then steps through
board reveals and round completion. Live model buzz comes in Phase 2.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


DEFAULT_CONTESTANTS: tuple[str, ...] = (
    "Opus",
    "Ember",
    "gpt-5.5",
    "Flash",
    "Kimi",
    "Qwen",
)


class Phase(str, Enum):
    LOBBY = "lobby"
    PICK_QUESTION = "pick_question"
    FACE_OFF_READY = "face_off_ready"
    FACE_OFF_RESULT = "face_off_result"
    MAIN_PLAY = "main_play"
    ROUND_OVER = "round_over"


@dataclass
class BoardSlot:
    answer: str
    points: int
    revealed: bool = False


@dataclass
class BuzzEvent:
    model: str
    text: str
    latency_s: float
    hit: bool
    matched: str | None = None
    points: int = 0


@dataclass
class Question:
    text: str
    slots: list[BoardSlot]
    source: str = ""
    index: int = 0


@dataclass
class MatchState:
    contestants: list[str]
    scores: dict[str, int]
    phase: Phase
    questions: list[Question]
    question: Question | None = None
    control: str | None = None
    strikes: int = 0
    buzz_log: list[BuzzEvent] = field(default_factory=list)
    message: str = "Pick a question to start the face-off."
    host_sees_answers: bool = True


def _board_answers(raw: dict[str, Any]) -> list[dict[str, Any]]:
    answers = raw.get("answers")
    if answers is None:
        answers = raw.get("answer")
    if not isinstance(answers, list):
        return []
    return [a for a in answers if isinstance(a, dict) and "answer" in a]


def load_question_bank(
    path: str | Path,
    *,
    limit: int | None = None,
) -> list[Question]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_questions = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(raw_questions, list):
        raise ValueError(f"Unexpected question format in {path}")

    bank: list[Question] = []
    for index, item in enumerate(raw_questions):
        text = str(item.get("question") or "").strip()
        if not text:
            continue
        slots = [
            BoardSlot(
                answer=str(entry.get("answer") or "").strip(),
                points=int(entry.get("score") or 0),
            )
            for entry in _board_answers(item)
            if str(entry.get("answer") or "").strip()
        ]
        # Highest survey points first (classic board order).
        slots.sort(key=lambda slot: (-slot.points, slot.answer.lower()))
        if not slots:
            continue
        bank.append(
            Question(
                text=text,
                slots=slots,
                source=str(path),
                index=index,
            )
        )
        if limit is not None and len(bank) >= limit:
            break
    return bank


def new_match(
    questions: list[Question],
    *,
    contestants: list[str] | None = None,
) -> MatchState:
    names = list(contestants or DEFAULT_CONTESTANTS)
    return MatchState(
        contestants=names,
        scores={name: 0 for name in names},
        phase=Phase.PICK_QUESTION,
        questions=questions,
        message=f"Loaded {len(questions)} questions. Pick one to begin.",
    )


def select_question(state: MatchState, question_index: int) -> MatchState:
    if question_index < 0 or question_index >= len(state.questions):
        state.message = "Invalid question index."
        return state
    question = state.questions[question_index]
    # Fresh reveal flags for this round.
    fresh = Question(
        text=question.text,
        slots=[
            BoardSlot(answer=s.answer, points=s.points, revealed=False)
            for s in question.slots
        ],
        source=question.source,
        index=question.index,
    )
    state.question = fresh
    state.control = None
    state.strikes = 0
    state.buzz_log = []
    state.phase = Phase.FACE_OFF_READY
    state.message = (
        f"Face-off ready. Press Space to buzz models on: {fresh.text}"
    )
    return state


def _normalize(text: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in text).split())


def grade_against_board(
    guess: str, slots: list[BoardSlot]
) -> tuple[bool, str | None, int]:
    needle = _normalize(guess)
    if not needle:
        return False, None, 0
    best_points = 0
    best_answer = None
    for slot in slots:
        board = _normalize(slot.answer)
        if not board:
            continue
        if needle == board or needle in board or board in needle:
            if slot.points >= best_points:
                best_points = slot.points
                best_answer = slot.answer
    return best_answer is not None, best_answer, best_points


def mock_buzz(state: MatchState, *, seed: int | None = None) -> MatchState:
    """Simulate a face-off: canned / random answers with fake latency."""
    if state.question is None:
        state.message = "Pick a question first."
        return state
    if state.phase not in {Phase.FACE_OFF_READY, Phase.FACE_OFF_RESULT}:
        state.message = "Face-off already resolved. Advance with Space."
        return state

    rng = random.Random(seed)
    slots = state.question.slots
    top_answers = [s.answer for s in slots[:3]]
    decoys = ["pass", "I don't know", "stuff", "things", "maybe"]

    events: list[BuzzEvent] = []
    for model in state.contestants:
        # ~60% chance to hit a real board answer in the mock.
        if rng.random() < 0.6 and top_answers:
            text = rng.choice(top_answers)
        else:
            text = rng.choice(decoys + [s.answer for s in slots[3:4]] or decoys)
        latency = round(rng.uniform(0.4, 2.8), 2)
        hit, matched, points = grade_against_board(text, slots)
        events.append(
            BuzzEvent(
                model=model,
                text=text,
                latency_s=latency,
                hit=hit,
                matched=matched,
                points=points,
            )
        )

    # First valid hit by latency wins (classic buzz-in).
    hits = sorted([e for e in events if e.hit], key=lambda e: e.latency_s)
    events.sort(key=lambda e: (0 if e.hit else 1, e.latency_s))
    state.buzz_log = events

    if hits:
        winner = hits[0]
        state.control = winner.model
        state.phase = Phase.FACE_OFF_RESULT
        state.message = (
            f"{winner.model} buzzes in first with {winner.text!r} "
            f"({winner.latency_s:.2f}s) → matched {winner.matched!r} "
            f"for {winner.points}. Press Space to take control."
        )
    else:
        state.control = None
        state.phase = Phase.FACE_OFF_RESULT
        state.message = (
            "No one hit the board. Press Space to reveal answers / end round."
        )
    return state


def reveal_matched_slot(state: MatchState, matched: str | None) -> None:
    if not state.question or not matched:
        return
    for slot in state.question.slots:
        if slot.answer == matched and not slot.revealed:
            slot.revealed = True
            return


def advance(state: MatchState) -> MatchState:
    """Host Space: step one beat forward."""
    if state.phase == Phase.PICK_QUESTION:
        state.message = "Select a question from the list, then press Enter."
        return state

    if state.phase == Phase.FACE_OFF_READY:
        return mock_buzz(state)

    if state.phase == Phase.FACE_OFF_RESULT:
        if state.control and state.buzz_log:
            winner = next(e for e in state.buzz_log if e.model == state.control)
            reveal_matched_slot(state, winner.matched)
            state.scores[state.control] = state.scores.get(state.control, 0) + winner.points
            state.phase = Phase.MAIN_PLAY
            state.message = (
                f"{state.control} has control. Press Space to reveal the "
                "next board answer (Phase 1 mock main play)."
            )
        else:
            state.phase = Phase.MAIN_PLAY
            state.message = (
                "No controller. Press Space to reveal board answers one by one."
            )
        return state

    if state.phase == Phase.MAIN_PLAY:
        if state.question is None:
            state.phase = Phase.PICK_QUESTION
            return state
        hidden = [s for s in state.question.slots if not s.revealed]
        if not hidden:
            state.phase = Phase.ROUND_OVER
            state.message = "Board clear. Press Space to pick another question."
            return state
        slot = hidden[0]
        slot.revealed = True
        if state.control:
            state.scores[state.control] = state.scores.get(state.control, 0) + slot.points
            state.message = (
                f"Revealed {slot.answer!r} ({slot.points}). "
                f"Points to {state.control}. "
                f"{len(hidden) - 1} left — Space to continue."
            )
        else:
            state.message = (
                f"Revealed {slot.answer!r} ({slot.points}). "
                f"{len(hidden) - 1} left — Space to continue."
            )
        if all(s.revealed for s in state.question.slots):
            state.phase = Phase.ROUND_OVER
            state.message += " Round over."
        return state

    if state.phase == Phase.ROUND_OVER:
        state.question = None
        state.control = None
        state.strikes = 0
        state.buzz_log = []
        state.phase = Phase.PICK_QUESTION
        state.message = "Pick the next question."
        return state

    return state


def reveal_next_host(state: MatchState) -> MatchState:
    """Host 'r': reveal next hidden answer without awarding points."""
    if state.question is None:
        state.message = "No active question."
        return state
    for slot in state.question.slots:
        if not slot.revealed:
            slot.revealed = True
            state.message = f"Host reveal: {slot.answer!r} ({slot.points})."
            return state
    state.message = "Nothing left to reveal."
    return state
