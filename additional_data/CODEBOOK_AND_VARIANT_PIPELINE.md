---
title: "Fairwork × Uber India codebook, and the counterfactual variant pipeline"
status: design specification
date: 2026-09-22
standard: Fairwork Location-based Platform Work Principles (in effect 15 Oct 2024)
baseline_platform: Uber (India), Fairwork India Ratings 2024 score = 0/10
corpus_version: "2026.09-lb1 (re-filed against the location-based standard, 2026-09-22)"
---

# 0. The finding that gated everything else — now closed

**Resolved on 2026-09-22.** `Uber_India_Policy_Corpus_Fairwork_Levers.md` is now filed against the
**Fairwork Location-based Platform Work Principles** and carries `corpus_version: 2026.09-lb1`.
Section 0 is kept as the record of what was wrong and what the fix did.

The corpus as compiled (v2026.09) was filed against the **Fairwork AI Principles**, not the
**Fairwork Location-based Platform Work Principles**. Its front matter said
`standard: Fairwork AI Principles`, and its threshold headings were the AI ones.

| # | Corpus heading (Fairwork AI) | Location-based heading (what Uber India is actually rated on) | Same subject? |
|---|---|---|---|
| 1.1 | Pays at least the local minimum wage | Ensures workers earn at least the local minimum wage after costs | close |
| 1.2 | Pays at least the local living wage | Ensures workers earn at least a local living wage after costs | close |
| 2.1 | Ensures safe working conditions | Mitigates task specific risk | close |
| 2.2 | Ensures paid leave and a safety net | Ensures safe working conditions and a safety net | close |
| 3.1 | Provides decent contracts | Provides clear and transparent terms and conditions | close |
| 3.2 | **Ensures secure and continuous work** | **Ensures that no unfair contract terms are imposed** | **different** |
| 4.1 | Provides fair treatment and due process | Provides due process for decisions affecting workers | close |
| 4.2 | **Clear and effective systems for data management, explanations, and appeals** | **Provides equity in the management process** | **different** |
| 5.1 | Assures freedom of association and worker voice | Assures freedom of association and the expression of worker voice | same |
| 5.2 | Supports democratic governance and collective bargaining | Supports democratic governance | close |

## Why it had to be fixed before coding

The whole design compares a counterfactual Uber against **the Fairwork India rating Uber actually
holds** (0/10, 2024). That rating is issued under the location-based standard. Coding the corpus
against the AI standard would have made the dial positions mean something the rating does not.

## What the re-file actually did

Threshold assignment was derived from **Table B of the codebook** (161 chunk-criterion links), not
re-judged by hand. An extract is filed under the threshold holding the most of its links; ties fall
to the v2026.09 filing where that threshold's subject survives the change of standard (all but 3.2
and 4.2), then to the strongest judgement, then to threshold order.

| | v2026.09 | v2026.09-lb1 |
|---|---|---|
| Extracts | 126 | 126 (0 lost, 0 added) |
| Extracts that changed threshold | — | **39** |
| Extracts with no criterion (`OUT_OF_FRAME`) | — | **5** |
| Recorded absences | 42 | 42, of which **21** re-filed and **4** out of frame |
| Criterion-level anchors | none | **every** extract carries `criteria` with its judgement |

Threshold counts moved from `1.1:32 2.1:11 2.2:9 3.1:24 3.2:5 4.1:22 4.2:17 5.1:5 5.2:1` to
`1.1:33 2.1:13 2.2:9 3.1:20 3.2:22 4.1:12 4.2:6 5.1:5 5.2:1` plus 5 out of frame.

Verbatim text, `chunk_id`, `source_id`, `policy_surfaces`, `section`, `audience` and every citation
are byte-identical to v2026.09; this was verified mechanically, not by eye. `chunk_id` and absence
identifiers were deliberately **not** renumbered — they are opaque stable keys and the codebook
cites them, so `L4-4.1-015` now sits at threshold 4.2 and says so in a `refiled_from` field.

## What the audit predicted, and what happened

- **Current `4.2` holds 17 chunks**, almost all privacy, data rights and algorithm description
  (S08 Privacy Notice, S06 Communications Intelligence, S03 Uber Pro, S14 ratings, S19 Trip Radar,
  S32 clauses). Under the location-based standard these split three ways:
  - privacy / data protection policy chunks → **3.1.f**
  - matching, dispatch tiering, ratings, pricing and bonus logic → **3.2.d**
  - human review of automated decisions and appeal rights → **4.1.b**
  - almost nothing remains for location-based 4.2 (equity).
- **S04, the Uber Non-Discrimination Policy**, is currently filed at `L4-4.1-015`. It is the single
  most relevant document for location-based **4.2.a** and must move there.
- **Current `3.2` holds 5 chunks** on contract term, termination, notice and the post-engagement
  multi-apping restriction. Under location-based 3.2 only some of these are on-criterion
  (3.2.a notice of change, 3.2.b unfair/liability clauses); contract-continuity material has **no
  location-based criterion** and goes to an `OUT_OF_FRAME` bucket rather than being forced.

All three predictions held. The estimate of "roughly 22 of 126" chunks changing threshold was low:
**39** moved once the assignment was driven off Table B rather than off the heading crosswalk. The
underestimate came from reading the heading crosswalk rather than the coding: it caught the 4.2
block (all 17 moved) but missed the 3.1 block, which lost 12 extracts — nine of them to 3.2 on
contract-fairness grounds no comparison of threshold *names* would surface. Old 4.1 lost 13: six to
4.2, two to 3.2, and the five that turned out to have no criterion at all.

This was a re-coding pass over existing structured data, not a re-collection.

---

# 1. Codebook

Three tables. One is the frozen scientific artifact; the other two are derived from it.

## 1.1 Table A — `criteria.csv` (the standard, 33 rows, never edited after freeze)

Straight from `Fairwork_LocationBased_Principles_verbatim.md`.

```
criterion_id      3.2.d
principle         3
threshold         3.2
threshold_name    Ensures that no unfair contract terms are imposed
satisfaction_rule ALL          # ALL | ONE | BOTH
criterion_text    <verbatim>
footnotes         [ ]          # verbatim footnote text cited by this criterion
```

## 1.2 Table B — `chunk_criterion_links.csv` (the coding work; one row per chunk × criterion)

This is the correlation book. A chunk may link to several criteria; a criterion may draw on many
chunks; a chunk may link to none (`OUT_OF_FRAME`).

```
link_id              L3-3.2-005__3.2.b
chunk_id             L3-3.2-005
source_id            S32
criterion_id         3.2.b
relation             SUPPORTS | PARTIAL | CONTRADICTS | SILENT | SCOPE_LIMITED | OUT_OF_FRAME
evidence_span        <exact substring of the chunk's verbatim text>
rationale            <1–2 sentences, why this span bears on this criterion>
scope_caveat         e.g. "Cars only; no published contract for Moto/Auto"
coder_a / coder_b    initials
agreement            1 | 0
resolution           <text, where coders disagreed>
```

`relation` definitions, fixed before coding starts:

| value | means |
|---|---|
| `SUPPORTS` | the text, on its face, does what the criterion requires |
| `PARTIAL` | on-topic and moves toward the criterion, but falls short of it |
| `CONTRADICTS` | the text works against the criterion (e.g. a clause limiting worker voice) |
| `SCOPE_LIMITED` | would support, but applies to a subset (one city, one vehicle class, one tier) |
| `SILENT` | the chunk was expected to address it and does not — recorded, not inferred |
| `OUT_OF_FRAME` | the chunk has no location-based criterion |

`CONTRADICTS` matters more than it looks. `L5-5.1-005` (S32 §2.5, disparagement and deactivation
grounds) and `L3-3.2-005` (post-engagement restriction) are evidence *against* 5.1.c and 3.2.b.
A codebook that only records supporting evidence cannot represent Uber's actual position.

## 1.3 Table C — `threshold_verdicts.csv` (10 rows, rolled up from Table B)

```
threshold_id        3.2
criteria_status     {3.2.a: NOT_MET, 3.2.b: NOT_MET, 3.2.c: NO_EVIDENCE, 3.2.d: PARTIAL}
threshold_awarded   0
gate_satisfied      <is 3.1 awarded? 3.2 is unawardable if not>
fairwork_2024       0     # cross-check against the published rating
divergence_note     <if our adjudication differs from Fairwork's published note, say so and why>
gaps                [ GapSpec, ... ]   # see §2
```

`fairwork_2024` is the external validity check. Uber India 2024 is blank on all ten, so every
threshold must roll up to 0. If a threshold rolls up to 1, the coding is wrong or the corpus has
material Fairwork did not see — either way it must be resolved and reported, not quietly kept.
(For calibration on a platform that *does* score, code bigbasket 2024 the same way and check
against its six published notes. That is a cheap, publishable reliability claim.)

---

# 2. GapSpec — the object the design agent consumes

One per unmet criterion. Derived deterministically from Table C. **This is the treatment
definition, and it is frozen.**

```yaml
gap_id: 3.2.d
criterion_text: >
  In cases where algorithms are used to determine pricing, bonuses, ratings and/or allocate jobs,
  the data collected, and calculations used must be transparent and documented in a form available
  to workers in clear and comprehensible language that all workers could be expected to understand.
current_state: PARTIAL
current_evidence:
  - chunk_id: L4-4.2-009
    span: "Priority Rides ... Airport Advantage"
    reading: "Dispatch priority is named as a tier benefit but the allocation rule is not stated."
  - chunk_id: L4-4.2-011
    span: "<S14 ratings text>"
    reading: "Rating arithmetic is disclosed; matching and pricing calculations are not."
commitment:                       # what would close the gap, in Fairwork's terms, not Uber's
  - "Publish, in the driver app, the data inputs and the calculation used to set the fare shown
     for a trip, to set bonus eligibility, and to decide which driver a trip is offered to."
  - "Write it at a reading level all drivers can be expected to understand, in the languages the
     driver app already supports."
uber_anchor:                      # the existing Uber surface the change attaches to
  surfaces: [ "Upfront Fares screen (S11)", "Uber Pro tier page (S03)", "Trip Radar (S19)" ]
  register_source: [ S11, S12, S20 ]   # chunks the design agent imitates for voice
scope_caveat: "Cars only in the published contract; state coverage for Moto/Auto as unchanged."
```

---

# 3. The variant pipeline

## 3.1 Layer separation

```
version code  01122
      │
      ▼
[ 1. LOOKUP — deterministic ]
      dial digit per lever → the GapSpecs that dial position closes
      0 → {}                    1 → gaps of threshold X.1
      2 → gaps of threshold X.1 ∪ X.2
      │   (Fairwork's cumulative rule is what makes 0/1/2 ordinal and legitimate)
      ▼
   DeltaSpec  = the exact set of commitments for this cell.  Hashable. Identical every run.
      │
      ▼
[ 2. RENDER — generative, constrained ]
      Design agent input:  DeltaSpec commitments
                         + uber_anchor verbatim chunks (for register)
                         + style contract (§3.3)
      Design agent output: 5 lever paragraphs of driver-facing scenario text in Uber's voice
      │
      ▼
[ 3. VERIFY — deterministic + checker agent ]
      every commitment present?   nothing invented?   length/reading level in band?
      │
      ▼
   scenario_text  →  cached against hash(DeltaSpec, style_version)  →  twins
```

The dial is fully determined by Table D's thirty gaps. Nothing here is a free parameter:

| Lever | Dial 0 | Dial 1 (X.1) | Dial 2 (X.1 ∪ X.2) | Rules already met, so never a gap |
|---|---:|---:|---:|---|
| L1 Fair Pay | 0 | 2 | 3 | — |
| L2 Fair Conditions | 0 | 3 | 6 | — |
| L3 Fair Contracts | 0 | 4 | 8 | 3.1.a, 3.1.c |
| L4 Fair Management | 0 | 3 | 8 | 4.1.c |
| L5 Fair Representation | 0 | 3 | 5 | — |

`00000` closes nothing; `22222` closes all thirty. The three met rules generate no GapSpec at any
dial position, which is what keeps the `SHAM` cell in §4.1 distinguishable from a live one.

## 3.2 Why not the two options as posed

**Option A (hand raw chunks + Fairwork text to an LLM, let it propose the variant).** The treatment
stops being a fixed stimulus. Cell `01122` would mean something slightly different on every run, and
across the 243 cells the *strength* of a given dial position would drift. Any effect you then
attribute to "Fair Contracts at level 1" is confounded with how forcefully that run happened to word
it. This is the failure mode a reviewer at ISR or JMIS will find first.

**Option B (adjudicate fully offline, and the design agent has nothing to do).** The premise is
wrong — it has exactly the right thing to do. In an experiment, *what* changes is the manipulation
and must be fixed; *how it is said* is realism, and that is the design agent's job. Rendering 243
cells so that Fair Pay at level 2 reads like Uber wrote it, stays coherent with the other four lever
paragraphs in the same cell, and holds length and reading level constant across cells, is real work
and it is the part an LLM is actually good at.

Option B is also load-bearing for a reason that has nothing to do with the design agent: **you cannot
compute "change from Uber today" without knowing where Uber today sits.** Table C is that baseline.
Without it the dial has no origin.

So: B produces the treatment, A's generative step survives as rendering only.

## 3.3 Style contract for the design agent

Constant across all 243 cells, because anything that varies with the cell is a confound.

- Second person, present or near-future tense — matches S20, S11, S12.
- One paragraph per lever, 45–70 words, no bullets.
- Every commitment in the DeltaSpec appears; nothing outside it appears.
- No numbers, no dates, no monetary amounts unless the GapSpec supplies them.
- Levers at dial 0 render as a fixed string, **not** regenerated: `"No change from today."`
- Never names Fairwork, never says "principle", "threshold", "score", "research", or "study".
- Lever paragraph order is fixed in the text; **presentation order to the twin is randomised**.

## 3.4 What the checker verifies before a variant reaches a twin

1. **Coverage** — each commitment string in the DeltaSpec is entailed by the rendered text.
2. **Containment** — no commitment appears that the DeltaSpec does not contain. This catches the
   design agent "helpfully" adding pay language to a Fair Conditions paragraph, which would silently
   contaminate the Fair Pay cell.
3. **Invariance** — word count and reading grade within band; no cell-specific intensifiers.
4. **Null-cell identity** — `00000` renders to five `"No change from today."` lines, byte-identical.
5. **Sham indistinguishability** — `SHAM` must pass every check a live cell passes: same paragraph
   count, same word band, same reading grade, no `"No change from today."` line. A sham a twin can
   spot as a sham measures nothing. Its DeltaSpec is the three met rules and nothing else, so
   Containment (check 2) is what stops a real commitment leaking into it.

Fail any check → re-render once → then halt the cell and log it. Never let an unverified variant
into the twin loop.

---

# 4. Design issues worth settling now

**4.1 The baseline is 0/10, so the dial is monotone.** Every cell ≥ 0 is an improvement; there is no
"worse than today" arm. That gives a clean dose-response reading, but it means the study cannot
detect backlash to withdrawal of an existing protection, and the twins may learn that "change text =
better". There are exactly **two control cells, and no others**:

| Cell | Definition | Renders as | Reads on |
|---|---|---|---|
| `00000` | Empty DeltaSpec. | Five `"No change from today."` lines, byte-identical every run. | Floor. Any movement here is noise. |
| `SHAM` | DeltaSpec = the three rules Table C records as **already met**: 3.1.a (contracting party named), 3.1.c (informed consent taken), 4.1.c (appeal survives deactivation). | Five paragraphs in the ordinary style, same word band and voice as a live cell. | Reaction to the *presence* of change text. |

The sham has no free parameters: its commitment set is fixed by Table C, not chosen. It works
because the codebook already identifies the trap — "a change describing post-deactivation appeals as
new would be describing something Uber already does, and any measured response to it would be
uninterpretable". That is precisely what makes it the right null. If twins improve on `SHAM`, the
difference between `SHAM` and `00000` is the demand-characteristic estimate, and it is subtracted
from every live cell before any lever effect is reported.

**4.2 The baseline is always shown.** Every cell shows the twin its own baseline answers before
asking it to re-answer. This is a fixed feature of the round prompt, not a manipulation, and there is
no no-baseline arm. Anchoring toward the direction of change is therefore a **stated limitation**,
bounded by the `SHAM` − `00000` contrast above, which is measured under the same anchoring. Adding a
no-baseline arm would double the cell count to buy an estimate the sham already bounds.

**4.3 Call volume.** The twin re-answers the **whole Likert instrument**, not a short outcome
battery. From `Survey_Research_GIGWORKER_v2.md` that is **37 items**: 39 Likert items across Parts
5–13, less the two attention checks, which are a human data-quality device and are not put to a twin.
Excluded from the round prompt: every why-probe, every open-ended item, the Part 15 scenario, the
Part 16 re-answer block, and the Part 17 six-version block — those six versions are the human
validation set the twins are scored against, so showing them to a twin would destroy the comparison.

Cost shape: 243 cells × N twins × 37 items. Cache on `hash(DeltaSpec, style_version)` so re-renders
cost nothing, and batch the 37 items into one call per twin per cell rather than one call per item.

**4.4 Uber's two live pay models.** The corpus records both the subscription model (S32, S33) and the
commission model (S09, S11, S12) and does not reconcile them. The Fair Pay GapSpec must state which
model the counterfactual attaches to, or the Fair Pay lever is ambiguous at every dial position.

**4.5 Scope gaps are not compliance gaps.** No published driver contract exists for Moto, Auto,
Intercity, Hire or courier work. That is a *coverage* limit on the corpus, not evidence Uber fails a
criterion. `SCOPE_LIMITED` keeps the two apart; a codebook that conflates them will overstate the
gap and inflate every treatment effect.
