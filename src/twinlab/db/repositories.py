"""Table access for the orchestrator. `docs/04` §1 and §3.

Every query the loop makes lives here, because SQL and table names live only in `db/`
(`CLAUDE.md` → Boundaries). The orchestrator asks for rows; it never knows a column name.

Two things are load-bearing rather than conveniences:

* **Every mutation that carries an invariant goes through the RPC that flips its pointer** —
  `runs_complete` and `quality_run_record` demote the previous holder and append in the **same
  transaction** (I9). There is no path here that UPDATEs a completed run or a scored quality row.
* **`get_or_create` and `record_answer` are idempotent.** That is what makes resume free: a
  half-finished run re-enters at the same row, and `twin_answers`' unique index on
  `(run_id, twin_id, wording)` means an answered twin is skipped rather than re-asked.
"""

from __future__ import annotations

import uuid
from typing import Any

from twinlab.db.client import DbBackend, DbError, get_backend
from twinlab.models.run import Run, Session
from twinlab.models.twin import PanelMember
from twinlab.models.validity import assert_not_a_probe


def _backend(backend: DbBackend | None = None) -> DbBackend:
    return backend or get_backend()


# --------------------------------------------------------------------------- sessions


class SessionRepo:
    """`sessions`. `docs/04` §3.1."""

    def __init__(self, backend: DbBackend | None = None) -> None:
        self.db = _backend(backend)

    async def create(
        self,
        *,
        name: str,
        kind: str = "sweep",
        iterations: int = 1,
        start_code: str = "10000",
        panel_size: int = 20,
        panel_seed: int | None = None,
        population: str = "real",
        config: dict | None = None,
        budget: dict | None = None,
    ) -> Session:
        """A fresh session. ``cursor_index`` is left ``None`` on purpose.

        ``None`` is how the loop knows this session has not run its control cells yet — it is the
        difference between a fresh session and one resuming at index 0, which `start_code` 00000
        would otherwise make indistinguishable.

        ``panel_seed`` is **drawn here** when not supplied, so the panel is reproducible from the
        stored row alone (I14, `docs/03` §9.1).
        """
        row = {
            "session_id": str(uuid.uuid4()),
            "name": name,
            "kind": kind,
            "status": "created",
            "iterations": iterations,
            "start_code": start_code,
            "cursor_index": None,
            "completed": 0,
            "panel_size": panel_size,
            "panel_seed": panel_seed if panel_seed is not None else uuid.uuid4().int % (2**31),
            "population": population,
            "config": config or {},
            "budget": budget,
        }
        made = await self.db.insert("sessions", [row])
        return Session(**_session_fields(made[0]))

    async def get(self, session_id: str) -> Session:
        rows = await self.db.select("sessions", [("eq", "session_id", session_id)])
        if not rows:
            raise DbError(f"no session {session_id}")
        return Session(**_session_fields(rows[0]))

    async def by_status(self, status: str) -> list[Session]:
        rows = await self.db.select("sessions", [("eq", "status", status)])
        return [Session(**_session_fields(r)) for r in rows]

    async def set_status(self, session_id: str, status: str, **fields: Any) -> None:
        await self.db.update(
            "sessions", {"status": status, **fields}, [("eq", "session_id", session_id)]
        )

    async def set_cursor(self, session_id: str, cursor_index: int) -> None:
        await self.db.update(
            "sessions", {"cursor_index": cursor_index}, [("eq", "session_id", session_id)]
        )

    async def advance(self, session_id: str, cursor_index: int, completed: int) -> None:
        """The checkpoint. Written **after** a run finishes, so a crash re-runs at most one cell."""
        await self.db.update(
            "sessions",
            {"cursor_index": cursor_index, "completed": completed},
            [("eq", "session_id", session_id)],
        )

    async def fail(self, session_id: str, error: str) -> None:
        await self.set_status(session_id, "failed")
        # The reason belongs in the event log, which is what the researcher reads; `sessions` has no
        # error column and adding one would put the same fact in two places.
        _ = error

    async def set_budget(self, session_id: str, budget: dict) -> None:
        await self.db.update("sessions", {"budget": budget}, [("eq", "session_id", session_id)])


def _session_fields(row: dict) -> dict:
    """Only the columns `Session` declares, so an added DDL column does not break construction."""
    return {k: v for k, v in row.items() if k in Session.model_fields}


# --------------------------------------------------------------------------- the frozen panel


class PanelRepo:
    """`session_panel`. I14 made physical: drawn once, then read."""

    def __init__(self, backend: DbBackend | None = None) -> None:
        self.db = _backend(backend)

    async def get(self, session_id: str) -> list[PanelMember]:
        rows = await self.db.select(
            "session_panel", [("eq", "session_id", session_id)], order=("position", False)
        )
        return [
            PanelMember(twin_id=r["twin_id"], stratum=r["stratum"], position=r["position"])
            for r in rows
        ]

    async def freeze(self, session_id: str, panel: list[PanelMember]) -> list[PanelMember]:
        """Write the drawn panel. **Refuses to overwrite an existing one** (I14).

        A session that already has a panel keeps it. Redrawing mid-session would mean two cells
        answered by different twins inside one experiment, which is the thing I14 exists to
        prevent —
        so this raises rather than replacing.
        """
        existing = await self.get(session_id)
        if existing:
            raise DbError(
                f"session {session_id} already has a frozen panel of {len(existing)} twins. "
                "The panel is drawn once and never redrawn (I14): a cell answered by a different "
                "set of twins is a different experiment."
            )
        await self.db.insert(
            "session_panel",
            [
                {
                    "session_id": session_id,
                    "twin_id": m.twin_id,
                    "stratum": m.stratum,
                    "position": m.position,
                }
                for m in panel
            ],
        )
        return panel


# --------------------------------------------------------------------------- runs


class RunRepo:
    """`runs`. Append-only in the sense that matters: `completed` is reached only via the RPC."""

    def __init__(self, backend: DbBackend | None = None) -> None:
        self.db = _backend(backend)

    async def get_or_create(
        self, session_id: str, version_code: str, *, origin: str = "sweep"
    ) -> Run:
        """Idempotent per `(session, code)`. What lets `execute_run` resume mid-flight.

        ``origin`` is written **explicitly** rather than left to the DDL default
        (`ARCHITECTURE_UPDATE.md` §4.3). The column exists so that every number says whether it came
        from the frozen panel or from a one-twin Twin Studio ask, and a value that is only ever
        correct because Postgres filled it in is one the in-memory mirror does not reproduce — which
        is the class of drift `TABLE_COLUMNS` is derived to catch.
        """
        rows = await self.db.select(
            "runs",
            [("eq", "session_id", session_id), ("eq", "version_code", version_code)],
        )
        if rows:
            return Run(**_run_fields(rows[0]))
        made = await self.db.insert(
            "runs",
            [{
                "run_id": str(uuid.uuid4()),
                "session_id": session_id,
                "version_code": version_code,
                "status": "pending",
                "twins_n": 0,
                "origin": origin,
            }],
        )
        return Run(**_run_fields(made[0]))

    async def get(self, run_id: str) -> Run:
        rows = await self.db.select("runs", [("eq", "run_id", run_id)])
        if not rows:
            raise DbError(f"no run {run_id}")
        return Run(**_run_fields(rows[0]))

    async def set_status(self, run_id: str, status: str, **fields: Any) -> None:
        await self.db.update("runs", {"status": status, **fields}, [("eq", "run_id", run_id)])

    async def attach_variant(self, run_id: str, variant_id: str) -> None:
        await self.db.update("runs", {"variant_id": variant_id}, [("eq", "run_id", run_id)])

    async def fail(self, run_id: str, error: str) -> Run:
        """A failed run keeps its row and its reason. The loop continues to the next code."""
        await self.db.update(
            "runs", {"status": "failed", "error": error}, [("eq", "run_id", run_id)]
        )
        return await self.get(run_id)

    async def complete(
        self,
        run_id: str,
        *,
        twins_n: int,
        metrics: dict | None = None,
        index_value: float | None = None,
        analysis: str | None = None,
    ) -> Run:
        """Through `runs_complete`, which flips `is_latest_for_version` in the same transaction
        (I9).

        The RPC refuses ``twins_n <= 0``: a run with no twins is `failed`, never `completed` with an
        index of 0.000 (I15). That refusal is the database's, not this function's, which is the
        point
        — an invariant enforced in DDL cannot be forgotten by a caller.
        """
        await self.db.rpc(
            "runs_complete",
            {
                "p_run_id": run_id,
                "p_twins_n": twins_n,
                "p_metrics": metrics,
                "p_index": index_value,
                "p_analysis": analysis,
            },
        )
        return await self.get(run_id)

    async def latest_completed(self, version_code: str) -> Run | None:
        """The current holder of `is_latest_for_version`. The Dial board's cache check."""
        rows = await self.db.select(
            "runs",
            [
                ("eq", "version_code", version_code),
                ("eq", "status", "completed"),
                ("eq", "is_latest_for_version", True),
            ],
        )
        return Run(**_run_fields(rows[0])) if rows else None

    async def for_session(self, session_id: str) -> list[Run]:
        rows = await self.db.select("runs", [("eq", "session_id", session_id)])
        return [Run(**_run_fields(r)) for r in rows]


def _run_fields(row: dict) -> dict:
    return {k: v for k, v in row.items() if k in Run.model_fields}


# --------------------------------------------------------------------------- answers


class AnswerRepo:
    """`twin_answers`. **Evidence: append-only, never updated** (I9)."""

    def __init__(self, backend: DbBackend | None = None) -> None:
        self.db = _backend(backend)

    async def answered_twins(self, run_id: str, wording: str = "A") -> set[str]:
        """Who has already answered this run. **This is what makes resume free.**

        `twin_answers` has a unique index on `(run_id, twin_id, wording)`, so the loop reads
        this set
        and skips those twins rather than re-paying for them. Asserted on the call counter in the M7
        resume test, because "it resumed" and "it resumed without re-asking" are different claims.
        """
        rows = await self.db.select(
            "twin_answers",
            [("eq", "run_id", run_id), ("eq", "wording", wording)],
        )
        return {r["twin_id"] for r in rows}

    async def record(
        self,
        *,
        run_id: str,
        twin_id: str,
        answers: dict[str, int],
        lever_order: list[int],
        seed: int,
        wording: str,
        model: str,
        prompt_version: str | None = None,
        retries: int = 0,
        latency_ms: int | None = None,
    ) -> dict:
        """Append one answer vector. Idempotent on `(run_id, twin_id, wording)`.

        Upserted rather than inserted so a crash between the model call and the write cannot produce
        a duplicate on resume. The answers themselves are never *changed* — the same twin answering
        the same cell under the same wording is the same evidence.
        """
        rows = await self.db.upsert(
            "twin_answers",
            [{
                "run_id": run_id,
                "twin_id": twin_id,
                "answers": answers,
                "lever_order": lever_order,
                "seed": seed,
                "wording": wording,
                "model": model,
                "prompt_version": prompt_version,
                "retries": retries,
                "latency_ms": latency_ms,
            }],
            on_conflict="run_id,twin_id,wording",
        )
        return rows[0]

    async def for_run(self, run_id: str) -> list[dict]:
        return await self.db.select("twin_answers", [("eq", "run_id", run_id)])


# --------------------------------------------------------------------------- variants


class VariantRepo:
    """`variants`, keyed `(version_code, style_version)`. `docs/04` §6."""

    def __init__(self, backend: DbBackend | None = None) -> None:
        self.db = _backend(backend)

    async def get(self, version_code: str, style_version: str) -> dict | None:
        rows = await self.db.select(
            "variants",
            [("eq", "version_code", version_code), ("eq", "style_version", style_version)],
        )
        return rows[0] if rows else None

    async def put(
        self,
        *,
        version_code: str,
        style_version: str,
        delta_spec: dict,
        delta_hash: str,
        paragraphs: dict,
        checker: dict,
    ) -> dict:
        """Store one variant, keyed `(version_code, style_version)`. Idempotent.

        **Refuses test 4's contradictory probe** (`docs/08` §4 test 4). The guard is here, at the
        write, rather than in whatever calls this: the probe bypassed the lookup (I1) and the
        Checker (I3) by construction, and a `variants` row is exactly what makes a stimulus
        reachable from the Dial board and from the run cache.

        **`variant_id` is minted once and never re-minted.** This was an upsert that carried a
        fresh uuid in every payload; PostgREST resolves a conflict with ``DO UPDATE SET`` over
        every column supplied, so re-storing a variant rewrote its primary key — and `runs`
        already references it. The orchestrator calls this on every run of a code (a resume, a
        rerun, a second iteration), so the second write of any cell would have hit the foreign
        key. Nothing caught it because the in-memory backend has no foreign keys.
        """
        assert_not_a_probe(delta_spec, paragraphs, checker)
        values = {
            "delta_spec": delta_spec,
            "delta_hash": delta_hash,
            "paragraphs": paragraphs,
            "checker": checker,
        }
        existing = await self.get(version_code, style_version)
        if existing is not None:
            await self.db.update(
                "variants", values, [("eq", "variant_id", existing["variant_id"])]
            )
            return {**existing, **values}
        rows = await self.db.insert(
            "variants",
            [{
                "variant_id": str(uuid.uuid4()),
                "version_code": version_code,
                "style_version": style_version,
                **values,
            }],
        )
        return rows[0]
