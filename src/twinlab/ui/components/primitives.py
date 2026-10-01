"""Primitives. `docs/05_DESIGN_SYSTEM.md` §4.2 and §5.

Every one returns an HTML string rather than a Gradio component, so the same primitive can be
composed into a card, a table cell or a log row without three variants of it existing. Nothing
here is defined twice anywhere in the app (§4).

**Never colour alone** (§6). `status_dot`, `pill` and every state helper take their text as a
required argument, so there is no way to call one that emits a coloured mark with no label. The
M10 acceptance test asserts this over the rendered HTML of every screen.
"""

from __future__ import annotations

import html

#: `docs/05` §4.2. Green complete, amber running, red failed, grey pending.
DOT_COLOURS: dict[str, str] = {
    "complete": "var(--tl-ok)",
    "running": "var(--tl-warn)",
    "failed": "var(--tl-bad)",
    "pending": "var(--tl-grey-500)",
}

#: Verdict pills. `INCONCLUSIVE` is grey and is mandatory whenever a test ran on zero twins (I15).
VERDICT_TONE: dict[str, str] = {
    "PASS": "green",
    "FAIL": "red",
    "CHECK": "amber",
    "INCONCLUSIVE": "grey",
}


def esc(text: object) -> str:
    return html.escape(str(text))


def pill(text: str, tone: str = "grey") -> str:
    """A labelled pill. ``text`` is required: a pill with no text is a colour, not a state."""
    if not text:
        raise ValueError("a pill must carry text; colour alone is not a state (docs/05 §6)")
    return f'<span class="tl-pill tl-pill-{esc(tone)}">{esc(text)}</span>'


def status_dot(state: str, label: str) -> str:
    """An 8px dot **beside a text label**. `docs/05` §4.2.

    The label is not optional. A dot on its own is unreadable to a third of the audience and
    unreadable to everyone in a screen reader.
    """
    if not label:
        raise ValueError(
            f"status_dot({state!r}) needs a label; a dot alone encodes by colour only (docs/05 §6)"
        )
    colour = DOT_COLOURS.get(state, DOT_COLOURS["pending"])
    return (
        f'<span class="tl-dot-wrap"><span class="tl-dot" style="background:{colour}" '
        f'aria-hidden="true"></span><span class="tl-dot-label">{esc(label)}</span></span>'
    )


def badge_cached() -> str:
    """The amber `cached` badge on a Dial board result (`docs/06` §3.2)."""
    return pill("cached", "amber")


def verdict_pill(verdict: str) -> str:
    """`PASS` / `FAIL` / `CHECK` / `INCONCLUSIVE`, always with the word visible."""
    return pill(verdict, VERDICT_TONE.get(verdict, "grey"))


def empty_state(why: str, action: str) -> str:
    """`docs/05` §5: say why it is empty **and** the single action that fixes it."""
    return (
        f'<div class="tl-empty"><strong>{esc(why)}</strong>'
        f'<div class="tl-empty-action">{esc(action)}</div></div>'
    )


def error_state(summary: str, category: str, event_id: object) -> str:
    """`docs/05` §5: "it failed" is always followed by "here is exactly where".

    ``event_id`` is required (`docs/04` §9). An error with no event id cannot be traced, and an
    untraceable failure in a research instrument is indistinguishable from a wrong answer.
    """
    return (
        f'<div class="tl-error"><strong>{esc(summary)}</strong>'
        f'<div class="tl-error-meta">{esc(category)} · event {esc(event_id)}</div></div>'
    )


def loading_state(what: str) -> str:
    """A spinner plus **what** is loading, never a bare spinner."""
    return f'<div class="tl-loading"><span class="tl-spinner"></span>{esc(what)}</div>'


def section_title(text: str) -> str:
    return f'<div class="tl-section-title">{esc(text)}</div>'


def kv_table(rows: list[tuple[str, str]], *, caption: str = "") -> str:
    """A two-column label/value table with tabular numerals."""
    body = "".join(
        f'<tr><th scope="row">{esc(k)}</th><td class="tl-num">{v}</td></tr>' for k, v in rows
    )
    head = f"<caption>{esc(caption)}</caption>" if caption else ""
    return f'<table class="tl-kv">{head}<tbody>{body}</tbody></table>'


def data_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    caption: str = "",
    empty: str = "",
    row_keys: list[str] | None = None,
    row_attr: str = "data-key",
) -> str:
    """A scrollable table with sticky headers. `docs/05` §6.

    Cells are inserted as trusted HTML so a pill or a dot can live in one; callers escape their
    own text with :func:`esc`. Everything this module builds is escaped at the point it is made.

    ``row_keys`` marks each row with ``row_attr`` and makes it look and behave clickable. `gr.HTML`
    emits no events, so a page bridges the click into a Gradio component with :func:`load_js` —
    the same constraint `docs/05` §8.3 solves this way for the 243-grid, and the same reason: a
    table a researcher has to re-type a key out of is a table that is read wrong.
    """
    if not rows:
        return empty or empty_state("Nothing here yet.", "Run the step that fills it.")
    if row_keys is not None and len(row_keys) != len(rows):
        raise ValueError(
            f"data_table got {len(row_keys)} row_keys for {len(rows)} rows; a row whose key "
            "belongs to a different row is worse than no key at all"
        )
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    opens = [
        f'<tr class="tl-row-pick" tabindex="0" role="button" '
        f'{esc(row_attr)}="{esc(key)}">'
        for key in row_keys
    ] if row_keys is not None else ["<tr>"] * len(rows)
    body = "".join(
        opens[i] + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for i, row in enumerate(rows)
    )
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return (
        f'<div class="tl-table-wrap tl-scroll"><table class="tl-data">{cap}'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def num(value: float | None, *, places: int = 2, signed: bool = True) -> str:
    """A number, or ``Not tested``. **Never a fabricated zero.**

    ``None`` means no completed run. Rendering it as ``0.00`` would make an absent measurement
    indistinguishable from a measured null (I17).
    """
    if value is None:
        return '<span class="tl-absent">Not tested</span>'
    return f"{value:+.{places}f}" if signed else f"{value:.{places}f}"
