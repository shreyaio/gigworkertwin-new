"""The Results tab's readers. `docs/06` §3.7.

The side panel is **deliberately the same bundle the Analyst received, in the same order**, so the
researcher can read the input and the output together. That ordering is the specification's, not a
layout choice, and :func:`results_panel` builds it in exactly those seven steps.

Nothing here computes a metric. Shifts and the index come off the stored run; the floors come from
`analysis/metrics.py`; the interactions come from `analysis/interactions.py`, which returns a named
missing leg rather than an estimate (I17).
"""

from __future__ import annotations

from twinlab.analysis.metrics import demand_floor
from twinlab.db.client import DbBackend, get_backend
from twinlab.models.view import (
    InteractionRow,
    ResultsPanel,
    StatusRow,
    TestedVersionRow,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE
from twinlab.services.dials import dial_board
from twinlab.services.metrics_view import build_interaction_rows, build_metric_bars
from twinlab.services.status import control_index

#: `docs/02` §6.2. Prose written by the deterministic fallback carries this prefix, and the UI
#: must keep it: a template reading and a model's reading are different evidence.
FALLBACK_MARK = "Generated summary"


async def completed_runs(backend: DbBackend | None = None) -> list[dict]:
    """Every completed run, newest first, latest per version code.

    A `completed` run always has twins (I15, enforced by `runs_completed_has_twins`), so nothing
    here needs to guard against an index computed over nobody — but a row that somehow carries
    ``twins_n = 0`` is skipped rather than shown as a result.
    """
    db = backend or get_backend()
    rows = await db.select(
        "runs", [("eq", "status", "completed")], order=("started_at", True)
    )
    latest: dict[str, dict] = {}
    for row in rows:
        code = row.get("version_code")
        if not code or code in latest or not row.get("twins_n"):
            continue
        latest[code] = row
    return list(latest.values())


async def tested_rows(backend: DbBackend | None = None) -> list[TestedVersionRow]:
    """The Tested versions table's rows — the grid's accessible equivalent (`docs/05` §6).

    Controls are excluded: `00000` is the comparison every shift is measured against, and `SHAM`
    is the demand-characteristic floor. Listing either as a tested version would put a control in
    the results table.
    """
    out: list[TestedVersionRow] = []
    for run in await completed_runs(backend):
        code = run["version_code"]
        if code in (CONTROL_CODE, SHAM_CODE):
            continue
        out.append(
            TestedVersionRow(
                version_code=code,
                fairwork_score=sum(int(d) for d in code),
                twins_n=int(run.get("twins_n") or 0),
                shifts=dict((run.get("metrics") or {}).get("shifts") or {}),
                index_value=run.get("index_value"),
                run_id=str(run.get("run_id") or "") or None,
                # `ARCHITECTURE_UPDATE.md` §4.3 item 4: `origin` is shown wherever a number is.
                # A row whose latest run came from the Twin Studio is an index over ONE twin, and
                # the controls it is measured against came from the frozen panel — so it is not the
                # same quantity as a sweep row and must not read like one. Defaulted rather than
                # required so a database still on migration 003 reports 'sweep', which is what every
                # pre-004 row is.
                origin=str(run.get("origin") or "sweep"),
            )
        )
    return out


#: The two headline interactions the Results tab leads with, as the prototype states them:
#: ``(label, code A, code B, metric)``. Both are single-lever cells, so each pair's joint cell is
#: the two-lever cell — three runs in all, which is the cheapest interaction the design admits.
#:
#: These are a **reading order**, not a hypothesis set: they name two pairings a reader of this
#: study will look for first, and `docs/07` §5 defines the arithmetic for any pair. Every other
#: pair involving a selected cell is still listed in that cell's side panel (`docs/06` §3.7 step
#: 5), so nothing is hidden by leading with these two.
HEADLINE_INTERACTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("Appeals and a drivers' forum", "00010", "00001", "pushback"),
    ("Minimum pay and safety cover", "10000", "01000", "staying"),
)


async def interaction_rows(
    backend: DbBackend | None = None,
) -> list[InteractionRow]:
    """The Results tab's *Do changes work together?* panel. I17.

    Computable pairs are described from the stored shifts; a pair with a missing leg **names the
    codes to run** and is never estimated, interpolated or called "approximately"
    (`CLAUDE.md` rule 5). That is why the incomputable rows are returned rather than filtered out.

    Nothing is computed here: :func:`analysis.interactions.interaction` does the arithmetic and
    this only chooses which pairs to put in front of the reader.
    """
    from twinlab.analysis.interactions import (
        Interaction,
        describe,
        describe_missing,
        interaction,
    )
    from twinlab.models.view import InteractionRow

    shifts = await shifts_by_code(backend)
    out: list[InteractionRow] = []
    for label, a, b, metric in HEADLINE_INTERACTIONS:
        result = interaction(a, b, metric, shifts)
        computable = isinstance(result, Interaction)
        body = describe(result) if computable else describe_missing(result)
        out.append(
            InteractionRow(
                a=result.a,
                b=result.b,
                joint=result.joint,
                metric=metric,
                computable=computable,
                text=f"{label} ({metric}): {body}",
            )
        )
    return out


async def shifts_by_code(backend: DbBackend | None = None) -> dict[str, dict[str, float]]:
    """Completed **tested versions** only, so an absent key means an absent run rather than a zero.

    Controls are excluded, as in :func:`tested_rows`. An interaction is between two dialled
    versions, and `00000` and `SHAM` are not dial vectors: passing `SHAM` to the joint-code step
    raised `ValueError` on its `S`, which is what blanked the side panel.
    """
    return {
        run["version_code"]: dict((run.get("metrics") or {}).get("shifts") or {})
        for run in await completed_runs(backend)
        if run["version_code"] not in (CONTROL_CODE, SHAM_CODE)
    }


async def session_floor(backend: DbBackend | None = None) -> float | None:
    """The `SHAM − 00000` demand floor, or ``None``.

    ``None`` when either control is missing: a floor is never assumed, and a cell reported against
    an assumed floor is reported against nothing (`docs/07` §6).
    """
    db = backend or get_backend()
    return demand_floor(
        await control_index(SHAM_CODE, db), await control_index(CONTROL_CODE, db)
    )


async def results_panel(
    version_code: str, *, metric: str = "fairness", backend: DbBackend | None = None
) -> ResultsPanel:
    """The side panel's contents, in `docs/06` §3.7's **mandatory seven-step order**.

    1. Version code with its Fairwork score
    2. What the twins are told
    3. Scenario text — the five lever paragraphs actually rendered
    4. Numeric results — six shifts, six baselines, index, ``twins_n`` and the floor
    5. Computable interactions involving this cell
    6. Written analysis, with the *Generated summary* prefix where the fallback was used
    7. Run metadata, with a provenance link to the run

    Returns a view model, not markup: `ui/` renders it. A service that returned HTML would put a
    presentation decision below the layer boundary that exists to keep them apart.
    """
    from twinlab.services.lab import scenario_paragraphs

    db = backend or get_backend()
    board = dial_board(version_code)

    run = next(
        (r for r in await completed_runs(db) if r["version_code"] == version_code), None
    )
    metrics = (run or {}).get("metrics") or {}
    bars = build_metric_bars(
        metrics.get("shifts"),
        index_value=(run or {}).get("index_value"),
        twins_n=int((run or {}).get("twins_n") or 0),
        version_code=version_code,
        floor=await session_floor(db),
    )
    analysis = (run or {}).get("llm_analysis")
    return ResultsPanel(
        board=board,
        scenario_text=await scenario_paragraphs(version_code, backend=db),
        bars=bars,
        baselines=dict(metrics.get("baselines") or {}),
        interactions=build_interaction_rows(
            version_code, await shifts_by_code(db), metric=metric
        ),
        analysis=analysis,
        analysis_is_fallback=bool(analysis) and analysis.startswith(FALLBACK_MARK),
        metadata=await _metadata(run, db),
        run_id=str((run or {}).get("run_id") or "") or None,
        origin=str((run or {}).get("origin") or "sweep"),
        twins_n=int((run or {}).get("twins_n") or 0),
    )


async def _metadata(run: dict | None, db: DbBackend) -> list[StatusRow]:
    """Step 7. Everything needed to reproduce the cell, or to say it has not been run."""
    if run is None:
        return [StatusRow(label="Run", value="Not tested", state="pending")]
    origin = str(run.get("origin") or "sweep")
    twins_n = int(run.get("twins_n") or 0)
    rows = [
        StatusRow(label="Run", value=str(run.get("run_id") or "")),
        StatusRow(label="Session", value=str(run.get("session_id") or "")),
        # Step 7 carries the origin beside the twin count, because the two together are what say
        # whether this number is comparable with the panel's (§4.3 item 4). `pending` is the state
        # `status_dot` paints amber, which is the right weight: a Studio number is not wrong, it is
        # a different quantity.
        StatusRow(
            label="Where it came from",
            value=(
                "the frozen panel (a sweep or a Dial board ask)"
                if origin == "sweep"
                else f"the Twin Studio — one twin, so this index is over n = {twins_n}"
            ),
            state="complete" if origin == "sweep" else "pending",
        ),
        StatusRow(label="Twins", value=str(twins_n)),
        StatusRow(label="Completed", value=str(run.get("finished_at") or "")),
    ]
    variant_id = run.get("variant_id")
    if variant_id:
        found = await db.select(
            "variants", [("eq", "variant_id", variant_id)], limit=1
        )
        if found:
            rows.append(
                StatusRow(label="Style version", value=str(found[0].get("style_version") or ""))
            )
            rows.append(
                StatusRow(label="Delta hash", value=str(found[0].get("delta_hash") or ""))
            )
    return rows


__all__ = [
    "FALLBACK_MARK",
    "completed_runs",
    "results_panel",
    "session_floor",
    "shifts_by_code",
    "tested_rows",
]
