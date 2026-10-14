# M19 — the remediation, applied

**Written 2026-10-03 against `SYSTEM_AUDIT_AND_PLAN.md`.** Every work package in that plan is in
the code. **No model call was made and nothing was written to the evidence tables** — the suite
uses a stub client and an in-memory backend, as `CLAUDE.md` requires.

The three research questions in the plan's §3.2 were **put to the researcher and answered on
2026-10-03**. They are recorded in `docs/DECISIONS.md` → "M19" as decisions taken, not as
defaults picked by the agent.

Read §3 before running anything: it lists the five things that still need a live model, and one
of them must come first.

---

## 0. Status against the plan

| WP | What it fixes | State |
|---|---|---|
| **WP-1** | The blocker: one word band for 2–8 commitments | **Done.** `style_version: v3`, band = `f(n)`, calibrated against the eight paragraphs actually rendered. |
| **WP-2** | A cached failure was a life sentence | **Done.** The verdict is cached, the attempt is not. An exhausted re-entry costs **zero** model calls. |
| **WP-3** | 6 gate calls per repeat where 1 would do | **Done.** One call, all six Part-17 versions. 10 twins × 2 = **20 calls**. |
| **WP-4** | The gate halted on the first bad stimulus | **Done.** All six rendered and reported, then halt. |
| **WP-5** | The Dial board could not succeed on this database | **Done.** Population, editable panel size, *use every eligible twin*, and a budget before anything starts. |
| **WP-6** | Validity tests failed silently; the UI reported success | **Done.** Task held, death reported, stimulus refused, session aimable, readiness per card. |
| **WP-7** | The Validation tab's only button was inert | **Done.** It is a refresh, named as one, and the empty state names the gate. |
| **WP-8** | Agent Studio edits were saved and never used | **Done.** Five call sites read the live config; the version is frozen onto every session. |
| **WP-9** | The Settings tab stated something false | **Done.** The message is true, `panel_size` is editable, the stale `style` row warns at boot. |
| **WP-10** | "Twin today" was empty with no explanation | **Done.** Labelled `Twin today (00000)`, with a sentence instead of a column of dashes. |
| **WP-11** | Verification pass over the Twin Studio | **Partly.** The free-text path is verified; the rest needs live calls — §3. |
| **WP-12** | *(not in the plan)* the demand floor was missing from the Dial board | **Done.** §2.1. |

**Gate:** **899 tests pass** (855 before; +37 new M19 tests and +7 from splitting reframed ones),
`ruff` clean on `src`, `tests` and `config`, all **6 import-linter contracts hold**, and
`build_reference --check` exits 0.

One note on how that was arrived at, because it is the kind of thing worth saying rather than
quietly fixing: the first full run after WP-10 showed **1 failure that passed in isolation**.
`test_m19`'s WP-9 test saves `quality_runs_per_twin = 2` and `refresh_twin_config` installs it as
a **process-level** override, so the next test file in the run inherited it and
`test_m6_twin_quality`'s assertion of the seeded 3 failed. The fixture now saves and restores
`services.config._override`, which is the pattern `test_m16_settings_apply` already had for the
same reason. Full-suite-only failures are the worst shape of test pollution to find, so it is
recorded here.

---

## 1. Three things the plan did not catch

These are reported first because two of them are research-validity issues and one is an invariant
breach.

### 1.1 The sham would have become recognisable as the control

The plan says the sham's word band comes from "the number of slots that lever announces". That is
1 or 2, so under WP-1's formula four of the sham's five levers would land in **`[45, 55]`** while
every live lever sits at `[51, 85]` or wider — up to `[159, 265]`.

`ARCHITECTURE.md` §5.2 requires the sham to render as *"five ordinary paragraphs, **same word band
and voice as a live cell**"*. A sham that is systematically the shortest cell in the study is
recognisable as the control by length alone, and **a twin that can tell it is looking at a control
is not measuring the demand characteristic the cell exists to measure.** That would have quietly
destroyed the floor every live cell is reported against.

**Fixed**: the sham's band is **that lever's dial-1 band**, read straight out of the frozen
`dial_lookup` — the smallest real intervention the lever can carry. Deterministic, constant, and
with zero free parameters, which is the property §5.2 cares about most.

| Lever | Announces | Band under the plan's reading | Band as implemented |
|---|---:|---|---|
| L1 | 1 | `[45, 55]` | `[51, 85]` |
| L2 | 1 | `[45, 55]` | `[69, 115]` |
| L3 | 2 | `[51, 85]` | `[87, 145]` |
| L4 | 1 | `[45, 55]` | `[69, 115]` |
| L5 | 1 | `[45, 55]` | `[69, 115]` |

### 1.2 An I3 hole: validity tests 4–8 would have been handed a *rejected* variant

`services/validity._paragraphs_for` is documented as returning "the stored, Checker-**passed**
paragraphs". Its query filtered on `(version_code, style_version)` only and returned the latest
row **whatever its verdict**. So a variant the Checker had rejected would have gone straight to
the panel.

It was the third read site of a stored variant and the only one that did not check `passed` —
`studio._stimulus` and `quality._render_stimuli` both refuse on the same ground. I3 has no
exemption for a validity test. **Fixed and covered by a test that asserts zero model calls on the
refusal path.**

### 1.3 WP-3 inverts `docs/10`'s claim about which cost dominates

`docs/10` names the quality gate *"the dominant cost of the study, not the sweep"*, and that was
arithmetically true: 9,000 calls at N=500 × 3 against 4,915 for a full 243-cell sweep at K=20.

After WP-3 the gate is **1,500** calls and the full sweep is still **4,915** — so the sweep is now
about **3.3× larger**. The *structural* claim is unchanged and is what the comparison was ever
for: the gate is paid on every consented twin, the sweep only on the frozen panel, so the gate is
the cost that grows with fieldwork. **The literal sentence in `docs/10` needs correcting**, and
`tests/test_m7_orchestrator.py::test_the_gate_scales_with_the_population_and_the_sweep_with_the_panel`
now pins both the inversion and the structural claim so it cannot be rediscovered by surprise.

---

## 2. What the wiring audit turned up beyond the plan

The plan's eleven defects were the brief. Sweeping the rest of the codebase for the same *class* of
defect — a control that does nothing, a handler whose logic diverges from its stated intent, a
write nothing reads — turned up one more.

### 2.1 WP-12 — the demand floor was missing from the Dial board

`ARCHITECTURE.md` §5.2: *"`SHAM − 00000` is the demand-characteristic floor and is reported
**alongside every live cell**. Any cell whose shift is smaller than that floor is **not
interpretable**."*

`services/results.results_panel` passed `floor=await session_floor(db)` to `build_metric_bars`.
The Dial board's cached-result path (`ui/pages/lab`) did **not**, so `floor_note` was always
`None` there — a researcher reading a cached cell on the Dial board saw an index with no statement
about whether it clears the floor, which is exactly the reading the control cells exist to
prevent.

Separately, `floor=None` rendered as **silence**, and silence is indistinguishable from "it cleared
the floor" — the same defect WP-10 fixed for the baseline column. There are now three states, each
said plainly: below the floor, above it, and *not measured*.

### 2.2 Verified correct, and worth recording as such

Checked against the specification and found right, so nothing was changed:

- **Metric bars are coloured by "good for the driver", not by sign** (§9's warning that getting it
  backwards inverts the headline finding on every screen). `good_for_driver = index_sign × value >
  0`, with the sign read from the frozen `constructs.index_sign` — not from config, so a researcher
  editing a config cannot invert what a metric means.
- **Dial colours** are red/amber/green for 0/1/2, from `--tl-bad` / `#F0B429` / `--tl-ok`.
- **I10**: the twin battery is 37 items; `AMQ6` and `ALGO5` are absent. 18 H3 holdouts, 16 H2.
- **The odometer**: `0→00000`, `1→00001`, `3→00010`, `81→10000`, `242→22222`, round-trips over all
  243, Representation least significant.
- **The four human arms** map to `00000 / 00010 / 01000 / 00001` as §5.3 specifies.
- **H2 shows a twin its own driver's arm** and *raises* on a mismatch rather than recording it.
- **The bootstrap floor**: hard 30, default 5,000, warning below 1,000, and the warning reaches the
  screen.
- **The generator seed** is persisted on `synthetic_batches.seed` with `batch_id` on every
  submission, so a batch is reproducible from `(seed, count, spec)`. It was not *shown* after
  generation, and the plan's §6 asks the researcher to record it — so the confirmation line now
  names it.
- **No dead service code**: every public function in `services/`, `variant/` and `orchestrator/`
  has a caller. One disabled button remains in the whole UI — the Dial board's *Ask the twins* —
  and its dial handler correctly re-enables it for every code except `00000`.
- **`_require_quality_passed`** still refuses to *file* a Studio result for a dropped twin. Left
  alone; it is open question §7.2 item 1 and is the researcher's call.

---

## 3. What still needs a live model — in this order

Nothing below could be done here: it needs `OLLAMA_API_KEY` against the real Supabase project, and
the plan's own §5 sequences it. **Step 1 must come first** — everything else is downstream of it.

1. **Render the ten lever paragraphs under v3.** 10 design calls + 5 sham slots = **15 calls, about
   two minutes.** `attempts` is 0 on every v3 key, so the budget is intact.
   *Pass:* all ten render and all five Checker gates pass. The two that could not be rendered under
   v2 — `L3` and `L4` at dial 2 — now have a `[159, 265]` band instead of being compressed into 150.
2. **Render the six H3 stimuli.** *Pass:* all six `passed=True`. This is the plan's checkpoint 5,
   and it is the gate on everything else. If any fails, read the Checker's note before pressing
   anything again — and note that from WP-2 a second press now **re-renders within the budget**
   rather than returning the same verdict for free, and says in the Agents log which it did.
3. **The quality gate on 10 twins × 2 repeats.** *Pass:* the budget card reads **20 calls**, the
   gate completes, and ten `twin_quality_runs` H3 rows appear with `detail.protocol =
   "h3_single_call_v1"`.
   One caveat on the plan's acceptance check A-2: it asks for `items_n = 18` per row, but
   `average_scores` deliberately **sums** `items_n` across repeats, so the correct figure is
   `18 × quality_runs_per_twin` = 36 at two repeats. The code's reading is the better one — it
   makes the verdict say how much evidence it rests on — so **A-2's wording needs correcting**, not
   the code.
4. **A Dial board ask.** Set the dials, pick `synthetic`, tick *use every eligible twin*, read the
   confirm step, press Start. *Pass:* the session runs, every kept twin answers, and the cell
   appears in Results with `twins_n = N`.
5. **The validity tests**, which need step 4's session to exist before they have a panel to aim at.
   Every card now states what it is waiting for before the button is pressed, and a test that dies
   in the background appends an `INCONCLUSIVE` row naming the exception.

**WP-11's remaining items** (render `22000` from the Studio on demand, ask twice and confirm the
latest pointer moved, the `origin='studio'` filing, *From a survey answer* and *Make one by hand*)
sit after step 1. The free-text path is verified here: it needs no variant, stays sandboxed, and
writes no `runs` row.

---

## 4. One thing to apply by hand

`app_config['style']` on the live project still declares `style_version: v1`. **Nothing reads it**
— the contract is read from `config/style_contract.yaml` — so no stimulus is affected and it cannot
produce a wrong render. But it is a second, wrong declaration of the render cache key sitting in the
evidence database, and it will mislead the first person who inspects it.

`ingest/seed_db.py` writes that row from the YAML, so **a reseed corrects it**. Until then
`startup_check` logs a warning at boot naming both values.

No migration is needed for M19. `004_studio_origin.sql` is unchanged by this work.

---

## 5. Where to read the reasoning

- `docs/DECISIONS.md` → **"M19"** — every decision, the three researcher answers with their
  arguments, the confound WP-1 makes explicit, what remains open, and the three documents this work
  supersedes.
- `config/style_contract.yaml` → the **v3 HISTORY block** — the calibration table, the measured
  series that forced the change, and the confound statement.
- `tests/test_m19_remediation.py` — 37 tests, one section per work package, each naming the package
  and the invariant it protects.
- The reframed tests live beside the behaviour they originally pinned, so a reader of those files is
  not told two different stories: `test_m5_render_checker.py` for the word band,
  `test_m17_i3_stored_variant.py` for the cached failure, `test_m7_orchestrator.py` and
  `test_m18_usability.py` for the budget.

---

## 6. What this does not do

It does not render a stimulus for the paper, produce a number for the paper, or decide a research
question. It removes the wall the plan identified and fixes the defects behind it, and it makes
every screen it touched tell the truth about what it is showing.

The gate on the study itself is still `HANDOFF_M17_VALIDATION_PLAN.md` §5.1 and §5.2, which are
untouched here.
