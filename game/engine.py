"""Pure Family Feud match state machine (UI-free).

Locked rules: see game/rules.py
  - Solo contestants (one model each)
  - Wrong face-off buzz = lockout only
  - Main play Mode B: 3 strikes → one steal
  - BuzzFeed 115 default pool
  - Host always sees board answers
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from game.rules import DEFAULT_CONTESTANTS, STRIKES_TO_STEAL


class Phase(str, Enum):
    PICK_QUESTION = "pick_question"
    FACE_OFF_READY = "face_off_ready"
    FACE_OFF_RUNNING = "face_off_running"
    FACE_OFF_RESULT = "face_off_result"
    MAIN_PLAY = "main_play"
    STEAL = "steal"
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
    locked_out: bool = False  # True when face-off miss (wrong buzz)


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
    steal_challenger: str | None = None
    strikes: int = 0
    round_points: int = 0  # points banked this question (awarded at resolve)
    buzz_log: list[BuzzEvent] = field(default_factory=list)
    play_log: list[str] = field(default_factory=list)
    # Wrong main-play / steal guesses this round — must be sent back to the model.
    wrong_guesses: list[str] = field(default_factory=list)
    # Question bank indices already played this episode (until process restart).
    used_questions: set[int] = field(default_factory=set)
    message: str = "Pick a question to start the face-off."
    host_sees_answers: bool = True  # locked rule
    live: bool = False


BuzzFn = Callable[[MatchState], MatchState]
# name, question, revealed_answers, wrong_guesses → (text, latency_s)
AnswerFn = Callable[[str, str, list[str], list[str]], tuple[str, float]]


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
        slots.sort(key=lambda slot: (-slot.points, slot.answer.lower()))
        if not slots:
            continue
        bank.append(
            Question(text=text, slots=slots, source=str(path), index=index)
        )
        if limit is not None and len(bank) >= limit:
            break
    return bank


def new_match(
    questions: list[Question],
    *,
    contestants: list[str] | None = None,
    live: bool = False,
) -> MatchState:
    names = list(contestants or DEFAULT_CONTESTANTS)
    return MatchState(
        contestants=names,
        scores={name: 0 for name in names},
        phase=Phase.PICK_QUESTION,
        questions=questions,
        live=live,
        message=(
            f"Loaded {len(questions)} questions. "
            f"{'LIVE' if live else 'MOCK'} buzz. Pick one to begin."
        ),
    )


def select_question(state: MatchState, question_index: int) -> MatchState:
    if question_index < 0 or question_index >= len(state.questions):
        state.message = "Invalid question index."
        return state
    if question_index in state.used_questions:
        state.message = (
            "That question was already used this episode. "
            "Pick another (used ones stay marked until you quit)."
        )
        return state
    question = state.questions[question_index]
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
    state.used_questions.add(question_index)
    state.control = None
    state.steal_challenger = None
    state.strikes = 0
    state.round_points = 0
    state.buzz_log = []
    state.play_log = []
    state.wrong_guesses = []
    state.phase = Phase.FACE_OFF_READY
    mode = "LIVE" if state.live else "MOCK"
    state.message = (
        f"Face-off ready ({mode}). Space to buzz all models on: {fresh.text}"
    )
    return state


def _normalize(text: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    )


def _light_stem(token: str) -> str:
    """Light inflection fold: shopping→shop, cars→car. Not election→select."""
    if len(token) > 5 and token.endswith("ing"):
        base = token[:-3]
        # shopping → shopp → shop; brewing → brew
        if len(base) > 2 and base[-1] == base[-2] and base[-1] not in "aeiou":
            base = base[:-1]
        return base
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es") and token[-3] not in "aeiou":
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _guess_matches_board(needle: str, board: str) -> bool:
    """True when guess matches a board slot without CoT / infix false positives.

    Accepts: grocery shopping ↔ Grocery shop (stem).
    Rejects: election ⊄ selection (single-token infix).
    """
    if not needle or not board:
        return False
    if needle == board:
        return True
    if len(needle.split()) > 6 or len(needle) > 48:
        return False

    n_toks = [_light_stem(t) for t in needle.split()]
    b_toks = [_light_stem(t) for t in board.split()]
    if not n_toks or not b_toks:
        return False

    # Single-token answers: equality / light stem only — never raw substring.
    if len(n_toks) == 1 and len(b_toks) == 1:
        return n_toks[0] == b_toks[0]

    # Multi-word: either phrase as a contiguous stemmed-token sequence in the other.
    if len(n_toks) <= len(b_toks):
        shorter, longer = n_toks, b_toks
    else:
        shorter, longer = b_toks, n_toks
    for i in range(len(longer) - len(shorter) + 1):
        if longer[i : i + len(shorter)] == shorter:
            return True
    return False


def grade_against_board(
    guess: str, slots: list[BoardSlot], *, revealed_only: bool = False
) -> tuple[bool, str | None, int]:
    needle = _normalize(guess)
    if not needle:
        return False, None, 0
    best_points = 0
    best_answer = None
    for slot in slots:
        if revealed_only and not slot.revealed:
            continue
        if not revealed_only and slot.revealed:
            # Main play: already-revealed answers don't count as new hits.
            continue
        board = _normalize(slot.answer)
        if not board:
            continue
        if _guess_matches_board(needle, board):
            if slot.points >= best_points:
                best_points = slot.points
                best_answer = slot.answer
    return best_answer is not None, best_answer, best_points


def revealed_answers(state: MatchState) -> list[str]:
    if not state.question:
        return []
    return [s.answer for s in state.question.slots if s.revealed]


def unrevealed_slots(state: MatchState) -> list[BoardSlot]:
    if not state.question:
        return []
    return [s for s in state.question.slots if not s.revealed]


def reveal_matched_slot(state: MatchState, matched: str | None) -> int:
    if not state.question or not matched:
        return 0
    for slot in state.question.slots:
        if slot.answer == matched and not slot.revealed:
            slot.revealed = True
            return slot.points
    return 0


def pick_steal_challenger(state: MatchState) -> str | None:
    """Fastest face-off board-hit among non-controllers; else fastest lockout."""
    if not state.control:
        return None
    others_hit = [
        e
        for e in state.buzz_log
        if e.model != state.control and e.hit and not e.locked_out
    ]
    if others_hit:
        return sorted(others_hit, key=lambda e: e.latency_s)[0].model
    others = [e for e in state.buzz_log if e.model != state.control]
    if not others:
        return None
    return sorted(others, key=lambda e: e.latency_s)[0].model


def apply_face_off_results(state: MatchState, events: list[BuzzEvent]) -> MatchState:
    """Resolve face-off: first hit by latency wins; misses are lockout only."""
    for event in events:
        if not event.hit:
            event.locked_out = True
    events = sorted(events, key=lambda e: (0 if e.hit else 1, e.latency_s))
    state.buzz_log = events
    hits = [e for e in events if e.hit]
    if hits:
        winner = sorted(hits, key=lambda e: e.latency_s)[0]
        state.control = winner.model
        state.steal_challenger = None
        state.phase = Phase.FACE_OFF_RESULT
        fastest = sorted(events, key=lambda e: e.latency_s)[0]
        if fastest.model != winner.model:
            note = (
                f" Fastest buzz was {fastest.model} "
                f"({fastest.latency_s:.2f}s, {fastest.text!r}) but missed the board."
            )
        else:
            note = ""
        state.message = (
            f"{winner.model} wins face-off with {winner.text!r} "
            f"({winner.latency_s:.2f}s) → {winner.matched!r} ({winner.points}). "
            f"Control goes to the fastest board hit, not the fastest miss.{note} "
            "Space to take control."
        )
    else:
        state.control = None
        state.phase = Phase.FACE_OFF_RESULT
        state.message = (
            "No one hit the board (all locked out). Space to end the round."
        )
    return state


def mock_buzz(state: MatchState, *, seed: int | None = None) -> MatchState:
    if state.question is None:
        state.message = "Pick a question first."
        return state
    rng = random.Random(seed)
    slots = state.question.slots
    top = [s.answer for s in slots[:3]]
    decoys = ["pass", "I don't know", "stuff", "things", "maybe"]
    events: list[BuzzEvent] = []
    for model in state.contestants:
        if rng.random() < 0.55 and top:
            text = rng.choice(top)
        else:
            text = rng.choice(decoys)
        latency = round(rng.uniform(0.35, 2.6), 2)
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
    return apply_face_off_results(state, events)


def bank_points(state: MatchState, points: int) -> None:
    state.round_points += points


def resolve_round(state: MatchState, winner: str | None) -> MatchState:
    """Award banked round points and close the question."""
    if winner and state.round_points:
        state.scores[winner] = state.scores.get(winner, 0) + state.round_points
        state.play_log.append(
            f"{winner} wins the round for {state.round_points} points."
        )
        state.message = (
            f"Round over — {winner} takes {state.round_points}. "
            "Space for next question."
        )
    else:
        state.message = "Round over — no points awarded. Space for next question."
        state.play_log.append("Round over with no points awarded.")
    state.phase = Phase.ROUND_OVER
    return state


def begin_main_play(state: MatchState) -> MatchState:
    if state.question is None:
        return state
    if not state.control:
        # Reveal remaining for show, no points.
        for slot in state.question.slots:
            slot.revealed = True
        state.round_points = 0
        return resolve_round(state, None)

    winner_event = next(e for e in state.buzz_log if e.model == state.control)
    pts = reveal_matched_slot(state, winner_event.matched)
    bank_points(state, pts)
    state.strikes = 0
    state.phase = Phase.MAIN_PLAY
    state.play_log.append(
        f"{state.control} takes control with {winner_event.matched!r} (+{pts})."
    )
    left = len(unrevealed_slots(state))
    if left == 0:
        return resolve_round(state, state.control)
    state.message = (
        f"{state.control} has control. Strikes 0/{STRIKES_TO_STEAL}. "
        f"{left} answers left. Space for next guess (Mode B)."
    )
    return state


def apply_main_guess(state: MatchState, text: str, latency_s: float = 0.0) -> MatchState:
    """One main-play guess from the controlling contestant."""
    if state.phase != Phase.MAIN_PLAY or not state.control or not state.question:
        return state
    hit, matched, points = grade_against_board(text, state.question.slots)
    if hit and matched:
        pts = reveal_matched_slot(state, matched)
        bank_points(state, pts)
        state.play_log.append(
            f"{state.control}: {text!r} → {matched!r} (+{pts}) [{latency_s:.2f}s]"
        )
        left = len(unrevealed_slots(state))
        if left == 0:
            return resolve_round(state, state.control)
        state.message = (
            f"Good answer! {matched!r} (+{pts}). "
            f"Strikes {state.strikes}/{STRIKES_TO_STEAL}. "
            f"{left} left. Space for next guess."
        )
        return state

    state.strikes += 1
    # Only store short wrongs — never CoT dumps (they poison the next prompt).
    wrong = text.strip()
    if wrong and len(wrong.split()) <= 8 and len(wrong) <= 60:
        state.wrong_guesses.append(wrong)
    elif wrong:
        state.play_log.append(
            f"(omitted long/invalid guess from wrong list: {len(wrong)} chars)"
        )
    state.play_log.append(
        f"{state.control}: {text!r} → STRIKE {state.strikes} [{latency_s:.2f}s]"
    )

    if state.strikes >= STRIKES_TO_STEAL:
        challenger = pick_steal_challenger(state)
        state.steal_challenger = challenger
        state.phase = Phase.STEAL
        if challenger:
            state.message = (
                f"3 strikes! {challenger} steals for one answer. "
                f"Round bank={state.round_points}. Space for steal attempt."
            )
        else:
            state.message = (
                "3 strikes and no challenger. "
                f"{state.control} keeps the bank ({state.round_points}). Space."
            )
            return resolve_round(state, state.control)
        return state

    state.message = (
        f"Strike {state.strikes}/{STRIKES_TO_STEAL} on {text!r}. "
        "Space for next guess."
    )
    return state


def apply_steal_guess(state: MatchState, text: str, latency_s: float = 0.0) -> MatchState:
    if state.phase != Phase.STEAL or not state.question:
        return state
    challenger = state.steal_challenger
    if not challenger:
        return resolve_round(state, state.control)

    hit, matched, _points = grade_against_board(text, state.question.slots)
    if hit and matched:
        pts = reveal_matched_slot(state, matched)
        bank_points(state, pts)
        state.play_log.append(
            f"STEAL {challenger}: {text!r} → {matched!r} (+{pts}) "
            f"takes bank {state.round_points} [{latency_s:.2f}s]"
        )
        return resolve_round(state, challenger)

    state.play_log.append(
        f"STEAL {challenger}: {text!r} MISS — {state.control} keeps bank "
        f"{state.round_points} [{latency_s:.2f}s]"
    )
    return resolve_round(state, state.control)


def mock_answer(
    model: str, question: str, already: list[str], *, seed: int | None = None
) -> tuple[str, float]:
    """Deterministic-ish mock answer for Mode B stepping."""
    rng = random.Random(f"{seed}-{model}-{question}-{len(already)}")
    # Prefer unused board-looking strings from already context — engine tests
    # pass real remaining answers via a wrapper in TUI/tests.
    decoys = ["lamp", "sandwich", "giraffe", "password", "trombone"]
    text = rng.choice(decoys)
    return text, round(rng.uniform(0.5, 2.0), 2)


def advance(
    state: MatchState,
    *,
    buzz_fn: BuzzFn | None = None,
    answer_fn: AnswerFn | None = None,
) -> MatchState:
    """Host Space — one beat forward."""
    if state.phase == Phase.PICK_QUESTION:
        state.message = "Select a question from the list, then press Enter."
        return state

    if state.phase == Phase.FACE_OFF_READY:
        state.phase = Phase.FACE_OFF_RUNNING
        state.message = "Buzzing models…"
        fn = buzz_fn or mock_buzz
        return fn(state)

    if state.phase == Phase.FACE_OFF_RUNNING:
        state.message = "Still buzzing…"
        return state

    if state.phase == Phase.FACE_OFF_RESULT:
        return begin_main_play(state)

    if state.phase == Phase.MAIN_PLAY:
        if not state.control or not state.question:
            return resolve_round(state, None)
        already = revealed_answers(state)
        wrongs = list(state.wrong_guesses)
        remaining = [s.answer for s in unrevealed_slots(state)]
        if answer_fn is None:
            # Mock: 60% chance to hit a remaining answer.
            rng = random.Random(len(state.play_log) + state.strikes)
            if remaining and rng.random() < 0.55:
                text = rng.choice(remaining)
                latency = round(rng.uniform(0.4, 1.8), 2)
            else:
                text, latency = mock_answer(
                    state.control, state.question.text, already + wrongs
                )
        else:
            text, latency = answer_fn(
                state.control, state.question.text, already, wrongs
            )
        return apply_main_guess(state, text, latency)

    if state.phase == Phase.STEAL:
        if not state.steal_challenger or not state.question:
            return resolve_round(state, state.control)
        already = revealed_answers(state)
        wrongs = list(state.wrong_guesses)
        remaining = [s.answer for s in unrevealed_slots(state)]
        if answer_fn is None:
            rng = random.Random(f"steal-{len(state.play_log)}")
            if remaining and rng.random() < 0.45:
                text = rng.choice(remaining)
                latency = round(rng.uniform(0.4, 1.8), 2)
            else:
                text, latency = mock_answer(
                    state.steal_challenger, state.question.text, already + wrongs
                )
        else:
            text, latency = answer_fn(
                state.steal_challenger, state.question.text, already, wrongs
            )
        return apply_steal_guess(state, text, latency)

    if state.phase == Phase.ROUND_OVER:
        state.question = None
        state.control = None
        state.steal_challenger = None
        state.strikes = 0
        state.round_points = 0
        state.buzz_log = []
        state.play_log = []
        state.wrong_guesses = []
        state.phase = Phase.PICK_QUESTION
        used = len(state.used_questions)
        state.message = (
            f"Pick the next question ({used} used this episode — marked in list)."
        )
        return state

    return state


def reveal_next_host(state: MatchState) -> MatchState:
    """Host 'r': reveal next hidden answer without changing the point bank."""
    if state.question is None:
        state.message = "No active question."
        return state
    for slot in state.question.slots:
        if not slot.revealed:
            slot.revealed = True
            state.message = (
                f"Host reveal (no points): {slot.answer!r} ({slot.points})."
            )
            return state
    state.message = "Nothing left to reveal."
    return state
