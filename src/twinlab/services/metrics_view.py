"""`metric_bars` and the grid, assembled for the UI. `docs/05` §4.5, `docs/06` §3.7.

**The colour rule is the whole point of this module.** `docs/05` §4.5: a bar is coloured by
"good for the driver", not by sign. `leaving −0.59` extends left and is **green**; `pushback +1.20`
extends right and is **red**. Getting it backwards inverts the headline finding on every screen
that shows it, so the decision is made exactly once — here, from `constructs.index_sign` in the
**frozen** reference data — and `ui/` only paints what it is handed.

Nothing in this module computes a metric. Shifts and the index arrive already computed by
`analysis/metrics.py` (I12, `docs/05` §8.4 rule 5); what happens here is scaling a bar to the
widest value on screen and turning a float into the string beside it.
"""

from __future__ import annotations

from twinlab.analysis.interactions import describe, describe_missing, interaction
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.analysis import Interaction
from twinlab.models.view import (
    GridCell,
    InteractionRow,
    MetricBars,
    MetricRow,
    TestedVersionRow,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, all_codes, validate_code

#: Display labels for the six index metrics, in `docs/06` §3.7's column order.
METRIC_LABELS: dict[str, str] = {
    "fairness": "Fairness",
    "clarity": "Clarity",
    "happiness": "Happiness",
    "staying": "Staying",
    "pushback": "Pushback",
    "leaving": "Leaving",
}

#: The empty state `docs/05` §5 requires: why it is empty, and the one action that fixes it.
NO_VERSIONS_EMPTY = (
    "No tested versions yet. Set the dials and press Ask the twins, or let the agents "
    "choose six versions."
)


def metric_order(ref: ReferenceData | None = None) -> list[str]:
    """The six index metrics in construct order. Read from frozen data, never hard-coded here."""
    ref = ref or reference()
    return [c.metric_name for c in ref.constructs.values() if c.metric_name is not None]


def index_signs(ref: ReferenceData | None = None) -> dict[str, int]:
    """metric → ``+1`` or ``−1``, from `constructs.index_sign`.

    Deliberately not a list in this file and not a config key: a researcher editing a config must
    not be able to invert what a metric means (`docs/07` §4.1).
    """
    ref = ref or reference()
    return {
        c.metric_name: c.index_sign
        for c in ref.constructs.values()
        if c.metric_name is not None and c.index_sign is not None
    }


def build_metric_bars(
    shifts: dict[str, float] | None,
    *,
    index_value: float | None = None,
    twins_n: int = 0,
    version_code: str = "",
    floor: float | None = None,
    floor_kind: str = "demand",
    ref: ReferenceData | None = None,
) -> MetricBars:
    """Six rows, the index and a plain sentence. `docs/05` §4.5.

    ``shifts`` of ``None`` is an untested cell and every row reads ``Not tested``. A cell with no
    twins is never rendered as an index of 0.000 (I15) — ``twins_n = 0`` carries no index, because
    a failed run has none to carry.

    Bars scale to the largest absolute shift **on this screen**, so rows are comparable within a
    view; every row still carries its number, and the bar is redundant encoding, never the only
    encoding (`docs/05` §6).
    """
    ref = ref or reference()
    signs = index_signs(ref)
    order = metric_order(ref)

    values = {} if shifts is None else shifts
    present = [abs(v) for m, v in values.items() if m in signs and v is not None]
    widest = max(present) if present else 0.0

    rows: list[MetricRow] = []
    for metric in order:
        value = values.get(metric)
        if value is None:
            rows.append(
                MetricRow(metric=metric, label=METRIC_LABELS.get(metric, metric))
            )
            continue
        rows.append(
            MetricRow(
                metric=metric,
                label=METRIC_LABELS.get(metric, metric),
                value=value,
                value_text=f"{value:+.2f}",
                # The colour rule. Not `value > 0`.
                good_for_driver=(signs[metric] * value) > 0 if value else None,
                bar_pct=0.0 if widest == 0 else round(abs(value) / widest * 100.0, 2),
            )
        )

    tested = shifts is not None and twins_n > 0
    index_text = "Not tested" if not tested or index_value is None else f"{index_value:.3f}"

    if not tested:
        caption = NO_VERSIONS_EMPTY if not version_code else f"{version_code} has not been tested."
    else:
        direction = (
            "better for drivers than Uber today"
            if (index_value or 0) > 0
            else "worse for drivers than Uber today"
            if (index_value or 0) < 0
            else "no different from Uber today"
        )
        caption = (
            f"Version {version_code}: {twins_n} twins answered. "
            f"On the index this is {direction}."
        )

    floor_note = None
    if tested and floor is not None and index_value is not None and index_value <= floor:
        label = "demand floor (SHAM − 00000)" if floor_kind == "demand" else "noise floor (00000)"
        floor_note = (
            f"This index ({index_value:.3f}) does not clear the {label} of {floor:.3f}, "
            "so it is not interpretable as an effect."
        )

    return MetricBars(
        rows=rows,
        index_value=index_value if tested else None,
        index_text=index_text,
        twins_n=twins_n,
        caption=caption,
        floor_note=floor_note,
    )


def grid_position(version_code: str) -> tuple[int, int]:
    """`docs/05` §8.3's mapping, 9 rows × 27 columns."""
    validate_code(version_code)
    pay, conditions, contracts, management, representation = (int(d) for d in version_code)
    return pay * 3 + conditions, contracts * 9 + management * 3 + representation


def build_grid(
    index_by_code: dict[str, float | None],
) -> list[GridCell]:
    """All 243 cells, tested or not. `docs/06` §3.7.

    Two outlines carry meaning and both are repeated in the accessible name, because the grid may
    never encode anything by colour alone (`docs/05` §6): `00000` is the red "Uber today" control,
    and the best index carries the gold outline.
    """
    tested = {c: v for c, v in index_by_code.items() if v is not None}
    best = max(tested, key=lambda c: tested[c]) if tested else None
    # The colour scale is relative to the cells tested so far, so a half-finished sweep still
    # separates its results instead of painting them all one shade. `high == low` (one result, or
    # several identical) gives every tested cell the full depth rather than dividing by zero.
    low = min(tested.values()) if tested else 0.0
    high = max(tested.values()) if tested else 0.0
    span = high - low

    cells: list[GridCell] = []
    for code in all_codes():
        row, col = grid_position(code)
        value = index_by_code.get(code)
        outline = (
            "control" if code == CONTROL_CODE else "best" if code == best else None
        )
        if value is None:
            name = f"version {code}, not tested"
        else:
            name = f"version {code}, index {value:.3f}"
        if outline == "control":
            name += ", Uber today"
        elif outline == "best":
            name += ", best so far"
        cells.append(
            GridCell(
                version_code=code,
                row=row,
                col=col,
                index_value=value,
                tested=value is not None,
                outline=outline,
                intensity=(
                    None if value is None else (1.0 if span <= 0 else (value - low) / span)
                ),
                accessible_name=name,
            )
        )
    return cells


def build_tested_table(
    rows: list[TestedVersionRow], *, search: str = ""
) -> list[TestedVersionRow]:
    """The grid's linear, screen-readable equivalent (`docs/05` §6), sorted by index descending.

    ``search`` filters on version code only, as `docs/06` §3.7 specifies. Sorting happens here so
    the table and the grid's gold outline can never disagree about which cell is best.
    """
    needle = search.strip()
    kept = [r for r in rows if not needle or needle in r.version_code]
    return sorted(
        kept, key=lambda r: (r.index_value is None, -(r.index_value or 0.0), r.version_code)
    )


def build_interaction_rows(
    code: str,
    shifts_by_code: dict[str, dict[str, float]],
    *,
    metric: str = "fairness",
    panels_by_code: dict[str, frozenset[str]] | None = None,
    candidates: list[str] | None = None,
) -> list[InteractionRow]:
    """Interactions involving ``code``, **including the ones that cannot be computed**. I17.

    A missing leg is rendered as the sentence naming the code to run, never as an estimate and
    never as a blank (`CLAUDE.md` rule 5). That is why this returns rows for incomputable pairs
    rather than filtering them out the way the analyst bundle does.
    """
    others = candidates if candidates is not None else sorted(shifts_by_code)
    out: list[InteractionRow] = []
    for other in others:
        if other == code:
            continue
        result = interaction(
            code, other, metric, shifts_by_code, panels_by_code=panels_by_code
        )
        if isinstance(result, Interaction):
            out.append(
                InteractionRow(
                    a=result.a,
                    b=result.b,
                    joint=result.joint,
                    metric=metric,
                    computable=True,
                    text=describe(result),
                )
            )
        else:
            out.append(
                InteractionRow(
                    a=result.a,
                    b=result.b,
                    joint=result.joint,
                    metric=metric,
                    computable=False,
                    text=describe_missing(result),
                    missing_codes=list(result.missing_codes),
                )
            )
    return out
