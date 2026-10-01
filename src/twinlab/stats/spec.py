"""The measurement and structural model, built from the frozen register. `docs/07` §7.

**Nothing here is a literal item list.** Every construct's indicators are read from
`instrument.json` through :mod:`twinlab.ingest.reference_store`, so a construct cannot drift from
the register that defines it. The only literals in this module are the **structural edges**, which
are a theory claim and exist nowhere in the frozen data.

The structural model (researcher, 2026-09-29 — recorded in `docs/DECISIONS.md` as an AMBIGUITY,
because `docs/07` §7.2 names only the antecedent, the moderator and the chain in prose)::

    arm        -> EXPO, CTRL
    EXPO, CTRL -> FAIR, TRAN
    FAIR, TRAN -> SATI
    SATI       -> LOYA, VOIC, EXIT
    EDEP       -> LOYA, VOIC, EXIT          (main effect)
    EDEP x SATI-> LOYA, VOIC, EXIT          (moderation)

Full mediation: justice perceptions reach the behavioural intentions **only** through
satisfaction. `docs/07` §8.6 is explicit that the indirect effects are where the theory lives, and
this is the structure that makes them testable.

Two things this module must get right, because they are exactly what the golden test exists to
catch (`docs/07` §10):

1. **Attention checks are never indicators.** `AMQ6` and `ALGO5` sit in the `AMQ` and `ALGO`
   blocks and are screening instruments, not measurements (I10). They are filtered by
   ``attention_check``, never by name, so a future attention item is excluded automatically.
2. **Holdout items are never indicators.** Parts 16 and 17 measure the twins' fidelity, not the
   humans' constructs. They are excluded by ``in_twin_battery`` and by block.
"""

from __future__ import annotations

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.stats import ConstructSpec, ModelSpec, PathEdge

#: The experimental antecedent as one formative block of arm dummies. `docs/01` §5.
ARM_CONSTRUCT = "ARM"

#: `docs/01` §5: the no-change control every other arm is measured against.
ARM_REFERENCE = "BASE"

#: The moderator and the path it moderates. `docs/07` §7.2; resolved 2026-09-29.
MODERATOR = "EDEP"
MODERATED = "SATI"

#: The interaction latent variable's name. Product indicators, Mode A.
INTERACTION_CONSTRUCT = f"{MODERATOR}_x_{MODERATED}"

#: The structural edges. **The only theory literal in the statistics layer.**
#: ``ARM`` and the interaction term are added by :func:`build_model_spec`, which knows which
#: constructs they point at, so the chain below stays readable.
STRUCTURAL_EDGES: tuple[tuple[str, str], ...] = (
    ("EXPO", "FAIR"),
    ("EXPO", "TRAN"),
    ("CTRL", "FAIR"),
    ("CTRL", "TRAN"),
    ("FAIR", "SATI"),
    ("TRAN", "SATI"),
)

#: The antecedent's targets — the algorithmic-management perceptions. `docs/07` §8.6.
ANTECEDENT_TARGETS: tuple[str, ...] = ("EXPO", "CTRL")

#: The behavioural intentions. `docs/01` §3.3: wants to stay, pushes back, wants to leave.
INTENTIONS: tuple[str, ...] = ("LOYA", "VOIC", "EXIT")


class ModelSpecError(ValueError):
    """The model cannot be built from the register. Never a silently shorter model."""


def arm_dummy_columns(ref: ReferenceData | None = None) -> tuple[str, ...]:
    """One dummy per non-reference arm, in `arms.json` order. `docs/01` §5.

    The reference arm gets **no** column — that is what makes it the reference. Three dummies for
    four arms; a fourth would make the block singular and the engine would fail on a rank
    deficiency rather than on anything a reader could interpret.
    """
    ref = ref or reference()
    dummies = tuple(
        f"arm_{arm_id}" for arm_id in ref.arms if arm_id != ARM_REFERENCE
    )
    if not dummies:
        raise ModelSpecError(
            f"no arms other than the reference {ARM_REFERENCE!r}; the antecedent has no variance"
        )
    return dummies


def construct_items(code: str, ref: ReferenceData | None = None) -> tuple[str, ...]:
    """The indicator items of one of the nine constructs, from the frozen register.

    Filters, in order: the construct's own block, then out every attention check (I10), then out
    everything that is not in the twin battery — which removes the Part 16 and Part 17 holdouts
    without naming them.

    Raises rather than returning a short block. A construct silently measured by fewer items than
    the register gives it is precisely the fault `docs/07` §10 requires the golden test to catch,
    and a raise here means it can never reach an estimate.
    """
    ref = ref or reference()
    construct = ref.constructs.get(code)
    if construct is None:
        raise ModelSpecError(f"unknown construct {code!r}")

    items = tuple(
        item_id
        for item_id, item in ref.items.items()
        if item.block == construct.block
        and not item.attention_check
        and item.in_twin_battery
    )
    if not items:
        raise ModelSpecError(
            f"construct {code!r} (block {construct.block!r}) has no indicator items in the "
            "register. No construct is ever estimated from a subset."
        )
    return items


def interaction_columns(ref: ReferenceData | None = None) -> tuple[str, ...]:
    """The product-indicator column names for ``EDEP x SATI``. `docs/07` §7.2.

    The standard product-indicator approach: every moderator item crossed with every moderated
    item, on standardised values. Two `DEP` items by three `SAT` items gives six indicators.
    """
    ref = ref or reference()
    mod = construct_items(MODERATOR, ref)
    tgt = construct_items(MODERATED, ref)
    return tuple(f"{m}_x_{t}" for m in mod for t in tgt)


def build_model_spec(ref: ReferenceData | None = None) -> ModelSpec:
    """The whole model. Built once, pinned by the golden test through its fingerprint.

    Implements `docs/07` §7.2: all nine register constructs reflective (Mode A), the arm dummies
    formative (Mode B), and the moderation carried by a product-indicator interaction construct.
    """
    ref = ref or reference()

    constructs: list[ConstructSpec] = [
        ConstructSpec(
            code=ARM_CONSTRUCT,
            label="Experimental arm",
            mode="B",
            items=arm_dummy_columns(ref),
            scale_id=None,
            reflective=False,
        )
    ]
    for construct in ref.constructs.values():
        constructs.append(
            ConstructSpec(
                code=construct.code,
                label=construct.label,
                mode="A",
                items=construct_items(construct.code, ref),
                scale_id=construct.scale_id,
                reflective=True,
            )
        )
    constructs.append(
        ConstructSpec(
            code=INTERACTION_CONSTRUCT,
            label=f"{MODERATOR} x {MODERATED}",
            mode="A",
            items=interaction_columns(ref),
            scale_id=None,
            # A product term is not a construct anyone claims to have measured: reliability and
            # discriminant validity are not reported for it (docs/07 §8.1 covers the nine).
            reflective=False,
        )
    )

    edges: list[PathEdge] = [
        PathEdge(source=ARM_CONSTRUCT, target=target) for target in ANTECEDENT_TARGETS
    ]
    edges += [PathEdge(source=s, target=t) for s, t in STRUCTURAL_EDGES]
    for target in INTENTIONS:
        edges.append(PathEdge(source=MODERATED, target=target))
        edges.append(PathEdge(source=MODERATOR, target=target))
        edges.append(PathEdge(source=INTERACTION_CONSTRUCT, target=target))

    spec = ModelSpec(
        constructs=tuple(constructs),
        edges=tuple(edges),
        arm_reference=ARM_REFERENCE,
        interaction=(MODERATOR, MODERATED),
    )
    _assert_acyclic(spec)
    return spec


def _assert_acyclic(spec: ModelSpec) -> None:
    """The engine needs a lower-triangular path matrix, so the model must be a DAG.

    Raised here with the cycle named, because the engine's own error is a shape complaint about a
    matrix the caller never built.
    """
    incoming: dict[str, set[str]] = {code: set() for code in spec.codes}
    for edge in spec.edges:
        if edge.source not in incoming or edge.target not in incoming:
            raise ModelSpecError(
                f"edge {edge} names a construct that is not in the model {spec.codes}"
            )
        incoming[edge.target].add(edge.source)

    resolved: list[str] = []
    remaining = dict(incoming)
    while remaining:
        ready = sorted(c for c, deps in remaining.items() if not deps - set(resolved))
        if not ready:
            raise ModelSpecError(
                f"the structural model has a cycle among {sorted(remaining)}; PLS-SEM requires a "
                "directed acyclic graph"
            )
        resolved.extend(ready)
        for code in ready:
            remaining.pop(code)


def topological_order(spec: ModelSpec) -> tuple[str, ...]:
    """Constructs ordered so every source precedes its target. `openpls` needs lower triangular.

    Deterministic: ties break alphabetically, so the path matrix — and therefore every stored
    payload's row order — is identical across processes (`docs/09` §2).
    """
    incoming: dict[str, set[str]] = {code: set() for code in spec.codes}
    for edge in spec.edges:
        incoming[edge.target].add(edge.source)

    order: list[str] = []
    remaining = dict(incoming)
    while remaining:
        ready = sorted(c for c, deps in remaining.items() if not deps - set(order))
        order.extend(ready)
        for code in ready:
            remaining.pop(code)
    return tuple(order)
