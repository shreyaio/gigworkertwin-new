"""Agent Studio — configure and test each agent. `docs/06` §6.

**Not the execution engine.** The study runs from Twin Lab; this screen edits configuration and
builds test views over it. The most important line in `docs/06` §6 is the last one:

    Run Manager's test button builds a plan; it never launches a sweep.

:func:`manager_plan` is therefore a pure function of counts and settings. It creates no session,
starts no task and makes no model call, and the M11 acceptance test asserts no session row appears.

Two other rules are enforced here rather than in the UI, because a disabled control is not a
guarantee:

* **A frozen agent cannot be edited while a session is running** (`docs/06` §6). Freezing is what
  makes a sweep's configuration stable; editing underneath a live session would mean two halves of
  one sweep ran under different instructions, with nothing in the data to show it.
* **`native` is never offered as an output mode.** `AgentConfig` refuses to construct one and
  `build_agent` raises on it (I13, `docs/02` §5.1); :data:`OUTPUT_MODES` is the UI's list and holds
  two entries, so the option cannot appear even by accident.

Every write appends to `agent_config_history` with its `changed_fields` and its `action`. That
table is the audit trail the *What was changed* log reads, and saves, restores and freezes each
write their own row.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import VariantRepo
from twinlab.models.agent import AgentConfig
from twinlab.models.view import StatusRow

log = logging.getLogger(__name__)

#: The output modes the UI offers. `native` is absent by construction, not by filtering
#: (`docs/02` §5.1, I13): the provider accepts a JSON schema and silently does not enforce it.
OUTPUT_MODES: tuple[str, ...] = ("tool", "prompted")


def _providers() -> tuple[str, ...]:
    """The providers the UI may offer, **read off `ModelRef.provider`'s Literal**. §5.5 item 1.

    Derived, never hand-written. Agent Studio showed `Mistral` as a provider, which `ModelRef`
    rejects — so either the stored row was invalid or the dropdown offered an option the model
    refuses, and it was both. A hand-maintained list is a second source of truth that drifts from
    the type it is supposed to mirror, which is the same failure `db/client.TABLE_COLUMNS` is
    derived to avoid.
    """
    from typing import get_args

    return tuple(get_args(AgentConfig.model_fields["model"].annotation.model_fields[
        "provider"
    ].annotation))


#: The AI providers the dropdown offers. `mistral` is absent because the type has no such member.
PROVIDERS: tuple[str, ...] = _providers()

#: `agent_config_history.action`. Each is a separate row; none replaces another (I9).
ACTIONS: tuple[str, ...] = ("saved", "restored", "frozen", "unfrozen")

#: The shared rules panel's key in `app_config`, and the pseudo-agent id its history uses.
RULES_KEY = "RULES"

#: `docs/06` §6's *Checker rules*, with the defaults `docs/08` §2.1 sets.
CHECKER_RULES: tuple[tuple[str, str, float], ...] = (
    ("mae_max", "Keep a twin if average error at most", 1.0),
    ("pct_within_1_min", "At least this share within 1 point", 0.80),
    ("repair_attempts", "Times to ask again for a bad answer", 1),
    ("rate_limit_retries", "Tries when rate limited", 3),
)

#: `docs/06` §6's *Analyst score weights*. Default 1 each; **0 omits a metric from the index**.
#: The sign flip is deliberately not here — it comes from `constructs.index_sign` in the frozen
#: data, so a file edit cannot invert what a metric means (`docs/07` §4.1).
WEIGHT_METRICS: tuple[str, ...] = (
    "fairness",
    "clarity",
    "happiness",
    "staying",
    "pushback",
    "leaving",
)

#: `docs/06` §6's left-hand list, in its order — Twin Interviewer first, Run Manager last.
STUDIO_AGENT_ORDER: tuple[str, ...] = ("twin", "design", "checker", "analyst", "manager")


#: Agents whose `enabled` switch may not be turned off, and why. WP-8 item 4.
#:
#: The Checker's coverage probe is what makes I3 enforceable: disabling it would let an unverified
#: stimulus reach a twin, and a probe that did not run must never look like one that passed. That
#: is not a preference to be weighed against convenience, so the save is **refused** rather than
#: the UI merely hiding the toggle — `CLAUDE.md` rule 1, and the refusal has to hold for an API
#: wrapper and a direct service call too.
UNDISABLEABLE: dict[str, str] = {
    "checker": (
        "the Quality Checker cannot be switched off. Its coverage probe is what enforces I3 — "
        "every render is verified before any twin sees it — and a probe that did not run must "
        "never look like one that passed."
    ),
}


class AgentConfigError(RuntimeError):
    """Any refusal to change an agent's configuration."""


class AgentFrozen(AgentConfigError):
    """A frozen agent was edited while a session was running. `docs/06` §6.

    Freezing is what makes a sweep's configuration stable. Editing underneath a live session would
    split one sweep across two sets of instructions with nothing in the data to show it.
    """


# ------------------------------------------------- the live config (M19 WP-8)


async def refresh_agent_configs(
    backend: DbBackend | None = None,
) -> dict[str, AgentConfig]:
    """Re-read `agent_configs` and install it as the runtime's live config. WP-8.

    Mirrors :func:`services.config.refresh_twin_config` exactly, including its failure policy: a
    read that fails is logged and swallowed, because an unreachable database must not stop a UI
    tick and the YAML seed is a defined state to fall back to. A stored row that does not
    *validate* is handled per agent by `registry.live_agent_configs`, not here.

    The merging lives in `agents/registry.py` and the reading lives here, because `agents/` may
    not import `db/` (`ARCHITECTURE.md` §4) and `variant/` importing `services/` would invert the
    layering. So this function reads rows and pushes them down; nothing below the service layer
    touches the database.

    Called at boot (`services.config.startup_check`) and before every session, gate and Studio ask
    (`services.runs.session_config`) — the same boundaries the twin config uses, so an edit saved
    in Agent Studio governs the next thing the researcher starts and nothing already running.
    """
    from twinlab.agents.registry import live_agent_configs, set_live_agent_configs

    db = backend or get_backend()
    try:
        rows = await db.select("agent_configs", None)
    except Exception as exc:  # noqa: BLE001 — never block a UI tick on a config read
        log.warning("could not read agent_configs: %r", exc)
        return live_agent_configs()

    known = set(AgentConfig.model_fields)
    fresh: dict[str, dict[str, Any]] = {}
    versions: dict[str, int] = {}
    for row in rows:
        agent_id = str(row.get("agent_id") or "")
        if not agent_id:
            continue
        fresh[agent_id] = {k: v for k, v in row.items() if k in known}
        versions[agent_id] = int(row.get("version") or 1)
    set_live_agent_configs(fresh, versions)
    log.info(
        "live agent configs: %s",
        ", ".join(f"{a}=v{versions[a]}" for a in sorted(versions)) or "none stored",
    )
    return live_agent_configs()


# ------------------------------------------------------------------ reading


async def load_agent(
    agent_id: str, *, backend: DbBackend | None = None
) -> AgentConfig:
    """One agent's live configuration, falling back to the seeded default.

    The fallback matters on a machine with no database: the screen must show the real seeded
    config rather than an empty form that a researcher might then save over the top of.
    """
    from twinlab.agents.registry import default_agent_configs

    db = backend or get_backend()
    defaults = default_agent_configs()
    rows = await db.select("agent_configs", [("eq", "agent_id", agent_id)], limit=1)
    if rows:
        try:
            return AgentConfig(
                **{k: v for k, v in rows[0].items() if k in AgentConfig.model_fields}
            )
        except Exception as exc:  # noqa: BLE001 — see below
            # A stored row that no longer validates. The live case is the stale `mistral` row
            # (`ARCHITECTURE_UPDATE.md` §1.2): `ModelRef.provider` is
            # `Literal["ollama", "openai", "mock"]`, so there is no `mistral` provider in the model
            # at all and constructing it raises.
            #
            # Falling back to the seed is right because the seed is **what the runtime actually
            # runs** — every agent is built from `default_agent_configs()` at the call site — so
            # this
            # shows the truth rather than an error card. It is logged at WARNING, not swallowed:
            # `correct_stale_models` is what repairs the row, and it runs at boot.
            if agent_id not in defaults:
                raise
            log.warning(
                "stored agent_configs row for %r does not validate (%s); showing the seeded "
                "config, which is what the runtime uses. Run `correct_stale_models` to repair "
                "the row.",
                agent_id,
                exc,
            )
            return defaults[agent_id]
    if agent_id not in defaults:
        raise AgentConfigError(f"no agent {agent_id!r}")
    return defaults[agent_id]


async def agent_view(
    agent_id: str, *, backend: DbBackend | None = None
) -> dict[str, Any]:
    """The right-hand panel of `docs/06` §6: name, purpose, resolved prompt, model, versions.

    The prompt shown is the **resolved** one and its hash is the hash of that resolved text, which
    is what a run records (I11). Showing the unresolved `file:` reference would let two different
    prompts display identically.
    """
    from twinlab.agents.registry import resolve_prompt

    cfg = await load_agent(agent_id, backend=backend)
    resolved, digest = resolve_prompt(cfg)
    force = in_force(agent_id)
    return {
        "agent_id": cfg.agent_id,
        "name": cfg.name,
        "role": cfg.role,
        "enabled": cfg.enabled,
        "prompt": resolved,
        "prompt_hash": digest,
        "provider": cfg.model.provider,
        "model_name": cfg.model.name,
        "temperature": cfg.model.temperature,
        "output_mode": cfg.output_mode,
        "version": cfg.version,
        "frozen": cfg.frozen,
        # docs/06 §6: show each agent's ACTUAL model usage from its config, never a fixed badge.
        # The prototype's `rules only` / `uses AI` labels described the prototype, not this.
        "uses_model": bool(cfg.model.name),
        # `ARCHITECTURE_UPDATE.md` §5.5 item 3. The three boxes above are the **stored row**; these
        # are what the agent is actually run with. They are not always the same thing, and a screen
        # that shows a number the runtime discards is worse than one that shows nothing.
        "in_force": force,
        "in_force_differs": (
            force["provider"] != cfg.model.provider
            or force["model_name"] != cfg.model.name
            or abs(float(force["temperature"]) - float(cfg.model.temperature)) > 1e-9
        ),
        # WP-8 item 5. The twin's temperature is owned by `app_config['twin']` (Twin Lab →
        # Settings), because that is what a session freezes onto its `config` column and what
        # validity test 8 sets. The box is therefore read-only on this screen and carries the
        # sentence saying why — the state that must not survive is a control showing a number the
        # runtime silently discards.
        "temperature_read_only": cfg.agent_id == "twin",
        "temperature_note": (
            "The twin's temperature is set in Twin Lab → Settings, because it is frozen onto "
            "every session and is the subject of validity test 8."
            if cfg.agent_id == "twin"
            else ""
        ),
        # WP-8 item 4. The Checker's switch is removed rather than shown and refused on save.
        "can_disable": cfg.agent_id not in UNDISABLEABLE,
        "cannot_disable_reason": UNDISABLEABLE.get(cfg.agent_id, ""),
        # WP-8 item 7. "saved version 4 · in force since …" needs the version actually running.
        "live_version": force.get("version"),
    }


def in_force(agent_id: str) -> dict[str, Any]:
    """What this agent is **actually run with**, and where each value comes from.

    **Rewritten in M19 WP-8.** Until then this function existed to report a gap: Agent Studio
    showed the Twin Interviewer on *Mistral / mistral-small-latest / temperature 1* from a stale
    `agent_configs` row, while the twin ran on `gpt-oss:120b` at 0.25, because every call site
    constructed its agent from `config/agents.default.yaml` and the stored row was read by nothing
    but Agent Studio. The gap is now closed — `registry.live_agent_configs` merges the stored row
    over the seed and the five runtime call sites read it — so this reports the live config rather
    than explaining why the screen disagrees with it.

    One value still comes from somewhere else, deliberately:

    * **The twin's temperature comes from `app_config['twin']`** (Twin Lab → Settings), via
      `twin_runtime.twin_agent_config`, because that is the value a session freezes onto its
      `config` column and reports with its results (`docs/09` §4), and because it is the live
      subject of validity test 8. One value, one place: Agent Studio's twin temperature box is
      read-only and says so, rather than showing a number that is silently discarded (WP-8 item
      5).

    Everything else — model, provider, prompt, output mode, retry policy, `enabled` — is the
    stored row when there is one and the seed otherwise.
    """
    from twinlab.agents.registry import (
        default_agent_configs,
        live_agent_configs,
        live_agent_versions,
    )
    from twinlab.services.config import load_twin_config

    live = live_agent_configs().get(agent_id)
    if live is None:
        return {
            "provider": "",
            "model_name": "",
            "temperature": 0.0,
            "enabled": False,
            "version": None,
            "source": f"no config for {agent_id!r}",
        }

    from twinlab.agents.registry import resolve_prompt

    versions = live_agent_versions()
    stored_version = versions.get(agent_id)
    seeded = default_agent_configs().get(agent_id)
    # The **resolved** text is compared, not the reference. The seed says `file:twin_v1.md` and a
    # saved row holds the text itself, so comparing references would call an unchanged prompt
    # "different" the moment it was saved.
    prompt_differs = seeded is not None and resolve_prompt(seeded)[0] != resolve_prompt(live)[0]
    # Which file or row each value came from, as a sentence a researcher can act on. The honest
    # distinction is "a stored row won" versus "nothing is stored, so the seed is running".
    if stored_version is not None:
        source = f"agent_configs v{stored_version} (Agent Studio)"
    else:
        source = "config/agents.default.yaml (nothing saved in Agent Studio yet)"

    temperature = float(live.model.temperature)
    if agent_id == "twin":
        temperature = float(load_twin_config().temperature)
        source = (
            f"{source} for the model and prompt; app_config['twin'] "
            "(Twin Lab → Settings) for the temperature"
        )
    return {
        "provider": live.model.provider,
        "model_name": live.model.name,
        "temperature": temperature,
        "enabled": live.enabled,
        "version": stored_version,
        #: True when a stored row is being used and it differs from the seed — which is the state
        #: a researcher most needs to see, because it means "this is not the shipped default".
        "differs_from_seed": bool(
            seeded is not None
            and (
                seeded.model.name != live.model.name
                or seeded.model.provider != live.model.provider
                or prompt_differs
                or seeded.output_mode != live.output_mode
                or seeded.enabled != live.enabled
            )
        ),
        "source": source,
    }


def changed_fields(before: AgentConfig, after: AgentConfig) -> list[str]:
    """Which fields a save actually altered. Written to `agent_config_history.changed_fields`.

    Computed by comparison rather than taken from the caller: a history row that recorded what the
    UI *meant* to change, rather than what changed, would make the audit trail unfalsifiable.
    """
    old, new = before.model_dump(), after.model_dump()
    return sorted(k for k in new if old.get(k) != new.get(k))


# ------------------------------------------------------------------ writing


async def _append_history(
    db: DbBackend,
    *,
    agent_id: str,
    version: int,
    snapshot: dict,
    fields: list[str],
    action: str,
    actor: str | None = None,
) -> None:
    """One append-only audit row. `docs/06` §6's *What was changed* log reads this."""
    if action not in ACTIONS:
        raise AgentConfigError(f"unknown history action {action!r}; expected one of {ACTIONS}")
    await db.insert(
        "agent_config_history",
        [{
            "agent_id": agent_id,
            "version": version,
            "snapshot": snapshot,
            "changed_fields": fields,
            "action": action,
            "actor": actor,
        }],
    )


async def _refuse_if_frozen_and_running(
    cfg: AgentConfig, db: DbBackend, *, what: str
) -> None:
    """`docs/06` §6. A frozen agent is editable only while nothing is running."""
    if not cfg.frozen:
        return
    running = await db.select("sessions", [("eq", "status", "running")], limit=1)
    if running:
        raise AgentFrozen(
            f"{cfg.agent_id} is frozen and session {running[0]['session_id']} is running, so "
            f"{what} is refused. Editing an agent underneath a live session splits one sweep "
            "across two sets of instructions with nothing in the data to show it (docs/06 §6)."
        )


async def save_agent(
    agent_id: str,
    changes: dict[str, Any],
    *,
    actor: str | None = None,
    backend: DbBackend | None = None,
) -> AgentConfig:
    """Save an edit, bump the version and append a `saved` history row. `docs/06` §6.

    Validated through :class:`AgentConfig` and `validate_config`, so `native` output, an
    out-of-allow-list tool or a prompt missing its six-section skeleton is refused here rather
    than at the next run (`docs/02` §2, I13).
    """
    from twinlab.agents.registry import resolve_prompt, validate_config

    db = backend or get_backend()
    before = await load_agent(agent_id, backend=db)
    await _refuse_if_frozen_and_running(before, db, what="saving")

    merged = before.model_dump()
    # `model` is merged field-by-field rather than replaced. A caller that sends three of
    # `ModelRef`'s five fields means "change these three", but a wholesale replacement would hand
    # the other two to `ModelRef`'s defaults — silently resetting a stored `max_tokens` to 2048 and
    # a stored `seed` to `None`. Nobody asked for that, and a reset seed is a provenance loss (I11).
    # It is also what lets Agent Studio omit the twin's temperature and have the row keep its own.
    changes = dict(changes)
    if isinstance(changes.get("model"), dict):
        changes["model"] = {**merged["model"], **changes["model"]}
    merged.update(changes)
    merged["version"] = before.version + 1
    after = validate_config(AgentConfig(**merged), require_schema=False)
    # WP-8 item 4. `enabled` gates the runtime from M19, so switching an agent off is now a real
    # action with a real consequence — and for one agent the consequence is not permitted.
    if not after.enabled and agent_id in UNDISABLEABLE:
        raise AgentConfigError(UNDISABLEABLE[agent_id])
    # The skeleton is checked **here**, not left to the next run. `live_agent_configs` falls back
    # to the seed for an agent whose row does not validate, so a prompt missing a section would be
    # saved with "Saved." and then silently ignored by every session: the screen would say one
    # thing and the study would run another. Refused at save, the researcher sees why.
    resolve_prompt(after)

    fields = [f for f in changed_fields(before, after) if f != "version"]
    await db.upsert("agent_configs", [_row(after)], on_conflict="agent_id")
    await _append_history(
        db,
        agent_id=agent_id,
        version=after.version,
        snapshot=after.model_dump(),
        fields=fields,
        action="saved",
        actor=actor,
    )
    # Installed into this process now, not at the next session. The Test buttons and the Studio
    # read the live config, so a save they cannot see would make the screen lie until a restart.
    await refresh_agent_configs(db)
    return after


async def restore_agent(
    agent_id: str, *, actor: str | None = None, backend: DbBackend | None = None
) -> AgentConfig:
    """*Put the original text back* — restore the seeded default. `docs/06` §6.

    Writes its **own** history row with action ``restored``. A restore is an edit like any other:
    the previous configuration is not deleted, and the row says which fields moved.
    """
    from twinlab.agents.registry import default_agent_configs

    db = backend or get_backend()
    before = await load_agent(agent_id, backend=db)
    await _refuse_if_frozen_and_running(before, db, what="restoring")

    defaults = default_agent_configs()
    if agent_id not in defaults:
        raise AgentConfigError(f"no seeded default for {agent_id!r}")

    original = defaults[agent_id]
    after = original.model_copy(
        update={"version": before.version + 1, "frozen": before.frozen}
    )
    fields = [f for f in changed_fields(before, after) if f != "version"]
    await db.upsert("agent_configs", [_row(after)], on_conflict="agent_id")
    await _append_history(
        db,
        agent_id=agent_id,
        version=after.version,
        snapshot=after.model_dump(),
        fields=fields,
        action="restored",
        actor=actor,
    )
    await refresh_agent_configs(db)
    return after


async def set_frozen(
    agent_id: str,
    frozen: bool,
    *,
    actor: str | None = None,
    backend: DbBackend | None = None,
) -> AgentConfig:
    """*Freeze for the main study*, or lift it. Appends its **own** history row. `docs/06` §6."""
    db = backend or get_backend()
    before = await load_agent(agent_id, backend=db)
    if before.frozen and not frozen:
        # Unfreezing is itself an edit to a frozen agent.
        await _refuse_if_frozen_and_running(before, db, what="unfreezing")

    after = before.model_copy(update={"frozen": frozen, "version": before.version + 1})
    await db.upsert("agent_configs", [_row(after)], on_conflict="agent_id")
    await _append_history(
        db,
        agent_id=agent_id,
        version=after.version,
        snapshot=after.model_dump(),
        fields=["frozen"],
        action="frozen" if frozen else "unfrozen",
        actor=actor,
    )
    await refresh_agent_configs(db)
    return after


async def correct_stale_models(
    *, actor: str = "seed-correction", backend: DbBackend | None = None
) -> list[dict[str, Any]]:
    """Reset any stored `agent_configs` row whose model disagrees with the seed. §5.5 items 1–2.

    `ARCHITECTURE_UPDATE.md` §1.2, confirmed by the researcher: *"no its gpt oss only"*. Agent
    Studio showed the Twin Interviewer on **Mistral / `mistral-small-latest` / temperature 1**, last
    saved 2026-09-25. That row is not merely against the researcher's intent, it is **invalid
    against
    the code**: `ModelRef.provider` is ``Literal["ollama", "openai", "mock"]`` and there is no
    `mistral` provider in the model at all, so `load_agent` would raise constructing it.

    Reproducible, and not a hand-edit in the UI: each correction goes through
    :func:`restore_agent`, so it resets the row to `config/agents.default.yaml` — which already says
    `gpt-oss:120b` and `ollama` for all five agents — bumps the version and **appends an
    `agent_config_history` row** saying what moved. A hand-edit would leave the same data with no
    audit trail.

    Rows are read raw rather than through `load_agent`, precisely because an invalid stored row is
    the case this exists to repair and must not be unrepairable by its own invalidity.

    Returns one entry per agent it touched, or an empty list when nothing was stale.
    """
    from twinlab.agents.registry import default_agent_configs

    db = backend or get_backend()
    seeds = default_agent_configs()
    rows = {str(r["agent_id"]): r for r in await db.select("agent_configs", None)}
    corrected: list[dict[str, Any]] = []
    for agent_id, seed in seeds.items():
        row = rows.get(agent_id)
        stored = dict((row or {}).get("model") or {})
        if row is None:
            continue
        was = {
            "provider": stored.get("provider"),
            "name": stored.get("name"),
            "temperature": stored.get("temperature"),
        }
        if was["provider"] == seed.model.provider and was["name"] == seed.model.name:
            continue
        if row.get("frozen"):
            # A frozen agent is not quietly rewritten. Freezing is what makes a sweep's
            # configuration stable, and a correction that bypassed it would be the one edit nobody
            # could see (`docs/06` §6).
            corrected.append(
                {"agent_id": agent_id, "was": was, "now": None, "skipped": "frozen"}
            )
            continue
        # Written directly from the seed rather than through `restore_agent`, because
        # `restore_agent` goes via `load_agent`, which constructs an `AgentConfig` from the stored
        # row — and the `mistral` row is invalid against `ModelRef.provider`, so loading it raises.
        # A repair that the damage prevents is not a repair.
        after = seed.model_copy(
            update={
                "version": int(row.get("version") or 0) + 1,
                "frozen": False,
                "enabled": bool(row.get("enabled", seed.enabled)),
            }
        )
        await db.upsert("agent_configs", [_row(after)], on_conflict="agent_id")
        await _append_history(
            db,
            agent_id=agent_id,
            version=after.version,
            snapshot=after.model_dump(),
            fields=["model"],
            action="restored",
            actor=actor,
        )
        corrected.append(
            {
                "agent_id": agent_id,
                "was": was,
                "now": {
                    "provider": after.model.provider,
                    "name": after.model.name,
                    "temperature": after.model.temperature,
                },
                "skipped": "",
            }
        )
    return corrected


def _row(cfg: AgentConfig) -> dict:
    """`AgentConfig` as an `agent_configs` row."""
    return {
        "agent_id": cfg.agent_id,
        "name": cfg.name,
        "role": cfg.role,
        "enabled": cfg.enabled,
        "model": cfg.model.model_dump(),
        "system_prompt": cfg.system_prompt,
        "instructions": list(cfg.instructions),
        "input_schema": cfg.input_schema,
        "output_schema": cfg.output_schema,
        "output_mode": cfg.output_mode,
        "tools": list(cfg.tools),
        "context_sources": [c.model_dump() for c in cfg.context_sources],
        "react": cfg.react,
        "retry": cfg.retry.model_dump(),
        "version": cfg.version,
        "frozen": cfg.frozen,
    }


async def save_rules(
    *,
    checker: dict[str, float],
    weights: dict[str, float],
    actor: str | None = None,
    backend: DbBackend | None = None,
) -> int:
    """*Save rules* — a new `app_config` version, recorded on every subsequent run.

    **Historical runs are untouched** (`docs/06` §6). A run stores the config version it ran
    under, so raising the version here cannot retroactively change what an existing result was
    produced by.
    """
    from twinlab.services.lab import save_settings

    unknown = sorted(set(weights) - set(WEIGHT_METRICS))
    if unknown:
        raise AgentConfigError(
            f"unknown index weight(s) {unknown}; the six metrics are {list(WEIGHT_METRICS)}"
        )
    negative = sorted(k for k, v in weights.items() if v < 0)
    if negative:
        raise AgentConfigError(
            f"negative index weight for {negative}. A negative weight inverts a metric's "
            "meaning; the sign flip belongs to constructs.index_sign (docs/07 §4.1)."
        )

    db = backend or get_backend()
    payload = {"checker": dict(checker), "weights": dict(weights)}
    version = await save_settings("rules", payload, backend=db)
    await _append_history(
        db,
        agent_id=RULES_KEY,
        version=version,
        snapshot=payload,
        fields=sorted(payload),
        action="saved",
        actor=actor,
    )
    return version


async def history(
    agent_id: str | None = None, *, backend: DbBackend | None = None
) -> list[dict]:
    """*What was changed* — append-only, newest first. `docs/06` §6."""
    db = backend or get_backend()
    filters = [("eq", "agent_id", agent_id)] if agent_id else None
    return await db.select("agent_config_history", filters, order=("history_id", True))


# ------------------------------------------------------------------ the plan


#: Agent Studio's model-calling tests, by job id. A test is a model call, and CLAUDE.md rule 12
#: keeps a model call off a Gradio handler's synchronous path, so each one runs as a background task
#: and the screen reads the finished result back. The job holds its task, as `studio._RENDERS` does:
#: asyncio keeps only a weak reference to a running task.
_TEST_JOBS: dict[str, dict[str, Any]] = {}


def _refuse_sham(version_code: str) -> None:
    """The three tests take a real version code. SHAM has five briefs of its own and no dial row."""
    from twinlab.orchestrator.odometer import SHAM_CODE, validate_code

    validate_code(version_code)
    if version_code == SHAM_CODE:
        raise AgentConfigError(
            "SHAM has its own five briefs and no dial board row, so this test does not take it. "
            "Test a real version code."
        )


def _with_prompt(cfg: AgentConfig, prompt_text: str | None) -> AgentConfig:
    """The live config, with the prompt in the box swapped in when it was edited.

    The swap is held to the same six-section skeleton as a saved prompt, so an edit that a save
    would refuse is refused here too, rather than tested under a prompt no run would ever use.
    """
    from twinlab.agents.registry import resolve_prompt

    edited = (prompt_text or "").strip()
    if not edited or edited == resolve_prompt(cfg)[0].strip():
        return cfg
    swapped = cfg.model_copy(update={"system_prompt": edited})
    resolve_prompt(swapped)
    return swapped


def start_agent_test(
    agent_id: str,
    *,
    twin_id: str | None,
    version_code: str,
    prompt_text: str,
) -> str:
    """Start one model-calling test in the background and return its job id. CLAUDE.md rule 12."""
    job_id = uuid.uuid4().hex
    _TEST_JOBS[job_id] = {"agent_id": agent_id, "status": "running", "view": None}
    task = asyncio.create_task(
        _run_test(job_id, agent_id, twin_id, version_code, prompt_text)
    )
    _TEST_JOBS[job_id]["task"] = task
    return job_id


async def _run_test(
    job_id: str,
    agent_id: str,
    twin_id: str | None,
    version_code: str,
    prompt_text: str,
) -> None:
    job = _TEST_JOBS[job_id]
    try:
        if agent_id == "twin":
            if not twin_id:
                raise AgentConfigError("No twin selected.")
            view = await twin_test_view(twin_id, version_code, edited_prompt=prompt_text)
        elif agent_id == "design":
            view = await design_test_view(version_code, prompt_text=prompt_text)
        else:
            raise AgentConfigError(f"{agent_id} has no model test on this screen")
    except Exception as exc:  # noqa: BLE001 — a failed test is a result the screen names, not a crash
        log.warning("agent test for %s failed: %r", agent_id, exc)
        job.update(status="failed", view={"error": f"{type(exc).__name__}: {exc}"[:400]})
        return
    job.update(status="done", view=view)


def agent_test_result(job_id: str) -> dict[str, Any]:
    """The state of one test job: ``running``, ``done``, ``failed``, or ``unknown``."""
    job = _TEST_JOBS.get(job_id)
    if job is None:
        return {"status": "unknown", "agent_id": None, "view": None}
    return {"status": job["status"], "agent_id": job["agent_id"], "view": job["view"]}


async def checker_test_view(
    version_code: str, *, backend: DbBackend | None = None
) -> dict[str, Any]:
    """Agent Studio's *Quality Checker* view: the codebook policy beside the design agent's framing.

    Reads only. No model is called and nothing is judged here. Each area shows the commitments the
    codebook says this version carries (`variant/lookup`), beside the paragraph the design agent
    actually rendered for that area (the stored render). Whether the Checker passed the render is
    recorded on the render itself and is not restated on this screen.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.models.reference import LEVER_BY_POSITION
    from twinlab.orchestrator.odometer import dials
    from twinlab.services.dials import dial_board
    from twinlab.variant.lookup import commitments_for_lever, lookup

    _refuse_sham(version_code)
    db = backend or get_backend()
    out: dict[str, Any] = {"version_code": version_code, "rendered": False, "rows": []}
    row = await VariantRepo(db).get(version_code, settings.style_version)
    if row is None:
        return out
    out["rendered"] = True

    stored = dict(row.get("paragraphs") or {})
    spec = lookup(version_code, reference())
    per_lever = dials(version_code)
    names = {lever.lever: lever.lever_name for lever in dial_board(version_code).told}

    rows: list[dict[str, Any]] = []
    for lever in LEVER_BY_POSITION:
        if per_lever[lever] == 0:
            rows.append(
                {"lever": names[lever], "policy": [], "framed": "", "status": "fixed", "reason": ""}
            )
            continue
        entry = stored.get(lever)
        if isinstance(entry, dict):
            text = str(entry.get("text", ""))
            status = str(entry.get("status", "ok"))
            reason = str(entry.get("reason", ""))
        else:
            text, status, reason = str(entry or ""), "ok", ""
        rows.append(
            {
                "lever": names[lever],
                "policy": [c for _, c in sorted(commitments_for_lever(spec, lever).items())],
                "framed": text,
                "status": status,
                "reason": reason,
            }
        )
    out["rows"] = rows
    return out


async def twin_test_view(
    twin_id: str,
    version_code: str,
    *,
    edited_prompt: str | None = None,
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """Agent Studio's *Twin Interviewer* view: what the driver said, and what the twin said.

    Always these two columns for this twin and this version, whatever the prompt box holds. The
    twin is asked once, with the prompt in the box (the saved one when nothing was edited), against
    the stored, Checker-passed variant for ``version_code``. The driver's answers are the twin's
    baseline, and are shown beside its answers so the two can be read against each other.

    There is no path here that renders a variant: an unverified variant never reaches a twin (I3),
    including on a test screen. `services/studio.start_render` is where a variant is produced.
    """
    from twinlab.agents.registry import resolve_prompt
    from twinlab.ingest.reference_store import reference
    from twinlab.models.reference import LEVER_BY_POSITION
    from twinlab.services.twin_runtime import (
        ask_items,
        battery_for,
        driver_answers,
        round_seed,
    )

    db = backend or get_backend()
    ref = reference()
    driver = await driver_answers(twin_id, db)
    out: dict[str, Any] = {
        "twin_id": twin_id,
        "version_code": version_code,
        "items": [
            {
                "item_id": i,
                "question": ref.items[i].stem,
                "points": ref.scale_points(i),
                "driver": driver.get(i),
                "twin": None,
            }
            for i in ref.battery_item_ids
        ],
        "twin_checked": False,
        "note": "",
    }

    # The prompt in the box, or the saved one when the box is empty. Both are the same text when
    # nothing was edited, so the two columns never change shape with the prompt.
    saved = await load_agent("twin", backend=db)
    prompt = (edited_prompt or "").strip() or resolve_prompt(saved)[0].strip()

    stored_row = await VariantRepo(db).get(version_code, settings.style_version)
    if stored_row is None:
        out["note"] = (
            f"{version_code} has never been rendered, so there is no verified stimulus to put a "
            "prompt to. Render it in Twin Studio, or ask the twins for it on the Dial board."
        )
        return out
    if not (dict(stored_row.get("checker") or {})).get("passed"):
        out["note"] = f"{version_code} did not pass the Checker, so it must not reach a twin (I3)."
        return out

    stored = dict(stored_row.get("paragraphs") or {})
    paragraphs = {}
    for lever in LEVER_BY_POSITION:
        entry = stored.get(lever)
        paragraphs[lever] = entry.get("text", "") if isinstance(entry, dict) else str(entry or "")

    from twinlab.services.config import load_twin_config

    try:
        answers, _telemetry = await ask_items(
            twin_id=twin_id,
            paragraphs=paragraphs,
            items=battery_for(ref),
            baseline=driver,
            seed=round_seed("agent-studio", twin_id, version_code),
            # Live config, not hard-coded (`docs/DECISIONS.md`, 2026-10-07): this preview must run
            # under the same elicitation the sweep actually uses, or it previews an instrument the
            # study is not running — the "Driver said" column still shows `driver` for comparison
            # either way, independent of whether the model itself was shown it.
            show_baseline=load_twin_config().show_baseline,
            version_code=version_code,
            system_prompt=prompt,
            backend=db,
        )
    except Exception as exc:  # noqa: BLE001 — a failed twin is a note on the screen, not a dead screen
        # False means the twin did not produce a valid answer set after its one targeted repair.
        # Its column stays *Not tested*: a failed answer is never coerced into a number (I13).
        out["note"] = f"The twin did not give a valid answer: {type(exc).__name__}: {exc}"[:400]
        return out

    for item in out["items"]:
        item["twin"] = answers.get(item["item_id"])
    out["twin_checked"] = True
    return out


async def design_test_view(
    version_code: str, *, prompt_text: str | None = None, backend: DbBackend | None = None
) -> dict[str, Any]:
    """Agent Studio's *Policy Designer* view: what the design agent writes for this version now.

    Runs the design agent once per lever, with the prompt in the box when it was edited, on the
    same brief the render path builds (`variant/render.build_brief`). It shows the paragraph and
    whether it came back as a paragraph or a refusal.

    **It writes nothing.** The paragraphs are not stored in the render cache, so a test cannot
    change what a twin is shown (I4). A paragraph already in the cache keeps its text: see the
    decision log on the design prompt and the cache.
    """
    from twinlab.agents.registry import get_client, live_agent
    from twinlab.ingest.reference_store import reference
    from twinlab.models.reference import LEVER_BY_POSITION
    from twinlab.orchestrator.odometer import dials
    from twinlab.services.dials import dial_board
    from twinlab.variant.lookup import lookup
    from twinlab.variant.render import band_for, build_brief, load_style_contract, run_design

    _refuse_sham(version_code)
    cfg = _with_prompt(live_agent("design"), prompt_text)
    ref = reference()
    style = load_style_contract()
    spec = lookup(version_code, ref)
    per_lever = dials(version_code)
    names = {lever.lever: lever.lever_name for lever in dial_board(version_code).told}
    client = get_client()

    rows: list[dict[str, Any]] = []
    for lever in LEVER_BY_POSITION:
        if per_lever[lever] == 0:
            rows.append(
                {"lever": names[lever], "dial": 0, "text": "", "status": "fixed",
                 "reason": "Dial 0 is the fixed text, which is never generated (I5).",
                 "words": None, "band": None}
            )
            continue
        brief = build_brief(spec, lever, ref, style)
        paragraph = await run_design(cfg, brief, client)
        low, high = band_for(len(brief.commitments), style)
        rows.append(
            {"lever": names[lever], "dial": per_lever[lever], "text": paragraph.text,
             "status": paragraph.status, "reason": paragraph.reason,
             "words": len(paragraph.text.split()), "band": [low, high]}
        )
    return {"version_code": version_code, "rows": rows}


def _next_versions(
    version_code: str,
    *,
    advance: Any,
    code_from_index: Any,
    index_from_code: Any,
    control: str,
    how_many: int = 6,
) -> list[tuple[str, str]]:
    """The next codes the sweep would walk, each with the reason. §5.2 item 3.

    **Read-only, and it is the odometer, not a sampler.** Six is not a sampling scheme the
    orchestrator knows about (`CLAUDE.md` rule 9); a six-version session is 243's loop stopped after
    six, so "what it would test next" is just the next six odometer positions from here. Saying so
    in the `Why` column is the point — a reader who thinks the agent *chose* these has misunderstood
    the design.

    Pure. Its collaborators are injected so it is testable without importing the orchestrator, and
    so
    this function cannot quietly grow a database read.
    """
    out: list[tuple[str, str]] = []
    index = index_from_code(version_code)
    seen = {version_code}
    while len(out) < how_many:
        index = advance(index)
        code = code_from_index(index)
        if code in seen:
            break
        seen.add(code)
        if code == control:
            # Skipped as a *next version*, and said rather than silently dropped: `00000` does run,
            # first, as the control every shift is measured against (`docs/03` §6.1).
            out.append((code, "Uber today — the control, run first and not as a test."))
            continue
        lit = sum(1 for d in code if d != "0")
        if lit == 1:
            why = "Test one dial on its own first."
        elif lit == 2:
            why = "Two dials together — the cheapest interaction the design admits."
        else:
            why = f"{lit} dials together, Fairwork score {sum(int(d) for d in code)}."
        out.append((code, why))
    return out


async def manager_plan(
    version_code: str, *, backend: DbBackend | None = None
) -> list[StatusRow]:
    """Run Manager's test: **a deterministic plan. It starts nothing.** `docs/06` §6.

    Every number is read or arithmetic over settings. No session is created, no task is scheduled
    and no model is called — the M11 acceptance test asserts the `sessions` table is unchanged
    across this call.
    """
    from config.settings import settings
    from twinlab.orchestrator import budget as budget_calc
    from twinlab.services.config import load_twin_config
    from twinlab.services.runs import budget_view

    db = backend or get_backend()
    cfg = load_twin_config()

    twins = await db.count("twins")
    kept = await db.count(
        "twin_quality_runs",
        [("eq", "is_latest", True), ("eq", "holdout_set", "H3"), ("eq", "kept", True)],
    )
    panel = min(settings.panel_size, kept) if kept else settings.panel_size
    view = budget_view(budget_calc.ask_budget(panel_size=panel))
    agent = await load_agent("twin", backend=db)

    return [
        StatusRow(label="Version", value=version_code),
        StatusRow(label="Twins in Supabase", value=str(twins)),
        StatusRow(label="Twins kept by the quality test", value=f"{kept} of {twins}"),
        StatusRow(label="Wordings", value=str(1)),
        StatusRow(label="Runs per wording", value=str(1)),
        StatusRow(label="AI calls for this version", value=str(view.calls)),
        StatusRow(label="Calls at once", value=str(settings.max_concurrency)),
        StatusRow(label="Pause between calls", value=f"{getattr(settings, 'call_pause', 0)} s"),
        StatusRow(label="Estimated time", value=view.est_hours_text),
        StatusRow(label="Model", value=agent.model.name),
        StatusRow(label="Temperature", value=str(cfg.temperature)),
    ]


def manager_log_preview(version_code: str) -> list[StatusRow]:
    """*What it would write to the log* — five preview lines, one per agent. §5.4.

    The whole point of screenshot 7 is that it is a **dry run**: it shows the shape of the log a
    sweep would produce without producing one. So this is a pure function of the version code,
    phrased in the same `stage` vocabulary `run_events` actually uses (`docs/04` §3.2) — a preview
    that invented its own wording would be a preview of nothing.

    It creates no session, schedules no task and makes no model call, exactly as
    :func:`manager_plan` does not.
    """
    return [
        StatusRow(
            label="MANAGER",
            value=(
                f"control — session Ask {version_code}: 00000 and SHAM first, "
                f"then {version_code}"
            ),
        ),
        StatusRow(
            label="DESIGN",
            value=(
                f"render — {version_code}: the lever paragraphs this version needs that are not "
                "already cached"
            ),
        ),
        StatusRow(
            label="CHECKER",
            value=f"check — {version_code}: five gates; a failure re-renders once, then halts",
        ),
        StatusRow(
            label="TWIN",
            value=f"ask — {version_code}: one call per twin on the frozen panel, serial",
        ),
        StatusRow(
            label="ANALYST",
            value=(
                f"analyse — {version_code}: six shifts and the index, computed in Python, then "
                "prose grounded against them"
            ),
        ),
    ]


__all__ = [
    "agent_test_result",
    "checker_test_view",
    "start_agent_test",
    "PROVIDERS",
    "correct_stale_models",
    "in_force",
    "twin_test_view",
    "ACTIONS",
    "CHECKER_RULES",
    "OUTPUT_MODES",
    "RULES_KEY",
    "STUDIO_AGENT_ORDER",
    "WEIGHT_METRICS",
    "AgentConfigError",
    "AgentFrozen",
    "agent_view",
    "changed_fields",
    "design_test_view",
    "manager_log_preview",
    "history",
    "load_agent",
    "manager_plan",
    "restore_agent",
    "save_agent",
    "save_rules",
    "set_frozen",
]
