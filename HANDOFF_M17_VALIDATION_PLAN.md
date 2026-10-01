# Handoff — M17. What has been proven, what has not, and what must be

**Written 2026-10-01 at the end of the M16 session. Paste this whole file into a fresh session to
resume; it is self-contained and you should not need to re-read the M15 or M16 handoffs except
where this file points at them.**

Read `CLAUDE.md` first. Then §0 and §1 here. Everything else is reference.

Use `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. Bare `python` is a different interpreter
without `pydantic_ai` or `openpls`. On Windows, prefix any script that prints a rendered paragraph
with `PYTHONIOENCODING=utf-8` (they contain non-breaking hyphens cp1252 cannot encode) and
`PYDANTIC_AI_NO_BANNER=1` to silence the startup banner.

---

## 0. The one-paragraph state of the instrument

The live path **works**: a twin answers, the Studio scores it against its own driver, and the
repair ladder repairs. Three researcher decisions from M15 are implemented and the migration is
applied. **783 tests pass, `ruff` is clean, the 6 import-linter contracts hold,
`build_reference.py --check` exits 0.** What does **not** work is the six Part 17 stimuli, and
therefore the quality gate, and therefore the panel draw, and therefore the sweep. All six failed
on 2026-10-01. The causes are now known and are **not** what M15 thought: one was a bug in the
re-render loop (fixed this session), one is a genuine duplication in the frozen gap register
(§5.1, needs you), and one is a containment false positive on a contentless bigram (§5.2, needs
you). No study evidence has ever been written — `runs`, `twin_answers`, `twin_quality_runs`,
`run_events`, `sessions` and `validity_results` are all **0**.

### Database state, verified at the end of the session

```
twins              50  (all source='synthetic', SYN-30092026-xxxx, all 50 carry a persona)
survey_answers   3650  (73 per twin)          survey_submissions  50
lever_paragraphs    7  (all style_version=v1 — the M15 record, nothing reads them)
variants            3  (00000, 01000, 00001 — all v1, all passed=true, nothing reads them)
studio_runs         6  (4 pre-existing mock + 2 real, model='gpt-oss:120b')

runs 0   run_events 0   sessions 0   twin_answers 0   twin_quality_runs 0   validity_results 0
```

**The v2 cache was cleared at the researcher's instruction** at the end of the session: 7
`lever_paragraphs` and 7 `variants` rows at `style_version=v2` were deleted. They were products of
the re-render bug in §4.1 and every one had `attempts=2`, so the v2 re-render budget was exhausted
on blind re-rolls. **v2 is now a clean slate: no paragraph, no variant, full budget.** The v1 rows
are deliberately left in place — they are keyed on a `style_version` nothing now reads, they are
the record of what M15 rendered, and they are in nobody's way.

`app_config` is live and read. **Two values in force differ from the specification** — see §5.4.

---

## 1. What to do first, in order

1. **Read §4.1 and §5.** Two of the three blockers are researcher decisions and nothing renders
   past them.
2. **Do not re-render anything until §5.1 and §5.2 are decided.** A render under v2 now costs the
   paragraph's one durable re-render, and `§5.1`'s conflict makes `L5` dial 1 unrenderable by
   construction — you would spend the budget to arrive back here.
3. `docs/DECISIONS.md` → M16 **has been corrected** (the §4.1 overstatement, the `_rerender_cell`
   defect, M15's wrong diagnosis of the `L5` refusal, and the open containment false positive).
   Nothing is owed there; §3.1 below restates the correction if you want the detail.
4. Then §6, which is the validation plan, in the order §7 gives.

---

## 2. What changed in the M16 session

### 2.1 Code

| File | Change |
|---|---|
| `models/twin.py` | New `AnswerVector` — the permissive **transport** shape. `answers: dict[str, Any]`, `rationale: Any`, no cross-field validator, `extra="allow"`. |
| `agents/contract.py` | New `model_payload()`, used by `run_answer_ladder`: a `BaseModel` reply is converted with `model_dump()` before `normalise_answers`. |
| `agents/twin.py` | `run_twin` passes `output_type=AnswerVector`. |
| `agents/registry.py` | `AnswerVector` registered in `SCHEMA_REGISTRY`. |
| `services/twin_runtime.py` | `ask_items` passes `output_type=AnswerVector`. Durable re-render budget (`_attempts`, `RENDER_ATTEMPTS_MAX`, `_pending_attempts`, charge-before-call, refusal keeps the row). **`_rerender_cell` now skips a lever with nothing to repair** (§4.1). `_repair_for` docstring corrected. |
| `services/config.py` | New `_check_schema` / `_REQUIRED_COLUMNS`: boot refuses a database missing a column the code writes, naming the migration. |
| `services/studio.py`, `services/agent_config.py`, `services/validity.py`, `services/lab.py` | The `variants` lookup uses **both** halves of `(version_code, style_version)`. |
| `agents/design.py` | `reading_grade_min` / `reading_grade_max` added to `STYLE_KEYS_SHOWN`. |

### 2.2 Config, migrations, docs

* `config/agents.default.yaml` — the twin agent's `output_schema` is `AnswerVector`.
* `config/style_contract.yaml` — `style_version: v2`; the stale "not bumped, and why" commentary
  rewritten as HISTORY; the reading-grade keys marked as shown to the agent.
* `config/settings.py` — `style_version = "v2"`.
* `src/twinlab/db/migrations/003_render_attempts.sql` — **applied by the researcher on
  2026-10-01.** Adds `lever_paragraphs.attempts smallint not null default 1` with
  `check (attempts between 1 and 2)`.
* `docs/DECISIONS.md` — a `## M16` section. **Its §4.1 entry needs the correction in §3.1 below.**
* `HANDOFF_M16_LIVE_ANSWER.md` — the session log. This file supersedes its §4 and §7.

### 2.3 Tests: 749 → 783

| File | New | What |
|---|---|---|
| `tests/test_m2_contract.py` | +6 (66 total) | The transport shape and the model-instance ladder. |
| `tests/test_m16_render_budget.py` | 18 (new file) | The durable budget, the band in the prompt, the v2 bump, the boot gate, the compound key, the re-roll fix. |
| `tests/test_m16_settings_apply.py` | 10 (new file) | A Settings save reaching the budget card and the computed index. |

**Every regression test in these was checked by reverting the fix and watching it fail**, not
assumed. Counts that failed pre-fix: 6/6 in `test_m2_contract`, 3 (budget) + 3 (compound key) + 1
(re-roll) in the M16 files.

`services/twin_runtime.py` — the whole live path built in M15 — **had no tests at all** before this
session.

---

## 3. What was tested, and the actual observations

Everything in this section was run. Nothing is inferred. Live model calls are marked **LIVE**.

### 3.1 The register band — and the correction that matters

**LIVE.** `reading_grade_min`/`max` added to `STYLE_KEYS_SHOWN`, then one design call per
lever/dial, scored exactly as `check_invariance` scores it:

| Lever, dial | Commitments | M15, band withheld | Band shown, isolated draw |
|---|---|---|---|
| `L1` 1 | 2 | 83w, grade 18.07 | 82w, **13.26 PASS** |
| `L3` 2 | 8 | 151w, grade 24.51 | 150w, **14.47 PASS** |
| `L4` 1 | 3 | 109w, grade 18.08 | 114w, 17.73 FAIL |
| `L4` 2 | 8 | 150w, grade 17.89 | 150w, **13.82 PASS** |

`L4` dial 1 was then drawn three more times: **17.73, 17.86, 17.16** — consistent, so structural
rather than sampling. Its cause is vocabulary, not commitment count: its three commitments carry
the study's densest legal nouns ("disparagement", "deactivation", "Community Guidelines") and
Flesch-Kincaid punishes syllables per word hardest, which is why `L4` dial **2**, with eight
commitments, scores *lower* — more commitments force terser clauses.

The one re-render was then measured on `L4` dial 1, three renders per arm:

* the existing instruction, which describes the breach in words and quotes no number:
  **3/3 pass**, grades 9.09 / 10.09 / 8.37
* the same plus the measured grade and the ceiling: **3/3 pass**, grades 11.37 / 8.36 / 11.19

The wordless instruction was kept — no worse, and it puts no digit near prose that prompt rule 6
forbids digits in.

> **CORRECTION, and it belongs in `docs/DECISIONS.md` → M16 §4.1.**
> On the strength of the table above I wrote that showing the band "fixed" the dense levers. **The
> full six-code run contradicts that.** The same paragraphs, rendered through the real pipeline,
> stored at `L1` d1 **17.79** (isolated: 13.26) and `L3` d2 **16.58** (isolated: 14.47).
> Part of that gap is the §4.1 bug — good paragraphs were deleted and re-rolled with no
> instruction — but part is simply that four single draws at temperature 0.3 were too small a
> sample to support the word "fixed". **What is actually established:** showing the band lowers the
> dense levers' grade substantially on average, and does **not** reliably clear 16.0 on a single
> draw. The band should be kept; the claim that it alone unblocks the grid should not.

### 3.2 §3.1's blocker — the provider output type. FIXED, proven LIVE

Two defects, both silent until a live call, the second predating M15:

1. `TwinAnswerSet` was handed to the provider as `output_type`, so pydantic-ai validated the
   37-item register **before** `run_answer_ladder` saw anything. A 36-item reply raised inside
   pydantic-ai and the one targeted repair of `docs/02` §5.4 was never issued.
2. `normalise_answers` branches on `isinstance(payload, dict)` and raises otherwise, while
   `PydanticAIClient.run().output` is a model **instance**. So every live reply, including a
   perfect one, was recorded "unparseable", burned an attempt and failed the round. CI never caught
   it because `StubModelClient`'s handler returns dicts.

Proven broken before the fix, directly:

```
normalise_answers(AnswerVector(...))        -> ContractError: expected an object of answers,
                                               got AnswerVector
TwinAnswerSet(answers=<36 items>)           -> ValidationError: missing=['PAC4']
AnswerVector(answers=<36 items>)            -> fine, 36 items, no raise
```

Then **LIVE**, the first twin answer in the project's history:

```
stimulus  01000 (v1 row, used as text only)   5 paragraphs, 105 words
twin      SYN-30092026-0000                   baseline covers 73 items, battery is 37

ANSWERED in 10.8s
  items 37/37     out of range: none     retries 0     calls 1
  model gpt-oss:120b    lever_order [2,3,1,4,0]    seed 20260101
  prompt_version 46577760a20658b6
  moved from baseline: 14/37 items
```

On the way it exercised persona lookup → round-prompt assembly → **I8's guard, which ran and
passed on a real assembled prompt** → the repair ladder → per-item range validation against the
frozen register. `lever_order_for(20260101)` reproduces `[2, 3, 1, 4, 0]` deterministically across
five calls, so **I11 holds for this round**. `ask_items` writes nothing, so no row was created.

The transport model's value type is `Any` and **not** `int` deliberately: `dict[str, int]` rejects
`5.5` and `null`, which are exactly the `not_an_integer` defects the ladder exists to name and
re-ask for. **Do not tighten it.**

### 3.3 The durable re-render budget. LIVE-verified

Migration applied; the 7 pre-existing rows defaulted to `attempts=1`; `_check_schema` passes. The
first v2 render came back `attempts=2` — the first pass failed a gate and the re-render fixed it,
so `docs/03` §5's second pass ran end to end and the counter recorded it on live data.

Charge-before-call and refusal-keeps-the-row were both chosen deliberately; §4 of
`HANDOFF_M16_LIVE_ANSWER.md` has the reasoning. The known gap: a key whose renders have **never**
produced text has no row and so no durable count, because a refusal is not a paragraph and must
never become a cache hit.

### 3.4 Twin Studio, test 16. LIVE, PASSED

```
01000 @ v2, SYN-30092026-0000, 37-item battery + 2 free-text questions, 11.4s
sandbox False    version_code '01000'    blocked ''    model 'gpt-oss:120b'

Fairness   today 2.25  now 2.5   +0.25      Staying    today 2.0   now 2.0   0.0
Clarity    today 2.0   now 2.0    0.0       Pushback   today 6.25  now 6.25  0.0
Happiness  today 2.67  now 3.0   +0.33      Leaving    today 5.67  now 5.67  0.0

studio_runs 5 -> 6      model 'gpt-oss:120b'  — NOT "mock"
```

Every pass condition met. The replies were in the persona's voice and grounded in the stimulus (the
twin named the safety gear and the insurance, and said it would not believe the irrevocability
claim "until I get the helmet and see the insurer's name and the claim process in the app").

**Those shifts are not a result.** One twin, one single-lever cell, four of six metrics unmoved. It
establishes that the pipeline computes shifts against the right baseline and nothing else.

### 3.5 Settings actually applying, §5.2 of the M15 handoff. CLOSED

**LIVE** observation:

```
stored app_config['twin'] v3 : quality_runs_per_twin 2, temperature 0.25, mae_max 1.0,
                               pct_within_1_min 0.8, wording A, max_concurrency 1
seed twin.default.yaml       : quality_runs_per_twin 3
IN FORCE                     : quality_runs_per_twin 2   (config_version 3)
budget for one twin          : 12 calls, not 18
index weights in force       : {} — unweighted, which is what the paper reports
```

The override is read, the seed is overridden, the version is recoverable for the evidence row, and
`max_concurrency` (which `seed_db` writes into that row and which is not a `TwinConfig` field) is
dropped rather than crashing the read. Ten tests now follow a value from `save_settings` through
`app_config` → `refresh_twin_config` → `load_twin_config` → the budget card, and separately
`app_config['rules'].weights` → `_index_weights` → `compute_shifts`.

One trap worth knowing if you extend these: `compute_index` is a **normalised** weighted mean, so
weighting all six metrics by 3.0 returns exactly the unweighted index. A test built on uniform
weights passes against an implementation that reads the weights and ignores them. The test uses
`{first: 9.0, rest: 1.0}` and asserts the index **number** moves.

### 3.6 The six Part 17 stimuli, under v2. LIVE. ALL SIX FAILED

660 s total. Rendered with a script that reports all six instead of aborting on the first, which
`services/quality._render_stimuli` does.

```
12220  296.5s FAILED  words=536 grade=17.788
       uncovered ['3.1.f','3.2.a','3.2.d','4.1.d']   containment ['1.1.a']
       L1 d1  83w 17.79 | L2 d2 149w 13.35 | L3 d2 150w 16.58 | L4 d2 150w 13.76

00222  123.2s FAILED  words=424 grade=16.584
       uncovered ['3.1.f','3.2.a','3.2.d','4.1.d']   containment ['1.1.a']
       L3 d2 150w 16.58 | L4 d2 150w 13.76 | L5 d2 116w 13.71

11010   55.6s FAILED  words=288 grade=17.788
       uncovered ['4.1.a']
       L1 d1  83w 17.79 | L2 d1  95w  9.87 | L4 d1 102w 16.36

11211   99.8s FAILED  words=430 grade=17.788
       uncovered ['3.1.b','3.2.a','4.1.a','4.1.d']  containment ['1.1.a']
       L1 d1 83w 17.79 | L2 d1 95w 9.87 | L3 d2 150w 16.58 | L4 d1 102w 16.36
       L5 d1  cannot_render

02211   41.8s FAILED  words=405 grade=16.584
       uncovered ['3.1.f','3.2.a','3.2.d','4.1.a']  containment ['1.1.a']
       L2 d2 149w 13.35 | L3 d2 150w 16.58 | L4 d1 102w 16.36 | L5 d1 cannot_render

02200   40.3s FAILED  words=311 grade=16.584
       uncovered ['3.1.f']                          containment ['1.1.a']
       L2 d2 149w 13.35 | L3 d2 150w 16.58

PASSED []     FAILED all six      §3.3 verdict: STILL BINDING, 6 of 6
```

**No paragraph failed the word band.** Mid-run I saw `L4` d2 at 151 words and reported it as a
word-ceiling failure; it was re-rendered to 150 and the final state has no word-band violation.
`word_max: 150` is not currently the problem — though every dial-2 paragraph sits at 149/150, so it
is one draw away from being one (§5.5).

Three distinct causes, in descending order of how much they explain:

1. **reading grade** on `L1` d1 (17.79), `L3` d2 (16.58), `L4` d1 (16.36) — 0.4 to 1.8 over a 16.0
   ceiling. Largely the §4.1 bug; partly variance (§3.1).
2. **coverage** — `3.1.f`, `3.2.a`, `3.2.d`, `3.1.b`, `4.1.a`, `4.1.d` not entailed. Substantive:
   the paragraph did not state a commitment it was given. Untouched by any fix so far and the
   least understood of the three. See §6.2 T-4.
3. **containment `1.1.a`** on 5 of 6 codes — a false positive (§5.2).
4. **`L5` d1 `cannot_render`** — correct behaviour against contradictory inputs (§5.1).

---

## 4. Defects found and FIXED this session

### 4.1 `_rerender_cell` threw away passing paragraphs and re-rolled them blind

**The most consequential fix in the session, and it rewrites M15's conclusions.**

`_repair_for` returns `None` for a lever that "missed nothing" — its docstring says so. That `None`
was passed straight into `pool.rerender`, whose no-instruction branch **deletes the row and
re-renders from the brief with no repair**. Since `_rerender_cell` loops over every non-zero lever
in a failing cell, **one failing lever discarded and re-sampled every other lever's paragraph in
that cell**, spending each one's single durable re-render on a blind re-roll of text that had
already passed.

Evidence:

* `L2` d1 stored at grade **9.87** — a clean pass — yet sitting at `attempts = 2`.
* `L1` d1 measured **13.26** in isolation, stored at **17.79** after an instruction-less re-roll.
* All 7 v2 paragraphs reached `attempts = 2` after only six cells.

**This is the mechanism behind `HANDOFF_M15_LIVE_PATH.md` §2.4's "the targeted re-render made
several of these WORSE" (`L1` dial 1: 11.48 before, 18.07 after).** M15 read that as the repair
failing to converge and inferred the band might be wrong. It was a good paragraph being deleted and
re-sampled without an instruction. `rerender`'s no-instruction path had exactly one caller, and it
was only ever reached in the case where it should not have been.

Fixed: the loop skips a lever whose repair is `None`. Test
`test_a_lever_with_nothing_to_repair_is_not_re_rolled` fails against the old loop
(`assert 2 == 1` on the design-call counter).

### 4.2 The `variants` lookup used half its key

`variants` is keyed `(version_code, style_version)` — a unique index. Four service-layer lookups
filtered on `version_code` alone and took the newest row by `created_at`:

| Site | Feeds |
|---|---|
| `services/studio._stimulus` | a twin, now (Twin Studio) |
| `services/agent_config` | a twin, now (Agent Studio's Twin Interviewer) |
| `services/validity._paragraphs_for` | a twin, now (validity tests 4–8) |
| `services/lab.scenario_paragraphs` | the screen, and four callers |

Harmless while only v1 existed. From the v2 bump it meant **a twin could be shown a v1 paragraph
while the app ran v2** — a stimulus verified under a style contract it was not written to, and
invisible in the data because the row reads `passed = true`. Fixed at all four. A *historical* run
is still read back by `variant_id` (`services/results.py`), which is what keeps `docs/09` §2 true
the next time the contract moves.

### 4.3 Boot now refuses a database missing a column the code writes

`services/config._check_schema`, driven by `_REQUIRED_COLUMNS`, which names the migration file for
each. Migrations are applied by hand, so the code and the database can disagree; failing at boot
beats failing on the first write, by which point a design call has been paid for. An empty table
says nothing about its columns and does not block boot.

---

## 5. OPEN — the researcher owns these, and two of them block everything

### 5.1 BLOCKER — `5.1.c` and `4.1.d` are the same commitment under two levers

`L5` dial 1 **must state** its own `5.1.c`:

> "Remove the disparagement ground for deactivation, and narrow the confidentiality clause so it
> does not cover drivers discussing their own pay and conditions with each other or with a
> representative body."

`L5`'s DO_NOT_SAY **contains** `4.1.d`, which is L4's:

> "Remove disparagement, and harm to Uber's brand, reputation or business, from the grounds for
> deactivation in §2.5 and from the Community Guidelines. State positively that raising a concern
> or bringing an appeal will never count against a driver's standing."

**The design agent's refusal is correct.** The brief asks for a sentence and forbids it in the same
breath, and no prompt wording can resolve that. Its stated reason is accurate: "The commitment to
remove the disparagement ground for deactivation is prohibited by the DO_NOT_SAY list."

**`HANDOFF_M15_LIVE_PATH.md` §2.4 item 3 is wrong about this.** It concluded "this is the model's
own misreading, not a data defect" on the strength of a difflib sweep — but that sweep compared
`L4` dial-2's allowed set against **its own** do-not-say list, never `L5`'s. The overlap is
cross-lever and the check could not have seen it.

This blocks `11211` and `02211` outright (both dial `L5` to 1), and `L5` dial 1 is unrenderable
under any style version until it is resolved.

**Constraints on any fix.** `CLAUDE.md` rule 8 forbids renumbering an identifier: `4.1.d` and
`5.1.c` are opaque stable keys cited by the codebook and the corpus. The gap register is frozen.
So the options are about **what the do-not-say list contains**, not about the ids:

1. **Exempt a near-duplicate from the do-not-say list** — when a forbidden commitment is
   substantively the same as one the lever must state, drop it from `do_not_say` for that lever.
   Mechanically small (`variant/lookup.do_not_say`), but it weakens containment exactly where two
   levers genuinely overlap, and the overlap is then invisible in the rendered stimulus: `11211`
   and `02011` would carry the same disparagement sentence under different lever attributions.
2. **Rewrite one of the two commitment texts** so they are distinguishable in substance —
   e.g. `5.1.c` narrowed to the confidentiality clause only, leaving deactivation grounds to
   `4.1.d`. Changes a **stimulus**, so it is a research decision in the strongest sense, and it
   changes what `L5` dial 1 means.
3. **Accept that `L5` dial 1 cannot render** and exclude every cell with `L5 = 1` — 81 of 243 —
   reporting the attrition. §3.3's circularity then bites: two of the six H3 codes are in that set,
   so the quality gate never runs and the study cannot start.
4. **Audit the whole register for this class first.** Before choosing, run the sweep in §6.2 T-3:
   it is deterministic, costs no model calls, and tells you whether this is one collision or a
   pattern. **Do this regardless of which option you pick.** My note at
   `memory/project-gigworker-twin-study.md` records a separate known defect — the corpus filed
   against the Fairwork *AI* Principles rather than the location-based ones, with thresholds 3.2
   and 4.2 substantively different and ~22 chunks needing re-filing. The uncovered commitments in
   §3.6 include `3.2.a` and `3.2.d`. **These may be the same underlying problem and should be
   investigated together.**

### 5.2 BLOCKER — containment fires on a contentless bigram

`1.1.a` hits on 5 of 6 codes. The matched distinctive pair is `("rather", "leaving")`:

* `1.1.a`: "…Uber makes up the difference **rather than leaving** the loss with the driver."
* `L3` d2 paragraph: "…checks how fleet partners treat drivers they supply **rather than leaving**
  responsibility to you."

Generic English carrying no commitment content. It survives the 2026-09-30 narrowing because that
drops pairs **shared between forbidden commitments**, and this pair is unique to `1.1.a` — it is
non-distinctive in the sense that matters (it says nothing) while being distinctive in the sense
the code measures (no other forbidden commitment uses it).

Same *class* as the `("driver","app")` false positive M15 fixed, different mechanism: shared
vocabulary then, function words now. And the same stakes `HANDOFF.md` §0.7 item 3 sets out — one
hit fails the cell, a failed paragraph is cached as failed, and every repair makes the detector
**less** sensitive, which is the undetectable direction I3 exists to prevent.

Options, none of them picked:

1. **Exclude function words from a signature.** A pair must be two content words. `rather`,
   `leaving`, `than`, `where`, `does` carry no commitment. Standard practice, and the narrowest
   change that addresses the observed failure.
2. **Require two distinct matched pairs**, not one. Keeps every pair but raises the bar. Halves
   sensitivity to short leaks.
3. **Trigrams instead of bigrams.** More specific per match, and "rather than leaving" would still
   match — so this one probably does not fix the observed case.
4. **Leave it and treat the hits as real**, accepting the cell failures.

**Measure before choosing, the way M15 did for the last narrowing** — §6.2 T-3 gives the sweep. The
number that matters is: for each option, how many of the 285 (lever, dial, forbidden) combinations
lose their entire distinctive signature, and is every commitment dropped in verbatim still caught.

### 5.3 The coverage failures are the least understood blocker

Six commitments were not entailed across the six codes: `3.1.f`, `3.2.a`, `3.2.d`, `3.1.b`,
`4.1.a`, `4.1.d`. Unlike the grade and containment failures, **nothing this session addressed
these**, and they are a different kind of problem: the design agent was given a commitment and did
not state it recognisably enough for the coverage probe to find it.

Three candidate explanations, untested and mutually compatible:

1. **Genuine omission** — eight commitments in 150 words is too tight, and the model drops the
   ones it can least easily phrase. `L4` d2 carries eight; `L3` d2 carries eight.
2. **The probe is strict** — the commitment is stated in substance but the probe's entailment
   judgement is conservative. This is a model call per commitment, so it is also the expensive part
   of a render.
3. **The corpus filing defect** — `3.2.a` and `3.2.d` are in threshold 3.2, which
   `memory/project-gigworker-twin-study.md` flags as substantively different between the two
   Fairwork principle sets and needing re-filing. If the anchors are wrong, the brief is wrong.

§6.2 T-5 is the test that separates them, and explanation 3 should be checked first because it is
free.

### 5.4 Two values in force differ from the specification. For information

Neither was changed. Both are frozen onto every `sessions.config`, so they are recorded rather than
silent — but they are in force **now**:

* **`temperature: 0.25`**, against a seed of 0.7. `TwinConfig.temperature`'s docstring says "CONFIG
  and the live empirical question. **Set from validity test 8; do not pick it.**" Test 8 has never
  run. So the twin agent runs on a temperature that was picked, not measured. `HANDOFF.md` §0.7
  item 10 has the recommendation-rule ambiguity that still needs confirming.
* **`quality_runs_per_twin: 2`**, against `docs/08` §2.1's 3. It cuts the study's dominant cost by
  a third (12 calls per twin, not 18). §2.1's reason for 3 — "repeat the H3 gate and average, so
  one bad sample does not discard a good twin" — is a research argument. Two still averages;
  whether two is enough is yours.

### 5.5 `word_max: 150` is one draw from binding

Every dial-2 paragraph in §3.6 landed at 149 or 150 against a ceiling of 150; a mid-run draw hit
151. With grades improved, the model writes eight-commitment levers to ~150 words every time and
lands either side of the line by chance. `word_max: 150` still carries its 2026-09-29
"DELIBERATELY UNVERIFIED" note and `HANDOFF.md` §0.7 item 9's warning that **length is a stimulus
property** — if dial-1 cells run ~60 words and dial-2 cells ~150, part of any lever effect is
"more text". This is not currently a failure and is not a reason to act on its own; it is a thing to
watch, and §6.2 T-6 measures it.

### 5.6 Still open from earlier handoffs, untouched

`HANDOFF.md` §0.7 items 4 (HTMT confidence intervals), 5 (the Analyst's tools), 6
(`PersonaIncomplete`), 7 (panel size vs eligible twins), 8 (`ANCHOR_CHUNKS_PER_BRIEF = 9`), 9
(`word_max`, see §5.5), 10 (twin temperature, see §5.4). `HANDOFF_M15_LIVE_PATH.md` §3.3 (the
quality-gate/panel circularity — still structurally true, and §3.6 shows it is currently binding).

---

## 6. The validation plan — what must be true before a number goes in the paper

Organised by tier. **A tier is not started until the one above it is green**, because a failure
upstream makes every downstream measurement meaningless. Each entry has an id you can cite, what it
proves, how to run it, and the pass condition.

Marks: **[done]** proven this session or earlier · **[unit]** covered by the suite but never
exercised live · **[TODO]** neither.

### 6.1 Tier A — the deterministic core. Largely done, and it is the foundation

| id | What | How | Pass |
|---|---|---|---|
| A-1 | The 783-test suite | `PYTHONPATH="src;." ./venv/Scripts/python.exe -m pytest -q` | 783 pass **[done]** |
| A-2 | Invariants I1–I17 each named in a docstring | `pytest tests/test_invariants.py -q` | 42 pass, `DEFERRED` empty **[done]** |
| A-3 | Layer boundaries | `pytest tests/test_m0_scaffold.py -k linter` | 6 contracts, 0 broken **[done]** |
| A-4 | Frozen reference data | `python -m twinlab.ingest.build_reference --check` | exit 0, 8 files OK **[done]** |
| A-5 | The golden PLS-SEM dataset | `pytest tests/test_stats_golden.py -q` | 345 pinned values, \|Δ\| < 0.001 **[done]** |
| A-6 | `ruff` | `ruff check src tests tools` | clean **[done]** |
| A-7 | `build_ui()` constructs every page | `SUPABASE_URL="" SUPABASE_SERVICE_KEY="" python -c "from twinlab.ui.app import build_ui; build_ui()"` | no exception **[done]** |

**A-1 through A-7 must be re-run and green before anything below is trusted.** They are cheap
(~2 min) and they are the only thing standing between a refactor and a silently broken instrument.

### 6.2 Tier B — the render pipeline. THIS IS THE BLOCKING TIER

Nothing downstream can run until the six H3 codes render. All of T-3 and T-6 are **free** (no model
calls) and should be done first.

| id | What it proves | How | Pass condition |
|---|---|---|---|
| T-1 | §5.1 decided and implemented | researcher decision, then code | `L5` dial 1 renders, or every `L5=1` cell is explicitly excluded with the attrition recorded |
| T-2 | §5.2 decided and implemented | researcher decision, then `variant/checker.py` | no containment hit on a contentless pair; **every commitment dropped in verbatim is still caught** |
| T-3 | **The register has no other near-duplicate collisions.** FREE, do this first | for each (lever, dial), difflib every commitment in the lever's own set against every entry in its `do_not_say`; report ratio > 0.6 | either no pair above threshold, or a complete list. §5.1 is one instance; this says whether it is a pattern |
| T-4 | The containment narrowing costs nothing it should not. FREE | for each option in §5.2, over all 285 (lever, dial, forbidden) combinations: count commitments whose distinctive signature becomes empty, and assert each is still caught when dropped in verbatim | 0 empty signatures, 100% verbatim detection — the same two numbers M15 measured for the last narrowing |
| T-5 | The coverage failures are understood (§5.3) | (a) FREE: check whether `3.2.a`/`3.2.d`'s anchors come from the mis-filed corpus chunks; (b) LIVE: render `L4` d2 and `L3` d2 three times each and see whether the same commitments are dropped every time | either a stable set of commitments the model always drops (→ too many per paragraph) or a varying set (→ probe strictness or sampling) |
| T-6 | Paragraph length does not track dial. FREE on stored rows, else 1 draw per lever/dial | word count per (lever, dial) once the grid renders | dial-1 and dial-2 distributions overlap; if dial-1 ~60w and dial-2 ~150w, **`word_max` is a confound** and §5.5 becomes a decision |
| T-7 | The re-render fix holds live | after T-1/T-2: render one failing cell and check `attempts` | only the levers that actually failed reach `attempts=2`; a passing lever stays at 1 **[unit]** |
| T-8 | **The six H3 codes all pass** | `render_h3_stimuli.py` (§9) | 6/6 passed. **This is the gate on the whole study** |
| T-9 | I4 — the design-call count | call counter across a multi-cell session under a fresh style version | ≤ 10 first renders + ≤ 10 re-renders. `L4` d1 reliably needs its, so budget 11+ **[unit]** |
| T-10 | I1 — the lookup is a pure function | `pytest -k lookup` plus: same code twice → identical `DeltaSpec` | byte-identical **[done, unit]** |
| T-11 | I5 — dial 0 is never generated | design call counter on `00000` | 0 design calls, byte-identical constant **[done, unit]** |
| T-12 | I3 — an unverified variant never reaches a twin | point each of `SessionRunner`, `_render_stimuli`, `studio._stimulus` at a stored variant with `checker.passed = false` | all three refuse. Studio's half **[done]** in `test_m16_render_budget`; the other two **[TODO]** |
| T-13 | The sham is indistinguishable | render `SHAM` and check gate 5 | `sham_indistinguishable` true; the sham announces only existing policy **[unit]** |

### 6.3 Tier C — the twin path

| id | What it proves | How | Pass condition |
|---|---|---|---|
| C-1 | One twin answers one cell | done | 37 integers, each in its own range **[done, LIVE]** |
| C-2 | The ladder repairs | stub returning a 36-item model instance then a valid one | exactly one repair, `ok=True`, nothing padded **[done]** |
| C-3 | The ladder fails honestly | stub returning 36 items twice | `ok=False`, no output, 2 calls **[done]** |
| C-4 | `twin_answers` is written | `ask_twin` inside a session | one row; `(run_id, twin_id, wording)` unique; `lever_order`, `seed`, `retries` stored **[TODO]** |
| C-5 | **I11 — the round rebuilds byte-identically** | `rebuild_round_prompt` from a **stored** `twin_answers` row's seed + lever_order | byte-identical prompt, same `round_hash`. `lever_order` half **[done]**; the full rebuild off a stored row **[TODO]** |
| C-6 | I8 — the guard fires | inject a why-text, a holdout id and a version code into the scenario | `RoundPromptError` each time. **[unit]**; the passing direction **[done, LIVE]** |
| C-7 | I10 — attention checks never reach a twin | assert `AMQ6`, `ALGO5` absent from every battery prompt | absent **[unit]** |
| C-8 | I7 — the persona carries words, not numbers | assert no digit from a Likert answer appears in a persona passage | **[unit]** |
| C-9 | I6 — no holdout material in a persona | two rows differing only in all 34 holdout answers | byte-identical passage and hash **[done, unit]** |
| C-10 | A twin that fails a cell stays on the panel | force a ladder failure mid-session | that cell records no answer for that twin; the twin answers the next cell **[TODO]** |
| C-11 | Studio, custom change | free text, no version code | `sandbox` label shown, `version_code` NULL in `studio_runs` **[TODO]** |
| C-12 | Studio, manual twin | create by hand, then ask | `source='manual'`, no persona hash, baseline column **empty not zero**, never drawable into a panel **[TODO]** |
| C-13 | Studio refuses an unchecked cell | dial a code with no passing variant | `StudioBlocked`, gate named, nothing asked **[done]** |
| C-14 | Temperature actually varies output | same twin, same cell, temperature 0.0 vs 1.0, 3 draws each | 0.0 gives identical vectors; 1.0 does not. Prerequisite for validity test 8 to mean anything **[TODO]** |

### 6.4 Tier D — the quality gate and the panel

| id | What it proves | How | Pass condition |
|---|---|---|---|
| D-1 | The gate, one twin, one repeat | Twins tab filtered to one twin | 6 calls, 18 items, one `twin_quality_runs` H3 row, `items_n=18`, `is_latest` flipped in the same transaction **[TODO]** |
| D-2 | H2 is stored | after D-1 | `detail["answers"]` has 16 items, `arm` matches the driver's own arm **[TODO]** |
| D-3 | I15 — a score over nothing is no score | force `items_n = 0` | `QualityScore` refuses; the run is `failed`, never `completed` with 0.000 **[unit]** |
| D-4 | The keep rule is AND, not either/or | thresholds either side of both | keep iff `mae <= mae_max` **and** `pct_within_1 >= pct_within_1_min` **[unit]** |
| D-5 | Repeats average rather than last-wins | 2 repeats with different scores | the stored verdict reflects the mean **[TODO]** |
| D-6 | The config version is on the row | after D-1 | `twin_quality_runs.config_version` = `twin_config_version()` **[TODO]** |
| D-7 | I14 — the panel is frozen | draw, then rerun and resume | `session_panel` identical; a rerun inherits it **[unit]** |
| D-8 | The draw is stratified and reproducible | same seed twice | identical `PanelMember` list, strata balanced on city × service **[unit]** |
| D-9 | Manual twins are never drawn | include a manual twin in the population | absent from the panel **[unit]** |
| D-10 | Panel size vs eligible twins | fewer eligible than `panel_size` | `InsufficientEligibleTwins` raises (§0.7 item 7 — confirm this is what you want) **[unit]** |

### 6.5 Tier E — the sweep, the orchestrator and analysis

| id | What it proves | How | Pass condition |
|---|---|---|---|
| E-1 | A full `ask_twins` session | Dial board → *Ask the twins*, `PANEL_SIZE=2`, one passing cell | `00000` and `SHAM` run first, then the cell; `runs` completed; index computed **[TODO]** |
| E-2 | `analyse()` | after E-1 | `metrics.shifts` has six entries, `index_value` not None, prose numerically grounded against its bundle **[TODO]** |
| E-3 | I12 — no model produces a metric | `grounded()` over the Analyst's prose | zero ungrounded numeric tokens; an injected bad number triggers one retry then the template **[unit]** |
| E-4 | The Analyst fallback | force `write_analysis` to fail | prose carries `FALLBACK_PREFIX`, the run still completes **[TODO]** |
| E-5 | Stop is cooperative | Stop mid-session | the run returns to `pending`, **not** `completed`; resume re-asks only unanswered twins **[TODO]** |
| E-6 | Resume re-pays nothing | resume after E-5 | design-call counter unchanged; `answered_twins` skipped **[TODO]** |
| E-7 | I9 — nothing is overwritten | inspect after a rerun | a second run appends; "latest" is a boolean flipped in the same transaction **[unit]** |
| E-8 | I15 at run level | fail every twin in a cell | `twins_n = 0` → `failed`, never `completed` with index 0.000 **[TODO]** |
| E-9 | The noise floor is measured | `00000` and `SHAM` on the real panel | \|index(00000)\| reported; **a lever effect below it is not an effect** |
| E-10 | I17 — nothing is imputed | an interaction with two of three cells | reports which code to run; no estimate, no interpolation **[unit]** |
| E-11 | Crash recovery | kill the process mid-session, restart | the session is `paused`, not stuck `running`; resumable **[TODO]** |
| E-12 | Serial discipline | any session | one concurrent provider request; `max_concurrency=1` honoured **[TODO]** |

### 6.6 Tier F — statistics. Strong already, two gaps

| id | What it proves | How | Pass |
|---|---|---|---|
| F-1 | The golden dataset | `pytest tests/test_stats_golden.py` | 345 values, \|Δ\| < 0.001 **[done]** |
| F-2 | `ModelSpec.fingerprint()` is `7c7fd73a12a4ec48` | pinned in CI | unchanged, and the `UNVALIDATED` banner is driven by it **[done]** |
| F-3 | Casewise deletion, not imputation | a matrix with holes | rows dropped, count reported **[unit]** |
| F-4 | Reverse coding reads each item's own scale | assert no reverse-coded item is 5-point | holds **[done, unit]** |
| F-5 | The export's two header rows; construct means pre-computed in Python | inspect an export | I12 holds in the file, not just the UI **[unit]** |
| F-6 | HTMT confidence intervals | §0.7 item 4 — **not implemented**; point estimate judged against 0.90 | researcher decision: ~25 min of extra resampling **[TODO]** |
| F-7 | The statistics never read the sweep | layer test | `stats/` has no path to `runs` **[done]** |

### 6.7 Tier G — the validity tests

These are the study's own credibility argument, so a stub verdict is worth nothing.

| id | Test | Pass condition |
|---|---|---|
| G-1 | 1 and 3 — no new model calls | a real verdict instead of `INCONCLUSIVE`, **and zero model calls on the counter** **[TODO]** |
| G-2 | 4 — contradictory probe | a verdict; the probe must **not** appear in `variants` (`assert_not_a_probe` guards the write) **[unit]** |
| G-3 | 5 — wording and order swap | a verdict; stored `lever_order` still describes what was shown **[TODO]** |
| G-4 | 6 — ablated persona | a verdict; the ablated persona must **not** appear in `twins` **[unit]** |
| G-5 | 7 | a verdict **[TODO]** |
| G-6 | 8 — temperature sweep | a recommendation; then **apply it deliberately** to `TwinConfig.temperature` (§5.4). Depends on C-14 **[TODO]** |
| G-7 | Every badge matches `CALLS_PER_TWIN` | bookkeeping test **[done]** |

### 6.8 Tier H — the UI. Never once clicked

**No Gradio server has been run in the M15, M16 or this session.** Every screen is verified only by
`build_ui()` succeeding and by the service-layer tests. This whole tier is **[TODO]** and needs a
human at the screen.

```bash
SUPABASE_URL="" SUPABASE_SERVICE_KEY="" PYTHONPATH="src;." ./venv/Scripts/python.exe app.py
```

* **H-1** Twins tab: a row click fills the twin-id box and opens the panel; Enter and Space too;
  the selected row highlights.
* **H-2** Twins tab: *Run twin quality test* respects all four filters and shows the right count;
  the budget card says 12 calls per twin, not 18 (§3.5 — this is the live proof of the Settings
  read path at the screen).
* **H-3** Agents tab: the log resets on a new session; the job line updates every 3 s; Stop, then
  Resume.
* **H-4** Dial board: *Ask the twins* starts a session on a cache miss; `00000` stays disabled;
  *Rerun?* inherits the panel (I14 — check `session_panel` matches).
* **H-5** Twin Studio: all of C-11, C-12, C-13 at the screen.
* **H-6** Agent Studio: Quality Checker's `Held-out item · Driver said · Twin said` table and
  keep/drop verdict; Twin Interviewer's two calls and six-metric saved-vs-edited comparison, which
  **writes nothing**; Run Manager produces a plan and leaves `sessions` unchanged.
* **H-7** Results: the scenario text shown is the stored variant, never a re-render (`docs/09` §2).
* **H-8** Every table that cannot be resizable is scrollable, and no specified element is missing
  (`CLAUDE.md` — degrade styling, never content or ordering).

### 6.9 Tier I — reproducibility and deployment

| id | What | Pass |
|---|---|---|
| I-1 | A completed run replays from stored fields alone | rebuild the prompt, the persona hash, the lever order, the style version and the wording; byte-identical **[TODO]** |
| I-2 | The four caches are the specified ones | `docs/04` §6 — no fifth cache invented **[unit]** |
| I-3 | Nothing durable on the filesystem (I16) | evidence reaches Postgres or Storage before it is acknowledged **[unit]** |
| I-4 | The Edge Function's HMAC layer | **never executed** — no Deno. POST `apps_script/sample_payload.json` with a valid signature (expect 200) and a mangled one (expect 401). Nothing in CI can catch this **[TODO]** |
| I-5 | `api/` stays optional | no feature depends on an HTTP route existing **[unit]** |
| I-6 | The one-commit PRO + Docker upgrade | `app.py` and `app_docker.py` both build the same `gr.Blocks` **[unit]** |
| I-7 | A `style_version` bump invalidates exactly what it should | bump, then confirm paragraphs and variants are re-rendered and **historical runs still read back by `variant_id`** (§4.2) **[TODO]** |

### 6.10 What "the whole system works as intended" actually requires

The short list, if you want one sentence per tier:

1. **Tier A green** — the deterministic core, every time, before anything else.
2. **T-8** — the six H3 codes pass the Checker. Until then there is no study.
3. **D-1, D-2** — one twin scores through the gate, with `items_n = 18` and H2 stored.
4. **E-1, E-2, E-9** — one real sweep cell with a computed index **and a measured noise floor**,
   because a lever effect below \|index(00000)\| is not an effect.
5. **C-5, I-1** — a completed run replays byte-identically from stored fields. This is what makes
   the numbers defensible rather than merely produced.
6. **G-1 through G-6** — the validity tests give real verdicts, and test 8's temperature is applied
   deliberately.
7. **F-1** — the golden gate still passes at the end, proving nothing upstream moved a statistic.
8. **Tier H** — a human has actually used every screen.

---

## 7. Suggested order for the next session

1. **Tier A** (~2 min). Confirm 783 green before touching anything.
2. **T-3 and T-4** — both free, no model calls. They give you the evidence for the §5.1 and §5.2
   decisions instead of a guess, and T-3 may turn §5.1 from one collision into a pattern.
3. **T-5(a)** — free. Check whether `3.2.a`/`3.2.d`'s anchors come from the mis-filed corpus
   chunks. If they do, §5.3 and the defect in `memory/project-gigworker-twin-study.md` are the same
   problem and should be fixed once.
4. **Take the §5.1 and §5.2 decisions.** Nothing renders past them.
5. **T-7, then T-8.** v2 has a clean slate and a full re-render budget, so this is the real attempt.
   Expect ~11 design calls plus coverage probes; budget 15–20 minutes.
6. **T-1, T-2, T-6, T-12, T-13** to close Tier B.
7. Then Tier C (C-4, C-5, C-10, C-14), then Tier D, then Tier E at `PANEL_SIZE=2`.
8. **Before Tier E writes anything**, settle where smoke-test evidence lands — §8.
9. Tier G, then Tier H with a human, then Tier I.
10. Re-run Tier A and F-1 at the end.

---

## 8. Evidence hygiene — decide before Tier E

Tier E is the first thing that writes to the **evidence tables**. `runs`, `run_events`,
`twin_answers`, `twin_quality_runs` and `validity_results` are append-only by `CLAUDE.md` rule 6:
there is no UPDATE and no delete path in the code. A `PANEL_SIZE=2` smoke session therefore leaves
permanent rows that are not a study result and never can be — the real panel is 20, and a cell
answered by a different set of twins is a different experiment (I10, I14).

This was raised at the end of the M16 session and **deliberately left undecided**. The options:

1. **Add `sessions.purpose`** (`'smoke'` | `'study'`, default `'study'`) — a small additive
   migration, so a test session is marked in the data rather than inferred from its panel size.
2. **Run it here and exclude later**, identifying smoke sessions by `sessions.config.panel_size`.
   No migration; the marker is inferred, and a future reader has to know to look.
3. **A scratch Supabase project** for every smoke test, keeping this project's evidence tables
   empty until the real sweep. Costs a project and a re-seed, and the smoke tests then never
   exercise the real schema.

`lever_paragraphs` and `variants` are **not** in this category — they are caches keyed on
`style_version`, and clearing them is legitimate invalidation (done this session).

---

## 9. Cost model, and the scratch scripts

### Costs measured this session

| Thing | Cost |
|---|---|
| One lever paragraph, first render | 5–25 s, 1 design call |
| One cell's coverage probes | 1 model call **per commitment** — this is the expensive part |
| One cell, render + check, 8 commitments | 40–300 s (`12220` took 296 s) |
| All six H3 codes | **660 s** |
| One twin, 37-item battery | ~11 s, 1 call when clean |
| One Studio run, battery + 2 questions | ~12 s |
| The quality gate, per twin | 6 calls × `quality_runs_per_twin` — **12** at the live value of 2 |
| A full sweep at the default panel | ~4,860 twin calls, **serial** |

The provider tier allows **one concurrent request**. Before adding any call, ask whether it
multiplies by 243, by the panel size, or by both (`CLAUDE.md`).

### Scratch scripts from the M16 session

They live in the session scratchpad, **not the repo**, and are described here so you can rebuild
them in one pass. All are read-only on the evidence tables.

| Script | What it does |
|---|---|
| `measure_band.py` | Renders one `lever:dial` and scores gate 3 exactly as `check_invariance` does. Writes **nothing** — no pool, no `lever_paragraphs`. The cheapest way to re-measure a lever after any style-contract change. `python measure_band.py L4:2 L3:2 L1:1` |
| `measure_repair.py` | Renders `L4` dial 1, then compares two repair instructions (wordless vs one quoting the measured grade) over N repeats. Writes nothing. |
| `prove_live_answer.py` | One twin, one stored variant, the 37-item battery, through `ask_items`. Writes nothing. Prints items, retries, calls, lever_order, seed, out-of-range and the baseline delta. |
| `render_v2.py` | Renders a code through the real `render_and_check` and reports `attempts` per paragraph. **Note:** `render_and_check` deliberately does **not** store the variant — `orchestrator/loop.py` and `services/quality.py` do, right after reading the verdict — so a script that renders without calling `VariantRepo.put` leaves `variants` empty and the next caller pays the render again. |
| `studio_test16.py` | Stores the variant the way the orchestrator does, then runs `ask_studio` with the battery and two questions. The only one that writes (`studio_runs`, the quarantined table). |
| `render_h3_stimuli.py` | **The T-8 script.** Renders all six H3 codes, stores each with its report, and reports every failure instead of aborting on the first like `_render_stimuli` does. Prints the per-paragraph word/grade table and a §3.3 verdict line. |

---

## 10. Things that are easy to get wrong, collected

Learned the hard way this session. Each cost real time.

1. **`render_and_check` does not store the variant.** Its callers do. A render script without
   `VariantRepo.put` silently leaves `variants` empty.
2. **`AnswerVector.answers` must stay `dict[str, Any]`.** `dict[str, int]` rejects `5.5` and
   `null`, which are defects the ladder must be allowed to name and re-ask for.
3. **`compute_index` is a normalised weighted mean.** Uniform weights return the unweighted index,
   so a weighting test built on uniform weights proves nothing.
4. **`variants` is keyed on two columns.** Any new lookup must use both (§4.2).
5. **A `_repair_for` of `None` means "leave this lever alone"**, not "re-render it without an
   instruction" (§4.1).
6. **The re-render budget is durable now.** A render attempt on a cell spends real, permanent
   budget. Clear the cache rows for a style version if you need a genuine retry.
7. **`_override` in `services/config.py` is process-global.** A test that touches it must restore
   it, or it leaks into every later test.
8. **On Windows:** `PYTHONIOENCODING=utf-8` before printing any rendered paragraph, and
   `PYDANTIC_AI_NO_BANNER=1` to keep output readable. Redirecting a long-running script's stdout
   buffers it, so you see nothing until it exits — check progress by querying the database instead.
9. **`CheckerReport` forbids extras** and has no `version_code` field.
10. **A bad-draw single measurement is not a measurement.** Design temperature is 0.3; `L4` dial 1
    needed three draws to show it was structural and `L1` dial 1 looked fixed on one draw and was
    not. **Three draws minimum before concluding anything about a render.**
