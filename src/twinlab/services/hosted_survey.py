"""Receiving one driver's questionnaire from the hosted page. `docs/06` §2.1.

**The same four steps as `ingest.survey_intake.intake`, in the same order, for the same reasons**
— minus step 1, because there is no HTTP body to authenticate: the answers came from a Gradio
session in this process, not from a signed POST.

1. Build the Form-shaped payload (`survey.payload`).
2. **Write the raw object to Storage.** A failure here aborts before any table write (I16).
3. Map ``"<section>|<title>"`` → `item_id` and build the rows (`ingest.survey_intake.build_rows`).
4. Insert `survey_submissions` + `survey_answers`, then build the twin.

Step 2 precedes step 4 so that a failed insert leaves a replayable object. Reverse them and a
submission that failed to store is gone: the driver filled the questionnaire and there is no
record.

**This module writes no row shape of its own.** Everything a hosted submission becomes is produced
by `build_rows` and `persona.from_payload.twin_from_payload`, which are the same functions the
Google Form path and the synthetic generator use. The hosted page is a third client of one
contract, not a third pipeline.

**A note on where this runs.** `ARCHITECTURE.md` §8.2 rule 2 puts intake in the Supabase Edge
Function and not in the Space, because a free Space sleeping after 48 hours idle would silently
drop a driver's submission. Hosting the questionnaire in the Space was asked for deliberately
(`docs/DECISIONS.md`, 2026-10-08) and that trade is real and unmitigated by this module: a request
that never arrives cannot be stored by code that is asleep. What this module does guarantee is
that a submission which *does* arrive is written in the order that makes it recoverable.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any

from twinlab.db.client import DbBackend, StorageBackend, get_backend, get_storage
from twinlab.ingest.reference_store import reference
from twinlab.ingest.survey_intake import StorageFailed, build_rows, raw_object_path
from twinlab.models.survey import SubmissionReceipt, SurveyProgress
from twinlab.models.validity import assert_not_ablated
from twinlab.persona.builder import build_persona
from twinlab.persona.from_payload import twin_from_payload
from twinlab.services.generator import REAL_DATA_TYPE
from twinlab.survey.payload import build_payload

log = logging.getLogger(__name__)


class AlreadySubmitted(RuntimeError):
    """This questionnaire has already been sent.

    Raised rather than writing again. `survey_submissions.submission_id` is the primary key, so a
    second send would upsert over the first — and the two could differ, because the page stays
    open and editable after the send. One driver's record must be the one they pressed send on.
    """


#: `survey_submissions.arm_source` for an arm this application drew. The column exists so that how
#: an arm was assigned is answerable later; "it was balanced within the stratum" and "the Form
#: builder fixed it" are different provenances and must not look alike.
ARM_SOURCE = "hosted_balanced"


async def assign_arm(
    city: str | None,
    service: str | None,
    *,
    backend: DbBackend | None = None,
) -> tuple[str, str]:
    """Draw this respondent's arm, balanced **within their `city|service` stratum**. `docs/01` §5.2.

    Balance is within stratum and never overall, which is what makes H2 validation comparable
    across strata — the same rule the Driver survey page's balance table reports against.

    The draw takes the arm with the fewest respondents already in this stratum, breaking a tie at
    random so the assignment is not predictable from the one before it. Only **real** submissions
    are counted: a synthetic batch carries its own arms and counting them would let generated data
    steer which story a driver reads.

    **Approximate under concurrency, by design.** Counts come from committed rows, so two drivers
    answering at the same moment can draw the same arm. Reserving an arm at the first page view
    would be exact and would also leak arms to everyone who opened the link and left, which
    biases the balance far more than a rare collision. Fieldwork balance is checked on the
    Driver survey page, which is where a drift would show.
    """
    from twinlab.ingest.reference_store import reference

    db = backend or get_backend()
    arms = sorted(reference().arms)
    stratum_city = city or "unknown"
    stratum_service = service or "unknown"

    rows = await db.select("survey_submissions", [("eq", "data_type", REAL_DATA_TYPE)])
    counts = {arm: 0 for arm in arms}
    for row in rows:
        arm = row.get("arm")
        if arm in counts and (row.get("city") or "unknown") == stratum_city \
                and (row.get("service") or "unknown") == stratum_service:
            counts[arm] += 1

    fewest = min(counts.values())
    return random.choice([a for a in arms if counts[a] == fewest]), ARM_SOURCE


def twin_gate(submission: dict[str, Any]) -> str | None:
    """Why this respondent cannot become a twin, or ``None`` if they can. `docs/06` §3.8.

    **One rule, used in three places**: the hosted survey's immediate build, the Generator's bulk
    import, and the live count on the Settings tab. It used to be expressed as a database filter
    in :func:`~twinlab.services.lab.importable_submissions` only, which meant the hosted path
    would have had to restate it — and a second copy of a consent gate is exactly the kind of
    drift that ends with a twin built from a driver who refused one.

    The returned string is shown to the researcher verbatim, so it says which gate and why.
    """
    if not submission.get("consented"):
        return "the respondent did not agree to all seven consent statements"
    if not submission.get("consent_twin"):
        # Statement 7 is its own gate: a driver may consent to the research and decline the twin.
        return "consent statement 7 was withheld, so no computer model may be built (docs/01 §6.2)"
    if not submission.get("eligible"):
        return "the Part 1 screeners place this respondent outside the eligible population"
    if submission.get("outcome") != "complete":
        return (
            f"the submission is {submission.get('outcome')!r}, not 'complete' — a persona must be "
            "lossless over all 37 battery items (I6) and cannot be built from a partial row"
        )
    return None


async def submit(
    progress: SurveyProgress,
    *,
    backend: DbBackend | None = None,
    storage: StorageBackend | None = None,
    build_twin: bool = True,
) -> SubmissionReceipt:
    """Store one driver's questionnaire and, when the gates allow it, build their twin.

    ``build_twin=False`` stores the record and stops, which is what a researcher wants when
    importing in bulk later through `docs/06` §3.8. It never changes what is stored.
    """
    if progress.submitted:
        raise AlreadySubmitted(
            f"{progress.response_id} was already sent. Its record is the one the driver pressed "
            "send on; sending again would overwrite it with whatever the page holds now."
        )

    db = backend or get_backend()
    store = storage or get_storage()
    ref = reference()

    payload = build_payload(progress)
    path = raw_object_path(payload["response_id"])

    # Step 2, BEFORE any table write (I16). The body is the exact bytes the row will point at.
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
    try:
        result = store.put(path, body)
        if hasattr(result, "__await__"):
            await result
    except Exception as exc:
        raise StorageFailed(
            f"could not write {path}: {exc}. Nothing was written to a table, so the submission is "
            "not half-recorded — but it is also not recorded, and the driver's answers are lost. "
            "This is the one failure intake cannot make safe."
        ) from exc

    rows = build_rows(
        payload,
        raw_object_path=path,
        data_type=REAL_DATA_TYPE,
        # The arm the driver was actually shown. Drawn during the questionnaire, not here: the
        # story they read depends on it, so it has to exist before Part 15 is rendered.
        arm=progress.arm,
        arm_source=progress.arm_source,
        ref=ref,
    )
    submission = rows["submission"]
    await db.upsert("survey_submissions", [submission], on_conflict="submission_id")
    if rows["answers"]:
        await db.upsert(
            "survey_answers", rows["answers"], on_conflict="submission_id,item_id"
        )

    answered = sum(
        1 for r in rows["answers"]
        if r["item_id"] in ref.battery_item_ids and r.get("value_num") is not None
    )
    receipt: dict[str, Any] = {
        "reference": submission["submission_id"],
        "raw_object_path": path,
        "outcome": submission["outcome"],
        "consented": submission["consented"],
        "consent_twin": submission["consent_twin"],
        "eligible": submission["eligible"],
        "attention_passed": submission["attention_passed"],
        "battery_answered": answered,
        "battery_expected": len(ref.battery_item_ids),
    }

    if not build_twin:
        return SubmissionReceipt(
            **receipt, twin_note="Stored. The twin is built by the Generator's import."
        )

    blocked = twin_gate(submission)
    if blocked is not None:
        # Not an error: a respondent who is recorded but does not become a twin is a normal and
        # expected outcome, and `survey_submissions` exists to hold exactly those people.
        return SubmissionReceipt(**receipt, twin_note=f"No twin: {blocked}.")

    try:
        twin, response = twin_from_payload(
            submission, payload, ref, data_type=REAL_DATA_TYPE, source="real"
        )
        passage = build_persona(twin, response, ref)
        # At the write, not in a handler: an ablated persona is missing its fairness clauses by
        # design (test 6, I6) and a twin hashed from one is indistinguishable downstream from a
        # twin whose driver never answered those items.
        assert_not_ablated(passage)
        await db.insert("twins", [{
            "twin_id": twin.twin_id,
            "submission_id": twin.submission_id,
            "source": twin.source,
            "service": twin.service,
            "city": twin.city,
            "age": twin.age,
            "gender": twin.gender,
            "tenure_months": twin.tenure_months,
            "hours_per_week": twin.hours_per_week,
            "background": twin.background.model_dump(mode="json"),
            "persona_passage": passage.text,
            "persona_hash": passage.persona_hash,
            "persona_template_version": passage.template_version,
        }])
    except Exception as exc:  # noqa: BLE001 — the record is safe; say why the twin is not there.
        log.warning("hosted twin build failed for %s: %s", submission["submission_id"], exc)
        return SubmissionReceipt(
            **receipt,
            twin_note=(
                f"The answers are stored, but no twin was built: {type(exc).__name__}: "
                f"{str(exc)[:200]}. The record is replayable from {path}."
            ),
        )

    return SubmissionReceipt(
        **receipt,
        twin_id=twin.twin_id,
        persona_hash=passage.persona_hash,
        twin_note=(
            f"Twin built from {passage.clause_count} clauses over "
            f"{len(passage.items_used)} items."
        ),
    )


async def payload_json(
    submission_id: str, *, storage: StorageBackend | None = None
) -> str:
    """The stored raw object for one submission, as it was written.

    Read back from Storage rather than rebuilt, because the point of the mirror is that it is what
    actually arrived — a reconstruction would be a different artefact that happened to agree.
    """
    store = storage or get_storage()
    return await store.get(raw_object_path(submission_id))


__all__ = [
    "ARM_SOURCE",
    "AlreadySubmitted",
    "assign_arm",
    "payload_json",
    "submit",
    "twin_gate",
]
