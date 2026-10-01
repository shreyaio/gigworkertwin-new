"""The PLS-SEM engine wrapper. `docs/07` §7–§9.

We specify the model, the population and the thresholds; `openpls-engine` computes
(`ARCHITECTURE.md` §3.4). **Nothing in this module reimplements a statistic** — every number comes
off the engine and this file's whole job is to hand it the right matrix, ask for the right things
and label each result against the published threshold.

Two decisions here are load-bearing and are recorded in `docs/DECISIONS.md`:

* **The bootstrap is :class:`openpls.long_bootstrap.LongBootstrap`**, not
  ``Plspm(bootstrap=True)``.
  `docs/07` §9 requires the seed to be stored and a resumed run to be identical to an
  uninterrupted one. The upstream :class:`openpls.bootstrap.Bootstrap` draws its resamples with
  an unseeded ``np.random.randint`` across a multiprocessing pool, so it cannot honour either
  requirement. ``LongBootstrap`` takes a ``seed``, runs serially, reports progress and exposes its
  failure ratio.
* **The import name is ``openpls``**, though the distribution is ``openpls-engine``. The version
  recorded on every run is the distribution's, because that is what the paper must cite.

`docs/07` §8.1's threshold table, §8.2's HTMT bands, §8.3's VIF limits, §8.4's loading floor and
§8.9's SRMR bound are the only numeric literals in this file, and each carries the section it
comes from.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from typing import Any

from twinlab.models.stats import (
    STAGES,
    AnalysisProvenance,
    CaseMatrix,
    EffectRow,
    ExplainedRow,
    FitRow,
    FornellLarckerRow,
    FSquaredRow,
    HtmtRow,
    LoadingRow,
    ModelSpec,
    PathRow,
    PredictRow,
    PredictSummary,
    ReliabilityRow,
    Status,
    VifRow,
)
from twinlab.stats.spec import build_model_spec, topological_order

log = logging.getLogger(__name__)

#: `docs/07` §8.1.
ALPHA_MIN = 0.70
RHO_A_MIN = 0.70
RHO_C_MIN = 0.70
RHO_C_MAX = 0.95
AVE_MIN = 0.50

#: `docs/07` §8.2. ``< 0.90`` for conceptually similar constructs, ``< 0.85`` strict.
HTMT_MAX = 0.90
HTMT_STRICT = 0.85

#: `docs/07` §8.3. ``< 5``, ideally ``< 3``.
VIF_MAX = 5.0

#: `docs/07` §8.4. Below this the construct explains under half the item's variance.
LOADING_MIN = 0.708
LOADING_REMOVE = 0.40

#: `docs/07` §8.9.
SRMR_MAX = 0.08

#: `docs/07` §9.
BOOTSTRAP_FLOOR = 30
BOOTSTRAP_DEFAULT = 5000
BOOTSTRAP_WARN_BELOW = 1000

#: `docs/07` §8.7's R^2 bands. Conventions, not laws — the UI shows the band and never colours an
#: R^2 red for being small.
R2_BANDS = ((0.75, "substantial"), (0.50, "moderate"), (0.25, "weak"))


class EngineError(RuntimeError):
    """The engine could not produce a statistic. Never substituted with a plausible number."""


class BootstrapFloorError(ValueError):
    """Below `docs/07` §9's hard floor of 30. Mirrors the `analysis_bootstrap_floor` constraint."""


def engine_version() -> str:
    """The `openpls-engine` version, recorded on every run. `docs/01` §6.8."""
    try:
        return _dist_version("openpls-engine")
    except PackageNotFoundError as exc:  # pragma: no cover - the dependency is pinned
        raise EngineError(
            "openpls-engine is not installed; no statistic is computable and none may be "
            "estimated another way"
        ) from exc


def _status(ok: bool) -> Status:
    return "ok" if ok else "check"


def _float(value: Any) -> float | None:
    """A finite float, or ``None``. **Never a zero standing in for a missing statistic** (I17)."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out  # NaN


def build_config(spec: ModelSpec):  # noqa: ANN201 - openpls type, engine-internal
    """Translate a :class:`ModelSpec` into the engine's `Config`. `docs/07` §7.2.

    The engine needs a **lower-triangular** path matrix, so the latent variables are added in
    topological order. :func:`twinlab.stats.spec.topological_order` breaks ties alphabetically,
    which is what makes the matrix — and every payload's row order — identical across processes.
    """
    from openpls.config import MV, Config, Structure
    from openpls.mode import Mode

    structure = Structure()
    for edge in spec.edges:
        # add_path requires one side to be a single entry, so edges go in one at a time.
        structure.add_path([edge.source], [edge.target])

    config = Config(structure.path(), scaled=True)
    for code in topological_order(spec):
        construct = spec.construct(code)
        config.add_lv(
            code,
            Mode.B if construct.mode == "B" else Mode.A,
            *[MV(item) for item in construct.items],
        )
    return config


def fit(matrix: CaseMatrix, spec: ModelSpec | None = None):  # noqa: ANN201
    """Estimate the model once, on the full sample. The point estimates every stage reads."""
    from openpls.plspm import Plspm
    from openpls.scheme import Scheme

    spec = spec or build_model_spec()
    frame = matrix.to_frame()
    missing = [c for c in spec.indicators() if c not in frame.columns]
    if missing:
        raise EngineError(
            f"the matrix is missing {len(missing)} model indicator(s): {missing[:6]}. The model "
            "is never estimated on a subset of its own specification."
        )
    # Scheme.PATH is the weighting scheme openpls-engine's published validation covers
    # (ARCHITECTURE.md §3.4) — the only one whose agreement with SmartPLS 4 is cited.
    return Plspm(frame[list(spec.indicators())], build_config(spec), Scheme.PATH, 300, 1e-7)


def bootstrap(
    matrix: CaseMatrix,
    spec: ModelSpec | None = None,
    *,
    samples: int = BOOTSTRAP_DEFAULT,
    seed: int = 20260929,
    on_progress: Callable[[int, int], None] | None = None,
):  # noqa: ANN201
    """The seeded, serial bootstrap. `docs/07` §9.

    Raises below the hard floor rather than running a bootstrap nobody may report, which mirrors
    `analysis_bootstrap_floor` in the DDL so the two cannot disagree.
    """
    from openpls.long_bootstrap import LongBootstrap
    from openpls.scheme import Scheme

    if samples < BOOTSTRAP_FLOOR:
        raise BootstrapFloorError(
            f"{samples} bootstrap samples is below the hard floor of {BOOTSTRAP_FLOOR} "
            f"(docs/07 §9). The default is {BOOTSTRAP_DEFAULT}; below "
            f"{BOOTSTRAP_WARN_BELOW} the confidence intervals are unstable and not reportable."
        )
    spec = spec or build_model_spec()
    frame = matrix.to_frame()
    return LongBootstrap(
        frame[list(spec.indicators())],
        build_config(spec),
        Scheme.PATH,
        iterations=samples,
        seed=seed,
        on_progress=on_progress,
    )


def bootstrap_warning(samples: int) -> str:
    """The message `docs/07` §9 requires below 1,000. Empty above it."""
    if samples >= BOOTSTRAP_WARN_BELOW:
        return ""
    return (
        f"{samples:,} bootstrap samples is below {BOOTSTRAP_WARN_BELOW:,}. The confidence "
        f"intervals are unstable and should not be reported. The published convention is "
        f"{BOOTSTRAP_DEFAULT:,}."
    )


# --------------------------------------------------------------------------- the nine stages

def stage_reliability(pls, matrix: CaseMatrix, spec: ModelSpec) -> list[ReliabilityRow]:
    """`docs/07` §8.1. Cronbach's alpha, rho_A, composite reliability, AVE, per construct.

    ``rho_A`` comes from the engine's consistent-PLS estimator, which is where Dijkstra–Henseler
    reliability lives; alpha, rho_c and AVE come from the standard run. A **formative** block has
    none of these — reliability is a claim about interchangeable reflective indicators — so the
    arm dummies and the interaction term are reported ``na`` with the reason, never as a failure.
    """
    reliability = pls.reliability()
    summary = pls.inner_summary()
    try:
        rho_a = pls.plsc().rho_a()
    except Exception as exc:  # pragma: no cover - engine-internal
        raise EngineError(f"rho_A could not be computed: {exc}") from exc

    frame = matrix.to_frame()
    rows: list[ReliabilityRow] = []
    for construct in spec.constructs:
        code = construct.code
        if not construct.reflective:
            rows.append(
                ReliabilityRow(
                    construct_code=code,
                    label=construct.label,
                    n_items=construct.n_items,
                    mean=None, sd=None,
                    cronbach_alpha=None, rho_a=None, rho_c=None, ave=None,
                    status="na",
                    note="formative block — reliability and AVE do not apply",
                )
            )
            continue

        values = frame[list(construct.items)]
        alpha = _float(reliability.loc[code, "cronbach_alpha"])
        rc = _float(reliability.loc[code, "dillon_goldstein_rho"])
        ave = _float(summary.loc[code, "ave"])
        ra = _float(rho_a.get(code))
        ok = (
            alpha is not None and alpha >= ALPHA_MIN
            and ra is not None and ra >= RHO_A_MIN
            and rc is not None and RHO_C_MIN <= rc <= RHO_C_MAX
            and ave is not None and ave >= AVE_MIN
        )
        note = ""
        if rc is not None and rc > RHO_C_MAX:
            # §8.1: above 0.95 indicates redundant items, not excellent measurement.
            note = f"rho_c above {RHO_C_MAX} suggests redundant items, not better measurement"
        rows.append(
            ReliabilityRow(
                construct_code=code,
                label=construct.label,
                n_items=construct.n_items,
                mean=_float(values.stack().mean()),
                sd=_float(values.stack().std()),
                cronbach_alpha=alpha, rho_a=ra, rho_c=rc, ave=ave,
                status=_status(ok), note=note,
            )
        )
    return rows


def stage_discriminant(
    pls, spec: ModelSpec, htmt_ci: dict[tuple[str, str], tuple[float, float]] | None = None
) -> tuple[list[HtmtRow], list[FornellLarckerRow]]:
    """`docs/07` §8.2. HTMT is primary; Fornell–Larcker is reported because reviewers expect it.

    §8.2's decisive test is that the **upper bound of the CI is below 1**, so when a bootstrapped
    interval is supplied it decides the status and the point estimate only informs it.
    """
    reflective = {c.code for c in spec.constructs if c.reflective}
    pairs = pls.htmt().pairs()
    htmt_ci = htmt_ci or {}

    htmt_rows: list[HtmtRow] = []
    for _, row in pairs.iterrows():
        a, b = str(row["lv_a"]), str(row["lv_b"])
        if a not in reflective or b not in reflective:
            continue  # HTMT is undefined for a formative block; the engine returns NaN.
        value = _float(row["htmt"])
        if value is None:
            continue
        lower, upper = htmt_ci.get((a, b), (None, None))
        ok = upper < 1.0 if upper is not None else value < HTMT_MAX
        htmt_rows.append(
            HtmtRow(
                lv_a=a, lv_b=b, htmt=value,
                ci_lower=lower, ci_upper=upper, status=_status(bool(ok)),
            )
        )

    fl = pls.fornell_larcker().summary()
    fl_rows: list[FornellLarckerRow] = []
    for code, row in fl.iterrows():
        if str(code) not in reflective:
            continue
        sqrt_ave = _float(row.get("sqrt_ave"))
        max_corr = _float(row.get("max_abs_corr"))
        passes = row.get("passes")
        if sqrt_ave is None or max_corr is None:
            fl_rows.append(
                FornellLarckerRow(
                    construct_code=str(code), sqrt_ave=sqrt_ave,
                    max_abs_correlation=max_corr, status="na",
                    note=str(row.get("note") or "no AVE for this block"),
                )
            )
            continue
        fl_rows.append(
            FornellLarckerRow(
                construct_code=str(code), sqrt_ave=sqrt_ave,
                max_abs_correlation=max_corr,
                status=_status(bool(passes) if passes is not None else sqrt_ave > max_corr),
            )
        )
    return htmt_rows, fl_rows


def stage_collinearity(pls) -> list[VifRow]:
    """`docs/07` §8.3. Inner VIF per predictor->criterion; outer VIF per indicator."""
    vif = pls.vif()
    rows: list[VifRow] = []
    for target, frame in vif.inner().items():
        for _, row in frame.iterrows():
            value = _float(row["vif"])
            if value is None:
                continue
            rows.append(
                VifRow(
                    scope="inner", target=str(target), predictor=str(row["predictor"]),
                    vif=value, status=_status(value < VIF_MAX),
                )
            )
    for _, row in vif.items().iterrows():
        value = _float(row["vif"])
        if value is None:
            continue
        rows.append(
            VifRow(
                scope="outer", target=str(row["lv"]), predictor=str(row["indicator"]),
                vif=value, status=_status(value < VIF_MAX),
            )
        )
    return rows


def stage_outer_model(
    pls, spec: ModelSpec, boot=None
) -> list[LoadingRow]:
    """`docs/07` §8.4. ``>= 0.708``; 0.40–0.708 is a judgement call; below 0.40, remove.

    The recommendation is a **prompt, not an action**. §8.4: any item removal is a change to the
    instrument, recorded in `docs/DECISIONS.md` with the loading that justified it, and it never
    edits `instrument.json` — the register is frozen, so removal is an analysis-time exclusion
    list rather than a re-coding.
    """
    outer = pls.outer_model()
    inference = _boot_frame(boot, "loadings")
    of_construct = {
        item: c.code for c in spec.constructs for item in c.items
    }

    rows: list[LoadingRow] = []
    for item, row in outer.iterrows():
        code = of_construct.get(str(item))
        if code is None or not spec.construct(code).reflective:
            continue
        loading = _float(row["loading"])
        if loading is None:
            continue
        stats = _lookup(inference, lv=code, indicator=str(item))
        if loading >= LOADING_MIN:
            status, recommendation = "ok", ""
        elif loading >= LOADING_REMOVE:
            status, recommendation = "check", (
                "retain only if removing it would not raise AVE or rho_c above threshold"
            )
        else:
            status, recommendation = "check", "below 0.40 — remove (an exclusion, not a re-coding)"
        rows.append(
            LoadingRow(
                construct_code=code, item=str(item), loading=loading,
                t_statistic=stats.get("t"), p_value=stats.get("p"),
                ci_lower=stats.get("ci_lower"), ci_upper=stats.get("ci_upper"),
                status=status, recommendation=recommendation,
            )
        )
    return rows


def stage_paths(pls, spec: ModelSpec, boot=None) -> list[PathRow]:
    """`docs/07` §8.5. **Report confidence intervals as primary**, p-values alongside.

    A bootstrap CI excluding zero is the inferential claim, so that — not the p-value — sets
    ``status``.
    """
    coefficients = pls.path_coefficients()
    inference = _boot_frame(boot, "paths")

    rows: list[PathRow] = []
    for edge in spec.edges:
        estimate = _float(coefficients.loc[edge.target, edge.source])
        if estimate is None:
            raise EngineError(
                f"the engine returned no coefficient for {edge}; the model was specified with "
                "that path and a missing estimate is never read as zero"
            )
        stats = _lookup(inference, source=edge.source, target=edge.target)
        lower, upper = stats.get("ci_lower"), stats.get("ci_upper")
        excludes_zero = (lower > 0 or upper < 0) if None not in (lower, upper) else None
        rows.append(
            PathRow(
                source=edge.source, target=edge.target, original_sample=estimate,
                sample_mean=stats.get("mean"), sd=stats.get("sd"),
                t_statistic=stats.get("t"), p_value=stats.get("p"),
                ci_lower=lower, ci_upper=upper,
                status=_status(bool(excludes_zero)) if excludes_zero is not None else "na",
            )
        )
    return rows


def stage_indirect_total(pls, spec: ModelSpec, boot=None) -> list[EffectRow]:
    """`docs/07` §8.6. Specific indirect effects per mediation path, and total effects.

    "The model is a chain, so the indirect effects are where the theory lives" — under the full
    mediation this project specifies, every arm effect on a behavioural intention is **entirely**
    indirect, so this stage carries the whole experimental claim.
    """
    effects = pls.effects()
    total_ci = _boot_frame(boot, "total_effects")
    specific_ci = _boot_frame(boot, "specific_indirect_effects")

    rows: list[EffectRow] = []
    for _, row in effects.iterrows():
        source, target = str(row["from"]), str(row["to"])
        stats = _lookup(total_ci, source=source, target=target)
        for kind in ("direct", "indirect", "total"):
            estimate = _float(row[kind])
            if estimate is None:
                continue
            carry = stats if kind == "total" else {}
            rows.append(
                EffectRow(
                    source=source, target=target, kind=kind, estimate=estimate,
                    sd=carry.get("sd"), t_statistic=carry.get("t"), p_value=carry.get("p"),
                    ci_lower=carry.get("ci_lower"), ci_upper=carry.get("ci_upper"),
                    status="ok",
                )
            )

    if specific_ci is not None:
        for _, row in specific_ci.iterrows():
            estimate = _float(row.get("original") if "original" in row else row.get("estimate"))
            if estimate is None:
                continue
            lower, upper = _float(row.get("ci_lower")), _float(row.get("ci_upper"))
            excludes_zero = (lower > 0 or upper < 0) if None not in (lower, upper) else None
            rows.append(
                EffectRow(
                    source=str(row.get("source", row.get("from", ""))),
                    target=str(row.get("target", row.get("to", ""))),
                    kind="specific_indirect", estimate=estimate,
                    via=str(row.get("via", row.get("through", "")) or ""),
                    sd=_float(row.get("sd")), t_statistic=_float(row.get("t")),
                    p_value=_float(row.get("p")), ci_lower=lower, ci_upper=upper,
                    status=_status(bool(excludes_zero)) if excludes_zero is not None else "na",
                )
            )
    return rows


def stage_r2_f2_q2(pls, spec: ModelSpec) -> tuple[list[ExplainedRow], list[FSquaredRow]]:
    """`docs/07` §8.7. R^2, adjusted R^2, f^2 and Q^2.

    The R^2 band is a **label**. §8.7 is explicit: the bands are conventions, behavioural IS models
    routinely report lower and defend it, and the UI never colours an R^2 red for being small.
    """
    summary = pls.inner_summary()
    q2 = pls.q_squared()
    endogenous = {e.target for e in spec.edges}

    explained: list[ExplainedRow] = []
    for code in spec.codes:
        if code not in endogenous:
            continue
        r2 = _float(summary.loc[code, "r_squared"])
        q_value = _float(q2.loc[code, "q_squared"]) if code in q2.index else None
        explained.append(
            ExplainedRow(
                construct_code=code,
                r_squared=r2,
                r_squared_adj=_float(summary.loc[code, "r_squared_adj"]),
                q_squared=q_value,
                band=_r2_band(r2),
                # §8.7: Q^2 > 0 is predictive relevance. Absent is "na", never a failure.
                q_status="na" if q_value is None else _status(q_value > 0),
            )
        )

    f_rows = [
        FSquaredRow(
            source=str(row["from"]), target=str(row["to"]),
            f_squared=_float(row["f_squared"]) or 0.0,
            effect_size=str(row["effect_size"]),
        )
        for _, row in pls.f_squared().table().iterrows()
        if _float(row["f_squared"]) is not None
    ]
    return explained, f_rows


def _r2_band(r2: float | None) -> str:
    if r2 is None:
        return "not computed"
    for threshold, label in R2_BANDS:
        if r2 >= threshold:
            return label
    return "below the weak band"


def stage_plspredict(
    pls, spec: ModelSpec, *, folds: int = 10, repeats: int = 1, seed: int = 20260929
) -> tuple[list[PredictRow], PredictSummary]:
    """`docs/07` §8.8. PLS errors against a **linear-model benchmark**, k-fold.

    Assessed on the **endogenous** constructs' indicators only: an exogenous construct is not
    predicted by the model, so its indicators say nothing about predictive power. The four-way
    reading in §8.8's table is computed here rather than left to the reader.
    """
    endogenous = {e.target for e in spec.edges}
    metrics = pls.predict(k=folds, repeats=repeats, seed=seed).metrics()

    rows: list[PredictRow] = []
    for (lv, indicator), row in metrics.iterrows():
        if str(lv) not in endogenous:
            continue
        q2p = _float(row["q2_predict"])
        rmse_pls, rmse_lm = _float(row["rmse_pls"]), _float(row["rmse_lm"])
        if None in (q2p, rmse_pls, rmse_lm):
            continue
        rows.append(
            PredictRow(
                construct_code=str(lv), indicator=str(indicator), q2_predict=q2p,
                rmse_pls=rmse_pls, rmse_lm=rmse_lm,
                mae_pls=_float(row["mae_pls"]) or 0.0, mae_lm=_float(row["mae_lm"]) or 0.0,
                status=_status(q2p > 0 and rmse_pls < rmse_lm),
            )
        )
    return rows, _predict_summary(rows)


def _predict_summary(rows: list[PredictRow]) -> PredictSummary:
    """`docs/07` §8.8's table, as a verdict. All / most / a minority / none."""
    total = len(rows)
    beating = sum(1 for r in rows if r.beats_benchmark)
    positive = sum(1 for r in rows if r.q2_predict > 0)
    if total == 0:
        return PredictSummary(
            verdict="none", indicators=0, beating_benchmark=0, q2_positive=0,
            note="no endogenous indicator could be assessed",
        )
    if positive == 0:
        verdict = "none"
    elif beating == total and positive == total:
        verdict = "strong"
    elif beating > total / 2:
        verdict = "medium"
    elif beating > 0:
        verdict = "low"
    else:
        verdict = "none"
    return PredictSummary(
        verdict=verdict, indicators=total, beating_benchmark=beating, q2_positive=positive,
        note=(
            f"PLS beat the linear benchmark on {beating} of {total} indicator(s); "
            f"Q²predict was positive on {positive}."
        ),
    )


def stage_model_fit(pls) -> list[FitRow]:
    """`docs/07` §8.9. **Report fit, do not lead with it.**

    NFI and the exact-fit test are reported only where the engine provides them — §8.9 says "where
    the engine provides it", and a fit index this build cannot compute is absent, never zero.
    """
    fit_result = pls.model_fit()
    srmr = _float(fit_result.srmr())
    rows = [
        FitRow(
            statistic="SRMR", value=srmr, threshold=f"< {SRMR_MAX}",
            status="na" if srmr is None else _status(srmr < SRMR_MAX),
        ),
        FitRow(
            statistic="d_ULS", value=_float(fit_result.d_uls()),
            threshold="reported, no published cut-off", status="na",
        ),
    ]
    for name, method in (("d_G", "d_g"), ("NFI", "nfi")):
        getter = getattr(fit_result, method, None)
        value = _float(getter()) if callable(getter) else None
        rows.append(
            FitRow(
                statistic=name, value=value,
                threshold="reported where the engine provides it", status="na",
            )
        )
    return rows


# --------------------------------------------------------------------------- bootstrap plumbing

def _boot_frame(boot, name: str):  # noqa: ANN001, ANN202
    """One of ``LongBootstrap``'s inference frames, or ``None`` when no bootstrap was run."""
    if boot is None:
        return None
    getter = getattr(boot, name, None)
    if not callable(getter):
        return None
    try:
        return getter()
    except Exception as exc:  # pragma: no cover - engine-internal
        log.warning("bootstrap frame %s unavailable: %s", name, exc)
        return None


def _lookup(frame, **keys: str) -> dict[str, float | None]:
    """Pull one row's inference statistics out of a bootstrap frame, tolerant of column naming.

    Returns an empty mapping when there is no bootstrap, so every caller renders ``None`` — which
    the view models turn into ``Not tested`` rather than into a zero (I17).
    """
    if frame is None or len(frame) == 0:
        return {}
    mask = None
    for column, wanted in (
        ("lv", keys.get("lv")), ("indicator", keys.get("indicator")),
        ("source", keys.get("source")), ("target", keys.get("target")),
        ("from", keys.get("source")), ("to", keys.get("target")),
    ):
        if wanted is None or column not in frame.columns:
            continue
        test = frame[column].astype(str) == wanted
        mask = test if mask is None else (mask & test)
    if mask is None or not mask.any():
        return {}
    row = frame[mask].iloc[0]

    def pick(*names: str) -> float | None:
        for candidate in names:
            if candidate in row.index:
                value = _float(row[candidate])
                if value is not None:
                    return value
        return None

    return {
        "mean": pick("mean", "sample_mean", "boot_mean"),
        "sd": pick("sd", "std", "std_error", "se"),
        "t": pick("t", "t_stat", "t_statistic"),
        "p": pick("p", "p_value", "pval"),
        "ci_lower": pick("ci_lower", "lower", "ci_low", "bca_lower"),
        "ci_upper": pick("ci_upper", "upper", "ci_high", "bca_upper"),
    }


def provenance(
    matrix: CaseMatrix,
    spec: ModelSpec,
    *,
    samples: int,
    seed: int,
    validated: bool = False,
) -> AnalysisProvenance:
    """The five facts `docs/07` §9 requires on every result view, plus the model fingerprint."""
    return AnalysisProvenance(
        engine_version=engine_version(),
        n_cases=matrix.n_cases,
        bootstrap_samples=samples,
        seed=seed,
        screening=matrix.screening,
        population=matrix.population,
        model_fingerprint=spec.fingerprint(),
        engine_validated=validated,
    )


def run_all_stages(
    matrix: CaseMatrix,
    spec: ModelSpec | None = None,
    *,
    samples: int = BOOTSTRAP_DEFAULT,
    seed: int = 20260929,
    with_bootstrap: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Every stage, in `docs/01` §6.8's order. Used by the golden test and by the runner.

    The service layer persists each stage as it completes and skips a stage already stored, so a
    resumed run never recomputes one (`docs/01` §6.8). This function is the single-shot form.
    """
    spec = spec or build_model_spec()
    pls = fit(matrix, spec)
    boot = (
        bootstrap(matrix, spec, samples=samples, seed=seed, on_progress=on_progress)
        if with_bootstrap
        else None
    )

    htmt_rows, fl_rows = stage_discriminant(pls, spec)
    explained, f_squared = stage_r2_f2_q2(pls, spec)
    predict_rows, predict_summary = stage_plspredict(pls, spec, seed=seed)

    out: dict[str, Any] = {
        "reliability": stage_reliability(pls, matrix, spec),
        "discriminant": {"htmt": htmt_rows, "fornell_larcker": fl_rows},
        "collinearity": stage_collinearity(pls),
        "outer_model": stage_outer_model(pls, spec, boot),
        "paths": stage_paths(pls, spec, boot),
        "indirect_total": stage_indirect_total(pls, spec, boot),
        "r2_f2_q2": {"explained": explained, "f_squared": f_squared},
        "plspredict": {"rows": predict_rows, "summary": predict_summary},
        "model_fit": stage_model_fit(pls),
    }
    assert set(out) == set(STAGES), "every stage in docs/01 §6.8 must be produced"
    return out
