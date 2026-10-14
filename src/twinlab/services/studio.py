"""Twin Studio — one twin, any version. `docs/06` §5, `docs/01` §6.9 **as amended**.

This module exists to let a researcher interrogate one twin in their own words. Until 2026-10-01 it
was quarantined outright: `docs/01` §6.9 said studio runs never appear in `runs`, never contribute
to a metric, a shift, an index or the Results grid, and never enter Statistics.

**The researcher has reversed that for the dialled-version path** (`ARCHITECTURE_UPDATE.md` §1.1,
*"by overwrite, it's ok for the studio values to feed analyses"*). So the wall is no longer where it
was, and where it now runs is the most important thing in this file:

* **A dialled version is filed as evidence.** :func:`file_studio_run` appends a `sessions` row, a
  `runs` row with ``origin='studio'`` and ``twins_n=1``, and one `twin_answers` row. Nothing is
  updated in place, so `CLAUDE.md` rule 6 holds; and `services/results.completed_runs` already
  takes the latest run per `version_code` by `started_at`, so a later Dial board run supersedes the
  Studio value automatically. That is the requested precedence with no precedence logic to get
  wrong.
* **What that costs is in the data, not in a reader's head.** A Studio-origin index is computed over
  **one twin**, while `00000` and `SHAM` — the noise floor a lever effect must clear — come from the
  frozen panel. `origin` and `twins_n` therefore travel with every number this produces.
* **A custom free-text change is still fully quarantined, and is the one path that is.** It
  bypasses the lookup (I1) and the Checker (I3) by construction, is not one of the 243, has no
  version code to be latest for, carries :data:`SANDBOX_LABEL` and **never reaches**
  :func:`file_studio_run`. A number produced under a custom change is not a measurement of anything
  in the design.
* **A hand-built twin** is stored ``source='manual'``, and `orchestrator.panel.POPULATION_SOURCES`
  contains no ``manual`` entry — so it cannot be drawn into a panel by any population setting, not
  even ``both`` (`docs/03` §9.3).
* **A Studio run writes no `session_panel` row** and is never inheritable by a rerun. I14 is about
  frozen panels and a Studio ask has none.

I3 keeps no sandbox exemption. A version with no stored, Checker-passed variant is still refused —
what changed is that :func:`start_render` now lets the Studio *produce* one, through the same
`render_and_check` the sweep uses, instead of leaving the screen a dead end (§4.2).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from config.settings import settings
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import VariantRepo
from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
from twinlab.models.twin import Background, SurveyResponse, Twin
from twinlab.models.validity import assert_not_ablated
from twinlab.models.variant import DIAL_ZERO_TEXT
from twinlab.models.view import TwinRow
from twinlab.persona.builder import build_persona

log = logging.getLogger(__name__)

#: The label a custom free-text change must carry (`docs/06` §5).
#:
#: It bypasses `variant.lookup` and `variant.checker`, so nothing guarantees it differs from a
#: neighbouring cell, stays inside its threshold, or says anything Uber could have said. Its
#: output is a conversation, not a measurement.
SANDBOX_LABEL = "sandbox — not a study result"

#: `twins.source` for a hand-built twin. Never in `POPULATION_SOURCES`, therefore never on a panel.
MANUAL_SOURCE = "manual"

#: The Studio's three ways of getting a twin, in `docs/06` §5's order.
TWIN_MODES: tuple[tuple[str, str], ...] = (
    ("existing", "Use a twin I have"),
    ("survey", "From a survey answer"),
    ("manual", "Make one by hand"),
)

#: `docs/06` §5's hand-built fields: nine 1-7 sliders, one per construct.
MANUAL_SLIDERS: tuple[tuple[str, str], ...] = (
    ("EXPO", "Managed by the app"),
    ("CTRL", "Feels controlled"),
    ("FAIR", "Feels treated fairly"),
    ("TRAN", "Finds the app clear"),
    ("SATI", "Happy with the job"),
    ("LOYA", "Wants to stay"),
    ("VOIC", "Pushes back"),
    ("EXIT", "Wants to leave"),
    ("EDEP", "Needs the money"),
)

#: `docs/06` §5: at most five free-text questions per studio run.
MAX_QUESTIONS = 5


class StudioError(RuntimeError):
    """Any refusal by the Studio."""


# ------------------------------------------------------------------ selectors


async def studio_twins(backend: DbBackend | None = None) -> list[TwinRow]:
    """Mode 1 — every twin, **including ones the quality gate dropped**. `docs/06` §5.

    Non-passed twins may be inspected here; they can never enter the main study. That asymmetry is
    the point of the Studio, so this deliberately does not filter on quality the way
    `orchestrator.panel.eligible_candidates` does.
    """
    from twinlab.services.lab import twin_rows

    return await twin_rows(backend=backend)


async def studio_selectors(backend: DbBackend | None = None) -> dict[str, Any]:
    """Everything card 1's twin picker needs, in one round trip. `docs/06` §5.

    The prototype puts a count under the picker — *"34 twins in the sheet. 0 survey answers not
    yet made into twins."* — and that line is content, not decoration: an empty dropdown with no
    count reads as a broken screen, and the two numbers say which of the two reasons it is.

    The labels carry the identity line rather than a bare id, because a twin id is opaque by
    design (`CLAUDE.md` rule 8) and a researcher choosing one needs to know who it is.
    """
    twins = await studio_twins(backend)
    candidates = await survey_candidates(backend)
    labels: list[str] = []
    for twin in twins:
        who = " — ".join(
            part for part in (
                ", ".join(p for p in (twin.service, twin.city) if p),
                twin.quality_text,
            ) if part
        )
        labels.append(f"{twin.twin_id} — {who}" if who else twin.twin_id)
    return {
        "twin_labels": labels,
        "survey_labels": [c["label"] for c in candidates],
        "line": (
            f"{len(twins):,} {'twin' if len(twins) == 1 else 'twins'} available. "
            f"{len(candidates):,} survey "
            f"{'answer' if len(candidates) == 1 else 'answers'} not yet made into twins."
        ),
    }


def twin_id_of(label: str | None) -> str:
    """The twin id out of a picker label. The label is ``id — who``; the id is opaque.

    Split on the first separator only: an identity line may itself contain an em dash, and
    splitting on the last one would return a fragment of the description as an id.
    """
    return (label or "").split(" — ", 1)[0].strip()


async def studio_persona(
    twin_id: str, backend: DbBackend | None = None
) -> str:
    """The persona a twin is given about itself. `docs/06` §5's *Show what the twin is told*.

    Read from the stored `twins.persona_passage` rather than rebuilt: the passage that is shown
    must be the passage the twin was actually given, and rebuilding it here could differ from the
    stored one after a template version bump and nothing on screen would say so.

    A hand-built twin has no persona — `create_manual_twin` stores ``None`` on purpose, because a
    persona is a lossless reconstruction of a real driver and there is no driver behind a manual
    twin. That is stated rather than rendered as an empty box.
    """
    db = backend or get_backend()
    rows = await db.select("twins", [("eq", "twin_id", twin_id)])
    if not rows:
        raise StudioError(f"no twin {twin_id!r}")
    passage = rows[0].get("persona_passage")
    if not passage:
        return (
            "This twin has no persona passage.\n\n"
            "A persona is a lossless reconstruction of a real driver's survey answers, so a "
            "hand-built twin does not have one (docs/06 §5). It is told its profile and its "
            "slider values, and nothing else."
        )
    return str(passage)


async def survey_candidates(backend: DbBackend | None = None) -> list[dict[str, Any]]:
    """Mode 2 — **real respondents who consented to a twin only**. `docs/06` §5.

    Synthetic rows must not appear in this selector, and the filter is on `data_type` rather than
    on an absence of a batch id: a synthetic row is identified by what it is, not by what it
    lacks. `consent_twin` is statement 7 — a respondent who did not agree to a twin is never one,
    whatever else their row says (`docs/01` §6.2).
    """
    db = backend or get_backend()
    rows = await db.select(
        "survey_submissions",
        [("eq", "consent_twin", True), ("eq", "eligible", True), ("eq", "consented", True)],
        order=("submitted_at", True),
    )
    existing = {r["twin_id"] for r in await db.select("twins", None)}
    return [
        {
            "submission_id": r["submission_id"],
            "city": r.get("city"),
            "service": r.get("service"),
            "label": f"{r['submission_id']} — {r.get('city') or '?'} · {r.get('service') or '?'}",
        }
        for r in rows
        # Belt and braces: the query already excludes them, and so does this.
        if r.get("data_type") != SYNTHETIC_DATA_TYPE
        and r["submission_id"] not in existing
    ]


# ------------------------------------------------------------------ creation


async def create_twin_from_survey(
    submission_id: str, *, backend: DbBackend | None = None
) -> Twin:
    """Build one twin from a real, consented submission. `docs/06` §5 mode 2.

    Refuses a synthetic or unconsented row rather than filtering it earlier and trusting the
    caller: the selector and this function are two independent checks on the same rule, and the
    one that matters is the one next to the write.
    """
    db = backend or get_backend()
    rows = await db.select(
        "survey_submissions", [("eq", "submission_id", submission_id)], limit=1
    )
    if not rows:
        raise StudioError(f"no survey submission {submission_id!r}")
    row = rows[0]

    if row.get("data_type") == SYNTHETIC_DATA_TYPE:
        raise StudioError(
            f"{submission_id} is synthetic. 'From a survey answer' offers real respondents only "
            "(docs/06 §5); a synthetic twin is made in the Generator."
        )
    if not row.get("consent_twin"):
        raise StudioError(
            f"{submission_id} did not agree to a twin (statement 7). A respondent who withheld "
            "consent never becomes a twin (docs/01 §6.2)."
        )

    answers = {
        r["item_id"]: r["value_num"]
        for r in await db.select("survey_answers", [("eq", "submission_id", submission_id)])
        if r.get("value_num") is not None
    }
    twin = Twin(
        twin_id=submission_id,
        submission_id=submission_id,
        source="real",
        service=row.get("service"),
        city=row.get("city"),
        age=row.get("age"),
        gender=row.get("gender"),
        tenure_months=row.get("tenure_months"),
        hours_per_week=row.get("hours_per_week"),
    )
    passage = build_persona(
        twin, SurveyResponse(twin_id=submission_id, answers=answers)
    )
    # At the write, not in a handler: test 6's ablated persona is missing its fairness clauses by
    # design (I6), and a twin hashed from one would be indistinguishable downstream from a twin
    # whose driver never answered those items (`docs/08` §4 test 6).
    assert_not_ablated(passage)
    await db.insert(
        "twins",
        [{
            "twin_id": twin.twin_id,
            "source": "real",
            "service": twin.service,
            "city": twin.city,
            "age": twin.age,
            "gender": twin.gender,
            "tenure_months": twin.tenure_months,
            "hours_per_week": twin.hours_per_week,
            "consent_twin": True,
            "background": {},
            "persona_passage": passage.text,
            "persona_hash": passage.persona_hash,
            "persona_template_version": passage.template_version,
        }],
    )
    return twin


async def create_manual_twin(
    *,
    city: str,
    service: str,
    age: int | None = None,
    gender: str | None = None,
    tenure_months: int | None = None,
    hours_per_week: int | None = None,
    note: str = "",
    sliders: dict[str, int] | None = None,
    backend: DbBackend | None = None,
) -> Twin:
    """Mode 3 — a hand-built twin, stored ``source='manual'``. `docs/06` §5.

    **A manual twin is a sandbox object and can never enter an analysis** (`docs/03` §9.3): it has
    no real survey row, therefore no holdout and no quality score, and `POPULATION_SOURCES` names
    no ``manual`` population, so no panel draw can reach it.

    It carries no persona passage. A persona is a lossless reconstruction of a real driver's
    answers (I6); there is no driver here to be lossless about, and writing one would make a
    fabricated passage indistinguishable from a reconstructed one.
    """
    db = backend or get_backend()
    twin_id = f"manual-{uuid.uuid4().hex[:12]}"
    assert_not_ablated(sliders or {})
    twin = Twin(
        twin_id=twin_id,
        submission_id=None,
        source=MANUAL_SOURCE,
        service=service,
        city=city,
        age=age,
        gender=gender,
        tenure_months=tenure_months,
        hours_per_week=hours_per_week,
        background=Background(),
    )
    await db.insert(
        "twins",
        [{
            "twin_id": twin_id,
            "source": MANUAL_SOURCE,
            "service": service,
            "city": city,
            "age": age,
            "gender": gender,
            "tenure_months": tenure_months,
            "hours_per_week": hours_per_week,
            "consent_twin": False,
            "background": {"note": note, "sliders": dict(sliders or {})},
            "persona_passage": None,
            "persona_hash": None,
        }],
    )
    return twin


# ------------------------------------------------------------------ the ask


def studio_scenario(
    version_code: str | None, custom_change: str
) -> tuple[list[str], bool]:
    """What the twin is told, and whether this run is a sandbox-only one.

    A version code goes through the same stored-variant path the study uses. A custom change does
    not: it is free text that bypassed the lookup and the Checker, so the second return value is
    ``True`` and the caller must show :data:`SANDBOX_LABEL`.
    """
    if custom_change.strip():
        return [custom_change.strip()], True
    if not version_code:
        raise StudioError(
            "a studio run needs either a version code or a custom change (docs/06 §5)"
        )
    return [], False


async def run_studio(
    *,
    twin_id: str,
    version_code: str | None = None,
    custom_change: str = "",
    questions: list[str] | None = None,
    include_battery: bool = False,
    model: str = "mock",
    seed: int = 0,
    answers: dict[str, int] | None = None,
    free_answers: dict[str, str] | None = None,
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """Record one studio run in `studio_runs`, **appending** and moving the latest pointer. §4.4.

    `studio_runs` stays the full sandbox record — it holds `free_answers`, `questions` and
    `scenario_text` that `twin_answers` has no column for. What changed is that a second ask for the
    same ``(twin_id, version_code, custom_change)`` **appends and moves
    `is_latest_for_twin_version`**, exactly as `runs.is_latest_for_version` works: demote and insert
    in one transaction, and the earlier row survives (I9).

    This function still has **no code path to `runs` or `twin_answers`**. Filing a Studio ask as
    evidence is :func:`file_studio_run`'s job, which is called separately and only for a dialled
    version — so the one path that must stay fully quarantined (a custom free-text change) is
    quarantined by not calling it, not by remembering a rule.
    """
    db = backend or get_backend()
    asked = [q.strip() for q in (questions or []) if q.strip()]
    if len(asked) > MAX_QUESTIONS:
        raise StudioError(
            f"{len(asked)} questions asked; the Studio takes at most {MAX_QUESTIONS} "
            "(docs/06 §5)"
        )

    scenario, sandbox = studio_scenario(version_code, custom_change)
    if not sandbox and version_code:
        from twinlab.services.lab import scenario_paragraphs

        scenario = await scenario_paragraphs(version_code, backend=db)

    row = await db.rpc(
        "studio_run_record",
        {
            "p_row": {
                "studio_run_id": str(uuid.uuid4()),
                "twin_id": twin_id,
                # Exactly one of these is set: a custom change has no version code, because it is
                # not one of the 243 and must never be filed as one.
                "version_code": None if sandbox else version_code,
                "custom_change": custom_change.strip() or None,
                "questions": asked,
                "include_battery": include_battery,
                "answers": answers,
                "free_answers": free_answers,
                "scenario_text": scenario,
                "model": model,
                "seed": seed,
            }
        },
    )
    result = dict(row)
    result["sandbox"] = sandbox
    result["label"] = SANDBOX_LABEL if sandbox else ""
    return result


# ------------------------------------------------------------------ filing a Studio ask
#
# `ARCHITECTURE_UPDATE.md` §1.1 and §4.3, confirmed by the researcher: *"by overwrite, it's ok for
# the studio values to feed analyses"*. This reverses `docs/01` §6.9's blanket quarantine for the
# **dialled-version** path only, and it is satisfiable without breaking `CLAUDE.md` rule 6:
#
#   * a Studio ask APPENDS a `sessions` row, a `runs` row and a `twin_answers` row. Nothing is
#     updated in place anywhere;
#   * `services/results.completed_runs` already takes the latest run per `version_code` by
#     `started_at` descending, so a later Dial board run supersedes the Studio value automatically.
#     That is the requested precedence, with no precedence logic to write or get wrong.
#
# What it costs is stated in the data rather than argued about: a version whose most recent run is a
# Studio run reports an index over **one twin**, while `00000` and `SHAM` — the noise floor a lever
# effect must clear — come from the frozen panel. `runs.origin` and `twins_n` are therefore shown
# wherever that number is (`services/results`, the Results table, the side panel).


async def _require_quality_passed(twin_id: str, db: DbBackend) -> None:
    """Refuse to file a result for a twin the quality gate did not keep.

    **Not in `ARCHITECTURE_UPDATE.md`; raised by it.** §1.1 lets a Studio ask become a result, and
    the Studio deliberately offers *every* twin including the ones the gate dropped — that asymmetry
    is the point of the screen (`services/studio.studio_twins`). Those two together would let a
    dropped twin's answer into the analysis, and `docs/03` §9.1 is explicit that a twin that failed
    the gate is dropped from the panel **and from all cells**.

    The plan does not decide this, so the conservative reading of the existing invariant is taken:
    the twin can still be **asked** — nothing about the Studio's inspection value changes — but its
    answer is not **filed**. The screen says so. A manual twin has no quality run either, so this
    subsumes that case.

    **Flagged for the researcher**: the alternative reading, that a Studio result is explicitly
    labelled `origin='studio'` and so a reader can judge it for themselves, is defensible and is
    theirs to take. It would be one line here.
    """
    rows = await db.select(
        "twin_quality_runs",
        [
            ("eq", "twin_id", twin_id),
            ("eq", "holdout_set", "H3"),
            ("eq", "is_latest", True),
        ],
    )
    if rows and rows[0].get("kept"):
        return
    why = (
        "has not been through the quality test"
        if not rows
        else "was dropped by the quality test"
    )
    raise StudioError(
        f"{twin_id} {why}, so its answer is not recorded as a result for this version. A twin the "
        "gate dropped is dropped from the panel and from every cell (docs/03 §9.1) — you can still "
        "ask it anything here, and the conversation is kept in the Studio record."
    )


async def file_studio_run(
    *,
    twin_id: str,
    version_code: str,
    answers: dict[str, int],
    model: str,
    seed: int,
    wording: str = "A",
    backend: DbBackend | None = None,
) -> dict[str, Any]:
    """File one Studio answer vector as a real run. §4.3. **Append only.**

    Five properties, each of which is a commitment rather than plumbing:

    * **The index is computed by the same** :func:`services.twin_runtime.analyse` **the sweep
      uses**, so a Studio number and a sweep number are the same statistic over a different n —
      never two different formulas.
    * **No `session_panel` row is written** and the session is never inheritable by a rerun. I14
      applies to frozen panels and a Studio ask has none; a rerun that "inherited" a one-twin panel
      would be a different experiment wearing a version code.
    * **`origin='studio'` and `twins_n=1`** travel with the row, so every surface that shows the
      number can say where it came from.
    * **I15 holds**: ``twins_n = 1 ≥ 1``. A Studio ask whose twin failed the answer ladder never
      reaches this function, so it is `failed`, never `completed` with an index of 0.000.
    * **A custom free-text change never reaches here.** It has no `version_code` to be latest for,
      it bypassed the lookup (I1) and the Checker (I3), and it is not one of the 243.
    * **A twin the quality gate dropped is refused.** See :func:`_require_quality_passed`.
    """
    from twinlab.db.repositories import AnswerRepo, RunRepo, SessionRepo
    from twinlab.orchestrator.odometer import CONTROL_CODE, validate_code
    from twinlab.services.runs import session_config
    from twinlab.services.twin_runtime import analyse

    if not answers:
        raise StudioError(
            "a Studio run with no answers is not a result (I15). It is recorded as failed."
        )
    validate_code(version_code)
    if version_code == CONTROL_CODE:
        raise StudioError(
            f"{CONTROL_CODE} is the control every shift is measured against, not a cell to file a "
            "one-twin result for (docs/03 §6.1). Its index comes from the frozen panel."
        )

    db = backend or get_backend()
    await _require_quality_passed(twin_id, db)
    session = await SessionRepo(db).create(
        name=f"Studio {version_code} · {twin_id}",
        kind="studio",
        iterations=1,
        start_code=version_code,
        # Zero, not one. `panel_size` is the size of a *frozen panel*, and this run has none —
        # writing 1 would make a rerun believe it could inherit a panel of one twin.
        panel_size=0,
        config=await session_config(db),
    )
    # `origin` is set on the INSERT, not stamped afterwards. An UPDATE to a `runs` row — even one
    # this function has just created and which carries no result yet — is the one shape `CLAUDE.md`
    # rule 6 asks nobody to reach for, and there is no reason to: the value is known here.
    run = await RunRepo(db).get_or_create(
        session.session_id, version_code, origin="studio"
    )
    await AnswerRepo(db).record(
        run_id=run.run_id,
        twin_id=twin_id,
        answers=answers,
        lever_order=[],
        seed=seed,
        wording=wording,
        model=model,
    )
    # The same `analyse` the sweep calls, so the formula cannot diverge. It reads `twin_answers`
    # back and computes every number in Python (`CLAUDE.md` rule 3, I12).
    await SessionRepo(db).set_status(session.session_id, "running")
    try:
        metrics, index_value, reading = await analyse(run.run_id, backend=db)
    except Exception as exc:
        # I15. The commonest cause is a hand-built twin, or one whose driver left part of the
        # battery blank: `compute_shifts` excludes it from both sides and the intersection is empty.
        # The run is marked `failed` with the reason rather than completed with an index of 0.000,
        # and the `twin_answers` row stays — the answer happened, the comparison did not.
        await RunRepo(db).fail(run.run_id, f"{type(exc).__name__}: {exc}"[:400])
        # The session is closed on the way out, not left at `created`. A session that never reaches
        # a terminal state is reported by the Agents tab as a job that is still running — which
        # keeps the poll timer awake and makes the job line say "0 of 1 done" for ever.
        await SessionRepo(db).set_status(session.session_id, "failed")
        raise StudioError(
            f"{version_code} could not be scored for {twin_id}: {exc} The answer is kept in the "
            "Studio record, but nothing was filed as a result."
        ) from exc
    completed = await RunRepo(db).complete(
        run.run_id,
        twins_n=1,
        metrics=metrics,
        index_value=index_value,
        analysis=reading,
    )
    await SessionRepo(db).set_status(session.session_id, "completed")
    return {
        "run_id": completed.run_id,
        "session_id": session.session_id,
        "origin": "studio",
        "twins_n": 1,
        "index_value": index_value,
        "metrics": metrics,
    }


#: The system prompt for the free-text questions. The twin agent's own prompt asks for a 37-item
#: JSON vector, which is the wrong shape for "would you tell other drivers about it?" — so the
#: round is assembled the same way and only the OUTPUT section differs.
#:
#: It carries the same `# IF YOU CANNOT` discipline as every other prompt (`docs/02` §3.2): a model
#: given no failure path invents one.
QUESTION_PROMPT = """# ROLE

You are the driver described in `<<<PERSONA>>>`. You drive for Uber in India.

# INPUTS

- `<<<PERSONA>>>` — who you are, in your own account.
- `<<<SCENARIO>>>` — what Uber is now doing differently. Read it as an announcement in the app.
- `<<<QUESTIONS>>>` — what someone has asked you, one per line.

# TASK

Answer each question in `<<<QUESTIONS>>>`, in order, as that person would answer it now that
`<<<SCENARIO>>>` is true.

# RULES

1. Stay in character. Never mention being a model, a program or a simulation.
2. Two or three sentences per question. Your own words, not a summary of the announcement.
3. Use nothing beyond `<<<PERSONA>>>` and `<<<SCENARIO>>>`. Do not invent circumstances.
4. A change may matter a great deal, a little, or not at all. Saying it changes nothing for you is
   a real and common answer.

# OUTPUT

A JSON object with exactly these fields:

- `replies` — a list of strings, **one per question, in the order asked**. Never fewer, never more.
- `rationale` — at most two sentences on what made the difference.

Return the object and nothing else.

# IF YOU CANNOT

Answer anyway, in the voice of the person in `<<<PERSONA>>>`. If a question does not apply to you,
say so in your own words — that is an answer. Do not leave a question out and do not return fewer
replies than there are questions; a reply list that does not line up is discarded, not filled in
for you.
"""


class StudioBlocked(StudioError):
    """A stimulus that must not reach a twin, even in the sandbox.

    The quarantine is about where an answer is **filed**, not about whether the stimulus was
    verified. A dialled version whose Checker report fails is an unverified variant, and I3 has no
    sandbox exemption.
    """


# ------------------------------------------------------------------ render on demand
#
# `ARCHITECTURE_UPDATE.md` §4.2. The Studio used to be a dead end for any version that had never
# been rendered: `_stimulus` refused, correctly, and the only way to produce a verified variant was
# to run the **whole frozen panel** from the Dial board to answer a one-twin question.
#
# The refusal stays — I3 has no sandbox exemption. What is added is a way to *produce* a verified
# variant from the Studio. Rendering was never forbidden, only expensive, and `CLAUDE.md` rule 12
# forbids it in a handler's synchronous path — so it is enqueued and the log is how it is watched,
# exactly as `start_quality_gate` works.
#
# It is also a net **saving**: the variant is keyed `(version_code, style_version)` like any other,
# so a later Dial board run for the same code hits the cache and pays nothing (I4).

#: Strong references to running render tasks, keyed by version code. `asyncio` keeps only a weak
#: reference to a running task, so a bare `create_task` whose result nobody holds can be collected
#: mid-render — documented, not theoretical.
_RENDERS: dict[str, Any] = {}


def rendering(version_code: str) -> bool:
    """Whether a render for this code is in flight **in this process**."""
    task = _RENDERS.get(version_code)
    return task is not None and not task.done()


async def variant_status(
    version_code: str, *, backend: DbBackend | None = None
) -> dict[str, Any]:
    """Whether this code has a stored, Checker-passed variant, and what it would cost to make one.

    Pure read, and it is what the Studio shows **before** offering *Render this version now*:
    `docs/06` §9 requires the budget on every confirm step, and §4.2 point 4 says never render
    blind.
    """
    from twinlab.orchestrator import budget as budget_calc
    from twinlab.services.runs import budget_view
    from twinlab.services.twin_runtime import _levers_with_budget, paragraph_pool

    db = backend or get_backend()
    row = await VariantRepo(db).get(version_code, settings.style_version)
    report = dict((row or {}).get("checker") or {})
    cached = await db.count(
        "lever_paragraphs", [("eq", "style_version", settings.style_version)]
    )
    # WP-2 item 3. A stored row that did **not** pass used to be a dead end on this screen: the
    # Studio showed the failure and offered nothing, because `render_and_check` short-circuited on
    # it. It is now retryable within the durable paragraph budget, so the screen must say how much
    # of that budget is left — "retry" with nothing to spend is a button that cannot work.
    retryable: list[str] = []
    if row is not None and not report.get("passed"):
        retryable = await _levers_with_budget(version_code, paragraph_pool(backend=db))
    return {
        "version_code": version_code,
        "exists": row is not None,
        "passed": bool(report.get("passed")),
        "notes": str(report.get("notes") or ""),
        #: Non-dial-0 levers of this code that still have their one re-render. Empty while a
        #: stored failure stands means pressing again would make no model call and change nothing.
        "retryable_levers": retryable,
        "can_retry": bool(retryable),
        "rendering": rendering(version_code),
        # The ten lever paragraphs are shared by all 243 cells, so a code is usually free to render
        # once a few of its neighbours have been. That is the cache being visible, per `docs/10` §7.
        "budget": budget_view(budget_calc.render_budget(paragraphs_cached=cached)),
    }


async def start_render(
    version_code: str, *, backend: DbBackend | None = None
) -> str:
    """Render and Checker-verify one version in the background. Returns the session id. §4.2.

    Mirrors :func:`services.quality.start_quality_gate`: it writes a session row, enqueues the
    work, and returns — **no model call happens in this function** (`CLAUDE.md` rule 12).

    It reuses :func:`services.twin_runtime.render_and_check` unchanged, so the `(version_code,
    style_version)` cache (I4), the durable re-render budget and all five Checker gates apply
    exactly as they do on the sweep path. There is deliberately no second render implementation
    here: a Studio render that verified a stimulus differently from the study's render would be the
    worst possible thing this function could be.
    """
    from twinlab.db.repositories import SessionRepo
    from twinlab.orchestrator.odometer import validate_code
    from twinlab.services.runs import session_config

    validate_code(version_code)
    db = backend or get_backend()
    if rendering(version_code):
        raise StudioError(
            f"{version_code} is already being rendered in this process. Watch it in "
            "Twin Lab → Agents; starting a second render would spend the design budget twice."
        )

    session = await SessionRepo(db).create(
        name=f"Render {version_code}",
        kind="render",
        iterations=0,
        start_code=version_code,
        panel_size=0,
        population="real",
        config=await session_config(db),
    )
    task = asyncio.create_task(
        _render_task(version_code, session.session_id, db)
    )
    _RENDERS[version_code] = task

    def _done(finished: asyncio.Task) -> None:
        """Release the slot **and retrieve the exception**.

        `_render_task` guards its model call, but not the writes either side of it, and a callback
        that never calls `.exception()` turns anything else into an "exception was never retrieved"
        warning at interpreter shutdown — which is the exact failure `services/runs._spawn` was
        written to prevent, and which would leave the researcher watching a render that silently
        never happened.
        """
        _RENDERS.pop(version_code, None)
        if not finished.cancelled() and finished.exception() is not None:
            log.error(
                "render of %s failed outside its own guard: %r",
                version_code,
                finished.exception(),
            )

    task.add_done_callback(_done)
    return session.session_id


async def _render_task(version_code: str, session_id: str, db: DbBackend) -> None:
    """The background half of :func:`start_render`. Emits into `run_events` throughout.

    Every stage is logged under the session id, so the Agents log tree shows a Studio render the
    same way it shows a sweep's — which is the only reason a researcher can tell a slow render from
    a dead one.
    """
    from twinlab.db.repositories import SessionRepo
    from twinlab.orchestrator.events import EventLog

    log_ = EventLog(session_id, db)
    sessions = SessionRepo(db)
    try:
        await _render_body(version_code, session_id, db, log_, sessions)
    except Exception as exc:  # noqa: BLE001 — the session must not be left `running` for ever
        log.error("render of %s failed: %r", version_code, exc)
        try:
            await sessions.set_status(session_id, "failed")
        except Exception:  # noqa: BLE001 — the error path must not raise its own error
            pass


async def _render_body(
    version_code: str, session_id: str, db: DbBackend, log_: Any, sessions: Any
) -> None:
    """The body of :func:`_render_task`, separated so its guard cannot miss a line of it."""
    from twinlab.services.twin_runtime import render_and_check

    await sessions.set_status(session_id, "running")
    parent = await log_.emit(
        stage="render",
        agent="design",
        label=f"Rendering {version_code} for the Twin Studio",
        status="running",
    )
    try:
        variant, report = await render_and_check(
            version_code, settings.style_version, backend=db, events=log_
        )
    except Exception as exc:  # noqa: BLE001 — the reason must reach the log, not just the console
        await log_.emit(
            stage="render",
            agent="design",
            label=f"{type(exc).__name__}: {exc}"[:400],
            status="error",
            parent_event_id=parent,
        )
        await sessions.set_status(session_id, "failed")
        return

    # Stored **with its verdict, pass or fail** — the same call, with the same payload shape, that
    # `orchestrator/loop._render` and `services/quality` make. Three reasons it is not "store only
    # on a pass":
    #
    #  * what blocks the stimulus is `checker.passed`, read by `_stimulus` and by
    #    `agent_config.twin_test_view`, not the absence of a row. I3 is enforced at the read.
    #  * `render_and_check` short-circuits on a stored row, so a stored failure is what makes
    #    `docs/03` §5's "re-render once, then halt that cell" actually halt.
    #  * a cell that failed and left no trace is indistinguishable from one never attempted.
    await VariantRepo(db).put(
        version_code=version_code,
        style_version=settings.style_version,
        delta_spec={"version_code": version_code},
        delta_hash=variant.delta_hash,
        paragraphs={lever: p.text for lever, p in variant.paragraphs.items()},
        checker=report.model_dump(),
    )
    await log_.emit(
        stage="check",
        agent="checker",
        label=(
            f"{version_code} passed the Checker and is stored."
            if report.passed
            else f"{version_code} did not pass the Checker: {str(report.notes or '')[:200]}"
        ),
        status="ok" if report.passed else "error",
        parent_event_id=parent,
    )
    # The parent is closed too. An event left `running` is what the Agents tab's Policy Designer
    # card reads as its latest line, so without this the card says "Rendering 22000…" for ever —
    # for a render that finished seconds ago.
    await log_.set_status(
        parent, "ok" if report.passed else "error",
        label=f"render {version_code} (Twin Studio)",
    )
    await sessions.set_status(
        session_id, "completed" if report.passed else "failed"
    )




async def ask_studio(
    *,
    twin_id: str,
    version_code: str | None = None,
    custom_change: str = "",
    questions: list[str] | None = None,
    include_battery: bool = False,
    backend: DbBackend | None = None,
) -> Any:
    """`docs/06` §5's *Ask the twin*, for real. Records the run and returns what to render.

    Three things happen here and nothing else: the stimulus is resolved, the twin is asked, and
    :func:`run_studio` files the result in `studio_runs`. There is still no code path from this
    function to `runs`, `twin_answers` or any metric table.

    **The comparison is against the twin's own driver**, which is what "Uber today" means on this
    screen: every driver is their own control (`docs/07` §3.1). A hand-built twin has no driver, so
    its baseline column is empty rather than zero.
    """
    from twinlab.agents.contract import ContractError
    from twinlab.agents.registry import get_client
    from twinlab.analysis.metrics import score
    from twinlab.ingest.reference_store import reference
    from twinlab.models.view import StudioMetricRow, StudioResult
    from twinlab.services.twin_runtime import (
        TwinPathError,
        ask_items,
        battery_for,
        driver_answers,
        persona_for,
        round_seed,
        twin_agent_config,
    )

    db = backend or get_backend()
    # RESEARCHER 2026-10-05. Nothing asks a twin under a config the quality test has not validated.
    # The check is that the live config has at least one qualified twin, not that this twin is one:
    # a hand-built twin has no driver, so it can never pass the gate, and the Studio must still
    # reach it once the config is validated.
    from twinlab.services.config_match import (
        current_config,
        current_fingerprint,
        qualified_twin_ids,
    )

    live_fp = await current_fingerprint(db)
    if not await qualified_twin_ids(live_fp, db):
        live = await current_config(db)
        raise StudioError(
            f"The twin quality test has not been run for the current config ({live['model']} at "
            f"temperature {float(live['temperature']):g}). Run it on the Agents tab first; nothing "
            "asks a twin under a config that has not been validated."
        )
    ref = reference()
    asked = [q.strip() for q in (questions or []) if q.strip()]
    if len(asked) > MAX_QUESTIONS:
        raise StudioError(
            f"{len(asked)} questions asked; the Studio takes at most {MAX_QUESTIONS} "
            "(docs/06 §5)"
        )

    paragraphs, scenario, sandbox = await _stimulus(version_code, custom_change, db)
    cfg = twin_agent_config()
    seed = round_seed("studio", twin_id, version_code or "custom")
    persona = await persona_for(twin_id, db)
    baseline = await driver_answers(twin_id, db)

    result = StudioResult(
        twin_id=twin_id,
        version_code=None if sandbox else version_code,
        model=cfg.model.name,
        sandbox=sandbox,
        label=SANDBOX_LABEL if sandbox else "",
        scenario_text=scenario,
    )

    answers: dict[str, int] | None = None
    rationale = ""
    if include_battery:
        from twinlab.services.config import load_twin_config

        try:
            answers, telemetry = await ask_items(
                twin_id=twin_id,
                paragraphs=paragraphs,
                items=battery_for(ref),
                baseline=baseline,
                seed=seed,
                # Live config, not hard-coded: a Studio ask puts the live instrument to one twin,
                # and a hard-coded True would silently diverge from what the sweep actually shows
                # once `show_baseline` differs from it (`docs/DECISIONS.md`, 2026-10-07).
                show_baseline=load_twin_config().show_baseline,
                version_code=None if sandbox else version_code,
                backend=db,
            )
            rationale = str(telemetry.get("rationale") or "")
        except (ContractError, TwinPathError) as exc:
            # Nothing is coerced into a vector. The run is still recorded, with the reason, so a
            # failure is visible rather than looking like a twin that did not move.
            result.blocked = (
                f"The twin did not produce a valid 37-item answer after one repair "
                f"({type(exc).__name__}). Nothing was recorded for the survey questions."
            )
    else:
        result.no_battery_note = (
            "The 37 survey questions were not asked, so there is no comparable answer set for "
            "this run. Tick 'Also ask the 37 survey questions' to record one."
        )

    if answers is not None:
        complete_baseline = all(i in baseline for i in ref.battery_item_ids)
        for metric in ref.metrics:
            now = score(answers, metric, ref)
            # A metric is never computed over a subset (`docs/07` §2.3), so a twin whose driver
            # left part of the battery blank gets an empty "Uber today" column, not a partial one.
            before = score(baseline, metric, ref) if complete_baseline else None
            result.rows.append(
                StudioMetricRow(
                    metric=metric,
                    label=metric.capitalize(),
                    now=round(now, 2),
                    baseline=None if before is None else round(before, 2),
                    change=None if before is None else round(now - before, 2),
                    reason=rationale,
                )
            )
        result.rationale = rationale

    replies: dict[str, str] = {}
    if asked:
        replies = await _ask_questions(
            cfg=cfg,
            client=get_client(),
            persona=persona,
            paragraphs=paragraphs,
            questions=asked,
            seed=seed,
        )
        result.replies = replies

    await run_studio(
        twin_id=twin_id,
        version_code=version_code,
        custom_change=custom_change,
        questions=asked,
        include_battery=include_battery,
        model=cfg.model.name,
        seed=seed,
        answers=answers,
        free_answers=replies or None,
        backend=db,
    )

    # `ARCHITECTURE_UPDATE.md` §1.1 and §4.3: a **dialled** version with a real answer vector is
    # also filed as a run, so it reaches Results and the index. Three conditions, all of which must
    # hold, and each of which is an invariant rather than a preference:
    #
    #   * `not sandbox` — a custom free-text change is not one of the 243 and has no version code
    #     to be latest for. It stays fully quarantined (§4.5).
    #   * `answers is not None` — nothing is filed without a complete, validated 37-item vector.
    #   * `version_code` — the control cell is refused inside `file_studio_run`.
    if not sandbox and answers is not None and version_code:
        try:
            filed = await file_studio_run(
                twin_id=twin_id,
                version_code=version_code,
                answers=answers,
                model=cfg.model.name,
                seed=seed,
                backend=db,
            )
        except StudioError as exc:
            # The conversation still happened and is still shown; it simply did not become a
            # result. Saying so is the point — a number that quietly did not appear in Results is
            # indistinguishable from one that did.
            result.not_filed = str(exc)
        else:
            result.run_id = filed["run_id"]
            result.origin = "studio"
            result.twins_n = 1
            result.index_value = filed["index_value"]
    elif not sandbox and answers is not None:
        result.not_filed = ""
    elif not sandbox:
        result.not_filed = (
            "The 37 survey questions were not asked, so there is no answer vector to score. "
            "Nothing was filed in Results."
        )
    return result


async def _stimulus(
    version_code: str | None, custom_change: str, db: DbBackend
) -> tuple[dict[str, str], list[str], bool]:
    """``(paragraphs by lever, scenario lines, sandbox)``.

    A dialled version uses **the stored, Checker-passed variant** and nothing else. If the cell
    has never been rendered, or its stored Checker report did not pass, the Studio refuses: I3 has
    no sandbox exemption, and asking anyway would put an unverified stimulus in front of a twin
    for the sake of a screen.

    A custom change bypasses the lookup (I1) and the Checker (I3) **by construction** — it is free
    text, not one of the 243 — so it is allowed, carries :data:`SANDBOX_LABEL`, and is never filed
    under a version code.
    """
    from twinlab.models.reference import LEVER_BY_POSITION

    scenario, sandbox = studio_scenario(version_code, custom_change)
    if sandbox:
        # One free-text block in the first slot; the other four carry the fixed dial-0 line, so
        # the round prompt gets the five paragraphs it requires without inventing four changes.
        paragraphs = {lever: DIAL_ZERO_TEXT for lever in LEVER_BY_POSITION}
        paragraphs[LEVER_BY_POSITION[0]] = scenario[0]
        return paragraphs, scenario, True

    # Keyed on BOTH halves of `(version_code, style_version)`. A lookup on the version code alone
    # served a v1 paragraph to a v2 app the moment a second style_version existed — a stimulus
    # verified under a style contract it was not written to, which is exactly the confound
    # `config/style_contract.yaml` bumps the key to prevent.
    row = await VariantRepo(db).get(version_code, settings.style_version)
    rows = [row] if row else []
    if not rows:
        raise StudioBlocked(
            f"{version_code} has never been rendered, so there is nothing verified to show a "
            "twin (I3). Press **Render this version now** above — it costs only the lever "
            "paragraphs this version needs that are not already cached, and a later Dial board "
            "run for the same version reuses them. Or write your own change instead."
        )
    report = rows[0].get("checker") or {}
    if not report.get("passed"):
        raise StudioBlocked(
            f"{version_code} did not pass the Checker, so it must not reach a twin (I3). "
            f"{str(report.get('notes') or '')[:300]}"
        )
    stored = dict(rows[0].get("paragraphs") or {})
    paragraphs = {}
    for lever in LEVER_BY_POSITION:
        entry = stored.get(lever)
        paragraphs[lever] = entry.get("text", "") if isinstance(entry, dict) else str(entry or "")
    return paragraphs, [paragraphs[lever] for lever in LEVER_BY_POSITION], False


async def _ask_questions(
    *,
    cfg: Any,
    client: Any,
    persona: str,
    paragraphs: dict[str, str],
    questions: list[str],
    seed: int,
) -> dict[str, str]:
    """The free-text half of `docs/06` §5. Prose, never parsed for data (I12).

    The persona and scenario blocks are assembled by the **same** functions the battery round
    uses, so the twin reads the identical stimulus either way; only the battery fence is replaced
    by the researcher's questions, and only the OUTPUT section of the prompt differs.
    """
    from twinlab.agents.twin import build_round_prompt, build_user_prompt
    from twinlab.models.twin import StudioReply

    round_prompt = build_round_prompt(
        persona_hash="",
        paragraphs=paragraphs,
        baseline={},
        # `build_user_prompt` refuses an empty fence, so the battery carries one placeholder that
        # is cut off below with the fence itself. Nothing downstream reads it.
        battery={"_": ("placeholder", 7)},
        seed=seed,
        show_baseline=False,
    )
    body = build_user_prompt(round_prompt, persona)
    body = body.split("<<<BATTERY>>>", 1)[0].rstrip()
    body += "\n\n<<<QUESTIONS>>>\n" + "\n".join(questions) + "\n<<<END QUESTIONS>>>"

    result = await client.run(
        cfg, system_prompt=QUESTION_PROMPT, user_prompt=body, output_type=StudioReply
    )
    output = result.output
    if not isinstance(output, StudioReply):
        return {}
    try:
        return output.aligned(questions)
    except ValueError:
        # A reply list that does not line up is discarded, not padded: a reply attached to a
        # question the twin did not answer is a fabricated answer.
        return {}


async def studio_history(
    twin_id: str | None = None, *, backend: DbBackend | None = None
) -> list[dict]:
    """Past studio runs, newest first. Read-only; never joined to `runs`."""
    db = backend or get_backend()
    filters = [("eq", "twin_id", twin_id)] if twin_id else None
    return await db.select("studio_runs", filters, order=("created_at", True))


__all__ = [
    "MANUAL_SOURCE",
    "MANUAL_SLIDERS",
    "MAX_QUESTIONS",
    "SANDBOX_LABEL",
    "TWIN_MODES",
    "QUESTION_PROMPT",
    "StudioBlocked",
    "StudioError",
    "ask_studio",
    "create_manual_twin",
    "file_studio_run",
    "create_twin_from_survey",
    "rendering",
    "run_studio",
    "start_render",
    "studio_history",
    "studio_scenario",
    "studio_persona",
    "studio_selectors",
    "studio_twins",
    "survey_candidates",
    "twin_id_of",
    "variant_status",
]
