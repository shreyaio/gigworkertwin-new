"""Do two levers compound, or substitute? `docs/07` §5. **Implements I17.**

For two codes A and B the joint cell is the elementwise **maximum** of their dial vectors, and the
interaction is what the joint cell does beyond the sum of the two alone::

    extra = shift(joint) - (shift(A) + shift(B))

    extra < 0  → sub-additive     the two protections substitute for each other
    extra > 0  → super-additive   they compound
    extra == 0 → additive

**Sub-additivity is the contribution.** It tells a regulator which reform to mandate when only
one is
affordable — a claim no small vignette study can support.

**I17: nothing is imputed.** All three cells must have completed runs, on the same panel. A missing
leg returns a :class:`MissingInteraction` naming the codes to run — never an estimate, never an
interpolation, never "approximately". That is `CLAUDE.md` rule 5, and this module is where the study
would most plausibly have cheated: two of three cells is *almost* enough, and an interpolated third
leg would look exactly like a measured one in the finished table.
"""

from __future__ import annotations

from twinlab.models.analysis import Interaction, MissingInteraction
from twinlab.orchestrator.odometer import combine, validate_code
from twinlab.orchestrator.panel import PanelMismatch


def joint_code(a: str, b: str) -> str:
    """The joint cell: elementwise max of the dial vectors. `docs/07` §5, `docs/02` §8.3."""
    validate_code(a)
    validate_code(b)
    return combine(a, b)


def interaction(
    a: str,
    b: str,
    metric: str,
    shifts_by_code: dict[str, dict[str, float]],
    *,
    panels_by_code: dict[str, frozenset[str]] | None = None,
    decimals: int = 3,
) -> Interaction | MissingInteraction:
    """One interaction, or an honest statement of what is missing. I17.

    ``shifts_by_code`` holds only **completed** runs: the caller passes what the database actually
    has, so an absent key means an absent run rather than a zero.

    ``panels_by_code`` is checked when supplied. Legs drawn from different panels raise
    :class:`PanelMismatch` (I14) — three cells answered by three different sets of twins do not form
    an interaction, they form three unrelated numbers.
    """
    joint = joint_code(a, b)

    missing = [code for code in (a, b, joint) if code not in shifts_by_code]
    if missing:
        # Never None-and-nothing: the UI must be able to say WHICH code to run.
        return MissingInteraction(a=a, b=b, joint=joint, metric=metric, missing_codes=missing)

    for code in (a, b, joint):
        if metric not in shifts_by_code[code]:
            return MissingInteraction(
                a=a, b=b, joint=joint, metric=metric, missing_codes=[code]
            )

    if panels_by_code is not None:
        panels = {code: panels_by_code.get(code) for code in (a, b, joint)}
        known = {code: p for code, p in panels.items() if p is not None}
        distinct = {frozenset(p) for p in known.values()}
        if len(distinct) > 1:
            raise PanelMismatch(
                f"interaction {a} x {b} spans different panels: "
                + "; ".join(f"{code}={len(p)} twins" for code, p in known.items())
                + ". Three cells answered by three different sets of twins are three unrelated "
                "numbers, not an interaction (I14)."
            )

    alone_a = shifts_by_code[a][metric]
    alone_b = shifts_by_code[b][metric]
    together = shifts_by_code[joint][metric]
    extra = round(together - (alone_a + alone_b), decimals)

    return Interaction(
        a=a,
        b=b,
        joint=joint,
        metric=metric,
        alone_a=alone_a,
        alone_b=alone_b,
        together=together,
        extra=extra,
        verdict=(
            "sub-additive" if extra < 0 else "super-additive" if extra > 0 else "additive"
        ),
    )


def computable_interactions(
    code: str,
    metric: str,
    shifts_by_code: dict[str, dict[str, float]],
    *,
    panels_by_code: dict[str, frozenset[str]] | None = None,
) -> list[Interaction]:
    """Every interaction involving ``code`` that is **fully** computable, for the analyst bundle.

    Only complete ones: the bundle may contain no number that was not computed, so a missing leg is
    simply not offered to the analyst (`docs/02` §4.4). The UI surfaces the missing ones separately,
    with the code to run.
    """
    out: list[Interaction] = []
    for other in sorted(shifts_by_code):
        if other == code:
            continue
        # A pair where one code dominates the other is not an interaction. `01000` with `01010`
        # has joint `01010`, so `extra` collapses to `-shift(01000)` — an arithmetic artefact that
        # would appear in the bundle looking exactly like a measured interaction.
        if joint_code(code, other) in (code, other):
            continue
        try:
            result = interaction(
                code, other, metric, shifts_by_code, panels_by_code=panels_by_code
            )
        except PanelMismatch:
            continue
        if isinstance(result, Interaction):
            out.append(result)
    return out


def describe(result: Interaction) -> str:
    """The deterministic sentence `docs/07` §5 works through. Python, never a model.

    "staying changes +0.31 and +0.09 alone, +0.22 together. The extra is −0.18, so together they add
    less than the sum."
    """
    tail = {
        "sub-additive": "so together they add less than the sum",
        "super-additive": "so together they add more than the sum",
        "additive": "so together they add exactly the sum",
    }[result.verdict]
    return (
        f"{result.metric} changes {result.alone_a:+.2f} and {result.alone_b:+.2f} alone, "
        f"{result.together:+.2f} together. The extra is {result.extra:+.2f}, {tail}."
    )


def describe_missing(result: MissingInteraction) -> str:
    """What the UI tells the researcher. **Names the code to run.** I17, `CLAUDE.md` rule 5."""
    codes = ", ".join(result.missing_codes)
    return (
        f"{result.a} x {result.b} on {result.metric} cannot be computed: no completed run for "
        f"{codes}. Run {codes} to complete it — this is not estimated."
    )
