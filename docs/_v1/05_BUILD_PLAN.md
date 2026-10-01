# 05 — Build plan

Ten milestones. Each has an acceptance test that must pass before the next begins. Do not build
ahead; the ordering exists because later milestones depend on frozen artifacts from earlier ones.

## M0 — Scaffold

Repo layout from `ARCHITECTURE.md` §4. `requirements.txt`, `Dockerfile`, HF Space card
(`sdk: docker`, `app_port: 7860`), `config/settings.py` via pydantic-settings, `.env.example`.
A FastAPI app with `/api/health` and an empty Gradio shell with five named tabs.

**Accept:** `docker build` succeeds; `/api/health` returns `{"status":"ok"}`; the Space renders five
tabs in the order Logs · Dial board · Twins · Results · Settings.

## M1 — Reference data and schema

`ingest/build_reference.py` regenerates all eight files in `data/reference/` from the source
documents. `migrations/001_init.sql` applied. `ingest/seed_db.py` idempotent.

**Accept:**
- Re-running the builder produces **byte-identical** output (assert on sha256).
- Counts: 33 criteria, 33 findings, 30 gaps, 10 thresholds, 126 chunks, 171 links, 73 items, 5 scales.
- `criterion_findings` has exactly 3 rows with `finding='Met'`, and they are `3.1.a, 3.1.c, 4.1.c`.
- Running `seed_db.py` twice changes no row count.

## M2 — Item register and persona builder

`persona/templates.py` with one template per battery item plus demographics and background.
`persona/builder.py` producing a deterministic, hashable passage.

**Accept:**
- Same survey row in → byte-identical passage out, across two processes.
- A row with a missing template raises `PersonaTemplateMissing`; nothing is silently dropped.
- The passage contains **no digits from Likert answers** (I7) — assert no bare `1`–`7` token derived
  from a scale value.
- The passage contains **no Part 15, 16 or 17 content** (I6) — assert none of the 34 holdout item
  stems appears.
- Every answered battery item contributes at least one clause (count clauses ≥ count answers).

## M3 — Lookup and the dial

`variant/lookup.py`, `orchestrator/odometer.py`.

**Accept:**
- `lookup("01000").commitments` has exactly 3 keys: `2.1.a`, `2.1.b`, `2.1.c`.
- `lookup("02000")` has 6; `lookup("22222")` has 30; `lookup("00000")` has 0.
- `delta_hash` is stable across processes.
- `code_from_index(0)=="00000"`, `(1)=="00001"`, `(3)=="00010"`, `(81)=="10000"`, `(242)=="22222"`;
  `index_from_code` is its exact inverse for all 243.
- `sum(digit_sum(code) for all 243) == 1215`.

## M4 — Design agent and checker

`variant/render.py`, `variant/checker.py`, `agents/design.py`, `agents/checker.py`,
`config/style_contract.yaml`.

**Accept:**
- Rendering all 243 codes calls the design agent **exactly 10 times** (I4) — assert on a call
  counter, not on wall time.
- Every dial-0 lever renders the byte-identical string `"No change from today."` (I5).
- A deliberately poisoned render containing 2.2 language fails `containment` for `01000` (I3).
- A render of 41 or 80 words fails `in_band`.
- `SHAM` passes every gate and contains no `"No change from today."` line.
- The design agent's `AgentConfig.tools == []` and `build_agent` raises if tools are added (I2).

## M5 — Twin agent

`agents/twin.py`, round-prompt assembly, `TwinAnswerSet` validation.

**Accept:**
- Output validates to exactly the 37 battery item ids; a missing or extra key raises.
- Every value is within its own scale's range (5-point items reject 6 and 7).
- The round prompt contains **no** why-text, **no** open-ended answers, **no** holdout items (I8).
- `lever_order` and `seed` are persisted and a round can be reconstructed byte-identically.

## M6 — Orchestrator

`orchestrator/loop.py`, `events.py`, sessions and runs repositories, stop/resume.

**Accept:**
- A session stopped mid-sweep and restarted resumes at the same `cursor_index` and does **not**
  re-ask twins that already answered (assert the LLM call count on resume).
- Killing the process mid-run and restarting marks the session `paused` and emits an interrupted
  event; no session auto-restarts.
- A fresh session runs `00000` then `SHAM` before the first swept code.
- `run_events` forms a valid tree: every `parent_event_id` resolves, no cycles.
- A checker failure marks that run `failed` and the loop continues to the next code.

## M7 — Analyst

`analysis/metrics.py`, `interactions.py`, `report.py`.

**Accept:**
- Reverse coding applied to `SAT2` and `DEP1` only.
- 5-point metrics are **not** rescaled to 7.
- Given the mock's shift vectors, `index` reproduces all ten published values to 3 dp — in
  particular `21122 → 1.245` and `01000 → 0.143`.
- `interaction()` returns `None` when any of the three cells is missing; never imputes.
- The analysis prompt bundle contains no number absent from the computed metrics.

## M8 — UI

All five tabs per `docs/04_FRONTEND.md`, then the quality page.

**Accept, tab by tab:**
- **Logs:** the reconstruction row's label updates in place through twin ids on a single row;
  clicking it opens a panel listing twins as collapsed accordions, each expanding to the full
  passage. Status dots reflect real status.
- **Dial board:** changing a dial updates the version code and "What the twins are told" with no
  network call. `00000` shows the warning and blocks "Ask the twins". A cached code shows the amber
  badge and a `Rerun?` button; rerun creates a visible session.
- **Twins:** the quality card sits above list and panel; list and panel are side by side. The panel
  order is exactly §5.3, including the scenario block between the version dropdown and the tables.
  **No reason column anywhere.**
- **Quality page:** Select → checkboxes; Run selection honours check order; Run all runs every
  consented twin; the right block streams that session's log.
- **Results:** grid click opens the panel; panel order is exactly §7.4; the tested-versions table
  searches by version code.

## M9 — Intake and hardening

`/api/survey/intake` with HMAC, the `data/temp` mirror, `config/form_map.yaml`,
`ingest/replay_temp.py`. Backoff and retry across providers. Logfire wiring behind a flag.

**Accept:**
- An unsigned or wrongly signed POST is rejected 401.
- The mirror file is written **before** any DB write; a forced DB failure leaves a replayable file.
- A response without consent statement 7 is stored and produces **no** twin.
- An unmapped Form question raises rather than being dropped.
- With `LOGFIRE_TOKEN` unset the app runs normally.

## M10 — Invariant suite

`tests/test_invariants.py` — I1 to I11 as executable tests, run in CI.

**Accept:** all eleven pass, and each test names the invariant it guards in its docstring.

---

## What "done" means

A researcher can: create a session, set five dials by hand, ask the twins, watch the run in the logs
tab with a side panel showing every agent's input and output, read the metrics and the written
analysis, open the Twins tab and compare a driver's own answers to their twin's answers under that
version, run a quality test on selected twins and see every surface update, and open the Results tab
to see all 243 cells with the tested ones filled in — then stop the app, restart it, and resume the
sweep where it left off.
