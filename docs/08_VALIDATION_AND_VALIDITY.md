# 08 — Validation and validity

The quality gate, the two holdouts, and the eight validity tests.

Normative. **Every number here is computed in Python** (I12).

---

## 1. Three different things called "validation"

| Layer | Asks | Mechanism | Consequence of failure |
|---|---|---|---|
| **Output contract** | Did the model return 37 valid integers? | `docs/02` §5 | That twin fails for that cell |
| **Twin fidelity** | Does this twin reproduce *its own human* on unseen stimuli? | §2–§3 | The twin is **dropped** |
| **Validity tests** | Are the answers attributable to the counterfactual rather than to the model? | §4 | The **study** is in question |

They escalate. The first is engineering. The second is calibration — a twin is an instrument and an
uncalibrated instrument's readings mean nothing. The third is the argument a reviewer will attack,
and it is why the tests are run and reported whatever they say.

---

## 2. The quality gate — H3, Part 17

The gate that decides whether a twin counts. Run per twin, independently of any sweep.

### 2.1 Procedure

1. Render the six Part 17 version codes — `12220`, `00222`, `11010`, `11211`, `02211`, `02200` —
   **through the normal pipeline**: same design agent, same Checker, same style version. Not
   specially written vignettes.
2. Show each to the twin with its persona. **No baseline is shown**, because the human had none
   either.
3. Collect 18 numbers: 6 versions × (fairness, pushback, keep).
4. Score against the human's own 18 answers from `survey_answers`.
5. Repeat `quality_runs_per_twin` times (default 3) and average, so one bad sample does not discard
   a good twin.

### 2.2 The score

```python
def score_holdout(human: dict[str,int], twin: dict[str,int], ids: list[str]) -> QualityScore:
    errs = [abs(human[i] - twin[i]) for i in ids if i in human and i in twin]
    if not errs:
        raise QualityScoreEmpty(ids)              # I15 — never a score of zero error
    mae = sum(errs) / len(errs)
    pct = sum(e <= 1 for e in errs) / len(errs)
    return QualityScore(mae=mae, pct_within_1=pct, items_n=len(errs))
```

**Keep if `mae ≤ 1.0` AND `pct_within_1 ≥ 0.80`.** Both thresholds are CONFIG and are recorded on
every quality run, so a threshold change is visible rather than silently retroactive.

### 2.3 Why H3 and not H2 gates

H3 is six *unseen stimuli* rendered through the real pipeline. H2 is one scenario the human saw
once. A twin that reproduces its human across six different policy worlds has demonstrated
something H2 cannot: that the *mapping from stimulus to response* transfers, not just the level.

### 2.4 Dropped twins are dropped, not tuned

A twin below threshold is excluded from the panel and from every cell. It is not re-prompted, not
re-personaed, and not given a second model. Tuning a twin until it passes its own validation test is
circular.

Typical reported outcome: *"17 of 20 twins kept (error 1.0 or less, 80 per cent within 1 point)."*

**Attrition is a stated limitation.** A dropped twin is excluded from all cells rather than flagged
per cell, which keeps N constant across the grid at the cost of some data
(`ARCHITECTURE.md` §10.4).

### 2.5 Propagation

Writing a `twin_quality_runs` row demotes the previous `is_latest` in the same transaction, so every
surface reading quality — the Twins list, the quality page, the panel selector, the analyst's
`twins_n` — reads the new number with no cache to invalidate.

**A quality re-run after a panel is drawn does not retroactively change that panel** (I14). The
session keeps the twins it froze; the new score applies to the next session. The UI flags a session
whose panel contains a twin that has since been dropped.

---

## 3. H2 validation — Part 16, per arm

The second validation set. **It does not gate.**

### 3.1 Procedure

Each human was assigned one of four arms and re-answered 16 outcome items after seeing that arm's
story (`docs/01` §5). To validate a twin on H2:

1. Look up **its own driver's arm**.
2. Render that arm's version code through the normal pipeline.
3. Show it to the twin with its persona, no baseline.
4. Collect the 16 mirrored answers; score MAE and % within 1 against the human's.

**Showing a twin a different arm than its human saw is a bug, not a variation.**
`twin_quality_runs.arm` exists so it is checkable after the fact, and the Validation table's *Arm
seen* column is how it surfaces.

### 3.2 `BASE` is the human noise floor

A quarter of respondents were shown *no change* and re-answered anyway. Their H2−baseline
difference is **human response instability** — the direct analogue of the twin's `00000` noise
floor, measured on real people.

This is a genuinely useful number and should be reported: it tells a reviewer how much movement is
expected from re-asking alone, in humans, in this instrument.

### 3.3 Correlations

Beyond MAE, the Validation tab reports whether twin and driver **move together** across the six H3
versions: Pearson `r` for fairness, pushback and staying, per twin.

MAE says the twin is close; `r` says the twin's ordering of the six worlds matches its human's. A
twin can have low MAE and near-zero `r` by predicting everyone's mean — which is exactly what
validity test 3 exists to rule out.

---

## 4. The eight validity tests

Each challenges whether twin responses are attributable to the intended driver-specific
counterfactual rather than to generic model behaviour.

**Every completed test appends a `validity_results` row and never replaces one.** Results double as
the log. A test run on zero twins is recorded `INCONCLUSIVE`, never `PASS` (I15) — the prototype
recorded live-mode `PASS` verdicts on `twins = 0`, and the DDL now makes that impossible.

Cost matters: at one concurrent request (`ARCHITECTURE.md` §7.1), a test needing fresh twin calls is
not free. Three of the eight need **no new calls at all**.

| # | Test | New LLM calls | Calls at N=20 |
|---|---|---|---:|
| 1 | Wrong person | **none** | 0 |
| 2 | Placebo change | yes | N |
| 3 | Beating simple guesses | **none** | 0 |
| 4 | Impossible version | yes | N |
| 5 | Order and wording swap | yes | 2N |
| 6 | Leave out the fairness items | yes | N |
| 7 | A second AI model | yes | N |
| 8 | Temperature sweep | yes | 3N |

### Test 1 — Wrong person

**Is a twin really about its own driver?**

Score each sampled twin's **existing H2 answer vector** against its own driver's 16 H2 answers, and
against a different, randomly paired driver's. Errors should be materially lower for the correct
person.

```
statistic:  mae_own, mae_other, gap = mae_other − mae_own
            paired across twins; report the mean gap and its CI
pass:       gap ≥ 0.5 points AND the paired CI excludes 0
check:      gap > 0 but CI includes 0
fail:       gap ≤ 0
```

**This is the most important of the eight**, because it is the one that distinguishes "a twin" from
"a plausible gig-driver chatbot". It needs **no new model calls** — it re-scores stored vectors —
so it should be run early and often.

> **Changed in 2.0.** The prototype scored this on a 16-item holdout carved out of the core battery.
> That holdout was dropped so the persona stays lossless (`docs/DECISIONS.md`), and the test
> re-bases onto the H2 block — also 16 items, and the same thing the legacy `post_mae` column
> already scored.

### Test 2 — Placebo change

**Do twins welcome any change at all?**

Show `SHAM` — five ordinary paragraphs describing what Uber already does. Measure movement from
baseline.

```
statistic:  mean |shift| across the six metrics; share of twins moving > 0.5
pass:       mean |shift| ≤ the 00000 noise floor
check:      above the noise floor but below half the median live-cell shift
fail:       comparable to a live cell
```

Needs a live model — a mock twin does not read the scenario. This test **is** the demand-
characteristic floor (`docs/07` §6), measured deliberately rather than inferred.

### Test 3 — Beating simple guesses

**Do twins beat ordinary statistics?**

Compare twin H2 error against two naive predictors on the same items:

1. **No change** — predict the human's own baseline, unchanged.
2. **Group average shift** — predict baseline plus the mean shift of all other respondents in the
   same arm.

```
statistic:  mae_twin, mae_nochange, mae_groupshift
pass:       mae_twin < both
check:      beats one
fail:       beats neither
```

No new calls. **A twin that cannot beat "nothing changed" is not adding information**, whatever its
absolute MAE looks like — and a low MAE achieved by predicting no movement is exactly the failure
mode §3.3 warns about.

### Test 4 — Impossible version

**Do twins notice a contradiction?**

Construct a deliberately self-contradictory stimulus — a guaranteed minimum wage *and* a pay cut for
the same work — and show it.

```
statistic:  mean shift in happiness; share of twins treating it as a clear improvement
pass:       happiness does not rise materially; < 25% treat it as an improvement
fail:       it reads as an ordinary improvement
```

Needs a live model. **The contradictory spec bypasses the lookup and the Checker by construction**,
so it is built by a dedicated fixture, flagged `synthetic_probe = true`, never written to `variants`,
and never reachable from the Dial board.

### Test 5 — Order and wording swap

**Are answers about the change, or about the words?**

Show the same version code twice: once with lever order reversed, once in wording variant B.

```
statistic:  mean |difference| per metric between the two presentations
pass:       ≤ the 00000 noise floor
check:      between the noise floor and half the cell's own shift
fail:       comparable to the cell's own shift
```

Costs `2N` calls. A failure here means paragraph position or phrasing is a confound, which would
undermine every lever comparison — and is why lever order is randomised per round in the first place
(`docs/03` §8).

### Test 6 — Leave out the fairness items

**Does the twin use its memory, or a stock answer?**

Re-run the twin with the fairness items removed from its persona. Its fairness response should be
sensitive to their removal.

```
statistic:  |fairness_with − fairness_without|
pass:       materially different — the twin was using its own history
check:      barely different — possibly a stock response
```

Needs a live model and an **ablated persona**. That persona violates the losslessness of I6 by
design: it is built by a test fixture, flagged `ablated = true`, never hashed into `twins`, and
never used in a study run. The ablation is the experiment.

### Test 7 — A second AI model

**Is the finding about the drivers or the model?**

Run a sample of twins on a different Ollama Cloud model, same cell, same personas.

```
statistic:  correlation of per-twin index between models; mean |difference| per metric
pass:       r ≥ 0.7 and the sign of every metric shift agrees
check:      signs agree but r is lower
fail:       any metric's sign flips
```

**A sign flip is the failure that matters.** Different magnitudes across models are expected;
different *directions* mean the finding is a property of one model.

Record both model names on the result. Ollama Cloud's model list is the pool
(`ARCHITECTURE.md` §3.3).

### Test 8 — Temperature sweep

**How much is chance?**

Run the same twins on the same cell at three temperatures — `0.0`, `0.5`, `1.0`.

```
statistic:  per-metric spread across temperatures; per-twin index SD
pass:       spread ≤ the 00000 noise floor
report:     always — this test SETS the twin temperature
```

**Run this before the main study and set the twin temperature from its result** (`docs/02` §7.3).
Do not pick a temperature from intuition; the prototype used `1.0` with no evidence, the
highest-variance option available.

Lower is not automatically better. A twin at `0.0` may collapse to modal answers and lose the
between-twin variance the design depends on. The sweep shows where the knee is, and the chosen value
is recorded on every subsequent run.

---

## 5. Verdicts

Four, and they render as pills:

| Verdict | Meaning |
|---|---|
| `PASS` | The stated criterion was met. |
| `CHECK` | Directionally right, but weak or ambiguous. Report it; do not lean on it. |
| `FAIL` | The criterion was not met. Report it. |
| `INCONCLUSIVE` | The test could not run — most often `twins_n = 0`. **Not a pass.** |

Each row also stores the statistics, the model, the mode, the temperature, the config version and a
one-line `detail` explaining what the test measures, so the table is readable without this document.

---

## 6. Reporting

### 6.1 Report everything, including failures

All eight run on the final dataset and all eight appear in the paper, whatever they say. A validity
section reporting only passes is not a validity section. A `FAIL` on test 5 or 7 is a finding about
the method and belongs in the limitations; a `FAIL` on test 1 or 3 is a finding about whether there
is a study.

### 6.2 Synthetic data proves nothing

Wherever the tested set includes synthetic twins or mock-model output, the UI shows:

> The generator and the mock twin share the same built-in reaction rules, so validation on synthetic
> data always looks good. **It tests the machinery, not whether twins are valid.**

This appears on Validation, on Validity tests and on the Generator. It is not a disclaimer to be
dismissed — a green board on synthetic data is the expected result and means nothing.

### 6.3 The mapping to the paper

The Research Model page's *How this ties the validation together* table
(`docs/06` §8) maps each technique to what it assesses and where it is used:

| Technique | Assesses |
|---|---|
| H3 holdout (quality gate) | Twin fidelity on unseen stimuli — the instrument's calibration |
| H2 holdout, per arm | Fidelity on the stimulus the human actually saw |
| `BASE` arm | Human response instability — the floor for any re-ask |
| `00000` control | Twin noise floor |
| `SHAM` control | Demand characteristics |
| Test 1 wrong person | Person-specificity — that twins are about *their* driver |
| Test 2 placebo | That change-shaped text alone does not move outcomes |
| Test 3 simple guesses | That twins add information over naive prediction |
| Test 4 impossible version | That twins read the stimulus rather than pattern-matching approval |
| Test 5 order and wording | That effects are about the change, not the presentation |
| Test 6 ablation | That twins use their own history |
| Test 7 second model | That findings are not an artefact of one model |
| Test 8 temperature | Sampling variance, and the basis for the chosen setting |
