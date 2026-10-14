"""The generator's lever->construct matrix, its diminishing second step and its two interactions.

`v5`, from `docs/AUDIT_PROTOTYPE_PARITY.md` §A6. Ported from the Apps Script prototype's
`GEN_LEVER`, `1.6` second-step factor and `together` knob.

**Why this file exists.** Before `v5`, `reaction_shift` returned one scalar magnitude per version
code, applied to every construct with only the construct's `index_sign` for direction. Two
consequences, neither visible in any output:

* no lever was distinguishable from another by its effects — a pay rise moved *clarity* exactly as
  much as it moved *happiness*, so no path estimated on synthetic data corresponded to anything;
* the scalar was linear in the dials, so `analysis/interactions.py`'s
  ``extra = shift(joint) - (shift(a) + shift(b))`` was **exactly zero by construction**. `docs/07`
  §5 calls sub-additivity the study's contribution, and no fixture in the suite could exhibit it
  against a known truth.

Everything here is deterministic arithmetic over the spec. No database, no model call, no batch
where a shift alone will do.
"""

from __future__ import annotations

import pytest

from twinlab.analysis.interactions import Interaction, interaction
from twinlab.generator.synthetic import (
    GENERATOR_VERSION,
    generate_batch,
    reaction_shift,
    spec_from_config,
)
from twinlab.generator.voice import VOICE_VERSION
from twinlab.models.view import GeneratorSpec

#: Mid-scale economic dependence, so the captive-voice multiplier is engaged but not at its bound.
EDEP = 0.5


@pytest.fixture
def spec():
    return GeneratorSpec(seed=31)


def shift_of(spec: GeneratorSpec, code: str, construct: str) -> float:
    return reaction_shift(code, spec, economic_dependence=EDEP)[construct]


# --------------------------------------------------------------------- lever specificity


def test_each_lever_moves_its_own_constructs_and_leaves_the_others(spec):
    """Contracts (L3) is the only lever with a path to clarity; conditions (L2) has none.

    Not expressible before `v5`: one scalar moved every construct, so these two would have been
    equal.
    """
    only_conditions = reaction_shift("01000", spec, economic_dependence=EDEP)
    only_contracts = reaction_shift("00100", spec, economic_dependence=EDEP)

    assert only_conditions["SATI"] > 0
    assert only_conditions["TRAN"] == 0.0, "conditions has no path to clarity"

    assert only_contracts["TRAN"] > 0
    assert only_contracts["SATI"] == 0.0, "contracts has no path to happiness"


def test_an_unraised_version_moves_nothing(spec):
    """`00000` is the control. Every construct sits at its baseline, which is the correct null."""
    assert set(reaction_shift("00000", spec, economic_dependence=EDEP).values()) == {0.0}


def test_protection_raises_fairness_and_lowers_the_wish_to_leave(spec):
    """The matrix is signed, and `_item_target` must not re-apply `index_sign` on top of it.

    Double-applying would invert pushback, leaving and control while leaving fairness, clarity,
    happiness and staying untouched — a fault visible in no single construct's direction alone,
    which is why both signs are asserted together.
    """
    full = reaction_shift("22222", spec, economic_dependence=EDEP)
    assert full["FAIR"] > 0 and full["SATI"] > 0 and full["LOYA"] > 0
    assert full["EXIT"] < 0 and full["VOIC"] < 0 and full["CTRL"] < 0


def test_the_second_dial_step_adds_less_than_the_first(spec):
    """`second_step_factor` — nothing-to-minimum-wage is a bigger change than minimum-to-living."""
    one = shift_of(spec, "10000", "SATI")
    two = shift_of(spec, "20000", "SATI")
    assert one < two < 2 * one, "dial 2 adds more than dial 1 but less than twice it"
    assert two == pytest.approx(one * spec.second_step_factor)


# --------------------------------------------------------------------- the two interactions


def test_the_synthetic_population_exhibits_sub_additivity(spec):
    """**The reason A6 exists.** `docs/07` §5: "sub-additivity is the contribution."

    Both of the prototype's interactions, asserted from the generator's own ground truth: appeals
    (L4) and a forum (L5) compound on pushback; pay (L1) and safety (L2) substitute on staying.

    The synergy is scaled by `reaction_gain` along with everything else (`v8`), because the gain
    is applied to the **finished** shift. Asserted with the gain in it rather than loosened to an
    inequality: scaling the per-lever contributions and *not* the synergy term would leave these
    comparisons passing while quietly changing how sub-additive the population is, which is the
    claim `docs/07` §5 rests on.
    """
    # Appeals and a forum together: pushback falls FURTHER than the sum of the two alone.
    alone = shift_of(spec, "00010", "VOIC") + shift_of(spec, "00001", "VOIC")
    together = shift_of(spec, "00011", "VOIC")
    assert together < alone, "L4 x L5 must compound on pushback"
    assert together - alone == pytest.approx(-spec.lever_synergy * spec.reaction_gain)

    # Pay and safety together: staying rises LESS than the sum of the two alone.
    alone_stay = shift_of(spec, "10000", "LOYA") + shift_of(spec, "01000", "LOYA")
    together_stay = shift_of(spec, "11000", "LOYA")
    assert together_stay < alone_stay, "L1 x L2 must substitute on staying"
    assert together_stay - alone_stay == pytest.approx(
        -spec.lever_synergy / 2 * spec.reaction_gain
    )


def test_interactions_read_sub_additive_through_the_analysis_layer(spec):
    """The same ground truth, read through the function the paper's claim comes from.

    `interaction()` takes stored per-cell shifts, so this hands it the generator's truth and
    asserts the verdict it reports — the end-to-end form of the test above.
    """
    codes = ("00010", "00001", "00011")
    shifts_by_code = {
        code: {"pushback": shift_of(spec, code, "VOIC")} for code in codes
    }

    result = interaction("00010", "00001", "pushback", shifts_by_code)
    assert isinstance(result, Interaction)
    assert result.joint == "00011"
    assert result.extra < 0
    assert result.verdict == "sub-additive"


def test_zero_synergy_makes_every_interaction_exactly_additive():
    """The null — and the pre-`v5` behaviour, now an explicit setting rather than an accident."""
    flat = GeneratorSpec(seed=31, lever_synergy=0.0)
    alone = shift_of(flat, "00010", "VOIC") + shift_of(flat, "00001", "VOIC")
    assert shift_of(flat, "00011", "VOIC") == pytest.approx(alone)

    shifts = {
        code: {"pushback": shift_of(flat, code, "VOIC")}
        for code in ("00010", "00001", "00011")
    }
    result = interaction("00010", "00001", "pushback", shifts)
    assert isinstance(result, Interaction)
    assert result.verdict == "additive"


def test_a_lever_a_version_does_not_raise_contributes_nothing(spec):
    """The synergy is a property of the version, not of the matrix: both legs must be raised."""
    # L4 alone, L5 absent: no synergy term.
    alone = shift_of(spec, "00010", "VOIC")
    per_step = spec.lever_effects["L4"]["VOIC"] * spec.reaction("L4") * spec.reaction_gain
    assert alone == pytest.approx(per_step)


# --------------------------------------------------------------------- captive voice


def test_captive_voice_only_strengthens_the_forum_lever(spec):
    """`docs/06` §4's one dashboard interaction, and it must not leak into the other levers."""
    low = reaction_shift("00001", spec, economic_dependence=0.0)
    high = reaction_shift("00001", spec, economic_dependence=1.0)
    assert abs(high["VOIC"]) > abs(low["VOIC"]), "a captive driver reacts more to a forum"

    pay_low = reaction_shift("10000", spec, economic_dependence=0.0)
    pay_high = reaction_shift("10000", spec, economic_dependence=1.0)
    assert pay_low == pay_high, "pay carries no captive-voice multiplier"


def test_captive_voice_off_removes_the_multiplier():
    """The checkbox, honoured. At `False` dependence changes nothing anywhere."""
    off = GeneratorSpec(seed=31, captive_voice=False)
    assert reaction_shift("00001", off, economic_dependence=0.0) == reaction_shift(
        "00001", off, economic_dependence=1.0
    )


# --------------------------------------------------------------------- the spec's own guards


def test_a_misspelt_construct_in_the_matrix_is_refused():
    """Rule 7 — a key that contributes nothing would leave a batch looking correct."""
    with pytest.raises(ValueError, match="not constructs"):
        GeneratorSpec(
            seed=1,
            lever_effects={
                "L1": {"SATISFACTION": 0.5}, "L2": {}, "L3": {}, "L4": {}, "L5": {},
            },
        )


def test_a_lever_with_no_row_is_refused():
    """A lever that moves nothing is indistinguishable from a slider set to zero on purpose."""
    with pytest.raises(ValueError, match="missing"):
        GeneratorSpec(seed=1, lever_effects={"L1": {"SATI": 0.5}})


def test_an_unknown_lever_in_the_matrix_is_refused():
    """I2's frozen order — a sixth lever is a renumbering, not a configuration."""
    with pytest.raises(ValueError, match="not one of the five levers"):
        GeneratorSpec(
            seed=1,
            lever_effects={
                "L1": {}, "L2": {}, "L3": {}, "L4": {}, "L5": {}, "L6": {"SATI": 1.0},
            },
        )


def test_effects_raises_on_an_unknown_lever(spec):
    """As `reaction()` already does, and for the same reason."""
    with pytest.raises(KeyError, match="no construct effects"):
        spec.effects("L9")


# --------------------------------------------------------------------- config and provenance


def test_the_config_file_supplies_the_matrix():
    """`config/generator.default.yaml` is the source, so retuning needs no code change."""
    spec = spec_from_config(seed=7)
    assert spec.lever_effects["L4"]["FAIR"] == pytest.approx(0.7)
    assert spec.lever_effects["L2"].get("TRAN") is None, "conditions has no path to clarity"
    assert spec.second_step_factor == pytest.approx(1.6)
    assert spec.lever_synergy == pytest.approx(0.3)


def test_the_generator_version_records_the_v12_break():
    """`docs/09` §2 — "same seed, same batch" holds within a version, never across one."""
    assert GENERATOR_VERSION == "v12"
    batch = generate_batch(seed=31, count=3)
    assert batch["batch"]["config"]["generator_version"] == "v12"
    # The prose banks are versioned separately: a reworded bank changes every persona hash
    # without changing which values were drawn, and the two have to be tellable apart.
    assert batch["batch"]["config"]["voice_version"] == VOICE_VERSION
    # The spec that actually produced the batch is recorded beside the config file, so the matrix
    # a batch was drawn under is reproducible from the row rather than from today's defaults.
    assert batch["batch"]["config"]["spec"]["lever_effects"]["L4"]["FAIR"] == pytest.approx(0.7)


# ------------------------------------------------------- v7: the staying question's own construct


def test_the_staying_question_reads_the_behavioural_block_not_the_hope_block():
    """`v7` — `H3_V{n}_KEEP` asks likelihood, so it reads `EXIT` mirrored, never `LOYA`.

    *"How likely would you be to keep driving with Uber?"* is a behavioural intention; `LOYA` is
    *"I hope this job carries on in the future"*. Reading one off the other made the generator
    describe its most economically captive respondents as the ones about to leave — inverting the
    moderation `EDEP` carries in `stats/spec.py`, inside the data meant to exercise it.
    """
    from twinlab.generator.synthetic import _H3_MIRRORED, _H3_SUFFIX

    assert _H3_SUFFIX["KEEP"] == "EXIT"
    assert _H3_MIRRORED["KEEP"] is True
    # The other two read their construct forward, and must not be mirrored by a blanket rule.
    assert _H3_SUFFIX["FAIR"] == "FAIR" and _H3_MIRRORED["FAIR"] is False
    assert _H3_SUFFIX["PUSH"] == "VOIC" and _H3_MIRRORED["PUSH"] is False


def test_the_two_part_17_tables_name_the_same_questions():
    """A suffix in one table and not the other would be scored forward by default — the v7 bug."""
    from twinlab.generator.synthetic import _H3_MIRRORED, _H3_SUFFIX

    assert set(_H3_SUFFIX) == set(_H3_MIRRORED)


def test_a_captive_driver_is_likely_to_keep_driving_while_hoping_it_ends():
    """The divergence `v7` exists to represent, asserted on a drawn respondent, not on a constant.

    A respondent set low on hope (`LOYA`) and low on the wish to leave (`EXIT`) is someone who
    does not want the job and is not going anywhere. Part 17's staying question must read the
    second, so it answers **above** the midpoint while the `LOYA` battery answers below it.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.survey_intake import form_map
    from twinlab.models.reference import construct_code_for

    ref = reference()
    targets = {"LOYA": 2.0, "EXIT": 2.0, "EDEP": 6.5}
    spec = GeneratorSpec(
        seed=5, construct_targets=targets, disposition_spread=0.0, shared_mood=0.0,
        between_driver_swing=0.0, likert_sd=0.1, need_money=6.5,
    )
    batch = generate_batch(seed=5, count=6, spec=spec)
    inv = dict(form_map())
    rows = []
    for payload in batch["payloads"]:
        answers = {}
        for a in payload["answers"]:
            target = inv.get(f"{a['section']}|{a['title']}")
            if target:
                answers[target] = a["value"]
        rows.append(answers)

    loya_ids = [
        i for i in ref.battery_item_ids if str(construct_code_for(ref.items[i])) == "LOYA"
    ]
    for answers in rows:
        # Does not hope the job continues: the LOYA block sits in the bottom half of its scale.
        for item_id in loya_ids:
            points = ref.scale_points(item_id)
            assert int(answers[item_id]) < (points + 1) / 2, item_id
        # And is nevertheless likely to keep driving, on every one of the six versions.
        for position in range(1, 7):
            keep = int(answers[f"H3_V{position}_KEEP"])
            assert keep > 4, f"version {position} reads staying as {keep}, below the midpoint"


# ------------------------------------------------------------------- v7: the clipping pre-flight


def test_clipping_share_finds_the_floor_pile_up_the_sweep_found_the_hard_way():
    """`v7` — the 2026-10-12 spec put 37% of its batch on the fairness floor, silently.

    The clamp in `_respondent_targets` is correct and silent, so a slider near an end converts
    `between_driver_swing`'s extra width into respondents who are identical at the wall. This is
    the number that was only discoverable by spending the twin calls.
    """
    from twinlab.generator.synthetic import clipping_share

    spec = GeneratorSpec(
        seed=12102026,
        sentiment="frustrated",
        construct_targets={
            "CTRL": 6.0, "EXIT": 5.5, "EXPO": 6.5, "FAIR": 2.0,
            "LOYA": 2.5, "SATI": 2.5, "TRAN": 2.0, "VOIC": 5.5,
        },
        between_driver_swing=2.4,
    )
    shares = clipping_share(spec, samples=2000)
    assert shares["FAIR"] > 0.30
    assert shares["TRAN"] > 0.30
    # The constructs set mid-scale are not pinned, so the diagnostic is not simply alarmed.
    assert shares["EDEP"] < 0.05
    assert shares["VOIC"] < 0.05


def test_raising_the_swing_against_a_slider_near_the_end_buys_pile_up_not_spread():
    """The finding behind the note: on a floored construct the dial widens the wall, not the panel.

    Asserted as a comparison rather than an absolute, because the claim is about what the dial
    *does*, not about any particular share.
    """
    from twinlab.generator.synthetic import clipping_share

    def spec_at(swing: float) -> GeneratorSpec:
        return GeneratorSpec(
            seed=99, sentiment="frustrated", construct_targets={"FAIR": 2.0},
            between_driver_swing=swing,
        )

    low = clipping_share(spec_at(1.5), samples=2000)["FAIR"]
    high = clipping_share(spec_at(2.4), samples=2000)["FAIR"]
    assert high > low * 1.5, (
        f"swing 1.5 -> 2.4 moved the floor share only {low:.1%} -> {high:.1%}; the note this "
        "guards would have nothing to report"
    )


def test_the_clipping_diagnostic_never_changes_a_drawn_batch():
    """It reads a spec and has its own RNG, so calling it cannot disturb the draw order (I11)."""
    from twinlab.generator.synthetic import clipping_share

    spec = GeneratorSpec(seed=404, count=4)
    before = generate_batch(seed=404, count=4, spec=spec)
    clipping_share(spec, samples=500)
    after = generate_batch(seed=404, count=4, spec=spec)
    assert before["answers"] == after["answers"]


def test_a_clean_spec_reports_nothing_pinned_rather_than_staying_silent():
    """`CLAUDE.md` rule 7 — the screen must be able to say the check ran and found nothing."""
    from twinlab.services.generator import clipping

    assert clipping(GeneratorSpec(seed=1)) == []


# ------------------------------------------- v8: the gain, calibrated against a real respondent


def test_the_gain_scales_the_whole_matrix_and_nothing_else():
    """`v8` — one multiplier over every construct, so the matrix structure is untouched.

    What the gain may change is how far a respondent moves. What it may **not** change is which
    lever moves which construct, in what proportion, or with which sign — that is a separate
    claim and it has no external check. Asserted as exact proportionality rather than as a
    direction, because a gain that quietly altered one construct's share of a lever's effect would
    still pass every directional test in this file.
    """
    base = GeneratorSpec(seed=31, reaction_gain=1.0)
    scaled = GeneratorSpec(seed=31, reaction_gain=2.11)
    for code in ("10000", "02200", "11211", "22222", "00011"):
        one = reaction_shift(code, base, economic_dependence=EDEP)
        two = reaction_shift(code, scaled, economic_dependence=EDEP)
        assert set(one) == set(two)
        for construct, value in one.items():
            assert two[construct] == pytest.approx(value * 2.11), construct
            # A zero is a claim ("conditions has no path to clarity") and must stay a zero.
            if value == 0.0:
                assert two[construct] == 0.0, construct


def test_a_zero_gain_is_the_control_and_not_an_error():
    """Gain 0 reproduces the baseline everywhere — the correct null, and sometimes wanted."""
    spec = GeneratorSpec(seed=31, reaction_gain=0.0)
    assert set(reaction_shift("22222", spec, economic_dependence=EDEP).values()) == {0.0}


def test_the_shipped_gain_is_the_value_fitted_to_real_responses():
    """`v8` — the default is pinned to its derivation, so it cannot drift without a conscious edit.

    `2.11` is not a chosen number: it is the least-squares fit of the matrix gain against the one
    real respondent's own 18 Part 17 answers (`calibrate_reaction_gain`). Pinning it here means a
    later edit to the default has to come past this test and explain itself.

    The derivation is **re-run against the live database**, never in CI (`CLAUDE.md`: no live DB
    in CI, ever), which is why this asserts the constant rather than recomputing the fit.

    `v11` re-derived it to **2.40** jointly with `holdout_version_differentiation` against the
    same respondent and the same 18 answers. The two are coupled through the fit — compressing
    the spread between packages changes which level best explains those answers — and the joint
    fit halves the error on them, 0.863 to 0.392. `2.11` remains the correct **one-parameter**
    fit and `calibrate_reaction_gain` still returns it; both constants are pinned so neither can
    drift, and so a reader can see that the change was a re-derivation and not a retune.
    """
    assert GeneratorSpec(seed=0).reaction_gain == 2.40
    assert GeneratorSpec(seed=0).holdout_version_differentiation == 0.18


def _humans_from(batch, ref, inverse):
    """Real-shaped answer dicts out of a generated batch, for the fit's round-trip tests."""
    humans: dict[str, dict[str, int]] = {}
    for submission, payload in zip(batch["submissions"], batch["payloads"], strict=True):
        answers: dict[str, int] = {}
        for row in payload["answers"]:
            target = inverse.get(f"{row['section']}|{row['title']}")
            if target in ref.items and str(row["value"]).lstrip("-").isdigit():
                answers[target] = int(row["value"])
        humans[str(submission["submission_id"])] = answers
    return humans


def test_the_gain_fit_recovers_a_gain_it_was_given():
    """Round-trip: generate at a known gain, fit it back. The property, with no real data in CI.

    This is what makes the fit trustworthy when it is re-run on real responses as `n` grows — it
    is tested against ground truth the test itself set, rather than against the one sample that
    motivated it.
    """
    from twinlab.generator.synthetic import calibrate_reaction_gain
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.survey_intake import form_map

    ref = reference()
    inverse = dict(form_map())
    for truth in (1.0, 2.0, 3.0):
        # No answer noise and no reactivity spread, so the batch IS the matrix at `truth` and the
        # fit has a single right answer to find.
        spec = GeneratorSpec(
            # `holdout_version_differentiation` at 1.0 because THIS fit's model assumes it:
            # `calibrate_reaction_gain` has one parameter and reads a compressed batch as a
            # larger gain (it returns 4.91 for a truth of 3.00 at a compression of 0.5). That is
            # not a bug in either function — it is why `calibrate_reaction_model` exists, and
            # `test_the_joint_fit_recovers_both_parameters` pins the two-parameter case.
            # `endpoint_avoidance` off for the same reason as the differentiation: the fit's
            # model does not describe it, and a batch drawn with it is a batch whose endpoint
            # answers have been moved inward after the matrix produced them. (On REAL data that
            # bias is present and unmodelled too — one more reason the fit is provisional.)
            seed=77, reaction_gain=truth, reactivity_spread=0.0, likert_sd=0.01,
            holdout_version_differentiation=1.0, endpoint_avoidance=0.0,
            disposition_spread=0.0, between_driver_swing=0.0,
        )
        batch = generate_batch(seed=77, count=8, spec=spec)
        fit = calibrate_reaction_gain(_humans_from(batch, ref, inverse), ref=ref)
        assert fit.respondents_n == 8
        assert fit.items_n == 8 * len(ref.holdout_h3_item_ids)
        # Rounding to the scale's integers costs precision, so this is a band, not a point.
        assert abs(fit.gain - truth) <= 0.35, f"fitted {fit.gain} for a true gain of {truth}"


def test_the_gain_fit_is_idempotent_on_an_already_calibrated_spec():
    """Re-fitting must not compound. `calibrate_reaction_gain` forces unit gain internally.

    The trap this guards: `reaction_shift` applies `spec.reaction_gain` itself, so a fit that used
    the caller's spec as given would return the gain *on top of* the one already there — reporting
    1.00 ("no correction needed") when it meant "2.11 was right". That reading is
    indistinguishable from a successful calibration and would halve the gain on every
    re-derivation. Found by running the fit against the real respondent and getting 1.00 back.
    """
    from twinlab.generator.synthetic import calibrate_reaction_gain
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.survey_intake import form_map

    ref = reference()
    inverse = dict(form_map())
    spec = GeneratorSpec(
        seed=91, reaction_gain=2.0, reactivity_spread=0.0, likert_sd=0.01,
        disposition_spread=0.0, between_driver_swing=0.0,
    )
    humans = _humans_from(generate_batch(seed=91, count=6, spec=spec), ref, inverse)
    # The spec handed in already carries 2.0; the fit must still say 2.0, not 1.0.
    passed_in = calibrate_reaction_gain(humans, ref=ref, spec=spec)
    at_unit = calibrate_reaction_gain(
        humans, ref=ref, spec=spec.model_copy(update={"reaction_gain": 1.0})
    )
    assert passed_in.gain == at_unit.gain


def test_a_fit_with_nothing_scorable_raises_rather_than_reporting_a_gain():
    """I15's shape — a gain with no fit behind it is the perfect-score-over-zero-items defect."""
    from twinlab.generator.synthetic import GeneratorError, calibrate_reaction_gain

    with pytest.raises(GeneratorError, match="nothing to fit"):
        calibrate_reaction_gain({"nobody": {}})


# ------------------------------------------- v8: reactivity, and that the persona carries it


def test_reactivity_varies_the_shift_between_respondents():
    """`v8` — before this the shift was a batch constant and no twin could infer it.

    Across the whole range of `EDEP`, its only respondent-level input, the fairness shift varied
    by at most 0.16 scale points and by exactly 0.00 on four of the six Part 17 versions.
    """
    spec = GeneratorSpec(seed=31)
    low = reaction_shift("12220", spec, economic_dependence=0.5, reactivity=0.5)["FAIR"]
    high = reaction_shift("12220", spec, economic_dependence=0.5, reactivity=1.5)["FAIR"]
    assert high == pytest.approx(low * 3.0)
    assert high - low > 1.0, "two respondents must differ by more than the old 0.16 ceiling"


def test_the_persona_says_how_reactive_its_respondent_is():
    """**The information fix.** A twin cannot infer a quantity nobody told it.

    Part 17 asks for the baseline moved by this respondent's reactivity. The baseline is all over
    the persona; the reactivity was nowhere in it. This asserts the clause is present and that it
    tracks the drawn value rather than being decorative.

    I8 permits this: its own guard puts the whys and open answers *in* the persona block, where
    "the twin is meant to read them as who this person is". No version code, no holdout id and no
    version's answer appears — a disposition, like the baseline attitudes already there.
    """
    from twinlab.generator.voice import CIRCUMSTANCE, reactivity_tag

    assert reactivity_tag(0.5) == "react:low"
    assert reactivity_tag(1.0) == "react:mid"
    assert reactivity_tag(1.5) == "react:high"
    for band in ("react:low", "react:mid", "react:high"):
        assert CIRCUMSTANCE[band], f"{band} has no clause, so a respondent would carry none"

    # And the clauses reach a real passage. Zero spread puts the whole batch in one band, so the
    # assertion is about the band actually drawn rather than about any clause appearing.
    batch = generate_batch(
        seed=5, count=6, spec=GeneratorSpec(seed=5, reactivity_spread=0.0)
    )
    text = " ".join(
        str(row["value"])
        for payload in batch["payloads"]
        for row in payload["answers"]
        if isinstance(row["value"], str)
    )
    assert any(clause in text for clause in CIRCUMSTANCE["react:mid"]), (
        "a zero-spread batch should speak in the mid reactivity band"
    )
    assert not any(
        clause in text
        for band in ("react:low", "react:high")
        for clause in CIRCUMSTANCE[band]
    ), "a zero-spread batch must not speak in a band no respondent was drawn into"


def test_no_part_17_answer_or_version_code_leaks_into_the_free_text():
    """The reactivity clause is a disposition, so it must not name a version or an answer (I8)."""
    from twinlab.ingest.reference_store import reference

    ref = reference()
    batch = generate_batch(seed=23, count=6)
    for payload in batch["payloads"]:
        for row in payload["answers"]:
            value = row["value"]
            if not isinstance(value, str) or value.isdigit():
                continue
            for item_id in ref.holdout_h3_item_ids + ref.holdout_h2_item_ids:
                assert item_id.lower() not in value.lower(), f"{item_id} named in free text"
            for code in ref.h3_version_codes:
                assert code not in value, f"version code {code} named in free text"


# ------------------------------- v10: lever salience, and that the persona carries it
#
# The last of the three hidden batch constants. `reaction_gain` said how far any change moves a
# driver and was calibrated; `reactivity_spread` said how far it moves *this* driver and is now
# drawn and spoken; `lever_reactions` says **which** change moves them and carried `L1: 2.0` for
# the whole batch, disclosed in no persona. That is why the twin told the six Part 17 versions
# apart (its spread across them more than doubled at stage 3) and ranked them wrong.


def test_a_respondents_salience_differs_from_the_batchs_and_from_other_respondents():
    """`v10` - before this every respondent weighted pay double and no twin could infer it."""
    import random

    from twinlab.generator.synthetic import respondent_lever_weights

    spec = GeneratorSpec(seed=31)
    a = respondent_lever_weights(random.Random("a"), spec)
    b = respondent_lever_weights(random.Random("b"), spec)

    assert set(a) == {"L1", "L2", "L3", "L4", "L5"}, "all five levers, always"
    assert a != b, "two respondents must not carry the same weighting"
    assert any(
        abs(a[lever] - spec.reaction(lever)) > 0.05 for lever in a
    ), "a respondent must be able to sit off the batch mean"
    # And it reaches the shift: the same version moves two respondents by different amounts for
    # a reason that is about WHICH lever they care about, not only how much they react.
    assert reaction_shift("12220", spec, economic_dependence=EDEP, lever_weights=a) != (
        reaction_shift("12220", spec, economic_dependence=EDEP, lever_weights=b)
    )


def test_the_salience_draw_leaves_the_batch_mean_on_every_lever_unchanged():
    """**The non-circularity condition.** Route A adds variance; it does not re-weight.

    `CLAUDE.md` and `docs/08` 2.4 - choosing lever weights by checking a twin pass rate is the
    circularity that would make every path estimated on synthetic data meaningless. The guard is
    that the batch's mean salience per lever is the researcher's `lever_reactions` and nothing
    here moves it.
    """
    import random

    from twinlab.generator.synthetic import respondent_lever_weights

    spec = GeneratorSpec(seed=31)
    rng = random.Random("mean")
    draws = [respondent_lever_weights(rng, spec) for _ in range(4000)]
    for lever in ("L1", "L2", "L3", "L4", "L5"):
        mean = sum(d[lever] for d in draws) / len(draws)
        assert mean == pytest.approx(spec.reaction(lever), abs=0.03), (
            f"{lever}'s batch mean moved; the population was re-weighted, not spread"
        )


def test_salience_is_multiplicative_so_a_zero_slider_stays_zero_and_none_go_negative():
    """`docs/06` 4's no-reaction null must stay null, and no lever may invert for one driver.

    An additive spread would give a respondent a negative weight on a lever the researcher set to
    zero, which would turn a pay rise into something that *lowers* their satisfaction - a sign
    flip inside the data meant to exercise the analysis.
    """
    import random

    from twinlab.generator.synthetic import respondent_lever_weights

    off = GeneratorSpec(
        seed=31,
        lever_reactions={"L1": 0.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0},
        salience_spread=0.9,
    )
    rng = random.Random("zero")
    for _ in range(500):
        weights = respondent_lever_weights(rng, off)
        assert weights["L1"] == 0.0, "a slider at zero must stay at zero for every respondent"
        assert all(w >= 0.0 for w in weights.values()), "a salience weight may not go negative"
    # And a batch with every slider off contributes nothing from any lever, for every
    # respondent, at the widest spread.
    null = GeneratorSpec(
        seed=31,
        lever_reactions=dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 0.0),
        salience_spread=0.9,
    )
    weights = respondent_lever_weights(random.Random("null"), null)
    assert set(weights.values()) == {0.0}
    # Asserted against the batch-weighted shift rather than against zero **on purpose.**
    # `lever_synergy` is applied per version and reads the dials, not the reaction weights, so a
    # no-reaction batch still carries the two interaction terms — a pre-`v10` behaviour that
    # contradicts `GeneratorSpec.lever_reactions`' own docstring ("every reaction at zero
    # produces holdouts identical to the baseline"). Left alone and recorded in
    # `docs/DECISIONS.md` as an open question: whether an interaction between two levers a
    # respondent does not react to should fire is `docs/07` §5's sub-additivity claim and the
    # researcher's to take, not a thing to change while fixing salience. What `v10` owes is that
    # the per-respondent draw changes nothing here, and that is what this asserts.
    assert reaction_shift(
        "22222", null, economic_dependence=EDEP, lever_weights=weights
    ) == reaction_shift("22222", null, economic_dependence=EDEP)


def test_a_zero_spread_reproduces_the_batch_weighting_exactly():
    """The control. At `salience_spread: 0.0` every respondent carries `lever_reactions`."""
    import random

    from twinlab.generator.synthetic import respondent_lever_weights

    flat = GeneratorSpec(seed=31, salience_spread=0.0)
    weights = respondent_lever_weights(random.Random("flat"), flat)
    assert weights == {lever: flat.reaction(lever) for lever in weights}
    # Which means the shift is the pre-`v10` shift, so the version is the only thing that broke.
    assert reaction_shift(
        "12220", flat, economic_dependence=EDEP, lever_weights=weights
    ) == reaction_shift("12220", flat, economic_dependence=EDEP)


def test_an_incomplete_weighting_raises_rather_than_defaulting_a_lever_to_normal():
    """`CLAUDE.md` rule 7, as :meth:`GeneratorSpec.reaction` already does.

    A lever missing from the draw would silently move at weight 1.0, so a whole holdout block
    would move for a reason nothing recorded.
    """
    spec = GeneratorSpec(seed=31)
    with pytest.raises(KeyError, match="L2"):
        reaction_shift("12220", spec, economic_dependence=EDEP, lever_weights={"L1": 2.0})


def test_captive_voice_still_multiplies_the_respondents_own_forum_weight():
    """`docs/06` 4's one dashboard interaction survives Route A, on whichever weight is in force.

    The handoff names this explicitly: keep `captive_voice`'s EDEP multiplier on L5. It must act
    on the respondent's drawn salience, not on a batch mean the respondent no longer carries.
    """
    spec = GeneratorSpec(seed=31)
    weights = {"L1": 1.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 0.5}
    low = reaction_shift("00001", spec, economic_dependence=0.0, lever_weights=weights)["VOIC"]
    high = reaction_shift("00001", spec, economic_dependence=1.0, lever_weights=weights)["VOIC"]
    assert abs(high) == pytest.approx(abs(low) * 2.0)
    # And it is scaled by this respondent's own weight, half the batch's, not by the batch's.
    batch = reaction_shift("00001", spec, economic_dependence=0.0)["VOIC"]
    assert abs(low) == pytest.approx(abs(batch) * 0.5)


def test_the_gain_fit_uses_the_batch_weighting_and_never_invents_a_respondents_salience():
    """A real respondent's salience is unknown, so the fit must not draw one for them.

    `CLAUDE.md` rule 5 - no imputation. The fit is of the batch's gain against the batch's
    weighting; giving each real respondent a drawn salience would be fitting to a fiction.
    """
    import inspect

    from twinlab.generator.synthetic import calibrate_reaction_gain

    source = inspect.getsource(calibrate_reaction_gain)
    assert "lever_weights" not in source, (
        "the gain fit must call reaction_shift at the batch weighting (lever_weights=None)"
    )


def test_the_persona_says_which_change_matters_most_to_its_respondent():
    """**The information fix, one level down.** A twin cannot infer a quantity nobody told it.

    The precedent is `v9`: the identical fix for reactivity took the twin's tracking of it from
    r -0.08 to +0.87, the largest single gain in the sequence. Part 17 asks how a respondent
    would answer under six described packages; which levers those packages raise is on the page,
    but which of them this driver *cares* about was a batch constant held nowhere in the persona.

    I8 permits this: no version code, no holdout id, no dial and no number - a disposition, like
    the baseline attitudes the persona already carries.
    """
    from twinlab.generator.voice import CIRCUMSTANCE, SALIENCE_BY_LEVER, salience_tag

    for lever, tag in SALIENCE_BY_LEVER.items():
        assert CIRCUMSTANCE[tag], f"{lever} has no clause, so a respondent would carry none"

    # The tag names the lever this respondent weights highest, and ties resolve in the odometer's
    # frozen order rather than by dictionary order.
    assert salience_tag({"L1": 2.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0}) == "salience:pay"
    assert salience_tag({"L1": 0.5, "L2": 1.0, "L3": 1.0, "L4": 3.0, "L5": 1.0}) == (
        "salience:appeals"
    )
    assert salience_tag(dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 1.0)) == "salience:pay"
    # No lever weighted at all is `docs/06` 4's null: no lever matters most, and the persona
    # says nothing rather than claiming one.
    assert salience_tag(dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 0.0)) is None

    # And the clauses reach a real passage. Zero spread pins the whole batch on pay, so the
    # assertion is about the band actually drawn rather than about any clause appearing.
    batch = generate_batch(seed=5, count=6, spec=GeneratorSpec(seed=5, salience_spread=0.0))
    text = " ".join(
        str(row["value"])
        for payload in batch["payloads"]
        for row in payload["answers"]
        if isinstance(row["value"], str)
    )
    assert any(clause in text for clause in CIRCUMSTANCE["salience:pay"]), (
        "a zero-spread batch at the default weighting should speak in the pay band"
    )
    assert not any(
        clause in text
        for tag in (
            "salience:conditions",
            "salience:contracts",
            "salience:appeals",
            "salience:forum",
        )
        for clause in CIRCUMSTANCE[tag]
    ), "a zero-spread batch must not speak for a lever no respondent weights highest"


def test_a_spread_batch_speaks_for_more_than_one_lever():
    """The point of Route A: the panel must contain drivers who care about different things."""
    from twinlab.generator.voice import CIRCUMSTANCE, SALIENCE_BY_LEVER

    batch = generate_batch(seed=19, count=12, spec=GeneratorSpec(seed=19, salience_spread=0.9))
    spoken = set()
    for payload in batch["payloads"]:
        text = " ".join(
            str(row["value"]) for row in payload["answers"] if isinstance(row["value"], str)
        )
        for tag in SALIENCE_BY_LEVER.values():
            if any(clause in text for clause in CIRCUMSTANCE[tag]):
                spoken.add(tag)
    assert len(spoken) >= 2, (
        f"a wide-spread batch spoke for only {spoken}; the salience draw is not reaching the "
        "persona, which is the whole of Route A"
    )


def test_the_config_file_supplies_the_salience_spread():
    """`config/generator.default.yaml` is the source, so retuning needs no code change."""
    spec = spec_from_config(seed=7)
    assert spec.salience_spread == pytest.approx(0.5)


def test_the_salience_pre_flight_says_how_pay_dominated_a_batch_still_is():
    """`v10` - the number Route A owes the researcher, before any twin call is spent.

    Centring the spread on `lever_reactions` is what keeps the draw non-circular, and its
    consequence is that spreading a pay mean of 2.0 against four means of 1.0 leaves most of the
    batch weighting pay highest anyway. Every persona then *states* that weighting - the defect
    `v10` repairs - but the batch carries little between-driver signal on WHAT a driver wants.
    Measured rather than asserted from the dial, because that is the lesson `clipping_share`
    taught: finding it out after the sweep costs the sweep.
    """
    from twinlab.generator.synthetic import salience_mix

    narrow = salience_mix(GeneratorSpec(seed=1, salience_spread=0.0))
    assert narrow["L1"] == pytest.approx(1.0), (
        "at zero spread the clause is still a batch constant, disclosed rather than hidden"
    )

    default = salience_mix(GeneratorSpec(seed=1, salience_spread=0.5))
    assert default["L1"] > 0.75, "the default spread does not undo a doubled pay mean"
    assert all(default[lever] > 0 for lever in ("L2", "L3", "L4", "L5")), (
        "some drivers must be able to care most about something other than pay"
    )

    wide = salience_mix(GeneratorSpec(seed=1, salience_spread=0.9))
    assert wide["L1"] < default["L1"], "a wider spread must buy real rank variation"
    assert sum(wide.values()) == pytest.approx(1.0, abs=0.01)


def test_a_flat_weighting_gives_every_lever_a_share_of_the_batch():
    """The contrast case. Pay dominates because the researcher's mean says so, not the draw.

    Asserted so that the diagnostic cannot be read as a defect in the draw: with the five means
    equal, the same spread spreads the top salience roughly evenly. Flattening those means is a
    claim about the population and the researcher's to make (`CLAUDE.md`, "when the spec is
    silent"); this only shows what each choice produces.
    """
    from twinlab.generator.synthetic import salience_mix

    flat = GeneratorSpec(
        seed=1,
        lever_reactions=dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 1.0),
        salience_spread=0.5,
    )
    mix = salience_mix(flat)
    assert all(0.1 < share < 0.35 for share in mix.values()), (
        f"a flat weighting should spread the top salience, got {mix}"
    )


def test_the_salience_pre_flight_reports_the_null_as_a_null_rather_than_as_a_winner():
    """`docs/06` §4's no-reaction batch: nobody has a change that matters most.

    Five zeros, never 100% on whichever lever came first - the I15 class of defect, where a score
    over nothing reads as a result.
    """
    from twinlab.generator.synthetic import salience_mix

    null = GeneratorSpec(
        seed=1,
        lever_reactions=dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 0.0),
        salience_spread=0.9,
    )
    assert set(salience_mix(null).values()) == {0.0}


def test_the_salience_diagnostic_never_changes_a_drawn_batch():
    """Its own RNG, like `clipping_share`: a pre-flight that perturbed the draw would be a bug."""
    from twinlab.generator.synthetic import salience_mix

    spec = GeneratorSpec(seed=44)
    before = generate_batch(seed=44, count=3, spec=spec)
    salience_mix(spec)
    salience_mix(spec, samples=50)
    after = generate_batch(seed=44, count=3, spec=spec)
    assert before["payloads"] == after["payloads"]
    # And it is deterministic in the spec, so two readings of one spec agree.
    assert salience_mix(spec) == salience_mix(spec)


# ------------------- v11: the holdout answers report a hypothetical coarsely
#
# The 2026-10-13 diagnosis: the twins were not failing on the persona (they reproduce their
# driver's 37 battery answers to 0.18 of a point on the control cells) but on one axis only - the
# twin gives nearly the same answer to all six Part 17 versions, and the generator made its
# drivers differentiate those versions sharply. The one real respondent does not differentiate
# them either: a range of exactly ONE scale point across six described worlds, while moving 2.47
# points from their own baseline.
#
# The two facts are separate and this is the test file's load-bearing distinction:
# `reaction_shift` keeps the full lever matrix (how far protections move a construct) and the
# compression applies to the holdout ANSWER (how coarsely a person reports a hypothetical).


def test_the_compression_never_touches_the_lever_matrix():
    """**The reason the compression lives in `_item_target` and not in `reaction_shift`.**

    Shrinking inside `reaction_shift` was implemented, measured and rejected: it fitted the real
    respondent beautifully (error 0.863 -> 0.392) and, because shrinking toward a mean over all
    codes mixes every lever's row into every code, it moved a conditions-only code's effect on
    clarity from the matrix's exact `0.000` to `+1.028` and **inverted** sub-additivity from
    -0.72 to +2.10. That is the pre-`v5` defect - no lever distinguishable from another by its
    effects - and it would make every path estimated on synthetic data an artefact of the
    shrinkage rather than of the matrix (`docs/07` section 5 calls sub-additivity the study's
    contribution).

    So `reaction_shift` must be **identical at every value** of the parameter.
    """
    codes = ("01000", "00100", "10000", "00011", "12220", "11211", "00000")
    full = GeneratorSpec(seed=31, holdout_version_differentiation=1.0)
    for lam in (0.0, 0.18, 0.5, 0.97):
        shrunk = GeneratorSpec(seed=31, holdout_version_differentiation=lam)
        for code in codes:
            assert reaction_shift(code, shrunk, economic_dependence=EDEP) == reaction_shift(
                code, full, economic_dependence=EDEP
            ), f"{code} moved at compression {lam}; the matrix must be untouched"

    # And the two properties that rejection was about, stated directly at the shipped default.
    shipped = GeneratorSpec(seed=31)
    assert reaction_shift("01000", shipped, economic_dependence=EDEP)["TRAN"] == 0.0, (
        "conditions (L2) has no path to clarity, and that zero is a claim"
    )
    a = reaction_shift("00010", shipped, economic_dependence=EDEP)["VOIC"]
    b = reaction_shift("00001", shipped, economic_dependence=EDEP)["VOIC"]
    joint = reaction_shift("00011", shipped, economic_dependence=EDEP)["VOIC"]
    assert joint - (a + b) < 0, "the population must still be sub-additive"


def test_the_compression_narrows_the_holdout_answers_across_the_six_versions():
    """What the parameter is **for**: the spread a twin is scored against.

    Measured on the answers a batch actually emits, per version code, because that is what the
    gate reads. The real respondent's own spread across the six is 0.167.
    """
    import statistics as st

    from twinlab.ingest.reference_store import reference

    ref = reference()
    h3 = ref.holdout_h3_item_ids
    codes_of = {i: str(ref.items[i].version_code or "") for i in h3}

    def version_spread(lam: float) -> float:
        # `endpoint_avoidance` off, so the spread measured here is the compression's and not
        # the response style's — endpoint avoidance narrows a spread near the scale's ends too,
        # and this test is about one parameter.
        spec = GeneratorSpec(
            seed=404, holdout_version_differentiation=lam, endpoint_avoidance=0.0
        )
        batch = generate_batch(seed=404, count=10, spec=spec)
        by_code: dict[str, list[float]] = {}
        for row in batch["answers"]:
            item = row["item_id"]
            if item in codes_of and row.get("value_num") is not None:
                by_code.setdefault(codes_of[item], []).append(float(row["value_num"]))
        means = [st.mean(v) for _, v in sorted(by_code.items()) if v]
        return st.pstdev(means)

    full = version_spread(1.0)
    shipped = version_spread(0.18)
    flat = version_spread(0.0)
    assert full > shipped, (
        f"compression must narrow the spread: full {full:.3f}, shipped {shipped:.3f}"
    )
    assert shipped < full / 2.0, "the shipped value should roughly halve the spread or better"
    assert flat < full / 2.0, "at zero the six versions must answer nearly alike"
    # **Not** `shipped > flat`. Below about 0.2 the between-version spread is smaller than the
    # answer noise, so which of the two reads higher is a property of the seed and not of the
    # parameter — asserting an order there would be asserting noise. What the parameter guarantees
    # is that both are far below the uncompressed spread, which is what the two lines above pin.


def test_a_control_version_moves_nobody_at_any_compression():
    """`00000` is zero however low the parameter goes. The invariant, not an edge case.

    Shrinking toward a mean "effect of being shown some package" must not leak that mean onto a
    respondent who was shown no package: the control cell is what the whole design is measured
    against, and a non-zero `00000` would offset every comparison in the study.
    """
    for lam in (0.0, 0.18, 0.5, 1.0):
        spec = GeneratorSpec(seed=31, holdout_version_differentiation=lam)
        assert set(reaction_shift("00000", spec, economic_dependence=EDEP).values()) == {0.0}
        assert set(
            reaction_shift(
                "00000", spec, economic_dependence=EDEP, reactivity=1.4,
                lever_weights={"L1": 2.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0},
            ).values()
        ) == {0.0}


def test_the_mean_shift_closed_form_equals_enumerating_every_raising_code():
    """`mean_shift` is four lines of probability; a wrong constant would bias every holdout.

    The closed form rests on each lever's dial being uniform on {0, 1, 2} over the 243 codes, so
    a lever contributes `(1 + second_step_factor) / 3` steps on average and is raised with
    probability 2/3, and the two synergy terms need both their levers raised (4/9). Dropping the
    all-zero code is one rescale by 243/242. Nothing else in the suite would catch an error here,
    because a biased mean still produces plausible-looking answers.
    """
    import random

    from twinlab.generator.synthetic import (
        _mean_shift_by_enumeration,
        mean_shift,
        respondent_lever_weights,
    )

    for seed in (1, 31):
        for edep in (0.0, 0.5, 1.0):
            for reactivity in (0.6, 1.0, 1.4):
                spec = GeneratorSpec(seed=seed)
                weights = respondent_lever_weights(random.Random(seed), spec)
                closed = mean_shift(
                    spec, economic_dependence=edep, reactivity=reactivity,
                    lever_weights=weights,
                )
                brute = _mean_shift_by_enumeration(
                    spec, economic_dependence=edep, reactivity=reactivity,
                    lever_weights=weights,
                )
                for construct, value in closed.items():
                    assert value == pytest.approx(brute[construct], abs=1e-9), construct


def test_the_compression_preserves_the_mean_holdout_level():
    """Why the compression is close to orthogonal to the gain.

    The shrinkage is toward the mean over the raising codes, so that mean is a fixed point: the
    LEVEL a driver is moved to stays calibrated to `reaction_gain` and only the SPREAD between
    packages changes. Without this the two parameters would trade off against each other and
    neither would mean anything on its own.
    """
    import random

    from twinlab.generator.synthetic import (
        mean_shift,
        reaction_shift,
        respondent_lever_weights,
    )

    spec = GeneratorSpec(seed=31)
    weights = respondent_lever_weights(random.Random(5), spec)
    mean = mean_shift(spec, economic_dependence=EDEP, reactivity=1.0, lever_weights=weights)
    for lam in (0.0, 0.18, 0.5, 1.0):
        # The shrinkage, applied as `_item_target` applies it, leaves the mean a fixed point.
        for construct, mu in mean.items():
            shrunk = mu + lam * (mu - mu)
            assert shrunk == pytest.approx(mu), construct
    # And a code AT the mean is unmoved by any compression.
    one = reaction_shift(
        "12220", spec, economic_dependence=EDEP, lever_weights=weights
    )
    assert one != mean, "the sanity of the above: a real code is not already at the mean"


def test_the_joint_fit_recovers_both_parameters_it_was_given():
    """The two-parameter fit round-trips, where the one-parameter fit cannot.

    Generated at a known pair, then fitted back. Recovery is **attenuated**, not exact, and that
    is a property of the data rather than of the fit: the answers are rounded to integers and
    clamped to the scale, and the baseline is reconstructed from the battery, which is itself
    rounded. The tolerance is wide for that reason and the test's job is the direction and the
    rough size - which is also all one real respondent can establish.

    Asserted beside the one-parameter fit on the same batch, which reads a compressed batch as a
    much larger gain (4.91 for a truth of 3.00 at a compression of 0.5). That mis-specification
    is why this function exists.
    """
    from twinlab.generator.synthetic import calibrate_reaction_gain, calibrate_reaction_model

    for truth_gain, truth_lam in ((2.0, 0.2), (3.0, 0.5), (1.5, 1.0)):
        spec = GeneratorSpec(
            seed=77, reaction_gain=truth_gain, holdout_version_differentiation=truth_lam,
            reactivity_spread=0.0, salience_spread=0.0, likert_sd=0.01,
            # Off: the fit models the matrix and the compression, not the response style.
            endpoint_avoidance=0.0,
        )
        batch = generate_batch(seed=77, count=8, spec=spec)
        humans: dict[str, dict[str, int]] = {}
        for row in batch["answers"]:
            if row.get("value_num") is not None:
                humans.setdefault(str(row["submission_id"]), {})[str(row["item_id"])] = int(
                    row["value_num"]
                )

        fit = calibrate_reaction_model(humans, spec=spec)
        assert fit.holdout_version_differentiation == pytest.approx(truth_lam, abs=0.15), (
            f"compression {truth_lam} came back as {fit.holdout_version_differentiation}"
        )
        assert fit.gain == pytest.approx(truth_gain, rel=0.25), (
            f"gain {truth_gain} came back as {fit.gain}"
        )
        assert fit.respondents_n == 8
        # Not a strict inequality: the fit minimises SSE, so when the truth IS full
        # differentiation the fitted 0.97 can sit a hair above it on MAE. The tolerance says
        # "the fit never makes the error materially worse", which is the honest claim.
        assert fit.mae_at_fit <= fit.mae_at_full_differentiation + 0.02

        if truth_lam < 0.6:
            loose = calibrate_reaction_gain(humans, spec=spec)
            assert loose.gain != pytest.approx(truth_gain, rel=0.05), (
                "the one-parameter fit should be visibly mis-specified on compressed data; if it "
                "is not, the compression is not reaching the answers"
            )


def test_the_fit_reports_both_spreads_so_the_value_is_not_taken_on_trust():
    """`observed_version_spread` beside `fitted_version_spread` — the pair being reconciled.

    A fitted parameter with no residual reported is a number a reader has to believe. These two
    say what the respondents did across the six codes and what the generator does at the fit.
    """
    from twinlab.generator.synthetic import calibrate_reaction_model

    spec = GeneratorSpec(
        seed=77, reaction_gain=2.0, holdout_version_differentiation=0.2,
        reactivity_spread=0.0, salience_spread=0.0, likert_sd=0.01,
        endpoint_avoidance=0.0,
    )
    batch = generate_batch(seed=77, count=8, spec=spec)
    humans: dict[str, dict[str, int]] = {}
    for row in batch["answers"]:
        if row.get("value_num") is not None:
            humans.setdefault(str(row["submission_id"]), {})[str(row["item_id"])] = int(
                row["value_num"]
            )
    fit = calibrate_reaction_model(humans, spec=spec)
    assert fit.observed_version_spread > 0
    assert fit.fitted_version_spread > 0
    assert "spread across the six versions" in fit.headline
    assert "1 real respondent" not in fit.headline, "eight respondents, not one"


def test_an_unscorable_joint_fit_raises_rather_than_reporting_a_model():
    """I15's sibling: a model reported without a fit behind it is the defect to prevent."""
    from twinlab.generator.synthetic import GeneratorError, calibrate_reaction_model

    with pytest.raises(GeneratorError):
        calibrate_reaction_model({"nobody": {}})


def test_the_config_file_supplies_the_holdout_compression():
    """`config/generator.default.yaml` is the source, so re-deriving needs no code change."""
    spec = spec_from_config(seed=7)
    assert spec.holdout_version_differentiation == pytest.approx(0.18)
    assert spec.reaction_gain == pytest.approx(2.40)
