"""Running the eight validity tests and appending their results. `docs/08` §4, `docs/06` §3.5.

The statistics themselves are in `validity/tests.py`, which knows nothing about a database. This
module is the part that reads stored evidence, decides whether a test *can* run, and appends one
`validity_results` row per completed test.

Five properties are research commitments rather than plumbing:

* **Every completed test appends** (I9). :func:`append_result` inserts and has no update path; no
  test ever replaces a row. The results table doubles as the log (`docs/08` §4).
* **A test that ran on nobody records `INCONCLUSIVE`** (I15). Three separate things say so:
  :class:`~twinlab.models.validity.ValidityOutcome` refuses to be constructed otherwise, the DDL's
  `validity_zero_n` rejects the row, and the in-memory backend mirrors the constraint. The
  prototype shipped live-mode `PASS` verdicts on `twins = 0`.
* **Tests 1 and 3 make zero model calls.** Neither branch below takes or passes an ``ask``
  callable; both read stored vectors. `docs/11` M13 asserts this on the call counter.
* **Test 4's probe is never written to `variants`** and **test 6's ablated persona is never hashed
  into `twins`**. Both are enforced at the write — :func:`assert_not_a_probe` is called inside
  `VariantRepo.put` and :func:`assert_not_ablated` inside the two functions that insert a twin —
  rather than by a handler remembering, which is the Studio quarantine's pattern.
* **Test 8 writes a recommendation, not a setting.** `TwinConfig.temperature` is frozen onto every
  session's config (`docs/09` §4); changing it from inside a test would make two sessions
  incomparable with nothing in the data saying why. The researcher applies it deliberately.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from config.settings import settings
from twinlab.analysis.metrics import compute_index, score, score_all
from twinlab.db.client import DbBackend, get_backend
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.validity import (
    AblatedPersona,
    TemperatureRecommendation,
    ValidityOutcome,
    assert_not_a_probe,
    assert_not_ablated,
)
from twinlab.models.view import BudgetView
from twinlab.orchestrator import budget as budget_calc
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE
from twinlab.validity import tests as vt

#: `app_config` key test 8 writes. **Not** `temperature`: a recommendation and an applied setting
#: are different things, and only one of them is frozen onto a session (`docs/02` §7.3).
TEMPERATURE_RECOMMENDATION_KEY = "twin_temperature_recommendation"

#: Where a twin's H2 answer vector lives. `docs/01` §6 gives `twin_quality_runs` a `detail` jsonb
#: and no column for the vector, so the vector is filed under this key by the quality gate and read
#: back here. Recorded in `docs/DECISIONS.md` — the specification names no home for it, and test 1
#: is the only reader.
H2_ANSWERS_KEY = "answers"

#: How a validity test identifies the model it ran on when no live provider is configured.
MOCK_MODEL = "mock"


class ValidityRunError(RuntimeError):
    """A validity test that must not run, or a result that must not be stored."""


#: What a live validity test needs in order to put a stimulus to twins. Injected rather than
#: imported so this layer stays testable without a provider, exactly as `SessionRunner` takes
#: `ask_twin`. ``None`` means no live twin path is wired, and the affected tests say so rather
#: than inventing vectors.
AskTwins = Callable[..., Awaitable[dict[str, dict[str, int]]]]


# ------------------------------------------------------------------------------ budgets


def calls_for(number: int, twins: int) -> int:
    """`docs/08` §4's call table. Tests 1 and 3 are zero; test 5 is 2N and test 8 is 3N."""
    if number not in vt.CALLS_PER_TWIN:
        raise ValidityRunError(f"there are eight validity tests; {number} is not one of them")
    return vt.CALLS_PER_TWIN[number] * max(twins, 0)


async def validity_budget_view(
    number: int, *, twins: int | None = None, backend: DbBackend | None = None
) -> BudgetView:
    """The confirm step's budget, like every other long action (`docs/06` §9).

    A zero-call test still gets a budget card, showing zero. That is the point: it is how the
    researcher sees that tests 1 and 3 are free and can be run early and often (`docs/08` §4).
    """
    from twinlab.services.runs import budget_view

    n = twins if twins is not None else settings.panel_size
    return budget_view(budget_calc.ask_budget(panel_size=calls_for(number, n)))


# --------------------------------------------------------------------------- stored reads


async def _submission_id(twin_id: str, db: DbBackend) -> str:
    rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
    # `twin_id` matches `submission_id` by convention where the column is absent, which is what
    # `services/lab._driver_answers` already relies on.
    return str((rows[0].get("submission_id") if rows else None) or twin_id)


async def _human_answers(twin_id: str, db: DbBackend) -> dict[str, int]:
    """One driver's own survey answers, by item id. Never imputed, never defaulted."""
    submission = await _submission_id(twin_id, db)
    rows = await db.select("survey_answers", [("eq", "submission_id", submission)])
    return {r["item_id"]: int(r["value_num"]) for r in rows if r.get("value_num") is not None}


async def h2_vectors(db: DbBackend) -> dict[str, dict[str, int]]:
    """Every twin's stored H2 answer vector. `docs/08` §3.1.

    Read from the latest H2 `twin_quality_runs` row's `detail`, which is where the quality gate
    files it. A twin whose row carries no vector is **absent** from the result rather than present
    and empty: test 1 must not score a twin it has no answers for.
    """
    rows = await db.select(
        "twin_quality_runs", [("eq", "is_latest", True), ("eq", "holdout_set", "H2")]
    )
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        answers = (row.get("detail") or {}).get(H2_ANSWERS_KEY) or {}
        vector = {k: int(v) for k, v in answers.items() if v is not None}
        if vector:
            out[str(row["twin_id"])] = vector
    return out


async def noise_floor(
    session_id: str | None, db: DbBackend
) -> float | None:
    """``|index(00000)|`` for this session. `docs/07` §6. ``None`` when the control never ran.

    Never pooled across sessions: a floor drawn from a different panel describes different twins,
    and a cell reported against it is reported against nothing.
    """
    if session_id is None:
        return None
    rows = await db.select(
        "runs",
        [
            ("eq", "session_id", session_id),
            ("eq", "version_code", CONTROL_CODE),
            ("eq", "status", "completed"),
        ],
        order=("started_at", True),
        limit=1,
    )
    if not rows or rows[0].get("index_value") is None:
        return None
    return round(abs(float(rows[0]["index_value"])), 4)


async def _run_answers(
    session_id: str, version_code: str, db: DbBackend
) -> dict[str, dict[str, int]]:
    """Twin → answer vector for one completed cell of this session, or ``{}``."""
    runs = await db.select(
        "runs",
        [
            ("eq", "session_id", session_id),
            ("eq", "version_code", version_code),
            ("eq", "status", "completed"),
        ],
        order=("started_at", True),
        limit=1,
    )
    if not runs:
        return {}
    rows = await db.select("twin_answers", [("eq", "run_id", runs[0]["run_id"])])
    return {str(r["twin_id"]): {k: int(v) for k, v in dict(r["answers"]).items()} for r in rows}


async def _baseline_vectors(
    twin_ids: list[str], db: DbBackend, ref: ReferenceData
) -> dict[str, dict[str, int]]:
    """Each twin's **own driver's** battery answers — every driver is their own control.

    A twin missing any battery item is dropped rather than completed from anywhere (I17): a metric
    is never computed over a subset (`docs/07` §2.3).
    """
    battery = ref.battery_item_ids
    out: dict[str, dict[str, int]] = {}
    for twin_id in twin_ids:
        answers = await _human_answers(twin_id, db)
        vector = {i: answers[i] for i in battery if i in answers}
        if len(vector) == len(battery):
            out[twin_id] = vector
    return out


async def _median_live_shift(session_id: str, db: DbBackend) -> float | None:
    """The median |index| over this session's completed non-control cells. `docs/08` §4 test 2."""
    rows = await db.select(
        "runs", [("eq", "session_id", session_id), ("eq", "status", "completed")]
    )
    live = sorted(
        abs(float(r["index_value"]))
        for r in rows
        if r.get("index_value") is not None
        and r.get("version_code") not in (CONTROL_CODE, SHAM_CODE)
    )
    if not live:
        return None
    mid = len(live) // 2
    return live[mid] if len(live) % 2 else (live[mid - 1] + live[mid]) / 2


# ------------------------------------------------------------------------- the pairing


def pair_with_another(twin_ids: list[str], *, seed: int) -> dict[str, str]:
    """Pair every twin with a **different** twin, reproducibly. `docs/08` §4 test 1.

    A seeded rotation rather than a shuffle: it is random in the offset, exactly reproducible from
    the session's own panel seed, and **structurally a derangement** — nobody can be paired with
    themselves, which would silently turn the test's "other driver" error into its "own driver"
    error and report a gap of zero as a `FAIL`.
    """
    ids = sorted(twin_ids)
    if len(ids) < 2:
        return {}
    offset = random.Random(seed).randrange(1, len(ids))
    return {t: ids[(i + offset) % len(ids)] for i, t in enumerate(ids)}


# ------------------------------------------------------------------------ appending a row


async def append_result(
    outcome: ValidityOutcome,
    *,
    session_id: str | None = None,
    backend: DbBackend | None = None,
    mode: str | None = None,
    provider: str = "ollama",
    config_version: int = 1,
) -> dict:
    """Append one `validity_results` row. **Insert only** (I9) — nothing here updates.

    The zero-twin rule is checked once more immediately before the write. It is already
    unconstructible on :class:`ValidityOutcome` and rejected by the database, and it is checked
    here too because this is the line the prototype's defect went through.
    """
    db = backend or get_backend()
    if outcome.twins_n == 0 and outcome.verdict != "INCONCLUSIVE":
        raise ValidityRunError(
            f"refusing to store {outcome.verdict} on zero twins for {outcome.test_id}: a test "
            "that ran on nobody concluded nothing (I15)."
        )
    live = bool(settings.ollama_api_key)
    rows = await db.insert(
        "validity_results",
        [{
            "test_id": outcome.test_id,
            "session_id": session_id,
            "twins_n": outcome.twins_n,
            "mode": mode or ("live" if live else "mock"),
            "provider": provider,
            # The model(s) the test actually compared, or — for a test that made no call, which
            # includes every `INCONCLUSIVE` row — the model this installation is configured with.
            # Writing `mock` there while `mode` reads `live` would put two contradictory facts on
            # one row of evidence.
            "model": (
                " + ".join(outcome.models)
                if outcome.models
                else (settings.twinlab_model if live else MOCK_MODEL)
            ),
            "temperature": outcome.temperature,
            "statistics": dict(outcome.statistics),
            "verdict": outcome.verdict,
            "headline": outcome.headline,
            "detail": outcome.detail,
            "config_version": config_version,
        }],
    )
    return dict(rows[0])


async def record_temperature_recommendation(
    recommendation: TemperatureRecommendation, *, backend: DbBackend | None = None
) -> None:
    """Store test 8's recommendation under its **own** key. `docs/02` §7.3.

    `TwinConfig.temperature` is untouched on purpose. It is frozen onto every session's config, so
    a test that changed it would retroactively make two sessions incomparable with nothing in the
    data saying why. The researcher applies the recommendation deliberately, from Settings.
    """
    if recommendation.recommended is None:
        return
    db = backend or get_backend()
    await db.upsert(
        "app_config",
        [{
            "key": TEMPERATURE_RECOMMENDATION_KEY,
            "value": recommendation.model_dump(),
        }],
        on_conflict="key",
    )


# ------------------------------------------------------------------------ the eight runs


def enqueue_validity_test(number: int, **kwargs: Any) -> asyncio.Task[ValidityOutcome]:
    """Hand a validity test to the event loop and return at once. `CLAUDE.md` rule 12.

    The six tests that need fresh twin calls must never run inside a Gradio handler's synchronous
    path — at `3N` calls test 8 is a twenty-minute action at one concurrent request. The task keeps
    running if the researcher changes tab, exactly as a session does, and the appended row is how
    the screen learns it finished.
    """
    return asyncio.create_task(run_validity_test(number, **kwargs))


async def run_validity_test(
    number: int,
    *,
    session_id: str | None = None,
    backend: DbBackend | None = None,
    ask: AskTwins | None = None,
    second_model_name: str | None = None,
    version_code: str | None = None,
    append: bool = True,
) -> ValidityOutcome:
    """Run one validity test and append its result. `docs/08` §4.

    ``ask`` is the live twin call, injected like `SessionRunner`'s. **Tests 1 and 3 never receive
    it and never reference it**: they re-score stored vectors, which is why `docs/08` §4 gives them
    a cost of zero and why `docs/11` M13 asserts that against the call counter.

    A test that cannot run returns `INCONCLUSIVE` and — because `INCONCLUSIVE` is a result about
    the test, not an error — is still appended, so the attempt is in the log.
    """
    if number not in vt.TEST_IDS:
        raise ValidityRunError(f"there are eight validity tests; {number} is not one of them")
    db = backend or get_backend()
    ref = reference()
    if session_id is None:
        from twinlab.services.runs import latest_session_id

        session_id = await latest_session_id(db)

    if number == 1:
        outcome = await _test1(db, ref, session_id)
    elif number == 3:
        outcome = await _test3(db, ref)
    else:
        outcome = await _live_test(
            number,
            db=db,
            ref=ref,
            session_id=session_id,
            ask=ask,
            second_model_name=second_model_name,
            version_code=version_code,
        )

    if append:
        await append_result(outcome, session_id=session_id, backend=db)
    return outcome


# ---------------------------------------------------------------- test 1: wrong person


async def _test1(
    db: DbBackend, ref: ReferenceData, session_id: str | None
) -> ValidityOutcome:
    """Test 1 end to end, **with no model call anywhere in this function.**"""
    h2_items = ref.holdout_h2_item_ids
    twin_vectors = await h2_vectors(db)
    if not twin_vectors:
        return vt.inconclusive(
            1,
            "no twin has a stored H2 answer vector. Run the quality gate first; this test "
            "re-scores what it stored and makes no new calls (docs/08 §4 test 1).",
        )

    seed = 0
    if session_id is not None:
        rows = await db.select("sessions", [("eq", "session_id", session_id)], limit=1)
        seed = int(rows[0].get("panel_seed") or 0) if rows else 0
    pairs = pair_with_another(sorted(twin_vectors), seed=seed)
    if not pairs:
        return vt.inconclusive(
            1, "only one twin has an H2 vector, so there is no other driver to pair it with"
        )

    own_errors: dict[str, float] = {}
    other_errors: dict[str, float] = {}
    for twin_id, vector in twin_vectors.items():
        other_id = pairs.get(twin_id)
        if other_id is None:
            continue
        own = vt.mae(vector, await _human_answers(twin_id, db), h2_items)
        other = vt.mae(vector, await _human_answers(other_id, db), h2_items)
        # Both or neither. A twin scored against only one side is not a paired observation, and
        # pairing it with a mean from elsewhere would be imputation (I17).
        if own is None or other is None:
            continue
        own_errors[twin_id] = own
        other_errors[twin_id] = other

    return vt.wrong_person(
        own_errors=own_errors, other_errors=other_errors, model=settings.model_badge
    )


# ------------------------------------------------------------- test 3: simple guesses


async def _test3(db: DbBackend, ref: ReferenceData) -> ValidityOutcome:
    """Test 3 end to end, **with no model call anywhere in this function.**

    The two naive predictors are `docs/08` §4's. Both are built from the H2 items' `mirrors` link:
    an H2 item mirrors a battery item by construction (`docs/01` §3.5), so the human's answer to
    the mirrored item **is** their unchanged baseline for that H2 item.
    """
    h2_items = ref.holdout_h2_item_ids
    mirrors = {i: ref.items[i].mirrors for i in h2_items if ref.items[i].mirrors}
    if not mirrors:
        return vt.inconclusive(
            3, "no H2 item names the battery item it mirrors, so there is no baseline predictor"
        )

    twin_vectors = await h2_vectors(db)
    if not twin_vectors:
        return vt.inconclusive(
            3, "no twin has a stored H2 answer vector. Run the quality gate first."
        )

    humans: dict[str, dict[str, int]] = {}
    arms: dict[str, str] = {}
    for twin_id in twin_vectors:
        humans[twin_id] = await _human_answers(twin_id, db)
        submission = await _submission_id(twin_id, db)
        rows = await db.select(
            "survey_submissions", [("eq", "submission_id", submission)], limit=1
        )
        arms[twin_id] = str((rows[0].get("arm") if rows else None) or "")

    twin_errors: dict[str, float] = {}
    nochange_errors: dict[str, float] = {}
    groupshift_errors: dict[str, float] = {}
    for twin_id, vector in twin_vectors.items():
        human = humans[twin_id]
        nochange = {i: human[m] for i, m in mirrors.items() if m in human}
        shift = _group_shift(twin_id, arms, humans, mirrors)
        groupshift = {
            i: nochange[i] + shift[i] for i in nochange if i in shift
        }
        errors = (
            vt.mae(vector, human, h2_items),
            vt.mae(nochange, human, h2_items),
            # `groupshift` is a predicted value and may be fractional; `mae` takes the same
            # arithmetic either way and the rounding stays out of it.
            vt.mae(groupshift, human, h2_items),  # type: ignore[arg-type]
        )
        if any(e is None for e in errors):
            continue
        twin_errors[twin_id], nochange_errors[twin_id], groupshift_errors[twin_id] = errors  # type: ignore[assignment]

    return vt.simple_guesses(
        twin_errors=twin_errors,
        nochange_errors=nochange_errors,
        groupshift_errors=groupshift_errors,
        model=settings.model_badge,
    )


def _group_shift(
    twin_id: str,
    arms: dict[str, str],
    humans: dict[str, dict[str, int]],
    mirrors: dict[str, str],
) -> dict[str, float]:
    """The mean H2-minus-baseline shift of **the other** respondents in the same arm.

    "Other" is not a nicety: including the twin's own driver would leak the answer being predicted
    into the predictor and make the naive baseline artificially strong.
    """
    peers = [t for t, a in arms.items() if a and a == arms.get(twin_id) and t != twin_id]
    out: dict[str, float] = {}
    for item, mirrored in mirrors.items():
        deltas = [
            humans[p][item] - humans[p][mirrored]
            for p in peers
            if item in humans[p] and mirrored in humans[p]
        ]
        if deltas:
            out[item] = sum(deltas) / len(deltas)
    return out


# ----------------------------------------------------------------- tests 2, 4, 5, 6, 7, 8


async def _live_test(
    number: int,
    *,
    db: DbBackend,
    ref: ReferenceData,
    session_id: str | None,
    ask: AskTwins | None,
    second_model_name: str | None,
    version_code: str | None,
) -> ValidityOutcome:
    """The six tests that need fresh twin calls. `docs/08` §4's table: N, N, 2N, N, N, 3N.

    Each begins by establishing the `00000` noise floor, because five of the six judge against it
    and a floor that was never measured is not assumed (`docs/07` §6).
    """
    floor = await noise_floor(session_id, db)
    if session_id is None:
        return vt.inconclusive(number, "no session has been run, so there is nothing to test")

    if number == 2:
        return await _test2(db, ref, session_id, floor, ask)
    if ask is None:
        return vt.inconclusive(
            number,
            f"test {number} needs {vt.CALLS_PER_TWIN[number]} fresh twin call(s) per twin and no "
            "live twin path is wired yet (docs/08 §4)",
        )
    # Tests 4-8 are wired behind the same injected call; each assembles its own stimulus and
    # compares against the same baseline vectors, and each is reached only with a live `ask`.
    return await _test_with_calls(
        number,
        db=db,
        ref=ref,
        session_id=session_id,
        floor=floor,
        ask=ask,
        second_model_name=second_model_name,
        version_code=version_code,
    )


async def _test2(
    db: DbBackend,
    ref: ReferenceData,
    session_id: str,
    floor: float | None,
    ask: AskTwins | None,
) -> ValidityOutcome:
    """Test 2 — the placebo. `docs/08` §4 test 2.

    `SHAM` is one of the two control cells every fresh session runs before its sweep
    (`docs/03` §6.1), so its answers are normally already stored and this test costs nothing extra.
    That is the cache the whole orchestrator is built on, not a shortcut: the vectors were produced
    by the same twins, the same stimulus and the same model.
    """
    variant = await _run_answers(session_id, SHAM_CODE, db)
    if not variant and ask is not None:
        variant = await ask(twin_ids=[], paragraphs={}, purpose="sham")
    if not variant:
        return vt.inconclusive(
            2,
            "this session has no completed SHAM control. SHAM runs once per session before the "
            "sweep (docs/03 §6.1); run the session first.",
        )

    baselines = await _baseline_vectors(sorted(variant), db, ref)
    twins = sorted(set(baselines) & set(variant))
    if not twins:
        return vt.inconclusive(
            2, "no twin answered SHAM and also has a complete baseline of its own to move from"
        )

    shifts, per_twin = _shifts_and_moves(baselines, variant, twins, ref)
    return vt.placebo_change(
        sham_shifts=shifts,
        per_twin_abs_move=per_twin,
        noise_floor=floor,
        median_live_shift=await _median_live_shift(session_id, db),
        model=settings.model_badge,
    )


def _shifts_and_moves(
    baselines: dict[str, dict[str, int]],
    variant: dict[str, dict[str, int]],
    twins: list[str],
    ref: ReferenceData,
) -> tuple[dict[str, float], dict[str, float]]:
    """Six mean metric shifts, and each twin's own mean absolute movement.

    **One twin set, used for both sides** (`docs/07` §3.1). Computing the baseline over everybody
    and the variant over the survivors makes every failure look like an effect.
    """
    shifts: dict[str, float] = {}
    per_twin: dict[str, float] = {t: 0.0 for t in twins}
    moves: dict[str, list[float]] = {t: [] for t in twins}
    for metric in ref.metrics:
        deltas = [
            score(variant[t], metric, ref) - score(baselines[t], metric, ref) for t in twins
        ]
        shifts[metric] = round(sum(deltas) / len(deltas), 4)
        for twin_id, delta in zip(twins, deltas, strict=True):
            moves[twin_id].append(abs(delta))
    for twin_id, values in moves.items():
        per_twin[twin_id] = sum(values) / len(values)
    return shifts, per_twin


def _index_per_twin(
    baselines: dict[str, dict[str, int]],
    variant: dict[str, dict[str, int]],
    twins: list[str],
    ref: ReferenceData,
) -> dict[str, float]:
    """Each twin's own index for a cell. `docs/07` §4, applied one twin at a time."""
    out: dict[str, float] = {}
    for twin_id in twins:
        base = score_all(baselines[twin_id], ref)
        after = score_all(variant[twin_id], ref)
        out[twin_id] = compute_index(
            {m: after[m] - base[m] for m in base}, ref=ref
        )
    return out


async def _test_with_calls(
    number: int,
    *,
    db: DbBackend,
    ref: ReferenceData,
    session_id: str,
    floor: float | None,
    ask: AskTwins,
    second_model_name: str | None,
    version_code: str | None,
) -> ValidityOutcome:
    """Tests 4-8. Each puts a stimulus to the panel through ``ask`` and compares in Python.

    Nothing here interprets a model's prose. ``ask`` returns validated answer vectors — the output
    contract has already run (I13) — and every number below is computed from those integers (I12).
    """
    code = version_code or settings.start_code
    paragraphs = await _paragraphs_for(code, db)
    baseline_ids: list[str] = []
    panel = await db.select("session_panel", [("eq", "session_id", session_id)])
    baseline_ids = [str(r["twin_id"]) for r in panel]
    if not baseline_ids:
        return vt.inconclusive(number, "this session has no frozen panel to put a stimulus to")
    baselines = await _baseline_vectors(baseline_ids, db, ref)
    if not baselines:
        return vt.inconclusive(
            number, "no twin on the panel has a complete baseline of its own to move from"
        )
    twin_ids = sorted(baselines)
    temperature = _temperature()

    if number == 4:
        # The probe goes straight to the twins and nowhere else. There is deliberately no call
        # to `VariantRepo.put` on this path, and `assert_not_a_probe` guards that repo so a future
        # one would be refused rather than quietly filed (`docs/08` §4 test 4).
        probe = vt.contradictory_probe(ordinary_paragraphs=paragraphs)
        answers = await ask(
            twin_ids=twin_ids,
            paragraphs=dict(probe.paragraphs),
            purpose="probe",
            temperature=temperature,
        )
        twins = sorted(set(answers) & set(baselines))
        if not twins:
            return vt.inconclusive(4, "no twin answered the contradictory probe")
        per_twin = {
            t: score(answers[t], "happiness", ref) - score(baselines[t], "happiness", ref)
            for t in twins
        }
        return vt.impossible_version(
            happiness_shift=vt.mean(list(per_twin.values())),
            per_twin_happiness_shift=per_twin,
            noise_floor=floor,
            model=settings.model_badge,
            temperature=temperature,
        )

    if number == 5:
        first = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="order",
            wording="A", reverse_order=True, temperature=temperature,
        )
        second = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="wording",
            wording="B", reverse_order=False, temperature=temperature,
        )
        twins = sorted(set(first) & set(second) & set(baselines))
        if not twins:
            return vt.inconclusive(5, "no twin answered both presentations of the cell")
        diff = {
            m: sum(abs(score(first[t], m, ref) - score(second[t], m, ref)) for t in twins)
            / len(twins)
            for m in ref.metrics
        }
        own, _ = _shifts_and_moves(baselines, first, twins, ref)
        return vt.order_and_wording(
            diff_per_metric=diff,
            twins_n=len(twins),
            noise_floor=floor,
            cell_own_shift=sum(abs(v) for v in own.values()) / len(own),
            model=settings.model_badge,
            temperature=temperature,
        )

    if number == 6:
        fairness_items = [i.item_id for i in ref.block_items("FAIR")]
        with_answers = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="fairness_with",
            temperature=temperature,
        )
        ablated = await _ablated_personas(twin_ids, fairness_items, db)
        without_answers = await ask(
            twin_ids=sorted(ablated),
            paragraphs=paragraphs,
            purpose="fairness_without",
            personas={k: v.text for k, v in ablated.items()},
            temperature=temperature,
        )
        twins = sorted(set(with_answers) & set(without_answers))
        if not twins:
            return vt.inconclusive(6, "no twin answered both with and without its fairness clauses")
        return vt.ablation(
            fairness_with={t: score(with_answers[t], "fairness", ref) for t in twins},
            fairness_without={t: score(without_answers[t], "fairness", ref) for t in twins},
            noise_floor=floor,
            model=settings.model_badge,
            temperature=temperature,
        )

    if number == 7:
        other = second_model_name or ""
        if not other:
            return vt.inconclusive(
                7, "no second model was named; test 7 compares two models by name (docs/08 §4)"
            )
        first = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="model_a",
            model=settings.twinlab_model, temperature=temperature,
        )
        second = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="model_b",
            model=other, temperature=temperature,
        )
        twins = sorted(set(first) & set(second) & set(baselines))
        if not twins:
            return vt.inconclusive(
                7, f"no twin answered the same cell on both {settings.twinlab_model} and {other}"
            )
        shifts_a, _ = _shifts_and_moves(baselines, first, twins, ref)
        shifts_b, _ = _shifts_and_moves(baselines, second, twins, ref)
        return vt.second_model(
            index_a=_index_per_twin(baselines, first, twins, ref),
            index_b=_index_per_twin(baselines, second, twins, ref),
            shifts_a=shifts_a,
            shifts_b=shifts_b,
            model_a=settings.twinlab_model,
            model_b=other,
            temperature=temperature,
        )

    # number == 8
    index_by_temp: dict[float, dict[str, float]] = {}
    shifts_by_temp: dict[float, dict[str, float]] = {}
    for temp in vt.TEMPERATURES:
        answers = await ask(
            twin_ids=twin_ids, paragraphs=paragraphs, purpose="temperature", temperature=temp,
        )
        twins = sorted(set(answers) & set(baselines))
        if not twins:
            continue
        index_by_temp[temp] = _index_per_twin(baselines, answers, twins, ref)
        shifts_by_temp[temp], _ = _shifts_and_moves(baselines, answers, twins, ref)
    outcome, recommendation = vt.temperature_sweep(
        index_by_temp=index_by_temp,
        shifts_by_temp=shifts_by_temp,
        noise_floor=floor,
        model=settings.model_badge,
    )
    await record_temperature_recommendation(recommendation, backend=db)
    return outcome


def _temperature() -> float:
    from twinlab.services.config import load_twin_config

    return load_twin_config().temperature


async def _paragraphs_for(version_code: str, db: DbBackend) -> dict[str, str]:
    """The stored, Checker-passed paragraphs for a cell. ``{}`` when it has never been rendered.

    Read from `variants`, never re-rendered here: **`ParagraphPool` is the only thing that may
    render a paragraph and `check_variant` the only thing that may declare one usable** (I3).
    """
    # Both halves of `(version_code, style_version)`: these paragraphs go straight to a twin
    # (tests 4-8), and a stimulus verified under another style contract is not verified for this
    # one. See `services/studio._stimulus` for the same fix.
    rows = await db.select(
        "variants",
        [("eq", "version_code", version_code), ("eq", "style_version", settings.style_version)],
        order=("created_at", True),
        limit=1,
    )
    if not rows:
        return {}
    out: dict[str, str] = {}
    for lever, entry in dict(rows[0].get("paragraphs") or {}).items():
        out[lever] = entry.get("text", "") if isinstance(entry, dict) else str(entry)
    return out


async def _ablated_personas(
    twin_ids: list[str], fairness_items: list[str], db: DbBackend
) -> dict[str, AblatedPersona]:
    """Build test 6's ablated personas. **Never written anywhere** — they live for one call.

    A twin whose persona carries no recognisable fairness clause is skipped rather than "ablated"
    into an identical passage: `ablate_persona` raises on a no-op, and a no-op ablation would make
    test 6 compare a twin with itself and report `CHECK` forever.
    """
    out: dict[str, AblatedPersona] = {}
    for twin_id in twin_ids:
        rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
        passage = str((rows[0].get("persona_passage") if rows else None) or "")
        if not passage:
            continue
        try:
            out[twin_id] = vt.ablate_persona(
                twin_id=twin_id, persona_text=passage, fairness_item_ids=fairness_items
            )
        except vt.ValidityInputError:
            continue
    return out


__all__ = [
    "H2_ANSWERS_KEY",
    "assert_not_a_probe",
    "assert_not_ablated",
    "MOCK_MODEL",
    "TEMPERATURE_RECOMMENDATION_KEY",
    "AskTwins",
    "ValidityRunError",
    "append_result",
    "calls_for",
    "enqueue_validity_test",
    "h2_vectors",
    "noise_floor",
    "pair_with_another",
    "record_temperature_recommendation",
    "run_validity_test",
    "validity_budget_view",
]
