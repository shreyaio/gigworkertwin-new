# Decisions log

Mechanical choices the specification is silent on, per `CLAUDE.md` → "When the spec is silent".
One line each: what was picked and why. Research-validity questions are **not** decided here —
they go to the researcher (`ARCHITECTURE.md` §9).

## M0 — Scaffold

- **2026-09-22 — `pyproject.toml` added.** Not in the §4 layout, but pytest needs `pythonpath`
  and ruff/black need a config home. No packaging behaviour depends on it.
- **2026-09-22 — `PYTHONPATH=/app/src` in the Dockerfile,** and a `sys.path` shim at the top of
  `app.py`. The layout puts the package under `src/` without an install step; this is the smallest
  thing that makes both `uvicorn app:app` and `pytest` resolve `twinlab`.
- **2026-09-22 — local Gradio is 6.22, `requirements.txt` pins `>=5.29,<6.0` per ARCHITECTURE §3.**
  The deployed image gets 5.x. Local runs emit a Gradio 6 warning that `theme`/`css` moved off the
  `Blocks` constructor; harmless, and the pinned version is the specified one.
- **2026-09-22 — tab stub modules created at M0, contents deferred to M8.** The shell has to name
  five tabs to satisfy the M0 acceptance test; `docs/04` owns what goes inside them.

### Rebuild, 2026-09-28

- **The v1.0 tree was archived to `_v1_removed/`, not deleted.** `HANDOFF.md` §1.3 says
  `rm -rf src/ tests/ …` after the safety commit in §0.1, but the researcher has reserved every
  git operation for themselves, so that commit does not exist yet and a delete would be
  permanent — the same reasoning that put the superseded v1.0 documents in `docs/_v1/`. The two
  PRESERVE files were copied to `_preserve/` first, and `_preserve/frozen_reference.sha256`
  records the eight frozen files' hashes from before the move; they verified unchanged after it.
  **`_v1_removed/` and `_preserve/` are scaffolding for the rebuild and should be deleted once
  the repository is in git.**
- **`demo.route()` is called outside the `gr.Blocks` context.** Gradio raises
  `ValueError: You cannot create a route while inside a Blocks() context`. The root page is built
  inside the `with`, the other seven after it. No effect on route order or content.
- **The CSS is attached by constructor kwarg where available, otherwise as an inline `<style>`.**
  Gradio 5 takes `css=` on `Blocks`; 6.x moved it off, and local development runs 6.22 while
  `requirements.txt` pins 5.x per ARCHITECTURE §3. `ui/app.py` detects the parameter rather than
  branching on a version string, so the tokens land in both. Delete the fallback when the pin and
  the local environment agree.
- **`python -m importlinter.cli lint` does not lint.** That module has no `__main__` handling, so
  it imports cleanly, prints nothing and exits 0 — a gate that silently always passes. CI and
  `tests/test_m0_scaffold.py` invoke the click command object directly, the test asserts the
  output actually contains a contract count, and a companion test appends a `ui/ → db/` import to
  prove the contract rejects a violation.
- **Ban scans ignore comments and docstrings.** `@spaces.GPU` and "Google Sheet" are named in
  prose in the very modules that forbid them, so a raw text scan flagged the prohibition itself.
  `executable_source()` in the M0 tests strips comments and docstrings and keeps ordinary string
  literals, which is where user-facing text lives.
- **The seed YAMLs are not recreated at M0.** `agents.default.yaml`, `twin.default.yaml`,
  `analysis.default.yaml` and `generator.default.yaml` appear in the §4 layout, but their fields
  are specified in `docs/02`, `docs/07` and `docs/08` and belong to M2, M5, M8 and M9. Writing
  them now would be building ahead. `form_map.yaml` and `style_contract.yaml` carried over
  unchanged.
- **CI steps for later milestones are present but commented out,** each labelled with the
  milestone that enables it. The alternative — adding them later — is how a gate gets forgotten.
- **The ZeroGPU gate is a separate Space, not a route in the app.** `_probe/` is a self-contained
  three-file Gradio app depending only on `gradio`. A ninth route — even hidden — would have
  meant bending the eight-route contract in `docs/06` §0 for a temporary diagnostic, and a
  probe sharing the app's dependency set would confound "ZeroGPU killed the task" with
  "`openpls-engine` would not install". A free account may host two ZeroGPU Spaces, which is
  exactly what running both needs. **Delete `_probe/` when M1 closes.**
  The probe reports `INCONCLUSIVE` until the full 30 minutes have elapsed and never `PASS`
  early, mirroring I15: a gate that can pass without evidence is not a gate. It also reports
  the interpreter version, settling `ARCHITECTURE.md` §10 question "does Python 3.13 run on
  ZeroGPU" in the same visit.
- **`tools/deploy_space.py` uploads over the HTTP API rather than pushing git.** A Space is a git
  repository, but the researcher is handling every git operation themselves, and `upload_folder`
  deploys without requiring this repository to be in git or creating a commit in it. It uploads
  code only; secrets stay in the Space's own settings. Portability rule 1 is what makes this
  safe — `app.py` holds no logic, so there is nothing to configure at the deployment boundary.

### M1 deployment gate — measured 2026-09-28

Findings from the first attempt at the real target. **These are measurements, not decisions**;
the deployment target itself is the researcher's call (`ARCHITECTURE.md` §10 question 6).

- **`ARCHITECTURE.md` §8.1's VERIFY claim did not hold on the test account.** The claim —
  *"free personal accounts in good standing … may host up to 2 Gradio Spaces running on
  ZeroGPU"* — was marked VERIFY as true on 2026-09-28 and must be re-checked. Re-checked the
  same day: `POST /api/repos/create` with `space_hardware="zero-a10g"` returns **402 Payment
  Required** for the free account `shreyyyaa`. Corroborated by the pre-existing
  `shreyyyaa/twin-lab`, whose runtime reports `requested: zero-a10g, current: None` — it never
  received the hardware either. **Whether this is an account-specific condition or a change in
  Hugging Face's terms is not yet established.**
- **`tools/deploy_space.py` no longer requests ZeroGPU by default.** `--hardware` now defaults
  to unset, and 402/403 are reported with an explanation rather than a traceback. The script
  does **not** silently fall back to `cpu-basic`: a cheaper tier does not answer the M1
  question, and quietly deploying somewhere the specification did not choose is exactly the
  substitution this milestone exists to prevent.
- **`shreyyyaa/twin-lab` is `PAUSED` with `errorMessage: "Flagged as abusive"`.** Unresolved and
  under appeal with Hugging Face. The 503 served by that Space is a consequence of the pause,
  not of the application. Whether the flag is scoped to that Space or to the account is not yet
  known; a fresh-Space creation attempt failed on the 402 above before it could distinguish
  them.
- **Space creation fails on *every* tier, not just ZeroGPU.** With `space_hardware` omitted —
  i.e. requesting the free `cpu-basic` tier — `create_repo` still returns **402 Payment
  Required**. The account cannot create a Space at all.
- **The account meets both stated eligibility conditions.** `emailVerified: True`, and the
  account is at least six months old (its oldest access token dates from 2026-03-20).
  `isPro: False`, `canPay: False`.
- **DECIDED 2026-09-28 — run locally for now; hosting deferred, not abandoned. RESEARCHER.**
  Presented with the three deviations below, the researcher chose local execution and asked
  that the Hugging Face option stay open. It does, and at no cost: §8.2's four portability
  rules are unchanged and already enforced by `tests/test_m0_scaffold.py` — two thin
  entrypoints over one `gr.Blocks`, `spaces` never imported, every capability a service-layer
  function, `api/` optional. Nothing about running locally weakens any of them.
  Two things this decision does *not* do. It does not make **ZeroGPU** reachable later: that
  target still requires all three deviations, and choosing it in future is a fresh decision,
  not a resumption. It does re-open **PRO + Docker** as the clean hosted path, which §8.2 was
  written for and which costs a commit.
  Consequently the M1 ZeroGPU gate is **moot for the chosen target** — a long background
  `asyncio` task obviously survives on the researcher's own machine — and M7 onward may
  proceed. `_probe/` is kept rather than deleted: if hosting is revisited it is the first
  thing to run. No 3.10 syntax gate is added, because the chosen target and the Docker path
  both control their own interpreter; one would be needed only if ZeroGPU came back.
- **ZeroGPU refuses to start without a `@spaces.GPU` function. This falsifies §8.1's premise
  and collides head-on with §8.2 rule 4.** After the Python 3.10 fix the Space still fails, now
  with `No @spaces.GPU function detected during startup`. §8.1 reasons that *"all inference is
  remote on Ollama Cloud, so nothing is decorated and the `spaces` package is never imported.
  **ZeroGPU is being used as a free CPU Space**"* — the platform does not permit that. Rule 4
  (*"Never import `spaces`; never decorate anything with `@spaces.GPU`"*) is stated as binding,
  so per `CLAUDE.md` hard rule 1 this was **not** worked around and no stub decorator was
  added. **Escalated to the researcher; the deployment target is unresolved.**
  Stated for the decision: using ZeroGPU now requires three simultaneous deviations — Python
  3.10 against a 3.13 floor, Gradio 6.28 against a `<6.0` pin, and importing `spaces` against
  rule 4 — in exchange for a free CPU box running a workload that needs no GPU. The two
  alternatives that require no deviation are local execution, and a paid tier with the Docker
  SDK, which §8.2 already designs for.
- **ZeroGPU runs Python 3.10 and ignores the Space card's `python_version`.** This answers
  `ARCHITECTURE.md` §10's open question *"Whether Python 3.13 runs on ZeroGPU"* — **it does
  not**, and the platform does not even offer the 3.12 fallback that question names. Measured
  from the run log of `ShreyaShah/twin-lab-probe`, which requested 3.13 in its card and
  crashed with
  `ImportError: cannot import name 'UTC' from 'datetime' (/usr/local/lib/python3.10/datetime.py)`;
  the build log independently shows every package resolving into
  `/usr/local/lib/python3.10/site-packages`. The probe is now 3.10-compatible and its card no
  longer claims a version the platform will not honour.
  **This contradicts `CLAUDE.md`, `ARCHITECTURE.md` §8.2 rule 4, and
  `requires-python = ">=3.13"` in `pyproject.toml`, and is for the researcher to decide.**
  One measurement that narrows it: all 34 application source files currently parse under
  3.10 syntax (`ast.parse(..., feature_version=(3, 10))`), so the conflict today is about the
  declared floor rather than about code that has to be rewritten. That will stop being true
  the moment anything uses 3.11+ syntax, which nothing yet guards against.
- **ZeroGPU forces Gradio 6, which contradicts the pin in `ARCHITECTURE.md` §3.** The first
  build failed outright. A ZeroGPU Space appends its own packages to the install line —
  observed 2026-09-28 as `pip install -r requirements.txt "torch<=2.13.0"
  gradio[oauth,mcp]==6.28.0 "uvicorn>=0.14.0" "websockets>=10.4" spaces==0.51.3`. Against
  `gradio>=5.29,<6.0` that is unsatisfiable, so pip fails before any application code runs.
  `_probe/requirements.txt` now names no dependency at all. **The application's own
  `requirements.txt` carries the same fatal pin and must be decided before the shell can
  deploy — RESEARCHER.** Two mitigations already exist: `ui/app.py` detects the `css=`
  constructor kwarg rather than branching on a version, and local development has been on
  Gradio 6.22 since the rebuild began, so the shell is already exercised on 6.
- **The platform installing `spaces` does not breach §8.2 rule 4.** The rule forbids importing
  it and decorating with `@spaces.GPU`; ZeroGPU installs `spaces==0.51.3` into every image
  regardless. `tests/test_m0_scaffold.py` asserts on our source, which is the right scope, and
  the probe reports at runtime that the module has not been imported.
- **Resolved: §8.1 was right, and `cpu-basic` is the tier that is not free.** The Hugging Face
  new-Space form, viewed on the clean account, shows Gradio free and **Docker "Paid"**; under
  *Space hardware — Free tier* it offers **ZeroGPU (Free)** while **CPU Basic and Custom
  Hardware are disabled**. So a free account's Gradio Space must be created *on ZeroGPU*, and
  the intuition that "we only need a CPU, so ask for the cheaper tier" is backwards here.
  The second account's 402 was self-inflicted: `--hardware` had been defaulted to unset, so
  the API defaulted to `cpu-basic`, the one tier the account cannot have. `--hardware`
  defaults to `zero-a10g` again, and the 402 message now names the cause.
  **The deployment target is unchanged, and `HANDOFF.md` §2.3 was not triggered.**
  Still unexplained: the *first* account's 402 when `zero-a10g` **was** requested. The abuse
  flag on `shreyyyaa/twin-lab` remains the best explanation for that one, and remains
  unconfirmed.
- **~~That hypothesis was tested and rejected the same day.~~** A second, independent account
  (`ShreyaShah`: verified email, a **write**-role token, no Spaces, no flag) returns the same
  **402 Payment Required** when creating a free `cpu-basic` Gradio Space. Two unrelated
  accounts failing identically rules out account standing as the cause and leaves §8.1's
  broader VERIFY claim — *"Hugging Face requires a paid plan to create Gradio or Docker
  Spaces"* — as the operative fact. The ZeroGPU exception either no longer exists, does not
  apply to these accounts, or is not reachable through the API. **This is the
  stop-and-re-decide branch of `HANDOFF.md` §2.3: the deployment target is now an open
  research-instrument decision for the researcher, not a default the build may pick.**
  The superseded hypothesis is kept below, struck through in substance, because a rejected
  explanation that looked convincing is worth remembering.
- **~~Working hypothesis: the 402 is downstream of the abuse flag.~~** §8.1's exception is granted
  to *"free personal accounts **in good standing**"*. Verified email and account age both hold,
  so the remaining condition is good standing — which a Space flagged as abusive plausibly
  revokes. That would make one flag the single cause of every failure observed today: the 503
  on `twin-lab`, the 402 on ZeroGPU, and the 402 on cpu-basic. **Unconfirmed** — Hugging Face
  has not been asked yet, and no API field exposes standing directly.
- **No technical workaround is appropriate.** If the hypothesis holds, the blocker is a
  moderation state, and creating Spaces under other names to get around it would be flag
  evasion. The appeal is the only route.
- **Consequence for the build: none yet.** M1's other work is target-independent, and the
  background-task question stays open. Nothing from M7 onward may be built on the assumption
  that it is settled. The fallback stated to the researcher, and not yet chosen, is to run the
  instrument locally and treat a hosted Space as a convenience: no invariant, metric, or twin
  behaviour depends on where it runs.

## M1 — Reference data and schema

- **2026-09-22 — `ingest/reference_store.py` holds the frozen data in memory.** Not named in the
  §4 layout, which shows only the files. Lookup, persona, metrics and the checker must stay
  deterministic without a network call, so the eight JSON files load once into a validated
  singleton and everything downstream reads that.
- **2026-09-22 — `db/client.py` exposes a narrow `DbBackend` protocol with two implementations.**
  `supabase` is still imported in exactly one file. The in-memory backend exists so the seeder,
  the repositories and the invariant suite are testable with no Supabase project, per the brief's
  Step 5. It logs a warning when selected and `require_live_backend()` refuses it.
- **2026-09-22 — the two "same transaction" pointer flips are Postgres functions**
  (`runs_complete`, `quality_run_record`) in `001_init.sql`, called by RPC. PostgREST cannot send
  two statements in one transaction, and I9 requires the demote and the insert to land together.
- **2026-09-22 — `orchestrator/odometer.py` written during M1.** `seed_db.py`'s specified
  post-seed assertion includes the digit-sum identity, so the odometer is its dependency. M3
  still owns its acceptance test.
- **2026-09-22 — `tests/conftest.py` drives coroutine tests directly when pytest-asyncio is
  absent.** A skipped invariant test is an invariant that is not being guarded.

### M1 rebuild, 2026-09-28

The 2.0 pass over M1. Everything above in this section is the 2026-09-22 v1.0 work and still
holds where it is not contradicted here.

- **The nine constructs are a frozen constant in `models/reference.py`, not an eleventh reference
  file.** `docs/01` §2 attributes "9 constructs" to `instrument.json`, but `instrument.json` is
  frozen byte-identical and does not contain them, and §2 says there are exactly ten files. A new
  file would change a stated count; a constant changes nothing. `CONSTRUCTS` sits beside
  `MET_CRITERIA` and `LEVER_NAMES`, which are normative-specification constants for the same
  reason. **It is not free-floating:** `ReferenceData._check_constructs` asserts on load that the
  six signed constructs name exactly the six metrics in `instrument.json`, with the same scale,
  the same direction and the same item list, so the constant and the frozen file cannot drift.
  `tests/test_m1_reference.py` flips one `index_sign` and asserts the load is refused.
- **`survey_items.construct_code` is derived from the item block at seed time,** by
  `construct_code_for()`, because `instrument.json` is frozen and cannot carry the column. Null
  for attention checks and for both holdouts, per `docs/01` §6.1. An H2 item's construct is
  reached through `mirrors` and is deliberately **not** copied onto the row, so a query for
  `FAIR` cannot pool Part 7 with Part 16.
- **`arms.json`'s arm-to-lever assignment is transcribed from `docs/01` §5 and verified three
  ways, not re-derived by a scorer.** The derivation is already resolved by evidence (see
  "Resolved 2026-09-28 (second pass)"). Re-running it as term-overlap scoring inside a frozen
  builder would add a tie-break failure mode with no research meaning. Instead the builder
  asserts: the four labels appear **verbatim and in order** among Part 15's manipulation-check
  options parsed from the survey source; each non-control code is a single-lever dial-1 code over
  a non-empty dial-1 gap set; and every term quoted in §5.1's derivation table
  (`safety equipment`, `accident and injury cover`, `human point of contact`, `Extend appeals`,
  `voice mechanism`, `recognise and bargain`) still appears in that lever's dial-1 commitment
  text. Any of the three drifting is a build failure. The derived codes match §5 exactly:
  `BASE 00000 · MGT1 00010 · CON1 01000 · REP1 00001`.
- **`legacy_crosswalk.json` holds 24 *rules*; `legacy_items` holds 73 *rows*.** The 24 are 20
  explicit non-identity item renames (`PAF`, `PAT`, `LOY`, `VOI`, `EXT`, `ECD`, `AC1`, `AC2`) plus
  the four holdout families kept as pattern rules (`post_<X>`, `cj{v}_cj_fair|resist|stay`). The
  seeder expands the families and adds the identity mappings, so all 73 prototype identifiers
  resolve and nobody re-derives one by hand. **AMBIGUITY — flagged, not decided:** `docs/01` §2
  states `legacy_crosswalk.json` has "24 rows", and 24 is not reproducible from §4's table any
  other way — that table itself has 15 rows and covers 73 identifiers. The reading above is the
  only construction that yields 24, and it is a reconstruction rather than a quotation. Nothing
  asserts 24 in §9 or in M1's acceptance list, so no acceptance test rests on the guess.
- **`docs/01` §9 lists 18 seed assertions; `docs/11` M1 calls them "17".** All 18 are
  implemented, so the acceptance criterion is met as a superset either way. **AMBIGUITY —
  flagged.** The discrepancy is worth a one-word fix in whichever document is wrong.
- **`001_init.sql` is restored verbatim and 2.0 lands as `002_v2_model.sql`,** per `docs/01` §6
  ("an existing project migrates rather than being rebuilt"). The file came from `_v1_removed/`
  and is byte-identical to it; that is restoring an artefact the specification names, not
  importing from the archive.
- **`002` is strictly additive and `survey_responses` is left in place.** `docs/01` §11 says it
  was "split into" `survey_submissions` + `survey_answers`, but it may hold v1 evidence and
  deleting append-only evidence is not a migration step (I9). The legacy importer is its only
  reader. `tests/test_m1_schema.py` asserts that no `drop table` and no `drop column` appears in
  any migration.
- **Four constraints in `002` validate existing rows and will fail the migration on a database
  carrying the prototype's defects** — a `completed` run with `twins_n = 0`, a quality row with
  `items_n = 0`. `NOT VALID` would have grandfathered exactly the rows I15 exists to forbid.
  Failing loudly and handing the decision to the researcher is the specified behaviour.
- **Columns added to pre-existing tables carry defaults** (`survey_items.part_name = ''`,
  `sessions.panel_size = 20`, `sessions.panel_seed = 0`, `twin_quality_runs.items_n = 0`), so the
  migration also succeeds against a project already seeded from `001`. Every one of them is always
  supplied by its writer — the seeder for `part_name`, session creation for the panel fields — so
  no default is ever the stored value for a real row, and `quality_has_items` is what stops the
  `items_n` default from being usable.
- **`app_config` gains a sixth key, `reference`,** holding
  `{hash, instrument_version, crosswalk_version}`. `docs/01` §6.10 lists five keys
  (`twin`/`style`/`orchestrator`/`analysis`/`generator`), but M1 requires `reference_hash` to be
  "computed and checked at startup" and `app_config` is the only versioned store that exists. The
  digest covers all ten files, in a fixed order, with their names.
- **The startup gate lives in `services/config.py::startup_check()` and is called by
  `ui.app.build_ui()`.** Both entrypoints get it and neither gains logic, so portability rule 1 is
  intact. It runs its own `asyncio.run` deliberately: there is no running loop at build time, and
  this is not a Gradio handler. An unseeded database is a setup step and only warns; a *different*
  digest raises `ReferenceMismatch` and the application does not start. With no live database
  configured the check logs that it was not performed rather than passing silently.
- **The `ui`, `api` and `supabase` import-linter contracts are scoped to direct imports**
  (`allow_indirect_imports = True`). The layer table allows `ui/ -> services/` and
  `services/ -> db/`, so `ui -> services -> db.client -> supabase` is the mediation the table
  exists to create; read transitively, the contracts forbid the service layer from ever reaching
  the database, which makes the architecture unimplementable. They were written at M0 before any
  service imported `db/`, so the distinction had not yet come up. **Nothing is relaxed in
  substance:** M0's companion test appends a direct `ui/ -> db/` import and still gets a
  rejection, `test_m0_scaffold.py` scans the source for the file-level "supabase in exactly one
  file" claim, and `tests/test_m1_schema.py` appends a direct `import supabase` to
  `services/config.py` and asserts the linter fails.
- **The in-memory backend mirrors the DDL check constraints.** `runs_completed_has_twins`,
  `validity_zero_n`, `quality_has_items`, `quality_h3_gates`, `quality_h2_arm`,
  `agent_no_native_output`, `analysis_bootstrap_floor` and `analysis_has_cases` are all enforced
  in `InMemoryBackend`, and the two generated columns (`speeder`, `mc_correct`) are computed
  there. Without this, the invariants enforced only in Postgres would be exactly the ones CI never
  tests — and I15 is the one the prototype broke.
- **`seed_db.py` skips a config table whose YAML does not exist yet.** `agents.default.yaml` and
  `twin.default.yaml` belong to M2 and M5, and M1 must be runnable before them. The skip is
  printed, not silent, and it applies only to `agent_configs`/`app_config` — configuration, not
  the frozen reference data this milestone is about. `style_contract.yaml` exists and is seeded.
- **`tests/conftest.py` installs a fresh in-memory backend for every test, autouse and
  unconditional,** so no test can reach Supabase even if the environment carries credentials. It
  also drives coroutine tests itself when `pytest-asyncio` is absent — a skipped invariant test is
  an invariant that is not being guarded.
- **The frozen sha256 manifest is hard-coded into `tests/test_m1_reference.py`** rather than read
  from `_preserve/frozen_reference.sha256`. That directory is scaffolding and is deleted once the
  repository is in git; the guard must outlive it.
- **`build_reference.py`'s ruff exemption is removed.** `E501`, `E741` and `B023` are gone: `l`
  renamed to `line`, the loop-variable closure in `parse_corpus` lifted to a module-level
  `chunk_field(block, name)`, long lines wrapped. `--check` proves all eight frozen files are
  byte-identical after the reformat, verified against `_preserve/frozen_reference.sha256`.
- **M1's deployment smoke test is struck, not deferred.** `HANDOFF.md` §0.6: the target is local
  execution, so there is no Space for a background task to survive on. Recorded in the M1 test
  module's docstring so a future reader does not go looking for it.
- **CI gains two M1 steps**, both before the suite: `build_reference.py --check` and `seed_db.py`.
  The seeder runs against the in-memory backend — no `SUPABASE_*` secret exists in CI and none may
  be added.
- **`app.py`'s docstring no longer says ZeroGPU is the target.** Rule 4 is unchanged and still
  stated; only the claim that the Space "is being used as a free CPU Space" was removed, because
  §0.6 settled that it cannot be.

## M2 — Item register and persona builder

- **2026-09-22 — `twins.background jsonb` added to `001_init.sql`.** Parts 3 (extras), 4 and 14 are
  survey content with no `item_id`: the 73-item register is frozen and `survey_responses.item_id`
  is FK'd to it, so they cannot be rows there. The persona must be lossless (docs/02 §5), so they
  are kept on the twin rather than dropped. Written once at intake, never edited.
- **2026-09-22 — why-probes are addressed by stable keys, not item ids.** `WHY_CONTROL`,
  `WHY_SATISFACTION`, `WHY_OTHER_WORK`, and `OWN1`–`OWN5` for Part 14. `WHY_PROBE_ANCHOR` maps
  each probe to the battery item whose `survey_responses.why_text` column holds it.
- **2026-09-22 — every quantity the builder renders is spelled in words** (`spell()`), including a
  categorical answer that is itself a numeral such as "2" platform apps. I7 only requires it of
  Likert values; doing it everywhere means "no bare numeral" is a property of the whole passage and
  the I7 test needs no exceptions. A verbatim option label such as "Class 12" keeps its digits —
  rewriting the driver's own answer would be paraphrasing.
- **2026-09-22 — attention checks contribute no persona clause.** `AMQ6` and `ALGO5` are recorded
  in `EXCLUDED_FROM_PERSONA` with the reason, so the exclusion is declared rather than implicit.
  They carry no experiential content and are never put to a twin (I10).

## M2 — The output contract and the agent registry

2026-09-28. `agents/contract.py`, `agents/registry.py`, `agents/tools.py`, the five prompt files,
`config/agents.default.yaml`, and the model shapes the registry names.

> The section above titled "M2 — Item register and persona builder" belongs to the **superseded
> v1.0 build plan**, whose milestones were numbered differently. In `docs/11_BUILD_PLAN.md` the
> item register is M1 and the persona builder is M4. Both sections are kept: the v1.0 entries
> record real decisions, several of which still hold.

- **`docs/02` §2.1 names eight registry schemas and none of them is the Manager's,** yet §1 lists
  the Manager as one of the five agents. Its two shapes — `ManagerState` (the `<<<STATE>>>`,
  `<<<BUDGET>>>`, `<<<STOP>>>` blocks §4.5 describes) and `ManagerDecision`
  (`{action, unit, reason}`) — are declared in `models/run.py` and registered beside the eight, so
  `SCHEMA_REGISTRY` holds ten. **AMBIGUITY — flagged.** Pointing the Manager at another agent's
  shapes would have been worse than adding two: a config whose declared output does not match what
  the agent returns is a validation gate that cannot fire.
- **The Analyst is seeded with `tools: []`.** `docs/02` §1's table gives it "metric readers", but
  the prose directly beneath that table says it "**lost its ReAct loop and its history tools**" in
  2.0 and "now receives one assembled bundle and nothing else", and §4.4 repeats it. The two
  disagree; the table is stale. **AMBIGUITY — flagged, resolved conservatively:** a tool is an
  unbounded surface through which a number the analyst was not given can enter its prose, which is
  exactly what I12 forbids, so the tightening direction is the safe one. Reverting it would be a
  research decision.
- **The Manager's three tool names are registered at M2 and raise `NotImplementedError` until M7.**
  `register_tool("session_state", …)` and two more, in `agents/tools.py`. The alternative was to
  seed the Manager with `tools: []` and `react: false` until M7, which would have made
  `agents.default.yaml` a placeholder rather than the real config, and would have hidden the
  `react: true` config from every M2 gate. A stub that raises cannot cause a silent defect; a stub
  that returned a plausible empty state would let the Manager route on fiction, which is not
  distinguishable downstream from routing correctly. The Manager row is `enabled: false`.
- **`build_agent` validates before importing any provider library.** `pydantic_ai` is not installed
  in this environment and is not needed to prove a config is inadmissible, so `validate_config` is
  pure and the M2 acceptance tests for `native` output and unknown tools run without it. The lazy
  import also keeps the deterministic layers free of the dependency.
- **`native` output is refused in three independent places:** a `field_validator` on
  `AgentConfig.output_mode` (so the row cannot even be constructed in memory, including one read
  back out of a database that acquired it before the DDL constraint existed), `validate_config`, and
  the DDL constraint `agent_no_native_output`. `docs/02` §5.1 asks for two; the third costs nothing
  and closes the "read it back from the database" path.
- **The prompt skeleton is enforced, not just documented.** `check_prompt_skeleton()` requires
  `docs/02` §3.2's six sections, present and **in order**, and every agent's prompt goes through
  `resolve_prompt()` on load. §3.2 states the order is mandatory and §3.3 states that a reordered
  prompt is a different stimulus, so an unchecked skeleton would be a specification with no gate
  behind it. `# IF YOU CANNOT` is included in the check: a model given no failure path invents one.
- **`prompt_hash` is computed on load and never read from the YAML.** The two could otherwise
  disagree, and the hash's whole job (I11) is to describe the text the agent was actually given.
- **The five prompt bodies are transcribed from `docs/02` §4's stated contracts, not designed.**
  §4 opens "This is the contract each must satisfy" and enumerates what each agent receives, the
  rules that matter and the `# IF YOU CANNOT` behaviour; the files say those things and nothing
  more. **M5, M6 and M7 own their wording** and will bump versions. Two consequences of §3.4 and
  §3.5 are already honoured and tested: `design_v1.md` and `twin_v1.md` carry **no few-shot
  example**, and neither contains any of the style contract's eight forbidden terms — §3.5 extends
  them to "the prompt files themselves". That forced rewording: the twin's rule 1 says "never
  mention being a model, a program or a simulation" rather than naming what it is.
  `checker_v1.md` and `analyst_v1.md` do carry examples, which §3.4 explicitly permits because
  neither produces stimulus or data.
- **Normalisation keeps an unreadable value exactly as it arrived** rather than dropping it or
  substituting anything. A `5.5` stays `5.5` and becomes a `not_an_integer` defect; an
  unrecognisable key stays and becomes an `extra` defect. Dropping either would hide the failure,
  and hiding a failure is the forbidden column of `docs/02` §5.3 by another route.
- **Disagreeing duplicates are preserved as an `_Ambiguous` marker, not resolved.** `docs/02` §5.3
  forbids "pick the first of two disagreeing duplicates", so the ambiguity has to survive
  normalisation in order to be reportable. A duplicate whose values *agree* is collapsed, which is
  the allowed repair.
- **A boolean is not an answer.** `bool` is a subclass of `int` in Python, so `True` would
  otherwise validate as `1`. Rejected in `_as_int`, in `validate_answers`, and in both answer
  schemas.
- **`validate_answers` returns every defect, not the first.** A targeted repair should name all of
  them at once and spend a single serial slot — the scarcest resource in the system
  (`ARCHITECTURE.md` §7.1).
- **The repair instruction groups defective items by their own range.** A repair covering a 5-point
  and a 7-point item must not offer one shared range; that would reintroduce the prototype's "1 to
  7 for everything" defect inside the repair path, where nothing downstream would catch it.
- **The repair ladder lives in `contract.py` as `run_answer_ladder(ask, …)`, agent-agnostic.**
  `ask` is a callable the caller supplies, so the ladder never imports a provider and M6 wires the
  twin agent into it rather than reimplementing it. M2's acceptance tests drive it with a stub.
  `attempts` counts the first call, so the default of 2 is "one call plus one repair" exactly as
  §5.4 specifies.
- **`docs/02` §6's numeric grounding is implemented at M2, with the rest of the contract,** rather
  than at M8 with the analyst. §5 and §6 are one contract, `numeric_tokens()` is a property of the
  bundle shape the registry already names, and I12 is the invariant most easily left as prose.
  `offending_sentences()` exists because §6.1 specifies a retry that *quotes the offending
  sentence* — quoting the token would tell the model a digit was wrong somewhere, not which claim
  is unsupported.
- **`numeric_tokens()` includes signed and absolute renderings as well as 1 and 2 dp.** §6.1 names
  the rounded forms and explains "+1.6" as a legitimate rendering of `1.62`; a shift of `-0.59`
  is legitimately written "0.59" and "+0.59" in different sentences, so all of them are allowed.
  The structural integers §6.1 permits are the metric count, the baseline count, the number of
  non-zero dials and the version code's own digits — nothing more.
- **`tests/test_invariants.py` starts here and carries its own bookkeeping.** `DEFERRED` names the
  seven invariants with no test yet (I1, I3, I4, I7, I8, I14, I17) and the milestone that owns
  each, and a test fails if an invariant is neither tested nor declared — and also if one is
  declared deferred while a test already names it. `docs/11` says the suite accumulates from M2;
  without the bookkeeping, "accumulates" has nothing enforcing it.
- **I16's test scans for filesystem writes and exempts `build_reference.py` by name.** The builder
  is an offline one-shot that produces the frozen artifact and is never called by the running
  application; every other module is checked for `write_text`, `write_bytes`, `mkdir` and
  `open(..., "w")`.
- **`seed_db.py` now seeds `agent_configs` from `default_agent_configs()`, not the raw YAML,** so
  the stored `prompt_hash` is real and every config gate has already run before a row is written.
  This replaces the M1 placeholder that stored an empty hash.
- **`agents.default.yaml` quotes every instruction string.** An unquoted `Uncertainty fails closed:
  a call that cannot decide…` parses as a YAML mapping, not a string. Worth recording because the
  failure is silent in the editor and loud only at load.
- **CI gains the invariant step**, run on its own before the full suite so an invariant failure is
  unmistakable rather than one line in 132.

## M3 — Lookup, odometer, panel

2026-09-28. `variant/lookup.py`, `orchestrator/panel.py`, and the odometer's acceptance tests
(the module itself was written during M1, because `seed_db.py`'s digit-sum assertion depends on it).

- **`lookup("SHAM")` raises `ShamNotLookedUp` rather than returning an empty spec.** SHAM has no row
  in `dial_lookup.json`: its set is the three criteria coded **Met** (`ARCHITECTURE.md` §5.2), which
  are by definition not gaps, and its unfilled levers announce that lever's *existing* driver-facing
  policy (`docs/03` §6.2). Assembling that text is M5's. Returning an empty spec would have made the
  demand-characteristic control silently identical to the noise-floor control — the two cells that
  bound every reported result.
- **`do_not_say()` is in `lookup.py`, beside the thing it excludes.** `docs/03` §3 calls the
  exclusion set "the most important step in the pipeline", and it is derived from the same
  `gaps_by_lever` the lookup just produced. Putting it in `checker.py` would separate the boundary
  from its definition and leave the Checker as the only thing that knows where the line is.
- **`lookup()` copies the gap lists out of the reference store rather than aliasing them.** The
  store is a process-wide `lru_cache`d singleton, so a caller appending to a returned list would
  edit the frozen treatment table in memory for every later lookup in the process. There is a test.
- **The panel draw is a pure function over `(candidates, panel_size, panel_seed)` and never touches
  a database.** `docs/03` §9.1's sketch reads `twins` and `latest_quality()` inline; splitting the
  eligibility data out into `PanelCandidate` makes the draw reproducible across processes *by
  construction*, and makes I14 testable with no backend. The service layer (M7) is the only thing
  that has to know where candidates come from.
- **`proportional_stratified_sample` is implemented as largest-remainder (Hare) allocation with
  capacity redistribution.** `docs/03` §9.1 names the function and the properties — stratified on
  `city × service`, proportional, seeded — but not the rounding rule, and proportional allocation
  always needs one. Largest remainder is the standard choice, guarantees the seats sum to exactly
  `panel_size`, and ties break on the **stratum name** so the allocation depends on the populations
  alone. A stratum smaller than its quota returns its surplus and the remaining seats are
  re-allocated among strata that still have capacity, repeated until every seat is placed.
- **Determinism is enforced at three points, not one.** Strata are processed in sorted key order,
  members within a stratum are sorted by `twin_id` before `rng.sample`, and allocation ties break on
  the name. Any one of the three left out gives a draw that is reproducible inside one process and
  silently different between the session that created a panel and the session that resumed it —
  which is I14 failing in the one way no in-process test would catch. `test_m3_lookup_panel.py`
  re-runs the draw and the `delta_hash` in a fresh interpreter with `PYTHONHASHSEED=random`.
- **Too few eligible twins raises `InsufficientEligibleTwins` instead of drawing a shorter panel.**
  `sessions.panel_size` is frozen onto the session and reported with its results, so a panel of 15
  recorded as 20 would misstate the study; and a panel of zero would make every run `twins_n = 0`,
  which I15 forbids from ever being a result. The researcher lowers `panel_size` or quality-tests
  more twins. Nothing in the specification asked for a partial-panel mode and adding one would be a
  researcher degree of freedom.
- **A twin with no city or service lands in a stratum named `unknown`.** `docs/01` §6.4 gives the
  stratum as `'Mumbai|cab'` and says nothing about blanks. The alternatives were to drop such a twin
  (an undeclared eligibility rule) or to let it join whichever twins happen to share its blanks
  under an empty key. A named stratum keeps it eligible and keeps the omission visible in
  `session_panel.stratum`.
- **`manual` appears in no population's source set at all**, rather than being filtered separately.
  `docs/03` §9.3 says a manual twin has no real survey row and therefore no holdout and no quality
  score. Encoding it in `POPULATION_SOURCES` means `population: "both"` cannot accidentally include
  it, and a manual twin marked quality-passed by some future bug is still not eligible. Tested for
  all three populations.
- **`require_same_panel()` takes `(label, panel)` pairs.** `docs/04` §9 requires the error to *name
  the two panels*, which a bare comparison of two id sets cannot do. It also reports which twins are
  in one and not the other, so "refuses the comparison" is followed by "here is exactly why".
  Comparability is judged on membership, not draw order: `panel_ids()` is a frozenset, because draw
  order is provenance while membership is what makes a difference meaningful.
- **The grid-wide commitment count is asserted as a closed form.** Summing `len(commitments)` over
  all 243 codes gives 3,645 — each lever's dial-1 and dial-2 sets appear 81 times each, so
  `81 × ((2+3)+(3+6)+(4+8)+(3+8)+(3+5)) = 81 × 45`. It catches a truncated or duplicated odometer
  and a mis-keyed `dial_lookup` in one assertion, where a spot check on four codes would not.
- **I1 has a source-level test as well as a behavioural one.** `variant/lookup.py` is parsed and
  asserted to import no provider library, no HTTP client and no database module. The behavioural
  test proves the treatment *is* a table read today; the source test is what stops it quietly
  ceasing to be one.
- **I1 and I14 move out of `test_invariants.py::DEFERRED`**, leaving I3, I4, I7, I8 and I17 declared
  against M4, M5, M6 and M8.

## M4 — Persona

2026-09-28. `persona/builder.py`, the 2.0 twin models, and the acceptance tests for the restored
`persona/templates.py`. The templates themselves were preserved through the rebuild
(`HANDOFF.md` §1.2) and needed no change: they were already keyed per scale, which is what §7.1
requires.

- **`docs/11` M4's holdout criterion is unsatisfiable as written for 16 of the 34 items, and the
  test was changed rather than the builder.** The criterion asks that "none of the 34 holdout item
  stems appears" in the passage. Each H2 item `mirrors` a battery item and carries **the same stem
  by construction** (`docs/01` §3.5) — `H2_ALGO1`'s stem *is* `ALGO1`'s — and I6 requires the
  persona to carry `ALGO1`. So for the H2 half the criterion contradicts the invariant it exists to
  protect. **AMBIGUITY — flagged.** What is actually at stake is that no holdout *answer* can
  influence the passage, and that is now asserted three ways: no holdout item appears in
  `items_used` or by name, H3's 18 stems (which are unique to Part 17) are absent, and two rows
  differing **only** in every one of the 34 holdout answers produce the byte-identical passage and
  the same `persona_hash`. The last is the sharp test and the one the criterion was reaching for.
- **Part 15 cannot reach the persona structurally, not by exclusion.** `MC1` is not in the frozen
  73-item register at all: the manipulation check lives on `survey_submissions.mc_answer`
  (`docs/01` §5.2), and `SurveyResponse` has no field that could carry it. There is nothing for the
  builder to filter, which is a stronger guarantee than a filter.
- **A battery item with no answer raises `PersonaIncomplete`.** `docs/03` §7.1 says "every
  *answered* item contributes at least one clause", which read alone permits a shorter passage;
  `docs/11` M4 says all 37 contribute, asserted per item. The second is the 2.0 reading (the
  item-level holdout was dropped precisely so the persona could be lossless), and the first is
  v1.0 wording that survived. Building from a partial row would give a persona quietly missing
  clauses — indistinguishable downstream from one that never had them — while the twin built on it
  would answer those items with no experience behind it. A respondent whose row is incomplete
  should not have become a twin, and this is where that surfaces. **No partial-persona mode was
  added**; adding one would be a researcher degree of freedom.
- **`spell()` covers every quantity, not only Likert values.** I7 only requires words for ratings,
  but spelling ages, months, hours and dependants too makes "no bare numeral" a property of the
  whole passage, so the I7 test needs no exceptions and no allow-list. Carried forward from the
  2026-09-22 decision, unchanged.
- **A verbatim option label keeps its own digits.** `"Class 12"` stays `"Class 12"`: rewriting the
  driver's own answer would be paraphrasing, and I7 is about Likert values. A categorical answer
  that is *itself* a numeral — `"2"` platform apps — is spelled, because there it is a count the
  template turns into prose. Both cases have a test, so the boundary is fixed rather than
  incidental.
- **An out-of-range Likert value raises instead of being clamped to the nearest anchor.**
  `anchor_for("agree5", 6)` has no entry and raises `PersonaTemplateMissing`. This is the same rule
  as the output contract's (`docs/02` §5.3): inventing an anchor would convert a detectable data
  defect into a plausible-looking clause.
- **Part 14 is read from `twins.background.own_words`, with `SurveyResponse.own_words` merged in
  and the background winning.** The background copy is the stored one that a rebuild would read
  (`docs/01` §6.2), so it has to be authoritative; accepting the response copy as well means an
  intake path that carries Part 14 there does not silently lose it. Losing it is the specific
  failure `docs/03` §7.1 warns about.
- **Optional demographic fields are skipped when absent; battery items are not.** An unanswered
  optional question has nothing to carry, so skipping it is not a loss. The distinction is made in
  one place — `_render_fields` skips, `_battery` raises — so the two cannot be confused.
- **Determinism is tested across processes, with `PYTHONHASHSEED=random`.** The passage and its hash
  are asserted identical in a fresh interpreter. An in-process test passes against a builder that
  iterated a set anywhere, and that version produces a different `persona_hash` on the run that
  rebuilds a missing persona — which silently breaks the tie between a result and the text that
  produced it (I11).
- **The persona modules are asserted at the source level to import no provider, no HTTP client, no
  database module and no `random`.** `docs/03` §7.2 is explicit that a model-written persona would
  be an unauditable paraphrase; the behavioural tests prove the builder is deterministic today, and
  the source test is what stops it quietly ceasing to be.
- **`Twin` loses `consent_twin` and gains `submission_id` and `source: "manual"`.** The 2.0 split
  (`docs/01` §11) puts consent on `survey_submissions`, where a respondent who withheld it can be
  counted; a twin only exists for a consenting respondent, so a field on the twin could only ever
  drift out of step with the row that records the consent.
- **I6 and I7 move out of `test_invariants.py::DEFERRED`**, leaving I3, I4, I8 and I17 declared
  against M5, M6 and M8.

## M4 — Design agent and checker

> **v1.0 numbering.** This section is from the superseded v1.0 build plan. In
> `docs/11_BUILD_PLAN.md` the design agent and the Checker are **M5**; M4 is the persona, recorded
> in the section above. Kept for the decisions it records, several of which still hold.

- **2026-09-22 — the SHAM cell's unfilled levers announce existing policy** (researcher decision,
  asked and answered mid-M4). §5.2 fixes the sham's commitments to the three Met criteria, which
  sit on Contracts and Management only, yet requires five ordinary paragraphs. Pay, Conditions and
  Representation therefore announce, as though new, what that lever's driver-facing corpus already
  says — the sham's whole purpose. Selection is deterministic and minimal: one chunk per lever,
  driver audience, ordered by `chunk_id` (`SHAM_CHUNKS_PER_LEVER = 1`).
- **2026-09-22 — the sham's containment gate is scoped to that existing policy.** Containment asks
  "is there a commitment here beyond what this cell may say?" For the sham, what it may say *is*
  the existing policy, so that text is the allowed set. The gate still fails on any real gap
  commitment, because a gap's distinctive vocabulary is by definition absent from the policy it
  falls short of. No second containment path and no extra LLM call.
- **2026-09-22 — the sham occupies `dial = 3` in `lever_paragraphs`.** Its five paragraphs need a
  cache slot that cannot collide with a live dial-0/1/2 paragraph. The column has no CHECK
  constraint. I4's "ten paragraphs" still counts only dials 1 and 2.
- **2026-09-22 — reading-grade band is `[4.0, 16.0]` Flesch–Kincaid,** in `style_contract.yaml`.
  docs/02 §4.5 names the gate but no numbers. Wide enough that ordinary policy prose passes,
  tight enough that one cell cannot be markedly harder to read than another. CONFIG.
- **2026-09-22 — a cached paragraph is not re-rendered per cell.** docs/02 §4.5 allows one
  re-render on failure; applying it to a cache *hit* would call the design agent once per cell and
  break I4. A failed paragraph is cached as failed and every cell using it fails loudly.
- **2026-09-22 — the design prompt tells the agent to rephrase a forbidden term that appears in a
  commitment's own wording.** Gap `3.2.d` says "tier thresholds", meaning incentive tiers; copying
  it through would fail the invariance gate on every Contracts-2 cell. The gate is not relaxed.

## M5 — Design agent and Checker

*2026-09-28. `docs/11_BUILD_PLAN.md` numbering — the current one. The `## M4 — Design agent and
checker` section above is v1.0 numbering for the same subject; its decisions still hold and are
referenced rather than restated.*

### AMBIGUITY — the specification's own exemplar render failed its own word band

**RESOLVED by the researcher, 2026-09-29: the band is widened to 45–75.**

`docs/03` §4.2 and `additional_data/worked_out_eg.txt` both present a `01000` Conditions paragraph
as correct output and both call it **66 words**. It is **71** by any counting rule that does not
treat a bare em dash as a word, and 73 by naive `str.split()`. The band was **45–70**, so the
specification's own worked example was rejected by the gate the same specification defines.

The agent implemented the reading that protected the threshold — band untouched, discrepancy
reported — because `word_min` / `word_max` are researcher thresholds and widening a gate so an
illustration passes is not an engineering call. **The researcher then made it: widen.** That is the
right call on the evidence, because the alternative reading has a cost the agent could not weigh.
The exemplar is not merely an illustration; it is the only known-good render in the repository and
the thing the design prompt's register is calibrated against. A band that rejects it would have had
the design agent aiming at a target the specification's own best example misses, and the first
symptom would have been a re-render loop on live cells, months from now.

**75, not 71.** A bound set exactly at the one known-good render leaves no headroom, so an equally
good 72-word paragraph would fail for no reason. The band's ratio barely moves — 75/45 = 1.67
against 70/45 = 1.56 — so `docs/DECISIONS.md`'s original justification still holds: no cell can be
markedly longer than another.

`word_count()` counts whitespace tokens carrying at least one letter or digit, so punctuation is not
a word and an identical sentence cannot pass or fail on its dashes. `tests/test_m5_render_checker.py`
asserts **the 71 rather than the band**, so the counting rule stays pinned if the band moves again,
and pins 44 and 76 as the edges so a later widening cannot pass unnoticed.

**`style_version` was deliberately NOT bumped.** No paragraph has ever been rendered under v1:
`pydantic_ai` is not installed, no `.env` exists, the migrations are not applied, every cache is
empty. There is nothing to invalidate, and a v2 whose v1 produced no text would send a future reader
hunting for renders that never existed. **Any later change to the contract, once a single paragraph
exists, must bump it** — a cached paragraph served under a contract it was not written to is exactly
the confound the `(lever, dial, style_version)` key exists to prevent. The comment in
`config/style_contract.yaml` says so at the point of temptation.

**One number in the specification is still wrong.** `docs/03` §4.2 and `worked_out_eg.txt` both say
"66 words" about a 71-word paragraph. Widening the band does not fix that; those two files need a
one-word correction.

### Three guards on the style contract, because it is now a thing that changes

Added when the band moved. `load_style_contract()` reads the file; `validate_style_contract()` is
pure and holds the checks, so they can be tested on a mutated dict without writing to the
repository's own config (I16 — and a test that crashed mid-way would otherwise leave the real
contract corrupted).

- `dial_zero_text` must equal `DIAL_ZERO_TEXT` (I5) — already present.
- `style_version` must equal `settings.style_version`. **The value is declared twice**, in the
  contract and in `config/settings.py`, and nothing read the settings copy — which is precisely how
  it would come to disagree unnoticed. The render cache key is built from it, so a disagreement
  means two different contracts competing for one cache slot.
- The word band must be non-empty.

### Containment matches distinctive **bigrams**, not keywords

`docs/03` §5 gate 2 specifies "keyword and semantic scan over the do-not-say list" and defines
neither the keyword derivation nor the semantic step. Resolved by measurement against the one piece
of known-good output the repository contains — the exemplar above:

| Rule | Hits on the exemplar (must be 0) | Catches a verbatim 2.2 leak |
|---|---:|---|
| distinctive **unigrams** | **16 of 27** | yes |
| distinctive **bigrams** | **0** | yes |

A forbidden commitment's signature is its content-word bigrams minus those of the commitments the
cell *may* say. The unigram rule is unusable: `uber`, `trip`, `app`, `claim` and `written` are
shared vocabulary, not distinctive vocabulary, and a gate that fails every cell is not a gate.

Two structural properties are asserted over the frozen data, not assumed: across all **285**
`(lever, dial, forbidden)` combinations no signature is empty — an empty one would be a commitment
that could leak undetected — and every forbidden commitment dropped in verbatim is caught. The
allowed set is **this lever's commitments only**, deliberately not the anchor chunks: 45,000
characters of corpus in the allowed set would mask real leaks and could empty a signature outright.

**No semantic/LLM step was added.** `docs/03` §5 names coverage as "the only model step" and
`CLAUDE.md` asks whether any new call multiplies by 243 or by the panel. A second model call in
containment would do both while making a deterministic gate non-reproducible. The bigram rule is
deterministic, fails closed, and needs no network.

### `STOPWORDS` is a frozen constant, not config

Changing it changes every containment verdict retroactively. It lives in `variant/checker.py` beside
the gate it serves rather than in `style_contract.yaml`, so it cannot be edited as though it were a
style preference.

### `ANCHOR_CHUNKS_PER_BRIEF = 9` — CONFIG, and the one M5 pick worth a researcher's eye

`docs/02` §4.1 says "anchor chunks … for register only" and names **no count**. Taken literally,
`ref.anchor_chunks()` gives an `L4` dial-2 brief **93 chunks — 95,296 characters, roughly 24,000
tokens**, against `docs/10`'s 2,300-token per-call estimate. Ten times the planned prompt, for
material whose only job is to demonstrate the voice.

Capped following the selection idiom the researcher already approved for the sham: deterministic,
ordered by `chunk_id`, **round-robin across the gap's own `anchor_sources`** so every named source
contributes rather than the first source consuming the whole budget. Round-robin matters because the
sources do different jobs — `S15` shows the voice, `S32` shows what the Services Agreement already
says.

Cost is not the reason: I4 means this prompt is built ten times per style version, ever. Prompt
bloat degrading instruction-following is the reason. The cap is constant for a given
`(lever, dial)`, so it cannot vary with the cell and cannot confound a lever comparison, and it is
reversible — raising it is a `style_version` bump that re-renders exactly the ten paragraphs.

**Flagged to the researcher; 9 is a defensible default, not a derived number. Accepted 2026-09-29
("anchor chunk is ok for now") — explicitly as a for-now default, so it is worth revisiting once a
real render has been seen: if the ten paragraphs come back in the wrong register, this is the first
dial to turn, and turning it costs a `style_version` bump and ten calls.**

### The design brief carries no lever identity and no dial digit

`build_user_prompt()` emits the four blocks and nothing else — not `L2`, not `01000`, not the gap
ids. Two reasons. A digit telling the agent it is writing "the strong version" is a channel through
which cell identity can reach the prose and become a confound. And an agent given `2.2.a` cannot act
on it; only the sentence it stands for is actionable, which is why `do_not_say` is resolved to prose
before it reaches the prompt.

### Flesch–Kincaid is implemented in-repo, not taken from a dependency

The reading-grade band is a **gate**. A library version bump that changed a syllable heuristic would
move every cell's grade, and `requirements.txt` is the wrong place to record a research threshold.
No new dependency was added.

### The sham is assembled entirely from frozen data

Following the researcher's 2026-09-22 decisions without adding to them. `3.1.a` and `3.1.c` land on
Contracts and `4.1.c` on Management because `criteria.json` puts them at principles 3 and 4; their
text is the `reason` field of `criterion_findings.json`, which describes what Uber *already does*.
The three unfilled levers take their lowest-numbered `audience: driver` chunk
(`SHAM_CHUNKS_PER_LEVER = 1`). `do_not_say` is all 30 gap commitments. **Nothing was chosen for
plausibility and no free parameter was introduced**, so the escalation `HANDOFF.md` §2.2 anticipated
was not needed.

### Mechanical picks

- **A `cannot_render` refusal fails the report.** `CheckerReport` has `extra="forbid"` and no field
  for a refusal, so it is carried in `notes` and clears `in_band`. Nothing is padded or truncated.
- **Forbidden terms and intensifiers are reported in `notes`, not in `containment`.** `containment`
  is specified as "forbidden commitments detected"; a forbidden *term* is not a commitment. Both
  still fail the report.
- **`passed` is computed from explicit flags, never by re-reading `notes`.** An earlier draft
  inferred the style verdict by substring-matching its own note strings, where a reworded note would
  have silently turned a failure into a pass.
- **Dial-0 levers are neither probed nor scanned nor word-counted.** The fixed string is 4 words and
  would fail the 45–70 band; gate 4's byte comparison is what holds it to account (I5).
- **`load_style_contract()` raises if `dial_zero_text` disagrees with `DIAL_ZERO_TEXT`.** The two
  could otherwise drift, and I5 would fail silently in four cells out of five.
- **`RenderedVariant` was added to `models/variant.py`**, not to `variant/render.py` — `CLAUDE.md`
  rule 13. It holds all five paragraphs in `LEVER_BY_POSITION` order; the per-twin randomisation is
  M6's and happens when the round prompt is built.
- **`ParagraphPool` re-checks its cache under an `asyncio.Lock`.** At `max_concurrency = 1` this is
  redundant today, but two cells awaiting the same paragraph would otherwise each spend a design
  call, which is I4 failing at the concurrency boundary rather than in the arithmetic.

## M5 — findings from the first live render (2026-09-29)

Ten real design calls on `gpt-oss:120b` via Ollama Cloud, then coverage probes on `01000`. Two
defects fixed, two questions **escalated to the researcher, not decided**.

### What worked

- **`ToolOutput` structured output holds against Ollama Cloud.** 10/10 calls returned a valid
  `LeverParagraph`. I13's premise (the provider does not *enforce* a schema) is unchanged — the
  Python ladder still validated every one — but the round trip works.
- **The widened 45–75 word band: 10/10 inside.** Eight of ten landed on exactly 75, so the model
  writes to the cap; the band's upper edge is load-bearing, not slack.
- **Coverage worked well.** 3/3 entailed on `01000`, with discriminating reasons that cited the cost
  and publication conditions rather than rewarding tone.
- **Gradio pin resolved.** The suite passes on the venv's **Gradio 5.50**, inside
  `requirements.txt`'s `>=5.29,<6.0`. `HANDOFF.md` §0.7 item 2 recorded that tests had only ever
  passed on Gradio 6; they now pass on both.

### FIXED — two silent defects in M2's live client

Neither could be caught by CI, because CI never makes a live call.

1. **`result.usage()` raised `TypeError`.** `usage` became a **property** in pydantic-ai 2.x. The
   model call had already completed and been paid for; only the telemetry read failed, so ten calls
   were spent and their text discarded.
2. **Worse, and silent: the token fields were renamed** (`request_tokens`/`response_tokens` →
   `input_tokens`/`output_tokens`). A naive `getattr(..., default=None)` returns `None` on 2.x
   without complaint, and `docs/10` costs every estimate on those counts — the credit budget would
   have read as unmeasurable while appearing to work. `_token_counts()` now reads both generations
   and **raises** on a third rename rather than reporting `None`.
3. **`max_tokens` was declared on all five agents and never passed to the model.** Moot for a
   paragraph; the twin's 1024 is a real ceiling on a 37-item vector, and a truncated vector fails
   the contract rather than being coerced (I13) — it would have surfaced in M6 as unexplained twin
   failures, not as a missing setting.

`requirements.txt` pins `pydantic-ai-slim[openai]>=0.0.30` with **no upper bound**, which is how a
major-version API change walked in. Worth a ceiling; that is a researcher call.

### ESCALATED 1 — containment has a measured false-positive rate

**2 of 10 live paragraphs were flagged, and all five hits are false positives.** Four were triggered
by the single bigram `("driver", "app")` and one by `("indian", "drivers")`:

| Paragraph | Flagged | Trigger |
|---|---|---|
| L4 dial 1 | `3.1.b`, `3.1.c`, `5.1.b`, `5.2.b` | `("driver","app")` |
| L3 dial 1 | `4.2.c` | `("indian","drivers")` |

`("driver","app")` occurs in **four different** commitments — it is shared institutional vocabulary,
not the distinctive signature of any one of them. The 285-combination test proved signatures are
never empty and catch a verbatim leak; it did **not** measure false positives on realistic
non-leaking prose, where n was 1 (the spec exemplar). Live output is the first real sample.

This matters more than the count suggests: "one hit fails the cell", and a failed paragraph is cached
as failed, so a spurious L4-dial-1 hit fails **every cell with Management = 1** — about a third of
the sweep.

**Not fixed, deliberately.** The obvious repairs — require a bigram to appear in exactly one
commitment register-wide, and/or drop bigrams already present in Uber's own 126-chunk corpus as
register vocabulary — both make the detector *less* sensitive, and false negatives are the
**undetectable** direction that I3 exists to prevent. Trading a loud, countable failure for a silent
one is exactly the asymmetry `docs/03` §5 says to resolve in favour of noise. That trade is the
researcher's to make. The gate currently errs safe: it fails cells loudly.

### ESCALATED 2 — the word band and the commitment counts are in tension

**6 of 10 paragraphs failed the reading-grade band**, and the failures are not marginal: 34.7, 38.2,
34.3. Diagnosed, not guessed — those paragraphs are a **single 75-word sentence**, semicolon-chained,
with one terminal full stop. Flesch–Kincaid is ~0.39 x (words/sentences), so one 75-word sentence
scores ~34 mechanically.

**The grade gate is working correctly and should not be widened.** It is detecting a real register
failure: `docs/03` §4.1 sets the target register from `S15` — *"Safety is designed into the
experience."* — short, plain, second person. A 75-word semicolon chain is the opposite.

But the cause is arithmetic, not just prompt wording. Dial 2 carries up to **8 commitments** (L3, L4)
and dial 1 as few as 2. Eight commitments as short plain sentences needs roughly 100–120 words; the
cap is 75. The model is doing the only thing available to it — compressing eight undertakings into
one clause chain. Note the pattern: **every low-commitment paragraph passed the grade**, and the
three worst offenders are 8-, 5- and 3-commitment sets under the same 75-word ceiling.

The band cannot vary by lever or dial — `docs/03` §4.2 is explicit that anything varying with the
cell is a confound — so a single band must accommodate the **largest** commitment set. Three routes,
all research decisions:

1. **Raise `word_max`** so 8 commitments fit in plain short sentences (~110–120).
2. **Revise the prompt** under a `design_v2.md` bump to demand several short sentences, and accept
   that dial-2 coverage may then fail instead — trading a grade failure for a coverage failure.
3. **Reconsider one paragraph per lever** (`paragraphs_per_lever: 1`) for high-commitment levers.

Route 1 is the only one that does not trade one gate failure for another, but it lengthens the
stimulus every twin reads, which is a design parameter, not an implementation detail. **Stopping
here rather than picking.**

### RESOLVED — `word_max = 150`. RESEARCHER, 2026-09-29. Route 1, and deliberately unverified.

The researcher chose to raise the band rather than trade a grade failure for a coverage failure, and
**instructed that it not be verified** — log it and proceed to M6. Recorded here as such, because
the distinction matters to anyone reading the numbers later: 150 was **not** measured against live
output. It buys headroom, not a demonstrated fit. 45-75 was evidence-based; 45-150 is a judgement.

`style_version` still **not** bumped. Ten paragraphs were rendered live on 2026-09-29, but the pool
is per-process and in-memory, the migrations are unapplied, and `lever_paragraphs` has never been
written — so nothing persists that could be served under the wrong contract. **From M7, when renders
persist, this reasoning stops applying and a bump becomes mandatory.** The comment in
`config/style_contract.yaml` now says "persisted" rather than "exists" for exactly this reason.

**This supersedes an M5 acceptance criterion.** `docs/11` M5 says verbatim: *"A 41-word or 80-word
render fails `in_band`."* Under a 45-150 band an 80-word render is legitimately inside it. The test
was **not** quietly dropped: it is re-expressed as
`test_an_out_of_band_render_fails_in_band` (41, 44, 151, 200 fail) and 80 is asserted to **pass** in
`test_a_render_inside_the_band_passes_in_band`, so the contradiction is executable rather than buried
in prose. **`docs/11` M5 needs a one-line update**; it is the only one of the eight bullets that no
longer holds as written.

**Two things now unmeasured, to watch on the first real sweep:**

1. **Length may become confounded with dial.** `word_max` no longer binds for small commitment sets,
   so a 2-commitment dial-1 lever may write ~60 words while an 8-commitment dial-2 lever writes
   ~140. Paragraph length is a stimulus property a twin experiences, so if length tracks dial, part
   of any lever effect is "more text" rather than "stronger commitment". Under 45-75 the cap
   compressed everything toward one length and masked this; at 150 it is free to vary. Worth
   measuring once the ten paragraphs are rendered and frozen: record each one's word count and check
   whether dial-1 and dial-2 lengths separate.
2. **The reading-grade gate is now the only thing holding register.** With the band slack, `[4.0,
   16.0]` Flesch-Kincaid is the sole constraint keeping a paragraph from becoming a clause chain.
   It is doing real work — it caught all six failures above — and should not be widened without
   re-reading this section.

Neither is blocking, and neither is an M6 concern. Both are cheap to check the first time the pool is
rendered for real.

## M6 — Twin agent and the quality gate

*2026-09-29. `docs/11_BUILD_PLAN.md` numbering. All seven acceptance criteria green in
`tests/test_m6_twin_quality.py` (29 tests); I8 moved out of `DEFERRED`, leaving only I17 (M8).*

### CORRECTED — why-text is forbidden in the *stimulus*, not in the persona

The first draft of `assert_no_forbidden_content()` scanned the whole assembled prompt for why-text and
therefore rejected every valid round. **The persona block is supposed to carry the whys**: `docs/03`
§8's own diagram reads `[persona] <<<PERSONA>>> whys, open answers`, and I6 makes the persona lossless
over them. What I8 forbids is why-text travelling with the **scenario, baseline and battery**, because
a twin re-reading its own justifications beside each counterfactual restates them and looks immovable
no matter what it is shown.

So the guard has **two scopes**: holdout ids and the version code are checked over the whole prompt,
where they are forbidden everywhere; why-text is checked only after the `<<<END PERSONA>>>` fence.
Conflating them is wrong in both directions — the strict reading blocks every round, and a
persona-only reading would let a why reach the stimulus. Caught by the acceptance test, which is the
test working.

### `validity/quality.py`, not `analysis/` or `services/`

`ARCHITECTURE.md` §4 names `validity/tests.py` for the eight validity tests and `services/quality.py`
for the service wrapper, but nowhere for the gate's own logic. Put in `validity/quality.py`, beside
`tests.py`: it is validation, it is deterministic, and the service layer wraps it later. Mechanical.

### `max_concurrency` lives in `twin.default.yaml` although it is not a twin setting

`seed_db.py` (M1, done) reads `twin_yaml["max_concurrency"]` to build the `orchestrator` app_config
row, so creating `twin.default.yaml` without that key broke the seeder and eight M1 tests. The key
stays where the existing contract expects it rather than changing finished M1 code.

`load_twin_config()` pops it **by name** before validating the rest into `TwinConfig`, and asserts it
equals `settings.max_concurrency`. Popped by name, not by tolerating extras: `TwinConfig` forbids
extras so a typo'd threshold fails loudly, and a blanket filter would throw that protection away.
The guard exists because the value is declared twice and *both* are read — `seed_db` writes the YAML
value to `app_config` while the orchestrator will honour the settings value, so a disagreement means
the recorded concurrency is not the one that ran. Same class of defect as the `style_version`
duplication found in M5.

### Mechanical picks

- **`lever_order_for(seed)` uses a local `random.Random(seed)`, never the global RNG.** The order is
  persisted and expected to reconstruct (I11); the global RNG would make it depend on whatever else
  ran first in the process.
- **`rebuild_round_prompt()` *checks* the stored `lever_order` against what the seed regenerates**
  rather than trusting it. A disagreement means the text shown was not the text the provenance
  describes, so it raises: the result is unattributable, which is worse than a crash.
- **The `<<<BASELINE>>>` fence is absent, not empty, when no baseline is shown.** An empty fence tells
  the twin a baseline exists and was withheld, which is a different stimulus from never having had
  one. The quality gate needs this: the human had no baseline either (`docs/08` §2.1).
- **`average_scores()` sums `items_n` rather than averaging it.** It is a count of measurements taken
  and it is what `quality_has_items` constrains; averaging would report 18 for three runs of 18 and
  hide how much evidence the verdict rests on.
- **`pearson_r()` returns `None`, not `0.0`, when either side has no variance.** A twin that answered
  all six H3 versions identically has an *undefined* ordering, not an uncorrelated one, and 0.0 would
  let "predicted everyone's mean" look like a measured null — which is what validity test 3 exists to
  rule out.
- **`h2_arm_for()` raises on a mismatch** rather than recording it and moving on. `docs/08` §3.1:
  showing a twin a different arm than its human saw is a bug, not a variation.
- **`QualityScore` refuses `items_n = 0` at the model boundary**, so no code path can assemble one —
  I15 holds in the model, in `score_holdout`, and in the backend's `quality_has_items`.

### Not built, and deliberately

The gate's **orchestration** — rendering the six H3 codes through the real pipeline, looping
`quality_runs_per_twin`, writing the row — is M7's, which owns the run loop, the budget and
`run_events`. M6 built the scoring, the verdict, the round assembly and the row shape, each
independently testable. Building the loop here would have meant building M7's orchestrator early and
without its event log.

## M7 — Orchestrator, budget, events, resume

*2026-09-29. All nine acceptance criteria green in `tests/test_m7_orchestrator.py` (25 tests).
329 tests total.*

### The runner takes its model work as injected callables

`SessionRunner` receives `render_and_check`, `ask_twin`, `analyse` and `candidates` rather than
importing them. Two reasons, and the second is the real one:

1. M7 owns **sequencing and checkpointing**, not rendering or answering. Injecting them means the
   acceptance tests exercise exactly what M7 is responsible for, with a counter standing in for the
   provider — and "it resumed" versus "it resumed **without re-asking**" are different claims that
   only a call counter can distinguish.
2. `analyse` is M8's and does not exist yet. Injected, its absence is a `skipped` event rather than a
   stub that returns a plausible empty metric — and a plausible empty metric is how a run completes
   with numbers nobody computed.

### `cursor_index = None` means "fresh", and that is load-bearing

The loop runs `00000` and `SHAM` only when `cursor_index is None`. Using `0` for a fresh session would
make it indistinguishable from one resuming at index 0 — which is `start_code = "00000"` — and the
controls would either re-run on every resume or never run at all. `SessionRepo.create` therefore
inserts `None` explicitly rather than letting a default fill it.

### The cursor is advanced **after** the run, not before

So a crash re-runs at most one cell, and that cell is itself idempotent: its paragraphs are cached on
`(lever, dial, style_version)` (I4) and its answered twins are skipped via `twin_answers`' unique
index. Advancing first would silently skip a cell on every crash, and a missing cell in a 243-cell
grid is not visible by eye.

### `PanelRepo.freeze` raises rather than replacing

I14 is the one place idempotence is an invariant rather than an optimisation. A session that already
has a panel keeps it; attempting to freeze a second one is a `DbError`. Redrawing mid-session would
mean two cells answered by different twins inside one experiment, which is precisely what the
invariant exists to prevent — so the failure is loud rather than a silent overwrite.

### `redact()` raises on a body but truncates on size

Two different failures, deliberately handled differently (`docs/04` §7.2):

- **A forbidden key is a programming error.** There is always a reference to store instead, so it
  raises. Silently dropping it would hide that the caller believed it was recording something.
  `strict=False` exists for one caller — the error path — because a run must not fail over a log line.
- **Oversize is a data condition**, so it sheds the largest values and sets `truncated = true`, which
  is what §7.2 specifies. Shedding whole values rather than truncating the JSON text keeps the payload
  parseable, and the references survive while the bodies go.

`FORBIDDEN_KEYS` is checked **by name** as well as by size, because a *small* persona passage would
pass a size-only check and I11 is about the prompt being rebuilt, not about bytes.

### FIXED — the in-memory backend was not enforcing `run_events_payload_small`

The 8 KB cap existed only in `002_v2_model.sql`. M7's acceptance criterion is "no `run_events.payload`
exceeds 8 KB", and a cap enforced only in Postgres would be exactly the one CI never tests — the same
gap `docs/DECISIONS.md` → M1 records for I15. Now mirrored in `_check_constraints`, with a test that
the backend rejects an oversize payload.

### Budget arithmetic anchors

`sweep_budget` counts the two control cells (they add `panel_size` calls each but consume no
iteration, `docs/03` §6.1) and the sham's five paragraph slots. A full sweep at the default panel
comes to 243 x 20 + 10 design calls, which reconciles with `docs/10` §2's "~4,860 twin calls".

`est_credits` stays **`None`**. The Ollama Cloud free credit allowance is unpublished (`docs/10`
§3.3), and a number invented here would be reported as a cost. The three per-call constants
(`SECONDS_PER_CALL = 8`, `2300`, `400`) are named so `docs/10` §9's "measure 20 real calls" is one
edit and every estimate moves with it — **they are still placeholders.**

`quality_budget` uses `H3_CALLS_PER_REPEAT = 6`, not 18: the 18 H3 numbers come from **six rounds of
three items**, so a repeat is six calls. At N=500 and 3 repeats that is 9,000 calls, and a test
asserts the quality gate exceeds a full sweep — the cost ordering `docs/10` stresses.

### Not built, and deliberately

**The Manager's three tools still raise.** `agents/tools.py` says they raise "until M7 builds the
session state machine behind them", and the state machine now exists — so they *could* be wired. They
were not: the Manager is `enabled: false` in `agents.default.yaml`, no M7 acceptance criterion
exercises it, and wiring an agent nobody calls would add untested surface to the one component that
can route a session. Whoever enables the Manager should implement them against `SessionRepo` and
`EventLog`, with tests, as that milestone's work. The comment in `tools.py` is now slightly stale and
says M7 rather than "when the Manager is enabled".

**Backoff and the 429 ladder** (`docs/04` §5.3) are not implemented. No acceptance criterion covers
them, they need a live provider to exercise, and `run_twin`'s repair ladder already handles the
"fails for that cell only" outcome. The `asyncio.Semaphore` pool is in place and tested correct at 1,
which is the criterion M7 does state.

## M8 — Analysis

*2026-09-29. All seven acceptance criteria green in `tests/test_m8_analysis.py` (36 tests).
366 tests total. **`DEFERRED` is now empty: every invariant I1–I17 has an executable test.***

### SPEC OBSERVATION — all three reverse-coded items are 7-point, so §2.1's warning does not bite

`docs/07` §2.1 says: *"A 5-point item reverses about 6, a 7-point item about 8. Reversing every item
about 8 is a silent corruption of three of the nine constructs."* In the frozen register, `SAT2`,
`DEP1` and `H2_SAT2` are **all `agree7`**. Reversing about 8 is therefore *correct* for all three, and
the corruption the sentence warns about cannot currently occur.

**Nothing was changed.** `score()` reads each item's own `scales.points` rather than the metric's, so
the safeguard is implemented as specified and a future 5-point reverse-coded item cannot break it. The
unit test exercises `reverse_code` at both 5 and 7 even though only 7 occurs in the data, and a test
asserts that **no reverse-coded item is 5-point** — so if one ever becomes so, the assertion fires and
whoever changed it re-reads §2.1 rather than discovering the problem in a metric.

Worth a one-line correction in `docs/07` §2.1: the hazard is real in principle, but "three of the nine
constructs" describes a situation the data does not currently contain.

### FIXED — `computable_interactions` paired codes where one dominates the other

`01000` with `01010` has joint `01010`, so `extra` collapses to `−shift(01000)`: an arithmetic
artefact that would have appeared in the analyst's bundle looking exactly like a measured
interaction, and been written about as one. Pairs whose joint equals either input are now skipped.
Found by the acceptance test, which expected one computable interaction and got the same one twice.

### The index sign flip comes from the frozen constructs, not from config or a list

`constructs.index_sign` is `−1` for `VOIC` (pushback) and `EXIT` (leaving). Putting the flip in
`analysis.default.yaml` would let a researcher invert a metric's meaning by editing a file, and
hard-coding a list in `metrics.py` would let it drift from the register. `AnalysisConfig` also
**rejects a negative weight** for the same reason: a negative weight is a sign flip wearing a
weight's clothes.

### Golden fixtures: all six reproduce, and `21122` is kept

`docs/07` §4.2's five stored-output fixtures reproduce to 3 dp, including `22222 → 1.315` and
`21012 → 1.027`. The sixth, `21122 → 1.245` from the 1.0 mock, also reproduces and is kept as a
fixture — it costs nothing and it is one more chance to notice a formula moving. The test is
parametrised so a failure names the code that moved.

### `MissingInteraction` rather than a bare `None`

`docs/07` §5's signature returns `Interaction | None`. Returning `None` alone satisfies I17's letter
but not its purpose: `CLAUDE.md` rule 5 requires that the missing **code be reported**, and a `None`
carries no code. `interaction()` therefore returns `Interaction | MissingInteraction`, where the
latter names `missing_codes` and `describe_missing()` renders the sentence the UI shows — ending in
"this is not estimated". Callers that only want computable ones use `computable_interactions()`, which
is what assembles the analyst bundle.

### `below_floor` and `demand_floor` return `None`, never `False` or `0.0`

"We did not measure the floor" and "this cell clears the floor" are different claims and only one of
them supports a finding. A missing control returns `None` so the fallback template says "the sham
floor has not been measured" rather than silently reporting a cell as interpretable.

### `analyse` is now seedable and wired for M7's injection point

`seed_db.py` named `analysis.default.yaml` as M8's but never loaded it, so the `analysis` key would
have been absent from `app_config` — and `docs/07` §4.1's "any non-default weight set is recorded on
the run" is unenforceable if the defaults live only in a file on disk. Now seeded as the `analysis`
key; `app_config` goes from 4 rows to 5.

**`SessionRunner` still receives `analyse` as an injected callable** (M7's design). M8 built the
pieces — `compute_shifts`, `compute_index`, `build_bundle`, `write_analysis` — but wiring them into
the runner needs a real answer store and the twins' own survey vectors, which is the service layer's
job. M8's acceptance criteria are all about the arithmetic and the grounding, and they are met
independently of that wiring.

### Mechanical picks

- **`average_within_twin` averages *scores*, not answers.** Averaging raw answers and then scoring is
  not the same thing once an item is reverse coded, and `docs/07` §3.2 says to average within twin
  first — so the collapse happens after scoring.
- **`mean_over_twins` takes `twin_ids` as a parameter, not `vectors.keys()`.** That is the whole
  mechanism of `docs/07` §3.1: the caller passes the *same* set to both sides of a shift.
  `CellShifts.twin_ids` then stores it, so the paired-sample rule is auditable after the fact rather
  than a property of the function that computed it.
- **`score()` raises on a missing item** rather than averaging a subset (`docs/07` §2.3).
- **`write_analysis` returns `(result, used_fallback)`.** The fallback rate is a reportable
  diagnostic (`docs/02` §6.2), and a caller should not have to string-match the prefix to record it.
- **`confidence: "none"` short-circuits the ladder.** It is a recorded outcome, not a failed one: a
  cell with no defensible reading gets no reading, and retrying it would be asking the model to
  invent one.

## M9 — Intake and the generator

*2026-09-29. All eight acceptance criteria green in `tests/test_m9_intake.py` (27 tests).
393 tests total.*

### FIXED — a Google Forms checkbox answers as a LIST, and consent read as false

`apps_script/sample_payload.json` sends consent statement 6 as `["I agree"]`, not `"I agree"`. The
first version of `_affirmative()` stringified the value and compared `"['i agree']"` against the
allow-list, so **every consent read as false, every submission became `no_consent`, and no twin would
ever have been built** — the whole study, silently, with no error anywhere to notice.

This is the single most valuable thing the committed fixture has done. It is also why
`apps_script/sample_payload.json` must not be "tidied": its awkward shapes are the real Form's shapes.
Both implementations now handle lists, and a test asserts consent is read from a list rather than a
string.

### AMBIGUITY — `eligible` is computed and recorded, but never used to exclude

The DDL has `eligible boolean not null` and `outcome text not null -- complete|screened_out|…`, which
together imply intake screens. `docs/GOOGLE_FORM.md` → "Three things the specification did not fix"
says the opposite, explicitly: *"Part 1 screeners … are mapped, so they are accepted, but no database
column exists for them and nothing infers from them. Only consent statement 7 gates whether a twin is
built. If you want eligibility to exclude a response, that is a research decision and I have not made
it."*

Resolved to honour both: `eligible` is **derived from the screeners and stored**, so the NOT NULL
column is filled with the real answer rather than a placeholder — and **`outcome` is never
`screened_out`**, so nothing is excluded. That value stays available for a screening rule the
researcher may later choose, and turning it on would then be a dated decision here rather than a
silent default. The committed fixture is conveniently ineligible (it answers "Yes" to all three
disqualifying screeners), so a test asserts it is recorded as `complete` anyway.

Consistent with the existing Post-M10 decision *"Part 15 / `MC1` screening: switch built, default
OFF"*.

### The contract test genuinely runs both implementations

`docs/11` M9 requires that the Edge Function and `ingest/survey_intake.py` produce identical rows from
the fixture. Deno is not installed here, so the row-building logic was factored into
**`supabase/functions/survey_intake/rows.mjs`** — dependency-free ESM with no Deno globals — which
`index.ts` imports unmodified and which `apps_script/contract_harness.mjs` runs under Node. The test
shells out to Node and compares every field of the submission row and all 73 answer rows. They match.

**What is therefore still unverified:** `index.ts`'s own HTTP, HMAC and Storage layer. It has never
been executed — no Deno, no Supabase project. The Python side's HMAC is tested against a hand-computed
`hmac.new(...).hexdigest()` and the TypeScript mirrors it via WebCrypto, but *mirrors* is the operative
word. **First live deploy should post the fixture with a known signature and confirm a 200, then post
it with a mangled signature and confirm a 401.** Recorded here because nothing in CI can catch it.

### Two generated assets, checked like the frozen reference data

Deno cannot read `config/form_map.yaml` at request time, so `tools/gen_edge_assets.py` emits
`form_map.json` (the map verbatim) and `register_spec.json` (the item register reduced to what
`rows.mjs` needs). **A hand-edited copy of the map is exactly the drift the one-contract rule exists to
prevent**, so `--check` re-derives both and fails on any difference, and it runs in CI beside
`build_reference.py --check`. `register_spec.json` is *reduced*, not copied: the Edge Function has no
business knowing item stems or constructs, and a smaller asset is a smaller thing to drift.

### The generator emits a Form-shaped payload and reuses `build_rows`

Rather than building rows directly. Three consequences, all wanted: the synthetic path cannot produce
a shape the real path could not; the generator answers **every** key in `form_map.yaml` by
construction, because it inverts the real map, so a missed question raises `UnmappedQuestion` from the
same guard that protects live intake; and a test asserts the payload's key set **equals** the map's.

Attention checks are answered **correctly** and the screeners eligibly, so a synthetic respondent is
quality-testable — a batch that failed its own attention checks could never produce a twin and the
generator would be useless for exercising the gate.

**Clamping is used in `_likert` and that is not a contradiction.** `docs/02` §5.3 bans clamping a
*model's* output, where it converts a detectable failure into an undetectable fabrication. Here there
is no respondent whose answer is being altered — the value is being generated.

### `delete_synthetic` deletes `twins` by `source` **and** by id

`twins` has no foreign key to `survey_submissions` — `twin_id` matches `submission_id` only by
convention — so the DDL cannot cascade to it and the deletion is explicit. Requiring **both**
conditions means a real twin that happened to share an id cannot be caught and a synthetic twin from
another batch cannot be missed. The function takes **no id list from a caller**: a delete that accepts
ids is a delete that can be given the wrong ones.

`survey_answers` cascades in Postgres but is deleted explicitly too, so the behaviour is identical
against the in-memory backend the whole suite runs on. A test asserts the run count is unchanged
rather than trusting that `runs` references no submission.

### Mechanical picks

- **`_as_int` returns `None` for a multi-select**, rather than taking the first option. A checkbox grid
  is never a Likert item, and collapsing two selections into one is the forbidden repair.
- **Attention-check expected values are parsed from each item's own stem**, not hard-coded, so
  re-wording the Form cannot leave the checker scoring against a number the driver was never asked.
- **`store_batch` writes raw objects before rows**, like live intake: a synthetic row with no
  replayable object is a different kind of record, and `replay_raw` would call it an orphan forever.
- **`replay_all` returns `{"replayed", "failed"}`** and never raises on one bad object. An object that
  cannot be replayed is a driver's submission missing from the data, so it is reported, not swallowed.
- **`orphaned_paths` compares on `raw_object_path`**, the column intake actually wrote, rather than on
  a re-parsed id — so an id-formatting difference cannot make an object look orphaned when it is not.

## M6 / M7 — Orchestrator and analyst

- **2026-09-22 — `analysis/metrics.py` written during M6.** The orchestrator's `analyse` stage
  cannot complete a run without it. M7 owns its acceptance test and added `interactions.py` and
  `report.py`.
- **2026-09-22 — shifts are a paired comparison.** `compute_metrics` means over the twins that
  answered *both* the baseline and the cell. A twin that failed for this cell is excluded from both
  sides rather than leaving a baseline mean drawn from a different sample.
- **2026-09-22 — `request_stop` on a session that has not started yet is honoured when it does.**
  The flag lives on the runner, created on demand. Simpler than a second "pending stop" state, and
  the semantics a researcher would expect from pressing Stop.
- **2026-09-22 — `invented_numbers()` ignores a digit glued to letters.** `agree5` and `extent7`
  are scale identifiers, not figures. The guard still catches any real number absent from the
  bundle.
- **2026-09-22 — the analysis prose is stored as JSON** on `runs.llm_analysis` (`summary`,
  `mechanism`, `caveats`, `confidence`). The column is text and the four fields are the specified
  `AnalysisResult`; storing them as one blob keeps the Results panel free to render them in order.

## M8 — UI

- **2026-09-22 — Gradio handlers are `async def`, not `asyncio.run` in a sync handler.** The dial
  board's "Ask the twins" and the quality page's Run buttons enqueue a task; `asyncio.run` closes
  its loop on return and takes the task with it. Gradio awaits async handlers on the app's own
  loop, so the enqueued session survives. `logs.py` and `dialboard.py` were converted with the
  rest. Guarded by `test_logs_handlers_are_async`.
- **2026-09-22 — `services/twins.start_quality_test` added beside `run_quality_test`.** The page
  needs a session id the instant the button is pressed, and CLAUDE.md rule 9 forbids the model
  call in the handler's path. `create_quality_session` makes the row; `start_quality_test`
  enqueues the body and returns. `run_quality_test` is unchanged for tests and the API.
- **2026-09-22 — each tab loads through a self-cancelling `gr.Timer`.** Gradio exposes `load` only
  on the `Blocks` object, which a tab module does not have. A 1.5 s timer fills the tab and
  returns `gr.Timer(active=False)`; per-session, so it re-fires for each new page load.
- **2026-09-22 — the results grid carries its row key in a legend, not a row column.** docs/04 §7.1
  fixes `code = f"{row//3}{row%3}{col//9}{(col//3)%3}{col%3}"` against the `.select()` index, so a
  label column would shift every column index by one. Column headers are the 27 three-digit codes
  and a caption above states the nine row codes in order: styling degraded, content and ordering
  intact (docs/04 §10).
- **2026-09-22 — cell tooltips are `Styler.set_tooltips`, wrapped in a try.** docs/04 §7.1 wants
  `version code · index` on hover. Some Gradio builds strip the title attributes; where they do,
  the tested-versions table below still carries version code and index, so no content is lost.
- **2026-09-22 — the interactions panel names levers with `told_bullets` headings**
  ("Pay step 1 and Conditions step 1"), not the friendlier gloss in the docs/04 §7.2 example.
  docs/04 §2 requires one source for what a cell is called; a second naming scheme is exactly the
  drift that rule exists to prevent. Sentence shape and every figure follow §7.2.
- **2026-09-22 — "Twin model" in Settings is the section heading over provider, model name and
  temperature,** not a sixth field. docs/04 §8 lists it first in a run of model fields and
  `TwinConfig.model` is one `ModelRef`; inventing a separate control would invent a setting.
- **2026-09-22 — the Settings data-source radio filters the twin count; it is not persisted.**
  `TwinConfig` has no such field and forbids extras. The control is rendered and live, and the
  pool it names is read straight from `twins.source`.
- **2026-09-22 — "Import twins from the survey" and "Clear runs and load demo twins" are rendered
  and state why they do nothing yet.** Import belongs to M9's intake route. Clearing runs would
  delete append-only evidence (I9), which is a database operation and not a button. Neither is
  dropped and neither fails silently (rule 6).
- **2026-09-22 — the twins list is scroll-capped rather than paginated.** docs/04 §10.4 allows
  either; twenty twins in a `tl-scroll` panel needs no pager.

## M9 — Intake and hardening

- **2026-09-22 — `twins.background` gains `own_words` and `translations`.** A defect, not a choice:
  `persona/builder.py` reads `SurveyResponse.own_words`, but nothing persisted Part 14 and
  `stage_reconstruction` never supplied it, so every rebuilt passage silently lost the driver's own
  words against docs/02 §5. `001_init.sql` already names `twins.background` as their home (no
  `item_id`, frozen register), so they go there, intake writes them, and reconstruction feeds them
  back. jsonb: no migration.
- **2026-09-22 — the intake payload's `answers` is a list of `{section, title, value}`,** and
  `form_map.yaml` is keyed `"<section>|<title>"`. Form question titles repeat: Part 16 re-asks
  Part 7's and Part 9's questions, and Part 17 asks the same three questions six times, so a
  title-only map cannot tell `SAT1` from `H2_SAT1` or `H3_V1_FAIR` from `H3_V2_FAIR`. The Form is
  out of scope (ARCHITECTURE §6.3), so this is the contract the Apps Script is written against.
  **The researcher should confirm it before the Form is built.**
- **2026-09-22 — `form_map.yaml` values carry a prefix** (`field:`, `background:`, `why:`,
  `own_words:`, `consent:`, `meta:`, `screen:`); a bare value is an `item_id`. Still two columns,
  and it keeps every Form question in one file instead of five.
- **2026-09-22 — Part 1 eligibility answers live in the `data/temp` mirror only.** They are mapped,
  so they are not "unmapped", and they are recorded — the mirror is the immutable record of the
  submission (ARCHITECTURE §6.3). No column exists for them, and gating on them would be a
  research decision the docs do not make: only consent statement 7 gates a twin.
- **2026-09-22 — `tenure_years` is converted to `tenure_months` at intake.** The Form asks in
  years; the twin row and the persona speak in months.
- **2026-09-22 — intake with no `INTAKE_HMAC_SECRET` returns 503, not 200.** An unsigned intake
  route would accept a submission from anyone. Refusing is the safe failure.
- **2026-09-22 — provider backoff is classified on the exception, not on an SDK type.**
  `is_transient()` reads `status_code`/`status` where a provider exposes one and matches the
  message otherwise, so 429/5xx/timeouts get three attempts with exponential backoff across every
  provider without importing any of them. A schema failure is *not* transient and keeps the
  agent's own `RetryPolicy`: a wrong prompt fails identically every time and must not be retried
  three times at cost.
- **2026-09-22 — `src/twinlab/telemetry.py` added.** Not in the §4 layout. `configure()` is a
  no-op without `LOGFIRE_TOKEN` and never raises: telemetry is an aid to the researcher, never a
  dependency of the science.
- **2026-09-22 — crash recovery runs from a FastAPI lifespan in `app.py`.** docs/03 §3.3 specifies
  it at startup and `resume_interrupted_sessions()` already existed; nothing was calling it.
  Failures there are logged and swallowed so a missing database cannot stop the UI booting.

## M10 — Invariant suite

- **2026-09-22 — `.github/workflows/ci.yml` added.** CLAUDE.md says the invariant suite runs in CI
  and no workflow existed. It checks the frozen reference bytes, runs `test_invariants.py` on its
  own so a failure there is unmistakable, then the full suite. `ruff` is advisory
  (`continue-on-error`) so a lint nit never masks an invariant failure.
- **2026-09-22 — `test_every_invariant_has_at_least_one_test` guards the suite itself.** It asserts
  each of I1–I11 has a test whose docstring opens with that invariant's tag, so a future invariant
  cannot be added to `ARCHITECTURE.md` §2 and left unguarded here.

## Post-M10 — researcher setup

- **2026-09-23 — `build_reference.py` resolves its four source documents from `additional_data/`
  first, then the repo root.** The sources were moved into `additional_data/` and the hard-coded
  root paths broke `--check`. Both locations are searched and a missing document names every place
  it looked. The regenerated JSON is byte-identical, so the move cost nothing.
- **2026-09-23 — Part 15's manipulation check is mapped as `check:manipulation`.** It is a real
  Form question and was the one question with no row, so a complete submission would have been
  rejected with 422. Like the attention checks it is a data-quality device about the *human's*
  reading, never twin input (I10), so it is recorded in the mirror with no column of its own —
  the same treatment as the Part 1 screeners, under its own prefix so the distinction stays honest.
- **2026-09-23 — an unreadable scale point is 422, not 500.** A Likert grid whose columns are
  labelled "Strongly agree" rather than `1`–`7` is a Form mistake the researcher fixes and
  replays, so the route names it instead of raising a server error. The mirror is already written.
- **2026-09-23 — `ingest/seed_demo_twins.py` added.** The first live smoke run needs a twin pool
  before the Form exists, and the only alternative was a one-line script in the setup doc. Writes
  `source = "synthetic"` with `DEMO` ids so a demo twin can never be mistaken for a driver or
  collide with a Form response id; `--clear` removes synthetic rows only and never touches `runs`.

---

# Revamp 2026-09 — v2.0

`ARCHITECTURE.md` 2.0 supersedes 1.0. The **research design is unchanged**. What changed is the
stack, the execution model, the UI surface and the deployment target, because four external facts
turned out not to be what 1.0 assumed.

Entries marked **RESEARCHER** were decided by the researcher on 2026-09-28, not by the coding
agent. They are recorded here so they are not silently reversed.

## Forced by external facts

- **2026-09-28 — `NativeOutput` is forbidden; validation moves into Python.** Ollama Cloud accepts
  `response_format` with `json_schema` without error and does **not** apply grammar-constrained
  decoding — schemas are silently unenforced. pydantic-ai raises `UserError` on `NativeOutput` for
  `ollama.com` URLs. This became invariant **I13**, a `build_agent` guard, and the DDL constraint
  `agent_no_native_output`. The whole of `docs/02` §5 exists because of it.
- **2026-09-28 — `max_concurrency` defaults to 1, not 4.** The free provider tier permits one
  concurrent request. The bounded pool stays so a paid plan changes a number rather than code, but
  **1 is the tested default**. Every time estimate in `docs/10` is serial as a result.
- **2026-09-28 — deployment targets a free ZeroGPU Gradio Space, with four binding portability
  rules.** Hugging Face now requires a paid plan to create Gradio *or* Docker Spaces; free personal
  accounts get 2 ZeroGPU Gradio Spaces. **RESEARCHER:** stay free now, keep Docker a one-commit
  upgrade. Hence `ARCHITECTURE.md` §8.2, two entrypoints from M0, and the ban on importing `spaces`.
- **2026-09-28 — Python 3.13. RESEARCHER.** The Spaces `python_version` key accepts any valid 3.x;
  the 3.12/3.10 list in the ZeroGPU docs governs its PyTorch runtime, which is unused here. Fall
  back to 3.12 only if a deploy shows ZeroGPU pins the image Python.
- **2026-09-28 — survey intake moves out of the Space into a Supabase Edge Function.** A Space
  sleeps after 48 h idle and would silently drop driver submissions. This also removed the only
  feature that genuinely required FastAPI routes, which is what makes the Gradio-SDK target viable.
- **2026-09-28 — nothing durable on the filesystem (I16).** Space disk is ephemeral and persistent
  storage has been withdrawn entirely. `data/temp/survey_<id>.json` becomes a Supabase Storage
  object written before any table write.
- **2026-09-28 — access control is `hf_oauth` with `hf_oauth_authorized_org`,** replacing the
  prototype's shared "Lab passcode".

## Research decisions

- **2026-09-28 — the frozen analysis panel (I14). RESEARCHER.** A sweep uses a stratified subsample
  of K quality-passed twins, drawn once per session and identical in every cell. **K=20 default,
  configurable.** Rejected: per-cell sampling, which was the prototype's `live_sample` behaviour and
  makes `shift(A∪B) − (shift(A)+shift(B))` uninterpretable because the legs would carry
  between-person variance. All 500 twins are still built, quality-tested and analysed in Statistics.
- **2026-09-28 — the item-level holdout is dropped; the persona stays lossless. RESEARCHER.** The
  prototype withheld 16 even-ordinal battery items from the persona and scored the `wrong_person`
  test on them. That conflicted with I6/I7's losslessness. The test **re-bases onto the H2 block**
  (Part 16, also 16 items) — the same thing the legacy `post_mae` column already scored — so nothing
  is lost. The Validation tab's "Part 9b" row is **removed, not renamed**.
- **2026-09-28 — full PLS-SEM in-app via `openpls-engine`. RESEARCHER.** GPL-3.0, which makes this
  application GPL-3.0; accepted knowingly for an academic instrument and recorded in
  `ARCHITECTURE.md` §3.1. Chosen over hand-rolling because a wrong bootstrap scheme invalidates a
  paper silently. It is validated against SmartPLS 4 across 14 reference models to |Δ| < 0.001, but
  that does not validate *our wiring* — hence the mandatory golden-dataset test in `docs/07` §10.
- **2026-09-28 — the Research Model diagram is theory; the nine constructs are its
  operationalisation. RESEARCHER.** They do not map one-to-one, so a **measurement mapping table**
  is mandatory on that page. Without it the Research Model page and the Statistics page appear to
  describe different studies. The instrument does not change.
- **2026-09-28 — the Analyst loses its ReAct loop and its history tools.** In 1.0 it could fetch run
  history, an unbounded surface through which an ungiven number can enter its prose. It now receives
  one assembled bundle, and its output is numerically grounded against that bundle (`docs/02` §6).

## Modelling corrections

- **2026-09-28 — `survey_responses(twin_id, …)` split into `survey_submissions` +
  `survey_answers`.** v1.0 keyed answers by `twin_id`, so a respondent who was ineligible, withheld
  consent, or failed an attention check had nowhere to live — yet the Fieldwork tab must count
  exactly those people, the Generator must delete synthetic rows without touching twins, and
  Statistics analyses respondents rather than twins. Respondent and twin are now separate entities.
- **2026-09-28 — the four human arms are documented for the first time** (`docs/01` §5). Decoded
  from Part 15's manipulation-check options matched against the `arm` column and the `Assignments`
  stratification in the prototype workbook: `BASE`→`00000`, `MGT1`→`00010`, `CON1`→`01000`,
  `REP1`→`00001`. Neither source states it. **Subsequently derived from the commitment texts and
  no longer an inference — see "Resolved 2026-09-28 (second pass)" below.** Two consequences are
  load-bearing: H2 validation must show a twin its *own driver's* arm, and `BASE` is the human noise
  floor mirroring the twin's `00000`.
- **2026-09-28 — nine constructs become first-class** (`constructs` table,
  `survey_items.construct_code`). Six metrics were not enough: the Statistics section reports on all
  nine. Note the new namespace collision — `FAIR` is now both an item block and a construct code,
  which it was not in the prototype (block was `PAF`). They stay in separate columns.
- **2026-09-28 — `legacy_crosswalk.json` and the `legacy_scale` flag.** The prototype collected
  `PAC`, `PAT`/`CLAR` and `LOY`/`CONT` on 1–7; canonically they are 1–5. Legacy values for those
  blocks are **not poolable** with new ones. The importer marks them and the analysis dataset
  excludes them by default. Silently pooling them would corrupt every reliability statistic.
- **2026-09-28 — anchor clauses are per scale.** Using the 7-point wording for a 5-point item would
  render a `4` as "I agree" in one block and "I neither agree nor disagree" in another, inside one
  passage.

## Defects inherited from the prototype, now structurally impossible

Each was found in the saved workbook and each is closed by a DDL constraint rather than a code path,
because a constraint cannot be forgotten by a caller.

- **2026-09-28 — a run with no twins is a failure, not a result (I15).** The `Designs` sheet
  contains rows with `twins = 0, index = 0.000` stored as findings. Closed by
  `runs_completed_has_twins`.
- **2026-09-28 — a validity test on zero twins is `INCONCLUSIVE`, never `PASS` (I15).** The
  `ValidityTests` sheet contains live-mode rows with `twins = 0` reading
  `PASS: twins are about their own driver`. Closed by `validity_zero_n`, plus a fourth verdict
  value.
- **2026-09-28 — scales are native, never flattened to 1–7.** The prototype's twin prompt said
  "1 to 7" for every item and its export claimed the same; three of the nine constructs are 5-point
  in the source instrument. Closed by `scales.points`, by the output contract, and by a seed
  assertion that every `anchors` array length equals its `points`.
- **2026-09-28 — `run_events.payload` capped at 8 KB (was 32 KB) and prompt bodies are never
  stored.** At panel scale, prompt bodies alone would exhaust the 500 MB tier. The round prompt is
  rebuilt from stored fields instead, and `rebuild_round_prompt()` has its own test.

## Deliberately kept from 1.0

- The eight frozen reference files are **not** regenerated. `build_reference.py --check` must still
  exit 0.
- `twins.background jsonb` still holds Part 3 extras, Part 4 **and Part 14 own-words**. Part 14 has
  no `item_id` and the 73-item register is frozen; without this the persona loses the driver's own
  words.
- SHAM still occupies `dial = 3` in `lever_paragraphs`, and its unfilled levers still announce that
  lever's existing driver-facing policy with containment scoped to it. **Researcher-approved.**
- Reading-grade band `[4.0, 16.0]` Flesch–Kincaid in `style_contract.yaml`.
- Gradio handlers are `async def`; never `asyncio.run` in a sync handler — the latter closes its
  loop and takes any enqueued session task with it.
- A cached lever paragraph is never re-rendered per cell (that would break I4).

## Degradations accepted

- **No drag-to-resize splitters, no floating windows, vertical-only CSS resize.** Horizontal
  proportions come from `gr.Column(scale=…)`. Content and ordering are unaffected.
- **Log polling, not websockets.** `gr.Timer` with `after_id`; never re-fetch the stream.
- **The 243-grid is a Plotly heatmap** with a styled `gr.Dataframe` fallback. The Tested versions
  table below it is the accessible equivalent, because 243 focusable cells is a keyboard trap.

## Resolved 2026-09-28 (second pass)

- **The four human arms are now DERIVED, not pending.** The mapping was recovered by matching Part
  15's four manipulation-check options against the commitment texts in `gaps.json`. Every
  non-control arm matches its lever's dial-1 set term for term: `CON1` ↔ `2.1.a`/`2.1.c` (safety
  equipment and training; accident and injury cover), `MGT1` ↔ `4.1.a`/`4.1.b`/`4.1.d` (human
  contact; extended appeals; disparagement removed as grounds), `REP1` ↔ `5.1.a`/`5.1.b` (open the
  voice mechanism; *"recognise and bargain with an independent body of drivers or a trade union"*).
  Part 16's story text is `5.1.a` + `5.1.b` rendered near-verbatim. `BASE` is `00000` trivially.
  **RESEARCHER delegated this decision to the agent**; it was resolved by evidence rather than
  judgement, which is why it is recorded here rather than left open. `docs/01` §5.1 carries the
  derivation, a seed assertion that every non-control arm is a single-lever dial-1 code, and a
  one-off manual verification to run once real data exists.
- **Quality-test the full population. RESEARCHER.** All consented twins go through the H3 gate at
  `quality_runs_per_twin = 3` — 9,000 calls, ~20 h at N=500. Degradation rung 7 (test a stratified
  pool instead) was considered and **declined**: it would change the calibration claim from
  *"k of N kept"* to *"84 of 100 tested kept, from which 20 were drawn"*, and that choice cannot be
  made after collection without becoming a researcher degree of freedom. The rung stays documented;
  taking it later requires a dated entry here and a disclosure in the paper.
- **The full 243-cell sweep is deferred; the design is built in full. RESEARCHER.** Rung 5 of the
  degradation ladder is the operating mode: the odometer, the grid, the panel, the controls and the
  ten single-lever cells are built and runnable, but no full sweep is scheduled. This costs coverage,
  not validity — the cells that do run are the same cells they would have been. Nothing in the
  design, the schema or the UI is simplified on account of it.
- **Part 15 / `MC1` screening: switch built, default OFF. RESEARCHER.** `mc_answer` and
  `mc_correct` are captured on every submission and the failure rate appears on Fieldwork.
  Turning it on **after** seeing results is a researcher degree of freedom; every analysis run
  records which screening rule produced it, so the choice stays visible.
- **2026-09-28 — the four superseded v1.0 documents and `HANDOFF.md` moved to `docs/_v1/`,** not
  deleted; this is not a git repository, so deletion would be permanent. `docs/_v1/README.md` lists
  what superseded what and enumerates the specific claims those files now get wrong — `HANDOFF.md`
  especially, because it states *"M0–M10 are complete, 212 tests pass"* against a build plan that no
  longer exists, which a fresh session would believe.

---

## M10 — UI shell and Twin Lab

*2026-09-29. Mechanical picks and one degradation, per `CLAUDE.md` → "When the spec is silent" and
"When Gradio cannot do it". Nothing here changes a research commitment.*

### The bug that shaped the milestone

- **A repeating `gr.Timer` must never paint an initial state.** The first build gave every tab a
  `gr.Timer(0.2)` to draw its first state, because `gr.Blocks.load` cannot be called from a page
  function — a page builds into the *enclosing* context and never sees the `Blocks`. The timers
  never stopped. On the Dial board the tick kept recomputing and its output landed on top of the
  change handler's, so **moving a dial did nothing**: the code stayed `00000` however the radios
  were set, with no error anywhere. Seven such timers also produced ~28 requests a second.
  This was found by running the app, not by the tests, which is worth recording: every assertion
  about the dial handler passed the whole time, because the handler was correct and its result was
  being overwritten downstream.
  **Fix:** `components.shell.load_once()` queues `(fn, inputs, outputs)` and
  `drain_pending_loads(demo)` attaches each to `demo.load` inside that route's context. Two
  repeating timers remain and both are specified: the Agents log poll (`docs/06` §3.1) and the Main
  menu's live counters (§1.3). `tests/test_m10_ui.py` asserts no other `gr.Timer` exists, by scan.

### Degradation accepted

- **The 243-grid ships as an HTML table of buttons, not a Plotly heatmap.** `docs/05` §8.3 names
  Plotly primary and `gr.Dataframe` as the fallback. Neither was taken, for an accessibility
  reason §6 makes binding: the grid must carry an accessible name per cell
  (`version 21122, index 1.245`) and both outlines must be stated in text, and neither a heatmap
  trace nor a Dataframe gradient can do that. A `<button>` per cell carries `aria-label`, `title`
  and a focus ring for free, and drops the Plotly dependency from a free-tier deployment.
  **Content and ordering are unchanged**; only the mechanism differs. `docs/05` §8.3's real
  requirement — *never ship a grid without click handling* — is met by a documented bridge:
  `gr.HTML` emits no events, so a delegated click writes the code into the version-code textbox
  through the native value setter plus an `input` event, which is what Gradio's binding listens
  for. Both halves are asserted in `test_the_grid_is_click_wired`.

### Mechanical picks

- **View models live in `models/view.py`** (`CLAUDE.md` rule 13). Every one carries its value
  *and* its rendering — `index_value = 0.143` beside `index_text = "0.143"` — so a Gradio handler
  never does arithmetic on a shift (`docs/05` §8.4 rule 5), and `None` always renders `Not tested`
  rather than a zero (I17).
- **`services/results.py` returns `ResultsPanel`, not HTML.** A service that returned markup would
  put a presentation decision below the layer boundary that exists to keep them apart. `ui/`
  renders it in `components.domain.results_panel_html`, in `docs/06` §3.7's seven-step order.
- **`what_twins_are_told` is defined once**, in `services/dials.py`, and re-exported by
  `services/lab.py`. `components.domain.what_twins_are_told` is a renderer over that output whose
  only parameter is the list it is given, so it cannot become a second source (`docs/05` §4.4).
- **Validation reads `twin_quality_runs.arm`, not a key in `detail`.** The DDL's `quality_h2_arm`
  makes that column non-null on every H2 row, so the *Arm seen* column (`docs/01` §5) reads the
  value the database guarantees rather than one a writer might omit. Found by the DDL refusing a
  test fixture — the constraint taught the service the right source.
- **`_KEPT_H3` filters on `kept` **and** `holdout_set = 'H3'`.** `quality_h3_gates` requires H2
  rows to carry `kept = null`, so "passed quality test" is an H3 count by construction.
- **"Real surveys" is computed as the complement of synthetic**, not as `data_type = 'REAL'`, so a
  third `data_type` introduced later cannot be silently counted as real.
- **Contrast overrides against Gradio's defaults.** Gradio styles bare `strong`, `span`, `div` and
  radio labels near-white on this light surface, which put card titles, legend text and the dial
  controls below `docs/05` §6's floors — the dial labels rendered grey-700 on `rgb(39,39,42)`.
  §6's minimums are testable requirements, not taste, so they are overridden in `theme.py` rather
  than accepted as a degradation. The dial traffic light (§7 rule 1) is applied by option position
  within each radio group, since the three steps are one group.

### Left for later milestones, deliberately

- The three workflow buttons confirm with a real budget and then **enqueue a stub**: the Agents
  tab does not yet start a quality run, a six-version selection or a full sweep. Wiring them needs
  `analyse` connected to `SessionRunner` and the twin/quality services, which `HANDOFF.md` §2.2
  records as service-layer work still open. The budget, the confirm step, the log tree, the status
  card and the cooperative-stop copy are all real.
- The eight validity **Run this test** buttons render per `docs/06` §3.5 but do not execute; the
  tests themselves are M13.
- *Import twins from the survey*, *Check twins against their drivers* and the quality page's
  *Run selection* / *Run all* are rendered and budgeted but not wired, for the same reason.

---

## M11 — Twin Studio and Agent Studio

*2026-09-29. `docs/06` §5 and §6. Mechanical picks only; no research commitment changed.*

### Where the quarantine actually lives

`docs/01` §6.9 says a studio run never enters `runs`, never contributes to a metric, a shift, an
index or the Results grid, and never reaches Statistics. That is enforced in three independent
places, none of which depends on a caller remembering:

- **`services/studio.run_studio` has no code path to the evidence tables.** A test parses the
  module's AST and fails on any `insert`/`upsert`/`update`/`delete`/`rpc` naming `runs`,
  `twin_answers`, `twin_quality_runs` or `validity_results`. A behavioural test alone would pass
  until someone actually used a newly added path.
- **A manual twin cannot be drawn into a panel.** `POPULATION_SOURCES` has no `manual` entry, so
  the test asserts `eligible_candidates` returns empty for *every* population including `both` —
  rather than only checking that the stored string says `manual`.
- **A custom change files `version_code = NULL`.** Free text bypasses the lookup (I1) and the
  Checker (I3), so it is not a Fairwork treatment. Filing it under one of the 243 would make it
  findable as a cell; it carries `SANDBOX_LABEL` instead.

Verified live as well as by test: after a studio run on a hand-built twin, the Main menu read
`Twins built 1`, `Versions tested 0 of 242`, `Twin answers saved 0`.

### Mechanical picks

- **A manual twin carries no persona passage.** A persona is a lossless reconstruction of a real
  driver's answers (I6) and there is no driver here. Writing one would make a fabricated passage
  indistinguishable from a reconstructed one, which is the failure mode the persona hash exists to
  prevent. The hand-built sliders are stored on `twins.background` instead.
- **`changed_fields` is computed by comparing before and after**, not taken from the caller. A
  history row recording what the UI *meant* to change rather than what changed would make the
  audit trail unfalsifiable.
- **`_refuse_if_frozen_and_running` checks `sessions.status = 'running'`**, so freezing alone does
  not lock an agent forever and an unfrozen agent stays editable during a sweep. Both directions
  have a test, because a gate that always refuses is as wrong as one that never does.
- **The *What was changed* log is newest-first.** A test initially asserted the opposite; the
  service was right and the test was corrected, not the code.
- **`manager_plan` is asserted twice**: behaviourally (sessions, runs, events and answers are all
  unchanged across the call, and `active_runners()` stays empty) and by source (its AST contains
  no `start_session`, `create_task`, `SessionRunner` or `ask_twins`).
- **Output modes come from `OUTPUT_MODES`, a two-entry tuple.** `native` is absent by construction
  at three levels — this list, the `AgentConfig` validator, and `build_agent` — because the
  provider accepts a JSON schema and silently does not enforce it (I13, `docs/02` §5.1).

### Styling: the Gradio dark-block override is now page-wide

Gradio fills `.block`, every radio/checkbox label and every text input with `rgb(39,39,42)`.
Against this light surface that puts grey-700 text on near-black and makes whole controls
unreadable — `docs/05` §6's contrast floors are testable minimums, not taste. M10 overrode it only
for `.tl-dial-row`; M11's screens hit the same wall immediately, so the override moved to
`.tl-page .block`, `.tl-page label`, `.tl-page textarea|input|select` and the table cells. A later
screen should not have to rediscover it.

### Main menu: an initial paint was missing

Found by running the app. `docs/06` §1.3 calls the counters live, so M10 gave them a 10 s
`gr.Timer` — but nothing painted them on load, so the table sat empty for ten seconds on every
visit, which reads as a broken page. It now has **both**: `load_once` for the first paint and the
timer for liveness. This is the one place a repeating timer is correct, because nothing in that
table is a control the researcher can be editing, which is what made the M10 dial-board timer
destructive.

### Left for later milestones, deliberately

- *Ask the twin* records a studio run and its scenario, but the **answer table is empty**: filling
  it needs a live twin call, which is the service-layer work M10's entry already records as open.
  The quarantine, the labels, the question cap and the storage are all real.
- Agent Studio's *Test this agent* is built for all five; the Twin Interviewer and Quality Checker
  views show the twin's stored answers rather than a fresh instruction comparison, for the same
  reason. Run Manager's plan is complete and is the one §6 singles out.

---

## M12 — Statistics and the golden dataset

*2026-09-29. `docs/06` §7, `docs/07` §7–§11, `docs/01` §6.8. **One research decision, taken by the
researcher.** Everything else is mechanical, or a defect flagged and worked around.*

### RESEARCHER — the structural path model. It was not in the specification.

**This is the one thing in M12 that could not be picked.** `docs/07` §7.2 names only that all nine
constructs are reflective, that `EDEP` is the moderator and that `arm` is the experimental
antecedent; §8.6 gives the chain as prose — "governance → algorithmic-management perceptions →
justice perceptions → behavioural intentions". **The edge list appears nowhere**: not in
`ARCHITECTURE.md` §10's open questions, not here, not in the frozen data. It decides every path
coefficient, R², f², Q², indirect effect and PLSpredict number in the paper, and the golden test
would have frozen whatever was chosen as "validated" — which is exactly the plausible-numbers
failure `docs/07` §10 exists to catch. So it was escalated, per `CLAUDE.md` → "When the spec is
silent" item 3.

**Decided by the researcher, 2026-09-29 — full mediation:**

```
arm          -> EXPO, CTRL            (3 dummies, BASE the reference; Mode B)
EXPO, CTRL   -> FAIR, TRAN
FAIR, TRAN   -> SATI
SATI         -> LOYA, VOIC, EXIT
EDEP         -> LOYA, VOIC, EXIT      (main effect)
EDEP x SATI  -> LOYA, VOIC, EXIT      (moderation, product indicators)
```

Seventeen edges. Justice perceptions reach the behavioural intentions **only** through
satisfaction, so under this model every arm effect on an intention is entirely indirect — which is
where §8.6 says the theory lives.

**AMBIGUITY, resolved by a second question rather than by picking.** The first answer paired this
edge list with "EDEP moderates justice → intentions", i.e. `EDEP x FAIR` and `EDEP x TRAN` on the
paths into the intentions. Under full mediation **those paths do not exist** — the only path into
an intention is `SATI →`. Adding them would have silently converted the chosen model into the
partial-mediation alternative the researcher had just declined. Both readings were put back, and
the researcher chose `EDEP x SATI → intentions`, which keeps the edge list exactly as decided.

`arm` enters as one **formative** (Mode B) block of three dummies with `BASE` omitted as the
reference — the conventional treatment of a categorical antecedent, and the omission is what makes
`BASE` the reference. A fourth dummy would make the block singular. `docs/07` §7.2's "all nine are
reflective" is unaffected: `ARM` is not one of the nine.

**Consequence:** `ModelSpec.fingerprint()` is recorded on every analysis run and pinned by the
golden test. Changing an item's construct, adding a path or changing the arm reference moves it,
and an analysis produced under a different model can never be mistaken for a comparable one.

### The bootstrap is `LongBootstrap`, not `Plspm(bootstrap=True)`

`docs/07` §9 requires `seed` to be stored and a resumed run to be identical to an uninterrupted
one. **The obvious API cannot honour either.** `openpls.bootstrap.Bootstrap` — what
`Plspm(bootstrap=True)` builds — draws its resamples with an unseeded `np.random.randint` across a
multiprocessing pool. `openpls.long_bootstrap.LongBootstrap` takes a `seed`, runs serially,
reports progress and exposes its failure ratio, so it is the only variant that can satisfy §9.

Measured at N=120: ~0.3 s per iteration, so the specified default of 5,000 is ~25 minutes. That is
consistent with §9's "long bootstraps are staged and resumable", and is why each stage persists
individually.

### The engine's import name is `openpls`

The distribution is `openpls-engine` (1.11.0 installed); the module is `openpls`. Neither
`openpls_engine` nor `plspm` resolves. `engine_version()` records the **distribution** version,
because that is what the paper must cite.

### `rho_A` comes from the consistent-PLS estimator

`reliability()` gives Cronbach's alpha and `dillon_goldstein_rho` (composite reliability, §8.1's
`rho_c`); AVE comes from `inner_summary()`. **`rho_A` is on none of those** — it lives on
`plsc().rho_a()`, which is where Dijkstra–Henseler reliability is computed. All four are read from
the engine; none is reimplemented.

### The golden dataset uses a PRNG defined in this repository

`stats/golden.py` generates its 120 respondents with a 64-bit LCG written in that file, not with
`numpy` or `random`. A reference dataset whose values depend on a library's stream is one a
dependency upgrade can silently move, and the failure would surface as forty drifting statistics
rather than as one changed input. `GOLDEN_DIGEST` pins the matrix itself and is asserted **before**
any statistic, so a changed fixture reports itself as a changed fixture.

345 statistics are pinned to |Δ| < 0.001. Regenerate with `tools/gen_golden.py --write` — and read
the diff, because a change there is a change to a number in the paper.

The golden run uses **30** bootstrap samples: deliberately the hard floor, which keeps CI to about
a minute and exercises the floor itself. No number from that run is ever presented as a finding.

### The two wiring faults are injected as *data*, not as flags

`docs/07` §10 requires the golden test to catch a reverse-coded item left unreversed. Reverse
coding is **unconditional** in `dataset.build_matrix`, so there is no production code path that can
skip it — a parameter that switched it off would be a parameter someone could set. The fault is
therefore injected by inverting the fixture's answers (`golden.unreversed_answers`). Measured
effect: `SATI`'s alpha falls 0.904 → 0.0 and `EDEP`'s 0.668 → 0.0, while the five constructs
carrying no reverse-coded item are **unchanged** — so the detector localises rather than merely
fires.

### Mechanical picks

- **Screening defaults differ between the analysis matrix (`strict`) and the export (`none`)**, on
  purpose. The export is the evidence file a reviewer recomputes the screen from, so it carries
  every respondent plus a `screened_out` column saying what a strict screen would have done.
- **A respondent missing any indicator is dropped whole, never imputed** (I17), and the count is
  reported, so a systematically missing block shows up as a screening figure rather than as a quiet
  sample shrink.
- **A constant column raises at matrix-build time.** The engine standardises, so a zero-variance
  indicator would otherwise reach the outer model as `NaN` — a plausible-looking table with a
  silently unidentified construct.
- **Interaction products are built from standardised components.** A product of raw values encodes
  where each scale's origin happens to sit.
- **PLSpredict is assessed on endogenous indicators only**; the model does not predict an exogenous
  construct, so its indicators say nothing about predictive power.
- **Reliability, AVE and discriminant validity read `na` for the formative blocks** (`ARM`, the
  interaction term), with the reason, never as a failure. Reliability is a claim about
  interchangeable reflective indicators.
- `d_G` and NFI are reported only where the engine provides them (§8.9 says "where the engine
  provides it"); this build does not, so they render absent rather than zero.

### Defects found and fixed in existing code

Three, all the same shape: **a gate that could not fail**.

1. **`tests/test_m0_scaffold.py::executable_source` re-joined tokens with newlines**, which splits
   every multi-token construct — `@spaces.GPU` became four lines. The scans for `@spaces.GPU` and
   `google sheet` therefore **could never match**, so one of the four *binding* portability rules
   (`ARCHITECTURE.md` §8.2 rule 4) was silently always green. Made line-based; verified by
   injecting `@spaces.GPU` into a `ui/` module and confirming the test now fails.
2. **`tests/test_m10_ui.py`'s repeating-timer scan read raw source**, so any module that
   *documents* the prohibition tripped it. This is the failure `HANDOFF.md` §0.5 already records
   for `@spaces.GPU` and "Google Sheet". Switched to `_executable_source`; verified it still
   rejects a real `gr.Timer(0.2)`.
3. **`tests/conftest.py`'s live-database ban did not hold at every fixture scope.** The guarantee —
   "no test can reach Supabase even if the environment happens to carry credentials" — rested on a
   **function-scoped** autouse fixture, so a `module`- or `session`-scoped fixture ran first and
   got whatever `get_backend()` built. M12's integration fixture **reached the researcher's real
   Supabase project** and failed on `PGRST205`. The ban is now enforced at the factory
   (`_no_live_database`, session-scoped), so no fixture at any scope can construct a
   `SupabaseBackend`, and `test_no_test_can_construct_a_live_backend` proves it rejects an attempt.

### Specification defects flagged, not silently fixed

| Where | The problem | What was done |
|---|---|---|
| `docs/07` §7.2 / §8.6 | **The structural edge list is not specified anywhere.** §7.2 names the antecedent, the moderator and "all nine reflective"; §8.6 gives the chain as prose. Neither yields an edge list, and `ARCHITECTURE.md` §10 does not carry it as an open question with a default. | Escalated, not picked. Researcher decided (above). The decision and its fingerprint are recorded on every run. **Outstanding: `docs/07` §7.2 needs the edge list written into it.** |
| `docs/07` §8.1 | Specifies `rho_A`, but the engine's `reliability()` does not return it | Read from `plsc().rho_a()`. No formula reimplemented. §8.1 could name where it comes from. |
| `docs/07` §8.2 | Requires HTMT "with bootstrap confidence intervals"; `LongBootstrap` produces path, loading, weight and effect intervals, **not HTMT** | HTMT is reported with its point estimate and judged against §8.2's 0.90 band. `HtmtRow` carries `ci_lower`/`ci_upper`, and when an interval is supplied the CI's upper bound decides the status exactly as §8.2 requires. **Open:** a seeded HTMT bootstrap is a second full resample loop (~25 minutes at 5,000), and whether that cost is worth paying is a researcher call. |
| `docs/07` §11 | Lists `female` and `tenure_months` per respondent; neither is on `survey_submissions` — both live on `twins` | The export joins `twins` on `submission_id` and writes an **empty cell**, never a zero, when a submission never became a twin. |
| `docs/11` M12 | "A staged run resumes without recomputing a completed stage" is listed as an acceptance criterion but names no stage granularity | Implemented at `analysis_results.stage` granularity, which is what `docs/01` §6.8 specifies. Both the stubbed and the real-stack forms are tested. |

### Found while writing the M12 handoff — a flag that contradicts the specification

**`services/lab.py::VALIDITY_TESTS` marks Test 1 `needs_live_model=True`.** `docs/08` §4's cost
table gives Test 1 "New LLM calls: **none**", and §4's Test 1 section says outright: "It needs **no
new model calls** — it re-scores stored vectors — so it should be run early and often." Test 3,
which is the other zero-call test, is correctly `False`.

The flag drives an amber *needs a live AI model* badge in `ui/pages/lab.py`, so the screen currently
tells the researcher the opposite of the specification's own advice about **the single most
important of the eight tests** — the one §4 says "distinguishes 'a twin' from 'a plausible
gig-driver chatbot'".

**Not fixed here, because it belongs to M13**, whose acceptance criterion is "tests 1 and 3 make
**zero** LLM calls — assert on the call counter". Flipping the flag without the counter assertion
behind it would just move the unverified claim. Recorded in `HANDOFF.md` §0.8 and §2.5 so the M13
session flips it and proves it in the same change.

---

## M13 — The eight validity tests

*2026-09-29.* `docs/08` §4 is the specification; `docs/11` M13 is the acceptance list. New code:
`models/validity.py`, `validity/tests.py`, `services/validity.py`, and the Validity tests tab's
confirm step and eight buttons in `ui/pages/lab.py`.

### The flag that contradicted the specification — now fixed

`services/lab.py::VALIDITY_TESTS` marked **Test 1 `needs_live_model=True`**, which the M12 handoff
flagged and deliberately left for this milestone. `docs/08` §4 gives Test 1 "New LLM calls: none"
and says it "needs **no new model calls** — it re-scores stored vectors — so it should be run early
and often". The flag drove an amber *needs a live AI model* badge, so the screen told the researcher
the opposite of the truth about the single most important of the eight.

Flipped to `False`, **and** backed by the counter assertion `docs/11` M13 asks for:
`test_tests_1_and_3_make_zero_model_calls` runs both tests with a `StubModelClient` in hand and
asserts `client.calls == []`. A bookkeeping test also asserts the badge and `CALLS_PER_TWIN` agree
for **all eight**, so the two cannot drift apart again.

Two card descriptions were also wrong and were corrected:

* **Test 3** read "compares twin predictions with a regression and a nearest-neighbour baseline".
  `docs/08` §4 test 3's two naive predictors are **no change** and **group average shift**. The card
  described a different test.
* **Test 7** read "compares the index ranking". §4 test 7 compares the per-twin index correlation
  **and every metric's sign**, and says the sign flip is the failure that matters.

### Decisions taken (mechanical, per `CLAUDE.md` "when the spec is silent")

1. **Where a twin's H2 answer vector lives.** `docs/01` §6 gives `twin_quality_runs` a `detail`
   jsonb and no column for the vector, and test 1 is its only reader. Filed under
   `detail["answers"]`, named once as `services/validity.H2_ANSWERS_KEY` rather than spelled in two
   places. **This is a read the quality gate must satisfy when it is wired**: until an H2 row
   carries a vector, tests 1 and 3 record `INCONCLUSIVE` — correctly, since there is nothing to
   re-score.
2. **The paired interval is Student's `t`, not the normal approximation.** A panel of twenty twins
   is df 19, where 1.96 is about 6% too narrow — the direction that manufactures a `PASS`. A small
   table, rounding *down* to the nearest tabulated df so an untabulated one never narrows.
3. **A spread indistinguishable from zero is zero.** Three identical gaps have an SD of 1.1e-16, not
   0.0, which produced a degenerate interval of width ~0 that "excludes zero" — a `PASS` resting on
   no variance at all. `_NO_SPREAD = 1e-9`; the interval is then `None`, which
   `PairedGap.excludes_zero` reads as *not* evidence. This is the same stance `pearson_r` already
   takes for a variance-free series (`docs/08` §3.3).
4. **"A different, randomly paired driver" is a seeded rotation.** Random in the offset, exactly
   reproducible from the session's own `panel_seed`, and **structurally a derangement** — a shuffle
   can pair a twin with itself, which would silently turn the test's "other driver" error into its
   "own driver" error and report a real gap as a `FAIL`.
5. **"Materially" in tests 4 and 6 means the `00000` noise floor.** `docs/08` §4 leaves the word
   undefined for test 4 ("happiness does not rise materially", "a clear improvement") and test 6
   ("materially different"). `docs/07` §6 already defines how much movement means nothing, so the
   floor is used rather than a second, unvalidated threshold. **When a session has no completed
   `00000`, tests 2, 4, 5, 6 and 8 are `INCONCLUSIVE`** — a floor that was never measured is not
   assumed, and a cell reported against an assumed floor is reported against nothing.
6. **Test 2 reads the stored `SHAM` control before asking for fresh calls.** `SHAM` is one of the
   two control cells every fresh session runs before its sweep (`docs/03` §6.1), so the vectors are
   normally already there, produced by the same twins, stimulus and model. This is the
   orchestrator's own cache, not a shortcut. `docs/08` §4's table still prices the test at `N` for
   the case where the control has not run.
7. **An `asyncio` task for the six costly tests, inline for the two free ones.** `CLAUDE.md` rule
   12: no LLM call in a Gradio handler's synchronous path. Tests 1 and 3 have no such call by
   construction, so they run inline and the table refreshes immediately — which is the behaviour
   `docs/08` §4 asks for when it says to run test 1 early and often.

### The two quarantines, enforced at the write

`docs/11` M13 requires test 4's probe never to reach `variants` and test 6's ablated persona never
to be hashed into `twins`. Both guards live in `models/validity.py` — **because `db/` may import
`models/` and nothing else** (`ARCHITECTURE.md` §4), and a guard that cannot be called from the
repository is a guard in a handler, which is exactly what the Studio quarantine taught us not to
rely on.

* `assert_not_a_probe` is called **inside `VariantRepo.put`**. `ProbeStimulus` additionally has **no
  `version_code` field at all**: every path that files a stimulus is keyed on one, so a shape that
  cannot carry a version code cannot be filed, reached from the Dial board, or cached as a run.
* `assert_not_ablated` is called **inside both functions that insert a `twins` row**.
  `AblatedPersona` is deliberately **not** a `PersonaPassage` and carries **no `persona_hash`** —
  there is nothing on it that `twins.persona_hash` could be set from.

Both guards were verified by injecting the violation and watching the refusal, and both were
verified to still accept an ordinary variant and an ordinary passage — a guard that refuses
everything is as useless as one that refuses nothing.

### AMBIGUITY — test 8's recommendation rule, and what was done about it

`docs/02` §7.3 and `docs/08` §4 test 8 both say the twin temperature is **set from test 8** and must
not be picked. Neither states the rule. §4 test 8 states the two considerations in prose — lower is
preferred, but *"a twin at 0.0 may collapse to modal answers and lose the between-twin variance the
design depends on"* — and nothing more.

Implemented as exactly those two considerations with **no free parameter**: the recommendation is
**the lowest temperature whose between-twin index SD is still above zero**. Any tuned cut-off (say
"within 90% of the best spread") would be a threshold nobody validated, frozen into the study by a
coding session.

Two consequences, both deliberate:

* When every temperature collapses, **nothing is recommended** (`recommended = None`). Not a
  default, not 0.7.
* The value is written to `app_config` under its **own key**, `twin_temperature_recommendation`,
  and **`TwinConfig.temperature` is not touched**. `docs/09` §4 freezes the temperature onto every
  session's config, so a test that changed it would retroactively make two sessions incomparable
  with nothing in the data saying why. Applying it is the researcher's deliberate act.
  **This is a rule the researcher should confirm or replace.**

### Specification defects flagged, not silently fixed

| Where | The problem | What was done |
|---|---|---|
| `docs/08` §4 test 4 | "happiness does not rise **materially**" and "treat it as **a clear improvement**" are both undefined | Judged against the `00000` noise floor (`docs/07` §6); no second threshold invented. §4 could name the floor explicitly. |
| `docs/08` §4 test 6 | "**materially** different" is undefined, and the block gives **no `FAIL` verdict** — only `pass` and `check` | The floor again; and the implementation has no `FAIL` path for test 6, matching the specification as written. A test that cannot fail is unusual and §4 may want to say whether that is intended. |
| `docs/08` §4 test 8 | Gives a `pass` rule and "report: always" but **no `FAIL`** | A spread above the floor is `CHECK`: information about sampling variance, not a verdict that the study is invalid. |
| `docs/08` §4 test 8 | Says the test **sets** the temperature but states no rule for choosing one | See the AMBIGUITY above. Escalated in this file rather than picked silently. |
| `docs/01` §6 | `twin_quality_runs` has no column for the twin's H2 answer vector, which test 1 must re-score | Filed under `detail["answers"]`, named once. §6 could add the key to the `detail` contract. |
| `docs/08` §6.2 | Requires the synthetic-data warning on **Validation, Validity tests and the Generator**; the Validity tests tab did not carry it | Added to the Validity tests tab, reusing `services/lab.SYNTHETIC_WARNING` so there is one copy of the sentence. |

---

## M14 — Research model, invariants, deploy

*2026-09-29.* `docs/06` §8 is the specification; `docs/11` M14 is the acceptance list. New code:
`models/research.py`, `services/research.py`, `config/research_model.yaml`, and
`ui/pages/research_model.py` — which was an M0 stub until now.

### The split that makes this page trustworthy

`docs/06` §8 says the page is "rendered from structured data rather than hardcoded prose". That
splits every field on it in two, and the split is the whole design:

* **What the codebase owns is generated from it.** The nine constructs, their item blocks,
  indicator counts, scales and index signs are read from the frozen register. The diagram is
  built from `stats/spec.py::STRUCTURAL_EDGES` — *the same object the estimator uses* — and the
  page prints `ModelSpec.fingerprint()` (`7c7fd73a12a4ec48`) beside it. The indicator counts come
  from `stats/spec.construct_items`, which is the function `build_model_spec` itself calls, so the
  measurement mapping cannot claim a construct is fielded by items the model does not give it.
  **That is the drift `docs/06` §8.4 exists to prevent**, and generating both from one source is
  what makes it impossible rather than merely unlikely.
* **What only a researcher can write is supplied**, in `config/research_model.yaml`, and **ships
  empty**. `docs/06` §8.9 forbids fabricating a reference; the same rule is applied to research
  question wording, hypotheses, construct definitions, source citations, the method narrative and
  the paper-section column. Each renders an explicit *Not supplied yet* rather than a blank cell
  that reads as "nothing to say".

The three research-question **ids and titles** are seeded, because `docs/06` §8.2 names all three
itself — RQ1 governance configurations, RQ2 conditional responses under dependence, RQ3 validated
simulation as an instrument. Their wording is not.

### Decisions taken (mechanical)

1. **The validation mapping's row SET is generated, not configured.** It is built from the
   application's own objects — the two holdouts, the two control cells, the reference arm and
   `VALIDITY_TESTS` — so a technique cannot appear that the app does not run, and one it runs
   cannot be missing. Only `assesses` (from `docs/08` §6.3) and `paper_section` are in the YAML.
2. **The method's nine parts and their order are in code**, `METHOD_PARTS`; only the prose is in
   the YAML. `docs/06` §0 makes content and ordering mandatory, and an order a config file could
   reorder is not mandatory.
3. **Each method row carries a generated *In this build* fact** beside the researcher's prose —
   counts, codes and versions the codebase owns. The row is therefore never wholly blank, and the
   prose can be checked against the instrument it describes rather than drifting from it.
4. **The diagram degrades to a layered board plus a full edge table.** Gradio cannot draw a path
   diagram. `CLAUDE.md`: degrade the styling, never the content — the edge list *is* the content,
   including the moderation and main-effect paths a drawing would have to letter separately, and it
   is always present. Recorded here as the degradation `CLAUDE.md` asks to be recorded.
5. **`ONE_LINE` is the only sentence of research prose in the layer**, and it is a restatement of
   `docs/07` §7.2's chain rather than a claim: every noun in it is a construct the register
   defines and every arrow is an edge the estimator uses.
6. **The document export is a string; only the handler touches the filesystem.**
   `research_document()` returns Markdown, and `ui/` writes it to a `tempfile` handle purely
   because `gr.File` needs a path — the same mechanism M12's statistics export uses. Nothing
   durable is written (I16), and a test asserts `services/research.py` contains no `write_text`,
   `write_bytes` or `mkdir`.
7. **An unsupplied field exports as an explicit gap, never dropped.** A document that omitted its
   empty sections would read as complete, and the researcher would have no list of what is left to
   write.

### Found by running the page, not by the tests

Two defects the green suite did not catch — the pattern that has now held for M10, M11, M13 and
M14:

* **`card.name.lower()` turned "A second AI model" into "a second ai model"** in the validation
  mapping. Fixed to use the card's own name.
* **The diagram's role label used `tl-prov`**, which is blue and underlined, so a plain label read
  as a link (`docs/05` §6). Changed to `tl-muted`.

### What M14 could not do, and why

Two of `docs/11` M14's six criteria are about **deployment**, and the researcher struck that on
2026-09-28 (`HANDOFF.md` §0.6, and "M1 deployment gate" above): ZeroGPU runs Python 3.10, force-
installs Gradio 6, and refuses to boot without `@spaces.GPU`, so it cannot host this application.
Hosting is deferred to PRO + Docker, which is a commit, not a rewrite.

The parts of those criteria that do not need a live host **are** tested:

* the boot-time `reference_hash` assertion, which refuses to start against a database seeded from
  different reference data;
* `resume_interrupted_sessions`, which marks a session found `running` at boot as `paused` and
  **never auto-restarts** it;
* the Space card's `hf_oauth: true` and `hf_oauth_authorized_org` organisation gate.

What is **not** tested, and is not claimed: that a Space boots, that OAuth actually admits only the
named organisation, and that a resume survives a real restart on a real host. Those need a
deployment, and asserting them green here would be asserting something nobody has observed.

### Specification defects flagged, not silently fixed

| Where | The problem | What was done |
|---|---|---|
| `docs/06` §8.2 | Requires three research-question cards with "id, title, question, hypothesis references and contribution". **The ids and titles are in §8; the questions, hypothesis references and contributions are specified nowhere in the repository.** | Ids and titles seeded from §8; the rest ships empty and renders *Not supplied yet*. Nothing is invented. |
| `docs/06` §8.5 | Requires a `Hypothesis ID · Statement · Support` table. **No hypothesis is stated anywhere in the repository** — not in `docs/00`, not in `additional_data/`. | Ships as an empty list with an empty state naming where they go and against which frozen model they must be written. **The researcher owes this content.** |
| `docs/06` §8.7 | `Where it comes from` is a citation column, and no construct citations exist in the repository | Ships empty, under §8.9's never-fabricate rule. |
| `docs/06` §8.8 | Requires a **`Paper section`** column; no paper outline exists in the repository | Ships empty per row. The other three columns are generated. |
| `docs/06` §8.3 vs `docs/07` §7.2 | §8.3 describes the diagram as "antecedent → algorithmic-management perceptions → justice perceptions → behavioural intentions", which **omits satisfaction** — yet the frozen structural model routes every intention through `SATI` (full mediation, decided 2026-09-29) | The diagram is generated from `STRUCTURAL_EDGES`, so it shows the model that is actually estimated, satisfaction included. §8.3's prose needs satisfaction added to the chain. |
| `docs/11` M14 | "The Space deploys, boots, asserts `reference_hash`, and resumes an interrupted session" and "`hf_oauth` restricts access to the named organisation" | Superseded by the researcher's 2026-09-28 decision to run locally. The host-independent parts are tested; the rest is reported, not faked. |

---

## Post-M14 — full-system audit, 2026-09-30

A whole-codebase audit of imports, wiring, boundaries, rate limits, logic and the UI. Everything
below was found **at a seam that no test covers**, because every test runs against
`InMemoryBackend` with injected stubs: the deterministic core is well guarded, and the gaps are all
in UI → service → orchestrator → provider → Postgres.

### Fixed

- **2026-09-30 — `gaps.criterion_id` is projected out of the seeded row, not added to the DDL.**
  `gaps.json` and the `Gap` model carry both `gap_id` and `criterion_id`, and all 30 rows have them
  equal; `001_init.sql` stores the relation structurally as
  `gap_id text primary key references criteria(criterion_id)` and declares no `criterion_id`
  column. Seeding a real project therefore died on `PGRST204` while the suite stayed green.
  Projecting is preferred to adding the column because the same fact would then live in two places
  and could drift. `_gap_rows` **asserts** the identity and raises `SeedError` on a difference, so
  the redundancy is proved rather than assumed. The general guard is
  `test_every_seeded_column_exists_in_the_migrations`, which compares every seeded key against the
  migrations as text — the class of bug, not the instance.
- **2026-09-30 — CI's `PYTHONPATH` is `src:.`, not `src`.** `python src/twinlab/ingest/seed_db.py`
  puts the *script's* directory on `sys.path`, not the working directory, so `config.settings` was
  unimportable and the *reference data seeds and asserts* step could never have passed.
  `HANDOFF.md` §0.0 already documented the requirement; the workflow had not been updated.
- **2026-09-30 — `VariantRepo.put` mints `variant_id` once.** It was an upsert carrying a fresh
  uuid in every payload, and PostgREST resolves a conflict with `DO UPDATE SET` over every column
  supplied — so re-storing a variant rewrote a primary key `runs.variant_id` already referenced.
  The orchestrator stores on every run of a code, so a resume, a rerun or a second iteration would
  have hit the foreign key. `InMemoryBackend` has none, which is why nothing caught it.
- **2026-09-30 — transient provider failures are retried, with backoff, in `PydanticAIClient`.**
  There was no 429/5xx handling anywhere: a rate-limited call raised out of the twin call,
  `ask_panel` logged it and moved on, and `execute_run` — which fails a cell only when *no* twin
  answered — **completed** the cell with one twin fewer than its neighbours. On the free tier's
  single slot, over 4,860 serial calls, provider pressure silently produced cells answered by
  different subsets of the frozen panel, recorded as results. That is what I14 forbids.
  `is_transient()` classifies on the exception, not on an SDK type, per the 2026-09-22 decision;
  `TRANSPORT_ATTEMPTS = 3` is a **separate budget from `RetryPolicy.attempts`**, which is the
  schema-repair ladder — a wrong prompt fails identically every time and must not be re-paid for.
  `RetryPolicy.backoff`, declared on all five agents and read by nothing, now shapes the wait.
- **2026-09-30 — `settings.delay_seconds` is applied before every model call.** The Settings tab
  offered it as *Pause between AI calls — raise it if calls start being refused*, and nothing read
  it, so the remedy the UI recommended did nothing.
- **2026-09-30 — a stop mid-panel leaves the cell `pending`, not `completed`.** `ask_panel` broke
  out of the loop on the stop flag and `execute_run` completed the run with whatever had answered;
  because `execute_run` skips a `completed` run on resume, a stop permanently baked a short-panel
  cell in as the latest result for that version code. `ask_panel` now returns
  `(answered, interrupted)`, and `run()` checks the flag **after** `execute_run` as well as before
  it — on the last iteration the session was otherwise marked `completed` with a `pending` run
  inside it. Resume finishes the panel and pays only for the twins that are left.
  `test_stop_is_cooperative_...` asserted `== "completed"`, which encoded the defect; it now
  asserts `== "pending"` and a companion test proves resume asks the remaining three and re-asks
  nobody.
- **2026-09-30 — `events_since` reads `ts`, not `created_at`.** `run_events` has no `created_at`
  column — `InMemoryBackend.HAS_CREATED_AT` excludes the table for that reason — so `EventRow.when`
  was `""` for every row and the log tree rendered a blank timestamp on every line.
- **2026-09-30 — `events_since` fetches only the missing ancestors.** Its parent map was built with
  an unfiltered `select` over the session's events, so the one function whose stated contract is
  *"the stream is never re-fetched whole"* re-read the entire history every three seconds. It now
  walks up one generation at a time, bounded by tree depth rather than stream length.
- **2026-09-30 — `save_settings` merges rather than replaces.** `app_config` rows are whole
  configurations and an upsert on `key` replaces the whole `value`, so a caller sending a partial
  dict silently deleted every setting it did not mention. The Settings tab was doing exactly that
  with `{"saved_from": "settings tab"}`, destroying the seeded quality-gate thresholds and
  reporting success with a fresh version number.
- **2026-09-30 — the Settings tab shows the values actually in force and validates what it
  writes.** Every control was a hard-coded literal bound to nothing. The five `TwinConfig` fields
  are editable and validated through `TwinConfig` before the write; the environment-owned values
  are shown read-only, because a Gradio control cannot change an environment variable and a
  control that looks editable and is not is the same lie in a smaller font.
- **2026-09-30 — `resume_interrupted_sessions` is called at startup again.** The v1.0 FastAPI
  lifespan that called it did not survive the 2026-09-28 rebuild, so a session killed by a restart
  stayed `running` forever — `active_runners()` is empty after a restart, so Stop returns `False`
  and the session could be neither resumed nor stopped from the UI. Failures are logged and
  swallowed: crash recovery must not stop the UI booting. **Nothing auto-restarts**, unchanged.
- **2026-09-30 — background session tasks are held and their exceptions logged.** `create_task`
  keeps only a weak reference, and an exception escaping `start_session` — `SessionAlreadyRunning`
  from `register()` is the ordinary case — was swallowed, so a session row would appear and never
  move.
- **2026-09-30 — the UI stopped claiming things that are not true.** *Run without watching* replied
  "Queued: {kind}. Watch the log below; the run continues if you change tab." while creating no
  session and starting nothing; it now says plainly that the orchestrator's callables are not wired
  and that nothing was spent. The four buttons with no handler at all — *Rerun?*, *Run twin quality
  test*, *Check twins against their drivers*, *Import twins from the survey* — are
  `interactive=False` rather than silently inert.
- **2026-09-30 — `_v1_removed/` and `_preserve/` deleted** at the researcher's instruction, with
  the caches. `_preserve` was verified redundant first: `templates.py` byte-identical to the live
  copy, `build_reference.py` superseded, and all eight sha256 digests already hard-coded at
  `tests/test_m1_reference.py:49`. `_probe/` and `docs/_v1/` are kept.

### Found, not fixed — these are the researcher's

- **`app_config` is write-only.** Nothing reads `"twin"`, `"rules"`, `"analysis"`, `"style"` or
  `"orchestrator"` back; only `"reference"` is ever selected. `load_twin_config()` and
  `load_analysis_config()` read the YAML files. So Agent Studio's *Save rules* (checker rules and
  index weights) and the Settings tab both write rows no code path consults, while `docs/09` §4 and
  `docs/06` §3.8/§6 describe app_config as where the live values live. **Which source wins is a
  research decision** — it determines what a session runs under — so it is escalated, not picked.
  Both save messages now state plainly that the value is recorded and not yet in force. Related:
  `ask_twins` passes no `config`, so `sessions.config` is always `{}` and `_render`/`ask_panel`
  always fall back to `style_version="v1"` and `wording="A"`.
- **No injected runner callables.** Nothing in `ui/` or `services/` supplies `render_and_check`,
  `ask_twin`, `analyse` or `candidates`, and `services.runs.ask_twins` — the only real entry point
  to the orchestrator — is never called from the UI. There is no end-to-end path from any button to
  a model call. This is `HANDOFF.md` §0.5's M8/M10/M11 remainder, stated as one fact.
- **The PLS-SEM run blocks the event loop.** `statistics._run` awaits `run_analysis`, which calls
  `plssem.fit` and `LongBootstrap` directly with no `to_thread`. At 5,000 samples (~25 minutes) the
  UI and any running sweep freeze. `asyncio.to_thread` would fix it; whether the engine is
  thread-safe has not been established, so it is not assumed.
- **`openpls-engine>=0.1` is unpinned**, and it computes every statistic the golden gate holds to
  |Δ| < 0.001. `pydantic-ai-slim>=0.0.30` resolves to 2.51.0, two majors past what the pin was
  written against — `_TOKEN_FIELDS` already exists to absorb that drift. Both want upper bounds.
- **`docs/06` §7 mandates CSV, XLSX and raw JSON export; only CSV is exposed.** `to_xlsx` and
  `to_json` exist in `stats/export.py` and are unreachable, and `openpyxl` is not in
  `requirements.txt`, so `to_xlsx` would raise if it were called.
- **Declared and unused**: `settings.yield_every`, `settings.log_poll_seconds` (`lab.py` hardcodes
  `gr.Timer(3.0)`), `settings.hf_oauth_org`, `settings.logfire_token`/`logfire_enabled`,
  `settings.intake_hmac_secret` (intake runs in the Edge Function, by design), `TEMP_DIR`;
  `docs/04` §4's `max_run_seconds`, implemented nowhere; the dependencies `plotly`, `logfire` and
  `httpx`, imported by nothing. `telemetry.py` did not survive the rebuild, so
  `run_events.logfire_span_id` is permanently null.
- **`validate_code` admits `"SHAM"`, and five callers then crash on it** with an opaque
  `ValueError` rather than `InvalidVersionCode`: `digit_sum`, `dials`, `index_from_code`, `combine`
  and `lookup.dial_of`.
- **`SupabaseBackend._run` retries every exception**, including deterministic 4xx like the
  `PGRST204` above — four attempts with backoff on an error that can never succeed.
- **`black` is the declared style and CI never runs it**; 82 files would reformat. CI's
  `ruff check src tests tools` also omits `config/` and `app*.py`.
- **`.env` holds live Supabase and Ollama credentials inside a OneDrive-synced directory.**
  Gitignored, but synced.

### Found by running it against the live project, 2026-09-30

The audit above was static plus the in-memory suite. Seeding the real project and generating a
300-respondent synthetic batch found four more, all of the same kind: **correct in memory, wrong
against Postgres.** None was reachable by any test, because `InMemoryBackend` has no row cap, no
foreign keys and no PostgREST.

- **2026-09-30 — `SupabaseBackend.select` pages. It was silently truncating at 1,000 rows.**
  PostgREST caps a response at `db-max-rows` — 1,000 on Supabase — and returns the first page with
  a `200`, not an error. `select` issued one request and returned whatever came back. Measured:
  `survey_answers` held 21,900 rows and `select` returned 1,000. Every statistic
  `stats/dataset.py` builds, and the `docs/07` §11 export, would have been computed on a fifth of
  the data with **nothing anywhere saying so** — the golden gate passes because it runs on
  in-memory fixtures. A plausible number that is wrong is the worst failure this system can have.
  Paging stops on a **short page** rather than on an assumed cap, so a lowered `db-max-rows` costs
  requests, not rows. The loop is `paged_select`, separate from the backend so it can be tested
  without a client — the live backend is banned outright in `tests/conftest.py`, and the cap is a
  server behaviour no stand-in reproduces. Callers that need more than one page and care about
  order across page boundaries must pass `order`; Postgres guarantees none without it.
- **2026-09-30 — the `in` and `is` filters never worked against a real database.** `_apply` did
  `getattr(query, op)`, and postgrest spells them `in_` and `is_` because both are Python
  keywords. `getattr(query, "in")` raised `AttributeError`, which `_run` then retried four times
  and reported as *"database call failed after 4 attempts"*. `InMemoryBackend` implements both by
  name, so the suite was green and only two callers were affected — `services.surveys
  .delete_synthetic`, which could never have run, and the log tree's ancestor lookup added in this
  audit. `FILTER_METHODS` maps them, an unmapped operator now raises at the boundary instead of
  being retried, and the test asserts every operator in `Filter` against the installed SDK rather
  than a hard-coded list.
- **2026-09-30 — `available_survey_twins` excludes synthetic rows.**
  `services.studio.create_twin_from_survey` refuses a synthetic submission by design (`docs/06` §5:
  a synthetic twin is made in the Generator), but the count did not, so with the synthetic batch
  loaded the Settings tab read *300 available* and all 300 would have been refused. A count and the
  rule it counts against have to be the same rule.
- **2026-09-30 — the `raw-surveys` Storage bucket did not exist and no document says to create
  it.** `supabase/functions/survey_intake/index.ts` uploads every raw object to it before any table
  write (I16) and expects it to be there; `docs/SETUP.md` never mentions it. Created **private**,
  because it holds raw driver responses. **`docs/SETUP.md` needs this step written into it** —
  live intake would have failed on the first real submission with `Bucket not found`.

### The live project, as of 2026-09-30

- **Migrations 001 and 002 are applied.** The seed had previously stopped at `gaps` — the
  `criterion_id` defect above — leaving `criteria`, `thresholds`, `survey_items`, `constructs` and
  `arms` written and everything after `gaps` empty. With the fix, `seed_db.py` completes and all
  eighteen post-seed assertions pass. `HANDOFF.md` §0.7 item 2 is resolved and should be rewritten.
- **A 300-respondent synthetic batch is loaded**, `(seed=20260930, count=300)`, 21,900 answers, 300
  raw objects in `raw-surveys`. Reproducible from that pair; `tools/generate_synthetic.py
  --delete-synthetic` removes it and nothing else.
- **`tools/generate_synthetic.py` added.** The Generator screen is still an M0 stub, so this
  supplies the two things a screen would — the parameters and a Storage client. It is the only
  place outside `db/client.py` that touches the Supabase SDK, because Storage is not part of the
  `DbBackend` vocabulary and widening that boundary for one script is worse; it should move into
  the Generator screen's service function when that screen is built.
- **Statistics runs end to end on it**: 300 cases, `openpls-engine` 1.11.0, all nine stages,
  `ModelSpec.fingerprint()` `7c7fd73a12a4ec48` as pinned. Fit plus a 200-sample bootstrap took
  190 s, so 5,000 samples is roughly 80 minutes — and it runs on the event loop (see the unfixed
  item above), so the UI is frozen for the duration.
- **`.claude/launch.json` added** so the app starts as a named preview on port 7860.

## D-UI — Visual parity with the prototype

- **2026-09-30 — D-UI-01: the interface now reproduces the prototype's styling, not only its
  density.** `docs/05` §1 previously said "reproduce the density and the hierarchy, **not** the
  Apps Script styling", and §2 locked a single blue accent, a system font stack and an explicit
  no-webfont rule. The researcher asked for visual parity with
  `additional_data/screenshots of the prototype - Google Docs.pdf` — "the font, boxes, colors,
  exactly ditto same" — and confirmed that `docs/05` should be updated to match rather than left
  contradicting the code. Every token in the rewritten §2 was **sampled off the screenshots**
  (dominant-colour and ink-height measurement over the 63 extracted images), not eyeballed.
  What changed: Roboto in place of the system stack; Google Material neutrals (`#F8F9FA`
  background, `#202124` text, `#E9EAED` borders) in place of the Tailwind-ish greys; a per-app
  accent (`ROUTE_ACCENTS`) in place of one blue; 8px radius and no resting card shadow; and the
  section heading became a 3px accent bar.
- **2026-09-30 — D-UI-02: the webfont ban is answered, not overridden.** Roboto loads through
  `gr.Blocks(head=FONT_HEAD)` with `display=swap` behind a complete fallback stack, so a cold
  Space paints in the fallback and swaps when the font lands. The original reason — first paint
  must not wait on a font — still governs: if the `<link>` ever gates first paint, remove the
  `<link>`, not the fallback.
- **2026-09-30 — D-UI-03: `gr.Navbar` is hidden and `global_nav` draws the strip.** Gradio's
  navbar cannot carry the accent underline or the `< Main menu` back link the prototype has on
  every screen, and two navbars on one page is the one thing the prototype definitely does not
  have. `visible=False` is set *and* `nav.fillable{display:none}`, because Gradio 5 renders the
  element either way. Routing is unaffected — `demo.route()` is what makes the URLs real.
- **2026-09-30 — D-UI-04: the Agent Studio cards became the selector.** `docs/06` §6 asks for
  "five selectable `agent_card`s"; the build had a `gr.Radio` *and* a separate card list, so the
  cards were decoration. They now carry `data-agent` and a click bridges to the radio through
  `load_js`, the same mechanism `docs/05` §8.3 mandates for the 243-grid. The radio stays in the
  DOM, visually clipped rather than `display:none`, so the agent list keeps its keyboard and
  screen-reader behaviour.
- **2026-09-30 — D-UI-05: dial segments are labelled `0 today` / `1 some` / `2 more`.** They were
  `0` / `1` / `2`, which is a digit plus a colour. `docs/06` §3.2's legend and the prototype's
  segments both carry the words, and §6 forbids colour alone.
- **2026-09-30 — D-UI-06: Statistics' two population controls became dropdowns and its ten
  sections became pill tabs,** matching the prototype's control strip. No handler changed; the
  choices and values are identical.

### Degradations accepted, 2026-09-30

- **The prototype's `rules only` / `uses AI` agent badges are NOT reproduced.** `docs/06` §6
  retires them explicitly — they described the prototype, not the architecture — so the cards
  show each agent's actual model usage. Visual parity does not reopen a decided content question.
- **The `00000` warning strip has no prototype counterpart and stays.** `docs/05` §7 rule 3 is an
  invariant; the prototype simply did not implement it.
- **The Generator and Driver survey screens are still M0 stubs.** They now carry the prototype's
  purple and blue accents and its shell, but their content is M9's and was not built here. The
  prototype's Generator (batch, cities, weights, sentiment sliders) is not reproduced yet.

---

## 2026-09-30 — audit session: the schema-drift class, dark mode, and the Generator page

### Fixed

- **D-DB-01: `runs` has no `created_at`, and five callers ordered by it.** The DDL timestamps
  `runs` with `started_at` and `finished_at`. `services.status.tested_codes`,
  `status.control_index`, `lab.comparable_codes`, `lab._answers_for` and `results.completed_runs`
  all ordered by `created_at`, and `results._metadata` read it for the "Completed" label (now
  `finished_at`). Against Postgres every one raised `42703` and took the Agents tab's poll with
  it, so the five agent cards never left *Loading…*.
  **Why 684 tests passed:** `InMemoryBackend.select` sorted with `r.get(col)`, which answers
  `None` for a column that does not exist. The mirror already knew `runs` has no `created_at` —
  it is excluded from `HAS_CREATED_AT` — it simply did not enforce it, making the stand-in *more
  permissive than the database in the one direction that hides drift*. This is the same shape as
  the `FILTER_METHODS` bug (`in` / `is`), which is why the fix is structural rather than local:
  `db.client.TABLE_COLUMNS` is now **parsed out of the migration files at import**, and every
  in-memory `select` / `insert` / `update` / `upsert` / `delete` / `count` raises
  `undefined_column` the way Postgres would. A static AST sweep of `src/` asserts the same thing
  for code no test exercises; both gates were proved to fail against the original bug.

- **D-UI-07: Gradio's dark theme was leaking into a light design.** Gradio applies `.dark` from
  the browser's `prefers-color-scheme` and re-points ~234 of its own custom properties. Twin Lab
  forces white surfaces, so dark-theme *text* landed on forced-*white* surfaces: the help
  accordion's labels computed to `#F4F4F5` on `#FFFFFF`, **1.05:1**. It was invisible on every
  screen and was reported as "I cannot see the headings".
  Repaired at the **token layer** under `.dark`, not per component: a per-component list is never
  finished, which is exactly how `.label-wrap` — a `<span>`, caught by neither of the two label
  overrides — stayed invisible. Gradio's documented `?__theme=light` redirect was rejected: it
  costs a full reload on each of the eight routes, and a screen that flashes dark then reloads is
  worse than one that was never dark.

- **D-UI-08: the navbar was rendering as eight blue links.** `.tl-page a{color:var(--tl-info)}`
  sits later in the stylesheet than `.tl-nav a{color:var(--tl-grey-500)}` at equal specificity,
  so the generic page-link rule won. `.tl-nav` is raised above it rather than `.tl-page a` being
  lowered, because a link in a page body *should* be `--tl-info`; it is the navbar that is not
  body text. This also cleared a 4.38:1 contrast failure on every screen.

- **D-UI-09: Gradio's screen-reader copy of each tab strip was visible.**
  `.tab-container{display:flex !important}` beat the `visually-hidden` clip, so Twin Lab's eight
  tabs and Statistics' ten rendered twice. The hidden copy is now `display:none`; the real strip
  keeps the flex rule it needs.

- **D-UI-10: `docs/05` §6's contrast floor is now enforced.** It was stated as "a testable
  minimum" and never tested, so it drifted: `--tl-ok` on `--tl-ok-tint` was 4.34:1 and rendered
  **267 times on one Statistics page**; the live-model badge was 4.39:1. A pill's letters now take
  the dark variant of its own hue while its fill keeps the measured tint, so the prototype's
  colour language (D-UI-01) is unchanged and only the ink moved. The test reads the rule out of
  `TWINLAB_CSS` rather than restating the token, so reverting the stylesheet fails it.
  **Button fills and tab strips were left alone**: §6 puts chrome at 3:1 and they all clear it,
  and darkening a per-app accent would change the measured identity of a whole screen — that is
  the researcher's call, not a lint fix.

- **D-UI-11: destination cards are controls again.** `docs/06` §1.1's cards wrapped only the
  route in an `<a>`, leaving the title and the description inert and the hit target about a
  quarter of the tile. The whole card is the link now; the route stays as a quiet caption because
  §1.1 makes all three elements mandatory. The link goes to the route, not to the tab within it:
  `demo.route()` gives each page one URL and no per-tab address, so inventing one would not
  resolve.

### The Generator page — `docs/06` §4

- **D-GEN-01: `config/generator.default.yaml` was provenance that described nothing.** It was
  written into every batch's stored `config`, but **none of its values were read** — `likert_sd`,
  `mc_correct_rate` and the completion-second bounds were hard-coded literals in
  `synthetic_payload` that happened to match the file. A batch therefore recorded a configuration
  that did not produce it. `spec_from_config()` now reads the file, and the batch records the
  `GeneratorSpec` that actually drew it beside the file's defaults.

- **D-GEN-02: `GENERATOR_VERSION = "v2"`, and a `v1` seed does not reproduce under `v2`.**
  `docs/06` §4's city and service weights required a weighted draw in place of `random.choice`,
  which consumes the respondent's RNG differently. "Same seed, same batch" (`docs/09` §2) holds
  **within a version, never across one**, so the version is recorded on every batch and the break
  is visible in the data rather than left for a later reader to infer. The three batches already
  in the researcher's project are `v1` and predate the field; synthetic rows prove nothing about
  drivers (`docs/08` §6.2), so regenerating them costs only the seconds it takes.

- **D-GEN-03: eleven of §4's twelve sentiment controls are bound; one is not, and says so.**
  Nine map onto the frozen register's constructs, and *how much drivers differ* and *answer noise*
  map onto `disposition_spread` and `likert_sd`. *Appeals and forum work together* and the five
  per-lever reaction sliders describe how a **mock twin** reacts to a change. `docs/11` assigns
  the mock twin no milestone and this build has none — the generator makes survey answers, not
  reactions — so there is no parameter to bind them to. **They are named on the page as not built
  rather than shipped as controls that would do nothing** (`docs/05` §8.2: degrade the styling,
  never drop a specified element silently).

- **D-GEN-04: *Generate surveys* is rendered and disabled.** `services.surveys.store_batch`
  writes each raw payload to Storage **before** its rows (I16), and `storage` is a duck-typed
  `Any` with no implementation anywhere outside `FakeStorage` in the tests — no bucket name, no
  client, no setting. Building one is a deployment decision about the researcher's own project,
  not a code cleanup, so the button is disabled and the page states the reason. *Preview 3
  drivers* (which `docs/06` §4 specifies as deriving only and inserting nothing — enforced by
  giving `preview()` no backend parameter at all) and *Delete all synthetic surveys* are live.

### Still open after this session

- **Driver survey (`docs/06` §2) is still an M0 stub.** Not touched; no milestone assigns it.
- **The four `SessionRunner` callables are still uninjected**, so no sweep, quality test, twin
  import or validation runs. Every piece they would call is built and tested.
- **There is no Storage client**, so I16's ordering guarantee is unexercised outside tests, and
  `raw_object_path` is recorded on 300 existing rows whose objects were never written.

## D-PARITY — prototype parity: the Generator, the Studio, the validity board and the grid

*2026-09-30. The researcher compared the running system against the Apps Script prototype
screen by screen and named what was missing. This section records what changed and why. Every
earlier D-GEN entry above is superseded where the two disagree.*

### The generator's controls

- **D-GEN-05: the generator drew a city the Form cannot produce.** `docs/GOOGLE_FORM.md` Part 3
  question 2 offers **Mumbai / Pune / Delhi NCR / Jaipur / Bengaluru**. The generator's list held
  four and spelled Delhi NCR as `"Delhi"`, so roughly a quarter of every synthetic batch carried a
  `field:city` value live intake could never receive, and Jaipur never appeared at all. The list is
  now `models/view.GENERATOR_CITIES`, imported by both the generator and the page, so there is one
  spelling of each. **The 300-row batch in the researcher's project predates this and carries the
  old values**; regenerating it costs the seconds it takes (`docs/08` §6.2).

- **D-GEN-06: the sentiment sliders are absolute 1–7 targets, not offsets.** `docs/06` §4's caption
  is *"average answer on a 1 to 7 scale (5 point questions are converted)"*, which is a target, and
  the prototype's sliders read 1–7. They were built as `−2…+2` nudges on top of a preset, which is
  a different control with a different meaning. `construct_offsets` is replaced by
  `construct_targets`; the conversion to a 5-point item is
  `generator.synthetic.centre_for_points`, a **linear map of the scale's range** — 7/7 becomes 5/5
  and 4/7 becomes 3/5 — never a clamp. This is generation, not repair, so `docs/02` §5.3's ban on
  clamping is not in play: there is no respondent whose answer is being altered.

- **D-GEN-07: a preset fills the sliders rather than acting beside them.** In the prototype the
  three presets are buttons that set every construct slider, which is why the sliders show values
  and not offsets. `SENTIMENT_PRESETS` holds the three sets. They are deliberately **not flat**: a
  frustrated driver is low on fairness, clarity, satisfaction and loyalty and *high* on exposure,
  control, pushback and exit. A flat preset would make every construct correlate +1 with every
  other, which no analysis could use.

- **D-GEN-08: four of §4's controls existed in the prototype and in no form here** — *use other
  apps too*, *car or bike on a loan*, *need the money (1 to 7)* and *shared overall mood*. All four
  are bound. Two of them fixed a data defect on the way: `background:platform_count` and
  `background:other_apps` were drawn **independently**, so a synthetic respondent routinely
  reported one platform and then named two others — a contradiction a real submission cannot
  contain. They are now one decision. *Need the money* sets the `EDEP` block, which is the
  moderator in `stats/spec.py`'s frozen structural model, and that is why it is a control of its
  own rather than a ninth construct slider.

- **D-GEN-09: tenure is set in months and stored in years.** The prototype asks *fewest / most
  months on Uber* (3–72); the Form asks years and intake converts back (this file, 2026-09-22).
  Three months is the eligibility floor and "0.25 years" is not a quantity a researcher sets.
  `synthetic.years_from_months` is the single conversion and **round-trips exactly** —
  `round(float(years_from_months(m)) * 12) == m` — so the tenure a batch stores is the tenure it
  was drawn with. Tested.

- **D-GEN-10 — the correction that matters most: reverse-coded items were drawn forward.** `SAT2`
  ("In general, I don't like my job"), `DEP1` and `H2_SAT2` carry `reverse_coded` on the frozen
  register, and the generator ignored it — so `SAT2` **rose** with satisfaction. Every synthetic
  batch therefore contained a SAT block that contradicted itself, which destroys the construct's
  reliability before any analysis runs, and the same for DEP. The draw now mirrors a reverse-coded
  item about its scale midpoint. This is read off the register, not re-decided here.

- **D-GEN-11: the five reaction sliders and the captive-voice checkbox are bound, and D-GEN-03 is
  withdrawn.** D-GEN-03 read them as describing a *mock twin*, which this build does not have, and
  shipped a "not built" notice in their place. That reading was wrong: the prototype's own caption
  says *"used for the change story (Part 16) and the six versions (Part 17)"* — both of which are
  **the synthetic respondent's own answers**, not a twin's. They were doing nothing because the
  two holdout blocks were drawn from the unchanged baseline:

  * `H2_*` (Part 16) asks the battery again *imagining the respondent's assigned arm is true*. It
    now moves by that arm's version code. Before, the arm a respondent was assigned had no effect
    on anything they answered, so H2 validation could not distinguish the four arms at all.
  * `H3_V{n}_*` (Part 17) asks three questions about **six real version codes** (`docs/01` §3.6).
    Each now moves by its own code, so a respondent answers the six differently. Before, all six
    were identical up to noise — and H3 is *the fidelity gate*, so a twin scored against that human
    could not fail it for the right reason.

  The arithmetic is `synthetic.reaction_shift`: `dial × weight` summed over the five levers, scaled
  so full protection at normal weights moves a respondent about two points on a seven-point scale.
  The **sign** is applied by the caller from the construct's own `index_sign`, because more
  protection raises fairness and lowers the wish to leave and one magnitude cannot carry both.
  *Captive voice* raises the weight of the representation lever only, in proportion to the
  respondent's own `EDEP`. A batch with every reaction at zero produces holdouts identical to the
  baseline, which is the correct null and is tested as one.

- **D-GEN-12: `GENERATOR_VERSION` is `v3`, and a `v2` seed does not reproduce under it.** Every
  change above moves the draw order, not only the values. "Same seed, same batch" (`docs/09` §2)
  holds within a version and never across one, and recording the break in the data beats leaving a
  later reader to infer it.

- **D-GEN-13: `config/generator.default.yaml` now carries every §4 default and the page opens on
  it.** The page had its own literal defaults, which could drift from the file silently; it reads
  `default_spec()` instead. `likert_sd` moved from **1.1 to 0.3**: at 1.1 a seven-point item's
  answers span most of the scale from noise alone and the construct means the dashboard sets are
  barely visible in them.

### Storage, and *Generate surveys*

- **D-GEN-14: there is a Storage client, it lives in `db/client.py`, and *Generate surveys* is
  live. D-GEN-04 is withdrawn.** D-GEN-04 called building one "a deployment decision, not a code
  cleanup" and shipped the button disabled. But a client already existed — inside
  `tools/generate_synthetic.py` — which put the `supabase` SDK **outside the one file allowed to
  import it** (`CLAUDE.md`, Boundaries) and left the screen with nothing to call. It is now
  `db.client.SupabaseStorage` alongside `InMemoryStorage`, reached through `get_storage()`, and
  the script uses it too, so the SDK is confined again. The bucket is `raw-surveys`, the name the
  Edge Function already uses: **one name, two writers**, because a second name would split the
  mirror in two.

  `get_storage()` is paired with `get_backend()` on purpose. A live database with an in-memory
  mirror would write durable rows pointing at objects that vanish on restart, and `replay_raw.py`
  would report every one of them as an orphan forever — so the two fail together.

  A failed upload raises `StorageError` and is **never swallowed**: I16 is an ordering guarantee,
  and a batch that stored rows after a silent upload failure has rows whose `raw_object_path`
  points at nothing. The ordering itself is now tested against a recorder that fails if any row is
  written before the last object lands.

### The screens

- **D-UI-12: Twin Studio had two selectors for one selection.** A `gr.Dropdown` *"Use a twin I
  have"* and a read-only `gr.Textbox` *"Twin in use"*, and both rendered as unlabelled fields with
  number-spinner arrows, with long option text running outside the box — which is what the
  researcher reported as *"some letters are not even in the box"*. There is now **one picker**,
  its value is the selection, and creating a twin from a survey row or by hand re-reads the picker
  and selects the new twin. The persona panel moved under it, as in the prototype, with the
  prototype's own heading. The dial card gained the protection legend, the prototype's
  `Version code: 00000 (00000 means Uber today)` line and its placeholder text.

- **D-UI-13: the validity board's Run control is inside its own card.** Eight cards were followed
  by eight buttons whose only tie to them was a number in the label, so the reader had to match
  them up by hand. Gradio cannot put a `gr.Button` inside a `gr.HTML` blob, so each card is now a
  `gr.Group` holding its own text and its own button — a filled green pill, white text, arrow.
  Green is `--tl-ok`, whose fixed meaning (`docs/05` §7) is PASS / good; it is deliberately not the
  route accent. The confirm-before-cost step (`docs/06` §9) is unchanged and still gates all eight.

- **D-UI-14 — a real bug: the 243 grid was invisible, and had been.** `.tl-subnav button` set
  `background:transparent !important` on **every button inside the Twin Lab tab panel**, and each
  of the 243 grid cells is a `<button>`. `docs/05` §8.3's *"tested filled white→green by index"*
  therefore could not render whatever the data said; the grid read as an empty outlined table. The
  rule is now scoped to `.tl-subnav .tab-container button`, which is the tab strip it was written
  for, and the cell rules carry `.tl-page` specificity so no panel rule can blank a data mark
  again.

- **D-UI-15: the grid fills by index, and says so twice.** `GridCell.intensity` is where a cell's
  index sits in the **range tested so far**, so a half-finished sweep still separates its results
  instead of painting them one shade. It drives a single `--tl-cell-depth` alpha. A floor of 0.18
  keeps the palest tested cell clearly darker than an untested one, because *tested and worst* and
  *not tested* are different facts. `docs/05` §6 forbids encoding anything by colour **alone**, so
  the exact index stays in every cell's `title` and `aria-label` and again in the Tested versions
  table. Cells went 14px → 20px and the row axis is labelled `pay 0, cond. 0` … `pay 2, cond. 2`,
  read from `grid_position`'s own mapping rather than written down beside it.

- **D-UI-16: *Do changes work together?* is a card beside the grid, as `docs/06` §3.7 lists it.**
  It was only ever in the side panel, for one selected cell. `services.results.interaction_rows`
  leads with two named pairings — appeals × forum on pushback, pay × conditions on staying — which
  are a **reading order, not a hypothesis set**; `docs/07` §5 defines the arithmetic for any pair
  and every other pair involving a selected cell is still in that cell's side panel. A missing leg
  names the codes to run and is never estimated (I17, `CLAUDE.md` rule 5).

- **D-UI-17: the Driver survey screen is built (`docs/06` §2), and it still does not host the
  survey.** It shows what the instrument is, intake status, the four-arm balance by `city|service`
  and the form link. The two counts it states are **counted, not written down** — 112 from
  `form_map.yaml`, 73 from the register, 17 parts from the items — so the page cannot drift from
  the instrument. Synthetic rows are excluded from every fieldwork number and shown separately.
  `SURVEY_FORM_URL` and `SURVEY_INTAKE_URL` are new settings; with neither set the page shows §2's
  placeholder in §2's own words rather than a dead link.

  **Intake status is reported as *configured*, not as *reachable*.** The Space never calls the
  endpoint to prove it is up: a page that probed intake on every render would be exactly the
  participant in the intake path that §2 says it must not be.

### Open — the researcher's, not a coding session's

- **A second intake route is a specification change and has not been made.** The researcher has
  said a driver survey will arrive with **two routes** — the external Google Form, and the Driver
  survey tab itself. `docs/06` §2 and `docs/04` §8 currently say the opposite in as many words:
  the page *"does not host the survey"*, and intake runs outside the Space **so that a sleeping
  free Space cannot drop a submission**. Hosting intake in the Space also meets I16, since a
  Gradio handler has nowhere durable to write before Storage.

  Nothing was built for it, and no schema was changed, because three things would have to be
  decided first and all three are research decisions:

  1. **Provenance.** `survey_submissions` has no column for the route a submission arrived by, and
     `data_type` is `REAL`/`SYNTHETIC`, not a source. Two real routes that cannot be told apart in
     the data cannot be compared, and mode effects between a self-administered Form and an
     interviewer-operated tab are a real threat to H1–H3.
  2. **Assignment.** Arms are balanced *within* `city|service` stratum (`docs/01` §5.2). Two
     independent intake paths assigning arms from the same strata will drift unless one of them
     owns the counter.
  3. **Whether the in-app route writes through the Edge Function anyway.** It could post to the
     same signed endpoint rather than writing rows itself, which would keep I16, keep one row
     builder and make the route a UI over the existing path. That is the cheapest answer and the
     one that changes the least, but it is still a change to §2.

  **Recommendation: option 3, plus a `source` column.** It costs one migration and one page, keeps
  every invariant, and makes the two routes separable in the export. It needs the researcher's
  agreement before it is built.

- **The 300-row synthetic batch in the live project is `v2`** and carries the four-city list, the
  forward-drawn reverse-coded items and holdout blocks that do not move with the arm. It is
  reproducible from `(seed=20260930, count=300)` under `v2` only. Regenerating it under `v3` is a
  button press and synthetic rows prove nothing about drivers (`docs/08` §6.2) — but it should be
  a deliberate press, so it has not been done.

---

## M15 — Wiring the live twin path, 2026-09-30

Until this session **no live twin path existed anywhere in the build** (HANDOFF §0.5: M10's
workflow buttons "enqueue a stub", M11's *Ask the twin* "has no live twin call yet", M13's tests
4–8 "record `INCONCLUSIVE` until one is wired"). `services/twin_runtime.py` and
`services/quality.py` are that path.

### Researcher decisions taken this session

- **2026-09-30 — RESEARCHER: containment fires on *distinctive* bigrams only.** HANDOFF §0.7 item
  3, closed. A signature pair that occurs in **more than one** forbidden commitment is shared
  vocabulary, not distinctive vocabulary, and is no longer a hit
  (`variant/checker.distinctive_signatures`).

  The evidence: on `11010` the `L4` paragraph was flagged for leaking `3.1.b`, `3.1.c`, `5.1.b`
  **and** `5.2.b`, and every one of those hits was the single pair `("driver", "app")` — because
  *Driver app* is Uber's own name for the thing and it appears in four commitments. A pair that
  cannot say *which* commitment leaked is not evidence that one did. This is the argument of the
  2026-09-22 single-word decision applied one level up.

  **The narrowing costs nothing measurable over the frozen data.** Across all 285 (lever, dial,
  forbidden) combinations, **zero** commitments have an empty distinctive signature, and every one
  of them dropped in verbatim is still caught by name. Both facts are asserted in
  `tests/test_m5_render_checker.py`, so neither can decay silently.

### Mechanical choices

- **2026-09-30 — `docs/03` §5's "re-render once" is implemented, and it is targeted.** The second
  pass was specified and never built, so a cell that failed on one stochastic bad paragraph failed
  permanently — and, because paragraphs are cached, so did every other cell using it. The
  re-render now carries an instruction naming what the previous attempt missed **of its own
  contract**: commitments it did not state, a forbidden intensifier it used, prose too dense for
  the register band. It cannot change what the paragraph may say — the brief's commitments and
  do-not-say list are untouched — so it is the design agent's equivalent of the twin's targeted
  repair (`docs/02` §5.4), not the Checker steering the text it grades. **No number from the style
  contract is quoted**, because `agents/design.STYLE_KEYS_SHOWN` withholds the reading-grade band
  on purpose.

  The budget is **one re-render per `(lever, dial, style_version)` per process**, not per cell:
  per cell would call the design agent once for every code and break I4 outright.

- **2026-09-30 — `lever_paragraphs` is now written, and it is the same cache, not a fourth.**
  `StoredParagraphPool` warms `ParagraphPool` from the table on first use and writes a miss back,
  on the `(lever, dial, style_version)` key the DDL already declares. Without it the ten design
  calls were re-paid on every restart, and on a free Space a restart is routine. The write is an
  **upsert**: a re-render deletes the row and writes a new one, and a duplicate key there is the
  cache working, not a data defect.

- **2026-09-30 — `app_config['twin']` is now read back.** The Settings tab wrote a new version and
  nothing read it, so a researcher who changed a quality threshold saw a success message and
  changed nothing. `services/config.load_twin_config()` now returns `app_config` over the YAML
  seed; `refresh_twin_config()` re-reads it at boot, and every session and quality run re-reads it
  before it freezes its own `config` column. The YAML stays the **seed**, per `docs/09` §4.

- **2026-09-30 — the quality gate aborts if any of its six stimuli fails the Checker.** It does not
  score the twin on the codes that did render. Eighteen items over five versions is a different
  measurement from eighteen over six, and recording it under the same `holdout_set` would make two
  twins incomparable with nothing in the data saying why (I3 + I15's spirit).

- **2026-09-30 — the H2 answer vector is written.** `twin_quality_runs.detail["answers"]`, which is
  what `services/validity.H2_ANSWERS_KEY` has always read. This is the wiring job HANDOFF §0.5
  named as unlocking validity tests 1 and 3, and both make no model call.

- **2026-09-30 — a quality session is `kind='quality'` with `iterations=0`.** It has no cells and
  no cursor, so `running_job_line`'s "x of y versions" would count nothing; the Agents tab reports
  twins scored instead. It emits into `run_events` under its own session id like any other job, so
  the log and the Stop button work without a second mechanism.

- **2026-09-30 — Twin Studio's free-text replies are rendered above the metric table.** `docs/06`
  §5 specifies the construct table and the scenario accordion but says nothing about where the
  answers to the researcher's own five questions go — and a screen that takes five questions and
  shows no replies is not a screen. `models/twin.StudioReply` refuses a reply list that does not
  line up with the questions rather than zipping it short: a reply attached to a question the twin
  did not answer is a fabricated answer.

- **2026-09-30 — Twin Studio refuses a dialled version whose Checker report failed.** The
  quarantine (`docs/01` §6.9) is about where an answer is **filed**, not about whether the stimulus
  was verified; I3 has no sandbox exemption. A *custom* change is still allowed, because it bypasses
  the lookup and the Checker by construction and carries `SANDBOX_LABEL` saying so.

- **2026-09-30 — a table row opens the row it names.** `data_table(row_keys=...)` plus a click
  bridge, the same pattern `docs/05` §8.3 already mandates for the 243-grid and for the same
  reason: `twin_id` is opaque by design (`CLAUDE.md` rule 8), so a table a researcher has to
  re-type a key out of is a table that gets read wrong.

- **2026-09-30 — `tests/test_m10_ui.py::test_available_survey_twins_excludes_synthetic_rows`
  corrected.** It called `available_survey_twins(backend)` positionally against a signature that
  had since gained a leading `scope`, so it passed the backend in as the scope and asserted a rule
  the function deliberately no longer has. Renamed and rewritten to check all three scopes.

### Still open, and now measured

- **The register band is what fails cells now, not containment.** With containment narrowed, the
  live failures on the Part 17 stimuli are `reading grade > 16.0` on the `L4` paragraphs and
  uncovered commitments on `L4` at dial 2, which carries **eight** commitments inside a 45–150 word
  band. This is the tension `config/style_contract.yaml`'s own 2026-09-29 note predicted — "word_max
  no longer binds for small commitment sets, so the reading-grade gate is the only thing holding
  register. Watch it, not the band." It is being watched, and it is binding. Whether `word_max`,
  `reading_grade_max` or the per-lever commitment count moves is a research decision and has not
  been taken. **Taken on 2026-10-01 - see M16 below. None of the three moved.**


## M16 — the live path, unblocked

Three RESEARCHER decisions and one defect fix, 2026-10-01. The session began where
`HANDOFF_M15_LIVE_PATH.md` left it: 749 tests green and no twin had ever answered a question.

### The blocker (§3.1) — not a decision, a defect

- **2026-10-01 — the provider is handed a permissive transport shape, never a validating one.**
  `models/twin.AnswerVector`: `answers: dict[str, Any]`, `rationale: Any`, no cross-field
  validator, `extra="allow"`. `ask_items` and `agents/twin.run_twin` pass it as `output_type`, and
  the twin agent's `output_schema` in `config/agents.default.yaml` now names it too, because
  `build_agent` falls back to the config when no `output_type` is given and that fallback was a
  live call site.

  Two failures, both silent until a live call. `TwinAnswerSet` as the output marker validated the
  37-item register **inside pydantic-ai**, so a 36-item reply raised before `run_answer_ladder`
  ran and the one targeted repair of `docs/02` §5.4 was never issued — the provider schema doing
  the validating, which `CLAUDE.md` rule 4 forbids. And `normalise_answers` branches on
  `isinstance(payload, dict)`, while `PydanticAIClient.run().output` is a model *instance*, so
  every live reply including a perfect one was recorded "unparseable", burned an attempt and
  failed the round. `agents/contract.model_payload` now converts a `BaseModel` reply with
  `model_dump()` inside the ladder, which fixes `run_twin` at the same time and answers §3.4's
  question about it: fixed, not deleted.

  The value type is `Any` rather than `int` deliberately. `dict[str, int]` would reject `5.5` and
  `null` — precisely the `not_an_integer` defects the ladder exists to name and re-ask for. A
  transport model that rejects anything moves a judgement out of Python and into the provider
  round trip.

  Six regression tests in `tests/test_m2_contract.py`. All six fail against the old code; three of
  them are the ones the handoff asked for first.

### §4.1 — the register band versus the commitment load. RESEARCHER

- **2026-10-01 — the design agent is shown the reading-grade band.** Option 3 of four.
  `reading_grade_min` and `reading_grade_max` added to `agents.design.STYLE_KEYS_SHOWN`; both
  bounds, because gate 3 tests both. `reading_grade_max`, `word_max` and `paragraphs_per_lever`
  are all **unchanged** — the band did not move and the stimulus shape did not change.

  The band had been withheld on the theory that "showing a model a number it cannot act on invites
  it to put the number in the prose". The theory had never been tested and measurement overtook
  it. Rendered blind, then with the band shown, one design call each:

  | Lever, dial | Commitments | Blind | Band shown |
  |---|---|---|---|
  | `L1` 1 | 2 | 83w, grade 18.07 | 82w, **13.26 PASS** |
  | `L3` 2 | 8 | 151w, grade 24.51 | 150w, **14.47 PASS** |
  | `L4` 1 | 3 | 109w, grade 18.08 | 114w, 17.73 FAIL |
  | `L4` 2 | 8 | 150w, grade 17.89 | 150w, **13.82 PASS** |

  The original worry did not materialise and is not unguarded if it ever does: prompt rule 6
  forbids any number a commitment did not supply, and `check_invariance` would fail a render that
  leaked one rather than letting it reach a twin.

  **CORRECTED 2026-10-01, later the same day.** The table above is four single draws and the word
  "PASS" in it was over-read: I wrote that showing the band fixed the dense levers. The full
  six-code run contradicts that — the same paragraphs, rendered through the real pipeline, stored
  at `L1` d1 **17.79** (isolated draw: 13.26) and `L3` d2 **16.58** (isolated: 14.47). Part of the
  gap is the `_rerender_cell` defect below, which deleted passing paragraphs and re-rolled them
  with no instruction; part is simply that four draws at temperature 0.3 cannot support the word
  "fixed". **What is established: showing the band lowers the dense levers' grade substantially on
  average, and does NOT reliably clear 16.0 on a single draw.** The decision stands — the band is
  kept, and nothing about the stimulus moved — but it is not on its own what unblocks the grid.
  Three draws minimum before concluding anything about a render.

- **2026-10-01 — `L4` dial 1 is left to the re-render, and the repair instruction still quotes no
  number.** `L4` dial 1 is the one paragraph the band alone does not fix: 17.73, 17.86 and 17.16
  on three consecutive first-pass draws, so it is structural, not sampling. The cause is
  vocabulary, not commitment count — its three commitments carry the study's densest legal nouns
  ("disparagement", "deactivation", "Community Guidelines") and Flesch-Kincaid punishes syllables
  per word hardest, while `L4` dial 2's eight commitments force terser clauses and score *lower*.

  Since the agent now sees the band, the old reason for keeping the measured grade out of
  `services/twin_runtime._repair_for` had lapsed, so the two were compared live on `L4` dial 1,
  three renders each. Both cleared gate 3 **3/3**: wordless 9.09 / 10.09 / 8.37, numbered
  11.37 / 8.36 / 11.19. The wordless instruction is kept — it is no worse, and it puts no digit
  near prose that rule 6 forbids digits in. `docs/03` §5's one re-render is therefore enough for
  the whole grid, and nothing about the stimulus had to change.

- **2026-10-01 — `L3` dial 2 sits one word from the ceiling and should be watched.** Three draws
  gave 151, 152 and 150 words against a `word_max` of 150 — it passes or fails the band on
  sampling noise, while its grade is now comfortable at 13.14–14.47. `word_max: 150` is still
  carrying the 2026-09-29 "DELIBERATELY UNVERIFIED" note. The re-render handles a word-count
  breach (the instruction names the count and the range), so this is a cost in design calls rather
  than a blocked cell, and it is **not** a reason to move the band on its own.

### §4.2 — the style_version bump. RESEARCHER

- **2026-10-01 — `style_version` bumped v1 → v2,** in `config/style_contract.yaml` and
  `config/settings.py` together. The contract's own rule — "any change to this file, once a
  paragraph has been PERSISTED, MUST bump this" — bit for the first time: M15 persisted 7
  `lever_paragraphs` rows and 3 passing `variants`, and the §4.1 change alters the design prompt,
  so a v1 and a v2 paragraph are no longer written to the same contract. The 7 paragraphs and the
  3 passing cells (`00000`, `01000`, `00001`) must be re-rendered under v2. Paid now, deliberately,
  because the cost only grows once a sweep has run under v1. The stale "not bumped, and here is
  why" commentary in the contract is rewritten as a HISTORY section rather than deleted.

### §3.2 — the re-render budget. RESEARCHER

- **2026-10-01 — the budget is durable: `lever_paragraphs.attempts`,
  `003_render_attempts.sql`.** Additive, with a `check (attempts between 1 and 2)` so a
  hand-written UPDATE in the SQL editor cannot make the data say something the code will not.
  `RENDER_ATTEMPTS_MAX = 2` is the specification's own ceiling, not a preference. Previously
  `_rerendered` was a module-level set, so every restart — routine on a free Space — handed every
  `(lever, dial, style_version)` key a fresh re-render, and the design calls a paragraph had cost
  were recorded nowhere. I4's asserted call count now has a denominator that survives a process.

- **2026-10-01 — the attempt is charged to the table *before* the design call, and a refused
  re-render leaves the previous row in place.** Charging afterwards loses the record whenever the
  call crashes, times out or returns `cannot_render` — which is the case M15 actually hit on `L4`
  dial 2 — and the paragraph would then be re-rendered on every restart forever. The old code
  deleted the row before re-rendering; it now deletes only on the no-instruction path, where
  eviction is the point, and `_store` carries the charged count forward so eviction does not refund
  it. A refusal therefore leaves the old failing paragraph cached with `attempts = 2`, which is
  exactly the loud once-only failure `docs/03` §5 asks for.

  A key whose renders have *never* produced text still has no row and so no durable count. That is
  unchanged and separate: a refusal is not a paragraph and must never become a cache hit for the
  next cell (`StoredParagraphPool.get`).

### Mechanical

- **2026-10-01 — boot refuses a database missing a column the code writes.**
  `services/config._check_schema`, driven by `_REQUIRED_COLUMNS`, which names the migration file
  for each. Migrations are applied by hand in the Supabase SQL editor (`HANDOFF.md` §0.7), so the
  code and the database can disagree; failing at boot beats failing on the first write, by which
  point a design call has been paid for. An empty table says nothing about its columns and does not
  block boot.

- **2026-10-01 — `tests/test_m16_render_budget.py` added.** `services/twin_runtime.py` — the whole
  live path from M15 — had no tests at all. 13 of them; three fail against the pre-fix budget,
  which was checked by reverting it rather than assumed.

- **2026-10-01 — the `variants` lookup uses both halves of its key.** `services/studio._stimulus`,
  `services/agent_config`, `services/validity._paragraphs_for` and `services/lab.scenario_paragraphs`
  all selected on `version_code` alone and took the newest row by `created_at`. `variants` is keyed
  `(version_code, style_version)`; harmless while only v1 existed, but from the v2 bump it meant a
  twin could be shown a v1 paragraph while the app ran v2 — a stimulus verified under a contract it
  was not written to, invisible in the data because the row reads `passed = true`. Mechanical, not a
  research decision: a lookup on half a compound key is wrong. A *historical* run is still read by
  `variant_id` (`services/results.py`), which is what keeps `docs/09` §2 true when the contract
  moves again.

- **2026-10-01 — `_rerender_cell` no longer re-rolls a lever that had nothing to repair.**
  `_repair_for` documents `None` as "it missed nothing", but that `None` was passed straight to
  `rerender`, whose no-instruction branch **deletes the row and re-renders from the brief**. Since
  the loop covers every non-zero lever in a failing cell, one failing lever discarded and
  re-sampled every *other* lever's paragraph, spending each one's single durable re-render on a
  blind re-roll of text that had already passed. Observed: `L2` dial 1 stored at grade 9.87 — a
  clean pass — sitting at `attempts = 2`, and `L1` dial 1 measured 13.26 in isolation but stored at
  17.79. **This is the mechanism behind `HANDOFF_M15_LIVE_PATH.md` §2.4's "the targeted re-render
  made several of these WORSE" (`L1` dial 1: 11.48 before, 18.07 after),** which was read there as
  the repair failing to converge. Mechanical: the docstring already stated the intent, and
  `rerender`'s no-instruction path had exactly one caller which only ever reached it in the wrong
  case.

- **2026-10-01 — `HANDOFF_M15_LIVE_PATH.md` §2.4 item 3 was wrong, and the `L5` dial 1 refusal is
  correct.** M15 concluded the `cannot_render` on the disparagement commitment was "the model's own
  misreading, not a data defect", on the strength of a difflib sweep finding no overlap. That sweep
  compared **`L4` dial 2's** allowed set against its own do-not-say list; it never looked at `L5`.
  `L5` dial 1 must state its own `5.1.c` ("Remove the disparagement ground for deactivation...")
  while `4.1.d` ("Remove disparagement... from the grounds for deactivation...") sits in its
  do-not-say list. The brief asks for a sentence and forbids it in the same breath. **Not fixed —
  it is a research decision** (the gap register is frozen and rule 8 forbids renumbering); the
  options are in `HANDOFF_M17_VALIDATION_PLAN.md` §5.1.

- **2026-10-01 — containment fires on a contentless bigram, and this is NOT fixed.** `1.1.a` hit
  5 of 6 H3 codes on the distinctive pair `("rather", "leaving")`: `1.1.a` says "makes up the
  difference **rather than leaving** the loss with the driver" and the `L3` dial 2 paragraph says
  "treat drivers they supply **rather than leaving** responsibility to you". The 2026-09-30
  narrowing drops pairs *shared between forbidden commitments*; this pair is unique to `1.1.a`, so
  it is non-distinctive in the sense that matters and distinctive in the sense the code measures.
  Same class as the `("driver","app")` false positive, different mechanism. **Left open on purpose**
  — every repair makes the detector less sensitive and false negatives are the undetectable
  direction I3 exists to prevent, which is the same reasoning `HANDOFF.md` §0.7 item 3 records.
  Options and the sweep to measure them: `HANDOFF_M17_VALIDATION_PLAN.md` §5.2 and §6.2 T-4.

## M18 — the usability pass, and the Studio override

`ARCHITECTURE_UPDATE.md`, executed 2026-10-01. §1.1 and §1.2 are **researcher decisions** recorded
here because they move a documented rule; everything else is mechanical.

### Researcher decisions carried into the code

- **2026-10-01 — Twin Studio results may feed analysis, for the dialled-version path only.**
  *"by overwrite, it's ok for the studio values to feed analyses"* (`ARCHITECTURE_UPDATE.md` §1.1).
  This narrows `docs/01` §6.9's blanket quarantine, and it is satisfiable **without breaking
  `CLAUDE.md` rule 6**: a Studio ask *appends* a `sessions` row, a `runs` row with
  `origin='studio'` and one `twin_answers` row, and `services/results.completed_runs` already takes
  the latest run per `version_code` by `started_at` descending — so a later Dial board run
  supersedes the Studio value automatically, with no precedence logic to write or get wrong.
  What it costs is that a version whose most recent run is a Studio run reports an index over **one
  twin**, while `00000` and `SHAM` — the noise floor a lever effect must clear — come from the frozen
  panel. The two are therefore not the same quantity, so `runs.origin` and `twins_n` are shown on
  the Results table, in the side panel's step 7 and as an explicit `n = 1` badge above the panel's
  numbers (§4.3 item 4). `docs/01` §6.9 is **not** rewritten — `services/studio.py`'s docstring
  states where the wall now runs and points here.
- **2026-10-01 — three walls did not move, and are each asserted.** A **custom free-text change** is
  still fully quarantined and is now the only such path: it bypasses the lookup (I1) and the Checker
  (I3) by construction, is not one of the 243, has no `version_code` to be latest for, and never
  reaches `file_studio_run`. A Studio run writes **no `session_panel` row** and is never inheritable
  by a rerun (I14 is about frozen panels; a Studio ask has none, so `panel_size` is 0 and not 1).
  `twin_quality_runs` and `validity_results` remain unreachable from `services/studio.py` entirely —
  a Studio write to either would be a twin tuning its own admission.
- **2026-10-01 — the model is `gpt-oss:120b` only.** *"no its gpt oss only"* (§1.2).
  `config/agents.default.yaml` already said so for all five agents; the stale `agent_configs` row
  showing *Mistral / `mistral-small-latest` / temperature 1* was also **invalid against the code** —
  `ModelRef.provider` is `Literal["ollama", "openai", "mock"]` and has no `mistral` member, so
  `load_agent` raised constructing it. Corrected as a reproducible seed correction
  (`agent_config.correct_stale_models`, run from `startup_check`), which resets the row from the
  YAML, bumps the version and appends an `agent_config_history` row — not by hand in the UI.
- **2026-10-01 — `sessions.purpose` added, taking `ARCHITECTURE_UPDATE.md` §7 option 1.** Studio
  asks now write to `runs` and `twin_answers`, so smoke-test rows and study rows share a table. A
  test session is *marked* at creation rather than inferred later from `sessions.config.panel_size`:
  option 2 works but requires a future reader to know to look, and a convention nobody is told about
  is not evidence hygiene.

### Mechanical

- **2026-10-01 — the Agents tab's `gr.Timer` is off when nothing is running, and 5 s when something
  is.** It was `gr.Timer(3.0, active=True)` with seven outputs including the whole log-tree HTML and
  the agent-card HTML. Gradio replaces every returned output's DOM subtree whether its value changed
  or not, so scroll position reset, open elements collapsed and focus was lost every three seconds,
  forever, on an idle page — and the ~13 reads per tick are the source of the `ConnectionTerminated
  (last_stream_id:133)` and `WinError 10035` pair. `_poll` now carries a fingerprint in a `gr.State`,
  returns `gr.skip()` for **every** output when nothing moved, and does not even issue the three
  expensive reads in that case. `docs/06` §3.1 asks for a job line kept current; nothing there asks
  for a full re-render every three seconds. **Degradation recorded per `CLAUDE.md`:** the status card
  and the agent cards refresh on the tick that moves the event log rather than on a fixed interval,
  so a change made in another tab (adding twins in the Generator) appears on the Agents tab at the
  next log event or the next page load rather than within three seconds. No specified element was
  dropped.
- **2026-10-01 — database concurrency is bounded and HTTP/2 is off on the PostgREST client.**
  `supabase-py` is synchronous and every call runs through `asyncio.to_thread`, so one `httpx`
  client — one HTTP/2 connection — was shared across an unbounded thread pool.
  `settings.max_concurrency` bounds the *provider*; nothing bounded the database.
  `SupabaseBackend` now holds a semaphore (`settings.db_max_concurrency`, default 4) **per event
  loop**, because `startup_check` runs four separate `asyncio.run` calls before Gradio's loop exists
  and an `asyncio.Semaphore` binds to the first loop it blocks on. HTTP/1.1 keep-alive suits many
  small sequential requests and the study's query volume never needs multiplexing
  (`settings.db_http2_disabled`).
- **2026-10-01 — the database retry loop classifies before it retries.** It caught bare `Exception`
  and retried everything four times with exponential backoff, which is why one blocked delete
  printed the same foreign-key violation four times across ~5 seconds. A SQLSTATE in class `23`
  (integrity), `22` (data) or `42` (syntax/access), a PostgREST `PGRST2xx`, or a
  `TypeError`/`AttributeError` from this module's own filter map is **deterministic** and is raised
  on first occurrence with the constraint name intact. Transport failures, 5xx and 429 are retried;
  **anything unrecognised is treated as transient**, because a dead session costs more than three
  wasted retries. The loop lives at module level as `retrying()` for the same reason `paged_select`
  does — `tests/conftest.py` forbids constructing a `SupabaseBackend`, so a policy on the method
  alone would be untestable.
- **2026-10-01 — `_parse_ddl_columns` accepts a wrapped `alter table`.** Its `add column` regex used
  a literal space, so `alter table x` + newline + `  add column …` was silently dropped from the
  in-memory mirror — exactly the drift the function is derived to prevent. Caught by migration `004`.
- **2026-10-01 — deleting synthetic surveys counts its blockers first, and takes `studio_runs` with
  it.** Three tables reference `twins(twin_id)` without `on delete cascade`. `twin_answers`
  (evidence, rule 6) and `session_panel` (I14) **block**, with a sentence naming the twins and
  offering to delete the rest; `studio_runs` **goes with the twin**, because a sandbox conversation
  about a twin that no longer exists is not evidence of anything. Previously `studio_runs` was simply
  never considered — the docstring reasoned carefully about `runs` and concluded "no run is touched",
  which was true and was not the problem. A blocked twin keeps its submission and its answers too: a
  twin whose answers were deleted is no longer a lossless reconstruction of anything (I6), so "cannot
  be deleted" means the whole record. Without `skip_blocked`, **nothing at all** is deleted — a
  partial delete the researcher did not ask for is worse than a refusal.
- **2026-10-01 — eligibility is checked before a `sessions` row is written.** `start_sweep` created
  the row, spawned the task, and *then* the panel draw failed, leaving a permanent session row for a
  job that never ran. `services.runs.check_eligibility` is a pure read returning
  `(eligible, total, quality_passed, by_source, reason)`, and `start_sweep`, `ask_twins` and
  `resume_session` raise a typed `NotReadyToSweep` from it before `SessionRepo.create`. The message
  names the **real** blocker: "0 of 50 twins have passed the quality test … Population is 'real' and
  the twins you have are all 50 synthetic". `resume_session` skips the check when the session already
  has a frozen panel, because I14 means that panel is read and never redrawn.
- **2026-10-01 — a background session death is written to `run_events`.** `_spawn`'s done-callback
  called `log.error` and nothing else, so an `InsufficientEligibleTwins` the researcher needed to
  read appeared only in a terminal they were not looking at. It now also emits a `status="error"`
  event under the session id and marks the session `failed`, so the failure appears in the log tree
  they are already watching. The reporter swallows its own failure: an exception raised while
  reporting an exception loses both.
- **2026-10-01 — the sweep population is an explicit control, defaulting to the stored value.**
  §1.3 is still open — which population a *study* sweep runs on is a research question — so nothing
  picks one. The confirm step shows a `real / synthetic / both` control defaulting to `'real'` (the
  DDL default and what the code has always used) with the live counts beside it
  (`real: 0 · synthetic: 50 · manual (never on a panel): 0 · passed the quality gate: 0`) and a
  readiness line that re-pre-flights on change. A synthetic-only database is deliberately **not**
  defaulted to `synthetic`. The quality gate shows no population control, because it is what
  *produces* quality-passed twins and has no panel.
- **2026-10-01 — the quality budget explains itself; the number does not change.**
  `6 × 2 × 50 = 600` is correct: the 6 is the six Part-17 stimuli at one model call each, reading
  three holdout items per round (`docs/08`'s 18 H3 numbers), **not** a repeat count. It read as a bug
  because the total appeared with nothing beside it. `BudgetView` gained `breakdown` and `per_unit`,
  and `budget_summary` renders them under the total. The sweep budget's breakdown names `00000` and
  `SHAM` for the same reason.
- **2026-10-01 — Twin Studio can render a version on demand.** `services/studio._stimulus`'s refusal
  stays, because I3 has no sandbox exemption; what was missing was a way to *produce* a verified
  variant, since the only route was running the whole frozen panel from the Dial board to answer a
  one-twin question. `start_render` enqueues and returns (rule 12), emits into `run_events`, and
  **reuses `twin_runtime.render_and_check` unchanged** — same cache key
  `(version_code, style_version)`, same durable re-render budget, all five Checker gates. It is a
  net *saving*: a later Dial board run for the same code hits the cache. The budget is shown first
  (`docs/06` §9). A failed variant is stored **with** its verdict, matching
  `orchestrator/loop._render` and `services/quality`: what blocks a stimulus is `checker.passed` read
  at the use site, and a stored failure is what makes `docs/03` §5's "re-render once, then halt that
  cell" actually halt.
- **2026-10-01 — `runs.origin` is written on the INSERT, never stamped by an UPDATE.**
  `RunRepo.get_or_create` takes `origin` (default `'sweep'`). Relying on the DDL default would leave
  the column correct only because Postgres filled it in, which the in-memory mirror does not
  reproduce; and an UPDATE to a `runs` row — even one created a line earlier — is the shape rule 6
  asks nobody to reason about case by case. `tests/test_m11_studios.py` asserts
  `services/studio.py` contains **zero** UPDATEs or DELETEs on `runs`, `twin_answers` or
  `studio_runs`.
- **2026-10-01 — `studio_runs.is_latest_for_twin_version`, flipped by an RPC.** §4.4. The key is
  `(twin_id, coalesce(version_code,''), coalesce(custom_change,''))`: a custom free-text ask has no
  version code by construction, so two different custom changes for one twin are two different
  questions and both are current. The demote and the insert are one transaction, as
  `runs_complete` and `quality_run_record` are — otherwise a crash between them leaves either two
  current rows (which the partial unique index refuses) or none (which reads as "never asked").
- **2026-10-01 — the Twin Interviewer panel was showing its input instead of its result.** Its
  answers table was headed *"what this twin's **driver** answered"* and listed the baseline — the
  survey vector the twin is anchored on. The screenshot asks for *"Some of the 37 answers it gave"*.
  `twin_test_view` now returns the twin's vector as `answers` with the driver's value in a second
  column (as the Checker panel does), and the comparison is **one row per instruction variant** with
  `Answer checked?` (the contract/range verdict `run_answer_ladder` already computes), the six
  metrics and the rationale — not the transposed one-row-per-metric table it was. It also runs the
  saved prompt even when there is no edit, since a test screen that asks the twin nothing unless you
  edit the prompt is not a test screen; and a prompt that fails is a **row** with its reason, not an
  early return, because "the saved prompt failed and the edit did not" is exactly the comparison the
  screen exists to show.
- **2026-10-01 — `twin_test_view` compares the edit against the *resolved* prompt.**
  `AgentConfig.system_prompt` is the unresolved `file:twin.md` reference and the textarea holds the
  resolved text, so comparing against it meant an untouched box always looked edited — and the panel
  would have run the same prompt twice and presented it as a comparison.
- **2026-10-01 — Policy Designer's `Text used` is the rendered paragraph.** It joined
  `lever.bullets`, which is `told_summary` — the researcher-facing list `variant/lookup.py` is
  explicit *a twin never sees*. Not cosmetic: it made two artefacts `docs/03` §4.3 keeps deliberately
  apart look interchangeable on the one screen whose job is to show what the design agent produced.
  Both are shown, in columns named for what they are. Added: labelled **Wording A / Wording B**
  blocks (wording is a real experimental factor — validity test 5 — and B is the reversed paragraph
  order `ask_items(reverse_order=True)` shows a twin, derived from the stored paragraphs and never
  re-rendered, per `docs/09` §2); and a read-only **Versions it would test next** `Version | Why`
  table from the odometer, whose `Why` column says these are the next odometer positions rather than
  an agent's choice — six is not a sampling scheme the orchestrator knows about (`CLAUDE.md` rule 9).
- **2026-10-01 — Run Manager previews the log it would write.** Five lines, one per agent, in
  `run_events`' own `stage` vocabulary so the preview is of the real thing. Pure, and screenshot 7 is
  explicitly a dry run: `manager_log_preview` creates no session and makes no model call.
- **2026-10-01 — the Quality Checker's two threshold rows carry their `must be …` caption from the
  live config,** not from a number written into the screen, and the `Decision` line states the rule
  as the conjunction it is (`validity/quality.h3_verdict`, validation-plan D-4 — verified: it is
  `mae <= mae_max` **AND** `pct_within_1 >= pct_within_1_min`). A hard-coded `1.0` beside a changed
  threshold would be the screen disagreeing with the data.
- **2026-10-01 — the *What was changed* log carries the model, off each row's own snapshot.** §5.6.
  The model was the missing field and it is the one that makes the log answer what it is read for.
  Read from the snapshot rather than from the current config, so a later edit or seed correction
  cannot retroactively change what an old entry says it was saved with — which is the only reason an
  append-only audit log is worth keeping. Agent names are upper-cased, as the screenshot has them.
- **2026-10-01 — the provider dropdown is built from `ModelRef.provider`'s `Literal`.** A
  hand-written list let `Mistral` be offered on a screen whose model rejects it, so the screen could
  produce a row `load_agent` cannot construct. Same reason `db/client.TABLE_COLUMNS` is derived from
  the migrations. `load_agent` also now falls back to the seeded config, with a WARNING, when a
  stored row does not validate — a repair the damage prevents is not a repair, and the seed is what
  the runtime actually loads.
- **2026-10-01 — the `tl-note-strip` class.** The Studio's "filed as a result" line and the Results
  panel's `n = 1` badge are **not** warnings: a Studio number is a real measurement over one twin,
  and what the badge says is which quantity it is. Rendering them in `tl-warn-strip`'s red would read
  as "this number is wrong", which is the opposite of true and would train the researcher to dismiss
  it.

- **2026-10-01 — a twin the quality gate dropped can be asked in the Studio but is never filed.**
  **Not in `ARCHITECTURE_UPDATE.md`; raised by it.** §1.1 lets a Studio ask become a result, and
  `services/studio.studio_twins` deliberately offers *every* twin including the ones the gate
  dropped — that asymmetry is the stated point of the screen. Together those two would put a
  dropped twin's answer into the analysis, and `docs/03` §9.1 is explicit that a twin that failed
  the gate is dropped from the panel **and from all cells**. The plan does not decide it, so the
  conservative reading of the existing invariant is taken: `_require_quality_passed` refuses the
  *filing*, the ask still happens and is kept in `studio_runs`, and the screen says which. A manual
  twin has no quality run either, so this subsumes that case. **Flagged below** — the alternative
  reading is the researcher's to take, and it is one line.
- **2026-10-01 — Twin Studio's standing caveat card was rewritten, because it had become false.**
  It said *"Studio runs are stored separately and never enter the results, the index or
  Statistics"* — the most load-bearing sentence on the screen, and after §1.1 untrue for the
  dialled-version path. It now states each path separately: dials are recorded as a result and
  marked *Studio* with `n = 1`; a change you write yourself is never recorded; a hand-built twin has
  no driver to compare against. The "twins the gate dropped can be inspected here" line gained what
  it now also means.

### Still open after M18

- **The sweep population (§1.3 / §11).** Handled non-blockingly: made explicit and visible, never
  defaulted by code. It becomes a real decision the first time a study sweep is run.
- **Agent Studio edits a row the runtime does not read.** Every agent is constructed from
  `agents/registry.default_agent_configs()` — that is, from `config/agents.default.yaml` — at the call
  site (`twin_runtime`, `variant/render.py`, `variant/checker.py`), and the twin's temperature comes
  from `app_config['twin']` on top of that. So the `agent_configs` row Agent Studio saves is an
  editable, audited **record**, not the configuration in force. §5.5 item 3 offered two remedies —
  show the value actually in force, or make the box authoritative — and the first was taken, because
  which file a model id is read from is frozen onto every run by I11 and changing it mid-study is a
  research decision, not a screen fix. `agent_config.in_force()` reports what runs and where each
  value comes from, and the panel states it. **Raised for the researcher**, because the larger
  question — whether editing an agent in the UI should change what a sweep runs — is theirs.
- **Should a Studio result from a quality-dropped twin be filed?** Refused for now (above), on the
  conservative reading of `docs/03` §9.1. The case for allowing it is that `origin='studio'` and
  `twins_n` are on every surface, so a reader can judge it; the case against is that the gate exists
  precisely so that judgement does not have to be made per number. **Researcher's call.**
