"""M13 — the eight validity tests. `docs/11` M13, specified in `docs/08` §4.

The eight acceptance criteria are implemented verbatim, each named in its test, beside the tests
that prove each gate can **fail**: a gate that cannot fail is not a gate (`HANDOFF.md` §2.4). Where
this module asserts a prohibition — the probe never reaching `variants`, the ablated persona never
reaching `twins`, a `PASS` never reaching a zero-twin row — it also injects the violation and
watches the refusal.

No live LLM and no live DB. Model calls are counted on :class:`StubModelClient`'s own counter,
which is how `docs/11` M13 requires "tests 1 and 3 make zero calls" to be established — in numbers,
not in prose.
"""

from __future__ import annotations

import pytest

from twinlab.agents.registry import StubModelClient, default_agent_configs
from twinlab.db.client import DbError
from twinlab.db.repositories import VariantRepo
from twinlab.ingest.reference_store import reference
from twinlab.models.validity import (
    AblatedPersona,
    ProbeStimulus,
    QuarantinedArtefact,
    ValidityOutcome,
    assert_not_ablated,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, validate_code
from twinlab.services import validity as service
from twinlab.validity import tests as vt

SESSION_ID = "11111111-1111-1111-1111-111111111111"


# --------------------------------------------------------------------------- seeding


async def _seed_twins(backend, n: int = 4, *, gap: int = 1) -> list[str]:
    """`n` twins, each with a driver, a full battery, an arm and a stored H2 vector.

    ``gap`` is how far every twin's H2 answer sits from its **own** driver's, in points. The
    drivers differ from each other by construction, so a larger `gap` makes test 1 fail and a
    smaller one makes it pass — which is what lets both directions be asserted rather than only
    the happy one.
    """
    ref = reference()
    battery = ref.battery_item_ids
    h2 = ref.holdout_h2_item_ids
    twin_ids: list[str] = []
    for i in range(n):
        twin_id = f"UBR-{i:03d}"
        twin_ids.append(twin_id)
        base = 3 + (i % 3)          # drivers genuinely differ from one another
        await backend.insert(
            "survey_submissions",
            [{
                "submission_id": twin_id, "data_type": "real", "eligible": True,
                "consented": True, "consent_twin": True, "attention_passed": True,
                "outcome": "complete", "arm": "BASE", "city": "Mumbai", "service": "cab",
                "raw_object_path": f"raw/{twin_id}.json", "submitted_at": "2026-01-01T00:00:00Z",
            }],
        )
        await backend.insert(
            "survey_answers",
            [
                {"submission_id": twin_id, "item_id": item, "value_num": base}
                for item in battery
            ]
            + [
                {"submission_id": twin_id, "item_id": item, "value_num": base}
                for item in h2
            ],
        )
        await backend.insert(
            "twins",
            [{
                "twin_id": twin_id, "submission_id": twin_id, "source": "real",
                "city": "Mumbai", "service": "cab", "consent_twin": True,
                "persona_passage": (
                    "I drive a cab in Mumbai. I do not think the app treats me fairly. "
                    "The pay is unfair when a trip is cancelled. I can see how my fares "
                    "are worked out."
                ),
                "persona_hash": f"hash-{i}",
            }],
        )
        await backend.insert(
            "twin_quality_runs",
            [{
                "twin_id": twin_id, "holdout_set": "H2", "arm": "BASE", "items_n": len(h2),
                "mae": 0.5, "pct_within_1": 0.9, "kept": None, "model": "stub", "repeats": 1,
                "is_latest": True,
                "detail": {service.H2_ANSWERS_KEY: {item: base + gap for item in h2}},
            }],
        )
    return twin_ids


async def _seed_session(backend, twin_ids: list[str], *, floor_index: float = 0.05) -> None:
    """A session with a frozen panel and a completed `00000` control, so a floor exists."""
    await backend.insert(
        "sessions",
        [{
            "session_id": SESSION_ID, "name": "m13", "status": "completed", "config": {},
            "panel_size": len(twin_ids), "panel_seed": 7,
        }],
    )
    await backend.insert(
        "session_panel",
        [
            {"session_id": SESSION_ID, "twin_id": t, "stratum": "Mumbai|cab", "position": i}
            for i, t in enumerate(twin_ids)
        ],
    )
    await backend.insert(
        "runs",
        [{
            "run_id": "22222222-2222-2222-2222-222222222222", "session_id": SESSION_ID,
            "version_code": CONTROL_CODE, "status": "completed", "twins_n": len(twin_ids),
            "index_value": floor_index, "is_latest_for_version": True,
        }],
    )


def _stub() -> StubModelClient:
    """A client that would answer if anything asked it. Nothing in tests 1 or 3 may."""
    return StubModelClient(lambda cfg, prompt, out: out())


# ------------------------------------------- accept 1: tests 1 and 3 make ZERO LLM calls


async def test_tests_1_and_3_make_zero_model_calls(backend) -> None:
    """`docs/11` M13 accept 1. **Asserted on the call counter, never on prose.**

    The stub is handed to nothing, which is the point: neither `_test1` nor `_test3` takes a
    client, so there is no path by which either could spend a call. The counter proves it.
    """
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    client = _stub()
    configs = default_agent_configs()

    one = await service.run_validity_test(1, session_id=SESSION_ID, backend=backend)
    three = await service.run_validity_test(3, session_id=SESSION_ID, backend=backend)

    assert client.calls == []
    assert sum(client.call_count(agent_id) for agent_id in configs) == 0
    assert one.test_id == "wrong_person"
    assert three.test_id == "simple_guesses"


def test_the_call_table_matches_the_specification() -> None:
    """`docs/08` §4's table: 0, N, 0, N, 2N, N, N, 3N."""
    assert vt.CALLS_PER_TWIN == {1: 0, 2: 1, 3: 0, 4: 1, 5: 2, 6: 1, 7: 1, 8: 3}
    assert service.calls_for(1, 20) == 0
    assert service.calls_for(3, 20) == 0
    assert service.calls_for(5, 20) == 40
    assert service.calls_for(8, 20) == 60


def test_test_1_is_not_badged_as_needing_a_live_model() -> None:
    """`docs/08` §4 test 1 — "it needs no new model calls". The card said the opposite."""
    from twinlab.services.lab import VALIDITY_TESTS

    by_number = {card.number: card for card in VALIDITY_TESTS}
    assert by_number[1].needs_live_model is False
    assert by_number[3].needs_live_model is False
    # Every test the call table prices at zero must also be unbadged, and vice versa.
    for number, card in by_number.items():
        assert card.needs_live_model == (vt.CALLS_PER_TWIN[number] > 0), number


# --------------------------------- accept 2: test 1 scores the H2 block and reports a CI


async def test_test_1_scores_against_the_h2_block_and_reports_a_paired_gap(backend) -> None:
    """`docs/11` M13 accept 2. `docs/08` §4 test 1."""
    twin_ids = await _seed_twins(backend, n=6)
    await _seed_session(backend, twin_ids)

    outcome = await service.run_validity_test(
        1, session_id=SESSION_ID, backend=backend, append=False
    )

    assert outcome.twins_n == len(twin_ids)
    for key in ("mae_own", "mae_other", "gap", "gap_ci_lower", "gap_ci_upper"):
        assert key in outcome.statistics
    assert outcome.verdict in ("PASS", "CHECK", "FAIL")
    # The scoring is on the 16 H2 items, which is what `docs/08` §4 test 1 re-bases onto.
    assert len(reference().holdout_h2_item_ids) == 16


def test_a_paired_gap_with_no_spread_reports_no_interval() -> None:
    """An uncomputable interval is ``None``, and ``None`` never counts as excluding zero.

    Reporting a zero-width interval around an identical set of gaps would make "we could not
    measure the spread" indistinguishable from "the spread is zero", and only one of them is
    evidence that the gap is real.
    """
    flat = vt.paired_gap([0.8, 0.8, 0.8])
    assert flat.sd == 0.0
    assert flat.ci_lower is None and flat.ci_upper is None
    assert flat.excludes_zero is False
    assert vt.paired_gap([]).n == 0
    assert vt.paired_gap([1.0]).sd is None


def test_the_wrong_person_verdict_can_fail() -> None:
    """The gate proves it rejects a violation: a twin no closer to its own driver `FAIL`s."""
    same = {f"t{i}": 1.0 for i in range(5)}
    worse = {f"t{i}": 0.5 for i in range(5)}
    assert vt.wrong_person(own_errors=same, other_errors=worse).verdict == "FAIL"
    narrow = vt.wrong_person(
        own_errors={"a": 1.0, "b": 1.0}, other_errors={"a": 1.2, "b": 1.2}
    )
    assert narrow.verdict == "CHECK"        # positive but under half a point


def test_the_pairing_never_pairs_a_twin_with_itself() -> None:
    """`docs/08` §4 test 1's "a different, randomly paired driver". Structurally a derangement."""
    ids = [f"t{i}" for i in range(9)]
    for seed in range(25):
        pairs = service.pair_with_another(ids, seed=seed)
        assert set(pairs) == set(ids)
        assert all(pairs[t] != t for t in ids), seed
    # Reproducible from the seed, which is what makes the test re-runnable (docs/09 §2).
    assert service.pair_with_another(ids, seed=3) == service.pair_with_another(ids, seed=3)
    assert service.pair_with_another(["only"], seed=1) == {}


# ------------------------------------- accept 3: zero twins is INCONCLUSIVE, never PASS


def test_a_zero_twin_outcome_cannot_even_be_constructed() -> None:
    """I15, `docs/08` §5. The impossible row does not survive to the write."""
    with pytest.raises(ValueError, match="concluded nothing"):
        ValidityOutcome(
            test_id="wrong_person", twins_n=0, verdict="PASS",
            headline="twins are about their own driver", detail="x",
        )
    assert vt.inconclusive(1, "nobody").verdict == "INCONCLUSIVE"


async def test_the_ddl_constraint_rejects_a_pass_on_zero_twins(backend) -> None:
    """`docs/11` M13 accept 3 — **assert the DDL constraint rejects the alternative** (I15).

    The in-memory backend mirrors `validity_zero_n`, so the invariant is tested in CI rather than
    only in Postgres. Injecting the violation is the whole test: the prototype stored exactly this
    row and called it a finding.
    """
    with pytest.raises(DbError, match="validity_zero_n"):
        await backend.insert(
            "validity_results",
            [{
                "test_id": "wrong_person", "twins_n": 0, "mode": "live", "provider": "ollama",
                "model": "gpt-oss:120b", "statistics": {}, "verdict": "PASS",
                "headline": "twins are about their own driver", "detail": "x",
                "config_version": 1,
            }],
        )
    # The same row is storable the moment it tells the truth about what it measured.
    await backend.insert(
        "validity_results",
        [{
            "test_id": "wrong_person", "twins_n": 0, "mode": "live", "provider": "ollama",
            "model": "gpt-oss:120b", "statistics": {}, "verdict": "INCONCLUSIVE",
            "headline": "no twin had a stored H2 vector", "detail": "x", "config_version": 1,
        }],
    )


async def test_the_service_refuses_to_append_a_pass_on_zero_twins(backend) -> None:
    """The service checks it too, at the line the prototype's defect went through."""
    outcome = vt.inconclusive(1, "nobody")
    forced = outcome.model_copy(update={"verdict": "PASS"})   # bypasses the validator
    with pytest.raises(service.ValidityRunError, match="ran on nobody"):
        await service.append_result(forced, backend=backend)


async def test_a_test_with_no_evidence_records_inconclusive(backend) -> None:
    """An empty database yields `INCONCLUSIVE` rows, not an exception and not a `PASS`."""
    for number in (1, 3):
        outcome = await service.run_validity_test(number, backend=backend)
        assert outcome.verdict == "INCONCLUSIVE"
        assert outcome.twins_n == 0
    rows = await backend.select("validity_results", None)
    assert len(rows) == 2
    assert {r["verdict"] for r in rows} == {"INCONCLUSIVE"}


async def test_a_floor_that_was_never_measured_is_not_assumed(backend) -> None:
    """`docs/07` §6. Five tests judge against the `00000` floor; none of them invents one."""
    for number in (2, 4, 5, 6, 8):
        assert vt._floor_or_inconclusive(number, None) is not None
        assert vt._floor_or_inconclusive(number, 0.05) is None
    assert await service.noise_floor(None, backend) is None
    assert await service.noise_floor(SESSION_ID, backend) is None


# ---------------------------------------------- accept 4: every completed test APPENDS


async def test_every_completed_test_appends_and_never_replaces(backend) -> None:
    """`docs/11` M13 accept 4, I9. Running the same test twice leaves **two** rows."""
    twin_ids = await _seed_twins(backend, n=5)
    await _seed_session(backend, twin_ids)

    first = await service.run_validity_test(1, session_id=SESSION_ID, backend=backend)
    second = await service.run_validity_test(1, session_id=SESSION_ID, backend=backend)

    rows = await backend.select("validity_results", [("eq", "test_id", "wrong_person")])
    assert len(rows) == 2
    assert first.verdict == second.verdict
    assert len({r["validity_run_id"] for r in rows}) == 2


def test_the_service_has_no_update_path_for_a_result() -> None:
    """I9 by construction: nothing in this module updates or deletes `validity_results`."""
    import inspect

    source = inspect.getsource(service)
    for forbidden in (".update(", ".delete("):
        assert f'"validity_results"{forbidden}' not in source
    assert 'await db.insert(\n        "validity_results"' in source


# ------------------------------------------------- accept 5: test 4's probe is quarantined


def test_the_probe_is_flagged_and_carries_no_version_code() -> None:
    """`docs/11` M13 accept 5. The absence of a version code is the enforcement."""
    probe = vt.contradictory_probe()
    assert probe.synthetic_probe is True
    assert not hasattr(probe, "version_code")
    assert "minimum payment" in probe.paragraphs["L1"]
    assert "reduce the amount paid" in probe.paragraphs["L1"]
    with pytest.raises(ValueError):                       # the flag cannot be turned off
        ProbeStimulus(probe_id="x", synthetic_probe=False, paragraphs={}, contradiction="y")


async def test_the_probe_is_refused_at_the_variants_write(backend) -> None:
    """`docs/11` M13 accept 5 — **never written to `variants`**, enforced at the write.

    The violation is injected and the refusal watched, because a guard nobody has seen reject
    something is a guard nobody has tested.
    """
    repo = VariantRepo(backend)
    probe = vt.contradictory_probe()
    with pytest.raises(QuarantinedArtefact, match="synthetic_probe"):
        await repo.put(
            version_code="10000", style_version="v1",
            delta_spec={"synthetic_probe": True}, delta_hash="h",
            paragraphs=dict(probe.paragraphs), checker={"passed": True},
        )
    assert await backend.select("variants", None) == []
    # An ordinary variant still stores, so the guard is not simply refusing everything.
    await repo.put(
        version_code="10000", style_version="v1", delta_spec={"version_code": "10000"},
        delta_hash="h", paragraphs={"L1": "text"}, checker={"passed": True},
    )
    assert len(await backend.select("variants", None)) == 1


def test_the_probe_is_unreachable_from_the_dial_board() -> None:
    """The Dial board addresses cells by version code; the probe has none to be addressed by."""
    probe = vt.contradictory_probe()
    with pytest.raises(ValueError):
        validate_code(probe.probe_id)
    assert "synthetic_probe" not in str(vt.TEST_IDS)
    assert probe.label.startswith("synthetic probe")


def test_the_impossible_version_verdict_can_fail() -> None:
    """A contradiction read as an ordinary improvement is a `FAIL`."""
    rose = vt.impossible_version(
        happiness_shift=0.9,
        per_twin_happiness_shift={f"t{i}": 0.9 for i in range(4)},
        noise_floor=0.05,
    )
    assert rose.verdict == "FAIL"
    flat = vt.impossible_version(
        happiness_shift=0.01,
        per_twin_happiness_shift={f"t{i}": 0.01 for i in range(4)},
        noise_floor=0.05,
    )
    assert flat.verdict == "PASS"


# ------------------------------------------ accept 6: test 6's ablated persona is quarantined


def test_the_ablated_persona_is_flagged_and_has_no_hash() -> None:
    """`docs/11` M13 accept 6. Not a `PersonaPassage`, and nothing to hash into `twins`."""
    from twinlab.models.twin import PersonaPassage

    ablated = vt.ablate_persona(
        twin_id="UBR-001",
        persona_text=(
            "I drive a cab in Mumbai. I do not think the app treats me fairly. "
            "I can see how my fares are worked out."
        ),
        fairness_item_ids=["FAIR1", "FAIR2"],
    )
    assert ablated.ablated is True
    assert not isinstance(ablated, PersonaPassage)
    assert not hasattr(ablated, "persona_hash")
    assert "fairly" not in ablated.text
    assert "fares are worked out" in ablated.text


def test_an_ablation_that_removes_nothing_raises() -> None:
    """A no-op ablation would make test 6 compare a twin with itself and `CHECK` forever."""
    with pytest.raises(vt.ValidityInputError, match="no-op"):
        vt.ablate_persona(
            twin_id="t", persona_text="I drive a cab in Mumbai.", fairness_item_ids=["FAIR1"]
        )
    with pytest.raises(vt.ValidityInputError, match="nothing to ablate"):
        vt.ablate_persona(
            twin_id="t", persona_text="I am not treated fairly.", fairness_item_ids=[]
        )


async def test_the_ablated_persona_is_refused_at_the_twins_write(backend) -> None:
    """`docs/11` M13 accept 6 — **never hashed into `twins`**, enforced at the write."""
    ablated = AblatedPersona(twin_id="t", text="x", removed_items=["FAIR1"])
    with pytest.raises(QuarantinedArtefact, match="ablated persona"):
        assert_not_ablated(ablated)
    with pytest.raises(QuarantinedArtefact):
        assert_not_ablated({"ablated": True})
    # A real passage passes the same guard, so it is not refusing everything.
    assert_not_ablated({"ablated": False}, None, "an ordinary passage")

    from twinlab.services.studio import create_manual_twin

    with pytest.raises(QuarantinedArtefact):
        await create_manual_twin(
            city="Mumbai", service="cab", sliders={"ablated": True}, backend=backend
        )
    assert await backend.select("twins", None) == []


def test_the_ablation_verdict_has_no_fail() -> None:
    """`docs/08` §4 test 6 names `pass` and `check` only — there is no `FAIL` to be had."""
    moved = vt.ablation(
        fairness_with={"a": 5.0, "b": 5.0}, fairness_without={"a": 3.0, "b": 3.2},
        noise_floor=0.05,
    )
    assert moved.verdict == "PASS"
    stuck = vt.ablation(
        fairness_with={"a": 5.0, "b": 5.0}, fairness_without={"a": 5.0, "b": 5.0},
        noise_floor=0.05,
    )
    assert stuck.verdict == "CHECK"


# ------------------------------- accept 7: test 7 records both models and fails on a sign flip


def test_test_7_fails_on_any_metric_sign_flip() -> None:
    """`docs/11` M13 accept 7. **A sign flip is the failure that matters**, whatever `r` says."""
    index_a = {f"t{i}": float(i) for i in range(6)}
    index_b = {f"t{i}": float(i) for i in range(6)}      # r = 1.0, perfectly correlated
    flipped = vt.second_model(
        index_a=index_a, index_b=index_b,
        shifts_a={"fairness": 0.4, "happiness": 0.2},
        shifts_b={"fairness": -0.3, "happiness": 0.2},
        model_a="gpt-oss:120b", model_b="qwen3:32b",
    )
    assert flipped.verdict == "FAIL"
    assert flipped.models == ["gpt-oss:120b", "qwen3:32b"]
    assert flipped.statistics["signs_flipped"] == 1.0
    assert "fairness" in flipped.headline


def test_test_7_records_both_model_names_on_every_verdict() -> None:
    """`docs/11` M13 accept 7 — both names, not just the one that produced the headline."""
    index_a = {f"t{i}": float(i) for i in range(6)}
    agreeing = vt.second_model(
        index_a=index_a, index_b=dict(index_a),
        shifts_a={"fairness": 0.4}, shifts_b={"fairness": 0.35},
        model_a="A", model_b="B",
    )
    assert agreeing.verdict == "PASS" and agreeing.models == ["A", "B"]
    uncorrelated = vt.second_model(
        index_a={"a": 1.0, "b": 2.0, "c": 3.0}, index_b={"a": 3.0, "b": 1.0, "c": 2.0},
        shifts_a={"fairness": 0.4}, shifts_b={"fairness": 0.35},
        model_a="A", model_b="B",
    )
    assert uncorrelated.verdict == "CHECK" and uncorrelated.models == ["A", "B"]
    assert vt.second_model(
        index_a={}, index_b={}, shifts_a={}, shifts_b={}, model_a="A", model_b="B"
    ).verdict == "INCONCLUSIVE"


# ------------------------- accept 8: test 8 reports the spread and writes a recommendation


def test_test_8_reports_per_metric_spread_across_three_temperatures() -> None:
    """`docs/11` M13 accept 8. `docs/08` §4 test 8's three temperatures, and the spread."""
    assert vt.TEMPERATURES == (0.0, 0.5, 1.0)
    index_by_temp = {
        0.0: {"a": 0.10, "b": 0.10},          # collapsed: no between-twin variance
        0.5: {"a": 0.10, "b": 0.20},
        1.0: {"a": 0.05, "b": 0.40},
    }
    shifts_by_temp = {
        0.0: {"fairness": 0.30, "happiness": 0.10},
        0.5: {"fairness": 0.32, "happiness": 0.11},
        1.0: {"fairness": 0.55, "happiness": 0.12},
    }
    outcome, recommendation = vt.temperature_sweep(
        index_by_temp=index_by_temp, shifts_by_temp=shifts_by_temp, noise_floor=0.05
    )
    assert outcome.statistics["spread_fairness"] == pytest.approx(0.25, abs=1e-6)
    assert outcome.statistics["spread_happiness"] == pytest.approx(0.02, abs=1e-6)
    assert outcome.statistics["max_metric_spread"] == pytest.approx(0.25, abs=1e-6)
    assert "mean_within_twin_index_sd" in outcome.statistics
    # 0.0 collapsed to one index, so the lowest surviving temperature is recommended.
    assert recommendation.recommended == 0.5
    assert outcome.verdict == "CHECK"          # spread above the floor; never a FAIL
    assert "Recommended temperature 0.5" in outcome.headline


def test_test_8_recommends_nothing_when_every_temperature_collapses() -> None:
    """No candidate preserves between-twin variance, so nothing is recommended. Not a default."""
    flat = {t: {"a": 0.1, "b": 0.1} for t in vt.TEMPERATURES}
    rec = vt.recommend_temperature(index_by_temp=flat, max_metric_spread=0.0)
    assert rec.recommended is None
    assert "no" in rec.reason.lower()


async def test_test_8_writes_a_recommendation_and_never_the_setting(backend) -> None:
    """`docs/11` M13 accept 8 — "writes a recommended setting". **A recommendation, not the
    setting.** `TwinConfig.temperature` is frozen onto every session's config (`docs/09` §4)."""
    from twinlab.services.config import load_twin_config

    rec = vt.recommend_temperature(
        index_by_temp={0.0: {"a": 0.1, "b": 0.1}, 0.5: {"a": 0.1, "b": 0.3}},
        max_metric_spread=0.2,
    )
    await service.record_temperature_recommendation(rec, backend=backend)

    rows = await backend.select(
        "app_config", [("eq", "key", service.TEMPERATURE_RECOMMENDATION_KEY)]
    )
    assert len(rows) == 1
    assert rows[0]["value"]["recommended"] == 0.5
    assert rows[0]["value"]["reason"]
    # The live setting is untouched: applying the recommendation is the researcher's act.
    assert service.TEMPERATURE_RECOMMENDATION_KEY != "temperature"
    assert load_twin_config().temperature == 0.7


# ------------------------------------------------------------------ the six live tests


class _Recorder:
    """A stand-in for the live twin call. Counts rounds; never touches a provider."""

    def __init__(self, answers: dict[str, dict[str, int]]) -> None:
        self.answers = answers
        self.rounds: list[dict] = []

    async def __call__(self, **kwargs) -> dict[str, dict[str, int]]:
        self.rounds.append(kwargs)
        ids = kwargs.get("twin_ids") or list(self.answers)
        return {t: dict(self.answers[t]) for t in ids if t in self.answers}


async def test_a_live_test_without_a_wired_twin_call_is_inconclusive(backend) -> None:
    """Honest rather than invented: no live twin path means no result, not a made-up one."""
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    for number in (4, 5, 6, 7, 8):
        outcome = await service.run_validity_test(
            number, session_id=SESSION_ID, backend=backend, append=False
        )
        assert outcome.verdict == "INCONCLUSIVE", number
        assert outcome.twins_n == 0, number


async def test_test_4_puts_the_probe_to_the_panel_and_stores_no_variant(backend) -> None:
    """The probe reaches the twins and nothing else. `docs/08` §4 test 4."""
    ref = reference()
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    ask = _Recorder({t: {i: 3 for i in ref.battery_item_ids} for t in twin_ids})

    outcome = await service.run_validity_test(
        4, session_id=SESSION_ID, backend=backend, ask=ask, append=False
    )

    assert outcome.test_id == "impossible_version"
    assert outcome.twins_n == len(twin_ids)
    assert ask.rounds and ask.rounds[0]["purpose"] == "probe"
    assert "minimum payment" in ask.rounds[0]["paragraphs"]["L1"]
    # Nothing was filed. `variants` is what makes a stimulus reachable from the Dial board.
    assert await backend.select("variants", None) == []


async def test_test_5_asks_twice_and_test_8_asks_three_times(backend) -> None:
    """`docs/08` §4's call table, observed rather than asserted in prose: 2N and 3N."""
    ref = reference()
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    vectors = {t: {i: 3 for i in ref.battery_item_ids} for t in twin_ids}

    five = _Recorder(vectors)
    await service.run_validity_test(
        5, session_id=SESSION_ID, backend=backend, ask=five, append=False
    )
    assert [r["wording"] for r in five.rounds] == ["A", "B"]
    assert [r["reverse_order"] for r in five.rounds] == [True, False]

    eight = _Recorder(vectors)
    await service.run_validity_test(
        8, session_id=SESSION_ID, backend=backend, ask=eight, append=False
    )
    assert [r["temperature"] for r in eight.rounds] == list(vt.TEMPERATURES)


async def test_test_7_needs_a_named_second_model(backend) -> None:
    """Without a second model there is no comparison, and no comparison is `INCONCLUSIVE`."""
    ref = reference()
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    ask = _Recorder({t: {i: 3 for i in ref.battery_item_ids} for t in twin_ids})

    unnamed = await service.run_validity_test(
        7, session_id=SESSION_ID, backend=backend, ask=ask, append=False
    )
    assert unnamed.verdict == "INCONCLUSIVE"
    assert ask.rounds == []

    named = await service.run_validity_test(
        7, session_id=SESSION_ID, backend=backend, ask=ask,
        second_model_name="qwen3:32b", append=False,
    )
    assert len(named.models) == 2 and named.models[1] == "qwen3:32b"


async def test_test_2_reads_the_stored_sham_control(backend) -> None:
    """`SHAM` runs once per session before the sweep (`docs/03` §6.1), so test 2 re-reads it."""
    from twinlab.orchestrator.odometer import SHAM_CODE

    ref = reference()
    twin_ids = await _seed_twins(backend)
    await _seed_session(backend, twin_ids)
    await backend.insert(
        "runs",
        [{
            "run_id": "33333333-3333-3333-3333-333333333333", "session_id": SESSION_ID,
            "version_code": SHAM_CODE, "status": "completed", "twins_n": len(twin_ids),
            "index_value": 0.02,
        }],
    )
    await backend.insert(
        "twin_answers",
        [
            {
                "run_id": "33333333-3333-3333-3333-333333333333", "twin_id": t,
                "answers": {i: 3 for i in ref.battery_item_ids},
                "lever_order": [0, 1, 2, 3, 4], "seed": 1, "wording": "A", "model": "stub",
            }
            for t in twin_ids
        ],
    )

    outcome = await service.run_validity_test(
        2, session_id=SESSION_ID, backend=backend, append=False
    )
    assert outcome.test_id == "placebo_change"
    assert outcome.twins_n == len(twin_ids)
    assert "mean_abs_shift" in outcome.statistics
    assert "share_moved" in outcome.statistics


def test_the_placebo_verdict_can_fail() -> None:
    """A SHAM that moves like a live cell is a `FAIL`, not a shrug."""
    big = vt.placebo_change(
        sham_shifts={"fairness": 0.6, "happiness": 0.6},
        per_twin_abs_move={"a": 0.8, "b": 0.7},
        noise_floor=0.05,
        median_live_shift=0.7,
    )
    assert big.verdict == "FAIL"
    assert big.statistics["share_moved"] == 1.0
    quiet = vt.placebo_change(
        sham_shifts={"fairness": 0.01}, per_twin_abs_move={"a": 0.01},
        noise_floor=0.05, median_live_shift=0.7,
    )
    assert quiet.verdict == "PASS"


def test_the_order_and_wording_verdict_can_fail() -> None:
    """Presentation moving the metrics as much as the change itself is a `FAIL`."""
    confounded = vt.order_and_wording(
        diff_per_metric={"fairness": 0.5, "happiness": 0.5}, twins_n=10,
        noise_floor=0.05, cell_own_shift=0.6,
    )
    assert confounded.verdict == "FAIL"
    clean = vt.order_and_wording(
        diff_per_metric={"fairness": 0.01}, twins_n=10, noise_floor=0.05, cell_own_shift=0.6
    )
    assert clean.verdict == "PASS"


def test_the_simple_guesses_verdict_can_fail() -> None:
    """A twin beating neither naive predictor adds no information. `docs/08` §4 test 3."""
    useless = vt.simple_guesses(
        twin_errors={"a": 1.2}, nochange_errors={"a": 0.4}, groupshift_errors={"a": 0.5}
    )
    assert useless.verdict == "FAIL"
    partial = vt.simple_guesses(
        twin_errors={"a": 0.45}, nochange_errors={"a": 0.4}, groupshift_errors={"a": 0.5}
    )
    assert partial.verdict == "CHECK"
    good = vt.simple_guesses(
        twin_errors={"a": 0.2}, nochange_errors={"a": 0.4}, groupshift_errors={"a": 0.5}
    )
    assert good.verdict == "PASS"


# ------------------------------------------------------------------------- bookkeeping


def test_every_test_has_a_stable_id_and_a_stored_detail() -> None:
    """`docs/08` §5: each row stores a one-line `detail`, so the table reads without the doc."""
    from twinlab.services.lab import VALIDITY_TESTS

    assert sorted(vt.TEST_IDS) == list(range(1, 9))
    assert sorted(vt.TEST_DETAIL) == list(range(1, 9))
    assert len({*vt.TEST_IDS.values()}) == 8
    assert [c.number for c in VALIDITY_TESTS] == list(range(1, 9))
    for number in vt.TEST_IDS:
        assert vt.TEST_DETAIL[number].strip()


async def test_a_stored_row_carries_every_column_the_ddl_names(backend) -> None:
    """`002_v2_model.sql`'s `validity_results` columns. Read the constraints, not a `detail` key."""
    twin_ids = await _seed_twins(backend, n=3)
    await _seed_session(backend, twin_ids)
    await service.run_validity_test(1, session_id=SESSION_ID, backend=backend)

    row = (await backend.select("validity_results", None))[0]
    for column in (
        "test_id", "session_id", "twins_n", "mode", "provider", "model", "statistics",
        "verdict", "headline", "detail", "config_version",
    ):
        assert column in row, column
    assert row["mode"] in ("mock", "live")
    assert row["session_id"] == SESSION_ID


async def test_the_results_table_refuses_to_render_a_pass_on_zero_twins(backend) -> None:
    """`services/lab.validity_results` is the last gate, for a database reached another way."""
    from twinlab.services.lab import validity_results

    backend.tables.setdefault("validity_results", []).append({
        "validity_run_id": "x", "test_id": "wrong_person", "twins_n": 0, "mode": "live",
        "provider": "ollama", "model": "m", "statistics": {}, "verdict": "PASS",
        "headline": "h", "detail": "d", "config_version": 1, "created_at": "2026-01-01",
    })
    with pytest.raises(ValueError, match="ran on nobody"):
        await validity_results(backend=backend)


async def test_the_confirm_step_shows_a_budget_for_every_test(backend) -> None:
    """`docs/06` §9. Zero calls is a budget, and showing it is how the researcher learns it."""
    free = await service.validity_budget_view(1, twins=20, backend=backend)
    assert free.calls == 0
    costly = await service.validity_budget_view(8, twins=20, backend=backend)
    assert costly.calls == 60
    with pytest.raises(service.ValidityRunError):
        await service.validity_budget_view(9, twins=20, backend=backend)
