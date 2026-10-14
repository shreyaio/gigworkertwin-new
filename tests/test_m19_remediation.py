"""M19 — the work packages of `SYSTEM_AUDIT_AND_PLAN.md`, as executable proofs.

One section per work package, each test naming the package it proves. The reframed tests for
behaviour M19 *changed* live beside the behaviour they originally pinned — `test_m5_render_checker`
for the word band, `test_m17_i3_stored_variant` for the cached failure, `test_m7_orchestrator` and
`test_m18_usability` for the budget — so a reader of those files is not told two different stories.
What is here is the behaviour M19 *added*.

No live LLM and no live DB (`docs/11` → Ground rules).
"""

from __future__ import annotations

import asyncio

import pytest

from config.settings import settings
from twinlab.agents.registry import (
    AgentDisabled,
    default_agent_configs,
    live_agent,
    live_agent_configs,
    live_agent_versions,
    reset_live_agent_configs,
    set_live_agent_configs,
)
from twinlab.db.repositories import VariantRepo
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import TwinConfig
from twinlab.orchestrator import budget as bud
from twinlab.orchestrator.odometer import dials
from twinlab.services import twin_runtime

STYLE = settings.style_version


@pytest.fixture(autouse=True)
def _fresh_process_state():
    """Reset every piece of process-global state these tests touch, before and after.

    Three of them, and all three leak:

    * `twin_runtime`'s paragraph pool, which carries the in-memory paragraph cache and the
      `_rerendered` budget set;
    * `registry`'s live agent config, which WP-8's tests install deliberately;
    * `services.config`'s `_override`, which `save_settings` + `refresh_twin_config` populate.
      WP-9's test saves `quality_runs_per_twin=2`, and without this the *next test file in the
      process* runs under it — `test_m6_twin_quality` asserts the seeded 3 and failed only in the
      full-suite run, which is the worst shape of test pollution to find. The restore pattern is
      `test_m16_settings_apply`'s, which already had it for the same reason.
    """
    from twinlab.services import config as cfg

    before, before_version = dict(cfg._override), cfg._override_version
    twin_runtime.reset_pool()
    reset_live_agent_configs()
    yield
    twin_runtime.reset_pool()
    reset_live_agent_configs()
    cfg._override, cfg._override_version = before, before_version


# ============================================================ WP-1: the word band


def test_wp1_the_band_is_resolved_from_the_commitment_count_at_every_lever_and_dial():
    """WP-1. Every one of the ten non-zero paragraphs gets the band its own brief asked for.

    The blocker was that `L3` and `L4` at dial 2 carry **eight** commitments and the single band
    `[45, 150]` gave them nineteen words each. This asserts the resolution end to end: for all
    five levers at both dials, the brief's band is `band_for(len(commitments))` and nothing else.
    """
    from twinlab.variant.lookup import lookup
    from twinlab.variant.render import band_for, build_brief, load_style_contract

    style = load_style_contract()
    seen: dict[tuple[str, int], tuple[int, int]] = {}
    for dial in (1, 2):
        code = str(dial) * 5
        spec = lookup(code)
        for lever in LEVER_BY_POSITION:
            brief = build_brief(spec, lever)
            band = (brief.style_contract["word_min"], brief.style_contract["word_max"])
            assert band == band_for(len(brief.commitments), style), (lever, dial)
            seen[(lever, dial)] = band

    # The eight-commitment levers are the two that failed under v2, and they now get a floor of
    # 159 — above the 150/152 they were compressed into.
    assert seen[("L3", 2)] == (159, 265)
    assert seen[("L4", 2)] == (159, 265)
    # And the smallest set still gets a workable band rather than the absolute floor.
    assert seen[("L1", 1)] == (51, 85)


def test_wp1_every_lever_paragraph_is_gradeable_under_v3():
    """WP-1's end outcome: all ten paragraphs can be rendered **and graded**.

    Under v2 the Checker refused `L3`/`L4` dial 2 on coverage after the model compressed eight
    commitments into 150 words. This does not re-prove the model's behaviour — that needs a live
    call — but it proves the band each paragraph is held to is satisfiable: a paragraph of the
    band's own midpoint length clears gate 3 at every (lever, dial).
    """
    from twinlab.variant import checker as ck
    from twinlab.variant.lookup import lookup
    from twinlab.variant.render import build_brief, load_style_contract

    from .test_m5_render_checker import filler_words

    load_style_contract()
    for dial in (1, 2):
        spec = lookup(str(dial) * 5)
        for lever in LEVER_BY_POSITION:
            brief = build_brief(spec, lever)
            low, high = brief.style_contract["word_min"], brief.style_contract["word_max"]
            text = filler_words((low + high) // 2)
            in_band, grade, violations = ck.check_invariance(text, brief.style_contract)
            assert in_band, (lever, dial, low, high)
            assert violations == [], (lever, dial, violations)
            assert brief.style_contract["reading_grade_min"] <= grade


def test_wp1_the_checker_refuses_to_grade_a_paragraph_it_has_no_band_for():
    """WP-1. There is no global band to fall back on, so a missing one must raise.

    Grading against a guessed band, or skipping gate 3 because none arrived, would both let an
    ungraded stimulus reach a twin. The failure is a wiring failure and is named as one.
    """
    from twinlab.models.variant import LeverParagraph
    from twinlab.variant import checker as ck
    from twinlab.variant.render import load_style_contract

    with pytest.raises(ck.CheckerMisuse, match="no word band"):
        ck.build_report(
            paragraphs={"L2": LeverParagraph(text="a paragraph with no band to judge it")},
            dials={"L2": 1},
            style=load_style_contract(),
            coverage={},
            containment=[],
        )


def test_wp1_the_style_version_bump_restores_the_paragraph_budget():
    """WP-1's second half: the budget comes back **by the cache key**, not by hand.

    `lever_paragraphs.attempts` reached its ceiling on `L3`/`L4` dial 2 under v2, and the budget
    is durable by design — so no button in the application could produce a different paragraph.
    The key contains `style_version`, so v3 is a fresh key with `attempts = 0`, which is what the
    key exists for. Asserted as "a v2 row does not satisfy a v3 pool", because that is the
    mechanism.
    """
    from twinlab.services.twin_runtime import StoredParagraphPool

    pool = StoredParagraphPool()
    assert pool.style_version == STYLE
    assert pool.key("L3", 2) == ("L3", 2, STYLE)
    assert pool.key("L3", 2) != ("L3", 2, "v2")


# ====================================================== WP-2: a cached failure is a verdict


async def _store_variant(backend, code: str, *, passed: bool) -> None:
    await VariantRepo(backend).put(
        version_code=code,
        style_version=STYLE,
        delta_spec={"version_code": code},
        delta_hash="h",
        paragraphs={lever: {"text": f"text for {lever}"} for lever in LEVER_BY_POSITION},
        checker={"passed": passed, "notes": "" if passed else "containment hit"},
    )


async def _spend_budget(backend, code: str) -> None:
    await backend.upsert(
        "lever_paragraphs",
        [
            {
                "lever": lever,
                "dial": dial,
                "style_version": STYLE,
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


async def test_wp2_a_passing_variant_still_short_circuits(backend):
    """WP-2 changes the failure path only. A passing cell must still cost nothing to re-read.

    The coverage probe is one model call per commitment, so re-checking a passing cell would be
    the most expensive thing the module could do for no new information.
    """
    await _store_variant(backend, "01000", passed=True)

    def _no_pool(*args, **kwargs):
        raise AssertionError("the render path was entered for a cell that already passed")

    original = twin_runtime.paragraph_pool
    twin_runtime.paragraph_pool = _no_pool
    try:
        variant, report = await twin_runtime.render_and_check("01000", STYLE, backend=backend)
    finally:
        twin_runtime.paragraph_pool = original

    assert report.passed is True
    assert variant.version_code == "01000"


async def test_wp2_an_exhausted_failure_emits_an_event_saying_it_cost_nothing(backend):
    """WP-2 item 2. **A second press must be visibly a second press.**

    The 04:44/04:48 experience — the identical error twice, the second free and uninformative —
    was possible because a cache hit on a failure emitted nothing at all. A press that costs
    nothing must still say so, in the log tree the researcher is already watching.
    """
    from twinlab.orchestrator.events import EventLog

    await _store_variant(backend, "01000", passed=False)
    await _spend_budget(backend, "01000")

    events = EventLog("s-m19-wp2", backend)
    _, report = await twin_runtime.render_and_check(
        "01000", STYLE, backend=backend, events=events
    )

    assert report.passed is False
    rows = await backend.select("run_events", [("eq", "session_id", "s-m19-wp2")])
    assert rows, "a re-entry on a stored failure emitted nothing"
    labels = " ".join(str(r.get("label") or "") for r in rows)
    assert "spent its one re-render" in labels
    assert "makes no model call" in labels
    assert any(r.get("status") == "error" for r in rows)


async def test_wp2_the_studio_offers_a_retry_only_while_there_is_budget(backend):
    """WP-2 item 3. The Studio's dead end becomes a retry — but only when one is possible.

    `variant_status` is what the screen reads before offering *Render this version again*. A
    retry button with nothing to spend would make no model call and change nothing, which is a
    worse screen than the dead end it replaced.
    """
    from twinlab.services.studio import variant_status

    await _store_variant(backend, "01000", passed=False)

    with_budget = await variant_status("01000", backend=backend)
    assert with_budget["exists"] is True
    assert with_budget["passed"] is False
    assert with_budget["can_retry"] is True
    assert with_budget["retryable_levers"] == ["L2"], (
        "01000 sets only Conditions; the other four levers are dial 0, a constant that is never "
        "generated (I5)"
    )

    await _spend_budget(backend, "01000")
    twin_runtime.reset_pool()
    exhausted = await variant_status("01000", backend=backend)
    assert exhausted["can_retry"] is False
    assert exhausted["retryable_levers"] == []


# ============================================= WP-3: one call per repeat for the H3 gate


def test_wp3_the_h3_prompt_shows_six_labelled_versions_and_names_no_code():
    """WP-3. Six blocks in `version_shown` order, labelled by position only.

    The version codes must not reach the prompt: `assert_no_forbidden_content` refuses a round
    naming one (I8), and a digit in the prompt is a channel through which "this is the strong
    version" could reach the answer and become a confound.
    """
    from twinlab.agents.twin import build_h3_prompt, build_h3_user_prompt
    from twinlab.ingest.reference_store import reference
    from twinlab.services.quality import h3_items

    ref = reference()
    by_version = h3_items(ref)
    codes = list(ref.h3_version_codes)
    paragraphs = {
        position: {
            lever: f"Version {position} says this about {lever}."
            for lever in LEVER_BY_POSITION
        }
        for position in sorted(by_version)
    }

    prompt = build_h3_prompt(
        persona_hash="abc",
        paragraphs_by_version=paragraphs,
        items_by_version=by_version,
        seed=1234,
    )
    assert sorted(prompt.scenario) == sorted(by_version)
    assert len(prompt.item_ids) == 18, "docs/08's 18 H3 numbers: six versions x three items"

    body = build_h3_user_prompt(prompt, "I drive in Mumbai.")
    # Six labelled blocks, in order.
    positions = [body.index(f"Version {p}") for p in sorted(by_version)]
    assert positions == sorted(positions), "the six blocks are not in version_shown order"
    # No version code anywhere.
    for code in codes:
        assert code not in body, f"the H3 prompt names the version code {code} (I8)"
    # No baseline fence: the human had no baseline either, and an empty fence would announce one.
    assert "<<<BASELINE>>>" not in body
    assert "<<<PERSONA>>>" in body and "<<<SCENARIO>>>" in body and "<<<BATTERY>>>" in body


def test_wp3_the_h3_prompt_rebuilds_byte_identically_from_its_seed():
    """WP-3, I11. Six lever orders, all regenerated from the one stored seed."""
    from twinlab.agents.twin import (
        RoundPromptError,
        build_h3_prompt,
        build_h3_user_prompt,
        rebuild_h3_prompt,
    )
    from twinlab.ingest.reference_store import reference
    from twinlab.services.quality import h3_items

    ref = reference()
    by_version = h3_items(ref)
    paragraphs = {
        p: {lever: f"v{p} {lever}" for lever in LEVER_BY_POSITION} for p in sorted(by_version)
    }
    kwargs = dict(
        persona_hash="abc",
        paragraphs_by_version=paragraphs,
        items_by_version=by_version,
        seed=99,
    )

    first = build_h3_prompt(**kwargs)
    second = build_h3_prompt(**kwargs)
    assert first.lever_order == second.lever_order
    assert build_h3_user_prompt(first, "p") == build_h3_user_prompt(second, "p")

    rebuilt = rebuild_h3_prompt(**kwargs, lever_order=first.lever_order)
    assert build_h3_user_prompt(rebuilt, "p") == build_h3_user_prompt(first, "p")

    # The six orders are not all the same: a twin must not be able to learn one position's
    # meaning and carry it across the six blocks.
    assert len({tuple(o) for o in first.lever_order.values()}) > 1

    # And a stored order that disagrees with the seed is a hard failure, not a warning.
    broken = {p: list(reversed(o)) for p, o in first.lever_order.items()}
    with pytest.raises(RoundPromptError, match="not reconstructible"):
        rebuild_h3_prompt(**kwargs, lever_order=broken)


def test_wp3_an_h3_round_missing_a_lever_is_refused():
    """WP-3. A round with four paragraphs is not a cell, in the H3 prompt as in the battery one."""
    from twinlab.agents.twin import RoundPromptError, build_h3_prompt

    with pytest.raises(RoundPromptError, match="not all five"):
        build_h3_prompt(
            persona_hash="a",
            paragraphs_by_version={1: {"L1": "x", "L2": "y"}},
            items_by_version={1: {"P17_V1_FAIR": ("stem", 7)}},
            seed=1,
        )
    with pytest.raises(RoundPromptError, match="not a gate"):
        build_h3_prompt(
            persona_hash="a",
            paragraphs_by_version={},
            items_by_version={},
            seed=1,
        )


def test_wp3_the_budget_is_one_call_per_repeat_and_says_so():
    """WP-3's cost claim, and the caption that stops the new total reading as a bug.

    10 twins x 2 repeats = **20 calls**, which is the number the plan's acceptance check A-2
    requires on the budget card.
    """
    assert bud.H3_CALLS_PER_REPEAT == 1
    assert bud.H3_VERSIONS_PER_CALL == 6
    # RESEARCHER 2026-10-05: each twin also answers the two controls, two battery rounds.
    assert bud.quality_budget(twins=10, repeats=2).calls == 10 * (2 + bud.CONTROL_CALLS_PER_TWIN)

    # An H3 call is six scenarios in one prompt, so it is costed at its own rate rather than the
    # battery's — estimating it at 8 s would understate the gate's wall-clock by about 2.5x.
    assert bud.H3_SECONDS_PER_CALL > bud.SECONDS_PER_CALL
    assert bud.H3_TOKENS_IN_PER_CALL > bud.TOKENS_IN_PER_CALL
    one = bud.quality_budget(twins=1, repeats=1)
    assert one.est_seconds == (
        bud.H3_SECONDS_PER_CALL + bud.CONTROL_CALLS_PER_TWIN * bud.SECONDS_PER_CALL
    )
    assert one.tokens_in == (
        bud.H3_TOKENS_IN_PER_CALL + bud.CONTROL_CALLS_PER_TWIN * bud.TOKENS_IN_PER_CALL
    )


async def test_wp3_the_gate_records_which_protocol_produced_a_row(backend):
    """WP-3 item 7. Six-in-one-context and six-in-isolation **cannot be pooled**.

    `twin_quality_runs` was empty when the protocol changed, so there is nothing to migrate — but
    a row that does not say which presentation produced it cannot be excluded later, so the name
    is written on every row rather than inferred from a date.
    """
    assert twin_runtime.H3_PROTOCOL == "h3_single_call_v1"

    # And the Validation tab surfaces it, rather than averaging across protocols in silence.
    from twinlab.services.lab import validation_view

    view, _ = await validation_view(backend=backend)
    assert view.h3_protocols == [], "no rows, so no protocol to name"

    await backend.insert(
        "twin_quality_runs",
        [
            # `items_n` is required and must be > 0: a verdict over nothing is not a verdict
            # (I15, enforced by the `quality_has_items` check constraint).
            {
                "twin_id": "T1", "holdout_set": "H3", "is_latest": True, "mae": 0.5,
                "pct_within_1": 0.9, "items_n": 18, "kept": True,
                "detail": {"protocol": "h3_single_call_v1"},
            },
            {
                "twin_id": "T2", "holdout_set": "H3", "is_latest": True, "mae": 0.6,
                "pct_within_1": 0.8, "items_n": 18, "kept": True, "detail": {},
            },
        ],
    )
    view, _ = await validation_view(backend=backend)
    assert view.h3_protocols == ["h3_single_call_v1", "unrecorded"], (
        "a table mixing two protocols must say so rather than averaging across them"
    )


# ===================================== WP-4: render all six, report all six, then halt


async def test_wp4_all_six_stimuli_are_rendered_before_the_gate_halts(backend):
    """WP-4, decision D2. Four failures and two passes, not one failure and silence.

    `12220` is the first entry in `h3_version_codes`, so raising on the first failure meant three
    renders that would also have failed were never attempted — the researcher was told about one
    bad code when four of six were affected. The halt itself is unchanged and still correct.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.quality import QualityGateError, _render_stimuli

    ref = reference()
    codes = list(ref.h3_version_codes)
    failing = {codes[0], codes[1], codes[3], codes[4]}
    # The two control stimuli are rendered by the gate too (RESEARCHER 2026-10-05). Stored as
    # passing, so the test never reaches the design agent.
    for code in [*codes, "00000", "SHAM"]:
        await _store_variant(backend, code, passed=code not in failing)
        if code in failing:
            await _spend_budget(backend, code)

    events = EventLog("s-m19-wp4", backend)
    parent = await events.emit(stage="render", label="parent")

    with pytest.raises(QualityGateError) as caught:
        await _render_stimuli("s-m19-wp4", ref, events, parent, backend, include_h2=False)

    message = str(caught.value)
    # The two control stimuli are checked by the same Checker, so they are in the total (+2).
    assert f"{len(failing)} of {len(codes) + 2}" in message
    for code in failing:
        assert code in message, f"{code} failed and was not named"
    # The halt's reason names the measurement, not merely the failure.
    assert "fewer than 18 items" in message

    rows = await backend.select("run_events", [("eq", "session_id", "s-m19-wp4")])
    errors = [r for r in rows if r.get("status") == "error"]
    assert len(errors) >= len(failing)


# ============================================ WP-5: the Dial board can ask, and ask everybody


def test_wp5_the_panel_size_is_a_researcher_owned_setting():
    """WP-5 item 4. `PANEL_SIZE` in the environment is the **seed**, not the authority.

    An environment variable a researcher cannot reach from the frontend is not "configuration is
    data, and the researcher owns it" (`ARCHITECTURE.md` §1.1). The precedence is the same one the
    twin temperature uses, and the chosen value is what a session freezes onto its config.
    """
    from twinlab.services.config import _override
    from twinlab.services.runs import effective_panel_size

    assert TwinConfig().panel_size is None, (
        "None means 'whatever the environment says', which is the behaviour this field preserves"
    )
    assert effective_panel_size() == settings.panel_size
    assert effective_panel_size(50) == 50, "an explicit value always wins"

    # A stored value wins over the environment.
    _override["panel_size"] = 7
    try:
        assert effective_panel_size() == 7
        assert effective_panel_size(3) == 3
    finally:
        _override.pop("panel_size", None)


def test_wp5_a_panel_of_zero_twins_is_refused_by_the_model():
    """WP-5, I15. A run with no twins is a failure, never a result with an index of 0.000."""
    with pytest.raises(ValueError, match="at least 1"):
        TwinConfig(panel_size=0)
    with pytest.raises(ValueError, match="at least 1"):
        TwinConfig(panel_size=-5)


# ================================================= WP-6: the validity tests run and fail loudly


async def test_wp6_an_unverified_stimulus_is_refused_with_zero_model_calls(backend):
    """WP-6 item 2, and an I3 hole the plan did not name.

    `_paragraphs_for`'s docstring said "Checker-passed" and the query filtered only on
    `(version_code, style_version)`, returning the latest row **whatever its verdict** — so a
    variant the Checker had rejected would have been handed to tests 4-8 and put to the panel.
    """
    from twinlab.services.validity import _paragraphs_for

    await _store_variant(backend, "10000", passed=False)
    assert await _paragraphs_for("10000", backend) == {}, (
        "a Checker-rejected variant was handed out as a stimulus (I3)"
    )

    await _store_variant(backend, "10000", passed=True)
    assert len(await _paragraphs_for("10000", backend)) == 5


async def test_wp6_a_live_test_with_no_stimulus_is_inconclusive_and_asks_nobody(backend):
    """WP-6 item 2. The refusal replaces a `RoundPromptError` raised into a dropped task.

    `settings.start_code` has never been rendered, so `_paragraphs_for` returned `{}` and nothing
    checked it; `build_round_prompt` then raised, `RoundPromptError` was caught nowhere, and the
    exception vanished into a task nobody held — while the handler had already said the result
    would appear in the table.
    """
    from twinlab.services import validity as service

    calls: list[dict] = []

    async def _never(**kwargs):
        calls.append(kwargs)
        return {}

    from twinlab.services.config_match import current_fingerprint

    await backend.insert(
        "sessions",
        [{
            "session_id": "s-wp6", "name": "wp6", "status": "completed",
            "config": {"config_fingerprint": await current_fingerprint(backend)},
            "panel_size": 2, "panel_seed": 1,
        }],
    )
    await backend.insert(
        "session_panel",
        [
            {"session_id": "s-wp6", "twin_id": "T1", "stratum": "x", "position": 0},
            {"session_id": "s-wp6", "twin_id": "T2", "stratum": "x", "position": 1},
        ],
    )

    outcome = await service.run_validity_test(
        4, session_id="s-wp6", backend=backend, ask=_never, append=False
    )
    assert outcome.verdict == "INCONCLUSIVE"
    assert "nothing verified to put to a twin" in outcome.headline
    assert calls == [], "a twin was asked for a cell with no verified stimulus (I3)"


async def test_wp6_a_dead_background_test_appends_an_inconclusive_row(backend):
    """WP-6 item 1. **A background death must appear where the researcher is looking.**

    `enqueue_validity_test` returned a task the UI discarded, with no module-level set and no
    done-callback — the one background path in the codebase that did not guard against it. The
    task could be collected mid-run and anything it raised became an "exception was never
    retrieved" warning at shutdown, while the screen said the result would appear below.
    """
    from twinlab.services import validity as service

    async def _boom(*args, **kwargs):
        raise RuntimeError("the provider exploded")

    original = service.run_validity_test
    service.run_validity_test = _boom
    try:
        task = service.enqueue_validity_test(4, session_id=None)
        assert task in service._TASKS, "the task is not held, so it can be collected mid-run"
        with pytest.raises(RuntimeError):
            await task
        # The done-callback schedules the append; let the loop run it.
        for _ in range(5):
            await asyncio.sleep(0)
    finally:
        service.run_validity_test = original

    rows = await backend.select("validity_results", None)
    assert rows, "a dead validity task wrote nothing; the researcher sees a test that never ends"
    assert rows[0]["verdict"] == "INCONCLUSIVE", (
        "a test that did not run is INCONCLUSIVE, never FAIL — recording FAIL would put an "
        "opinion about the instrument into the evidence table on the strength of a traceback"
    )
    assert "provider exploded" in str(rows[0].get("headline") or "")
    assert task not in service._TASKS, "the task was not released after it finished"


async def test_wp6_the_default_session_is_one_that_has_a_panel(backend):
    """WP-6 item 3. A render session and a quality session have no panel by construction.

    `run_validity_test` defaulted to the newest session of **any** kind. On the study database
    that was `Render 01000` (`kind='render'`, `panel_size=0`), so tests 4-8 read `session_panel`,
    found nothing, and could only ever report INCONCLUSIVE.
    """
    from twinlab.services.runs import (
        latest_session_id,
        latest_session_with_panel,
        sessions_with_panels,
    )

    assert await latest_session_with_panel(backend) is None

    await backend.insert(
        "sessions",
        [{
            "session_id": "s-sweep", "name": "Ask 01000", "kind": "ask",
            "status": "completed", "config": {}, "panel_size": 2, "panel_seed": 1,
        }],
    )
    await backend.insert(
        "session_panel",
        [{"session_id": "s-sweep", "twin_id": "T1", "stratum": "x", "position": 0}],
    )
    await backend.insert(
        "sessions",
        [{
            "session_id": "s-render", "name": "Render 01000", "kind": "render",
            "status": "completed", "config": {}, "panel_size": 0,
        }],
    )

    assert await latest_session_id(backend) == "s-render", "the newest of any kind"
    assert await latest_session_with_panel(backend) == "s-sweep", (
        "the newest session that a stimulus can actually be put to"
    )
    listed = await sessions_with_panels(backend)
    assert [sid for sid, _ in listed] == ["s-sweep"]
    assert "1 twin(s) on the panel" in listed[0][1]


async def test_wp6_every_card_says_what_it_still_needs(backend):
    """WP-6 item 5. Computed from the same reads the test makes, never guessed.

    Eight cards, eight buttons, and no path by which any of them could produce a row — and for
    five of them, no error either. Every one of those blockers is knowable without a model call.
    """
    from twinlab.services.validity import test_readiness

    # Tests 1 and 3 need stored H2 vectors.
    ready = await test_readiness(1, backend=backend)
    assert ready["ready"] is False and "quality gate" in ready["reason"]

    # Test 7 needs a second model name, and says so before the button is pressed.
    ready = await test_readiness(7, backend=backend)
    assert ready["ready"] is False and "second model name" in ready["reason"]

    # Tests 2 and 4-8 need a session with a frozen panel.
    ready = await test_readiness(4, backend=backend)
    assert ready["ready"] is False and "frozen panel" in ready["reason"]

    await backend.insert(
        "sessions",
        [{
            "session_id": "s-r", "name": "r", "kind": "ask", "status": "completed",
            "config": {}, "panel_size": 1, "panel_seed": 1,
        }],
    )
    await backend.insert(
        "session_panel",
        [{"session_id": "s-r", "twin_id": "T1", "stratum": "x", "position": 0}],
    )

    # Now 4-8 need a verified stimulus, named by code.
    ready = await test_readiness(4, session_id="s-r", backend=backend)
    assert ready["ready"] is False
    assert settings.start_code in ready["reason"] and "Checker-passed" in ready["reason"]

    # Test 2 needs a completed SHAM in that session.
    ready = await test_readiness(2, session_id="s-r", backend=backend)
    assert ready["ready"] is False and "SHAM" in ready["reason"]

    # With a stimulus, 4 is ready.
    await _store_variant(backend, settings.start_code, passed=True)
    ready = await test_readiness(4, session_id="s-r", backend=backend)
    assert ready["ready"] is True, ready["reason"]


async def test_wp6_the_version_control_offers_only_checker_passed_codes(backend):
    """WP-6 item 4. The *Version to test* dropdown may not offer an unverified cell (I3)."""
    from twinlab.services.validity import runnable_version_codes

    await _store_variant(backend, "01000", passed=True)
    await _store_variant(backend, "02000", passed=False)
    assert await runnable_version_codes(backend) == ["01000"]


# ============================================= WP-7: the Validation tab is honest and live


async def test_wp7_the_empty_state_counts_what_is_missing_and_names_the_gate(backend):
    """WP-7. The tab stopped instructing the researcher to press a disabled button.

    It is a read-only view over `twin_quality_runs`; there is no separate validation run to start.
    The empty state now says where the data comes from, and counts it.
    """
    from twinlab.services.lab import validation_view

    await backend.insert(
        "twins",
        [{"twin_id": f"T{i}", "source": "synthetic"} for i in range(5)],
    )
    view, rows = await validation_view(backend=backend)
    assert view.twins_total == 5
    assert view.twins_checked == 0
    assert rows == []


# ===================================== WP-8: Agent Studio governs the runtime


def test_wp8_a_saved_edit_reaches_the_runtime_without_a_restart():
    """WP-8 items 1 and 2. **The stored row wins over the YAML seed.**

    Agent Studio's edits were saved, versioned and audited — and read by nothing except Agent
    Studio, because every call site constructed its agent from `default_agent_configs()`. That is
    not compatible with `ARCHITECTURE.md` §1.1.
    """
    seeded = default_agent_configs()["twin"]
    set_live_agent_configs(
        {"twin": {"model": {**seeded.model.model_dump(), "name": "gpt-oss:20b"}}},
        {"twin": 4},
    )

    assert live_agent_configs()["twin"].model.name == "gpt-oss:20b"
    assert live_agent("twin").model.name == "gpt-oss:20b"
    assert default_agent_configs()["twin"].model.name == seeded.model.name, (
        "the seed is the restore target and must not be mutated"
    )
    assert live_agent_versions() == {"twin": 4}

    # And the twin agent the runtime actually builds carries it.
    assert twin_runtime.twin_agent_config().model.name == "gpt-oss:20b"


def test_wp8_a_stored_row_that_does_not_validate_falls_back_for_that_agent_only():
    """WP-8 item 1. One bad row costs one agent its edit, never the whole runtime.

    The live case is the stale `mistral` row: `ModelRef.provider` is
    `Literal["ollama", "openai", "mock"]`, so there is no `mistral` provider in the model at all
    and constructing it raises. Raising here would take down every call site rather than one
    screen, and the seed is a defined state to fall back to.
    """
    seeded = default_agent_configs()
    set_live_agent_configs(
        {
            "twin": {"model": {"provider": "mistral", "name": "mistral-small-latest"}},
            "analyst": {"model": {**seeded["analyst"].model.model_dump(), "name": "gpt-oss:20b"}},
        },
        {"twin": 3, "analyst": 2},
    )
    configs = live_agent_configs()
    assert configs["twin"].model.name == seeded["twin"].model.name, "twin fell back to the seed"
    assert configs["analyst"].model.name == "gpt-oss:20b", "the good row still took effect"


def test_wp8_a_live_config_cannot_introduce_a_tool_on_the_design_or_twin_agent():
    """WP-8, I2 and I6. `validate_config` runs on every merged config, not only on save.

    A stored row is not a trusted input. If it could give the design agent a tool, an `01000`
    render could absorb threshold 2.2 material and `01000` would stop differing from `02000`.
    """
    from twinlab.agents.registry import TOOL_REGISTRY

    tool = sorted(TOOL_REGISTRY)[0]
    set_live_agent_configs({"design": {"tools": [tool]}}, {"design": 2})
    assert live_agent_configs()["design"].tools == [], (
        "a stored row gave the design agent a tool (I2)"
    )
    set_live_agent_configs({"twin": {"tools": [tool]}}, {"twin": 2})
    assert live_agent_configs()["twin"].tools == [], "a stored row gave the twin a tool (I6)"


def test_wp8_a_live_config_cannot_introduce_native_output():
    """WP-8, I13. `NativeOutput` is forbidden and a stored row is not an exemption."""
    set_live_agent_configs({"twin": {"output_mode": "native"}}, {"twin": 2})
    assert live_agent_configs()["twin"].output_mode != "native"


def test_wp8_a_disabled_agent_is_refused_rather_than_run():
    """WP-8 item 4. `enabled` gated nothing: one read in the whole codebase, painting a pill."""
    set_live_agent_configs({"twin": {"enabled": False}}, {"twin": 2})
    assert live_agent_configs()["twin"].enabled is False
    with pytest.raises(AgentDisabled, match="switched off"):
        live_agent("twin")


async def test_wp8_the_quality_checker_cannot_be_disabled(backend):
    """WP-8 item 4. Disabling the coverage probe would let an unverified stimulus reach a twin.

    Refused at **save**, not merely hidden in the UI: the refusal has to hold for an API wrapper
    and a direct service call too (`CLAUDE.md` rule 1).
    """
    from twinlab.services.agent_config import (
        UNDISABLEABLE,
        AgentConfigError,
        save_agent,
    )

    assert "checker" in UNDISABLEABLE
    with pytest.raises(AgentConfigError, match="I3"):
        await save_agent("checker", {"enabled": False}, backend=backend)

    # And an agent with a defined off-path is still switchable.
    saved = await save_agent("analyst", {"enabled": False}, backend=backend)
    assert saved.enabled is False


async def test_wp8_a_disabled_analyst_uses_the_template_and_makes_no_model_call(backend):
    """WP-8 item 4. The one switch with a defined, already-tested meaning.

    The deterministic template carries `FALLBACK_PREFIX`, so a reader always knows which reading
    they are looking at — a template reading and a model's reading are different evidence and
    must not look alike (`docs/02` §6.2).
    """
    from twinlab.analysis.report import FALLBACK_PREFIX

    def _no_client(*args, **kwargs):
        raise AssertionError("the analyst was called while switched off")

    set_live_agent_configs({"analyst": {"enabled": False}}, {"analyst": 2})
    original = twin_runtime.get_client
    twin_runtime.get_client = _no_client
    try:
        from twinlab.ingest.reference_store import reference
        from twinlab.models.analysis import CellShifts

        shifts = CellShifts(
            version_code="01000",
            baselines={"fairness": 3.0},
            shifts={"fairness": 0.4},
            index_value=0.4,
            twin_ids=["T1"],
        )
        reading = await twin_runtime._reading("s", "01000", shifts, backend, reference())
    finally:
        twin_runtime.get_client = original

    assert reading.startswith(FALLBACK_PREFIX)


async def test_wp8_a_session_freezes_the_agent_versions_it_ran_under(backend):
    """WP-8 item 3. `ARCHITECTURE.md` §1.1's "frozen onto every run that used them", in the data.

    This **strengthens** I11 rather than weakening it: the run now records which agent version
    produced it, so two sessions under different agent configurations can never be silently
    compared.
    """
    from twinlab.services.agent_config import save_agent
    from twinlab.services.runs import session_config

    before = await session_config(backend)
    assert before["agent_versions"] == {}, "nothing stored, so no version to record"

    saved = await save_agent("analyst", {"model": {"provider": "ollama", "name": "gpt-oss:20b"}},
                             backend=backend)
    after = await session_config(backend)
    assert after["agent_versions"]["analyst"] == saved.version
    assert after["config_version"] == before["config_version"], (
        "an agent save is not a TwinConfig save and must not move that version"
    )


def test_wp8_the_twin_temperature_has_exactly_one_owner():
    """WP-8 item 5. The box showed `1` while the twin ran at 0.25.

    The temperature comes from `app_config['twin']` because that is what a session freezes onto
    its config column and what validity test 8 sets. So Agent Studio's box is read-only and says
    where the value lives, rather than showing a number the runtime silently discards.
    """
    from twinlab.services.agent_config import in_force

    force = in_force("twin")
    assert "app_config['twin']" in force["source"]
    assert "Settings" in force["source"]

    from twinlab.services.config import load_twin_config

    assert force["temperature"] == pytest.approx(load_twin_config().temperature)
    assert twin_runtime.twin_agent_config().model.temperature == pytest.approx(
        load_twin_config().temperature
    )


async def test_wp8_a_twin_save_leaves_the_rows_temperature_alone(backend):
    """WP-8 item 5, completed. Read-only was half the fix; the save path was the other half.

    The box is read-only and shows the value in force from `app_config['twin']`, so sending it on
    save would copy that number into the `agent_configs` row and leave two places holding it. The
    UI omits the key and `save_agent` merges `model` field-by-field, so the row keeps its own.
    """
    from twinlab.services.agent_config import load_agent, save_agent

    before = await load_agent("twin", backend=backend)
    stored = before.model.temperature

    after = await save_agent(
        "twin",
        {"role": "Edited.", "model": {"provider": "ollama", "name": "gpt-oss:120b"}},
        backend=backend,
    )
    assert after.model.name == "gpt-oss:120b", "the fields that were sent still change"
    assert after.model.temperature == pytest.approx(stored), (
        "a twin save must not write the in-force temperature into the row"
    )
    # A partial `model` must not hand the unsent fields to `ModelRef`'s defaults either: a reset
    # `seed` is a provenance loss (I11) and a reset `max_tokens` silently changes what the agent
    # can emit.
    assert after.model.max_tokens == before.model.max_tokens
    assert after.model.seed == before.model.seed


def test_wp8_in_force_reports_the_live_config_not_the_seed():
    """WP-8. `in_force` existed to report a gap; the gap is closed, so it reports the config."""
    from twinlab.services.agent_config import in_force

    seeded = default_agent_configs()["design"]
    assert in_force("design")["version"] is None
    assert "agents.default.yaml" in in_force("design")["source"]
    assert in_force("design")["differs_from_seed"] is False

    set_live_agent_configs(
        {"design": {"model": {**seeded.model.model_dump(), "name": "gpt-oss:20b"}}},
        {"design": 9},
    )
    force = in_force("design")
    assert force["model_name"] == "gpt-oss:20b"
    assert force["version"] == 9
    assert "agent_configs v9" in force["source"]
    assert force["differs_from_seed"] is True


async def test_wp8_the_policy_designer_card_names_its_model_free_half(backend):
    """WP-8 item 6. The researcher's instinct was half right, and that half is deterministic.

    Selecting the commitment set is `variant/lookup.py`, a pure frozen lookup over
    `dial_lookup.json` and `gaps.json` that consults no model (I1). Only turning that set into
    Uber-voice prose uses one. The card showed the two as a single step.
    """
    from twinlab.services.menu import AGENT_STEPS, agent_cards
    from twinlab.ui.components.domain import agent_card

    assert set(AGENT_STEPS) == {"manager", "design", "twin", "checker", "analyst"}
    deterministic, model_step = AGENT_STEPS["design"]
    assert "No AI model" in deterministic and "I1" in deterministic
    assert "one AI call" in model_step and "I4" in model_step

    cards = {c.agent_id: c for c in await agent_cards(backend)}
    assert cards["design"].deterministic_step == deterministic
    assert cards["checker"].undisableable is True
    assert "I3" in cards["checker"].undisableable_reason

    html = agent_card(cards["design"])
    assert "no AI model" in html and "uses AI" in html


# ========================================= WP-9: the Settings tab stops misinforming


async def test_wp9_a_saved_setting_governs_the_next_session(backend):
    """WP-9. The old message said nothing read `app_config` back. It did, and does.

    A researcher who believed it edited YAML by hand — unversioned, unaudited, and outside the
    `config_version` that `twin_quality_runs` records — which actively undoes the reproducibility
    chain the save button exists to maintain.
    """
    from twinlab.services.lab import save_settings
    from twinlab.services.runs import session_config

    version = await save_settings(
        "twin", {"quality_runs_per_twin": 2, "panel_size": 33}, backend=backend
    )
    frozen = await session_config(backend)
    assert frozen["quality_runs_per_twin"] == 2
    assert frozen["panel_size"] == 33
    assert frozen["config_version"] == version, (
        "the version the config came from must be recordable on the evidence row"
    )

    from twinlab.services.runs import effective_panel_size

    assert effective_panel_size() == 33


def test_wp9_the_settings_tab_no_longer_tells_the_researcher_to_edit_yaml():
    """WP-9 item 1, asserted against the source because it is a sentence on a screen."""
    from pathlib import Path

    source = Path("src/twinlab/ui/pages/lab.py").read_text(encoding="utf-8")
    assert "Edit the YAML to change behaviour" not in source
    assert "You do not need to edit any file." in source


# ============================================================ WP-10: "Twin today"


async def test_wp10_an_unmeasured_baseline_is_a_sentence_not_a_column_of_dashes(backend):
    """WP-10, I17. *Not yet measured* and *the twin declined* must be distinguishable.

    `00000` runs once per session, by the orchestrator, before the sweep — it is refused from the
    Dial board by design. With no session ever run the column is empty for every twin in every
    row, and nothing said why.
    """
    from twinlab.models.view import BASELINE_MEASURED, BASELINE_NOT_MEASURED
    from twinlab.services.lab import twin_panel
    from twinlab.ui.components.domain import answer_compare

    await backend.insert(
        "twins",
        [{
            "twin_id": "T1", "source": "synthetic", "persona_passage": "I drive.",
            "persona_hash": "h",
        }],
    )
    view = await twin_panel("T1", backend=backend)
    assert view.baseline_state == BASELINE_NOT_MEASURED
    assert BASELINE_MEASURED != BASELINE_NOT_MEASURED

    html = answer_compare(view)
    assert "has not been measured" in html
    assert "rather than zero" in html, "a dash can be read as a zero; the note says it is not"
    # The column header names the cell the numbers come from. The literal lives in `models/view`
    # because `ui/` may not import `orchestrator/` (`ARCHITECTURE.md` §4), so it is pinned against
    # the real constant here rather than left as two strings that can drift.
    from twinlab.models.view import BASELINE_COLUMN_HEADER
    from twinlab.orchestrator.odometer import CONTROL_CODE

    assert BASELINE_COLUMN_HEADER == f"Twin today ({CONTROL_CODE})"
    assert BASELINE_COLUMN_HEADER in html

    # And nothing fabricated a number.
    for block in view.blocks:
        for row in block.rows:
            assert row.baseline is None


async def test_wp3_a_gate_over_three_twins_makes_six_h3_calls_not_thirty_six(backend, monkeypatch):
    """WP-3's cost claim on the **call counter**, which is what `docs/11` asks of I4-style claims.

    3 twins x 2 repeats is `3 x 2 x 1 = 6` calls. It was `3 x 2 x 6 = 36`. Asserted by counting
    `ask_h3_round` invocations through the real `_gate_one_twin`, so the saving cannot be claimed
    by a constant that the gate does not actually obey.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.models.twin import TwinConfig
    from twinlab.orchestrator.events import EventLog
    from twinlab.services import quality

    ref = reference()
    codes = list(ref.h3_version_codes)
    # The two control stimuli are rendered by the gate too (RESEARCHER 2026-10-05).
    stimuli = {
        code: {lever: f"{code} says this about {lever}." for lever in LEVER_BY_POSITION}
        for code in [*codes, "00000", "SHAM"]
    }
    h3_ids = ref.holdout_h3_item_ids

    calls: list[dict] = []

    async def _fake_h3_round(**kwargs):
        calls.append(kwargs)
        # Every one of the 18 items, so the repeat is scorable and the gate does not discard it.
        return {i: 4 for i in h3_ids}, {"protocol": quality.H3_PROTOCOL}

    monkeypatch.setattr(quality, "ask_h3_round", _fake_h3_round)

    # The control answers are one battery round each. Stubbed, so the count below is H3 only.
    control_calls: list[str] = []

    async def _fake_ask_items(**kwargs):
        control_calls.append(kwargs["version_code"])
        battery = {item: 3 for item in ref.battery_item_ids}
        return battery, {"lever_order": [0, 1, 2, 3, 4], "model": "stub",
                         "prompt_version": "p", "retries": 0}

    monkeypatch.setattr(quality, "ask_items", _fake_ask_items)

    # The drivers' own answers, so `score_holdout` has both sides.
    await backend.insert(
        "twins",
        [
            {"twin_id": f"T{i}", "source": "synthetic", "submission_id": f"S{i}"}
            for i in range(3)
        ],
    )
    await backend.insert(
        "survey_answers",
        [
            {"submission_id": f"S{i}", "item_id": item, "value_num": 4}
            for i in range(3)
            for item in h3_ids
        ],
    )

    events = EventLog("s-m19-count", backend)
    parent = await events.emit(stage="ask", label="parent")
    config = TwinConfig(quality_runs_per_twin=2)

    for i in range(3):
        await quality._gate_one_twin(
            twin_id=f"T{i}",
            stimuli=stimuli,
            repeats=2,
            include_h2=False,
            config=config,
            config_version=1,
            session_id="s-m19-count",
            ref=ref,
            events=events,
            parent=parent,
            db=backend,
            fingerprint="fp-test",
        )

    assert len(calls) == 6, (
        f"3 twins x 2 repeats made {len(calls)} H3 calls; WP-3 requires 6 (one per repeat, all "
        "six Part-17 versions in it), and the old protocol made 36"
    )
    # Plus one control answer per twin per control, and no more: 3 twins x 2 controls.
    assert sorted(control_calls) == sorted(["00000", "SHAM"] * 3)
    # Each call carried all six versions and all 18 items, so the saving is not a lost measurement.
    for kwargs in calls:
        assert len(kwargs["paragraphs_by_version"]) == len(codes)
        assert sum(len(v) for v in kwargs["items_by_version"].values()) == 18

    # And every row says which protocol produced it, so two protocols cannot be pooled.
    rows = await backend.select("twin_quality_runs", [("eq", "holdout_set", "H3")])
    assert len(rows) == 3
    for row in rows:
        assert (row.get("detail") or {}).get("protocol") == quality.H3_PROTOCOL
        # 18 per repeat, **summed** across repeats — `validity.quality.average_scores` is
        # explicit that `items_n` is a count of measurements taken rather than a mean, so that
        # the verdict says how much evidence it rests on. Two repeats of 18 is 36.
        #
        # Worth noting against the plan: acceptance check A-2 asks for `items_n = 18` on each
        # row, which only holds at one repeat. The code's reading is the better one and is kept;
        # **A-2's wording needs correcting to `18 x quality_runs_per_twin`.**
        assert int(row["items_n"]) == 18 * 2, "18 H3 items per repeat, summed over 2 repeats"


# ================================= show_baseline reversed, docs/DECISIONS.md 2026-10-07
#
# The earlier tests for this change only proved two things: that the seed's default flipped
# (`test_m6_twin_quality`) and that the existing suite still passes. Neither proves that the three
# call sites which used to hard-code `show_baseline=True` now actually *read* the live config —
# a wiring mistake there would have left every validity test, every Studio ask and the Twin
# Interviewer silently showing the baseline regardless of the flip, and nothing above would have
# caught it. These close that gap, each against the live `TwinConfig`, not a hard-coded value.


def test_the_registered_twin_prompt_has_no_baseline_language() -> None:
    """Guards the YAML pointer and the prompt text together. A revert of `config/agents.default.
    yaml` back to `twin_v1.md` without also reverting `show_baseline` — or the reverse — would
    silently reintroduce the anchor this decision removed."""
    from twinlab.agents.registry import resolve_prompt

    text, _ = resolve_prompt(default_agent_configs()["twin"])
    # The frontmatter's own `changed:` note names the old fence and the old rule's wording, by
    # design (it says what v2 removed) — strip it so that note cannot false-positive this check.
    body = text.split("---", 2)[-1]
    assert "<<<BASELINE>>>" not in body
    assert "leaving a number exactly where it was" not in body.lower()


async def test_ask_panel_twins_reads_the_live_show_baseline_config(backend) -> None:
    """Every validity test that makes a fresh call (2, 4-8) goes through this. Before this it
    hard-coded `show_baseline=True`, so flipping the config would have silently done nothing here
    — the one path the Twin Lab's validity tab actually runs."""
    from unittest import mock

    from twinlab.services import config as cfg
    from twinlab.services.twin_runtime import ask_panel_twins

    async def fake_driver_answers(_twin_id, _db):
        return {}

    seen: list[bool | None] = []

    async def fake_ask_items(**kwargs):
        seen.append(kwargs.get("show_baseline"))
        return {"X": 1}, {"lever_order": [0], "model": "m", "prompt_version": "1", "retries": 0}

    for forced in (True, False):
        cfg._override["show_baseline"] = forced
        seen.clear()
        with mock.patch(
            "twinlab.services.twin_runtime.driver_answers", new=fake_driver_answers
        ), mock.patch("twinlab.services.twin_runtime.ask_items", new=fake_ask_items):
            await ask_panel_twins(
                twin_ids=["T1"], paragraphs={"L1": "x"}, purpose="probe", backend=backend
            )
        assert seen == [forced], f"show_baseline={forced} was not what ask_items received"


async def test_studio_and_agent_studio_also_read_the_live_show_baseline_config(backend) -> None:
    """The other two call sites fixed alongside `ask_panel_twins`. Both used to hard-code
    `show_baseline=True` too, which would have left Twin Studio and the Twin Interviewer showing a
    different instrument than the one the live config — and the sweep — actually runs under."""
    from unittest import mock

    from twinlab.ingest.reference_store import reference
    from twinlab.services.config import refresh_twin_config
    from twinlab.services.lab import save_settings

    full_vector = {item: 3 for item in reference().battery_item_ids}
    seen: list[bool | None] = []

    async def fake_ask_items(**kwargs):
        seen.append(kwargs.get("show_baseline"))
        # A full 37-item vector: `ask_studio` and `twin_test_view` both score the reply for
        # display, and a short fixture would fail there instead of proving this test's point.
        return (
            dict(full_vector),
            {"lever_order": [0], "model": "m", "prompt_version": "1", "retries": 0},
        )

    from tests._qualify import qualify

    await backend.insert(
        "twins",
        [{
            "twin_id": "T1", "source": "real", "service": "Uber Go", "city": "Mumbai",
            "consent_twin": True, "persona_passage": "A persona passage.", "persona_hash": "h",
        }],
    )
    await VariantRepo(backend).put(
        version_code="01000", style_version=settings.style_version,
        delta_spec={"version_code": "01000"}, delta_hash="h",
        paragraphs={lever: {"text": "x"} for lever in LEVER_BY_POSITION},
        checker={"passed": True},
    )

    # Both call `from twinlab.services.twin_runtime import ask_items` **inside** the function body
    # rather than at module import time, so the patch target is the source, not either caller.
    # `ask_studio`, not `run_studio` — `run_studio` only records a row via RPC and never calls a
    # model itself; `ask_studio` is `docs/06` §5's "Ask the twin, for real" and is where the fixed
    # `show_baseline` line actually lives.
    #
    # `show_baseline` is poked through `save_settings`, not `cfg._override` directly: both
    # `ask_studio` and `twin_test_view` call `current_fingerprint`, which calls
    # `refresh_twin_config` internally — a direct `_override` write would be silently discarded by
    # that refresh before the config was even read, which is itself worth knowing. Because
    # `show_baseline` is part of the fingerprint, the twin has to be re-qualified for each value.
    for forced in (True, False):
        await save_settings("twin", {"show_baseline": forced}, backend=backend)
        await refresh_twin_config(backend)
        await qualify(backend, "T1")

        seen.clear()
        with mock.patch("twinlab.services.twin_runtime.ask_items", new=fake_ask_items):
            from twinlab.services.studio import ask_studio

            await ask_studio(
                twin_id="T1", version_code="01000", include_battery=True, backend=backend
            )
        assert seen == [forced], f"Studio: show_baseline={forced} was not what ask_items received"

        seen.clear()
        with mock.patch("twinlab.services.twin_runtime.ask_items", new=fake_ask_items):
            from twinlab.services.agent_config import twin_test_view

            await twin_test_view("T1", "01000", backend=backend)
        assert seen == [forced], (
            f"Agent Studio: show_baseline={forced} was not what ask_items received"
        )
