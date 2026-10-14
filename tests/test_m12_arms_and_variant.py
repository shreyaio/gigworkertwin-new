"""Per-arm contrasts, and the partial-mediation robustness check.

`docs/AUDIT_PROTOTYPE_PARITY.md` §A2 and §A1, both landed 2026-10-11.

**§A2.** The four arms used to enter as one Mode B composite of three dummies. A composite yields
one `ARM -> EXPO` coefficient, so the model produced **no per-arm contrast** — no estimate of the
form "MGT1 raised perceived fairness by x", which is the reportable output of a four-arm
between-subjects experiment. Three single-indicator constructs give three bootstrappable contrasts
against `BASE`.

**§A1.** The reported model imposes full mediation, dropping the direct justice->intention paths.
That was the researcher's deliberate choice (`docs/DECISIONS.md`), so `partial` exists as a
**declared robustness check**: the full model plus exactly three edges, nested, distinguishable by
fingerprint, and never the headline.
"""

from __future__ import annotations

import pytest

from twinlab.ingest.reference_store import reference
from twinlab.models.stats import ModelSpec
from twinlab.stats.dataset import build_matrix
from twinlab.stats.spec import (
    ANTECEDENT_TARGETS,
    ARM_PREFIX,
    ARM_REFERENCE,
    INTENTIONS,
    PARTIAL_MEDIATION_EDGES,
    build_model_spec,
)


@pytest.fixture
def ref():
    return reference()


@pytest.fixture
def spec(ref):
    return build_model_spec(ref)


def _arms(spec: ModelSpec):
    return [c for c in spec.constructs if c.code.startswith(ARM_PREFIX)]


# ------------------------------------------------------------------ A2: per-arm contrasts


def test_every_non_reference_arm_is_its_own_construct(spec, ref):
    """Three constructs for four arms. The reference gets none — that is what makes it reference."""
    arms = _arms(spec)
    assert len(arms) == len(ref.arms) - 1 == 3
    assert {c.code for c in arms} == {f"{ARM_PREFIX}{a}" for a in ref.arms if a != ARM_REFERENCE}
    assert f"{ARM_PREFIX}{ARM_REFERENCE}" not in spec.codes


def test_each_arm_construct_carries_exactly_one_dummy(spec):
    """One indicator each. This is what separates three contrasts from one composite score."""
    for construct in _arms(spec):
        assert construct.n_items == 1, f"{construct.code} is not a single-indicator construct"
    # Together they still cover every dummy the matrix builds, with no duplicates.
    items = [i for c in _arms(spec) for i in c.items]
    assert sorted(items) == sorted(set(items))
    assert len(items) == 3


def test_every_arm_has_its_own_path_to_every_antecedent_target(spec):
    """**The point of §A2.** Six coefficients where the composite had two.

    Each is separately estimated and separately bootstrapped, so the paths table carries a row per
    arm per target and the paper can report "MGT1 raised exposure by beta [CI]".
    """
    edges = {(e.source, e.target) for e in spec.edges}
    arms = _arms(spec)
    for construct in arms:
        for target in ANTECEDENT_TARGETS:
            assert (construct.code, target) in edges
    arm_edges = [e for e in spec.edges if e.source.startswith(ARM_PREFIX)]
    assert len(arm_edges) == len(arms) * len(ANTECEDENT_TARGETS) == 6


def test_the_arms_reach_no_construct_but_the_antecedent_targets(spec):
    """Full mediation applies to the arms too: nothing goes straight to an intention."""
    targets = {e.target for e in spec.edges if e.source.startswith(ARM_PREFIX)}
    assert targets == set(ANTECEDENT_TARGETS)
    for intention in INTENTIONS:
        assert intention not in targets


def test_arm_constructs_are_formative_so_reliability_reads_na(spec):
    """A single indicator has a loading of 1 and an AVE of 1 **by construction**.

    Reporting those as measurement quality would be meaningless, and `reflective=False` is how the
    existing stages already skip it — `stage_reliability` reports `na` with a reason,
    `stage_discriminant` and `stage_outer_model` leave it out. No stage needed a special case.
    """
    for construct in _arms(spec):
        assert construct.reflective is False
        assert construct.mode == "B"
        assert construct.scale_id is None


def test_the_nine_measured_constructs_are_untouched(spec, ref):
    """§A2 changes the structural model, not the measurement model."""
    reflective = {c.code for c in spec.constructs if c.reflective}
    assert reflective == set(ref.constructs)
    assert len(reflective) == 9


def test_the_matrix_builds_one_column_per_arm_dummy(spec, ref):
    """`build_matrix` reads the arm columns as a union across constructs, not one block's items."""
    submissions, answers = [], []
    for index, arm in enumerate(["BASE", "MGT1", "CON1", "REP1"]):
        sid = f"S{index}"
        submissions.append(
            {
                "submission_id": sid, "data_type": "REAL", "consented": True,
                "attention_passed": True, "completion_seconds": 900, "speeder": False,
                "straight_liner": False, "arm": arm,
            }
        )
        for construct in spec.constructs:
            if not construct.reflective:
                continue
            for position, item_id in enumerate(construct.items):
                points = ref.scale_points(item_id)
                answers.append(
                    {
                        "submission_id": sid, "item_id": item_id,
                        "value_num": 1 + ((index * 3 + position * 2) % points),
                        "legacy_scale": False,
                    }
                )

    matrix = build_matrix(submissions, answers, spec=spec, ref=ref)
    for arm in ("MGT1", "CON1", "REP1"):
        assert f"arm_{arm}" in matrix.columns
    assert f"arm_{ARM_REFERENCE}" not in matrix.columns

    # The reference respondent is all-zero across the dummies: that is how BASE is encoded.
    index_of = {name: i for i, name in enumerate(matrix.columns)}
    base_row = matrix.rows[matrix.submission_ids.index("S0")]
    assert {base_row[index_of[f"arm_{a}"]] for a in ("MGT1", "CON1", "REP1")} == {0.0}


def test_the_arm_dummies_are_not_perfectly_collinear(spec, ref):
    """Mutually exclusive dummies with the reference omitted sum to <= 1, never to 1.

    So the block is estimable and inner VIF stays modest. Asserted because the opposite — four
    dummies — would be a rank deficiency the engine reports as a shape complaint about a matrix the
    caller never built.
    """
    dummies = [i for c in _arms(spec) for i in c.items]
    assert len(dummies) == len(ref.arms) - 1


# ------------------------------------------------------------------ A1: the variant


def test_full_is_the_default_and_the_reported_model():
    """Nothing has to ask for the headline model; `partial` must be requested explicitly."""
    assert build_model_spec().fingerprint() == build_model_spec(variant="full").fingerprint()


def test_partial_adds_exactly_the_three_direct_paths():
    """Nested by construction: the full model **plus** three edges, and nothing else.

    That is what makes each added path's own bootstrap interval the test of that mediation
    restriction.
    """
    full = build_model_spec(variant="full")
    partial = build_model_spec(variant="partial")

    added = set((e.source, e.target) for e in partial.edges) - set(
        (e.source, e.target) for e in full.edges
    )
    assert added == set(PARTIAL_MEDIATION_EDGES)
    assert len(partial.edges) == len(full.edges) + 3
    # Nothing is removed, so the comparison is nested rather than a different model.
    assert set((e.source, e.target) for e in full.edges) <= set(
        (e.source, e.target) for e in partial.edges
    )


def test_partial_restores_the_algoactivism_path():
    """`FAIR -> VOIC` is the central claim of the literature, and the first reviewer question."""
    edges = {(e.source, e.target) for e in build_model_spec(variant="partial").edges}
    assert ("FAIR", "VOIC") in edges
    assert ("FAIR", "VOIC") not in {
        (e.source, e.target) for e in build_model_spec(variant="full").edges
    }


def test_partial_does_not_add_the_declined_interactions():
    """`docs/DECISIONS.md`: the researcher was asked and chose `EDEP x SATI` alone.

    Adding `EDEP x FAIR` or `EDEP x TRAN` here would quietly convert the robustness check into the
    partial-mediation model that was declined — the exact substitution that decision exists to
    prevent.
    """
    partial = build_model_spec(variant="partial")
    interactions = [c.code for c in partial.constructs if "_x_" in c.code]
    assert interactions == ["EDEP_x_SATI"]
    assert partial.interaction == ("EDEP", "SATI")


def test_the_two_variants_have_different_fingerprints():
    """`docs/07` §9 — a result under one can never be read as a result under the other."""
    full = build_model_spec(variant="full").fingerprint()
    partial = build_model_spec(variant="partial").fingerprint()
    assert full != partial


def test_both_variants_are_acyclic_and_identically_measured():
    """The added edges must not create a cycle, and must not touch the measurement model."""
    full = build_model_spec(variant="full")
    partial = build_model_spec(variant="partial")
    # `_assert_acyclic` runs inside `build_model_spec`; reaching here means both passed.
    assert {c.code: c.items for c in full.constructs} == {
        c.code: c.items for c in partial.constructs
    }
    assert full.indicators() == partial.indicators()
