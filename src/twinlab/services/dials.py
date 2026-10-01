"""The Dial board's state, computed in process with **no network call**. `docs/06` §3.2.

`docs/05` §8.4 rule 6 is an explicit acceptance criterion for M10: changing a dial recomputes the
version code, the Fairwork score and "what the twins are told" from reference data already loaded,
and it must feel instant. Nothing in this module touches the database, the provider or the disk —
:func:`twinlab.variant.lookup.lookup` is a pure table read over frozen JSON (I1).

This module also owns the single implementation of **what the twins are told** (`docs/05` §4.4).
The Dial board, the Results side panel and the Twins side panel must show byte-identical text for
the same code, so all three call :func:`what_twins_are_told` and there is no second renderer.
"""

from __future__ import annotations

from twinlab.models.reference import LEVER_BY_POSITION, LEVER_NAMES
from twinlab.models.view import DialBoard, TellBullet, TellLever
from twinlab.orchestrator.odometer import CONTROL_CODE, validate_code
from twinlab.variant.lookup import lookup, told_summary

#: The five dial rows, top to bottom, in version-code order (`ARCHITECTURE.md` §5).
LEVER_ORDER: tuple[str, ...] = LEVER_BY_POSITION

#: `docs/05` §7 rule 1. The legend the dial colours mean: a traffic light for *protection level*.
DIAL_LEGEND: tuple[str, ...] = (
    "0 = as Uber is today",
    "1 = some protection",
    "2 = more protection",
)

#: The exact warning strip copy for the control cell (`docs/06` §3.2).
CONTROL_WARNING = "Turn at least one dial above 0. 00000 is a control cell."

#: Why *Ask the twins* is disabled rather than merely discouraged. Raised as `ControlCellError`
#: by the orchestrator; shown as this sentence in the UI.
CONTROL_REASON = (
    "00000 is the control the orchestrator runs at the start of every session, "
    "not a cell to ask by hand."
)


def code_from_dials(dials: dict[str, int]) -> str:
    """Five dial values to a version code. Pure.

    Raises on an unknown lever or an out-of-range dial rather than clamping: a silently clamped
    dial is a different treatment wearing the same code (`CLAUDE.md`, "never coerce").
    """
    missing = [lever for lever in LEVER_ORDER if lever not in dials]
    if missing:
        raise KeyError(f"no dial value for {missing}; all five levers are required")
    digits = []
    for lever in LEVER_ORDER:
        value = dials[lever]
        if value not in (0, 1, 2):
            raise ValueError(
                f"dial {lever}={value!r} is out of range. Dials are 0, 1 or 2 "
                "(docs/03 §2); a clamped dial is a different treatment under the same code."
            )
        digits.append(str(value))
    return validate_code("".join(digits))


def dials_of(version_code: str) -> dict[str, int]:
    """A version code back to its five dials."""
    validate_code(version_code)
    return {lever: int(version_code[i]) for i, lever in enumerate(LEVER_ORDER)}


def fairwork_text(score: int) -> str:
    """``Fairwork score 1 of 10``. One wording, so two screens cannot differ."""
    return f"Fairwork score {score} of 10"


def what_twins_are_told(version_code: str) -> list[TellLever]:
    """The researcher-facing bullet summary for one code. **The only implementation.**

    `docs/05` §4.4: one component, one source, used by the Dial board, the Results side panel and
    the Twins side panel. `docs/03` §4.3: this and the scenario paragraph come from the same
    `DeltaSpec` and must never be swapped — a twin never sees these bullets, and this summary is
    never fed to a model.
    """
    spec = lookup(version_code)
    summary = told_summary(spec)
    out: list[TellLever] = []
    for position, lever in enumerate(LEVER_ORDER):
        dial = int(version_code[position])
        name = LEVER_NAMES[lever]
        bullets = [
            TellBullet(gap_id=gap_id, text=text)
            for gap_id, text in (
                line.split(" — ", 1) for line in summary.get(lever, [])
            )
        ]
        heading = f"{name} step {dial}" if dial else f"{name} — no change"
        out.append(
            TellLever(
                lever=lever, lever_name=name, dial=dial, heading=heading, bullets=bullets
            )
        )
    return out


def is_control(version_code: str) -> bool:
    """`00000` only. `SHAM` is the other control but has no dial representation."""
    return version_code == CONTROL_CODE


def dial_board(dials: dict[str, int] | str) -> DialBoard:
    """Everything the Dial board shows, from five dials or a code. Pure; no I/O.

    Implements the M10 acceptance criterion for `docs/06` §3.2 — code, score and "what the twins
    are told" recomputed with no network call — and the control-cell block of `docs/05` §7 rule 3.
    """
    version_code = dials if isinstance(dials, str) else code_from_dials(dials)
    validate_code(version_code)
    spec = lookup(version_code)
    control = is_control(version_code)
    return DialBoard(
        version_code=version_code,
        dials=dials_of(version_code),
        fairwork_score=spec.fairwork_score,
        fairwork_text=fairwork_text(spec.fairwork_score),
        told=what_twins_are_told(version_code),
        is_control=control,
        warning=CONTROL_WARNING if control else None,
    )
