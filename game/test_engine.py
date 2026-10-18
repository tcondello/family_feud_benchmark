"""Unit tests for host game engine (Mode B + lockout)."""

from __future__ import annotations

from pathlib import Path

from game.engine import (
    BoardSlot,
    BuzzEvent,
    Phase,
    advance,
    apply_face_off_results,
    apply_main_guess,
    apply_steal_guess,
    begin_main_play,
    grade_against_board,
    load_question_bank,
    mock_buzz,
    new_match,
    select_question,
)


def test_load_buzzfeed_style(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    path.write_text(
        """
        {"questions": [
          {"question": "Name something that might be brewing",
           "answers": [
             {"answer": "Coffee", "score": 37},
             {"answer": "Beer", "score": 28},
             {"answer": "Tea", "score": 17},
             {"answer": "Trouble", "score": 8}
           ]}
        ]}
        """,
        encoding="utf-8",
    )
    bank = load_question_bank(path)
    state = new_match(bank, contestants=["Opus", "Flash", "Ember"])
    state = select_question(state, 0)
    assert state.phase == Phase.FACE_OFF_READY
    assert state.host_sees_answers is True


def test_wrong_buzz_is_lockout_only() -> None:
    events = [
        BuzzEvent("Flash", "Coffee", 0.9, True, "Coffee", 37),
        BuzzEvent("Opus", "teapot", 0.5, False),
    ]
    from game.engine import Question

    state = new_match([], contestants=["Flash", "Opus"])
    state.question = Question(
        text="Name something that might be brewing",
        slots=[BoardSlot("Coffee", 37), BoardSlot("Beer", 28)],
    )
    state = apply_face_off_results(state, events)
    assert state.control == "Flash"
    opus = next(e for e in state.buzz_log if e.model == "Opus")
    assert opus.locked_out is True
    assert state.strikes == 0  # lockout only — no strike from face-off miss


def test_mode_b_three_strikes_then_steal() -> None:
    state = new_match([], contestants=["Flash", "Opus"])
    from game.engine import Question

    state.question = Question(
        text="Name something that might be brewing",
        slots=[
            BoardSlot("Coffee", 37),
            BoardSlot("Beer", 28),
            BoardSlot("Tea", 17),
        ],
    )
    state.buzz_log = [
        BuzzEvent("Flash", "Coffee", 0.8, True, "Coffee", 37),
        BuzzEvent("Opus", "Beer", 1.2, True, "Beer", 28),
    ]
    state.control = "Flash"
    state = begin_main_play(state)
    assert state.phase == Phase.MAIN_PLAY
    assert state.round_points == 37

    state = apply_main_guess(state, "nope1")
    state = apply_main_guess(state, "nope2")
    assert state.strikes == 2
    assert state.wrong_guesses == ["nope1", "nope2"]
    state = apply_main_guess(state, "nope3")
    assert state.phase == Phase.STEAL
    assert state.steal_challenger == "Opus"
    assert state.wrong_guesses == ["nope1", "nope2", "nope3"]

    # Successful steal takes the bank.
    state = apply_steal_guess(state, "Beer")
    assert state.phase == Phase.ROUND_OVER
    assert state.scores["Opus"] == state.round_points or state.scores["Opus"] > 0
    assert state.scores["Opus"] >= 37 + 28


def test_used_question_cannot_be_reselected(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    path.write_text(
        """
        {"questions": [
          {"question": "Q1", "answers": [{"answer": "A", "score": 10}]},
          {"question": "Q2", "answers": [{"answer": "B", "score": 10}]}
        ]}
        """,
        encoding="utf-8",
    )
    state = new_match(load_question_bank(path), contestants=["Opus"])
    state = select_question(state, 0)
    assert 0 in state.used_questions
    state = select_question(state, 0)
    assert state.phase == Phase.FACE_OFF_READY  # still on first selection
    assert "already used" in state.message.lower()
    state = select_question(state, 1)
    assert state.phase == Phase.FACE_OFF_READY
    assert state.question and state.question.text == "Q2"


def test_grade_against_board() -> None:
    slots = [BoardSlot("Coffee", 37), BoardSlot("Beer", 28)]
    hit, matched, points = grade_against_board("coffee", slots)
    assert hit and matched == "Coffee" and points == 37


def test_mock_advance_path(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    path.write_text(
        """
        {"questions": [
          {"question": "Name something with wheels",
           "answers": [
             {"answer": "Car", "score": 40},
             {"answer": "Bike", "score": 25},
             {"answer": "Bus", "score": 10}
           ]}
        ]}
        """,
        encoding="utf-8",
    )
    state = new_match(load_question_bank(path), contestants=["Opus", "Flash"])
    state = select_question(state, 0)
    state = mock_buzz(state, seed=2)
    assert state.phase == Phase.FACE_OFF_RESULT
    state = advance(state)
    assert state.phase in {Phase.MAIN_PLAY, Phase.ROUND_OVER}
