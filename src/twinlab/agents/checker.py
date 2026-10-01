"""The coverage probe — the **only** model step in the gate. `docs/02` §4.3, `docs/03` §5 gate 1.

One call per commitment, at temperature 0.0, with the commitment and the paragraph as the sole
inputs. Everything else in the Checker is deterministic Python and lives in `variant/checker.py`;
the split is deliberate and the gates are specified in `docs/03` §5 so they cannot drift.

**Uncertainty fails closed.** A call that cannot decide, will not parse, or raises returns
``entailed: false`` with the reason. A gate that cannot decide has not passed, and this module has
no path that turns an unusable answer into a pass — that is the whole of its contribution to I3.
"""

from __future__ import annotations

from twinlab.agents.contract import ContractError, validate_output
from twinlab.agents.registry import ModelClient, resolve_prompt
from twinlab.models.agent import AgentConfig
from twinlab.models.variant import CoverageProbe, CoverageVerdict

#: The two labelled fences, in the order `docs/02` §3.3 fixes.
BLOCK_ORDER: tuple[str, ...] = ("COMMITMENT", "PARAGRAPH")


def build_user_prompt(probe: CoverageProbe) -> str:
    """The commitment and the paragraph, and nothing else. `docs/02` §4.3.

    The gap id is **not** sent. The probe judges entailment of a sentence by a paragraph; an
    identifier would tell it which threshold it is looking at and invite it to reason about the
    codebook rather than read the text.
    """
    blocks = {"COMMITMENT": probe.commitment, "PARAGRAPH": probe.paragraph}
    return "\n\n".join(f"<<<{n}>>>\n{blocks[n]}\n<<<END {n}>>>" for n in BLOCK_ORDER)


async def run_coverage_probe(
    cfg: AgentConfig,
    probe: CoverageProbe,
    client: ModelClient,
) -> CoverageVerdict:
    """One probe → one verdict. Every failure mode returns ``entailed=False``.

    `config/agents.default.yaml` gives the checker ``attempts: 1`` and ``repair_mode: none``: an
    unparseable verdict counts as not entailed and is **not** re-asked (`docs/02` §5.5). Re-asking
    a gate until it answers cleanly is how a gate stops being one.
    """
    system_prompt, _ = resolve_prompt(cfg)
    try:
        result = await client.run(
            cfg,
            system_prompt=system_prompt,
            user_prompt=build_user_prompt(probe),
            output_type=CoverageVerdict,
        )
    except Exception as exc:  # noqa: BLE001 - a probe that raised has not decided
        return CoverageVerdict(entailed=False, reason=f"probe raised {type(exc).__name__}: {exc}")

    output = result.output
    if isinstance(output, CoverageVerdict):
        return output
    try:
        outcome = validate_output(output, CoverageVerdict)
    except ContractError as exc:
        return CoverageVerdict(entailed=False, reason=f"unparseable verdict: {exc}")
    if not outcome.ok or outcome.output is None:
        return CoverageVerdict(entailed=False, reason=f"invalid verdict: {outcome.reason}")
    assert isinstance(outcome.output, CoverageVerdict)
    return outcome.output
