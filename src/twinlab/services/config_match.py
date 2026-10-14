"""The config a quality verdict belongs to. RESEARCHER 2026-10-05 (`docs/DECISIONS.md`).

A quality verdict and a twin's control answers are only valid for the configuration that produced
them. Change the model, the temperature, the wording, the prompt, the battery, the style version or
a kept threshold and the same twin can answer differently, so the old verdict no longer describes
the instrument the study is about to run.

So every verdict and every control answer is stored with :func:`current_fingerprint`, and every
stage that uses a twin (a session, a sweep, a resume, a validity test) first checks that the twin
was qualified under the **current** fingerprint. A mismatch is a refusal that says what to run, not
a silent reuse (I15: fail loudly and stop).

The fingerprint is a hash of inputs, never of outputs, and nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, get_backend
from twinlab.ingest.reference_store import reference
from twinlab.services.config import refresh_twin_config


async def current_config(backend: DbBackend | None = None) -> dict[str, Any]:
    """Every input that changes what a twin answers or what a verdict means. Read, never stored.

    Shown beside the verdicts so a researcher can see *which* config a number was made under, not
    only whether it matches.
    """
    from twinlab.agents.registry import resolve_prompt
    from twinlab.services.twin_runtime import battery_for, twin_agent_config

    db = backend or get_backend()
    cfg = await refresh_twin_config(db)
    twin = twin_agent_config()
    _, prompt_sha = resolve_prompt(twin)
    # The same agent config with the H3 round's prompt override applied, exactly as
    # `ask_h3_round` builds it, so the hash is of the file the gate actually sends.
    from twinlab.services.twin_runtime import (
        H3_PROMPT_REF,
        H3_PROTOCOL,
        H3_PROTOCOL_ISOLATED,
        h3_protocol_is_isolated,
    )

    _, h3_prompt_sha = resolve_prompt(twin_agent_config(prompt_ref=H3_PROMPT_REF))
    battery = battery_for(reference())
    return {
        "model": twin.model.name,
        "temperature": float(twin.model.temperature),
        "prompt_sha256": prompt_sha,
        # **The H3 gate's own prompt, which is not the twin prompt above.** `H3_PROMPT_REF`
        # swaps in a sibling file for the Part 17 round only, so the hash above describes the
        # battery and sweep rounds and says nothing about the prompt that produced every stored
        # H3 verdict. Without this a rewritten H3 prompt left the fingerprint unmoved: the gate
        # reported "already scored under this config" and skipped every twin, and a verdict made
        # under an older Part 17 prompt read as current. Found while re-gating after
        # `twin_h3_v3.md` (`docs/DECISIONS.md`, 2026-10-13).
        "h3_prompt_sha256": h3_prompt_sha,
        # **Which Part 17 protocol produced the verdict.** Six versions in one context and six in
        # isolation are different measurements, so a verdict taken under one must not read as
        # current under the other — the same class of defect as the H3 prompt hash above, which
        # let the gate skip every twin after the prompt was rewritten.
        "h3_protocol": (
            H3_PROTOCOL_ISOLATED if h3_protocol_is_isolated() else H3_PROTOCOL
        ),
        "wording": cfg.wording,
        "show_baseline": cfg.show_baseline,
        "style_version": settings.style_version,
        # The stem, the range **and the anchors**: all three are what the twin reads, so all
        # three belong in the fingerprint. Adding the anchors moves every fingerprint once,
        # which is the intended effect — a verdict made when the scale ran unlabelled was made
        # under a different instrument (`docs/DECISIONS.md`, 2026-10-12).
        "battery": sorted(
            [item_id, [item.stem, item.points, list(item.anchors)]]
            for item_id, item in battery.items()
        ),
        "mae_max": cfg.mae_max,
        "pct_within_1_min": cfg.pct_within_1_min,
    }


async def current_fingerprint(backend: DbBackend | None = None) -> str:
    """A short, stable hash of :func:`current_config`, stored on every verdict and control."""
    payload = json.dumps(await current_config(backend), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


async def describe(backend: DbBackend | None = None) -> str:
    """One line for the status card: which model and temperature the live verdicts are for."""
    cfg = await current_config(backend)
    return f"{cfg['model']} at temperature {cfg['temperature']:g}"


async def qualified_twin_ids(
    fingerprint: str, backend: DbBackend | None = None
) -> set[str]:
    """Twins a panel may be drawn from **under this fingerprint**. The single definition.

    Kept by the latest H3 verdict made under ``fingerprint``, and holding both control answers under
    it. Every other reader (the panel draw, the readiness line, the status card) takes this set, so
    the answer to "is this twin qualified?" cannot differ between screens.
    """
    from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE

    db = backend or get_backend()
    latest = await db.select(
        "twin_quality_runs",
        [("eq", "is_latest", True), ("eq", "holdout_set", "H3"),
         ("eq", "config_fingerprint", fingerprint)],
    )
    kept = {str(r["twin_id"]) for r in latest if r.get("kept")}
    if not kept:
        return set()
    controls = await db.select(
        "twin_control_answers", [("eq", "config_fingerprint", fingerprint)]
    )
    have: dict[str, set[str]] = {}
    for row in controls:
        have.setdefault(str(row["twin_id"]), set()).add(str(row["control_code"]))
    needed = {CONTROL_CODE, SHAM_CODE}
    return {t for t in kept if have.get(t, set()) >= needed}


async def qualified_state(
    fingerprint: str, backend: DbBackend | None = None
) -> dict[str, int]:
    """How the twin pool stands against one fingerprint. One read per table, no writes.

    ``current`` is twins whose **latest** H3 verdict was made under ``fingerprint`` and kept them.
    ``stale`` is twins that were kept under some other config and have no current verdict, the case
    the refusal message exists for. ``controlled`` is twins that also have both control answers
    under ``fingerprint``, which a panel needs.
    """
    from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE

    db = backend or get_backend()
    latest = await db.select(
        "twin_quality_runs", [("eq", "is_latest", True), ("eq", "holdout_set", "H3")]
    )
    current_kept: set[str] = set()
    current_scored: set[str] = set()
    stale: set[str] = set()
    for row in latest:
        twin_id = str(row["twin_id"])
        if row.get("config_fingerprint") == fingerprint:
            current_scored.add(twin_id)
            if row.get("kept"):
                current_kept.add(twin_id)
        elif row.get("kept"):
            stale.add(twin_id)
    controls = await db.select(
        "twin_control_answers", [("eq", "config_fingerprint", fingerprint)]
    )
    have: dict[str, set[str]] = {}
    for row in controls:
        have.setdefault(str(row["twin_id"]), set()).add(str(row["control_code"]))
    needed = {CONTROL_CODE, SHAM_CODE}
    # A verdict counts as finished only with both of its control answers beside it.
    scored = {t for t in current_scored if have.get(t, set()) >= needed}
    controlled = {t for t in current_kept if have.get(t, set()) >= needed}
    return {
        "scored": len(scored),
        "current": len(current_kept),
        "controlled": len(controlled),
        "stale": len(stale - current_kept),
    }


__all__ = [
    "current_config",
    "current_fingerprint",
    "describe",
    "qualified_state",
]
