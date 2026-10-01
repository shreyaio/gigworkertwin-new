"""M18 — Twin Studio feeds analysis, and Agent Studio shows its result. §4 and §5.

The researcher confirmed on 2026-10-01 that *"by overwrite, it's ok for the studio values to feed
analyses"* (`ARCHITECTURE_UPDATE.md` §1.1), which narrows `docs/01` §6.9. Everything here tests
either the new behaviour or the wall that did **not** move:

* **§4.2** render on demand, through the same `render_and_check` the sweep uses.
* **§4.3** a dialled ask is filed as a run with ``origin='studio'`` and ``twins_n=1``; it writes no
  `session_panel` row; and a later Dial board run supersedes it **with no precedence logic**.
* **§4.4** a second ask appends and moves the latest pointer; the earlier row survives.
* **§4.5** a custom free-text change stays fully quarantined; a hand-built twin shows an empty
  baseline.
* **§5** the Twin Interviewer returns the twin's answers, not its input; the Designer returns the
  rendered paragraph, not the bullets.

No live LLM and no live DB (`CLAUDE.md` → Testing).
"""

from __future__ import annotations

import pytest

from twinlab.agents.registry import StubModelClient, set_client
from twinlab.ingest.reference_store import reference


@pytest.fixture(autouse=True)
def _stub_client():
    """A twin that answers every item with its scale midpoint, and a Checker that always entails.

    The prose is irrelevant to every assertion in this file — what is tested is the contract
    (`CLAUDE.md` → Testing: "test the contract, not the prose").
    """
    from twinlab.models.variant import CoverageVerdict
    from twinlab.models.variant import LeverParagraph as LP

    ref = reference()

    # At least `word_min` (45) words and inside the reading-grade band, so the real Checker passes
    # it. The Checker is not stubbed: §4.2 point 2 is that a Studio render goes through the SAME
    # `render_and_check` and the same five gates as the sweep, so stubbing them would test nothing.
    paragraph = (
        "Uber will now show you the full fare before you decide whether to accept a trip. "
        "You will be able to see how the money is worked out, and how much of it reaches you. "
        "If a trip is cancelled after you have already started driving towards it, you will be "
        "paid for the distance you covered. These changes apply to every trip you take in the "
        "city from now on."
    )

    def handler(cfg, prompt, out):
        if out is LP:
            return LP(text=paragraph)
        if out is CoverageVerdict:
            return CoverageVerdict(entailed=True, reason="stub")
        fields = set(getattr(out, "model_fields", {}))
        if "answers" in fields:
            # Every item at 4, which is inside both the 5- and the 7-point ranges.
            asked = [i for i in ref.battery_item_ids if i in prompt]
            payload = {"answers": {i: 4 for i in (asked or ref.battery_item_ids)}}
            if "rationale" in fields:
                payload["rationale"] = "The fare being visible is the part that matters."
            if "holdout_set" in fields:
                payload["holdout_set"] = "H3"
            return out(**payload)
        if "replies" in fields:
            return out(replies=["It would help a little."], rationale="Small but real.")
        return out()

    client = StubModelClient(handler)
    set_client(client)
    yield client
    set_client(None)


@pytest.fixture(autouse=True)
def _fresh_pool():
    from twinlab.services import twin_runtime

    twin_runtime.reset_pool()
    yield
    twin_runtime.reset_pool()


# =================================================================== helpers


async def _twin_with_driver(
    backend, twin_id: str, *, source: str = "synthetic", quality_passed: bool = True
) -> None:
    """A twin whose driver answered the **whole** battery, and which the quality gate kept.

    Complete on purpose: `compute_shifts` excludes a twin whose baseline is partial, because a
    metric is never computed over a subset (`docs/07` §2.3) — so an incomplete driver would make
    every filing test fail for the wrong reason.

    Quality-passed on purpose too: a twin the gate dropped can be *asked* in the Studio but its
    answer is never *filed* (`docs/03` §9.1), so a filing test on a dropped twin would fail for the
    wrong reason as well. ``quality_passed=False`` is how that rule is tested directly.
    """
    ref = reference()
    await backend.insert(
        "twins",
        [{
            "twin_id": twin_id,
            "submission_id": twin_id,
            "source": source,
            "service": "cab",
            "city": "Mumbai",
            "consent_twin": True,
            "persona_passage": "I drive a cab in Mumbai and have done for three years.",
            "persona_hash": "abc123",
        }],
    )
    await backend.insert(
        "survey_answers",
        [
            {"submission_id": twin_id, "item_id": item_id, "value_num": 3}
            for item_id in ref.battery_item_ids
        ],
    )
    if quality_passed:
        await backend.insert(
            "twin_quality_runs",
            [{
                "twin_id": twin_id, "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
                "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
            }],
        )


async def _stored_variant(backend, code: str, *, passed: bool = True) -> None:
    """A Checker-passed `variants` row, so `_stimulus` has something verified to show."""
    from config.settings import settings
    from twinlab.db.repositories import VariantRepo
    from twinlab.models.reference import LEVER_BY_POSITION

    await VariantRepo(backend).put(
        version_code=code,
        style_version=settings.style_version,
        delta_spec={"version_code": code},
        delta_hash="deadbeef",
        # The version code must NOT appear in the text: I8 forbids it travelling with the
        # stimulus, and `assert_no_forbidden_content` scans the assembled prompt for it.
        paragraphs={
            lever: f"Paragraph for {lever}, as rendered." for lever in LEVER_BY_POSITION
        },
        checker={"passed": passed, "notes": "" if passed else "a gate failed"},
    )


# =================================================================== §4.2 render on demand


async def test_an_unrendered_version_offers_a_render_instead_of_a_dead_end(backend):
    """§4.1 and §4.2: the refusal stays (I3) but it now names the way out.

    Screenshot 2 is the dead end: every dial set, a valid code, nothing to press. Running the whole
    frozen panel from the Dial board to answer a one-twin question is not a way out.
    """
    from twinlab.services.studio import StudioBlocked, ask_studio

    await _twin_with_driver(backend, "T1")
    with pytest.raises(StudioBlocked) as caught:
        await ask_studio(twin_id="T1", version_code="22000", backend=backend)
    message = str(caught.value)
    assert "has never been rendered" in message
    assert "Render this version now" in message, "the refusal must name the way out"
    assert "I3" in message, "and still say why it refused"


async def test_an_unpassed_variant_is_still_refused(backend):
    """I3 keeps no sandbox exemption. A stored Checker failure is not a stimulus."""
    from twinlab.services.studio import StudioBlocked, ask_studio

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "22000", passed=False)
    with pytest.raises(StudioBlocked, match="did not pass the Checker"):
        await ask_studio(twin_id="T1", version_code="22000", backend=backend)


async def test_variant_status_reports_the_budget_before_the_button(backend):
    """§4.2 point 4: **never render blind.** `docs/06` §9 wants the budget on every confirm step."""
    from twinlab.services.studio import variant_status

    before = await variant_status("22000", backend=backend)
    assert before["exists"] is False and before["passed"] is False
    assert before["budget"].calls > 0, "a version with nothing cached costs design calls"

    await _stored_variant(backend, "22000")
    after = await variant_status("22000", backend=backend)
    assert after["exists"] is True and after["passed"] is True


async def test_start_render_stores_a_variant_and_logs_it(backend):
    """§4.2: it enqueues, emits into `run_events`, and stores via `VariantRepo.put`.

    **No model call in `start_render` itself** (`CLAUDE.md` rule 12) — it returns a session id and
    the work happens in the task this awaits.
    """
    from twinlab.services.studio import _RENDERS, start_render

    session_id = await start_render("01000", backend=backend)
    await _RENDERS["01000"]

    variants = await backend.select("variants", [("eq", "version_code", "01000")])
    assert len(variants) == 1
    assert (variants[0]["checker"] or {}).get("passed") is True

    events = await backend.select("run_events", [("eq", "session_id", session_id)])
    stages = {str(r["stage"]) for r in events}
    assert {"render", "check"} <= stages, "a Studio render must be visible in the Agents log"
    session = (await backend.select("sessions", [("eq", "session_id", session_id)]))[0]
    assert session["kind"] == "render"
    assert session["status"] == "completed"
    # A render has no panel and must never look like one.
    assert session["panel_size"] == 0
    assert await backend.count("session_panel") == 0


async def test_a_studio_render_is_reused_by_a_later_run(backend):
    """§4.2 point 3: Studio rendering is a net **saving**, not a new cost.

    The variant is keyed `(version_code, style_version)` like any other, so the next caller for the
    same code hits the cache and pays nothing. I4 is unchanged.
    """
    from config.settings import settings
    from twinlab.services.studio import _RENDERS, start_render
    from twinlab.services.twin_runtime import render_and_check

    client_calls_before = None
    await start_render("01000", backend=backend)
    await _RENDERS["01000"]
    from twinlab.agents.registry import get_client

    client_calls_before = get_client().call_count("design")

    await render_and_check("01000", settings.style_version, backend=backend)
    assert get_client().call_count("design") == client_calls_before, (
        "a cached variant must not be re-rendered; that is the I4 cache doing its job"
    )


async def test_two_renders_of_one_code_cannot_run_at_once(backend):
    """Spending the design budget twice on the same code is the one thing a second press must not
    do."""
    from twinlab.services.studio import _RENDERS, StudioError, rendering, start_render

    await start_render("01000", backend=backend)
    assert rendering("01000") is True
    with pytest.raises(StudioError, match="already being rendered"):
        await start_render("01000", backend=backend)
    await _RENDERS["01000"]
    assert rendering("01000") is False


# =================================================================== §4.3 results that count


async def test_a_dialled_studio_ask_is_filed_as_a_run(backend):
    """§4.3: `origin='studio'`, `twins_n=1`, one `twin_answers` row, and it reaches Results."""
    from twinlab.services.results import completed_runs, tested_rows
    from twinlab.services.status import tested_codes
    from twinlab.services.studio import ask_studio

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")

    result = await ask_studio(
        twin_id="T1", version_code="01000", include_battery=True, backend=backend
    )

    assert result.run_id, "a dialled ask with a complete vector is filed"
    assert result.origin == "studio" and result.twins_n == 1
    assert result.index_value is not None

    runs = await backend.select("runs", None)
    assert len(runs) == 1
    assert runs[0]["origin"] == "studio"
    assert runs[0]["twins_n"] == 1
    assert runs[0]["status"] == "completed"
    assert await backend.count("twin_answers") == 1

    # It reaches every downstream surface, which is the point of the override.
    assert "01000" in await tested_codes(backend)
    assert [r["version_code"] for r in await completed_runs(backend)] == ["01000"]
    assert [r.origin for r in await tested_rows(backend)] == ["studio"]


async def test_a_studio_run_writes_no_session_panel_row(backend):
    """§4.3 item 5, asserted: I14 applies to frozen panels and a Studio run has none.

    A rerun that "inherited" a one-twin panel would be a different experiment wearing a version
    code, so `panel_size` is 0 rather than 1 and there is nothing to inherit.
    """
    from twinlab.services.studio import ask_studio

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    await ask_studio(
        twin_id="T1", version_code="01000", include_battery=True, backend=backend
    )

    assert await backend.count("session_panel") == 0
    session = (await backend.select("sessions", [("eq", "kind", "studio")]))[0]
    assert session["panel_size"] == 0, (
        "panel_size 1 would let a rerun believe it could inherit a panel of one twin"
    )


async def test_a_later_sweep_run_supersedes_the_studio_value_with_no_precedence_logic(backend):
    """§1.1 and §4.3 item 3 — the whole reason the override is safe.

    `completed_runs` already selects the latest run per `version_code` by `started_at` descending,
    so
    a Dial board run with a newer timestamp becomes the latest automatically. **Nothing is updated
    in
    place**, so `CLAUDE.md` rule 6 holds and there is no precedence code to get wrong.
    """
    from twinlab.db.repositories import AnswerRepo, RunRepo, SessionRepo
    from twinlab.services.results import completed_runs, tested_rows
    from twinlab.services.studio import ask_studio

    await _twin_with_driver(backend, "T1")
    await _twin_with_driver(backend, "T2")
    await _stored_variant(backend, "01000")
    studio = await ask_studio(
        twin_id="T1", version_code="01000", include_battery=True, backend=backend
    )

    # A later sweep-origin run for the same code, with two twins.
    session = await SessionRepo(backend).create(name="Sweep", kind="sweep", panel_size=2)
    run = await RunRepo(backend).get_or_create(session.session_id, "01000")
    for twin_id in ("T1", "T2"):
        await AnswerRepo(backend).record(
            run_id=run.run_id, twin_id=twin_id,
            answers={i: 5 for i in reference().battery_item_ids},
            lever_order=[], seed=1, wording="A", model="stub",
        )
    from twinlab.services.twin_runtime import analyse

    metrics, index_value, reading = await analyse(run.run_id, backend=backend)
    await RunRepo(backend).complete(
        run.run_id, twins_n=2, metrics=metrics, index_value=index_value, analysis=reading
    )

    latest = await completed_runs(backend)
    assert len(latest) == 1, "one row per version code"
    assert latest[0]["origin"] == "sweep" and latest[0]["twins_n"] == 2
    assert [r.origin for r in await tested_rows(backend)] == ["sweep"]

    # And the Studio row is still there. Superseded is not deleted (rule 6).
    all_runs = await backend.select("runs", None)
    assert len(all_runs) == 2
    assert {r["run_id"] for r in all_runs} >= {studio.run_id}


async def test_the_results_panel_names_n_when_the_latest_run_is_a_studio_one(backend):
    """§4.3 item 4: `origin` and `twins_n` are visible **wherever a number is**."""
    from twinlab.services.results import results_panel
    from twinlab.services.studio import ask_studio
    from twinlab.ui.components import results_panel_html

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    await ask_studio(
        twin_id="T1", version_code="01000", include_battery=True, backend=backend
    )

    panel = await results_panel("01000", backend=backend)
    assert panel.origin == "studio" and panel.twins_n == 1
    html = results_panel_html(panel)
    assert "From the Twin Studio" in html
    assert "n = 1" in html
    labels = {row.label for row in panel.metadata}
    assert "Where it came from" in labels


async def test_an_unscorable_studio_ask_is_failed_never_completed_with_zero(backend):
    """I15, and §4.3 item 6. A twin whose driver is incomplete cannot be scored, so it is `failed`.

    The answer still happened and is still kept in `studio_runs` — the answer is real, the
    comparison is not possible. An index of 0.000 over nobody is the thing I15 exists to forbid.
    """
    from twinlab.services.studio import StudioError, file_studio_run

    # A twin with NO driver answers at all: the baseline/variant intersection is empty. It carries a
    # `kept` quality row so this test fails on the SCORING gate and not on the quality one — a test
    # that can pass for two different reasons is testing neither.
    await backend.insert(
        "twins",
        [{
            "twin_id": "M1", "source": "manual", "city": "Mumbai", "service": "cab",
            "consent_twin": False, "persona_passage": None, "persona_hash": None,
        }],
    )
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "M1", "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
        }],
    )
    with pytest.raises(StudioError, match="could not be scored"):
        await file_studio_run(
            twin_id="M1",
            version_code="01000",
            answers={i: 4 for i in reference().battery_item_ids},
            model="stub",
            seed=1,
            backend=backend,
        )
    runs = await backend.select("runs", None)
    assert len(runs) == 1 and runs[0]["status"] == "failed"
    assert runs[0]["error"]
    # Nothing reaches Results.
    from twinlab.services.results import completed_runs

    assert await completed_runs(backend) == []


async def test_the_control_cell_cannot_be_filed_from_the_studio(backend):
    """`00000` is the comparison every shift is measured against, and its index comes from the
    panel.

    A one-twin `00000` would move the floor every other cell is read against (`docs/03` §6.1).
    """
    from twinlab.services.studio import StudioError, file_studio_run

    await _twin_with_driver(backend, "T1")
    with pytest.raises(StudioError, match="control"):
        await file_studio_run(
            twin_id="T1", version_code="00000",
            answers={i: 4 for i in reference().battery_item_ids},
            model="stub", seed=1, backend=backend,
        )


# =================================================================== §4.4 the latest pointer


async def test_a_second_ask_appends_and_moves_the_latest_pointer(backend):
    """§4.4: the earlier row survives and the pointer moves, exactly as `runs` works."""
    from twinlab.services.studio import ask_studio, studio_history

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    for _ in range(2):
        await ask_studio(
            twin_id="T1", version_code="01000", include_battery=True, backend=backend
        )

    rows = await studio_history("T1", backend=backend)
    assert len(rows) == 2, "a second ask appends; it never overwrites (I9)"
    current = [r for r in rows if r["is_latest_for_twin_version"]]
    assert len(current) == 1, "exactly one row is current for a (twin, version)"


async def test_two_different_custom_changes_are_both_current(backend):
    """A custom ask has no version code, so the key includes the change itself.

    Two different questions for one twin are two different questions, and treating them as one would
    silently discard an answer.
    """
    from twinlab.services.studio import run_studio, studio_history

    await _twin_with_driver(backend, "T1")
    await run_studio(twin_id="T1", custom_change="Imagine a fixed cancellation fee.",
                     backend=backend)
    await run_studio(twin_id="T1", custom_change="Imagine a guaranteed hourly rate.",
                     backend=backend)

    rows = await studio_history("T1", backend=backend)
    assert len(rows) == 2
    assert all(r["is_latest_for_twin_version"] for r in rows)


# =================================================================== §4.5 the three twin sources


async def test_a_custom_change_is_never_filed_as_a_run(backend):
    """§4.5, and the one Studio path that stays **fully** quarantined.

    It bypasses the lookup (I1) and the Checker (I3) by construction, is not one of the 243, and has
    no `version_code` to be latest for. A number produced under a custom change is not a measurement
    of anything in the design.
    """
    from twinlab.services.studio import SANDBOX_LABEL, ask_studio

    await _twin_with_driver(backend, "T1")
    result = await ask_studio(
        twin_id="T1",
        custom_change="Imagine Uber pays for every cancelled trip after 2 km.",
        include_battery=True,
        backend=backend,
    )

    assert result.sandbox is True
    assert result.label == SANDBOX_LABEL
    assert result.run_id is None and result.origin == ""
    assert await backend.count("runs") == 0, "a custom change never enters `runs`"
    assert await backend.count("twin_answers") == 0
    # And it is never filed under a version code.
    rows = await backend.select("studio_runs", None)
    assert rows[0]["version_code"] is None
    assert rows[0]["custom_change"]


async def test_a_hand_made_twin_has_an_empty_baseline_not_zeros(backend):
    """§4.5 and C-12: a manual twin is `source='manual'`, has no persona hash, and shows blanks.

    An empty baseline column and a baseline of zero are different claims (I17). `POPULATION_SOURCES`
    names no `manual` population, so it can never be drawn into a panel either (`docs/03` §9.3).
    """
    from twinlab.orchestrator.panel import POPULATION_SOURCES
    from twinlab.services.studio import MANUAL_SOURCE, ask_studio, create_manual_twin

    assert all(MANUAL_SOURCE not in sources for sources in POPULATION_SOURCES.values())

    twin = await create_manual_twin(
        city="Mumbai", service="cab", sliders={"FAIR": 3}, backend=backend
    )
    stored = (await backend.select("twins", [("eq", "twin_id", twin.twin_id)]))[0]
    assert stored["source"] == MANUAL_SOURCE
    assert not stored["persona_hash"], "a manual twin has no driver to be lossless about (I6)"

    await _stored_variant(backend, "01000")
    result = await ask_studio(
        twin_id=twin.twin_id, version_code="01000", include_battery=True, backend=backend
    )
    assert result.rows, "the twin still answers"
    assert all(row.baseline is None for row in result.rows), (
        "a hand-built twin has no driver, so 'Uber today' is EMPTY and never zero (I17)"
    )
    assert all(row.change is None for row in result.rows)
    # And it could not be scored, so it is not filed.
    assert result.run_id is None
    assert result.not_filed


async def test_a_dropped_twin_can_be_asked_but_is_never_filed(backend):
    """**Not in the plan; raised by it.** `docs/03` §9.1 against `ARCHITECTURE_UPDATE.md` §1.1.

    The Studio deliberately offers *every* twin, including the ones the quality gate dropped — that
    asymmetry is the point of the screen. §1.1 then lets a Studio ask become a result. Together
    those
    two would put a dropped twin's answer into the analysis, and §9.1 is explicit that a twin that
    failed the gate is dropped from the panel **and from all cells**.

    The conservative reading is taken: it can be asked, it is not filed, and the screen says which.
    """
    from twinlab.services.studio import ask_studio

    await _twin_with_driver(backend, "DROPPED", quality_passed=False)
    # A real verdict of `kept: False`, not merely an absent one — the two are different states and
    # the message distinguishes them.
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "DROPPED", "holdout_set": "H3", "mae": 1.8, "pct_within_1": 0.4,
            "kept": False, "items_n": 18, "detail": {}, "is_latest": True,
        }],
    )
    await _stored_variant(backend, "01000")

    result = await ask_studio(
        twin_id="DROPPED", version_code="01000", include_battery=True, backend=backend
    )
    # Asked, and answered: the conversation is the whole value of the screen.
    assert result.rows, "a dropped twin can still be asked"
    assert await backend.count("studio_runs") == 1
    # But not filed.
    assert result.run_id is None
    assert "dropped by the quality test" in result.not_filed
    assert await backend.count("runs") == 0
    assert await backend.count("twin_answers") == 0


async def test_an_untested_twin_is_also_not_filed(backend):
    """A twin never put through the gate is not "passed" either; the message says which."""
    from twinlab.services.studio import StudioError, file_studio_run

    await _twin_with_driver(backend, "UNTESTED", quality_passed=False)
    with pytest.raises(StudioError, match="has not been through the quality test"):
        await file_studio_run(
            twin_id="UNTESTED", version_code="01000",
            answers={i: 4 for i in reference().battery_item_ids},
            model="stub", seed=1, backend=backend,
        )


async def test_a_twin_from_a_survey_answer_can_be_asked(backend):
    """C-11, verified rather than assumed: mode 2 produces an askable twin."""
    from twinlab.services.studio import ask_studio, create_twin_from_survey

    ref = reference()
    await backend.insert(
        "survey_submissions",
        [{
            "submission_id": "REAL-1", "data_type": "REAL", "consent_twin": True,
            "eligible": True, "consented": True, "city": "Mumbai", "service": "cab",
        }],
    )
    await backend.insert(
        "survey_answers",
        [
            {"submission_id": "REAL-1", "item_id": i, "value_num": 3}
            for i in ref.battery_item_ids
        ],
    )
    twin = await create_twin_from_survey("REAL-1", backend=backend)
    assert twin.source == "real"
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "REAL-1", "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
        }],
    )

    await _stored_variant(backend, "01000")
    result = await ask_studio(
        twin_id="REAL-1", version_code="01000", include_battery=True, backend=backend
    )
    assert result.run_id, "a real survey twin with a complete driver is filed"
    assert all(row.baseline is not None for row in result.rows)


# =================================================================== §5 Agent Studio


async def test_the_twin_interviewer_returns_the_twins_answers_not_its_input(backend):
    """§5.1, the defect that mattered: **the panel was showing its input instead of its result.**

    Its table was headed "what this twin's driver answered" and listed the baseline — the survey
    vector the twin is anchored on. The screenshot asks for *"Some of the 37 answers it gave"*.
    """
    from twinlab.services.agent_config import twin_test_view

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")

    view = await twin_test_view("T1", "01000", backend=backend)
    assert view["answers"], "the answers table is the subject of this panel"
    first = view["answers"][0]
    assert first["twin"] == 4, "the TWIN's answer, from the stub"
    assert first["driver"] == 3, "and the driver's beside it, as the Checker panel does"


async def test_the_twin_interviewer_compares_one_row_per_instruction_variant(backend):
    """§5.1: one row per prompt, with `Answer checked?` and a reason — not one row per metric."""
    from twinlab.services.agent_config import load_agent, twin_test_view

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    # The **resolved** prompt, which is what the Agent Studio textarea holds. `system_prompt` is the
    # unresolved `file:twin.md` reference and would fail the six-section skeleton check.
    from twinlab.agents.registry import resolve_prompt

    saved = await load_agent("twin", backend=backend)
    edited = resolve_prompt(saved)[0] + "\n\nAnswer plainly."

    view = await twin_test_view("T1", "01000", edited_prompt=edited, backend=backend)
    assert [row["which"] for row in view["variants"]] == ["saved", "your edit"]
    for row in view["variants"]:
        assert row["checked"] is True, "the contract/range verdict the ladder already computed"
        assert row["reason"], "and the one-line rationale the screenshot shows"
        assert set(row["scores"]) == set(view["metrics"])
    assert view["driver_scores"], "the driver's six scores, for comparison"


async def test_the_twin_interviewer_runs_the_saved_prompt_even_with_no_edit(backend):
    """A screen that asks the twin nothing unless you edit the prompt is not a test screen."""
    from twinlab.services.agent_config import twin_test_view

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    view = await twin_test_view("T1", "01000", backend=backend)
    assert [row["which"] for row in view["variants"]] == ["saved"]
    assert view["answers"][0]["twin"] is not None


async def test_the_twin_interviewer_still_refuses_an_unrendered_version(backend):
    """I3 has no test-screen exemption either. There is no render path in this function."""
    from twinlab.services.agent_config import twin_test_view

    await _twin_with_driver(backend, "T1")
    view = await twin_test_view("T1", "22000", backend=backend)
    assert "has never been rendered" in view["note"]
    assert view["variants"] == []


async def test_the_policy_designer_shows_the_rendered_paragraph_not_the_bullets(backend):
    """§5.2 item 1: `Text used` held `told_summary`, which `variant/lookup.py` says a twin never
    sees.

    Showing the bullets there is not cosmetic: it makes two artefacts `docs/03` §4.3 keeps
    deliberately apart look interchangeable on the one screen whose job is to show what the design
    agent produced.
    """
    from twinlab.services.agent_config import design_test_view

    await _stored_variant(backend, "01000")
    view = await design_test_view("01000", backend=backend)

    lit = [lever for lever in view["levers"] if lever["dial"] > 0]
    assert lit, "01000 has one lever set"
    for lever in view["levers"]:
        assert lever["paragraph"].startswith("Paragraph for "), (
            "Text used must be the rendered paragraph the twin is shown"
        )
    # The bullets are still available, in their own column.
    assert any(lever["bullets"] for lever in view["levers"])
    assert all(
        lever["paragraph"] not in lever["bullets"] for lever in view["levers"]
    ), "the two artefacts must not be the same string"


async def test_the_policy_designer_labels_both_wordings(backend):
    """§5.2 item 2: wording is a real experimental factor (validity test 5), so it is labelled."""
    from twinlab.services.agent_config import design_test_view

    await _stored_variant(backend, "01000")
    view = await design_test_view("01000", backend=backend)
    assert set(view["wordings"]) == {"A", "B"}
    assert view["wordings"]["B"] == list(reversed(view["wordings"]["A"])), (
        "wording B is the reversed paragraph order `ask_items(reverse_order=True)` shows a twin"
    )


async def test_the_policy_designer_lists_the_versions_it_would_test_next(backend):
    """§5.2 item 3: absent entirely before this. Read-only, and it starts nothing."""
    from twinlab.services.agent_config import design_test_view

    await _stored_variant(backend, "00001")
    before = await backend.count("sessions")
    view = await design_test_view("00001", backend=backend)

    assert view["next_versions"], "the table was missing entirely"
    assert all(row["why"] for row in view["next_versions"]), "every row names its reason"
    assert await backend.count("sessions") == before, "looking at a plan starts nothing"


def test_the_next_versions_table_explains_one_dial_at_a_time():
    """The screenshot's own example: `00001 — Test one dial on its own first.`"""
    from twinlab.orchestrator.odometer import advance, code_from_index, index_from_code
    from twinlab.services.agent_config import _next_versions

    rows = dict(
        _next_versions(
            "00000",
            advance=advance,
            code_from_index=code_from_index,
            index_from_code=index_from_code,
            control="00000",
            how_many=3,
        )
    )
    assert rows["00001"] == "Test one dial on its own first."


def test_the_run_manager_previews_the_log_without_writing_one():
    """§5.4: five preview lines, one per agent, and screenshot 7 is explicitly a dry run."""
    from twinlab.services.agent_config import manager_log_preview

    rows = manager_log_preview("01000")
    assert [r.label for r in rows] == ["MANAGER", "DESIGN", "CHECKER", "TWIN", "ANALYST"]
    assert all("01000" in r.value for r in rows)


# =================================================================== §5.5 gpt-oss only


def test_the_provider_list_is_read_off_the_type():
    """§5.5 item 1: the dropdown is built **from the Literal**, not from a hand-written list.

    `Mistral` was offerable on a screen whose model rejects it, so the screen could produce a row
    that `load_agent` cannot construct. A hand-maintained list is a second source of truth.
    """
    from twinlab.services.agent_config import PROVIDERS

    assert PROVIDERS == ("ollama", "openai", "mock")
    assert "mistral" not in PROVIDERS


async def test_a_stale_mistral_row_is_corrected_from_the_seed(backend):
    """§5.5 item 2, with the live row's exact shape: provider `mistral`, last saved 2026-09-25.

    Reproducible, not a hand-edit: it resets to `config/agents.default.yaml` — which already says
    `gpt-oss:120b` — and appends an `agent_config_history` row saying what moved.
    """
    from twinlab.services.agent_config import correct_stale_models, load_agent

    await backend.insert(
        "agent_configs",
        [{
            "agent_id": "twin",
            "name": "Twin",
            "role": "Answers the battery as one driver.",
            "model": {
                "provider": "mistral", "name": "mistral-small-latest", "temperature": 1.0
            },
            "system_prompt": "file:twin.md",
            "output_mode": "prompted",
            "version": 3,
        }],
    )
    corrected = await correct_stale_models(backend=backend)
    assert [e["agent_id"] for e in corrected] == ["twin"]
    assert corrected[0]["was"]["provider"] == "mistral"
    assert corrected[0]["now"]["name"] == "gpt-oss:120b"
    assert corrected[0]["now"]["provider"] == "ollama"

    row = (await backend.select("agent_configs", [("eq", "agent_id", "twin")]))[0]
    assert row["model"]["name"] == "gpt-oss:120b"
    assert row["version"] == 4, "the version bumps; a correction is an edit like any other"

    history = await backend.select("agent_config_history", None)
    assert len(history) == 1 and history[0]["action"] == "restored"

    # And the row now loads.
    assert (await load_agent("twin", backend=backend)).model.name == "gpt-oss:120b"


async def test_an_invalid_stored_row_still_renders_the_screen(backend):
    """A row that no longer validates must not take Agent Studio down with it.

    The seed is what the runtime actually runs, so falling back to it shows the truth rather than an
    error card — and it is logged, not swallowed.
    """
    from twinlab.services.agent_config import load_agent

    await backend.insert(
        "agent_configs",
        [{
            "agent_id": "twin", "name": "Twin", "role": "r",
            "model": {"provider": "mistral", "name": "mistral-small-latest"},
            "system_prompt": "file:twin.md", "output_mode": "prompted", "version": 3,
        }],
    )
    cfg = await load_agent("twin", backend=backend)
    assert cfg.model.provider == "ollama" and cfg.model.name == "gpt-oss:120b"


def test_a_correction_leaves_a_frozen_agent_alone():
    """Freezing is what makes a sweep's configuration stable; a silent rewrite would defeat it."""
    import asyncio

    from twinlab.db.client import InMemoryBackend
    from twinlab.services.agent_config import correct_stale_models

    backend = InMemoryBackend()

    async def _go():
        await backend.insert(
            "agent_configs",
            [{
                "agent_id": "twin", "name": "Twin", "role": "r",
                "model": {"provider": "mistral", "name": "mistral-small-latest"},
                "system_prompt": "file:twin.md", "output_mode": "prompted",
                "version": 3, "frozen": True,
            }],
        )
        return await correct_stale_models(backend=backend)

    corrected = asyncio.run(_go())
    assert corrected[0]["skipped"] == "frozen"
    assert corrected[0]["now"] is None


async def test_the_screen_reports_the_temperature_actually_in_force(backend):
    """§5.5 item 3: the current state — a screen showing a number the runtime discards — must not
    survive.

    Agent Studio read temperature 1 from the stored row while `twin_runtime.twin_agent_config`
    applied `app_config['twin']`'s value. Both are reported, and which is which is said.
    """
    from twinlab.services.agent_config import agent_view, in_force
    from twinlab.services.config import load_twin_config

    force = in_force("twin")
    assert force["model_name"] == "gpt-oss:120b"
    assert force["temperature"] == pytest.approx(load_twin_config().temperature)
    assert "app_config['twin']" in force["source"], (
        "the twin's temperature comes from app_config, and the screen must say so"
    )

    view = await agent_view("twin", backend=backend)
    assert view["in_force"]["model_name"] == "gpt-oss:120b"
    assert "in_force_differs" in view


def test_every_seeded_agent_is_on_gpt_oss():
    """§1.2: *"no its gpt oss only"*. Asserted over the seed, which is what the runtime loads."""
    from twinlab.agents.registry import default_agent_configs

    for agent_id, cfg in default_agent_configs().items():
        assert cfg.model.name == "gpt-oss:120b", f"{agent_id} is on {cfg.model.name}"
        assert cfg.model.provider == "ollama", f"{agent_id} uses {cfg.model.provider}"


async def test_a_render_that_dies_outside_its_guard_fails_the_session(backend, monkeypatch):
    """A render that breaks must not leave a session `running` for ever, or die into nothing.

    `_render_task` guarded its model call but not the writes either side of it, and
    `start_render`'s done-callback never called `.exception()` — so anything else became an
    "exception was never retrieved" warning at interpreter shutdown and the researcher watched a
    render that silently never happened. That is the exact failure `services/runs._spawn` exists to
    prevent, reproduced here; the fix is the same discipline.
    """
    import twinlab.services.studio as studio

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("the variant store is unreachable")

    monkeypatch.setattr(studio, "_render_body", _boom)
    session_id = await studio.start_render("01000", backend=backend)
    await studio._RENDERS["01000"]

    session = (await backend.select("sessions", [("eq", "session_id", session_id)]))[0]
    assert session["status"] == "failed", "a dead render must not leave the session `running`"
    assert studio.rendering("01000") is False, "and must release its slot"


async def test_every_studio_session_reaches_a_terminal_state(backend):
    """A session left at `created` is reported for ever as a job that is still running.

    Caught at the screen: after a Studio ask the Agents tab read *"Running Studio 22000 · SYN-0:
    0 of 1 done"* indefinitely, which also keeps the poll timer awake — the §3.1 defect by another
    route. Both the success and the failure path now close the session.
    """
    from twinlab.services.studio import StudioError, ask_studio, file_studio_run

    await _twin_with_driver(backend, "T1")
    await _stored_variant(backend, "01000")
    await ask_studio(
        twin_id="T1", version_code="01000", include_battery=True, backend=backend
    )
    sessions = await backend.select("sessions", [("eq", "kind", "studio")])
    assert [s["status"] for s in sessions] == ["completed"]

    # And the failure path. A twin with no driver cannot be scored.
    await backend.insert(
        "twins",
        [{
            "twin_id": "M1", "source": "manual", "city": "Mumbai", "service": "cab",
            "consent_twin": False, "persona_passage": None, "persona_hash": None,
        }],
    )
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "M1", "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
        }],
    )
    with pytest.raises(StudioError):
        await file_studio_run(
            twin_id="M1", version_code="01000",
            answers={i: 4 for i in reference().battery_item_ids},
            model="stub", seed=1, backend=backend,
        )
    statuses = sorted(
        s["status"] for s in await backend.select("sessions", [("eq", "kind", "studio")])
    )
    assert statuses == ["completed", "failed"], "no studio session is left at `created`"


async def test_a_render_closes_its_parent_event(backend):
    """An event left `running` is what the Policy Designer card shows as its latest line.

    Caught at the screen: the card read *"running — Rendering 22000 for the Twin Studio"* for a
    render that had finished seconds earlier, while the Checker card beside it already said the
    variant was stored. `agent_cards` takes the newest event per agent and reads its status, so an
    unclosed parent is a card that is permanently wrong.
    """
    from twinlab.services.menu import agent_cards
    from twinlab.services.studio import _RENDERS, start_render

    await start_render("01000", backend=backend)
    await _RENDERS["01000"]

    events = await backend.select("run_events", [("eq", "stage", "render")])
    assert [e["status"] for e in events] == ["ok"], "the render's parent event must be closed"
    design = next(c for c in await agent_cards(backend) if c.agent_id == "design")
    assert design.state != "running"
