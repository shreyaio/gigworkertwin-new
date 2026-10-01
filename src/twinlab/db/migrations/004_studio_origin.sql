-- Twin Studio results may feed analysis, and every number says where it came from.
-- ARCHITECTURE_UPDATE.md §4.3, §4.4 and §7. RESEARCHER 2026-10-01.
--
-- ADDITIVE, per docs/01 §6. Nothing is dropped, nothing is renumbered, and no existing row
-- changes meaning: every `runs` row written before this migration was written by a sweep or an
-- ask from the Dial board, which is exactly what the default of 'sweep' says.
--
-- WHY THIS EXISTS AT ALL. The researcher confirmed that a Twin Studio ask may feed the analysis
-- ("by overwrite, it's ok for the studio values to feed analyses"), which reverses `docs/01` §6.9's
-- blanket quarantine for the dialled-version path. It is satisfiable WITHOUT breaking CLAUDE.md
-- rule 6, because `services/results.completed_runs` already selects the latest run per
-- `version_code` by `started_at` descending:
--
--   * a Studio ask APPENDS a `runs` row and `twin_answers` rows; nothing is updated in place;
--   * a later Dial board run for the same code has a newer `started_at`, becomes the latest, and
--     supersedes the Studio value automatically.
--
-- That is the requested precedence with no precedence logic to write or get wrong. What it costs
-- is that a version whose most recent run is a Studio run reports an index computed from ONE twin
-- rather than from the frozen panel, while `00000` and `SHAM` — the noise floor a lever effect must
-- clear — come from the panel. A Studio-origin number and a sweep number are therefore not the
-- same quantity. `origin` is what makes that difference live in the DATA rather than in a future
-- reader's head, which is the whole reason this column exists instead of inferring it from
-- `twins_n = 1`.

begin;

-- ---------------------------------------------------------------- runs.origin

alter table runs add column if not exists origin text not null default 'sweep';

-- Two origins, and there is no third. A 'studio' run is one twin answering one cell from the
-- Twin Studio; a 'sweep' run is the frozen panel answering it from the Dial board or a sweep.
-- Constrained in DDL so a hand-written INSERT in the SQL editor cannot invent a third value that
-- the Results table would then render as a blank badge.
alter table runs drop constraint if exists runs_origin_check;
alter table runs add constraint runs_origin_check check (origin in ('sweep', 'studio'));

comment on column runs.origin is
  'Where this run came from. ''sweep'' = the frozen panel (a sweep or a Dial board ask). '
  '''studio'' = one twin, from the Twin Studio, so twins_n = 1 and the index is over one person. '
  'Shown beside every number this run produces (ARCHITECTURE_UPDATE.md §4.3 item 4).';

-- I15 is unchanged and still enforced by `runs_completed_has_twins`: twins_n = 1 >= 1, so a
-- Studio run is a legitimate completed run, and a Studio ask whose twin fails the answer ladder
-- is `failed` — never `completed` with an index of 0.000.

-- ---------------------------------------------------------------- studio_runs pointer

alter table studio_runs
  add column if not exists is_latest_for_twin_version boolean not null default true;

-- BACKFILL, and it must run before the index below exists. The column defaults to true, so
-- every pre-004 row claims to be current; a twin asked the same cell twice in the Studio before
-- this migration therefore has two current rows and `studio_runs_latest_uq` refuses to build
-- ("Key (...)=(SYN-30092026-0001, 22000, ) is duplicated").
--
-- The resolution is a DEMOTE, never a delete: the losing rows keep every field they had and only
-- stop being the pointer, which is exactly what a second ask would have done to the first had the
-- pointer existed at the time (CLAUDE.md rule 6 — evidence is append-only, and `is_latest_*` is a
-- boolean pointer, not a fact about the answer).
--
-- Newest wins by `created_at`, tie-broken by `studio_run_id`, because `created_at` has no
-- uniqueness guarantee and two rows inserted in the same millisecond must still resolve to one
-- winner or the index fails again. Idempotent: on a database with no duplicates it updates nothing.
with ranked as (
  select studio_run_id,
         row_number() over (
           partition by twin_id,
                        coalesce(version_code, ''),
                        coalesce(custom_change, '')
           order by created_at desc, studio_run_id desc
         ) as rn
    from studio_runs
   where is_latest_for_twin_version
)
update studio_runs s
   set is_latest_for_twin_version = false
  from ranked r
 where s.studio_run_id = r.studio_run_id
   and r.rn > 1;

-- Flipped in the same transaction as the insert, exactly as `runs.is_latest_for_version` is
-- (ARCHITECTURE_UPDATE.md §4.4). A second ask for the same (twin_id, version_code, wording)
-- appends and moves the pointer; the earlier row survives. `studio_runs` keeps being the full
-- sandbox record, because it holds `free_answers`, `questions` and `scenario_text` that
-- `twin_answers` has no column for.
--
-- `custom_change` is part of the key because a custom free-text ask is NOT filed under a version
-- code (its `version_code` is null by construction), so two different custom changes for one twin
-- are two different questions and both are current. `coalesce` is what makes that work inside a
-- partial unique index over nullable columns.
create unique index if not exists studio_runs_latest_uq
  on studio_runs (twin_id, coalesce(version_code, ''), coalesce(custom_change, ''))
  where is_latest_for_twin_version;

comment on column studio_runs.is_latest_for_twin_version is
  'The current answer for this (twin, version_code, custom_change). Append-only: a second ask '
  'demotes the previous holder in the same transaction and the earlier row survives (I9).';

-- The pointer flip, as an RPC, for the same reason `runs_complete` is one: the demote and the
-- insert must be ONE transaction, or a crash between them leaves either two current rows (which
-- the index above refuses) or none (which reads as "never asked").
create or replace function studio_run_record(p_row jsonb)
returns jsonb
language plpgsql
as $$
declare
  v_row studio_runs;
begin
  update studio_runs
     set is_latest_for_twin_version = false
   where twin_id = p_row->>'twin_id'
     and coalesce(version_code, '') = coalesce(p_row->>'version_code', '')
     and coalesce(custom_change, '') = coalesce(p_row->>'custom_change', '')
     and is_latest_for_twin_version;

  insert into studio_runs
    (studio_run_id, twin_id, version_code, custom_change, questions, include_battery,
     answers, free_answers, scenario_text, model, seed, is_latest_for_twin_version)
  select
    coalesce((p_row->>'studio_run_id')::uuid, gen_random_uuid()),
    p_row->>'twin_id',
    p_row->>'version_code',
    p_row->>'custom_change',
    coalesce(
      (select array_agg(value) from jsonb_array_elements_text(p_row->'questions')),
      '{}'::text[]
    ),
    coalesce((p_row->>'include_battery')::boolean, false),
    p_row->'answers',
    p_row->'free_answers',
    p_row->'scenario_text',
    p_row->>'model',
    coalesce((p_row->>'seed')::bigint, 0),
    true
  returning * into v_row;

  return to_jsonb(v_row);
end;
$$;

-- ---------------------------------------------------------------- sessions.purpose

-- ARCHITECTURE_UPDATE.md §7, option 1. Studio asks now write to `runs` and `twin_answers`, so
-- smoke-test rows and study rows share a table. A test session is MARKED rather than inferred
-- later from its panel size: option 2 works but requires a future reader to know to look at
-- `sessions.config.panel_size`, and a convention nobody is told about is not evidence hygiene.
alter table sessions add column if not exists purpose text not null default 'study';

alter table sessions drop constraint if exists sessions_purpose_check;
alter table sessions add constraint sessions_purpose_check
  check (purpose in ('smoke', 'study'));

comment on column sessions.purpose is
  'Why this session ran. ''study'' is the default and the reportable case; ''smoke'' marks a '
  'plumbing test whose numbers must never be quoted. Marked at creation, never inferred later '
  'from panel size (ARCHITECTURE_UPDATE.md §7).';

commit;
