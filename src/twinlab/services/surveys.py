"""Survey-facing service functions. `docs/04` §2.

`ARCHITECTURE.md` §8.2 rule 3: every capability is a service-layer function, and `api/` is an
optional wrapper over this. No feature may depend on an HTTP route existing.
"""

from __future__ import annotations

import logging
from typing import Any

from twinlab.db.client import DbBackend, get_backend
from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE

log = logging.getLogger(__name__)

#: `twins.source` for a synthetic twin. Matches `orchestrator.panel.POPULATION_SOURCES`.
SYNTHETIC_TWIN_SOURCE = "synthetic"


#: `docs/06` §2's instrument facts. Read off the frozen register rather than restated, so a page
#: claiming "112 questions" cannot drift from the register that holds them (`CLAUDE.md` rule 8).
#: The three languages are the Form's own (`docs/GOOGLE_FORM.md`).
SURVEY_LANGUAGES: tuple[str, ...] = ("English", "Hindi", "Marathi")

#: `docs/06` §2, verbatim. The instrument's most load-bearing property, so the page states it.
HOLDOUT_WARNING = (
    "Parts 15, 16 and 17 are holdout material and must never enter a persona (I6). They are how "
    "a twin is scored, not what a twin is told."
)

#: `docs/06` §2's placeholder, in its own words, for when the **Edge Function** is not configured.
#: It no longer means "there is no survey": since 2026-10-08 the questionnaire is hosted at
#: :data:`HOSTED_SURVEY_PATH` and a driver can fill it in whether or not this endpoint exists.
INTAKE_PLACEHOLDER = (
    "The Google Form intake endpoint is not configured. The hosted questionnaire below does not "
    "need it — it writes through this application — so this panel is about the Form path only."
)

#: Where a driver fills the questionnaire in. A path, not a URL: the origin depends on where the
#: application is deployed, and the page appends it to whatever the browser is already on.
HOSTED_SURVEY_PATH = "/take"

#: Shown beside the link. The durability trade `ARCHITECTURE.md` §8.2 rule 2 exists to avoid is
#: real and is not mitigated by hosting, so the researcher is told rather than left to find out.
HOSTED_SURVEY_NOTE = (
    "This link is the questionnaire itself, served by this application. A submission is written "
    "to Storage before any table row (I16), so a failed insert leaves a replayable object — but "
    "a request that never arrives cannot be stored at all. On a free Space that sleeps after 48 "
    "hours idle, keep the Edge Function path configured as well for unattended fieldwork "
    "(ARCHITECTURE.md §8.2 rule 2, docs/DECISIONS.md 2026-10-08)."
)


async def survey_status(backend: DbBackend | None = None) -> dict[str, Any]:
    """Everything `docs/06` §2's Driver survey shows. **It reports on intake, never hosts it.**

    §2 is explicit that the driver-facing instrument is the existing Google Form and that intake
    runs in a Supabase Edge Function outside the Space (`docs/04` §8), so a sleeping Space cannot
    drop a submission. Nothing here accepts a submission; every number is read back from what
    intake already stored.

    **Synthetic rows are excluded from every fieldwork number and counted separately.** A real
    intake count that quietly included the 300-row synthetic batch would read as fieldwork that
    has not happened (`docs/08` §6.2).
    """
    from config.settings import settings
    from twinlab.ingest.reference_store import reference
    from twinlab.ingest.survey_intake import form_map
    from twinlab.services.lab import fieldwork_counts
    from twinlab.survey.instrument import hosted_instrument

    ref = reference()
    counts = await fieldwork_counts(backend)
    db = backend or get_backend()
    real = [
        row for row in await db.select("survey_submissions", None)
        if row.get("data_type") != SYNTHETIC_DATA_TYPE
    ]
    stamps = sorted(str(r.get("submitted_at") or "") for r in real if r.get("submitted_at"))
    today = max(stamps)[:10] if stamps else ""

    hosted = hosted_instrument()
    return {
        # Where a driver fills it in, and how much of it they are asked (§2.1).
        "hosted_path": HOSTED_SURVEY_PATH,
        "hosted_note": HOSTED_SURVEY_NOTE,
        "hosted_stops": len(hosted.stops),
        "hosted_probes": sum(1 for q in hosted.questions if q.is_why),
        # What the instrument is (§2).
        "parts": max(item.part for item in ref.items.values()),
        # §2's "112 questions" is every Form question, not only the register's scored items —
        # it counts the screeners, the consents, the demographics, the why-probes and the
        # own-words fields too. Both numbers are shown, because a reader who sees only 112 cannot
        # tell how many of them are scored, and one who sees only 73 thinks the Form is shorter
        # than it is. Counted off `form_map.yaml` and the register, never written down here.
        "questions": len(form_map()),
        "items": len(ref.items),
        "languages": list(SURVEY_LANGUAGES),
        # Live intake status (§2). "Configured" is the honest word: the Space never calls the
        # endpoint to prove it is reachable, because a Space that probed intake on every render
        # would be the one thing §2 says it must not be — a participant in the intake path.
        "intake_configured": bool(settings.survey_intake_url and settings.intake_hmac_secret),
        "intake_url": settings.survey_intake_url,
        "form_url": settings.survey_form_url,
        "last_submission": stamps[-1][:19] if stamps else "",
        "received_today": sum(1 for s in stamps if s[:10] == today) if today else 0,
        "real_total": counts["real_total"],
        "synthetic_total": counts["synthetic_total"],
        # Four-arm balance by `city|service` (§2, `docs/01` §5.2).
        "arm_balance": counts["arm_balance"],
        "arms": sorted(ref.arms),
        "per_day": counts["per_day"],
    }


async def counts_by_type(backend: DbBackend | None = None) -> dict[str, int]:
    """How many submissions of each `data_type`. `docs/04` §2."""
    db = backend or get_backend()
    rows = await db.select("survey_submissions", None)
    out: dict[str, int] = {}
    for row in rows:
        key = str(row.get("data_type"))
        out[key] = out.get(key, 0) + 1
    return out


#: Tables that reference `twins(twin_id)` **without** `on delete cascade`, and whether a row in
#: each is a reason to refuse the delete. `ARCHITECTURE_UPDATE.md` §3.4.
#:
#: * ``twin_answers`` — evidence. Deleting the twin would change a stored result (rule 6).
#: * ``session_panel`` — the frozen panel. I14: a panel member cannot vanish from under a session.
#: * ``studio_runs`` — the quarantined sandbox. A conversation about a twin that no longer exists
#:   is not evidence of anything, so these go with the twin rather than blocking it.
BLOCKING_TWIN_REFERENCES: tuple[tuple[str, str], ...] = (
    ("twin_answers", "have answered a run"),
    ("session_panel", "sit on a frozen analysis panel"),
)

#: Tables that must be emptied, **children first**, before a `sessions` row can go.
#:
#: The first four cascade from `sessions` (or from `runs`, which cascades from `sessions`) in
#: Postgres and are deleted explicitly so the in-memory backend behaves identically — the same
#: reason `survey_answers` is deleted explicitly in :func:`delete_synthetic`.
#:
#: **The last three do not cascade at all**, and a session delete that skipped them would fail
#: with a raw `23503`: `twin_quality_runs`, `validity_results` and `twin_control_answers` all
#: reference `sessions(session_id)` with no `on delete` clause. `validity_results` is the one
#: worth naming — it holds the verdicts of the eight tests, so purging a synthetic session
#: discards the synthetic verdicts computed from it. That is the point rather than a side effect:
#: a verdict about twins that no longer exist describes nothing.
SESSION_CASCADE_ORDER: tuple[tuple[str, str], ...] = (
    ("twin_answers", "run_id"),
    ("run_events", "session_id"),
    ("runs", "session_id"),
    ("session_panel", "session_id"),
    ("twin_quality_runs", "session_id"),
    ("validity_results", "session_id"),
    ("twin_control_answers", "session_id"),
)

#: Referencing tables deleted alongside the twin, in the order they must go (children first).
#:
#: **Every table referencing `twins(twin_id)` must appear here or in
#: :data:`BLOCKING_TWIN_REFERENCES`**, and `tests/test_m22_hosted_survey.py` reads the migrations
#: and asserts it. This list has now been wrong twice for the same reason — a table added in a
#: later migration, never added here, and `delete_synthetic` failing with a raw `23503` the first
#: time a researcher pressed the button. `studio_runs` was the first; `twin_control_answers`
#: (migration 005) was the second and made the button fail against any synthetic twin that had
#: answered a control cell, which after one config-matched run is all of them.
#:
#: * ``studio_runs`` — the quarantined sandbox. A conversation about a twin that no longer exists
#:   is not evidence of anything.
#: * ``twin_quality_runs`` — the DDL already cascades these. Listed so the in-memory backend
#:   behaves identically, which is the same reason `survey_answers` is deleted explicitly below.
#: * ``twin_control_answers`` — the config-matched `00000` and `SHAM` cache (migration 005). Keyed
#:   by config fingerprint and regenerable, and it references `twins` with **no** cascade, so it
#:   has to go before the twin rather than after.
#: * ``survey_responses`` — the v1 table, superseded by `survey_submissions` + `survey_answers`
#:   and deliberately not dropped (migration 002). Nothing in 2.0 writes to it, and the DDL
#:   cascades, so this is listed for completeness and for in-memory parity rather than because a
#:   row is expected. Found by the coverage test, not by a failure.
CASCADING_TWIN_REFERENCES: tuple[str, ...] = (
    "studio_runs",
    "twin_control_answers",
    "twin_quality_runs",
    "survey_responses",
)


class DeleteBlocked(RuntimeError):
    """Some synthetic twins cannot be deleted without changing a stored result.

    Raised instead of letting Postgres answer with a `23503`. The researcher needs the sentence,
    not the constraint name: which twins, why, and what deleting the rest would do.
    """

    def __init__(self, message: str, *, blocked: dict[str, list[str]], deletable: int) -> None:
        super().__init__(message)
        self.blocked = blocked
        self.deletable = deletable


async def synthetic_delete_preflight(
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """What a delete *would* do, counted **before** anything is deleted. §3.4.

    Pure read. Returns the synthetic submission ids, which of their twins are blocked and by what,
    and how many would go. The Generator screen shows this and the delete refuses on it, so the
    researcher is never shown a traceback where a sentence belongs — and never sees the same
    foreign-key violation four times because a retry loop treated a deterministic refusal as a
    flaky connection (§3.3).
    """
    db = backend or get_backend()
    submissions = await db.select(
        "survey_submissions", [("eq", "data_type", SYNTHETIC_DATA_TYPE)]
    )
    ids = sorted(str(r["submission_id"]) for r in submissions)
    twins = (
        await db.select(
            "twins", [("eq", "source", SYNTHETIC_TWIN_SOURCE), ("in", "twin_id", ids)]
        )
        if ids
        else []
    )
    twin_ids = sorted(str(r["twin_id"]) for r in twins)

    blocked: dict[str, list[str]] = {}
    if twin_ids:
        for table, _why in BLOCKING_TWIN_REFERENCES:
            rows = await db.select(table, [("in", "twin_id", twin_ids)])
            held = sorted({str(r["twin_id"]) for r in rows})
            if held:
                blocked[table] = held
    held_all = sorted({t for ids_ in blocked.values() for t in ids_})
    sessions = await _dependent_sessions(twin_ids, db) if held_all else []
    return {
        "submission_ids": ids,
        "twin_ids": twin_ids,
        "blocked": blocked,
        "blocked_twin_ids": held_all,
        "deletable_twin_ids": [t for t in twin_ids if t not in set(held_all)],
        #: Every session holding one of these twins. Each is synthetic-contaminated by
        #: construction — it is here only because a synthetic twin sits on its panel or answered
        #: one of its runs, so its `index_value` was computed over synthetic twins and
        #: `docs/08` §6.2 already says that number proves nothing about drivers.
        "dependent_sessions": sessions,
        #: The ones made of synthetic twins **alone**, which a purge may take without putting a
        #: single real row at risk. *Delete all synthetic surveys* purges exactly these.
        "purgeable_session_ids": [s["session_id"] for s in sessions if s["synthetic_only"]],
        #: The ones that *also* hold real twins. The generator **never** touches these: *delete
        #: all synthetic surveys* means synthetic, so a real driver's rows are not at risk from
        #: that screen whatever is ticked, and the synthetic twins sitting on such a session stay
        #: too. Clearing one is a per-twin decision made in Twin Lab → Twins, which is where
        #: ``allow_real_loss`` is reachable from.
        "mixed_session_ids": [s["session_id"] for s in sessions if not s["synthetic_only"]],
        "real_twins_at_risk": sorted(
            {t for s in sessions for t in s["real_twin_ids"]}
        ),
    }


async def _dependent_sessions(
    twin_ids: list[str], db: DbBackend
) -> list[dict[str, Any]]:
    """Which sessions hold these twins, and whether each is made of synthetic twins alone.

    A session is **synthetic-only** when every twin on its panel and every twin that answered one
    of its runs is in ``twin_ids``. Both are checked rather than the panel alone: a run can hold
    an answer from a twin the panel no longer lists, and a session judged synthetic on its panel
    while holding one real driver's answer would lose that answer to a purge.
    """
    synthetic = set(twin_ids)
    if not synthetic:
        return []

    panel = await db.select("session_panel", [("in", "twin_id", twin_ids)])
    answers = await db.select("twin_answers", [("in", "twin_id", twin_ids)])
    run_ids = sorted({str(r["run_id"]) for r in answers})
    runs = await db.select("runs", [("in", "run_id", run_ids)]) if run_ids else []
    session_of_run = {str(r["run_id"]): str(r["session_id"]) for r in runs}

    touched = {str(r["session_id"]) for r in panel}
    touched |= {
        session_of_run[str(r["run_id"])]
        for r in answers
        if str(r["run_id"]) in session_of_run
    }
    if not touched:
        return []

    ids = sorted(touched)
    session_rows = await db.select("sessions", [("in", "session_id", ids)])
    rows = {str(r["session_id"]): r for r in session_rows}
    all_panel = await db.select("session_panel", [("in", "session_id", ids)])
    all_runs = await db.select("runs", [("in", "session_id", ids)])
    all_run_ids = sorted({str(r["run_id"]) for r in all_runs})
    all_answers = (
        await db.select("twin_answers", [("in", "run_id", all_run_ids)]) if all_run_ids else []
    )
    run_session = {str(r["run_id"]): str(r["session_id"]) for r in all_runs}

    out: list[dict[str, Any]] = []
    for session_id in ids:
        members = {str(r["twin_id"]) for r in all_panel if str(r["session_id"]) == session_id}
        answered = {
            str(r["twin_id"])
            for r in all_answers
            if run_session.get(str(r["run_id"])) == session_id
        }
        everyone = members | answered
        row = rows.get(session_id) or {}
        out.append({
            "session_id": session_id,
            "name": str(row.get("name") or session_id),
            "kind": str(row.get("kind") or row.get("status") or ""),
            "panel_n": len(members),
            "answered_n": len(answered),
            "runs_n": sum(1 for r in all_runs if str(r["session_id"]) == session_id),
            "panel_twin_ids": sorted(members),
            "answered_twin_ids": sorted(answered),
            #: Relative to the ids passed in. For the Generator that set is "every synthetic
            #: twin", so this reads as *real* twins; for Twin Lab's per-twin delete it is "every
            #: twin not selected", which is the collateral the screen must name.
            "real_twin_ids": sorted(everyone - synthetic),
            "synthetic_only": bool(everyone) and everyone <= synthetic,
        })
    return out


def _blocked_sentence(preflight: dict[str, Any]) -> str:
    """§3.4 step 3's sentence, not a traceback.

    *"3 of 50 synthetic twins cannot be deleted: they have answered runs or sit on a frozen panel.
    Deleting them would change a stored result. Delete the other 47?"*
    """
    held = preflight["blocked_twin_ids"]
    total = len(preflight["twin_ids"])
    reasons = " or ".join(
        why for table, why in BLOCKING_TWIN_REFERENCES if table in preflight["blocked"]
    )
    rest = len(preflight["deletable_twin_ids"])
    names = ", ".join(held[:5]) + (f" and {len(held) - 5} more" if len(held) > 5 else "")
    purgeable = preflight.get("purgeable_session_ids") or []
    mixed = preflight.get("mixed_session_ids") or []
    offer = ""
    if purgeable:
        offer = (
            f" {len(purgeable)} test session(s) hold them and contain nothing but synthetic "
            "twins — tick 'also delete their test sessions and results' to remove those "
            "sessions, their runs and their validity verdicts, and then those twins go."
        )
    if mixed:
        offer += (
            f" {len(mixed)} session(s) mix these twins with real drivers, and this screen never "
            "deletes a real row — so those sessions and the synthetic twins on them are left "
            "alone. Select those twins yourself in Twin Lab > Twins to clear them."
        )
    return (
        f"{len(held)} of {total} synthetic twins cannot be deleted: they {reasons} "
        f"({names}). Deleting them would change a stored result, which evidence tables do not "
        f"permit (CLAUDE.md rule 6)." + offer + " "
        + (
            f"Delete the other {rest}? Press again with 'keep the blocked twins' ticked."
            if rest
            else "Nothing can be deleted."
        )
    )


async def purge_synthetic_sessions(
    session_ids: list[str], db: DbBackend
) -> dict[str, int]:
    """Delete whole synthetic test sessions, children first. Returns what went.

    **Why a session rather than a twin's rows.** The two things blocking a synthetic delete are
    `twin_answers` (the twin answered a run) and `session_panel` (it sits on a frozen panel). Both
    hang off a session. Deleting a twin's rows out from under a session that keeps its `runs` row
    would leave a stored `index_value` computed over twins that no longer exist — a result nobody
    can audit and nobody can reproduce, which is a worse breach of rule 6 than the delete it was
    meant to avoid. Taking the whole session leaves **nothing dangling**: the panel, the runs, the
    answers and the validity verdicts go together, as one unit of evidence that is withdrawn
    rather than edited.

    This is not a relaxation of rule 6 — an append-only table is still never UPDATEd, and nothing
    here rewrites a stored number. It is a whole-unit withdrawal of **synthetic** evidence, which
    `docs/08` §6.2 says proves nothing about drivers in the first place.

    Every session reaching here is synthetic-contaminated by construction — it is in the
    pre-flight's list only because a synthetic twin sits on its panel or answered one of its runs.
    When it holds real twins too, :func:`delete_synthetic` discloses them and requires an explicit
    acknowledgement before calling this; the real driver's survey, answers, twin row and persona
    are not touched either way.
    """
    if not session_ids:
        return {}

    runs = await db.select("runs", [("in", "session_id", session_ids)])
    run_ids = sorted({str(r["run_id"]) for r in runs})

    removed: dict[str, int] = {}
    for table, column in SESSION_CASCADE_ORDER:
        keys = run_ids if column == "run_id" else session_ids
        if not keys:
            continue
        rows = await db.select(table, [("in", column, keys)])
        if rows:
            await db.delete(table, [("in", column, keys)])
            removed[table] = len(rows)
    await db.delete("sessions", [("in", "session_id", session_ids)])
    removed["sessions"] = len(session_ids)
    log.warning(
        "purged %d synthetic test session(s) and their stored results: %s",
        len(session_ids), removed,
    )
    return removed


async def twin_delete_preflight(
    twin_ids: list[str], backend: DbBackend | None = None
) -> dict[str, Any]:
    """What deleting **these** twins would cost. Pure read. Backs Twin Lab → Twins.

    The Generator's bulk delete is keyed on `data_type` and can only ever reach synthetic rows.
    This one takes an explicit selection and will delete a **real** twin if that is what the
    researcher ticked, because a researcher must be able to remove a withdrawn respondent or a
    test row of their own making. The protection is therefore not "real rows are untouchable" —
    it is that nothing goes without the selection being named and its cost shown first.

    ``collateral_twin_ids`` is the number that matters on screen: twins **not** selected that sit
    on a session this delete would have to withdraw. Deleting two twins and silently voiding a
    run that forty others answered is the surprise this field exists to prevent.
    """
    db = backend or get_backend()
    ids = sorted({str(t) for t in twin_ids if str(t)})
    if not ids:
        return {
            "twin_ids": [], "blocked": {}, "blocked_twin_ids": [],
            "dependent_sessions": [], "collateral_twin_ids": [], "free_twin_ids": [],
        }

    rows = await db.select("twins", [("in", "twin_id", ids)])
    found = sorted(str(r["twin_id"]) for r in rows)
    sources = {str(r["twin_id"]): str(r.get("source") or "") for r in rows}

    blocked: dict[str, list[str]] = {}
    for table, _why in BLOCKING_TWIN_REFERENCES:
        rows_held = await db.select(table, [("in", "twin_id", found)])
        held = sorted({str(r["twin_id"]) for r in rows_held})
        if held:
            blocked[table] = held
    held_all = sorted({t for v in blocked.values() for t in v})
    sessions = await _dependent_sessions(found, db) if held_all else []

    chosen = set(found)
    collateral = sorted(
        {
            t
            for s in sessions
            for t in s["panel_twin_ids"] + s["answered_twin_ids"]
            if t not in chosen
        }
    )
    return {
        "twin_ids": found,
        "missing_twin_ids": [t for t in ids if t not in chosen],
        "sources": sources,
        "real_twin_ids": sorted(t for t, src in sources.items() if src != SYNTHETIC_TWIN_SOURCE),
        "blocked": blocked,
        "blocked_twin_ids": held_all,
        "free_twin_ids": [t for t in found if t not in set(held_all)],
        "dependent_sessions": sessions,
        "session_ids": [s["session_id"] for s in sessions],
        "collateral_twin_ids": collateral,
    }


async def delete_twins(
    twin_ids: list[str],
    backend: DbBackend | None = None,
    *,
    purge_sessions: bool = False,
    delete_surveys: bool = True,
) -> dict[str, Any]:
    """Delete an explicit selection of twins — real or synthetic. Twin Lab → Twins.

    ``purge_sessions`` withdraws the sessions these twins are evidence in, which is the only way a
    twin that has answered a run can go: leaving the `runs` row behind would strand a stored
    `index_value` computed over twins that no longer exist (rule 6 — evidence is withdrawn whole,
    never edited). Without it, a twin that has answered a run raises :class:`DeleteBlocked` and
    **nothing is deleted**, the same refusal the Generator gives.

    ``delete_surveys`` also removes the `survey_submissions` row and its answers, which is what
    "delete this survey" means on screen. Off, the respondent's survey stays and only the twin
    built from it goes, so it can be re-imported.

    Unlike :func:`delete_synthetic` there is no `data_type` guard here, because the selection *is*
    the guard. The caller shows :func:`twin_delete_preflight` first; the screen is what makes this
    safe, so it names every collateral twin before the button is live.
    """
    db = backend or get_backend()
    pre = await twin_delete_preflight(twin_ids, db)
    going = pre["twin_ids"]
    if not going:
        return {"twins": 0, "submissions": 0, "answers": 0, "purged": {}, "blocked": []}

    if pre["blocked_twin_ids"] and not purge_sessions:
        rows = {s["session_id"]: s for s in pre["dependent_sessions"]}
        where = "; ".join(f"{rows[s]['name']} ({rows[s]['runs_n']} run(s))" for s in rows)
        extra = (
            f" Doing so also withdraws {len(pre['collateral_twin_ids'])} other twin(s)' answers "
            "from those sessions."
            if pre["collateral_twin_ids"]
            else ""
        )
        raise DeleteBlocked(
            f"Nothing was deleted. {len(pre['blocked_twin_ids'])} of the {len(going)} selected "
            f"twin(s) are evidence in: {where}. A twin cannot leave a stored result behind that "
            "was computed over it, so those sessions have to be withdrawn with it." + extra
            + " Tick 'also withdraw their sessions and results' to proceed.",
            blocked=pre["blocked"],
            deletable=len(pre["free_twin_ids"]),
        )

    purged = (
        await purge_synthetic_sessions(pre["session_ids"], db) if purge_sessions else {}
    )

    for table in CASCADING_TWIN_REFERENCES:
        await db.delete(table, [("in", "twin_id", going)])
    await db.delete("twins", [("in", "twin_id", going)])

    submissions = answers = 0
    if delete_surveys:
        # `twin_id` matches `submission_id` by convention, which is why `delete_synthetic` matches
        # on both source and id. Here the selection is explicit, so the ids are taken as given.
        rows = await db.select("survey_answers", [("in", "submission_id", going)])
        answers = len(rows)
        await db.delete("survey_answers", [("in", "submission_id", going)])
        existing = await db.select("survey_submissions", [("in", "submission_id", going)])
        submissions = len(existing)
        await db.delete("survey_submissions", [("in", "submission_id", going)])

    log.warning(
        "deleted %d twin(s) by explicit selection (%d real), %d submission(s), %d answer(s); "
        "purged %s",
        len(going), len(pre["real_twin_ids"]), submissions, answers, purged or "nothing",
    )
    return {
        "twins": len(going),
        "submissions": submissions,
        "answers": answers,
        "purged": purged,
        "real_twins": pre["real_twin_ids"],
        "collateral_twin_ids": pre["collateral_twin_ids"],
        "blocked": [],
    }


async def delete_synthetic(
    backend: DbBackend | None = None,
    *,
    skip_blocked: bool = False,
    purge_sessions: bool = False,
    allow_real_loss: bool = False,
) -> dict[str, Any]:
    """Remove every synthetic submission, its answers and its twins. **Nothing else.**

    `ARCHITECTURE_UPDATE.md` §3.4 changed two things about this function.

    **It counts blocking references first** (:func:`synthetic_delete_preflight`) rather than
    issuing the delete and letting a foreign key answer. A `23503` reaching the screen is a
    traceback where a sentence belongs, and the old retry policy printed it four times.

    **`studio_runs` is deleted with the twin.** It was simply never considered — the docstring
    below reasoned carefully about `runs` and concluded "no run is touched", which is true and was
    not the problem. `studio_runs` references `twins(twin_id)` with no cascade, so six sandbox
    rows against one synthetic twin made the whole batch undeletable. A Studio conversation about a
    twin that no longer exists is not evidence of anything, so it goes.

    ``skip_blocked`` deletes everything that is safe and leaves the rest, which is what the
    screen's second press means. Without it, a blocked twin raises :class:`DeleteBlocked` and
    **nothing at all is deleted** — a partial delete the researcher did not ask for is worse than a
    refusal.

    Three safety properties, each asserted in `tests/test_m9_intake.py`:

    * **Keyed on `data_type` alone**, so the filter cannot reach a real row. There is no branch here
      that takes an id list from a caller: a delete that accepts ids is a delete that can be given
      the wrong ones.
    * **`twins` is deleted by `source` *and* by id.** `twins` has no foreign key to
      `survey_submissions` — `twin_id` matches `submission_id` only by convention — so the DDL
      cannot cascade to it. Requiring both conditions means a real twin that happened to share an
      id cannot be caught, and a synthetic twin from a different batch cannot be missed.
    * **No run is touched.** A `runs` row references a session and a variant, never a submission, so
      deleting synthetic surveys cannot remove evidence. The test asserts the run count is
      unchanged rather than trusting that.

    `survey_answers` cascades in Postgres (`on delete cascade`); it is deleted explicitly as well
    so the behaviour is identical against the in-memory backend, which the whole test suite runs
    on.
    """
    db = backend or get_backend()

    preflight = await synthetic_delete_preflight(db)
    ids = preflight["submission_ids"]
    if not ids:
        return {"submissions": 0, "answers": 0, "twins": 0, "studio_runs": 0, "blocked": []}

    held = set(preflight["blocked_twin_ids"])
    purged: dict[str, int] = {}
    if held and purge_sessions:
        # A session holding real twins as well is **disclosed, then allowed on a second,
        # explicit acknowledgement** — not refused outright. Refusing it was a dead end: there is
        # no session delete anywhere else in the app, so a researcher whose one real driver had
        # landed on a test panel could never clear their synthetic data at all.
        #
        # What makes it allowable is structural rather than a judgement call. A session is in this
        # list only because a synthetic twin is on its panel or answered one of its runs, so its
        # index was computed over synthetic twins and `docs/08` §6.2 already says that number
        # proves nothing about drivers. There is no reportable result here to protect. And the
        # real driver keeps everything that is hard to replace — their survey, their answers,
        # their twin row and their persona all survive, because the `twins` delete below matches
        # on `source = synthetic`. What they lose is their place in a contaminated run.
        going_sessions = list(preflight["purgeable_session_ids"])
        if allow_real_loss:
            # Only ever set by the per-twin delete in Twin Lab → Twins, never by the Generator
            # screen, which does not plumb this through at all. There the researcher has ticked
            # the specific rows and been shown the real twins affected.
            going_sessions += preflight["mixed_session_ids"]
        purged = await purge_synthetic_sessions(sorted(set(going_sessions)), db)
        # Re-read: with the sessions gone, the twins that were blocked by them are now free.
        preflight = await synthetic_delete_preflight(db)
        ids = preflight["submission_ids"]
        held = set(preflight["blocked_twin_ids"])

    if held and not skip_blocked:
        raise DeleteBlocked(
            _blocked_sentence(preflight),
            blocked=preflight["blocked"],
            deletable=len(preflight["deletable_twin_ids"]),
        )

    going = list(preflight["deletable_twin_ids"])
    # A blocked twin keeps its submission and its answers too: a twin whose answers have been
    # deleted is no longer a lossless reconstruction of anything, and the persona is rebuilt from
    # those rows (I6). "Cannot be deleted" has to mean the whole record.
    keep_submissions = held
    going_submissions = [i for i in ids if i not in keep_submissions]

    answers = await db.select("survey_answers", [("in", "submission_id", going_submissions)])
    if going_submissions:
        await db.delete("survey_answers", [("in", "submission_id", going_submissions)])

    # `studio_runs` first: it references `twins(twin_id)` with no cascade, so it has to go before
    # the twin it is about, not after (§3.4 step 2).
    studio = 0
    for table in CASCADING_TWIN_REFERENCES:
        if going:
            rows = await db.select(table, [("in", "twin_id", going)])
            studio += len(rows)
            await db.delete(table, [("in", "twin_id", going)])

    # Both conditions, deliberately. See the docstring.
    if going:
        await db.delete(
            "twins", [("eq", "source", SYNTHETIC_TWIN_SOURCE), ("in", "twin_id", going)]
        )
    if going_submissions:
        await db.delete(
            "survey_submissions",
            [("eq", "data_type", SYNTHETIC_DATA_TYPE), ("in", "submission_id", going_submissions)],
        )

    log.info(
        "deleted %d synthetic submission(s), %d answer(s), %d twin(s), %d studio run(s); "
        "%d twin(s) kept because they are referenced by evidence",
        len(going_submissions), len(answers), len(going), studio, len(held),
    )
    return {
        "submissions": len(going_submissions),
        "answers": len(answers),
        "twins": len(going),
        "studio_runs": studio,
        "blocked": sorted(held),
        #: What a `purge_sessions` pass withdrew, by table, so the screen can say it out loud.
        #: Empty unless the researcher asked for it.
        "purged": purged,
    }


async def store_batch(
    batch: dict[str, Any],
    *,
    storage: Any,
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """Persist a generated batch, **raw objects first** (I16).

    The same ordering live intake uses, for the same reason: a synthetic row whose raw object is
    missing is a different kind of record from a real one, and `replay_raw.py` would report it as
    an orphan forever.
    """
    import json

    db = backend or get_backend()
    from twinlab.ingest.survey_intake import raw_object_path

    for payload in batch["payloads"]:
        result = storage.put(
            raw_object_path(payload["response_id"]), json.dumps(payload, sort_keys=True)
        )
        if hasattr(result, "__await__"):
            await result

    created = await db.insert("synthetic_batches", [batch["batch"]])
    batch_id = created[0]["batch_id"]
    submissions = [{**s, "batch_id": batch_id} for s in batch["submissions"]]

    await db.upsert("survey_submissions", submissions, on_conflict="submission_id")
    if batch["answers"]:
        await db.upsert(
            "survey_answers", batch["answers"], on_conflict="submission_id,item_id"
        )
    return {"batch_id": batch_id, "submissions": len(submissions)}
