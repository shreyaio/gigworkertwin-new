-- Twin Lab 2.0 schema. docs/01 §6, §7 and §11.
--
-- ADDITIVE, per docs/01 §6: "001_init.sql is the 1.0 schema; 2.0 changes land as 002_*.sql
-- onward so an existing project migrates rather than being rebuilt." Nothing is dropped.
-- `survey_responses` is superseded by survey_submissions + survey_answers and is deliberately
-- LEFT IN PLACE: it may hold v1 evidence, and deleting append-only evidence is not a migration
-- step (I9). The legacy importer is its only reader.
--
-- Four constraints here validate existing rows and will FAIL LOUDLY on a database that already
-- contains the prototype's defects — a `completed` run with no twins, a quality row with no
-- items. That is the correct outcome (CLAUDE.md, I15): the researcher decides what to do with
-- such a row, and the migration does not quietly grandfather it.

begin;

-- ---------------------------------------------------------------- reference: new tables

-- The nine constructs. docs/01 §3.3. Six carry a metric name and an index sign; EXPO, CTRL and
-- EDEP are traits and carry neither.
create table if not exists constructs (
  code        text primary key,
  label       text not null,
  block       text not null,          -- the ITEM block. Not the same namespace as `code`: FAIR
                                      -- is both a block and a construct code (docs/01 §3.3).
  metric_name text,
  index_sign  smallint,
  scale_id    text references scales(scale_id),

  constraint constructs_sign check (index_sign is null or index_sign in (-1, 1)),
  -- A construct either enters the index with both a name and a sign, or with neither.
  constraint constructs_metric_and_sign
    check ((metric_name is null) = (index_sign is null))
);

-- The four human survey arms. docs/01 §5. NOT the twin control cells (ARCHITECTURE.md §5.2) —
-- this is a between-subjects survey design.
create table if not exists arms (
  arm_id       text primary key,
  label        text not null,
  version_code text not null,
  lever        text,                              -- null for BASE
  is_control   boolean not null default false
);

-- The prototype's identifiers. docs/01 §4. Read-only; the legacy importer is its only reader.
create table if not exists legacy_items (
  legacy_id text primary key,
  item_id   text references survey_items(item_id),
  note      text
);

-- ---------------------------------------------------------------- reference: survey_items

-- `part_name` carries a default because this migration must also succeed against a project
-- already seeded from 001. The seeder always supplies the real value from the item register,
-- so the default is never the stored value for any seeded row.
alter table survey_items add column if not exists part_name text not null default '';
alter table survey_items add column if not exists construct_code text references constructs(code);
create index if not exists survey_items_construct_idx on survey_items (construct_code);

-- ---------------------------------------------------------------- submissions and answers

create table if not exists synthetic_batches (
  batch_id    uuid primary key default gen_random_uuid(),
  name        text not null,
  seed        bigint not null,
  requested   integer not null,
  created_n   integer not null default 0,
  rejected_n  integer not null default 0,
  config      jsonb not null,
  created_at  timestamptz not null default now()
);

-- The respondent, separate from the twin (docs/01 §11): a respondent who was ineligible,
-- withheld consent or failed an attention check must have somewhere to live, because Fieldwork
-- counts exactly those people.
create table if not exists survey_submissions (
  submission_id     text primary key,
  data_type         text not null,
  batch_id          uuid references synthetic_batches(batch_id),

  eligible          boolean not null,
  consented         boolean not null,
  consent_twin      boolean not null,     -- statement 7. FALSE ⇒ never a twin.
  attention_passed  boolean not null,
  completion_seconds integer,
  speeder           boolean generated always as (completion_seconds < 480) stored,
  straight_liner    boolean not null default false,
  outcome           text not null,

  arm               text references arms(arm_id),
  arm_source        text,
  mc_answer         text,
  mc_correct        boolean generated always as (mc_answer = arm) stored,

  city              text,
  service           text,
  language          text,
  raw_object_path   text not null,        -- Storage key, written BEFORE this row (I16)
  started_at        timestamptz,
  submitted_at      timestamptz not null,
  received_at       timestamptz not null default now()
);
create index if not exists survey_submissions_type_outcome_idx
  on survey_submissions (data_type, outcome);
create index if not exists survey_submissions_city_service_idx
  on survey_submissions (city, service);
create index if not exists survey_submissions_arm_idx on survey_submissions (arm);

create table if not exists survey_answers (
  submission_id text not null
    references survey_submissions(submission_id) on delete cascade,
  item_id       text not null references survey_items(item_id),
  value_num     smallint,
  value_text    text,
  why_text      text,                     -- the paired why-probe, VERBATIM, never paraphrased
  language      text,
  legacy_scale  boolean not null default false,   -- imported on the prototype's 1-7 scale (§4)
  primary key (submission_id, item_id)
);

-- ---------------------------------------------------------------- twins

alter table twins add column if not exists submission_id text
  references survey_submissions(submission_id);
create unique index if not exists twins_submission_uq on twins (submission_id);

-- Consent now lives on the submission. The 1.0 column stays for v1 rows but stops being
-- required, so a 2.0 insert does not have to duplicate it.
alter table twins alter column consent_twin drop not null;

-- ---------------------------------------------------------------- sessions and the panel

alter table sessions add column if not exists kind text not null default 'sweep';
alter table sessions add column if not exists population text not null default 'real';
alter table sessions add column if not exists budget jsonb;
-- The frozen analysis panel (I14). Defaults exist only so the migration succeeds against an
-- existing project; `sessions.create` always supplies a drawn seed and the configured size.
alter table sessions add column if not exists panel_size smallint not null default 20;
alter table sessions add column if not exists panel_seed bigint not null default 0;

-- I14 made physical: the panel is drawn once and every cell in the session uses these twins.
create table if not exists session_panel (
  session_id uuid not null references sessions(session_id) on delete cascade,
  twin_id    text not null references twins(twin_id),
  stratum    text not null,        -- 'Mumbai|cab'
  position   smallint not null,    -- draw order, so the panel is reproducible from the seed
  primary key (session_id, twin_id)
);
create index if not exists session_panel_order_idx on session_panel (session_id, position);

-- ---------------------------------------------------------------- runs

alter table runs add column if not exists analysis_prompt_version text;
update runs set twins_n = 0 where twins_n is null;
alter table runs alter column twins_n set default 0;
alter table runs alter column twins_n set not null;

-- I15 in DDL: the prototype's `Designs` sheet stored rows with twins = 0, index = 0.000 as
-- findings. An invariant enforced in DDL cannot be forgotten by a caller.
alter table runs drop constraint if exists runs_completed_has_twins;
alter table runs add constraint runs_completed_has_twins
  check (status <> 'completed' or twins_n > 0);

-- ---------------------------------------------------------------- events

-- ARCHITECTURE.md §7.2: never store a prompt body. At panel scale the prompt bodies alone would
-- exhaust the 500 MB tier, so payloads carry references and telemetry only and the round prompt
-- is rebuilt from stored fields (I11). 8 KB, down from 1.0's 32 KB.
alter table run_events drop constraint if exists run_events_payload_small;
alter table run_events add constraint run_events_payload_small
  check (payload is null or pg_column_size(payload) <= 8192);

-- ---------------------------------------------------------------- answers

alter table twin_answers add column if not exists prompt_version text;
alter table twin_answers add column if not exists retries smallint not null default 0;

-- ---------------------------------------------------------------- quality and validation

alter table twin_quality_runs add column if not exists arm text references arms(arm_id);
alter table twin_quality_runs add column if not exists items_n smallint not null default 0;
alter table twin_quality_runs add column if not exists correlations jsonb;
alter table twin_quality_runs add column if not exists repeats smallint not null default 1;
alter table twin_quality_runs add column if not exists config_version integer not null default 1;
alter table twin_quality_runs alter column model set not null;
-- H3 gates and carries `kept`; H2 does not and carries null.
alter table twin_quality_runs alter column kept drop not null;

alter table twin_quality_runs drop constraint if exists quality_h3_gates;
alter table twin_quality_runs add constraint quality_h3_gates
  check ((holdout_set = 'H3') = (kept is not null));
alter table twin_quality_runs drop constraint if exists quality_h2_arm;
alter table twin_quality_runs add constraint quality_h2_arm
  check (holdout_set <> 'H2' or arm is not null);
alter table twin_quality_runs drop constraint if exists quality_has_items;
alter table twin_quality_runs add constraint quality_has_items check (items_n > 0);   -- I15

-- ---------------------------------------------------------------- validity tests

create table if not exists validity_results (
  validity_run_id uuid primary key default gen_random_uuid(),
  test_id       text not null,
  session_id    uuid references sessions(session_id),
  twins_n       smallint not null,
  mode          text not null,          -- 'mock' | 'live'
  provider      text not null,
  model         text not null,
  temperature   numeric(3,2),
  statistics    jsonb not null,         -- test-specific numbers, computed in Python (I12)
  verdict       text not null,          -- PASS | FAIL | CHECK | INCONCLUSIVE
  headline      text not null,
  detail        text not null,
  config_version integer not null,
  created_at    timestamptz not null default now(),

  -- I15: the prototype's ValidityTests sheet carried live rows with twins = 0 reading
  -- "PASS: twins are about their own driver". A test that ran on nobody concluded nothing.
  constraint validity_zero_n check (twins_n > 0 or verdict = 'INCONCLUSIVE')
);
create index if not exists validity_results_test_idx
  on validity_results (test_id, created_at desc);

-- ---------------------------------------------------------------- statistics

create table if not exists analysis_runs (
  analysis_id       uuid primary key default gen_random_uuid(),
  population        text not null,
  screening         text not null,
  bootstrap_samples integer not null,
  seed              bigint not null,
  n_cases           integer not null,
  status            text not null default 'created',
  stage_cursor      text,
  engine_version    text not null,     -- openpls-engine version — provenance for the paper
  config            jsonb not null,
  created_at        timestamptz not null default now(),
  finished_at       timestamptz,

  -- The prototype's UI floor, enforced. 30 is far below reportable; the default is 5,000 and
  -- the UI warns below 1,000 (ARCHITECTURE.md §10.7).
  constraint analysis_bootstrap_floor check (bootstrap_samples >= 30),
  constraint analysis_has_cases       check (n_cases > 0)
);

create table if not exists analysis_results (
  analysis_id uuid not null references analysis_runs(analysis_id) on delete cascade,
  stage       text not null,
  payload     jsonb not null,
  computed_at timestamptz not null default now(),
  primary key (analysis_id, stage)
);

-- ---------------------------------------------------------------- studio

-- Quarantined by design: studio runs never appear in `runs`, never contribute to a metric, a
-- shift, an index or the Results grid, and never enter Statistics. They are not evidence.
create table if not exists studio_runs (
  studio_run_id  uuid primary key default gen_random_uuid(),
  twin_id        text not null references twins(twin_id),
  version_code   text,
  custom_change  text,
  questions      text[] not null default '{}',
  include_battery boolean not null default false,
  answers        jsonb,
  free_answers   jsonb,
  scenario_text  jsonb,
  model          text not null,
  seed           bigint not null,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------- configuration

alter table agent_configs add column if not exists prompt_hash text not null default '';
alter table agent_configs add column if not exists output_mode text not null default 'tool';
alter table agent_configs add column if not exists frozen boolean not null default false;
alter table agent_configs add column if not exists frozen_at timestamptz;

-- ARCHITECTURE.md §3.2 enforced in DDL. Ollama Cloud accepts a JSON schema and silently does
-- not enforce it, so NativeOutput fails invisibly; the schema forbids even configuring it.
alter table agent_configs drop constraint if exists agent_no_native_output;
alter table agent_configs add constraint agent_no_native_output
  check (output_mode in ('tool', 'prompted'));

-- The "What was changed" panel on every Agent Studio screen. Append-only.
create table if not exists agent_config_history (
  history_id     bigserial primary key,
  agent_id       text not null,     -- or 'RULES' for the shared rules panel
  version        integer not null,
  snapshot       jsonb not null,
  changed_fields text[] not null,
  action         text not null,     -- saved | restored | frozen | unfrozen
  actor          text,
  created_at     timestamptz not null default now()
);
create index if not exists agent_config_history_recent_idx
  on agent_config_history (created_at desc);

-- ---------------------------------------------------------------- pointer flips (I9)

-- `quality_run_record` gains the 2.0 columns. The old signature is dropped rather than
-- overloaded, so there is exactly one way to append a quality row.
drop function if exists quality_run_record(text, uuid, text, numeric, numeric, boolean, jsonb, text);

create or replace function quality_run_record(
  p_twin_id text, p_session_id uuid, p_holdout_set text, p_arm text,
  p_items_n smallint, p_mae numeric, p_pct_within_1 numeric, p_correlations jsonb,
  p_kept boolean, p_repeats smallint, p_detail jsonb, p_model text, p_config_version integer
) returns twin_quality_runs language plpgsql as $$
declare
  v_row twin_quality_runs;
begin
  update twin_quality_runs set is_latest = false
   where twin_id = p_twin_id and holdout_set = p_holdout_set and is_latest;
  insert into twin_quality_runs
    (twin_id, session_id, holdout_set, arm, items_n, mae, pct_within_1, correlations,
     kept, repeats, detail, model, config_version, is_latest)
  values
    (p_twin_id, p_session_id, p_holdout_set, p_arm, p_items_n, p_mae, p_pct_within_1,
     p_correlations, p_kept, p_repeats, p_detail, p_model, p_config_version, true)
  returning * into v_row;
  return v_row;
end;
$$;

-- ---------------------------------------------------------------- RLS

alter table constructs          enable row level security;
alter table arms                enable row level security;
alter table legacy_items        enable row level security;
alter table synthetic_batches   enable row level security;
alter table survey_submissions  enable row level security;
alter table survey_answers      enable row level security;
alter table session_panel       enable row level security;
alter table validity_results    enable row level security;
alter table analysis_runs       enable row level security;
alter table analysis_results    enable row level security;
alter table studio_runs         enable row level security;
alter table agent_config_history enable row level security;

commit;
