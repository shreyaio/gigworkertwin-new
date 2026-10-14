"""M9 — intake and the generator. `docs/11` M9.

The eight acceptance criteria are implemented verbatim, each named in its test.

The **contract test actually runs both implementations.** Deno is not installed, so the Edge
Function's HTTP/HMAC/Storage layer in `index.ts` is not exercised — but `rows.mjs`, the file that
builds the rows and the file `index.ts` imports unmodified, is run under Node over the committed
fixture and compared byte-for-byte with the Python. That is the half the contract is about.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from twinlab.generator.synthetic import (
    SYNTHETIC_DATA_TYPE,
    assign_arms,
    generate_batch,
    synthetic_payload,
)
from twinlab.ingest.reference_store import reference
from twinlab.ingest.replay_raw import orphaned_paths, replay_all, replay_one
from twinlab.ingest.survey_intake import (
    BadSignature,
    StorageFailed,
    UnmappedQuestion,
    build_rows,
    form_map,
    intake,
    raw_object_path,
    sign,
    verify_signature,
)
from twinlab.services.surveys import (
    DeleteBlocked,
    counts_by_type,
    delete_synthetic,
    delete_twins,
    store_batch,
    synthetic_delete_preflight,
    twin_delete_preflight,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = REPO_ROOT / "apps_script" / "sample_payload.json"
HARNESS = REPO_ROOT / "apps_script" / "contract_harness.mjs"
SECRET = "test-intake-secret"


def _payload() -> dict:
    return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))


class FakeStorage:
    """An in-memory stand-in for Supabase Storage. Records write order."""

    def __init__(self, *, fail: bool = False) -> None:
        self.objects: dict[str, str] = {}
        self.fail = fail

    def put(self, path: str, body: str) -> None:
        if self.fail:
            raise RuntimeError("storage is down")
        self.objects[path] = body

    def get(self, path: str) -> str:
        return self.objects[path]

    def list(self, prefix: str = "") -> list[str]:
        return sorted(p for p in self.objects if p.startswith(prefix))


class RefusingBackend:
    """A backend whose inserts always fail, to prove the raw object survives (I16)."""

    def __init__(self) -> None:
        self.calls = 0

    async def upsert(self, table, rows, *, on_conflict):
        self.calls += 1
        raise RuntimeError(f"insert into {table} failed")

    async def select(self, table, filters=None, **kw):
        return []


# ---------------------------------------------------------------- signature


async def test_an_unsigned_or_wrongly_signed_post_is_rejected_401():
    """`docs/11` M9, verbatim. `docs/04` §8 step 1."""
    body = json.dumps(_payload())
    storage, backend = FakeStorage(), RefusingBackend()

    for bad in (None, "", "deadbeef", sign(body, "the-wrong-secret")):
        with pytest.raises(BadSignature) as caught:
            await intake(body, bad, secret=SECRET, storage=storage, backend=backend)
        assert caught.value.status == 401

    # Nothing was stored and nothing was inserted: rejection happens before step 2.
    assert storage.objects == {}
    assert backend.calls == 0


def test_a_correct_signature_verifies_and_the_comparison_is_constant_time():
    """The gate is not vacuous, and `hmac.compare_digest` is what does the comparing."""
    import inspect

    from twinlab.ingest import survey_intake

    body = '{"a":1}'
    verify_signature(body, sign(body, SECRET), SECRET)
    verify_signature(body, sign(body, SECRET).upper(), SECRET)   # case-insensitive hex

    source = inspect.getsource(survey_intake.verify_signature)
    assert "compare_digest" in source, "a timing-variable comparison leaks the digest"


async def test_intake_refuses_when_no_secret_is_configured():
    """An unset secret must not mean "accept everything"."""
    body = json.dumps(_payload())
    with pytest.raises(BadSignature, match="no INTAKE_HMAC_SECRET"):
        await intake(body, "anything", secret="", storage=FakeStorage(), backend=RefusingBackend())


def test_the_signature_matches_the_apps_script_implementation():
    """`apps_script/intake.gs` → `hmacHex` computes hex HMAC-SHA256 over the raw UTF-8 bytes."""
    import hashlib
    import hmac as hmac_mod

    body = '{"response_id":"x"}'
    expected = hmac_mod.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    assert sign(body, SECRET) == expected
    assert len(expected) == 64


# ---------------------------------------------------------------- I16: storage before tables


async def test_the_raw_object_is_written_before_any_table_write(backend):
    """`docs/11` M9, verbatim, and I16."""
    body = json.dumps(_payload())
    storage = FakeStorage()
    result = await intake(
        body, sign(body, SECRET), secret=SECRET, storage=storage, backend=backend
    )

    path = raw_object_path(_payload()["response_id"])
    assert path in storage.objects
    assert storage.objects[path] == body, "the raw bytes are stored verbatim"
    assert result["status"] == "ok"

    rows = await backend.select("survey_submissions", None)
    assert len(rows) == 1
    assert rows[0]["raw_object_path"] == path


async def test_a_forced_insert_failure_leaves_a_replayable_object():
    """`docs/11` M9, verbatim, and I16.

    Reverse the order and a submission that failed to insert is simply gone: the driver filled in
    the form and there is no record anywhere.
    """
    body = json.dumps(_payload())
    storage, refusing = FakeStorage(), RefusingBackend()

    with pytest.raises(RuntimeError, match="insert into survey_submissions failed"):
        await intake(body, sign(body, SECRET), secret=SECRET, storage=storage, backend=refusing)

    path = raw_object_path(_payload()["response_id"])
    assert path in storage.objects, "the raw object must survive a failed insert"
    assert refusing.calls == 1


async def test_a_storage_failure_aborts_before_any_table_write(backend):
    """`docs/04` §8 step 2 — "A failure here aborts before any table write"."""
    body = json.dumps(_payload())
    with pytest.raises(StorageFailed) as caught:
        await intake(
            body, sign(body, SECRET), secret=SECRET,
            storage=FakeStorage(fail=True), backend=backend,
        )
    assert caught.value.status == 500
    assert await backend.select("survey_submissions", None) == []


async def test_replay_re_drives_an_orphaned_object(backend):
    """`docs/04` §8 — why step 2 precedes step 4."""
    body = json.dumps(_payload())
    storage, refusing = FakeStorage(), RefusingBackend()
    with pytest.raises(RuntimeError):
        await intake(body, sign(body, SECRET), secret=SECRET, storage=storage, backend=refusing)

    path = raw_object_path(_payload()["response_id"])
    assert await orphaned_paths(storage, backend) == [path]

    submission = await replay_one(path, storage=storage, backend=backend)
    assert submission["raw_object_path"] == path
    assert len(await backend.select("survey_submissions", None)) == 1

    # Now it is no longer an orphan, and replaying again changes nothing (idempotent).
    assert await orphaned_paths(storage, backend) == []
    again = await replay_all(storage=storage, backend=backend)
    assert again == {"replayed": [], "failed": []}


async def test_replay_reports_a_corrupt_object_rather_than_editing_it(backend):
    """The raw object is the immutable record; a replay never edits it."""
    storage = FakeStorage()
    storage.objects["raw/survey_broken.json"] = "{not json"
    result = await replay_all(storage=storage, backend=backend)
    assert result == {"replayed": [], "failed": ["raw/survey_broken.json"]}
    assert storage.objects["raw/survey_broken.json"] == "{not json"


# ---------------------------------------------------------------- 422 on an unmapped question


def test_an_unmapped_form_question_raises_422_rather_than_being_dropped():
    """`docs/11` M9, verbatim. `CLAUDE.md` rule 7 — losslessness is the point."""
    payload = _payload()
    payload["answers"].append({
        "section": "PART 99 — A NEW SECTION",
        "title": "A question nobody added to the map",
        "value": "5",
    })
    with pytest.raises(UnmappedQuestion) as caught:
        build_rows(payload, raw_object_path="raw/x.json")
    assert caught.value.status == 422
    assert "PART 99" in str(caught.value)


def test_every_question_in_the_sample_payload_is_mapped():
    """The gate is not vacuous: the committed fixture maps cleanly."""
    payload = _payload()
    rows = build_rows(payload, raw_object_path="raw/x.json")
    assert len(rows["answers"]) == 73
    keys = {f"{a['section']}|{a['title']}" for a in payload["answers"]}
    assert keys <= set(form_map())


# ---------------------------------------------------------------- consent statement 7


def test_a_response_without_consent_statement_7_is_stored_and_produces_no_twin():
    """`docs/11` M9, verbatim. `docs/04` §8 — statement 7 gates the twin, **not the record**."""
    payload = _payload()
    mapping = form_map()
    twin_key = next(k for k, v in mapping.items() if v == "consent:twin")
    for answer in payload["answers"]:
        if f"{answer['section']}|{answer['title']}" == twin_key:
            answer["value"] = []            # the checkbox left unticked

    rows = build_rows(payload, raw_object_path="raw/x.json")
    submission = rows["submission"]

    assert submission["consent_twin"] is False, "no twin may be built"
    # But the record is complete and kept in full.
    assert submission["consented"] is True
    assert submission["outcome"] == "complete"
    assert len(rows["answers"]) == 73


def test_consent_is_read_from_a_checkbox_list_not_a_string():
    """A Google Forms checkbox answers as a LIST.

    This is the bug the committed fixture caught: stringifying `["I agree"]` gave `"['i agree']"`,
    which matched nothing, so every consent read as false and every submission became `no_consent`
    — the entire study, silently, with no error anywhere.
    """
    payload = _payload()
    rows = build_rows(payload, raw_object_path="raw/x.json")
    assert rows["submission"]["consented"] is True
    assert rows["submission"]["consent_twin"] is True


def test_eligibility_is_recorded_but_never_used_to_exclude():
    """`docs/GOOGLE_FORM.md` — the screeners are mapped and accepted, but nothing infers from them.

    Making eligibility exclude a response is a research decision the researcher has **not** made,
    so `outcome` is never `screened_out` here. See `docs/DECISIONS.md` → M9.
    """
    payload = _payload()
    rows = build_rows(payload, raw_object_path="raw/x.json")
    # The fixture answers "Yes" to the three disqualifying screeners, so it is ineligible...
    assert rows["submission"]["eligible"] is False
    # ...and is nonetheless recorded as a complete response.
    assert rows["submission"]["outcome"] == "complete"
    assert rows["submission"]["outcome"] != "screened_out"


# ---------------------------------------------------------------- the contract test


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_edge_function_and_the_python_produce_identical_rows(tmp_path):
    """`docs/11` M9, verbatim: "**Contract test:** the Edge Function and
    `ingest/survey_intake.py` produce identical rows from `apps_script/sample_payload.json`."

    Runs `rows.mjs` — the file `index.ts` imports unmodified — under Node, and compares every
    field. Deno is absent here, so `index.ts`'s HMAC/Storage/HTTP layer is not exercised; the row
    building, which is what can silently drift, is.
    """
    path = "raw/survey_contract.json"
    proc = subprocess.run(
        ["node", str(HARNESS), str(PAYLOAD_PATH), path],
        capture_output=True, text=True, cwd=REPO_ROOT,
        env={**os.environ},
    )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)
    py = build_rows(_payload(), raw_object_path=path)

    assert js["submission"] == py["submission"], "the submission rows differ"
    assert js["answers"] == py["answers"], "the answer rows differ"
    assert len(js["answers"]) == 73


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_two_implementations_agree_on_a_missing_consent_and_an_unmapped_question(tmp_path):
    """The contract holds on the edge cases too, not only the happy fixture."""
    mapping = form_map()
    twin_key = next(k for k, v in mapping.items() if v == "consent:twin")

    payload = _payload()
    for answer in payload["answers"]:
        if f"{answer['section']}|{answer['title']}" == twin_key:
            answer["value"] = []
    edited = tmp_path / "no_twin.json"
    edited.write_text(json.dumps(payload), encoding="utf-8")

    proc = subprocess.run(
        ["node", str(HARNESS), str(edited), "raw/x.json"],
        capture_output=True, text=True, cwd=REPO_ROOT, env={**os.environ},
    )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)
    py = build_rows(payload, raw_object_path="raw/x.json")
    assert js["submission"]["consent_twin"] is False == py["submission"]["consent_twin"]
    assert js["submission"] == py["submission"]

    # And both refuse an unmapped question.
    payload["answers"].append({"section": "PART 99", "title": "unmapped", "value": "1"})
    bad = tmp_path / "unmapped.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(bad), "raw/x.json"],
        capture_output=True, text=True, cwd=REPO_ROOT, env={**os.environ},
    )
    assert proc.returncode != 0
    assert "not in form_map" in proc.stderr
    with pytest.raises(UnmappedQuestion):
        build_rows(payload, raw_object_path="raw/x.json")


def test_the_generated_edge_assets_have_not_drifted():
    """`tools/gen_edge_assets.py --check` — the Edge Function's copy of the map must match the YAML.

    The assets are generated because Deno cannot read the YAML at request time. A hand-edited copy
    is exactly the drift `docs/04` §8's one-contract rule exists to prevent, so it is a checked
    artefact like the frozen reference data.
    """
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "gen_edge_assets.py"), "--check"],
        capture_output=True, text=True, cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(["src", "."])},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "DRIFT" not in proc.stdout


# ---------------------------------------------------------------- the generator


def test_the_generator_produces_a_complete_quality_testable_submission():
    """`docs/11` M9, verbatim — all 73 items, why-text, an arm, 16 H2 and 18 H3 answers."""
    ref = reference()
    batch = generate_batch(seed=7, count=2)
    submission = batch["submissions"][0]
    answers = [a for a in batch["answers"] if a["submission_id"] == submission["submission_id"]]

    assert len(answers) == 73 == len(ref.items)
    by_item = {a["item_id"]: a for a in answers}
    assert all(by_item[i]["value_num"] is not None for i in ref.battery_item_ids)
    assert len([i for i in ref.holdout_h2_item_ids if by_item[i]["value_num"] is not None]) == 16
    assert len([i for i in ref.holdout_h3_item_ids if by_item[i]["value_num"] is not None]) == 18

    # Why-text is present, on its anchor item.
    assert [a["item_id"] for a in answers if a["why_text"]]

    # Quality-testable: consented, attention passed, an arm assigned.
    assert submission["consent_twin"] is True
    assert submission["attention_passed"] is True
    assert submission["outcome"] == "complete"
    assert submission["eligible"] is True
    assert submission["arm"] and submission["arm_source"] == "generator"
    assert submission["data_type"] == SYNTHETIC_DATA_TYPE
    assert submission["submission_id"].startswith("SYN-")


def test_every_answer_is_inside_its_own_scale():
    """A generated value outside its scale would fail the output contract downstream."""
    ref = reference()
    batch = generate_batch(seed=11, count=3)
    for answer in batch["answers"]:
        points = ref.scale_points(answer["item_id"])
        assert 1 <= answer["value_num"] <= points, answer


def test_the_same_seed_gives_an_identical_batch():
    """`docs/11` M9, verbatim (in-process half)."""
    assert generate_batch(seed=99, count=3) == generate_batch(seed=99, count=3)
    assert generate_batch(seed=99, count=3) != generate_batch(seed=100, count=3)


def test_the_same_seed_gives_an_identical_batch_across_processes():
    """`docs/11` M9, verbatim: "**across processes**".

    Run with `PYTHONHASHSEED=random`. A generator that iterated a set or used the global RNG
    anywhere passes the in-process test and then produces a different batch on the run that
    regenerates it — and a synthetic batch nobody can regenerate is not reproducible data.
    """
    import hashlib

    snippet = (
        "import json,hashlib;"
        "from twinlab.generator.synthetic import generate_batch;"
        "b=generate_batch(seed=4242,count=3);"
        "print(hashlib.sha256(json.dumps(b,sort_keys=True).encode()).hexdigest())"
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(["src", "."]),
        "PYTHONHASHSEED": "random",
    }
    digests = set()
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, "-c", snippet],
            cwd=REPO_ROOT, capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        digests.add(proc.stdout.strip())

    batch = generate_batch(seed=4242, count=3)
    local = hashlib.sha256(json.dumps(batch, sort_keys=True).encode()).hexdigest()
    assert digests == {local}, "the batch is not reproducible across processes"


def test_the_generator_makes_no_model_call():
    """`docs/11` M9, verbatim. Asserted by scanning the module, so it cannot regress quietly."""
    import inspect

    from twinlab.generator import synthetic

    source = inspect.getsource(synthetic)
    body = "\n".join(
        line for line in source.splitlines()
        if not line.strip().startswith("#")
    )
    for banned in ("get_client", "run_design", "pydantic_ai", "ModelClient", "await client"):
        assert banned not in body, f"the generator references {banned}"


def test_arms_are_balanced_within_stratum():
    """`docs/01` §5.2 — balanced within `city|service`, not merely balanced overall."""
    ref = reference()
    n_arms = len(ref.arms)
    strata = ["Mumbai|cab"] * n_arms + ["Pune|bike"] * n_arms
    arms = assign_arms(len(strata), seed=3, strata=strata)

    assert sorted(arms[:n_arms]) == sorted(ref.arms), "each stratum gets one of every arm"
    assert sorted(arms[n_arms:]) == sorted(ref.arms)
    assert assign_arms(len(strata), seed=3, strata=strata) == arms


def test_a_synthetic_payload_answers_every_mapped_question():
    """The generator cannot produce a payload live intake would reject."""
    payload = synthetic_payload(seed=1, index=0, arm="CON1")
    keys = {f"{a['section']}|{a['title']}" for a in payload["answers"]}
    assert keys == set(form_map()), "the generator and the map disagree"


# ---------------------------------------------------------------- delete synthetic


async def test_delete_synthetic_touches_no_real_row_and_no_run(backend):
    """`docs/11` M9, verbatim.

    Removes only `data_type='SYNTHETIC'`, cascades to answers and twins, and touches no real row
    and no run.
    """
    storage = FakeStorage()
    batch = generate_batch(seed=5, count=2)
    await store_batch(batch, storage=storage, backend=backend)

    # A real submission, a real twin, a synthetic twin, and a run that must all be left alone.
    real = build_rows(_payload(), raw_object_path="raw/real.json")
    await backend.upsert("survey_submissions", [real["submission"]], on_conflict="submission_id")
    await backend.upsert("survey_answers", real["answers"], on_conflict="submission_id,item_id")

    synthetic_id = batch["submissions"][0]["submission_id"]
    await backend.insert("twins", [
        {"twin_id": real["submission"]["submission_id"], "source": "real", "consent_twin": True},
        {"twin_id": synthetic_id, "source": "synthetic", "consent_twin": True},
    ])
    await backend.insert("sessions", [{"session_id": "s1", "name": "x", "config": {}}])
    await backend.insert("runs", [
        {"run_id": "r1", "session_id": "s1", "version_code": "10000", "status": "completed",
         "twins_n": 3}
    ])

    before = await counts_by_type(backend)
    assert before == {SYNTHETIC_DATA_TYPE: 2, "REAL": 1}

    result = await delete_synthetic(backend)
    assert result["submissions"] == 2
    assert result["answers"] == 146            # 73 per synthetic submission
    assert result["twins"] == 1

    assert await counts_by_type(backend) == {"REAL": 1}

    # The real submission, its answers and its twin survive.
    remaining = await backend.select("survey_submissions", None)
    assert [r["submission_id"] for r in remaining] == [real["submission"]["submission_id"]]
    assert len(await backend.select("survey_answers", None)) == 73
    twins = await backend.select("twins", None)
    assert [t["twin_id"] for t in twins] == [real["submission"]["submission_id"]]

    # And no run was touched.
    assert len(await backend.select("runs", None)) == 1


async def test_delete_synthetic_on_an_empty_database_is_a_no_op(backend):
    """A delete that reports work it did not do is worse than one that reports none."""
    assert await delete_synthetic(backend) == {
        "submissions": 0,
        "answers": 0,
        "twins": 0,
        # ARCHITECTURE_UPDATE.md §3.4: `studio_runs` is now deleted with the twin, and the twins a
        # delete refuses are reported by name. Both are zero and empty on an empty database.
        "studio_runs": 0,
        "blocked": [],
    }


async def test_a_stored_batch_writes_its_raw_objects_first(backend):
    """I16 — a synthetic row with no replayable object is a different kind of record."""
    storage = FakeStorage()
    batch = generate_batch(seed=13, count=2)
    await store_batch(batch, storage=storage, backend=backend)

    assert len(storage.objects) == 2
    assert await orphaned_paths(storage, backend) == [], "every object has a row"


# ==================================================================== docs/06 §4, the generator
#
# The dashboard's controls. M9 built the engine and `docs/11` never assigned the page a
# milestone, so these cover the binding between a control and the draw it changes — not the
# wording of any label.


def test_a_spec_is_deterministic_in_seed_and_spec():
    """`docs/09` §2's guarantee, now that a batch has parameters as well as a seed."""
    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(seed=4, count=5, sentiment="frustrated", woman_share=0.5)
    first = generate_batch(seed=4, count=5, spec=spec)
    second = generate_batch(seed=4, count=5, spec=spec.model_copy())

    assert first["submissions"] == second["submissions"]
    assert first["answers"] == second["answers"]


def test_two_specs_that_differ_draw_different_batches():
    """A control that changes nothing is worse than no control."""
    from twinlab.models.view import GeneratorSpec

    calm = generate_batch(seed=4, count=5, spec=GeneratorSpec(seed=4, sentiment="content"))
    cross = generate_batch(seed=4, count=5, spec=GeneratorSpec(seed=4, sentiment="frustrated"))

    def mean(batch: dict) -> float:
        values = [float(a["value_num"]) for a in batch["answers"] if a.get("value_num")]
        return sum(values) / len(values)

    assert mean(calm) > mean(cross), "the sentiment preset must move the answers"


def test_omitting_the_spec_still_produces_a_complete_submission():
    """M9's acceptance criterion, unchanged by §4's controls."""
    ref = reference()
    batch = generate_batch(seed=11, count=1)

    answered = {a["item_id"] for a in batch["answers"]}
    assert answered == set(ref.items), "every register item must still be answered"


def test_city_weights_of_zero_exclude_a_city_entirely():
    """`docs/06` §4's weights are relative, and zero means "do not draw this one"."""
    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(
        seed=9, city_weights={"Mumbai": 1.0, "Pune": 0.0, "Delhi": 0.0, "Bengaluru": 0.0}
    )
    batch = generate_batch(seed=9, count=12, spec=spec)

    assert {s["city"] for s in batch["submissions"]} == {"Mumbai"}


def test_a_spec_with_no_positive_weight_is_refused():
    """A batch with no city to draw from is not a batch. Never silently fall back to uniform."""
    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(seed=9, city_weights={"Mumbai": 0.0, "Pune": 0.0})
    with pytest.raises(ValueError, match="at least one positive value"):
        generate_batch(seed=9, count=1, spec=spec)


def test_attention_failures_are_generated_only_when_asked_for():
    """Zero by default: a respondent who fails is screened out and can never make a twin."""
    from twinlab.models.view import GeneratorSpec

    clean = generate_batch(seed=5, count=20)
    assert all(s["attention_passed"] for s in clean["submissions"])

    spec = GeneratorSpec(seed=5, attention_fail_share=1.0)
    failing = generate_batch(seed=5, count=20, spec=spec)
    assert not any(s["attention_passed"] for s in failing["submissions"])


def test_a_construct_target_moves_only_that_constructs_items():
    """A slider is bound to one construct; it must not leak into the others.

    The sliders are **absolute 1-7 targets** rather than offsets (docs/06 section 4: "average
    answer on a 1 to 7 scale"), so the bumped batch names a high target and the flat one names
    none at all.
    """
    from twinlab.models.reference import construct_code_for
    from twinlab.models.view import GeneratorSpec

    ref = reference()
    flat = generate_batch(seed=3, count=8, spec=GeneratorSpec(seed=3))
    bumped = generate_batch(
        seed=3, count=8, spec=GeneratorSpec(seed=3, construct_targets={"FAIR": 7.0})
    )

    def by_construct(batch: dict, code: str) -> float:
        values = [
            float(a["value_num"])
            for a in batch["answers"]
            if a.get("value_num") is not None
            and construct_code_for(ref.items[a["item_id"]]) == code
        ]
        return sum(values) / len(values)

    assert by_construct(bumped, "FAIR") > by_construct(flat, "FAIR")
    assert by_construct(bumped, "EXIT") == by_construct(flat, "EXIT"), "the nudge leaked"


def test_the_batch_records_the_spec_and_the_generator_version():
    """Reproducing a batch needs the values used, not the ones that were on disk.

    The config file was written into every batch as provenance while **none of its values were
    read** — `likert_sd` and `mc_correct_rate` were hard-coded literals that happened to match.
    """
    from twinlab.generator.synthetic import GENERATOR_VERSION
    from twinlab.models.view import GeneratorSpec

    spec = GeneratorSpec(seed=2, sentiment="content", woman_share=0.25)
    batch = generate_batch(seed=2, count=2, spec=spec)
    config = batch["batch"]["config"]

    assert config["generator_version"] == GENERATOR_VERSION
    assert config["spec"]["sentiment"] == "content"
    assert config["spec"]["woman_share"] == 0.25
    assert config["spec"]["seed"] == 2


def test_spec_from_config_reads_the_config_file_rather_than_restating_it():
    """`config/generator.default.yaml` must actually drive the draw it documents."""
    from twinlab.generator.synthetic import generator_config, spec_from_config

    config = generator_config()
    spec = spec_from_config(seed=1)

    assert spec.likert_sd == float(config["likert_sd"])
    assert spec.mc_correct_rate == float(config["mc_correct_rate"])
    assert spec.completion_seconds_range == (
        int(config["completion_seconds_min"]),
        int(config["completion_seconds_max"]),
    )


def test_preview_takes_no_backend_and_writes_nothing(backend):
    """`docs/06` §4: *Preview 3 drivers* "derives a preview only, inserts nothing".

    Asserted structurally as well as behaviourally: `preview` has no `backend` parameter, so it
    has no handle to write with.
    """
    import inspect

    from twinlab.services.generator import preview

    assert "backend" not in inspect.signature(preview).parameters

    from twinlab.models.view import GeneratorSpec

    rows = preview(GeneratorSpec(seed=8, count=40), n=3)

    assert len(rows) == 3
    assert all(r.items_answered > 0 for r in rows)
    # Nothing reached the database: the fixture's backend is still empty.
    assert all(not stored for stored in backend.tables.values())


def test_every_sentiment_slider_names_a_real_construct():
    """A slider bound to a construct the register does not have would move nothing."""
    from twinlab.models.reference import CONSTRUCTS
    from twinlab.services.generator import SENTIMENT_SLIDERS

    codes = {c.code for c in CONSTRUCTS}
    for label, code in SENTIMENT_SLIDERS:
        assert code in codes, f"{label!r} is bound to {code!r}, which is not a construct"


def test_every_docs06_s4_control_is_bound_to_a_spec_field():
    """docs/05 section 8.2: never drop a specified element. Every section 4 control HAS a parameter.

    The five reaction sliders and the captive-voice checkbox used to be listed on the page as
    "not built", because they were read as describing a mock twin. They describe the synthetic
    respondent instead - an H2 answer moves by the assigned arm and an H3 answer by that
    version's own code - so there is a parameter for each and the notice is gone.
    """
    from twinlab.models.reference import CONSTRUCTS, LEVERS
    from twinlab.models.view import GeneratorSpec
    from twinlab.services.generator import (
        BATCH_SLIDERS,
        REACTION_SLIDERS,
        SENTIMENT_PRESETS,
        SENTIMENT_SLIDERS,
    )

    spec = GeneratorSpec(seed=1)
    codes = {c.code for c in CONSTRUCTS}

    for label, code in SENTIMENT_SLIDERS:
        assert code in codes, f"{label!r} is bound to {code!r}, which is not a construct"
    for _label, field, low, high, _step in BATCH_SLIDERS:
        value = getattr(spec, field)
        assert low <= value <= high, f"{field} default {value} is outside its own slider"
    # Every lever has a reaction slider, and every slider names a real lever, in I2's order.
    assert [lever for _label, lever in REACTION_SLIDERS] == list(LEVERS)
    assert set(spec.lever_reactions) == set(LEVERS)
    assert isinstance(spec.captive_voice, bool)
    # A preset fills every construct slider, so pressing one cannot leave a slider behind.
    for preset, values in SENTIMENT_PRESETS.items():
        assert set(values) == {code for _label, code in SENTIMENT_SLIDERS}, preset


def test_the_reaction_sliders_move_the_holdout_blocks():
    """The controls are bound to the ANSWERS, not merely to a field on the spec.

    H3 asks about six real version codes (docs/01 section 3.6). With every reaction at zero the
    six versions must answer alike; at the default weights the version that raises four dials
    must separate from the one that raises two.
    """
    from twinlab.models.view import GeneratorSpec

    def fair_by_version(spec: GeneratorSpec) -> dict[str, float]:
        batch = generate_batch(seed=12, count=60, spec=spec)
        sums: dict[str, list[float]] = {}
        for answer in batch["answers"]:
            item = answer["item_id"]
            if item.startswith("H3_") and item.endswith("_FAIR"):
                sums.setdefault(item, []).append(float(answer["value_num"]))
        return {k: sum(v) / len(v) for k, v in sums.items()}

    levers = ("L1", "L2", "L3", "L4", "L5")
    dead = fair_by_version(
        GeneratorSpec(seed=12, lever_reactions=dict.fromkeys(levers, 0.0))
    )
    live = fair_by_version(GeneratorSpec(seed=12))

    # V1 is 12220, Fairwork 7. V3 is 11010, Fairwork 3.
    assert abs(dead["H3_V1_FAIR"] - dead["H3_V3_FAIR"]) < 0.25, "no reaction, yet it moved"

    # The sliders are bound to the ANSWERS: with every reaction at zero the holdout sits at the
    # baseline, and at the default weights it has moved a long way from it. This is the binding
    # check and it is unconditional.
    assert live["H3_V1_FAIR"] - dead["H3_V1_FAIR"] > 1.0, "the reaction sliders did nothing"

    # **How far V1 separates from V3 is now a calibrated quantity, not a free one** (`v11`).
    # `holdout_version_differentiation` is fitted to the one real respondent, who answered the
    # six versions within a range of exactly one scale point, so at the shipped 0.18 this
    # separation is deliberately small. The assertion is therefore split in two, and the strong
    # half is kept: the SEPARATION IS STILL THERE, and the MATRIX still produces the full
    # separation when the compression is off. If that second assertion ever fails, the lever
    # matrix really has stopped differentiating the versions, which is the defect `v5` removed.
    assert live["H3_V1_FAIR"] > live["H3_V3_FAIR"], (
        "the version that raises four dials must still rank above the one that raises two"
    )
    # Both response-style layers off, so what is measured is the MATRIX. `endpoint_avoidance`
    # pulls answers off the ceiling, which narrows the gap between two versions that both sit
    # near the top of the scale — a real effect of a real parameter, and not the thing this
    # assertion is about.
    uncompressed = fair_by_version(
        GeneratorSpec(
            seed=12, holdout_version_differentiation=1.0, endpoint_avoidance=0.0
        )
    )
    assert uncompressed["H3_V1_FAIR"] - uncompressed["H3_V3_FAIR"] > 0.5, (
        "with the holdout compression off, the matrix must separate the two versions as it "
        "always did — the compression describes how a person REPORTS a hypothetical, and must "
        "not have reached the lever matrix"
    )


# ------------------------------------------------------- purging synthetic test sessions


async def _blocked_batch(backend, storage, *, n=3, real_on_panel=False):
    """A synthetic batch whose twins sit on a frozen panel and have answered a run.

    This is the state a researcher is actually in after testing: the synthetic twins cannot be
    deleted, because deleting them would change the stored result of the run they answered.
    """
    batch = generate_batch(seed=909, count=n)
    await store_batch(batch, storage=storage, backend=backend)
    ids = [s["submission_id"] for s in batch["submissions"]]
    await backend.insert(
        "twins", [{"twin_id": i, "source": "synthetic", "consent_twin": True} for i in ids]
    )
    await backend.insert("sessions", [{"session_id": "sess", "name": "My test sweep",
                                       "config": {}}])
    await backend.insert("runs", [
        {"run_id": "run1", "session_id": "sess", "version_code": "10000",
         "status": "completed", "twins_n": n}
    ])
    panel = [
        {"session_id": "sess", "twin_id": i, "stratum": "Mumbai|cab", "position": p}
        for p, i in enumerate(ids)
    ]
    answers = [
        {"answer_id": f"a{p}", "run_id": "run1", "twin_id": i, "answers": {},
         "lever_order": [1, 2, 3, 4, 5], "seed": 1, "wording": "A", "model": "m"}
        for p, i in enumerate(ids)
    ]
    if real_on_panel:
        await backend.insert(
            "twins", [{"twin_id": "UBR-REAL", "source": "real", "consent_twin": True}]
        )
        panel.append(
            {"session_id": "sess", "twin_id": "UBR-REAL", "stratum": "Pune|cab", "position": n}
        )
    await backend.insert("session_panel", panel)
    await backend.insert("twin_answers", answers)
    # A validity verdict computed on this panel, which the purge must also withdraw: a verdict
    # about twins that no longer exist describes nothing.
    await backend.insert("validity_results", [
        {"validity_run_id": "v1", "session_id": "sess", "test_id": "wrong_person",
         "twins_n": n, "statistics": {}, "verdict": "FAIL", "headline": "h", "detail": "d"}
    ])
    return ids


async def test_the_preflight_tells_a_synthetic_only_session_from_a_mixed_one(backend):
    """The distinction the whole feature rests on. `purge_sessions` may take the first, never
    the second."""
    ids = await _blocked_batch(backend, FakeStorage())
    pre = await synthetic_delete_preflight(backend)
    assert pre["blocked_twin_ids"] == sorted(ids), "the twins should be blocked to begin with"
    assert pre["purgeable_session_ids"] == ["sess"]
    assert pre["mixed_session_ids"] == []
    assert pre["dependent_sessions"][0]["name"] == "My test sweep"
    assert pre["dependent_sessions"][0]["real_twin_ids"] == []


async def test_a_session_holding_one_real_driver_is_not_synthetic_only(backend):
    """One real twin on the panel makes the session real evidence, whatever else is on it."""
    await _blocked_batch(backend, FakeStorage(), real_on_panel=True)
    pre = await synthetic_delete_preflight(backend)
    assert pre["purgeable_session_ids"] == []
    assert pre["mixed_session_ids"] == ["sess"]
    assert pre["dependent_sessions"][0]["real_twin_ids"] == ["UBR-REAL"]


async def test_purge_sessions_clears_the_whole_batch_and_leaves_nothing_dangling(backend):
    """What the researcher asked for: delete all, with no orphaned result left behind.

    The point is the *second* half of that sentence. Deleting the twins while keeping the `runs`
    row would leave a stored `index_value` computed over twins that no longer exist — a number
    nobody can audit or reproduce, which is a worse breach of rule 6 than the refusal it replaced.
    The session goes as one unit: panel, runs, answers and validity verdict together.
    """
    await _blocked_batch(backend, FakeStorage())
    result = await delete_synthetic(backend, purge_sessions=True)

    assert result["twins"] == 3, "every synthetic twin should now be gone"
    assert result["blocked"] == []
    assert result["purged"]["sessions"] == 1
    assert result["purged"]["validity_results"] == 1
    assert result["purged"]["twin_answers"] == 3

    for table in ("twins", "sessions", "runs", "twin_answers", "session_panel",
                  "validity_results", "survey_submissions"):
        assert await backend.select(table, None) == [], f"{table} still holds a row"


async def test_deleting_synthetic_never_touches_a_session_holding_a_real_twin(backend):
    """*Delete all synthetic surveys* means **synthetic**, whatever is ticked.

    The Generator screen does not plumb ``allow_real_loss`` through at all, so a session mixing
    synthetic twins with a real driver is left intact and the synthetic twins sitting on it stay
    blocked. Clearing those is a per-twin decision made in Twin Lab > Twins, where the researcher
    picks the rows and is shown the real twins affected.
    """
    await _blocked_batch(backend, FakeStorage(), real_on_panel=True)
    with pytest.raises(DeleteBlocked, match="rule 6"):
        await delete_synthetic(backend, purge_sessions=True)
    # The real twin, the session, its run and its verdict are all untouched.
    assert len(await backend.select("sessions", None)) == 1
    assert len(await backend.select("runs", None)) == 1
    assert len(await backend.select("validity_results", None)) == 1
    assert any(
        t["twin_id"] == "UBR-REAL" for t in await backend.select("twins", None)
    ), "the real twin must survive a synthetic delete"


async def test_allow_real_loss_is_the_per_twin_route_and_is_opt_in(backend):
    """The capability exists for Twin Lab > Twins, and only takes effect when asked for.

    It withdraws the contaminated session, which costs the real driver their run answers and
    panel place. Their **survey, answers and twin row survive** — `delete_synthetic` matches
    `twins` on ``source = synthetic`` — so nothing hard to replace is lost.
    """
    await _blocked_batch(backend, FakeStorage(), real_on_panel=True)
    result = await delete_synthetic(backend, purge_sessions=True, allow_real_loss=True)

    assert result["twins"] == 3, "the synthetic twins should now be gone"
    assert await backend.select("sessions", None) == []
    assert await backend.select("twin_answers", None) == []
    # The real driver keeps their twin row, and with it their persona.
    surviving = [t["twin_id"] for t in await backend.select("twins", None)]
    assert surviving == ["UBR-REAL"]


async def test_purge_is_off_by_default(backend):
    """The old refusal is unchanged unless the researcher explicitly asks for the purge."""
    await _blocked_batch(backend, FakeStorage())
    with pytest.raises(DeleteBlocked, match="rule 6"):
        await delete_synthetic(backend)
    assert len(await backend.select("sessions", None)) == 1


# ------------------------------------------- per-twin delete (Twin Lab > Twins)


async def test_delete_twins_removes_an_explicit_selection_including_a_real_one(backend):
    """The researcher ticks the rows, so a real twin goes if that is what they ticked.

    The Generator's bulk delete is keyed on `data_type` and can never reach a real row. This path
    is the other half of the design: an explicit selection, which is itself the guard.
    """
    await backend.insert("twins", [
        {"twin_id": "UBR-1", "source": "real", "consent_twin": True},
        {"twin_id": "SYN-1", "source": "synthetic", "consent_twin": True},
        {"twin_id": "UBR-2", "source": "real", "consent_twin": True},
    ])
    for i in ("UBR-1", "SYN-1", "UBR-2"):
        await backend.upsert(
            "survey_submissions",
            [{"submission_id": i, "data_type": "REAL", "outcome": "completed"}],
            on_conflict="submission_id",
        )

    result = await delete_twins(["UBR-1", "SYN-1"], backend)
    assert result["twins"] == 2
    assert result["real_twins"] == ["UBR-1"]
    assert result["submissions"] == 2, "deleting a twin deletes the survey it was built from"
    assert [t["twin_id"] for t in await backend.select("twins", None)] == ["UBR-2"]


async def test_delete_twins_refuses_a_twin_that_is_evidence_unless_sessions_go_too(backend):
    """Rule 6, from the other direction: a twin may not leave a result computed over it behind."""
    ids = await _blocked_batch(backend, FakeStorage())
    with pytest.raises(DeleteBlocked, match="withdraw their sessions"):
        await delete_twins(ids[:1], backend)
    assert len(await backend.select("twins", None)) == 3

    result = await delete_twins(ids[:1], backend, purge_sessions=True)
    assert result["twins"] == 1
    assert result["purged"]["sessions"] == 1
    assert await backend.select("runs", None) == []


async def test_the_preflight_names_the_twins_that_would_be_caught_in_the_blast(backend):
    """Deleting two twins must not silently void a run forty others answered.

    ``collateral_twin_ids`` is what the confirm screen shows. Without it the researcher ticks one
    row, loses a session, and finds out afterwards that nine other twins' answers went with it.
    """
    ids = await _blocked_batch(backend, FakeStorage(), n=4)
    pre = await twin_delete_preflight(ids[:1], backend)
    assert pre["twin_ids"] == ids[:1]
    assert pre["blocked_twin_ids"] == ids[:1]
    assert pre["collateral_twin_ids"] == sorted(ids[1:]), (
        "the other three twins on that session are collateral and must be named"
    )


async def test_delete_twins_can_keep_the_survey_for_a_re_import(backend):
    """``delete_surveys=False`` drops the twin and leaves the respondent's answers to re-import."""
    await backend.insert(
        "twins", [{"twin_id": "UBR-9", "source": "real", "consent_twin": True}]
    )
    await backend.upsert(
        "survey_submissions",
        [{"submission_id": "UBR-9", "data_type": "REAL", "outcome": "completed"}],
        on_conflict="submission_id",
    )
    result = await delete_twins(["UBR-9"], backend, delete_surveys=False)
    assert result["twins"] == 1
    assert result["submissions"] == 0
    assert len(await backend.select("survey_submissions", None)) == 1


async def test_delete_twins_on_an_empty_selection_does_nothing(backend):
    """A delete that reports work it did not do is worse than one that reports none."""
    assert await delete_twins([], backend) == {
        "twins": 0, "submissions": 0, "answers": 0, "purged": {}, "blocked": [],
    }


def test_the_salience_pre_flight_orders_the_mix_and_reports_the_null_as_a_null():
    """`v10`'s service half, beside `clipping`. Derives only, and takes no backend.

    The ordering is what the screen reads first — a note that opened on a 4% lever would tell the
    researcher nothing — and the empty list is `docs/06` §4's no-reaction batch, which the page
    says out loud rather than rendering nothing (`CLAUDE.md` rule 7).
    """
    from twinlab.models.reference import LEVERS
    from twinlab.models.view import GeneratorSpec
    from twinlab.services.generator import SALIENCE_NOTICE_SHARE, salience

    mix = salience(GeneratorSpec(seed=1))
    assert [row.share_value for row in mix] == sorted(
        (row.share_value for row in mix), reverse=True
    ), "the note must open on the lever most of the batch cares about"
    assert mix[0].lever == "L1" and mix[0].label == "Pay", (
        "the default weighting doubles pay, so the batch's top salience is pay"
    )
    assert mix[0].share_value > SALIENCE_NOTICE_SHARE, (
        "the default batch is pay-dominated enough to warrant the warning branch, which is the "
        "number Route A owes the researcher"
    )
    assert all(row.label != row.lever for row in mix), "every lever has §4's own label"

    # The no-reaction null: no driver has a change that matters most to them.
    assert salience(
        GeneratorSpec(seed=1, lever_reactions=dict.fromkeys(LEVERS, 0.0))
    ) == []


def test_the_salience_note_distinguishes_a_dominated_batch_from_a_mixed_one():
    """The screen must not call a pay-dominated batch and a mixed one the same thing.

    `v10`'s repair is that every persona *states* the batch's weighting. Whether the batch also
    contains drivers who want different things is a separate claim, and the note is where the
    researcher reads which one they are about to generate.
    """
    from twinlab.models.reference import LEVERS
    from twinlab.models.view import GeneratorSpec
    from twinlab.services.generator import salience
    from twinlab.ui.pages.generator import _salience_note

    dominated = _salience_note(salience(GeneratorSpec(seed=1, salience_spread=0.0)))
    assert "tl-note-warn" in dominated and "Pay" in dominated

    flat = GeneratorSpec(
        seed=1, lever_reactions=dict.fromkeys(LEVERS, 1.0), salience_spread=0.5
    )
    mixed = _salience_note(salience(flat))
    assert "tl-note-warn" not in mixed and "tl-note-info" in mixed

    off = GeneratorSpec(seed=1, lever_reactions=dict.fromkeys(LEVERS, 0.0))
    null = _salience_note(salience(off))
    assert "no-reaction null" in null, "an empty mix must be reported, never rendered as nothing"
