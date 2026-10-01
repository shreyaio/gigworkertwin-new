# 03 — Backend

FastAPI surface, the orchestrator state machine, resume, and caching.

## 1. Layering

```
UI (Gradio)  ─┐
              ├─► services/          ← the only thing both callers touch
HTTP (API)   ─┘        │
                       ├─► orchestrator/   (session state machine)
                       ├─► variant/        (lookup, render, check)
                       ├─► persona/        (builder)
                       ├─► analysis/       (metrics, interactions, report)
                       └─► db/repo_*       (the ONLY place SQL lives)
```

**Rules.** No SQL outside `db/`. No `supabase` import outside `db/client.py`. No LLM call outside
`agents/`. A Gradio handler calls a service and nothing deeper. Services are `async` and return
Pydantic models, never raw dicts or DB rows.

## 2. HTTP API

Everything the UI does is available as JSON, so the platform is scriptable and testable without
driving the UI.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sessions` | Create. Body: `name`, `iterations`, `start_code`, optional config overrides. |
| `GET` | `/api/sessions` | List, newest first. |
| `GET` | `/api/sessions/{id}` | Detail + progress. |
| `POST` | `/api/sessions/{id}/start` | Start, or resume from `cursor_index`. |
| `POST` | `/api/sessions/{id}/stop` | Cooperative stop at the next checkpoint. |
| `DELETE` | `/api/sessions/{id}` | Delete session and cascade. |
| `GET` | `/api/sessions/{id}/events` | `?after_id=` — the log tail. Powers the Timer poll. |
| `GET` | `/api/events/{event_id}` | One event with full payload for the side panel. |
| `GET` | `/api/versions/{code}` | Dial-board bundle: DeltaSpec, "what twins are told", cache status. |
| `POST` | `/api/versions/{code}/ask` | Ask the twins. Returns cached run, or starts one. `?rerun=true` forces. |
| `GET` | `/api/versions/{code}/result` | Latest completed run + metrics + analysis. |
| `GET` | `/api/results/grid` | All 243 cells: index value or `null`. Powers the heatmap. |
| `GET` | `/api/results/interactions` | Computable interactions only. |
| `GET` | `/api/twins` | List + latest quality. |
| `GET` | `/api/twins/{id}` | Persona, baseline answers, per-version answers. |
| `POST` | `/api/twins/quality` | Body: `twin_ids: [] \| null` (null = all). Starts a quality session. |
| `POST` | `/api/survey/intake` | HMAC-signed Google Form webhook. |
| `GET` | `/api/config/agents` · `PUT` | Agent registry read/write. |
| `GET` | `/api/config/twin` · `PUT` | TwinConfig read/write. |

## 3. The orchestrator state machine

One session runs one loop. The loop is a coroutine owned by a `SessionRunner`, held in a
process-level registry keyed by `session_id`.

```
                    ┌──────────► paused ──────────┐
                    │                             ▼
created ──► running ┼──────────► stopped     (start → running, from cursor)
                    ├──────────► completed
                    └──────────► failed
```

### 3.1 Run stages

Every version code passes through these, in order. **Each is a checkpoint.**

| Stage | Does | Emits | Idempotent? |
|---|---|---|---|
| `lookup` | version_code → DeltaSpec | parent + 1 child | yes, pure |
| `render` | DeltaSpec → 5 lever paragraphs | parent + 1 child per non-cached lever | yes, cache-keyed |
| `check` | CheckerReport | parent + 1 child per gate | yes |
| `ask` | 37 answers × N twins | parent + 1 child per twin | yes, per (run, twin, wording) |
| `analyse` | metrics, index, LLM analysis | parent + children | yes |

Plus two session-level stages that run once: `ingestion` (load reference + twins into memory) and
`reconstruction` (build any missing persona passages).

### 3.2 The loop

```python
async def run_session(session_id: UUID) -> None:
    s = await repo_sessions.get(session_id)
    await repo_sessions.set_status(session_id, "running")
    try:
        await stage_ingestion(s)
        await stage_reconstruction(s)          # emits 'reconstruction (T07)' per twin

        if s.cursor_index is None:             # fresh session: control cells first
            await execute_run(s, "00000")
            await execute_run(s, "SHAM")
            await repo_sessions.set_cursor(session_id, index_from_code(s.start_code))

        while s.completed < s.iterations:
            if await should_stop(session_id):
                await repo_sessions.set_status(session_id, "paused"); return
            code = code_from_index(s.cursor_index)
            await execute_run(s, code)
            s.completed += 1
            s.cursor_index = (s.cursor_index + 1) % 243
            await repo_sessions.advance(session_id, s.cursor_index, s.completed)

        await repo_sessions.set_status(session_id, "completed")
    except Exception as e:
        await repo_sessions.fail(session_id, repr(e))
        raise
```

`execute_run` resumes mid-flight: it reads the existing `runs` row for `(session, code)` and skips
any stage already recorded as done.

```python
async def execute_run(s: Session, code: str) -> Run:
    run = await repo_runs.get_or_create(s.session_id, code)
    if run.status == "completed":
        return run                                   # already done in this session
    if run.status in ("pending",):
        spec = lookup(code)                          # I1
        await repo_runs.set_status(run, "rendering")
    variant = await render_and_check(spec, s.config.style_version)   # cached (I4)
    if not variant.checker["passed"]:
        return await repo_runs.fail(run, "checker failed")
    await repo_runs.attach_variant(run, variant)
    await ask_all_twins(run, variant, s.config)      # skips twins already answered
    await analyse(run)
    return await repo_runs.complete(run)             # flips is_latest_for_version
```

### 3.3 Stop, pause, resume

**Stop is cooperative.** `POST /stop` sets a flag; the loop checks it at every checkpoint and exits
after the current unit, leaving `cursor_index` at the next unstarted cell. It never kills mid-LLM-
call, so no partial answer is written.

**Resume is just start.** `POST /start` on a `paused` or `stopped` session reads `cursor_index` and
continues. Because every stage is idempotent and cache-keyed, a half-finished run resumes without
re-paying for completed work: rendered paragraphs are cached, and `twin_answers` has a unique index
on `(run_id, twin_id, wording)`, so answered twins are skipped.

**Crash recovery.** On startup:

```python
async def resume_interrupted_sessions():
    for s in await repo_sessions.by_status("running"):
        await repo_sessions.set_status(s.session_id, "paused")
        emit(s.session_id, stage="control", label="session interrupted; paused for resume",
             status="error")
```

Sessions found `running` at boot were killed by a Space restart. They are marked `paused`, not
auto-restarted — the researcher decides, and the logs say plainly what happened.

### 3.4 Concurrency

- **One `SessionRunner` per session**, at most one *active* session per process (*CONFIG*
  `max_active_sessions`, default 1). A second start is rejected with a clear message, not queued
  silently.
- **Twins run in a bounded pool** inside `ask`, `asyncio.Semaphore(max_concurrency)`, default 4.
- **429 / 5xx** → exponential backoff, 3 attempts, then that twin fails for that cell only.
- **Gradio handlers never await LLM work.** They call a service that enqueues and returns
  immediately; the Timer polls.

## 4. Caching

Three layers, each with an explicit key. Nothing else is cached.

| What | Key | Table | Invalidated by |
|---|---|---|---|
| Lever paragraph | `(lever, dial, style_version)` | `lever_paragraphs` | bumping `style_version` |
| Variant | `(version_code, style_version)` | `variants` | bumping `style_version` |
| Run result | `version_code` where `is_latest_for_version` | `runs` | a rerun |

### 4.1 "Ask the twins" — the dial board contract

```python
async def ask_twins(code: str, rerun: bool = False) -> AskResult:
    if not rerun:
        cached = await repo_runs.latest_completed(code)
        if cached:
            return AskResult(status="cached", run=cached)      # UI: badge + "Rerun?" button
    session = await create_session(name=f"{'Rerun' if rerun else 'Ask'} {code}",
                                   iterations=1, start_code=code)
    await start_session(session.session_id)                    # logs appear in the Logs tab
    return AskResult(status="started", session_id=session.session_id)
```

A rerun creates a real session, so its logs are visible like any other. When it completes, the new
`runs` row takes `is_latest_for_version` and the previous holder is demoted **in the same
transaction** — superseded, never deleted (I9).

```sql
-- repo_runs.complete()
begin;
  update runs set is_latest_for_version = false
   where version_code = $code and is_latest_for_version;
  update runs set status = 'completed', finished_at = now(), is_latest_for_version = true
   where run_id = $run_id;
commit;
```

## 5. Events and the log tree

```python
async def emit(session_id, *, stage, label, status="running", agent=None,
               run_id=None, parent_event_id=None, payload=None) -> int:
    row = await repo_events.insert(...)
    if logfire_enabled:
        with logfire.span(stage, **(payload or {})) as span:
            await repo_events.set_span(row.event_id, span.span_id)
    return row.event_id
```

**Pattern:** a stage opens a parent event with `status='running'`, does its work emitting children,
then updates the parent to `ok` or `error`. The label of a parent is **rewritten in place** as work
progresses — this is what gives the researcher `reconstruction (T07)` ticking through twin ids on a
single row:

```python
parent = await emit(sid, stage="reconstruction", label="reconstruction")
for twin in twins:
    await repo_events.set_label(parent, f"reconstruction ({twin.twin_id})")
    await emit(sid, stage="reconstruction", label=twin.twin_id, status="ok",
               parent_event_id=parent, payload={"passage": passage, "hash": h})
await repo_events.set_status(parent, "ok")
```

`payload` carries whatever the side panel shows: `input`, `output`, `prompt`, `prompt_tokens`,
`completion_tokens`, `latency_ms`, `model`. For a reconstruction child it is the passage itself.

**Payload size.** Cap at 32 KB; anything larger is truncated with `payload.truncated = true` and the
full artifact is fetched from its own table (`variants`, `twin_answers`, `twins.persona_passage`)
when the panel opens.

## 6. Survey intake

```python
@router.post("/survey/intake")
async def intake(request: Request, x_signature: str = Header(...)):
    raw = await request.body()
    expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(401, "bad signature")
    payload = json.loads(raw)

    # 1. mirror first — the immutable record of what was submitted
    path = Path("data/temp") / f"survey_{payload['response_id']}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    # 2. then the DB
    twin = await survey_intake.upsert(payload)          # maps Form fields -> item_ids
    if not twin.consent_twin:
        return {"status": "stored", "twin": None}       # response kept, no twin built

    passage = build_persona(twin.twin_id)
    await repo_twins.set_persona(twin.twin_id, passage, sha256(passage))
    return {"status": "ok", "twin_id": twin.twin_id}
```

**Mirror before DB**, so a DB failure leaves a replayable file. `ingest/replay_temp.py` re-posts any
mirror without a matching `twins` row.

**Field mapping.** The Google Form's question titles are mapped to `item_id` in
`config/form_map.yaml` — a two-column file, Form title → item id. Keeping it in config means a
re-worded Form question is a config edit, not a code change. The mapper **fails loudly** on an
unmapped question rather than dropping it.

## 7. Errors

| Class | Behaviour |
|---|---|
| `ConfigError` | Startup fails. Never runs with a bad agent config. |
| `CheckerFailure` | Cell marked `failed`, logged, loop continues. |
| `PersonaTemplateMissing` | Reconstruction fails for that twin, logged, loop continues. |
| `ProviderRateLimit` | Backoff, 3 attempts, then that twin fails for that cell only. |
| `SchemaValidationError` | Retry once, then fail that unit. |

Every one writes a `run_events` row with `status='error'` and the exception in `payload`, so a
failure is visible in the UI and not only in stderr.
