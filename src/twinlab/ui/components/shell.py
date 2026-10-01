"""Shell components. `docs/05_DESIGN_SYSTEM.md` §4.1.

Every component is a function returning Gradio components. Nothing here is defined twice
anywhere else in the app (§4).
"""

from __future__ import annotations

import html

import gradio as gr

from ..theme import APP_SUBTITLE, APP_TITLE, ROUTES


def app_header(
    title: str = APP_TITLE,
    subtitle: str = APP_SUBTITLE,
    badge: str | None = None,
    build_line: str = "",
) -> gr.HTML:
    """Title, subtitle, the model badge and the build line (`docs/06` §0).

    The badge reads ``Mock model`` or ``Live: <model name>``. It is resolved by the caller from
    the service layer, never read from the environment here — ``ui/`` holds no logic (§8.4).

    A live model gets a red badge rather than the accent-tinted one. In the prototype the badge
    is the only thing on screen that says whether a press costs money, so the two states must
    not look alike.
    """
    tone = " tl-badge-live" if badge and not badge.lower().startswith("mock") else ""
    badge_html = f'<span class="tl-badge{tone}">{html.escape(badge)}</span>' if badge else ""
    build_html = f'<span class="tl-build">{html.escape(build_line)}</span>' if build_line else ""
    return gr.HTML(
        f'<div class="tl-header">'
        f"<h1>{html.escape(title)}</h1>"
        f"{badge_html}"
        f"{build_html}"
        f'<span class="tl-sub">{html.escape(subtitle)}</span>'
        f"</div>",
        elem_classes=["tl-shell-header"],
    )


def global_nav(current: str) -> gr.HTML:
    """The prototype's text navbar: `‹ Main menu` then the seven apps, active one underlined.

    `gr.Navbar` is still mounted by :func:`twinlab.ui.app.build_ui` — it is what makes the
    routes real. This renders the *visible* strip, because Gradio's own navbar cannot carry the
    accent underline and the leading back-link that the prototype has on every screen
    (`docs/05` §8.2: degrade the styling, never the content).

    ``current`` is the route path. An unknown path raises rather than rendering a strip with
    nothing marked active.
    """
    paths = [path for _, path in ROUTES]
    if current not in paths:
        raise ValueError(f"global_nav: {current!r} is not one of {paths} (docs/06 §0)")
    links = ['<a class="tl-nav-back" href="/">&lsaquo; Main menu</a>']
    for label, path in ROUTES[1:]:
        on = " tl-nav-on" if path == current else ""
        links.append(f'<a class="{on.strip()}" href="{path}">{html.escape(label)}</a>')
    return gr.HTML(f'<nav class="tl-nav">{"".join(links)}</nav>')


def section(title: str, subtitle: str = "") -> gr.HTML:
    """A section heading: 3px accent bar, near-black title, optional grey one-liner.

    The prototype opens every region this way and the bar takes the app's accent, so this is
    the component that makes Twin Lab read green and Twin Studio orange (`docs/05` §4.1).
    """
    sub = f'<div class="tl-section-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    return gr.HTML(
        f'<div class="tl-section"><div class="tl-section-title">'
        f"{html.escape(title)}</div>{sub}</div>"
    )


def section_card(title: str, body_html: str = "") -> gr.HTML:
    """White surface, thin border, title. `docs/05` §4.1."""
    return gr.HTML(
        f'<div class="tl-card"><strong>{html.escape(title)}</strong><div>{body_html}</div></div>'
    )


def sub_nav(labels: tuple[str, ...] | list[str]) -> gr.Tabs:
    """A `gr.Tabs` within a section. `docs/05` §4.1.

    Used as ``with sub_nav(LAB_TABS) as tabs:``; the caller then opens one `gr.Tab` per label, in
    order. **The order is mandatory** (`docs/06` §0), so it is passed in from one list that both
    the nav and the tests read, rather than being written out twice.
    """
    if not labels:
        raise ValueError("sub_nav needs its labels: the tab order is mandatory (docs/06 §0)")
    return gr.Tabs(elem_classes=["tl-subnav"])


#: Initial paints queued by pages and attached to the `Blocks` by :func:`build_ui`.
#:
#: A page function builds into the *enclosing* context and never sees the `Blocks`, so it cannot
#: call ``demo.load`` itself. Queuing here and draining once is what keeps every first paint on
#: the load event.
_PENDING_LOADS: list[tuple] = []


def load_js(script: str) -> None:
    """Run one browser-side script on page load.

    Used for exactly one thing: bridging a click inside a `gr.HTML` region back into a Gradio
    component. `gr.HTML` emits no events, so without this the 243-grid would be decoration — and
    `docs/05` §8.3 is explicit that a grid without click handling must never ship, because the
    click is how a researcher reaches the scenario text.
    """
    _PENDING_LOADS.append((None, None, None, script))


def load_once(fn, *, inputs=None, outputs=None) -> None:
    """Paint a region **once**, on page load. `docs/05` §5 ("Loading").

    Deliberately not a `gr.Timer`. A repeating timer re-runs the handler forever and its result
    lands on top of whatever the researcher has since changed — which is precisely how the first
    build of the Dial board came to ignore a dial: the initial paint kept overwriting the change
    handler's output, and at 0.2 s across seven tabs it also produced ~28 requests a second.

    The work still happens off the render path (`docs/05` §8.4 rule 2): `load` fires after the
    page is served, never inside the function that builds it.
    """
    _PENDING_LOADS.append((fn, inputs, outputs, None))


def drain_pending_loads(demo: gr.Blocks) -> int:
    """Attach every queued initial paint to ``demo.load`` and clear the queue.

    Called once per route by :func:`twinlab.ui.app.build_ui`, inside that route's context —
    ``demo.load`` refuses to be called outside a `Blocks` context. Returns how many were
    attached, so a test can assert that nothing was queued and then silently dropped.
    """
    count = 0
    while _PENDING_LOADS:
        fn, inputs, outputs, script = _PENDING_LOADS.pop(0)
        if script is not None:
            demo.load(None, None, None, js=script)
        else:
            demo.load(fn, inputs=inputs, outputs=outputs)
        count += 1
    return count


def help_accordion(topics: tuple[tuple[str, str], ...]) -> None:
    """The collapsible help area retained from the prototype. `docs/06` §1.4."""
    with gr.Accordion("Help", open=False):
        for title, body in topics:
            with gr.Accordion(title, open=False):
                gr.Markdown(body)


def placeholder(text: str) -> gr.HTML:
    """A named, styled 'not built yet' region.

    M0 ships the eight routes empty. A placeholder states which milestone fills it, so an empty
    screen is never mistaken for a screen whose data failed to load.
    """
    return gr.HTML(f'<div class="tl-placeholder">{html.escape(text)}</div>')
