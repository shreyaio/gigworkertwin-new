"""The `v6` individuality layer. `generator/voice.py`, `docs/06` §4.

What these tests are defending. Up to `v5` a synthetic respondent's 39 free-text answers came from
two constant banks: the 37 why-probes from a flat four-string tuple with no reference to the item
or to the answer just drawn, and Part 14 from a fixed five-tuple with **no RNG call at all**. The
free-text word set was therefore *byte-identical* across the panel (measured Jaccard 1.000), and
the battery answers were drawn with a between-driver SD of ~0.62 points, so four respondents in
five gave the same integer on a 5-point item.

The consequence was not cosmetic. `docs/08` §4 test 1 asks whether a twin's answers fit its own
driver better than a randomly paired one, and wants a gap of half a scale point. With a panel that
uniform the *ceiling* on that gap — what a perfect oracle twin could score — was about 0.70, so
the threshold was asking for most of a ceiling nothing could clear. These tests pin the three
properties that fixed it, and the two that must not regress while it is fixed.

No LLM and no database here: every assertion is over deterministic Python, as the rest of
`generator/` is.
"""

from __future__ import annotations

import itertools
import re
import statistics as st

import pytest

from twinlab.generator.synthetic import (
    OWN_WORDS_CONSTRUCT,
    spec_from_config,
    synthetic_payload,
)
from twinlab.generator.voice import (
    BANDS,
    CIRCUMSTANCE,
    NO_INCIDENT,
    OWN_WORDS_BANK,
    STANCE,
    VoiceBankIncomplete,
    band_of,
    band_of_target,
    draw_voice,
    facts_of,
)
from twinlab.ingest.reference_store import reference
from twinlab.ingest.survey_intake import form_map
from twinlab.models.reference import CONSTRUCTS
from twinlab.models.twin import OWN_WORDS_IDS, WHY_PROBE_ANCHOR, WHY_PROBE_IDS

#: The batch's own `lever_reactions`, which is what `facts_of` is handed for a respondent drawn
#: at the default salience spread's centre. `v10` made the weights an argument rather than a
#: batch constant, so a caller has to say which weighting a respondent carries.
BATCH_WEIGHTS: dict[str, float] = {"L1": 2.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0}

#: Big enough that a panel-level statistic means something, small enough to stay a unit test.
PANEL = 30
SEED = 4201
ARM = "MGT1"


@pytest.fixture(scope="module")
def ref():
    return reference()


@pytest.fixture(scope="module")
def keys():
    """``target -> "SECTION|TITLE"``, so a test can find an answer in a Form-shaped payload."""
    return {target: key for key, target in form_map().items()}


@pytest.fixture(scope="module")
def panel(ref):
    """One batch of payloads at the shipped defaults."""
    spec = spec_from_config(SEED)
    return [
        synthetic_payload(seed=SEED, index=i, arm=ARM, ref=ref, spec=spec)
        for i in range(PANEL)
    ]


def _answers(payload, keys):
    return {f"{a['section']}|{a['title']}": a["value"] for a in payload["answers"]}


def _free_text(payload, keys):
    got = _answers(payload, keys)
    whys = [str(got[keys[f"why:{p}"]]) for p in WHY_PROBE_IDS]
    own = [str(got[keys[f"own_words:{o}"]]) for o in OWN_WORDS_IDS]
    return whys, own


# --------------------------------------------------------------------------- the banks


def test_every_bank_cell_is_populated_and_digit_free(ref):
    """A missing cell raises rather than borrowing a neighbouring band (`CLAUDE.md` rule 7).

    The digit half is I7's. The persona builder quotes a driver's words verbatim and never edits
    them, so this module is the only thing standing between a numeral in a bank and a numeral in
    a persona passage — where a twin would do arithmetic on it instead of reasoning from
    experience.
    """
    from twinlab.generator.voice import assert_banks_complete

    blocks = tuple(sorted({c.block for c in CONSTRUCTS}))
    assert blocks, "the reference data defines no construct blocks"
    assert_banks_complete(blocks, OWN_WORDS_IDS)

    # And the check itself bites: a bank with a digit in it must be caught, or the guard above
    # is decoration. `STANCE` is patched rather than mocked so the real check runs.
    STANCE["FAIR"]["mid"] = (*STANCE["FAIR"]["mid"], "it was 5 out of 7 that week")
    try:
        with pytest.raises(VoiceBankIncomplete, match="I7"):
            assert_banks_complete(blocks, OWN_WORDS_IDS)
    finally:
        STANCE["FAIR"]["mid"] = STANCE["FAIR"]["mid"][:-1]
    assert_banks_complete(blocks, OWN_WORDS_IDS)


def test_the_stance_bank_covers_every_block_a_probe_can_anchor_to(ref):
    """Every why-probe's anchor item has a stance cell, so no probe can fail at generation.

    `WHY_CONTROL`, `WHY_SATISFACTION` and `WHY_OTHER_WORK` anchor to `PAC11`, `SAT1` and `DEP1` —
    items in blocks the bank must also cover, which an item-keyed bank would have missed.
    """
    for probe in WHY_PROBE_IDS:
        block = ref.items[WHY_PROBE_ANCHOR[probe]].block
        assert block in STANCE, f"{probe} anchors to a {block} item with no stance bank"
        for band in BANDS:
            assert STANCE[block][band], f"{block}/{band} is empty"


def test_an_unknown_block_or_tag_raises_rather_than_falling_back():
    """Rule 7: an unmapped key raises. A fallback would be a silent skip wearing a disguise."""
    import random

    from twinlab.generator.voice import circumstance_for, stance_for

    rng = random.Random(0)
    with pytest.raises(VoiceBankIncomplete):
        stance_for("NOSUCHBLOCK", "mid", rng)
    with pytest.raises(VoiceBankIncomplete):
        stance_for("FAIR", "enthusiastic", rng)
    with pytest.raises(VoiceBankIncomplete):
        circumstance_for("city:Atlantis", rng)


def test_an_unmapped_service_or_vehicle_raises():
    """A respondent drawn with a fact the bank cannot speak to is an error, not a blank clause."""
    with pytest.raises(VoiceBankIncomplete):
        facts_of(
            city="Mumbai",
            service="Helicopter",
            tenure_months=12,
            dependants=2,
            vehicle_arrangement="Own outright",
            multi_apping=False,
            edep_position=0.5,
            reactivity=1.0,
            lever_weights=BATCH_WEIGHTS,
        )


# --------------------------------------------------------------------------- banding


@pytest.mark.parametrize(
    ("value", "points", "expected"),
    [
        (1, 7, "very_low"),
        (4, 7, "mid"),
        (7, 7, "very_high"),
        (1, 5, "very_low"),
        (3, 5, "mid"),
        (5, 5, "very_high"),
    ],
)
def test_a_five_and_a_seven_point_item_band_the_same_way(value, points, expected):
    """One bank serves both scale lengths because the band is a *position*, not a raw value."""
    assert band_of(value, points) == expected


def test_a_reverse_coded_item_bands_on_its_mirrored_position():
    """`SAT2` answered low is a *satisfied* respondent, and its why must say so.

    Reading the raw value here would attach a sour explanation to a contented respondent, so the
    SAT block would contradict itself — the same failure as drawing reverse items forward, which
    is what `v3` had to fix in the numbers.
    """
    assert band_of(2, 7, reverse_coded=True) == "high"
    assert band_of(7, 7, reverse_coded=True) == "very_low"
    assert band_of(2, 7, reverse_coded=False) == "low"


def test_a_whys_band_matches_the_answer_it_explains(ref, keys, panel):
    """I6's point, applied to the free text: the explanation belongs to *that* rating.

    This is the `v5` defect in test form. A respondent who had just strongly agreed that the app
    controls their work had a one-in-four chance of explaining it with "sometimes it feels fair
    and sometimes it does not" — text that contradicted the clause the persona builder attached
    it to, and so taught the twin that the words do not predict the numbers.
    """
    checked = 0
    for payload in panel:
        got = _answers(payload, keys)
        for probe in WHY_PROBE_IDS:
            anchor = WHY_PROBE_ANCHOR[probe]
            item = ref.items[anchor]
            band = band_of(
                int(got[keys[anchor]]),
                ref.scale_points(anchor),
                reverse_coded=item.reverse_coded,
            )
            text = str(got[keys[f"why:{probe}"]])
            opening = STANCE[item.block][band]
            assert any(text.startswith(v) for v in opening), (
                f"{payload['response_id']} {probe}: the why opens on text from a band other "
                f"than {band}, which is the rating it is attached to"
            )
            checked += 1
    assert checked == PANEL * len(WHY_PROBE_IDS)


def test_part_fourteen_is_banded_on_the_construct_its_prompt_asks_about(ref, keys, panel):
    """Each of the five prompts reads its own construct, not one shared mood.

    `OWN5` is the one that earns the most: banded on `EXIT`, a respondent who wants out says
    something structurally different from one who means to stay, and those are precisely the H2
    answers a wrong-person comparison scores the twin against.
    """
    assert set(OWN_WORDS_CONSTRUCT) == set(OWN_WORDS_IDS)
    codes = {c.code for c in CONSTRUCTS}
    assert set(OWN_WORDS_CONSTRUCT.values()) <= codes
    # OWN3 is the exception by design: a respondent drawn without an incident has no story to
    # narrate at any fairness band, so it has a cell of its own.
    assert OWN_WORDS_BANK["OWN3"][NO_INCIDENT]


def test_the_no_incident_cell_does_not_claim_a_good_support_experience():
    """A driver who was never blocked must not thereby claim their one request went well.

    `v6` first reused the top fairness band for this, which produced a respondent who rated
    fairness at the floor and still said their one request for help was handled at once — the
    `v5` incoherence in a new place.
    """
    top = set(OWN_WORDS_BANK["OWN3"]["very_high"])
    none = set(OWN_WORDS_BANK["OWN3"][NO_INCIDENT])
    assert not (top & none)
    assert all("never had to ask" in t or "no story" in t or "nothing like that" in t
               for t in none)


# --------------------------------------------------------------------------- individuality


def test_no_two_respondents_share_a_part_fourteen_block(keys, panel):
    """The `v5` defect this layer exists to remove, as a regression test.

    `_OWN_WORDS` was a fixed five-tuple consumed with **no RNG call**, so the passage's longest
    unstructured block — its closing section, and the most attributable text a reader has — was
    byte-identical for every twin in every batch at every seed. A wrong-person comparison had
    nothing to discriminate on there, for one hundred per cent of the panel, at any dial setting.
    """
    blocks = [" | ".join(_free_text(p, keys)[1]) for p in panel]
    assert len(set(blocks)) == len(blocks), "two respondents told the same five stories"


def test_the_panel_does_not_share_one_free_text_vocabulary(keys, panel):
    """Panel-wide word overlap. At `v5` this was 1.000 — the same word set for everybody."""
    texts = [" ".join(sum(_free_text(p, keys), [])) for p in panel]
    overlaps = [
        len(set(a.split()) & set(b.split())) / len(set(a.split()) | set(b.split()))
        for a, b in itertools.combinations(texts, 2)
    ]
    assert st.mean(overlaps) < 0.6, (
        f"mean Jaccard {st.mean(overlaps):.3f}: the panel is sharing one vocabulary, which is "
        "what made every synthetic persona read as the same person"
    )


def test_a_respondent_keeps_one_voice_across_the_whole_passage(keys, panel):
    """Attribution needs consistency, not only variety.

    Thirty-nine independently sampled good sentences read as a committee. The test looks for the
    recurrence that makes them read as one driver: a respondent's own circumstance clauses are
    drawn from their own seven facts, so some fragments repeat *within* a respondent far more
    often than they appear across the panel.
    """
    for payload in panel[:8]:
        whys, _ = _free_text(payload, keys)
        # Every circumstance fragment this respondent used must be one their own facts allow.
        used = {
            frag
            for frag in (f for variants in CIRCUMSTANCE.values() for f in variants)
            if any(frag in w for w in whys)
        }
        assert used, f"{payload['response_id']} used no circumstance clause at all"


def test_the_battery_can_discriminate_between_two_drivers(ref, keys, panel):
    """The ceiling test, and the reason `between_driver_swing` exists.

    `docs/08` §4 test 1 wants a wrong-person gap of half a scale point. The gap cannot exceed the
    mean absolute difference between two random drivers' answers, so if that figure sits near the
    threshold the test is unpassable however good the twin is. At the hard-coded `1.5` this was
    ~0.70 against a 0.5 threshold; the default `2.4` puts it near 1.07.

    This asserts the **ceiling**, not that any twin clears it. No model is called here.
    """
    vectors = []
    for payload in panel:
        got = _answers(payload, keys)
        vectors.append(
            {i: int(got[keys[i]]) for i in ref.battery_item_ids if keys.get(i) in got}
        )
    diffs = []
    for a, b in itertools.combinations(vectors, 2):
        shared = [k for k in a if k in b]
        diffs.append(sum(abs(a[k] - b[k]) for k in shared) / len(shared))
    assert st.mean(diffs) > 0.9, (
        f"mean between-driver difference {st.mean(diffs):.3f} leaves no room above the "
        "half-point wrong-person threshold docs/08 §4 test 1 asks for"
    )


def test_raising_between_driver_signal_did_not_cost_construct_reliability(ref, keys):
    """The trade this change refuses to make.

    Raising `likert_sd` would widen the panel too, and far more cheaply — but as noise
    uncorrelated with the construct, which buys apparent individuality by destroying the
    reliability the PLS-SEM needs. The signal was raised **between** respondents instead, so
    every construct's alpha must hold up rather than fall.

    Reverse items are recoded before summing; alpha over a block containing a raw reverse item is
    negative by construction and would say nothing about the generator.
    """
    spec = spec_from_config(SEED)
    vectors = []
    for i in range(60):
        got = _answers(
            synthetic_payload(seed=SEED, index=i, arm=ARM, ref=ref, spec=spec), keys
        )
        vec = {}
        for item_id in ref.battery_item_ids:
            if keys.get(item_id) not in got:
                continue
            value = int(got[keys[item_id]])
            if ref.items[item_id].reverse_coded:
                value = ref.scale_points(item_id) + 1 - value
            vec[item_id] = value
        vectors.append(vec)

    for construct in CONSTRUCTS:
        ids = [i.item_id for i in ref.block_items(construct.block)]
        ids = [i for i in ids if all(i in v for v in vectors)]
        if len(ids) < 2:
            continue
        item_var = sum(st.pvariance([v[i] for v in vectors]) for i in ids)
        total_var = st.pvariance([sum(v[i] for i in ids) for v in vectors])
        k = len(ids)
        alpha = (k / (k - 1)) * (1 - item_var / total_var)
        assert alpha > 0.7, f"{construct.code} alpha fell to {alpha:.3f}"


def test_answers_do_not_pile_up_at_the_ends_of_their_scales(ref, keys, panel):
    """A wider panel must not be bought by clipping.

    `_likert` clamps to the item's own scale, which is correct for generation — but a swing wide
    enough to push a large share of answers onto the floor or the ceiling would flatten the
    distribution into something no real sample looks like, and would destroy variance at the
    extremes rather than create it.
    """
    at_bound = total = 0
    for payload in panel:
        got = _answers(payload, keys)
        for item_id in ref.battery_item_ids:
            if keys.get(item_id) not in got:
                continue
            total += 1
            if int(got[keys[item_id]]) in (1, ref.scale_points(item_id)):
                at_bound += 1
    assert at_bound / total < 0.10, f"{at_bound / total:.1%} of answers sit at a scale bound"


# --------------------------------------------------------------------------- determinism


def test_same_seed_same_free_text(ref, keys):
    """`docs/09` §2. The composed text is a function of the seed, not of iteration order."""
    spec = spec_from_config(SEED)
    first = synthetic_payload(seed=SEED, index=3, arm=ARM, ref=ref, spec=spec)
    second = synthetic_payload(seed=SEED, index=3, arm=ARM, ref=ref, spec=spec)
    assert _free_text(first, keys) == _free_text(second, keys)


def test_a_voice_is_a_function_of_the_stream_it_is_given():
    """Two identical streams give two identical voices, and leave the stream in the same place.

    Not a *draw count* test. `rng.choice` and `rng.sample` reach `_randbelow`, whose rejection
    sampling consumes a variable number of primitive values by design, so nothing built on them
    has a constant draw count and asserting one would be asserting a CPython internal.

    What the reproducibility guarantee (`docs/09` section 2) actually needs is weaker and
    sufficient: the draws are a deterministic function of the seed, so a voice cannot shift what
    follows it in a way that depends on anything but the seed and the spec. That is what this
    pins, and `test_the_whole_payload_reproduces_in_a_fresh_process` pins the end-to-end form.
    """
    import random

    facts = facts_of(
        city="Pune",
        service="Auto rickshaw",
        tenure_months=20,
        dependants=3,
        vehicle_arrangement="Own with a loan",
        multi_apping=True,
        edep_position=0.8,
        reactivity=1.0,
        lever_weights=BATCH_WEIGHTS,
    )
    seen = set()
    for seed in range(60):
        left, right = random.Random(seed), random.Random(seed)
        assert draw_voice(left, facts=facts, incident_share=0.35) == draw_voice(
            right, facts=facts, incident_share=0.35
        )
        # The stream is left in the same place, so every later answer lands identically too.
        assert [left.random() for _ in range(5)] == [right.random() for _ in range(5)]
        voice = draw_voice(random.Random(seed), facts=facts, incident_share=0.35)
        seen.add((voice.register, voice.verbosity, len(voice.motifs), voice.fact_offset))
    assert len(seen) > 10, "every seed drew the same voice, so the panel has one register"


def test_the_whole_payload_reproduces_in_a_fresh_process(tmp_path):
    """"Same seed, same batch, **across processes**" -- the generator module's own promise.

    Run in a subprocess rather than twice in this one, because the failure this guards against is
    a draw that reads process state: the global RNG, a set's iteration order, or a dict built in
    insertion order. All three reproduce perfectly within one process and diverge between two.
    """
    import json
    import subprocess
    import sys
    import textwrap
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "once.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json, sys
            sys.path[:0] = [{str(root / "src")!r}, {str(root)!r}]
            from twinlab.generator.synthetic import spec_from_config, synthetic_payload

            spec = spec_from_config({SEED})
            rows = [
                synthetic_payload(seed={SEED}, index=i, arm={ARM!r}, spec=spec)
                for i in range(4)
            ]
            print(json.dumps(rows))
            """
        ),
        encoding="utf-8",
    )
    runs = []
    for _ in range(2):
        out = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root),
        )
        runs.append(json.loads(out.stdout))
    assert runs[0] == runs[1]
    # And it matches what this process draws, so the in-process tests test the real thing.
    spec = spec_from_config(SEED)
    here = [synthetic_payload(seed=SEED, index=i, arm=ARM, spec=spec) for i in range(4)]
    assert json.loads(json.dumps(here)) == runs[0]


def test_band_of_target_reads_the_dashboards_common_scale():
    """Part 14 bands on a construct target, which is always on 1–7 whatever the item scale is."""
    assert band_of_target(1.0) == "very_low"
    assert band_of_target(4.0) == "mid"
    assert band_of_target(7.0) == "very_high"


def test_a_long_block_does_not_repeat_one_sentence(ref, keys, panel):
    """An eleven-item block must not say the same thing five times.

    `PAC` has eleven items and a respondent's eleven answers mostly land in **one** band -- that
    is what having a disposition means. Drawing independently from a cell then put one sentence in
    the block five times, which reads as a template however well the bank is written, so the
    composition draws without replacement and refills with a fresh shuffle when a cell runs out.
    """
    worst = 0
    for payload in panel:
        got = _answers(payload, keys)
        openings: dict[str, int] = {}
        for probe in WHY_PROBE_IDS:
            if ref.items[WHY_PROBE_ANCHOR[probe]].block != "PAC":
                continue
            text = str(got[keys[f"why:{probe}"]])
            stance = next(
                v
                for cell in STANCE["PAC"].values()
                for v in cell
                if text.startswith(v)
            )
            openings[stance] = openings.get(stance, 0) + 1
        worst = max(worst, max(openings.values()))
    assert worst <= 3, (
        f"one PAC stance clause appeared {worst} times in a single respondent's eleven items"
    )


def test_reactivity_holds_several_circumstance_slots_so_the_clause_is_legible():
    """`v9` — present is not the same as legible.

    At one slot in eight the clause surfaced one to three times in a 1,700-2,450 word passage,
    once at 93% of the way through, and a twin directed to find it tracked the real reactivity at
    only r +0.20 against a +0.59 ceiling. Asserted as a share of the tuple rather than as a count
    of mentions, because the rotation decides the mentions and the tuple is what this module owns.
    """
    from twinlab.generator.voice import facts_of

    facts = facts_of(
        city="Pune", service="Auto rickshaw", tenure_months=20, dependants=3,
        vehicle_arrangement="Own with a loan", multi_apping=True, edep_position=0.8,
        reactivity=0.6, lever_weights=BATCH_WEIGHTS,
    )
    reactivity_slots = [f for f in facts if f.startswith("react:")]
    assert len(reactivity_slots) >= 3, "the clause needs enough slots to surface early and recur"
    assert len(set(reactivity_slots)) == 1, "a respondent has ONE reactivity, not several"
    # And it must not crowd out the rest: the other facts carry the baseline individuality a
    # wrong-person comparison reads.
    assert len(set(facts) - set(reactivity_slots)) >= 7


def test_salience_holds_several_circumstance_slots_so_the_clause_is_legible():
    """`v10` - the same legibility condition `v9` established for reactivity.

    Reactivity at one slot in eight tracked at r +0.20; at three slots it tracked at +0.87.
    Salience is read by the same Part 17 question and so needs comparable prominence. Asserted as
    a share of the tuple rather than as a count of mentions, because the rotation decides the
    mentions and the tuple is what this module owns.
    """
    from twinlab.generator.voice import facts_of

    facts = facts_of(
        city="Pune", service="Auto rickshaw", tenure_months=20, dependants=3,
        vehicle_arrangement="Own with a loan", multi_apping=True, edep_position=0.8,
        reactivity=0.6, lever_weights={"L1": 0.4, "L2": 1.0, "L3": 1.0, "L4": 2.6, "L5": 1.0},
    )
    salience_slots = [f for f in facts if f.startswith("salience:")]
    assert len(salience_slots) >= 3, "the clause needs enough slots to surface early and recur"
    assert len(set(salience_slots)) == 1, "a respondent weights ONE lever highest, not several"
    assert salience_slots[0] == "salience:appeals", (
        "the clause must name the lever this respondent actually weights highest"
    )
    # It must not crowd out the rest: the other facts carry the baseline individuality a
    # wrong-person comparison reads, and reactivity keeps its own three slots.
    assert len([f for f in facts if f.startswith("react:")]) >= 3
    assert len(set(facts) - set(salience_slots)) >= 8


def test_a_respondent_nothing_would_move_claims_no_salience_at_all():
    """`docs/06` 4's no-reaction null. A clause the generator did not draw is a fabrication.

    `CLAUDE.md` rule 7 cuts both ways here: an unmapped fact raises, and a fact the spec says
    does not exist is omitted rather than invented. A respondent whose every lever is at zero has
    no change that matters most to them, and the tuple is shorter by three.
    """
    from twinlab.generator.voice import facts_of

    facts = facts_of(
        city="Jaipur", service="Cab (sedan or hatchback)", tenure_months=48, dependants=0,
        vehicle_arrangement="Own outright", multi_apping=False, edep_position=0.2,
        reactivity=1.0, lever_weights=dict.fromkeys(("L1", "L2", "L3", "L4", "L5"), 0.0),
    )
    assert not [f for f in facts if f.startswith("salience:")]
    # Everything else about the respondent is unchanged, so the omission is local.
    assert "city:Jaipur" in facts
    assert len([f for f in facts if f.startswith("react:")]) >= 3


def test_an_unweighted_lever_in_the_salience_draw_raises():
    """A lever missing from the weights is an error, not a respondent with no opinion on it."""
    from twinlab.generator.voice import salience_tag

    with pytest.raises(VoiceBankIncomplete):
        salience_tag({"L1": 2.0, "L2": 1.0})


def test_no_salience_clause_names_a_lever_code_a_dial_or_a_number():
    """Rule 3 of Route A: natural language naming the thing, never the machinery.

    `L1`, a five-digit version code or a dial setting in a persona would be the generator telling
    the twin the answer in its own notation rather than a driver describing what they care about.
    """
    from twinlab.generator.voice import CIRCUMSTANCE, SALIENCE_BY_LEVER

    for tag in SALIENCE_BY_LEVER.values():
        for clause in CIRCUMSTANCE[tag]:
            assert not re.search(r"\bL[1-5]\b", clause), f"{clause!r} names a lever code"
            assert not re.search(r"\d", clause), f"{clause!r} carries a digit"
            assert clause == clause.strip(), f"{clause!r} is not trimmed"
