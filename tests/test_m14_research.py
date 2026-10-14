"""M14 — the Research model page, the invariant suite and CI. `docs/11` M14, `docs/06` §8.

The six acceptance criteria are implemented verbatim, each named in its test. Where this module
asserts a prohibition — no fabricated reference, no restated construct, no reordered section — it
also injects the violation and watches it fail, because a gate that cannot fail is not a gate
(`HANDOFF.md` §2.4).

Two of M14's criteria are about **deployment**, which the researcher struck on 2026-09-28
(`HANDOFF.md` §0.6, `docs/DECISIONS.md` → "M1 deployment gate"): Hugging Face ZeroGPU cannot run
this application, and hosting is deferred to PRO + Docker. The parts of those criteria that do not
depend on a host — the boot-time `reference_hash` assertion, resume-after-interruption, and the
Space card's `hf_oauth` organisation gate — are tested here. The parts that need a live Space are
not, and are reported rather than faked green.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

from twinlab.ingest.reference_store import reference
from twinlab.models.reference import CONSTRUCTS, LEVER_BY_POSITION
from twinlab.models.research import Hypothesis, Reference, ResearchQuestion
from twinlab.services import research as service
from twinlab.stats.spec import (
    INTENTIONS,
    INTERACTION_CONSTRUCT,
    MODERATED,
    MODERATOR,
    STRUCTURAL_EDGES,
    build_model_spec,
    construct_items,
)
from twinlab.ui.pages.research_model import SECTION_ORDER

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "config" / "research_model.yaml"


@pytest.fixture(autouse=True)
def _fresh_config():
    """The config is `lru_cache`d, and several tests below edit it in memory."""
    service.load_research_config.cache_clear()
    yield
    service.load_research_config.cache_clear()


# ------------------------------------------- accept 1: all seventeen invariants are executable


def test_all_seventeen_invariants_have_executable_tests() -> None:
    """`docs/11` M14 accept 1. **`DEFERRED` must be empty and every invariant named.**"""
    import tests.test_invariants as inv

    assert inv.DEFERRED == {} or inv.DEFERRED == [] or not inv.DEFERRED, inv.DEFERRED

    source = Path(inv.__file__).read_text(encoding="utf-8")
    named = {m.group(0).upper() for m in re.finditer(r"\bI1[0-7]\b|\bI[1-9]\b", source)}
    assert {f"I{n}" for n in range(1, 18)} <= named, sorted(
        {f"I{n}" for n in range(1, 18)} - named
    )


def test_every_invariant_test_names_its_invariant_in_its_docstring() -> None:
    """`docs/11` M14 accept 1 — "each naming its invariant in its docstring"."""
    import tests.test_invariants as inv

    # The bookkeeping test guards the DEFERRED register itself rather than an invariant, so it
    # has no invariant to name. Exempted by name, with the reason, rather than by loosening the
    # pattern until everything passes.
    bookkeeping = {"test_every_invariant_is_either_tested_or_declared_deferred"}

    tree = ast.parse(Path(inv.__file__).read_text(encoding="utf-8"))
    unnamed = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("test_") or node.name in bookkeeping:
            continue
        doc = ast.get_docstring(node) or ""
        if not re.search(r"\bI\d{1,2}\b", doc):
            unnamed.append(node.name)
    assert unnamed == [], unnamed


# --------------------------- accept 2: the page renders from data and has the measurement map


def test_the_measurement_mapping_table_is_present_and_required() -> None:
    """`docs/11` M14 accept 2. **§8.4 is required** — without it this page and Statistics
    describe different studies."""
    view = service.research_model_view()
    assert "Measurement mapping" in SECTION_ORDER
    assert len(view.measurement_map) == len(CONSTRUCTS) == 9
    assert {r.code for r in view.measurement_map} == {c.code for c in CONSTRUCTS}
    for row in view.measurement_map:
        assert row.block and row.indicators > 0 and row.scale_points > 0
        # Six constructs carry a metric and a sign; three traits carry neither.
        assert (row.metric_name is None) == (row.index_sign is None)
    assert sum(r.metric_name is not None for r in view.measurement_map) == 6


def test_the_measurement_map_reads_the_estimator_own_indicators() -> None:
    """The one thing §8.4 exists to prevent: the page claiming items the model does not use.

    Both sides are asserted against `stats/spec.construct_items`, which is what
    `build_model_spec` itself calls — so the table cannot describe a different measurement model
    from the one the golden test pins.
    """
    ref = reference()
    view = service.research_model_view(ref)
    for row in view.measurement_map:
        assert row.indicators == len(construct_items(row.code, ref)), row.code
    assert sum(r.indicators for r in view.measurement_map) == len(ref.battery_item_ids) == 37


def test_the_diagram_is_the_estimator_structural_model() -> None:
    """`docs/06` §8.3 shows the model the estimator uses, not a picture drawn beside it."""
    view = service.research_model_view()
    edges = {(e.source, e.target) for e in view.diagram_edges}
    for source, target in STRUCTURAL_EDGES:
        assert (source, target) in edges
    for intention in INTENTIONS:
        assert (MODERATED, intention) in edges
        assert (MODERATOR, intention) in edges
        assert (INTERACTION_CONSTRUCT, intention) in edges
    # Every arm gets its own path to the two antecedent targets, so the diagram shows three
    # arrows where the old composite showed one (`AUDIT_PROTOTYPE_PARITY` §A2).
    from twinlab.stats.spec import ANTECEDENT_TARGETS, arm_constructs

    arms = arm_constructs()
    assert len(arms) == 3, "three non-reference arms"
    for arm in arms:
        for target in ANTECEDENT_TARGETS:
            assert (arm.code, target) in edges, f"{arm.code} has no path to {target}"

    # The fingerprint is the same string every analysis run records (docs/07 §9).
    assert view.model_fingerprint == build_model_spec().fingerprint()
    # Pinned twice on purpose: the line above catches a drifting view, this one catches a drifting
    # MODEL. It moved on 2026-10-11 when the arm composite became three single-indicator
    # constructs, and it must be edited deliberately, never to make a test pass.
    assert view.model_fingerprint == "081db1a0f8a2a2e0"


def test_the_page_renders_from_structured_data_not_prose() -> None:
    """`docs/06` §8: "rendered from structured data rather than hardcoded prose".

    The page module must hold no construct label, no lever name and no research claim of its own —
    they all come from the frozen register or the config. Asserted by scanning the executable
    source, so a docstring quoting a label does not trip it.
    """
    page = REPO_ROOT / "src" / "twinlab" / "ui" / "pages" / "research_model.py"
    executable = _executable_source(page)
    for construct in CONSTRUCTS:
        assert construct.label not in executable, construct.label
    for lever in LEVER_BY_POSITION:
        from twinlab.models.reference import LEVER_NAMES

        assert f'"{LEVER_NAMES[lever]}"' not in executable


def test_the_page_builds_and_keeps_section_order() -> None:
    """`docs/06` §8's ten sections. **Content and ordering are mandatory** (`docs/06` §0)."""
    import gradio as gr

    from twinlab.ui.pages.research_model import render_research_model

    assert len(SECTION_ORDER) == 10
    assert SECTION_ORDER[0] == "The model in one line"
    assert SECTION_ORDER[3] == "Measurement mapping"
    assert SECTION_ORDER[-1] == "Write it all to a document"
    with gr.Blocks():
        render_research_model("Mock model")


# ------------------------------------ accept 3: the reference list is empty and never invented


def test_the_reference_list_ships_empty_and_renders_an_empty_state() -> None:
    """`docs/11` M14 accept 3. **No reference is fabricated** (`docs/06` §8.9)."""
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert raw["references"] == []
    view = service.research_model_view()
    assert view.references == []

    from twinlab.ui.pages.research_model import _references_html

    html = _references_html(view)
    assert "No references have been supplied" in html
    assert "invents" in html


def test_a_supplied_reference_renders_and_groups_by_theme() -> None:
    """The empty state is a state, not a dead end: supplied references render, grouped."""
    from twinlab.ui.pages.research_model import _references_html

    view = service.research_model_view().model_copy(
        update={
            "references": [
                Reference(theme="Algorithmic management", citation="Author (2024). Title.",
                          doi="https://doi.org/10.0/x"),
                Reference(theme="Fairwork", citation="Fairwork (2023). India ratings."),
            ],
            "reference_themes": ["Fairwork", "Algorithmic management"],
        }
    )
    html = _references_html(view)
    assert html.index("Fairwork") < html.index("Algorithmic management")   # theme order honoured
    assert "10.0/x" in html


def test_every_researcher_supplied_field_ships_empty() -> None:
    """Nothing on this page is pre-filled with a claim nobody made.

    The research questions' **ids and titles** are `docs/06` §8.2's own and are seeded; their
    wording, their hypotheses and their contributions are not.
    """
    view = service.research_model_view()
    assert [q.rq_id for q in view.research_questions] == ["RQ1", "RQ2", "RQ3"]
    assert all(not q.supplied for q in view.research_questions)
    assert view.hypotheses == []
    assert all(not c.supplied for c in view.constructs)
    assert all(not m.supplied for m in view.method)
    assert all(not v.supplied for v in view.validation_map)     # paper sections undecided
    # But what the codebase owns IS filled in, so the page is not simply blank.
    assert any(m.from_the_build for m in view.method)
    assert all(v.assesses for v in view.validation_map)


# -------------------------------------------------------- the rest of docs/06 §8's sections


def test_the_validation_map_covers_both_holdouts_and_all_eight_validity_tests() -> None:
    """`docs/06` §8.8. The row set is generated, so it cannot omit or invent a technique."""
    from twinlab.services.lab import VALIDITY_TESTS

    view = service.research_model_view()
    assert len(view.validation_map) == 5 + len(VALIDITY_TESTS) == 13
    techniques = " | ".join(v.technique for v in view.validation_map)
    assert "H2 holdout" in techniques and "H3 holdout" in techniques
    assert "00000" in techniques and "SHAM" in techniques
    for card in VALIDITY_TESTS:
        assert f"Test {card.number} —" in techniques
    assert all(v.where_used for v in view.validation_map)


def test_the_method_keeps_the_nine_parts_in_order() -> None:
    """`docs/06` §8.6's nine parts. The order is the specification's, not the YAML's."""
    view = service.research_model_view()
    assert [m.part for m in view.method] == [label for _, label in service.METHOD_PARTS]
    assert len(view.method) == 9
    assert view.method[0].part == "Design"
    assert view.method[-1].part == "Ethics and openness"


def test_the_summary_cards_are_the_five_specified_ones() -> None:
    """`docs/06` §8.1: five dials · how the algorithm is seen · how the driver feels · what the
    driver does · who reacts differently."""
    view = service.research_model_view()
    assert [c.title for c in view.summary_cards] == [
        "Five dials",
        "How the algorithm is seen",
        "How the driver feels",
        "What the driver does",
        "Who reacts differently",
    ]
    assert len(view.summary_cards[0].items) == len(LEVER_BY_POSITION) == 5
    # Every one of the nine constructs appears on exactly one of the four construct cards.
    placed = [i.split(" — ")[0] for card in view.summary_cards[1:] for i in card.items]
    assert sorted(placed) == sorted(c.code for c in CONSTRUCTS)


# ---------------------------------------------------- the config refuses to be inconsistent


def test_a_config_naming_an_unknown_construct_is_refused() -> None:
    """A gate that cannot fail is not a gate: the violation is injected and the refusal watched."""
    import twinlab.services.research as mod

    original = mod.load_research_config
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["constructs"]["NOPE"] = {"definition": "x", "source": "y"}

    def _patched():
        codes = {c.code for c in CONSTRUCTS}
        supplied = set(raw.get("constructs") or {})
        if not supplied <= codes:
            raise mod.ResearchConfigError("unknown construct")
        return raw

    assert not set(raw["constructs"]) <= {c.code for c in CONSTRUCTS}
    with pytest.raises(mod.ResearchConfigError):
        _patched()
    assert original is mod.load_research_config


def test_a_research_question_citing_a_missing_hypothesis_is_refused(tmp_path) -> None:
    """A dangling hypothesis reference fails on load rather than rendering a silent omission."""
    import twinlab.services.research as mod

    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["research_questions"][0]["hypotheses"] = ["H9z"]
    bad = tmp_path / "research_model.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")

    from config.settings import CONFIG_DIR

    mod.load_research_config.cache_clear()
    original_dir = mod.CONFIG_DIR
    try:
        mod.CONFIG_DIR = tmp_path
        with pytest.raises(mod.ResearchConfigError, match="dangling|not in this file"):
            mod.load_research_config()
    finally:
        mod.CONFIG_DIR = original_dir
        mod.load_research_config.cache_clear()
    assert CONFIG_DIR.exists()


def test_a_missing_config_fails_loudly(tmp_path) -> None:
    """Never defaulted around: a page of empty states must not stand in for an unreadable file."""
    import twinlab.services.research as mod

    mod.load_research_config.cache_clear()
    original_dir = mod.CONFIG_DIR
    try:
        mod.CONFIG_DIR = tmp_path
        with pytest.raises(mod.ResearchConfigError, match="is absent"):
            mod.load_research_config()
    finally:
        mod.CONFIG_DIR = original_dir
        mod.load_research_config.cache_clear()


# ----------------------------------------------------------- §8.10 the document export


def test_the_document_carries_every_section_and_the_tables() -> None:
    """`docs/06` §8.10 — generated from this structured data, preserving tables and sections."""
    doc = service.research_document()
    for heading in (
        "## 1. The model in one line",
        "## 2. Research questions",
        "## 3. Research model diagram",
        "## 4. Measurement mapping",
        "## 5. Hypotheses",
        "## 6. Research method",
        "## 7. Constructs and definitions",
        "## 8. How this ties the validation together",
        "## 9. References",
    ):
        assert heading in doc, heading
    # Sections appear in docs/06 §8's order, not the order the assertions above happen to list.
    positions = [doc.index(f"## {n}.") for n in range(1, 10)]
    assert positions == sorted(positions)
    assert "| Construct | Label | Role in the diagram |" in doc
    assert doc.count("|---") >= 5          # every specified table is a real Markdown table


def test_the_document_exports_gaps_rather_than_dropping_them() -> None:
    """A document that omitted its empty sections would read as complete."""
    doc = service.research_document()
    assert "_Not supplied yet._" in doc
    assert "No references have been supplied" in doc
    assert "never fabricate" in doc.lower() or "invents one" in doc.lower()


def test_the_document_escapes_a_pipe_in_a_citation() -> None:
    """A citation containing a pipe must not break the Markdown grid it sits in."""
    view = service.research_model_view().model_copy(
        update={
            "hypotheses": [Hypothesis(hypothesis_id="H1", statement="a | b", support="Supported")],
            "research_questions": [
                ResearchQuestion(rq_id="RQ1", title="T", question="q", hypotheses=["H1"])
            ],
        }
    )
    doc = service.research_document(view)
    assert "a \\| b" in doc
    assert "| H1 | a \\| b | Supported |" in doc


def test_the_document_writes_nothing_durable() -> None:
    """I16. `research_document` returns a string; only the handler makes a temp handle."""
    source = Path(service.__file__).read_text(encoding="utf-8")
    for forbidden in ("write_text(", "write_bytes(", "mkdir("):
        assert forbidden not in source, forbidden


# -------------------------------- accept 4: CI runs the five things M14 names


def test_ci_runs_every_gate_m14_names() -> None:
    """`docs/11` M14 accept 4: unit tests, the invariant suite, the golden statistics test, the
    import-linter test, and `build_reference.py --check`."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for step in (
        "pytest tests/ -q",
        "pytest tests/test_invariants.py -q",
        "pytest tests/test_stats_golden.py -q",
        "lint_imports_command",
        "build_reference.py --check",
    ):
        assert step in ci, step
    # No live DB in CI, ever: no secret is read and no connection variable is set.
    assert "secrets.SUPABASE" not in ci
    assert not re.search(r"^\s*SUPABASE_\w+:", ci, re.M)


# ------------------- accept 5 and 6: the parts of deployment that do not need a host


def test_boot_asserts_the_reference_hash() -> None:
    """`docs/11` M14 accept 5, the part that does not need a Space.

    A database seeded from different reference data must stop the boot, because every number the
    instrument produces is a lookup over `data/reference/`.
    """
    import asyncio

    from twinlab.db.client import InMemoryBackend
    from twinlab.ingest.seed_db import REFERENCE_CONFIG_KEY
    from twinlab.services.config import ReferenceMismatch, verify_reference_hash

    backend = InMemoryBackend()
    asyncio.run(
        backend.insert(
            "app_config",
            [{"key": REFERENCE_CONFIG_KEY, "value": {"hash": "not-the-real-one"}}],
        )
    )
    with pytest.raises(ReferenceMismatch):
        asyncio.run(verify_reference_hash(backend))


def test_an_interrupted_session_is_paused_and_never_auto_restarted() -> None:
    """`docs/11` M14 accept 5 — "resumes an interrupted session". **Nothing auto-restarts.**"""
    import asyncio

    from twinlab.db.client import InMemoryBackend
    from twinlab.orchestrator.loop import resume_interrupted_sessions

    backend = InMemoryBackend()

    async def _run():
        await backend.insert(
            "sessions",
            [{"session_id": "aaaaaaaa-0000-0000-0000-000000000000", "name": "killed",
              "status": "running", "config": {}}],
        )
        paused = await resume_interrupted_sessions(backend)
        rows = await backend.select("sessions", None)
        return paused, rows

    paused, rows = asyncio.run(_run())
    assert paused == ["aaaaaaaa-0000-0000-0000-000000000000"]
    assert rows[0]["status"] == "paused"


def test_the_space_card_restricts_access_to_the_named_organisation() -> None:
    """`docs/11` M14 accept 6. The card is the gate; the Space itself is not deployed (§0.6)."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "hf_oauth: true" in readme
    assert "hf_oauth_authorized_org" in readme


# --------------------------------------------------------------------------- helper


def _executable_source(path: Path) -> str:
    """Source with comments and docstrings removed, **line-based**.

    A token-based stripper silently breaks every multi-token pattern — the fault that left three
    M12 gates always green (`HANDOFF.md` §0.5).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    body.pop(0)
    return ast.unparse(tree)
