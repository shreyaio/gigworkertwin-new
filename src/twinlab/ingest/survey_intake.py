"""Survey intake — the Python reference implementation. `docs/04` §8. Serves I16.

**One contract, two implementations.** This module and the Supabase Edge Function
(`supabase/functions/survey_intake/`) share `config/form_map.yaml` and one fixture
(`apps_script/sample_payload.json`), and a contract test asserts both produce identical rows from
it so they cannot drift.

Intake lives in the Edge Function in production, not the Space: a Space sleeping after 48 hours
idle would silently drop driver submissions (`ARCHITECTURE.md` §6.2). This module exists because
the contract needs a second implementation to be testable, and because `replay_raw.py` re-drives
stored objects from inside the Space.

The order of steps is the invariant, not a style:

1. Verify the HMAC over the **raw body** with `hmac.compare_digest`. Bad signature → 401. 2. Write
the raw payload to Storage. **A failure here aborts before any table write** (I16). 3. Map
``"<section>|<title>"`` → `item_id`. **An unmapped question is a 422, never a dropped
   answer.**
4. Insert `survey_submissions` + `survey_answers`.

Step 2 precedes step 4 so that a failed insert leaves a replayable object. Reverse them and a
submission that failed to store is gone: the driver filled the form and there is no record.

**Persona building is deliberately not done here.** It is pure Python and cheap, but doing it in an
Edge Function would duplicate the template library outside the repo — drift risk with no benefit.
Intake stores; the Space imports.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from functools import lru_cache
from typing import Any

import yaml

from config.settings import CONFIG_DIR
from twinlab.ingest.reference_store import ReferenceData, reference

#: The header the Apps Script sends. Hex HMAC-SHA256 over the exact UTF-8 bytes of the body.
SIGNATURE_HEADER = "X-Signature"

#: Consent statements 1-6 are "consented". **Statement 7 is `consent:twin`** and gates the twin,
#: not the record (`docs/04` §8).
CONSENT_STATEMENTS = tuple(f"statement_{n}" for n in range(1, 7))
CONSENT_TWIN_KEY = "twin"

#: Values the Form's Yes/No and checkbox questions send for agreement.
AFFIRMATIVE = frozenset({"yes", "i agree", "true", "agree", "yes, i agree to take part"})


class IntakeError(Exception):
    """Base class. Every subclass carries the HTTP status the Edge Function must return."""

    status = 400


class BadSignature(IntakeError):
    """401. The body was not signed by the holder of `INTAKE_HMAC_SECRET`."""

    status = 401


class UnmappedQuestion(IntakeError):
    """422. A Form question absent from `form_map.yaml`.

    **Never a dropped answer** (`CLAUDE.md` rule 7). A Form edited without updating the map fails
    loudly on the first submission, when it is cheap to fix — rather than silently losing one item
    from every response until someone notices a construct is short.
    """

    status = 422


class StorageFailed(IntakeError):
    """500. The raw object could not be stored, so **nothing is written to a table** (I16)."""

    status = 500


@lru_cache(maxsize=1)
def form_map() -> dict[str, str]:
    """`config/form_map.yaml`'s `map` block: ``"SECTION|TITLE"`` → target."""
    raw = yaml.safe_load((CONFIG_DIR / "form_map.yaml").read_text(encoding="utf-8"))
    return dict(raw["map"])


@lru_cache(maxsize=1)
def form_map_version() -> str:
    raw = yaml.safe_load((CONFIG_DIR / "form_map.yaml").read_text(encoding="utf-8"))
    return str(raw["version"])


# --------------------------------------------------------------------------- step 1


def sign(body: bytes | str, secret: str) -> str:
    """The hex HMAC-SHA256 the Apps Script computes. `apps_script/intake.gs` → `hmacHex`."""
    payload = body.encode("utf-8") if isinstance(body, str) else body
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_signature(body: bytes | str, signature: str | None, secret: str) -> None:
    """Constant-time comparison over the **raw body**. Raises :class:`BadSignature`.

    `hmac.compare_digest`, not `==`: a timing-variable comparison leaks the expected digest one
    byte at a time to anyone who can post repeatedly, and this endpoint is public by necessity.

    The signature is checked over the bytes as received, never over a re-serialised object — a
    round-trip through `json.loads`/`json.dumps` can reorder keys and change whitespace, and the
    signature would then never match.
    """
    if not secret:
        raise BadSignature(
            "no INTAKE_HMAC_SECRET is configured, so no signature can be verified. Intake refuses "
            "rather than accepting unsigned submissions."
        )
    if not signature:
        raise BadSignature("missing X-Signature header")
    if not hmac.compare_digest(sign(body, secret), signature.strip().lower()):
        raise BadSignature("signature does not match the body")


# --------------------------------------------------------------------------- step 3


def _key(answer: dict) -> str:
    return f"{answer.get('section', '')}|{answer.get('title', '')}"


def map_answers(payload: dict) -> dict[str, list[tuple[str, Any]]]:
    """Group the payload's answers by target prefix. Raises :class:`UnmappedQuestion`.

    Returns ``prefix → [(target, value), ...]`` where an item id has the prefix ``"item"``. The
    grouping is what lets the caller build each destination — a `survey_answers` row, a `twins`
    column, a `background` key — without re-walking the payload and without a chain of `if`s that
    could silently fall through.
    """
    mapping = form_map()
    grouped: dict[str, list[tuple[str, Any]]] = {}
    unmapped: list[str] = []

    for answer in payload.get("answers", []):
        key = _key(answer)
        target = mapping.get(key)
        if target is None:
            unmapped.append(key)
            continue
        prefix, _, name = target.partition(":")
        if not name:
            prefix, name = "item", target
        grouped.setdefault(prefix, []).append((name, answer.get("value")))

    if unmapped:
        raise UnmappedQuestion(
            f"{len(unmapped)} Form question(s) are not in form_map.yaml (version "
            f"{form_map_version()}): {unmapped[:5]}. Nothing is dropped — add them to the map "
            "(CLAUDE.md rule 7)."
        )
    return grouped


def _affirmative(value: Any) -> bool:
    """Whether a Yes/No or checkbox answer means yes.

    **A Google Forms checkbox answers as a list**, so consent statement 6 arrives as
    ``["I agree"]``, not ``"I agree"``. An earlier version of this function stringified the value
    and compared `"['i agree']"` against the allow-list, so every consent read as **false** and
    every submission became `no_consent` — the whole study, silently, with no error anywhere.
    `apps_script/sample_payload.json` is what caught it, which is the reason the fixture is
    committed.
    """
    if isinstance(value, (list, tuple)):
        return any(_affirmative(v) for v in value)
    return str(value).strip().lower() in AFFIRMATIVE


def _as_int(value: Any) -> int | None:
    """A Likert answer as an integer, or ``None``. **Never coerced** (`docs/02` §5.3).

    Forms send the number as a label, sometimes with the anchor text attached (``"6 — I agree"``),
    so the leading integer is read. A value with no leading integer returns ``None`` and becomes a
    `value_text` rather than an invented number.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)):
        # A checkbox grid is never a Likert item. One selected option reads as its own value; more
        # than one has no single number and must not be collapsed into the first.
        return _as_int(value[0]) if len(value) == 1 else None
    match = re.match(r"\s*(-?\d+)", str(value))
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------- step 4


def build_rows(
    payload: dict,
    *,
    raw_object_path: str,
    data_type: str = "REAL",
    batch_id: str | None = None,
    arm: str | None = None,
    arm_source: str | None = None,
    ref: ReferenceData | None = None,
) -> dict[str, Any]:
    """Payload → the `survey_submissions` row and its `survey_answers` rows.

    **Pure.** No I/O, no clock, no randomness — which is what makes it comparable byte-for-byte with
    the Edge Function's TypeScript over the same fixture.

    `eligible` is **computed and recorded but never used to exclude.** `docs/GOOGLE_FORM.md` §
    "Three things the specification did not fix" is explicit: the Part 1 screeners are mapped so
    they are accepted, but nothing infers from them, and making eligibility exclude a response is
    a research decision the researcher has not made. So `outcome` is never `screened_out` here —
    that value stays available for a screening rule the researcher may later choose. See
    `docs/DECISIONS.md`.
    """
    ref = ref or reference()
    grouped = map_answers(payload)

    consents = dict(grouped.get("consent", []))
    fields = dict(grouped.get("field", []))
    background = dict(grouped.get("background", []))
    meta = dict(grouped.get("meta", []))
    screens = dict(grouped.get("screen", []))
    checks = dict(grouped.get("check", []))
    whys = dict(grouped.get("why", []))
    own_words = dict(grouped.get("own_words", []))
    items = grouped.get("item", [])

    consented = all(_affirmative(consents.get(s)) for s in CONSENT_STATEMENTS)
    consent_twin = _affirmative(consents.get(CONSENT_TWIN_KEY))

    # Recorded, never applied. See the docstring.
    eligible = (
        all(_affirmative(screens.get(k)) for k in
            ("age_18_plus", "tenure_3_months", "active_30_days",
             "reads_survey_language", "in_india"))
        and not any(_affirmative(screens.get(k)) for k in
                    ("uber_employee", "earlier_stage", "deactivated"))
    )

    answers_by_item: dict[str, dict[str, Any]] = {}
    for item_id, value in items:
        if item_id not in ref.items:
            raise UnmappedQuestion(
                f"form_map.yaml points at {item_id!r}, which is not in the frozen item register"
            )
        number = _as_int(value)
        answers_by_item[item_id] = {
            "submission_id": payload["response_id"],
            "item_id": item_id,
            "value_num": number,
            "value_text": None if number is not None else _text_or_none(value),
            "why_text": None,
            "language": meta.get("language"),
            "legacy_scale": False,
        }

    # A why-probe is stored as `why_text` on its anchor item, verbatim and never paraphrased.
    from twinlab.models.twin import WHY_PROBE_ANCHOR

    for probe_id, text in whys.items():
        anchor = WHY_PROBE_ANCHOR.get(probe_id)
        if anchor is None:
            raise UnmappedQuestion(
                f"why-probe {probe_id!r} has no anchor item in WHY_PROBE_ANCHOR; it would be lost"
            )
        if anchor in answers_by_item:
            answers_by_item[anchor]["why_text"] = _text_or_none(text)

    attention_passed = all(
        answers_by_item.get(item_id, {}).get("value_num") == expected
        for item_id, expected in _attention_expectations(ref).items()
    )

    battery_present = [
        i for i in ref.battery_item_ids
        if answers_by_item.get(i, {}).get("value_num") is not None
    ]
    complete = len(battery_present) == len(ref.battery_item_ids)

    outcome = "complete" if (consented and complete) else (
        "no_consent" if not consented else "partial"
    )

    submission = {
        "submission_id": payload["response_id"],
        "data_type": data_type,
        "batch_id": batch_id,
        "eligible": eligible,
        "consented": consented,
        "consent_twin": consent_twin,
        "attention_passed": attention_passed,
        "completion_seconds": payload.get("completion_seconds"),
        "straight_liner": _straight_lining(answers_by_item, ref),
        "outcome": outcome,
        "arm": arm,
        "arm_source": arm_source,
        "mc_answer": _text_or_none(checks.get("manipulation")),
        "city": _text_or_none(fields.get("city")),
        "service": _text_or_none(fields.get("service")),
        "language": meta.get("language"),
        "raw_object_path": raw_object_path,
        "started_at": payload.get("started_at"),
        "submitted_at": payload["submitted_at"],
    }

    return {
        "submission": submission,
        "answers": [answers_by_item[i] for i in sorted(answers_by_item)],
        # Not database columns. Carried so the Space can build a twin without re-reading the raw
        # object, and so the mirror keeps everything the driver sent (losslessness).
        "extras": {
            "fields": fields,
            "background": background,
            "own_words": own_words,
            "screens": screens,
            "checks": checks,
            "form_map_version": form_map_version(),
        },
    }


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _attention_expectations(ref: ReferenceData) -> dict[str, int]:
    """The value each attention check asks for, read from **its own stem**. I10.

    Parsed from the stem rather than hard-coded, so re-wording the Form cannot leave the checker
    scoring against a number the driver was never asked for.
    """
    from twinlab.models.reference import ATTENTION_ITEMS

    out: dict[str, int] = {}
    for item_id in ATTENTION_ITEMS:
        match = re.search(r"select\s+(\d+)", ref.items[item_id].stem, re.I)
        if match is None:
            raise IntakeError(
                f"{item_id} is an attention check but its stem names no value to select"
            )
        out[item_id] = int(match.group(1))
    return out


def _straight_lining(answers: dict[str, dict], ref: ReferenceData) -> bool:
    """One value across every battery item. A data-quality flag, recorded, never a gate here."""
    values = [
        answers[i]["value_num"] for i in ref.battery_item_ids
        if i in answers and answers[i]["value_num"] is not None
    ]
    return len(values) > 1 and len(set(values)) == 1


# --------------------------------------------------------------------------- the whole thing


async def intake(
    body: bytes | str,
    signature: str | None,
    *,
    secret: str,
    storage: Any,
    backend: Any,
    ref: ReferenceData | None = None,
) -> dict[str, Any]:
    """The four steps, in order. `docs/04` §8.

    ``storage.put(path, body)`` writes the raw object; ``backend`` inserts the rows. Both are
    injected so the order can be tested by making the insert fail and asserting the object
    survives (I16, and `docs/11` M9's "a forced insert failure leaves a replayable object").
    """
    verify_signature(body, signature, secret)

    text = body.decode("utf-8") if isinstance(body, bytes) else body
    payload = json.loads(text)
    if "response_id" not in payload or "submitted_at" not in payload:
        raise IntakeError("payload needs response_id and submitted_at")

    path = raw_object_path(payload["response_id"])
    try:
        # Step 2, BEFORE any table write. A failure here aborts (I16).
        result = storage.put(path, text)
        if hasattr(result, "__await__"):
            await result
    except IntakeError:
        raise
    except Exception as exc:
        raise StorageFailed(
            f"could not write {path}: {exc}. Nothing was written to a table, so the submission is "
            "not half-recorded — but it is also not recorded, and the driver's answers are lost. "
            "This is the one failure intake cannot make safe."
        ) from exc

    rows = build_rows(payload, raw_object_path=path, ref=ref)
    await backend.upsert("survey_submissions", [rows["submission"]], on_conflict="submission_id")
    if rows["answers"]:
        await backend.upsert(
            "survey_answers", rows["answers"], on_conflict="submission_id,item_id"
        )

    return {
        "status": "ok",
        "submission_id": rows["submission"]["submission_id"],
        "consent_twin": rows["submission"]["consent_twin"],
    }


def raw_object_path(response_id: str) -> str:
    """`raw/survey_<id>.json`. `docs/04` §8, and what `replay_raw.py` scans."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", response_id)
    return f"raw/survey_{safe}.json"
