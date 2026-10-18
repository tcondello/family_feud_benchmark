"""Unit tests for Phase 1 game engine (no TUI)."""

from __future__ import annotations

from game.engine import (
    Phase,
    advance,
    grade_against_board,
    load_question_bank,
    mock_buzz,
    new_match,
    select_question,
)


def test_load_and_select_face_off(tmp_path):
    path = tmp_path / "q.json"
    path.write_text(
        """
        {"questions": [
          {"question": "Name something with wheels",
           "answers": [
             {"answer": "Car", "score": 40},
             {"answer": "Bike", "score": 25}
           ]}
        ]}
        """,
        encoding="utf-8",
    )
    bank = load_question_bank(path)
    state = new_match(bank, contestants=["Opus", "Flash"])
    assert state.phase == Phase.PICK_QUESTION
    state = select_question(state, 0)
    assert state.phase == Phase.FACE_OFF_READY
    assert state.question is not None
    assert state.question.slots[0].answer == "Car"

    state = mock_buzz(state, seed=1)
    assert state.phase == Phase.FACE_OFF_RESULT
    assert len(state.buzz_log) == 2

    # Step into main play / awards
    before = dict(state.scores)
    state = advance(state)
    assert state.phase in {Phase.MAIN_PLAY, Phase.ROUND_OVER}
    if state.control:
        assert state.scores[state.control] >= before[state.control]


def test_grade_against_board():
    from game.engine import BoardSlot

    slots = [
        BoardSlot("Coffee", 37),
        BoardSlot("Beer", 28),
    ]
    hit, matched, points = grade_against_board("coffee", slots)
    assert hit and matched == "Coffee" and points == 37
    hit, matched, points = grade_against_board("teapot", slots)
    assert not hit and matched is None
