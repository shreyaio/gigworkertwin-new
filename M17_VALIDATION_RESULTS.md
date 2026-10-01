# M17 — validation results. Tier A, and the free half of Tier B

**Run 2026-10-01 against `HANDOFF_M17_VALIDATION_PLAN.md`.** Every number here was produced by a
script; nothing is inferred. **No model call was made and nothing was written to the evidence
tables.** The scratch scripts are in the session scratchpad.

Read §1 first: it changes the diagnosis of two of the three blockers, and one of the plan's own
free tests was returning a false negative.

---

## 0. Status against the plan

| Tier / id | Result |
|---|---|
| A-1 … A-7 | **7/7 green.** 783 pass → **787** with the new T-12 tests. `ruff` clean, 6 import-linter contracts hold, `build_reference --check` exit 0, golden PLS-SEM 17/17, `build_ui()` constructs. |
| T-3 | **Run, and the recipe as specified is defective.** See §1.1. Corrected sweep in §1.2. |
| T-4 | **Run. Option 1 strictly dominates.** See §2. |
| T-5(a) | **Ruled out, on two independent grounds.** See §3. |
| T-6 | **FAILS on the stored evidence.** Length tracks dial with zero overlap. See §4. |
| T-12 | **Closed.** 4 new tests, each verified by reverting the gate. See §5. |
| T-1, T-2 | Still researcher decisions — but the evidence base has changed. §1, §2. |
| T-5(b), T-7, T-8, T-9, T-13 | Not attempted: they need live model calls, and §1 of the plan says do not render until §5.1 and §5.2 are decided. |

---

## 1. §5.1 is wider than stated, there is a second collision, and the gate is not what blocks it

### 1.1 The T-3 recipe as written returns a false clean bill of health

T-3 says: "difflib every commitment in the lever's own set against every entry in its `do_not_say`;
report ratio > 0.6". Run exactly that way over all 1,105 (must-say, forbidden) pairs:
**no pair scores above 0.6, and the known `5.1.c` / `4.1.d` collision scores 0.048.**

Two independent reasons, either of which alone would have made T-3 conclude "no pattern":

1. **`difflib.SequenceMatcher` defaults to `autojunk=True`.** On a sequence longer than 200 elements
   it treats any element occurring in more than 1% of the text as junk. Commitment texts are 200–350
   *characters*, so nearly every letter becomes junk and matching collapses. The longest common
   substring of two commitments that both open *"Remove … disparagement … deactivation"* comes back
   as **2 characters**. Any future use of difflib on this register must pass `autojunk=False`, and
   should compare **words**, not characters.
2. **Dilution.** Even corrected, whole-text similarity is the wrong measure. Two commitments can
   share an entire forbidden clause and still score low because the rest differs. Corrected
   word-level ratio for `5.1.c` vs `4.1.d` is 0.200; longest common word-run 0.065; content-word
   Jaccard 0.129 — **ranked 20th**, well below an unrelated pair at 0.400.

**This also bears on `HANDOFF_M15_LIVE_PATH.md` §2.4 item 3.** §5.1 attributes M15's miss to the
sweep comparing the wrong sets. That is true, but `autojunk` is a second, independent reason that
sweep could not have found the collision even against the right sets.

### 1.2 The collision is symmetric and affects 216 of 243 codes, not 81

`4.1.d` is in **L4 dial 1 and dial 2**; `5.1.c` is in **L5 dial 1 and dial 2**. Each is in the
other's `do_not_say` in all four cases. So the contradiction is present whenever
`L4 ∈ {1,2}` **or** `L5 ∈ {1,2}` — **216 of 243 codes**, not the 81 §5.1 states.

Empirically (plan §3.6) `L4` d1, `L4` d2 and `L5` d2 all **rendered**; only `L5` d1 refused. So the
same structural contradiction produced a refusal in one cell and silent output in three.

### 1.3 A second collision, on `L5` dial 1, not previously known

`L5` dial 1 must state `5.1.b` while `5.2.b` is forbidden:

* `5.1.b` — "Publish, **on the Driver app**, a written statement that Uber will recognise and
  bargain with **an independent body of drivers or a trade union**."
* `5.2.b` (forbidden at dial 1) — "Publish formal, non-exclusive recognition of **an independent
  drivers' body or union on the Driver app**."

These are substantively the same commitment. Content-word Jaccard **0.400 — the highest of any pair
in the register**, higher than the known `5.1.c`/`4.1.d` collision. It exists **only at `L5` dial
1**: at dial 2 `5.2.b` joins the must-say set and the conflict disappears.

`L5` dial 1 is therefore the only cell in the register carrying **two** contradictions, and it is
the only cell that refused to render. The agent's stated reason named `5.1.c`, so this second one is
a contributor rather than necessarily the cause — but it is unresolved and undocumented.

### 1.4 The containment gate is **not** what blocks these cells — and this reframes the fix

I gave the checker a paragraph stating each lever's **own** commitment verbatim, which is the
correct behaviour, and asked whether the forbidden near-twin fires:

| Cell | Must state | Forbidden near-twin | Containment |
|---|---|---|---|
| `L4` d1 | `4.1.d` | `5.1.c` | does **not** fire |
| `L4` d2 | `4.1.d` | `5.1.c` | does **not** fire |
| `L5` d1 | `5.1.c` | `4.1.d` | does **not** fire |
| `L5` d2 | `5.1.c` | `4.1.d` | does **not** fire |
| `L5` d1 | `5.1.b` | `5.2.b` | does **not** fire |

`signature()` subtracts `bigrams(allowed_text)`, so the shared clause is removed from the forbidden
commitment's signature by construction. **The gate already tolerates the overlap.**

What blocks `L5` d1 is therefore the design agent's reading of the `do_not_say` **text** in the
brief — not gate 2. That matters for choosing among §5.1's options: the handoff's objection to
option 1 was that it "weakens containment exactly where two levers genuinely overlap", and the
measurement shows **containment was never catching that overlap in the first place**. The fix space
is the brief text shown to the agent, not the checker.

> **Correction to something stated earlier in this session.** On the strength of a paraphrase probe
> I said containment would catch `5.1.c` in an L4 paragraph, and therefore that the agent must have
> dropped `4.1.d` to avoid a leak. The verbatim test above shows it would not. The brief-level
> contradiction remains the likely cause of the dropped commitment; the gate-mediated mechanism I
> described does not exist.

### 1.5 A latent false positive worth more than the one in §5.2

The gate tolerates the overlap only for *some* wordings of the same true fact. `L4` dial 1, stating
a true fact about its own `4.1.d`:

| Wording | Verdict |
|---|---|
| `4.1.d`'s own words ("Disparagement, and harm to Uber's brand … removed from the grounds for deactivation") | passes |
| **"Uber removes the disparagement ground for deactivation."** | **FAILS on `5.1.c`**, matching `("disparagement","ground")` and `("ground","deactivation")` |
| "You can no longer be deactivated for criticising Uber publicly." | passes |
| "Criticising Uber is no longer a reason for deactivation." | passes |

So a correct `L4` cell passes or fails on **which words it chooses for the same fact**, at design
temperature 0.3. This is the same *class* as §5.2's false positive but with substantive words rather
than function words, and it is latent across `L4` d1 and d2 — **162 of 243 codes**. It has not fired
yet only because the agent happened not to use that phrasing. Neither §5.2's option list nor T-4's
pass condition addresses it.

---

## 2. T-4 — the §5.2 options measured. Option 1 strictly dominates

All 285 (lever, dial, forbidden) combinations. "empty sigs" and "verbatim" are the two numbers the
plan asks for; the partial-leak columns are added because those two turn out not to discriminate.

| Option | empty sigs | verbatim | 1st sentence | **1st clause** | 1st half | §5.2 FP |
|---|---|---|---|---|---|---|
| 0 — current: bigrams, 1 hit | 0 | 285/285 | 285/285 | **277/285** | 285/285 | **still fires** |
| **1 — content-word pairs only** | **0** | **285/285** | **285/285** | **277/285** | **285/285** | **cleared** |
| 2 — require 2 distinct pairs | 0 | 285/285 | 285/285 | 268/285 | 285/285 | cleared |
| 3 — trigrams | 0 | 285/285 | 285/285 | 268/285 | 285/285 | cleared |
| 1+2 combined | 0 | 285/285 | 285/285 | 268/285 | 285/285 | cleared |

**Option 1 clears the false positive at zero sensitivity cost** — identical to the current gate on
every leak shape measured. Options 2, 3 and 1+2 each lose 9 partial-leak detections. Option 1 is the
narrowest change that fixes the observed failure and the only one that costs nothing measurable.

Two corrections to §5.2's own reasoning:

* §5.2 option 3 predicts trigrams "would still match … so this one probably does not fix the
  observed case". **It does clear it.** Grams are built from *content* words, so "rather than
  leaving" becomes the trigram `(rather, leaving, responsibility)` in the paragraph against
  `(difference, rather, leaving)` in `1.1.a` — different trigrams. The reasoning was in surface
  words; the code works in content words.
* T-4's stated pass condition ("0 empty signatures, 100% verbatim detection") is satisfied by
  **every** option, including doing nothing. It cannot select between them. Partial-leak sensitivity
  can, and does.

The function-word list option 1 was measured with is
`rather leaving than where does doing made make makes making given give gives giving taking take
takes let lets say says saying said state states stating within across among per via upon`.
It is a first cut, not a researcher decision — the list is a frozen research constant
(`checker.STOPWORDS` says so), so whatever is settled on belongs in `docs/DECISIONS.md`.

---

## 3. T-5(a) — the corpus filing defect is ruled out, twice over

1. **The re-filing is already applied and frozen.** `data/reference/corpus_chunks.json` has 126
   chunks, of which **44 carry `refiled_from`** naming *"Fairwork AI Principles filing in corpus
   v2026.09"*. Threshold 3.2 now holds **22 chunks** — the "~22 chunks needing re-filing" that
   `memory/project-gigworker-twin-study.md` flagged. That note was stale and has been corrected.
2. **Even unfixed it could not reach a brief.** `ReferenceData.anchor_chunks()` selects a brief's
   anchor chunks purely by `source_id`; `select_anchors` then round-robins by source. **No path
   reads `threshold_id`.** Re-filing a chunk's threshold changes nothing the design agent ever sees.

**§5.3's explanation 3 is therefore dead.** Of its three candidates only 1 (too many commitments per
paragraph) and 2 (probe strictness) remain — plus a fourth the handoff does not list: for the
`4.1.d` failures specifically, the brief-level contradiction in §1.2. `4.1.d` is uncovered in
exactly the L4-active cells — 2/2 of the `L4=2` codes (`12220`, `00222`) and 1/3 of the `L4=1` codes
(`11211`) — and never where `L4=0`. T-5(b) should render `L4` d1/d2 and check whether `4.1.d` is the
dropped commitment before blaming paragraph length.

---

## 4. T-6 — FAILS. Paragraph length tracks the dial with no overlap

Measured on the 7 stored `v1` `lever_paragraphs` rows, plus the v2 figures from plan §3.6:

```
stored v1 rows          dial 1: n=4  83,  89,  96, 109     mean  94.2
                        dial 2: n=3 139, 150, 151          mean 146.7
§3.6 v2 renders         dial 1: 83, 95, 102
                        dial 2: 116, 149, 150, 150
combined                dial 1: 83 – 109        dial 2: 116 – 151
```

**The distributions do not overlap.** T-6's pass condition is "dial-1 and dial-2 distributions
overlap"; its stated failure mode is "if dial-1 ~60w and dial-2 ~150w, `word_max` is a confound".
Observed is 83–109 against 116–151 — not as extreme as the example, but a clean separation with a
7-word gap and no shared value.

So **§5.5 is not only a "one draw from binding" ceiling risk.** Length is a stimulus property
(`HANDOFF.md` §0.7 item 9): a twin shown a dial-2 cell reliably reads ~50% more text than one shown
a dial-1 cell, so part of any measured dial-1 → dial-2 effect is "more text". This is now a decision
rather than something to watch, and it is a decision about the **word band**, which is a research
commitment — untouched here.

Caveat: the sample is small (n=7 stored, n=7 reported) and all of it predates the M16 fixes. It
should be re-measured at T-8 when the grid renders. But the mechanism is structural — eight
commitments cannot be stated in 90 words — so the separation is unlikely to close on its own.

---

## 5. T-12 — closed. `tests/test_m17_i3_stored_variant.py`, 4 tests

The plan marks the `SessionRunner` and `_render_stimuli` halves **[TODO]**. The gap was narrower and
more interesting than "no test": `test_m7_orchestrator.py` already proves the runner refuses a
failing report, but it **supplies its own `render_and_check` stub and so never touches the
`variants` cache**. The real `render_and_check` short-circuits on a stored row and returns the stored
report verbatim, and a failed cell is stored as failed (§5.2) — so **the cached-failure path is the
one that will actually occur in the study, and nothing exercised it.**

| Test | Proves |
|---|---|
| `test_a_stored_failure_is_returned_as_a_failure_and_costs_no_model_call` | the cache returns `passed=False`, so every downstream I3 gate sees it |
| `test_a_stored_failure_is_not_re_rendered_into_a_pass` | the render path is never entered — a recorded failure cannot become an unrecorded pass, and no durable re-render is spent |
| `test_the_quality_gate_refuses_a_stored_failed_variant` | `quality._render_stimuli` raises `QualityGateError` rather than showing a failed cell |
| `test_the_session_runner_asks_no_twin_for_a_stored_failed_variant` | the runner over the **real** cache read: run `failed`, `twin_calls == []` |

**Each was verified by reverting the gate and watching it fail**, per `CLAUDE.md`: breaking the three
sites (`quality`'s `if not report.passed`, `loop`'s, and forging `passed=True` on the cache read)
fails all four; removing the cache short-circuit fails three.

---

## 6. Smaller observations

* **`app_config['style']` is a stale record, not a live value.** It reads `style_version: 'v1'` at
  `version 1` while the app runs v2. It is written by `seed_db.py` and **read by nothing** —
  `load_style_contract()` reads `config/style_contract.yaml` directly. So it is not a live
  contradiction, but plan §3.5 describes `app_config` as "live and read" without qualification, and
  a future reader could reasonably treat this row as authoritative. Worth either refreshing on a
  style bump or dropping.
* **`variants` has no `passed` column.** The verdict lives at `checker.passed` inside the JSON blob,
  which is what all three gates read. The plan's "all `passed=true`" is accurate; noted only because
  a query written against a `passed` column would silently match nothing.
* **DB state confirmed exactly as the plan's census states it**: `twins` 50, `survey_answers` 3650,
  `lever_paragraphs` 7 (all v1, all `attempts=1`), `variants` 3 (all v1, `checker.passed=true`),
  `studio_runs` 6, and `runs` / `run_events` / `sessions` / `twin_answers` / `twin_quality_runs` /
  `validity_results` all **0**. v2 is a clean slate with a full re-render budget.
* Of the 7 stored v1 paragraphs, **4 have a reading grade over the 16.0 ceiling** (`L1` d1 18.07,
  `L3` d2 24.51, `L4` d1 18.08, `L4` d2 17.89) — consistent with the plan, and a reminder that these
  rows are the pre-fix record.

---

## 7. What is recommended next, and what was not touched

**Decisions now better supported than they were:**

* **T-2 / §5.2 → option 1** (a signature pair must be two content words). Strictly dominant on the
  measurement: clears the false positive, loses nothing. Then handle the `L4` phrasing false
  positive in §1.5 — which is the larger exposure of the two.
* **T-1 / §5.1** → the fix belongs in the **brief text**, not the gate (§1.4). Note that the scope is
  216 codes not 81, that `L5` d1 carries a **second** collision (§1.3), and that option 3 ("accept
  `L5` d1 cannot render, exclude 81 cells") would have to exclude far more if the contradiction were
  treated consistently across L4 as well.
* **T-6 / §5.5** → the word band is now a live confound question, not a watch item.

**Not done here:** no researcher decision taken, no gate changed, no register or `do_not_say` edit,
no change to the word band, nothing rendered, nothing written to an evidence table. §5.1 and §5.2 are
still open, so per plan §1 item 2 nothing should be rendered under v2 yet.
