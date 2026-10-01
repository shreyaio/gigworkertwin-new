"""M18 — `ARCHITECTURE_UPDATE.md`. The usability fixes, the Studio override and the guards.

Grouped by the plan's own sections so a failure names the thing it is defending:

* **§2** the quality budget explains itself; the number does not change.
* **§3.1** the Agents tab's poll is idempotent in the DOM and silent when idle (U-1, U-2).
* **§3.3** a deterministic database refusal is raised once, not retried four times (U-4's "one log
  line not four").
* **§3.4** deleting synthetic surveys takes `studio_runs` with it and refuses evidence by sentence
  (U-3, U-4).
* **§3.5** eligibility is checked **before** a `sessions` row is written, and a background death
  reaches the log tree (U-5, U-6).
* **§3.6** the population is visible, and never defaulted by code.
* **§4** Twin Studio: render on demand, results that count, and the walls that stay.
* **§5** Agent Studio: the Twin Interviewer shows its result, the Designer shows the paragraph.

Every test runs on `InMemoryBackend` with a stub model. No live LLM and no live DB, ever
(`CLAUDE.md` → Testing).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "twinlab"


# =================================================================== helpers


async def _twin(backend, twin_id: str, *, source: str = "synthetic") -> None:
    await backend.insert(
        "twins",
        [{
            "twin_id": twin_id,
            "source": source,
            "service": "Uber Go",
            "city": "Mumbai",
            "consent_twin": True,
            "persona_passage": "A persona passage.",
            "persona_hash": "abc123",
        }],
    )


async def _passed(backend, twin_id: str) -> None:
    """Give a twin a `kept` H3 verdict, which is the second half of panel eligibility."""
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": twin_id, "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
        }],
    )


# =================================================================== §2 the budget


async def test_the_quality_budget_explains_its_own_total(backend):
    """§2: *"for 50 twins (2 calls each) it will have 600 calls"* — the total is right.

    `6 × 2 × 50 = 600`, and the 6 is the six Part-17 stimuli at one model call each reading three
    holdout items per round (`docs/08`'s 18 H3 numbers), **not** a repeat count. The plan is
    explicit
    that nothing about the number changes; what changes is that it says how it was reached.
    """
    from twinlab.services.runs import quality_budget_view

    view = await quality_budget_view(twins=50, repeats=2)
    assert view.calls == 600, "the number is correct and must not be quietly reduced"
    assert "6 Part-17 versions" in view.breakdown
    assert "2 repeat(s)" in view.breakdown
    assert "50 twin(s)" in view.breakdown
    assert view.per_unit == "12", "12 calls per twin is the figure a researcher decides against"


async def test_the_sweep_budget_names_the_two_control_cells(backend):
    """The sweep total is not iterations × panel, because `00000` and `SHAM` run too."""
    from twinlab.services.runs import sweep_budget_view

    view = await sweep_budget_view(iterations=6, panel_size=20)
    assert "00000" in view.breakdown and "SHAM" in view.breakdown


# =================================================================== §3.1 the poll


def test_the_agents_tab_timer_starts_inactive_and_is_woken_by_a_button():
    """U-1: **an idle Agents page must make zero database calls.**

    Asserted over the source because the behaviour is a Gradio wiring property: a `gr.Timer` that
    is `active=True` at build time polls forever whether or not anything is running, which is what
    produced 133 HTTP/2 streams on one connection (§3.2).
    """
    source = (SRC / "ui" / "pages" / "lab.py").read_text(encoding="utf-8")
    assert "gr.Timer(POLL_SECONDS, active=False)" in source, (
        "the Agents tab's timer must be off at build time; an idle page polls nothing"
    )
    assert "gr.Timer(3.0, active=True)" not in source
    # And something must switch it on, or the log would never move.
    assert "gr.Timer(POLL_SECONDS, active=True)" in source


def test_the_poll_skips_every_output_when_nothing_moved():
    """§3.1 points 1–3: an unchanged tick returns `gr.skip()` for **every** output.

    Gradio replaces a returned output's whole DOM subtree whether its value changed or not, so a
    seven-output tick every three seconds reset scroll position, collapsed open elements and stole
    focus on an idle page. The fingerprint is what makes a tick a no-op.
    """
    import ast

    source = (SRC / "ui" / "pages" / "lab.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    poll = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_poll"
    )
    # `ast.unparse` normalises quoting, so the fingerprint comparison is matched on the raw
    # source and the ordering on the unparsed body.
    assert "before.get(\"log\") == after[\"log\"]" in source, (
        "the unchanged branch must compare a fingerprint, not re-render and hope"
    )
    body = ast.unparse(poll)
    assert "gr.skip()" in body
    # The expensive reads must sit AFTER the early return, or the tick still costs 13 calls.
    early = body.index("gr.skip(), gr.skip()")
    assert body.index("agent_cards()") > early
    assert body.index("lab_status()") > early


# =================================================================== §3.3 retry classification


@pytest.mark.parametrize(
    "code",
    ["23503", "23505", "23514", "22P02", "42703", "42P01", "PGRST205"],
)
def test_a_deterministic_database_error_is_never_retried(code):
    """§3.3: a SQLSTATE in class 23, 22 or 42 fails identically every time.

    This is why one blocked delete printed the same foreign-key violation four times across ~5
    seconds before reporting it. Retrying a `23503` is four times the latency for no chance of
    success, and it buries the one sentence the researcher needed.
    """
    from twinlab.db.client import is_permanent

    class APIError(Exception):
        def __init__(self, c):
            self.code = c
            super().__init__({"code": c, "message": "boom"})

    assert is_permanent(APIError(code)) is True


@pytest.mark.parametrize(
    "text",
    [
        "ConnectionTerminated(error_code:0, last_stream_id:133)",
        "[WinError 10035] A non-blocking socket operation could not be completed",
        "ReadTimeout",
        "Server disconnected without sending a response",
    ],
)
def test_a_transport_failure_is_still_retried(text):
    """The other half, and the one that matters more: a dead session costs more than three retries.

    An **unrecognised** failure is treated as transient for the same reason — the cost of retrying a
    transient error wrongly classified as permanent is a sweep that stops.
    """
    from twinlab.db.client import is_permanent

    assert is_permanent(Exception(text)) is False
    assert is_permanent(Exception("something nobody has seen before")) is False


def test_a_mis_mapped_filter_operator_is_permanent():
    """`AttributeError` from the filter-method map is a bug in `db/client.py`, not a flaky network.

    Retrying it four times is how that class of defect stayed invisible for a release
    (`FILTER_METHODS`' own docstring).
    """
    from twinlab.db.client import is_permanent

    assert is_permanent(AttributeError("object has no attribute 'in'")) is True


async def test_the_retry_loop_calls_a_permanent_failure_exactly_once():
    """U-4's "**one** log line not four", asserted on a call counter.

    `retrying` is module level precisely so this can be tested: `tests/conftest.py` forbids the
    suite
    from constructing a `SupabaseBackend` at all, so a policy that lived only on the method would be
    the one piece of the database boundary with no test.
    """
    from twinlab.db.client import DbError, retrying

    calls = {"n": 0}

    def _fk_violation():
        calls["n"] += 1
        exc = Exception({"code": "23503", "message": "violates foreign key constraint"})
        exc.code = "23503"
        raise exc

    with pytest.raises(DbError, match="refused the call"):
        await retrying(_fk_violation, attempts=4, sleep=_no_sleep)
    assert calls["n"] == 1, f"a 23503 was attempted {calls['n']} times; it can only ever fail"


async def test_the_retry_loop_does_retry_a_transient_failure():
    """And the complement, so the classification is tested in both directions."""
    from twinlab.db.client import DbError, retrying

    calls = {"n": 0}

    def _flaky():
        calls["n"] += 1
        raise Exception("ConnectionTerminated(last_stream_id:133)")

    with pytest.raises(DbError, match="after 4 attempts"):
        await retrying(_flaky, attempts=4, sleep=_no_sleep)
    assert calls["n"] == 4


async def _no_sleep(_delay: float) -> None:
    """Injected so the backoff is not actually waited out."""
    return None


# =================================================================== §3.4 the delete


async def test_a_studio_run_does_not_block_deleting_a_synthetic_twin(backend):
    """U-3: `studio_runs` goes **with** the twin, and reports its count.

    The live failure: `studio_runs_twin_id_fkey` on `SYN-30092026-0000`, with six sandbox rows
    against it. `delete_synthetic` reasoned carefully about `runs` and concluded "no run is touched"
    — true, and not the problem. `studio_runs` was simply never considered.
    """
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.surveys import delete_synthetic

    await backend.insert(
        "survey_submissions",
        [{"submission_id": "SYN-1", "data_type": SYNTHETIC_DATA_TYPE}],
    )
    await _twin(backend, "SYN-1")
    await backend.insert(
        "studio_runs",
        [{
            "studio_run_id": f"sr{i}", "twin_id": "SYN-1", "version_code": "01000",
            "questions": [], "model": "mock", "seed": 1,
        }
            for i in range(6)
        ],
    )

    result = await delete_synthetic(backend)
    assert result["twins"] == 1
    assert result["studio_runs"] == 6, "a Studio conversation about a deleted twin is not evidence"
    assert result["blocked"] == []
    assert await backend.count("studio_runs") == 0
    assert await backend.count("twins") == 0


async def test_an_answered_twin_refuses_the_delete_by_message(backend):
    """U-4: it refuses **with the sentence**, deletes nothing, and names the twins.

    The message, not the exception type, is what is asserted: a researcher reading
    `23503 studio_runs_twin_id_fkey` four times learned nothing about what to do.
    """
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.surveys import DeleteBlocked, delete_synthetic

    await backend.insert(
        "survey_submissions",
        [
            {"submission_id": "SYN-1", "data_type": SYNTHETIC_DATA_TYPE},
            {"submission_id": "SYN-2", "data_type": SYNTHETIC_DATA_TYPE},
        ],
    )
    await _twin(backend, "SYN-1")
    await _twin(backend, "SYN-2")
    await backend.insert(
        "sessions", [{"session_id": "s1", "name": "s", "config": {}}]
    )
    await backend.insert(
        "runs", [{"run_id": "r1", "session_id": "s1", "version_code": "01000"}]
    )
    await backend.insert(
        "twin_answers",
        [{
            "run_id": "r1", "twin_id": "SYN-1", "answers": {"FAIR1": 5},
            "lever_order": [], "seed": 1, "wording": "A", "model": "mock",
        }],
    )

    with pytest.raises(DeleteBlocked) as caught:
        await delete_synthetic(backend)
    message = str(caught.value)
    assert "1 of 2 synthetic twins cannot be deleted" in message
    assert "have answered a run" in message
    assert "SYN-1" in message
    assert "Delete the other 1" in message
    # Nothing at all was deleted. A partial delete the researcher did not ask for is worse than a
    # refusal.
    assert await backend.count("twins") == 2
    assert await backend.count("survey_submissions") == 2


async def test_skip_blocked_deletes_the_rest_and_keeps_the_blocked_record_whole(backend):
    """The second press. A blocked twin keeps its submission and its answers too.

    A twin whose survey answers have been deleted is no longer a lossless reconstruction of
    anything, and its persona is rebuilt from those rows (I6). "Cannot be deleted" has to mean the
    whole record.
    """
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.surveys import delete_synthetic

    await backend.insert(
        "survey_submissions",
        [
            {"submission_id": "SYN-1", "data_type": SYNTHETIC_DATA_TYPE},
            {"submission_id": "SYN-2", "data_type": SYNTHETIC_DATA_TYPE},
        ],
    )
    await backend.insert(
        "survey_answers",
        [
            {"submission_id": "SYN-1", "item_id": "FAIR1", "value_num": 4},
            {"submission_id": "SYN-2", "item_id": "FAIR1", "value_num": 5},
        ],
    )
    await _twin(backend, "SYN-1")
    await _twin(backend, "SYN-2")
    await backend.insert("sessions", [{"session_id": "s1", "name": "s", "config": {}}])
    await backend.insert(
        "runs", [{"run_id": "r1", "session_id": "s1", "version_code": "01000"}]
    )
    await backend.insert(
        "twin_answers",
        [{
            "run_id": "r1", "twin_id": "SYN-1", "answers": {"FAIR1": 5},
            "lever_order": [], "seed": 1, "wording": "A", "model": "mock",
        }],
    )

    result = await delete_synthetic(backend, skip_blocked=True)
    assert result["twins"] == 1 and result["blocked"] == ["SYN-1"]
    kept = await backend.select("twins", None)
    assert [r["twin_id"] for r in kept] == ["SYN-1"]
    # SYN-1's whole record survives; SYN-2's is gone.
    assert [r["submission_id"] for r in await backend.select("survey_submissions", None)] == [
        "SYN-1"
    ]
    assert [r["submission_id"] for r in await backend.select("survey_answers", None)] == ["SYN-1"]
    assert await backend.count("twin_answers") == 1, "evidence is untouched (rule 6)"


async def test_a_panel_member_also_blocks_the_delete(backend):
    """I14: a twin cannot vanish from under a session's frozen panel."""
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.surveys import DeleteBlocked, delete_synthetic

    await backend.insert(
        "survey_submissions",
        [{"submission_id": "SYN-1", "data_type": SYNTHETIC_DATA_TYPE}],
    )
    await _twin(backend, "SYN-1")
    await backend.insert("sessions", [{"session_id": "s1", "name": "s", "config": {}}])
    await backend.insert(
        "session_panel",
        [{"session_id": "s1", "twin_id": "SYN-1", "stratum": "Mumbai|cab", "position": 0}],
    )

    with pytest.raises(DeleteBlocked, match="frozen analysis panel"):
        await delete_synthetic(backend)


# =================================================================== §3.5 the pre-flight


async def test_starting_a_sweep_with_no_eligible_twins_creates_no_session_row(backend):
    """U-5: a clean in-page message, and **no `sessions` row**.

    §3.5 defect 2: `start_sweep` created the row, spawned the task, and *then* the draw failed —
    leaving a permanent `sessions` row for a job that never ran, which a reader cannot tell from one
    that failed halfway.
    """
    from twinlab.services.runs import NotReadyToSweep, start_sweep

    for i in range(50):
        await _twin(backend, f"SYN-{i}")  # synthetic, and none quality-passed

    with pytest.raises(NotReadyToSweep) as caught:
        await start_sweep(iterations=6, name="Six versions", backend=backend)

    assert await backend.count("sessions") == 0, "a refusal must leave nothing behind"
    message = str(caught.value)
    # §3.5: the message names the REAL blocker, not the symptom. "No eligible twins for population
    # 'real'" is true and tells a researcher looking at 50 synthetic twins nothing.
    assert "0 of 50 twins have passed the quality test" in message
    assert "Agents → Run twin quality test" in message
    assert "all 50 synthetic" in message


async def test_the_pre_flight_separates_the_two_reasons_the_pool_is_empty(backend):
    """`eligible_candidates` wants source **and** `quality_passed`; the pool was empty twice over.

    Counting them separately is what lets the message say which one to fix.
    """
    from twinlab.services.runs import check_eligibility

    for i in range(3):
        await _twin(backend, f"SYN-{i}")
    await _passed(backend, "SYN-0")

    real = await check_eligibility("real", 1, backend=backend)
    assert real["ok"] is False
    assert real["quality_passed"] == 1 and real["eligible"] == 0
    assert "none of them is in population 'real'" in real["reason"]

    synthetic = await check_eligibility("synthetic", 1, backend=backend)
    assert synthetic["ok"] is True
    assert synthetic["eligible"] == 1
    assert synthetic["by_source"] == {"synthetic": 3}


async def test_the_pre_flight_refuses_a_panel_bigger_than_the_pool(backend):
    """I14: a panel of 15 recorded as 20 would misstate the study, so it is refused, not shrunk."""
    from twinlab.services.runs import check_eligibility

    for i in range(3):
        await _twin(backend, f"SYN-{i}")
        await _passed(backend, f"SYN-{i}")
    result = await check_eligibility("synthetic", 20, backend=backend)
    assert result["ok"] is False
    assert "3 twin(s) are eligible for a panel of 20" in result["reason"]


async def test_the_pre_flight_writes_nothing_at_all(backend):
    """A pure read. It is called on a confirm step, before the researcher has decided anything."""
    from twinlab.services.runs import check_eligibility

    await _twin(backend, "SYN-0")
    # Non-empty tables only: a read creates the empty list for a table it touches, which is the
    # mirror's bookkeeping and not a write.
    def _rows():
        return {t: len(r) for t, r in backend.tables.items() if r}

    before = _rows()
    await check_eligibility("real", 20, backend=backend)
    assert _rows() == before


async def test_a_background_session_failure_appears_in_the_log_tree(backend):
    """U-6: force a background task to raise; the failure must reach `run_events`.

    §3.5 defect 1: `_spawn`'s done-callback called `log.error` and nothing else, so the researcher
    saw a session appear and never move. Console-only failure reporting is why
    `InsufficientEligibleTwins` went unexplained.
    """
    from twinlab.services.runs import _spawn, events_since

    await backend.insert(
        "sessions", [{"session_id": "s1", "name": "doomed", "config": {}}]
    )

    async def _boom():
        raise RuntimeError("the panel could not be drawn")

    task = _spawn(_boom(), session_id="s1", backend=backend)
    with pytest.raises(RuntimeError):
        await task
    # The done-callback's reporter is a separate task; let the loop run it.
    for _ in range(10):
        await asyncio.sleep(0)
        if await backend.count("run_events"):
            break

    rows = await events_since("s1", 0, backend=backend)
    assert rows, "a background death must appear in the log tree, not only the console"
    assert rows[0].status == "error"
    assert "the panel could not be drawn" in rows[0].message
    session = (await backend.select("sessions", [("eq", "session_id", "s1")]))[0]
    assert session["status"] == "failed"


# =================================================================== §3.6 the population


async def test_the_population_counts_are_reported_without_choosing_one(backend):
    """§3.6 and §1.3: the state is made **visible**; nothing picks a population.

    Which population a study sweep runs on is a research decision. A synthetic-only database is
    deliberately not defaulted to `synthetic` by code.
    """
    from twinlab.services.runs import population_counts

    for i in range(3):
        await _twin(backend, f"SYN-{i}", source="synthetic")
    await _twin(backend, "R-1", source="real")
    await _twin(backend, "M-1", source="manual")
    await _passed(backend, "SYN-0")

    line = await population_counts(backend)
    assert "real: 1" in line
    assert "synthetic: 3" in line
    assert "passed the quality gate: 1" in line
    # `manual` is in no population, so it is reported separately rather than silently omitted — a
    # count that does not add up is a reason to doubt the screen.
    assert "manual (never on a panel): 1" in line


def test_the_sweep_confirm_step_shows_the_population_as_a_control():
    """§3.6: an explicit control on the confirm step, with the live counts beside it."""
    source = (SRC / "ui" / "pages" / "lab.py").read_text(encoding="utf-8")
    assert 'choices=["real", "synthetic", "both"]' in source
    assert "population_counts()" in source
    assert "_stored_population()" in source, (
        "it must default to the stored value, never to a value the code picked"
    )


def test_the_poll_switches_the_timer_off_unconditionally():
    """The §3.1 defect, reintroduced by its own fix and caught at the screen.

    The three workflow buttons wake the timer directly, so after a **refused** start — a
    `NotReadyToSweep` with no session row created — the fingerprint already reads `live: False`.
    A timer update gated on that value having *changed* is therefore never sent, and the page polls
    `select sessions` every 5 s for ever on a page where nothing was started. Measured in a running
    app before this: 7 calls in 35 s, indefinitely.

    Switching **off** is idempotent and must be unconditional; switching **on** stays gated, because
    returning `active=True` every tick restarts the interval every tick.
    """
    # Whitespace-normalised rather than `ast.unparse`d: unparsing re-indents a nested block to the
    # top level, so the two branches would not match however they are written.
    source = (SRC / "ui" / "pages" / "lab.py").read_text(encoding="utf-8")
    normalised = " ".join(source.split())
    assert "if not live: timer = gr.Timer(POLL_SECONDS, active=False)" in normalised, (
        "turning the timer off must not be gated on the fingerprint having changed"
    )
    assert 'elif before.get("live") is True: timer = gr.skip()' in normalised, (
        "turning it on must stay gated, or the interval restarts on every tick"
    )
