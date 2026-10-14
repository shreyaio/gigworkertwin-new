"""The twin agent. `docs/02` §4.2, `docs/03` §8. Implements I8, serves I7, I10, I11 and I13.

**Persona and round prompt are two separate documents** (I8). The persona says who this person is;
the round prompt asks what they would now say. If the whys travelled with the stimulus, every twin
would restate its own justifications under every counterfactual and would look immovable no matter
what it was shown — which is the signal, destroyed.

What the round prompt carries, and nothing else: the persona passage, the five scenario
paragraphs in randomised order, the twin's own baseline **numbers**, and the 37-item battery with
each item's
own range. No why-text, no open-ended answers, no version code, no dial digits, no holdout items.

**Nothing here is stored.** The prompt is rebuilt from the stored seed, persona hash, lever order,
wording and style version (I11), which is why :func:`rebuild_round_prompt` exists and why the order
is drawn from a seeded `random.Random` rather than the global one.
"""

from __future__ import annotations

import hashlib
import json
import random

from twinlab.agents.contract import ContractOutcome, run_answer_ladder
from twinlab.agents.registry import ModelClient, resolve_prompt
from twinlab.models.agent import AgentConfig
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.twin import (
    AnswerVector,
    BatteryItem,
    H3RoundPrompt,
    RoundPrompt,
    TwinAnswerSet,
)

#: The four labelled fences, in the order `docs/02` §3.3 fixes. **Order is part of the contract**:
#: a reordered prompt is a different stimulus.
BLOCK_ORDER: tuple[str, ...] = ("PERSONA", "SCENARIO", "BASELINE", "BATTERY")

#: Blocks omitted when the gate shows no baseline, so the fence is absent rather than empty. An
#: empty `<<<BASELINE>>>` would tell the twin a baseline exists and was withheld.
_OPTIONAL_BLOCKS: frozenset[str] = frozenset({"BASELINE"})


class RoundPromptError(ValueError):
    """A round prompt that must not reach a twin."""


def lever_order_for(seed: int) -> list[int]:
    """The randomised lever order for one round, reproducibly. `docs/03` §8.

    Positions 0-4 into `LEVER_BY_POSITION`, shuffled by a **local** `random.Random(seed)`. Using the
    global RNG would make the order depend on whatever else ran first in the process, and the order
    is persisted and expected to reconstruct (I11).
    """
    order = list(range(len(LEVER_BY_POSITION)))
    random.Random(seed).shuffle(order)
    return order


def build_round_prompt(
    *,
    persona_hash: str,
    paragraphs: dict[str, str],
    baseline: dict[str, int],
    battery: dict[str, BatteryItem],
    seed: int,
    wording: str = "A",
    show_baseline: bool = True,
) -> RoundPrompt:
    """Assemble one round. The scenario is ordered by ``seed``, never by lever position.

    ``paragraphs`` is keyed by lever; the scenario list is the same five strings in the drawn order.
    ``show_baseline=False`` yields an empty ``baseline``, which is what the quality gate uses: the
    human had no baseline either (`docs/08` §2.1).
    """
    if set(paragraphs) != set(LEVER_BY_POSITION):
        raise RoundPromptError(
            f"expected all five levers, got {sorted(paragraphs)} — a round with a missing lever is "
            "not a cell"
        )
    order = lever_order_for(seed)
    return RoundPrompt(
        persona_hash=persona_hash,
        scenario=[paragraphs[LEVER_BY_POSITION[i]] for i in order],
        lever_order=order,
        baseline=dict(baseline) if show_baseline else {},
        battery=dict(battery),
        wording=wording,
        seed=seed,
    )


def build_user_prompt(round_prompt: RoundPrompt, persona_text: str) -> str:
    """The four labelled fences. `docs/02` §3.3.

    ``persona_text`` is passed in rather than rebuilt here: `agents/` may not reach the database or
    the persona builder's inputs, and the caller already holds the passage whose hash is on the
    round.

    The battery renders each item with **its own range**, which is `docs/02` §4.2 rule 6 — stated in
    the prompt *and* enforced in Python (I13), because the prototype's prompt said "1 to 7" for
    every item and its 5-point blocks were silently wrong.
    """
    blocks: dict[str, str] = {
        "PERSONA": persona_text,
        "SCENARIO": "\n\n".join(round_prompt.scenario),
        "BASELINE": "\n".join(
            f"{item_id} = {value}" for item_id, value in sorted(round_prompt.baseline.items())
        ),
        "BATTERY": "\n".join(
            _battery_line(item_id, item) for item_id, item in _battery_in_order(round_prompt)
        ),
    }
    parts: list[str] = []
    for name in BLOCK_ORDER:
        body = blocks[name]
        if not body and name in _OPTIONAL_BLOCKS:
            # Absent, not empty: an empty fence announces that a baseline exists and was withheld.
            continue
        if not body:
            raise RoundPromptError(f"round prompt block {name} is empty")
        parts.append(f"<<<{name}>>>\n{body}\n<<<END {name}>>>")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- Part 17, one round

#: The H3 round's three fences, in order. **Order is part of the contract.** There is no
#: `BASELINE`: `docs/08` §2.1 step 2 is explicit that the human had none either, and an empty
#: fence would tell the twin a baseline exists and was withheld.
H3_BLOCK_ORDER: tuple[str, ...] = ("PERSONA", "SCENARIO", "BATTERY")

#: How a version is named to the twin. **Never the version code.** `assert_no_forbidden_content`
#: refuses a round naming a code (I8), and a digit in the prompt is a channel through which "this
#: is the strong version" could reach the answer and become a confound.
H3_VERSION_LABEL = "Version {position}"


def build_h3_prompt(
    *,
    persona_hash: str,
    paragraphs_by_version: dict[int, dict[str, str]],
    items_by_version: dict[int, dict[str, BatteryItem]],
    seed: int,
    wording: str = "A",
) -> H3RoundPrompt:
    """Assemble the whole of Part 17 as **one** round. M19 WP-3.

    ``paragraphs_by_version`` and ``items_by_version`` are keyed by ``version_shown`` (1..6) — the
    order the human respondent saw, which is the order the blocks appear in. Each version draws
    its **own** lever order from ``seed`` combined with its position, so paragraph position cannot
    become a confound within a version, and the six orders are not identical to each other (which
    would let a twin learn one position's meaning and carry it across).

    Deterministic: the same ``(seed, codes, twin)`` rebuilds the same six orders, which is what
    makes the round reconstructible (I11).
    """
    if not paragraphs_by_version:
        raise RoundPromptError(
            "the H3 round was given no stimuli. A gate scored on nothing is not a gate (I15)."
        )
    if set(paragraphs_by_version) != set(items_by_version):
        raise RoundPromptError(
            f"H3 stimuli cover versions {sorted(paragraphs_by_version)} but the items cover "
            f"{sorted(items_by_version)}. A version with no items, or an item with no version, is "
            "a data defect and is not skipped."
        )

    scenario: dict[int, list[str]] = {}
    orders: dict[int, list[int]] = {}
    for position in sorted(paragraphs_by_version):
        paragraphs = paragraphs_by_version[position]
        if set(paragraphs) != set(LEVER_BY_POSITION):
            raise RoundPromptError(
                f"version {position} has levers {sorted(paragraphs)}, not all five — a round "
                "with a missing lever is not a cell"
            )
        order = lever_order_for(h3_version_seed(seed, position))
        orders[position] = order
        scenario[position] = [paragraphs[LEVER_BY_POSITION[i]] for i in order]

    return H3RoundPrompt(
        persona_hash=persona_hash,
        scenario=scenario,
        lever_order=orders,
        battery={p: dict(items_by_version[p]) for p in sorted(items_by_version)},
        wording=wording,
        seed=seed,
    )


def h3_version_seed(seed: int, position: int) -> int:
    """The lever-order seed for one version block of an H3 round.

    Derived from the round seed and the version's position rather than drawn, so all six orders
    rebuild from the one stored number (I11) while still differing from each other.
    """
    digest = hashlib.sha256(f"{seed}|h3|{position}".encode()).hexdigest()
    return int(digest[:8], 16)


def build_h3_user_prompt(round_prompt: H3RoundPrompt, persona_text: str) -> str:
    """The three labelled fences of an H3 round. `docs/02` §3.3.

    The six scenario blocks are labelled by position, never by code (:data:`H3_VERSION_LABEL`), and
    the battery is grouped under the same labels so a twin can see which statements belong to which
    version. Each item still renders with **its own range** (`docs/02` §4.2 rule 6).
    """
    scenario_parts: list[str] = []
    for position in sorted(round_prompt.scenario):
        label = H3_VERSION_LABEL.format(position=position)
        body = "\n\n".join(round_prompt.scenario[position])
        if not body.strip():
            raise RoundPromptError(f"H3 scenario block for version {position} is empty")
        scenario_parts.append(f"{label}\n{body}")

    battery_parts: list[str] = []
    for position in sorted(round_prompt.battery):
        label = H3_VERSION_LABEL.format(position=position)
        lines = [
            _battery_line(item_id, item)
            for item_id, item in round_prompt.battery[position].items()
        ]
        if not lines:
            raise RoundPromptError(f"H3 battery block for version {position} is empty")
        battery_parts.append(f"{label}\n" + "\n".join(lines))

    blocks = {
        "PERSONA": persona_text,
        "SCENARIO": "\n\n".join(scenario_parts),
        "BATTERY": "\n\n".join(battery_parts),
    }
    parts: list[str] = []
    for name in H3_BLOCK_ORDER:
        body = blocks[name]
        if not body:
            raise RoundPromptError(f"H3 round prompt block {name} is empty")
        parts.append(f"<<<{name}>>>\n{body}\n<<<END {name}>>>")
    return "\n\n".join(parts)


def rebuild_h3_prompt(
    *,
    persona_hash: str,
    paragraphs_by_version: dict[int, dict[str, str]],
    items_by_version: dict[int, dict[str, BatteryItem]],
    seed: int,
    lever_order: dict[int, list[int]],
    wording: str = "A",
) -> H3RoundPrompt:
    """Reconstruct a stored H3 round. I11, `docs/09` §6.

    The stored orders are **checked against** what the seed regenerates, not merely trusted: if
    they disagree the round is not reconstructible, which means the orders drawn were not the
    orders shown and every verdict built on them is unattributable.
    """
    rebuilt = build_h3_prompt(
        persona_hash=persona_hash,
        paragraphs_by_version=paragraphs_by_version,
        items_by_version=items_by_version,
        seed=seed,
        wording=wording,
    )
    stored = {int(k): list(v) for k, v in lever_order.items()}
    if rebuilt.lever_order != stored:
        raise RoundPromptError(
            f"stored H3 lever_order {stored} != {rebuilt.lever_order} regenerated from seed "
            f"{seed}. The round is not reconstructible (I11) and the verdict built on it cannot "
            "be attributed to a known stimulus."
        )
    return rebuilt


def _battery_line(item_id: str, item: BatteryItem) -> str:
    """One `<<<BATTERY>>>` line: the stem, the range, and **what each end of the range means**.

    `docs/02` §4.2 rule 6 — the item's own range travels with it — is satisfied by the range *and*
    by the anchors, because a range alone does not say which direction it runs in. The human saw a
    labelled radio row; this is the nearest text equivalent.

    Only the two ends and the midpoint are named, not all seven labels. Naming every point would
    make an 18-item H3 round a wall of repeated scale text, and the ends plus the middle are what
    fix direction and calibration. The midpoint is omitted on an even-pointed scale, where there
    is none to name — never faked by picking a neighbour.
    """
    low, high = item.anchors[0], item.anchors[-1]
    if item.points % 2 == 1:
        middle = item.anchors[item.points // 2]
        scale = f"1 = {low}, {item.points // 2 + 1} = {middle}, {item.points} = {high}"
    else:
        scale = f"1 = {low}, {item.points} = {high}"
    return f"{item_id}: {item.stem} (answer 1 to {item.points}; {scale})"


def _battery_in_order(round_prompt: RoundPrompt) -> list[tuple[str, BatteryItem]]:
    """The battery in its register order, which `dict` preserves from the caller."""
    return list(round_prompt.battery.items())


def round_hash(round_prompt: RoundPrompt, persona_text: str) -> str:
    """sha256 over the exact text a twin was given. `docs/09` §6, I11.

    Hashing the assembled prompt rather than its parts is the point: it is what proves a rebuilt
    round is byte-identical to the one that produced a stored answer.
    """
    return hashlib.sha256(build_user_prompt(round_prompt, persona_text).encode("utf-8")).hexdigest()


def rebuild_round_prompt(
    *,
    persona_hash: str,
    paragraphs: dict[str, str],
    baseline: dict[str, int],
    battery: dict[str, BatteryItem],
    seed: int,
    lever_order: list[int],
    wording: str = "A",
    show_baseline: bool = True,
) -> RoundPrompt:
    """Reconstruct a stored round from `twin_answers`. I11, `docs/09` §6.

    The stored ``lever_order`` is **checked against** the order the seed regenerates rather than
    merely trusted. If they disagree the round is not reconstructible and that is a hard failure: it
    means the drawn order was not the order shown, and every result built on it is unattributable.
    """
    rebuilt = build_round_prompt(
        persona_hash=persona_hash,
        paragraphs=paragraphs,
        baseline=baseline,
        battery=battery,
        seed=seed,
        wording=wording,
        show_baseline=show_baseline,
    )
    if rebuilt.lever_order != list(lever_order):
        raise RoundPromptError(
            f"stored lever_order {list(lever_order)} != {rebuilt.lever_order} regenerated from "
            f"seed {seed}. The round is not reconstructible (I11) and the result built on it "
            "cannot be attributed to a known stimulus."
        )
    return rebuilt


async def run_twin(
    cfg: AgentConfig,
    round_prompt: RoundPrompt,
    persona_text: str,
    client: ModelClient,
    *,
    expected: list[str],
    points_for: dict[str, int],
) -> ContractOutcome:
    """One twin round → a validated 37-item vector, or an honest failure. I13.

    Goes through :func:`run_answer_ladder`, so a defective vector gets **one targeted repair**
    naming only the defective items and their own ranges, and then fails. Nothing is coerced: a
    missing item is never padded from the baseline and a `6` on a 5-point item is never clamped to
    `5`. A twin
    that cannot produce a valid vector **fails for that cell only** — it is not dropped from the
    study or the panel: only the quality gate drops twins (`docs/02` §5.4).
    """
    system_prompt, _ = resolve_prompt(cfg)
    user_prompt = build_user_prompt(round_prompt, persona_text)

    async def ask(instruction: str | None):
        prompt = user_prompt if instruction is None else f"{user_prompt}\n\n{instruction}"
        result = await client.run(
            cfg,
            system_prompt=system_prompt,
            user_prompt=prompt,
            # The provider is shown the permissive transport shape, never the
            # validating one: `TwinAnswerSet` would validate inside pydantic-ai and a 36-item
            # reply would raise before the ladder could issue its one targeted repair
            # (`CLAUDE.md` rule 4, `docs/02` §5.4).
            output_type=AnswerVector,
        )
        return result.output

    return await run_answer_ladder(
        ask,
        expected=expected,
        points_for=points_for,
        schema=TwinAnswerSet,
        attempts=cfg.retry.attempts,
    )


def assert_no_forbidden_content(
    prompt: str,
    *,
    holdout_ids: list[str],
    why_texts: list[str],
    version_code: str | None = None,
) -> None:
    """I8's guard, callable from the orchestrator as well as from tests.

    Checks the assembled prompt for the things `docs/03` §8 forbids. It exists as a function rather
    than only as a test because the orchestrator can afford one string scan per round, and the
    failure it prevents — a twin that has seen its own holdout answers — invalidates the twin
    silently and permanently.

    **Two scopes, and conflating them is wrong in both directions.** `docs/03` §8 puts the whys and
    the open answers *in* the `<<<PERSONA>>>` block: the persona is lossless over them by I6,
    and the
    twin is meant to read them as who this person is. What I8 forbids is why-text travelling
    with the
    **stimulus** — the scenario, baseline and battery — because a twin re-reading its own
    justifications alongside each counterfactual restates them and looks immovable. So why-text is
    checked **after** the persona fence, while holdout ids and the version code are checked over the
    whole prompt, where they are forbidden everywhere.
    """
    lowered = prompt.lower()
    for item_id in holdout_ids:
        if item_id.lower() in lowered:
            raise RoundPromptError(f"round prompt names holdout item {item_id} (I8)")
    if version_code and version_code in prompt:
        raise RoundPromptError(f"round prompt names the version code {version_code} (I8)")

    stimulus = prompt.split("<<<END PERSONA>>>", 1)[-1].lower()
    for why in why_texts:
        if why and why.strip() and why.strip().lower() in stimulus:
            raise RoundPromptError(
                "why-text travels with the stimulus (I8). It belongs in the persona block only: "
                "a twin that re-reads its own justifications under every counterfactual looks "
                "immovable no matter what it is shown."
            )


def config_digest(payload: dict) -> str:
    """Stable digest of a frozen config, for `sessions.config` provenance (I11)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
