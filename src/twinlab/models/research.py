"""The Research model page's shapes. `docs/06` §8.

`CLAUDE.md` rule 13: every Pydantic model lives in `models/`. These are the ten sections of
`docs/06` §8, and the page is **rendered from them rather than from hardcoded prose** — which is
what §8 asks for and what keeps the page and the Statistics page describing the same study.

Two properties are research commitments rather than structure:

* **Nothing here is fabricated.** §8.9 says it outright about the reference list, and the same rule
  applies to every other claim on the page: a research question's wording, a hypothesis, a
  construct's definition and its source citation are the researcher's to write. Each of those
  fields defaults to empty and renders as an explicit *not supplied yet* state.
  :class:`Supplied` is the mixin that makes "not supplied" a value rather than a blank.
* **Everything the codebase owns is generated from it**, never restated. The nine constructs, their
  blocks, their indicator counts, their scales and their index signs come from the frozen register;
  the diagram comes from `stats/spec.py::STRUCTURAL_EDGES`, which is also what the estimator uses.
  A page that restated either would be free to disagree with the numbers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: `docs/06` §8.5's third column. Empty means *not yet tested*, which is not the same as
#: *not supported* — the distinction I17 insists on everywhere else in this build.
Support = Literal["", "Supported", "Partly supported", "Not supported", "Not yet tested"]

#: What a construct does in `docs/07` §7.2's diagram. Derived from the structural model, never
#: typed in twice.
DiagramRole = Literal[
    "antecedent", "algorithmic-management perception", "justice perception",
    "satisfaction", "behavioural intention", "moderator",
]


class _Research(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Supplied(_Research):
    """Base for a row whose research prose the researcher supplies.

    ``supplied`` is read by the page to choose between the row and an empty state. It is a
    property rather than a stored flag so it cannot disagree with the content it describes.
    """

    @property
    def supplied(self) -> bool:
        raise NotImplementedError


class ResearchQuestion(Supplied):
    """One of `docs/06` §8.2's three cards.

    ``rq_id`` and ``title`` come from `docs/06` §8 itself, which names all three. ``question``,
    ``hypotheses`` and ``contribution`` are the researcher's words and default to empty — a
    research question invented by a build step is a claim nobody made.
    """

    rq_id: str
    title: str
    question: str = ""
    #: Ids of the hypotheses this question is answered by. Checked against the hypothesis list on
    #: load, so a reference to a hypothesis that does not exist fails loudly.
    hypotheses: list[str] = Field(default_factory=list)
    contribution: str = ""

    @property
    def supplied(self) -> bool:
        return bool(self.question.strip())


class Hypothesis(Supplied):
    """One row of `docs/06` §8.5 — `Hypothesis ID · Statement · Support`."""

    hypothesis_id: str
    statement: str
    support: Support = ""

    @property
    def supplied(self) -> bool:
        return bool(self.statement.strip())


class Reference(_Research):
    """One row of `docs/06` §8.9. **Never fabricated** — the list is empty until supplied."""

    theme: str
    citation: str
    doi: str = ""


class SummaryCard(_Research):
    """One of `docs/06` §8.1's five cards. Generated, never written."""

    title: str
    detail: str
    items: list[str] = Field(default_factory=list)


class DiagramNode(_Research):
    """One construct's place in `docs/07` §7.2's diagram, derived from the structural model."""

    code: str
    label: str
    role: DiagramRole
    #: Layer 0 is the antecedent; each edge moves one layer right. The moderator sits beside the
    #: path it moderates rather than on a layer of its own.
    layer: int


class DiagramEdge(_Research):
    """One structural path, as the estimator has it. `stats/spec.py::STRUCTURAL_EDGES`."""

    source: str
    target: str
    kind: Literal["path", "moderation", "main effect"] = "path"


class MeasurementMapRow(_Research):
    """One row of **`docs/06` §8.4 — required, new in 2.0.**

    The theoretical diagram's constructs do not map one-to-one onto what the instrument fields, and
    without this table the Research model page and the Statistics page appear to describe different
    studies. Every column is read from the frozen register or from the structural model, so the two
    pages cannot disagree.
    """

    #: The construct code. Named ``code`` rather than ``construct`` because pydantic's own
    #: deprecated ``BaseModel.construct`` would shadow it; the column header is still "Construct".
    code: str
    label: str
    role: DiagramRole
    #: The **item** block, which is a different namespace from the construct code (`docs/01` §3.3):
    #: `FAIR` is both.
    block: str
    indicators: int
    scale_id: str
    scale_points: int
    #: Set on exactly the six constructs that enter the index; ``None`` on the three traits.
    metric_name: str | None = None
    index_sign: int | None = None


class ConstructDefinitionRow(Supplied):
    """One row of `docs/06` §8.7 — `Construct · Definition · Where it comes from`.

    ``code`` and ``label`` are generated from the frozen register. ``definition`` and ``source``
    are the researcher's, and ``source`` in particular is a citation — see §8.9.
    """

    code: str
    label: str
    definition: str = ""
    source: str = ""

    @property
    def supplied(self) -> bool:
        return bool(self.definition.strip())


class MethodRow(Supplied):
    """One row of `docs/06` §8.6 — `Part · What it involves`.

    ``part`` is fixed and ordered by §8.6. ``involves`` is the researcher's prose, and
    ``from_the_build`` is a fact this codebase owns — a count, a code, a version — appended so
    the row is never wholly blank and so the prose can be checked against what it describes.
    """

    part: str
    involves: str = ""
    from_the_build: str = ""

    @property
    def supplied(self) -> bool:
        return bool(self.involves.strip())


class ValidationMapRow(Supplied):
    """One row of `docs/06` §8.8.

    `Technique · What it assesses · Where it is used · Paper section`.

    The row **set** is generated from the application's own objects — the two holdouts, the two
    control cells, the reference arm and all eight validity tests — so a technique cannot appear
    here that the app does not run, and one it runs cannot be missing. `assesses` is `docs/08`
    §6.3's wording; `paper_section` is the researcher's.
    """

    technique: str
    assesses: str
    where_used: str
    paper_section: str = ""

    @property
    def supplied(self) -> bool:
        return bool(self.paper_section.strip())


class ResearchModelView(_Research):
    """The whole page, in `docs/06` §8's mandatory section order.

    Assembled once in the service layer and handed to `ui/` complete. The page does no lookups and
    computes nothing (`docs/05` §8.4 rule 5).
    """

    one_line: str
    summary_cards: list[SummaryCard]
    research_questions: list[ResearchQuestion]
    diagram_nodes: list[DiagramNode]
    diagram_edges: list[DiagramEdge]
    #: `ModelSpec.fingerprint()`. The same string the Statistics page prints on every analysis run,
    #: shown here so a reader can see the two pages are describing one model.
    model_fingerprint: str
    measurement_map: list[MeasurementMapRow]
    hypotheses: list[Hypothesis]
    method: list[MethodRow]
    constructs: list[ConstructDefinitionRow]
    validation_map: list[ValidationMapRow]
    references: list[Reference]
    #: Themes in the order the config gives them, so grouping is stable across renders.
    reference_themes: list[str] = Field(default_factory=list)


__all__ = [
    "ConstructDefinitionRow",
    "DiagramEdge",
    "DiagramNode",
    "DiagramRole",
    "Hypothesis",
    "MeasurementMapRow",
    "MethodRow",
    "Reference",
    "ResearchModelView",
    "ResearchQuestion",
    "SummaryCard",
    "Supplied",
    "Support",
    "ValidationMapRow",
]
