# Archived — v1.0 documents

**Superseded on 2026-09-28 by `ARCHITECTURE.md` 2.0 and `docs/01`–`docs/11`.**

Kept for provenance only. **Do not build from anything in this folder.** Where a statement here
conflicts with the current set, the current set wins without exception.

| Archived | Superseded by |
|---|---|
| `02_AGENTS_AND_PIPELINE.md` | `docs/02_AGENTS_AND_PROMPTS.md` + `docs/03_RESEARCH_PIPELINE.md` |
| `03_BACKEND.md` | `docs/04_BACKEND.md` |
| `04_FRONTEND.md` | `docs/05_DESIGN_SYSTEM.md` + `docs/06_SCREENS.md` |
| `05_BUILD_PLAN.md` | `docs/11_BUILD_PLAN.md` |
| `HANDOFF_v1.md` | `docs/11_BUILD_PLAN.md` — and it is now **actively wrong** |

## Why `HANDOFF_v1.md` is dangerous rather than merely stale

It states *"M0–M10 are complete, 212 tests pass"* and lists the v1.0 milestones as done. That was
true of the v1.0 build. The v2.0 build plan has fourteen different milestones against a different
schema, a different agent contract and a different deployment target, and the `src/` tree is being
rebuilt against them. A fresh session reading that file would believe the work was finished.

## The specific things these files get wrong now

- **`max_concurrency: 4`.** The free provider tier permits **one** concurrent request.
- **`NativeOutput` / provider-enforced schemas.** Ollama Cloud accepts a JSON schema and silently
  does not enforce it. Validation is Python's job (I13).
- **`survey_responses(twin_id, item_id)`.** Split into `survey_submissions` + `survey_answers`; the
  old shape had nowhere to put a respondent who was screened out or withheld consent.
- **Five Gradio tabs.** The application has eight routes and Twin Lab has eight sub-tabs.
- **Docker SDK on a free Hugging Face Space.** Free accounts get ZeroGPU Gradio Spaces only.
- **`data/temp/survey_<id>.json` as the audit mirror.** Space disk is ephemeral (I16); the mirror
  is a Supabase Storage object and intake runs in an Edge Function outside the Space.
- **Eleven invariants.** There are seventeen.
- **Python 3.11.** The target is 3.13.
- **No frozen analysis panel**, so a sweep could silently use a different twin set per cell (I14).
- **The Analyst had ReAct and history tools** — an unbounded path for an ungiven number to reach
  its prose.

See `docs/DECISIONS.md` → *Revamp 2026-09 — v2.0* for why each changed.
