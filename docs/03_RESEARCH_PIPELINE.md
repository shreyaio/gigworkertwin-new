# 03 — The research pipeline

From a version code to 37 integers. Lookup, render, check, persona, round prompt, controls, panel.

Normative. Metrics and statistics are in `docs/07`; the quality gate and validity tests are in
`docs/08`.

---

## 1. The chain

```
version code ──► lookup ──► DeltaSpec ──► render ──► 5 paragraphs ──► CHECK ──┐
                (no model)   (frozen)     (cached)                            │ gate
                                                                              ▼
 survey row ──► persona passage ──────────────────► TWIN ◄───── round prompt ─┘
                (no model, lossless)                  │         + own baseline numbers
                                                      ▼
                                                 37 integers
                                                      │
                                                      ▼
                                         Python: score, shift, index  (docs/07)
```

The model appears in exactly three places — writing the stimulus, being the twin, writing the
commentary — and in none of them does it choose a treatment or compute a number.

---

## 2. Lookup — deterministic, no model

```python
def lookup(version_code: str) -> DeltaSpec:
    gaps_by_lever = {}
    for pos, lever in enumerate(["L1", "L2", "L3", "L4", "L5"]):
        dial = int(version_code[pos])
        gaps_by_lever[lever] = DIAL_LOOKUP[lever][str(dial)]      # dial_lookup.json
    commitments = {g: GAPS[g].commitment
                   for lever in gaps_by_lever for g in gaps_by_lever[lever]}
    return DeltaSpec(
        version_code=version_code,
        gaps_by_lever=gaps_by_lever,
        commitments=commitments,
        delta_hash=sha256(json.dumps(gaps_by_lever, sort_keys=True).encode()).hexdigest(),
    )
```

Pure. Same code in, byte-identical DeltaSpec out, forever (I1). `lookup("00000")` returns zero
commitments, `lookup("01000")` three, `lookup("02000")` six, `lookup("22222")` thirty.

### 2.1 Worked: `01000`

Pay 0, **Conditions 1**, Contracts 0, Management 0, Representation 0. Fairwork score 1. Four levers
do nothing; one does all the work.

The Conditions digit is `1`, so take only the threshold 2.1 gaps — three of them, copied out of
Table D:

| Gap | Type | Commitment |
|---|---|---|
| `2.1.a` | INTRODUCE | Supply safety equipment at no cost, and pay for induction and refresher training, instead of requiring the driver to arrive already trained. |
| `2.1.b` | REMOVE | Delete the clause making safety and support services discretionary, so the features already built are commitments rather than favours. |
| `2.1.c` | INTRODUCE | Provide accident and injury cover at Uber's cost, with a published sum insured, named insurer and claims route. |

Three sentences. No judgement, no model.

---

## 3. The exclusion set — the most important step in the pipeline

Because the digit is `1` and not `2`, the threshold 2.2 gaps stay **out**:

- `2.2.a` — social protection Uber actually funds
- `2.2.b` — standing protected during a long absence
- `2.2.c` — pay stops rewarding risk-taking

**If any of those leaks into the text, `01000` and `02000` become the same stimulus and the
Conditions lever stops measuring anything.** Most of what the Checker does is guard this line.

```python
def do_not_say(spec: DeltaSpec, lever: str) -> list[str]:
    """Every commitment NOT in this lever's set, plus already-met material."""
    mine = set(spec.gaps_by_lever[lever])
    others = {g for g in ALL_GAP_IDS if g not in mine}
    already_met = {"3.1.a", "3.1.c", "4.1.c"}       # never announce as new
    return sorted(others | already_met)
```

The already-met three matter for a second reason: announcing something Uber already does measures
reaction to a thing drivers already have. That is the sham's job, deliberately and in one place
(§6.2) — never an accident in a live cell.

---

## 4. Render

### 4.1 The brief

Four things, nothing else (`docs/02` §4.1): this lever's commitments, anchor chunks for register,
the style contract, the do-not-say list.

`gaps.anchor_sources` for `2.1.*` gives `S15`, `S23`, `S32`. Those chunks are pulled for two jobs
that must not be conflated:

- **Copy the voice.** S15 reads *"Safety is designed into the experience."* Short sentences, second
  person, plain. That is the register to match.
- **Do not re-announce what exists.** `chunk_criterion_links` shows the emergency button, trip
  sharing, number masking and 24/7 support already judged `SUPPORTS`.

### 4.2 The style contract

`config/style_contract.yaml`. **Constant across all 243 cells — anything that varies with the cell
is a confound.**

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
forbidden_intensifiers: [dramatically, finally, at last, revolutionary, unprecedented, historic]
reading_grade_min: 4.0          # Flesch-Kincaid
reading_grade_max: 16.0
dial_zero_text: "No change from today."
lever_order_in_text: fixed
lever_order_to_twin: randomised
```

Expected output for `01000`, Conditions — 66 words, inside band:

> Uber now gives you the safety equipment you need for your vehicle, and pays for your training
> instead of expecting you to arrive with it. The safety support already in the app — the emergency
> button, trip sharing, round-the-clock help — is now something you can count on rather than
> something Uber can withdraw. And if you are hurt while working, Uber's cover pays, with the
> amount and the claim steps written down.

Three commitments present. Nothing from 2.2.

### 4.3 The rendering economy

A version code's five paragraphs are assembled from a pool of exactly **11 strings**: ten non-zero
lever paragraphs (5 levers × 2 dials) plus the one fixed dial-0 line. Cached on
`(lever, dial, style_version)`.

**So the design agent runs 10 times per style version, not 243.** All 243 cells are permutations of
those 11 strings.

This buys a second, more important thing: it makes the levers *structurally* independent. Every
cell with Conditions = 1 shows the **byte-identical** Conditions paragraph. There is no per-cell
wording variation to confound a lever comparison. Bumping `style_version` invalidates all ten and
nothing else.

**Dial 0 is never generated.** `"No change from today."` is a constant (I5).

> **Two different artefacts, easily confused.** The *scenario paragraph* is twin-facing prose,
> 45–70 words, no bullets. "**What the twins are told**" is a *researcher-facing* bullet summary of
> the selected commitments, rendered per lever as `Pay step 1 / Pay step 2`, shown on the Dial
> board, the Results panel and the Twins panel. They come from the same DeltaSpec and must never be
> swapped: a twin never sees bullets, and the researcher's summary is never fed to a model.

---

## 5. The Checker — five gates

Every render passes before any twin sees it (I3). Fail any → re-render **once** → then halt that
cell, mark the run `failed`, log it, and continue to the next code. **An unverified variant never
reaches a twin.**

```python
class CheckerReport(BaseModel):
    coverage: dict[str, bool]        # gap_id -> entailed by the text
    containment: list[str]           # forbidden commitments detected (empty = pass)
    word_count: int
    in_band: bool
    reading_grade: float
    dial_zero_identical: bool
    sham_indistinguishable: bool | None
    passed: bool
    notes: str
```

| # | Gate | Asks | How |
|---|---|---|---|
| 1 | **Coverage** | Is every commitment in the DeltaSpec entailed by the text? | LLM, one call per commitment, temp 0.0. The only model step. |
| 2 | **Containment** | Is anything present that is *not* in the spec? | Deterministic. Keyword and semantic scan over the do-not-say list. **A single hit fails the cell.** |
| 3 | **Invariance** | 45–70 words, reading grade in band, no cell-specific intensifiers. | Deterministic. |
| 4 | **Null identity** | Does every dial-0 lever render the byte-identical string? | Deterministic, byte comparison. |
| 5 | **Sham indistinguishability** | Does SHAM pass every gate a live cell passes, with no `"No change from today."` line? | Deterministic + gates 1–3. |

**Gate 2 is asymmetric on purpose.** Coverage failing means the stimulus is weaker than intended —
bad, recoverable, detectable in the data. Containment failing means two cells are no longer
distinguishable — which silently destroys a lever comparison and is not detectable downstream. One
containment hit fails the cell; there is no threshold and no tolerance.

**Uncertainty fails closed.** A coverage call that cannot decide returns `entailed: false`.

---

## 6. The two twin control cells

Exactly two. **No third is ever added.**

### 6.1 `00000` — the noise floor

Five identical `"No change from today."` lines. Measures how much a twin's answer moves when
nothing changed. Every twin's baseline for every shift is its **own survey answers**, so each
driver is their own control; `00000` bounds the instrument's own instability on top of that.

`00000` is answered once per twin per config, inside the twin quality test (RESEARCHER 2026-10-05).
A session does not ask it: the session records its floor from the panel's stored answers and
consumes no iteration. It is **blocked from the Dial board's "Ask the twins" button** — it is a
control the orchestrator records, not a cell a researcher pokes at.

### 6.2 `SHAM` — the demand-characteristic floor

Five ordinary paragraphs, same word band and voice as a live cell, describing the three things Uber
**already does** (`3.1.a`, `3.1.c`, `4.1.c`). Measures how much a twin moves simply because it was
shown change-shaped text.

**Zero free parameters.** Its content is the three `Met` criteria read straight out of
`criterion_findings.json`. We did not pick a plausible-sounding placebo; the codebook named it.

SHAM is answered once per twin per config inside the quality test, like `00000` (§6.1). It occupies
`dial = 3` in `lever_paragraphs`: its unfilled levers announce that lever's *existing*
driver-facing policy, so they are neither dial-0 lines nor live-cell paragraphs. Its containment
gate is scoped to that existing policy. Researcher-approved; see `docs/DECISIONS.md`.

**`SHAM − 00000` is the floor.** Any live cell whose shift is smaller than it is **not
interpretable**, and the Analyst is instructed to say so (`docs/02` §4.4). It is reported with
every cell.

---

## 7. The persona passage

Deterministic, Python only, no LLM. `persona/builder.py`.

### 7.1 Contract

- **Lossless over the battery.** Every answered item contributes at least one clause. A field with
  no template raises `PersonaTemplateMissing` — it is never silently skipped (I6).
- **First person, plain register.** The passage reads as the driver speaking.
- **Words, not numbers** (I7). `AMQ3 = 6` → *"I agree that my work schedule is made by an automated
  system."* A twin shown numbers does arithmetic instead of reasoning from experience.
- **Whys verbatim.** Every why-probe is carried word for word, never paraphrased. Non-English
  answers keep the original with a bracketed translation.
- **Excludes Parts 15, 16 and 17 absolutely** (I6). A twin that has read its own holdout answers
  cannot be validated.
- **Fixed order**, always: identity → work context → household and dependence → how the app manages
  me → how the app guides me → fairness → clarity → satisfaction → staying → working around it →
  leaving → own words.
- **Deterministic and hashable.** Same row in, byte-identical passage out. `persona_hash` is stored
  on every run.

```python
TEMPLATES: dict[str, str] = {
  "AMQ3": "{anchor_clause} that my work schedule is made by an automated system.{why}",
  # one per battery item + demographics/background. ~50 templates. Frozen, versioned.
}
ANCHOR_CLAUSE = {
  "agree7": {1:"I strongly disagree", 2:"I disagree", 3:"I somewhat disagree",
             4:"I neither agree nor disagree", 5:"I somewhat agree", 6:"I agree",
             7:"I strongly agree"},
  "agree5": {1:"I strongly disagree", 2:"I disagree",
             3:"I neither agree nor disagree", 4:"I agree", 5:"I strongly agree"},
  # ... one map per scale. A 5-point item NEVER borrows the 7-point wording.
}
```

**Anchor clauses are per scale.** Using the 7-point wording for a 5-point item would render a `4`
as "I agree" in one block and "I neither agree nor disagree" in another — the same number meaning
two different things inside one passage.

**Part 14 own-words** has no `item_id` and the 73-item register is frozen, so it travels in
`twins.background` and is appended verbatim as the closing section. Without this the persona
silently loses the driver's own words.

### 7.2 Why no LLM here

A model-written persona would be a paraphrase, and a paraphrase is lossy in a way nobody can audit.
Determinism also means the passage is hashable, and the hash is what ties a result back to the exact
text that produced it (I11).

---

## 8. The round prompt

Two documents, kept apart (I8).

```
[system]     twin_v2.md
[persona]    <<<PERSONA>>>    whys, open answers, stable, no numbers
[scenario]   <<<SCENARIO>>>   5 lever paragraphs, RANDOMISED order, no code, no dial digits
[baseline]   <<<BASELINE>>>   OMITTED by default since 2026-10-07 (show_baseline=false) — see below
[battery]    <<<BATTERY>>>    the 37 items to re-answer, each with its own range
```

The round prompt contains **no** whys, **no** open-ended text, **no** holdout items, **no** version
code and **no** dial digits.

**Why persona and round prompt are separate.** If the whys travelled with the stimulus, every twin
would restate its own justifications under every counterfactual, and the twin would look immovable
no matter what you showed it. The persona explains who this person is; the round prompt asks what
they would now say.

**Lever order is randomised per twin per round**, so paragraph position cannot become a confound.
The order actually shown, the seed, the wording variant, the persona hash, the delta hash, the style
version, the prompt version and the model name are all persisted on `twin_answers` (I11), so any
round is reconstructible byte-for-byte.

**Baseline is not shown, by default, since 2026-10-07** (`docs/DECISIONS.md`). This section used to
argue the opposite: that anchoring a twin to its own baseline numbers was what kept it recognisably
its own driver, bounded by `SHAM − 00000`. That bound did not hold in practice — the twin prompt
told the model, in words, that leaving a number unchanged was a normal answer, and a twin shown its
own numbers overwhelmingly did exactly that. The `00000` control came back at an index of `0.000` in
most sessions checked, which is not a measured noise floor, it is the twin complying with an
instruction. `show_baseline` remains a recorded field, not a UI control — a researcher-set default,
not a per-run toggle — but the default is now `false`. A twin's tie to its own driver now runs
entirely through the persona passage (§7), which is already where `docs/08` §4 test 1 looks.

---

## 9. The frozen analysis panel

Invariant I14, and the reason a 500-twin study is affordable (`docs/10`).

### 9.1 The draw

At session creation, once:

```python
def draw_panel(session: Session) -> list[PanelMember]:
    eligible = [t for t in twins
                if t.source in session.population_sources          # real | synthetic | both
                and latest_quality(t, "H3").kept]                  # quality-passed only
    rng = random.Random(session.panel_seed)
    strata = group_by(eligible, key=lambda t: f"{t.city}|{t.service}")
    return proportional_stratified_sample(strata, session.panel_size, rng)
```

Stratified on `city × service`, proportional to the eligible population, seeded, and written to
`session_panel` with a draw `position` so it is reproducible from the seed alone.

### 9.2 Why it must be frozen

Shifts are **within-subject**. The interaction

```
extra = shift(A ∪ B) − (shift(A) + shift(B))
```

is meaningless if A, B and A∪B were answered by different people — the differences would carry
between-person variance, not the effect of combining protections. I14 exists for exactly this.

### 9.3 What it does not bound

All consented twins are still built, persona'd and quality-tested. Statistics analyses **human
survey rows** and does not touch the panel at all. The panel bounds the counterfactual sweep and
nothing else.

Manual twins (`source = 'manual'`) are never eligible: they have no real survey row and therefore
no holdout and no quality score.

### 9.4 Comparing sessions

Two sessions with different panels are **not differenced** without an explicit, logged decision.
The UI shows the panel hash beside any cross-session comparison, and refuses to compute an
interaction whose legs come from different panels.

---

## 10. Asking

```
for each version code:
  ├─ lookup    → DeltaSpec               deterministic
  ├─ render    → 5 lever paragraphs      cached on (lever, dial, style_version)
  ├─ check     → CheckerReport           gate; failure halts this cell only
  ├─ ask       → 37 answers × K twins    cached on (twin, code, style, wording)
  └─ analyse   → metrics, index, prose   Python first, model last
  checkpoint after every unit
```

Twin answers cache on `(twin_id, version_code, style_version, wording)`, so a sweep is paid for
once and a resume does not re-pay for completed work.

**Wordings.** `wordings` (CONFIG, default `["A"]`) are prompt phrasing variants used by validity
test 5 (order and wording swap). Running two wordings doubles the cost of a sweep; it is a
robustness check, not the default.

`runs_per_wording` (default 1) repeats the same twin on the same cell. Greater than 1 gives a
per-twin stability estimate at linear cost. The averaging rule is in `docs/07`.

---

## 11. Failure semantics

| Event | Consequence |
|---|---|
| Lookup raises | Impossible by construction; a bug, not a runtime path. Halt the session. |
| Design returns `cannot_render` | Re-render once, then the **cell** fails. Never a generic paragraph. |
| Checker fails any gate | Re-render once, then the **cell** fails, logged with the failing gate. |
| Twin output invalid after repair | That **twin fails for that cell only**. Not dropped from the study. |
| Provider 429 / 5xx | Backoff, 3 attempts, then that twin fails for that cell. |
| `PersonaTemplateMissing` | Reconstruction fails for that twin, logged, loop continues. |
| `twins_n = 0` after all twins fail | Run `failed` (I15). Never a result of zero. |

Every one writes a `run_events` row with `status='error'` and the exception in `payload`, so a
failure is visible in the UI and not only in stderr.

---

## 12. What makes the resulting number trustworthy

Every claim can be traced backwards without a gap:

> an index value
> → six metric shifts
> → 37 integers per twin
> → the exact round prompt, reconstructible from the stored seed, lever order, persona hash and
>   prompt version
> → five checker-verified paragraphs
> → a commitment set that is a table lookup
> → gaps read from a codebook
> → findings coded against Fairwork criteria
> → verbatim extracts of Uber's own published policy, cited

And the instrument is calibrated: only twins that reproduced their human on unseen stimuli
contributed, and every effect is reported against both a null floor (`00000`) and a
demand-characteristic floor (`SHAM`).
