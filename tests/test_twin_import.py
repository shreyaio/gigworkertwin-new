"""`docs/06` §3.8's *Import twins from the survey*.

The button was `interactive=False` with no handler and the *Which survey answers?* radio was bound
to nothing, so a generated batch could be stored and then never became twins. Three things had to
exist before it could work, and each is tested here:

* the Storage mirror had to be **readable** — `put` alone makes it write-only, and
  `ingest/replay_raw.py` has always called `get` and `list`;
* the twin had to be rebuilt **from the raw object**, because `survey_submissions` has no column
  for age, gender, tenure or any Part 4 answer, and no Part 14 own-words question is in the frozen
  73-item register, so none of it is in `survey_answers` either;
* the count and the import had to apply **one rule**, or the screen promises an import it will not
  perform.

No live LLM and no live database (`CLAUDE.md` — Testing).
"""

from __future__ import annotations

import asyncio

import pytest

from twinlab.db.client import InMemoryBackend, InMemoryStorage
from twinlab.services.generator import default_spec, generate_and_store


def _run(coro):
    return asyncio.run(coro)


def _loaded(count: int = 12, seed: int = 20260930):
    """A backend and mirror holding one stored synthetic batch, as the Generator leaves them."""
    db, store = InMemoryBackend(), InMemoryStorage()
    _run(generate_and_store(default_spec(seed, count=count), backend=db, storage=store))
    return db, store


# --------------------------------------------------------------------- the mirror is readable


def test_the_mirror_can_be_read_back_and_listed():
    """`replay_raw` calls both. A write-only mirror cannot serve I16's payoff."""
    from twinlab.db.client import StorageError

    _db, store = _loaded(3)
    paths = _run(store.list("raw/"))
    assert len(paths) == 3
    assert paths == sorted(paths), "listing must be sorted so a replay is reproducible"
    assert _run(store.get(paths[0])).startswith("{")
    with pytest.raises(StorageError, match="no object at"):
        _run(store.get("raw/does-not-exist.json"))


# ------------------------------------------------------------------------ the scope is a rule


def test_the_count_follows_the_scope_control():
    """`docs/06` §3.8's radio is bound. It used to be decoration beside a hard-coded count.

    `available_survey_twins` excluded synthetic rows outright, so a synthetic batch read **0
    available** and there was no way to import it at all.
    """
    from twinlab.services.lab import available_survey_twins

    db, _store = _loaded(12)
    assert _run(available_survey_twins("Real and synthetic", db)) == 12
    assert _run(available_survey_twins("Synthetic only", db)) == 12
    assert _run(available_survey_twins("Real only", db)) == 0


def test_an_unknown_scope_raises_rather_than_importing_everything():
    """`CLAUDE.md` rule 7 — a mistyped scope must not silently widen the import."""
    from twinlab.services.lab import available_survey_twins

    db, _store = _loaded(2)
    with pytest.raises(ValueError, match="unknown survey scope"):
        _run(available_survey_twins("Everything", db))


def test_the_count_and_the_import_apply_the_same_rule():
    """A screen that promises N and imports M is worse than one that promises nothing."""
    from twinlab.services.lab import available_survey_twins, import_survey_twins

    db, store = _loaded(12)
    promised = _run(available_survey_twins("Synthetic only", db))
    result = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert result.imported == promised
    assert result.remaining == 0


# ------------------------------------------------------------------------------ the import


def test_import_builds_twins_with_everything_the_driver_sent():
    """I6 — a persona is lossless. From the row alone it would have neither.

    `survey_submissions` carries no age, gender, tenure or Part 4 answer, and Part 14's own-words
    questions are not in the frozen register, so a twin built from the row has empty demographics
    and an empty background — which `docs/01` §6.2 names exactly: "without this the persona loses
    the driver's own words".
    """
    from twinlab.services.lab import import_survey_twins

    db, store = _loaded(6)
    result = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert (result.imported, result.invalid) == (6, 0)

    twins = _run(db.select("twins", None))
    assert len(twins) == 6
    for twin in twins:
        assert twin["age"] and twin["gender"], "demographics were not recovered"
        assert twin["tenure_months"] and twin["hours_per_week"]
        assert twin["city"] and twin["service"]
        background = twin["background"]
        assert background["vehicle_arrangement"], "Part 4 was lost"
        assert background["education"]
        assert len(background["own_words"]) == 5, "Part 14 was lost"
        assert twin["persona_passage"] and twin["persona_hash"]
        # I6 — the holdouts are never in a persona, whatever else is.
        assert "H3_" not in twin["persona_passage"]


def test_an_imported_synthetic_twin_is_marked_synthetic():
    """`delete_synthetic` and `panel.POPULATION_SOURCES` both key on `source`.

    A twin built from a synthetic row that called itself `real` would survive a delete of its own
    batch and could be drawn into an analysis panel as though a driver were behind it.
    """
    from twinlab.services.lab import import_survey_twins
    from twinlab.services.surveys import delete_synthetic

    db, store = _loaded(5)
    _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert {t["source"] for t in _run(db.select("twins", None))} == {"synthetic"}

    removed = _run(delete_synthetic(db))
    assert removed["twins"] == 5
    assert _run(db.select("twins", None)) == []


def test_tenure_survives_the_round_trip_into_months():
    """The dashboard set months, the Form stored years, and the twin must show the months set."""
    from twinlab.models.view import GeneratorSpec
    from twinlab.services.generator import generate_and_store
    from twinlab.services.lab import import_survey_twins

    db, store = InMemoryBackend(), InMemoryStorage()
    spec = GeneratorSpec(seed=55, count=8, tenure_months_range=(18, 18))
    _run(generate_and_store(spec, backend=db, storage=store))
    _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert {t["tenure_months"] for t in _run(db.select("twins", None))} == {18}


def test_a_second_import_is_a_no_op_rather_than_a_duplicate():
    """`twins.submission_id` is unique. Evidence is append-only (I9); a rebuild is a delete."""
    from twinlab.services.lab import import_survey_twins

    db, store = _loaded(7)
    first = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    second = _run(import_survey_twins("Synthetic only", backend=db, storage=store))

    assert first.imported == 7
    assert second.imported == 0
    assert second.skipped == 7
    assert len(_run(db.select("twins", None))) == 7


def test_a_respondent_who_withheld_twin_consent_is_never_imported():
    """Statement 7 is the gate. `docs/01` §6.2 — whatever else their row says."""
    from twinlab.services.lab import available_survey_twins, import_survey_twins

    db, store = _loaded(6)
    rows = _run(db.select("survey_submissions", None))
    _run(db.update("survey_submissions", {"consent_twin": False},
                   [("eq", "submission_id", rows[0]["submission_id"])]))

    assert _run(available_survey_twins("Synthetic only", db)) == 5
    result = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert result.imported == 5
    imported_ids = {t["twin_id"] for t in _run(db.select("twins", None))}
    assert rows[0]["submission_id"] not in imported_ids


def test_a_missing_raw_object_is_reported_by_name_not_silently_skipped():
    """`CLAUDE.md` rule 7. An import that says "5 of 6" and nothing else is a guess for the reader.

    It must also not cost the other rows: one unreadable payload fails its own row alone.
    """
    from twinlab.services.lab import import_survey_twins

    db, store = _loaded(6)
    lost = sorted(store.objects)[0]
    del store.objects[lost]

    result = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    assert result.imported == 5
    assert result.invalid == 1
    assert result.reasons and "StorageError" in result.reasons[0]
    assert len(_run(db.select("twins", None))) == 5, "one bad row discarded the good ones"


def test_the_import_makes_no_model_call():
    """The whole path is deterministic Python: `build_rows`, then the persona builder."""
    from twinlab.services.lab import import_survey_twins

    db, store = _loaded(4)
    a = _run(import_survey_twins("Synthetic only", backend=db, storage=store))
    hashes_a = sorted(t["persona_hash"] for t in _run(db.select("twins", None)))

    db2, store2 = _loaded(4)
    _run(import_survey_twins("Synthetic only", backend=db2, storage=store2))
    hashes_b = sorted(t["persona_hash"] for t in _run(db2.select("twins", None)))

    assert a.imported == 4
    assert hashes_a == hashes_b, "the same row must give a byte-identical passage"
