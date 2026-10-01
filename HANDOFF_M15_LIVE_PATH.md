# Handoff — M15, wiring the live twin path

**Session of 2026-09-30. Paste this whole file into a fresh session to resume.**

Read `CLAUDE.md`, then `HANDOFF.md` §0.5 and §0.7, then this file. This file supersedes nothing in
`HANDOFF.md`; it records what changed on 2026-09-30 and what is still unverified.

Use `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. Bare `python` is a different interpreter
without `pydantic_ai` or `openpls` (`HANDOFF.md` §0.0).

---

## 0. One-paragraph summary

Before this session **no live twin path existed anywhere in the build** — the Agents tab's three
buttons enqueued a stub, Twin Studio's *Ask the twin* recorded a row with `model="mock"` and no
answers, and validity tests 4–8 recorded `INCONCLUSIVE` by construction. That path now exists
(`services/twin_runtime.py`, `services/quality.py`) and every button on every screen named below is
wired to it. **749 tests pass, `ruff` is clean, the 6 import-linter contracts hold.**
**But no twin has yet answered a single question against the live model**, because every
multi-lever stimulus still fails the Checker on the register band, and because of a defect in the
provider output type found at the end of the session and *not* fixed (§3.1). Fix §3.1 first; it is
the one thing standing between this code and a first real answer.

---

## 1. What was changed

### 1.1 New files

| File | What it is |
|---|---|
| `src/twinlab/services/twin_runtime.py` | The live twin path. `render_and_check`, `ask_items`, `ask_twin`, `analyse`, `candidates`, `runner_callables`, `ask_panel_twins`, `StoredParagraphPool`. The only module in `services/` that reaches `agents/` and `variant/`. |
| `src/twinlab/services/quality.py` | The quality gate runner. `start_quality_gate`, `run_quality_gate`, H3 + H2, writes `twin_quality_runs` through the `quality_run_record` RPC, emits into `run_events`. |
| `HANDOFF_M15_LIVE_PATH.md` | This file. |

### 1.2 Changed files

| File | Change |
|---|---|
| `services/runs.py` | **Fixed the reported crash**: `load_twin_config().quality_repeats` → `.quality_runs_per_twin` (the field has never existed under the old name). Added `start_sweep`, `resume_session`, `session_config`, `paused_sessions`, `get_session`, `_with_runtime` (injects the runner callables by default). Re-exports `SessionAlreadyRunning`. |
| `services/config.py` | `load_twin_config()` now returns **`app_config['twin']` merged over the YAML seed**; the old lru-cached YAML read is `seed_twin_config()`. Added `refresh_twin_config()` and `twin_config_version()`. `startup_check()` refreshes at boot. This is why a Settings save now takes effect. |
| `variant/checker.py` | Added `distinctive_signatures()`; `containment_hits()` now fires only on a bigram belonging to **one** forbidden commitment. **Researcher decision, taken in-session.** |
| `agents/design.py` | `run_design()` takes an optional `instruction`, appended to the user prompt. Used only by the one specified re-render. |
| `services/studio.py` | Added `QUESTION_PROMPT`, `StudioBlocked`, `ask_studio`, `_stimulus`, `_ask_questions`. |
| `services/agent_config.py` | Added `checker_test_view`, `twin_test_view`. |
| `models/twin.py` | Added `StudioReply` (with `aligned()`, which refuses a mismatched reply count). |
| `models/view.py` | Added `StudioMetricRow`, `StudioResult`. |
| `ui/components/primitives.py` | `data_table(row_keys=..., row_attr=...)` — clickable rows. |
| `ui/theme.py` | `tr.tl-row-pick` / `.tl-row-on` styles. |
| `ui/pages/lab.py` | `_row_click_js()`; Twins tab rows clickable + *Run twin quality test* wired to the filtered selection with a budget confirm; Agents tab `_start` really starts, plus Stop and Resume; `_poll` resets on a new session and drives the job line; Dial board *Ask the twins* starts a session on a cache miss and *Rerun?* is live; validity tests 4–8 get the live `ask`. |
| `ui/pages/studio.py` | `_ask` calls `ask_studio`; added `_said_html`. |
| `ui/pages/agent_studio.py` | `_test_panel` takes the prompt box; added `_checker_html`, `_twin_html`. |
| `tests/test_m5_render_checker.py` | Extended the empty-signature test to distinctive signatures; added `test_a_bigram_shared_between_commitments_is_not_a_leak`. |
| `tests/test_m10_ui.py` | Fixed a **pre-existing** broken test (§2.5). |
| `docs/DECISIONS.md` | New `## M15` section recording every decision below. |

---

## 2. What was tested, and what was observed

Everything in this section was actually run. Nothing here is inferred.

### 2.1 Environment — verified live

```
backend: supabase (migrations ARE applied; HANDOFF §0.7 item 2 is closed)
twins 50 (all source='synthetic', SYN-30092026-xxxx)   survey_answers 3650 (73 per twin)
survey_submissions 50 (data_type=SYNTHETIC, arms assigned)
runs 0   sessions 0   twin_answers 0   twin_quality_runs 0   validity_results 0   run_events 0
studio_runs 4 (from before this session, all model="mock")
OLLAMA_API_KEY set; TWINLAB_MODEL=gpt-oss:120b; badge reads "Live: gpt-oss:120b"
```

A live provider call was confirmed working end to end (`run_coverage_probe`, 4.1 s, correct
verdict with a correct reason). **The model, the key and the database are all fine.**

### 2.2 The reported crash — fixed and verified

`AttributeError: 'TwinConfig' object has no attribute 'quality_repeats'` at `services/runs.py:137`.
`TwinConfig` declares `quality_runs_per_twin`; there has never been a `quality_repeats`. Fixed.
The Agents tab and the Twins tab both now reach the budget card.

### 2.3 Containment — the researcher decision, measured

On `11010`, before the change:

```
containment=['3.1.b', '3.1.c', '5.1.b', '5.2.b']
```

Every one of those four hits was the **single bigram `("driver", "app")`**, from the `L4`
paragraph, because *Driver app* is Uber's own name for the thing and the pair occurs in four
different commitments. This is exactly the defect `HANDOFF.md` §0.7 item 3 records as open.

The researcher was asked and chose **"ignore non-distinctive bigrams"**: a signature pair that
occurs in more than one forbidden commitment is shared vocabulary and no longer counts.
Measured cost of the narrowing over the frozen data:

```
285 (lever, dial, forbidden) combinations checked
  0 commitments have an empty distinctive signature
  every commitment dropped in verbatim is still caught BY NAME
```

Both facts are now assertions in `tests/test_m5_render_checker.py`. Containment has produced no
false positive since.

### 2.4 Render and check — the current blocker

`docs/03` §5 specifies "fail any gate → re-render **once** → then halt that cell". **That second
pass had never been implemented.** It now is, and it is targeted: the re-render names which
commitments the previous paragraph did not state, which forbidden intensifier it used, and — when
the register band was breached — asks for shorter sentences and plainer words. It quotes **no**
number from the style contract, because `agents/design.STYLE_KEYS_SHOWN` deliberately withholds the
reading-grade band.

Observed results, live, in order:

| Code | Before containment fix | After containment fix | After targeted re-render |
|---|---|---|---|
| `11010` | grade 17.5 + coverage + **4 containment** | grade 16.8/17.5, coverage `4.1.d` | grade 17.1 on `L4`, **coverage passed** |
| `12220` | coverage ×7 + intensifier | grade OK, coverage ×5 | `L4` returned `cannot_render` |

**Three codes now pass and are stored; the six Part 17 stimuli do not.** A full pass over every
code the quality gate needs was run at the end of the session. Verbatim result:

```
12220 277s failed: L1 grade 18.1; L3 151 words; L3 grade 24.5; L4 grade 17.9;
                   not entailed 3.2.c; containment 4.2.c
00222 123s failed: L3 151 words; L3 grade 24.5; L4 grade 17.9;
                   L5 cannot_render ("removing the disparagement ground ... conflicts with a
                   prohibited statement")
11010  65s failed: L1 grade 18.1; L4 grade 18.1; L4 forbidden intensifier 'finally'
11211 131s failed: L1 grade 18.1; L3 151 words; L3 grade 24.5; L4 grade 18.1;
                   L4 'finally'; not entailed 3.2.c; containment 4.2.c
02211  60s failed: L3 151 words; L3 grade 24.5; L4 grade 18.1; L4 'finally';
                   not entailed 3.1.b, 3.2.c; containment 4.2.c
02200  35s failed: L3 151 words; L3 grade 24.5; not entailed 3.1.b, 3.2.c; containment 4.2.c
00000   1s PASSED and stored        (all dial 0 - no probes, no containment, trivially)
00010  11s failed: L4 grade 18.1; L4 forbidden intensifier 'finally'
01000   8s PASSED and stored        <-- the specification's own exemplar cell
00001  18s PASSED and stored

PASSED ['00000', '01000', '00001']
FAILED ['12220','00222','11010','11211','02211','02200','00010']
```

**Read this table carefully — it is the clearest statement of where the instrument actually is.**

* Every failure traces to **three paragraphs**: `L1` dial 1 (grade 18.07), `L3` dial 2 (151 words,
  grade 24.51) and `L4` at both dials (grade 17.89–18.08, and the word *finally*, which is on the
  forbidden-intensifier list). Fix those three and most of the grid passes.
* `L3` dial 2 at **151 words against a 150 ceiling** is a one-word miss. The band was set to 150 on
  2026-09-29 and explicitly marked "DELIBERATELY UNVERIFIED".
* **`00001` (`L5` dial 1, grade 10.70) and `01000` (`L2` dial 1, grade 12.75) pass cleanly.** Single-
  lever, low-commitment cells are fine. The problem is entirely the dense levers.
* A containment hit on `4.2.c` now appears on four codes. This one is **not** the shared-bigram false
  positive — those are gone. It needs looking at on its own terms before anything is concluded about
  it; it may be a genuine leak, in which case the gate is doing its job.
* `L5` returned `cannot_render` on `00222` for the same "conflicts with DO_NOT_SAY" reason `L4` gave
  earlier, so that misreading is not confined to one lever.

Three `variants` rows are stored with `passed = true`: **`00000`, `01000`, `00001`.** That is enough
to run Twin Studio and a single-cell `ask_twins` **as soon as §3.1 is fixed** — see §6.

The failures are no longer containment; they are:

1. **`reading_grade_max: 16.0` on the `L4` paragraphs** (measured 17.1–18.1).
2. **Coverage on `L4` at dial 2**, which carries **eight** commitments inside a 45–150 word band.
3. One `cannot_render`: the design agent reported that commitment `4.1.d` ("Remove disparagement …
   from the grounds for deactivation") "directly conflicts with the DO_NOT_SAY list". **Checked:
   there is no id overlap and no near-duplicate between `L4` dial-2's allowed set and its
   do-not-say list** (verified with a difflib sweep at ratio > 0.6 — nothing). So this is the
   model's own misreading, not a data defect. It may still be worth making the brief clearer.

For calibration: the specification's own known-good exemplar (`worked_out_eg.txt`'s `01000`
paragraph) measures **71 words, grade 11.76** — comfortably inside the band. The problem is
confined to the dense, many-commitment levers.

This is the tension `config/style_contract.yaml`'s own 2026-09-29 note predicted:
> "word_max no longer binds for small commitment sets, so the reading-grade gate is the only thing
> holding register. **Watch it, not the band.**"

It is being watched, and it is binding. **Whether `reading_grade_max`, `word_max`, or the per-lever
commitment count moves is a research decision and was NOT taken.** See §4.1.

Paragraph cache as left in the database (`lever_paragraphs`, `style_version=v1`):

```
L1 1  83 words  grade 18.07      L4 1  109 words  grade 18.08
L2 1  89 words  grade 12.75      L4 2  150 words  grade 17.89
L2 2 139 words  grade 13.27      L5 1   96 words  grade 10.70
L3 2 151 words  grade 24.51   <-- 151 words is OUTSIDE the 45-150 band
```

**Note the trend: the targeted re-render made several of these WORSE**, not better (`L1` dial 1 was
11.48 before, 18.07 after; `L3` dial 2 is now both over-length and grade 24.5). One re-render per
key per process is not converging. See §4.1 — this may be an argument that the repair instruction
needs the actual numbers after all, or that the band is wrong, or both.

`variants` holds **three** rows, all `passed = true`: `00000`, `01000`, `00001`.

### 2.5 Test suite

```
749 passed in ~160s        (was 737 in HANDOFF; +10 new, +2 from the split test)
ruff check src tests tools -> All checks passed
import-linter -> 6 contracts, 0 broken
build_ui() -> builds a Blocks with every page, no exception
```

Three failures appeared during the work and all three are resolved:

1. `test_import_linter_contracts_hold` and `test_ui_imports_only_services_and_models` — **caused by
   me**: `ui/pages/lab.py` had grown imports of `twinlab.db.repositories` and
   `twinlab.orchestrator.loop`. Fixed by adding `paused_sessions()` / `get_session()` to
   `services/runs.py` and re-exporting `SessionAlreadyRunning` there. `ui/` reaches only
   `services/` and `models/` again.
2. `test_available_survey_twins_excludes_synthetic_rows` — **pre-existing, not mine**. It called
   `available_survey_twins(backend)` positionally against a signature that had gained a leading
   `scope` parameter, so it passed the backend object in as the scope string, and it asserted a
   rule the function deliberately no longer has. Renamed to
   `test_available_survey_twins_follows_the_chosen_scope` and rewritten to check all three scopes.
   **If `HANDOFF.md` claims 737 green, that claim was already stale.**

---

## 3. Defects found and NOT fixed — start here

### 3.1 BLOCKER — the provider output type defeats the repair ladder

**Found at the very end of the session, confirmed, not fixed.**

`services/twin_runtime.ask_items` (and, identically, the pre-existing `agents/twin.run_twin`) passes
`output_type=TwinAnswerSet` to `client.run`. Two things go wrong, and both are silent until a live
call happens:

1. **`TwinAnswerSet` validates in pydantic-ai, before the repair ladder sees anything.** Its
   `_check` requires exactly the 37 register ids. A 36-item reply therefore raises *inside*
   pydantic-ai, so `run_answer_ladder` never gets the chance to issue its one targeted repair. The
   whole of `docs/02` §5.4 is bypassed. It also contradicts `CLAUDE.md` rule 4 — the provider
   schema is being trusted to do the validating.
2. **`run_answer_ladder` cannot read a model instance at all.** Verified directly:

   ```
   normalise_answers(TwinAnswerSet(...))  ->  ContractError:
       expected an object of answers, got TwinAnswerSet
   normalise_answers(TwinAnswerSet(...).model_dump())  ->  fine
   ```

   `normalise_answers` branches on `isinstance(payload, dict)` and raises otherwise.
   `PydanticAIClient.run().output` is a **model instance**, not a dict. So *every* live reply —
   including a perfectly good one — is recorded as "unparseable", burns an attempt, and the round
   fails. The M6 tests never caught this because `StubModelClient`'s handler returns dicts.

   This defect is in the shipped `agents/twin.run_twin` too, so it predates this session.

**Proposed fix (not applied):**

- Add a permissive transport model to `models/twin.py` — e.g.
  `class AnswerVector(BaseModel): answers: dict[str, int] = {}; rationale: str = ""` with **no**
  cross-field validator. This is the shape handed to the provider.
- `ask_items` (and `run_twin`) pass `output_type=AnswerVector` for **every** item set, battery or
  holdout. The real validation stays where `CLAUDE.md` rule 4 puts it: `run_answer_ladder` against
  `TwinAnswerSet` / `QualityAnswerSet`.
- In `run_answer_ladder`, or at the call site, convert a `BaseModel` reply with `model_dump()`
  before `normalise_answers`. Doing it inside the ladder fixes `run_twin` at the same time.
- **Write the regression test first**: a stub client that returns a *model instance* with one item
  missing must produce exactly one repair attempt and then an `ok=False` outcome — never a padded
  vector. Today that test fails twice over.

Until this is fixed, **nothing live can produce an answer**, so §2.4's Checker problem is not the
only blocker even if the band is widened.

### 3.2 The re-render budget is per process, not durable

`_rerendered` in `twin_runtime.py` is a module-level set. Restarting the app gives every
`(lever, dial, style_version)` key a fresh re-render. That is a defensible reading of "re-render
once" (a researcher pressing the button again is a new attempt) but it is **not** what the words
say, and it means the number of design calls a paragraph has consumed is not recorded anywhere.
Decide, and if it should be durable, put it on `lever_paragraphs` (e.g. an `attempts` column) —
which needs a migration.

### 3.3 The quality gate aborts on the first failing stimulus

`_render_stimuli` raises if any of the six Part 17 codes fails the Checker. That is deliberate
(scoring 15 items instead of 18 under the same `holdout_set` makes two twins incomparable with
nothing in the data saying why) but it means **one bad lever paragraph blocks the entire gate, and
therefore the entire study** — the panel draw needs quality-passed twins, and the quality gate needs
passing renders. That circularity is real and currently unbroken.

### 3.4 Things left deliberately alone

- `agents/twin.run_twin` — not touched beyond what §3.1 describes; `ask_items` supersedes it for
  every live caller, but it is still exported and still tested. Decide whether to delete it or fix
  it.
- The `L4` dial-2 `cannot_render` reason (§2.4 item 3) — the brief may be worth clarifying, but that
  changes a stimulus and is a research decision.
- `HANDOFF.md` §0.7 items 4, 5, 6, 7, 8, 9, 10 — all still open, none touched.

---

## 4. What must be decided before anything else is built

### 4.1 The register band versus the commitment load — RESEARCHER

This is now the binding constraint on the whole instrument. The options, with what each costs:

1. **Raise `reading_grade_max`.** The failures cluster at 17–18 against a ceiling of 16.0. The
   ceiling's own comment says it is "wide enough that ordinary policy prose passes" — measurement
   says otherwise for the dense levers. Cheapest. Changes a CONFIG value, **and requires a
   `style_version` bump** because paragraphs have now been persisted (`style_contract.yaml` says so
   in terms).
2. **Split a dial-2 lever's commitments across more than one paragraph.** Changes
   `paragraphs_per_lever`, so it changes the stimulus shape for every cell. Most expensive, most
   faithful to the register.
3. **Give the design agent the band.** `STYLE_KEYS_SHOWN` withholds `reading_grade_max` on the
   grounds that "showing a model a number it cannot act on invites it to put the number in the
   prose". That reasoning is testable and has never been tested. One experiment settles it.
4. **Accept that some cells fail and report the attrition.** Honest, but §3.3 means the study cannot
   start at all, so this is only viable if the six Part 17 codes specifically pass.

**Recommendation: try 3 first** (it is one config-key change and one render, and it either works or
it doesn't), then 1 with a `style_version` bump if 3 is not enough. Do not do 2 without a strong
reason.

### 4.2 Whether `style_version` must now bump — RESEARCHER

`config/style_contract.yaml` states, in terms: *"Any later change to this file, once a paragraph has
been PERSISTED, MUST bump this."* Paragraphs are now persisted in `lever_paragraphs` for the first
time. Seven rows exist, none of which has passed the Checker, so bumping to `v2` costs nothing
today — **but it will stop costing nothing the moment a cell passes.** Bump now, before the first
real render, or decide explicitly not to.

---

## 5. What has NOT been tested — the work list

Nothing below has been exercised once. This is the honest state.

### 5.1 The live path, end to end — none of it has run

| # | What to test | How | Pass condition |
|---|---|---|---|
| 1 | One twin answers one cell | Fix §3.1, then `ask_items` on `SYN-30092026-0000` with a stored, Checker-passed variant and the 37-item battery | 37 integers, each inside its **own** scale range, `retries` recorded |
| 2 | The repair ladder actually repairs | Stub client returning a 36-item **model instance**, then a valid one | exactly one repair, `ok=True`, nothing padded |
| 3 | The repair ladder actually fails | Stub returning 36 items twice | `ok=False`, `ask_twin` returns `None`, the twin stays on the panel |
| 4 | `twin_answers` is written | run 1 through `ask_twin` | one row, `(run_id, twin_id, wording)` unique, `lever_order` and `seed` stored |
| 5 | I11 — the round rebuilds | `rebuild_round_prompt` from the stored `seed` + `lever_order` | byte-identical prompt, same `round_hash` |
| 6 | I8 — the guard fires | inject a why-text into the scenario | `RoundPromptError` |
| 7 | A full `ask_twins` session | Dial board → *Ask the twins* on a passing single-lever code, `PANEL_SIZE=2` | `00000` and `SHAM` run first, then the cell; `runs` completed; index computed |
| 8 | `analyse()` | after 7 | `metrics.shifts` has six entries, `index_value` is not `None`, prose is grounded |
| 9 | The Analyst fallback | force `write_analysis` to fail | prose carries `FALLBACK_PREFIX`, run still completes |
| 10 | Stop is cooperative | Stop mid-session | run goes back to `pending`, **not** `completed`; resume re-asks only the unanswered twins |
| 11 | Resume re-pays nothing | Resume after 10 | design-call counter unchanged, `answered_twins` skips |
| 12 | The quality gate, 1 twin, 1 repeat | Twins tab, filter to one twin | 6 calls, 18 items, one `twin_quality_runs` H3 row, `items_n=18`, `is_latest` flipped |
| 13 | H2 is stored | after 12 | `detail["answers"]` has 16 items, `arm` matches the driver's own arm |
| 14 | Validity tests 1 and 3 | after 13 | a real verdict instead of `INCONCLUSIVE`, **and zero model calls on the counter** |
| 15 | Validity tests 4–8 | after 7, 2 twins | a verdict; test 4's probe must **not** appear in `variants`; test 6's ablated persona must **not** appear in `twins` |
| 16 | Twin Studio, existing twin | pick a twin, set dials to a passing code, tick the 37 questions, 2 free-text questions | metric table populated, replies shown, `studio_runs` row with `model` = the real model name, **never "mock"** |
| 17 | Twin Studio, custom change | free text | `sandbox — not a study result` shown, `version_code` is `NULL` in `studio_runs` |
| 18 | Twin Studio, manual twin | create by hand, then ask it | `source='manual'`, no persona hash, baseline column empty (not zero), and it can **never** be drawn into a panel |
| 19 | Twin Studio refuses an unchecked cell | dial a code with no passing variant | `StudioBlocked`, named gate, nothing asked |
| 20 | Agent Studio — Quality Checker | after 12 | completeness + scale pass/fail, the `Held-out item · Driver said · Twin said` table, the keep/drop verdict |
| 21 | Agent Studio — Twin Interviewer | edit the prompt, test | two calls, six-metric saved-vs-edited comparison; **writes nothing** |
| 22 | Agent Studio — Run Manager | press it | a plan; `sessions` table unchanged across the call (this one already has a test) |

### 5.2 Settings actually applying — CLOSED 2026-10-01, see HANDOFF_M16 §8

The read path exists and `refresh_twin_config()` is called at boot and before every session. **It
has not been observed changing behaviour.** Test: save `quality_runs_per_twin = 1` in Settings,
then open the quality-test confirm card and check the budget says 6 calls per twin, not 18; then
start it and check `sessions.config` records `1`.

Also unverified: that `app_config['rules'].weights` (Agent Studio) reaches
`twin_runtime._index_weights` and changes a computed index.

### 5.3 The UI interactions — built, never clicked

I never ran the Gradio server in this session, so **every screen change below is verified only by
`build_ui()` succeeding and by the test suite.** All of it needs a human pass:

- Twins tab: clicking a row fills the twin-id box and opens the panel; keyboard Enter/Space too;
  the selected row highlights.
- Twins tab: *Run twin quality test* respects the four filters and shows the right count.
- Agents tab: the log resets when a new session starts, and the job line updates every 3 s.
- Agents tab: Stop, then Resume.
- Dial board: *Ask the twins* on a cache miss starts a session; `00000` stays disabled.
- Dial board: *Rerun?* inherits the panel (I14) — check `session_panel` matches the original.

### 5.4 Invariants that this work touches and that are only unit-tested

- **I3** — an unverified variant never reaches a twin. Three call sites now enforce it
  (`SessionRunner`, `_render_stimuli`, `studio._stimulus`). Prove it by pointing each at a stored
  variant whose `checker.passed` is `false` and watching all three refuse.
- **I4** — ten design calls per style version. Prove it on the call counter across a multi-cell
  session now that `lever_paragraphs` is durable. **The re-render adds up to ten more** (§3.2);
  decide what the asserted number should be.
- **I14** — the panel is frozen. Prove it on a rerun and on a resume.
- **I15** — `twins_n = 0` is `failed`. Prove it by failing every twin in a cell.

---

## 6. Suggested order for the next session

1. Fix §3.1 and write its two regression tests. Nothing else works until this is done.
2. Take the §4.1 decision (try option 3 — give the design agent the band — it is one change and one
   render) and the §4.2 `style_version` decision.
3. **Skip this step — it is already done.** `01000` and `00001` are stored and passing. Go
   straight to 4.
4. Run test 16 (Twin Studio on that code, one twin). That is the shortest path to a first real
   answer and it exercises persona → round prompt → I8 → ladder → metrics.
5. Run tests 1–5, then 7–11 with `PANEL_SIZE=2`.
6. Only then attempt the six Part 17 stimuli and the quality gate (tests 12–14). Expect §3.3 to
   bite; `L4` is the problem lever in every failure so far.
7. Sweep and validity tests last.

**Cost note.** A render of one cell is ~1 design call per non-zero lever plus one coverage probe per
commitment — `12220` took 250 s. A quality gate at the default 3 repeats is 18 calls per twin.
Keep every test in §5.1 to one or two twins until step 6 passes (`CLAUDE.md` — "ask whether it
multiplies by 243, by the panel size, or by both").

---

## 7. Loose ends left in the working tree

- The background render finished before the session ended and its results are folded into §2.4.
  Final database state: `lever_paragraphs` 7 rows, `variants` 3 rows (`00000`, `01000`, `00001`,
  all `passed = true`), and `runs` / `twin_answers` / `twin_quality_runs` / `run_events` all still
  **0** — no twin has been asked anything.
- Scratch scripts used during the session live in the session scratchpad, not in the repo. They are
  not needed; §5.1 describes what they did.
- `data/reference/` was not touched. `build_reference.py --check` was not re-run this session —
  **run it once** to confirm, though nothing in this work reads or writes those files.
- A `lever_paragraphs` / `variants` mass delete was attempted and **denied by the sandbox**. It is
  not needed — `StoredParagraphPool.rerender` deletes a single key by filter and that path works —
  but if you want a clean slate for `style_version=v1` you will have to clear those two tables
  yourself from the Supabase SQL editor.
