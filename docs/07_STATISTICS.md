# 07 — Statistics

Every formula the platform computes. Metrics, shifts, the index, interactions, and the PLS-SEM
battery.

Normative. **No model produces any number in this document** (I12).

---

## 1. Two statistical layers, on two different datasets

Conflating them is the easiest serious mistake available in this project.

| | **Counterfactual layer** | **Measurement layer** |
|---|---|---|
| Question | Which policy change moves which outcome, by how much? | Do the constructs measure what they claim, and how do they relate? |
| Unit | one twin × one version code | one human respondent |
| Data | `twin_answers` | `survey_answers` |
| N | the frozen panel, K (default 20) | all screened respondents, up to 500 |
| Output | shifts, index, interactions | α, ρ_A, CR, AVE, HTMT, VIF, paths, R², f², Q², PLSpredict, fit |
| Where | Results, Dial board | Statistics |
| Engine | this document, §2–§6 | `openpls-engine`, §7–§10 |

**Statistics never reads the sweep.** The PLS-SEM model is estimated on human survey rows; the twins
are an instrument for the counterfactual question, not respondents in the measurement model. The
`arm` assignment is the experimental antecedent within the human layer.

---

## 2. Metric scoring

Six outcome metrics, from six of the nine constructs (`docs/01` §3.3–3.4).

### 2.1 Reverse code first

Exactly three items: `SAT2`, `DEP1`, and `H2_SAT2` by inheritance.

```python
reversed_value = (points + 1) - raw
```

`points` comes from **that item's own scale**. A 5-point item reverses about 6, a 7-point item about
8. Reversing every item about 8 is a silent corruption of three of the nine constructs.

### 2.2 Then mean, on the item's own scale

```python
METRICS = {
  "fairness":  (["FAIR1","FAIR2","FAIR3","FAIR4"], "extent7"),
  "clarity":   (["CLAR1","CLAR2","CLAR3"],         "agree5"),
  "happiness": (["SAT1","SAT2","SAT3"],            "agree7"),   # SAT2 reversed
  "staying":   (["CONT1","CONT2"],                 "agree5"),
  "pushback":  (["ALGO1","ALGO2","ALGO3","ALGO4"], "agree7"),
  "leaving":   (["TURN1","TURN2","TURN3"],         "agree7"),
}

def score(answers: dict[str, int], metric: str) -> float:
    ids, scale = METRICS[metric]
    pts = SCALE_POINTS[scale]
    vals = [(pts + 1 - answers[i]) if ITEMS[i].reverse_coded else answers[i] for i in ids]
    return sum(vals) / len(vals)
```

**Five-point blocks are never rescaled to seven.** `clarity` and `staying` are reported on 1–5;
`fairness`, `happiness`, `pushback` and `leaving` on 1–7. Standardisation happens at the modelling
stage, never in the display metric.

`TURN3` is `likely7`, not `agree7` — same range, different anchors, so the mean is unaffected but
the displayed anchor text is not.

### 2.3 Missing items

There are none. A twin vector that reached storage passed the output contract (I13) and has exactly
37 valid items. A vector that did not is **absent**, not partial — that twin failed for that cell.
No metric is ever computed over a subset.

---

## 3. Shifts

Baseline is the twin's **own survey answers**, so every driver is their own control.

```python
shift[m] = mean_over_twins(score(variant, m)) - mean_over_twins(score(baseline, m))
```

### 3.1 The paired-sample rule

Both means are taken over **exactly the twins that answered this cell**. A twin that failed for this
cell is excluded from **both** sides, never only from the variant side.

Computing the baseline over the full panel and the variant over the survivors would make every
failure look like an effect. This is the single most dangerous arithmetic error available in the
counterfactual layer, and `analysis/metrics.py` takes one twin-id set and uses it for both.

### 3.2 Repeats

With `runs_per_wording > 1` or multiple wordings, a twin has several vectors for one cell. Average
**within twin first**, then across twins — so a twin that was asked twice does not get double weight.

---

## 4. The index

One headline number per cell. Pushback and leaving are sign-flipped because less of each is better
for the driver.

```python
index = mean([ shift.fairness, shift.clarity, shift.happiness,
               shift.staying, -shift.pushback, -shift.leaving ])
```

Shifts are stored **signed**; the flip happens only in the index.

### 4.1 Weights

`analysis.default.yaml` carries a weight per metric, default `1.0` for all six. A weight of `0`
omits a metric. The index is then the weighted mean over non-zero weights. **The default is
unweighted and that is what the paper reports**; weights exist for sensitivity analysis and any
non-default set is recorded on the run and shown in the UI.

### 4.2 Golden fixtures — verified against real prototype output

These five reproduce the prototype's `Designs` sheet to 3 dp. They are regression tests in
`tests/test_metrics.py`, not illustrations.

| Code | fairness | clarity | happiness | staying | pushback | leaving | Index |
|---|---:|---:|---:|---:|---:|---:|---:|
| `20000` | +0.13 | 0.00 | +0.76 | +0.52 | 0.00 | −0.59 | **0.333** |
| `21000` | +0.13 | 0.00 | +1.06 | +0.61 | 0.00 | −0.91 | **0.452** |
| `22200` | +0.46 | +0.95 | +1.29 | +0.72 | 0.00 | −0.99 | **0.735** |
| `21012` | +1.01 | +0.01 | +1.38 | +1.06 | −1.72 | −0.98 | **1.027** |
| `22222` | +1.62 | +0.94 | +1.53 | +1.01 | −1.81 | −0.98 | **1.315** |

Worked, `22222`: `(1.62 + 0.94 + 1.53 + 1.01 + 1.81 + 0.98) / 6 = 7.89 / 6 = 1.315`.

A sixth value, `21122 → 1.245`, appears in the 1.0 documents from the mock. Its per-metric vector is
`(1.62, 0.60, 1.50, 0.68, −2.05, −1.02)`; it is retained as a fixture but the five above are
preferred because they came from stored output rather than a worked example.

### 4.3 Stated limitation — carry it into the paper

The index averages 5-point and 7-point shifts unweighted. It is the **display** index. Per-metric
shifts are stored so a standardised index can be computed at modelling time, and the UI never
presents the index without the six shifts beside it.

---

## 5. Interactions

For two codes A and B, the joint cell is the **elementwise maximum** of their dial vectors.

```python
def interaction(a: str, b: str, metric: str) -> Interaction | None:
    joint = "".join(str(max(int(x), int(y))) for x, y in zip(a, b))
    ra, rb, rab = (latest_completed(c) for c in (a, b, joint))
    if not all((ra, rb, rab)):
        return None                        # I17 — never impute
    extra = rab.shift[metric] - (ra.shift[metric] + rb.shift[metric])
    return Interaction(
        a=a, b=b, joint=joint, metric=metric,
        alone_a=ra.shift[metric], alone_b=rb.shift[metric],
        together=rab.shift[metric], extra=extra,
        verdict="sub-additive" if extra < 0 else
                "super-additive" if extra > 0 else "additive",
    )
```

```
extra < 0 → sub-additive     the two protections substitute for each other
extra > 0 → super-additive   they compound
extra = 0 → additive
```

**All three cells must have completed runs, on the same panel.** A missing leg returns `None` and
the UI **names the code to run** — never an estimate, never an interpolation, never
"approximately" (I17). Legs from different panels raise `PanelMismatch` (I14).

Worked: *"staying changes +0.31 and +0.09 alone, +0.22 together. The extra is −0.18, so together
they add less than the sum."*

**Sub-additivity is the contribution.** It tells a regulator which reform to mandate when only one
is affordable — a claim no small vignette study can support.

---

## 6. The two floors

Every live cell is reported against both.

```
noise floor (cell) = mean over the six metrics of |mean over twins of shift(00000)|
noise floor (twin) = mean over the six metrics of mean over twins of |shift(00000)|
demand floor       = index(SHAM) - index(00000)
```

### 6.1 Why the noise floor has two levels (RESEARCHER 2026-10-07)

It was `|index(00000)|` until 2026-10-07. That is an **absolute value of a signed mean**: the index
applies `index_sign` and averages the six metrics, so a twin moving up and a twin moving down leave
it where it started. Every statistic it gates — tests 2, 4, 5, 6 and 8 — is a **mean of absolute
values**, and by Jensen's inequality `|E[X]| <= E[|X|]`. The floor could therefore never exceed the
quantity it was judging, and every floor-judged test leaned toward `FAIL` for a reason that had
nothing to do with the twins.

On the study database this was not a small bias. Session `7a1b78a6` stored
`shifts = {clarity: 0, leaving: 0, staying: 0, fairness: 0, pushback: 0, happiness: 0}` for `00000`
and a floor of `0.000`, against which five tests were judged.

The two levels are the two functionals the tests actually compute, so each is compared with
something built the same way:

| Test | Statistic | Level |
|---|---|---|
| 2 | mean over metrics of \|mean shift\| | **cell** |
| 4 | mean happiness shift | **cell**, happiness only |
| 4 | share of twins reading it as a clear improvement | **twin**, happiness only |
| 5 | mean over metrics of mean \|A − B\| per twin | **twin** |
| 6 | mean over twins of \|with − without\| | **twin**, fairness only |
| 8 | range of mean shifts across temperatures | **cell** |

Tests 4 and 6 judge a single metric, so they take that metric's own floor: a six-metric average is
not the floor for fairness.

The **demand floor is unchanged and stays signed.** It is a directional quantity — how much further
SHAM moves the index than `00000` — and an absolute value there would discard the direction that
makes it interpretable.

**A cell whose index does not exceed the demand floor is not interpretable**, and the Analyst is
required to say so (`docs/02` §4.4). The UI shows the floor on every Results panel and marks cells
below it.

All are computed per session, from that session's panel, and never pooled across sessions. Each
twin's control answers were given once in the quality test under the session's own config
fingerprint, so a session's floors are assembled from stored answers and no session asks a control
(RESEARCHER 2026-10-05).

---

## 7. The measurement model

Estimated by `openpls-engine` (`ARCHITECTURE.md` §3.4). We specify the model, the population and
the thresholds; the engine computes. Formulas below are the published PLS-SEM conventions the
engine implements — stated here so a reader knows what each column means, not so anyone
reimplements them.

### 7.1 The population

```python
population: Literal["real", "synthetic", "both"]
screening:  Literal["strict", "none"]
```

`strict` drops a respondent who failed either attention check (`AMQ6`, `ALGO5`), completed in under
8 minutes, or straight-lined.

**Straight-lining is a dispersion rule: the standard deviation of a respondent's _raw_ battery
answers, below `0.30`.** Two things about it are load-bearing.

*Raw, meaning pre-reversal.* The prototype computed this SD **after** reverse-coding, so an all-7s
respondent had their three reversed items sitting at 1, an SD near 2.8, and passed. That rule only
ever caught straight-lining at the scale midpoint. Reading raw answers is the only ordering under
which the statistic means what its name says.

*The threshold was fixed on 2026-10-11, before any real data existed*, and it is the prototype's own
`0.30` so it can be cited as pre-specified. A rule chosen after seeing results is a researcher
degree of freedom — which is the paragraph below — so the number carries a date.

The rule is enforced in `stats/dataset.py`, not at intake. The stored `straight_liner` column is a
**fact** ("every battery answer was identical"), written by the Edge Function and
`ingest/survey_intake.py` in lockstep; the threshold is a **judgement**, and keeping it in the
analysis layer is what lets it change without an Edge Function deploy and without rewriting a
single stored row (rule 6). Both tests run: the stored flag still screens out a respondent whose
answers are no longer loadable. `analysis_runs.config.straight_line_sd_min` records which threshold
produced each analysis.

**Failing the Part 15 manipulation check (`MC1`) does not drop a respondent.** Decided 2026-09-28:
the switch is built and defaults **off**. `mc_answer` and `mc_correct` are captured on every
submission and the failure rate is reported on Fieldwork, so the decision can be revisited against
data. Turning it on **after** seeing results is a researcher degree of freedom; the analysis run
records which screening rule produced it, so the choice is always visible.

`n_cases` after screening is recorded on the run and shown on every result view. **A screening rule
chosen after seeing results is a researcher degree of freedom**; the UI records which rule produced
which analysis so the choice is visible.

### 7.2 The nine constructs as measurement model

All nine are **reflective**, each with its items from `docs/01` §3.3. `EDEP` enters as a moderator.

**`arm` enters as one single-indicator construct per non-reference arm** — `ARM_MGT1`, `ARM_CON1`,
`ARM_REP1`, with `BASE` omitted as the reference — each carrying its own dummy and its own path to
`EXPO` and `CTRL`. Six coefficients, each separately bootstrapped.

Until 2026-10-11 these were one formative `ARM` composite of three dummies. That collapses three
degrees of freedom to one: a composite yields a single `ARM → EXPO` coefficient, so there was no
estimate of the form *"MGT1 raised perceived exposure by β"* — which is the reportable output of a
four-arm between-subjects experiment. A composite is the conventional treatment of a categorical
**control** variable, not of the manipulation under test.

The arm constructs are flagged formative, so reliability, AVE and discriminant validity read `na`
for them: a single indicator has a loading of 1 and an AVE of 1 by construction, and reporting
those as measurement quality would be meaningless. The three dummies are mutually exclusive with
the reference omitted, so they sum to ≤ 1, never to 1 — the block is estimable and inner VIF stays
modest. A fourth dummy would be a rank deficiency.

### 7.3 Mediation structure, and the robustness check

The reported model imposes **full mediation**: justice perceptions reach the behavioural intentions
only through satisfaction, so every arm effect on an intention is entirely indirect. That is the
researcher's decision, recorded in `docs/DECISIONS.md`.

A second variant, `partial`, adds exactly three edges — `FAIR → VOIC`, `FAIR → LOYA`,
`CTRL → VOIC` — and nothing else. It exists because `FAIR → VOIC` is the central claim of the
algoactivism literature and its absence is the first thing a reviewer asks about, and because the
check costs **no extra data**: same matrix, same engine call.

```python
build_model_spec(variant="full")     # the reported model, and the default
build_model_spec(variant="partial")  # the robustness check, never a second headline
```

The variant is **nested** — the full model plus three edges, with nothing removed — so each added
path's own bootstrap interval is the test of that mediation restriction.

`EDEP × FAIR` and `EDEP × TRAN` are deliberately **not** added. `EDEP × SATI` was chosen over them
after the question was put twice (`docs/DECISIONS.md`); adding them here would quietly convert the
robustness check into the partial-mediation model that was declined.

The two variants produce different `ModelSpec.fingerprint()` values and `model_variant` is recorded
in `analysis_runs.config`, so a result under one can never be read as a result under the other, and
a resumed run rebuilds the model its own matrix was built for.

---

## 8. The nine analysis stages

Each persists on completion and is never recomputed on resume (`docs/01` §6.8).

### 8.1 Construct reliability and validity

Columns: `Construct · Items · Mean · SD · Cronbach α · ρ_A · Composite reliability · AVE · Status`.

| Statistic | Definition | Threshold |
|---|---|---|
| Cronbach's α | `(k/(k−1))·(1 − Σσ²ᵢ/σ²ₜ)` | ≥ 0.70 |
| ρ_A | Dijkstra–Henseler consistent reliability | ≥ 0.70 |
| Composite reliability ρ_c | `(Σλᵢ)² / [(Σλᵢ)² + Σ(1−λᵢ²)]` | ≥ 0.70, and **≤ 0.95** |
| AVE | `Σλᵢ² / k` | ≥ 0.50 |

The upper bound on ρ_c matters: above 0.95 indicates redundant items, not excellent measurement.

### 8.2 Discriminant validity

**HTMT** — the ratio of average heterotrait-heteromethod correlations to the geometric mean of the
average monotrait-heteromethod correlations, per construct pair, with bootstrap confidence
intervals.

Threshold: **< 0.90** for conceptually similar constructs, **< 0.85** strict. The decisive test is
that the **upper bound of the CI is below 1**.

**Fornell–Larcker** — `√AVE` on the diagonal must exceed every off-diagonal correlation in its row
and column.

Both are reported. HTMT is the primary criterion; Fornell–Larcker is reported because reviewers
expect it.

### 8.3 Collinearity

**Inner VIF** per predictor→criterion relation; **outer VIF** per indicator. `VIF = 1/(1 − R²ᵢ)`.

Threshold: **< 5**, ideally **< 3**. Outer VIF above 5 on a reflective construct signals redundant
items; inner VIF above 5 makes a path coefficient uninterpretable.

### 8.4 Outer model

`Construct · Item · Loading · Status`, with bootstrap significance.

Threshold: **≥ 0.708** (so the construct explains ≥ 50% of item variance). An item loading
0.40–0.708 is **retained only if** removing it would not raise AVE or ρ_c above threshold. Below
0.40, remove.

**Any item removal is a change to the instrument.** It is recorded in `docs/DECISIONS.md` with the
loading that justified it, and it does not change `instrument.json` — the register is frozen
(I-rule: never renumber). Removal is an analysis-time exclusion list, not a re-coding.

### 8.5 Path coefficients

`Path · Original sample · Sample mean · SD · t · p · CI · Status`, from the bootstrap (§9).

Report **confidence intervals as primary**, p-values alongside. A bootstrap CI excluding zero is the
inferential claim; the p-value is a convention.

### 8.6 Indirect and total effects

**Specific indirect effects** per mediation path, and **total effects** decomposed as
`Direct · Indirect · Total`, each with CI and p.

The model is a chain — governance → algorithmic-management perceptions → justice perceptions →
behavioural intentions — so the indirect effects are where the theory lives.

### 8.7 R², f², Q²

| Statistic | Definition | Interpretation |
|---|---|---|
| R² | variance explained per endogenous construct | 0.75 substantial · 0.50 moderate · 0.25 weak *(field-dependent)* |
| Adjusted R² | penalised for predictors | report alongside |
| f² | `(R²incl − R²excl)/(1 − R²incl)` | 0.02 small · 0.15 medium · 0.35 large |
| Q² | blindfolding, `1 − ΣE/ΣO` | **> 0** = predictive relevance |

The R² bands are conventions, not laws; behavioural IS models routinely report lower and defend it.
The UI shows the band and does not colour an R² red for being small.

### 8.8 PLSpredict

Out-of-sample assessment: k-fold prediction, PLS errors against a **linear-model benchmark**.

| Outcome | Reading |
|---|---|
| `Q²predict > 0` and PLS RMSE < LM RMSE on **all** indicators | strong predictive power |
| … on **most** | medium |
| … on **a minority** | low |
| … on **none**, or `Q²predict ≤ 0` | none |

### 8.9 Model fit

`SRMR` (**< 0.08**), `d_ULS`, `d_G`, NFI, and the bootstrap-based exact-fit test where the engine
provides it.

**Report fit, do not lead with it.** PLS-SEM fit indices are contested and are not the basis on
which this model should be judged; reliability, validity and predictive relevance are.

---

## 9. Bootstrap

```python
bootstrap_samples: int     # default 5000, hard floor 30, warn below 1000
seed: int                  # stored; the resample is reproducible
```

- **Default 5,000**, the published convention.
- **Warn below 1,000** — CIs are unstable and should not be reported.
- **Hard floor 30**, enforced by `analysis_bootstrap_floor`. This is the prototype's UI minimum,
  kept for compatibility, and it exists so a researcher can smoke-test the pipeline quickly. It is
  not a reportable setting and the UI says so.
- Long bootstraps are staged and resumable; the seed makes a resumed run identical to an
  uninterrupted one.

`bootstrap_samples`, `seed`, `n_cases`, `screening` and `engine_version` appear on **every** result
view, because the paper must state all five.

---

## 10. Validating the engine

We cite someone else's validation; we still prove our wiring is correct.

`stats/golden.py` holds a fixed reference dataset with stored expected values for every statistic in
§8, and `tests/test_stats_golden.py` asserts agreement to **|Δ| < 0.001**. It runs in CI.

Two things it catches that the engine's own validation cannot: a construct wired to the wrong items,
and a reverse-coded item not reversed before estimation. Both produce plausible numbers.

**Until that test passes, no Statistics number is reportable**, and the UI carries an
`UNVALIDATED` banner driven by a config flag.

---

## 11. Export

Replaces the prototype's Google Sheet. CSV, XLSX, or raw JSON.

**One row per respondent.** Columns:

```
submission_id · data_type · city · service · arm · female · tenure_months
· <37 battery items> · <2 attention items> · <16 H2 items> · <18 H3 items>
· <9 construct means> · screening flags · completion_seconds · language
```

Two header rows: item ids, then **`scale_id` and `points` per column**. The prototype's export
claimed every item was 1–7; three constructs are 1–5 (`docs/01` §3.2). Carrying the scale in the
file makes it impossible for a downstream tool to repeat the error.

A `legacy_scale` column marks any value imported from the prototype on the old 1–7 scale. **Those
rows are excluded by default** and pooling them requires an explicit override.

Construct means are exported **pre-computed in Python** so a downstream tool cannot re-derive them
with different reverse-coding (I12).
