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

#: `docs/06` §2's placeholder, in its own words, for when intake is not configured.
INTAKE_PLACEHOLDER = (
    "This area will host the real driver survey. Survey integration is pending."
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

    ref = reference()
    counts = await fieldwork_counts(backend)
    db = backend or get_backend()
    real = [
        row for row in await db.select("survey_submissions", None)
        if row.get("data_type") != SYNTHETIC_DATA_TYPE
    ]
    stamps = sorted(str(r.get("submitted_at") or "") for r in real if r.get("submitted_at"))
    today = max(stamps)[:10] if stamps else ""

    return {
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

#: Referencing tables deleted alongside the twin, in the order they must go (children first).
CASCADING_TWIN_REFERENCES: tuple[str, ...] = ("studio_runs",)


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
    return {
        "submission_ids": ids,
        "twin_ids": twin_ids,
        "blocked": blocked,
        "blocked_twin_ids": held_all,
        "deletable_twin_ids": [t for t in twin_ids if t not in set(held_all)],
    }


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
    return (
        f"{len(held)} of {total} synthetic twins cannot be deleted: they {reasons} "
        f"({names}). Deleting them would change a stored result, which evidence tables do not "
        f"permit (CLAUDE.md rule 6). "
        + (
            f"Delete the other {rest}? Press again with 'keep the blocked twins' ticked."
            if rest
            else "Nothing can be deleted."
        )
    )


async def delete_synthetic(
    backend: DbBackend | None = None, *, skip_blocked: bool = False
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
