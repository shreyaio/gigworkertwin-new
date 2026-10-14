# System audit and remediation plan — M19

**Written 2026-10-01 against commit `8ea2598`, verified against the live Supabase project.**

This document supersedes `ARCHITECTURE_UPDATE.md` (the M18 plan), which has been **executed**: §3.1
polling, §3.2 connection churn, §3.3 retry classification, §3.4 the delete pre-flight, §3.5 the
eligibility pre-flight, §3.6 the population control, §4 Twin Studio render-on-demand and the
`origin` column, §5.1–§5.6 the Agent Studio panels, and migration `004` are all in the code and
pass tests. Keep that file for its reasoning; do not work from its task list.

Read `CLAUDE.md` first, then §0 and §1 here.

Run everything with `./venv/Scripts/python.exe` and `PYTHONPATH="src;."`. On Windows prefix
anything that prints rendered prose with `PYTHONIOENCODING=utf-8`, and `PYDANTIC_AI_NO_BANNER=1`.

---

## 0. The one-paragraph version

The instrument is built, tested and internally consistent — **855 tests pass, `ruff` is clean, six
import-linter contracts hold, `build_reference --check` exits 0**. It is nonetheless unable to
produce a single number, and the reason is not a bug in the plumbing. It is that **one style
contract cannot carry a commitment set that ranges from 2 to 8 commitments**: the `L3` and `L4`
dial-2 paragraphs cannot state eight commitments inside a 150-word cap and be found to entail them,
so two of the ten lever paragraphs are permanently failing, their one durable re-render is spent,
and the failure has been cached into `variants` where nothing can clear it. Everything the
researcher has pressed since then — the quality gate, the Dial board, the Twin Studio, every live
validity test — is downstream of that one wall. This plan removes the wall, then fixes the eight
independent defects behind it that the wall has been hiding.

---

## 1. What the system actually is, verified

### 1.1 Shape

31,277 lines of Python across `src/twinlab/`, in the layering `ARCHITECTURE.md` §4 specifies and
CI enforces. One divergence from the specified layout, benign: `ui/pages/lab.py` is a single
1,551-line module rather than the specified `ui/pages/lab/` package. The eight Twin Lab tabs are
`gr.Tab`s inside it and their order is asserted against `services.menu.LAB_TABS` at build time
(`lab.py:1532`). Splitting it is housekeeping, not a defect; it is **not** in this plan.

| Area | Module | Lines | State |
|---|---|---:|---|
| Agents | `agents/` | 1,564 | Complete. Contract ladder, registry, five agents. |
| Variant pipeline | `variant/` | 957 | Complete. Lookup → render → five Checker gates. |
| Orchestrator | `orchestrator/` | 1,178 | Complete. State machine, odometer, panel, budget. |
| Services | `services/` | 8,595 | Complete; three wiring gaps (§2.6, §2.8, §2.9). |
| UI | `ui/` | ~5,300 | Complete; four dead or mis-wired controls (§2.5–§2.8). |
| Statistics / validity | `stats/`, `validity/` | 2,600 | Complete. Golden PLS-SEM test passes. |

### 1.2 Live database state, read 2026-10-01

```
twins                     50   (all source='synthetic')
survey_submissions        50
survey_answers         3,650
lever_paragraphs          13   (8 at v2, 5 at v1)
variants                   6   (5 passed, 1 FAILED — see §2.1)
runs                       0
twin_answers               0
twin_quality_runs          0
validity_results           0
session_panel              0
sessions                   4   (2 render completed, 1 quality FAILED, 1 ask FAILED)
studio_runs                1
agent_configs              5   (all gpt-oss:120b / ollama — the stale `mistral` row is gone)
app_config                 5
```

**Every evidence table is empty.** Nothing in this plan destroys a result, because there are no
results. That is the one piece of good news in the audit: the whole remediation can be done without
touching a single stored number.

### 1.3 What works today, confirmed by reading and by the suite

- The frozen reference data, the item register, the odometer, the persona builder, the metric and
  index arithmetic, the interaction logic, the PLS-SEM wrapper and its golden regression.
- The output contract ladder (`agents/contract.py`) — parse, normalise, validate against the
  register, one targeted repair, hard fail. Nothing coerces.
- All five Checker gates, including the two narrowings recorded in `docs/DECISIONS.md`.
- The durable paragraph cache, the variant cache, the durable re-render budget.
- The session state machine: checkpointing, cooperative stop, resume, panel freezing, I15.
- The eligibility pre-flight, the population control, the synthetic-delete pre-flight, the
  fingerprinted Agents poll. All of M18.
- Twin Studio's render-on-demand, its `studio_runs` latest pointer, its `origin='studio'` filing.
- Agent Studio's five panels, the `in_force` reporting, the provider list derived from the Literal.

---

## 2. The defects, in severity order

Each has: the evidence, the root cause, the consequence, and a pointer to the work package in §4
that fixes it.

---

### 2.1 BLOCKER — two lever paragraphs cannot be rendered, and the budget to retry them is spent

**Evidence.** `lever_paragraphs`, live:

| lever | dial | style | words | attempts | commitments it must carry |
|---|---:|---|---:|---:|---:|
| L3 | 2 | v2 | **150** | **2** | **8** |
| L4 | 2 | v2 | **152** | **2** | **8** |
| L2 | 2 | v2 | 138 | 2 | 6 |
| L1 | 2 | v2 | 92 | 1 | 3 |
| L1 | 1 | v2 | 77 | 2 | 2 |
| L2 | 1 | v2 | 88 | 1 | 3 |

and the stored Checker verdict on `12220`:

> `L4: 152 words outside [45, 150]; not entailed: 3.1.b, 3.2.a, 3.2.c, 4.1.a, 4.2.d`

**Root cause.** `config/style_contract.yaml` fixes one word band, `[45, 150]`, for every lever at
every dial. The commitment count per `(lever, dial)` is **not** constant — it ranges 2 to 8
(`dial_lookup.json`, `ARCHITECTURE.md` §5):

| | d1 | d2 |
|---|---:|---:|
| L1 Pay | 2 | 3 |
| L2 Conditions | 3 | 6 |
| L3 Contracts | 4 | 8 |
| L4 Management | 3 | 8 |
| L5 Representation | 3 | 5 |

Words available per commitment at the cap therefore range from 75 down to 18. The design prompt
asks for each commitment "in its own short sentence" and the Checker probes each one for
entailment, one model call each. At eight commitments the model has no choice but to compress, and
compression is precisely what loses an entailment. The measured series shows exactly that:

| commitments | observed words | words/commitment | coverage |
|---:|---:|---:|---|
| 2 | 77 | 38 | pass |
| 3 | 88–109 | 29–36 | pass |
| 6 | 138 | 23 | pass |
| 8 | 150 / 152 | 19 | **fail, 2–3 commitments each** |

The file itself predicted this. Its own comment says 150 is *"DELIBERATELY UNVERIFIED… What it buys
is headroom, not a measured fit."* It does not buy enough.

**Second half of the blocker.** `lever_paragraphs.attempts = 2` on both keys, and
`RENDER_ATTEMPTS_MAX = 2` (`twin_runtime.py:240`). `StoredParagraphPool.rerender` refuses a third
design call and returns the cached failing paragraph. The budget is durable by design (correctly —
it is what stops a restart buying an unlimited re-roll), so **no amount of pressing any button in
the application can produce a different paragraph under `style_version: v2`.**

**Consequence.** Four of the six H3 gate stimuli (`12220`, `00222`, `11211`, `02211`, `02200` — all
of which carry `L3` at dial 2 or `L4` at dial 2) cannot pass the Checker. The quality gate is
unrunnable. The sweep is unrunnable for 162 of the 243 cells. The study has no path forward.

→ **WP-1** (§4.1).

---

### 2.2 BLOCKER — a failed variant is cached and never retried

**Evidence.** `variants` holds `12220 / v2 / passed=False`. The Agents log shows the identical
error at 04:44:42 and again at 04:48:50 — the second attempt made no model call at all.

**Root cause.** Two lines, in two files, that together form a trap:

- `services/quality.py:345` and `orchestrator/loop.py:332` call `VariantRepo.put(…, checker=report)`
  **before** testing `report.passed`. Storing a failure is deliberate and defensible — the module
  comments argue it well: a cell that failed and left no trace is indistinguishable from one never
  attempted, and I3 is enforced at the *read*, not by the absence of a row.
- `services/twin_runtime.py:318` — `render_and_check` returns the cached row **unconditionally**:

  ```python
  cached = await VariantRepo(db).get(code, style_version)
  if cached is not None:
      return _variant_from_row(cached), CheckerReport(**dict(cached.get("checker") or {}))
  ```

Each half is reasonable. Together they mean a cell that fails once is failed **for ever**, with no
UI path to clear it, no event saying the second attempt was a cache hit, and no distinction on
screen between "this cell is genuinely unrenderable" and "this cell was unlucky once in September".

**Consequence.** Even after WP-1 fixes the paragraphs, `12220` at any style version that has a
stored failure would keep failing. More damagingly: the researcher has been told the same thing
twice and had no way to know the second telling cost nothing and proved nothing.

→ **WP-2** (§4.2).

---

### 2.3 HIGH — the quality gate costs 6 calls per twin per repeat where 1 would do

**Evidence.** `orchestrator/budget.py:35` — `H3_CALLS_PER_REPEAT = 6`; `services/quality.py:398` —
`for position, code in enumerate(codes, start=1):` with one `ask_items` call inside it. At 10 twins
× 2 repeats that is **120 calls**. At the study's N=500 × 3 repeats it is **9,000 calls ≈ 20 hours
serial**, which `docs/10` correctly names as the dominant cost of the whole study.

**Root cause.** The gate shows each of the six Part-17 stimuli in its own call and reads three
holdout items from each. Nothing requires this. **The human did not do it this way.** `docs/01`
§3.6 is explicit: Part 17 of the survey is *"18 items: six versions × three questions"* — one
section of one questionnaire, answered in one sitting, with all six worlds visible to the
respondent. Asking a twin the six versions in six isolated contexts is therefore not a faithful
reproduction of the human protocol; it is a *less* faithful one.

This matters beyond cost. `docs/08` §2.3 says H3 gates rather than H2 because H3 tests that *"the
mapping from stimulus to response transfers"* — and §3.3 reports Pearson `r` across the six
versions per twin, i.e. whether the twin **orders the six worlds** the way its driver did. A
respondent ordering six worlds does so by comparing them. A twin asked about each in isolation
cannot.

**Consequence.** Six times the calls, six times the wall-clock, roughly four times the tokens, and
a stimulus presentation that diverges from the human's. The user's request to collapse this to one
call per repeat is not a cost optimisation that costs validity — it is a correction that happens to
save 83% of the study's largest line item.

→ **WP-3** (§4.3).

---

### 2.4 HIGH — the gate aborts the whole session on the first unrenderable stimulus

**Evidence.** `services/quality.py:358` raises `QualityGateError` inside `_render_stimuli` on the
first failing code. `12220` is the **first** entry in `ref.h3_version_codes`, so the gate dies
before rendering the other five and before asking a single twin. The session is marked `failed`;
the Agents tab reads *"Quality gate (10 twins × 2) — failed. Versions tested so far: 0."*

**Root cause and the part that is correct.** Halting is right: an H3 score over 15 of 18 items is a
different measurement from one over 18, and silently scoring the five that rendered would be the
"never impute" rule broken. What is wrong is the **granularity of the diagnosis**. The researcher
is told about one bad code when two underlying paragraphs are bad and four of six codes are
affected. Three renders that would also have failed were never attempted, so the real scale of §2.1
was invisible for a fortnight.

**Consequence.** The failure under-reports itself. The correct behaviour is: render all six, report
all six verdicts, then halt with the complete picture.

→ **WP-4** (§4.4).

---

### 2.5 HIGH — the Dial board's *Ask the twins* cannot succeed on this database

**Evidence.** `ui/pages/lab.py:634`:

```python
session = await ask_twins(code)
```

No `population`, no `panel_size`. `services/runs.ask_twins` defaults `population="real"` and
`panel_size=settings.panel_size` (20, from `PANEL_SIZE` in `.env`). All 50 twins are
`source='synthetic'`. `check_eligibility("real", 20)` therefore refuses with:

> *0 of 50 twins have passed the quality test… Population is 'real' and the twins you have are all
> 50 synthetic — change the population below if this is a synthetic study.*

— and there is no "below". The population control exists only on the **Agents** tab
(`lab.py:172`). The Dial board has no way to set it.

**Consequence.** The refusal is correct, the message is correct, and the control it names does not
exist on the screen that produced it. Even after the quality gate runs, this button will refuse,
because `population` will still be `'real'` and every twin will still be `'synthetic'`.

**Second half.** The user wants *all* twins to answer a dialled version, not a stratified panel of
20. That is a legitimate and different thing from a sweep cell, and the system has no way to ask for
it: `panel_size` is read-only on the Settings tab (`lab.py:1358`, `interactive=False`) because it
comes from the environment.

→ **WP-5** (§4.5).

---

### 2.6 HIGH — the live validity tests fail silently and the UI reports success

This is three defects stacked, and the outermost one hides the other two.

**(a) The task is dropped and its exception is never retrieved.**
`services/validity.py:318` — `enqueue_validity_test` returns `asyncio.create_task(...)`.
`ui/pages/lab.py:1091` calls it and **discards the return value**. There is no module-level task
set and no done-callback. Every other background path in this codebase guards against exactly this
(`services/runs._spawn`, `services/quality._TASKS`, `services/studio._RENDERS`, each with a comment
calling it "the documented failure mode, not a theoretical one"). This one does not. The task can be
garbage-collected mid-run, and anything it raises becomes an *"exception was never retrieved"*
warning at interpreter shutdown.

Meanwhile the handler has already returned *"Queued test N. The result appears in the table below
when it finishes."* **It never finishes and nothing ever says so.**

**(b) What it raises.** `services/validity.py:646`:

```python
code = version_code or settings.start_code          # "10000"
paragraphs = await _paragraphs_for(code, db)        # {} — 10000 has never been rendered
```

`_paragraphs_for` returns `{}` and nothing checks it. Downstream,
`agents/twin.build_round_prompt` raises `RoundPromptError` ("expected all five levers, got []").
`RoundPromptError` is a `ValueError`; `twin_runtime.ask_panel_twins` catches only
`(ContractError, TwinPathError)`; nothing anywhere catches `RoundPromptError` — confirmed by grep
across `src/`. So it propagates into the dropped task from (a) and vanishes.

**(c) The session it picks has no panel.** `run_validity_test` defaults `session_id` to
`latest_session_id()`, which returns the newest session of **any kind**. The newest session here is
`Render 01000` (`kind='render'`, `panel_size=0`). `_test_with_calls` then reads `session_panel`,
finds nothing, and would return `INCONCLUSIVE: "this session has no frozen panel to put a stimulus
to"` — which is honest but is never reached, because (b) raises first.

**Also.** Test 7 compares two models by name and the UI never supplies `second_model_name`, so it
can only ever return `INCONCLUSIVE`. Tests 1 and 3 read H2 vectors written by the quality gate
(`twin_quality_runs` = 0). Test 2 reads a completed `SHAM` run in the chosen session (`runs` = 0).
There is no control anywhere on the screen for *which session* or *which version* a test runs
against.

**Consequence.** Eight cards, eight buttons, and no path by which any of them can produce a row —
and for five of them, no error either.

→ **WP-6** (§4.6).

---

### 2.7 HIGH — the Validation tab's only button is inert

**Evidence.** `ui/pages/lab.py:905-908`:

```python
gr.Button(
    "Check twins against their drivers",
    variant="primary",
    interactive=False,  # no handler; disabled rather than silently inert
)
```

**Root cause.** The tab is a **read-only view over `twin_quality_runs`** — `validation_view()`
aggregates H2 error, H3 error and the three Pearson `r`s from rows the quality gate writes. There is
no separate "validation run" to start, so the button was disabled rather than wired. That was the
honest choice at the time, but the result on screen is a primary-styled button that does nothing,
above a table that says *"Validation has not been run. Press Check twins against their drivers."*
— instructing the researcher to press the control that is disabled.

**Consequence.** The screen tells the user to do something impossible, and nothing on it explains
that the data arrives from the quality gate.

→ **WP-7** (§4.7).

---

### 2.8 HIGH — Agent Studio edits are saved, versioned, audited, and never used

**Evidence.** Every runtime call site constructs its agent from the **YAML seed**, not from the row
Agent Studio writes:

| Call site | Line |
|---|---|
| twin agent | `services/twin_runtime.py:580` — `default_agent_configs()["twin"]` |
| design agent | `variant/render.py:314` — `default_agent_configs()["design"]` |
| design re-render | `services/twin_runtime.py:205` |
| coverage probe | `variant/checker.py:396` — `default_agent_configs()["checker"]` |
| analyst | `services/twin_runtime.py:901` |

`default_agent_configs()` is `@lru_cache(maxsize=1)` over `config/agents.default.yaml`
(`agents/registry.py:504`). `services/agent_config.save_agent` writes to the `agent_configs`
table, bumps `version`, and appends an `agent_config_history` row — and **nothing reads that table
except Agent Studio itself.**

The codebase knows. `agent_config.in_force()` documents it as a deliberate report rather than a
rewiring: *"a `agent_configs` row's model is not read by the runtime at all. The stored row is the
editable record; the YAML is what runs."*

That was a defensible holding position. It is not compatible with `ARCHITECTURE.md` §1.1, which is
one of the three principles the whole product is built on:

> **Configuration is data, and the researcher owns it.** Models, prompts, thresholds, weights, run
> limits, wording variants, sample sizes and agent behaviour are all editable from the frontend by
> someone with no engineering background, versioned on write, and **frozen onto every run that used
> them**.

**Second defect, same area.** `AgentConfig.enabled` gates nothing. A grep across `src/` finds
exactly one read: `ui/components/domain.py:291`, which paints a pill. Setting the Results Analyst to
disabled changes a badge and nothing else; it would still be called by
`twin_runtime._reading`.

**Third, cosmetic but misleading.** The Agents tab cards describe the design agent as *"Policy
Designer — renders a decided commitment set into one paragraph"*, and the user's instinct that it
"doesn't really need a live AI model" is **half right and worth making visible**: selecting the
commitment set is `variant/lookup.py`, a pure frozen lookup with no model (I1); only turning that
set into Uber-voice prose uses the model. The screen does not separate the two, so the deterministic
half of the agent is invisible.

→ **WP-8** (§4.8).

---

### 2.9 MEDIUM — the Settings tab tells the researcher something that stopped being true

**Evidence.** `ui/pages/lab.py:1412`, in the save confirmation:

> *"**This does not change what the next session runs under yet.** Nothing reads `app_config` back
> — the running values come from `config/twin.default.yaml` until that read path exists. Edit the
> YAML to change behaviour."*

**Root cause.** `services/config.refresh_twin_config` reads `app_config['twin']` into a process
override, `load_twin_config()` merges it over the seed, and `services/runs.session_config` calls
`refresh_twin_config` before every session so a sweep runs under what was just saved. The read path
exists and works. The message is a leftover from before it did.

**Consequence.** A researcher who reads it edits YAML by hand — unversioned, unaudited, and outside
the `config_version` that `twin_quality_runs` records. It actively undoes the reproducibility chain
that the save button was written to maintain.

**Related.** `app_config['style']` carries `style_version: v1` while `settings.style_version` is
`v2`. Nothing reads that row (grep confirms), so it is inert — but it is a second, wrong declaration
of the cache key sitting in the evidence database, and it will mislead the first person who inspects
it.

→ **WP-9** (§4.9).

---

### 2.10 MEDIUM — "Twin today" is empty and nothing says why

**The question asked.** On Twin Lab → Twins, clicking a twin opens a side panel whose answer table
has five columns: `Item | Question | Driver | Twin today | Twin, version NNNNN`
(`ui/components/domain.py:381`).

- **Driver** — the human's own survey answers from `survey_answers`. Always present.
- **Twin today** — the twin's own answer vector for the **`00000` control cell**
  (`services/lab.twin_panel:360`, `_answers_for(twin_id, CONTROL_CODE, db)`). It is what the twin
  says when shown five `"No change from today."` lines. It is the twin's **noise floor**, and it is
  the thing every shift on that screen is measured against.
- **Twin, version NNNNN** — the same twin under the selected counterfactual.

`00000` is run once per session by the orchestrator before the sweep (`loop.CONTROL_CELLS`) and is
refused from the Dial board by design. With `runs = 0`, no session has ever run, so the column is
empty for every twin, in every row, with no label distinguishing "not yet measured" from "the twin
declined to answer".

→ **WP-10** (§4.10).

---

### 2.11 LOW — the Twin Studio is usable but inherits §2.1 and §2.2

Confirmed working by reading: all three twin sources, the free-text sandbox path, the render-on-
demand button, the budget card, the `studio_runs` latest pointer, and the `origin='studio'` filing.
Two real limits remain:

1. **Every dialled version the researcher is likely to try is blocked by §2.1/§2.2.** `_stimulus`
   refuses without a stored, Checker-**passed** variant, which is correct (I3 has no sandbox
   exemption) and will keep refusing until WP-1 and WP-2 land. The *"Render this version now"*
   button will produce another failing variant and cache it.
2. **`_require_quality_passed` (`services/studio.py:443`) refuses to *file* a result for a twin the
   gate has not kept** — so on today's database every Studio ask returns the conversation and the
   strip *"Not filed as a result"*. The twin is still asked and the answer is still shown, which is
   the screen's stated purpose. The module flags the alternative reading explicitly and leaves it to
   the researcher. **This plan does not change it**; it is listed as open question §7.2.

The free-text path (*"write your own change"*) does **not** require a variant and should work
today, for any twin, tested or not. If it does not, that is a separate report and is covered by the
WP-11 verification pass.

→ **WP-11** (§4.11).

---

## 3. Decisions this plan needs

### 3.1 Taken here, because they are mechanical

| # | Decision | Why it is mechanical |
|---|---|---|
| D1 | A stored **failing** variant is a cache of the *verdict*, not of the *attempt*: `render_and_check` re-renders when the stored report did not pass and the paragraph budget allows it. | The current behaviour is an accident of two independently correct lines, not a stated rule. No doc specifies it. |
| D2 | `_render_stimuli` renders and reports **all six** H3 codes, then halts if any failed. | `docs/08` §2.1 step 1 says render the six; it does not say stop at the first. Diagnosis only — the halt is unchanged. |
| D3 | The Dial board passes the researcher's chosen population explicitly, with the same control the Agents tab has. | `ask_twins` already takes the parameter; the UI simply never passes it. |
| D4 | The validity-test task is held in a module-level set with a done-callback that writes an `INCONCLUSIVE`/error row. | Every other background path in the codebase already does this. |
| D5 | The Settings tab's save message states what is actually true. | It is a false statement about this code. |

### 3.2 Needs the researcher — **ask before WP-1 is merged**

> **Q1. The word band becomes a function of the commitment count.** Today one band, `[45, 150]`,
> serves sets of 2 to 8 commitments. The plan is to make it
> `word_min = 15 + 18n`, `word_max = 25 + 30n`, where `n` is the number of commitments in that
> `(lever, dial)` brief — deterministic, constant for a given `(lever, dial)`, declared in
> `style_contract.yaml`, and bumping `style_version` to **v3**.
>
> **It is calibrated, not invented.** Against the eight paragraphs this project has actually
> rendered, the formula accepts all six that passed and rejects both that failed — and rejects them
> for being **too short**, which is the correct diagnosis: `L3` d2 at 150 words and `L4` d2 at 152
> both lost entailments to compression, and the proposed floor for eight commitments is 159.
>
> | n | lever·dial | observed | proposed band | formula verdict | actual verdict |
> |---:|---|---:|---|---|---|
> | 2 | L1·1 | 77 | [51, 85] | pass | pass |
> | 3 | L2·1 | 88 | [69, 115] | pass | pass |
> | 3 | L1·2 | 92 | [69, 115] | pass | pass |
> | 3 | L5·1 | 96 | [69, 115] | pass | pass |
> | 3 | L4·1 | 109 | [69, 115] | pass | pass |
> | 6 | L2·2 | 138 | [123, 205] | pass | pass |
> | 8 | L3·2 | 150 | [159, 265] | **too short** | **fail (coverage)** |
> | 8 | L4·2 | 152 | [159, 265] | **too short** | **fail (band + coverage)** |
>
> **What it costs, stated plainly.** Paragraph length now varies systematically with dial: a dial-1
> cell reads ~90 words and a dial-2 cell ~180. Dial is therefore partly confounded with how much
> text a twin reads. **This is already true and is unavoidable** — more commitments is more text —
> and `style_contract.yaml` already records it as a watch item. The formula makes the covariance
> explicit and principled rather than letting it be whatever the model happened to compress to. It
> must be recorded in `docs/DECISIONS.md` and stated in the paper's limitations.
>
> **The alternative considered and rejected:** `paragraphs_per_lever: 2` for dial 2. It changes the
> *shape* of the stimulus between dials, not merely its length, which is a larger confound than the
> one it fixes.
>
> I4 is untouched: still ten paragraphs per style version, still cached on
> `(lever, dial, style_version)`, still byte-identical in every cell that uses them.

> **Q2. The quality gate asks all six Part-17 versions in one call.** Today: six calls per repeat
> per twin. Proposed: one call presenting all six scenarios, returning all 18 holdout answers.
>
> **The research argument is that this is more faithful, not less.** `docs/01` §3.6 describes Part
> 17 as one section of one questionnaire — six versions, three questions each, answered in one
> sitting by a respondent who could see and compare them. `docs/08` §3.3 scores the twin on Pearson
> `r` across the six, i.e. on whether it **orders the six worlds** the way its driver did; a
> respondent orders by comparing, and a twin asked in six isolated contexts cannot compare.
>
> **What it costs.** 10 twins × 2 repeats: **120 calls → 20 calls**. N=500 × 3 repeats:
> **9,000 calls (~20 h) → 1,500 calls (~5 h)**. Tokens fall roughly 4× as well, because the persona
> and the battery frame are sent once instead of six times. One failed call now loses 18 answers
> instead of 3 — mitigated by the existing targeted repair, which already asks only for the items
> that are missing.
>
> **Caveat to record.** Six-in-one-context and six-in-isolation are **not** the same measurement.
> They cannot be pooled. `twin_quality_runs` is empty, so there is nothing to pool and no migration
> problem — but the gate's `config_version` must record which protocol produced a row, and this
> plan adds that.

> **Q3. Scope of the Dial board's *Ask the twins*.** The request is that *all* twins answer, not a
> panel of 20. Two readings, and they are different experiments:
>
> - **(a) A one-off census.** Ask every eligible twin, record `twins_n = N`, no frozen panel. Good
>   for looking; its index is **not** differenceable against a sweep cell, because I14 requires the
>   same twin set across cells.
> - **(b) Raise `panel_size` to the eligible population.** The panel is frozen at that size, every
>   cell in the session uses the same twins, and the numbers are comparable — at N× the cost of a
>   20-twin panel for every cell.
>
> The plan implements **(b)** as an editable panel size with a *"use every eligible twin"* preset,
> because it preserves comparability, and shows the cost before starting. **Confirm, or ask for
> (a).**

### 3.3 Explicitly not taken

- **The design agent is not made rule-based.** The user's observation that the Policy Designer is
  "more rule based" is correct about half of it and that half is already deterministic: the
  `version_code → DeltaSpec` lookup consults no model (I1). Replacing the *rendering* half with a
  template would turn the stimulus from Uber-voice prose into a bulleted list of commitments, which
  is a different experiment. WP-8 makes the deterministic half **visible** on the screen instead.
- **`_require_quality_passed` stays.** See §7.2.
- **No third control cell, no renumbering, no relaxed invariant** anywhere in this plan.

---

## 4. The work packages

Each states: **what changes · where · the end outcome · how it is proved**.

---

### WP-1 — Make the word band a function of the commitment count. Bump to `style_version: v3`

**Blocks:** everything. Do this first.
**Needs:** Q1 answered.

**Changes**

1. `config/style_contract.yaml`
   - `style_version: v3`.
   - Replace the two scalars with the formula's coefficients, keeping the scalars as documented
     absolute clamps so a pathological `n` cannot produce an absurd band:
     ```yaml
     word_min_base: 15
     word_min_per_commitment: 18
     word_max_base: 25
     word_max_per_commitment: 30
     word_floor: 45        # never below this, whatever n says
     word_ceiling: 300     # never above this
     ```
   - A HISTORY block recording v2 → v3, the measured table from Q1, and the confound statement.
2. `config/settings.py` — `style_version: str = "v3"`. The two **must** move together;
   `variant/render.validate_style_contract` already refuses a disagreement.
3. `variant/render.py` — `band_for(n: int, style: dict) -> tuple[int, int]`, pure and tested.
   `build_brief` computes `n = len(commitments)` and writes the resolved `word_min`/`word_max` into
   the brief's `style_contract` copy, so the agent is shown **its own** band and the Checker reads
   the same two numbers. For the sham, `n` is the number of slots that lever announces.
4. `variant/checker.check_invariance` — takes the resolved band from the brief rather than the
   global contract. `build_report` already receives `style`; it gains the per-lever band.
5. `agents/design.STYLE_KEYS_SHOWN` — unchanged in content; the values it shows are now the
   resolved ones.

**End outcome.** All ten lever paragraphs render and pass under v3. `attempts` resets to 0 for every
key because the cache key contains `style_version` — so the budget is restored **by the principled
route**, not by hand-editing a counter. All six H3 stimuli, both controls and all 243 cells become
renderable. Cost: 10 design calls + 5 sham slots = **15 calls, about two minutes.**

**Proof**
- Unit: `band_for` over n ∈ 2..8 matches the table in Q1; the eight historical paragraphs are
  replayed through `check_invariance` and produce exactly the pass/fail pattern Q1 predicts.
- Unit: `validate_style_contract` still refuses a `style_version` that disagrees with `settings`.
- Live: render the six H3 codes under v3; all six report `passed=True`.
- `tests/test_m5_render_checker.py`'s 285-combination signature assertion still holds (it is about
  containment, not length, and is untouched).

---

### WP-2 — A cached failure is a verdict, not a sentence

**Changes**

1. `services/twin_runtime.render_and_check` — the short-circuit becomes conditional:
   ```python
   cached = await VariantRepo(db).get(code, style_version)
   if cached is not None:
       report = CheckerReport(**dict(cached.get("checker") or {}))
       if report.passed:
           return _variant_from_row(cached), report
       # A stored failure records what happened; it does not forbid another attempt. The
       # paragraph budget (lever_paragraphs.attempts) is what actually bounds the cost, and it
       # is durable — so a re-entry either re-renders within budget or returns the same verdict
       # having spent nothing.
   ```
   When every lever's budget is spent, `_rerender_cell` returns `None` and the same failing report
   comes back — at the cost of zero model calls, which is the correct, cheap, loud outcome.
2. Emit a `run_events` row on that path — `"12220: re-checking a cell that failed on <date>;
   N lever paragraph(s) still have a re-render available"` — so a second press is visibly a second
   press and not a silent cache hit.
3. `services/studio.variant_status` — when a stored variant exists but did not pass, the Studio
   offers *"Render this version again"* with the remaining paragraph budget shown, rather than the
   current dead end.

**End outcome.** A cell that failed once can be retried after its cause is fixed, within the durable
budget and never outside it. The 04:44/04:48 experience — the same error twice, the second free and
uninformative — cannot recur.

**Proof**
- Unit: a stub whose first `check_variant` fails and whose second passes; `render_and_check` called
  twice returns `passed=False` then `passed=True`, and `VariantRepo.put` is never called with a
  fresh `variant_id` (the existing primary-key guard is unaffected).
- Unit: with `attempts = RENDER_ATTEMPTS_MAX` on every lever, a second `render_and_check` makes
  **zero** model calls and returns the stored failing report. Asserted on the call counter.
- I4 regression: rendering all 243 codes still spends exactly ten design calls.

---

### WP-3 — One call per repeat for the H3 gate

**Needs:** Q2 answered.

**Changes**

1. `agents/prompts/twin_h3_v1.md` — a new system prompt, same six-section skeleton
   (`registry.PROMPT_SECTIONS` enforces it). It asks for 18 integers keyed by holdout item id,
   where each item id names the version it belongs to. Same `# IF YOU CANNOT` discipline.
2. `agents/twin.build_h3_prompt(...)` — a sibling of `build_round_prompt` producing a
   `<<<SCENARIO>>>` fence of **six labelled blocks** in fixed `version_shown` order 1…6 (the order
   the human saw), each block's five lever paragraphs ordered by the existing seeded shuffle so
   lever order stays randomised and reconstructible (I11). `<<<BASELINE>>>` is absent, as now.
   `<<<BATTERY>>>` lists the 18 items grouped under their version with each item's own range.
   - **The version codes themselves never appear in the prompt.** Blocks are labelled
     "Version 1" … "Version 6". `assert_no_forbidden_content` already refuses a round naming a
     version code (I8) and that guard is reused unchanged.
3. `services/twin_runtime.ask_h3_round(...)` — one `ask_items`-shaped function over the 18 ids. It
   reuses `run_answer_ladder` with `schema=QualityAnswerSet` and `expected` = the 18 ids, so the
   existing targeted repair asks only for whatever is missing. **No new validation path.**
4. `services/quality._gate_one_twin` — the inner `for position, code in enumerate(codes)` loop
   collapses to a single call per repeat. H2 is unchanged (it is already one call).
5. `orchestrator/budget.py` — `H3_CALLS_PER_REPEAT = 1`, with the comment rewritten to say why, and
   `H3_VERSIONS_PER_CALL = 6` kept as a named constant for the breakdown line.
6. `services/runs.quality_budget_view` — breakdown becomes
   `"1 call × 2 repeat(s) × 10 twin(s), each call showing all 6 Part-17 versions"`.
7. `twin_quality_runs.detail` gains `"protocol": "h3_single_call_v1"`, so a row always says which
   presentation produced it and two protocols can never be pooled by accident.

**End outcome.** 10 twins × 2 repeats = **20 calls**, exactly as requested. The gate runs to
completion in minutes rather than a quarter of an hour. At study scale the dominant cost drops from
~20 h to ~5 h.

**Proof**
- Unit: `build_h3_prompt` emits six labelled blocks in `version_shown` order, names no version code,
  names no non-H3 holdout item, and rebuilds byte-identically from `(seed, twin, codes)`.
- Unit (call counter, stub client): a gate over 3 twins × 2 repeats makes **6** twin calls for H3,
  not 36.
- Unit: a stub returning 15 of 18 items triggers exactly one targeted repair naming the 3 missing
  ids, and a stub that then returns 18 scores normally; a stub that returns 15 twice fails the
  repeat and **does not** score it (I15).
- Invariant: `tests/test_invariants.py` I8 gains the H3 prompt to its forbidden-content scan.

---

### WP-4 — Render all six stimuli, report all six, then halt

**Changes**

`services/quality._render_stimuli` — collect verdicts for every code before raising:

```python
failed: dict[str, str] = {}
for code in codes:
    variant, report = await render_and_check(code, style_version, backend=db)
    await VariantRepo(db).put(...)          # unchanged: a failure that leaves no trace is worse
    if not report.passed:
        failed[code] = report.notes[:300]
        await events.emit(stage="check", status="error", label=f"{code} failed the Checker", ...)
        continue
    out[code] = {...}
if failed:
    raise QualityGateError(
        f"{len(failed)} of {len(codes)} Part-17 stimuli did not pass the Checker, so the gate "
        f"cannot run: a twin scored on fewer than 18 items is a different measurement (I15). "
        + "; ".join(f"{c}: {why}" for c, why in sorted(failed.items()))
    )
```

**End outcome.** The researcher sees all six verdicts in one go — four failures and two passes,
rather than one failure and silence. The halt itself is unchanged and still correct.

**Proof.** Unit with a stub failing codes 1 and 4: six render events are emitted, two carry
`status="error"`, the raised message names both, and no twin is asked.

---

### WP-5 — Make the Dial board able to ask, and able to ask everybody

**Needs:** Q3 answered (plan assumes reading (b)).

**Changes**

1. `ui/pages/lab._dial_board_tab` gains, beside *Ask the twins*:
   - a **population** radio (`real` / `synthetic` / `both`), defaulting to the stored session
     population exactly as the Agents tab's does (`lab._stored_population`);
   - a **panel size** number with a *"use every eligible twin"* checkbox that sets it to
     `check_eligibility(...)["eligible"]`;
   - the live counts line from `services.runs.population_counts()`;
   - a **confirm step with the budget**, as `docs/06` §9 requires of every long action and as the
     Agents tab, the Twins tab and the Validity tab already have. *Ask the twins* currently starts
     a session with no cost shown — a gap in its own right.
2. `_ask` passes `population=` and `panel_size=` through to `ask_twins`.
3. `_rerun` is unchanged: a rerun **inherits** the original panel (I14) and must not take new
   values.
4. `ui/pages/lab._settings_tab` — `panel_size` becomes editable and is stored in `app_config`
   alongside the other `TwinConfig` values, with `settings.panel_size` as its seed. The read-only
   environment box stays beside it, labelled as the default.

**End outcome.** After the quality gate, the researcher sets the dials, picks `synthetic`, ticks
*use every eligible twin*, sees "N twins · M calls · ~T minutes", presses Start, and every kept twin
answers that version. The result lands in Results with `twins_n = N`.

**Proof**
- Unit: `_ask` forwards both parameters; `_rerun` forwards neither.
- Unit: with 50 synthetic twins all gate-passed, `check_eligibility("synthetic", 50)["ok"]` is true
  and `ask_twins(code, population="synthetic", panel_size=50)` creates a session with
  `panel_size=50`.
- Unit: the confirm step renders before any session row is written; cancelling writes nothing.

---

### WP-6 — Make the validity tests run, fail loudly, and be aimable

**Changes**

1. **Hold the task and report its death.** `services/validity.enqueue_validity_test` gains a
   module-level `_TASKS: set[asyncio.Task]` and a done-callback that, on an exception, appends a
   `validity_results` row with `verdict="INCONCLUSIVE"` and the reason in `headline`. This is the
   `services/runs._spawn` pattern applied where it was missed. **A background death must appear
   where the researcher is looking.**
2. **Refuse an empty stimulus instead of crashing on one.**
   `services/validity._test_with_calls` checks `paragraphs` before using it:
   ```python
   if not paragraphs:
       return vt.inconclusive(number,
           f"{code} has no stored, Checker-passed variant, so there is nothing verified to put "
           "to a twin (I3). Render it in Twin Studio, or pick a version that has been run.")
   ```
   And `twin_runtime.ask_panel_twins` adds `RoundPromptError` to its caught set, so a malformed
   round fails that twin rather than the whole test. (`RoundPromptError` is caught **nowhere** in
   the codebase today — grep-confirmed.)
3. **Pick the right session.** `run_validity_test` defaults `session_id` to the newest session that
   **has a frozen panel**, not the newest session of any kind — a new
   `services/runs.latest_session_with_panel()`. A render session or a quality session is not a
   thing a validity test can be run against.
4. **Aim it from the screen.** The Validity tab gains three controls above the eight cards:
   - **Session** — the sessions that have a panel, newest first, with their panel size.
   - **Version to test** — the codes with a Checker-passed variant (tests 4–8 need a stimulus).
   - **Second model** — a text box, shown only for test 7, defaulting empty with the note that test
     7 cannot run without it.
   All three are passed to `run_validity_test`.
5. **Say what each test still needs.** Each card gains a one-line readiness state computed from a
   new `services/validity.test_readiness(number, session_id)` — *"ready"*, or *"needs the quality
   gate (0 twins have an H2 vector)"*, or *"needs a completed SHAM in this session"*, or *"needs a
   second model name"*. Computed, not guessed, from the same reads the test itself makes.

**End outcome.** Every test either produces a `validity_results` row or says on screen exactly what
it is waiting for. Nothing is queued into silence.

**Proof**
- Unit: a test whose `ask` raises appends an `INCONCLUSIVE` row naming the exception; the task is
  in `_TASKS` while running and removed after.
- Unit: `_test_with_calls` with no stored variant returns `INCONCLUSIVE` and makes **zero** calls.
- Unit: `latest_session_with_panel` skips `kind='render'` and `kind='quality'` sessions.
- Unit: test 7 with no `second_model_name` returns `INCONCLUSIVE` (already true) **and** its card
  says so before the button is pressed (new).

---

### WP-7 — Make the Validation tab honest and live

**Changes**

1. The button becomes **"Recheck twins against their drivers"**, `interactive=True`, and its handler
   re-runs `validation_view()` and repaints — the honest action, which is a refresh, named as one.
   It makes **no model call**: every number on the tab is re-aggregated from stored
   `twin_quality_runs` rows.
2. The empty state stops instructing the researcher to press it and instead says where the data
   comes from: *"These numbers are produced by the twin quality test. Run it on the Twins tab; the
   verdicts land here."* With a count: *"0 of 50 twins have a stored quality run."*
3. A line above the table naming which protocol produced the rows (from WP-3's
   `detail.protocol`), so H3 numbers always say how they were collected.

**End outcome.** No disabled primary button, no instruction to press it, and a clear statement that
this tab reads the gate's output.

**Proof.** Unit: the handler is attached and returns the same three HTML blobs `load_once` does;
with zero quality runs the empty state names the gate and the count.

---

### WP-8 — Make Agent Studio edits actually govern the runtime

This is the largest package and the one that changes a documented holding position, so it is
specified tightly.

**Changes**

1. **A live config override, exactly mirroring `services/config.refresh_twin_config`.**
   New `services/agent_config.refresh_agent_configs(backend)` reads `agent_configs` into a
   process-level dict and `live_agent_configs()` merges it over the YAML seed, validating through
   `AgentConfig` either way. A stored row that will not validate logs at WARNING and falls back to
   the seed for **that agent only** — the behaviour `load_agent` already has.
2. **Call sites read the live config.** The five sites in §2.8's table take
   `live_agent_configs()[...]` instead of `default_agent_configs()[...]`. `default_agent_configs`
   stays, `@lru_cache` and all, as the seed and the restore target.
3. **Refresh on the same boundaries the twin config uses.** `services/config.startup_check` calls
   `refresh_agent_configs` at boot; `services/runs.session_config` calls it before every session,
   gate and Studio ask, and **freezes the resulting `{agent_id: version}` map onto
   `sessions.config["agent_versions"]`** — which is `ARCHITECTURE.md` §1.1's *"frozen onto every run
   that used them"*, satisfied in the data. I11 is strengthened, not weakened: the run now records
   which agent version produced it.
4. **`enabled` gates something.** `live_agent_configs` raises `AgentDisabled` when a disabled
   agent's config is requested, and each call site turns that into its own defined outcome:
   - `design` disabled → the render fails loudly and the cell fails. There is no rule-based
     fallback (see §3.3).
   - `checker` disabled → **refused outright.** Disabling the coverage probe would let an
     unverified stimulus reach a twin, which is I3, which is not negotiable. The UI removes the
     toggle for this agent and says why.
   - `analyst` disabled → `twin_runtime._reading` uses the deterministic template with its
     `FALLBACK_PREFIX`, which is an existing, tested path.
   - `twin` disabled → nothing can be asked; refused with that sentence.
   - `manager` is already `enabled: false` and already calls nothing.
5. **The temperature box stops lying.** `twin_runtime.twin_agent_config` currently overrides the
   agent row with `load_twin_config().temperature` unconditionally (`twin_runtime.py:581`). It
   becomes: `app_config['twin'].temperature` wins **when it is set**, and Agent Studio's twin
   temperature box is made read-only with the sentence *"The twin's temperature is set in Twin Lab →
   Settings, because it is frozen onto every session and is the subject of validity test 8."* One
   value, one place, stated. (`in_force()` already computes and displays this correctly; now the
   editable control matches it.)
6. **Split the Policy Designer card in two.** On the Agents tab and in Agent Studio, the design
   agent is shown as two steps:
   - *Choosing what changes* — **no AI model.** A frozen lookup over `dial_lookup.json` and
     `gaps.json`; identical input, byte-identical output, every time (I1). Shows the commitment list
     for the current dials, read straight from the lookup.
   - *Writing it in Uber's voice* — **one AI call per `(lever, dial, style_version)`**, ten per
     style version for all 243 cells (I4).
   This is a presentation change that makes an existing structural fact visible. It changes no
   behaviour.
7. **Agent Studio shows the version in force.** Beside each agent: *"saved version 4 · in force
   since <timestamp> · 2 sessions have run under it"*.

**End outcome.** Editing a prompt, a temperature, a model name, an output mode or a retry policy in
Agent Studio changes what the next quality gate, Dial board ask, sweep, Studio ask and validity test
actually do — and the run records which version it ran under, so two sessions under different agent
configurations can never be silently compared.

**Proof**
- Unit: save a prompt edit; `live_agent_configs()["twin"].system_prompt` reflects it without a
  process restart, and `default_agent_configs()` does not.
- Unit: a session started after a save carries `config["agent_versions"]["twin"]` equal to the new
  version.
- Unit: disabling `analyst` makes `_reading` return the `FALLBACK_PREFIX` template and makes no
  model call; disabling `checker` raises at save time with the I3 sentence.
- Unit: a stored `agent_configs` row that does not validate falls back to the seed **for that agent
  only** and logs once.
- Invariant: I2 and I6 still hold — `validate_config` already refuses a tool on `design` or `twin`
  and runs on every save, so a live config cannot introduce one.

---

### WP-9 — Stop the Settings tab from misinforming

**Changes**

1. `ui/pages/lab.py:1405-1415` — the save message becomes true:
   > *Saved to `app_config` as version **N**. The next session, quality gate or Studio ask reads
   > this; runs already completed keep the config version they ran under. You do not need to edit
   > any file.*
2. Delete the `app_config['style']` row, or correct it to `v3` in the same operation as WP-1 and
   have `services/config.startup_check` warn when it disagrees with `settings.style_version`. The
   row is read by nothing (grep-confirmed) but sits in the evidence database declaring the wrong
   cache key.
3. `panel_size` becomes editable (shared with WP-5).

**Proof.** Unit: `save_settings` followed by `session_config()` returns the saved values; the boot
check warns on a `style` row that disagrees.

---

### WP-10 — Label "Twin today"

**Changes**

1. `ui/components/domain.answer_compare` — the column header becomes
   **"Twin today (00000)"** with a tooltip/caption: *"What this twin says when shown no change. It
   is produced by the `00000` control cell, which runs once at the start of every session."*
2. `services/lab.twin_panel` returns a new `baseline_state`: `"measured"`, or
   `"not measured — 00000 has not been run for this twin"`. The cells render that sentence once
   above the table rather than a column of dashes, so *not yet measured* is distinguishable from
   *the twin declined*.
3. The same sentence appears in the side panel's quality line when `twin_quality_runs` has no row.

**Proof.** Unit: with no `00000` run, `twin_panel(...).baseline_state` is the "not measured" value
and no cell fabricates a number (I17).

---

### WP-11 — Verification pass over the Twin Studio

No code change expected; this is the package that proves §2.11 and catches whatever it turns up.
After WP-1 and WP-2:

1. Pick a twin that has **not** been through the gate. Render `22000` from the Studio; confirm the
   budget card shows the remaining paragraph cost, the Agents log shows the render, and the stored
   variant passes.
2. Ask that twin `22000` with the battery ticked. Confirm: the answers appear, the scenario text
   appears, and the strip reads *"Not filed as a result"* with `_require_quality_passed`'s sentence.
3. Ask the same twin with a **free-text change** and the battery ticked. Confirm: the sandbox strip,
   the answers, **no** `runs` row, **no** `version_code` on the `studio_runs` row.
4. Repeat 2 for a twin the gate **kept**. Confirm the run is filed with `origin='studio'`,
   `twins_n=1`, and appears in Results with the Studio badge.
5. Ask the same `(twin, version)` twice. Confirm the second appends and the first survives with
   `is_latest_for_twin_version = false`.
6. Exercise *From a survey answer* and *Make one by hand* (validation-plan C-11 and C-12, both still
   `[TODO]`). A hand-made twin must show an **empty** baseline column, not zeros.

Anything that fails here becomes a WP-12 with its own root cause.

---

## 5. Execution order

| Step | Package | Depends on | Rough size |
|---:|---|---|---|
| 1 | **Ask Q1, Q2, Q3** | — | a conversation |
| 2 | **WP-1** band formula, `style_version: v3` | Q1 | medium; 15 design calls to re-render |
| 3 | **WP-2** cached failure is a verdict | — | small |
| 4 | **WP-4** render all six, report all six | — | small |
| 5 | **Checkpoint:** render the six H3 codes live; all six must pass | 2–4 | 5 minutes |
| 6 | **WP-3** one call per repeat | Q2, step 5 | medium; new prompt + builder |
| 7 | **Checkpoint:** run the gate on 10 twins × 2. Must be **20 calls** and must complete | 6 | ~5 minutes |
| 8 | **WP-5** Dial board population, panel size, budget | Q3 | medium |
| 9 | **Checkpoint:** dial a version, ask every eligible twin, see the result in Results | 8 | — |
| 10 | **WP-7** Validation tab | 7 | small |
| 11 | **WP-6** validity tests | 9 (needs a session with a panel) | medium |
| 12 | **WP-8** Agent Studio governs the runtime | — | large |
| 13 | **WP-9**, **WP-10** | — | small |
| 14 | **WP-11** Studio verification | 2 | a session at the screen |
| 15 | Re-run the full suite; re-run `build_reference --check`; re-run import-linter | all | 3 minutes |

Steps 3, 4, 12 and 13 are independent of the research questions and can start immediately.

---

## 6. Acceptance checks

Each is a thing the researcher does at the screen, with a pass condition. These are the contract.

| id | Action | Pass |
|---|---|---|
| A-1 | Render the six H3 codes under v3 | all six `passed=True`; ten lever paragraphs stored; `attempts = 1` on each |
| A-2 | Press *Run twin quality test* on 10 twins | budget card reads **20 calls**; the gate completes; 10 `twin_quality_runs` H3 rows with `items_n = 18` |
| A-3 | The same gate, with H2 on | one H2 row per twin whose driver has a recorded arm, `items_n = 16`, each at **its own driver's arm** |
| A-4 | Re-press the quality test with a twin that failed its ladder | that twin is `Not run`, never `kept` with a perfect score (I15) |
| A-5 | Dial board: set `01000`, population `synthetic`, *use every eligible twin*, Start | confirm step shows N twins and the call count; session runs; every kept twin answers |
| A-6 | Results tab after A-5 | the cell appears with `twins_n = N`, `origin = sweep`, a six-metric bar set and a grounded reading |
| A-7 | Twins tab, open a twin, compare with `01000` | *Twin today (00000)* is populated from the session's control cell; *Driver* is populated; neither fabricates a number |
| A-8 | Validation tab | the button works; the summary shows H2 error, H3 error and three Pearson `r`s over the twins that have rows; the protocol line names `h3_single_call_v1` |
| A-9 | Validity tests 1 and 3 | run inline, append a row, **zero** model calls on the counter |
| A-10 | Validity test 2 | runs against the session from A-5; if that session has no completed SHAM, the card says so **before** the button is pressed |
| A-11 | Validity test 7 with no second model | the card reads *"needs a second model name"* and the button explains rather than queues |
| A-12 | Force any validity test to raise | an `INCONCLUSIVE` row appears in the table naming the exception; nothing is silently queued |
| A-13 | Agent Studio: edit the twin prompt, save, run one Studio ask | the ask uses the edited prompt; `sessions.config["agent_versions"]["twin"]` is the new version |
| A-14 | Agent Studio: disable the Results Analyst, run a cell | the reading is the template with `FALLBACK_PREFIX`; no analyst call is made |
| A-15 | Agent Studio: try to disable the Quality Checker | refused, naming I3 |
| A-16 | Settings: save a temperature, start a session | the session's frozen config carries it; the save message does not mention YAML |
| A-17 | Twin Studio on an untested twin, `22000` | asked and shown; **not** filed; the strip says why |
| A-18 | Twin Studio free-text change | sandbox strip; `studio_runs` row with `version_code = null`; **no** `runs` row |
| A-19 | Sit on the Agents tab for 2 minutes, idle | zero database calls, no re-render (M18's U-1, re-verified) |
| A-20 | Full suite | 855+ tests pass; `ruff` clean; 6 import-linter contracts; `build_reference --check` exits 0 |

---

## 7. Invariants, and open questions

### 7.1 Every invariant this plan touches, and how it is kept

| Invariant | Touched by | Kept how |
|---|---|---|
| **I1** treatment is a frozen lookup | WP-8 item 6 | Presentation only. The lookup is unchanged and is now *shown* to be model-free. |
| **I2** design agent has no tools | WP-8 | `validate_config` runs on every save and refuses a tool on `design`. A live config cannot introduce one. |
| **I3** unverified variant never reaches a twin | WP-1, WP-2, WP-6 | The refusal at every read is unchanged. WP-2 re-opens the *attempt*, never the *verdict*. WP-6 adds a refusal where an empty stimulus was being passed through. |
| **I4** ten paragraphs per style version | WP-1, WP-2 | Same `(lever, dial, style_version)` key; v3 is a legitimate bump that invalidates exactly ten paragraphs, which is what the key exists for. WP-2 spends no call when the budget is gone. |
| **I5** dial 0 is a fixed string | WP-1 | Dial 0 short-circuits before any band is computed; gate 4 is unchanged. |
| **I6 / I8** persona and round prompt separate; no holdout leakage | WP-3 | The H3 prompt goes through `assert_no_forbidden_content` with the same holdout list and the same version-code refusal. Covered by a new I8 test. |
| **I9** evidence is append-only | WP-6, WP-8 | WP-6 **inserts** an `INCONCLUSIVE` row; `append_result` has no update path. WP-8 appends an `agent_config_history` row per save, as now. |
| **I11** everything shown is reproducible | WP-3, WP-8 | WP-3's prompt rebuilds from `(seed, twin, codes)`. WP-8 **adds** the agent version map to the frozen session config — a strengthening. |
| **I12** no model produces a metric | none | Untouched. Every number in this plan is Python. |
| **I13** provider schemas never trusted | WP-3 | The H3 round goes through `run_answer_ladder` with `QualityAnswerSet` over the 18 named ids. No new validation path, no `NativeOutput`. |
| **I14** the panel is frozen | WP-5 | Panel size is chosen **before** the session is created and frozen onto it. A rerun still inherits and is forbidden from taking new values. |
| **I15** no result over zero twins | WP-3, WP-4, WP-6 | A repeat that cannot produce 18 scorable items is discarded; a gate missing a stimulus halts rather than scoring 15; a validity test that ran on nobody is `INCONCLUSIVE`. |
| **I17** nothing is imputed | WP-10 | *Not measured* is rendered as a sentence, never as a zero or a dash that could be read as one. |
| `CLAUDE.md` **rule 12** no LLM in a handler | WP-5, WP-6 | Both new paths enqueue and return; the confirm steps are pure reads. |

### 7.2 Open, and deliberately not decided here

1. **Does a Studio result from a dropped twin belong in the analysis?**
   `services/studio._require_quality_passed` says no, and documents that the alternative — file it,
   labelled `origin='studio'`, and let a reader judge — is defensible and is the researcher's call.
   It is one line. **Not changed by this plan.**
2. **The sweep population.** `sessions.population` defaults to `'real'`; every twin is `synthetic`.
   M18 made it an explicit, visible control rather than picking one, and WP-5 extends that control
   to the Dial board. Which population a **study** sweep runs on remains a research decision taken
   at the moment of running it.
3. **The confound WP-1 makes explicit.** Paragraph length covaries with dial. It already did; the
   formula makes it principled and declared. It belongs in `docs/DECISIONS.md` and in the paper's
   limitations, and it is worth asking whether the analysis should carry a word-count covariate.
4. **Twin temperature** is still `0.25` in `app_config` against a seeded `0.7`, chosen by neither
   measurement. Validity test 8 is what sets it, and WP-6 is what makes test 8 runnable. Do not pick
   it before then.
5. **`quality_runs_per_twin`** is 2, down from the specified 3. `docs/08` §2.1 wants 3 so one bad
   sample does not discard a good twin. WP-3 makes 3 repeats cost 30 calls at 10 twins instead of
   180 — the reason for the reduction largely evaporates. **Worth revisiting after step 7.**

---

## 8. What this plan does not do

It does not render a stimulus for the paper, produce a number for the paper, or decide a research
question. It makes the instrument operable and makes every screen tell the truth about what it is
showing. The gate on the study itself is still `HANDOFF_M17_VALIDATION_PLAN.md` §5.1 and §5.2, which
are untouched here.
