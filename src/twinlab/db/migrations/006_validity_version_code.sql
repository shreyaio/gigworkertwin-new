-- 006 — validity_results.version_code
--
-- Additive, applied by hand (HANDOFF.md §0.7), same as 003/004/005.
--
-- Before this, a `validity_results` row recorded that a test ran and what it found, but not what
-- it was shown. Tests 4-8 put a stimulus to the panel through whichever version code the confirm
-- step resolved, and two FAIL rows for the same test could not be told apart without re-deriving
-- the version from the session and the UI default at the time. Test 2 always runs against SHAM;
-- tests 1 and 3 use no stimulus at all and leave this column null, which is the honest answer for
-- them, not a gap.
--
-- Nullable, no default: existing rows stay exactly as they are (I9, append-only — this is a column
-- added to the table, not a rewrite of what is already stored), and a null here means "no version
-- code applies to this test," not "unknown."

alter table validity_results add column if not exists version_code text;

comment on column validity_results.version_code is
  'The stimulus this test ran against: SHAM for test 2, the resolved version for tests 4-8, null '
  'for tests 1 and 3 (docs/DECISIONS.md, 2026-10-07).';
