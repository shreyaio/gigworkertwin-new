"""One hosted submission, as the payload `ingest.survey_intake` already knows how to read.

**This module is the whole reason the hosted page is not a second pipeline.** The Apps Script
posts ``{response_id, submitted_at, answers: [{section, title, value}, ...]}`` and
`build_rows` turns that into a `survey_submissions` row and its `survey_answers`. This builds the
*same object* from the same 112 keys, so from `build_rows` onward a hosted submission and a Google
Form submission are indistinguishable — one mapping, one row shape, one persona builder, one set of
tests.

**Every question is emitted, answered or not.** A skipped question travels as an explicit ``null``
rather than being left out, because the raw object in Storage is the immutable record of what the
driver was asked (`docs/04` §8) and "asked and declined" is different evidence from "never asked".
The cover sheet promises a driver may skip anything; a mirror that cannot tell a skip from an
omission cannot show that promise was kept.

Nothing here coerces. A Likert answer arrives as an ``int`` because the control only produces
ints; a blank arrives as ``None``. There is no path that turns a missing answer into a number
(`CLAUDE.md`, "Never coerce a bad answer into a good one").
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from twinlab.models.survey import HostedInstrument, Question, SurveyProgress
from twinlab.survey.instrument import hosted_instrument

#: Prefix on every hosted `response_id`, so a submission's origin is legible in the raw bucket and
#: in `survey_submissions` without joining anything. The Apps Script's ids look like
#: ``2_ABaOnud…``; these cannot collide with them.
HOSTED_PREFIX = "web"


def new_response_id() -> str:
    """A fresh submission id. Also the reference number the driver is told to keep.

    One identifier, not two: the cover sheet promises a number that can be quoted to withdraw
    within 14 days, and a reference that does not resolve to a row is not a withdrawal route.
    """
    return f"{HOSTED_PREFIX}_{uuid.uuid4().hex}"


def now_iso() -> str:
    """UTC, to the second, with a ``Z`` — the shape `survey_submissions.submitted_at` expects."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def new_progress() -> SurveyProgress:
    """A driver's blank questionnaire, stamped with the moment they opened it."""
    return SurveyProgress(response_id=new_response_id(), started_at=now_iso())


def _value(question: Question, raw: Any) -> Any:
    """One answer, in the shape the Form would have sent it. Never invented, never widened.

    The only transformations are the ones `CLAUDE.md` lists as syntax: trimming whitespace, and
    reading an empty string as "not answered". A blank numeric box is ``None`` — not zero, which
    is a real answer to "how many people depend on your earnings".
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        # Numeric questions arrive here as text, because the page draws them as text boxes (see
        # `ui/pages/survey_take.py`). They are **left as text**, which is exactly what the Google
        # Form sent: `build_rows._as_int` reads the leading integer for a scored item, and
        # `persona.from_payload` parses `field:age` and the Part 4 counts. Converting here would
        # make the hosted raw object a different artefact from the Form's over the same answers.
        text = raw.strip()
        return text or None
    if isinstance(raw, bool):
        # Only a consent tick-box produces a bool. An unticked box is not "No", it is no answer:
        # `build_rows` reads consent as "did they affirm", and a false there would be identical.
        return "I agree" if raw else None
    if question.kind == "likert" and isinstance(raw, float) and raw.is_integer():
        # A radio can hand back 5.0 for 5. Exactly-integral is syntax, so it converts; 5.5 is
        # meaning, and falls through to be recorded as it arrived.
        return int(raw)
    return raw


def build_payload(
    progress: SurveyProgress,
    *,
    submitted_at: str | None = None,
    instrument: HostedInstrument | None = None,
) -> dict[str, Any]:
    """``SurveyProgress`` → the Form-shaped payload. **Pure**: no clock unless none is given.

    The answers are emitted in instrument order so two drivers who answered identically produce
    byte-identical raw objects, which is what makes the stored mirror diffable and the end-to-end
    test exact.
    """
    inst = instrument or hosted_instrument()
    sent = submitted_at or now_iso()
    answers = [
        {
            "section": question.section,
            "title": question.title,
            "value": _value(question, progress.answers.get(question.key)),
        }
        for question in inst.questions
    ]
    payload: dict[str, Any] = {
        "response_id": progress.response_id,
        "started_at": progress.started_at,
        "submitted_at": sent,
        "answers": answers,
    }
    seconds = _elapsed_seconds(progress.started_at, sent)
    if seconds is not None:
        # `survey_submissions.speeder` is generated from this column, so a missing duration must
        # stay missing rather than become a zero that reads as an instant completion.
        payload["completion_seconds"] = seconds
    # Provenance, carried on the mirror only. `build_rows` ignores unknown top-level keys, so this
    # cannot reach a column — it is there for whoever reads the raw object later.
    payload["source"] = {
        "channel": "hosted",
        "instrument_version": inst.instrument_version,
        "form_map_version": inst.form_map_version,
    }
    return payload


def _elapsed_seconds(started_at: str, submitted_at: str) -> int | None:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    seconds = int((end - start).total_seconds())
    return seconds if seconds >= 0 else None


__all__ = ["HOSTED_PREFIX", "build_payload", "new_progress", "new_response_id", "now_iso"]
