"""M17 — T-12. I3 against a **stored** variant whose Checker report failed.

`HANDOFF_M17_VALIDATION_PLAN.md` §6.2 T-12 asks that each of `SessionRunner`, `_render_stimuli`
and `studio._stimulus` refuse a stored variant with ``checker.passed = false``. The Studio half is
covered in `test_m16_render_budget.py`; the other two were marked **[TODO]** and are covered here.

The link these tests exercise is the one the existing orchestrator test cannot reach.
`test_m7_orchestrator.test_a_checker_failure_marks_that_run_failed_and_the_loop_continues` proves
the gate fires, but it supplies its own stub ``render_and_check`` and so never touches the
`variants` cache. The real :func:`render_and_check` **short-circuits on a stored row and returns
the stored report verbatim** (`services/twin_runtime.py` §"A stored row short-circuits both the
render and the Checker"), and a cell that fails is stored as failed — §5.2 of the handoff. So the
cached-failure path is the one that will actually occur in the study, and nothing tested it.

No live LLM and no live DB (`docs/11` → Ground rules).
"""

from __future__ import annotations

import pytest

from twinlab.db.repositories import VariantRepo
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import PanelMember
from twinlab.services import twin_runtime


@pytest.fixture(autouse=True)
def _fresh_pool():
    """`twin_runtime`'s pool is process-global state; no test may inherit another's."""
    twin_runtime.reset_pool()
    yield
    twin_runtime.reset_pool()


FAILED_CHECKER = {
    "coverage": {"1.1.a": True},
    # One containment hit fails the cell and there is no tolerance (`variant/checker.py`).
    "containment": ["1.1.a"],
    "word_count": 60,
    "in_band": True,
    "reading_grade": 9.0,
    "dial_zero_identical": True,
    "sham_indistinguishable": True,
    "passed": False,
    "notes": "containment hit (one fails the cell, I3): 1.1.a",
}


async def _store(backend, code: str, style: str, checker: dict) -> str:
    row = await VariantRepo(backend).put(
        version_code=code,
        style_version=style,
        delta_spec={"version_code": code},
        delta_hash="h",
        paragraphs={lever: {"text": f"text for {lever}"} for lever in LEVER_BY_POSITION},
        checker=checker,
    )
    return row["variant_id"]


# ------------------------------------------------------- render_and_check, the cache short-circuit


async def test_a_stored_failure_is_returned_as_a_failure_and_costs_no_model_call(backend):
    """The cache returns the stored verdict, so the gate downstream sees ``passed=False``. I3."""
    await _store(backend, "01000", "v2", FAILED_CHECKER)

    variant, report = await twin_runtime.render_and_check("01000", "v2", backend=backend)

    assert report.passed is False, (
        "a stored failed variant came back as passing — every I3 gate downstream reads this flag"
    )
    assert report.containment == ["1.1.a"], "the stored report was not returned verbatim"
    assert variant.version_code == "01000"


async def test_a_stored_failure_is_not_re_rendered_into_a_pass(backend, monkeypatch):
    """Reading a cached failure must not reach the render path at all.

    `_rerender_cell` spends a paragraph's one **durable** re-render (migration 003). Re-rendering
    on a cache read would spend it on every read and could convert a recorded failure into a pass
    whose failure is nowhere in the evidence — a detectable failure made undetectable.

    Proven by making the paragraph pool explode: the short-circuit must return before it is built.
    """
    await _store(backend, "01000", "v2", FAILED_CHECKER)

    def _no_pool(*args, **kwargs):
        raise AssertionError(
            "the render path was entered for a cell whose stored Checker report already failed"
        )

    monkeypatch.setattr(twin_runtime, "paragraph_pool", _no_pool)

    _, report = await twin_runtime.render_and_check("01000", "v2", backend=backend)
    assert report.passed is False


# --------------------------------------------------------------- the quality gate's render step


async def test_the_quality_gate_refuses_a_stored_failed_variant(backend):
    """`services/quality._render_stimuli` stops the gate rather than showing a failed cell. I3.

    T-12, second of the three sites. The gate renders every H3 code before it scores a single
    twin, so a failed cell here must stop the whole gate — not be shown with a note.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.quality import QualityGateError, _render_stimuli

    ref = reference()
    # Fail the FIRST H3 code the gate will reach, and store every other as passing so the only
    # thing that can stop the gate is the failed verdict.
    codes = list(ref.h3_version_codes)
    for code in codes:
        checker = dict(FAILED_CHECKER) if code == codes[0] else {"passed": True}
        await _store(backend, code, "v2", checker)

    events = EventLog("s-m17", backend)
    parent = await events.emit(stage="render", label="test parent")

    with pytest.raises(QualityGateError, match="failed the Checker"):
        await _render_stimuli("s-m17", ref, events, parent, backend, include_h2=False)


# ----------------------------------------------------------------- SessionRunner, over the cache


async def test_the_session_runner_asks_no_twin_for_a_stored_failed_variant(backend):
    """T-12, third site — through the **real** `render_and_check`, not a stub.

    The existing orchestrator test supplies its own ``render_and_check`` and so proves only that
    the gate reads the flag it is handed. This drives the runner over the real cache read, which
    is the path a resumed or rerun session actually takes.
    """
    from twinlab.db.repositories import PanelRepo, SessionRepo
    from twinlab.orchestrator.loop import SessionRunner

    await _store(backend, "01000", "v2", FAILED_CHECKER)

    sessions = SessionRepo(backend)
    session = await sessions.create(
        name="m17-t12",
        iterations=1,
        start_code="01000",
        panel_size=1,
        panel_seed=7,
        config={"style_version": "v2", "wording": "A"},
    )
    await PanelRepo(backend).freeze(
        session.session_id, [PanelMember(twin_id="SYN-TEST-0001", stratum="x", position=0)]
    )

    twin_calls: list[str] = []

    async def _never_asked(session, run_id, code, variant, member):
        twin_calls.append(code)
        return None

    runner = SessionRunner(
        session.session_id,
        backend=backend,
        render_and_check=lambda code, style: twin_runtime.render_and_check(
            code, style, backend=backend
        ),
        ask_twin=_never_asked,
    )
    run = await runner.execute_run(
        session, "01000", [PanelMember(twin_id="SYN-TEST-0001", stratum="x", position=0)]
    )

    # The I3 claim first, so a regression names the violation rather than a downstream symptom.
    assert twin_calls == [], "a twin was asked for a cell whose stored Checker report failed"
    assert run.status == "failed"
    assert "checker failed" in (run.error or "")
