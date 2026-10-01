# ARCHITECTURE_UPDATE — M18. Final plan

**Written 2026-10-01. Paste this whole file into a fresh session to start executing.** It is
self-contained; you should not need the M15/M16/M17 handoffs except where it points at them.

Read `CLAUDE.md` first, then §1 and §2 here.

Use `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. On Windows prefix anything that prints a
rendered paragraph with `PYTHONIOENCODING=utf-8`, and `PYDANTIC_AI_NO_BANNER=1` to keep output
readable.

**State at the time of writing:** 787 tests pass, `ruff` clean, 6 import-linter contracts hold,
`build_reference --check` exits 0. `twins` 50 (all synthetic), `survey_answers` 3650,
`lever_paragraphs` 7 (all v1), `variants` 3 (all v1), `studio_runs` 6. Evidence tables — `runs`,
`run_events`, `sessions`, `twin_answers`, `twin_quality_runs`, `validity_results` — are all **0**.
v2 is a clean slate with a full re-render budget.

**This plan makes the instrument usable. It does not make it correct** — that is
`HANDOFF_M17_VALIDATION_PLAN.md` §5.1 and §5.2, which remain the gate on the study and are
untouched here. Nothing in this plan renders a stimulus or produces a number for the paper.

---

## 1. Decisions taken. These are settled; do not re-litigate

### 1.1 Studio values may feed analysis — CONFIRMED by the researcher

> *"by overwrite, it's ok for the studio values to feed analyses"*

**Decided.** Implement it. The good news from tracing it: this is satisfiable **without breaking
`CLAUDE.md` rule 6**, because `services/results.completed_runs` already selects the latest run per
`version_code` ordered by `started_at` descending. So:

* A Studio ask **appends** a `runs` row and `twin_answers` rows. Nothing is updated in place.
* A later Dial board run for the same code has a newer `started_at`, becomes the latest, and
  **supersedes the Studio value automatically** — which is exactly the requested precedence, with
  no precedence logic to write or get wrong.

Rule 6 holds. What this *does* cost is stated once, here, and then designed around rather than
argued about again:

> A version whose most recent run is a Studio run reports an index computed from **one twin**, not
> from the frozen panel. `00000` and `SHAM` — the noise floor a lever effect must clear — come from
> the panel. So a Studio-origin number and a sweep number are not the same quantity, and §4.3
> makes the difference visible in the data, the results table and the export rather than leaving a
> future reader to infer it from `twins_n`.

### 1.2 The model is `gpt-oss:120b` only — CONFIRMED by the researcher

> *"no its gpt oss only"*

**Decided.** Screenshot 3's *Mistral / `mistral-small-latest` / temperature 1* is stale stored
config and must be corrected, not preserved. Note `ModelRef.provider` is
`Literal["ollama", "openai", "mock"]` — **there is no `mistral` provider in the model at all**, so
that row is invalid against the code as well as against the researcher's intent. §5.5 covers the
data fix and the guard.

### 1.3 Still open, but NOT blocking — the sweep population

`session.population` defaults to `"real"`; every twin is `synthetic`. Unanswered, so the plan does
**not** silently pick a study default. §3.6 makes the population an explicit, visible control with
the current state shown next to it, and the researcher chooses at the moment of running a sweep.
That unblocks execution without deciding a study question in code.

---

## 2. Not a bug — the 600-call preview is correct

> *"for 50 twins (2 calls each) it will have 600 calls, that is too much"*

`H3_CALLS_PER_REPEAT × quality_runs_per_twin × twins` = `6 × 2 × 50 = 600`
(`orchestrator/budget.py:35`, `:133`).

The **6** is not a repeat count. The H3 gate shows each twin **all six Part-17 stimuli**, one model
call each, reading three holdout items from every round — that is `docs/08`'s "18 H3 numbers"
(6 rounds × 3 items). `quality_runs_per_twin = 2` repeats that whole set, so **12 calls per twin**.

The preview is honest and the cost is real. Levers, most to least defensible: fewer twins (the four
filters already on the Twins tab); `quality_runs_per_twin` 2 → 1 (**research decision** —
`docs/08` §2.1 wants 3 so one bad sample does not discard a good twin, and it is already down from
3 to 2); the six H3 codes are frozen and not a lever.

**Change nothing about the number. Change the caption** so it explains itself: show
`6 versions × 2 repeats × 50 twins` and calls-per-twin beside the total. One-line change in
`quality_budget_view`'s caption text.

---

## 3. Phase 1 — the app is currently unusable. Do this first

### 3.1 The Agents page re-renders every 3 seconds

`ui/pages/lab.py:355` — `gr.Timer(3.0, active=True).tick(_poll, …)` with **seven outputs**,
including the whole log-tree HTML, the agent-card HTML, the status table and the job line. Gradio
replaces every one of those DOM subtrees on every tick whether anything changed or not: scroll
position resets, open elements collapse, focus is lost. `_poll` is already incremental where it
fetches (`after_id`), then throws that away by re-rendering `log_tree(merged)` over the full list
and returning fresh HTML for all seven outputs.

**Fix**

1. Fingerprint the tick's inputs (`next_id`, `session_id`, session status, `tested`, hash of the
   status rows) and carry it in a `gr.State`.
2. Unchanged fingerprint → return `gr.skip()` for **every** output. The DOM is left alone.
3. Rebuild each output only when *its own* input moved: a status change must not re-render the log.
4. `gr.Timer(active=…)` is settable from a handler — stop the timer when no session is running and
   raise the interval to 5 s while one is. **An idle Agents page must make zero database calls.**

`docs/06` §3.1 asks for a job line kept current; nothing there requires a 3-second full re-render.
Record the degradation in `docs/DECISIONS.md` per `CLAUDE.md`.

### 3.2 `ConnectionTerminated` and `WinError 10035`

`last_stream_id:133` is the tell — 133 HTTP/2 streams on one connection. This is connection churn
and **§3.1 is the source**: six-plus round trips every three seconds, forever, on an idle page.

Second, independent contributor: `SupabaseBackend` builds one `supabase-py` client
(`db/client.py:169`) and every call runs through `asyncio.to_thread`, so one synchronous `httpx`
client is shared across an unbounded thread pool. Both errors are currently *recovered* by the
retry loop — a symptom, not yet a failure.

**Fix, in order, re-measuring after each**

1. **§3.1 first.** This may be the entire fix; do not do more until it is measured.
2. Bound database concurrency with an `asyncio.Semaphore` in the backend. `max_concurrency=1`
   bounds the *provider*; the database has no such bound.
3. If it persists: disable HTTP/2 on the PostgREST client, or recycle the client on
   `ConnectionTerminated`. HTTP/1.1 keep-alive suits this access pattern and the study's query
   volume never needs multiplexing.
4. Keep the retry, but classify it — §3.3.

### 3.3 The retry loop retries what can never succeed

`db/client.py:174–185` catches bare `Exception` and retries **everything** four times with
exponential backoff. A foreign-key violation (`23503`), unique violation (`23505`), check violation
(`23514`) or malformed filter is deterministic — the same call fails identically every time. That is
why one failed delete printed the same error four times across ~5 seconds before raising.

**Fix.** Split transient from permanent in `_run`:

* **Retry**: connection errors, timeouts, `ConnectionTerminated`, `WinError 10035`, HTTP 5xx, 429.
* **Never retry**: any PostgREST error with a SQLSTATE in class `23` (integrity), `22` (data) or
  `42` (syntax/access). Raise `DbError` on the first occurrence, constraint name intact.

Unit-test both branches against a stub that counts calls.

### 3.4 Deleting synthetic surveys crashes on a foreign key

```
update or delete on table "twins" violates foreign key constraint "studio_runs_twin_id_fkey"
Key (twin_id)=(SYN-30092026-0000) is still referenced from table "studio_runs".
```

Three tables reference `twins(twin_id)` **without** `on delete cascade`:

| Table | Migration | Should it block a delete? |
|---|---|---|
| `twin_answers` | `001_init.sql:212` | **Yes** — evidence, rule 6 |
| `session_panel` | `002_v2_model.sql:145` | **Yes** — I14, the frozen panel |
| `studio_runs` | `002_v2_model.sql:260` | **No** — quarantined sandbox |

`services/surveys.delete_synthetic` deletes `survey_answers`, `twins`, `survey_submissions`. Its
docstring reasons carefully about `runs` and concludes "no run is touched" — true, and not the
problem. **`studio_runs` is simply never considered**, and the database currently holds 6 such rows
against `SYN-30092026-0000`.

> **Note the interaction with §4.** Once Studio asks write `runs` and `twin_answers` (§1.1), a twin
> that has been used in the Studio **will** be blocked by `twin_answers`, correctly. Implement §3.4
> before §4 and re-test it after §4 lands.

**Fix**

1. **Pre-flight, not crash-and-retry.** Count blocking references *first*, then delete what is safe.
2. **`studio_runs`**: delete the rows for those twins in the same operation, before `twins`. A
   Studio run about a twin that no longer exists is not evidence of anything.
3. **`twin_answers` / `session_panel`**: still block — but with a sentence, not a traceback:
   *"3 of 50 synthetic twins cannot be deleted: they have answered runs or sit on a frozen panel.
   Deleting them would change a stored result. Delete the other 47?"*
4. Tests: a `studio_runs` row must not block; a `twin_answers` row must refuse **by message**, not
   by exception type alone.

### 3.5 `InsufficientEligibleTwins` — correct error, invisible delivery

```
background session failed: InsufficientEligibleTwins("no eligible twins for population 'real' …")
```

**The message is right.** `eligible_candidates` (`orchestrator/panel.py:74`) requires
`source ∈ POPULATION_SOURCES[population]` **and** `quality_passed`. With `population="real"`, 50
synthetic twins and `twin_quality_runs = 0`, the pool is empty twice over.

Three defects behind one console line:

1. **Logged, never shown.** `services/runs._spawn`'s done-callback calls `log.error` (`runs.py:81`).
   The researcher sees a session appear and never move.
2. **The session row is written before the panel is validated.** `start_sweep` creates the row,
   spawns, *then* the draw fails — leaving a permanent `sessions` row for a job that never ran.
   Eligibility is knowable before the row is written.
3. **It is the circularity, not user error.** The gate needs stimuli, the panel needs gate-passed
   twins, the sweep needs a panel (`HANDOFF_M15_LIVE_PATH.md` §3.3).

**Fix**

* Add `services/runs.check_eligibility(population, panel_size)` → structured result
  (`eligible`, `total`, `quality_passed`, `by_source`, `reason`). Pure read, no session row.
* `start_sweep` and `ask_twins` call it **before** `SessionRepo.create` and raise a typed
  `NotReadyToSweep`. `_start` (`lab.py:219`) already renders `SessionAlreadyRunning` cleanly; this
  joins that path.
* Message names the real blocker: *"0 of 50 twins have passed the quality test. Run it first
  (Agents → Run twin quality test). Population is 'real' and all 50 twins are synthetic — change
  the population below if this is a synthetic study."*
* `_spawn`'s done-callback must also emit a `run_events` row with `status="error"`, so a background
  death appears in the log tree the researcher is already watching. Console-only failure reporting
  is why this went unexplained.

**Diagnostic to run first:** check whether `sessions` grows a row per occurrence. If it does, the
source is the resume button (`lab.py:283`; screenshot 1 shows a paused session) and the pre-flight
is the complete fix. If it fires with no row created, something else calls `_spawn` — find it before
building the pre-flight.

### 3.6 Make the population visible (§1.3)

Non-blocking implementation of the undecided question: surface `population` as an explicit control
on the sweep confirmation, defaulting to the **current stored value** and never silently changed by
code. Beside it show the live counts — *"real: 0 · synthetic: 50 · passed the quality gate: 0"* —
so the choice is made against the data. Do **not** default a synthetic-only database to `synthetic`
automatically: which population a study sweep runs on is the researcher's call.

---

## 4. Phase 3 — Twin Studio: one twin, any version, results that count

Implements §1.1. **Do §3 first** — this phase writes to evidence tables and should not be debugged
on a machine that throws an error every three seconds.

### 4.1 What is wrong now

`services/studio._stimulus:614` refuses any version with no stored, Checker-passed variant:

> *"`22000` has never been rendered … Ask the twins for it on the Dial board first."*

Unusable for the purpose: the Dial board runs the **whole frozen panel** to answer a one-twin
question. Screenshot 2 is this dead end — every dial set, a valid code, nothing to press.

The refusal is **correct and stays**: I3 has no sandbox exemption. What is missing is a way to
*produce* a verified variant from the Studio. Rendering is not forbidden, only expensive — and
`CLAUDE.md` rule 12 forbids it in a handler's synchronous path.

### 4.2 Render on demand

1. New `services/studio.start_render(version_code)`, mirroring `start_quality_gate`: enqueue an
   `asyncio` task, return immediately, emit into `run_events` so the Agents log shows it, store via
   `VariantRepo.put`.
2. It **reuses `twin_runtime.render_and_check`**, so the cache (I4), the durable re-render budget
   and all five Checker gates apply unchanged.
3. The variant is keyed `(version_code, style_version)` like any other, so **a later Dial board run
   hits the cache and pays nothing**. Studio rendering is a net saving, not a new cost.
4. Show the budget first, as the other three buttons do. Never render blind.
5. When no variant exists, Studio offers *"Render this version now"* instead of a dead end.

### 4.3 Studio results feed analysis — the design

Migration **`004`** (additive; apply by hand as with `003`):

```sql
alter table runs add column if not exists origin text not null default 'sweep';
alter table runs add constraint runs_origin_check check (origin in ('sweep','studio'));
```

Then:

1. A Studio ask creates a `sessions` row of `kind='studio'` and a `runs` row with
   `origin='studio'`, `version_code` set, `twins_n=1`, and appends the twin's `twin_answers` row
   under it. **Append only — no UPDATE anywhere.**
2. The index is computed by the **same** `analyse()` the sweep uses, so a Studio number and a sweep
   number are the same statistic over a different n — never two different formulas.
3. `services/results.completed_runs` needs **no change**: it already takes the latest per
   `version_code` by `started_at`, so a later Dial board run supersedes the Studio value. This is
   the requested precedence, for free.
4. **`origin` and `twins_n` must be visible wherever a number is.** The Results table gets both
   columns; the export's header rows carry `origin`; a version whose latest run is `origin='studio'`
   renders with an explicit badge naming n. §1.1's consequence is thereby in the data, not in a
   reader's head.
5. **A Studio run writes no `session_panel` row** and is never inheritable by a rerun — I14 applies
   to frozen panels and a Studio run has none. Assert this in a test.
6. I15 still holds: `twins_n = 1 ≥ 1`. A Studio ask whose twin fails the ladder is `failed`, never
   `completed` with an index of 0.000.

### 4.4 Per-`(twin, version)` history in `studio_runs`

Keep `studio_runs` as the full sandbox record (it holds `free_answers`, `questions`,
`scenario_text` that `twin_answers` has no column for). Same migration:

```sql
alter table studio_runs add column if not exists is_latest_for_twin_version boolean not null default true;
```

Flipped in the same transaction as the insert, exactly as `runs.is_latest_for_version` is. A second
ask for the same `(twin_id, version_code, wording)` appends and moves the pointer; the earlier row
survives.

### 4.5 All three twin sources must work

Screenshot 2 shows *Use a twin I have*, *From a survey answer*, *Make one by hand*. Validation-plan
**C-11** and **C-12** cover the last two and are both `[TODO]`. Verify here rather than assume:

* Custom free text stays sandboxed, keeps `SANDBOX_LABEL`, is never filed under a version code, and
  **never writes a `runs` row** — it is not one of the 243 and has no `version_code` to be latest
  for. This is the one Studio path that stays fully quarantined.
* A hand-made twin is `source='manual'`, carries no persona hash, shows an **empty** baseline column
  rather than zeros, and is never drawable into a panel.

---

## 5. Phase 4 — Agent Studio

Screenshots 3–7 are the target (§1.3 of the previous draft is resolved: follow the screenshots, and
where one disagrees with `docs/06` §6, flag it in `docs/DECISIONS.md` rather than silently
choosing). Current state: `ui/pages/agent_studio.py:232–313`.

### 5.1 Twin Interviewer — wrong data, not just wrong layout (screenshot 4)

| | Screenshot | Current (`_twin_html`, `agent_studio.py:137`) |
|---|---|---|
| Comparison | one row **per instruction variant** (`saved`, and the edit); columns `Answer checked?`, the six metrics, `A reason it gave` | one row **per metric**; columns `Saved / Your edit / Difference` — transposed, no pass/fail, no reason |
| Answers | **"Some of the 37 answers it gave"** — the **twin's** output (`PAF1 4`, `SAT1 3`, `LOY1 2`) | *"what this twin's **driver** answered"* — the baseline |

The second row is the real defect: **the panel is showing its input instead of its result.** Fix
`twin_test_view` to return the twin's answer vector and render it; keep the driver's value as a
second column, as screenshot 6 does for the Checker. Add the `Answer checked?` column (the
contract/range verdict `run_answer_ladder` already computes) and the one-line rationale.

### 5.2 Policy Designer — two sections missing, one column wrong (screenshot 5)

Current code (`agent_studio.py:248`) renders the dial table, the Fairwork score and the scenario
paragraphs. Fix three things:

1. **`Text used` shows the wrong string.** It joins `lever.bullets` — that is `told_summary`, the
   **researcher-facing** bullet list which `variant/lookup.py` is explicit *a twin never sees*.
   Screenshot 5's column holds the **rendered paragraph** ("You can now reach a human
   representative and appeal low ratings…"). Show the rendered text; keep bullets in a separate
   column if wanted.
2. **"The whole scenario, in both wordings"** — screenshot 5 shows labelled **Wording A** and
   **Wording B** blocks. Current panel shows one unlabelled set of cards. Wording is a real
   experimental factor (validity test 5).
3. **"Versions it would test next"** — a `Version | Why` table (`00001 — Test one dial on its own
   first.`). Absent entirely. The candidate logic exists for the sweep (`SessionRunner`'s
   `candidates`); surface it read-only.

### 5.3 Quality Checker (screenshot 6)

Closest to correct. Confirm against `_checker_html`: the three completeness checks, the two
threshold rows with their `must be …` captions, the `Hidden question | Driver said | Twin said`
table, and the explicit **`Decision: Keep this twin`** line. Verify the decision is the **AND** of
both thresholds (validation-plan D-4) and that the numbers shown are the stored ones.

### 5.4 Run Manager (screenshot 7)

Plan table is present (`agent_studio.py:241`). Missing: **"What it would write to the log"** — five
preview lines, one per agent. Add it; keep the "nothing has been started" assurance, since
screenshot 7 is explicitly a dry run.

### 5.5 `gpt-oss:120b` only — the data fix and the guard (§1.2)

Screenshot 3 shows the Twin Interviewer on **Mistral / `mistral-small-latest` / temperature 1**,
last saved 2026-09-25. Three problems:

1. **`mistral` is not a valid provider.** `ModelRef.provider` is
   `Literal["ollama", "openai", "mock"]`. Either the stored row is invalid or the UI dropdown offers
   options the model rejects. Fix both: the dropdown must be built **from the Literal**, not from a
   hand-written list.
2. **Correct the stored `agent_configs` rows** to `gpt-oss:120b` for all five agents, as a
   migration or a seed correction — not by hand in the UI, so it is reproducible.
3. **The temperature box lies.** `twin_runtime.twin_agent_config:581` applies
   `load_twin_config().temperature` (**0.25**, from `app_config`), overriding whatever the
   `agent_configs` row says. So the Agent Studio shows `1` while the twin runs at `0.25`. Either
   show the value actually in force with a note saying where it comes from, or make the box
   authoritative — but the current state, where the screen shows a number that is silently
   discarded, must not survive. Related: twin temperature is still the un-run validity test 8
   (`HANDOFF_M17_VALIDATION_PLAN.md` §5.4).

### 5.6 The "What was changed" log (screenshot 4, bottom)

`When | Agent | What was saved`, agent names upper-cased (`MANAGER`, `ANALYST`, `CHECKER`), each row
a truncated summary with the model appended. Rendered from `history()` (`agent_studio.py:438`).
Compare field by field against the screenshot — this is the log reported as wrong.

### 5.7 Results Analyst

No target screenshot was supplied. Leave as is; confirm only that I12 holds — every number in the
prose grounded against its input bundle. **Ask before inventing a panel.**

---

## 6. Phase 5 — the test protocol

> *"delete the 50 present synthetic twins, create a new batch of 20 twins frustrated drivers and run
> the tests"*

Deliberately **not** done in the planning session: the delete is blocked by the live bug in §3.4 and
would have failed exactly as it did for you, and it is destructive.

1. **Pre-flight.** Record counts (`twins` 50, `survey_answers` 3650, `survey_submissions` 50,
   `studio_runs` 6). Confirm `twin_answers` and `session_panel` are still **0** so nothing blocks on
   evidence grounds. *(If §4 has already run a Studio ask, it will not be 0 — delete before §4, or
   accept that those twins are now undeletable, which is correct behaviour.)*
2. **Delete** via Generator → *Delete all synthetic surveys*. The 6 `studio_runs` rows go with them.
   Confirm `runs` / `twin_answers` / `validity_results` stay 0 and no real row is touched.
3. **Generate 20 frustrated drivers.** The `frustrated` preset exists
   (`services/generator.py:64`) and is deliberately **not flat**: low fairness/clarity/satisfaction/
   loyalty, **high** exposure/control/pushback/exit. **Record the seed** — the batch must be
   reproducible from `(seed, count, spec)` per `docs/09` §2.
   * **Confound warning:** 20 twins from one sentiment preset is a low-variance, strongly-correlated
     panel. Fine for plumbing; **not** a study panel, and no number from it should be quoted.
4. **Re-run Tier A** (~2 min). It must still be green after a data change.
5. **Quality gate on the 20.** Budget reads `6 × 2 × 20 = 240`. First real exercise of **D-1, D-2,
   D-5, D-6** (all `[TODO]`): one `twin_quality_runs` H3 row per twin, `items_n = 18`, H2 stored
   with 16 items, repeats **averaged** not last-wins, `config_version` on the row.
   * **Needs stimuli → needs `HANDOFF_M17_VALIDATION_PLAN.md` §5.1 and §5.2 decided.** The gate
     renders the six H3 codes first and stops on the first failure. Sequence accordingly.
6. **Twin Studio on one of the 20**, exercising §4: render `22000` on demand, ask, ask again,
   confirm the latest pointer moved and the earlier row survives, and confirm the Results table
   shows the run with `origin='studio'` and `twins_n=1`.

---

## 7. Evidence hygiene — decide before step 5

`HANDOFF_M17_VALIDATION_PLAN.md` §8 left this open and **§1.1 makes it sharper**: Studio runs now
write to `runs` and `twin_answers`, so smoke-test rows and study rows share a table. Options
unchanged; option 1 is a small additive migration and is the one to take:

1. **`sessions.purpose`** (`'smoke' | 'study'`, default `'study'`) — a test session is *marked*
   rather than inferred later from panel size. **Fold it into migration `004`** alongside
   `runs.origin`; it costs nothing extra and the two answer the same question from different angles.
2. Run and exclude later by `sessions.config.panel_size`. No migration; a future reader must know to
   look.
3. A scratch Supabase project. Costs a re-seed, and smoke tests then never exercise the real schema.

---

## 8. Execution order

1. **§3.1, §3.2, §3.3** — polling, connection churn, retry classification. Smallest changes, largest
   effect; the app becomes usable and the console goes quiet.
2. **§3.4, §3.5, §3.6** — the delete, the eligibility pre-flight, the population control.
3. **§9 (Phase 2 checks)** at the screen. Do not skip: Tier H has never been exercised.
4. **§7** decision, then migration **`004`** (`runs.origin` + `studio_runs.is_latest_for_twin_version`
   + `sessions.purpose`) applied by hand, with `_REQUIRED_COLUMNS` updated so boot refuses a
   database without it.
5. **§4** — Twin Studio.
6. **§5** — Agent Studio, panel by panel, screenshot beside the screen.
7. **§6** — delete, regenerate 20, quality gate (after the M17 §5.1/§5.2 decisions).
8. **Re-run Tier A and F-1** at the end (`HANDOFF_M17_VALIDATION_PLAN.md` §6.10 item 7).

---

## 9. Phase 2 — verification that Phase 1 worked

Cheap, and not optional.

| id | Check | Pass |
|---|---|---|
| U-1 | Sit on the Agents tab 2 minutes, no job running | **zero** database calls, no visible re-render, scroll position held |
| U-2 | Start the quality gate, watch the log | rows append, no flicker, job line updates |
| U-3 | Delete synthetic surveys with a `studio_runs` row present | succeeds, reports counts |
| U-4 | Delete with a `twin_answers` row present | refuses **with the sentence**, deletes nothing, **one** log line not four |
| U-5 | *Let the agents choose 6 versions* with 0 eligible twins | clean in-page message naming the quality gate; **no `sessions` row created** |
| U-6 | Force a background task to raise | the failure appears in the Agents log tree, not only the console |

---

## 10. Invariants this plan touches, and how each is kept

| Invariant | Touched by | Kept how |
|---|---|---|
| Rule 6, append-only evidence | §4.3 Studio → `twin_answers` | Append only; "latest" stays an ordering/pointer. No UPDATE is added anywhere. |
| I3, unverified variant never reaches a twin | §4.2 render on demand | Render **then** check, via the existing `render_and_check`. The `_stimulus` refusal stays. |
| I4, ten design calls per style version | §4.2 | Same `(version_code, style_version)` cache; a Studio render is reused by the Dial board. |
| I14, the panel is frozen | §4.3 | A Studio run writes **no** `session_panel` row and is never inheritable by a rerun. Asserted in a test. |
| I15, no result over zero twins | §4.3 | `twins_n = 1`; a failed ladder is `failed`, never `completed` with 0.000. |
| I12, no model produces a metric | §5 | Unchanged — every Agent Studio panel renders numbers Python computed. |

---

## 11. Open question that remains

**The sweep population (§1.3).** Handled non-blockingly by §3.6 — made explicit and visible, never
defaulted by code. It becomes a real decision the first time a study sweep is run, not before.

Everything else raised has been decided (§1.1, §1.2) or diagnosed with a root cause and a fix.
