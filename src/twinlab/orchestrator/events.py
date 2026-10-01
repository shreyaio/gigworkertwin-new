"""The log tree. `docs/04` §7. Serves I11 and the payload discipline of `ARCHITECTURE.md` §7.2.

A stage opens a parent event with ``status='running'``, does its work emitting children, then
updates the parent to ``ok`` or ``error``. The parent's label is **rewritten in place** as work
progresses — that is what gives the researcher `reconstruction (T07)` ticking through twin ids on a
single row rather than a thousand rows to scroll.

**Payloads carry references and telemetry, never bodies.** Not a size optimisation: at panel scale
the prompt bodies alone would exhaust the free tier's 500 MB, and the round prompt is *rebuilt* from
stored fields rather than stored (I11). :func:`redact` enforces this — it is not advisory, and the
DDL caps the column at 8 KB behind it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from twinlab.models.run import EventStatus, Stage

log = logging.getLogger(__name__)

#: `run_events_payload_small`. 8 KB, down from 1.0's 32 KB (`docs/01` §6).
PAYLOAD_MAX_BYTES = 8192

#: Keys that must never appear in a payload, each with what to store instead. `docs/04` §7.2.
#:
#: Checked by name because that is what a caller reaches for. A body that arrives under an
#: unexpected key is still caught by the size cap, but a *small* persona passage would slip
#: through a size-only check — and I11 is about the prompt being rebuilt, not about bytes.
FORBIDDEN_KEYS: dict[str, str] = {
    "prompt": "store `prompt_version` and `prompt_hash`; the prompt is rebuilt (I11)",
    "user_prompt": "store `prompt_hash`",
    "system_prompt": "store `prompt_hash`",
    "round_prompt": "store `seed` and `lever_order`; the round is rebuilt (I11)",
    "persona": "store `persona_hash`",
    "persona_passage": "store `persona_hash`",
    "persona_text": "store `persona_hash`",
    "answers": "store `items_n` and `retries`; the vector lives in `twin_answers`",
    "answer_vector": "store `items_n`",
    "scenario": "store `variant_id` and `delta_hash`",
    "paragraphs": "store `paragraph_id`",
    "text": "store the id of whatever table holds it",
}


class PayloadDiscipline(ValueError):
    """A payload carrying a body rather than a reference. `docs/04` §7.2."""


def payload_size(payload: dict | None) -> int:
    """Serialised size in bytes, the way the DDL's `pg_column_size` counts it closely enough."""
    if payload is None:
        return 0
    return len(json.dumps(payload, default=str, sort_keys=True).encode("utf-8"))


def redact(payload: dict | None, *, strict: bool = True) -> dict | None:
    """Enforce §7.2. Returns a payload that is safe to store, or raises.

    Two different failures, handled differently on purpose:

    * **A forbidden key is a programming error**, so with ``strict`` it raises. There is always a
      reference to store instead, and silently dropping the key would hide that the caller believed
      it was recording something. ``strict=False`` drops it with a marker, for the one place that
      cannot afford to fail a run over a log line — the error path.
    * **Oversize is a data condition**, so it truncates and sets ``truncated = true``, which is what
      `docs/04` §7.2 specifies. A run must not fail because a payload grew.
    """
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise PayloadDiscipline(f"payload must be an object, got {type(payload).__name__}")

    cleaned: dict[str, Any] = {}
    dropped: list[str] = []
    for key, value in payload.items():
        if key.lower() in FORBIDDEN_KEYS:
            if strict:
                raise PayloadDiscipline(
                    f"payload key {key!r} carries a body: {FORBIDDEN_KEYS[key.lower()]} "
                    "(docs/04 §7.2, ARCHITECTURE.md §7.2)"
                )
            dropped.append(key)
            continue
        cleaned[key] = value
    if dropped:
        cleaned["redacted"] = sorted(dropped)

    if payload_size(cleaned) <= PAYLOAD_MAX_BYTES:
        return cleaned

    # Shed the largest values until it fits, rather than truncating the JSON text into something
    # unparseable. The marker is what tells the side panel to go to the source table.
    by_size = sorted(cleaned, key=lambda k: payload_size({k: cleaned[k]}), reverse=True)
    out = dict(cleaned)
    shed: list[str] = []
    for key in by_size:
        if payload_size(out) <= PAYLOAD_MAX_BYTES - 64:
            break
        if key in ("truncated", "redacted"):
            continue
        out.pop(key, None)
        shed.append(key)
    out["truncated"] = True
    if shed:
        out["truncated_keys"] = sorted(shed)
    if payload_size(out) > PAYLOAD_MAX_BYTES:  # pragma: no cover - only if the markers overflow
        return {"truncated": True}
    return out


def validate_tree(events: list[dict]) -> None:
    """Every `parent_event_id` resolves and there are no cycles. `docs/11` M7.

    The tree **is** the researcher-facing record of what ran: a dangling parent hides a stage, and a
    cycle makes the UI's renderer loop. Both are cheap to rule out and impossible to notice by eye
    once a sweep has emitted tens of thousands of rows.
    """
    by_id = {e["event_id"]: e for e in events}
    if len(by_id) != len(events):
        raise ValueError("duplicate event_id in the stream")

    for event in events:
        parent = event.get("parent_event_id")
        if parent is None:
            continue
        if parent not in by_id:
            raise ValueError(
                f"event {event['event_id']} has parent_event_id {parent}, which does not resolve"
            )
        if parent == event["event_id"]:
            raise ValueError(f"event {event['event_id']} is its own parent")

    for event in events:
        seen: set[int] = set()
        cursor = event.get("parent_event_id")
        while cursor is not None:
            if cursor in seen:
                raise ValueError(f"cycle in the event tree at {cursor}")
            seen.add(cursor)
            cursor = by_id[cursor].get("parent_event_id")


class EventLog:
    """Emits events for one session. `docs/04` §7.

    Thin on purpose: it holds the session id and the backend so a stage does not have to thread both
    through every call, and it exposes exactly the four operations §7's pattern needs — open a
    parent, emit a child, rewrite a label, close a parent.
    """

    def __init__(self, session_id: str, backend: Any) -> None:
        self.session_id = session_id
        self._backend = backend

    async def emit(
        self,
        *,
        stage: Stage,
        label: str,
        status: EventStatus = "running",
        agent: str | None = None,
        run_id: str | None = None,
        parent_event_id: int | None = None,
        payload: dict | None = None,
        strict: bool = True,
    ) -> int:
        """One event. Returns its ``event_id`` so it can be a parent."""
        rows = await self._backend.insert(
            "run_events",
            [{
                "session_id": self.session_id,
                "run_id": run_id,
                "parent_event_id": parent_event_id,
                "stage": stage,
                "agent": agent,
                "label": label,
                "status": status,
                "payload": redact(payload, strict=strict),
            }],
        )
        return rows[0]["event_id"]

    async def set_label(self, event_id: int, label: str) -> None:
        """Rewrite a parent's label in place, so progress is one row and not a thousand."""
        await self._backend.update(
            "run_events", {"label": label}, [("eq", "event_id", event_id)]
        )

    async def set_status(self, event_id: int, status: EventStatus, **fields: Any) -> None:
        values: dict[str, Any] = {"status": status}
        if "payload" in fields:
            values["payload"] = redact(fields.pop("payload"), strict=False)
        values.update(fields)
        await self._backend.update("run_events", values, [("eq", "event_id", event_id)])

    async def since(self, after_id: int = 0) -> list[dict]:
        """Only rows newer than ``after_id``. `docs/04` §7.3.

        **Never re-fetch the whole stream** — at sweep scale that is tens of thousands of rows per
        UI tick. The UI keeps the rendered tree in `gr.State` and appends.
        """
        rows = await self._backend.select(
            "run_events",
            [("eq", "session_id", self.session_id), ("gt", "event_id", after_id)],
            order=("event_id", False),
        )
        return rows
