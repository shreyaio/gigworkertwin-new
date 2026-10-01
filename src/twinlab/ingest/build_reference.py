"""Regenerate data/reference/*.json from the source documents.

Byte-stable: same sources in, same bytes out. Every count is asserted — a mismatch is a
build failure, not a warning (CLAUDE.md rule 7).

    python src/twinlab/ingest/build_reference.py [--check]

--check regenerates into memory and diffs against the committed files, exiting non-zero on
any difference. That is the M1 acceptance test.

Ten files. The **eight** built from the source documents are frozen and are never regenerated
in anger: `--check` must exit 0 at all times. `arms.json` and `legacy_crosswalk.json` are new in
2.0 (`docs/01` §5 and §4) and are derived here rather than hand-written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import docx
import docx.oxml.ns as ns
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "reference"

#: Where the source documents may live. `additional_data/` is where they are kept; the repo root
#: is accepted too, so an older checkout still builds. First match wins, and a missing source
#: raises with every place that was searched rather than failing on one hard-coded path.
SOURCE_DIRS = (ROOT / "additional_data", ROOT)


def source(name: str) -> Path:
    for directory in SOURCE_DIRS:
        candidate = directory / name
        if candidate.exists():
            return candidate
    searched = ", ".join(str(d) for d in SOURCE_DIRS)
    raise FileNotFoundError(f"source document {name!r} not found. Searched: {searched}")


SRC_FAIRWORK = source("Fairwork_LocationBased_Principles_verbatim.md")
SRC_CODEBOOK = source("Fairwork_Uber_India_Codebook_v2.docx")
SRC_CORPUS = source("Uber_India_Policy_Corpus_Fairwork_Levers.md")
SRC_SURVEY = source("Survey_Research_GIGWORKER_v2.md")

EXPECTED = {
    "criteria": 33, "criterion_findings": 33, "gaps": 30, "thresholds": 10,
    "corpus_chunks": 126, "chunk_criterion_links": 171,
}
SATISFACTION_RULE = {"1.1": "BOTH", "1.2": "ONE", "2.1": "ALL", "2.2": "ALL", "3.1": "ALL",
                     "3.2": "ALL", "4.1": "ALL", "4.2": "ALL", "5.1": "ALL", "5.2": "ANY"}


# --------------------------------------------------------------------------- docx
def docx_lines(path: Path) -> list[str]:
    """Flatten a .docx to lines; table rows become ' | '-joined lines."""
    d = docx.Document(str(path))
    lines: list[str] = []
    for child in d.element.body.iterchildren():
        if child.tag == ns.qn("w:p"):
            p = Paragraph(child, d)
            if not p.text.strip():
                continue
            try:
                style = p.style.name or ""
            except Exception:
                style = ""
            lines.append(("### " if style.startswith("Heading") else "") + p.text.strip())
        elif child.tag == ns.qn("w:tbl"):
            for row in Table(child, d).rows:
                lines.append(" | ".join(c.text.strip().replace("\n", " ") for c in row.cells))
            lines.append("")
    return lines


def section(lines: list[str], start: str, end: str) -> list[str]:
    s = next(i for i, line in enumerate(lines) if line.startswith(start))
    e = next(i for i, line in enumerate(lines) if line.startswith(end))
    return lines[s:e]


# --------------------------------------------------------------------------- parsers
def parse_criteria() -> list[dict]:
    fw = SRC_FAIRWORK.read_text(encoding="utf-8")
    out = []
    pat = (r"## Threshold (\d\.\d) — (.+?) \((one point|one additional point)\)\n"
           r"(.*?)(?=\n## |\n---|\Z)")
    for m in re.finditer(pat, fw, re.S):
        tid, tname, point, body = m.groups()
        for cm in re.finditer(r"- \*\*\[(\d\.\d\.[a-f])\]\*\* (.+)", body):
            out.append({
                "criterion_id": cm.group(1), "principle": int(tid[0]), "threshold_id": tid,
                "threshold_name": tname, "threshold_point": point,
                "satisfaction_rule": SATISFACTION_RULE[tid],
                "criterion_text": cm.group(2).strip(),
            })
    return out


def parse_codebook() -> tuple[list[dict], list[dict], list[dict]]:
    lines = docx_lines(SRC_CODEBOOK)
    crit_re = re.compile(r"\d\.\d\.[a-f]")

    findings = []
    for line in section(lines, "### 9.  Table C", "### 10.  Table D"):
        p = [x.strip() for x in line.split(" | ")]
        if len(p) == 3 and crit_re.fullmatch(p[0]):
            findings.append({"criterion_id": p[0], "finding": p[1], "reason": p[2]})

    thresholds = []
    for line in section(lines, "### Threshold outcomes", "### 10.  Table D"):
        p = [x.strip() for x in line.split(" | ")]
        if len(p) == 4 and re.fullmatch(r"\d\.\d", p[0]):
            thresholds.append({
                "threshold_id": p[0], "threshold_name": p[1], "lever": "L" + p[0][0],
                "awarded_2026": 0 if p[2] == "No" else 1, "reason": p[3],
                "gate_threshold": None if p[0].endswith("1") else p[0][0] + ".1",
            })

    gaps = []
    for line in section(lines, "### 10.  Table D", "### 11.  Appendix"):
        p = [x.strip() for x in line.split(" | ")]
        if len(p) == 5 and crit_re.fullmatch(p[0]):
            gaps.append({
                "gap_id": p[0], "criterion_id": p[0], "threshold_id": p[0][:3],
                "lever": "L" + p[0][0], "gap_type": p[1], "commitment": p[2],
                "precedent": p[3], "anchor_text": p[4],
                "anchor_sources": sorted(set(re.findall(r"S\d{2}", p[4]))),
            })

    # Cross-check against Table B, which the corpus re-file was derived from. 161 evidence rows
    # expand to 171 chunk x criterion pairs; both numbers are correct (`docs/01` §2).
    rows_b = sum(
        1 for line in section(lines, "### 8.  Table B", "### 9.  Table C")
        if len(line.split(" | ")) >= 5 and crit_re.fullmatch(line.split(" | ")[0].strip())
    )
    assert rows_b == 161, f"Table B rows: expected 161, got {rows_b}"
    return findings, gaps, thresholds


def chunk_field(block: str, name: str) -> str | None:
    """One `- **name**: value` line out of a chunk's front matter."""
    fm = re.search(rf"- \*\*{name}\*\*: (.*)", block)
    return fm.group(1).strip() if fm else None


def parse_corpus() -> tuple[list[dict], list[dict]]:
    text = SRC_CORPUS.read_text(encoding="utf-8")
    chunks, links = [], []
    pat = (r"##### (.+?)\n\n(- \*\*chunk_id\*\*: `(L\d-\d\.\d-\d{3})`.*?)"
           r"\n\nVerbatim text:\n\n(.*?)\n\n(\*Citation:[^\n]*\*)")
    for m in re.finditer(pat, text, re.S):
        heading, block, cid, verbatim, citation = m.groups()
        surfaces = [
            s.strip(" `")
            for s in (chunk_field(block, "policy_surfaces") or "").split(",")
            if s.strip()
        ]
        chunks.append({
            "chunk_id": cid, "source_id": chunk_field(block, "source_id"),
            "source_type": (chunk_field(block, "source_type") or "").strip("`"),
            "jurisdiction": chunk_field(block, "jurisdiction"),
            "audience": (chunk_field(block, "audience") or "").strip("`"),
            "lever": chunk_field(block, "levers"),
            "threshold_id": chunk_field(block, "threshold"),
            "refiled_from": chunk_field(block, "refiled_from"), "policy_surfaces": surfaces,
            "section": chunk_field(block, "section"), "heading": heading.strip(),
            "verbatim_text": "\n".join(
                line[2:] if line.startswith("> ") else line.lstrip(">").strip()
                for line in verbatim.split("\n")
            ).strip(),
            "citation": citation.strip("*"),
        })
        criteria_field = chunk_field(block, "criteria") or ""
        for crit, judgement in re.findall(r"`(\d\.\d\.[a-f])` \((\w[\w ]*)\)", criteria_field):
            links.append({"link_id": f"{cid}__{crit}", "chunk_id": cid,
                          "criterion_id": crit, "judgement": judgement})
    return chunks, links


# --------------------------------------------------------------------------- instrument
BLOCKS = {
    5: ("AMQ", "agree7", "trait"), 6: ("PAC", "agree5", "trait"),
    7: ("FAIR", "extent7", "outcome"), 8: ("CLAR", "agree5", "outcome"),
    9: ("SAT", "agree7", "outcome"), 10: ("CONT", "agree5", "outcome"),
    11: ("ALGO", "agree7", "outcome"), 12: ("TURN", "agree7", "outcome"),
    13: ("DEP", "agree7", "trait"),
}
SCALE_OVERRIDE = {"TURN3": "likely7"}
REVERSE = {"SAT2", "DEP1"}
ATTENTION = {"AMQ6", "ALGO5"}
H2_BLOCKS = [("FAIR", 4), ("SAT", 3), ("ALGO", 4), ("TURN", 3), ("CONT", 2)]
H3_CODES = ["12220", "00222", "11010", "11211", "02211", "02200"]
H3_STEMS = {
    "FAIR": "Under this version, how fair would the app's decisions be for you?",
    "PUSH": ("Under this version, how likely would you be to push back against or work around "
             "the app?"),
    "KEEP": "Under this version, how likely would you be to keep driving with Uber?",
}
SCALES = {
    "agree7": {"points": 7, "format": "agreement", "anchors": [
        "Strongly disagree", "Disagree", "Somewhat disagree", "Neither agree nor disagree",
        "Somewhat agree", "Agree", "Strongly agree"]},
    "agree5": {"points": 5, "format": "agreement", "anchors": [
        "Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree",
        "Strongly agree"]},
    "extent7": {"points": 7, "format": "extent", "anchors": [
        "To a very small extent", "To a small extent", "To a somewhat small extent",
        "To a moderate extent", "To a somewhat large extent", "To a large extent",
        "To a very large extent"]},
    "likely7": {"points": 7, "format": "likelihood", "anchors": [
        "Not at all likely", "Slightly likely", "Somewhat likely", "Moderately likely",
        "Quite likely", "Very likely", "Extremely likely"]},
    "fair7": {"points": 7, "format": "fairness", "anchors": [
        "Very unfair", "Unfair", "Somewhat unfair", "Neither fair nor unfair",
        "Somewhat fair", "Fair", "Very fair"]},
}
METRICS = {
    "fairness": {"items": ["FAIR1", "FAIR2", "FAIR3", "FAIR4"], "scale": "extent7",
                 "direction": "positive"},
    "clarity": {"items": ["CLAR1", "CLAR2", "CLAR3"], "scale": "agree5",
                "direction": "positive"},
    "happiness": {"items": ["SAT1", "SAT2", "SAT3"], "scale": "agree7",
                  "direction": "positive"},
    "staying": {"items": ["CONT1", "CONT2"], "scale": "agree5", "direction": "positive"},
    "pushback": {"items": ["ALGO1", "ALGO2", "ALGO3", "ALGO4"], "scale": "agree7",
                 "direction": "negative"},
    "leaving": {"items": ["TURN1", "TURN2", "TURN3"], "scale": "agree7",
                "direction": "negative"},
}


def parse_instrument() -> dict:
    src = SRC_SURVEY.read_text(encoding="utf-8")
    items: list[dict] = []
    for sec in re.split(r"\n## (?=PART \d)", src):
        m = re.match(r"PART (\d+) — ([^\n]+)", sec)
        if not m or int(m.group(1)) not in BLOCKS:
            continue
        part, part_name = int(m.group(1)), m.group(2).strip()
        block, scale, role = BLOCKS[part]
        for n, im in enumerate(re.finditer(r"^(\d+)\. (.*?) — ((?:\d ?)+)$", sec, re.M), start=1):
            iid = f"{block}{n}"
            items.append({
                "item_id": iid, "part": part, "part_name": part_name, "block": block,
                "ordinal": n, "stem": im.group(2).strip(),
                "scale_id": SCALE_OVERRIDE.get(iid, scale),
                "reverse_coded": iid in REVERSE, "attention_check": iid in ATTENTION,
                "role": "attention" if iid in ATTENTION else role,
                "in_twin_battery": iid not in ATTENTION,
            })

    by_id = {i["item_id"]: i for i in items}
    for block, count in H2_BLOCKS:
        for n in range(1, count + 1):
            base = by_id[f"{block}{n}"]
            items.append({**base, "item_id": f"H2_{block}{n}", "part": 16,
                          "part_name": "IMAGINING THE STORY IS TRUE", "block": "H2",
                          "ordinal": len([i for i in items if i["block"] == "H2"]) + 1,
                          "role": "holdout_h2", "in_twin_battery": False,
                          "mirrors": f"{block}{n}"})

    for v, code in enumerate(H3_CODES, start=1):
        for k, suffix in enumerate(["FAIR", "PUSH", "KEEP"]):
            items.append({
                "item_id": f"H3_V{v}_{suffix}", "part": 17, "part_name": "SIX VERSIONS",
                "block": "H3", "ordinal": (v - 1) * 3 + k + 1, "stem": H3_STEMS[suffix],
                "scale_id": "fair7" if suffix == "FAIR" else "likely7",
                "reverse_coded": False, "attention_check": False,
                "role": "holdout_h3", "in_twin_battery": False,
                "version_shown": v, "version_code": code,
            })

    battery = [i for i in items if i["in_twin_battery"]]
    assert len(battery) == 37, f"twin battery: expected 37, got {len(battery)}"
    assert len([i for i in items if i["role"] == "holdout_h2"]) == 16
    assert len([i for i in items if i["role"] == "holdout_h3"]) == 18
    for metric, spec in METRICS.items():
        missing = [i for i in spec["items"] if i not in by_id]
        assert not missing, f"metric {metric}: unknown items {missing}"
    return {"instrument_version": "2.1", "scales": SCALES, "metrics": METRICS, "items": items}


# --------------------------------------------------------------------------- arms (2.0)
#: `arm_id → (lever or None, the terms that prove the match)`. `docs/01` §5.1.
#:
#: The arm → lever assignment is stated normatively in `docs/01` §5 and was recovered by matching
#: Part 15's manipulation-check options against the dial-1 commitment texts in `gaps.json`
#: (`docs/DECISIONS.md` → "Resolved 2026-09-28 (second pass)"). It is transcribed here rather
#: than re-derived by a scorer — a fuzzy matcher in a frozen builder would add a tie-break
#: failure mode with no research meaning. What the builder *does* do is verify it three ways:
#: the label must appear verbatim among the Part 15 options, the code must be a single-lever
#: dial-1 code, and every term below must appear in that lever's dial-1 commitment text. Any
#: of the three drifting is a build failure.
ARM_DERIVATION: dict[str, tuple[str | None, tuple[str, ...]]] = {
    "BASE": (None, ()),
    "MGT1": ("L4", ("human point of contact", "Extend appeals")),
    "CON1": ("L2", ("safety equipment", "refresher training", "accident and injury cover")),
    "REP1": ("L5", ("voice mechanism", "recognise and bargain")),
}

#: Part 15's four manipulation-check options, in the order the Form presents them, paired with
#: the arm each one denotes. Parsed out of the survey source and compared against this.
ARM_LABELS: tuple[tuple[str, str], ...] = (
    ("BASE", "No change"),
    ("MGT1", "Human appeals with no penalty for complaints"),
    ("CON1", "Safety equipment, training, and accident cover"),
    ("REP1", "A drivers' forum and union recognition"),
)


def parse_part15_options() -> list[str]:
    """The four manipulation-check options, verbatim, in source order."""
    src = SRC_SURVEY.read_text(encoding="utf-8")
    part15 = re.search(
        r"\n## PART 15 — .*?Which change did the story describe\?[^\n]*\n(.*?)\n---", src, re.S
    )
    if part15 is None:
        raise AssertionError("Part 15's manipulation check was not found in the survey source")
    return [m.group(1).strip() for m in re.finditer(r"^- (.+)$", part15.group(1), re.M)]


def build_arms(gaps: list[dict], lookup: dict[str, dict[str, list[str]]]) -> list[dict]:
    """The four human arms, derived and then verified against both sources. `docs/01` §5."""
    options = parse_part15_options()
    expected = [label for _, label in ARM_LABELS]
    assert options == expected, f"Part 15 options drifted:\n  source={options}\n  spec={expected}"

    commitments = {
        lever: " ".join(g["commitment"] for g in gaps if g["gap_id"] in lookup[lever]["1"])
        for lever in lookup
    }

    arms = []
    for arm_id, label in ARM_LABELS:
        lever, terms = ARM_DERIVATION[arm_id]
        if lever is None:
            code = "00000"
        else:
            position = int(lever[1]) - 1
            code = "".join("1" if i == position else "0" for i in range(5))
            # `docs/01` §5.1's seed assertion, made at build time as well: a single-lever
            # dial-1 code over a non-empty dial-1 gap set.
            assert sum(int(d) for d in code) == 1 and code[position] == "1", code
            assert lookup[lever]["1"], f"{arm_id}: {lever} has no dial-1 gaps"
            haystack = commitments[lever].lower()
            missing = [t for t in terms if t.lower() not in haystack]
            assert not missing, f"{arm_id} → {lever}: commitment text lost {missing}"
        arms.append({
            "arm_id": arm_id, "label": label, "version_code": code, "lever": lever,
            "is_control": lever is None,
        })
    assert len(arms) == 4 and sum(a["is_control"] for a in arms) == 1
    return arms


# --------------------------------------------------------------------------- crosswalk (2.0)
#: `(legacy prefix, canonical prefix, n, note)`. `docs/01` §4.
#:
#: Identity mappings (`AMQ`, `PAC`, `SAT`) are not listed: a crosswalk row exists to record a
#: *change*, and the seeder adds the identities when it populates `legacy_items`.
LEGACY_RENAMES: tuple[tuple[str, str, int, str | None], ...] = (
    ("PAF", "FAIR", 4, None),
    ("PAT", "CLAR", 3, "collected 1-7 in the prototype; canonically 1-5. Not poolable."),
    ("LOY", "CONT", 2, "collected 1-7 in the prototype; canonically 1-5. Not poolable."),
    ("VOI", "ALGO", 4, None),
    ("EXT", "TURN", 3, None),
    ("ECD", "DEP", 2, None),
)

#: The two attention checks, which the prototype numbered separately.
LEGACY_ATTENTION: tuple[tuple[str, str], ...] = (("AC1", "AMQ6"), ("AC2", "ALGO5"))

#: The four holdout families, kept as pattern rules rather than expanded. `docs/01` §4.
LEGACY_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("post_{legacy_id}", "H2_{item_id}", "Part 16, all 16 items. H2_SAT2 inherits reverse_coded."),
    ("cj{v}_cj_fair", "H3_V{v}_FAIR", "Part 17, v = 1..6."),
    ("cj{v}_cj_resist", "H3_V{v}_PUSH", "Part 17, v = 1..6."),
    ("cj{v}_cj_stay", "H3_V{v}_KEEP", "Part 17, v = 1..6."),
)

#: Blocks the prototype collected on 1-7 that are 1-5 canonically. `docs/01` §4.
LEGACY_RESCALED_BLOCKS: tuple[str, ...] = ("PAC", "CLAR", "CONT")


def build_crosswalk(instrument: dict) -> dict:
    """`legacy_crosswalk.json`. Read-only, used by the legacy importer and nothing else."""
    by_id = {i["item_id"]: i for i in instrument["items"]}
    renames: list[dict] = []

    for legacy_prefix, canonical_prefix, n, note in LEGACY_RENAMES:
        for i in range(1, n + 1):
            item_id = f"{canonical_prefix}{i}"
            assert item_id in by_id, f"crosswalk target {item_id} is not in the register"
            renames.append({
                "legacy_id": f"{legacy_prefix}{i}", "item_id": item_id, "note": note,
                "pattern": False,
            })
    for legacy_id, item_id in LEGACY_ATTENTION:
        assert by_id[item_id]["attention_check"], f"{item_id} is not an attention check"
        renames.append({
            "legacy_id": legacy_id, "item_id": item_id,
            "note": "attention check; never put to a twin (I10).", "pattern": False,
        })
    for legacy_id, item_id, note in LEGACY_PATTERNS:
        renames.append({
            "legacy_id": legacy_id, "item_id": item_id, "note": note, "pattern": True,
        })

    # `d_<CONSTRUCT>` → `shift.<metric>`, derived from the register's own metrics block so the
    # six signed constructs cannot drift out of the crosswalk. Stored SIGNED; the index applies
    # the sign flip (`docs/01` §4).
    construct_by_metric = {
        "fairness": "FAIR", "clarity": "TRAN", "happiness": "SATI",
        "staying": "LOYA", "pushback": "VOIC", "leaving": "EXIT",
    }
    shift_fields = [
        {
            "legacy_field": f"d_{construct_by_metric[metric]}",
            "canonical": f"shift.{metric}",
            "note": (f"stored signed; direction is {spec['direction']} and the index, not the "
                     f"column, applies the flip"),
        }
        for metric, spec in instrument["metrics"].items()
    ]

    crosswalk = {
        "crosswalk_version": "2.0",
        "renames": renames,
        "field_mappings": [
            {"legacy_field": "design", "canonical": "version_code",
             "note": "the prototype called a version code a \"design\"."},
            *shift_fields,
        ],
        "scale_changes": [
            {
                "blocks": list(LEGACY_RESCALED_BLOCKS),
                "legacy_points": 7,
                "canonical_points": 5,
                "note": ("legacy values for these blocks are NOT comparable to new ones and must "
                         "not be pooled. The importer sets legacy_scale = true and the analysis "
                         "dataset excludes them by default."),
            }
        ],
    }
    assert len(renames) == 24, f"crosswalk renames: expected 24, got {len(renames)}"
    for block in LEGACY_RESCALED_BLOCKS:
        points = SCALES[by_id[f"{block}1"]["scale_id"]]["points"]
        assert points == 5, f"{block} is {points}-point canonically; the scale-change note lies"
    return crosswalk


# --------------------------------------------------------------------------- build
def build() -> dict[str, object]:
    criteria = parse_criteria()
    findings, gaps, thresholds = parse_codebook()
    chunks, links = parse_corpus()
    instrument = parse_instrument()

    artifacts = {
        "criteria.json": criteria, "criterion_findings.json": findings,
        "gaps.json": gaps, "thresholds.json": thresholds,
        "corpus_chunks.json": chunks, "chunk_criterion_links.json": links,
        "instrument.json": instrument,
    }
    for name, expected in EXPECTED.items():
        got = len(artifacts[f"{name}.json"])
        assert got == expected, f"{name}: expected {expected}, got {got}"

    met = [f["criterion_id"] for f in findings if f["finding"] == "Met"]
    assert met == ["3.1.a", "3.1.c", "4.1.c"], f"SHAM set drifted: {met}"

    gap_ids = {g["gap_id"] for g in gaps}
    lookup = {}
    for p in "12345":
        lever = f"L{p}"
        t1 = sorted(g for g in gap_ids if g.startswith(f"{p}.1"))
        t2 = sorted(g for g in gap_ids if g.startswith(f"{p}.2"))
        lookup[lever] = {"0": [], "1": t1, "2": t1 + t2}
    assert sum(len(v["2"]) for v in lookup.values()) == 30
    artifacts["dial_lookup.json"] = lookup

    # New in 2.0. The eight above are frozen; these two are generated here for the first time.
    artifacts["arms.json"] = build_arms(gaps, lookup)
    artifacts["legacy_crosswalk.json"] = build_crosswalk(instrument)
    return artifacts


#: The eight files built from the source documents. Frozen: `--check` must exit 0 at all times,
#: and nothing in M1 onward may change a byte of them (`CLAUDE.md` → Before writing code).
FROZEN_FILES: tuple[str, ...] = (
    "criteria.json", "criterion_findings.json", "gaps.json", "thresholds.json",
    "corpus_chunks.json", "chunk_criterion_links.json", "instrument.json", "dial_lookup.json",
)


def serialise(obj: object) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="diff against committed files instead of writing")
    args = ap.parse_args()

    artifacts = build()
    OUT.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, obj in artifacts.items():
        text = serialise(obj)
        digest = hashlib.sha256(text.encode()).hexdigest()[:12]
        path = OUT / name
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            ok = current == text
            failed |= not ok
            print(f"{'OK  ' if ok else 'DIFF'} {name:<32} sha256={digest}")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {name:<32} {len(text):>7} bytes  sha256={digest}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
