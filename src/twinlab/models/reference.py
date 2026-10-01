"""Frozen reference data models. `docs/01_DATA_MODEL.md` §2–§5.

These mirror `data/reference/*.json` exactly. The files are the scientific artifact: generated
once by `ingest/build_reference.py`, committed, seeded into Postgres, and never written by the
running application.

Three tables of constants live here rather than in a JSON file, because they are *definitions*
the specification states normatively rather than data parsed out of a source document:
:data:`MET_CRITERIA`, :data:`LEVER_NAMES` and :data:`CONSTRUCTS`. See `docs/DECISIONS.md`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Finding = Literal["Met", "Partly met", "Not met", "No evidence found", "Contradicted"]
GapType = Literal["INTRODUCE", "EXTEND", "REMOVE", "UNIVERSALISE", "DOCUMENT"]
Judgement = Literal["SUPPORTS", "PARTIAL", "ASSERTED", "SCOPE LIMITED", "CONTRADICTS"]
Lever = Literal["L1", "L2", "L3", "L4", "L5"]
ItemRole = Literal[
    "outcome", "trait", "attention", "holdout_h2", "holdout_h3", "open", "demographic"
]
Direction = Literal["positive", "negative"]

#: The three criteria Table C records as Met. They are the SHAM commitment set and are never
#: announced as new in any render (`docs/02` §4.2).
MET_CRITERIA: tuple[str, str, str] = ("3.1.a", "3.1.c", "4.1.c")

#: The two attention checks. Human data-quality devices, never put to a twin (I10).
ATTENTION_ITEMS: tuple[str, str] = ("ALGO5", "AMQ6")

#: Reverse-coded items. `H2_SAT2` inherits from `SAT2` (`docs/01` §3.1).
REVERSE_CODED_ITEMS: tuple[str, str, str] = ("DEP1", "H2_SAT2", "SAT2")

LEVERS: tuple[Lever, ...] = ("L1", "L2", "L3", "L4", "L5")

#: Version-code position → lever, left to right. `ARCHITECTURE.md` §5.
LEVER_BY_POSITION: tuple[Lever, ...] = LEVERS

LEVER_NAMES: dict[str, str] = {
    "L1": "Pay",
    "L2": "Conditions",
    "L3": "Contracts",
    "L4": "Management",
    "L5": "Representation",
}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Criterion(_Frozen):
    criterion_id: str
    principle: int
    threshold_id: str
    threshold_name: str
    threshold_point: str
    satisfaction_rule: str
    criterion_text: str


class CriterionFinding(_Frozen):
    criterion_id: str
    finding: Finding
    reason: str


class Threshold(_Frozen):
    threshold_id: str
    threshold_name: str
    lever: Lever
    awarded_2026: int
    reason: str
    gate_threshold: str | None = None


class Gap(_Frozen):
    """A Table D row. ``commitment`` IS the treatment text — what would close the gap."""

    gap_id: str
    criterion_id: str
    threshold_id: str
    lever: Lever
    gap_type: GapType
    commitment: str
    precedent: str
    anchor_text: str
    anchor_sources: list[str]


class Chunk(_Frozen):
    """A verbatim extract of Uber policy. ``chunk_id`` is opaque and never renumbered (rule 8)."""

    chunk_id: str
    source_id: str
    source_type: str | None = None
    jurisdiction: str | None = None
    audience: str | None = None
    lever: str | None = None
    threshold_id: str | None = None
    refiled_from: str | None = None
    policy_surfaces: list[str] = Field(default_factory=list)
    section: str | None = None
    heading: str | None = None
    verbatim_text: str
    citation: str


class ChunkCriterionLink(_Frozen):
    link_id: str
    chunk_id: str
    criterion_id: str
    judgement: Judgement


class Scale(_Frozen):
    """``anchors`` is fully labelled at every point, and its length must equal ``points``."""

    scale_id: str
    points: int
    format: str
    anchors: list[str]


class Item(_Frozen):
    """A survey item. ``item_id`` is the addressing scheme everywhere — never renumber (rule 8)."""

    item_id: str
    part: int
    part_name: str | None = None
    block: str
    ordinal: int
    stem: str
    scale_id: str | None = None
    reverse_coded: bool = False
    attention_check: bool = False
    role: ItemRole
    in_twin_battery: bool = False
    mirrors: str | None = None
    version_shown: int | None = None
    version_code: str | None = None


class MetricDef(_Frozen):
    """An instrument property, not an analyst property (`docs/02` §2)."""

    items: list[str]
    scale: str
    direction: Direction


class Construct(_Frozen):
    """One of the nine constructs. `docs/01` §3.3.

    ``metric_name`` and ``index_sign`` are set on exactly the six that enter the index; the
    three traits carry ``None`` for both. ``EDEP`` is the moderator.
    """

    code: str
    label: str
    block: str
    metric_name: str | None = None
    index_sign: Literal[-1, 1] | None = None
    scale_id: str


class Arm(_Frozen):
    """One of the four human survey arms. `docs/01` §5.

    Distinct from the two *twin* control cells (`ARCHITECTURE.md` §5.2) — this is a
    between-subjects survey design, not a control cell, and adding one is not adding an arm
    to the sweep.
    """

    arm_id: str
    label: str
    version_code: str
    lever: Lever | None = None
    is_control: bool = False


class LegacyItem(_Frozen):
    """A prototype identifier and what it means canonically. `docs/01` §4.

    ``pattern`` rows carry a ``{}``-style legacy id family rather than a single id: the four
    holdout families are recorded as rules because expanding them by hand is what the
    crosswalk exists to prevent.
    """

    legacy_id: str
    item_id: str | None = None
    note: str | None = None
    pattern: bool = False


#: The nine constructs, in `docs/01` §3.3 order.
#:
#: This is normative specification text, not data parsed from a source document, and
#: `instrument.json` is frozen byte-identical so it cannot carry it (`docs/DECISIONS.md`).
#: `ingest/reference_store.py` cross-checks every signed construct against `instrument.json`'s
#: own `metrics` block, so the two cannot drift.
CONSTRUCTS: tuple[Construct, ...] = (
    Construct(code="EXPO", label="Managed by the app", block="AMQ", scale_id="agree7"),
    Construct(code="CTRL", label="Feels controlled", block="PAC", scale_id="agree5"),
    Construct(
        code="FAIR", label="Feels treated fairly", block="FAIR",
        metric_name="fairness", index_sign=1, scale_id="extent7",
    ),
    Construct(
        code="TRAN", label="Finds the app clear", block="CLAR",
        metric_name="clarity", index_sign=1, scale_id="agree5",
    ),
    Construct(
        code="SATI", label="Happy with the job", block="SAT",
        metric_name="happiness", index_sign=1, scale_id="agree7",
    ),
    Construct(
        code="LOYA", label="Wants to stay", block="CONT",
        metric_name="staying", index_sign=1, scale_id="agree5",
    ),
    Construct(
        code="VOIC", label="Pushes back", block="ALGO",
        metric_name="pushback", index_sign=-1, scale_id="agree7",
    ),
    Construct(
        code="EXIT", label="Wants to leave", block="TURN",
        metric_name="leaving", index_sign=-1, scale_id="agree7",
    ),
    Construct(code="EDEP", label="Needs the money", block="DEP", scale_id="agree7"),
)

#: Item block → construct code. The inverse of :data:`CONSTRUCTS`.
#:
#: **Namespace warning** (`docs/01` §3.3): `FAIR` is both an item block and a construct code.
#: They are different namespaces. Read ``item.block`` or ``construct.code``, never a bare
#: ``FAIR``.
BLOCK_TO_CONSTRUCT: dict[str, str] = {c.block: c.code for c in CONSTRUCTS}


def construct_code_for(item: Item) -> str | None:
    """The construct an item measures, or ``None``.

    Holdout and attention items have no construct: `docs/01` §6.1 declares
    ``survey_items.construct_code`` null for both. An H2 item's construct is reachable through
    ``mirrors``; it is deliberately not duplicated onto the row, so a query for `FAIR` cannot
    accidentally pool Part 7 with Part 16.
    """
    if item.attention_check or item.role.startswith("holdout"):
        return None
    return BLOCK_TO_CONSTRUCT.get(item.block)
