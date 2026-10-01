"""M12 — the Statistics screen. `docs/06` §7, `docs/05` §4.4.

`HANDOFF.md` §0.5 is blunt about the limit of these: **green tests do not prove a Gradio screen
works**, and both bugs found in M10 and M11 were invisible to the suite. What is testable is the
contract — the tab order, the legend on every table, the provenance on every view, the absence of
arithmetic in a handler — and that is what is asserted here.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from twinlab.models.stats import STAGES, AnalysisProvenance, StatsTableSpec
from twinlab.ui.components import provenance_strip, stats_table, unvalidated_banner
from twinlab.ui.pages import statistics as page

SRC = Path(__file__).resolve().parents[1] / "src" / "twinlab"
PAGE = SRC / "ui" / "pages" / "statistics.py"


def _source() -> str:
    from tests.test_m10_ui import _executable_source

    return _executable_source(PAGE)


# --------------------------------------------------------------------- structure

def test_ten_tabs_in_the_specified_order():
    """`docs/06` §7. Content and ordering are mandatory, not a design choice."""
    assert page.TAB_ORDER == (
        "Construct reliability and validity",
        "Discriminant validity",
        "Collinearity",
        "Outer model",
        "Path coefficients",
        "Indirect and total effects",
        "R², f², Q²",
        "PLSpredict",
        "Model fit",
        "Export",
    )
    assert len(page.TAB_ORDER) == 10


def test_nine_stages_have_a_renderer_and_export_does_not():
    """Nine computed stages plus Export, which is a file, not a stage."""
    assert set(page.RENDERERS) == set(STAGES)
    assert len(page.TAB_ORDER) == len(STAGES) + 1


def test_control_strip_offers_the_three_populations_and_two_screenings():
    """`docs/06` §7's control strip."""
    assert [v for _, v in page.POPULATION_CHOICES] == ["synthetic", "real", "both"]
    assert [v for _, v in page.SCREENING_CHOICES] == ["strict", "none"]


def test_the_page_builds():
    """The route renders without raising. Not proof it works — proof it constructs."""
    import gradio as gr

    with gr.Blocks():
        page.render_statistics("stub")


# --------------------------------------------------------------------- docs/05 §4.4

def test_every_stats_table_carries_a_legend():
    """`docs/05` §4.4 — a statistical abbreviation needs a `title` **and** a visible legend."""
    from twinlab.services.statistics import LEGENDS

    for stage in STAGES:
        assert LEGENDS.get(stage), f"{stage} has no legend"


def test_stats_table_renders_the_legend_above_the_table():
    spec = StatsTableSpec(
        title="Construct reliability",
        headers=("Construct", "AVE"),
        legend=(("AVE", "Average variance extracted. 0.50 or above."),),
    )
    html = stats_table(spec, [["FAIR", "0.751"]])
    assert html.index("tl-legend") < html.index("<table"), "the legend must come above the table"
    assert "Average variance extracted" in html


def test_stats_table_puts_the_meaning_in_a_title_attribute():
    """§4.4 requires both. The column header carries the tooltip; the legend carries the text."""
    spec = StatsTableSpec(
        title="T", headers=("rho_A",), legend=(("rho_A", "Dijkstra-Henseler reliability."),)
    )
    html = stats_table(spec, [["0.91"]])
    assert 'title="Dijkstra-Henseler reliability."' in html


def test_stats_table_refuses_a_spec_with_no_legend():
    """A gate that cannot fail is not a gate (`HANDOFF.md` §2.4)."""
    spec = StatsTableSpec(title="T", headers=("A",), legend=())
    with pytest.raises(ValueError, match="legend"):
        stats_table(spec, [["1"]])


def test_stats_table_shows_an_empty_state_rather_than_a_blank(monkeypatch):
    """`docs/05` §5: an empty state names the action that fixes it."""
    spec = StatsTableSpec(title="T", headers=("A",), legend=(("A", "a thing"),))
    html = stats_table(spec, [])
    assert "Run the analysis" in html


# --------------------------------------------------------------------- docs/07 §9

def test_provenance_strip_carries_all_five_required_facts():
    """`docs/07` §9. The paper must state all five, so every result view shows them."""
    html = provenance_strip(
        AnalysisProvenance(
            engine_version="1.11.0", n_cases=314, bootstrap_samples=5000, seed=99,
            screening="strict", population="real", model_fingerprint="abc123",
        )
    )
    assert "1.11.0" in html
    assert "314" in html
    assert "5,000" in html
    assert "99" in html
    assert "Dropped attention failures" in html


def test_provenance_names_the_screening_rule_in_words():
    """A rule shown as `strict` tells the researcher nothing about what it removed."""
    kept = provenance_strip(
        AnalysisProvenance(
            engine_version="1.11.0", n_cases=10, bootstrap_samples=5000, seed=1,
            screening="none", population="both", model_fingerprint="x",
        )
    )
    assert "Kept everyone" in kept
    assert "Real and synthetic" in kept


def test_unvalidated_banner_carries_its_text_not_just_a_colour():
    """`docs/05` §6: never colour alone."""
    html = unvalidated_banner("No number here is reportable.")
    assert "UNVALIDATED" in html
    assert "reportable" in html
    assert 'role="status"' in html


# --------------------------------------------------------------------- rendering rules

def test_absent_statistics_render_as_not_tested_never_as_zero():
    """I17. A missing statistic and a measured zero must never look the same."""
    html = page._reliability_html(
        {
            "rows": [
                {
                    "construct_code": "ARM", "label": "Experimental arm", "n_items": 3,
                    "mean": None, "sd": None, "cronbach_alpha": None, "rho_a": None,
                    "rho_c": None, "ave": None, "status": "na",
                    "note": "formative block",
                }
            ]
        }
    )
    assert "Not tested" in html
    assert "0.000" not in html


def test_status_is_a_word_not_only_a_colour():
    """`docs/05` §6. A colour-only status cannot be constructed by the primitives."""
    for value, word in (("ok", "ok"), ("check", "check"), ("na", "not applicable")):
        assert word in page._status(value)


def test_a_missing_stage_renders_an_empty_state_not_an_empty_table():
    for stage, render in page.RENDERERS.items():
        html = render(None)
        assert html, f"{stage} rendered nothing at all"


# --------------------------------------------------------------------- the handler rules

def test_the_page_imports_no_forbidden_layer():
    """`ARCHITECTURE.md` §4: `ui/` may import `services/` and `models/` only."""
    tree = ast.parse(PAGE.read_text(encoding="utf-8"))
    forbidden = ("twinlab.db", "twinlab.agents", "twinlab.orchestrator", "twinlab.analysis")
    for node in ast.walk(tree):
        module = ""
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
        elif isinstance(node, ast.Import):
            module = node.names[0].name
        for banned in forbidden:
            assert not module.startswith(banned), f"statistics.py imports {module}"


def test_no_repeating_timer_on_this_page():
    """`docs/05` §8.4 and the M10 regression: a first paint belongs on `load_once`."""
    assert "gr.Timer" not in _source()
    assert "load_once(" in _source()


def test_no_arithmetic_on_a_statistic_in_a_handler():
    """`docs/05` §8.4 rule 5. The service hands over the number *and* its rendering.

    Scanned over executable source so the prose explaining the rule does not trip it.
    """
    source = _source()
    # Division and multiplication on a rendered value are what this forbids; the page may still
    # index, format and concatenate.
    offenders = re.findall(r"(?:loading|estimate|r_squared|ave|htmt|vif)\s*[*/+-]\s*\w", source)
    assert offenders == [], f"statistics.py does arithmetic on a statistic: {offenders}"


def test_no_llm_call_in_the_page():
    """`CLAUDE.md` rule 12 and I12. The measurement layer is arithmetic; no model touches it."""
    source = _source()
    for banned in ("build_agent", "pydantic_ai", "run_answer_ladder", "agents."):
        assert banned not in source, f"statistics.py references {banned}"


def test_the_page_states_that_statistics_never_reads_the_sweep():
    """`docs/07` §1. Conflating the two layers is the easiest serious mistake in the project."""
    prose = PAGE.read_text(encoding="utf-8")
    assert "does not read" in prose or "never reads" in prose


def test_export_tab_explains_the_two_header_rows():
    """`docs/07` §11 — the scale row is the whole reason the export was rebuilt."""
    intro = page._export_intro()
    assert "two header rows" in intro
    assert "1-5" in intro and "1-7" in intro
