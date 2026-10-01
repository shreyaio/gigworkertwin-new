"""The Statistics service. `docs/06` §7, `docs/07` §7–§11, `docs/01` §6.8.

Everything the Statistics screen can do is a function here; `ui/` holds no logic and `api/` would
be a wrapper (`ARCHITECTURE.md` §8.2 rule 3).

Three properties are load-bearing:

* **Stages persist and are never recomputed on resume** (`docs/01` §6.8). :func:`run_analysis`
  reads `analysis_results` first and computes only what is missing, so a bootstrap interrupted at
  stage seven restarts at stage seven. The seed makes the resumed run identical to an
  uninterrupted one (`docs/07` §9).
* **The bootstrap floor is enforced here as well as in the DDL.** `analysis_bootstrap_floor`
  rejects the row; this rejects the request, with the sentence explaining why 30 is not a
  reportable setting. Two gates, because the DDL one is not reachable from a Gradio handler.
* **No LLM call, ever.** The measurement layer is arithmetic. The Analyst writes prose about the
  counterfactual layer's numbers, which is a different screen (I12).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from twinlab.db.client import DbBackend, get_backend
from twinlab.models.stats import (
    STAGES,
    AnalysisRunView,
    CaseMatrix,
    ModelSpec,
    Population,
    Screening,
    StatsTableSpec,
)
from twinlab.stats import export as export_module
from twinlab.stats import plssem
from twinlab.stats.dataset import NoCasesError, load_matrix
from twinlab.stats.golden import GOLDEN_FINGERPRINT
from twinlab.stats.spec import build_model_spec

log = logging.getLogger(__name__)

#: `docs/07` §10. Flipped to ``True`` only when the golden test has passed against **this** model.
#: `services.config.startup_check` does not run pytest, so the honest signal available at runtime
#: is whether the running model is the one the stored expectations were computed under.
def engine_is_validated(spec: ModelSpec | None = None) -> bool:
    """Whether the running model matches the one the golden values were pinned against.

    A different fingerprint means the golden test — whatever it did in CI — did not validate
    *this* wiring, so the `UNVALIDATED` banner stays up. `docs/07` §10.
    """
    spec = spec or build_model_spec()
    return spec.fingerprint() == GOLDEN_FINGERPRINT


UNVALIDATED_BANNER = (
    "UNVALIDATED — the golden dataset test has not passed against this model specification. "
    "No number on this screen is reportable until it does (docs/07 §10)."
)


class StageError(RuntimeError):
    """A stage failed. Recorded as a failure; never stored as an empty payload."""


async def create_analysis(
    *,
    population: Population = "real",
    screening: Screening = "strict",
    bootstrap_samples: int = plssem.BOOTSTRAP_DEFAULT,
    seed: int = 20260929,
    pool_legacy: bool = False,
    backend: DbBackend | None = None,
) -> tuple[str, CaseMatrix]:
    """Create the run row and build its matrix. Nothing is computed yet.

    The matrix is built **before** the row is inserted, because `analysis_has_cases` requires a
    real `n_cases` and a run row that exists with nobody in it is exactly the shape I15 forbids in
    the counterfactual layer.
    """
    db = backend or get_backend()
    if bootstrap_samples < plssem.BOOTSTRAP_FLOOR:
        raise plssem.BootstrapFloorError(
            f"{bootstrap_samples} bootstrap samples is below the hard floor of "
            f"{plssem.BOOTSTRAP_FLOOR}. The default is {plssem.BOOTSTRAP_DEFAULT:,}; below "
            f"{plssem.BOOTSTRAP_WARN_BELOW:,} the confidence intervals are unstable and should "
            "not be reported (docs/07 §9)."
        )

    spec = build_model_spec()
    matrix = await load_matrix(
        population=population, screening=screening, pool_legacy=pool_legacy,
        spec=spec, backend=db,
    )
    rows = await db.insert(
        "analysis_runs",
        [
            {
                "population": population,
                "screening": screening,
                "bootstrap_samples": bootstrap_samples,
                "seed": seed,
                "n_cases": matrix.n_cases,
                "status": "created",
                "stage_cursor": STAGES[0],
                "engine_version": plssem.engine_version(),
                "config": {
                    "model_fingerprint": spec.fingerprint(),
                    "pool_legacy": pool_legacy,
                    "dropped": len(matrix.dropped),
                    "legacy_excluded": matrix.legacy_excluded,
                },
            }
        ],
    )
    analysis_id = str(rows[0]["analysis_id"])
    log.info(
        "analysis %s created: %s/%s, n=%d, %d bootstrap samples",
        analysis_id, population, screening, matrix.n_cases, bootstrap_samples,
    )
    return analysis_id, matrix


async def completed_stages(
    analysis_id: str, backend: DbBackend | None = None
) -> set[str]:
    """Which stages are already stored. `docs/01` §6.8 — these are never recomputed."""
    db = backend or get_backend()
    rows = await db.select(
        "analysis_results", [("eq", "analysis_id", analysis_id)]
    )
    return {str(r["stage"]) for r in rows}


async def run_analysis(
    analysis_id: str,
    matrix: CaseMatrix,
    *,
    on_stage: Callable[[str, int, int], None] | None = None,
    backend: DbBackend | None = None,
) -> AnalysisRunView:
    """Compute every outstanding stage, persisting each as it completes.

    **Resumable by construction**: a stage already in `analysis_results` is skipped, so the work
    done before an interruption is not repeated (`docs/01` §6.8). The seed is read back off the
    run row rather than passed in, so a resumed run cannot accidentally use a different one.
    """
    db = backend or get_backend()
    run_rows = await db.select("analysis_runs", [("eq", "analysis_id", analysis_id)])
    if not run_rows:
        raise StageError(f"no analysis run {analysis_id}")
    run = run_rows[0]

    spec = build_model_spec()
    done = await completed_stages(analysis_id, db)
    outstanding = [stage for stage in STAGES if stage not in done]

    if outstanding:
        await db.update(
            "analysis_runs", {"status": "running"}, [("eq", "analysis_id", analysis_id)]
        )
        samples = int(run["bootstrap_samples"])
        seed = int(run["seed"])

        # One fit and one bootstrap serve every outstanding stage. Re-fitting per stage would
        # multiply the dominant cost by nine for no gain — and, with the bootstrap, would draw a
        # different resample for each, which is not one analysis.
        pls = plssem.fit(matrix, spec)
        needs_boot = {"outer_model", "paths", "indirect_total"} & set(outstanding)
        boot = (
            plssem.bootstrap(matrix, spec, samples=samples, seed=seed)
            if needs_boot else None
        )

        for index, stage in enumerate(outstanding, start=1):
            if on_stage:
                on_stage(stage, index, len(outstanding))
            try:
                payload = _compute_stage(stage, pls, matrix, spec, boot, seed)
            except Exception as exc:
                await db.update(
                    "analysis_runs",
                    {"status": "failed", "stage_cursor": stage},
                    [("eq", "analysis_id", analysis_id)],
                )
                raise StageError(f"stage {stage!r} failed: {exc}") from exc

            await db.upsert(
                "analysis_results",
                [{"analysis_id": analysis_id, "stage": stage, "payload": payload}],
                on_conflict="analysis_id,stage",
            )
            done.add(stage)

        await db.update(
            "analysis_runs",
            {"status": "completed", "stage_cursor": None},
            [("eq", "analysis_id", analysis_id)],
        )

    return await analysis_view(analysis_id, backend=db)


def _compute_stage(
    stage: str, pls, matrix: CaseMatrix, spec: ModelSpec, boot, seed: int
) -> dict[str, Any]:
    """One stage's payload, JSON-serialisable for `analysis_results.payload`."""
    if stage == "reliability":
        return {"rows": _dump(plssem.stage_reliability(pls, matrix, spec))}
    if stage == "discriminant":
        htmt, fornell = plssem.stage_discriminant(pls, spec)
        return {"htmt": _dump(htmt), "fornell_larcker": _dump(fornell)}
    if stage == "collinearity":
        return {"rows": _dump(plssem.stage_collinearity(pls))}
    if stage == "outer_model":
        return {"rows": _dump(plssem.stage_outer_model(pls, spec, boot))}
    if stage == "paths":
        return {"rows": _dump(plssem.stage_paths(pls, spec, boot))}
    if stage == "indirect_total":
        return {"rows": _dump(plssem.stage_indirect_total(pls, spec, boot))}
    if stage == "r2_f2_q2":
        explained, f_squared = plssem.stage_r2_f2_q2(pls, spec)
        return {"explained": _dump(explained), "f_squared": _dump(f_squared)}
    if stage == "plspredict":
        rows, summary = plssem.stage_plspredict(pls, spec, seed=seed)
        return {"rows": _dump(rows), "summary": summary.model_dump()}
    if stage == "model_fit":
        return {"rows": _dump(plssem.stage_model_fit(pls))}
    raise StageError(f"unknown stage {stage!r}; docs/01 §6.8 defines exactly {list(STAGES)}")


def _dump(rows: list) -> list[dict]:
    return [row.model_dump() for row in rows]


async def analysis_view(
    analysis_id: str, backend: DbBackend | None = None
) -> AnalysisRunView:
    """One run as the screen reads it, carrying the five facts `docs/07` §9 requires."""
    db = backend or get_backend()
    rows = await db.select("analysis_runs", [("eq", "analysis_id", analysis_id)])
    if not rows:
        raise StageError(f"no analysis run {analysis_id}")
    run = rows[0]
    done = await completed_stages(analysis_id, db)
    config = run.get("config") or {}
    samples = int(run["bootstrap_samples"])

    from twinlab.models.stats import AnalysisProvenance

    return AnalysisRunView(
        analysis_id=str(run["analysis_id"]),
        status=str(run["status"]),
        provenance=AnalysisProvenance(
            engine_version=str(run["engine_version"]),
            n_cases=int(run["n_cases"]),
            bootstrap_samples=samples,
            seed=int(run["seed"]),
            screening=str(run["screening"]),
            population=str(run["population"]),
            model_fingerprint=str(config.get("model_fingerprint", "")),
            engine_validated=str(config.get("model_fingerprint", "")) == GOLDEN_FINGERPRINT,
        ),
        stages_done=tuple(stage for stage in STAGES if stage in done),
        stage_cursor=run.get("stage_cursor"),
        bootstrap_warning=plssem.bootstrap_warning(samples),
    )


async def latest_analysis(backend: DbBackend | None = None) -> AnalysisRunView | None:
    """The most recent run, or ``None``. The Statistics screen's initial paint."""
    db = backend or get_backend()
    rows = await db.select("analysis_runs", None, order=("created_at", True))
    if not rows:
        return None
    return await analysis_view(str(rows[0]["analysis_id"]), backend=db)


async def stage_payload(
    analysis_id: str, stage: str, backend: DbBackend | None = None
) -> dict[str, Any] | None:
    """One stored stage, or ``None`` when it has not been computed. Never a fabricated empty."""
    db = backend or get_backend()
    rows = await db.select(
        "analysis_results",
        [("eq", "analysis_id", analysis_id), ("eq", "stage", stage)],
    )
    return dict(rows[0]["payload"]) if rows else None


async def build_export(
    *,
    population: Population = "both",
    screening: Screening = "none",
    pool_legacy: bool = False,
    backend: DbBackend | None = None,
) -> tuple[list[str], list[str], list[list[Any]]]:
    """The export sheet: two header rows and the data. `docs/07` §11."""
    db = backend or get_backend()
    submissions = await db.select("survey_submissions", None)
    answers = await db.select("survey_answers", None)
    twins = await db.select("twins", None)
    header = export_module.header_rows()
    rows = export_module.build_rows(
        list(submissions), list(answers), list(twins),
        population=population, screening=screening, pool_legacy=pool_legacy,
    )
    return header[0], header[1], rows


def screening_note(matrix: CaseMatrix) -> str:
    """One sentence about who was dropped and why. `docs/07` §7.1.

    A screening rule chosen after seeing results is a researcher degree of freedom; saying plainly
    who it removed is what keeps that choice visible rather than buried in an `n`.
    """
    if not matrix.dropped:
        return f"{matrix.n_cases} respondent(s); none screened out."
    reasons: dict[str, int] = {}
    for _sid, reason in matrix.dropped:
        reasons[reason] = reasons.get(reason, 0) + 1
    parts = ", ".join(f"{count} {reason}" for reason, count in sorted(reasons.items()))
    return f"{matrix.n_cases} respondent(s) kept; {len(matrix.dropped)} screened out — {parts}."


# --------------------------------------------------------------------------- table specs

#: `docs/05` §4.4: a statistical abbreviation carries a ``title`` **and** a visible legend, because
#: ``rho_A`` and ``AVE`` are not self-explanatory even to the intended reader (`docs/05` §6).
#: Defined once, here, so the ten tabs cannot word the same abbreviation differently.
LEGENDS: dict[str, tuple[tuple[str, str], ...]] = {
    "reliability": (
        ("alpha", "Cronbach's alpha — internal consistency. 0.70 or above."),
        ("rho_A", "Dijkstra-Henseler consistent reliability. 0.70 or above."),
        ("rho_c", "Composite reliability. 0.70 to 0.95; above 0.95 means redundant items."),
        ("AVE", "Average variance extracted — the share of item variance the construct "
                "explains. 0.50 or above."),
    ),
    "discriminant": (
        ("HTMT", "Heterotrait-monotrait ratio — how far two constructs are distinct. "
                 "Below 0.90, strictly below 0.85."),
        ("CI", "Bootstrap confidence interval. The decisive test is an upper bound below 1."),
        ("sqrt(AVE)", "Fornell-Larcker: must exceed every correlation in the construct's row."),
    ),
    "collinearity": (
        ("VIF", "Variance inflation factor. Below 5, ideally below 3."),
        ("inner", "Between constructs — a value above 5 makes a path uninterpretable."),
        ("outer", "Between a construct's own items — a value above 5 means redundant items."),
    ),
    "outer_model": (
        ("Loading", "How strongly the item reflects its construct. 0.708 or above."),
        ("t", "Bootstrap t-statistic."),
        ("CI", "Bootstrap confidence interval; primary over the p-value."),
    ),
    "paths": (
        ("Original sample", "The coefficient estimated on the full sample."),
        ("Sample mean", "The mean across bootstrap resamples."),
        ("CI", "Bootstrap confidence interval. **A CI excluding zero is the inferential claim**; "
               "the p-value is a convention reported alongside."),
    ),
    "indirect_total": (
        ("Direct", "The effect along a single path."),
        ("Indirect", "The effect transmitted through mediators."),
        ("Total", "Direct plus indirect."),
    ),
    "r2_f2_q2": (
        ("R²", "Variance explained. 0.75 substantial, 0.50 moderate, 0.25 weak — "
                    "conventions, and field-dependent."),
        ("f²", "Effect size of one predictor. 0.02 small, 0.15 medium, 0.35 large."),
        ("Q²", "Blindfolding. Above zero means predictive relevance."),
    ),
    "plspredict": (
        ("Q²predict", "Out-of-sample predictive power. Above zero."),
        ("RMSE (PLS)", "Root mean squared error of the PLS model."),
        ("RMSE (LM)", "The same for a linear-model benchmark. PLS should be lower."),
    ),
    "model_fit": (
        ("SRMR", "Standardised root mean square residual. Below 0.08."),
        ("d_ULS", "Squared Euclidean discrepancy. Reported; no published cut-off."),
    ),
}


def table_spec(
    stage: str, title: str, headers: tuple[str, ...], caption: str = ""
) -> StatsTableSpec:
    """A :class:`StatsTableSpec` with the stage's legend attached.

    Raises on an unknown stage rather than rendering a table with no legend — `docs/05` §4.4 makes
    the legend mandatory, so a missing one is a specification breach, not a cosmetic gap.
    """
    if stage not in LEGENDS:
        raise KeyError(
            f"no legend for stage {stage!r}; docs/05 §4.4 requires every statistics table to "
            "carry one"
        )
    return StatsTableSpec(
        title=title, headers=headers, legend=LEGENDS[stage], caption=caption
    )


__all__ = [
    "LEGENDS",
    "NoCasesError",
    "UNVALIDATED_BANNER",
    "analysis_view",
    "build_export",
    "completed_stages",
    "create_analysis",
    "engine_is_validated",
    "latest_analysis",
    "run_analysis",
    "screening_note",
    "stage_payload",
    "table_spec",
]
