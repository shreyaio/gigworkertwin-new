"""Session control and the live log, for the UI. `docs/04` §3, §5.4 and §7.3.

Three contracts M10 must not break live here rather than in a Gradio handler:

* **Polling is incremental.** :func:`events_since` takes the last ``event_id`` and asks for rows
  after it. The stream is never re-fetched whole — at sweep scale that is tens of thousands of
  rows per UI tick (`docs/04` §7.3).
* **`00000` is blocked from *Ask the twins*.** It is a control the orchestrator runs at the start
  of every session, not a cell a researcher pokes at, and :class:`ControlCellError` is raised here
  rather than being a disabled button the UI could forget to disable (`docs/03` §6.1).
* **A rerun inherits the original session's panel** unless the researcher explicitly chooses a new
  one (I14). A rerun answered by different twins is not a rerun; it is a different experiment
  wearing the same version code.

No LLM call happens in this module's synchronous path. Starting a session hands the work to the
orchestrator as a task and returns immediately (`CLAUDE.md` rule 12, `docs/05` §8.4 rule 2).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import PanelRepo, RunRepo, SessionRepo
from twinlab.models.run import Budget, Session
from twinlab.models.view import BudgetView, EventRow
from twinlab.orchestrator import budget as budget_calc
from twinlab.orchestrator.events import EventLog
from twinlab.orchestrator.loop import (
    ControlCellError,
    SessionAlreadyRunning,
    get_runner,
    request_stop,
    start_session,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, index_from_code, validate_code

log = logging.getLogger(__name__)

#: The Agents tab's three workflow buttons, in the mandatory order of `docs/06` §3.1.
WORKFLOW_BUTTONS: tuple[tuple[str, str, str], ...] = (
    ("quality", "Run twin quality test", "primary"),
    ("choose6", "Let the agents choose 6 versions", "primary"),
    ("sweep243", "Test all 243 versions", "secondary"),
)

#: Stop is cooperative and the UI says so, because a researcher who expects a kill will press it
#: twice and then assume it is broken (`ARCHITECTURE.md` §7.4).
STOP_NOTE = (
    "Stop is cooperative: the current twin call finishes, then the session pauses at its next "
    "checkpoint and can be resumed from where it stopped."
)


# ------------------------------------------------------------------ budgets


#: Strong references to the background session tasks. `asyncio` keeps only a weak reference to a
#: running task, so a bare `create_task(...)` whose result nobody holds can be garbage-collected
#: mid-sweep — the documented failure mode, not a theoretical one.
_TASKS: set[asyncio.Task] = set()


def _spawn(coro: Any, *, session_id: str | None = None, backend: DbBackend | None = None
           ) -> asyncio.Task:
    """Run a session in the background, holding it and surfacing anything it raises.

    The exception callback matters as much as the reference. `start_session` can raise before the
    runner's own `try` takes over — `SessionAlreadyRunning` from `register()` is the ordinary case
    — and a bare task swallows that into an "exception was never retrieved" warning at interpreter
    shutdown. The researcher would see a session row appear and then never move.

    **And a log line is not delivery.** `ARCHITECTURE_UPDATE.md` §3.5 defect 1: this callback wrote
    the failure to the console and nowhere else, so an `InsufficientEligibleTwins` the researcher
    needed to read appeared only in a terminal they were not looking at. When the session id is
    known, the failure is now also appended to `run_events` with ``status="error"`` — so a
    background death shows up in the log tree the researcher is already watching.
    """
    task = asyncio.create_task(coro)
    _TASKS.add(task)

    def _done(finished: asyncio.Task) -> None:
        _TASKS.discard(finished)
        if finished.cancelled() or finished.exception() is None:
            return
        exc = finished.exception()
        log.error("background session failed: %r", exc)
        if session_id is None:
            return
        # Fire-and-forget, and held, for the same reason the session task is: a bare `create_task`
        # whose result nobody keeps can be collected before it runs.
        reporter = asyncio.create_task(_report_failure(session_id, exc, backend))
        _TASKS.add(reporter)
        reporter.add_done_callback(_TASKS.discard)

    task.add_done_callback(_done)
    return task


async def _report_failure(
    session_id: str, exc: BaseException | None, backend: DbBackend | None
) -> None:
    """Put a background death in the log tree. §3.5.

    Swallows its own failure deliberately: this is the error path, and an exception raised while
    reporting an exception loses both. The console line above has already been written.
    """
    try:
        db = backend or get_backend()
        await EventLog(session_id, db).emit(
            stage="control",
            agent="manager",
            label=f"{type(exc).__name__}: {exc}"[:400],
            status="error",
        )
        await SessionRepo(db).set_status(session_id, "failed")
    except Exception as inner:  # noqa: BLE001 — never raise from a done-callback
        log.warning("could not record the background failure for %s: %r", session_id, inner)


def budget_view(budget: Budget) -> BudgetView:
    """A `Budget` formatted for `budget_summary`. `docs/05` §4.4, `docs/06` §9.

    ``est_credits`` renders as ``not known`` rather than a number. The Ollama Cloud free credit
    allowance is unpublished (`docs/10` §3.3) and an invented figure here would be read as a cost.
    """
    hours = budget.est_seconds / 3600
    if budget.est_seconds < 60:
        hours_text = f"{budget.est_seconds} s"
    elif hours < 1:
        hours_text = f"{budget.est_seconds / 60:.0f} min"
    else:
        hours_text = f"{hours:.1f} h"
    return BudgetView(
        calls=budget.calls,
        tokens_in=budget.tokens_in,
        tokens_out=budget.tokens_out,
        est_hours_text=hours_text,
        est_credits_text=(
            "not known" if budget.est_credits is None else f"{budget.est_credits:.2f}"
        ),
        cache_hits=budget.cache_hits,
        warnings=list(budget.warnings),
    )


async def ask_budget_view(
    version_code: str,
    *,
    panel_size: int | None = None,
    backend: DbBackend | None = None,
) -> BudgetView:
    """The budget for asking one cell, shown before *Ask the twins* starts anything."""
    size = panel_size if panel_size is not None else settings.panel_size
    answered = await _answered_for_code(version_code, backend=backend)
    return budget_view(budget_calc.ask_budget(panel_size=size, answered_already=answered))


async def sweep_budget_view(
    *, iterations: int, panel_size: int | None = None
) -> BudgetView:
    size = panel_size if panel_size is not None else settings.panel_size
    view = budget_view(budget_calc.sweep_budget(iterations=iterations, panel_size=size))
    # Same reason as the gate's: a confirm step that shows only a total invites the total to be
    # read as a defect (`ARCHITECTURE_UPDATE.md` §2). The two control cells are named because they
    # are the reason the arithmetic is not simply iterations × panel.
    view.breakdown = (
        f"({iterations:,} version(s) + 00000 + SHAM) × {size} twin(s), "
        "plus the ten lever paragraphs"
    )
    return view


async def quality_budget_view(
    *, twins: int, repeats: int | None = None, already_scored: int = 0
) -> BudgetView:
    """`docs/10`: 18 calls per twin. At N=500 this is ~20 hours, so it is never started blind."""
    from twinlab.services.config import load_twin_config

    # `TwinConfig` names this `quality_runs_per_twin`; there has never been a `quality_repeats`
    # field. The attribute error surfaced only when a researcher pressed the button.
    times = repeats if repeats is not None else load_twin_config().quality_runs_per_twin
    view = budget_view(
        budget_calc.quality_budget(
            twins=twins, repeats=times, already_scored=already_scored
        )
    )
    # `ARCHITECTURE_UPDATE.md` §2. `6 × 2 × 50 = 600` is correct and is not a bug: the 6 is the
    # six Part-17 stimuli, one model call each, reading three holdout items per round — `docs/08`'s
    # 18 H3 numbers. It read as a bug because the total appeared with nothing beside it. The number
    # does not change; it now explains itself.
    remaining = max(twins - already_scored, 0)
    view.breakdown = (
        f"{budget_calc.H3_CALLS_PER_REPEAT} Part-17 versions × {times} repeat(s) × "
        f"{remaining:,} twin(s)"
    )
    view.per_unit = str(budget_calc.H3_CALLS_PER_REPEAT * max(times, 1))
    return view


async def _answered_for_code(
    version_code: str, *, backend: DbBackend | None = None
) -> int:
    """(run, twin) pairs already stored for this code — calls a rerun will not make."""
    db = backend or get_backend()
    runs = await db.select(
        "runs", [("eq", "version_code", version_code), ("eq", "status", "completed")]
    )
    total = 0
    for run in runs:
        total += await db.count("twin_answers", [("eq", "run_id", run["run_id"])])
    return total


# ------------------------------------------------------------------ eligibility


class NotReadyToSweep(RuntimeError):
    """The panel cannot be drawn, so no session row is written. `ARCHITECTURE_UPDATE.md` §3.5.

    Typed, so the Agents tab renders it the way it already renders
    :class:`SessionAlreadyRunning` — in the page, next to the button that was pressed. The three
    defects this replaces were all one thing: the refusal was correct and arrived nowhere a
    researcher would see it.
    """


async def check_eligibility(
    population: str,
    panel_size: int,
    *,
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """Can a panel of ``panel_size`` be drawn from ``population``? **Pure read.** §3.5.

    Writes nothing, and in particular creates no `sessions` row — which is the second of §3.5's
    three defects. `start_sweep` created the row, spawned the task, and *then* the draw failed,
    leaving a permanent session row for a job that never ran. Eligibility is knowable before the
    row is written, so it is checked before the row is written.

    ``reason`` names the **real** blocker rather than restating the symptom. "No eligible twins for
    population 'real'" is true and tells a researcher looking at 50 synthetic twins nothing: the
    pool is empty twice over, because `eligible_candidates` requires both a matching `source` and
    `quality_passed`, and the quality gate has never run. Both halves are therefore counted and
    reported separately.
    """
    from twinlab.orchestrator.panel import POPULATION_SOURCES, eligible_candidates
    from twinlab.services.twin_runtime import candidates as candidate_rows

    db = backend or get_backend()
    if population not in POPULATION_SOURCES:
        raise NotReadyToSweep(
            f"unknown population {population!r}; expected one of {sorted(POPULATION_SOURCES)}."
        )

    # A throwaway `Session` so `candidates` has the shape it reads. Not persisted, by design.
    probe = Session(
        session_id="preflight",
        name="preflight",
        population=population,
        panel_size=panel_size,
    )
    pool = await candidate_rows(probe, backend=db)
    by_source: dict[str, int] = {}
    for candidate in pool:
        by_source[candidate.source] = by_source.get(candidate.source, 0) + 1
    passed = sum(1 for c in pool if c.quality_passed)
    eligible = len(eligible_candidates(pool, population))

    reason = ""
    if not pool:
        reason = (
            "There are no twins at all. Import them from the survey in Twin Lab → Settings, or "
            "generate a batch in the Generator."
        )
    elif eligible == 0 and passed == 0:
        reason = (
            f"0 of {len(pool)} twins have passed the quality test. Run it first "
            f"(Agents → Run twin quality test). Population is {population!r} and the twins you "
            f"have are {_source_phrase(by_source)} — change the population below if this is a "
            "synthetic study."
        )
    elif eligible == 0:
        reason = (
            f"{passed} twin(s) have passed the quality test, but none of them is in population "
            f"{population!r} ({_source_phrase(by_source)}). Change the population below."
        )
    elif eligible < panel_size:
        reason = (
            f"{eligible} twin(s) are eligible for a panel of {panel_size}. Lower the panel size "
            "or quality-test more twins; a smaller panel recorded as "
            f"{panel_size} would misstate the study (I14)."
        )
    return {
        "ok": not reason,
        "eligible": eligible,
        "total": len(pool),
        "quality_passed": passed,
        "by_source": by_source,
        "population": population,
        "panel_size": panel_size,
        "reason": reason,
    }


def _source_phrase(by_source: dict[str, int]) -> str:
    """``all 50 synthetic`` / ``30 real and 20 synthetic``. For the message above."""
    if not by_source:
        return "none"
    parts = [f"{n} {source}" for source, n in sorted(by_source.items())]
    if len(parts) == 1:
        return f"all {parts[0]}"
    return " and ".join((", ".join(parts[:-1]), parts[-1]))


async def population_counts(backend: DbBackend | None = None) -> str:
    """``real: 0 · synthetic: 50 · passed the quality gate: 0``. `ARCHITECTURE_UPDATE.md` §3.6.

    Shown beside the population control so the choice is made against the data rather than against
    a default. §1.3 is still open — which population a *study* sweep runs on is a research decision
    — so nothing here picks one; it only makes the state visible.
    """
    from twinlab.orchestrator.panel import POPULATION_SOURCES

    db = backend or get_backend()
    rows = await db.select("twins", None)
    counts: dict[str, int] = {}
    for row in rows:
        source = str(row.get("source") or "unknown")
        counts[source] = counts.get(source, 0) + 1
    passed = await db.count(
        "twin_quality_runs",
        [("eq", "is_latest", True), ("eq", "holdout_set", "H3"), ("eq", "kept", True)],
    )
    known = sorted({s for sources in POPULATION_SOURCES.values() for s in sources})
    parts = [f"{source}: {counts.get(source, 0)}" for source in known]
    # `manual` is in no population, so it is reported separately rather than silently omitted —
    # a count that does not add up is a reason to doubt the screen.
    extra = sorted(set(counts) - set(known))
    parts += [f"{source} (never on a panel): {counts[source]}" for source in extra]
    parts.append(f"passed the quality gate: {passed}")
    return " · ".join(parts)


# ------------------------------------------------------------------ the log


async def events_since(
    session_id: str, after_id: int = 0, *, backend: DbBackend | None = None
) -> list[EventRow]:
    """Rows newer than ``after_id`` only. `docs/04` §7.3.

    The UI keeps the rendered tree in ``gr.State`` and appends; it must never ask for the whole
    stream. ``depth`` is computed from the parent chain **within the rows returned plus the
    parents already seen**, so a child arriving in a later poll still nests correctly.
    """
    db = backend or get_backend()
    rows = await EventLog(session_id, db).since(after_id)
    if not rows:
        return []

    # Parents may have arrived in an earlier poll, so a row's depth can depend on an ancestor that
    # is not in this page. Only the missing ANCESTORS are fetched, walking up one generation at a
    # time — bounded by the depth of the tree (stage → run → child, so one or two extra reads of a
    # handful of rows each), not by the length of the stream.
    #
    # This read was `select("run_events", [eq session_id])` with no limit: the whole session's
    # event stream, every three seconds, in the one function whose contract is that the stream is
    # never re-fetched whole. At sweep scale that is the tens of thousands of rows per UI tick
    # `docs/04` §7.3 exists to forbid.
    parent_of = {r["event_id"]: r.get("parent_event_id") for r in rows}
    for _ in range(32):
        missing = sorted(
            {p for p in parent_of.values() if p is not None and p not in parent_of}
        )
        if not missing:
            break
        fetched = await db.select("run_events", [("in", "event_id", missing)])
        if not fetched:
            break
        for row in fetched:
            parent_of[row["event_id"]] = row.get("parent_event_id")

    def depth_of(event_id: int) -> int:
        depth, cursor, guard = 0, parent_of.get(event_id), 0
        while cursor is not None and guard < 32:
            depth += 1
            cursor = parent_of.get(cursor)
            guard += 1
        return depth

    return [
        EventRow(
            event_id=row["event_id"],
            parent_id=row.get("parent_event_id"),
            # `run_events` timestamps the column `ts`, not `created_at` — `InMemoryBackend`
            # excludes the table from `HAS_CREATED_AT` for exactly that reason. Reading the wrong
            # name made `when` the empty string for every row, so `log_tree` rendered a blank
            # timestamp beside every line and nothing said why.
            when=str(row.get("ts") or ""),
            agent=str(row.get("agent") or ""),
            stage=str(row.get("stage") or ""),
            status=str(row.get("status") or ""),
            message=str(row.get("label") or ""),
            depth=depth_of(row["event_id"]),
            payload=row.get("payload"),
        )
        for row in rows
    ]


async def latest_session_id(backend: DbBackend | None = None) -> str | None:
    """The newest session, for the Agents tab's default log view."""
    db = backend or get_backend()
    rows = await db.select("sessions", None, order=("created_at", True), limit=1)
    return rows[0]["session_id"] if rows else None


def running_job_line(session: Session | None, tested: int) -> str:
    """`docs/06` §3.1's current-job line.

    ``No background job running. Versions tested so far: 7.``
    """
    if session is None or session.status not in ("running", "created"):
        return f"No background job running. Versions tested so far: {tested}."
    return (
        f"Running {session.name}: {session.completed} of {session.iterations} done. "
        f"Versions tested so far: {tested}."
    )


# ------------------------------------------------------------------ control


async def cached_run(
    version_code: str, *, backend: DbBackend | None = None
) -> dict[str, Any] | None:
    """The latest completed run for a code, or ``None``. Drives the amber `cached` badge."""
    run = await RunRepo(backend or get_backend()).latest_completed(version_code)
    return run.model_dump() if run is not None else None


async def ask_twins(
    version_code: str,
    *,
    panel_size: int | None = None,
    population: str = "real",
    inherit_panel_from: str | None = None,
    backend: DbBackend | None = None,
    **runner_kwargs: Any,
) -> Session:
    """Create a session for one cell and start it in the background. Returns immediately.

    Raises :class:`ControlCellError` for `00000`. The Dial board disables the button, but the
    block lives here as well: a control cell reached through any other path — a rerun, an API
    wrapper, a later screen — must be refused the same way (`docs/03` §6.1).

    ``inherit_panel_from`` is how a rerun keeps the original panel (I14). Passing it copies that
    session's ``panel_size`` and ``panel_seed``, so the same twins are drawn; omitting it on a
    rerun would quietly produce a different experiment under the same version code.
    """
    validate_code(version_code)
    if version_code == CONTROL_CODE:
        raise ControlCellError(
            f"{CONTROL_CODE} is a control cell the orchestrator runs at the start of every "
            "session, not a cell to ask by hand (docs/03 §6.1)."
        )

    db = backend or get_backend()
    sessions = SessionRepo(db)

    size = panel_size if panel_size is not None else settings.panel_size
    seed: int | None = None
    name = f"Ask {version_code}"
    if inherit_panel_from is not None:
        origin = await sessions.get(inherit_panel_from)
        size, seed, population = origin.panel_size, origin.panel_seed, origin.population
        name = f"Rerun {version_code}"

    # **Before the row is written** (§3.5 defect 2). A session row for a job that never ran is
    # permanent, and the researcher cannot tell it from one that failed halfway.
    ready = await check_eligibility(population, size, backend=db)
    if not ready["ok"]:
        raise NotReadyToSweep(ready["reason"])

    session = await sessions.create(
        name=name,
        kind="ask",
        iterations=1,
        start_code=version_code,
        panel_size=size,
        panel_seed=seed,
        population=population,
        config=await session_config(),
    )
    await sessions.set_budget(
        session.session_id,
        budget_calc.ask_budget(panel_size=size).model_dump(),
    )
    # The LLM work never runs in the handler's synchronous path (CLAUDE.md rule 12).
    _spawn(
        start_session(session.session_id, backend=db, **_with_runtime(runner_kwargs, db)),
        session_id=session.session_id,
        backend=db,
    )
    return session


async def start_sweep(
    *,
    iterations: int,
    name: str,
    start_code: str | None = None,
    panel_size: int | None = None,
    population: str = "real",
    backend: DbBackend | None = None,
    **runner_kwargs: Any,
) -> Session:
    """Create a sweep session and start it in the background. Returns immediately.

    This is what the Agents tab's *Let the agents choose 6 versions* and *Test all 243 versions*
    press. The two differ only in ``iterations``: both freeze one panel (I14), both run `00000`
    and `SHAM` first without consuming an iteration (`docs/03` §6.1), and both walk the odometer
    from ``start_code``.

    **There is no third control cell and no third workflow** (`CLAUDE.md` rule 9). Six is not a
    sampling scheme the orchestrator knows about; it is 243's loop stopped after six, which is why
    a six-version session and a full sweep are the same code path with one number different.
    """
    db = backend or get_backend()
    sessions = SessionRepo(db)
    size = panel_size if panel_size is not None else settings.panel_size

    # **Before the row is written** (§3.5 defect 2). The draw used to fail inside the background
    # task, leaving a `sessions` row for a job that never ran and a console line nobody read.
    ready = await check_eligibility(population, size, backend=db)
    if not ready["ok"]:
        raise NotReadyToSweep(ready["reason"])

    session = await sessions.create(
        name=name,
        kind="sweep",
        iterations=iterations,
        start_code=start_code or settings.start_code,
        panel_size=size,
        population=population,
        config=await session_config(),
    )
    await sessions.set_budget(
        session.session_id,
        budget_calc.sweep_budget(iterations=iterations, panel_size=size).model_dump(),
    )
    _spawn(
        start_session(session.session_id, backend=db, **_with_runtime(runner_kwargs, db)),
        session_id=session.session_id,
        backend=db,
    )
    return session


async def session_config(backend: DbBackend | None = None) -> dict[str, Any]:
    """What a session freezes onto its `config` column. `docs/09` §4, I11.

    Re-read from `app_config` first, so a session started right after a Settings save runs under
    what the researcher just chose — and records it, so a later threshold change cannot be applied
    retroactively in silence (`docs/08` §2.2).
    """
    from twinlab.services.config import refresh_twin_config, twin_config_version

    cfg = await refresh_twin_config(backend)
    payload = cfg.model_dump()
    payload["style_version"] = settings.style_version
    payload["config_version"] = twin_config_version()
    return payload


def _with_runtime(kwargs: dict[str, Any], db: DbBackend) -> dict[str, Any]:
    """Fill in whatever model callables the caller did not supply.

    The runner takes them injected so the orchestrator stays testable without a provider (M7); a
    test passes its own stubs and they win. Nothing else in this module knows what a model is.
    """
    from twinlab.services.twin_runtime import runner_callables

    supplied = dict(kwargs)
    for key, value in runner_callables(backend=db).items():
        supplied.setdefault(key, value)
    return supplied


async def rerun(
    version_code: str,
    *,
    original_session_id: str,
    new_panel: bool = False,
    backend: DbBackend | None = None,
    **runner_kwargs: Any,
) -> Session:
    """Rerun a cached cell as a real, visible session. I14.

    ``new_panel`` must be an explicit researcher choice. The default inherits, because a rerun
    with a different panel is not a rerun.
    """
    return await ask_twins(
        version_code,
        inherit_panel_from=None if new_panel else original_session_id,
        backend=backend,
        **runner_kwargs,
    )


async def resume_session(
    session_id: str, *, backend: DbBackend | None = None, **runner_kwargs: Any
) -> Session:
    """Resume a paused session. **Resume is just start** (`docs/04` §3.4).

    The session reads its own `cursor_index` and frozen panel, and every stage is idempotent and
    cache-keyed, so a half-finished run continues without re-paying: `answered_twins` skips the
    twins that answered, and the paragraph and variant caches survive a restart.
    """
    db = backend or get_backend()
    session = await SessionRepo(db).get(session_id)
    # A session with a frozen panel already has its twins and re-checks nothing: I14 means the
    # panel is read, not redrawn. One that died *before* the draw is the case §3.5's diagnostic
    # points at — it fails identically on every press, so it is refused in the page rather than in
    # the console.
    if not await PanelRepo(db).get(session_id):
        ready = await check_eligibility(
            session.population, session.panel_size, backend=db
        )
        if not ready["ok"]:
            raise NotReadyToSweep(ready["reason"])
    _spawn(
        start_session(session_id, backend=db, **_with_runtime(runner_kwargs, db)),
        session_id=session_id,
        backend=db,
    )
    return session


async def paused_sessions(backend: DbBackend | None = None) -> list[Session]:
    """Every session a resume could continue, newest first.

    `ui/` may not reach `db/` (`ARCHITECTURE.md` §4), so the Agents tab asks for this rather than
    opening a repository. A session is `paused` either because the researcher stopped it or
    because a restart killed it and `_pause_interrupted` marked it so at boot — the two are the
    same thing to a resume, which is why nothing here distinguishes them.
    """
    sessions = await SessionRepo(backend or get_backend()).by_status("paused")
    return sorted(sessions, key=lambda s: s.session_id)


async def get_session(session_id: str, *, backend: DbBackend | None = None) -> Session:
    """One session, for the Agents tab's current-job line."""
    return await SessionRepo(backend or get_backend()).get(session_id)


async def panel_for(
    session_id: str, *, backend: DbBackend | None = None
) -> frozenset[str]:
    """The frozen panel of a session, for the interaction panel check (I14)."""
    members = await PanelRepo(backend or get_backend()).get(session_id)
    return frozenset(m.twin_id for m in members)


def stop(session_id: str) -> bool:
    """Cooperative stop. ``False`` when no runner is registered for that session."""
    return request_stop(session_id)


def is_running(session_id: str) -> bool:
    runner = get_runner(session_id)
    return runner is not None and not runner.stop_requested


def code_index(version_code: str) -> int:
    """The odometer index of a code, for the sweep's start position."""
    return index_from_code(version_code)


__all__ = [
    "STOP_NOTE",
    "WORKFLOW_BUTTONS",
    "ControlCellError",
    "NotReadyToSweep",
    "SessionAlreadyRunning",
    "ask_budget_view",
    "ask_twins",
    "budget_view",
    "cached_run",
    "check_eligibility",
    "code_index",
    "events_since",
    "get_session",
    "is_running",
    "latest_session_id",
    "panel_for",
    "paused_sessions",
    "population_counts",
    "quality_budget_view",
    "rerun",
    "resume_session",
    "running_job_line",
    "stop",
    "session_config",
    "start_sweep",
    "sweep_budget_view",
]
