# 11 — Build plan

Fourteen milestones. Each has acceptance tests that must pass before the next begins.

The ordering exists because later milestones depend on frozen artefacts from earlier ones. **Do not
build ahead.**

---

## Ground rules

- **Never call a live LLM or a live DB in a test.** `conftest.py` installs an in-memory backend per
  test; `fixtures/stub_agents.py` provides a stub model client routed by `agent_id`.
- **Test the contract, not the prose.** Assert the design agent was called 10 times for 243 codes;
  do not assert the wording it produced.
- **Every invariant gets an executable test** naming it in the docstring. They accumulate across
  milestones and all run in CI from M2 onward.
- `data/reference/*.json` for the eight existing files is **frozen and verified**. Never regenerate
  or hand-edit them. Two new files (`arms.json`, `legacy_crosswalk.json`) are generated in M1.

---

## M0 — Scaffold and portability

Repo layout per `ARCHITECTURE.md` §4. `pyproject.toml` (Python **3.13**), `requirements.txt`,
`config/settings.py` via pydantic-settings, `.env.example`.

Both entrypoints from day one: `app.py` (`demo.launch()`) and `app_docker.py`
(`gr.mount_gradio_app`). Space card with `sdk: gradio`, `python_version: "3.13"`, `hf_oauth: true`.
An empty Gradio shell with the eight routes.

**Accept:**
- `app.py` and `app_docker.py` both start and serve the same `gr.Blocks`; neither contains logic.
- The eight routes render in the order of `docs/06` §0, with a working navbar.
- `spaces` is not imported anywhere; no `@spaces.GPU` decorator exists.
- An **import-linter** test enforces the layer table in `ARCHITECTURE.md` §4 and fails on a
  violation.
- No route, service or component named or referencing "Google Sheet".

---

## M1 — Reference data, schema, and a deployment smoke test

`ingest/build_reference.py` regenerates all ten files. Migrations applied. `ingest/seed_db.py`
idempotent with the §9 assertions from `docs/01`.

**Deploy the empty shell to the real target now**, and answer the open question before anything is
built on it.

**Accept:**
- Re-running the builder produces **byte-identical** output for the eight existing files (assert on
  sha256). `--check` exits 0.
- Counts: 33 criteria, 33 findings, 30 gaps, 10 thresholds, 126 chunks, 171 links, 73 items,
  5 scales, 9 constructs, 4 arms.
- `criterion_findings` has exactly 3 rows with `finding='Met'`, and they are `3.1.a, 3.1.c, 4.1.c`.
- Every `anchors` array length equals its `scales.points`.
- All 17 seed assertions pass; running `seed_db.py` twice changes no row count.
- `reference_hash` is computed and checked at startup; a mismatch refuses to boot.
- **A background `asyncio` task survives ≥ 30 minutes on the deployed ZeroGPU Space**
  (`ARCHITECTURE.md` §8.1). If it does not, stop and re-decide the deployment target before M2.

---

## M2 — The output contract and the agent registry

`agents/contract.py` and `agents/registry.py`. Built early because every agent depends on it and
retrofitting validation is how silent corruption gets in.

**Accept:**
- `build_agent` raises on an unknown tool name, and on `output_mode == "native"` (I13,
  `ARCHITECTURE.md` §3.2).
- Normalisation performs every allowed repair in `docs/02` §5.3 and **none** of the forbidden ones.
  One test per forbidden repair, asserting it does **not** happen: no padding from baseline, no
  clamping, no rounding of non-integral values, no first-of-disagreeing-duplicates.
- A vector missing two items triggers a **targeted** repair naming only those two; valid items from
  attempt 1 are retained.
- After a failed repair the unit is recorded failed. Nothing is coerced.
- `twin_answers.retries` records the repair count.
- A 5-point item rejects `6` and `7`, reading `points` from the item register rather than a
  constant.

---

## M3 — Lookup, odometer, panel

`variant/lookup.py`, `orchestrator/odometer.py`, `orchestrator/panel.py`.

**Accept:**
- `lookup("01000").commitments` has exactly 3 keys: `2.1.a`, `2.1.b`, `2.1.c`.
- `lookup("02000")` has 6; `lookup("22222")` has 30; `lookup("00000")` has 0.
- `delta_hash` is stable across processes.
- `code_from_index`: `0→"00000"`, `1→"00001"`, `3→"00010"`, `81→"10000"`, `242→"22222"`;
  `index_from_code` is its exact inverse for all 243.
- `sum(digit_sum(code) for all 243) == 1215`.
- The panel draw is reproducible from `(panel_seed, eligible set, panel_size)` across processes, is
  stratified on `city × service`, and **excludes** twins that are `source='manual'` or not
  quality-passed (I14).
- Two sessions with different panels raise `PanelMismatch` on a cross-session interaction.

---

## M4 — Persona

`persona/templates.py`, `persona/builder.py`.

**Accept:**
- Same survey row in → byte-identical passage out, across two processes.
- A row with a missing template raises `PersonaTemplateMissing`; nothing is silently dropped (I6).
- **Every one of the 37 battery items contributes at least one clause** — assert per item, not in
  aggregate (I6, as amended in 2.0).
- The passage contains **no digits derived from a Likert value** (I7).
- The passage contains **no Part 15, 16 or 17 content** — assert none of the 34 holdout item stems
  appears (I6).
- Anchor clauses are **per scale**: a `4` on a 5-point item renders differently from a `4` on a
  7-point item (`docs/03` §7.1).
- Part 14 own-words appears verbatim as the closing section, from `twins.background`.

---

## M5 — Design agent and Checker

`variant/render.py`, `variant/checker.py`, `agents/design.py`, `agents/checker.py`,
`config/style_contract.yaml`.

**Accept:**
- Rendering all 243 codes calls the design agent **exactly 10 times** (I4) — assert on a call
  counter, not wall time.
- Every dial-0 lever renders the byte-identical string `"No change from today."` (I5).
- A poisoned render containing 2.2 language fails `containment` for `01000` (I3). **One hit fails
  the cell** — there is no threshold.
- A 41-word or 80-word render fails `in_band`.
- A coverage probe that cannot decide returns `entailed: false` (fails closed).
- `SHAM` passes every gate, contains no `"No change from today."` line, and occupies `dial = 3`.
- The design agent's `tools == []` and `build_agent` raises if a tool is added (I2).
- No prompt file for `design` or `twin` contains a few-shot example (`docs/02` §3.4) — assert by
  scanning the prompt files.

---

## M6 — Twin agent and the quality gate

`agents/twin.py`, round-prompt assembly, `TwinAnswerSet`, the H3 gate and H2 validation.

**Accept:**
- Output validates to exactly the 37 battery item ids; a missing or extra key raises.
- The round prompt contains **no** why-text, **no** open-ended answers, **no** holdout items, **no**
  version code and **no** dial digits (I8).
- `lever_order` and `seed` are persisted, and `rebuild_round_prompt()` reconstructs a stored round
  that hashes to the recorded value (I11, `docs/09` §6).
- The H3 gate keeps iff `mae <= 1.0 and pct_within_1 >= 0.80`, averaged over `repeats`.
- A quality score over zero scorable items raises `QualityScoreEmpty` (I15).
- H2 validation shows a twin **its own driver's arm**; a mismatch is a test failure
  (`docs/08` §3.1).
- Writing a quality run demotes the previous `is_latest` in the same transaction (I9).

---

## M7 — Orchestrator, budget, events, resume

`orchestrator/loop.py`, `budget.py`, `events.py`, repositories, cooperative stop.

**Accept:**
- A session stopped mid-sweep and restarted resumes at the same `cursor_index` and does **not**
  re-ask twins that already answered — assert on the LLM call count on resume.
- Killing the process mid-run and restarting marks the session `paused` and emits an interrupted
  event; **no session auto-restarts**.
- A fresh session draws and freezes its panel, then runs `00000` and `SHAM`, before the first swept
  code.
- `run_events` forms a valid tree: every `parent_event_id` resolves, no cycles.
- A checker failure marks that run `failed` and the loop continues to the next code.
- A run where every twin failed is `failed`, never `completed` with index 0.000 (I15) — assert the
  DDL constraint rejects it too.
- No `run_events.payload` exceeds 8 KB, and none contains a prompt body, a persona passage or a full
  answer vector (`docs/04` §7.2).
- `budget()` returns calls, tokens, seconds and cache hits, and its cache-hit count matches the
  calls actually skipped.
- `max_concurrency = 1` is the tested default and the pool is correct at 1.

---

## M8 — Analysis

`analysis/metrics.py`, `interactions.py`, `report.py`.

**Accept:**
- Reverse coding applied to `SAT2`, `DEP1` and `H2_SAT2` **only**, each about its own scale's
  midpoint.
- 5-point metrics are **not** rescaled to 7.
- `index` reproduces all five golden fixtures in `docs/07` §4.2 to 3 dp — in particular
  `22222 → 1.315` and `21012 → 1.027`.
- **Shifts use one twin-id set for both baseline and variant** (`docs/07` §3.1) — assert with a
  fixture where one twin failed the cell.
- `interaction()` returns `None` when any of the three cells is missing, and the UI receives the
  code to run (I17).
- The analyst bundle contains **no number absent from the computed metrics**.
- `grounded()` rejects prose containing an unlisted number, retries once, then falls back to the
  deterministic template with its prefix (`docs/02` §6).

---

## M9 — Intake and the generator

Supabase Edge Function, `ingest/survey_intake.py`, `replay_raw.py`, `generator/synthetic.py`.

**Accept:**
- An unsigned or wrongly signed POST is rejected `401`.
- The raw object is written to Storage **before** any table write; a forced insert failure leaves a
  replayable object (I16).
- An unmapped Form question raises `422` rather than being dropped.
- A response without consent statement 7 is stored and produces **no** twin.
- **Contract test:** the Edge Function and `ingest/survey_intake.py` produce identical rows from
  `apps_script/sample_payload.json`.
- The generator produces a **complete** submission — all 73 items, why-text, an assigned arm, 16 H2
  and 18 H3 answers — so a synthetic twin is quality-testable.
- Same seed → identical batch, across processes. No LLM call is made.
- Delete-synthetic removes only `data_type='SYNTHETIC'`, cascades to answers and twins, and touches
  **no** real row and **no** run.

---

## M10 — UI shell and Twin Lab

`ui/theme.py`, components, Main menu, and all eight Twin Lab tabs per `docs/06` §1 and §3.

**Accept, tab by tab:**
- **Shell:** eight routes in order; `prefers-reduced-motion` honoured; no colour-only status
  anywhere (assert every pill and dot has a text label).
- **Main menu:** counters are live Supabase counts; "Versions tested" reads **of 242**.
- **Agents:** the three workflow buttons in the specified order; each shows `budget_summary` before
  starting; the log tree polls with `after_id` and never re-fetches the stream; a parent label
  rewrites in place through twin ids on a single row.
- **Dial board:** changing a dial updates the code, score and "what the twins are told" with **no
  network call**; `00000` shows the warning and blocks *Ask the twins*; a cached code shows the
  amber badge and a `Rerun?` button; rerun creates a visible session and inherits the panel.
- **Twins:** panel order is exactly `docs/06` §3.3, including the scenario block between the
  dropdown and the tables; an untested version shows `Not tested`.
- **Validation:** the *Arm seen* column is present; the synthetic-data warning appears whenever the
  set includes synthetic twins.
- **Results:** grid click opens the panel; panel order is exactly §3.7; the tested-versions table
  carries the same data linearly; a missing interaction leg names the code to run.
- **Settings:** saving writes a new `app_config` version; completed runs keep their own config;
  there is **no** "clear runs" button.
- **`what_twins_are_told` has exactly one implementation** — assert by import graph.
- No metric is computed in `ui/` (assert no arithmetic on shift values outside `analysis/`).

---

## M11 — Twin Studio and Agent Studio

`docs/06` §5 and §6.

**Accept:**
- "From a survey answer" lists **only real, consented** respondents — synthetic rows must not
  appear.
- A hand-built twin is stored `source='manual'` and is **never** drawn into a panel.
- A studio run writes to `studio_runs` and appears in **no** metric, shift, index, Results cell or
  Statistics population.
- A custom free-text change is labelled *sandbox — not a study result*.
- Agent Studio save writes an `agent_config_history` row with `changed_fields`; restore and freeze
  each write their own.
- A frozen agent cannot be edited while a session is running.
- `native` is not offered as an output mode.
- **Run Manager's test button builds a plan and starts nothing** — assert no session is created.

---

## M12 — Statistics and the golden dataset

`stats/dataset.py`, `plssem.py`, `golden.py`, and all ten tabs.

**Accept:**
- **The golden-dataset test passes to |Δ| < 0.001 on every statistic in `docs/07` §8**, in CI.
- Two deliberate wiring faults are caught by it: a construct bound to the wrong items, and a
  reverse-coded item not reversed before estimation.
- Analysis is blocked below 30 bootstrap samples (DDL constraint plus a UI message); the default is
  5,000 and a warning shows below 1,000.
- A staged run resumes without recomputing a completed stage.
- `engine_version`, `n_cases`, `bootstrap_samples`, `seed` and `screening` appear on every result
  view.
- Export carries **two header rows**, the second being `scale_id` and `points` per column.
- `legacy_scale` rows are excluded by default and require an explicit override to pool.
- Until the golden test passes, the UI shows the `UNVALIDATED` banner.

---

## M13 — Validity tests

`validity/tests.py`, all eight, and the Validity tests tab.

**Accept:**
- Tests 1 and 3 make **zero** LLM calls — assert on the call counter.
- Test 1 scores against the H2 block and reports a paired gap with a CI.
- A test run with `twins_n = 0` records `INCONCLUSIVE`, never `PASS` — assert the DDL constraint
  rejects the alternative (I15).
- Every completed test **appends**; no test ever replaces a row (I9).
- Test 4's contradictory spec is flagged `synthetic_probe`, is never written to `variants`, and is
  unreachable from the Dial board.
- Test 6's ablated persona is flagged `ablated`, is never hashed into `twins`, and never enters a
  study run.
- Test 7 records both model names and fails on any metric sign flip.
- Test 8 reports per-metric spread across three temperatures and writes a recommended setting.

---

## M14 — Research model, invariants, deploy

`docs/06` §8, `tests/test_invariants.py`, CI, and the real deployment.

**Accept:**
- **All seventeen invariants pass as executable tests**, each naming its invariant in its docstring.
- The Research Model page renders from structured data and includes the **measurement mapping
  table** (§8.4 of `docs/06`) — without it the page and Statistics describe different studies.
- The reference list shows an empty state. **No reference is fabricated.**
- CI runs: unit tests, the invariant suite, the golden statistics test, the import-linter test, and
  `build_reference.py --check`.
- The Space deploys, boots, asserts `reference_hash`, and resumes an interrupted session.
- `hf_oauth` restricts access to the named organisation.

---

## What "done" means

A researcher can:

1. Generate synthetic surveys, or receive real ones through the Edge Function while the Space
   sleeps.
2. Import consented respondents as twins and read a persona.
3. Run the quality gate, see who was kept and dropped, and why.
4. Set five dials by hand, read what the twins will be told with no network call, see the budget,
   and ask.
5. Watch the run as an expandable tree with every agent's input and output inspectable.
6. Read the six shifts, the index, the interactions and a grounded written analysis — and click from
   any number through to Uber's own published words.
7. Run all eight validity tests and see failures reported as plainly as passes.
8. Run the full PLS-SEM battery on the human rows and export a scale-annotated matrix.
9. Stop the app, restart it, and resume the sweep where it left off.

And a reviewer can trace any number in the paper back to a verbatim extract of Uber's policy without
a gap.
