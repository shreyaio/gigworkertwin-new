# 09 — Reproducibility

The determinism contract: what is guaranteed, what is not, and how a result is traced to its cause.

Normative.

---

## 1. Be honest about what is reproducible

A language model sits in three places in this pipeline. Claiming bit-identical reproducibility end
to end would be false, and a reviewer will find it. So the contract is stated in three tiers, and
every part of the system is assigned to one.

| Tier | Guarantee | Applies to |
|---|---|---|
| **A — Deterministic** | Same input → byte-identical output, always, on any machine | Lookup, persona, metrics, shifts, index, interactions, odometer, hashes, export |
| **B — Frozen** | Sampled once, then reused byte-identically forever | Lever paragraphs, variants, twin answers (cached), the analysis panel |
| **C — Reconstructible** | Not bit-identical on re-sampling, but the exact input is recoverable and the output is stored forever | Twin answers on first sampling, checker coverage calls, analyst prose |

**Tier A is most of the study.** Every number that reaches the paper — every metric, shift, index
and interaction — is Tier A arithmetic over Tier B stored data.

Tier C is the honest boundary. A re-sampled twin answer will not match bit-for-bit, and the design
does not require it to: the original answer is stored, append-only, and the prompt that produced it
is rebuildable from stored fields. **Reproducibility here means an auditor can verify what happened,
not that a coin lands the same way twice.**

---

## 2. Why caching is the primary determinism mechanism

This is the part that is easy to miss. The three caches (`docs/04` §6) are not only a cost
optimisation — they are what moves most of the pipeline from Tier C to Tier B.

- A lever paragraph is sampled **once per `(lever, dial, style_version)`** and reused byte-identically
  across every cell that includes it. Variance enters exactly ten times per style version, and the
  Checker gates each one before any twin sees it.
- A twin answer is cached on `(twin_id, version_code, style_version, wording)`. **A re-run reads; it
  does not re-sample.** Re-opening a result a year later returns the same numbers because they are
  the same numbers.
- All 243 cells are permutations of 11 strings, so every cell with `Conditions = 1` shows the
  *identical* paragraph. There is no per-cell wording variation to confound a lever comparison
  (`docs/03` §4.3).

Remove the caches and the study becomes non-reproducible — not slower. That is why `docs/04` says
not to invent a fourth cache and not to bypass an existing one.

---

## 3. The provenance chain

Every claim traces backwards without a gap. This is the chain a reviewer walks, and every arrow is a
stored field or a pure function:

```
an index value
  └─ six metric shifts                    Python, Tier A
      └─ 37 integers per twin             twin_answers, append-only
          └─ the round prompt              REBUILT from persona_hash + seed + lever_order
          │                                 + style_version + wording + prompt_hash
          └─ five checker-verified paragraphs   variants → lever_paragraphs
              └─ a commitment set          pure lookup over dial_lookup.json
                  └─ gaps                  codebook Table D
                      └─ findings          coded against Fairwork criteria
                          └─ verbatim extracts of Uber's published policy, cited
```

The UI implements this as `provenance_link` (`docs/05` §4.4): two clicks from any number on any
screen to Uber's own words.

---

## 4. Hashes

Five, each `sha256`, each stored on the rows it explains.

| Hash | Over | Stored on | Answers |
|---|---|---|---|
| `persona_hash` | the persona passage bytes | `twins`, and every run | Which text grounded this twin? |
| `delta_hash` | the sorted gap ids, JSON, sorted keys | `variants`, `lever_paragraphs` | Which commitments did this cell close? |
| `prompt_hash` | the resolved prompt file text | `agent_configs`, `twin_answers` | Which instructions produced this? |
| `panel_hash` | the sorted twin ids of the frozen panel | `sessions` | Which twins answered? |
| `reference_hash` | all ten `data/reference/*.json` | build artefact, asserted at boot | Which codebook build? |

**`panel_hash` is what makes cross-session comparison safe** (I14). The UI shows it beside any
comparison and refuses an interaction whose legs come from different panels.

**`reference_hash` is checked at startup**, not only in the seeder. A Space pointed at the wrong
Supabase project, or running against a drifted reference build, refuses to start rather than quietly
producing results against the wrong codebook (`docs/04` §10).

---

## 5. Seeds

Four, all stored, all independent.

| Seed | Controls | Tier |
|---|---|---|
| `sessions.panel_seed` | which twins are drawn into the panel | **A** |
| `twin_answers.seed` | the lever-order randomisation for that round | **A** |
| `analysis_runs.seed` | bootstrap resampling | **A** |
| `synthetic_batches.seed` | generated survey data | **A** |
| `ModelRef.seed` | provider sampling | **C — unverified** |

The first four are ours and are genuinely deterministic: same seed, same draw, on any machine.

**`ModelRef.seed` is different. VERIFY:** whether Ollama Cloud honours `seed` is undocumented and
untested. **Assume it does not until measured**, and measure it early — one twin, one cell, the same
seed, ten times. If the vectors are identical, record that; if not, record that too.

Nothing in the contract depends on the answer. Tiers A and B carry the study; a working model seed
would be a bonus that moves some Tier C work to Tier B.

---

## 6. What is recorded on every run

The complete set, so a round is reconstructible byte-for-byte (I11):

```
persona_hash · delta_hash · prompt_hash · panel_hash
style_version · wording · lever_order · seed
model name · provider · temperature · max_tokens · output_mode
config_version · agent version · retries
started_at · finished_at · latency_ms
```

**The prompt itself is never stored** (`docs/04` §7.2). It is rebuilt from these fields on demand.
At sweep scale, storing prompt bodies would exhaust the 500 MB tier on its own — and a rebuilt
prompt verified against its hash is stronger evidence than a stored copy, because it proves the
rebuild path works.

`rebuild_round_prompt(twin_answer_id) -> str` is a supported operation with its own test: it
reconstructs a stored round and asserts the result hashes to the recorded value.

---

## 7. Freezing before the main study

Reproducibility is not only about replaying the past; it is about the study not moving underneath
itself while it runs.

**Freeze, in this order, before the first main-study session:**

1. **Reference data** — already frozen and committed. `build_reference.py --check` exits 0.
2. **`style_version`** — bumping it invalidates all ten lever paragraphs and changes every stimulus.
3. **Agent configs and prompts** — `Freeze for the main study` (`docs/02` §8). Each records its
   `prompt_hash`.
4. **`TwinConfig`** — model, temperature (set from validity test 8), thresholds, wordings, panel
   size.
5. **The panel** — drawn at session creation and written to `session_panel`.

A session that spans an unfreeze is **flagged in the UI**, because prompts changing mid-study is
precisely what a reviewer will ask about. Runs made under different `prompt_hash` values are
visually distinguished and are **never silently pooled**.

---

## 8. The audit trail

`run_events` is append-only and forms a tree via `parent_event_id`. It is the audit trail, not a
progress bar: every stage, every agent call, every gate verdict, every routing decision and every
error is a row, and the side panel shows each one's inputs, outputs and telemetry.

**Nothing is ever overwritten** (I9). A rerun appends a new `runs` row and flips
`is_latest_for_version` in the same transaction; the superseded run stays queryable forever. The
same pattern covers `twin_quality_runs`. There is no UI path that deletes evidence
(`docs/05` §5.1).

Three consequences worth stating plainly:

- **A result can be re-derived from the log alone.** Given the events for a session, the metrics can
  be recomputed independently of `runs.metrics` — and a test does exactly that.
- **A superseded result is still readable.** "What did this cell say before we re-rendered?" is a
  query, not an archaeology exercise.
- **A failure is as durable as a success.** Failed cells, failed twins, `INCONCLUSIVE` tests and
  checker rejections all persist. A study that only retains its successes has no denominator.

---

## 9. Environment provenance

Recorded at startup and stamped on every session's `config`:

```
app version (git sha) · python version · gradio · pydantic-ai · openpls-engine
reference_hash · model name and provider · deployment target (zerogpu | docker | local)
```

`openpls-engine` version is also stored on `analysis_runs` (`docs/01` §6.8) and shown on every
Statistics view, because the paper must state which implementation produced the numbers.

---

## 10. What ships with the paper

An independent researcher should be able to verify the chain without access to this Space.

| Artefact | Contains | Why |
|---|---|---|
| `data/reference/*.json` + `reference_hash` | The whole codebook, corpus and instrument | The treatment is a lookup over these; anyone can verify a DeltaSpec |
| The 11 lever paragraphs, per style version | Every stimulus any twin ever saw | All 243 cells are permutations of these |
| `config/` at the frozen versions | Style contract, twin config, agent configs, prompt files + hashes | The apparatus |
| Per-cell results | Six shifts, six baselines, index, `twins_n`, panel hash | The findings |
| The export matrix | One row per respondent, with scales | The measurement layer, independently re-analysable |
| Validity results | All eight tests, including failures | The method's own evidence |
| Aggregate quality | Per-twin MAE and % within 1, and the drop count | The instrument's calibration |

**What does not ship:** persona passages and verbatim why-text. They are identifiable free text from
gig workers who consented to research, not to publication. `persona_hash` is published so a
passage's identity is verifiable without disclosing it; the passages themselves stay in the
database, and anything released is aggregated.

This is a research-ethics constraint, not a technical one, and it is the one place where the
otherwise-complete chain is deliberately cut.
