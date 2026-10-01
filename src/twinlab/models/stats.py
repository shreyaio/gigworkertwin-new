"""The measurement layer's shapes. `docs/07` §7–§11.

`CLAUDE.md` rule 13: every Pydantic model lives in `models/`. These are the shapes the PLS-SEM
wrapper, the service layer and `ui/` pass between them, so no bare dict crosses a boundary
(`ARCHITECTURE.md` §4).

Three properties here are research commitments rather than tidiness:

* **The model specification is data, not code.** :class:`ModelSpec` is built once from the frozen
  item register and is what the golden test pins. The two faults `docs/07` §10 requires that test
  to catch — a construct bound to the wrong items, and a reverse-coded item not reversed — are
  both edits to a :class:`ModelSpec` or to the matrix built from one, so both are visible as a
  diff and both move a stored expected value.
* **A statistic carries its own verdict.** Every row model computes ``status`` against the
  published threshold in `docs/07` §8 rather than leaving the UI to compare numbers. `docs/05`
  §8.4 rule 5: no arithmetic on a statistic in a Gradio handler.
* **Absence is never zero.** A formative construct has no AVE and no Cronbach's alpha; a
  statistic the engine could not compute is ``None`` and renders as ``Not applicable`` or
  ``Not computed``, never ``0.000`` (I17).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: `docs/07` §7.1. ``strict`` drops attention failures, speeders and straight-liners.
Screening = Literal["strict", "none"]

#: `docs/07` §7.1 and `docs/01` §6.8.
Population = Literal["real", "synthetic", "both"]

#: `docs/01` §6.8's `analysis_results.stage` enumeration, in computation order.
STAGES: tuple[str, ...] = (
    "reliability",
    "discriminant",
    "collinearity",
    "outer_model",
    "paths",
    "indirect_total",
    "r2_f2_q2",
    "plspredict",
    "model_fit",
)

#: A statistic's verdict against its published threshold. ``na`` is a construct the statistic does
#: not apply to — a formative block has no AVE — and is never rendered as a failure.
Status = Literal["ok", "check", "na"]


class _Stats(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- the model

class ConstructSpec(_Stats):
    """One latent variable and the manifest variables that measure it.

    ``mode`` is ``A`` (reflective) for all nine constructs in `docs/01` §3.3 and ``B`` (formative)
    only for the experimental antecedent, which is a set of dummy columns rather than a set of
    interchangeable indicator items.
    """

    code: str
    label: str
    mode: Literal["A", "B"]
    items: tuple[str, ...]
    #: ``None`` for the antecedent and the interaction term, which sit on no survey scale.
    scale_id: str | None = None
    #: Reflective constructs get reliability, AVE and discriminant validity; formative ones do not.
    reflective: bool = True

    @property
    def n_items(self) -> int:
        return len(self.items)


class PathEdge(_Stats):
    """One directed structural path, ``source -> target``."""

    source: str
    target: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.source} -> {self.target}"


class ModelSpec(_Stats):
    """The whole measurement and structural model. `docs/07` §7.2.

    Built once by :func:`twinlab.stats.spec.build_model_spec` from the frozen item register, so a
    construct cannot drift from the register that defines it. The golden test pins this object's
    :meth:`fingerprint`, which is what makes "a construct bound to the wrong items" a test failure
    rather than a plausible number.
    """

    constructs: tuple[ConstructSpec, ...]
    edges: tuple[PathEdge, ...]
    #: The reference level of the experimental antecedent — the arm every dummy is measured
    #: against. `docs/01` §5: ``BASE`` is the no-change control.
    arm_reference: str
    #: The moderator and the path it moderates, as ``(moderator, moderated)``. `docs/07` §7.2.
    interaction: tuple[str, str] | None = None

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(c.code for c in self.constructs)

    def construct(self, code: str) -> ConstructSpec:
        for c in self.constructs:
            if c.code == code:
                return c
        raise KeyError(f"no construct {code!r} in the model; have {self.codes}")

    def indicators(self) -> tuple[str, ...]:
        """Every manifest column the model needs, in construct order."""
        return tuple(item for c in self.constructs for item in c.items)

    def fingerprint(self) -> str:
        """A stable digest of the whole specification. `docs/09` §2.

        Recorded on every analysis run and pinned by the golden test. Changing which items load on
        a construct, adding a path or changing the arm reference all move it, so an analysis
        produced under a different model can never be mistaken for a comparable one.
        """
        import hashlib

        parts = [f"ref={self.arm_reference}"]
        for c in self.constructs:
            parts.append(f"{c.code}:{c.mode}:{','.join(c.items)}")
        parts.extend(sorted(f"{e.source}->{e.target}" for e in self.edges))
        if self.interaction:
            parts.append("x=" + "*".join(self.interaction))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- the dataset

class CaseMatrix(_Stats):
    """The screened analysis matrix, one row per human respondent. `docs/07` §1.

    ``columns`` and ``rows`` are a plain matrix rather than a DataFrame because a Pydantic model
    crosses layer boundaries and a DataFrame does not validate. :func:`to_frame` rebuilds it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    columns: tuple[str, ...]
    rows: tuple[tuple[float, ...], ...]
    submission_ids: tuple[str, ...]
    population: Population
    screening: Screening
    #: Why each excluded respondent was dropped, for the screening audit. `docs/07` §7.1.
    dropped: tuple[tuple[str, str], ...] = ()
    #: Submissions carrying any answer on the prototype's 1–7 scale. Excluded unless pooled.
    legacy_excluded: int = 0

    @property
    def n_cases(self) -> int:
        return len(self.rows)

    def to_frame(self):  # noqa: ANN201 - pandas is a service-layer concern
        import pandas as pd

        return pd.DataFrame(
            [list(r) for r in self.rows], columns=list(self.columns), dtype=float
        )


# --------------------------------------------------------------------------- stage payloads

class ReliabilityRow(_Stats):
    """`docs/07` §8.1. ``Construct · Items · Mean · SD · alpha · rho_A · rho_c · AVE · Status``."""

    construct_code: str
    label: str
    n_items: int
    mean: float | None
    sd: float | None
    cronbach_alpha: float | None
    rho_a: float | None
    rho_c: float | None
    ave: float | None
    status: Status
    note: str = ""


class HtmtRow(_Stats):
    """`docs/07` §8.2. The decisive test is that the CI's upper bound is below 1."""

    lv_a: str
    lv_b: str
    htmt: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    status: Status = "ok"


class FornellLarckerRow(_Stats):
    """`docs/07` §8.2. ``sqrt(AVE)`` must exceed every correlation in the construct's row."""

    construct_code: str
    sqrt_ave: float | None
    max_abs_correlation: float | None
    status: Status
    note: str = ""


class VifRow(_Stats):
    """`docs/07` §8.3. ``< 5``, ideally ``< 3``. ``scope`` is ``inner`` or ``outer``."""

    scope: Literal["inner", "outer"]
    target: str
    predictor: str
    vif: float
    status: Status


class LoadingRow(_Stats):
    """`docs/07` §8.4. ``>= 0.708``; 0.40–0.708 is a judgement call; below 0.40, remove."""

    construct_code: str
    item: str
    loading: float
    t_statistic: float | None = None
    p_value: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    status: Status = "ok"
    #: ``remove`` below 0.40, ``review`` in the band, empty above it. `docs/07` §8.4.
    recommendation: str = ""


class PathRow(_Stats):
    """`docs/07` §8.5. **The CI is the inferential claim**; the p-value is a convention."""

    source: str
    target: str
    original_sample: float
    sample_mean: float | None = None
    sd: float | None = None
    t_statistic: float | None = None
    p_value: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    #: ``ok`` when the bootstrap CI excludes zero. Never a claim about importance.
    status: Status = "ok"

    @property
    def ci_excludes_zero(self) -> bool | None:
        if self.ci_lower is None or self.ci_upper is None:
            return None
        return self.ci_lower > 0 or self.ci_upper < 0


class EffectRow(_Stats):
    """`docs/07` §8.6. ``Direct · Indirect · Total``, each with a CI where bootstrapped."""

    source: str
    target: str
    kind: Literal["direct", "indirect", "total", "specific_indirect"]
    estimate: float
    via: str = ""
    sd: float | None = None
    t_statistic: float | None = None
    p_value: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    status: Status = "ok"


class ExplainedRow(_Stats):
    """`docs/07` §8.7. R^2, adjusted R^2 and Q^2 per endogenous construct.

    ``band`` is a **label**, never a colour on its own: §8.7 is explicit that the UI does not
    colour an R^2 red for being small.
    """

    construct_code: str
    r_squared: float | None
    r_squared_adj: float | None
    q_squared: float | None
    band: str
    #: ``> 0`` is predictive relevance. ``None`` for an exogenous construct.
    q_status: Status = "na"


class FSquaredRow(_Stats):
    """`docs/07` §8.7. 0.02 small, 0.15 medium, 0.35 large."""

    source: str
    target: str
    f_squared: float
    effect_size: str


class PredictRow(_Stats):
    """`docs/07` §8.8. PLS errors against a linear-model benchmark, per indicator."""

    construct_code: str
    indicator: str
    q2_predict: float
    rmse_pls: float
    rmse_lm: float
    mae_pls: float
    mae_lm: float
    #: ``ok`` when Q2_predict > 0 and PLS RMSE beats the LM benchmark.
    status: Status = "ok"

    @property
    def beats_benchmark(self) -> bool:
        return self.rmse_pls < self.rmse_lm


class PredictSummary(_Stats):
    """`docs/07` §8.8's four-way reading, computed from the indicator rows."""

    verdict: Literal["strong", "medium", "low", "none"]
    indicators: int
    beating_benchmark: int
    q2_positive: int
    note: str


class FitRow(_Stats):
    """`docs/07` §8.9. **Report fit, do not lead with it.**"""

    statistic: str
    value: float | None
    threshold: str
    status: Status


# --------------------------------------------------------------------------- the run

class AnalysisProvenance(_Stats):
    """The five facts `docs/07` §9 requires on **every** result view, plus the model fingerprint.

    The paper must state all of them, so a result view that cannot show them is a result view that
    cannot be published from.
    """

    engine_version: str
    n_cases: int
    bootstrap_samples: int
    seed: int
    screening: Screening
    population: Population
    model_fingerprint: str
    #: `docs/07` §10. ``False`` until the golden test passes; drives the UNVALIDATED banner.
    engine_validated: bool = False


class StageResult(_Stats):
    """One persisted stage. `docs/01` §6.8 — never recomputed on resume."""

    stage: str
    payload: dict = Field(default_factory=dict)
    computed_at: str | None = None


class AnalysisRunView(_Stats):
    """One analysis run as the Statistics screen reads it. `docs/06` §7."""

    analysis_id: str
    status: str
    provenance: AnalysisProvenance
    stages_done: tuple[str, ...] = ()
    stage_cursor: str | None = None
    #: The warning `docs/07` §9 requires below 1,000 samples. Empty when not applicable.
    bootstrap_warning: str = ""

    @property
    def is_complete(self) -> bool:
        return set(self.stages_done) >= set(STAGES)


class StatsTableSpec(_Stats):
    """What `stats_table` renders. `docs/05` §4.4.

    §4.4 requires a statistical abbreviation to carry **both** a ``title`` and a **visible legend**
    above the table, because ``rho_A`` and ``AVE`` are not self-explanatory even to the intended
    reader (`docs/05` §6). ``legend`` is therefore not optional and the renderer raises without it.
    """

    title: str
    headers: tuple[str, ...]
    #: ``abbreviation -> what it means``, rendered above the table and as a ``title`` attribute.
    legend: tuple[tuple[str, str], ...]
    caption: str = ""
    empty: str = ""
