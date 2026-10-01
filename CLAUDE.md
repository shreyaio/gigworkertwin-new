# Rules for the coding agent

Read `ARCHITECTURE.md` first, then `docs/01`–`docs/11`. Build in the order of `docs/11_BUILD_PLAN.md`.

## This is a research instrument, not an app

Numbers produced here go into a paper. A bug that makes the UI ugly costs an afternoon. A bug that
lets threshold 2.2 language into an `01000` render silently invalidates the whole study and may not
be caught for months. **When in doubt, fail loudly and stop.**

## Hard rules

1. **Never relax an invariant to make a test pass.** I1–I17 in `ARCHITECTURE.md` §2 are research
   commitments. If one blocks you, stop and say so — do not work around it.
2. **Never give the design agent or the twin agent a tool.** `tools: []` is enforced in
   `build_agent`. Not a style preference.
3. **Never let a model produce a metric.** Metrics, shifts, the index, interactions and every
   statistic are computed in Python. The LLM writes prose *about* numbers it is given, and that
   prose is numerically grounded against its input bundle before it is stored.
4. **Never trust a provider schema.** Ollama Cloud accepts a JSON schema and silently does not
   enforce it. Validate every model output in Python against the item register, every time.
   `NativeOutput` is forbidden. See `ARCHITECTURE.md` §3.2 and `docs/02` §5.
5. **Never impute a missing cell.** If an interaction needs three runs and has two, report which
   code to run. No estimates, no interpolation, no "approximately".
6. **Never UPDATE evidence.** `runs`, `run_events`, `twin_answers`, `twin_quality_runs` and
   `validity_results` are append-only. "Latest" is a boolean pointer flipped in the same
   transaction.
7. **Never silently skip.** A missing persona template, an unmapped Form question, an unknown tool
   name — all raise. Losslessness is the point.
8. **Never renumber an identifier.** `chunk_id`, `criterion_id`, `item_id`, `gap_id` are opaque
   stable keys cited by the codebook and the corpus. `L4-4.1-015` sits at threshold 4.2 and that is
   correct.
9. **Never add a third control cell.** There are two: `00000` and `SHAM`. Adding arms adds
   researcher degrees of freedom, which is the thing this design is built to avoid. (The four
   *human* arms in `docs/01` §5 are a different thing — a between-subjects survey design, not twin
   control cells.)
10. **Never change the analysis panel mid-session.** The twins that answer a sweep are drawn once
    and frozen. A cell answered by a different set of twins is a different experiment.
11. **Never record a result with no twins.** `twins_n = 0` is `failed`, never `completed` with an
    index of 0.000. A validity test on zero twins is `INCONCLUSIVE`, never `PASS`.
12. **Never put an LLM call in a Gradio handler's synchronous path.**
13. **Never define a Pydantic model outside `src/twinlab/models/`.**
14. **Never write anything durable to the filesystem.** Space disk is ephemeral. Evidence goes to
    Postgres or Supabase Storage before it is acknowledged.

## Never coerce a bad answer into a good one

This deserves its own heading because it is the easiest way to destroy the study without noticing.

**Allowed** (syntax): stripping markdown fences, `"6"` → `6`, `6.0` → `6` when exactly integral,
trimming whitespace, dropping a duplicated key whose values agree.

**Forbidden** (meaning): padding a missing item with the baseline, clamping `6` on a 5-point item to
`5`, rounding `5.5`, inferring an item from a neighbour, picking the first of two disagreeing
duplicates.

Everything in the second list converts a detectable failure into an undetectable fabrication. A twin
that cannot produce 37 valid integers after one targeted repair **fails for that cell**. That is the
correct outcome.

## Boundaries

| Layer | May import | May not |
|---|---|---|
| `ui/` | `services/`, `models/` | `db/`, `agents/`, raw SQL |
| `api/` | `services/`, `models/` | `db/`, `agents/` |
| `services/` | everything below | `gradio`, `fastapi` |
| `agents/` | `models/` | `db/`, `ui/` |
| `db/` | `models/` | `agents/`, `ui/` |

`supabase` is imported in exactly one file: `db/client.py`. SQL lives only in `db/`. An
import-linter test enforces this table in CI.

**`api/` must stay optional.** No feature may depend on an HTTP route existing — the free
Gradio-SDK deployment may not expose them.

## Deployment portability — binding, not advice

The target is a free ZeroGPU Gradio Space that must remain a one-commit upgrade to PRO + Docker.

1. The UI is a plain `gr.Blocks` from `ui.app.build_ui()`, with two thin entrypoints: `app.py`
   (`demo.launch()`) and `app_docker.py` (`gr.mount_gradio_app`). Neither holds logic.
2. Survey intake lives in the Supabase Edge Function, never in the Space.
3. Every capability is a service-layer function; `api/` is a wrapper.
4. Never import `spaces`; never decorate anything with `@spaces.GPU`. Python 3.13.

## Style

- Python 3.13, full type hints, `ruff` + `black`.
- `async` all the way down from the service layer.
- Pydantic v2 everywhere. No bare dicts across a layer boundary.
- Comment *why*, not *what*. Match the density of the surrounding file.
- Docstrings on anything implementing an invariant, naming the invariant.

## When the spec is silent

1. Check `ARCHITECTURE.md` §10 — it may be a known open question with a stated default.
2. Check `docs/DECISIONS.md` — it may already be decided. **Read it before questioning an existing
   choice.**
3. If it affects research validity, **stop and ask.** Do not pick.
4. If it is purely mechanical, pick the simplest thing, and add a line to `docs/DECISIONS.md`
   saying what you picked and why.

## When Gradio cannot do it

The researcher has accepted Gradio's limits knowingly. Degrade the *styling*, never the *content*
or the *ordering*. If a panel cannot be resizable, ship it scrollable. If a tooltip cannot be
attached, ship the value in a column. **Never drop a specified element**, and note the degradation
in `docs/DECISIONS.md`.

## Testing

- Unit tests for every deterministic function: lookup, odometer, persona, metrics, checker gates,
  panel draw, the output contract.
- The invariant suite (I1–I17) runs in CI, each test naming its invariant in its docstring.
- Agent tests use a stub model returning fixtures — **no live LLM and no live DB in CI, ever.**
- Test the *contract*, not the prose: assert the design agent was called 10 times for 243 codes;
  do not assert the wording it produced.
- The golden PLS-SEM dataset test must pass to |Δ| < 0.001 before any statistic is reportable.

## Cost

A full sweep at the default panel is ~4,860 twin calls, **serial** — the free provider tier allows
one concurrent request. Before adding any LLM call, ask whether it multiplies by 243, by the panel
size, or by both.

The quality gate is the dominant cost of the study — 18 calls per twin, 9,000 calls at N=500 —
not the sweep. Cache keys are specified in `docs/04` §6; use them, and do not invent a fourth cache.
The caches are not only an optimisation: they are what makes the study reproducible (`docs/09` §2).

## Before writing code in a new area

- Reference data in `data/reference/` is **frozen**. Never regenerate or hand-edit the eight
  original files. `build_reference.py --check` must exit 0.
- The item register is frozen. An item removed at analysis time is an exclusion list, not a
  re-coding.
- If you are about to store a prompt body, a persona passage or a full answer vector in a
  `run_events` payload — don't. Store the reference; the prompt is rebuilt from stored fields.
