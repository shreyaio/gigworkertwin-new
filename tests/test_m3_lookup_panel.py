"""M3 acceptance tests — lookup, odometer, panel. `docs/11` → M3.

The cross-process tests matter more than they look. `delta_hash` and the panel draw are both
claimed to be reproducible *across processes*, and a `hash()`-based or dict-order-based
implementation passes an in-process test and fails in production, where the panel would silently
differ between the session that created it and the session that resumed it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from twinlab.ingest.reference_store import reference
from twinlab.models.twin import PanelCandidate
from twinlab.orchestrator.odometer import (
    CONTROL_CODE,
    N_CODES,
    SHAM_CODE,
    InvalidVersionCode,
    advance,
    all_codes,
    code_from_index,
    combine,
    dials,
    digit_sum,
    index_from_code,
    validate_code,
)
from twinlab.orchestrator.panel import (
    InsufficientEligibleTwins,
    PanelError,
    PanelMismatch,
    draw_panel,
    eligible_candidates,
    panel_ids,
    require_same_panel,
)
from twinlab.variant.lookup import (
    ShamNotLookedUp,
    commitments_for_lever,
    dial_of,
    do_not_say,
    lookup,
    told_summary,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _in_fresh_process(code: str) -> str:
    """Run a snippet in a new interpreter and return its stdout.

    Python randomises string hash seeds per process, so this is what distinguishes a genuinely
    canonical digest from one that merely looks stable inside one run.
    """
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(["src", "."]),
        # The point of the fresh process: a different string-hash seed. A digest or a draw built
        # from `hash()` or from set iteration order differs between runs under this.
        "PYTHONHASHSEED": "random",
    }
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


# --------------------------------------------------------------------------- lookup


def test_lookup_01000_selects_exactly_the_three_threshold_2_1_gaps():
    """`docs/11` → M3: `lookup("01000").commitments` has exactly 2.1.a, 2.1.b, 2.1.c."""
    spec = lookup("01000")
    assert sorted(spec.commitments) == ["2.1.a", "2.1.b", "2.1.c"]
    assert len(spec.commitments) == 3
    assert spec.gaps_by_lever["L2"] == ["2.1.a", "2.1.b", "2.1.c"]
    assert all(spec.gaps_by_lever[lever] == [] for lever in ("L1", "L3", "L4", "L5"))


def test_the_specified_commitment_counts():
    """`docs/11` → M3: 02000 → 6, 22222 → 30, 00000 → 0."""
    assert len(lookup("02000").commitments) == 6
    assert len(lookup("22222").commitments) == 30
    assert len(lookup("00000").commitments) == 0
    assert set(lookup("22222").commitments) == set(reference().gaps)


def test_dial_two_is_cumulative_over_dial_one():
    """`ARCHITECTURE.md` §5: `2` closes X.1 ∪ X.2. That is what makes 0/1/2 ordinal."""
    for lever, position in (("L1", 0), ("L2", 1), ("L3", 2), ("L4", 3), ("L5", 4)):
        one = "".join("1" if i == position else "0" for i in range(5))
        two = "".join("2" if i == position else "0" for i in range(5))
        d1 = set(lookup(one).gaps_by_lever[lever])
        d2 = set(lookup(two).gaps_by_lever[lever])
        assert d1 < d2, lever
        assert d1 and d2 - d1, lever


def test_the_per_lever_gap_counts_match_the_frozen_table():
    """`ARCHITECTURE.md` §5: L3 dial 1 has four gaps and L4 dial 1 has three.

    Not five and four, because `3.1.a`, `3.1.c` and `4.1.c` are already **Met** and are therefore
    never gaps. This is also why the sham has content to describe.
    """
    counts = {
        "L1": (2, 3), "L2": (3, 6), "L3": (4, 8), "L4": (3, 8), "L5": (3, 5),
    }
    ref = reference()
    for lever, (one, two) in counts.items():
        assert len(ref.dial_lookup[lever]["1"]) == one, lever
        assert len(ref.dial_lookup[lever]["2"]) == two, lever
    for met in ("3.1.a", "3.1.c", "4.1.c"):
        assert met not in reference().gaps


def test_the_commitment_text_is_copied_verbatim_from_gaps_json():
    """I1 — the commitment text *is* the treatment. Nothing paraphrases it."""
    ref = reference()
    spec = lookup("22222")
    for gap_id, text in spec.commitments.items():
        assert text == ref.gaps[gap_id].commitment


def test_lookup_is_pure_and_consults_no_model():
    """I1 — identical input, byte-identical output, every time."""
    a, b = lookup("21122"), lookup("21122")
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()


def test_lookup_does_not_alias_the_frozen_reference_data():
    """A caller mutating the result must not be able to edit the frozen data in memory."""
    spec = lookup("01000")
    spec.gaps_by_lever["L2"].append("2.2.a")
    assert reference().dial_lookup["L2"]["1"] == ["2.1.a", "2.1.b", "2.1.c"]
    assert lookup("01000").gaps_by_lever["L2"] == ["2.1.a", "2.1.b", "2.1.c"]


def test_delta_hash_is_stable_across_processes():
    """`docs/11` → M3: `delta_hash` is stable across processes.

    Run in a fresh interpreter with a randomised hash seed, which is what catches a digest built
    from `hash()` or from dict iteration order.
    """
    local = lookup("21122").delta_hash
    remote = _in_fresh_process(
        "from twinlab.variant.lookup import lookup; print(lookup('21122').delta_hash)"
    )
    assert local == remote
    assert len(local) == 64


def test_delta_hash_identifies_the_selection_not_the_code():
    """The hash is over `gaps_by_lever`, so two different codes with different sets differ."""
    assert lookup("01000").delta_hash != lookup("02000").delta_hash
    assert lookup("00000").delta_hash != lookup("01000").delta_hash
    assert len({lookup(c).delta_hash for c in all_codes()}) == N_CODES


def test_all_243_codes_look_up_without_error():
    """The whole grid is a table read. Nothing about any cell is a special case."""
    total = 0
    for code in all_codes():
        spec = lookup(code)
        assert spec.version_code == code
        assert spec.fairwork_score == digit_sum(code)
        total += len(spec.commitments)
    assert total == 3645  # sum over the grid; each lever-dial contributes its gaps 81 times


# --------------------------------------------------------------------------- do_not_say


def test_do_not_say_excludes_2_2_material_from_01000():
    """`docs/03` §3 — the most important step in the pipeline.

    Because the Conditions digit is `1` and not `2`, the 2.2 gaps stay out. If any leaked into the
    text, `01000` and `02000` would be the same stimulus and the Conditions lever would stop
    measuring anything.
    """
    banned = do_not_say(lookup("01000"), "L2")
    for gap_id in ("2.2.a", "2.2.b", "2.2.c"):
        assert gap_id in banned
    for gap_id in ("2.1.a", "2.1.b", "2.1.c"):
        assert gap_id not in banned


def test_do_not_say_always_includes_the_three_already_met_criteria():
    """`docs/03` §3 — announcing something Uber already does is the sham's job, in one place."""
    for code in ("00000", "01000", "22222"):
        for lever in ("L1", "L2", "L3", "L4", "L5"):
            banned = do_not_say(lookup(code), lever)
            assert {"3.1.a", "3.1.c", "4.1.c"} <= set(banned), (code, lever)


def test_do_not_say_for_22222_still_bans_the_other_levers_gaps():
    """Even with every gap selected, a lever may only speak to its own."""
    spec = lookup("22222")
    banned = set(do_not_say(spec, "L2"))
    assert banned & set(spec.gaps_by_lever["L1"]) == set(spec.gaps_by_lever["L1"])
    assert not banned & set(spec.gaps_by_lever["L2"])


def test_do_not_say_rejects_an_unknown_lever():
    with pytest.raises(KeyError):
        do_not_say(lookup("01000"), "L9")


def test_commitments_for_lever_gives_the_design_agent_one_lever_only():
    """`docs/02` §4.1 — the design agent has no way to reach another lever's material."""
    spec = lookup("21122")
    for lever in ("L1", "L2", "L3", "L4", "L5"):
        subset = commitments_for_lever(spec, lever)
        assert set(subset) == set(spec.gaps_by_lever[lever])


def test_told_summary_is_researcher_facing_and_separate_from_the_scenario():
    """`docs/03` §4.3 — bullets for the researcher, prose for the twin. Never swapped."""
    summary = told_summary(lookup("01000"))
    assert len(summary["L2"]) == 3
    assert all(line.startswith("2.1.") for line in summary["L2"])
    assert summary["L1"] == []


def test_sham_is_not_a_lookup():
    """`ARCHITECTURE.md` §5.2 — SHAM's set is the three Met criteria, which are not gaps.

    It has no `dial_lookup` row, and assembling its text is M5's. Raising here rather than
    returning an empty spec keeps a control cell from silently becoming `00000`.
    """
    with pytest.raises(ShamNotLookedUp):
        lookup(SHAM_CODE)


def test_dial_of_reads_the_position_for_each_lever():
    assert dial_of("21122", "L1") == 2
    assert dial_of("21122", "L2") == 1
    assert dial_of("21122", "L5") == 2


# --------------------------------------------------------------------------- odometer


def test_the_specified_index_to_code_mappings():
    """`docs/11` → M3: 0→"00000", 1→"00001", 3→"00010", 81→"10000", 242→"22222"."""
    assert code_from_index(0) == "00000"
    assert code_from_index(1) == "00001"
    assert code_from_index(3) == "00010"
    assert code_from_index(81) == "10000"
    assert code_from_index(242) == "22222"


def test_index_from_code_is_the_exact_inverse_for_all_243():
    """`docs/11` → M3. Representation is least significant, which is what makes the grid scan."""
    for i in range(N_CODES):
        assert index_from_code(code_from_index(i)) == i
    codes = all_codes()
    assert len(codes) == N_CODES == 243
    assert len(set(codes)) == N_CODES


def test_the_digit_sum_identity():
    """`docs/11` → M3: `sum(digit_sum(code) for all 243) == 1215`.

    A closed-form check on the whole grid: 243 codes × 5 digits × mean digit 1 = 1215. It catches
    a silently truncated or duplicated odometer that a spot check would not.
    """
    assert sum(digit_sum(code) for code in all_codes()) == 1215
    assert digit_sum("21122") == 8
    assert digit_sum("00000") == 0
    assert digit_sum("22222") == 10


def test_representation_is_least_significant():
    """`ARCHITECTURE.md` §5.1 — consecutive indices differ in the Representation digit."""
    assert code_from_index(0) == "00000" and code_from_index(1) == "00001"
    assert code_from_index(2) == "00002" and code_from_index(3) == "00010"


def test_dials_maps_positions_to_levers_left_to_right():
    """`ARCHITECTURE.md` §5: Pay · Conditions · Contracts · Management · Representation."""
    assert dials("21122") == {"L1": 2, "L2": 1, "L3": 1, "L4": 2, "L5": 2}


def test_combine_takes_the_elementwise_maximum():
    """`docs/02` §8.3 — the joint cell of two codes, for an interaction's third leg."""
    assert combine("10000", "01000") == "11000"
    assert combine("20000", "10000") == "20000"
    assert combine("00000", "22222") == "22222"


def test_invalid_codes_are_rejected():
    for bad in ("0000", "000000", "01300", "0100a", "", "sham"):
        with pytest.raises(InvalidVersionCode):
            validate_code(bad)
    with pytest.raises(InvalidVersionCode):
        code_from_index(243)
    with pytest.raises(InvalidVersionCode):
        code_from_index(-1)


def test_sham_validates_as_a_code_but_is_not_a_grid_cell():
    """SHAM is a cell name, not a five-digit code. There are exactly two control cells."""
    assert validate_code(SHAM_CODE) == SHAM_CODE
    assert SHAM_CODE not in all_codes()
    assert CONTROL_CODE == "00000" and CONTROL_CODE in all_codes()


def test_advance_wraps_at_243():
    assert advance(0) == 1
    assert advance(242) == 0
    assert advance(240, 5) == 2


# --------------------------------------------------------------------------- panel


def _candidates(n: int = 40, *, passed: bool = True, source: str = "real") -> list:
    """A synthetic eligible population across four `city × service` strata."""
    cities = ["Mumbai", "Delhi"]
    services = ["cab", "bike"]
    out = []
    for i in range(n):
        out.append(PanelCandidate(
            twin_id=f"T{i:03d}",
            source=source,
            city=cities[i % 2],
            service=services[(i // 2) % 2],
            quality_passed=passed,
        ))
    return out


def test_the_panel_draw_is_reproducible_from_seed_size_and_eligible_set():
    """`docs/11` → M3. Same three inputs, same panel — including the draw order."""
    pool = _candidates()
    first = draw_panel(pool, panel_size=20, panel_seed=42)
    second = draw_panel(pool, panel_size=20, panel_seed=42)
    assert [m.model_dump() for m in first] == [m.model_dump() for m in second]
    assert len(first) == 20
    assert [m.position for m in first] == list(range(20))


def test_the_panel_draw_does_not_depend_on_candidate_order():
    """Rows come back from a database in no guaranteed order; the panel must not follow it."""
    pool = _candidates()
    shuffled = list(reversed(pool))
    assert panel_ids(draw_panel(pool, panel_size=20, panel_seed=7)) == panel_ids(
        draw_panel(shuffled, panel_size=20, panel_seed=7)
    )


def test_the_panel_draw_is_reproducible_across_processes():
    """`docs/11` → M3: "across processes".

    Run in a fresh interpreter with a randomised hash seed. A draw that iterated a set or a dict
    would pass the in-process test and silently differ between the session that created the panel
    and the session that resumed it.
    """
    snippet = (
        "from twinlab.models.twin import PanelCandidate;"
        "from twinlab.orchestrator.panel import draw_panel;"
        "cities=['Mumbai','Delhi'];services=['cab','bike'];"
        "pool=[PanelCandidate(twin_id=f'T{i:03d}',source='real',city=cities[i%2],"
        "service=services[(i//2)%2],quality_passed=True) for i in range(40)];"
        "print([m.twin_id for m in draw_panel(pool,panel_size=20,panel_seed=42)])"
    )
    remote = _in_fresh_process(snippet)
    local = [m.twin_id for m in draw_panel(_candidates(), panel_size=20, panel_seed=42)]
    assert json.loads(remote.replace("'", '"')) == local


def test_a_different_seed_gives_a_different_panel():
    """Otherwise the seed is decoration and the draw is not actually sampling."""
    pool = _candidates()
    a = panel_ids(draw_panel(pool, panel_size=20, panel_seed=1))
    b = panel_ids(draw_panel(pool, panel_size=20, panel_seed=2))
    assert a != b


def test_the_panel_is_stratified_on_city_by_service_and_proportional():
    """`docs/03` §9.1 — stratified on `city × service`, proportional to the eligible population."""
    pool = _candidates(40)          # four strata, 10 each
    panel = draw_panel(pool, panel_size=20, panel_seed=42)
    counts: dict[str, int] = {}
    for member in panel:
        counts[member.stratum] = counts.get(member.stratum, 0) + 1
    assert set(counts) == {"Mumbai|cab", "Mumbai|bike", "Delhi|cab", "Delhi|bike"}
    assert set(counts.values()) == {5}, counts


def test_proportional_allocation_follows_uneven_strata():
    """A stratum twice the size of another gets about twice the seats."""
    pool = [
        PanelCandidate(twin_id=f"A{i:03d}", source="real", city="Mumbai", service="cab",
                       quality_passed=True) for i in range(30)
    ] + [
        PanelCandidate(twin_id=f"B{i:03d}", source="real", city="Delhi", service="cab",
                       quality_passed=True) for i in range(10)
    ]
    panel = draw_panel(pool, panel_size=20, panel_seed=3)
    counts: dict[str, int] = {}
    for member in panel:
        counts[member.stratum] = counts.get(member.stratum, 0) + 1
    assert counts == {"Mumbai|cab": 15, "Delhi|cab": 5}


def test_allocation_redistributes_when_a_stratum_is_smaller_than_its_quota():
    """A tiny stratum cannot supply its proportional share; the rest make up the seats."""
    pool = [
        PanelCandidate(twin_id=f"A{i:03d}", source="real", city="Mumbai", service="cab",
                       quality_passed=True) for i in range(19)
    ] + [
        PanelCandidate(twin_id="B000", source="real", city="Delhi", service="bike",
                       quality_passed=True)
    ]
    panel = draw_panel(pool, panel_size=20, panel_seed=5)
    assert len(panel) == 20
    assert panel_ids(panel) == frozenset(c.twin_id for c in pool)


def test_the_panel_excludes_twins_that_did_not_pass_the_quality_gate():
    """`docs/11` → M3, and I14. A twin that failed the gate is in no cell, and is never tuned."""
    pool = _candidates(20, passed=True) + [
        PanelCandidate(twin_id=f"F{i:03d}", source="real", city="Mumbai", service="cab",
                       quality_passed=False) for i in range(20)
    ]
    panel = draw_panel(pool, panel_size=20, panel_seed=42)
    assert all(not tid.startswith("F") for tid in panel_ids(panel))
    assert len(eligible_candidates(pool)) == 20


def test_the_panel_excludes_manual_twins():
    """`docs/11` → M3, and `docs/03` §9.3.

    A manual twin has no real survey row, therefore no holdout and no quality score. It is a
    sandbox object and is never eligible — even if something marked it quality-passed.
    """
    pool = _candidates(20) + [
        PanelCandidate(twin_id=f"M{i:03d}", source="manual", city="Mumbai", service="cab",
                       quality_passed=True) for i in range(20)
    ]
    assert all(not c.twin_id.startswith("M") for c in eligible_candidates(pool))
    panel = draw_panel(pool, panel_size=20, panel_seed=42)
    assert all(not tid.startswith("M") for tid in panel_ids(panel))
    # And 'manual' is in no population's source set at all.
    for population in ("real", "synthetic", "both"):
        assert all(
            not c.twin_id.startswith("M") for c in eligible_candidates(pool, population)
        )


def test_the_population_setting_selects_the_source():
    pool = _candidates(10, source="real") + [
        PanelCandidate(twin_id=f"S{i:03d}", source="synthetic", city="Delhi", service="cab",
                       quality_passed=True) for i in range(10)
    ]
    assert len(eligible_candidates(pool, "real")) == 10
    assert len(eligible_candidates(pool, "synthetic")) == 10
    assert len(eligible_candidates(pool, "both")) == 20
    with pytest.raises(PanelError, match="unknown population"):
        eligible_candidates(pool, "everyone")


def test_too_few_eligible_twins_raises_rather_than_drawing_a_short_panel():
    """A panel of 15 recorded as `panel_size = 20` would misstate the study.

    `sessions.panel_size` is frozen onto the session and reported with its results, so the honest
    outcome is to refuse and tell the researcher.
    """
    with pytest.raises(InsufficientEligibleTwins, match="15 eligible"):
        draw_panel(_candidates(15), panel_size=20, panel_seed=42)


def test_a_panel_of_zero_is_refused_and_names_i15():
    """I15 — a panel of zero would make every run `twins_n = 0`, which is never a result."""
    with pytest.raises(InsufficientEligibleTwins, match="I15"):
        draw_panel(_candidates(20, passed=False), panel_size=20, panel_seed=42)
    with pytest.raises(InsufficientEligibleTwins, match="I15"):
        draw_panel([], panel_size=20, panel_seed=42)


def test_panel_size_must_be_at_least_one():
    with pytest.raises(PanelError, match="at least 1"):
        draw_panel(_candidates(), panel_size=0, panel_seed=42)


# --------------------------------------------------------------------------- PanelMismatch


def test_two_sessions_with_different_panels_raise_panel_mismatch():
    """`docs/11` → M3: a cross-session interaction is refused. I14.

    `extra = shift(A∪B) − (shift(A) + shift(B))` is arithmetic on incomparable numbers when the
    legs were answered by different people.
    """
    pool = _candidates(40)
    session_a = draw_panel(pool, panel_size=20, panel_seed=1)
    session_b = draw_panel(pool, panel_size=20, panel_seed=2)

    with pytest.raises(PanelMismatch) as exc:
        require_same_panel(("session A", session_a), ("session B", session_b))
    message = str(exc.value)
    assert "session A" in message and "session B" in message, "the error must name both panels"
    assert "I14" in message


def test_the_same_panel_compares_cleanly_across_three_legs():
    """The A, B and A∪B case an interaction actually needs."""
    panel = draw_panel(_candidates(40), panel_size=20, panel_seed=1)
    shared = require_same_panel(
        ("10000", panel), ("01000", list(panel)), ("11000", list(reversed(panel)))
    )
    assert shared == panel_ids(panel)


def test_panel_comparison_is_order_independent_but_membership_sensitive():
    """Draw order is provenance; membership is comparability."""
    panel = draw_panel(_candidates(40), panel_size=20, panel_seed=1)
    require_same_panel(("a", panel), ("b", list(reversed(panel))))
    with pytest.raises(PanelMismatch):
        require_same_panel(("a", panel), ("b", panel[:-1]))


def test_require_same_panel_needs_two_panels():
    panel = draw_panel(_candidates(40), panel_size=20, panel_seed=1)
    with pytest.raises(PanelError, match="at least two"):
        require_same_panel(("only", panel))
