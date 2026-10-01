"""The frozen analysis panel. `docs/03` §9. Implements I14.

Shifts are **within-subject**, so the interaction

    extra = shift(A ∪ B) − (shift(A) + shift(B))

is meaningless if A, B and A∪B were answered by different people: the differences would carry
between-person variance rather than the effect of combining protections. The resolution is to draw
a stratified subsample of K quality-passed twins **once**, at session creation, and have those exact
twins answer every cell.

Everything here is pure. The draw takes a list of candidates, a size and a seed, and returns the
panel; it never touches a database, so it is reproducible across processes by construction and the
service layer (M7) is the only thing that has to know where candidates come from.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable

from twinlab.models.twin import PanelCandidate, PanelMember

#: `twins.source` values a panel may draw from, by the session's `population` setting.
#:
#: **`manual` is in none of them.** A manual twin has no real survey row, therefore no holdout and
#: no quality score, and it is a sandbox object that must never enter an analysis (`docs/03` §9.3,
#: `docs/01` §6.2).
POPULATION_SOURCES: dict[str, frozenset[str]] = {
    "real": frozenset({"real"}),
    "synthetic": frozenset({"synthetic"}),
    "both": frozenset({"real", "synthetic"}),
}


class PanelError(RuntimeError):
    """Any refusal to produce or compare a panel."""


class InsufficientEligibleTwins(PanelError):
    """Fewer quality-passed twins than the session asked for.

    Raised rather than quietly drawing a smaller panel. `sessions.panel_size` is frozen onto the
    session and reported with its results, so a panel of 15 recorded as 20 would misstate the
    study; and a panel of zero would produce runs with `twins_n = 0`, which I15 forbids from ever
    being a result. The researcher lowers `panel_size` or quality-tests more twins.
    """


class PanelMismatch(PanelError):
    """Two panels being compared are not the same set of twins. I14.

    Refuses the comparison and names both panels (`docs/04` §9). A cell answered by a different set
    of twins is a different experiment: it cannot be compared or differenced against the others,
    and an interaction assembled across the two would be arithmetic on incomparable numbers.
    """


def eligible_candidates(
    candidates: Iterable[PanelCandidate], population: str = "real"
) -> list[PanelCandidate]:
    """The twins a session may draw from. `docs/03` §9.1.

    Two filters, both exclusions rather than preferences: the source must match the session's
    population, and the twin must have passed the H3 quality gate. A twin that failed the gate is
    dropped from the panel and from all cells — and is never tuned into passing.
    """
    if population not in POPULATION_SOURCES:
        raise PanelError(
            f"unknown population {population!r}; expected one of {sorted(POPULATION_SOURCES)}"
        )
    allowed = POPULATION_SOURCES[population]
    return [c for c in candidates if c.source in allowed and c.quality_passed]


def _allocate(sizes: dict[str, int], total_seats: int) -> dict[str, int]:
    """Seats per stratum, proportional to size, summing to exactly ``total_seats``.

    Largest-remainder allocation, with ties broken by stratum name so the result depends on the
    populations alone and not on dict ordering. A stratum smaller than its quota gives its surplus
    back and the remaining seats are re-allocated among strata that still have capacity, repeated
    until every seat is placed.
    """
    remaining = dict(sizes)
    seats: dict[str, int] = dict.fromkeys(sizes, 0)
    left = total_seats

    while left > 0:
        pool = {k: v - seats[k] for k, v in remaining.items() if v - seats[k] > 0}
        if not pool:
            raise InsufficientEligibleTwins(
                f"cannot place {left} more seat(s): every stratum is at capacity"
            )
        population = sum(pool.values())
        if left >= population:
            # Everyone left is needed; take them all and stop.
            for key, capacity in pool.items():
                seats[key] += capacity
            left -= population
            continue

        exact = {k: left * v / population for k, v in pool.items()}
        floors = {k: int(v) for k, v in exact.items()}
        placed = sum(floors.values())
        # Deterministic tie-break: larger remainder first, then stratum name.
        order = sorted(exact, key=lambda k: (-(exact[k] - floors[k]), k))
        for key in order[: left - placed]:
            floors[key] += 1
        for key, n in floors.items():
            seats[key] += n
        left = 0

    return seats


def draw_panel(
    candidates: Iterable[PanelCandidate],
    *,
    panel_size: int,
    panel_seed: int,
    population: str = "real",
) -> list[PanelMember]:
    """The panel, drawn once. `docs/03` §9.1. I14.

    Stratified on `city × service`, proportional to the eligible population, seeded, and returned
    with a draw ``position`` so it is reproducible from the seed alone.

    Determinism is deliberate at three points: strata are processed in sorted key order, members
    within a stratum are sorted by `twin_id` before sampling, and the allocation's ties break on
    the stratum name. Without all three, the same seed would give a different panel depending on
    the order rows came back from the database.
    """
    if panel_size < 1:
        raise PanelError(f"panel_size must be at least 1, got {panel_size}")

    pool = eligible_candidates(candidates, population)
    if not pool:
        raise InsufficientEligibleTwins(
            f"no eligible twins for population {population!r}: a panel of zero would make every "
            "run twins_n = 0, which is a failure and never a result (I15)"
        )
    if len(pool) < panel_size:
        raise InsufficientEligibleTwins(
            f"{len(pool)} eligible twin(s) for a panel of {panel_size}. Lower panel_size or "
            "quality-test more twins; a smaller panel recorded as "
            f"{panel_size} would misstate the study."
        )

    strata: dict[str, list[PanelCandidate]] = defaultdict(list)
    for candidate in pool:
        strata[candidate.stratum].append(candidate)

    seats = _allocate({k: len(v) for k, v in strata.items()}, panel_size)

    rng = random.Random(panel_seed)
    members: list[PanelMember] = []
    for stratum in sorted(strata):
        n = seats[stratum]
        if n == 0:
            continue
        ordered = sorted(strata[stratum], key=lambda c: c.twin_id)
        for candidate in rng.sample(ordered, n):
            members.append(
                PanelMember(
                    twin_id=candidate.twin_id, stratum=stratum, position=len(members)
                )
            )

    if len(members) != panel_size:  # pragma: no cover — _allocate guarantees this
        raise PanelError(f"drew {len(members)} of {panel_size}; allocation is wrong")
    return members


def panel_ids(panel: Iterable[PanelMember]) -> frozenset[str]:
    """The twin ids of a panel, order-independent. What comparability is judged on."""
    return frozenset(m.twin_id for m in panel)


def require_same_panel(*panels: tuple[str, Iterable[PanelMember]]) -> frozenset[str]:
    """Refuse a comparison across panels that are not the same set of twins. I14.

    Each argument is ``(label, panel)``, and the label is used in the error so the message names
    both panels (`docs/04` §9). Returns the shared twin id set when they agree.

    This is what an interaction calls before differencing three cells: `extra` is only meaningful
    when A, B and A∪B were answered by the same people (`docs/07` §5, `docs/03` §9.2).
    """
    if len(panels) < 2:
        raise PanelError("require_same_panel needs at least two panels to compare")

    first_label, first_panel = panels[0]
    reference_ids = panel_ids(first_panel)
    for label, panel in panels[1:]:
        ids = panel_ids(panel)
        if ids != reference_ids:
            only_first = sorted(reference_ids - ids)
            only_other = sorted(ids - reference_ids)
            raise PanelMismatch(
                f"{first_label} and {label} were answered by different twins, so they cannot be "
                f"differenced (I14). Only in {first_label}: {only_first or 'none'}. "
                f"Only in {label}: {only_other or 'none'}. "
                f"Sizes {len(reference_ids)} and {len(ids)}."
            )
    return reference_ids
