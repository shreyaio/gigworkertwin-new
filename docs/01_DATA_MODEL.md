# 01 — Data model

Reference data, the item register, the legacy crosswalk, and the full Postgres schema.

Normative. Where this states a count, a key or a column, that is the specification.

---

## 1. The three kinds of data

**Frozen reference data** is the scientific artifact. Generated once from the source documents by
`ingest/build_reference.py`, committed to `data/reference/`, seeded into Postgres, and **never
written by the running application**. If it changes, it changes by re-running the builder against
edited sources and bumping a version — never by an `UPDATE`.

**Operational evidence** is what the platform produces and a reviewer may audit: submissions,
answers, runs, renders, quality scores, validity results, events. **Append-only.** "Latest" is a
pointer flipped in the same transaction (I9).

**Mutable state** is the small set of things that are genuinely state rather than evidence:
`sessions.status`, `sessions.cursor_index`, `agent_configs`, `app_config`. Every one of them is
versioned on write and frozen onto the runs that used it.

The test for which bucket something belongs in: *would a reviewer ever ask "what did this look
like before?"* If yes, it is evidence and it is append-only.

---

## 2. Reference files

Ten files. Counts are exact and are asserted by the builder — a mismatch is a build failure, not a
warning. `build_reference.py --check` exits non-zero if any byte drifted.

| File | Rows | Source | Primary key |
|---|---:|---|---|
| `criteria.json` | 33 | `Fairwork_LocationBased_Principles_verbatim.md` | `criterion_id` |
| `criterion_findings.json` | 33 | Codebook Table C | `criterion_id` |
| `gaps.json` | 30 | Codebook Table D | `gap_id` (= `criterion_id`) |
| `thresholds.json` | 10 | Codebook "Threshold outcomes" | `threshold_id` |
| `corpus_chunks.json` | 126 | `Uber_India_Policy_Corpus_Fairwork_Levers.md` | `chunk_id` |
| `chunk_criterion_links.json` | 171 | Codebook Table B | `link_id` |
| `instrument.json` | 73 items, 5 scales, 9 constructs, 6 metrics | `Survey_Research_GIGWORKER_v2.md` | `item_id` |
| `dial_lookup.json` | 5 levers × 3 dials | derived from `gaps.json` | — |
| **`arms.json`** | 4 | Survey Part 15 + `ARCHITECTURE.md` §5.3 | `arm_id` |
| **`legacy_crosswalk.json`** | 24 | this document, §4 | `legacy_id` |

The last two are **new in 2.0**. Everything above them is unchanged and must not be regenerated.

**On 161 vs 171.** The codebook records **161 evidence rows**. A row may cite several extracts, so
expanding rows to chunk × criterion pairs gives **171**. Both figures are correct and both appear
in the codebook's own front matter. Do not "fix" either number.

**Findings distribution** (asserted by the seeder): `Partly met 12 · Not met 10 · No evidence
found 6 · Met 3 · Contradicted 2 = 33`. The three `Met` rows are `3.1.a`, `3.1.c`, `4.1.c` and they
are the SHAM commitment set.

**Gap types:** `INTRODUCE 11 · EXTEND 9 · REMOVE 6 · UNIVERSALISE 2 · DOCUMENT 2 = 30`.

**Link judgements:** `PARTIAL 66 · CONTRADICTS 52 · SUPPORTS 31 · ASSERTED 16 · SCOPE LIMITED 6
= 171`.

**Already met, so never a gap:** `3.1.a`, `3.1.c` (Contracts) and `4.1.c` (Management). This is why
L3 dial 1 has four gaps rather than six and L4 dial 1 has three rather than four — and it is why
the sham has content to describe.

---

## 3. The item register

`instrument.json`, version **2.1**. 73 items. IDs are stable and are the addressing scheme for the
persona templates, the round prompt, the metrics, the Form map and the database. **Never renumber.**

### 3.1 Blocks

| Block | Part | IDs | n | Scale | Role |
|---|---:|---|---:|---|---|
| `AMQ` | 5 | `AMQ1`–`AMQ6` | 6 | agree7 | trait (`AMQ6` = attention) |
| `PAC` | 6 | `PAC1`–`PAC11` | 11 | **agree5** | trait |
| `FAIR` | 7 | `FAIR1`–`FAIR4` | 4 | extent7 | outcome — *fairness* |
| `CLAR` | 8 | `CLAR1`–`CLAR3` | 3 | **agree5** | outcome — *clarity* |
| `SAT` | 9 | `SAT1`–`SAT3` | 3 | agree7 | outcome — *happiness* |
| `CONT` | 10 | `CONT1`–`CONT2` | 2 | **agree5** | outcome — *staying* |
| `ALGO` | 11 | `ALGO1`–`ALGO5` | 5 | agree7 | outcome — *pushback* (`ALGO5` = attention) |
| `TURN` | 12 | `TURN1`–`TURN3` | 3 | agree7 / likely7 | outcome — *leaving* |
| `DEP` | 13 | `DEP1`–`DEP2` | 2 | agree7 | trait |
| `H2` | 16 | `H2_*` | 16 | mirrors source | **holdout H2** |
| `H3` | 17 | `H3_V{1..6}_{FAIR,PUSH,KEEP}` | 18 | fair7 / likely7 | **holdout H3 — the fidelity gate** |

**Twin battery = 37 items**: AMQ 5 + PAC 11 + FAIR 4 + CLAR 3 + SAT 3 + CONT 2 + ALGO 4 + TURN 3 +
DEP 2. Attention checks excluded (I10). Demographics, screening, consent, open-ended items and
why-probes are **not** in the battery.

`37 battery + 2 attention + 16 H2 + 18 H3 = 73.`

**Reverse-coded — exactly three:** `SAT2` ("In general, I don't like my job"), `DEP1` ("I can
easily get another job outside the platform economy"), and `H2_SAT2` by inheritance. Reverse
before any mean: `reversed = (points + 1) − raw`.

**Scale override:** `TURN3` is `likely7`, not `agree7` — it is the likelihood-form turnover item.

### 3.2 Scales

Five. Anchors are **fully labelled at every point**, deliberately: fully-labelled scales reduce
acquiescence bias and translate more reliably into Hindi and Marathi.

| `scale_id` | points | format | 1 → n |
|---|---:|---|---|
| `agree7` | 7 | agreement | Strongly disagree → Strongly agree |
| `agree5` | **5** | agreement | Strongly disagree → Strongly agree |
| `extent7` | 7 | extent | To a very small extent → To a very large extent |
| `likely7` | 7 | likelihood | Not at all likely → Extremely likely |
| `fair7` | 7 | fairness | Very unfair → Very fair |

**Do not rescale 5-point blocks to 7.** Three of the nine constructs are 5-point. The prototype's
twin prompt flattened everything to 1–7 and its export claimed "every item on a 1 to 7 scale";
both were wrong against the source instrument, and 2.0 corrects them. Every item is scored on its
own published scale; standardisation happens at the modelling stage only.

The consequence is enforced twice: by `scales.points` in the schema, and by the validation ladder
(I13), where a `6` submitted for a 5-point item is a hard error, not a value to clamp.

### 3.3 The nine constructs

The item blocks group into nine constructs. These codes are what the Statistics section, the
export matrix and the Research Model mapping table use.

| Construct | Code | Items | n | Scale | In index |
|---|---|---|---:|---|---|
| Managed by the app | `EXPO` | AMQ1–5 | 5 | agree7 | — |
| Feels controlled | `CTRL` | PAC1–11 | 11 | agree5 | — |
| Feels treated fairly | `FAIR` | FAIR1–4 | 4 | extent7 | **+** |
| Finds the app clear | `TRAN` | CLAR1–3 | 3 | agree5 | **+** |
| Happy with the job | `SATI` | SAT1–3 | 3 | agree7 | **+** |
| Wants to stay | `LOYA` | CONT1–2 | 2 | agree5 | **+** |
| Pushes back | `VOIC` | ALGO1–4 | 4 | agree7 | **−** |
| Wants to leave | `EXIT` | TURN1–3 | 3 | agree7/likely7 | **−** |
| Needs the money | `EDEP` | DEP1–2 | 2 | agree7 | — |

Six of the nine carry a sign and enter the index; `EXPO`, `CTRL` and `EDEP` do not — they are
traits, and `EDEP` is the moderator.

> **Namespace warning.** `FAIR` is both an item block (`FAIR1`–`FAIR4`) and a construct code. They
> are different namespaces and must never be merged into one column. In the prototype the block was
> `PAF` and the construct `FAIR`, so the collision is new. Code reads `item.block` or
> `construct.code`, never a bare `FAIR`.

### 3.4 The six index metrics

The six signed constructs, under the names the metric code and the UI use:

| Metric | Construct | Items | Scale | Direction |
|---|---|---|---|---|
| `fairness` | FAIR | FAIR1–4 | extent7 | positive |
| `clarity` | TRAN | CLAR1–3 | agree5 | positive |
| `happiness` | SATI | SAT1–3 | agree7 | positive |
| `staying` | LOYA | CONT1–2 | agree5 | positive |
| `pushback` | VOIC | ALGO1–4 | agree7 | **negative** |
| `leaving` | EXIT | TURN1–3 | agree7 | **negative** |

Formulas are in `docs/07_STATISTICS.md`. They are not repeated here, so they cannot drift.

### 3.5 The H2 holdout — Part 16

16 items, each `mirrors` a battery item, re-answered after the respondent is shown **their own
arm's** story (§5).

`H2_FAIR1–4 · H2_SAT1–3 · H2_ALGO1–4 · H2_TURN1–3 · H2_CONT1–2 = 16`

Note which blocks are absent: no `H2_AMQ*`, no `H2_PAC*`, no `H2_DEP*`. Part 16 re-asks the
*outcomes*, not the traits — a policy story is not expected to move how automated a driver
believes the system is. `H2_SAT2` inherits `reverse_coded`.

H2 is the **second** validation set. It does not gate. It is run on demand, per arm, and is also
the item base for the `wrong_person` validity test (`docs/08`).

### 3.6 The H3 holdout — Part 17 — and its version codes

18 items: six versions × three questions (`FAIR`, `PUSH`, `KEEP`). The six scenarios are **not**
free-written vignettes — they are six real version codes rendered from this same pipeline, so the
human and the twin meet the *identical stimulus*.

| Shown | `version_code` | Fairwork score | `FAIR` scale | `PUSH` / `KEEP` scale |
|---:|---|---:|---|---|
| 1 | `12220` | 7 | fair7 | likely7 |
| 2 | `00222` | 6 | fair7 | likely7 |
| 3 | `11010` | 3 | fair7 | likely7 |
| 4 | `11211` | 6 | fair7 | likely7 |
| 5 | `02211` | 6 | fair7 | likely7 |
| 6 | `02200` | 4 | fair7 | likely7 |

**H3 is the fidelity gate.** The quality test renders these six codes through the normal pipeline —
same design agent, same checker, same style version — shows each to the twin with its persona and
**no baseline** (the human had none either), collects 18 numbers, and scores them against the
human's own 18. This is the only honest test of a twin.

---

## 4. The legacy crosswalk

The Google Apps Script prototype used different item and construct ids. The canonical register
above wins; the crosswalk exists so the prototype's saved data (`Uber Driver STUDY.xlsx`, ~8,500
`Runs` rows and ~556 `Twins`) stays readable, and so nobody re-derives it by hand.

`data/reference/legacy_crosswalk.json` — **read-only, never written, used only by the legacy
importer and by nothing else.**

| Prototype | Canonical | Construct | n |
|---|---|---|---:|
| `AMQ1`–`AMQ5` | `AMQ1`–`AMQ5` | EXPO | 5 |
| `PAC1`–`PAC11` | `PAC1`–`PAC11` | CTRL | 11 |
| **`PAF1`–`PAF4`** | **`FAIR1`–`FAIR4`** | FAIR | 4 |
| **`PAT1`–`PAT3`** | **`CLAR1`–`CLAR3`** | TRAN | 3 |
| `SAT1`–`SAT3` | `SAT1`–`SAT3` | SATI | 3 |
| **`LOY1`–`LOY2`** | **`CONT1`–`CONT2`** | LOYA | 2 |
| **`VOI1`–`VOI4`** | **`ALGO1`–`ALGO4`** | VOIC | 4 |
| **`EXT1`–`EXT3`** | **`TURN1`–`TURN3`** | EXIT | 3 |
| **`ECD1`–`ECD2`** | **`DEP1`–`DEP2`** | EDEP | 2 |
| **`AC1`** | **`AMQ6`** | — (attention) | 1 |
| **`AC2`** | **`ALGO5`** | — (attention) | 1 |
| `post_<X>` (16) | `H2_<X>` (16) | — (holdout H2) | 16 |
| `cj{1..6}_cj_fair` | `H3_V{1..6}_FAIR` | — (holdout H3) | 6 |
| `cj{1..6}_cj_resist` | `H3_V{1..6}_PUSH` | — (holdout H3) | 6 |
| `cj{1..6}_cj_stay` | `H3_V{1..6}_KEEP` | — (holdout H3) | 6 |

Three things the crosswalk also records, because they are not pure renames:

- **`design` → `version_code`.** The prototype called a version code a "design".
- **`d_<CONSTRUCT>` → `shift.<metric>`.** The `Designs` sheet stored six signed deltas
  (`d_FAIR, d_TRAN, d_SATI, d_LOYA, d_VOIC, d_EXIT`). They are stored **signed**; the index applies
  the sign flip. Verified: `22222` → `(1.62+0.94+1.53+1.01+1.81+0.98)/6 = 1.315`, matching the
  sheet exactly.
- **Scale change.** Legacy `PAC`, `PAT`/`CLAR` and `LOY`/`CONT` values were collected on 1–7 in the
  prototype but are 1–5 in the canonical instrument (§3.2). **Legacy values for those blocks are
  not comparable to new ones and must not be pooled.** The importer marks them
  `legacy_scale = true` and the analysis dataset excludes them by default.

---

## 5. The four human arms

`data/reference/arms.json`. The *human* survey is a four-arm between-subjects design, distinct from
the two *twin* control cells (`ARCHITECTURE.md` §5.2). Each respondent is assigned one arm, sees
that arm's story in Part 15, and re-answers 16 items in Part 16.

| `arm_id` | Story shown in Parts 15–16 | `version_code` | Role |
|---|---|---|---|
| `BASE` | no change | `00000` | human noise floor |
| `MGT1` | human appeals with no penalty for complaints | `00010` | Management, dial 1 |
| `CON1` | safety equipment, training, accident cover | `01000` | Conditions, dial 1 |
| `REP1` | a drivers' forum and union recognition | `00001` | Representation, dial 1 |

### 5.1 The mapping is derived, not assumed

Neither the instrument nor the codebook states this table. It was **recovered** by matching Part
15's four manipulation-check options against the commitment texts in `gaps.json`, and every
non-control arm matches its lever's dial-1 set term for term:

| Arm story | Dial-1 gaps | Commitment text |
|---|---|---|
| "Safety equipment, training, and accident cover" | `2.1.a` · `2.1.b` · `2.1.c` | *"Supply safety equipment … and deliver induction and refresher training"* · *"Provide accident and injury cover at Uber's cost"* |
| "Human appeals with no penalty for complaints" | `4.1.a` · `4.1.b` · `4.1.d` | *"Make a human point of contact reachable"* · *"Extend appeals beyond deactivation"* · *"Remove disparagement … from the grounds for deactivation"* |
| "A drivers' forum and union recognition" | `5.1.a` · `5.1.b` · `5.1.c` | *"Open the voice mechanism to every driver"* · *"Uber will recognise and bargain with an independent body of drivers or a trade union"* |

Part 16's story text in `Survey_Research_GIGWORKER_v2.md` — *"Uber now runs a documented forum where
all workers can raise serious concerns, and it states in writing that it will recognise and bargain
with an independent workers' body"* — is `5.1.a` + `5.1.b` rendered, near-verbatim. `BASE` is
`00000` trivially.

**Seed assertion.** `seed_db.py` asserts that every non-control arm's `version_code` is a
single-lever dial-1 code (exactly one non-zero digit, equal to 1) and that its lever's dial-1 gap
set is non-empty. This does not re-derive the semantic match, but it catches an `arms.json` edited
to something structurally impossible.

**Verification once real data exists.** Take any respondent with `arm = 'CON1'`, render `01000`
through the normal pipeline, and confirm the resulting Conditions paragraph describes what their
Part 16 story described. This is a one-off manual check and it belongs in the method section.

### 5.2 Consequences

Assignment is balanced within `city|service` strata, recorded on the submission as `arm` plus
`arm_source` (how it was assigned). Part 15 asks which change the story described, with these four
as options; the answer is stored as `mc_answer` and scored against `arm` into `mc_correct`.

**H2 validation shows a twin *its own driver's arm*,** rendered through the normal pipeline.
Showing a twin a different arm than its human saw is a bug, not a variation, and
`twin_quality_runs.arm` plus the Validation tab's *Arm seen* column exist so it is checkable after
the fact.

**`BASE` is the human noise floor.** A quarter of respondents re-answered 16 items after being told
nothing changed. Their H2−baseline difference is human response instability in this instrument — the
direct analogue of the twin's `00000` control, measured on real people. It should be reported.

---

## 6. Postgres schema

`src/twinlab/db/migrations/`. Postgres 15 (Supabase). **RLS is enabled on every table**; the server
uses the service key and bypasses it. No anon access, ever — the Space is the only client.

Migrations are additive and numbered. `001_init.sql` is the 1.0 schema; 2.0 changes land as
`002_*.sql` onward so an existing project migrates rather than being rebuilt.

### 6.1 Reference tables

```sql
create table scales (
  scale_id text primary key,
  points   smallint not null,
  format   text not null,
  anchors  jsonb not null            -- length must equal points
);

create table constructs (
  code            text primary key,   -- 'EXPO' | 'CTRL' | 'FAIR' | ...
  label           text not null,      -- 'Managed by the app'
  metric_name     text,               -- 'fairness' | ... | null for EXPO/CTRL/EDEP
  index_sign      smallint,           -- +1 | -1 | null
  scale_id        text references scales(scale_id)
);

create table survey_items (
  item_id         text primary key,      -- 'FAIR1'
  part            smallint not null,
  part_name       text not null,
  block           text not null,         -- NOT the construct code. See §3.3.
  construct_code  text references constructs(code),   -- null for holdouts/attention
  ordinal         smallint not null,
  stem            text not null,
  scale_id        text not null references scales(scale_id),
  reverse_coded   boolean not null default false,
  attention_check boolean not null default false,
  role            text not null,   -- outcome|trait|attention|holdout_h2|holdout_h3|open|demographic
  in_twin_battery boolean not null default false,
  mirrors         text references survey_items(item_id),   -- H2_* → its source item
  version_shown   smallint,        -- H3 only, 1..6
  version_code    text             -- H3 only
);
create index on survey_items (block, ordinal);
create index on survey_items (construct_code);

create table arms (
  arm_id       text primary key,   -- 'CON1'
  label        text not null,
  version_code text not null,
  is_control   boolean not null default false   -- true for BASE
);

create table legacy_items (
  legacy_id text primary key,                          -- 'PAF1'
  item_id   text references survey_items(item_id),     -- 'FAIR1'
  note      text                                       -- e.g. scale change warning
);
```

Plus `criteria`, `thresholds`, `criterion_findings`, `gaps`, `corpus_chunks` and
`chunk_criterion_links` — **unchanged from `001_init.sql`**, which is correct and already seeded.
Their columns are listed there; the only thing worth restating is that `corpus_chunks.chunk_id`
(e.g. `L4-4.1-015`) is an **opaque stable key** cited by the codebook. It is never renumbered even
when a chunk was refiled — `refiled_from` records the move.

### 6.2 Submissions, answers, twins

**Changed in 2.0.** v1.0 keyed survey answers by `twin_id`, which left no home for a respondent who
was ineligible, withheld consent, or failed an attention check. The Fieldwork tab has to count
exactly those people, and the Generator has to delete synthetic rows without touching twins. So the
respondent and the twin are now separate entities.

```sql
create table survey_submissions (
  submission_id     text primary key,        -- 'UBR-L7S7MP' | 'SYN-K6DBWL'
  data_type         text not null,           -- 'REAL' | 'SYNTHETIC'
  batch_id          uuid references synthetic_batches(batch_id),  -- synthetic only

  -- fieldwork / quality
  eligible          boolean not null,
  consented         boolean not null,        -- consent statements 1-6
  consent_twin      boolean not null,        -- statement 7. FALSE ⇒ never a twin.
  attention_passed  boolean not null,        -- AMQ6 and ALGO5
  completion_seconds integer,
  speeder           boolean generated always as (completion_seconds < 480) stored,
  straight_liner    boolean not null default false,
  outcome           text not null,           -- complete|screened_out|no_consent|partial

  -- assignment
  arm               text references arms(arm_id),
  arm_source        text,
  mc_answer         text,                    -- Part 15 manipulation check
  mc_correct        boolean generated always as (mc_answer = arm) stored,

  -- context
  city              text,
  service           text,
  language          text,                    -- en | hi | mr
  raw_object_path   text not null,           -- Supabase Storage key. Written BEFORE this row. (I16)
  started_at        timestamptz,
  submitted_at      timestamptz not null,
  received_at       timestamptz not null default now()
);
create index on survey_submissions (data_type, outcome);
create index on survey_submissions (city, service);
create index on survey_submissions (arm);

create table survey_answers (
  submission_id text not null references survey_submissions(submission_id) on delete cascade,
  item_id       text not null references survey_items(item_id),
  value_num     smallint,     -- Likert
  value_text    text,         -- open-ended / short answer
  why_text      text,         -- the paired why-probe, VERBATIM, never paraphrased
  language      text,
  legacy_scale  boolean not null default false,   -- imported on the prototype's 1-7 scale (§4)
  primary key (submission_id, item_id)
);

create table twins (
  twin_id           text primary key,
  submission_id     text unique not null references survey_submissions(submission_id),
  source            text not null,   -- 'real' | 'synthetic' | 'manual'
  service           text,
  city              text,
  age               smallint,
  gender            text,
  tenure_months     smallint,
  hours_per_week    smallint,
  background        jsonb not null default '{}',
     -- Part 3 extras, Part 4, AND Part 14 own-words. Part 14 has no item_id and the
     -- 73-item register is frozen; without this the persona loses the driver's own words.
  persona_passage   text,
  persona_hash      text,
  persona_template_version text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index on twins (source);
```

**Manual twins** (Twin Studio Mode C) have `source = 'manual'` and a synthesised submission row
with `data_type = 'SYNTHETIC'`, `consent_twin = true` and `outcome = 'manual'`. They are sandbox
objects: they are never drawn into an analysis panel (§6.4) and never contribute to Statistics.

### 6.3 Quality and validation

One table covers both holdouts. H3 gates; H2 does not.

```sql
create table twin_quality_runs (
  quality_run_id  uuid primary key default gen_random_uuid(),
  twin_id         text not null references twins(twin_id) on delete cascade,
  session_id      uuid references sessions(session_id),
  holdout_set     text not null,          -- 'H3' (the gate) | 'H2' (second set)
  arm             text references arms(arm_id),   -- H2 only: the arm the HUMAN saw (§5)
  items_n         smallint not null,
  mae             numeric(5,3) not null,
  pct_within_1    numeric(4,3) not null,
  correlations    jsonb,                  -- H3: {fairness: r, pushback: r, staying: r}
  kept            boolean,                -- H3 only; null for H2
  repeats         smallint not null,      -- quality_runs_per_twin, averaged
  detail          jsonb not null,         -- [{item_id, human, twin, abs_err}, ...]
  model           text not null,
  config_version  integer not null,
  created_at      timestamptz not null default now(),
  is_latest       boolean not null default true,

  constraint quality_h3_gates check ((holdout_set = 'H3') = (kept is not null)),
  constraint quality_h2_arm   check (holdout_set <> 'H2' or arm is not null),
  constraint quality_has_items check (items_n > 0)          -- I15
);
create unique index on twin_quality_runs (twin_id, holdout_set) where is_latest;
```

`is_latest` plus a partial unique index is the pattern used throughout: **append a new row, demote
the old one in the same transaction.** Nothing is destroyed (I9), and "current value" is one
indexed lookup. It is why the Twins list, the quality card, the panel selector and the analyst's
`twins_n` all update together with no cache to invalidate.

**Keep if `mae <= 1.0` AND `pct_within_1 >= 0.80`**, averaged over `repeats` (default 3), on
holdout `H3`. Thresholds are CONFIG.

### 6.4 Sessions, the frozen panel, and runs

```sql
create table sessions (
  session_id   uuid primary key default gen_random_uuid(),
  name         text not null,
  kind         text not null default 'sweep',  -- sweep|ask|quality|validation|validity
  status       text not null default 'created',
     -- created|running|paused|stopped|completed|failed
  iterations   smallint not null default 1,
  start_code   text not null default '10000',
  cursor_index smallint,
  completed    smallint not null default 0,

  -- the frozen analysis panel (I14)
  panel_size   smallint not null,
  panel_seed   bigint not null,
  population   text not null default 'real',   -- real|synthetic|both

  config       jsonb not null,   -- frozen TwinConfig + model + style_version + prompt versions
  budget       jsonb,            -- the pre-flight estimate shown at confirm time (§ARCH 7.2)
  created_at   timestamptz not null default now(),
  finished_at  timestamptz
);

create table session_panel (
  session_id uuid not null references sessions(session_id) on delete cascade,
  twin_id    text not null references twins(twin_id),
  stratum    text not null,        -- 'Mumbai|cab'
  position   smallint not null,    -- draw order, so the panel is reproducible from the seed
  primary key (session_id, twin_id)
);
create index on session_panel (session_id, position);
```

**`session_panel` is invariant I14 made physical.** The panel is drawn once at session creation —
stratified on `city × service`, seeded, from twins that are quality-passed and match `population` —
and every cell in that session is answered by exactly these twins. A session's results are
comparable internally; two sessions with different panels are not differenced without an explicit,
logged decision.

```sql
create table runs (
  run_id       uuid primary key default gen_random_uuid(),
  session_id   uuid not null references sessions(session_id) on delete cascade,
  version_code text not null,                   -- '01000' | 'SHAM'
  status       text not null default 'pending',
     -- pending|rendering|checking|asking|analysing|completed|failed
  variant_id   uuid references variants(variant_id),
  twins_n      smallint not null default 0,
  metrics      jsonb,        -- baselines, variant means, shifts. See docs/07.
  index_value  numeric(6,3),
  llm_analysis text,
  analysis_prompt_version text,
  error        text,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  is_latest_for_version boolean not null default false,

  -- I15: a run with no twins is a failure, not a result of zero.
  constraint runs_completed_has_twins
    check (status <> 'completed' or twins_n > 0)
);
create unique index runs_latest_uq on runs (version_code) where is_latest_for_version;
create index on runs (session_id, status);
```

`runs_completed_has_twins` is the schema refusing to record the prototype's defect: its `Designs`
sheet contains rows with `twins = 0, index = 0.000` stored as findings. **An invariant enforced in
DDL cannot be forgotten by a caller.**

`runs_latest_uq` is also the cache. The Dial board's "Ask the twins" is one query against it; a hit
renders the cached result with a `cached` badge and a `Rerun?` button, a miss starts a session.

### 6.5 Events

```sql
create table run_events (
  event_id        bigserial primary key,
  session_id      uuid not null references sessions(session_id) on delete cascade,
  run_id          uuid references runs(run_id) on delete cascade,
  parent_event_id bigint references run_events(event_id),   -- the log TREE
  ts              timestamptz not null default now(),
  stage           text not null,   -- ingestion|panel|reconstruction|lookup|render|check|ask|analyse|control
  agent           text,            -- manager|design|twin|checker|analyst|null
  label           text not null,   -- what the row shows collapsed; rewritten in place
  status          text not null,   -- running|ok|error
  payload         jsonb,
  logfire_span_id text,

  -- §ARCH 7.2: never store a prompt body. Payloads carry references and telemetry only.
  constraint run_events_payload_small
    check (payload is null or pg_column_size(payload) <= 8192)
);
create index on run_events (session_id, event_id);
create index on run_events (parent_event_id);
```

`parent_event_id` is what makes the Logs view a tree rather than a list: a stage emits one parent
row whose label is **rewritten in place** as work progresses, and each twin or lever emits a child.

**The 8 KB cap is load-bearing, not tidiness.** At a full sweep the `ask` stage alone emits one
child per twin per cell. Storing prompt bodies there would exhaust the 500 MB tier on its own. The
prompt is never stored — it is *rebuilt* from `persona_hash`, `seed`, `lever_order`,
`style_version`, `wording` and the prompt version (I11). Anything genuinely large lives in its own
table (`variants`, `twin_answers`, `twins.persona_passage`) and the panel fetches it on open.

### 6.6 Variants and answers

```sql
create table lever_paragraphs (
  paragraph_id  uuid primary key default gen_random_uuid(),
  lever         text not null,      -- L1..L5
  dial          smallint not null,  -- 0|1|2, plus 3 = SHAM (see note)
  style_version text not null,
  text          text not null,
  word_count    smallint not null,
  delta_hash    text not null,
  checker_pass  boolean not null default false,
  created_at    timestamptz not null default now()
);
create unique index on lever_paragraphs (lever, dial, style_version);

create table variants (
  variant_id    uuid primary key default gen_random_uuid(),
  version_code  text not null,
  style_version text not null,
  delta_spec    jsonb not null,
  delta_hash    text not null,
  paragraphs    jsonb not null,   -- {L1: paragraph_id, ...}
  checker       jsonb not null,   -- CheckerReport
  created_at    timestamptz not null default now()
);
create unique index on variants (version_code, style_version);

create table twin_answers (
  answer_id   uuid primary key default gen_random_uuid(),
  run_id      uuid not null references runs(run_id) on delete cascade,
  twin_id     text not null references twins(twin_id),
  answers     jsonb not null,      -- exactly 37 keys, each within its own scale
  lever_order smallint[] not null, -- the randomised order actually shown
  seed        bigint not null,
  wording     text not null,       -- 'A' | 'B'
  model       text not null,
  prompt_version text not null,
  retries     smallint not null default 0,   -- how many validation retries this took (I13)
  latency_ms  integer,
  created_at  timestamptz not null default now()
);
create unique index on twin_answers (run_id, twin_id, wording);
```

**`dial = 3` is SHAM.** The sham's unfilled levers announce that lever's *existing* driver-facing
policy, so they are not dial-0 lines and not live-cell paragraphs; they occupy their own slot in
the same cache. Researcher-approved; see `docs/DECISIONS.md`.

**Why `answers` is jsonb and not a row per item.** 243 cells × 20 twins × 37 items is ~180,000 rows
against a 500 MB tier, for data that is always read as a whole vector. One row per
(run, twin, wording) gives ~4,860 rows and every read is a single fetch. Metrics are computed in
Python from the vector, never in SQL.

### 6.7 Validity tests

Append-only. Every completed test writes a new row; results double as the log (spec §15.5).

```sql
create table validity_results (
  validity_run_id uuid primary key default gen_random_uuid(),
  test_id       text not null,
     -- wrong_person|placebo|baselines|impossible|order_swap|leave_block|second_model|temperature
  session_id    uuid references sessions(session_id),
  twins_n       smallint not null,
  mode          text not null,          -- 'mock' | 'live'
  provider      text not null,
  model         text not null,
  temperature   numeric(3,2),
  statistics    jsonb not null,         -- test-specific numbers, computed in Python
  verdict       text not null,          -- PASS | FAIL | CHECK | INCONCLUSIVE
  headline      text not null,          -- 'twins are about their own driver'
  detail        text not null,          -- what the test measures, for the reader
  config_version integer not null,
  created_at    timestamptz not null default now(),

  -- I15: a test that ran on nobody concluded nothing.
  constraint validity_zero_n check (twins_n > 0 or verdict = 'INCONCLUSIVE')
);
create index on validity_results (test_id, created_at desc);
```

`validity_zero_n` closes the prototype's worst recorded defect: its `ValidityTests` sheet contains
live-mode rows with `twins = 0` that nonetheless emitted **`PASS: twins are about their own
driver`**. A test that ran on nobody must never read as evidence.

### 6.8 Statistics

Staged and resumable, because a bootstrap is long and the Space can restart.

```sql
create table analysis_runs (
  analysis_id       uuid primary key default gen_random_uuid(),
  population        text not null,     -- real|synthetic|both
  screening         text not null,     -- 'strict' (drop attention fails, speeders,
                                       --  straight-liners) | 'none'
  bootstrap_samples integer not null,
  seed              bigint not null,
  n_cases           integer not null,
  status            text not null default 'created',
  stage_cursor      text,              -- the next stage to compute
  engine_version    text not null,     -- openpls-engine version — provenance for the paper
  config            jsonb not null,
  created_at        timestamptz not null default now(),
  finished_at       timestamptz,

  constraint analysis_bootstrap_floor check (bootstrap_samples >= 30),
  constraint analysis_has_cases       check (n_cases > 0)
);

create table analysis_results (
  analysis_id uuid not null references analysis_runs(analysis_id) on delete cascade,
  stage       text not null,
     -- reliability|discriminant|collinearity|outer_model|paths
     -- |indirect_total|r2_f2_q2|plspredict|model_fit
  payload     jsonb not null,
  computed_at timestamptz not null default now(),
  primary key (analysis_id, stage)
);
```

A completed stage is never recomputed on resume. `engine_version` is recorded because the paper
must state which implementation produced the numbers.

**On the bootstrap floor.** 30 is the prototype's UI minimum and is kept for compatibility, but it
is far below reportable: PLS-SEM convention is 5,000, with 1,000 an absolute floor. The default is
5,000 and the UI warns below 1,000. See `ARCHITECTURE.md` §10.7.

### 6.9 Generator and Studio

```sql
create table synthetic_batches (
  batch_id    uuid primary key default gen_random_uuid(),
  name        text not null,
  seed        bigint not null,        -- same seed, same data
  requested   integer not null,
  created_n   integer not null default 0,
  rejected_n  integer not null default 0,
  config      jsonb not null,         -- the complete generator control state
  created_at  timestamptz not null default now()
);

create table studio_runs (
  studio_run_id  uuid primary key default gen_random_uuid(),
  twin_id        text not null references twins(twin_id),
  version_code   text,                -- null when custom_change is used
  custom_change  text,
  questions      text[] not null default '{}',   -- up to 5
  include_battery boolean not null default false,
  answers        jsonb,               -- the 37, when include_battery
  free_answers   jsonb,               -- the custom Q&A
  scenario_text  jsonb,
  model          text not null,
  seed           bigint not null,
  created_at     timestamptz not null default now()
);
```

**Studio runs are a sandbox and are quarantined.** They never appear in `runs`, never contribute to
a metric, a shift, an index or the Results grid, and never enter Statistics. The Studio is for a
researcher to interrogate one twin in their own words; it is not evidence.

The Generator's "Delete all synthetic surveys" deletes `survey_submissions where data_type =
'SYNTHETIC'` and cascades to answers and twins. It **must not** touch `REAL` rows, and it must not
delete `runs` — deleting append-only evidence is not a button (I9).

### 6.10 Configuration and its history

```sql
create table agent_configs (
  agent_id      text primary key,
  name          text not null,
  role          text not null,
  enabled       boolean not null default true,
  model         jsonb not null,
  system_prompt text not null,       -- inline, or "file:design_v1.md"
  prompt_hash   text not null,       -- hash of the resolved prompt, frozen onto runs
  instructions  text[] not null default '{}',
  input_schema  text not null,
  output_schema text not null,
  output_mode   text not null default 'tool',   -- tool | prompted. NEVER 'native' (§ARCH 3.2)
  tools         text[] not null default '{}',   -- ALLOW-LIST. Design and Twin: '{}'.
  context_sources jsonb not null default '[]',
  react         boolean not null default false,
  retry         jsonb not null default '{"attempts":2,"backoff":"exponential"}',
  version       integer not null default 1,
  frozen        boolean not null default false,   -- "Freeze for the main study"
  frozen_at     timestamptz,
  updated_at    timestamptz not null default now(),

  constraint agent_no_native_output check (output_mode in ('tool','prompted'))
);

create table agent_config_history (
  history_id     bigserial primary key,
  agent_id       text not null,     -- or 'RULES' for the shared rules panel
  version        integer not null,
  snapshot       jsonb not null,    -- the complete config at save time
  changed_fields text[] not null,
  action         text not null,     -- saved | restored | frozen | unfrozen
  actor          text,
  created_at     timestamptz not null default now()
);
create index on agent_config_history (created_at desc);

create table app_config (
  key        text primary key,   -- 'twin' | 'style' | 'orchestrator' | 'analysis' | 'generator'
  value      jsonb not null,
  version    integer not null default 1,
  updated_at timestamptz not null default now()
);
```

`agent_config_history` is the "What was changed" panel that appears on every Agent Studio screen —
append-only, `When · Agent · What was saved`. `agent_no_native_output` is §ARCH 3.2 enforced in
DDL: `NativeOutput` against Ollama Cloud fails silently, so the schema forbids even configuring it.

A **frozen** agent cannot be edited while any session is running; unfreezing is itself a history
row. Behaviour is data, so a sixth agent is an `INSERT` plus a prompt file — no backend change.

---

## 7. Pointer-flip functions

Two, both already in `001_init.sql`, both doing the same thing: demote the old `is_latest`, promote
the new, in one transaction.

```sql
-- repo_runs.complete()
begin;
  update runs set is_latest_for_version = false
   where version_code = $code and is_latest_for_version;
  update runs set status = 'completed', finished_at = now(),
                  is_latest_for_version = true
   where run_id = $run_id;
commit;
```

`quality_run_record()` is the same shape over `twin_quality_runs (twin_id, holdout_set)`. Any new
"latest" pointer added later uses this pattern and nothing else.

---

## 8. Entity relationships

```
criteria ─1:1─ criterion_findings
   │  1:0..1
   └──────── gaps ──────┐
   │                    │ selected by dial_lookup
   └─1:n─ chunk_criterion_links ─n:1─ corpus_chunks
                                            │ anchor_sources (voice + do-not-re-announce)
                                            ▼
                                  variants ─n:1─ lever_paragraphs
                                     │ 1:1
sessions ─1:n─ runs ─────────────────┘
   │             │
   │             ├─1:n─ twin_answers ──n:1─┐
   │             └─1:n─ run_events (tree)  │
   │ 1:n                                   │
   └── session_panel ──────────────────────┤
                                           ▼
                                        twins ─1:n─ twin_quality_runs
                                           │ n:1
                            survey_submissions ─1:n─ survey_answers ─n:1─ survey_items
                                           │                                   │ n:1
                                       arms ┘                            constructs ─n:1─ scales

analysis_runs ─1:n─ analysis_results        (reads survey_submissions + survey_answers)
validity_results                            (reads twins + twin_answers)
studio_runs ─n:1─ twins                     (quarantined; feeds nothing)
```

Read the top half as **evidence flowing down** — a published standard, a coded corpus, a real
survey — and note that `studio_runs` is deliberately a leaf with no path into `runs`.

---

## 9. Seeding

`ingest/seed_db.py` is idempotent — upsert on primary key, in FK order:

```
scales → constructs → survey_items → arms → legacy_items
      → criteria → thresholds → criterion_findings → gaps
      → corpus_chunks → chunk_criterion_links
      → agent_configs → app_config
```

After seeding it **asserts**, aborting non-zero on any failure:

| Assertion | Expected |
|---|---:|
| `criteria` | 33 |
| `criterion_findings` | 33 |
| `criterion_findings where finding = 'Met'` | 3, and exactly `{3.1.a, 3.1.c, 4.1.c}` |
| `gaps` | 30 |
| `thresholds` | 10 |
| `corpus_chunks` | 126 |
| `chunk_criterion_links` | 171 |
| `survey_items` | 73 |
| `survey_items where in_twin_battery` | 37 |
| `survey_items where attention_check` | 2, and exactly `{AMQ6, ALGO5}` |
| `survey_items where reverse_coded` | 3, and exactly `{SAT2, DEP1, H2_SAT2}` |
| `scales` | 5 |
| `constructs` | 9, of which 6 have a non-null `index_sign` |
| `arms` | 4, of which 1 is `is_control` |
| every `H2_*` resolves `mirrors` | 16 |
| every `H3_*` has a valid `version_code` | 18 |
| `sum(digit_sum(code)) over all 243 codes` | 1215 |
| every `anchors` array length | `= scales.points` |

The last one catches the 5-vs-7 scale error at seed time rather than in a metric.

---

## 10. Storage budget

The free tier is 500 MB. The binding constraint is **not** answers.

| Table | At K=20 panel, 243 cells, 500 submissions | Note |
|---|---:|---|
| `twin_answers` | ~5 MB | 4,860 rows × ~1 KB |
| `run_events` | ~10 MB | ~6,000 rows, payload capped at 8 KB |
| `survey_answers` | ~18 MB | 500 × 73, whys dominate |
| `survey_submissions` | <1 MB | |
| `twins` (personas) | ~2 MB | 500 × ~4 KB |
| `corpus_chunks` + reference | <1 MB | |
| **Total** | **~36 MB** | comfortable |

At K=500 the same arithmetic reaches ~356 MB — survivable, but only because `run_events` payloads
are capped and prompt bodies are never stored. Remove either discipline and the tier is exhausted
before the sweep finishes. The full model, including the degradation ladder, is in
`docs/10_SCALE_AND_COST.md`.

---

## 11. What changed from 1.0

| Change | Why |
|---|---|
| `survey_responses(twin_id, …)` split into `survey_submissions` + `survey_answers` | A non-consenting or screened-out respondent had nowhere to live, yet Fieldwork must count them |
| `constructs` table, `survey_items.construct_code` | The Statistics section needs the nine construct codes; six metrics were not enough |
| `arms`, `survey_submissions.arm` | The four-arm human design was undocumented in 1.0 |
| `legacy_items` | So the prototype's ~8,500 saved rows stay readable |
| `session_panel`, `sessions.panel_*` | I14 — the frozen analysis panel |
| `validity_results` | The eight validity tests had no home |
| `analysis_runs` / `analysis_results` | Statistics had no home |
| `synthetic_batches`, `studio_runs` | Generator and Twin Studio had no home |
| `agent_config_history`, `agent_configs.frozen` | The "What was changed" panel and the main-study freeze |
| `twin_quality_runs.arm`, `.correlations`, `.repeats` | H2 is per-arm; the Validation tab reports correlations |
| `runs.twins_n` NOT NULL + `runs_completed_has_twins` | I15, enforced in DDL |
| `validity_results.validity_zero_n` | I15, enforced in DDL |
| `run_events` payload cap 32 KB → **8 KB** | Storage budget at panel scale |
| `agent_configs.output_mode` + `agent_no_native_output` | §ARCH 3.2 — Ollama Cloud ignores schemas silently |
| `twin_answers.retries`, `.prompt_version` | The validation ladder and prompt provenance |
| `analysis_bootstrap_floor` | The prototype's ≥30 UI rule, enforced |
