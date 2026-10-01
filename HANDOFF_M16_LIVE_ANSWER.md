# Handoff — M16, the first live twin answer

**Session of 2026-10-01. Paste this whole file into a fresh session to resume.**

Read `CLAUDE.md`, then `HANDOFF.md` §0.5 and §0.7, then `HANDOFF_M15_LIVE_PATH.md`, then this
file. This supersedes `HANDOFF_M15_LIVE_PATH.md` §3.1, §3.2, §4.1 and §4.2 — all four are now
closed. Its §5.1 work list is still the work list, with the status column below.

Use `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. Bare `python` is a different
interpreter without `pydantic_ai` or `openpls` (`HANDOFF.md` §0.0).

---

## 0. DONE — the migration was applied on 2026-10-01

**`003_render_attempts.sql` has been run.** Verified live: `lever_paragraphs.attempts` exists, the
7 pre-existing rows defaulted to `1`, and `services/config._check_schema` passes. The v2 row
written since carries `attempts = 2`, so the durable counter is confirmed on live data.

The rest of this section is kept for the record.

**Run `src/twinlab/db/migrations/003_render_attempts.sql` in the Supabase SQL editor.**

It adds `lever_paragraphs.attempts` (additive, one column, one check constraint). Migrations are
applied by hand in this project (`HANDOFF.md` §0.7), and there is no DDL path from the code.

Until it is run, **the app refuses to boot** against the live database, by design:

```
DbError: `lever_paragraphs.attempts` is missing from the live database. Run
`src/twinlab/db/migrations/003_render_attempts.sql` in the Supabase SQL editor, then restart.
```

That gate is `services/config._check_schema`. It fails at boot rather than on the first write
because a render that dies on its write has already paid for a design call.

---

## 1. One-paragraph summary

`HANDOFF_M15_LIVE_PATH.md` §3.1 is fixed, and **a twin has answered a question against the live
model for the first time in the project's history**: 37 valid integers, every one inside its own
register range, `retries 0`, `calls 1`, 10.8 s, on `SYN-30092026-0000` against the stored `01000`
stimulus. 14 of the 37 answers moved off the driver's baseline, so it is a differentiated response
and not a copy. The three §4 researcher decisions were taken and implemented, and the binding
constraint the whole instrument was stuck behind — the register band — **is no longer binding**:
showing the design agent the band dropped the dense levers from grade 17–24 to 13–14 without
moving `reading_grade_max`, `word_max` or `paragraphs_per_lever`. **768 tests pass, `ruff` is
clean, the 6 import-linter contracts hold, `build_reference.py --check` exits 0.**

---

## 2. What was fixed, and how it was proven

### 2.1 §3.1, the blocker — FIXED and proven live

Two defects, both silent until a live call, both in the shipped code (the second predated M15):

1. `TwinAnswerSet` was handed to the provider as the `output_type`, so pydantic-ai validated the
   37-item register **before** `run_answer_ladder` saw anything. A 36-item reply raised inside
   pydantic-ai and the one targeted repair of `docs/02` §5.4 was never issued — the provider schema
   doing the validating, which `CLAUDE.md` rule 4 forbids.
2. `normalise_answers` branches on `isinstance(payload, dict)` and raises otherwise, while
   `PydanticAIClient.run().output` is a model **instance**. So *every* live reply, including a
   perfect one, was recorded "unparseable", burned an attempt and failed the round.

The fix, as `HANDOFF_M15_LIVE_PATH.md` proposed it:

| File | Change |
|---|---|
| `models/twin.py` | New `AnswerVector` — the **transport** shape. `answers: dict[str, Any]`, `rationale: Any`, no cross-field validator, `extra="allow"`. |
| `agents/contract.py` | New `model_payload()`, used by `run_answer_ladder`: a `BaseModel` reply is converted with `model_dump()` before `normalise_answers`. This fixes `agents/twin.run_twin` at the same time. |
| `services/twin_runtime.py` | `ask_items` passes `output_type=AnswerVector`. |
| `agents/twin.py` | `run_twin` likewise — so §3.4's question is answered: **fixed, not deleted.** |
| `agents/registry.py` | `AnswerVector` registered in `SCHEMA_REGISTRY`. |
| `config/agents.default.yaml` | The twin agent's `output_schema` is now `AnswerVector`. `build_agent` falls back to the config when no `output_type` is given, so that fallback was a live call site. |

The value type is `Any` and not `int` **deliberately**: `dict[str, int]` rejects `5.5` and `null`,
which are exactly the `not_an_integer` defects the ladder exists to name and re-ask for. A
transport model that rejects anything moves a judgement out of Python and into the provider round
trip. Do not tighten it.

Six regression tests at the end of `tests/test_m2_contract.py`. **All six were checked against the
old behaviour and fail there** — including the two the handoff asked for first (a stub returning a
*model instance* short by one item must produce exactly one repair then `ok=False`, and must pad
nothing).

### 2.2 §4.1, the register band — DECIDED (option 3) and measured

RESEARCHER chose **"give the design agent the band"**. `reading_grade_min` and `reading_grade_max`
are now in `agents.design.STYLE_KEYS_SHOWN` — both bounds, because gate 3 tests both.
**`reading_grade_max`, `word_max` and `paragraphs_per_lever` did not move.** The stimulus shape is
unchanged.

Measured live, one design call each, blind versus band-shown:

| Lever, dial | Commitments | Blind (M15) | Band shown |
|---|---|---|---|
| `L1` 1 | 2 | 83w, grade 18.07 | 82w, **13.26 PASS** |
| `L3` 2 | 8 | 151w, grade 24.51 | 150w, **14.47 PASS** |
| `L4` 1 | 3 | 109w, grade 18.08 | 114w, 17.73 FAIL |
| `L4` 2 | 8 | 150w, grade 17.89 | 150w, **13.82 PASS** |

The worry that justified withholding it — "a model shown a number it cannot act on puts the number
in the prose" — did not materialise, and is not unguarded if it ever does: prompt rule 6 forbids
any number a commitment did not supply, and `check_invariance` fails a render that leaks one.

**`L4` dial 1 is the one paragraph the band alone does not fix** — 17.73, 17.86, 17.16 on three
consecutive first-pass draws, so structural, not sampling. The cause is **vocabulary, not
commitment count**: its three commitments carry the study's densest legal nouns
("disparagement", "deactivation", "Community Guidelines"), and Flesch-Kincaid punishes syllables
per word hardest — which is why `L4` dial 2's *eight* commitments score **lower**, the terser
clauses pulling it down.

`docs/03` §5's one re-render clears it. Measured on `L4` dial 1, three renders per arm:

* the existing wordless instruction: **3/3 pass**, grades 9.09 / 10.09 / 8.37
* the same plus the measured grade and the ceiling: **3/3 pass**, grades 11.37 / 8.36 / 11.19

Both work, so the **wordless instruction is kept** — no worse, and it puts no digit near prose that
rule 6 forbids digits in. `services/twin_runtime._repair_for` is unchanged except for its docstring,
which had gone stale (it claimed the band was withheld).

**Watch `L3` dial 2.** Three draws gave 151, 152 and 150 words against `word_max: 150` — it passes
or fails the *word* band on sampling noise now that its grade is comfortable. The re-render handles
a word-count breach, so this costs design calls rather than blocking a cell, and it is not on its
own a reason to move the band. `word_max: 150` still carries its 2026-09-29 "DELIBERATELY
UNVERIFIED" note.

### 2.3 §4.2, `style_version` — DECIDED: bumped to v2

`config/style_contract.yaml` and `config/settings.py` both say `v2`; a test asserts they agree. The
contract's own MUST bit for the first time, because M15 persisted paragraphs and §4.1 changes the
design prompt. The stale "not bumped, and here is why" commentary is rewritten as a HISTORY section
rather than deleted.

**Consequence, and it is the second thing to do after the migration:** the 7 `lever_paragraphs`
rows and the 3 passing `variants` (`00000`, `01000`, `00001`) are v1 and are now **orphaned**.
`variants` is keyed `(version_code, style_version)` and `lever_paragraphs` on
`(lever, dial, style_version)`, so nothing reads them and nothing breaks — but no cell has a
passing v2 variant yet, so **Twin Studio and `ask_twins` will both refuse until a cell is
re-rendered under v2** (I3, three call sites). The v1 rows can be left in place as evidence, or
cleared from the SQL editor if you want a clean slate; they are append-only evidence of nothing
that was ever shown to a twin, so either is defensible.

### 2.4 §3.2, the re-render budget — DECIDED: durable

`lever_paragraphs.attempts`, via `003_render_attempts.sql`, with
`check (attempts between 1 and 2)`. `RENDER_ATTEMPTS_MAX = 2` in `services/twin_runtime.py` is the
specification's ceiling, not a preference.

Two details worth not undoing:

* **The attempt is charged to the table before the design call.** Charging afterwards loses the
  record when the call crashes, times out or returns `cannot_render` — the case M15 actually hit on
  `L4` dial 2 — and the paragraph would then be re-rendered on every restart forever.
* **A refused re-render leaves the previous row in place**, now marked `attempts = 2`. The refusal
  fails *this* cell through the in-memory cache; the next process reloads the old failing paragraph
  and declines to pay again. That is the loud once-only failure `docs/03` §5 asks for. The old code
  deleted the row first; it now deletes only on the no-instruction path, where eviction is the
  point, and `_store` carries the charged count forward so eviction does not refund it.

A key whose renders have **never** produced text still has no row and so no durable count. That is
unchanged and separate: a refusal is not a paragraph and must never become a cache hit
(`StoredParagraphPool.get`).

### 2.5 Tests

```
768 passed in ~128s        (was 749; +19)
ruff check src tests tools -> All checks passed
import-linter -> 6 contracts, 0 broken
build_reference.py --check -> exit 0, all eight frozen files OK
```

New: 6 in `tests/test_m2_contract.py` (§3.1 regressions), 13 in `tests/test_m16_render_budget.py`.

**`services/twin_runtime.py` had no tests at all before this session** — the whole live path from
M15 was covered only by `build_ui()` succeeding. It now has 13. Three of them were checked by
reverting the fix and watching them fail, rather than assumed.

---

## 3. What was proven live, and what that cost

Every number in §2 came from a live call. Total spend this session: **~15 design calls and 1 twin
call.** No sweep, no quality gate, no panel draw.

The twin answer, verbatim:

```
stimulus  01000  style_version=v1  checker.passed=True
          5 paragraphs, 105 words total
twin      SYN-30092026-0000  baseline covers 73 items, battery is 37 items

ANSWERED in 10.8s
  items          37 (expected 37)
  model          gpt-oss:120b
  retries        0   calls 1
  lever_order    [2, 3, 1, 4, 0]
  seed           20260101
  prompt_version 46577760a20658b6
  out of range   none
  moved from baseline: 14/37 items
```

Note what this exercised on the way: persona lookup → round prompt assembly → **I8's guard ran and
passed on a real assembled prompt** → the repair ladder → per-item range validation against the
frozen register. `lever_order_for(20260101)` reproduces `[2, 3, 1, 4, 0]` deterministically, so
**I11 holds for this round** (`twin_answers` was not written — see below).

**Read-only.** It went through `ask_items`, which reads the twin row, persona and baseline and
writes nothing; `ask_twin` is what appends to `twin_answers`, and it was not called. So the
database is unchanged this session: `runs`, `twin_answers`, `twin_quality_runs`, `run_events` are
all still **0**, `variants` still 3 (v1), `lever_paragraphs` still 7 (v1). The stimulus was the
stored v1 `01000` row, used purely as text, so no render was paid for and the migration was not
needed to run it.

`HANDOFF_M15_LIVE_PATH.md` §5.1 status, updated:

| # | What | Status |
|---|---|---|
| 1 | One twin answers one cell | **DONE, live.** 37 integers, each in its own range, `retries` recorded. |
| 2 | The repair ladder repairs | **DONE.** Stub returning a 36-item *model instance*, then valid: exactly one repair, `ok=True`, nothing padded. |
| 3 | The repair ladder fails | **DONE.** 36 items twice → `ok=False`, no output, 2 calls, defect named `missing`, not `unparseable`. |
| 4 | `twin_answers` is written | **NOT DONE** — needs `ask_twin`, so needs a session. Waiting on the §7 decision, not on any code. |
| 16 | Twin Studio, existing twin | **DONE, live.** See §6. |
| 5 | I11 — the round rebuilds | **PARTLY.** `lever_order` reproduces from the live seed; the full `rebuild_round_prompt` byte-identity check is unit-tested but not yet run off a stored `twin_answers` row. |
| 6 | I8 — the guard fires | **PARTLY.** It ran and passed live; the injected-why-text failure case is unit-tested only. |
| 7–15, 17–22 | everything else | **NOT DONE.** Unchanged from M15. |

---

## 4. Suggested order for the next session

1. **Run `003_render_attempts.sql`.** Nothing that writes a paragraph works until then.
2. Re-render one cheap passing cell under v2 — `01000` (`L2` dial 1, which passed blind at grade
   12.75 and is untouched by any of this) or `00001`. One design call plus its coverage probes.
   Confirm `lever_paragraphs.attempts = 1` on the new row.
3. Run §5.1 test 16 — Twin Studio on that code, one twin. Shortest path to a *stored* real answer,
   and it checks `studio_runs.model` is the real model name and never `"mock"`.
4. Then §5.1 tests 4, 5, 7–11 with `PANEL_SIZE=2`.
5. Then the six Part 17 stimuli and the quality gate (12–14). **Expect §3.3 to bite less than M15
   predicted** — the register failures that caused it are gone — but `L4` dial 1 will consume its
   re-render on every style version, so budget 11 design calls for the grid, not 10 (§5.4's I4
   question: the asserted number is 10 first renders plus up to 10 re-renders, and `L4` dial 1 is
   the one that reliably needs its).
6. Sweep and validity tests last.

**Still open and untouched:** `HANDOFF_M15_LIVE_PATH.md` §3.3 (the quality-gate/panel circularity),
§5.2 (Settings actually applying), §5.3 (every UI interaction — the Gradio server was not run this
session either), §5.4 (I3, I4, I14, I15 proven only by unit test), and `HANDOFF.md` §0.7 items
4–10.

---

## 5. Loose ends

* Scratch scripts live in the session scratchpad, not the repo: `measure_band.py` (render one
  lever/dial and score gate 3, writes nothing), `measure_repair.py` (compare the two repair
  instructions), `prove_live_answer.py` (the live twin answer, read-only). §2 and §3 record
  everything they showed; none is needed again, but the first is the cheapest way to re-measure a
  lever after any style-contract change.
* `data/reference/` untouched; `build_reference.py --check` re-run this session and exits 0.
* The pydantic-ai banner prints to stderr on every live script. `PYDANTIC_AI_NO_BANNER=1` silences
  it. Console encoding on Windows also needs `PYTHONIOENCODING=utf-8` before printing any rendered
  paragraph — they contain non-breaking hyphens that cp1252 cannot encode.


---

## 6. After the migration — steps 2 and 3 done, and a defect the v2 bump exposed

### 6.1 A defect found by doing it: the variant lookup used half its key

`variants` is keyed `(version_code, style_version)` — that is a unique index. **Four service-layer
lookups filtered on `version_code` alone** and took the newest row by `created_at`:

| Site | What it feeds |
|---|---|
| `services/studio._stimulus` | a twin, now (Twin Studio) |
| `services/agent_config` | a twin, now (Agent Studio's Twin Interviewer) |
| `services/validity._paragraphs_for` | a twin, now (validity tests 4–8) |
| `services/lab.scenario_paragraphs` | the screen, and four callers |

Harmless while only one `style_version` had ever existed. **The moment v2 arrived it meant a twin
could be shown a v1 paragraph while the app ran v2** — a stimulus verified under a style contract
it was not written to, which is the exact confound the key exists to prevent, and it would have
been invisible in the data because the `variants` row read `passed = true`.

Fixed at all four: the three "show a twin now" sites use both halves of the key, and
`scenario_paragraphs` does too. A *historical* run is still read back by `variant_id`
(`services/results.py`), which is what keeps `docs/09` §2 true the next time the contract moves.
Mechanical, not a research decision — a lookup on half a compound key is simply wrong — and logged
in `docs/DECISIONS.md`.

Four tests in `tests/test_m16_render_budget.py`; three of them fail against the old lookups, which
was checked by reverting them.

**If you have written any code against these four functions, re-read it.** Anything that relied on
"newest variant for this code" now gets "the variant for this code under the running style
version", which is what it should always have meant.

### 6.2 Step 2 — `01000` renders and passes under v2

```
01000  @ v2   PASSED   111 words   reading_grade 9.874
       L2 dial 1: 95w  grade 9.87  attempts=2
```

Grade 9.87, against 12.75 blind under v1 and a ceiling of 16.0.

**`attempts = 2`, and that is the ladder working, not a fault.** The first pass failed a gate and
the one re-render fixed it — so the very first cell rendered under v2 exercised
`docs/03` §5's second pass end to end, and the durable counter recorded the spend on live data.
Note the consequence for §5.4's I4 question: budget **11** design calls for a full grid under a
fresh style version, not 10, and expect `L2` dial 1 and `L4` dial 1 to be the two that need theirs.

`render_and_check` deliberately does **not** store — `orchestrator/loop.py` and
`services/quality.py` do, right after they read the verdict. A script that renders without storing
leaves `variants` empty and the next caller pays the render again.

### 6.3 Step 3 = test 16 — Twin Studio, live, PASSED

```
01000 @ v2, SYN-30092026-0000, 37-item battery + 2 free-text questions, 11.4s

  sandbox False    version_code '01000'    blocked ''    model 'gpt-oss:120b'

  Fairness    today 2.25  now 2.5   change +0.25
  Clarity     today 2.0   now 2.0   change  0.0
  Happiness   today 2.67  now 3.0   change +0.33
  Staying     today 2.0   now 2.0   change  0.0
  Pushback    today 6.25  now 6.25  change  0.0
  Leaving     today 5.67  now 5.67  change  0.0

  studio_runs 5 -> 6    model 'gpt-oss:120b'   NOT "mock"
```

Every pass condition the handoff set for test 16 is met: the metric table is populated against the
twin's own driver, both replies came back, and the `studio_runs` row carries the real model name.
The replies are in the persona's voice and grounded in the stimulus — the twin named the safety
gear and the insurance, and said it would not believe the irrevocability claim until it saw the
policy — which is the qualitative signal `docs/06` §5 wants that screen for.

**Do not read the shifts as a result.** One twin, one single-lever cell, four of six metrics
unmoved. It says the pipeline computes shifts against the right baseline; it says nothing about
the study.

### 6.4 Database state after all of it

```
runs 0   twin_answers 0   twin_quality_runs 0   run_events 0   sessions 0   validity_results 0
studio_runs 6            lever_paragraphs 8 (7 × v1, 1 × v2)
variants 4               00000/01000/00001 @ v1, 01000 @ v2 (all passed)
```

**No study evidence has been written.** Everything live so far went through `ask_items` (writes
nothing) or `ask_studio` (writes only `studio_runs`, the quarantined table of `docs/01` §6.9, which
has no code path to `runs`, `twin_answers` or any metric table).

### 6.5 Tests

```
772 passed        (749 at the start of M16; +6 §3.1, +13 budget/band, +4 compound key)
ruff -> clean     import-linter -> 6 contracts, 0 broken
```

---

## 7. The one thing to decide before step 4 — RESEARCHER

Steps 4 onward (§5.1 tests 4, 5, 7–11: a real `ask_twins` session at `PANEL_SIZE=2`) are the first
thing that **writes to the evidence tables**. `runs`, `run_events` and `twin_answers` are
append-only by rule (`CLAUDE.md` rule 6) — there is no UPDATE and no delete path in the code — so a
2-twin smoke session leaves permanent rows that are not a study result and never can be: the
default analysis panel is 20, and a cell answered by a different set of twins is a different
experiment (I10, I14).

Nothing is blocked on code. The question is only where those rows should land:

1. **Run it in this project and accept the rows**, identifiable by their `sessions.config`
   (`panel_size = 2`) and excluded at analysis time. Simplest; the evidence tables carry a handful
   of rows that are documented as a smoke test.
2. **Run it against a scratch Supabase project**, and keep this one's evidence tables empty until
   the real sweep. Costs a second project and a re-seed; keeps the study's evidence pristine.
3. **Add a `sessions.purpose` column** (`smoke` / `study`) so a test session is marked in the data
   rather than inferred from its panel size. A migration, and the honest version of option 1.

Until this is decided, the furthest the live path can be taken without writing evidence is exactly
where it now is: §6.3.

---

## 8. §5.2 — Settings actually applying: CLOSED

The read path was built in M15 and had never been observed changing anything. It works, and it is
now tested rather than hoped.

### 8.1 Observed on the live database

```
stored app_config['twin'] v3 : quality_runs_per_twin 2, temperature 0.25, mae_max 1.0,
                               pct_within_1_min 0.8, wording A, max_concurrency 1
seed twin.default.yaml       : quality_runs_per_twin 3
IN FORCE                     : quality_runs_per_twin 2   (config_version 3)
budget for one twin          : 12 calls, not 18
index weights in force       : {} - unweighted, which is what the paper reports
```

The override is read, the seed is overridden, the version is recoverable for the evidence row, and
`max_concurrency` — which `seed_db` writes into that row and which is not a `TwinConfig` field — is
dropped rather than crashing the read.

### 8.2 Two values in force that differ from the specification — RESEARCHER, for information

Neither was changed. Both are frozen onto every `sessions.config`, so they are recorded rather than
silent — but they are in force *now* and worth knowing:

* **`temperature: 0.25`**, against a seed of 0.7. `TwinConfig.temperature`'s own docstring says
  "CONFIG and the live empirical question. **Set from validity test 8; do not pick it.**" Validity
  test 8 has never run. So the twin agent is running on a temperature that was picked, not measured.
* **`quality_runs_per_twin: 2`**, against `docs/08` §2.1's 3. It cuts the study's dominant cost by a
  third — 12 calls per twin instead of 18 — and `docs/08` §2.1's reason for 3 ("repeat the H3 gate
  and average, so one bad sample does not discard a good twin") is a research argument, not a
  tuning one. Two samples still average; whether two is enough is the researcher's call.

### 8.3 Tested — `tests/test_m16_settings_apply.py`, 10 tests

Following one value from the save to the thing it moves:

    save_settings -> app_config -> refresh_twin_config -> load_twin_config -> the budget card

* the seed is what runs when nothing is stored, and that is version 1, not `None`
* saving `quality_runs_per_twin = 1` moves the budget card from 18 calls to 6
* a partial save only changes the keys it names (the merge in `save_settings`, which exists because
  an upsert on `key` replaces the whole value object and silently deleted every unmentioned
  threshold)
* a stored config that cannot run **raises** rather than falling back to the seed — running the
  seed as though it were the researcher's choice is the failure the module exists to prevent
* an unknown stored key is dropped, not fatal
* an unreachable database falls back instead of blocking a UI tick
* the default index is unweighted, a malformed weight block falls back to unweighted rather than to
  a partial weighting, and saved weights **move the computed index number**

The last one is deliberately asymmetric (`{first: 9.0, rest: 1.0}`). `compute_index` is a
normalised weighted mean, so weighting all six metrics by 3.0 returns exactly the unweighted index
— a test built on uniform weights would pass against an implementation that read the weights and
then ignored them, which is the M15 defect one level down.
