"""M10 — UI shell and Twin Lab. Acceptance tests for `docs/11_BUILD_PLAN.md` → M10.

Each test names the acceptance bullet it discharges. Where a bullet states a prohibition, there
is also a test proving the guard rejects a violation: a gate that cannot fail is not a gate
(`docs/11` → Testing rules).

These tests assert the **contract**, never the prose: the tab order, the "of 242" denominator, the
colour rule, the seven-step panel orders, the `after_id` polling discipline. They do not assert
any wording a model produced.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "twinlab"


def _executable_source(path: Path) -> str:
    """Source with comments and docstrings removed. Mirrors `tests/test_m0_scaffold.py`.

    The bans below are scanned by text, and the modules that enforce them name their own subjects
    in prose. Stripping commentary keeps a scan for a banned construct from tripping on a note
    saying it is banned.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            docstrings.add(id(body[0]))
    lines = source.splitlines()
    kept = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        kept.append(line)
    text = "\n".join(kept)
    # Crude but sufficient: drop triple-quoted blocks, which are docstrings in these modules.
    out, in_doc = [], False
    for line in text.splitlines():
        marks = line.count('"""')
        if in_doc:
            if marks:
                in_doc = False
            continue
        if marks == 1:
            in_doc = True
            continue
        if marks >= 2:
            continue
        out.append(line)
    return "\n".join(out)


def _ui_files() -> list[Path]:
    return sorted((SRC / "ui").rglob("*.py"))


# ===================================================================== shell


def test_eight_routes_in_order():
    """M10 shell: eight routes, in `docs/06` §0's mandatory order."""
    from twinlab.ui.theme import ROUTES

    assert [r[1] for r in ROUTES] == [
        "/",
        "/survey",
        "/lab",
        "/generator",
        "/studio",
        "/agents",
        "/statistics",
        "/research",
    ]
    assert [r[0] for r in ROUTES][:3] == ["Main menu", "Driver survey", "Twin Lab"]


def test_lab_sub_tabs_in_order():
    """M10 shell: Twin Lab's eight sub-tabs, in order, and `render_lab` refuses any other."""
    from twinlab.services.menu import LAB_TABS
    from twinlab.ui.pages.lab import _TABS

    assert LAB_TABS == (
        "Agents",
        "Dial board",
        "Twins",
        "Validation",
        "Validity tests",
        "Fieldwork",
        "Results",
        "Settings",
    )
    assert tuple(name for name, _ in _TABS) == LAB_TABS


def test_tab_order_guard_rejects_a_reordering(monkeypatch):
    """The order check is a real gate: reordering the tabs must fail loudly."""
    import twinlab.ui.pages.lab as lab

    scrambled = tuple(reversed(lab._TABS))
    monkeypatch.setattr(lab, "_TABS", scrambled)
    with pytest.raises(AssertionError, match="mandatory order"):
        lab.render_lab()


def test_prefers_reduced_motion_is_honoured():
    """M10 shell: `prefers-reduced-motion` is honoured in the global CSS (`docs/05` §3)."""
    from twinlab.ui.theme import TWINLAB_CSS

    assert "@media (prefers-reduced-motion: reduce)" in TWINLAB_CSS
    assert "animation-duration:.01ms !important" in TWINLAB_CSS


def test_no_colour_only_status_anywhere():
    """M10 shell: every pill and dot carries a text label (`docs/05` §6).

    Asserted at the constructor rather than over rendered markup, because that is the only place
    a colour-without-text can be introduced: both primitives raise on empty text.
    """
    from twinlab.ui.components import pill, status_dot

    assert "Kept (0.56)" in status_dot("complete", "Kept (0.56)")
    assert "PASS" in pill("PASS", "green")

    with pytest.raises(ValueError, match="colour alone"):
        pill("", "green")
    with pytest.raises(ValueError, match="colour only"):
        status_dot("complete", "")


def test_every_verdict_pill_shows_its_word():
    """`INCONCLUSIVE` is mandatory and grey, and the word is always visible (I15)."""
    from twinlab.ui.components import verdict_pill

    for verdict in ("PASS", "FAIL", "CHECK", "INCONCLUSIVE"):
        assert verdict in verdict_pill(verdict)
    assert "tl-pill-grey" in verdict_pill("INCONCLUSIVE")


def test_google_sheet_is_removed_from_every_screen():
    """`docs/06` §0: no route, no card, no link and no user-facing text naming a sheet."""
    from twinlab.services import menu

    text = " ".join(
        [g.title + " " + " ".join(c.title + c.description for c in g.cards)
         for g in menu.WORKFLOW_GROUPS]
        + [c.title + c.description for c in menu.DIRECT_CARDS]
    ).lower()
    assert "sheet" not in text
    for path in _ui_files():
        assert "google sheet" not in _executable_source(path).lower(), path


# ================================================================= main menu


async def test_versions_tested_reads_of_242(backend):
    """M10 main menu: "Versions tested" reads **of 242** — `00000` is a control, not a cell."""
    from twinlab.services.status import TESTABLE_CODES, where_things_stand

    assert TESTABLE_CODES == 242
    rows = {r.label: r.value for r in await where_things_stand(backend)}
    assert rows["Versions tested"] == "0 of 242"


async def test_counters_are_live_counts(backend):
    """M10 main menu: counters are live database counts, not cached figures."""
    from twinlab.services.status import where_things_stand

    before = {r.label: r.value for r in await where_things_stand(backend)}
    assert before["Twins built"] == "0"

    await backend.insert(
        "twins", [{"twin_id": "T1", "source": "real", "consent_twin": True}]
    )
    after = {r.label: r.value for r in await where_things_stand(backend)}
    assert after["Twins built"] == "1"


async def test_control_cell_is_never_counted_as_a_tested_version(backend):
    """A completed `00000` run must not raise the tested count: it is the comparison."""
    from twinlab.services.status import tested_codes

    await _completed_run(backend, "00000", index=0.0)
    assert await tested_codes(backend) == {}

    await _completed_run(backend, "01000", index=0.143)
    assert set(await tested_codes(backend)) == {"01000"}


def test_main_menu_has_seven_groups_and_seven_direct_cards():
    """`docs/06` §1.1 and §1.2. Content and ordering are mandatory."""
    from twinlab.services.menu import DIRECT_CARDS, WORKFLOW_GROUPS

    assert [g.title for g in WORKFLOW_GROUPS] == [
        "Collect answers",
        "Build and test the twins",
        "Check the twins can be trusted",
        "Explore the 243 versions",
        "Analyse and export",
        "Write the paper",
        "Set up and manage",
    ]
    # One card per route except Main menu.
    assert len(DIRECT_CARDS) == 7
    assert {c.route for c in DIRECT_CARDS} == {
        "/survey",
        "/lab",
        "/generator",
        "/studio",
        "/agents",
        "/statistics",
        "/research",
    }
    # Every card carries title, one-line description and destination (`docs/06` §1.1).
    for group in WORKFLOW_GROUPS:
        for card in group.cards:
            assert card.title and card.description and card.route


# ==================================================================== agents


def test_three_workflow_buttons_in_the_specified_order():
    """M10 agents: the three workflow buttons, in `docs/06` §3.1's exact order."""
    from twinlab.services.runs import WORKFLOW_BUTTONS

    assert [b[1] for b in WORKFLOW_BUTTONS] == [
        "Run twin quality test",
        "Let the agents choose 6 versions",
        "Test all 243 versions",
    ]
    assert [b[2] for b in WORKFLOW_BUTTONS] == ["primary", "primary", "secondary"]


async def test_every_long_action_has_a_budget_before_it_starts():
    """M10 agents / `docs/06` §9: a budget is shown on the confirm step, before anything runs."""
    from twinlab.services.runs import (
        ask_budget_view,
        quality_budget_view,
        sweep_budget_view,
    )

    for view in (
        await ask_budget_view("01000"),
        await sweep_budget_view(iterations=6),
        await sweep_budget_view(iterations=243),
        await quality_budget_view(twins=10, repeats=3),
    ):
        assert view.calls > 0
        assert view.est_hours_text
        # Never an invented cost: the free credit allowance is unpublished (docs/10 §3.3).
        assert view.est_credits_text == "not known"


async def test_log_polling_is_incremental_and_never_refetches(backend):
    """M10 agents: the log polls with `after_id`, never re-fetching the stream (`docs/04` §7.3)."""
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.runs import events_since

    session_id = await _session(backend)
    log = EventLog(session_id, backend)
    first = await log.emit(stage="control", label="session one", agent="manager")
    await log.emit(stage="lookup", label="01000", agent="manager", parent_event_id=first)

    page = await events_since(session_id, 0, backend=backend)
    assert [e.event_id for e in page] == sorted(e.event_id for e in page)
    assert len(page) == 2
    # The child nests under the parent.
    assert page[1].depth == page[0].depth + 1

    cursor = max(e.event_id for e in page)
    assert await events_since(session_id, cursor, backend=backend) == []

    await log.emit(stage="ask", label="asking 20 twins", agent="twin", parent_event_id=first)
    tail = await events_since(session_id, cursor, backend=backend)
    assert len(tail) == 1, "a poll must return only rows after the cursor"
    assert tail[0].message == "asking 20 twins"


async def test_a_parent_label_rewrites_in_place_on_one_row(backend):
    """M10 agents: a parent label rewrites in place through twin ids on a **single** row."""
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.runs import events_since

    session_id = await _session(backend)
    log = EventLog(session_id, backend)
    parent = await log.emit(stage="ask", label="asking twin 1 of 20", agent="twin")
    await log.set_label(parent, "asking twin 7 of 20")

    rows = await events_since(session_id, 0, backend=backend)
    assert len(rows) == 1, "progress must be one row, not one row per twin"
    assert rows[0].message == "asking twin 7 of 20"


async def test_agent_cards_are_the_five_in_order(backend):
    """`docs/06` §3.1: five cards, and the Manager reports that nothing calls it yet."""
    from twinlab.services.menu import agent_cards

    cards = await agent_cards(backend)
    assert [c.name for c in cards] == [
        "Run Manager",
        "Policy Designer",
        "Twin Interviewer",
        "Quality Checker",
        "Results Analyst",
    ]
    assert cards[0].enabled is False


# ================================================================ dial board


def test_changing_a_dial_does_no_network_work():
    """M10 dial board: code, score and "what the twins are told" recomputed with **no** network.

    `docs/05` §8.4 rule 6. Enforced by installing a backend that raises on any call: if the dial
    handler ever grows a database read, this test fails rather than merely getting slower.
    """
    from twinlab.db.client import set_backend
    from twinlab.services.dials import dial_board

    class Exploding:
        def __getattr__(self, name):
            raise AssertionError(
                f"the dial board reached the database ({name}); changing a dial is a pure "
                "lookup over frozen reference data (docs/05 §8.4 rule 6)"
            )

    set_backend(Exploding())
    try:
        board = dial_board({"L1": 0, "L2": 1, "L3": 0, "L4": 0, "L5": 0})
    finally:
        set_backend(None)

    assert board.version_code == "01000"
    assert board.fairwork_text == "Fairwork score 1 of 10"
    told = {lever.lever: lever for lever in board.told}
    assert told["L2"].heading == "Conditions step 1"
    assert told["L2"].bullets, "the Conditions lever at dial 1 carries commitments"
    assert told["L1"].heading == "Pay — no change"
    assert told["L1"].bullets == []


def test_dial_board_is_a_pure_lookup_of_the_worked_example():
    """`01000` selects exactly the Conditions threshold-2.1 commitments (I1, `docs/03` §4.2)."""
    from twinlab.services.dials import dial_board

    board = dial_board("01000")
    ids = [b.gap_id for lever in board.told for b in lever.bullets]
    assert ids == ["2.1.a", "2.1.b", "2.1.c"]
    # Threshold 2.2 material must not be selected at dial 1 — that is the whole of I3's premise.
    assert not any(i.startswith("2.2") for i in ids)


def test_00000_warns_and_blocks_ask_the_twins():
    """M10 dial board: `00000` shows the warning strip and blocks *Ask the twins*."""
    from twinlab.services.dials import CONTROL_WARNING, dial_board

    board = dial_board("00000")
    assert board.is_control is True
    assert board.warning == CONTROL_WARNING
    assert board.warning == "Turn at least one dial above 0. 00000 is a control cell."

    assert dial_board("00001").is_control is False
    assert dial_board("00001").warning is None


async def test_ask_the_twins_refuses_the_control_cell(backend):
    """The block is enforced in the service too, not only by a disabled button (`docs/03` §6.1)."""
    from twinlab.orchestrator.loop import ControlCellError
    from twinlab.services.runs import ask_twins

    with pytest.raises(ControlCellError, match="control cell"):
        await ask_twins("00000", backend=backend)


async def test_a_cached_code_reports_cached_and_offers_rerun(backend):
    """M10 dial board: a cached code shows the amber badge and a Rerun? button."""
    from twinlab.services.runs import cached_run

    assert await cached_run("01000", backend=backend) is None
    await _completed_run(backend, "01000", index=0.143)
    hit = await cached_run("01000", backend=backend)
    assert hit is not None and hit["version_code"] == "01000"


async def test_a_rerun_inherits_the_original_panel(backend, monkeypatch):
    """M10 dial board: a rerun creates a visible session and **inherits the panel** (I14)."""
    import twinlab.services.runs as runs_service
    from twinlab.db.repositories import SessionRepo

    started: list[str] = []

    async def _no_start(session_id, **kwargs):
        started.append(session_id)

    monkeypatch.setattr(runs_service, "start_session", _no_start)

    # `ask_twins` now pre-flights eligibility before it writes a session row
    # (`ARCHITECTURE_UPDATE.md` §3.5), so a rerun needs a drawable panel to get as far as the
    # inheritance this test is about. 20 is `settings.panel_size`, which the `new_panel=True`
    # leg below draws against; the inherited leg needs only 17.
    await _eligible_twins(backend, 20)
    sessions = SessionRepo(backend)
    origin = await sessions.create(
        name="origin", kind="ask", start_code="01000", panel_size=17, panel_seed=4242
    )

    again = await runs_service.rerun(
        "01000", original_session_id=origin.session_id, backend=backend
    )
    assert again.panel_size == 17
    assert again.panel_seed == 4242, "a rerun with a different panel is not a rerun (I14)"
    assert again.name == "Rerun 01000"

    # And an explicit new panel is a deliberate choice, not the default.
    fresh = await runs_service.rerun(
        "01000", original_session_id=origin.session_id, new_panel=True, backend=backend
    )
    assert fresh.panel_seed != 4242


def test_the_scenario_paragraph_and_the_bullet_summary_are_different_artefacts():
    """`docs/03` §4.3: a twin never sees bullets, and the bullet summary never reaches a model."""
    from twinlab.services.dials import what_twins_are_told
    from twinlab.variant.lookup import lookup, told_summary

    told = what_twins_are_told("01000")
    spec = lookup("01000")
    summary = told_summary(spec)
    assert [b.gap_id for lever in told for b in lever.bullets] == [
        line.split(" — ", 1)[0] for lines in summary.values() for line in lines
    ]


# ===================================================================== twins


def test_twin_panel_order_is_exactly_the_specified_seven_steps():
    """M10 twins: the panel order is `docs/06` §3.3's, scenario block **before** the tables."""
    from twinlab.models.view import TwinPanel

    order = list(TwinPanel.model_fields)
    assert order.index("identity") < order.index("background") < order.index("quality_line")
    assert order.index("quality_line") < order.index("persona_text")
    assert order.index("persona_text") < order.index("compare_codes")
    # The reader must see what the twin was told BEFORE reading what it said.
    assert order.index("compare_codes") < order.index("scenario_text") < order.index("blocks")


async def test_an_untested_version_shows_not_tested(backend):
    """M10 twins: an untested version shows `Not tested`, never a fabricated number (I17)."""
    from twinlab.services.lab import twin_panel
    from twinlab.ui.components import answer_compare

    await _twin(backend, "T1")
    panel = await twin_panel("T1", version_code="01000", backend=backend)
    assert panel.not_tested is True
    assert all(
        row.variant is None for block in panel.blocks for row in block.rows
    )
    assert "Not tested" in answer_compare(panel)


async def test_holdout_items_are_marked_hidden(backend):
    """A twin never saw Parts 15-17 (I6); the comparison marks them rather than dropping them."""
    from twinlab.services.lab import twin_panel

    await _twin(backend, "T1")
    panel = await twin_panel("T1", backend=backend)
    assert panel.blocks, "the comparison has one block per construct, in battery order"
    for block in panel.blocks:
        for row in block.rows:
            assert row.hidden is False, "battery items are not holdout items"


def test_num_never_renders_an_absent_value_as_zero():
    """I17: an absent measurement must not be indistinguishable from a measured null."""
    from twinlab.ui.components import num

    assert "Not tested" in num(None)
    assert "0.00" not in num(None)
    assert num(0.0) == "+0.00"


# ================================================================ validation


async def test_validation_has_an_arm_seen_column(backend):
    """M10 validation: the *Arm seen* column is present — it is how an arm mismatch is caught."""
    from twinlab.models.view import ValidationRow
    from twinlab.services.lab import validation_view

    assert "arm_seen" in ValidationRow.model_fields
    assert ValidationRow.model_fields["arm_seen"].is_required(), (
        "arm_seen is required: a blank hides exactly the bug the column exists to catch "
        "(docs/01 §5)"
    )

    await _twin(backend, "T1")
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "T1", "holdout_set": "H2", "mae": 0.5, "pct_within_1": 0.9,
            "kept": None, "items_n": 16, "arm": "MGT1", "detail": {},
            "is_latest": True,
        }],
    )
    _, rows = await validation_view(backend)
    assert [r.arm_seen for r in rows] == ["MGT1"]


async def test_synthetic_warning_appears_whenever_the_set_includes_synthetic_twins(backend):
    """M10 validation: the warning appears whenever the checked set includes synthetic twins."""
    from twinlab.services.lab import SYNTHETIC_WARNING, validation_view

    await _twin(backend, "T1", source="real")
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "T1", "holdout_set": "H2", "mae": 0.5, "pct_within_1": 0.9,
            "kept": None, "items_n": 16, "arm": "BASE", "detail": {},
            "is_latest": True,
        }],
    )
    summary, _ = await validation_view(backend)
    assert summary.synthetic_present is False

    await _twin(backend, "T2", source="synthetic")
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": "T2", "holdout_set": "H2", "mae": 0.5, "pct_within_1": 0.9,
            "kept": None, "items_n": 16, "arm": "BASE", "detail": {},
            "is_latest": True,
        }],
    )
    summary, _ = await validation_view(backend)
    assert summary.synthetic_present is True
    assert "tests the machinery" in SYNTHETIC_WARNING


def test_validation_uses_the_canonical_part_numbers():
    """`docs/06` §3.4: parts **16 and 17**, and Part 9b does not exist in 2.0."""
    source = _executable_source(SRC / "ui" / "pages" / "lab.py")
    assert "Part 16 (H2)" in source
    assert "Part 17 (H3)" in source
    assert "Part 9b" not in source
    assert "Part 10b" not in source


# =========================================================== validity tests


def test_eight_validity_test_cards_in_order():
    """`docs/06` §3.5: the eight tests, numbered and in order."""
    from twinlab.services.lab import VALIDITY_TESTS
    from twinlab.validity.tests import CALLS_PER_TWIN

    assert [t.number for t in VALIDITY_TESTS] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [t.name for t in VALIDITY_TESTS] == [
        "Wrong person",
        "Placebo change",
        "Beating simple guesses",
        "Impossible version",
        "Order and wording swap",
        "Leave out the fairness items",
        "A second AI model",
        "Temperature sweep",
    ]
    # **Tests 1 AND 3 are the purely statistical ones.** `docs/08` §4's cost table gives both
    # "New LLM calls: none", and §4 test 1 says outright that it "needs no new model calls — it
    # re-scores stored vectors — so it should be run early and often".
    #
    # This assertion previously read `count(False) == 1`, which encoded the M12 handoff's own
    # flagged defect: Test 1 was marked `needs_live_model=True`, so the screen badged the single
    # most important of the eight as needing a live model. M13 flipped the flag and proved it on
    # the call counter (`tests/test_m13_validity.py`), so the badge is now tied to the call table
    # rather than to a count that could drift from it in either direction.
    assert [t.needs_live_model for t in VALIDITY_TESTS].count(False) == 2
    assert {t.number for t in VALIDITY_TESTS if not t.needs_live_model} == {1, 3}
    assert all(
        t.needs_live_model == (CALLS_PER_TWIN[t.number] > 0) for t in VALIDITY_TESTS
    )


async def test_a_pass_on_zero_twins_can_never_be_rendered(backend):
    """I15: a validity test on zero twins is `INCONCLUSIVE`, never `PASS`.

    The DDL makes such a row unstorable. This asserts the renderer refuses it too, so a database
    reached by another path cannot put a pass on nobody on screen.
    """
    from twinlab.db.client import DbError
    from twinlab.services.lab import validity_results

    with pytest.raises(DbError, match="validity_zero_n"):
        await backend.insert(
            "validity_results",
            [{
                "test_id": "wrong_person", "twins_n": 0, "mode": "live", "provider": "ollama",
                "model": "gpt-oss:120b", "statistics": {}, "verdict": "PASS",
                "headline": "twins are about their own driver", "detail": "",
                "config_version": 1,
            }],
        )

    # And if one arrives regardless, rendering it raises rather than showing a pass.
    backend.tables.setdefault("validity_results", []).append(
        {
            "validity_run_id": "x", "test_id": "wrong_person", "twins_n": 0, "mode": "live",
            "provider": "ollama", "model": "m", "statistics": {}, "verdict": "PASS",
            "headline": "h", "detail": "", "config_version": 1, "created_at": "2026-09-29",
        }
    )
    with pytest.raises(ValueError, match="ran on nobody"):
        await validity_results(backend)


# ================================================================= fieldwork


async def test_real_fieldwork_metrics_never_count_synthetic_rows(backend):
    """`docs/06` §3.6: real fieldwork metrics never count synthetic rows."""
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.lab import fieldwork_counts

    common = {
        "eligible": True, "consented": True, "consent_twin": True,
        "attention_passed": True, "outcome": "completed",
        "raw_object_path": "p", "submitted_at": "2026-09-29T00:00:00Z",
    }
    await backend.insert(
        "survey_submissions",
        [
            {"submission_id": "R1", "data_type": "REAL", "city": "Mumbai",
             "service": "Go", **common},
            {"submission_id": "S1", "data_type": SYNTHETIC_DATA_TYPE, "city": "Mumbai",
             "service": "Go", **common},
        ],
    )
    data = await fieldwork_counts(backend)
    assert data["real_total"] == 1
    assert data["synthetic_total"] == 1
    assert data["by_stratum"] == {("Mumbai", "Go"): 1}


# =================================================================== results


async def test_results_panel_order_is_exactly_the_specified_seven_steps(backend):
    """M10 results: the panel order is `docs/06` §3.7's — the Analyst's bundle, in that order."""
    from twinlab.models.view import ResultsPanel

    order = list(ResultsPanel.model_fields)
    assert order.index("board") < order.index("scenario_text") < order.index("bars")
    assert order.index("bars") < order.index("baselines") < order.index("interactions")
    assert order.index("interactions") < order.index("analysis") < order.index("metadata")


async def test_grid_click_opens_the_panel_and_the_table_carries_the_same_data(backend):
    """M10 results: every cell is clickable, and the table is the grid's linear equivalent."""
    from twinlab.services.metrics_view import build_grid, build_tested_table
    from twinlab.services.results import results_panel, tested_rows
    from twinlab.services.status import tested_codes
    from twinlab.ui.components import grid_243

    await _completed_run(backend, "01000", index=0.143)
    await _completed_run(backend, "00000", index=0.004)

    cells = build_grid(await tested_codes(backend))
    assert len(cells) == 243
    markup = grid_243(cells)
    assert markup.count("data-code=") == 243, "never ship a grid without click handling"

    rows = build_tested_table(await tested_rows(backend))
    assert [r.version_code for r in rows] == ["01000"], "controls are not tested versions"
    assert rows[0].index_value == 0.143

    panel = await results_panel("01000", backend=backend)
    assert panel.board.version_code == "01000"
    assert panel.bars.index_text == "0.143"


async def test_the_control_and_best_cells_carry_their_outlines_in_text(backend):
    """`docs/05` §7 rule 3 and §6: both outlines are stated in the accessible name too."""
    from twinlab.services.metrics_view import build_grid

    cells = {
        c.version_code: c
        for c in build_grid({"00000": 0.004, "01000": 0.143, "22222": 1.2})
    }
    assert cells["00000"].outline == "control"
    assert "Uber today" in cells["00000"].accessible_name
    assert cells["22222"].outline == "best"
    assert "best so far" in cells["22222"].accessible_name
    assert "not tested" in cells["21111"].accessible_name


def test_a_missing_interaction_leg_names_the_code_to_run():
    """M10 results: a missing leg names the code to run, never an estimate, never a blank (I17)."""
    from twinlab.services.metrics_view import build_interaction_rows

    rows = build_interaction_rows(
        "01000", {"01000": {"fairness": 0.1}}, candidates=["00010"]
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.computable is False
    assert row.missing_codes == ["00010", "01010"]
    assert "Run 00010, 01010" in row.text
    assert "this is not estimated" in row.text
    # Nothing in the row can express an approximation.
    assert "approx" not in row.text.lower()


def test_the_colour_rule_is_good_for_the_driver_not_sign():
    """`docs/05` §4.5 and §7 rule 2. Getting this backwards inverts the headline finding.

    `leaving −0.59` extends left and is **green**; `pushback +1.20` extends right and is **red**.
    """
    from twinlab.services.metrics_view import build_metric_bars

    bars = build_metric_bars(
        {
            "fairness": 0.30, "clarity": 0.07, "happiness": 0.20,
            "staying": 0.10, "pushback": 1.20, "leaving": -0.59,
        },
        index_value=0.143,
        twins_n=20,
        version_code="01000",
    )
    rows = {r.metric: r for r in bars.rows}
    assert rows["pushback"].value > 0 and rows["pushback"].good_for_driver is False
    assert rows["leaving"].value < 0 and rows["leaving"].good_for_driver is True
    assert rows["fairness"].good_for_driver is True
    # Every row carries its number: the bar is redundant encoding, never the only encoding.
    assert all(r.value_text for r in bars.rows)


def test_a_cell_with_no_twins_is_never_rendered_as_an_index_of_zero():
    """I15: `twins_n = 0` is a failed run, not a result with an index of 0.000."""
    from twinlab.services.metrics_view import build_metric_bars

    bars = build_metric_bars({}, index_value=0.0, twins_n=0, version_code="01000")
    assert bars.index_text == "Not tested"
    assert bars.index_value is None


def test_the_demand_floor_is_reported_when_a_cell_does_not_clear_it():
    """`docs/07` §6: a cell inside the floor is not interpretable and the UI says so."""
    from twinlab.services.metrics_view import build_metric_bars

    bars = build_metric_bars(
        {"fairness": 0.02, "clarity": 0.01, "happiness": 0.0,
         "staying": 0.0, "pushback": 0.0, "leaving": 0.0},
        index_value=0.005,
        twins_n=20,
        version_code="01000",
        floor=0.05,
    )
    assert bars.floor_note is not None
    assert "not interpretable" in bars.floor_note


# ================================================================== settings


async def test_saving_settings_writes_a_new_app_config_version(backend):
    """M10 settings: saving writes a **new** `app_config` version."""
    from twinlab.services.lab import config_version, save_settings

    assert await save_settings("twin", {"temperature": 0.7}, backend=backend) == 1
    assert await save_settings("twin", {"temperature": 0.5}, backend=backend) == 2
    assert await config_version("twin", backend=backend) == 2


def test_there_is_no_clear_runs_button():
    """M10 settings and I9: evidence is never deletable from the UI."""
    from twinlab.services.lab import CLEAR_RUNS_NOTE

    assert "append-only" in CLEAR_RUNS_NOTE
    assert "not a button" in CLEAR_RUNS_NOTE

    for path in _ui_files():
        source = _executable_source(path)
        for banned in ("Clear runs", "clear_runs", "Load demo twins"):
            assert banned not in source, f"{path} offers {banned!r}; runs are append-only (I9)"

    # And no service the UI can reach deletes a run.
    for path in sorted((SRC / "services").glob("*.py")):
        source = _executable_source(path)
        assert 'delete("runs"' not in source, path
        assert 'delete("run_events"' not in source, path
        assert 'delete("twin_answers"' not in source, path


# ================================================= cross-cutting UI contracts


def test_what_twins_are_told_has_exactly_one_implementation():
    """M10: `what_twins_are_told` has one implementation — asserted by import graph.

    `docs/05` §4.4: one component, one source, used by the Dial board, the Results side panel and
    the Twins side panel. Two implementations would drift, and a drift means the researcher reads
    a different treatment from the one the twins were given.
    """
    from twinlab.services.dials import what_twins_are_told as service_impl
    from twinlab.services.lab import what_twins_are_told as lab_reexport
    from twinlab.ui.components import what_twins_are_told as ui_renderer

    # The data has exactly one producer, re-exported rather than reimplemented.
    assert lab_reexport is service_impl
    assert inspect.getsourcefile(service_impl).endswith("dials.py")

    # Only one module in the whole tree defines it.
    definitions = [
        path
        for path in SRC.rglob("*.py")
        if "def what_twins_are_told(" in path.read_text(encoding="utf-8")
    ]
    assert sorted(p.name for p in definitions) == ["dials.py", "domain.py"], definitions

    # And the UI one is a renderer over the service's output, not a second source: it takes the
    # service's list and reads nothing else.
    signature = inspect.signature(ui_renderer)
    assert list(signature.parameters) == ["told"]


def test_all_three_screens_show_identical_told_text():
    """The Dial board, the Results panel and the Twins panel cannot disagree for one code."""
    from twinlab.services.dials import dial_board, what_twins_are_told
    from twinlab.ui.components import dial_board_summary
    from twinlab.ui.components import what_twins_are_told as render

    board = dial_board("01000")
    from_board = render(board.told)
    from_service = render(what_twins_are_told("01000"))
    assert from_board == from_service
    assert from_service in dial_board_summary(board)


def test_no_metric_is_computed_in_ui():
    """M10: no arithmetic on shift values anywhere in `ui/` (`docs/05` §8.4 rule 5).

    Scans the AST for arithmetic whose operands are read off a metric-bearing attribute. The UI
    may format a number it was given; it may never derive one.
    """
    metric_attrs = {"value", "index_value", "shifts", "baselines", "extra", "mae"}
    offenders: list[str] = []

    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp):
                continue
            if not isinstance(node.op, ast.Add | ast.Sub | ast.Mult | ast.Div):
                continue
            for side in (node.left, node.right):
                if isinstance(side, ast.Attribute) and side.attr in metric_attrs:
                    offenders.append(f"{path.name}:{node.lineno} uses .{side.attr}")
                if (
                    isinstance(side, ast.Subscript)
                    and isinstance(side.value, ast.Attribute)
                    and side.value.attr in metric_attrs
                ):
                    offenders.append(f"{path.name}:{node.lineno} indexes .{side.value.attr}")

    assert not offenders, "ui/ computed a metric: " + "; ".join(offenders)


def test_ui_imports_only_services_and_models():
    """`ARCHITECTURE.md` §4: `ui/` may not import `db/`, `agents/` or raw SQL."""
    banned = ("twinlab.db", "twinlab.agents", "twinlab.orchestrator", "twinlab.analysis")
    for path in _ui_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                module = node.names[0].name
            if module and module.startswith(banned):
                raise AssertionError(f"{path.name}:{node.lineno} imports {module}")


def test_no_llm_call_in_a_handler_synchronous_path():
    """`CLAUDE.md` rule 12: no agent call anywhere in `ui/`, on any path."""
    for path in _ui_files():
        source = _executable_source(path)
        for banned in ("build_agent", "run_answer_ladder", "pydantic_ai", "ask_twin("):
            assert banned not in source, f"{path.name} reaches a model directly"


def test_the_grid_is_click_wired():
    """`docs/05` §8.3: **never ship a grid without click handling.**

    Without it the grid is decoration, and the click is how a researcher reaches the scenario
    text. `gr.HTML` emits no events, so the cell click is bridged into the version-code box; this
    asserts both halves of that bridge exist and agree on the element id.
    """
    from twinlab.services.metrics_view import build_grid
    from twinlab.ui.components import grid_243
    from twinlab.ui.pages.lab import _GRID_CLICK_JS

    markup = grid_243(build_grid({"01000": 0.143}))
    assert markup.count("data-code=") == 243
    assert 'class="tl-cell' in markup

    # The bridge targets the same class the grid emits and the same id the textbox carries.
    assert ".tl-cell" in _GRID_CLICK_JS
    assert "tl-grid-pick" in _GRID_CLICK_JS
    assert 'elem_id="tl-grid-pick"' in _executable_source(SRC / "ui" / "pages" / "lab.py")
    # Assigning `.value` alone is ignored by Gradio's binding; the native setter is required.
    assert "getOwnPropertyDescriptor" in _GRID_CLICK_JS
    assert 'new Event("input"' in _GRID_CLICK_JS


def test_every_grid_cell_has_an_accessible_name():
    """`docs/05` §6: 243 cells may not encode anything by colour or position alone."""
    from twinlab.services.metrics_view import build_grid
    from twinlab.ui.components import grid_243

    cells = build_grid({"01000": 0.143})
    assert all(c.accessible_name for c in cells)
    markup = grid_243(cells)
    assert markup.count("aria-label=") == 243


def test_initial_paints_use_load_not_a_repeating_timer():
    """A first paint must not be a repeating timer. Regression, found by running the app.

    The Dial board originally painted its initial state from a 0.2 s `gr.Timer`. The timer kept
    firing and its output landed on top of the change handler's, so **moving a dial did nothing**
    — the code stayed `00000` however the radios were set. Seven such timers also produced about
    28 requests a second.

    Only two repeating timers are legitimate, and both are specified: the Agents log poll and the
    Main menu's live counters (`docs/06` §1.3, §3.1).
    """
    import re

    allowed = {
        ("lab.py", "3.0"),        # docs/06 §3.1: the log is polled
        ("main_menu.py", "10.0"),  # docs/06 §1.3: the counters are live
    }
    # Scanned over executable source, not raw text: a module that DOCUMENTS this prohibition
    # names `gr.Timer(0.2)` in its docstring, and a ban scan tripped by a note saying the thing
    # is banned is the failure mode HANDOFF §0.5 records for `@spaces.GPU` and "Google Sheet".
    for path in _ui_files():
        for interval in re.findall(r"gr\.Timer\(\s*([0-9.]+)", _executable_source(path)):
            assert (path.name, interval) in allowed, (
                f"{path.name} starts a repeating gr.Timer({interval}). A first paint belongs on "
                "load_once; a repeating timer overwrites whatever the researcher changed."
            )


def test_load_once_defers_to_the_blocks_load_event():
    """`load_once` queues for `demo.load` and `build_ui` drains the queue to empty."""
    from twinlab.ui.app import build_ui
    from twinlab.ui.components.shell import _PENDING_LOADS

    _PENDING_LOADS.clear()
    build_ui()
    assert _PENDING_LOADS == [], "every queued initial paint must be attached to a Blocks load"


def test_the_dial_handler_reads_its_inputs_not_a_fixed_default():
    """The dial handler must compute from the radios, never from a hard-coded zero vector.

    The bug this guards was exactly a hard-coded ``_on_dial(0, 0, 0, 0, 0)`` initial paint.
    """
    import twinlab.ui.pages.lab as lab

    source = _executable_source(SRC / "ui" / "pages" / "lab.py")
    assert "_on_dial(0, 0, 0, 0, 0)" not in source
    assert "load_once(_on_dial, inputs=inputs" in source
    assert hasattr(lab, "_dial_board_tab")


def test_the_whole_app_builds():
    """The shell assembles: one `gr.Blocks`, eight routes, no logic in the entrypoints."""
    from twinlab.ui.app import build_ui

    demo = build_ui()
    assert demo.__class__.__name__ == "Blocks"


# ==================================================================== helpers


async def _session(backend, **kwargs) -> str:
    from twinlab.db.repositories import SessionRepo

    session = await SessionRepo(backend).create(name="test", **kwargs)
    return session.session_id


async def _completed_run(backend, code: str, *, index: float, twins: int = 20) -> str:
    """A completed run, through `RunRepo.complete`.

    Deliberately not a raw insert: completion flips `is_latest_for_version` in the same
    transaction (I9), and that pointer is what the Dial board's cache check reads. A fixture that
    wrote the row directly would test a state the application cannot produce.
    """
    from twinlab.db.repositories import RunRepo

    session_id = await _session(backend)
    runs = RunRepo(backend)
    run = await runs.get_or_create(session_id, code)
    await runs.complete(
        run.run_id,
        twins_n=twins,
        index_value=index,
        metrics={
            "shifts": {
                "fairness": 0.3, "clarity": 0.07, "happiness": 0.2,
                "staying": 0.1, "pushback": -0.1, "leaving": -0.59,
            },
            "baselines": {
                "fairness": 4.0, "clarity": 3.0, "happiness": 4.0,
                "staying": 3.0, "pushback": 4.0, "leaving": 4.0,
            },
        },
    )
    return run.run_id


async def _twin(backend, twin_id: str, *, source: str = "real") -> None:
    await backend.insert(
        "twins",
        [{
            "twin_id": twin_id,
            "source": source,
            "service": "Uber Go",
            "city": "Mumbai",
            "age": 41,
            "gender": "Man",
            "tenure_months": 38,
            "hours_per_week": 72,
            "consent_twin": True,
            "persona_passage": "A persona passage.",
            "persona_hash": "abc123",
        }],
    )


async def _eligible_twins(backend, n: int, *, source: str = "real") -> list[str]:
    """``n`` twins that `eligible_candidates` would accept: right source, H3 verdict `kept`.

    Both filters, because the pre-flight of `ARCHITECTURE_UPDATE.md` §3.5 counts them separately
    and a test that satisfied only one would pass against the wrong message.
    """
    ids = [f"EL{i:03d}" for i in range(n)]
    for twin_id in ids:
        await _twin(backend, twin_id, source=source)
    await backend.insert(
        "twin_quality_runs",
        [
            {
                "twin_id": twin_id, "holdout_set": "H3", "mae": 0.5, "pct_within_1": 0.9,
                "kept": True, "items_n": 18, "detail": {}, "is_latest": True,
            }
            for twin_id in ids
        ],
    )
    return ids


# ---------------------------------------------------------------- the live log


async def test_an_event_row_carries_its_timestamp(backend):
    """`run_events` timestamps the column `ts`, not `created_at`.

    This read `created_at`, which the table does not have — `InMemoryBackend` excludes it from
    `HAS_CREATED_AT` for exactly that reason — so `EventRow.when` was the empty string for every
    row and `log_tree` rendered a blank timestamp beside every line of every run.
    """
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.runs import events_since

    await EventLog("s1", backend).emit(stage="control", label="started")
    rows = await events_since("s1", 0, backend=backend)

    assert len(rows) == 1
    assert rows[0].when, "the event carries no timestamp"


async def test_polling_does_not_re_read_the_whole_stream(backend):
    """`docs/04` §7.3 — the stream is never re-fetched whole.

    The parent map was built with an unfiltered `select` over the session's events, so every
    three-second tick read the entire history back: at sweep scale the tens of thousands of rows
    per tick the incremental cursor exists to avoid. Only missing **ancestors** are fetched now.
    """
    from twinlab.orchestrator.events import EventLog
    from twinlab.services.runs import events_since

    log = EventLog("s2", backend)
    parent = await log.emit(stage="control", label="session")
    for i in range(50):
        await log.emit(stage="ask", label=f"twin {i}", parent_event_id=parent)
    cursor = max(r["event_id"] for r in await log.since(0))

    reads: list[tuple] = []
    original = backend.select

    async def _counting(table, filters=None, **kwargs):
        reads.append((table, filters))
        return await original(table, filters, **kwargs)

    backend.select = _counting
    try:
        await log.emit(stage="ask", label="twin 50", parent_event_id=parent)
        rows = await events_since("s2", cursor, backend=backend)
    finally:
        backend.select = original

    assert len(rows) == 1
    assert rows[0].depth == 1, "the ancestor outside this page was not resolved"
    # The only `run_events` reads are the incremental page and a narrow lookup of the one missing
    # ancestor. Neither may be an unfiltered scan of the session.
    for table, filters in reads:
        if table != "run_events":
            continue
        ops = {op for op, _, _ in (filters or [])}
        assert ops & {"gt", "in"}, f"an unbounded read of run_events: {filters}"


# ---------------------------------------------------------------- app_config


async def test_saving_settings_cannot_delete_a_key_it_did_not_mention(backend):
    """`app_config` rows are whole configurations; an upsert on `key` replaces the whole value.

    The Settings tab called this with ``{"saved_from": "settings tab"}``, which wiped every
    quality-gate threshold `seed_db` had written into the `twin` row — and then reported success
    with a fresh version number, so the loss looked deliberate.
    """
    from twinlab.services.lab import save_settings

    await backend.upsert(
        "app_config",
        [{"key": "twin", "value": {"temperature": 0.7, "mae_max": 1.0}, "version": 1}],
        on_conflict="key",
    )

    version = await save_settings("twin", {"temperature": 0.4}, backend=backend)
    rows = await backend.select("app_config", [("eq", "key", "twin")])

    assert version == 2
    assert rows[0]["value"] == {"temperature": 0.4, "mae_max": 1.0}


async def test_available_survey_twins_follows_the_chosen_scope(backend):
    """The count must agree with the rule the import it sits above actually applies.

    It once excluded synthetic rows unconditionally, on the grounds that
    `services.studio.create_twin_from_survey` refuses them — which it does, because `docs/06` §5's
    *From a survey answer* is a real-respondent mode. But §3.8's *Import twins from the survey* is
    the Generator-side path and its own control offers *Synthetic only*, so the blanket exclusion
    made the Settings tab read **0 available** with a synthetic batch loaded and left no way to
    import it. The scope decides, and the count follows it.

    This test was written against the older signature and called
    ``available_survey_twins(backend)`` positionally, passing the backend in as the scope — so it
    asserted a rule the function no longer has, through an argument it never read.
    """
    from twinlab.services.lab import available_survey_twins

    common = {
        "eligible": True, "consented": True, "consent_twin": True,
        "attention_passed": True, "outcome": "complete",
        "raw_object_path": "raw/x.json", "submitted_at": "2026-09-30T00:00:00Z",
    }
    await backend.insert("survey_submissions", [
        {"submission_id": "real-1", "data_type": "REAL", **common},
        {"submission_id": "synth-1", "data_type": "SYNTHETIC", **common},
        {"submission_id": "synth-2", "data_type": "SYNTHETIC", **common},
    ])

    assert await available_survey_twins("Real and synthetic", backend) == 3
    assert await available_survey_twins("Real only", backend) == 1
    assert await available_survey_twins("Synthetic only", backend) == 2


# ------------------------------------------------------------------- docs/05 §6, contrast


def _tl_tokens() -> dict[str, str]:
    """Every `--tl-*` colour token, resolved to a hex literal.

    Read out of `TWINLAB_CSS` rather than restated here: `docs/05` §2 makes the stylesheet the
    only place a colour is declared, so a test carrying its own copy would be a second source
    of truth for exactly the values it is checking.
    """
    import re

    from twinlab.ui.theme import TWINLAB_CSS

    literal = dict(re.findall(r"(--tl-[a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})", TWINLAB_CSS))
    alias = dict(re.findall(r"(--tl-[a-z0-9-]+)\s*:\s*var\((--tl-[a-z0-9-]+)\)", TWINLAB_CSS))
    for name, target in alias.items():
        seen, cursor = set(), target
        while cursor in alias and cursor not in seen:
            seen.add(cursor)
            cursor = alias[cursor]
        if cursor in literal:
            literal.setdefault(name, literal[cursor])
    return literal


def _contrast(fg: str, bg: str) -> float:
    """WCAG 2.1 relative-luminance contrast ratio."""

    def channel(value: int) -> float:
        srgb = value / 255
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    def luminance(hexcolour: str) -> float:
        r, g, b = (int(hexcolour[i : i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    first, second = luminance(fg), luminance(bg)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _rule_colours(selector: str) -> tuple[str, str]:
    """The `color` and `background` a class rule actually declares, as token names.

    Read from the rule rather than restated in the test, so darkening a pill in the stylesheet
    and darkening it in the test are the same edit. A test that carried its own copy of the
    token would keep passing after someone reverted the rule.
    """
    import re

    from twinlab.ui.theme import TWINLAB_CSS

    match = re.search(
        re.escape(selector) + r"\s*\{([^}]*)\}", TWINLAB_CSS
    )
    assert match, f"{selector} is not declared in TWINLAB_CSS"
    body = match.group(1)
    ink = re.search(r"(?<!-)color\s*:\s*var\((--tl-[a-z0-9-]+)\)", body)
    surface = re.search(r"background\s*:\s*var\((--tl-[a-z0-9-]+)\)", body)
    assert ink and surface, f"{selector} no longer declares both a colour and a background"
    return ink.group(1), surface.group(1)


@pytest.mark.parametrize(
    "selector",
    [".tl-pill-green", ".tl-pill-red", ".tl-pill-grey", ".tl-badge-live", ".tl-warn-strip"],
)
def test_a_pill_clears_the_body_floor_with_the_tokens_it_actually_declares(selector: str) -> None:
    """Reads the rule, so reverting the stylesheet fails here.

    `--tl-ok` on `--tl-ok-tint` was 4.34:1 and rendered 267 times on one Statistics page;
    `--tl-bad` on `--tl-bad-tint` was 4.39:1 on the live-model badge. Both read fine to someone
    who already knows what they say, which is why neither was noticed.
    """
    tokens = _tl_tokens()
    ink, surface = _rule_colours(selector)
    ratio = _contrast(tokens[ink], tokens[surface])
    assert ratio >= 4.5, (
        f"{selector}: {ink} ({tokens[ink]}) on {surface} ({tokens[surface]}) is "
        f"{ratio:.2f}:1, under the 4.5:1 body floor (docs/05 §6)"
    )


#: `docs/05` §6: "Body text >= 4.5:1 contrast; large text and UI chrome >= 3:1." Every pair here
#: is small text a researcher reads as data, so all of them take the body floor. Button fills
#: and tab strips are chrome and are not listed.
INK_ON_SURFACE: tuple[tuple[str, str, str], ...] = (
    ("body", "--tl-grey-900", "--tl-white"),
    ("body on page", "--tl-grey-900", "--tl-grey-50"),
    ("secondary body", "--tl-grey-700", "--tl-white"),
    ("caption", "--tl-grey-500", "--tl-white"),
    ("caption on page", "--tl-grey-500", "--tl-grey-50"),
    ("nav", "--tl-grey-500", "--tl-grey-50"),
)


@pytest.mark.parametrize(("label", "ink", "surface"), INK_ON_SURFACE)
def test_small_text_clears_the_body_contrast_floor(label: str, ink: str, surface: str) -> None:
    """`docs/05` §6's 4.5:1 body floor, per ink-on-surface pair the design system declares.

    Stated as a testable minimum in §6 and never enforced, so it drifted: `--tl-ok` on
    `--tl-ok-tint` sat at 4.34:1 and rendered 267 times on one Statistics page, and the live
    model badge sat at 4.39:1. Both read fine to someone who already knows what they say.
    """
    tokens = _tl_tokens()
    assert ink in tokens, f"{ink} is not declared in TWINLAB_CSS"
    assert surface in tokens, f"{surface} is not declared in TWINLAB_CSS"

    ratio = _contrast(tokens[ink], tokens[surface])
    assert ratio >= 4.5, (
        f"{label}: {ink} ({tokens[ink]}) on {surface} ({tokens[surface]}) is {ratio:.2f}:1, "
        f"under the 4.5:1 body floor (docs/05 §6)"
    )


def test_the_contrast_check_rejects_a_pair_that_fails() -> None:
    """A gate that cannot fail is not a gate. These are the two values that were actually wrong."""
    assert _contrast("#308038", "#E7F4EA") < 4.5  # --tl-ok on --tl-ok-tint, the 267 pills
    assert _contrast("#CD3021", "#FAE8E6") < 4.5  # --tl-bad on --tl-bad-tint, the live badge


#: The Gradio tokens that decide whether text is legible at all. Each is re-pointed under
#: `.dark` in `TWINLAB_CSS`; without them Gradio's dark theme puts #F4F4F5 letters on the white
#: surfaces this design forces, which is 1.05:1.
DARK_MODE_TOKENS: tuple[str, ...] = (
    "--body-text-color",
    "--body-text-color-subdued",
    "--background-fill-primary",
    "--block-background-fill",
    "--block-label-text-color",
    "--input-background-fill",
    "--border-color-primary",
    "--table-text-color",
    "--error-text-color",
)


def test_dark_mode_is_neutralised_at_the_token_layer() -> None:
    """Twin Lab is a light design; Gradio applies `.dark` from the browser's own preference.

    The repair is at the token layer, not per component, because a per-component list is never
    finished — the accordion labels, which are a `<span class="label-wrap">`, were missed by
    both of the label overrides that existed and were invisible on every screen.
    """
    import re

    from twinlab.ui.theme import TWINLAB_CSS

    blocks = re.findall(r"\.dark[^{]*\{([^}]*)\}", TWINLAB_CSS, re.S)
    assert blocks, "TWINLAB_CSS no longer overrides anything under `.dark`"
    declared = "\n".join(blocks)

    missing = [token for token in DARK_MODE_TOKENS if f"{token}:" not in declared]
    assert not missing, f"dark mode would leak through these tokens: {', '.join(missing)}"


def test_the_screen_reader_copy_of_a_tab_strip_stays_hidden() -> None:
    """Gradio ships a `visually-hidden` duplicate of every tab list.

    `display:flex !important` on `.tab-container` beat the clip that hides it, so every tab
    label rendered twice on Twin Lab and on Statistics. The fix must stay a `display:none` on
    the hidden copy, not the removal of the flex rule the real strip needs.
    """
    from twinlab.ui.theme import TWINLAB_CSS

    for strip in (".tl-subnav", ".tl-pilltabs"):
        assert f"{strip} .tab-container.visually-hidden" in TWINLAB_CSS, (
            f"{strip} no longer hides Gradio's screen-reader copy of the tab strip"
        )


def test_a_destination_card_is_a_link_around_the_whole_card() -> None:
    """`docs/06` §1.1's cards are controls, not paragraphs with a link in them.

    The card used to wrap only the route in an `<a>`, leaving the title and the description
    inert and the hit target about a quarter of the tile.
    """
    from twinlab.models.view import LinkCard
    from twinlab.ui.pages.main_menu import _card_html

    html = _card_html(
        LinkCard(title="Look inside one twin", description="Persona and answers.", route="/lab",
                 tab="Twins")
    )

    assert html.startswith('<a class="tl-card tl-link-card" href="/lab">')
    assert html.rstrip().endswith("</a>")
    assert html.count("<a ") == 1, "the destination must not be a second, nested link"
    # All three elements of §1.1 survive the change.
    assert "Look inside one twin" in html
    assert "Persona and answers." in html
    assert "/lab → Twins" in html
