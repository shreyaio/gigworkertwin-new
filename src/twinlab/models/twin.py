"""The twin's input and output shapes. `docs/02` §5.2 and §4.2.

The output shape is **flat** on purpose. An unconstrained model produces flat key–value output far
more reliably than nested JSON, and a flat shape makes a partial answer *repairable* rather than a
total loss (`docs/02` §5.2).

Validation here reads the item register, so a 5-point item's range comes from `instrument.json`
rather than from a constant in this file. The prototype's prompt said "1 to 7" for every item and
three of its nine constructs were 5-point; `scales.points` is now the only source.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Language = Literal["en", "hi", "mr"]

#: Why-probe and own-words fields carry no `item_id`: the 73-item register is frozen. They are
#: addressed by these stable keys, which the persona templates and `config/form_map.yaml` share.
WHY_PROBE_IDS: tuple[str, ...] = ("WHY_CONTROL", "WHY_SATISFACTION", "WHY_OTHER_WORK")
OWN_WORDS_IDS: tuple[str, ...] = ("OWN1", "OWN2", "OWN3", "OWN4", "OWN5")

#: Which battery item each why-probe is paired with, for `survey_answers.why_text`.
WHY_PROBE_ANCHOR: dict[str, str] = {
    "WHY_CONTROL": "PAC11",      # Part 6 q12, on the app controlling how you work
    "WHY_SATISFACTION": "SAT1",  # Part 9 q4, the main reason for the satisfaction rating
    "WHY_OTHER_WORK": "DEP1",    # Part 13 q3, why other work is easy or hard to find
}


class Background(BaseModel):
    """Part 3 extras, Part 4 and Part 14. Survey content with no `item_id`. `docs/01` §6.2.

    These cannot be `survey_answers` rows: that table's `item_id` is a foreign key into the frozen
    73-item register, and none of these questions is in it. The persona must be lossless (I6), so
    they travel on `twins.background` rather than being dropped. Written once at intake, never
    edited.
    """

    model_config = ConfigDict(extra="forbid")

    platform_count: str | None = None            # P3 q5: 1 | 2 | 3 or more
    other_apps: str | None = None                # P3 q6
    vehicle_arrangement: str | None = None       # P4 q1
    dependants: int | None = None                # P4 q2
    other_household_income: str | None = None    # P4 q3
    education: str | None = None                 # P4 q4
    years_driving_before_uber: float | None = None   # P4 q5
    own_words: dict[str, str] = Field(default_factory=dict)
    """Part 14, verbatim, keyed by :data:`OWN_WORDS_IDS`. Without this the persona silently loses
    the driver's own words (`docs/03` §7.1)."""
    translations: dict[str, str] = Field(default_factory=dict)
    """Bracketed English of a non-English free-text answer, keyed the same as its source."""


class Twin(BaseModel):
    """A driver, and the twin built from them. `docs/01` §6.2.

    Consent lives on the submission in 2.0, not here: a respondent who withheld consent never
    becomes a twin at all, so there is no `consent_twin` field to get out of step with the row
    that records the consent.
    """

    model_config = ConfigDict(extra="forbid")

    twin_id: str
    submission_id: str | None = None
    #: `manual` twins are sandbox objects: no real survey row, so no holdout, no quality score,
    #: and never eligible for an analysis panel (`docs/03` §9.3).
    source: Literal["real", "synthetic", "manual"] = "real"
    service: str | None = None
    city: str | None = None
    age: int | None = None
    gender: str | None = None
    tenure_months: int | None = None
    hours_per_week: int | None = None
    background: Background = Field(default_factory=Background)
    persona_passage: str | None = None
    persona_hash: str | None = None
    persona_template_version: str | None = None


class SurveyResponse(BaseModel):
    """One driver's submission, as the persona builder consumes it.

    ``answers`` holds every Likert item the driver answered, keyed by `item_id` — **including** the
    holdouts, which the builder excludes absolutely (I6) but the quality gate needs. Keeping them in
    one object rather than two is deliberate: the exclusion is then a property of the builder, which
    is tested, rather than of whoever assembled the input.
    """

    model_config = ConfigDict(extra="forbid")

    twin_id: str
    language: Language = "en"
    answers: dict[str, int] = Field(default_factory=dict)
    whys: dict[str, str] = Field(default_factory=dict)
    own_words: dict[str, str] = Field(default_factory=dict)
    translations: dict[str, str] = Field(default_factory=dict)
    """Bracketed English of a non-English free-text answer, keyed the same as its source."""

    @field_validator("whys")
    @classmethod
    def _known_probes(cls, v: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(v) - set(WHY_PROBE_IDS))
        if unknown:
            raise ValueError(f"unknown why-probe ids {unknown}")
        return v

    @field_validator("own_words")
    @classmethod
    def _known_own_words(cls, v: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(v) - set(OWN_WORDS_IDS))
        if unknown:
            raise ValueError(f"unknown own-words ids {unknown}")
        return v


class PersonaPassage(BaseModel):
    """The deterministic first-person passage. Same row in, byte-identical passage out.

    ``persona_hash`` is what ties a result back to the exact text that produced it (I11). The
    passage is stored on `twins.persona_passage`; the round prompt is rebuilt from the hash and the
    other stored fields, never stored itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    twin_id: str
    text: str
    persona_hash: str
    template_version: str
    clause_count: int
    items_used: list[str]


class PanelCandidate(BaseModel):
    """A twin considered for the analysis panel. `docs/03` §9.1.

    Deliberately narrow: the draw is stratified on `city × service` and filtered on `source` and
    the H3 quality verdict, so nothing else about a twin can influence who is selected. The
    service layer builds these from `twins` plus the latest `twin_quality_runs` row; the draw
    itself never touches a database.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    twin_id: str
    source: str
    city: str | None = None
    service: str | None = None
    #: The latest H3 verdict. Manual twins have no real survey row, so no holdout and no score.
    quality_passed: bool = False

    @property
    def stratum(self) -> str:
        """`'Mumbai|cab'`. `docs/01` §6.4.

        A missing city or service becomes the literal `unknown` rather than an empty string, so a
        twin with incomplete demographics lands in a named stratum instead of silently joining
        whichever other twins happen to share its blanks.
        """
        return f"{self.city or 'unknown'}|{self.service or 'unknown'}"


class PanelMember(BaseModel):
    """One drawn twin, with the draw order that makes the panel reproducible from the seed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    twin_id: str
    stratum: str
    position: int


class RoundPrompt(BaseModel):
    """What a twin is given for one round. `docs/02` §4.2 and I8.

    Persona and round prompt are **separate documents**. This one holds the scenario text, the
    twin's own baseline *numbers* and the battery to re-answer — and nothing else. It carries no
    why-text, no open-ended answers, no version code, no digits identifying dials and no holdout
    items. Keeping them apart is what stops a twin restating its own justifications under every
    counterfactual.

    Nothing here is ever stored: the prompt is **rebuilt** from the stored seed, persona hash,
    lever order, style version and wording (I11, `ARCHITECTURE.md` §7.2).
    """

    model_config = ConfigDict(extra="forbid")

    persona_hash: str
    #: The five paragraphs in the order actually shown. Randomised per twin per round so
    #: paragraph position cannot become a confound; persisted on `twin_answers.lever_order`.
    scenario: list[str]
    lever_order: list[int]
    #: The twin's own survey answers for the battery items — numbers, not words. This is the one
    #: place numbers are correct: they are what the twin is being asked to revise.
    baseline: dict[str, int]
    #: item_id → (stem, points). Each item's own range travels with it (`docs/02` §4.2 rule 6).
    battery: dict[str, tuple[str, int]]
    wording: str = "A"
    seed: int | None = None


class AnswerVector(BaseModel):
    """The **transport** shape handed to the provider. Deliberately permissive. `CLAUDE.md` rule 4.

    This is not a validation model and must never grow one. It exists because the thing a provider
    is shown and the thing a reply is judged against have to be two different objects:

    * Ollama Cloud accepts a JSON schema and silently does not enforce it, so a schema handed to
      the provider validates nothing. Trusting it is exactly what rule 4 forbids.
    * Worse, pydantic-ai *does* validate the marker schema on the way out. Handing it
      :class:`TwinAnswerSet` means a 36-item reply raises **inside** pydantic-ai, before
      :func:`~twinlab.agents.contract.run_answer_ladder` ever sees it — so the one targeted repair
      `docs/02` §5.4 specifies never happens, and a repairable vector is recorded as a total
      failure.

    So the provider is shown this: any string keys, any integer values, no cross-field rule. The
    real contract — exactly the expected ids, each inside **its own** register range — is applied
    in Python by the ladder against :class:`TwinAnswerSet` or :class:`QualityAnswerSet`.

    The value type is ``Any``, not ``int``, for the same reason. pydantic would reject ``5.5`` and
    ``null`` on a ``dict[str, int]`` — and those are precisely the ``not_an_integer`` defects the
    ladder exists to name and re-ask for. A transport model that rejects anything moves a judgement
    out of Python and into the provider round trip. It must reject **nothing**.

    Permissive here is not laxity: nothing downstream ever reads an ``AnswerVector``. It is the
    ladder's raw input, and a vector that cannot pass the real contract after one repair fails.
    """

    model_config = ConfigDict(extra="allow")

    answers: dict[str, Any] = Field(default_factory=dict)
    #: Display only (I12). ``Any`` so a model that answers with a number here cannot cost a
    #: perfectly good 37-item vector its one repair attempt.
    rationale: Any = ""


class TwinAnswerSet(BaseModel):
    """The twin's 37 numbers. `docs/02` §5.2.

    Implements I13: exactly the expected item ids, each within **its own** scale range, validated
    in Python against the item register every time, because the provider accepts a schema and
    silently does not enforce it. A malformed answer is retried, then failed. It is never coerced,
    padded, truncated or rounded into validity.
    """

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, int]
    #: Display only. Never parsed for data and never enters a metric (I12). The per-block
    #: "reasons" the prototype collected are deliberately not requested: at one concurrent
    #: request, a third more output tokens for something no number depends on is a real cost.
    rationale: str = ""

    @model_validator(mode="after")
    def _check(self) -> TwinAnswerSet:
        # Deferred import: `models/` is the bottom layer and must not depend on `ingest/` at
        # import time. The register is a frozen file read once, so this costs nothing per call.
        from twinlab.ingest.reference_store import reference

        ref = reference()
        expected = set(ref.battery_item_ids)
        got = set(self.answers)
        if got != expected:
            raise ValueError(
                f"missing={sorted(expected - got)} extra={sorted(got - expected)}"
            )
        for item_id, value in self.answers.items():
            points = ref.scale_points(item_id)
            # `bool` is an `int` in Python, and `True` is not an answer.
            if isinstance(value, bool) or not 1 <= value <= points:
                raise ValueError(f"{item_id}={value!r} outside 1..{points}")
        return self


class QualityAnswerSet(BaseModel):
    """A holdout answer vector. `docs/01` §3.5 and §3.6.

    The same contract as :class:`TwinAnswerSet` over a different item set: H3's 18 items (the
    fidelity gate) or H2's 16 (the second set). The expected ids are supplied by the caller,
    because which holdout is being run is the caller's business — but the per-item range still
    comes from the register, never from a constant.
    """

    model_config = ConfigDict(extra="forbid")

    holdout_set: str
    answers: dict[str, int]
    expected_items: list[str] = Field(default_factory=list)
    rationale: str = ""

    @model_validator(mode="after")
    def _check(self) -> QualityAnswerSet:
        from twinlab.ingest.reference_store import reference

        ref = reference()
        if self.expected_items:
            expected = set(self.expected_items)
            got = set(self.answers)
            if got != expected:
                raise ValueError(
                    f"missing={sorted(expected - got)} extra={sorted(got - expected)}"
                )
        for item_id, value in self.answers.items():
            points = ref.scale_points(item_id)
            if isinstance(value, bool) or not 1 <= value <= points:
                raise ValueError(f"{item_id}={value!r} outside 1..{points}")
        return self


class StudioReply(BaseModel):
    """A twin's answers to the researcher's own questions. `docs/06` §5.

    **Display only, and quarantined twice over.** It is prose, so it never enters a metric (I12),
    and it is produced only by `services/studio.py`, which has no code path to `runs`
    (`docs/01` §6.9). Nothing downstream parses it.

    ``replies`` is positional against the questions asked, so a short reply cannot be silently
    matched to the wrong question — the validator refuses a count that does not line up rather
    than padding it, which is the same rule the answer contract applies to a short vector.
    """

    model_config = ConfigDict(extra="forbid")

    replies: list[str] = Field(default_factory=list)
    rationale: str = ""

    def aligned(self, questions: list[str]) -> dict[str, str]:
        """``question → reply``. Raises when the counts disagree.

        Never zipped short and never padded: a reply attached to a question the twin did not
        answer is a fabricated answer, which is exactly what `CLAUDE.md` forbids one level up for
        the numeric vector.
        """
        if len(self.replies) != len(questions):
            raise ValueError(
                f"{len(self.replies)} replies for {len(questions)} questions; a reply cannot be "
                "matched to a question it does not belong to"
            )
        return dict(zip(questions, self.replies, strict=True))


class TwinConfig(BaseModel):
    """The twin agent's live settings and the quality gate's thresholds. `docs/09` §4.

    Frozen onto every session's `config` column, so a threshold change is visible in the data rather
    than silently retroactive (`docs/08` §2.2). `extra="forbid"`: a setting that does not exist here
    cannot be smuggled in per run, which is what keeps two sessions comparable.
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    #: CONFIG and the live empirical question. **Set from validity test 8; do not pick it**
    #: (`docs/02` §7.3). Seeded at 0.7 as a placeholder, matching `agents.default.yaml`.
    temperature: float = 0.7
    #: `docs/08` §2.1 — repeat the H3 gate and average, so one bad sample does not discard a good
    #: twin.
    quality_runs_per_twin: int = 3
    #: **Keep iff `mae <= mae_max` AND `pct_within_1 >= pct_within_1_min`.** Both CONFIG, both
    #: recorded on every quality run.
    mae_max: float = 1.0
    pct_within_1_min: float = 0.80
    #: A recorded field, **not a UI control**: there is no no-baseline arm (`docs/03` §8). The
    #: quality gate overrides it to False, because the human had no baseline either.
    show_baseline: bool = True
    #: Which wording variant of the battery stems. Validity test 5 swaps it.
    wording: str = "A"

    @field_validator("quality_runs_per_twin")
    @classmethod
    def _at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quality_runs_per_twin counts the first run, so it is at least 1")
        return v

    @field_validator("pct_within_1_min")
    @classmethod
    def _a_proportion(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"pct_within_1_min is a proportion, got {v}")
        return v


class QualityScore(BaseModel):
    """One holdout scoring. `docs/08` §2.2.

    ``items_n`` is the number of items that **actually scored** — present in both the human's and
    the twin's answers. It is carried rather than recomputed because it is the thing I15 turns on: a
    score over zero scorable items is not a perfect score, it is no score, and
    `twin_quality_runs.items_n > 0` is a database constraint.
    """

    model_config = ConfigDict(extra="forbid")

    mae: float
    pct_within_1: float
    items_n: int

    @field_validator("items_n")
    @classmethod
    def _never_empty(cls, v: int) -> int:
        """I15 — a score over nothing is never a score."""
        if v <= 0:
            raise ValueError(
                "items_n must be > 0: a quality score over zero scorable items is no score, "
                "never a perfect one (I15)"
            )
        return v

    def keeps(self, *, mae_max: float, pct_within_1_min: float) -> bool:
        """`docs/08` §2.2 — keep iff **both** thresholds are met. Never either/or."""
        return self.mae <= mae_max and self.pct_within_1 >= pct_within_1_min
