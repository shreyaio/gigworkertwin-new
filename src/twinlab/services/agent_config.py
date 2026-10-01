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

import logging
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


class AgentConfigError(RuntimeError):
    """Any refusal to change an agent's configuration."""


class AgentFrozen(AgentConfigError):
    """A frozen agent was edited while a session was running. `docs/06` §6.

    Freezing is what makes a sweep's configuration stable. Editing underneath a live session would
    split one sweep across two sets of instructions with nothing in the data to show it.
    """


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
    }


def in_force(agent_id: str) -> dict[str, Any]:
    """What this agent is **actually run with**, and where each value comes from. §5.5 item 3.

    Agent Studio showed the Twin Interviewer on *Mistral / mistral-small-latest / temperature 1*
    from a stale `agent_configs` row, while the twin ran on `gpt-oss:120b` at 0.25. Two separate
    causes, and this function reports both rather than papering over either:

    * **The model and provider come from `config/agents.default.yaml`.** Every agent is constructed
      from `agents/registry.default_agent_configs()` at the call site — `twin_runtime`,
      `variant/render.py`, `variant/checker.py` — so a `agent_configs` row's model is not read by
      the runtime at all. The stored row is the *editable record*; the YAML is what runs.
    * **The twin's temperature comes from `app_config['twin']`**, via
      `twin_runtime.twin_agent_config`, because that is the value a session freezes onto its
      `config` column and reports with its results (`docs/09` §4). It overrides both the row and the
      YAML, and it is the live subject of validity test 8.

    This is deliberately a **report**, not a rewiring. Which file the twin's model is read from is a
    reproducibility property frozen onto every run (I11); changing it mid-study is a research
    decision, not a screen fix. See `docs/DECISIONS.md`, 2026-10-01.
    """
    from twinlab.agents.registry import default_agent_configs
    from twinlab.services.config import load_twin_config

    seeded = default_agent_configs().get(agent_id)
    if seeded is None:
        return {
            "provider": "",
            "model_name": "",
            "temperature": 0.0,
            "source": f"no seeded config for {agent_id!r}",
        }
    source = "config/agents.default.yaml"
    temperature = float(seeded.model.temperature)
    if agent_id == "twin":
        temperature = float(load_twin_config().temperature)
        source = (
            "config/agents.default.yaml for the model; app_config['twin'] (Twin Lab → Settings) "
            "for the temperature"
        )
    return {
        "provider": seeded.model.provider,
        "model_name": seeded.model.name,
        "temperature": temperature,
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
    from twinlab.agents.registry import validate_config

    db = backend or get_backend()
    before = await load_agent(agent_id, backend=db)
    await _refuse_if_frozen_and_running(before, db, what="saving")

    merged = before.model_dump()
    merged.update(changes)
    merged["version"] = before.version + 1
    after = validate_config(AgentConfig(**merged), require_schema=False)

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


async def checker_test_view(
    twin_id: str, *, backend: DbBackend | None = None
) -> dict[str, Any]:
    """Agent Studio's *Quality Checker* view. `docs/06` §6's table. **Reads; never re-runs.**

    Everything here comes off the twin's latest H3 `twin_quality_runs` row and its driver's own
    `survey_answers`. Agent Studio is not the execution engine: re-scoring here would be a second
    verdict beside the stored one, and two disagreeing verdicts is worse than none.

    The completeness and scale checks are the output contract's, restated over what was stored
    (I13): every expected holdout item present, each answer inside **its own** range.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.services.config import load_twin_config
    from twinlab.services.twin_runtime import driver_answers
    from twinlab.services.validity import H2_ANSWERS_KEY

    db = backend or get_backend()
    ref = reference()
    # The live thresholds, so the `must be …` captions below cannot disagree with the gate a twin
    # was actually judged by (§5.3).
    cfg = load_twin_config()
    rows = await db.select(
        "twin_quality_runs",
        [
            ("eq", "twin_id", twin_id),
            ("eq", "is_latest", True),
            ("eq", "holdout_set", "H3"),
        ],
        limit=1,
    )
    if not rows:
        return {"twin_id": twin_id, "has_run": False}

    row = rows[0]
    twin_answers = {
        k: int(v) for k, v in ((row.get("detail") or {}).get(H2_ANSWERS_KEY) or {}).items()
    }
    human = await driver_answers(twin_id, db)
    expected = ref.holdout_h3_item_ids

    missing = [i for i in expected if i not in twin_answers]
    out_of_range = [
        i for i, v in twin_answers.items()
        if i in ref.items and not 1 <= v <= ref.scale_points(i)
    ]
    comparison = [
        {
            "item_id": i,
            "question": ref.items[i].stem,
            "driver": human.get(i),
            "twin": twin_answers.get(i),
            # `None` where either side is absent: an item only one of them answered is not
            # scored, and showing a difference against a blank would invent one (`docs/08` §2.2).
            "error": (
                None if i not in human or i not in twin_answers
                else abs(human[i] - twin_answers[i])
            ),
        }
        for i in expected
    ]
    return {
        "twin_id": twin_id,
        "has_run": True,
        "complete": not missing,
        "missing": missing,
        "in_scale": not out_of_range,
        "out_of_range": out_of_range,
        "mae": None if row.get("mae") is None else float(row["mae"]),
        "pct_within_1": (
            None if row.get("pct_within_1") is None else float(row["pct_within_1"])
        ),
        "items_n": int(row.get("items_n") or 0),
        "repeats": int(row.get("repeats") or 0),
        "kept": row.get("kept"),
        "model": str(row.get("model") or ""),
        "correlations": dict(row.get("correlations") or {}),
        "comparison": comparison,
        # `ARCHITECTURE_UPDATE.md` §5.3: the two threshold rows carry their `must be …` caption, and
        # the caption is the LIVE config rather than a number written into the screen — the gate a
        # twin was judged by is `app_config`'s, and a hard-coded 1.0 beside a changed threshold
        # would
        # be the screen disagreeing with the data.
        #
        # The decision is the **AND** of both (`validity/quality.h3_verdict`, validation-plan D-4),
        # which is stated here so the panel can show the conjunction rather than imply either/or.
        "mae_max": float(cfg.mae_max),
        "pct_within_1_min": float(cfg.pct_within_1_min),
        # Plain prose, no markdown: this is rendered into HTML through `esc`, so `**and**` would
        # appear with its asterisks. The emphasis is carried by the sentence instead.
        "decision_rule": (
            f"Keep only if average error is {cfg.mae_max} or less AND at least "
            f"{cfg.pct_within_1_min * 100:.0f}% of answers are within 1 point. Both, never either."
        ),
    }


async def twin_test_view(
    twin_id: str,
    version_code: str,
    *,
    edited_prompt: str | None = None,
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """Agent Studio's *Twin Interviewer* view. `docs/06` §6, `ARCHITECTURE_UPDATE.md` §5.1.

    Two defects are fixed here, and the second is the one that mattered.

    **The panel was showing its input instead of its result.** Its answers table was headed *"what
    this twin's driver answered"* and listed the baseline — the survey vector the twin is anchored
    on. The screenshot asks for *"Some of the 37 answers it gave"*: the **twin's** output. So the
    twin's answer vector is returned as ``answers`` and the driver's value stays as a second column,
    the way the Checker panel shows the two side by side.

    **The comparison was transposed.** It returned one row per metric with `Saved / Your edit /
    Difference` columns; the screenshot has one row **per instruction variant** — the saved prompt
    and the edit — with ``Answer checked?``, the six metrics and ``A reason it gave``. So each
    variant is now a row carrying its own pass/fail verdict and its own rationale. The verdict is
    the contract/range one `run_answer_ladder` already computes; nothing new is judged here.

    The stimulus is the **stored, Checker-passed variant** for ``version_code``. There is no path
    here that renders one: an unverified variant never reaches a twin (I3), including on a test
    screen. `services/studio.start_render` is where a variant is produced.
    """
    from twinlab.agents.registry import resolve_prompt
    from twinlab.analysis.metrics import score
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
    out: dict[str, Any] = {
        "twin_id": twin_id,
        "version_code": version_code,
        "metrics": list(ref.metrics),
        # One row per instruction variant. Empty until a run happens.
        "variants": [],
        # `item_id → (stem, the twin's answer, the driver's answer)`. The TWIN's answers are the
        # subject; the driver's is the comparison column.
        "answers": [],
        "note": "",
    }

    baseline = await driver_answers(twin_id, db)
    # Rendered before any model call, so the table is populated even when the test cannot run — and
    # so a twin with no driver (a hand-built one) shows an EMPTY column rather than zeros (I17,
    # §4.5).
    out["answers"] = [
        {
            "item_id": i,
            "question": ref.items[i].stem,
            "twin": None,
            "driver": baseline.get(i),
        }
        for i in ref.battery_item_ids
    ]

    saved = await load_agent("twin", backend=db)
    edited = (edited_prompt or "").strip()
    # Compared against the **resolved** prompt, which is what the textarea holds. `system_prompt` is
    # the unresolved `file:twin.md` reference, so comparing against it meant an untouched box always
    # looked edited — and the panel would run the same prompt twice and present it as a comparison.
    saved_resolved, _ = resolve_prompt(saved)
    saved_text = saved_resolved.strip()
    # Both prompts are run when they differ; only the saved one when they do not. Either way the
    # twin IS asked, which is what makes this a test of the agent rather than a view of its input.
    prompts: dict[str, str] = {"saved": saved_resolved}
    if edited and edited != saved_text:
        prompts["your edit"] = edited
    else:
        out["note"] = (
            "The prompt in the box is the saved one, so there is one row below rather than two. "
            "Edit it above and press Test this agent to run the same twin on both."
        )

    _row_ = await VariantRepo(db).get(version_code, settings.style_version)
    if _row_ is None:
        out["note"] = (
            f"{version_code} has never been rendered, so there is no verified stimulus to put a "
            "prompt to. Render it in Twin Studio, or ask the twins for it on the Dial board."
        )
        return out
    if not (dict(_row_.get("checker") or {})).get("passed"):
        out["note"] = (
            f"{version_code} did not pass the Checker, so it must not reach a twin (I3)."
        )
        return out

    stored = dict(_row_.get("paragraphs") or {})
    paragraphs = {}
    for lever in LEVER_BY_POSITION:
        entry = stored.get(lever)
        paragraphs[lever] = entry.get("text", "") if isinstance(entry, dict) else str(entry or "")

    complete_baseline = all(i in baseline for i in ref.battery_item_ids)
    first: dict[str, int] | None = None
    for which, prompt_text in prompts.items():
        row: dict[str, Any] = {
            "which": which,
            # The contract/range verdict the ladder computed, as a pass/fail — the screenshot's
            # `Answer checked?` column. False means the twin did not produce 37 valid integers after
            # its one targeted repair, which is a real failure and never coerced into a pass.
            "checked": False,
            "reason": "",
            "scores": {},
            "retries": None,
        }
        try:
            answers, telemetry = await ask_items(
                twin_id=twin_id,
                paragraphs=paragraphs,
                items=battery_for(ref),
                baseline=baseline,
                seed=round_seed("agent-studio", twin_id, version_code),
                show_baseline=True,
                version_code=version_code,
                system_prompt=prompt_text,
                backend=db,
            )
        except Exception as exc:  # noqa: BLE001 — a failed variant is a ROW, not a dead screen
            # Deliberately not an early return. The saved prompt failing and the edit succeeding is
            # exactly the comparison this screen exists to show, and bailing out hid it.
            row["reason"] = f"{type(exc).__name__}: {exc}"[:300]
            out["variants"].append(row)
            continue

        row["checked"] = True
        row["reason"] = str(telemetry.get("rationale") or "")
        row["retries"] = telemetry.get("retries")
        row["scores"] = {m: round(score(answers, m, ref), 2) for m in ref.metrics}
        if first is None:
            first = answers
        out["variants"].append(row)

    if first is not None:
        for entry in out["answers"]:
            entry["twin"] = first.get(entry["item_id"])
    # The driver's six scores, for the row the table puts underneath. `None` when the driver left
    # part of the battery blank: a metric is never computed over a subset (`docs/07` §2.3).
    out["driver_scores"] = (
        {m: round(score(baseline, m, ref), 2) for m in ref.metrics}
        if complete_baseline
        else {}
    )
    if not out["note"]:
        out["note"] = (
            "Same twin, same cell, one call per prompt. This is a test of one agent and writes "
            "nothing — it is not a run and does not appear in Results."
        )
    return out


async def design_test_view(
    version_code: str, *, backend: DbBackend | None = None
) -> dict[str, Any]:
    """Agent Studio's *Policy Designer* view. `docs/06` §6, `ARCHITECTURE_UPDATE.md` §5.2.

    Three things the panel got wrong, and this is where each is fixed.

    1. **`Text used` showed the wrong string.** It joined `lever.bullets`, which is `told_summary` —
       the **researcher-facing** bullet list that `variant/lookup.py` is explicit *a twin never
       sees*. The screenshot's column holds the **rendered paragraph** ("You can now reach a human
       representative and appeal low ratings…"). Showing the bullets there is not a cosmetic slip:
       it makes the two artefacts look interchangeable on the one screen whose job is to show what
       the design agent produced, and `docs/03` §4.3 keeps them apart on purpose. Both are returned
       now, in separate columns.
    2. **Both wordings.** Wording is a real experimental factor (validity test 5), so the paragraphs
       are returned per wording — ``A`` as rendered, ``B`` as the same five paragraphs in reverse
       order, which is exactly what `twin_runtime.ask_items(reverse_order=True)` shows a twin. It is
       derived from the stored paragraphs, never re-rendered: `docs/09` §2 says what the twins saw
       is what is shown.
    3. **Versions it would test next.** A `Version | Why` table, from the odometer — read-only, and
       it starts nothing.
    """
    from twinlab.orchestrator.odometer import (
        CONTROL_CODE,
        advance,
        code_from_index,
        index_from_code,
    )
    from twinlab.services.dials import dial_board
    from twinlab.services.lab import scenario_paragraphs

    db = backend or get_backend()
    board = dial_board(version_code)
    rendered = await scenario_paragraphs(version_code, backend=db)

    # Positional, because `scenario_paragraphs` returns the five paragraphs in lever order and
    # `board.told` is in the same order. A lever with no rendered paragraph gets an empty string
    # rather than a neighbour's text.
    levers: list[dict[str, Any]] = []
    for position, lever in enumerate(board.told):
        levers.append(
            {
                "lever": lever.lever,
                "lever_name": lever.lever_name,
                "dial": lever.dial,
                # What the TWIN is shown. The subject of this panel.
                "paragraph": rendered[position] if position < len(rendered) else "",
                # The researcher-facing bullet summary. Never fed to a model (`docs/03` §4.3).
                "bullets": [b.text for b in lever.bullets],
            }
        )

    return {
        "version_code": version_code,
        "fairwork_text": board.fairwork_text,
        "levers": levers,
        # Wording A is the rendered order; wording B is the reversed one validity test 5 uses.
        # Empty when nothing has been rendered, so the panel says so rather than showing two
        # identical empty blocks.
        "wordings": (
            {"A": list(rendered), "B": list(reversed(rendered))} if rendered else {}
        ),
        "next_versions": [
            {"code": code, "why": why}
            for code, why in _next_versions(
                version_code,
                advance=advance,
                code_from_index=code_from_index,
                index_from_code=index_from_code,
                control=CONTROL_CODE,
            )
        ],
    }


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
    "checker_test_view",
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
