"""Family Feud host TUI — Phase 2 (Mode B + optional live buzz)."""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
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

from game.buzz import available_contestants, make_answer_fn, make_buzz_fn
from game.engine import (
    MatchState,
    Phase,
    advance,
    load_question_bank,
    new_match,
    reveal_next_host,
    select_question,
)
from game.rules import DEFAULT_CONTESTANTS, STRIKES_TO_STEAL

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "questions" / "question_list.json"


class Scoreboard(Static):
    def update_scores(self, state: MatchState) -> None:
        parts = []
        for name in state.contestants:
            score = state.scores.get(name, 0)
            if state.control == name:
                marker = "★"
            elif state.steal_challenger == name and state.phase == Phase.STEAL:
                marker = "◆"
            else:
                marker = " "
            parts.append(f"{marker}{name} {score}")
        bank = f"  bank:{state.round_points}" if state.question else ""
        self.update("   ".join(parts) + bank)


class BoardPanel(Static):
    def update_board(self, state: MatchState) -> None:
        if state.question is None:
            self.update("[dim]No question selected[/dim]")
            return
        lines = [f"[bold]{state.question.text}[/bold]", ""]
        for index, slot in enumerate(state.question.slots, start=1):
            if slot.revealed:
                answer = f"[bold green]{slot.answer}[/bold green]"
                pts = f"{slot.points:>3}"
            elif state.host_sees_answers:
                answer = f"[dim]{slot.answer}[/dim]"
                pts = f"[dim]{slot.points:>3}[/dim]"
            else:
                answer = "•" * min(12, max(4, len(slot.answer)))
                pts = " ? "
            lines.append(f" {index}. {answer:<40} {pts}")
        self.update("\n".join(lines))


class StatusPanel(Static):
    def update_status(self, state: MatchState) -> None:
        q = state.question.text if state.question else "(none)"
        mode = "LIVE" if state.live else "MOCK"
        wrongs = ", ".join(state.wrong_guesses[-4:]) if state.wrong_guesses else "—"
        self.update(
            f"[bold]Mode:[/bold] {mode} · Mode B ({STRIKES_TO_STEAL} strikes) · "
            f"wrong buzz = lockout · used Qs: {len(state.used_questions)}\n"
            f"[bold]Phase:[/bold] {state.phase.value}   "
            f"[bold]Control:[/bold] {state.control or '—'}   "
            f"[bold]Steal:[/bold] {state.steal_challenger or '—'}   "
            f"[bold]Strikes:[/bold] {state.strikes}/{STRIKES_TO_STEAL}\n"
            f"[bold]Q:[/bold] {q}\n"
            f"[bold]Wrong tries:[/bold] {wrongs}\n"
            f"[bold]Host:[/bold] {state.message}"
        )


class HostApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #top { height: 1fr; }
    #picker { width: 2fr; border: solid $accent; }
    #picker-title {
        dock: top; padding: 0 1; background: $accent; color: $text;
    }
    #filter { dock: top; margin: 0 1 1 1; }
    #stage { width: 3fr; layout: vertical; }
    #scoreboard { height: 3; padding: 1; border: solid $success; }
    #board { height: 1fr; padding: 1; border: solid $warning; }
    #status { height: 7; padding: 0 1; border: solid $primary; }
    #buzz { height: 12; border: solid $secondary; }
    ListView { height: 1fr; }
    """

    BINDINGS = [
        Binding("space", "advance", "Advance", show=True),
        Binding("enter", "select_question", "Select Q", show=True),
        Binding("r", "reveal", "Reveal", show=True),
        Binding("n", "next_pick", "Pick Q", show=True),
        Binding("slash", "focus_filter", "Filter", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    TITLE = "Family Feud — Host"
    SUB_TITLE = "Mode B · solo models · lockout buzz · BuzzFeed 115"

    def __init__(
        self,
        questions_path: str | Path = DEFAULT_QUESTIONS,
        *,
        limit: int | None = None,
        live: bool = False,
        contestants: list[str] | None = None,
    ) -> None:
        super().__init__()
        bank = load_question_bank(questions_path, limit=limit)
        if live:
            names = contestants or available_contestants() or list(DEFAULT_CONTESTANTS)
        else:
            names = contestants or list(DEFAULT_CONTESTANTS)
        self.state = new_match(bank, contestants=names, live=live)
        self._filter = ""
        self._visible_indices: list[int] = list(range(len(bank)))
        self._buzz_fn = make_buzz_fn(live=live)
        self._answer_fn = make_answer_fn(live=live)
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top"):
            with Vertical(id="picker"):
                yield Label("BuzzFeed questions", id="picker-title")
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
            used = index in self.state.used_questions
            if used:
                # Red + strikethrough so hosts see spent questions at a glance.
                label = (
                    f"[strike red]{index + 1:03d}  {question.text}[/strike red]"
                )
            else:
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
        mode = "LIVE" if self.state.live else "MOCK"
        buzz.write(f"[bold]{mode} face-off / play log[/bold]")
        if self.state.buzz_log:
            buzz.write("[bold]Buzz[/bold] (✓ hit · ✗ lockout)")
            for rank, event in enumerate(self.state.buzz_log, start=1):
                mark = "✓" if event.hit else "✗"
                matched = f" → {event.matched}" if event.matched else ""
                lock = " [lockout]" if event.locked_out else ""
                buzz.write(
                    f"{rank}. {mark} {event.model:<8} "
                    f"{event.text!r:<24} {event.latency_s:5.2f}s"
                    f"{matched}{lock}"
                )
        if self.state.play_log:
            buzz.write("[bold]Play[/bold]")
            for line in self.state.play_log[-8:]:
                buzz.write(f"• {line}")
        if not self.state.buzz_log and not self.state.play_log:
            buzz.write("[dim]Space starts the face-off.[/dim]")

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
        if self._busy:
            return
        before = set(self.state.used_questions)
        self.state = select_question(self.state, bank_index)
        # Rebuild list so the newly used question shows strikethrough.
        if self.state.used_questions != before or bank_index in self.state.used_questions:
            self._rebuild_question_list()
        self._refresh()

    def action_advance(self) -> None:
        if self._busy:
            return
        if self.state.phase == Phase.FACE_OFF_READY:
            self._run_face_off()
            return
        # Main play / steal may call live models — run in worker when live.
        if self.state.live and self.state.phase in {Phase.MAIN_PLAY, Phase.STEAL}:
            self._run_answer_step()
            return
        self.state = advance(
            self.state, buzz_fn=self._buzz_fn, answer_fn=self._answer_fn
        )
        self._refresh()

    @work(thread=True)
    def _run_face_off(self) -> None:
        self._busy = True
        self.state.phase = Phase.FACE_OFF_RUNNING
        self.state.message = "Buzzing models…"
        self.call_from_thread(self._refresh)
        try:
            self.state = self._buzz_fn(self.state)
        finally:
            self._busy = False
        self.call_from_thread(self._refresh)

    @work(thread=True)
    def _run_answer_step(self) -> None:
        self._busy = True
        self.state.message = "Model thinking…"
        self.call_from_thread(self._refresh)
        try:
            self.state = advance(
                self.state, buzz_fn=self._buzz_fn, answer_fn=self._answer_fn
            )
        finally:
            self._busy = False
        self.call_from_thread(self._refresh)

    def action_reveal(self) -> None:
        if self._busy:
            return
        self.state = reveal_next_host(self.state)
        self._refresh()

    def action_next_pick(self) -> None:
        if self._busy:
            return
        self.state.phase = Phase.PICK_QUESTION
        self.state.question = None
        self.state.buzz_log = []
        self.state.play_log = []
        self.state.wrong_guesses = []
        self.state.control = None
        self.state.steal_challenger = None
        self.state.strikes = 0
        self.state.round_points = 0
        used = len(self.state.used_questions)
        self.state.message = (
            f"Pick the next question ({used} already used — red/strike)."
        )
        self._rebuild_question_list()
        self._refresh()
        self.query_one("#question-list", ListView).focus()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()


def run(
    questions_path: str | Path = DEFAULT_QUESTIONS,
    *,
    limit: int | None = None,
    live: bool = False,
    contestants: list[str] | None = None,
) -> None:
    HostApp(
        questions_path,
        limit=limit,
        live=live,
        contestants=contestants,
    ).run()


if __name__ == "__main__":
    run()
