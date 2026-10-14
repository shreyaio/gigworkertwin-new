"""Twin Lab's readers: twins, validation, validity, fieldwork, settings. `docs/06` §3.3–§3.8.

Everything here returns a view model from `models/view.py`. `ui/` may reach `services/` and
`models/` and nothing lower (`ARCHITECTURE.md` §4), so this module is where the database shapes
stop and the screen shapes begin.

The parts that are research commitments rather than plumbing:

* **`Not tested` is a value.** A twin compared against a version with no completed run shows that
  string. Never a neighbour's number, never the baseline, never a blank that reads as a zero (I17).
* **The Twins side panel order is mandatory** and one step of it matters: the scenario text comes
  *before* the answers, so a reader sees what the twin was told before reading what it said
  (`docs/06` §3.3).
* **Validation carries an "Arm seen" column** because H2 validation must show a twin its own
  driver's arm (`docs/01` §5). A mismatch there is a bug, and the column is how it is caught.
* **A validity verdict on zero twins is `INCONCLUSIVE`** (I15), enforced by the DDL and asserted
  again here so an impossible row cannot be rendered as a pass.
* **Evidence is never deletable from the UI** (I9). There is no "clear runs" function in this
  module, and :data:`CLEAR_RUNS_NOTE` is the sentence that stands where the prototype had a button.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, StorageBackend, get_backend, get_storage
from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.reference import CONSTRUCTS
from twinlab.models.twin import SurveyResponse, Twin
from twinlab.models.validity import assert_not_ablated
from twinlab.models.view import (
    BASELINE_MEASURED,
    BASELINE_NOT_MEASURED,
    AnswerCompareBlock,
    AnswerCompareRow,
    StatusRow,
    TwinImportResult,
    TwinPanel,
    TwinRow,
    ValidationRow,
    ValidationSummary,
    ValidityResultRow,
    ValidityTestCard,
)
from twinlab.orchestrator.odometer import CONTROL_CODE
from twinlab.persona.builder import build_persona
from twinlab.persona.from_payload import twin_from_payload
from twinlab.services.dials import what_twins_are_told  # noqa: F401  (re-exported below)
from twinlab.services.generator import REAL_DATA_TYPE

log = logging.getLogger(__name__)

#: `docs/06` §3.8 and `docs/05` §5.1. The card that stands where the prototype had a button.
CLEAR_RUNS_NOTE = (
    "Runs, agent messages, twin answers, quality runs and validity results are append-only "
    "evidence. Clearing them is a database operation a researcher performs deliberately, not a "
    "button in this application."
)

#: `docs/06` §3.4's mandatory warning. Shown whenever the checked set includes synthetic twins.
SYNTHETIC_WARNING = (
    "Some of these twins come from synthetic surveys. The generator and the mock twin share the "
    "same built-in reaction rules, so validation on synthetic data always looks good. It tests "
    "the machinery, not whether twins are valid."
)

#: `docs/06` §2. The instrument's most load-bearing property, stated on the survey page.
HOLDOUT_NOTE = (
    "Parts 15, 16 and 17 are holdout material and never enter a persona (I6). They are how a "
    "twin is checked against its own driver; a twin that had seen them would be checking itself."
)

#: The eight tests of `docs/06` §3.5. Definitions, statistics and pass rules are `docs/08` §4's,
#: deliberately not restated here — two copies of a pass rule is one copy too many.
VALIDITY_TESTS: tuple[ValidityTestCard, ...] = (
    ValidityTestCard(
        number=1, name="Wrong person", question="Is a twin really about its own driver?",
        what_it_does="Scores each twin against a different driver's holdout answers and compares "
        "the error with its own.",
        # NOT `needs_live_model`. `docs/08` §4 test 1: it "needs no new model calls — it re-scores
        # stored vectors — so it should be run early and often", and `docs/11` M13 requires zero
        # calls to be asserted on the call counter. The flag drives an amber "needs a live AI
        # model" badge, so leaving it True told the researcher the opposite of the truth about the
        # single most important test of the eight.
        needs_live_model=False,
    ),
    ValidityTestCard(
        number=2, name="Placebo change", question="Do twins welcome any change at all?",
        what_it_does="Runs the SHAM cell, which announces what Uber already does, and checks the "
        "index against 00000.", needs_live_model=True,
    ),
    ValidityTestCard(
        number=3, name="Beating simple guesses",
        question="Do twins beat ordinary statistics?",
        # `docs/08` §4 test 3's two naive predictors are **no change** and **group average
        # shift**, not a regression and a nearest neighbour. The card described a different test.
        what_it_does="Compares twin error with two naive predictors on the same items: the "
        "driver's own unchanged baseline, and that baseline plus the mean shift of the other "
        "respondents in their arm.",
    ),
    ValidityTestCard(
        number=4, name="Impossible version", question="Do twins notice a contradiction?",
        what_it_does="Presents a self-contradicting scenario and checks whether the twin flags it "
        "rather than answering smoothly.", needs_live_model=True,
    ),
    ValidityTestCard(
        number=5, name="Order and wording swap",
        question="Are answers about the change, or about the words?",
        what_it_does="Re-asks the same cell with a second wording and a permuted lever order, and "
        "compares.", needs_live_model=True,
    ),
    ValidityTestCard(
        number=6, name="Leave out the fairness items",
        question="Does the twin use its memory?",
        what_it_does="Rebuilds the persona without the fairness block and measures how far the "
        "fairness answers move — against the same twin asked twice on its real persona, so a twin "
        "that simply answers differently each time is not mistaken for one using its history.",
        needs_live_model=True,
    ),
    ValidityTestCard(
        number=7, name="A second AI model",
        question="Is the finding about the drivers or the model?",
        what_it_does="Re-runs the same cell on a second model with the same personas, and "
        "compares the per-twin index and every metric's sign. A sign flip is the failure that "
        "matters.",
        needs_live_model=True,
    ),
    ValidityTestCard(
        number=8, name="Temperature sweep", question="How much is chance?",
        what_it_does="Re-runs one cell across temperatures and reports the spread. This is what "
        "sets the twin temperature; it is measured, not chosen.", needs_live_model=True,
    ),
)

#: `docs/06` §3.6's data-quality rows, each read from `survey_submissions` (`docs/01` §6.2).
FIELDWORK_QUALITY_ROWS: tuple[tuple[str, str], ...] = (
    ("Agreed to a twin (statement 7)", "consent_twin"),
    ("Failed an attention check", "attention_passed"),
    ("Finished in under 8 minutes", "speeder"),
    ("Straight-lined", "straight_liner"),
    ("Failed the manipulation check (Part 15)", "mc_correct"),
    ("Not eligible", "eligible"),
    ("Did not consent", "consented"),
)

#: Rows above whose count is of the FALSE case. Reading these the other way round would report
#: every compliant respondent as a failure.
_NEGATED = {"attention_passed", "mc_correct", "eligible", "consented", "consent_twin"}


# ------------------------------------------------------------------ twins


def _identity_line(twin: dict) -> str:
    """`docs/06` §3.3 step 1, e.g. *Uber Go (cab) driver in Mumbai, 41 years, Man, 38 months on
    Uber, about 72 hours a week.*"""
    parts = [p for p in (twin.get("service"), twin.get("city")) if p]
    head = " driver in ".join(parts) if len(parts) == 2 else (parts[0] if parts else "Driver")
    bits = [head]
    if twin.get("age"):
        bits.append(f"{twin['age']} years")
    if twin.get("gender"):
        bits.append(str(twin["gender"]))
    if twin.get("tenure_months"):
        bits.append(f"{twin['tenure_months']} months on Uber")
    if twin.get("hours_per_week"):
        bits.append(f"about {twin['hours_per_week']} hours a week")
    return ", ".join(bits) + "."


async def _latest_quality(
    twin_id: str, holdout: str, db: DbBackend
) -> dict | None:
    rows = await db.select(
        "twin_quality_runs",
        [
            ("eq", "twin_id", twin_id),
            ("eq", "is_latest", True),
            ("eq", "holdout_set", holdout),
        ],
        order=("created_at", True),
        limit=1,
    )
    return rows[0] if rows else None


def _quality_text(row: dict | None) -> tuple[str, str]:
    """``Kept (0.56)`` / ``Dropped (1.1)``.

    The number is always beside the colour (`docs/05` §6, "never colour alone").
    """
    if row is None:
        return "Not run", "pending"
    mae = float(row.get("mae") or 0.0)
    return (
        (f"Kept ({mae:.2f})", "complete") if row.get("kept") else (f"Dropped ({mae:.2f})", "failed")
    )


async def twin_rows(
    *,
    source: str | None = None,
    city: str | None = None,
    service: str | None = None,
    quality: str | None = None,
    backend: DbBackend | None = None,
) -> list[TwinRow]:
    """The Twins list. Columns in `docs/06` §3.3 order, with its four filters."""
    db = backend or get_backend()
    filters: list = []
    if source:
        filters.append(("eq", "source", source))
    if city:
        filters.append(("eq", "city", city))
    if service:
        filters.append(("eq", "service", service))

    rows = await db.select("twins", filters or None, order=("twin_id", False))
    out: list[TwinRow] = []
    for twin in rows:
        text, state = _quality_text(await _latest_quality(twin["twin_id"], "H3", db))
        if quality == "kept" and state != "complete":
            continue
        if quality == "dropped" and state != "failed":
            continue
        if quality == "not_run" and state != "pending":
            continue
        out.append(
            TwinRow(
                twin_id=twin["twin_id"],
                service=str(twin.get("service") or ""),
                city=str(twin.get("city") or ""),
                age=str(twin.get("age") or ""),
                source=str(twin.get("source") or ""),
                quality_text=text,
                quality_state=state,
            )
        )
    return out


async def comparable_codes(backend: DbBackend | None = None) -> list[str]:
    """Codes with a completed run, newest first. The side panel's *Compare with version* list.

    `00000` is excluded: it **is** the "Twin today" column, so offering it as a comparison would
    invite comparing a cell with itself.
    """
    db = backend or get_backend()
    rows = await db.select(
        "runs", [("eq", "status", "completed")], order=("started_at", True)
    )
    seen: list[str] = []
    for row in rows:
        code = row.get("version_code")
        if code and code != CONTROL_CODE and code not in seen and row.get("twins_n"):
            seen.append(code)
    return seen


async def _answers_for(
    twin_id: str, version_code: str, db: DbBackend
) -> dict[str, int] | None:
    """One twin's answer vector for one code, or ``None`` when that code has no completed run."""
    runs = await db.select(
        "runs",
        [("eq", "version_code", version_code), ("eq", "status", "completed")],
        order=("started_at", True),
    )
    for run in runs:
        rows = await db.select(
            "twin_answers",
            [("eq", "run_id", run["run_id"]), ("eq", "twin_id", twin_id)],
            order=("created_at", True),
            limit=1,
        )
        if rows:
            return dict(rows[0]["answers"])
    return None


async def _driver_answers(twin_id: str, db: DbBackend) -> dict[str, int]:
    """The human's own survey answers. ``twin_id`` matches ``submission_id`` by convention."""
    rows = await db.select("survey_answers", [("eq", "submission_id", twin_id)])
    return {
        r["item_id"]: r["value_num"] for r in rows if r.get("value_num") is not None
    }


def _compare_blocks(
    driver: dict[str, int],
    baseline: dict[str, int] | None,
    variant: dict[str, int] | None,
    ref: ReferenceData,
) -> list[AnswerCompareBlock]:
    """One table per construct block, in battery order. `docs/06` §3.3.

    Holdout items are marked ``hidden`` rather than omitted: the reader needs to see that the
    twin never had them (I6), and a silently missing row looks like a bug in the table.
    """
    blocks: list[AnswerCompareBlock] = []
    for construct in CONSTRUCTS:
        items = [
            item
            for item in ref.items.values()
            if item.block == construct.block and item.in_twin_battery
        ]
        if not items:
            continue
        rows = [
            AnswerCompareRow(
                item_id=item.item_id,
                question=item.stem,
                driver=driver.get(item.item_id),
                baseline=None if baseline is None else baseline.get(item.item_id),
                variant=None if variant is None else variant.get(item.item_id),
                hidden=item.role in ("holdout_h2", "holdout_h3"),
            )
            for item in items
        ]
        blocks.append(
            AnswerCompareBlock(
                construct_code=construct.code, label=construct.label, rows=rows
            )
        )
    return blocks


async def twin_panel(
    twin_id: str,
    *,
    version_code: str | None = None,
    backend: DbBackend | None = None,
    ref: ReferenceData | None = None,
) -> TwinPanel:
    """The Twins side panel, in the mandatory seven-step order of `docs/06` §3.3.

    Step 6 (scenario text) precedes step 7 (the answers) deliberately: the reader must see what
    the twin was told before reading what it said.
    """
    db = backend or get_backend()
    ref = ref or reference()

    rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
    if not rows:
        raise KeyError(f"no twin {twin_id!r}")
    twin = rows[0]

    h3 = await _latest_quality(twin_id, "H3", db)
    if h3 is None:
        # Named as not run, not as failed. A twin with no quality row has not been tested; it has
        # not been dropped, and the panel must not read as though it had (I15's spirit applied to
        # a screen).
        quality_line = (
            "Quality test: not run. Run it on the Twins tab; the verdict lands here and on the "
            "Validation tab."
        )
    else:
        quality_line = (
            f"Quality test: average error {float(h3['mae']):.2f}, "
            f"{float(h3['pct_within_1']) * 100:.0f}% within 1 point."
        )

    baseline = await _answers_for(twin_id, CONTROL_CODE, db)
    variant = (
        await _answers_for(twin_id, version_code, db) if version_code else None
    )

    scenario: list[str] = []
    if version_code:
        scenario = await scenario_paragraphs(version_code, backend=db)

    background = twin.get("background") or {}
    background_line = (
        background.get("summary", "") if isinstance(background, dict) else str(background)
    )

    return TwinPanel(
        twin_id=twin_id,
        identity=_identity_line(twin),
        background=background_line,
        quality_line=quality_line,
        persona_text=str(twin.get("persona_passage") or ""),
        persona_hash=str(twin.get("persona_hash") or ""),
        compare_codes=await comparable_codes(db),
        selected_code=version_code,
        scenario_text=scenario,
        blocks=_compare_blocks(
            await _driver_answers(twin_id, db), baseline, variant, ref
        ),
        not_tested=bool(version_code) and variant is None,
        # WP-10. `baseline` is the twin's own vector for the `00000` control cell — its noise
        # floor, and the thing every shift on this screen is measured against. Empty means the
        # control has not been run for this twin, which is the expected state until a session
        # has run and is **not** the same as the twin having declined.
        baseline_state=BASELINE_MEASURED if baseline else BASELINE_NOT_MEASURED,
    )


async def scenario_paragraphs(
    version_code: str, *, backend: DbBackend | None = None
) -> list[str]:
    """The five lever paragraphs actually rendered for a code, in lever order.

    **The stored variant, never a re-render.** `docs/09` §2: what the twins saw is what is shown,
    and a paragraph re-rendered now could differ from the one that was used.
    """
    db = backend or get_backend()
    # Both halves of `(version_code, style_version)`. Two style versions now exist, so a lookup on
    # the code alone returns whichever row was written last — which may be a paragraph no twin was
    # ever shown. A *historical* run is read back by `variant_id` instead (`services/results.py`),
    # which is what keeps `docs/09` §2 true when the contract moves again.
    rows = await db.select(
        "variants",
        [("eq", "version_code", version_code), ("eq", "style_version", settings.style_version)],
        order=("created_at", True),
        limit=1,
    )
    if not rows:
        return []
    paragraphs = rows[0].get("paragraphs") or {}
    from twinlab.models.reference import LEVER_BY_POSITION

    out: list[str] = []
    for lever in LEVER_BY_POSITION:
        entry = paragraphs.get(lever)
        if isinstance(entry, dict):
            entry = entry.get("text", "")
        if entry:
            out.append(str(entry))
    return out


# ------------------------------------------------------------------ validation


async def validation_view(
    backend: DbBackend | None = None,
) -> tuple[ValidationSummary, list[ValidationRow]]:
    """`docs/06` §3.4's summary card and per-twin table.

    Part numbers are the canonical 16 and 17. The prototype's *Part 10 / 10b / 9b* are its own
    survey numbering, and **Part 9b does not exist in 2.0** — the item-level holdout was dropped,
    so that row is gone rather than renamed.
    """
    db = backend or get_backend()
    h2_rows = await db.select(
        "twin_quality_runs", [("eq", "is_latest", True), ("eq", "holdout_set", "H2")]
    )
    h3_rows = await db.select(
        "twin_quality_runs", [("eq", "is_latest", True), ("eq", "holdout_set", "H3")]
    )
    h3_by_twin = {r["twin_id"]: r for r in h3_rows}

    twins = {r["twin_id"] for r in h2_rows} | set(h3_by_twin)
    synthetic = False
    for twin_id in twins:
        rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
        if rows and rows[0].get("source") == "synthetic":
            synthetic = True
            break

    def mean(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 3) if values else None

    out_rows: list[ValidationRow] = []
    for row in sorted(h2_rows, key=lambda r: r["twin_id"]):
        detail = row.get("detail") or {}
        h3 = h3_by_twin.get(row["twin_id"]) or {}
        h3_detail = h3.get("detail") or {}
        # The per-outcome `r` is written to the `correlations` column, keyed by metric name
        # (`fairness`, `pushback`, `staying`), not into `detail`. Reading `detail["fairness_r"]`
        # found nothing, so every r rendered as *Not tested* although the test had run.
        h3_corr = h3.get("correlations") or {}
        out_rows.append(
            ValidationRow(
                twin_id=row["twin_id"],
                # Read from the `arm` COLUMN, which `quality_h2_arm` makes non-null on every H2
                # row, not from the free-form detail blob. Required, not optional: a blank here
                # hides exactly the bug the column exists to catch (`docs/01` §5).
                arm_seen=str(row.get("arm") or detail.get("arm_seen") or "unknown"),
                h2_error=float(row["mae"]) if row.get("mae") is not None else None,
                within_one=(
                    float(row["pct_within_1"]) if row.get("pct_within_1") is not None else None
                ),
                versions=int(h3_detail.get("versions") or 0),
                h3_error=float(h3["mae"]) if h3.get("mae") is not None else None,
                fairness_r=h3_corr.get("fairness"),
                pushback_r=h3_corr.get("pushback"),
                staying_r=h3_corr.get("staying"),
            )
        )

    # WP-7. Two facts the tab could not state: how many twins exist at all (so the empty state
    # can say "0 of 50" rather than "nothing"), and which H3 protocol produced the rows — because
    # six-in-one-context and six-in-isolation are different measurements and a table that mixes
    # them silently is worse than one that is empty.
    protocols = sorted(
        {
            str((row.get("detail") or {}).get("protocol") or "unrecorded")
            for row in h3_rows
        }
    )
    summary = ValidationSummary(
        twins_checked=len(twins),
        twins_total=await db.count("twins", None),
        h3_protocols=protocols,
        h2_mae=mean([r.h2_error for r in out_rows if r.h2_error is not None]),
        h2_within_one=mean([r.within_one for r in out_rows if r.within_one is not None]),
        h3_mae=mean([float(r["mae"]) for r in h3_rows if r.get("mae") is not None]),
        h3_r={
            "fairness": mean([r.fairness_r for r in out_rows if r.fairness_r is not None]),
            "pushback": mean([r.pushback_r for r in out_rows if r.pushback_r is not None]),
            "staying": mean([r.staying_r for r in out_rows if r.staying_r is not None]),
        },
        synthetic_present=synthetic,
    )
    return summary, out_rows


# ------------------------------------------------------------------ validity


async def validity_results(backend: DbBackend | None = None) -> list[ValidityResultRow]:
    """The append-only *Results so far* table. `docs/06` §3.5.

    A row with ``twins_n = 0`` must read `INCONCLUSIVE` (I15). The DDL's `validity_zero_n`
    constraint makes such a row unstorable; this function refuses to *render* one as anything
    else, so a database reached by another path cannot put a `PASS` on zero twins on screen.
    """
    db = backend or get_backend()
    rows = await db.select("validity_results", None, order=("created_at", True))
    out: list[ValidityResultRow] = []
    for row in rows:
        twins_n = int(row.get("twins_n") or 0)
        verdict = str(row.get("verdict") or "INCONCLUSIVE")
        if twins_n == 0 and verdict != "INCONCLUSIVE":
            raise ValueError(
                f"validity result {row.get('validity_run_id')} claims {verdict} on zero twins. "
                "A test that ran on nobody concluded nothing (I15)."
            )
        version = row.get("version_code")
        out.append(
            ValidityResultRow(
                when=str(row.get("created_at") or ""),
                test=str(row.get("test_id") or ""),
                twins_n=twins_n,
                model=str(row.get("model") or ""),
                result=str(row.get("headline") or ""),
                verdict=verdict,
                version_code=str(version) if version else None,
            )
        )
    return out


# ------------------------------------------------------------------ fieldwork


async def fieldwork_counts(
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """`docs/06` §3.6. **Real fieldwork metrics never count synthetic rows.**

    The synthetic total is returned separately and labelled, rather than filtered away silently,
    because a researcher looking at a low real count needs to see where the other rows went.
    """
    db = backend or get_backend()
    everything = await db.select("survey_submissions", None)
    real = [r for r in everything if r.get("data_type") != SYNTHETIC_DATA_TYPE]
    synthetic = [r for r in everything if r.get("data_type") == SYNTHETIC_DATA_TYPE]

    by_stratum: dict[tuple[str, str], int] = {}
    arm_balance: dict[tuple[str, str], dict[str, int]] = {}
    for row in real:
        key = (str(row.get("city") or "?"), str(row.get("service") or "?"))
        by_stratum[key] = by_stratum.get(key, 0) + 1
        arm = str(row.get("arm") or "?")
        arm_balance.setdefault(key, {})
        arm_balance[key][arm] = arm_balance[key].get(arm, 0) + 1

    quality: list[StatusRow] = []
    for label, column in FIELDWORK_QUALITY_ROWS:
        if column in _NEGATED:
            count = sum(1 for r in real if not r.get(column))
        else:
            count = sum(1 for r in real if r.get(column))
        quality.append(StatusRow(label=label, value=str(count)))

    per_day: dict[str, int] = {}
    for row in real:
        stamp = str(row.get("submitted_at") or "")[:10]
        if stamp:
            per_day[stamp] = per_day.get(stamp, 0) + 1

    return {
        "real_total": len(real),
        "synthetic_total": len(synthetic),
        "by_stratum": by_stratum,
        "arm_balance": arm_balance,
        "quality": quality,
        "per_day": dict(sorted(per_day.items())),
    }


# ------------------------------------------------------------------ settings


async def save_settings(
    key: str, value: dict, *, backend: DbBackend | None = None
) -> int:
    """Write a **new version** of an `app_config` key and return it. `docs/06` §3.8.

    Completed runs stay associated with the config they ran under: a run stores its
    ``config_version``, so bumping the version here cannot retroactively change what an existing
    result was produced by.

    **The new value is merged over the stored one, never substituted for it.** `app_config` rows
    are whole configurations — `twin` carries every quality-gate threshold that `seed_db` wrote —
    and an upsert on `key` replaces the entire `value` object. A caller that sent a partial dict
    therefore silently deleted every setting it did not mention, while the version bump made the
    result look deliberate. Merging means a caller can only ever change the keys it names.
    """
    db = backend or get_backend()
    rows = await db.select("app_config", [("eq", "key", key)], limit=1)
    stored = rows[0].get("value") if rows else None
    version = int(rows[0].get("version") or 1) + 1 if rows else 1
    merged = {**stored, **value} if isinstance(stored, dict) else dict(value)
    await db.upsert(
        "app_config",
        [{"key": key, "value": merged, "version": version}],
        on_conflict="key",
    )
    return version


async def config_version(key: str, *, backend: DbBackend | None = None) -> int | None:
    db = backend or get_backend()
    rows = await db.select("app_config", [("eq", "key", key)], limit=1)
    return int(rows[0]["version"]) if rows else None


#: `docs/06` §3.8's *Which survey answers?*, in its order. The value is the `data_type` filter.
SURVEY_SCOPES: tuple[tuple[str, str | None], ...] = (
    ("Real and synthetic", None),
    ("Real only", REAL_DATA_TYPE),
    ("Synthetic only", SYNTHETIC_DATA_TYPE),
)


def _scope_filter(scope: str) -> list[tuple[str, str, Any]]:
    """The `data_type` filter for one scope label. An unknown label raises (`CLAUDE.md` rule 7)."""
    for label, data_type in SURVEY_SCOPES:
        if label == scope:
            return [] if data_type is None else [("eq", "data_type", data_type)]
    raise ValueError(
        f"unknown survey scope {scope!r}; expected one of "
        f"{[label for label, _ in SURVEY_SCOPES]}"
    )


async def importable_submissions(
    scope: str = "Real and synthetic", backend: DbBackend | None = None
) -> list[dict]:
    """Respondents in ``scope`` who could still become twins, in submission order.

    The gate is `docs/06` §3.8's, and it is one rule used in three places — this function backs
    both the live count and the import itself, and `services.hosted_survey.twin_gate` is the same
    predicate applied to a single row the moment a driver presses send. The number on the screen
    is therefore the number that would be imported, and a hosted twin and an imported twin pass
    the same gate.

    * **eligible** and **consented** and `outcome = 'complete'` — a partial battery cannot build a
      persona (`PersonaIncomplete`);
    * **`consent_twin`** is statement 7. A respondent who did not agree to a twin is never one,
      whatever else their row says (`docs/01` §6.2);
    * **not already a twin** — `twins.submission_id` is unique, so a re-import is a duplicate, not
      an update. Evidence is append-only (I9) and a twin is rebuilt by deleting it, never by
      overwriting it in place.

    The first four conditions are :func:`~twinlab.services.hosted_survey.twin_gate`, applied in
    Python rather than as a database filter so that the single-row and the bulk path cannot drift.
    The scope stays a filter: it selects which population is being imported, not who qualifies.
    """
    from twinlab.services.hosted_survey import twin_gate

    db = backend or get_backend()
    rows = await db.select(
        "survey_submissions", _scope_filter(scope), order=("submitted_at", False)
    )
    existing = {r["submission_id"] for r in await db.select("twins", None)}
    return [
        r for r in rows
        if r["submission_id"] not in existing and twin_gate(r) is None
    ]


async def available_survey_twins(
    scope: str = "Real and synthetic", backend: DbBackend | None = None
) -> int:
    """`docs/06` §3.8's live count. The same rule the import applies, never a looser one.

    **This used to exclude synthetic rows** on the grounds that the creation path refused them —
    `services.studio.create_twin_from_survey` does, by design, because `docs/06` §5's *From a
    survey answer* is a real-respondent mode and "a synthetic twin is made in the Generator".
    But §3.8's import is the Generator-side path and its own control offers *Synthetic only*, so
    excluding them here made the Settings tab read **0 available** with a synthetic batch loaded
    and left no way to import it at all. The scope now decides, and the count follows it.
    """
    return len(await importable_submissions(scope, backend))


def _twin_from_payload(
    submission: dict, payload: dict, ref: ReferenceData
) -> tuple[Twin, SurveyResponse]:
    """`docs/06` §3.8's rebuild, delegated to the one shared implementation.

    The body moved to `persona.from_payload` when the hosted survey arrived and needed exactly
    this. Two copies would let an imported twin and a hosted twin drift into different field
    shapes, which no test downstream would catch — they would simply be different people.
    """
    return twin_from_payload(
        submission,
        payload,
        ref,
        data_type=REAL_DATA_TYPE,
        source=(
            "synthetic" if submission.get("data_type") == SYNTHETIC_DATA_TYPE else "real"
        ),
    )


async def import_survey_twins(
    scope: str = "Real and synthetic",
    *,
    backend: DbBackend | None = None,
    storage: StorageBackend | None = None,
    limit: int | None = None,
) -> TwinImportResult:
    """`docs/06` §3.8's *Import twins from the survey*. **No model call anywhere in this path.**

    §3.8 names exactly what it must do — "imports eligible completed respondents, applies the
    consent gate, prevents duplicates, builds personas, returns imported / skipped / invalid
    counts" — and this returns all three counts with a **named reason for every row that did not
    become a twin**. A silent skip is the failure mode `CLAUDE.md` rule 7 exists to prevent: an
    import that reported "40 imported" out of 50 and said nothing about the other ten would leave
    the researcher to guess whether the batch or the importer was at fault.

    Rows are inserted **one at a time, each after its own persona is built and checked**, rather
    than as one batch at the end. A payload that cannot build a persona then costs its own row and
    nothing else, and the rows that did import are real: a single failing respondent in a batch of
    500 must not discard 499 good twins.
    """
    from twinlab.services.hosted_survey import twin_gate

    db = backend or get_backend()
    store = storage or get_storage()
    ref = reference()

    # Snapshot **before** the import loop. Taken afterwards, every row this run just imported
    # would also read as "already a twin" and be counted twice — imported and skipped at once.
    already_twin_ids = {r["submission_id"] for r in await db.select("twins", None)}

    candidates = await importable_submissions(scope, db)
    if limit is not None:
        candidates = candidates[:limit]

    imported = 0
    invalid: list[str] = []
    for submission in candidates:
        submission_id = str(submission["submission_id"])
        path = str(submission.get("raw_object_path") or "")
        try:
            if not path:
                raise ValueError("the row records no raw_object_path")
            payload = json.loads(await store.get(path))
            twin, response = _twin_from_payload(submission, payload, ref)
            passage = build_persona(twin, response, ref)
            # At the write, not in a handler: an ablated persona is missing its fairness clauses
            # by design (test 6, I6) and a twin hashed from one is indistinguishable downstream
            # from a twin whose driver never answered those items.
            assert_not_ablated(passage)
            await db.insert(
                "twins",
                [{
                    "twin_id": twin.twin_id,
                    "submission_id": twin.submission_id,
                    "source": twin.source,
                    "service": twin.service,
                    "city": twin.city,
                    "age": twin.age,
                    "gender": twin.gender,
                    "tenure_months": twin.tenure_months,
                    "hours_per_week": twin.hours_per_week,
                    "background": twin.background.model_dump(mode="json"),
                    "persona_passage": passage.text,
                    "persona_hash": passage.persona_hash,
                    "persona_template_version": passage.template_version,
                }],
            )
            imported += 1
        except Exception as exc:  # noqa: BLE001 — every reason is reported, never swallowed.
            invalid.append(f"{submission_id}: {type(exc).__name__}: {str(exc)[:160]}")
            log.warning("twin import failed for %s: %s", submission_id, exc)

    # Everything in scope that was NOT a candidate, **split by why**. Counted rather than listed,
    # because on a 500-row batch the list is the batch.
    #
    # The two reasons are opposite outcomes and were previously one `skipped` number, which made
    # the screen report a respondent who already has a working twin with the sentence "Nothing was
    # eligible". Since the hosted questionnaire builds the twin at submit time, *every* hosted
    # respondent arrives here already imported, so that reading is now the common one rather than
    # the rare one.
    in_scope = await db.select("survey_submissions", _scope_filter(scope))
    already = sum(1 for r in in_scope if r["submission_id"] in already_twin_ids)
    gated = sum(
        1 for r in in_scope
        if r["submission_id"] not in already_twin_ids and twin_gate(r) is not None
    )

    return TwinImportResult(
        scope=scope,
        imported=imported,
        skipped=already + gated,
        already_twins=already,
        gated=gated,
        invalid=len(invalid),
        reasons=invalid[:20],
        remaining=await available_survey_twins(scope, db),
    )


__all__ = [
    "CLEAR_RUNS_NOTE",
    "FIELDWORK_QUALITY_ROWS",
    "HOLDOUT_NOTE",
    "SYNTHETIC_WARNING",
    "VALIDITY_TESTS",
    "available_survey_twins",
    "import_survey_twins",
    "importable_submissions",
    "SURVEY_SCOPES",
    "comparable_codes",
    "config_version",
    "fieldwork_counts",
    "save_settings",
    "scenario_paragraphs",
    "twin_panel",
    "twin_rows",
    "validation_view",
    "validity_results",
    "what_twins_are_told",
]
