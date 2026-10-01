# 04 — Backend

The service layer, the orchestrator state machine, jobs, rate limiting, caching, resume.

Normative.

---

## 1. Layering

```
UI (Gradio pages)  ─┐
                    ├─► services/          ← the only layer both callers touch
API (FastAPI)      ─┘        │
                             ├─► orchestrator/   session state machine, panel, budget
                             ├─► variant/        lookup, render, check
                             ├─► persona/        builder
                             ├─► analysis/       metrics, interactions, report
                             ├─► stats/          PLS-SEM
                             ├─► validity/       the eight tests
                             ├─► generator/      synthetic surveys
                             └─► db/repo_*       the ONLY place SQL lives
```

**Rules, enforced by an import-linter test in CI:**

- No SQL outside `db/`. No `supabase` import outside `db/client.py`.
- No LLM call outside `agents/`.
- `services/` imports neither `gradio` nor `fastapi`. If it did, the two callers would diverge.
- A Gradio handler calls a service and nothing deeper.
- Services are `async`, take and return Pydantic models, never raw dicts or DB rows.

**`api/` is optional and must stay optional** (`ARCHITECTURE.md` §8.2 rule 3). It is a thin router
over `services/` so the platform is scriptable and testable without driving the UI. No feature may
depend on an HTTP route existing, because the free Gradio-SDK deployment may not expose them.

---

## 2. The service layer

This is the real API. Every screen in `docs/06` maps onto functions here, and every function is
callable from a test with no UI and no server.

| Module | Key functions |
|---|---|
| `dashboard` | `counts()` — the Main Menu's "Where things stand" |
| `surveys` | `list()`, `counts_by_type()`, `fieldwork_summary()`, `delete_synthetic()` |
| `generator` | `preview(config)`, `generate(config)`, `batches()` |
| `twins` | `list()`, `get(id)`, `import_from_surveys(filter)`, `create_manual(profile)`, `persona(id)` |
| `quality` | `run(twin_ids, holdout)`, `latest(twin_id)`, `summary()` |
| `validation` | `run_h2(twin_ids)`, `summary()`, `per_twin()` |
| `validity` | `run(test_id, n)`, `results()` |
| `versions` | `preview(code)`, `ask(code, rerun)`, `result(code)` |
| `sessions` | `create()`, `start()`, `stop()`, `events(after_id)`, `budget(params)` |
| `results` | `grid()`, `detail(code)`, `interactions()`, `tested_table()` |
| `studio` | `ask(twin_id, change, questions, include_battery)` |
| `agents` | `list()`, `save(id, cfg)`, `restore(id)`, `freeze(id)`, `test(id, params)`, `history()` |
| `stats` | `run(config)`, `stage(analysis_id, stage)`, `export(format)` |
| `config` | `get(key)`, `put(key, value)` |
| `research` | `model()`, `hypotheses()`, `constructs()`, `references()`, `to_doc()` |

### 2.1 The one rule for Gradio handlers

**Never await LLM work in a handler's synchronous path** (CLAUDE.md rule 9). A handler that calls
a model blocks the Gradio worker; with one concurrent provider slot it blocks the whole app for
the length of a sweep.

```
handler ──► service.enqueue()  ──► returns a job id immediately
   │
   └──► gr.Timer polls service.job_status(job_id) and service.events(after_id)
```

Handlers are `async def` and never call `asyncio.run` — the latter closes its loop and takes any
enqueued session task with it.

---

## 3. The orchestrator

### 3.1 States

```
                    ┌──────────► paused ──────────┐
                    │                             ▼
created ──► running ┼──────────► stopped     (start → running, from cursor)
                    ├──────────► completed
                    └──────────► failed
```

One `SessionRunner` per session, held in a process-level registry keyed by `session_id`. **At most
one active session per process** (CONFIG `max_active_sessions`, default 1). A second start is
rejected with a clear message, never queued silently — with one provider slot, two concurrent
sessions would interleave and both would crawl.

### 3.2 Stages

Every version code passes through these in order. **Each is a checkpoint.**

| Stage | Does | Emits | Idempotent |
|---|---|---|---|
| `lookup` | version_code → DeltaSpec | parent + 1 child | yes, pure |
| `render` | DeltaSpec → 5 paragraphs | parent + 1 child per non-cached lever | yes, cache-keyed |
| `check` | CheckerReport | parent + 1 child per gate | yes |
| `ask` | 37 answers × K twins | parent + 1 child per twin | yes, per (run, twin, wording) |
| `analyse` | metrics, index, prose | parent + children | yes |

Plus three session-level stages that run once: `ingestion` (load reference and twins), `panel`
(draw and freeze the analysis panel — I14), and `reconstruction` (build any missing personas).

### 3.3 The loop

```python
async def run_session(session_id: UUID) -> None:
    s = await repo_sessions.get(session_id)
    await repo_sessions.set_status(session_id, "running")
    try:
        await stage_ingestion(s)
        await stage_panel(s)                   # idempotent: reads session_panel if present
        await stage_reconstruction(s)

        if s.cursor_index is None:             # fresh session: control cells first
            await execute_run(s, "00000")
            await execute_run(s, "SHAM")
            await repo_sessions.set_cursor(session_id, index_from_code(s.start_code))

        while s.completed < s.iterations:
            if await should_stop(session_id):
                await repo_sessions.set_status(session_id, "paused")
                return
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
    spec = lookup(code)                              # I1, pure, cheap to redo
    variant = await render_and_check(spec, s.config.style_version)   # cached, I4
    if not variant.checker["passed"]:
        return await repo_runs.fail(run, "checker failed")
    await repo_runs.attach_variant(run, variant)
    await ask_panel(run, variant, s)                 # skips twins already answered
    if run.twins_n == 0:
        return await repo_runs.fail(run, "no twins answered")        # I15
    await analyse(run)
    return await repo_runs.complete(run)             # flips is_latest_for_version
```

### 3.4 Stop, pause, resume, crash

**Stop is cooperative.** `stop()` sets a flag; the loop checks it at every checkpoint and exits
after the current unit, leaving `cursor_index` at the next unstarted cell. It never kills
mid-model-call, so no partial answer is ever written.

**Resume is just start.** Starting a `paused` or `stopped` session reads `cursor_index` and
continues. Because every stage is idempotent and cache-keyed, a half-finished run resumes without
re-paying: rendered paragraphs are cached, and `twin_answers` has a unique index on
`(run_id, twin_id, wording)`, so answered twins are skipped.

**Crash recovery.** On startup:

```python
async def resume_interrupted_sessions():
    for s in await repo_sessions.by_status("running"):
        await repo_sessions.set_status(s.session_id, "paused")
        emit(s.session_id, stage="control", status="error",
             label="session interrupted by a restart; paused for resume")
```

Sessions found `running` at boot were killed by a Space restart. They are marked `paused`, **not
auto-restarted** — the researcher decides, and the logs say plainly what happened. On a sleeping
free Space this is a routine event, not an exception.

---

## 4. Background jobs

The prototype time-sliced work into "seconds of work per button press" because Apps Script caps
execution at six minutes. We have a real event loop, so a job is an `asyncio.Task` — but the Space
can still restart under it, which is why §3.4 exists.

Five named background operations, matching the Agents tab's "Run without watching" card:

| Action | Creates |
|---|---|
| Quality test in the background | a `quality` session over all consented twins |
| One dial at a time | a `sweep` session over the ten single-lever codes |
| All remaining versions | a `sweep` session over every untested code |
| Validation | a `validation` session (H2, per arm) |
| Stop the background job | sets the cooperative stop flag |

Each returns a job id immediately and streams into the same `run_events` tree, so "run without
watching" and "watch it run" are the same machinery viewed differently.

**`max_run_seconds` is retained as a soft slice.** It does not kill work; it causes the loop to
checkpoint and yield so the UI stays responsive, then continue. This is CONFIG and defaults to 0
(no slicing) since we are not on Apps Script.

---

## 5. Concurrency, rate limiting and backoff

Read `ARCHITECTURE.md` §7.1 first: **the free provider tier permits one concurrent request.**

### 5.1 The pool

```python
sem = asyncio.Semaphore(cfg.max_concurrency)     # CONFIG, default 1
```

The bounded pool exists so the value becomes 3 or 10 on a paid plan without a code change. **It
must be correct at 1** — that is the tested default, not an edge case.

### 5.2 Pacing

`delay_seconds` (CONFIG, default 0) inserts a pause between calls. The prototype used 10 s to avoid
provider pressure; with one slot and a real backoff ladder it should be 0 and raised only if 429s
appear. A blanket delay on a serial pipeline multiplies directly into the sweep duration: at
K=20 × 243 cells, one extra second per call is another 81 minutes.

### 5.3 Backoff

| Response | Behaviour |
|---|---|
| `429` | Exponential backoff with jitter, honouring `Retry-After` when present. 3 attempts. |
| `5xx` | Same ladder. |
| Timeout | Same ladder, with the timeout counted as an attempt. |
| Still failing | That **twin fails for that cell only**. The sweep continues. |

**A sustained 429 rate is a budget signal, not just a retry problem.** The orchestrator emits a
`control` event when the 429 rate over the last 50 calls exceeds 20%, so the researcher learns
their credits are constrained during the run rather than after it.

### 5.4 Pre-flight budget

Every long action is costed before it starts (`orchestrator/budget.py`):

```python
class Budget(BaseModel):
    calls: int
    tokens_in: int
    tokens_out: int
    est_seconds: int
    est_credits: float | None      # None until the researcher supplies the rate
    warnings: list[str]
```

The UI shows this on the confirm step for: a sweep, a quality run, a validation run, and any
validity test. **No researcher should discover the cost of a sweep by running one.** The estimate is
stored on `sessions.budget` so predicted and actual can be compared afterwards.

---

## 6. Caching

Three layers, each with an explicit key. **Nothing else is cached** — do not invent a fourth.

| What | Key | Table | Invalidated by |
|---|---|---|---|
| Lever paragraph | `(lever, dial, style_version)` | `lever_paragraphs` | bumping `style_version` |
| Variant | `(version_code, style_version)` | `variants` | bumping `style_version` |
| Run result | `version_code` where `is_latest_for_version` | `runs` | a rerun |
| Twin answer | `(run_id, twin_id, wording)` | `twin_answers` | never — evidence |

The last is not a cache in the eviction sense; it is the unique index that makes resume free.

### 6.1 "Ask the twins" — the dial board contract

```python
async def ask(code: str, rerun: bool = False) -> AskResult:
    if code == "00000":
        raise ControlCellError("00000 is a control cell; the orchestrator runs it")
    if not rerun:
        cached = await repo_runs.latest_completed(code)
        if cached:
            return AskResult(status="cached", run=cached)   # UI: badge + "Rerun?" button
    session = await create_session(name=f"{'Rerun' if rerun else 'Ask'} {code}",
                                   kind="ask", iterations=1, start_code=code)
    await start_session(session.session_id)                 # logs appear like any other session
    return AskResult(status="started", session_id=session.session_id)
```

A rerun creates a real session, so its logs are visible like any other. When it completes, the new
`runs` row takes `is_latest_for_version` and the previous holder is demoted **in the same
transaction** — superseded, never deleted (I9).

**A rerun inherits the original session's panel** unless the researcher explicitly chooses a new
one, because a rerun with a different panel is not a rerun (I14).

---

## 7. Events and the log tree

```python
async def emit(session_id, *, stage, label, status="running", agent=None,
               run_id=None, parent_event_id=None, payload=None) -> int:
    payload = redact(payload)          # §7.2 — enforced, not optional
    row = await repo_events.insert(...)
    if logfire_enabled:
        with logfire.span(stage, **(payload or {})) as span:
            await repo_events.set_span(row.event_id, span.span_id)
    return row.event_id
```

**Pattern:** a stage opens a parent event with `status='running'`, does its work emitting children,
then updates the parent to `ok` or `error`. The parent's label is **rewritten in place** as work
progresses — this is what gives the researcher `reconstruction (T07)` ticking through twin ids on a
single row.

```python
parent = await emit(sid, stage="reconstruction", label="reconstruction")
for twin in twins:
    await repo_events.set_label(parent, f"reconstruction ({twin.twin_id})")
    await emit(sid, stage="reconstruction", label=twin.twin_id, status="ok",
               parent_event_id=parent, payload={"hash": h, "chars": len(passage)})
await repo_events.set_status(parent, "ok")
```

### 7.2 Payload discipline

`payload` carries what the side panel shows: **references and telemetry**, never bodies.

| Store | Never store |
|---|---|
| `persona_hash`, `delta_hash`, `variant_id`, `paragraph_id` | the round prompt |
| `model`, `prompt_version`, `prompt_hash` | the persona passage |
| `prompt_tokens`, `completion_tokens`, `latency_ms`, `retries` | the full answer vector |
| gate names and verdicts | the scenario text |

The DDL enforces an 8 KB cap (`run_events_payload_small`). `redact()` truncates anything larger
with `payload.truncated = true`. The side panel fetches the real artifact from its own table
(`variants`, `twin_answers`, `twins.persona_passage`) when opened — one extra query, in exchange
for a sweep that fits the tier.

### 7.3 Polling

`events(session_id, after_id)` returns only rows newer than `after_id`. The UI keeps the rendered
tree in `gr.State` and appends. **Never re-fetch the whole stream** — at sweep scale that is tens
of thousands of rows per tick.

---

## 8. Survey intake

Intake lives in a **Supabase Edge Function**, not the Space (`ARCHITECTURE.md` §6.2). A Space
sleeping after 48 hours idle would silently drop driver submissions.

```
Google Form ──► Apps Script onFormSubmit ──► Edge Function  (X-Signature: HMAC-SHA256)
                                                    │
                    ┌───────────────────────────────┴──────────────┐
                    ▼                                              ▼
   Supabase Storage: raw/survey_<id>.json            survey_submissions + survey_answers
        (written FIRST — I16)                                      │
                                                                   ▼
                                                   (deferred) persona build on import
```

Steps, in this order:

1. Verify the HMAC over the **raw body** with `hmac.compare_digest`. Bad signature → `401`.
2. Write the raw payload to Storage. A failure here aborts before any table write.
3. Map `"<section>|<title>"` → `item_id` via `config/form_map.yaml`. **An unmapped question is a
   `422`, never a dropped answer.**
4. Insert `survey_submissions` + `survey_answers`.
5. Return `{status, submission_id, consent_twin}`.

**Persona building is deferred to twin import**, not done at intake. It is pure Python and cheap,
but doing it in an Edge Function duplicates the template library outside the repo — a drift risk
with no benefit. Intake stores; the Space imports.

**Consent statement 7 gates the twin, not the record.** A response without it is stored in full and
never becomes a twin.

`ingest/replay_raw.py` re-drives any Storage object with no matching row, which is why step 2
precedes step 4.

**One contract, two implementations.** The Edge Function (TypeScript) and `ingest/survey_intake.py`
share `config/form_map.yaml` and one test fixture (`apps_script/sample_payload.json`). A contract
test asserts both produce identical rows from that fixture, so they cannot drift.

---

## 9. Errors

| Class | Behaviour |
|---|---|
| `ConfigError` | Startup fails. Never runs with a bad agent config. |
| `ControlCellError` | Rejected at the service boundary with an explanation. |
| `CheckerFailure` | Cell marked `failed`, logged, loop continues. |
| `PersonaTemplateMissing` | Reconstruction fails for that twin, logged, loop continues. |
| `ProviderRateLimit` | Backoff ladder (§5.3), then that twin fails for that cell. |
| `OutputContractError` | Targeted repair, then that twin fails for that cell. Never coerced. |
| `PanelMismatch` | Refuses the comparison and names the two panels. |
| `SupabasePaused` | Retry with backoff up to 60 s (free-tier cold start), then surface. |

Every one writes a `run_events` row with `status='error'` and the exception in `payload`. Every
error surfaced to the UI carries the `event_id`, so "it failed" is always followed by "here is
exactly where".

---

## 10. Startup

```python
async def on_startup():
    await db.ping_with_backoff()        # Supabase free tier cold start: 10-30 s
    await config.load()                 # app_config + agent_configs; ConfigError halts here
    assert_reference_counts()           # docs/01 §9; a drifted seed halts the app
    await resume_interrupted_sessions() # §3.4
```

`assert_reference_counts()` running at boot rather than only in the seeder is deliberate: a Space
pointed at the wrong Supabase project should refuse to start, not quietly produce results against
the wrong reference data.
