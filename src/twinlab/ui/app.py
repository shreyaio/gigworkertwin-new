"""The Gradio root. `ARCHITECTURE.md` §8.2 rule 1.

``build_ui()`` returns a plain ``gr.Blocks``. Both entrypoints call it and neither adds
behaviour: ``app.py`` launches it, ``app_docker.py`` mounts it. Upgrading to PRO + Docker must
cost a commit, not a port, and that stays true only while all of the UI lives here.

The eight routes and their order are mandatory (`docs/06` §0).
"""

from __future__ import annotations

import inspect

import gradio as gr

from . import pages
from .components import drain_pending_loads
from .theme import APP_TITLE, FONT_HEAD, PARTICIPANT_ROUTES, ROUTES, TWINLAB_CSS

# Gradio 5 takes `css` on the Blocks constructor; Gradio 6 moved it off. Detect rather than
# pin behaviour to one, so the same file works on the pinned 5.x and on a local 6.x.
# See docs/DECISIONS.md -> M0.
_BLOCKS_PARAMS = inspect.signature(gr.Blocks.__init__).parameters
_ACCEPTS_CSS_KWARG = "css" in _BLOCKS_PARAMS
# Roboto is loaded through `head` rather than an `@import` inside the stylesheet: Gradio
# appends our CSS to a sheet that already has rules, and an `@import` that is not the first
# rule is dropped by every browser. See docs/DECISIONS.md -> D-UI-01.
_ACCEPTS_HEAD_KWARG = "head" in _BLOCKS_PARAMS

_RENDERERS = {
    "/": pages.render_main_menu,
    "/survey": pages.render_driver_survey,
    "/lab": pages.render_lab,
    "/generator": pages.render_generator,
    "/studio": pages.render_studio,
    "/agents": pages.render_agent_studio,
    "/statistics": pages.render_statistics,
    "/research": pages.render_research_model,
    # Driver-facing. A real route, deliberately not in ROUTES — see PARTICIPANT_ROUTES.
    "/take": pages.render_survey_take,
}


def _model_badge() -> str:
    """Header badge text. Resolved once per build, from the service layer only.

    ``ui/`` may import ``services/`` and ``models/`` and nothing lower (`ARCHITECTURE.md` §4).
    """
    from twinlab.services.config import model_badge

    return model_badge()


def _startup_check() -> None:
    """Boot-time gates, through the service layer only.

    Loads the ten reference files and, against a live database, verifies that the project was
    seeded from this same reference data — a mismatch refuses to boot (`docs/11` → M1).
    """
    from twinlab.services.config import startup_check

    startup_check()


def build_ui() -> gr.Blocks:
    """Build the whole application as one ``gr.Blocks`` with eight routes.

    Implements portability rule 1 (`ARCHITECTURE.md` §8.2): the object returned holds every
    screen, and the two entrypoints are thin wrappers over it.
    """
    _startup_check()
    badge = _model_badge()
    kwargs = {"title": APP_TITLE, "fill_width": True}
    if _ACCEPTS_CSS_KWARG:
        kwargs["css"] = TWINLAB_CSS
    if _ACCEPTS_HEAD_KWARG:
        kwargs["head"] = FONT_HEAD

    with gr.Blocks(**kwargs) as demo:
        if not _ACCEPTS_CSS_KWARG:
            gr.HTML(f"<style>{TWINLAB_CSS}</style>")
        if not _ACCEPTS_HEAD_KWARG:
            gr.HTML(FONT_HEAD)
        # Hidden, not absent. `demo.route()` is what makes the seven URLs real; the Navbar
        # only draws a strip, and `global_nav` draws the prototype's strip instead — with the
        # accent underline and the `< Main menu` back link that Gradio's cannot carry. Two
        # navbars on one page is the one thing the prototype definitely does not have.
        gr.Navbar(visible=False, main_page_name=ROUTES[0][0])
        _RENDERERS["/"](badge)
        # Each page's first paint attaches to `load` in its own context. A repeating timer would
        # keep recomputing and land on top of whatever the researcher has since changed, which is
        # how the Dial board first came to ignore a dial. See `components.load_once`.
        drain_pending_loads(demo)

    # ROUTES[0] is the root Blocks above; the remaining seven become real URLs. `route()`
    # refuses to run inside a Blocks context, so the loop sits outside the `with`.
    #
    # PARTICIPANT_ROUTES are built the same way and are just as real, but they are kept out of
    # ROUTES so that `global_nav` — which draws its strip from ROUTES — cannot put a link to the
    # researcher's application in front of a driver filling in the questionnaire.
    for label, path in (*ROUTES[1:], *PARTICIPANT_ROUTES):
        with demo.route(label, path):
            if not _ACCEPTS_CSS_KWARG:
                gr.HTML(f"<style>{TWINLAB_CSS}</style>")
            if not _ACCEPTS_HEAD_KWARG:
                gr.HTML(FONT_HEAD)
            _RENDERERS[path](badge)
            drain_pending_loads(demo)

    return demo
