"""M2 acceptance tests — the output contract and the agent registry. `docs/11` → M2.

The forbidden-repair tests are the point of this file. Each one asserts that a *meaning-changing*
repair does **not** happen, because every repair in `docs/02` §5.3's right-hand column converts a
detectable failure into an undetectable fabrication. A test that only checked the allowed repairs
would pass just as happily against a coercing implementation.
"""

from __future__ import annotations

import re

import pytest

from twinlab.agents.contract import (
    ContractError,
    Defect,
    _Ambiguous,
    merge_valid,
    normalise_answers,
    parse_json,
    repair_instruction,
    run_answer_ladder,
    strip_fences,
    validate_answers,
    validate_output,
)
from twinlab.agents.registry import (
    PROMPT_SECTIONS,
    SCHEMA_REGISTRY,
    ConfigError,
    StubModelClient,
    build_agent,
    check_prompt_skeleton,
    default_agent_configs,
    load_prompt,
    prompt_hash,
    resolve_prompt,
    validate_config,
)
from twinlab.agents.tools import TOOL_REGISTRY, register_tool
from twinlab.ingest.reference_store import reference
from twinlab.models.agent import AgentConfig, ModelRef
from twinlab.models.twin import TwinAnswerSet
from twinlab.models.variant import CoverageVerdict, LeverParagraph


def _cfg(**overrides) -> AgentConfig:
    base = {
        "agent_id": "probe",
        "name": "Probe",
        "role": "a config under test",
        "model": ModelRef(name="gpt-oss:120b"),
        "system_prompt": "inline prompt",
        "input_schema": "CoverageProbe",
        "output_schema": "CoverageVerdict",
    }
    return AgentConfig(**{**base, **overrides})


def _battery() -> tuple[list[str], dict[str, int]]:
    ref = reference()
    items = ref.battery_item_ids
    return items, {i: ref.scale_points(i) for i in items}


def _valid_vector() -> dict[str, int]:
    """A vector that passes: every item at 2, which is inside 1..5 and 1..7 alike."""
    items, _ = _battery()
    return dict.fromkeys(items, 2)


# --------------------------------------------------------------------------- build_agent gates


def test_build_agent_raises_on_native_output():
    """`docs/11` → M2, I13, `ARCHITECTURE.md` §3.2.

    `native` is refused twice over: `AgentConfig` will not construct it, and `validate_config`
    raises if one arrives some other way — from a database row, say, predating the DDL constraint.
    """
    with pytest.raises(ValueError, match="native output is unsupported"):
        _cfg(output_mode="native")

    smuggled = _cfg().model_copy(update={"output_mode": "native"})
    with pytest.raises(ConfigError, match="native output is unsupported"):
        validate_config(smuggled)
    with pytest.raises(ConfigError, match="native output is unsupported"):
        build_agent(smuggled)


def test_build_agent_raises_on_an_unknown_tool_name():
    """`docs/11` → M2: the allow-list is checked once, here, and rejects an unknown name."""
    with pytest.raises(ConfigError, match=r"unknown tools \['fetch_gap'\]"):
        build_agent(_cfg(tools=["fetch_gap"], react=True))


def test_build_agent_raises_on_an_unknown_schema():
    with pytest.raises(ConfigError, match="unknown output_schema"):
        build_agent(_cfg(output_schema="NotAShape"))
    with pytest.raises(ConfigError, match="unknown input_schema"):
        build_agent(_cfg(input_schema="NotAShape"))


def test_the_design_and_twin_agents_cannot_hold_a_tool():
    """I2 and I6, enforced in `build_agent` and not left to discipline.

    The guard is on the agent id, not on the tool name, so registering a harmless tool can never
    make the design agent able to fetch.
    """
    register_tool("a_harmless_tool", lambda: None)
    try:
        for agent_id, invariant in (("design", "I2"), ("twin", "I6")):
            with pytest.raises(ConfigError, match=f"{agent_id} must have tools"):
                build_agent(_cfg(agent_id=agent_id, tools=["a_harmless_tool"]))
            with pytest.raises(ConfigError, match=invariant):
                validate_config(_cfg(agent_id=agent_id, tools=["a_harmless_tool"]))
    finally:
        TOOL_REGISTRY.pop("a_harmless_tool", None)


def test_the_design_and_twin_agents_cannot_be_react():
    """`docs/02` §1: a ReAct loop can fetch. That is the whole reason they are `react: false`."""
    for agent_id in ("design", "twin"):
        with pytest.raises(ConfigError, match="must be react: false"):
            validate_config(_cfg(agent_id=agent_id, react=True))


def test_a_valid_config_passes_every_gate():
    """A gate that rejects everything is not a gate either."""
    assert validate_config(_cfg()) is not None
    assert validate_config(_cfg(agent_id="design", tools=[], react=False)) is not None


# --------------------------------------------------------------------------- prompts


def test_all_five_seed_agents_load_and_validate():
    """`config/agents.default.yaml` is the real config from M2, not a placeholder."""
    configs = default_agent_configs()
    assert set(configs) == {"manager", "design", "twin", "checker", "analyst"}
    for cfg in configs.values():
        assert cfg.prompt_hash, cfg.agent_id
        assert cfg.output_mode in ("tool", "prompted")
        assert cfg.output_schema in SCHEMA_REGISTRY


def test_the_specified_temperatures():
    """`docs/02` §7.1. Each has a reason and none is arbitrary."""
    configs = default_agent_configs()
    assert configs["checker"].model.temperature == 0.0, "a gate that varies is not a gate"
    assert configs["manager"].model.temperature == 0.0, "routing must be reproducible"
    assert configs["analyst"].model.temperature == 0.2
    assert configs["design"].model.temperature == 0.3


def test_design_and_twin_are_toolless_and_non_react_in_the_seed_config():
    """I2 and I6 in the shipped configuration, not only in the guard."""
    configs = default_agent_configs()
    for agent_id in ("design", "twin"):
        assert configs[agent_id].tools == []
        assert configs[agent_id].react is False


def test_only_the_manager_holds_tools_and_is_react():
    """`docs/02` §1: the Manager is the only ReAct agent.

    The Analyst is included deliberately: it lost its ReAct loop and its history tools in 2.0,
    because run history is an unbounded surface through which an ungiven number can enter prose.
    """
    configs = default_agent_configs()
    assert configs["manager"].react is True
    assert configs["manager"].tools
    for agent_id in ("design", "twin", "checker", "analyst"):
        assert configs[agent_id].tools == [], agent_id
        assert configs[agent_id].react is False, agent_id


def test_the_twin_retry_is_targeted_and_budgeted_at_one_repair():
    """`docs/02` §5.4: one call plus one targeted repair, then failed for that cell only."""
    twin = default_agent_configs()["twin"]
    assert twin.retry.repair_mode == "targeted"
    assert twin.retry.attempts == 2


def test_every_prompt_file_has_the_six_sections_in_order():
    """`docs/02` §3.2. A reordered prompt is a different stimulus."""
    for cfg in default_agent_configs().values():
        resolved, digest = resolve_prompt(cfg)
        assert len(digest) == 64
        positions = [resolved.index(section) for section in PROMPT_SECTIONS]
        assert positions == sorted(positions), cfg.agent_id


def test_the_skeleton_check_rejects_a_missing_or_reordered_section():
    """A gate that cannot fail is not a gate."""
    good = "\n".join(f"{s}\nbody\n" for s in PROMPT_SECTIONS)
    check_prompt_skeleton(good)

    without_failure_path = "\n".join(f"{s}\nbody\n" for s in PROMPT_SECTIONS[:-1])
    with pytest.raises(ConfigError, match="IF YOU CANNOT"):
        check_prompt_skeleton(without_failure_path)

    swapped = list(PROMPT_SECTIONS)
    swapped[1], swapped[3] = swapped[3], swapped[1]
    with pytest.raises(ConfigError, match="out of order"):
        check_prompt_skeleton("\n".join(f"{s}\nbody\n" for s in swapped))


def test_prompt_hash_is_over_the_resolved_text():
    """I11: the hash describes the text the agent is actually given, not the reference to it."""
    resolved = load_prompt("file:twin_v1.md")
    assert prompt_hash(resolved) == prompt_hash(load_prompt("file:twin_v1.md"))
    assert prompt_hash(resolved) != prompt_hash(resolved + " ")


def test_a_missing_prompt_file_raises():
    with pytest.raises(ConfigError, match="prompt file not found"):
        load_prompt("file:no_such_prompt_v9.md")


def test_the_forbidden_vocabulary_is_absent_from_the_twin_facing_prompts():
    """`docs/02` §3.5.

    The style contract's forbidden terms apply to everything a twin can see — including the prompt
    files themselves. A driver told they are in a study answers like a participant, not a driver.
    """
    import yaml

    from config.settings import CONFIG_DIR

    contract = yaml.safe_load((CONFIG_DIR / "style_contract.yaml").read_text(encoding="utf-8"))
    forbidden = [t.lower() for t in contract["forbidden_terms"]]
    for name in ("design_v1.md", "twin_v1.md"):
        text = load_prompt(f"file:{name}").lower()
        body = text.split("---", 2)[-1]          # skip the provenance front matter
        found = [term for term in forbidden if re.search(rf"\b{re.escape(term)}\b", body)]
        assert found == [], f"{name} contains forbidden terms {found}"


# --------------------------------------------------------------------------- allowed repairs


def test_allowed_strip_markdown_fences_and_surrounding_prose():
    """`docs/02` §5.3, allowed: how the JSON was presented, not what it says."""
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert parse_json('Here you go:\n```\n{"a": 1}\n```\nHope that helps!') == {"a": 1}
    assert parse_json('Sure. {"a": 1} Let me know.') == {"a": 1}


def test_allowed_string_digit_becomes_an_integer():
    report = normalise_answers({"FAIR1": "6"})
    assert report.value["answers"]["FAIR1"] == 6


def test_allowed_exactly_integral_float_becomes_an_integer():
    report = normalise_answers({"FAIR1": 6.0, "FAIR2": "7.0"})
    assert report.value["answers"]["FAIR1"] == 6
    assert report.value["answers"]["FAIR2"] == 7


def test_allowed_whitespace_and_key_case_are_normalised():
    items, _ = _battery()
    known = {i.upper(): i for i in items}
    report = normalise_answers({" fair1 ": " 4 "}, known_items=known)
    assert report.value["answers"]["FAIR1"] == 4


def test_allowed_duplicate_key_whose_values_agree_is_collapsed():
    """The only duplicate that carries no ambiguity."""
    items, _ = _battery()
    known = {i.upper(): i for i in items}
    report = normalise_answers({"FAIR1": 5, "fair1": "5"}, known_items=known)
    assert report.value["answers"]["FAIR1"] == 5
    assert any("duplicate" in r for r in report.repairs)


def test_normalisation_reports_what_it_did():
    """Every repair is inspectable rather than implicit."""
    report = normalise_answers({"FAIR1": "6"})
    assert report.repairs


# --------------------------------------------------------------------------- forbidden repairs


def test_forbidden_a_missing_item_is_never_padded_from_the_baseline():
    """`docs/02` §5.3, forbidden. This is the one that fabricates a whole answer."""
    items, points = _battery()
    baseline = dict.fromkeys(items, 4)
    partial = {i: 2 for i in items if i != "PAC4"}

    report = normalise_answers(partial, known_items={i.upper(): i for i in items})
    answers = report.value["answers"]
    assert "PAC4" not in answers, "a missing item was filled in"
    assert baseline["PAC4"] not in {answers.get("PAC4")}

    defects = validate_answers(answers, items, points)
    assert [d.item_id for d in defects] == ["PAC4"]
    assert defects[0].kind == "missing"


def test_forbidden_a_six_on_a_five_point_item_is_never_clamped():
    """`docs/02` §5.3, forbidden — and `docs/11` → M2's per-item range test.

    `PAC1` is `agree5`. Clamping `6` to `5` would turn a detectable provider failure into a
    plausible-looking answer, which is precisely the silent corruption I13 exists to stop.
    """
    items, points = _battery()
    assert points["PAC1"] == 5, "read from the item register, not a constant"

    vector = {**_valid_vector(), "PAC1": 6}
    report = normalise_answers(vector, known_items={i.upper(): i for i in items})
    assert report.value["answers"]["PAC1"] == 6, "the out-of-range value was altered"

    defects = validate_answers(report.value["answers"], items, points)
    assert [(d.item_id, d.kind) for d in defects] == [("PAC1", "out_of_range")]


def test_forbidden_a_five_point_item_rejects_both_six_and_seven():
    """`docs/11` → M2, reading `points` from the register rather than a constant."""
    items, points = _battery()
    for bad in (6, 7):
        defects = validate_answers({**_valid_vector(), "CLAR1": bad}, items, points)
        assert [(d.item_id, d.kind) for d in defects] == [("CLAR1", "out_of_range")]
    # The same value on a 7-point item is perfectly valid — the range is per item.
    assert points["SAT1"] == 7
    assert validate_answers({**_valid_vector(), "SAT1": 7}, items, points) == []


def test_forbidden_a_non_integral_value_is_never_rounded():
    """`docs/02` §5.3, forbidden: `5.5` → `6`."""
    items, points = _battery()
    for raw in (5.5, "5.5", "4.7"):
        report = normalise_answers({**_valid_vector(), "SAT1": raw},
                                   known_items={i.upper(): i for i in items})
        assert report.value["answers"]["SAT1"] == raw, f"{raw!r} was coerced"
        defects = validate_answers(report.value["answers"], items, points)
        assert [(d.item_id, d.kind) for d in defects] == [("SAT1", "not_an_integer")]


def test_forbidden_an_item_is_never_inferred_from_a_neighbour():
    """`docs/02` §5.3, forbidden. FAIR2 present and FAIR3 absent must stay that way."""
    items, points = _battery()
    vector = {i: 3 for i in items if i != "FAIR3"}
    report = normalise_answers(vector, known_items={i.upper(): i for i in items})
    assert "FAIR3" not in report.value["answers"]
    assert [d.item_id for d in validate_answers(report.value["answers"], items, points)] \
        == ["FAIR3"]


def test_forbidden_disagreeing_duplicates_are_never_resolved_to_the_first():
    """`docs/02` §5.3, forbidden. The ambiguity is preserved and reported."""
    items, points = _battery()
    known = {i.upper(): i for i in items}
    report = normalise_answers({**_valid_vector(), "FAIR1": 2, "fair1": 6}, known_items=known)
    value = report.value["answers"]["FAIR1"]
    assert isinstance(value, _Ambiguous), "a disagreeing duplicate was silently resolved"
    assert value.values == [2, 6]

    defects = validate_answers(report.value["answers"], items, points)
    assert [(d.item_id, d.kind) for d in defects] == [("FAIR1", "ambiguous")]


def test_forbidden_a_boolean_is_not_an_answer():
    """`True` is an `int` in Python. It is not a Likert response."""
    items, points = _battery()
    report = normalise_answers({**_valid_vector(), "SAT1": True},
                               known_items={i.upper(): i for i in items})
    defects = validate_answers(report.value["answers"], items, points)
    assert [(d.item_id, d.kind) for d in defects] == [("SAT1", "not_an_integer")]


def test_forbidden_an_unrecognised_key_is_not_silently_dropped():
    """Dropping it would hide that the model answered something that does not exist."""
    items, points = _battery()
    report = normalise_answers({**_valid_vector(), "FAIR9": 3},
                               known_items={i.upper(): i for i in items})
    assert "FAIR9" in report.value["answers"]
    defects = validate_answers(report.value["answers"], items, points)
    assert [(d.item_id, d.kind) for d in defects] == [("FAIR9", "extra")]


def test_the_schema_itself_refuses_a_coerced_vector():
    """I13 at the model boundary too, reading the register rather than a constant."""
    with pytest.raises(ValueError, match="outside 1..5"):
        TwinAnswerSet(answers={**_valid_vector(), "PAC1": 6})
    with pytest.raises(ValueError, match="missing="):
        TwinAnswerSet(answers={k: v for k, v in _valid_vector().items() if k != "PAC4"})
    with pytest.raises(ValueError, match="extra="):
        TwinAnswerSet(answers={**_valid_vector(), "NOPE1": 3})


# --------------------------------------------------------------------------- targeted repair


def test_the_repair_instruction_names_only_the_defective_items_and_their_own_ranges():
    """`docs/02` §5.4's worked example, exactly.

    Nothing about the valid items is mentioned, so the model has nothing to re-roll.
    """
    defects = [Defect("PAC4", "missing", points=5), Defect("PAC7", "missing", points=5)]
    text = repair_instruction(defects)
    assert "`PAC4`" in text and "`PAC7`" in text
    assert "were missing" in text
    assert "from 1 to 5" in text
    assert "those 2" in text
    # No other battery item is named.
    items, _ = _battery()
    named = {i for i in items if f"`{i}`" in text}
    assert named == {"PAC4", "PAC7"}


def test_the_repair_instruction_groups_items_by_their_own_range():
    """A 5-point and a 7-point item in one repair must not be given one shared range."""
    text = repair_instruction([
        Defect("PAC4", "missing", points=5), Defect("SAT1", "missing", points=7),
    ])
    assert "from 1 to 5" in text and "from 1 to 7" in text


def test_merge_valid_keeps_attempt_ones_answers():
    """`docs/02` §5.4: "Valid items from attempt 1 are kept."

    This is what makes the repair targeted rather than a re-roll — 35 already-valid answers do not
    move, so the repair adds no variance to them.
    """
    items, _ = _battery()
    first = {i: 3 for i in items if i not in ("PAC4", "PAC7")}
    defects = [Defect("PAC4", "missing", points=5), Defect("PAC7", "missing", points=5)]
    merged = merge_valid(first, {"PAC4": 2, "PAC7": 5}, defects)
    assert merged["PAC4"] == 2 and merged["PAC7"] == 5
    assert all(merged[i] == 3 for i in first)


async def test_a_vector_missing_two_items_is_repaired_and_retries_records_one():
    """`docs/11` → M2, end to end: targeted repair, retained answers, `retries == 1`."""
    items, points = _battery()
    asked: list[str | None] = []

    async def ask(instruction: str | None):
        asked.append(instruction)
        if instruction is None:
            return {i: 3 for i in items if i not in ("PAC4", "PAC7")}
        return {"PAC4": 2, "PAC7": 5}

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok
    assert outcome.retries == 1, "twin_answers.retries records the repair count"
    answers = outcome.output.answers
    assert answers["PAC4"] == 2 and answers["PAC7"] == 5
    assert all(answers[i] == 3 for i in items if i not in ("PAC4", "PAC7"))

    # The repair named only the two defective items.
    assert asked[1] is not None
    assert {i for i in items if f"`{i}`" in asked[1]} == {"PAC4", "PAC7"}


async def test_a_clean_first_attempt_records_no_retries():
    items, points = _battery()

    async def ask(_instruction):
        return _valid_vector()

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok and outcome.retries == 0


async def test_after_a_failed_repair_the_unit_is_failed_and_nothing_is_coerced():
    """`docs/11` → M2. The correct outcome, not a recoverable one.

    A twin that cannot produce a valid vector after one targeted repair fails **for that cell
    only** — it is not dropped from the study or the panel.
    """
    items, points = _battery()
    calls = 0

    async def ask(_instruction):
        nonlocal calls
        calls += 1
        return {i: 3 for i in items if i != "PAC4"}      # PAC4 never arrives

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False
    assert outcome.output is None, "a failed unit has no output to store"
    assert calls == 2, "one call plus one repair, then stop"
    assert [d.item_id for d in outcome.defects] == ["PAC4"]
    assert "nothing coerced" in outcome.reason
    with pytest.raises(ContractError):
        outcome.raise_if_failed()


async def test_an_out_of_range_value_that_survives_repair_fails_rather_than_being_clamped():
    items, points = _battery()

    async def ask(_instruction):
        return {**_valid_vector(), "PAC1": 6}

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False
    assert [(d.item_id, d.kind) for d in outcome.defects] == [("PAC1", "out_of_range")]


async def test_unparseable_output_is_retried_then_failed():
    items, points = _battery()

    async def ask(_instruction):
        return "I would rather not answer in JSON."

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False
    assert outcome.defects and outcome.defects[0].kind == "unparseable"


# --------------------------------------------------------------------------- other shapes


def test_validate_output_parses_and_validates_a_non_answer_shape():
    outcome = validate_output('```json\n{"entailed": true, "reason": "same undertaking"}\n```',
                              CoverageVerdict)
    assert outcome.ok and outcome.output.entailed is True


def test_an_unparseable_checker_verdict_is_not_entailed():
    """`docs/02` §5.5: uncertainty fails closed. The default carries the safe answer."""
    assert CoverageVerdict().entailed is False
    outcome = validate_output('{"entailed": "maybe"}', CoverageVerdict)
    assert outcome.ok is False


def test_the_design_agents_refusal_is_a_recorded_outcome():
    """`docs/02` §4.1: `cannot_render` is logged; the cell is never filled with generic prose."""
    outcome = validate_output(
        '{"text": "", "status": "cannot_render", "reason": "2.2 material unavoidable"}',
        LeverParagraph,
    )
    assert outcome.ok
    assert outcome.output.status == "cannot_render"
    assert outcome.output.text == ""


async def test_the_stub_client_counts_calls_per_agent():
    """`docs/11` → Ground rules: test the contract, not the prose. M5 counts design calls."""
    client = StubModelClient(lambda cfg, prompt, out: out())
    cfg = default_agent_configs()["checker"]
    await client.run(cfg, system_prompt="s", user_prompt="u", output_type=CoverageVerdict)
    await client.run(cfg, system_prompt="s", user_prompt="u", output_type=CoverageVerdict)
    assert client.call_count("checker") == 2
    assert client.call_count("design") == 0


# ------------------------------------------------- telemetry across pydantic-ai generations


def test_token_counts_are_read_across_pydantic_ai_generations():
    """`PydanticAIClient` must read token counts on both the 0.0.x and 2.x usage APIs.

    Found by the first live call, 2026-09-29. Both ways of getting this wrong are silent in CI and
    only bite against a real provider:

    * `usage` became a **property** in 2.x, so `result.usage()` raised `TypeError` *after* the model
      call had already been paid for.
    * the fields were renamed, so `getattr(usage, "request_tokens", None)` returns `None` on 2.x
      without complaining — and `docs/10` costs every estimate on these numbers, so a permanently
      `None` count makes the credit budget unmeasurable while looking like it works.
    """
    from twinlab.agents.registry import _token_counts

    class _Usage2x:
        input_tokens, output_tokens = 2300, 400

    class _Usage00x:
        request_tokens, response_tokens = 1100, 250

    class _Result:
        def __init__(self, usage):
            self.usage = usage

    assert _token_counts(_Result(_Usage2x())) == (2300, 400)
    assert _token_counts(_Result(_Usage00x())) == (1100, 250)
    # 0.0.x exposed it as a method; a callable must still resolve.
    assert _token_counts(_Result(lambda: _Usage00x())) == (1100, 250)


def test_an_unrecognised_usage_object_raises_rather_than_reporting_none():
    """A third rename must fail loudly, not silently zero the cost model."""
    from twinlab.agents.registry import _token_counts

    class _Result:
        usage = object()

    with pytest.raises(ConfigError, match="usage API"):
        _token_counts(_Result())


def test_max_tokens_reaches_the_model_settings():
    """`max_tokens` was declared on all five agents and silently never passed.

    Moot for a 45-75 word paragraph, but the twin's 1024 is a real ceiling on a 37-item vector, and
    a truncated vector fails the contract rather than being coerced (I13) — so it would have
    surfaced as unexplained twin failures, not as a missing setting.
    """
    cfg = default_agent_configs()["twin"]
    assert cfg.model.max_tokens == 1024

    captured = {}

    class _Agent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    import twinlab.agents.registry as reg

    real_resolve = reg.resolve_model
    reg.resolve_model = lambda model: "stub-model"
    try:
        import sys
        import types

        fake = types.ModuleType("pydantic_ai")
        fake.Agent = _Agent
        fake.ToolOutput = lambda schema: schema
        fake.PromptedOutput = lambda schema: schema
        saved = sys.modules.get("pydantic_ai")
        sys.modules["pydantic_ai"] = fake
        try:
            reg.build_agent(cfg)
        finally:
            if saved is None:
                del sys.modules["pydantic_ai"]
            else:
                sys.modules["pydantic_ai"] = saved
    finally:
        reg.resolve_model = real_resolve

    assert captured["model_settings"]["max_tokens"] == 1024
    assert captured["model_settings"]["temperature"] == cfg.model.temperature


# ---------------------------------------------------------------- the transport ladder


@pytest.fixture(autouse=True)
def _no_real_waiting(monkeypatch):
    """The ladder's shape is under test, not the wall clock. Keeps CI honest about time."""
    monkeypatch.setattr("twinlab.agents.registry.TRANSPORT_BASE_DELAY", 0.0)


class _Boom(Exception):
    """A provider failure carrying a status code, the way an HTTP client exposes one."""

    def __init__(self, status_code: int, message: str = "") -> None:
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code


@pytest.mark.parametrize(
    "exc, transient",
    [
        (_Boom(429), True),
        (_Boom(503), True),
        (_Boom(500), True),
        (_Boom(400), False),
        (_Boom(401), False),
        (_Boom(422), False),
        (TimeoutError("read timed out"), True),
        (ConnectionError("connection reset by peer"), True),
        (RuntimeError("Rate limit exceeded, please retry"), True),
        (RuntimeError("model returned a value outside 1..5"), False),
        (ValueError("answers did not validate"), False),
    ],
)
def test_only_provider_pressure_is_worth_repeating(exc, transient):
    """`docs/DECISIONS.md` 2026-09-22 — classified on the exception, not on an SDK type.

    A schema failure must NOT be transient: a wrong prompt fails identically every time, and
    retrying it three times spends the scarcest resource in the system for nothing.
    """
    from twinlab.agents.registry import is_transient

    assert is_transient(exc) is transient


async def test_a_rate_limited_twin_call_is_retried_rather_than_losing_the_twin():
    """Without this ladder a 429 costs a twin, and the cell still completes (I14, I15).

    `ask_panel` catches whatever a twin call raises and moves on, and `execute_run` fails a cell
    only when *no* twin answered. So one transient refusal used to shrink that cell's panel
    permanently while the run was recorded as a result.
    """
    from twinlab.agents import registry

    calls: list[int] = []

    class _Agent:
        async def run(self, _prompt):
            calls.append(1)
            if len(calls) < 3:
                raise _Boom(429, "Too Many Requests")
            return "ok"

    cfg = registry.default_agent_configs()["twin"]
    client = registry.PydanticAIClient()
    result = await client._run_with_backoff(_Agent(), "prompt", cfg)

    assert result == "ok"
    assert len(calls) == 3, "the ladder did not repeat a transient failure"


async def test_a_schema_failure_is_not_repeated_at_cost():
    """One call, then it raises. The repair ladder owns schema failures, not the transport."""
    from twinlab.agents import registry

    calls: list[int] = []

    class _Agent:
        async def run(self, _prompt):
            calls.append(1)
            raise ValueError("output did not match the schema")

    cfg = registry.default_agent_configs()["twin"]
    with pytest.raises(ValueError, match="schema"):
        await registry.PydanticAIClient()._run_with_backoff(_Agent(), "prompt", cfg)
    assert len(calls) == 1, "a deterministic failure was paid for more than once"


async def test_the_ladder_gives_up_and_raises_rather_than_looping():
    """`TRANSPORT_ATTEMPTS` is a budget, not a wait-forever."""
    from twinlab.agents import registry

    calls: list[int] = []

    class _Agent:
        async def run(self, _prompt):
            calls.append(1)
            raise _Boom(429)

    cfg = registry.default_agent_configs()["twin"]
    with pytest.raises(_Boom):
        await registry.PydanticAIClient()._run_with_backoff(_Agent(), "prompt", cfg)
    assert len(calls) == registry.TRANSPORT_ATTEMPTS


# ------------------------------------------------- the transport shape (M15 §3.1 regressions)
#
# Every test below failed before the transport model existed. They are here because the defect
# they cover was invisible to the whole M6 suite: `StubModelClient`'s handler returns *dicts*,
# while `PydanticAIClient.run().output` is a *model instance*. Nothing in CI ever exercised the
# shape a live provider actually returns, so the live path could not produce a single answer.


def test_the_transport_shape_rejects_nothing_the_ladder_must_judge():
    """`CLAUDE.md` rule 4 — the provider's schema validates nothing, so it must block nothing.

    `AnswerVector` is what the provider is handed. If it rejected a defective vector, pydantic-ai
    would raise before `run_answer_ladder` ran, and the one targeted repair `docs/02` §5.4
    specifies would never be issued. Each value below is a defect the ladder has a `Defect.kind`
    for and must be allowed to name.
    """
    from twinlab.models.twin import AnswerVector

    vector = AnswerVector.model_validate(
        {"answers": {"PAC1": 5.5, "PAC2": 9, "PAC3": None, "PAC4": "x"}, "rationale": 7}
    )
    assert set(vector.answers) == {"PAC1", "PAC2", "PAC3", "PAC4"}, (
        "the transport shape dropped a key it was given"
    )

    # And a short vector — the exact case that used to raise inside pydantic-ai.
    short = AnswerVector.model_validate({"answers": {"PAC1": 3}})
    assert short.answers == {"PAC1": 3}


def test_the_twin_agent_is_never_configured_with_a_validating_schema():
    """`CLAUDE.md` rule 4. The gate a future edit would trip.

    `build_agent` falls back to `SCHEMA_REGISTRY[cfg.output_schema]` when no `output_type` is
    passed, so the shipped twin config is a live call site. Naming `TwinAnswerSet` there puts the
    37-item register check back inside the provider round trip.
    """
    from twinlab.models.twin import AnswerVector

    cfg = default_agent_configs()["twin"]
    assert SCHEMA_REGISTRY[cfg.output_schema] is AnswerVector, (
        f"the twin agent is configured with {cfg.output_schema}, which validates in pydantic-ai "
        "before the repair ladder can see the reply"
    )


async def test_the_ladder_reads_a_model_instance_reply():
    """A valid live reply must not be recorded as unparseable.

    `normalise_answers` branches on `isinstance(payload, dict)`. A model instance took the `else`
    branch and raised `ContractError('expected an object of answers, got ...')`, so **every** live
    reply — including this one, which is perfectly valid — burned an attempt and failed the round.
    """
    from twinlab.models.twin import AnswerVector

    items, points = _battery()

    async def ask(_instruction):
        return AnswerVector(answers=_valid_vector(), rationale="because of the fare change")

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok, f"a valid model instance was rejected: {outcome.reason}"
    assert outcome.retries == 0, "a clean first attempt must not be charged a repair"
    assert outcome.output is not None
    assert outcome.output.answers == _valid_vector()
    assert outcome.output.rationale == "because of the fare change"


async def test_a_model_instance_short_by_one_gets_exactly_one_targeted_repair():
    """`docs/02` §5.4, as a *model instance* rather than a dict. The M15 §3.1 blocker.

    This is the test the handoff asked for first. Before the fix it failed twice over: the short
    reply raised inside pydantic-ai, and the ladder could not have read it anyway.
    """
    from twinlab.models.twin import AnswerVector

    items, points = _battery()
    asked: list[str | None] = []

    async def ask(instruction: str | None):
        asked.append(instruction)
        if instruction is None:
            return AnswerVector(answers={i: 3 for i in items if i != "PAC4"})
        return AnswerVector(answers={"PAC4": 2})

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok and outcome.retries == 1
    assert len(asked) == 2, "one call plus one repair"
    assert asked[1] is not None and "`PAC4`" in asked[1]
    assert {i for i in items if f"`{i}`" in asked[1]} == {"PAC4"}, (
        "the repair re-asked for an item that was already valid"
    )
    # Nothing was padded: the repaired item carries the repair's value, the other 36 carry
    # attempt 1's, and attempt 1's values did not move.
    assert outcome.output.answers["PAC4"] == 2
    assert all(outcome.output.answers[i] == 3 for i in items if i != "PAC4")


async def test_a_model_instance_that_stays_short_fails_and_pads_nothing():
    """The correct outcome for a twin that cannot answer: `ok=False`, not a padded vector.

    Fails for that cell only. The twin stays on the panel — only the quality gate drops twins
    (`docs/02` §5.4).
    """
    from twinlab.models.twin import AnswerVector

    items, points = _battery()
    calls = 0

    async def ask(_instruction):
        nonlocal calls
        calls += 1
        return AnswerVector(answers={i: 3 for i in items if i != "PAC4"})

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False
    assert outcome.output is None, "a failed unit has no vector to store"
    assert calls == 2, "one call plus one repair, then stop"
    assert [d.item_id for d in outcome.defects] == ["PAC4"]
    assert outcome.defects[0].kind == "missing"
    assert not any("unparseable" in str(d) for d in outcome.defects), (
        "a readable model instance was reported as unparseable"
    )


async def test_an_out_of_range_model_instance_is_named_not_clamped():
    """A `6` on a 5-point item reaches the ladder and is re-asked, never clamped.

    The transport shape must let it through for this to be possible at all.
    """
    from twinlab.models.twin import AnswerVector

    items, points = _battery()
    five_point = next(i for i in items if points[i] == 5)
    asked: list[str | None] = []

    async def ask(instruction: str | None):
        asked.append(instruction)
        return AnswerVector(answers={**_valid_vector(), five_point: 6})

    outcome = await run_answer_ladder(
        ask, expected=items, points_for=points, schema=TwinAnswerSet
    )
    assert outcome.ok is False, "a 6 on a 5-point item was accepted"
    assert [d.kind for d in outcome.defects] == ["out_of_range"]
    assert asked[1] is not None and "1 to 5" in asked[1]
