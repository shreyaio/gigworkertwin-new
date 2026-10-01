"""`version_code → DeltaSpec`. A pure lookup. `docs/03` §2 and §3. Implements I1.

**No model is ever consulted about what a dial means.** The treatment is a table read: the digit
selects a row of `dial_lookup.json`, and the commitment text is copied verbatim out of `gaps.json`.
Identical input gives byte-identical output, every run, forever.

The most important function here is :func:`do_not_say`, not :func:`lookup`. Because the Conditions
digit is `1` and not `2`, the threshold 2.2 gaps stay **out** — and if any of them leaks into the
rendered text, `01000` and `02000` become the same stimulus and the Conditions lever stops measuring
anything. Most of what the Checker does is guard that line; this is where the line is drawn.
"""

from __future__ import annotations

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.reference import LEVER_BY_POSITION, MET_CRITERIA
from twinlab.models.variant import DeltaSpec
from twinlab.orchestrator.odometer import SHAM_CODE, validate_code


class ShamNotLookedUp(ValueError):
    """`SHAM` has no row in `dial_lookup.json` and is not a lookup.

    Its commitment set is the three criteria coded **Met** (`ARCHITECTURE.md` §5.2), which are by
    definition not gaps, and its unfilled levers announce that lever's *existing* driver-facing
    policy (`docs/03` §6.2). Assembling that is M5's, and doing it here would mean choosing text
    for a control cell whose whole point is having zero free parameters.
    """


def lookup(version_code: str, ref: ReferenceData | None = None) -> DeltaSpec:
    """The frozen treatment for one version code. Pure; no model, no network, no I/O. I1.

    `lookup("00000")` returns zero commitments, `lookup("01000")` three, `lookup("02000")` six,
    `lookup("22222")` thirty.
    """
    if version_code == SHAM_CODE:
        raise ShamNotLookedUp(
            "SHAM is not a dial_lookup row: its set is the three Met criteria "
            f"{MET_CRITERIA} and its unfilled levers announce existing policy (docs/03 §6.2)"
        )
    validate_code(version_code)
    ref = ref or reference()

    gaps_by_lever: dict[str, list[str]] = {}
    for position, lever in enumerate(LEVER_BY_POSITION):
        dial = int(version_code[position])
        selected = ref.dial_lookup[lever][str(dial)]
        # Copied, not aliased: a caller mutating the returned list must not be able to edit the
        # frozen reference data in memory.
        gaps_by_lever[lever] = list(selected)

    commitments = {
        gap_id: ref.gaps[gap_id].commitment
        for lever in LEVER_BY_POSITION
        for gap_id in gaps_by_lever[lever]
    }
    return DeltaSpec(
        version_code=version_code,
        gaps_by_lever=gaps_by_lever,
        commitments=commitments,
        delta_hash=DeltaSpec.hash_of(gaps_by_lever),
    )


def do_not_say(spec: DeltaSpec, lever: str, ref: ReferenceData | None = None) -> list[str]:
    """Every commitment **not** in this lever's set, plus the already-met three. `docs/03` §3.

    Two distinct reasons, which must not be conflated:

    * A commitment from another lever or another threshold would make two cells the same stimulus.
      That is I3, and it is undetectable downstream.
    * The three already-met criteria describe things Uber **already does**. Announcing one as new
      measures reaction to something drivers already have — which is the sham's job, deliberately
      and in one place, never an accident in a live cell.
    """
    ref = ref or reference()
    if lever not in spec.gaps_by_lever:
        raise KeyError(f"{lever!r} is not a lever of {spec.version_code}")
    mine = set(spec.gaps_by_lever[lever])
    others = {gap_id for gap_id in ref.gaps if gap_id not in mine}
    return sorted(others | set(MET_CRITERIA))


def dial_of(version_code: str, lever: str) -> int:
    """The dial this code sets for one lever."""
    validate_code(version_code)
    return int(version_code[LEVER_BY_POSITION.index(lever)])


def commitments_for_lever(spec: DeltaSpec, lever: str) -> dict[str, str]:
    """This lever's commitments only — what the design agent is given. `docs/02` §4.1.

    The design agent receives one lever at a time and has no way to reach another: that is what
    makes the 11-string render cache (I4) and lever independence structural rather than a
    convention.
    """
    return {gap_id: spec.commitments[gap_id] for gap_id in spec.gaps_by_lever[lever]}


def told_summary(spec: DeltaSpec, ref: ReferenceData | None = None) -> dict[str, list[str]]:
    """"What the twins are told" — the **researcher-facing** bullet summary. `docs/03` §4.3.

    Rendered per lever as `Pay step 1 / Pay step 2`. This and the scenario paragraph come from the
    same DeltaSpec and must never be swapped: a twin never sees bullets, and this summary is never
    fed to a model.
    """
    ref = ref or reference()
    out: dict[str, list[str]] = {}
    for lever, gap_ids in spec.gaps_by_lever.items():
        out[lever] = [f"{gap_id} — {ref.gaps[gap_id].commitment}" for gap_id in gap_ids]
    return out
