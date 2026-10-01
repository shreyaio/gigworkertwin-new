# Twin Lab — build handoff

**Paste this whole file into a fresh coding session working in this repository.**

*Last updated 2026-09-29, after M14 — the last milestone. Supersedes the after-M13 edition.*

---

You are building **Twin Lab**: a researcher workbench for a study on algorithmic management of gig
workers in India, targeted at ISR/JMIS. A complete, normative specification already exists in this
repo. Your job is to build the system from it — not to redesign it.

**The numbers this platform produces go into a peer-reviewed paper.** A bug that makes the UI ugly
costs an afternoon. A bug that lets threshold 2.2 language into an `01000` render, or records a
zero-twin run as a result, or binds a construct to the wrong items, silently invalidates the study
and may not be caught for months. **When in doubt, fail loudly and stop.**

---

# Step 0 — Where the build actually is

**All fifteen milestones are complete. 737 tests pass.** There is no next milestone; what remains
is listed in §0.7 and is the researcher's, not a coding session's.

Do not re-wipe `src/`, do not re-scaffold, and do not redo a finished milestone. Read §0.5 for
exactly what each one landed.

## 0.0 Use the venv. Read this before your first command.

**`./venv/Scripts/python.exe` is the project interpreter. Bare `python` is the wrong one.**

They differ in ways that will waste your time and mislead you:

| | `./venv/Scripts/python.exe` | bare `python` on this machine |
|---|---|---|
| Python | 3.13.0 | 3.13 (several on PATH, incl. 3.11 and anaconda) |
| Gradio | **5.50** — matches the `>=5.29,<6.0` pin | **6.22** — outside the pin |
| `pydantic_ai` | 2.51.0, installed | **absent** — no live agent call possible |
| `openpls` | 1.11.0, installed | **absent** — no statistic is computable |
| `pytest-asyncio` | installed | absent (the suite drives its own loop, so it still passes) |

Every command in this file assumes the venv. On Git Bash:

```bash
cd "C:/Users/Shreya Shah/OneDrive/Documents/Research_ISR_JMIS/codefiles/gigworkertwin_new" && ./venv/Scripts/python.exe -m pytest tests/ -q
```

**Several scripts need `PYTHONPATH="src;."`, not just `src`** — `config.settings` is imported from
the repo root. `seed_db.py`, `gen_golden.py` and `app.py` all fail with `ModuleNotFoundError: No
module named 'config'` without it.

`node` (v22) is on PATH and is needed for M9's intake contract test. `deno` is **not** installed —
see §0.8's last row for what that leaves unverified.

## 0.1 Git — the researcher owns it, you do not touch it

**This repository is still not in git, and that is deliberate.** The researcher has reserved every
git operation for themselves.

**Never run `git init`, `git add`, `git commit`, `git push`, or any other git command.** If a
commit would help, say so and let them do it.

## 0.2 Read, in this order

Do not write code until you have read all of these. They are consistent with each other; where two
appear to disagree, the earlier one in this list wins.

| # | File | Why it comes here |
|---|---|---|
| 1 | `CLAUDE.md` | The rules you work under. Non-negotiable. Read it twice. |
| 2 | `ARCHITECTURE.md` | System map. **§2 (the seventeen invariants) matters most.** Then §3.2, §7, §8. |
| 3 | `docs/00_RESEARCH_OVERVIEW.md` | Non-normative, but read it — you will make better decisions knowing *why*. |
| 4 | `docs/01_DATA_MODEL.md` | Reference data, the 73-item register, the crosswalk, the full DDL. |
| 5 | `docs/02_AGENTS_AND_PROMPTS.md` | The five agents, prompt architecture, **and §5, the output contract**. |
| 6 | `docs/03_RESEARCH_PIPELINE.md` | How a version code becomes 37 integers. |
| 7 | `docs/04_BACKEND.md` | Service layer, orchestrator, caching, resume, intake. |
| 8 | `docs/05_DESIGN_SYSTEM.md` | Tokens, motion, components, states, accessibility. |
| 9 | `docs/06_SCREENS.md` | All eight sections. **Content and ordering are mandatory.** |
| 10 | `docs/07_STATISTICS.md` | Every formula. Nothing is computed anywhere else. |
| 11 | `docs/08_VALIDATION_AND_VALIDITY.md` | Quality gate, two holdouts, eight validity tests. §4 landed in M13. |
| 12 | `docs/09_REPRODUCIBILITY.md` | What is guaranteed and what is not. |
| 13 | `docs/10_SCALE_AND_COST.md` | What a sweep costs. Read before adding any LLM call. |
| 14 | `docs/11_BUILD_PLAN.md` | **Your actual work order.** Fifteen milestones with acceptance tests. |
| 15 | `docs/DECISIONS.md` | Every judgement call already made. **Read before questioning a choice.** Its M12 section is the most recent and records the one research decision that could not be picked. |

Also skim `additional_data/worked_out_eg.txt` — one version code traced end to end by hand.

**`docs/_v1/` is archived and wrong.** Do not read it for guidance and never build from it. Its
README lists the specific claims it now gets wrong. It exists for provenance only.

**`docs/DECISIONS.md` has duplicate milestone headings.** The v1.0 build plan numbered milestones
differently, so there is a `## M2 — Item register and persona builder` (v1.0) as well as
`## M2 — The output contract and the agent registry` (current), and likewise two `## M4`s. Each
v1.0 heading now carries a note saying so. The current sections are the ones dated 2026-09-28 or
later with milestone names matching `docs/11_BUILD_PLAN.md`.

## 0.3 The six things that will get you in trouble

Commit these to memory before you start. Each has already gone wrong at least once.

1. **The provider does not enforce schemas.** Ollama Cloud accepts `response_format` with
   `json_schema` *without error* and silently does not apply grammar-constrained decoding. It looks
   like it works. Validate every model output in Python, every time (I13). `NativeOutput` is
   forbidden and `build_agent` raises on it — **already built, see `agents/contract.py`. Use it;
   do not write a second validation path.**
2. **Never coerce a bad answer into a good one.** Padding a missing item from the baseline, clamping
   a `6` on a 5-point item, rounding `5.5` — each converts a detectable failure into an undetectable
   fabrication. A twin that cannot produce 37 valid integers after one targeted repair **fails for
   that cell**. That is the correct outcome.
3. **One concurrent request.** The free provider tier permits one. `max_concurrency` defaults to 1
   and 1 is the tested default, not an edge case.
4. **A run with no twins is a failure, not a result.** The prototype stored rows with
   `twins = 0, index = 0.000` as findings, and emitted `PASS` verdicts on validity tests that ran on
   nobody. DDL constraints and the in-memory backend now make both impossible — do not work around
   them. **M13 was where this mattered most**: `validity_zero_n` is the constraint, I15 is the
   rule, and `ValidityOutcome` now refuses to be constructed in violation of it.
5. **Nothing durable on the filesystem** (I16). Evidence goes to Postgres or Supabase Storage before
   it is acknowledged. A test scans every module for `write_text`, `write_bytes`, `mkdir` and
   `open(…, "w")`; only `build_reference.py` is exempt.
6. **A gate that cannot fail is not a gate.** Three were found in M12, all silently always-green
   (§0.5). Where you write a prohibition, also write the test that proves it rejects a violation —
   and *run* that proof by injecting the violation once.

## 0.4 What was done to the repo on 2026-09-28 (the rebuild wipe)

Recorded so you do not repeat it or undo it.

| Category | State |
|---|---|
| **FROZEN** | Untouched. The eight `data/reference/*.json` files verified byte-identical before and after the wipe; hashes in `_preserve/frozen_reference.sha256` **and hard-coded in `tests/test_m1_reference.py`** so the guard outlives that directory. `additional_data/**` untouched. |
| **PRESERVED** | `build_reference.py` and `persona/templates.py` were copied to `_preserve/` and have since been **restored** and extended. |
| **REMOVED** | The whole v1.0 implementation, archived to `_v1_removed/`. |

**Three scaffolding directories exist and are not part of the application:**

```
_v1_removed/    the old implementation, kept only until the repo is in git
_preserve/      the two rescued files plus frozen_reference.sha256
_probe/         the ZeroGPU diagnostic; dormant, see §0.6
```

`_v1_removed/` and `_preserve/` should be deleted once the researcher has committed. Do not delete
them yourself, and **do not import from them** — though restoring a *specified artefact* from there
is fine and has been done once: `001_init.sql` is named by `docs/01` §6 as the base migration.

## 0.5 What is built — M0 through M12

**737 tests pass. `build_reference.py --check` exits 0 with ten `OK` lines. 6/6 import-linter
contracts kept. `ruff check src tests tools` clean. The golden PLS-SEM gate passes.**

| Milestone | Tests | Status |
|---|---:|---|
| M0 Scaffold and portability | 15 | DONE |
| M1 Reference data, schema | 32 + 18 | DONE except **migrations not applied** (§0.7) |
| M2 Output contract, agent registry | 46 | DONE |
| M3 Lookup, odometer, panel | 44 | DONE |
| M4 Persona | 33 | DONE |
| M5 Design agent and Checker | 46 | DONE |
| M6 Twin agent, quality gate | 29 | DONE |
| M7 Orchestrator, budget, events, resume | 25 | DONE; backoff ladder and the Manager's tools deferred |
| M8 Analysis | 36 | DONE; `analyse` not yet wired into the runner |
| M9 Intake and the generator | 27 | DONE; `index.ts`'s HTTP/HMAC layer never executed (no Deno) |
| M10 UI shell and Twin Lab | 53 | DONE; three workflow buttons confirm a real budget but enqueue a stub |
| M11 Twin Studio and Agent Studio | 27 | DONE; *Ask the twin* records a run but has no live twin call yet |
| M12 Statistics, golden dataset | 116 | DONE; the golden gate passes and every statistic is reportable |
| M13 Validity tests | 39 | DONE; the six tests that need fresh twin calls take an injected `ask` and record `INCONCLUSIVE` until one is wired |
| **M14 Research model, invariants, deploy** | **24** | **DONE except deployment, which the researcher struck on 2026-09-28 (§0.6)** |
| Invariant suite | 42 | **I1–I17 all tested. `DEFERRED` is empty.** |

M12's 116 are `test_m12_dataset.py` (41), `test_m12_ui.py` (21), `test_m12_integration.py` (19),
`test_m12_service.py` (18) and `test_stats_golden.py` (17). M13's 39 are all in
`test_m13_validity.py` and M14's 24 in `test_m14_research.py`. The per-file counts sum to 652.

### What exists now

```
app.py  app_docker.py            two thin entrypoints over one gr.Blocks; neither holds logic
config/settings.py               pydantic-settings; max_concurrency=1, panel_size=20
config/agents.default.yaml       M2 — the five agents as seed rows, validated on load
config/style_contract.yaml       the design agent's contract (M5 reads it)
config/form_map.yaml             112 Form question -> item_id
config/twin.default.yaml         M6 — must carry max_concurrency (§1.3)
config/analysis.default.yaml     M8 — the index weights; default unweighted

src/twinlab/models/              ALL Pydantic models. No model is declared anywhere else.
  reference.py    M1  Criterion Gap Chunk Scale Item Construct Arm LegacyItem
                      + MET_CRITERIA, CONSTRUCTS, BLOCK_TO_CONSTRUCT, construct_code_for()
  agent.py        M2  AgentConfig ModelRef ContextSource RetryPolicy AgentResult ConfigError
  variant.py      M2  DeltaSpec LeverBrief LeverParagraph CoverageProbe CoverageVerdict
                      CheckerReport + DIAL_ZERO_TEXT, SHAM_DIAL
  twin.py         M2/M3/M4  TwinAnswerSet QualityAnswerSet RoundPrompt PanelCandidate
                      PanelMember Twin Background SurveyResponse PersonaPassage
  analysis.py     M2  AnalysisBundle (numeric_tokens()) AnalysisResult
  run.py          M2  ManagerState ManagerDecision Budget Session Run
  view.py         M10 EVERY read-only shape ui/ renders for the counterfactual layer
  stats.py        M12 EVERY measurement-layer shape: ModelSpec ConstructSpec PathEdge
                      CaseMatrix, the nine stages' row models, AnalysisProvenance,
                      AnalysisRunView, StatsTableSpec + STAGES
src/twinlab/ingest/
  build_reference.py    M1  emits TEN files; --check is the frozen-data guard
  reference_store.py    M1  all ten files in memory + reference_hash(); cross-source gates
  seed_db.py            M1  idempotent, 18 post-seed assertions, writes the reference digest
src/twinlab/db/
  client.py             M1  the ONLY supabase import; SupabaseBackend + InMemoryBackend
                            (the in-memory one MIRRORS the DDL check constraints)
  migrations/001_init.sql       restored v1.0 base schema
  migrations/002_v2_model.sql   M1 — the 2.0 schema, strictly additive
  repositories.py       M7  Session/Panel/Run/Answer/Variant repos
src/twinlab/agents/
  contract.py           M2  THE validation ladder + grounded() + run_answer_ladder()
  registry.py           M2  SCHEMA_REGISTRY, build_agent, resolve_prompt, StubModelClient
  tools.py              M2  the allow-list; the Manager's three names still raise
  design.py  checker.py M5  the four-block brief; the coverage probe
  twin.py               M6  round assembly, rebuild_round_prompt() (I11)
  prompts/*_v1.md       M2  five prompts, six-section skeleton enforced
src/twinlab/variant/    M3/M5  lookup.py render.py checker.py
src/twinlab/orchestrator/  M1/M3/M7  odometer.py panel.py loop.py events.py budget.py
src/twinlab/validity/quality.py M6  score_holdout(), h3_verdict(), h2_arm_for(), pearson_r()
src/twinlab/analysis/   M8  metrics.py interactions.py report.py
src/twinlab/persona/    M4  templates.py (preserved) builder.py
src/twinlab/stats/              M12 — the measurement layer. Statistics NEVER reads the sweep.
  spec.py               the model, built from the FROZEN register; the only theory literal
                        in the layer is STRUCTURAL_EDGES. build_model_spec(), topological_order()
  dataset.py            screening, reverse coding, arm dummies, interaction products,
                        casewise deletion (I17), legacy exclusion; build_matrix()/load_matrix()
  plssem.py             the engine wrapper; the nine stages; LongBootstrap (seeded, serial)
  golden.py             the reference dataset (own PRNG) + 345 pinned expected values
  export.py             the TWO-header-row export; construct means pre-computed (I12)
src/twinlab/services/            the ONLY layer ui/ may reach, besides models/
  config.py  surveys.py  dials.py  metrics_view.py  status.py  runs.py  lab.py
  results.py  menu.py  studio.py  agent_config.py
  statistics.py         M12 — staged resumable analysis runs, the bootstrap floor,
                        provenance, the export, and LEGENDS (one per stage, docs/05 §4.4)
src/twinlab/ui/
  theme.py              tokens + the contrast overrides + M12's legend and banner CSS
  app.py                build_ui(); drains each page's load_once() per route context
  components/shell.py       app_header, sub_nav, help_accordion, load_once, load_js, ...
  components/primitives.py  pill/status_dot/empty_state/data_table/kv_table/num/...
  components/domain.py      metric_bars, grid_243, what_twins_are_told, log_tree,
                            results_panel_html, answer_compare, budget_summary,
                            + M12: stats_table, provenance_strip, unvalidated_banner
  pages/main_menu.py    M10 docs/06 §1
  pages/lab.py          M10 docs/06 §3 -- all eight tabs, order asserted at build time
  pages/studio.py       M11 docs/06 §5
  pages/agent_studio.py M11 docs/06 §6
  pages/statistics.py   M12 docs/06 §7 -- all TEN tabs, order asserted
  pages/research_model.py M14 docs/06 §8 -- all TEN sections, order asserted
  pages/{driver_survey,generator}.py   still M0 stubs
tools/
  gen_build_form.py  gen_form_map.py  gen_edge_assets.py  deploy_space.py
  gen_golden.py         M12 — recomputes the 345 pinned values. READ THE DIFF before --write.
```

Every other package directory exists with a docstring-only `__init__.py`.

### What M14 landed, and what the researcher now owes the page

```
config/research_model.yaml          the researcher-supplied content. SHIPS EMPTY on purpose.
src/twinlab/models/research.py      the ten sections' shapes
src/twinlab/services/research.py    assembles the view; research_document() writes the export
src/twinlab/ui/pages/research_model.py   docs/06 §8's ten sections, order asserted at build time
```

**The page splits every field in two, and the split is the design.** What the codebase owns is
*generated* from it — the nine constructs and their indicator counts come from
`stats/spec.construct_items`, the same function `build_model_spec` calls, and the diagram comes
from `STRUCTURAL_EDGES`, the same tuple the estimator uses. The page prints
`ModelSpec.fingerprint()` (`7c7fd73a12a4ec48`) beside the diagram. **That is what stops the
Research model page and Statistics from describing different studies**, which is why `docs/06` §8.4
calls the measurement mapping required.

**What only a researcher can write ships empty and renders *Not supplied yet*.** `docs/06` §8.9
forbids fabricating a reference; the same rule is applied to every prose field. **Four of them are
specified nowhere in this repository and are now waiting for you:**

| `docs/06` | What is missing | Where it goes |
|---|---|---|
| §8.2 | The three research questions' **wording, hypothesis references and contributions**. The ids and titles are §8.2's own and are seeded. | `research_questions:` |
| §8.5 | **Every hypothesis.** None is stated in `docs/00`, in `additional_data/` or anywhere else. Write them against the frozen model `7c7fd73a12a4ec48`, not around it. | `hypotheses:` |
| §8.7 | Each construct's **definition and source citation**. | `constructs:` |
| §8.8 | The **`Paper section`** column. The other three columns are generated. | `validation_map:` |
| §8.9 | The **reference list**. Empty until you write it; nothing invents one. | `references:` |

The method table's nine parts each already carry a generated *In this build* fact — counts, codes
and versions — beside the empty prose column, so the page is informative before a word is written
and your prose can be checked against the instrument rather than drifting from it.

**Deployment is struck, not outstanding.** `docs/11` M14's last two criteria assume a Hugging Face
Space; §0.6 records why that is not happening. The host-independent parts are tested — the boot
`reference_hash` assertion, `resume_interrupted_sessions` never auto-restarting, and the Space
card's `hf_oauth_authorized_org` gate. That a Space boots, that OAuth admits only the named
organisation and that a resume survives a real restart on a real host are **not** tested and are
not claimed.

### What M13 landed, and the one thing it left for the researcher

```
src/twinlab/models/validity.py    ValidityOutcome PairedGap ProbeStimulus AblatedPersona
                                  TemperatureRecommendation QuarantinedArtefact
                                  + assert_not_a_probe / assert_not_ablated (see below)
src/twinlab/validity/tests.py     the eight, PURE. No db, no agents, no callable in sight for
                                  tests 1 and 3. TEST_IDS, TEST_DETAIL, CALLS_PER_TWIN
src/twinlab/services/validity.py  reads stored evidence, decides whether a test CAN run, appends
                                  one validity_results row per completed test
ui/pages/lab.py §3.5              the eight buttons, one shared confirm step, the synthetic warning
```

**The two quarantines are enforced at the write, and the guards live in `models/validity.py`
because `db/` may import `models/` and nothing else.** `assert_not_a_probe` is inside
`VariantRepo.put`; `assert_not_ablated` is inside both functions that insert a `twins` row. Both
were verified by injecting the violation. `ProbeStimulus` additionally has **no `version_code`
field**, and `AblatedPersona` has **no `persona_hash`** — the absence is the enforcement.

**Tests 1 and 3 are proven free on the call counter**, and `services/lab.py::VALIDITY_TESTS`'s
wrong `needs_live_model` flag on Test 1 is fixed. A bookkeeping test now ties every badge to
`CALLS_PER_TWIN`, so the two cannot drift apart again. `tests/test_m10_ui.py`'s
`count(False) == 1` assertion **encoded that defect** and was corrected to `== 2`.

**The six tests that need fresh twin calls take an injected `ask`**, exactly as `SessionRunner`
takes `ask_twin`. **Nothing wires one yet** — no live twin path exists anywhere in the build (the
Studio's *Ask the twin* has the same gap). Until one does, tests 4–8 record `INCONCLUSIVE` with a
message saying so, which is honest rather than invented. Test 2 is different: it reads the stored
`SHAM` control, which every fresh session runs before its sweep, so it works today against a
completed session.

**Test 1 and test 3 need the quality gate to store the twin's H2 answer vector.** `docs/01` §6
gives `twin_quality_runs` a `detail` jsonb and no column for it, so it is filed under
`detail["answers"]` (`services/validity.H2_ANSWERS_KEY`). **The quality gate does not write it
yet**, so both tests currently record `INCONCLUSIVE` on a real database. That is the one wiring
job that unlocks the two most important tests, and it is cheap: they make no model calls.

**Test 8 writes a recommendation, never the setting.** `app_config["twin_temperature_recommendation"]`,
and `TwinConfig.temperature` is untouched at 0.7. The rule — *the lowest temperature whose
between-twin index SD is still above zero* — is the only one `docs/08` §4 test 8's prose yields
without a free parameter, but the specification states no rule at all. **§0.7 item 10 is therefore
still open, and it is now a question with a concrete proposal rather than a blank.**

### Findings worth carrying forward

All are in `docs/DECISIONS.md` with full reasoning. The ones most likely to bite you:

**From M12 — three of these were gates that could not fail:**

- **`executable_source` in `tests/test_m0_scaffold.py` re-joined tokens with newlines**, which
  splits every multi-token construct: `@spaces.GPU` became four separate lines. The scans for
  `@spaces.GPU` and `google sheet` therefore **could never match**, so one of the four *binding*
  portability rules (`ARCHITECTURE.md` §8.2 rule 4) was **silently always green**. Now line-based,
  and verified by injecting `@spaces.GPU` into a `ui/` module and watching the test fail.
- **`tests/conftest.py`'s live-database ban did not hold at every fixture scope.** Its docstring
  promised "no test can reach Supabase even if the environment happens to carry credentials", but
  the guard was a **function-scoped** autouse fixture — so a `module`- or `session`-scoped fixture
  ran *first* and got whatever `get_backend()` built. M12's integration fixture **reached the
  researcher's real Supabase project**. The ban is now enforced at the factory
  (`_no_live_database`, session-scoped): nothing at any scope can construct a `SupabaseBackend`.
  **If you write a module- or session-scoped fixture that touches the DB, install an
  `InMemoryBackend` inside it** — see `tests/test_m12_integration.py::completed` for the pattern,
  including re-installing it after the per-test fixture swaps in a fresh one.
- **The M10 repeating-timer scan read raw source**, so a module that *documents* the prohibition
  tripped it — exactly the failure this file already recorded for `@spaces.GPU`. Ban scans read
  `_executable_source`, never `read_text()`.
- **The structural path model was not in the specification at all** and had to be escalated. See
  §0.7 item 1 — it is now decided and pinned, and you must not change it.
- **`openpls-engine`'s import name is `openpls`.** Neither `openpls_engine` nor `plspm` resolves.
- **`Plspm(bootstrap=True)` cannot honour `docs/07` §9's seed.** It draws resamples with an
  unseeded `np.random.randint` across a multiprocessing pool. Use
  `openpls.long_bootstrap.LongBootstrap`, which takes a `seed`, runs serially and reports progress.
  Its `completed` and `failed` are **attributes, not methods**.
- **`Plspm.reliability()` does not return `rho_A`.** It is on `plsc().rho_a()`.
- **A zero-variance column reaches the outer model as `NaN`, not as an error.** `dataset.py` raises
  at matrix-build time instead. This fires easily in tests — a fixture where every respondent
  shares an arm has no antecedent variance.

**From M10–M11 — both found by RUNNING the app, not by the tests:**

- **A repeating `gr.Timer` silently ate every dial change.** The Dial board painted its initial
  state from a `gr.Timer(0.2)` because `gr.Blocks.load` cannot be called from a page function. The
  timer never stopped, so it kept recomputing and its output landed on top of the change handler's:
  **moving a dial did nothing**, the code stayed `00000`, and there was no error anywhere. Every
  assertion about the handler passed the whole time, because the handler was correct and its result
  was being overwritten downstream. Fixed with `components.load_once` + `drain_pending_loads`.
  **The lesson generalises: green tests do not prove a Gradio screen works. Run it.**
- **Gradio's defaults are near-white on this light theme.** `theme.py` overrides them page-wide
  under `.tl-page`. A new screen inherits the fix; do not re-solve it per component.
- **The DDL corrected a service.** `twin_quality_runs` has an `arm` **column** that
  `quality_h2_arm` makes non-null on every H2 row; validation had been reading `detail["arm_seen"]`.
  Read the constraints in `002_v2_model.sql` before inventing a `detail` key — several of them
  encode where a value lives. **This was directly relevant to M13**, whose results go in
  `validity_results` with its own constraints.
- **`gr.HTML` emits no events.** The 243-grid's cell click is bridged into a textbox via the native
  value setter plus an `input` event. Same trick if you need it again.

**From M5–M9 — these cost real time to find:**

- **A Google Forms checkbox answers as a LIST.** `["I agree"]`, not `"I agree"`. Stringifying it gave
  `"['i agree']"`, so **every consent read as false and no twin would ever have been built**.
  `apps_script/sample_payload.json` caught it. **Do not "tidy" that fixture.**
- **pydantic-ai is pinned with no upper bound** (`>=0.0.30`) and **2.51 is installed**, which renamed
  the usage API. `result.usage` is a property, not a method; the fields are
  `input_tokens`/`output_tokens`. `registry._token_counts` handles both and **raises** on a third
  rename rather than reporting `None`.
- **The only live render (2026-09-29, 10 calls) showed two real problems.** Containment produced
  **false positives on 2 of 10** paragraphs, all from the generic bigram `("driver","app")`. Still
  open — see §0.7 item 3.
- **`Filter` in `db/client.py` is `(op, col, val)` — operator FIRST.** The other order does not
  error, it **matches everything**.
- **Wrapping long lines mechanically breaks code.** Reflow docstring *paragraphs*, never single
  lines, and check `ruff` after.

**From M0–M4:**

- **`python -m importlinter.cli lint` does not lint.** No `__main__` handling — it imports, prints
  nothing, exits 0. Invoke the click command object instead.
- **Cross-process determinism needs a subprocess test.** `delta_hash`, the panel draw and the
  persona hash are asserted in a fresh interpreter with `PYTHONHASHSEED=random`.
- **`agents.default.yaml` must quote any instruction containing `": "`** or YAML parses it as a
  mapping.
- **The in-memory backend enforces the DDL check constraints** and computes the generated columns.
  Without that, the invariants enforced only in Postgres would be exactly the ones CI never tests.

## 0.6 Deployment: decided, and it is not Hugging Face for now

The old M1 gate was run on 2026-09-28. **It failed, and the researcher has decided.** Full evidence
in `docs/DECISIONS.md` → "M1 deployment gate".

**`ARCHITECTURE.md` §8.1's central premise is false.** It assumed ZeroGPU could be used as a free
CPU Space with `spaces` never imported. Measured against the real platform:

| `ARCHITECTURE.md` says | ZeroGPU actually does |
|---|---|
| Python 3.13, fallback 3.12 | **Python 3.10**, silently ignoring the Space card |
| `gradio>=5.29,<6.0` (§3) | force-installs **`gradio[oauth,mcp]==6.28.0`** |
| Never import `spaces` (§8.2 rule 4) | **refuses to boot**: `No @spaces.GPU function detected` |

**DECISION (researcher, 2026-09-28): run locally. Hosting is deferred, not abandoned.**

```bash
PYTHONPATH="src;." ./venv/Scripts/python.exe app.py      # http://127.0.0.1:7860
```

- **The M1 ZeroGPU gate is struck, not deferred.** A long background `asyncio` task obviously
  survives on the researcher's own machine.
- **The four portability rules in §8.2 still bind** and are enforced by tests — and as of M12 the
  `@spaces.GPU` one is actually enforced rather than nominally.
- **"Hosting later" means PRO + Docker**, which costs a commit. It does **not** mean ZeroGPU.
- `_probe/` is kept, dormant, deliberately Python 3.10-compatible. Do not "modernise" it.
- `tools/deploy_space.py` uploads over the HTTP API without touching git. Unused; keep it working.

## 0.6b What changed after the prototype-parity pass (2026-09-30)

**Read `docs/DECISIONS.md` → `D-PARITY` before touching the Generator or the Twin Lab CSS.** The
researcher compared the running system against the Apps Script prototype and named what was
missing. The short version:

* **The Generator is fully bound.** Five cities (Delhi NCR and Jaipur were missing), multi-apping,
  the vehicle loan, economic dependence, shared mood, tenure in months, and the five lever-reaction
  sliders plus the captive-voice checkbox. The sentiment sliders are **absolute 1–7 targets**, not
  offsets; the presets fill them.
* **Two data defects were fixed on the way, and both had been silently wrong in every batch.**
  Reverse-coded items (`SAT2`, `DEP1`, `H2_SAT2`) were drawn forward, so those blocks contradicted
  themselves; and the two holdout blocks repeated the baseline, so `H2_*` did not move with the
  respondent's arm and all six `H3` versions answered alike. `GENERATOR_VERSION` is **`v3`** and a
  `v2` seed does not reproduce under it.
* **There is a Storage client** — `db.client.SupabaseStorage` / `InMemoryStorage`, via
  `get_storage()`, bucket `raw-surveys`. `tools/generate_synthetic.py` no longer imports the SDK,
  so `supabase` is confined to `db/client.py` again. **`Generate surveys` is live.**
* **The Driver survey screen is built** (`docs/06` §2) and still does not host the survey.
* **A real CSS bug is fixed: the 243 grid was invisible.** `.tl-subnav button` set
  `background:transparent !important` on every button in the Twin Lab tab panel, and each grid cell
  is a `<button>`. It is now scoped to `.tl-subnav .tab-container button`.

**The live project's 300-row synthetic batch is `v2`** and carries all of the above defects. It is
a deliberate press of *Generate surveys* to replace, so it has not been done.

## 0.7 Open items the researcher owns — do not pick these yourself

1. **The structural path model — DECIDED 2026-09-29, and now frozen. Do not change it.**
   `docs/07` §7.2 names only the antecedent, the moderator and "all nine reflective"; §8.6 gives
   the chain as prose. **The edge list is in none of the documents.** It was escalated and the
   researcher chose **full mediation**:

   ```
   arm          -> EXPO, CTRL            (3 dummies, BASE the reference; Mode B, formative)
   EXPO, CTRL   -> FAIR, TRAN
   FAIR, TRAN   -> SATI
   SATI         -> LOYA, VOIC, EXIT
   EDEP         -> LOYA, VOIC, EXIT      (main effect)
   EDEP x SATI  -> LOYA, VOIC, EXIT      (moderation, product indicators)
   ```

   Seventeen edges, in `stats/spec.py::STRUCTURAL_EDGES` — **the only theory literal in the
   statistics layer.** `ModelSpec.fingerprint()` is `7c7fd73a12a4ec48`; it is recorded on every
   analysis run, pinned by the golden test, and drives the `UNVALIDATED` banner. Changing an item's
   construct, adding a path or changing the arm reference moves it and fails CI. **That is
   intended. `docs/07` §7.2 still needs the edge list written into it.**
2. **A Supabase project EXISTS and the migrations are still not applied — so `app.py` will not
   start** against it. `startup_check()` reaches the real database and dies with:

   ```
   twinlab.db.client.DbError: database call failed after 4 attempts: Error PGRST205:
   Message: Could not find the table 'public.app_config' in the schema cache
   ```

   **This is not a bug and nothing downstream is broken** — `pytest` is unaffected, because
   `tests/conftest.py` now blocks any live backend at the factory (§0.5). It is the boot gate doing
   its job.

   **To fix it (researcher):** run `001_init.sql` then `002_v2_model.sql` in the Supabase SQL
   editor, then `PYTHONPATH="src;." ./venv/Scripts/python.exe src/twinlab/ingest/seed_db.py`.
   **To work around it meanwhile:** run with the two variables blanked, which is how M10–M12 were
   built and verified:

   ```bash
   SUPABASE_URL="" SUPABASE_SERVICE_KEY="" PYTHONPATH="src;." ./venv/Scripts/python.exe app.py
   ```

   **Note:** four constraints in `002` validate existing rows and will fail loudly on a database
   carrying the prototype's defects. That is deliberate — `NOT VALID` would grandfather exactly the
   rows I15 forbids.

   **Everything through M12 has been exercised against the in-memory backend only** — including
   the whole UI, which has never read a real Postgres row.
3. **Containment's false-positive rate. The most consequential one open.** On the only live render,
   **2 of 10 paragraphs were falsely flagged**, every hit from one generic bigram —
   `("driver","app")`, which occurs in four different commitments. Because "one hit fails the cell"
   and a failed paragraph is cached as failed, a spurious `L4` dial-1 hit fails **every cell with
   Management = 1**, about a third of the sweep.
   **Not fixed on purpose.** Every obvious repair makes the detector *less* sensitive, and false
   negatives are the **undetectable** direction I3 exists to prevent. Trading a countable failure
   for a silent one is a research decision.
4. **HTMT confidence intervals.** `docs/07` §8.2 asks for HTMT "with bootstrap confidence
   intervals" and says the decisive test is an upper bound below 1. `LongBootstrap` produces path,
   loading, weight and effect intervals — **not HTMT**. The UI reports the point estimate against
   §8.2's 0.90 band, and `HtmtRow` already carries `ci_lower`/`ci_upper` so supplying an interval
   switches the verdict to the CI rule with no other change. Adding it means a **second full
   resample loop** (~25 minutes at 5,000 samples). Whether that cost is worth paying is the
   researcher's call.
5. **The Analyst's tools.** `docs/02` §1's table gives it "metric readers"; the prose below it and
   §4.4 both say it lost its history tools in 2.0. It is seeded `tools: []` — the tightening
   direction. Reverting that is a research decision.
6. **`PersonaIncomplete`.** A row missing any battery answer refuses to build a persona rather than
   building a shorter one. If partial rows should build partial personas, that is the researcher's
   call.
7. **Panel size vs eligible twins.** Fewer eligible twins than `panel_size` raises
   `InsufficientEligibleTwins` rather than drawing a short panel.
8. **`ANCHOR_CHUNKS_PER_BRIEF = 9`.** The specification names no chunk count. Accepted 2026-09-29
   **"for now"**. Turning it costs a `style_version` bump and ten calls.
9. **`word_max = 150`, set 2026-09-29 and deliberately unverified.** Paragraph length may vary a lot
   between dial-1 and dial-2, and **length is a stimulus property** — if it tracks dial, part of any
   lever effect is "more text".
10. **The twin temperature is still 0.7, a placeholder — and test 8 now exists to set it.**
    `docs/02` §7.3 says to compute it, not choose it. M13 implemented test 8 and it writes
    `app_config["twin_temperature_recommendation"]`; **`TwinConfig.temperature` is deliberately
    untouched**, because it is frozen onto every session's config and a silent change would make
    two sessions incomparable with nothing in the data saying why. **The recommendation rule is
    not in the specification.** M13 used the only rule §4 test 8's prose yields without a free
    parameter — *the lowest temperature whose between-twin index SD is still above zero* — and
    recorded it as an AMBIGUITY in `docs/DECISIONS.md`. **Confirm or replace that rule, then apply
    the value deliberately.**

## 0.8 Specification defects found so far — flagged, not silently fixed

Each is recorded in `docs/DECISIONS.md` under its milestone. **None is blocking.** They are listed
here because a fresh session will otherwise rediscover them one by one.

| Where | The problem | What was done |
|---|---|---|
| `docs/01` §2 | `legacy_crosswalk.json` "24 rows" is not reproducible from §4's table | Built the only construction yielding 24: 20 explicit renames + 4 family pattern rules. No acceptance test rests on the guess. |
| `docs/01` §9 vs `docs/11` M1 | §9 lists **18** seed assertions; M1 calls them "17" | All 18 implemented, so the criterion is met as a superset. One document needs a one-word fix. |
| `docs/01` §2 | Attributes "9 constructs" to `instrument.json`, which does not contain them | `CONSTRUCTS` is a frozen constant in `models/reference.py`, cross-checked on load against `instrument.json`'s own metrics block. |
| `docs/02` §2.1 | Names eight registry schemas, none of them the Manager's, yet §1 lists the Manager | `ManagerState` / `ManagerDecision` declared in `models/run.py` and registered beside the eight. |
| `docs/02` §1 | The agent table gives the Analyst "metric readers"; the prose below removes its tools | Seeded `tools: []`. See §0.7 item 5. |
| `docs/11` M4 | **"none of the 34 holdout item stems appears" is unsatisfiable for 16 of them** — each H2 item `mirrors` a battery item and carries the same stem by construction, and I6 *requires* the persona to carry it | Test changed, not the builder. Asserts no holdout item in `items_used` or by name, H3's 18 stems absent, and **two rows differing only in all 34 holdout answers give the byte-identical passage and hash**. |
| `ARCHITECTURE.md` §8.1 | Its ZeroGPU premise is false | §0.6. Researcher decided: run locally. |
| `docs/03` §4.2 + `worked_out_eg.txt` | **The specification's own exemplar render failed its own word band** — both call the `01000` paragraph 66 words; it is 71 | **RESOLVED** — researcher widened the band to 45–150. **Outstanding: "66 words" in both files, and `docs/11` M5's 80-word bullet, each need a one-line fix.** |
| `docs/07` §2.1 | Warns that reversing every item about 8 corrupts three constructs. **All three reverse-coded items are `agree7`**, so the corruption described cannot currently occur | Nothing changed — `score()` reads each item's own scale. A test asserts **no reverse-coded item is 5-point**, so if that changes the assertion fires. §2.1 needs a one-line correction. |
| DDL vs `docs/GOOGLE_FORM.md` | The schema implies intake screens; `GOOGLE_FORM.md` says nothing infers from the screeners | Both honoured: `eligible` is derived and **stored**, and **`outcome` is never `screened_out`**. |
| `supabase/functions/survey_intake/index.ts` | **Never executed.** No `deno`, no Supabase project, so its HMAC/Storage/HTTP layer is *mirrored from* the tested Python, not proven. `rows.mjs` **is** tested against the Python under Node | On first deploy: POST `apps_script/sample_payload.json` with a valid signature (expect **200**) and with a mangled one (expect **401**). Nothing in CI can catch this. |
| ~~`services/lab.py::VALIDITY_TESTS` vs `docs/08` §4~~ **FIXED in M13** | **Test 1 was flagged `needs_live_model=True`, and it must not be.** `docs/08` §4's table gives Test 1 "New LLM calls: **none**", and its section says outright "It needs **no new model calls** — it re-scores stored vectors — so it should be run early and often." The card makes the UI badge it *needs a live AI model*, which says the opposite of the specification's own advice. Test 3 is correctly `False`. | **Fixed.** Flipped to `False`, proved on `StubModelClient`'s counter, and a bookkeeping test now ties every badge to `CALLS_PER_TWIN` so they cannot drift apart again. Test 3's and Test 7's card descriptions were also wrong and were corrected. |
| **`docs/07` §7.2 / §8.6** | **The structural edge list is specified nowhere.** Neither section yields one, and `ARCHITECTURE.md` §10 does not carry it as an open question with a default | Escalated, not picked. Researcher decided (§0.7 item 1). **`docs/07` §7.2 needs the edge list written into it.** |
| **`docs/07` §8.1** | Specifies `rho_A`, but the engine's `reliability()` does not return it | Read from `plsc().rho_a()`. No formula reimplemented. §8.1 could name where it comes from. |
| **`docs/07` §8.2** | Requires HTMT "with bootstrap confidence intervals"; `LongBootstrap` does not produce them | Point estimate judged against the 0.90 band; the CI path is wired for when a value arrives. §0.7 item 4. |
| **`docs/07` §11** | Lists `female` and `tenure_months` per respondent; neither is on `survey_submissions` — both live on `twins` | The export joins `twins` on `submission_id` and writes an **empty cell**, never a zero. |

---

# Step 1 — The repo as you find it

## 1.1 FROZEN — never regenerate, never hand-edit

```
data/reference/criteria.json                 33 rows
data/reference/criterion_findings.json       33 rows
data/reference/gaps.json                     30 rows
data/reference/thresholds.json               10 rows
data/reference/corpus_chunks.json           126 rows
data/reference/chunk_criterion_links.json   171 rows
data/reference/instrument.json               73 items, 5 scales, 6 metrics
data/reference/dial_lookup.json              5 levers x 3 dials
additional_data/**                           the source documents
```

This is the scientific artifact. The entire treatment is a lookup over it. `chunk_id`,
`criterion_id`, `item_id` and `gap_id` are **opaque stable keys** cited by the codebook — never
renumber one, even when it looks misfiled.

**Two more files, generated in M1 and now also fixed:**

```
data/reference/arms.json                     4 rows   (docs/01 §5)
data/reference/legacy_crosswalk.json        24 renames (docs/01 §4, see §0.8)
```

`./venv/Scripts/python.exe src/twinlab/ingest/build_reference.py --check` **must exit 0 at all
times** — it does right now, with ten `OK` lines. If it fails with `PackageNotFoundError`, a
`.docx` is open in Word — close it.

The eight original files' sha256 are hard-coded in `tests/test_m1_reference.py`. If that test fails,
**stop**: the frozen data moved and every number downstream moved with it.

**The item register is frozen too**, and M12 depends on that: `stats/spec.py` reads every
construct's indicators out of it rather than listing them, so a construct cannot drift from the
register that defines it. An item removed at analysis time is an **exclusion list**, not a
re-coding (`docs/07` §8.4).

## 1.2 Config that exists and is correct

```
config/settings.py            pydantic-settings; max_concurrency=1, panel_size=20
config/agents.default.yaml    M2. The five agents. prompt_hash is computed on load.
config/style_contract.yaml    M5 reads this: word band 45-150, forbidden terms, grade 4-16
config/form_map.yaml          112 Form question -> item_id mappings
config/twin.default.yaml      M6. MUST carry max_concurrency — seed_db.py reads it from there.
config/analysis.default.yaml  M8. Index weights; default unweighted. The sign flip is NOT here —
                              it comes from constructs.index_sign in the frozen data.
apps_script/build_form.gs     The Form is unchanged.
apps_script/intake.gs         Repoint at the Supabase Edge Function URL. Keep the HMAC.
apps_script/sample_payload.json   The shared intake contract fixture. Do not edit.
docs/GOOGLE_FORM.md           The Form build spec. Still correct.
docs/SETUP.md                 Update for the local-execution decision in M14, not before.
```

`supabase/functions/survey_intake/` holds `index.ts`, `rows.mjs` and two **generated** assets kept
honest by `./venv/Scripts/python.exe tools/gen_edge_assets.py --check`. **Never hand-edit the two
JSON files** — regenerate them.

`tests/fixtures/` holds only an `__init__.py`. The stub model client is
`registry.StubModelClient`, which counts calls per `agent_id` — which is how "the design agent was
called exactly 10 times" is asserted, and how **M13's "tests 1 and 3 make zero LLM calls"** must be
asserted. **Do not write a second stub.**

---

# Step 2 — Build

## 2.1 The work order

`docs/11_BUILD_PLAN.md` is your work order.

```
M0  Scaffold and portability        DONE   M8  Analysis                        DONE
M1  Reference data, schema          DONE   M9  Intake and the generator        DONE
M2  Output contract and registry    DONE   M10 UI shell and Twin Lab           DONE
M3  Lookup, odometer, panel         DONE   M11 Twin Studio and Agent Studio    DONE
M4  Persona                         DONE   M12 Statistics, golden dataset      DONE
M5  Design agent and Checker        DONE   M13 Validity tests                  DONE
M6  Twin agent, quality gate        DONE   M14 Research model, invariants      DONE
M7  Orchestrator, budget, events    DONE

15 of 15 done. Deployment is struck, not outstanding (§0.6).
```

**M12 landed the whole measurement layer** — `src/twinlab/stats/`, `services/statistics.py`,
`models/stats.py`, `ui/pages/statistics.py`'s ten tabs, and `stats_table`. Read
`docs/DECISIONS.md` → M12 before touching any of it: it records the structural model the researcher
chose (and why it could not be picked), why the bootstrap is `LongBootstrap`, and the three
always-green gates that were fixed.

**The golden PLS-SEM gate passes**, so `docs/07` §10's precondition is met and every Statistics
number is now reportable. `tests/test_stats_golden.py` pins 345 statistics to |Δ| < 0.001 and runs
as its own CI step. **If it fails, stop** — either the model, the fixture or the engine moved, and
the test says which.

## 2.2 What the finished milestones left open

None of it blocks you; all of it is something a fresh session would otherwise rebuild or trip
over. Full reasoning per milestone in `docs/DECISIONS.md`.

**Deliberately unfinished, each for a stated reason:**

| What | Where it sits | Why it was left |
|---|---|---|
| `analyse` is **not wired** into `SessionRunner` | `orchestrator/loop.py` takes it as an injected callable and records `skipped` when absent | M8 built the pieces; connecting them needs the answer store and the twins' own survey vectors, which is **service-layer** work |
| The **429 backoff ladder** (`docs/04` §5.3) | not implemented | No acceptance criterion covers it and it needs a live provider. The `asyncio.Semaphore` pool **is** in and tested correct at 1 |
| The **Manager's three tools** still raise | `agents/tools.py` | The Manager is `enabled: false` and nothing calls it. That comment says "M7" and is stale |
| `index.ts`'s HMAC/Storage/HTTP layer | `supabase/functions/survey_intake/` | No Deno, no Supabase project. §0.8's row has the two-request check for first deploy |
| The Agents tab's **three workflow buttons enqueue a stub** | `ui/pages/lab.py` | The confirm step, the real budget, the log tree and the status card are all live; only the start is a stub |
| The **live twin call** the six costly validity tests need | `services/validity.py` takes it as an injected `ask`, exactly as `SessionRunner` takes `ask_twin` | M13 built all eight tests; **no live twin path exists anywhere in the build yet** — the Studio's *Ask the twin* has the same gap. Until one is wired, tests 4-8 record `INCONCLUSIVE` and say why |
| The **quality gate does not store the twin's H2 answer vector** | `validity/quality.py::quality_row`'s `detail`, under `services/validity.H2_ANSWERS_KEY` | M13's tests 1 and 3 re-score that vector and make **zero** model calls. Writing it is the cheapest unlock in the build: it turns the two most important tests from `INCONCLUSIVE` into real verdicts at no provider cost |
| *Import twins from the survey* and *Check twins against their drivers* | `ui/pages/lab.py` | Rendered and budgeted, not wired |
| Studio's *Ask the twin* records the run but **the answer table is empty** | `ui/pages/studio.py` | Filling it needs a live twin call |
| `pages/{driver_survey,generator}.py` | still M0 stubs | Neither has a milestone: `docs/11` never assigns them one, and no acceptance criterion depends on either |

**Contracts nothing may break** (M10–M13 hold all of these; M14 must too):

- **`ParagraphPool` is the only thing that may render a paragraph**, and `checker.check_variant()` is
  the only thing that may declare one usable. **A twin must never be shown a variant whose
  `CheckerReport.passed` is not `True`** (I3). **M13's tests 2 and 4 both create stimuli — read
  their entries in `docs/11` M13 carefully: test 4's spec is flagged `synthetic_probe`, is never
  written to `variants`, and must be unreachable from the Dial board. M13 built both guards into
  `models/validity.py` and calls them at the write.**
- **`00000` is blocked from the Dial board's "Ask the twins" button**. `ControlCellError` exists.
- **A rerun inherits the original session's panel** unless the researcher explicitly chooses a new
  one (I14).
- **The scenario paragraph and "what the twins are told" are different artefacts** and must never be
  swapped: a twin never sees bullets, and the researcher's bullet summary is never fed to a model.
- **`run_events` polling is incremental.** `EventLog.since(after_id)` only.
- **Every payload is `redact()`ed.** References and telemetry, never bodies; 8 KB cap.
- **`ui/` may import `services/` and `models/` only.** The import-linter is the first CI step.
- **No LLM call in a Gradio handler's synchronous path** (`CLAUDE.md` rule 12).
- **Never paint an initial state from a repeating `gr.Timer`.** Use `components.load_once`. Only two
  repeating timers are legitimate and both are specified; a scan test rejects any other.
- **A studio run is quarantined** and a **manual twin can never reach a panel**.
- **`manager_plan` builds a plan and starts nothing.** Asserted behaviourally and by AST.
- **`native` is never an output mode** (I13).
- **Statistics never reads the sweep** (`docs/07` §1) and the counterfactual layer never reads
  `survey_answers`. Conflating the two layers is the easiest serious mistake in the project.
- **Every statistics table carries a legend** (`docs/05` §4.4) and **every result view carries the
  five provenance facts** (`docs/07` §9). `stats_table` raises without a legend.
- **The model specification is frozen by fingerprint.** Changing it fails the golden test, by design.

## 2.3 The gate rule

**A milestone is not done until its acceptance tests pass. Do not build ahead.**

The ordering is not stylistic — later milestones depend on frozen artefacts from earlier ones. M2
came before any agent because retrofitting validation is exactly how silent corruption gets in.
M1 came before everything because if the frozen data is wrong, every number downstream is wrong.

For each milestone: read its section in `docs/11_BUILD_PLAN.md`, write the acceptance tests
**first**, then make them pass. Report which tests pass and which do not. Never report a milestone
complete with a failing test.

## 2.4 Testing rules

- **Never call a live LLM or a live DB in a test.** `tests/conftest.py` installs a fresh
  `InMemoryBackend` for **every** test *and*, since M12, blocks `SupabaseBackend` construction at
  the factory for the whole session — because the per-test fixture is function-scoped and a
  **module- or session-scoped fixture escapes it**. That is not hypothetical; it reached the
  researcher's real project. **If you write a higher-scoped fixture that touches the database,
  install an `InMemoryBackend` inside it** (`tests/test_m12_integration.py::completed` shows the
  pattern, including re-installing it after the per-test fixture runs).
- **Test the contract, not the prose.** Assert the design agent was called exactly 10 times for 243
  codes; do not assert the wording it produced. **M13 did this for tests 1 and 3: the assertion is
  on `StubModelClient`'s counter, not on what their prose says.**
- **Every invariant gets an executable test naming it in the docstring.**
  `tests/test_invariants.py::DEFERRED` names every invariant that has no test yet and the milestone
  that owns it, and a bookkeeping test fails if that drifts **either way**. **`DEFERRED` is empty:
  all seventeen have executable tests.** A new invariant goes in with the milestone that owns it.
- **A gate that cannot fail is not a gate.** Where a test enforces a prohibition, also write the
  test that proves it rejects a violation — and **inject the violation once and watch it fail.**
  Three always-green gates survived eleven milestones because nobody did that (§0.5).
- **Ban scans must ignore comments and docstrings**, and must use a **line-based** stripper.
  `_executable_source` in `tests/test_m10_ui.py` and `executable_source` in
  `tests/test_m0_scaffold.py` are both line-based now. A token-based one silently breaks every
  multi-token pattern.
- **Anything claimed reproducible "across processes" gets a subprocess test** with
  `PYTHONHASHSEED=random`.
- **The golden PLS-SEM test gates every statistic.** It must keep passing to |Δ| < 0.001. If you
  change `stats/spec.py`, `stats/dataset.py` or the engine version, it will fail — that is the
  point. Regenerate with `tools/gen_golden.py --write` **only** when the change was intended, and
  read the diff.
- `.github/workflows/ci.yml` runs: layer boundaries, M0 portability, `build_reference.py --check`,
  `seed_db.py`, the invariant suite, **the golden statistics test**, the full suite, the edge
  assets check, the intake contract, then ruff over `src tests tools`. Only the M9 Apps Script step
  is still commented out. **Uncomment yours as you land it.**

## 2.5 M13 — what it built, for when you need to change it

Landed 2026-09-29. Kept here because M14 touches the same surfaces.

- **`docs/08` §4 is the specification.** Eight tests, each with its own subsection (§4's table gives
  the call cost: tests 1 and 3 are free, test 5 is 2N, test 8 is 3N). §5 is the verdict vocabulary,
  §6 is reporting. `validity/tests.py::CALLS_PER_TWIN` is that table, executable.
- **`validity/tests.py` is pure.** Every statistic is deterministic Python over stored integers
  (I12); nothing in it reads, writes, calls a provider or knows what a database is. Change a
  verdict rule here and nowhere else.
- **`services/validity.py` is the only thing that appends.** `append_result` inserts and has no
  update path (I9). It also refuses a non-`INCONCLUSIVE` verdict on zero twins immediately before
  the write, which is the line the prototype's defect went through.
- **`validity_results`'s columns are** `test_id · session_id · twins_n · mode · provider · model ·
  temperature · statistics jsonb · verdict · headline · detail · config_version`, with
  `validity_zero_n` enforced in Postgres **and** in the in-memory backend. **Read the columns
  before inventing a `detail` key** — M10 learned that lesson the hard way.
- **Both quarantine guards live in `models/validity.py`**, not in `services/`, because `db/` may
  import `models/` and nothing else (`ARCHITECTURE.md` §4) — and a guard that cannot be called from
  the repository is a guard in a handler. `assert_not_a_probe` is in `VariantRepo.put`;
  `assert_not_ablated` is in both `twins` inserts.
- **The six costly tests take an injected `ask`**, like `SessionRunner`'s `ask_twin`. Nothing wires
  one yet. If you wire a live twin call for M14, these six become real without touching
  `validity/tests.py`.
- **Test 2 is the exception among the six**: it reads the stored `SHAM` control rather than asking
  again, because `SHAM` runs once per session before the sweep (`docs/03` §6.1).
- **Test 8 writes `app_config["twin_temperature_recommendation"]` and never
  `TwinConfig.temperature`.** §0.7 item 10 says why, and what the researcher still owes.

---

# Step 3 — When you are stuck

## 3.1 The escalation order

1. **Check `ARCHITECTURE.md` §10** — it may be a known open question with a stated default.
2. **Check `docs/DECISIONS.md`** — it may already be decided, with the reasoning. Read this before
   questioning any existing choice.
3. **If it affects research validity — stop and ask.** Do not pick. This includes: adding a control
   cell, changing a threshold, altering the panel rule, adding a metric, changing what a dial means,
   changing the structural model, or relaxing an invariant. **M12 had to do exactly this** — the
   path model was absent from every document, and picking it would have frozen a guess into the
   golden test as "validated".
4. **If it is purely mechanical** — pick the simplest thing, proceed, and add one line to
   `docs/DECISIONS.md` saying what you picked and why.

**If the specification itself is wrong or self-contradictory** — which has now happened sixteen
times (§0.8) — say so plainly, implement the reading that protects the invariant, record it in
`docs/DECISIONS.md` as an AMBIGUITY, and report it. Do not silently pick and move on, and do not
weaken a test to match a defective criterion.

**If two answers you were given contradict each other, go back.** M12's moderation question had to
be asked twice, because the chosen edge list had no path for the chosen interaction term to attach
to; implementing either reading silently would have changed a model the researcher had just decided.

## 3.2 Stop and ask when

- An invariant (I1–I17) blocks you. **Never work around one.** Say which one and why.
- A **binding** rule blocks you — the four portability rules in §8.2 are binding, not advice.
- You want to add a control cell, an experimental arm, a metric, or a fourth cache. Don't.
- A specified UI element cannot be built in Gradio. Degrade the **styling**, never the **content**
  or the **ordering**, and record the degradation in `docs/DECISIONS.md`.
- A test only passes if you relax an assertion. That is the test working.

## 3.3 Things that are not yet measured — do not guess them

| Unknown | Where it bites |
|---|---|
| The Ollama Cloud free **credit allowance** (unpublished) | `budget.est_credits` stays `None` until supplied |
| Whether Ollama Cloud **honours `seed`** | `docs/09` §5. Assume it does not until measured. |
| Real **per-call latency and token counts** | Every estimate uses 8 s / 2,300 in / 400 out |
| The right **twin temperature** | Still 0.7. Test 8 exists and writes a *recommendation*; the rule behind it is §0.7 item 10, and applying the value is the researcher's act. |
| Containment's **false-positive rate** | Measured once: **2 of 10** live paragraphs. §0.7 item 3. |
| Whether paragraph **length now tracks dial** | `word_max = 150` leaves it free to vary. |
| Whether the **UI works against real Postgres** | Everything through M12 ran on the in-memory backend only. |

**Resolved, no longer unknown:**

- *Whether `pydantic_ai` works against Ollama Cloud* — **yes.** 2.51.0, and 10 real design calls
  plus 3 checker probes succeeded on `gpt-oss:120b` (2026-09-29). I13's premise is unchanged: the
  provider still does not *enforce* the schema.
- *Whether the tests pass on the pinned Gradio* — **yes**, 5.50 in the venv.
- *Whether a long background task survives ZeroGPU* — **moot.** Not deploying there.
- *Whether Python 3.13 runs on ZeroGPU* — **no, the image is 3.10.**
- *Whether `openpls-engine` covers the whole `docs/07` §8 battery* — **yes**, 1.11.0, verified
  stage by stage. Import name `openpls`.
- *Whether our wiring of the engine is correct* — **yes**, to |Δ| < 0.001 across 345 statistics,
  and both faults `docs/07` §10 names are caught.
- *Bootstrap cost* — **~0.3 s per iteration at N=120**, so the specified 5,000 is ~25 minutes.

---

# The non-negotiables — quick reference

Keep this visible while you work. Full text in `CLAUDE.md` and `ARCHITECTURE.md` §2. Invariants
already under executable test are marked ✓.

**The treatment**
- ✓ `version_code → DeltaSpec` is a pure lookup. **No model is ever consulted** about what a dial
  means (I1).
- ✓ The design agent has `tools: []`, enforced in `build_agent`. It renders; it never proposes (I2).
- ✓ Every render passes the Checker before any twin sees it. **One containment hit fails the cell** —
  there is no threshold (I3).
- ✓ Ten non-zero lever paragraphs plus one fixed dial-0 string. The design agent runs **10 times per
  style version, not 243** (I4, I5).

**The twin**
- ✓ The persona is Python-built, lossless over all 37 battery items, **words not numbers**, and
  excludes Parts 15/16/17 absolutely (I6, I7).
- ✓ Persona and round prompt are separate documents (I8).
- ✓ Attention checks `AMQ6` and `ALGO5` are never put to a twin, and — since M12 — are never
  indicators in the measurement model either. The battery is 37, not 39 (I10).
- ✓ Validate every output in Python. Never coerce (I13).

**The evidence**
- ✓ `runs`, `run_events`, `twin_answers`, `twin_quality_runs`, `validity_results` are
  **append-only**. Latest is a pointer flipped in the same transaction (I9).
- ✓ Everything shown to a twin is reproducible from stored fields. **The prompt is rebuilt, never
  stored** (I11).
- ✓ No model ever produces a metric — in either layer. The Analyst writes prose about numbers it was
  given, and that prose is numerically grounded before storage (I12).
- ✓ The analysis panel is frozen per session (I14).
- ✓ `twins_n = 0` is `failed`, never `completed`. A validity test on zero twins is `INCONCLUSIVE`,
  never `PASS` (I15). **M13 was where this was easiest to get wrong, and it is now guarded in
  three places.**
- ✓ Nothing durable on the filesystem (I16). ✓ Nothing is imputed (I17) — including a respondent
  with a missing indicator, who is dropped whole rather than filled in.

**`tests/test_invariants.py::DEFERRED` is empty — all seventeen have executable tests.** A new
invariant goes in `DEFERRED` with the milestone that owns it; a bookkeeping test fails if that
drifts either way.

**The layers**

| Layer | May import | May not |
|---|---|---|
| `ui/` | `services/`, `models/` | `db/`, `agents/`, raw SQL |
| `api/` | `services/`, `models/` | `db/`, `agents/` |
| `services/` | everything below | `gradio`, `fastapi` |
| `agents/` | `models/` | `db/`, `ui/` |
| `db/` | `models/` | `agents/`, `ui/` |

`supabase` is imported in exactly one file: `db/client.py`. SQL lives only in `db/`. Enforced by
`.importlinter` (direct imports) and `tests/test_m0_scaffold.py`.

**Deployment portability — binding, and still binding while running locally**
1. The UI is a plain `gr.Blocks`; `app.py` and `app_docker.py` are thin entrypoints holding no
   logic.
2. Survey intake lives in the Supabase Edge Function, never in the Space.
3. Every capability is a service-layer function; `api/` is an optional wrapper. **No feature may
   depend on an HTTP route existing.**
4. Never import `spaces`; never decorate anything `@spaces.GPU`. *(Actually enforced since M12 —
   the scan was silently always green before.)*

---

# What "done" means

A researcher with no engineering background can:

1. Generate synthetic surveys, or receive real ones through the Edge Function **while the
   application is not running**.
2. Import consented respondents as twins and read a persona.
3. Run the quality gate and see who was kept, who was dropped, and why.
4. Set five dials by hand, see what the twins will be told **with no network call**, see the budget,
   and ask.
5. Watch the run as an expandable tree with every agent's input and output inspectable.
6. Read six shifts, the index, the interactions and a grounded written analysis — and click from
   any number through to Uber's own published words.
7. Run all eight validity tests and see failures reported as plainly as passes.  **← built; tests
   1-3 give real verdicts once the quality gate stores its H2 vectors, 4-8 once a live twin call
   is wired**
8. Run the full PLS-SEM battery on the human rows and export a scale-annotated matrix.  **← done**
9. Stop the app, restart it, and resume where it left off.

And a reviewer can trace any number in the paper back to a verbatim extract of Uber's policy without
a gap.

---

# Start now

**Use the venv (§0.0).** Seven checks, in this order. If any fails, **stop and report it** —
something has drifted and nothing downstream is trustworthy until you know what.

```bash
./venv/Scripts/python.exe -m pytest tests/ -q
```

**589 tests should pass.** Takes about 100 seconds.

```bash
./venv/Scripts/python.exe -m pytest tests/test_stats_golden.py -q
```

**17 tests, about 45 seconds. This is the gate for every statistic in the paper.** If it fails,
either the model specification, the fixture or the engine version moved — the failure names which.
Do not regenerate the expected values to make it pass unless you know what you changed.

```bash
./venv/Scripts/python.exe src/twinlab/ingest/build_reference.py --check
```

**Exit 0 with ten `OK` lines.** If it fails with `PackageNotFoundError`, a `.docx` is open in Word.

```bash
PYTHONPATH="src;." ./venv/Scripts/python.exe -c "from importlinter.cli import lint_imports_command as c; c.main([])"
```

**6 contracts kept, 0 broken.**

```bash
./venv/Scripts/python.exe tools/gen_edge_assets.py --check
```

**Two `OK` lines.**

```bash
./venv/Scripts/python.exe -m ruff check src tests tools
```

**All checks passed.**

```bash
SUPABASE_URL="" SUPABASE_SERVICE_KEY="" PYTHONPATH="src;." ./venv/Scripts/python.exe app.py
```

**With the two variables blanked it boots on the in-memory backend.** Without blanking them it
will **not** start — it reaches the real Supabase named in `.env`, whose migrations have never been
applied, and refuses to boot on `PGRST205`. **That is the boot gate working, not a bug** (§0.7
item 2).

**Once it starts, open http://127.0.0.1:7860 and click something.** This is the seventh check and it
is not optional: **both bugs found in M10 and M11 were invisible to the test suite.** A green suite
tells you the service layer is correct; it does not tell you the screen works — M13 and M14 each
added two defects found this way and no other. Five 30-second sanity checks:

- **Twin Lab → Dial board:** move the Conditions dial to 1. The code must become `01000` and the
  score `Fairwork score 1 of 10`. If it stays `00000`, something is overwriting the change handler.
- **Main menu:** *Where things stand* must fill **immediately**, not after ten seconds.
- **Statistics:** set *Bootstrap samples* to 10 — a **Blocked** banner must appear naming the floor
  of 30. Press *Run the analysis* on an empty database — it must say *"it is not a weak result, it
  is not a result"*, not throw.
- **Twin Lab → Validity tests:** tests 1 and 3 must carry a grey *no model calls* pill, not the
  amber one. Press *Run this test — 1* on an empty database: the confirm step must read **Calls 0**,
  and pressing *Start* must append an `INCONCLUSIVE` row saying no twin has a stored H2 vector —
  never a `PASS`, never a throw.
- **Research model:** the measurement mapping table must list all nine constructs with their item
  blocks and indicator counts, and the fingerprint beneath the diagram must read
  `7c7fd73a12a4ec48` — the same string Statistics records on every analysis run. Press *Write it
  all to a document*: a `.md` file must download.

Stop it with `Ctrl-C`. On Windows a stale server keeps the port and will serve you your **old**
code — if `curl` still answers after you stop it, find the PID with `netstat -ano | grep ':7860'`
and kill it, or you will debug a file you already fixed. That cost an hour in M10.


**The build is complete.** §0.7 is what remains, and all of it is the researcher's.

**M13 is done; §2.5 reads as a record of what is there rather than a to-do.** The four things
it was easiest to break are all under executable test, each beside a test that injects the
violation and watches the refusal:

- **A test that ran on nobody is `INCONCLUSIVE`, never `PASS`** (I15), in three places:
  `ValidityOutcome` refuses to be constructed, `append_result` refuses to write, and the DDL —
  mirrored in the in-memory backend — refuses to store.
- **Every completed test appends** (I9). `services/validity.py` has no update or delete path for
  `validity_results`, asserted by source scan as well as behaviourally.
- **Tests 1 and 3 make zero LLM calls**, asserted on `StubModelClient`'s counter.
- **Tests 4 and 6's artefacts are quarantined at the write**, in `VariantRepo.put` and in both
  `twins` inserts — not in a handler.

**Read `docs/DECISIONS.md` → M13 and → M14 before changing either area.** Between them they record
two AMBIGUITIES the researcher owns — test 8's temperature rule (§0.7 item 10) and the research
content `docs/06` §8 requires but no document in this repository states — plus twelve specification
defects flagged rather than silently fixed.

**And do not run any git command.** The researcher owns git (§0.1); the repo is still not in it.
