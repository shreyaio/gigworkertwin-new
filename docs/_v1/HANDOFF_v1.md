# Twin Lab — handoff prompt for a fresh session

Paste everything below the line into a new session, working in this repo.

---

You are continuing work on **Twin Lab**, a research platform for a study on algorithmic management
of gig workers in India (targeted at ISR/JMIS). The full specification already exists in this repo.
Numbers this platform produces go into a peer-reviewed paper: **when in doubt, fail loudly and
stop rather than guess.**

## Step 1 — Read before writing any code

1. `CLAUDE.md` — the rules you work under. Non-negotiable.
2. `ARCHITECTURE.md` — system map, the eleven invariants (**§2 matters most**), stack, repo layout,
   version code semantics (§5), deployment (§7), open questions (§9).
3. `docs/01_DATA_MODEL.md` — reference data, the 73-item register, full Postgres DDL.
4. `docs/02_AGENTS_AND_PIPELINE.md` — the five agents, the variant pipeline, the analyst maths.
5. `docs/03_BACKEND.md` — FastAPI surface (§2 is the route list), orchestrator, resume, caching.
6. `docs/04_FRONTEND.md` — Gradio tabs, components, exact panel orderings, CSS.
7. `docs/05_BUILD_PLAN.md` — the ten milestones and their acceptance tests.
8. `docs/DECISIONS.md` — every judgement call already made and why. **Read this before questioning
   an existing choice.**

Also skim `worked_out_eg.txt` (one version code traced end to end by hand).

## Step 2 — State of the build

**M0–M10 are complete. 212 tests pass** (`python -m pytest tests/ -q`). Nothing is outstanding in
the build plan. Do not rebuild these.

| Milestone | State | Key files |
|---|---|---|
| M0 Scaffold | done | `app.py`, `Dockerfile`, `requirements.txt`, `README.md`, `.env.example`, `config/settings.py`, `config/{agents.default,twin.default,style_contract}.yaml` |
| M1 Reference + schema | done | `db/migrations/001_init.sql`, `db/client.py`, `ingest/{seed_db,reference_store}.py`, `models/reference.py` |
| M2 Persona | done | `persona/{templates,builder}.py`, `models/twin.py` |
| M3 Lookup + odometer | done | `variant/lookup.py`, `orchestrator/odometer.py`, `models/variant.py` |
| M4 Design agent + checker | done | `variant/{render,checker}.py`, `agents/{registry,design,tools}.py`, `agents/prompts/`, `db/repo_variants.py` |
| M5 Twin agent | done | `agents/twin.py`, `agents/prompts/twin_v1.md`, `models/run.py` |
| M6 Orchestrator | done | `orchestrator/{loop,events}.py`, `db/repo_{sessions,runs,twins}.py` |
| M7 Analyst | done | `analysis/{metrics,interactions,report}.py`, `models/analysis.py` |
| M8 UI | done | `ui/app.py`, `ui/theme.py`, `ui/components/` (12), `ui/tabs/` (5), `services/` (4) |
| M9 Intake + hardening | done | `api.py`, `models/{api,intake}.py`, `ingest/{survey_intake,replay_temp}.py`, `config/form_map.yaml`, `telemetry.py` |
| M10 Invariant suite | done | `tests/test_invariants.py`, `.github/workflows/ci.yml` |

Tests: `test_m0_scaffold`, `test_m1_reference`, `test_persona`, `test_lookup`, `test_checker`,
`test_twin`, `test_orchestrator`, `test_metrics`, `test_ui`, `test_api`, `test_intake`,
`test_invariants`; fixtures in `tests/fixtures/{twins,stub_agents}.py` and `tests/conftest.py`.

**Never call a live LLM or a live DB in a test.** `conftest.py` installs an `InMemoryBackend` per
test; `fixtures/stub_agents.py` provides a `StubModelClient` routed by `agent_id`.

`data/reference/*.json` is **frozen and verified** — never regenerate or hand-edit.
`python src/twinlab/ingest/build_reference.py --check` must exit 0 (if it fails with
`PackageNotFoundError`, the `.docx` is open in Word — close it).

## Step 3 — What the researcher still owes the build

Nothing in the build plan is blocked on code. These are blocked on the researcher.

1. **Live credentials and a real database.** `.env` (Supabase URL + service key, `OLLAMA_API_KEY`,
   `INTAKE_HMAC_SECRET`) and running `001_init.sql` in Supabase. **Everything so far is verified
   against the in-memory backend and stub models only.** `docker build` has never been run, and
   no live model call has ever been made.
2. **Confirm the intake contract before the Google Form is built.** The Apps Script must POST
   `{response_id, submitted_at, answers: [{section, title, value}, …]}` with an
   `X-Signature` HMAC-SHA256 of the raw body, and every question's `"<section>|<title>"` must
   appear in `config/form_map.yaml`. See `docs/DECISIONS.md` → M9 for why the section is part of
   the key. An unmapped question is a 422, not a dropped answer.
3. **The mock's per-metric shift table.** `docs/02` §8.2 publishes the full six-metric shift vector
   for `21122` only, so seven of the ten published index values cannot be verified from the mock's
   own inputs. If the table arrives, add direct assertions to `tests/test_metrics.py`.
4. **ARCHITECTURE §9 open questions** 1–4 (sweep start, Part 15, the mixed-scale index, twin N)
   are running on their stated defaults.
5. **Two Settings buttons are deliberately inert** — "Import twins from the survey" and "Clear runs
   and load demo twins". Import belongs to the intake route; clearing `runs` would delete
   append-only evidence (I9), which is a database operation and not a button. Both say so in the
   UI. Tell the next session if you want either wired.

## Step 4 — Sensible next work, none of it specified

- **A live smoke run.** With credentials in place: seed, create a session, run `00000` and `SHAM`,
  read the Logs tab. This is the first thing that would exercise a real model call, a real
  Supabase transaction and the two Postgres pointer-flip functions (`runs_complete`,
  `quality_run_record`), none of which has run outside the in-memory backend.
- **`docker build`,** then the Hugging Face Space (Docker SDK, per ARCHITECTURE §7).
- **Gradio pin.** `requirements.txt` pins 5.x per ARCHITECTURE §3 while the local interpreter has
  6.x. The UI is written to work on both, but the deployed image has never been run.
- **Plotly heatmap** for the Results grid, the optional enhancement in docs/04 §7.1. The
  `gr.Dataframe` grid is shipped and clickable; only the hover tooltip is degraded.

## Step 5 — Stop and ask when

- An invariant (I1–I11) blocks you. Never work around one; `tests/test_invariants.py` is what
  catches it.
- A research-validity decision is not covered by the docs. Mechanical choices: pick the simplest
  option, proceed, and log one line in `docs/DECISIONS.md`.
- You want to add a control cell, an experimental arm, a metric, or a fourth cache. Don't.
- A specified UI element cannot be built in Gradio. Degrade the **styling**, never the **content**
  or the **ordering**, and record the degradation in `docs/DECISIONS.md`.

## Decisions you must not silently reverse

- `twins.background jsonb` holds Part 3 extras, Part 4, **and Part 14 own-words**. Part 14 has no
  `item_id` and the 73-item register is frozen; without this the persona silently loses the
  driver's own words.
- The SHAM cell's unfilled levers announce that lever's existing driver-facing policy, one chunk by
  `chunk_id`; its containment gate is scoped to that policy. **Researcher-approved.** SHAM occupies
  `dial = 3` in `lever_paragraphs`.
- Reading-grade band `[4.0, 16.0]` Flesch–Kincaid in `style_contract.yaml`.
- A cached lever paragraph is never re-rendered per cell (that would break I4).
- Gradio handlers are `async def`, never `asyncio.run` in a sync handler: the latter closes its
  loop and takes any enqueued session task with it.
- The interactions panel names levers with `told_bullets` headings, the same source as the dial
  board, not a second friendlier naming scheme.

Full list with reasons: `docs/DECISIONS.md`.

## Start now

Run `python -m pytest tests/ -q` to confirm 212 passing and
`python src/twinlab/ingest/build_reference.py --check` to confirm exit 0. Then take the work the
researcher gives you — the build plan itself is finished.
