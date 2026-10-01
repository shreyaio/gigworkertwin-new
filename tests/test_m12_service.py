"""M12 — the Statistics service: staging, resume, the floor and provenance. `docs/06` §7.

No engine fit happens in most of these: the point is the *bookkeeping* around the estimate — what
is persisted, what is skipped on resume, what is refused. A stub stands in for the estimator so
each rule is tested on its own, which is the same reason `docs/11` M2 put the output contract
before any agent.

No live database and no live LLM, per `HANDOFF.md` §2.4. `tests/conftest.py` installs a fresh
`InMemoryBackend` for every test, and it mirrors the DDL's check constraints — including
`analysis_bootstrap_floor` and `analysis_has_cases`, which are the two this milestone leans on.
"""

from __future__ import annotations

import pytest

from twinlab.db.client import get_backend
from twinlab.models.stats import STAGES, CaseMatrix
from twinlab.services import statistics
from twinlab.stats import plssem
from twinlab.stats.golden import GOLDEN_FINGERPRINT
from twinlab.stats.spec import build_model_spec


@pytest.fixture
def matrix():
    return CaseMatrix(
        columns=("A", "B"),
        rows=((1.0, 2.0), (2.0, 1.0), (3.0, 4.0)),
        submission_ids=("S1", "S2", "S3"),
        population="real",
        screening="strict",
    )


async def _seed_run(**overrides):
    """An `analysis_runs` row straight through the backend, bypassing the matrix build."""
    row = {
        "population": "real", "screening": "strict", "bootstrap_samples": 5000,
        "seed": 7, "n_cases": 120, "status": "created", "stage_cursor": STAGES[0],
        "engine_version": "1.11.0",
        "config": {"model_fingerprint": GOLDEN_FINGERPRINT},
    }
    row.update(overrides)
    rows = await get_backend().insert("analysis_runs", [row])
    return str(rows[0]["analysis_id"])


# --------------------------------------------------------------------- the bootstrap floor

async def test_below_the_floor_is_refused_by_the_service():
    """`docs/07` §9's hard floor of 30, enforced where a Gradio handler can reach it."""
    with pytest.raises(plssem.BootstrapFloorError) as excinfo:
        await statistics.create_analysis(bootstrap_samples=29)
    assert "30" in str(excinfo.value)


async def test_below_the_floor_is_refused_by_the_backend():
    """`analysis_bootstrap_floor`. Two gates, because the DDL is not reachable from a handler."""
    from twinlab.db.client import DbError

    with pytest.raises(DbError, match="analysis_bootstrap_floor"):
        await _seed_run(bootstrap_samples=10)


async def test_zero_cases_is_refused_by_the_backend():
    """`analysis_has_cases`. The measurement layer's I15."""
    from twinlab.db.client import DbError

    with pytest.raises(DbError, match="analysis_has_cases"):
        await _seed_run(n_cases=0)


def test_bootstrap_warning_fires_below_one_thousand():
    """`docs/07` §9. Below 1,000 the CIs are unstable and should not be reported."""
    assert statistics.plssem.bootstrap_warning(5000) == ""
    assert statistics.plssem.bootstrap_warning(1000) == ""
    warning = statistics.plssem.bootstrap_warning(500)
    assert "500" in warning and "1,000" in warning


def test_the_floor_is_not_a_reportable_setting():
    """The floor exists so a researcher can smoke-test the pipeline, and the UI must say so."""
    assert plssem.BOOTSTRAP_FLOOR == 30
    assert plssem.BOOTSTRAP_DEFAULT == 5000
    assert statistics.plssem.bootstrap_warning(plssem.BOOTSTRAP_FLOOR) != ""


# --------------------------------------------------------------------- staging and resume

async def test_stages_persist_and_are_not_recomputed(matrix, monkeypatch):
    """`docs/01` §6.8. A completed stage is never recomputed on resume.

    The estimator is counted, not asserted on: the contract is "each stage computed once", not
    "the numbers were these" — those are the golden test's job (`HANDOFF.md` §2.4).
    """
    analysis_id = await _seed_run(bootstrap_samples=30)
    computed: list[str] = []

    monkeypatch.setattr(statistics.plssem, "fit", lambda *a, **k: object())
    monkeypatch.setattr(statistics.plssem, "bootstrap", lambda *a, **k: None)

    def fake_stage(stage, pls, mtx, spec, boot, seed):
        computed.append(stage)
        return {"rows": []}

    monkeypatch.setattr(statistics, "_compute_stage", fake_stage)

    view = await statistics.run_analysis(analysis_id, matrix)
    assert computed == list(STAGES)
    assert view.is_complete
    assert view.status == "completed"

    computed.clear()
    again = await statistics.run_analysis(analysis_id, matrix)
    assert computed == [], "a completed stage must never be recomputed"
    assert again.is_complete


async def test_resume_computes_only_the_outstanding_stages(matrix, monkeypatch):
    """An interruption at stage seven restarts at stage seven, not at stage one."""
    analysis_id = await _seed_run(bootstrap_samples=30)
    backend = get_backend()
    for stage in STAGES[:6]:
        await backend.insert(
            "analysis_results",
            [{"analysis_id": analysis_id, "stage": stage, "payload": {"rows": []}}],
        )

    computed: list[str] = []
    monkeypatch.setattr(statistics.plssem, "fit", lambda *a, **k: object())
    monkeypatch.setattr(statistics.plssem, "bootstrap", lambda *a, **k: None)
    monkeypatch.setattr(
        statistics, "_compute_stage",
        lambda stage, *a: (computed.append(stage), {"rows": []})[1],
    )

    await statistics.run_analysis(analysis_id, matrix)
    assert computed == list(STAGES[6:])


async def test_a_failed_stage_records_the_cursor_and_stores_nothing(matrix, monkeypatch):
    """A stage that raised is not stored as an empty payload. `CLAUDE.md` rule 7."""
    analysis_id = await _seed_run(bootstrap_samples=30)
    monkeypatch.setattr(statistics.plssem, "fit", lambda *a, **k: object())
    monkeypatch.setattr(statistics.plssem, "bootstrap", lambda *a, **k: None)

    def boom(stage, *a):
        if stage == "collinearity":
            raise RuntimeError("the engine returned nothing")
        return {"rows": []}

    monkeypatch.setattr(statistics, "_compute_stage", boom)

    with pytest.raises(statistics.StageError, match="collinearity"):
        await statistics.run_analysis(analysis_id, matrix)

    stored = await statistics.completed_stages(analysis_id)
    assert "collinearity" not in stored
    view = await statistics.analysis_view(analysis_id)
    assert view.status == "failed"
    assert view.stage_cursor == "collinearity"


async def test_progress_is_reported_per_stage(matrix, monkeypatch):
    """`docs/06` §7: "Progress shows the current stage"."""
    analysis_id = await _seed_run(bootstrap_samples=30)
    seen: list[tuple[str, int, int]] = []
    monkeypatch.setattr(statistics.plssem, "fit", lambda *a, **k: object())
    monkeypatch.setattr(statistics.plssem, "bootstrap", lambda *a, **k: None)
    monkeypatch.setattr(statistics, "_compute_stage", lambda *a: {"rows": []})

    await statistics.run_analysis(analysis_id, matrix, on_stage=lambda *a: seen.append(a))
    assert [s[0] for s in seen] == list(STAGES)
    assert seen[-1][1] == seen[-1][2] == len(STAGES)


# --------------------------------------------------------------------- provenance

async def test_every_result_view_carries_the_five_required_facts():
    """`docs/07` §9. The paper must state all five, so a view without them cannot be published."""
    analysis_id = await _seed_run(bootstrap_samples=2500, seed=99, n_cases=314)
    view = await statistics.analysis_view(analysis_id)
    p = view.provenance
    assert p.engine_version
    assert p.n_cases == 314
    assert p.bootstrap_samples == 2500
    assert p.seed == 99
    assert p.screening == "strict"
    assert p.population == "real"


async def test_unvalidated_until_the_model_matches_the_golden_fingerprint():
    """`docs/07` §10. A different model means the golden test did not validate *this* wiring."""
    matching = await _seed_run(config={"model_fingerprint": GOLDEN_FINGERPRINT})
    assert (await statistics.analysis_view(matching)).provenance.engine_validated

    drifted = await _seed_run(config={"model_fingerprint": "0000000000000000"})
    assert not (await statistics.analysis_view(drifted)).provenance.engine_validated


def test_the_running_model_is_the_validated_one():
    """The banner is driven by a real comparison, not by a hand-set flag."""
    assert statistics.engine_is_validated(build_model_spec())


def test_unvalidated_banner_names_the_consequence():
    assert "reportable" in statistics.UNVALIDATED_BANNER
    assert "UNVALIDATED" in statistics.UNVALIDATED_BANNER


# --------------------------------------------------------------------- legends and specs

def test_every_stage_has_a_legend():
    """`docs/05` §4.4: statistical abbreviations need a visible legend, on every table."""
    for stage in STAGES:
        assert stage in statistics.LEGENDS, f"{stage} has no legend"
        assert statistics.LEGENDS[stage], f"{stage}'s legend is empty"


def test_table_spec_refuses_a_stage_with_no_legend():
    """A gate that cannot fail is not a gate."""
    with pytest.raises(KeyError):
        statistics.table_spec("not_a_stage", "Title", ("A",))


def test_legends_explain_the_abbreviations_that_need_it():
    """`rho_A` and `AVE` are not self-explanatory even to the intended reader (`docs/05` §6)."""
    reliability = dict(statistics.LEGENDS["reliability"])
    assert "rho_A" in reliability
    assert "AVE" in reliability
    assert len(reliability["AVE"]) > 20


def test_screening_note_names_who_was_dropped_and_why():
    """`docs/07` §7.1 — the rule's effect stays visible rather than buried in an `n`."""
    clean = CaseMatrix(
        columns=("A",), rows=((1.0,), (2.0,)), submission_ids=("S1", "S2"),
        population="real", screening="strict",
    )
    assert "none screened out" in statistics.screening_note(clean)

    screened = clean.model_copy(
        update={"dropped": (("S3", "failed an attention check"),
                            ("S4", "failed an attention check"))}
    )
    note = statistics.screening_note(screened)
    assert "2 failed an attention check" in note


# --------------------------------------------------------------------- the live-database ban

def test_no_test_can_construct_a_live_backend():
    """`HANDOFF.md` §2.4 — **no test may reach a live database**, at any fixture scope.

    Regression. The guarantee used to rest on `conftest.backend`, which is function-scoped, so a
    ``module``- or ``session``-scoped fixture ran before it and got whatever `get_backend()` built
    — a real `SupabaseBackend` whenever `.env` carries credentials. M12's integration fixture hit
    the researcher's actual project that way. `conftest._no_live_database` now blocks it at the
    factory, and this proves the block rejects an attempt rather than merely existing.
    """
    import twinlab.db.client as client

    with pytest.raises(AssertionError, match="live SupabaseBackend"):
        client.SupabaseBackend("https://example.supabase.co", "service-key")
