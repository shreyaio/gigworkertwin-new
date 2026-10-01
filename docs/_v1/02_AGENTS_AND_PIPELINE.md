# 02 — Agents and the variant pipeline

## 1. Five agents, and why not six

| Agent | Job | ReAct? | Tools |
|---|---|---|---|
| **Manager** | Owns the session. Routes, schedules, checkpoints, decides what runs next. | yes | session/run/cursor tools |
| **Design** | DeltaSpec → five lever paragraphs in Uber's voice. | **no** | **none** |
| **Twin** | Persona + round prompt → 37 numbers. Also answers holdouts in quality mode. | **no** | **none** |
| **Checker** | Gates every render: coverage, containment, invariance, identity. | no | deterministic helpers only |
| **Analyst** | Metrics, shifts, index, interactions, written analysis. | yes | metric + history tools |

**No validation agent.** There are two validation jobs and neither wants one:

*Variant validation* is the Checker, which already exists. Most of its work is deterministic (word
count, byte-identity of dial-0 lines, do-not-say substring scan); exactly one step needs a model
(does the paragraph entail this commitment?).

*Twin validation* is the holdout test. The Twin agent answers the six held-out versions; scoring is
**pure Python** — mean absolute error against the human's answers. Putting an LLM in that path would
make the fidelity number nondeterministic, and the fidelity number is precisely what must be stable
across re-runs. It is a **run mode** of the Twin agent plus a scorer function.

**Design and Twin are `react: false` on purpose.** A ReAct loop can fetch. A Design agent that can
fetch a gap can pull threshold 2.2 material into an `01000` render and destroy the difference
between `01000` and `02000` (I2). A Twin that can fetch can read its own holdout answers (I6). Both
get everything they need injected, and nothing else.

## 2. `AgentConfig` — what it holds and what it refuses to hold

```python
# src/twinlab/models/agent.py
from pydantic import BaseModel, Field
from typing import Literal

class ModelRef(BaseModel):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    name: str                              # CONFIG; verify against the provider's live list
    temperature: float = 0.2
    max_tokens: int = 2048
    seed: int | None = None                # pinned per run for reproducibility

class ContextSource(BaseModel):
    """Declarative: what gets injected into the prompt, resolved by the registry."""
    kind: Literal["delta_spec", "anchor_chunks", "style_contract", "persona",
                  "baseline_answers", "battery", "metrics", "run_history"]
    required: bool = True

class RetryPolicy(BaseModel):
    attempts: int = 2
    backoff: Literal["none", "linear", "exponential"] = "exponential"
    on_schema_error: Literal["retry", "fail"] = "retry"

class AgentConfig(BaseModel):
    agent_id: str
    name: str
    role: str
    enabled: bool = True
    model: ModelRef
    system_prompt: str                     # inline, or "file:design_v3.md"
    instructions: list[str] = Field(default_factory=list)
    input_schema: str                      # key into SCHEMA_REGISTRY
    output_schema: str                     # key into SCHEMA_REGISTRY
    tools: list[str] = Field(default_factory=list)      # ALLOW-LIST into TOOL_REGISTRY
    context_sources: list[ContextSource] = Field(default_factory=list)
    react: bool = False
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    version: int = 1
```

**Deliberately absent, and why.** Each of these was considered and rejected — do not add them.

| Not included | Because |
|---|---|
| DB credentials / connection info | Agents never touch the DB. Repositories do. An agent receives data and returns data. |
| Inline prompt templates for each call | Prompts are versioned files under `agents/prompts/`. Inlining them in a DB row makes diffing and review impossible. |
| Output parsing rules / regex | pydantic-ai gives typed output from `output_schema`. A parser field would be a second, competing mechanism. |
| Per-agent rate limits | Rate limiting is a property of the provider and the pool, not the agent. It lives in `app_config.orchestrator`. |
| `max_iterations` for non-ReAct agents | Meaningless when `react: false`. A field that is valid for two of five agents invites misuse. |
| Metric definitions | Metrics are instrument properties (`instrument.json`), not analyst properties. If the analyst owned them, changing the analyst would silently change the measurements. |

**Why `tools` is an allow-list and not a capability flag.** A boolean like `can_read_corpus` grows
one flag per resource and is checked in five places. A name list is checked once, in
`registry.build_agent()`, which looks each name up in `TOOL_REGISTRY` and raises on an unknown one.
The design agent's list is `[]`, which is enforceable and obvious in a config diff.

### 2.1 Adding a sixth agent later (the scalability requirement)

Because behaviour is data:

1. `INSERT` an `agent_configs` row (or add to `config/agents.default.yaml`).
2. Drop a prompt file in `agents/prompts/`.
3. If it needs a new output shape, register a Pydantic model in `SCHEMA_REGISTRY`.
4. If it needs a new tool, register a function in `TOOL_REGISTRY`.

Steps 3 and 4 are the only ones touching Python, and both are single-line registrations. A
future "create an agent" screen writes step 1 and 2 from the UI. **Build the registry indirection
now even though there are five agents** — retrofitting it later means rewriting all five.

```python
# src/twinlab/agents/registry.py
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "DeltaSpec": DeltaSpec, "LeverParagraphSet": LeverParagraphSet,
    "RoundPrompt": RoundPrompt, "TwinAnswerSet": TwinAnswerSet,
    "CheckerReport": CheckerReport, "AnalysisResult": AnalysisResult,
}
TOOL_REGISTRY: dict[str, Callable] = {...}

def build_agent(cfg: AgentConfig) -> Agent:
    unknown = set(cfg.tools) - TOOL_REGISTRY.keys()
    if unknown:
        raise ConfigError(f"{cfg.agent_id}: unknown tools {unknown}")
    return Agent(
        model=resolve_model(cfg.model),
        output_type=SCHEMA_REGISTRY[cfg.output_schema],
        system_prompt=load_prompt(cfg.system_prompt),
        tools=[TOOL_REGISTRY[t] for t in cfg.tools],
        model_settings={"temperature": cfg.model.temperature, "seed": cfg.model.seed},
    )
```

## 3. `TwinConfig`

Mirrors the Settings tab one-for-one.

```python
class TwinConfig(BaseModel):
    model: ModelRef
    persona_template_version: str = "v1"
    wordings: list[str] = ["A", "B"]        # prompt wording variants, for stability checks
    runs_per_wording: int = 1
    quality_runs_per_twin: int = 3
    quality_mae_threshold: float = 1.0      # keep if MAE <= 1.0
    quality_pct_within_1: float = 0.80      # AND >= 80% of items within 1 point
    show_baseline: bool = True              # FIXED true. No no-baseline arm (I8 / pipeline section 4.2)
    randomise_lever_order: bool = True
    seed: int = 20260922
    max_concurrency: int = 4
```

`show_baseline` is typed as a field but is **not a UI control**. It exists so the value is recorded
on every run, not so it can be flipped. Anchoring is a stated limitation bounded by `SHAM − 00000`.

## 4. The variant pipeline

Worked end to end for `01000` — Pay 0, Conditions 1, Contracts 0, Management 0, Representation 0.
Fairwork score 1.

### 4.1 Lookup — deterministic, no model

```python
def lookup(version_code: str) -> DeltaSpec:
    gaps_by_lever = {}
    for pos, lever in enumerate(["L1", "L2", "L3", "L4", "L5"]):
        dial = int(version_code[pos])
        gaps_by_lever[lever] = DIAL_LOOKUP[lever][str(dial)]     # from dial_lookup.json
    commitments = {g: GAPS[g].commitment for lever in gaps_by_lever for g in gaps_by_lever[lever]}
    return DeltaSpec(
        version_code=version_code,
        gaps_by_lever=gaps_by_lever,
        commitments=commitments,
        delta_hash=sha256(json.dumps(gaps_by_lever, sort_keys=True).encode()).hexdigest(),
    )
```

For `01000` this yields exactly three commitments — `2.1.a`, `2.1.b`, `2.1.c` — copied out of
`gaps.json`. No judgement, no model.

### 4.2 The exclusion set — the most important step

Because the Conditions digit is `1` and not `2`, the threshold 2.2 gaps stay **out**: `2.2.a`
(social protection Uber funds), `2.2.b` (standing protected during long absence), `2.2.c` (pay stops
rewarding risk).

If any of those leaks into the text, `01000` and `02000` become the same stimulus and the Conditions
lever stops measuring anything. Most of what the Checker does is guard this line.

```python
def do_not_say(spec: DeltaSpec, lever: str) -> list[str]:
    """Every commitment NOT in this lever's set, plus already-met material."""
    mine = set(spec.gaps_by_lever[lever])
    others = {g for g in ALL_GAP_IDS if g not in mine}
    already_met = {"3.1.a", "3.1.c", "4.1.c"}          # never announce as new
    return sorted(others | already_met)
```

### 4.3 Anchors — two different jobs

`gaps.anchor_sources` for `2.1.*` gives `S15`, `S23`, `S32`. Those chunks are pulled for two reasons
that must not be conflated:

- **To copy the voice.** S15 reads *"Safety is designed into the experience."* Short sentences,
  second person, plain. That is the register to match.
- **To avoid re-announcing what exists.** `chunk_criterion_links` shows Uber's lone-working features
  — emergency button, trip sharing, number masking, 24/7 support — already judged `SUPPORTS`. The
  new text must not present them as new, or the study measures reaction to something drivers have.

### 4.4 The design agent brief — four things, nothing else

1. The commitments for this lever from §4.1.
2. The anchor chunks from §4.3, for register.
3. The style contract (`config/style_contract.yaml`, versioned).
4. The do-not-say list from §4.2.

**Style contract** — constant across all 243 cells, because anything that varies with the cell is a
confound:

```yaml
style_version: v1
person: second
tense: present or near-future
paragraphs_per_lever: 1
word_min: 45
word_max: 70
bullets: false
numbers: only where the GapSpec supplies them
forbidden_terms: [Fairwork, principle, threshold, score, research, study, survey, twin]
dial_zero_text: "No change from today."
lever_order_in_text: fixed
lever_order_to_twin: randomised
```

Expected output for `01000`, Conditions (66 words — inside band):

> Uber now gives you the safety equipment you need for your vehicle, and pays for your training
> instead of expecting you to arrive with it. The safety support already in the app — the emergency
> button, trip sharing, round-the-clock help — is now something you can count on rather than
> something Uber can withdraw. And if you are hurt while working, Uber's cover pays, with the amount
> and the claim steps written down.

Three commitments present. Nothing from 2.2.

### 4.5 The Checker — five gates

```python
class CheckerReport(BaseModel):
    coverage: dict[str, bool]        # gap_id -> entailed by the text
    containment: list[str]           # forbidden commitments detected (empty = pass)
    word_count: int
    in_band: bool
    dial_zero_identical: bool
    sham_indistinguishable: bool | None
    passed: bool
    notes: str
```

1. **Coverage** — every commitment in the DeltaSpec is entailed by the rendered text. *This is the
   one LLM call in the Checker*, and it is a per-commitment yes/no with the commitment and the
   paragraph as the only inputs.
2. **Containment** — nothing from the do-not-say list appears. Deterministic: keyword/semantic scan
   over the forbidden commitments. **A single hit fails the cell.**
3. **Invariance** — word count in `[45, 70]`; reading grade within band; no cell-specific
   intensifiers ("dramatically", "finally", "at last").
4. **Null identity** — every dial-0 lever renders byte-identically to `"No change from today."`
5. **Sham indistinguishability** — `SHAM` must pass every gate a live cell passes: five real
   paragraphs, same band, no `"No change from today."` line. A sham a twin can spot measures nothing.

Fail any → re-render **once** → then halt the cell, mark the run `failed`, log it, and continue to
the next cell. **Never let an unverified variant reach a twin.**

### 4.6 Caching (I4)

```
lever_paragraphs  keyed (lever, dial, style_version)  → 10 non-zero rows, ever
variants          keyed (version_code, style_version) → assembled from paragraph ids
```

Every other cell with `Conditions = 1` reuses this exact paragraph. The design agent runs **10
times per style version, not 243**. Bumping `style_version` invalidates all 10 and nothing else.

## 5. The persona passage

Deterministic, Python only, no LLM. `persona/builder.py`.

**Contract**

- **Total.** Every answered item contributes at least one clause. A field with no template is a
  build error, not a silent skip.
- **First person, plain register.** The passage reads as the driver speaking.
- **Words, not numbers** (I7). `AMQ3` = 6 → *"I agree that my work schedule is made by an automated
  system."*
- **Whys verbatim** (never paraphrased, never translated in place). Non-English responses carry the
  original with a bracketed translation.
- **Fixed order.** identity → work context → household and dependence → how the app manages me →
  how the app guides me → fairness → clarity → satisfaction → staying → working around it →
  leaving → own words.
- **Excludes Parts 15, 16, 17** (I6).
- **Deterministic and hashable.** Same row in, byte-identical passage out. `persona_hash` is stored
  on every run.

```python
TEMPLATES: dict[str, str] = {
  "AMQ3": "{anchor_clause} that my work schedule is made by an automated system.{why}",
  # ... one per battery item + demographics/background. ~50 templates. Frozen, versioned.
}
ANCHOR_CLAUSE = {  # agree7
  1: "I strongly disagree", 2: "I disagree", 3: "I somewhat disagree",
  4: "I neither agree nor disagree", 5: "I somewhat agree", 6: "I agree", 7: "I strongly agree",
}
def why_clause(t: str | None) -> str:
    return f" In my own words: '{t}'" if t else ""
```

A missing template raises `PersonaTemplateMissing`. Do not add a fallback that silently drops an
item — losslessness is the whole point.

## 6. The twin round prompt

Two documents, kept apart (I8).

```
[system]     You are answering as the driver described below. Answer only with numbers.
[persona]    <persona_passage>                      ← whys, open answers, stable
[scenario]   Five lever paragraphs, RANDOMISED order, no code, no digits shown
[baseline]   Your own previous answers: AMQ1=6, AMQ2=5, ...   ← NUMBERS ONLY
[battery]    Re-answer these 37 items given the scenario.
```

The round prompt contains **no** whys, **no** open-ended answers, and **no** version-block items.
`lever_order` and `seed` are persisted on `twin_answers` so any round can be reconstructed exactly.

Output is schema-constrained:

```python
class TwinAnswerSet(BaseModel):
    answers: dict[str, int]
    @model_validator(mode="after")
    def _check(self):
        expected = set(BATTERY_ITEM_IDS)          # exactly 37
        if set(self.answers) != expected:
            raise ValueError(f"missing {expected - set(self.answers)}, extra {set(self.answers) - expected}")
        for iid, v in self.answers.items():
            pts = SCALE_POINTS[ITEM_SCALE[iid]]
            if not 1 <= v <= pts:
                raise ValueError(f"{iid}={v} out of range 1..{pts}")
        return self
```

A schema failure retries once per `RetryPolicy`, then the twin is recorded as failed **for that
cell only** — it is not dropped from the study.

## 7. Twin quality test (fidelity)

Holdout `H3`, Part 17. The twin has never seen these items (I6).

1. Render the six holdout version codes (`12220`, `00222`, `11010`, `11211`, `02211`, `02200`)
   through the **normal pipeline** — same design agent, same checker, same style version.
2. Show each to the twin with its persona. **No baseline is shown** for the holdout, because the
   human had no baseline for it either.
3. Collect 18 numbers (6 versions × fairness/pushback/keep).
4. Score against the human's 18 answers from `survey_responses`.

```python
def score_holdout(human: dict[str,int], twin: dict[str,int]) -> QualityScore:
    errs = [abs(human[i] - twin[i]) for i in H3_ITEM_IDS if i in human]
    mae = sum(errs) / len(errs)
    pct = sum(e <= 1 for e in errs) / len(errs)
    return QualityScore(mae=mae, pct_within_1=pct,
                        kept=(mae <= cfg.quality_mae_threshold and pct >= cfg.quality_pct_within_1))
```

Run `quality_runs_per_twin` times (default 3) and average before the keep/drop decision, so one bad
sample does not drop a good twin. The mock's wording — *"17 of 20 twins kept (error 1.0 or less,
80 per cent within 1 point)"* — is exactly this.

**Holdout H2** (Part 16) is the second holdout, scored identically against its single scenario. It
is run on demand, not as part of the keep/drop gate.

**Updates propagate.** Writing a `twin_quality_runs` row demotes the previous `is_latest` in the
same transaction, so every surface reading quality — Twins list, quality page, analyst `twins_n` —
reads the new number with no cache to invalidate.

## 8. Analyst maths

### 8.1 Metric scoring

Six outcome metrics. Reverse-code first, then mean the raw items **on their own scale** — no
rescaling of 5-point blocks to 7.

```python
METRICS = {
  "fairness":  (["FAIR1","FAIR2","FAIR3","FAIR4"], "extent7"),
  "clarity":   (["CLAR1","CLAR2","CLAR3"],         "agree5"),
  "happiness": (["SAT1","SAT2","SAT3"],            "agree7"),   # SAT2 reverse
  "staying":   (["CONT1","CONT2"],                 "agree5"),
  "pushback":  (["ALGO1","ALGO2","ALGO3","ALGO4"], "agree7"),
  "leaving":   (["TURN1","TURN2","TURN3"],         "agree7"),
}
def score(answers: dict[str,int], metric: str) -> float:
    ids, scale = METRICS[metric]
    pts = SCALE_POINTS[scale]
    vals = [(pts + 1 - answers[i]) if ITEMS[i].reverse_coded else answers[i] for i in ids]
    return sum(vals) / len(vals)
```

### 8.2 Shift and index

Baseline is the twin's **own survey answers**; variant is the twin's answers under the cell.

```python
shift[m]      = mean_over_twins(score(variant, m)) - mean_over_twins(score(baseline, m))
index         = mean([ shift.fairness, shift.clarity, shift.happiness,
                       shift.staying, -shift.pushback, -shift.leaving ])
```

Pushback and leaving are sign-flipped because less of each is better for the driver.

**Verified against the mock**, all ten rows. `21122`: (1.62 + 0.60 + 1.50 + 0.68 + 2.05 + 1.02) / 6
= **1.245** ✓. Also `11122` → 1.098, `00222` → 0.843, `00111` → 0.525, `11000` → 0.338,
`10000` → 0.223, `00010` → 0.220, `00001` → 0.148, `01000` → 0.143.

**Known limitation, carry it into the paper.** The index averages 5-point and 7-point shifts
unweighted. It reproduces the mock and is the display number; per-metric shifts are stored so a
standardised index can be computed at modelling time.

### 8.3 Interactions

```python
def interaction(code_a: str, code_b: str, metric: str) -> Interaction | None:
    """Both singleton cells and the joint cell must exist, or return None. Never impute."""
    joint = combine(code_a, code_b)       # elementwise max of the two dial vectors
    a, b, ab = (latest_run(c) for c in (code_a, code_b, joint))
    if not all((a, b, ab)): return None
    extra = ab.shift[metric] - (a.shift[metric] + b.shift[metric])
    return Interaction(a=code_a, b=code_b, joint=joint, metric=metric,
                       alone_a=a.shift[metric], alone_b=b.shift[metric],
                       together=ab.shift[metric], extra=extra,
                       verdict="sub-additive" if extra < 0 else "super-additive" if extra > 0 else "additive")
```

Reproduces the mock's panel: *"staying changes +0.31 and +0.09 alone, +0.22 together. The extra is
−0.18, so together they add less than the sum."*

The Results panel renders an interaction **only when all three cells have completed runs**. If one
is missing it says which code to run — never an estimate.

### 8.4 The written analysis

The Analyst receives, deterministically assembled — the same bundle the Results side panel shows:

1. `version_code` and its Fairwork score
2. "What the twins are told" — the per-dial commitment summary
3. The scenario text actually rendered for this cell
4. The six shifts, the six baselines, the index, `twins_n`
5. Any available interactions involving this cell
6. `SHAM − 00000` for that session, as the demand-characteristic floor

It returns `AnalysisResult(summary, mechanism, caveats, confidence)`. The prompt is under
`agents/prompts/analyst_v1.md` and must instruct:

- Explain **why** a lever moved a metric, grounding the claim in the commitments actually shown.
- State when a change is smaller than the sham floor and therefore not interpretable.
- Never invent a number. Every figure quoted must be in the input bundle.
- Name the sub-additive pairs and say what they suggest about substitutable protections.
- Say plainly when `twins_n` is too small to support a claim.

The output is stored on `runs.llm_analysis`. It is a *reading* of the numbers; the numbers
themselves are computed in Python and are never produced by a model.
