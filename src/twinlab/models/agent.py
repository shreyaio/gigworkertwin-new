"""Agent configuration. `docs/02` §2.

Agent behaviour is **data**: a sixth agent is an `agent_configs` row plus a prompt file, not a
deployment. What this module refuses to hold is as specified as what it holds — `docs/02` §2's
"Deliberately absent" table lists seven fields that were considered and rejected, and adding any
of them back is a research decision, not a convenience.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Output modes the provider can actually be held to. **Never `native`** — Ollama Cloud accepts a
#: JSON schema and silently does not enforce it (`ARCHITECTURE.md` §3.2, I13), so `NativeOutput`
#: fails invisibly. Forbidden in `build_agent()` and by the DDL constraint
#: `agent_no_native_output`.
OutputMode = Literal["tool", "prompted"]

#: The mode the specification names and the code must refuse. Kept as a constant so the guard and
#: its test cannot drift apart.
FORBIDDEN_OUTPUT_MODE = "native"


class ConfigError(RuntimeError):
    """A configuration that must not become a running agent.

    Raised before any provider library is imported, so a bad config fails identically whether or
    not `pydantic_ai` is installed.
    """


class ModelRef(BaseModel):
    """Which model, and how it is sampled. `docs/02` §2."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    provider: Literal["ollama", "openai", "mock"] = "ollama"
    name: str
    temperature: float = 0.2
    max_tokens: int = 2048
    #: Set and persisted on every run. **VERIFY:** whether Ollama Cloud honours it is untested;
    #: assume it does not (`docs/02` §7.2). Reproducibility rests on the caches and on full
    #: provenance (I11), never on this.
    seed: int | None = None


class ContextSource(BaseModel):
    """What the registry injects into the prompt. Declarative: resolved, never fetched.

    This is the difference between injection and a tool. A `react: false` agent receives exactly
    these blocks and has no way to ask for anything else — which is what makes I2 and I6
    structural rather than a matter of prompt discipline.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "delta_spec", "anchor_chunks", "style_contract", "do_not_say",
        "persona", "baseline_answers", "battery", "scenario", "bundle",
    ]
    required: bool = True


class RetryPolicy(BaseModel):
    """The repair ladder's budget. `docs/02` §5.4."""

    model_config = ConfigDict(extra="forbid")

    attempts: int = 2
    backoff: Literal["none", "linear", "exponential"] = "exponential"
    #: `targeted` re-asks only the defective items. Re-asking all 37 because two were missing
    #: wastes the scarcest resource in the system — a serial slot — and re-rolls 35 valid
    #: answers, adding variance for no reason.
    repair_mode: Literal["targeted", "full", "none"] = "targeted"

    @field_validator("attempts")
    @classmethod
    def _at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("attempts counts the first call, so it is at least 1")
        return v


class AgentConfig(BaseModel):
    """One agent, as a row. `docs/02` §2."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    agent_id: str
    name: str
    role: str
    enabled: bool = True
    model: ModelRef
    #: Inline text, or `"file:design_v1.md"`. A change is a new file and a version bump, never an
    #: edit in place, so an old run stays reconstructible (`docs/02` §3.1).
    system_prompt: str
    #: sha256 of the **resolved** prompt, computed by `load_prompt()` and frozen onto every run
    #: that used it (I11). Two runs with different hashes are not the same experiment.
    prompt_hash: str = ""
    instructions: list[str] = Field(default_factory=list)
    input_schema: str
    output_schema: str
    output_mode: OutputMode = "tool"
    #: An ALLOW-LIST into `TOOL_REGISTRY`, not capability flags. Checked once, in
    #: `build_agent()`. Design and Twin are `[]`, which is enforceable and obvious in a diff.
    tools: list[str] = Field(default_factory=list)
    context_sources: list[ContextSource] = Field(default_factory=list)
    react: bool = False
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    version: int = 1
    frozen: bool = False

    @field_validator("output_mode", mode="before")
    @classmethod
    def _refuse_native(cls, v: object) -> object:
        """`ARCHITECTURE.md` §3.2 and I13, at the earliest possible point.

        `build_agent()` raises on it too. Refusing it here as well means a `native` row cannot
        even be constructed in memory — including one read back out of a database that somehow
        acquired it before the DDL constraint existed.
        """
        if v == FORBIDDEN_OUTPUT_MODE:
            raise ValueError(
                "native output is unsupported on Ollama Cloud: the provider accepts a JSON "
                "schema without error and does not enforce it (ARCHITECTURE.md §3.2, I13). "
                "Use 'tool' or 'prompted'."
            )
        return v


class AgentResult(BaseModel):
    """One model call's outcome, with the telemetry a run event records.

    The output itself is a validated schema object. `run_events` stores references and telemetry
    only — never a prompt body (I11, `ARCHITECTURE.md` §7.2).
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    agent_id: str
    output: object
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    retries: int = 0
