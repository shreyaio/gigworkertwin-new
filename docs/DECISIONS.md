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

## M19 — the system audit and remediation (`SYSTEM_AUDIT_AND_PLAN.md`)

The three research questions of §3.2 were **put to the researcher and answered on 2026-10-03**;
they are recorded here as taken, not as chosen by the agent.

### Researcher decisions, 2026-10-03

- **Q1 / WP-1 — the word band is a function of the commitment count, and `style_version` → `v3`.**
  One band `[45, 150]` served sets of 2 to 8 commitments, giving `L1` dial 1 seventy-five words per
  commitment and `L3`/`L4` dial 2 nineteen. The design prompt asks for each commitment in its own
  short sentence and the Checker probes each one for entailment, so at eight commitments the model
  had to compress and the compression lost the entailments — permanently, because the one durable
  re-render was already spent. The formula is `word_min = 15 + 18n`, `word_max = 25 + 30n`, clamped
  into `[45, 300]`, and it is **calibrated against the eight paragraphs this project actually
  rendered**: it accepts all six that passed and rejects both that failed, for being too *short*.
  Bumping to v3 restores the paragraph budget by the principled route — the cache key contains
  `style_version` — rather than by hand-editing a counter.
  **The confound this makes explicit:** paragraph length now varies systematically with dial, about
  90 words at dial 1 against about 180 at dial 2. That was already true under v2's unverified 150
  and is unavoidable, since more commitments is more text; the formula makes the covariance
  declared and deterministic rather than leaving it to be whatever the model compressed to.
  **It belongs in the paper's limitations**, and §7.2 item 3's question — whether the analysis
  should carry a word-count covariate — is still open.
  Rejected alternative: `paragraphs_per_lever: 2` at dial 2, which changes the *shape* of the
  stimulus between dials rather than its length, a larger confound than the one it fixes.
- **Q2 / WP-3 — the quality gate asks all six Part-17 versions in one call.** Six calls per repeat
  became one. The argument is **fidelity, not cost**: `docs/01` §3.6 describes Part 17 as one
  section of one questionnaire, "18 items: six versions × three questions", answered in one sitting
  by a respondent who could see and compare the six worlds, and `docs/08` §3.3 scores the twin on
  Pearson `r` **across** the six — on whether it *orders* them as its driver did. A respondent
  orders by comparing; a twin asked in six isolated contexts cannot. The saving (9,000 calls → 1,500
  at N=500 × 3) is a consequence.
  **Six-in-one-context and six-in-isolation are different measurements and cannot be pooled.**
  `twin_quality_runs.detail["protocol"]` records `h3_single_call_v1` on every row, the Validation
  tab names it, and a table carrying two protocols says so rather than averaging across them.
  `twin_quality_runs` was empty, so there is nothing to migrate.
- **Q3 / WP-5 — the Dial board asks an editable panel size, with a "use every eligible twin"
  preset.** Reading (b) of the plan: the panel stays **frozen** at the chosen size, so every cell in
  the session is answered by the same twins and the indices remain differenceable against each other
  and against the `00000` and `SHAM` floors (I14). Reading (a), a census with no frozen panel, was
  declined — its index is not differenceable against a sweep cell. `panel_size` became a
  `TwinConfig` field, so it is versioned on write and frozen onto every run; `PANEL_SIZE` in the
  environment is now only the seed it starts from.

### Mechanical, taken here

- **2026-10-03 — a stored *failing* variant caches the verdict, not the attempt (WP-2, D1).**
  `render_and_check` short-circuited on **any** stored row, and the gate stores a report pass or
  fail. Each half is defensible and documented; together they made a cell that failed once fail for
  ever, with no path in the application to clear it and nothing on screen distinguishing "genuinely
  unrenderable" from "unlucky once in September". No document specified that behaviour — it was an
  accident of two independently correct lines. It now re-renders when the stored report did not pass
  **and the durable paragraph budget allows it**, and the budget is read *before* anything is
  re-assembled so an exhausted re-entry costs zero model calls — not even a coverage probe. I3 is
  untouched: the refusal is at every read of a non-passing variant, and this re-opens the attempt,
  never the verdict. A re-entry emits a `run_events` row, so a free second press says that it was
  free.
- **2026-10-03 — the sham's word band is its lever's *dial-1* band, not a function of its own slot
  count (WP-1).** **Not in the plan; raised by it.** The plan says the sham's `n` is "the number of
  slots that lever announces", which is 1 or 2 — so four of five sham levers would have landed in
  `[45, 55]` while every live lever sits at `[51, 85]` or wider. `ARCHITECTURE.md` §5.2 requires the
  sham to render as "five ordinary paragraphs, **same word band and voice as a live cell**", and a
  sham that is the shortest cell in the study is recognisable as the control by length alone — a
  twin that can tell it is looking at a control is not measuring the demand characteristic the cell
  exists to measure. The dial-1 count is read straight out of the frozen `dial_lookup`, so the sham
  keeps its zero free parameters.
- **2026-10-03 — gate 3's band is passed per lever and a missing one raises (WP-1).** From v3 there
  is no global `word_min`/`word_max` to fall back on, so `build_report` takes `bands` and raises
  `CheckerMisuse` for a non-dial-0 paragraph it was given no band for. Grading against a guessed
  band and skipping gate 3 because none arrived would both let an ungraded stimulus reach a twin.
- **2026-10-03 — `_render_stimuli` renders and reports all six H3 codes, then halts (WP-4, D2).**
  The halt is unchanged and still correct — a twin scored on fewer than 18 items is a different
  measurement. What was wrong was the granularity: `12220` is first in `h3_version_codes`, so three
  renders that would also have failed were never attempted, and the researcher was told about one
  bad code when four of six were affected. `docs/08` §2.1 step 1 says render the six; it does not
  say stop at the first.
- **2026-10-03 — the H3 gate is costed at its own rate (WP-3).** An H3 call carries the persona once
  but six scenarios, so it is estimated at 20 s and 6,500 tokens in rather than the battery round's
  8 s and 2,300. `_budget` gained a `seconds_per_call` parameter; the tokens were already
  parameterised and the seconds were quietly the battery's, which understated the gate's wall-clock
  by about 2.5×. `ARCHITECTURE.md` §7.2 is explicit that no researcher should discover the cost of a
  long action by running one.
- **2026-10-03 — the validity task is held and its death is reported (WP-6, D4).**
  `enqueue_validity_test` returned a task the UI discarded, with no module-level set and no
  done-callback — the one background path in the codebase that did not guard against it, while every
  other one carries a comment calling it the documented failure mode. It is now held in `_TASKS` and
  a done-callback appends a `validity_results` row with `verdict="INCONCLUSIVE"` naming the
  exception. `INCONCLUSIVE` and not `FAIL`: the test did not fail, it did not run, and recording
  `FAIL` would put an opinion about the instrument into the evidence table on the strength of a
  traceback.
- **2026-10-03 — `_paragraphs_for` honours the Checker verdict (WP-6).** **An I3 hole the plan did
  not name.** The function's docstring said "Checker-passed"; its query filtered on
  `(version_code, style_version)` only and returned the latest row whatever its verdict, so a
  variant the Checker had *rejected* would have been handed to validity tests 4-8 and put to the
  panel. It was the third read site of a stored variant and the only one that did not check
  `passed`.
- **2026-10-03 — a validity test defaults to the newest session that has a *frozen panel* (WP-6).**
  It defaulted to the newest session of any kind, which on the study database was `Render 01000`
  (`kind='render'`, `panel_size=0`). A render session and a quality session have no panel by
  construction. Filtered by an actual `session_panel` row rather than by `kind`, because a session
  whose draw failed has the right kind and no panel.
- **2026-10-03 — `RoundPromptError` is caught where a twin round is made (WP-6).** It is a
  `ValueError` and was caught **nowhere** in the codebase, so a malformed round killed a whole
  validity test instead of that twin's turn in it.
- **2026-10-03 — the Validation tab's button is a refresh, and is named as one (WP-7).** The tab is
  a read-only view over `twin_quality_runs`; there is no separate validation run to start. It had a
  primary-styled `interactive=False` button with no handler, above a table whose empty state told
  the researcher to press it. The empty state now names the quality gate and counts what is missing.
- **2026-10-03 — Agent Studio's edits govern the runtime (WP-8).** This reverses the holding
  position recorded under "Still open after M18". The five call sites read
  `registry.live_agent_configs()`, which merges the stored `agent_configs` row over the YAML seed —
  the precedence `docs/09` §4 already defines for `TwinConfig`. The merge lives in
  `agents/registry.py` and the database read in `services/agent_config.py`, because `agents/` may not
  import `db/` and `variant/` importing `services/` would invert the layering.
  **I11 is strengthened, not weakened:** `sessions.config["agent_versions"]` freezes
  `{agent_id: version}` onto every session, gate and Studio ask, so two sessions under different
  agent configurations can never be silently compared — which is `ARCHITECTURE.md` §1.1's "frozen
  onto every run that used them", satisfied in the data. `validate_config` runs on every merged
  config, so a stored row cannot give the design agent or the twin a tool (I2, I6) or introduce
  `native` output (I13); a row that will not validate falls back to the seed **for that agent
  only**, logged once.
- **2026-10-03 — `enabled` gates the runtime, and the Quality Checker cannot be disabled (WP-8).**
  The flag had exactly one read in the whole codebase — a pill. Now: `design` or `twin` disabled
  fails loudly, `analyst` disabled uses the existing deterministic template with its
  `FALLBACK_PREFIX` and makes **no** model call, and `checker` is **refused at save**, naming I3 —
  disabling the coverage probe would let an unverified stimulus reach a twin, and a probe that did
  not run must never look like one that passed. Refused in the service rather than hidden in the UI,
  because the refusal has to hold for an API wrapper and a direct call too.
- **2026-10-03 — the twin's temperature has one owner, and Agent Studio says so (WP-8).** It comes
  from `app_config['twin']` because that is what a session freezes onto its config column and what
  validity test 8 sets. The box is read-only and carries the sentence; the state that must not
  survive is a control showing a number the runtime silently discards.
- **2026-10-03 — the agent cards name each agent's two steps (WP-8 item 6).** Presentation only. The
  researcher's instinct that the Policy Designer "doesn't really need a live AI model" is half
  right, and that half was invisible: choosing the commitment set is a frozen lookup over
  `dial_lookup.json` and `gaps.json` with no model in it (I1), and only writing it in Uber's voice
  uses one. Replacing the *rendering* half with a template was considered and **rejected** — it
  would turn the stimulus from Uber-voice prose into a bulleted list of commitments, which is a
  different experiment.
- **2026-10-03 — the Settings tab's save message states what is true (WP-9).** It said *"This does
  not change what the next session runs under yet… Edit the YAML to change behaviour."* That had
  stopped being true: `refresh_twin_config` reads the row, `load_twin_config` merges it, and
  `session_config` calls the refresh before every session. A researcher who believed the message
  edited YAML by hand — unversioned, unaudited, outside the `config_version` that
  `twin_quality_runs` records — which actively undoes the reproducibility chain the button exists to
  maintain.
- **2026-10-03 — `app_config['style']` disagreeing with `settings.style_version` warns at boot
  (WP-9).** The row is read by nothing, which is why it is dangerous: it is a second, wrong
  declaration of the render cache key sitting in the evidence database. A warning rather than a
  refusal, because nothing reads it and a stale row cannot produce a wrong stimulus;
  `ingest/seed_db.py` writes it from the YAML, so a reseed corrects it.
- **2026-10-03 — "Twin today" is labelled, and an unmeasured baseline is a sentence (WP-10).** The
  column is the twin's answers to the `00000` control cell — its noise floor, and what every shift
  on the screen is measured against. `00000` runs once per session by the orchestrator, so with no
  session run the column is empty for every twin and nothing said why. The header is now
  `Twin today (00000)` and `TwinPanel.baseline_state` carries `measured` / `not measured`, rendered
  as one sentence above the table rather than a column of dashes — a dash can be read as a zero,
  and I17 forbids rendering an unmeasured cell as anything that could be.
- **2026-10-03 — the demand floor is reported on the Dial board too, and an unmeasured floor is
  stated (WP-12).** **Not in the plan.** `ARCHITECTURE.md` §5.2 requires `SHAM − 00000` to be
  reported "alongside every live cell" and §9 that a cell below it is not interpretable. The Results
  panel passed `floor=`; the Dial board's cached-result path did not, so a researcher could read an
  uninterpretable index there as a finding. Separately, `floor=None` rendered as silence, which is
  indistinguishable from "it cleared the floor" — the same defect WP-10 fixed for the baseline.
  There are now three states: below the floor, above it, and not measured, each said plainly.
- **2026-10-03 — `test_m19_remediation`'s fixture saves and restores `services.config._override`.**
  WP-9's test saves `quality_runs_per_twin = 2`, and `refresh_twin_config` installs it as a
  **process-level** override — so the next test file in the run inherited it and
  `test_m6_twin_quality`'s assertion of the seeded 3 failed **in the full suite only**, which is
  the worst shape of test pollution to find. The save-and-restore pattern is
  `test_m16_settings_apply`'s, which already had it for exactly this reason. Recorded rather than
  quietly fixed, because a full-suite-only failure is worth knowing the cause of.

### M19 continuation — the two loose ends in `HANDOFF_M19_CONTINUATION.md` §2, 2026-10-04

- **2026-10-04 — a twin save no longer writes the in-force temperature into its `agent_configs`
  row (§2.2).** WP-8 item 5 made the box read-only; the save path still sent its value, so saving
  copied `app_config['twin']`'s number into the row and left two places holding it — the shape of
  problem the read-only box existed to remove. `ui/pages/agent_studio._save` omits `temperature`
  when `agent_id == "twin"`. The alternative — leave it, since `twin_agent_config` overrides the row
  regardless — was rejected: nothing ran differently either way, so the deciding argument is which
  state a future reader is misled by, and a row that silently mirrors a value it does not own is
  worse than one that visibly does not own it.
- **2026-10-04 — `save_agent` merges the nested `model` dict field-by-field instead of replacing
  it.** Required by the above (omitting `temperature` from a replaced dict would hand it to
  `ModelRef`'s default of 0.2, which is a *change*, not a no-op), and it fixes a latent defect of
  its own that was not in the plan: Agent Studio's save only ever sent `provider`, `name` and
  `temperature`, so **every save silently reset a stored `max_tokens` to 2048 and a stored `seed` to
  `None`**. A reset seed is a provenance loss (I11) and a reset `max_tokens` changes what the agent
  can emit. A partial `model` now means "change these fields", which is what every caller already
  assumed it meant.
- **2026-10-04 — `app_config['style']` is corrected by a one-row patch, not a reseed (§2.3).** The
  handoff left the choice open. A reseed is the destructive option: `ingest/seed_db.build_rows`
  rewrites `app_config['twin']` — on the live project at **version 3**, holding the researcher's
  0.25 twin temperature and `quality_runs_per_twin`, the live subject of validity test 8 — and every
  `agent_configs` row with it. So the row's value is read from `config/style_contract.yaml` and
  upserted alone, with its `version` bumped so the move is recorded. The boot warning in
  `services/config._check_style_version_row` stays, because the row can drift again on the next
  `style_version` bump.

### Still open after M19

- **The word-length confound (Q1).** Paragraph length covaries with dial by construction. Declared
  above and in the paper's limitations; whether the analysis should carry a word-count covariate is
  the researcher's call.
- **`quality_runs_per_twin` is 2, against `docs/08` §2.1's 3.** The reason for the reduction was
  cost, and WP-3 largely removes it: 3 repeats at 10 twins is now 30 calls instead of 180.
  **Worth revisiting.**
- **Twin temperature** is 0.25 in `app_config` against a seeded 0.7, chosen by neither measurement.
  Validity test 8 is what sets it, and WP-6 is what makes test 8 runnable. Do not pick it before
  then.
- **Should a Studio result from a quality-dropped twin be filed?** Unchanged from M18. Still the
  researcher's call, still one line.
- **The sweep population.** Unchanged from M18. WP-5 extends the explicit control to the Dial board;
  which population a *study* sweep runs on remains a decision taken at the moment of running it.

### Documents this supersedes, which need correcting at write-up

- **`docs/10`'s "the quality gate is the dominant cost of the study, not the sweep"** no longer
  holds arithmetically. After WP-3 the gate is 1,500 calls at N=500 × 3 and a full 243-cell sweep at
  K=20 is 4,915, so the sweep is now about 3.3× larger. The *structural* claim is unchanged and is
  what the comparison was ever for: the gate is paid on every consented twin, the sweep only on the
  frozen panel, so the gate is the cost that grows with fieldwork.
  `tests/test_m7_orchestrator.py::test_the_gate_scales_with_the_population_and_the_sweep_with_the_panel`
  pins both the inversion and the structural claim.
- **`SYSTEM_AUDIT_AND_PLAN.md`'s acceptance check A-2** asks for `items_n = 18` on each
  `twin_quality_runs` row. `validity.quality.average_scores` deliberately *sums* `items_n` across
  repeats — it is a count of measurements taken, so the verdict says how much evidence it rests on —
  so the correct figure is `18 × quality_runs_per_twin`. The code's reading is kept; **A-2's wording
  needs correcting.**
- **`docs/11` M5's word-band bullets** ("a 41-word or 80-word render fails `in_band`") are now
  superseded twice over: by the 2026-09-29 widening and by v3's per-commitment band. The intent —
  the gate rejects a render that is too short or too long, at both ends — is what
  `tests/test_m5_render_checker.py` asserts, against the three-commitment band `[69, 115]`.

## 2026-10-04 — Checker: word band and reading grade are informational (`style_version: v4`)

**Researcher decision.** Gate 3's word band and Flesch–Kincaid grade no longer fail a cell. They are
still computed and written to the report as `info:` notes. Forbidden terms, refusals, coverage,
containment and the dial-0 / sham checks are unchanged and still fail a cell.

**Why.** The band and grade measure style, not content. Both were rejecting paragraphs that differ
from the intended policy in no way that matters to a twin, and they were the most common cause of
the quality gate halting. **Bumped to v4** because a change to what the Checker enforces changes which
cached paragraphs are valid under the contract (I4).

**Not decided here.** Coverage and containment tolerance. I3 currently says one containment hit fails
the cell with no threshold; softening it needs an explicit amendment to I3 and its test, and is
pending the researcher's decision.

## 2026-10-04 — Containment is recorded, not enforced; coverage gets more repair rounds

**Containment (I3, amended by researcher decision).** A containment hit is detected on every render
and written to the report as `info: containment hit (recorded, not enforced)`. It does not fail the
cell. Reason: two predefined commitments can legitimately share wording, so a hit is not evidence of
a leak by itself. The hits remain in `checker.containment` so the overlap is visible in the data.
The I3 test was rewritten to assert this rule and that hits are still detected and reported.

**Coverage (researcher instruction: address the faults, do not tolerate them).** Not yet changed.
The L3 dial-2 and L4 dial-2 paragraphs have spent their two durable render attempts
(`RENDER_ATTEMPTS_MAX = 2`, mirrored as a DB check constraint and specified by `docs/03` §5 as one
re-render) while still missing `3.2.c`, `3.2.d` and `4.1.a`. Raising the budget needs a migration and
a `docs/03` change, so it is pending the researcher's decision.

**Not solved by this.** A dial-2 cell that still cannot be rendered (L5, the `5.1.c` / `4.1.d`
overlap in the frozen reference data) is still refused. That needs a reference-data decision.

## 2026-10-04 — `style_version: v5` (containment becomes informational)

Bumped because the Checker's enforcement changed (containment no longer fails a cell). Stored
`variants` and `lever_paragraphs` rows under v4 carry verdicts computed under the old rule, and the
gate replays a stored failing verdict verbatim, so without a bump the old failures were never
re-judged. v5 forces fresh renders and fresh checks under the current rules.

## 2026-10-04 — `style_version: v6` (forbidden terms are a warning)

Researcher decision: forbidden *terms* (`config/style_contract.yaml` `forbidden_terms`) no longer fail
a cell; they are reported as `info:`. The design prompt still names them, so the agent is still told
to avoid them. Forbidden *intensifiers* remain enforced. Bumped because the Checker's enforcement
changed (I4; see the v5 note).

## 2026-10-04 — `style_version: v7`: design prompt v2 (coverage by prompt, not by call count)

**Researcher decision.** Coverage misses are fixed in the design prompt, not by more model calls and
not by a higher repair budget. `design_v2.md` treats the commitments as a checklist, requires each
to be stated by its own substance, and asks the agent to check its draft against the list before
answering. Calls stay at one per lever. Rejected: one design call per commitment (raises calls for
every lever and changes the paragraph's shape).

Bumped because the design prompt is part of the style contract (`STYLE_KEYS_SHOWN`, I4). The stored
`design` agent row is saved to `file:design_v2.md` through `services.agent_config.save_agent`, so the
change is in the audit history. `design_v1.md` is kept, unedited.

## 2026-10-04 — `style_version: v8`: design prompt v3 (condensed, same meaning)

Researcher request: the prompt was too long. `design_v3.md` is `design_v2.md` condensed, with duplicate
statements merged (the coverage rule was stated three times, the forbidden-word rule twice). No rule
was added, removed or weakened. Bumped because the prompt text changed (I4). The stored `design` row
is saved to `file:design_v3.md` through `services.agent_config.save_agent`. `design_v2.md` is kept.

## 2026-10-04 — `style_version: v9`: coverage repair appends the missing sentences

**Researcher decision.** On a coverage miss, the one repair no longer regenerates the whole paragraph.
The same design agent (no new agent) is asked, once, for only the sentences for the commitments the
paragraph left out. Python appends them to the text already written. The Checker then judges the
combined paragraph. The repair is still the one `RENDER_ATTEMPTS_MAX` allows, so the budget is
unchanged at 2. Calls per lever are unchanged apart from the repair itself.

**Known limit.** If a cell also fails a non-coverage rule (a forbidden intensifier), the append does
not fix it, and that cell still fails. Bumped because the repair path is part of what the cache
represents.

## 2026-10-05 — Dial board wiring: budget counts stored paragraphs, resume takes the newest, runs push to the screens

**Mechanical fixes, no research decision changed.**

* *Ask the twins* now prices lever paragraphs from `lever_paragraphs`: a paragraph already stored for
  `(lever, dial, style_version)` costs nothing (`services/runs.py: missing_paragraph_calls`). The
  breakdown names the twin calls and the unwritten paragraphs separately. The twin figure is
  unchanged: three cells (the version, `00000`, `SHAM`) × panel size, one call per twin per cell.
* Resume takes the newest paused session by `created_at`. It used to sort by `session_id`, a uuid,
  so the button resumed an arbitrary session (`services/runs.py: paused_sessions`).
* Starting or rerunning from the Dial board wakes the Agents poll. A finished session writes a
  completion signal, which repaints the Dial board's cached result and reloads the Results grid,
  with no page reload (`ui/pages/lab.py: _LabSignals`). The idle-page rule (`ARCHITECTURE_UPDATE.md`
  §3.1) still holds: nothing polls until a session starts.

**Superseded by the 2026-10-05 amendment below.** The paragraph above said every session re-answers
`00000` and `SHAM`. That is no longer true.

## 2026-10-05 — Amendment: the control cells move into the quality test, and verdicts are config-matched

**Researcher decision.** Keep both controls, `00000` and `SHAM`. Answer each once per twin per config,
inside the twin quality test. No session asks them. Every session records its floors from its panel's
stored answers under its own config fingerprint. Remove the per-session control runs.

**Config matching.** A verdict and a twin's control answers are valid only for the config they were
made under (model, temperature, prompt, wording, battery, style version, kept thresholds). A twin
qualifies for the live config only with the latest H3 verdict under that fingerprint and both control
answers. The Dial board and sweeps, resume, the validity tests and the Studio all refuse on a
mismatch and say which config to re-run. Migration `005_config_matched_controls.sql`; the function
is `services/config_match.py`.

**Choices I made that you may want to change.**
* The Studio requires at least one validated twin under the live config, not that the twin it asks is
  one. A hand-built twin has no driver, so it can never pass the gate.
* A validity test on a mismatched session is INCONCLUSIVE and still appended, so the attempt stays on
  the record.
* Quality verdicts made before `005` have no fingerprint, so they qualify nobody. The gate has to be
  run again for the live config. That costs `2 + quality_runs_per_twin` calls per twin, once.
* The two control floors' prose is written by the deterministic template, not the Analyst, so a session
  makes no model call for them (`services/twin_runtime.py: _reading`). The numbers were never the
  Analyst's to produce (I12), so they are unchanged.
* Interactions and the headline interaction rows pair only tested versions. A control is not a dial
  vector, and pairing it raised `ValueError` and blanked the Results side panel (`services/results.py:
  shifts_by_code`).


## 2026-10-05 — Agent Studio: the wiring audit, and the three tests show the agent's own output

**Superseded in part by the 2026-10-05 revision below: the Twin Interviewer shows two columns and the Quality Checker shows a side-by-side, with no verdict and no model call.**

**What was wrong, found by reading the call sites.**
* A save of a prompt missing a mandatory section said *Saved.* and then every session silently
  ran the seed (`live_agent_configs` falls back per agent). `save_agent` now runs the skeleton
  check and refuses with the reason.
* A save reached the process only at the next session. `save_agent`, `restore_agent` and
  `set_frozen` now install the new config in the process before they return, so the Test buttons
  and the sessions read the same thing.
* `differs_from_seed` compared a file reference with a stored text and reported every saved row
  as different from the shipped default. It now compares the resolved prompts.
* The Quality Checker panel read the stored quality numbers and never ran the Checker's prompt.
  It now runs `agents/checker.run_coverage_probe` once per commitment on the paragraph the design
  agent rendered for the version, and shows the verdict and the reason.
* The Twin Interviewer panel showed the driver's answers and the six index metrics beside the
  twin's. It now shows the twin's answers, the `Answer checked?` verdict and the twin's reason, one
  column per instruction set.
* The Policy Designer panel showed the stored paragraphs. It now runs `agents/design` once per lever
  with a dial set, on the brief the render path builds, and shows what it wrote and its word count
  against the band. It writes nothing to `lever_paragraphs`.
* The three model-calling tests run as background tasks (`services/agent_config.start_agent_test`),
  and the screen reads the result with *Show the result*. A model call on the handler's own path
  is what `CLAUDE.md` rule 12 forbids, and the old Twin test was doing it.
* The analyst's bundle labels did not match `agents/prompts/analyst_v1.md`, which names `CODE`,
  `TEXT` and `COMBINATIONS`, and the bundle sent `CELL`, `SCENARIO` and `INTERACTIONS`. The bundle now
  uses the prompt's labels. Only the labels changed. The prompt was not edited.

**Left as it is, deliberately. These are research-validity questions, not mechanical ones, so they
are the researcher's to decide.**
1. **A design prompt edit does not reach paragraphs already in `lever_paragraphs`.** The cache is
   keyed `(lever, dial, style_version)`, which is I4's frozen key, so a saved design prompt governs
   only the paragraphs not yet rendered. Options: key the cache on the prompt hash too (a schema
   change to a frozen key), or bump `style_version` when the design prompt changes. The Policy
   Designer's note says this on screen.
2. **The H3 quality gate does not read the Studio's twin prompt.** `twin_runtime.H3_PROMPT_REF`
   swaps in `twin_h3_v1.md` for the six-stimulus round. An edit in Agent Studio governs the battery
   and the sessions, not the H3 gate.
3. **Twin Studio's free-text question prompt is hard-coded.** `services/studio.QUESTION_PROMPT` is
   not one of the five agents and is not editable in Agent Studio.
4. **`design_v3.md` says "numbered checklist"** and the brief sends a bulleted list. It is a frozen
   stimulus prompt, so a text change is a new version file, not an edit.

**Not converted.** The Results Analyst's test still reads the stored reading for a version. Its
input is a finished cell's computed shifts, which the Studio does not store, so re-running it is
not a small change. It shows the reading only, with the metric bars removed.

**The Run Manager's test is unchanged.** It is a plan built from counts and settings, and it calls
no model.


## 2026-10-07 — `show_baseline` default reversed to `false`: a twin no longer sees its own numbers

**Researcher decision, overriding the `docs/03` §8 design this project shipped with.** The earlier
text argued: *"Anchoring is deliberate and bounded. Showing a twin its own baseline numbers pulls
answers toward them — that is what keeps a twin recognisably its own driver. The bound on it is
`SHAM − 00000`, reported with every cell."* That argument was considered and rejected, not missed.

**Why it was reversed.** Debugging the validity tests (`docs/08` §4) surfaced that the bound was not
holding. In the one live session inspected (7 twins, `gpt-oss:120b`, temperature 0.25):

* The `00000` control — five "no change from today" paragraphs, baseline shown — returned the
  twin's own stored baseline on **all 37 items for 6 of 7 twins**. The control's index was exactly
  `0.000` in 3 of 5 control runs checked across the database.
* `SHAM` — five paragraphs restating existing policy as if new, same twins, same session — changed
  **10 to 26 of 37 items per twin**, with every one of the six metrics moving in the "improvement"
  direction.
* With the floor at `0.000`, every validity test judged against it (2, 4, 5, 6, 8) could not
  distinguish a real effect from the floor itself: any movement at all counted as "above the floor."
  Test 4 (`impossible version`) reported "57% of twins read the contradiction as an improvement,"
  which was arithmetically "4 of 7 twins moved happiness at all" — not a meaningful share.

**Why this isn't just noisy data.** The twin prompt (`twin_v1.md`) did not merely show the baseline —
it told the model, in words, that *"leaving a number exactly where it was is a real and common
answer"* and to *"move one only where the change would genuinely move this person's view."* That is
an explicit demand cue layered on top of a documented LLM failure mode: models shown a reference
number before answering measurably anchor to it (anchoring-bias literature, e.g. arXiv:2412.06593,
arXiv:2508.21137). The `00000` floor was not measuring the twin's natural stability; it was measuring
how well the twin followed an instruction to be stable. `SHAM − 00000` cannot bound a demand effect
when `00000` itself is manufactured by the same kind of demand cue the bound exists to catch.

**What changed.**
* `TwinConfig.show_baseline` default: `true` → `false` (`src/twinlab/models/twin.py`,
  `config/twin.default.yaml`).
* New prompt `twin_v2.md`, superseding `twin_v1.md`: drops the `<<<BASELINE>>>` input and the two
  rules about keeping or moving a prior number. A twin now answers each round the way it already
  answers H2 and H3 — from persona and scenario alone, with no earlier numbers in view. The twin
  agent's `system_prompt` in `config/agents.default.yaml` now points at `file:twin_v2.md`, and its
  `context_sources` no longer list `baseline_answers` as required.
* Three call sites that hard-coded `show_baseline=True`, bypassing the config entirely, were fixed to
  read the live `TwinConfig` instead: `services/twin_runtime.ask_panel_twins` (every validity test
  that makes a fresh call), `services/studio`'s battery-ask path (Twin Studio), and
  `services/agent_config`'s Twin Interviewer diagnostic (Agent Studio). Before this fix those three
  paths would have kept showing the baseline regardless of the config flip, silently diverging from
  what the main sweep actually does — the same class of defect as the Agent Studio temperature box
  already flagged in `ARCHITECTURE_UPDATE.md` §5.5.

**What this does not change.** `compute_shifts`/`compute_index` (`docs/07` §3–§4) are untouched: a
cell's shift is still the twin's stimulus-conditioned answer minus the **human's own real survey
answer**, read from `survey_answers`, never from a twin call. Removing `show_baseline` only removes
the baseline from what the *twin sees before answering*; it does not change what a shift is computed
against. H2 and H3 are unaffected — both already ran with no baseline (`docs/08` §2.1, §3.1).

**Consequence, and why nothing breaks silently.** `show_baseline` and the prompt's hash are both
inputs to `services/config_match.current_fingerprint`. Every twin's H3 qualification and both control
answers (`00000`, `SHAM`) are stamped with the fingerprint they were produced under, and
`run_validity_test` already refuses to score a session against a live config it no longer matches
(`services/validity.py`, the `RESEARCHER 2026-10-05` block). So every twin qualified before this
change goes stale automatically the next time anything reads `current_fingerprint()` — no twin is
silently reused under an instrument it was not qualified for. The quality gate (Agents → Run twin
quality test) needs to be re-run before a new sweep or a new validity-test pass under the new
instrument. Existing `runs`, `twin_answers`, `twin_quality_runs` and `validity_results` rows are
untouched (append-only, rule 6) and remain correctly attributed to the config that produced them.

**Still open, not decided here.** Test 3 (`docs/08` §4) compares a twin's H2 answers — which never
showed a baseline, by that test's own spec (§3.1 step 3) — against a "no-change" predictor that is
handed the human's exact baseline answer. That asymmetry predates this decision, is unrelated to it
(H2 never showed a baseline either way), and is not addressed here.


## 2026-10-05 — Revision: Twin Interviewer is two columns; Quality Checker is a side-by-side

**Researcher decision after a live run.** The earlier panels were too much. The researcher wanted:

* **Twin Interviewer: always two columns, for this twin and this version.** `Driver said` (the
  driver's own answer to each item) and `Twin said` (the twin acting on the stored, Checker-passed
  version). The shape is the same whether or not the prompt box was edited, so no saved-versus-edit
  columns, no `Answer checked?` column, and no reason. An empty box runs the saved prompt. A twin that
  gives no valid answer leaves its column *Not tested* and says so in a note; it is never filled with a
  number (I13, I17). `services/agent_config.twin_test_view`.
* **Quality Checker: the codebook policy beside how the design agent framed it.** One row per area: the
  commitments the codebook gives this version on the left, the stored paragraph the design agent wrote
  on the right. No verdict, no reason, and **no model call**, so the screen only reads (CLAUDE.md rule 3
  and rule 12 are then trivially met). `services/agent_config.checker_test_view`. The Checker's gate
  verdict is still recorded on the render itself; this screen does not restate it.

**Consequences the researcher should know.**
* The Checker prompt is no longer run from Agent Studio. Editing it changes the gate's future verdicts
  (`variant/checker` reads the live config through `run_coverage_probe`), but nothing on this screen
  will show that. If a
  side-by-side verdict is wanted back, it is a yes/no column added to this table, not a reason.
* The twin's rationale is no longer shown on the screen. It is still stored with the twin's answers.
* The Test buttons for the Twin and the Policy Designer still run as background jobs. The Checker no
  longer needs one.

## 2026-10-05 — Analyst test shows the computed numbers beside the reading

**Researcher decision.** The Analyst test shows the six movements, the index and the floors again, as
the metric bars the Results screen uses, above the analyst's reading. The earlier revision removed them
on the grounds that they were not the agent's output. The researcher wants them back as the reference
the reading is read against: the analyst is grounded on those numbers (I12), so the screen shows both.
Presentation only. The numbers are the stored, computed ones from `services/results.results_panel`, and
the analyst still makes no call from this screen. `ui/pages/agent_studio.py`, the Analyst branch of
`_test_panel`.

---

## 2026-10-07 — the noise floor becomes two measured levels, not `|index(00000)|`

**Found while auditing the six validity verdicts from session `7a1b78a6`.** Five of the eight tests
judge against the `00000` noise floor, and the floor they were judging against was `0.000`.

Two separate faults produced that, and the second survives the fix for the first.

**Fault 1 — the control echoed.** With `show_baseline: true` the twin was shown its own numbers and
returned them verbatim: all 37 items, 6 of 7 twins, every metric shift exactly `0.000`. That is the
decision above, and it is already reversed in `config/twin.default.yaml`, `models/twin.py` and
`twin_v2.md`. **It is not yet applied** — `app_config.twin` still reads `show_baseline: true` and
`temperature: 0.25`, and `app_config` is what runs. The YAML is a seed, read by `seed_db.py`.

**Fault 2 — the floor's functional form.** `noise_floor = |index(00000)|` is an **absolute value of
a signed mean**: `compute_index` applies `index_sign` and averages the six metrics, so a twin moving
up and a twin moving down cancel before the absolute value is taken. Every statistic the floor gates
is a **mean of absolute values**, and by Jensen `|E[X]| <= E[|X|]` — the floor could never exceed the
quantity it judged, so every floor-judged test was biased toward `FAIL` for reasons unrelated to the
twins. Fixing fault 1 makes this one *worse*, not better: unanchored twins scatter in sign, so the
index cancels toward zero while the mean-of-absolutes does not. Fixed first, so the `show_baseline`
change can be read for what it does.

**What replaced it.** `analysis.metrics.measure_noise_floor` measures from the control run's own
answer vectors and returns a `models.analysis.NoiseFloor` carrying both functionals the tests
actually compute — `cell` (mean over metrics of |mean shift|) and `twin` (mean over metrics of mean
|per-twin shift|) — each broken down per metric, because tests 4 and 6 judge a single metric and a
six-metric average is not that metric's floor. **Each test selects its own level**, beside its own
docstring, rather than the caller choosing: whether a figure is a mean-of-absolutes or an
absolute-of-a-mean is a property of the test. The mapping is tabulated in `docs/07` §6.1.

`demand_floor` is unchanged and stays signed — it is directional by design.

`twins_n` on `NoiseFloor` is `gt=0`: a floor measured on nobody is not a floor (I15's shape), and
`services.validity.noise_floor` returns `None` rather than a zero when the control has no stored
answers. A fixture that seeds only `runs.index_value` now describes a session whose floor was never
measured, which is `INCONCLUSIVE` — correctly.

---

## 2026-10-07 — validity test 6 gains a same-persona retest control; cost N → 3N

`fairness_with` and `fairness_without` come from two **separate model calls**. Their difference
therefore contains the twin's own call-to-call variance as well as any sensitivity to the ablation,
and the test had nothing to subtract that against. It could not distinguish *"the twin used its
fairness history"* from *"two calls to one twin differ"* — and would report `PASS` for a twin that
ignored its persona entirely, which is the opposite of what test 6 is asked to detect. On the study
database it reported `PASS` at 0.571 against a 0.000 floor, which is a verdict about nothing.

A third round asks the **unablated** persona the same question again. The comparator is
`max(retest, floor)`: the two are alternative explanations of the same difference, not components of
it, so they are not summed and not subtracted from one another.

`CALLS_PER_TWIN[6]` is 3 — with, retest, without — and `docs/08` §4's table says 3N. The retest runs
**before** the ablated round so a provider failure costs the control rather than the comparison.
`fairness_retest` is optional on `vt.ablation` so an outcome stored before this existed can still be
reconstructed; when it is absent the headline says so rather than implying the comparison was made.

---

## 2026-10-07 — two reported statistics added; no threshold moved

Both are **reported and never thresholded**, because changing a pass rule is a research decision and
`CLAUDE.md` says not to pick one.

**Test 1 — `between_person_distance`.** The mean distance between the two paired drivers' own
vectors on the same items. It is the gap a flawless twin would score: `mae_own = 0` leaves
`gap = mae_other`, which cannot exceed how far apart the two humans are. A gap of 0.4 reads very
differently against drivers 3 points apart than against drivers 0.8 apart, and without it on the row
those cases cannot be told apart afterwards. `gap_share_of_distance` is carried beside it. The
0.5-point threshold is unchanged. **Open question:** whether the threshold should be a share of this
distance rather than a fixed point value.

**Test 3 — paired 95% intervals** on `advantage_over_nochange` and `advantage_over_groupshift`,
computed with the same `paired_gap` machinery test 1 uses. The verdict stays the comparison of means
`docs/08` §4 specifies. A `FAIL` on nine twins is a claim about a difference and differences have
intervals; test 1, one screen away, already reported one for the same shape of quantity.

---

## 2026-10-07 — `metrics.noise_floor` removed rather than deprecated

It had one caller — `tests/test_m8_analysis.py`. The production floor has always been computed in
`services.validity.noise_floor`. Leaving a function that returns the old, biased number beside the
new one invites a future caller to pick the wrong one, and there is no stored value or external
contract that depends on the name.

---

## 2026-10-07 — the Settings screen is wired to `app_config`, and cannot write `show_baseline`

Applying `show_baseline: false` surfaced that the Settings tab was reading and writing the wrong
thing. `_settings_tab` evaluated `cfg = load_twin_config()` **while the Blocks were being built** —
before anything had called `refresh_twin_config`, so the process override was empty and `cfg` was
`config/twin.default.yaml`, the seed. Two consequences, both silent:

1. **Every control displayed the seed, not what was in force.** The screen showed `temperature: 0.7`
   and `quality_runs_per_twin: 3` while `app_config` held `0.25` and `2`. A researcher reading the
   screen was reading a file, not the instrument.
2. **Any Save wrote the seed's `show_baseline` over the stored one.** `_save` passed
   `show_baseline=cfg.show_baseline` into the `TwinConfig` it dumped to `save_settings`. So saving
   an unrelated field — a threshold, the panel size — would silently flip `show_baseline` back to
   whatever the YAML said. This is how `false` could sit in three files for a day while
   `app_config` went on running `true`.

**Fixed two ways, because one of them is structural.** `_refresh` repaints every control from
`refresh_twin_config()` on page load (`load_once`, off the render path per `docs/05` §8.4 rule 2),
and `_save` now re-reads the live row before validating. More importantly, `_save` writes only the
keys in `EDITABLE` — `temperature`, `wording`, `quality_runs_per_twin`, `mae_max`,
`pct_within_1_min`, `panel_size`. `save_settings` merges, so **a key the screen never sends is a key
it cannot clobber**, whatever a future handler does with the form. `show_baseline` is not in that
tuple and `tests/test_m16_settings_apply.py` pins it there.

`show_baseline` is now **displayed read-only** beside the environment-owned values. `docs/03` §321
makes it a researcher-set default rather than a UI control, and that is kept — but a value that
governs every twin round and appears on no screen is a value nobody can check.

---

## 2026-10-07 — `agent_configs.twin` pointed at `twin_v1.md`; which prompt ran depended on the process

`config/agents.default.yaml` had been updated to `system_prompt: "file:twin_v2.md"`. The stored
`agent_configs` row still said `file:twin_v1.md`, and `registry.live_agent` prefers the stored row
and falls back to the YAML seed only when `_LIVE` is empty. So **which twin prompt ran depended on
whether `refresh_agent_configs` had run in that process yet**: a session (`services/runs.py` calls
the refresh before every one) got v1, while a cold-start path got v2.

That split mattered more than a version number. v1 declares a `<<<BASELINE>>>` input and carries
rule 3, *"Leaving a number exactly where it was is a real and common answer"*, and rule 4, *"keep the
number you gave"* — the wording the entry above blames for the `00000` control returning the stored
baseline on all 37 items. With `show_baseline: false` the baseline block renders empty, so v1 would
have instructed the twin about numbers it was no longer being shown: worse than either consistent
option.

Aligned to `file:twin_v2.md` through `save_agent`, so it is versioned (`agent_configs.version` 1 → 2)
and appended to the agent history like any researcher edit, rather than written at the table. Both
resolution paths now agree and `resolve_prompt` returns `sha256(twin_v2.md) = 0dd86eba66e461d3`.

**The seed and the stored row are two declarations of one value and they drift.** The same shape as
`twin.default.yaml` vs `app_config['twin']`, and as `max_concurrency`. Nothing here detects it; a
start-up check that compares every seeded agent's prompt reference against its stored row would, and
is not built.

---

## 2026-10-07 — live config applied; every stored verdict is stale

`app_config['twin']` v3 → v4, `show_baseline: true → false`, written through `save_settings` so the
rest of the row is untouched. `agent_configs['twin']` v1 → v2. The config fingerprint moved to
`35411b382053eda1`; every session on the database was run under `a77e706099a4a7bd`.

By `docs/08` §2.4a **every H3 verdict and every stored control answer is now stale**, so no twin is
qualified until the quality gate is run again. That is the intended consequence, not a side effect:
the twins were qualified under an elicitation the study no longer uses.

`temperature` stays at the stored `0.25` and `quality_runs_per_twin` at `2`. Both are Settings-screen
values and are the researcher's to set from there (above); the YAML's `0.7` and `3` are seeds and are
deliberately not applied here.

---

## 2026-10-08 — validity test 7 costs `2N`, not `N`; the budget card had always understated it

`CALLS_PER_TWIN[7]` was `1` and `docs/08` §4's table said `N`. `_test_with_calls` has always asked
**two** full rounds — `purpose="model_a"` on the configured model, then `purpose="model_b"` on the
named one — so the confirm card a researcher presses OK on promised half the calls it spent. At a
20-twin panel that is 20 approved against 40 spent, serially, on a one-concurrent-request tier.

It cannot be reduced to `N` by reusing the sweep's stored answers for model A. `second_model`
compares a **paired** per-twin index, and the pairing only holds if both sides were asked the same
way in the same test — same seed, same wording, same stimulus. Reusing a sweep round would compare
two different elicitations and call the difference a model effect.

**The table is no longer asserted against its own literal.**
`test_the_call_table_matches_the_rounds_each_test_actually_asks` drives each of tests 4–8 with a
recording stub and counts the rounds. A table that restates itself cannot catch this class of
defect, which is how it survived; the same test now also covers test 6's `3N`.

---

## 2026-10-08 — `provider: "openai"` refuses instead of silently resolving to Ollama

`resolve_model` sent both live providers to `OpenAIProvider(base_url=settings.ollama_base_url,
api_key=settings.ollama_api_key)`, on the correct observation that Ollama Cloud speaks the OpenAI
wire format. The consequence was that selecting `openai` in Agent Studio **changed nothing**: the
call went to Ollama Cloud, with the Ollama key, and the run recorded `openai` as the provider it had
reached. A provider written onto evidence that the call never touched is a provenance failure (I11),
and it is invisible precisely because both endpoints answer.

`openai` now resolves against new, empty-by-default `OPENAI_BASE_URL` / `OPENAI_API_KEY` settings and
raises `ConfigError` while the base URL is unset, naming `ollama` as the thing that works. **Not
defaulted to the Ollama endpoint** — the default is what made it a no-op.

Nothing in the study uses it today. It is worth fixing now rather than when a second endpoint is
added, because at that point the failure stops being benign and starts being wrong numbers.

---

## 2026-10-08 — test 7's model name is checked against the endpoint, and the check fails open

`test_readiness(7)` checked only that the second-model box was **non-empty**. Test 7 asks model A
first, so a typo — `mistral-large-5` — passed readiness, spent a full panel of calls on the model
already in use, and only then died on model B. The death was handled correctly (an `INCONCLUSIVE`
row via `_report_validity_death`, never `FAIL`), but N serial calls had already been spent to learn
that a name was misspelled.

`agents.registry.served_model_names` lists the endpoint's catalogue once per process and caches it,
**including the failure**: the readiness line is repainted on every change of the session or version
dropdown, and one GET per repaint is a request storm against the endpoint the sweep is queued on.

Three properties, each deliberate:

* **Fails open.** `None` means "could not ask", never "serves nothing". A listing that is slow,
  blocked or unreadable lets the test run. This exists to catch a typo, not to become a second gate
  between the researcher and a test they are entitled to run — a check that can refuse wrongly costs
  more than the typo it prevents.
* **No key, no request.** Mock mode returns `None` without touching a transport, so `CLAUDE.md`'s
  "no live LLM in CI, ever" holds on a UI readiness path. This is load-bearing rather than
  theoretical: a developer's `.env` is on the path when the suite runs locally, so the guard is
  asserted by emptying the key and proving no transport is reached, not by assuming a clean
  environment.
* **Names the near miss.** `mistral-large-5` is refused with *"Did you mean mistral-large-4?"*,
  matched on the name's stem.

Readiness also now refuses the **currently configured model** as the second one: a model cannot be
asked whether a finding is a property of itself.

**What this makes possible, for the record.** The endpoint served 18 models when this was written,
including `mistral-large-4` and `mistral-large-3:675b`. A second model therefore needs **no second
provider and no code change** — test 7 overrides `cfg.model.name` and nothing else. Crossing model
families is the point; two variants of one base model agreeing with each other is not evidence about
the drivers.

## M22 — The hosted questionnaire (`/take`), 2026-10-08

Asked for directly: a page a driver can be sent a link to, whose answers land in the database and
the raw mirror, and whose persona is built by the existing deterministic path.

### The one research-affecting choice, made by the researcher

- **The questionnaire is hosted in the Space, overriding `ARCHITECTURE.md` §8.2 rule 2.** Rule 2
  puts intake in the Supabase Edge Function precisely so that a free Space sleeping after 48 hours
  idle cannot silently drop a driver's submission, and **hosting does not mitigate that**: a
  request that never arrives cannot be stored by code that is asleep. The researcher asked for the
  hosted path knowing this. The Edge Function path is untouched and still works; both now write
  the same rows through the same `build_rows`. For unattended fieldwork on a sleeping Space, keep
  the Edge Function configured as well — `services/surveys.HOSTED_SURVEY_NOTE` says so on screen.

### Mechanical choices

- **The hosted page is a third client of one intake contract, not a second pipeline.** It emits
  the same `"<section>|<title>"` payload the Apps Script emits, over the same `form_map.yaml`,
  into the same `build_rows`. `survey/instrument.py` refuses to build unless its question keys are
  **exactly** the map's keys, both directions: a drawn-but-unmapped question would be rejected at
  intake after the driver answered it, and a mapped-but-undrawn one is a question silently missing
  from the instrument. Both are rule 7 failures and both now fail at import.
- **73 of the 112 original questions are derived from `data/reference/instrument.json`,** not
  retyped — stem, scale, points and anchors. A second copy of frozen text is a copy that can
  drift from the register `survey_answers.item_id` is foreign-keyed to.
- **Nine stops.** The reference screens fix stops 1, 2, 3 and 5 (*Start*, *Check*, *Consent*, and
  Part 5's AMQ block headed "Part 4"), from which the "Part" label is one less than the stop index
  and the instrument's Parts 3 and 4 share stop 4. The rest follows. **No item moves relative to
  another**; only the page breaks are decided here. Parts 15–17 are one contiguous stop so the
  holdout material (I6) is one block rather than interleaved with persona material. The partition
  is `survey/instrument._stops` and nothing else depends on it.
- **`persona/from_payload.twin_from_payload` was lifted out of `services/lab.py` unchanged.** Two
  callers now need it; two copies is how an imported twin and a hosted twin come to carry
  different field shapes with no test able to see it.
- **`twin_gate` is one predicate used in three places** — the hosted submit, the Generator's bulk
  import and the Settings count. `importable_submissions` now applies it in Python rather than
  restating it as a database filter, so the single-row and bulk paths cannot drift.
- **Numeric answers are text boxes, not `gr.Number`.** Gradio renders a `Number` whose value is
  `None` as a box containing `0`, so a driver who skipped "how many people depend on your
  earnings?" would submit a zero — a real and very different answer. This was caught in the
  browser, not by a unit test, which asserted the Python-side value was `None` and passed. The
  Google Form sent these as strings too, so the two channels stay comparable through `build_rows`.
- **Nothing is written until the driver presses send.** No autosave and no draft table: the cover
  sheet says a driver may stop at any time and that no partial response is retained.
- **`/take` is a real route deliberately absent from `ROUTES`.** `global_nav` builds its strip
  from `ROUTES`, so this is what keeps a strip of links into the Dial board off a driver's screen.
  `PARTICIPANT_ROUTES` carries it instead, and a test asserts the separation rather than trusting
  whoever next edits the list.

### Degraded, and noted per `CLAUDE.md` → "When Gradio cannot do it"

- **Likert rows are restyled radios.** Gradio has no button-group control. The content — N boxes,
  one per scale point, numbered, selectable, with the anchors at the ends — is intact; only the
  mechanism differs. Below 560px the row wraps to four columns rather than shrinking tap targets
  below 44px, because a mis-tap is a data defect.
- **No "Skip this question" link,** which the reference screens show under each rating. Every
  battery item is already optional, so the control would do nothing; the probe's help text says
  the box may be left blank instead. Adding 37 no-op controls would be 37 more components to
  gather on every navigation for no change in what can be answered.

## The why-probe layer, 2026-10-08

Applies `additional_data/SURVEY_SCALES_AND_WHY_PROBES.md` §3, which the v2 instrument lists under
`not_yet_applied`. Both questions below were put to the researcher and answered.

- **34 new probes; PAC11, SAT1 and DEP1 keep the instrument's own part-level open questions.**
  §3.1 asks for one probe per Likert item, but `survey_answers.why_text` is one column per item
  and those three already carry richer, question-specific probes. The named three stay exactly
  where they are; the other 34 battery items get the constant probe. Nothing changes storage and
  no existing answer is reinterpreted. The instrument goes 112 → 146 questions.
- **The probe wording is constant across every item,** verbatim from §3.1. A per-item wording
  would cue content; a valenced one ("why are you unhappy with this?") would bias the persona
  toward grievance and propagate into every counterfactual the twin answers.
- **The map key carries the item's stem; the driver is shown the wording alone.** Five AMQ probes
  titled "Why did you choose that?" would collide into one `form_map.yaml` key and four answers
  would be lost. `Question.prompt` holds what the driver reads.
- **No probe on an attention check, a screener, a demographic, or Parts 15–17** (§3.2). An
  attention check has no experiential content to explain, and the counterfactual blocks are
  hypotheticals that are also holdout, so a why there could never be used.
- **`TEMPLATE_VERSION` v1 → v2, and the why is now inline on its own item's clause** (§4.2):
  *"I agree that my work schedule is made by an automated system. In my own words: '…'"*. Whys
  used to be grouped at the end of a block's section, which read well while there were three; with
  one per item it would put eleven unattributed "In my own words: …" clauses in a row at the end
  of the PAC section with nothing saying which rating each explained. **Every persona hash
  changes.** Confirmed acceptable — no fieldwork twins exist yet.
- **`GENERATOR_VERSION` v3 → v4.** The synthetic generator now answers all 37 probes rather than
  three, so a synthetic persona has the same shape as a real one. That is 34 further draws from
  the same RNG, so **a `v3` seed does not reproduce under `v4`**.
- **`form_map.yaml` v1 → v2**, and `supabase/functions/survey_intake/form_map.json` regenerated
  with `tools/gen_edge_assets.py`. Adding map keys cannot break the Apps Script contract test:
  `map_answers` fails on a payload key absent from the map, never the reverse.

## A tab left open across a restart, 2026-10-08

Reported during the first hands-on run: the Part 16 block drawn twice, and a bare red **Error**
chip on *Send my answers*. Neither reproduces on a freshly loaded page — the served HTML carries
`FAIRNESS` exactly once, stop 9 mounts exactly 238 radios, and a full walk-through submits and
returns a reference number.

The cause is a Gradio client holding the component tree it loaded with. The instrument grew from
112 questions to 146 when the why-probe layer landed, and the development server was restarted
several times with the page open; an open tab then draws the tree it cached and posts a value list
that no longer lines up with the questions. **Reloading the page fixes it.**

Two things changed so it cannot be cryptic again:

- **A value-count mismatch raises `StaleSession` and refuses.** The values arrive positionally and
  nothing identifies which question each belongs to, so a short list cannot be realigned — pairing
  the first *n* would file real answers under the wrong questions, which is a fabricated record
  and much worse than an error. Nothing is stored and the page says to reload.
- **Every handler failure is rendered on the page, never left to Gradio.** An uncaught exception
  reaches a driver as a red chip with no text; a researcher can read a terminal, a driver on a
  phone cannot. The wrapper names the failure and gives the remedy.

**Running the application locally writes to the live Supabase project**, because `.env` is
populated and `settings.db_configured` is true. Two test submissions were written to
`survey_submissions` as `data_type=REAL` during this work and both were removed, with their
answer rows and raw objects. Testing the hosted questionnaire now means pressing Send, so run it
against the in-memory backend instead:

```
SUPABASE_URL= SUPABASE_SERVICE_KEY= ./venv/Scripts/python.exe app.py
```

## "Already a twin" is not "nothing was eligible", 2026-10-08

Reported: a respondent who filled in the hosted questionnaire correctly, then *Import twins from
the survey* reporting **"Imported 0, skipped 1"** under the sentence *"Nothing was eligible."* The
twin existed the whole time, with a complete persona.

`docs/06` §3.8 asks for "imported / skipped / invalid", and `skipped` was defined as "already a
twin, **or** gated out". Those are opposite outcomes — one means there is nothing left to do, the
other means the respondent did not qualify — and the screen's explanatory sentence led with the
second. That was tolerable while every twin arrived through the bulk import. The hosted
questionnaire builds the twin when the driver presses send, so **every hosted respondent now
reaches §3.8 already imported**, and the wrong reading became the common one.

- `TwinImportResult` gains `already_twins` and `gated`. `skipped` stays as their sum, so §3.8's
  three counts are unchanged, but it is never reported on its own.
- The Generator says which happened, and reads as success when the only reason nothing was
  imported is that the twins already exist.
- **The snapshot of existing twins is taken before the import loop.** Taken after, every row just
  imported also reads as "already a twin" and is counted twice — caught by a test asserting
  `imported == 1 and already_twins == 0` on a fresh respondent.

### Tests could reach live Supabase Storage

Found while fixing the above: `conftest._no_live_database` refused to construct a `SupabaseBackend`
but said nothing about `SupabaseStorage`, and `get_storage()` builds one whenever
`settings.db_configured` is true — which it is whenever a developer's `.env` is on the path. A
twin-import test was reading raw objects from the researcher's real `raw-surveys` bucket. It
surfaced only because the object was missing and the 404 failed the test; a read that *succeeded*
would have been invisible.

`SupabaseStorage` is now refused the same way, and the per-test fixture installs an
`InMemoryStorage` beside the `InMemoryBackend` — paired, as `get_storage()` pairs them in the
application, because a live mirror behind an in-memory database writes objects nothing can read
back.

## The four human arms reach a real respondent, 2026-10-08

Reported: the quality run logged *"no recorded arm, so no H2 stimulus"* and skipped the first real
twin. The skip is correct — H2 must show a twin **its own driver's arm** (`docs/08` §3.1) — but the
cause was older and larger than the hosted questionnaire.

**No real-respondent intake path had ever assigned an arm.** `docs/01` §5 specifies a four-arm
between-subjects design; only `generator/synthetic.py` implemented it. The Apps Script and the Edge
Function both default `arm = null`, and the hosted questionnaire inherited that. The reason is
upstream of all three: **the instrument contains one arm's story.** Parts 15 and 16 carry `REP1`'s
text and `docs/GOOGLE_FORM.md` §4 says to paste that one, so there was never a second story to
show. H2 could not have run on a real twin at any point in the project's history.

Decided with the researcher:

- **Four arms, and the three missing stories are composed from the instrument's own frozen text.**
  Part 17 already states each lever's dial-1 commitments in driver-facing prose, and §5.1 maps each
  arm to exactly those commitments — `CON1` to `2.1.a–c`, `MGT1` to `4.1.a/b/d`, `REP1` to
  `5.1.a–c`. `ARM_STORIES` is therefore a derivation, not an authoring. `BASE` names the five
  levers so that "nothing changed" is as concrete as the three that did. **Treat as frozen
  instrument text.**
- Spelled out rather than spliced from `_COND_1` / `_MGMT_1`. Lowering the paragraph's first
  letter to follow the stem produced "…this is true: uber now provides safety equipment" — a
  lowercased proper noun in text a driver reads. A test pins each story to its lever paragraph.
- **The arm is drawn once, on leaving the demographics stop**, balanced within the driver's
  `city|service` stratum (§5.2) and counting **real** submissions only — generated data must not
  decide which story a real driver reads. Never redrawn: the arm decides the story, so a second
  draw could leave the story read and the arm stored disagreeing, which is undetectable afterwards.
- Approximate under concurrency, deliberately. Counts come from committed rows, so two simultaneous
  drivers can draw the same arm. Reserving at first page view would be exact and would also leak an
  arm to everyone who opened the link and left, which biases balance far more than a rare collision.
- **Hosted path only.** The Form path keeps its current behaviour; its `arm` stays null until the
  researcher decides to field it.

### `mc_correct` was false for every real respondent

Found while wiring the above. `survey_submissions.mc_correct` is
`generated always as (mc_answer = arm)`. Part 15 offers the four arms by **label**; `arm` holds an
**id**. Storing the label therefore made `mc_correct` false for every real respondent, silently and
permanently. The synthetic generator hid it by writing the id straight into `mc_answer`, so the two
paths disagreed about the column's contents and no test compared them.

`build_rows` now resolves the label to its arm id, and `rows.mjs` does the same so the two
implementations still agree over the fixture. An answer matching no arm is kept verbatim — it is
still what the driver picked, and `mc_correct` is simply false.

### A note on verifying against a running server

Four orphaned `app.py` processes were found holding port 7860; `pkill -f app.py` under Git Bash does
not kill native Windows processes, so several restarts during this work never took effect and some
checks ran against stale code. Kill by PID instead:

```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.py*' } | Stop-Process -Force"
```

## Deleting a twin, and the tables that reference it, 2026-10-08

Removing one hosted test respondent at the researcher's request was refused by Postgres with a raw
`23503`: `twin_control_answers` references `twins(twin_id)` with **no** cascade, and the twin had
answered the `00000` and `SHAM` control cells.

The same refusal applies to the Generator's *Delete synthetic surveys* button.
`CASCADING_TWIN_REFERENCES` listed only `studio_runs`, so with 40 control answers standing against
10 synthetic twins **the button could not have worked**. This is the second time that list has been
wrong in exactly this way — its own docstring records the first, when `studio_runs` was missed and
"six sandbox rows against one synthetic twin made the whole batch undeletable". `twin_control_answers`
arrived in migration 005 after that fix and was never added.

- `twin_control_answers` and `twin_quality_runs` join the list, plus `survey_responses`, the
  superseded v1 table, which the new coverage test found.
- **The list is now checked against the migrations.**
  `tests/test_m22_hosted_survey.test_every_table_referencing_twins_is_classified` parses every
  `create table` for `references twins(twin_id)` and fails unless each is classified as blocking
  or cascading. Reading the schema rather than restating it is what stops a third occurrence; it
  caught `survey_responses` on its first run.

`twin_control_answers` cascades rather than blocks: it is a cache keyed by config fingerprint and
is regenerable, so a control answer about a twin that no longer exists is not evidence — the same
reasoning the list already applies to `studio_runs`. `twin_quality_runs` already cascades in the
DDL; listing it makes the in-memory backend behave identically, which is why `survey_answers` is
deleted explicitly too.

---

## 2026-10-11 — `pearson_r` reports nothing below three paired points

**Prototype-parity audit** (`docs/AUDIT_PROTOTYPE_PARITY.md` §C7). `validity/quality.pearson_r`
accepted `n >= 2`. With two pairs that both vary, `r` is **exactly** ±1 whatever the numbers are —
the arithmetic forces it — so a twin with only two scorable H3 items for an outcome had
`r = 1.00` written into `twin_quality_runs.correlations` as evidence that its ordering of the six
policy worlds matched its driver's. The Apps Script prototype's `corr_` guarded `n < 3`; the Python
port dropped the guard.

**What changed.** A named `R_MIN_POINTS = 3` in `validity/quality.py`, and `pearson_r` returns
`None` below it — the same `None` it already returns for a flat series, and for the same reason
(`docs/08` §3.3): an uninformative correlation is *undefined*, not zero, and not ±1.

`h3_correlations` carried its own copy of the floor at `< 2`. The copy is deleted rather than
corrected — two statements of one rule is how they came to disagree — so the floor now lives in
`pearson_r` alone and both call sites inherit it. The second call site is validity test 7
(`second_model`), where the same reasoning applies to a two-twin panel: it now reports `CHECK` with
"the correlation is undefined" rather than `PASS` on an `r` of 1.00.

**Why three and not more.** Three is the first `n` at which the answer is not fixed by the
arithmetic. H3 gives six points per outcome by design (`docs/01` §3.6), so fewer than three means
items were lost — a reason to report nothing, not to report a perfect correlation over the two that
survived. Anything above three would be a tuned cut-off nobody validated.

No stored row is rewritten (rule 6). Rows written before today under the old floor keep whatever
they recorded; `test_pearson_r_refuses_two_points_because_r_is_plus_or_minus_one_by_construction`
pins the new behaviour.

---

## 2026-10-11 — straight-lining is a dispersion rule, fixed at SD < 0.30 before any data existed

**Prototype-parity audit** (`docs/AUDIT_PROTOTYPE_PARITY.md` §A5). Two defects, in opposite
directions.

The prototype's rule was **SD < 0.3 across the battery, computed after reverse-coding**. An all-7s
respondent therefore had their three reversed items sitting at 1, an SD near 2.8, and passed: the
rule only ever caught straight-lining at the scale midpoint. The Python port fixed the ordering —
`_straight_lining` reads raw `value_num` — but narrowed the rule to exact equality
(`len(set(values)) == 1`), so "36 sevens and one six" passes.

**Decided: SD of the raw battery answers below `0.30`.** The prototype's own threshold, kept so it
can be cited as pre-specified, with the prototype's arithmetic discarded. RESEARCHER chose it on
2026-10-11, **before any real data existed**, which is the whole point: `docs/07` §7.1 is explicit
that a screening rule chosen after seeing results is a researcher degree of freedom, so the number
carries a date and the constant carries the date in its docstring.

**Where it is enforced, and why not at intake.** `straight_liner` is a stored boolean written by
*two* implementations — `ingest/survey_intake._straight_lining` and the Deno edge function
`supabase/functions/survey_intake/rows.mjs` — held in lockstep by
`test_m9_intake.test_the_edge_function_and_the_python_produce_identical_rows`. Changing the rule
there would need a coordinated Edge Function deploy and would still not reclassify one already
stored row.

So the split is: the **stored flag is a fact** ("every battery answer was identical") and stays a
lossless record; the **threshold is a judgement** and lives in `stats/dataset.py`, beside the
`screen()` that already owns every other screening rule. Neither intake copy was touched, and that
contract test passing untouched is the evidence. A threshold in the analysis layer can change
without rewriting evidence (rule 6) — the same answers screen differently under a different rule,
and `analysis_runs.config.straight_line_sd_min` records which rule produced which analysis, so the
two can never be confused.

Both tests still run in `screen()`. The stored flag catches a respondent whose answers are no longer
loadable, which the SD cannot see.

**`battery_sd` returns `None`, not `0.0`, below two answers.** One answer has no spread, and such a
respondent is already dropped for missing indicators; `0.0` would route them to the straight-lining
reason instead and give a wrong account of why they left the sample.

**Empirical check.** The golden fixture's *least*-varied respondent sits at SD `0.74`, 2.5x the
threshold, and the median is `1.16` — so `test_golden_fixture_screens_nobody` holds with real
headroom rather than by luck.

---

## 2026-10-11 — the generator gets the prototype's lever matrix, and `GENERATOR_VERSION` is `v5`

**Prototype-parity audit** (`docs/AUDIT_PROTOTYPE_PARITY.md` §A6). `reaction_shift` returned a
single scalar magnitude per version code, applied to every construct with only the construct's
`index_sign` for direction. Two consequences, neither visible in any output:

* **No lever was distinguishable from another by its effects.** A pay rise moved *clarity* exactly
  as much as it moved *happiness*, so no path estimated on synthetic data corresponded to anything
  and `docs/06` §4's five reaction sliders had nothing lever-specific to bind to.
* **Every interaction was exactly additive by construction.** `analysis/interactions.py` computes
  `extra = shift(joint) - (shift(a) + shift(b))`, and against a scalar linear in the dials that is
  identically zero. `docs/07` §5 calls sub-additivity the study's contribution, and no fixture in
  the suite could exhibit it against a known truth.

**Ported from the prototype's `GEN_LEVER`, verbatim**, as three new `GeneratorSpec` fields with
`config/generator.default.yaml` as their source:

* `lever_effects` — the 5x9 matrix, **signed**, in 1-7 scale points per dial step. A construct
  absent from a lever's row does not move: conditions (L2) has no path to clarity, and that zero is
  a claim, not an omission.
* `second_step_factor = 1.6` — nothing-to-minimum-wage is a bigger change than
  minimum-to-living-wage. `2.0` would make the dials linear.
* `lever_synergy = 0.3` — the prototype's `together`. `-synergy` on pushback when L4 and L5 are
  both raised (an appeals route and a forum compound); `-synergy/2` on staying when L1 and L2 are
  both raised (pay and safety substitute).

**The sign moved into the matrix, and had to come out of two places.** `_H3_SUFFIX` carried a sign
as a second tuple element and `_item_target` multiplied it in. Both are gone: with a signed matrix,
a sign at the call site would **double-apply** it and silently invert pushback, leaving and control
while leaving the other four untouched — a fault no single construct's direction reveals, which is
why `test_protection_raises_fairness_and_lowers_the_wish_to_leave` asserts all six together.

**`GENERATOR_VERSION = "v5"`.** The draw order is unchanged — the matrix consumes no randomness —
but every holdout answer moves, so a `v4` seed does not reproduce under `v5`. Recorded on every
batch, with the spec that produced it, so the matrix a batch was drawn under is reproducible from
the row rather than from today's defaults. Synthetic rows exist to exercise the machinery and prove
nothing about drivers (`docs/08` §6.2), so regenerating a `v4` batch costs only the seconds.

**Measured, not assumed.** `test_the_reaction_sliders_move_the_holdout_blocks` separates V1 (12220)
from V3 (11010) on H3 fairness by **0.833** against its `> 0.5` bar, with the no-reaction null at
**0.017** against `< 0.25` — so it passes on substance under the matrix, not on margin. The
assertion was re-verified rather than loosened, as the plan required.

**One test changed shape, not meaning.**
`test_d_ui_parity.test_the_captive_voice_checkbox_changes_only_the_representation_lever` compared
whole return values with `>`; it now compares `abs()` of the forum's own outcome, because
representation *lowers* pushback and "reacts more" means it falls further.

---

## 2026-10-11 — the arm composite becomes three single-indicator constructs

**Prototype-parity audit** (`docs/AUDIT_PROTOTYPE_PARITY.md` §A2). RESEARCHER chose this over the
alternatives on 2026-10-11.

`arm` entered as one formative (Mode B) block of three dummies. The 2026-09-29 entry above calls
that "the conventional treatment of a categorical antecedent" — true for a **control** variable,
and wrong for the manipulation under test. A composite yields **one** `ARM -> EXPO` coefficient and
**one** `ARM -> CTRL`, so the model produced no per-arm contrast: there was no estimate of the form
"MGT1 raised perceived exposure by beta", which is the reportable output of a four-arm
between-subjects experiment. Recovering it from outer weights x path coefficient is not how any IS
paper reports an arm effect, and **nothing in the output looked wrong** — the table was complete,
every number plausible, and the missing quantity simply absent.

**Now:** `ARM_MGT1`, `ARM_CON1`, `ARM_REP1`, one dummy each, `BASE` omitted as the reference, each
with its own path to `EXPO` and `CTRL`. Six coefficients where there were two, each separately
bootstrapped.

Alternatives weighed and declined: keeping the composite and adding multi-group analysis (the
engine ships `MGA` with permutation p-values) answers "does the `FAIR -> SATI` path differ between
arms?" — a different and also interesting claim, but **not** the arm main effect, so it is a
complement rather than a substitute and was deferred.

**Mode B and `reflective=False`.** With one indicator the two modes coincide — the weight is 1
either way — and Mode B is kept because an observed dummy is not a reflective measurement of a
latent arm. `reflective=False` is what routes them through the stages that already handle the
formative case: `stage_reliability` reports `na` with a reason, `stage_discriminant` and
`stage_outer_model` skip them. **No stage needed a special case**, which is why the change is small.
A single indicator has a loading fixed at 1 and an AVE of 1 by construction, so reporting those as
measurement quality would be meaningless.

**The golden diff, read rather than accepted.** `GOLDEN_FINGERPRINT` moved
`7c7fd73a12a4ec48 -> 081db1a0f8a2a2e0`; `GOLDEN_DIGEST` did **not** move, so the matrix data is
byte-identical and only the specification changed. Of 424 pinned statistics, 185 moved. The pattern
is exactly what the theory predicts, and that is the evidence nothing broke:

* **Every Cronbach's alpha is byte-identical.** Alpha depends only on the indicator covariances,
  never on the structural model.
* **AVE, rho_A and the loadings moved slightly** — max 0.0051, concentrated on `CTRL` — because
  under the path weighting scheme a construct's outer weights depend on its inner model, and `CTRL`
  is one of the two constructs the arm block points at. No loading came near the 0.708 floor; every
  AVE stayed above 0.50.
* **The structural numbers moved, and in the direction that vindicates the change.**
  `R^2(CTRL)` went **0.0101 -> 0.0412, a 4.1x increase**: the composite had been crushing three arm
  contrasts into one dimension and losing most of the signal. `R^2(EXPO)` barely moved
  (0.1024 -> 0.1058), which fits — `EXPO` was already dominated by a single arm's effect.

On the golden fixture the six coefficients separate exactly as the composite could not:
`ARM_MGT1 -> CTRL` is `+0.188` while `ARM_REP1 -> CTRL` is `+0.019`, a tenfold difference that was
previously averaged away into one number.

`docs/07` §7.2 rewritten. `EDEP`'s alpha on the golden fixture is `0.6677`, below 0.70 — unchanged
by this work, a known property of a two-item construct, and exactly why §8.1 reports rho_A and
rho_c beside alpha rather than alpha alone.

---

## 2026-10-11 — a partial-mediation variant, as a declared robustness check

**Prototype-parity audit** (`docs/AUDIT_PROTOTYPE_PARITY.md` §A1). The reported model is
**unchanged**: full mediation stays the headline, as decided on 2026-09-29.

The prototype had three direct justice->intention paths that full mediation drops: `FAIR -> VOIC`,
`FAIR -> LOYA`, `CTRL -> VOIC`. `FAIR -> VOIC` is the central claim of the algoactivism literature,
so its absence is the first thing a reviewer asks about — and the check costs **no extra data**:
same matrix, same engine call, no model call anywhere.

`build_model_spec(variant="partial")` adds `PARTIAL_MEDIATION_EDGES` and nothing else. The variant
is therefore **nested** — the full model plus three edges, with nothing removed — so each added
path's own bootstrap interval is directly interpretable as the test of that mediation restriction,
with no second fit to compare against.

**`EDEP x FAIR` and `EDEP x TRAN` are deliberately absent.** The 2026-09-29 entry records that this
exact pairing was put to the researcher and declined in favour of `EDEP x SATI` alone. Adding them
to the variant would quietly convert the robustness check into the partial-mediation model that was
declined, which is the substitution that decision exists to prevent —
`test_partial_does_not_add_the_declined_interactions` pins it.

**A latent bug this closed first.** `services/statistics.run_analysis` rebuilt the spec with a bare
`build_model_spec()` while `create_analysis` had built the matrix under its own call. With one model
they agreed by luck. With two, a resumed or re-entered run would have estimated the **default**
model against a matrix built for the other one and stored the result under the other one's
fingerprint, and **nothing would have raised**. `_spec_for_run` now reads `model_variant` off the
row and **asserts** the rebuilt fingerprint equals the one recorded at creation, raising
`StageError` on a mismatch rather than interleaving two models in one `analysis_results` table. A
row with no `model_variant` is read as `full`, which is the only model that existed when it was
written (rule 6 — old rows are not rewritten, so they must stay readable).

The Statistics tab carries a third dropdown, labelled so the run that produced a number is
self-describing on screen: a reader coming back to a result should not have to recall how a control
was set.

---

## 2026-10-11 — Generator `v6`: a synthetic respondent is an individual

**Why this came up.** Synthetic twins were failing the Twins Lab validity tests, and the first
reading was that the free text was repetitive. Repetition was real but secondary. Three layers
were wrong, and the one that mattered most was in the **numbers**, not the prose.

**Layer 0 — the panel had no between-driver variance.** `_respondent_targets` carried a hard-coded
`swing = 1.5`, which at the shipped `disposition_spread` and `shared_mood` gave a construct target
a between-driver SD of about 0.62 scale points. Measured over a forty-respondent batch, the mean
absolute difference between two random respondents' battery answers was **0.717**. `docs/08` §4
test 1 wants a wrong-person gap of **0.5**. A gap cannot exceed that between-driver difference, so
the test was asking for seventy per cent of a ceiling a *perfect oracle* twin could not clear, and
no twin was ever going to pass it. After the 5-point conversion the same compression meant four
respondents in five answered a 5-point item with the same integer, so the panel also rendered
near-identical persona clauses.

`swing` is now `GeneratorSpec.between_driver_swing`, default **2.4**, which puts the between-driver
difference at **1.070** and the mean per-item SD at **0.963** — in the range these instruments show
in published samples — with 2.1% of answers at a scale bound, so the width is not bought by
clipping.

**The trade that was refused.** Raising `likert_sd` would widen the panel far more cheaply, but as
noise uncorrelated with the construct: apparent individuality bought by destroying the construct
reliability the PLS-SEM needs. Between-driver *signal* was raised instead and within-driver noise
left alone, so every construct's alpha **rose** (e.g. `FAIR` 0.898 → 0.967, `SATI` 0.855 → 0.945)
rather than falling. `test_raising_between_driver_signal_did_not_cost_construct_reliability` pins
this.

**A sub-change considered and dropped.** The first plan also stopped `centre_for_points` from
compressing the respondent's *deviation* on 5-point scales. Dropped: item SD in scale points really
is smaller on a shorter scale, so the compression is psychometrically right, and a ±2.4 deviation
on a 5-point scale saturates both ends. Raising `swing` fixes both scale lengths at once.

**Layers 1 and 2 — the free text.** The 37 why-probes were drawn from a flat four-string tuple with
no reference to the item or to the value just drawn, so a respondent who had just strongly agreed
the app controls their work had a one-in-four chance of explaining it with "sometimes it feels fair
and sometimes it does not" — text contradicting the clause the persona builder attaches it to.
Part 14 was worse: `_OWN_WORDS` was a fixed five-tuple consumed with **no RNG call at all**, so the
passage's longest unstructured block and its closing section was byte-identical for every twin in
every batch at every seed. Measured panel-wide free-text word overlap was **Jaccard 1.000**.

Both are now composed in `generator/voice.py` as `[stance: block × band] + [circumstance: the
respondent's own facts] + [consequence: band]`, with Part 14 banded on the construct each prompt
actually asks about. Overlap is now **0.416** and no two respondents in a batch share a Part 14
block. A `Voice` drawn once per respondent fixes verbosity, register, one or two recurring motifs
and a fact-rotation offset, so the passage reads as one person rather than thirty-nine samples.

**Still no LLM, still deterministic.** Every clause is a Python draw from the respondent's own
`random.Random`. `VOICE_VERSION` is recorded beside `GENERATOR_VERSION` on every batch, because a
reworded bank changes every persona hash without changing which values were drawn and the two have
to be tellable apart. `GENERATOR_VERSION` is `v6` and **a `v5` seed does not reproduce under it.**

### Three smaller choices made inside this, for the record

* **The why bank is keyed on the item's `block`, not on `item_id`.** A bespoke line for each of the
  37 items would be unmaintainable and no more individual: the individuality comes from the band and
  the circumstance. Nine blocks × five bands × three variants, except `PAC`, which has eleven items
  and so carries five.
* **Composition draws without replacement within a respondent.** A respondent's eleven `PAC`
  answers mostly land in one band — that is what having a disposition means — and independent draws
  put one sentence in the block five times. Cells are cycled and refilled with a fresh shuffle.
* **`OWN3` has a `no_incident` cell that is not a band.** `incident_share` (default 0.35) decides
  whether a respondent has a support or deactivation story at all, which is a *structural*
  difference between passages rather than one of wording. The first `v6` draft reused the top
  fairness band for respondents without one, which produced a driver who rated fairness at the floor
  and still said their one request for help was handled at once — the same incoherence in a new
  place. The cell now says only that there is nothing to report.

### What this does **not** establish

`docs/08` §6.2 already says synthetic data proves nothing about drivers, and this change makes that
caveat sharper rather than weaker. Any deterministic non-LLM free text must be **derived from the
drawn numbers** — there is no other source of signal — so a synthetic persona now contains, in
effect, a paraphrase of the answers test 1 scores the twin against. A real driver's "why" is far
less tidily aligned with their own ratings.

So a validity test passing on a synthetic panel is a **machinery check and an upper bound**, never a
calibration of how the twins will do on real drivers. It says the pipeline can discriminate when the
signal is there; it does not say how much signal real personas carry. No synthetic validity result
may be reported as evidence about twin fidelity.

---

## 2026-10-12 — Deleting twins: two paths, with different guarantees

**The problem.** *Delete all synthetic surveys* refused: 9 of 10 synthetic twins had answered a
run or sat on a frozen panel, so deleting them would have changed a stored result (rule 6). The
first instinct — drop the guard — would have been worse than the refusal. Deleting a twin while
its `runs` row survives leaves a stored `twins_n` and `index_value` computed over twins that no
longer exist: a number nobody can audit or reproduce, sitting in an evidence table looking valid.

**The resolution: evidence is withdrawn whole, never edited.** Both blockers hang off `sessions`,
so the delete takes the *session* — panel, runs, twin answers and validity verdicts together —
rather than cutting rows out from under a result that stays. Rule 6 is intact: no append-only
table is UPDATEd and no stored number is rewritten. What makes the withdrawal legitimate is
structural rather than a judgement call: a session only blocks a synthetic delete because a
synthetic twin is on its panel or answered one of its runs, so its index was computed over
synthetic twins, and `docs/08` §6.2 already says that number proves nothing about drivers. There
is no reportable result in the set.

### The two paths, and why they are not one

| | Generator → *Delete all synthetic* | Twin Lab → Twins → *Delete twins* |
|---|---|---|
| Scope | every `data_type='SYNTHETIC'` row | the ticked selection |
| Can reach a real row | **never** | yes, if ticked |
| Guard | the `data_type` key | the explicit selection, and the confirm screen |

**The Generator path never puts a real row at risk, whatever is ticked.** `allow_real_loss` exists
in `services.surveys.delete_synthetic` but is deliberately **not plumbed through**
`services.generator.delete_all_synthetic`. A session mixing synthetic twins with a real driver is
left intact, and the synthetic twins sitting on it stay blocked — the screen says so and points at
the other path. *Delete all synthetic* means synthetic.

That was a correction mid-build. The first version offered a second tick on the Generator screen to
accept a real driver's loss. Wrong place: a bulk button labelled "synthetic" must not be able to
reach real data however many confirmations it collects.

**The per-twin path can delete a real twin, because a researcher must be able to remove a withdrawn
respondent.** Its protection is not "real rows are untouchable" — it is that nothing goes without
the selection being named and its cost shown. `twin_delete_preflight` returns
`collateral_twin_ids`: twins **not** selected that sit on a session this delete would withdraw.
Deleting two twins and silently voiding a run forty others answered is the surprise that field
exists to prevent, and the confirm screen leads with it. Those twins are not deleted; they lose the
run they answered, and the screen says exactly that.

`delete_surveys` defaults on, because "delete this survey" is what the screen offers; unticking it
drops the twin and keeps the respondent's answers for a re-import.

### Gradio degradation

The selection is a `gr.CheckboxGroup` below the twins table, **not** checkboxes inside it. That
table is `gr.HTML` and Gradio gives no way to read a tick out of rendered markup. The degradation
is in the styling, not the content: the boxes list exactly the twins the filters select, so the
selection is still made by ticking. The ticks are cleared whenever the filters change — a
selection left over from a filter the researcher can no longer see is dangerous on a delete button.

### Tables that do not cascade

`SESSION_CASCADE_ORDER` exists because three tables reference `sessions(session_id)` with **no**
`on delete` clause: `twin_quality_runs`, `validity_results` and `twin_control_answers`. A session
delete that skipped them fails with a raw `23503`. This is the third time this class of bug has
appeared — `studio_runs` and `twin_control_answers` were the first two, both found when a
researcher pressed a button — so the list is explicit and ordered children-first rather than
trusting the DDL, which also keeps the in-memory backend behaving identically.

---

## 2026-10-12 — the twin was never shown what the ends of a scale mean; `KEEP` read the wrong block

**Found while diagnosing the first quality gate ever run on synthetic twins.** Nine of nine
synthetic twins were dropped at MAE 2.08-3.17 against `mae_max = 1.0`. The verdicts are correct and
the threshold did not move. Three defects sat behind them, and the first two are fixed here.

**What the evidence said.** The signed error against each twin's own driver, over 54 H3 items per
outcome, was one-directional and barely dispersed: fairness **+2.80** (sd 1.25), staying **+3.46**
(sd 1.03), pushback **-1.56** (sd 1.34). Three facts rule out a twin-fidelity explanation:

* On the `00000` and `SHAM` control cells the same twins reproduced their drivers to within ~0.2
  points on **all nine constructs** (`FAIR` 1.52 to 2.17, `TRAN` 1.43 to 1.12, `LOYA` 1.50 to 1.35,
  `SATI` 3.33 to 3.23, and so on). The persona and the twin agent were not the problem.
* The Pearson `r` the gate records but does not gate on was *good* — fairness 0.77, staying 0.80.
  The twins ordered the six worlds correctly and sat at the wrong level.
* The gate was not too strict. A twin answering the literal constant **3** eighteen times scores
  MAE 0.76 and within-1 89% on that batch, and would have been **kept on 10 of 10 twins**. Raising
  `mae_max` to admit 2.8 would admit a random number generator, and the one real twin on record
  passed at 0.75 with `r = 0.00` on all three outcomes — right level, ordering absent. The gate
  measures level only; that is `docs/08` section 2.2 as specified and is not changed here.

**Defect 1 — the `<<<BATTERY>>>` block never carried the anchors.** Both renderers in
`agents/twin.py` wrote the item as stem plus "answer 1 to N". The register loads an `anchors` array
per scale, validates its length against `points` at import (`reference_store._check_anchors`) and
then showed it to nobody. The human read a radio row labelled at every point; the twin got a bare
range. For `agree5` and `agree7` the convention carries it. For the two scales that reach a twin
**only** through H3 it does not: `likely7` runs `Not at all likely` to `Extremely likely` with **no
negative end**, so its point 4 is "Moderately likely" and a twin reading it as a symmetric
agreement scale is miscalibrated before it answers — which is the shape of the largest bias term.

*What changed.* New `models.twin.BatteryItem` (stem, points, anchors) replaces the bare
`(stem, points)` tuple on `RoundPrompt` and `H3RoundPrompt`, with a validator requiring one anchor
per point. `ReferenceData.scale_anchors` and `ReferenceData.battery_item` are the **only** place one
is built, so no caller can assemble a round that quietly omits them. Each line now reads
`(answer 1 to 7; 1 = Very unfair, 4 = Neither fair nor unfair, 7 = Very fair)` — the two ends and
the midpoint, not all seven labels, because 18 items by 7 labels is a wall of repeated scale text;
the midpoint is omitted on an even-pointed scale rather than faked from a neighbour.

New prompts `twin_v3.md` (supersedes `twin_v2.md`) and `twin_h3_v2.md` (supersedes `twin_h3_v1.md`),
not edits: a frozen stimulus prompt gets a new version file. Rule 5 and rule 7 now say to read the
words before choosing the number, and `twin_h3_v2.md` gains a **rule 8** — *the number describes
this person, not the version* — because the twin's failure was to answer how good the announcement
sounded rather than how far this driver would actually move.

`config_match.current_config` now hashes stem, points **and** anchors. Every `config_fingerprint`
moves once, which is the intended effect: decision `005` already says a verdict is only valid for
the config it was made under, and a verdict taken when the scale ran unlabelled was taken under a
different instrument. **The nine stored H3 verdicts are superseded, not deleted** (rule 6).

**Defect 2 — `_H3_SUFFIX["KEEP"]` named the wrong construct.** `H3_V{n}_KEEP` asks "how likely
would you be to keep driving with Uber?" — a **behavioural intention** — and was answered from
`LOYA`, whose items are "I hope this job carries on in the future": **affective commitment**. The
two diverge, and for this study's own population they diverge in *opposite directions*. A driver
with four dependants, a vehicle rented from a fleet owner and no other household income does not
hope the job continues and is nevertheless extremely likely to keep driving. The generator was
therefore describing its most economically captive respondents as the ones about to leave —
inverting the moderation `EDEP` carries in `stats/spec.py`, inside the data built to exercise it.

*What changed.* `KEEP` reads `EXIT` ("I will probably look for a new job in the next year",
"Actively looking for a new job in the next year is quite likely for me"), mirrored on the 1-7
scale **after** the lever shift, never before — mirroring first would turn a version that reduces
the wish to leave into one that reduces the likelihood of staying. The direction lives in a new
`_H3_MIRRORED` table beside `_H3_SUFFIX`, with an import-time guard that both name the same three
questions, because a suffix in one and not the other would be scored forward by default.
`PUSH -> VOIC` has the same weakness — `VOIC` is three attitude items and one behaviour item — but
its bias is the smallest of the three and remapping it is a construct decision the researcher has
not taken; it is **not** changed here.

Measured against the stored H3 vectors: the `KEEP` gap falls 3.53 to 1.90 and the overall gap
2.69 to 2.14. Partial, and honestly so — see "what this does not fix".

`GENERATOR_VERSION` becomes **`v7`**. The draw order is unchanged (the mapping consumes no
randomness) but every `KEEP` holdout answer moves, so a `v6` seed does not reproduce under `v7`,
exactly as `v5` broke `v4` without touching the draw order.

**Defect 3 — `between_driver_swing` buys pile-up, not spread, against a slider near an end.** Not a
code fault; a silent interaction between two correct behaviours, surfaced rather than changed. The
clamp in `_respondent_targets` is right — a target off the scale is not a target — and it is
silent. With the `frustrated` preset, `FAIR` and `TRAN` sliders at 2.0 and `v6`'s swing of 2.4,
**38.5% of respondents land on the exact floor** of fairness and clarity (17.6% at swing 1.5), 20%
on satisfaction and loyalty. The between-driver SD on `FAIR` rose only 0.51 to 0.65 while more than
twice as many respondents became *identical at the wall*. `v6` was built to widen the panel and on
that batch narrowed it, and the first place it shows is a wrong-person test with no ceiling to
reach (`docs/08` section 4 test 1) — discoverable only after the twin calls were spent.

*What changed.* `generator.synthetic.clipping_share(spec)` is pure arithmetic over a spec, with its
own RNG so it cannot disturb a batch's draw order, and `services.generator.clipping` formats the
constructs above `CLIPPING_NOTICE_SHARE = 0.20` as `GeneratorClipping` rows. *Preview 3 drivers*
now carries the note above the three rows: three respondents cannot show that a fifth of the batch
shares one construct's floor. **A note, never a block** — a batch two-fifths on the fairness floor
may be exactly what the researcher wants — and it says so explicitly when nothing is pinned, so an
absent note and an unrun check cannot look alike (rule 7). `0.20` is a reporting threshold read
nowhere else; changing it cannot change a drawn batch.

**What this does not fix, and is the researcher's call.** After both fixes the twins would still be
roughly 2 points high, because the remaining disagreement is not about *who the driver is* but about
*how far a better world moves them*. The twin reads a world with a living wage, full pay
transparency, an appeals route and a drivers' forum and answers 6-7; `lever_effects` moves fairness
by at most +1.64 from a baseline already clamped near the floor, and answers 3. **Neither figure is
measured.** `lever_effects` is a hand-set matrix ported from the Apps Script prototype
(`docs/AUDIT_PROTOTYPE_PARITY.md` section A6); the model's reaction size is its own prior.

So the H3 gate **run on a synthetic twin is not a measurement of twin fidelity** — it compares the
model's implicit reaction function against the researcher's typed one. That is consistent with
`docs/08` section 6.2 (synthetic rows exercise the machinery and prove nothing about drivers), and
this gate run did exercise it correctly end to end: 0 failed calls, 36 items scored per twin,
correlations computed, controls answered, verdicts appended. **Tuning `lever_effects` until
synthetic twins pass is forbidden** — it is the circularity `docs/08` section 2.4 rules out, and
nothing here does it.

---

## 2026-10-13 — the generator could not reproduce a real driver: `reaction_gain` and reactivity

**Researcher decision on the gain; the rest is defect repair.** Nine of ten synthetic twins kept
failing the H3 gate after the scale-anchor fix (mean MAE 2.49 against `mae_max` 1.0). The anchors
were worth ~9%. This is the other 91%, and it was not the twins.

### What the evidence said

The twin and its driver agreed on **who the driver was** and disagreed on **how far a better world
would move them**, by a factor of 2.8:

* On the `00000`/`SHAM` controls the twins reproduced their drivers to a mean absolute gap of
  **0.16 points across all nine constructs**. The persona and the twin agent were sound.
* Fairness: the driver's baseline 1.52 went to 2.78 (a move of **+1.26**); the twin's 2.09 went to
  5.57 (**+3.48**).

Then the decisive check, which is **independent of any twin**. Fitting a single gain on
`lever_effects` against the one real respondent's own 18 Part 17 answers:

```
best k = 2.11
k=1.00  MAE 1.504   <- the inherited matrix
k=2.11  MAE 0.864
```

**At the inherited gain the generator could not reproduce the only real driver in the database** —
it predicted that driver's Part 17 answers at MAE 1.504, which is to say the generator would have
failed its own quality gate against a real person. Corroborated three further ways, with the H2
check carrying no method confound because H2 mirrors the battery item for item:

| | real driver | matrix said | ratio |
|---|---|---|---|
| H3 fairness move | +2.50 | +1.18 | 2.1x |
| H3 pushback move | -2.75 | -1.01 | 2.7x |
| H3 staying move | +2.17 | +0.74 | 2.9x |
| H2, 16 mirrored items | +0.375 / item | +0.112 | 3.3x |

So the twins' reaction magnitude was approximately right and the **generator's was wrong**. They
were being failed for agreeing with reality. The thresholds were never the problem: a twin
answering the constant `3` eighteen times would have scored MAE 0.76 and been kept on 10 of 10,
so loosening `mae_max` would have admitted a random number generator. **`mae_max` 1.0 and
`pct_within_1_min` 0.80 are unchanged, and so is every line of the gate.**

### Defect 1 — the gain had never been checked against a driver

`lever_effects` carries two separate claims: *which* construct each lever moves and in what
proportion, and *how far* the whole matrix moves a respondent. Only the second has an external
check, and it had never been made — the matrix was typed, ported from the Apps Script prototype
(`docs/AUDIT_PROTOTYPE_PARITY.md` §A6).

`GeneratorSpec.reaction_gain` is now that second claim, as one multiplier on the finished shift.
The structure is untouched: a zero in the matrix stays a zero, every proportion and every sign is
preserved, and `tests/test_m9_generator_levers.py` asserts exact proportionality rather than mere
direction, because a gain that quietly altered one construct's share would still pass every
directional test in that file.

Applied **after** the two interactions, so sub-additivity is preserved as a proportion. Scaling
the per-lever contributions but not `lever_synergy` would have left the comparisons passing while
changing how sub-additive the population is — `docs/07` §5's headline claim.

`calibrate_reaction_gain(humans)` is the derivation, kept as a function so the number is
**re-derived from real responses as n grows** rather than inherited. Default `2.11`, pinned by a
test so it cannot drift without a conscious edit. The fit forces unit gain internally: a fit that
used the caller's spec as given would return the gain *on top of* the one already there, reporting
`1.00` ("no correction needed") when it meant "2.11 was right" — indistinguishable from a
successful calibration, and it would have halved the gain on every re-derivation. Found by running
the fit against the real respondent and getting 1.00 back; now guarded by an idempotence test.

**Provisional at n=1.** One respondent fixes the direction and the rough gain and is not a
calibration sample. The derivation runs against the live database, never in CI, so the round-trip
test instead generates a batch at a known gain and fits it back.

**Fitted to survey answers, never to twin output.** Fitting the gain until twins pass is the
circularity `docs/08` §2.4 forbids; `calibrate_reaction_gain` cannot see a twin, and the gain was
settled before any twin was re-run.

### Defect 2 — the reaction was a batch constant no persona mentioned

Even at the right magnitude, **no twin could have passed except by guessing.** Part 17 asks for the
baseline moved by this respondent's reactivity. The baseline is all over the persona. The
reactivity was a hidden batch-level constant: across the whole range of `EDEP`, its only
respondent-level input, the fairness shift varied by at most **0.16 scale points** and by exactly
**0.00 on four of the six versions**. Every respondent reacted identically and nothing in any
persona said how reactive they were, so the gate was scoring twins on a quantity it had never
disclosed — an information defect in the test, not a failure of the twins.

`GeneratorSpec.reactivity_spread` draws a per-respondent reactivity from that respondent's own RNG,
centred on `1.0` so it widens the panel without moving the batch's mean reaction (the gain remains
the only thing that sets level). `generator/voice.py` gains a `react:low|mid|high` circumstance
family, so the respondent **says** how far an announcement would move them, in their own voice,
throughout the passage.

These are **dispositions, not answers.** None names a version, a lever, a dial or a number, and
the twin must still work out which of six specific packages would matter to this person and by how
much. I8 permits exactly this: its own guard puts the whys and open answers *in* the persona block,
where "the twin is meant to read them as who this person is" — the same standing the baseline
attitudes already have. A test asserts no holdout id and no version code reaches any free-text
field.

### What this produced

Synthetic Part 17 answers moved to where a driver's plausibly are, and acquired real
between-respondent variance where there had been almost none:

| | v7 | v8 | what the twins answered |
|---|---|---|---|
| fairness | 2.78 | **4.08** (sd 1.44) | 5.57 |
| pushback | 3.73 | **3.01** (sd 1.56) | 2.18 |
| staying | 2.53 | **4.61** (sd 1.36) | 5.65 |

Mean gap ~2.8 to ~1.1. Between-driver SD inside the holdout block ~0.6 to ~1.4.

`GENERATOR_VERSION` -> **`v8`**, `VOICE_VERSION` -> **`v2`**. The reactivity draw sits between the
background block and the construct targets, so a `v7` seed does not reproduce under `v8`.

### Also here

* **Four dials reached the screen.** `between_driver_swing` and `incident_share` were added to
  `GeneratorSpec` in `v6` and never put on the Generator page, so a batch could only be drawn at
  their defaults; they join the two new ones in `BATCH_SLIDERS`. A dial nobody can see is a dial
  nobody checks, and `between_driver_swing` is the one that decides whether a panel has any
  ceiling for a wrong-person test.
* **`clipping_share` stays baseline-only.** Extending it to the holdout answers was tried and
  reverted: at a calibrated gain nearly every respondent reaches an end of the scale on at least
  one of the six versions, so the measure fired on the *default* spec (pushback 84%) and carried
  no information. It is also not the same defect — a driver already low on pushback who is shown a
  near-total package and lands at "not at all likely" is answering correctly, whereas a respondent
  pinned at *baseline* is one whose persona cannot distinguish them from the next respondent.

### What was deliberately not done

* **No eligibility route for un-gated synthetic twins.** An earlier proposal would have let
  machinery-verified synthetic twins onto a panel with `kept` left `False`. Rejected by the
  researcher: twins reach a panel by passing, or not at all. `qualified_twin_ids` is unchanged.
* **No threshold moved**, and `kept` is never written on a row that failed.
* **`PUSH -> VOIC` left alone.** `VOIC` is three attitude items and one behaviour item, the same
  weakness `KEEP -> LOYA` had, but its bias is the smallest of the three and remapping it is a
  construct decision the researcher has not taken.
* **The remaining ~1.1-point gap is not closed by fitting.** Whether it is the twin or the matrix
  is not decidable at n=1, and the honest route is to re-run `calibrate_reaction_gain` as real
  Part 17 responses arrive. Test 3 (`docs/08` §4) is where reaction magnitude surfaces as a
  verdict, and it is left to report what it reports.

---

## 2026-10-13 (later) — two staged fixes: the level bias is gone, the failure moved to the versions

Continues the entry above. Three measured runs of the H3 gate on synthetic batches, one change per
stage, each with its metric predicted before the run. `tools/gate_diagnostic.py` is the instrument
and reports the same four numbers every time, filtered to one batch prefix so two generator
versions can never be pooled.

### Stage 1 — `twin_h3_v3.md`: tell the twin to locate how far this driver moves

Prompt only. Same batch, same personas, same twins, so the change is isolated from sampling.

The first TASK step and a new rule 1 now direct the twin to find, in the persona, what this person
says about announced changes **before** answering, and to let that set the size of its moves; the
`rationale` has to name it, so the step is visible in the output rather than assumed.

| | before | after |
|---|---|---|
| r(reactivity band, twin H3) | -0.08 | **+0.20** |
| twin H3 spread / driver spread | 46% | 190% |
| within-1 | 51.9% | **65.0%** |
| mean MAE | 1.517 | **1.219** |
| FAIR / PUSH / KEEP signed bias | +1.77 / -0.45 / +1.15 | **+0.18 / -0.22 / -0.48** |

**The level bias that opened this whole investigation is gone** — fairness +0.18, down from +2.88
at the start. The twin took the instruction and began varying per driver. It then varied *too
much and badly aimed*: 190% of its drivers' spread at only r +0.20 against a +0.59 ceiling. It was
hunting a signal it could not reliably locate, which is what Stage 2 then tested.

### A real defect found while re-gating: the fingerprint did not cover the H3 prompt

The first Stage 1 run **skipped every twin** — "already scored under this config". `H3_PROMPT_REF`
swaps a sibling file in for the Part 17 round only, so `current_config`'s `prompt_sha256` described
the battery and sweep rounds and said nothing about the prompt that produced every stored H3
verdict. Rewriting the H3 prompt therefore invalidated nothing, and a verdict made under a
superseded Part 17 prompt read as current — the same class of defect as a verdict taken on an
unlabelled scale, which decision `005` exists to prevent.

`current_config` now carries `h3_prompt_sha256`, hashed from the agent config with the H3 override
applied exactly as `ask_h3_round` builds it. `tests/test_m21_config_match.py` asserts the key is
present, non-empty and **different from** `prompt_sha256` — equality would mean the override is not
being applied and the gate is not sending the prompt the fingerprint claims.

### Stage 2 — `v9`: make the reactivity clause legible, not merely present

At one circumstance slot in eight the clause surfaced one to three times in a 1,700-2,450 word
passage, once at 93% of the way through. Reactivity now holds **three of ten slots** and each band
carries five phrasings rather than three. Mentions went from 1-3 to 4-15, first mention from as
late as 93% to 8-57%.

Repeated rather than given its own persona heading **on purpose**. A dedicated section would be the
obvious fix and a real driver has no such field, so a synthetic persona would carry a shape no real
one does — the parity `CLAUDE.md` insists on when it refuses a respondent who answered three of 37
probes. Legibility had to come from placement inside the existing shape.

`facts_of` returns a longer tuple, so `fact_offset` draws from a different range: **a `v8` seed does
not reproduce under `v9`**, and a new batch was required.

**The targeted metric moved emphatically:**

| | stage 1 | stage 2 |
|---|---|---|
| r(reactivity band, twin H3) | +0.20 | **+0.87** (ceiling +0.64) |
| twin H3 spread / driver spread | 190% | 148% |

The twin now tracks *which driver it is* better than the generator encoded it. Legibility was the
bottleneck for person-discrimination, and that part is solved.

**The gate thresholds did not follow:** mean MAE 1.352, within-1 58.6%, 0 of 9 kept. Read with the
confound stated: Stage 2 necessarily changed the **batch as well as** the persona (new seed, a
different draw of respondents, bands skewed 6 low / 2 mid / 1 high), so its MAE is not directly
comparable with Stage 1's. Stage 1 was clean; Stage 2 is not.

### Where the failure now sits, and it is a different axis

| | driver | twin |
|---|---|---|
| spread across the six **versions** | 0.495 | **0.126** |
| r(driver version means, twin version means) | | **+0.09** |
| within-person ordering, fairness | | +0.37 |
| within-person ordering, staying | | +0.38 |
| within-person ordering, **pushback** | | **-0.21** |

**Between-person discrimination is solved (r +0.87). Between-version discrimination is broken
(r +0.09).** The twin now gives nearly the same answer to all six worlds, modulated by person — a
quarter of its drivers' spread across versions, and it orders the versions *backwards* on pushback.
That is precisely what `docs/08` §2.3 says H3 exists to test: whether the mapping from stimulus to
response transfers, not just the level.

**A candidate cause is this entry's own Stage 1 change.** `twin_h3_v3.md` rule 1 says to answer at
this person's size of move "not at the size the version seems to deserve", and rule 9 that the
number "describes this person, not the version". Under the previous prompt the within-person
orderings were fairness +0.33, pushback +0.31, staying +0.32 — all positive; pushback has since
gone negative. The batches differ, so this is a candidate and not a finding, but the prompt
plausibly bought person-sensitivity by suppressing version-sensitivity and should be rebalanced
before anything else is tried.

### Stopped here: provider quota

The Stage 2 run lost its tenth twin to a `429 monthly usage limit` from Ollama Cloud, and no
further gate run is possible until the quota resets. The nine twins that did score have two clean
repeats and zero failed calls each, so their numbers stand; `SYN-14102026-0009` has **no verdict
and is recorded as not run**, never as a result (I15).

### Unchanged throughout

`mae_max` 1.0, `pct_within_1_min` 0.80, `h3_verdict`, `qualified_twin_ids` and every line of the
gate. `kept` has never been written on a row that failed, no eligibility route was added, and
`reaction_gain` has not been touched since it was fitted to survey answers. Panel-eligible twins
remain 1 — the real one.

### Next, in order, when quota returns

1. **Rebalance `twin_h3_v3.md`** into a `v4` that keeps the person-sizing step and restores an
   explicit instruction to tell the six versions apart. Prompt-only, so it can be run against the
   existing `SYN-14102026` batch with no new generation — the clean, isolated experiment Stage 1
   was. Predicted: r(version means) leaves +0.09 and pushback ordering returns positive.
2. If that does not move it, the next candidate is the **single-call H3 protocol**
   (`H3_PROTOCOL = "h3_single_call_v1"`, M19 WP-3): eighteen numbers for six worlds in one context
   may be producing one impression emitted six times. Reverting to six calls is a **documented
   research decision and 6x the cost**, and is the researcher's to take, not a tuning step.
3. The residual level question — the H3 fit said gain 2.11, the H2 corroboration 3.3x — waits on
   real Part 17 responses and `calibrate_reaction_gain`, not on another twin run.

---

## 2026-10-13 (stage 3) — `twin_h3_v4.md` rebalances v3; the next hidden constant is `lever_reactions`

Prompt only, run against the same `SYN-14102026` batch as stage 2, so this comparison is clean.

v3 had overcorrected: it bought person-discrimination by suppressing version-discrimination. v4
keeps the person-sizing step and restores the version as the other half of the answer — what a
version changes decides whether it touches what this person cares about; how far this person moves
decides the size. **Nothing in v4 says which direction any construct moves under any version.**
That stays the twin's to work out and the gate's to score; writing it in would be coaching the twin
to the generator's answer.

| | stage 2 (v3) | stage 3 (v4) |
|---|---|---|
| within-person ordering, **pushback** | **-0.21** | **+0.35** |
| ordering, fairness / staying | +0.37 / +0.38 | +0.40 / +0.39 |
| twin spread across the six versions | 0.126 | **0.283** (driver 0.475) |
| twin H3 spread / driver spread | 148% | **110%** |
| r(reactivity band, twin H3) | +0.87 | +0.37 |
| FAIR signed bias | +0.24 | **+1.38** |
| mean MAE | 1.352 | 1.325 |
| within-1 | 58.6% | 61.4% |
| **kept** | 0 of 9 | **1 of 10** |

The backwards pushback ordering is fixed and all three orderings are consistently positive.
`SYN-14102026-0000` is the **first synthetic twin to pass the gate on its merits** — MAE 0.94,
within-1 83.3%, under unchanged thresholds.

**It is a trade, not a pure win.** Fairness bias returned (+0.24 to +1.38) and person-tracking gave
some ground (+0.87 to +0.37) in exchange for version-tracking. Recorded as a trade rather than
tuned away: the two prompts are both honest readings of the task and the balance between them is
not something to fit against a pass rate.

### Mean MAE has plateaued, and the reason is the next hidden constant

Across stages 1-3 mean MAE sat at 1.219, 1.352, 1.325 and within-1 at 65.0%, 58.6%, 61.4%. Three
prompt and persona fixes each moved their own target metric and none moved the gate much. The
reason is visible in the one metric that never moved:

    r(driver version means, twin version means) = +0.09 (stage 2) -> +0.07 (stage 3)

The twin now *differentiates* the six versions — its spread across them more than doubled — but it
differentiates them in the **wrong order**:

| | driver | twin |
|---|---|---|
| ranks highest | V1 `12220`, V3 `11010` | V4 `11211`, V5 `02211` |

`V5` raises no pay at all (`L1=0`) and the twin ranks it second; the driver ranks it fifth. The
cause is `GeneratorSpec.lever_reactions`, which carries `{L1: 2.0, L2..L5: 1.0}` — **pay is
double-weighted for the whole batch, and no persona discloses it.**

That is the **same defect class** as `reaction_gain` before it was calibrated, and the same one as
reactivity before it was drawn per respondent and spoken aloud:

* it is a **hidden batch constant** — identical for every respondent, mentioned in no persona, so
  no twin can infer it except by guessing which lever this population happens to weight most;
* it has **never been checked against a driver**, exactly as the gain had not.

It is now the binding obstacle. It is also **not calibratable at n=1**: five lever weights plus a
gain is six parameters against eighteen observations from one respondent, which is underdetermined,
so the route that fixed the gain is not available here.

### Not decided here

Two routes, and both are research choices rather than defect repair, so they go to the researcher
(`CLAUDE.md`, "when the spec is silent"):

1. **Make lever salience per-respondent and legible**, the move that took reactivity tracking from
   r -0.08 to +0.87. A driver would carry which lever matters most to them and say so in their own
   words ("the money is the only thing that would change my mind" against "it is the disrespect,
   not the money"). It needs no calibration and is arguably more realistic than one batch-wide
   weight — but committing the generator to the claim that salience varies between drivers, and in
   what proportion, is a modelling decision.
2. **Calibrate `lever_reactions` against real Part 17 responses** once n supports six parameters,
   through the same kind of fit as `calibrate_reaction_gain`.

Until one of them is taken, a synthetic twin can pass the H3 gate only by happening to share the
researcher's lever weighting. One of ten now does.

`mae_max`, `pct_within_1_min`, `h3_verdict` and `qualified_twin_ids` remain untouched across all
three stages, and `reaction_gain` has not been altered since it was fitted to survey answers.

---

## 2026-10-13 (Route A) — `v10`: lever salience is per-respondent and spoken, and the mix is measured

The researcher chose **Route A** over calibrating `lever_reactions` against real data, which is
not available at n=1: five lever weights plus a gain is six parameters against one respondent's
eighteen Part 17 answers. Route A removes the **last of the three hidden batch constants** in the
reaction chain.

| | what it says | before | now |
|---|---|---|---|
| `reaction_gain` | how far *any* change moves a driver | typed `1.0` | fitted `2.11` (`v8`) |
| `reactivity_spread` | how far it moves *this* driver | batch constant | drawn + spoken (`v8`/`v9`) |
| `lever_reactions` | **which** change moves them | `{L1: 2.0, rest 1.0}`, in no persona | drawn + spoken (`v10`) |

### What changed

`GeneratorSpec.salience_spread` (default `0.5`) and `generator.synthetic.respondent_lever_weights`
draw a weight per lever per respondent, from that respondent's own RNG, in the odometer's frozen
order. `reaction_shift` takes them in place of `spec.reaction(lever)`; `captive_voice`'s EDEP
multiplier still lands on `L5`, now on whichever weight is in force. `voice.py` gains a
`salience:*` circumstance family — five levers, five phrasings each, named for the thing and never
the lever (*"the money is the only thing that would change my mind"*, *"it is the disrespect, not
the money"*) — and `salience_tag` keys it on the lever this respondent weights highest, with ties
resolved in I2's order. Three slots in `facts_of`, the share `v9` established as the threshold of
legibility. `GENERATOR_VERSION` → `v10`, `VOICE_VERSION` → `v4`; the new draws change the draw
order, so **a `v9` seed does not reproduce**.

**The draw is multiplicative and centred on `lever_reactions`**, which is three constraints at
once and all three are load-bearing:

* the batch's mean salience on every lever is unchanged (asserted over 4,000 draws), so this
  admits that drivers differ rather than re-weighting the population — re-tuning those means
  against a twin pass rate is the circularity `docs/08` §2.4 forbids;
* a lever whose slider is `0.0` stays `0.0` for every respondent, so `docs/06` §4's no-reaction
  null stays null;
* no weight can go negative, which would invert that lever's sign for one driver and make a pay
  rise lower their satisfaction.

A respondent with **no** lever above zero carries no salience clause at all. Omitted rather than
invented: they have no change that matters most to them, and rule 7 cuts both ways.

### Legibility: measured, and it passed

The `v9` measurement, repeated — clause occurrences and first-mention position per
`persona_passage`, on a fresh ten-respondent batch at the default spread:

| | reactivity (`v9`) | salience (`v10`) |
|---|---|---|
| mentions per passage | 4–15 | **5–12** |
| first mention, % through | 8–57% | **2–25%** |

### The number Route A owes the researcher, and it is not the one the handoff predicted

Centring the spread on the researcher's means has a consequence that must be stated rather than
discovered after a sweep. `L1`'s draw spans `[1.0, 3.0]`; every other lever's spans `[0.5, 1.5]`.
So **most of the batch still weights pay highest**:

| `salience_spread` | pay | conditions | contracts | appeals | forum |
|---|---|---|---|---|---|
| 0.0–0.3 | **100%** | 0 | 0 | 0 | 0 |
| 0.5 (default) | **85%** | 4% | 4% | 4% | 4% |
| 0.9 | **62%** | 10% | 9% | 10% | 9% |

With the five means flat at `1.0`, the same spread spreads the top salience roughly evenly, so
this is the researcher's own weighting and not a defect in the draw.

**What this means for the gate.** `v10` does repair the defect as stated: the pay weighting is no
longer hidden — every persona now says, in the driver's own words, that money is what would change
their mind, so a twin no longer has to guess which lever this population weights and should rank
`12220` and `11010` above `02211`. That is the prediction to score. But *"every persona discloses
the batch's weighting"* and *"the batch contains drivers who want different things"* are different
claims, and at the default spread only the first holds. If `r(driver version means, twin version
means)` moves and person-discrimination does not, that asymmetry is why.

`generator.synthetic.salience_mix` and `services.generator.salience` compute the mix, and the
Generator preview carries it as a pre-flight note beside the `v7` clipping note — the lesson of
`clipping_share`: the researcher sees the number **before** spending the calls. The note warns
above `SALIENCE_NOTICE_SHARE` (two-thirds) and reads as information below it. **A diagnostic,
never a correction.** Nothing in the generator reads it, and a pay-dominated population may be
exactly what the researcher means to model. Flattening `lever_reactions` is a claim about Indian
gig drivers and is **not taken here**.

### Found while testing, and deliberately not fixed: `lever_synergy` ignores the weights

`reaction_shift` applies its two interaction terms from the **dials alone**, so a batch with every
reaction slider at `0.0` still carries them — which contradicts `GeneratorSpec.lever_reactions`'
own docstring ("A batch with every reaction at zero produces holdouts identical to the baseline,
which is the correct null"). Pre-`v10`, and confirmed on the pre-`v10` code path.

Under `v10` it has a second edge: the synergy is now the **only part of the shift that is still a
batch constant**. A driver with near-zero salience on appeals and on a forum nevertheless receives
the full `-lever_synergy` on pushback when a version raises both.

Left alone and recorded, because whether an interaction between two levers a respondent does not
react to should fire is a claim about sub-additivity — `docs/07` §5's headline contribution — and
is the researcher's to take, not something to change while fixing salience. `CLAUDE.md`, "when the
spec is silent": it affects research validity, so it stops and asks. The test asserts that `v10`
changes nothing here, against the batch-weighted shift rather than against zero, and says why.

### Tests

Fifteen new, each naming what it holds: the weights vary between respondents and reach the shift;
the batch mean per lever is unchanged over 4,000 draws; a zero slider stays zero and no weight goes
negative; zero spread reproduces the batch weighting exactly; an incomplete weighting raises rather
than defaulting a lever to "normal"; `captive_voice` multiplies the respondent's own forum weight
and not the batch's; the gain fit still calls `reaction_shift` at the batch weighting, because a
real respondent's salience is unknown and drawing one for them would be fitting to a fiction
(rule 5); the persona states the salience and a wide batch speaks for more than one lever; no
clause names a lever code or a digit; three slots, one band, and the other facts not crowded out;
the mix diagnostic's four readings, its null, and that it cannot disturb a drawn batch; the
service's ordering and the note's three branches.

### Unchanged

`mae_max` 1.0, `pct_within_1_min` 0.80, `h3_verdict`, `qualified_twin_ids`, every line of the gate,
and `reaction_gain` at the value fitted to survey answers. `kept` has never been written on a row
that failed. No eligibility route was added. `lever_reactions`' means are exactly as the researcher
set them. `data/reference/*.json` untouched (`build_reference --check` exits 0).

### Next, and it needs the live path

Nothing below costs a decision; all of it costs quota.

1. Draw a fresh batch at `v10` (generation is free) and read the salience pre-flight note.
2. Import twins (free), run the gate (~5 model calls per twin, serial, 12–15 minutes for ten), then
   `python tools/gate_diagnostic.py --prefix <new> --label "stage 4"`. **Do not pool with
   `SYN-14102026`** — different generator version.
3. **Prediction, stated before the run:** `r(driver version means, twin version means)` leaves
   +0.07 and `within-1` rises above 61.4%. Report it honestly if it does not; the correct response
   to a miss is to measure why, never to move a threshold or re-tune a mean.
4. Re-gate the real twin `web_e6b4a70cb63c41a1b124f22bd285116e`, whose verdict predates the prompt
   change, so the one real driver is back in play.
5. Then validity tests 1 and 3 on the fresh batch (free, no model calls) against `docs/08` §4.

---

## 2026-10-13 (stage 4) — Route A ran, and **the prediction failed**: `v10` made the gate worse

Batch `SYN-20261013`, generator `v10`, voice `v4`, ten twins, all ten scored with no provider
failure. **0 of 10 kept**, down from 1 of 10 at stage 3.

The prediction stated before the run was that `r(driver version means, twin version means)` would
leave +0.07 and `within-1` would rise above 61.4%. **Neither happened.** Recorded as a miss
rather than re-tuned, which is the whole point of stating it first.

### The population was held fixed, deliberately

`tools/generate_synthetic.py` passes no spec and so draws `GeneratorSpec`'s defaults —
`sentiment='mixed'` with no `construct_targets`. Stages 1–3 ran on `frustrated` with the preset's
eight targets, `likert_sd` 0.3 and `shared_mood` 0.6. Drawing at the defaults would have changed
the researcher's choice of population while claiming to test a generator change, so the spec was
read back off the stored `SYN-14102026` batch row and reused field for field, with three changes
only: the seed, the name, and `salience_spread` written out explicitly. The clipping pre-flight
reproduces the handoff's figure (37% fairness, 37% clarity), which confirms the population is the
same one.

The seed is `20261013`, in ISO rather than the DDMMYYYY the three stage batches used. That
convention had already collided — today's own DDMMYYYY is the `v8` batch, which is why
`SYN-14102026` carries tomorrow's date — and the prefix is the batch's identity in every
`--prefix` filter, so it should say when the batch was drawn.

### What the batch itself says

The salience clause is in **every** stored persona: 5–12 mentions, first at 7–31% of the way
through, against reactivity's 4–15 at 8–57%. Legibility is not the problem.

All ten respondents weight **pay** highest, as `salience_mix` predicted (84% at the default
spread). So this batch tests **disclosure** — every persona states, in the driver's own words,
that money is what would change their mind — and does **not** test between-driver salience
variation. That asymmetry was recorded before the run and is the right reading of the result.

### Stage 4 against stage 3

| | stage 3 (`v9` + `h3_v4`) | **stage 4 (`v10`)** | |
|---|---|---|---|
| **kept** | 1 of 10 | **0 of 10** | worse |
| mean MAE | 1.325 | **1.575** | worse |
| within-1 | 61.4% | **53.0%** | worse |
| `r(driver version means, twin version means)` | +0.07 | **−0.08** | **worse** |
| twin spread across the six versions | 0.283 (driver 0.475) | **0.199** (driver 0.604) | worse |
| twin H3 between-person spread ÷ driver | 110% | **30%** | worse |
| `r(reactivity band, twin H3)` | +0.37 | **+0.60** (ceiling +0.81) | better |
| within-person ordering FAIR / PUSH / KEEP | +0.40 / +0.35 / +0.39 | **+0.46 / +0.47 / +0.13** | mixed |
| FAIR signed bias | +1.38 | +1.58 | worse |

The version-means figure was recomputed on `SYN-14102026` with the same script and returned
**+0.07 exactly**, so the comparison is between two readings of one measurement, not two
measurements.

**The ranking is the finding.** Every persona in this batch says money is what matters, and the
twin still does not rank the pay versions first:

```
driver:  12220, 11010, 11211, 02200, 02211, 00222
twin:    11211, 12220, 02211, 00222, 02200, 11010
```

`11010` raises pay and the twin ranks it **last**. `02211` raises no pay at all and the twin ranks
it third. Disclosure was necessary — the twin was previously being scored on a constant nobody had
told it — and it was **not sufficient**. The twin is not failing to read which lever this driver
cares about; `r(reactivity band, twin H3)` rose to +0.60, so it reads the persona better than
before. It is failing to connect *what a version changes* to *what this driver said they care
about*.

### The confound, stated

`v10` changes the draw order, so stage 4 **needed a new batch** and therefore changed the
respondents as well as the persona — exactly the confound stage 2 carried and stage 1 and 3 did
not. The driver's own spread across the six versions is larger in this batch (0.604 against
0.475), so the MAE and spread-ratio comparisons above are **not clean**. What is clean, because it
is a within-batch property: every persona discloses the pay weighting, and the twin still ranks
`11010` last.

### Validity tests, scoped to this batch

| test | stage 3 | stage 4 | goal |
|---|---|---|---|
| 1 wrong person | CHECK, gap +0.263, CI [−0.044, 0.569] | **CHECK**, gap **+0.538**, CI [−0.090, 1.165] | PASS |
| 3 naive predictors | FAIL, twin 0.619 vs no-change 0.475 | **FAIL**, twin 1.014 vs no-change 0.896 | PASS |

Test 1's gap now clears the 0.50 threshold and its interval still includes zero, so it stays
CHECK — the between-person distance is 1.44, and the twin recovers 0.54 of it. Test 3 still fails,
with the twin behind both naive predictors; the margin against no-change narrowed in relative
terms (1.30× to 1.13×) and the verdict did not change. One twin had no usable H2 answer for test 3
and is **excluded and reported**, never imputed.

### A real gap found while doing this: the free tests pooled every batch

`run_validity_test(1)` and `(3)` read `h2_vectors(db)`, which returned **every** twin in the
database — four generator versions and the one real driver. `docs/08` §4 test 1 asks whether a
twin is closer to its own driver than to **a stranger's**, and a stranger drawn under a different
construct mapping, lever matrix or reaction gain is not the stranger the test means. This is the
pooling that made one reading of test 3 meaningless, and `tools/gate_diagnostic.py` has required
`--prefix` ever since — the validity path had no equivalent guard.

`h2_vectors`, `_test1`, `_test3` and `run_validity_test` now take `twin_prefix`. The scope is
recorded in the outcome's `detail`, because `validity_results` is append-only and read months
later, and a row that cannot say which population it describes is a row that can mislead. The
argument is **refused** on tests 2 and 4–8 rather than ignored: those read a session's frozen
panel (I10), so the twin set is the session's and not a prefix's. Three tests cover it, including
that a scope matching no twin is `INCONCLUSIVE` and never a `PASS` (I15).

### Where this leaves the diagnosis

Three hidden batch constants have now been removed — the gain was calibrated, reactivity is drawn
and spoken, salience is drawn and spoken — and the twin reads all three signals better at each
step while the **gate** has not moved: 1.219, 1.352, 1.325, 1.575 mean MAE across four stages. The
information defect in the test is repaired. Something else is binding, and the evidence now points
away from the persona and towards the H3 round itself:

1. **The twin's version spread is collapsing, not growing.** 0.126 → 0.283 → 0.199 against drivers
   at 0.475 → 0.604. The twin gives nearly one answer to six worlds, and the `v4` prompt's
   rebalance bought only a temporary widening.
2. **`H3_PROTOCOL = "h3_single_call_v1"`** is the untested structural candidate the handoff
   already names: eighteen numbers for six worlds in one context may be producing one impression
   emitted six times, which is precisely what a collapsing version spread with a *rising*
   person-correlation looks like. Reverting to six calls is **6× the cost and a research
   decision** — the researcher's, not a tuning step. On this evidence it is now the first thing
   to test rather than the second.
3. **`lever_synergy` ignores the reaction weights** (recorded in the Route A entry above) is now
   the only part of the shift still constant across respondents.
4. **The flat-`lever_reactions` question** is live in a way it was not before. This batch shows
   that disclosing a pay-dominated weighting does not fix version ranking; a batch with flatter
   means would put drivers who want *different* things in the panel and would test whether the
   twin can discriminate on salience at all. That is a claim about the population and remains the
   researcher's.

### The real driver re-gated, and it passes where every synthetic twin fails

`web_e6b4a70cb63c41a1b124f22bd285116e`'s verdict predated the prompt change, which is the
fingerprint fix behaving correctly. Re-gated under the live config: **KEPT**, H3 MAE **0.694**,
within-1 **91.7%** over 36 items and two repeats.

**This is the most informative number of the stage.** The same prompt, the same model, the same
thresholds and the same gate that dropped all ten synthetic twins at MAE 1.11–2.14 scored the one
real driver at 0.694. The gate is not broken and the twin agent is not broken. Whatever is left is
a property of the **synthetic driver** — of how the generator says a described change moves
someone — and not of the instrument that scores it. Panel-eligible twins: 1, the real one, as
before.

### Unchanged

`mae_max` 1.0, `pct_within_1_min` 0.80, `h3_verdict`, `qualified_twin_ids`, every line of the
gate, `reaction_gain` at its fitted value, and `lever_reactions`' means as the researcher set
them. `kept` was not written on any row that failed. No eligibility route was added. Nothing was
deleted: `SYN-12102026`, `SYN-13102026` and `SYN-14102026` and all their `twin_quality_runs` rows
are intact, and stage 4 is a fourth batch beside them, never pooled with them.

---

## 2026-10-13 (diagnosis) — why the real driver passes: **it is not the persona, and the real PASS is weak evidence**

Asked to find why `web_e6b4a70…` passes the H3 gate at MAE 0.694 while all ten `v10` synthetic
twins fail at 0.89–2.83. Measured on `SYN-20261013` and the real driver, read-only, no model
calls. Four findings, in the order they settle the question.

### 1. The persona is not the problem — it is close to perfect

On the two control cells, which ask about the world **as it is**, the twins reproduce their
driver's 37 battery answers to:

| | `00000` | `SHAM` |
|---|---|---|
| real twin | 0.06 | 0.39 |
| ten synthetic twins | **0.18** | **0.25** |

Against a cap of 1.0. A persona that lets a model reproduce a stranger's 37 survey answers to a
fifth of a scale point is carrying the person. The two passages are also structurally identical —
12 paragraphs, no headings, same shape — the synthetic one merely longer (1828 words against 960,
because a synthetic respondent answers all 37 why-probes and this real one wrote less).

**The persona hypothesis is refused on evidence.** Whatever fails, fails only at the step where
the twin is asked to imagine a described change.

### 2. The twin is version-blind, and it is version-blind in both cases

Spread of a twin's answers across the six Part 17 versions, against its driver's own:

| | driver | twin |
|---|---|---|
| real | **0.17** | 0.52 |
| synthetic (range over ten) | 0.46–1.03 (mean 0.66) | 0.12–0.42 (mean 0.30) |

`r(driver version means, twin version means)` is +0.74 for the real twin and −0.08 across the
synthetic batch. The twin gives nearly one answer to six worlds. **That behaviour is the same for
both.** What differs is the driver.

### 3. The real driver is as flat as the twin is. That is the whole of the PASS

The one real respondent's Part 17, as they answered it:

```
version    FAIR  PUSH  KEEP
00222         6     2     6
02200         5     3     5
02211         5     3     5
11010         5     3     5
11211         6     2     6
12220         6     2     6
```

**Two distinct response patterns across six described worlds, and a range of exactly 1 point on
every question.** Not straight-lining — they discriminate sharply between the three outcomes — but
they do not discriminate between the versions. A version-blind twin matches them almost exactly.

The decisive measurement. A **version-blind oracle** — a twin that reads the person perfectly and
completely ignores which version it was asked about, answering each outcome's own mean — scores:

| | oracle MAE | passes the 1.0 cap? |
|---|---|---|
| real driver | **0.50** | yes, with room to spare |
| ten synthetic drivers | **1.01** | 5 of 10 fail |

**So the gate, as applied to this real driver, does not require version discrimination; as applied
to a synthetic driver it requires it absolutely.** That is the pass and the ten failures, in one
number.

**The consequence for the study is the serious part.** `docs/08` §2.3 says H3 exists to test
*whether the mapping from stimulus to response transfers*, not just the level. The real twin's
PASS does not establish that: it is a score a version-blind twin also earns against this
particular driver. "1 of 1 real twins kept" must not be read as evidence that the twin transfers
the counterfactual mapping. It is evidence that the twin reads the person — which the control
cells already showed at 0.06.

This is the same failure mode `CLAUDE.md`'s own warning names — a twin answering a near-constant
vector scoring a respectable MAE — one level up: not constant across items, but constant across
*versions*.

### 4. Secondary, and separable: the floor pile-up drives the level bias

Six of ten synthetic drivers start at or next to the scale's floor on fairness (`FAIR` baseline
1.00–1.25; batch mean 1.55). The real driver starts at 3.00. **16% of all synthetic battery
answers are a literal `1`; the real driver has none.**

`r(driver's H3 starting baseline, twin's signed error) = −0.77` over the ten. The lower a driver
starts, the more the twin over-shoots — +1.67 for the driver at `FAIR` 1.00, −0.11 for the one at
3.25, −0.11 for the real driver at 3.00. That is the whole of the `FAIR` +1.58 signed bias.

The mechanism is structural, and it is in the generator: `reaction_shift` is **additive and
level-independent** — it never reads the driver's baseline — so `_item_target` computes
`baseline + shift` and clamps. The generator therefore asserts that a driver at 1.0 and a driver
at 5.0 both move by the same ~2.2 points under the same package. A model reading "nothing about
this work is fair" and then a described living wage, an appeals route and a union moves that
person much further. Neither is verifiable at n=1.

Note what this is **not**: the *magnitude* of movement is calibrated and agrees. The synthetic
drivers move 2.17 from their own baseline on average; the real driver moved 2.47. `reaction_gain`
fitted the level correctly. What is wrong is **where that movement starts from** (finding 4) and
**how much it varies between versions** (finding 3).

### Why Route A failed, in hindsight

`v10` pushed the batch's driver spread across the six versions **up**, 0.475 → 0.604. The one
real respondent's is 0.17. Route A therefore moved the synthetic driver *further from* the only
real behaviour on record, which is why the version correlation went +0.07 → −0.08 and the MAE
rose. Adding per-respondent lever salience amplified exactly the thing the real data does not
exhibit. The information defect it fixed was real; the axis it amplified was the wrong one.

### What this does and does not license

**Not licensed.** Softening `lever_effects` or the gain until twins pass. The twin is version-blind
and the synthetic driver is version-sensitive; closing that gap by flattening the generator would
be fitting the generator to the twin's weakness — `docs/08` §2.4's circularity, and it would make
every path estimated on synthetic data an artefact of what the model cannot do.

**Open, and it needs data rather than a decision.** Whether real drivers differentiate the six
packages at all. One respondent gave a 1-point range. If that is typical, H3-as-fidelity-gate is
asking twins to reproduce a discrimination the population does not make, and the generator's
`lever_effects` shape is the thing out of line. If it is atypical — a tired respondent, or six
scenarios that read alike to them — the generator may be right and the twin simply cannot do H3.
**These point to opposite fixes and n=1 cannot separate them.** Re-derive with
`calibrate_reaction_gain` and a version-spread statistic as real Part 17 responses arrive.

### Recommended next, in order

1. **Report the version-blind oracle MAE beside every gate verdict** (`tools/gate_diagnostic.py`).
   Free, read-only, no new concept: it says whether a given PASS required version discrimination
   or not, and it is what would have stopped the real twin's PASS being over-read. Do this first
   because it is cheap and it changes how every later number is read.
2. **Move the population off the floor** — `construct_targets` for `FAIR`/`TRAN` off 2.0, or a
   lower `between_driver_swing`. Addresses finding 4 and the +1.58 bias; the preview already warns
   about it. **Researcher's choice of population**, and it will not touch finding 3.
3. **Test `H3_PROTOCOL`** — six calls instead of one. This is the only candidate that addresses
   finding 3 from the twin's side, and finding 3 is the binding one. 6× cost and a research
   decision.
4. **Collect real Part 17 responses.** Nothing above settles whether the generator's version
   differentiation is credible, and no amount of twin running will.

---

## 2026-10-13 (`v11`) — the holdout answers report a hypothetical coarsely, calibrated to the one real respondent

Directed by the researcher, following the diagnosis above: take the real respondent's **one-point
range across the six Part 17 versions** as the target and fix the generator.

`GeneratorSpec.holdout_version_differentiation`, fitted with the gain by
:func:`calibrate_reaction_model` against that respondent's own survey answers — **never against a
twin's output or a pass rate** (`docs/08` §2.4). Joint fit over their 18 Part 17 items:

| | gain | differentiation | mean error on those 18 answers |
|---|---|---|---|
| `v8` one-parameter fit | 2.11 | — (implicitly 1.0) | 0.863 |
| **`v11` joint fit** | **2.40** | **0.18** | **0.392** |

The generator can now reproduce a real driver's counterfactual answers **well inside the gate's
own 1.0 cap**, which it could not before. `2.11` remains the correct one-parameter fit and
`calibrate_reaction_gain` still returns it; both constants are pinned in tests so neither can
drift unnoticed.

### The first implementation was wrong, and it was rejected on measurement

The obvious place to put the shrinkage is inside `reaction_shift`, and that was built and
measured first. It fitted the respondent beautifully — the 0.863 → 0.392 above is that fit — and
it was **thrown away**, because shrinking toward a mean over all codes mixes every lever's row
into every code:

| at `0.18` | inherited | compressed inside `reaction_shift` |
|---|---|---|
| conditions-only code's effect on **clarity** | **0.000** ("that zero is a claim") | **+1.028** |
| sub-additivity on pushback (`extra`) | **−0.72** (sub-additive) | **+2.10** (super-additive) |

That is the pre-`v5` defect restored — no lever distinguishable from another by its effects, so no
path estimated on synthetic data corresponds to anything — and it **inverts** the sub-additivity
`docs/07` §5 calls the study's contribution. Buying a pass rate with that would have been
worthless in a paper. The mistake was conflating two separate facts about the same person: the
protections moved them **2.47 points** from their own baseline, *and* they reported six
hypotheticals in a **one-point range**. The first is about construct dynamics; the second is about
answering a hypothetical battery.

So the compression lives in `_item_target`, on the **holdout answer**. `reaction_shift` is
byte-identical at every value of the parameter — asserted directly — so the lever matrix, its
zeros, its signs, its two interactions, the sweep, `analysis/interactions.py` and the PLS-SEM are
untouched.

### Scope: Part 17 only, and that was also found by measurement

Applied to both holdout blocks at first. That was wrong for the same reason, one level down: Part
16 asks **one** hypothetical — the respondent's own assigned arm — so there is no across-version
spread to compress, and shrinking a single code toward the mean over all codes is not a
compression but a **level shift** away from what that arm implies. The level of an H2 answer is
`reaction_gain`'s to set, and it is calibrated.

Measured on the stage-5 batch before the scope was narrowed:

| H2 / validity | compression on H2 too | H3 only |
|---|---|---|
| `mae_own` (test 1) | 2.00 | 0.95-class |
| between-person distance | 1.20 | 1.44-class |
| validity test 1 | **FAIL** (gap −0.01) | CHECK-class |

Every respondent's H2 answers had converged on the same mean, which is the between-person signal
test 1 reads. `holdout_version_differentiation` now applies only where `item.role ==
"holdout_h3"`.

### Mechanics

`mean_shift` is the mean of `reaction_shift` over **every code that raises something** — a
property of the spec and the respondent, not of the code being asked about, which is what lets the
parameter mean the same thing for Part 17's six and the sweep's 243, and what makes the mean a
fixed point so the parameter is close to orthogonal to the gain. Computed in closed form (each
lever's dial is uniform on `{0,1,2}`, so a lever contributes `(1 + second_step_factor)/3` steps and
is raised with probability `2/3`; the synergy pairs need `4/9`; dropping the all-zero code is one
rescale by `243/242`) and asserted against brute-force enumeration of all 242 codes, because a
wrong constant there would bias every holdout answer and nothing else in the suite would catch it.

**`00000` is zero at every value of the parameter**, and that is the invariant rather than an edge
case: a non-zero control cell would offset every comparison in the study.

A respondent's own `reactivity` draw sits inside the mean, so **person-discrimination is
untouched** and only version-discrimination compresses. That is the exact opposite of `v10`'s
mistake, where the axis that grew was the wrong one.

### Stage 5 — measured

Batch `SYN-2026101311`, ten twins, all scored. Population held identical to `SYN-14102026`
(`frustrated`, swing 2.4, the same eight construct targets, `likert_sd` 0.3), so the generator
change is the only change.

| | stage 4 (`v10`) | **stage 5 (`v11`)** | |
|---|---|---|---|
| **kept** | 0 of 10 | **2 of 10** | better |
| mean MAE | 1.575 | **1.092** | better |
| within-1 | 53.0% | **70.8%** | better |
| H3 between-person spread recovered | 30% | **99%** | better |
| H2 spread recovered | 82% | 116% | — |
| `r(band, twin H3)` | +0.60 | +0.58 (ceiling +0.65) | — |
| FAIR / PUSH / KEEP signed bias | +1.58 / −0.90 / +1.12 | **+0.95 / +0.47 / +0.25** | better |
| **version-blind oracle MAE** | 1.00, 4 of 10 under cap | **0.32, 10 of 10** | — |

Driver spread across the six versions, per person: **0.575 → 0.222**, against the real
respondent's 0.167.

**The prediction, stated before the run, was 3–7 kept and mean MAE 1.0–1.2.** The MAE landed in
range at 1.092. The kept count came in **below** it at 2. Recorded as a partial miss.

### What now binds, and it is not the generator's reaction model

The oracle bound says it plainly: a version-blind twin would now score **0.32** against these
drivers and the twins scored **1.092**. The version axis is no longer the obstacle — the twins are
now far worse than version-blindness would be, so the residual is **level and person error**, not
version error.

And its mechanism is the one the diagnosis already named:
`r(driver's H3 starting baseline, twin's signed error) = **−0.66**` over the ten (was −0.77).
Fairness baseline **1.51** across the batch; **15% of all synthetic battery answers are a literal
`1`**; the real driver has none and sits at 3.00.

**The floor pile-up is now the binding constraint**, and it is `docs/06` §4's
`construct_targets`/`between_driver_swing` — the **researcher's choice of population**, flagged in
the handoff and warned about in the Generator preview, and **not changed here**. The prediction, to
be stated before any run that tests it: moving `FAIR`/`TRAN` off `2.0` removes most of the
remaining +0.95 bias.

### Instrument

`tools/gate_diagnostic.py` gains two things.

**The version-blind oracle bound**, reported beside every verdict. A twin that reads the person
perfectly and ignores which version it was asked about scores it, so where it sits under the cap a
PASS does **not** demonstrate the thing H3 exists to test (`docs/08` §2.3). On the real driver it
is 0.50; that is why "1 of 1 real twins kept" must not be read as evidence that the twin transfers
the counterfactual mapping.

**A refusal when a prefix spans more than one batch.** Found the hard way and by the measurement
itself: seeds `20261013` and `2026101311` produce `SYN-20261013-…` and `SYN-2026101311-…`, so the
shorter prefix silently matched both and the diagnostic reported **eleven** twins for a batch of
ten — the exact pooling the flag exists to prevent, arriving through the flag. The guard is on the
`batch_id`, not the generator version, because two batches drawn under one version are still two
different draws of respondents (rule 10).

### Unchanged

`mae_max` 1.0, `pct_within_1_min` 0.80, `h3_verdict`, `qualified_twin_ids`, every line of the gate,
`lever_reactions`' means, the whole of `reaction_shift` and `data/reference/*.json`. `kept` has
never been written on a row that failed and no eligibility route was added. `VOICE_VERSION` stays
at `v4` — no bank changed. Nothing was deleted; stage 5 and the corrected batch sit beside the
four earlier ones and are never pooled with them.

### Stage 6 — the scope fix, re-run, and what it settles

Batch `SYN-20261014`, `v11` with the compression on Part 17 only, ten twins, all scored.
**A new seed, so a different draw of respondents** — the same confound stages 2, 4 and 5 carried,
and it bit here: this batch drew almost no reactivity variation at all
(`r(band, DRIVER h3) = +0.09`, against +0.65 in stage 5), so its reactivity column says nothing
and its MAE is not cleanly comparable with stage 5's.

| | stage 4 (`v10`) | stage 5 (`v11`, H2 too) | **stage 6 (`v11`, H3 only)** |
|---|---|---|---|
| kept | 0 of 10 | 2 of 10 | **1 of 10** |
| mean MAE | 1.575 | 1.092 | **1.214** |
| within-1 | 53.0% | 70.8% | **66.4%** |
| FAIR signed bias | +1.58 | +0.95 | **+0.97** |
| PUSH / KEEP signed | −0.90 / +1.12 | +0.47 / +0.25 | **+0.02 / −0.20** |
| oracle MAE (under cap) | 1.00 (4/10) | 0.32 (10/10) | **0.35 (10/10)** |
| validity 1 | CHECK, gap +0.538 | **FAIL**, gap −0.01 | **CHECK**, gap +0.39 |
| validity 3 | FAIL, 1.014 vs 0.896 | CHECK, 2.000 vs 2.094 | **FAIL**, 0.618 vs 0.375 |

**The scope fix did what it was for.** Validity test 1 is back from FAIL to CHECK and the H2
errors fall by two thirds (test 3's twin error 2.000 → 0.618), because H2 answers are once again
what the respondent's own arm implies rather than a batch mean. Stage 5's test-1 FAIL and its
flattering test-3 CHECK were both artefacts of compressing H2, and both are withdrawn.

**What `v11` settles, and it is batch-independent.** Across two different draws of respondents:

* the **version axis is no longer the obstacle** — the version-blind oracle is 0.32 and 0.35, under
  the cap for 10 of 10 in both, against 1.00 and 4 of 10 at `v10`. The generator's drivers now
  discriminate the six packages about as much as the one real respondent does;
* the twins are now **much worse than version-blindness would be** (1.09 and 1.21 against 0.32 and
  0.35), so the residual is level and person error;
* **fairness bias is +0.95 and +0.97** in both, with `r(driver's starting baseline, twin's signed
  error)` at −0.66, fairness baseline 1.51 and **15% of battery answers a literal `1`**.

**So the floor pile-up is the binding constraint and the generator's reaction model is no longer
it.** That is `docs/06` §4's `construct_targets` and `between_driver_swing` — the researcher's
choice of population, warned about in the Generator preview, and **not changed here**.

**The gate improvement is real but small: 0–1 of 10 before, 1–2 of 10 after.** The honest reading
is that `v11` removed one of two obstacles and the second is untouched. Nothing was tuned to
improve a pass rate, and the error on the **real** respondent — the only external check that
exists — more than halved, 0.863 to 0.392, which is the result that matters most and does not
depend on any synthetic batch.

---

## 2026-10-13 (stage 7) — the floor fix: **the prediction failed, and it corrected my own diagnosis**

Directed by the researcher. `construct_targets` for `FAIR` and `TRAN` raised from `2.0` to `3.0`
on batch `SYN-20261015`, `v11`, everything else identical.

**Chosen against a stated criterion, not a pass rate:** the smallest raise that brings both
constructs under 10% pinned at the scale's end — `3.0` gives 6% and 7%, against 38% and 38% at
`2.0`. Corroborated by the one external anchor that exists: the real respondent's own `FAIR`
baseline is 3.00 and their `TRAN` is 2.50. The population keeps its frustrated character — both
stay below the 4.0 midpoint and `EXPO` 6.5, `CTRL` 6.0, `VOIC` 5.5, `EXIT` 5.5 are untouched.
`SATI` and `LOYA` remain 20% pinned and `EXPO` 12%; they are not Part 17 outcomes and were not
part of this change.

**Prediction, stated before the run: most of the +0.97 fairness bias goes, mean MAE 0.9–1.1, kept
3–6 of 10.**

### Result: the first half was right, the second half was wrong

| | stage 6 (floor at 2.0) | **stage 7 (floor at 3.0)** |
|---|---|---|
| FAIR signed bias | +0.97 | **+0.30** |
| PUSH / KEEP signed | +0.02 / −0.20 | **−0.17 / +0.08** |
| `FAIR`/`TRAN` pinned at an end | 38% / 38% | **6% / 7%** |
| mean MAE | 1.214 | **1.239** |
| within-1 | 66.4% | **61.9%** |
| **kept** | 1 of 10 | **0 of 10** |

The floor fix did precisely what it was aimed at. **All three signed biases are now
approximately zero and the gate did not move at all.**

### Why the prediction was wrong, and it is a real correction

Decomposing each twin's 18 H3 errors into the part explained by a per-outcome offset and the part
left over:

| | n | actual MAE | scatter | per-outcome offset |
|---|---|---|---|---|
| `SYN-20261015` (floor moved) | 10 | 1.22 | **0.71** | **1.03** |
| `SYN-20261014` (floor at 2.0) | 10 | 1.13 | **0.65** | **1.01** |
| **the real driver** | 1 | **0.78** | **0.63** | **0.78** |

Two things fall out, and the second is the correction.

1. **Scatter is the same for everybody — 0.63 to 0.71 — and it is comfortably under the 1.0 cap.**
   The twin's noise is not the problem and never was.
2. **The whole of the difference between pass and fail is the per-outcome offset: 0.78 for the real
   driver against 1.03 for the synthetic ones.** And the floor fix did not touch it: 1.01 → 1.03.

**The error I made was reading a batch-level signed bias as if it were the per-person error.** A
signed bias near zero and a per-outcome offset near 1.0 are perfectly compatible: the twin is off
by about a point on each outcome for each person, in **different directions for different people**,
so the batch mean cancels. The floor was driving the *mean* (fairness +0.97 → +0.30, exactly as
predicted) and the mean was never what the gate scores. The handoff's own standing warning applies
to the diagnosis as much as to the fix: a statistic that averages over people can hide the thing
that decides every individual verdict.

So **the floor pile-up was not the binding constraint.** It was a real defect, it is now fixed, and
fixing it bought nothing at the gate. Recorded as a miss.

### What is left, and the evidence now points at the twin rather than the generator

Every generator property that has been checked against reality is now right:

* it reproduces the one real respondent's 18 Part 17 answers at **0.392**, inside the gate's own cap;
* its drivers' spread across the six versions matches that respondent's (0.22 against 0.17);
* the version-blind oracle is **0.30, under the cap for 10 of 10** — version differentiation is not
  what is failing;
* nothing is pinned at the scale's ends on the Part 17 outcomes;
* all three signed biases are approximately zero.

What remains is the twin's **per-person, per-outcome level accuracy**: it places fairness, pushback
and staying each about one scale point away from where that driver sits, and the direction varies
by person. On a 7-point scale against a cap of 1.0 and an 80%-within-1 threshold, that is the
whole margin.

**A per-outcome offset with near-zero version signal is the exact signature of the single-call H3
protocol** (`H3_PROTOCOL = "h3_single_call_v1"`, M19 WP-3): eighteen numbers for six worlds in one
context produces one impression per outcome, emitted six times with noise — which is a constant per
outcome plus scatter, which is what the table above measures. That candidate has been on the list
since stage 2 and is now the only one the evidence supports. It is **6× the cost and a research
decision**, the researcher's and not a tuning step.

**And the real twin's PASS should be read with the same table.** Its offset is 0.78 against the
synthetic 1.03 — a quarter of a scale point, not a different regime. One real driver passing at
0.694 and ten synthetic drivers failing at 1.22 is, on this evidence, the same mechanism with a
slightly better draw, and there is no basis at n=1 for deciding whether real drivers are genuinely
easier to predict.

### Unchanged

`mae_max` 1.0, `pct_within_1_min` 0.80, `h3_verdict`, `qualified_twin_ids`, every line of the gate,
`reaction_shift`, the lever matrix, `reaction_gain` and `holdout_version_differentiation` at their
fitted values. `kept` has never been written on a row that failed. Nothing was deleted. The floor
change is on this batch's own spec row; `config/generator.default.yaml` still carries `FAIR`/`TRAN`
at `2.0`, because the population is the researcher's to set and stage 7 is one batch, not a new
default.

---

## 2026-10-14 (stage 8) — six-call H3 **refuted**, and the thing that was actually wrong all along

The last experiment. `H3_PROTOCOL` restored as a selectable six-call protocol
(`h3_six_calls_v1`), run on **the same batch, the same twins and the same personas** as stage 7 —
a clean protocol-only comparison, which only stages 1 and 3 have been.

### The hypothesis was wrong

| | stage 7 (one call) | **stage 8 (six calls)** |
|---|---|---|
| kept | 0 of 10 | **2 of 10** |
| mean MAE | 1.239 | **1.378** |
| within-1 | 61.9% | 62.5% |
| per-outcome **offset** | 1.03 | **1.11** |
| **scatter** | 0.71 | **0.79** |
| H3 version spread recovered | 57% | **30%** |
| `r(reactivity band, twin H3)` | +0.64 | **+0.26** |

Two twins crossed the line and **both error components got worse**. Isolating the six versions
removed the comparison the twin had been making and added noise; it did not touch the per-outcome
offset, which was the entire reason to try it. The single context was **not** the cause.

The protocol stays available and selectable (`TWINLAB_H3_PROTOCOL=six`), recorded on every row and
in `current_config`, and **the shipped default is unchanged** — it is 6× the cost and now measured
to be worse.

### What was actually wrong: the twin and the generator answer at different granularities

The distribution of the 180 H3 answers, synthetic batch, twin against driver:

| answer | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| synthetic **driver** | 10% | 3% | 18% | 22% | 23% | 14% | 9% |
| the **twin** | 2% | **27%** | 4% | 2% | **18%** | **43%** | 4% |
| the one **real** driver | 0% | 17% | 17% | 0% | 33% | 33% | 0% |

Means agree (4.25 against 4.53) and spreads agree (twin sd 109% of driver's). **The shapes do
not.** The twin spends 88% of its answers on just `2`, `5` and `6`, and almost never says `3` or
`4` (6% combined). The generator's driver uses all seven points on a smooth graded curve. And the
one real respondent on record used **four** values — `2`, `3`, `5`, `6`, and never `1`, `4` or
`7` — which is the twin's own coarse pattern, not the generator's smooth one.

So the twin answers in a few coarse buckets — "low", "high", "fairly high" — and so does the real
human. The **generator** answers on a continuum, because that is what its arithmetic produces:
`_likert` rounds a normal draw around a continuous target, so every point on the scale gets used
in proportion. A twin with three buckets cannot land within one point of a driver who answers
`3`, `4` and `7`, however well it reads the person.

Two hypotheses were tested against this and both refuted, so the finding is specifically about
granularity and not about level:

* **regression to the midpoint** — refuted: the twin's sd is 109% of the driver's, and
  `r(how far the driver sits from the midpoint, twin's error) = −0.26`, so extreme answers are if
  anything predicted slightly *better*;
* **level bias** — refuted at stage 7: all three signed biases were driven to approximately zero
  and the gate did not move.

### The whole record, in one table

Every stage, its own targeted metric, and the gate:

| stage | change | mean MAE | kept | its own target metric |
|---|---|---|---|---|
| 0 | anchors + gain + reactivity | 1.517 | 0/10 | level bias +2.88 → +1.77 |
| 1 | H3 prompt `v3` | 1.219 | 0/10 | **moved** (bias → +0.18) |
| 2 | legible reactivity `v9` | 1.352 | 0/9 | **moved** (r −0.08 → +0.87) |
| 3 | H3 prompt `v4` | 1.325 | 1/10 | **moved** (pushback order −0.21 → +0.35) |
| 4 | `v10` lever salience | 1.575 | 0/10 | **missed** (+0.07 → −0.08) |
| 5 | `v11` holdout compression | 1.092 | 2/10 | **moved** (oracle 1.00 → 0.32) |
| 6 | `v11` scope corrected to H3 | 1.214 | 1/10 | **moved** (test 1 FAIL → CHECK) |
| 7 | floor moved off the wall | 1.239 | 0/10 | **moved** (biases → ~0) |
| 8 | six-call H3 | 1.378 | 2/10 | **missed** (offset 1.03 → 1.11) |

**Nine stages. Seven of the nine moved their own target metric. The gate never moved.** Mean MAE
has sat between 1.09 and 1.58 throughout, and `kept` between 0 and 2 of 10.

That pattern is the finding, and the decomposition says why: across every stage and every
protocol, the twin's error is **scatter of 0.62–0.79 plus a per-outcome offset of 1.01–1.11**,
and nothing any stage changed touched the offset. The real driver's offset is 0.59–0.78, which is
the only reason it passes, and at n=1 there is no way to know whether that is typical of real
drivers or one lucky respondent.

### What this licenses, and what it does not

**Established, and worth keeping:**
* the persona is sound — the twins reproduce their driver's 37 battery answers to **0.18** of a
  point on the control cells;
* `reaction_gain` and `holdout_version_differentiation` are calibrated to the one real respondent
  and reproduce their 18 Part 17 answers at **0.392**, inside the gate's own cap;
* version differentiation is solved — the version-blind oracle is **0.30**, under the cap for 10
  of 10;
* nothing is pinned at the scale's ends on the Part 17 outcomes and all three signed biases are
  approximately zero;
* six-in-one-context is **measured to be better than six-in-isolation**, which was previously a
  documented assumption (M19 WP-3) and is now a result.

**The open question, and it is now sharp.** A twin and a real respondent both answer a
hypothetical battery in a few coarse buckets. The generator answers on a continuum. Either:

1. **real respondents answer coarsely**, in which case the generator's `_likert` draw is the
   remaining defect — it should produce a respondent who uses a few anchor values, not a smooth
   rounded normal — and the gate is currently asking twins to reproduce a granularity no human
   produces; or
2. **this one respondent happened to answer coarsely**, in which case the generator is right and
   the twin cannot resolve a 7-point hypothetical to within one point, which is a limit of the
   method and belongs in the paper as one.

**These point to opposite actions and n=1 cannot separate them.** Deciding by trying both against
the gate would be choosing a generator to suit the model, which is `docs/08` §2.4's circularity.
**It needs real Part 17 responses** — specifically the *distribution* of their answers, not only
the mean, which is a statistic no stage so far has had enough data to read.

Nothing was tuned to a pass rate at any point. `mae_max` 1.0 and `pct_within_1_min` 0.80 are
untouched, as are `h3_verdict`, `qualified_twin_ids`, every line of the gate, `reaction_shift` and
the lever matrix. No `kept` was written on a row that failed. Nothing was deleted; eight batches
exist and are never pooled.

---

## 2026-10-14 (`v12`) — respondents do not sit on the ends of a scale. **Generated, not yet gated.**

`_likert` **clamped** a rounded normal draw to the scale, so every respondent whose latent
position sat past an end landed exactly on it. The endpoint pile-up was created by the clamp:
14–19% of seven-point answers. Under-using the outermost options is a documented property of
Likert response, and the one real respondent on record used an endpoint **0 times in 39
seven-point answers** (21 battery, 18 Part 17). The generator was asserting a response style no
human in the data exhibits — and the endpoints are where a twin's error concentrates.

`GeneratorSpec.endpoint_avoidance = 0.70`: an endpoint answer is moved one step inward with that
probability. Chosen as **the smallest value that brings endpoint use inside what 0 of 39
supports** — 5% on the battery and 7% on Part 17, against a 95% upper bound of about 9% — the same
"smallest raise meeting a stated criterion" basis the floor fix used. **Not chosen against a twin
pass rate**, which is `docs/08` §2.4's circularity.

Applied to **every** Likert answer the respondent gives, battery and both holdout blocks: a
response style is a property of the person, and someone who avoids the ends describing today does
not stop when imagining a change. `_likert` draws one extra uniform per item, unconditionally so
the stream does not depend on earlier answers' content, so **a `v11` seed does not reproduce under
`v12`**. `VOICE_VERSION` stays `v4`.

### Batch `SYN-20261016`, drawn and stored. Part 17, seven-point items:

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | ends | in 2–6 |
|---|---|---|---|---|---|---|---|---|---|
| real respondent | 0% | 17% | 17% | 0% | 33% | 33% | 0% | **0%** | **100%** |
| `v11` batch | 10% | 3% | 18% | 22% | 23% | 14% | 9% | **19%** | 81% |
| **`v12` batch** | 6% | 17% | 14% | 14% | 23% | 25% | 1% | **6%** | **94%** |
| the twin (measured) | 2% | 27% | 4% | 2% | 18% | 43% | 4% | **6%** | **94%** |

Battery endpoints: real 0%, `v11` 14%, **`v12` 4%**.

**The generator's endpoint rate now matches the twin's exactly (6% / 6%) and sits inside what the
human's 39 answers support.** Note what has *not* changed: the twin still spends 70% of its
answers on `2`, `5` and `6` and almost nothing on `3` or `4`, while the `v12` driver spreads 14%
on `3` and 14% on `4`. The granularity mismatch identified at stage 8 is narrowed at the ends and
**untouched in the middle**, so the per-outcome offset has no particular reason to move. That is
the honest expectation to hold before any gate run, and it is why this was not run.

### Not gated

**No model calls were spent on this batch.** 1,115 tests pass; ruff, import-linter and
`build_reference --check` clean. The gate run is ~50 calls and 10 minutes whenever the researcher
wants it, and `tools/gate_diagnostic.py --prefix SYN-20261016` will read it without pooling.

**What the fix does and does not claim.** It removes a generator defect that was real and
independently justified: the clamp was manufacturing a response style the data contradicts, and
the floor pile-up diagnosed at stage 7 was one symptom of the same mechanism. It is **not** an
attempt to make twins pass, and it should not be read as one if the gate improves — nor as a
refutation if it does not.
