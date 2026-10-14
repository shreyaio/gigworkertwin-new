"""The design agent's invocation. `docs/02` §4.1. Serves I2 and I4.

It renders; it never proposes. The agent receives **exactly four blocks** — this lever's
commitments, anchor chunks for register, the style contract, and the do-not-say list — and holds no
tools, so there is no door through which a commitment from another threshold can arrive. That is
what makes I2 and I3 structural rather than a matter of prompt discipline.

This module builds the four blocks and validates what comes back. It deliberately does **not**
decide what the blocks contain: the commitments come from :func:`variant.lookup.lookup`, the
do-not-say list from :func:`variant.lookup.do_not_say`, and the anchors from the frozen corpus.
Nothing here consults a model about what a dial means (I1).

It imports from `models/` and `agents/` only, so the layer table holds and the brief can be
assembled by the caller that already has the reference data.
"""

from __future__ import annotations

import json

from twinlab.agents.contract import ContractError, validate_output
from twinlab.agents.registry import ModelClient, resolve_prompt
from twinlab.models.agent import AgentConfig
from twinlab.models.variant import LeverBrief, LeverParagraph

#: The four labelled fences, in the order `docs/02` §3.3 fixes. **Order is part of the contract**:
#: a reordered prompt is a different stimulus, so this tuple is not a formatting preference.
BLOCK_ORDER: tuple[str, ...] = ("COMMITMENTS", "ANCHORS", "STYLE", "DO_NOT_SAY")

#: Keys of `style_contract.yaml` the agent is shown. The lever ordering stays out — it is an
#: orchestrator concern the agent cannot act on.
#:
#: The reading-grade band was withheld until 2026-10-01 on the theory that "showing a model a
#: number it cannot act on invites it to put the number in the prose". Measurement overtook the
#: theory: every dense lever failed gate 3 at grade 17.1-18.1 against a 16.0 ceiling, and the
#: targeted re-render, which describes the breach in words but quotes no number, made several
#: paragraphs *worse* (L1 dial 1 went 11.48 -> 18.07). The band is the one gate the agent was
#: being judged on blind. RESEARCHER, 2026-10-01; see `docs/DECISIONS.md` M16.
#:
#: The original worry is not unguarded: rule 6 of the prompt forbids any number a commitment did
#: not supply, and `check_invariance` would catch a leaked "16.0" as a failed render rather than
#: letting it into a stimulus. Both bounds are shown because the gate tests both.
STYLE_KEYS_SHOWN: tuple[str, ...] = (
    "person",
    "tense",
    "paragraphs_per_lever",
    "word_min",
    "word_max",
    "bullets",
    "numbers",
    "forbidden_terms",
    "forbidden_intensifiers",
    "reading_grade_min",
    "reading_grade_max",
)


def style_block(style_contract: dict) -> dict:
    """The style keys shown to the agent, in a fixed order so the prompt is byte-stable."""
    return {k: style_contract[k] for k in STYLE_KEYS_SHOWN if k in style_contract}


def build_user_prompt(brief: LeverBrief) -> str:
    """The four blocks as labelled fences, in :data:`BLOCK_ORDER`. `docs/02` §3.3.

    Deterministic and byte-stable for a given brief: the commitments are emitted in sorted gap-id
    order and the do-not-say list as it arrives (already sorted by :func:`do_not_say`), so the same
    brief produces the same prompt in every process. Without that, the render cache key would
    describe a prompt that is not reproducible and I11 would be unprovable.

    The lever identity and the dial digit are **not** in the prompt. The agent is told what to
    commit to, never which cell it is serving — a digit in the prompt is a channel through which
    "this is the strong version" could reach the prose and become a confound.
    """
    blocks: dict[str, str] = {
        "COMMITMENTS": "\n".join(
            f"- {brief.commitments[gap_id]}" for gap_id in sorted(brief.commitments)
        ),
        "ANCHORS": "\n\n".join(brief.anchor_chunks),
        "STYLE": json.dumps(style_block(brief.style_contract), indent=2, sort_keys=False),
        "DO_NOT_SAY": "\n".join(f"- {line}" for line in brief.do_not_say),
    }
    parts: list[str] = []
    for name in BLOCK_ORDER:
        parts.append(f"<<<{name}>>>\n{blocks[name]}\n<<<END {name}>>>")
    return "\n\n".join(parts)


def missing_instruction(missing: dict[str, str]) -> str:
    """The one repair for a paragraph that left commitments out. Same agent, same prompt, one call.

    It asks for the missing sentences only, and the caller appends them to the paragraph it already
    has, so the rest of the text is never regenerated. The Checker then judges the combined text.
    """
    lines = "\n".join(f"- {text}" for text in missing.values())
    return (
        "Your previous paragraph left these commitments out. Write one sentence for each of them, "
        "in the order given, stating each one's specific action and object in the same voice. Put "
        "only those sentences in the text, joined by a single space. Do not restate anything else.\n"
        f"{lines}"
    )


async def run_design(
    cfg: AgentConfig,
    brief: LeverBrief,
    client: ModelClient,
    *,
    instruction: str | None = None,
) -> LeverParagraph:
    """One design call → one validated :class:`LeverParagraph`. Never a coerced paragraph.

    An output that will not validate is returned as ``cannot_render`` with the reason, exactly as
    the prompt's `# IF YOU CANNOT` path would. The cell is then marked `failed` and logged; it is
    **never** filled with a generic paragraph (`docs/02` §4.1), and nothing here pads, truncates or
    trims the text to make a gate pass — that is the forbidden column of `docs/02` §5.3.

    Note there is no retry here. `docs/03` §5 allows **one** re-render on gate failure, and it is
    the Checker's caller that spends it, on a cache *miss* only: applying it per cell would call the
    design agent once for every code and break I4.

    ``instruction`` is what that one re-render carries. It names which of the agent's **own**
    requirements the previous attempt missed — a commitment it did not state, a forbidden
    intensifier it used, prose too dense for the register band — and nothing else. It cannot change
    what the paragraph may say: the commitments and the do-not-say list are the brief's and are
    untouched, so this is the design agent's equivalent of the twin's targeted repair
    (`docs/02` §5.4), not the Checker steering the text it grades.
    """
    system_prompt, _ = resolve_prompt(cfg)
    user_prompt = build_user_prompt(brief)
    if instruction:
        user_prompt = f"{user_prompt}\n\n{instruction}"
    result = await client.run(
        cfg,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_type=LeverParagraph,
    )
    output = result.output
    if isinstance(output, LeverParagraph):
        return output
    try:
        outcome = validate_output(output, LeverParagraph)
    except ContractError as exc:
        return LeverParagraph(text="", status="cannot_render", reason=str(exc))
    if not outcome.ok or outcome.output is None:
        return LeverParagraph(text="", status="cannot_render", reason=outcome.reason)
    assert isinstance(outcome.output, LeverParagraph)
    return outcome.output
