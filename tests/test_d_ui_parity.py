"""The surfaces brought to parity with the Apps Script prototype, and the Storage client.

Four things are tested here, all of which were either absent or wrong before:

* **the Storage mirror** — `db/client.py` now owns it, and `store_batch` writes every raw object
  *before* any row (I16). That ordering was previously only assertable against a fake the tests
  built themselves, because no implementation existed;
* **the generator's bound controls** — the fifth city, the Form's own spellings, months, the
  economic-dependence control and the per-lever reactions that move the two holdout blocks;
* **the Results grid** — the index-scaled fill `docs/05` §8.3 specifies, and the row labels;
* **the Driver survey screen** — `docs/06` §2's numbers, counted rather than written down.

No live LLM and no live database (`CLAUDE.md` — Testing).
"""

from __future__ import annotations

import asyncio

from twinlab.ingest.reference_store import reference


def _run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ Storage and I16


def test_the_in_memory_mirror_satisfies_the_storage_protocol():
    """`get_storage()` returns something the service layer can call without knowing which it is."""
    from twinlab.db.client import InMemoryStorage, StorageBackend

    storage = InMemoryStorage()
    assert isinstance(storage, StorageBackend)
    _run(storage.put("raw/x.json", "{}"))
    assert storage.objects["raw/x.json"] == "{}"


def test_store_batch_writes_every_raw_object_before_any_row():
    """I16 — a row whose raw object is missing is a different kind of record from a real one.

    The recorder below fails the test if a single row is inserted before the last object lands,
    which is the ordering `supabase/functions/survey_intake/index.ts` uses for live intake.
    """
    from twinlab.db.client import InMemoryBackend
    from twinlab.generator.synthetic import generate_batch
    from twinlab.services.surveys import store_batch

    order: list[str] = []

    class RecordingStorage:
        name = "recording"

        def __init__(self) -> None:
            self.objects: dict[str, str] = {}

        async def put(self, path: str, body: str) -> None:
            order.append("object")
            self.objects[path] = body

    class RecordingBackend(InMemoryBackend):
        async def insert(self, table, rows):
            order.append(f"insert:{table}")
            return await super().insert(table, rows)

        async def upsert(self, table, rows, *, on_conflict):
            order.append(f"upsert:{table}")
            return await super().upsert(table, rows, on_conflict=on_conflict)

    storage = RecordingStorage()
    batch = generate_batch(seed=99, count=4)
    _run(store_batch(batch, storage=storage, backend=RecordingBackend()))

    writes = [i for i, step in enumerate(order) if step != "object"]
    objects = [i for i, step in enumerate(order) if step == "object"]
    assert objects, "no raw object was written at all"
    assert max(objects) < min(writes), f"a row was written before the last object: {order}"
    assert len(storage.objects) == 4, "one raw object per respondent"


def test_generate_and_store_reports_what_it_stored():
    """The Generator screen's button is this function, and it must not report a partial batch."""
    from twinlab.db.client import InMemoryBackend, InMemoryStorage
    from twinlab.services.generator import default_spec, generate_and_store

    storage = InMemoryStorage()
    result = _run(
        generate_and_store(
            default_spec(4242, count=6), backend=InMemoryBackend(), storage=storage
        )
    )
    assert result["submissions"] == 6
    assert result["raw_objects"] == 6 == len(storage.objects)
    assert result["answers"] > 0


# --------------------------------------------------------- the generator's §4 controls


def test_the_generator_draws_the_forms_own_five_cities():
    """A generated `field:city` outside the Form's options is one live intake could never receive.

    The list had four cities and spelled Delhi NCR as "Delhi", so every synthetic row in that
    city carried a value the real instrument cannot produce.
    """
    from twinlab.generator.synthetic import generate_batch
    from twinlab.models.view import GENERATOR_CITIES

    assert GENERATOR_CITIES == ("Mumbai", "Pune", "Delhi NCR", "Jaipur", "Bengaluru")
    batch = generate_batch(seed=77, count=150)
    drawn = {row["city"] for row in batch["submissions"]}
    assert drawn <= set(GENERATOR_CITIES), drawn
    assert len(drawn) == 5, f"a city was never drawn: {drawn}"


def test_tenure_months_round_trip_through_the_forms_years_question():
    """The dashboard sets months, the Form asks years, and the two must be the same number."""
    from twinlab.generator.synthetic import years_from_months

    for months in (3, 7, 11, 12, 37, 72, 599):
        assert round(float(years_from_months(months)) * 12) == months


def test_a_five_point_item_is_converted_by_position_not_clamped():
    """`docs/06` §4: "5 point questions are converted". Converted, never clipped."""
    from twinlab.generator.synthetic import centre_for_points

    assert centre_for_points(7.0, 7) == 7.0
    assert centre_for_points(7.0, 5) == 5.0
    assert centre_for_points(1.0, 5) == 1.0
    assert centre_for_points(4.0, 7) == 4.0
    assert centre_for_points(4.0, 5) == 3.0


def test_reverse_coded_items_are_drawn_mirrored():
    """`SAT2` asks the opposite question, so it must fall as `SAT1` rises.

    Drawn forward — which is what every batch before `v3` did — the SAT block contradicts itself
    and the construct's reliability is destroyed before any analysis runs.
    """
    from twinlab.generator.synthetic import generate_batch
    from twinlab.models.view import GeneratorSpec

    ref = reference()
    assert ref.items["SAT2"].reverse_coded

    def mean(batch: dict, item_id: str) -> float:
        values = [
            float(a["value_num"]) for a in batch["answers"] if a["item_id"] == item_id
        ]
        return sum(values) / len(values)

    happy = generate_batch(
        seed=31, count=80, spec=GeneratorSpec(seed=31, construct_targets={"SATI": 6.5})
    )
    sour = generate_batch(
        seed=31, count=80, spec=GeneratorSpec(seed=31, construct_targets={"SATI": 1.5})
    )
    assert mean(happy, "SAT1") > mean(sour, "SAT1")
    assert mean(happy, "SAT2") < mean(sour, "SAT2"), "the reverse-coded item moved with SAT1"


def test_need_the_money_control_moves_the_edep_block_only():
    """EDEP is the moderator in `stats/spec.py`, which is why §4 gives it its own control."""
    from twinlab.generator.synthetic import generate_batch
    from twinlab.models.view import GeneratorSpec

    def dep_mean(need: float) -> float:
        batch = generate_batch(
            seed=8, count=80, spec=GeneratorSpec(seed=8, need_money=need)
        )
        values = [
            float(a["value_num"])
            for a in batch["answers"]
            if a["item_id"] == "DEP2"  # forward-scored member of the DEP block
        ]
        return sum(values) / len(values)

    assert dep_mean(6.5) > dep_mean(1.5) + 1.0


def test_multi_apping_and_the_vehicle_loan_are_single_decisions():
    """A driver on one platform who names two others is a contradiction intake could not receive.

    The two answers used to be drawn independently, which produced that pair routinely.
    """
    from twinlab.generator.synthetic import generate_batch
    from twinlab.ingest.survey_intake import form_map
    from twinlab.models.view import GeneratorSpec

    titles = {target: key for key, target in form_map().items()}

    def answer(payload: dict, target: str) -> str:
        section, _, title = titles[target].partition("|")
        for a in payload["answers"]:
            if a["section"] == section and a["title"] == title:
                return str(a["value"])
        raise AssertionError(target)

    batch = generate_batch(
        seed=6, count=60, spec=GeneratorSpec(seed=6, multi_app_share=1.0, vehicle_loan_share=1.0)
    )
    for payload in batch["payloads"]:
        assert int(answer(payload, "background:platform_count")) >= 2
        assert answer(payload, "background:other_apps") != "None"
        assert answer(payload, "background:vehicle_arrangement") == "Own with a loan"

    none_batch = generate_batch(
        seed=6, count=60, spec=GeneratorSpec(seed=6, multi_app_share=0.0, vehicle_loan_share=0.0)
    )
    for payload in none_batch["payloads"]:
        assert answer(payload, "background:platform_count") == "1"
        assert answer(payload, "background:other_apps") == "None"
        assert answer(payload, "background:vehicle_arrangement") != "Own with a loan"


def test_the_h2_block_moves_by_the_respondents_own_arm():
    """Part 16 asks the battery again *imagining the assigned arm is true*. I6's other half.

    Before `v3` it repeated the baseline, so the arm a respondent was assigned had no effect on
    anything they answered and H2 validation could not distinguish the arms.
    """
    from twinlab.generator.synthetic import generate_batch
    from twinlab.models.view import GeneratorSpec

    batch = generate_batch(seed=21, count=240, spec=GeneratorSpec(seed=21))
    arms = {row["submission_id"]: row["arm"] for row in batch["submissions"]}
    by_arm: dict[str, list[float]] = {}
    for a in batch["answers"]:
        if a["item_id"] == "H2_FAIR1":
            by_arm.setdefault(arms[a["submission_id"]], []).append(float(a["value_num"]))

    means = {arm: sum(v) / len(v) for arm, v in by_arm.items()}
    assert set(means) >= {"BASE", "CON1", "MGT1", "REP1"}, means
    # BASE is 00000: no change, so it must sit below every arm that raises a dial.
    for arm in ("CON1", "MGT1", "REP1"):
        assert means[arm] > means["BASE"], f"{arm} did not move H2 fairness: {means}"


def test_the_captive_voice_checkbox_changes_only_the_representation_lever():
    """§4's one interaction: a driver who needs the money reacts more to a drivers' forum."""
    from twinlab.generator.synthetic import reaction_shift
    from twinlab.models.view import GeneratorSpec

    on = GeneratorSpec(seed=1, captive_voice=True)
    off = GeneratorSpec(seed=1, captive_voice=False)

    forum = "00001"  # representation alone
    pay = "10000"  # pay alone
    assert reaction_shift(forum, on, economic_dependence=1.0) > reaction_shift(
        forum, on, economic_dependence=0.0
    )
    assert reaction_shift(forum, off, economic_dependence=1.0) == reaction_shift(
        forum, off, economic_dependence=0.0
    )
    # Pay is untouched by the checkbox at any level of dependence.
    assert reaction_shift(pay, on, economic_dependence=1.0) == reaction_shift(
        pay, off, economic_dependence=0.0
    )


def test_an_unknown_lever_reaction_raises_rather_than_defaulting_to_normal():
    """`CLAUDE.md` rule 7 — a forgotten binding must not silently become "normal"."""
    import pytest

    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(seed=1, lever_reactions={"L1": 1.0})
    with pytest.raises(KeyError, match="no reaction weight for lever"):
        spec.reaction("L5")


def test_the_batch_is_still_deterministic_in_seed_and_spec():
    """`docs/09` §2 — same seed, same batch. Every new control is drawn from the batch's own RNG."""
    from twinlab.generator.synthetic import generate_batch
    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(seed=404, need_money=6.0, multi_app_share=0.3, shared_mood=0.8)
    a = generate_batch(seed=404, count=12, spec=spec)
    b = generate_batch(seed=404, count=12, spec=spec)
    assert a["answers"] == b["answers"]
    assert a["submissions"] == b["submissions"]


# ------------------------------------------------------------------- the Results grid


def test_the_grid_fills_tested_cells_by_index():
    """`docs/05` §8.3 — "tested filled white->green by index", not one flat green."""
    from twinlab.services.metrics_view import build_grid

    cells = {c.version_code: c for c in build_grid({"00000": 1.0, "21012": 1.2, "22222": 1.4})}
    assert cells["00000"].intensity == 0.0
    assert cells["22222"].intensity == 1.0
    assert 0.0 < cells["21012"].intensity < 1.0
    assert cells["11111"].intensity is None, "an untested cell has no depth"


def test_one_tested_cell_does_not_divide_by_zero():
    from twinlab.services.metrics_view import build_grid

    cells = {c.version_code: c for c in build_grid({"01000": 1.1})}
    assert cells["01000"].intensity == 1.0


def test_the_grid_carries_row_labels_and_the_index_in_every_name():
    """Colour is never the only channel (`docs/05` §6), and the rows must be identifiable."""
    from twinlab.services.metrics_view import build_grid
    from twinlab.ui.components import grid_243

    html = grid_243(build_grid({"00000": 1.0, "22222": 1.4}))
    assert "pay 0, cond. 0" in html
    assert "pay 2, cond. 2" in html
    assert 'aria-label="version 22222, index 1.400, best so far"' in html
    assert "--tl-cell-depth" in html


def test_the_headline_interactions_name_the_codes_to_run():
    """I17 — a missing leg is named, never estimated (`CLAUDE.md` rule 5)."""
    from twinlab.db.client import InMemoryBackend
    from twinlab.services.results import interaction_rows

    rows = _run(interaction_rows(InMemoryBackend()))
    assert rows and not any(r.computable for r in rows)
    joined = " ".join(r.text for r in rows)
    for code in ("00010", "00001", "00011", "10000", "01000", "11000"):
        assert code in joined, code
    assert "not estimated" in joined


# ------------------------------------------------------------------ the Driver survey


def test_the_driver_survey_counts_its_numbers_rather_than_stating_them():
    """`docs/06` §2's "17 parts, three languages, 112 questions", read off the frozen sources."""
    from twinlab.db.client import InMemoryBackend
    from twinlab.services.surveys import survey_status

    status = _run(survey_status(InMemoryBackend()))
    assert status["parts"] == 17
    assert status["questions"] == 112
    assert status["items"] == 73
    assert len(status["languages"]) == 3


def test_the_driver_survey_never_counts_synthetic_rows_as_fieldwork():
    """`docs/08` §6.2 — a real count that included a synthetic batch reads as fieldwork."""
    from twinlab.db.client import InMemoryBackend, InMemoryStorage
    from twinlab.services.generator import default_spec, generate_and_store
    from twinlab.services.surveys import survey_status

    backend = InMemoryBackend()
    _run(generate_and_store(default_spec(1234, count=5), backend=backend,
                            storage=InMemoryStorage()))
    status = _run(survey_status(backend))
    assert status["synthetic_total"] == 5
    assert status["real_total"] == 0
    assert status["arm_balance"] == {}, "a synthetic row reached the arm-balance table"
