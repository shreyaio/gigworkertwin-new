"""M11 — Twin Studio and Agent Studio. Acceptance tests for `docs/11_BUILD_PLAN.md` → M11.

Each of M11's eight acceptance bullets has a test below naming it, and every prohibition also has
the test that proves it rejects a violation — a gate that cannot fail is not a gate
(`docs/11` → Testing rules).

The heaviest of them is the **quarantine**: `docs/01` §6.9 says a studio run never appears in
`runs`, never contributes to a metric, a shift, an index or the Results grid, and never enters
Statistics. That is asserted here by running the Studio and then reading every downstream surface
the rest of the application computes from.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "twinlab"


# ======================================================= Twin Studio selectors


async def test_from_a_survey_answer_lists_only_real_consented_respondents(backend):
    """M11: *From a survey answer* lists **only real, consented** respondents.

    Synthetic rows must not appear. The bullet is about the selector, so this asserts over what
    the selector returns rather than over the query that built it.
    """
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.studio import survey_candidates

    await _submission(backend, "REAL-YES", data_type="REAL", consent_twin=True)
    await _submission(backend, "REAL-NO", data_type="REAL", consent_twin=False)
    await _submission(backend, "SYN-1", data_type=SYNTHETIC_DATA_TYPE, consent_twin=True)
    await _submission(backend, "REAL-INELIGIBLE", data_type="REAL", consent_twin=True,
                      eligible=False)

    offered = {c["submission_id"] for c in await survey_candidates(backend)}
    assert offered == {"REAL-YES"}
    assert "SYN-1" not in offered, "synthetic rows must not appear in this selector"
    assert "REAL-NO" not in offered, "statement 7 is the consent gate (docs/01 §6.2)"


async def test_creating_a_twin_refuses_a_synthetic_or_unconsented_row(backend):
    """The rule is enforced next to the write, not only in the selector."""
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.studio import StudioError, create_twin_from_survey

    await _submission(backend, "SYN-1", data_type=SYNTHETIC_DATA_TYPE, consent_twin=True)
    await _submission(backend, "REAL-NO", data_type="REAL", consent_twin=False)

    with pytest.raises(StudioError, match="synthetic"):
        await create_twin_from_survey("SYN-1", backend=backend)
    with pytest.raises(StudioError, match="consent|statement 7"):
        await create_twin_from_survey("REAL-NO", backend=backend)


async def test_use_a_twin_i_have_includes_twins_the_gate_dropped(backend):
    """`docs/06` §5: non-passed twins may be **inspected** here, though never studied.

    This is the one selector that deliberately does not filter on quality, so it is asserted
    rather than assumed.
    """
    from twinlab.services.studio import studio_twins

    await _twin(backend, "T-KEPT")
    await _twin(backend, "T-DROPPED")
    await _quality(backend, "T-DROPPED", kept=False, mae=1.4)

    assert {t.twin_id for t in await studio_twins(backend)} == {"T-KEPT", "T-DROPPED"}


# ==================================================== the manual twin and panels


async def test_a_hand_built_twin_is_manual_and_never_enters_a_panel(backend):
    """M11: a hand-built twin is stored ``source='manual'`` and is **never** drawn into a panel.

    Asserted against the panel rule itself, not just the stored string: `POPULATION_SOURCES` names
    no ``manual`` population, so no session setting — not even ``both`` — can reach one
    (`docs/03` §9.3).
    """
    from twinlab.models.twin import PanelCandidate
    from twinlab.orchestrator.panel import POPULATION_SOURCES, eligible_candidates
    from twinlab.services.studio import MANUAL_SOURCE, create_manual_twin

    twin = await create_manual_twin(
        city="Mumbai", service="Uber Go", age=41, backend=backend
    )
    assert twin.source == MANUAL_SOURCE == "manual"

    rows = await backend.select("twins", [("eq", "twin_id", twin.twin_id)])
    assert rows[0]["source"] == "manual"

    # No population admits it.
    assert "manual" not in set().union(*POPULATION_SOURCES.values())
    candidate = PanelCandidate(
        twin_id=twin.twin_id, source="manual", city="Mumbai", service="Uber Go",
        quality_passed=True,
    )
    for population in POPULATION_SOURCES:
        assert eligible_candidates([candidate], population) == [], population


async def test_a_manual_twin_carries_no_persona_passage(backend):
    """A persona is a lossless reconstruction of a real driver (I6). There is no driver here.

    Writing one would make a fabricated passage indistinguishable from a reconstructed one.
    """
    from twinlab.services.studio import create_manual_twin

    twin = await create_manual_twin(city="Pune", service="Moto", backend=backend)
    rows = await backend.select("twins", [("eq", "twin_id", twin.twin_id)])
    assert not rows[0].get("persona_passage")
    assert not rows[0].get("persona_hash")


# ======================================================== the quarantine
#
# `ARCHITECTURE_UPDATE.md` §1.1, confirmed by the researcher on 2026-10-01: *"by overwrite, it's ok
# for the studio values to feed analyses"*. `docs/01` §6.9's blanket quarantine is therefore
# narrowed, NOT removed, and these tests guard the wall where it now runs:
#
#   * `run_studio` itself still has no code path to `runs` or `twin_answers` — filing is a separate,
#     explicitly-called function, so the quarantine of the recording path is still a property of the
#     function rather than of a caller's discipline;
#   * a **custom free-text change** is still fully quarantined, and is now the one path that is;
#   * `twin_quality_runs` and `validity_results` remain unreachable from this module entirely;
#   * every evidence write is an append or a pointer flip, so `CLAUDE.md` rule 6 is untouched.
#
# See `docs/DECISIONS.md`, 2026-10-01.


async def test_run_studio_alone_writes_studio_runs_and_reaches_no_metric(backend):
    """`run_studio` writes `studio_runs` and nothing else — the sandbox record is still a wall.

    Filing a Studio ask as evidence is `file_studio_run`'s job and is called separately, so the
    recording function on its own still reaches no metric, shift, index, Results cell or Statistics
    row. Asserted by reading every downstream surface the application computes from, rather than by
    trusting that nothing joined to it.
    """
    from twinlab.services.results import completed_runs, shifts_by_code, tested_rows
    from twinlab.services.status import tested_codes, where_things_stand
    from twinlab.services.studio import run_studio

    await _twin(backend, "T1")
    before_runs = await backend.count("runs")

    await run_studio(
        twin_id="T1",
        version_code="01000",
        questions=["Would you keep driving?"],
        include_battery=True,
        answers={"FAIR1": 5},
        backend=backend,
    )

    assert await backend.count("studio_runs") == 1
    assert await backend.count("runs") == before_runs == 0, (
        "`run_studio` never enters `runs`; only `file_studio_run` does, and only for a dialled "
        "version with a complete answer vector"
    )
    assert await backend.count("twin_answers") == 0

    # Nothing downstream sees it.
    assert await tested_codes(backend) == {}
    assert await completed_runs(backend) == []
    assert await tested_rows(backend) == []
    assert await shifts_by_code(backend) == {}
    stand = {r.label: r.value for r in await where_things_stand(backend)}
    assert stand["Versions tested"] == "0 of 242"
    assert stand["Twin answers saved"] == "0"


def test_the_studio_still_cannot_reach_the_quality_or_validity_tables():
    """Two tables stay unreachable from this module **entirely**, override or no override.

    `twin_quality_runs` is the keep/drop verdict a twin is admitted to the study on, and
    `validity_results` is the validity suite's own evidence. Neither has anything to do with asking
    one twin a question, and a Studio write to either would be a twin tuning its own admission.

    Asserted over the source, because a future edit that added one would pass every behavioural test
    in this file until someone used it.
    """
    source = (SRC / "services" / "studio.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned = {"twin_quality_runs", "validity_results"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        method = getattr(node.func, "attr", None)
        if method not in ("insert", "upsert", "update", "delete", "rpc"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            table = node.args[0].value
            assert table not in banned, (
                f"services/studio.py:{node.lineno} writes to {table!r}. The Studio may file a "
                "dialled version as a run (ARCHITECTURE_UPDATE.md §1.1) but it never touches a "
                "twin's quality verdict or the validity suite's evidence."
            )


def test_evidence_writes_from_the_studio_are_appends_and_pointer_flips_only():
    """`CLAUDE.md` rule 6 survives the override: **no UPDATE or DELETE on an evidence table.**

    The override is only safe because filing a Studio ask APPENDS.
    `services/results.completed_runs` already takes the latest run per `version_code` by
    `started_at`, so a later Dial board run supersedes a Studio value with no precedence logic to
    write — but only as long as nothing here rewrites a stored one.

    Zero, not "one for `origin`": `origin` is set on the INSERT, through
    `RunRepo.get_or_create(origin=...)`. A row this module created a line earlier is still a `runs`
    row, and an UPDATE to one is the shape nobody should have to reason about case by case.
    """
    source = (SRC / "services" / "studio.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    evidence = {"runs", "twin_answers", "studio_runs"}
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        method = getattr(node.func, "attr", None)
        if method not in ("update", "delete"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Constant)):
            continue
        if node.args[0].value in evidence:
            found.append((node.lineno, method, node.args[0].value))

    assert found == [], (
        "services/studio.py must never UPDATE or DELETE an evidence row; every write is an insert, "
        f"an upsert or a pointer-flip RPC. Found: {found}"
    )


async def test_a_custom_change_is_labelled_sandbox_and_files_no_version_code(backend):
    """M11: a custom free-text change is labelled *sandbox — not a study result*.

    It bypasses the lookup (I1) and the Checker (I3), so it is not a Fairwork treatment. It also
    stores `version_code = NULL`: filing free text under one of the 243 would make it findable as
    a cell.
    """
    from twinlab.services.studio import SANDBOX_LABEL, run_studio

    await _twin(backend, "T1")
    result = await run_studio(
        twin_id="T1",
        custom_change="What if Uber paid weekly and published the formula?",
        backend=backend,
    )
    assert result["sandbox"] is True
    assert result["label"] == SANDBOX_LABEL == "sandbox — not a study result"
    assert result["version_code"] is None

    rows = await backend.select("studio_runs", None)
    assert rows[0]["version_code"] is None
    assert rows[0]["custom_change"].startswith("What if Uber paid weekly")


async def test_a_version_coded_studio_run_is_not_labelled_sandbox(backend):
    """The label must discriminate. A run on one of the 243 went through the lookup."""
    from twinlab.services.studio import run_studio

    await _twin(backend, "T1")
    result = await run_studio(twin_id="T1", version_code="01000", backend=backend)
    assert result["sandbox"] is False
    assert result["label"] == ""
    assert result["version_code"] == "01000"


async def test_the_studio_refuses_more_than_five_questions(backend):
    """`docs/06` §5: one per line, **up to 5**."""
    from twinlab.services.studio import MAX_QUESTIONS, StudioError, run_studio

    await _twin(backend, "T1")
    assert MAX_QUESTIONS == 5
    with pytest.raises(StudioError, match="at most 5"):
        await run_studio(
            twin_id="T1",
            version_code="01000",
            questions=[f"q{i}" for i in range(6)],
            backend=backend,
        )


async def test_a_studio_run_needs_a_version_or_a_change(backend):
    """Neither given is a refusal, not an empty run."""
    from twinlab.services.studio import StudioError, run_studio

    await _twin(backend, "T1")
    with pytest.raises(StudioError, match="version code or a custom change"):
        await run_studio(twin_id="T1", backend=backend)


# ===================================================== Agent Studio config


async def test_saving_an_agent_writes_history_with_changed_fields(backend):
    """M11: Agent Studio save writes an `agent_config_history` row with `changed_fields`."""
    from twinlab.services.agent_config import history, save_agent

    after = await save_agent("twin", {"role": "A different role."}, backend=backend)
    assert after.version == 2

    rows = await history("twin", backend=backend)
    assert len(rows) == 1
    assert rows[0]["action"] == "saved"
    assert rows[0]["changed_fields"] == ["role"]
    assert rows[0]["version"] == 2
    assert rows[0]["snapshot"]["role"] == "A different role."


async def test_restore_and_freeze_each_write_their_own_history_row(backend):
    """M11: restore and freeze **each write their own**. A history row is never replaced (I9)."""
    from twinlab.services.agent_config import (
        history,
        restore_agent,
        save_agent,
        set_frozen,
    )

    await save_agent("twin", {"role": "Edited."}, backend=backend)
    await restore_agent("twin", backend=backend)
    await set_frozen("twin", True, backend=backend)
    await set_frozen("twin", False, backend=backend)

    # Newest first — the order the *What was changed* log reads them in.
    rows = await history("twin", backend=backend)
    assert [r["action"] for r in rows] == ["unfrozen", "frozen", "restored", "saved"]
    # Append-only: every write has its own row and its own version, and none replaced another.
    assert [r["version"] for r in rows] == [5, 4, 3, 2]
    assert rows[1]["changed_fields"] == ["frozen"]


async def test_restore_puts_the_seeded_text_back(backend):
    """*Put the original text back* restores the seeded default, not the previous edit."""
    from twinlab.agents.registry import default_agent_configs
    from twinlab.services.agent_config import restore_agent, save_agent

    original = default_agent_configs()["twin"].role
    await save_agent("twin", {"role": "Edited."}, backend=backend)
    restored = await restore_agent("twin", backend=backend)
    assert restored.role == original


async def test_a_frozen_agent_cannot_be_edited_while_a_session_is_running(backend):
    """M11: a frozen agent cannot be edited while a session is running. `docs/06` §6."""
    from twinlab.db.repositories import SessionRepo
    from twinlab.services.agent_config import AgentFrozen, save_agent, set_frozen

    await set_frozen("twin", True, backend=backend)
    session = await SessionRepo(backend).create(name="live")
    await SessionRepo(backend).set_status(session.session_id, "running")

    with pytest.raises(AgentFrozen, match="frozen"):
        await save_agent("twin", {"role": "Sneaky edit."}, backend=backend)


async def test_a_frozen_agent_is_editable_when_nothing_is_running(backend):
    """The refusal must discriminate: freezing alone does not lock the agent forever."""
    from twinlab.services.agent_config import save_agent, set_frozen

    await set_frozen("twin", True, backend=backend)
    after = await save_agent("twin", {"role": "An allowed edit."}, backend=backend)
    assert after.role == "An allowed edit."
    assert after.frozen is True, "a save must not silently unfreeze"


async def test_an_unfrozen_agent_is_editable_while_a_session_runs(backend):
    """The gate is about *frozen*, not about *running*. An unfrozen agent stays editable."""
    from twinlab.db.repositories import SessionRepo
    from twinlab.services.agent_config import save_agent

    session = await SessionRepo(backend).create(name="live")
    await SessionRepo(backend).set_status(session.session_id, "running")
    after = await save_agent("twin", {"role": "Still allowed."}, backend=backend)
    assert after.role == "Still allowed."


def test_native_is_not_offered_as_an_output_mode():
    """M11: `native` is not offered. `docs/02` §5.1, I13.

    Absent by construction at three levels: the UI list, the Pydantic validator, and
    `build_agent`. The provider accepts a JSON schema and silently does not enforce it, so a
    `native` agent would look like it worked.
    """
    from twinlab.models.agent import FORBIDDEN_OUTPUT_MODE, AgentConfig
    from twinlab.services.agent_config import OUTPUT_MODES

    assert OUTPUT_MODES == ("tool", "prompted")
    assert FORBIDDEN_OUTPUT_MODE not in OUTPUT_MODES

    # And it cannot be constructed even if something tried.
    with pytest.raises(Exception, match="native"):
        AgentConfig(
            agent_id="x", name="x", role="x",
            model={"provider": "ollama", "name": "m"},
            system_prompt="x", input_schema="a", output_schema="b",
            output_mode="native",
        )


def test_the_agent_studio_page_never_offers_native():
    """Asserted over the page source too: the dropdown is built from `OUTPUT_MODES`."""
    source = (SRC / "ui" / "pages" / "agent_studio.py").read_text(encoding="utf-8")
    assert "list(OUTPUT_MODES)" in source
    assert '"native"' not in source and "'native'" not in source


async def test_saving_rules_writes_a_new_app_config_version(backend):
    """*Save rules* → a new `app_config` version; historical runs untouched. `docs/06` §6."""
    from twinlab.services.agent_config import WEIGHT_METRICS, save_rules
    from twinlab.services.lab import config_version

    weights = dict.fromkeys(WEIGHT_METRICS, 1.0)
    assert await save_rules(checker={"mae_max": 1.0}, weights=weights, backend=backend) == 1
    assert await save_rules(checker={"mae_max": 0.9}, weights=weights, backend=backend) == 2
    assert await config_version("rules", backend=backend) == 2


async def test_saving_rules_refuses_a_negative_weight(backend):
    """A negative weight inverts a metric's meaning.

    The sign flip belongs to `constructs.index_sign` in the frozen data (`docs/07` §4.1), so it
    must not be reachable through a weight a researcher types.
    """
    from twinlab.services.agent_config import AgentConfigError, save_rules

    with pytest.raises(AgentConfigError, match="negative"):
        await save_rules(checker={}, weights={"fairness": -1.0}, backend=backend)
    with pytest.raises(AgentConfigError, match="unknown index weight"):
        await save_rules(checker={}, weights={"not_a_metric": 1.0}, backend=backend)


def test_the_six_index_weights_default_to_one_and_zero_omits():
    """`docs/06` §6: each defaults to 1; **0 omits a metric from the index**."""
    from twinlab.analysis.metrics import compute_index
    from twinlab.services.agent_config import WEIGHT_METRICS

    assert WEIGHT_METRICS == (
        "fairness", "clarity", "happiness", "staying", "pushback", "leaving"
    )
    shifts = dict.fromkeys(WEIGHT_METRICS, 0.6)
    shifts["pushback"] = 0.0
    unweighted = compute_index(shifts)
    omitted = compute_index(shifts, weights={**dict.fromkeys(WEIGHT_METRICS, 1.0),
                                             "pushback": 0.0})
    assert unweighted != omitted, "a weight of 0 must change the index by omitting the metric"


# ==================================================== Run Manager builds a plan


async def test_run_managers_test_button_builds_a_plan_and_starts_nothing(backend):
    """M11, the sharpest bullet: **Run Manager's test builds a plan and starts nothing.**

    `docs/06` §6. Asserted by counting sessions, runs and events across the call — not by reading
    the function and believing it.
    """
    from twinlab.orchestrator.loop import active_runners
    from twinlab.services.agent_config import manager_plan

    before = (
        await backend.count("sessions"),
        await backend.count("runs"),
        await backend.count("run_events"),
        await backend.count("twin_answers"),
    )

    plan = await manager_plan("01000", backend=backend)

    after = (
        await backend.count("sessions"),
        await backend.count("runs"),
        await backend.count("run_events"),
        await backend.count("twin_answers"),
    )
    assert before == after == (0, 0, 0, 0), "building a plan must not start a sweep"
    assert active_runners() == {}, "no runner may be registered by a plan"

    # And it is a real plan: `docs/06` §6 names every row it must carry.
    labels = [r.label for r in plan]
    for required in (
        "Twins in Supabase",
        "Twins kept by the quality test",
        "Wordings",
        "Runs per wording",
        "AI calls for this version",
        "Calls at once",
        "Estimated time",
        "Model",
    ):
        assert required in labels, required


def test_manager_plan_creates_no_session_by_source():
    """The plan function must contain no session creation or task start, on any branch."""
    source = (SRC / "services" / "agent_config.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    plan = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "manager_plan"
    )
    body = ast.dump(plan)
    for banned in ("start_session", "create_task", "SessionRunner", "ask_twins"):
        assert banned not in body, f"manager_plan references {banned}; it must only build a plan"


# ================================================= cross-cutting UI contracts


def test_the_studio_pages_import_only_services_and_models():
    """`ARCHITECTURE.md` §4: `ui/` may not reach `db/`, `agents/`, `orchestrator/`, `analysis/`."""
    banned = ("twinlab.db", "twinlab.agents", "twinlab.orchestrator", "twinlab.analysis")
    for name in ("studio.py", "agent_studio.py"):
        path = SRC / "ui" / "pages" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                module = node.names[0].name
            if module and module.startswith(banned):
                raise AssertionError(f"{name}:{node.lineno} imports {module}")


def test_the_studio_pages_paint_on_load_not_a_repeating_timer():
    """The M10 regression, extended to M11's two pages.

    A repeating timer's output lands on top of whatever the researcher has since changed. Neither
    studio page may start one.
    """
    import re

    for name in ("studio.py", "agent_studio.py"):
        source = (SRC / "ui" / "pages" / name).read_text(encoding="utf-8")
        assert not re.search(r"gr\.Timer\(", source), f"{name} starts a repeating timer"
        assert "load_once(" in source, f"{name} paints nothing on load"


def test_both_studio_screens_build():
    """Both routes assemble inside the one `gr.Blocks`."""
    from twinlab.ui.app import build_ui

    demo = build_ui()
    assert demo.__class__.__name__ == "Blocks"


# ==================================================================== helpers


async def _submission(
    backend,
    submission_id: str,
    *,
    data_type: str = "REAL",
    consent_twin: bool = True,
    eligible: bool = True,
) -> None:
    await backend.insert(
        "survey_submissions",
        [{
            "submission_id": submission_id,
            "data_type": data_type,
            "eligible": eligible,
            "consented": True,
            "consent_twin": consent_twin,
            "attention_passed": True,
            "outcome": "completed",
            "city": "Mumbai",
            "service": "Uber Go",
            "raw_object_path": "p",
            "submitted_at": "2026-09-29T00:00:00Z",
        }],
    )


async def _twin(backend, twin_id: str, *, source: str = "real") -> None:
    await backend.insert(
        "twins",
        [{
            "twin_id": twin_id,
            "source": source,
            "service": "Uber Go",
            "city": "Mumbai",
            "age": 41,
            "consent_twin": True,
            "persona_passage": "A persona passage.",
            "persona_hash": "abc123",
        }],
    )


async def _quality(backend, twin_id: str, *, kept: bool, mae: float) -> None:
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": twin_id,
            "holdout_set": "H3",
            "mae": mae,
            "pct_within_1": 0.9 if kept else 0.4,
            "kept": kept,
            "items_n": 18,
            "detail": {},
            "is_latest": True,
        }],
    )
