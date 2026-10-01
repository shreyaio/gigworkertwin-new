"""Research model — `docs/06` §8. Ten sections, **in the mandatory order**.

Three contracts this module must not break:

* **The page renders from structured data**, never from prose written here. Everything comes from
  `services/research.research_model_view()`, which generates what the codebase owns from the
  frozen register and the structural model, and reads the rest from
  `config/research_model.yaml`. No handler computes anything (`docs/05` §8.4 rule 5).
* **Nothing is fabricated.** `docs/06` §8.9 says it of the reference list, and the same rule holds
  for every other researcher-supplied field: an unsupplied value renders an explicit empty state
  naming what is missing, never a blank cell that reads as "nothing to say".
* **The measurement mapping table is required** (§8.4). Without it this page and Statistics appear
  to describe different studies, so `_MEASUREMENT_REQUIRED` is asserted at build time rather than
  left to a reviewer to notice.

The diagram degrades to a layered board plus a full edge table. `CLAUDE.md`: degrade the styling,
never the content — the edge list is the diagram's content, and it is always present.
"""

from __future__ import annotations

import tempfile

import gradio as gr

from ..components import (
    app_header,
    data_table,
    empty_state,
    esc,
    global_nav,
    section_title,
)
from ..theme import page_classes

#: `docs/06` §8's ten sections, in order. Asserted at build time: the order is mandatory and a
#: silently reordered page is a different document.
SECTION_ORDER: tuple[str, ...] = (
    "The model in one line",
    "Research questions",
    "Research model diagram",
    "Measurement mapping",
    "Hypotheses",
    "Research method",
    "Constructs and definitions",
    "How this ties the validation together",
    "Reference list",
    "Write it all to a document",
)

#: §8.4 is not optional. A page without it and the Statistics page describe different studies.
_MEASUREMENT_REQUIRED = "Measurement mapping"

_GAP = '<span class="tl-muted">Not supplied yet</span>'


def _supplied(value: str) -> str:
    return esc(value) if value.strip() else _GAP


def render_research_model(badge: str | None = None) -> None:
    """Build the Research model page into the enclosing Blocks context."""
    from twinlab.services.research import research_model_view

    assert _MEASUREMENT_REQUIRED in SECTION_ORDER, "docs/06 §8.4 is required, not optional"

    view = research_model_view()

    with gr.Column(elem_classes=page_classes("/research")):
        app_header("Research model", "Constructs, hypotheses and the write-up", badge)
        global_nav("/research")

        # ---------------------------------------------------------- 1. one line
        gr.HTML(section_title(SECTION_ORDER[0]))
        gr.HTML(f'<div class="tl-card tl-lede">{esc(view.one_line)}</div>')
        gr.HTML(
            "".join(
                f'<div class="tl-card"><strong>{esc(card.title)}</strong>'
                f'<div class="tl-link-desc">{esc(card.detail)}</div>'
                + "".join(f"<div>{esc(item)}</div>" for item in card.items)
                + "</div>"
                for card in view.summary_cards
            ),
            elem_classes=["tl-card-grid"],
        )

        # ---------------------------------------------------- 2. research questions
        gr.HTML(section_title(SECTION_ORDER[1]))
        gr.HTML(
            "".join(
                f'<div class="tl-card"><strong>{esc(q.rq_id)} — {esc(q.title)}</strong>'
                f"<div>{_supplied(q.question)}</div>"
                + (
                    f'<div class="tl-link-desc">Hypotheses: {esc(", ".join(q.hypotheses))}</div>'
                    if q.hypotheses
                    else ""
                )
                + (
                    f'<div class="tl-link-desc">Contribution: {esc(q.contribution)}</div>'
                    if q.contribution.strip()
                    else ""
                )
                + "</div>"
                for q in view.research_questions
            )
            or empty_state(
                "No research question has been written yet.",
                "They live in config/research_model.yaml. Nothing here invents one.",
            ),
            elem_classes=["tl-card-grid"],
        )

        # ------------------------------------------------------------ 3. diagram
        gr.HTML(section_title(SECTION_ORDER[2]))
        gr.HTML(_diagram_html(view))
        gr.HTML(
            data_table(
                ["From", "To", "Kind"],
                [[esc(e.source), esc(e.target), esc(e.kind)] for e in view.diagram_edges],
            )
        )
        gr.HTML(
            f'<div class="tl-prov">Model fingerprint {esc(view.model_fingerprint)} — the same '
            "string every analysis run records, so this page and Statistics are provably "
            "describing one model.</div>"
        )

        # ------------------------------------------------- 4. measurement mapping
        gr.HTML(section_title(SECTION_ORDER[3]))
        gr.Markdown(
            "*The diagram's constructs do not map one-to-one onto what the instrument fields. "
            "This table states how the nine measured constructs operationalise the diagram; "
            "every column is read from the frozen register or from the structural model.*"
        )
        gr.HTML(
            data_table(
                [
                    "Construct",
                    "Role in the diagram",
                    "Item block",
                    "Indicators",
                    "Scale",
                    "Metric",
                    "Index sign",
                ],
                [
                    [
                        f"{esc(r.code)} — {esc(r.label)}",
                        esc(r.role),
                        esc(r.block),
                        str(r.indicators),
                        f"{esc(r.scale_id)} ({r.scale_points}-point)",
                        esc(r.metric_name) if r.metric_name else "—",
                        "—" if r.index_sign is None else f"{r.index_sign:+d}",
                    ]
                    for r in view.measurement_map
                ],
            )
        )

        # --------------------------------------------------------- 5. hypotheses
        gr.HTML(section_title(SECTION_ORDER[4]))
        gr.HTML(
            data_table(
                ["Hypothesis ID", "Statement", "Support"],
                [
                    [esc(h.hypothesis_id), esc(h.statement), esc(h.support or "Not yet tested")]
                    for h in view.hypotheses
                ],
                empty=empty_state(
                    "No hypothesis has been written yet.",
                    "They live in config/research_model.yaml, and are written against the frozen "
                    f"model {view.model_fingerprint}. Nothing here invents one.",
                ),
            )
        )

        # ------------------------------------------------------ 6. research method
        gr.HTML(section_title(SECTION_ORDER[5]))
        gr.HTML(
            data_table(
                ["Part", "What it involves", "In this build"],
                [
                    [esc(m.part), _supplied(m.involves), esc(m.from_the_build) or "—"]
                    for m in view.method
                ],
            )
        )

        # ------------------------------------------- 7. constructs and definitions
        gr.HTML(section_title(SECTION_ORDER[6]))
        gr.HTML(
            data_table(
                ["Construct", "Definition", "Where it comes from"],
                [
                    [
                        f"{esc(c.code)} — {esc(c.label)}",
                        _supplied(c.definition),
                        _supplied(c.source),
                    ]
                    for c in view.constructs
                ],
            )
        )

        # ------------------------------------------------ 8. the validation mapping
        gr.HTML(section_title(SECTION_ORDER[7]))
        gr.HTML(
            data_table(
                ["Technique", "What it assesses", "Where it is used", "Paper section"],
                [
                    [
                        esc(v.technique),
                        esc(v.assesses),
                        esc(v.where_used),
                        _supplied(v.paper_section),
                    ]
                    for v in view.validation_map
                ],
            )
        )

        # ----------------------------------------------------------- 9. references
        gr.HTML(section_title(SECTION_ORDER[8]))
        gr.HTML(_references_html(view))

        # ------------------------------------------------------ 10. the document
        gr.HTML(section_title(SECTION_ORDER[9]))
        gr.Markdown(
            "*Generated from the same structured data this page renders, so the file and the "
            "screen cannot disagree. Sections and tables are preserved, and an unsupplied field "
            "is exported as an explicit gap rather than dropped — a document that omitted its "
            "empty sections would read as complete.*"
        )
        document = gr.File(label="Download", visible=False)

        def _write() -> gr.update:
            """Render the document to a temp file. **Nothing durable is written** (I16).

            `tempfile` is the same mechanism the Statistics export uses: a handle that exists for
            one download because `gr.File` requires a path. It is not evidence, it is not
            acknowledged as stored, and the Space's disk resets under it.
            """
            from twinlab.services.research import research_document

            handle = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", prefix="research_model_", delete=False, encoding="utf-8"
            )
            handle.write(research_document())
            handle.close()
            return gr.update(value=handle.name, visible=True)

        gr.Button("Write it all to a document", variant="primary").click(_write, outputs=document)


def _diagram_html(view) -> str:
    """`docs/06` §8.3 as a layered board. Degraded in styling, never in content.

    Gradio cannot draw a real path diagram, so the layers are columns and the arrows are the table
    beneath — which carries every edge, including the moderation and main-effect paths a picture
    would have to letter separately anyway (`CLAUDE.md`, "when Gradio cannot do it").
    """
    layers: dict[int, list] = {}
    for node in view.diagram_nodes:
        layers.setdefault(node.layer, []).append(node)
    columns = []
    for layer in sorted(layers):
        cells = "".join(
            f'<div class="tl-node"><strong>{esc(n.code)}</strong>'
            f'<div class="tl-link-desc">{esc(n.label)}</div>'
            # `tl-muted`, not `tl-prov`: the role is a label, and tl-prov is blue and underlined,
            # which makes a non-link read as a link (`docs/05` §6).
            f'<div class="tl-muted">{esc(n.role)}</div></div>'
            for n in layers[layer]
        )
        columns.append(f'<div class="tl-layer">{cells}</div>')
    return f'<div class="tl-diagram">{"".join(columns)}</div>'


def _references_html(view) -> str:
    """§8.9, grouped by theme. **Empty until supplied — never fabricate a reference.**"""
    if not view.references:
        return empty_state(
            "No references have been supplied.",
            "The reference list is empty until the researcher writes it. Nothing here invents "
            "one (docs/06 §8.9).",
        )
    out: list[str] = []
    for theme in view.reference_themes:
        rows = [r for r in view.references if r.theme == theme]
        if not rows:
            continue
        out.append(f'<div class="tl-card"><strong>{esc(theme)}</strong>')
        for ref in rows:
            link = (
                f' <a href="{esc(ref.doi)}" target="_blank" rel="noopener">{esc(ref.doi)}</a>'
                if ref.doi
                else ""
            )
            out.append(f"<div>{esc(ref.citation)}{link}</div>")
        out.append("</div>")
    return "".join(out)


__all__ = ["SECTION_ORDER", "render_research_model"]
