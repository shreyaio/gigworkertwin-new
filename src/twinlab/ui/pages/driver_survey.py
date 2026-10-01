"""Driver survey — `docs/06` §2.

The page shows what the instrument is, the live intake status, the four-arm assignment balance by
`city|service`, and the form link.

**It does not host the survey, and that is a research constraint rather than a shortcut.** §2 and
`docs/04` §8 put intake in a Supabase Edge Function *outside* the Space, so a sleeping free Space
cannot drop a submission; this page reports on that endpoint and never participates in it. Nothing
here accepts an answer, and nothing here calls the endpoint — a Space that probed intake on every
render would be exactly the participant §2 says it must not be.

**Synthetic rows are excluded from every fieldwork number and counted separately** (`docs/08`
§6.2). A real intake count that quietly included a synthetic batch would read as fieldwork that
has not happened.
"""

from __future__ import annotations

import gradio as gr

from ..components import (
    app_header,
    data_table,
    empty_state,
    esc,
    global_nav,
    kv_table,
    load_once,
    section_title,
    status_dot,
)
from ..theme import page_classes


def _instrument_html(status: dict) -> str:
    """What the instrument is (`docs/06` §2), counted off the register and `form_map.yaml`."""
    from twinlab.services.surveys import HOLDOUT_WARNING

    languages = ", ".join(status["languages"])
    return (
        '<div class="tl-card">'
        f"<strong>{status['parts']} parts · {len(status['languages'])} languages · "
        f"{status['questions']} questions</strong>"
        f"<div class=\"tl-link-desc\">{esc(languages)}. "
        f"{status['items']} of the {status['questions']} questions are scored items on the "
        "frozen register; the rest are screeners, consent statements, demographics and "
        "open text.</div>"
        "</div>"
        # I6 is the instrument's most load-bearing property, so it is stated on the screen
        # rather than left in the documentation (`docs/06` §2).
        f'<div class="tl-note tl-note-warn">{esc(HOLDOUT_WARNING)}</div>'
    )


def _intake_html(status: dict) -> str:
    """Live intake status and the form link (`docs/06` §2).

    When intake is not configured the screen shows §2's placeholder **in its own words**, in the
    application's own navigation and style — not a blank panel and not a dead link.
    """
    from twinlab.services.surveys import INTAKE_PLACEHOLDER

    if not status["intake_configured"]:
        return (
            f'<div class="tl-note tl-note-info">{esc(INTAKE_PLACEHOLDER)}</div>'
            '<div class="tl-caption">Set <code>SURVEY_INTAKE_URL</code>, '
            "<code>INTAKE_HMAC_SECRET</code> and <code>SURVEY_FORM_URL</code> to turn this "
            "panel on. Intake runs in the Supabase Edge Function, never in this Space "
            "(docs/04 §8).</div>"
        )
    # `kv_table` escapes its keys and trusts its values as markup, so every value built from
    # configuration or from a stored row is escaped here.
    rows = [
        ("Endpoint", f"{esc(status['intake_url'])} — signed"),
        ("Last submission received", esc(status["last_submission"] or "None yet")),
        ("Received today", f"{status['received_today']:,}"),
        ("Real submissions", f"{status['real_total']:,}"),
        ("Synthetic (never fieldwork)", f"{status['synthetic_total']:,}"),
    ]
    link = (
        f'<div class="tl-card"><strong>The form drivers fill in</strong>'
        f'<div><a href="{esc(status["form_url"])}" target="_blank" rel="noopener">'
        f'{esc(status["form_url"])}</a></div></div>'
        if status["form_url"]
        else '<div class="tl-note tl-note-info">No form link configured '
             "(<code>SURVEY_FORM_URL</code>).</div>"
    )
    return kv_table(rows) + link


def _balance_html(status: dict) -> str:
    """The four-arm assignment balance by `city|service`. `docs/01` §5.2.

    Balance is **within** stratum, not overall, which is what makes H2 validation comparable
    across strata — so the table is one row per stratum and never a single global total.
    """
    arms = status["arms"]
    rows = []
    for (city, service), by_arm in sorted(status["arm_balance"].items()):
        total = sum(by_arm.values())
        counts = [by_arm.get(arm, 0) for arm in arms]
        # An empty arm inside a stratum that has respondents is the imbalance worth seeing, so
        # it is a zero in its own column rather than an absent column.
        spread = max(counts) - min(counts) if total else 0
        rows.append(
            [
                esc(city),
                esc(service),
                *[str(c) for c in counts],
                str(total),
                status_dot(
                    "complete" if spread <= 1 else "pending",
                    "balanced" if spread <= 1 else f"off by {spread}",
                ),
            ]
        )
    return data_table(
        ["City", "Service", *arms, "Total", "Balance"],
        rows,
        caption=(
            "Arms are balanced within each city|service stratum, never overall "
            "(docs/01 §5.2). Synthetic rows are not counted here."
        ),
        empty=empty_state(
            "No real submissions yet.",
            "The table fills as the Edge Function receives them. Synthetic batches never "
            "appear here.",
        ),
    )


def render_driver_survey(badge: str | None = None) -> None:
    """Build the Driver survey page into the enclosing Blocks context, in `docs/06` §2's order."""
    with gr.Column(elem_classes=page_classes("/survey")):
        app_header("Driver survey", "The instrument, and what intake has received", badge)
        global_nav("/survey")

        gr.HTML(section_title("What the instrument is"))
        instrument = gr.HTML("")

        gr.HTML(section_title("Intake"))
        intake = gr.HTML("")

        gr.HTML(section_title("Four-arm balance by city and service"))
        balance = gr.HTML("")

        async def _load() -> tuple[str, str, str]:
            """One read for the whole page. Off the render path, never inside it."""
            from twinlab.services.surveys import survey_status

            try:
                status = await survey_status()
            except Exception as exc:  # noqa: BLE001 — say why rather than paint three zeros.
                from ..components import error_state

                message = error_state(
                    "Could not read intake status.", type(exc).__name__, str(exc)[:200]
                )
                return message, message, message
            return (
                _instrument_html(status),
                _intake_html(status),
                _balance_html(status),
            )

        load_once(_load, outputs=[instrument, intake, balance])


__all__ = ["render_driver_survey"]
