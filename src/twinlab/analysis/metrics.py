"""Metric scoring, shifts and the index. `docs/07` §2–§4. Serves I12 and I17.

**No model produces any number here.** Every value is computed in Python from stored integers, and
the Analyst only ever writes prose *about* these numbers (I12).

Three things in this module are the ones most likely to silently corrupt the study:

1. **Reverse coding is about the item's own scale's midpoint.** Exactly three items are reversed —
   `SAT2`, `DEP1`, `H2_SAT2` — and a 5-point item reverses about 6 while a 7-point reverses about 8.
   Reversing everything about 8 silently corrupts three of the nine constructs.
2. **Five-point metrics are never rescaled to seven.** `clarity` and `staying` are reported on 1–5.
   Standardisation belongs to the modelling stage, never to a display metric.
3. **Shifts take one twin-id set and use it for both sides** (`docs/07` §3.1). Computing the
   baseline over the full panel and the variant over the survivors makes every failure look like an
   effect. This is the single most dangerous arithmetic error available in the counterfactual layer.

Everything is read from the frozen reference data — the metric definitions, the scale points, the
reverse-coded flags and the index signs. Nothing is a constant in this file.
"""

from __future__ import annotations

from collections.abc import Iterable

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.analysis import CellShifts, NoiseFloor


class MetricError(ValueError):
    """A metric that cannot be computed. Never silently skipped or partially computed."""


def reverse_code(value: int, points: int) -> int:
    """``(points + 1) - raw``, about **this item's own** scale's midpoint. `docs/07` §2.1."""
    return (points + 1) - value


def score(
    answers: dict[str, int], metric: str, ref: ReferenceData | None = None
) -> float:
    """The mean of one metric's items, on the items' own scale. `docs/07` §2.2.

    Raises on a missing item rather than averaging over a subset. `docs/07` §2.3: there are no
    missing items — a vector that reached storage passed the output contract and has exactly 37
    valid items, and one that did not is **absent, not partial**. A mean over a subset would be a
    number that looks like a measurement and is not.
    """
    ref = ref or reference()
    if metric not in ref.metrics:
        raise MetricError(f"unknown metric {metric!r}; expected one of {sorted(ref.metrics)}")
    definition = ref.metrics[metric]
    points = ref.scales[definition.scale].points

    values: list[int] = []
    for item_id in definition.items:
        if item_id not in answers:
            raise MetricError(
                f"{metric}: {item_id} is absent. No metric is ever computed over a subset — a "
                "vector that did not pass the output contract is absent, not partial "
                "(docs/07 §2.3)."
            )
        raw = answers[item_id]
        item = ref.items[item_id]
        # The item's OWN scale, not the metric's, because a reversed item could in principle sit on
        # a different scale from its block. Reading it per item is what makes that impossible to get
        # wrong.
        item_points = ref.scale_points(item_id) if item.scale_id else points
        values.append(reverse_code(raw, item_points) if item.reverse_coded else raw)

    return sum(values) / len(values)


def score_all(
    answers: dict[str, int], ref: ReferenceData | None = None
) -> dict[str, float]:
    """All six metrics for one vector, in the register's order."""
    ref = ref or reference()
    return {metric: score(answers, metric, ref) for metric in ref.metrics}


def mean_over_twins(
    vectors: dict[str, dict[str, int]],
    twin_ids: Iterable[str],
    metric: str,
    ref: ReferenceData | None = None,
) -> float:
    """The mean of one metric across an **explicit** twin set.

    ``twin_ids`` is a parameter rather than ``vectors.keys()`` on purpose: that is what lets the
    caller pass the *same* set to both sides of a shift (`docs/07` §3.1).
    """
    ids = list(twin_ids)
    if not ids:
        raise MetricError(
            f"{metric}: no twins. A metric over zero twins is not 0.0, it is no measurement "
            "(I15) — the run is failed, never completed."
        )
    ref = ref or reference()
    return sum(score(vectors[t], metric, ref) for t in ids) / len(ids)


def average_within_twin(
    repeats: dict[str, list[dict[str, int]]], ref: ReferenceData | None = None
) -> dict[str, dict[str, float]]:
    """Average a twin's several vectors for one cell **within twin first**. `docs/07` §3.2.

    With `runs_per_wording > 1` or multiple wordings a twin has more than one vector. Averaging
    across twins without collapsing within twin first gives a twin that was asked twice double
    weight, which silently reweights the panel.

    Returns ``twin_id → metric → mean score``, because a per-twin *score* average and a per-twin
    *answer* average are not the same thing once an item is reverse coded.
    """
    ref = ref or reference()
    out: dict[str, dict[str, float]] = {}
    for twin_id, vectors in repeats.items():
        if not vectors:
            raise MetricError(f"{twin_id} has no vectors for this cell")
        per_metric: dict[str, list[float]] = {}
        for vector in vectors:
            for metric, value in score_all(vector, ref).items():
                per_metric.setdefault(metric, []).append(value)
        out[twin_id] = {m: sum(v) / len(v) for m, v in per_metric.items()}
    return out


def compute_shifts(
    *,
    baseline_vectors: dict[str, dict[str, int]],
    variant_vectors: dict[str, dict[str, int]],
    version_code: str,
    weights: dict[str, float] | None = None,
    decimals: int = 3,
    ref: ReferenceData | None = None,
) -> CellShifts:
    """One cell's six shifts and its index. `docs/07` §3 and §4.

    **The twin set is the intersection, taken once and used for both sides** (`docs/07` §3.1). A
    twin that failed for this cell is excluded from the baseline as well as the variant;
    excluding it
    from only the variant side would make every failure look like an effect.

    ``baseline_vectors`` are the twins' **own survey answers**, so every driver is their own
    control.
    """
    ref = ref or reference()

    # One set, used twice. The whole of docs/07 §3.1 is this line and the two that consume it.
    twin_ids = sorted(set(baseline_vectors) & set(variant_vectors))
    if not twin_ids:
        raise MetricError(
            f"{version_code}: no twin answered both the baseline and this cell. A run with no "
            "twins is failed, never completed with an index of 0.000 (I15)."
        )

    baselines: dict[str, float] = {}
    shifts: dict[str, float] = {}
    for metric in ref.metrics:
        base = mean_over_twins(baseline_vectors, twin_ids, metric, ref)
        variant = mean_over_twins(variant_vectors, twin_ids, metric, ref)
        baselines[metric] = round(base, decimals)
        # Stored SIGNED. The sign flip for pushback and leaving happens only in the index.
        shifts[metric] = round(variant - base, decimals)

    return CellShifts(
        version_code=version_code,
        baselines=baselines,
        shifts=shifts,
        index_value=compute_index(shifts, weights=weights, decimals=decimals, ref=ref),
        twin_ids=twin_ids,
        weights=dict(weights or {}),
    )


def compute_index(
    shifts: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
    decimals: int = 3,
    ref: ReferenceData | None = None,
) -> float:
    """The headline number for one cell. `docs/07` §4.

    ``index = mean([fairness, clarity, happiness, staying, -pushback, -leaving])``

    The flip for `pushback` and `leaving` comes from `constructs.index_sign` in the **frozen**
    reference data, not from a list here and not from config: less of each is better for the driver,
    and that is a property of the construct, not a setting.

    A weight of ``0`` omits a metric and the index becomes the weighted mean over the non-zero
    weights. The default is unweighted, and that is what the paper reports (`docs/07` §4.1).
    """
    ref = ref or reference()
    signs = {
        c.metric_name: c.index_sign
        for c in ref.constructs.values()
        if c.index_sign is not None
    }

    numerator = 0.0
    denominator = 0.0
    for metric, value in shifts.items():
        if metric not in signs:
            raise MetricError(
                f"{metric!r} has no index sign in the frozen constructs; it cannot enter the index"
            )
        weight = 1.0 if weights is None else float(weights.get(metric, 1.0))
        if weight == 0:
            continue
        numerator += weight * signs[metric] * value
        denominator += weight

    if denominator == 0:
        raise MetricError(
            "every index weight is zero, so there is no index. A weight of 0 omits a metric; "
            "omitting all six is not an unweighted index, it is no measurement."
        )
    return round(numerator / denominator, decimals)


def measure_noise_floor(
    *,
    baseline_vectors: dict[str, dict[str, int]],
    control_vectors: dict[str, dict[str, int]],
    decimals: int = 4,
    ref: ReferenceData | None = None,
) -> NoiseFloor | None:
    """How much a twin moves when nothing changed, at both levels. `docs/07` §6.

    Measured from the `00000` control's own answers rather than read off its stored
    ``index_value``. **This replaced ``|index(00000)|`` on 2026-10-07** (`docs/DECISIONS.md`): the
    index applies `index_sign` and averages the six metrics, so a floor taken from it is an
    absolute-of-a-signed-mean, while every statistic it gates is a mean-of-absolutes. By Jensen the
    former can never exceed the latter, which made every floor-judged test lean toward `FAIL`.

    **The twin set is the intersection, taken once and used for both sides** (`docs/07` §3.1), for
    the same reason :func:`compute_shifts` takes it once.

    ``None`` when no twin answered both the control and its own baseline — a floor is measured or
    it is absent, never assumed.
    """
    ref = ref or reference()
    twin_ids = sorted(set(baseline_vectors) & set(control_vectors))
    if not twin_ids:
        return None

    cell_by_metric: dict[str, float] = {}
    twin_by_metric: dict[str, float] = {}
    for metric in ref.metrics:
        deltas = [
            score(control_vectors[t], metric, ref) - score(baseline_vectors[t], metric, ref)
            for t in twin_ids
        ]
        # The two functionals, taken over the same deltas: the cell moves by the mean, a twin
        # moves by the size of its own delta regardless of which way it went.
        cell_by_metric[metric] = round(abs(sum(deltas) / len(deltas)), decimals)
        twin_by_metric[metric] = round(sum(abs(d) for d in deltas) / len(deltas), decimals)

    return NoiseFloor(
        cell=round(sum(cell_by_metric.values()) / len(cell_by_metric), decimals),
        twin=round(sum(twin_by_metric.values()) / len(twin_by_metric), decimals),
        cell_by_metric=cell_by_metric,
        twin_by_metric=twin_by_metric,
        twins_n=len(twin_ids),
    )


def demand_floor(index_sham: float | None, index_00000: float | None) -> float | None:
    """``index(SHAM) − index(00000)``. `docs/07` §6.

    **A cell whose index does not exceed this is not interpretable**, and the Analyst is required to
    say so. Both floors are computed per session from that session's panel and **never pooled across
    sessions** — a floor from a different panel describes different twins.

    ``None`` when either control is missing: a floor is not assumed, and a cell reported against an
    assumed floor is reported against nothing.
    """
    if index_sham is None or index_00000 is None:
        return None
    return round(index_sham - index_00000, 3)


def below_floor(index_value: float | None, floor: float | None) -> bool | None:
    """Whether a cell fails to clear the demand floor. ``None`` when either is unknown.

    ``None`` rather than ``False``: "we did not measure the floor" and "this cell clears the floor"
    are different claims, and only one of them supports a finding.
    """
    if index_value is None or floor is None:
        return None
    return index_value <= floor
