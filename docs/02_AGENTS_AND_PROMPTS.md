# 02 — Agents, prompts and the output contract

The five agents, the prompt architecture, and what happens when a model does not do as it is told.

Normative.

---

## 1. Five agents, and why not six

| Agent | Job | ReAct | Tools | Temp |
|---|---|---|---|---:|
| **Manager** | Owns the session. Routes, schedules, checkpoints, decides what runs next. | yes | session/run/cursor | 0.0 |
| **Design** | DeltaSpec → one lever paragraph in Uber's voice. | **no** | **none** | 0.3 |
| **Twin** | Persona + round prompt → 37 integers. Also answers holdouts in quality mode. | **no** | **none** | CONFIG |
| **Checker** | Gates every render: coverage, containment, invariance, identity, sham. | no | none | **0.0** |
| **Analyst** | Writes prose about numbers Python computed. | no | metric readers | 0.2 |

**No validation agent.** There are two validation jobs and neither wants one.

*Variant validation* is the Checker, which already exists. Most of its work is deterministic — word
count, byte-identity of dial-0 lines, do-not-say substring scan. Exactly one step needs a model:
*does this paragraph entail this commitment?*

*Twin validation* is the holdout test. The Twin agent answers held-out versions; scoring is **pure
Python** — mean absolute error against the human's answers. Putting a model in that path would make
the fidelity number nondeterministic, and the fidelity number is precisely what must be stable
across re-runs. It is a **run mode** of the Twin agent plus a scorer function.

**Design and Twin are `react: false` on purpose.** A ReAct loop can fetch. A Design agent that can
fetch a gap can pull threshold 2.2 material into an `01000` render and destroy the difference
between `01000` and `02000` (I2). A Twin that can fetch can read its own holdout answers (I6). Both
get everything they need injected, and nothing else. `tools: []` is enforced in `build_agent()`,
not left to discipline.

**The Analyst lost its ReAct loop in 2.0.** In 1.0 it had `react: true` and tools that could fetch
run history. That is an unbounded surface through which a number the analyst was not given can
enter its prose. It now receives one deterministically assembled bundle and nothing else, and its
output is numerically grounded against that bundle (§6). This is a tightening, not a feature loss.

---

## 2. `AgentConfig` — what it holds, and what it refuses to hold

```python
# src/twinlab/models/agent.py
from typing import Literal
from pydantic import BaseModel, Field

class ModelRef(BaseModel):
    provider: Literal["ollama", "openai", "mock"] = "ollama"
    name: str                            # CONFIG; verify against the provider's live list
    temperature: float = 0.2
    max_tokens: int = 2048
    seed: int | None = None              # see §7.2 — honoured only if the provider honours it

class ContextSource(BaseModel):
    """Declarative: what the registry injects into the prompt. Resolved, never fetched."""
    kind: Literal["delta_spec", "anchor_chunks", "style_contract", "do_not_say",
                  "persona", "baseline_answers", "battery", "scenario", "bundle"]
    required: bool = True

class RetryPolicy(BaseModel):
    attempts: int = 2                    # total, including the first
    backoff: Literal["none", "linear", "exponential"] = "exponential"
    repair_mode: Literal["targeted", "full", "none"] = "targeted"   # §5.4

class AgentConfig(BaseModel):
    agent_id: str
    name: str
    role: str
    enabled: bool = True
    model: ModelRef
    system_prompt: str                   # inline, or "file:design_v1.md"
    prompt_hash: str                     # sha256 of the RESOLVED prompt. Frozen onto every run.
    instructions: list[str] = Field(default_factory=list)
    input_schema: str                    # key into SCHEMA_REGISTRY
    output_schema: str                   # key into SCHEMA_REGISTRY
    output_mode: Literal["tool", "prompted"] = "tool"   # never "native" — §5.1
    tools: list[str] = Field(default_factory=list)      # ALLOW-LIST into TOOL_REGISTRY
    context_sources: list[ContextSource] = Field(default_factory=list)
    react: bool = False
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    version: int = 1
    frozen: bool = False
```

**Deliberately absent.** Each was considered and rejected; do not add them.

| Not included | Because |
|---|---|
| DB credentials or connection info | Agents never touch the DB. Repositories do. An agent receives data and returns data. |
| Inline per-call prompt templates | Prompts are versioned files under `agents/prompts/`. Inlining them in a DB row makes diffing and review impossible. |
| Output parsing rules / regex | pydantic-ai gives typed output from `output_schema`. A parser field would be a second, competing mechanism. |
| Per-agent rate limits | Rate limiting is a property of the provider and the pool, not the agent. It lives in `app_config.orchestrator`. |
| `max_iterations` for non-ReAct agents | Meaningless when `react: false`. A field valid for one of five agents invites misuse. |
| Metric definitions | Metrics are instrument properties (`instrument.json`), not analyst properties. If the analyst owned them, editing the analyst would silently change the measurements. |
| Scale ranges | Same reason. The item register owns them; the validator reads them from there. |

**Why `tools` is an allow-list, not capability flags.** A boolean like `can_read_corpus` grows one
flag per resource and is checked in five places. A name list is checked once, in
`registry.build_agent()`, which looks each name up in `TOOL_REGISTRY` and raises on an unknown one.
The design agent's list is `[]`, which is enforceable and obvious in a config diff.

### 2.1 The registry indirection

Build it now, with five agents, even though it looks like overhead. Retrofitting it later means
rewriting all five.

```python
# src/twinlab/agents/registry.py
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "LeverBrief": LeverBrief,           "LeverParagraph": LeverParagraph,
    "RoundPrompt": RoundPrompt,         "TwinAnswerSet": TwinAnswerSet,
    "CoverageProbe": CoverageProbe,     "CoverageVerdict": CoverageVerdict,
    "AnalysisBundle": AnalysisBundle,   "AnalysisResult": AnalysisResult,
}
TOOL_REGISTRY: dict[str, Callable] = {...}

def build_agent(cfg: AgentConfig) -> Agent:
    if cfg.output_mode == "native":
        raise ConfigError(f"{cfg.agent_id}: native output is unsupported on Ollama Cloud (§5.1)")
    unknown = set(cfg.tools) - TOOL_REGISTRY.keys()
    if unknown:
        raise ConfigError(f"{cfg.agent_id}: unknown tools {unknown}")
    marker = ToolOutput if cfg.output_mode == "tool" else PromptedOutput
    return Agent(
        model=resolve_model(cfg.model),
        output_type=marker(SCHEMA_REGISTRY[cfg.output_schema]),
        system_prompt=load_prompt(cfg.system_prompt),   # also computes prompt_hash
        tools=[TOOL_REGISTRY[t] for t in cfg.tools],
        model_settings=settings_for(cfg.model),
    )
```

**Adding a sixth agent** is: insert an `agent_configs` row, drop a prompt file, and — only if it
needs a new shape or tool — add one line to a registry. A future "create an agent" screen writes
the first two from the UI.

---

## 3. Prompt architecture

The prototype's prompts were single paragraphs of prose written inline. They are not being carried
over. Prompts here are **versioned artefacts with a fixed structure**, because a prompt is part of
the experimental apparatus: change it and you have changed the instrument.

### 3.1 Every prompt is a file

`src/twinlab/agents/prompts/<agent>_v<N>.md`. Never inline, never edited in place. A change is a
**new file and a version bump**, so an old run stays reconstructible.

```markdown
---
agent: design
version: 3
supersedes: design_v2.md
changed: "tightened the do-not-say framing after a 2.2 leak in 01000"
---

# ROLE
...
# INPUTS
...
```

`load_prompt()` computes `sha256` over the resolved text and writes it to
`agent_configs.prompt_hash`, which is frozen onto every run that used it (I11). Two runs with
different `prompt_hash` values are not the same experiment and the UI says so.

### 3.2 The six-section skeleton — mandatory, in this order

Every prompt has exactly these sections, in this order, with these names. A consistent skeleton is
worth more than clever wording: it makes prompts diffable, makes an omission obvious, and stops
instructions drifting between the role and the rules where models weight them differently.

| Section | Holds | Never holds |
|---|---|---|
| `# ROLE` | Who the model is, in two or three sentences. | Tasks, rules, examples |
| `# INPUTS` | A named description of each injected block and what it means. | The data itself |
| `# TASK` | The single thing to produce. One imperative. | Constraints |
| `# RULES` | Numbered constraints, each independently checkable. | Output shape |
| `# OUTPUT` | The exact shape, field by field, with ranges. | Anything else |
| `# IF YOU CANNOT` | What to do when the task is impossible. | A licence to improvise |

**`# IF YOU CANNOT` is not padding.** A model given no failure path invents one, and an invented
failure path is a silent data defect. Every prompt tells the model precisely how to signal
inability — and every such signal is a recorded, inspectable outcome, never a discarded one.

### 3.3 Ordering inside the prompt

Injected data goes **after** the system prompt and **in a stable order**, each in a labelled
fence. Order is part of the contract: a reordered prompt is a different stimulus.

```
[system]     the six-section prompt file
[inputs]     <<<PERSONA>>> … <<<SCENARIO>>> … <<<BASELINE>>> … <<<BATTERY>>> …
```

The one deliberate exception is the **lever order inside `<<<SCENARIO>>>`, which is randomised
per twin per round** so paragraph position cannot become a confound. The order actually used is
persisted on `twin_answers.lever_order` (I11).

### 3.4 Few-shot examples: forbidden for Design and Twin

This is a containment rule, not a style preference.

- **Design.** An example paragraph necessarily contains commitments. Any commitment in an example
  can bleed into a render for a cell that does not include it — which is exactly the failure I2 and
  I3 exist to prevent, arriving through the one door the Checker does not watch. The design agent
  gets the style contract and anchor chunks for register; it does not get worked examples.
- **Twin.** An example answer vector anchors the distribution. Every twin would drift toward the
  example's numbers, compressing between-twin variance — which is the signal.
- **Checker and Analyst may use examples**, because neither produces stimulus or data. The Checker
  benefits from examples of entailment and non-entailment; the Analyst from examples of hedging.

### 3.5 Forbidden vocabulary

The style contract's `forbidden_terms` — `Fairwork`, `principle`, `threshold`, `score`, `research`,
`study`, `survey`, `twin` — apply to **everything a twin can see**: the design agent's output, the
round prompt, and the prompt files themselves. A twin told it is in a study answers like a
participant, not like a driver.

---

## 4. The five prompts

Full text lives in the files. This is the contract each must satisfy.

### 4.1 Design — `design_v1.md`

**Receives exactly four things** and nothing else (the worked example in
`additional_data/worked_out_eg.txt` traces this by hand):

1. The commitments for **this lever only**, from the frozen DeltaSpec.
2. Anchor chunks from `corpus_chunks`, for register only.
3. The style contract.
4. The do-not-say list — every commitment *not* in this lever's set, plus the three already-met
   criteria.

**Produces** one paragraph, 45–70 words, second person, present or near-future, no bullets, no
numbers except those a commitment supplies.

Anchors do **two different jobs** that must not be conflated: *copy the voice* (S15 reads "Safety
is designed into the experience" — short sentences, plain, second person), and *do not re-announce
what exists* (the emergency button, trip sharing and number masking are already coded `SUPPORTS`;
presenting them as new measures reaction to something drivers already have).

`# IF YOU CANNOT`: return `{"status": "cannot_render", "reason": "..."}`. The cell is marked
`failed` and logged. It is never filled with a generic paragraph.

### 4.2 Twin — `twin_v1.md`

**Receives** the persona passage, the five scenario paragraphs in randomised order, its own
baseline **numbers**, and the 37-item battery. It receives **no** why-text, **no** open-ended
answers, **no** version code, **no** digits identifying dials, and **no** holdout items (I8).

Rules that matter, each traceable to a defect:

1. Stay in character. Never mention being a model, a twin or a simulation.
2. **Judge each item on its own.** Do not repeat one number across items by habit. *(The prototype's
   straight-lining was a real failure mode.)*
3. A change may matter a lot, a little, or not at all. Report that honestly — including **not at
   all**. *(Without this, every scenario improves every outcome and the placebo test fails.)*
4. Your earlier answers were given **before** this change. Change them only where the change would
   actually change this person's view.
5. Use nothing beyond the persona, the scenario and the baseline.
6. **Each item has its own range and its own anchors, stated beside it.** A 5-point item never
   takes 6 or 7, and the line names what each end of the range — and its midpoint — mean in words.

Rule 6 is stated in the prompt *and* enforced in Python (I13), because the prototype's prompt said
"1 to 7" for every item and its 5-point blocks were silently wrong.

**The anchors are part of rule 6, not an addition to it** (2026-10-12, `docs/DECISIONS.md`). A
range alone does not say which direction it runs in, and the human read a radio row labelled at
every point. For `agree5` and `agree7` the convention covers the gap; for `fair7` and `likely7`,
which reach a twin only through the H3 holdout, it does not — `likely7` has no negative end at all,
so its point 4 is "Moderately likely" rather than a neutral midpoint. `models.twin.BatteryItem`
carries stem, points and anchors together and refuses a count that does not match the range;
`ReferenceData.battery_item` is the only place one is built, so no round can omit them.

`# IF YOU CANNOT`: answer every item anyway; there is no item a person cannot answer. Refusal is
recorded as a failure for that cell, never as a neutral 4.

### 4.3 Checker — `checker_v1.md`

The only LLM step is **coverage**: one call per commitment, with the commitment and the paragraph
as the sole inputs, returning a yes/no with a one-line reason. Temperature **0.0**.

Everything else is deterministic Python: containment scan, word count, reading grade, byte-identity
of dial-0 lines, sham indistinguishability. Gates are specified in `docs/03_RESEARCH_PIPELINE.md`
§4; they are not restated here so they cannot drift.

`# IF YOU CANNOT`: return `entailed: false` with the reason. **Uncertainty is a failure, not a
pass.** A gate that cannot decide has not passed.

### 4.4 Analyst — `analyst_v1.md`

**Receives one deterministically assembled bundle** — the same bundle the Results side panel shows,
in the same order, so the researcher can read the input and the output together:

1. `version_code` and its Fairwork score
2. "What the twins are told" — the per-dial commitment summary
3. The scenario text actually rendered
4. The six shifts, the six baselines, the index, `twins_n`
5. Any computable interactions involving this cell
6. The session's `SHAM − 00000` floor

**Must:** ground every claim in commitments actually shown; state plainly when a shift is smaller
than the sham floor and therefore not interpretable; name sub-additive pairs and what they suggest
about substitutable protections; say when `twins_n` is too small to support a claim.

**Must never** quote a figure absent from the bundle (I12). This is enforced, not requested — §6.

`# IF YOU CANNOT`: return `confidence: "none"` with the reason. A cell with no defensible reading
gets no reading.

### 4.5 Manager — `manager_v1.md`

The only ReAct agent. Decides what runs next within a session, respects the budget, and writes
every decision to `run_events` with `stage='control'` so routing is inspectable rather than
implicit.

It **cannot** choose what a dial means, change a panel, or skip a gate. Its tools read and advance
session state; that is all.

---

## 5. The output contract

**Read `ARCHITECTURE.md` §3.2 first.** This section is how that constraint is discharged.

### 5.1 The provider cannot be trusted

Ollama Cloud accepts `response_format` with `json_schema` **without error and does not enforce it**.
There is no exception and no flag that changes it. Therefore:

- `output_mode` is `tool` or `prompted`. **Never `native`** — forbidden in `build_agent()` and by a
  DDL constraint (`agent_no_native_output`).
- Validation is Python's job, always, for every agent (I13).
- "The schema says so" is never a reason to skip a check.

### 5.2 The twin output shape

Flat. Unconstrained models produce flat key–value output far more reliably than nested structures,
and a flat shape makes a partial answer *repairable* rather than a total loss.

```python
class TwinAnswerSet(BaseModel):
    answers: dict[str, int]      # exactly the 37 battery item ids
    rationale: str = ""          # <= 2 sentences, the person's voice. Never parsed for data.

    @model_validator(mode="after")
    def _check(self):
        expected = set(BATTERY_ITEM_IDS)                    # exactly 37
        got = set(self.answers)
        if got != expected:
            raise ValueError(f"missing={sorted(expected-got)} extra={sorted(got-expected)}")
        for iid, v in self.answers.items():
            pts = SCALE_POINTS[ITEM_SCALE[iid]]             # from the item register, not here
            if not isinstance(v, int) or not 1 <= v <= pts:
                raise ValueError(f"{iid}={v!r} outside 1..{pts}")
        return self
```

`rationale` is display-only and never enters a metric (I12). The per-block "reasons" the prototype
collected are **not** requested: they multiply output tokens by roughly a third for something no
number depends on, and at 1 concurrent request that cost is real.

### 5.3 Normalise, then validate — and know the difference

Normalisation is **syntactic only**. It may repair how a value was written. It may never change
what a value means.

| Allowed (syntax) | Forbidden (meaning) |
|---|---|
| Strip markdown fences, prose before/after JSON | Pad a missing item with the baseline |
| `"6"` → `6` | Clamp `6` on a 5-point item to `5` |
| `6.0` → `6` (exactly integral only) | Round `5.5` to `6` |
| Trim whitespace, normalise key case | Infer an item from a neighbouring one |
| Drop a duplicated key whose values agree | Pick the first of two disagreeing duplicates |

Everything in the right column converts a detectable failure into an undetectable fabrication.
`agents/contract.py` implements the left column and nothing else.

### 5.4 The repair ladder

```
attempt 1 ──► normalise ──► validate ──► OK ──► store
                               │
                              fail
                               ▼
                 targeted repair: re-ask ONLY the defective items,
                 naming them and their ranges, same context
                               │
                          normalise ──► validate ──► OK ──► store (retries = 1)
                               │
                              fail
                               ▼
                 record twin FAILED for this cell only.  Never coerce.
```

**Targeted repair is the important design choice.** Re-asking the whole 37-item battery because
two items were missing wastes a serial slot — the scarcest resource in the system (§ARCH 7.1) — and
re-rolls 35 answers that were already valid, adding variance for no reason. The repair prompt names
the defect precisely:

> `PAC4` and `PAC7` were missing. Return only those two, as whole numbers from 1 to 5.

Valid items from attempt 1 are **kept**. `twin_answers.retries` records how many repairs a vector
needed, so a model or prompt version that needs many is visible in the data rather than hidden.

A twin that fails after repair fails **for that cell only**. It is not dropped from the study and
not dropped from the panel — only the quality gate drops twins.

### 5.5 What the same ladder means for the other agents

| Agent | Invalid output → |
|---|---|
| Design | Re-render once. Then the **cell** fails and is logged (never a generic paragraph). |
| Checker | Any unparseable verdict counts as **not entailed**. Uncertainty fails closed. |
| Analyst | Re-ask once with the offending sentence quoted. Then fall back to the deterministic template (§6.2). |
| Manager | Halt the session and surface the decision to the researcher. Never guess a route. |

---

## 6. Numeric grounding — how the Analyst is stopped from inventing numbers

I12 says no model produces a metric. Prompt instructions are necessary but not sufficient: a model
told "never invent a number" still occasionally does. So it is checked.

### 6.1 The check

After the Analyst returns prose, Python extracts every numeric token from the text and asserts each
one is present in the input bundle.

```python
NUM = re.compile(r"-?\d+(?:\.\d+)?")

def grounded(prose: str, bundle: AnalysisBundle) -> list[str]:
    """Return numeric tokens in `prose` that do not appear in `bundle`. Empty list = grounded."""
    allowed = bundle.numeric_tokens()   # every shift, baseline, index, n, score, code —
                                        # each at full precision AND rounded to 1 and 2 dp
    return [t for t in NUM.findall(prose) if t not in allowed]
```

`numeric_tokens()` is generated from the bundle, never hand-maintained, and includes rounded forms
because "+1.6" is a legitimate rendering of `1.62`. Version codes and Fairwork scores are included.
Ordinals in prose ("the six outcomes", "both levers") are the reason the allowed set also contains
the small integers the bundle structurally implies — `twins_n`, the metric count, the dial values
present — and nothing more.

An unmatched token fails the output, triggers one targeted retry quoting the offending sentence,
and then falls back.

### 6.2 The deterministic fallback

If the Analyst cannot produce grounded prose in two attempts, the run still completes — with a
template-rendered summary built in Python from the same bundle, and
`runs.llm_analysis` prefixed:

> *Generated summary — the analyst agent did not produce a grounded reading for this cell.*

**A cell is never left without a reading, and never given an ungrounded one.** The fallback rate is
itself a reportable diagnostic: if it climbs, the prompt or the model is at fault, and the data says
so.

---

## 7. Determinism and model settings

`docs/09_REPRODUCIBILITY.md` owns the full contract. Three things belong here.

### 7.1 Temperature by agent, and why

| Agent | Temp | Reason |
|---|---:|---|
| Checker | **0.0** | A gate that answers differently on re-run is not a gate. |
| Manager | 0.0 | Routing must be reproducible. |
| Analyst | 0.2 | Readable prose; grounded anyway (§6), so drift is bounded. |
| Design | 0.3 | Needs to write naturally. Output is cached after one render (I4), so it is sampled **once per (lever, dial, style_version)** and then frozen forever. |
| Twin | CONFIG | The live question. See §7.3. |

Design's temperature is less risky than it looks: all 243 cells share 11 strings, so a paragraph is
sampled once and reused byte-identically. Variance enters the study exactly once per lever-dial,
and the Checker gates it before any twin sees it.

### 7.2 Seeds

`ModelRef.seed` is set and persisted on every run. **VERIFY:** whether Ollama Cloud honours `seed`
is undocumented and untested. Assume it does not until measured.

This is why reproducibility does not rest on the seed. It rests on: the render cache (the stimulus
is byte-identical), the answer cache keyed `(twin, code, style, wording)` (a re-run reads, it does
not re-sample), and full provenance (I11) so any round is *reconstructible* even where it is not
bit-identical. The seed is a bonus if it works.

### 7.3 Twin temperature is an empirical question

Validity test 8 (temperature sweep) measures how much answers move across temperatures on the same
twins and the same cell. **Run it before the main study; set the twin temperature from its result;
record it.** Do not pick a number from intuition — the prototype set 1.0 with no evidence, which is
the highest-variance choice available.

Lower is not automatically better: a twin at 0.0 may collapse to modal answers and lose the
between-twin variance the design depends on. The test tells you where the knee is.

---

## 8. Freezing before the main study

Agent Studio has a **Freeze for the main study** control. Freezing an agent:

1. Writes an `agent_config_history` row with `action = 'frozen'`.
2. Sets `agent_configs.frozen = true`, `frozen_at = now()`.
3. Makes the config read-only while any session is running.
4. Records the `prompt_hash` and `version` onto every subsequent run.

Unfreezing is itself a history row, so the audit trail shows the gap. **A session that spans an
unfreeze is flagged in the UI**, because prompts changing mid-study is precisely the thing a
reviewer will ask about.

The Statistics and Results surfaces show the `prompt_hash` set that produced them. Runs made under
different prompt versions are visually distinguished and are **not silently pooled**.
