---
title: "Survey revision: Likert anchor labels, scale provenance, and the why-probe layer"
date: 2026-09-20
applies_to: "Survey_Research_GIGWORKER (Uber India driver survey)"
---

# 1. Scale provenance and citations

Six distinct response formats appear in the instrument. Label every point, not just the ends —
fully-labelled scales reduce acquiescence and translate more reliably into Hindi and Marathi than
numeric-only scales with endpoint anchors.

| Block | Source scale | Points | Format |
|---|---|---|---|
| The app and your work | Algorithmic Management Questionnaire (AMQ) | 7 | agreement |
| How the app guides you | Perceived Algorithmic Control (PAC) | 5 | agreement |
| How fair the app is | Perceived Algorithmic Fairness | 7 | extent |
| How clear the app is | Algorithmic transparency | 5 | agreement |
| Your job | MOAQ job satisfaction subscale | 7 | agreement |
| Staying with Uber | Continuance intention | 5 | agreement |
| Working around the app | Algoactivism | 7 | agreement |
| Leaving Uber (items 1–2) | MOAQ turnover intention | 7 | agreement |
| Leaving Uber (item 3) | turnover intention, likelihood form | 7 | likelihood |
| Your income | Economic dependence | 7 | agreement |
| Six versions block | study-specific outcome items | 7 | fairness / likelihood |

**The 7-point agreement format traces to the AMQ.** Cite as:

> Parent-Rocheleau, X., Bentein, K., Simard, G., & Parker, S. K. (2024). Algorithmic management:
> Assessing the impacts of technological human resource management on the future of work.
> *Human Resource Management*. https://doi.org/10.1002/hrm.22185

The AMQ was developed through a six-phase scale development process on 1,332 gig workers, yielding
20 items on five subdimensions (monitoring, goal setting, scheduling, performance rating,
compensation) rated on a 7-point Likert agreement scale.

Other scale citations for the methods section:

- **PAC (5-point):** Pei et al. (2021), *Nankai Business Review*; 11 items, three subdimensions
  (standardised guidance, tracking evaluation, behavioural constraint). Reproduced in full in a 2024
  *Humanities and Social Sciences Communications* replication.
- **Perceived algorithmic fairness (7-point extent):** Jabagi et al. (2025),
  *International Journal of Human Resource Management*, https://doi.org/10.1080/09585192.2024.2441448.
  Built on the Colquitt (2001) procedural justice measure; validated on 435 Uber drivers. Colquitt's
  original uses a 5-point extent scale; the 7-point extension is Jabagi et al.'s — say so in the
  methods section rather than letting it read as Colquitt's format.
- **Transparency (5-point):** Höddinghaus, Sondern & Hertel (2021), *Computers in Human Behavior*,
  https://doi.org/10.1016/j.chb.2020.106635.
- **Satisfaction and turnover intention (7-point):** Michigan Organizational Assessment
  Questionnaire, Cammann, Fichman, Jenkins & Klesh (1979). Flag in the methods section that no
  algorithmic-management-specific satisfaction scale exists and this is an interim choice.
- **Continuance intention (5-point):** Qiao & Cheng (2023), https://doi.org/10.23977/appep.2023.040807.
- **Algoactivism (7-point):** de Jong, Weber & Remus (2025).
- **Economic dependence (7-point):** adapted from Van Dam (2005) and Clark (2005); α = 0.88.
  Item 1 is **reverse coded** — the current draft does not say so anywhere. Fix before fielding.

---

# 2. Anchor labels

## 2.1 Seven-point agreement (AMQ, algoactivism, satisfaction, turnover, dependence)

| # | English | Hindi | Marathi |
|---|---|---|---|
| 1 | Strongly disagree | पूरी तरह असहमत | पूर्णपणे असहमत |
| 2 | Disagree | असहमत | असहमत |
| 3 | Somewhat disagree | कुछ हद तक असहमत | काहीसा असहमत |
| 4 | Neither agree nor disagree | न सहमत न असहमत | सहमत नाही, असहमतही नाही |
| 5 | Somewhat agree | कुछ हद तक सहमत | काहीसा सहमत |
| 6 | Agree | सहमत | सहमत |
| 7 | Strongly agree | पूरी तरह सहमत | पूर्णपणे सहमत |

## 2.2 Seven-point extent (perceived algorithmic fairness)

| # | English |
|---|---|
| 1 | To a very small extent |
| 2 | To a small extent |
| 3 | To a somewhat small extent |
| 4 | To a moderate extent |
| 5 | To a somewhat large extent |
| 6 | To a large extent |
| 7 | To a very large extent |

## 2.3 Seven-point likelihood (turnover item 3; version-block pushback and keep-driving items)

| # | English |
|---|---|
| 1 | Not at all likely |
| 2 | Slightly likely |
| 3 | Somewhat likely |
| 4 | Moderately likely |
| 5 | Quite likely |
| 6 | Very likely |
| 7 | Extremely likely |

## 2.4 Seven-point fairness (version-block fairness item)

| # | English |
|---|---|
| 1 | Very unfair |
| 2 | Unfair |
| 3 | Somewhat unfair |
| 4 | Neither fair nor unfair |
| 5 | Somewhat fair |
| 6 | Fair |
| 7 | Very fair |

## 2.5 Five-point agreement (PAC, transparency, continuance)

| # | English | Hindi | Marathi |
|---|---|---|---|
| 1 | Strongly disagree | पूरी तरह असहमत | पूर्णपणे असहमत |
| 2 | Disagree | असहमत | असहमत |
| 3 | Neither agree nor disagree | न सहमत न असहमत | सहमत नाही, असहमतही नाही |
| 4 | Agree | सहमत | सहमत |
| 5 | Strongly agree | पूरी तरह सहमत | पूर्णपणे सहमत |

The 5-point and 7-point scales share endpoint wording and differ only in the number of intermediate
steps. That is deliberate: it keeps the translation burden down and keeps the twin's reading of
"strongly agree" stable across blocks. Do **not** rescale 5-point blocks to 7 for analysis — report
them on their published metric and standardise only at the modelling stage.

---

# 3. The why-probe layer

## 3.1 Rule

Every Likert item gains a paired free-text probe. Optional in the fielded survey; **mandatory in
testing**, because a twin built from a persona with missing whys is not comparable to one built
from a complete persona.

Probe wording, constant across items so it does not cue content:

> **Why did you choose that?** Did something happen that made you pick this number? A trip, a week,
> something the app did, something someone said. A sentence or two is enough.

Hindi: **आपने यह क्यों चुना?** क्या कुछ ऐसा हुआ जिसकी वजह से आपने यह नंबर चुना?
Marathi: **तुम्ही हेच का निवडलं?** असं काही घडलं का ज्यामुळे तुम्ही हा आकडा निवडला?

Keep the probe **neutral on valence**. "Why are you unhappy with this?" would bias the persona toward
grievance and would propagate into every counterfactual answer the twin gives.

## 3.2 What changes in the instrument

- Existing open-ended questions stay exactly as they are.
- Attention-check items (Part 4 item 6, Part 7 item 5) get **no** probe.
- Screening, consent and demographic items get no probe.
- The version-block items get no probe in the human survey — the version block is the
  counterfactual, and asking a human to justify a hypothetical adds length without adding persona.

## 3.3 Fixes to make in the same pass

1. **Duplicated block.** "PART 6 — CONTINUATION OF HOW THE APP GUIDES YOU" repeats PAC items 6–11
   and the open question verbatim from Part 5. Delete the duplicate; it is a pagination artifact and
   will otherwise double-weight the tracking-evaluation and behavioural-constraint subdimensions.
2. **Part numbering.** "PART 5" appears three times, "PART 7" three times, "PART 10" four times.
   Renumber sequentially so the twin-builder can address blocks by ID.
3. **Reverse-coded item.** Mark "I can easily get another job outside the platform economy if I want
   to" as reverse-coded in the codebook and reverse it before any index is computed.
4. **Stated duration.** The cover sheet says 36 minutes; the lit review's Section 6.2.1 wording says
   20. With ~50 why-probes added, neither is right. Time the pilot and put the measured number on
   the sheet — the consent claim has to be accurate.
5. **Consent statement 7** already covers twin construction ("an anonymised computer model that
   answers research questions in the way I might"). Extend it to say the model will be shown
   hypothetical future versions of Uber's rules and asked to answer again — that is what the twin is
   actually used for, and the current wording does not quite reach it.

---

# 4. Persona passage construction (deterministic, Python only)

The passage is the twin's entire grounding, so it must be lossless and rule-generated, with no LLM
in the loop.

## 4.1 Contract

- **Total function.** Every answered item contributes at least one clause. A field with no template
  is a build error, not a silent skip.
- **First person, plain register.** The passage reads as the driver speaking.
- **Numbers carried as words, not scores.** A `5` on a 7-point agreement item becomes
  "I somewhat agree that ..." — never "I rated this 5 out of 7". A twin that sees numbers will
  arithmetic its way to the next answer instead of reasoning from experience.
- **Whys quoted verbatim.** Never paraphrased, never translated in the passage itself. If the
  response is in Hindi or Marathi, carry the original and append a translation in brackets.
- **Fixed order.** Identity → work context → household and dependence → how the app manages me →
  how the app guides me → fairness → clarity → satisfaction → staying → working around it → leaving →
  own words. Stable order means passage differences across twins are content differences.
- **Deterministic and hashable.** Same survey row in, byte-identical passage out. Store
  `hash(passage)` with every twin run so a result can be traced to its exact grounding.

## 4.2 Clause template shape

```
AMQ3  ("My work schedule is made by an automated system", response 6, why "...")
  →  "I agree that my work schedule is made by an automated system. In my own words: '<why verbatim>'"
```

One template per item, keyed by item ID, with the anchor label substituted from §2. Roughly 50
templates. Write them once, freeze them, version them alongside the corpus.

## 4.3 What the twin sees at run time

Two documents, kept separate:

1. **Persona passage** (above) — stable for the life of the twin.
2. **Round prompt** — the scenario text for one version cell, plus the twin's own baseline numeric
   answers, plus the numeric battery to re-answer.

The persona passage contains the whys and the qualitative answers. The round prompt contains
**numbers only** — no whys, no qualitative answers, no version-block items from the human survey.
Keeping them apart is what stops the twin from re-reading its own justifications and simply
restating them under every counterfactual.
