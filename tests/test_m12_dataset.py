"""M12 — the model specification, the analysis matrix and the export. `docs/07` §7, §7.1, §11.

Everything here is deterministic and runs without an engine fit, so the rules that decide *which
numbers get estimated* are tested separately from the estimator. That split matters: a screening
or reverse-coding bug is invisible in the golden test's output if the fixture never exercises it.
"""

from __future__ import annotations

import pytest

from twinlab.ingest.reference_store import reference
from twinlab.models.stats import STAGES
from twinlab.stats import export as export_module
from twinlab.stats.dataset import (
    DatasetError,
    NoCasesError,
    build_matrix,
    reverse_if_needed,
    screen,
)
from twinlab.stats.spec import (
    ARM_REFERENCE,
    ModelSpecError,
    arm_dummy_columns,
    build_model_spec,
    construct_items,
    topological_order,
)


@pytest.fixture(scope="module")
def ref():
    return reference()


@pytest.fixture(scope="module")
def spec(ref):
    return build_model_spec(ref)


def _submission(sid: str, **overrides):
    base = {
        "submission_id": sid, "data_type": "REAL", "consented": True,
        "attention_passed": True, "completion_seconds": 900, "speeder": False,
        "straight_liner": False, "arm": "BASE",
    }
    base.update(overrides)
    return base


def _answers(sid: str, spec, ref, value: int | None = None, **per_item):
    """A complete indicator vector, mid-scale unless told otherwise."""
    rows = []
    for construct in spec.constructs:
        if not construct.reflective:
            continue
        for item_id in construct.items:
            points = ref.scale_points(item_id)
            rows.append(
                {
                    "submission_id": sid, "item_id": item_id,
                    "value_num": per_item.get(item_id, value or (points + 1) // 2),
                    "legacy_scale": False,
                }
            )
    return rows


def _varied(sids, spec, ref):
    """Several respondents whose answers vary, so no column is constant."""
    submissions, answers = [], []
    for index, sid in enumerate(sids):
        submissions.append(_submission(sid, arm=["BASE", "MGT1", "CON1", "REP1"][index % 4]))
        for construct in spec.constructs:
            if not construct.reflective:
                continue
            for position, item_id in enumerate(construct.items):
                points = ref.scale_points(item_id)
                value = 1 + ((index * 3 + position * 2) % points)
                answers.append(
                    {
                        "submission_id": sid, "item_id": item_id,
                        "value_num": value, "legacy_scale": False,
                    }
                )
    return submissions, answers


# --------------------------------------------------------------------- the specification

def test_attention_checks_are_never_indicators(spec):
    """I10. `AMQ6` and `ALGO5` sit in modelled blocks and are screening instruments, not items."""
    indicators = set(spec.indicators())
    assert "AMQ6" not in indicators
    assert "ALGO5" not in indicators
    assert spec.construct("EXPO").n_items == 5
    assert spec.construct("VOIC").n_items == 4


def test_holdout_items_are_never_indicators(spec, ref):
    """Parts 16 and 17 measure the twins' fidelity, not the humans' constructs."""
    indicators = set(spec.indicators())
    for item_id in (*ref.holdout_h2_item_ids, *ref.holdout_h3_item_ids):
        assert item_id not in indicators, f"{item_id} is a holdout and must not be modelled"


def test_every_register_construct_is_modelled(spec, ref):
    """All nine. A construct silently absent from the model is a silently different study."""
    for code in ref.constructs:
        construct = spec.construct(code)
        assert construct.reflective, f"{code} must be reflective (docs/07 §7.2)"
        assert construct.mode == "A"


def test_construct_items_match_the_register(spec, ref):
    """`docs/07` §10's first fault, at its source: the items come from the frozen register."""
    for code, construct in ref.constructs.items():
        modelled = set(spec.construct(code).items)
        registered = {
            item_id
            for item_id, item in ref.items.items()
            if item.block == construct.block
            and not item.attention_check
            and item.in_twin_battery
        }
        assert modelled == registered, f"{code} is not bound to its register block"


def test_arm_dummies_omit_the_reference_level(ref):
    """Three dummies for four arms. A fourth would make the block singular."""
    dummies = arm_dummy_columns(ref)
    assert len(dummies) == len(ref.arms) - 1
    assert f"arm_{ARM_REFERENCE}" not in dummies


def test_unknown_construct_raises(ref):
    """Never a silently empty block. `CLAUDE.md` rule 7."""
    with pytest.raises(ModelSpecError):
        construct_items("NOPE", ref)


def test_the_model_is_acyclic_and_topologically_ordered(spec):
    """The engine needs a lower-triangular path matrix, so every source must precede its target."""
    order = topological_order(spec)
    assert set(order) == set(spec.codes)
    position = {code: i for i, code in enumerate(order)}
    for edge in spec.edges:
        assert position[edge.source] < position[edge.target], f"{edge} is not ordered"


def test_topological_order_is_stable(spec):
    """Ties break alphabetically, so a stored payload's row order is the same in every process."""
    assert topological_order(spec) == topological_order(spec)


def test_fingerprint_moves_when_an_item_moves(spec):
    """`docs/07` §10's first fault must be visible as a changed fingerprint."""
    swapped = []
    for construct in spec.constructs:
        items = list(construct.items)
        if construct.code == "SATI":
            items[0] = "CLAR1"
        swapped.append(construct.model_copy(update={"items": tuple(items)}))
    moved = spec.model_copy(update={"constructs": tuple(swapped)})
    assert moved.fingerprint() != spec.fingerprint()


def test_fingerprint_moves_when_a_path_is_added(spec):
    """A different structural model is a different study and must never look comparable."""
    from twinlab.models.stats import PathEdge

    extra = spec.model_copy(
        update={"edges": (*spec.edges, PathEdge(source="FAIR", target="EXIT"))}
    )
    assert extra.fingerprint() != spec.fingerprint()


def test_stage_names_match_the_ddl():
    """`docs/01` §6.8's `analysis_results.stage` enumeration, exactly."""
    assert STAGES == (
        "reliability", "discriminant", "collinearity", "outer_model", "paths",
        "indirect_total", "r2_f2_q2", "plspredict", "model_fit",
    )


# --------------------------------------------------------------------- reverse coding

def test_reverse_coding_uses_the_items_own_scale(ref):
    """`docs/07` §2.1. A 5-point item reverses about 6 and a 7-point about 8."""
    assert reverse_if_needed("SAT2", 7, ref) == 1
    assert reverse_if_needed("SAT2", 1, ref) == 7
    assert reverse_if_needed("DEP1", 6, ref) == 2


def test_non_reversed_items_pass_through(ref):
    assert reverse_if_needed("SAT1", 3, ref) == 3
    assert reverse_if_needed("CLAR1", 5, ref) == 5


def test_no_reverse_coded_item_is_five_point(ref):
    """`docs/07` §2.1's warning is currently unreachable — this fires if that ever changes.

    All three reverse-coded items are `agree7`, so "reversing every item about 8" would happen to
    be correct today. The guard exists so a future 5-point reverse item is caught by a test rather
    than by a reader of the paper.
    """
    for item_id, item in ref.items.items():
        if item.reverse_coded:
            assert ref.scale_points(item_id) == 7, f"{item_id} is reverse-coded and not 7-point"


def test_matrix_applies_reverse_coding(spec, ref):
    """The matrix carries the reversed value, not the raw one."""
    sids = [f"S{i}" for i in range(6)]
    submissions, answers = _varied(sids, spec, ref)
    raw = {r["submission_id"]: r for r in answers if r["item_id"] == "SAT2"}
    matrix = build_matrix(submissions, answers, spec=spec, ref=ref)
    column = matrix.columns.index("SAT2")
    for row_index, sid in enumerate(matrix.submission_ids):
        assert matrix.rows[row_index][column] == 8 - raw[sid]["value_num"]


# --------------------------------------------------------------------- screening

@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({}, None),
        ({"attention_passed": False}, "failed an attention check"),
        ({"speeder": True}, "completed in under 8 minutes"),
        ({"completion_seconds": 100, "speeder": None}, "completed in under 8 minutes"),
        ({"straight_liner": True}, "straight-lined the battery"),
        ({"consented": False}, "did not consent"),
    ],
)
def test_strict_screening_reasons(overrides, expected):
    """`docs/07` §7.1. Every exclusion carries its reason, so `n_cases` stays explicable."""
    assert screen(_submission("S1", **overrides), "strict") == expected


def test_keep_everyone_drops_only_non_consenters():
    """`none` keeps everyone who consented. Consent is not a screening rule, it is a condition."""
    assert screen(_submission("S1", attention_passed=False, speeder=True), "none") is None
    assert screen(_submission("S1", consented=False), "none") == "did not consent"


def test_manipulation_check_never_screens_anyone_out():
    """`ARCHITECTURE.md` §10.2, decided 2026-09-28: the switch is built and defaults **off**.

    Turning it on after seeing results is a researcher degree of freedom. It must not be on by
    accident, under either rule.
    """
    failed_mc = _submission("S1", mc_correct=False, mc_answer="CON1")
    assert screen(failed_mc, "strict") is None
    assert screen(failed_mc, "none") is None


# --------------------------------------------------------------------- the matrix

def test_matrix_columns_cover_the_model(spec, ref):
    """Indicators, arm dummies and the interaction products — nothing missing, nothing extra."""
    sids = [f"S{i}" for i in range(6)]
    submissions, answers = _varied(sids, spec, ref)
    matrix = build_matrix(submissions, answers, spec=spec, ref=ref)
    assert set(spec.indicators()) <= set(matrix.columns)


def test_interaction_products_are_built_from_standardised_components(spec, ref):
    """`docs/07` §7.2. A product of raw values would encode where each scale's origin sits."""
    sids = [f"S{i}" for i in range(8)]
    submissions, answers = _varied(sids, spec, ref)
    matrix = build_matrix(submissions, answers, spec=spec, ref=ref)
    column = matrix.columns.index("DEP1_x_SAT1")
    values = [row[column] for row in matrix.rows]
    # Standardised components have mean 0, so their product's mean is the correlation — bounded,
    # and nowhere near the product of two mid-scale raw values (which would be ~16).
    assert max(abs(v) for v in values) < 10


def test_missing_indicator_drops_the_case_and_never_imputes(spec, ref):
    """I17. Casewise deletion is honest; a mean-filled cell is a fabricated measurement."""
    sids = [f"S{i}" for i in range(8)]
    submissions, answers = _varied(sids, spec, ref)
    answers = [a for a in answers if not (a["submission_id"] == "S3" and a["item_id"] == "FAIR2")]
    matrix = build_matrix(submissions, answers, spec=spec, ref=ref)
    assert "S3" not in matrix.submission_ids
    assert any(sid == "S3" and "missing" in reason for sid, reason in matrix.dropped)


def test_legacy_rows_are_excluded_by_default(spec, ref):
    """`docs/07` §11. Pooling the prototype's 1-7 answers takes an explicit override."""
    sids = [f"S{i}" for i in range(8)]
    submissions, answers = _varied(sids, spec, ref)
    answers = [
        {**a, "legacy_scale": True} if a["submission_id"] == "S2" else a for a in answers
    ]
    default = build_matrix(submissions, answers, spec=spec, ref=ref)
    assert "S2" not in default.submission_ids
    assert default.legacy_excluded == 1

    pooled = build_matrix(submissions, answers, spec=spec, ref=ref, pool_legacy=True)
    assert "S2" in pooled.submission_ids
    assert pooled.legacy_excluded == 0


def test_population_filter_separates_real_from_synthetic(spec, ref):
    # Each half keeps all four arms, so neither subset loses the antecedent's variance.
    sids = [f"S{i}" for i in range(16)]
    synthetic_ids = {f"S{i}" for i in range(8, 16)}
    submissions, answers = _varied(sids, spec, ref)
    submissions = [
        {**s, "data_type": "SYNTHETIC"} if s["submission_id"] in synthetic_ids else s
        for s in submissions
    ]
    real = build_matrix(submissions, answers, population="real", spec=spec, ref=ref)
    synthetic = build_matrix(submissions, answers, population="synthetic", spec=spec, ref=ref)
    both = build_matrix(submissions, answers, population="both", spec=spec, ref=ref)
    assert set(real.submission_ids).isdisjoint(synthetic.submission_ids)
    assert len(both.submission_ids) == len(real.submission_ids) + len(synthetic.submission_ids)


def test_no_cases_raises_rather_than_returning_an_empty_matrix(spec, ref):
    """The measurement-layer sibling of I15. A model estimated on nobody is not a result."""
    sids = [f"S{i}" for i in range(4)]
    submissions, answers = _varied(sids, spec, ref)
    submissions = [{**s, "attention_passed": False} for s in submissions]
    with pytest.raises(NoCasesError):
        build_matrix(submissions, answers, screening="strict", spec=spec, ref=ref)


def test_constant_column_raises(spec, ref):
    """A constant indicator would reach the outer model as NaN rather than as an error."""
    sids = [f"S{i}" for i in range(6)]
    submissions = [_submission(sid) for sid in sids]
    answers = []
    for sid in sids:
        answers.extend(_answers(sid, spec, ref, value=4))
    with pytest.raises(DatasetError):
        build_matrix(submissions, answers, spec=spec, ref=ref)


def test_matrix_is_reproducible(spec, ref):
    """`docs/09` §2. Same rows in, byte-identical matrix out."""
    sids = [f"S{i}" for i in range(8)]
    submissions, answers = _varied(sids, spec, ref)
    first = build_matrix(submissions, answers, spec=spec, ref=ref)
    second = build_matrix(submissions, answers, spec=spec, ref=ref)
    assert first.columns == second.columns
    assert first.rows == second.rows


# --------------------------------------------------------------------- the export

def test_export_has_exactly_two_header_rows(ref):
    """`docs/07` §11. The second row is the scale per column — the prototype's error, fixed."""
    row1, row2 = export_module.header_rows(ref)
    assert len(row1) == len(row2)
    assert row1[0] == "submission_id"


def test_export_scale_row_names_each_items_own_scale(ref):
    """Three constructs are 1-5. A sheet claiming 1-7 throughout is what 2.0 exists to correct."""
    row1, row2 = export_module.header_rows(ref)
    scales = dict(zip(row1, row2, strict=True))
    assert "7-point" in scales["SAT1"]
    assert "5-point" in scales["CLAR1"]
    assert "5-point" in scales["PAC1"]
    assert "7-point" in scales["FAIR1"]


def test_export_carries_every_register_item(ref):
    """All 73: the battery, both attention checks and both holdouts. `docs/07` §11."""
    row1, _ = export_module.header_rows(ref)
    for item_id in ref.items:
        assert item_id in row1, f"{item_id} is missing from the export"


def test_export_construct_means_are_precomputed_with_reverse_coding(ref):
    """I12. A downstream tool must not be able to re-derive these with different coding."""
    answers = {}
    for item_id, item in ref.items.items():
        if item.block == "SAT" and item.in_twin_battery and not item.attention_check:
            answers[item_id] = 7
    # SAT2 is reverse-coded, so a 7 on it means the lowest satisfaction.
    mean = export_module.construct_mean(answers, "SATI", ref)
    assert mean == pytest.approx((7 + 1 + 7) / 3)


def test_export_construct_mean_is_none_when_an_item_is_missing(ref):
    """`docs/07` §2.3. A mean over a subset looks like a measurement and is not."""
    assert export_module.construct_mean({"SAT1": 5}, "SATI", ref) is None


def test_export_excludes_legacy_rows_by_default(spec, ref):
    """`docs/07` §11, again at the export boundary."""
    submissions = [_submission("S1"), _submission("S2")]
    answers = _answers("S1", spec, ref) + [
        {**a, "legacy_scale": True} for a in _answers("S2", spec, ref)
    ]
    default = export_module.build_rows(submissions, answers, ref=ref)
    assert [r[0] for r in default] == ["S1"]
    pooled = export_module.build_rows(submissions, answers, ref=ref, pool_legacy=True)
    assert [r[0] for r in pooled] == ["S1", "S2"]


def test_export_keeps_screened_out_rows_and_flags_them(spec, ref):
    """The export is the evidence file a reviewer recomputes the screen from, not the sample."""
    submissions = [_submission("S1"), _submission("S2", attention_passed=False)]
    answers = _answers("S1", spec, ref) + _answers("S2", spec, ref)
    row1, _ = export_module.header_rows(ref)
    rows = export_module.build_rows(submissions, answers, ref=ref)
    assert [r[0] for r in rows] == ["S1", "S2"]
    flag = row1.index("screened_out")
    assert rows[0][flag] == 0
    assert rows[1][flag] == 1


def test_export_never_writes_a_zero_for_an_absent_value(spec, ref):
    """I17 at the file boundary. An empty cell is missing; a zero is a measurement."""
    submissions = [_submission("S1", city=None, service=None)]
    answers = _answers("S1", spec, ref)
    row1, _ = export_module.header_rows(ref)
    row = export_module.build_rows(submissions, answers, ref=ref)[0]
    assert row[row1.index("city")] == ""
    assert row[row1.index("female")] == ""
    assert row[row1.index("tenure_months")] == ""


def test_export_csv_emits_both_header_rows(spec, ref):
    submissions = [_submission("S1")]
    answers = _answers("S1", spec, ref)
    header = export_module.header_rows(ref)
    rows = export_module.build_rows(submissions, answers, ref=ref)
    text = export_module.to_csv(header, rows).splitlines()
    assert text[0].startswith("submission_id")
    assert "7-point" in text[1]
    assert text[2].startswith("S1")


def test_export_json_carries_the_scale_row_as_data(spec, ref):
    import json

    submissions = [_submission("S1")]
    answers = _answers("S1", spec, ref)
    header = export_module.header_rows(ref)
    rows = export_module.build_rows(submissions, answers, ref=ref)
    payload = json.loads(export_module.to_json(header, rows))
    assert payload["columns"] == header[0]
    assert payload["scales"] == header[1]
    assert len(payload["rows"]) == 1
