-- The re-render budget, made durable. HANDOFF_M15_LIVE_PATH.md §3.2, RESEARCHER 2026-10-01.
--
-- ADDITIVE, per docs/01 §6. Nothing is dropped and no existing row changes meaning: a
-- `lever_paragraphs` row written before this migration was written by a first render, which is
-- exactly what the default of 1 says.
--
-- `docs/03` §5 specifies "fail any gate -> re-render ONCE -> then halt that cell". Until now the
-- budget lived in a module-level set in `services/twin_runtime.py`, so every restart handed every
-- (lever, dial, style_version) key a fresh re-render -- a defensible reading of "once", but not
-- what the words say, and it meant the number of design calls a paragraph had consumed was
-- recorded nowhere. I4 asserts a design-call count, and that assertion needs a denominator that
-- survives a process.
--
-- `attempts` is that denominator: design calls spent on this key, ever. 1 = rendered once.
-- 2 = the one re-render `docs/03` §5 allows has been spent, and the cell halts.

begin;

alter table lever_paragraphs add column if not exists attempts smallint not null default 1;

-- The ceiling is the specification's, not a preference. A key at 2 has spent its re-render; a
-- third design call on the same paragraph would break I4's count and is refused in Python. The
-- constraint is here as well so a hand-written UPDATE in the SQL editor cannot make the data say
-- something the code will not.
alter table lever_paragraphs drop constraint if exists lever_paragraphs_attempts;
alter table lever_paragraphs
  add constraint lever_paragraphs_attempts check (attempts between 1 and 2);

comment on column lever_paragraphs.attempts is
  'Design calls spent on this (lever, dial, style_version), ever. 1 = first render; 2 = the one '
  're-render docs/03 §5 allows has been spent and the cell halts. Durable on purpose: the budget '
  'must not reset when the Space restarts.';

commit;
