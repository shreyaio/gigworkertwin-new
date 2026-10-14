"""The eight validity tests. `docs/08` §4. Implements I15, serves I9, I12 and I17.

**Everything in this module is deterministic Python over stored integers.** No model is consulted
about whether a test passed, and no statistic here is produced by an LLM (I12). The functions take
numbers the service layer read out of the database and return a :class:`ValidityOutcome`; they do
not read, write, call a provider or know what a database is.

Four properties are research commitments rather than structure:

* **A test that ran on nobody is `INCONCLUSIVE`, never `PASS`** (I15). Every function here routes a
  zero-twin case through :func:`inconclusive`, and :class:`ValidityOutcome` refuses to be built any
  other way, so the failure cannot survive to the write.
* **Nothing is imputed** (I17). A twin whose two vectors do not overlap on a scorable item is
  dropped from the test, not scored as a maximal error and not filled from a neighbour. It is
  therefore also not counted in ``twins_n``: the reported n is twins actually measured.
* **A floor that was never measured is not assumed.** Tests 2, 4, 5, 6 and 8 all judge against the
  `00000` noise floor (`docs/07` §6). When the session has no `00000` control the verdict is
  `INCONCLUSIVE` — a cell reported against an assumed floor is reported against nothing.
* **Tests 1 and 3 make no model calls**, by construction: they take vectors that already exist and
  there is no client, agent or callable anywhere in their signatures.

Two of the eight also build an artefact that must never enter the study, and both are built here so
the flag travels with the object rather than with a caller's discipline — see
:func:`contradictory_probe` (test 4) and :func:`ablate_persona` (test 6).
"""

from __future__ import annotations

import math
import re

from twinlab.models.analysis import NoiseFloor
from twinlab.models.reference import LEVER_BY_POSITION, LEVER_NAMES
from twinlab.models.validity import (
    AblatedPersona,
    PairedGap,
    ProbeStimulus,
    TemperatureRecommendation,
    ValidityOutcome,
)

#: Test number → the stable `validity_results.test_id`. **Opaque stable keys** (`CLAUDE.md` rule 8):
#: they are cited by the results table and by the paper's validity section, so they are never
#: renumbered when a test's wording changes.
TEST_IDS: dict[int, str] = {
    1: "wrong_person",
    2: "placebo_change",
    3: "simple_guesses",
    4: "impossible_version",
    5: "order_and_wording",
    6: "ablation",
    7: "second_model",
    8: "temperature_sweep",
}

#: Test number → the one-line `detail` stored on every row, so `validity_results` is readable
#: without `docs/08` open (`docs/08` §5's last paragraph).
TEST_DETAIL: dict[int, str] = {
    1: "Scores each twin's H2 vector against its own driver and against a randomly paired other "
       "driver; reports the paired gap and its 95% interval.",
    2: "Shows SHAM — five paragraphs describing what Uber already does — and measures movement "
       "from baseline against the 00000 noise floor.",
    3: "Compares twin H2 error with two naive predictors on the same items: the human's own "
       "unchanged baseline, and that baseline plus the mean shift of other respondents in the arm.",
    4: "Shows a deliberately self-contradictory stimulus and checks that happiness does not rise "
       "and that few twins read it as an improvement.",
    5: "Shows the same version code twice — lever order reversed, then wording variant B — and "
       "measures the difference between the two presentations.",
    6: "Re-runs the twin with the fairness items removed from its persona and measures how far "
       "its fairness answers move, against a same-persona retest of the same twin.",
    7: "Asks the same twins the same cell on both models, same personas, and compares the "
       "per-twin index and every metric's sign.",
    8: "Runs the same twins on the same cell at three temperatures and reports the spread. This "
       "is what sets the twin temperature; it is measured, not chosen.",
}

#: `docs/08` §4's table, as calls **per twin**, so a budget is `factor x N`. Tests 1 and 3 are
#: **zero**, and `docs/11` M13 requires that to be asserted on the call counter rather than stated.
#:
#: Test 7 is **2**, not 1 (2026-10-08). `docs/08` §4 read "run a sample of twins on a different
#: model", which sounds like one extra round — but the implementation cannot reuse the sweep's
#: stored answers for model A: they were given under a different seed, possibly a different
#: wording, and `second_model` compares a *paired* per-twin index that is only paired if both
#: sides were asked the same way in the same test. So it asks **both** models, and the confirm
#: card must say so. It said 1, so a researcher approved N calls and spent 2N.
CALLS_PER_TWIN: dict[int, int] = {1: 0, 2: 1, 3: 0, 4: 1, 5: 2, 6: 3, 7: 2, 8: 3}

#: `docs/08` §4 test 1: the gap must reach half a scale point before it is a pass.
WRONG_PERSON_GAP_MIN = 0.5

#: `docs/08` §4 test 4: fewer than a quarter of twins may read the contradiction as an improvement.
IMPROVEMENT_SHARE_MAX = 0.25

#: `docs/08` §4 test 2: a twin whose mean movement exceeds half a point has moved.
MOVED_THRESHOLD = 0.5

#: `docs/08` §4 test 7: below this the correlation is `CHECK`, not `PASS`.
SECOND_MODEL_R_MIN = 0.7

#: The three temperatures `docs/08` §4 test 8 names. Not a range to be widened: the result sets the
#: study's temperature, and a sweep over a different grid measures a different thing.
TEMPERATURES: tuple[float, ...] = (0.0, 0.5, 1.0)

#: Student's t, two-sided 95%, by degrees of freedom. Small n is the normal case here — a panel of
#: twenty twins is df 19, where the normal approximation's 1.96 is about 6% too narrow and would
#: widen the set of gaps that "exclude zero". The last entry is the large-sample limit.
_T95: dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
    9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074,
    23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045,
    30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980,
}
_T95_LIMIT = 1.960

#: Below this an observed spread is float noise around zero, not a measured spread.
_NO_SPREAD = 1e-9


class ValidityInputError(ValueError):
    """Inputs a validity test refuses to interpret. Never worked around with a default."""


# --------------------------------------------------------------------------- small statistics


def t95(df: int) -> float:
    """The two-sided 95% critical value for ``df``, from the table above.

    Rounds **down** to the nearest tabulated df — the wider, more conservative interval — so an
    untabulated df never yields a narrower interval than the true one, which is the direction that
    would manufacture a `PASS`.
    """
    if df < 1:
        raise ValidityInputError(f"df is at least 1, got {df}")
    if df > max(_T95):
        return _T95_LIMIT
    return _T95[[k for k in sorted(_T95) if k <= df][-1]]


def mean(values: list[float]) -> float | None:
    """The mean, or ``None`` over nothing. Never ``0.0`` for an empty list (I15's shape)."""
    return sum(values) / len(values) if values else None


def sd(values: list[float]) -> float | None:
    """Sample standard deviation, or ``None`` when it is undefined (fewer than two values)."""
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def paired_gap(gaps: list[float]) -> PairedGap:
    """Mean paired difference with its 95% interval. `docs/08` §4 test 1.

    The interval is ``None`` rather than zero-width when it cannot be computed — one twin, or no
    spread at all. :attr:`PairedGap.excludes_zero` is then ``False``, so an uncomputable interval
    can never be read as evidence that the gap is real.
    """
    if not gaps:
        return PairedGap(n=0)
    m = sum(gaps) / len(gaps)
    spread = sd(gaps)
    # `_NO_SPREAD`, not `== 0.0`: identical gaps accumulate float error, so the SD of three 0.8s
    # is 1.1e-16 rather than zero. Left alone, that produces a degenerate interval of width ~0
    # that "excludes zero" — a PASS resting on no variance at all, which is the same failure
    # `pearson_r` returns None for (`docs/08` §3.3).
    if spread is None or spread <= _NO_SPREAD:
        return PairedGap(n=len(gaps), mean=round(m, 4), sd=0.0 if spread is not None else None)
    half = t95(len(gaps) - 1) * spread / math.sqrt(len(gaps))
    return PairedGap(
        n=len(gaps),
        mean=round(m, 4),
        sd=round(spread, 4),
        ci_lower=round(m - half, 4),
        ci_upper=round(m + half, 4),
    )


def mae(left: dict[str, int], right: dict[str, int], ids: list[str]) -> float | None:
    """Mean absolute error over the items **both** sides answered, or ``None``.

    Intersection, never union, and never imputed (I17): an item only one side holds is not scored
    as a maximal error and not filled from anywhere. ``None`` when nothing overlaps, so the caller
    drops the twin rather than recording a perfect score over no measurement.
    """
    errs = [abs(left[i] - right[i]) for i in ids if i in left and i in right]
    return sum(errs) / len(errs) if errs else None


def inconclusive(number: int, why: str, *, twins_n: int = 0) -> ValidityOutcome:
    """The verdict of a test that could not run. `docs/08` §5. **Not a pass.**"""
    return ValidityOutcome(
        test_id=TEST_IDS[number],
        twins_n=twins_n,
        statistics={},
        verdict="INCONCLUSIVE",
        headline=f"Could not run: {why}",
        detail=TEST_DETAIL[number],
    )


def _floor_or_inconclusive(number: int, noise_floor: NoiseFloor | None) -> ValidityOutcome | None:
    """The shared guard for every test judged against the `00000` floor (`docs/07` §6).

    A floor that was never measured is not assumed. `docs/07` §6 computes both floors per session
    from that session's own panel and never pools them across sessions, so there is no fallback
    value that would be about these twins.

    Since 2026-10-07 the floor is a :class:`~twinlab.models.analysis.NoiseFloor` carrying two
    levels, and **each test below selects the level matching its own statistic** rather than the
    caller choosing for it: whether a figure is a mean of absolutes or an absolute of a mean is a
    property of the test, so it is decided beside the test's own docstring.
    """
    if noise_floor is None:
        return inconclusive(
            number,
            "this session has no completed 00000 control, so there is no noise floor to judge "
            "against (docs/07 §6)",
        )
    return None


# --------------------------------------------------------------------------- 1. Wrong person


def wrong_person(
    *,
    own_errors: dict[str, float],
    other_errors: dict[str, float],
    between_person_distance: float | None = None,
    model: str = "",
) -> ValidityOutcome:
    """Test 1. **The most important of the eight.** `docs/08` §4 test 1.

    ``own_errors`` and ``other_errors`` are per-twin MAE against its own driver's 16 H2 answers and
    against a randomly paired other driver's. Both are computed by the caller from **stored
    vectors**: this test re-scores what already exists and makes no model call, which is why it has
    no client in its signature and why `docs/08` §4 says to run it early and often.

    ``gap = mae_other - mae_own``, paired across twins.

    * `PASS` — mean gap at least 0.5 points **and** its 95% interval excludes zero.
    * `CHECK` — gap positive but the interval includes zero.
    * `FAIL` — gap at or below zero: the twin is no more about its own driver than a stranger's.

    ``between_person_distance`` is the mean distance between the paired drivers' own answer
    vectors, and it is **reported, never used in the verdict**. It is the gap a flawless twin would
    score — ``mae_own = 0`` leaves ``gap = mae_other``, which cannot exceed how far apart the two
    humans are. The fixed 0.5-point threshold reads very differently against a sample whose drivers
    sit 3 points apart and one whose drivers sit 0.8 apart, and without this number on the row there
    is no way to tell those cases apart after the fact. Changing the threshold itself is a research
    decision and is not taken here.
    """
    twins = sorted(set(own_errors) & set(other_errors))
    if not twins:
        return inconclusive(
            1, "no twin has both an own-driver and a paired-driver score to compare"
        )

    gaps = [other_errors[t] - own_errors[t] for t in twins]
    gap = paired_gap(gaps)
    mean_own = mean([own_errors[t] for t in twins])
    mean_other = mean([other_errors[t] for t in twins])
    assert gap.mean is not None and mean_own is not None and mean_other is not None

    if gap.mean <= 0:
        verdict = "FAIL"
        headline = (
            f"Twins are no closer to their own driver than to a stranger's "
            f"(gap {gap.mean:+.2f} points)."
        )
    elif gap.mean >= WRONG_PERSON_GAP_MIN and gap.excludes_zero:
        verdict = "PASS"
        headline = (
            f"Own-driver error is {gap.mean:.2f} points lower "
            f"({mean_own:.2f} vs {mean_other:.2f}), and the interval excludes zero."
        )
    else:
        verdict = "CHECK"
        reason = (
            "below 0.5 points" if gap.mean < WRONG_PERSON_GAP_MIN else "the interval includes zero"
        )
        headline = f"Gap is {gap.mean:+.2f} points but {reason}."

    return ValidityOutcome(
        test_id=TEST_IDS[1],
        twins_n=len(twins),
        statistics={
            "mae_own": round(mean_own, 4),
            "mae_other": round(mean_other, 4),
            "gap": gap.mean,
            "gap_sd": gap.sd,
            "gap_ci_lower": gap.ci_lower,
            "gap_ci_upper": gap.ci_upper,
            # Reported, never thresholded. See the docstring.
            "between_person_distance": (
                None if between_person_distance is None else round(between_person_distance, 4)
            ),
            "gap_share_of_distance": (
                None
                if not between_person_distance
                else round(gap.mean / between_person_distance, 4)
            ),
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[1],
        models=[model] if model else [],
    )


# --------------------------------------------------------------------------- 2. Placebo change


def placebo_change(
    *,
    sham_shifts: dict[str, float],
    per_twin_abs_move: dict[str, float],
    noise_floor: NoiseFloor | None,
    median_live_shift: float | None = None,
    model: str = "",
    temperature: float | None = None,
) -> ValidityOutcome:
    """Test 2. **This test is the demand-characteristic floor**, measured. `docs/08` §4 test 2.

    ``sham_shifts`` is the six signed metric shifts of the `SHAM` cell; ``per_twin_abs_move`` is
    each twin's own mean absolute movement, which is what gives the share that moved.

    * `PASS` — mean |shift| within the `00000` noise floor: change-shaped text alone moves nobody.
    * `CHECK` — above the floor but under half the median live-cell shift.
    * `FAIL` — comparable to a live cell: the twins are reacting to *a change being announced*.

    Judged against :attr:`NoiseFloor.cell`. ``sham_shifts`` holds one **mean over twins** per
    metric, so the statistic is an absolute-of-a-mean, and the cell level is the floor built the
    same way.
    """
    blocked = _floor_or_inconclusive(2, noise_floor)
    if blocked is not None:
        return blocked
    assert noise_floor is not None
    if not sham_shifts or not per_twin_abs_move:
        return inconclusive(2, "no twin answered the SHAM cell")

    floor = noise_floor.cell
    mean_abs = sum(abs(v) for v in sham_shifts.values()) / len(sham_shifts)
    moved = sum(1 for v in per_twin_abs_move.values() if abs(v) > MOVED_THRESHOLD)
    share_moved = moved / len(per_twin_abs_move)
    half_live = None if median_live_shift is None else abs(median_live_shift) / 2

    if mean_abs <= floor:
        verdict = "PASS"
        headline = (
            f"SHAM moves the metrics {mean_abs:.3f} on average, within the "
            f"{floor:.3f} noise floor."
        )
    elif half_live is None:
        verdict = "CHECK"
        headline = (
            f"SHAM moves {mean_abs:.3f}, above the {floor:.3f} floor; no live cell has "
            "completed, so there is nothing to call it comparable to."
        )
    elif mean_abs < half_live:
        verdict = "CHECK"
        headline = (
            f"SHAM moves {mean_abs:.3f}, above the {floor:.3f} floor but under half the "
            "median live cell."
        )
    else:
        verdict = "FAIL"
        headline = (
            f"SHAM moves {mean_abs:.3f}, comparable to a live cell — twins welcome any change."
        )

    return ValidityOutcome(
        test_id=TEST_IDS[2],
        twins_n=len(per_twin_abs_move),
        statistics={
            "mean_abs_shift": round(mean_abs, 4),
            "share_moved": round(share_moved, 4),
            "noise_floor": round(floor, 4),
            "noise_floor_twins_n": float(noise_floor.twins_n),
            "median_live_shift": (
                None if median_live_shift is None else round(median_live_shift, 4)
            ),
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[2],
        models=[model] if model else [],
        temperature=temperature,
    )


# --------------------------------------------------------------- 3. Beating simple guesses


def simple_guesses(
    *,
    twin_errors: dict[str, float],
    nochange_errors: dict[str, float],
    groupshift_errors: dict[str, float],
    model: str = "",
) -> ValidityOutcome:
    """Test 3. `docs/08` §4 test 3. **No model call** — three stored error series compared.

    The two naive predictors are `docs/08` §4's own: **no change**, the human's unchanged baseline;
    and **group average shift**, that baseline plus the mean shift of the other respondents in the
    same arm.

    * `PASS` — the twin beats both.
    * `CHECK` — it beats one.
    * `FAIL` — it beats neither. **A twin that cannot beat "nothing changed" adds no information**,
      whatever its absolute MAE looks like.
    """
    twins = sorted(set(twin_errors) & set(nochange_errors) & set(groupshift_errors))
    if not twins:
        return inconclusive(
            3, "no twin has a score against all three predictors on the same items"
        )

    m_twin = mean([twin_errors[t] for t in twins])
    m_nochange = mean([nochange_errors[t] for t in twins])
    m_group = mean([groupshift_errors[t] for t in twins])
    assert m_twin is not None and m_nochange is not None and m_group is not None

    # Paired intervals on the same differences the verdict is taken from. The verdict stays a
    # comparison of means, which is what `docs/08` §4 specifies, but a FAIL on nine twins read
    # as a settled fact with nothing beside it saying how settled — and test 1, one screen away,
    # reports an interval for the same shape of quantity.
    vs_nochange = paired_gap([nochange_errors[t] - twin_errors[t] for t in twins])
    vs_group = paired_gap([groupshift_errors[t] - twin_errors[t] for t in twins])

    beats = int(m_twin < m_nochange) + int(m_twin < m_group)
    if beats == 2:
        verdict, headline = "PASS", (
            f"Twin error {m_twin:.3f} beats no-change {m_nochange:.3f} and group-shift "
            f"{m_group:.3f}."
        )
    elif beats == 1:
        beaten = "no-change" if m_twin < m_nochange else "group-shift"
        verdict, headline = "CHECK", (
            f"Twin error {m_twin:.3f} beats {beaten} only (no-change {m_nochange:.3f}, "
            f"group-shift {m_group:.3f})."
        )
    else:
        verdict, headline = "FAIL", (
            f"Twin error {m_twin:.3f} beats neither no-change {m_nochange:.3f} nor group-shift "
            f"{m_group:.3f}: the twins add no information."
        )

    return ValidityOutcome(
        test_id=TEST_IDS[3],
        twins_n=len(twins),
        statistics={
            "mae_twin": round(m_twin, 4),
            "mae_nochange": round(m_nochange, 4),
            "mae_groupshift": round(m_group, 4),
            "predictors_beaten": float(beats),
            "advantage_over_nochange": vs_nochange.mean,
            "advantage_over_nochange_ci_lower": vs_nochange.ci_lower,
            "advantage_over_nochange_ci_upper": vs_nochange.ci_upper,
            "advantage_over_groupshift": vs_group.mean,
            "advantage_over_groupshift_ci_lower": vs_group.ci_lower,
            "advantage_over_groupshift_ci_upper": vs_group.ci_upper,
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[3],
        models=[model] if model else [],
    )


# ------------------------------------------------------------------- 4. Impossible version


def contradictory_probe(
    *,
    probe_id: str = "probe-contradiction-v1",
    ordinary_paragraphs: dict[str, str] | None = None,
) -> ProbeStimulus:
    """Build test 4's stimulus. `docs/08` §4 test 4.

    **It bypasses the lookup (I1) and the Checker (I3) by construction**, because a contradiction
    is exactly what the Checker rejects — so it is written by this fixture rather than rendered,
    and it is a :class:`ProbeStimulus`, which has no ``version_code`` field for any store or screen
    to file it under. `docs/11` M13: never written to `variants`, unreachable from the Dial board.
    """
    ordinary = dict(ordinary_paragraphs or {})
    paragraphs: dict[str, str] = {}
    for lever in LEVER_BY_POSITION:
        if lever == "L1":
            paragraphs[lever] = (
                "Uber will guarantee every driver a minimum payment for each hour they are "
                "logged in, and at the same time will reduce the amount paid for every trip so "
                "that the same work earns less than it does today."
            )
        else:
            paragraphs[lever] = ordinary.get(
                lever, f"{LEVER_NAMES[lever]}: no change from today."
            )
    return ProbeStimulus(
        probe_id=probe_id,
        paragraphs=paragraphs,
        contradiction=(
            "a guaranteed minimum wage and a pay cut for the same work, announced together"
        ),
    )


def impossible_version(
    *,
    happiness_shift: float | None,
    per_twin_happiness_shift: dict[str, float],
    noise_floor: NoiseFloor | None,
    model: str = "",
    temperature: float | None = None,
) -> ValidityOutcome:
    """Test 4. `docs/08` §4 test 4.

    "Materially" and "a clear improvement" are both judged against the `00000` noise floor rather
    than against a number invented here: `docs/07` §6 already defines how much movement means
    nothing, and a second definition would be a second, unvalidated threshold.

    **The two statistics are judged at two different levels, which is the point of
    :class:`~twinlab.models.analysis.NoiseFloor`.** ``happiness_shift`` is a mean over twins, so it
    takes the cell-level happiness floor. ``share_improved`` asks of **each twin** whether it moved
    up, so its threshold is the per-twin happiness floor — how far one twin's happiness moves when
    nothing changed. Against a cell-level floor, which cancels toward zero, the question degrades
    to "did this twin move up at all", whose answer is ~50% under any noise and which no panel can
    get below 25%. `docs/08` §4 says "a **clear** improvement", and the per-twin floor is what the
    word "clear" refers to.

    * `PASS` — happiness does not rise beyond the floor **and** fewer than 25% of twins read it as
      an improvement.
    * `FAIL` — it reads as an ordinary improvement.
    """
    blocked = _floor_or_inconclusive(4, noise_floor)
    if blocked is not None:
        return blocked
    assert noise_floor is not None
    if not per_twin_happiness_shift or happiness_shift is None:
        return inconclusive(4, "no twin answered the contradictory probe")

    cell_floor = noise_floor.for_metric("happiness", per_twin=False)
    twin_floor = noise_floor.for_metric("happiness", per_twin=True)
    improved = sum(1 for v in per_twin_happiness_shift.values() if v > twin_floor)
    share = improved / len(per_twin_happiness_shift)

    if happiness_shift <= cell_floor and share < IMPROVEMENT_SHARE_MAX:
        verdict = "PASS"
        headline = (
            f"Happiness moves {happiness_shift:+.3f} against a {cell_floor:.3f} floor and "
            f"{share:.0%} of twins read the contradiction as a clear improvement."
        )
    else:
        verdict = "FAIL"
        headline = (
            f"The contradiction reads as an improvement: happiness {happiness_shift:+.3f}, "
            f"{share:.0%} of twins improved."
        )

    return ValidityOutcome(
        test_id=TEST_IDS[4],
        twins_n=len(per_twin_happiness_shift),
        statistics={
            "happiness_shift": round(happiness_shift, 4),
            "share_improved": round(share, 4),
            "noise_floor": round(cell_floor, 4),
            "noise_floor_per_twin": round(twin_floor, 4),
            "noise_floor_twins_n": float(noise_floor.twins_n),
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[4],
        models=[model] if model else [],
        temperature=temperature,
    )


# ------------------------------------------------------------- 5. Order and wording swap


def order_and_wording(
    *,
    diff_per_metric: dict[str, float],
    twins_n: int,
    noise_floor: NoiseFloor | None,
    cell_own_shift: float | None = None,
    model: str = "",
    temperature: float | None = None,
) -> ValidityOutcome:
    """Test 5. `docs/08` §4 test 5.

    ``diff_per_metric`` is the mean absolute difference per metric between the two presentations of
    the same version code — lever order reversed, then wording variant B.

    A failure here means paragraph position or phrasing is a confound, which would undermine every
    lever comparison — and is why lever order is randomised per round in the first place
    (`docs/03` §8).

    Judged against :attr:`NoiseFloor.twin`. ``diff_per_metric`` is built by taking each twin's own
    ``|A - B|`` and averaging those, so it never cancels; the cell-level floor does, and comparing
    the two put a mean-of-absolutes against an absolute-of-a-mean.
    """
    blocked = _floor_or_inconclusive(5, noise_floor)
    if blocked is not None:
        return blocked
    assert noise_floor is not None
    if twins_n == 0 or not diff_per_metric:
        return inconclusive(5, "no twin answered both presentations of the cell")

    floor = noise_floor.twin
    mean_diff = sum(abs(v) for v in diff_per_metric.values()) / len(diff_per_metric)
    own = None if cell_own_shift is None else abs(cell_own_shift)

    if mean_diff <= floor:
        verdict = "PASS"
        headline = (
            f"Presentation moves the metrics {mean_diff:.3f}, within the {floor:.3f} "
            "noise floor."
        )
    elif own is None:
        verdict = "CHECK"
        headline = (
            f"Presentation moves {mean_diff:.3f}, above the {floor:.3f} floor; the cell's "
            "own shift is not known, so it cannot be called comparable."
        )
    elif mean_diff < own / 2:
        verdict = "CHECK"
        headline = (
            f"Presentation moves {mean_diff:.3f}, above the floor but under half the cell's own "
            f"{own:.3f} shift."
        )
    else:
        verdict = "FAIL"
        headline = (
            f"Presentation moves {mean_diff:.3f}, comparable to the cell's own {own:.3f} shift: "
            "wording or position is a confound."
        )

    return ValidityOutcome(
        test_id=TEST_IDS[5],
        twins_n=twins_n,
        statistics={
            "mean_abs_difference": round(mean_diff, 4),
            "noise_floor": round(floor, 4),
            "noise_floor_twins_n": float(noise_floor.twins_n),
            "cell_own_shift": None if own is None else round(own, 4),
            **{f"diff_{k}": round(abs(v), 4) for k, v in sorted(diff_per_metric.items())},
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[5],
        models=[model] if model else [],
        temperature=temperature,
    )


# ---------------------------------------------------------------------------- 6. Ablation

#: Words the persona builder uses in its fairness section. The passage is matched on the section's
#: *vocabulary* rather than on item ids, because by I7 it carries no item ids and no numerals.
_FAIRNESS_WORDS = ("fair", "unfair", "fairly", "fairness", "treated me", "treats me")


def _mentions_fairness(sentence: str, block: str) -> bool:
    lowered = sentence.lower()
    return block.lower() in lowered or any(w in lowered for w in _FAIRNESS_WORDS)


def ablate_persona(
    *, twin_id: str, persona_text: str, fairness_item_ids: list[str], fairness_block: str = "FAIR"
) -> AblatedPersona:
    """Remove the fairness clauses from a persona. `docs/08` §4 test 6.

    **This passage violates I6's losslessness on purpose, and the violation is the experiment.**
    It is returned as an :class:`AblatedPersona`, which is not a
    :class:`~twinlab.models.twin.PersonaPassage` and carries no ``persona_hash`` — so there is
    nothing here that `twins.persona_hash` could be written from, and no function expecting a real
    passage will accept it.

    The ablation is by sentence, because the builder emits one clause per battery item. Removing
    nothing **raises** rather than returning the original: an "ablation" that ablated nothing would
    make test 6 compare a twin with itself and report `CHECK` forever.
    """
    if not fairness_item_ids:
        raise ValidityInputError(
            "no fairness items given, so there is nothing to ablate. An ablation that removes "
            "nothing compares a twin with itself (docs/08 §4 test 6)."
        )
    keep: list[str] = []
    removed: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", persona_text):
        if _mentions_fairness(sentence, fairness_block):
            removed.append(sentence)
        else:
            keep.append(sentence)
    if not removed:
        raise ValidityInputError(
            f"nothing in this persona reads as a {fairness_block} clause, so the ablation would "
            "be a no-op and test 6 would compare a twin with itself"
        )
    return AblatedPersona(
        twin_id=twin_id,
        text=" ".join(keep).strip(),
        removed_items=list(fairness_item_ids),
    )


def ablation(
    *,
    fairness_with: dict[str, float],
    fairness_without: dict[str, float],
    fairness_retest: dict[str, float] | None = None,
    noise_floor: NoiseFloor | None,
    model: str = "",
    temperature: float | None = None,
) -> ValidityOutcome:
    """Test 6. `docs/08` §4 test 6. **No `FAIL` verdict exists for this test**, by specification.

    * `PASS` — the fairness answers move materially: the twin was using its own history.
    * `CHECK` — barely different, so the fairness answer may be a stock response.

    **``fairness_retest`` is the control this test was missing** (2026-10-07,
    `docs/DECISIONS.md`). ``fairness_with`` and ``fairness_without`` come from two *separate* model
    calls, so their difference contains the twin's own call-to-call variance as well as any
    sensitivity to the ablation. Without a same-persona retest there is nothing to subtract that
    off against, and the test cannot distinguish "the twin used its fairness history" from "two
    calls to one twin differ" — it would report `PASS` for a twin that ignored the persona
    entirely. The comparator is therefore ``max(retest, floor)``: the ablation has to beat both the
    twin's own noise and the panel's.

    It stays optional so a stored outcome from before the control existed can still be
    reconstructed; when it is absent the headline says the test ran without its control rather than
    implying the comparison was made.

    Judged against :attr:`NoiseFloor.twin` for ``fairness``: the statistic is a mean over twins of
    each twin's own absolute difference, and it is one metric, not six.
    """
    blocked = _floor_or_inconclusive(6, noise_floor)
    if blocked is not None:
        return blocked
    assert noise_floor is not None
    twins = sorted(set(fairness_with) & set(fairness_without))
    if not twins:
        return inconclusive(6, "no twin answered both with and without its fairness clauses")

    floor = noise_floor.for_metric("fairness", per_twin=True)
    m = mean([abs(fairness_with[t] - fairness_without[t]) for t in twins])
    assert m is not None

    retested = sorted(set(fairness_with) & set(fairness_retest or {}))
    retest = (
        mean([abs(fairness_with[t] - fairness_retest[t]) for t in retested])  # type: ignore[index]
        if retested
        else None
    )
    # `max`, never a sum or a subtraction: the two are alternative explanations of the same
    # difference, not components of it, and subtracting one from the other would report a
    # difference nobody measured.
    threshold = floor if retest is None else max(floor, retest)

    if m > threshold:
        verdict = "PASS"
        beat = (
            f"the {floor:.3f} floor"
            if retest is None
            else f"the {floor:.3f} floor and the twin's own {retest:.3f} retest difference"
        )
        headline = (
            f"Removing the fairness items moves the fairness answer {m:.3f}, beyond {beat}: the "
            "twin was using its own history."
        )
    else:
        verdict = "CHECK"
        against = (
            f"the {floor:.3f} floor"
            if retest is None
            else f"a {retest:.3f} retest difference on the same persona"
        )
        headline = (
            f"Removing the fairness items moves the answer only {m:.3f}, within {against}: "
            "possibly a stock response."
        )
    if retest is None:
        headline += (
            " (No same-persona retest was available, so call-to-call variance is not ruled out.)"
        )

    return ValidityOutcome(
        test_id=TEST_IDS[6],
        twins_n=len(twins),
        statistics={
            "mean_abs_difference": round(m, 4),
            "retest_difference": None if retest is None else round(retest, 4),
            "retest_twins_n": float(len(retested)),
            "noise_floor": round(floor, 4),
            "noise_floor_twins_n": float(noise_floor.twins_n),
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[6],
        models=[model] if model else [],
        temperature=temperature,
    )


# ------------------------------------------------------------------------ 7. A second model


def second_model(
    *,
    index_a: dict[str, float],
    index_b: dict[str, float],
    shifts_a: dict[str, float],
    shifts_b: dict[str, float],
    model_a: str,
    model_b: str,
    temperature: float | None = None,
) -> ValidityOutcome:
    """Test 7. `docs/08` §4 test 7. **A sign flip is the failure that matters.**

    Different magnitudes across models are expected; different *directions* mean the finding is a
    property of one model rather than of the drivers. The flip is therefore checked **first**, so a
    high correlation can never carry a flipped metric to `PASS`.

    Both model names are recorded on the row, which `docs/11` M13 requires.
    """
    from twinlab.validity.quality import pearson_r

    twins = sorted(set(index_a) & set(index_b))
    if not twins:
        return inconclusive(7, f"no twin answered the same cell on both {model_a} and {model_b}")

    r = pearson_r([index_a[t] for t in twins], [index_b[t] for t in twins])
    metrics = sorted(set(shifts_a) & set(shifts_b))
    flipped = [m for m in metrics if shifts_a[m] * shifts_b[m] < 0]
    mean_diff = mean([abs(shifts_a[m] - shifts_b[m]) for m in metrics])

    if flipped:
        verdict = "FAIL"
        headline = (
            f"{', '.join(flipped)} flips sign between {model_a} and {model_b}: the finding is a "
            "property of one model."
        )
    elif r is not None and r >= SECOND_MODEL_R_MIN:
        verdict = "PASS"
        headline = (
            f"Per-twin index correlates r={r:.2f} between {model_a} and {model_b} and every "
            "metric keeps its sign."
        )
    else:
        verdict = "CHECK"
        shown = "undefined" if r is None else f"{r:.2f}"
        headline = f"Signs agree between {model_a} and {model_b} but the correlation is {shown}."

    return ValidityOutcome(
        test_id=TEST_IDS[7],
        twins_n=len(twins),
        statistics={
            "index_r": None if r is None else round(r, 4),
            "mean_abs_metric_difference": None if mean_diff is None else round(mean_diff, 4),
            "metrics_compared": float(len(metrics)),
            "signs_flipped": float(len(flipped)),
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[7],
        models=[model_a, model_b],
        temperature=temperature,
    )


# ------------------------------------------------------------------- 8. Temperature sweep


def recommend_temperature(
    *, index_by_temp: dict[float, dict[str, float]], max_metric_spread: float | None
) -> TemperatureRecommendation:
    """The temperature the sweep supports. `docs/02` §7.3, `docs/08` §4 test 8.

    **The lowest temperature whose between-twin index SD is still above zero.** That is the rule
    `docs/08` §4 test 8 states in words and nothing more: lower is preferred, because sampling
    variance is noise the design does not want — but *"a twin at 0.0 may collapse to modal answers
    and lose the between-twin variance the design depends on"*, so a temperature at which the twins
    no longer differ from each other is not a candidate at all. There is deliberately no free
    parameter: a tuned cut-off would be a threshold nobody validated.

    It is a **recommendation**. Applying it to `TwinConfig.temperature` is the researcher's
    deliberate act, because the value is frozen onto every session's config and a silent change
    would make two sessions incomparable with nothing in the data saying why.
    """
    spreads = {
        f"{t:.1f}": round(sd(list(v.values())) or 0.0, 4)
        for t, v in sorted(index_by_temp.items())
    }
    candidates = [float(t) for t, s in spreads.items() if s > 0]
    if not candidates:
        return TemperatureRecommendation(
            recommended=None,
            between_twin_sd=spreads,
            max_metric_spread=max_metric_spread,
            reason=(
                "at every temperature tried the twins gave the same index, so there is no "
                "setting that preserves between-twin variance. Nothing is recommended."
            ),
        )
    chosen = min(candidates)
    return TemperatureRecommendation(
        recommended=chosen,
        between_twin_sd=spreads,
        max_metric_spread=max_metric_spread,
        reason=(
            f"{chosen:.1f} is the lowest temperature at which the twins still differ from each "
            f"other (between-twin index SD {spreads[f'{chosen:.1f}']:.3f}). Lower settings "
            "collapsed to modal answers; higher ones add sampling variance without adding spread."
        ),
    )


def temperature_sweep(
    *,
    index_by_temp: dict[float, dict[str, float]],
    shifts_by_temp: dict[float, dict[str, float]],
    noise_floor: NoiseFloor | None,
    model: str = "",
) -> tuple[ValidityOutcome, TemperatureRecommendation]:
    """Test 8. `docs/08` §4 test 8. **This test sets the twin temperature; it is not chosen.**

    Returns the outcome *and* the recommendation, because the recommendation is the point of the
    test and must not have to be reconstructed later from the stored statistics.

    `docs/08` §4 test 8 states a `pass` rule and "report: always", and names no `FAIL`. A spread
    above the floor is therefore `CHECK`: it is information about sampling variance, not a verdict
    that the study is invalid.

    Judged against :attr:`NoiseFloor.cell`: ``shifts_by_temp`` holds one mean per metric per
    temperature, so the spread is a range over cell-level means.
    """
    nothing = TemperatureRecommendation(
        recommended=None,
        between_twin_sd={},
        max_metric_spread=None,
        reason="the sweep did not produce comparable runs, so no temperature is recommended.",
    )
    blocked = _floor_or_inconclusive(8, noise_floor)
    if blocked is not None:
        return blocked, nothing
    assert noise_floor is not None

    populated = [set(v) for v in index_by_temp.values() if v]
    twins = sorted(set.intersection(*populated)) if len(populated) == len(index_by_temp) else []
    if len(index_by_temp) < 2 or not twins:
        return (
            inconclusive(
                8,
                "the same twins must answer at two or more temperatures before a spread means "
                "anything",
            ),
            nothing,
        )

    metrics = sorted(set.intersection(*(set(v) for v in shifts_by_temp.values())))
    per_metric_spread = {
        m: max(shifts_by_temp[t][m] for t in shifts_by_temp)
        - min(shifts_by_temp[t][m] for t in shifts_by_temp)
        for m in metrics
    }
    max_spread = max(per_metric_spread.values()) if per_metric_spread else None
    # Each twin's own SD across the temperatures — how much one twin wobbles, which is a different
    # question from how much the twins differ from each other.
    mean_within = mean(
        [sd([index_by_temp[t][twin] for t in sorted(index_by_temp)]) or 0.0 for twin in twins]
    )

    recommendation = recommend_temperature(
        index_by_temp=index_by_temp, max_metric_spread=max_spread
    )

    floor = noise_floor.cell
    if max_spread is not None and max_spread <= floor:
        verdict = "PASS"
        headline = (
            f"Metric spread across {len(index_by_temp)} temperatures is {max_spread:.3f}, within "
            f"the {floor:.3f} noise floor."
        )
    else:
        verdict = "CHECK"
        shown = "not measured" if max_spread is None else f"{max_spread:.3f}"
        headline = (
            f"Metric spread across temperatures is {shown}, above the {floor:.3f} noise "
            "floor: some of the movement is sampling variance."
        )
    if recommendation.recommended is not None:
        headline += f" Recommended temperature {recommendation.recommended:.1f}."

    outcome = ValidityOutcome(
        test_id=TEST_IDS[8],
        twins_n=len(twins),
        statistics={
            "max_metric_spread": None if max_spread is None else round(max_spread, 4),
            "mean_within_twin_index_sd": None if mean_within is None else round(mean_within, 4),
            "noise_floor": round(floor, 4),
            "noise_floor_twins_n": float(noise_floor.twins_n),
            "recommended_temperature": recommendation.recommended,
            **{f"spread_{k}": round(v, 4) for k, v in sorted(per_metric_spread.items())},
            **{f"between_twin_sd_{k}": v for k, v in recommendation.between_twin_sd.items()},
        },
        verdict=verdict,
        headline=headline,
        detail=TEST_DETAIL[8],
        models=[model] if model else [],
    )
    return outcome, recommendation


__all__ = [
    "CALLS_PER_TWIN",
    "IMPROVEMENT_SHARE_MAX",
    "MOVED_THRESHOLD",
    "SECOND_MODEL_R_MIN",
    "TEMPERATURES",
    "TEST_DETAIL",
    "TEST_IDS",
    "WRONG_PERSON_GAP_MIN",
    "ValidityInputError",
    "ablate_persona",
    "ablation",
    "contradictory_probe",
    "impossible_version",
    "inconclusive",
    "mae",
    "mean",
    "order_and_wording",
    "paired_gap",
    "placebo_change",
    "recommend_temperature",
    "sd",
    "second_model",
    "simple_guesses",
    "t95",
    "temperature_sweep",
    "wrong_person",
]
