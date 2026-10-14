# HANDOFF — synthetic twin credibility: why they fail the H3 gate, and the one fix left

**Written 2026-10-13.** Resume point for a new session. Read this file, then
`docs/DECISIONS.md` entries dated **2026-10-12** and **2026-10-13** (four entries, in order) for
the full evidence. Everything claimed here was measured, and the command that measures it is given.

**One sentence:** synthetic twins were failing the quality gate because the *generator* was wrong,
not the twins; four defects have been found and fixed, one remains — `lever_reactions` is a hidden
batch constant no persona discloses — and fixing it is **Route A** in §6.

> **STATUS, final — 2026-10-14. Nine stages run. STOP CHANGING THINGS AND GET REAL PART 17 DATA.**
>
> Full record: `docs/DECISIONS.md`, entries "2026-10-13 (diagnosis)", "(`v11`)", "(stage 7)" and
> "2026-10-14 (stage 8)". Nothing below was tuned to a pass rate; `mae_max` 1.0 and
> `pct_within_1_min` 0.80 are untouched, as is every line of the gate.
>
> **Nine stages. Seven moved their own target metric. The gate never moved.**
>
> | stage | change | MAE | kept |
> |---|---|---|---|
> | 1 | H3 prompt `v3` | 1.219 | 0/10 |
> | 2 | legible reactivity `v9` | 1.352 | 0/9 |
> | 3 | H3 prompt `v4` | 1.325 | 1/10 |
> | 4 | `v10` lever salience | 1.575 | 0/10 |
> | 5 | `v11` holdout compression | 1.092 | 2/10 |
> | 6 | `v11` scope corrected to H3 | 1.214 | 1/10 |
> | 7 | floor moved off the wall | 1.239 | 0/10 |
> | 8 | six-call H3 | 1.378 | 2/10 |
>
> **The decomposition that explains all nine.** Every twin's 18 H3 errors split into a per-outcome
> offset plus scatter:
>
> | | MAE | scatter | per-outcome offset |
> |---|---|---|---|
> | real driver | **0.78** | 0.62 | **0.59** |
> | synthetic, one call | 1.22 | 0.71 | **1.03** |
> | synthetic, six calls | 1.39 | 0.79 | **1.11** |
>
> Scatter is the same for everyone and passes comfortably. **The offset is the whole problem and
> nothing in nine stages touched it.**
>
> **What it actually is: granularity.** The twin spends **88% of its answers on `2`, `5` and `6`**
> and almost never says `3` or `4`. The generator's driver uses all seven points on a smooth curve.
> The one real respondent used **four** values — `2`, `3`, `5`, `6`, never `1`, `4` or `7` — which
> is the twin's coarse pattern, not the generator's smooth one. A twin with three buckets cannot
> land within one point of a driver who answers `3`, `4` and `7`, however well it reads the person.
>
> **Four things are now established and should not be re-litigated:**
> 1. **The persona is sound** — twins reproduce their driver's 37 battery answers to **0.18** of a
>    point on the control cells. It was never the persona.
> 2. **The generator's reaction model is calibrated** — it reproduces the real respondent's 18
>    Part 17 answers at **0.392**, inside the gate's own cap.
> 3. **Version differentiation is solved** — version-blind oracle **0.30**, under the cap for 10 of
>    10. Level bias is solved — all three signed biases ~zero after the floor fix.
> 4. **One call beats six.** Previously an assumption (M19 WP-3), now a measured result: six calls
>    made both error components worse. The six-call path stays selectable
>    (`TWINLAB_H3_PROTOCOL=six`), recorded on every row, **default unchanged**.
>
> **The one open question, and it needs data rather than another experiment.** A twin and a real
> respondent both answer a hypothetical battery in a few coarse buckets; the generator answers on a
> continuum. Either real respondents answer coarsely — in which case `_likert` is the remaining
> defect and the gate is asking for a granularity no human produces — **or** this one respondent
> happened to, in which case the twin cannot resolve a 7-point hypothetical to within a point and
> that is a method limit for the paper. **These point to opposite actions and n=1 cannot separate
> them.** Trying both against the gate would be choosing a generator to suit the model, which is
> `docs/08` §2.4's circularity.
>
> **What is needed is the answer DISTRIBUTION of real Part 17 responses**, not their mean — a
> statistic no stage has had the data to read. Until then, the honest report is that the gate is
> working and the twins do not pass it.
>
> **Also note:** the real twin's PASS is weak evidence. Its offset is 0.59–0.78 against the
> synthetic 1.03, and a version-blind twin scores 0.50 against that driver, so the PASS does not
> demonstrate what H3 exists to test (`docs/08` §2.3). `gate_diagnostic.py` prints that bound
> beside every verdict, and refuses a prefix spanning more than one batch.
>
> **State:** 1,115 tests pass; ruff, import-linter and `build_reference --check` clean. Panel-
> eligible twins: 1, the real one. Eight synthetic batches; never pool them.

---

## 1. READ THIS FIRST — the hard rules

These are not style preferences. Each one is a line that was deliberately held across this work,
and breaking any of them silently invalidates the study. `CLAUDE.md` governs; this is the subset
that this particular task keeps tripping over.

1. **NEVER change `mae_max` (1.0) or `pct_within_1_min` (0.80).** They are in
   `config/twin.default.yaml` and on the live `app_config.twin` row. A twin answering the constant
   `3` eighteen times scores MAE 0.76 and would be kept on 10 of 10 — loosening the gate admits a
   random number generator. **Verified: they are untouched. Keep them untouched.**
2. **NEVER fit anything to a twin's output.** `reaction_gain` was fitted to a *real respondent's
   survey answers*. Fitting any generator parameter until twins pass is the circularity
   `docs/08` §2.4 forbids, and it would make every path estimated on synthetic data meaningless.
   If you find yourself choosing a number by checking the pass rate, stop.
3. **NEVER write `kept = True` on a row that failed, and never add an eligibility route that
   bypasses the gate.** An earlier proposal to let "machinery-verified" synthetic twins onto a
   panel with `kept` left `False` was **rejected by the researcher**. Twins reach a panel by
   passing or not at all. `qualified_twin_ids` is unchanged and must stay unchanged.
4. **NEVER tell the twin which direction a construct moves.** The H3 prompt may say *how* to read
   the persona and *that* the six versions differ. It may not say "fairness rises under appeals" or
   anything equivalent. That is the twin's to work out and the gate's to score. `twin_h3_v4.md` was
   checked against this and is clean.
5. **NEVER give a synthetic persona a section a real persona does not have.** This was the reason
   reactivity was *not* given its own heading, even though that was the obvious fix. A real driver
   has no "how I react to change" field, so a synthetic persona with one carries a shape no real one
   does — the parity `CLAUDE.md` insists on when it refuses a respondent who answered three of 37
   probes. **Route A must obey this too:** lever salience goes in the existing free-text shape, as
   circumstance clauses, not a new block or a new register item.
6. **The frozen reference data is frozen.** `data/reference/*.json` must not be regenerated or
   hand-edited. `python -m twinlab.ingest.build_reference --check` must exit 0.
7. **Bump `GENERATOR_VERSION` whenever a drawn value or the draw order changes**, and
   `VOICE_VERSION` whenever a bank's contents change. Route A changes both. A seed does not
   reproduce across a version and that must be visible in the data.
8. **Never pool two generator versions in one measurement.** Three batches exist (§8); test 3 was
   briefly measured across two of them and the reading was meaningless. `tools/gate_diagnostic.py`
   requires `--prefix` for exactly this reason.
9. **No live DB and no live LLM in CI, ever.** The gain's derivation runs against the live database
   by hand; the test suite pins the constant and round-trips the fit on a generated batch instead.

---

## 2. THE END GOAL — what "done" means

**Primary (the gate).** Most synthetic twins in a fresh batch pass the H3 quality gate on their
merits, under the unchanged thresholds `mae ≤ 1.0 AND pct_within_1 ≥ 0.80`.

A concrete target: **≥ 6 of 10 kept.** Currently **1 of 10**. Treat this as a target, not a
promise — if Route A lands and the number is still low, the honest outcome is to report that and
diagnose again, **not** to move a threshold or fit a parameter.

**Secondary (the validity tests, `docs/08` §4).** On a single fresh batch, measured without pooling:

| test | what it asks | now | goal |
|---|---|---|---|
| 1 wrong person | is a twin closer to its own driver than a stranger's? | **CHECK** (gap +0.263, CI [−0.044, 0.569], needs ≥ 0.50 and CI excluding 0) | **PASS** |
| 3 naive predictors | does the twin beat "assume no change"? | **FAIL** (twin 0.619 vs no-change 0.475) | **PASS** |
| 2, 4–8 | need a frozen panel, which needs a kept twin | now runnable (1 eligible) | run them |

Tests 1 and 3 re-score stored vectors and cost **no model calls** — run them freely.

**Why test 3 is the one to watch.** It fails because the synthetic driver barely moves, so
"assume nothing changed" beats the twin. It is also where reaction magnitude legitimately surfaces
as a verdict. If Route A works, test 3 should move most.

---

## 3. THE PROBLEM — the full causal chain

The gate was dropping 9–10 of 10 synthetic twins at MAE 2.1–3.2 against a cap of 1.0. **The twins
were not the problem.** Evidence, in the order it was established:

1. **The twins reproduce their drivers almost exactly.** On the `00000`/`SHAM` control cells they
   matched their driver to a mean absolute gap of **0.16 points across all nine constructs**
   (`FAIR` 1.52→2.17, `TRAN` 1.43→1.35, `LOYA` 1.50→1.40, …). The persona builder and the twin
   agent were sound all along.
2. **The disagreement was about how far a better world moves a driver.** Fairness: the driver's
   baseline 1.52 went to 2.78 (a move of +1.26); the twin's 2.09 went to 5.57 (+3.48). **2.8×.**
3. **The generator was the party that disagreed with reality.** Fitting one gain parameter on
   `lever_effects` against the one real respondent's own 18 Part 17 answers:

   ```
   k=1.00  MAE 1.504   <- the inherited matrix: it could NOT reproduce a real driver
   k=2.11  MAE 0.864
   ```

   Corroborated on the H2 block, which mirrors the battery item for item and so carries no method
   confound: that driver moved **0.375** scale points per mirrored item against the matrix's
   predicted **0.112** (3.3×). **The twins were being failed for agreeing with reality.**
4. **And no twin could have passed anyway, because the answer was unknowable.** Part 17 asks for
   the baseline moved by this respondent's reactivity. The baseline is all over the persona. The
   reactivity was a **hidden batch constant**: across the entire range of `EDEP`, its only
   respondent-level input, the fairness shift varied by at most **0.16 scale points** and by
   **exactly 0.00 on four of the six versions**. Every respondent reacted identically and no
   persona said how reactive they were. The gate was scoring twins on a quantity it had never
   disclosed — an information defect in the *test*.
5. **The same defect, one level down, is what remains.** `lever_reactions = {L1: 2.0, L2..L5: 1.0}`
   — **pay is double-weighted for the whole batch and no persona mentions it.** This is §6.

Two smaller defects found en route: the twin was never shown the **scale anchors** (and `likely7`
has no negative end, so its point 4 is "Moderately likely", not a neutral midpoint); and
`_H3_SUFFIX["KEEP"]` read **`LOYA`** (*"I hope this job carries on"* — affective commitment) for a
question asking **behavioural likelihood**, which inverted the captive-driver relationship `EDEP`
exists to carry.

---

## 4. WHAT WAS ATTEMPTED, AND WHAT EACH ONE MOVED

Every stage changed one thing and had its metric predicted before the run.

| | stage 0 | stage 1 | stage 2 | stage 3 |
|---|---|---|---|---|
| change | anchors + gain + reactivity | H3 prompt v3 | legible reactivity (v9) | H3 prompt v4 |
| batch | SYN-13102026 | SYN-13102026 | SYN-14102026 | SYN-14102026 |
| mean MAE | 1.517 | 1.219 | 1.352 | 1.325 |
| within-1 | 51.9% | 65.0% | 58.6% | 61.4% |
| **kept** | 0/10 | 0/10 | 0/9 | **1/10** |
| r(reactivity band, twin H3) | −0.08 | +0.20 | **+0.87** | +0.37 |
| twin H3 spread ÷ driver | 46% | 190% | 148% | **110%** |
| pushback version ordering | +0.31 | — | **−0.21** | **+0.35** |
| FAIR signed bias | +1.77 | +0.18 | +0.24 | +1.38 |
| r(driver vs twin version means) | — | — | +0.09 | **+0.07** |

For context, before stage 0: mean MAE **2.736**, FAIR bias **+2.88**.

**What this says.** Every targeted metric moved. The level bias is essentially solved
(+2.88 → +0.18 at stage 1). Person-discrimination is solved (−0.08 → +0.87 at stage 2).
Version *differentiation* and the backwards pushback sign are fixed (stage 3). But **mean MAE has
plateaued at ~1.2–1.35 across three stages**, and the one metric that never moved is
`r(driver version means, twin version means)`: **+0.09 → +0.07**.

**Caveats to respect.** Stage 1 and stage 3 are clean (prompt-only, same batch). **Stage 2 is
confounded** — it needed a new batch because `facts_of` changed the draw order, so it changed the
respondents as well as the persona. Do not read stage 2's MAE against stage 1's. Stage 2 also lost
its tenth twin to a provider quota 429; that twin is recorded as **not run**, never as a result.

Stage 3 is a **trade, not a pure win**: version ordering fixed, fairness bias returned
(+0.24 → +1.38), person-tracking gave ground (+0.87 → +0.37). Recorded as a trade and deliberately
not tuned away — both prompts are honest readings and balancing them against a pass rate is rule 2.

---

## 5. WHAT IS DONE — every change, by file

**Nothing is committed.** The repo has one commit and most of the tree is untracked or modified, so
**git will not tell you which changes are this work.** This list is the record.

### Generator — `src/twinlab/generator/synthetic.py` (`GENERATOR_VERSION` → **v9**)
- `GeneratorSpec.reaction_gain` applied in `reaction_shift` as **one multiplier on the finished
  shift**, after the interactions, so sub-additivity survives as a proportion. Structure untouched:
  zeros stay zero, signs and proportions preserved.
- `calibrate_reaction_gain(humans)` — the least-squares fit against real Part 17 answers. **Forces
  unit gain internally**: a fit using the caller's spec as given returns the gain *on top of* the
  one already there, reporting 1.00 ("no correction needed") when it means "2.11 was right". That
  bug was hit and is now guarded by an idempotence test.
- Per-respondent `reactivity`, drawn from the respondent's own RNG, centred on 1.0, multiplied into
  the shift.
- `_H3_SUFFIX["KEEP"]` → `EXIT`, **mirrored after the shift** (`_H3_MIRRORED`), with an import-time
  guard that both tables name the same three questions.
- `clipping_share(spec)` — pre-flight share of a batch pinned at an end of the scale. **Baseline
  targets only**: extending it to holdout answers was tried and reverted because at a calibrated
  gain it fired on the default spec (pushback 84%) and carried no information.
- `spec_from_config` now reads `reaction_gain` and `reactivity_spread` from the YAML.

### Voice — `src/twinlab/generator/voice.py` (`VOICE_VERSION` → **v3**)
- `react:low|mid|high` circumstance family, five phrasings each; `reactivity_tag()` bands it.
- Reactivity holds **three of ten** slots in `facts_of`, so the clause lands early and recurs
  (mentions went from 1–3 per persona to 4–15; first mention from as late as 93% to 8–57%).

### Scale anchors — the twin was answering a different instrument
- `models/twin.BatteryItem` (stem, points, anchors) replaces the bare `(stem, points)` tuple on
  `RoundPrompt` and `H3RoundPrompt`; validator requires one anchor per point.
- `ReferenceData.scale_anchors()` and `.battery_item()` — **the only place a `BatteryItem` is
  built**, so no caller can assemble a round that omits the anchors.
- `agents/twin.py::_battery_line` renders `(answer 1 to 7; 1 = Very unfair, 4 = Neither fair nor
  unfair, 7 = Very fair)` — both ends and the midpoint, omitted on an even scale rather than faked.
- Threaded through `battery_for`, `h2_items`, `h3_items`.

### Prompts — new version files, never edits
- `twin_v3.md` (supersedes v2) — rule 5 says read the words before choosing the number.
- `twin_h3_v3.md` (supersedes v2) — locate the person's reactivity first. *Superseded.*
- `twin_h3_v4.md` (supersedes v3) — **live**. Keeps person-sizing, restores the version as the
  other half. `H3_PROMPT_REF = "file:twin_h3_v4.md"`.
- **`agent_configs.twin.system_prompt` on the live DB is `file:twin_v3.md` (version 3).** Already
  applied. The YAML is only a seed — if you change the twin prompt again you must also call
  `save_agent`, or the screen will say one thing and the study will run another.

### Config fingerprint — a real bug
- `config_match.current_config` now carries **`h3_prompt_sha256`**. `H3_PROMPT_REF` swaps a sibling
  file in for Part 17 only, so `prompt_sha256` never covered the prompt that produced every stored
  H3 verdict: rewriting it invalidated nothing, **the gate skipped every twin** ("already scored
  under this config"), and a verdict from a superseded prompt read as current.
- It also hashes the battery **anchors**, so a verdict taken on an unlabelled scale is superseded.

### UI / config
- `BATCH_SLIDERS` gained four dials: `between_driver_swing` and `incident_share` (added to the spec
  in v6 and **never put on the screen**, so batches could only be drawn at their defaults), plus
  `reaction_gain` and `reactivity_spread`.
- Generator preview carries the clipping pre-flight note; says so explicitly when nothing is pinned.
- `config/generator.default.yaml` documents and sets `reaction_gain: 2.11`, `reactivity_spread: 0.5`.

### Instrument
- **`tools/gate_diagnostic.py`** — read-only, no model calls. Four numbers: reactivity tracking
  (against the ceiling the generator encoded), spread recovery for H2 vs H3, both gate thresholds,
  and signed bias per outcome. **Requires `--prefix`.**

### Tests — 1050 passing
New: gain scales the matrix and nothing else (exact proportionality, zeros stay zero); zero gain is
the control; the shipped gain is pinned to its derivation; the fit round-trips a known gain; the fit
is idempotent; an unscorable fit raises; reactivity varies the shift; the persona states reactivity;
no holdout id or version code leaks into free text; reactivity holds ≥3 slots and exactly one band;
both holdout-only scales name their ends; the fingerprint covers the H3 prompt and differs from the
twin prompt.

**Pre-existing failures, not this work:** 3 failed + 30 errors in `test_stats_golden.py` and
`test_m12_integration.py`, all from a missing `openpls` module. That was the baseline before any
change and is unchanged.

---

## 6. WHAT IS LEFT — Route A, chosen by the researcher

### The defect

`GeneratorSpec.lever_reactions = {L1: 2.0, L2: 1.0, L3: 1.0, L4: 1.0, L5: 1.0}`. **Pay carries
double weight for the whole batch and no persona discloses it.** Same defect class as
`reaction_gain` and as reactivity: a hidden batch constant the twin cannot infer, never checked
against a driver.

It is now the binding obstacle. The twin differentiates the six versions but ranks them wrong:

```
driver ranks highest:  V1 12220,  V3 11010      (both raise pay, L1 ≥ 1)
twin   ranks highest:  V4 11211,  V5 02211      (V5 raises NO pay, L1 = 0)
```

**It cannot be calibrated at n=1** — five lever weights plus a gain is six parameters against
eighteen observations from one respondent, which is underdetermined. That is why Route B
(calibrate against real data) is deferred and Route A was chosen.

### Route A — make lever salience per-respondent and legible

Precedent: the identical fix one level up took reactivity tracking from **−0.08 to +0.87**, the
single largest gain in this whole sequence.

**Design constraints — all four are load-bearing:**

1. **Centre the per-respondent draw on the existing `lever_reactions`.** The batch's mean salience
   must be unchanged, so Route A adds *variance* without moving the batch mean. This is exactly how
   reactivity was centred on 1.0, and it is what keeps the change non-circular: you are not
   re-weighting the population, you are admitting that drivers differ. **Do not re-tune the means.**
2. **Express it in the existing free-text shape** — a `salience:*` circumstance family in
   `voice.py`, like `react:*`. **No new persona heading and no new register item** (rule 5).
3. **Natural language naming the thing, not the lever code.** "The money is the only thing that
   would change my mind"; "it is the disrespect, not the money"; "give me somewhere to appeal and
   I would feel differently". Never `L1`, never a dial, never a version code — the I8 guard refuses
   a version code anywhere and a holdout id anywhere.
4. **Enough slots to be legible.** Reactivity needed three of ten before the twin could track it.
   Expect salience to need comparable prominence. Check with the mention-count measurement in §7.

**Suggested shape** (the next session should confirm it against the code before committing):

- New `GeneratorSpec.salience_spread: float` (bounded, default > 0), documented like
  `reactivity_spread`.
- Per respondent, draw a weight per lever centred on `lever_reactions[lever]`, from that
  respondent's own RNG, in a fixed order. Keep them positive.
- `reaction_shift` takes the per-respondent weights and uses them in place of `spec.reaction(lever)`.
  **Keep `captive_voice`'s EDEP multiplier on L5** — it is `docs/06` §4's one dashboard interaction.
- `voice.py`: `salience:*` clauses keyed on **which lever this respondent weights highest**, plus
  slots in `facts_of`.
- `GENERATOR_VERSION` → **v10**, `VOICE_VERSION` → **v4**. The new draws change the draw order, so
  a v9 seed will not reproduce.
- Tests mirroring the reactivity ones: the weights vary between respondents; the batch mean is
  unchanged; the persona states the salience; no leak; the tables stay in lockstep.

**Then:** generate a fresh batch → import twins → run the gate → `tools/gate_diagnostic.py`.

**Prediction to state before the run** (and to report honestly if it fails):
`r(driver version means, twin version means)` leaves **+0.07**, and `within-1` rises above 61.4%.

### After Route A

Re-run tests 1 and 3 on the fresh batch (free, no model calls) against the §2 targets. Then, if a
twin is panel-eligible, tests 2 and 4–8.

**Still open, and not to be touched by fitting:**
- **The residual level question.** The H3 fit says gain 2.11; the H2 corroboration suggests 3.3×.
  Both are n=1. Re-derive with `calibrate_reaction_gain` as real Part 17 responses arrive. **Do not
  split the difference to make twins pass.**
- **The single-call H3 protocol** (`H3_PROTOCOL = "h3_single_call_v1"`, M19 WP-3). Eighteen numbers
  for six worlds in one context may be producing one impression emitted six times. Reverting to six
  calls is **6× the cost and a documented research decision** — the researcher's, not a tuning step.
- **`PUSH → VOIC`.** `VOIC` is three attitude items and one behaviour item, the same weakness
  `KEEP → LOYA` had. Its bias is the smallest of the three and the researcher has not taken the
  remapping decision.
- **The floor pile-up.** The current spec (`frustrated`, `FAIR`/`TRAN` at 2.0, swing 2.4) pins
  **37–38%** of respondents at the exact floor on fairness and clarity. This compresses the
  between-person distance that test 1 measures against (ceiling 1.025). Moving those sliders off
  the end, or lowering the swing, would give test 1 real headroom. The preview warns about it now.
  **Researcher's choice of population — do not change it silently to help a test pass.**

---

## 7. HOW TO RUN THINGS

**Use the project venv for anything that calls a model.** The system interpreter lacks
`pydantic_ai`; a gate run under it fails with `ModuleNotFoundError` after writing nothing.

```bash
# the diagnostic (read-only, no model calls) — ALWAYS pass --prefix
python tools/gate_diagnostic.py --prefix SYN-14102026 --label "stage N"

# tests, lint, layers, frozen reference
python -m pytest tests -q -p no:randomly
python -m ruff check src tests tools --output-format=concise
python -m importlinter.cli lint
PYTHONPATH="src;." python -m twinlab.ingest.build_reference --check

# re-derive the gain from real respondents (live DB, never CI)
# calibrate_reaction_gain({submission_id: {item_id: value}}) -> ReactionGainFit
```

A gate run is **~5 model calls per twin** (2 H3 repeats + 2 controls + 1 H2), **serial** — one
provider slot — at roughly **60–90 s per twin**. Ten twins ≈ 12–15 minutes. Generation and twin
import cost no model calls.

**Watch for `429 ... monthly usage limit`** in the run output. It exhausted the quota mid-stage once
and silently cost a twin its verdict.

**Measuring persona legibility** (how the reactivity fix was verified, and how to verify salience):
count clause occurrences and their position in each `persona_passage`, matching against the
`CIRCUMSTANCE` bank. Reactivity went from 1–3 mentions (one at 93% through) to 4–15 (first at
8–57%).

---

## 8. CURRENT DATABASE STATE

Three synthetic batches exist. **Do not pool them.**

| prefix | n | generator | voice | gain | status |
|---|---|---|---|---|---|
| `SYN-12102026` | 10 | v6 | v1 | — | **stale.** Pre-calibration. Delete before drawing any panel. |
| `SYN-13102026` | 10 | v8 | v2 | 2.11 | superseded by the v9 batch |
| `SYN-14102026` | 10 | v9 | v3 | 2.11 | **current.** Stages 2 and 3 ran on it. |

- Panel-eligible twins: **`SYN-14102026-0000`** only (MAE 0.94, within-1 83.3%).
- **The real twin `web_e6b4a70cb63c41a1b124f22bd285116e` is no longer eligible** — its verdict
  predates the prompt change, which is the fingerprint fix behaving correctly. **Re-gate it** (~5
  calls) so the one real driver is back in play.
- `twin_quality_runs` is append-only; "latest" is the `is_latest` pointer. Nothing was deleted.
- Deleting the synthetic batches **cascades away `twin_quality_runs` and `twin_control_answers`** —
  that is where the diagnostic evidence for all four stages lives. Everything load-bearing is
  written into `docs/DECISIONS.md`, but prefer leaving the rows alone.
- `SYN-14102026-0009` has an H3 verdict from stage 3; it had none after stage 2 (quota 429).

---

## 9. THE ONE THING MOST LIKELY TO BE GOT WRONG

The temptation, at every stage of this work, has been to close the remaining gap by adjusting a
number until twins pass. **Every gap left open in §6 is open on purpose.** The gate is currently
doing its job: it rejected twins that emitted a near-constant vector, and it passed the first twin
that genuinely reproduced its driver. That behaviour is the asset. A passing rate bought by moving
`mae_max`, by re-weighting `lever_reactions` to taste, or by coaching the twin toward the
generator's answers would look like success in a session log and would be worthless in a paper.

If Route A does not get most twins through, the correct next move is to measure why and say so.
