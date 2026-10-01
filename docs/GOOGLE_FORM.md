# The Google Form — exact build spec

This is what to build in Google Forms and how to wire it to Twin Lab. The Form itself is out of
scope for the code (ARCHITECTURE.md §6.3); this document is the contract between the two.

**Source of truth for wording is `additional_data/Survey_Research_GIGWORKER_v2.md`.** Source of truth for what the
intake route will accept is `config/form_map.yaml`. The tables below are generated from that map,
so a title here is a title the route accepts.

---

## 0. The one rule that matters

> **Every question title and every section header must match this document byte for byte.**

Intake looks each answer up by `"<section header>|<question title>"`. A question it cannot find is
rejected with **HTTP 422** and the whole submission is refused — deliberately, because a silently
dropped question is a hole in the persona that nothing downstream can detect (CLAUDE.md rule 6).

Things that will break it, all of which look identical on screen:

- **`—` is an em dash (U+2014), not a hyphen.** Copy the section headers from this file; do not
  retype them.
- A trailing space after a title.
- "Uber's" with a curly apostrophe where the map has a straight one. Copy, don't retype.
- Changing "don't like my job" to "do not like my job".
- Dropping the full stop at the end of a statement.

Nothing is lost when this happens — the raw submission is mirrored to `data/temp/` **before** the
database is touched, so you fix the map or the Form and replay it:

```bash
python src/twinlab/ingest/replay_temp.py --apply
```

**Before you send the Form to a single driver**, fill it in yourself once and confirm you get a
`200` with a `twin_id`. §5 below has a dry-run that does not need a driver.

---

## 1. Shape of the Form

**112 questions across 22 sections**, in this order:

| Section | Questions | What it is |
|---|---|---|
| Part 1 | 8 | Eligibility screeners |
| Part 2 | 8 | Consent — statement 7 is the one that decides whether a twin exists |
| Part 3 | 9 | Demographics and work |
| Part 4 | 5 | Background |
| Parts 5–13 | 42 | The batteries the twin re-answers |
| Part 14 | 5 | Own words |
| Part 15 | 1 | Manipulation check |
| Part 16 | 16 | Holdout H2 — the same batteries under a story |
| Part 17 ×6 | 18 | Holdout H3 — six versions, three questions each |

Parts 15, 16 and 17 are **holdout material**. They never enter a persona (I6) — Part 17 is exactly
what the twin fidelity test scores against, so a twin that had read its own answers could not be
validated. The code enforces this; you do not have to do anything except keep them in the Form.

### Settings to set before you build

| Setting | Value | Why |
|---|---|---|
| Collect email addresses | **Off** | `twin_id` is the Form's own response id. The design claims anonymity; an email column would break that claim. |
| Limit to 1 response | **Off** | It requires sign-in, which collects identity. |
| Allow response editing | **On** | This is the only way the driver gets a stable link back to their submission, which is what the 14-day withdrawal right needs. |
| Progress bar | On | It is a long form. |
| Shuffle question order | **Off** | Row order inside a grid is fixed by the instrument. |
| Confirmation message | see below | |

Suggested confirmation message:

> Thank you. Your answers have been sent.
>
> **Save the link on this page.** It is the only way to find your response again if you want to
> withdraw it within 14 days.

**An honest limitation:** the survey document says the driver "will see a reference number". Google
Forms cannot print a dynamic value on the confirmation screen. The edit-response link is the
closest equivalent and is unique per submission. If a visible reference number is a requirement of
your ethics approval, tell me and I will add a route that looks a response up and returns a short
code — but it cannot be done in Forms alone.

### Language — English only for this round

**Decided: one Form, in English.** Hindi and Marathi are not being built for now.

This costs the pipeline nothing. `language` is recorded on `survey_responses.language` as metadata
and **nothing reads it** — not the persona builder, not the metrics. `translations` (bracketed
English of a non-English free-text answer) stays empty, which is correct when there is nothing to
translate.

**Do not change any question title to reflect this**, and in particular leave these two exactly as
written:

- Part 1 — *"Can you read English, Hindi, or Marathi well enough to complete this questionnaire on
  your own?"*
- Part 3 — *"In which language are you completing this survey?"*

Two reasons. They are the map keys, so editing one is a 422 until the map is edited to match. More
importantly they are the wording in the approved instrument, and narrowing an approved eligibility
question is an ethics decision, not a formatting one.

**One optional change that is free:** restrict the Part 3 language question's *options* to
`English` alone. Option text is never matched against anything, so this cannot break intake. It is
worth doing — otherwise a driver can tick "Hindi" on an English form and you have a metadata value
that contradicts the Form it came from.

**When translations are added later**, put them in each question's **description** (the grey help
text under the title) in the same Form, rather than building a second Form. The Apps Script sends
only the title, so descriptions are free text. Three separate Forms would need three
`form_map.yaml` files and a small change to pick one by `form_id` — doable, not built, and not
worth it unless you have a reason to keep the response sets apart.

---

## 2. How Likert blocks are built

Every scale item is a **row of a "Multiple choice grid"**, not its own question. That is what keeps
the Form to a reasonable length.

For each grid:

- **Grid title**: free text. Use the instruction line from the survey document, e.g. *"Please
  select the number that best matches your experience."* The script ignores it.
- **Rows**: the statements, **exact**, in the order given below. These are what get matched.
- **Columns**: the numbers `1`, `2`, … `7` (or `1`…`5`). **Columns must be numbers, not words** —
  intake parses the answer as a scale point and raises if it cannot.
- Put the anchor words in the grid's **description**: *"1 = Strongly disagree · 7 = Strongly
  agree"*.
- **Require a response in each row**: on.

Where a section mixes scales it needs one grid per scale — that is why Part 12 and Part 16 are
listed below with more than one grid.

**Two rows are attention checks** (`AMQ6` in Part 5, `ALGO5` in Part 11). They are human
data-quality devices and are never put to a twin (I10). Keep them exactly as written, in position.

---

## 3. Section by section

Copy the header and the titles from here. `Maps to` is for your reference; it never appears in the
Form.


### Section header (exact): `PART 1 — A FEW QUICK CHECKS`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | Are you aged 18 years or above? | Multiple choice — Yes / No | `screen:age_18_plus` |
| 2 | Have you driven with Uber, by cab, auto rickshaw, or motorcycle, for at least three continuous months up to today? | Multiple choice — Yes / No | `screen:tenure_3_months` |
| 3 | Has the Uber Driver app, on your own device, given you trip requests in the last 30 days? | Multiple choice — Yes / No | `screen:active_30_days` |
| 4 | Can you read English, Hindi, or Marathi well enough to complete this questionnaire on your own? | Multiple choice — Yes / No | `screen:reads_survey_language` |
| 5 | Are you in India at present? | Multiple choice — Yes / No | `screen:in_india` |
| 6 | Are you a salaried employee on Uber's own payroll (for example ground or engineering staff)? | Multiple choice — Yes / No | `screen:uber_employee` |
| 7 | Have you taken part in an earlier stage of this research? | Multiple choice — Yes / No | `screen:earlier_stage` |
| 8 | Is your Uber account deactivated or suspended at present for a reason other than a voluntary pause? | Multiple choice — Yes / No | `screen:deactivated` |


### Section header (exact): `PART 2 — YOUR AGREEMENT`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | I have read and understood the information about this research on this sheet. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_1` |
| 2 | I understand my participation is voluntary and I can withdraw at any time during the survey without giving a reason. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_2` |
| 3 | I understand I can withdraw my responses within 14 days of completing the survey by writing to the principal investigator. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_3` |
| 4 | I understand my responses will be anonymised and used only for academic research on algorithmic management of gig workers. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_4` |
| 5 | I understand my data will be retained in encrypted form for five years and then destroyed. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_5` |
| 6 | I confirm I am aged 18 years or above and meet the eligibility criteria set out in Section II. | Checkboxes — one option, "I agree". **Required.** | `consent:statement_6` |
| 7 | I agree that my survey answers, including my answers in my own words, may be used to build an anonymised computer model that answers research questions in the way I might. I understand that the model will be used only for this research and that I can ask for it to be deleted within 14 days of completing the survey. | Checkboxes — one option, "I agree". **Required.** | `consent:twin` |
| 8 | Do you agree to take part? | Multiple choice — Yes, I agree to take part / No, I do not agree. End the survey. | `consent:participate` |


### Section header (exact): `PART 3 — ABOUT YOU AND YOUR WORK`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | Which Uber service do you drive for most? | Multiple choice — Cab (Uber Go or Premier) / Auto rickshaw / Motorcycle | `field:service` |
| 2 | In which city do you usually drive? | Multiple choice — Mumbai / Pune / Delhi NCR / Jaipur / Bengaluru | `field:city` |
| 3 | For how many years have you driven with Uber? | Short answer — number of years | `field:tenure_years` |
| 4 | In a typical week, how many hours do you work through platform apps? | Short answer — number of hours | `field:hours_per_week` |
| 5 | From how many platform apps do you receive tasks at present? | Multiple choice — 1 / 2 / 3 or more | `background:platform_count` |
| 6 | Which other ride or delivery apps, if any, do you also use for work? | Short answer — free text (may be left blank) | `background:other_apps` |
| 7 | What is your age in completed years? | Short answer — age in completed years | `field:age` |
| 8 | How do you describe your gender? | Multiple choice — Woman / Man / Another identity / Prefer not to say | `field:gender` |
| 9 | In which language are you completing this survey? | Multiple choice — English / Hindi / Marathi | `meta:language` |


### Section header (exact): `PART 4 — YOUR BACKGROUND`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | How do you have the vehicle you drive? | Multiple choice — Own outright / Own with a loan / Rent from an Uber fleet partner / Rent from someone else | `background:vehicle_arrangement` |
| 2 | How many people depend on your earnings? | Short answer — number of people | `background:dependants` |
| 3 | Apart from platform work, what other income does your household have? | Multiple choice — None / Another member's job / My other work / Other | `background:other_household_income` |
| 4 | What is the highest level of education you have completed? | Multiple choice — Up to class 10 / Class 12 / Diploma / Graduate or above | `background:education` |
| 5 | How many years did you drive for a living before joining Uber? | Short answer — number of years | `background:years_driving_before_uber` |


### Section header (exact): `PART 5 — THE APP AND YOUR WORK`

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (6):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | An automated system tracks me carefully to ensure I am completing my tasks. | `AMQ1` |
| 2 | My daily tasks are assigned by an automated system. | `AMQ2` |
| 3 | My work schedule is made by an automated system. | `AMQ3` |
| 4 | The evaluation of my work performance is handled by an electronic system. | `AMQ4` |
| 5 | A large part of my compensation is determined by an automated system. | `AMQ5` |
| 6 | To show you are reading carefully, please select 2 for this statement. **← attention check, keep it exactly as written** | `AMQ6` |


### Section header (exact): `PART 6 — HOW THE APP GUIDES YOU`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | What makes you feel the app controls, or does not control, how you work? | Paragraph — optional | `why:WHY_CONTROL` |

**Grid — `agree5` — 5 points, 1 = Strongly disagree · 5 = Strongly agree.** Columns `1`…`5`. Rows, in this order (11):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | The algorithm assigns my tasks intelligently. | `PAC1` |
| 2 | The algorithm provides normative instructions for my work according to the platform standard. | `PAC2` |
| 3 | The algorithm provides me with considerable information support related to the completion of work tasks. | `PAC3` |
| 4 | The algorithm provides me with real time feedback on performance information. | `PAC4` |
| 5 | The algorithm tracks my location in real time. | `PAC5` |
| 6 | The algorithm keeps track of my work progress. | `PAC6` |
| 7 | The algorithm tracks my work attitude in real time. | `PAC7` |
| 8 | The algorithm automatically evaluates the quality of my service. | `PAC8` |
| 9 | The algorithm ranks me according to my performance. | `PAC9` |
| 10 | The algorithm provides me a monetary incentive to work hard for a specific period. | `PAC10` |
| 11 | The algorithm imposes a fine on me if I fail to comply with the platform's requirements. | `PAC11` |


### Section header (exact): `PART 7 — HOW FAIR THE APP IS`

**Grid — `extent7` — 7 points, 1 = To a very small extent · 7 = To a very large extent.** Columns `1`…`7`. Rows, in this order (4):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Do you consider that the app's matching procedures are based on accurate information? | `FAIR1` |
| 2 | Have you been able to express your views and feelings during the evaluation procedure? | `FAIR2` |
| 3 | Are you able to appeal the rides assigned to you by the app? | `FAIR3` |
| 4 | Do you consider that the app's matching procedures are free of bias? | `FAIR4` |


### Section header (exact): `PART 8 — HOW CLEAR THE APP IS`

**Grid — `agree5` — 5 points, 1 = Strongly disagree · 5 = Strongly agree.** Columns `1`…`5`. Rows, in this order (3):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I think I could understand the decision making process of platform algorithms very well. | `CLAR1` |
| 2 | I think I can see through platform algorithms' decision making process. | `CLAR2` |
| 3 | I think the decision making process of platform algorithms are clear and transparent. | `CLAR3` |


### Section header (exact): `PART 9 — YOUR JOB`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | What is the main reason for your satisfaction rating? | Paragraph — optional | `why:WHY_SATISFACTION` |

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (3):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | All in all, I am satisfied with my job. | `SAT1` |
| 2 | In general, I don't like my job. | `SAT2` |
| 3 | In general, I like working here. | `SAT3` |


### Section header (exact): `PART 10 — STAYING WITH UBER`

**Grid — `agree5` — 5 points, 1 = Strongly disagree · 5 = Strongly agree.** Columns `1`…`5`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I hope this job will continue in the future. | `CONT1` |
| 2 | I hope my job will continue in the future. | `CONT2` |


### Section header (exact): `PART 11 — WORKING AROUND THE APP`

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (5):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I do not enjoy working under the supervision of algorithms. | `ALGO1` |
| 2 | I experience the platform's algorithms as unfair. | `ALGO2` |
| 3 | I would rather have more human management than algorithmic management. | `ALGO3` |
| 4 | I deliberately change my behavior to get assigned better tasks by the platform's algorithm. | `ALGO4` |
| 5 | To show you are reading carefully, please select 6 for this statement. **← attention check, keep it exactly as written** | `ALGO5` |


### Section header (exact): `PART 12 — LEAVING UBER`

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I will probably look for a new job in the next year. | `TURN1` |
| 2 | I often think about quitting. | `TURN2` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | How likely is it that you will actively look for a new job in the next year? | `TURN3` |


### Section header (exact): `PART 13 — YOUR INCOME`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | Why is finding other work easy or hard for you? | Paragraph — optional | `why:WHY_OTHER_WORK` |

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I can easily get another job outside the platform economy if I want to. | `DEP1` |
| 2 | To maintain the standard of living I desire for myself, I must keep working via a platform. | `DEP2` |


### Section header (exact): `PART 14 — YOUR WORK IN YOUR OWN WORDS`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | Describe your least difficult day driving with Uber. What happened, and what did you do? | Paragraph — optional | `own_words:OWN1` |
| 2 | In your own words, how does the Uber app decide what a trip pays and which driver gets it? | Paragraph — optional | `own_words:OWN2` |
| 3 | Tell us about a time you needed help from Uber, or your account was blocked or penalised. How was it handled? | Paragraph — optional | `own_words:OWN3` |
| 4 | What do you and other drivers do when you have a problem with the platform? | Paragraph — optional | `own_words:OWN4` |
| 5 | Who depends on your earnings, and where do you see yourself in a year or two? | Paragraph — optional | `own_words:OWN5` |


### Section header (exact): `PART 15 — IMAGINE A CHANGE`

| # | Question title (exact) | Type | Maps to |
|---|---|---|---|
| 1 | Which change did the story describe? Please tick one. | Multiple choice — No change / Human appeals with no penalty for complaints / Safety equipment, training, and accident cover / A drivers' forum and union recognition | `check:manipulation` |


### Section header (exact): `PART 16 — IMAGINING THE STORY IS TRUE`

**Grid — `extent7` — 7 points, 1 = To a very small extent · 7 = To a very large extent.** Columns `1`…`7`. Rows, in this order (4):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Do you consider that the app's matching procedures are based on accurate information? | `H2_FAIR1` |
| 2 | Have you been able to express your views and feelings during the evaluation procedure? | `H2_FAIR2` |
| 3 | Are you able to appeal the rides assigned to you by the app? | `H2_FAIR3` |
| 4 | Do you consider that the app's matching procedures are free of bias? | `H2_FAIR4` |

**Grid — `agree7` — 7 points, 1 = Strongly disagree · 7 = Strongly agree.** Columns `1`…`7`. Rows, in this order (9):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | All in all, I am satisfied with my job. | `H2_SAT1` |
| 2 | In general, I don't like my job. | `H2_SAT2` |
| 3 | In general, I like working here. | `H2_SAT3` |
| 4 | I do not enjoy working under the supervision of algorithms. | `H2_ALGO1` |
| 5 | I experience the platform's algorithms as unfair. | `H2_ALGO2` |
| 6 | I would rather have more human management than algorithmic management. | `H2_ALGO3` |
| 7 | I deliberately change my behavior to get assigned better tasks by the platform's algorithm. | `H2_ALGO4` |
| 8 | I will probably look for a new job in the next year. | `H2_TURN1` |
| 9 | I often think about quitting. | `H2_TURN2` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | How likely is it that you will actively look for a new job in the next year? | `H2_TURN3` |

**Grid — `agree5` — 5 points, 1 = Strongly disagree · 5 = Strongly agree.** Columns `1`…`5`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | I hope this job will continue in the future. | `H2_CONT1` |
| 2 | I hope my job will continue in the future. | `H2_CONT2` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 1 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V1_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V1_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V1_KEEP` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 2 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V2_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V2_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V2_KEEP` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 3 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V3_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V3_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V3_KEEP` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 4 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V4_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V4_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V4_KEEP` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 5 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V5_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V5_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V5_KEEP` |


### Section header (exact): `PART 17 — SIX VERSIONS — Version 6 of 6`

**Grid — `fair7` — 7 points, 1 = Very unfair · 7 = Very fair.** Columns `1`…`7`. Rows, in this order (1):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how fair would the app's decisions be for you? | `H3_V6_FAIR` |

**Grid — `likely7` — 7 points, 1 = Not at all likely · 7 = Extremely likely.** Columns `1`…`7`. Rows, in this order (2):

| # | Row label (exact) | Maps to |
|---|---|---|
| 1 | Under this version, how likely would you be to push back against or work around the app? | `H3_V6_PUSH` |
| 2 | Under this version, how likely would you be to keep driving with Uber? | `H3_V6_KEEP` |


---

## 4. Section descriptions to paste

These are **descriptions**, not titles. Nothing matches against them, so wording drift here is
harmless — but they carry the experimental stimulus, so copy them from
`additional_data/Survey_Research_GIGWORKER_v2.md` rather than paraphrasing.

| Section | Paste into its description | From |
|---|---|---|
| Part 15 | The "Imagine that this is true…" story | survey doc, Part 15 |
| Part 16 | The **same** story again, plus "Please answer every statement again, as if the story were true." | survey doc, Part 16 |
| Part 17 — Version 1 of 6 | The five-lever "This version of Uber" block | survey doc, Part 17 → Version 1 of 6 |
| Part 17 — Version 2 of 6 | same, Version 2 | survey doc → Version 2 of 6 |
| Part 17 — Version 3 of 6 | same, Version 3 | survey doc → Version 3 of 6 |
| Part 17 — Version 4 of 6 | same, Version 4 | survey doc → Version 4 of 6 |
| Part 17 — Version 5 of 6 | same, Version 5 | survey doc → Version 5 of 6 |
| Part 17 — Version 6 of 6 | same, Version 6 | survey doc → Version 6 of 6 |

The six Part 17 versions are the version codes `12220`, `00222`, `11010`, `11211`, `02211`,
`02200` in that order. That mapping is frozen in `data/reference/instrument.json`
(`version_shown` / `version_code`) and the quality test relies on it, so **do not reorder the six
sections** and do not swap a narrative between them. If the narratives ever need rewording, the
lever text must still describe the same code.

The cover sheet (participant information) goes in the Form's own description, above Part 1.

---

## 5. Wiring it to Twin Lab

### 5.0 Order of operations

The useful thing to know before you start: **verifying the mapping needs no server at all.** The
`printKeys` function below runs entirely inside Apps Script and just prints what the Form would
send. So build and check the Form first, and only then worry about where it posts to.

| Phase | What you do | Server needed? |
|---|---|---|
| **A. Build** | Create the Form from §3. Fill it in yourself once. | no |
| **B. Verify the mapping** | Paste the script, run `printKeys`, diff its 112 lines against `config/form_map.yaml`. | no |
| **C. Stand up an endpoint** | Either a tunnel to your machine, or a Space. | — |
| **D. Wire and prove** | Set the secret and `ENDPOINT`, run `testWithLastResponse`, read the persona. | yes |
| **E. Go live** | Add the installable trigger, send the link to drivers. | yes |

Do not skip B. It is the cheapest possible moment to catch a stray em dash, and a mapping error
found in phase B costs a minute where the same error found in phase E costs a re-run.

#### Endpoint options for phase C

You need a public HTTPS URL, because Apps Script runs on Google's servers and cannot reach
`localhost`. Two ways:

**A tunnel to your own machine** — fastest, right for testing and for a small pilot.
`cloudflared` is already installed on this machine; one script starts both halves:

```bash
powershell -ExecutionPolicy Bypass -File tools\start_tunnel.ps1
```

It starts `uvicorn` on 127.0.0.1:7860, waits for `/api/health`, then opens a quick tunnel and
prints a `https://*.trycloudflare.com` URL. That host plus `/api/survey/intake` is your
`ENDPOINT`. Ctrl+C stops both and the URL stops resolving.

**While it runs the URL is public** — random and unlisted, but anyone holding it reaches your
local Twin Lab, the whole JSON API included, not just the intake route. Close it when you are done
testing. A fresh URL is issued each time, so update `intake.gs` whenever you restart it.

**A Hugging Face Space** — right once drivers are submitting unattended. See `docs/SETUP.md` §6.

Either way, a submission that arrives while the endpoint is down is **not lost**: Google keeps
every response in the Form's own responses sheet, the Apps Script emails you the failure, and you
re-post it afterwards.

### 5.1 Set the shared secret

You generated `INTAKE_HMAC_SECRET` in `docs/SETUP.md` §3. The **same** value goes in three places:

1. `.env` on whichever machine serves the endpoint,
2. the Space's secrets, if you deploy,
3. the Apps Script's **Script Properties** (below) — never pasted into the code itself.

If they disagree, every submission is rejected with 401.

### 5.2 Add the script

In the Form: **⋮ → Apps Script**. Delete the placeholder and paste this.

```javascript
/**
 * Twin Lab survey intake.
 *
 * Posts each submission to /api/survey/intake, signed with HMAC-SHA256 over the raw body.
 * The section a question sits in is part of its key, because question titles repeat: Part 16
 * re-asks Part 9's questions and Part 17 asks the same three questions six times.
 */

// The Space URL, or http://localhost:7860 while testing through a tunnel.
const ENDPOINT = 'https://REPLACE-ME.hf.space/api/survey/intake';

// Items before the first page break belong to this section.
const FIRST_SECTION = 'PART 1 — A FEW QUICK CHECKS';

function onFormSubmit(e) {
  const payload = buildPayload(e.response);
  postToTwinLab(payload);
}

/** Response -> the JSON body the intake route expects. */
function buildPayload(response) {
  const sectionByItemId = buildSectionIndex(FormApp.getActiveForm());
  const answers = [];

  response.getItemResponses().forEach(function (itemResponse) {
    const item = itemResponse.getItem();
    const section = sectionByItemId[item.getId()] || FIRST_SECTION;
    const value = itemResponse.getResponse();
    const type = item.getType();

    if (type === FormApp.ItemType.GRID) {
      // One answer per row, keyed by the row label: that is what form_map.yaml holds.
      const rows = item.asGridItem().getRows();
      for (var i = 0; i < rows.length; i++) {
        if (value[i] === null || value[i] === '') continue;
        answers.push({ section: section, title: rows[i], value: value[i] });
      }
    } else if (type === FormApp.ItemType.CHECKBOX_GRID) {
      const rows = item.asCheckboxGridItem().getRows();
      for (var j = 0; j < rows.length; j++) {
        if (!value[j] || value[j].length === 0) continue;
        answers.push({ section: section, title: rows[j], value: value[j] });
      }
    } else {
      answers.push({ section: section, title: item.getTitle(), value: value });
    }
  });

  return {
    response_id: response.getId(),
    submitted_at: response.getTimestamp().toISOString(),
    answers: answers
  };
}

/** item id -> the section header it sits under. Page breaks are the section boundaries. */
function buildSectionIndex(form) {
  const index = {};
  var current = FIRST_SECTION;
  form.getItems().forEach(function (item) {
    if (item.getType() === FormApp.ItemType.PAGE_BREAK) {
      current = item.getTitle();
    } else {
      index[item.getId()] = current;
    }
  });
  return index;
}

function postToTwinLab(payload) {
  const secret = PropertiesService.getScriptProperties()
    .getProperty('INTAKE_HMAC_SECRET');
  if (!secret) {
    throw new Error('Script property INTAKE_HMAC_SECRET is not set.');
  }

  const body = JSON.stringify(payload);
  const response = UrlFetchApp.fetch(ENDPOINT, {
    method: 'post',
    contentType: 'application/json',
    payload: body,
    headers: { 'X-Signature': hmacHex(body, secret) },
    muteHttpExceptions: true
  });

  const code = response.getResponseCode();
  if (code !== 200) {
    // Throwing makes it visible in Executions and in the failure-notification email.
    throw new Error('Twin Lab intake failed (' + code + '): ' + response.getContentText());
  }
  console.log('intake ok: ' + response.getContentText());
}

/** Hex HMAC-SHA256 over the exact UTF-8 bytes of the body, matching hmac.new(...).hexdigest(). */
function hmacHex(message, key) {
  const signature = Utilities.computeHmacSha256Signature(
    Utilities.newBlob(message).getBytes(),
    Utilities.newBlob(key).getBytes()
  );
  return signature.map(function (byte) {
    const value = (byte < 0 ? byte + 256 : byte).toString(16);
    return value.length === 1 ? '0' + value : value;
  }).join('');
}

/**
 * Run this by hand before going live. Posts the most recent real submission again.
 * Intake is idempotent on response_id, so re-posting is safe.
 */
function testWithLastResponse() {
  const responses = FormApp.getActiveForm().getResponses();
  if (responses.length === 0) {
    throw new Error('Fill the form in once yourself first.');
  }
  postToTwinLab(buildPayload(responses[responses.length - 1]));
}

/** Prints every "<section>|<title>" key the form will send. Diff this against form_map.yaml. */
function printKeys() {
  const responses = FormApp.getActiveForm().getResponses();
  if (responses.length === 0) {
    throw new Error('Fill the form in once yourself first.');
  }
  const payload = buildPayload(responses[responses.length - 1]);
  payload.answers.forEach(function (a) {
    console.log(a.section + '|' + a.title);
  });
  console.log(payload.answers.length + ' answers');
}
```

### 5.3 Set the script property

Apps Script editor → **⚙ Project Settings** → *Script Properties* → Add:

| Property | Value |
|---|---|
| `INTAKE_HMAC_SECRET` | the same 64-character hex string as `.env` |

Then set `ENDPOINT` at the top of the script to your Space URL.

### 5.4 Add the trigger

**It must be an installable trigger.** The simple `onFormSubmit(e)` name alone will not work,
because `UrlFetchApp` needs authorisation that only an installable trigger carries.

Apps Script editor → **⏰ Triggers** → *Add Trigger*:

| Field | Value |
|---|---|
| Function | `onFormSubmit` |
| Event source | From form |
| Event type | On form submit |
| Failure notification | **Immediately** |

Authorise it when prompted. "Failure notification: immediately" is the safety net — if intake
starts rejecting submissions you find out the same day, not at analysis time.

### 5.5 Prove it works, in this order

1. **Fill the Form in yourself**, end to end, ticking consent statement 7.
2. In the Apps Script editor run **`printKeys`**. It prints 112 keys. Diff them against
   `config/form_map.yaml` — every printed line must appear there.
3. Run **`testWithLastResponse`**. Expect `intake ok: {"status":"ok","twin_id":"…"}`.
4. In Twin Lab, open the **Twins** tab. Your submission is there, with a reconstructed persona.
5. Open the side panel and read the passage. Check it against what you actually answered. **This
   is the one moment where a human can catch a mapping error that no test can** — a question mapped
   to the wrong item id produces a passage that is fluent, plausible and wrong.
6. Fill the Form in again **without** ticking consent statement 7. Expect
   `{"status":"stored","twin_id":null}`, and no new twin on the Twins tab.

If step 2 shows a key that is not in the map, fix whichever is wrong — usually a dash or an
apostrophe — and re-run. Nothing is lost while you do this.

---

## 6. What the request looks like

For reference, and for anyone testing with `curl`:

```
POST /api/survey/intake
Content-Type: application/json
X-Signature: <hex hmac-sha256 of the raw body, keyed with INTAKE_HMAC_SECRET>
```

```json
{
  "response_id": "2_ABaOnud...",
  "submitted_at": "2026-09-23T09:41:02.000Z",
  "answers": [
    {
      "section": "PART 3 — ABOUT YOU AND YOUR WORK",
      "title": "Which Uber service do you drive for most?",
      "value": "Cab (Uber Go or Premier)"
    },
    {
      "section": "PART 5 — THE APP AND YOUR WORK",
      "title": "An automated system tracks me carefully to ensure I am completing my tasks.",
      "value": "6"
    }
  ]
}
```

`response_id` becomes `twin_id`. It is a Google-generated opaque string and carries no identity.

### Responses

| Code | Meaning | What to do |
|---|---|---|
| `200` `{"status":"ok","twin_id":…}` | Stored, consent given, persona built | nothing |
| `200` `{"status":"stored","twin_id":null}` | Stored in full, consent statement 7 not given, no twin | nothing — this is correct behaviour |
| `401` | Signature missing or wrong | the secret differs between the script and the server |
| `422` | A question is not in `form_map.yaml` — the body names it | add the row, then `replay_temp.py --apply` |
| `503` | `INTAKE_HMAC_SECRET` not set on the server | set it and restart |

Every one of these, `401` aside, has already written the raw body to `data/temp/`. Nothing a driver
submits is ever lost to a mapping mistake.

---

## 7. Decisions in here that are mine, not yours

Three things the specification did not fix, which I had to decide to make the Form buildable.
**Tell me if you want any of them different** — each is a small change now and an expensive one
after drivers have started submitting.

1. **`answers` is a list of `{section, title, value}`, keyed on section + title.** Titles are not
   unique — `SAT1` and `H2_SAT1` have the same wording, and Part 17 repeats three titles six
   times. The alternative is keying on the Form's internal item ids, which would be robust against
   re-wording but unreadable in the map and tied to one Form.
2. **Part 1 screeners and Part 15's manipulation check are recorded in the mirror only.** They are
   mapped, so they are accepted, but no database column exists for them and nothing infers from
   them. Only consent statement 7 gates whether a twin is built. If you want eligibility to
   exclude a response, that is a research decision and I have not made it.
3. **One Form in English with translations as help text.** See §1.
