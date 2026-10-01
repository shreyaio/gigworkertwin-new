"""The analysis matrix, built from human survey rows. `docs/07` §1, §7.1 and §11.

**Statistics never reads the sweep** (`docs/07` §1). The unit here is one human respondent and the
source is `survey_answers`; `twin_answers` is the counterfactual layer's table and is not touched
by anything in this module.

Four things here decide whether every downstream number is right:

1. **Reverse coding happens once, here, about each item's own scale's midpoint.** A five-point
   item reverses about 6 and a seven-point about 8. `docs/07` §10 names "a reverse-coded item not
   reversed before estimation" as one of the two faults the golden test must catch, and this is
   the only place in the measurement layer where it could go wrong.
2. **Screening is recorded, not just applied.** Every dropped respondent carries the reason, so
   `n_cases` is explicable and a screening rule chosen after seeing results stays visible
   (`docs/07` §7.1).
3. **`legacy_scale` rows are excluded by default** and pooling them takes an explicit override
   (`docs/07` §11). The prototype's 1–7 answers are not comparable with the register's scales.
4. **A respondent with any missing indicator is dropped whole, never imputed** (I17). PLS-SEM's
   casewise deletion is the honest option; a mean-filled cell is a fabricated measurement.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

from twinlab.db.client import DbBackend, get_backend
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.stats import CaseMatrix, ModelSpec, Population, Screening
from twinlab.stats.spec import ARM_REFERENCE, MODERATED, MODERATOR, build_model_spec

log = logging.getLogger(__name__)

#: `docs/07` §7.1. Under eight minutes is a speeder; the DDL computes this as a stored column.
SPEEDER_SECONDS = 480

#: `twins.source` / `survey_submissions.data_type` for generated rows.
SYNTHETIC_DATA_TYPE = "SYNTHETIC"


class DatasetError(ValueError):
    """The matrix cannot be built. Never a silently smaller or partially imputed one."""


class NoCasesError(DatasetError):
    """Screening left nothing. `analysis_has_cases` forbids an analysis run with `n_cases = 0`.

    The measurement-layer sibling of I15: a model estimated on nobody is not a weak result, it is
    not a result.
    """


def _population_matches(data_type: str | None, population: Population) -> bool:
    is_synthetic = str(data_type).upper() == SYNTHETIC_DATA_TYPE
    if population == "both":
        return True
    return is_synthetic if population == "synthetic" else not is_synthetic


def screen(
    submission: dict[str, Any], screening: Screening
) -> str | None:
    """Why this respondent is excluded, or ``None`` to keep them. `docs/07` §7.1.

    ``strict`` drops an attention failure, a speeder or a straight-liner. ``none`` keeps everyone.

    **Failing the Part 15 manipulation check never drops anyone**, under either rule. That switch
    is built and defaults off (`ARCHITECTURE.md` §10.2, decided 2026-09-28); `mc_correct` is
    captured and reported on Fieldwork so the decision can be revisited against data rather than
    in advance.
    """
    if not submission.get("consented", True):
        return "did not consent"
    if screening == "none":
        return None
    if not submission.get("attention_passed", True):
        return "failed an attention check"
    seconds = submission.get("completion_seconds")
    speeder = submission.get("speeder")
    if speeder is None and seconds is not None:
        speeder = int(seconds) < SPEEDER_SECONDS
    if speeder:
        return f"completed in under {SPEEDER_SECONDS // 60} minutes"
    if submission.get("straight_liner"):
        return "straight-lined the battery"
    return None


def reverse_if_needed(item_id: str, raw: int, ref: ReferenceData) -> int:
    """``(points + 1) - raw`` when the register flags the item reversed. `docs/07` §2.1.

    Reads the item's **own** scale, never the construct's, so a reverse-coded item that sits on a
    different scale from its block cannot be reversed about the wrong midpoint.
    """
    item = ref.items[item_id]
    if not item.reverse_coded:
        return raw
    return (ref.scale_points(item_id) + 1) - raw


def build_matrix(
    submissions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    *,
    population: Population = "real",
    screening: Screening = "strict",
    pool_legacy: bool = False,
    spec: ModelSpec | None = None,
    ref: ReferenceData | None = None,
) -> CaseMatrix:
    """Build the screened, reverse-coded, standardised analysis matrix.

    Pure: takes rows, returns a matrix. The database read lives in :func:`load_matrix` so every
    screening and coding rule here is testable without a backend.

    Column order is the model's own indicator order, then the arm dummies, then the interaction
    products — deterministic, so a stored payload's row order is reproducible across processes.
    """
    ref = ref or reference()
    spec = spec or build_model_spec(ref)

    by_submission: dict[str, dict[str, Any]] = {}
    legacy_ids: set[str] = set()
    for row in answers:
        sid = str(row["submission_id"])
        if row.get("legacy_scale"):
            legacy_ids.add(sid)
        value = row.get("value_num")
        if value is None:
            continue
        by_submission.setdefault(sid, {})[str(row["item_id"])] = int(value)

    item_columns = tuple(
        item
        for construct in spec.constructs
        if construct.reflective
        for item in construct.items
    )
    arm_columns = spec.construct("ARM").items

    kept: list[tuple[str, dict[str, int], str]] = []
    dropped: list[tuple[str, str]] = []
    legacy_excluded = 0

    for submission in submissions:
        sid = str(submission["submission_id"])
        if not _population_matches(submission.get("data_type"), population):
            continue

        if sid in legacy_ids and not pool_legacy:
            # docs/07 §11: excluded by default. Counted, not silently absent — the researcher must
            # be able to see how many rows an override would add.
            legacy_excluded += 1
            dropped.append((sid, "answered on the prototype's 1-7 scale (legacy_scale)"))
            continue

        reason = screen(submission, screening)
        if reason:
            dropped.append((sid, reason))
            continue

        raw = by_submission.get(sid, {})
        missing = [item for item in item_columns if item not in raw]
        if missing:
            # I17: casewise deletion, never imputation. The count is named so a systematically
            # missing block shows up as a screening figure rather than as a quiet sample shrink.
            dropped.append(
                (sid, f"missing {len(missing)} indicator(s), first {missing[0]}")
            )
            continue

        coded = {item: reverse_if_needed(item, raw[item], ref) for item in item_columns}
        kept.append((sid, coded, str(submission.get("arm") or ARM_REFERENCE)))

    if not kept:
        raise NoCasesError(
            f"screening left no cases (population={population}, screening={screening}, "
            f"{len(dropped)} dropped). An analysis run with n_cases = 0 is forbidden by "
            "analysis_has_cases; it is not a weak result, it is not a result."
        )

    columns = list(item_columns) + list(arm_columns)
    rows: list[list[float]] = []
    for _sid, coded, arm in kept:
        row = [float(coded[item]) for item in item_columns]
        row += [1.0 if f"arm_{arm}" == column else 0.0 for column in arm_columns]
        rows.append(row)

    columns, rows = _append_interaction(columns, rows, spec, ref)

    _assert_variance(columns, rows)

    log.info(
        "analysis matrix: %d case(s), %d dropped, %d legacy excluded, %d column(s)",
        len(rows), len(dropped), legacy_excluded, len(columns),
    )
    return CaseMatrix(
        columns=tuple(columns),
        rows=tuple(tuple(r) for r in rows),
        submission_ids=tuple(sid for sid, _, _ in kept),
        population=population,
        screening=screening,
        dropped=tuple(dropped),
        legacy_excluded=legacy_excluded,
    )


def _append_interaction(
    columns: list[str],
    rows: list[list[float]],
    spec: ModelSpec,
    ref: ReferenceData,
) -> tuple[list[str], list[list[float]]]:
    """Add the ``EDEP x SATI`` product indicators. `docs/07` §7.2.

    The standard product-indicator approach: each component is standardised **first**, then
    multiplied. Multiplying raw values instead would make the product's scale depend on where the
    two scales' origins happen to sit, and the interaction's loadings would be an artefact of that
    rather than of the moderation.
    """
    interaction = next(
        (c for c in spec.constructs if c.code.startswith(f"{MODERATOR}_x_")), None
    )
    if interaction is None:
        return columns, rows

    mod_items = spec.construct(MODERATOR).items
    tgt_items = spec.construct(MODERATED).items
    index = {name: i for i, name in enumerate(columns)}

    standardised: dict[str, list[float]] = {}
    for item in (*mod_items, *tgt_items):
        values = [row[index[item]] for row in rows]
        mean = statistics.fmean(values)
        sd = statistics.pstdev(values)
        if sd == 0:
            raise DatasetError(
                f"{item} has zero variance across {len(values)} case(s); its product indicators "
                "would be constant and the interaction term could not be estimated."
            )
        standardised[item] = [(v - mean) / sd for v in values]

    for name in interaction.items:
        mod_item, tgt_item = name.split("_x_")
        product = [
            standardised[mod_item][i] * standardised[tgt_item][i]
            for i in range(len(rows))
        ]
        columns.append(name)
        for i, row in enumerate(rows):
            row.append(product[i])
    return columns, rows


def _assert_variance(columns: list[str], rows: list[list[float]]) -> None:
    """Every column must vary. A constant indicator is a failure, never a zero-loading result.

    The engine standardises, so a constant column divides by zero and surfaces as ``NaN`` loadings
    several stages later — a plausible-looking table with a silently unidentified construct. This
    turns it into a named error at the point the matrix is built.
    """
    constant = [
        name
        for j, name in enumerate(columns)
        if len({row[j] for row in rows}) == 1
    ]
    if constant:
        raise DatasetError(
            f"{len(constant)} column(s) have no variance across {len(rows)} case(s): "
            f"{constant[:6]}. An indicator that never varies cannot be standardised and would "
            "reach the outer model as NaN rather than as an error."
        )


async def load_matrix(
    *,
    population: Population = "real",
    screening: Screening = "strict",
    pool_legacy: bool = False,
    spec: ModelSpec | None = None,
    backend: DbBackend | None = None,
) -> CaseMatrix:
    """Read the human rows and build the matrix. The only database access in `stats/`."""
    db = backend or get_backend()
    submissions = await db.select("survey_submissions", None)
    answers = await db.select("survey_answers", None)
    return build_matrix(
        list(submissions),
        list(answers),
        population=population,
        screening=screening,
        pool_legacy=pool_legacy,
        spec=spec,
    )
