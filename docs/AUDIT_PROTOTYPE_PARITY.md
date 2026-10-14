# Audit — Apps Script prototype (build 48, 2026-09-25) vs the Python build

Scope: every statistical path and every validity test. Read against `Researcher Work Bench.docx`
(the single-file `.gs` prototype, 3,657 lines).

Verdict in one line: **the Python build is more rigorous than the prototype almost everywhere, and
three of the prototype's statistics are biased in ways that mean its numbers must not be reported.**
The items below are the exceptions — where Python diverged in a way that needs a researcher
decision, where a prototype behaviour was dropped without a recorded reason, and the one place I
would change Python to match the prototype.

Sections: **A** needs a decision · **B** prototype numbers to discard · **C** validity-test logic ·
**D** dropped features · **E** verified parity.

---

## A. Needs a researcher decision

### A1 — The structural model is not the prototype's, in three places — **ADDRESSED 2026-10-11**

> Resolved as a declared robustness check, not a model change: `build_model_spec(variant="partial")`
> adds exactly `FAIR → VOIC`, `FAIR → LOYA` and `CTRL → VOIC`, nested, with its own fingerprint and a
> dropdown on the Statistics tab. Full mediation stays the reported model. `EDEP × FAIR` / `EDEP × TRAN`
> deliberately not added — the researcher declined that pairing, and a test pins their absence.
> The `EXPO → CTRL` question below is **still open** and is a researcher decision.
> `docs/DECISIONS.md` (2026-10-11); `tests/test_m12_arms_and_variant.py`.

| | Prototype `SEM_MODEL` | Python `stats/spec.py` |
|---|---|---|
| Antecedent | none — `arm` never enters the SEM | `ARM -> EXPO, CTRL` |
| AM perceptions | `EXPO -> CTRL`, `EXPO -> FAIR`, `EXPO -> TRAN` | `EXPO, CTRL -> FAIR, TRAN`; **no `EXPO -> CTRL`** |
| Satisfaction | `CTRL, FAIR, TRAN -> SATI` | `FAIR, TRAN -> SATI` |
| Intentions | `SATI, FAIR, EDEP -> LOYA`; `SATI, CTRL, FAIR, EDEP -> VOIC`; `SATI, EDEP -> EXIT` | `SATI, EDEP, EDEP x SATI -> LOYA, VOIC, EXIT` |

Two consequences worth stating in the paper rather than discovering in review:

1. **Python imposes full mediation.** The prototype had direct `FAIR -> VOIC`, `FAIR -> LOYA` and
   `CTRL -> VOIC`. `docs/DECISIONS.md` records that the researcher chose full mediation
   deliberately and declined the partial-mediation alternative, so this is not a defect — but
   `FAIR -> VOIC` is the central claim of the algoactivism literature, and its absence is the first
   thing a reviewer will ask about. The partial-mediation model costs **zero** extra data (same
   matrix, same engine call) and `ModelSpec.fingerprint()` already makes the two unmistakable for
   each other. Recommend running it as a declared robustness check.
2. **`EXPO` and `CTRL` are modelled as parallel with no relation to each other.** They will be
   substantially correlated in the data, both are endogenous to `ARM`, and neither predicts the
   other. The prototype's `EXPO -> CTRL` was at least a claim. Worth confirming the omission is
   intended rather than inherited.

### A2 — `ARM` as one Mode B composite collapses three degrees of freedom to one — **FIXED 2026-10-11**

> Now `ARM_MGT1` / `ARM_CON1` / `ARM_REP1`, one dummy each, `BASE` the reference, six paths where there
> were two. On the golden fixture `R²(CTRL)` rose **0.0101 → 0.0412 (4.1×)** — the composite had been
> losing most of the arm signal — and `ARM_MGT1 → CTRL` (+0.188) now separates from `ARM_REP1 → CTRL`
> (+0.019), a tenfold difference previously averaged into one coefficient. Every Cronbach's alpha is
> byte-identical; AVE/ρ_A/loadings moved ≤ 0.0051 on `CTRL` only, which is what the path weighting
> scheme predicts. `GOLDEN_FINGERPRINT` 7c7fd73a12a4ec48 → 081db1a0f8a2a2e0, digest unchanged.
> MGA deferred as a complement, not a substitute. `docs/DECISIONS.md` (2026-10-11).

`stats/spec.py` builds `ARM` as a single formative block of three dummies (`MGT1`, `CON1`, `REP1`,
with `BASE` omitted). `docs/DECISIONS.md` calls this "the conventional treatment of a categorical
antecedent" — which is true for a **control** variable. Here it is the experimental manipulation.

The composite yields **one** `ARM -> EXPO` coefficient and **one** `ARM -> CTRL` coefficient. There
is no estimate of the form "MGT1 raised perceived fairness by *x*, CON1 by *y*" — a four-arm
between-subjects experiment's whole reportable output. Recovering it from outer weights x path
coefficient is not how any IS paper reports an arm effect.

Two alternatives, both standard:

- three single-indicator exogenous constructs, one per dummy, each with its own path — three
  directly interpretable, bootstrappable arm contrasts, no composite and no Mode B;
- keep `ARM` and add a multi-group analysis across arms.

This is the highest-stakes open item in the measurement layer, because nothing in the output will
*look* wrong — you will simply have no per-arm number to report.

### A3 — Shift baselines now carry the twin's reconstruction bias, and nothing subtracts it

The prototype's shift was `twin(code) - twin(00000)`: twin-vs-twin, so the model's own baseline bias
cancelled. Python's is `twin(code) - human(survey)`, decided 2026-10-07, and that decision is
correct — the 2026-10-07 `DECISIONS.md` entry shows the prototype-style control was *manufactured*
by an anchoring cue (`00000` returned the stored baseline on 37/37 items for 6 of 7 twins, floor
exactly `0.000`).

The residual: every reported shift is now **treatment effect + reconstruction bias**. The bias is
measured — it is exactly `shift(00000)` — and both floors use it when **judging** a cell, but no
reported shift is corrected by it.

Recommend a secondary per-metric column `shift(code) - shift(00000)`. It needs no new model call,
every input is already stored, and it reproduces the prototype's twin-vs-twin contrast exactly — so
the two baseline definitions become a sensitivity analysis instead of a fork.

### A4 — `docs/07` §4.2's golden fixtures do not validate the baseline choice

§4.2 says the five fixtures "reproduce the prototype's `Designs` sheet to 3 dp". They do — but only
because in the prototype's **mock** mode `mockTwinAnswer` at `00000` returns the driver's own answer
for every non-hidden item (`shift = 0`, `base = known[code]`, noise ±0.45 then rounded). The two
baseline definitions coincide **by construction in the mock** and diverge under any live model.

So those fixtures pin the arithmetic of `compute_shifts` / `compute_index` and nothing about §3's
baseline definition. Add one sentence to §4.2 saying so, before someone cites them as
cross-validation of the baseline.

### A5 — Straight-lining: the prototype's rule was broken; Python's is correct but narrow — **FIXED 2026-10-11**

> `STRAIGHT_LINE_SD_MIN = 0.30` on **raw** battery answers, enforced in `stats/dataset.py` rather than at
> intake: the stored `straight_liner` column is a fact, the threshold is a judgement, and keeping it in
> the analysis layer means it can change without an Edge Function deploy and without rewriting evidence
> (rule 6). Neither intake copy was touched — the `rows.mjs` contract test passing untouched is the
> evidence. Recorded per analysis in `analysis_runs.config.straight_line_sd_min`. Threshold fixed before
> any real data existed. Golden fixture's least-varied respondent sits at SD 0.74, 2.5× the threshold.

- **Prototype** (`screenCases_`): SD < 0.3 across all 37 items — computed **after** `statsData`
  reverse-codes. An all-7s respondent has their reversed items sitting at 1, SD about 2.8, and
  **passes**. The rule only ever caught midpoint straight-lining.
- **Python** (`_straight_lining`): `len(set(raw values)) == 1` on **raw** values. The ordering is
  right and all-7s is caught — but "36 sevens and one six" passes.

Keep the raw-value ordering and widen the rule: raw SD below a stated threshold, or "at least 95% of
battery items share one value". **Fix the number in `docs/DECISIONS.md` before looking at data** —
`docs/07` §7.1 already warns that a screening rule chosen after seeing results is a researcher
degree of freedom, and this is one.

### A6 — The synthetic generator cannot exercise the study's headline claim — **FIXED 2026-10-11**

> `GeneratorSpec.lever_effects` (the prototype's 5×9 matrix, signed), `second_step_factor = 1.6` and
> `lever_synergy = 0.3`, all from `config/generator.default.yaml`. `reaction_shift` now returns a signed
> per-construct dict, and the `sign *` multiplication left both `_item_target` and `_H3_SUFFIX` — leaving
> it would have double-applied the sign and silently inverted pushback, leaving and control.
> `GENERATOR_VERSION = "v5"`. `tests/test_m9_generator_levers.py` now exhibits sub-additivity from the
> generator's own ground truth, through `analysis/interactions.py`, which no fixture could do before.

This is the largest un-ported piece of logic, and it matters because it is what the interaction
machinery is tested against.

| | Prototype | Python `reaction_shift` |
|---|---|---|
| Lever -> construct | a 5 x 9 matrix (`GEN_LEVER`): pay moves `SATI +0.5`, `LOYA +0.4`, `EXIT -0.4`, `FAIR +0.1`; management moves `FAIR +0.7`, `VOIC -0.4`, `CTRL -0.2`, `SATI +0.2`; and so on | **one scalar** per version code, applied to every construct, direction from `index_sign` alone |
| Second dial step | `x 1.6`, diminishing | `x 2`, linear |
| Interactions | `MGT x REP -> VOIC -0.3` (complement); `PAY x CON -> LOYA -0.15` (substitute) | **none** |

Consequence: on synthetic data **every interaction is exactly additive by construction**. `docs/07`
§5's claim — "sub-additivity is the contribution… a claim no small vignette study can support" — has
no fixture that could ever exhibit sub-additivity, so `analysis/interactions.py` is untested against
a known truth. Lever specificity is also unrecoverable: a pay rise moves `clarity` exactly as much
as it moves `happiness`, so no PLS path estimated on synthetic data corresponds to anything.

Recommend porting `GEN_LEVER`, the 1.6 second-step and both interaction terms into
`generator/synthetic.py`, with the matrix living in `config/generator.default.yaml`. **Highest-value
remaining port.**

### A7 — The H3 gate got much harder; its thresholds did not move

`mae_max = 1.0` and `pct_within_1_min = 0.80` are identical in both builds. The instrument is not:

- prototype: 16 **hidden baseline** items — "recall what your driver said about things you were not
  told";
- Python: 18 items spanning **six unseen policy worlds** — "reproduce your driver's *mapping* from
  stimulus to response".

`docs/08` §2.3's argument for the change is right. But a 1.0 MAE bar on six counterfactual worlds is
a different bar from a 1.0 MAE bar on recall, so expect retention far below the prototype's — which
drives panel size and the roughly 9,000-call quality budget.

**Now measurable (A6 landed 2026-10-11).** This was blocked while every synthetic human moved all
six constructs by one shared scalar, which made the H3 gate trivially passable. Under `v5` the six
H3 versions separate by lever, so a `v5` batch can be scored against the gate to get a real
retention figure. **Still open**, and the threshold is a researcher decision: measure first, then
decide, and record the number before it is applied.

---

## B. Prototype statistics that must not reach the paper

Each is a *bias*, not a rounding difference, and each is correct in Python because
`stats/plssem.py` delegates to `openpls-engine` rather than reimplementing.

**B1 — CR and AVE use item-total correlations as loading proxies.** The prototype's own comment:
"approximated by the item to total correlation". The item sits inside its own total, so every
loading carries a spurious part-whole component. **CR and AVE are biased upward**, worst for short
blocks — `LOYA` (k=2), `EDEP` (k=2), `TRAN` (k=3). Any alpha/CR/AVE in the 1.0 drafts is optimistic.

**B2 — Wrong inner weighting scheme.** The comment says "path weighting scheme simplified to
correlation weights" — that is the **factor/centroid** scheme, not path. Different estimates from
SmartPLS and from the engine, which both default to path. Python uses `Scheme.PATH`.

**B3 — PLSpredict is not PLSpredict.** It predicts from `blockMean[p][i]`, a standardised block
average of the **test** case, instead of applying the **training** outer weights to the test case's
indicators. A different, weaker predictor — the prototype's `q2predict` and `beats_lm` are not
comparable with anything published.

**B4 — Missing items enter item totals as zero.** `reliability()` builds totals with
`(c.items[code] || 0)`. Items are 1–7, so a missing item contributes **0**: inflates total variance,
deflates alpha on any incomplete case. Python deletes casewise.

**B5 — Asymmetric bootstrap percentile bounds.** `lo = sorted[floor(0.025*n)]`,
`hi = sorted[floor(0.975*(n-1))]` — two bounds from two conventions, and a plain percentile interval
where SmartPLS reports BCa. Minor, but not the published quantity.

**B6 — No bootstrap floor.** `stat()` only requires `a.length >= 3`, so **`t` and `p` are printed
off three resamples**. Python has `BOOTSTRAP_FLOOR = 30` as both a code raise and a database
constraint, plus a sub-1,000 warning.

**B7 — Undefined correlation reported as zero.** `cor_` / `corr_` return `0` or `''` when a side has
no variance, so a twin that answered all six H3 versions identically looks like a measured null.
Python's `pearson_r` returns `None`, and `docs/08` §3.3 names exactly this failure.

Minor and benign: the prototype's `pnorm_` (Zelen–Severo) applied to a bootstrap-SE *t* ratio is the
normal approximation rather than *t* with df = samples − 1 — the same shortcut SmartPLS takes. Its
Q-squared blindfolding (D = 7, mean replacement, cross-validated redundancy) is methodologically
sound.

---

## C. Validity-test logic

### C1 — Test 1, wrong person
Prototype: `PASS iff mae_other > mae_own * 1.25` — a **ratio**, no interval, no `n` guard, stranger
drawn as `sample[(i+1) % n]` (a valid derangement for n >= 2, but pairs a twin with itself at n = 1).
Python: paired gap in **scale points**, `PASS` requires >= 0.5 **and** a *t*-based CI excluding zero,
a structurally guaranteed derangement, plus `between_person_distance` reported so the fixed 0.5 can
be read against how far apart the drivers actually are. **Python strictly better; do not report the
ratio rule as a prior result.**

### C2 — Test 3, simple guesses: the prototype leaks the answer into the predictor
`shift[arm|code]` is built over **all** kept twins **including the one being predicted**, so "group
average shift" partly contains that driver's own shift. Python's `_group_shift` excludes the twin's
own driver explicitly, with a comment saying why.

Direction of the prototype's error: it made the naive predictor *stronger*, so prototype test 3 was
**harder** on the twins than it should have been — the safe direction, but the numbers are not
comparable. Separately, the prototype's `VT_TESTS` text promises **three** predictors and the code
computes **two**; Python says two and computes two.

### C3 — Tests 2 and 4 are inert in the prototype's mock mode
`vtScenarioScores_` falls back to `vtAnswer_(twin, '00000', ...)` when not live — it returns the
baseline, so "movement about 0" reads as a `PASS`. The `spec.live && mode !== 'live'` guard in
`runValidityTest` does block the path, so this is dead code rather than a live defect — but
**discard any mock-mode PASS for test 2 or 4 from a prototype run.** Python's test 2 refuses with
`INCONCLUSIVE` when `SHAM` is absent; test 4 requires a Checker-passed stimulus.

### C4 — Test 6, ablation: the prototype measured the wrong thing
It compares `|twin_with - truth|` against `|twin_without - truth|` on the `FAIR` items — **but the
`FAIR` items are not hidden**, so the comparison is "can it copy" versus "can it guess", and the two
calls differ by call-to-call variance alone with nothing to subtract that against.

Python compares `|with - without|` against `max(noise floor, same-persona retest)`, added the retest
control the prototype lacked entirely, and has **no `FAIL` verdict** — which is the right shape: the
question is sensitivity to the ablation, not accuracy. **Python correct.**

### C5 — Test 5, order swap: the prototype never reversed the order
Despite the name, `vtAnswer_(t,'00011','A',1)` vs `vtAnswer_(t,'00011','B',2)` changes the **wording
and the run index** and never touches dial order. Python genuinely runs two presentations
(`reverse_order=True, wording="A"`, then `reverse_order=False, wording="B"`).

Residual in Python: it still reports **one** combined difference, so a `FAIL` cannot be attributed to
order versus wording. A third round (order-reversed, wording A) would separate them at a cost of N
more calls — worth it only if the test fails.

### C6 — Test 8, temperature
Prototype: `max - min` of construct scores across 0 / 0.5 / 1, `PASS` if `< 0.6` — a bare literal.
Python compares the spread to the **measured** `00000` floor and derives a recommendation (the lowest
temperature at which between-twin index SD is still above zero), which the prototype never did and
which is the actual point of the test. **Python materially better.**

### C7 — The one place to change Python: `pearson_r` admitted n = 2 — **FIXED 2026-10-11**

`validity/quality.py::pearson_r` accepted `n >= 2`. With two points, `r` is **exactly ±1** whenever
both sides vary. So a twin that happened to have only two scorable H3 items for an outcome got
`r = 1.00` written into `twin_quality_runs.correlations` as evidence of ordering fidelity — and
`h3_correlations` passed `len(paired) >= 2` straight through. The prototype's `corr_` guarded
`n < 3`.

Fixed: `R_MIN_POINTS = 3` in `validity/quality.py`, with `h3_correlations`'s duplicate copy of the
floor deleted so the rule has one home. Test 7 (`second_model`) inherits it and now reports `CHECK`
with "the correlation is undefined" on a two-twin panel instead of `PASS` on an `r` of 1.00.
Recorded in `docs/DECISIONS.md` (2026-10-11); pinned by
`test_pearson_r_refuses_two_points_because_r_is_plus_or_minus_one_by_construction`. No stored row
is rewritten (rule 6).

---

## D. Prototype behaviour with no Python equivalent

**D1 — `suggestDesigns`** (test single dials first, combine the best two, then step up the best so
far). **Correct to drop.** Adaptive design selection off an observed index is exactly the researcher
degree of freedom `CLAUDE.md` rule 9 guards against, and the Python build sweeps the odometer.
Record it in `DECISIONS.md` as a deliberate removal, so it does not read as an omission.

**D2 — per-block `reasons`** (nine short rationales per answer vector). Dropped for token cost,
documented in `models/twin.py`. Consequence: the prototype's test-4 detail says "read some reasons in
the Runs tab", and that qualitative trail for *why* a twin welcomed a contradiction is gone — test 4
is now purely the happiness number. Cheap partial restore: ask for one rationale **on the probe round
only**. Test 4 is 1 call/twin, so it never multiplies by 243.

---

## E. Verified parity — no action

- **Index formula.** Prototype `(w*FAIR + w*TRAN + w*SATI + w*LOYA - w*VOIC - w*EXIT) / sum(w)` is
  identical to Python `compute_index` (weighted mean, signs from frozen `constructs.index_sign`).
  Python additionally refuses an all-zero weight set.
- **Lever order and arm codes.** `pay, conditions, contracts, management, representation` maps to
  `L1`–`L5`; `BASE 00000 / MGT1 00010 / CON1 01000 / REP1 00001` identical in `arms.json`.
- **Reverse coding about the item's own scale.** Both correct; Python reads it per item from the
  register in three separate places (`dataset.reverse_if_needed`, `metrics.score`,
  `export.construct_mean`) and documents why.
- **Paired-sample rule.** One twin-id set used for both sides of a shift. Prototype
  `summariseFromSheet_` achieves it by only emitting twins present in `base`; Python states it as
  the intersection and names it the single most dangerous arithmetic error available.
- **Repeats averaged within twin first.** Prototype averages a twin's runs before differencing;
  Python's `average_within_twin` does the same and says why.
- **Quality-gate conjunction.** `mae <= max AND pct_within_1 >= min`, both builds, never either/or.
- **Elementwise-max joint cell for interactions.** Prototype's `suggestDesigns` combines with
  `Math.max`; `orchestrator.odometer.combine` is the same rule. Python additionally refuses a
  dominated pair, where `extra` collapses to `-shift(a)` — an artefact the prototype would have
  reported as a measured interaction.
- **Speeder threshold** 480 s, both builds (Python as a generated SQL column).
- **Attention checks never enter the measurement model.** Python filters on the `attention_check`
  flag rather than by item id, so a future attention item is excluded automatically.
- **CSV export.** `stats/export.py` carries the nine construct means plus a second header row naming
  each construct's scale points — better than the prototype's `statsExport`, which implied 1–7
  throughout.
- **Fieldwork strata.** `city | service` arm balance present in `services/surveys.py`, matching the
  prototype's `fieldwork()` / `getAssignment`.
- **Output contract.** Prototype `checkAnswer` plus a whole-vector re-roll on failure; Python's
  `agents/contract.py` validates per-item ranges from the register, returns every defect at once,
  and merges attempt 1's valid items so the repair adds no variance to the 35 that were already
  right. Strictly stronger, and it matches `CLAUDE.md`'s allowed/forbidden repair lists.

---

## Still open, carried from `DECISIONS.md` (2026-10-07)

Test 3 compares a twin's H2 answers — which never showed a baseline — against a "no-change"
predictor handed the human's **exact** baseline answer. The asymmetry predates the `show_baseline`
reversal and is unrelated to it. It is the same class of issue as C2 but in the opposite direction:
it makes the naive predictor artificially strong, so a test-3 `FAIL` is not yet attributable.
