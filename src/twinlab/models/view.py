"""Read-only shapes the UI renders. `docs/06_SCREENS.md`.

`CLAUDE.md` rule 13: every Pydantic model lives here in `models/`. These are the shapes the
service layer hands to `ui/`, and they exist so no bare dict crosses that boundary
(`ARCHITECTURE.md` §4).

Two properties of this module are load-bearing rather than tidy:

* **Every value is already formatted or already computed.** A view model carries
  ``index_text = "0.143"`` beside ``index_value = 0.143`` so a Gradio handler never does
  arithmetic on a shift — `docs/05` §8.4 rule 5, and the M10 acceptance test that asserts it.
* **Absence is a value, not a blank.** ``MetricRow.value is None`` renders ``Not tested``; a
  missing interaction leg renders the code to run. Nothing here can express "approximately" (I17).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _View(BaseModel):
    model_config = ConfigDict(extra="forbid")


#: `docs/05` §4.2. Green complete, amber running, red failed, grey pending. Always beside a text
#: label — never alone (§6, "never colour alone").
DotState = Literal["complete", "running", "failed", "pending"]


class StatusRow(_View):
    """One row of a two-column status table. `docs/06` §1.3 and §3.1.

    ``value`` is a string because these tables mix counts, ratios and words — ``7 of 242``,
    ``Not run``, ``HF OAuth · twinlab``. Formatting happens in the service layer so the same row
    reads identically on the Main menu and in the Agents tab.
    """

    label: str
    value: str
    #: Set when the row reports progress or health, so the dot always has this text beside it.
    state: DotState | None = None


class LinkCard(_View):
    """A titled card that goes somewhere. `docs/06` §1.1 and §1.2.

    ``tab`` names a Twin Lab sub-tab when ``route`` is ``/lab``; the Main menu's cards point at
    seven distinct tabs, and dropping that half of the destination would land four of the seven
    workflow groups on the same screen.
    """

    title: str
    description: str
    route: str
    tab: str | None = None


class CardGroup(_View):
    """One `section_card` of link cards. `docs/06` §1.1's seven groups."""

    title: str
    cards: list[LinkCard] = Field(default_factory=list)


class TellBullet(_View):
    """One line of "what the twins are told". `docs/03` §4.3.

    Researcher-facing, and **never fed to a model**: the twin sees the rendered paragraph, built
    from ``gap_id`` by a different path. The two must never be swapped.
    """

    gap_id: str
    text: str


class TellLever(_View):
    """One lever's bullets, with the dial that selected them."""

    lever: str
    lever_name: str
    dial: int
    #: ``Pay step 1``. A dial-0 lever carries no bullets and this reads ``Pay — no change``.
    heading: str
    bullets: list[TellBullet] = Field(default_factory=list)


class DialBoard(_View):
    """Everything the Dial board shows for one code, computed with **no network call**.

    `docs/05` §8.4 rule 6 and the M10 acceptance test: changing a dial recomputes the code, the
    Fairwork score and "what the twins are told" from reference data already in process.

    ``is_control`` is why *Ask the twins* is disabled. `00000` is a control cell the orchestrator
    runs, not a cell a researcher pokes at (`docs/03` §6.1, `docs/05` §7 rule 3).
    """

    version_code: str
    dials: dict[str, int] = Field(default_factory=dict)
    fairwork_score: int = 0
    #: ``Fairwork score 1 of 10`` — pre-formatted so two screens cannot word it differently.
    fairwork_text: str = ""
    told: list[TellLever] = Field(default_factory=list)
    is_control: bool = False
    warning: str | None = None


class MetricRow(_View):
    """One row of `metric_bars`. `docs/05` §4.5.

    ``good_for_driver`` is the colour, and it is **not** the sign. `leaving −0.59` extends left
    and is green; `pushback +1.20` extends right and is red. Getting this backwards inverts the
    headline finding on every screen that shows it, so the service layer decides it from
    ``constructs.index_sign`` and the UI only paints what it is told.

    ``bar_pct`` is the bar's half-width as a percentage of the row, already scaled to the largest
    absolute shift on screen. The UI does no arithmetic on ``value``.
    """

    metric: str
    label: str
    value: float | None = None
    #: ``+0.07``, or ``Not tested`` when ``value`` is ``None``. Never a fabricated number.
    value_text: str = "Not tested"
    good_for_driver: bool | None = None
    bar_pct: float = 0.0


class MetricBars(_View):
    """Six rows, the index and one plain sentence. `docs/05` §4.5."""

    rows: list[MetricRow] = Field(default_factory=list)
    index_value: float | None = None
    index_text: str = "Not tested"
    twins_n: int = 0
    caption: str = ""
    #: Set when the index sits inside the `SHAM − 00000` demand floor or the `00000` noise floor.
    floor_note: str | None = None


class GridCell(_View):
    """One of the 243 cells. `docs/06` §3.7, `docs/05` §8.3.

    ``outline`` carries the two semantic outlines: `00000` is red ("Uber today"), the best index
    is gold. Both are stated in the accessible name too, because the grid may never encode
    anything by colour alone (`docs/05` §6).
    """

    version_code: str
    row: int
    col: int
    index_value: float | None = None
    tested: bool = False
    outline: Literal["control", "best"] | None = None
    #: Where this cell's index sits in the tested range, ``0.0`` at the lowest tested index and
    #: ``1.0`` at the highest. ``None`` when untested. It is the **only** thing the cell's colour
    #: depth encodes, and it is relative to the cells tested so far — so a grid with two results
    #: shows one pale and one deep, and both move as more cells arrive. The exact index is in the
    #: accessible name and in the Tested versions table beneath, because the grid may never encode
    #: anything by colour alone (`docs/05` §6).
    intensity: float | None = None
    #: ``version 21122, index 1.245`` or ``version 21122, not tested``.
    accessible_name: str = ""


class TestedVersionRow(_View):
    """One row of the Tested versions table — the grid's accessible equivalent (`docs/05` §6)."""

    version_code: str
    fairwork_score: int
    twins_n: int
    shifts: dict[str, float] = Field(default_factory=dict)
    index_value: float | None = None
    run_id: str | None = None
    #: ``sweep`` or ``studio``. `ARCHITECTURE_UPDATE.md` §4.3 item 4: a row whose latest run came
    #: from the Twin Studio reports an index over **one twin**, while `00000` and `SHAM` come from
    #: the frozen panel — so the two are not the same quantity. The table shows this column and
    #: ``twins_n`` together rather than leaving a reader to infer one from the other.
    origin: str = "sweep"


class InteractionRow(_View):
    """A computable interaction, or a named missing leg. I17.

    When ``computable`` is false, ``text`` is :func:`analysis.interactions.describe_missing`'s
    sentence naming the codes to run. It is never an estimate and never a blank.
    """

    a: str
    b: str
    joint: str
    metric: str
    computable: bool
    text: str
    missing_codes: list[str] = Field(default_factory=list)


class TwinRow(_View):
    """One row of the Twins list. Columns in `docs/06` §3.3 order.

    ``quality_text`` is ``Kept (0.56)`` or ``Dropped (1.1)`` — the number is always beside the
    colour (`docs/05` §6).
    """

    twin_id: str
    service: str = ""
    city: str = ""
    age: str = ""
    source: str = ""
    quality_text: str = "Not run"
    quality_state: DotState = "pending"


class AnswerCompareRow(_View):
    """One item across driver, baseline twin and variant twin. `docs/06` §3.3.

    ``variant`` is ``None`` when that version has no completed run, and the UI renders
    ``Not tested`` — never a fabricated number, never a neighbour's value (I17).
    """

    item_id: str
    question: str
    driver: int | None = None
    baseline: int | None = None
    variant: int | None = None
    hidden: bool = False


class AnswerCompareBlock(_View):
    """One construct block of the comparison, in battery order."""

    construct_code: str
    label: str
    rows: list[AnswerCompareRow] = Field(default_factory=list)


class TwinPanel(_View):
    """The Twins side panel, in the seven-step order of `docs/06` §3.3.

    The order is mandatory and one step of it is a research property: the **scenario text comes
    before the answers**, so the reader sees what the twin was told before reading what it said.
    """

    twin_id: str
    identity: str = ""
    background: str = ""
    quality_line: str = ""
    persona_text: str = ""
    persona_hash: str = ""
    compare_codes: list[str] = Field(default_factory=list)
    selected_code: str | None = None
    scenario_text: list[str] = Field(default_factory=list)
    blocks: list[AnswerCompareBlock] = Field(default_factory=list)
    not_tested: bool = False


class ValidationSummary(_View):
    """`docs/06` §3.4's summary card. Canonical part numbers — 16 and 17, never 10 / 10b."""

    twins_checked: int = 0
    h2_mae: float | None = None
    h2_within_one: float | None = None
    h3_mae: float | None = None
    h3_r: dict[str, float | None] = Field(default_factory=dict)
    #: True whenever the checked set includes synthetic twins or mock-model output. The warning
    #: is not optional: validation on synthetic data always looks good, and it tests the
    #: machinery rather than whether the twins are valid.
    synthetic_present: bool = False


class ValidationRow(_View):
    """One per-twin validation row.

    ``arm_seen`` exists because H2 validation must show a twin **its own driver's arm**
    (`docs/01` §5). A mismatch is a bug, and this column is how it is caught — so it is a
    required field, not an optional extra.
    """

    twin_id: str
    arm_seen: str
    h2_error: float | None = None
    within_one: float | None = None
    versions: int = 0
    h3_error: float | None = None
    fairness_r: float | None = None
    pushback_r: float | None = None
    staying_r: float | None = None


class ValidityTestCard(_View):
    """One of the eight tests. `docs/06` §3.5; definitions live in `docs/08` §4."""

    number: int
    name: str
    question: str
    what_it_does: str
    needs_live_model: bool = False


class ValidityResultRow(_View):
    """One appended validity result. **Append-only** — a completed test adds a row, never
    replaces one (I9).

    ``verdict`` includes ``INCONCLUSIVE``, which is mandatory whenever ``twins_n = 0`` (I15). The
    prototype recorded live-mode `PASS` verdicts on zero twins; that must be unrenderable here.
    """

    when: str
    test: str
    twins_n: int
    model: str
    result: str
    verdict: Literal["PASS", "FAIL", "CHECK", "INCONCLUSIVE"]


class EventRow(_View):
    """One `run_events` row for `log_tree`. `docs/04` §7.3.

    Polling is incremental: ``event_id`` is the cursor handed back to
    :func:`twinlab.services.runs.events_since`. The stream is never re-fetched whole — at sweep
    scale that is tens of thousands of rows per UI tick.
    """

    event_id: int
    parent_id: int | None = None
    when: str
    agent: str
    stage: str
    status: str
    message: str
    depth: int = 0
    payload: dict | None = None


class BudgetView(_View):
    """`budget_summary` (`docs/05` §4.4), shown on every confirm step.

    ``est_credits_text`` reads ``not known`` rather than a number: the Ollama Cloud free credit
    allowance is unpublished (`docs/10` §3.3), and an invented figure here would be reported as a
    cost.
    """

    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_hours_text: str = ""
    est_credits_text: str = "not known"
    cache_hits: int = 0
    warnings: list[str] = Field(default_factory=list)
    #: How the call total was arrived at — ``6 versions × 2 repeats × 50 twins``. The quality
    #: gate's 600 was read as a bug (`ARCHITECTURE_UPDATE.md` §2) because the total appeared with
    #: nothing beside it saying that the 6 is the six Part-17 stimuli, one model call each, not a
    #: repeat count. The number was always honest; it did not explain itself.
    breakdown: str = ""
    #: ``12`` for the gate. Stated separately because that is the figure a researcher decides
    #: against when choosing how many twins to test.
    per_unit: str = ""


class AgentCardView(_View):
    """One of the five agent cards. `docs/06` §3.1."""

    agent_id: str
    name: str
    description: str
    state: DotState = "pending"
    #: The latest operational line, e.g. ``Rendered 10 paragraphs, style v1``.
    latest: str = ""
    enabled: bool = True


class ResultsPanel(_View):
    """The Results side panel. `docs/06` §3.7's **mandatory seven-step order**.

    The order is the specification's and is a research property, not a layout choice: it is
    deliberately the same bundle the Analyst received, in the same order, so the researcher can
    read the input and the output together.

    ``analysis_is_fallback`` keeps the *Generated summary* prefix visible (`docs/02` §6.2). A
    template reading and a model's reading are different evidence and must not look alike.
    """

    #: 1 — the code and its Fairwork score, plus 2 — what the twins are told.
    board: DialBoard
    #: 3 — the five lever paragraphs **actually rendered**, never a re-render.
    scenario_text: list[str] = Field(default_factory=list)
    #: 4 — six shifts, the index, ``twins_n`` and the floor note.
    bars: MetricBars
    baselines: dict[str, float] = Field(default_factory=dict)
    #: 5 — including the legs that cannot be computed, each naming the code to run (I17).
    interactions: list[InteractionRow] = Field(default_factory=list)
    #: 6 — `runs.llm_analysis`.
    analysis: str | None = None
    analysis_is_fallback: bool = False
    #: 7 — session, panel hash, style version, prompt hash, model, timestamp, run id.
    metadata: list[StatusRow] = Field(default_factory=list)
    run_id: str | None = None
    #: ``sweep`` or ``studio``, and the ``n`` behind every number on the panel. §4.3 item 4 asks for
    #: an explicit badge naming n when the latest run is a Studio one, because the panel's shifts
    #: are then one twin's and the floor it is read against is the frozen panel's.
    origin: str = "sweep"
    twins_n: int = 0


class CachedAsk(_View):
    """The Dial board's answer for a code that already has a completed run.

    ``cached`` drives the amber badge and the **Rerun?** button (`docs/06` §3.2). A rerun creates
    a real session, visible in the Agents log, and **inherits the original panel** — a rerun with
    a different panel is not a rerun (I14).
    """

    version_code: str
    cached: bool = False
    run_id: str | None = None
    session_id: str | None = None
    bars: MetricBars | None = None


# --------------------------------------------------------------------- the generator, docs/06 §4

#: `docs/06` §4's three sentiment presets. A preset moves the respondent-level disposition that
#: every Likert draw is centred on; it is not a separate distribution.
SentimentPreset = Literal["frustrated", "mixed", "content"]

#: The five levers, in `docs/03`'s order. Repeated here rather than imported: `models/` may not
#: import `variant/`, and the odometer's order is frozen (I2).
GENERATOR_LEVERS: tuple[str, ...] = ("pay", "conditions", "contracts", "management", "voice")

#: The five cities the Form offers, in `docs/GOOGLE_FORM.md` Part 3 question 2's order and
#: **spelled as the Form spells them**. A generated `field:city` that is not one of these five is
#: a value live intake could never receive, so the two lists are the same list.
GENERATOR_CITIES: tuple[str, ...] = ("Mumbai", "Pune", "Delhi NCR", "Jaipur", "Bengaluru")

#: The three services, spelled as the Form spells them, for the same reason.
GENERATOR_SERVICES: tuple[str, ...] = (
    "Cab (Uber Go or Premier)", "Auto rickshaw", "Motorcycle",
)


class GeneratorSpec(_View):
    """Every knob `docs/06` §4's dashboard exposes, as one frozen object.

    Passed whole into :func:`twinlab.generator.synthetic.generate_batch`, so a batch's stored
    `config` records exactly what produced it. **The batch stays deterministic in
    ``(seed, spec)``**: nothing here introduces a draw that is not from the batch's own
    `random.Random`, and the fields are read in a fixed order.

    Defaults reproduce the pre-spec generator exactly, so a call that passes no spec draws the
    batch it always drew and M9's acceptance tests keep their meaning.
    """

    # ---- Batch (§4, left column, row 1)
    count: int = Field(default=50, ge=1, le=5000)
    name: str = "synthetic batch"
    #: Never defaulted by the UI. Two batches sharing a seed silently share respondents.
    seed: int = Field(ge=0)
    #: `docs/06` §4. A respondent who fails an attention check is dropped by screening and can
    #: never produce a twin, so a batch generated to exercise the quality gate wants this low.
    #: It is a control because exercising the *screening* switch needs it above zero.
    attention_fail_share: float = Field(default=0.03, ge=0.0, le=1.0)

    # ---- Where they drive (§4, left column, row 2). Relative weights, not proportions.
    city_weights: dict[str, float] = Field(
        default_factory=lambda: {city: 1.0 for city in GENERATOR_CITIES}
    )

    # ---- Who they are (§4, left column, row 3)
    service_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "Cab (Uber Go or Premier)": 2.0, "Auto rickshaw": 2.0, "Motorcycle": 1.0
        }
    )
    age_range: tuple[int, int] = (21, 55)
    #: **Months, not years.** The Form asks in years and the twin row speaks in months
    #: (`docs/DECISIONS.md`, 2026-09-22), but the dashboard asks in months because three months
    #: is the eligibility floor and "0.25 years" is not a quantity a researcher sets. The payload
    #: still answers the Form's years question; :func:`synthetic.years_from_months` is the one
    #: conversion and it round-trips exactly.
    tenure_months_range: tuple[int, int] = (3, 72)
    hours_per_week_range: tuple[int, int] = (30, 80)
    woman_share: float = Field(default=0.1, ge=0.0, le=1.0)
    #: `docs/06` §4's *use other apps too*: the share who take work from more than one platform.
    #: Drives `background:platform_count` **and** `background:other_apps` together — a driver on
    #: one app who names two others is a contradiction a real submission could not contain.
    multi_app_share: float = Field(default=0.4, ge=0.0, le=1.0)
    #: §4's *car or bike on a loan*: the share whose `background:vehicle_arrangement` is the
    #: loan option. The rest split between owning outright and renting from a fleet owner.
    vehicle_loan_share: float = Field(default=0.5, ge=0.0, le=1.0)
    #: §4's *need the money (1 to 7)*: the batch's mean on the `EDEP` block, on its own 1–7
    #: scale. EDEP is the moderator in `stats/spec.py`'s structural model, which is why it is a
    #: control of its own rather than one more construct slider.
    need_money: float = Field(default=5.0, ge=1.0, le=7.0)

    # ---- How they feel about the app (§4, right column, row 1)
    sentiment: SentimentPreset = "mixed"
    #: **Absolute targets on a common 1–7 scale**, keyed by construct code
    #: (`models/reference.CONSTRUCTS`), as §4's sliders read. A construct absent here takes the
    #: preset alone. A 5-point item is converted rather than clamped: the target is read as a
    #: position on the scale, so 5.5/7 on `agree7` and the same position on `agree5` mean the
    #: same thing about the respondent (`synthetic.centre_for_points`).
    construct_targets: dict[str, float] = Field(default_factory=dict)
    #: §4's *how much drivers differ*: the spread of the respondent-level disposition. Zero makes
    #: every respondent identical, which is occasionally what a machinery test wants.
    disposition_spread: float = Field(default=1.0, ge=0.0, le=2.0)
    #: §4's *shared overall mood*: how much of a respondent's answer comes from one disposition
    #: they carry across every construct, against a per-construct wobble. At 1.0 a respondent is
    #: uniformly sour or uniformly content; at 0.0 each construct is drawn independently and no
    #: correlation between constructs survives — which makes the batch useless for PLS-SEM, so
    #: the default sits high.
    shared_mood: float = Field(default=0.6, ge=0.0, le=1.0)
    #: §4's *answer noise*: standard deviation of each Likert draw, in scale points.
    likert_sd: float = Field(default=0.3, gt=0.0, le=3.0)

    # ---- How strongly they react to each change (§4, right column, row 2)
    #: §4's five reaction sliders, keyed by lever id. **0 means no reaction, 1 normal, 2 strong**,
    #: exactly as §4's caption states. They are what makes the two holdout blocks answer the
    #: *change* rather than repeating the baseline: `H2_*` (Part 16, the assigned arm's story) and
    #: `H3_V{1..6}_*` (Part 17, six real version codes) move by the levers each version raises,
    #: weighted by these. A batch with every reaction at zero produces holdouts identical to the
    #: baseline, which is the correct null and is occasionally what a machinery test wants.
    lever_reactions: dict[str, float] = Field(
        default_factory=lambda: {"L1": 2.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0}
    )
    #: §4's *drivers who need the money react more to a drivers' forum (captive voice)*. When on,
    #: a respondent high on `EDEP` reacts more strongly to the **representation** lever (`L5`)
    #: than one who does not need the money. This is the one interaction §4's dashboard carries,
    #: and it is the generator's, not a twin's: it shapes the synthetic *respondents*.
    captive_voice: bool = True

    # ---- Provenance knobs that were in the config file and never read (see the service note)
    mc_correct_rate: float = Field(default=0.8, ge=0.0, le=1.0)
    completion_seconds_range: tuple[int, int] = (520, 1800)

    def weighted(self, which: Literal["city", "service"]) -> dict[str, float]:
        """The weights, refusing an all-zero set rather than dividing by zero."""
        weights = self.city_weights if which == "city" else self.service_weights
        if not weights or sum(weights.values()) <= 0:
            raise ValueError(
                f"{which} weights must contain at least one positive value; a batch with no "
                f"{which} to draw from is not a batch (docs/06 §4)."
            )
        return {k: v for k, v in sorted(weights.items()) if v > 0}

    def reaction(self, lever: str) -> float:
        """One lever's reaction weight. An unknown lever raises rather than defaulting to 1.

        `CLAUDE.md` rule 7 — a lever the dashboard forgot to bind must not be silently treated as
        "normal", because a whole holdout block would then move for a reason nothing recorded.
        """
        try:
            return self.lever_reactions[lever]
        except KeyError:
            raise KeyError(
                f"no reaction weight for lever {lever!r}; all five are required "
                f"(docs/06 §4). Have: {sorted(self.lever_reactions)}"
            ) from None


class GeneratorPreview(_View):
    """One previewed respondent. `docs/06` §4's *Preview 3 drivers* — derives, inserts nothing."""

    response_id: str
    city: str
    service: str
    arm: str
    age: str
    gender: str
    hours_per_week: str
    #: Months, as the dashboard and the twin row speak. Derived from the payload's years answer.
    tenure_months: str
    #: Formatted in the service layer, never computed in a handler (`docs/05` §8.4 rule 5).
    mean_answer: str
    items_answered: int


class TwinImportResult(_View):
    """What `docs/06` §3.8's *Import twins from the survey* did. Its three counts, and the reasons.

    §3.8 asks for "imported / skipped / invalid counts". ``reasons`` carries a named reason per
    invalid row because a count on its own tells the researcher that something failed and nothing
    about what — and a silent skip is the failure mode `CLAUDE.md` rule 7 exists to prevent. It is
    capped, because on a 500-row batch the full list is the batch.
    """

    scope: str
    #: Respondents that became twins in this run.
    imported: int
    #: In scope, but not a candidate: already a twin, or gated out by consent/eligibility/outcome.
    skipped: int
    #: Candidates whose persona could not be built. **Never counted as imported.**
    invalid: int
    reasons: list[str] = Field(default_factory=list)
    #: Still importable after this run. Zero means the scope is exhausted, not that it failed.
    remaining: int = 0


class GeneratorCounts(_View):
    """`docs/06` §4's status line: `In the database now: X real and Y synthetic surveys.`"""

    real: int
    synthetic: int
    line: str


class StudioMetricRow(_View):
    """One row of `docs/06` §5's *What the twin said* table.

    *What it measures · Now (1–7) · Uber today · Change · The twin's reason.* ``now`` and
    ``change`` are ``None`` when the 37 survey questions were not asked, and the column renders
    *Not tested* rather than a zero: an absent measurement and a measured null are different
    claims (I17).
    """

    metric: str
    label: str
    #: The twin's score under the change.
    now: float | None = None
    #: The twin's own driver's score, which is what "Uber today" means for this twin.
    baseline: float | None = None
    change: float | None = None
    reason: str = ""


class StudioResult(_View):
    """One Twin Studio run, as the screen renders it. **Never evidence** (`docs/01` §6.9).

    ``blocked`` is the one field that is not decoration. A dialled version whose Checker report
    fails must not reach a twin (I3), so the Studio refuses and says which gate failed — rather
    than asking anyway because it is "only a sandbox". The quarantine is about where the answer is
    *filed*, not about whether the stimulus was verified.
    """

    twin_id: str
    version_code: str | None = None
    model: str
    sandbox: bool = False
    label: str = ""
    scenario_text: list[str] = Field(default_factory=list)
    rows: list[StudioMetricRow] = Field(default_factory=list)
    replies: dict[str, str] = Field(default_factory=dict)
    rationale: str = ""
    #: Why nothing was asked. Empty when the run happened.
    blocked: str = ""
    #: Set when the researcher did not tick *Also ask the 37 survey questions*.
    no_battery_note: str = ""

    # --- Filed as a result, or not. `ARCHITECTURE_UPDATE.md` §1.1 and §4.3. ---
    #
    # A dialled version with a complete answer vector is now ALSO written to `runs` and
    # `twin_answers` with ``origin='studio'``, so it reaches Results and the index. These four
    # fields are how the screen says so, and in particular how it says **n = 1**: a Studio-origin
    # index is computed over one twin, while `00000` and `SHAM` come from the frozen panel, so the
    # two are not the same quantity and must never look alike.
    run_id: str | None = None
    origin: str = ""
    twins_n: int | None = None
    index_value: float | None = None
    #: Why this ask did **not** become a result, when it did not. A custom change is quarantined by
    #: design and carries :data:`~twinlab.services.studio.SANDBOX_LABEL` instead.
    not_filed: str = ""
