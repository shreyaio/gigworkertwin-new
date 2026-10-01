"""The treatment and its gates. `docs/03` §2–§5.

`DeltaSpec` is the frozen treatment: `version_code → DeltaSpec` is a pure lookup over
`dial_lookup.json` and `gaps.json` with no model consulted, and identical input gives
byte-identical output forever (I1).

The design-agent and checker shapes are declared here so `SCHEMA_REGISTRY` can name them at M2.
Their *behaviour* — rendering, the five gates, the coverage probe — is M5.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

from twinlab.models.reference import Lever

#: The fixed dial-0 string. Never generated, byte-identical everywhere (I5).
DIAL_ZERO_TEXT = "No change from today."

#: SHAM occupies its own slot in the paragraph cache: its unfilled levers announce that lever's
#: *existing* driver-facing policy, so they are neither dial-0 lines nor live-cell paragraphs
#: (`docs/01` §6.6, researcher-approved).
SHAM_DIAL = 3


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DeltaSpec(_Frozen):
    """The treatment for one version code. Frozen and deterministic (I1).

    ``commitments`` maps gap id → the commitment text out of `gaps.json`. That text *is* the
    treatment; nothing paraphrases it on the way to the design agent.
    """

    version_code: str
    gaps_by_lever: dict[str, list[str]]
    commitments: dict[str, str]
    delta_hash: str

    @staticmethod
    def hash_of(gaps_by_lever: dict[str, list[str]]) -> str:
        """The canonical delta hash: stable across processes and across dict ordering.

        `docs/03` §2 defines it over `gaps_by_lever` with sorted keys, so it identifies the
        *selection* and is unaffected by how the commitments happen to be rendered.
        """
        payload = json.dumps(gaps_by_lever, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    @property
    def fairwork_score(self) -> int:
        """The digit sum, 0–10. `ARCHITECTURE.md` §5."""
        return sum(int(d) for d in self.version_code)


class LeverBrief(_Frozen):
    """What the design agent receives — exactly four things and nothing else. `docs/02` §4.1.

    The fourth, ``do_not_say``, is the containment boundary: every commitment *not* in this
    lever's set plus the three already-met criteria. Without it an `01000` render can absorb
    threshold 2.2 material and `01000` stops differing from `02000` (I3).
    """

    lever: Lever
    dial: int
    #: gap id → commitment text, for **this lever only**.
    commitments: dict[str, str]
    #: Corpus extracts, for register only: copy the voice, and do not re-announce what exists.
    anchor_chunks: list[str] = Field(default_factory=list)
    style_contract: dict = Field(default_factory=dict)
    do_not_say: list[str] = Field(default_factory=list)


class LeverParagraph(BaseModel):
    """One rendered lever paragraph, or a refusal. `docs/02` §4.1.

    ``status`` is how the agent signals inability. `# IF YOU CANNOT` returns
    ``cannot_render`` with a reason, the cell is marked `failed` and logged, and it is **never**
    filled with a generic paragraph.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = ""
    status: str = "ok"
    reason: str = ""

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class CoverageProbe(_Frozen):
    """One coverage question: does this paragraph entail this commitment?

    The only LLM step in the Checker, one call per commitment at temperature 0.0, with the
    commitment and the paragraph as the sole inputs (`docs/02` §4.3).
    """

    gap_id: str
    commitment: str
    paragraph: str


class CoverageVerdict(BaseModel):
    """The probe's answer. **Uncertainty fails closed.**

    `docs/02` §4.3: a call that cannot decide returns ``entailed: false`` with the reason. A gate
    that cannot decide has not passed, and an unparseable verdict counts as not entailed
    (`docs/02` §5.5).
    """

    model_config = ConfigDict(extra="forbid")

    entailed: bool = False
    reason: str = ""


class CheckerReport(BaseModel):
    """The five gates' combined result. `docs/03` §5.

    ``containment`` is asymmetric on purpose: coverage failing means the stimulus is weaker than
    intended, which is detectable downstream; containment failing means two cells are no longer
    distinguishable, which is not. **One hit fails the cell** — there is no threshold.
    """

    model_config = ConfigDict(extra="forbid")

    coverage: dict[str, bool] = Field(default_factory=dict)
    containment: list[str] = Field(default_factory=list)
    word_count: int = 0
    in_band: bool = False
    reading_grade: float = 0.0
    dial_zero_identical: bool = False
    sham_indistinguishable: bool | None = None
    passed: bool = False
    notes: str = ""


class RenderedVariant(BaseModel):
    """One cell's five paragraphs, assembled from the 11-string pool. `docs/03` §4.3.

    The paragraphs are **assembled, not generated**: every cell with Conditions = 1 carries the
    byte-identical Conditions paragraph, which is what makes the levers structurally independent
    rather than independent by convention (I4). ``paragraphs`` is keyed by lever and always holds
    all five, in `LEVER_BY_POSITION` order — `lever_order_in_text: fixed`. Randomisation happens
    once, per twin per round, when the round prompt is built (M6), never here.
    """

    model_config = ConfigDict(extra="forbid")

    version_code: str
    style_version: str
    delta_hash: str
    paragraphs: dict[str, LeverParagraph]
    #: ``dial`` per lever, with :data:`SHAM_DIAL` for the sham's five slots.
    dials: dict[str, int]

    @property
    def ok(self) -> bool:
        """Every lever rendered. A single ``cannot_render`` fails the cell, never a partial fill."""
        return all(p.status == "ok" for p in self.paragraphs.values())

    def scenario_lines(self, order: list[str] | None = None) -> list[str]:
        """The five paragraphs, fixed order by default. ``order`` is the twin's randomisation."""
        levers = order or list(self.paragraphs)
        return [self.paragraphs[lever].text for lever in levers]
