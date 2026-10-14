"""The analyst bundle, the grounding ladder and the deterministic fallback. `docs/02` §4.4 and §6.

**Implements I12: no model ever produces a metric.** The analyst receives one deterministically
assembled bundle of numbers Python computed, writes prose *about* them, and that prose is checked
against the bundle before it is stored. A prompt instruction is necessary but not sufficient — a
model told "never invent a number" still occasionally does, so it is checked.

The ladder, from `docs/02` §6::

    prose → grounded()? → store
                       ↘ one targeted retry quoting the offending sentence
                                                   ↘ deterministic template, prefixed

**A cell is never left without a reading, and never given an ungrounded one.** The fallback rate is
itself a reportable diagnostic: if it climbs, the prompt or the model is at fault, and the data says
so rather than the prose quietly drifting.
"""

from __future__ import annotations

from twinlab.agents.contract import grounded, offending_sentences, validate_output
from twinlab.agents.registry import ModelClient, resolve_prompt
from twinlab.models.agent import AgentConfig
from twinlab.models.analysis import (
    AnalysisBundle,
    AnalysisResult,
    CellShifts,
    Interaction,
)

#: The prefix `docs/02` §6.2 requires on a fallback reading, so the reader always knows.
FALLBACK_PREFIX = (
    "Generated summary — the analyst agent did not produce a grounded reading for this cell."
)

#: The bundle's blocks, in the order `docs/02` §4.4 lists them. The analyst sees the same bundle in
#: the same order as the Results side panel, so the researcher can read input and output together.
#:
#: The labels are the ones `agents/prompts/analyst_v1.md` names in its INPUTS. The prompt is the
#: researcher's spec, and a label it names that the bundle does not carry is a block the model is
#: told to read and cannot find.
BLOCK_ORDER: tuple[str, ...] = (
    "CODE", "TOLD", "TEXT", "NUMBERS", "COMBINATIONS", "FLOOR",
)


def build_bundle(
    *,
    shifts: CellShifts,
    fairwork_score: int,
    commitment_summary: dict[str, list[str]],
    scenario_text: list[str],
    interactions: list[Interaction] | None = None,
    sham_floor: float | None = None,
) -> AnalysisBundle:
    """Assemble the bundle. Deterministic, and the analyst's **only** input. `docs/02` §4.4.

    Only fully computable interactions are included: the bundle may carry no number that was not
    computed, so a missing leg is simply not offered (I17 — the UI surfaces it separately with the
    code to run).
    """
    return AnalysisBundle(
        version_code=shifts.version_code,
        fairwork_score=fairwork_score,
        commitment_summary=commitment_summary,
        scenario_text=list(scenario_text),
        baselines=dict(shifts.baselines),
        shifts=dict(shifts.shifts),
        index_value=shifts.index_value,
        twins_n=shifts.twins_n,
        interactions=[i.model_dump() for i in (interactions or [])],
        sham_floor=sham_floor,
    )


def build_user_prompt(bundle: AnalysisBundle) -> str:
    """The bundle as labelled fences, in :data:`BLOCK_ORDER`. `docs/02` §3.3."""
    numbers = [f"twins_n = {bundle.twins_n}"]
    for metric in sorted(bundle.shifts):
        base = bundle.baselines.get(metric)
        numbers.append(
            f"{metric}: baseline {base}, shift {bundle.shifts[metric]:+}"
            if base is not None
            else f"{metric}: shift {bundle.shifts[metric]:+}"
        )
    if bundle.index_value is not None:
        numbers.append(f"index = {bundle.index_value}")

    told = [
        f"{lever}: " + "; ".join(items)
        for lever, items in sorted(bundle.commitment_summary.items())
    ]
    interactions = [
        f"{i['a']} x {i['b']} on {i['metric']}: alone {i['alone_a']:+} and {i['alone_b']:+}, "
        f"together {i['together']:+}, extra {i['extra']:+} ({i['verdict']})"
        for i in bundle.interactions
    ]

    blocks = {
        "CODE": f"version_code {bundle.version_code}, score {bundle.fairwork_score} of 10",
        "TOLD": "\n".join(told) or "(nothing changes in this cell)",
        "TEXT": "\n\n".join(bundle.scenario_text),
        "NUMBERS": "\n".join(numbers),
        "COMBINATIONS": "\n".join(interactions) or "(none computable for this cell)",
        "FLOOR": (
            f"sham floor = {bundle.sham_floor}"
            if bundle.sham_floor is not None
            else "the sham floor has not been measured for this session"
        ),
    }
    return "\n\n".join(f"<<<{n}>>>\n{blocks[n]}\n<<<END {n}>>>" for n in BLOCK_ORDER)


def template_reading(bundle: AnalysisBundle) -> str:
    """The deterministic fallback. `docs/02` §6.2. Python only, and therefore always grounded.

    Written from the same bundle, so every number in it is in the bundle by construction — the
    fallback cannot fail the grounding check that produced it.
    """
    lines = [FALLBACK_PREFIX]
    score = bundle.fairwork_score
    lines.append(
        f"Cell {bundle.version_code} scores {score} of 10 and was answered by "
        f"{bundle.twins_n} twins."
    )

    if bundle.shifts:
        moved = sorted(bundle.shifts.items(), key=lambda kv: -abs(kv[1]))
        parts = [f"{metric} {value:+}" for metric, value in moved]
        lines.append("Shifts: " + ", ".join(parts) + ".")
    if bundle.index_value is not None:
        lines.append(f"The index is {bundle.index_value}.")

    floor_note = _floor_note(bundle)
    if floor_note:
        lines.append(floor_note)

    sub = [i for i in bundle.interactions if i.get("verdict") == "sub-additive"]
    if sub:
        pairs = ", ".join(f"{i['a']} with {i['b']}" for i in sub)
        lines.append(
            f"Sub-additive pairs: {pairs}. Together these add less than the sum of each alone, "
            "which suggests they substitute for one another."
        )
    return " ".join(lines)


def _floor_note(bundle: AnalysisBundle) -> str:
    """The interpretability statement. `docs/07` §6 — the analyst is *required* to make it."""
    if bundle.sham_floor is None:
        return (
            "The sham floor has not been measured for this session, so this cell cannot be "
            "judged interpretable."
        )
    if bundle.index_value is None:
        return ""
    if bundle.index_value <= bundle.sham_floor:
        return (
            f"The index does not exceed the sham floor of {bundle.sham_floor}, so this cell is "
            "not interpretable."
        )
    return f"The index exceeds the sham floor of {bundle.sham_floor}."


async def write_analysis(
    cfg: AgentConfig,
    bundle: AnalysisBundle,
    client: ModelClient,
) -> tuple[AnalysisResult, bool]:
    """The ladder. Returns ``(result, used_fallback)``. `docs/02` §6.

    One targeted retry, quoting the **offending sentence** rather than merely saying a digit was
    wrong — the model is told which claim is unsupported. Then the deterministic template, prefixed.

    ``used_fallback`` is returned rather than inferred from the prefix, because the fallback rate is
    a reportable diagnostic and a caller should not have to string-match to record it.
    """
    system_prompt, _ = resolve_prompt(cfg)
    allowed = bundle.numeric_tokens()
    base_prompt = build_user_prompt(bundle)
    instruction: str | None = None
    attempts = max(cfg.retry.attempts, 1)

    for _ in range(attempts):
        prompt = base_prompt if instruction is None else f"{base_prompt}\n\n{instruction}"
        try:
            raw = await client.run(
                cfg, system_prompt=system_prompt, user_prompt=prompt,
                output_type=AnalysisResult,
            )
            output = raw.output
            if not isinstance(output, AnalysisResult):
                outcome = validate_output(output, AnalysisResult)
                if not outcome.ok or outcome.output is None:
                    instruction = _reask_shape(outcome.reason)
                    continue
                assert isinstance(outcome.output, AnalysisResult)
                output = outcome.output
        except Exception as exc:  # noqa: BLE001 - a raised analyst falls back, never fails the run
            instruction = f"The previous reply could not be used ({type(exc).__name__})."
            continue

        # `confidence: "none"` is a recorded outcome, not a discarded one: a cell with no
        # defensible reading gets no reading (`docs/02` §4.4).
        if output.confidence == "none":
            return output, False

        ungrounded = grounded(output.prose, allowed)
        if not ungrounded:
            return output, False

        sentences = offending_sentences(output.prose, allowed)
        instruction = (
            "These numbers are not in the bundle: "
            + ", ".join(sorted(set(ungrounded)))
            + ". Rewrite, quoting only numbers given to you. The unsupported claim"
            + ("s are" if len(sentences) > 1 else " is")
            + ": "
            + " / ".join(f'"{s}"' for s in sentences)
        )

    # Two ungrounded attempts. The run still completes, with a grounded reading nobody wrote.
    return (
        AnalysisResult(
            prose=template_reading(bundle),
            confidence="low",
            reason="the analyst did not produce grounded prose in two attempts (docs/02 §6.2)",
        ),
        True,
    )


def _reask_shape(reason: str) -> str:
    return (
        "The previous reply did not match the required shape "
        f"({reason[:160]}). Return a JSON object with `prose`, `confidence` and `reason`."
    )
