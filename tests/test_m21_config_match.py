"""M21 — the config-matched quality test (`005`, RESEARCHER 2026-10-05).

Each test names the rule it guards. The rule: a quality verdict and a twin's control answers belong
to the config they were made under. Nothing that uses a twin (a session, a sweep, a resume, a
validity test, the Studio) may run on a verdict from another config, and the controls are answered
once per twin per config, never per session.
"""

from __future__ import annotations

import pytest

from twinlab.db.repositories import ControlAnswerRepo, SessionRepo
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE
from twinlab.services.config import refresh_twin_config
from twinlab.services.config_match import (
    current_config,
    current_fingerprint,
    qualified_state,
    qualified_twin_ids,
)
from twinlab.services.lab import save_settings

from ._qualify import qualify


async def test_the_fingerprint_changes_when_the_temperature_changes(backend):
    """Changing the model or temperature must change the fingerprint, or a stale verdict would
    silently qualify a twin for a config it was never tested under."""
    await refresh_twin_config(backend)
    before = await current_fingerprint(backend)
    assert before == await current_fingerprint(backend), "the fingerprint is stable"

    await save_settings("twin", {"temperature": 0.3}, backend=backend)
    await refresh_twin_config(backend)
    after = await current_fingerprint(backend)
    assert after != before
    assert (await current_config(backend))["temperature"] == pytest.approx(0.3)


async def test_the_fingerprint_covers_the_h3_gates_own_prompt(backend):
    """The Part 17 prompt is **not** the twin prompt, and both must move the fingerprint.

    `H3_PROMPT_REF` swaps in a sibling file for the H3 round only, so `prompt_sha256` describes
    the battery and sweep rounds and says nothing about the prompt that produced every stored H3
    verdict. While that was missing, rewriting the H3 prompt left the fingerprint unmoved: the gate
    reported "already scored under this config" and **skipped every twin**, and a verdict made
    under a superseded Part 17 prompt read as current. Found by re-gating after `twin_h3_v3.md`
    (`docs/DECISIONS.md`, 2026-10-13).

    Asserted as a distinct key rather than through a prompt edit, because the H3 prompt is a
    frozen stimulus file and a test must not depend on editing one.
    """
    from twinlab.services.config_match import current_config

    await refresh_twin_config(backend)
    config = await current_config(backend)
    assert "h3_prompt_sha256" in config, (
        "the H3 round's prompt is absent from the fingerprint, so a rewritten Part 17 prompt "
        "would not invalidate a single stored verdict"
    )
    assert config["h3_prompt_sha256"], "the H3 prompt hash is empty"
    # The two prompts are different files, so conflating them would hide a change to either.
    assert config["h3_prompt_sha256"] != config["prompt_sha256"], (
        "the H3 hash equals the twin hash, so H3_PROMPT_REF is not being applied and the gate "
        "is not sending the prompt the fingerprint claims"
    )


async def test_a_verdict_under_another_config_does_not_qualify_a_twin(backend):
    """The panel draw reads only verdicts under the live fingerprint. A kept verdict from an old
    config is inert, and the state counts it as stale so the refusal can say why."""
    await qualify(backend, "T1", kept=True, fingerprint="an-older-config")
    live = await current_fingerprint(backend)

    assert await qualified_twin_ids(live, backend) == set()
    state = await qualified_state(live, backend)
    assert state["stale"] == 1
    assert state["controlled"] == 0


async def test_a_verdict_without_both_controls_does_not_qualify_a_twin(backend):
    """A verdict with a missing control is not a finished result (I15). It cannot put a twin on a
    panel, because the floors that twin would be measured against do not exist."""
    live = await current_fingerprint(backend)
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "T2", "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
            "config_fingerprint": live,
        }],
    )
    assert await qualified_twin_ids(live, backend) == set()
    await ControlAnswerRepo(backend).record(
        twin_id="T2", control_code=CONTROL_CODE, fingerprint=live, answers={"AMQ1": 3},
        lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub", prompt_version=None,
        retries=0, session_id=None,
    )
    assert await qualified_twin_ids(live, backend) == set(), "one control is not both controls"
    await ControlAnswerRepo(backend).record(
        twin_id="T2", control_code=SHAM_CODE, fingerprint=live, answers={"AMQ1": 3},
        lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub", prompt_version=None,
        retries=0, session_id=None,
    )
    assert await qualified_twin_ids(live, backend) == {"T2"}


async def test_control_answers_are_written_once_per_twin_per_config(backend):
    """One answer per (twin, control, config). A second record finds the first and writes nothing,
    which is what keeps a repeat gate run at zero control calls."""
    repo = ControlAnswerRepo(backend)
    kwargs = dict(
        twin_id="T3", control_code=CONTROL_CODE, fingerprint="fp-a", answers={"AMQ1": 2},
        lever_order=[0, 1, 2, 3, 4], seed=9, wording="A", model="stub", prompt_version=None,
        retries=0, session_id=None,
    )
    await repo.record(**kwargs)
    second = await repo.record(**{**kwargs, "answers": {"AMQ1": 5}})
    assert len(await repo.for_fingerprint(CONTROL_CODE, "fp-a")) == 1
    assert second["answers"] == {"AMQ1": 2}, "the first answer stands; it is never replaced"


async def test_asking_the_twins_refuses_when_the_config_is_not_validated(backend):
    """Dial board / sweep stage. Nothing qualified under the live config: refused, not written."""
    from twinlab.services.runs import NotReadyToSweep, ask_twins

    await backend.insert("twins", [{"twin_id": "T4", "source": "real", "submission_id": "S4"}])
    await qualify(backend, "T4", kept=True, fingerprint="an-older-config")
    with pytest.raises(NotReadyToSweep) as caught:
        await ask_twins("01000", population="real", panel_size=1)
    assert "current config" in str(caught.value)
    assert await SessionRepo(backend).by_status("created") == [], "no session row was written"


async def test_a_resume_refuses_a_session_started_under_another_config(backend):
    """A paused session resumed after the config changed would mix two configs into one
    experiment, so it is refused with the reason and the way out."""
    from twinlab.services.runs import NotReadyToSweep, resume_session

    repo = SessionRepo(backend)
    session = await repo.create(
        name="old", kind="sweep", iterations=1, start_code="01000", panel_size=1,
        config={"config_fingerprint": "an-older-config"},
    )
    await repo.set_status(session.session_id, "paused")
    with pytest.raises(NotReadyToSweep) as caught:
        await resume_session(session.session_id, backend=backend)
    assert "different config" in str(caught.value)


async def test_a_validity_test_on_a_session_from_another_config_is_inconclusive(backend):
    """A validity test reads a session's answers. Under another config it is INCONCLUSIVE, and the
    attempt is still appended to the record."""
    from twinlab.services.validity import run_validity_test

    repo = SessionRepo(backend)
    session = await repo.create(
        name="old", kind="sweep", iterations=1, start_code="01000", panel_size=1,
        config={"config_fingerprint": "an-older-config"},
    )
    outcome = await run_validity_test(1, session_id=session.session_id, backend=backend)
    assert outcome.verdict == "INCONCLUSIVE"
    assert "config" in outcome.headline
    recorded = await backend.select("validity_results", None)
    assert len(recorded) == 1


async def test_the_studio_refuses_when_the_live_config_has_no_validated_twin(backend):
    """The Studio asks a twin. With nothing validated under the live config it refuses."""
    from twinlab.services.studio import StudioError, ask_studio

    with pytest.raises(StudioError) as caught:
        await ask_studio(twin_id="T9", version_code="01000", backend=backend)
    assert "quality test has not been run" in str(caught.value)


async def test_a_session_records_the_fingerprint_it_started_under(backend):
    """`session_config` freezes the fingerprint onto the session, so a later resume can compare."""
    from twinlab.services.runs import session_config

    cfg = await session_config(backend)
    assert cfg["config_fingerprint"] == await current_fingerprint(backend)



async def test_the_gate_skips_a_twin_already_scored_under_this_config(backend):
    """The gate's cache. A twin with a current verdict and both controls is skipped, so a repeat run
    spends no calls. A twin scored under another config is not skipped, because its verdict does not
    describe this config."""
    from twinlab.services.quality import _already_qualified

    live = await current_fingerprint(backend)
    await qualify(backend, "T5", kept=False)
    await qualify(backend, "T6", kept=True, fingerprint="an-older-config")

    assert await _already_qualified("T5", live, backend) is False, "kept=False is final"
    assert await _already_qualified("T6", live, backend) is None, "another config must be re-gated"


async def test_the_grid_never_pairs_a_version_with_a_control(backend):
    """Defect fixed 2026-10-05: clicking a tested version blanked the side panel with
    `ValueError: invalid literal for int() with base 10: 'S'`, because `SHAM` reached the
    interaction step as a dial vector. Controls are not versions, so they never appear as
    interaction partners.
    """
    from twinlab.services.results import shifts_by_code

    runs = [
        {"version_code": "20002", "metrics": {"shifts": {"fairness": 0.7}}, "status": "completed"},
        {"version_code": CONTROL_CODE, "metrics": {"shifts": {"fairness": 0.1}},
         "status": "completed"},
        {"version_code": SHAM_CODE, "metrics": {"shifts": {"fairness": 0.3}},
         "status": "completed"},
    ]

    async def _runs(_backend=None):
        return runs

    import twinlab.services.results as results

    original = results.completed_runs
    results.completed_runs = _runs
    try:
        shifts = await shifts_by_code(backend)
    finally:
        results.completed_runs = original
    assert set(shifts) == {"20002"}


async def test_a_control_floor_gets_the_deterministic_prose_and_no_model_call(backend, monkeypatch):
    """The two control floors are written by the template, so no session calls the Analyst for them.
    The Analyst is made to fail if it is reached, so the test cannot pass by accident.
    """
    from twinlab.analysis import report
    from twinlab.analysis.metrics import compute_shifts
    from twinlab.ingest.reference_store import reference
    from twinlab.services import twin_runtime

    ref = reference()
    battery = ref.battery_item_ids
    shifts = compute_shifts(
        baseline_vectors={"T1": {i: 3 for i in battery}},
        variant_vectors={"T1": {i: 4 for i in battery}},
        version_code=SHAM_CODE,
        weights=None,
        ref=ref,
    )

    def _no_model(*args, **kwargs):
        raise AssertionError("the Analyst was called for a control floor")

    monkeypatch.setattr(report, "write_analysis", _no_model)
    monkeypatch.setattr(twin_runtime, "live_agent", _no_model)

    prose = await twin_runtime._reading("s-ctrl", SHAM_CODE, shifts, backend, ref)
    assert prose.startswith(report.FALLBACK_PREFIX)
