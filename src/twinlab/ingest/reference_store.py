"""The frozen reference data, loaded once into memory.

`data/reference/*.json` is read-only at runtime (`docs/01` §1). Everything downstream — lookup,
persona, metrics, checker, UI — reads these dicts rather than the DB, so a deterministic function
stays deterministic without a network call.

Counts are asserted on load. A count mismatch is a startup failure, not a warning.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from config.settings import REFERENCE_DIR
from twinlab.models.reference import (
    CONSTRUCTS,
    MET_CRITERIA,
    Arm,
    Chunk,
    ChunkCriterionLink,
    Construct,
    Criterion,
    CriterionFinding,
    Gap,
    Item,
    LegacyItem,
    MetricDef,
    Scale,
    Threshold,
    construct_code_for,
)
from twinlab.models.twin import BatteryItem

EXPECTED_COUNTS: dict[str, int] = {
    "criteria": 33,
    "criterion_findings": 33,
    "gaps": 30,
    "thresholds": 10,
    "corpus_chunks": 126,
    "chunk_criterion_links": 171,
    "items": 73,
    "scales": 5,
    "constructs": 9,
    "arms": 4,
    "legacy_renames": 24,
}

#: The ten reference files, in the order they are hashed. `docs/01` §2.
REFERENCE_FILES: tuple[str, ...] = (
    "criteria.json",
    "criterion_findings.json",
    "gaps.json",
    "thresholds.json",
    "corpus_chunks.json",
    "chunk_criterion_links.json",
    "instrument.json",
    "dial_lookup.json",
    "arms.json",
    "legacy_crosswalk.json",
)


class ReferenceCountError(RuntimeError):
    """Raised when a reference file does not hold the number of rows `docs/01` §2 specifies."""


def _read(name: str, directory: Path | None = None) -> object:
    path = (directory or REFERENCE_DIR) / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, got: int) -> None:
    want = EXPECTED_COUNTS[name]
    if got != want:
        raise ReferenceCountError(f"{name}: expected {want} rows, found {got}")


@lru_cache(maxsize=1)
def reference_hash(directory: Path | None = None) -> str:
    """One digest over all ten reference files.

    Frozen onto a seeded database and re-checked at startup (`docs/11` → M1): an instrument
    pointed at a Supabase project seeded from different reference data refuses to boot rather
    than producing numbers nobody can trace.
    """
    h = hashlib.sha256()
    base = directory or REFERENCE_DIR
    for name in REFERENCE_FILES:
        h.update(name.encode())
        h.update(b"\0")
        h.update((base / name).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


class ReferenceData:
    """All ten frozen files, keyed for lookup. Built once; treat as immutable."""

    def __init__(self, directory: Path | None = None) -> None:
        criteria = [Criterion(**r) for r in _read("criteria", directory)]
        findings = [CriterionFinding(**r) for r in _read("criterion_findings", directory)]
        thresholds = [Threshold(**r) for r in _read("thresholds", directory)]
        gaps = [Gap(**r) for r in _read("gaps", directory)]
        chunks = [Chunk(**r) for r in _read("corpus_chunks", directory)]
        links = [ChunkCriterionLink(**r) for r in _read("chunk_criterion_links", directory)]
        instrument = _read("instrument", directory)
        items = [Item(**r) for r in instrument["items"]]
        scales = [Scale(scale_id=k, **v) for k, v in instrument["scales"].items()]
        metrics = {k: MetricDef(**v) for k, v in instrument["metrics"].items()}
        arms = [Arm(**r) for r in _read("arms", directory)]
        crosswalk = _read("legacy_crosswalk", directory)
        legacy = [LegacyItem(**r) for r in crosswalk["renames"]]

        _check("criteria", len(criteria))
        _check("criterion_findings", len(findings))
        _check("thresholds", len(thresholds))
        _check("gaps", len(gaps))
        _check("corpus_chunks", len(chunks))
        _check("chunk_criterion_links", len(links))
        _check("items", len(items))
        _check("scales", len(scales))
        _check("constructs", len(CONSTRUCTS))
        _check("arms", len(arms))
        _check("legacy_renames", len(legacy))

        met = sorted(f.criterion_id for f in findings if f.finding == "Met")
        if tuple(met) != MET_CRITERIA:
            raise ReferenceCountError(f"Met findings must be {MET_CRITERIA}, found {tuple(met)}")

        self.instrument_version: str = instrument["instrument_version"]
        self.crosswalk_version: str = crosswalk["crosswalk_version"]
        self.criteria: dict[str, Criterion] = {c.criterion_id: c for c in criteria}
        self.findings: dict[str, CriterionFinding] = {f.criterion_id: f for f in findings}
        self.thresholds: dict[str, Threshold] = {t.threshold_id: t for t in thresholds}
        self.gaps: dict[str, Gap] = {g.gap_id: g for g in gaps}
        self.chunks: dict[str, Chunk] = {c.chunk_id: c for c in chunks}
        self.links: list[ChunkCriterionLink] = links
        self.items: dict[str, Item] = {i.item_id: i for i in items}
        self.scales: dict[str, Scale] = {s.scale_id: s for s in scales}
        self.metrics: dict[str, MetricDef] = metrics
        self.constructs: dict[str, Construct] = {c.code: c for c in CONSTRUCTS}
        self.arms: dict[str, Arm] = {a.arm_id: a for a in arms}
        self.legacy: dict[str, LegacyItem] = {row.legacy_id: row for row in legacy}
        self.legacy_field_mappings: list[dict] = crosswalk["field_mappings"]
        self.legacy_scale_changes: list[dict] = crosswalk["scale_changes"]
        self.dial_lookup: dict[str, dict[str, list[str]]] = _read("dial_lookup", directory)

        # Derived indexes, built once.
        self.chunks_by_source: dict[str, list[Chunk]] = {}
        for c in chunks:
            self.chunks_by_source.setdefault(c.source_id, []).append(c)
        self.links_by_criterion: dict[str, list[ChunkCriterionLink]] = {}
        for link in links:
            self.links_by_criterion.setdefault(link.criterion_id, []).append(link)

        self._check_constructs()
        self._check_anchors()
        self._check_arms()

    # --- Consistency checks that span two sources ---

    def _check_constructs(self) -> None:
        """The nine constructs against `instrument.json`'s own metrics block. `docs/01` §3.3.

        `CONSTRUCTS` is a normative constant and `instrument.json` is frozen, so nothing makes
        them agree automatically. This is what stops them drifting: the six signed constructs
        must name the six metrics, with the same scale and the same direction.
        """
        signed = {c.metric_name: c for c in self.constructs.values() if c.index_sign is not None}
        if len(signed) != 6:
            raise ReferenceCountError(f"expected 6 signed constructs, found {len(signed)}")
        if set(signed) != set(self.metrics):
            raise ReferenceCountError(
                f"construct metric names {sorted(signed)} != instrument metrics "
                f"{sorted(self.metrics)}"
            )
        for metric_name, construct in signed.items():
            metric = self.metrics[metric_name]
            if construct.scale_id != metric.scale:
                raise ReferenceCountError(
                    f"{construct.code}: scale {construct.scale_id} != metric {metric.scale}"
                )
            want = 1 if metric.direction == "positive" else -1
            if construct.index_sign != want:
                raise ReferenceCountError(
                    f"{construct.code}: index_sign {construct.index_sign} contradicts "
                    f"{metric_name} direction {metric.direction}"
                )
            block_items = [i.item_id for i in self.block_items(construct.block)]
            if block_items != list(metric.items):
                raise ReferenceCountError(
                    f"{construct.code}: block {construct.block} holds {block_items}, "
                    f"metric {metric_name} names {metric.items}"
                )

    def _check_anchors(self) -> None:
        """Every `anchors` array length equals its `scales.points`. `docs/01` §9.

        This catches the 5-vs-7 scale error at load time rather than in a metric — the defect
        that made the prototype's twin prompt claim "1 to 7" for 5-point blocks.
        """
        for scale in self.scales.values():
            if len(scale.anchors) != scale.points:
                raise ReferenceCountError(
                    f"scale {scale.scale_id}: {len(scale.anchors)} anchors for "
                    f"{scale.points} points"
                )

    def _check_arms(self) -> None:
        """`docs/01` §5.1: every non-control arm is a single-lever dial-1 code."""
        controls = [a for a in self.arms.values() if a.is_control]
        if len(controls) != 1:
            raise ReferenceCountError(f"expected exactly 1 control arm, found {len(controls)}")
        for arm in self.arms.values():
            if arm.is_control:
                if arm.version_code != "00000":
                    raise ReferenceCountError(f"{arm.arm_id}: control arm must be 00000")
                continue
            digits = [int(d) for d in arm.version_code]
            if sorted(digits) != [0, 0, 0, 0, 1]:
                raise ReferenceCountError(
                    f"{arm.arm_id}: {arm.version_code} is not a single-lever dial-1 code"
                )
            if arm.lever is None or not self.dial_lookup[arm.lever]["1"]:
                raise ReferenceCountError(f"{arm.arm_id}: lever {arm.lever} has no dial-1 gaps")

    # --- Convenience accessors used across layers ---

    @property
    def all_gap_ids(self) -> list[str]:
        return sorted(self.gaps)

    @property
    def battery_item_ids(self) -> list[str]:
        """The 37 items put to a twin. Attention checks excluded (I10)."""
        items = [i for i in self.items.values() if i.in_twin_battery]
        return [i.item_id for i in sorted(items, key=lambda i: (i.part, i.ordinal))]

    @property
    def holdout_h3_item_ids(self) -> list[str]:
        items = [i for i in self.items.values() if i.role == "holdout_h3"]
        return [i.item_id for i in sorted(items, key=lambda i: (i.part, i.ordinal))]

    @property
    def holdout_h2_item_ids(self) -> list[str]:
        items = [i for i in self.items.values() if i.role == "holdout_h2"]
        return [i.item_id for i in sorted(items, key=lambda i: (i.part, i.ordinal))]

    @property
    def h3_version_codes(self) -> list[str]:
        """The six codes Part 17 shows, in `version_shown` order. `docs/01` §3.6."""
        seen: dict[int, str] = {}
        for i in self.items.values():
            if i.role == "holdout_h3" and i.version_shown is not None and i.version_code:
                seen[i.version_shown] = i.version_code
        return [seen[k] for k in sorted(seen)]

    def block_items(self, block: str) -> list[Item]:
        """The items of one block, in ordinal order, attention checks excluded.

        ``block`` is the item block, never a construct code — they are different namespaces
        and `FAIR` is both (`docs/01` §3.3).
        """
        items = [
            i for i in self.items.values()
            if i.block == block and not i.attention_check and not i.role.startswith("holdout")
        ]
        return sorted(items, key=lambda i: i.ordinal)

    def construct_of(self, item_id: str) -> Construct | None:
        code = construct_code_for(self.items[item_id])
        return self.constructs[code] if code else None

    def scale_points(self, item_id: str) -> int:
        scale_id = self.items[item_id].scale_id
        if scale_id is None:
            raise KeyError(f"{item_id} has no scale")
        return self.scales[scale_id].points

    def scale_anchors(self, item_id: str) -> tuple[str, ...]:
        """One label per scale point, low to high, as the human read them on the Form.

        Raises on an item with no scale, exactly as :meth:`scale_points` does: an item shown to a
        twin without its anchors is shown on a scale whose direction the twin has to guess, and
        guessing it wrong is not a failure the twin can report (`CLAUDE.md` rule 7).
        `_check_anchors` has already proved the length matches ``points`` at load time.
        """
        scale_id = self.items[item_id].scale_id
        if scale_id is None:
            raise KeyError(f"{item_id} has no scale, so it has no anchors")
        return tuple(self.scales[scale_id].anchors)

    def battery_item(self, item_id: str) -> BatteryItem:
        """The item as a twin is shown it: stem, range and anchors, all from the frozen register.

        The **one** place a `BatteryItem` is built, so no caller can assemble a round that quietly
        omits the anchors. `docs/DECISIONS.md`, 2026-10-12.
        """
        item = self.items[item_id]
        return BatteryItem(
            stem=item.stem,
            points=self.scale_points(item_id),
            anchors=self.scale_anchors(item_id),
        )

    def anchor_chunks(self, gap_ids: list[str]) -> list[Chunk]:
        """Chunks for the anchor sources of these gaps: voice, and what not to re-announce."""
        sources: list[str] = []
        for gid in gap_ids:
            for src in self.gaps[gid].anchor_sources:
                if src not in sources:
                    sources.append(src)
        out: list[Chunk] = []
        for src in sources:
            out.extend(self.chunks_by_source.get(src, []))
        return out


@lru_cache(maxsize=1)
def reference() -> ReferenceData:
    return ReferenceData()
