-- The control cells move into the twin quality test, and every quality verdict is matched to the
-- config it was produced under. RESEARCHER 2026-10-05 (docs/DECISIONS.md).
--
-- WHY. `00000` (noise floor) and `SHAM` (demand floor) were answered again in every session, once
-- per panel, at 10 calls a session. Their answers depend on the twin and the config, not on the
-- session, so they are answered once per twin per config here, in the gate, and every session's
-- floors are assembled from its panel's stored answers. A session then costs its version calls
-- only.
--
-- A verdict is only valid for the config that produced it. `config_fingerprint` is a hash of the
-- model, temperature, wording, prompt, battery, style version and kept thresholds (see
-- services/config_match.py). A quality row without a fingerprint, or with another one, does not
-- qualify a twin for the current config, and nothing downstream may run until the gate is re-run.
--
-- ADDITIVE, per docs/01 §6. Existing quality rows keep their values; they have a null fingerprint
-- and therefore do not qualify any twin under the config that is live now.

begin;

alter table twin_quality_runs add column if not exists config_fingerprint text;

-- The RPC gains a parameter, so it is dropped and recreated rather than replaced. Postgres treats a
-- different argument list as a different function, and leaving the old one would let a caller use
-- the un-fingerprinted path by accident.
drop function if exists quality_run_record(
  text, uuid, text, text, smallint, numeric, numeric, jsonb, boolean, smallint, jsonb, text, integer
);

create or replace function quality_run_record(
  p_twin_id text, p_session_id uuid, p_holdout_set text, p_arm text,
  p_items_n smallint, p_mae numeric, p_pct_within_1 numeric, p_correlations jsonb,
  p_kept boolean, p_repeats smallint, p_detail jsonb, p_model text, p_config_version integer,
  p_config_fingerprint text default null
) returns twin_quality_runs language plpgsql as $$
declare
  v_row twin_quality_runs;
begin
  update twin_quality_runs set is_latest = false
   where twin_id = p_twin_id and holdout_set = p_holdout_set and is_latest;
  insert into twin_quality_runs
    (twin_id, session_id, holdout_set, arm, items_n, mae, pct_within_1, correlations,
     kept, repeats, detail, model, config_version, config_fingerprint, is_latest)
  values
    (p_twin_id, p_session_id, p_holdout_set, p_arm, p_items_n, p_mae, p_pct_within_1,
     p_correlations, p_kept, p_repeats, p_detail, p_model, p_config_version,
     p_config_fingerprint, true)
  returning * into v_row;
  return v_row;
end;
$$;

-- One answer per twin, per control, per config. Append-only: the gate looks for an existing row
-- before it asks, so a second gate run under the same config spends no calls and writes nothing.
create table if not exists twin_control_answers (
  control_answer_id uuid primary key default gen_random_uuid(),
  twin_id           text not null references twins(twin_id),
  control_code      text not null check (control_code in ('00000', 'SHAM')),
  config_fingerprint text not null,
  answers           jsonb not null,
  lever_order       smallint[] not null,
  seed              bigint not null,
  wording           text not null,
  model             text not null,
  prompt_version    text,
  retries           smallint not null default 0,
  session_id        uuid references sessions(session_id),
  created_at        timestamptz not null default now(),
  constraint twin_control_once unique (twin_id, control_code, config_fingerprint)
);
create index if not exists twin_control_answers_config_idx
  on twin_control_answers (config_fingerprint, control_code);

alter table twin_control_answers enable row level security;

commit;
