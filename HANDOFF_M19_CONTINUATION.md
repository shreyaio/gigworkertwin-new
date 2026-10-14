# HANDOFF — M19 remediation, and what is left

**Paste this whole file into a fresh session to resume.** Written 2026-10-03, at the end of the
session that executed `SYSTEM_AUDIT_AND_PLAN.md`.

**This does not supersede `HANDOFF.md`** — that file is the 1,055-line build spec and is still
current. This is the continuation note for one milestone, in the same series as
`HANDOFF_M15_LIVE_PATH.md` / `M16` / `M17`.

Read in this order: §0 (state), §1 (what is in the code), §2 (**the three loose ends** — start
here), §3 (what needs a live model), §4 (where the reasoning is).

Run everything with `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. On Windows prefix
anything that prints rendered prose with `PYTHONIOENCODING=utf-8`, and `PYDANTIC_AI_NO_BANNER=1`.

---

## 0. State, stated honestly

`SYSTEM_AUDIT_AND_PLAN.md` is **executed**: WP-1 through WP-10 are in the code, plus one defect the
plan did not name (WP-12, §1.12 below). The three research questions in its §3.2 were put to the
researcher and **answered on 2026-10-03**; they are recorded in `docs/DECISIONS.md` → "M19" as
decisions taken.

### What was actually verified

| Check | Result |
|---|---|
| **Full suite, 899 tests** | **899 passed, exit 0** |
| `ruff check src tests config` | **clean** |
| import-linter, 6 contracts | **6 kept, 0 broken** |
| `build_reference --check` | **exit 0** |
| `tests/test_m19_remediation.py` (new, 37 tests) | **37 passed** |

**One caveat on that green, stated precisely.** The confirming full-suite run completed *before*
the very last edit of the session — making Agent Studio's twin temperature box read-only
(`ui/pages/agent_studio.py:620`). That edit touches one UI page and nothing else; `ruff` was clean
after it and the three test files that cover that page were re-run (`119 passed`,
`test_m11_studios` / `test_m10_ui` / `test_d_ui_parity`). A full-suite run including it was started
and had not finished when the session ended.

So: **run the full gate first** — it should take about four minutes and read 899 passed. It is
expected to be green; if it is not, §2 is where to look.

```bash
PYTHONPATH="src;." ./venv/Scripts/python.exe -m pytest tests -q --no-header --tb=short
```

Then the other three:

```bash
./venv/Scripts/python.exe -m ruff check src tests config
```

```bash
PYTHONPATH="src;." ./venv/Scripts/python.exe -c "from importlinter.cli import lint_imports_command as c; c.main([])"
```

```bash
PYTHONPATH="src;." ./venv/Scripts/python.exe -m twinlab.ingest.build_reference --check
```

### Database

Untouched. **Every evidence table is still empty** (`runs`, `twin_answers`, `twin_quality_runs`,
`validity_results`, `session_panel` all 0), no model call was made, and nothing in this work wrote
to the live project. No migration is needed for M19 — `004_studio_origin.sql` is unchanged by it
(it shows as modified in `git status`, but that predates this session).

---

## 1. What is in the code

One subsection per work package. Each names the files to read.

### 1.1 WP-1 — the blocker: the word band is now a function of the commitment count

`style_version` **v2 → v3**. One band `[45, 150]` served commitment sets of 2 to 8, so `L1` dial 1
got 75 words per commitment and `L3`/`L4` dial 2 got 19. The design prompt asks for each commitment
in its own short sentence and the Checker probes each one for entailment, so at eight commitments
the model had to compress and the compression lost the entailments — permanently, because the one
durable re-render was already spent.

- `config/style_contract.yaml` — `style_version: v3`, the six coefficients
  (`word_min_base: 15`, `word_min_per_commitment: 18`, `word_max_base: 25`,
  `word_max_per_commitment: 30`, `word_floor: 45`, `word_ceiling: 300`), and a **HISTORY block**
  carrying the calibration table and the confound statement. Read this first.
- `config/settings.py:88` — `style_version: str = "v3"`. The two must move together;
  `validate_style_contract` refuses a disagreement.
- `variant/render.py` — new `band_for(n, style)` and `resolved_style(style, n)`, both pure.
  `build_brief` and `sham_briefs` write the resolved `word_min`/`word_max` into **the brief's own
  copy** of the contract, so the design agent is shown its own band and the Checker reads the same
  two numbers by construction.
- `variant/checker.py` — `build_report` takes `bands: dict[str, tuple[int, int]]` and raises the
  new `CheckerMisuse` for a non-dial-0 paragraph it was given no band for. There is no global band
  to fall back on, and grading against a guessed one would let an ungraded stimulus reach a twin.
- `services/twin_runtime._repair_for` — quotes the brief's resolved band, not a global one.

**Calibration** (the table is also in the YAML and in `docs/DECISIONS.md`):

| n | lever·dial | observed | band at v3 | verdict |
|---:|---|---:|---|---|
| 2 | L1·1 | 77 | `[51, 85]` | pass |
| 3 | L2·1, L1·2, L5·1, L4·1 | 88–109 | `[69, 115]` | pass |
| 6 | L2·2 | 138 | `[123, 205]` | pass |
| 8 | L3·2 | 150 | `[159, 265]` | **too short** (was: fail on coverage) |
| 8 | L4·2 | 152 | `[159, 265]` | **too short** (was: fail on band + coverage) |

The bump also **restores the paragraph budget by the principled route**: the cache key contains
`style_version`, so `attempts` is 0 on every v3 key. No counter was hand-edited.

### 1.2 WP-1b — the sham's band. **Not in the plan; raised by it.**

The plan says the sham's `n` is "the number of slots that lever announces" — 1 or 2 — which would
have put four of five sham levers in `[45, 55]` while every live lever sits at `[51, 85]` or wider.
`ARCHITECTURE.md` §5.2 requires the sham to render as *"five ordinary paragraphs, same word band
and voice as a live cell"*, and **a sham that is systematically the shortest cell in the study is
recognisable as the control by length alone** — which would have destroyed the demand-characteristic
floor every live cell is reported against.

`variant/render._sham_band_n` holds the sham to **that lever's dial-1 band**, read out of the
frozen `dial_lookup`. Zero free parameters. `check_variant` reads the sham's bands off the briefs
so the decision lives in one place.

### 1.3 WP-2 — a cached failure is a verdict, not a sentence

`services/twin_runtime.render_and_check` short-circuited on **any** stored row, and the gate stores
a report pass or fail. Each half is defensible; together they made a cell that failed once fail for
ever.

Now: a stored row that **passed** short-circuits as before; a stored row that **failed** re-renders
if the durable paragraph budget allows. The budget is read **first** —
`_levers_with_budget(code, pool)` — so an exhausted re-entry makes **zero** model calls, not even a
coverage probe (24 of them on `12220`). New `_emit_recheck` writes a `run_events` row so a free
second press says that it was free.

- `services/twin_runtime.py` — `render_and_check`, `_levers_with_budget`, `_emit_recheck`.
- `services/studio.variant_status` — returns `can_retry` and `retryable_levers`.
- `ui/pages/studio.py` — offers *"Render this version again"* only when there is budget, and
  explains the dead end when there is not.

### 1.4 WP-3 — one gate call per repeat, all six Part-17 versions

Six calls per repeat became one. **The argument is fidelity, not cost**: `docs/01` §3.6 describes
Part 17 as one section of one questionnaire answered in one sitting by a respondent who could
compare the six worlds, and `docs/08` §3.3 scores the twin on Pearson `r` *across* the six — on
whether it **orders** them as its driver did. A twin asked in six isolated contexts cannot compare.

- `agents/prompts/twin_h3_v1.md` — **new** system prompt, six-section skeleton, three fences, no
  `BASELINE`.
- `agents/twin.py` — `build_h3_prompt`, `build_h3_user_prompt`, `rebuild_h3_prompt`,
  `h3_version_seed`, `H3_BLOCK_ORDER`, `H3_VERSION_LABEL`. Six blocks labelled *Version 1…6* in
  `version_shown` order; **the version codes never reach the prompt** (I8). Each version draws its
  own lever order from the one stored seed, so all six rebuild from it and they are not identical
  to each other.
- `models/twin.py` — new `H3RoundPrompt`.
- `services/twin_runtime.ask_h3_round` — one call over the 18 ids, reusing `run_answer_ladder` with
  `QualityAnswerSet`. **No new validation path.** `H3_PROMPT_REF`, `H3_PROTOCOL` constants;
  `twin_agent_config` gained `prompt_ref`.
- `services/quality._gate_one_twin` — the inner per-code loop is gone.
- `orchestrator/budget.py` — `H3_CALLS_PER_REPEAT = 1`, `H3_VERSIONS_PER_CALL = 6`, and **H3-specific
  cost rates** (`H3_SECONDS_PER_CALL = 20`, `H3_TOKENS_IN_PER_CALL = 6500`): an H3 call carries six
  scenarios, and costing it at the battery's 8 s understated the gate's wall-clock by ~2.5×.
  `_budget` gained `seconds_per_call`.
- `twin_quality_runs.detail["protocol"]` records `h3_single_call_v1` on every row.
  **Six-in-one-context and six-in-isolation are different measurements and cannot be pooled.**

**10 twins × 2 repeats = 20 calls.** Verified on the call counter in
`test_wp3_a_gate_over_three_twins_makes_six_h3_calls_not_thirty_six`.

### 1.5 WP-4 — render all six stimuli, report all six, then halt

`services/quality._render_stimuli`. The halt is unchanged and still correct; the *granularity of
the diagnosis* was the defect. `12220` is first in `h3_version_codes`, so raising on the first
failure meant three renders that would also have failed were never attempted.

### 1.6 WP-5 — the Dial board can ask, and ask everybody

- `ui/pages/lab._dial_board_tab` — rewritten. Population radio, editable panel size, *use every
  eligible twin* checkbox, live counts, and a **confirm step with the budget** before anything
  starts. `_ask` passes `population=` and `panel_size=` through; **`_rerun` deliberately passes
  neither** (a rerun inherits the panel — I14).
- `models/twin.TwinConfig.panel_size: int | None` — `None` means "whatever `PANEL_SIZE` says".
  Validator refuses `< 1` (I15).
- `services/runs.effective_panel_size()` — the precedence, mirroring the twin temperature.
  Every `settings.panel_size` read in the service and UI layers now goes through it.
- `ui/pages/lab._settings_tab` — `panel_size` moved from the read-only environment column to the
  editable `TwinConfig` column; `PANEL_SIZE` stays on the right, relabelled as the default.
- `_stored_population` was promoted to module level, because two screens now open a control on it.

### 1.7 WP-6 — the validity tests run, fail loudly, and are aimable

Five distinct fixes in `services/validity.py`:

1. `_TASKS` set + done-callback (`_report_validity_death`) appending an `INCONCLUSIVE` row naming
   the exception. The task was previously discarded by the UI — the one background path in the
   codebase without this guard.
2. `_test_with_calls` refuses an empty stimulus and makes zero calls.
3. **`_paragraphs_for` now checks `checker.passed`** — see §1.11, this was an I3 breach.
4. `services/runs.latest_session_with_panel()` and `sessions_with_panels()`; `run_validity_test`
   defaults to the former.
5. `test_readiness(number, ...)` and `runnable_version_codes()`, surfaced per card.

Plus `services/twin_runtime.ask_panel_twins` now catches `RoundPromptError`, which was caught
**nowhere** in the codebase.

`ui/pages/lab._validity_tab` — three aiming controls (session, version, second model), a readiness
line on every card, and the aim passed through to both the inline and the enqueued paths.

### 1.8 WP-7 — the Validation tab is honest and live

`ui/pages/lab._validation_tab`. The button is a **refresh** and is named one; the tab is a
read-only view over `twin_quality_runs` and says so; the empty state counts what is missing
(`view.twins_total`) instead of naming a disabled button; a protocol line warns when rows mix H3
protocols. `models/view.ValidationSummary` gained `twins_total` and `h3_protocols`.

### 1.9 WP-8 — Agent Studio governs the runtime. **This reverses an M18 holding position.**

The largest package. Edits were saved, versioned, audited — and read by nothing but Agent Studio.

- `agents/registry.py` — `_LIVE`, `_LIVE_VERSIONS`, `set_live_agent_configs`,
  `live_agent_configs()`, `live_agent(id)`, `live_agent_versions()`, `reset_live_agent_configs()`,
  and `AgentDisabled`. **The merge lives here and the database read lives in the service**, because
  `agents/` may not import `db/` and `variant/` importing `services/` would invert the layering.
- `services/agent_config.refresh_agent_configs` — reads the rows and pushes them down. Mirrors
  `services/config.refresh_twin_config` including its failure policy.
- **The five call sites** now read `live_agent(...)`: `twin_runtime` (design re-render, twin,
  analyst), `variant/checker.py` (coverage probe), `variant/render.py` (first render).
- `services/config.startup_check` → `_refresh_agent_configs` at boot, **after**
  `_correct_agent_models`.
- `services/runs.session_config` → `payload["agent_versions"]`, frozen onto every session, gate and
  Studio ask. **I11 is strengthened**: a run records which agent version produced it.
- `enabled` gates things: `design`/`twin` disabled fails loudly; `analyst` disabled uses the
  existing deterministic template and makes **no** model call; **`checker` cannot be disabled** —
  refused in `save_agent` via `UNDISABLEABLE`, naming I3.
- `in_force()` was **rewritten** — it existed to report the gap, and the gap is closed.
- `services/menu.AGENT_STEPS` + `ui/components/domain.agent_card` — each agent's **two steps**, the
  model-free one and the one that costs a call. The Policy Designer is why: choosing the commitment
  set is a frozen lookup with no model in it (I1).
- `ui/pages/agent_studio._in_force_line` — the closing sentence said *"it does not change what the
  runtime loads"*, which WP-8 made **false**. Rewritten.

`validate_config` runs on every merged config, so a stored row cannot give the design agent or the
twin a tool (I2, I6) or introduce `native` output (I13). A row that will not validate falls back to
the seed **for that agent only**, logged once.

### 1.10 WP-9 / WP-10 — the two smaller ones

- `ui/pages/lab._settings_tab._save` — the message no longer says *"Edit the YAML to change
  behaviour."* It was false: `refresh_twin_config` reads the row and `session_config` calls it
  before every session. A researcher who believed it edited YAML by hand, outside the
  `config_version` that `twin_quality_runs` records.
- `services/config._check_style_version_row` — warns at boot when `app_config['style']` disagrees
  with `settings.style_version`. See §2.3.
- `models/view.py` — `BASELINE_MEASURED`, `BASELINE_NOT_MEASURED`, `BASELINE_NOT_MEASURED_NOTE`,
  `BASELINE_COLUMN_HEADER`; `TwinPanel.baseline_state`. The column is `Twin today (00000)` and an
  unmeasured baseline is **one sentence**, not a column of dashes — a dash can be read as a zero,
  and I17 forbids that.
  (`BASELINE_COLUMN_HEADER` lives in `models/` because `ui/` may not import `orchestrator/`, where
  `CONTROL_CODE` is; a test pins the literal against the constant.)

### 1.11 An I3 hole the plan did not name

`services/validity._paragraphs_for` was documented as returning the "Checker-**passed**"
paragraphs. Its query filtered on `(version_code, style_version)` only and returned the latest row
**whatever its verdict** — so a variant the Checker had *rejected* would have gone to validity
tests 4–8 and been put to the panel. It was the third read site of a stored variant and the only
one that did not check `passed`. Fixed, with a test asserting zero calls on the refusal path.

### 1.12 WP-12 — the demand floor was missing from the Dial board. **Not in the plan.**

`ARCHITECTURE.md` §5.2 requires `SHAM − 00000` "reported alongside every live cell" and §9 that a
cell below it is not interpretable. `services/results.results_panel` passed `floor=`; the Dial
board's cached-result path did not, so `floor_note` was always `None` there.

Separately, `floor=None` rendered as **silence**, indistinguishable from "it cleared the floor".
`services/metrics_view.build_metric_bars` now has three states: below, above, and **not measured**,
each said plainly.

### 1.13 Verified correct, so deliberately unchanged

Recorded so a future session does not re-audit them: metric bars coloured by `index_sign × value`
not by sign; dial colours red/amber/green for 0/1/2; I10 (37 battery items, `AMQ6`/`ALGO5` absent);
the odometer over all 243 with Representation least significant; the four human arms; H2 showing a
twin its own driver's arm and *raising* on a mismatch; the bootstrap floor 30 / default 5,000 /
warn below 1,000 reaching the screen; the generator seed persisted on `synthetic_batches.seed`; no
dead service code; and M18's A-19 (an idle Agents tab makes zero database calls) still intact.

---

## 2. The three loose ends. **All three are now closed — 2026-10-04.**

> **Closed on 2026-10-04**, in the session that read this file. §2.2 and §2.3 are **done**; §2.1 was
> already history. Gate re-run after the work: **900 passed** (899 + 1 new test), `ruff` clean,
> 6 import-linter contracts kept, `build_reference --check` exit 0. Every evidence table is still
> **0** and no model call was made. The decisions are in `docs/DECISIONS.md` →
> "M19 continuation". **Nothing in §2 needs doing; go to §3.**
>
> Two things a reader of §2.2 and §2.3 below should know, because both sections state the problem
> correctly and the *fix* turned out not to be the one they propose:
>
> 1. **§2.2's "omit `temperature` from the `changes` dict" is not a no-op on its own.** `save_agent`
>    **replaced** the nested `model` dict, so an omitted `temperature` fell through to `ModelRef`'s
>    default of `0.2` — a change, not a preservation. `save_agent` now merges `model`
>    field-by-field, which also fixed a latent defect neither document names: Agent Studio's save
>    only ever sent `provider`, `name` and `temperature`, so **every save silently reset a stored
>    `max_tokens` to 2048 and a stored `seed` to `None`**. A reset seed is a provenance loss (I11).
> 2. **§2.3's "reseed or patch the one row" are not equivalent, and the reseed is the destructive
>    option.** `ingest/seed_db.build_rows` also rewrites `app_config['twin']` — on the live project
>    at **version 3**, holding the 0.25 twin temperature and `quality_runs_per_twin`, the live
>    subject of validity test 8 — and every `agent_configs` row with it. The row was patched alone,
>    its value read from `config/style_contract.yaml`, `version` 1 → 2. `app_config['style']` now
>    reads `v3` and the boot warning is silent. The warning itself **stays**, because the row can
>    drift again on the next `style_version` bump.

§2.1 is history rather than work — it is here because the cause is worth knowing if anything like
it recurs. §2.2 and §2.3 were the two real open items, and both were small.

### 2.1 A test-pollution fix landed late — fixed, but know the shape of it

`tests/test_m19_remediation.py`'s WP-9 test saves `quality_runs_per_twin = 2`, and
`refresh_twin_config` installs it as a **process-level** override. Without a restore, the next test
file in the run inherited it and `test_m6_twin_quality`'s assertion of the seeded 3 failed — **in
the full suite only**, which is the worst shape of test pollution to find.

The `_fresh_process_state` autouse fixture now saves and restores `services.config._override` and
`_override_version`, matching `test_m16_settings_apply`'s existing pattern. **Fixed and confirmed
by a full green suite** (899 passed).

**If other process-global leaks appear,** the three this fixture resets are the pool
(`twin_runtime.reset_pool`), the live agent config (`reset_live_agent_configs`) and the twin config
override. A fourth would most likely be `_rerendered` (reset by `reset_pool`) or
`default_agent_configs`'s `lru_cache`.

### 2.2 One edit I was mid-way through and did **not** apply — **APPLIED 2026-10-04**

**Agent Studio's temperature box is read-only for the twin** (`ui/pages/agent_studio.py:620`,
`interactive=not v["temperature_read_only"]`, with the label *"Temperature (set in Twin Lab →
Settings)"*). That landed.

What did **not** land: `_save` (`ui/pages/agent_studio.py:686`) still sends
`"temperature": float(temp)` for every agent, including the twin. For the twin the box now shows
the value *in force* (from `app_config['twin']`), so saving copies that into the `agent_configs`
row.

**It is harmless** — `twin_agent_config` overrides the row's temperature with
`load_twin_config().temperature` regardless, so nothing runs differently. But it leaves two places
holding the same number, which is the shape of problem WP-8 item 5 set out to remove.

**The intended change:** omit `temperature` from the `changes` dict when
`agent_id == "twin"`, so the stored row keeps whatever it had and there is visibly one owner. One
condition, plus a test that a twin save does not alter the row's temperature. Decide whether it is
worth it — the argument against is that a row whose temperature is stale is its own small lie.

### 2.3 `app_config['style']` on the live project still says `v1` — **PATCHED to `v3` 2026-10-04**

**Nothing reads it** — the contract is read from `config/style_contract.yaml` — so no stimulus is
affected and it cannot produce a wrong render. But it is a second, wrong declaration of the render
cache key sitting in the evidence database, and it will mislead the first person who inspects it.
It said `v1` against a running `v2`; it now says `v1` against a running `v3`.

`ingest/seed_db.py` writes that row from the YAML, so **a reseed corrects it**. Until then
`startup_check` logs a warning at boot naming both values. Your call whether to reseed or to patch
the one row.

---

## 3. What needs a live model — in this order

Nothing below could be done in the session: it needs `OLLAMA_API_KEY` against the real Supabase
project. **Step 1 must come first**; everything else is downstream of it.

1. **Render the ten lever paragraphs under v3.** 10 design calls + 5 sham slots = **15 calls, about
   two minutes.** `attempts` is 0 on every v3 key.
   *Pass:* all ten render and all five Checker gates pass. The two that could not be rendered under
   v2 — `L3` and `L4` at dial 2 — now have `[159, 265]` instead of being compressed into 150.
2. **Render the six H3 stimuli** (plan checkpoint 5). *Pass:* all six `passed=True`. This gates
   everything else. If one fails, read the Checker's note before pressing again — and note that a
   second press now **re-renders within the budget** rather than returning the same verdict for
   free, and says in the Agents log which it did.
3. **The quality gate on 10 twins × 2 repeats** (plan checkpoint 7). *Pass:* the budget card reads
   **20 calls**, the gate completes, ten `twin_quality_runs` H3 rows with
   `detail.protocol = "h3_single_call_v1"`.
   **One correction to the plan:** its acceptance check A-2 asks for `items_n = 18` per row, but
   `validity.quality.average_scores` deliberately **sums** `items_n` across repeats — it is a count
   of measurements taken, so the verdict says how much evidence it rests on. The correct figure is
   `18 × quality_runs_per_twin` = **36** at two repeats. The code's reading is the better one;
   **A-2's wording needs correcting, not the code.**
4. **A Dial board ask** (plan checkpoint 9). Set the dials, pick `synthetic`, tick *use every
   eligible twin*, read the confirm step, press Start. *Pass:* the session runs, every kept twin
   answers, the cell appears in Results with `twins_n = N`.
5. **The validity tests** — they need step 4's session to exist before there is a panel to aim at.
   Every card states what it is waiting for before the button is pressed; a test that dies in the
   background appends an `INCONCLUSIVE` row naming the exception.
6. **WP-11, the Twin Studio verification pass.** The free-text path **is verified** (needs no
   variant, stays sandboxed, writes no `runs` row). The rest sits after step 1: render `22000` on
   demand, ask, ask again and confirm the latest pointer moved while the earlier row survived, the
   `origin='studio'` / `twins_n=1` filing, and validation-plan **C-11** / **C-12** (*From a survey
   answer*, *Make one by hand* — a hand-made twin must show an **empty** baseline column, not
   zeros).
7. **The plan's §6 test protocol** — delete the 50 synthetic twins, generate 20 frustrated drivers,
   re-run. **Record the seed**: it is now named on the confirmation line after *Generate surveys*.
   The plan's own confound warning stands — 20 twins from one sentiment preset is a low-variance,
   strongly-correlated panel, fine for plumbing and **not** a study panel.

**Still the gate on the study itself:** `HANDOFF_M17_VALIDATION_PLAN.md` §5.1 and §5.2, untouched
by this work.

---

## 4. Where the reasoning is

- **`M19_REMEDIATION_RESULTS.md`** — the results doc for this milestone: status table, the three
  things the plan did not catch, what the wiring audit found, and what needs a live model. Written
  for a reader who has not seen the code.
- **`docs/DECISIONS.md` → "M19"** — every decision. The three researcher answers with their
  arguments, 19 mechanical decisions each with its reason, what remains open, and **three documents
  this work supersedes** (see below).
- **`config/style_contract.yaml` → the v3 HISTORY block** — the calibration table, the measured
  series that forced the change, and the confound statement.
- **`tests/test_m19_remediation.py`** — 37 tests, one section per work package, each naming the
  package and the invariant it protects.
- Reframed tests live **beside the behaviour they originally pinned**, so a reader of those files is
  not told two different stories: `test_m5_render_checker.py` (word band),
  `test_m17_i3_stored_variant.py` (cached failure), `test_m7_orchestrator.py` and
  `test_m18_usability.py` (budget), `test_m16_render_budget.py` (style version),
  `test_m13_validity.py` (the stimulus fixture).
- `SYSTEM_AUDIT_AND_PLAN.md` — keep for its diagnoses. **Do not work from its task list**; it is
  done.

### Documents that now need correcting at write-up

1. **`docs/10`'s "the quality gate is the dominant cost of the study, not the sweep"** no longer
   holds arithmetically. After WP-3 the gate is 1,500 calls at N=500 × 3 and a full 243-cell sweep
   at K=20 is 4,915 — the sweep is now ~3.3× larger. The *structural* claim is unchanged and is
   what the comparison was ever for: the gate is paid on every consented twin, the sweep only on
   the frozen panel. `test_m7_orchestrator.py::test_the_gate_scales_with_the_population_and_the_sweep_with_the_panel`
   pins both.
2. **`SYSTEM_AUDIT_AND_PLAN.md`'s A-2** — `items_n`, as §3 step 3 above.
3. **`docs/11` M5's word-band bullets** ("a 41-word or 80-word render fails `in_band`") — superseded
   twice over, by the 2026-09-29 widening and by v3's per-commitment band.

### Open research questions carried forward

- **The word-length confound.** Paragraph length covaries with dial by construction. Declared in
  `docs/DECISIONS.md` and belongs in the paper's limitations. Whether the analysis should carry a
  word-count covariate is open.
- **`quality_runs_per_twin` is 2, against `docs/08` §2.1's 3.** The reason for the reduction was
  cost, and WP-3 largely removes it: 3 repeats at 10 twins is now 30 calls instead of 180. Worth
  revisiting.
- **Twin temperature** is 0.25 in `app_config` against a seeded 0.7, chosen by neither measurement.
  Validity test 8 sets it, and WP-6 is what makes test 8 runnable. Do not pick it before then.
- **Should a Studio result from a quality-dropped twin be filed?** Unchanged from M18.
  `_require_quality_passed` refuses; it is one line either way; researcher's call.
- **The sweep population.** Unchanged from M18. WP-5 extends the explicit control to the Dial
  board; which population a *study* sweep runs on remains a decision taken at the moment of running
  it.

---

## 5. Rules that bit during this work, worth knowing before you edit

- **`CLAUDE.md` rule 1 — never relax an invariant to make a test pass.** Six test files were
  reframed, and every reframing is a *specification change the researcher approved*, documented in
  the test's own docstring. None of them weakened an assertion to accommodate the code.
- **The layer table is enforced.** `ui/` may not import `orchestrator/` — a UI test catches it even
  though import-linter does not, which is why `BASELINE_COLUMN_HEADER` lives in `models/`. `agents/`
  may not import `db/`, which is why WP-8's merge is in `agents/registry.py` and the read is in
  `services/`.
- **A full-suite-only failure is almost always process-global state.** See §2.1.
- **If you edit `config/style_contract.yaml` after a paragraph has been persisted, bump
  `style_version`.** The file's own header states this as a MUST, and it bit for the first time in
  M16.
