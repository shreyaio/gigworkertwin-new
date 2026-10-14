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

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


#: What the *Twin today* column means when it is empty. M19 WP-10.
#:
#: `00000` runs **once per session**, by the orchestrator, before the sweep
#: (`loop.CONTROL_CELLS`) — it is refused from the Dial board by design. So with no session ever
#: run the column is empty for every twin in every row, and nothing on screen distinguished "not
#: yet measured" from "the twin declined to answer". Both rendered as a dash, and one of those is
#: a bug while the other is the expected state of a fresh database.
BASELINE_MEASURED = "measured"
BASELINE_NOT_MEASURED = "not measured"

#: The *Twin today* column header, naming the cell its numbers come from. Declared here rather
#: than built in `ui/components/domain.py` because `ui/` may import only `services/` and
#: `models/` (`ARCHITECTURE.md` §4) and `CONTROL_CODE` lives in `orchestrator/`. The literal is
#: pinned against that constant by a test, so the two cannot drift.
BASELINE_COLUMN_HEADER = "Twin today (00000)"

#: The sentence the panel shows above the table when the baseline has not been measured. It
#: appears **once**, rather than as a column of dashes: a dash can be read as a zero, and I17
#: forbids rendering an unmeasured cell as anything that could be.
BASELINE_NOT_MEASURED_NOTE = (
    "Twin today has not been measured for this twin. It is the twin's answers to the 00000 "
    "control cell — what it says when shown no change — which the orchestrator runs "
    "once at the start of every session. No session has produced it yet, so the column is empty "
    "rather than zero."
)


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
    #: :data:`BASELINE_MEASURED` or :data:`BASELINE_NOT_MEASURED`. WP-10: *not yet measured* and
    #: *the twin declined* must be distinguishable, and neither may be rendered as a number.
    baseline_state: str = BASELINE_NOT_MEASURED


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
    #: How many twins exist at all, so the empty state can say *"0 of 50 twins have a stored
    #: quality run"* rather than only *"nothing here"*. M19 WP-7: the tab's empty state used to
    #: instruct the researcher to press a disabled button, saying nothing about where the numbers
    #: come from.
    twins_total: int = 0
    #: Which H3 presentation produced these rows, from `twin_quality_runs.detail["protocol"]`.
    #: More than one value means the table is **mixing measurements** and they cannot be pooled
    #: (M19 WP-3): six-in-one-context and six-in-isolation are different protocols. Empty when
    #: nothing has been run; `"unrecorded"` for rows written before the field existed.
    h3_protocols: list[str] = Field(default_factory=list)


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

    ``version_code`` is the stimulus the test ran against — ``None`` for tests 1 and 3, which use
    none (`docs/DECISIONS.md`, 2026-10-07, `006_validity_version_code.sql`). A row from before that
    migration has no value to show here either, which is also ``None`` — "not recorded" and "no
    version applies" are the same blank on screen, and neither is guessed.
    """

    when: str
    test: str
    twins_n: int
    model: str
    result: str
    verdict: Literal["PASS", "FAIL", "CHECK", "INCONCLUSIVE"]
    version_code: str | None = None


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
    #: **The deterministic half of this agent's work**, when it has one. M19 WP-8 item 6.
    #:
    #: The researcher's instinct that the Policy Designer "doesn't really need a live AI model" is
    #: half right, and that half is already deterministic: selecting the commitment set is
    #: `variant/lookup.py`, a pure frozen lookup over `dial_lookup.json` and `gaps.json` that
    #: consults no model (I1). Only turning that set into Uber-voice prose uses one. The card
    #: showed the two as a single step, so the model-free half was invisible and the agent looked
    #: more discretionary than it is.
    #:
    #: Presentation only — it makes an existing structural fact visible and changes no behaviour.
    deterministic_step: str = ""
    #: The step that does cost a model call, and how many.
    model_step: str = ""
    #: True when this agent's `enabled` switch may not be turned off, with the reason below.
    #: The Checker's probe is what enforces I3, so disabling it is refused outright (WP-8 item 4).
    undisableable: bool = False
    undisableable_reason: str = ""
    #: `agent_configs.version` actually in force, or ``None`` when the YAML seed is running.
    live_version: int | None = None


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
    #: How far, in 1–7 scale points, a respondent at the extreme of the disposition sits from
    #: their construct's batch mean. **The ceiling on how distinguishable two respondents are**,
    #: and until `v6` a hard-coded `1.5` inside `_respondent_targets`.
    #:
    #: At `1.5`, with the default spread and shared mood, a construct target has a between-driver
    #: SD of about 0.62 points — so the expected gap between two random respondents' answers is
    #: ~0.70, and after `centre_for_points` compresses it, four respondents in five give the
    #: *same* integer on a 5-point item. The whole panel then renders near-identical persona
    #: clauses, and a wrong-person comparison asking for a half-point gap (`docs/08` §4 test 1) is
    #: being asked for most of a ceiling that an oracle twin could not clear.
    #:
    #: `2.4` puts the between-driver SD near 1.0 on 1–7, which is what these instruments show in
    #: published samples, with only mild clipping at the ends. Raising `likert_sd` would widen
    #: the panel too, but as noise uncorrelated with the construct — apparent individuality
    #: bought by destroying the construct reliability the PLS-SEM needs. Between-driver signal is
    #: raised here; within-driver noise stays where it is.
    between_driver_swing: float = Field(default=2.4, ge=0.0, le=4.0)
    #: The share of respondents who have a support or deactivation story at all, which is what
    #: `OWN3` narrates. A *structural* difference between respondents rather than a difference in
    #: wording: some drivers have been blocked and some have not, and that distinguishes two
    #: passages far more than paraphrase variety does.
    incident_share: float = Field(default=0.35, ge=0.0, le=1.0)

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
    #: **Which construct each lever moves, and by how much per dial step**, in 1–7 scale points.
    #: Signed: more protection raises fairness and lowers the wish to leave, and the sign lives
    #: here rather than being applied from `index_sign` by the caller — one scalar cannot carry
    #: both directions, which is exactly what the pre-`v5` generator tried to do.
    #:
    #: Ported from the Apps Script prototype's `GEN_LEVER` (`docs/AUDIT_PROTOTYPE_PARITY.md` §A6).
    #: Without it every lever moved every construct by the same amount, so a pay rise moved
    #: *clarity* as much as it moved *happiness* and no estimate on synthetic data corresponded to
    #: anything. A lever absent from a construct's row genuinely does not move it: conditions (L2)
    #: has no path to clarity, and that zero is a claim, not an omission.
    lever_effects: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "L1": {"SATI": 0.5, "LOYA": 0.4, "EXIT": -0.4, "FAIR": 0.1},
            "L2": {"SATI": 0.4, "LOYA": 0.2, "EXIT": -0.3},
            "L3": {"TRAN": 0.6, "FAIR": 0.2, "CTRL": -0.2},
            "L4": {"FAIR": 0.7, "VOIC": -0.4, "CTRL": -0.2, "SATI": 0.2},
            "L5": {"VOIC": -0.5, "LOYA": 0.2, "FAIR": 0.1},
        }
    )
    #: What a **second** dial step adds, as a multiple of the first. The prototype's `1.6`:
    #: diminishing returns, because going from a minimum wage to a living wage is a smaller change
    #: than going from nothing to a minimum wage. `2.0` would make the dials linear.
    second_step_factor: float = Field(default=1.6, ge=1.0, le=2.0)
    #: **The two lever interactions**, as one magnitude — the prototype's `together`.
    #:
    #: Applied as `-synergy` to pushback when L4 and L5 are both raised (an appeals route and a
    #: forum compound: somewhere to take a complaint plus a body to take it to), and `-synergy/2`
    #: to staying when L1 and L2 are both raised (pay and safety substitute, so together they add
    #: less than the sum).
    #:
    #: This is what makes a synthetic batch able to exhibit **sub-additivity** — `docs/07` §5's
    #: headline claim. At `0.0` every interaction is exactly additive by construction, which is
    #: what the generator produced before `v5` and which left `analysis/interactions.py` with no
    #: fixture that could test it against a known truth.
    lever_synergy: float = Field(default=0.3, ge=0.0, le=1.0)
    #: §4's *drivers who need the money react more to a drivers' forum (captive voice)*. When on,
    #: a respondent high on `EDEP` reacts more strongly to the **representation** lever (`L5`)
    #: than one who does not need the money. This is the one interaction §4's dashboard carries,
    #: and it is the generator's, not a twin's: it shapes the synthetic *respondents*.
    captive_voice: bool = True

    #: **The overall gain on `lever_effects`**, calibrated against real Part 17 responses rather
    #: than typed. `v8`, 2026-10-13.
    #:
    #: `lever_effects` says which construct each lever moves and in what proportion; this says how
    #: far the whole matrix moves a respondent. The two are separate claims and only this one has
    #: an external check: a real respondent's own Part 17 answers say how much a described change
    #: moved *them*, and `generator.synthetic.calibrate_reaction_gain` fits this single parameter
    #: to them by least squares.
    #:
    #: At the inherited `1.0` the matrix **could not reproduce the one real respondent in the
    #: database** — it predicted their 18 Part 17 answers at MAE 1.504, which is to say the
    #: generator would have failed its own quality gate against a real driver. The fitted value is
    #: `2.11` (MAE 0.864 on the same items), corroborated with no method confound by the H2 block,
    #: where that driver moved 0.375 scale points per mirrored item against the matrix's predicted
    #: 0.112. See `docs/DECISIONS.md`, 2026-10-13.
    #:
    #: **Re-derived at `v11` to `2.40`**, jointly with
    #: :attr:`holdout_version_differentiation`, by `calibrate_reaction_model`. The two are
    #: coupled through
    #: the fit — shrinking the spread between packages changes which level best explains the same
    #: eighteen answers — and the joint fit halves the error on them, 0.863 to **0.392**. Same
    #: respondent, same answers, one more parameter; `2.11` remains the correct one-parameter fit
    #: and `calibrate_reaction_gain` still returns it.
    #:
    #: **Provisional at n=1.** One respondent fixes the direction and the rough gain and is not a
    #: calibration sample. Re-derive with `calibrate_reaction_gain` as real responses arrive; the
    #: value is carried on every batch's config row so a stored batch always says which gain drew
    #: it. Fitted to **survey answers, never to twin output** — fitting it until twins pass is the
    #: circularity `docs/08` §2.4 forbids.
    reaction_gain: float = Field(default=2.40, ge=0.0, le=8.0)
    #: **How much respondents differ in how far a change moves them.** `v8`.
    #:
    #: Before this, the reaction was a *batch constant*: across the whole range of `EDEP` — the
    #: only respondent-level input the shift had — the fairness shift varied by at most 0.16 scale
    #: points and by exactly 0.00 on four of the six Part 17 versions. Every respondent reacted
    #: identically, and **nothing in any persona said how reactive that respondent was**, so a
    #: twin was being asked for a quantity it had never been given. No twin could pass the H3 gate
    #: except by guessing a hidden batch constant.
    #:
    #: A respondent's own reactivity is now drawn here and **spoken in their persona**, through
    #: `generator.voice`'s `react:*` clauses, so a careful twin can read it the way it already
    #: reads their baseline attitudes. The draw is centred on `1.0`, so this widens the panel
    #: without moving the batch's mean reaction — the gain above is the only thing that sets level.
    reactivity_spread: float = Field(default=0.5, ge=0.0, le=0.9)
    #: **How much respondents differ in WHICH lever matters to them.** `v10`, 2026-10-13.
    #:
    #: :attr:`lever_reactions` is the batch's mean salience per lever and it carried
    #: ``{L1: 2.0, L2..L5: 1.0}`` — **pay double-weighted for every respondent, disclosed in no
    #: persona.** That is the same defect class as :attr:`reaction_gain` before it was calibrated
    #: and as :attr:`reactivity_spread` before the reaction was drawn per respondent: a hidden
    #: batch constant a twin cannot infer except by guessing which lever this population happens
    #: to weight most. It is what left `r(driver version means, twin version means)` at +0.07
    #: across three stages while every other targeted metric moved: the twin differentiated the
    #: six versions and ranked them wrong, putting `02211` — which raises no pay at all — second
    #: where the driver put it fifth (`docs/DECISIONS.md`, 2026-10-13).
    #:
    #: Each respondent now draws their own weight per lever and **says which one matters most**,
    #: through `generator.voice`'s `salience:*` clauses. The draw is **multiplicative and centred
    #: on `lever_reactions`**, so this adds between-driver variance without moving the batch's
    #: mean salience on any lever: the population is not re-weighted, the claim is only that
    #: drivers differ. Multiplicative rather than additive for two further reasons — a lever whose
    #: slider is at `0.0` stays at `0.0` for every respondent (a no-reaction batch is `docs/06`
    #: §4's null and must stay null), and no weight can go negative, which would invert a lever's
    #: sign for one respondent.
    #:
    #: **Not calibrated, and not calibratable yet.** Five lever weights plus a gain is six
    #: parameters against one respondent's eighteen Part 17 answers, which is underdetermined, so
    #: the route that fixed the gain is unavailable here. This spreads the inherited means rather
    #: than re-tuning them; re-tuning them against a twin pass rate is the circularity
    #: `docs/08` §2.4 forbids.
    salience_spread: float = Field(default=0.5, ge=0.0, le=0.9)
    #: **How much a driver's reaction depends on WHICH package is announced, as against how
    #: much on being shown a package at all.** `v11`, 2026-10-13. Calibrated, not typed.
    #:
    #: `1.0` is the inherited generator: the shift is the lever matrix, so two version codes that
    #: raise different levers move a driver by very different amounts. `0.0` is the other
    #: extreme: any code that raises at least one lever moves them by the same amount, and which
    #: levers it raised makes no difference. `00000` moves nobody at either end — being shown
    #: nothing is nothing, and that zero is an invariant, not a limit of the shrinkage.
    #:
    #: **Why this parameter exists.** The one real respondent on record answered Part 17's six
    #: version codes with a range of **exactly one scale point** on every question — two distinct
    #: response patterns across six described worlds. They moved a long way from their own
    #: baseline (2.47 points, which is what `reaction_gain` fitted) and moved **almost the same
    #: distance whatever the package was**. The inherited generator spread its synthetic drivers
    #: across the six codes four times as widely (0.66 against 0.17), so a twin was being scored
    #: on a discrimination the only real driver on record does not make
    #: (`docs/DECISIONS.md`, 2026-10-13 diagnosis).
    #:
    #: Shrinkage is toward the **mean shift over the 242 codes that raise something**, which is a
    #: property of the spec and not of whichever code is being asked about, so the parameter means
    #: the same thing for Part 16's arms, Part 17's six and the sweep's 243. The mean is preserved
    #: exactly at every value of this parameter, so it is close to orthogonal to
    #: :attr:`reaction_gain`: the level a driver moves to stays calibrated, and only the spread
    #: between packages changes. A respondent's own :attr:`reactivity_spread` draw is inside the
    #: mean, so **person-discrimination is untouched** — it is only version-discrimination that
    #: shrinks.
    #:
    #: **Fitted to survey answers, never to twin output.** `calibrate_reaction_model` fits it with
    #: the gain by least squares against real Part 17 responses, the same standing
    #: `reaction_gain` has. **Provisional at n=1** — one respondent fixes the direction and the
    #: rough size, not the second decimal. Re-derive as real responses arrive.
    #:
    #: **Read the consequence before changing it.** This parameter also flattens the sweep: at a
    #: low value the 243 cells differ mainly in how much they announce rather than in what they
    #: announce, and the between-cell variation is the study's dependent variable. If real drivers
    #: genuinely do not discriminate between packages, that is a finding about the population and
    #: not a knob; if they do, this number is wrong and more respondents will say so.
    holdout_version_differentiation: float = Field(default=0.18, ge=0.0, le=1.0)
    #: **How strongly a respondent avoids the two ends of a scale.** `v12`, 2026-10-14.
    #:
    #: `0.0` is the inherited generator: `_likert` **clamps** a rounded normal draw to the scale,
    #: so every respondent whose latent position sits past an end answers `1` or `7` and the ends
    #: carry a pile-up the clamp created. `1.0` is a respondent who never uses either end.
    #:
    #: **Extreme-response avoidance is a documented property of Likert data**, not an inference
    #: from any twin's answers: respondents systematically under-use the outermost options, which
    #: is why published samples on seven-point scales show far less endpoint use than a normal
    #: draw would predict. The one real respondent on record used an endpoint **0 times in 39
    #: seven-point answers** — 21 battery and 18 Part 17 — while the synthetic batch drawn
    #: alongside them used one 14–19% of the time. That is the generator asserting a response
    #: style no human in the data exhibits.
    #:
    #: A property of the **person**, so it applies to every Likert answer they give — battery and
    #: both holdout blocks alike. Narrowing it to one block would be claiming that someone avoids
    #: the ends when describing today and stops avoiding them when imagining a change.
    #:
    #: **Fitted to human answers, never to twin output.** Chosen as the smallest value that brings
    #: endpoint use inside what the real respondent's 39 answers support, which is the same
    #: standing `reaction_gain` and `holdout_version_differentiation` have. A value picked by
    #: watching the twin pass rate would be `docs/08` §2.4's circularity and would make every path
    #: estimated on synthetic data an artefact of what the model can do.
    endpoint_avoidance: float = Field(default=0.70, ge=0.0, le=1.0)

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

    def effects(self, lever: str) -> dict[str, float]:
        """One lever's construct effects. An unknown lever raises, as :meth:`reaction` does.

        Rule 7, for the same reason: a lever with no row would silently move nothing, and a lever
        that moves nothing is indistinguishable in the output from a lever whose reaction slider
        was set to zero on purpose.
        """
        try:
            return self.lever_effects[lever]
        except KeyError:
            raise KeyError(
                f"no construct effects for lever {lever!r}; all five are required "
                f"(docs/06 §4). Have: {sorted(self.lever_effects)}"
            ) from None

    @model_validator(mode="after")
    def _check_lever_effects(self) -> GeneratorSpec:
        """Every lever has a row, and every row names real constructs. Rule 7.

        Validated here rather than at the call site so a spec that could not produce a coherent
        batch cannot be constructed at all — a misspelt construct key would otherwise sit in the
        matrix contributing nothing, and the batch would look fine.
        """
        from twinlab.models.reference import CONSTRUCTS, LEVERS

        known = {c.code for c in CONSTRUCTS}
        missing = [lever for lever in LEVERS if lever not in self.lever_effects]
        if missing:
            raise ValueError(
                f"lever_effects is missing {missing}; all five levers need a row, even an empty "
                f"one (docs/06 §4). A lever with no row moves nothing, which is indistinguishable "
                f"from a reaction slider set to zero."
            )
        for lever, row in self.lever_effects.items():
            if lever not in LEVERS:
                raise ValueError(
                    f"lever_effects names {lever!r}, which is not one of the five levers "
                    f"{list(LEVERS)} (I2's frozen order)"
                )
            unknown = sorted(set(row) - known)
            if unknown:
                raise ValueError(
                    f"lever_effects[{lever!r}] names {unknown}, which are not constructs. "
                    f"Have: {sorted(known)}. A misspelt key would contribute nothing and the "
                    f"batch would look correct."
                )
        return self


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


class ReactionGainFit(_View):
    """What `GeneratorSpec.reaction_gain` was fitted to. `v8`, 2026-10-13.

    The provenance of the one number in the generator that has an external check. Returned by
    `generator.synthetic.calibrate_reaction_gain` so a researcher can see the fit rather than
    inherit a constant, and so the value can be **re-derived** as real Part 17 responses arrive
    instead of being carried forward on faith.

    Read it with ``respondents_n`` in view. At n=1 the fit establishes that today's gain is wrong
    and roughly by how much; it does not establish the gain to two decimal places. Nothing here
    is fitted to a twin's answers — the inputs are real survey responses only.
    """

    #: The least-squares gain over the respondents supplied.
    gain: float
    #: How many real respondents the fit rests on. **The number to read first.**
    respondents_n: int
    #: Part 17 items actually scored, across those respondents.
    items_n: int
    #: Mean absolute error of the generator's predicted Part 17 answers **at** :attr:`gain`.
    mae_at_gain: float
    #: The same, at a gain of 1.0 — the inherited matrix, for comparison.
    mae_at_unit_gain: float
    #: Already formatted, so no handler recomputes it (`docs/05` §8.4 rule 5).
    headline: str


class ReactionModelFit(_View):
    """What `reaction_gain` **and** `holdout_version_differentiation` were jointly fitted to. `v11`.

    `ReactionGainFit` fits one parameter: how far a described change moves a driver. It cannot
    see the defect the 2026-10-13 diagnosis found, because a gain that matches the *average*
    movement can still spread the six Part 17 versions four times too widely — the level is right
    and the shape is not. This fits both at once.

    The two are nearly orthogonal by construction: the shrinkage preserves the mean shift over
    the code space exactly, so the gain still sets the level and this only sets the spread. Read
    with ``respondents_n`` in view, and nothing here is fitted to a twin's answers.
    """

    #: The least-squares gain, at the fitted differentiation.
    gain: float
    #: The least-squares version differentiation, in ``[0, 1]``.
    holdout_version_differentiation: float
    #: How many real respondents the fit rests on. **The number to read first.**
    respondents_n: int
    #: Part 17 items actually scored, across those respondents.
    items_n: int
    #: Mean absolute error at the fitted pair.
    mae_at_fit: float
    #: The same at the inherited model — the fitted gain with differentiation held at 1.0 — so
    #: the two readings differ in one parameter and the comparison is attributable.
    mae_at_full_differentiation: float
    #: The respondents' own spread across the six Part 17 version codes, and the generator's at
    #: the fit. The pair this parameter exists to reconcile.
    observed_version_spread: float
    fitted_version_spread: float
    #: Already formatted, so no handler recomputes it (`docs/05` §8.4 rule 5).
    headline: str


class GeneratorClipping(_View):
    """One construct's pile-up against the end of the scale, for the pre-flight note. `v7`.

    `docs/06` §4's *how much drivers differ* and the `between_driver_swing` dial both widen the
    spread of construct targets, and the spread is then **clamped** to the 1–7 scale. The clamp is
    right and it is silent, so a slider near an end converts the extra width into respondents who
    are *identical at the wall* — the panel's dial says individual and the batch is not. A
    wrong-person test on such a batch has no ceiling to reach (`docs/08` §4 test 1), and until `v7`
    the only way to find that out was to spend the twin calls.

    A diagnostic, never a correction: nothing in the generator reads this, and a high share may be
    exactly the batch the researcher wants.
    """

    construct_code: str
    #: The construct's own words from `docs/06` §4's slider, so the note names what the researcher
    #: set rather than a four-letter code they have to look up.
    label: str
    #: Share of the batch landing on 1.0 or 7.0, already formatted (`docs/05` §8.4 rule 5).
    share: str
    #: Sorting key, kept separate from the formatted share so the UI does not re-parse it.
    share_value: float


class GeneratorSalience(_View):
    """One lever's share of a batch as **the change that matters most**, for the pre-flight. `v10`.

    `lever_reactions` is the batch's *mean* salience per lever and `salience_spread` spreads it
    per respondent, centred, so the mean on every lever is unchanged — the condition that keeps
    Route A from being a re-weighting of the population fitted to a twin pass rate
    (`docs/08` §2.4). The consequence a researcher has to see is that spreading a `2.0` mean
    against four `1.0` means still leaves most of the batch weighting pay highest: 84% of it at
    the default spread. Every persona now *states* that weighting, which is the defect `v10`
    repairs, but the batch does not thereby contain drivers who want different things.

    A diagnostic, never a correction: nothing in the generator reads this, and a pay-dominated
    batch may be exactly the population the researcher means to model. Flattening
    `lever_reactions` is theirs to decide.
    """

    lever: str
    #: `docs/06` §4's own label for the lever, so the note names the change rather than `L3`.
    label: str
    #: What this lever's share of the batch weights it highest, already formatted
    #: (`docs/05` §8.4 rule 5).
    share: str
    #: Sorting key, kept separate from the formatted share so the UI does not re-parse it.
    share_value: float


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
    #: In scope, but not a candidate — ``already_twins + gated``. Kept as the §3.8 count, but it
    #: is never reported on its own: the two halves are opposite outcomes and conflating them is
    #: what made the screen tell a researcher with a perfectly good twin that "nothing was
    #: eligible".
    skipped: int
    #: Already imported, so there is nothing to do. The **expected** outcome for anyone who filled
    #: in the hosted questionnaire, which builds the twin at submit time.
    already_twins: int = 0
    #: Refused by :func:`~twinlab.services.hosted_survey.twin_gate` — not eligible, consent
    #: withheld, or a battery too short to build a lossless persona (I6).
    gated: int = 0
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
