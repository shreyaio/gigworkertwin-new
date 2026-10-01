# 06 — Screens

Screen-by-screen contract for all eight sections.

**Content and ordering in this document are mandatory.** Styling may degrade where Gradio cannot do
something; content may not. If a layout is unachievable, render the same content in a plainer
container — never drop it, never reorder it, and record the degradation in `docs/DECISIONS.md`.

Components referenced here are defined in `docs/05_DESIGN_SYSTEM.md` §4.

---

## 0. Navigation

Eight routes, in this order. Gradio 5 `demo.route()` with `gr.Navbar`.

| Order | Label | Route |
|---:|---|---|
| 1 | Main menu | `/` |
| 2 | Driver survey | `/survey` |
| 3 | Twin Lab | `/lab` |
| 4 | Generator | `/generator` |
| 5 | Twin Studio | `/studio` |
| 6 | Agent Studio | `/agents` |
| 7 | Statistics | `/statistics` |
| 8 | Research model | `/research` |

**Google Sheet is removed.** It was the prototype's database interface; Supabase replaces it. No
top-level item, no card, no link, and no user-facing text saying "sheet".

Twin Lab carries a second-level `gr.Tabs` in this order:

```
Agents · Dial board · Twins · Validation · Validity tests · Fieldwork · Results · Settings
```

Active route gets a coloured underline; active sub-tab gets its own. The header shows the app
title, the subtitle *Uber Driver Study with Digital Twins*, and a model badge reading
`Mock model` or `Live: <model name>`.

---

## 1. Main menu — `/`

The researcher's landing page and the application map. Not a dashboard — the primary entry point
into every workflow, grouped by research stage.

### 1.1 "What do you want to do?"

Seven groups, each a `section_card` of link cards. Every card: **title · one-line description ·
destination**.

| Group | Cards → destination |
|---|---|
| **Collect answers** | Send the survey to a driver → `/survey` · Make synthetic surveys for testing → `/generator` · Watch fieldwork → `/lab` Fieldwork |
| **Build and test the twins** | Import twins from the survey → `/lab` Settings · Run the twin quality test → `/lab` Agents · Look inside one twin → `/lab` Twins · Interview one twin in your own words → `/studio` |
| **Check the twins can be trusted** | Validation against each driver → `/lab` Validation · The eight validity tests → `/lab` Validity tests |
| **Explore the 243 versions** | Turn the dials and ask the twins → `/lab` Dial board · Let the agents choose what to test → `/lab` Agents · Read the results → `/lab` Results |
| **Analyse and export** | Reliability and correlations → `/statistics` · The PLS-SEM path model → `/statistics` · Export for SmartPLS, R or Python → `/statistics` Export |
| **Write the paper** | Research model, constructs and hypotheses → `/research` · Write it all to a document → `/research` |
| **Set up and manage** | Model, speed and sample settings → `/lab` Settings · Agent instructions and the freeze → `/agents` |

### 1.2 "Open an app directly"

Seven cards — one per route except Main menu — each with title, audience line and a blue **Open**
button.

### 1.3 "Where things stand"

Live Supabase counts, two-column table:

| Metric | Value |
|---|---|
| Real surveys saved | count |
| Synthetic surveys saved | count |
| Twins built | count |
| Passed quality test | count of twins built |
| Versions tested | count **of 242** (excludes the `00000` control — §3.2) |
| Twin answers saved | count |
| Validation run | status + count |
| Validity tests run | count |
| Access | `HF OAuth · <org>` |

Counters flash `--tl-blue-50` on change.

### 1.4 Quick start, and help

An ordered list: create test data → import twins → run the quality test → check validation →
explore dials or let the agents choose → read results → run analysis and export.

Below it, a collapsible help area (`help_accordion`), retained from the prototype: turning on a live
model · a live run is slow or the provider refuses calls · a twin answer was refused · something is
missing after an update · before real fieldwork.

---

## 2. Driver survey — `/survey`

**UI required now; driver-facing integration is the existing Google Form.**

The page shows: what the instrument is (17 parts, three languages, 112 questions), the live intake
status (endpoint reachable, last submission received, submissions today), the four-arm assignment
balance by `city|service`, and the form link.

It does **not** host the survey. Intake runs in a Supabase Edge Function outside the Space
(`docs/04` §8) so a sleeping Space cannot drop a submission; this page reports on it.

If intake is not yet configured, show the placeholder — *"This area will host the real driver
survey. Survey integration is pending."* — in the application's own navigation and style.

**Research constraint to surface here:** Parts 15, 16 and 17 are holdout material and must never
enter a persona (I6). The page states this, because it is the instrument's most load-bearing
property.

---

## 3. Twin Lab — `/lab`

Header: **Twin Lab** · *Agents testing 243 versions of Uber's rules on driver twins* · model badge.

### 3.1 Agents tab

**Section: The five agents.** Five `agent_card`s side by side — Run Manager, Policy Designer, Twin
Interviewer, Quality Checker, Results Analyst — each with name, one-line description, `status_dot`
and latest operational text.

**Primary workflow buttons, in this exact order:**

```
1. Run twin quality test      (primary)
2. Let the agents choose 6 versions  (primary)
3. Test all 243 versions      (secondary)
```

Each opens a confirm step showing `budget_summary` — calls, tokens, estimated hours, estimated
credits (`docs/04` §5.4) — before anything starts.

**Card: Run without watching.** Five controls: *Quality test in the background · One dial at a time
· All remaining versions · Validation · Stop the background job*. Below them, the current job line
(`No background job running. Versions tested so far: 7.`). Stop is cooperative and says so.

**Panel: What the agents said.** Scrollable `log_tree`, columns `Time · Agent · Message`, polled by
`gr.Timer`. Rows are clickable and open `side_panel`. This is the audit trail, backed by
`run_events` — append-only, never replaced.

**Card: Status.** Compact two-column table: Twins · Passed quality test · Versions tested · Answers
saved · Best so far.

### 3.2 Dial board tab

```
┌── warning strip (red, only when code == 00000) ──────────────────────┐
│  Turn at least one dial above 0. 00000 is a control cell.            │
├─────────────────────────────────┬────────────────────────────────────┤
│ DIALS (scale=5)                 │ VERSION CODE (scale=4)             │
│  legend: 0 today · 1 some · 2 more                                   │
│  Pay            [0][1][2]       │        0 1 0 0 0                   │
│  Conditions     [0][1][2]       │   Fairwork score 1 of 10           │
│  Contracts      [0][1][2]       │                                    │
│  Management     [0][1][2]       │   What the twins are told          │
│  Representation [0][1][2]       │   • Conditions step 1. …           │
│  [ Ask the twins ]  + badge     │   (scrollable)                     │
├─────────────────────────────────┴────────────────────────────────────┤
│ Version 01000: change compared with Uber today (20 twins)            │
│ Fairness ▕▏ +0.00  Clarity ▕▎ +0.07  …        Index 0.143            │
└──────────────────────────────────────────────────────────────────────┘
```

**Changing a dial does no network work.** One handler recomputes the code, the Fairwork score and
"What the twins are told" from reference data already in process. It must feel instant.

**Ask the twins:** cache hit → render the result plus an amber `cached` badge and a **Rerun?**
button; miss → confirm with budget, create and start a session, poll, render on completion. A rerun
creates a real session visible in the Agents log and inherits the original panel (`docs/04` §6.1).

`00000` is **blocked** — it is a control the orchestrator runs.

Results block per `metric_bars` (`docs/05` §4.5): six rows, divergent bars coloured by
good-for-the-driver, then `Index X.XXX` and a plain sentence.

### 3.3 Twins tab

Full-width card at the top: **Run twin quality test →**, opening the quality page (§3.3.2).

Below it, list and side panel side by side.

**List columns, in order:** Twin · Service · City · Age · Quality. Quality is a pill from
`twin_quality_runs where is_latest and holdout_set='H3'` — green `Kept (0.56)`, red `Dropped (1.1)`.
Filters: source (real / synthetic / manual), city, service, quality.

**Side panel — exact order:**

1. Twin id and one-line identity — *Uber Go (cab) driver in Mumbai, 41 years, Man, 38 months on
   Uber, about 72 hours a week.*
2. Background line — *Full time cab driver repaying a car loan.*
3. Quality line — *Quality test: average error 0.56, 94% within 1 point.*
4. **Reconstructed persona** — `gr.Accordion`, collapsed; expands to the full passage as plain text,
   with `persona_hash`.
5. **Compare with version** — dropdown listing only codes with a completed run, newest first.
6. **Scenario text** for the selected version — so the reader sees what the twin was told *before*
   reading the answers.
7. **Answer comparison**, one table per construct block in battery order: Managed by the app ·
   Feels controlled · Fairness · Clarity · Job · Staying · Working around · Leaving · Income.

Comparison columns: **Item · Question · Driver · Twin today · Twin, version NNNNN**, where *Driver*
is the human's own survey answer, *Twin today* is the twin under `00000`, and the last is the twin
under the selected code.

A version with no run shows **`Not tested`** — never a fabricated number. Holdout items are marked
`hidden` under the item id.

#### 3.3.2 Quality page

Reached from the card; a `gr.Group` visibility swap with a **← Back to twins** button.

```
← Back to twins   [ Select ] [ Run selection ] [ Run all ]
┌──────────────────────────┬───────────────────────────────┐
│ TWIN LIST (checkboxes)   │ RUN LOG (log_tree, this job)  │
└──────────────────────────┴───────────────────────────────┘
```

*Select* adds a checkbox column; check order is preserved and is the run order. *Run all* runs every
consented twin — show its budget first, since at 500 twins this is ~20 hours (`docs/10`).

### 3.4 Validation tab

Header: **Validation: do twins answer like their drivers?** Primary button: **Check twins against
their drivers**.

**Summary card:**

| Row | Source |
|---|---|
| Survey twins checked | count |
| Part 16 (H2): average error on the 16 follow-up answers | mae + % within 1 |
| Part 17 (H3): average error on the six versions | mae |
| Part 17 (H3): twin and driver move together (r) | fairness r, pushback r, staying r |

> **Nomenclature.** The prototype's UI said *Part 10 / Part 10b / Part 9b*, its own survey
> numbering. The canonical instrument numbers these **16** and **17**. This document uses the
> canonical numbers and shows the legacy label in parentheses where a reader may be comparing to old
> screenshots. **Part 9b does not exist in 2.0** — the item-level holdout was dropped
> (`docs/DECISIONS.md`); that row is gone rather than renamed.

**Warning area.** Whenever the checked set includes synthetic twins or mock-model output, show it
prominently:

> Some of these twins come from synthetic surveys. The generator and the mock twin share the same
> built-in reaction rules, so validation on synthetic data always looks good. **It tests the
> machinery, not whether twins are valid.**

**Per-twin table**, horizontally scrollable: Twin · Arm seen · H2 error · Within 1 point ·
Versions · H3 error · Fairness r · Pushback r · Staying r.

The **Arm seen** column exists because H2 validation must show a twin *its own driver's arm*
(`docs/01` §5). A mismatch here is a bug, and the column is how it is caught.

### 3.5 Validity tests tab

Header: **Validity tests: can the twin answers be trusted?** Control: **Twins per test** (numeric).

Eight `validity_test_card`s, each with the question it asks, what it does, a `needs a live AI model`
badge where applicable, and **Run this test**. Definitions, statistics and pass rules are in
`docs/08` §4 — not restated here.

| # | Test | Question |
|---|---|---|
| 1 | Wrong person | Is a twin really about its own driver? |
| 2 | Placebo change | Do twins welcome any change at all? |
| 3 | Beating simple guesses | Do twins beat ordinary statistics? |
| 4 | Impossible version | Do twins notice a contradiction? |
| 5 | Order and wording swap | Are answers about the change, or about the words? |
| 6 | Leave out the fairness items | Does the twin use its memory? |
| 7 | A second AI model | Is the finding about the drivers or the model? |
| 8 | Temperature sweep | How much is chance? |

**Results so far** table: When · Test · Twins · Model · Result · Verdict. **Append-only** — every
completed test adds a row and never replaces one. Verdicts render as pills: `PASS` green, `FAIL`
red, `CHECK` amber, **`INCONCLUSIVE` grey**.

`INCONCLUSIVE` is mandatory and is shown whenever `twins_n = 0` (I15). The prototype recorded
live-mode `PASS` verdicts on zero twins; that must be impossible to display here.

### 3.6 Fieldwork tab

Header: **Fieldwork: how collection is going** · *Real driver surveys only. Targets assume 500
drivers across 5 cities and 3 services.* Button: **Refresh**.

**Surveys by city and service** — a matrix of real counts against target, with synthetic shown
separately and clearly labelled, plus an **Arm balance** sub-section (BASE / MGT1 / CON1 / REP1 by
stratum).

**Data quality and drop out** — Agreed to a twin (statement 7) · Failed an attention check ·
Finished in under 8 minutes · Straight-lined · Failed the manipulation check (Part 15) · Not
eligible · Did not consent.

Every one of these rows reads from `survey_submissions`, which is why respondents and twins are
separate entities (`docs/01` §6.2).

**Surveys per day** — a daily trend chart; `Nothing yet.` before the first real submission.

**Real fieldwork metrics never count synthetic rows.**

### 3.7 Results tab

Header: **Results** · *Every tested version compared with Uber today. Higher index means better for
drivers.*

**Grid — All 243 versions.** 9 rows (`pay × conditions`) × 27 columns
(`contracts × management × representation`). Untested cells grey; tested filled white→green by
index. `00000` has a **red outline** ("Uber today"); the best index has a **gold outline**. Hover
shows `version code · index`. Click opens the side panel.

**Panel: Do changes work together?** Computable interactions only (`docs/07` §5). Where a leg is
missing it **names the code to run** — never an estimate (I17).

**Tested versions table**, with a search box filtering on version code: Version · Score · Twins ·
Fairness · Clarity · Happiness · Staying · Pushback · Leaving · Index. Sorted by index descending,
scroll-capped. This table is also the accessible equivalent of the grid (`docs/05` §6).

**Side panel — exact order**, deliberately the same bundle the Analyst received, in the same order,
so the researcher can read input and output together:

1. Version code, large, with Fairwork score
2. What the twins are told
3. Scenario text — the five lever paragraphs actually rendered
4. Numeric results — six shifts, six baselines, index, `twins_n`, and the `SHAM − 00000` floor
5. Computable interactions involving this cell
6. Written analysis (`runs.llm_analysis`), with the *Generated summary* prefix where the
   deterministic fallback was used (`docs/02` §6.2)
7. Run metadata — session, panel hash, style version, prompt hash, model, timestamp, and a
   `provenance_link` to the run

### 3.8 Settings tab

Two columns.

**Left — Settings.** Twin model · AI provider · Model name · Temperature · Wordings · Runs per
wording · Quality test runs per twin · **Panel size (twins per sweep)** · Pause between AI calls ·
Token limit · Calls sent at once · **Save settings**.

Retain the prototype's long operational help text as a collapsible block, updated for reality:
calls-at-once is capped by the provider tier (free = 1), pause limits provider pressure, panel size
sets the sweep budget. Every change shows its effect on the budget estimate live.

Saving validates, writes a new `app_config` version, shows a success state, and records the version
id. **Completed runs stay associated with the config they ran under.**

**Right — Data.**

> Survey answers, twins, runs, results, validation and agent messages are stored in Supabase.

Which survey answers? — *Real and synthetic · Real only · Synthetic only*. **Import twins from the
survey** — imports eligible completed respondents, applies the consent gate, prevents duplicates,
builds personas, returns imported / skipped / invalid counts. **How many survey twins are
available?** — a live count.

**"Clear runs and load demo twins" is not a button.** Clearing `runs` deletes append-only evidence
(I9). The card says so where the prototype had the control.

---

## 4. Generator — `/generator`

**Synthetic Survey Generator.** Records get an ID beginning `SYN-` and `data_type = 'SYNTHETIC'`.

Two-column dashboard:

| Left | Right |
|---|---|
| **Batch** — how many · batch name · seed (same seed, same data) · share failing attention checks | **How they feel about the app** — presets *Frustrated · Mixed · Content*, plus 1–7 sliders |
| **Where they drive** — relative city weights: Mumbai, Pune, Delhi NCR, Jaipur, Bengaluru | **How strongly they react to each change** — one slider per lever (Pay, Conditions, Contracts, Management, Representation), `0 = no reaction · 1 = normal · 2 = strong` |
| **Who they are** — service mix (cab / auto / motorcycle) · age range · months-on-Uber range · hours-a-week range · share of women · use of other apps · vehicle on a loan · need the money (1–7) | Checkbox: *Drivers who need the money react more to a driver's forum* |

Sentiment sliders, visible labels: the app manages my work · I feel controlled · the app treats me
fairly · I understand how the app decides · I am happy with the job · I want to stay · I push back ·
I want to leave · how much drivers differ · shared overall mood · answer noise · appeals and forum
work together.

**Controls:** *Preview 3 drivers* (derives a preview only, inserts nothing) · *Generate surveys* ·
*Delete all synthetic surveys*.

Status line: `In the database now: X real surveys and Y synthetic surveys.` From Supabase.

**Generation must produce a complete submission** — all 73 items including why-probes, an assigned
arm, the 16 H2 answers and the 18 H3 answers — or the twin cannot be quality-tested. Why-text is
**templated and seeded, never LLM-generated**: at 500 rows × ~20 probes an LLM pass costs more than
a sweep, for text no number depends on.

Delete is confirmed, names the count, deletes only `data_type = 'SYNTHETIC'`, cascades to answers
and twins, and **never touches real rows or any run**.

> **Standing warning, shown on this page and on Validation:** synthetic drivers are generated by
> rules, and a mock twin shares those rules. Results on synthetic data test the machinery, not
> whether twins are valid.

---

## 5. Twin Studio — `/studio`

A sandbox for interrogating one twin in the researcher's own words. **Studio runs are quarantined**:
they never enter `runs`, never contribute to a metric, a shift, an index or the Results grid, and
never reach Statistics (`docs/01` §6.9).

Two cards, side by side.

**1. Make or choose a twin** — three modes, one active at a time:

- **Use a twin I have** — dropdown with service, city and quality. Non-passed twins may be inspected
  here; they can never enter the main study.
- **From a survey answer** — dropdown of **real respondents who consented to a twin only**.
  Synthetic rows must not appear in this selector. → *Create this twin*.
- **Make one by hand** — city · service · age · gender · months on Uber · hours a week · note, plus
  nine 1–7 sliders. → *Create this twin*, stored with `source = 'manual'`.

Secondary on all three: **Show what the twin is told**.

**2. Ask a what-if question** — the five dials (live version code) · *or write your own change* ·
*your questions for the twin (one per line, up to 5)* · checkbox *Also ask the 37 survey questions
and show the change* · **Ask the twin**.

**Result — What the twin said.** Metadata line `Twin · model · version`. Table: *What it measures ·
Now (1–7) · Uber today · Change · The twin's reason*, one row per construct. Expandable **The change
the twin was told about** showing the exact scenario text used. A mock-model warning where
applicable.

A custom change is free text and therefore **not a Fairwork treatment**: it bypasses the lookup and
the Checker, so its result is labelled *sandbox — not a study result* and is not comparable to any
cell.

---

## 6. Agent Studio — `/agents`

Configure and test each agent. **Not the execution engine** — the study runs from Twin Lab.

Left: five selectable `agent_card`s — Twin Interviewer · Policy Designer · Quality Checker · Results
Analyst · Run Manager.

Right: the active agent's configuration —

- Name and purpose
- **What this agent is told** — large textarea, the resolved prompt
- AI provider · Model name · Temperature · **Output mode** (`tool` / `prompted`; `native` is not
  offered — `docs/02` §5.1)
- **Save this agent** · **Put the original text back** · **Freeze for the main study**
- `Last saved: <timestamp>` · `Prompt version: v3 · hash 4f2a…`

**Rules everyone follows** (shared panel, below the agent card):

- *Checker rules* — keep a twin if average error at most `1.0` · at least `0.80` within 1 point ·
  times to ask again for a bad answer `1` · tries when rate limited `3`
- *Analyst score weights* — Fairness · Clarity · Happiness · Staying · Pushback · Leaving, each
  default `1`; `0` omits a metric from the index
- **Save rules** → new `app_config` version, recorded on every subsequent run, historical runs
  untouched

**Test this agent** — per agent, with a twin selector and a version field:

| Agent | Shows |
|---|---|
| Twin Interviewer | Instruction comparison (saved vs your edit) across the six metrics, plus a sample of the 37 answers as `Item · Question · Answer` |
| Policy Designer | `Dial · Setting · Text used` for all five levers, the Fairwork score, and the whole scenario in each wording |
| Quality Checker | Completeness and scale checks with pass/fail, the holdout error and share within 1 point, a `Held-out item · Driver said · Twin said` table, and the keep/drop decision |
| Results Analyst | The six shifts, the six baselines and the index **for the selected twin and version**, and the prose it wrote about them |
| Run Manager | A deterministic plan: twins in Supabase · twins kept by the quality test · wordings · runs per wording · AI calls for this version · calls at once · pause · estimated time · model |

**Run Manager's test button builds a plan; it never launches a sweep.**

**What was changed** — append-only log at the foot of every agent screen: `When · Agent · What was
saved`, from `agent_config_history`.

> The prototype labelled some agents `rules only` and one `uses AI`. Those badges described the
> prototype, not the architecture. Show each agent's **actual** model usage from its config.

---

## 7. Statistics — `/statistics`

Analysis over **human survey rows** — one row per respondent. It does not read the sweep.

**Control strip:** Which answers (*Synthetic only · Real drivers only · Real and synthetic*) ·
Bootstrap samples · Screening (*Drop attention failures, speeders, straight liners · Keep everyone*)
· **Run the analysis** · **Make an export sheet**.

**Gating:** analysis is blocked below **30** bootstrap samples, with an explanatory message. The
default is **5,000** and a warning shows below **1,000** — 30 is the prototype's floor, kept for
compatibility, and is far below reportable (`ARCHITECTURE.md` §10.7).

Long runs are staged: each of the nine computation stages persists on completion and is never
recomputed on resume (`docs/01` §6.8). Progress shows the current stage.

Ten tabs, in this order — formulas, columns and thresholds in `docs/07`:

```
Construct reliability and validity · Discriminant validity · Collinearity · Outer model
Path coefficients · Indirect and total effects · R², f², Q² · PLSpredict · Model fit · Export
```

Every table shows a legend above it and an `ok` / `check` status column against the published
threshold. Analysis output is **read-only** after computation.

**Export** replaces the prototype's Google Sheet: download CSV, download XLSX, copy the raw JSON
payload. One row per respondent, every item on its **own** scale — the prototype's claim that
everything was 1–7 was wrong against the instrument (`docs/01` §3.2), and the export carries a
scale row so a downstream tool cannot repeat the error.

Every result view displays `engine_version`, `n_cases`, `bootstrap_samples`, `seed` and the
screening rule, because the paper must state which implementation produced the numbers.

---

## 8. Research model — `/research`

Static research content, rendered from structured data rather than hardcoded prose.

Sections, in order:

1. **The model in one line** — plus summary cards: five dials · how the algorithm is seen · how the
   driver feels · what the driver does · who reacts differently.
2. **Research questions** — three cards (RQ1 governance configurations · RQ2 conditional responses
   under dependence · RQ3 validated simulation as an instrument), each with id, title, question,
   hypothesis references and contribution.
3. **Research model diagram** — the theoretical model (antecedent → algorithmic-management
   perceptions → justice perceptions → behavioural intentions).
4. **Measurement mapping** — **required, new in 2.0.** The theoretical diagram's constructs do not
   map one-to-one onto what the instrument fields. This table states how the nine measured
   constructs (EXPO, CTRL, FAIR, TRAN, SATI, LOYA, VOIC, EXIT, EDEP) operationalise the diagram.
   Without it, the Research Model page and the Statistics page appear to describe different studies.
5. **Hypotheses** — `Hypothesis ID · Statement · Support`.
6. **Research method** — `Part · What it involves`: design · sample · measures · the experiment
   inside the study · twin reconstruction · validation before use · design space · analysis · ethics
   and openness.
7. **Constructs and definitions** — `Construct · Definition · Where it comes from`, wide enough for
   citations.
8. **How this ties the validation together** — `Technique · What it assesses · Where it is used ·
   Paper section`, covering both holdouts and all eight validity tests.
9. **Reference list, grouped by theme** — empty-state until supplied. **Never fabricate a
   reference.** Rows carry theme, citation and DOI/URL.
10. **Write it all to a document** — generates the research document from this structured data,
    preserving tables and sections. A document export, not a database.

---

## 9. States, budgets and provenance — global

Three requirements that apply to every screen and are not repeated above.

**Seven states.** Loading · Empty · Ready · Running · Partial · Success · Error, per `docs/05` §5.
Empty states name the action that fixes them. Error states carry the `event_id`.

**Budget before every long action.** A sweep, a quality run, a validation run, a validity test and
an analysis all show `budget_summary` — calls, tokens, estimated hours, estimated credits — on the
confirm step before anything starts.

**Provenance from every number.** `provenance_link` beside a shift opens the run; beside a run, the
variant; beside a paragraph, the commitments and their corpus citations. Two clicks from any number
on any screen to Uber's own published words. This is the product, not a feature.
