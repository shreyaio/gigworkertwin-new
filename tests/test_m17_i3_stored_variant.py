"""M17 — T-12. I3 against a **stored** variant whose Checker report failed.

`HANDOFF_M17_VALIDATION_PLAN.md` §6.2 T-12 asks that each of `SessionRunner`, `_render_stimuli`
and `studio._stimulus` refuse a stored variant with ``checker.passed = false``. The Studio half is
covered in `test_m16_render_budget.py`; the other two were marked **[TODO]** and are covered here.

The link these tests exercise is the one the existing orchestrator test cannot reach.
`test_m7_orchestrator.test_a_checker_failure_marks_that_run_failed_and_the_loop_continues` proves
the gate fires, but it supplies its own stub ``render_and_check`` and so never touches the
`variants` cache. A cell that fails is stored as failed (§5.2 of the handoff), so the
cached-failure path is the one that will actually occur in the study, and nothing tested it.

**Updated for M19 WP-2.** `render_and_check` used to short-circuit on *any* stored row and return
the stored report verbatim. It now short-circuits only on a row that **passed**: a stored failure
caches the verdict, not the attempt, and the cell is retried while its durable paragraph budget
allows. The I3 claim these tests make is unchanged — a stored failed variant never reaches a twin —
so what changed is the setup, not the assertion: each refusal test now spends the paragraph budget
first, which is the real state the study database was in.

No live LLM and no live DB (`docs/11` → Ground rules).
"""

from __future__ import annotations

import contextlib

import pytest

from config.settings import settings
from twinlab.db.repositories import VariantRepo
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import PanelMember
from twinlab.orchestrator.odometer import dials
from twinlab.services import twin_runtime

#: The version the app runs under. Written as the live value rather than a literal: these tests
#: are about the cache key, not about which version happens to be current.
STYLE = settings.style_version


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


async def _spend_the_budget(backend, code: str, style: str) -> None:
    """Mark every non-dial-0 lever paragraph of ``code`` as having spent its one re-render.

    **This is the live state of the study database**, and it is what makes a stored failure final.
    From M19 WP-2 a stored failure caches the *verdict*, not the *attempt*: `render_and_check` will
    try again while any lever still has its durable re-render. What stops it for ever is
    `lever_paragraphs.attempts` reaching :data:`RENDER_ATTEMPTS_MAX` — which is exactly the
    situation `12220` was in on 2026-10-01, and the reason no button in the application could
    produce a different paragraph for it.

    So the T-12 refusal tests below set it up deliberately rather than relying on an unconditional
    short-circuit that no longer exists. The I3 claim they make is unchanged and is the one that
    matters: a stored failed variant never reaches a twin.
    """
    await backend.upsert(
        "lever_paragraphs",
        [
            {
                "lever": lever,
                "dial": dial,
                "style_version": style,
                "text": f"text for {lever}",
                "word_count": 60,
                "delta_hash": "h",
                "checker_pass": False,
                "attempts": twin_runtime.RENDER_ATTEMPTS_MAX,
            }
            for lever, dial in dials(code).items()
            if dial != 0
        ],
        on_conflict="lever,dial,style_version",
    )


# ------------------------------------------------------- render_and_check, the cache short-circuit


async def test_a_stored_failure_is_returned_as_a_failure_and_costs_no_model_call(backend):
    """The cache returns the stored verdict, so the gate downstream sees ``passed=False``. I3.

    With the paragraph budget spent, which is the state that makes the verdict final. The
    assertion that matters is unchanged: whatever comes back, `passed` is `False`.
    """
    await _store(backend, "01000", STYLE, FAILED_CHECKER)
    await _spend_the_budget(backend, "01000", STYLE)

    variant, report = await twin_runtime.render_and_check("01000", STYLE, backend=backend)

    assert report.passed is False, (
        "a stored failed variant came back as passing — every I3 gate downstream reads this flag"
    )
    assert report.containment == ["1.1.a"], "the stored report was not returned verbatim"
    assert variant.version_code == "01000"


async def test_an_exhausted_stored_failure_makes_no_model_call_at_all(backend, monkeypatch):
    """WP-2's cost claim, on the call counter. **Not even a coverage probe.**

    A re-entry on a cell whose every lever has spent its re-render must cost nothing: no design
    call and no coverage probe. The probe is the expensive half — one call per commitment, 24 of
    them on `12220` — so re-assembling the cell and re-checking it "just to be sure" would make a
    free, uninformative second press into an expensive, uninformative one.

    Proven by making the client explode. The budget is read before anything is assembled, so the
    client must never be reached.
    """
    await _store(backend, "01000", STYLE, FAILED_CHECKER)
    await _spend_the_budget(backend, "01000", STYLE)

    def _no_client(*args, **kwargs):
        raise AssertionError(
            "a model call was made for a cell whose paragraph budget was already spent"
        )

    monkeypatch.setattr("twinlab.agents.registry.get_client", _no_client)
    monkeypatch.setattr(twin_runtime, "get_client", _no_client)

    _, report = await twin_runtime.render_and_check("01000", STYLE, backend=backend)
    assert report.passed is False


async def test_a_stored_failure_is_retried_while_the_durable_budget_allows_it(backend):
    """WP-2, decision D1. **A stored failure is a cache of the verdict, not of the attempt.**

    Until 2026-10-03 the short-circuit was unconditional, which combined with "store the report
    pass or fail" to make a cell that failed once fail for ever — no path in the application to
    clear it, no event saying a second attempt was a cache hit, and nothing on screen
    distinguishing "genuinely unrenderable" from "unlucky once in September". Each half was
    defensible; together they were a trap, and that trap is what stopped the whole study.

    The concern the old test recorded — that a re-render could convert a recorded failure into a
    pass whose failure is nowhere in the evidence — is answered rather than dismissed:

    * the failing `variants` row is **not** deleted; `VariantRepo.put` appends the new verdict and
      the old row stays, because evidence is append-only (I9);
    * the re-render is bounded by `lever_paragraphs.attempts`, which is **durable**, so a restart
      cannot buy another one (the test above proves the exhausted case costs nothing);
    * a re-entry emits a `run_events` row saying it is a second look, so the press is visible.
    """
    await _store(backend, "01000", STYLE, FAILED_CHECKER)
    # No `_spend_the_budget`: every lever still has its one re-render.

    calls: list[str] = []

    class _Pool:
        """Stands in for the paragraph pool: records that the render path was entered."""

        style_version = STYLE

        def __init__(self) -> None:
            calls.append("pool")

    # The claim is about reaching the render path, not about what it produces — what it produces
    # depends on a model, which these tests never call.
    entered: list[str] = []
    real = twin_runtime._levers_with_budget

    async def _watch(code, pool):
        remaining = await real(code, pool)
        entered.append(f"{code}:{','.join(remaining)}")
        return remaining

    twin_runtime._levers_with_budget = _watch
    try:
        with contextlib.suppress(Exception):
            await twin_runtime.render_and_check("01000", STYLE, backend=backend)
    finally:
        twin_runtime._levers_with_budget = real

    assert entered, (
        "the re-render path was never entered for a stored failure with budget remaining — "
        "WP-2's whole point is that a cell which failed once can be retried after its cause is "
        "fixed"
    )
    # `01000` sets only Conditions, so only `L2` has a paragraph to re-render; the other four are
    # dial 0, which is a constant and is never generated (I5).
    assert entered[0] == "01000:L2", entered


# --------------------------------------------------------------- the quality gate's render step


async def test_the_quality_gate_refuses_a_stored_failed_variant(backend):
    """`services/quality._render_stimuli` stops the gate rather than showing a failed cell. I3.

    T-12, second of the three sites. The gate renders every H3 code before it scores a single
    twin, so a failed cell here must stop the whole gate — not be shown with a note.

    From M19 WP-4 the gate renders and reports **all six** before halting, so the failed code's
    budget is spent here to keep the test about the refusal rather than about a model call. The
    halt is unchanged: an H3 score over 15 of 18 items is a different measurement from one over
    18, and scoring the five that rendered would break the never-impute rule.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.quality import QualityGateError, _render_stimuli

    ref = reference()
    # Fail the FIRST H3 code the gate will reach, and store every other as passing so the only
    # thing that can stop the gate is the failed verdict.
    codes = list(ref.h3_version_codes)
    for code in [*codes, "00000", "SHAM"]:
        checker = dict(FAILED_CHECKER) if code == codes[0] else {"passed": True}
        await _store(backend, code, STYLE, checker)
    await _spend_the_budget(backend, codes[0], STYLE)

    events = EventLog("s-m17", backend)
    parent = await events.emit(stage="render", label="test parent")

    with pytest.raises(QualityGateError, match="did not pass the Checker"):
        await _render_stimuli("s-m17", ref, events, parent, backend, include_h2=False)


async def test_the_gate_reports_every_failed_stimulus_not_just_the_first(backend):
    """WP-4, decision D2. All six verdicts in one go.

    `12220` is the first entry in `h3_version_codes`, so raising on the first failure meant three
    renders that would also have failed were never attempted. The researcher was told about one
    bad code when two underlying lever paragraphs were bad and four of six codes were affected,
    and the real scale of the problem stayed invisible for a fortnight.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.quality import QualityGateError, _render_stimuli

    ref = reference()
    codes = list(ref.h3_version_codes)
    failing = {codes[0], codes[3]}
    # The two control stimuli are rendered by the gate too (RESEARCHER 2026-10-05). They are stored
    # as passing, so the test never reaches the design agent.
    for code in [*codes, "00000", "SHAM"]:
        await _store(
            backend, code, STYLE,
            dict(FAILED_CHECKER) if code in failing else {"passed": True},
        )
        if code in failing:
            await _spend_the_budget(backend, code, STYLE)

    events = EventLog("s-m17-all", backend)
    parent = await events.emit(stage="render", label="test parent")

    with pytest.raises(QualityGateError) as caught:
        await _render_stimuli("s-m17-all", ref, events, parent, backend, include_h2=False)

    message = str(caught.value)
    for code in sorted(failing):
        assert code in message, f"{code} failed and was not named: {message}"
    # The two control stimuli are checked by the same Checker, so they are in the total (+2).
    assert f"{len(failing)} of {len(codes) + 2}" in message

    rows = await backend.select("run_events", [("eq", "session_id", "s-m17-all")])
    errors = [r for r in rows if r.get("status") == "error"]
    assert len(errors) >= len(failing), (
        "every failed stimulus must emit its own error event, so the log shows the scale"
    )


# ----------------------------------------------------------------- SessionRunner, over the cache


async def test_the_session_runner_asks_no_twin_for_a_stored_failed_variant(backend):
    """T-12, third site — through the **real** `render_and_check`, not a stub.

    The existing orchestrator test supplies its own ``render_and_check`` and so proves only that
    the gate reads the flag it is handed. This drives the runner over the real cache read, which
    is the path a resumed or rerun session actually takes.
    """
    from twinlab.db.repositories import PanelRepo, SessionRepo
    from twinlab.orchestrator.loop import SessionRunner

    await _store(backend, "01000", STYLE, FAILED_CHECKER)
    await _spend_the_budget(backend, "01000", STYLE)

    sessions = SessionRepo(backend)
    session = await sessions.create(
        name="m17-t12",
        iterations=1,
        start_code="01000",
        panel_size=1,
        panel_seed=7,
        config={"style_version": STYLE, "wording": "A"},
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
