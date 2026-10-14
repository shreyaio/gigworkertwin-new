"""The quality gate — H3 — and H2 validation. `docs/08` §2 and §3. Implements I15, serves I9.

**H3 gates; H2 does not.** H3 is six *unseen stimuli* rendered through the real pipeline — same
design agent, same Checker, same style version. A twin that reproduces its human across six
different policy worlds has shown that the *mapping from stimulus to response* transfers, not just
the level, which is what H2 cannot show (`docs/08` §2.3).

Two rules here are not negotiable:

* **A score over zero scorable items raises** :class:`QualityScoreEmpty` (I15). A perfect score on
  nothing is the prototype's defect, and `twin_quality_runs.items_n > 0` is a database constraint.
* **A twin below threshold is dropped, not tuned** (`docs/08` §2.4). It is not re-prompted, not
  re-personaed and not given a second model. Tuning a twin until it passes its own validation test
  is circular, so nothing in this module takes a "try again" path.
"""

from __future__ import annotations

import math

from twinlab.models.twin import QualityScore, TwinConfig

#: The six Part 17 version codes, in `version_shown` order. `docs/08` §2.1.
#:
#: Read from the frozen register rather than written here, because `docs/01` §3.6 already encodes
#: them on the holdout items and two copies would drift.
H3_CODE_COUNT = 6

#: H3 collects 6 versions x (fairness, pushback, keep).
H3_ITEMS_EXPECTED = 18

#: H2 collects the 16 mirrored outcome items. `docs/08` §3.1.
H2_ITEMS_EXPECTED = 16

#: The fewest paired points from which a correlation is reported. Three, because `r` over two
#: points is ±1 by construction. See :func:`pearson_r`.
R_MIN_POINTS = 3


class QualityScoreEmpty(ValueError):
    """No item scored, so there is no score. I15, `docs/08` §2.2.

    Raised rather than returning ``mae=0.0``: zero error over zero items reads as a perfect twin and
    is how the prototype kept twins it had never actually tested.
    """

    def __init__(self, ids: list[str]) -> None:
        super().__init__(
            f"no scorable item among {ids}: a quality score over zero items is no score, never a "
            "perfect one (I15). Check that the human's survey_answers and the twin's answers "
            "overlap on these ids."
        )
        self.ids = list(ids)


def score_holdout(
    human: dict[str, int], twin: dict[str, int], ids: list[str]
) -> QualityScore:
    """MAE and % within 1 point, over the items **both** sides answered. `docs/08` §2.2.

    Intersection, not union, and never imputed: an item the human skipped is not scored against a
    twin's answer to it, and an item the twin failed to produce is not scored as a maximal error.
    Both would be a number standing in for a measurement that does not exist (I17's spirit, and
    `CLAUDE.md` rule 5).
    """
    errs = [abs(human[i] - twin[i]) for i in ids if i in human and i in twin]
    if not errs:
        raise QualityScoreEmpty(ids)
    return QualityScore(
        mae=sum(errs) / len(errs),
        pct_within_1=sum(e <= 1 for e in errs) / len(errs),
        items_n=len(errs),
    )


def average_scores(scores: list[QualityScore]) -> QualityScore:
    """Average over repeats, so one bad sample does not discard a good twin. `docs/08` §2.1 step 5.

    ``items_n`` is the **total** scored across repeats, not the mean: it is a count of measurements
    taken, and it is what `twin_quality_runs.items_n > 0` constrains. Averaging it would report 18
    for three runs of 18 and hide how much evidence the verdict rests on.
    """
    if not scores:
        raise QualityScoreEmpty([])
    return QualityScore(
        mae=sum(s.mae for s in scores) / len(scores),
        pct_within_1=sum(s.pct_within_1 for s in scores) / len(scores),
        items_n=sum(s.items_n for s in scores),
    )


def h3_verdict(score: QualityScore, config: TwinConfig) -> bool:
    """**Keep iff `mae <= mae_max` AND `pct_within_1 >= pct_within_1_min`.** `docs/08` §2.2.

    A conjunction, never either/or: a twin with MAE 0.9 that is within a point only 60 per cent of
    the time is close on average by being wildly wrong occasionally, which is not the same twin.
    """
    return score.keeps(mae_max=config.mae_max, pct_within_1_min=config.pct_within_1_min)


def pearson_r(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation, or ``None`` when it is undefined. `docs/08` §3.3.

    ``None`` rather than 0.0 when either side has no variance. A twin that answered all six versions
    identically has an *undefined* ordering, not an uncorrelated one, and reporting 0.0 would let
    "predicted everyone's mean" look like a measured null — exactly what validity test 3 exists to
    rule out.

    ``None`` on fewer than :data:`R_MIN_POINTS` pairs, for the same reason and not as a
    convenience: with two points ``r`` is **exactly** ±1 whenever both sides vary at all, so it
    carries no information about ordering and would be stored as if it did. The prototype guarded
    this and the first Python port did not. H3 gives six points per outcome by design, so fewer
    than three means items were lost — which is a reason to report nothing, not to report a
    perfect correlation over the two that survived.
    """
    n = len(xs)
    if n < R_MIN_POINTS or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return sxy / math.sqrt(sxx * syy)


def h3_correlations(
    human: dict[str, int], twin: dict[str, int], items_by_outcome: dict[str, list[str]]
) -> dict[str, float | None]:
    """Per-outcome Pearson `r` across the six H3 versions. `docs/08` §3.3.

    MAE says the twin is close; `r` says its **ordering of the six worlds** matches its human's. A
    twin can have low MAE and near-zero `r` by predicting everyone's mean, so both are reported.

    The too-few-points rule lives in :func:`pearson_r` alone. This function used to carry its own
    copy of the floor, which is how the two came to disagree.
    """
    out: dict[str, float | None] = {}
    for outcome, ids in items_by_outcome.items():
        paired = [(human[i], twin[i]) for i in ids if i in human and i in twin]
        out[outcome] = pearson_r([float(h) for h, _ in paired], [float(t) for _, t in paired])
    return out


def h2_arm_for(twin_arm: str | None, human_arm: str | None) -> str:
    """The arm an H2 round must show: **the twin's own driver's arm**. `docs/08` §3.1.

    A mismatch is a bug, not a variation, so it raises here rather than being recorded and moved
    past. `twin_quality_runs.arm` exists so it is checkable after the fact, but the check is cheap
    enough to make before the call.
    """
    if human_arm is None:
        raise ValueError(
            "the human has no recorded arm, so there is no H2 stimulus to show (docs/08 §3.1)"
        )
    if twin_arm is not None and twin_arm != human_arm:
        raise ValueError(
            f"H2 would show arm {twin_arm!r} to a twin whose driver saw {human_arm!r}. "
            "Showing a twin a different arm than its human saw is a bug, not a variation "
            "(docs/08 §3.1)."
        )
    return human_arm


def quality_row(
    *,
    twin_id: str,
    holdout_set: str,
    score: QualityScore,
    model: str,
    repeats: int,
    detail: dict,
    config: TwinConfig,
    session_id: str | None = None,
    arm: str | None = None,
    correlations: dict[str, float | None] | None = None,
    config_version: int = 1,
    config_fingerprint: str | None = None,
) -> dict:
    """The `quality_run_record` RPC parameters. `docs/08` §2.5, I9.

    Written through the RPC, never as a plain insert: the function demotes the previous `is_latest`
    and appends the new row **in the same transaction**, so every surface reading quality — the
    Twins list, the panel selector, the analyst's `twins_n` — sees the new number with no cache to
    invalidate.

    `kept` is set for H3 and left ``None`` for H2, which `quality_h3_gates` enforces: H2 does not
    gate (`docs/08` §3).
    """
    if holdout_set not in ("H2", "H3"):
        raise ValueError(f"holdout_set is 'H2' or 'H3', got {holdout_set!r}")
    if holdout_set == "H2" and arm is None:
        raise ValueError("an H2 row records the arm the human saw (quality_h2_arm)")
    return {
        "p_twin_id": twin_id,
        "p_session_id": session_id,
        "p_holdout_set": holdout_set,
        "p_arm": arm,
        "p_items_n": score.items_n,
        "p_mae": round(score.mae, 3),
        "p_pct_within_1": round(score.pct_within_1, 3),
        "p_correlations": correlations,
        "p_kept": h3_verdict(score, config) if holdout_set == "H3" else None,
        "p_repeats": repeats,
        "p_detail": detail,
        "p_model": model,
        "p_config_version": config_version,
        # `005`. The verdict is only valid for the config it was made under (docs/DECISIONS.md).
        "p_config_fingerprint": config_fingerprint,
    }
