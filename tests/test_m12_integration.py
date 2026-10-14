"""M12 — the whole Statistics stack, from stored survey rows to rendered tabs.

`HANDOFF.md` §0.5: **green tests do not prove a Gradio screen works**, and both bugs found in M10
and M11 were invisible to the unit suite. This is the nearest a test can get: it puts real rows in
the backend, runs the real service, and renders the real tab HTML — so a tab that silently shows
`Not tested` where a number exists fails here rather than in front of a reader.

It uses the golden fixture as its data, which means the numbers on screen are the ones
`tests/test_stats_golden.py` pins.
"""

from __future__ import annotations

import pytest

from twinlab.db.client import get_backend
from twinlab.models.stats import STAGES
from twinlab.services import statistics
from twinlab.stats import golden, plssem
from twinlab.stats.spec import build_model_spec
from twinlab.ui.pages import statistics as page

#: Small enough to keep this inside a CI step, above `docs/07` §9's hard floor.
SAMPLES = plssem.BOOTSTRAP_FLOOR


@pytest.fixture(scope="module")
def spec():
    return build_model_spec()


async def _seed(spec) -> None:
    """Put the golden fixture into the backend exactly as intake would have."""
    submissions, answers = golden.golden_rows(spec=spec)
    backend = get_backend()
    await backend.upsert(
        "survey_submissions",
        [
            {
                **s,
                "eligible": True,
                "consent_twin": True,
                "outcome": "accepted",
                "raw_object_path": f"raw/{s['submission_id']}.json",
                "submitted_at": "2026-09-29T00:00:00Z",
            }
            for s in submissions
        ],
        on_conflict="submission_id",
    )
    await backend.upsert("survey_answers", answers, on_conflict="submission_id,item_id")


@pytest.fixture(scope="module")
def completed(spec):
    """One analysis, run all the way through, shared by every assertion below.

    **Owns its own backend.** `conftest.backend` is function-scoped, so it would wipe anything
    seeded at module scope before the first test ran; `_use_module_backend` re-installs this one
    after it. Driven with `asyncio.run` rather than declared `async` so the module does not depend
    on `pytest-asyncio` being installed — `conftest` only drives coroutine *tests*.
    """
    import asyncio

    from twinlab.db.client import InMemoryBackend, set_backend

    instance = InMemoryBackend()
    set_backend(instance)

    async def _go():
        await _seed(spec)
        analysis_id, matrix = await statistics.create_analysis(
            population="real", screening="strict", bootstrap_samples=SAMPLES,
            seed=golden.GOLDEN_SEED,
        )
        view = await statistics.run_analysis(analysis_id, matrix)
        return analysis_id, matrix, view

    result = asyncio.run(_go())
    yield (instance, *result)
    set_backend(None)


@pytest.fixture(autouse=True)
def _use_module_backend(completed):
    """Re-install the module's backend after `conftest.backend` has swapped in a fresh one."""
    from twinlab.db.client import set_backend

    set_backend(completed[0])


async def test_the_analysis_completes_every_stage(completed):
    """`docs/01` §6.8's nine stages, all persisted."""
    _backend, _analysis_id, _matrix, view = completed
    assert view.status == "completed"
    assert view.is_complete
    assert set(view.stages_done) == set(STAGES)


async def test_it_ran_on_the_whole_clean_fixture(completed):
    """Screening drops nobody here, so `n_cases` is the fixture's own N."""
    _backend, _analysis_id, matrix, view = completed
    assert matrix.n_cases == golden.GOLDEN_N
    assert view.provenance.n_cases == golden.GOLDEN_N


async def test_provenance_carries_the_real_engine_version(completed):
    """`docs/07` §9 — the paper must state which implementation produced the numbers."""
    _backend, _analysis_id, _matrix, view = completed
    assert view.provenance.engine_version == plssem.engine_version()
    assert view.provenance.seed == golden.GOLDEN_SEED
    assert view.provenance.bootstrap_samples == SAMPLES


async def test_the_run_is_flagged_validated_against_the_golden_model(completed):
    """The `UNVALIDATED` banner is driven by the model fingerprint, not a hand-set flag."""
    _backend, _analysis_id, _matrix, view = completed
    assert view.provenance.model_fingerprint == golden.GOLDEN_FINGERPRINT
    assert view.provenance.engine_validated


async def test_this_bootstrap_size_is_marked_unreportable(completed):
    """`docs/07` §9: 30 is a smoke-test setting and the UI must say so."""
    _backend, _analysis_id, _matrix, view = completed
    assert view.bootstrap_warning
    assert "not be reported" in view.bootstrap_warning


@pytest.mark.parametrize("stage", STAGES)
async def test_every_tab_renders_real_numbers(completed, stage):
    """The render path the browser uses, with a populated payload.

    Asserts the tab shows **numbers**, not that it shows particular ones — the values are the
    golden test's business (`HANDOFF.md` §2.4: test the contract, not the prose).
    """
    _backend, analysis_id, _matrix, _view = completed
    payload = await statistics.stage_payload(analysis_id, stage)
    assert payload is not None, f"{stage} was not persisted"

    html = page.RENDERERS[stage](payload)
    assert "<table" in html, f"{stage} rendered no table"
    assert "tl-legend" in html, f"{stage} rendered no legend (docs/05 §4.4)"
    assert "No analysis has been run" not in html
    # A populated stage must show at least one real number somewhere in a cell.
    assert any(ch.isdigit() for ch in html), f"{stage} rendered no numbers"


async def test_the_reliability_tab_shows_the_nine_constructs(completed):
    """A populated tab must not quietly show `Not tested` where a statistic exists."""
    _backend, analysis_id, _matrix, _view = completed
    payload = await statistics.stage_payload(analysis_id, "reliability")
    html = page._reliability_html(payload)
    for code in ("EXPO", "CTRL", "FAIR", "TRAN", "SATI", "LOYA", "VOIC", "EXIT", "EDEP"):
        assert code in html, f"{code} is missing from the reliability tab"
    # The formative blocks are the only rows allowed to read "Not tested" here. Counted from the
    # spec rather than hard-coded: there are four of them since 2026-10-11 (one per arm plus the
    # interaction term), and a literal here would have to be edited every time the antecedent's
    # shape changes, which is exactly when this assertion matters most.
    from twinlab.stats.spec import build_model_spec

    formative = sum(1 for c in build_model_spec().constructs if not c.reflective)
    assert html.count("Not tested") <= formative * 6


async def test_the_paths_tab_shows_every_structural_path(completed, spec):
    """All seventeen edges. A path silently absent is a silently different model."""
    _backend, analysis_id, _matrix, _view = completed
    payload = await statistics.stage_payload(analysis_id, "paths")
    html = page._paths_html(payload)
    for edge in spec.edges:
        assert f"{edge.source} &rarr; {edge.target}" in html, f"{edge} missing from the tab"


async def test_resume_after_an_interruption_recomputes_nothing(completed):
    """`docs/01` §6.8 — on the real stack, not a stub."""
    _backend, analysis_id, matrix, _view = completed
    before = await statistics.completed_stages(analysis_id)
    view = await statistics.run_analysis(analysis_id, matrix)
    after = await statistics.completed_stages(analysis_id)
    assert before == after == set(STAGES)
    assert view.status == "completed"


async def test_export_carries_two_header_rows_and_one_row_per_respondent(completed):
    """`docs/07` §11, through the service, against stored rows."""
    ids, scales, rows = await statistics.build_export(population="real", screening="none")
    assert len(ids) == len(scales)
    assert len(rows) == golden.GOLDEN_N
    assert ids[0] == "submission_id"
    # The scale row is the whole point: three constructs are 1-5, not 1-7.
    by_column = dict(zip(ids, scales, strict=True))
    assert "5-point" in by_column["CLAR1"]
    assert "7-point" in by_column["SAT1"]


async def test_export_construct_means_are_present_and_reverse_coded(completed):
    """I12 — pre-computed in Python so a downstream tool cannot re-derive them differently."""
    ids, _scales, rows = await statistics.build_export(population="real", screening="none")
    column = ids.index("SATI_mean")
    values = [r[column] for r in rows]
    assert all(v != "" for v in values), "a complete respondent must have a construct mean"
    assert all(1.0 <= float(v) <= 7.0 for v in values)
