"""The hosted questionnaire's shapes. `docs/06` §2.1.

These describe the **driver-facing instrument as a page can render it** — stops, blocks,
questions, options, anchors. They are presentation structure over content that is already frozen
elsewhere, and they deliberately own none of it:

* the 73 scored items, their scales and their anchors come from `data/reference/instrument.json`;
* every question's destination comes from `config/form_map.yaml`;
* what a submission becomes comes from `ingest.survey_intake.build_rows`.

So a :class:`Question` carries no truth of its own. Its ``key`` is a `form_map.yaml` key and
nothing else, which is what makes the hosted page a **third client of the one intake contract**
rather than a parallel pipeline: it emits the same ``section|title`` pairs the Apps Script emits,
over the same map, into the same rows.

`CLAUDE.md` rule 13 — every Pydantic model in the project is declared under `src/twinlab/models/`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: How a question is answered. The kind decides the control the page draws **and** the shape of
#: the value that reaches the payload, so the two can never disagree.
QuestionKind = Literal[
    "yes_no",      # a two-option radio. Value: "Yes" / "No".
    "consent",     # one tick-box that must be ticked. Value: "I agree".
    "choice",      # a radio over a fixed option list. Value: the option label, verbatim.
    "likert",      # 1..points, drawn as a numbered row. Value: the integer.
    "integer",     # a short numeric answer. Value: the integer.
    "decimal",     # a short numeric answer that may be fractional. Value: the number.
    "short_text",  # one line in the driver's own words. Value: the text, verbatim.
    "long_text",   # a paragraph in the driver's own words. Value: the text, verbatim.
]


class Question(BaseModel):
    """One question, as the page draws it and as the payload carries it.

    ``key`` is ``"<section>|<title>"`` — a `config/form_map.yaml` key, exactly. The instrument
    builder refuses to construct a :class:`HostedInstrument` holding a key the map does not have,
    and refuses to leave a map key unrendered (`CLAUDE.md` rule 7: nothing is silently skipped).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    section: str
    title: str
    kind: QuestionKind
    #: What `form_map.yaml` says this becomes — "AMQ1", "field:city", "why:WHY_CONTROL".
    #: Carried for display and for the bijection test; nothing here interprets it.
    target: str
    #: Radio options, verbatim and in the order the driver sees them. `choice` only.
    options: tuple[str, ...] = ()
    #: `likert` only — the register's scale id, its number of points and its end labels. Read from
    #: `instrument.json`, never written down here, so a 5-point construct cannot be drawn with
    #: seven boxes (the defect `models/twin.py` records from the prototype).
    scale_id: str | None = None
    points: int | None = None
    low_anchor: str = ""
    high_anchor: str = ""
    #: A screener or a consent statement. Everything else may be skipped — the cover sheet
    #: promises exactly that, so the page has to honour it (`docs/06` §2.1).
    required: bool = False
    #: What the driver reads, when that differs from ``title``. Empty means they are the same.
    #:
    #: They differ for exactly one thing: the why-probes. Their wording is identical across every
    #: item by design, so the *map key* has to carry the item's stem to stay unique — five AMQ
    #: probes keyed "Why did you choose that?" would be one key and four lost answers. The driver
    #: is shown the constant wording, which is what the instrument specifies.
    prompt: str = ""
    #: Shown under the control. Never the question: a question lives in ``title``.
    help_text: str = ""
    placeholder: str = ""
    #: `integer` / `decimal` only. "In years", "In hours" — the Form's own words.
    unit: str = ""
    #: The battery item this optional why-box is attached to, for a `why:` question. The persona
    #: builder stores it as that item's `why_text`, verbatim (`docs/03` §7.1).
    why_for_item: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Question:
        if self.kind == "likert" and (self.points is None or self.scale_id is None):
            raise ValueError(f"{self.key}: a likert question needs a scale_id and points")
        if self.kind == "choice" and not self.options:
            raise ValueError(f"{self.key}: a choice question with no options cannot be answered")
        if self.kind != "choice" and self.options:
            raise ValueError(f"{self.key}: options are only meaningful on a choice question")
        return self

    @property
    def key(self) -> str:
        """The `form_map.yaml` key. The only identity this object has."""
        return f"{self.section}|{self.title}"

    @property
    def shown(self) -> str:
        """The wording the driver reads. ``prompt`` when it differs from the map key's title."""
        return self.prompt or self.title

    @property
    def is_why(self) -> bool:
        return self.why_for_item is not None


class Block(BaseModel):
    """A run of questions under one heading, with the scale note that governs them.

    A block exists because the anchors are stated **once above the items they govern**, which is
    how the instrument reads on paper and on the reference screens. Repeating "1 = Strongly
    disagree" under all eleven PAC items would be a different instrument to answer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: The `form_map.yaml` section these questions belong to. One block, one section.
    section: str
    heading: str = ""
    intro: str = ""
    #: "1 = Strongly disagree / 7 = Strongly agree", or empty for a non-Likert block.
    scale_note: str = ""
    #: This block carries the Part 15/16 experimental stimulus, which differs by arm and so is not
    #: known when the page is built — the arm is drawn once the driver has answered the city and
    #: service that stratify it. The renderer leaves a slot and fills it per session.
    arm_story: bool = False
    questions: tuple[Question, ...] = ()


class Stop(BaseModel):
    """One screen of the questionnaire. Nine of them, `docs/06` §2.1.

    ``kicker`` is the word on the progress rail — *Start*, *Check*, *Consent*, *Ratings*. ``part``
    is the "Part 4" line above the title. They are different things and the reference screens show
    both, so neither is derived from the other.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    kicker: str
    part: str = ""
    title: str = ""
    intro: str = ""
    blocks: tuple[Block, ...] = ()
    #: Free-standing prose shown before the blocks — the cover sheet, a scenario to imagine.
    body: tuple[str, ...] = ()
    #: A boxed aside, as "Before you start" is on the cover sheet.
    callout_title: str = ""
    callout_points: tuple[str, ...] = ()

    @property
    def questions(self) -> tuple[Question, ...]:
        return tuple(q for block in self.blocks for q in block.questions)


class HostedInstrument(BaseModel):
    """The whole questionnaire, in the order a driver answers it.

    Built once by `twinlab.survey.instrument.hosted_instrument` and validated there against
    `form_map.yaml`. Holding it as a model rather than a module-level dict is what lets the
    bijection be asserted on an object in a test instead of on an import side effect.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_version: str
    form_map_version: str
    stops: tuple[Stop, ...]

    @property
    def questions(self) -> tuple[Question, ...]:
        return tuple(q for stop in self.stops for q in stop.questions)

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(q.key for q in self.questions)

    def stop(self, index: int) -> Stop:
        for stop in self.stops:
            if stop.index == index:
                return stop
        raise KeyError(f"no stop {index}; this instrument has {len(self.stops)}")

    @model_validator(mode="after")
    def _no_duplicate_keys(self) -> HostedInstrument:
        seen: set[str] = set()
        for question in self.questions:
            if question.key in seen:
                # Two controls writing one map key means one of them is silently discarded at
                # intake, and which one depends on iteration order. Rule 7.
                raise ValueError(
                    f"{question.key!r} is drawn twice; one answer would overwrite the other"
                )
            seen.add(question.key)
        return self


class SurveyProgress(BaseModel):
    """One driver's partly-filled questionnaire, as the page carries it between stops.

    Lives in Gradio session state, never on disk and never in a table until the driver sends it.
    ``answers`` is keyed by `form_map.yaml` key, so the thing the page accumulates is already the
    thing the payload needs — there is no second shape to keep in step.
    """

    model_config = ConfigDict(extra="forbid")

    response_id: str
    started_at: str
    answers: dict[str, Any] = Field(default_factory=dict)
    stop_index: int = 1
    #: The four-arm assignment (`docs/01` §5). Drawn once, balanced within this driver's
    #: `city|service` stratum, as soon as they have answered both — and **never redrawn**, because
    #: the arm decides which story they are shown and a second draw would mean the story they read
    #: and the arm stored against their answers could disagree.
    arm: str | None = None
    #: How it was assigned, for `survey_submissions.arm_source`.
    arm_source: str | None = None
    #: Set once the submission has been written. A second send is then refused rather than
    #: writing a duplicate record of one driver (`survey_submissions.submission_id` is the key).
    submitted: bool = False

    def answered(self, keys: frozenset[str]) -> int:
        return sum(1 for k in keys if self.answers.get(k) not in (None, "", [], ()))


class SubmissionReceipt(BaseModel):
    """What the driver and the researcher get back from one send. `docs/06` §2.1.

    ``reference`` is the number the cover sheet promises — the thing a driver quotes to withdraw
    within 14 days. It is the `submission_id`, not a second identifier: a withdrawal request that
    cannot be matched to a row is not a withdrawal.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference: str
    raw_object_path: str
    outcome: str
    consented: bool
    consent_twin: bool
    eligible: bool
    attention_passed: bool
    battery_answered: int
    battery_expected: int
    #: Set when the submission also produced a twin on the same request. ``None`` when it did not
    #: — because consent 7 was withheld, because the battery is short, or because twin building
    #: is left to the Generator's import. Never a silent omission: ``twin_note`` says which.
    twin_id: str | None = None
    persona_hash: str | None = None
    twin_note: str = ""


__all__ = [
    "Block",
    "HostedInstrument",
    "Question",
    "QuestionKind",
    "Stop",
    "SubmissionReceipt",
    "SurveyProgress",
]
