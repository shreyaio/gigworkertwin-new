"""The Research model page. `docs/06` §8.

**The page is rendered from structured data, not from prose**, and the split is the point:

* **Everything the codebase owns is generated from it.** The nine constructs, their item blocks,
  indicator counts, scales and index signs come from the frozen register. The diagram comes from
  `stats/spec.py::STRUCTURAL_EDGES` — *the same object the estimator uses* — and the page prints
  `ModelSpec.fingerprint()` beside it, so a reader can see the Research model page and the
  Statistics page are describing one model. `docs/06` §8.4 exists precisely because they could
  otherwise drift, and generating both from one source is how this build makes that impossible.
* **Everything only a researcher can write is supplied**, in `config/research_model.yaml`, and is
  **empty until they write it**. A research question's wording, a hypothesis, a construct's
  definition, its source citation and the reference list are claims; a build step that filled them
  in would be fabricating research. §8.9 says this of the reference list, and the same rule is
  applied to every other prose field here.

The validation mapping's **row set** is generated from the application's own objects — the two
holdouts, the two control cells, the reference arm and all eight validity tests — so a technique
cannot appear that the app does not run, and one it runs cannot be missing.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from config.settings import CONFIG_DIR, settings
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.reference import CONSTRUCTS, LEVER_BY_POSITION, LEVER_NAMES
from twinlab.models.research import (
    ConstructDefinitionRow,
    DiagramEdge,
    DiagramNode,
    DiagramRole,
    Hypothesis,
    MeasurementMapRow,
    MethodRow,
    Reference,
    ResearchModelView,
    ResearchQuestion,
    SummaryCard,
    ValidationMapRow,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, N_CODES, SHAM_CODE
from twinlab.stats.spec import (
    ANTECEDENT_TARGETS,
    ARM_CONSTRUCT,
    ARM_REFERENCE,
    INTENTIONS,
    INTERACTION_CONSTRUCT,
    MODERATED,
    MODERATOR,
    STRUCTURAL_EDGES,
    build_model_spec,
    construct_items,
)

#: `docs/06` §8.1's one-liner. The **only** sentence of research prose in this module, and it is a
#: restatement of `docs/07` §7.2's chain rather than a claim: every noun in it is a construct code
#: the register defines and every arrow is an edge the estimator uses.
ONE_LINE = (
    "What a platform commits to changes how drivers see the algorithm managing them, which "
    "changes whether they think it treats them fairly and clearly, which changes how satisfied "
    "they are — and satisfaction is what moves whether they stay, push back or leave, more or "
    "less strongly depending on how much they need the money."
)

#: `docs/06` §8.6's nine parts, **in order**. The order is mandatory; the prose is supplied.
METHOD_PARTS: tuple[tuple[str, str], ...] = (
    ("design", "Design"),
    ("sample", "Sample"),
    ("measures", "Measures"),
    ("experiment", "The experiment inside the study"),
    ("twin_reconstruction", "Twin reconstruction"),
    ("validation_before_use", "Validation before use"),
    ("design_space", "Design space"),
    ("analysis", "Analysis"),
    ("ethics_and_openness", "Ethics and openness"),
)

#: A construct's place in `docs/07` §7.2's diagram. Derived from the structural model below rather
#: than listed here — this maps only the layer a code lands on to the word `docs/06` §8.3 uses.
_ROLE_BY_LAYER: dict[int, DiagramRole] = {
    0: "antecedent",
    1: "algorithmic-management perception",
    2: "justice perception",
    3: "satisfaction",
    4: "behavioural intention",
}


class ResearchConfigError(RuntimeError):
    """`config/research_model.yaml` is missing or inconsistent. Never defaulted around.

    The file carries the researcher's own claims. A missing or malformed one must fail loudly
    rather than render a page of empty states that looks like "nothing has been written yet" when
    the truth is "the file that holds it could not be read".
    """


# ------------------------------------------------------------------------- the config


@lru_cache(maxsize=1)
def load_research_config() -> dict[str, Any]:
    """`config/research_model.yaml`, validated on load.

    Cross-checked against the frozen register and the hypothesis list, so a construct key that is
    not one of the nine, or a research question citing a hypothesis that does not exist, fails here
    rather than rendering a page that quietly omits it.
    """
    path = CONFIG_DIR / "research_model.yaml"
    if not path.exists():
        raise ResearchConfigError(
            f"{path} is absent. It holds the research questions, hypotheses, construct "
            "definitions and the reference list — the parts of docs/06 §8 that only the "
            "researcher can write. It is not defaulted in code, because a defaulted research "
            "question is a claim nobody made."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    codes = {c.code for c in CONSTRUCTS}
    supplied_codes = set(raw.get("constructs") or {})
    if not supplied_codes <= codes:
        raise ResearchConfigError(
            f"research_model.yaml names construct(s) {sorted(supplied_codes - codes)}, which are "
            f"not among the nine in the frozen register ({sorted(codes)}). The register is the "
            "definition; this file only annotates it."
        )

    ids = {h.get("hypothesis_id") for h in (raw.get("hypotheses") or [])}
    for question in raw.get("research_questions") or []:
        missing = [h for h in (question.get("hypotheses") or []) if h not in ids]
        if missing:
            raise ResearchConfigError(
                f"{question.get('rq_id')} cites hypothes(es) {missing}, which are not in this "
                "file's `hypotheses` block. A research question pointing at a hypothesis nobody "
                "wrote is a dangling claim."
            )
    return raw


# ---------------------------------------------------------------- generated from the model


def diagram_layers() -> dict[str, int]:
    """Each construct's layer, computed from `STRUCTURAL_EDGES`. `docs/06` §8.3.

    Longest-path layering, so a construct sits to the right of everything that reaches it. Derived
    rather than listed: a change to the structural model moves the diagram and the measurement
    map together, and moves `ModelSpec.fingerprint()` with them.
    """
    layers: dict[str, int] = {code: 1 for code in ANTECEDENT_TARGETS}
    # Relax repeatedly; the model is a DAG (asserted in `stats/spec.py`) so this terminates.
    for _ in range(len(CONSTRUCTS) + 1):
        for source, target in STRUCTURAL_EDGES:
            layers[target] = max(layers.get(target, 1), layers.get(source, 1) + 1)
    satisfaction_layer = layers.get(MODERATED, 3)
    for code in INTENTIONS:
        layers[code] = satisfaction_layer + 1
    layers[MODERATOR] = satisfaction_layer
    layers[ARM_CONSTRUCT] = 0
    return layers


def _role_for(code: str, layer: int) -> DiagramRole:
    if code == MODERATOR:
        return "moderator"
    return _ROLE_BY_LAYER.get(layer, "behavioural intention")


def diagram() -> tuple[list[DiagramNode], list[DiagramEdge]]:
    """`docs/06` §8.3's theoretical model, **as the estimator has it**.

    Built from `STRUCTURAL_EDGES` plus the arm block and the interaction term that
    `build_model_spec` adds, so the picture cannot show a path the model does not estimate.
    """
    layers = diagram_layers()
    labels = {c.code: c.label for c in CONSTRUCTS}
    nodes = [
        DiagramNode(
            code=ARM_CONSTRUCT,
            label=f"What the platform commits to ({ARM_REFERENCE} is the reference)",
            role="antecedent",
            layer=0,
        )
    ]
    nodes += [
        DiagramNode(
            code=c.code, label=labels[c.code], role=_role_for(c.code, layers[c.code]),
            layer=layers[c.code],
        )
        for c in CONSTRUCTS
    ]

    edges = [DiagramEdge(source=ARM_CONSTRUCT, target=t) for t in ANTECEDENT_TARGETS]
    edges += [DiagramEdge(source=s, target=t) for s, t in STRUCTURAL_EDGES]
    edges += [DiagramEdge(source=MODERATED, target=t) for t in INTENTIONS]
    edges += [
        DiagramEdge(source=MODERATOR, target=t, kind="main effect") for t in INTENTIONS
    ]
    edges += [
        DiagramEdge(source=INTERACTION_CONSTRUCT, target=t, kind="moderation")
        for t in INTENTIONS
    ]
    return nodes, edges


def measurement_map(ref: ReferenceData | None = None) -> list[MeasurementMapRow]:
    """**`docs/06` §8.4 — required, new in 2.0.** Every column read, none written.

    How each of the nine measured constructs operationalises the diagram: which item block fields
    it, how many indicators, on which scale, and whether it enters the index and with which sign.
    Without this table the Research model page and the Statistics page appear to describe different
    studies (`docs/06` §8.4).
    """
    ref = ref or reference()
    layers = diagram_layers()
    rows: list[MeasurementMapRow] = []
    for construct in CONSTRUCTS:
        # `construct_items` is the estimator's own filter, not a second one written here. That is
        # what stops this table from claiming a construct is fielded by items the model does not
        # give it — the precise drift `docs/06` §8.4 exists to prevent.
        items = construct_items(construct.code, ref)
        scale_id = construct.scale_id or ""
        rows.append(
            MeasurementMapRow(
                code=construct.code,
                label=construct.label,
                role=_role_for(construct.code, layers[construct.code]),
                block=construct.block,
                indicators=len(items),
                scale_id=scale_id,
                scale_points=ref.scales[scale_id].points if scale_id else 0,
                metric_name=construct.metric_name,
                index_sign=construct.index_sign,
            )
        )
    return rows


def summary_cards(ref: ReferenceData | None = None) -> list[SummaryCard]:
    """`docs/06` §8.1's five cards. Generated from the levers and the diagram's layers."""
    ref = ref or reference()
    layers = diagram_layers()

    def codes_at(*roles: str) -> list[str]:
        return [
            f"{c.code} — {c.label}"
            for c in CONSTRUCTS
            if _role_for(c.code, layers[c.code]) in roles
        ]

    return [
        SummaryCard(
            title="Five dials",
            detail=(
                f"Five Fairwork levers at three settings each: {N_CODES} version codes, plus "
                f"the two control cells {CONTROL_CODE} and {SHAM_CODE}."
            ),
            items=[f"{lever} — {LEVER_NAMES[lever]}" for lever in LEVER_BY_POSITION],
        ),
        SummaryCard(
            title="How the algorithm is seen",
            detail="What the commitments change first.",
            items=codes_at("algorithmic-management perception"),
        ),
        SummaryCard(
            title="How the driver feels",
            detail="Justice perceptions, and the satisfaction they feed.",
            items=codes_at("justice perception", "satisfaction"),
        ),
        SummaryCard(
            title="What the driver does",
            detail="The three behavioural intentions, reached only through satisfaction.",
            items=codes_at("behavioural intention"),
        ),
        SummaryCard(
            title="Who reacts differently",
            detail=(
                f"{MODERATOR} moderates the {MODERATED} path to all three intentions, and carries "
                "a main effect of its own."
            ),
            items=codes_at("moderator"),
        ),
    ]


def _build_facts(ref: ReferenceData) -> dict[str, str]:
    """The fact this build owns about each method part, or ``""``.

    Generated, never typed: counts and codes that would otherwise be restated in prose and be free
    to go stale. Shown beneath the researcher's own words as *In this build*.
    """
    battery = len(ref.battery_item_ids)
    return {
        "design": (
            f"A between-subjects survey with {len(ref.arms)} arms ({ARM_REFERENCE} is the "
            f"reference), and a within-twin counterfactual sweep over {N_CODES} version codes."
        ),
        "measures": (
            f"{len(ref.items)} registered items; {battery} of them form the twin battery. "
            f"{len(CONSTRUCTS)} constructs, six of which carry an index sign."
        ),
        "experiment": (
            f"Two control cells and exactly two: {CONTROL_CODE} (no change) and {SHAM_CODE} "
            "(what Uber already does)."
        ),
        "twin_reconstruction": (
            f"Persona template {settings.persona_template_version}, built in Python from all "
            f"{battery} battery answers, in words rather than numbers."
        ),
        "validation_before_use": (
            "Two holdouts — H3 gates and H2 does not — and eight validity tests, all reported "
            "whatever they say."
        ),
        "design_space": (
            f"{N_CODES} codes = five levers x three dials. Style version "
            f"{settings.style_version}; ten lever paragraphs per style version, not {N_CODES}."
        ),
        "analysis": (
            f"Six metric shifts and one index per cell, computed in Python; the PLS-SEM model's "
            f"fingerprint is {build_model_spec(ref).fingerprint()}."
        ),
        "sample": "",
        "ethics_and_openness": "",
    }


def validation_map(raw: dict[str, Any]) -> list[ValidationMapRow]:
    """`docs/06` §8.8, covering **both holdouts and all eight validity tests**.

    The row set is generated from the app's own objects, so it cannot omit a technique the app
    runs or list one it does not. `docs/08` §6.3 supplies the `assesses` wording, through the
    config so it is editable in one place.
    """
    from twinlab.services.lab import VALIDITY_TESTS

    supplied = raw.get("validation_map") or {}

    def row(key: str, technique: str, where: str) -> ValidationMapRow:
        entry = supplied.get(key) or {}
        return ValidationMapRow(
            technique=technique,
            assesses=str(entry.get("assesses") or ""),
            where_used=where,
            paper_section=str(entry.get("paper_section") or ""),
        )

    rows = [
        row("h3_holdout", "H3 holdout (quality gate)", "Twin Lab → Validation"),
        row("h2_holdout", "H2 holdout, per arm", "Twin Lab → Validation"),
        row("base_arm", f"{ARM_REFERENCE} arm", "Statistics → the arm dummies"),
        row("control_00000", f"{CONTROL_CODE} control", "Twin Lab → Results"),
        row("control_sham", f"{SHAM_CODE} control", "Twin Lab → Results"),
    ]
    rows += [
        # The card's own name, not a lower-cased copy of it: `.lower()` turned
        # "A second AI model" into "a second ai model".
        row(
            f"validity_{card.number}",
            f"Test {card.number} — {card.name}",
            "Twin Lab → Validity tests",
        )
        for card in VALIDITY_TESTS
    ]
    return rows


# ---------------------------------------------------------------------------- the view


def research_model_view(ref: ReferenceData | None = None) -> ResearchModelView:
    """The whole page, in `docs/06` §8's mandatory section order.

    Deterministic and offline: every value is either frozen reference data, the structural model,
    or the researcher's own YAML. **No database, no model call**, so the page renders identically
    on a machine that has never been seeded.
    """
    ref = ref or reference()
    raw = load_research_config()
    nodes, edges = diagram()
    facts = _build_facts(ref)
    labels = {c.code: c.label for c in CONSTRUCTS}
    construct_prose = raw.get("constructs") or {}
    method_prose = raw.get("method") or {}

    references = [Reference(**r) for r in (raw.get("references") or [])]
    themes = list(raw.get("reference_themes") or [])
    themes += sorted({r.theme for r in references} - set(themes))

    return ResearchModelView(
        one_line=ONE_LINE,
        summary_cards=summary_cards(ref),
        research_questions=[
            ResearchQuestion(**q) for q in (raw.get("research_questions") or [])
        ],
        diagram_nodes=nodes,
        diagram_edges=edges,
        model_fingerprint=build_model_spec(ref).fingerprint(),
        measurement_map=measurement_map(ref),
        hypotheses=[Hypothesis(**h) for h in (raw.get("hypotheses") or [])],
        method=[
            MethodRow(
                part=label,
                involves=str(method_prose.get(key) or ""),
                from_the_build=facts.get(key, ""),
            )
            for key, label in METHOD_PARTS
        ],
        constructs=[
            ConstructDefinitionRow(
                code=c.code,
                label=labels[c.code],
                definition=str((construct_prose.get(c.code) or {}).get("definition") or ""),
                source=str((construct_prose.get(c.code) or {}).get("source") or ""),
            )
            for c in CONSTRUCTS
        ],
        validation_map=validation_map(raw),
        references=references,
        reference_themes=themes,
    )


# ------------------------------------------------------------------- §8.10 the document


def research_document(view: ResearchModelView | None = None) -> str:
    """`docs/06` §8.10 — the research document, **from this structured data**.

    A document export, not a database (§8.10): it is generated on demand from the same view the
    page renders, so the file and the screen can never disagree. Sections and tables are preserved
    in §8's order.

    **Unsupplied content is exported as an explicit gap**, not silently dropped. A document that
    omitted its empty sections would read as complete, and the researcher would have no list of
    what is still to write.
    """
    view = view or research_model_view()
    out: list[str] = ["# Research model", "", "## 1. The model in one line", "", view.one_line, ""]

    for card in view.summary_cards:
        out += [f"**{card.title}** — {card.detail}", ""]
        out += [f"- {item}" for item in card.items] + [""]

    out += ["## 2. Research questions", ""]
    for question in view.research_questions:
        out += [f"### {question.rq_id} — {question.title}", ""]
        out += [question.question if question.supplied else _GAP, ""]
        if question.hypotheses:
            out += [f"Hypotheses: {', '.join(question.hypotheses)}", ""]
        if question.contribution:
            out += [f"Contribution: {question.contribution}", ""]

    out += ["## 3. Research model diagram", "", f"Model fingerprint `{view.model_fingerprint}`", ""]
    for edge in view.diagram_edges:
        suffix = "" if edge.kind == "path" else f"  ({edge.kind})"
        out.append(f"- {edge.source} -> {edge.target}{suffix}")
    out.append("")

    out += ["## 4. Measurement mapping", ""]
    out += _table(
        ["Construct", "Label", "Role in the diagram", "Item block", "Indicators", "Scale",
         "Metric", "Index sign"],
        [
            [r.code, r.label, r.role, r.block, str(r.indicators),
             f"{r.scale_id} ({r.scale_points}-point)", r.metric_name or "—",
             "—" if r.index_sign is None else f"{r.index_sign:+d}"]
            for r in view.measurement_map
        ],
    )

    out += ["## 5. Hypotheses", ""]
    out += (
        _table(
            ["Hypothesis ID", "Statement", "Support"],
            [[h.hypothesis_id, h.statement, h.support or "Not yet tested"]
             for h in view.hypotheses],
        )
        if view.hypotheses
        else [_GAP, ""]
    )

    out += ["## 6. Research method", ""]
    out += _table(
        ["Part", "What it involves", "In this build"],
        [[m.part, m.involves or _GAP, m.from_the_build or "—"] for m in view.method],
    )

    out += ["## 7. Constructs and definitions", ""]
    out += _table(
        ["Construct", "Definition", "Where it comes from"],
        [[f"{c.code} — {c.label}", c.definition or _GAP, c.source or _GAP]
         for c in view.constructs],
    )

    out += ["## 8. How this ties the validation together", ""]
    out += _table(
        ["Technique", "What it assesses", "Where it is used", "Paper section"],
        [[v.technique, v.assesses, v.where_used, v.paper_section or _GAP]
         for v in view.validation_map],
    )

    out += ["## 9. References", ""]
    if not view.references:
        out += [_NO_REFERENCES, ""]
    else:
        for theme in view.reference_themes:
            rows = [r for r in view.references if r.theme == theme]
            if not rows:
                continue
            out += [f"### {theme}", ""]
            out += [f"- {r.citation}" + (f" {r.doi}" if r.doi else "") for r in rows] + [""]
    return "\n".join(out).rstrip() + "\n"


#: What an unsupplied field exports and renders as. Explicit, so a gap reads as a gap.
_GAP = "_Not supplied yet._"

#: `docs/06` §8.9's empty state. **Never fabricate a reference.**
_NO_REFERENCES = (
    "_No references have been supplied. The reference list is empty until the researcher writes "
    "it; nothing here invents one._"
)


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    """A Markdown table, escaped so a pipe in a citation cannot break the grid."""
    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(cell(h) for h in header) + " |"]
    lines.append("|" + "|".join("---" for _ in header) + "|")
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return lines + [""]


__all__ = [
    "METHOD_PARTS",
    "ONE_LINE",
    "ResearchConfigError",
    "diagram",
    "diagram_layers",
    "load_research_config",
    "measurement_map",
    "research_document",
    "research_model_view",
    "summary_cards",
    "validation_map",
]
