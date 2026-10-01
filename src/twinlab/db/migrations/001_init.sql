-- Twin Lab initial schema. docs/01 section 4. Postgres 15 (Supabase).
-- Tables are created in FK dependency order. RLS is enabled on every table and no policy is
-- granted: the server uses the service key and bypasses RLS. There is no anon access.
--
-- Append-only by design (I9): runs, run_events, twin_answers, twin_quality_runs are never
-- UPDATEd to change evidence. "Latest" is a boolean pointer flipped in the same transaction.

begin;

-- ---------------------------------------------------------------- reference tables

create table if not exists scales (
  scale_id text primary key,
  points   smallint not null,
  format   text not null,
  anchors  jsonb not null
);

create table if not exists survey_items (
  item_id         text primary key,
  part            smallint not null,
  block           text not null,
  ordinal         smallint not null,
  stem            text not null,
  scale_id        text references scales(scale_id),
  reverse_coded   boolean not null default false,
  attention_check boolean not null default false,
  role            text not null,
  in_twin_battery boolean not null default false,
  mirrors         text references survey_items(item_id),
  version_shown   smallint,
  version_code    text
);
create index if not exists survey_items_block_ordinal_idx on survey_items (block, ordinal);

create table if not exists criteria (
  criterion_id      text primary key,
  principle         smallint not null,
  threshold_id      text not null,
  threshold_name    text not null,
  threshold_point   text not null,
  satisfaction_rule text not null,
  criterion_text    text not null
);

create table if not exists thresholds (
  threshold_id    text primary key,
  threshold_name  text not null,
  lever           text not null,
  awarded_2026    smallint not null default 0,
  gate_threshold  text references thresholds(threshold_id),
  reason          text not null
);

create table if not exists criterion_findings (
  criterion_id text primary key references criteria(criterion_id),
  finding      text not null,
  reason       text not null
);

create table if not exists gaps (
  gap_id         text primary key references criteria(criterion_id),
  threshold_id   text not null references thresholds(threshold_id),
  lever          text not null,
  gap_type       text not null,
  commitment     text not null,
  precedent      text not null,
  anchor_text    text not null,
  anchor_sources text[] not null
);

create table if not exists corpus_chunks (
  chunk_id        text primary key,
  source_id       text not null,
  source_type     text,
  jurisdiction    text,
  audience        text,
  lever           text,
  threshold_id    text,
  refiled_from    text,
  policy_surfaces text[],
  section         text,
  heading         text,
  verbatim_text   text not null,
  citation        text not null
);

create table if not exists chunk_criterion_links (
  link_id      text primary key,
  chunk_id     text not null references corpus_chunks(chunk_id),
  criterion_id text not null references criteria(criterion_id),
  judgement    text not null
);
create index if not exists chunk_criterion_links_criterion_idx
  on chunk_criterion_links (criterion_id);

-- ---------------------------------------------------------------- twins

create table if not exists twins (
  twin_id           text primary key,
  source            text not null default 'real',
  service           text,
  city              text,
  age               smallint,
  gender            text,
  tenure_months     smallint,
  hours_per_week    smallint,
  consent_twin      boolean not null,
  -- Part 3 extras, Part 4 background and Part 14 own-words, verbatim. These are survey content
  -- with no item_id: the 73-item register is frozen (docs/01 §2) and survey_responses.item_id is
  -- FK'd to it, so they cannot be rows there. The persona must be lossless (docs/02 §5), so they
  -- are kept here rather than dropped. Written once at intake; never edited by the app.
  background        jsonb not null default '{}'::jsonb,
  persona_passage   text,
  persona_hash      text,
  persona_template_version text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index if not exists twins_consented_idx on twins (consent_twin) where consent_twin;

create table if not exists survey_responses (
  twin_id    text not null references twins(twin_id) on delete cascade,
  item_id    text not null references survey_items(item_id),
  value_num  smallint,
  value_text text,
  why_text   text,
  language   text,
  primary key (twin_id, item_id)
);

-- ---------------------------------------------------------------- sessions, variants, runs

create table if not exists sessions (
  session_id   uuid primary key default gen_random_uuid(),
  name         text not null,
  status       text not null default 'created',
  iterations   smallint not null default 1,
  start_code   text not null default '10000',
  cursor_index smallint,
  completed    smallint not null default 0,
  config       jsonb not null,
  created_at   timestamptz not null default now(),
  finished_at  timestamptz
);

create table if not exists lever_paragraphs (
  paragraph_id  uuid primary key default gen_random_uuid(),
  lever         text not null,
  dial          smallint not null,
  style_version text not null,
  text          text not null,
  word_count    smallint not null,
  delta_hash    text not null,
  checker_pass  boolean not null default false,
  created_at    timestamptz not null default now()
);
create unique index if not exists lever_paragraphs_key_uq
  on lever_paragraphs (lever, dial, style_version);

create table if not exists variants (
  variant_id    uuid primary key default gen_random_uuid(),
  version_code  text not null,
  style_version text not null,
  delta_spec    jsonb not null,
  delta_hash    text not null,
  paragraphs    jsonb not null,
  checker       jsonb not null,
  created_at    timestamptz not null default now()
);
create unique index if not exists variants_key_uq on variants (version_code, style_version);

create table if not exists runs (
  run_id       uuid primary key default gen_random_uuid(),
  session_id   uuid not null references sessions(session_id) on delete cascade,
  version_code text not null,
  status       text not null default 'pending',
  variant_id   uuid references variants(variant_id),
  twins_n      smallint,
  metrics      jsonb,
  index_value  numeric(6,3),
  llm_analysis text,
  error        text,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  is_latest_for_version boolean not null default false
);
-- THE CACHE. One completed run per version code is the current answer (docs/03 section 4).
create unique index if not exists runs_latest_uq
  on runs (version_code) where is_latest_for_version;
create index if not exists runs_session_status_idx on runs (session_id, status);

create table if not exists run_events (
  event_id        bigserial primary key,
  session_id      uuid not null references sessions(session_id) on delete cascade,
  run_id          uuid references runs(run_id) on delete cascade,
  parent_event_id bigint references run_events(event_id),
  ts              timestamptz not null default now(),
  stage           text not null,
  agent           text,
  label           text not null,
  status          text not null,
  payload         jsonb,
  logfire_span_id text
);
create index if not exists run_events_session_idx on run_events (session_id, event_id);
create index if not exists run_events_parent_idx on run_events (parent_event_id);

create table if not exists twin_answers (
  answer_id   uuid primary key default gen_random_uuid(),
  run_id      uuid not null references runs(run_id) on delete cascade,
  twin_id     text not null references twins(twin_id),
  answers     jsonb not null,
  lever_order smallint[] not null,
  seed        bigint not null,
  wording     text not null,
  model       text not null,
  latency_ms  integer,
  created_at  timestamptz not null default now()
);
create unique index if not exists twin_answers_uq on twin_answers (run_id, twin_id, wording);

create table if not exists twin_quality_runs (
  quality_run_id  uuid primary key default gen_random_uuid(),
  twin_id         text not null references twins(twin_id) on delete cascade,
  session_id      uuid references sessions(session_id),
  holdout_set     text not null,
  mae             numeric(5,3) not null,
  pct_within_1    numeric(4,3) not null,
  kept            boolean not null,
  detail          jsonb not null,
  model           text,
  created_at      timestamptz not null default now(),
  is_latest       boolean not null default true
);
create unique index if not exists twin_quality_runs_latest_uq
  on twin_quality_runs (twin_id, holdout_set) where is_latest;

-- ---------------------------------------------------------------- configuration

create table if not exists agent_configs (
  agent_id      text primary key,
  name          text not null,
  role          text not null,
  enabled       boolean not null default true,
  model         jsonb not null,
  system_prompt text not null,
  instructions  text[] not null default '{}',
  input_schema  text not null,
  output_schema text not null,
  tools         text[] not null default '{}',
  context_sources jsonb not null default '[]',
  react         boolean not null default false,
  retry         jsonb not null default '{"attempts":2,"backoff":"exponential"}',
  version       integer not null default 1,
  updated_at    timestamptz not null default now()
);

create table if not exists app_config (
  key        text primary key,
  value      jsonb not null,
  version    integer not null default 1,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- atomic pointer flips (I9)

-- PostgREST cannot send two statements in one transaction, and I9 requires the demote and the
-- insert to land together. Both pointer flips are therefore Postgres functions, called by RPC.

create or replace function runs_complete(
  p_run_id uuid, p_metrics jsonb, p_index numeric, p_analysis text, p_twins_n smallint
) returns runs language plpgsql as $$
declare
  v_code text;
  v_row  runs;
begin
  select version_code into v_code from runs where run_id = p_run_id;
  if v_code is null then
    raise exception 'runs_complete: no run %', p_run_id;
  end if;
  update runs set is_latest_for_version = false
   where version_code = v_code and is_latest_for_version;
  update runs
     set status = 'completed', finished_at = now(), is_latest_for_version = true,
         metrics = p_metrics, index_value = p_index, llm_analysis = p_analysis,
         twins_n = p_twins_n
   where run_id = p_run_id
  returning * into v_row;
  return v_row;
end;
$$;

create or replace function quality_run_record(
  p_twin_id text, p_session_id uuid, p_holdout_set text, p_mae numeric,
  p_pct_within_1 numeric, p_kept boolean, p_detail jsonb, p_model text
) returns twin_quality_runs language plpgsql as $$
declare
  v_row twin_quality_runs;
begin
  update twin_quality_runs set is_latest = false
   where twin_id = p_twin_id and holdout_set = p_holdout_set and is_latest;
  insert into twin_quality_runs
    (twin_id, session_id, holdout_set, mae, pct_within_1, kept, detail, model, is_latest)
  values
    (p_twin_id, p_session_id, p_holdout_set, p_mae, p_pct_within_1, p_kept, p_detail,
     p_model, true)
  returning * into v_row;
  return v_row;
end;
$$;

-- ---------------------------------------------------------------- RLS

alter table scales                enable row level security;
alter table survey_items          enable row level security;
alter table criteria              enable row level security;
alter table thresholds            enable row level security;
alter table criterion_findings    enable row level security;
alter table gaps                  enable row level security;
alter table corpus_chunks         enable row level security;
alter table chunk_criterion_links enable row level security;
alter table twins                 enable row level security;
alter table survey_responses      enable row level security;
alter table sessions              enable row level security;
alter table lever_paragraphs      enable row level security;
alter table variants              enable row level security;
alter table runs                  enable row level security;
alter table run_events            enable row level security;
alter table twin_answers          enable row level security;
alter table twin_quality_runs     enable row level security;
alter table agent_configs         enable row level security;
alter table app_config            enable row level security;

commit;
