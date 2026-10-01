"""Domain components. `docs/05_DESIGN_SYSTEM.md` §4.4 and §4.5.

Two of these carry the rules that are easiest to get wrong and hardest to notice wrong:

* **:func:`what_twins_are_told` is one component used in three places** — the Dial board, the
  Results side panel and the Twins side panel (`docs/05` §4.4). It has exactly one implementation
  and one source, :func:`twinlab.services.dials.what_twins_are_told`, and the M10 acceptance test
  asserts that by import graph. Two renderers would drift, and a drift here means the researcher
  is reading a different treatment from the one the twins were given.

* **:func:`metric_bars` colours by "good for the driver", not by sign** (`docs/05` §4.5). The
  decision is made in `services/metrics_view.py` from `constructs.index_sign`; this function only
  paints ``MetricRow.good_for_driver``. It does **no arithmetic** on a shift — not a sum, not a
  percentage (`docs/05` §8.4 rule 5).

Everything else here is layout over values the service layer already computed.
"""

from __future__ import annotations

from twinlab.models.stats import AnalysisProvenance, StatsTableSpec
from twinlab.models.view import (
    AgentCardView,
    BudgetView,
    DialBoard,
    EventRow,
    GridCell,
    InteractionRow,
    MetricBars,
    ResultsPanel,
    TellLever,
    TwinPanel,
)

from .primitives import (
    badge_cached,
    data_table,
    empty_state,
    esc,
    kv_table,
    num,
    pill,
    section_title,
    status_dot,
)


def version_code_display(code: str, fairwork_text: str = "") -> str:
    """The version code as the primary identifier it is. `docs/05` §2.2."""
    spaced = " ".join(code)
    sub = f'<div class="tl-code-sub">{esc(fairwork_text)}</div>' if fairwork_text else ""
    return (
        f'<div class="tl-code-block"><div class="tl-code" aria-label="version {esc(code)}">'
        f"{esc(spaced)}</div>{sub}</div>"
    )


def dial_legend() -> str:
    """`docs/05` §7 rule 1: the dial colours are a traffic light for **protection level**."""
    from twinlab.services.dials import DIAL_LEGEND

    parts = "".join(
        f'<span class="tl-legend-item tl-dial-{i}">{esc(text)}</span>'
        for i, text in enumerate(DIAL_LEGEND)
    )
    return f'<div class="tl-legend">{parts}</div>'


def what_twins_are_told(told: list[TellLever]) -> str:
    """**The only renderer of this content.** `docs/05` §4.4.

    Takes the service layer's `TellLever` list unchanged. A twin never sees these bullets, and
    this summary is never fed to a model (`docs/03` §4.3) — the twin-facing artefact is
    :func:`scenario_text_block`, built from the same `DeltaSpec` by a different path.
    """
    blocks = []
    for lever in told:
        bullets = (
            "".join(
                f'<li><span class="tl-gap-id">{esc(b.gap_id)}</span> {esc(b.text)}</li>'
                for b in lever.bullets
            )
            or '<li class="tl-absent">No change from today.</li>'
        )
        blocks.append(
            f'<div class="tl-told-lever tl-dial-{lever.dial}">'
            f'<div class="tl-told-head">{esc(lever.heading)}</div>'
            f"<ul>{bullets}</ul></div>"
        )
    return f'<div class="tl-told tl-scroll">{"".join(blocks)}</div>'


def scenario_text_block(paragraphs: list[str]) -> str:
    """The five lever paragraphs **actually rendered** — what a twin was shown.

    Never the bullet summary, and never a re-render: `docs/09` §2 requires that what is displayed
    is what was used.
    """
    if not paragraphs:
        return empty_state(
            "No scenario text stored for this version.",
            "Ask the twins for this version; the rendered paragraphs are stored with the run.",
        )
    body = "".join(f"<p>{esc(p)}</p>" for p in paragraphs)
    return f'<div class="tl-scenario tl-scroll">{body}</div>'


def dial_board_summary(board: DialBoard) -> str:
    """The right-hand column of `docs/06` §3.2: code, score, and what the twins are told."""
    warning = (
        f'<div class="tl-warn-strip" role="alert">{esc(board.warning)}</div>'
        if board.warning
        else ""
    )
    return (
        f"{warning}"
        f"{version_code_display(board.version_code, board.fairwork_text)}"
        f"{section_title('What the twins are told')}"
        f"{what_twins_are_told(board.told)}"
    )


def metric_bars(bars: MetricBars, *, cached: bool = False) -> str:
    """Six rows, the index, and one plain sentence. `docs/05` §4.5.

    Zero is a centre line; positive extends right, negative left; the colour says whether the
    movement is good for the driver. Every row carries its number, so the bar is redundant
    encoding and never the only encoding (`docs/05` §6).
    """
    if not bars.rows or all(r.value is None for r in bars.rows):
        return empty_state(bars.caption or "Not tested.", "Press Ask the twins for this version.")

    rows = []
    for row in bars.rows:
        if row.value is None:
            rows.append(
                f'<div class="tl-bar-row"><span class="tl-bar-label">{esc(row.label)}</span>'
                f'<span class="tl-bar-track"></span>'
                f'<span class="tl-bar-value tl-num">{num(None)}</span></div>'
            )
            continue
        side = "right" if row.value > 0 else "left"
        tone = "good" if row.good_for_driver else "bad" if row.good_for_driver is False else "flat"
        rows.append(
            f'<div class="tl-bar-row"><span class="tl-bar-label">{esc(row.label)}</span>'
            f'<span class="tl-bar-track"><span class="tl-bar tl-bar-{side} tl-bar-{tone}" '
            f'style="width:{row.bar_pct / 2:.2f}%"></span></span>'
            f'<span class="tl-bar-value tl-num">{esc(row.value_text)}</span></div>'
        )

    badge = f" {badge_cached()}" if cached else ""
    floor = f'<div class="tl-floor-note">{esc(bars.floor_note)}</div>' if bars.floor_note else ""
    return (
        f'<div class="tl-bars">{"".join(rows)}'
        f'<div class="tl-index">Index <span class="tl-num">{esc(bars.index_text)}</span>'
        f"{badge}</div>"
        f'<div class="tl-caption">{esc(bars.caption)}</div>{floor}</div>'
    )


#: The nine row labels, top to bottom. `services.metrics_view.grid_position` puts
#: ``pay * 3 + conditions`` on the row axis, so the rows ARE these nine pairs — the labels read
#: the same mapping rather than restating it, and a change to the odometer order (I2) that got
#: past the tests would show up here as a mislabelled grid rather than as nothing at all.
_GRID_ROW_LABELS: tuple[str, ...] = tuple(
    f"pay {pay}, cond. {cond}" for pay in range(3) for cond in range(3)
)


def grid_243(cells: list[GridCell]) -> str:
    """The 9 × 27 overview. `docs/06` §3.7, `docs/05` §8.3.

    Rendered as a table of buttons rather than a plot so every cell carries an accessible name and
    keyboard focus without a 243-cell keyboard trap. The **Tested versions table below it carries
    the same data linearly** and is the accessible equivalent (`docs/05` §6).

    A tested cell's colour depth is its ``intensity`` — where its index sits in the range tested
    so far. `docs/05` §6 forbids encoding anything by colour **alone**, so the exact index is in
    every cell's `title` and `aria-label` and again in the table beneath; the depth is a second,
    redundant channel that makes a swept grid readable at a glance, which a single flat green
    could not do.

    The row axis is labelled. Without the labels the grid is 243 anonymous squares and the reader
    has no way to tell which cell is which without hovering every one of them.
    """
    by_position = {(c.row, c.col): c for c in cells}
    body = []
    for row in range(9):
        label = _GRID_ROW_LABELS[row] if row < len(_GRID_ROW_LABELS) else ""
        tds = [f'<th scope="row" class="tl-grid-rowlab">{esc(label)}</th>']
        for col in range(27):
            cell = by_position.get((row, col))
            if cell is None:
                tds.append("<td></td>")
                continue
            classes = ["tl-cell"]
            style = ""
            if cell.tested:
                classes.append("tl-cell-tested")
                # A floor of 0.18 keeps the palest tested cell clearly darker than an untested
                # one: "tested and worst" and "not tested" are different facts and must not
                # render as the same square.
                depth = 0.18 + 0.82 * (cell.intensity if cell.intensity is not None else 1.0)
                style = f' style="--tl-cell-depth:{depth:.3f}"'
            if cell.outline:
                classes.append(f"tl-cell-{cell.outline}")
            tds.append(
                f'<td><button type="button" class="{" ".join(classes)}"{style} '
                f'data-code="{esc(cell.version_code)}" '
                f'title="{esc(cell.accessible_name)}" '
                f'aria-label="{esc(cell.accessible_name)}"></button></td>'
            )
        body.append("<tr>" + "".join(tds) + "</tr>")
    legend = (
        '<div class="tl-grid-caption">'
        "Rows: pay and conditions dials. Columns: contracts, management, representation dials. "
        "Grey means not tested yet. Red box: Uber today. Gold box: best so far. "
        "A deeper cell has a higher index."
        "</div>"
    )
    return (
        f'<div class="tl-grid-wrap tl-scroll"><table class="tl-grid">'
        f"<tbody>{''.join(body)}</tbody></table></div>{legend}"
    )


def interactions_panel(rows: list[InteractionRow]) -> str:
    """*Do changes work together?* — computable ones, **and the missing legs by name**. I17.

    A missing leg renders the code to run. Never an estimate, never a blank
    (`CLAUDE.md` rule 5).
    """
    if not rows:
        return empty_state(
            "No interactions involve this version yet.",
            "Run a second single-lever version and their joint cell.",
        )
    items = []
    for row in rows:
        tone = "complete" if row.computable else "pending"
        label = "computed" if row.computable else "cannot be computed"
        items.append(f"<li>{status_dot(tone, label)} <span>{esc(row.text)}</span></li>")
    return f'<ul class="tl-interactions">{"".join(items)}</ul>'


def log_tree(events: list[EventRow]) -> str:
    """`Time · Agent · Message`, nested by parent. `docs/06` §3.1.

    The caller appends rows from :func:`twinlab.services.runs.events_since`; this renders whatever
    it is handed. **The stream is never re-fetched whole** (`docs/04` §7.3).
    """
    if not events:
        return empty_state(
            "No agent messages yet.",
            "Start a quality test, a sweep or an Ask to see the run appear here.",
        )
    rows = []
    for event in events:
        indent = min(event.depth, 6) * 14
        rows.append(
            [
                f'<span class="tl-num">{esc(event.when[11:19] or event.when)}</span>',
                esc(event.agent or event.stage),
                f'<span style="padding-left:{indent}px">'
                f"{status_dot(_event_state(event.status), event.status or 'pending')} "
                f"{esc(event.message)}</span>",
            ]
        )
    return data_table(["Time", "Agent", "Message"], rows)


def _event_state(status: str) -> str:
    return {
        "ok": "complete",
        "error": "failed",
        "running": "running",
        "skipped": "pending",
    }.get(status, "pending")


def side_panel(title: str, body_html: str) -> str:
    """A visibility-toggled overlay's contents. Gradio has no true modal (`docs/05` §8.2)."""
    return (
        f'<div class="tl-side-panel"><div class="tl-side-head">{esc(title)}</div>'
        f'<div class="tl-side-body tl-scroll">{body_html}</div></div>'
    )


def agent_card(agent: AgentCardView) -> str:
    """One of the five. `docs/06` §3.1."""
    state = pill("enabled", "green") if agent.enabled else pill("not enabled", "grey")
    return (
        f'<div class="tl-card tl-agent-card"><div class="tl-agent-name">{esc(agent.name)}'
        f" {state}</div>"
        f'<div class="tl-agent-role">{esc(agent.description)}</div>'
        f'<div class="tl-agent-latest">{status_dot(agent.state, agent.state)} '
        f"{esc(agent.latest)}</div></div>"
    )


def budget_summary(budget: BudgetView) -> str:
    """Shown on **every** confirm step before anything starts. `docs/06` §9.

    Estimated credits read ``not known`` rather than a number: the free credit allowance is
    unpublished, and an invented figure would be read as a cost (`docs/10` §3.3).
    """
    rows = [
        ("Calls", f"{budget.calls:,}"),
    ]
    # `ARCHITECTURE_UPDATE.md` §2: the total is correct and stays; what was missing is the line
    # that says how it was reached. Rendered immediately under the total, where it is read.
    if budget.breakdown:
        rows.append(("How that is counted", esc(budget.breakdown)))
    if budget.per_unit:
        rows.append(("Calls per twin", esc(budget.per_unit)))
    rows += [
        ("Tokens in", f"{budget.tokens_in:,}"),
        ("Tokens out", f"{budget.tokens_out:,}"),
        ("Estimated time", esc(budget.est_hours_text)),
        ("Estimated credits", esc(budget.est_credits_text)),
        ("Already answered (not re-run)", f"{budget.cache_hits:,}"),
    ]
    warnings = "".join(f'<li class="tl-budget-warning">{esc(w)}</li>' for w in budget.warnings)
    warn_html = f'<ul class="tl-budget-warnings">{warnings}</ul>' if warnings else ""
    return f'<div class="tl-budget">{kv_table(rows, caption="Before this starts")}{warn_html}</div>'


def provenance_link(kind: str, identifier: str, label: str = "") -> str:
    """The product principle as a widget. `docs/05` §4.4.

    Beside a shift it opens the run; beside a run, the variant; beside a paragraph, the
    commitments and their corpus citations. Two clicks from any number to Uber's own words.
    """
    if not identifier:
        return ""
    text = label or f"{kind}: {identifier}"
    return (
        f'<a class="tl-prov" href="#{esc(kind)}-{esc(identifier)}" '
        f'data-kind="{esc(kind)}" data-id="{esc(identifier)}">{esc(text)}</a>'
    )


def twin_profile_card(panel: TwinPanel) -> str:
    """Steps 1–3 of the Twins side panel: identity, background, quality. `docs/06` §3.3."""
    background = (
        f'<div class="tl-twin-background">{esc(panel.background)}</div>' if panel.background else ""
    )
    return (
        f'<div class="tl-card"><div class="tl-twin-id">{esc(panel.twin_id)}</div>'
        f'<div class="tl-twin-identity">{esc(panel.identity)}</div>'
        f"{background}"
        f'<div class="tl-twin-quality">{esc(panel.quality_line)}</div></div>'
    )


def answer_compare(panel: TwinPanel) -> str:
    """Step 7: one table per construct block, in battery order. `docs/06` §3.3.

    The variant column header names the version, and a version with no completed run renders
    ``Not tested`` in every cell — never a fabricated number (I17). Holdout items are marked
    ``hidden``, because a twin never saw them (I6) and a silently absent row looks like a bug.
    """
    code = panel.selected_code
    variant_header = f"Twin, version {code}" if code else "Twin, version —"
    blocks = []
    for block in panel.blocks:
        rows = []
        for row in block.rows:
            marker = ' <span class="tl-hidden-flag">hidden</span>' if row.hidden else ""
            rows.append(
                [
                    f"{esc(row.item_id)}{marker}",
                    esc(row.question),
                    _cell(row.driver),
                    _cell(row.baseline),
                    _cell(row.variant),
                ]
            )
        blocks.append(
            section_title(block.label)
            + data_table(["Item", "Question", "Driver", "Twin today", variant_header], rows)
        )
    return "".join(blocks)


def results_panel_html(panel: ResultsPanel) -> str:
    """The Results side panel, rendered in `docs/06` §3.7's **mandatory seven-step order**.

    The order is not a layout choice. It is deliberately the same bundle the Analyst received, in
    the same order, so the researcher reads the input and the output together — which is what
    makes a written reading checkable against the numbers it was written about.
    """
    baselines = (
        kv_table(
            [(k, f"{v:.2f}") for k, v in sorted(panel.baselines.items())],
            caption="Baselines (Uber today)",
        )
        if panel.baselines
        else ""
    )

    if panel.analysis:
        mark = pill("Generated summary", "grey") + " " if panel.analysis_is_fallback else ""
        analysis = f'<div class="tl-card">{mark}{esc(panel.analysis)}</div>'
    else:
        analysis = empty_state(
            "No written analysis for this version.",
            "The analyst writes one when the cell completes.",
        )

    # `ARCHITECTURE_UPDATE.md` §4.3 item 4. Above everything, because it changes how every number
    # below it should be read: the shifts are one twin's, while the `00000` and `SHAM` floors they
    # are measured against came from the frozen panel. It is not a warning — a Studio number is a
    # real measurement — it is a statement of what quantity this is.
    origin = (
        ""
        if panel.origin != "studio"
        else (
            '<div class="tl-note-strip" role="note">'
            f"From the Twin Studio — <strong>n = {panel.twins_n}</strong>. "
            "Every number below is one twin's, and the floors it is read against come from the "
            "frozen panel, so this is not the same quantity as a swept cell. A later Dial board "
            "run for this version supersedes it."
            "</div>"
        )
    )
    return (
        origin
        # 1 and 2
        + version_code_display(panel.board.version_code, panel.board.fairwork_text)
        + section_title("What the twins are told")
        + what_twins_are_told(panel.board.told)
        # 3
        + section_title("Scenario text")
        + scenario_text_block(panel.scenario_text)
        # 4
        + section_title("Numeric results")
        + metric_bars(panel.bars)
        + baselines
        # 5
        + section_title("Do changes work together?")
        + interactions_panel(panel.interactions)
        # 6
        + section_title("Written analysis")
        + analysis
        # 7
        + section_title("Run metadata")
        + kv_table([(r.label, esc(r.value)) for r in panel.metadata])
        + provenance_link("run", panel.run_id or "", "Open this run")
    )


def _cell(value: int | None) -> str:
    return (
        '<span class="tl-absent">Not tested</span>'
        if value is None
        else f'<span class="tl-num">{value}</span>'
    )


def stats_table(spec: StatsTableSpec, rows: list[list[str]]) -> str:
    """One Statistics table, with its mandatory legend. `docs/05` §4.4, used by all ten tabs.

    §4.4 requires a statistical abbreviation to carry a ``title`` attribute **and** a visible
    legend above the table, because ``rho_A`` and ``AVE`` are not self-explanatory even to the
    intended reader (`docs/05` §6). Both are rendered here from one :class:`StatsTableSpec`, so a
    tab cannot ship a table that explains its columns in one place and not the other.

    The legend is not optional and an empty one raises: a missing legend is a specification breach
    rather than a cosmetic gap, and `HANDOFF.md` §2.3 is explicit that a degradation may cost
    styling, never content.
    """
    if not spec.legend:
        raise ValueError(
            f"{spec.title!r} has no legend; docs/05 §4.4 requires every statistics table to "
            "carry one above it"
        )

    meanings = dict(spec.legend)
    items = "".join(
        f'<div class="tl-legend-item"><dt title="{esc(meaning)}">{esc(abbr)}</dt>'
        f"<dd>{esc(meaning)}</dd></div>"
        for abbr, meaning in spec.legend
    )
    legend = f'<dl class="tl-legend" aria-label="What these columns mean">{items}</dl>'

    # A header that names an abbreviation carries its explanation as a tooltip too, so the legend
    # and the column agree without the reader having to look twice.
    headers = [
        f'<span title="{esc(meanings[h])}">{esc(h)}</span>' if h in meanings else esc(h)
        for h in spec.headers
    ]
    body = data_table(
        list(spec.headers),
        rows,
        caption=spec.caption,
        empty=spec.empty
        or empty_state("This stage has not been computed yet.", "Run the analysis."),
    )
    # data_table escapes its own headers; swap in the tooltip-carrying versions.
    for plain, rich in zip(spec.headers, headers, strict=True):
        body = body.replace(f'<th scope="col">{esc(plain)}</th>', f'<th scope="col">{rich}</th>', 1)

    return (
        '<section class="tl-stats-table">'
        + section_title(spec.title)
        + legend
        + body
        + "</section>"
    )


def provenance_strip(provenance: AnalysisProvenance) -> str:
    """The five facts `docs/07` §9 requires on **every** result view, plus the model fingerprint.

    "The paper must state which implementation produced the numbers", so this sits on every
    Statistics tab rather than once on the screen. `docs/06` §7.
    """
    rows = [
        ("Engine", esc(f"openpls-engine {provenance.engine_version}")),
        ("Respondents", esc(str(provenance.n_cases))),
        ("Bootstrap samples", esc(f"{provenance.bootstrap_samples:,}")),
        ("Seed", esc(str(provenance.seed))),
        (
            "Screening",
            esc(
                "Dropped attention failures, speeders and straight liners"
                if provenance.screening == "strict"
                else "Kept everyone"
            ),
        ),
        (
            "Answers",
            esc(
                {
                    "real": "Real drivers only",
                    "synthetic": "Synthetic only",
                    "both": "Real and synthetic",
                }[provenance.population]
            ),
        ),
        ("Model", esc(provenance.model_fingerprint or "unknown")),
    ]
    return kv_table(rows, caption="How these numbers were produced")


def unvalidated_banner(text: str) -> str:
    """`docs/07` §10's banner. Shown until the golden test has passed against this model."""
    return (
        '<div class="tl-banner tl-banner-warn" role="status">'
        f"<strong>UNVALIDATED</strong><div>{esc(text)}</div></div>"
    )
