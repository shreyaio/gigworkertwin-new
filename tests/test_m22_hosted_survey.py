"""The hosted questionnaire: the instrument contract, intake ordering and the twin it produces.

The property every test here circles is that **the hosted page is a third client of one intake
contract, not a second pipeline**. If that holds, a hosted submission and a Google Form submission
are the same record built by the same code, and everything already proven about the second is true
of the first. If it stops holding, these tests say where.

No live LLM and no live database (`CLAUDE.md` → Testing). The persona path has no model call in it
at all, which is why an end-to-end test of it is possible at this speed.
"""

from __future__ import annotations

import json

import pytest

from twinlab.db.client import InMemoryStorage, StorageError
from twinlab.ingest.reference_store import reference
from twinlab.ingest.survey_intake import StorageFailed, form_map
from twinlab.models.reference import ATTENTION_ITEMS
from twinlab.services.hosted_survey import AlreadySubmitted, submit, twin_gate
from twinlab.survey.instrument import hosted_instrument
from twinlab.survey.payload import build_payload, new_progress

EXCLUDE_SCREENS = ("screen:uber_employee", "screen:earlier_stage", "screen:deactivated")


def _filled(**overrides):
    """A complete, eligible, consenting questionnaire. ``overrides`` are by map key."""
    instrument = hosted_instrument()
    ref = reference()
    progress = new_progress()
    # Read off each check's own stem, exactly as intake does (I10) — never hard-coded here, so a
    # re-worded check cannot leave the fixture scoring against a number nobody was asked for.
    import re

    attention = {
        item_id: int(re.search(r"select\s+(\d+)", ref.items[item_id].stem, re.I).group(1))
        for item_id in ATTENTION_ITEMS
    }
    for q in instrument.questions:
        if q.kind == "likert":
            progress.answers[q.key] = attention.get(q.target, 4)
        elif q.kind == "yes_no":
            progress.answers[q.key] = "No" if q.target in EXCLUDE_SCREENS else "Yes"
        elif q.kind == "consent":
            progress.answers[q.key] = True
        elif q.kind == "choice":
            progress.answers[q.key] = q.options[0]
        elif q.kind == "integer":
            progress.answers[q.key] = 3
        elif q.kind == "decimal":
            progress.answers[q.key] = 2.0
        else:
            progress.answers[q.key] = "In my own words."
    progress.answers.update(overrides)
    return progress


def _key_for(target: str) -> str:
    return next(q.key for q in hosted_instrument().questions if q.target == target)


# --------------------------------------------------------------------- the instrument contract


def test_the_hosted_questionnaire_and_the_form_map_are_the_same_instrument() -> None:
    """The bijection. Both directions, because they fail differently and both are silent.

    A drawn-but-unmapped question is rejected at intake *after* the driver answered it; a
    mapped-but-undrawn one is a question missing from the instrument with nothing to notice it.
    """
    assert hosted_instrument().keys == frozenset(form_map())


def test_every_question_claims_the_target_the_map_gives_it() -> None:
    mapping = form_map()
    for question in hosted_instrument().questions:
        assert mapping[question.key] == question.target, question.key


def test_no_question_is_drawn_twice() -> None:
    """Two controls on one map key means one answer silently overwrites the other."""
    keys = [q.key for q in hosted_instrument().questions]
    assert len(keys) == len(set(keys)) == 146


def test_a_likert_item_is_drawn_with_its_own_number_of_points() -> None:
    """The register is the only source of a scale's range (`docs/02` §4.2 rule 6).

    The prototype asked every item on 1–7 while three of its nine constructs were 5-point. A
    5-point item drawn with seven boxes collects answers that cannot exist.
    """
    ref = reference()
    likert = [q for q in hosted_instrument().questions if q.kind == "likert"]
    assert len(likert) == len(ref.items) == 73
    for q in likert:
        assert q.points == ref.scales[ref.items[q.target].scale_id].points
    assert {q.points for q in likert} == {5, 7}, "both ranges must actually occur"


def test_holdout_material_is_one_contiguous_stop() -> None:
    """Parts 15–17 sit together. I6 is easier to keep when the holdout is one block."""
    ref = reference()
    instrument = hosted_instrument()
    holdout_stops = {
        stop.index
        for stop in instrument.stops
        for q in stop.questions
        if q.target in ref.items and ref.items[q.target].part in (16, 17)
    }
    assert holdout_stops == {instrument.stops[-1].index}


# --------------------------------------------------------------------------- the payload


def test_every_question_reaches_the_payload_even_unanswered() -> None:
    """A skip travels as an explicit null. "Asked and declined" is different evidence from
    "never asked", and the raw object is the immutable record of which happened."""
    progress = new_progress()
    progress.answers[_key_for("AMQ1")] = 6
    payload = build_payload(progress)

    assert len(payload["answers"]) == 146
    answered = [a for a in payload["answers"] if a["value"] is not None]
    assert len(answered) == 1 and answered[0]["value"] == 6


def test_the_payload_matches_the_shape_the_apps_script_sends() -> None:
    """Same keys, same grouping — which is what lets `build_rows` read both."""
    payload = build_payload(_filled())
    assert {"response_id", "submitted_at", "answers"} <= set(payload)
    sent = {f"{a['section']}|{a['title']}" for a in payload["answers"]}
    assert sent == frozenset(form_map())


def test_a_blank_number_is_never_a_zero() -> None:
    """Zero is a real answer to "how many people depend on your earnings"."""
    progress = new_progress()
    progress.answers[_key_for("background:dependants")] = ""
    payload = build_payload(progress)
    value = next(
        a["value"] for a in payload["answers"]
        if a["title"] == "How many people depend on your earnings?"
    )
    assert value is None


# --------------------------------------------------------------------------- intake ordering


async def test_a_failed_insert_leaves_a_replayable_object(backend) -> None:
    """I16 — the raw object is written **before** any table row, so a failed insert is recoverable.

    The inverse is the failure intake cannot make safe: a submission that was accepted on screen,
    failed to insert, and left nothing behind.
    """
    storage = InMemoryStorage()

    async def _explode(*_a, **_k):
        raise RuntimeError("upsert refused")

    backend.upsert = _explode  # type: ignore[method-assign]
    progress = _filled()

    with pytest.raises(RuntimeError):
        await submit(progress, backend=backend, storage=storage)

    path = f"raw/survey_{progress.response_id}.json"
    stored = json.loads(await storage.get(path))
    assert len(stored["answers"]) == 146, "the driver's answers survived the failed insert"


async def test_a_storage_failure_writes_no_row(backend) -> None:
    """The other half of I16: if the mirror cannot be written, nothing is half-recorded."""

    class _DeadStorage(InMemoryStorage):
        async def put(self, path: str, body: str) -> None:
            raise StorageError("bucket unreachable")

    with pytest.raises(StorageFailed):
        await submit(_filled(), backend=backend, storage=_DeadStorage())

    assert await backend.count("survey_submissions") == 0
    assert await backend.count("survey_answers") == 0


async def test_sending_twice_is_refused(backend) -> None:
    """One driver's record is the one they pressed send on; a second send could differ."""
    progress = _filled()
    await submit(progress, backend=backend, storage=InMemoryStorage())
    progress.submitted = True
    with pytest.raises(AlreadySubmitted):
        await submit(progress, backend=backend, storage=InMemoryStorage())


# --------------------------------------------------------------------------- end to end


async def test_a_complete_questionnaire_becomes_a_twin_with_a_persona(backend) -> None:
    """The whole point: answers in, a twin with a deterministic persona out, no model call."""
    storage = InMemoryStorage()
    receipt = await submit(_filled(), backend=backend, storage=storage)

    assert receipt.outcome == "complete"
    assert receipt.consented and receipt.consent_twin and receipt.eligible
    assert receipt.attention_passed
    assert receipt.battery_answered == receipt.battery_expected == 37
    assert receipt.twin_id and receipt.persona_hash

    twins = await backend.select("twins", None)
    assert len(twins) == 1
    assert twins[0]["persona_hash"] == receipt.persona_hash
    assert twins[0]["persona_passage"].startswith("Who I am")
    # Part 14 is the reason `twins.background` exists; without it the persona loses the driver's
    # own words (`docs/01` §6.2).
    assert len(twins[0]["background"]["own_words"]) == 5


async def test_the_persona_carries_no_holdout_answer(backend) -> None:
    """I6. The holdouts are how a twin is scored, never what it is told.

    Asserted on ``items_used`` rather than on the prose: Part 16 re-asks Part 7's and Part 11's
    questions **in the same words**, so a substring search for a holdout stem matches the
    legitimate non-holdout clause and proves nothing.
    """
    from twinlab.persona.builder import build_persona
    from twinlab.persona.from_payload import twin_from_payload

    ref = reference()
    progress = _filled()
    payload = build_payload(progress)
    twin, response = twin_from_payload(
        {"submission_id": progress.response_id, "raw_object_path": "raw/x.json"},
        payload, ref, data_type="REAL", source="real",
    )
    passage = build_persona(twin, response, ref)

    assert len(response.answers) == 73, "the response carries the holdouts for the quality gate"
    assert len(passage.items_used) == 37
    assert not [i for i in passage.items_used if i.startswith(("H2_", "H3_"))]


async def test_the_same_answers_always_build_the_same_persona(backend) -> None:
    """Determinism is what ties a result back to the text that produced it (I11)."""
    from twinlab.persona.builder import build_persona
    from twinlab.persona.from_payload import twin_from_payload

    ref = reference()
    hashes = set()
    for _ in range(2):
        progress = _filled()
        progress.response_id = "web_fixed"  # the id is the only thing that would differ
        payload = build_payload(progress, submitted_at="2026-10-08T00:00:00.000Z")
        twin, response = twin_from_payload(
            {"submission_id": "web_fixed", "raw_object_path": "raw/x.json"},
            payload, ref, data_type="REAL", source="real",
        )
        hashes.add(build_persona(twin, response, ref).persona_hash)
    assert len(hashes) == 1


# --------------------------------------------------------------------------- the gates


async def test_withholding_consent_seven_records_the_driver_and_builds_no_twin(backend) -> None:
    """Statement 7 is its own gate: a driver may consent to the research and decline the twin."""
    twin_key = _key_for("consent:twin")
    receipt = await submit(
        _filled(**{twin_key: False}), backend=backend, storage=InMemoryStorage()
    )

    assert receipt.twin_id is None
    assert "statement 7" in receipt.twin_note
    assert await backend.count("survey_submissions") == 1, "the respondent is still recorded"
    assert await backend.count("twins") == 0


async def test_a_partial_battery_is_recorded_and_builds_no_twin(backend) -> None:
    """A persona must be lossless over all 37 items (I6); it is not built from a partial row."""
    receipt = await submit(
        _filled(**{_key_for("FAIR2"): None}), backend=backend, storage=InMemoryStorage()
    )

    assert receipt.outcome == "partial"
    assert receipt.battery_answered == 36
    assert receipt.twin_id is None
    assert "'partial'" in receipt.twin_note
    assert await backend.count("twins") == 0


async def test_an_ineligible_respondent_is_recorded_and_builds_no_twin(backend) -> None:
    receipt = await submit(
        _filled(**{_key_for("screen:in_india"): "No"}),
        backend=backend, storage=InMemoryStorage(),
    )
    assert receipt.eligible is False
    assert receipt.twin_id is None
    assert await backend.count("survey_submissions") == 1


async def test_a_failed_attention_check_is_recorded_not_excluded(backend) -> None:
    """Recorded as a data-quality flag. Excluding on it is a research decision not yet made."""
    receipt = await submit(
        _filled(**{_key_for("AMQ6"): 7}), backend=backend, storage=InMemoryStorage()
    )
    assert receipt.attention_passed is False
    assert receipt.twin_id, "the attention check does not gate the twin"


async def test_the_hosted_gate_and_the_bulk_import_gate_are_one_rule(backend) -> None:
    """`twin_gate` is what `importable_submissions` applies, so the two paths cannot drift."""
    from twinlab.services.lab import importable_submissions

    storage = InMemoryStorage()
    await submit(_filled(), backend=backend, storage=storage, build_twin=False)
    await submit(
        _filled(**{_key_for("consent:twin"): False}),
        backend=backend, storage=storage, build_twin=False,
    )

    rows = await backend.select("survey_submissions", None)
    assert len(rows) == 2
    passing = [r for r in rows if twin_gate(r) is None]
    assert len(passing) == 1

    importable = await importable_submissions("Real and synthetic", backend)
    assert [r["submission_id"] for r in importable] == [
        r["submission_id"] for r in passing
    ]


async def test_build_twin_false_stores_the_record_and_stops(backend) -> None:
    receipt = await submit(
        _filled(), backend=backend, storage=InMemoryStorage(), build_twin=False
    )
    assert receipt.twin_id is None
    assert await backend.count("survey_submissions") == 1
    assert await backend.count("twins") == 0


# --------------------------------------------------------------------------- the page


def test_the_page_builds_and_draws_one_control_per_question() -> None:
    """A question with no control is a question a driver cannot answer."""
    import gradio as gr

    from twinlab.ui.components import drain_pending_loads
    from twinlab.ui.pages.survey_take import render_survey_take

    with gr.Blocks() as demo:
        render_survey_take("badge")
        drain_pending_loads(demo)

    inputs = [
        c for c in demo.blocks.values()
        if isinstance(c, (gr.Radio, gr.Checkbox, gr.Number, gr.Textbox))
    ]
    assert len(inputs) == 146


def test_no_control_is_pre_selected() -> None:
    """A pre-selected midpoint is indistinguishable from a driver who chose it."""
    import gradio as gr

    from twinlab.ui.pages.survey_take import render_survey_take

    with gr.Blocks() as demo:
        render_survey_take(None)

    for c in demo.blocks.values():
        if isinstance(c, (gr.Radio, gr.Number, gr.Textbox)):
            assert c.value is None, f"{type(c).__name__} came pre-filled with {c.value!r}"
        if isinstance(c, gr.Checkbox):
            assert c.value is False


# --------------------------------------------------------------------------- the why-probe layer


def test_there_is_one_why_probe_per_battery_item() -> None:
    """`SURVEY_SCALES_AND_WHY_PROBES.md` §3.1.

    `WHY_PROBE_IDS` is hard-coded in `models/twin.py` because `models/` is the bottom layer and
    may not import `ingest/` at module scope. This is the test that stops the hard-coded list and
    the frozen register drifting apart.
    """
    from twinlab.models.twin import WHY_PROBE_ANCHOR, WHY_PROBE_IDS

    battery = set(reference().battery_item_ids)
    assert set(WHY_PROBE_ANCHOR) == set(WHY_PROBE_IDS)
    assert set(WHY_PROBE_ANCHOR.values()) == battery, "every battery item has exactly one probe"
    assert len(WHY_PROBE_ANCHOR) == len(battery) == 37


def test_every_probe_has_a_persona_prompt() -> None:
    """A probe with no prompt would be an answer the passage cannot phrase (rule 7)."""
    from twinlab.models.twin import WHY_PROBE_IDS
    from twinlab.persona.templates import WHY_PROBE_PROMPTS

    assert set(WHY_PROBE_PROMPTS) == set(WHY_PROBE_IDS)


def test_probes_are_drawn_only_where_the_spec_puts_them() -> None:
    """§3.2 — no probe on an attention check, a screener, a demographic or a counterfactual block.

    The exclusions matter for different reasons. An attention check has no experiential content to
    explain. The Part 16 and 17 blocks are hypotheticals, and asking a human to justify one adds
    length without adding persona — and both are holdout, so a why there could never be used.
    """
    ref = reference()
    probed = {q.why_for_item for q in hosted_instrument().questions if q.is_why}

    assert probed == set(ref.battery_item_ids)
    for item_id in probed:
        item = ref.items[item_id]
        assert not item.attention_check
        assert item.part not in (15, 16, 17)


def test_the_probe_wording_is_identical_across_every_item() -> None:
    """Constant by design: a per-item wording would cue content, and a valenced one would bias
    the persona toward grievance and propagate into every counterfactual the twin answers."""
    shown = {q.shown for q in hosted_instrument().questions if q.is_why and q.target.startswith(
        "why:WHY_"
    ) and q.target not in ("why:WHY_CONTROL", "why:WHY_SATISFACTION", "why:WHY_OTHER_WORK")}
    assert len(shown) == 1, shown


def test_each_probe_has_its_own_map_key_although_the_wording_repeats() -> None:
    """Five AMQ probes titled "Why did you choose that?" would be one key and four lost answers."""
    whys = [q for q in hosted_instrument().questions if q.is_why]
    assert len({q.key for q in whys}) == len(whys) == 37


def test_a_probe_is_drawn_directly_under_the_item_it_explains() -> None:
    """A driver asked to justify a rating three screens later is answering a different question."""
    questions = list(hosted_instrument().questions)
    for n, q in enumerate(questions):
        if q.is_why and q.target.startswith("why:WHY_") and n:
            previous = questions[n - 1]
            if previous.kind == "likert":
                assert previous.target == q.why_for_item, q.key


def test_a_why_answer_lands_inline_on_its_own_items_clause() -> None:
    """`SURVEY_SCALES_AND_WHY_PROBES.md` §4.2 fixes this shape.

    Grouped at the end of a section — which is where whys went while there were only three — the
    eleven PAC whys would sit in a row with nothing saying which rating each explained.
    """
    from twinlab.models.twin import SurveyResponse, Twin
    from twinlab.persona.builder import build_persona

    ref = reference()
    answers = {i: 5 if ref.scale_points(i) == 7 else 3 for i in ref.battery_item_ids}
    passage = build_persona(
        Twin(twin_id="T1"),
        SurveyResponse(twin_id="T1", answers=answers, whys={"WHY_AMQ1": "the app pings me"}),
        ref,
    ).text

    clause = (
        "I somewhat agree that an automated system tracks me carefully to make sure I finish my "
        "tasks. In my own words: 'the app pings me'"
    )
    assert clause in passage


def test_an_unanswered_probe_adds_nothing_to_the_passage() -> None:
    """Optional means optional: a blank probe leaves the clause exactly as it was."""
    from twinlab.models.twin import SurveyResponse, Twin
    from twinlab.persona.builder import build_persona

    ref = reference()
    answers = {i: 5 if ref.scale_points(i) == 7 else 3 for i in ref.battery_item_ids}
    bare = build_persona(
        Twin(twin_id="T1"), SurveyResponse(twin_id="T1", answers=answers), ref
    )
    assert "In my own words:" not in bare.text
    assert bare.clause_count == 37


async def test_a_hosted_why_answer_reaches_the_twins_persona(backend) -> None:
    """End to end: a driver types a why, and it is in the persona the twin is grounded on."""
    key = next(
        q.key for q in hosted_instrument().questions if q.target == "why:WHY_AMQ1"
    )
    receipt = await submit(
        _filled(**{key: "a passenger cancelled and the app still marked me down"}),
        backend=backend,
        storage=InMemoryStorage(),
    )
    assert receipt.twin_id

    twins = await backend.select("twins", None)
    assert "a passenger cancelled and the app still marked me down" in twins[0]["persona_passage"]

    # And it is stored as that item's own why_text, verbatim, not paraphrased.
    answers = await backend.select("survey_answers", [("eq", "item_id", "AMQ1")])
    assert answers[0]["why_text"] == "a passenger cancelled and the app still marked me down"


# --------------------------------------------------------------- a tab left open across a restart


def _handlers():
    """The page's forward and back click handlers, as Gradio registered them."""
    import gradio as gr

    from twinlab.ui.components import drain_pending_loads
    from twinlab.ui.pages.survey_take import render_survey_take

    with gr.Blocks() as demo:
        render_survey_take(None)
        drain_pending_loads(demo)

    found = {}
    for dep in demo.fns.values():
        for target in getattr(dep, "targets", []):
            block_id = target[0] if isinstance(target, tuple) else None
            block = demo.blocks.get(block_id)
            if isinstance(block, gr.Button) and block.value in ("Start the survey", "Back"):
                found["forward" if block.value == "Start the survey" else "back"] = dep
    return demo, found


async def test_a_short_value_list_refuses_rather_than_misfiling_answers() -> None:
    """The failure a tab left open across a restart produces, and why it must not be tolerated.

    A Gradio client replays the component tree it loaded with. When the instrument changed from
    112 questions to 146, an open tab kept posting 112 values against 146 questions. The values
    are positional and nothing identifies which question each belongs to, so pairing the first 112
    would file real answers under the wrong questions — a fabricated record, which is worse than
    any error. The handler must refuse, and must say so **on the page** rather than leaving Gradio
    to render a bare "Error" chip a driver can do nothing with.
    """
    from twinlab.survey.payload import new_progress

    _demo, handlers = _handlers()
    assert "forward" in handlers, "could not locate the forward handler"

    progress = new_progress()
    progress.stop_index = 5
    # One value short of the 146 the page registered.
    out = await handlers["forward"].fn(progress, *([4] * 145))

    error_html = out[2]
    assert "reload the page" in error_html
    assert "Nothing has been saved" in error_html
    # Still on the same stop, and no terminal screen: the driver has somewhere to go back to.
    assert not out[3], "no receipt should be rendered"


async def test_a_handler_failure_is_shown_on_the_page_not_as_a_bare_error(backend) -> None:
    """An uncaught exception reaches a driver as a red chip with no text. This asserts it does not.

    The submit path is forced to fail at the storage write, which is the one failure intake
    cannot make safe — so it is also the one the driver most needs told clearly.
    """
    from twinlab.db.client import set_storage
    from twinlab.survey.payload import new_progress

    class _DeadStorage(InMemoryStorage):
        async def put(self, path: str, body: str) -> None:
            raise StorageError("bucket unreachable")

    _demo, handlers = _handlers()
    instrument = hosted_instrument()
    progress = new_progress()
    progress.stop_index = len(instrument.stops)

    set_storage(_DeadStorage())
    try:
        out = await handlers["forward"].fn(progress, *([4] * len(instrument.questions)))
    finally:
        set_storage(None)

    assert "could not be sent" in out[2] or "went wrong" in out[2]
    assert not out[3], "no receipt when nothing was stored"
    assert await backend.count("survey_submissions") == 0


# ------------------------------------------------- "already a twin" is not "nothing was eligible"


async def test_a_hosted_respondent_is_already_a_twin_and_is_reported_as_such(backend) -> None:
    """The hosted questionnaire builds the twin at send, so the import has nothing left to do.

    That is a success, not a failure, and it used to be reported with the same `skipped` count as
    a respondent who was gated out — which made the Generator tell a researcher holding a perfectly
    good twin that "Nothing was eligible". The two counts are now separate.
    """
    from twinlab.services.lab import import_survey_twins

    receipt = await submit(_filled(), backend=backend, storage=InMemoryStorage())
    assert receipt.twin_id, "the hosted path builds the twin itself"

    result = await import_survey_twins("Real and synthetic", backend=backend)
    assert result.imported == 0
    assert result.already_twins == 1
    assert result.gated == 0
    assert result.invalid == 0
    assert result.skipped == 1, "skipped stays the docs/06 §3.8 total of the two"


async def test_a_gated_respondent_is_counted_separately_from_an_imported_one(backend) -> None:
    """A respondent who withheld consent 7 is `gated`, never `already_twins`."""
    from twinlab.services.lab import import_survey_twins

    storage = InMemoryStorage()
    await submit(
        _filled(**{_key_for("consent:twin"): False}), backend=backend, storage=storage
    )
    result = await import_survey_twins("Real and synthetic", backend=backend)

    assert result.imported == 0
    assert result.already_twins == 0
    assert result.gated == 1


async def test_build_twin_false_leaves_a_respondent_the_import_can_pick_up(backend) -> None:
    """The bulk path still works: a stored-but-not-built respondent imports normally."""
    from twinlab.services.lab import import_survey_twins

    storage = InMemoryStorage()
    await submit(_filled(), backend=backend, storage=storage, build_twin=False)
    # The same mirror the submission was written to: the import rebuilds the twin from the raw
    # object, so a different store would be a different (empty) bucket.
    result = await import_survey_twins(
        "Real and synthetic", backend=backend, storage=storage
    )

    assert result.imported == 1
    assert result.already_twins == 0 and result.gated == 0
    twins = await backend.select("twins", None)
    assert twins[0]["persona_hash"]


# --------------------------------------------------------------------------- the four human arms


def test_every_arm_has_a_part_15_story() -> None:
    """`docs/01` §5 — each respondent sees **their own arm's** story.

    Only `REP1`'s existed in the instrument, which is why no real-respondent path ever assigned an
    arm and H2 validation skipped every real twin.
    """
    from twinlab.survey.instrument import ARM_STORIES, arm_story

    assert set(ARM_STORIES) == set(reference().arms) == {"BASE", "CON1", "MGT1", "REP1"}
    for arm in ARM_STORIES:
        assert arm_story(arm).startswith("Imagine that this is true:")
    assert len({arm_story(a) for a in ARM_STORIES}) == 4, "four arms, four different worlds"


def test_an_unknown_arm_refuses_rather_than_showing_the_wrong_story() -> None:
    """A story that disagrees with the stored arm makes every H2 comparison on that row wrong,
    and nothing downstream could detect it (`docs/08` §3.1)."""
    from twinlab.survey.instrument import InstrumentMismatch, arm_story

    with pytest.raises(InstrumentMismatch):
        arm_story("REP2")


def test_the_three_derived_stories_carry_their_levers_own_words() -> None:
    """They are composed from Part 17's dial-1 lever paragraphs, never authored fresh.

    `docs/01` §5.1 maps `CON1` to `2.1.a–c` and `MGT1` to `4.1.a/b/d`, and Part 17 already states
    exactly those commitments in driver-facing prose. This pins the correspondence so a reworded
    Part 17 cannot leave an arm's story describing something else.
    """
    from twinlab.survey.instrument import _COND_1, _MGMT_1, ARM_STORIES

    assert _COND_1.rstrip(".") .lower()[-40:] in ARM_STORIES["CON1"].lower()
    assert _MGMT_1.rstrip(".").lower()[-40:] in ARM_STORIES["MGT1"].lower()


async def test_an_arm_is_drawn_balanced_within_the_city_service_stratum(backend) -> None:
    """Balance is **within** stratum, never overall. `docs/01` §5.2.

    Four draws into one empty stratum must take each arm once; a fifth has nothing left to
    balance and may take any.
    """
    from twinlab.services.hosted_survey import assign_arm

    drawn = []
    for _ in range(4):
        arm, source = await assign_arm("Mumbai", "Cab", backend=backend)
        drawn.append(arm)
        await backend.insert("survey_submissions", [{
            "submission_id": f"S{len(drawn)}", "data_type": "REAL", "arm": arm,
            "city": "Mumbai", "service": "Cab", "eligible": True, "consented": True,
            "consent_twin": True, "attention_passed": True, "outcome": "complete",
            "raw_object_path": "raw/x.json", "submitted_at": "2026-10-08T00:00:00Z",
        }])
        assert source == "hosted_balanced"
    assert sorted(drawn) == ["BASE", "CON1", "MGT1", "REP1"]


async def test_another_stratum_balances_independently(backend) -> None:
    """A stratum full of one arm must not steer the next stratum's draw."""
    from twinlab.services.hosted_survey import assign_arm

    for n in range(4):
        await backend.insert("survey_submissions", [{
            "submission_id": f"M{n}", "data_type": "REAL", "arm": "BASE",
            "city": "Mumbai", "service": "Cab", "eligible": True, "consented": True,
            "consent_twin": True, "attention_passed": True, "outcome": "complete",
            "raw_object_path": "raw/x.json", "submitted_at": "2026-10-08T00:00:00Z",
        }])
    # Pune is empty, so every arm is still equally short there.
    arms = {(await assign_arm("Pune", "Cab", backend=backend))[0] for _ in range(12)}
    assert len(arms) > 1, "an empty stratum must not inherit Mumbai's imbalance"
    # Mumbai is now four BASE and nothing else, so BASE is the one arm it cannot draw.
    assert (await assign_arm("Mumbai", "Cab", backend=backend))[0] != "BASE"


async def test_synthetic_rows_never_steer_a_real_drivers_arm(backend) -> None:
    """Generated data must not decide which story a real driver reads.

    Both readings of the counts are made **deterministic** here, so nothing rests on how four
    random draws happen to spread. Over real rows alone REP1 is the unique minimum; add the
    synthetic rows to the same counts and BASE becomes the unique minimum instead. `assign_arm`
    therefore has no tie to break either way: it returns REP1 on every call if it reads only real
    submissions, and BASE on every call if generated data leaked into the tally.
    """
    from twinlab.services.hosted_survey import assign_arm

    # Synthetic: one CON1, one MGT1, two REP1. Two REP1 is what makes the wrong reading land on a
    # single arm as well — with one, BASE and REP1 would tie and the bug would show only by luck.
    for n, arm in enumerate(["CON1", "MGT1", "REP1", "REP1"]):
        await backend.insert("survey_submissions", [{
            "submission_id": f"SYN{n}", "data_type": "SYNTHETIC", "arm": arm,
            "city": "Mumbai", "service": "Cab", "eligible": True, "consented": True,
            "consent_twin": True, "attention_passed": True, "outcome": "complete",
            "raw_object_path": "raw/x.json", "submitted_at": "2026-10-08T00:00:00Z",
        }])
    # Real: BASE, CON1 and MGT1 once each. REP1 is the one arm no real driver has read.
    for n, arm in enumerate(["BASE", "CON1", "MGT1"]):
        await backend.insert("survey_submissions", [{
            "submission_id": f"REAL{n}", "data_type": "REAL", "arm": arm,
            "city": "Mumbai", "service": "Cab", "eligible": True, "consented": True,
            "consent_twin": True, "attention_passed": True, "outcome": "complete",
            "raw_object_path": "raw/x.json", "submitted_at": "2026-10-08T00:00:00Z",
        }])

    drawn = {(await assign_arm("Mumbai", "Cab", backend=backend))[0] for _ in range(4)}
    assert drawn == {"REP1"}, (
        "REP1 is the unique minimum over real rows and there is no tie to break, so every draw "
        f"must be REP1; BASE means the synthetic rows were counted (got {sorted(drawn)})"
    )


async def test_a_submission_records_the_arm_it_was_shown(backend) -> None:
    """Without this `survey_submissions.arm` is null and H2 skips the twin entirely."""
    progress = _filled()
    progress.arm, progress.arm_source = "CON1", "hosted_balanced"
    receipt = await submit(progress, backend=backend, storage=InMemoryStorage())

    rows = await backend.select("survey_submissions", None)
    assert rows[0]["arm"] == "CON1"
    assert rows[0]["arm_source"] == "hosted_balanced"
    assert receipt.twin_id


async def test_the_manipulation_check_is_stored_as_an_arm_id(backend) -> None:
    """`mc_correct` is `generated always as (mc_answer = arm)`, so a label never matches.

    Part 15 offers the four arms by label; `arm` holds an id. Storing the label made
    `mc_correct` false for **every** real respondent, silently. The synthetic generator hid it by
    writing the id directly, which is why no test caught the disagreement.
    """
    mc_key = _key_for("check:manipulation")
    progress = _filled(**{mc_key: "A drivers' forum and union recognition"})
    progress.arm, progress.arm_source = "REP1", "hosted_balanced"
    await submit(progress, backend=backend, storage=InMemoryStorage())

    row = (await backend.select("survey_submissions", None))[0]
    assert row["mc_answer"] == "REP1", "the label must resolve to its arm id"
    assert row["arm"] == "REP1"


async def test_an_unrecognised_manipulation_answer_is_kept_verbatim(backend) -> None:
    """Still the driver's answer. `mc_correct` is simply false; nothing is guessed or dropped."""
    from twinlab.ingest.survey_intake import build_rows
    from twinlab.survey.payload import build_payload

    mc_key = _key_for("check:manipulation")
    payload = build_payload(_filled(**{mc_key: "something else entirely"}))
    rows = build_rows(payload, raw_object_path="raw/x.json")
    assert rows["submission"]["mc_answer"] == "something else entirely"


# ----------------------------------------------------- deleting a twin knows what references it


def test_every_table_referencing_twins_is_classified() -> None:
    """A table that references `twins(twin_id)` must be known to `delete_synthetic`.

    This list has been wrong twice, the same way both times: a table added in a later migration,
    never added to either tuple, and the Generator's delete button failing with a raw `23503` the
    first time a researcher pressed it. `studio_runs` was the first. `twin_control_answers`
    (migration 005) was the second, and it broke the button for **every** synthetic twin that had
    answered a config-matched control cell — which, after one run, is all of them.

    Reading the migrations rather than restating them is what stops a third.
    """
    import re
    from pathlib import Path

    from twinlab.services.surveys import (
        BLOCKING_TWIN_REFERENCES,
        CASCADING_TWIN_REFERENCES,
    )

    migrations = Path(__file__).resolve().parent.parent / "src/twinlab/db/migrations"
    sql = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(migrations.glob("*.sql"))
    )

    referencing: set[str] = set()
    table = None
    for line in sql.splitlines():
        created = re.search(r"create table if not exists (\w+)", line, re.I)
        if created:
            table = created.group(1)
        if table and re.search(r"references\s+twins\s*\(\s*twin_id\s*\)", line, re.I):
            referencing.add(table)

    assert "twin_control_answers" in referencing, "the migration scan found nothing to check"
    known = {t for t, _ in BLOCKING_TWIN_REFERENCES} | set(CASCADING_TWIN_REFERENCES)
    # `twins` itself and tables that cascade are still listed, because the in-memory backend has
    # no foreign keys and the suite runs on it.
    unclassified = referencing - known - {"twins"}
    assert not unclassified, (
        f"{sorted(unclassified)} reference twins(twin_id) but delete_synthetic does not know "
        "them; add each to BLOCKING_TWIN_REFERENCES or CASCADING_TWIN_REFERENCES"
    )


async def test_deleting_a_synthetic_batch_survives_its_control_answers(backend) -> None:
    """The failure this caused: one control answer made a whole synthetic batch undeletable."""
    from twinlab.generator.synthetic import SYNTHETIC_DATA_TYPE
    from twinlab.services.surveys import delete_synthetic

    await backend.insert("survey_submissions", [{
        "submission_id": "SYN-1", "data_type": SYNTHETIC_DATA_TYPE, "eligible": True,
        "consented": True, "consent_twin": True, "attention_passed": True,
        "outcome": "complete", "raw_object_path": "raw/x.json",
        "submitted_at": "2026-10-08T00:00:00Z",
    }])
    await backend.insert("twins", [{
        "twin_id": "SYN-1", "submission_id": "SYN-1", "source": "synthetic",
        "consent_twin": True,
    }])
    await backend.insert("twin_control_answers", [{
        "twin_id": "SYN-1", "control_code": "00000", "config_fingerprint": "f",
        "answers": {}, "lever_order": [1, 2, 3, 4, 5], "seed": 1, "wording": "A",
        "model": "stub",
    }])

    result = await delete_synthetic(backend)
    assert result["twins"] == 1
    assert await backend.count("twins") == 0
    assert await backend.count("twin_control_answers") == 0
