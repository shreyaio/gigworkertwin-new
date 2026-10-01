"""Running the quality gate. `docs/08` §2 (H3) and §3 (H2). Serves I9, I14 and I15.

`validity/quality.py` holds the arithmetic and knows nothing about a database or a model. This is
the part that renders the six Part 17 stimuli through the **normal pipeline**, puts them to a
twin, scores the result against that twin's own driver, and appends one `twin_quality_runs` row
per holdout set.

**This is the dominant cost of the study** (`docs/10`), not the sweep: six version codes per
repeat at the default three repeats is 18 calls per twin, ~9,000 at N=500. Everything here is
serial by construction, because the free provider tier permits one concurrent request.

Four things are commitments rather than plumbing:

* **The stimuli are rendered through the real pipeline** — same design agent, same Checker, same
  style version (`docs/08` §2.1 step 1). They are not specially written vignettes, and a stimulus
  the Checker failed is never shown to a twin (I3).
* **No baseline is shown** (§2.1 step 2). The human had none either, so `show_baseline` is
  overridden to `False` here whatever `TwinConfig` says.
* **A dropped twin is dropped, not tuned** (§2.4). There is no retry-until-it-passes path in this
  module, and the verdict is written once per gate run.
* **A score over zero scorable items is no score** (I15). `score_holdout` raises, the row is not
  written, and the twin is recorded as *not run* rather than as a perfect twin.
"""

from __future__ import annotations

import asyncio
import logging

from config.settings import settings
from twinlab.agents.contract import ContractError
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import SessionRepo, VariantRepo
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.run import Session
from twinlab.models.twin import QualityScore, TwinConfig
from twinlab.orchestrator.events import EventLog
from twinlab.services.twin_runtime import (
    TwinPathError,
    ask_items,
    driver_answers,
    render_and_check,
)
from twinlab.validity.quality import (
    QualityScoreEmpty,
    average_scores,
    h2_arm_for,
    h3_correlations,
    quality_row,
    score_holdout,
)

log = logging.getLogger(__name__)

#: The three outcomes each Part 17 round reads, and the metric name each maps to. `docs/08` §3.3.
H3_OUTCOMES: dict[str, str] = {"FAIR": "fairness", "PUSH": "pushback", "KEEP": "staying"}


class QualityGateError(RuntimeError):
    """A quality run that must not start or continue."""


# --------------------------------------------------------------------------- the registry

#: Strong references to running gate tasks, plus the stop flags the UI's Stop sets.
#: `asyncio` keeps only a weak reference to a running task, so a bare `create_task` whose result
#: nobody holds can be garbage-collected mid-gate — the documented failure mode, not a
#: theoretical one.
_TASKS: dict[str, asyncio.Task] = {}
_STOPS: dict[str, asyncio.Event] = {}


def is_running(session_id: str) -> bool:
    task = _TASKS.get(session_id)
    return task is not None and not task.done()


def request_stop(session_id: str) -> bool:
    """Cooperative stop, honoured between twins. ``False`` when nothing is running for that id."""
    event = _STOPS.get(session_id)
    if event is None:
        return False
    event.set()
    return True


def active_gate() -> str | None:
    """The session id of the gate currently running in this process, if any."""
    for session_id, task in _TASKS.items():
        if not task.done():
            return session_id
    return None


# --------------------------------------------------------------------------- item sets


def h3_items(ref: ReferenceData | None = None) -> dict[int, dict[str, tuple[str, int]]]:
    """``version_shown → {item_id: (stem, points)}``. Three items per round, six rounds.

    Built from the frozen register, never from a list here: `docs/01` §3.6 already encodes which
    code each Part 17 item belongs to, and a second copy would drift from it.
    """
    ref = ref or reference()
    out: dict[int, dict[str, tuple[str, int]]] = {}
    for item_id in ref.holdout_h3_item_ids:
        item = ref.items[item_id]
        if item.version_shown is None:
            raise QualityGateError(
                f"{item_id} is an H3 holdout with no `version_shown`, so there is no round to ask "
                "it in. The register is frozen; this is a data defect, not a case to skip."
            )
        out.setdefault(int(item.version_shown), {})[item_id] = (
            item.stem,
            ref.scale_points(item_id),
        )
    return out


def h3_items_by_outcome(ref: ReferenceData | None = None) -> dict[str, list[str]]:
    """``metric → the six item ids across the six versions``, for the per-outcome Pearson `r`."""
    ref = ref or reference()
    out: dict[str, list[str]] = {metric: [] for metric in H3_OUTCOMES.values()}
    for item_id in ref.holdout_h3_item_ids:
        suffix = item_id.rsplit("_", 1)[-1]
        if suffix not in H3_OUTCOMES:
            raise QualityGateError(
                f"{item_id} does not end in one of {sorted(H3_OUTCOMES)}, so the outcome it "
                "measures is unknown. It is not guessed."
            )
        out[H3_OUTCOMES[suffix]].append(item_id)
    return out


def h2_items(ref: ReferenceData | None = None) -> dict[str, tuple[str, int]]:
    ref = ref or reference()
    return {i: (ref.items[i].stem, ref.scale_points(i)) for i in ref.holdout_h2_item_ids}


def arm_code(arm_id: str, ref: ReferenceData | None = None) -> str:
    """The version code an arm shows. `docs/01` §5."""
    ref = ref or reference()
    arm = ref.arms.get(arm_id)
    if arm is None:
        raise QualityGateError(
            f"unknown arm {arm_id!r}; the four arms are {sorted(ref.arms)} (docs/01 §5)"
        )
    return arm.version_code


# --------------------------------------------------------------------------- the gate


async def start_quality_gate(
    *,
    twin_ids: list[str] | None = None,
    repeats: int | None = None,
    include_h2: bool = True,
    backend: DbBackend | None = None,
) -> Session:
    """Create a quality session and run it in the background. Returns immediately.

    **No model call happens in this function** (`CLAUDE.md` rule 12): it writes the session row,
    hands the work to the event loop and returns, exactly as `services.runs.ask_twins` does. The
    Agents tab's log is how the researcher watches it, because every stage emits into
    `run_events` under this session id.
    """
    db = backend or get_backend()
    if active_gate() is not None:
        raise QualityGateError(
            "a quality gate is already running in this process. With one provider slot, two "
            "would interleave and both would crawl — stop the running one first."
        )

    from twinlab.services.config import refresh_twin_config, twin_config_version
    from twinlab.services.lab import twin_rows
    from twinlab.services.runs import session_config

    config = await session_config(db)
    cfg = await refresh_twin_config(db)
    times = int(repeats if repeats is not None else cfg.quality_runs_per_twin)
    if times < 1:
        raise QualityGateError("quality_runs_per_twin counts the first run, so it is at least 1")

    chosen = list(twin_ids or [])
    if not chosen:
        chosen = [row.twin_id for row in await twin_rows(backend=db)]
    if not chosen:
        raise QualityGateError(
            "there are no twins to test. Import twins from the survey in Twin Lab → Settings, or "
            "make some in the Generator."
        )

    session = await SessionRepo(db).create(
        name=f"Quality gate ({len(chosen)} twins × {times})",
        kind="quality",
        iterations=0,
        start_code=settings.start_code,
        panel_size=len(chosen),
        config={**config, "quality_runs_per_twin": times, "twin_ids": chosen[:200]},
    )
    from twinlab.orchestrator import budget as budget_calc

    await SessionRepo(db).set_budget(
        session.session_id,
        budget_calc.quality_budget(twins=len(chosen), repeats=times).model_dump(),
    )

    stop = asyncio.Event()
    _STOPS[session.session_id] = stop
    task = asyncio.create_task(
        run_quality_gate(
            session_id=session.session_id,
            twin_ids=chosen,
            repeats=times,
            include_h2=include_h2,
            config=cfg,
            config_version=twin_config_version(),
            stop=stop,
            backend=db,
        )
    )
    _TASKS[session.session_id] = task

    def _done(finished: asyncio.Task) -> None:
        _STOPS.pop(session.session_id, None)
        if not finished.cancelled() and finished.exception() is not None:
            log.error("quality gate failed: %r", finished.exception())

    task.add_done_callback(_done)
    return session


async def run_quality_gate(
    *,
    session_id: str,
    twin_ids: list[str],
    repeats: int,
    include_h2: bool,
    config: TwinConfig,
    config_version: int,
    stop: asyncio.Event | None = None,
    backend: DbBackend | None = None,
) -> dict[str, bool | None]:
    """The gate itself. Returns ``twin_id → kept`` (``None`` where no score could be taken).

    Runs as a background task so the researcher can change tab. Every stage emits into
    `run_events`, so the Agents tab's log shows the six renders, then one row per twin whose label
    ticks through the rounds — the label-rewriting pattern of `docs/04` §7, because at N=500 a row
    per call is not a log a person can read.
    """
    db = backend or get_backend()
    ref = reference()
    sessions = SessionRepo(db)
    events = EventLog(session_id, db)
    stop = stop or asyncio.Event()

    await sessions.set_status(session_id, "running")
    parent = await events.emit(
        stage="control",
        label=f"quality gate: {len(twin_ids)} twin(s) × {repeats}",
        payload={"twins_n": len(twin_ids), "repeats": repeats, "include_h2": include_h2},
    )
    verdicts: dict[str, bool | None] = {}
    try:
        stimuli = await _render_stimuli(
            session_id, ref, events, parent, db, include_h2=include_h2
        )
        done = 0
        for twin_id in twin_ids:
            if stop.is_set():
                await events.emit(
                    stage="control", label="stop requested; gate paused", status="ok",
                    parent_event_id=parent,
                )
                await sessions.set_status(session_id, "paused")
                await sessions.advance(session_id, 0, done)
                return verdicts
            verdicts[twin_id] = await _gate_one_twin(
                twin_id=twin_id,
                stimuli=stimuli,
                repeats=repeats,
                include_h2=include_h2,
                config=config,
                config_version=config_version,
                session_id=session_id,
                ref=ref,
                events=events,
                parent=parent,
                db=db,
            )
            done += 1
            await sessions.advance(session_id, 0, done)

        kept = sum(1 for v in verdicts.values() if v)
        scored = sum(1 for v in verdicts.values() if v is not None)
        await events.set_status(
            parent, "ok",
            label=f"quality gate: {kept} of {scored} twin(s) kept",
            payload={"kept": kept, "scored": scored, "asked": len(verdicts)},
        )
        await sessions.set_status(session_id, "completed")
    except Exception as exc:
        await sessions.fail(session_id, repr(exc))
        await events.set_status(parent, "error", label=f"quality gate failed: {type(exc).__name__}")
        await events.emit(
            stage="control", label=f"{type(exc).__name__}: {exc}"[:400], status="error",
            parent_event_id=parent,
        )
        raise
    return verdicts


async def _render_stimuli(
    session_id: str,
    ref: ReferenceData,
    events: EventLog,
    parent: int,
    db: DbBackend,
    *,
    include_h2: bool,
) -> dict[str, dict[str, str]]:
    """Render and check every code the gate will show. `docs/08` §2.1 step 1.

    **An unverified variant never reaches a twin** (I3), so a code whose Checker report fails
    stops the gate rather than being shown with a note. Every code is stored on `variants`, which
    is both the durable cache and what `services/lab.scenario_paragraphs` reads back — the
    researcher can then see exactly what each twin was shown.
    """
    codes = list(ref.h3_version_codes)
    if include_h2:
        for arm in ref.arms.values():
            if arm.version_code not in codes:
                codes.append(arm.version_code)

    style_version = settings.style_version
    event = await events.emit(
        stage="render", label=f"render {len(codes)} stimuli", parent_event_id=parent,
        payload={"codes": codes, "style_version": style_version},
    )
    out: dict[str, dict[str, str]] = {}
    for code in codes:
        await events.set_label(event, f"render {code}")
        variant, report = await render_and_check(code, style_version, backend=db)
        await VariantRepo(db).put(
            version_code=code,
            style_version=style_version,
            delta_spec={"version_code": code},
            delta_hash=variant.delta_hash,
            paragraphs={k: v.text for k, v in variant.paragraphs.items()},
            checker=report.model_dump(),
        )
        if not report.passed:
            await events.set_status(
                event, "error", label=f"{code} failed the Checker",
                payload={"containment": report.containment, "notes": report.notes[:400]},
            )
            raise QualityGateError(
                f"{code} failed the Checker, so it must not be shown to a twin (I3). "
                f"{report.notes[:300]}"
            )
        out[code] = {k: v.text for k, v in variant.paragraphs.items()}
    await events.set_status(
        event, "ok", label=f"render ({len(out)} stimuli)", payload={"codes": sorted(out)}
    )
    return out


async def _gate_one_twin(
    *,
    twin_id: str,
    stimuli: dict[str, dict[str, str]],
    repeats: int,
    include_h2: bool,
    config: TwinConfig,
    config_version: int,
    session_id: str,
    ref: ReferenceData,
    events: EventLog,
    parent: int,
    db: DbBackend,
) -> bool | None:
    """H3 for one twin, then H2. Returns the H3 verdict, or ``None`` when nothing scored."""
    event = await events.emit(
        stage="ask", label=f"quality {twin_id}", parent_event_id=parent,
        payload={"twin_id": twin_id, "repeats": repeats},
    )
    human = await driver_answers(twin_id, db)
    by_version = h3_items(ref)
    codes = list(ref.h3_version_codes)
    h3_ids = ref.holdout_h3_item_ids

    scores: list[QualityScore] = []
    last_vector: dict[str, int] = {}
    failures = 0
    for attempt in range(repeats):
        vector: dict[str, int] = {}
        for position, code in enumerate(codes, start=1):
            await events.set_label(event, f"quality {twin_id} (run {attempt + 1}, {code})")
            try:
                answers, _ = await ask_items(
                    twin_id=twin_id,
                    paragraphs=stimuli[code],
                    items=by_version[position],
                    baseline={},
                    seed=_seed(session_id, twin_id, code, attempt),
                    wording=config.wording,
                    # docs/08 §2.1 step 2 — the human had no baseline either. Overridden here
                    # whatever TwinConfig says, because it is a property of the gate.
                    show_baseline=False,
                    version_code=code,
                    backend=db,
                )
            except (ContractError, TwinPathError) as exc:
                failures += 1
                await events.emit(
                    stage="ask", label=f"{twin_id} {code} run {attempt + 1}", status="error",
                    parent_event_id=event,
                    payload={"error": f"{type(exc).__name__}: {exc}"[:300]},
                )
                continue
            vector.update(answers)

        if not vector:
            continue
        try:
            scores.append(score_holdout(human, vector, h3_ids))
        except QualityScoreEmpty:
            # I15 — no scorable item is no score, never a perfect one. The repeat is discarded
            # and, if every repeat is, the twin stays `Not run` rather than becoming a result.
            await events.emit(
                stage="ask", label=f"{twin_id} run {attempt + 1}: nothing scorable",
                status="error", parent_event_id=event,
                payload={"items_n": 0, "reason": "human and twin share no H3 item"},
            )
            continue
        last_vector = vector

    if not scores:
        await events.set_status(
            event, "error", label=f"quality {twin_id}: no score",
            payload={"repeats": repeats, "failed_calls": failures},
        )
        return None

    averaged = average_scores(scores)
    correlations = h3_correlations(human, last_vector, h3_items_by_outcome(ref))
    kept = averaged.keeps(mae_max=config.mae_max, pct_within_1_min=config.pct_within_1_min)
    await db.rpc(
        "quality_run_record",
        quality_row(
            twin_id=twin_id,
            holdout_set="H3",
            score=averaged,
            model=settings.twinlab_model,
            repeats=len(scores),
            # The vector is filed under `detail` because `docs/01` §6 gives the table a `detail`
            # jsonb and no column for it. It is what validity tests 1 and 3 re-score.
            detail={"answers": last_vector, "failed_calls": failures},
            config=config,
            session_id=session_id,
            correlations=correlations,
            config_version=config_version,
        ),
    )
    await events.set_status(
        event, "ok",
        label=f"quality {twin_id}: {'kept' if kept else 'dropped'} ({averaged.mae:.2f})",
        payload={
            "twin_id": twin_id,
            "kept": kept,
            "mae": round(averaged.mae, 3),
            "pct_within_1": round(averaged.pct_within_1, 3),
            "items_n": averaged.items_n,
            "repeats": len(scores),
        },
    )

    if include_h2:
        await _h2_for_twin(
            twin_id=twin_id, stimuli=stimuli, config=config, config_version=config_version,
            session_id=session_id, ref=ref, events=events, parent=event, db=db,
        )
    return kept


async def _h2_for_twin(
    *,
    twin_id: str,
    stimuli: dict[str, dict[str, str]],
    config: TwinConfig,
    config_version: int,
    session_id: str,
    ref: ReferenceData,
    events: EventLog,
    parent: int,
    db: DbBackend,
) -> None:
    """H2 for one twin, at **its own driver's arm**. `docs/08` §3.1. H2 does not gate.

    One call, because H2 is one scenario and 16 items. It is what makes validity tests 1 and 3
    runnable: both re-score the stored vector and make no model call of their own.
    """
    rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
    submission = str((rows[0].get("submission_id") if rows else None) or twin_id)
    subs = await db.select(
        "survey_submissions", [("eq", "submission_id", submission)], limit=1
    )
    human_arm = subs[0].get("arm") if subs else None
    if not human_arm:
        await events.emit(
            stage="ask", label=f"{twin_id}: no recorded arm, so no H2 stimulus", status="skipped",
            parent_event_id=parent,
        )
        return
    # Raises on a mismatch rather than recording it: showing a twin a different arm than its human
    # saw is a bug, not a variation (`docs/08` §3.1).
    arm = h2_arm_for(None, str(human_arm))
    code = arm_code(arm, ref)

    try:
        answers, _ = await ask_items(
            twin_id=twin_id,
            paragraphs=stimuli[code],
            items=h2_items(ref),
            baseline={},
            seed=_seed(session_id, twin_id, code, 0),
            wording=config.wording,
            show_baseline=False,
            version_code=code,
            backend=db,
        )
    except (ContractError, TwinPathError, KeyError) as exc:
        await events.emit(
            stage="ask", label=f"{twin_id} H2 ({arm})", status="error", parent_event_id=parent,
            payload={"error": f"{type(exc).__name__}: {exc}"[:300]},
        )
        return

    human = await driver_answers(twin_id, db)
    try:
        score = score_holdout(human, answers, ref.holdout_h2_item_ids)
    except QualityScoreEmpty:
        await events.emit(
            stage="ask", label=f"{twin_id} H2 ({arm}): nothing scorable", status="error",
            parent_event_id=parent, payload={"items_n": 0},
        )
        return

    await db.rpc(
        "quality_run_record",
        quality_row(
            twin_id=twin_id,
            holdout_set="H2",
            score=score,
            model=settings.twinlab_model,
            repeats=1,
            detail={"answers": answers, "arm": arm},
            config=config,
            session_id=session_id,
            arm=arm,
            config_version=config_version,
        ),
    )
    await events.emit(
        stage="ask", label=f"{twin_id} H2 ({arm}): error {score.mae:.2f}", status="ok",
        parent_event_id=parent,
        payload={"arm": arm, "mae": round(score.mae, 3), "items_n": score.items_n},
    )


def _seed(session_id: str, twin_id: str, code: str, attempt: int) -> int:
    from twinlab.services.twin_runtime import round_seed

    return round_seed(session_id, twin_id, f"{code}#{attempt}")


__all__ = [
    "H3_OUTCOMES",
    "QualityGateError",
    "active_gate",
    "arm_code",
    "h2_items",
    "h3_items",
    "h3_items_by_outcome",
    "is_running",
    "request_stop",
    "run_quality_gate",
    "start_quality_gate",
]
