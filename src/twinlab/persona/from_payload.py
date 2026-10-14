"""A `Twin` and its `SurveyResponse`, rebuilt from the raw object its answers landed in.

Lifted out of `services/lab.py` unchanged when the hosted survey arrived, because two callers now
need it and a second copy is how an imported twin and a hosted twin come to carry different field
shapes without anyone noticing. The two callers are:

* `services.lab.import_survey_twins` — `docs/06` §3.8's bulk import from stored submissions;
* `services.hosted_survey.submit` — one driver, the moment they press send.

**Read from Storage rather than from the row, because the row does not have it.**
`survey_submissions` carries no column for age, gender, tenure or any Part 4 answer, and none of
Part 14's own-words questions is in the frozen 73-item register, so none of it reaches
`survey_answers` either. All of it is in the raw object, and `twins.background` exists to carry it
— `docs/01` §6.2 is explicit that without Part 14 "the persona loses the driver's own words". A
twin built from the row alone has no demographics and an empty background, which is a lossless
persona (I6) in name only.

The same `build_rows` live intake uses re-derives it, over the same bytes, so a twin cannot carry
a field shape a real submission could not.

``data_type`` and ``source`` are **arguments, not inferences**. Their constants live in
`generator/` and `services/`, both above this layer, and a persona module that imported either
would invert the layer table (`ARCHITECTURE.md` §4) to save a caller one keyword.
"""

from __future__ import annotations

from typing import Any

from twinlab.ingest.reference_store import ReferenceData
from twinlab.ingest.survey_intake import build_rows
from twinlab.models.twin import WHY_PROBE_ANCHOR, Background, SurveyResponse, Twin


def twin_from_payload(
    submission: dict[str, Any],
    payload: dict[str, Any],
    ref: ReferenceData,
    *,
    data_type: str,
    source: str,
) -> tuple[Twin, SurveyResponse]:
    """The pair the persona builder consumes. Pure — no database, no Storage, no clock."""
    rows = build_rows(
        payload,
        raw_object_path=str(submission.get("raw_object_path") or ""),
        data_type=str(submission.get("data_type") or data_type),
        batch_id=submission.get("batch_id"),
        arm=submission.get("arm"),
        arm_source=submission.get("arm_source"),
        ref=ref,
    )
    extras = rows["extras"]
    fields = extras["fields"]
    background = extras["background"]

    twin = Twin(
        twin_id=submission["submission_id"],
        submission_id=submission["submission_id"],
        # `POPULATION_SOURCES` and `delete_synthetic` both key on this, so a twin built from a
        # synthetic row must say so: deleting the batch has to take its twins with it.
        source=source,
        service=_text(fields.get("service")) or submission.get("service"),
        city=_text(fields.get("city")) or submission.get("city"),
        age=_int(fields.get("age")),
        gender=_text(fields.get("gender")),
        # The instrument asks years; the twin row and the persona speak months
        # (`docs/DECISIONS.md`, 2026-09-22). One conversion, here, matching
        # `generator.synthetic.years_from_months`.
        tenure_months=_months(fields.get("tenure_years")),
        hours_per_week=_int(fields.get("hours_per_week")),
        background=Background(
            platform_count=_text(background.get("platform_count")),
            other_apps=_text(background.get("other_apps")),
            vehicle_arrangement=_text(background.get("vehicle_arrangement")),
            dependants=_int(background.get("dependants")),
            other_household_income=_text(background.get("other_household_income")),
            education=_text(background.get("education")),
            years_driving_before_uber=_float(background.get("years_driving_before_uber")),
            own_words={k: str(v) for k, v in sorted(extras["own_words"].items()) if v},
        ),
    )

    answers = {
        row["item_id"]: int(row["value_num"])
        for row in rows["answers"]
        if row.get("value_num") is not None
    }
    whys = {
        probe: str(row["why_text"])
        for row in rows["answers"]
        if row.get("why_text")
        for probe, anchor in WHY_PROBE_ANCHOR.items()
        if anchor == row["item_id"]
    }
    response = SurveyResponse(
        twin_id=twin.twin_id,
        answers=answers,
        whys=whys,
        own_words=dict(twin.background.own_words),
    )
    return twin, response


def _text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _int(value: Any) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _months(years: Any) -> int | None:
    value = _float(years)
    return None if value is None else round(value * 12)


__all__ = ["twin_from_payload"]
