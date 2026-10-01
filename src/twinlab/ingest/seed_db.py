"""Seed the frozen reference data into Postgres. `docs/01` §9.

Idempotent: upsert on primary key, in FK dependency order. Running it twice changes no row count.
After seeding it asserts every count in `docs/01` §9, the three ``Met`` findings, the attention
and reverse-coded sets, the holdout resolution, the odometer digit-sum identity and the
anchors/points equality; any failure aborts with a non-zero exit.

It also records :func:`reference_hash` into ``app_config``, which is what lets startup refuse to
boot against a project seeded from different reference data.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import yaml

from config.settings import CONFIG_DIR
from twinlab.db.client import DbBackend, get_backend
from twinlab.ingest.reference_store import ReferenceData, reference, reference_hash
from twinlab.models.reference import (
    ATTENTION_ITEMS,
    MET_CRITERIA,
    REVERSE_CODED_ITEMS,
    construct_code_for,
)

#: FK dependency order. `docs/01` §9.
SEED_ORDER = [
    "scales",
    "constructs",
    "survey_items",
    "arms",
    "legacy_items",
    "criteria",
    "thresholds",
    "criterion_findings",
    "gaps",
    "corpus_chunks",
    "chunk_criterion_links",
    "agent_configs",
    "app_config",
]

PRIMARY_KEY = {
    "scales": "scale_id",
    "constructs": "code",
    "survey_items": "item_id",
    "arms": "arm_id",
    "legacy_items": "legacy_id",
    "criteria": "criterion_id",
    "thresholds": "threshold_id",
    "criterion_findings": "criterion_id",
    "gaps": "gap_id",
    "corpus_chunks": "chunk_id",
    "chunk_criterion_links": "link_id",
    "agent_configs": "agent_id",
    "app_config": "key",
}

EXPECTED_ROWS = {
    "criteria": 33,
    "criterion_findings": 33,
    "gaps": 30,
    "thresholds": 10,
    "corpus_chunks": 126,
    "chunk_criterion_links": 171,
    "survey_items": 73,
    "scales": 5,
    "constructs": 9,
    "arms": 4,
}

#: `app_config` key holding the reference digest. Checked at startup.
REFERENCE_CONFIG_KEY = "reference"


class SeedError(RuntimeError):
    """A post-seed assertion failed. The database is not fit to run a study against."""


def _thresholds_rows(ref: ReferenceData) -> list[dict]:
    """``thresholds`` self-references via ``gate_threshold``; insert gates last."""
    rows = [t.model_dump() for t in ref.thresholds.values()]
    rows.sort(key=lambda r: (r["gate_threshold"] is not None, r["threshold_id"]))
    return rows


def _gap_rows(ref: ReferenceData) -> list[dict]:
    """`gaps`, projected onto the DDL's columns. `docs/01` §6.

    `gaps.json` carries both `gap_id` and `criterion_id`, and every one of the 30 rows has them
    equal — a gap *is* a criterion Uber does not meet. The DDL says so structurally instead, with
    ``gap_id text primary key references criteria(criterion_id)``, so there is no `criterion_id`
    column to write and a `model_dump()` fails against a real Postgres with PGRST204.

    The identity is asserted rather than assumed. Dropping a column whose value might differ would
    be a silent loss; dropping one proved redundant is a projection.
    """
    rows = []
    for gap in ref.gaps.values():
        if gap.criterion_id != gap.gap_id:
            raise SeedError(
                f"{gap.gap_id}: gaps.json gives criterion_id {gap.criterion_id!r}, which differs "
                "from gap_id. The schema stores the relation as the primary key's own foreign "
                "key, so a differing criterion_id has nowhere to go and must not be dropped."
            )
        row = gap.model_dump()
        row.pop("criterion_id")
        rows.append(row)
    return rows


def _item_rows(ref: ReferenceData) -> list[dict]:
    """The 73 items, with ``construct_code`` derived from the block. `docs/01` §3.3."""
    rows = []
    for item in ref.items.values():
        row = item.model_dump()
        row["construct_code"] = construct_code_for(item)
        rows.append(row)
    return rows


def legacy_rows(ref: ReferenceData) -> list[dict]:
    """`legacy_items`: one row per prototype identifier. `docs/01` §4.

    The crosswalk file records *rules* — explicit renames plus four holdout families — because a
    hand-expanded list is exactly what it exists to prevent. This expands them, and adds the
    identity mappings the file omits, so every one of the 73 legacy identifiers resolves.
    """
    explicit = {r.legacy_id: r for r in ref.legacy.values() if not r.pattern}
    canonical_to_legacy = {r.item_id: r.legacy_id for r in explicit.values() if r.item_id}

    rows = [
        {"legacy_id": r.legacy_id, "item_id": r.item_id, "note": r.note}
        for r in explicit.values()
    ]

    # Identity mappings: a battery item the prototype named the same way.
    for item in ref.items.values():
        if item.role.startswith("holdout") or item.item_id in canonical_to_legacy:
            continue
        if item.item_id not in explicit:
            rows.append({"legacy_id": item.item_id, "item_id": item.item_id, "note": None})
            canonical_to_legacy.setdefault(item.item_id, item.item_id)

    # Family expansion. `post_<legacy id of the mirrored item>` → the H2 item.
    for item_id in ref.holdout_h2_item_ids:
        mirrors = ref.items[item_id].mirrors
        if mirrors is None:
            raise SeedError(f"{item_id} is an H2 item with no `mirrors`")
        legacy_source = canonical_to_legacy.get(mirrors)
        if legacy_source is None:
            raise SeedError(f"{item_id}: no legacy id for its source item {mirrors}")
        rows.append({
            "legacy_id": f"post_{legacy_source}", "item_id": item_id,
            "note": "Part 16 holdout, by the prototype's `post_` prefix.",
        })

    suffix_to_legacy = {"FAIR": "cj_fair", "PUSH": "cj_resist", "KEEP": "cj_stay"}
    for item_id in ref.holdout_h3_item_ids:
        item = ref.items[item_id]
        suffix = item_id.rsplit("_", 1)[1]
        rows.append({
            "legacy_id": f"cj{item.version_shown}_{suffix_to_legacy[suffix]}",
            "item_id": item_id,
            "note": f"Part 17 holdout, version {item.version_shown} = {item.version_code}.",
        })

    if len({r["legacy_id"] for r in rows}) != len(rows):
        raise SeedError("legacy_items: duplicate legacy_id after expansion")
    return rows


def _optional_yaml(name: str) -> dict | None:
    """A config YAML if it exists yet.

    `agents.default.yaml`, `twin.default.yaml`, `analysis.default.yaml` and
    `generator.default.yaml` belong to M2, M5, M8 and M9 (`docs/DECISIONS.md`). M1 seeds the
    reference tables and must run before they exist, so a missing file is skipped and reported
    rather than raising — `agent_configs` and `app_config` are configuration, not the frozen
    reference data this milestone is about.
    """
    path = CONFIG_DIR / name
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_rows(ref: ReferenceData) -> dict[str, list[dict]]:
    """Every seeded table as plain rows, keyed by table name."""
    twin_yaml = _optional_yaml("twin.default.yaml")
    style_yaml = _optional_yaml("style_contract.yaml")
    analysis_yaml = _optional_yaml("analysis.default.yaml")

    # Seeded from the validated configs rather than the raw YAML, so `prompt_hash` is the hash of
    # the prompt the agent would actually be given (I11) and every config gate — no `native`
    # output, no tools on design or twin — has already run (M2, `agents/registry.py`).
    agent_rows = []
    if (CONFIG_DIR / "agents.default.yaml").exists():
        from twinlab.agents.registry import default_agent_configs

        agent_rows = [cfg.model_dump() for cfg in default_agent_configs().values()]

    app_config = [
        # M1's startup gate: an instrument pointed at a project seeded from different reference
        # data refuses to boot rather than producing numbers nobody can trace.
        {
            "key": REFERENCE_CONFIG_KEY,
            "value": {
                "hash": reference_hash(),
                "instrument_version": ref.instrument_version,
                "crosswalk_version": ref.crosswalk_version,
            },
            "version": 1,
        }
    ]
    if style_yaml is not None:
        app_config.append({"key": "style", "value": style_yaml, "version": 1})
    # M8. The index weights must be in `app_config` because every analysis run records the weights
    # it used: docs/07 §4.1's "any non-default set is recorded on the run" is unenforceable if the
    # defaults live only in a file on disk.
    if analysis_yaml is not None:
        app_config.append({"key": "analysis", "value": analysis_yaml, "version": 1})
    if twin_yaml is not None:
        app_config.append({"key": "twin", "value": twin_yaml, "version": 1})
        app_config.append({
            "key": "orchestrator",
            "value": {
                "max_active_sessions": 1,
                "max_concurrency": twin_yaml["max_concurrency"],
                "rate_limit_attempts": 3,
                "backoff": "exponential",
            },
            "version": 1,
        })

    return {
        "scales": [s.model_dump() for s in ref.scales.values()],
        "constructs": [c.model_dump() for c in ref.constructs.values()],
        "survey_items": _item_rows(ref),
        "arms": [a.model_dump() for a in ref.arms.values()],
        "legacy_items": legacy_rows(ref),
        "criteria": [c.model_dump() for c in ref.criteria.values()],
        "thresholds": _thresholds_rows(ref),
        "criterion_findings": [f.model_dump() for f in ref.findings.values()],
        "gaps": _gap_rows(ref),
        "corpus_chunks": [c.model_dump() for c in ref.chunks.values()],
        "chunk_criterion_links": [link.model_dump() for link in ref.links],
        "agent_configs": agent_rows,
        "app_config": app_config,
    }


async def seed(
    backend: DbBackend | None = None, ref: ReferenceData | None = None
) -> dict[str, int]:
    """Upsert every reference table. Returns the row count per table after seeding."""
    backend = backend or get_backend()
    ref = ref or reference()
    rows = build_rows(ref)

    counts: dict[str, int] = {}
    for table in SEED_ORDER:
        if not rows[table]:
            continue
        await backend.upsert(table, rows[table], on_conflict=PRIMARY_KEY[table])
        counts[table] = await backend.count(table)
    return counts


async def assert_seeded(backend: DbBackend | None = None) -> None:
    """The `docs/01` §9 assertions. Raises :class:`SeedError` on the first failure."""
    from twinlab.orchestrator.odometer import all_codes, digit_sum, validate_code

    backend = backend or get_backend()
    ref = reference()

    # 1-8, 12-14: row counts.
    for table, want in EXPECTED_ROWS.items():
        got = await backend.count(table)
        if got != want:
            raise SeedError(f"{table}: expected {want} rows, found {got}")

    # 3: the three Met findings, which are the SHAM commitment set.
    met = await backend.select("criterion_findings", [("eq", "finding", "Met")])
    met_ids = tuple(sorted(r["criterion_id"] for r in met))
    if met_ids != MET_CRITERIA:
        raise SeedError(f"Met findings must be {MET_CRITERIA}, found {met_ids}")

    items = await backend.select("survey_items")

    # 9: the twin battery is 37, not 39 (I10).
    battery = [r for r in items if r.get("in_twin_battery")]
    if len(battery) != 37:
        raise SeedError(f"twin battery: expected 37 items, found {len(battery)}")

    # 10: the two attention checks, never put to a twin (I10).
    attention = tuple(sorted(r["item_id"] for r in items if r.get("attention_check")))
    if attention != ATTENTION_ITEMS:
        raise SeedError(f"attention checks must be {ATTENTION_ITEMS}, found {attention}")
    if any(r.get("in_twin_battery") for r in items if r.get("attention_check")):
        raise SeedError("an attention check is flagged in_twin_battery (I10)")

    # 11: the three reverse-coded items.
    reversed_ids = tuple(sorted(r["item_id"] for r in items if r.get("reverse_coded")))
    if reversed_ids != REVERSE_CODED_ITEMS:
        raise SeedError(f"reverse-coded must be {REVERSE_CODED_ITEMS}, found {reversed_ids}")

    # 13: nine constructs, six of which carry an index sign.
    constructs = await backend.select("constructs")
    signed = [c for c in constructs if c.get("index_sign") is not None]
    if len(signed) != 6:
        raise SeedError(f"expected 6 signed constructs, found {len(signed)}")

    # 14: four arms, one of which is the control.
    arms = await backend.select("arms")
    controls = [a for a in arms if a.get("is_control")]
    if len(controls) != 1:
        raise SeedError(f"expected exactly 1 control arm, found {len(controls)}")

    # 15: every H2 item resolves `mirrors`.
    by_id = {r["item_id"]: r for r in items}
    h2 = [r for r in items if r.get("role") == "holdout_h2"]
    if len(h2) != 16:
        raise SeedError(f"expected 16 H2 items, found {len(h2)}")
    for row in h2:
        if row.get("mirrors") not in by_id:
            raise SeedError(f"{row['item_id']}: mirrors {row.get('mirrors')!r} does not resolve")

    # 16: every H3 item carries a valid version code, and they are the six Part 17 codes.
    h3 = [r for r in items if r.get("role") == "holdout_h3"]
    if len(h3) != 18:
        raise SeedError(f"expected 18 H3 items, found {len(h3)}")
    for row in h3:
        code = row.get("version_code")
        try:
            validate_code(code or "")
        except ValueError as exc:
            raise SeedError(f"{row['item_id']}: {exc}") from exc
        if code not in ref.h3_version_codes:
            raise SeedError(f"{row['item_id']}: {code} is not one of the six Part 17 codes")

    # 17: the odometer identity. 243 codes, digit sums 0-10, summing to 1215.
    total = sum(digit_sum(code) for code in all_codes())
    if total != 1215:
        raise SeedError(f"digit-sum identity broken: {total} != 1215")

    # 18: every `anchors` array length equals its `scales.points`. This catches the 5-vs-7 scale
    # error at seed time rather than in a metric.
    for scale in await backend.select("scales"):
        if len(scale["anchors"]) != scale["points"]:
            raise SeedError(
                f"scale {scale['scale_id']}: {len(scale['anchors'])} anchors for "
                f"{scale['points']} points"
            )

    # The startup gate's stored value must be present and current.
    stored = await backend.select("app_config", [("eq", "key", REFERENCE_CONFIG_KEY)])
    if not stored:
        raise SeedError(f"app_config has no {REFERENCE_CONFIG_KEY!r} row; startup cannot verify")
    if stored[0]["value"].get("hash") != reference_hash():
        raise SeedError("stored reference hash does not match data/reference/")


async def main_async(check_only: bool) -> int:
    backend = get_backend()
    if not check_only:
        counts = await seed(backend)
        for table, n in counts.items():
            print(f"seeded {table:<24} {n:>4} rows")
        for table in SEED_ORDER:
            if table not in counts:
                print(f"skipped {table:<23} (its config YAML belongs to a later milestone)")
    await assert_seeded(backend)
    print("all post-seed assertions passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed reference data into Postgres.")
    parser.add_argument("--check", action="store_true", help="assert only; do not write")
    args = parser.parse_args()
    try:
        return asyncio.run(main_async(args.check))
    except SeedError as exc:
        print(f"SEED FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
