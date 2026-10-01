"""The export matrix. `docs/07` §11.

Replaces the prototype's Google Sheet. One row per respondent, every item on its **own** scale.

The header is **two rows**, and that is the whole point of this module. The prototype's export
claimed every item was 1–7; three of the nine constructs are 1–5 (`docs/01` §3.2), so every
downstream analysis that trusted the header was wrong about a third of the instrument. Carrying
``scale_id`` and ``points`` per column in the file itself makes that error impossible to repeat —
a downstream tool does not have to know the register, it can read the scale off the sheet.

Two more commitments from §11:

* **Construct means are pre-computed in Python** so a downstream tool cannot re-derive them with
  different reverse-coding (I12). The reversal is applied here, once, from the register.
* **`legacy_scale` rows are excluded by default** and pooling them takes an explicit override.
  They are answers on the prototype's 1–7 scale and are not comparable with the register's.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.stats import Population, Screening
from twinlab.stats.dataset import (
    SYNTHETIC_DATA_TYPE,
    reverse_if_needed,
    screen,
)

#: `docs/07` §11's respondent-level columns, before the item columns.
LEAD_COLUMNS: tuple[str, ...] = (
    "submission_id", "data_type", "city", "service", "arm",
    "female", "tenure_months",
)

#: `docs/07` §11's trailing columns, after the construct means.
TAIL_COLUMNS: tuple[str, ...] = (
    "eligible", "consented", "attention_passed", "speeder", "straight_liner",
    "mc_correct", "screened_out", "legacy_scale", "completion_seconds", "language",
)

#: What a column whose value is genuinely absent carries. Never ``0`` and never ``""`` for a
#: number — an empty cell in a statistics package is a missing value, a zero is a measurement.
ABSENT = ""


class ExportError(ValueError):
    """The export cannot be built. Never a partial sheet presented as a complete one."""


def item_columns(ref: ReferenceData | None = None) -> tuple[str, ...]:
    """Every register item, in register order. `docs/07` §11.

    All 73: the 37 battery items, the two attention checks, the 16 H2 and the 18 H3 holdouts.
    The attention checks are exported because they are the screening evidence — a reviewer must
    be able to recompute the screen — even though they are never put to a twin (I10).
    """
    ref = ref or reference()
    return tuple(ref.items.keys())


def header_rows(ref: ReferenceData | None = None) -> tuple[list[str], list[str]]:
    """The **two** header rows. `docs/07` §11.

    Row one is the column ids. Row two is ``scale_id`` and ``points`` for every item column, and
    a short type word for the others, so no cell in the sheet is unlabelled.
    """
    ref = ref or reference()
    items = item_columns(ref)
    constructs = tuple(ref.constructs)

    row1 = [*LEAD_COLUMNS, *items, *(f"{code}_mean" for code in constructs), *TAIL_COLUMNS]
    row2 = [*("" for _ in LEAD_COLUMNS)]
    for item_id in items:
        item = ref.items[item_id]
        row2.append(f"{item.scale_id} ({ref.scale_points(item_id)}-point)")
    for code in constructs:
        construct = ref.constructs[code]
        points = ref.scales[construct.scale_id].points
        row2.append(f"{construct.scale_id} ({points}-point) mean")
    row2 += ["" for _ in TAIL_COLUMNS]

    if len(row1) != len(row2):
        raise ExportError(
            f"the two header rows disagree: {len(row1)} ids vs {len(row2)} scale labels. "
            "Every column must carry its scale or the sheet repeats the prototype's error."
        )
    return row1, row2


def construct_mean(
    answers: dict[str, int], code: str, ref: ReferenceData
) -> float | None:
    """One construct's mean over its items, reverse-coded, on the items' own scale.

    Returns ``None`` when any item is missing rather than averaging a subset — the same rule as
    `analysis.metrics.score`. A mean over a subset is a number that looks like a measurement and
    is not (`docs/07` §2.3).
    """
    construct = ref.constructs[code]
    items = [
        item_id
        for item_id, item in ref.items.items()
        if item.block == construct.block
        and not item.attention_check
        and item.in_twin_battery
    ]
    values = [reverse_if_needed(i, answers[i], ref) for i in items if i in answers]
    if len(values) != len(items) or not values:
        return None
    return sum(values) / len(values)


def build_rows(
    submissions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    twins: list[dict[str, Any]] | None = None,
    *,
    population: Population = "both",
    screening: Screening = "none",
    pool_legacy: bool = False,
    ref: ReferenceData | None = None,
) -> list[list[Any]]:
    """The data rows, in submission order.

    ``screening`` defaults to ``none`` here and ``strict`` in the analysis matrix, deliberately:
    the export is the **evidence file** a reviewer recomputes the screen from, so it carries the
    screening flags and, by default, every respondent. The ``screened_out`` column says what a
    strict screen would have done without removing the row.
    """
    ref = ref or reference()
    items = item_columns(ref)
    constructs = tuple(ref.constructs)

    by_submission: dict[str, dict[str, int]] = {}
    text_answers: dict[str, dict[str, str]] = {}
    legacy_ids: set[str] = set()
    for row in answers:
        sid = str(row["submission_id"])
        if row.get("legacy_scale"):
            legacy_ids.add(sid)
        if row.get("value_num") is not None:
            by_submission.setdefault(sid, {})[str(row["item_id"])] = int(row["value_num"])
        elif row.get("value_text") is not None:
            text_answers.setdefault(sid, {})[str(row["item_id"])] = str(row["value_text"])

    twin_by_submission = {
        str(t.get("submission_id") or t.get("twin_id")): t for t in (twins or [])
    }

    out: list[list[Any]] = []
    for submission in submissions:
        sid = str(submission["submission_id"])
        is_synthetic = str(submission.get("data_type")).upper() == SYNTHETIC_DATA_TYPE
        if population == "real" and is_synthetic:
            continue
        if population == "synthetic" and not is_synthetic:
            continue
        is_legacy = sid in legacy_ids
        if is_legacy and not pool_legacy:
            continue

        numeric = by_submission.get(sid, {})
        text = text_answers.get(sid, {})
        twin = twin_by_submission.get(sid, {})
        reason = screen(submission, "strict")

        if screening == "strict" and reason:
            continue

        row: list[Any] = [
            sid,
            submission.get("data_type", ABSENT),
            submission.get("city") or ABSENT,
            submission.get("service") or ABSENT,
            submission.get("arm") or ABSENT,
            _female(twin.get("gender")),
            _absent_or(twin.get("tenure_months")),
        ]
        for item_id in items:
            if item_id in numeric:
                row.append(numeric[item_id])
            elif item_id in text:
                row.append(text[item_id])
            else:
                row.append(ABSENT)
        for code in constructs:
            row.append(_absent_or(construct_mean(numeric, code, ref)))
        row += [
            _bool(submission.get("eligible")),
            _bool(submission.get("consented")),
            _bool(submission.get("attention_passed")),
            _bool(submission.get("speeder")),
            _bool(submission.get("straight_liner")),
            _bool(submission.get("mc_correct")),
            _bool(bool(reason)),
            _bool(is_legacy),
            _absent_or(submission.get("completion_seconds")),
            submission.get("language") or ABSENT,
        ]
        out.append(row)
    return out


def _female(gender: Any) -> Any:
    """``1``/``0``, or absent. **Never a zero for an unstated gender** — that is a measurement."""
    if gender is None or str(gender).strip() == "":
        return ABSENT
    return 1 if str(gender).strip().lower().startswith("f") else 0


def _bool(value: Any) -> Any:
    return ABSENT if value is None else (1 if value else 0)


def _absent_or(value: Any) -> Any:
    return ABSENT if value is None else value


def to_csv(header: tuple[list[str], list[str]], rows: list[list[Any]]) -> str:
    """CSV with **both** header rows. `docs/06` §7."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header[0])
    writer.writerow(header[1])
    writer.writerows(rows)
    return buffer.getvalue()


def to_json(header: tuple[list[str], list[str]], rows: list[list[Any]]) -> str:
    """The raw JSON payload. Carries the scale row as data, not as a comment. `docs/06` §7."""
    return json.dumps(
        {
            "columns": header[0],
            "scales": header[1],
            "rows": rows,
            "note": (
                "Every item is on its own published scale; read the `scales` row rather than "
                "assuming 1-7. Construct means are pre-computed with reverse coding applied."
            ),
        },
        indent=2,
    )


def to_xlsx(header: tuple[list[str], list[str]], rows: list[list[Any]]) -> bytes:
    """XLSX with both header rows, via pandas. `docs/06` §7.

    Raises rather than silently degrading to CSV when no writer engine is installed: a researcher
    who asked for XLSX and received CSV under an ``.xlsx`` name has a file that lies about itself.
    """
    import pandas as pd

    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            frame = pd.DataFrame([header[1], *rows], columns=header[0])
            frame.to_excel(writer, index=False, sheet_name="responses")
    except (ImportError, ValueError) as exc:
        raise ExportError(
            f"no XLSX writer is available ({exc}). Use CSV or JSON rather than an .xlsx file "
            "that is not one."
        ) from exc
    return buffer.getvalue()
