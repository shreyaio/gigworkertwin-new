# 10 — Scale and cost

The capacity model. What a study costs in calls, tokens, time and bytes, and what to cut first.

Normative for the budget mechanism and the degradation ladder. The arithmetic is a model — calibrate
it against measurement before the first real sweep.

---

## 1. Three hard limits

**VERIFY** — all three were true on 2026-09-28 and must be re-checked before the first live run.

| Limit | Value | Consequence |
|---|---|---|
| **Ollama Cloud free: 1 concurrent request** | Pro 3, Max/Team 10 | Every twin call is serial. `max_concurrency` defaults to **1**. |
| **Ollama Cloud credits** | unpublished "starter amount", monthly reset, no rollover; 5-hour session and 7-day weekly limits | **The binding constraint, and its value is unknown.** Read it off the account. |
| **Supabase free: 500 MB** | 1 GB storage, 5 GB bandwidth, pauses after 7 days idle | Fine at panel scale; §5 shows where it is not. |

Plus: the HF Space sleeps after 48 h idle, has **ephemeral disk**, and on a free account is a
ZeroGPU Gradio Space (`ARCHITECTURE.md` §8).

**No published RPM or TPM.** Usage is metered in credits against per-model token rates. So the model
below is denominated in **calls and tokens**, and credits are derived once the rate is known.

---

## 2. What costs a call

| Operation | Calls | Note |
|---|---|---|
| Render a lever paragraph | 1 | **10 total per `style_version`** (I4), not per cell |
| Checker coverage probe | 1 per commitment | Only on a fresh render; up to 30 at `22222` |
| Ask one twin about one cell | 1 | Cached on `(twin, code, style, wording)` — paid once |
| Targeted repair | 1 | Only when validation failed; tracked in `twin_answers.retries` |
| Quality gate, one twin | 6 × `quality_runs_per_twin` | Default 3 → **18 calls per twin** |
| H2 validation, one twin | 1 | The twin's own arm |
| Analyst prose, one cell | 1 | Plus at most one grounding retry |

Two facts do most of the work: **rendering is 10 calls for the whole study**, and **twin answers
cache**, so a resumed or re-opened sweep costs nothing.

---

## 3. The capacity model

At ~8 s per twin call (≈2,300 tokens in, ≈400 out on a 120B-class cloud model), serial.

### 3.1 A full study

| Stage | N=100, K=20 | N=250, K=20 | **N=500, K=20** | N=500, K=50 |
|---|---:|---:|---:|---:|
| Quality gate (`N × 6 × 3`) | 1,800 | 4,500 | **9,000** | 9,000 |
| H2 validation (`N`) | 100 | 250 | 500 | 500 |
| Design renders | 10 | 10 | 10 | 10 |
| Controls (`2K`) | 40 | 40 | 40 | 100 |
| Sweep (`K × 243`) | 4,860 | 4,860 | **4,860** | 12,150 |
| Validity tests (`9K`) | 180 | 180 | 180 | 450 |
| **Total calls** | **6,990** | **9,840** | **14,590** | **22,210** |
| **Serial time** | 15.5 h | 21.9 h | **32.4 h** | 49.4 h |
| **Tokens** | 18.9 M | 26.6 M | **39.4 M** | 60.0 M |

### 3.2 The result that should change your planning

**At N=500, the quality gate costs 20 hours and the entire 243-cell sweep costs 10.8.**

The dominant cost of this study is not the counterfactual experiment. It is **validating 500 twins
at 18 calls each**. That is where the levers are (§6), and it is the opposite of where intuition
puts them.

The sweep is cheap because the panel is frozen (I14) and answers cache. The gate is expensive
because it scales with the *human sample*, which is the number you cannot reduce by design choice.

### 3.3 Sweep cost by panel size

| K | Calls | Serial hours | Days | Tokens |
|---:|---:|---:|---:|---:|
| **20** (default) | 4,860 | 10.8 | 0.5 | 13.1 M |
| 50 | 12,150 | 27.0 | 1.1 | 32.8 M |
| 100 | 24,300 | 54.0 | 2.2 | 65.6 M |
| 243 | 59,049 | 131.2 | 5.5 | 159.4 M |
| 500 | 121,500 | 270.0 | 11.2 | 328.1 M |

K=500 is 11 days of continuous serial inference for the sweep alone. It is listed to show why the
frozen panel exists, not as an option.

---

## 4. Time, and what a sleeping Space does to it

A 32-hour study on a Space that sleeps after 48 h idle is feasible — the Space is not idle while
sweeping — but it **will** be restarted at some point over a multi-day run.

That is designed for, not guarded against:

- Every unit checkpoints; a restart costs **one cell**, not the sweep (`docs/04` §3.2).
- Sessions found `running` at boot are marked `paused`, never auto-restarted. The researcher
  resumes.
- Cached answers mean a resume re-pays for nothing.

**Plan a sweep as several sessions, not one heroic run.** The odometer, `start_code` and
`iterations` exist precisely so a 243-cell sweep can be run in tranches, and `budget.py` estimates
each one.

**Do not add `delay_seconds` without evidence.** On a serial pipeline it multiplies directly: one
extra second per call at K=20 adds 81 minutes to a sweep. The prototype's 10 s default would add
13.5 hours. Set it to 0 and raise it only if 429s appear.

---

## 5. Storage

| Table | N=500, K=20 | N=500, K=500 |
|---|---:|---:|
| `twin_answers` | ~5 MB | ~119 MB |
| `run_events` (8 KB cap) | ~10 MB | ~237 MB |
| `survey_answers` (whys dominate) | ~18 MB | ~18 MB |
| `twins` (personas) | ~2 MB | ~2 MB |
| Reference + everything else | ~2 MB | ~2 MB |
| **Total** | **~37 MB** | **~378 MB** |

Comfortable at panel scale. At K=500 it reaches ~76% of the tier — survivable **only** because of
two disciplines, both enforced in DDL:

1. **`run_events.payload` is capped at 8 KB** (`run_events_payload_small`) and carries references
   and telemetry, never bodies.
2. **The round prompt is never stored.** It is rebuilt from `persona_hash`, `seed`, `lever_order`,
   `style_version`, `wording` and `prompt_hash` (I11, `docs/09` §6).

Storing prompt bodies would add roughly 6 KB per twin call — ~730 MB at K=500, exhausting the tier
before the sweep finished. This is why the cap is a constraint and not a style note.

**Answers are vectors, not rows.** 243 cells × 20 twins × 37 items would be ~180,000 rows; as
vectors it is 4,860, and every read is one fetch.

---

## 6. The degradation ladder

When the budget does not fit, cut in this order. **Every rung above the line preserves the design;
below it, something is traded.**

> ### The current plan — decided 2026-09-28
>
> **Rungs 1–4 are adopted. Rung 5 is the operating mode. Rungs 6–10 are not taken.**
>
> - **Quality-test the full population.** All consented twins go through the H3 gate at
>   `quality_runs_per_twin = 3` — 9,000 calls and ~20 h at N=500. Rung 7 is **available and
>   documented, but not chosen**: the calibration claim stays *"k of N kept"* over the whole sample.
> - **No full 243-cell sweep is scheduled.** The design, the odometer, the grid and the panel are
>   built and tested; the controls (`00000`, `SHAM`) and the ten single-lever cells are runnable on
>   demand. The response surface is filled later, in tranches, when the credit budget is known.
> - Nothing about the design changes. Rung 5 is above the line precisely because deferring a sweep
>   costs coverage, not validity — the cells that do run are the same cells they would have been.

| # | Lever | Saves | Cost to the study |
|---:|---|---|---|
| 1 | `delay_seconds` → 0 | up to 13.5 h | none — it was never justified |
| 2 | One wording, `runs_per_wording = 1` | halves a sweep if 2 were set | loses a per-twin stability estimate; test 5 still covers wording |
| 3 | Sweep in tranches across sessions | nothing in total | none — same work, scheduled |
| 4 | Run the three zero-call validity tests first (1, 3) | — | none — they are free and the most diagnostic |
| 5 | Defer the full sweep; run controls + the 10 single-lever cells + selected pairs | ~90% of sweep | main effects and named interactions only; the response surface is partial |
| ─ | ───────────── design preserved above this line ───────────── | | |
| 6 | `quality_runs_per_twin` 3 → 2 | ~6.7 h at N=500 | more sampling noise in the keep/drop decision |
| 7 | **Quality-test a stratified pool, not the population** | up to 15 h at N=500 | the pass rate is reported on the pool, not the sample; untested twins cannot enter a panel |
| 8 | `quality_runs_per_twin` → 1 | ~13.3 h | one bad sample can drop a good twin — the reason the default is 3 |
| 9 | Reduce K below 20 | linear | less power per cell; the interaction estimates weaken first |
| 10 | Cheaper model (`gpt-oss:20b`) | large | **re-run validity test 7 before trusting anything** |

**Rung 7 is the biggest single lever, and it was considered and declined.** Quality-testing a
stratified pool of ~100 rather than all 500 would cut the study's dominant cost by three-quarters,
but it changes the calibration claim from *"k of N kept"* over the whole sample to *"84 of 100
tested kept, from which 20 were drawn"*. Both are honest; only one can be chosen **before**
collection without becoming a researcher degree of freedom. **Decided 2026-09-28: test the full
population.** Keep this rung documented — if the credit budget forces it later, the change must be
recorded in `docs/DECISIONS.md` with the date and the reason, and the paper must report the pool.

**Never on the ladder:** removing a control cell, imputing a missing interaction leg, pooling across
panels, skipping a Checker gate, or lowering the quality thresholds. Those are the design.

---

## 7. The budget calculator

`orchestrator/budget.py`. Shown on the confirm step of every long action (`docs/04` §5.4).

```python
class Budget(BaseModel):
    calls: int
    tokens_in: int
    tokens_out: int
    est_seconds: int
    est_credits: float | None      # None until the researcher supplies the rate
    cache_hits: int                # calls this action will NOT make
    warnings: list[str]
```

Two properties matter more than the arithmetic:

- **It counts cache hits.** "1,240 of 4,860 already answered" turns a re-run from frightening into
  routine, and makes the value of the cache visible.
- **It warns before it blocks.** Warnings fire for: a sweep over 24 h, an estimate exceeding the
  remaining credit balance, a panel containing a since-dropped twin, and a config that changed since
  the session's last run.

The estimate is stored on `sessions.budget` so predicted and actual can be compared afterwards —
which is how the 8 s and 2,300/400 token assumptions get calibrated.

---

## 8. Monitoring during a run

| Signal | Source | Meaning |
|---|---|---|
| 429 rate over the last 50 calls | orchestrator | > 20% emits a `control` event: credits are constrained **now**, not after |
| Mean latency, rolling | `twin_answers.latency_ms` | Recalibrates the time estimate live |
| Repair rate | `twin_answers.retries` | Rising = prompt or model degradation |
| Failed twins per cell | `runs` | Rising = a systematic problem, not bad luck |
| DB size | Supabase | Approaching 500 MB well before it arrives |

**The repair rate is the early-warning signal.** Because Ollama Cloud does not enforce schemas
(`ARCHITECTURE.md` §3.2), a model or prompt getting worse shows up first as more repairs and only
later as failed twins. It is a first-class metric, stored per answer, not a log line.

---

## 9. Before the first real sweep

A short checklist, because every number above is a model:

1. **Read the actual credit allowance** off the Ollama account and enter it. `est_credits` is `None`
   until this exists.
2. **Measure per-call latency and tokens** on 20 real calls; replace the 8 s / 2,300 / 400
   assumptions.
3. **Test whether `seed` is honoured** — one twin, one cell, same seed, ten times (`docs/09` §5).
4. **Run validity test 8** and set the twin temperature from it (`docs/08` §4).
5. **Smoke-test a long background task on ZeroGPU** — whether it survives is undocumented
   (`ARCHITECTURE.md` §8.1).
6. **Run validity tests 1 and 3.** They cost nothing and are the most diagnostic of the eight.
7. ~~Decide rung 7~~ — **decided 2026-09-28: quality-test the full population** (§6).

Steps 1–3 and 5 are measurements this document is guessing at. Do them before committing days of
serial inference to a plan built on estimates.
