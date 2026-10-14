"""AgentConfig → a runnable agent. `docs/02` §2 and §2.1.

Agent behaviour is data. Adding a sixth agent is a config row plus a prompt file; the only Python
is a one-line registration in :data:`SCHEMA_REGISTRY` or :data:`TOOL_REGISTRY`. The indirection is
built now, with five agents, because retrofitting it later means rewriting all five.

Three things are enforced here rather than trusted:

* **I13 / `ARCHITECTURE.md` §3.2** — ``output_mode == "native"`` raises. The provider accepts a
  JSON schema without error and does not enforce it, so `NativeOutput` fails invisibly.
* **I2** — the design agent's tool list is empty and cannot be otherwise. A design agent that can
  fetch can pull threshold 2.2 material into an `01000` render, and `01000` stops differing from
  `02000`.
* **I6** — the same for the twin agent, which could otherwise read its own holdout answers.

Every config gate runs **before** any provider library is imported, so a bad config fails
identically whether or not `pydantic_ai` is installed.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel

from config.settings import CONFIG_DIR, settings
from twinlab.agents.tools import TOOL_REGISTRY
from twinlab.models.agent import (
    FORBIDDEN_OUTPUT_MODE,
    AgentConfig,
    AgentResult,
    ConfigError,
    ModelRef,
)
from twinlab.models.analysis import AnalysisBundle, AnalysisResult
from twinlab.models.run import ManagerDecision, ManagerState
from twinlab.models.twin import AnswerVector, RoundPrompt, TwinAnswerSet
from twinlab.models.variant import (
    CoverageProbe,
    CoverageVerdict,
    LeverBrief,
    LeverParagraph,
)

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

#: Agents that may never hold a tool, with the invariant that says so. Checked by
#: :func:`validate_config`, so the prohibition does not depend on a tool being absent from
#: :data:`TOOL_REGISTRY`.
TOOLLESS_AGENTS: dict[str, str] = {
    "design": "I2 — a design agent that can fetch can pull another threshold into a render",
    "twin": "I6 — a twin that can fetch can read its own holdout answers",
}

#: The eight shapes named in `docs/02` §2.1, plus the Manager's two.
#:
#: §2.1's list omits the Manager, which §1 nonetheless lists as one of the five agents, so its
#: input and output shapes are registered here as well (`docs/DECISIONS.md`).
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "LeverBrief": LeverBrief,
    "LeverParagraph": LeverParagraph,
    "RoundPrompt": RoundPrompt,
    "TwinAnswerSet": TwinAnswerSet,
    # The twin's *transport* shape. This, not `TwinAnswerSet`, is what the twin agent is
    # configured with: a schema handed to the provider validates nothing there and validates too
    # much in pydantic-ai. `TwinAnswerSet` stays registered because the ladder names it as the
    # shape it validates against in Python.
    "AnswerVector": AnswerVector,
    "CoverageProbe": CoverageProbe,
    "CoverageVerdict": CoverageVerdict,
    "AnalysisBundle": AnalysisBundle,
    "AnalysisResult": AnalysisResult,
    "ManagerState": ManagerState,
    "ManagerDecision": ManagerDecision,
}

#: The mandatory prompt skeleton, in this order. `docs/02` §3.2.
#:
#: A consistent skeleton makes prompts diffable, makes an omission obvious, and stops instructions
#: drifting between the role and the rules where models weight them differently. `# IF YOU CANNOT`
#: is not padding: a model given no failure path invents one, and an invented failure path is a
#: silent data defect.
PROMPT_SECTIONS: tuple[str, ...] = (
    "# ROLE",
    "# INPUTS",
    "# TASK",
    "# RULES",
    "# OUTPUT",
    "# IF YOU CANNOT",
)


def register_schema(key: str, model: type[BaseModel]) -> None:
    """One-line registration for a new agent's output shape (`docs/02` §2.1)."""
    if key in SCHEMA_REGISTRY and SCHEMA_REGISTRY[key] is not model:
        raise ConfigError(f"schema {key!r} is already registered to something else")
    SCHEMA_REGISTRY[key] = model


# --------------------------------------------------------------------------- prompts


def load_prompt(reference: str) -> str:
    """``"file:design_v1.md"`` → the file's contents; anything else is an inline prompt.

    Prompts are versioned files under `agents/prompts/`. Inlining one in a database row would make
    diffing and review impossible (`docs/02` §2), and a change is a new file plus a version bump so
    an old run stays reconstructible (§3.1).
    """
    if not reference.startswith("file:"):
        return reference
    path = PROMPTS_DIR / reference.removeprefix("file:")
    if not path.exists():
        raise ConfigError(f"prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def prompt_hash(resolved: str) -> str:
    """sha256 over the resolved prompt text. Frozen onto every run that used it (I11).

    Two runs with different hashes are not the same experiment, and the UI says so.
    """
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()


def check_prompt_skeleton(resolved: str, *, where: str = "prompt") -> None:
    """The six sections, present and **in order**. `docs/02` §3.2. Raises :class:`ConfigError`."""
    positions: list[int] = []
    for section in PROMPT_SECTIONS:
        index = _section_index(resolved, section)
        if index < 0:
            raise ConfigError(f"{where}: missing mandatory section {section!r} (docs/02 §3.2)")
        positions.append(index)
    if positions != sorted(positions):
        order = [
            s for _, s in sorted(zip(positions, PROMPT_SECTIONS, strict=True), key=lambda p: p[0])
        ]
        raise ConfigError(
            f"{where}: sections out of order. Found {order}, expected {list(PROMPT_SECTIONS)} "
            "(docs/02 §3.2 — a reordered prompt is a different stimulus)"
        )


def _section_index(text: str, heading: str) -> int:
    """Where a heading starts, as a line of its own. ``-1`` when absent."""
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.strip() == heading:
            return offset
        offset += len(line)
    return -1


def resolve_prompt(cfg: AgentConfig) -> tuple[str, str]:
    """``(resolved text, hash)``, with the skeleton checked. Every agent goes through here."""
    resolved = load_prompt(cfg.system_prompt)
    check_prompt_skeleton(resolved, where=f"{cfg.agent_id} ({cfg.system_prompt})")
    return resolved, prompt_hash(resolved)


# --------------------------------------------------------------------------- config gates


def validate_config(cfg: AgentConfig, *, require_schema: bool = True) -> AgentConfig:
    """Every check that must hold before an agent exists. Raises :class:`ConfigError`.

    Deliberately importing nothing from a provider: a config is either admissible or it is not,
    and that answer must not depend on which packages are installed.
    """
    if cfg.output_mode == FORBIDDEN_OUTPUT_MODE:
        raise ConfigError(
            f"{cfg.agent_id}: native output is unsupported on Ollama Cloud — the provider "
            "accepts a JSON schema without error and does not enforce it "
            "(ARCHITECTURE.md §3.2, I13)"
        )
    if cfg.agent_id in TOOLLESS_AGENTS and cfg.tools:
        raise ConfigError(
            f"{cfg.agent_id} must have tools == []: {TOOLLESS_AGENTS[cfg.agent_id]}. "
            f"Refusing to build it with {cfg.tools}."
        )
    unknown = sorted(set(cfg.tools) - TOOL_REGISTRY.keys())
    if unknown:
        raise ConfigError(f"{cfg.agent_id}: unknown tools {unknown}")
    if require_schema:
        for field_name in ("input_schema", "output_schema"):
            key = getattr(cfg, field_name)
            if key not in SCHEMA_REGISTRY:
                raise ConfigError(f"{cfg.agent_id}: unknown {field_name} {key!r}")
    if cfg.react and cfg.agent_id in TOOLLESS_AGENTS:
        raise ConfigError(f"{cfg.agent_id} must be react: false — {TOOLLESS_AGENTS[cfg.agent_id]}")
    if cfg.react and not cfg.tools:
        raise ConfigError(
            f"{cfg.agent_id}: react: true with no tools is a loop with nothing to call"
        )
    return cfg


def resolve_model(model: ModelRef) -> Any:
    """ModelRef → a pydantic-ai model object. Imported lazily.

    Both live providers speak the OpenAI wire format and resolve through `OpenAIProvider`, but
    **against different endpoints**, and the provider on the `ModelRef` is what decides which.

    Until 2026-10-08 `openai` and `ollama` both resolved against `settings.ollama_base_url` with
    `settings.ollama_api_key`. Selecting `openai` in Agent Studio therefore changed nothing: the
    call went to Ollama Cloud, with the Ollama key, and the run recorded a provider it had never
    reached. That is a silent misattribution in the evidence, so `openai` now **refuses** rather
    than falling back — `docs/DECISIONS.md` 2026-10-08.

    A second *model* does not need a second provider: validity test 7 compares two model names on
    one endpoint, and `mistral-large-4` or `deepseek-v4-pro:0813` are reachable by name with
    nothing configured. `openai` is for a genuinely different endpoint.
    """
    if model.provider == "mock":
        raise ConfigError(
            "the 'mock' provider has no live model: install a StubModelClient with "
            "`set_client()` instead"
        )
    if model.provider not in ("ollama", "openai"):
        raise ConfigError(f"unsupported provider {model.provider!r}")

    if model.provider == "openai":
        base_url, api_key = settings.openai_base_url, settings.openai_api_key
        if not base_url:
            raise ConfigError(
                "provider 'openai' has no OPENAI_BASE_URL, so there is no endpoint to send it "
                "to. It is not defaulted to the Ollama one: that is what made this setting a "
                "no-op that recorded a provider the call never reached. Set OPENAI_BASE_URL and "
                "OPENAI_API_KEY, or use provider 'ollama' — every model that endpoint serves, "
                "Mistral and DeepSeek included, is reachable there by name."
            )
    else:
        base_url, api_key = settings.ollama_base_url, settings.ollama_api_key

    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    return OpenAIChatModel(
        model.name, provider=OpenAIProvider(base_url=base_url, api_key=api_key)
    )


def build_agent(
    cfg: AgentConfig,
    *,
    output_type: type[BaseModel] | None = None,
    system_prompt: str | None = None,
) -> Any:
    """AgentConfig → a pydantic-ai Agent.

    `ARCHITECTURE.md` §3.2: the output marker is `ToolOutput` or `PromptedOutput`, never
    `NativeOutput` — pydantic-ai raises `UserError` on it for `ollama.com` URLs, and that is not
    worked around.
    """
    validate_config(cfg)
    resolved = system_prompt if system_prompt is not None else resolve_prompt(cfg)[0]
    schema = output_type or SCHEMA_REGISTRY[cfg.output_schema]

    from pydantic_ai import Agent, PromptedOutput, ToolOutput

    marker = ToolOutput if cfg.output_mode == "tool" else PromptedOutput
    return Agent(
        model=resolve_model(cfg.model),
        output_type=marker(schema),
        system_prompt=resolved,
        tools=[TOOL_REGISTRY[t] for t in cfg.tools],
        # `max_tokens` was declared on all five agents and silently never passed. For a 45-75 word
        # paragraph the 512 default is moot, but the twin's 1024 is a real ceiling on a 37-item
        # vector (M6), and a truncated vector fails the contract rather than being coerced (I13) —
        # so it would have shown up as unexplained twin failures, not as a missing setting.
        model_settings={
            "temperature": cfg.model.temperature,
            "max_tokens": cfg.model.max_tokens,
            "seed": cfg.model.seed,
        },
    )


# --------------------------------------------------------------------------- clients


class ModelClient(Protocol):
    """How the platform talks to a model. One implementation per provider, plus the stub."""

    name: str

    async def run(
        self,
        cfg: AgentConfig,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> AgentResult: ...


class StubModelClient:
    """Returns fixtures. CI and every test use this: **no test ever calls a live LLM.**

    Counts calls per agent, because most agent tests assert on the contract rather than the prose
    — "the design agent was called exactly 10 times for 243 codes" is the M5 acceptance test, and
    it needs a counter, not wall time.
    """

    name = "stub"

    def __init__(
        self, handler: Callable[[AgentConfig, str, type[BaseModel]], Any | Awaitable[Any]]
    ) -> None:
        self._handler = handler
        self.calls: list[tuple[str, str]] = []

    async def run(
        self,
        cfg: AgentConfig,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> AgentResult:
        self.calls.append((cfg.agent_id, user_prompt))
        started = time.perf_counter()
        out = self._handler(cfg, user_prompt, output_type)
        if hasattr(out, "__await__"):
            out = await out
        return AgentResult(
            agent_id=cfg.agent_id,
            output=out,
            model=f"stub:{cfg.model.name}",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def call_count(self, agent_id: str) -> int:
        return sum(1 for a, _ in self.calls if a == agent_id)


#: Transport attempts for a transient provider failure. **A separate budget from
#: :class:`RetryPolicy`**, which is the *schema repair* ladder: a wrong prompt fails identically
#: every time and must not be re-paid for three times (`docs/DECISIONS.md`, 2026-09-22), whereas a
#: 429 on the free tier's single slot succeeds on the next attempt and must not cost a twin.
TRANSPORT_ATTEMPTS = 3

#: Base delay for the exponential ladder: 1 s, 2 s, 4 s.
TRANSPORT_BASE_DELAY = 1.0

#: Substrings that mark a transport failure in a provider message, for the case where no status
#: code is exposed. Matched case-insensitively.
_TRANSIENT_MARKERS = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "timeout",
    "timed out",
    "connection reset",
    "connection aborted",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "overloaded",
)


def is_transient(exc: BaseException) -> bool:
    """Whether a failed provider call is worth repeating. `docs/DECISIONS.md`, 2026-09-22.

    Classified on the **exception**, not on an SDK type, so no provider library is imported to
    decide it. A status code is read where one is exposed (429 and 5xx are transient; every other
    4xx is the caller's fault and repeating it just spends the slot again); otherwise the message
    is matched against :data:`_TRANSIENT_MARKERS`.

    A schema failure is deliberately **not** transient — it is the output contract's business, and
    the repair ladder in `agents/contract.py` owns it.
    """
    for attr in ("status_code", "status", "code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and 100 <= value < 600:
            return value == 429 or value >= 500
    if isinstance(exc, TimeoutError | ConnectionError):
        return True
    text = str(exc).lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


class PydanticAIClient:
    """The live client. `pydantic_ai` is imported lazily, so the deterministic layers and CI do
    not depend on the package being installed.

    **Transient provider failures are retried here, with backoff.** Without it, a single 429
    during a sweep raises out of the twin call, `ask_panel` logs it and moves on, and the cell
    **completes** with one twin fewer than its neighbours — a cell answered by a different set of
    twins, which is exactly what I14 forbids, recorded as a result. Provider pressure is a
    condition to wait out, not a reason to drop a twin.
    """

    name = "pydantic-ai"

    async def run(
        self,
        cfg: AgentConfig,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> AgentResult:
        agent = build_agent(cfg, output_type=output_type, system_prompt=system_prompt)
        started = time.perf_counter()
        result = await self._run_with_backoff(agent, user_prompt, cfg)
        prompt_tokens, completion_tokens = _token_counts(result)
        return AgentResult(
            agent_id=cfg.agent_id,
            output=result.output,
            model=cfg.model.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def _run_with_backoff(
        self, agent: Any, user_prompt: str, cfg: AgentConfig
    ) -> Any:
        """One model call, repeated only while :func:`is_transient` says it is worth repeating.

        ``settings.delay_seconds`` is honoured before every attempt. The Settings tab offers it as
        *Pause between AI calls — raise it if calls start being refused*, and until now nothing
        read it, so the remedy the UI recommended did nothing.
        """
        last: Exception | None = None
        for attempt in range(TRANSPORT_ATTEMPTS):
            if settings.delay_seconds > 0:
                await asyncio.sleep(settings.delay_seconds)
            try:
                return await agent.run(user_prompt)
            except Exception as exc:  # noqa: BLE001 — re-raised below unless transient
                last = exc
                if attempt == TRANSPORT_ATTEMPTS - 1 or not is_transient(exc):
                    raise
                delay = _backoff_delay(cfg.retry.backoff, attempt)
                log.warning(
                    "%s: transient provider failure (%s); retrying in %.1fs (attempt %d of %d)",
                    cfg.agent_id, exc, delay, attempt + 2, TRANSPORT_ATTEMPTS,
                )
                await asyncio.sleep(delay)
        raise ConfigError(f"unreachable: transport ladder exhausted without raising ({last!r})")


def _backoff_delay(shape: str, attempt: int) -> float:
    """The wait before the next transport attempt, in the shape the agent's config names.

    ``RetryPolicy.backoff`` was declared on all five agents, seeded into `agent_configs` and shown
    in Agent Studio while being read by nothing. It shapes the wait here; the attempt *count* stays
    :data:`TRANSPORT_ATTEMPTS`, because `attempts` budgets schema repairs, not provider pressure.
    """
    if shape == "none":
        return 0.0
    if shape == "linear":
        return TRANSPORT_BASE_DELAY * (attempt + 1)
    return TRANSPORT_BASE_DELAY * (2**attempt)


#: Token-count attribute names, newest first. pydantic-ai renamed them between the 0.0.x line
#: `requirements.txt` was written against and the 2.x line actually installed.
_TOKEN_FIELDS: tuple[tuple[str, str], ...] = (
    ("input_tokens", "output_tokens"),      # pydantic-ai 2.x
    ("request_tokens", "response_tokens"),  # pydantic-ai 0.0.x
)


def _token_counts(result: Any) -> tuple[int | None, int | None]:
    """``(prompt, completion)`` token counts from a run result, across pydantic-ai generations.

    Written defensively because **both** ways of getting this wrong are silent. `usage` became a
    property in 2.x, so calling it raised `TypeError` *after* the model call had already been paid
    for; and the fields were renamed, so a naive `getattr(..., "request_tokens", None)` returns
    `None` on 2.x without complaint. `docs/10`'s cost model and the whole credit budget are built
    on these numbers, and a permanently-`None` token count would make the budget unmeasurable while
    looking like it worked.

    Raises :class:`ConfigError` if no known naming matches: an unrecognised usage object means the
    provider library moved again, and guessing would re-create the silent failure.
    """
    usage = result.usage
    if callable(usage):            # pydantic-ai 0.0.x exposed a method
        usage = usage()
    for prompt_field, completion_field in _TOKEN_FIELDS:
        if hasattr(usage, prompt_field) or hasattr(usage, completion_field):
            return getattr(usage, prompt_field, None), getattr(usage, completion_field, None)
    raise ConfigError(
        f"cannot read token counts from {type(usage).__name__}: none of "
        f"{[f for pair in _TOKEN_FIELDS for f in pair]} is present. pydantic-ai has changed its "
        "usage API again — add the new names to _TOKEN_FIELDS rather than letting the counts go "
        "silently None (docs/10 costs every estimate on them)."
    )


_client: ModelClient | None = None


def get_client() -> ModelClient:
    global _client
    if _client is None:
        _client = PydanticAIClient()
    return _client


#: `base_url` → the model ids that endpoint serves, or ``None`` when it could not be asked.
#: Process-level and never invalidated: a provider's catalogue does not change inside a session,
#: and this is consulted on a UI readiness path that must not issue a request per repaint.
_SERVED_MODELS: dict[str, frozenset[str] | None] = {}


async def served_model_names(*, timeout: float = 5.0) -> frozenset[str] | None:
    """Model ids the configured endpoint serves, or ``None`` if it could not be listed.

    **``None`` is "not known", never "none served".** Every caller treats it as "cannot check"
    and proceeds, because a provider listing that is slow or blocked must not be able to stop a
    validity test the researcher is entitled to run. The only thing this buys is catching a typo
    before it costs a round of calls, and a check that can produce a false refusal costs more than
    the typo does.

    Cached for the life of the process, including the ``None``: a readiness line is repainted on
    every change of the session or version dropdown, and one GET per repaint is a request storm
    against the same endpoint the sweep is queueing on.
    """
    # No key means mock mode: there is no endpoint to ask and nothing in CI may reach one
    # (`CLAUDE.md`, Testing). Not cached — the key can be set without restarting the process.
    if not settings.ollama_api_key:
        return None

    base = settings.ollama_base_url.rstrip("/")
    if base in _SERVED_MODELS:
        return _SERVED_MODELS[base]

    names: frozenset[str] | None = None
    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as http:
            response = await http.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {settings.ollama_api_key}"},
            )
            response.raise_for_status()
            served = response.json().get("data") or []
        names = frozenset(str(m["id"]) for m in served if m.get("id"))
        # An endpoint that answers with an empty catalogue is indistinguishable here from one
        # that answered something this code cannot read. Neither supports refusing a model name.
        names = names or None
    except Exception as exc:  # noqa: BLE001 — never block on a provider listing
        log.info("could not list models at %s (%r); model names will not be checked", base, exc)

    _SERVED_MODELS[base] = names
    return names


def reset_served_models() -> None:
    """Drop the cached catalogue. Test hook; the application does not call it."""
    _SERVED_MODELS.clear()


def set_client(client: ModelClient | None) -> None:
    """Install a client. Tests install :class:`StubModelClient`; the app does not call this."""
    global _client
    _client = client


# --------------------------------------------------------------------------- seed configs


@lru_cache(maxsize=1)
def default_agent_configs() -> dict[str, AgentConfig]:
    """The seed configs from `config/agents.default.yaml`, validated and hashed on load.

    `prompt_hash` is computed from the resolved prompt rather than read from the YAML, so the two
    cannot disagree: the hash always describes the text the agent would actually be given.
    """
    path = CONFIG_DIR / "agents.default.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    configs: dict[str, AgentConfig] = {}
    for entry in raw["agents"]:
        cfg = AgentConfig(**entry)
        _, digest = resolve_prompt(cfg)
        cfg = cfg.model_copy(update={"prompt_hash": digest})
        validate_config(cfg)
        configs[cfg.agent_id] = cfg
    return configs


# --------------------------------------------------------------- the live config (M19 WP-8)

#: `agent_id` → the stored `agent_configs` row's fields. **Pushed in** by
#: `services.agent_config.refresh_agent_configs`, never read from here: `agents/` may not import
#: `db/` (`ARCHITECTURE.md` §4), and `variant/` importing `services/` would invert the layering,
#: so the service does the reading and this module does the merging.
#:
#: Empty means "nothing stored", and every call site then gets the YAML seed — which is what the
#: whole runtime did until M19 WP-8.
_LIVE: dict[str, dict] = {}

#: `agent_id` → the `agent_configs.version` the live config came from. Frozen onto every session
#: as `sessions.config["agent_versions"]`, which is `ARCHITECTURE.md` §1.1's "frozen onto every
#: run that used them" satisfied in the data rather than in a docstring.
_LIVE_VERSIONS: dict[str, int] = {}


class AgentDisabled(ConfigError):
    """A disabled agent's config was requested at a call site that needs it to run.

    `AgentConfig.enabled` gated **nothing** before M19 WP-8 — a grep across `src/` found exactly
    one read, `ui/components/domain.py`, which paints a pill. Setting the Results Analyst to
    disabled changed a badge, and the analyst was still called.

    Each call site turns this into its own defined outcome rather than a generic failure, because
    "disabled" means something different per agent: the analyst has a deterministic template to
    fall back to, the design agent and the twin do not, and the Checker may not be disabled at all
    (I3).
    """


def set_live_agent_configs(
    rows: dict[str, dict], versions: dict[str, int] | None = None
) -> None:
    """Install the stored `agent_configs` rows as the process override. WP-8.

    Called only by `services.agent_config.refresh_agent_configs`. Takes plain dicts rather than
    `AgentConfig`s so an invalid stored row can be rejected **per agent** at merge time, with a
    fallback to the seed for that agent only, instead of taking down the whole refresh.
    """
    global _LIVE, _LIVE_VERSIONS
    _LIVE = {str(k): dict(v) for k, v in rows.items()}
    _LIVE_VERSIONS = {str(k): int(v) for k, v in (versions or {}).items()}


def reset_live_agent_configs() -> None:
    """Drop the override. Test hook; the application does not call it."""
    set_live_agent_configs({}, {})


def live_agent_versions() -> dict[str, int]:
    """`agent_id → agent_configs.version` for every stored row.

    Only agents with a stored row appear: an agent running on the YAML seed has no version to
    record, and writing `1` for it would be indistinguishable from a stored version 1.
    """
    return dict(_LIVE_VERSIONS)


def live_agent_configs() -> dict[str, AgentConfig]:
    """The agent configs **actually in force**: the stored rows over the YAML seed. WP-8.

    The twin-config precedence applied to agents (`docs/09` §4): the YAML is the *seed*, the
    stored row is what the researcher chose in Agent Studio, and the stored row wins. Until M19
    WP-8 every call site read :func:`default_agent_configs` directly, so Agent Studio's edits were
    saved, versioned, audited — and read by nothing except Agent Studio.

    That was a documented holding position (`services.agent_config.in_force` still explains it)
    and it is not compatible with `ARCHITECTURE.md` §1.1, which is one of the three principles the
    product is built on: *"Models, prompts, thresholds, weights, run limits, wording variants,
    sample sizes and agent behaviour are all editable from the frontend by someone with no
    engineering background, versioned on write, and frozen onto every run that used them."*

    **A stored row that will not validate falls back to the seed for that agent only**, logged
    once at WARNING. That is the behaviour `services.agent_config.load_agent` already had, for the
    same reason: the seed is a defined state, and raising here would take down every call site in
    the runtime rather than one screen.

    `validate_config` runs on every merged config, so I2 and I6 cannot be weakened by a stored
    row: a tool on `design` or `twin`, or `output_mode: native`, is refused here exactly as it is
    on save.
    """
    out = dict(default_agent_configs())
    for agent_id, stored in _LIVE.items():
        seeded = out.get(agent_id)
        merged = {**(seeded.model_dump() if seeded else {}), **stored}
        try:
            cfg = AgentConfig(
                **{k: v for k, v in merged.items() if k in AgentConfig.model_fields}
            )
            _, digest = resolve_prompt(cfg)
            cfg = cfg.model_copy(update={"prompt_hash": digest})
            validate_config(cfg)
        except Exception as exc:  # noqa: BLE001 — one bad row must not break every call site
            log.warning(
                "stored agent_configs row for %r does not validate (%s); %s",
                agent_id,
                exc,
                "falling back to the seeded config for that agent only"
                if seeded
                else "and there is no seeded config to fall back to, so it is ignored",
            )
            continue
        out[agent_id] = cfg
    return out


def live_agent(agent_id: str) -> AgentConfig:
    """One agent's live config, **refusing a disabled one**. WP-8 item 4.

    Raises :class:`AgentDisabled` rather than handing back a config the caller would run anyway.
    Call sites with a defined non-model path catch it; the ones without fail loudly, which is
    correct — a disabled twin means nothing can be asked, and asking it anyway would make the
    toggle a lie in the other direction.
    """
    configs = live_agent_configs()
    if agent_id not in configs:
        raise ConfigError(f"no agent {agent_id!r}")
    cfg = configs[agent_id]
    if not cfg.enabled:
        raise AgentDisabled(
            f"{cfg.name} ({agent_id}) is switched off in Agent Studio, so it cannot be run. "
            "Switch it back on there, or use a path that does not need it."
        )
    return cfg

