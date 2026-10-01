"""The seventeen invariants, as executable tests. `ARCHITECTURE.md` §2.

Every test here names its invariant in the docstring. They **accumulate**: this file starts at M2
and each later milestone adds the invariants its code makes testable. Nothing is quietly skipped —
:data:`DEFERRED` names every invariant that has no test yet and the milestone that owns it, and
:func:`test_every_invariant_is_either_tested_or_declared_deferred` fails if that bookkeeping drifts.

These exist because the study's validity rests on them. A change here is a research decision, not
an engineering one. **Never relax one to make a test pass.**
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from twinlab.agents.contract import (
    Defect,
    grounded,
    merge_valid,
    normalise_answers,
    offending_sentences,
    repair_instruction,
    run_answer_ladder,
    validate_answers,
)
from twinlab.agents.registry import ConfigError, build_agent, default_agent_configs, validate_config
from twinlab.agents.tools import TOOL_REGISTRY
from twinlab.db.client import DbError
from twinlab.ingest.reference_store import reference
from twinlab.models.agent import AgentConfig, ModelRef
from twinlab.models.analysis import AnalysisBundle
from twinlab.models.reference import ATTENTION_ITEMS, LEVER_BY_POSITION, MET_CRITERIA
from twinlab.models.twin import (
    Background,
    PanelCandidate,
    SurveyResponse,
    Twin,
    TwinAnswerSet,
)
from twinlab.models.variant import DIAL_ZERO_TEXT, LeverParagraph
from twinlab.orchestrator.panel import (
    InsufficientEligibleTwins,
    PanelMismatch,
    draw_panel,
    panel_ids,
    require_same_panel,
)
from twinlab.persona.builder import PersonaIncomplete, build_persona
from twinlab.persona.templates import TEMPLATES, anchor_for
from twinlab.variant.lookup import do_not_say, lookup

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

ALL_INVARIANTS = tuple(f"I{n}" for n in range(1, 18))

#: Invariants with no executable test yet, and the milestone that owns the code they describe.
#: Removing an entry here without adding a test makes the bookkeeping test fail.
#: Empty since M8. Every invariant I1-I17 now has an executable test naming it in its docstring.
#: A new invariant is added here with the milestone that owns it, and
#: :func:`test_every_invariant_is_either_tested_or_declared_deferred` fails if the bookkeeping
#: drifts **either way** — including declaring one deferred when a test already names it.
DEFERRED: dict[str, str] = {}


def _cfg(**overrides) -> AgentConfig:
    base = {
        "agent_id": "probe",
        "name": "Probe",
        "role": "a config under test",
        "model": ModelRef(name="gpt-oss:120b"),
        "system_prompt": "inline",
        "input_schema": "CoverageProbe",
        "output_schema": "CoverageVerdict",
    }
    return AgentConfig(**{**base, **overrides})


def _battery() -> tuple[list[str], dict[str, int]]:
    ref = reference()
    items = ref.battery_item_ids
    return items, {i: ref.scale_points(i) for i in items}


# --------------------------------------------------------------------------- I1


def test_i1_the_treatment_is_a_pure_lookup_with_no_model():
    """I1 — `version_code → DeltaSpec` is a pure lookup over `dial_lookup.json` and `gaps.json`.

    No model is consulted. Identical input, byte-identical output, every run, forever.
    """
    assert len(lookup("01000").commitments) == 3
    assert len(lookup("02000").commitments) == 6
    assert len(lookup("22222").commitments) == 30
    assert len(lookup("00000").commitments) == 0
    assert lookup("21122").model_dump_json() == lookup("21122").model_dump_json()

    ref = reference()
    for gap_id, text in lookup("22222").commitments.items():
        assert text == ref.gaps[gap_id].commitment, "the commitment text was not copied verbatim"


def test_i1_the_lookup_module_reaches_no_model_and_no_network():
    """I1 at the source level: nothing in `variant/lookup.py` can consult anything.

    An import of `agents/`, a provider library or `httpx` here would mean the treatment could stop
    being a table read without any test noticing.
    """
    tree = ast.parse((SRC / "twinlab" / "variant" / "lookup.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("httpx", "requests", "openai", "pydantic_ai", "supabase"):
        assert banned not in imported, f"lookup.py imports {banned}"
    assert "twinlab" in imported or not imported


def test_i1_the_exclusion_set_keeps_the_dials_distinguishable():
    """I1 with `docs/03` §3 — the step the whole design rests on.

    Because the Conditions digit is `1`, the 2.2 gaps stay out. If one leaked into the text,
    `01000` and `02000` would be the same stimulus and the Conditions lever would measure nothing.
    """
    banned = set(do_not_say(lookup("01000"), "L2"))
    assert {"2.2.a", "2.2.b", "2.2.c"} <= banned
    assert not banned & {"2.1.a", "2.1.b", "2.1.c"}
    assert set(MET_CRITERIA) <= banned
    assert lookup("01000").delta_hash != lookup("02000").delta_hash


# --------------------------------------------------------------------------- I2


def test_i2_the_design_agent_renders_and_never_proposes():
    """I2 — the design agent has no tools and cannot fetch a gap, a chunk or a criterion.

    If it could, an `01000` render could absorb threshold 2.2 material and `01000` would stop
    differing from `02000`. `tools: []` is enforced in `build_agent`, not left to discipline.
    """
    assert default_agent_configs()["design"].tools == []
    assert default_agent_configs()["design"].react is False
    with pytest.raises(ConfigError, match="I2"):
        validate_config(_cfg(agent_id="design", tools=list(TOOL_REGISTRY)[:1]))


# --------------------------------------------------------------------------- I3


def test_i3_a_commitment_outside_the_delta_spec_is_a_hard_failure():
    """I3 — containment is enforced, not trusted. **One hit fails the cell**, with no threshold.

    Threshold 2.2 material in an `01000` render makes `01000` and `02000` the same stimulus, and
    the Conditions lever stops measuring anything. Unlike a coverage failure, this is not
    detectable anywhere downstream, which is why there is no tolerance.
    """
    from twinlab.variant import checker as ck
    from twinlab.variant.lookup import commitments_for_lever, lookup
    from twinlab.variant.render import forbidden_for, load_style_contract

    spec = lookup("01000")
    allowed = commitments_for_lever(spec, "L2")
    forbidden = forbidden_for(spec, "L2")

    leaked = forbidden["2.2.a"]
    hits = ck.containment_hits(leaked, forbidden, allowed)
    assert "2.2.a" in hits

    report = ck.build_report(
        paragraphs={"L2": LeverParagraph(text=leaked)},
        dials={"L2": 1},
        style=load_style_contract(),
        coverage=dict.fromkeys(allowed, True),
        containment=hits,
    )
    assert not report.passed, "a containment hit must fail the cell"

    # And the gate is not vacuous: the same machinery clears text that carries no forbidden
    # commitment, so failure means something.
    assert ck.containment_hits(allowed["2.1.a"], forbidden, allowed) == []


def test_i3_every_render_passes_the_checker_before_a_twin_sees_it():
    """I3 — an unverified variant never reaches a twin.

    Asserted structurally: a `CheckerReport` is the only thing that says a variant may be used, and
    a refusal or a failed gate can never produce ``passed``.
    """
    from twinlab.variant import checker as ck
    from twinlab.variant.render import load_style_contract

    style = load_style_contract()
    refusal = ck.build_report(
        paragraphs={"L2": LeverParagraph(text="", status="cannot_render", reason="blocked")},
        dials={"L2": 1},
        style=style,
        coverage={},
        containment=[],
    )
    assert not refusal.passed


# --------------------------------------------------------------------------- I4


async def test_i4_lever_paragraphs_are_cached_on_lever_dial_style_version():
    """I4 — exactly **10** non-zero paragraphs plus one fixed zero string serve all 243 cells.

    The design agent runs 10 times per style version, not 243. Asserted on a call counter, and on
    the cache keys being exactly `(lever, dial, style_version)` for the ten non-zero combinations.
    """
    from twinlab.agents.registry import StubModelClient
    from twinlab.models.variant import CoverageVerdict
    from twinlab.models.variant import LeverParagraph as LP
    from twinlab.orchestrator.odometer import all_codes
    from twinlab.variant.render import ParagraphPool, render_all

    text = (
        "The way this works for you is changing from today onwards, and the notes below explain "
        "what that means in ordinary language. You can read them whenever you like, and they stay "
        "in the same place so you can find them again later. Nothing here asks anything further "
        "of you, and you can carry on driving exactly as before."
    )

    def handler(cfg, prompt, out):
        return LP(text=text) if out is LP else CoverageVerdict(entailed=True, reason="stub")

    client = StubModelClient(handler)
    pool = ParagraphPool(client=client)
    variants = await render_all(all_codes(), pool)

    assert len(variants) == 243
    assert client.call_count("design") == 10
    keys = pool.cached()
    assert len(keys) == 10
    assert {(lever, dial) for lever, dial, _ in keys} == {
        (lever, dial) for lever in LEVER_BY_POSITION for dial in (1, 2)
    }
    assert {version for _, _, version in keys} == {pool.style_version}


# --------------------------------------------------------------------------- I5


def test_i5_dial_zero_is_a_fixed_string():
    """I5 — `"No change from today."` is never generated and is byte-identical everywhere."""
    assert DIAL_ZERO_TEXT == "No change from today."
    import yaml

    from config.settings import CONFIG_DIR

    contract = yaml.safe_load((CONFIG_DIR / "style_contract.yaml").read_text(encoding="utf-8"))
    assert contract["dial_zero_text"] == DIAL_ZERO_TEXT, "the constant and the contract disagree"


# --------------------------------------------------------------------------- I6


def test_i6_the_twin_agent_cannot_fetch():
    """I6 — a twin that can fetch can read its own holdout answers.

    The losslessness and holdout-exclusion halves of I6 are M4's, when the persona builder exists;
    this is the half the registry can enforce today.
    """
    assert default_agent_configs()["twin"].tools == []
    assert default_agent_configs()["twin"].react is False
    with pytest.raises(ConfigError, match="I6"):
        validate_config(_cfg(agent_id="twin", tools=list(TOOL_REGISTRY)[:1]))


# --------------------------------------------------------------------------- I6 / I7


def _persona_row(**answer_overrides):
    """A complete, digit-free row, plus its holdout answers as a real row carries them."""
    ref = reference()
    twin = Twin(
        twin_id="INV-1", city="Mumbai", service="cab", age=34, tenure_months=28,
        background=Background(dependants=4, education="secondary school"),
    )
    answers = {
        i: (4 if ref.scale_points(i) == 5 else 5)
        for i in ref.battery_item_ids + ref.holdout_h2_item_ids + ref.holdout_h3_item_ids
    }
    answers.update(answer_overrides)
    return twin, SurveyResponse(twin_id="INV-1", answers=answers)


def test_i6_the_persona_holds_every_battery_item():
    """I6 — all 37 battery items contribute at least one clause; nothing is silently skipped.

    Asserted per item: a clause count of 37 would pass against a builder that rendered one item
    twice and another not at all.
    """
    ref = reference()
    twin, response = _persona_row()
    passage = build_persona(twin, response)
    assert passage.items_used == ref.battery_item_ids
    assert len(passage.items_used) == 37
    for item_id in ref.battery_item_ids:
        assert item_id in TEMPLATES, item_id


def test_i6_a_row_missing_a_battery_answer_is_refused():
    """I6 — losslessness is not negotiable, so a partial row does not become a shorter passage."""
    twin, response = _persona_row()
    partial = {k: v for k, v in response.answers.items() if k != "PAC4"}
    with pytest.raises(PersonaIncomplete, match="PAC4"):
        build_persona(twin, SurveyResponse(twin_id="INV-1", answers=partial))


def test_i6_the_persona_holds_no_holdout_material():
    """I6 — Parts 15, 16 and 17 are excluded absolutely.

    A twin that has read its own holdout answers cannot be validated. Two rows differing only in
    every holdout answer give the byte-identical passage.
    """
    ref = reference()
    twin, response = _persona_row()
    baseline = build_persona(twin, response)

    flipped = dict(response.answers)
    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        flipped[item_id] = 1 if flipped[item_id] != 1 else 2
    moved = build_persona(twin, SurveyResponse(twin_id="INV-1", answers=flipped))

    assert baseline.persona_hash == moved.persona_hash
    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        assert item_id not in baseline.items_used
        assert item_id not in TEMPLATES


def test_i7_the_persona_carries_words_not_numbers():
    """I7 — a `5` on a 7-point item becomes "I somewhat agree that…", never "I rated this 5".

    A twin shown numbers does arithmetic instead of reasoning from experience.
    """
    twin, response = _persona_row()
    text = build_persona(twin, response).text
    assert re.findall(r"\d", text) == [], text[:300]
    assert "I somewhat agree that" in text


def test_i7_no_item_renders_a_digit_at_any_value_on_its_own_scale():
    """I7, exhaustively over the register rather than over one fixture's answers."""
    ref = reference()
    for item_id in ref.battery_item_ids:
        scale_id = ref.items[item_id].scale_id
        for value in range(1, ref.scale_points(item_id) + 1):
            clause = TEMPLATES[item_id].format(anchor=anchor_for(scale_id, value))
            assert not re.search(r"\d", clause), f"{item_id}={value}: {clause}"


def test_i7_anchor_wording_is_per_scale():
    """I7 with `docs/03` §7.1 — a `4` on a 5-point item must not borrow the 7-point wording.

    Otherwise the same number means two different things inside one passage.
    """
    assert anchor_for("agree5", 4) == "I agree"
    assert anchor_for("agree7", 4) == "I neither agree nor disagree"


# --------------------------------------------------------------------------- I8


def test_i8_the_persona_and_the_round_prompt_are_separate_documents():
    """I8 — the persona says who this person is; the round prompt asks what they would now say.

    The whys live in the persona and must not travel with the stimulus. If they did, every twin
    would
    restate its own justifications under every counterfactual and would look immovable no matter
    what
    it was shown — which is the signal, destroyed.

    Also asserts the round carries no holdout item and no version code, and that the guard rejects
    each violation: a gate that cannot fail is not a gate.
    """
    from twinlab.agents.twin import (
        RoundPromptError,
        assert_no_forbidden_content,
        build_round_prompt,
        build_user_prompt,
    )
    from twinlab.models.reference import LEVER_BY_POSITION
    from twinlab.models.twin import Background, SurveyResponse, Twin

    ref = reference()
    why = "the app cancelled my ride near Andheri and nobody explained the reason to me"
    twin = Twin(
        twin_id="UBR-INV", city="Mumbai", service="cab", age=34, gender="Male",
        tenure_months=28, hours_per_week=58,
        background=Background(
            platform_count="2", other_apps="Ola", vehicle_arrangement="rented",
            dependants=4, other_household_income="none", education="secondary school",
            years_driving_before_uber=3.5,
        ),
    )
    answers = {
        i: (4 if ref.scale_points(i) == 5 else 5) for i in ref.battery_item_ids
    }
    persona = build_persona(
        twin, SurveyResponse(twin_id="UBR-INV", answers=answers, whys={"WHY_CONTROL": why})
    ).text
    assert why in persona, "the persona is lossless over the whys (I6)"

    round_prompt = build_round_prompt(
        persona_hash="a" * 64,
        paragraphs={lever: f"Paragraph for {lever}." for lever in LEVER_BY_POSITION},
        baseline=answers,
        battery={i: (ref.items[i].stem, ref.scale_points(i)) for i in ref.battery_item_ids},
        seed=4242,
    )
    prompt = build_user_prompt(round_prompt, persona)

    # The stimulus half carries no why-text, although the persona half does.
    stimulus = prompt.split("<<<END PERSONA>>>", 1)[1]
    assert why not in stimulus

    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        assert item_id not in prompt
    for code in ("01000", "02000", "22222", "SHAM"):
        assert code not in prompt

    assert_no_forbidden_content(
        prompt,
        holdout_ids=ref.holdout_h2_item_ids + ref.holdout_h3_item_ids,
        why_texts=[why],
        version_code="01000",
    )

    holdout = ref.holdout_h3_item_ids[0]
    with pytest.raises(RoundPromptError, match="holdout"):
        assert_no_forbidden_content(f"x {holdout} y", holdout_ids=[holdout], why_texts=[])
    with pytest.raises(RoundPromptError, match="stimulus"):
        assert_no_forbidden_content(
            f"<<<END PERSONA>>> {why}", holdout_ids=[], why_texts=[why]
        )


# --------------------------------------------------------------------------- I17


def test_i17_nothing_is_imputed():
    """I17 — a missing cell is reported, never estimated.

    `CLAUDE.md` rule 5: if an interaction needs three runs and has two, report which code to run. No
    estimates, no interpolation, no "approximately". This is where the study would most plausibly
    have cheated — two of three cells is *almost* enough, and an interpolated third leg would look
    exactly like a measured one in the finished table.
    """
    from twinlab.analysis.interactions import describe_missing, interaction
    from twinlab.analysis.metrics import MetricError, below_floor, compute_shifts, demand_floor
    from twinlab.models.analysis import Interaction, MissingInteraction

    shifts = {"01000": {"staying": 0.31}, "00010": {"staying": 0.09}}

    # Two legs of three: no number is produced, and the code to run is named.
    result = interaction("01000", "00010", "staying", shifts)
    assert isinstance(result, MissingInteraction)
    assert result.missing_codes == ["01010"]
    assert "01010" in describe_missing(result)
    assert "not estimated" in describe_missing(result)

    # With the third leg present it computes, so the refusal above is not vacuous.
    shifts["01010"] = {"staying": 0.22}
    assert isinstance(interaction("01000", "00010", "staying", shifts), Interaction)

    # A floor that was not measured is None, never 0.0 — an assumed floor is no floor.
    assert demand_floor(None, 0.05) is None
    assert below_floor(0.4, None) is None

    # And a cell no twin answered raises rather than scoring zero (I15's other face).
    with pytest.raises(MetricError):
        compute_shifts(
            baseline_vectors={"T1": {}}, variant_vectors={}, version_code="10000"
        )


# --------------------------------------------------------------------------- I9


async def test_i9_evidence_is_appended_and_the_pointer_is_flipped(backend):
    """I9 — nothing is overwritten; "latest" is a pointer flipped in the same transaction.

    A rerun supersedes; it does not erase.
    """
    common = {
        "p_twin_id": "t1", "p_session_id": None, "p_holdout_set": "H3", "p_arm": None,
        "p_items_n": 18, "p_pct_within_1": 0.9, "p_correlations": None, "p_kept": True,
        "p_repeats": 3, "p_detail": [], "p_model": "m", "p_config_version": 1,
    }
    await backend.rpc("quality_run_record", {**common, "p_mae": 0.9})
    await backend.rpc("quality_run_record", {**common, "p_mae": 0.4})
    rows = await backend.select("twin_quality_runs")
    assert len(rows) == 2, "the superseded row must still exist"
    assert [r["is_latest"] for r in rows].count(True) == 1


# --------------------------------------------------------------------------- I10


def test_i10_attention_checks_are_never_put_to_a_twin():
    """I10 — `AMQ6` and `ALGO5` are human data-quality devices. The battery is 37, not 39."""
    ref = reference()
    assert len(ref.battery_item_ids) == 37
    for item_id in ATTENTION_ITEMS:
        assert ref.items[item_id].attention_check
        assert item_id not in ref.battery_item_ids


def test_i10_the_twin_schema_refuses_an_attention_check():
    """I10 at the output boundary: an attention check in an answer vector is an `extra` item."""
    items, _ = _battery()
    vector = dict.fromkeys(items, 2)
    with pytest.raises(ValueError, match="extra="):
        TwinAnswerSet(answers={**vector, "AMQ6": 4})


# --------------------------------------------------------------------------- I11


def test_i11_the_prompt_is_hashed_so_a_round_is_reconstructible():
    """I11 — the prompt version is stored on every run; the prompt itself never is.

    Two runs with different `prompt_hash` values are not the same experiment.
    """
    configs = default_agent_configs()
    for cfg in configs.values():
        assert len(cfg.prompt_hash) == 64, cfg.agent_id
    assert len({c.prompt_hash for c in configs.values()}) == len(configs), "hashes collide"


def test_i11_no_module_writes_a_prompt_body_into_an_event_payload():
    """I11 and `ARCHITECTURE.md` §7.2 — the prompt is rebuilt, never stored.

    At panel scale, prompt bodies in `run_events` would exhaust the 500 MB tier on their own. The
    DDL cap is the hard guard (`run_events_payload_small`); this is the source-level one.
    """
    banned = re.compile(r"payload\s*=\s*\{[^}]*\b(system_prompt|user_prompt|prompt_text)\b")
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in SRC.rglob("*.py")
        if banned.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], offenders


# --------------------------------------------------------------------------- I12


def test_i12_a_number_absent_from_the_bundle_is_not_grounded():
    """I12 — no model ever produces a metric.

    The analyst writes prose *about* numbers it is handed, and may not quote a figure absent from
    its input bundle. Checked, not merely requested (`docs/02` §6.1).
    """
    bundle = AnalysisBundle(
        version_code="01000", fairwork_score=1, twins_n=20,
        baselines={"fairness": 3.41}, shifts={"fairness": 0.62}, index_value=0.18,
        sham_floor=0.05,
    )
    allowed = bundle.numeric_tokens()

    assert grounded("Fairness moved 0.62 against a baseline of 3.41.", allowed) == []
    assert grounded("Fairness moved +0.6 on 20 drivers.", allowed) == []
    assert grounded("Fairness rose by 0.71.", allowed) == ["0.71"]
    assert grounded("That is a 19% improvement.", allowed) == ["19"]


def test_i12_the_offending_sentence_is_identified_for_the_targeted_retry():
    """I12 — an unmatched token triggers one retry quoting the offending sentence."""
    bundle = AnalysisBundle(
        version_code="01000", fairwork_score=1, twins_n=20, shifts={"fairness": 0.62}
    )
    allowed = bundle.numeric_tokens()
    prose = "Fairness moved 0.62. Clarity rose 0.93. The floor was not exceeded."
    assert offending_sentences(prose, allowed) == ["Clarity rose 0.93."]


def test_i12_numeric_tokens_are_generated_from_the_bundle():
    """I12 — the allowed set is generated, never hand-maintained, and includes rounded forms."""
    bundle = AnalysisBundle(version_code="21122", fairwork_score=8, shifts={"leaving": -0.59})
    allowed = bundle.numeric_tokens()
    for token in ("-0.59", "0.59", "0.6", "8", "21122"):
        assert token in allowed, token


def test_i12_no_agent_may_return_a_metric_shape():
    """I12 — metrics are computed in Python. No agent's output schema carries one."""
    for cfg in default_agent_configs().values():
        assert cfg.output_schema not in ("AnalysisBundle",), (
            f"{cfg.agent_id} would return the bundle of computed numbers"
        )


# --------------------------------------------------------------------------- I13


def test_i13_provider_schemas_are_never_trusted():
    """I13 — every model output is validated in Python against the item register.

    `NativeOutput` is forbidden, in three independent places: the model refuses to construct it,
    `validate_config` raises, and the DDL constraint `agent_no_native_output` rejects the row.
    """
    with pytest.raises(ValueError, match="native output is unsupported"):
        _cfg(output_mode="native")
    smuggled = _cfg().model_copy(update={"output_mode": "native"})
    with pytest.raises(ConfigError):
        build_agent(smuggled)
    for cfg in default_agent_configs().values():
        assert cfg.output_mode in ("tool", "prompted"), cfg.agent_id


async def test_i13_a_native_output_row_is_refused_by_the_database_too(backend):
    """I13 in DDL, so a caller cannot forget it."""
    with pytest.raises(DbError, match="agent_no_native_output"):
        await backend.insert("agent_configs", [{
            "agent_id": "x", "name": "X", "role": "r", "model": {}, "system_prompt": "",
            "input_schema": "A", "output_schema": "B", "output_mode": "native",
        }])


def test_i13_per_item_ranges_come_from_the_register_not_a_constant():
    """I13 — each answer is checked against *its own* scale range.

    The prototype's prompt said "1 to 7" for every item and three of the nine constructs are
    5-point. A `6` on a 5-point item is a hard error, never a value to clamp.
    """
    items, points = _battery()
    assert points["PAC1"] == 5 and points["SAT1"] == 7
    vector = dict.fromkeys(items, 2)
    assert validate_answers(vector, items, points) == []
    assert [d.kind for d in validate_answers({**vector, "PAC1": 6}, items, points)] \
        == ["out_of_range"]


@pytest.mark.parametrize(
    "forbidden_repair,vector_change,expected_kind",
    [
        ("pad a missing item", "drop", "missing"),
        ("clamp a 6 on a 5-point item", "over", "out_of_range"),
        ("round a non-integral value", "half", "not_an_integer"),
    ],
)
def test_i13_a_malformed_answer_is_never_coerced(forbidden_repair, vector_change, expected_kind):
    """I13 — never coerced, padded, truncated or rounded into validity.

    Each of these converts a detectable failure into an undetectable fabrication, which is the
    single easiest way to destroy the study without noticing.
    """
    items, points = _battery()
    vector: dict[str, object] = dict.fromkeys(items, 2)
    if vector_change == "drop":
        vector.pop("PAC4")
    elif vector_change == "over":
        vector["PAC1"] = 6
    else:
        vector["SAT1"] = 5.5

    report = normalise_answers(vector, known_items={i.upper(): i for i in items})
    defects = validate_answers(report.value["answers"], items, points)
    assert [d.kind for d in defects] == [expected_kind], forbidden_repair
    # And the value itself was left exactly as it arrived.
    if vector_change == "over":
        assert report.value["answers"]["PAC1"] == 6
    elif vector_change == "half":
        assert report.value["answers"]["SAT1"] == 5.5


async def test_i13_a_unit_that_cannot_be_repaired_is_recorded_failed():
    """I13 — retried, then failed. A twin that cannot produce 37 valid integers fails that cell."""
    items, points = _battery()

    async def ask(_instruction):
        return {i: 2 for i in items if i != "PAC4"}

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False and outcome.output is None


def test_i13_the_repair_is_targeted_and_keeps_valid_answers():
    """I13 with `docs/02` §5.4 — a repair must not re-roll answers that were already valid."""
    items, _ = _battery()
    defects = [Defect("PAC4", "missing", points=5)]
    text = repair_instruction(defects)
    assert {i for i in items if f"`{i}`" in text} == {"PAC4"}
    first = {i: 3 for i in items if i != "PAC4"}
    merged = merge_valid(first, {"PAC4": 1}, defects)
    assert merged["PAC4"] == 1 and all(merged[i] == 3 for i in first)


# --------------------------------------------------------------------------- I14


def _panel_pool(n: int = 40) -> list[PanelCandidate]:
    cities, services = ["Mumbai", "Delhi"], ["cab", "bike"]
    return [
        PanelCandidate(twin_id=f"T{i:03d}", source="real", city=cities[i % 2],
                       service=services[(i // 2) % 2], quality_passed=True)
        for i in range(n)
    ]


def test_i14_the_panel_is_drawn_once_and_is_reproducible_from_the_seed():
    """I14 — the twins that enter a sweep are drawn once and are identical in every cell.

    Reproducible from `(panel_seed, eligible set, panel_size)` alone, so the session that resumes a
    sweep rebuilds exactly the panel the session that started it drew.
    """
    pool = _panel_pool()
    first = draw_panel(pool, panel_size=20, panel_seed=42)
    second = draw_panel(list(reversed(pool)), panel_size=20, panel_seed=42)
    assert panel_ids(first) == panel_ids(second)
    assert len(first) == 20


def test_i14_a_cell_answered_by_different_twins_cannot_be_differenced():
    """I14 — a cell answered by a different set of twins is a different experiment.

    `extra = shift(A∪B) − (shift(A) + shift(B))` is arithmetic on incomparable numbers when the
    legs carry between-person variance instead of the effect of combining protections.
    """
    pool = _panel_pool()
    with pytest.raises(PanelMismatch, match="I14"):
        require_same_panel(
            ("session A", draw_panel(pool, panel_size=20, panel_seed=1)),
            ("session B", draw_panel(pool, panel_size=20, panel_seed=2)),
        )


def test_i14_a_failed_or_manual_twin_never_enters_a_panel():
    """I14 — only quality-passed twins, and never a sandbox object.

    A manual twin has no real survey row, so no holdout and no quality score; a twin that failed
    the gate is dropped from the panel and from all cells, and is never tuned into passing.
    """
    pool = _panel_pool(20) + [
        PanelCandidate(twin_id="FAILED", source="real", city="Mumbai", service="cab",
                       quality_passed=False),
        PanelCandidate(twin_id="MANUAL", source="manual", city="Mumbai", service="cab",
                       quality_passed=True),
    ]
    drawn = panel_ids(draw_panel(pool, panel_size=20, panel_seed=42))
    assert "FAILED" not in drawn and "MANUAL" not in drawn


def test_i14_a_panel_of_zero_is_refused():
    """I14 with I15 — a panel of zero would make every run `twins_n = 0`, never a result."""
    with pytest.raises(InsufficientEligibleTwins):
        draw_panel([], panel_size=20, panel_seed=42)


# --------------------------------------------------------------------------- I15


async def test_i15_a_run_with_no_twins_is_a_failure_not_a_result(backend):
    """I15 — `twins_n = 0` marks the run `failed`, never `completed` with an index of 0.000."""
    with pytest.raises(DbError, match="runs_completed_has_twins"):
        await backend.insert("runs", [{
            "run_id": "r", "session_id": "s", "version_code": "01000",
            "status": "completed", "twins_n": 0,
        }])


async def test_i15_a_validity_test_on_zero_twins_is_inconclusive(backend):
    """I15 — a test that ran on zero twins reports `INCONCLUSIVE`, never `PASS`."""
    row = {
        "test_id": "placebo", "twins_n": 0, "mode": "live", "provider": "ollama", "model": "m",
        "statistics": {}, "verdict": "PASS", "headline": "h", "detail": "d",
        "config_version": 1,
    }
    with pytest.raises(DbError, match="validity_zero_n"):
        await backend.insert("validity_results", [row])
    assert await backend.insert("validity_results", [{**row, "verdict": "INCONCLUSIVE"}])


# --------------------------------------------------------------------------- I16


def test_i16_nothing_durable_is_written_to_the_filesystem():
    """I16 — the disk is ephemeral; evidence goes to Postgres or Supabase Storage first.

    Scans for a write to a path under `data/`. The reference builder is exempt: it is an offline
    one-shot that produces the frozen artifact and is never called by the running application.
    """
    exempt = {"src/twinlab/ingest/build_reference.py"}
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in exempt:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("write_text", "write_bytes", "mkdir"):
                    offenders.append(f"{rel}::{node.func.attr}")
                if node.func.attr == "open" and any(
                    isinstance(a, ast.Constant) and isinstance(a.value, str) and "w" in a.value
                    for a in node.args
                ):
                    offenders.append(f"{rel}::open(w)")
    assert offenders == [], offenders


# --------------------------------------------------------------------------- bookkeeping


def test_every_invariant_is_either_tested_or_declared_deferred():
    """`ARCHITECTURE.md` §2: one executable test per invariant, each naming it in its docstring.

    A milestone that adds an invariant's code without its test cannot quietly skip it: either a
    test in this file names the invariant, or :data:`DEFERRED` says which milestone owns it.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    tested: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            for match in re.findall(r"\bI(1[0-7]|[1-9])\b", doc):
                tested.add(f"I{match}")

    missing = [i for i in ALL_INVARIANTS if i not in tested and i not in DEFERRED]
    assert missing == [], f"no test and not declared deferred: {missing}"

    both = sorted(set(DEFERRED) & tested)
    assert both == [], f"declared deferred but actually tested — remove from DEFERRED: {both}"
