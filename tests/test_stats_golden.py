"""M12 — the golden PLS-SEM dataset. `docs/07` §10, `docs/11` M12.

**This is the gate for every statistic in the paper.** Until it passes, no Statistics number is
reportable and the UI carries the `UNVALIDATED` banner (`docs/07` §10).

We cite `openpls-engine`'s published agreement with SmartPLS 4 (`ARCHITECTURE.md` §3.4). That
validates the engine; it cannot validate **our wiring of it**. `docs/07` §10 names the two faults
that wiring can carry, and both produce entirely plausible numbers:

* a construct bound to the wrong items, and
* a reverse-coded item not reversed before estimation.

Each gets a test here that proves the detector fires — `HANDOFF.md` §2.4: a gate that cannot fail
is not a gate.

The whole battery runs once per session; the module-scoped fixture is what keeps that to about a
minute rather than about ten.
"""

from __future__ import annotations

import pytest

from twinlab.stats import golden, plssem
from twinlab.stats.dataset import build_matrix
from twinlab.stats.spec import build_model_spec

TOL = golden.TOLERANCE


@pytest.fixture(scope="module")
def spec():
    return build_model_spec()


@pytest.fixture(scope="module")
def matrix(spec):
    return golden.golden_matrix(spec=spec)


@pytest.fixture(scope="module")
def results(matrix, spec):
    return plssem.run_all_stages(
        matrix, spec, samples=golden.GOLDEN_BOOTSTRAP, seed=golden.GOLDEN_SEED
    )


def _close(actual: float | None, expected: float | None, label: str) -> None:
    """|delta| < 0.001, with the label naming the statistic so a failure is self-explaining."""
    if expected is None:
        assert actual is None, f"{label}: expected no value, got {actual}"
        return
    assert actual is not None, f"{label}: expected {expected}, got nothing"
    delta = abs(actual - expected)
    assert delta < TOL, f"{label}: {actual} vs expected {expected} (|delta| = {delta:.6f})"


# --------------------------------------------------------------------- the fixture itself

def test_golden_matrix_is_unchanged(matrix):
    """The reference dataset has not moved. Asserted **before** any statistic.

    A changed fixture must report itself as a changed fixture. Without this, a fixture that
    drifted would surface as three hundred statistics failing at once and the cause would have to
    be inferred.
    """
    assert matrix.n_cases == golden.GOLDEN_N
    assert golden.matrix_digest(matrix) == golden.GOLDEN_DIGEST, (
        "the golden dataset changed. If that was deliberate, re-run "
        "tools/gen_golden.py --write and read the diff — every expected value moves with it."
    )


def test_golden_model_specification_is_unchanged(spec):
    """The model the expected values were computed under. `docs/07` §10.

    Pins the fingerprint, so moving an item between constructs, adding a path or changing the arm
    reference all fail here rather than quietly producing a different study's numbers.
    """
    assert spec.fingerprint() == golden.GOLDEN_FINGERPRINT


def test_golden_fixture_screens_nobody(matrix):
    """The fixture is clean by design, so a screening change cannot silently shrink the golden N."""
    assert matrix.dropped == ()
    assert matrix.legacy_excluded == 0


# --------------------------------------------------------------------- every statistic in §8

def test_reliability_matches(results):
    """`docs/07` §8.1 — Cronbach's alpha, rho_A, composite reliability and AVE, per construct."""
    expected = golden.EXPECTED["reliability"]
    actual = {r.construct_code: r for r in results["reliability"] if r.status != "na"}
    assert set(actual) == set(expected)
    for code, want in expected.items():
        row = actual[code]
        _close(row.cronbach_alpha, want["alpha"], f"{code} alpha")
        _close(row.rho_a, want["rho_a"], f"{code} rho_A")
        _close(row.rho_c, want["rho_c"], f"{code} rho_c")
        _close(row.ave, want["ave"], f"{code} AVE")


def test_discriminant_validity_matches(results):
    """`docs/07` §8.2 — HTMT per construct pair, and Fornell-Larcker's sqrt(AVE) diagonal."""
    expected = golden.EXPECTED["htmt"]
    actual = {f"{r.lv_a}|{r.lv_b}": r.htmt for r in results["discriminant"]["htmt"]}
    assert set(actual) == set(expected)
    for pair, want in expected.items():
        _close(actual[pair], want, f"HTMT {pair}")

    fl = {
        r.construct_code: r.sqrt_ave
        for r in results["discriminant"]["fornell_larcker"] if r.sqrt_ave is not None
    }
    for code, want in golden.EXPECTED["fornell_larcker"].items():
        _close(fl[code], want, f"sqrt(AVE) {code}")


def test_collinearity_matches(results):
    """`docs/07` §8.3 — inner VIF per predictor->criterion and outer VIF per indicator."""
    expected = golden.EXPECTED["vif"]
    actual = {f"{r.scope}|{r.target}|{r.predictor}": r.vif for r in results["collinearity"]}
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"VIF {key}")


def test_outer_loadings_match(results):
    """`docs/07` §8.4 — every indicator's outer loading."""
    expected = golden.EXPECTED["loadings"]
    actual = {f"{r.construct_code}|{r.item}": r.loading for r in results["outer_model"]}
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"loading {key}")


def test_path_coefficients_match(results):
    """`docs/07` §8.5 — every structural path's original-sample estimate."""
    expected = golden.EXPECTED["paths"]
    actual = {f"{r.source}->{r.target}": r.original_sample for r in results["paths"]}
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"path {key}")


def test_indirect_and_total_effects_match(results):
    """`docs/07` §8.6 — direct, indirect and total effects.

    Under the full mediation this project specifies, the arm reaches every behavioural intention
    **only** indirectly, so these rows carry the experimental claim.
    """
    expected = golden.EXPECTED["effects"]
    actual = {
        f"{r.kind}|{r.source}->{r.target}": r.estimate
        for r in results["indirect_total"]
        if r.kind in ("direct", "indirect", "total")
    }
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"effect {key}")


def test_explained_variance_matches(results):
    """`docs/07` §8.7 — R^2, adjusted R^2 and Q^2 per endogenous construct."""
    expected = golden.EXPECTED["explained"]
    actual = {r.construct_code: r for r in results["r2_f2_q2"]["explained"]}
    assert set(actual) == set(expected)
    for code, want in expected.items():
        _close(actual[code].r_squared, want["r2"], f"{code} R2")
        _close(actual[code].r_squared_adj, want["r2_adj"], f"{code} adjusted R2")
        _close(actual[code].q_squared, want["q2"], f"{code} Q2")


def test_f_squared_matches(results):
    """`docs/07` §8.7 — f^2 per structural path."""
    expected = golden.EXPECTED["f_squared"]
    actual = {f"{r.source}->{r.target}": r.f_squared for r in results["r2_f2_q2"]["f_squared"]}
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"f2 {key}")


def test_plspredict_matches(results):
    """`docs/07` §8.8 — Q2_predict and both RMSEs per endogenous indicator, and the verdict."""
    expected = golden.EXPECTED["plspredict"]
    actual = {
        f"{r.construct_code}|{r.indicator}": r for r in results["plspredict"]["rows"]
    }
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key].q2_predict, want["q2_predict"], f"Q2predict {key}")
        _close(actual[key].rmse_pls, want["rmse_pls"], f"RMSE_PLS {key}")
        _close(actual[key].rmse_lm, want["rmse_lm"], f"RMSE_LM {key}")
    assert results["plspredict"]["summary"].verdict == golden.EXPECTED["predict_verdict"]


def test_model_fit_matches(results):
    """`docs/07` §8.9 — SRMR and d_ULS. A fit index the engine does not provide stays `None`."""
    expected = golden.EXPECTED["model_fit"]
    actual = {r.statistic: r.value for r in results["model_fit"]}
    assert set(actual) == set(expected)
    for key, want in expected.items():
        _close(actual[key], want, f"fit {key}")


def test_every_stage_is_pinned(results):
    """All nine stages in `docs/01` §6.8 produced a payload; none is silently absent."""
    from twinlab.models.stats import STAGES

    assert set(results) == set(STAGES)


# --------------------------------------------------------------------- the two wiring faults

def test_catches_a_construct_bound_to_the_wrong_items(matrix):
    """`docs/07` §10, fault 1 — **the detector must fire.**

    `SAT1` and `CLAR1` swap constructs. Both constructs keep their item count, the model still
    estimates and every number still looks like a number. What must not survive is agreement with
    the pinned values.
    """
    miswired = golden.miswired_spec()
    assert miswired.fingerprint() != golden.GOLDEN_FINGERPRINT, (
        "swapping two items between constructs must move the model fingerprint"
    )

    pls = plssem.fit(matrix, miswired)
    actual = {
        r.construct_code: r.cronbach_alpha
        for r in plssem.stage_reliability(pls, matrix, miswired)
        if r.status != "na"
    }
    expected = golden.EXPECTED["reliability"]
    moved = [
        code
        for code in ("SATI", "TRAN")
        if abs((actual[code] or 0.0) - expected[code]["alpha"]) >= TOL
    ]
    assert moved == ["SATI", "TRAN"], (
        "a construct bound to the wrong items must move its reliability beyond tolerance; "
        f"only {moved} moved"
    )


def test_catches_a_reverse_coded_item_left_unreversed(spec):
    """`docs/07` §10, fault 2 — **the detector must fire.**

    Note the fault is injected into the *data*, not through a flag: reverse coding is
    unconditional in `dataset.build_matrix`, so there is no production code path that can skip it.

    `SATI` holds `SAT2` and `EDEP` holds `DEP1`; leaving either un-reversed makes that item
    correlate negatively with its block and collapses the construct's reliability.
    """
    submissions, answers = golden.unreversed_answers(spec=spec)
    broken = build_matrix(
        submissions, answers, population="real", screening="strict", spec=spec
    )
    pls = plssem.fit(broken, spec)
    actual = {
        r.construct_code: r.cronbach_alpha
        for r in plssem.stage_reliability(pls, broken, spec)
        if r.status != "na"
    }
    expected = golden.EXPECTED["reliability"]

    for code in ("SATI", "EDEP"):
        delta = abs((actual[code] or 0.0) - expected[code]["alpha"])
        assert delta >= TOL, (
            f"{code} carries a reverse-coded item; leaving it unreversed must move its alpha "
            f"beyond tolerance, but it moved by only {delta:.6f}"
        )
        assert (actual[code] or 0.0) < expected[code]["alpha"], (
            f"{code}'s reliability must fall, not rise, when its reverse-coded item is not "
            "reversed"
        )


def test_untouched_constructs_are_unaffected_by_the_reverse_coding_fault(spec):
    """The reverse-coding fault is **local**. A detector that fires everywhere localises nothing.

    `FAIR`, `TRAN`, `LOYA`, `VOIC` and `EXIT` carry no reverse-coded item, so their reliability
    must be identical — which is what makes the two that move diagnostic.
    """
    submissions, answers = golden.unreversed_answers(spec=spec)
    broken = build_matrix(
        submissions, answers, population="real", screening="strict", spec=spec
    )
    pls = plssem.fit(broken, spec)
    actual = {
        r.construct_code: r.cronbach_alpha
        for r in plssem.stage_reliability(pls, broken, spec)
        if r.status != "na"
    }
    for code in ("FAIR", "TRAN", "LOYA", "VOIC", "EXIT"):
        _close(actual[code], golden.EXPECTED["reliability"][code]["alpha"], f"{code} alpha")
