"""Family Feud host TUI — Phase 1 (mock buzz, stepped pacing)."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from game.engine import (
    MatchState,
    Phase,
    advance,
    load_question_bank,
    new_match,
    reveal_next_host,
    select_question,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "questions" / "question_list.json"


class Scoreboard(Static):
    """Contestant scores."""

    def update_scores(self, state: MatchState) -> None:
        parts = []
        for name in state.contestants:
            score = state.scores.get(name, 0)
            marker = "★" if state.control == name else " "
            parts.append(f"{marker}{name} {score}")
        self.update("   ".join(parts))


class BoardPanel(Static):
    """Survey board slots."""

    def update_board(self, state: MatchState) -> None:
        if state.question is None:
            self.update("[dim]No question selected[/dim]")
            return
        lines = [f"[bold]{state.question.text}[/bold]", ""]
        for index, slot in enumerate(state.question.slots, start=1):
            if slot.revealed:
                answer = slot.answer
                pts = f"{slot.points:>3}"
            elif state.host_sees_answers:
                answer = f"[dim]{slot.answer}[/dim]"
                pts = f"[dim]{slot.points:>3}[/dim]"
            else:
                answer = "•" * min(12, max(4, len(slot.answer)))
                pts = " ? "
            lines.append(f" {index}. {answer:<28} {pts}")
        self.update("\n".join(lines))


class StatusPanel(Static):
    def update_status(self, state: MatchState) -> None:
        q = state.question.text if state.question else "(none)"
        self.update(
            f"[bold]Phase:[/bold] {state.phase.value}   "
            f"[bold]Control:[/bold] {state.control or '—'}   "
            f"[bold]Strikes:[/bold] {state.strikes}\n"
            f"[bold]Q:[/bold] {q}\n"
            f"[bold]Host:[/bold] {state.message}"
        )


class HostApp(App[None]):
    """Step through a Family Feud episode as host."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #top {
        height: 1fr;
    }
    #picker {
        width: 2fr;
        border: solid $accent;
    }
    #picker-title {
        dock: top;
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    #filter {
        dock: top;
        margin: 0 1 1 1;
    }
    #stage {
        width: 3fr;
        layout: vertical;
    }
    #scoreboard {
        height: 3;
        padding: 1;
        border: solid $success;
    }
    #board {
        height: 1fr;
        padding: 1;
        border: solid $warning;
    }
    #status {
        height: 5;
        padding: 0 1;
        border: solid $primary;
    }
    #buzz {
        height: 10;
        border: solid $secondary;
    }
    ListView {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("space", "advance", "Advance", show=True),
        Binding("enter", "select_question", "Select Q", show=True),
        Binding("r", "reveal", "Reveal", show=True),
        Binding("n", "next_pick", "Pick Q", show=True),
        Binding("t", "focus_buzz", "Buzz log", show=False),
        Binding("slash", "focus_filter", "Filter", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    TITLE = "Family Feud — Host"
    SUB_TITLE = "Phase 1 · mock buzz · stepped pacing"

    def __init__(
        self,
        questions_path: str | Path = DEFAULT_QUESTIONS,
        *,
        limit: int | None = None,
    ) -> None:
        super().__init__()
        bank = load_question_bank(questions_path, limit=limit)
        self.state = new_match(bank)
        self._filter = ""
        self._visible_indices: list[int] = list(range(len(bank)))

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top"):
            with Vertical(id="picker"):
                yield Label("Questions", id="picker-title")
                yield Input(placeholder="Filter questions…", id="filter")
                yield ListView(id="question-list")
            with Vertical(id="stage"):
                yield Scoreboard(id="scoreboard")
                yield BoardPanel(id="board")
                yield StatusPanel(id="status")
                yield RichLog(id="buzz", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild_question_list()
        self._refresh()
        self.query_one("#question-list", ListView).focus()

    def _rebuild_question_list(self) -> None:
        list_view = self.query_one("#question-list", ListView)
        list_view.clear()
        needle = self._filter.strip().lower()
        self._visible_indices = []
        for index, question in enumerate(self.state.questions):
            if needle and needle not in question.text.lower():
                continue
            self._visible_indices.append(index)
            label = f"{index + 1:03d}  {question.text}"
            list_view.append(ListItem(Label(label), name=str(index)))
        if self._visible_indices:
            list_view.index = 0

    def _refresh(self) -> None:
        self.query_one("#scoreboard", Scoreboard).update_scores(self.state)
        self.query_one("#board", BoardPanel).update_board(self.state)
        self.query_one("#status", StatusPanel).update_status(self.state)
        buzz = self.query_one("#buzz", RichLog)
        buzz.clear()
        if not self.state.buzz_log:
            buzz.write("[dim]Buzz log empty — Space starts the mock face-off.[/dim]")
            return
        buzz.write("[bold]Face-off results[/bold] (✓ = board hit)")
        for rank, event in enumerate(self.state.buzz_log, start=1):
            mark = "✓" if event.hit else "✗"
            matched = f" → {event.matched}" if event.matched else ""
            buzz.write(
                f"{rank}. {mark} {event.model:<8}  "
                f"{event.text!r:<22}  {event.latency_s:4.2f}s"
                f"{matched}"
            )

    @on(Input.Changed, "#filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._filter = event.value
        self._rebuild_question_list()

    @on(ListView.Selected, "#question-list")
    def on_question_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if item is None or item.name is None:
            return
        self._apply_question(int(item.name))

    def action_select_question(self) -> None:
        """Enter: use the highlighted list row even if Selected didn't fire."""
        list_view = self.query_one("#question-list", ListView)
        index = list_view.index
        if index is None or not self._visible_indices:
            self.state.message = "Highlight a question first."
            self._refresh()
            return
        if index < 0 or index >= len(self._visible_indices):
            return
        self._apply_question(self._visible_indices[index])

    def _apply_question(self, bank_index: int) -> None:
        self.state = select_question(self.state, bank_index)
        self._refresh()

    def action_advance(self) -> None:
        self.state = advance(self.state)
        self._refresh()

    def action_reveal(self) -> None:
        self.state = reveal_next_host(self.state)
        self._refresh()

    def action_next_pick(self) -> None:
        self.state.phase = Phase.PICK_QUESTION
        self.state.question = None
        self.state.buzz_log = []
        self.state.control = None
        self.state.message = "Pick the next question from the list."
        self._refresh()
        self.query_one("#question-list", ListView).focus()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_focus_buzz(self) -> None:
        self.query_one("#buzz", RichLog).focus()


def run(
    questions_path: str | Path = DEFAULT_QUESTIONS,
    *,
    limit: int | None = None,
) -> None:
    HostApp(questions_path, limit=limit).run()


if __name__ == "__main__":
    run()
