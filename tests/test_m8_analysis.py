"""M8 — analysis. `docs/11` M8.

The seven acceptance criteria are implemented verbatim, each named in its test.

The golden fixtures in `docs/07` §4.2 are **regression tests, not illustrations** — they reproduce
the prototype's stored output to 3 dp. If one moves, a formula moved with it.
"""

from __future__ import annotations

import pytest

from twinlab.agents.registry import StubModelClient, default_agent_configs
from twinlab.analysis import metrics as mx
from twinlab.analysis.interactions import (
    computable_interactions,
    describe,
    describe_missing,
    interaction,
    joint_code,
)
from twinlab.analysis.report import (
    FALLBACK_PREFIX,
    build_bundle,
    build_user_prompt,
    template_reading,
    write_analysis,
)
from twinlab.ingest.reference_store import reference
from twinlab.models.analysis import (
    AnalysisConfig,
    AnalysisResult,
    CellShifts,
    Interaction,
    MissingInteraction,
)
from twinlab.orchestrator.panel import PanelMismatch
from twinlab.services.config import load_analysis_config

#: `docs/07` §4.2. Five from stored prototype output, plus `21122` from the 1.0 mock.
GOLDEN: dict[str, tuple[tuple[float, ...], float]] = {
    "20000": ((+0.13, 0.00, +0.76, +0.52, 0.00, -0.59), 0.333),
    "21000": ((+0.13, 0.00, +1.06, +0.61, 0.00, -0.91), 0.452),
    "22200": ((+0.46, +0.95, +1.29, +0.72, 0.00, -0.99), 0.735),
    "21012": ((+1.01, +0.01, +1.38, +1.06, -1.72, -0.98), 1.027),
    "22222": ((+1.62, +0.94, +1.53, +1.01, -1.81, -0.98), 1.315),
    "21122": ((+1.62, +0.60, +1.50, +0.68, -2.05, -1.02), 1.245),
}

METRIC_ORDER = ("fairness", "clarity", "happiness", "staying", "pushback", "leaving")


def _shift_dict(values: tuple[float, ...]) -> dict[str, float]:
    return dict(zip(METRIC_ORDER, values, strict=True))


def _answers(value_5: int = 4, value_7: int = 5, **overrides) -> dict[str, int]:
    ref = reference()
    out = {
        i: (value_5 if ref.scale_points(i) == 5 else value_7) for i in ref.battery_item_ids
    }
    out.update(overrides)
    return out


# ---------------------------------------------------------------- reverse coding


def test_reverse_coding_is_applied_to_sat2_dep1_and_h2_sat2_only():
    """`docs/11` M8, verbatim — those three items and no others."""
    ref = reference()
    reversed_items = sorted(i.item_id for i in ref.items.values() if i.reverse_coded)
    assert reversed_items == ["DEP1", "H2_SAT2", "SAT2"]


def test_each_reversal_is_about_its_own_scales_midpoint():
    """`docs/07` §2.1 — a 5-point item reverses about 6, a 7-point about 8.

    Reversing everything about 8 silently corrupts three of the nine constructs, which is
    exactly the
    class of defect that survives review because every number still looks plausible.
    """
    assert mx.reverse_code(1, 7) == 7 and mx.reverse_code(7, 7) == 1
    assert mx.reverse_code(1, 5) == 5 and mx.reverse_code(5, 5) == 1
    assert mx.reverse_code(4, 7) == 4          # the 7-point midpoint is its own reverse
    assert mx.reverse_code(3, 5) == 3          # and so is the 5-point one

    # **All three reverse-coded items are in fact 7-point** in the frozen register, so `docs/07`
    # §2.1's stated consequence — "Reversing every item about 8 is a silent corruption of three of
    # the nine constructs" — does not describe the current data: about 8 is *correct* for all three.
    # The safeguard is still right and still tested above, because `score()` reads each item's own
    # `scales.points` rather than the metric's, so a future 5-point reverse item cannot break it.
    # Recorded in `docs/DECISIONS.md`.
    ref = reference()
    for item_id in ("SAT2", "DEP1", "H2_SAT2"):
        assert ref.scale_points(item_id) == 7, f"{item_id} moved scale; re-read docs/07 §2.1"
    assert not [
        i.item_id for i in ref.items.values() if i.reverse_coded and ref.scale_points(i.item_id)
        == 5
    ]


def test_a_reversed_item_actually_changes_its_metric():
    """SAT2 sits in `happiness`. If the reversal were skipped the mean would differ."""
    answers = _answers(value_5=4, value_7=5)
    happiness = mx.score(answers, "happiness")
    # SAT1=5, SAT2 raw 5 -> reversed 3, SAT3=5  =>  (5+3+5)/3
    assert happiness == pytest.approx((5 + 3 + 5) / 3)
    assert happiness != pytest.approx(5.0), "the reversal was not applied"


# ---------------------------------------------------------------- scales


def test_five_point_metrics_are_not_rescaled_to_seven():
    """`docs/11` M8, verbatim. `docs/07` §2.2.

    `clarity` and `staying` are reported on 1-5. Standardisation belongs to the modelling stage,
    never to a display metric — a rescaled display metric makes the index's stated limitation
    invisible.
    """
    ref = reference()
    answers = _answers(value_5=5, value_7=7)
    assert mx.score(answers, "clarity") == 5.0
    assert mx.score(answers, "staying") == 5.0
    assert mx.score(answers, "fairness") == 7.0

    assert ref.metrics["clarity"].scale == "agree5"
    assert ref.metrics["staying"].scale == "agree5"


def test_a_metric_is_never_computed_over_a_subset():
    """`docs/07` §2.3 — a vector that did not pass the contract is absent, not partial."""
    answers = _answers()
    del answers["FAIR2"]
    with pytest.raises(mx.MetricError, match="FAIR2"):
        mx.score(answers, "fairness")


def test_all_six_metrics_come_from_the_frozen_register():
    """Nothing in `metrics.py` is a constant: the definitions are the reference data."""
    ref = reference()
    assert sorted(ref.metrics) == sorted(METRIC_ORDER)
    scores = mx.score_all(_answers())
    assert sorted(scores) == sorted(METRIC_ORDER)


# ---------------------------------------------------------------- the index and the goldens


@pytest.mark.parametrize("code", sorted(GOLDEN))
def test_the_index_reproduces_every_golden_fixture_to_three_dp(code: str):
    """`docs/11` M8, verbatim — in particular `22222 → 1.315` and `21012 → 1.027`.

    `docs/07` §4.2: these reproduce the prototype's `Designs` sheet to 3 dp and are regression
    tests,
    not illustrations. If one moves, a formula moved with it.
    """
    values, expected = GOLDEN[code]
    assert mx.compute_index(_shift_dict(values)) == expected


def test_the_index_flips_pushback_and_leaving_from_the_frozen_constructs():
    """`docs/07` §4 — less of each is better for the driver, and that is a construct property.

    Not a list in the code and not a config key: `constructs.index_sign` is frozen reference
    data, so
    a researcher cannot invert a metric's meaning by editing a file.
    """
    ref = reference()
    signs = {c.metric_name: c.index_sign for c in ref.constructs.values() if c.index_sign}
    assert signs["pushback"] == -1 and signs["leaving"] == -1
    assert signs["fairness"] == 1

    # A positive pushback shift (more pushback) lowers the index.
    worse = mx.compute_index(_shift_dict((0, 0, 0, 0, +1.0, 0)))
    better = mx.compute_index(_shift_dict((0, 0, 0, 0, -1.0, 0)))
    assert worse < 0 < better


def test_shifts_are_stored_signed_and_only_the_index_flips():
    """`docs/07` §4 — "Shifts are stored signed; the flip happens only in the index"."""
    baseline = {"T1": _answers(value_7=5), "T2": _answers(value_7=5)}
    variant = {"T1": _answers(value_7=6), "T2": _answers(value_7=6)}
    result = mx.compute_shifts(
        baseline_vectors=baseline, variant_vectors=variant, version_code="10000"
    )
    # pushback rose by +1 in the raw data, and it is stored as +1, not negated.
    assert result.shifts["pushback"] == pytest.approx(1.0)
    assert result.index_value is not None and result.index_value < 0


def test_a_zero_weight_omits_a_metric_and_all_zero_weights_raise():
    """`docs/07` §4.1 — the index is the weighted mean over the non-zero weights."""
    shifts = _shift_dict((+1.2, 0.0, 0.0, 0.0, 0.0, 0.0))
    assert mx.compute_index(shifts) == pytest.approx(0.2)
    only_fairness = mx.compute_index(shifts, weights={"fairness": 1.0, **dict.fromkeys(
        ("clarity", "happiness", "staying", "pushback", "leaving"), 0.0)})
    assert only_fairness == pytest.approx(1.2)

    with pytest.raises(mx.MetricError, match="no measurement"):
        mx.compute_index(shifts, weights=dict.fromkeys(METRIC_ORDER, 0.0))


def test_the_default_weights_are_unweighted_and_that_is_what_the_paper_reports():
    """`docs/07` §4.1."""
    config = load_analysis_config()
    assert set(config.weights) == set(METRIC_ORDER)
    assert set(config.weights.values()) == {1.0}
    assert config.decimals == 3

    with pytest.raises(ValueError, match="at least 30"):
        AnalysisConfig(bootstrap_samples=10)
    with pytest.raises(ValueError, match="negative index weight"):
        AnalysisConfig(weights={"fairness": -1.0})


# ---------------------------------------------------------------- the paired-sample rule


def test_shifts_use_one_twin_id_set_for_both_baseline_and_variant():
    """`docs/11` M8, verbatim — **assert with a fixture where one twin failed the cell.**

    `docs/07` §3.1: computing the baseline over the full panel and the variant over the survivors
    makes every failure look like an effect. This is the single most dangerous piece of
    arithmetic in
    the counterfactual layer.

    The fixture is built so the two readings differ: the twin that failed has an extreme
    baseline, so
    including it on the baseline side alone would move the shift a long way.
    """
    ref = reference()
    # T1, T2 answered the cell. T3 did NOT: it failed for this cell.
    baseline = {
        "T1": _answers(value_7=4),
        "T2": _answers(value_7=4),
        "T3": _answers(value_7=1),      # extreme, and must be excluded from BOTH sides
    }
    variant = {
        "T1": _answers(value_7=6),
        "T2": _answers(value_7=6),
    }

    result = mx.compute_shifts(
        baseline_vectors=baseline, variant_vectors=variant, version_code="10000"
    )

    assert result.twin_ids == ["T1", "T2"], "the failed twin must be excluded from both sides"
    assert result.twins_n == 2
    # Paired: baseline over T1,T2 only = 4; variant = 6; shift = +2.
    assert result.baselines["fairness"] == pytest.approx(4.0)
    assert result.shifts["fairness"] == pytest.approx(2.0)

    # The wrong arithmetic — baseline over all three — would have given 3.0 and a shift of +3.
    wrong_base = mx.mean_over_twins(baseline, list(baseline), "fairness", ref)
    assert wrong_base == pytest.approx(3.0)
    assert result.shifts["fairness"] != pytest.approx(6.0 - wrong_base)


def test_a_cell_no_twin_answered_raises_rather_than_scoring_zero():
    """I15 — a metric over zero twins is not 0.0, it is no measurement."""
    with pytest.raises(mx.MetricError, match="I15"):
        mx.compute_shifts(
            baseline_vectors={"T1": _answers()}, variant_vectors={}, version_code="10000"
        )


def test_repeats_are_averaged_within_twin_first():
    """`docs/07` §3.2 — a twin asked twice must not get double weight."""
    per_twin = mx.average_within_twin({
        "T1": [_answers(value_7=4), _answers(value_7=6)],
        "T2": [_answers(value_7=5)],
    })
    assert per_twin["T1"]["fairness"] == pytest.approx(5.0)
    assert per_twin["T2"]["fairness"] == pytest.approx(5.0)

    with pytest.raises(mx.MetricError, match="no vectors"):
        mx.average_within_twin({"T1": []})


# ---------------------------------------------------------------- the two floors


def test_the_two_floors_and_the_interpretability_test():
    """`docs/07` §6 — a cell that does not exceed the demand floor is not interpretable."""
    assert mx.demand_floor(0.31, 0.05) == pytest.approx(0.26)

    assert mx.below_floor(0.20, 0.26) is True
    assert mx.below_floor(0.40, 0.26) is False

    # Unknown is None, never False: "we did not measure the floor" and "this cell clears it" are
    # different claims and only one supports a finding.
    assert mx.demand_floor(None, 0.05) is None
    assert mx.below_floor(0.4, None) is None


def test_the_noise_floor_does_not_let_opposing_twins_cancel():
    """`docs/07` §6 — the defect that made every floor-judged validity test lean toward FAIL.

    Two twins move the same metric by the same amount in opposite directions. The **cell** has not
    moved, and the old floor — `|index(00000)|` — reported exactly that: `0.000`. But each twin
    moved a full point, and tests 4, 5 and 6 measure per-twin movement, so they were judged against
    a floor describing a quantity none of them computes.
    """
    ref = reference()
    battery = ref.battery_item_ids
    base = {item: 4 for item in battery}
    floor = mx.measure_noise_floor(
        baseline_vectors={"up": dict(base), "down": dict(base)},
        control_vectors={
            "up": {item: 5 for item in battery},
            "down": {item: 3 for item in battery},
        },
        ref=ref,
    )
    assert floor is not None
    assert floor.twins_n == 2
    # The cell did not move, on any metric: the two twins cancel exactly.
    assert floor.cell == pytest.approx(0.0, abs=1e-9)
    assert all(v == pytest.approx(0.0, abs=1e-9) for v in floor.cell_by_metric.values())
    # Every twin did move, on every metric. `happiness` moves by a third of a point rather than a
    # full one because `SAT2` is reverse coded, so a raw +1 on it scores -1 and cancels two of the
    # three SAT items — which is `docs/07` §2.1 working, not a defect in the floor.
    assert floor.twin == pytest.approx(0.8889, abs=5e-4)
    assert all(v > 0 for v in floor.twin_by_metric.values())
    assert floor.twin_by_metric["happiness"] == pytest.approx(1 / 3, abs=5e-4)
    assert floor.cell < floor.twin, "a cancelling floor must not be used to gate per-twin movement"
    # An unknown metric falls back to the overall figure, never to zero.
    assert floor.for_metric("not-a-metric", per_twin=True) == floor.twin
    assert floor.for_metric("happiness", per_twin=True) > floor.for_metric(
        "happiness", per_twin=False
    )


def test_a_floor_measured_on_nobody_is_not_a_floor():
    """`docs/07` §6, I15's shape — ``None``, never a zero that reads as "nothing moved"."""
    assert (
        mx.measure_noise_floor(baseline_vectors={}, control_vectors={"a": {}}, ref=reference())
        is None
    )


# ---------------------------------------------------------------- interactions and I17


def test_the_joint_cell_is_the_elementwise_maximum():
    """`docs/07` §5."""
    assert joint_code("01000", "00200") == "01200"
    assert joint_code("22222", "00000") == "22222"
    assert joint_code("10000", "20000") == "20000"


def test_an_interaction_reports_extra_and_a_verdict():
    """`docs/07` §5 — sub-additive means the two protections substitute for each other."""
    shifts = {
        "01000": {"staying": 0.31},
        "00010": {"staying": 0.09},
        "01010": {"staying": 0.22},
    }
    result = interaction("01000", "00010", "staying", shifts)
    assert isinstance(result, Interaction)
    assert result.joint == "01010"
    assert result.extra == pytest.approx(-0.18)
    assert result.verdict == "sub-additive"
    assert "less than the sum" in describe(result)

    shifts["01010"] = {"staying": 0.60}
    assert interaction("01000", "00010", "staying", shifts).verdict == "super-additive"
    shifts["01010"] = {"staying": 0.40}
    assert interaction("01000", "00010", "staying", shifts).verdict == "additive"


def test_interaction_returns_none_when_a_cell_is_missing_and_names_the_code_to_run():
    """`docs/11` M8, verbatim, and **I17**.

    `CLAUDE.md` rule 5: if an interaction needs three runs and has two, report which code to run.
    No estimates, no interpolation, no "approximately". The UI receives the code.
    """
    shifts = {"01000": {"staying": 0.31}, "00010": {"staying": 0.09}}
    result = interaction("01000", "00010", "staying", shifts)

    assert isinstance(result, MissingInteraction)
    assert not isinstance(result, Interaction)
    assert result.missing_codes == ["01010"]
    assert "01010" in describe_missing(result)
    assert "not estimated" in describe_missing(result)

    # A missing leg on either side is reported the same way.
    assert interaction("01000", "00010", "staying", {}).missing_codes == [
        "01000", "00010", "01010"
    ]
    # And a metric absent from an otherwise-present cell is missing too, not zero.
    partial = {"01000": {}, "00010": {"staying": 0.09}, "01010": {"staying": 0.22}}
    assert isinstance(interaction("01000", "00010", "staying", partial), MissingInteraction)


def test_legs_from_different_panels_raise_panel_mismatch():
    """`docs/07` §5 and I14 — three cells answered by three different twin sets are not an
    interaction."""
    shifts = {
        "01000": {"staying": 0.31},
        "00010": {"staying": 0.09},
        "01010": {"staying": 0.22},
    }
    panels = {
        "01000": frozenset({"T1", "T2"}),
        "00010": frozenset({"T1", "T2"}),
        "01010": frozenset({"T3", "T4"}),
    }
    with pytest.raises(PanelMismatch, match="different panels"):
        interaction("01000", "00010", "staying", shifts, panels_by_code=panels)

    same = dict(panels, **{"01010": frozenset({"T1", "T2"})})
    assert isinstance(
        interaction("01000", "00010", "staying", shifts, panels_by_code=same), Interaction
    )


def test_only_complete_interactions_reach_the_bundle():
    """`docs/02` §4.4 — the bundle may carry no number that was not computed (I17)."""
    shifts = {
        "01000": {"staying": 0.31},
        "00010": {"staying": 0.09},
        "01010": {"staying": 0.22},
        "00002": {"staying": 0.5},          # its joint with 01000 (01002) is absent
    }
    found = computable_interactions("01000", "staying", shifts)
    assert [i.joint for i in found] == ["01010"]
    assert all(isinstance(i, Interaction) for i in found)


# ---------------------------------------------------------------- the bundle


def _bundle(**overrides):
    shifts = CellShifts(
        version_code="21012",
        baselines={m: 4.0 for m in METRIC_ORDER},
        shifts=_shift_dict(GOLDEN["21012"][0]),
        index_value=GOLDEN["21012"][1],
        twin_ids=["T1", "T2", "T3"],
    )
    base = dict(
        shifts=shifts,
        fairwork_score=4,
        commitment_summary={"L1": ["Pay step 1"]},
        scenario_text=["Paragraph one.", "No change from today."],
        interactions=[],
        sham_floor=0.12,
    )
    return build_bundle(**{**base, **overrides})


def test_the_analyst_bundle_contains_no_number_absent_from_the_computed_metrics():
    """`docs/11` M8, verbatim, and I12.

    Every numeric token in the assembled prompt must be one the bundle vouches for — because
    `numeric_tokens()` is the allowed set the grounding check uses, and a number in the prompt
    that is
    not in that set is a number the analyst may legitimately echo and then be failed for.
    """
    from twinlab.agents.contract import grounded

    bundle = _bundle()
    prompt = build_user_prompt(bundle)
    allowed = bundle.numeric_tokens()

    # The prompt's own numbers are all vouched for — apart from the version code's digits, which
    # numeric_tokens() carries explicitly, and the "of 10" score denominator.
    unexplained = [t for t in grounded(prompt, allowed) if t != "10"]
    assert unexplained == [], (
        f"the prompt states numbers the bundle cannot vouch for: {unexplained}"
    )


def test_the_bundle_carries_the_blocks_docs_02_lists_in_order():
    """`docs/02` §4.4 — the same bundle, in the same order, the Results panel shows."""
    import re

    from twinlab.analysis.report import BLOCK_ORDER

    prompt = build_user_prompt(_bundle())
    assert [m.group(1) for m in re.finditer(r"<<<([A-Z]+)>>>", prompt)] == list(BLOCK_ORDER)
    assert "sham floor" in prompt
    assert "twins_n = 3" in prompt


def test_the_bundle_offers_no_interaction_that_was_not_computed():
    """I17 at the bundle boundary."""
    bundle = _bundle(interactions=[])
    assert bundle.interactions == []
    assert "none computable" in build_user_prompt(bundle)


# ---------------------------------------------------------------- grounding and the fallback


async def test_grounded_rejects_an_unlisted_number_retries_once_then_falls_back():
    """`docs/11` M8, verbatim, and `docs/02` §6.

    The retry quotes the **offending sentence**, so the model is told which claim is unsupported
    rather than merely that a digit was wrong somewhere.
    """
    cfg = default_agent_configs()["analyst"]
    bundle = _bundle()
    prompts: list[str] = []

    def handler(c, prompt, out):
        prompts.append(prompt)
        # Always ungrounded: 9.99 is in no bundle.
        return AnalysisResult(prose="The index rose to 9.99 overall.", confidence="high")

    client = StubModelClient(handler)
    result, used_fallback = await write_analysis(cfg, bundle, client)

    assert client.call_count("analyst") == 2, "one call plus exactly one targeted retry"
    assert "9.99" in prompts[1], "the retry must quote the offending number"
    assert "The index rose to 9.99 overall." in prompts[1], "and the offending sentence"

    assert used_fallback is True
    assert result.prose.startswith(FALLBACK_PREFIX)
    assert result.confidence == "low"


async def test_grounded_prose_is_kept_without_a_retry():
    """The happy path, so the fallback above means something."""
    cfg = default_agent_configs()["analyst"]
    bundle = _bundle()
    prose = f"The index is {bundle.index_value} over {bundle.twins_n} twins."

    client = StubModelClient(
        lambda c, p, o: AnalysisResult(prose=prose, confidence="high")
    )
    result, used_fallback = await write_analysis(cfg, bundle, client)

    assert client.call_count("analyst") == 1
    assert used_fallback is False
    assert result.prose == prose


async def test_a_retry_that_becomes_grounded_is_kept():
    """One bad attempt does not force the template: the retry is a real second chance."""
    cfg = default_agent_configs()["analyst"]
    bundle = _bundle()
    good = f"The index is {bundle.index_value}."
    replies = iter([
        AnalysisResult(prose="It rose to 9.99.", confidence="high"),
        AnalysisResult(prose=good, confidence="medium"),
    ])
    client = StubModelClient(lambda c, p, o: next(replies))
    result, used_fallback = await write_analysis(cfg, bundle, client)
    assert used_fallback is False
    assert result.prose == good


async def test_confidence_none_is_recorded_not_replaced():
    """`docs/02` §4.4 — a cell with no defensible reading gets no reading."""
    cfg = default_agent_configs()["analyst"]
    client = StubModelClient(
        lambda c, p, o: AnalysisResult(prose="", confidence="none", reason="twins_n too small")
    )
    result, used_fallback = await write_analysis(cfg, _bundle(), client)
    assert result.confidence == "none"
    assert used_fallback is False
    assert not result.prose.startswith(FALLBACK_PREFIX)


async def test_an_analyst_that_raises_falls_back_rather_than_failing_the_run():
    """`docs/02` §6.2 — a cell is never left without a reading."""
    cfg = default_agent_configs()["analyst"]

    def boom(c, p, o):
        raise RuntimeError("provider exploded")

    result, used_fallback = await write_analysis(cfg, _bundle(), StubModelClient(boom))
    assert used_fallback is True
    assert result.prose.startswith(FALLBACK_PREFIX)


def test_the_deterministic_template_is_grounded_by_construction():
    """`docs/02` §6.2 — the fallback cannot fail the check that produced it.

    It is written in Python from the same bundle, so every number in it is in the bundle.
    """
    from twinlab.agents.contract import grounded

    bundle = _bundle()
    prose = template_reading(bundle)
    assert prose.startswith(FALLBACK_PREFIX)
    unexplained = [t for t in grounded(prose, bundle.numeric_tokens()) if t != "10"]
    assert unexplained == []


def test_the_template_states_when_a_cell_is_not_interpretable():
    """`docs/07` §6 and `docs/02` §4.4 — the analyst is *required* to say so."""
    low = _bundle()
    low_shifts = low.model_copy(update={"index_value": 0.05, "sham_floor": 0.26})
    assert "not interpretable" in template_reading(low_shifts)

    high = low.model_copy(update={"index_value": 0.90, "sham_floor": 0.26})
    assert "exceeds the sham floor" in template_reading(high)

    unknown = low.model_copy(update={"sham_floor": None})
    assert "has not been measured" in template_reading(unknown)


def test_the_template_names_sub_additive_pairs():
    """`docs/02` §4.4 — name sub-additive pairs and what they suggest."""
    pair = Interaction(
        a="01000", b="00010", joint="01010", metric="staying",
        alone_a=0.31, alone_b=0.09, together=0.22, extra=-0.18, verdict="sub-additive",
    )
    prose = template_reading(_bundle(interactions=[pair]))
    assert "Sub-additive pairs" in prose
    assert "01000 with 00010" in prose
    assert "substitute" in prose
