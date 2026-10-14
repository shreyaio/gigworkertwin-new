"""The analyst's input bundle and output. `docs/02` §4.4 and §6.

I12: no model ever produces a metric. The analyst receives one deterministically assembled bundle
of numbers Python computed, and its prose is checked against that bundle before storage — prompt
instructions alone are necessary but not sufficient.

The bundle's *assembly* is M8. Declared here so `SCHEMA_REGISTRY` can name it at M2, and because
:meth:`AnalysisBundle.numeric_tokens` is what the M2 grounding check consumes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisBundle(BaseModel):
    """Everything the analyst is allowed to know. `docs/02` §4.4.

    The same bundle, in the same order, that the Results side panel shows — so the researcher can
    read the input and the output together.
    """

    model_config = ConfigDict(extra="forbid")

    version_code: str
    fairwork_score: int
    #: "What the twins are told": the per-dial commitment summary. Researcher-facing bullets,
    #: never the twin-facing paragraph (`docs/03` §4.3).
    commitment_summary: dict[str, list[str]] = Field(default_factory=dict)
    scenario_text: list[str] = Field(default_factory=list)
    baselines: dict[str, float] = Field(default_factory=dict)
    shifts: dict[str, float] = Field(default_factory=dict)
    index_value: float | None = None
    twins_n: int = 0
    #: Only interactions whose three cells are all completed. Nothing is imputed (I17).
    interactions: list[dict] = Field(default_factory=list)
    #: The session's `SHAM − 00000` demand-characteristic floor. A shift smaller than this is not
    #: interpretable and the analyst is instructed to say so.
    sham_floor: float | None = None

    def numeric_tokens(self) -> set[str]:
        """Every number the analyst may write, at full precision and rounded to 1 and 2 dp.

        Generated from the bundle, never hand-maintained (`docs/02` §6.1). Rounded forms are
        included because "+1.6" is a legitimate rendering of `1.62`.

        The set also holds the small integers the bundle *structurally* implies — `twins_n`, the
        metric count, the dial values present, the version code's digits — because ordinals in
        prose ("the six outcomes", "both levers") are legitimate. Nothing more than that.
        """
        tokens: set[str] = set()

        def add(value: float | int | None) -> None:
            if value is None:
                return
            tokens.add(str(value))
            if isinstance(value, float):
                tokens.add(f"{value:.1f}")
                tokens.add(f"{value:.2f}")
                # A float that is exactly integral reads as an integer in prose.
                if value.is_integer():
                    tokens.add(str(int(value)))
            # Signed renderings: prose writes "+1.6" and "-0.59" for the same numbers.
            if isinstance(value, float):
                tokens.add(f"{value:+.1f}")
                tokens.add(f"{value:+.2f}")
            else:
                tokens.add(f"{value:+d}")
            tokens.add(str(abs(value)))
            if isinstance(value, float):
                tokens.add(f"{abs(value):.1f}")
                tokens.add(f"{abs(value):.2f}")

        add(self.fairwork_score)
        add(self.index_value)
        add(self.twins_n)
        add(self.sham_floor)
        for value in self.baselines.values():
            add(value)
        for value in self.shifts.values():
            add(value)
        for interaction in self.interactions:
            for value in interaction.values():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    add(value)

        # The version code, whole and by digit — a code is a number the analyst must be able to
        # name, and its digits are the dial values.
        tokens.add(self.version_code)
        for digit in self.version_code:
            if digit.isdigit():
                tokens.add(digit)
        # The structural counts: how many metrics the bundle carries, how many levers moved.
        tokens.add(str(len(self.shifts)))
        tokens.add(str(len(self.baselines)))
        tokens.add(str(sum(1 for d in self.version_code if d.isdigit() and d != "0")))
        return tokens


class AnalysisResult(BaseModel):
    """The analyst's prose. `docs/02` §4.4.

    ``confidence: "none"`` is how it signals that a cell has no defensible reading — and a cell
    with no defensible reading gets no reading. It is a recorded outcome, never a discarded one.
    """

    model_config = ConfigDict(extra="forbid")

    prose: str = ""
    confidence: Literal["high", "medium", "low", "none"] = "medium"
    reason: str = ""


class AnalysisConfig(BaseModel):
    """Index weights and precision. `docs/07` §4.1.

    **The default is unweighted and that is what the paper reports.** Weights exist for sensitivity
    analysis; any non-default set is recorded on the run and shown in the UI, so a reweighted index
    cannot be mistaken for the headline one.

    The sign flip for `pushback` and `leaving` is deliberately **not** here — it comes from
    `constructs.index_sign` in the frozen reference data. In config, a researcher could invert the
    meaning of a metric by editing a file.
    """

    model_config = ConfigDict(extra="forbid")

    weights: dict[str, float] = Field(default_factory=dict)
    bootstrap_samples: int = 5000
    decimals: int = 3

    @field_validator("bootstrap_samples")
    @classmethod
    def _floor(cls, v: int) -> int:
        """`analysis_bootstrap_floor` — the DDL refuses fewer than 30."""
        if v < 30:
            raise ValueError(
                f"bootstrap_samples must be at least 30, got {v}: fewer resamples report a "
                "confidence interval narrower than the evidence supports (docs/07 §9)"
            )
        return v

    @field_validator("weights")
    @classmethod
    def _non_negative(cls, v: dict[str, float]) -> dict[str, float]:
        negative = sorted(k for k, w in v.items() if w < 0)
        if negative:
            raise ValueError(
                f"negative index weight for {negative}. A negative weight inverts a metric's "
                "meaning; the sign flip belongs to `constructs.index_sign` (docs/07 §4.1)."
            )
        return v


class MetricScores(BaseModel):
    """Six metric means for one answer vector, each on **its own scale**. `docs/07` §2.2.

    Five-point metrics are never rescaled to seven: `clarity` and `staying` are reported on 1-5,
    the rest on 1-7. Standardisation happens at the modelling stage, never in the display metric.
    """

    model_config = ConfigDict(extra="forbid")

    scores: dict[str, float] = Field(default_factory=dict)


class CellShifts(BaseModel):
    """One cell's shifts, index and the twin set they were computed over. `docs/07` §3.

    ``twin_ids`` is carried, not just counted, because `docs/07` §3.1's paired-sample rule is the
    single most dangerous piece of arithmetic in the counterfactual layer: both means must be taken
    over **exactly** this set. Storing it makes the rule auditable after the fact rather than a
    property of the function that computed it.
    """

    model_config = ConfigDict(extra="forbid")

    version_code: str
    baselines: dict[str, float] = Field(default_factory=dict)
    shifts: dict[str, float] = Field(default_factory=dict)
    index_value: float | None = None
    twin_ids: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)

    @property
    def twins_n(self) -> int:
        return len(self.twin_ids)


class NoiseFloor(BaseModel):
    """How much a twin moves when nothing changed. `docs/07` §6, measured at two levels.

    **One number was not enough, and the single number was systematically too small.** Until
    2026-10-07 the floor was ``|index(00000)|`` — the absolute value of a *signed, sign-flipped,
    cross-metric mean*. Every statistic judged against it is a **mean of absolute values**, and by
    Jensen's inequality ``|E[X]| <= E[|X|]``: a floor built by letting metrics cancel can never
    exceed the quantity it gates, so every floor-judged test was biased toward `FAIL`. The two
    levels here are the two functionals the five tests actually compute, so each is compared with
    something on its own scale.

    * :attr:`cell` — mean over the six metrics of ``|mean over twins of the shift|``. The
      cell-level movement, which is what tests 2 and 8 measure.
    * :attr:`twin` — mean over the six metrics of ``mean over twins of |the twin's own shift|``.
      The per-twin movement, which is what tests 4, 5 and 6 measure. It is always at least
      :attr:`cell` and is usually much larger, because one twin moving up and another down leaves
      :attr:`cell` at zero and :attr:`twin` untouched.

    Both breakdowns are carried per metric, because tests 4 and 6 judge a **single** metric
    (happiness, fairness) and a six-metric average is not that metric's floor.

    ``twins_n`` is ``gt=0`` by construction: a floor measured on nobody is not a floor, and a cell
    judged against an unmeasured floor is judged against nothing (I15's shape).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    #: Mean over metrics of |mean shift|. Gates the cell-level statistics.
    cell: float = Field(ge=0)
    #: Mean over metrics of mean |per-twin shift|. Gates the per-twin statistics.
    twin: float = Field(ge=0)
    cell_by_metric: dict[str, float] = Field(default_factory=dict)
    twin_by_metric: dict[str, float] = Field(default_factory=dict)
    twins_n: int = Field(gt=0)

    def for_metric(self, metric: str, *, per_twin: bool) -> float:
        """One metric's floor at the level asked for, falling back to the overall figure.

        The fallback is the **overall** floor rather than zero: a metric absent from the control
        measurement has no floor of its own, and zero is the one value guaranteed to be wrong in
        the direction that manufactures a verdict.
        """
        table = self.twin_by_metric if per_twin else self.cell_by_metric
        default = self.twin if per_twin else self.cell
        return table.get(metric, default)


class Interaction(BaseModel):
    """Whether two levers compound or substitute. `docs/07` §5.

    **Sub-additivity is the contribution.** It tells a regulator which reform to mandate when only
    one is affordable — a claim no small vignette study can support.
    """

    model_config = ConfigDict(extra="forbid")

    a: str
    b: str
    joint: str
    metric: str
    alone_a: float
    alone_b: float
    together: float
    extra: float
    verdict: Literal["sub-additive", "super-additive", "additive"]


class MissingInteraction(BaseModel):
    """A leg that has not run. I17 — **never imputed**, and the code to run is named.

    `CLAUDE.md` rule 5: if an interaction needs three runs and has two, report which code to run.
    No estimates, no interpolation, no "approximately". This model is how that reaches the UI, and
    it is why :func:`interactions.interaction` returns a value rather than ``None`` alone.
    """

    model_config = ConfigDict(extra="forbid")

    a: str
    b: str
    joint: str
    metric: str
    #: The version codes with no completed run. What the UI tells the researcher to run.
    missing_codes: list[str] = Field(default_factory=list)
