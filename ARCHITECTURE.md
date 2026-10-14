---
title: "Twin Lab — system architecture"
project: "Digital Platform Algorithmic Management: attrition and voice of gig workers in India"
version: "2.0"
date: 2026-09-28
supersedes: "1.0 (2026-09-22)"
status: build specification
target: "A coding agent should be able to build the whole platform from this document set without further design decisions."
---

# Twin Lab — system architecture

A researcher workbench that tests 243 versions of Uber's rules on digital twins of real drivers.

## 0. Read this first

This document set is **normative**. Where it states a number, a name, a formula or an order, that
is the specification — do not improvise an alternative. Three markers appear throughout:

- **CONFIG** — the value lives in `config/` or the `app_config` table and is changeable from the UI
  without a code edit.
- **ASSUMPTION** — a decision taken in the absence of instruction, flagged for the researcher.
- **VERIFY** — a claim about an external service that was true on 2026-09-28 and must be re-checked
  before the first live run.

| Doc | Covers |
|---|---|
| `ARCHITECTURE.md` (this) | System map, invariants, stack, layout, execution model, deployment |
| `docs/00_RESEARCH_OVERVIEW.md` | The *why*. Non-normative orientation. |
| `docs/01_DATA_MODEL.md` | Reference data, the item register, the legacy crosswalk, full Postgres DDL |
| `docs/02_AGENTS_AND_PROMPTS.md` | The five agents, prompt architecture, the structured-output contract |
| `docs/03_RESEARCH_PIPELINE.md` | Lookup → render → check → ask → score. Controls, arms, holdouts. |
| `docs/04_BACKEND.md` | Service layer, orchestrator state machine, jobs, rate limiting, resume, caching |
| `docs/05_DESIGN_SYSTEM.md` | Tokens, typography, motion, component inventory, states, accessibility |
| `docs/06_SCREENS.md` | Screen-by-screen contract for all eight sections |
| `docs/07_STATISTICS.md` | Every formula: metrics, shifts, index, interactions, the PLS-SEM battery |
| `docs/08_VALIDATION_AND_VALIDITY.md` | The quality gate, the two holdouts, the eight validity tests |
| `docs/09_REPRODUCIBILITY.md` | Determinism contract, seeds, freezing, hashing, the provenance chain |
| `docs/10_SCALE_AND_COST.md` | The capacity model, credit budget, degradation ladder |
| `docs/11_BUILD_PLAN.md` | Ordered milestones with acceptance tests |
| `docs/DECISIONS.md` | Every judgement call already made, and why |
| `CLAUDE.md` | Rules for the coding agent |

**This version supersedes 1.0.** What changed and why is in `docs/DECISIONS.md` § "Revamp 2026-09".
The research design is unchanged. The stack, the execution model, the UI surface and the
deployment target changed, because four external facts turned out not to be what 1.0 assumed
(§3.2, §7, §8).

## 1. What the system does

A gig driver fills in a survey. Python deterministically turns that one survey row into a
**persona passage** — a first-person account of that driver, lossless, no LLM. The passage grounds
a **digital twin**.

Separately, Uber India's published policy has been coded against the Fairwork Location-based
Platform Work Principles. Uber scores **0 of 10**. Thirty criteria are unmet, and each unmet
criterion carries a **commitment**: the specific thing that would close it.

A **version code** is five digits, one per Fairwork principle, each 0, 1 or 2. It selects a set of
those commitments. The system renders that set into driver-facing scenario text in Uber's voice,
shows it to every twin alongside the twin's own baseline answers, and asks the twin to re-answer
the 37-item battery. Python measures the shift and reports which combinations of policy change
move driver fairness, satisfaction, voice and turnover — and whether they add up.

3⁵ = **243 version codes**.

```
 survey row ──► persona passage ──► TWIN
                                      │
 codebook ──► GapSpec ──► DeltaSpec ──► scenario text ──► round prompt ──► 37 answers
              (frozen)    (frozen)      (rendered)                            │
                                                                              ▼
                                                          baseline vs variant ──► metrics ──► index
```

### 1.1 Three principles that shape every screen

**The chain is the product.** A reviewer must be able to walk backwards from an index value to a
verbatim extract of Uber's own published policy without a gap. The UI exists to make that chain
inspectable, not to hide it behind a Run button. Every screen that shows a number must be able to
show where the number came from.

**Configuration is data, and the researcher owns it.** Models, prompts, thresholds, weights, run
limits, wording variants, sample sizes and agent behaviour are all editable from the frontend by
someone with no engineering background, versioned on write, and frozen onto every run that used
them. Adding a sixth agent is a row and a prompt file, not a deployment.

**Fail loudly and stop.** Numbers here go into a peer-reviewed paper. A bug that makes the UI ugly
costs an afternoon; a bug that lets threshold 2.2 language into an `01000` render, or records a
zero-twin run as a result, silently invalidates the study. Every ambiguity resolves toward halting.

## 2. Invariants

These exist because the study's validity rests on them. A change here is a research decision, not
an engineering one. **Never relax one to make a test pass.** `tests/test_invariants.py` carries one
executable test per invariant, each naming the invariant in its docstring.

**I1 — The treatment is frozen and deterministic.** `version_code → DeltaSpec` is a pure lookup
over `dial_lookup.json` and `gaps.json`. No model is consulted. Identical input, byte-identical
output, every run, forever.

**I2 — The design agent renders, it never proposes.** It receives a DeltaSpec and emits prose. It
has **no tools** and cannot fetch a gap, a chunk or a criterion. If it could, an `01000` render
could absorb threshold 2.2 material and `01000` would stop differing from `02000`.

**I3 — Containment is enforced, not trusted.** Every render passes the Checker before any twin
sees it. A commitment outside the DeltaSpec appearing in the text is recorded on the report.
*(Amended 2026-10-04, researcher decision: containment hits are reported, not enforced, because
predefined commitments can legitimately share wording. Coverage remains enforced.)*

**I4 — Lever paragraphs are cached on `(lever, dial, style_version)`.** There are exactly **10**
non-zero paragraphs plus one fixed zero string. All 243 cells are assembled from those 11 strings.
The design agent runs 10 times per style version, not 243.

**I5 — Dial 0 is a fixed string.** `"No change from today."` — never generated, byte-identical
everywhere.

**I6 — The persona holds every battery item and no holdout material.** All 37 battery items
contribute at least one clause; a survey field with no template raises rather than being skipped.
Survey Parts 15, 16 and 17 are excluded absolutely. A twin that has read its own holdout answers
cannot be validated. *(Changed in 2.0: there is no item-level holdout. See `docs/DECISIONS.md`.)*

**I7 — The persona carries words, not numbers.** A `5` on a 7-point agreement item becomes
"I somewhat agree that…", never "I rated this 5 out of 7". A twin shown numbers does arithmetic
instead of reasoning from experience.

**I8 — Persona and round prompt are separate documents.** The persona holds whys and open-ended
answers. The round prompt holds the scenario text, the twin's own baseline **numbers**, and the
battery to re-answer — and nothing else. Keeping them apart is what stops a twin restating its own
justifications under every counterfactual.

**I9 — Nothing is overwritten.** `runs`, `run_events`, `twin_answers`, `twin_quality_runs` and
`validity_results` are append-only. "Latest" is a pointer flipped in the same transaction. A rerun
supersedes; it does not erase.

**I10 — Attention checks are never put to a twin.** `AMQ6` and `ALGO5` are human data-quality
devices. The twin battery is 37 items, not 39.

**I11 — Everything a twin or agent is shown is reproducible.** Store the lever-order seed, the
persona hash, the delta hash, the style version, the wording variant, the prompt version and the
model name on every run. The exact prompt is never stored — it is *rebuilt* from these.

**I12 — No model ever produces a metric.** Metrics, shifts, the index, interactions and every
statistic are computed in Python. The analyst agent writes prose *about* numbers it is handed and
may not quote a figure absent from its input bundle.

**I13 — Provider schemas are never trusted.** Ollama Cloud accepts a JSON schema and silently does
not enforce it (§3.2). Every model output is validated in Python against the item register: exactly
the expected item ids, each within *its own* scale range. A malformed answer is retried, then
failed. It is never coerced, padded, truncated or rounded into validity.

**I14 — The analysis panel is frozen per study.** The twins that enter a sweep are drawn once,
stored on the session, and are identical in every cell. A cell answered by a different set of twins
is a different experiment and cannot be compared or differenced against the others.

**I15 — A run with no twins is a failure, not a result.** `twins_n = 0` marks the run `failed`.
It is never written as `completed` with an index of 0.000. The same applies to a validity test: a
test that ran on zero twins reports `INCONCLUSIVE`, never `PASS`.

**I16 — Nothing durable lives on the filesystem.** The Space's disk is ephemeral and resets on
every restart. Evidence is written to Postgres or Supabase Storage *before* it is acknowledged to
the caller.

**I17 — Nothing is imputed.** An interaction needs three completed cells; with two, the system
reports which code to run. No estimates, no interpolation, no "approximately".

## 3. Stack

| Layer | Choice | Note |
|---|---|---|
| UI | **Gradio 5.x**, native multipage | `demo.route()` + `gr.Navbar`. See §3.3. |
| Server | **FastAPI** | Optional wrapper over the service layer. Never load-bearing — §8.2. |
| Agents | **pydantic-ai 2.x** | `OllamaModel` + `OllamaProvider`. Typed outputs, validated in Python. |
| LLM | **Ollama Cloud** | `https://ollama.com/v1`, key `OLLAMA_API_KEY`. Model is CONFIG. |
| DB | **Supabase** (Postgres + PostgREST) | `supabase-py`. Free tier: 500 MB, 1 GB storage. |
| Intake | **Supabase Edge Function** | Outside the Space, so a sleeping Space cannot drop a survey. |
| Statistics | **`openpls-engine`** | GPL-3.0. Validated against SmartPLS 4 — §3.4. |
| Telemetry | **Pydantic Logfire** | Optional. The UI reads `run_events` from Postgres, not Logfire. |
| Deploy | **HF Space, Gradio SDK on ZeroGPU** | Python 3.13. Portable to Docker — §8. |

`supabase` is imported in exactly one file: `db/client.py`. SQL lives only in `db/`.

### 3.1 Licence note

`openpls-engine` is **GPL-3.0**, inherited from `plspm-python`. Linking it makes this application
GPL-3.0. This is accepted knowingly for an academic research instrument, and the repository
licence must say so. If the platform is ever to be released under a permissive licence, the
statistics engine has to move out of process (a separate service or an offline script).

### 3.2 The structured-output problem — read this before writing an agent

Ollama's documentation states that structured outputs do not work on Cloud. pydantic-ai's is
blunter:

> Ollama Cloud's inference backend accepts `response_format` with `json_schema` **without error but
> does not apply grammar-constrained decoding, so schemas are silently not enforced.**

This is the most dangerous failure mode in the stack, because it looks like success. A twin
returning 35 items instead of 37, or a `6` on a 5-point scale, would pass straight through if the
provider were trusted.

Consequences, all binding:

- **`NativeOutput` is forbidden.** pydantic-ai auto-detects `ollama.com` URLs and raises
  `UserError`; do not work around it. Use `ToolOutput` (default) or `PromptedOutput`.
- **Validation is a Python responsibility** (I13). The ladder is: parse → normalise → validate
  against the item register → bounded retry → hard fail. It is specified once, in
  `docs/02_AGENTS_AND_PROMPTS.md` §5, and used by every agent.
- **Prefer a flat output shape.** A model that is not grammar-constrained produces flat key–value
  output far more reliably than nested JSON. The twin returns one item id per key, nothing nested.
- **A failed twin fails that cell only.** It is not dropped from the study (§7.4).

**VERIFY** before the first live run: re-read the pydantic-ai Ollama page. If Cloud gains
grammar-constrained decoding, `NativeOutput` becomes available and the retry budget can drop — but
I13 stays, because the Python-side check is also what enforces per-item scale ranges, which no
provider schema expresses.

### 3.3 What Gradio can and cannot do here

Gradio 5 is a better fit than 1.0 assumed. It has **native multipage routing**: `demo.route()`
creates a real URL per page with an auto-generated `gr.Navbar`, sharing one backend and one queue.
The prototype's eight-section navbar maps onto eight routes, and every screen is deep-linkable —
no visibility-toggle hacks at the top level.

**Cannot be done natively:** drag-to-resize panel splitters; a freely draggable window layout;
true virtualised infinite log scroll.

**Will be done instead, and must not be skipped:**

- **Collapsible** → `gr.Accordion`.
- **Scrollable within container** → `elem_classes` + CSS `max-height` + `overflow-y: auto`.
- **Resizable** → CSS `resize: vertical` on the wrapper. Vertical axis only; horizontal
  proportions come from `gr.Column(scale=…)`.
- **Live log stream** → `gr.Timer` polling `run_events` with `after_id`, rendering an HTML tree.
  Not websockets. Poll interval is CONFIG.
- **243-cell grid with hover and click** → Plotly heatmap in `gr.Plot` with `.select()`, falling
  back to a styled `gr.Dataframe` if `.select()` misbehaves on the pinned version. Never ship a
  grid without click handling.
- **Sub-tabs inside a section** (Twin Lab's eight, Statistics' ten) → `gr.Tabs`, not routes, so
  section state survives tab changes.

**Every piece of content and every ordering in `docs/06_SCREENS.md` is mandatory.** Styling may
degrade; content may not. If a layout cannot be achieved, render the content in a plainer
container — never drop it, never reorder it, and record the degradation in `docs/DECISIONS.md`.

### 3.4 Why an external PLS-SEM engine and not our own

The Statistics section reports Cronbach's α, ρ_A, composite reliability, AVE, HTMT with confidence
intervals, Fornell–Larcker, inner and outer VIF, outer loadings, bootstrapped path coefficients,
specific indirect and total effects, R²/f²/Q², PLSpredict and model fit. Hand-rolling that is a
research-grade numerical project in which a wrong bootstrap resampling scheme invalidates the
paper silently.

`openpls-engine` is a maintained fork of Google's `plspm-python` that covers the whole battery and
ships a published validation: agreement with SmartPLS 4 across 14 canonical reference models
(ECSI, ACSI, TAM, UTAUT, Corporate Reputation and others) to **|Δ| < 0.001** on every path
coefficient, R², indicator loading, outer weight and HTMT ratio, for the path-weighting scheme.
It has an SSRN validation paper and a Zenodo DOI, so the method section can cite the engine.

**The obligation this does not remove:** `docs/07_STATISTICS.md` §9 specifies a golden-dataset
regression test that runs in CI against stored reference values. We cite someone else's validation;
we still prove our wiring of it is correct.

## 4. Repository layout

```
twinlab/
├─ app.py                       # Gradio-SDK entrypoint: builds the Blocks, demo.launch()
├─ app_docker.py                # Docker entrypoint: FastAPI + gr.mount_gradio_app  (§8.2)
├─ README.md                    # HF Space card: sdk gradio, python_version 3.13, hf_oauth
├─ pyproject.toml  requirements.txt  Dockerfile
├─ ARCHITECTURE.md  CLAUDE.md  docs/
│
├─ config/
│  ├─ settings.py               # pydantic-settings; env + defaults
│  ├─ agents.default.yaml       # seed AgentConfig rows
│  ├─ twin.default.yaml         # seed TwinConfig
│  ├─ style_contract.yaml       # the design agent's style contract, versioned
│  ├─ analysis.default.yaml     # metric weights, bootstrap defaults, screening rules
│  ├─ generator.default.yaml    # synthetic survey generator presets
│  └─ form_map.yaml             # "<section>|<title>" → item_id for all 112 Form questions
│
├─ data/reference/              # FROZEN. Generated once, committed, never written by the app.
│  ├─ criteria.json  (33)              criterion_findings.json  (33)
│  ├─ gaps.json      (30)              thresholds.json          (10)
│  ├─ corpus_chunks.json (126)         chunk_criterion_links.json (171)
│  ├─ instrument.json (73 items, 5 scales, 6 metrics, 9 constructs)
│  ├─ dial_lookup.json (5 × 3)         arms.json (4 human arms → version codes)
│  └─ legacy_crosswalk.json            # prototype item/construct ids ↔ canonical ids
│
├─ supabase/functions/survey_intake/   # Edge Function: HMAC verify → Storage mirror → insert
│
├─ src/twinlab/
│  ├─ models/                   # ALL Pydantic models. No model defined anywhere else.
│  │  reference.py  twin.py  variant.py  run.py  analysis.py  agent.py
│  │  stats.py  validity.py  generator.py  api.py
│  ├─ db/
│  │  client.py                 # the ONLY supabase import
│  │  repo_*.py                 # one repository per aggregate; no SQL outside db/
│  │  migrations/
│  ├─ ingest/
│  │  build_reference.py        # source .md/.docx → data/reference/*.json, byte-stable
│  │  seed_db.py                # reference → Postgres, idempotent
│  │  survey_intake.py          # payload → survey_responses (shared with the Edge Function)
│  │  replay_raw.py             # re-drive any mirrored payload
│  ├─ persona/
│  │  templates.py              # one clause template per item. Frozen, versioned.
│  │  builder.py                # deterministic passage builder + hash
│  ├─ variant/
│  │  lookup.py                 # version_code → DeltaSpec            (I1)
│  │  render.py                 # DeltaSpec → lever paragraphs        (I4)
│  │  checker.py                # coverage, containment, invariance   (I3)
│  ├─ agents/
│  │  registry.py               # AgentConfig → pydantic-ai Agent; SCHEMA_/TOOL_REGISTRY
│  │  contract.py               # THE validation ladder               (I13)
│  │  manager.py  design.py  twin.py  checker.py  analyst.py
│  │  prompts/                  # *.md, versioned, loaded by name and hashed onto every run
│  ├─ orchestrator/
│  │  loop.py                   # the session state machine
│  │  odometer.py               # index ↔ version_code
│  │  panel.py                  # frozen analysis panel selection     (I14)
│  │  budget.py                 # pre-flight call/token/time estimate (§7.3)
│  │  events.py                 # emit() → run_events
│  ├─ analysis/
│  │  metrics.py  interactions.py  report.py
│  ├─ stats/
│  │  dataset.py                # population selection, screening, export matrix
│  │  plssem.py                 # openpls-engine wrapper
│  │  golden.py                 # reference-value regression harness  (§3.4)
│  ├─ validity/
│  │  tests.py                  # the eight validity tests, one function each
│  ├─ generator/
│  │  synthetic.py              # seeded synthetic survey generation
│  ├─ services/                 # the only layer the UI and the API both touch
│  │  dashboard.py  surveys.py  twins.py  quality.py  validation.py
│  │  validity.py  versions.py  sessions.py  results.py  studio.py
│  │  agents.py  config.py  stats.py  research.py
│  ├─ api/                      # thin FastAPI routers over services/. Optional. (§8.2)
│  └─ ui/
│     ├─ app.py                 # gr.Blocks root, demo.route() per section
│     ├─ theme.py               # tokens, CSS, motion
│     ├─ components/            # REUSABLE. See docs/05_DESIGN_SYSTEM.md.
│     └─ pages/
│        main_menu.py  driver_survey.py  generator.py  studio.py
│        agent_studio.py  statistics.py  research_model.py
│        lab/                   # agents dials twins validation validity
│                               # fieldwork results settings
└─ tests/
   ├─ test_invariants.py        # I1..I17 as executable tests
   └─ ...
```

**Layer boundaries** (enforced by an import-linter test in CI):

| Layer | May import | May not |
|---|---|---|
| `ui/` | `services/`, `models/` | `db/`, `agents/`, raw SQL |
| `api/` | `services/`, `models/` | `db/`, `agents/` |
| `services/` | everything below | `gradio`, `fastapi` |
| `agents/` | `models/` | `db/`, `ui/` |
| `db/` | `models/` | `agents/`, `ui/` |

**Rule:** a Pydantic model is declared once, in `src/twinlab/models/`. No dict-passing across a
layer boundary.

## 5. The version code

Five digits, **in this order**, left to right:

| Position | Lever | Fairwork principle | Thresholds |
|---|---|---|---|
| 1 | Pay | P1 Fair Pay | 1.1, 1.2 |
| 2 | Conditions | P2 Fair Conditions | 2.1, 2.2 |
| 3 | Contracts | P3 Fair Contracts | 3.1, 3.2 |
| 4 | Management | P4 Fair Management | 4.1, 4.2 |
| 5 | Representation | P5 Fair Representation | 5.1, 5.2 |

Digit meaning: `0` = no change · `1` = close the gaps under threshold X.1 · `2` = close X.1 ∪ X.2.
The cumulative rule mirrors Fairwork's own gating — the second point is unawardable without the
first — which is what makes 0/1/2 ordinal and legitimate rather than three arbitrary labels.

**Fairwork score = digit sum** (0–10). `21122` → 8.

Gaps per dial, frozen in `dial_lookup.json`:

| Lever | dial 1 | dial 2 | Already met, so never a gap |
|---|---|---|---|
| L1 Pay | 1.1.a, 1.1.b | + 1.2.a → 3 | — |
| L2 Conditions | 2.1.a–c | + 2.2.a–c → 6 | — |
| L3 Contracts | 3.1.b, 3.1.d, 3.1.e, 3.1.f | + 3.2.a–d → 8 | **3.1.a, 3.1.c** |
| L4 Management | 4.1.a, 4.1.b, 4.1.d | + 4.2.a–e → 8 | **4.1.c** |
| L5 Representation | 5.1.a–c | + 5.2.a–b → 5 | — |

`00000` closes nothing. `22222` closes all thirty.

### 5.1 Odometer order

Base-3, **Representation least significant**. This matches the Results grid: rows are
`pay × conditions` (9), columns are `contracts × management × representation` (27).

```python
def code_from_index(i: int) -> str:            # 0 <= i < 243
    return "".join(str((i // 3**p) % 3) for p in (4, 3, 2, 1, 0))

def index_from_code(code: str) -> int:
    return sum(int(d) * 3**p for d, p in zip(code, (4, 3, 2, 1, 0)))
```

`0 → "00000"`, `1 → "00001"`, `3 → "00010"`, `81 → "10000"`, `242 → "22222"`.

**ASSUMPTION — sweep start.** `00000` runs **once per session as the control cell** and does not
consume an iteration; the odometer sweep proper starts at `start_code` (CONFIG, default `"10000"`,
index 81). Setting `start_code: "00000"` makes it a plain sweep from index 0. This is why the
prototype's status card reads *"versions tested 7 of 242"* rather than 243. Confirm before the
first real run.

### 5.2 The two twin control cells

Exactly two. **No third is ever added** — each extra arm is a researcher degree of freedom, and
eliminating those is the point of the design.

| Cell | DeltaSpec | Renders as | Measures |
|---|---|---|---|
| `00000` | empty | five `"No change from today."` lines, byte-identical | the twin's **noise floor** under a null stimulus |
| `SHAM` | the three criteria coded **Met**: `3.1.a`, `3.1.c`, `4.1.c` | five ordinary paragraphs, same word band and voice as a live cell | **demand characteristics** — movement caused by being shown change-shaped text |

The sham has zero free parameters: its commitment set is read from `criterion_findings.json`, not
chosen. `SHAM − 00000` is the demand-characteristic floor and is reported alongside every live
cell. Any cell whose shift is smaller than that floor is **not interpretable**, and the analyst is
instructed to say so.

**Where the controls are answered (RESEARCHER 2026-10-05).** Each twin answers `00000` and `SHAM`
once per config, inside the twin quality test (`docs/08` §2.1 step 6). A session never asks them: it
records each control from its panel's stored answers under its own config fingerprint, so the
floors are the same measurement the versions get, at no per-session cost. A twin with no control
answer under the live config is not qualified, and a session cannot start or resume on it.

### 5.3 The four human arms

Distinct from the twin control cells, and easy to confuse with them. The *human* survey is a
four-arm between-subjects design: each respondent is assigned one arm, sees that arm's story in
Part 15, and re-answers 16 items in Part 16. Arms are balanced within `city|service` strata.

| Arm | Story shown | Version code |
|---|---|---|
| `BASE` | no change | `00000` |
| `MGT1` | human appeals with no penalty for complaints | `00010` |
| `CON1` | safety equipment, training, accident cover | `01000` |
| `REP1` | a drivers' forum and union recognition | `00001` |

Frozen in `data/reference/arms.json`. **The mapping is derived, not assumed** — each non-control
arm's Part 15 story matches its lever's dial-1 commitment set term for term, and Part 16's story
text is `5.1.a` + `5.1.b` rendered near-verbatim. The derivation and its seed assertion are in
`docs/01` §5.1.

Two consequences:

1. **H2 validation is per-arm.** A twin is scored on Part 16 by being shown *its own driver's arm*,
   rendered through the normal pipeline. Showing a twin a different arm than its human saw is a
   bug, not a variation.
2. **`BASE` is the human noise floor**, mirroring the twin's `00000`. A quarter of respondents
   re-answered after being told nothing changed, which bounds human response instability the same
   way `00000` bounds the twin's.

Part 15 is a manipulation check on the human: it asks which change the story described, with the
four arm descriptions as options. It is registered as `MC1` and captured as `mc_answer`. Whether
failing it screens a respondent out is **OPEN** (§10).

## 6. Data flow

### 6.1 Ingestion — once, then frozen

```
Fairwork_LocationBased_Principles_verbatim.md ─┐
Fairwork_Uber_India_Codebook_v2.docx          ─┼─► ingest/build_reference.py ─► data/reference/*.json
Uber_India_Policy_Corpus_Fairwork_Levers.md   ─┤                                        │
Survey_Research_GIGWORKER_v2.md               ─┘                        ingest/seed_db.py ─► Postgres
```

The builder is **byte-stable**: same sources in, same bytes out, verified by hash. It asserts every
count — 33 criteria, 30 gaps, 126 chunks, 171 links, 73 items. A count mismatch is a build failure,
not a warning. `--check` exits non-zero if anything drifted. `seed_db.py` is idempotent.

### 6.2 Survey intake — outside the Space

The Space sleeps after 48 hours idle. A sleeping Space would silently drop driver submissions,
which is unacceptable during fieldwork. Intake therefore does not live in the Space:

```
Google Form ──► Apps Script onFormSubmit ──► Supabase Edge Function  (HMAC-signed)
                                                    │
                          ┌─────────────────────────┴───────────────────┐
                          ▼                                             ▼
        Supabase Storage: raw/survey_<id>.json          survey_responses + twins
             (immutable mirror, written FIRST)                          │
                                                                        ▼
                                                    persona builder ─► twins.persona_passage
```

The mirror is written **before** any table write (I16), so a failed insert leaves a replayable
object. An unmapped Form question is a **422**, never a dropped answer. Intake requires consent
statement 7 (`consent_twin`); without it the response is stored and never becomes a twin.

The Edge Function and `ingest/survey_intake.py` share one mapping contract (`config/form_map.yaml`)
and one test fixture, so they cannot drift.

### 6.3 A session

```
create session
  ├─ freeze config + draw the analysis panel        (I14 — once, stored on the session)
  ├─ reconstruction   build any missing personas
  ├─ control: 00000   the noise floor
  ├─ control: SHAM    the demand-characteristic floor
  └─ for each version code in odometer(start, n):
       ├─ lookup    → DeltaSpec           deterministic, no model
       ├─ render    → 5 lever paragraphs  cached on (lever, dial, style_version)
       ├─ check     → CheckerReport       gate; a failure halts this cell only
       ├─ ask       → 37 answers × K twins  cached on (twin, code, style, wording)
       └─ analyse   → metrics, index, prose  Python first, model last
     checkpoint after every single unit
```

## 7. The execution model

This section is load-bearing. 1.0 assumed a concurrency the provider does not offer, and the
difference is the difference between a feasible study and an unaffordable one.

### 7.1 One request at a time

**VERIFY.** As of 2026-09-28 the Ollama Cloud free tier permits **1 concurrent request**. Pro is 3;
Max and Team are 10. Excess requests queue, and once the queue fills they are rejected. There is no
published RPM or TPM; usage is metered in credits against per-model token rates, resetting monthly,
with session limits every 5 hours and weekly limits every 7 days.

So `max_concurrency` (CONFIG) defaults to **1**, and every twin call is serial. The bounded worker
pool still exists — it is how the value becomes 3 or 10 on a paid plan without a code change — but
it must be correct at 1.

### 7.2 What that costs

At a measured ~8 s per twin call (≈2,300 tokens in, ≈400 out on a 120B-class cloud model):

| Panel K | Twin calls per sweep | Serial hours | Days | M tokens |
|---:|---:|---:|---:|---:|
| **20** (default) | 4,860 | 10.8 | 0.5 | 13.1 |
| 50 | 12,150 | 27.0 | 1.1 | 32.8 |
| 100 | 24,300 | 54.0 | 2.2 | 65.6 |
| 500 | 121,500 | 270.0 | 11.2 | 328.1 |

The quality gate is separate and is paid on **every consented twin**, not just the panel: at 6
holdout versions × 3 repeats, 500 twins is **9,000 calls ≈ 20 hours**. Budget it explicitly; it is
the largest single cost before a sweep begins.

`docs/10_SCALE_AND_COST.md` carries the full model, the storage arithmetic and the degradation
ladder. Two rules from it belong here:

- **Never store a prompt body in `run_events`.** At K=500 that alone would exhaust the 500 MB tier.
  Payloads carry references and telemetry; the prompt is rebuilt from the stored seed, persona
  hash, lever order, style version and wording (I11).
- **Every long action is costed before it starts.** `orchestrator/budget.py` returns calls, tokens,
  estimated hours and estimated credits, and the UI shows it on the confirm step. No researcher
  should discover the cost of a sweep by running one.

### 7.3 The frozen analysis panel

500 twins in 243 cells is not affordable, and sampling per cell destroys the design: shifts are
within-subject, so `shift(A∪B) − (shift(A) + shift(B))` is meaningless if A, B and A∪B were
answered by different people.

The resolution (I14): draw a **stratified subsample of K quality-passed twins once**, at session
creation, balanced on `city × service`, seeded and stored on the session. Those exact K twins
answer every cell. K is CONFIG, default **20**.

All 500 twins are still collected, persona-built, quality-tested, and used in the Statistics
section — which analyses *human* survey rows and does not depend on the sweep at all. The panel
bounds only the counterfactual sweep.

A session records its panel; two sessions with different panels are not differenced against one
another without an explicit, logged decision.

### 7.4 Failure semantics

| Event | Consequence |
|---|---|
| Checker fails twice | That **cell** is `failed`, logged, the loop continues |
| Twin output fails validation twice | That **twin fails for that cell only**; it is not dropped from the study |
| Provider 429 / 5xx | Exponential backoff, 3 attempts, then that twin fails for that cell |
| Twin fails the quality gate | Dropped from the panel and from all cells, never tuned |
| `twins_n = 0` | Run `failed` (I15). Never a result. |
| Space restart mid-sweep | Session marked `paused` at boot; the researcher resumes. Never auto-restarted. |

Stop is **cooperative**: it sets a flag checked at every checkpoint and exits after the current
unit. It never kills mid-model-call, so no partial answer is ever written.

## 8. Deployment

### 8.1 The tier reality

**VERIFY.** As of 2026-09-28 Hugging Face requires a paid plan to create **Gradio or Docker**
Spaces. The exception: free personal accounts in good standing — verified email, account older
than 30 days — may host **up to 2 Gradio Spaces running on ZeroGPU**.

Target: **free account, Gradio SDK, ZeroGPU hardware, Python 3.13.**

ZeroGPU's daily GPU quota is irrelevant here. It meters time spent inside `@spaces.GPU`-decorated
functions; all inference is remote on Ollama Cloud, so **nothing is decorated and the `spaces`
package is never imported**. ZeroGPU is being used as a free CPU Space.

```yaml
# README.md
title: Twin Lab
sdk: gradio
python_version: "3.13"
app_file: app.py
hf_oauth: true
hf_oauth_authorized_org: <org>        # access control; replaces the prototype's passcode
startup_duration_timeout: 30m
```

Known environment facts, each of which the design already accommodates:

- **2 vCPU, 16 GB RAM.**
- **50 GB disk, ephemeral, resets on restart. Persistent storage has been withdrawn entirely** —
  the config key is documented as ignored. Hence I16.
- **Sleeps after 48 h idle** on free hardware. Hence intake living outside the Space (§6.2), and
  checkpoint-per-unit resume (§7.4).
- **Outbound traffic only on ports 80, 443 and 8080.**
- Secrets via Space settings, read as environment variables.

**Unverified risk.** ZeroGPU is built for request-scoped GPU bursts, not a multi-hour background
asyncio sweep. Whether a long-running task survives there is undocumented. **Smoke-test this in
M1**, before building on it. The mitigation is already in the design: checkpointing after every
cell means a restart costs one cell, not the sweep.

### 8.2 The four portability rules

Upgrading to PRO and the Docker SDK later must cost a commit, not a port — `sdk: docker` in the
README plus a Dockerfile, with hardware changed from a dropdown and no rebuild. That stays true
only if the build holds to these from day one. **They are binding constraints, not advice.**

1. **The UI is a plain `gr.Blocks` object** built by `ui.app.build_ui()`, with two thin
   entrypoints: `app.py` calling `demo.launch()`, and `app_docker.py` calling
   `gr.mount_gradio_app()`. Neither holds logic.
2. **Survey intake lives in the Edge Function**, never in the Space. This removes the only
   feature that genuinely required FastAPI routes.
3. **Every capability is a service-layer function.** `api/` is a thin optional wrapper over
   `services/`. No feature may depend on an HTTP route existing.
4. **Never import `spaces`; never decorate anything with `@spaces.GPU`.** Pin Python 3.13.

### 8.3 Environment

| Var | Required | Purpose |
|---|---|---|
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | yes | DB |
| `OLLAMA_API_KEY` | yes | LLM |
| `OLLAMA_BASE_URL` | no | default `https://ollama.com/v1` |
| `TWINLAB_MODEL` | no | default model name (CONFIG) |
| `INTAKE_HMAC_SECRET` | yes | shared by Apps Script and the Edge Function |
| `LOGFIRE_TOKEN` | no | telemetry; absent ⇒ disabled |

### 8.4 Free-tier realities to design around

- **Supabase free pauses after 7 days idle**; the first request after a pause takes 10–30 s. The DB
  client retries with backoff before surfacing an error. An active study never idles that long.
- **500 MB database.** The binding constraint is `run_events`, not answers — see §7.2.
- **Answers are stored as one JSON vector per (run, twin, wording)**, not one row per item. At 243
  cells × 20 twins × 37 items that is ~4,860 rows instead of ~180,000, and every read is one fetch.

## 9. Design language

The prototype is information-dense by design; it is a research console, not a consumer app.
Reproduce the **density and hierarchy**, not the Apps Script styling. Full tokens, type scale,
motion and the component inventory are in `docs/05_DESIGN_SYSTEM.md`.

```
--tl-blue-900  #0B1F3A   navbar, headings
--tl-blue-600  #1D4ED8   primary action, links, active tab
--tl-blue-50   #EFF5FF   selected row, info panel
--tl-green-600 #15803D   positive-for-driver shift, completed step, "Kept"
--tl-green-50  #ECFDF5   positive cell fill
--tl-amber-500 #F59E0B   in-progress, "cached" badge
--tl-red-600   #DC2626   negative-for-driver shift, "Dropped", error, dial 0
--tl-grey-700  #374151   body text
--tl-grey-200  #E5E7EB   borders, gridlines
```

Three rules that are easy to get wrong:

- **Dials are red / amber / green for 0 / 1 / 2** — a traffic light for protection level, matching
  the prototype and the legend `0 = as Uber is today · 1 = some protection · 2 = more protection`.
- **Metric bars are coloured by "good for the driver", not by sign.** A shift of −0.59 on *leaving*
  is **green** and extends left from a centre line. Getting this backwards inverts the headline
  finding on every screen.
- **Status never relies on colour alone.** Every dot, pill and cell carries a text label —
  `Kept (0.56)`, `Dropped (1.1)`, `PASS`, `FAIL`, `Not tested`.

Motion: 150 ms ease-out on hover and tab change, 200 ms on panel open, a 1.2 s pulse on the amber
running dot, and a cross-fade on route change. Transitions are CSS on `elem_classes`; they must
never gate the arrival of data, and must respect `prefers-reduced-motion`.

## 10. Open questions

Each has a working default and blocks nothing. Carry them forward; they belong in the paper's
limitations if they remain open at write-up.

1. **Sweep start** (§5.1) — `00000` as control plus a sweep from `10000`, or a plain sweep from
   index 0? *Default: the former.*
2. **Part 15 / `MC1`** (§5.3) — should failing the human manipulation check screen a respondent out
   of the analysable sample, as the attention checks do? **Decided 2026-09-28: the switch is built
   and defaults OFF.** `mc_answer` and `mc_correct` are captured on every submission, and the
   Fieldwork tab reports the failure rate, so the decision can be revisited with data rather than
   in advance. Revisiting it *after* seeing results is a researcher degree of freedom and must be
   recorded as one.
3. **The index mixes scale lengths.** Clarity and staying are 5-point; the other four are 7-point.
   The unweighted mean of six shifts is the **display** index, and per-metric shifts are stored so
   a standardised index can be computed at modelling time. *Default: display as-is, state it as a
   limitation.*
4. **Panel size K** (§7.3) — default 20, configurable. The full 243-cell sweep is **deferred**
   (`docs/10` §6, rung 5): the design, the odometer and the grid are built and the controls plus
   single-lever cells are runnable, but no full sweep is scheduled. Revisit K when the real Ollama
   credit allowance is known.
5. **Free credit allowance is unpublished.** It must be read off the account before the first
   sweep, and `budget.py` calibrated against it.
6. **ZeroGPU and long background tasks** (§8.1) — undocumented; smoke-test in M1.
7. **Bootstrap floor.** The prototype's UI blocks analysis below 30 bootstrap samples. 30 is far
   below reportable; PLS-SEM convention is 5,000, with 1,000 an absolute floor. *Default: keep 30
   as the hard UI floor for compatibility, default to 5,000, and warn below 1,000.*
