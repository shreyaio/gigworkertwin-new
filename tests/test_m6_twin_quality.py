"""M6 — the twin agent and the quality gate. `docs/11` M6.

The seven acceptance criteria are implemented verbatim, each named in its test, beside the tests
that
prove each gate can **fail**: a gate that cannot fail is not a gate (`HANDOFF.md` §2.4).

No live LLM and no live DB. The twin's rounds go through :class:`StubModelClient` and the quality
rows through the autouse :class:`InMemoryBackend`, which mirrors the DDL check constraints — so I15
and I9 are tested here rather than only in Postgres.
"""

from __future__ import annotations

import pytest

from twinlab.agents.registry import StubModelClient, default_agent_configs
from twinlab.agents.twin import (
    BLOCK_ORDER,
    RoundPromptError,
    assert_no_forbidden_content,
    build_round_prompt,
    build_user_prompt,
    lever_order_for,
    rebuild_round_prompt,
    round_hash,
    run_twin,
)
from twinlab.ingest.reference_store import reference
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import (
    Background,
    BatteryItem,
    QualityScore,
    SurveyResponse,
    Twin,
    TwinAnswerSet,
    TwinConfig,
)
from twinlab.persona.builder import build_persona
from twinlab.services.config import load_twin_config
from twinlab.validity.quality import (
    H2_ITEMS_EXPECTED,
    H3_ITEMS_EXPECTED,
    QualityScoreEmpty,
    average_scores,
    h2_arm_for,
    h3_correlations,
    h3_verdict,
    pearson_r,
    quality_row,
    score_holdout,
)

TWIN_KWARGS = dict(
    twin_id="UBR-TEST", city="Mumbai", service="cab", age=34, gender="Male",
    tenure_months=28, hours_per_week=58,
)
BACKGROUND_KWARGS = dict(
    platform_count="2", other_apps="Ola and Rapido",
    vehicle_arrangement="rent from a fleet owner", dependants=4,
    other_household_income="none", education="secondary school",
    years_driving_before_uber=3.5,
)

#: A distinctive why-text, so the I8 scan is looking for something that could only have leaked.
WHY_TEXT = "the app cancelled my ride near Andheri and nobody explained the reason to me"


def _twin() -> Twin:
    return Twin(**TWIN_KWARGS, background=Background(**BACKGROUND_KWARGS))


def _battery_answers(value_5: int = 4, value_7: int = 5) -> dict[str, int]:
    ref = reference()
    return {
        item_id: (value_5 if ref.scale_points(item_id) == 5 else value_7)
        for item_id in ref.battery_item_ids
    }


def _response(**overrides) -> SurveyResponse:
    base = {"twin_id": "UBR-TEST", "answers": _battery_answers()}
    return SurveyResponse(**{**base, **overrides})


def _battery() -> dict[str, BatteryItem]:
    """item_id → the item as shown, in register order, battery only (I10: 37, not 39)."""
    ref = reference()
    return {i: ref.battery_item(i) for i in ref.battery_item_ids}


def _paragraphs() -> dict[str, str]:
    return {lever: f"Paragraph for {lever}." for lever in LEVER_BY_POSITION}


def _round(**overrides):
    base = dict(
        persona_hash="a" * 64,
        paragraphs=_paragraphs(),
        baseline=_battery_answers(),
        battery=_battery(),
        seed=12345,
    )
    return build_round_prompt(**{**base, **overrides})


# ------------------------------------------------------------------ the 37-item output contract


def test_output_validates_to_exactly_the_37_battery_items():
    """`docs/11` M6, verbatim: a missing or extra key raises. I10 and I13.

    37, not 39: the attention checks `AMQ6` and `ALGO5` are never put to a twin.
    """
    ref = reference()
    expected = ref.battery_item_ids
    assert len(expected) == 37
    assert "AMQ6" not in expected and "ALGO5" not in expected

    # `TwinAnswerSet` reads the register itself — the expected set is not a caller-supplied
    # argument, so no call site can widen it.
    TwinAnswerSet(answers=_battery_answers())

    short = _battery_answers()
    short.pop(expected[0])
    with pytest.raises(ValueError, match="missing"):
        TwinAnswerSet(answers=short)

    extra = _battery_answers()
    extra["NOT_AN_ITEM"] = 3
    with pytest.raises(ValueError, match="extra"):
        TwinAnswerSet(answers=extra)


def test_a_five_point_item_rejects_a_six():
    """I13 — per-item ranges come from `scales.points`, never from a constant.

    The prototype's prompt said "1 to 7" for every item and three of its nine constructs were
    5-point, so its 5-point blocks were silently wrong.
    """
    ref = reference()
    five_point = next(i for i in ref.battery_item_ids if ref.scale_points(i) == 5)
    answers = _battery_answers()
    answers[five_point] = 6
    with pytest.raises(ValueError, match=five_point):
        TwinAnswerSet(answers=answers)


async def test_a_vector_that_survives_one_repair_fails_rather_than_being_coerced():
    """`docs/02` §5.4 — a twin that cannot produce 37 valid integers fails **for that cell**.

    Nothing is padded from the baseline and nothing is clamped. The failure is the correct outcome.
    """
    ref = reference()
    cfg = default_agent_configs()["twin"]
    five_point = next(i for i in ref.battery_item_ids if ref.scale_points(i) == 5)

    def handler(c, prompt, out):
        answers = _battery_answers()
        answers[five_point] = 6          # out of range, and stays out of range on the repair
        return {"answers": answers}

    outcome = await run_twin(
        cfg, _round(), "persona text", StubModelClient(handler),
        expected=ref.battery_item_ids,
        points_for={i: ref.scale_points(i) for i in ref.battery_item_ids},
    )
    assert not outcome.ok
    assert outcome.output is None
    assert any(d.item_id == five_point for d in outcome.defects)
    assert "nothing coerced" in outcome.reason


async def test_a_clean_vector_validates_and_spends_one_call():
    """The happy path, so the failure above means something."""
    ref = reference()
    cfg = default_agent_configs()["twin"]
    client = StubModelClient(lambda c, p, o: {"answers": _battery_answers()})
    outcome = await run_twin(
        cfg, _round(), "persona text", client,
        expected=ref.battery_item_ids,
        points_for={i: ref.scale_points(i) for i in ref.battery_item_ids},
    )
    assert outcome.ok
    assert client.call_count("twin") == 1
    assert outcome.retries == 0


# ------------------------------------------------------------------ I8: what the round may not hold


def test_the_round_prompt_carries_none_of_the_five_forbidden_things():
    """`docs/11` M6, verbatim, and I8. No why-text, no open-ended answers, no holdout items,
    no version code and no dial digits.

    Asserted on the **assembled prompt string**, not on the model: `RoundPrompt` forbidding a field
    proves the shape, and the string is what the twin actually reads.
    """
    ref = reference()
    persona = build_persona(_twin(), _response(whys={"WHY_CONTROL": WHY_TEXT})).text
    prompt = build_user_prompt(_round(), persona)

    # no holdout items, by id
    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        assert item_id not in prompt, f"round prompt names holdout item {item_id}"

    # no version code and no dial digits identifying a cell
    for code in ("01000", "02000", "22222", "00000", "SHAM"):
        assert code not in prompt

    # the guard agrees, and it is callable from the orchestrator
    assert_no_forbidden_content(
        prompt,
        holdout_ids=ref.holdout_h2_item_ids + ref.holdout_h3_item_ids,
        why_texts=[WHY_TEXT],
        version_code="01000",
    )


def test_the_i8_guard_rejects_each_violation():
    """A guard that cannot fail is not a guard — one case per forbidden thing."""
    ref = reference()
    holdout = ref.holdout_h3_item_ids[0]

    with pytest.raises(RoundPromptError, match="holdout"):
        assert_no_forbidden_content(
            f"... {holdout} ...", holdout_ids=[holdout], why_texts=[]
        )
    # Why-text is forbidden in the STIMULUS, not in the persona: docs/03 §8 puts the whys inside
    # <<<PERSONA>>> deliberately, and I6 makes the persona lossless over them.
    with pytest.raises(RoundPromptError, match="travels with the stimulus"):
        assert_no_forbidden_content(
            f"<<<END PERSONA>>> ... {WHY_TEXT} ...", holdout_ids=[], why_texts=[WHY_TEXT]
        )
    # ...and the same why-text inside the persona block is fine.
    assert_no_forbidden_content(
        f"<<<PERSONA>>> {WHY_TEXT} <<<END PERSONA>>> stimulus",
        holdout_ids=[], why_texts=[WHY_TEXT],
    )
    with pytest.raises(RoundPromptError, match="version code"):
        assert_no_forbidden_content(
            "... 01000 ...", holdout_ids=[], why_texts=[], version_code="01000"
        )


def test_the_persona_and_the_round_prompt_are_separate_documents():
    """I8 — the persona explains who this person is; the round prompt asks what they now say.

    The whys live in the persona and must **not** travel with the stimulus. If they did, every twin
    would restate its own justifications under every counterfactual and would look immovable no
    matter what it was shown — which is the signal.
    """
    persona = build_persona(_twin(), _response(whys={"WHY_CONTROL": WHY_TEXT})).text
    assert WHY_TEXT in persona

    round_prompt = _round()
    # The round object itself has no field that could carry a why, and the assembled SCENARIO,
    # BASELINE and BATTERY blocks are built only from paragraphs, numbers and stems.
    assert "why" not in {f.lower() for f in round_prompt.model_fields}
    body = build_user_prompt(round_prompt, persona)
    scenario_onward = body.split("<<<END PERSONA>>>", 1)[1]
    assert WHY_TEXT not in scenario_onward


def test_the_baseline_block_is_absent_rather_than_empty_when_no_baseline_is_shown():
    """`docs/08` §2.1 — the quality gate shows no baseline, because the human had none either.

    Absent, not empty: an empty `<<<BASELINE>>>` fence tells the twin a baseline exists and was
    withheld, which is a different stimulus from never having had one.
    """
    shown = build_user_prompt(_round(), "persona")
    hidden = build_user_prompt(_round(show_baseline=False), "persona")
    assert "<<<BASELINE>>>" in shown
    assert "<<<BASELINE>>>" not in hidden
    assert "<<<SCENARIO>>>" in hidden and "<<<BATTERY>>>" in hidden


def test_the_blocks_appear_in_the_fixed_contract_order():
    """`docs/02` §3.3 — a reordered prompt is a different stimulus."""
    import re

    prompt = build_user_prompt(_round(), "persona")
    seen = [m.group(1) for m in re.finditer(r"<<<([A-Z]+)>>>", prompt)]
    assert seen == list(BLOCK_ORDER)


def test_every_battery_item_carries_its_own_range_and_its_anchors():
    """`docs/02` §4.2 rule 6 — stated in the prompt *and* enforced in Python (I13).

    The anchors are part of rule 6, not an extra: a range without them does not say which
    direction it runs in, and the human read a labelled row (`docs/DECISIONS.md`, 2026-10-12).
    """
    ref = reference()
    prompt = build_user_prompt(_round(), "persona")
    for item_id in ref.battery_item_ids:
        assert f"{item_id}: " in prompt
        shown = prompt.split(f"{item_id}: ")[1][:400]
        points = ref.scale_points(item_id)
        anchors = ref.scale_anchors(item_id)
        assert f"(answer 1 to {points};" in shown
        assert f"1 = {anchors[0]}" in shown
        assert f"{points} = {anchors[-1]}" in shown


def test_the_two_holdout_only_scales_name_their_ends_to_the_twin():
    """`fair7` and `likely7` reach a twin **only** through H3, so only H3 can get them wrong.

    `likely7` runs `Not at all likely … Extremely likely` with no negative end, so its point 4 is
    "Moderately likely" and a twin reading it as a symmetric agreement scale is miscalibrated
    before it answers. This is the defect that put every synthetic twin's `KEEP` answer +3.46 above
    its driver's (`docs/DECISIONS.md`, 2026-10-12).
    """
    from twinlab.agents.twin import build_h3_prompt, build_h3_user_prompt
    from twinlab.services.quality import h3_items

    ref = reference()
    by_version = h3_items(ref)
    prompt = build_h3_prompt(
        persona_hash="h",
        paragraphs_by_version={p: _paragraphs() for p in sorted(by_version)},
        items_by_version=by_version,
        seed=7,
    )
    rendered = build_h3_user_prompt(prompt, "persona")
    for item_id in ref.holdout_h3_item_ids:
        anchors = ref.scale_anchors(item_id)
        shown = rendered.split(f"{item_id}: ")[1][:400]
        assert f"1 = {anchors[0]}" in shown, f"{item_id} does not name its low end"
        assert f"7 = {anchors[-1]}" in shown, f"{item_id} does not name its high end"
        assert f"4 = {anchors[3]}" in shown, f"{item_id} does not name its midpoint"
    # The asymmetry is the whole point: likely7's point 4 is not neutral.
    assert "4 = Moderately likely" in rendered
    assert "4 = Neither fair nor unfair" in rendered


# ------------------------------------------------------------------ I11: reconstructing a round


def test_lever_order_and_seed_reconstruct_a_stored_round_to_the_recorded_hash():
    """`docs/11` M6, verbatim, and I11 / `docs/09` §6.

    The prompt is **rebuilt, never stored**. What is stored is the seed, the lever order, the
    persona
    hash, the wording and the style version; this proves those are sufficient.
    """
    original = _round(seed=987654)
    persona = "the persona passage, verbatim"
    recorded = round_hash(original, persona)

    rebuilt = rebuild_round_prompt(
        persona_hash=original.persona_hash,
        paragraphs=_paragraphs(),
        baseline=_battery_answers(),
        battery=_battery(),
        seed=987654,
        lever_order=original.lever_order,
    )
    assert rebuilt.lever_order == original.lever_order
    assert rebuilt.scenario == original.scenario
    assert round_hash(rebuilt, persona) == recorded


def test_a_stored_lever_order_that_contradicts_its_seed_is_a_hard_failure():
    """I11 — a round that does not reconstruct cannot be attributed to a known stimulus.

    Checked rather than trusted: if the stored order is not the order the seed regenerates, the text
    shown was not the text the provenance describes, and every number built on it is unattributable.
    """
    original = _round(seed=987654)
    wrong = list(reversed(original.lever_order))
    with pytest.raises(RoundPromptError, match="not reconstructible"):
        rebuild_round_prompt(
            persona_hash=original.persona_hash,
            paragraphs=_paragraphs(),
            baseline=_battery_answers(),
            battery=_battery(),
            seed=987654,
            lever_order=wrong,
        )


def test_the_lever_order_is_seeded_not_global_and_is_a_permutation():
    """`docs/03` §8 — randomised per twin per round, but reproducibly.

    Drawn from a local `random.Random(seed)`. The global RNG would make the order depend on whatever
    else ran first in the process, and the order is persisted and expected to reconstruct.
    """
    import random

    order = lever_order_for(42)
    assert sorted(order) == list(range(5))
    assert lever_order_for(42) == order

    random.seed(1)
    assert lever_order_for(42) == order          # unaffected by the global RNG

    # Different seeds do actually reorder, or randomisation is decorative.
    assert any(lever_order_for(s) != order for s in range(50))


def test_a_round_missing_a_lever_is_refused():
    """Five paragraphs or none: a round with four levers is not a cell."""
    short = {k: v for k, v in _paragraphs().items() if k != "L3"}
    with pytest.raises(RoundPromptError, match="five levers"):
        _round(paragraphs=short)


# ------------------------------------------------------------------ the H3 gate


def test_the_h3_gate_keeps_iff_mae_at_most_1_and_pct_within_1_at_least_080():
    """`docs/11` M6, verbatim. `docs/08` §2.2 — a conjunction, never either/or.

    The either/or cases matter: a twin with MAE 0.9 that is within a point only 60 per cent of the
    time is close on average by being wildly wrong occasionally, which is not the same twin.
    """
    config = load_twin_config()
    assert (config.mae_max, config.pct_within_1_min) == (1.0, 0.80)

    assert h3_verdict(QualityScore(mae=1.0, pct_within_1=0.80, items_n=18), config)
    assert h3_verdict(QualityScore(mae=0.4, pct_within_1=1.00, items_n=18), config)
    # each threshold alone is not enough
    assert not h3_verdict(QualityScore(mae=0.9, pct_within_1=0.60, items_n=18), config)
    assert not h3_verdict(QualityScore(mae=1.1, pct_within_1=1.00, items_n=18), config)


def test_the_score_is_mae_and_pct_within_one_over_the_items_both_sides_answered():
    """`docs/08` §2.2, and nothing is imputed.

    Intersection, not union: an item the human skipped is not scored, and an item the twin failed to
    produce is not scored as a maximal error. Either would be a number standing in for a measurement
    that does not exist.
    """
    human = {"a": 5, "b": 3, "c": 7, "d": 1}
    twin = {"a": 5, "b": 4, "c": 4, "e": 2}
    score = score_holdout(human, twin, ["a", "b", "c", "d", "e"])
    assert score.items_n == 3                      # a, b, c — d and e are not pairs
    assert score.mae == pytest.approx((0 + 1 + 3) / 3)
    assert score.pct_within_1 == pytest.approx(2 / 3)


def test_the_gate_averages_over_repeats_so_one_bad_sample_does_not_discard_a_good_twin():
    """`docs/08` §2.1 step 5, and `quality_runs_per_twin` defaults to 3."""
    config = load_twin_config()
    assert config.quality_runs_per_twin == 3

    good = QualityScore(mae=0.5, pct_within_1=0.95, items_n=18)
    bad = QualityScore(mae=1.6, pct_within_1=0.60, items_n=18)
    averaged = average_scores([good, good, bad])

    assert averaged.mae == pytest.approx((0.5 + 0.5 + 1.6) / 3)
    assert h3_verdict(averaged, config)            # kept despite the one bad sample
    assert not h3_verdict(bad, config)             # which alone would have failed

    # items_n is the TOTAL measured, not the mean: it says how much evidence the verdict rests on.
    assert averaged.items_n == 54


def test_h3_expects_eighteen_numbers_and_h2_sixteen():
    """`docs/08` §2.1 step 3 and §3.1 step 4 — 6 versions x 3 outcomes, and 16 mirrored items."""
    ref = reference()
    assert H3_ITEMS_EXPECTED == 18
    assert len(ref.holdout_h3_item_ids) == H3_ITEMS_EXPECTED
    assert H2_ITEMS_EXPECTED == 16
    assert len(ref.holdout_h2_item_ids) == H2_ITEMS_EXPECTED
    assert len(ref.h3_version_codes) == 6


# ------------------------------------------------------------------ I15: a score over nothing


def test_a_quality_score_over_zero_scorable_items_raises():
    """`docs/11` M6, verbatim, and I15.

    Zero error over zero items reads as a perfect twin. This is how the prototype kept twins it had
    never actually tested.
    """
    with pytest.raises(QualityScoreEmpty):
        score_holdout({"a": 4}, {"b": 4}, ["a", "b"])       # no overlapping id
    with pytest.raises(QualityScoreEmpty):
        score_holdout({}, {}, [])
    with pytest.raises(QualityScoreEmpty):
        average_scores([])


def test_a_quality_score_cannot_be_constructed_with_no_items():
    """I15 at the model boundary, so no code path can assemble one."""
    with pytest.raises(ValueError, match="items_n"):
        QualityScore(mae=0.0, pct_within_1=1.0, items_n=0)


async def test_the_backend_refuses_a_quality_row_with_no_items(backend):
    """I15 in the DDL, mirrored by the in-memory backend — `quality_has_items`."""
    from twinlab.db.client import DbError

    params = {
        "p_twin_id": "UBR-TEST", "p_session_id": None, "p_holdout_set": "H3",
        "p_arm": None, "p_items_n": 0, "p_mae": 0.0, "p_pct_within_1": 1.0,
        "p_correlations": None, "p_kept": True, "p_repeats": 1,
        "p_detail": {}, "p_model": "stub", "p_config_version": 1,
    }
    with pytest.raises(DbError, match="items_n"):
        await backend.rpc("quality_run_record", params)


# ------------------------------------------------------------------ H2: the twin's own arm


def test_h2_shows_a_twin_its_own_drivers_arm():
    """`docs/11` M6 and `docs/08` §3.1.

    **Showing a twin a different arm than its human saw is a bug, not a variation.** It raises here
    rather than being recorded and moved past; `twin_quality_runs.arm` exists so it is also
    checkable
    after the fact.
    """
    ref = reference()
    arm = sorted(ref.arms)[0]
    assert h2_arm_for(None, arm) == arm
    assert h2_arm_for(arm, arm) == arm

    other = sorted(ref.arms)[1]
    with pytest.raises(ValueError, match="bug, not a variation"):
        h2_arm_for(other, arm)

    with pytest.raises(ValueError, match="no recorded arm"):
        h2_arm_for(None, None)


def test_an_h2_row_records_the_arm_and_does_not_gate():
    """`docs/08` §3 — H2 does not gate. `quality_h3_gates` enforces the pairing.

    H3 carries `kept`; H2 carries null. A `kept` on an H2 row would make a non-gating check look
    like it had excluded a twin.
    """
    ref = reference()
    config = load_twin_config()
    score = QualityScore(mae=0.5, pct_within_1=0.95, items_n=16)

    h2 = quality_row(
        twin_id="UBR-TEST", holdout_set="H2", score=score, model="stub", repeats=1,
        detail={}, config=config, arm=sorted(ref.arms)[0],
    )
    assert h2["p_kept"] is None
    assert h2["p_arm"] is not None

    h3 = quality_row(
        twin_id="UBR-TEST", holdout_set="H3", score=score, model="stub", repeats=3,
        detail={}, config=config,
    )
    assert h3["p_kept"] is True

    with pytest.raises(ValueError, match="arm"):
        quality_row(
            twin_id="UBR-TEST", holdout_set="H2", score=score, model="stub", repeats=1,
            detail={}, config=config,
        )


async def test_the_backend_refuses_an_h2_row_with_no_arm_and_an_h3_row_with_no_verdict(backend):
    """Both halves of `quality_h3_gates` / `quality_h2_arm` can actually fail."""
    from twinlab.db.client import DbError

    base = {
        "p_twin_id": "UBR-TEST", "p_session_id": None, "p_arm": None, "p_items_n": 16,
        "p_mae": 0.5, "p_pct_within_1": 0.95, "p_correlations": None, "p_repeats": 1,
        "p_detail": {}, "p_model": "stub", "p_config_version": 1,
    }
    with pytest.raises(DbError, match="quality_h2_arm"):
        await backend.rpc("quality_run_record", {**base, "p_holdout_set": "H2", "p_kept": None})
    with pytest.raises(DbError, match="quality_h3_gates"):
        await backend.rpc("quality_run_record", {**base, "p_holdout_set": "H3", "p_kept": None})


# ------------------------------------------------------------------ I9: the pointer flip


async def test_writing_a_quality_run_demotes_the_previous_is_latest(backend):
    """`docs/11` M6, verbatim, and I9. `docs/08` §2.5.

    Append-only with a pointer: every surface reading quality — the Twins list, the panel selector,
    the analyst's `twins_n` — sees the new number with no cache to invalidate. The old row is
    **kept**, demoted, never updated in place.
    """
    ref = reference()
    config = load_twin_config()

    first = quality_row(
        twin_id="UBR-TEST", holdout_set="H3",
        score=QualityScore(mae=1.5, pct_within_1=0.5, items_n=18),
        model="stub", repeats=3, detail={"run": 1}, config=config,
    )
    second = quality_row(
        twin_id="UBR-TEST", holdout_set="H3",
        score=QualityScore(mae=0.4, pct_within_1=0.95, items_n=18),
        model="stub", repeats=3, detail={"run": 2}, config=config,
    )
    await backend.rpc("quality_run_record", first)
    await backend.rpc("quality_run_record", second)

    rows = await backend.select("twin_quality_runs", filters=[("eq", "twin_id", "UBR-TEST")])
    assert len(rows) == 2, "evidence is append-only: the old row is demoted, never overwritten"
    latest = [r for r in rows if r["is_latest"]]
    assert len(latest) == 1
    assert float(latest[0]["mae"]) == 0.4
    assert latest[0]["kept"] is True

    # The demoted row keeps its own verdict, so the history stays readable.
    demoted = [r for r in rows if not r["is_latest"]]
    assert demoted[0]["kept"] is False

    # An H2 row is a separate pointer: it must not demote the H3 one.
    await backend.rpc("quality_run_record", quality_row(
        twin_id="UBR-TEST", holdout_set="H2",
        score=QualityScore(mae=0.6, pct_within_1=0.9, items_n=16),
        model="stub", repeats=1, detail={}, config=config, arm=sorted(ref.arms)[0],
    ))
    h3_latest = [
        r for r in await backend.select("twin_quality_runs", filters=[("eq", "holdout_set", "H3")])
        if r["is_latest"]
    ]
    assert len(h3_latest) == 1 and float(h3_latest[0]["mae"]) == 0.4


# ------------------------------------------------------------------ correlations


def test_pearson_r_is_none_rather_than_zero_when_undefined():
    """`docs/08` §3.3 — a twin with no variance has an *undefined* ordering, not an uncorrelated
    one.

    Reporting 0.0 would let "predicted everyone's mean" look like a measured null, which is exactly
    what validity test 3 exists to rule out.
    """
    assert pearson_r([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert pearson_r([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert pearson_r([4.0, 4.0, 4.0], [1.0, 2.0, 3.0]) is None      # flat twin
    assert pearson_r([1.0], [1.0]) is None                          # one point


def test_pearson_r_refuses_two_points_because_r_is_plus_or_minus_one_by_construction():
    """`docs/08` §3.3 — two points carry no information about ordering.

    With two pairs that both vary, `r` is exactly +1 or -1 whatever the numbers are, so storing it
    in `twin_quality_runs.correlations` would record a perfect ordering match as evidence. H3 gives
    six points per outcome by design; fewer than three means items were lost, which is a reason to
    report nothing. The prototype guarded this and the first Python port did not.
    """
    assert pearson_r([1.0, 2.0], [5.0, 9.0]) is None                 # would have been +1.0
    assert pearson_r([1.0, 2.0], [9.0, 5.0]) is None                 # would have been -1.0
    # Three points is the first n at which the answer is not forced by the arithmetic.
    assert pearson_r([1.0, 2.0, 3.0], [1.0, 3.0, 2.0]) == pytest.approx(0.5)


def test_h3_correlations_report_per_outcome_and_survive_a_missing_pair():
    """`docs/08` §3.3 — MAE says the twin is close, `r` says its ordering of the six worlds
    matches."""
    human = {"f1": 2, "f2": 4, "f3": 6, "p1": 1, "p2": 2}
    twin = {"f1": 3, "f2": 4, "f3": 7, "p1": 1}
    out = h3_correlations(human, twin, {"fairness": ["f1", "f2", "f3"], "pushback": ["p1", "p2"]})
    assert out["fairness"] is not None and out["fairness"] > 0.9
    assert out["pushback"] is None          # only one usable pair


# ------------------------------------------------------------------ config


def test_the_twin_config_is_loaded_and_validated_not_defaulted_in_code():
    """`ARCHITECTURE.md` §4 — `twin.default.yaml` is the seed TwinConfig.

    `extra="forbid"`, so a typo'd threshold fails on load rather than leaving the gate running on
    defaults the researcher did not choose.
    """
    config = load_twin_config()
    assert isinstance(config, TwinConfig)
    assert config.temperature == 0.7           # placeholder; set from validity test 8
    assert config.show_baseline is False        # reversed 2026-10-07, docs/DECISIONS.md
    assert config.wording == "A"

    with pytest.raises(ValueError):
        TwinConfig(mae_max=1.0, pct_witin_1_min=0.8)     # deliberate typo
    with pytest.raises(ValueError, match="proportion"):
        TwinConfig(pct_within_1_min=1.5)
    with pytest.raises(ValueError, match="at least 1"):
        TwinConfig(quality_runs_per_twin=0)


def test_the_twin_temperature_matches_the_agent_config():
    """Two declarations of the same placeholder must not drift before test 8 sets it."""
    assert load_twin_config().temperature == default_agent_configs()["twin"].model.temperature
