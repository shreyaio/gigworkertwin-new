"""The session state machine. `docs/04` §3. Serves I3, I9, I14 and I15.

One :class:`SessionRunner` per session, in a process-level registry keyed by `session_id`. **At most
one active session per process** (`max_active_sessions`, default 1): with one provider slot, two
concurrent sessions would interleave and both would crawl, so a second start is rejected with a
clear
message rather than queued silently.

Four properties the rest of the build depends on:

* **Every stage is a checkpoint and every stage is idempotent.** A half-finished run resumes without
  re-paying: paragraphs are cached on `(lever, dial, style_version)` (I4) and `twin_answers` is
  unique on `(run_id, twin_id, wording)`, so answered twins are skipped.
* **Stop is cooperative.** It sets a flag checked at each checkpoint and exits after the current
  unit. It never kills mid-model-call, so no partial answer is ever written.
* **A fresh session freezes its panel, then runs `00000` and `SHAM`, before the first swept code.**
  The controls do not consume an iteration (`docs/03` §6.1).
* **Nothing auto-restarts.** A session found `running` at boot was killed by a restart; it is marked
  `paused` and says so in the log. The researcher decides.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import (
    AnswerRepo,
    ControlAnswerRepo,
    PanelRepo,
    RunRepo,
    SessionRepo,
    VariantRepo,
)
from twinlab.models.run import Session
from twinlab.models.twin import PanelMember
from twinlab.orchestrator.events import EventLog
from twinlab.orchestrator.odometer import (
    CONTROL_CODE,
    N_CODES,
    SHAM_CODE,
    code_from_index,
    index_from_code,
)
from twinlab.orchestrator.panel import draw_panel

log = logging.getLogger(__name__)

#: The two control cells, in the order a fresh session records them. **Exactly two, ever**
#: (`CLAUDE.md` rule 9). They consume no iteration.
#:
#: **Nobody is asked here.** Since RESEARCHER 2026-10-05 each twin answers both controls once per
#: config, inside the quality gate (`docs/08` §2.4). A session records each control from its panel's
#: stored answers, under its own config fingerprint, so a session costs its version calls only.
CONTROL_CELLS: tuple[str, ...] = (CONTROL_CODE, SHAM_CODE)


class OrchestratorError(RuntimeError):
    """A session that must not start or continue."""


class SessionAlreadyRunning(OrchestratorError):
    """`max_active_sessions` reached. Rejected loudly, never queued silently (`docs/04` §3.1)."""


class ControlCellError(OrchestratorError):
    """`00000` is the orchestrator's to run, not a cell a researcher pokes at (`docs/03` §6.1)."""


class SessionRunner:
    """Runs one session. Holds the stop flag and the per-session event log.

    ``ask_twin`` and ``render_and_check`` are injected rather than imported so the loop is testable
    without a provider: the orchestrator's job is sequencing and checkpointing, and that is what the
    M7 tests exercise.
    """

    def __init__(
        self,
        session_id: str,
        *,
        backend: DbBackend | None = None,
        render_and_check: Any = None,
        ask_twin: Any = None,
        analyse: Any = None,
        candidates: Any = None,
    ) -> None:
        self.session_id = session_id
        self.db = backend or get_backend()
        self.sessions = SessionRepo(self.db)
        self.runs = RunRepo(self.db)
        self.answers = AnswerRepo(self.db)
        self.panels = PanelRepo(self.db)
        self.variants = VariantRepo(self.db)
        self.events = EventLog(session_id, self.db)
        self._stop = asyncio.Event()
        self._render_and_check = render_and_check
        self._ask_twin = ask_twin
        self._analyse = analyse
        self._candidates = candidates
        #: Calls the semaphore actually admitted, for the budget's predicted-vs-actual comparison.
        self.calls_made = 0
        self.sem = asyncio.Semaphore(settings.max_concurrency)

    # ---------------------------------------------------------------- stop

    def request_stop(self) -> None:
        """Cooperative stop. Honoured at the next checkpoint (`ARCHITECTURE.md` §7.4)."""
        self._stop.set()

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    # ---------------------------------------------------------------- the loop

    async def run(self) -> Session:
        """`docs/04` §3.3. Returns the session in its final state."""
        session = await self.sessions.get(self.session_id)
        await self.sessions.set_status(self.session_id, "running")
        parent = await self.events.emit(
            stage="control", label=f"session {session.name}", payload={"kind": session.kind}
        )
        try:
            panel = await self.stage_panel(session)
            await self.stage_reconstruction(session, panel)

            if session.cursor_index is None:
                # Fresh session: the two control floors, assembled from the panel's stored answers.
                # They consume no iteration and no model call.
                for code in CONTROL_CELLS:
                    await self.stage_control_floor(session, code, panel)
                    if self.stop_requested:
                        return await self._pause(parent)
                session.cursor_index = index_from_code(session.start_code)
                await self.sessions.set_cursor(self.session_id, session.cursor_index)

            while session.completed < session.iterations:
                if self.stop_requested:
                    return await self._pause(parent)
                code = code_from_index(session.cursor_index)
                await self.execute_run(session, code, panel)
                if self.stop_requested:
                    # Checked here, not only at the top of the loop. A stop raised *during* this
                    # cell leaves it unfinished, and counting it would advance the cursor past a
                    # cell that was never put to the whole panel — on the last iteration the
                    # session would even be marked `completed` with a `pending` run inside it.
                    # The cursor stays where it is; resume re-enters this cell and, because
                    # `answered_twins` skips whoever answered, pays only for the twins that are
                    # left.
                    return await self._pause(parent)
                session.completed += 1
                session.cursor_index = (session.cursor_index + 1) % N_CODES
                # Written AFTER the run, so a crash re-runs at most one cell — and that cell is
                # itself idempotent, so re-running it costs nothing already paid for.
                await self.sessions.advance(
                    self.session_id, session.cursor_index, session.completed
                )

            await self.sessions.set_status(self.session_id, "completed")
            await self.events.set_status(parent, "ok")
        except Exception as exc:
            await self.sessions.fail(self.session_id, repr(exc))
            await self.events.set_status(
                parent, "error", label=f"session failed: {type(exc).__name__}"
            )
            await self.events.emit(
                stage="control", label=f"{type(exc).__name__}: {exc}", status="error",
                parent_event_id=parent,
            )
            raise
        finally:
            _REGISTRY.pop(self.session_id, None)
        return await self.sessions.get(self.session_id)

    async def _pause(self, parent: int) -> Session:
        """Leave `cursor_index` at the next unstarted cell and stop. `docs/04` §3.4."""
        await self.sessions.set_status(self.session_id, "paused")
        await self.events.emit(
            stage="control", label="stop requested; paused for resume", status="ok",
            parent_event_id=parent,
        )
        await self.events.set_status(parent, "ok")
        _REGISTRY.pop(self.session_id, None)
        return await self.sessions.get(self.session_id)

    # ---------------------------------------------------------------- session-level stages

    async def stage_panel(self, session: Session) -> list[PanelMember]:
        """Draw and freeze the panel, or read the frozen one. Idempotent. I14.

        A session that already has a panel **keeps it**. This is the one stage where idempotence is
        an invariant rather than an optimisation: redrawing mid-session would mean two cells
        answered
        by different twins inside one experiment.
        """
        existing = await self.panels.get(self.session_id)
        if existing:
            await self.events.emit(
                stage="panel", label=f"panel of {len(existing)} (frozen)", status="ok",
                payload={"twins_n": len(existing), "frozen": True},
            )
            return existing

        parent = await self.events.emit(stage="panel", label="drawing the panel")
        candidates = await self._eligible(session)
        panel = draw_panel(
            candidates,
            panel_size=session.panel_size,
            panel_seed=session.panel_seed,
            population=session.population,
        )
        await self.panels.freeze(self.session_id, panel)
        await self.events.set_status(
            parent, "ok",
            label=f"panel of {len(panel)}",
            payload={
                "twins_n": len(panel),
                "panel_seed": session.panel_seed,
                "strata": sorted({m.stratum for m in panel}),
            },
        )
        return panel

    async def _eligible(self, session: Session) -> list[Any]:
        if self._candidates is None:
            raise OrchestratorError(
                "no candidate source: the runner needs `candidates` to draw a panel. A panel of "
                "zero would make every run twins_n = 0, which is a failure, never a result (I15)."
            )
        result = self._candidates(session)
        if hasattr(result, "__await__"):
            result = await result
        return list(result)

    async def stage_reconstruction(self, session: Session, panel: list[PanelMember]) -> None:
        """Rebuild any missing persona. `docs/04` §7's label-rewriting pattern.

        One parent row whose label ticks through twin ids, rather than one row per twin: at panel
        scale the log has to stay readable.
        """
        parent = await self.events.emit(stage="reconstruction", label="reconstruction")
        for member in panel:
            await self.events.set_label(parent, f"reconstruction ({member.twin_id})")
        await self.events.set_status(
            parent, "ok", label=f"reconstruction ({len(panel)} twins)",
            payload={"twins_n": len(panel)},
        )

    # ---------------------------------------------------------------- control floors

    async def stage_control_floor(
        self, session: Session, code: str, panel: list[PanelMember]
    ) -> Any:
        """Record one control cell from the panel's stored answers. No model call. `docs/08` §2.4.

        Every panel twin must already hold this control under **this session's** config
        fingerprint. A missing one is refused, not asked for here: the draw only admits twins with
        both controls under the live config (`services/config_match.qualified_twin_ids`), so a gap
        means the config or the gate changed underneath the session, and that is for the researcher
        to resolve by running the quality test again (I14, I15).
        """
        run = await self.runs.get_or_create(self.session_id, code)
        if run.status == "completed":
            await self.events.emit(
                stage="control", label=f"{code} floor already recorded", status="skipped",
                run_id=run.run_id, payload={"version_code": code},
            )
            return run

        if not panel:
            # I15: a floor over zero twins is a failure, never an index of 0.000.
            raise OrchestratorError(f"{code} floor over an empty panel is a failure (I15)")
        fingerprint = str(session.config.get("config_fingerprint") or "")
        if not fingerprint:
            raise OrchestratorError(
                f"session {self.session_id[:8]} has no config fingerprint, so its {code} floor "
                "cannot be matched to a quality test. Start a new session."
            )

        parent = await self.events.emit(
            stage="control", label=f"{code} floor (from the quality test)", run_id=run.run_id,
            payload={"version_code": code, "config_fingerprint": fingerprint},
        )
        await self.runs.set_status(run.run_id, "running")
        controls = ControlAnswerRepo(self.db)
        for member in panel:
            stored = await controls.get(member.twin_id, code, fingerprint)
            if stored is None:
                raise OrchestratorError(
                    f"twin {member.twin_id} has no {code} answer under config {fingerprint}. The "
                    "quality test has to be run again for this config before a session can use "
                    "this panel."
                )
            await self.answers.record(
                run_id=run.run_id,
                twin_id=member.twin_id,
                answers={k: int(v) for k, v in dict(stored["answers"]).items()},
                lever_order=[int(x) for x in stored["lever_order"]],
                seed=int(stored["seed"]),
                wording=str(stored["wording"]),
                model=str(stored["model"]),
                prompt_version=stored.get("prompt_version"),
                retries=int(stored.get("retries") or 0),
            )

        metrics, index_value, prose = await self._analyse_run(run.run_id, code, parent)
        completed = await self.runs.complete(
            run.run_id, twins_n=len(panel), metrics=metrics,
            index_value=index_value, analysis=prose,
        )
        await self.events.set_status(
            parent, "ok", label=f"{code} floor ({len(panel)} twins)",
            payload={"version_code": code, "twins_n": len(panel), "index": index_value},
        )
        return completed

    # ---------------------------------------------------------------- per-code

    async def execute_run(
        self, session: Session, code: str, panel: list[PanelMember]
    ) -> Any:
        """One version code through the five stages. `docs/04` §3.3.

        Resumes mid-flight: a run already `completed` in this session returns immediately, and
        `ask_panel` skips twins that already answered.
        """
        run = await self.runs.get_or_create(self.session_id, code)
        if run.status == "completed":
            await self.events.emit(
                stage="control", label=f"{code} already completed", status="skipped",
                run_id=run.run_id, payload={"version_code": code},
            )
            return run

        parent = await self.events.emit(
            stage="lookup", label=code, run_id=run.run_id, payload={"version_code": code}
        )
        await self.runs.set_status(run.run_id, "running")

        variant, report = await self._render(session, code, run.run_id, parent)

        # I3: an unverified variant never reaches a twin. One containment hit fails the cell.
        if not report.passed:
            await self.events.set_status(parent, "error", label=f"{code} checker failed")
            await self.events.emit(
                stage="check", label="checker failed", status="error", run_id=run.run_id,
                parent_event_id=parent,
                payload={"containment": report.containment, "notes": report.notes[:400]},
            )
            # The loop continues to the next code: one bad cell is not a bad sweep.
            return await self.runs.fail(run.run_id, f"checker failed: {report.notes[:400]}")

        twins_n, interrupted = await self.ask_panel(
            session, run.run_id, code, variant, panel, parent
        )

        if twins_n == 0:
            # I15. Never `completed` with an index of 0.000.
            await self.events.set_status(parent, "error", label=f"{code} no twins answered")
            return await self.runs.fail(
                run.run_id, "no twins answered: a run with no twins is failed, never a result (I15)"
            )

        if interrupted:
            # A stop cut the ask short, so this cell was put to part of the panel. Completing it
            # here would be permanent: `execute_run` skips a `completed` run on resume, so the
            # cell would keep a short panel for the rest of the study while its neighbours kept
            # the full one — a cell answered by a different set of twins (I14), recorded as a
            # result. It goes back to `pending` instead and resume asks the twins that are left,
            # which costs nothing already paid for: `answered_twins` skips the ones who answered.
            await self.runs.set_status(run.run_id, "pending")
            await self.events.set_status(
                parent, "ok",
                label=f"{code} paused after {twins_n} of {len(panel)} twins",
                payload={
                    "version_code": code, "answered": twins_n, "panel_size": len(panel),
                    "completed": False, "reason": "stop requested mid-panel",
                },
            )
            return await self.runs.get(run.run_id)

        metrics, index_value, prose = await self._analyse_run(run.run_id, code, parent)
        completed = await self.runs.complete(
            run.run_id, twins_n=twins_n, metrics=metrics,
            index_value=index_value, analysis=prose,
        )
        await self.events.set_status(
            parent, "ok", label=f"{code} ({twins_n} twins)",
            payload={"version_code": code, "twins_n": twins_n, "index": index_value},
        )
        return completed

    async def _render(self, session: Session, code: str, run_id: str, parent: int) -> Any:
        """`render` and `check`, cache-keyed on `(version_code, style_version)`. I4."""
        style_version = str(session.config.get("style_version", "v1"))
        event = await self.events.emit(
            stage="render", label=f"render {code}", run_id=run_id, parent_event_id=parent
        )
        if self._render_and_check is None:
            raise OrchestratorError("the runner needs `render_and_check` to produce a variant")
        variant, report = await self._render_and_check(code, style_version)
        stored = await self.variants.put(
            version_code=code,
            style_version=style_version,
            delta_spec={"version_code": code},
            delta_hash=variant.delta_hash,
            paragraphs={k: v.text for k, v in variant.paragraphs.items()},
            checker=report.model_dump(),
        )
        await self.runs.attach_variant(run_id, stored["variant_id"])
        await self.events.set_status(
            event, "ok",
            payload={
                "variant_id": stored["variant_id"],
                "delta_hash": variant.delta_hash,
                "style_version": style_version,
                "passed": report.passed,
            },
        )
        return variant, report

    async def ask_panel(
        self,
        session: Session,
        run_id: str,
        code: str,
        variant: Any,
        panel: list[PanelMember],
        parent: int,
    ) -> tuple[int, bool]:
        """Put the cell to every twin on the frozen panel. Skips those who already answered.

        Returns ``(answered, interrupted)``. ``answered`` is what `twins_n` records and what I15
        turns on. A twin whose call fails **fails for that cell only**: it stays on the panel and
        in the study, because only the quality gate drops twins.

        ``interrupted`` distinguishes the two ways a panel can come up short, which the caller must
        not conflate. A twin that *failed* is data — the cell is still a measurement, and the
        shortfall is recorded on the event so it is visible rather than inferred. A stop that cut
        the loop short is not data: the remaining twins were never asked, and the cell is
        unfinished rather than smaller.
        """
        wording = str(session.config.get("wording", "A"))
        already = await self.answers.answered_twins(run_id, wording)
        event = await self.events.emit(
            stage="ask", label=f"ask {len(panel)} twins", run_id=run_id, parent_event_id=parent,
            payload={"panel_size": len(panel), "already_answered": len(already)},
        )

        answered = set(already)
        interrupted = False
        for member in panel:
            if self.stop_requested:
                interrupted = True
                break
            if member.twin_id in already:
                await self.events.emit(
                    stage="ask", label=member.twin_id, status="skipped", run_id=run_id,
                    parent_event_id=event, payload={"cached": True},
                )
                continue
            await self.events.set_label(event, f"ask {member.twin_id}")
            try:
                async with self.sem:
                    self.calls_made += 1
                    recorded = await self._ask_twin(session, run_id, code, variant, member)
            except Exception as exc:
                await self.events.emit(
                    stage="ask", label=member.twin_id, status="error", run_id=run_id,
                    parent_event_id=event,
                    payload={"error": f"{type(exc).__name__}: {exc}"[:400]},
                )
                continue
            if recorded is None:
                await self.events.emit(
                    stage="ask", label=member.twin_id, status="error", run_id=run_id,
                    parent_event_id=event, payload={"failed_for_cell": True},
                )
                continue
            answered.add(member.twin_id)
            await self.events.emit(
                stage="ask", label=member.twin_id, status="ok", run_id=run_id,
                parent_event_id=event,
                payload={k: recorded[k] for k in ("retries", "model") if k in recorded},
            )

        # `short_by` is emitted even when zero, so "every twin answered" is a recorded fact rather
        # than the absence of a note. A cell answered by fewer twins than its neighbours is
        # comparable only if the reader can see that it was.
        await self.events.set_status(
            event, "ok", label=f"ask ({len(answered)} of {len(panel)})",
            payload={
                "answered": len(answered),
                "panel_size": len(panel),
                "short_by": len(panel) - len(answered),
                "interrupted": interrupted,
            },
        )
        return len(answered), interrupted

    async def _analyse_run(self, run_id: str, code: str, parent: int) -> tuple:
        event = await self.events.emit(
            stage="analyse", label=f"analyse {code}", run_id=run_id, parent_event_id=parent
        )
        if self._analyse is None:
            await self.events.set_status(event, "skipped", label="analyse (M8)")
            return None, None, None
        metrics, index_value, prose = await self._analyse(run_id)
        await self.events.set_status(
            event, "ok", payload={"index": index_value, "metrics_n": len(metrics or {})}
        )
        return metrics, index_value, prose


# --------------------------------------------------------------------------- the registry

_REGISTRY: dict[str, SessionRunner] = {}


def active_runners() -> dict[str, SessionRunner]:
    return dict(_REGISTRY)


def register(runner: SessionRunner) -> SessionRunner:
    """At most `max_active_sessions` at once. `docs/04` §3.1.

    Rejected loudly rather than queued: with one provider slot, two concurrent sessions interleave
    and both crawl, and a silent queue would look like a hung UI.
    """
    if runner.session_id in _REGISTRY:
        raise SessionAlreadyRunning(f"session {runner.session_id} is already running")
    if len(_REGISTRY) >= settings.max_active_sessions:
        raise SessionAlreadyRunning(
            f"{len(_REGISTRY)} session(s) already active and max_active_sessions is "
            f"{settings.max_active_sessions}. Stop the running session first — with one provider "
            "slot, two concurrent sessions interleave and both crawl."
        )
    _REGISTRY[runner.session_id] = runner
    return runner


def get_runner(session_id: str) -> SessionRunner | None:
    return _REGISTRY.get(session_id)


def request_stop(session_id: str) -> bool:
    """Ask a running session to stop at its next checkpoint. ``False`` if it is not running."""
    runner = _REGISTRY.get(session_id)
    if runner is None:
        return False
    runner.request_stop()
    return True


def clear_registry() -> None:
    """Test hook. The application never calls this."""
    _REGISTRY.clear()


# --------------------------------------------------------------------------- crash recovery


async def resume_interrupted_sessions(backend: DbBackend | None = None) -> list[str]:
    """Mark sessions found `running` at boot as `paused`. **Nothing auto-restarts.**

    `docs/04` §3.4: a session still `running` at startup was killed by a restart. It is paused and
    the log says plainly what happened, and the researcher decides whether to resume. Auto-
    restarting
    would begin spending credits on a process nobody asked to start, and on a sleeping free Space
    this is a routine event rather than an exception.

    Returns the session ids it paused.
    """
    db = backend or get_backend()
    repo = SessionRepo(db)
    paused: list[str] = []
    for session in await repo.by_status("running"):
        await repo.set_status(session.session_id, "paused")
        await EventLog(session.session_id, db).emit(
            stage="control",
            label="session interrupted by a restart; paused for resume",
            status="error",
            payload={"auto_restarted": False},
        )
        paused.append(session.session_id)
    return paused


async def start_session(
    session_id: str, *, backend: DbBackend | None = None, **kwargs: Any
) -> Session:
    """Create, register and run a session. **Resume is just start** (`docs/04` §3.4).

    A `paused` or `stopped` session reads its `cursor_index` and continues; because every stage is
    idempotent and cache-keyed, a half-finished run resumes without re-paying.
    """
    runner = register(SessionRunner(session_id, backend=backend, **kwargs))
    return await runner.run()
