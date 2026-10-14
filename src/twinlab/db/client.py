"""The database boundary.

``supabase`` is imported here and nowhere else (`CLAUDE.md`, Boundaries). Every repository speaks
the small :class:`DbBackend` protocol below, which is deliberately narrower than PostgREST:
select, insert, upsert, update, delete, count, rpc. Nothing else reaches the database.

Two backends:

* :class:`SupabaseBackend` — the real one. Retries with backoff, because a free Supabase project
  pauses after ~7 days idle and the first request after a pause fails (`ARCHITECTURE.md` §8.4).
* :class:`InMemoryBackend` — a faithful-enough stand-in for tests and for running the app before
  credentials exist. It implements the same operations over dicts, including the two pointer-flip
  RPCs, so idempotency and append-only behaviour are testable without a server.

The in-memory backend is never selected silently in production: choosing it logs a warning line,
and :func:`require_live_backend` raises if a caller demands the real thing.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from config.settings import settings

log = logging.getLogger(__name__)

Filter = tuple[Literal["eq", "neq", "in", "is", "gt", "gte", "lt", "lte"], str, Any]

#: Our operator name → postgrest's method name. `in` and `is` are Python keywords, so the builder
#: spells them `in_` and `is_`; `getattr(query, "in")` therefore raised `AttributeError`, which
#: `SupabaseBackend._run` retried four times before reporting it as a database failure. Both
#: operators work by name in :class:`InMemoryBackend`, so the whole suite passed and the two
#: callers — `services.surveys.delete_synthetic` and the log tree's ancestor lookup — failed only
#: against a real project. Module level so a test can check it without the live-backend ban in
#: `tests/conftest.py` getting in the way.
FILTER_METHODS = {"in": "in_", "is": "is_"}

#: Rows per PostgREST request. Supabase's `db-max-rows` is 1,000 and the server silently returns
#: the first page rather than erroring, so this is a ceiling we page under, not a preference.
PAGE_SIZE = 1000

#: Where the DDL lives. :data:`TABLE_COLUMNS` is derived from it at import so the in-memory
#: mirror cannot drift from the schema it mirrors.
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _parse_ddl_columns(sql: str) -> dict[str, set[str]]:
    """Table → column names, read out of the migration SQL.

    Deliberately derived rather than hand-written. A hand-maintained copy is a second source of
    truth that drifts silently, which is the exact failure this exists to catch: five callers
    ordered `runs` by `created_at`, a column the DDL has never had, and 684 tests passed because
    the mirror answered `None` for it where Postgres answers `42703`.
    """
    tables: dict[str, set[str]] = {}
    for match in re.finditer(
        r"create table if not exists (\w+)\s*\((.*?)\n\);", sql, re.S | re.I
    ):
        cols = tables.setdefault(match.group(1), set())
        for line in match.group(2).splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            word = re.match(r"([a-z_][a-z0-9_]*)\s", line)
            # Table-level constraint clauses open with a reserved word, not a column name.
            if word and word.group(1) not in _DDL_CONSTRAINT_WORDS:
                cols.add(word.group(1))
    # `\s+` rather than a literal space: a wrapped `alter table x\n  add column ...` is the same
    # DDL, and a parser that missed it silently dropped the column from the mirror — which is the
    # exact drift this function exists to make impossible. Caught by `004`'s wrapped line.
    for match in re.finditer(
        r"alter\s+table\s+(\w+)\s+add\s+column\s+if\s+not\s+exists\s+(\w+)", sql, re.I
    ):
        tables.setdefault(match.group(1), set()).add(match.group(2))
    return tables


_DDL_CONSTRAINT_WORDS = frozenset(
    {"primary", "unique", "check", "constraint", "foreign", "references", "exclude"}
)


def _load_table_columns() -> dict[str, frozenset[str]]:
    sql = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
    )
    return {table: frozenset(cols) for table, cols in _parse_ddl_columns(sql).items()}


#: Every table's real column set, from the migrations. Used by :class:`InMemoryBackend` to refuse
#: a column Postgres would refuse.
TABLE_COLUMNS: dict[str, frozenset[str]] = _load_table_columns()


async def paged_select(
    fetch: Any, limit: int | None = None, *, page: int = PAGE_SIZE
) -> list[Row]:
    """Accumulate `fetch(start, count)` pages until a short one arrives or ``limit`` is reached.

    Separate from :class:`SupabaseBackend` so the paging can be tested without a client: the live
    backend is banned outright in `tests/conftest.py`, and the cap it exists to defeat is a
    server-side one that no in-memory stand-in reproduces.

    Stopping on a **short page** rather than on a row count means the loop ends on the real last
    page instead of on an assumption about the server's cap — if `db-max-rows` is lowered, this
    keeps working and simply makes more requests.
    """
    out: list[Row] = []
    while True:
        want = page if limit is None else min(page, limit - len(out))
        if want <= 0:
            return out
        got = await fetch(len(out), want)
        out.extend(got)
        if len(got) < want:
            return out
Row = dict[str, Any]


class DbError(RuntimeError):
    """Any failure that reached the database boundary."""


#: SQLSTATE classes that are **deterministic**. A call that fails with one of these fails
#: identically every time, so retrying it is four times the latency and four identical log lines
#: for no chance of success — which is exactly what one failed delete produced before this existed
#: (`ARCHITECTURE_UPDATE.md` §3.3).
#:
#: * ``23`` integrity — foreign key (`23503`), unique (`23505`), check (`23514`), not-null.
#: * ``22`` data — bad numeric, bad datetime, out-of-range.
#: * ``42`` syntax or access — unknown column (`42703`), unknown table (`42P01`).
#:
#: A `23503` is the researcher being told something true about their data. Dressing it up as a
#: flaky connection is the failure mode this study cannot afford.
PERMANENT_SQLSTATE_CLASSES = ("23", "22", "42")

#: PostgREST's own error codes for a schema it cannot see. Not SQLSTATEs, and just as permanent.
PERMANENT_PGRST_CODES = frozenset({"PGRST202", "PGRST204", "PGRST205"})

#: Substrings that mark a **transient** transport failure. Matched on the exception text because
#: `httpx` and `h2` raise their own types through two wrapper layers and the SDK does not
#: normalise them. Deliberately narrow: anything unrecognised is retried, because the cost of
#: retrying a transient error wrongly classified as permanent is a dead session.
TRANSIENT_MARKERS = (
    "connectionterminated",
    "connectionreset",
    "remoteprotocolerror",
    "connecterror",
    "connecttimeout",
    "readtimeout",
    "writetimeout",
    "pooltimeout",
    "timeout",
    "winerror 10035",
    "winerror 10054",
    "winerror 10053",
    "temporarily unavailable",
    "server disconnected",
    "connection aborted",
    "too many requests",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
)


def _sqlstate_of(exc: Exception) -> str:
    """The SQLSTATE or PostgREST code an exception carries, or ``""``.

    ``postgrest.exceptions.APIError`` exposes ``code``; `supabase-py` also raises the raw dict
    through in places. Both shapes are read, and a text fallback catches the string form the SDK
    produces when it wraps a response it could not parse.
    """
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    details = getattr(exc, "args", None)
    if details and isinstance(details[0], dict):
        found = details[0].get("code")
        if isinstance(found, str):
            return found
    # `"{'code': '23503', ...}"` — the SDK's repr of a body it passed through unparsed.
    match = re.search(r"'code':\s*'([0-9A-Za-z]+)'", str(exc))
    return match.group(1) if match else ""


def is_permanent(exc: Exception) -> bool:
    """Whether retrying ``exc`` can ever succeed. `ARCHITECTURE_UPDATE.md` §3.3.

    Permanent by code (integrity, data, syntax, a schema PostgREST cannot see) or by type — an
    `AttributeError` from a mis-mapped filter operator is a bug in this file, not a flaky network,
    and retrying it four times is how that class of defect stayed invisible for a release.

    A transient marker in the text wins over nothing else: an unrecognised failure is treated as
    transient, because a dead session costs more than three wasted retries.
    """
    if isinstance(exc, TypeError | AttributeError | KeyError | NotImplementedError):
        return True
    code = _sqlstate_of(exc)
    if code:
        if code in PERMANENT_PGRST_CODES:
            return True
        if code[:2] in PERMANENT_SQLSTATE_CLASSES:
            return True
    text = str(exc).lower()
    if any(marker in text for marker in TRANSIENT_MARKERS):
        return False
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if isinstance(status, int):
        # 5xx and 429 are worth another try; every other 4xx is the request being wrong.
        return not (status >= 500 or status == 429)
    return False


async def retrying(
    fn: Any, *, attempts: int = 4, base_delay: float = 0.75, sleep: Any = None
) -> Any:
    """Call ``fn`` in a worker thread, retrying **only** what a retry could fix. §3.3.

    Module level, and for the same reason :func:`paged_select` is: `tests/conftest.py` forbids the
    suite from constructing a :class:`SupabaseBackend` at all, so a retry policy that lived only on
    the method would be the one piece of the database boundary with no test. ``sleep`` is injected
    so a test asserts the branch without waiting 5 s for the backoff.
    """
    pause = sleep or asyncio.sleep
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return await asyncio.to_thread(fn)
        except DbError:
            # Already classified and already worded for the researcher — `_apply`'s
            # unmapped-operator refusal is the one that reaches here. Re-wrapping it would bury
            # the sentence that says what to do about it.
            raise
        except Exception as exc:  # noqa: BLE001 — classified, then surfaced as DbError
            last = exc
            if is_permanent(exc):
                raise DbError(f"database refused the call: {exc}") from exc
            if attempt == attempts - 1:
                break
            delay = base_delay * (2**attempt)
            log.warning("db call failed (%s); retrying in %.2fs", exc, delay)
            await pause(delay)
    raise DbError(f"database call failed after {attempts} attempts: {last!r}")


class DbBackend(Protocol):
    """The only vocabulary a repository has."""

    name: str

    async def select(
        self,
        table: str,
        filters: list[Filter] | None = None,
        *,
        order: tuple[str, bool] | None = None,
        limit: int | None = None,
    ) -> list[Row]: ...

    async def insert(self, table: str, rows: list[Row]) -> list[Row]: ...

    async def upsert(self, table: str, rows: list[Row], *, on_conflict: str) -> list[Row]: ...

    async def update(self, table: str, values: Row, filters: list[Filter]) -> list[Row]: ...

    async def delete(self, table: str, filters: list[Filter]) -> list[Row]: ...

    async def count(self, table: str, filters: list[Filter] | None = None) -> int: ...

    async def rpc(self, fn: str, params: Row) -> Any: ...


# --------------------------------------------------------------------------- Supabase


class SupabaseBackend:
    """PostgREST via supabase-py, wrapped in backoff.

    supabase-py is synchronous; every call runs in a worker thread so the orchestrator's event
    loop is never blocked (`CLAUDE.md` → Style: async all the way down from the service layer).
    """

    name = "supabase"

    def __init__(
        self,
        url: str,
        key: str,
        *,
        attempts: int = 4,
        base_delay: float = 0.75,
        max_concurrency: int | None = None,
    ) -> None:
        from supabase import create_client  # the one and only import

        self._client = create_client(url, key)
        self._attempts = attempts
        self._base_delay = base_delay
        # `ARCHITECTURE_UPDATE.md` §3.2. supabase-py is synchronous and every call here runs in
        # `asyncio.to_thread`, so one `httpx` client — one HTTP/2 connection — was shared across
        # an unbounded default thread pool. 133 streams on one connection is what
        # `last_stream_id:133` in the `ConnectionTerminated` was reporting. `max_concurrency`
        # bounds the *provider*; nothing bounded the database, so this does.
        limit = (
            max_concurrency
            if max_concurrency is not None
            else getattr(settings, "db_max_concurrency", 4)
        )
        self._limit = max(int(limit), 1)
        # One semaphore **per event loop**. `services.config.startup_check` runs four separate
        # `asyncio.run` calls before Gradio's own loop exists, and an `asyncio.Semaphore` binds
        # itself to the first loop it has to block on and then raises against any other. A single
        # shared semaphore would therefore work until the first time it actually contended, and
        # then fail inside a sweep — the worst possible place.
        self._gates: dict[Any, asyncio.Semaphore] = {}
        self._disable_http2()

    def _gate(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        gate = self._gates.get(loop)
        if gate is None:
            gate = self._gates[loop] = asyncio.Semaphore(self._limit)
        return gate

    def _disable_http2(self) -> None:
        """Put the PostgREST client on HTTP/1.1. `ARCHITECTURE_UPDATE.md` §3.2 step 3.

        Keep-alive suits this access pattern — many small sequential requests from a bounded pool —
        and the study's query volume never needs multiplexing. HTTP/2 bought nothing here and cost
        a stream-exhaustion `ConnectionTerminated` that the retry loop then hid.

        Best-effort and silent on failure: the attribute path is `supabase-py`'s private shape and
        a version bump may move it. The semaphore above is the load-bearing half; this is the belt
        to its braces, and a database that works slightly less well must not stop the app booting.
        """
        if not settings.db_http2_disabled:
            return
        for owner in (getattr(self._client, "postgrest", None), self._client):
            session = getattr(owner, "session", None) or getattr(owner, "_session", None)
            if session is None:
                continue
            try:
                session._transport = __import__("httpx").HTTPTransport(
                    retries=0, http2=False
                )
            except Exception as exc:  # noqa: BLE001 — never block boot on a transport tweak
                log.debug("could not force HTTP/1.1 on the PostgREST client: %r", exc)

    async def _run(self, fn: Any) -> Any:
        """One PostgREST call, bounded, with **transient failures retried and permanent ones not**.

        Implements `ARCHITECTURE_UPDATE.md` §3.3. A `23503` foreign-key violation is a true
        statement about the researcher's data and is raised on its first occurrence with the
        constraint name intact; only transport failures, 5xx and 429 are retried. The old loop
        caught bare `Exception` and retried everything four times, which is why one blocked delete
        printed the same violation four times over five seconds before reporting it.
        """
        async with self._gate():
            return await retrying(
                fn, attempts=self._attempts, base_delay=self._base_delay
            )

    def _apply(self, query: Any, filters: list[Filter] | None) -> Any:
        for op, col, val in filters or []:
            method = getattr(query, FILTER_METHODS.get(op, op), None)
            if method is None:
                raise DbError(
                    f"postgrest has no filter method for {op!r}. Map it in `_METHODS` rather "
                    "than letting `getattr` fail at the boundary."
                )
            query = method(col, val)
        return query

    async def select(
        self,
        table: str,
        filters: list[Filter] | None = None,
        *,
        order: tuple[str, bool] | None = None,
        limit: int | None = None,
    ) -> list[Row]:
        """Every matching row, **paged**. `docs/07` §11.

        PostgREST caps a response at `db-max-rows` — 1,000 on a Supabase project — and returns the
        first page with a `200`, not an error. This method used to issue one request and hand back
        whatever came, so any read of a large table was silently truncated: `survey_answers` at 300
        synthetic respondents is 21,900 rows and `select` returned 1,000 of them. Every statistic
        `stats/dataset.py` builds from those rows would have been computed on a fifth of the data,
        the export would have been short, and **nothing anywhere would have said so** — the golden
        gate passes because it runs on in-memory fixtures, and `InMemoryBackend` has no cap. This
        is the single most dangerous kind of defect in the system: a plausible number that is
        wrong.

        Paging continues until a short page arrives, so the loop ends on the real last page rather
        than on a guess about the server's cap.

        **Order matters when paging.** Postgres does not guarantee row order without an `ORDER BY`,
        so a caller that needs more than one page and cares about duplicates or gaps across page
        boundaries should pass ``order``. Every caller that reads a large table either passes one
        or consumes the rows as a set.
        """
        def _go(start: int, count: int) -> list[Row]:
            q = self._apply(self._client.table(table).select("*"), filters)
            if order is not None:
                q = q.order(order[0], desc=order[1])
            return list(q.range(start, start + count - 1).execute().data or [])

        async def _fetch(start: int, count: int) -> list[Row]:
            return await self._run(lambda: _go(start, count))

        return await paged_select(_fetch, limit)

    async def insert(self, table: str, rows: list[Row]) -> list[Row]:
        return await self._run(lambda: list(self._client.table(table).insert(rows).execute().data))

    async def upsert(self, table: str, rows: list[Row], *, on_conflict: str) -> list[Row]:
        return await self._run(
            lambda: list(
                self._client.table(table).upsert(rows, on_conflict=on_conflict).execute().data
            )
        )

    async def update(self, table: str, values: Row, filters: list[Filter]) -> list[Row]:
        def _go() -> list[Row]:
            q = self._apply(self._client.table(table).update(values), filters)
            return list(q.execute().data or [])

        return await self._run(_go)

    async def delete(self, table: str, filters: list[Filter]) -> list[Row]:
        def _go() -> list[Row]:
            q = self._apply(self._client.table(table).delete(), filters)
            return list(q.execute().data or [])

        return await self._run(_go)

    async def count(self, table: str, filters: list[Filter] | None = None) -> int:
        def _go() -> int:
            q = self._apply(self._client.table(table).select("*", count="exact"), filters)
            return int(q.execute().count or 0)

        return await self._run(_go)

    async def rpc(self, fn: str, params: Row) -> Any:
        return await self._run(lambda: self._client.rpc(fn, params).execute().data)


# --------------------------------------------------------------------------- in memory


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class InMemoryBackend:
    """Dict-backed stand-in with the same semantics for the operations we use."""

    name: str = "memory"
    tables: dict[str, list[Row]] = field(default_factory=dict)
    _serial: itertools.count = field(default_factory=lambda: itertools.count(1))

    #: Primary keys, so upsert can be idempotent the way `seed_db.py` needs. Composite keys are
    #: comma-separated, matching the `on_conflict` spelling PostgREST takes.
    PRIMARY_KEYS = {
        "scales": "scale_id",
        "constructs": "code",
        "survey_items": "item_id",
        "arms": "arm_id",
        "legacy_items": "legacy_id",
        "criteria": "criterion_id",
        "thresholds": "threshold_id",
        "criterion_findings": "criterion_id",
        "gaps": "gap_id",
        "corpus_chunks": "chunk_id",
        "chunk_criterion_links": "link_id",
        "synthetic_batches": "batch_id",
        "survey_submissions": "submission_id",
        "survey_answers": "submission_id,item_id",
        "twins": "twin_id",
        "sessions": "session_id",
        "session_panel": "session_id,twin_id",
        "lever_paragraphs": "paragraph_id",
        "variants": "variant_id",
        "runs": "run_id",
        "run_events": "event_id",
        "twin_answers": "answer_id",
        "twin_quality_runs": "quality_run_id",
        "validity_results": "validity_run_id",
        "analysis_runs": "analysis_id",
        "analysis_results": "analysis_id,stage",
        "studio_runs": "studio_run_id",
        "agent_configs": "agent_id",
        "agent_config_history": "history_id",
        "app_config": "key",
    }

    #: Tables whose primary key the database generates. Everything else must arrive with one.
    GENERATED_KEYS = frozenset(
        {
            "synthetic_batches",
            "sessions",
            "lever_paragraphs",
            "variants",
            "runs",
            "run_events",
            "twin_answers",
            "twin_quality_runs",
            "validity_results",
            "analysis_runs",
            "studio_runs",
            "agent_config_history",
        }
    )

    #: Tables that actually carry a `created_at` column. `run_events` uses `ts`, and
    #: `survey_answers` has neither, so neither gets one invented for it.
    HAS_CREATED_AT = frozenset(
        {
            "synthetic_batches",
            "survey_submissions",
            "twins",
            "sessions",
            "lever_paragraphs",
            "variants",
            "twin_answers",
            "twin_quality_runs",
            "validity_results",
            "analysis_runs",
            "studio_runs",
            "agent_config_history",
        }
    )

    #: Serial primary keys, which are integers rather than UUIDs.
    SERIAL_KEYS = frozenset({"run_events", "agent_config_history"})

    @staticmethod
    def _check_columns(table: str, columns: Any, where: str) -> None:
        """Refuse a column the real schema does not have, the way Postgres would.

        Mirrors `42703 undefined_column`. Without this the mirror is *more permissive* than the
        database in the one direction that hides schema drift: ``row.get(col)`` answers ``None``
        for a column that does not exist, so a sort or a filter on a misspelled column passes
        every test and fails only against a live project.

        A table absent from :data:`TABLE_COLUMNS` is not checked — a test may stand up a scratch
        table that no migration declares, and inventing a failure for it would be its own bug.
        """
        known = TABLE_COLUMNS.get(table)
        if known is None:
            return
        unknown = sorted(c for c in columns if c not in known)
        if unknown:
            raise DbError(
                f"undefined_column: {table} has no column(s) {', '.join(unknown)} "
                f"(in {where}). Columns are {', '.join(sorted(known))}."
            )

    def _rows(self, table: str) -> list[Row]:
        return self.tables.setdefault(table, [])

    @staticmethod
    def _matches(row: Row, filters: list[Filter] | None) -> bool:
        for op, col, val in filters or []:
            got = row.get(col)
            if op == "eq" and got != val:
                return False
            if op == "neq" and got == val:
                return False
            if op == "in" and got not in val:
                return False
            if op == "is" and got is not val:
                return False
            if op == "gt" and not (got is not None and got > val):
                return False
            if op == "gte" and not (got is not None and got >= val):
                return False
            if op == "lt" and not (got is not None and got < val):
                return False
            if op == "lte" and not (got is not None and got <= val):
                return False
        return True

    def _defaults(self, table: str, row: Row) -> Row:
        row = dict(row)
        pk = self.PRIMARY_KEYS.get(table)
        if pk and "," not in pk and pk not in row and table in self.GENERATED_KEYS:
            row[pk] = next(self._serial) if table in self.SERIAL_KEYS else str(uuid.uuid4())
        if table in self.HAS_CREATED_AT:
            row.setdefault("created_at", _now())
        if table == "runs":
            row.setdefault("status", "pending")
            row.setdefault("is_latest_for_version", False)
            row.setdefault("twins_n", 0)
            row.setdefault("started_at", _now())
        if table == "run_events":
            row.setdefault("ts", _now())
        if table == "twin_quality_runs":
            row.setdefault("is_latest", True)
        if table == "survey_submissions":
            # Generated columns (docs/01 §6.2), computed here so a test sees the same values.
            seconds = row.get("completion_seconds")
            row["speeder"] = None if seconds is None else seconds < 480
            row["mc_correct"] = row.get("mc_answer") == row.get("arm")
        return row

    def _check_constraints(self, table: str, row: Row) -> None:
        """The DDL constraints that encode an invariant. `docs/01` §6.

        The in-memory backend is what the invariant suite runs against, so a constraint that
        only existed in Postgres would be untested (I15 especially — it is the one the
        prototype broke). These mirror `002_v2_model.sql`.
        """
        if table == "runs" and row.get("status") == "completed" and not (row.get("twins_n") or 0):
            raise DbError("runs_completed_has_twins: a completed run needs twins_n > 0 (I15)")
        if table == "validity_results":
            if not (row.get("twins_n") or 0) and row.get("verdict") != "INCONCLUSIVE":
                raise DbError(
                    "validity_zero_n: a test on zero twins is INCONCLUSIVE, never "
                    f"{row.get('verdict')!r} (I15)"
                )
        if table == "twin_quality_runs":
            if not (row.get("items_n") or 0) > 0:
                raise DbError("quality_has_items: items_n must be > 0 (I15)")
            if (row.get("holdout_set") == "H3") != (row.get("kept") is not None):
                raise DbError("quality_h3_gates: H3 carries `kept`; H2 carries null")
            if row.get("holdout_set") == "H2" and row.get("arm") is None:
                raise DbError("quality_h2_arm: an H2 row records the arm the human saw")
        if table == "run_events" and row.get("payload") is not None:
            # `run_events_payload_small`, 8 KB. `ARCHITECTURE.md` §7.2: at panel scale the prompt
            # bodies alone would exhaust the 500 MB tier, so payloads carry references and
            # telemetry only. Mirrored here because a cap enforced only in Postgres would be
            # untested — and `events.redact()` is what is meant to keep callers under it.
            size = len(json.dumps(row["payload"], default=str).encode("utf-8"))
            if size > 8192:
                raise DbError(
                    f"run_events_payload_small: payload is {size} bytes, over the 8192 cap. "
                    "Store the reference, not the body (docs/04 §7.2) — the prompt is rebuilt "
                    "from stored fields (I11)."
                )
        if table == "agent_configs" and row.get("output_mode") not in ("tool", "prompted"):
            raise DbError(
                "agent_no_native_output: output_mode must be 'tool' or 'prompted' "
                "(ARCHITECTURE.md §3.2)"
            )
        if table == "analysis_runs":
            if (row.get("bootstrap_samples") or 0) < 30:
                raise DbError("analysis_bootstrap_floor: bootstrap_samples must be >= 30")
            if (row.get("n_cases") or 0) <= 0:
                raise DbError("analysis_has_cases: n_cases must be > 0")

    async def select(
        self,
        table: str,
        filters: list[Filter] | None = None,
        *,
        order: tuple[str, bool] | None = None,
        limit: int | None = None,
    ) -> list[Row]:
        self._check_columns(table, [c for _, c, _ in filters or []], "select filters")
        out = [dict(r) for r in self._rows(table) if self._matches(r, filters)]
        if order is not None:
            col, desc = order
            self._check_columns(table, [col], "select order")
            out.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        return out[:limit] if limit is not None else out

    async def insert(self, table: str, rows: list[Row]) -> list[Row]:
        for row in rows:
            self._check_columns(table, row, "insert")
        made = [self._defaults(table, r) for r in rows]
        for row in made:
            self._check_constraints(table, row)
        self._rows(table).extend(made)
        return [dict(r) for r in made]

    async def upsert(self, table: str, rows: list[Row], *, on_conflict: str) -> list[Row]:
        keys = [k.strip() for k in on_conflict.split(",")]
        self._check_columns(table, keys, "upsert on_conflict")
        out: list[Row] = []
        for row in rows:
            self._check_columns(table, row, "upsert")
            new = self._defaults(table, row)
            self._check_constraints(table, new)
            existing = next(
                (r for r in self._rows(table) if all(r.get(k) == new.get(k) for k in keys)),
                None,
            )
            if existing is None:
                self._rows(table).append(new)
                out.append(dict(new))
            else:
                existing.update(dict(new))
                out.append(dict(existing))
        return out

    async def update(self, table: str, values: Row, filters: list[Filter]) -> list[Row]:
        self._check_columns(table, values, "update values")
        self._check_columns(table, [c for _, c, _ in filters or []], "update filters")
        touched: list[Row] = []
        for row in self._rows(table):
            if self._matches(row, filters):
                candidate = {**row, **values}
                self._check_constraints(table, candidate)
                row.update(values)
                touched.append(dict(row))
        return touched

    async def delete(self, table: str, filters: list[Filter]) -> list[Row]:
        self._check_columns(table, [c for _, c, _ in filters or []], "delete filters")
        keep, gone = [], []
        for row in self._rows(table):
            (gone if self._matches(row, filters) else keep).append(row)
        self.tables[table] = keep
        return [dict(r) for r in gone]

    async def count(self, table: str, filters: list[Filter] | None = None) -> int:
        self._check_columns(table, [c for _, c, _ in filters or []], "count filters")
        return len([r for r in self._rows(table) if self._matches(r, filters)])

    async def rpc(self, fn: str, params: Row) -> Any:
        """The two pointer-flip functions, with the same ordering as the SQL (I9)."""
        if fn == "runs_complete":
            run = next((r for r in self._rows("runs") if r["run_id"] == params["p_run_id"]), None)
            if run is None:
                raise DbError(f"runs_complete: no run {params['p_run_id']}")
            twins_n = params.get("p_twins_n") or 0
            if twins_n <= 0:
                raise DbError(
                    "runs_completed_has_twins: a run with no twins is failed, never completed "
                    "with an index of 0.000 (I15)"
                )
            for other in self._rows("runs"):
                if other["version_code"] == run["version_code"] and other.get(
                    "is_latest_for_version"
                ):
                    other["is_latest_for_version"] = False
            run.update(
                status="completed",
                finished_at=_now(),
                is_latest_for_version=True,
                metrics=params.get("p_metrics"),
                index_value=params.get("p_index"),
                llm_analysis=params.get("p_analysis"),
                twins_n=twins_n,
            )
            return dict(run)
        if fn == "quality_run_record":
            for row in self._rows("twin_quality_runs"):
                if (
                    row["twin_id"] == params["p_twin_id"]
                    and row["holdout_set"] == params["p_holdout_set"]
                    and row.get("is_latest")
                ):
                    row["is_latest"] = False
            new = self._defaults(
                "twin_quality_runs",
                {
                    "twin_id": params["p_twin_id"],
                    "session_id": params.get("p_session_id"),
                    "holdout_set": params["p_holdout_set"],
                    "arm": params.get("p_arm"),
                    "items_n": params.get("p_items_n"),
                    "mae": params["p_mae"],
                    "pct_within_1": params["p_pct_within_1"],
                    "correlations": params.get("p_correlations"),
                    "kept": params.get("p_kept"),
                    "repeats": params.get("p_repeats", 1),
                    "detail": params["p_detail"],
                    "model": params["p_model"],
                    "config_version": params.get("p_config_version", 1),
                    # `005`: a verdict with no fingerprint qualifies nobody under a live config.
                    "config_fingerprint": params.get("p_config_fingerprint"),
                    "is_latest": True,
                },
            )
            self._check_constraints("twin_quality_runs", new)
            self._rows("twin_quality_runs").append(new)
            return dict(new)
        if fn == "studio_run_record":
            # `ARCHITECTURE_UPDATE.md` §4.4. Same shape as the two above: demote the current holder
            # and append, in one step, so the mirror cannot show a state the SQL cannot reach.
            # `coalesce(..., '')` is how the partial unique index treats a null `version_code` (a
            # custom free-text ask) and a null `custom_change`, so the mirror matches it exactly.
            row = dict(params["p_row"])
            key = (
                row.get("twin_id"),
                row.get("version_code") or "",
                row.get("custom_change") or "",
            )
            for other in self._rows("studio_runs"):
                same = (
                    other.get("twin_id"),
                    other.get("version_code") or "",
                    other.get("custom_change") or "",
                )
                if same == key and other.get("is_latest_for_twin_version"):
                    other["is_latest_for_twin_version"] = False
            new = self._defaults(
                "studio_runs", {**row, "is_latest_for_twin_version": True}
            )
            self._check_constraints("studio_runs", new)
            self._rows("studio_runs").append(new)
            return dict(new)
        raise DbError(f"unknown rpc {fn}")


# ----------------------------------------------------------------------------- storage
#
# I16 — nothing durable lives on the filesystem. A raw survey object is written to Supabase
# Storage **before** any table row, so a failed insert leaves a replayable mirror rather than a
# row with no evidence behind it. `ingest/replay_raw.py` reads back from here.
#
# Storage lives in this file for the same reason the Postgres client does: `supabase` is imported
# in exactly one place (`CLAUDE.md` — Boundaries). Before this, the only client was a class inside
# `tools/generate_synthetic.py`, which put the SDK outside the boundary and left the Generator
# screen with nothing to call — so *Generate surveys* was shipped disabled.

#: The Edge Function's bucket, `supabase/functions/survey_intake/index.ts`. **One name, two
#: writers**: live intake writes real objects here and the Generator writes synthetic ones, and a
#: second name would split the mirror in two. Private — it holds raw driver responses.
RAW_BUCKET = "raw-surveys"


class StorageError(RuntimeError):
    """A raw object that could not be mirrored. **Never swallowed**: I16 is an ordering
    guarantee, and a batch that stored rows after a silent upload failure has rows whose
    `raw_object_path` points at nothing."""


@runtime_checkable
class StorageBackend(Protocol):
    """What a raw-object mirror must do. Two implementations, plus the tests' own fake.

    ``get`` and ``list`` are not conveniences: `ingest/replay_raw.py` is I16's whole payoff — it
    re-drives objects whose row never landed — and it has always called both. Without them the
    mirror is write-only and a failed insert is still a submission that is simply gone.

    They are also how a twin is built with everything the driver sent. `survey_submissions` has
    no column for age, gender, tenure, or any Part 4 answer, and none of Part 14's own-words
    questions is in the frozen 73-item register, so none of it is in `survey_answers` either.
    All of it is in the raw object, and `twins.background` exists to carry it (`docs/01` §6.2:
    "without this the persona loses the driver's own words").
    """

    name: str

    async def put(self, path: str, body: str) -> None:
        """Write one object, overwriting any object already at ``path``."""
        ...

    async def get(self, path: str) -> str:
        """Read one object back. Raises :class:`StorageError` if it is not there."""
        ...

    async def list(self, prefix: str = "") -> list[str]:
        """Every object path under ``prefix``, sorted, so a replay is reproducible."""
        ...


class SupabaseStorage:
    """`put(path, body)` over Supabase Storage. Upserts, so replaying a batch is idempotent."""

    name = "supabase"

    def __init__(self, url: str, key: str, bucket: str = RAW_BUCKET) -> None:
        from supabase import create_client

        self._bucket = create_client(url, key).storage.from_(bucket)
        self.bucket_name = bucket

    async def put(self, path: str, body: str) -> None:
        def _go() -> None:
            self._bucket.upload(
                path,
                body.encode("utf-8"),
                {"content-type": "application/json", "upsert": "true"},
            )

        try:
            # The SDK is synchronous. Off the event loop, so a 300-object batch cannot freeze
            # the Gradio UI for the duration (`docs/05` §8.4 rule 2).
            await asyncio.to_thread(_go)
        except Exception as exc:  # noqa: BLE001 — every failure mode is the same failure here.
            raise StorageError(
                f"could not write {path!r} to the {self.bucket_name!r} bucket: {exc}. "
                "Raw objects are written before rows (I16), so nothing was stored. If this says "
                "'Bucket not found', create it PRIVATE in the Supabase dashboard."
            ) from exc

    async def get(self, path: str) -> str:
        """One object's bytes as text. A missing object raises rather than returning empty."""

        def _go() -> bytes:
            return self._bucket.download(path)

        try:
            body = await asyncio.to_thread(_go)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(
                f"could not read {path!r} from the {self.bucket_name!r} bucket: {exc}"
            ) from exc
        return body.decode("utf-8") if isinstance(body, bytes) else str(body)

    async def list(self, prefix: str = "") -> list[str]:
        """Object paths under ``prefix``, sorted.

        Supabase lists one folder at a time and returns names relative to it, so the prefix is
        put back on each name — `replay_raw` compares these against `raw_object_path`, which is
        the full key, and a bare name would make every object look orphaned.
        """
        folder = prefix.rstrip("/")

        def _go() -> list[dict]:
            # 100 is the SDK default and would silently truncate a 300-object batch.
            return self._bucket.list(folder, {"limit": 10_000})

        try:
            entries = await asyncio.to_thread(_go)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(
                f"could not list {prefix!r} in the {self.bucket_name!r} bucket: {exc}"
            ) from exc
        names = [str(e["name"]) for e in entries if e.get("name")]
        return sorted(f"{folder}/{n}" if folder else n for n in names)


class InMemoryStorage:
    """The mirror when Supabase is not configured. Holds objects for the life of the process.

    **Not a durable mirror and it says so.** It exists so the Generator screen works against the
    in-memory backend the whole UI was built on, and so a test can assert the ordering I16
    requires without a network. A batch stored here vanishes on restart, exactly as the in-memory
    database does — the two fail together, which is the honest pairing.
    """

    name = "memory"

    def __init__(self) -> None:
        self.objects: dict[str, str] = {}

    async def put(self, path: str, body: str) -> None:
        self.objects[path] = body

    async def get(self, path: str) -> str:
        try:
            return self.objects[path]
        except KeyError:
            raise StorageError(
                f"no object at {path!r} in the in-memory mirror. It does not survive a restart, "
                "so a row written in an earlier process has no object here."
            ) from None

    async def list(self, prefix: str = "") -> list[str]:
        return sorted(p for p in self.objects if p.startswith(prefix))


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """The process-wide raw-object mirror. Supabase when configured, in-memory otherwise.

    Paired with :func:`get_backend` deliberately: a live database with an in-memory mirror would
    write durable rows pointing at objects that disappear on restart, and `replay_raw.py` would
    report every one of them as an orphan forever.
    """
    global _storage
    if _storage is None:
        if settings.db_configured:
            _storage = SupabaseStorage(settings.supabase_url, settings.supabase_service_key)
        else:
            log.warning(
                "SUPABASE_URL / SUPABASE_SERVICE_KEY not set — raw survey objects are mirrored "
                "in memory and are lost on restart."
            )
            _storage = InMemoryStorage()
    return _storage


def set_storage(storage: StorageBackend | None) -> None:
    """Install a mirror explicitly. Tests use this; the app does not."""
    global _storage
    _storage = storage


# --------------------------------------------------------------------------- singleton

_backend: DbBackend | None = None


def get_backend() -> DbBackend:
    """The process-wide backend. Supabase when configured, in-memory otherwise."""
    global _backend
    if _backend is None:
        if settings.db_configured:
            _backend = SupabaseBackend(
                settings.supabase_url,
                settings.supabase_service_key,
                max_concurrency=settings.db_max_concurrency,
            )
        else:
            log.warning(
                "SUPABASE_URL / SUPABASE_SERVICE_KEY not set — using the in-memory backend. "
                "Nothing is persisted across restarts."
            )
            _backend = InMemoryBackend()
    return _backend


def set_backend(backend: DbBackend | None) -> None:
    """Install a backend explicitly. Tests use this; the app does not."""
    global _backend
    _backend = backend


def require_live_backend() -> DbBackend:
    backend = get_backend()
    if backend.name != "supabase":
        raise DbError("this operation needs a live Supabase connection; set SUPABASE_* env vars")
    return backend
