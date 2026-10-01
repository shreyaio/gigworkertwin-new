"""Live counters. `docs/06` §1.3 ("Where things stand") and §3.1 ("Status").

Two numbers here are specified rather than obvious, and both are research statements:

* **"Versions tested" reads "of 242", not "of 243".** `00000` is a control the orchestrator runs,
  not one of the versions under test (`docs/06` §1.3 and §3.2). Counting it would inflate coverage
  by one cell and imply the control is a finding.
* **A run with ``twins_n = 0`` is never counted as tested.** It is a `failed` run (I15), so the
  count reads completed runs only.

Every count is a database read. Formatting lives here so the Main menu and the Agents tab cannot
word the same row differently.
"""

from __future__ import annotations

from twinlab.db.client import DbBackend, get_backend
from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
from twinlab.models.view import StatusRow
from twinlab.orchestrator.odometer import CONTROL_CODE, N_CODES, SHAM_CODE

#: 243 cells minus the `00000` control. `SHAM` was never one of the 243.
TESTABLE_CODES = N_CODES - 1

#: The latest H3 quality row that kept a twin. `twin_quality_runs.kept`, not `passed` — the
#: column name is the DDL's, and H3 is the holdout the keep/drop decision is made on (`docs/08`).
_KEPT_H3: list = [
    ("eq", "is_latest", True),
    ("eq", "holdout_set", "H3"),
    ("eq", "kept", True),
]

#: `docs/06` §1.4's ordered quick start.
QUICK_START: tuple[str, ...] = (
    "Create test data in the Generator, or wait for real survey submissions.",
    "Import twins from the survey in Twin Lab → Settings.",
    "Run the twin quality test in Twin Lab → Agents.",
    "Check validation in Twin Lab → Validation.",
    "Explore dials in Twin Lab → Dial board, or let the agents choose six versions.",
    "Read results in Twin Lab → Results.",
    "Run analysis and export in Statistics.",
)


async def _count(backend: DbBackend, table: str, filters: list | None = None) -> int:
    return await backend.count(table, filters)


async def tested_codes(backend: DbBackend | None = None) -> dict[str, float | None]:
    """version code → index, for every **completed** run, latest first.

    Excludes `00000` and `SHAM`: both are controls, and neither is a version under test. They are
    read separately by the floors (`docs/07` §6), which is the only place they belong.
    """
    backend = backend or get_backend()
    rows = await backend.select(
        "runs", [("eq", "status", "completed")], order=("started_at", True)
    )
    out: dict[str, float | None] = {}
    for row in rows:
        code = row.get("version_code")
        if code in (CONTROL_CODE, SHAM_CODE) or code in out:
            continue
        if not row.get("twins_n"):
            # A completed run with no twins should be impossible (I15); if one exists, it is
            # not a result and is not counted as one.
            continue
        out[code] = row.get("index_value")
    return out


async def control_index(
    code: str, backend: DbBackend | None = None
) -> float | None:
    """The latest completed index for one control cell, or ``None``. Never assumed."""
    backend = backend or get_backend()
    rows = await backend.select(
        "runs",
        [("eq", "status", "completed"), ("eq", "version_code", code)],
        order=("started_at", True),
        limit=1,
    )
    return rows[0].get("index_value") if rows else None


async def where_things_stand(backend: DbBackend | None = None) -> list[StatusRow]:
    """`docs/06` §1.3's nine rows, in order. Live counts, never cached figures."""
    backend = backend or get_backend()

    total_submissions = await _count(backend, "survey_submissions")
    synthetic = await _count(
        backend, "survey_submissions", [("eq", "data_type", SYNTHETIC_DATA_TYPE)]
    )
    # Real is the complement, so a third `data_type` can never be silently counted as real.
    real = total_submissions - synthetic
    twins = await _count(backend, "twins")
    passed = await _count(backend, "twin_quality_runs", _KEPT_H3)
    answers = await _count(backend, "twin_answers")
    validity = await _count(backend, "validity_results")
    tested = len(await tested_codes(backend))

    validation_rows = await _count(
        backend, "twin_quality_runs", [("eq", "is_latest", True), ("eq", "holdout_set", "H2")]
    )
    validation_value = (
        f"Run on {validation_rows} twins" if validation_rows else "Not run"
    )

    return [
        StatusRow(label="Real surveys saved", value=str(real)),
        StatusRow(label="Synthetic surveys saved", value=str(synthetic)),
        StatusRow(label="Twins built", value=str(twins)),
        StatusRow(label="Passed quality test", value=f"{passed} of {twins}"),
        # "of 242" — the control is not a version under test.
        StatusRow(label="Versions tested", value=f"{tested} of {TESTABLE_CODES}"),
        StatusRow(label="Twin answers saved", value=str(answers)),
        StatusRow(
            label="Validation run",
            value=validation_value,
            state="complete" if validation_rows else "pending",
        ),
        StatusRow(label="Validity tests run", value=str(validity)),
        StatusRow(label="Access", value=access_line()),
    ]


def access_line() -> str:
    """``HF OAuth · <org>``, or the local-execution reality.

    The deployment decision of 2026-09-28 is to run locally (`HANDOFF.md` §0.6), so this states
    that rather than implying an OAuth session that does not exist.
    """
    from config.settings import settings

    org = getattr(settings, "hf_org", None)
    return f"HF OAuth · {org}" if org else "Local · no sign-in"


async def lab_status(backend: DbBackend | None = None) -> list[StatusRow]:
    """`docs/06` §3.1's compact Status card: five rows.

    "Best so far" reads ``Nothing yet`` when no cell has completed — never ``0.000``, which would
    be indistinguishable from a measured null result.
    """
    backend = backend or get_backend()
    twins = await _count(backend, "twins")
    passed = await _count(backend, "twin_quality_runs", _KEPT_H3)
    answers = await _count(backend, "twin_answers")
    indexed = await tested_codes(backend)
    scored = {c: v for c, v in indexed.items() if v is not None}
    if scored:
        best_code = max(scored, key=lambda c: scored[c])
        best = f"{best_code} ({scored[best_code]:.3f})"
    else:
        best = "Nothing yet"

    return [
        StatusRow(label="Twins", value=str(twins)),
        StatusRow(label="Passed quality test", value=f"{passed} of {twins}"),
        StatusRow(label="Versions tested", value=f"{len(indexed)} of {TESTABLE_CODES}"),
        StatusRow(label="Answers saved", value=str(answers)),
        StatusRow(label="Best so far", value=best),
    ]
