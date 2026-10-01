---
title: "Twin Lab — the research model, explained"
project: "Digital Platform Algorithmic Management: attrition and voice of gig workers in India"
audience: "anyone who needs to understand why this exists and how it produces its numbers"
status: orientation document — non-normative
date: 2026-09-27
---

# Twin Lab — the research model, explained

This is the **why** document. It is not the specification. `ARCHITECTURE.md` and `docs/01`–`docs/11`
are normative; where they state a number or an order, they win. This document exists so that a
reader — a co-author, a reviewer, a research assistant, a future you — can read one file and
understand what the study is asking, why it is built the way it is, what each data file is for, and
how a driver's survey answer eventually becomes a row in a results table.

Read it top to bottom. It moves from the research question, to the design that answers it, to the
machinery, to the stage-by-stage walkthrough, to the file inventory, to the limits.

---

## Part I — The research problem

### 1. The question

Gig platforms in India manage drivers through software rather than through supervisors. Allocation,
pricing, ratings, incentives and deactivation are algorithmic. The worker experiences this as a
system that issues instructions and consequences without a person to argue with.

The consequences we care about are the classic organisational-behaviour outcomes, transposed onto
a workforce that has no employer in the legal sense:

- **Fairness** — does the driver experience the system as just?
- **Clarity** — does the driver understand the rules they are being held to?
- **Happiness** — job satisfaction.
- **Staying** — continuance intention.
- **Pushback** — workarounds, gaming, informal resistance (algorithmic "voice" expressed sideways).
- **Leaving** — turnover intention.

The question is not *"are drivers unhappy?"* — that is well established. The question is
**which specific changes to platform policy move which specific outcome, and by how much, and do
those changes add up or substitute for each other?**

That is a causal question about a counterfactual. It requires showing the same worker a world that
does not exist, which is the thing field research cannot do.

### 2. Why this cannot be a normal experiment

Three walls:

1. **You cannot randomise Uber's policy.** No platform will let a researcher switch off the clause
   that makes safety support discretionary for half its fleet.
2. **A vignette study cannot cover the space.** There are five policy domains, each with a
   meaningful "partial" and "full" version. That is 3⁵ = **243** distinct policy worlds. A human
   respondent can absorb perhaps six before fatigue destroys the data. Our survey does show six
   (Part 17) — and that is the ceiling for humans.
3. **Within-subject counterfactuals need the same person in every cell.** Between-subjects designs
   at 243 cells need a sample no gig-worker study will ever recruit.

So the design question becomes: *can we get a full factorial response surface out of a small real
sample, without inventing the respondents?*

### 3. The answer: digital twins as a counterfactual instrument

A **digital twin** here is a language model conditioned on one real driver's survey response, so
tightly that it answers as that driver. Not a synthetic population, not a demographic simulation —
one twin per one real human, grounded in that human's own words.

The twins are not the finding. They are the **measurement instrument**, and like any instrument they
must be calibrated before their readings mean anything. The survey holds back two blocks of answers
(Parts 16 and 17) that the twin never sees. The twin is asked those questions blind, and its answers
are compared against what its human actually said. A twin that cannot reproduce its human on
held-out material is **dropped**, not corrected.

That validation step is what separates this from "we asked a chatbot to pretend to be a gig worker."

### 4. Why Fairwork, and not a treatment we invented

The treatment has to be legitimate or the paper is a simulation of nothing. So the treatments are
not designed — they are **read off an external standard**.

The **Fairwork Location-based Platform Work Principles** are five principles (Fair Pay, Fair
Conditions, Fair Contracts, Fair Management, Fair Representation), each worth two points, scored
against 33 published criteria. Uber India's own public policy documents were coded against those
criteria in a formal codebook exercise.

**Uber India scores 0 out of 10.** Thirty of the 33 criteria are unmet. Three are met
(`3.1.a`, `3.1.c`, `4.1.c`) and become the sham control (see §9).

Each unmet criterion carries a **commitment**: the concrete, specific thing Uber would have to do to
close it. Not an aspiration — a sentence like *"provide accident and injury cover at Uber's cost,
with a published sum insured, named insurer and claims route."*

This gives the study three things it could not manufacture:

- **An externally validated treatment.** We did not choose what "better pay policy" means; Fairwork's
  published criteria did.
- **A legitimate ordinal scale.** Fairwork's second point in each principle is unawardable without
  the first. So `0 → 1 → 2` is genuinely cumulative and ordered, not three arbitrary labels.
- **A baseline that is not a guess.** Uber today is `00000`, and it is `00000` because the codebook
  says so, criterion by criterion.

### 5. The version code

Five digits, one per principle, each `0`, `1` or `2`.

| Position | Lever | Fairwork principle | `1` closes | `2` closes |
|---|---|---|---|---|
| 1 | **Pay** | P1 Fair Pay | threshold 1.1 gaps | 1.1 ∪ 1.2 |
| 2 | **Conditions** | P2 Fair Conditions | 2.1 | 2.1 ∪ 2.2 |
| 3 | **Contracts** | P3 Fair Contracts | 3.1 | 3.1 ∪ 3.2 |
| 4 | **Management** | P4 Fair Management | 4.1 | 4.1 ∪ 4.2 |
| 5 | **Representation** | P5 Fair Representation | 5.1 | 5.1 ∪ 5.2 |

`0` = no change from today. **Fairwork score = the digit sum**, 0 to 10. `21122` scores 8.

`00000` closes nothing — it is today's Uber. `22222` closes all thirty gaps.

Every cell in the design is one of these 243 codes. The study's output is a **response surface over
that grid**: for each cell, how far each of the six outcomes moved relative to the driver's own
baseline.

### 6. What a finding looks like

Three kinds of claim come out of this, and they are the reason for the factorial rather than a
handful of vignettes:

1. **Main effects.** Which single lever, alone, moves which outcome most? (`10000` vs `01000` vs
   `00100` vs `00010` vs `00001`.)
2. **Dose.** Does the second Fairwork point buy anything? (`01000` vs `02000`.) A lever whose
   dial-2 adds nothing is a lever where the cheap half of the reform captures the whole effect.
3. **Interaction.** Do two reforms together deliver more or less than the sum of their separate
   effects? Computed as `shift(A∪B) − (shift(A) + shift(B))`. Negative means **sub-additive**:
   the two protections are substitutes — either one satisfies the driver and the second is
   redundant. Positive means they compound.

That third class is the contribution. It is the thing you cannot get from a small vignette study,
and it is directly actionable: sub-additive pairs tell a regulator which reform to mandate when
only one is affordable.

---

## Part II — The design commitments that keep it honest

These are the parts a reviewer will attack, so they are built as machine-checked invariants
(I1–I11 in `ARCHITECTURE.md` §2), not as good intentions. Understanding these five ideas is
understanding the study.

### 7. The treatment is a lookup, never a judgement

`version_code → set of commitments` is a **pure table lookup** over `dial_lookup.json` and
`gaps.json`. No model is asked what `01000` should mean. Same code in, byte-identical commitment
set out, forever.

This matters because the alternative — letting a model decide what "Conditions at level 1" involves
— would make the treatment drift between runs, and a treatment that drifts is not a treatment.

### 8. The model writes the stimulus but cannot choose it

A commitment from the codebook (*"delete the clause making safety and support services
discretionary"*) is not something you can show a driver. It has to become driver-facing text in
Uber's own register.

That is the **design agent's** only job: it receives a frozen commitment set and emits one
45–70 word paragraph per lever, second person, present tense, in Uber's voice.

**The design agent has no tools.** It cannot look anything up. This is not a style choice — it is
the containment guarantee. If it could fetch, an `01000` render could absorb threshold 2.2
material (social protection, protected standing, risk-free pay), and then `01000` and `02000` would
be the same stimulus, and the Conditions lever would be measuring nothing.

Every render is then gated by a **checker** before any twin sees it, on five tests:

| Gate | Asks |
|---|---|
| Coverage | Is every commitment in the spec actually present in the text? |
| **Containment** | Is anything present that is *not* in the spec? A single hit fails the cell. |
| Invariance | 45–70 words, reading grade in band, no cell-specific intensifiers ("finally", "at last") |
| Null identity | Does every dial-0 lever render the byte-identical string `"No change from today."`? |
| Sham indistinguishability | Does the sham pass every gate a live cell passes? |

Fail → re-render once → then halt that cell, mark it failed, log it, move on. **An unverified
variant never reaches a twin.**

### 9. Two controls, and only two

| Cell | What it shows the twin | What it measures |
|---|---|---|
| `00000` | Five identical `"No change from today."` lines | The twin's **noise floor**: how much does a twin's answer move when nothing changed? |
| `SHAM` | Five ordinary paragraphs, same word band and voice, describing the three things Uber **already does** | **Demand characteristics**: how much does a twin move simply because it was shown change-shaped text? |

`SHAM − 00000` is the floor. Any live cell whose shift is smaller than the sham floor is **not
interpretable**, and the analyst is instructed to say so.

The sham has **zero free parameters** — its content is the three `Met` criteria read straight out
of `criterion_findings.json`. We did not pick a plausible-sounding placebo; the codebook named it.

**No third control arm is ever added.** Each extra arm is a researcher degree of freedom, and
eliminating those is the point of the whole design.

### 10. Persona and stimulus are separate documents

Two documents reach the twin and they are kept apart on purpose.

**The persona passage** is built from the survey by Python, deterministically, with no LLM. Every
answered item becomes at least one first-person clause. Its rules:

- **Words, not numbers.** A `6` on a 7-point agreement item becomes *"I agree that my work schedule
  is made by an automated system"* — never *"I rated this 6 out of 7."* A twin shown numbers does
  arithmetic instead of reasoning from experience.
- **Whys verbatim.** Every why-probe the driver wrote is carried word for word, never paraphrased.
  Non-English answers keep the original with a bracketed translation.
- **Holdouts excluded.** Parts 15, 16 and 17 never appear. A twin that has read its own holdout
  answers cannot be validated.
- **Lossless.** A survey field with no template raises an error. It is never silently skipped.

**The round prompt** is a different document. It holds the scenario paragraphs (in randomised lever
order), the twin's own baseline **numbers**, and the 37 items to re-answer. It holds no whys and no
open-ended text.

Why separate: if the whys travelled with the stimulus, every twin would restate its own
justifications under every counterfactual, and the twin would look immovable no matter what you
showed it.

### 11. No model ever produces a metric

The twin produces 37 integers. Everything after that — reverse coding, metric means, shifts, the
index, interactions — is **Python arithmetic**. The analyst agent writes prose *about* numbers it
is handed, and is forbidden from quoting a figure not in its input bundle.

And nothing is imputed. An interaction needs three completed cells; with two, the system reports
**which code to run**. No estimates, no interpolation, no "approximately".

---

## Part III — The workflow, stage by stage

### 12. Stage 0 — Building the reference corpus (once, then frozen)

Four source documents in `additional_data/` are compiled into eight JSON files in
`data/reference/`, which are then **committed and never touched by the running app**.

```
Fairwork_LocationBased_Principles_verbatim.md  ─┐
Fairwork_Uber_India_Codebook_v2.docx           ─┼─► ingest/build_reference.py ─► data/reference/*.json
Uber_India_Policy_Corpus_Fairwork_Levers.md    ─┤                                        │
Survey_Research_GIGWORKER_v2.md                ─┘                        ingest/seed_db.py ─► Postgres
```

The builder is **byte-stable**: same sources in, same bytes out, verified by hash. It asserts every
count (33 criteria, 30 gaps, 126 chunks, 171 links, 73 items). A count mismatch is a build failure,
not a warning. `--check` mode exits non-zero if anything drifted.

This is the stage that makes the treatment auditable. Every commitment shown to a twin traces back
to a criterion, which traces back to a coded extract of Uber's own published words, cited.

### 13. Stage 1 — A driver fills in the survey

A Google Form, built by code (`apps_script/build_form.gs`) rather than typed, so that not one of its
112 question titles can drift from the item register. 22 sections, three languages
(English / Hindi / Marathi), fully labelled scale anchors at every point.

Seventeen parts, in this order:

| Parts | What they collect | Where it ends up |
|---|---|---|
| 1–2 | Screening, consent (7 statements) | Gate. **Consent statement 7 is the twin consent** — without it the response is stored and never becomes a twin. |
| 3–4 | Demographics, work context, background | Persona (identity, work context) |
| 5 | AMQ — algorithmic management perception (6 items) | Persona + twin battery (trait) |
| 6 | PAC — perceived algorithmic control (11 items) | Persona + twin battery (trait) |
| 7–12 | **The six outcomes**: fairness, clarity, satisfaction, continuance, workarounds, turnover | Persona + twin battery + **baseline for every shift** |
| 13 | Income | Persona |
| 14 | Own words, open-ended | Persona (verbatim) |
| 15 | Manipulation check on the human | Registered as `MC1`. Asks which of the four arm stories was shown; captured, not yet enforced as a screen. |
| **16** | **The respondent's assigned arm**, re-answered | **Holdout H2** — second validation set, scored per arm |
| **17** | **Six scenarios, re-answered** | **Holdout H3 — the fidelity test** |

On submit, an Apps Script HMAC-signs the payload and POSTs it to `/api/survey/intake`. The route
writes an immutable raw mirror to `data/temp/survey_<id>.json` **before** touching the database, so
a failed write is replayable. An unmapped question is a 422 — never a dropped answer.

**Part 17 is the keystone of the whole design.** Its six scenarios are not free-written vignettes:
they are six real version codes rendered from this same pipeline — `12220`, `00222`, `11010`,
`11211`, `02211`, `02200`. So the human and the twin meet the *identical stimulus*, and the twin's
fidelity can be scored on stimuli neither has seen before.

### 14. Stage 2 — The persona passage

Python reads the survey row and emits a first-person passage in a fixed order:

> identity → work context → household and dependence → how the app manages me → how the app guides
> me → fairness → clarity → satisfaction → staying → working around it → leaving → own words

Deterministic and hashable. The `persona_hash` is stored on every run, so any result can be traced
to the exact passage that produced it. Parts 15–17 are absent.

### 15. Stage 3 — A session runs

A session is one sweep. The researcher sets the five dials by hand, or sets a start code and a
number of iterations and lets the odometer advance.

```
create session
  ├─ ingestion        load reference data and twins
  ├─ panel            draw and FREEZE the twins that will answer every cell
  ├─ reconstruction   build any missing persona passages  (one log row per twin)
  ├─ control: 00000   the noise floor
  ├─ control: SHAM    the demand-characteristic floor
  └─ for each version code:
       ├─ lookup    → commitment set          deterministic, no model
       ├─ render    → 5 lever paragraphs      cached, design agent
       ├─ check     → checker report          gate; fail halts this cell only
       ├─ ask       → 37 answers × N twins    cached per (twin, code, style, wording)
       └─ analyse   → metrics, index, prose   Python first, model last
     checkpoint after every single unit
```

**Checkpointing is not defensive padding.** The platform runs on free tiers that sleep. Every stage
is idempotent and cache-keyed, so a session that dies mid-sweep resumes at its cursor and does not
re-pay for work already done. Stop is cooperative — it never kills mid-model-call, so no partial
answer is ever written.

**The odometer** is base-3 with Representation least significant, which is exactly the layout of the
results grid: 9 rows (pay × conditions) by 27 columns (contracts × management × representation).
`0 → 00000`, `81 → 10000`, `242 → 22222`.

### 16. Stage 4 — The rendering economy

This is worth understanding because it is the difference between a feasible study and an
unaffordable one.

A version code's five paragraphs are assembled from a pool of exactly **11 strings**: ten non-zero
lever paragraphs (5 levers × 2 dials) plus the one fixed dial-0 line. Paragraphs are cached on
`(lever, dial, style_version)`.

So **the design agent runs 10 times per style version, not 243 times.** All 243 cells are
permutations of those 11 strings.

This also buys a second, more important thing: it makes the levers *structurally* independent. Every
cell with Conditions = 1 shows the byte-identical Conditions paragraph. There is no per-cell wording
variation to confound a lever comparison.

Bumping `style_version` invalidates all ten and nothing else.

### 17. Stage 5 — Asking the twins

Each twin receives its persona, the five scenario paragraphs in **randomised order** (so paragraph
position cannot become a confound), its own baseline numbers, and the 37-item battery.

The battery is **37 items, not 39**: the two attention checks (`AMQ6`, `ALGO5`) are human
data-quality devices and are never put to a twin.

Output is schema-constrained: exactly the 37 expected item ids, each within its own scale's range
(a 5-point item rejects a 6). A schema failure retries once, then that twin is recorded as failed
**for that cell only** — it is not dropped from the study.

The randomisation seed, the lever order actually shown, the wording variant, the persona hash, the
delta hash, the style version and the model name are all persisted, so any round can be
reconstructed byte-for-byte.

### 18. Stage 6 — The quality test (where twins earn the right to count)

Run per twin, independently of any sweep.

1. Render the six Part 17 holdout codes **through the normal pipeline** — same design agent, same
   checker, same style version.
2. Show each to the twin with its persona. **No baseline is shown**, because the human had none
   either.
3. Collect 18 numbers (6 versions × fairness / pushback / keep).
4. Score against the human's own 18 answers: mean absolute error, and percentage of items within
   1 point.
5. Repeat three times and average, so one bad sample does not discard a good twin.

**Keep if MAE ≤ 1.0 and ≥ 80% of items within 1 point.** Otherwise the twin is dropped.

Typical reported outcome: *"17 of 20 twins kept."* The dropped ones are dropped, not tuned. Holdout
H2 (Part 16) is the second validation set, run on demand rather than as part of the gate.

### 19. Stage 7 — The analysis

**Metric scoring.** Reverse-code first (`SAT2`, `DEP1`, and `H2_SAT2` by inheritance:
`reversed = points + 1 − raw`), then mean the items **on their own published scale**. Five-point
blocks are never rescaled to seven.

| Metric | Items | Scale |
|---|---|---|
| fairness | FAIR1–4 | extent7 |
| clarity | CLAR1–3 | agree5 |
| happiness | SAT1–3 | agree7 |
| staying | CONT1–2 | agree5 |
| pushback | ALGO1–4 | agree7 |
| leaving | TURN1–3 | agree7 |

**Shift.** Baseline is the twin's **own survey answers**, so every driver is their own control:

```
shift[m] = mean_over_twins(score under the cell) − mean_over_twins(score at baseline)
```

**Index.** One headline number per cell, with pushback and leaving sign-flipped because less of each
is better for the driver:

```
index = mean(fairness, clarity, happiness, staying, −pushback, −leaving)
```

For `21122`: (1.62 + 0.60 + 1.50 + 0.68 + 2.05 + 1.02) / 6 = **1.245**.

**Interaction.** For two codes A and B, the joint cell is the elementwise max of their dial vectors.
All three cells must have completed runs or the function returns nothing:

```
extra = shift(A∪B) − (shift(A) + shift(B))
extra < 0 → sub-additive     extra > 0 → super-additive     extra = 0 → additive
```

Worked: *"staying changes +0.31 and +0.09 alone, +0.22 together. The extra is −0.18, so together
they add less than the sum."*

**The written analysis.** The analyst agent receives a deterministically assembled bundle — the code
and its Fairwork score, what the twins were told, the scenario text actually rendered, the six
shifts and six baselines, the index, `twins_n`, any computable interactions, and the session's
`SHAM − 00000` floor. It must ground every claim in commitments actually shown, flag anything below
the sham floor as uninterpretable, name the sub-additive pairs, say plainly when `twins_n` is too
small, and never invent a number.

### 20. Stage 8 — What the researcher sees

Eight sections, each its own route. `docs/06_SCREENS.md` is the full contract.

| Section | What it is for |
|---|---|
| **Main menu** | The application map, grouped by research stage, plus live counts of where things stand. |
| **Driver survey** | What the instrument is, and whether intake is healthy. The survey itself is a Google Form; intake runs outside the app so a sleeping Space cannot drop a submission. |
| **Twin Lab** | The study itself, in eight tabs: Agents · Dial board · Twins · Validation · Validity tests · Fieldwork · Results · Settings. |
| **Generator** | Synthetic surveys for testing the machinery. Seeded, so a batch is reproducible. |
| **Twin Studio** | Interrogate one twin in your own words. A sandbox — its runs are never evidence. |
| **Agent Studio** | What each agent is told, which model it uses, and the freeze before the main study. |
| **Statistics** | The PLS-SEM battery over human survey rows, and the export. |
| **Research model** | The model, hypotheses, constructs, method and the validation mapping. |

Inside Twin Lab, the four that carry the study: **Agents** is the live run as an expandable tree —
every agent's actual input and output inspectable, the audit trail rather than a progress bar.
**Dial board** sets the five dials by hand, with the code and "what the twins are told" updating
with no network call; `00000` warns and blocks. **Twins** shows the persona, the human's own
answers and the twin's answers under any version, side by side. **Results** is all 243 cells, and
clicking one gives its scenario text, shifts, index, interactions and written analysis.

Nothing is ever overwritten. A rerun **appends** a new run and flips an `is_latest_for_version`
pointer in the same transaction; the superseded run stays queryable forever.

---

## Part IV — The data files, and which stage uses each

### 21. Source documents — `additional_data/`

The human-authored inputs. Everything downstream is derived from these.

| File | What it is | Feeds |
|---|---|---|
| `Fairwork_LocationBased_Principles_verbatim.md` | The Fairwork standard, verbatim: 5 principles, 10 thresholds, 33 criteria | `criteria.json`, `thresholds.json` |
| `Fairwork_Uber_India_Codebook_v2.docx` | The coding exercise. Table B = evidence rows; Table C = per-criterion finding; Table D = the gaps and their commitments | `criterion_findings.json`, `gaps.json`, `chunk_criterion_links.json` |
| `Uber_India_Policy_Corpus_Fairwork_Levers.md` | Uber India's published policy, chunked into 126 citable extracts, verbatim | `corpus_chunks.json` |
| `Survey_Research_GIGWORKER_v2.md` | The full instrument: 17 parts, 73 registered items, 5 scales | `instrument.json` |
| `CODEBOOK_AND_VARIANT_PIPELINE.md` | The coding protocol and how gaps become treatments | Method section of the paper |
| `SURVEY_SCALES_AND_WHY_PROBES.md` | Scale rationale and the why-probe design | Instrument justification |
| `worked_out_eg.txt` | `01000` traced end to end by hand | Read this first if the pipeline feels abstract |
| `Digital_Platforms_Algorithmic_Management_Restructured.docx` | The theory paper | Framing |

### 22. Frozen reference data — `data/reference/`

**Generated once, committed, never written by the running application.** This is the scientific
artifact. If it changes, it changes by re-running the builder against edited sources and bumping a
version — never by an in-place edit.

| File | Rows | What it holds | Used at |
|---|---:|---|---|
| `criteria.json` | 33 | The Fairwork criteria: id, principle, threshold, satisfaction rule, text | Lookup, audit |
| `criterion_findings.json` | 33 | Per criterion: Met / Partly met / Not met / No evidence / Contradicted, with reason | **Defines the 0/10 baseline. The three `Met` rows are the SHAM set.** |
| `gaps.json` | 30 | **The treatment library.** Per gap: type (INTRODUCE / EXTEND / REMOVE / UNIVERSALISE / DOCUMENT), the **commitment** text, the precedent, the anchor sources | Lookup → DeltaSpec → design brief |
| `thresholds.json` | 10 | The ten threshold points, their lever, what gates what, and why 2026 awarded zero | Score arithmetic, gating logic |
| `corpus_chunks.json` | 126 | Uber's own words, verbatim, with citation and policy surface | Design agent's **voice anchors**, and the do-not-re-announce check |
| `chunk_criterion_links.json` | 171 | Which extract bears on which criterion, and how (SUPPORTS / PARTIAL / ASSERTED / SCOPE LIMITED / CONTRADICTS) | Evidence trail; what already exists |
| `instrument.json` | 73 items, 5 scales, 6 metrics | The item register: stem, part, block, scale, reverse-coded flag, attention flag, role, in-battery flag, H3 version code | Persona templates, round prompt, metrics, Form build |
| `dial_lookup.json` | 5 × 3 | **The treatment table.** Lever × dial → exact list of gap ids | `version_code → DeltaSpec`, the one operation the whole design rests on |

**On 161 vs 171.** The codebook records 161 evidence rows. A row may cite several extracts, so
expanding to chunk × criterion pairs gives 171. Both numbers are correct and both appear in the
codebook's front matter. Neither is a bug.

**Findings distribution** (the seeder asserts it): Partly met 12 · Not met 10 · No evidence found 6
· Met 3 · Contradicted 2 = 33.

**Gap types:** INTRODUCE 11 · EXTEND 9 · REMOVE 6 · UNIVERSALISE 2 · DOCUMENT 2 = 30.

**Already met, so never a gap:** `3.1.a`, `3.1.c` (Contracts) and `4.1.c` (Management). This is why
L3 dial 1 has four gaps rather than six and L4 dial 1 has three rather than four — and it is why
the sham has content to describe.

### 23. Configuration — `config/`

Changeable without touching code. Versioned, because changing one changes what a twin sees.

| File | What it controls |
|---|---|
| `style_contract.yaml` | The design agent's constraints: second person, 45–70 words, one paragraph per lever, no bullets, forbidden terms (`Fairwork`, `threshold`, `score`, `study`, `survey`, `twin`), the fixed dial-0 string, reading-grade band. **Constant across all 243 cells — anything that varies with the cell is a confound.** |
| `twin.default.yaml` | Model, persona template version, wording variants, quality thresholds (MAE ≤ 1.0, ≥ 80% within 1), seed, concurrency |
| `agents.default.yaml` | The five agent definitions. Behaviour is data: a sixth agent is an INSERT plus a prompt file. |
| `form_map.yaml` | `"<section>\|<title>"` → `item_id` for all 112 Form questions. **An unmapped question is a 422.** |
| `settings.py` | Environment plumbing |

### 24. Operational data — Postgres

Everything the platform produces. **Append-only where it is evidence.**

| Table | Holds | Mutability |
|---|---|---|
| `survey_submissions` | One row per submitted survey, real or synthetic, **consented or not**: eligibility, consent, attention, arm, city, service | Immutable. The Fieldwork denominator. |
| `survey_answers` | One row per (submission, item): the number, the text, the why verbatim, the language | **The baseline. Immutable.** |
| `twins` | One row per consented submission that was imported: demographics, persona passage, persona hash | Metadata mutable; passage versioned by hash |
| `sessions` | A sweep: status, iterations, start code, cursor, panel seed and size, frozen config | Status and cursor are genuine state |
| `session_panel` | The frozen set of twins that answer every cell in this session | Immutable once drawn |
| `runs` | One row per (session, version code): status, metrics, index, written analysis | **Append-only.** "Latest" is a flipped pointer. |
| `run_events` | The log tree, self-referencing via `parent_event_id`: stage, agent, status, full payload | **Append-only.** The audit trail. |
| `variants` | Per (code, style version): the DeltaSpec, its hash, the paragraph ids, the checker report | Append-only |
| `lever_paragraphs` | The **11 strings**, keyed (lever, dial, style version) | The render cache |
| `twin_answers` | 37 numbers per (run, twin, wording), plus lever order, seed, model, latency | **Append-only.** The raw data. |
| `twin_quality_runs` | Per (twin, holdout set): MAE, % within 1, correlations, kept/dropped, per-item detail | **Append-only.** Latest is a pointer. |
| `validity_results` | One row per completed validity test: statistics, verdict, model, twins | **Append-only.** The results *are* the log. |
| `analysis_runs` / `analysis_results` | The PLS-SEM battery, staged and resumable, with the engine version | Append-only per stage |
| `studio_runs` | Twin Studio sandbox interrogations | A leaf. Feeds no metric, no cell, no statistic. |

Answers are stored as one JSON vector per (run, twin, wording) rather than one row per item:
243 cells × 20 twins × 37 items would be ~180,000 rows against a 500 MB tier, for data that is
always read whole. As vectors it is ~4,860 rows and every read is one fetch.

### 25. Mirrors and scaffolding

| Path | What |
|---|---|
| `data/temp/survey_<id>.json` | The immutable raw record of what the worker actually submitted, written **before** any DB write. A failed write leaves a replayable file. Gitignored. |
| `apps_script/build_form.gs` | The Form, generated from `form_map.yaml` + `instrument.json`. Never hand-edited. |
| `apps_script/intake.gs` | The webhook: HMAC-signs each submission and posts it |
| `apps_script/test_harness.js` | Builds and round-trips the whole Form offline in Node, no Google account |
| `docs/GOOGLE_FORM.md` | The Form's exact build spec, section by section |
| `docs/DECISIONS.md` | Every judgement call already made, and why. **Read before questioning an existing choice.** |

---

## Part V — How the pieces make the answer

### 26. The whole chain in one view

```
Fairwork standard ──► codebook ──► gaps.json ─────┐
                                                  │  dial_lookup
                                    version code ─┴─► commitment set  (pure lookup, no model)
                                                          │
Uber policy corpus ──► anchor chunks ─────────────────────┤  (voice + don't re-announce)
style_contract.yaml ─────────────────────────────────────►┤
do-not-say list ─────────────────────────────────────────►┘
                                                          ▼
                                            design agent (no tools)
                                                          ▼
                                            5 lever paragraphs ──► CHECKER (gate)
                                                                      │
 survey row ──► persona passage ──► TWIN ◄────────────────────────────┘
      │              (no holdouts)     │  + own baseline numbers
      │                                ▼
      │                          37 numbers
      │                                │
      └──── baseline ──────────────────┤
                                       ▼
                        Python: reverse-code, score, shift, index, interactions
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                  analyst agent               results grid
                  (prose about numbers)       (243 cells)
```

Read it as: the **left column is evidence** (a published standard, a coded corpus, a real survey),
the **middle is deterministic machinery**, and the **model appears in exactly three places** —
writing the stimulus, being the twin, and writing the commentary. In none of those three does it
choose a treatment or compute a number.

### 27. What makes the resulting number trustworthy

Every claim in the paper can be traced backwards without a gap:

> an index value
> → six metric shifts
> → 37 integers per twin
> → the exact round prompt, reconstructible from the stored seed, lever order and persona hash
> → five checker-verified paragraphs
> → a commitment set that is a table lookup
> → gaps read from a codebook
> → findings coded against Fairwork criteria
> → verbatim extracts of Uber's own published policy, cited

And the instrument is calibrated: only twins that reproduced their human on unseen stimuli
contributed to it, and every effect is reported against both a null floor (`00000`) and a
demand-characteristic floor (`SHAM`).

### 28. Stated limitations — carry these into the paper

Not defects. Known bounds, written down so a reviewer does not have to find them.

1. **Twins are not people.** They are a validated instrument for extrapolating a real person's
   pattern to unseen stimuli. The fidelity number (MAE against holdout) is the honest statement of
   how far that extrapolation can be trusted, and it is reported per twin.
2. **Anchoring.** Twins are shown their own baseline numbers, which will pull answers toward those
   numbers. This is deliberate — it is what keeps a twin recognisably its own driver — and the
   bound on it is `SHAM − 00000`, reported with every cell.
3. **The index mixes scale lengths.** Clarity and staying are 5-point; the other four are 7-point.
   The unweighted mean of six shifts is the **display** index. Per-metric shifts are stored so a
   standardised index can be computed at modelling time.
4. **Attrition through the quality gate reduces analysable N.** A dropped twin is currently excluded
   from all cells rather than flagged per cell, which keeps N constant across the grid at the cost
   of some data.
5. **Fairwork's own judgement is inherited.** A criterion coded "Partly met" reflects the coders'
   reading of published policy, not of practice on the ground. The corpus is what Uber says, not
   what Uber does.
6. **Part 15** (the human manipulation check) is registered as `MC1` and currently unused.

### 29. Open questions running on defaults

Each has a working default; none blocks anything. `ARCHITECTURE.md` §10 is the live list.

1. **Sweep start.** `00000` runs once per session as the control and does not consume an iteration;
   the odometer sweep proper starts at `10000`. Setting `start_code: "00000"` makes it a plain sweep
   from index 0.
2. **Part 15 / `MC1`** — should failing the human manipulation check screen a respondent out of the
   analysable sample, as the attention checks do? Captured, not enforced.
3. **Mixed-scale index** — display index as-is, standardise at modelling time.
4. **Panel size** — 20 by default. A sweep uses a stratified subsample of quality-passed twins,
   frozen at session creation and identical in every cell; a failed twin is dropped from all cells
   rather than flagged per cell, which keeps N constant across the grid.
5. **The free credit allowance** is unpublished and must be read off the provider account before
   the first sweep.
6. **Whether a long background task survives on the deployment target** is undocumented and is
   smoke-tested in M1.
7. **Bootstrap floor** — 30 is kept as a hard UI minimum for compatibility with the prototype;
   the default is 5,000 and anything below 1,000 is not reportable.

---

## Where to go next

| You want to | Read |
|---|---|
| See one version code traced by hand | `additional_data/worked_out_eg.txt` |
| Know the invariants that cannot be relaxed | `ARCHITECTURE.md` §2 |
| Know exactly what a data file contains | `docs/01_DATA_MODEL.md` |
| Understand the agents and how prompts are structured | `docs/02_AGENTS_AND_PROMPTS.md` |
| Understand how a version code becomes 37 numbers | `docs/03_RESEARCH_PIPELINE.md` |
| Understand the orchestrator, resume and caching | `docs/04_BACKEND.md` |
| Understand the visual language and components | `docs/05_DESIGN_SYSTEM.md` |
| Understand the screens | `docs/06_SCREENS.md` |
| Find a formula | `docs/07_STATISTICS.md` |
| Understand the quality gate and the eight validity tests | `docs/08_VALIDATION_AND_VALIDITY.md` |
| Know what is reproducible and what is not | `docs/09_REPRODUCIBILITY.md` |
| Know what a sweep costs | `docs/10_SCALE_AND_COST.md` |
| Know what to build next | `docs/11_BUILD_PLAN.md` |
| Know why a choice was made | `docs/DECISIONS.md` |
