"""M1 acceptance tests — the schema and its constraints. `docs/01` §6.

Several invariants are enforced in DDL rather than in a code path, "because a constraint cannot
be forgotten by a caller" (`docs/DECISIONS.md`). The in-memory backend mirrors those constraints,
so the invariant suite can prove they reject without a live Postgres — and every test here that
asserts a prohibition also proves the prohibition can fail (`docs/11` → Ground rules).

The two migration files are read as text: the SQL is the specification, and a constraint silently
missing from it would leave the in-memory mirror as the only guard.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from twinlab.db.client import DbError, InMemoryBackend

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = REPO_ROOT / "src" / "twinlab" / "db" / "migrations"


def _sql() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS.glob("*.sql"))
    )


# --------------------------------------------------------------------------- migrations


def test_migrations_are_numbered_and_additive():
    """`docs/01` §6: 001 is the 1.0 schema; 2.0 lands as 002 onward so a project migrates."""
    files = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    assert files[0] == "001_init.sql"
    assert len(files) >= 2
    sql = _sql().lower()
    # Nothing is dropped: `survey_responses` may hold v1 evidence and evidence is append-only
    # (I9). Dropping a *function* to replace its signature is not dropping data.
    assert "drop table" not in sql
    assert "drop column" not in sql


def test_every_2_0_table_is_created():
    """`docs/01` §6: the tables the revamp adds."""
    sql = _sql().lower()
    for table in (
        "constructs", "arms", "legacy_items", "survey_submissions", "survey_answers",
        "session_panel", "validity_results", "analysis_runs", "analysis_results",
        "synthetic_batches", "studio_runs", "agent_config_history",
    ):
        assert f"create table if not exists {table} (" in sql, table


def test_the_named_check_constraints_are_present():
    """The constraints `docs/01` §6 names, each closing an invariant or a prototype defect."""
    sql = _sql().lower()
    for constraint in (
        "runs_completed_has_twins",      # I15
        "validity_zero_n",               # I15
        "quality_has_items",             # I15
        "quality_h3_gates",
        "quality_h2_arm",
        "run_events_payload_small",      # storage budget; prompt bodies never stored (I11)
        "agent_no_native_output",        # ARCHITECTURE.md §3.2
        "analysis_bootstrap_floor",
        "analysis_has_cases",
    ):
        assert constraint in sql, constraint


def test_rls_is_enabled_on_every_new_table():
    """`docs/01` §6: RLS on every table; the server uses the service key. No anon access, ever."""
    sql = _sql().lower()
    for table in (
        "constructs", "arms", "legacy_items", "survey_submissions", "survey_answers",
        "session_panel", "validity_results", "analysis_runs", "analysis_results",
        "synthetic_batches", "studio_runs", "agent_config_history",
    ):
        assert f"alter table {table:<19} enable row level security;" in sql or (
            f"alter table {table} enable row level security;" in sql
        ), table


def test_the_event_payload_cap_is_eight_kilobytes():
    """`docs/01` §11: 32 KB → 8 KB. Load-bearing, not tidiness — see `docs/10`."""
    assert "pg_column_size(payload) <= 8192" in _sql()


# --------------------------------------------------------------------------- I15 in DDL


async def test_a_completed_run_with_no_twins_is_rejected(backend):
    """I15: `twins_n = 0` is `failed`, never `completed` with an index of 0.000.

    The prototype's `Designs` sheet stored exactly such rows as findings. `runs_completed_has_twins`
    makes it impossible.
    """
    with pytest.raises(DbError, match="runs_completed_has_twins"):
        await backend.insert("runs", [{
            "run_id": "r1", "session_id": "s1", "version_code": "01000",
            "status": "completed", "twins_n": 0,
        }])


async def test_a_failed_run_with_no_twins_is_allowed(backend):
    """The same run recorded as `failed` is the correct outcome, and is accepted."""
    rows = await backend.insert("runs", [{
        "run_id": "r1", "session_id": "s1", "version_code": "01000",
        "status": "failed", "twins_n": 0,
    }])
    assert rows[0]["status"] == "failed"


async def test_completing_a_run_through_the_pointer_flip_needs_twins(backend):
    """I15 at the RPC too, so the path the orchestrator actually uses is guarded."""
    await backend.insert("runs", [{
        "run_id": "r1", "session_id": "s1", "version_code": "01000", "status": "asking",
    }])
    with pytest.raises(DbError, match="I15"):
        await backend.rpc("runs_complete", {
            "p_run_id": "r1", "p_metrics": {}, "p_index": 0.0, "p_analysis": "",
            "p_twins_n": 0,
        })


async def test_a_validity_test_on_zero_twins_must_be_inconclusive(backend):
    """I15: the prototype emitted `PASS: twins are about their own driver` on zero twins."""
    row = {
        "test_id": "wrong_person", "twins_n": 0, "mode": "live", "provider": "ollama",
        "model": "m", "statistics": {}, "verdict": "PASS",
        "headline": "twins are about their own driver", "detail": "", "config_version": 1,
    }
    with pytest.raises(DbError, match="validity_zero_n"):
        await backend.insert("validity_results", [row])

    written = await backend.insert("validity_results", [{**row, "verdict": "INCONCLUSIVE"}])
    assert written[0]["verdict"] == "INCONCLUSIVE"


async def test_a_quality_run_on_no_items_is_rejected(backend):
    """I15 for the quality gate: a score computed over nothing is not a score."""
    with pytest.raises(DbError, match="quality_has_items"):
        await backend.insert("twin_quality_runs", [{
            "twin_id": "t1", "holdout_set": "H3", "items_n": 0, "mae": 0.5,
            "pct_within_1": 0.9, "kept": True, "detail": [], "model": "m",
        }])


# --------------------------------------------------------------------------- holdout shape


async def test_h3_carries_kept_and_h2_does_not(backend):
    """`docs/01` §6.3: H3 gates, H2 does not. `quality_h3_gates` is the equality, both ways."""
    with pytest.raises(DbError, match="quality_h3_gates"):
        await backend.insert("twin_quality_runs", [{
            "twin_id": "t1", "holdout_set": "H3", "items_n": 18, "mae": 0.5,
            "pct_within_1": 0.9, "kept": None, "detail": [], "model": "m",
        }])
    with pytest.raises(DbError, match="quality_h3_gates"):
        await backend.insert("twin_quality_runs", [{
            "twin_id": "t1", "holdout_set": "H2", "arm": "CON1", "items_n": 16, "mae": 0.5,
            "pct_within_1": 0.9, "kept": True, "detail": [], "model": "m",
        }])


async def test_an_h2_row_must_record_the_arm_the_human_saw(backend):
    """`docs/01` §5.2: showing a twin a different arm than its human saw is a bug.

    `twin_quality_runs.arm` exists so it is checkable after the fact, so it cannot be null.
    """
    with pytest.raises(DbError, match="quality_h2_arm"):
        await backend.insert("twin_quality_runs", [{
            "twin_id": "t1", "holdout_set": "H2", "items_n": 16, "mae": 0.5,
            "pct_within_1": 0.9, "kept": None, "detail": [], "model": "m",
        }])


async def test_the_quality_pointer_flip_demotes_the_previous_latest(backend):
    """I9: append a new row, demote the old one in the same transaction. Nothing is erased."""
    common = {
        "p_twin_id": "t1", "p_session_id": None, "p_holdout_set": "H3", "p_arm": None,
        "p_items_n": 18, "p_pct_within_1": 0.9, "p_correlations": None, "p_kept": True,
        "p_repeats": 3, "p_detail": [], "p_model": "m", "p_config_version": 1,
    }
    await backend.rpc("quality_run_record", {**common, "p_mae": 0.80})
    await backend.rpc("quality_run_record", {**common, "p_mae": 0.62})

    rows = await backend.select("twin_quality_runs")
    assert len(rows) == 2, "the superseded row is kept (I9)"
    latest = [r for r in rows if r["is_latest"]]
    assert len(latest) == 1
    assert latest[0]["mae"] == 0.62


# --------------------------------------------------------------------------- other gates


async def test_native_output_cannot_be_configured(backend):
    """`ARCHITECTURE.md` §3.2 and I13.

    Ollama Cloud accepts a JSON schema and silently does not enforce it, so `NativeOutput` fails
    invisibly. The schema forbids even storing it as a configuration.
    """
    row = {
        "agent_id": "twin", "name": "Twin", "role": "twin", "model": {}, "system_prompt": "",
        "input_schema": "X", "output_schema": "Y", "output_mode": "native",
    }
    with pytest.raises(DbError, match="agent_no_native_output"):
        await backend.insert("agent_configs", [row])
    for mode in ("tool", "prompted"):
        written = await backend.insert("agent_configs", [{**row, "output_mode": mode}])
        assert written[0]["output_mode"] == mode


async def test_the_bootstrap_floor_is_thirty(backend):
    """`ARCHITECTURE.md` §10.7: 30 is the prototype's UI floor, kept and enforced."""
    row = {
        "population": "real", "screening": "strict", "bootstrap_samples": 29, "seed": 1,
        "n_cases": 100, "engine_version": "0.1", "config": {},
    }
    with pytest.raises(DbError, match="analysis_bootstrap_floor"):
        await backend.insert("analysis_runs", [row])
    with pytest.raises(DbError, match="analysis_has_cases"):
        await backend.insert("analysis_runs", [{**row, "bootstrap_samples": 5000, "n_cases": 0}])


async def test_submission_generated_columns_are_computed(backend):
    """`docs/01` §6.2: `speeder` and `mc_correct` are generated, not supplied by a caller."""
    rows = await backend.insert("survey_submissions", [{
        "submission_id": "UBR-1", "data_type": "REAL", "eligible": True, "consented": True,
        "consent_twin": True, "attention_passed": True, "completion_seconds": 300,
        "outcome": "complete", "arm": "CON1", "mc_answer": "CON1",
        "raw_object_path": "raw/UBR-1.json", "submitted_at": "2026-09-28T00:00:00Z",
    }])
    assert rows[0]["speeder"] is True
    assert rows[0]["mc_correct"] is True

    rows = await backend.insert("survey_submissions", [{
        "submission_id": "UBR-2", "data_type": "REAL", "eligible": True, "consented": True,
        "consent_twin": True, "attention_passed": True, "completion_seconds": 900,
        "outcome": "complete", "arm": "CON1", "mc_answer": "REP1",
        "raw_object_path": "raw/UBR-2.json", "submitted_at": "2026-09-28T00:00:00Z",
    }])
    assert rows[0]["speeder"] is False
    assert rows[0]["mc_correct"] is False


def test_a_direct_supabase_import_outside_db_client_is_rejected():
    """The `supabase` contract is scoped to direct imports in M1 — prove it still rejects.

    `services/ → db/client.py → supabase` is the intended chain (the layer table allows it), so
    the contract sets ``allow_indirect_imports``. That relaxation would be worthless if a
    *direct* `import supabase` from another layer then slipped through, so this appends one and
    checks the linter fails.
    """
    pytest.importorskip("importlinter", reason="import-linter is a declared dependency")
    target = REPO_ROOT / "src" / "twinlab" / "services" / "config.py"
    original = target.read_text(encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(["src", "."])}
    try:
        target.write_text(original + "\nimport supabase  # noqa: E402,F401\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-c",
             "from importlinter.cli import lint_imports_command as c; c.main([])"],
            cwd=REPO_ROOT, capture_output=True, text=True, env=env,
        )
    finally:
        target.write_text(original, encoding="utf-8")

    assert result.returncode != 0, "a direct supabase import from services/ was not rejected"
    assert "BROKEN" in (result.stdout + result.stderr).upper()


async def test_a_row_needing_a_supplied_key_does_not_get_one_invented(backend):
    """Reference rows carry their own opaque stable keys and must not be auto-assigned."""
    written = await backend.insert("survey_items", [{"item_id": "FAIR1", "part": 7}])
    assert written[0]["item_id"] == "FAIR1"
    fresh = InMemoryBackend()
    made = await fresh.insert("runs", [{"session_id": "s", "version_code": "00000"}])
    assert made[0]["run_id"], "runs.run_id is generated by the database"


# ------------------------------------------------- every seeded column exists in the DDL


def _columns_by_table(sql: str) -> dict[str, set[str]]:
    """``table -> column names``, from `create table` bodies plus `alter table ... add column`.

    Deliberately textual, like the rest of this module: the SQL *is* the specification, and a
    column the seeder writes but the schema does not declare is invisible to every test in the
    suite — the in-memory backend stores whatever dict it is handed.
    """
    import re

    body = re.sub(r"--[^\n]*", "", sql)
    tables: dict[str, set[str]] = {}
    for match in re.finditer(
        r"create table if not exists (\w+)\s*\((.*?)\n\);", body, re.S
    ):
        columns: set[str] = set()
        depth = 0
        current = ""
        for char in match.group(2):
            if char == "(":
                depth += 1
            if char == ")":
                depth -= 1
            if char == "," and depth == 0:
                columns.add(current)
                current = ""
            else:
                current += char
        columns.add(current)
        named = set()
        for column in columns:
            first = column.strip().split()
            if not first:
                continue
            if first[0].lower() in (
                "primary", "unique", "foreign", "check", "constraint", "exclude",
            ):
                continue
            named.add(first[0])
        tables[match.group(1)] = named
    for match in re.finditer(
        r"alter table (\w+)\s+add column(?: if not exists)?\s+(\w+)", body, re.I
    ):
        tables.setdefault(match.group(1), set()).add(match.group(2))
    return tables


def test_every_seeded_column_exists_in_the_migrations():
    """A seeded key with no column fails against Postgres and is invisible in memory.

    `gaps` was the live case: `gaps.json` carries both `gap_id` and `criterion_id`, `Gap` declares
    both, and `model_dump()` sent both — but the DDL stores the relation as the primary key's own
    foreign key and has no `criterion_id` column, so seeding a real project died on

        PGRST204: Could not find the 'criterion_id' column of 'gaps' in the schema cache

    while the whole suite stayed green, because `InMemoryBackend` is a dict. This is the general
    guard, not a patch for that one table.
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.seed_db import build_rows

    declared = _columns_by_table(_sql())
    offenders: dict[str, set[str]] = {}
    for table, rows in build_rows(reference()).items():
        if not rows:
            continue
        assert table in declared, f"{table} is seeded but no migration creates it"
        keys: set[str] = set()
        for row in rows:
            keys |= set(row)
        extra = keys - declared[table]
        if extra:
            offenders[table] = extra
    assert not offenders, f"seeded keys with no column: {offenders}"


def test_the_gaps_projection_refuses_a_row_whose_criterion_id_differs():
    """The redundancy is proved, not assumed — a differing value has nowhere to go and must raise.

    A gate that cannot fail is not a gate (`HANDOFF.md` §0.3 item 6).
    """
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.seed_db import SeedError, _gap_rows

    ref = reference()
    first = next(iter(ref.gaps))

    class _Tampered:
        gaps = {
            **ref.gaps,
            first: ref.gaps[first].model_copy(update={"criterion_id": "9.9.z"}),
        }

    with pytest.raises(SeedError, match="differs"):
        _gap_rows(_Tampered())


def test_every_filter_operator_resolves_to_a_real_postgrest_method():
    """`Filter`'s vocabulary must exist on the builder. `in` and `is` are Python keywords.

    postgrest spells them `in_` and `is_`, so `getattr(query, "in")` raised `AttributeError` at
    the boundary — which `SupabaseBackend._run` retried four times and reported as a database
    failure. `InMemoryBackend` implements both by name, so the whole suite passed and the two
    callers (`services.surveys.delete_synthetic` and the log tree's ancestor lookup) failed only
    against a real project.

    Asserted against the SDK rather than a hard-coded list, so a rename upstream fails here.
    """
    import typing

    from postgrest.base_request_builder import BaseFilterRequestBuilder

    from twinlab.db.client import FILTER_METHODS, Filter

    operators = typing.get_args(typing.get_args(Filter)[0])
    assert operators, "Filter's operator literal could not be read"
    for op in operators:
        method = FILTER_METHODS.get(op, op)
        assert hasattr(BaseFilterRequestBuilder, method), (
            f"filter {op!r} maps to {method!r}, which postgrest does not have"
        )


# ------------------------------------------------- PostgREST's row cap


def _capped_server(total: int, cap: int = 1000):
    """A `fetch(start, count)` that behaves like PostgREST: never more than `cap` rows, no error."""
    calls: list[tuple[int, int]] = []

    async def fetch(start: int, count: int) -> list[dict]:
        calls.append((start, count))
        end = min(start + min(count, cap), total)
        return [{"i": i} for i in range(start, max(start, end))]

    return fetch, calls


@pytest.mark.parametrize("total", [0, 1, 999, 1000, 1001, 2000, 21900])
async def test_a_read_larger_than_the_row_cap_is_paged_not_truncated(total):
    """Supabase caps a response at `db-max-rows` (1,000) and returns a 200, not an error.

    `select` issued one request and returned whatever came back, so a read of a large table was
    silently short: `survey_answers` at 300 synthetic respondents is 21,900 rows and 1,000 came
    back. Every statistic `stats/dataset.py` builds from those rows would have been computed on a
    fifth of the data, with nothing anywhere saying so — the golden gate passes because it runs on
    in-memory fixtures and `InMemoryBackend` has no cap. A plausible number that is wrong is the
    worst failure this system can have.
    """
    from twinlab.db.client import paged_select

    fetch, _ = _capped_server(total)
    rows = await paged_select(fetch)

    assert len(rows) == total
    assert [r["i"] for r in rows] == list(range(total)), "paging dropped or repeated rows"


async def test_paging_honours_a_limit_without_over_fetching():
    """A limited read must not walk the whole table to satisfy a small `limit`."""
    from twinlab.db.client import paged_select

    fetch, calls = _capped_server(21900)

    assert len(await paged_select(fetch, limit=5)) == 5
    assert calls == [(0, 5)], "a limited read made more than one request"

    fetch, calls = _capped_server(21900)
    assert len(await paged_select(fetch, limit=2500)) == 2500
    assert sum(count for _, count in calls) == 2500


async def test_paging_stops_on_a_short_page_rather_than_a_row_count():
    """The loop ends on the real last page, so a lower server cap costs requests, not rows."""
    from twinlab.db.client import paged_select

    fetch, calls = _capped_server(250, cap=100)
    rows = await paged_select(fetch, page=100)

    assert len(rows) == 250
    assert calls == [(0, 100), (100, 100), (200, 100)]


# ------------------------------------------------------- the mirror refuses an unknown column


def test_table_columns_is_derived_from_the_migrations_not_hand_written():
    """`TABLE_COLUMNS` must come from the DDL, so it cannot drift from the schema it mirrors."""
    from twinlab.db.client import TABLE_COLUMNS, _parse_ddl_columns

    parsed = _parse_ddl_columns(_sql())

    assert set(TABLE_COLUMNS) == set(parsed), "the derived map lost or invented a table"
    for table, columns in parsed.items():
        assert TABLE_COLUMNS[table] == frozenset(columns)


def test_runs_has_started_at_and_has_never_had_created_at():
    """The column five callers ordered by. `runs` timestamps `started_at` / `finished_at`.

    Pinned because the mistake is natural — twelve other tables *do* carry `created_at` — and
    because the whole suite passed while it was wrong.
    """
    from twinlab.db.client import TABLE_COLUMNS

    assert "started_at" in TABLE_COLUMNS["runs"]
    assert "finished_at" in TABLE_COLUMNS["runs"]
    assert "created_at" not in TABLE_COLUMNS["runs"]


async def test_in_memory_select_rejects_a_column_the_schema_does_not_have():
    """The gate that would have caught `runs.created_at`. A gate that cannot fail is not a gate.

    Postgres answers `42703 undefined_column`; before this the mirror answered `None` and sorted
    happily, so ordering `runs` by a column that has never existed passed 684 tests and failed
    only against the researcher's live project.
    """
    db = InMemoryBackend()

    with pytest.raises(DbError, match="undefined_column"):
        await db.select("runs", [("eq", "status", "completed")], order=("created_at", True))

    with pytest.raises(DbError, match="undefined_column"):
        await db.select("runs", [("eq", "created_at", "x")])

    # The real column is accepted, so the check is discriminating rather than blanket.
    kept = await db.select("runs", [("eq", "status", "completed")], order=("started_at", True))
    assert kept == []


async def test_in_memory_write_paths_reject_an_unknown_column_too():
    """A misspelled column on the way in is as invisible as one on the way out."""
    db = InMemoryBackend()

    with pytest.raises(DbError, match="undefined_column"):
        await db.insert("runs", [{"version_code": "01000", "creatd_at": "typo"}])
    with pytest.raises(DbError, match="undefined_column"):
        await db.update("runs", {"nonesuch": 1}, [("eq", "status", "pending")])
    with pytest.raises(DbError, match="undefined_column"):
        await db.delete("runs", [("eq", "nonesuch", 1)])
    with pytest.raises(DbError, match="undefined_column"):
        await db.count("runs", [("eq", "nonesuch", 1)])


def test_a_table_outside_the_ddl_is_not_checked():
    """A scratch table a test stands up must not be failed for columns no migration declares."""
    from twinlab.db.client import InMemoryBackend as B

    B._check_columns("not_a_real_table", ["whatever"], "test")  # must not raise


def test_no_source_file_reads_a_column_the_schema_does_not_have():
    """Static sweep of every literal table/column pair in `src/`, against the DDL.

    The runtime gate above only fires on a code path a test exercises. This one reads the source,
    so an unexercised handler — which is exactly what `services.status.tested_codes` was — cannot
    carry a bad column into a release.
    """
    import ast

    from twinlab.db.client import TABLE_COLUMNS

    ops = {"eq", "neq", "in", "is", "gt", "gte", "lt", "lte"}
    methods = {"select", "insert", "update", "upsert", "delete", "count"}
    offences: list[str] = []

    def literal(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else None
            if name not in methods:
                continue
            table = literal(node.args[0])
            known = TABLE_COLUMNS.get(table) if table else None
            if known is None:
                continue
            columns: set[str] = set()
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                for sub in ast.walk(arg):
                    if not isinstance(sub, ast.Tuple):
                        continue
                    values = [literal(e) for e in sub.elts]
                    # ("eq", "col", value)
                    if len(values) == 3 and values[0] in ops and values[1]:
                        columns.add(values[1])
                    # order=("col", descending)
                    if (
                        len(values) == 2
                        and values[0]
                        and isinstance(sub.elts[1], ast.Constant)
                        and isinstance(sub.elts[1].value, bool)
                    ):
                        columns.add(values[0])
            for column in sorted(columns - known):
                offences.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno} reads {table}.{column}"
                )

    assert not offences, "columns that do not exist in the DDL:\n  " + "\n  ".join(offences)
