"""Twin Lab — `docs/06` §3. Eight sub-tabs, in the mandatory order of `docs/06` §0.

``Agents · Dial board · Twins · Validation · Validity tests · Fieldwork · Results · Settings``

Contracts this module must not break, each of which is an M10 acceptance criterion:

* **No LLM call in a handler's synchronous path** (`CLAUDE.md` rule 12, `docs/05` §8.4 rule 2).
  Every long action goes through a service function that enqueues and returns; the Timer polls.
* **`ui/` may import `services/` and `models/` only** — never `db/`, `agents/` or raw SQL
  (`ARCHITECTURE.md` §4). The import-linter is the first CI step.
* **Changing a dial does no network work.** One handler recomputes code, score and "what the
  twins are told" from reference data already in process (`docs/05` §8.4 rule 6).
* **`00000` is blocked from *Ask the twins*.** The button is disabled *and* the service refuses,
  so neither path alone is load-bearing (`docs/03` §6.1).
* **No metric is computed here.** Shifts, the index and the floors arrive already computed
  (`docs/05` §8.4 rule 5).
* **Evidence is never deletable from the UI** (I9): there is no "clear runs" control, and the
  Settings tab says so where the prototype had one.
"""

from __future__ import annotations

import logging
import time
from typing import NamedTuple

import gradio as gr

from config.settings import settings
from twinlab.models.reference import LEVER_NAMES

from ..components import (
    agent_card,
    answer_compare,
    app_header,
    budget_summary,
    data_table,
    dial_board_summary,
    dial_legend,
    empty_state,
    error_state,
    esc,
    global_nav,
    grid_243,
    interactions_panel,
    kv_table,
    load_js,
    load_once,
    log_tree,
    metric_bars,
    num,
    results_panel_html,
    scenario_text_block,
    section_title,
    side_panel,
    status_dot,
    sub_nav,
    twin_profile_card,
    verdict_pill,
)
from ..theme import page_classes

log = logging.getLogger(__name__)

_NOT_RUN = "Not run"

#: How often the Agents tab asks for new log rows **while a job is running**. It is off entirely
#: when nothing is (`ARCHITECTURE_UPDATE.md` §3.1 point 4).
#:
#: 5 s rather than the old 3 s, and the number is now the cheap half of the change: a tick whose
#: event stream has not moved issues two reads and touches no DOM at all. A twin call takes about
#: eight seconds, so 5 s still shows every step of a sweep as it happens.
POLL_SECONDS = 5.0

#: Bridges a click on a grid cell into the version-code textbox. The native value setter plus an
#: `input` event is what Gradio's Svelte binding listens for; assigning `.value` alone is ignored.
_GRID_CLICK_JS = """
() => {
  if (window.__tlGridBound) return;
  window.__tlGridBound = true;
  document.addEventListener("click", (event) => {
    const cell = event.target.closest(".tl-cell");
    if (!cell) return;
    const box = document.querySelector("#tl-grid-pick textarea, #tl-grid-pick input");
    if (!box) return;
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, "value"
    ).set || Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(box, cell.dataset.code);
    box.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
"""


def _row_click_js(target_id: str) -> str:
    """A click on a table row fills the textbox ``target_id``, the way a grid cell does.

    `gr.HTML` emits no events, so without this bridge a researcher has to re-type an opaque twin
    id out of the table to open it — which `CLAUDE.md` rule 8 makes a hazard rather than an
    inconvenience, and which `docs/05` §8.3 already forbids for the 243-grid for the same reason.
    Keyboard activation is handled too: the row is a `role="button"` with a tab stop, so a control
    that only answers a mouse would not be one.
    """
    return """
() => {
  const target = "__TARGET__";
  const flag = "__tlRowBound_" + target;
  if (window[flag]) return;
  window[flag] = true;
  const pick = (row) => {
    const box = document.querySelector("#" + target + " textarea, #" + target + " input");
    if (!box) return;
    const proto = box.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(box, row.dataset.key);
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const table = row.closest("table");
    if (table) table.querySelectorAll("tr.tl-row-on")
                    .forEach((r) => r.classList.remove("tl-row-on"));
    row.classList.add("tl-row-on");
  };
  const owned = (node) => {
    const row = node && node.closest ? node.closest("tr.tl-row-pick") : null;
    return row && row.closest("#" + target + "-table") ? row : null;
  };
  document.addEventListener("click", (event) => {
    const row = owned(event.target);
    if (row) pick(row);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = owned(event.target);
    if (row) { event.preventDefault(); pick(row); }
  });
}
""".replace("__TARGET__", target_id)


# ===================================================================== Agents


def _stored_population() -> str:
    """The default a population control opens on. §3.6: **the stored value**, never a guess.

    `sessions.population` defaults to `'real'` in the DDL and that is what the code has always
    used, so that is what is shown. It is a default the researcher can see and change, which is
    the whole point — it is not a study decision taken in code.

    Module-level because two screens now open a population control on it (the Agents tab and,
    from M19 WP-5, the Dial board). Two copies would be two defaults that could drift apart.
    """
    return "real"


class _LabSignals(NamedTuple):
    """Components the Lab tabs share, so one tab's action can wake another tab's refresh.

    ``ticker`` is the Agents tab's poll timer. It used to be private to that tab and only the three
    Agents buttons woke it, so a run started from the Dial board never reached the Agents page
    until a reload — the cards stayed on whatever they said at page load. ``run_done`` is a hidden
    value the poll writes when a session reaches a terminal state, which is what lets the Dial
    board and the Results tab repaint a finished run without a reload.
    """

    ticker: gr.Timer
    run_done: gr.Textbox


def _wake_ticker() -> gr.Timer:
    """Switch the Agents poll on. Wired to every control that starts a session."""
    return gr.Timer(POLL_SECONDS, active=True)


async def _cached_board(run: dict, code: str) -> str:
    """The metric bars for a completed run, the same whether it was just asked or just finished.

    **The floor is included.** `ARCHITECTURE.md` §5.2 requires `SHAM − 00000` beside every live
    cell, and a Dial board index with no floor statement invites exactly the reading the control
    cells exist to prevent.
    """
    from twinlab.services.metrics_view import build_metric_bars
    from twinlab.services.results import session_floor

    bars = build_metric_bars(
        (run.get("metrics") or {}).get("shifts"),
        index_value=run.get("index_value"),
        twins_n=int(run.get("twins_n") or 0),
        version_code=code,
        floor=await session_floor(),
    )
    return metric_bars(bars, cached=True)


def _agents_tab(signals: _LabSignals) -> None:
    """`docs/06` §3.1. Five cards, three workflow buttons **in order**, the log and the status."""
    from twinlab.services.menu import AGENT_CARDS
    from twinlab.services.runs import STOP_NOTE, WORKFLOW_BUTTONS

    gr.HTML(section_title("The five agents"))
    cards = gr.HTML(
        "".join(
            f'<div class="tl-card tl-agent-card"><div class="tl-agent-name">{esc(name)}</div>'
            f'<div class="tl-agent-role">{esc(role)}</div>'
            f'<div class="tl-agent-latest">Loading…</div></div>'
            for _, name, role in AGENT_CARDS
        ),
        elem_classes=["tl-card-grid"],
    )

    # The three buttons, in this exact order. Each opens a confirm step showing the budget
    # BEFORE anything starts (`docs/06` §9).
    with gr.Row():
        buttons = {
            key: gr.Button(
                label,
                variant="primary" if kind == "primary" else "secondary",
                elem_id=f"tl-workflow-{key}",
            )
            for key, label, kind in WORKFLOW_BUTTONS
        }

    with gr.Group(visible=False) as confirm:
        confirm_title = gr.Markdown("")
        confirm_budget = gr.HTML("")
        # `ARCHITECTURE_UPDATE.md` §3.6 — the non-blocking implementation of the still-open
        # question §1.3. The population is an explicit control, defaulting to **the current stored
        # value** and never silently changed by code, with the live counts beside it so the choice
        # is made against the data. A synthetic-only database is deliberately NOT defaulted to
        # `synthetic`: which population a study sweep runs on is the researcher's call.
        with gr.Row(visible=False) as population_row:
            population = gr.Radio(
                choices=["real", "synthetic", "both"],
                value="real",
                label="Which twins should answer?",
                elem_classes=["tl-toggle"],
            )
        population_line = gr.Markdown("", visible=False)
        readiness = gr.Markdown("")
        with gr.Row():
            confirm_go = gr.Button("Start", variant="primary")
            gr.Button("Cancel").click(lambda: gr.update(visible=False), outputs=confirm)
    pending = gr.State(None)

    async def _confirm(kind: str):
        """The budget, **before** anything starts (`docs/06` §9). No model call on this path.

        It also pre-flights the panel for a sweep (§3.5), so *Let the agents choose 6 versions*
        with no quality-passed twins says so here — in the page, beside the button — instead of
        creating a session row and dying in a background task.
        """
        from twinlab.services.config import load_twin_config
        from twinlab.services.lab import twin_rows
        from twinlab.services.runs import (
            check_eligibility,
            effective_panel_size,
            population_counts,
            quality_budget_view,
            sweep_budget_view,
        )

        cfg = load_twin_config()
        if kind == "quality":
            twins = len(await twin_rows())
            view = await quality_budget_view(twins=twins, repeats=cfg.quality_runs_per_twin)
            from twinlab.services.config_match import describe

            # RESEARCHER 2026-10-05: a verdict belongs to the config it was made under, so the
            # confirm step says which model and temperature these verdicts will be for.
            title = (
                f"Run the twin quality test on {twins:,} twins, "
                f"{cfg.quality_runs_per_twin} repeat(s) each, for {await describe()}"
            )
            # The gate is what *produces* quality-passed twins, so it has no panel and no
            # population: showing the control here would imply a choice that does not exist.
            return (
                gr.update(visible=True), f"### {title}", budget_summary(view),
                gr.update(visible=False), gr.update(visible=False), "", kind,
            )

        iterations = 6 if kind == "choose6" else 243
        title = (
            "Let the agents choose 6 versions" if kind == "choose6"
            else "Test all 243 versions"
        )
        view = await sweep_budget_view(iterations=iterations)
        stored = _stored_population()
        ready = await check_eligibility(stored, effective_panel_size())
        note = (
            f"**Not ready.** {ready['reason']}" if not ready["ok"]
            else (
                f"{ready['eligible']} twin(s) eligible for a panel of {ready['panel_size']}, "
                f"qualified for {ready['config_model']} at temperature "
                f"{float(ready['config_temperature']):g}."
            )
        )
        return (
            gr.update(visible=True),
            f"### {title}",
            budget_summary(view),
            gr.update(visible=True),
            gr.update(visible=True, value=await population_counts()),
            note,
            kind,
        )

    for key, button in buttons.items():
        button.click(
            _confirm,
            inputs=gr.State(key),
            outputs=[
                confirm, confirm_title, confirm_budget,
                population_row, population_line, readiness, pending,
            ],
        )

    async def _recheck(chosen: str) -> str:
        """Re-pre-flight when the researcher changes the population. One read, no writes.

        Without this the readiness line would describe the population they just moved away from,
        which is worse than no line at all.
        """
        from twinlab.services.runs import check_eligibility, effective_panel_size

        ready = await check_eligibility(chosen, effective_panel_size())
        if ready["ok"]:
            return f"{ready['eligible']} twin(s) eligible for a panel of {ready['panel_size']}."
        return f"**Not ready.** {ready['reason']}"

    population.change(_recheck, inputs=population, outputs=readiness)

    async def _start(kind: str | None, chosen_population: str):
        """Hand the job to the loop and return. **No model call in this function.**

        Each of the three creates a real row and a real background task, so the log below starts
        moving within a tick. `CLAUDE.md` rule 12: the LLM work never runs in a handler's
        synchronous path — `start_quality_gate` and `start_sweep` both enqueue and return.

        `NotReadyToSweep` joins `SessionAlreadyRunning` on the already-clean refusal path (§3.5):
        it is raised *before* any `sessions` row is written, so a refusal leaves nothing behind.
        """
        from twinlab.services.quality import QualityGateError, start_quality_gate
        from twinlab.services.runs import (
            NotReadyToSweep,
            SessionAlreadyRunning,
            start_sweep,
        )

        if kind is None:
            return gr.update(visible=False), "No job selected."
        pop = chosen_population or _stored_population()
        try:
            if kind == "quality":
                session = await start_quality_gate()
                what = "the quality gate"
            elif kind == "choose6":
                session = await start_sweep(
                    iterations=6, name="Six versions", population=pop
                )
                what = f"six versions on {pop} twins"
            else:
                session = await start_sweep(
                    iterations=243, name="All 243 versions", population=pop
                )
                what = f"all 243 versions on {pop} twins"
        except (QualityGateError, SessionAlreadyRunning, NotReadyToSweep) as exc:
            # Deliberately leaves the confirm panel open: the researcher's next move is usually to
            # change the population right there, not to find the button again.
            return gr.update(visible=True), f"**Not started.** {exc}"
        except Exception as exc:  # noqa: BLE001 — say why, rather than a silent dead button
            return gr.update(visible=True), (
                f"**Not started.** {type(exc).__name__}: {exc}"
            )
        return gr.update(visible=False), (
            f"Started {what} as session `{session.session_id[:8]}`. Watch it below; it continues "
            "if you change tab."
        )

    gr.HTML(section_title("Run without watching"))
    job_line = gr.Markdown("")
    confirm_go.click(_start, inputs=[pending, population], outputs=[confirm, job_line])
    with gr.Row():
        stop_button = gr.Button("Stop the running job", variant="stop")
        resume_button = gr.Button("Resume the last paused job", variant="secondary")
    stop_note = gr.Markdown("")
    gr.Markdown(STOP_NOTE)

    async def _stop():
        """Cooperative, and it says which mechanism answered.

        A sweep is stopped through the orchestrator's registry and the quality gate through its
        own, because the gate is not a `SessionRunner` — it has no cells and no cursor. Reporting
        `False` as "stopped" would be the worst outcome: a researcher who expects a kill presses
        twice and then assumes it is broken (`ARCHITECTURE.md` §7.4).
        """
        from twinlab.services.quality import active_gate
        from twinlab.services.quality import request_stop as stop_gate
        from twinlab.services.runs import latest_session_id, stop

        gate = active_gate()
        if gate is not None and stop_gate(gate):
            return "Stop requested. The current twin finishes, then the gate pauses."
        session_id = await latest_session_id()
        if session_id and stop(session_id):
            return (
                "Stop requested. The current twin call finishes, then the session pauses at its "
                "next checkpoint and can be resumed from where it stopped."
            )
        return (
            "**Nothing is running in this process.** A session left `running` by a restart was "
            "marked `paused` at boot and can be resumed."
        )

    async def _resume():
        """Resume is just start (`docs/04` §3.4): the cursor and the frozen panel are both stored.

        Nothing already paid for is re-paid — `answered_twins` skips whoever answered, and the
        paragraph and variant caches survive the restart.
        """
        from twinlab.services.runs import (
            NotReadyToSweep,
            SessionAlreadyRunning,
            paused_sessions,
            resume_session,
        )

        paused = await paused_sessions()
        if not paused:
            return "**Nothing to resume.** No session is paused."
        # `paused_sessions` is newest first. It used to be sorted by uuid, so `[-1]` resumed an
        # arbitrary old session rather than the one the researcher had just stopped.
        newest = paused[0]
        try:
            await resume_session(newest.session_id)
        except (SessionAlreadyRunning, NotReadyToSweep) as exc:
            # `ARCHITECTURE_UPDATE.md` §3.5's diagnostic: a session that died before its panel was
            # drawn fails identically on every press. It is refused here, in the page, rather than
            # spawning a task that logs to a console nobody is reading.
            return f"**Not resumed.** {exc}"
        return (
            f"Resumed `{newest.session_id[:8]}` ({newest.name}) at cell "
            f"{newest.completed + 1} of {newest.iterations}."
        )

    stop_button.click(_stop, outputs=stop_note)
    resume_button.click(_resume, outputs=stop_note)

    gr.HTML(section_title("What the agents said"))
    log = gr.HTML(empty_state("No agent messages yet.", "Start a job to see the run appear."))
    cursor = gr.State(0)
    rendered = gr.State([])

    session_state = gr.State(None)
    #: What the last tick saw, per output. An unchanged entry means that output's DOM subtree is
    #: left alone — see `_poll`.
    fingerprint = gr.State({})

    gr.HTML(section_title("Status"))
    status_card = gr.HTML("")
    #: **Off when nothing is running.** `ARCHITECTURE_UPDATE.md` §3.1 point 4: an idle Agents page
    #: must make zero database calls. The three workflow buttons, Stop and Resume all switch it on,
    #: and `_poll` switches it off again once the session it is watching reaches a terminal state.
    ticker = signals.ticker

    async def _poll(after_id: int, seen: list, watching: str | None, seen_fp: dict):
        """Incremental, and **idempotent in the DOM**. `docs/04` §7.3, `ARCHITECTURE_UPDATE.md`
        §3.1.

        ``watching`` is the session whose rows are already rendered. When a **new** session starts
        the cursor and the rendered tree are reset, because appending a second session's rows to
        the first one's tree would show two runs as one — and the parent ids would not resolve.

        The fingerprint is the fix for the real defect. This handler had seven outputs, including
        the whole log-tree HTML and the agent-card HTML, and Gradio replaces every returned output's
        DOM subtree whether its value changed or not: scroll position reset, open elements
        collapsed and focus was lost every three seconds, forever, on an idle page. So each output
        is now compared against what the last tick produced for it and `gr.skip()`-ed when it has
        not moved — and when the event stream itself has not moved, the three expensive reads
        behind the cards, the status card and the job line are not even issued.

        `docs/06` §3.1 asks for a job line kept current; nothing there asks for a full re-render
        every three seconds (`docs/DECISIONS.md`, 2026-10-01).
        """
        from twinlab.services.menu import agent_cards
        from twinlab.services.runs import events_since, latest_session_id, running_job_line
        from twinlab.services.status import lab_status

        before = dict(seen_fp or {})
        session_id = await latest_session_id()
        fresh = session_id != watching
        if fresh:
            after_id, seen = 0, []
        new = await events_since(session_id, after_id) if session_id else []
        merged = list(seen) + list(new)
        next_id = max([e.event_id for e in merged], default=after_id)

        session = None
        if session_id is not None:
            from twinlab.services.runs import get_session

            session = await get_session(session_id)
        live = session is not None and session.status in ("running", "created")
        # **Switching off is unconditional; switching on is not.** Returning `active=True` on every
        # tick would restart the interval on every tick, so that one is gated on the state having
        # changed. `active=False` is idempotent and must not be gated: the three buttons wake the
        # timer directly, so after a refused start — `NotReadyToSweep`, with no session row
        # created —
        # the fingerprint already reads `live: False` and a gated update would leave the timer
        # running for ever. Measured: one `select sessions` every 5 s, indefinitely, on a page where
        # nothing had started. That is the §3.1 defect in miniature, reintroduced by its own fix.
        if not live:
            timer = gr.Timer(POLL_SECONDS, active=False)
        elif before.get("live") is True:
            timer = gr.skip()
        else:
            timer = gr.Timer(POLL_SECONDS, active=True)

        after: dict = {"log": [session_id, next_id], "live": live}
        # A live → finished transition is the moment the Dial board and Results must repaint. It is
        # checked **before** the early return below, because a session can finish without writing a
        # new event (`set_status` on the parent row changes no id), and a check placed after the
        # return would miss it. The timestamp makes each finish a distinct value, so Gradio fires
        # `.change` again even for a re-run of the same session.
        finished = before.get("live") is True and session is not None and not live
        done = f"{session_id}:{session.status}:{time.time_ns()}" if finished else gr.skip()
        if not fresh and before.get("log") == after["log"]:
            # Nothing moved. **No further reads**, and not one DOM subtree is touched.
            return (
                gr.skip(), gr.skip(), gr.skip(), gr.skip(),
                gr.skip(), gr.skip(), gr.skip(),
                {**before, **after},
                timer,
                done,
            )

        cards_html = "".join(agent_card(a) for a in await agent_cards())
        status_html = kv_table(
            [(r.label, esc(r.value)) for r in await lab_status()], caption="Status"
        )
        job = _job_line(session, len(await _tested()), running_job_line)
        after |= {"cards": cards_html, "status": status_html, "job": job}

        def moved(key: str, value):
            return value if before.get(key) != value else gr.skip()

        return (
            log_tree(merged)
            if merged
            else empty_state("No agent messages yet.", "Start a job to see the run appear."),
            next_id,
            merged,
            session_id,
            moved("cards", cards_html),
            moved("status", status_html),
            moved("job", job),
            {**before, **after},
            timer,
            done,
        )

    async def _tested():
        from twinlab.services.status import tested_codes

        return await tested_codes()

    def _job_line(session, tested: int, render) -> str:
        """`docs/06` §3.1's current-job line. Pure: the session row is already in hand.

        It used to fetch the session itself, which meant the job line cost a read on every tick
        even when the tick had nothing to say.
        """
        if session is None:
            return render(None, tested)
        if session.kind == "quality":
            # A quality session has no cells and no cursor, so `running_job_line`'s "x of y
            # versions" would be a count of nothing. It reports twins instead.
            if session.status in ("running", "created"):
                return (
                    f"Running {session.name}: {session.completed} of {session.panel_size} "
                    f"twin(s) scored."
                )
            return f"{session.name} — {session.status}. Versions tested so far: {tested}."
        if session.kind == "studio":
            # A Studio ask is one twin and one cell, so `running_job_line`'s "x of y done" would
            # read "0 of 1" throughout and "1 of 1" for an instant. It names the twin instead.
            if session.status in ("running", "created"):
                return f"Running {session.name}. Watch it below."
            return f"{session.name} — {session.status}. Versions tested so far: {tested}."
        if session.kind == "render":
            # A Twin Studio render (`ARCHITECTURE_UPDATE.md` §4.2) has no cells and no panel, so
            # `running_job_line`'s "x of y versions" would read "0 of 0 done". It reports itself.
            if session.status in ("running", "created"):
                return f"Running {session.name}. Watch the render below."
            return f"{session.name} — {session.status}. Versions tested so far: {tested}."
        return render(session, tested)

    poll_outputs = [
        log, cursor, rendered, session_state, cards, status_card, job_line,
        fingerprint, ticker, signals.run_done,
    ]
    ticker.tick(
        _poll,
        inputs=[cursor, rendered, session_state, fingerprint],
        outputs=poll_outputs,
    )
    # One render at page load, then silence until something is started. `load_once` is a `.load`
    # handler, so this is the only read an untouched Agents tab ever makes.
    load_once(
        _poll,
        inputs=[cursor, rendered, session_state, fingerprint],
        outputs=poll_outputs,
    )
    # Starting, stopping or resuming wakes the timer. The Dial board and Rerun also start sessions,
    # and they wake it from their own tab (`_dial_board_tab`) — before, they did not, so a run
    # started there left these cards frozen until a reload.
    for trigger in (confirm_go, stop_button, resume_button):
        trigger.click(_wake_ticker, outputs=ticker)


# ================================================================= Dial board


def _dial_board_tab(signals: _LabSignals) -> None:
    """`docs/06` §3.2. **Changing a dial does no network work.**"""
    from twinlab.services.dials import CONTROL_REASON, LEVER_ORDER

    with gr.Row():
        with gr.Column(scale=5):
            gr.HTML(section_title("Dials"))
            gr.HTML(dial_legend())
            radios = {
                lever: gr.Radio(
                    choices=[("0 today", 0), ("1 some", 1), ("2 more", 2)],
                    value=0,
                    label=LEVER_NAMES[lever],
                    elem_classes=["tl-dial-row"],
                )
                for lever in LEVER_ORDER
            }
            ask = gr.Button("Ask the twins", variant="primary", interactive=False)
            gr.Markdown(CONTROL_REASON, elem_classes=["tl-dial-note"])
        with gr.Column(scale=4):
            summary = gr.HTML("")

    # M19 WP-5. *Ask the twins* used to call `ask_twins(code)` with no population and no panel
    # size, so on an all-synthetic database it always refused — naming a population control that
    # existed only on the Agents tab. It also started a session with **no cost shown**, which
    # `docs/06` §9 requires of every long action and which the Agents, Twins and Validity tabs
    # already do. Both are fixed by giving this button the same confirm step they have.
    with gr.Group(visible=False) as dial_confirm:
        dial_confirm_title = gr.Markdown("")
        dial_budget = gr.HTML("")
        with gr.Row():
            dial_population = gr.Radio(
                choices=["real", "synthetic", "both"],
                value="real",
                label="Which twins should answer?",
                elem_classes=["tl-toggle"],
            )
            # Reading (b) of the plan's Q3, confirmed by the researcher: the panel is **frozen at
            # the chosen size**, so every cell in the session is answered by the same twins and
            # the indices stay differenceable against each other and against the 00000 and SHAM
            # floors (I14). A census with no frozen panel would be cheaper to look at and
            # impossible to difference.
            dial_panel_size = gr.Number(
                value=settings.panel_size,
                precision=0,
                minimum=1,
                label="How many twins",
            )
            dial_every = gr.Checkbox(value=False, label="Use every eligible twin")
        dial_counts = gr.Markdown("")
        dial_readiness = gr.Markdown("")
        with gr.Row():
            dial_go = gr.Button("Start", variant="primary")
            gr.Button("Cancel").click(
                lambda: gr.update(visible=False), outputs=dial_confirm
            )

    results = gr.HTML("")
    rerun_row = gr.Row(visible=False)
    with rerun_row:
        rerun_button = gr.Button("Rerun?", variant="secondary", elem_id="tl-rerun")
        rerun_note = gr.Markdown("")
    cached_session = gr.State(None)

    def _on_dial(*values: int):
        """Pure and synchronous: a lookup over frozen data already in memory (I1).

        This handler must not grow a database read or a model call. `docs/05` §8.4 rule 6 makes
        "it must feel instant" a contract, not a preference.
        """
        from twinlab.services.dials import dial_board

        board = dial_board(dict(zip(LEVER_ORDER, values, strict=True)))
        return (
            dial_board_summary(board),
            # `00000` is a control the orchestrator runs, not a cell to poke at.
            gr.update(interactive=not board.is_control),
        )

    inputs = [radios[lever] for lever in LEVER_ORDER]
    for radio in inputs:
        radio.change(_on_dial, inputs=inputs, outputs=[summary, ask])

    async def _eligible_count(population: str) -> int:
        """How many twins *could* answer. One read, no writes."""
        from twinlab.services.runs import check_eligibility

        # `panel_size=1` asks only "is there anybody", so the count comes back whether or not the
        # researcher's chosen size is satisfiable.
        ready = await check_eligibility(population, 1)
        return int(ready.get("eligible") or 0)

    async def _resolve_size(population: str, size: float | None, every: bool) -> int:
        """The panel size this confirm step would actually freeze onto the session."""
        if every:
            return await _eligible_count(population)
        return max(int(size or 0), 0)

    async def _dial_readiness_line(population: str, size: int) -> str:
        from twinlab.services.runs import check_eligibility

        if size <= 0:
            return (
                "**Not ready.** No twins selected. A run with no twins is a failure, never a "
                "result with an index of 0.000 (I15)."
            )
        ready = await check_eligibility(population, size)
        if ready["ok"]:
            return (
                f"{ready['eligible']} twin(s) eligible for {ready['config_model']} at temperature "
                f"{float(ready['config_temperature']):g}; the panel will be frozen at "
                f"{ready['panel_size']} and every cell in this session uses those same twins "
                "(I14). The 00000 and SHAM floors come from each twin's quality test, so this "
                "run asks only its versions."
            )
        return f"**Not ready.** {ready['reason']}"

    async def _open_confirm(*values: int):
        """The cost and the population, **before** a session row exists. No model call. WP-5.

        Nothing here writes: `check_eligibility` and the budget are both pure reads, so cancelling
        leaves no trace (`docs/06` §9).
        """
        from twinlab.services.dials import code_from_dials
        from twinlab.services.runs import (
            effective_panel_size,
            population_counts,
            sweep_budget_view,
        )

        code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
        population = _stored_population()
        size = effective_panel_size()
        view = await sweep_budget_view(iterations=1, panel_size=size, start_code=code)
        return (
            gr.update(visible=True),
            f"### Ask the twins for `{code}`",
            budget_summary(view),
            gr.update(value=population),
            gr.update(value=size),
            gr.update(value=False),
            await population_counts(),
            await _dial_readiness_line(population, size),
        )

    async def _recost(population: str, size: float | None, every: bool, *values: int):
        """Re-cost and re-pre-flight when any of the three controls moves. Reads only."""
        from twinlab.services.dials import code_from_dials
        from twinlab.services.runs import sweep_budget_view

        resolved = await _resolve_size(population, size, every)
        code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
        view = await sweep_budget_view(
            iterations=1, panel_size=max(resolved, 1), start_code=code
        )
        return (
            budget_summary(view),
            gr.update(value=resolved) if every else gr.update(),
            await _dial_readiness_line(population, resolved),
        )

    async def _ask(population: str, size: float | None, every: bool, *values: int):
        """`docs/04` §6.1's contract. **No model call on this path.**

        A cache hit renders immediately and offers *Rerun?*; a miss creates a real session and
        starts it in the background, so its log appears like any other run. `00000` is refused by
        the service as well as by the disabled button — neither path alone is load-bearing
        (`docs/03` §6.1).

        The population and the panel size the researcher chose are passed through explicitly
        (WP-5). `ask_twins` has always taken both; this screen simply never supplied them, so it
        ran against `population='real'` and `settings.panel_size` whatever was on the screen.
        """
        from twinlab.services.dials import code_from_dials
        from twinlab.services.runs import (
            ControlCellError,
            NotReadyToSweep,
            SessionAlreadyRunning,
            ask_twins,
            cached_run,
        )

        code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
        run = await cached_run(code)
        if run is not None:
            return (
                await _cached_board(run, code),
                gr.update(visible=True),
                run.get("session_id"),
                gr.update(visible=False),
            )
        resolved = await _resolve_size(population, size, every)
        try:
            session = await ask_twins(
                code, population=population, panel_size=resolved
            )
        except (ControlCellError, NotReadyToSweep, SessionAlreadyRunning) as exc:
            return (
                error_state("Nothing was started.", type(exc).__name__, str(exc)[:300]),
                gr.update(visible=False),
                None,
                gr.update(visible=False),
            )
        except Exception as exc:  # noqa: BLE001 — a dead button is worse than a named failure
            return (
                error_state("Nothing was started.", type(exc).__name__, str(exc)[:300]),
                gr.update(visible=False),
                None,
                gr.update(visible=False),
            )
        return (
            f'<div class="tl-note tl-note-ok"><strong>Started {esc(code)} as session '
            f"{esc(session.session_id[:8])}.</strong><div>{resolved} twin(s) from the "
            f"<strong>{esc(population)}</strong> population, frozen as this session's panel. "
            "It runs in the background and continues if you change tab. Watch it in "
            "<strong>Agents → What the agents said</strong>; the result lands here and on the "
            "Results tab when it finishes.</div></div>",
            gr.update(visible=False),
            session.session_id,
            gr.update(visible=False),
        )

    async def _rerun(session_id: str | None, *values: int):
        """A rerun **inherits the original session's panel** (I14).

        A rerun answered by a different set of twins is not a rerun; it is a different experiment
        wearing the same version code. `services.runs.rerun` defaults to inheriting, and this
        passes the originating session rather than letting it default to a fresh draw.

        It deliberately takes **neither** the population nor the panel size from the confirm step
        above: both are inherited, and letting a rerun take new values is exactly the thing I14
        forbids.
        """
        from twinlab.services.dials import code_from_dials
        from twinlab.services.runs import (
            ControlCellError,
            NotReadyToSweep,
            SessionAlreadyRunning,
            ask_twins,
            rerun,
        )

        code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
        try:
            session = (
                await rerun(code, original_session_id=session_id)
                if session_id
                else await ask_twins(code)
            )
        except (ControlCellError, NotReadyToSweep, SessionAlreadyRunning) as exc:
            return f"**Not started.** {exc}"
        except Exception as exc:  # noqa: BLE001 — say why rather than a dead button
            return f"**Not started.** {type(exc).__name__}: {exc}"
        inherited = (
            "It inherits the original session's panel, so it is the same twins (I14)."
            if session_id
            else "No earlier session to inherit a panel from, so a fresh panel was drawn."
        )
        return (
            f"Started `{session.session_id[:8]}` for **{code}**. {inherited} "
            "Watch it in Agents → What the agents said."
        )

    async def _refresh_board(_done: str, *values: int):
        """Repaint a finished run on the board, with no reload. Reads only, and only on a finish.

        Before, the board showed a result only when *Start* found it cached, so a run that finished
        while the researcher watched it did not appear here until the page was reloaded.
        """
        from twinlab.services.dials import code_from_dials
        from twinlab.services.runs import cached_run

        code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
        run = await cached_run(code)
        if run is None:
            return gr.skip(), gr.skip(), gr.skip()
        return (
            await _cached_board(run, code),
            gr.update(visible=True),
            run.get("session_id"),
        )

    rerun_button.click(_rerun, inputs=[cached_session, *inputs], outputs=rerun_note)
    # Starting a session from here wakes the Agents poll, so its cards and log move as it runs.
    dial_go.click(_wake_ticker, outputs=signals.ticker)
    rerun_button.click(_wake_ticker, outputs=signals.ticker)
    signals.run_done.change(
        _refresh_board,
        inputs=[signals.run_done, *inputs],
        outputs=[results, rerun_row, cached_session],
    )
    # The button now opens the confirm step; *Start* inside it is what asks.
    ask.click(
        _open_confirm,
        inputs=inputs,
        outputs=[
            dial_confirm, dial_confirm_title, dial_budget, dial_population,
            dial_panel_size, dial_every, dial_counts, dial_readiness,
        ],
    )
    recost_inputs = [dial_population, dial_panel_size, dial_every, *inputs]
    recost_outputs = [dial_budget, dial_panel_size, dial_readiness]
    dial_population.change(_recost, inputs=recost_inputs, outputs=recost_outputs)
    dial_panel_size.change(_recost, inputs=recost_inputs, outputs=recost_outputs)
    dial_every.change(_recost, inputs=recost_inputs, outputs=recost_outputs)
    dial_go.click(
        _ask,
        inputs=recost_inputs,
        outputs=[results, rerun_row, cached_session, dial_confirm],
    )
    # Paint the initial state once. It reads the radios rather than assuming zeros, and it stops
    # after the first tick -- a repeating timer would overwrite every dial the researcher moves.
    load_once(_on_dial, inputs=inputs, outputs=[summary, ask])


# ===================================================================== Twins


def _twins_tab() -> None:
    """`docs/06` §3.3. The side panel's seven steps are in their mandatory order.

    Two things here are the screen's whole job. A row **opens the twin it names**: the twin id is
    opaque by design (`CLAUDE.md` rule 8), so a table a researcher has to re-type a key out of is
    a table that gets read wrong. And *Run twin quality test* runs the gate on **the twins the
    filters currently select**, so a researcher can test two twins before committing to five
    hundred — which is the difference between an 18-call check and a twenty-hour one (`docs/10`).
    """
    quality = gr.Button(
        "Run twin quality test →", variant="primary", elem_id="tl-quality-page"
    )
    with gr.Group(visible=False) as q_confirm:
        q_title = gr.Markdown("")
        q_budget = gr.HTML("")
        with gr.Row():
            q_go = gr.Button("Start", variant="primary")
            gr.Button("Cancel").click(lambda: gr.update(visible=False), outputs=q_confirm)
    q_note = gr.Markdown("")

    with gr.Row():
        with gr.Column(scale=5):
            with gr.Row():
                f_source = gr.Dropdown(
                    ["", "real", "synthetic", "manual"], value="", label="Source"
                )
                f_city = gr.Textbox(label="City")
                f_service = gr.Textbox(label="Service")
                f_quality = gr.Dropdown(
                    ["", "kept", "dropped", "not_run"], value="", label="Quality"
                )
            twin_table = gr.HTML("")
            selected_line = gr.Markdown("")
            picked = gr.Textbox(
                label="Twin id",
                placeholder="Click a row above, or type a twin id",
                elem_id="tl-twin-pick",
                info="Clicking a row fills this and opens the twin on the right.",
            )

            # Deleting twins. **A `gr.CheckboxGroup`, not checkboxes in the table above**: that
            # table is `gr.HTML`, and Gradio gives no way to read a tick out of rendered markup.
            # The degradation is in the styling rather than the content (`CLAUDE.md`) — the boxes
            # list exactly the twins the filters select, so the selection is still made by
            # ticking, and `docs/DECISIONS.md` records the choice.
            with gr.Accordion("Delete twins", open=False):
                gr.Markdown(
                    "Tick the twins to delete. This removes the twin **and the survey it was "
                    "built from**, real or synthetic — unlike the Generator's *delete all "
                    "synthetic*, which can never touch a real row. Narrow the list with the "
                    "filters above."
                )
                d_pick = gr.CheckboxGroup([], label="Twins", value=[])
                d_all = gr.Button("Select all shown", size="sm")
                d_button = gr.Button("Delete selected", elem_classes=["tl-btn-danger"])
                with gr.Group(visible=False) as d_confirm:
                    d_line = gr.Markdown("")
                    d_purge = gr.Checkbox(
                        label=(
                            "Also withdraw their sessions, runs and validity results "
                            "(required when a twin has answered a run)"
                        ),
                        value=False,
                        visible=False,
                    )
                    d_keep_survey = gr.Checkbox(
                        label="Keep the surveys, delete only the twins (lets you re-import)",
                        value=False,
                    )
                    with gr.Row():
                        d_go = gr.Button("Delete them", elem_classes=["tl-btn-danger"])
                        gr.Button("Cancel").click(
                            lambda: gr.update(visible=False), outputs=d_confirm
                        )
                d_note = gr.Markdown("")
        with gr.Column(scale=4):
            compare = gr.Dropdown([], label="Compare with version", value=None)
            panel = gr.HTML("")

    async def _list(source: str, city: str, service: str, quality: str):
        from twinlab.services.lab import comparable_codes, twin_rows

        rows = await twin_rows(
            source=source or None,
            city=city or None,
            service=service or None,
            quality=quality or None,
        )
        table = data_table(
            ["Twin", "Service", "City", "Age", "Quality"],
            [
                [
                    esc(r.twin_id),
                    esc(r.service),
                    esc(r.city),
                    esc(r.age),
                    status_dot(r.quality_state, r.quality_text),
                ]
                for r in rows
            ],
            empty=empty_state(
                "No twins yet.",
                "Import twins from the survey in the Settings tab.",
            ),
            row_keys=[r.twin_id for r in rows],
        )
        return (
            f'<div id="tl-twin-pick-table">{table}</div>',
            gr.update(choices=await comparable_codes()),
            f"{len(rows):,} {'twin' if len(rows) == 1 else 'twins'} selected by these filters.",
            # The delete list follows the filters, and the ticks are cleared when it does: a
            # selection left over from a previous filter is a selection the researcher can no
            # longer see, and this button deletes things.
            gr.update(
                choices=[(f"{r.twin_id} · {r.source}", r.twin_id) for r in rows], value=[]
            ),
        )

    filters = [f_source, f_city, f_service, f_quality]
    for control in filters:
        control.change(
            _list, inputs=filters, outputs=[twin_table, compare, selected_line, d_pick]
        )

    async def _select_all(source: str, city: str, service: str, quality: str):
        from twinlab.services.lab import twin_rows

        rows = await twin_rows(
            source=source or None,
            city=city or None,
            service=service or None,
            quality=quality or None,
        )
        return gr.update(value=[r.twin_id for r in rows])

    d_all.click(_select_all, inputs=filters, outputs=d_pick)

    async def _ask_twin_delete(chosen: list[str]):
        """The cost of **this** selection, before the button is live. `docs/06` §9.

        The collateral line is the one that matters: deleting two twins can require withdrawing a
        session that forty others answered, and a researcher who finds that out afterwards has
        lost evidence they never agreed to lose.
        """
        from twinlab.services.surveys import twin_delete_preflight

        if not chosen:
            return gr.update(visible=False), "", gr.update(visible=False), "Nothing ticked."

        pre = await twin_delete_preflight(list(chosen))
        real = pre["real_twin_ids"]
        line = f"### Delete {len(pre['twin_ids'])} twin(s)?\n"
        if real:
            line += (
                f"**{len(real)} of them are real respondents** "
                f"({', '.join(real[:5])}). Their surveys go too unless you keep them below.\n\n"
            )
        if pre["blocked_twin_ids"]:
            rows = {s["session_id"]: s for s in pre["dependent_sessions"]}
            named = ", ".join(f"*{r['name']}* ({r['runs_n']} run(s))" for r in rows.values())
            line += (
                f"{len(pre['blocked_twin_ids'])} of them **are evidence** in {named}. A twin "
                "cannot leave behind a stored result that was computed over it, so those "
                "sessions and their validity verdicts have to be withdrawn as well."
            )
            if pre["collateral_twin_ids"]:
                line += (
                    f"\n\n⚠️ **That also withdraws {len(pre['collateral_twin_ids'])} other "
                    f"twin(s)' answers** from those sessions "
                    f"({', '.join(pre['collateral_twin_ids'][:6])}"
                    + (" …" if len(pre["collateral_twin_ids"]) > 6 else "")
                    + "). Those twins are **not** deleted — they lose the run they answered."
                )
        return (
            gr.update(visible=True),
            line,
            gr.update(visible=bool(pre["blocked_twin_ids"]), value=False),
            "",
        )

    async def _do_twin_delete(chosen: list[str], purge: bool, keep_surveys: bool):
        from twinlab.services.surveys import DeleteBlocked, delete_twins

        try:
            removed = await delete_twins(
                list(chosen),
                purge_sessions=bool(purge),
                delete_surveys=not bool(keep_surveys),
            )
        except DeleteBlocked as exc:
            return gr.update(visible=True), f"**Nothing was deleted.** {exc}"
        note = f"Deleted {removed['twins']:,} twin(s)"
        if removed["submissions"]:
            note += f" and {removed['submissions']:,} survey(s)"
        purged = removed.get("purged") or {}
        if purged:
            note += (
                f". **Withdrew {purged.get('sessions', 0):,} session(s)**: "
                + ", ".join(
                    f"{n:,} {t.replace('_', ' ')}"
                    for t, n in sorted(purged.items())
                    if t != "sessions"
                )
            )
        return gr.update(visible=False), note + "."

    d_button.click(
        _ask_twin_delete, inputs=d_pick, outputs=[d_confirm, d_line, d_purge, d_note]
    )
    d_go.click(
        _do_twin_delete,
        inputs=[d_pick, d_purge, d_keep_survey],
        outputs=[d_confirm, d_note],
    )

    async def _confirm_quality(source: str, city: str, service: str, quality: str):
        """The budget **for the twins these filters select**, before anything starts (`docs/06` §9).

        The gate is the study's dominant cost — 18 calls per twin at the default three repeats
        (`docs/10`) — so the count it would run on is shown, not the whole population's.
        """
        from twinlab.services.config import load_twin_config
        from twinlab.services.lab import twin_rows
        from twinlab.services.runs import quality_budget_view

        rows = await twin_rows(
            source=source or None,
            city=city or None,
            service=service or None,
            quality=quality or None,
        )
        repeats = load_twin_config().quality_runs_per_twin
        view = await quality_budget_view(twins=len(rows), repeats=repeats)
        if not rows:
            return (
                gr.update(visible=True),
                "### No twins match these filters\n"
                "Nothing would be tested.",
                budget_summary(view),
            )
        return (
            gr.update(visible=True),
            f"### Run the twin quality test on {len(rows):,} twin(s)\n"
            f"Six Part 17 versions × {repeats} repeat(s) each, scored against each twin's own "
            "driver, plus the two control answers (00000, SHAM) per twin. A twin below threshold "
            "is dropped, not tuned. Verdicts are for the config shown in the budget.",
            budget_summary(view),
        )

    quality.click(
        _confirm_quality, inputs=filters, outputs=[q_confirm, q_title, q_budget]
    )

    async def _start_quality(source: str, city: str, service: str, quality_filter: str):
        """Hand the gate to the event loop and return. **No model call on this path.**"""
        from twinlab.services.lab import twin_rows
        from twinlab.services.quality import QualityGateError, start_quality_gate

        rows = await twin_rows(
            source=source or None,
            city=city or None,
            service=service or None,
            quality=quality_filter or None,
        )
        if not rows:
            return gr.update(visible=False), "**Not started.** No twins match these filters."
        try:
            session = await start_quality_gate(twin_ids=[r.twin_id for r in rows])
        except QualityGateError as exc:
            return gr.update(visible=False), f"**Not started.** {exc}"
        return gr.update(visible=False), (
            f"Started on {len(rows):,} twin(s) as session `{session.session_id[:8]}`. "
            "Watch it in **Agents → What the agents said**; it continues if you change tab. "
            "Re-apply the filters here to see the verdicts land."
        )

    q_go.click(_start_quality, inputs=filters, outputs=[q_confirm, q_note])

    async def _open(twin_id: str, code: str | None):
        """Steps 1-7 in order. Scenario text precedes the answers, deliberately."""
        from twinlab.services.lab import twin_panel

        if not twin_id:
            return ""
        view = await twin_panel(twin_id, version_code=code or None)
        body = (
            twin_profile_card(view)
            + section_title("Reconstructed persona")
            + _persona_html(view)
            + section_title("Scenario text")
            + scenario_text_block(view.scenario_text)
            + section_title("Answer comparison")
            + (
                empty_state(
                    f"{code} is not tested for this twin.",
                    "Ask the twins for this version first.",
                )
                if view.not_tested
                else ""
            )
            + answer_compare(view)
        )
        return side_panel(view.twin_id, body)

    picked.change(_open, inputs=[picked, compare], outputs=panel)
    compare.change(_open, inputs=[picked, compare], outputs=panel)
    load_once(_list, inputs=filters, outputs=[twin_table, compare, selected_line, d_pick])
    # A row click fills the textbox above, which is what opens the panel. Without it the table is
    # a list of opaque keys to re-type (`CLAUDE.md` rule 8, `docs/05` §8.3).
    load_js(_row_click_js("tl-twin-pick"))


def _persona_html(view) -> str:
    """Step 4, collapsed by default, with its hash so a reader can cite the exact passage."""
    if not view.persona_text:
        return empty_state(
            "No persona stored for this twin.",
            "Rebuild the twin from its survey row; a persona is built at import.",
        )
    return (
        f'<details class="tl-card"><summary>Reconstructed persona</summary>'
        f'<pre class="tl-persona tl-scroll">{esc(view.persona_text)}</pre>'
        f'<div class="tl-prov">persona_hash {esc(view.persona_hash)}</div></details>'
    )


# ================================================================= Validation


def _validation_tab() -> None:
    """`docs/06` §3.4. Canonical part numbers, and the **Arm seen** column.

    **This tab is a read-only view over `twin_quality_runs`.** There is no separate "validation
    run" to start: `validation_view` aggregates H2 error, H3 error and the three Pearson `r`s from
    the rows the twin quality test writes. Until M19 WP-7 that produced a screen with a
    primary-styled button that did nothing (`interactive=False`, no handler) above a table whose
    empty state read *"Press Check twins against their drivers"* — instructing the researcher to
    press the control that was disabled, and saying nothing about where the numbers come from.

    The honest action is a **refresh**, so that is what the button is and what it is called. It
    makes no model call: every number here is re-aggregated from stored rows.
    """
    from twinlab.services.lab import SYNTHETIC_WARNING

    gr.Markdown("### Validation: do twins answer like their drivers?")
    gr.Markdown(
        "These numbers are produced by the **twin quality test**, which you run on the "
        "**Twins** tab. Its verdicts land here. Nothing on this tab calls a model."
    )
    recheck = gr.Button("Recheck twins against their drivers", variant="primary")
    warning = gr.HTML("")
    protocol_line = gr.Markdown("")
    summary = gr.HTML("")
    table = gr.HTML("")

    async def _load():
        from twinlab.services.lab import validation_view

        view, rows = await validation_view()
        card = kv_table(
            [
                ("Survey twins checked", str(view.twins_checked)),
                (
                    "Part 16 (H2): average error on the 16 follow-up answers",
                    f"{num(view.h2_mae, signed=False)}"
                    + (
                        f", {view.h2_within_one * 100:.0f}% within 1"
                        if view.h2_within_one is not None
                        else ""
                    ),
                ),
                (
                    "Part 17 (H3): average error on the six versions",
                    num(view.h3_mae, signed=False),
                ),
                (
                    "Part 17 (H3): twin and driver move together (r)",
                    " · ".join(
                        f"{name} {num(value, signed=False)}" for name, value in view.h3_r.items()
                    ),
                ),
            ],
            caption="Summary",
        )
        body = data_table(
            [
                "Twin",
                "Arm seen",
                "H2 error",
                "Within 1 point",
                "Versions",
                "H3 error",
                "Fairness r",
                "Pushback r",
                "Staying r",
            ],
            [
                [
                    esc(r.twin_id),
                    esc(r.arm_seen),
                    num(r.h2_error, signed=False),
                    num(r.within_one, signed=False),
                    str(r.versions),
                    num(r.h3_error, signed=False),
                    num(r.fairness_r, signed=False),
                    num(r.pushback_r, signed=False),
                    num(r.staying_r, signed=False),
                ]
                for r in rows
            ],
            # WP-7. The empty state says where the data comes from and counts what is missing,
            # instead of naming a button to press.
            empty=empty_state(
                f"{view.twins_checked} of {view.twins_total} twins have a stored quality run.",
                "These numbers are produced by the twin quality test. Run it on the Twins tab; "
                "the verdicts land here.",
            ),
        )
        warn = (
            f'<div class="tl-warn-strip" role="alert">{esc(SYNTHETIC_WARNING)}</div>'
            if view.synthetic_present
            else ""
        )
        return warn, _protocol_note(view), card, body

    def _protocol_note(view) -> str:
        """Which H3 presentation produced these rows. WP-7 item 3.

        An H3 number must always say how it was collected: `h3_single_call_v1` shows a twin all
        six Part-17 versions in one call, the way the human respondent saw them (M19 WP-3), while
        the earlier protocol asked each version in its own call. The two are **different
        measurements and cannot be pooled**, so a table carrying both says so rather than
        averaging across them.
        """
        if not view.h3_protocols:
            return ""
        if len(view.h3_protocols) == 1:
            return f"Part 17 answers collected under protocol `{esc(view.h3_protocols[0])}`."
        joined = "`, `".join(esc(p) for p in view.h3_protocols)
        return (
            f"⚠️ **These rows mix {len(view.h3_protocols)} H3 protocols** (`{joined}`). "
            "Six-in-one-context and six-in-isolation are different measurements and must not be "
            "pooled — exclude one before quoting an average."
        )

    outputs = [warning, protocol_line, summary, table]
    recheck.click(_load, outputs=outputs)
    load_once(_load, outputs=outputs)


# ============================================================== Validity tests


def _validity_tab() -> None:
    """`docs/06` §3.5. Definitions live in `docs/08` §4 and are deliberately not restated.

    Two contracts hold here rather than in the service:

    * **Every test confirms a budget before it starts** (`docs/06` §9), including the two that
      cost nothing — showing zero calls is how a researcher learns tests 1 and 3 are free and can
      be run early and often (`docs/08` §4).
    * **No model call in the synchronous path** (`CLAUDE.md` rule 12). The six tests that need
      fresh twin calls are enqueued and the table picks the appended row up; only tests 1 and 3,
      which make no call by construction, run inline.
    """
    from twinlab.services.lab import SYNTHETIC_WARNING, VALIDITY_TESTS

    gr.Markdown("### Validity tests: can the twin answers be trusted?")
    # `docs/08` §6.2 — mandatory wherever the tested set may include synthetic twins. "A green
    # board on synthetic data is the expected result and means nothing."
    gr.HTML(f'<div class="tl-warn-strip" role="note">{esc(SYNTHETIC_WARNING)}</div>')

    # M19 WP-6 item 4. There was no control anywhere for **which** session or **which** version a
    # test ran against, so every test took `latest_session_id` (the newest session of any kind,
    # which on this database was a render session with no panel) and `settings.start_code` (which
    # had never been rendered). Eight cards, eight buttons, and no path by which any of them could
    # produce a row.
    #
    # M19 WP-7: there used to be a "Twins per test" number here too, feeding the confirm step's
    # budget. Tests 2 and 4-8 always put a stimulus to the **frozen** panel of the session above
    # (I14) — the number of twins is not a free parameter once a session is picked, so a manual
    # count could only ever disagree with what the run actually did. Removed; the budget below
    # reads the panel's own size.
    with gr.Row():
        session_pick = gr.Dropdown(
            choices=[],
            label="Session to test (only sessions with a frozen panel)",
            interactive=True,
        )
        version_pick = gr.Dropdown(
            choices=[],
            label="Version to test (only versions that passed the Checker)",
            interactive=True,
        )
    second_model = gr.Textbox(
        value="",
        label="Second model name (test 7 only)",
        info=(
            "Test 7 asks whether the same twins answer the same way under a different model, "
            "which cannot be answered against one model. Any model this installation's endpoint "
            "serves works by name — mistral-large-4 or deepseek-v4-pro:0813, say; crossing model "
            "families is worth more than two variants of one base model agreeing. The name is "
            "checked before the test spends anything. Leave empty and test 7 will say so."
        ),
    )

    # `docs/06` §3.5's eight cards. The Run control is **inside its own card**, not in a separate
    # list of buttons below the grid: a researcher picks a test by reading it, and a button whose
    # only tie to the card above it is a number in its label is a control the reader has to match
    # up by hand. Gradio cannot put a `gr.Button` inside a `gr.HTML` blob, so each card is a
    # `gr.Group` holding its own text and its own button.
    #
    # The buttons are still created BEFORE the confirm step so they read above it, and their
    # handlers are attached below, once `confirm` exists.
    buttons: dict[int, gr.Button] = {}
    #: Per-card readiness line, computed from the same reads the test itself makes (WP-6 item 5).
    readiness: dict[int, gr.Markdown] = {}
    with gr.Row(elem_classes=["tl-validity-grid"]):
        for card in VALIDITY_TESTS:
            with gr.Column(min_width=280):
                with gr.Group(elem_classes=["tl-validity-card"]):
                    gr.HTML(
                        '<div class="tl-validity-head">'
                        f'<span class="tl-validity-name">{esc(card.name)}</span>'
                        + (
                            '<span class="tl-pill tl-pill-amber">needs a live AI model</span>'
                            if card.needs_live_model
                            else '<span class="tl-pill">no model calls</span>'
                        )
                        + "</div>"
                        f'<div class="tl-validity-q">{esc(card.question)}</div>'
                        f'<div class="tl-validity-what">{esc(card.what_it_does)}</div>'
                    )
                    readiness[card.number] = gr.Markdown(
                        "", elem_classes=["tl-validity-ready"]
                    )
                    buttons[card.number] = gr.Button(
                        "Run this test  →",
                        elem_id=f"tl-validity-{card.number}",
                        elem_classes=["tl-run-pill"],
                    )

    # The confirm step, shared by all eight (`docs/06` §9). Nothing starts from the first click.
    with gr.Group(visible=False) as confirm:
        confirm_title = gr.Markdown("")
        confirm_budget = gr.HTML("")
        with gr.Row():
            confirm_go = gr.Button("Start", variant="primary")
            gr.Button("Cancel").click(lambda: gr.update(visible=False), outputs=confirm)
    pending = gr.State(None)
    note = gr.Markdown("")

    async def _confirm(
        number: int,
        session: str | None,
        version: str | None,
        model_name: str | None,
    ):
        from twinlab.services.validity import test_readiness, validity_budget_view

        view = await validity_budget_view(number, session_id=session or None)
        card = VALIDITY_TESTS[number - 1]
        free = "" if view.calls else " This test re-scores stored answers and makes no model call."
        ready = await test_readiness(
            number,
            session_id=session or None,
            version_code=version or None,
            second_model_name=model_name or None,
        )
        # Shown on the confirm step as well as on the card, because the card was painted when the
        # tab loaded and the researcher may have changed the session or version since.
        state = (
            f"**Ready.** {ready['reason']}" if ready["ready"]
            else f"**Not ready** — {ready['reason']}"
        )
        return (
            gr.update(visible=True),
            f"### {number}. {card.name}\n{card.question}{free}\n\n{state}",
            budget_summary(view),
            number,
        )

    aim_inputs = [session_pick, version_pick, second_model]
    for number, button in buttons.items():
        button.click(
            _confirm,
            inputs=[gr.State(number), *aim_inputs],
            outputs=[confirm, confirm_title, confirm_budget, pending],
        )

    async def _readiness_lines(session: str | None, version: str | None, model_name: str | None):
        """Every card's readiness, recomputed when an aiming control moves. Reads only.

        Computed rather than guessed from the card's metadata: a line that can disagree with what
        the test will actually do is worse than no line.
        """
        from twinlab.services.validity import test_readiness

        out = []
        for card in VALIDITY_TESTS:
            try:
                ready = await test_readiness(
                    card.number,
                    session_id=session or None,
                    version_code=version or None,
                    second_model_name=model_name or None,
                )
            except Exception as exc:  # noqa: BLE001 — name it rather than leave the card blank
                out.append(f"*could not check: {type(exc).__name__}*")
                continue
            out.append(
                "\✓ ready" if ready["ready"] else f"**needs** {ready['reason']}"
            )
        return out

    async def _load_aim():
        """Populate the two dropdowns and paint every readiness line. One pass, reads only."""
        from twinlab.services.runs import sessions_with_panels
        from twinlab.services.validity import runnable_version_codes

        sessions = await sessions_with_panels()
        codes = await runnable_version_codes()
        session_value = sessions[0][0] if sessions else None
        version_value = codes[0] if codes else None
        lines = await _readiness_lines(session_value, version_value, "")
        return (
            gr.update(
                choices=[(label, sid) for sid, label in sessions], value=session_value
            ),
            gr.update(choices=codes, value=version_value),
            *lines,
        )

    async def _run(
        number: int | None,
        session: str | None,
        version: str | None,
        model_name: str | None,
    ):
        """Run it, or hand it to the loop. **No model call happens in this function.**

        The session, version and second model the researcher chose are passed through (WP-6 item
        4). Before M19 none of the three reached the service, so every test ran against the newest
        session of any kind and `settings.start_code`.
        """
        from twinlab.services.twin_runtime import ask_panel_twins
        from twinlab.services.validity import (
            enqueue_validity_test,
            run_validity_test,
        )
        from twinlab.validity.tests import CALLS_PER_TWIN

        if number is None:
            return gr.update(visible=False), "No test selected.", await _load(), gr.skip()
        aim: dict[str, object] = {
            "session_id": session or None,
            "version_code": version or None,
            "second_model_name": model_name or None,
        }
        if CALLS_PER_TWIN[number] == 0:
            # Tests 1 and 3 re-score stored vectors and take no `ask` at all, which is why
            # `docs/08` §4 gives them a cost of zero and why they run inline.
            outcome = await run_validity_test(number, **aim)
            return (
                gr.update(visible=False),
                f"**{outcome.verdict}** — {outcome.headline}",
                await _load(),
                gr.skip(),  # nothing queued; the poll timer is untouched
            )
        # The live twin path, injected exactly as `SessionRunner` takes `ask_twin`. Without it
        # tests 4-8 record INCONCLUSIVE and say so, which was honest but never a result.
        # The returned task is held by `enqueue_validity_test`'s own module-level set, and its
        # done-callback writes an INCONCLUSIVE row if it raises (WP-6 item 1). Discarding it here
        # used to mean the task could be garbage-collected mid-run and anything it raised became
        # an "exception was never retrieved" warning at interpreter shutdown — while this handler
        # had already promised the result would appear in the table.
        enqueue_validity_test(number, ask=ask_panel_twins, **aim)
        return (
            gr.update(visible=False),
            f"Queued test {number}. The result appears in the table below when it finishes; "
            "the run continues if you change tab. If it cannot finish, an INCONCLUSIVE row "
            "appears there saying why.",
            await _load(),
            # M19 WP-7. The table used to be painted once on load, so a queued test's row stayed
            # invisible until the page was reloaded by hand, though this message already promised
            # it would "appear in the table below when it finishes." Wakes the poll started below.
            gr.Timer(POLL_SECONDS, active=True),
        )

    gr.HTML(section_title("Results so far"))
    results = gr.HTML("")
    # Off until a test is queued, exactly as the Agents tab's ticker (`_wake_ticker`): an idle
    # Validity tab must make zero database calls.
    validity_timer = gr.Timer(POLL_SECONDS, active=False)

    async def _load():
        from twinlab.services.lab import validity_results

        rows = await validity_results()
        return data_table(
            ["When", "Test", "Version", "Twins", "Model", "Result", "Verdict"],
            [
                [
                    esc(r.when[:19]),
                    esc(r.test),
                    esc(r.version_code or "—"),
                    str(r.twins_n),
                    esc(r.model),
                    esc(r.result),
                    verdict_pill(r.verdict),
                ]
                for r in rows
            ],
            empty=empty_state(
                "No validity test has been run.", "Pick a test above and press Run this test."
            ),
        )

    async def _tick():
        """One poll while a validity test is in flight. M19 WP-7.

        Switching off is unconditional — sent fresh on every tick where nothing is left running, the
        same rule the Agents tab's ticker uses, since `active=False` is idempotent. Switching on
        happens once, in `_run`'s return; while the timer is already active this returns `gr.skip()`
        for it rather than resetting the interval on every tick.
        """
        from twinlab.services.validity import pending_validity_tests

        table = await _load()
        if pending_validity_tests() == 0:
            return table, gr.Timer(POLL_SECONDS, active=False)
        return table, gr.skip()

    confirm_go.click(
        _run,
        inputs=[pending, session_pick, version_pick, second_model],
        outputs=[confirm, note, results, validity_timer],
    )
    validity_timer.tick(_tick, outputs=[results, validity_timer])

    ready_outputs = [readiness[card.number] for card in VALIDITY_TESTS]
    aim_controls = [session_pick, version_pick, second_model]
    for control in aim_controls:
        control.change(_readiness_lines, inputs=aim_controls, outputs=ready_outputs)

    load_once(_load, outputs=results)
    load_once(_load_aim, outputs=[session_pick, version_pick, *ready_outputs])


# ================================================================== Fieldwork


def _fieldwork_tab() -> None:
    """`docs/06` §3.6. **Real fieldwork metrics never count synthetic rows.**"""
    gr.Markdown(
        "### Fieldwork: how collection is going\n"
        "*Real driver surveys only. Targets assume 500 drivers across 5 cities and "
        "3 services.*"
    )
    refresh = gr.Button("Refresh")
    body = gr.HTML("")

    async def _load():
        from twinlab.services.lab import fieldwork_counts

        data = await fieldwork_counts()
        strata = data["by_stratum"]
        matrix = data_table(
            ["City", "Service", "Real surveys"],
            [[esc(c), esc(s), str(n)] for (c, s), n in sorted(strata.items())],
            empty=empty_state(
                "No real surveys yet.",
                "Share the Google Form link on the Driver survey page.",
            ),
        )
        arms = data_table(
            ["City", "Service", "Arm", "Count"],
            [
                [esc(c), esc(s), esc(arm), str(n)]
                for (c, s), balance in sorted(data["arm_balance"].items())
                for arm, n in sorted(balance.items())
            ],
            empty=empty_state("No arm balance yet.", "It fills as real surveys arrive."),
        )
        quality = kv_table(
            [(r.label, esc(r.value)) for r in data["quality"]],
            caption="Data quality and drop out",
        )
        per_day = data_table(
            ["Day", "Real surveys"],
            [[esc(d), str(n)] for d, n in data["per_day"].items()],
            empty='<div class="tl-empty">Nothing yet.</div>',
        )
        synthetic = (
            f'<div class="tl-card">Synthetic surveys, counted separately and never part of '
            f"fieldwork: <strong>{data['synthetic_total']}</strong></div>"
        )
        return (
            section_title("Surveys by city and service")
            + matrix
            + synthetic
            + section_title("Arm balance")
            + arms
            + section_title("Data quality and drop out")
            + quality
            + section_title("Surveys per day")
            + per_day
        )

    refresh.click(_load, outputs=body)
    load_once(_load, outputs=body)


# ==================================================================== Results


def _results_tab(signals: _LabSignals) -> None:
    """`docs/06` §3.7. Grid, interactions, the linear table and the seven-step side panel."""
    gr.Markdown(
        "### Results\n*Every tested version compared with Uber today. Higher index means "
        "better for drivers.*"
    )
    # The prototype's two-card row: the grid on the left, the interaction reading on the right.
    # The grid is the screen's subject, so it gets the wider column.
    with gr.Row(equal_height=False):
        with gr.Column(scale=3):
            with gr.Group(elem_classes=["tl-panel"]):
                gr.HTML(section_title("All 243 versions"))
                grid = gr.HTML("")
        with gr.Column(scale=2):
            with gr.Group(elem_classes=["tl-panel"]):
                gr.HTML(section_title("Do changes work together?"))
                interactions = gr.HTML("")

    with gr.Row():
        picked = gr.Textbox(
            label="Version code",
            placeholder="e.g. 01000",
            elem_id="tl-grid-pick",
            info="Click a cell in the grid above, or type a code.",
        )
        search = gr.Textbox(label="Search version codes")
    panel = gr.HTML("")
    gr.HTML(section_title("Tested versions"))
    table = gr.HTML("")

    async def _load(needle: str):
        from twinlab.services.metrics_view import build_grid, build_tested_table
        from twinlab.services.results import tested_rows
        from twinlab.services.status import tested_codes

        index_by_code = await tested_codes()
        rows = build_tested_table(await tested_rows(), search=needle or "")
        body = data_table(
            [
                "Version",
                "Score",
                "Twins",
                # `ARCHITECTURE_UPDATE.md` §4.3 item 4. A Studio row's index is over one twin while
                # the controls it is measured against came from the frozen panel, so the two are
                # different quantities. The column makes that visible in the table rather than
                # leaving it to be inferred from a `Twins` value of 1.
                "From",
                "Fairness",
                "Clarity",
                "Happiness",
                "Staying",
                "Pushback",
                "Leaving",
                "Index",
            ],
            [
                [
                    esc(r.version_code),
                    str(r.fairwork_score),
                    str(r.twins_n),
                    (
                        status_dot("complete", "panel")
                        if r.origin == "sweep"
                        else status_dot("pending", f"Studio, n={r.twins_n}")
                    ),
                    *(
                        num(r.shifts.get(m))
                        for m in (
                            "fairness",
                            "clarity",
                            "happiness",
                            "staying",
                            "pushback",
                            "leaving",
                        )
                    ),
                    num(r.index_value, places=3),
                ]
                for r in rows
            ],
            empty=empty_state(
                "No tested versions yet.",
                "Set the dials and press Ask the twins, or let the agents choose six versions.",
            ),
        )
        return grid_243(build_grid(index_by_code)), body, await _interactions()

    async def _interactions() -> str:
        """I17 — *Do changes work together?*, **including the legs that are missing by name**.

        A missing leg renders the code to run, never an estimate and never a blank
        (`CLAUDE.md` rule 5). The reading is computed in the analysis layer; nothing is derived
        in this handler.
        """
        from twinlab.services.results import interaction_rows

        try:
            return interactions_panel(await interaction_rows())
        except Exception as exc:  # noqa: BLE001 — say why, rather than render an empty card.
            from ..components import error_state

            return error_state(
                "Could not read the interactions.", type(exc).__name__, str(exc)[:200]
            )

    async def _open(code: str):
        from twinlab.services.results import results_panel

        if not code:
            return ""
        return side_panel(code, results_panel_html(await results_panel(code)))

    picked.change(_open, inputs=picked, outputs=panel)
    search.change(_load, inputs=search, outputs=[grid, table, interactions])
    load_once(_load, inputs=search, outputs=[grid, table, interactions])
    # A finished run must reach the grid without a reload. Same loader, same outputs.
    signals.run_done.change(_load, inputs=search, outputs=[grid, table, interactions])
    # `gr.HTML` emits no events, so a cell click is bridged into the version-code box, which is
    # what opens the panel. `docs/05` §8.3: never ship a grid without click handling -- without
    # it the grid is decoration, and the click is how a researcher reaches the scenario text.
    load_js(_GRID_CLICK_JS)


# =================================================================== Settings


def _settings_tab() -> None:
    """`docs/06` §3.8. Two columns, and **no "clear runs" button** (I9).

    Every control here shows the value that is **actually in force**, read from the live
    `TwinConfig` and from `settings`. They were hard-coded literals, bound to nothing, beside a
    *Save settings* button that wrote ``{"saved_from": "settings tab"}`` over the whole `twin`
    row — so a researcher who changed the panel size saw a success message, changed nothing, and
    destroyed the seeded quality-gate thresholds in the same click.

    The split is the design. The fields on the left are `TwinConfig`'s and are editable; the
    environment-owned values on the right of them are shown read-only, because a Gradio control
    cannot change an environment variable and a control that looks editable and is not is the same
    lie in a smaller font.

    **`panel_size` moved from the right to the left in M19 WP-5.** It was environment-only, which
    left the researcher's "let every twin answer this version" with no control anywhere and made
    the Dial board's refusal name a setting that could not be reached. `PANEL_SIZE` is still shown
    on the right, now labelled as the default the editable field starts from.
    """
    from config.settings import settings
    from twinlab.services.config import load_twin_config
    from twinlab.services.lab import CLEAR_RUNS_NOTE
    from twinlab.services.runs import effective_panel_size

    # The **seed**, used only to give every control a value while the page is being built. It is
    # not what is in force: `load_twin_config` reads a process override that nothing has populated
    # at build time, so before `_refresh` runs below these are `config/twin.default.yaml`'s
    # numbers. Every control is repainted from `app_config` on page load, because a settings screen
    # showing the seed while the database holds something else is the same lie as a read-only
    # control that looks editable — and it is how `show_baseline: false` sat in the YAML for a day
    # while `app_config` ran `true`.
    cfg = load_twin_config()

    with gr.Row():
        with gr.Column():
            gr.HTML(section_title("Settings"))
            temperature = gr.Slider(0.0, 1.5, value=cfg.temperature, step=0.05, label="Temperature")
            wording = gr.Textbox(value=cfg.wording, label="Wording variant")
            quality_runs = gr.Number(
                value=cfg.quality_runs_per_twin,
                precision=0,
                label="Quality test runs per twin",
            )
            mae_max = gr.Number(value=cfg.mae_max, label="Quality gate: highest average error")
            pct_min = gr.Number(
                value=cfg.pct_within_1_min, label="Quality gate: lowest share within 1 point"
            )
            # Editable from M19 WP-5. It was read-only on the right, with the environment's
            # `PANEL_SIZE` as the only way to change it — so the researcher's question "let all
            # the twins answer this version" had no control anywhere, and the Dial board's
            # refusal named a setting they could not reach. It is a `TwinConfig` field now, so it
            # is versioned on write and frozen onto every session that ran under it (I11, I14).
            panel_size = gr.Number(
                value=effective_panel_size(),
                precision=0,
                minimum=1,
                label="Panel size (twins per sweep)",
            )

            gr.Markdown("**Set outside the app** — these come from the environment, not from here.")
            # `docs/03` §321: a recorded field, a researcher-set default, **not a UI control**.
            # Shown because a value that governs every twin round and appears on no screen is a
            # value nobody can check; read-only because changing it is a deliberate act against
            # the database, not a slider. `_save` below never writes it (see there).
            baseline_shown = gr.Textbox(
                value=str(cfg.show_baseline),
                label="Twin sees its own baseline numbers (set in app_config, not here)",
                interactive=False,
            )
            gr.Textbox(value=settings.model_badge, label="Twin model", interactive=False)
            gr.Textbox(value=settings.twinlab_model, label="Model name", interactive=False)
            gr.Number(
                value=settings.panel_size,
                precision=0,
                interactive=False,
                label="Panel size default (PANEL_SIZE in the environment)",
            )
            gr.Number(
                value=settings.delay_seconds,
                interactive=False,
                label="Pause between AI calls (seconds)",
            )
            gr.Number(
                value=settings.max_concurrency,
                precision=0,
                interactive=False,
                label="Calls sent at once",
            )

            save = gr.Button("Save settings", variant="primary")
            saved = gr.Markdown("")
            with gr.Accordion("What these settings do", open=False):
                gr.Markdown(
                    "**Calls sent at once** is capped by the provider tier; the free tier "
                    "permits one, so a sweep is serial by design.\n\n"
                    "**Pause between AI calls** limits provider pressure. Raise it if calls "
                    "start being refused. It is applied before every model call.\n\n"
                    "**Panel size** sets the sweep budget: a full sweep is panel size × 243 twin "
                    "calls. It is frozen onto a session when the session starts, so every cell "
                    "in that session is answered by the same twins (I14) and a later change "
                    "cannot be applied to it retroactively. `PANEL_SIZE` on the right is only "
                    "the default this field starts from.\n\n"
                    "**Temperature** is a placeholder at 0.7 and should be set from validity "
                    "test 8, not chosen."
                )

            #: The `TwinConfig` fields this screen owns. **`show_baseline` is deliberately absent**
            #: and `_save` writes only these keys, so the UI path cannot change it whatever the
            #: form holds. `services.lab.save_settings` merges over the stored row, so a key this
            #: screen never sends is a key it can never clobber — which is the only way
            #: "researcher-set in the database, not from here" survives a researcher pressing Save.
            EDITABLE = (
                "temperature",
                "wording",
                "quality_runs_per_twin",
                "mae_max",
                "pct_within_1_min",
                "panel_size",
            )

            async def _refresh():
                """Repaint every control from `app_config`, on page load.

                Without this the screen showed `config/twin.default.yaml` — `load_twin_config`
                merges a process override that nothing has populated when the Blocks are built. A
                researcher read the seed, believed it, and `_save` then wrote the seed's
                `show_baseline` back over the database's.
                """
                from twinlab.services.config import refresh_twin_config

                try:
                    live = await refresh_twin_config()
                except Exception as exc:  # noqa: BLE001 — never block a page load on a config read
                    log.warning("settings tab could not read the live config: %r", exc)
                    return (gr.skip(),) * 7
                return (
                    gr.update(value=live.temperature),
                    gr.update(value=live.wording),
                    gr.update(value=live.quality_runs_per_twin),
                    gr.update(value=live.mae_max),
                    gr.update(value=live.pct_within_1_min),
                    gr.update(value=effective_panel_size()),
                    gr.update(value=str(live.show_baseline)),
                )

            async def _save(temp, word, runs, mae, pct, panel):
                from twinlab.models.twin import TwinConfig
                from twinlab.services.config import refresh_twin_config
                from twinlab.services.lab import save_settings

                # The live row, not the build-time seed: the proposal is validated against what is
                # actually stored, and `show_baseline` is taken from there purely so the model can
                # be constructed. It is dropped again before the write.
                try:
                    live = await refresh_twin_config()
                except Exception as exc:  # noqa: BLE001
                    return f"**Not saved.** Could not read the live config: {exc}"

                # Validated before it is written, through the same model `load_twin_config` uses.
                # `TwinConfig` forbids extras and range-checks the two gate thresholds, so a value
                # that could not be run is refused here rather than stored and discovered later.
                try:
                    proposed = TwinConfig(
                        temperature=float(temp),
                        wording=str(word),
                        quality_runs_per_twin=int(runs),
                        mae_max=float(mae),
                        pct_within_1_min=float(pct),
                        show_baseline=live.show_baseline,
                        panel_size=int(panel) if panel else None,
                    )
                except ValueError as exc:
                    return f"**Not saved.** {exc}"

                from twinlab.services.config_match import current_fingerprint, describe

                before = await current_fingerprint()
                # Only the keys this screen owns. `save_settings` merges, so everything else on
                # the row — `show_baseline`, `max_concurrency` — is left exactly as stored.
                dumped = proposed.model_dump()
                version = await save_settings(
                    "twin", {k: dumped[k] for k in EDITABLE}
                )
                after = await current_fingerprint()
                if after != before:
                    # RESEARCHER 2026-10-05. A change to the config makes every verdict made under
                    # the old one stale, and nothing downstream runs until the gate is run again.
                    return (
                        f"Saved to `app_config` as version **{version}**. The config is now "
                        f"{await describe()}, which is not the config the quality test was run "
                        "under. **Run the twin quality test again** before a session, validity "
                        "test or Studio ask runs. Verdicts under the old config are kept on the "
                        "record but do not qualify any twin now."
                    )
                # M19 WP-9. The old message said "this does not change what the next session runs
                # under yet. Nothing reads `app_config` back." That had stopped being true:
                # `services.config.refresh_twin_config` reads the row into a process override,
                # `load_twin_config` merges it over the seed, and `services.runs.session_config`
                # calls the refresh before every session, so a sweep already runs under what was
                # just saved. A researcher who believed the message edited the YAML by hand
                # instead — unversioned, unaudited, and outside the `config_version` that
                # `twin_quality_runs` records — which actively undoes the reproducibility chain
                # this button exists to maintain.
                return (
                    f"Saved to `app_config` as version **{version}**. The next session, quality "
                    "gate or Studio ask reads this; runs already completed keep the config "
                    "version they ran under (I9). You do not need to edit any file."
                )

            save.click(
                _save,
                inputs=[temperature, wording, quality_runs, mae_max, pct_min, panel_size],
                outputs=saved,
            )
            # Every control shows what is in force, not what the YAML seeds. Off the render path
            # (`docs/05` §8.4 rule 2) — the read happens after the page is served.
            load_once(
                _refresh,
                outputs=[
                    temperature, wording, quality_runs, mae_max, pct_min, panel_size,
                    baseline_shown,
                ],
            )

        with gr.Column():
            gr.HTML(section_title("Data"))
            gr.Markdown(
                "Survey answers, twins, runs, results, validation and agent messages are "
                "stored in Supabase."
            )
            from twinlab.services.lab import SURVEY_SCOPES

            scope = gr.Radio(
                [label for label, _ in SURVEY_SCOPES],
                value=SURVEY_SCOPES[0][0],
                label="Which survey answers?",
                elem_classes=["tl-toggle"],
            )
            available = gr.Markdown("")
            import_button = gr.Button("Import twins from the survey", variant="primary")
            imported = gr.HTML("")
            gr.HTML(f'<div class="tl-card">{esc(CLEAR_RUNS_NOTE)}</div>')

            async def _available(which: str) -> str:
                """§3.8's live count. The same rule the import applies, never a looser one."""
                from twinlab.services.lab import available_survey_twins

                try:
                    n = await available_survey_twins(which)
                except Exception as exc:  # noqa: BLE001
                    return f"**Could not read the count.** {type(exc).__name__}: {exc}"
                if not n:
                    return (
                        "**How many survey twins are available?** 0 — every respondent in this "
                        "scope is already a twin, or was gated out by consent, eligibility or an "
                        "incomplete battery."
                    )
                return f"**How many survey twins are available?** {n:,}"

            async def _import(which: str) -> tuple[str, str]:
                """§3.8's *Import twins from the survey*. **No model call in this path.**

                The whole action is `services.lab.import_survey_twins`; this renders what it
                returns (`docs/05` §8.4 rule 1). Every row that did not become a twin is named
                rather than silently dropped (`CLAUDE.md` rule 7).
                """
                from twinlab.services.lab import import_survey_twins

                try:
                    result = await import_survey_twins(which)
                except Exception as exc:  # noqa: BLE001
                    return (
                        error_state(
                            "Nothing was imported.", type(exc).__name__, str(exc)[:300]
                        ),
                        await _available(which),
                    )

                # "Nothing left to import" and "nothing qualified" are opposite outcomes and used
                # to share the word `skipped`, so a researcher whose respondent already had a
                # working twin was told "Nothing was eligible". Since the hosted questionnaire
                # builds the twin at submit time, that is now the ordinary case.
                nothing_wrong = (
                    not result.imported and not result.invalid and not result.gated
                )
                tone = (
                    "ok" if (result.imported and not result.invalid) or nothing_wrong else "warn"
                )
                head = (
                    f"Imported {result.imported:,}, already twins {result.already_twins:,}, "
                    f"gated out {result.gated:,}, invalid {result.invalid:,}."
                )
                body = ""
                if nothing_wrong and result.already_twins:
                    body = (
                        f"<div><strong>Nothing to do, and nothing is wrong.</strong> "
                        f"{result.already_twins:,} respondent"
                        f"{'s' if result.already_twins != 1 else ''} in this scope already "
                        "ha" + ("ve" if result.already_twins != 1 else "s") + " a twin. The "
                        "hosted questionnaire builds the twin when the driver presses send, so "
                        "there is usually nothing left here to import — look for them on the "
                        "Twin Lab's Twins tab.</div>"
                    )
                elif result.gated:
                    body = (
                        f"<div>{result.gated:,} respondent"
                        f"{'s' if result.gated != 1 else ''} did not qualify. A respondent "
                        "becomes a twin only if they are eligible, consented, answered the whole "
                        "battery and agreed to a twin (statement 7).</div>"
                    )
                elif nothing_wrong:
                    body = (
                        "<div>There are no respondents in this scope yet.</div>"
                    )
                if result.reasons:
                    items = "".join(f"<li>{esc(r)}</li>" for r in result.reasons)
                    more = (
                        f"<div class=\"tl-caption\">Showing the first {len(result.reasons)} "
                        f"of {result.invalid:,}.</div>"
                        if result.invalid > len(result.reasons)
                        else ""
                    )
                    body += (
                        "<div><strong>These could not be imported:</strong>"
                        f"<ul>{items}</ul>{more}</div>"
                    )
                return (
                    f'<div class="tl-note tl-note-{tone}"><strong>{esc(head)}</strong>'
                    f"{body}</div>",
                    await _available(which),
                )

            scope.change(_available, inputs=scope, outputs=available)
            import_button.click(_import, inputs=scope, outputs=[imported, available])
            load_once(_available, inputs=scope, outputs=available)


# ======================================================================= page


_TABS = (
    ("Agents", _agents_tab),
    ("Dial board", _dial_board_tab),
    ("Twins", _twins_tab),
    ("Validation", _validation_tab),
    ("Validity tests", _validity_tab),
    ("Fieldwork", _fieldwork_tab),
    ("Results", _results_tab),
    ("Settings", _settings_tab),
)


#: The tabs that start, watch or repaint a session. The rest take no shared state.
_SIGNALLED_TABS = frozenset({"Agents", "Dial board", "Results"})


def render_lab(badge: str | None = None) -> None:
    """Build Twin Lab into the enclosing Blocks context. Tab order is mandatory."""
    from twinlab.services.menu import LAB_TABS

    names = tuple(name for name, _ in _TABS)
    if names != LAB_TABS:
        raise AssertionError(
            f"Twin Lab tab order {names} does not match the mandatory order {LAB_TABS} "
            "(docs/06 §0). Content and ordering may not be changed."
        )

    with gr.Column(elem_classes=page_classes("/lab")):
        app_header(
            "Twin Lab",
            "Agents testing 243 versions of Uber's rules on driver twins",
            badge,
        )
        global_nav("/lab")
        # Created once, before any tab, so every tab that starts, watches or repaints a run shares
        # the same components. The timer is invisible; the textbox only carries the finish signal.
        signals = _LabSignals(
            ticker=gr.Timer(POLL_SECONDS, active=False),
            run_done=gr.Textbox(visible=False, elem_id="tl-run-done"),
        )
        with sub_nav(LAB_TABS):
            for name, build in _TABS:
                with gr.Tab(name):
                    if name in _SIGNALLED_TABS:
                        build(signals)
                    else:
                        build()


__all__ = ["render_lab"]
