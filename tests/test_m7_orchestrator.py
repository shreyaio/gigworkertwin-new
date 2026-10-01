"""M7 — the orchestrator, budget, events and resume. `docs/11` M7.

The nine acceptance criteria are implemented verbatim, each named in its test, beside the tests that
prove each guard can fail.

The runner takes `render_and_check`, `ask_twin` and `analyse` as injected callables, so these tests
exercise **sequencing and checkpointing** — which is what M7 owns — with a counter standing in for
the provider. "It resumed" and "it resumed without re-asking" are different claims, and only a call
counter can tell them apart.
"""

from __future__ import annotations

import pytest

from twinlab.db.client import DbError
from twinlab.db.repositories import (
    AnswerRepo,
    PanelRepo,
    RunRepo,
    SessionRepo,
    VariantRepo,
)
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import PanelCandidate
from twinlab.models.variant import CheckerReport, LeverParagraph, RenderedVariant
from twinlab.orchestrator import budget as bud
from twinlab.orchestrator.events import (
    FORBIDDEN_KEYS,
    PAYLOAD_MAX_BYTES,
    EventLog,
    PayloadDiscipline,
    payload_size,
    redact,
    validate_tree,
)
from twinlab.orchestrator.loop import (
    CONTROL_CELLS,
    SessionAlreadyRunning,
    SessionRunner,
    clear_registry,
    register,
    request_stop,
    resume_interrupted_sessions,
)
from twinlab.orchestrator.odometer import index_from_code


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


def _candidates(n: int = 6) -> list[PanelCandidate]:
    """Eligible twins, two strata, deterministic ids."""
    out = []
    for i in range(n):
        city, service = ("Mumbai", "cab") if i % 2 == 0 else ("Pune", "bike")
        out.append(
            PanelCandidate(
                twin_id=f"UBR-{i:03d}", source="real", city=city, service=service,
                quality_passed=True,
            )
        )
    return out


def _variant(code: str, *, passed: bool = True) -> tuple[RenderedVariant, CheckerReport]:
    variant = RenderedVariant(
        version_code=code,
        style_version="v1",
        delta_hash="d" * 64,
        paragraphs={lv: LeverParagraph(text=f"Text for {lv}.") for lv in LEVER_BY_POSITION},
        dials=dict.fromkeys(LEVER_BY_POSITION, 1),
    )
    return variant, CheckerReport(passed=passed, notes="" if passed else "containment hit")


class Harness:
    """A runner wired to counting stubs. Counts every twin call so resume can be asserted."""

    def __init__(self, backend, *, fail_codes: frozenset[str] = frozenset(), answer_all=True):
        self.backend = backend
        self.fail_codes = fail_codes
        self.answer_all = answer_all
        self.twin_calls: list[tuple[str, str]] = []
        self.render_calls: list[str] = []
        self.sessions = SessionRepo(backend)
        self.runs = RunRepo(backend)
        self.answers = AnswerRepo(backend)
        self.panels = PanelRepo(backend)

    async def render_and_check(self, code: str, style_version: str):
        self.render_calls.append(code)
        return _variant(code, passed=code not in self.fail_codes)

    async def ask_twin(self, session, run_id, code, variant, member):
        self.twin_calls.append((code, member.twin_id))
        if not self.answer_all:
            return None
        return await self.answers.record(
            run_id=run_id, twin_id=member.twin_id,
            answers={"AMQ1": 5}, lever_order=[0, 1, 2, 3, 4], seed=1,
            wording="A", model="stub", retries=0,
        )

    async def analyse(self, run_id: str):
        return {"fairness": 0.2}, 0.25, None

    def runner(self, session_id: str) -> SessionRunner:
        return SessionRunner(
            session_id,
            backend=self.backend,
            render_and_check=self.render_and_check,
            ask_twin=self.ask_twin,
            analyse=self.analyse,
            candidates=lambda s: _candidates(),
        )


async def _session(harness: Harness, **kwargs):
    return await harness.sessions.create(
        name="test", iterations=kwargs.pop("iterations", 1),
        start_code=kwargs.pop("start_code", "10000"),
        panel_size=kwargs.pop("panel_size", 4), panel_seed=7,
        config={"style_version": "v1", "wording": "A"}, **kwargs,
    )


# ---------------------------------------------------------------- controls and the panel


async def test_a_fresh_session_freezes_its_panel_then_runs_00000_and_sham_first(backend):
    """`docs/11` M7, verbatim. `docs/03` §6.1 — the controls consume no iteration."""
    h = Harness(backend)
    session = await _session(h, iterations=1, start_code="10000")

    await h.runner(session.session_id).run()

    codes_in_order = [c for c, _ in h.twin_calls]
    first_three = []
    for code in codes_in_order:
        if code not in first_three:
            first_three.append(code)
    assert first_three[:2] == list(CONTROL_CELLS) == ["00000", "SHAM"]
    assert first_three[2] == "10000", "the swept code runs after both controls"

    # The controls did not consume the iteration.
    final = await h.sessions.get(session.session_id)
    assert final.completed == 1
    assert final.status == "completed"

    panel = await h.panels.get(session.session_id)
    assert len(panel) == 4
    assert [m.position for m in panel] == [0, 1, 2, 3]


async def test_the_panel_is_frozen_and_never_redrawn(backend):
    """I14 — a cell answered by a different set of twins is a different experiment."""
    h = Harness(backend)
    session = await _session(h)
    runner = h.runner(session.session_id)
    first = await runner.stage_panel(session)
    second = await runner.stage_panel(session)
    assert [m.twin_id for m in first] == [m.twin_id for m in second]

    with pytest.raises(DbError, match="drawn once"):
        await h.panels.freeze(session.session_id, first)


# ---------------------------------------------------------------- resume


async def test_a_stopped_session_resumes_without_re_asking_answered_twins(backend):
    """`docs/11` M7, verbatim — **assert on the LLM call count on resume.**

    The mechanism is `twin_answers`' unique index on `(run_id, twin_id, wording)`: the loop
    reads who
    answered and skips them. Counting calls is the only way to tell "resumed" from "resumed for
    free".
    """
    h = Harness(backend)
    session = await _session(h, iterations=3, start_code="10000")
    runner = h.runner(session.session_id)

    # Stop after the controls, mid-sweep.
    original = h.ask_twin
    async def ask_then_stop(s, run_id, code, variant, member):
        out = await original(s, run_id, code, variant, member)
        if code == "10000":
            runner.request_stop()
        return out
    h.ask_twin = ask_then_stop
    runner._ask_twin = ask_then_stop

    paused = await runner.run()
    assert paused.status == "paused"
    calls_before = len(h.twin_calls)
    assert calls_before > 0

    # Resume is just start. Same harness, so the counter carries over.
    h.ask_twin = original
    resumed_runner = h.runner(session.session_id)
    final = await resumed_runner.run()

    assert final.status == "completed"
    assert final.completed == 3

    # Every (code, twin) pair was asked EXACTLY once across both halves.
    assert len(h.twin_calls) == len(set(h.twin_calls)), (
        "a twin was re-asked on resume: the answered-twin skip is not working"
    )

    # And the cursor did not rewind.
    assert final.cursor_index == (index_from_code("10000") + 3) % 243


async def test_resuming_a_completed_run_spends_no_calls(backend):
    """`docs/04` §6 — the unique index is what makes resume free, not a cache in the eviction
    sense."""
    h = Harness(backend)
    session = await _session(h, iterations=1)
    await h.runner(session.session_id).run()
    spent = len(h.twin_calls)

    # Re-running the same session re-enters every run row and finds them completed.
    await h.sessions.set_status(session.session_id, "paused")
    await h.runner(session.session_id).run()
    assert len(h.twin_calls) == spent, "a completed run was re-asked"


async def test_stop_is_cooperative_and_leaves_the_cursor_at_the_next_unstarted_cell(backend):
    """`docs/04` §3.4 — it never kills mid-model-call, so no partial answer is written."""
    h = Harness(backend)
    session = await _session(h, iterations=5, start_code="10000")
    runner = h.runner(session.session_id)
    register(runner)

    async def ask_and_stop(s, run_id, code, variant, member):
        out = await h.answers.record(
            run_id=run_id, twin_id=member.twin_id, answers={"AMQ1": 5},
            lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub",
        )
        h.twin_calls.append((code, member.twin_id))
        if code == "10000":
            assert request_stop(session.session_id) is True
        return out
    runner._ask_twin = ask_and_stop

    result = await runner.run()
    assert result.status == "paused"
    assert result.completed < 5

    # The stop lands on the FIRST of this session's four panel twins, so three were never asked.
    # The cell is therefore unfinished, not smaller: it goes back to `pending` so resume asks the
    # three that are left. Completing it here would be permanent — `execute_run` skips a
    # `completed` run on resume — and would leave one cell answered by one twin while its
    # neighbours were answered by four, which is a different experiment under the same version
    # code (I14). This assertion previously read `== "completed"`, which encoded that defect.
    runs = {r.version_code: r.status for r in await h.runs.for_session(session.session_id)}
    assert runs["10000"] == "pending"
    assert len({t for c, t in h.twin_calls if c == "10000"}) < 4


async def test_a_stop_mid_panel_resumes_and_asks_only_the_twins_that_are_left(backend):
    """I14 — a cell interrupted mid-panel is finished by the full panel, and nobody is re-asked."""
    h = Harness(backend)
    session = await _session(h, iterations=1, start_code="10000")
    runner = h.runner(session.session_id)
    register(runner)

    async def ask_and_stop(s, run_id, code, variant, member):
        out = await h.answers.record(
            run_id=run_id, twin_id=member.twin_id, answers={"AMQ1": 5},
            lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub",
        )
        h.twin_calls.append((code, member.twin_id))
        if code == "10000":
            assert request_stop(session.session_id) is True
        return out
    runner._ask_twin = ask_and_stop
    await runner.run()

    asked_before = [t for c, t in h.twin_calls if c == "10000"]
    assert len(asked_before) == 1

    await h.runner(session.session_id).run()

    asked_after = [t for c, t in h.twin_calls if c == "10000"]
    assert len(asked_after) == 4, "resume did not finish the panel"
    assert len(set(asked_after)) == 4, "resume re-asked a twin that had already answered"

    runs = {r.version_code: r for r in await h.runs.for_session(session.session_id)}
    assert runs["10000"].status == "completed"
    assert runs["10000"].twins_n == 4


def test_requesting_a_stop_on_an_unregistered_session_is_false():
    """A stop for a session this process is not running is reported, not silently swallowed."""
    assert request_stop("not-a-session") is False


# ---------------------------------------------------------------- crash recovery


async def test_a_session_left_running_is_paused_and_never_auto_restarted(backend):
    """`docs/11` M7, verbatim, and `docs/04` §3.4.

    Auto-restarting would begin spending credits on a process nobody asked to start.
    """
    h = Harness(backend)
    session = await _session(h)
    await h.sessions.set_status(session.session_id, "running")

    paused = await resume_interrupted_sessions(backend)
    assert paused == [session.session_id]
    assert (await h.sessions.get(session.session_id)).status == "paused"

    events = await EventLog(session.session_id, backend).since(0)
    interrupted = [e for e in events if "interrupted" in e["label"]]
    assert len(interrupted) == 1
    assert interrupted[0]["status"] == "error"
    assert interrupted[0]["payload"]["auto_restarted"] is False

    # Nothing started it: no runner is registered and no run row appeared.
    assert await h.runs.for_session(session.session_id) == []


async def test_a_second_concurrent_session_is_rejected_not_queued(backend):
    """`docs/04` §3.1 — with one provider slot, two sessions interleave and both crawl."""
    h = Harness(backend)
    a = await _session(h)
    b = await _session(h)
    register(h.runner(a.session_id))
    with pytest.raises(SessionAlreadyRunning, match="max_active_sessions"):
        register(h.runner(b.session_id))


async def test_max_concurrency_is_one_and_the_pool_is_correct_at_one(backend):
    """`docs/11` M7, verbatim. 1 is the tested default, not an edge case."""
    from config.settings import settings

    assert settings.max_concurrency == 1

    h = Harness(backend)
    session = await _session(h, iterations=1, panel_size=4)
    runner = h.runner(session.session_id)
    assert runner.sem._value == 1

    overlap = {"max": 0, "now": 0}

    async def ask_watching(s, run_id, code, variant, member):
        overlap["now"] += 1
        overlap["max"] = max(overlap["max"], overlap["now"])
        try:
            return await h.ask_twin(s, run_id, code, variant, member)
        finally:
            overlap["now"] -= 1
    runner._ask_twin = ask_watching

    await runner.run()
    assert overlap["max"] == 1, "two twin calls overlapped at max_concurrency=1"
    assert runner.calls_made == len(h.twin_calls)


# ---------------------------------------------------------------- failure handling


async def test_a_checker_failure_marks_that_run_failed_and_the_loop_continues(backend):
    """`docs/11` M7, verbatim, and I3 — an unverified variant never reaches a twin."""
    h = Harness(backend, fail_codes=frozenset({"10000"}))
    session = await _session(h, iterations=2, start_code="10000")
    final = await h.runner(session.session_id).run()

    assert final.status == "completed"
    runs = {r.version_code: r for r in await h.runs.for_session(session.session_id)}
    assert runs["10000"].status == "failed"
    assert "checker failed" in runs["10000"].error
    assert runs["10001"].status == "completed", "the loop continued to the next code"

    # No twin was asked for the failed cell.
    assert not [c for c, _ in h.twin_calls if c == "10000"]


async def test_a_run_where_every_twin_failed_is_failed_never_completed(backend):
    """`docs/11` M7, verbatim, and I15. `twins_n = 0` is a failure, never an index of 0.000."""
    h = Harness(backend, answer_all=False)
    session = await _session(h, iterations=1, start_code="10000")
    final = await h.runner(session.session_id).run()

    runs = {r.version_code: r for r in await h.runs.for_session(session.session_id)}
    for code in ("00000", "SHAM", "10000"):
        assert runs[code].status == "failed"
        assert runs[code].twins_n == 0
        assert runs[code].index_value is None
        assert "I15" in runs[code].error
    assert final.status == "completed"      # the SESSION finished; every cell failed


async def test_the_ddl_constraint_rejects_a_completed_run_with_no_twins(backend):
    """`docs/11` M7, verbatim: "assert the DDL constraint rejects it too."

    Mirrored in the in-memory backend because an invariant enforced only in Postgres would be
    exactly the one CI never tests — and I15 is the one the prototype broke.
    """
    h = Harness(backend)
    session = await _session(h)
    run = await h.runs.get_or_create(session.session_id, "10000")

    with pytest.raises(DbError, match="twins"):
        await h.runs.complete(run.run_id, twins_n=0, index_value=0.0)
    with pytest.raises(DbError, match="runs_completed_has_twins"):
        await backend.update(
            "runs", {"status": "completed", "twins_n": 0}, [("eq", "run_id", run.run_id)]
        )


async def test_a_twin_whose_call_raises_fails_for_that_cell_only(backend):
    """`docs/04` §5.3 — the sweep continues, and only the quality gate drops twins."""
    h = Harness(backend)
    session = await _session(h, iterations=1, panel_size=4)
    runner = h.runner(session.session_id)

    async def flaky(s, run_id, code, variant, member):
        h.twin_calls.append((code, member.twin_id))
        if member.twin_id == "UBR-000":
            raise RuntimeError("provider exploded")
        return await h.answers.record(
            run_id=run_id, twin_id=member.twin_id, answers={"AMQ1": 5},
            lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub",
        )
    runner._ask_twin = flaky

    await runner.run()
    runs = {r.version_code: r for r in await h.runs.for_session(session.session_id)}
    assert runs["10000"].status == "completed"
    assert runs["10000"].twins_n == 3, "the cell completed with the twins that answered"

    # The twin is still on the panel: a failed call is not a dropped twin.
    assert "UBR-000" in {m.twin_id for m in await h.panels.get(session.session_id)}


# ---------------------------------------------------------------- the event tree


async def test_run_events_form_a_valid_tree(backend):
    """`docs/11` M7, verbatim: every `parent_event_id` resolves, no cycles."""
    h = Harness(backend)
    session = await _session(h, iterations=2)
    await h.runner(session.session_id).run()

    events = await EventLog(session.session_id, backend).since(0)
    assert len(events) > 10
    validate_tree(events)

    assert {e["event_id"] for e in events if e["parent_event_id"] is None}
    assert any(e["parent_event_id"] is not None for e in events)


def test_the_tree_validator_rejects_a_dangling_parent_and_a_cycle():
    """A validator that cannot fail is not a validator."""
    with pytest.raises(ValueError, match="does not resolve"):
        validate_tree([{"event_id": 2, "parent_event_id": 99}])
    with pytest.raises(ValueError, match="its own parent"):
        validate_tree([{"event_id": 1, "parent_event_id": 1}])
    with pytest.raises(ValueError, match="cycle"):
        validate_tree([
            {"event_id": 1, "parent_event_id": 2},
            {"event_id": 2, "parent_event_id": 1},
        ])
    with pytest.raises(ValueError, match="duplicate"):
        validate_tree([{"event_id": 1, "parent_event_id": None}] * 2)


async def test_events_are_polled_incrementally(backend):
    """`docs/04` §7.3 — never re-fetch the whole stream."""
    log = EventLog("s-poll", backend)
    await backend.insert("sessions", [{"session_id": "s-poll", "name": "x", "config": {}}])
    first = await log.emit(stage="control", label="one")
    second = await log.emit(stage="control", label="two")
    assert [e["event_id"] for e in await log.since(first)] == [second]
    assert len(await log.since(0)) == 2


async def test_a_parent_label_is_rewritten_in_place(backend):
    """`docs/04` §7 — one ticking row, not a thousand rows to scroll."""
    h = Harness(backend)
    session = await _session(h, iterations=1)
    await h.runner(session.session_id).run()
    events = await EventLog(session.session_id, backend).since(0)
    reconstruction = [e for e in events if e["stage"] == "reconstruction"]
    assert len(reconstruction) == 1, "reconstruction emitted one row per twin instead of ticking"
    assert reconstruction[0]["status"] == "ok"
    assert "twins" in reconstruction[0]["label"]


# ---------------------------------------------------------------- payload discipline


async def test_no_payload_exceeds_8kb_or_contains_a_body(backend):
    """`docs/11` M7, verbatim, and `docs/04` §7.2.

    Not a size optimisation: at panel scale the prompt bodies alone would exhaust the free tier, and
    the round prompt is **rebuilt** from stored fields rather than stored (I11).
    """
    h = Harness(backend)
    session = await _session(h, iterations=2)
    await h.runner(session.session_id).run()

    events = await EventLog(session.session_id, backend).since(0)
    for event in events:
        payload = event.get("payload")
        if payload is None:
            continue
        assert payload_size(payload) <= PAYLOAD_MAX_BYTES
        for key in payload:
            assert key.lower() not in FORBIDDEN_KEYS, f"{key} is a body, not a reference"

    # And nothing carried the scenario text, which is what the paragraphs actually say.
    blob = str(events)
    assert "Text for L1." not in blob


def test_redact_raises_on_a_body_and_truncates_on_size():
    """Two different failures, handled differently on purpose (`docs/04` §7.2)."""
    for key in ("prompt", "persona_passage", "answers", "scenario"):
        with pytest.raises(PayloadDiscipline, match=key):
            redact({key: "x"})

    # Non-strict drops it with a marker, for the error path that must not fail a run
    # over a single log line.
    out = redact({"prompt": "x", "keep": 1}, strict=False)
    assert out == {"keep": 1, "redacted": ["prompt"]}

    big = redact({"huge": "x" * (PAYLOAD_MAX_BYTES * 2), "delta_hash": "d" * 64})
    assert big["truncated"] is True
    assert payload_size(big) <= PAYLOAD_MAX_BYTES
    assert big["delta_hash"] == "d" * 64, "the reference survived; the body was shed"


async def test_the_backend_rejects_an_oversize_payload(backend):
    """`run_events_payload_small`, mirrored from the DDL so CI tests it."""
    await backend.insert("sessions", [{"session_id": "s-big", "name": "x", "config": {}}])
    with pytest.raises(DbError, match="run_events_payload_small"):
        await backend.insert("run_events", [{
            "session_id": "s-big", "stage": "control", "label": "x", "status": "ok",
            "payload": {"blob": "x" * (PAYLOAD_MAX_BYTES + 100)},
        }])


# ---------------------------------------------------------------- budget


def test_budget_returns_calls_tokens_seconds_and_cache_hits():
    """`docs/11` M7, verbatim."""
    b = bud.sweep_budget(iterations=10, panel_size=20)
    assert b.calls > 0
    assert b.tokens_in == b.calls * bud.TOKENS_IN_PER_CALL
    assert b.tokens_out == b.calls * bud.TOKENS_OUT_PER_CALL
    assert b.est_seconds == b.calls * bud.SECONDS_PER_CALL
    assert b.est_credits is None, "the free-tier rate is unpublished; None, never a guess"
    assert b.cache_hits == 0


def test_the_cache_hit_count_matches_the_calls_actually_skipped():
    """`docs/11` M7, verbatim: "its cache-hit count matches the calls actually skipped."."""
    full = bud.sweep_budget(iterations=10, panel_size=20, include_controls=False)
    partial = bud.sweep_budget(
        iterations=10, panel_size=20, include_controls=False, answered_already=120
    )
    assert partial.cache_hits == 120
    assert full.calls - partial.calls == 120, (
        "the hits must be exactly the calls not made"
    )

    # Paragraph cache hits are counted too, and they are capped at the ten that exist (I4).
    cached = bud.render_budget(paragraphs_cached=4)
    assert cached.calls == 6 and cached.cache_hits == 4
    assert bud.render_budget(paragraphs_cached=99).calls == 0


def test_a_full_sweep_is_about_the_number_docs_10_quotes():
    """`docs/10` §2 — ~4,860 twin calls at the default panel. A sanity anchor on the arithmetic."""
    b = bud.full_sweep_budget(panel_size=20, include_controls=False)
    assert b.calls == 243 * 20 + bud.DESIGN_CALLS_PER_STYLE_VERSION


def test_the_budget_warns_before_it_blocks():
    """`docs/10` §7 — a warning is information; refusing to start moves the decision out of the
    researcher's hands."""
    long = bud.sweep_budget(iterations=243, panel_size=100)
    assert long.est_seconds > bud.LONG_RUN_SECONDS
    assert any("concurrent request" in w for w in long.warnings)

    dropped = bud.sweep_budget(
        iterations=1, panel_size=20, dropped_twins_in_panel=["UBR-001"]
    )
    assert any("I14" in w for w in dropped.warnings)

    changed = bud.sweep_budget(iterations=1, panel_size=20, config_changed=True)
    assert any("config has changed" in w for w in changed.warnings)


def test_the_quality_gate_is_the_dominant_cost_not_the_sweep():
    """`docs/10` — 18 calls per twin at the default repeats, 9,000 at N=500."""
    q = bud.quality_budget(twins=500, repeats=3)
    assert q.calls == 500 * bud.H3_CALLS_PER_REPEAT * 3 == 9000
    assert bud.quality_budget(twins=500, repeats=3, already_scored=500).calls == 0
    assert bud.full_sweep_budget(panel_size=20).calls < q.calls


# ---------------------------------------------------------------- the variant cache key


async def test_re_storing_a_variant_keeps_its_variant_id(backend):
    """`variants.variant_id` is minted once. `runs.variant_id` references it.

    This was an upsert carrying a fresh uuid in every payload. PostgREST resolves a conflict with
    ``DO UPDATE SET`` over every column supplied, so the second store of a cell rewrote the
    primary key a `runs` row already pointed at — and the orchestrator stores on **every** run of
    a code, so a resume, a rerun or a second iteration would have hit the foreign key. Invisible
    in memory, because `InMemoryBackend` has none.
    """
    repo = VariantRepo(backend)
    first = await repo.put(
        version_code="10000", style_version="v1", delta_spec={"version_code": "10000"},
        delta_hash="h1", paragraphs={"L1": "one"}, checker={"passed": True},
    )
    again = await repo.put(
        version_code="10000", style_version="v1", delta_spec={"version_code": "10000"},
        delta_hash="h2", paragraphs={"L1": "two"}, checker={"passed": True},
    )

    assert again["variant_id"] == first["variant_id"], "the primary key was rewritten"
    assert await backend.count("variants") == 1, "the cache key did not hold"
    assert again["delta_hash"] == "h2", "the re-store did not update the row"

    stored = await repo.get("10000", "v1")
    assert stored["variant_id"] == first["variant_id"]
    assert stored["paragraphs"] == {"L1": "two"}
