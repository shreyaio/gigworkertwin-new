"""Statistics — `docs/06` §7.

Ten tabs over the **human survey rows**. `docs/07` §1: Statistics never reads the sweep — the
twins are an instrument for the counterfactual question, not respondents in the measurement model.

What this module may and may not do, all of it enforced elsewhere as well:

* **No arithmetic on a statistic.** Every number arrives from `services.statistics` already
  computed and already judged against its threshold; a handler here formats and nothing more
  (`docs/05` §8.4 rule 5).
* **No `db/`, `agents/`, `orchestrator/` or `analysis/` import.** The import-linter is the first
  CI step (`ARCHITECTURE.md` §4).
* **No repeating `gr.Timer` for an initial paint.** `components.load_once` queues for
  `demo.load` and is drained per route. The M10 Dial board shipped a `gr.Timer(0.2)` for its first
  paint, the timer never stopped, its output landed on top of the change handler's, and moving a
  dial silently did nothing while every test passed. Only two repeating timers are legitimate in
  this app and neither is here.
* **Every table carries a legend** (`docs/05` §4.4) and **every tab carries the five provenance
  facts** (`docs/07` §9), because the paper must state all five.

The `UNVALIDATED` banner is driven by a real comparison — whether the running model's fingerprint
is the one the golden expectations were pinned against — not by a hand-set flag (`docs/07` §10).
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from ..components import (
    app_header,
    empty_state,
    esc,
    global_nav,
    kv_table,
    load_once,
    num,
    provenance_strip,
    stats_table,
    unvalidated_banner,
)
from ..theme import page_classes

#: `docs/06` §7's tab order. **Mandatory** — content and ordering are not a design choice.
TAB_ORDER: tuple[str, ...] = (
    "Construct reliability and validity",
    "Discriminant validity",
    "Collinearity",
    "Outer model",
    "Path coefficients",
    "Indirect and total effects",
    "R², f², Q²",
    "PLSpredict",
    "Model fit",
    "Export",
)

#: The control strip's three choices. `docs/06` §7.
POPULATION_CHOICES = [
    ("Synthetic only", "synthetic"),
    ("Real drivers only", "real"),
    ("Real and synthetic", "both"),
]
SCREENING_CHOICES = [
    ("Drop attention failures, speeders, straight liners", "strict"),
    ("Keep everyone", "none"),
]

_STATUS_WORDS = {"ok": "ok", "check": "check", "na": "not applicable"}


def _status(value: str) -> str:
    """A status word, never a bare colour. `docs/05` §6: never colour alone."""
    from ..components import pill

    tone = {"ok": "green", "check": "amber", "na": "grey"}.get(value, "grey")
    return pill(_STATUS_WORDS.get(value, value), tone)


def _n(value: Any, places: int = 3, signed: bool = False) -> str:
    """A number, or ``Not tested``. Formatting only — the value was computed in the service."""
    return num(value, places=places, signed=signed)


def _rows(payload: dict | None, key: str = "rows") -> list[dict]:
    return list((payload or {}).get(key) or [])


# --------------------------------------------------------------------------- the ten tabs


def _reliability_html(payload: dict | None) -> str:
    """`docs/07` §8.1."""
    from twinlab.services.statistics import table_spec

    spec = table_spec(
        "reliability",
        "Construct reliability and validity",
        ("Construct", "Items", "Mean", "SD", "alpha", "rho_A", "rho_c", "AVE", "Status", "Note"),
        caption="Each statistic against its published threshold (docs/07 §8.1).",
    )
    rows = [
        [
            f"{esc(r['construct_code'])} — {esc(r['label'])}",
            esc(str(r["n_items"])),
            _n(r["mean"], 2),
            _n(r["sd"], 2),
            _n(r["cronbach_alpha"]),
            _n(r["rho_a"]),
            _n(r["rho_c"]),
            _n(r["ave"]),
            _status(r["status"]),
            esc(r.get("note") or ""),
        ]
        for r in _rows(payload)
    ]
    return stats_table(spec, rows)


def _discriminant_html(payload: dict | None) -> str:
    """`docs/07` §8.2. HTMT is primary; Fornell-Larcker is reported because reviewers expect it."""
    from twinlab.services.statistics import table_spec

    htmt_spec = table_spec(
        "discriminant",
        "Discriminant validity — HTMT",
        ("Construct A", "Construct B", "HTMT", "CI lower", "CI upper", "Status"),
        caption="The decisive test is an upper confidence bound below 1 (docs/07 §8.2).",
    )
    htmt_rows = [
        [
            esc(r["lv_a"]),
            esc(r["lv_b"]),
            _n(r["htmt"]),
            _n(r["ci_lower"]),
            _n(r["ci_upper"]),
            _status(r["status"]),
        ]
        for r in _rows(payload, "htmt")
    ]

    fl_spec = table_spec(
        "discriminant",
        "Discriminant validity — Fornell-Larcker",
        ("Construct", "sqrt(AVE)", "Largest correlation", "Status", "Note"),
        caption="sqrt(AVE) must exceed every correlation in the construct's row.",
    )
    fl_rows = [
        [
            esc(r["construct_code"]),
            _n(r["sqrt_ave"]),
            _n(r["max_abs_correlation"]),
            _status(r["status"]),
            esc(r.get("note") or ""),
        ]
        for r in _rows(payload, "fornell_larcker")
    ]
    return stats_table(htmt_spec, htmt_rows) + stats_table(fl_spec, fl_rows)


def _collinearity_html(payload: dict | None) -> str:
    """`docs/07` §8.3. Inner VIF between constructs, outer VIF between a construct's own items."""
    from twinlab.services.statistics import table_spec

    rows_all = _rows(payload)
    out = ""
    for scope, title, caption in (
        (
            "inner",
            "Collinearity — inner (between constructs)",
            "Above 5 makes a path coefficient uninterpretable (docs/07 §8.3).",
        ),
        (
            "outer",
            "Collinearity — outer (between a construct's items)",
            "Above 5 on a reflective construct signals redundant items.",
        ),
    ):
        spec = table_spec(
            "collinearity",
            title,
            ("Construct", "Predictor" if scope == "inner" else "Item", "VIF", "Status"),
            caption=caption,
        )
        rows = [
            [esc(r["target"]), esc(r["predictor"]), _n(r["vif"], 2), _status(r["status"])]
            for r in rows_all
            if r["scope"] == scope
        ]
        out += stats_table(spec, rows)
    return out


def _outer_model_html(payload: dict | None) -> str:
    """`docs/07` §8.4. A recommendation is a prompt; removal is a researcher's decision."""
    from twinlab.services.statistics import table_spec

    spec = table_spec(
        "outer_model",
        "Outer model — indicator loadings",
        (
            "Construct",
            "Item",
            "Loading",
            "t",
            "p",
            "CI lower",
            "CI upper",
            "Status",
            "What this suggests",
        ),
        caption=(
            "0.708 or above. Removing an item is a change to the instrument, recorded with the "
            "loading that justified it — an exclusion at analysis time, never a re-coding "
            "(docs/07 §8.4)."
        ),
    )
    rows = [
        [
            esc(r["construct_code"]),
            esc(r["item"]),
            _n(r["loading"]),
            _n(r["t_statistic"], 2),
            _n(r["p_value"]),
            _n(r["ci_lower"]),
            _n(r["ci_upper"]),
            _status(r["status"]),
            esc(r.get("recommendation") or ""),
        ]
        for r in _rows(payload)
    ]
    return stats_table(spec, rows)


def _paths_html(payload: dict | None) -> str:
    """`docs/07` §8.5. **The CI is the inferential claim**; the p-value is a convention."""
    from twinlab.services.statistics import table_spec

    spec = table_spec(
        "paths",
        "Path coefficients",
        (
            "Path",
            "Original sample",
            "Sample mean",
            "SD",
            "t",
            "p",
            "CI lower",
            "CI upper",
            "Status",
        ),
        caption="A bootstrap CI excluding zero is the claim; p is reported alongside.",
    )
    rows = [
        [
            f"{esc(r['source'])} &rarr; {esc(r['target'])}",
            _n(r["original_sample"], signed=True),
            _n(r["sample_mean"], signed=True),
            _n(r["sd"]),
            _n(r["t_statistic"], 2),
            _n(r["p_value"]),
            _n(r["ci_lower"], signed=True),
            _n(r["ci_upper"], signed=True),
            _status(r["status"]),
        ]
        for r in _rows(payload)
    ]
    return stats_table(spec, rows)


def _effects_html(payload: dict | None) -> str:
    """`docs/07` §8.6. Under full mediation the arm reaches every intention only indirectly."""
    from twinlab.services.statistics import table_spec

    spec = table_spec(
        "indirect_total",
        "Indirect and total effects",
        ("Effect", "Path", "Through", "Estimate", "CI lower", "CI upper", "Status"),
        caption="The model is a chain, so the indirect effects are where the theory lives.",
    )
    rows = [
        [
            esc(r["kind"].replace("_", " ")),
            f"{esc(r['source'])} &rarr; {esc(r['target'])}",
            esc(r.get("via") or ""),
            _n(r["estimate"], signed=True),
            _n(r["ci_lower"], signed=True),
            _n(r["ci_upper"], signed=True),
            _status(r["status"]),
        ]
        for r in _rows(payload)
    ]
    return stats_table(spec, rows)


def _explained_html(payload: dict | None) -> str:
    """`docs/07` §8.7. The band is a **label**: an R^2 is never coloured red for being small."""
    from twinlab.services.statistics import table_spec

    r2_spec = table_spec(
        "r2_f2_q2",
        "Explained variance and predictive relevance",
        ("Construct", "R²", "Adjusted R²", "Band", "Q²", "Q² status"),
        caption=(
            "The R² bands are conventions and are field-dependent; behavioural IS models "
            "routinely report lower and defend it (docs/07 §8.7)."
        ),
    )
    r2_rows = [
        [
            esc(r["construct_code"]),
            _n(r["r_squared"]),
            _n(r["r_squared_adj"]),
            esc(r["band"]),
            _n(r["q_squared"]),
            _status(r["q_status"]),
        ]
        for r in _rows(payload, "explained")
    ]

    f2_spec = table_spec(
        "r2_f2_q2",
        "Effect sizes (f²)",
        ("Path", "f²", "Effect size"),
        caption="0.02 small, 0.15 medium, 0.35 large.",
    )
    f2_rows = [
        [
            f"{esc(r['source'])} &rarr; {esc(r['target'])}",
            _n(r["f_squared"]),
            esc(r["effect_size"]),
        ]
        for r in _rows(payload, "f_squared")
    ]
    return stats_table(r2_spec, r2_rows) + stats_table(f2_spec, f2_rows)


def _plspredict_html(payload: dict | None) -> str:
    """`docs/07` §8.8. Out-of-sample errors against a linear-model benchmark."""
    from twinlab.services.statistics import table_spec

    summary = (payload or {}).get("summary") or {}
    verdict = ""
    if summary:
        verdict = kv_table(
            [
                ("Predictive power", esc(str(summary.get("verdict", "")).title())),
                ("Indicators assessed", esc(str(summary.get("indicators", 0)))),
                ("Beat the linear benchmark", esc(str(summary.get("beating_benchmark", 0)))),
                ("Q²predict above zero", esc(str(summary.get("q2_positive", 0)))),
            ],
            caption="How to read this: docs/07 §8.8.",
        )

    spec = table_spec(
        "plspredict",
        "PLSpredict",
        (
            "Construct",
            "Indicator",
            "Q²predict",
            "RMSE (PLS)",
            "RMSE (LM)",
            "MAE (PLS)",
            "MAE (LM)",
            "Status",
        ),
        caption="Assessed on endogenous indicators only — the model does not predict an "
        "exogenous construct.",
    )
    rows = [
        [
            esc(r["construct_code"]),
            esc(r["indicator"]),
            _n(r["q2_predict"]),
            _n(r["rmse_pls"]),
            _n(r["rmse_lm"]),
            _n(r["mae_pls"]),
            _n(r["mae_lm"]),
            _status(r["status"]),
        ]
        for r in _rows(payload)
    ]
    return verdict + stats_table(spec, rows)


def _fit_html(payload: dict | None) -> str:
    """`docs/07` §8.9. **Report fit, do not lead with it.**"""
    from twinlab.services.statistics import table_spec

    spec = table_spec(
        "model_fit",
        "Model fit",
        ("Statistic", "Value", "Threshold", "Status"),
        caption=(
            "PLS-SEM fit indices are contested and are not the basis on which this model should "
            "be judged; reliability, validity and predictive relevance are (docs/07 §8.9)."
        ),
    )
    rows = [
        [esc(r["statistic"]), _n(r["value"]), esc(r["threshold"]), _status(r["status"])]
        for r in _rows(payload)
    ]
    return stats_table(spec, rows)


#: stage -> renderer, in `docs/06` §7's tab order. Export is not a stage.
RENDERERS = {
    "reliability": _reliability_html,
    "discriminant": _discriminant_html,
    "collinearity": _collinearity_html,
    "outer_model": _outer_model_html,
    "paths": _paths_html,
    "indirect_total": _effects_html,
    "r2_f2_q2": _explained_html,
    "plspredict": _plspredict_html,
    "model_fit": _fit_html,
}


# --------------------------------------------------------------------------- the screen


def render_statistics(badge: str | None = None) -> None:
    """Build the Statistics page into the enclosing Blocks context. `docs/06` §7."""
    from twinlab.models.stats import STAGES

    with gr.Column(elem_classes=page_classes("/statistics")):
        app_header(
            "Statistics",
            "Reliability, correlations, the PLS-SEM path model and export",
            badge,
        )
        global_nav("/statistics")
        banner = gr.HTML()
        gr.Markdown(
            "Analysis over **human survey rows** — one row per respondent. This does not read "
            "the sweep: the twins answer the counterfactual question, and the measurement model "
            "is estimated on people."
        )

        # ---- control strip (docs/06 §7)
        with gr.Row():
            population = gr.Dropdown(
                choices=POPULATION_CHOICES,
                value="real",
                label="Which answers",
            )
            screening = gr.Dropdown(
                choices=SCREENING_CHOICES,
                value="strict",
                label="Screening",
            )
        with gr.Row():
            samples = gr.Number(
                value=5000,
                precision=0,
                label="Bootstrap samples",
                info="Default 5,000. Below 1,000 the intervals are unstable. Hard floor 30.",
            )
            pool_legacy = gr.Checkbox(
                value=False,
                label="Pool rows imported on the prototype's 1-7 scale",
                info="Excluded by default; they are not comparable with the current scales.",
            )
        with gr.Row():
            run_button = gr.Button("Run the analysis", variant="primary")
            export_button = gr.Button("Make an export sheet")

        gating = gr.HTML()
        provenance = gr.HTML()

        panels: dict[str, gr.components.Component] = {}
        with gr.Tabs(elem_classes=["tl-pilltabs"]):
            for title, stage in zip(TAB_ORDER, (*STAGES, "export"), strict=True):
                with gr.Tab(title):
                    panels[stage] = gr.HTML()
            # `export` is the tenth tab and has no stage payload; it gets its own controls.
            export_file = gr.File(label="Download", visible=False)

        # ---- handlers. No LLM call and no arithmetic on a statistic (CLAUDE.md rule 12).

        def _banner() -> str:
            from twinlab.services.statistics import (
                UNVALIDATED_BANNER,
                engine_is_validated,
            )

            return "" if engine_is_validated() else unvalidated_banner(UNVALIDATED_BANNER)

        def _gate(value: float | None) -> str:
            """`docs/06` §7's gating message. Blocked below 30, warned below 1,000."""
            from twinlab.services.statistics import plssem

            try:
                count = int(value or 0)
            except (TypeError, ValueError):
                count = 0
            if count < plssem.BOOTSTRAP_FLOOR:
                return (
                    '<div class="tl-banner tl-banner-warn" role="status"><strong>Blocked'
                    f"</strong><div>{esc(str(count))} bootstrap samples is below the floor of "
                    f"{plssem.BOOTSTRAP_FLOOR}. The analysis will not run. The default is "
                    f"{plssem.BOOTSTRAP_DEFAULT:,}.</div></div>"
                )
            warning = plssem.bootstrap_warning(count)
            if warning:
                return (
                    '<div class="tl-banner tl-banner-warn" role="status"><strong>Not '
                    f"reportable</strong><div>{esc(warning)}</div></div>"
                )
            return ""

        async def _load_latest() -> list:
            """The initial paint. `load_once`, never a repeating timer."""
            from twinlab.services.statistics import latest_analysis, stage_payload

            view = await latest_analysis()
            if view is None:
                blank = empty_state(
                    "No analysis has been run yet.",
                    "Choose the answers and screening above, then select Run the analysis.",
                )
                return ["", *[blank for _ in STAGES], _export_intro()]
            strip = provenance_strip(view.provenance)
            out = [strip]
            for stage in STAGES:
                payload = await stage_payload(view.analysis_id, stage)
                out.append(
                    RENDERERS[stage](payload)
                    if payload
                    else empty_state(
                        f"The {stage.replace('_', ' ')} stage has not been computed.",
                        "Run the analysis.",
                    )
                )
            out.append(_export_intro())
            return out

        async def _run(pop: str, screen_rule: str, count: float | None, pool: bool) -> list:
            from twinlab.services.statistics import (
                NoCasesError,
                create_analysis,
                run_analysis,
                screening_note,
                stage_payload,
            )
            from twinlab.stats.plssem import BootstrapFloorError

            try:
                analysis_id, matrix = await create_analysis(
                    population=pop,
                    screening=screen_rule,
                    bootstrap_samples=int(count or 0),
                    pool_legacy=bool(pool),
                )
            except (BootstrapFloorError, NoCasesError) as exc:
                blocked = (
                    '<div class="tl-banner tl-banner-warn" role="status"><strong>Not run'
                    f"</strong><div>{esc(str(exc))}</div></div>"
                )
                return [blocked, *[gr.update() for _ in STAGES], gr.update()]

            view = await run_analysis(analysis_id, matrix)
            strip = provenance_strip(view.provenance) + kv_table(
                [("Screening", esc(screening_note(matrix)))]
            )
            out = [strip]
            for stage in STAGES:
                payload = await stage_payload(analysis_id, stage)
                out.append(
                    RENDERERS[stage](payload)
                    if payload
                    else empty_state("This stage did not complete.", "Run the analysis again.")
                )
            out.append(_export_intro())
            return out

        async def _export(pop: str, pool: bool):
            """`docs/07` §11 — one row per respondent, **two** header rows."""
            import csv
            import tempfile

            from twinlab.services.statistics import build_export

            ids, scales, rows = await build_export(
                population=pop, screening="none", pool_legacy=bool(pool)
            )
            # I16: nothing durable. A tempfile is the handoff to the browser's download, which is
            # what gr.File requires; it is not evidence and is not acknowledged as stored.
            handle = tempfile.NamedTemporaryFile(
                "w", suffix=".csv", delete=False, newline="", encoding="utf-8"
            )
            with handle as fh:
                writer = csv.writer(fh)
                writer.writerow(ids)
                writer.writerow(scales)
                writer.writerows(rows)
            return gr.update(value=handle.name, visible=True), _export_intro(len(rows))

        targets = [provenance, *[panels[s] for s in STAGES], panels["export"]]
        run_button.click(
            _run, inputs=[population, screening, samples, pool_legacy], outputs=targets
        )
        export_button.click(
            _export, inputs=[population, pool_legacy], outputs=[export_file, panels["export"]]
        )
        samples.change(_gate, inputs=samples, outputs=gating)

        load_once(_banner, outputs=banner)
        load_once(_gate, inputs=samples, outputs=gating)
        load_once(_load_latest, outputs=targets)


def _export_intro(rows: int | None = None) -> str:
    """The Export tab's standing explanation. `docs/07` §11."""
    counted = f"<div><strong>{rows:,}</strong> row(s) in the last sheet.</div>" if rows else ""
    return (
        '<div class="tl-card">'
        "<strong>Export</strong>"
        "<div>One row per respondent, with <strong>two header rows</strong>: the column ids, "
        "then each column's scale and how many points it has.</div>"
        "<div>The prototype's export claimed every item was on a 1-7 scale. Three of the nine "
        "constructs are 1-5, so carrying the scale in the file makes that error impossible to "
        "repeat downstream.</div>"
        "<div>Construct means are computed in Python with reverse coding already applied, so a "
        "downstream tool cannot re-derive them differently.</div>"
        "<div>Rows imported on the prototype's 1-7 scale are excluded unless you pool them "
        "above.</div>"
        f"{counted}"
        "</div>"
    )
