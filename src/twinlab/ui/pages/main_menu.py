"""Main menu — `docs/06` §1.

The landing page and the application map, grouped by research stage. **Content and ordering are
mandatory** (`docs/06`, preamble): the seven workflow groups, the seven direct-open cards, the
live counts, the quick start and the help accordion, in that order.

The ordering itself lives in `services/menu.py`, not here, so it is testable without constructing
a Gradio app and so this module stays a formatter (`docs/05` §8.4 rule 1).

**Google Sheet is removed** (`docs/06` §0): no card, no link, no user-facing text naming a sheet.
"""

from __future__ import annotations

import gradio as gr

from twinlab.models.view import CardGroup, LinkCard, StatusRow

from ..components import (
    app_header,
    esc,
    global_nav,
    help_accordion,
    kv_table,
    load_once,
    loading_state,
    section_title,
    status_dot,
)
from ..theme import page_classes


def _card_html(card: LinkCard) -> str:
    """Title · one-line description · destination. All three are mandatory (`docs/06` §1.1).

    The **whole card** is the link. It used to wrap only the destination in an `<a>`, which left
    the title and the description inert and reduced a 260px tile to a 60px hit target that also
    read as body text rather than as something to press. The route stays visible as a caption
    because §1.1 requires it, but it is no longer the control.

    The link goes to the route, not to the tab within it: Gradio's `demo.route()` gives each
    page one URL and no per-tab address, so a card naming a tab lands on the page and the
    caption says which tab to open. Inventing a URL that does not resolve would be worse.
    """
    where = card.route if not card.tab else f"{card.route} → {card.tab}"
    return (
        f'<a class="tl-card tl-link-card" href="{esc(card.route)}">'
        f"<strong>{esc(card.title)}</strong>"
        f'<div class="tl-link-desc">{esc(card.description)}</div>'
        f'<div class="tl-link-dest">{esc(where)}</div></a>'
    )


def _group_html(group: CardGroup) -> str:
    cards = "".join(_card_html(c) for c in group.cards)
    return (
        f'<div class="tl-card"><strong>{esc(group.title)}</strong>'
        f'<div class="tl-card-grid">{cards}</div></div>'
    )


def _stand_html(rows: list[StatusRow]) -> str:
    """`docs/06` §1.3's two-column table. "Versions tested" reads *of 242* — the control is not
    a version under test."""
    pairs = []
    for row in rows:
        value = esc(row.value)
        if row.state is not None:
            value = status_dot(row.state, row.value)
        pairs.append((row.label, value))
    # No caption: the section title above already names this table, and a caption would repeat it.
    return kv_table(pairs)


async def _load_stand() -> str:
    """Live Supabase counts. Errors surface as an error state, never as a plausible zero."""
    from twinlab.services.status import where_things_stand

    try:
        return _stand_html(await where_things_stand())
    except Exception as exc:  # noqa: BLE001 — the screen must say why, not show zeros.
        from ..components import error_state

        return error_state("Could not read the live counts.", type(exc).__name__, "no event id")


def render_main_menu(badge: str | None = None) -> None:
    """Build the Main menu into the enclosing Blocks context, in `docs/06` §1's order."""
    from twinlab.services.menu import DIRECT_CARDS, HELP_TOPICS, WORKFLOW_GROUPS
    from twinlab.services.status import QUICK_START

    with gr.Column(elem_classes=page_classes("/")):
        app_header("Main menu", "The application map, grouped by research stage", badge)
        global_nav("/")

        # 1.1 — seven groups, in order.
        gr.HTML(section_title("What do you want to do?"))
        gr.HTML("".join(_group_html(g) for g in WORKFLOW_GROUPS))

        # 1.2 — one card per route except Main menu.
        gr.HTML(section_title("Open an app directly"))
        gr.HTML(
            '<div class="tl-card-grid">' + "".join(_card_html(c) for c in DIRECT_CARDS) + "</div>"
        )

        # 1.3 — live counts. Loaded after render so a slow database never blocks the page.
        gr.HTML(section_title("Where things stand"))
        stand = gr.HTML(value=loading_state("the live counts"))

        # 1.4 — quick start, then help.
        gr.HTML(section_title("Quick start"))
        gr.HTML(
            '<ol class="tl-quickstart">'
            + "".join(f"<li>{esc(step)}</li>" for step in QUICK_START)
            + "</ol>"
        )
        help_accordion(HELP_TOPICS)

        # The counts are the only network work on this page and it happens off the render path,
        # never inside it (`docs/05` §8.4 rule 2).
        #
        # Two triggers, and both are needed. `load_once` paints them immediately — without it the
        # table sits empty until the first tick, which at a 10 s interval reads as a broken page.
        # The timer then keeps them live, which `docs/06` §1.3 asks for ("live Supabase counts",
        # counters flashing on change). This is the one place a repeating timer is correct,
        # because nothing here is a control the researcher can be editing.
        load_once(_load_stand, outputs=stand)
        gr.Timer(10.0, active=True).tick(_load_stand, outputs=stand)
