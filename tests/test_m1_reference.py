"""M1 acceptance tests — reference data and schema. `docs/11` → M1.

The eight source-built reference files are frozen: every test here that touches them asserts
they did **not** change. `arms.json` and `legacy_crosswalk.json` are new in 2.0 and are tested
for the properties `docs/01` §4 and §5 specify.

The struck acceptance test is M1's ZeroGPU background-task smoke test: the deployment target is
local execution (`HANDOFF.md` §0.6), so there is no Space to survive on.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from config.settings import REFERENCE_DIR
from twinlab.ingest import build_reference
from twinlab.ingest.reference_store import (
    REFERENCE_FILES,
    ReferenceCountError,
    ReferenceData,
    reference,
    reference_hash,
)
from twinlab.ingest.seed_db import (
    REFERENCE_CONFIG_KEY,
    SeedError,
    assert_seeded,
    build_rows,
    seed,
)
from twinlab.models.reference import (
    ATTENTION_ITEMS,
    CONSTRUCTS,
    MET_CRITERIA,
    REVERSE_CODED_ITEMS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The eight frozen files and their sha256, recorded before the 2026-09-28 rebuild wiped `src/`
#: (`_preserve/frozen_reference.sha256`). Hard-coded here so the guard does not depend on a
#: scaffolding directory that is deleted once the repository is in git.
FROZEN_SHA256 = {
    "chunk_criterion_links.json":
        "4b1f284825bd57dadc3c8c8dbe090f98de285cc1fe9f66903af23ec7ce49f93a",
    "corpus_chunks.json":
        "464860cf0397e820d1f04d123df65946f1a7490875c142df6d95ad70e6b4026b",
    "criteria.json":
        "c2ff701da55ab2cd44e8f824a6bed54c41a6bae9d6cc999b9fae30d9f956bdce",
    "criterion_findings.json":
        "b9c8ee558a3f8e3717e70b599047512b7c36756f091d6d5f9db1aa7ec960f5eb",
    "dial_lookup.json":
        "d8ea9d3615d05c412fa24aab46856971884b5c9b00d21d4620af9e7476b43dbb",
    "gaps.json":
        "dc2f64139c79a5ebff0db66b809a42df943d0c5c3f5f4f72947302de207129fe",
    "instrument.json":
        "1ad278d5ff755b89148d7d19c4742b2b7df23e648183dd02d05470e50ec4a527",
    "thresholds.json":
        "f76465ec3ed4db362464aeab25e690b0e10a30061f0dee031ec3c349c60c3c22",
}


# --------------------------------------------------------------------------- frozen data


def test_the_eight_frozen_files_are_byte_identical():
    """`docs/11` → M1: the eight existing reference files never change.

    Hashes recorded before the rebuild. This is the regression guard for everything downstream:
    if the frozen data moved, every number in the study moved with it.
    """
    for name, want in FROZEN_SHA256.items():
        got = hashlib.sha256((REFERENCE_DIR / name).read_bytes()).hexdigest()
        assert got == want, f"{name} is no longer byte-identical"


def test_builder_check_exits_zero():
    """`build_reference.py --check` exits 0 — same sources in, same bytes out, all ten files."""
    proc = subprocess.run(
        [sys.executable, "src/twinlab/ingest/build_reference.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count("OK") == 10, proc.stdout


def test_builder_is_deterministic_in_process():
    """Two builds in one process produce identical bytes for all ten artifacts."""
    first = {k: build_reference.serialise(v) for k, v in build_reference.build().items()}
    second = {k: build_reference.serialise(v) for k, v in build_reference.build().items()}
    assert first == second


def test_ten_reference_files_exist():
    """`docs/01` §2: ten files, the last two new in 2.0."""
    assert len(REFERENCE_FILES) == 10
    for name in REFERENCE_FILES:
        assert (REFERENCE_DIR / name).exists(), name


def test_the_specified_counts():
    """`docs/11` → M1: 33 criteria, 33 findings, 30 gaps, 10 thresholds, 126 chunks, 171 links,
    73 items, 5 scales, 9 constructs, 4 arms."""
    ref = reference()
    assert len(ref.criteria) == 33
    assert len(ref.findings) == 33
    assert len(ref.gaps) == 30
    assert len(ref.thresholds) == 10
    assert len(ref.chunks) == 126
    assert len(ref.links) == 171
    assert len(ref.items) == 73
    assert len(ref.scales) == 5
    assert len(ref.constructs) == 9
    assert len(ref.arms) == 4


def test_exactly_three_met_findings_and_they_are_the_sham_set():
    """`docs/11` → M1: 3 rows with finding='Met', and they are 3.1.a, 3.1.c, 4.1.c.

    They are the SHAM commitment set (`ARCHITECTURE.md` §5.2), which is what gives the sham
    zero free parameters — its content is read, never chosen.
    """
    ref = reference()
    met = tuple(sorted(f.criterion_id for f in ref.findings.values() if f.finding == "Met"))
    assert met == MET_CRITERIA == ("3.1.a", "3.1.c", "4.1.c")
    assert not (set(met) & set(ref.gaps)), "a Met criterion must never also be a gap"


def test_every_anchors_array_length_equals_its_scale_points():
    """`docs/11` → M1, and `docs/01` §9's last assertion.

    This is the check that catches the 5-vs-7 scale error at load time rather than inside a
    metric — the prototype flattened every item to 1–7 and three of the nine constructs are
    5-point.
    """
    ref = reference()
    for scale in ref.scales.values():
        assert len(scale.anchors) == scale.points, scale.scale_id
    assert ref.scales["agree5"].points == 5
    assert ref.scales["agree7"].points == 7


def test_the_battery_is_thirty_seven_and_excludes_both_attention_checks():
    """I10: attention checks are never put to a twin. The battery is 37, not 39."""
    ref = reference()
    assert len(ref.battery_item_ids) == 37
    for item_id in ATTENTION_ITEMS:
        assert item_id not in ref.battery_item_ids
        assert ref.items[item_id].attention_check
    assert len(ref.holdout_h2_item_ids) == 16
    assert len(ref.holdout_h3_item_ids) == 18
    assert 37 + len(ATTENTION_ITEMS) + 16 + 18 == 73


def test_reverse_coded_items_are_exactly_three():
    """`docs/01` §3.1: SAT2, DEP1, and H2_SAT2 by inheritance."""
    ref = reference()
    got = tuple(sorted(i.item_id for i in ref.items.values() if i.reverse_coded))
    assert got == REVERSE_CODED_ITEMS == ("DEP1", "H2_SAT2", "SAT2")


def test_reference_hash_is_stable_and_covers_every_file(tmp_path):
    """The startup gate's digest. Stable across calls, and sensitive to any file changing."""
    first = reference_hash()
    reference_hash.cache_clear()
    assert reference_hash() == first

    copy = tmp_path / "reference"
    copy.mkdir()
    for name in REFERENCE_FILES:
        (copy / name).write_bytes((REFERENCE_DIR / name).read_bytes())
    reference_hash.cache_clear()
    assert reference_hash(copy) == first

    (copy / "arms.json").write_text("[]", encoding="utf-8")
    reference_hash.cache_clear()
    assert reference_hash(copy) != first
    reference_hash.cache_clear()


# --------------------------------------------------------------------------- constructs


def test_nine_constructs_six_of_which_enter_the_index():
    """`docs/01` §3.3: EXPO, CTRL and EDEP carry no metric and no sign."""
    assert len(CONSTRUCTS) == 9
    signed = [c for c in CONSTRUCTS if c.index_sign is not None]
    assert len(signed) == 6
    unsigned = {c.code for c in CONSTRUCTS if c.index_sign is None}
    assert unsigned == {"EXPO", "CTRL", "EDEP"}
    assert {c.metric_name for c in signed} == {
        "fairness", "clarity", "happiness", "staying", "pushback", "leaving"
    }
    negative = {c.metric_name for c in signed if c.index_sign == -1}
    assert negative == {"pushback", "leaving"}


def test_fair_is_both_a_block_and_a_construct_and_they_stay_separate():
    """`docs/01` §3.3's namespace warning. The collision is new in 2.0 and must not merge."""
    ref = reference()
    assert "FAIR" in ref.constructs
    assert ref.items["FAIR1"].block == "FAIR"
    assert ref.construct_of("FAIR1").code == "FAIR"
    # An H2 item carries no construct of its own: it is reached through `mirrors`, so a query
    # for FAIR cannot pool Part 7 with Part 16.
    assert ref.construct_of("H2_FAIR1") is None
    assert ref.items["H2_FAIR1"].mirrors == "FAIR1"


def test_attention_checks_have_no_construct():
    ref = reference()
    for item_id in ATTENTION_ITEMS:
        assert ref.construct_of(item_id) is None


def test_a_construct_contradicting_the_instrument_is_rejected(monkeypatch):
    """A gate that cannot fail is not a gate (`docs/11` → Ground rules).

    `CONSTRUCTS` is a normative constant and `instrument.json` is frozen, so nothing makes them
    agree automatically. Flip one sign and the store must refuse to load.
    """
    import twinlab.ingest.reference_store as store

    broken = tuple(
        c.model_copy(update={"index_sign": 1}) if c.code == "EXIT" else c for c in CONSTRUCTS
    )
    monkeypatch.setattr(store, "CONSTRUCTS", broken)
    with pytest.raises(ReferenceCountError, match="contradicts"):
        ReferenceData()


# --------------------------------------------------------------------------- arms


def test_four_arms_one_control_with_the_specified_codes():
    """`docs/01` §5: BASE→00000, MGT1→00010, CON1→01000, REP1→00001."""
    ref = reference()
    assert {a: ref.arms[a].version_code for a in ref.arms} == {
        "BASE": "00000", "MGT1": "00010", "CON1": "01000", "REP1": "00001",
    }
    assert sum(a.is_control for a in ref.arms.values()) == 1
    assert ref.arms["BASE"].is_control


def test_every_non_control_arm_is_a_single_lever_dial_one_code():
    """`docs/01` §5.1's seed assertion.

    It does not re-derive the semantic match; it catches an `arms.json` edited to something
    structurally impossible.
    """
    ref = reference()
    for arm in ref.arms.values():
        if arm.is_control:
            continue
        digits = [int(d) for d in arm.version_code]
        assert sorted(digits) == [0, 0, 0, 0, 1], arm.arm_id
        assert arm.lever is not None
        assert ref.dial_lookup[arm.lever]["1"], f"{arm.arm_id}: no dial-1 gaps"
        position = int(arm.lever[1]) - 1
        assert arm.version_code[position] == "1"


def test_arm_labels_are_the_part_15_options_verbatim():
    """`docs/01` §5.1: the mapping is derived from Part 15, not assumed.

    The builder asserts this too; asserting it here as well means an edited survey source fails
    the suite and not only the build.
    """
    ref = reference()
    options = build_reference.parse_part15_options()
    assert options == [ref.arms[a].label for a, _ in build_reference.ARM_LABELS]
    assert len(options) == 4


def test_each_arm_matches_its_levers_dial_one_commitment_text():
    """`docs/01` §5.1: every non-control arm matches its lever's dial-1 set term for term."""
    ref = reference()
    for arm_id, (lever, terms) in build_reference.ARM_DERIVATION.items():
        if lever is None:
            continue
        haystack = " ".join(
            ref.gaps[g].commitment for g in ref.dial_lookup[lever]["1"]
        ).lower()
        for term in terms:
            assert term.lower() in haystack, f"{arm_id}: {term!r} missing from {lever}"
        assert ref.arms[arm_id].lever == lever


def test_a_structurally_impossible_arm_is_rejected(tmp_path):
    """The arm gate rejects a dial-2 code, proving it can fail."""
    copy = tmp_path / "reference"
    copy.mkdir()
    for name in REFERENCE_FILES:
        (copy / name).write_bytes((REFERENCE_DIR / name).read_bytes())
    arms = json.loads((copy / "arms.json").read_text(encoding="utf-8"))
    for arm in arms:
        if arm["arm_id"] == "CON1":
            arm["version_code"] = "02000"
    (copy / "arms.json").write_text(json.dumps(arms), encoding="utf-8")
    with pytest.raises(ReferenceCountError, match="single-lever dial-1"):
        ReferenceData(copy)


# --------------------------------------------------------------------------- crosswalk


def test_crosswalk_has_twenty_four_renames_and_resolves_every_target():
    """`docs/01` §2 and §4: 24 rows, four of them family patterns."""
    ref = reference()
    assert len(ref.legacy) == 24
    patterns = [r for r in ref.legacy.values() if r.pattern]
    assert len(patterns) == 4
    for row in ref.legacy.values():
        if row.pattern:
            continue
        assert row.item_id in ref.items, row.legacy_id


def test_crosswalk_records_the_renames_that_are_not_identity():
    """`docs/01` §4: PAF→FAIR, PAT→CLAR, LOY→CONT, VOI→ALGO, EXT→TURN, ECD→DEP, AC1, AC2."""
    ref = reference()
    assert ref.legacy["PAF1"].item_id == "FAIR1"
    assert ref.legacy["PAT3"].item_id == "CLAR3"
    assert ref.legacy["LOY2"].item_id == "CONT2"
    assert ref.legacy["VOI4"].item_id == "ALGO4"
    assert ref.legacy["EXT3"].item_id == "TURN3"
    assert ref.legacy["ECD1"].item_id == "DEP1"
    assert ref.legacy["AC1"].item_id == "AMQ6"
    assert ref.legacy["AC2"].item_id == "ALGO5"


def test_crosswalk_flags_the_rescaled_blocks_as_not_poolable():
    """`docs/01` §4: legacy PAC/CLAR/CONT were 1–7 and are 1–5 canonically.

    Silently pooling them would corrupt every reliability statistic, so the warning travels with
    the data rather than living only in prose.
    """
    ref = reference()
    change = ref.legacy_scale_changes[0]
    assert set(change["blocks"]) == {"PAC", "CLAR", "CONT"}
    assert change["legacy_points"] == 7 and change["canonical_points"] == 5
    assert "not be pooled" in change["note"]
    for block in change["blocks"]:
        assert ref.scales[ref.items[f"{block}1"].scale_id].points == 5


def test_crosswalk_maps_the_six_signed_shift_columns():
    """`docs/01` §4: `d_<CONSTRUCT>` → `shift.<metric>`, stored signed."""
    ref = reference()
    fields = {f["legacy_field"]: f["canonical"] for f in ref.legacy_field_mappings}
    assert fields["design"] == "version_code"
    for construct in CONSTRUCTS:
        if construct.index_sign is None:
            continue
        assert fields[f"d_{construct.code}"] == f"shift.{construct.metric_name}"


# --------------------------------------------------------------------------- seeding


async def test_seed_is_idempotent(backend):
    """`docs/11` → M1: running `seed_db.py` twice changes no row count."""
    first = await seed(backend)
    second = await seed(backend)
    assert first == second
    assert first["survey_items"] == 73
    assert first["constructs"] == 9
    assert first["arms"] == 4


async def test_all_post_seed_assertions_pass(backend):
    """`docs/11` → M1: the `docs/01` §9 assertions, on a freshly seeded database."""
    await seed(backend)
    await assert_seeded(backend)


async def test_post_seed_assertions_reject_a_damaged_database(backend):
    """A gate that cannot fail is not a gate. Drop one criterion and the seeder must object."""
    await seed(backend)
    await backend.delete("criteria", [("eq", "criterion_id", "1.1.a")])
    with pytest.raises(SeedError, match="criteria"):
        await assert_seeded(backend)


async def test_post_seed_assertions_reject_a_stale_reference_hash(backend):
    """The startup gate's stored value is checked at seed time too."""
    await seed(backend)
    await backend.update(
        "app_config", {"value": {"hash": "deadbeef"}}, [("eq", "key", REFERENCE_CONFIG_KEY)]
    )
    with pytest.raises(SeedError, match="reference hash"):
        await assert_seeded(backend)


async def test_seeded_items_carry_their_construct_code(backend):
    """`docs/01` §6.1: `survey_items.construct_code`, null for holdouts and attention checks."""
    await seed(backend)
    rows = {r["item_id"]: r for r in await backend.select("survey_items")}
    assert rows["FAIR1"]["construct_code"] == "FAIR"
    assert rows["PAC1"]["construct_code"] == "CTRL"
    assert rows["TURN3"]["construct_code"] == "EXIT"
    assert rows["AMQ6"]["construct_code"] is None
    assert rows["H2_FAIR1"]["construct_code"] is None
    assert rows["H3_V1_FAIR"]["construct_code"] is None
    assert rows["FAIR1"]["part_name"], "part_name is NOT NULL in the 2.0 schema"


async def test_seeded_h3_items_carry_the_six_part_17_codes(backend):
    """`docs/01` §3.6: the six scenarios are real version codes, not free-written vignettes."""
    await seed(backend)
    rows = await backend.select("survey_items", [("eq", "role", "holdout_h3")])
    assert len(rows) == 18
    assert {r["version_code"] for r in rows} == {
        "12220", "00222", "11010", "11211", "02211", "02200"
    }


async def test_every_legacy_identifier_resolves(backend):
    """`docs/01` §4: all 73 prototype identifiers map to a canonical item.

    The file holds 24 rules; the seeder expands the four families and adds the identities, so the
    importer never has to guess.
    """
    await seed(backend)
    rows = await backend.select("legacy_items")
    assert len(rows) == 73
    items = {r["item_id"] for r in await backend.select("survey_items")}
    for row in rows:
        assert row["item_id"] in items, row["legacy_id"]
    by_legacy = {r["legacy_id"]: r["item_id"] for r in rows}
    assert by_legacy["post_PAF1"] == "H2_FAIR1"
    assert by_legacy["post_SAT2"] == "H2_SAT2"
    assert by_legacy["cj1_cj_fair"] == "H3_V1_FAIR"
    assert by_legacy["cj6_cj_resist"] == "H3_V6_PUSH"
    assert by_legacy["cj3_cj_stay"] == "H3_V3_KEEP"
    assert by_legacy["AMQ1"] == "AMQ1", "identity mappings are added by the seeder"


def test_seed_order_is_fk_dependency_order():
    """`docs/01` §9: scales → constructs → survey_items → arms → legacy_items → criteria → …"""
    from twinlab.ingest.seed_db import SEED_ORDER

    def before(a: str, b: str) -> bool:
        return SEED_ORDER.index(a) < SEED_ORDER.index(b)

    assert before("scales", "constructs")
    assert before("constructs", "survey_items")
    assert before("survey_items", "legacy_items")
    assert before("arms", "legacy_items")
    assert before("criteria", "criterion_findings")
    assert before("criteria", "gaps")
    assert before("thresholds", "gaps")
    assert before("corpus_chunks", "chunk_criterion_links")


def test_thresholds_are_ordered_so_gates_insert_last():
    """`thresholds.gate_threshold` self-references, so X.1 must precede X.2."""
    ref = reference()
    rows = build_rows(ref)["thresholds"]
    seen: set[str] = set()
    for row in rows:
        gate = row["gate_threshold"]
        assert gate is None or gate in seen, row["threshold_id"]
        seen.add(row["threshold_id"])
