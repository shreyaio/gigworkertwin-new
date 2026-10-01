"""Re-drive stored raw objects that have no matching row. `docs/04` §8. Implements I16's payoff.

This module is **why** intake writes to Storage before it writes to a table. If the insert fails —
a constraint, a dropped connection, a Postgres restart — the driver's answers are still on disk
under `raw/survey_<id>.json`, and this re-drives them. Reverse the order and a failed insert means
a submission that was filled in and is simply gone.

The raw object is the immutable record of what the driver sent. Replay **never edits it**: it
re-runs the same `build_rows` over the same bytes, so a replayed row is byte-identical to the row
the first attempt would have written, and the signature check is not repeated because the object's
presence in private Storage is already proof it was accepted.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.ingest.survey_intake import build_rows

log = logging.getLogger(__name__)


class ReplayError(RuntimeError):
    """A replay that could not be completed. Never silently skipped."""


async def orphaned_paths(storage: Any, backend: Any, *, prefix: str = "raw/") -> list[str]:
    """Storage objects with no `survey_submissions` row. Sorted, so a replay is reproducible.

    Compared on `raw_object_path` rather than on a parsed id: the path is what intake stored and
    what the column holds, so a mismatch in id formatting cannot make an object look orphaned when
    it is not, or the reverse.
    """
    listed = storage.list(prefix)
    if hasattr(listed, "__await__"):
        listed = await listed
    rows = await backend.select("survey_submissions", None)
    known = {r.get("raw_object_path") for r in rows}
    return sorted(p for p in listed if p not in known)


async def replay_one(
    path: str,
    *,
    storage: Any,
    backend: Any,
    ref: ReferenceData | None = None,
) -> dict[str, Any]:
    """Re-drive one object. Idempotent: upserted, so replaying a replayed object changes nothing."""
    ref = ref or reference()
    body = storage.get(path)
    if hasattr(body, "__await__"):
        body = await body
    text = body.decode("utf-8") if isinstance(body, bytes) else str(body)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReplayError(
            f"{path} is not valid JSON: {exc}. The object is left untouched — it is the immutable "
            "record of what the driver sent, and a replay never edits it."
        ) from exc

    rows = build_rows(payload, raw_object_path=path, ref=ref)
    await backend.upsert("survey_submissions", [rows["submission"]], on_conflict="submission_id")
    if rows["answers"]:
        await backend.upsert(
            "survey_answers", rows["answers"], on_conflict="submission_id,item_id"
        )
    return rows["submission"]


async def replay_all(
    *, storage: Any, backend: Any, ref: ReferenceData | None = None
) -> dict[str, list[str]]:
    """Replay every orphan. Returns ``{"replayed": [...], "failed": [...]}``.

    A failure on one object does not stop the rest — but it is **reported**, never swallowed: the
    caller gets both lists and the UI shows the failures, because an object that cannot be
    replayed is a driver's submission that is not in the data.
    """
    replayed: list[str] = []
    failed: list[str] = []
    for path in await orphaned_paths(storage, backend):
        try:
            await replay_one(path, storage=storage, backend=backend, ref=ref)
            replayed.append(path)
        except Exception as exc:  # noqa: BLE001 - one bad object must not block the others
            log.error("replay failed for %s: %s", path, exc)
            failed.append(path)
    return {"replayed": replayed, "failed": failed}
