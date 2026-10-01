"""Twin Studio — `docs/06` §5.

A place to interrogate one twin in the researcher's own words. **The quarantine moved on
2026-10-01** (`ARCHITECTURE_UPDATE.md` §1.1): a *dialled version* asked here is now recorded as a
result with `origin='studio'` and `twins_n=1`, and reaches Results and the index. `docs/01` §6.9's
blanket version no longer holds, and this page must not claim it does — see `services/studio.py`
for where the wall now runs.

This page never states any of that as a promise it keeps by itself. It calls `services.studio`,
whose `run_studio` has no code path to `runs` and whose `file_studio_run` is the only thing that
does — the guarantees live next to the writes, not in a handler.

Four things on this screen are content, not decoration:

* a **custom free-text change** is *sandbox — not a study result* and is never filed, because it
  bypasses the lookup (I1) and the Checker (I3) and is therefore not a Fairwork treatment;
* a **dialled version that is filed** says so, and says **n = 1**, because one twin is not the
  frozen panel the controls come from;
* a **hand-built twin** is `source='manual'`, can never enter a panel, and has no driver to be
  compared against;
* a **twin the quality gate dropped** can be asked but is never filed (`docs/03` §9.1).

**Layout note.** The twin picker used to be a bare `gr.Dropdown` beside a read-only `gr.Textbox`
called *Twin in use*, and both rendered as unlabelled boxes with spinner arrows and text escaping
the field. There is now one picker, the selection is the picker's own value, and the persona the
twin is given sits under it in a scrolling panel — which is also the prototype's arrangement.
"""

from __future__ import annotations

import gradio as gr

from ..components import (
    app_header,
    budget_summary,
    data_table,
    dial_legend,
    empty_state,
    error_state,
    esc,
    global_nav,
    load_once,
    num,
    scenario_text_block,
    section_title,
    status_dot,
)
from ..theme import page_classes

_ASK_PLACEHOLDER = (
    "Would you change how you work?\nWhat would still worry you?\n"
    "Would you tell other drivers about it?"
)

_CUSTOM_PLACEHOLDER = (
    "For example: Imagine Uber pays a fixed amount for every cancelled trip after you have "
    "driven more than 2 km."
)


def _said_html(result) -> str:
    """*What the twin said* — `docs/06` §5's table, plus the answers to the researcher's own
    questions.

    §5 specifies the construct table and the expandable scenario text; it does not say where the
    free-text answers go, and a screen that takes up to five questions and shows none of the
    replies is not a screen. They are rendered above the table, closest to where they were asked
    (`docs/DECISIONS.md`, 2026-09-30).
    """
    parts: list[str] = []
    if result.replies:
        parts.append(section_title("In the twin's own words"))
        parts.append(
            "".join(
                f'<div class="tl-card"><strong>{esc(q)}</strong>'
                f"<div>{esc(a)}</div></div>"
                for q, a in result.replies.items()
            )
        )
    if result.blocked:
        parts.append(error_state("The survey questions were not recorded.", "contract",
                                 esc(result.blocked)))
    parts.append(section_title("What it measures"))
    parts.append(
        data_table(
            ["What it measures", "Now (1–7)", "Uber today", "Change", "The twin's reason"],
            [
                [
                    esc(row.label),
                    num(row.now, signed=False),
                    num(row.baseline, signed=False),
                    num(row.change),
                    esc(row.reason),
                ]
                for row in result.rows
            ],
            empty=empty_state(
                "No answers recorded for this run.",
                result.no_battery_note
                or "Tick 'Also ask the 37 survey questions' to record a comparable answer set.",
            ),
        )
    )
    return "".join(parts)


def _mode_notes() -> str:
    """The standing caveats for the three modes (`docs/06` §5)."""
    from twinlab.services.studio import SANDBOX_LABEL

    return (
        '<div class="tl-card">'
        "<strong>What the Studio is</strong>"
        "<div>A place to ask one twin questions in your own words.</div>"
        # `ARCHITECTURE_UPDATE.md` §1.1 reversed the blanket quarantine for the dialled-version
        # path, so this card no longer says studio runs "never enter the results" — which is now
        # false and was the most load-bearing sentence on the screen. It says instead exactly which
        # of the two paths does what, and what `n = 1` costs.
        "<div><strong>If you set the dials</strong>, the answer is recorded as a result for that "
        "version and appears in Results — but over <strong>one twin</strong>, not the frozen "
        "panel, so it is marked <em>Studio</em> there. A later <em>Ask the twins</em> on the Dial "
        "board supersedes it.</div>"
        "<div><strong>If you write your own change</strong>, nothing is recorded as a result. It "
        "bypasses the version lookup and the Checker, so it is not a Fairwork treatment, it is "
        f"labelled <em>{esc(SANDBOX_LABEL)}</em>, and it is not comparable to any version.</div>"
        "<div>A twin you build by hand is stored as <code>manual</code> and can never be drawn "
        "into a panel. It has no driver, so it has no &ldquo;Uber today&rdquo; column to compare "
        "against and nothing it says is scored.</div>"
        "</div>"
    )


def _twin_card() -> tuple[gr.components.Component, ...]:
    """Card 1 — *Make or choose a twin*, three modes, one active at a time (`docs/06` §5)."""
    from twinlab.services.studio import MANUAL_SLIDERS, TWIN_MODES

    gr.HTML(section_title("1. Make or choose a twin"))
    # Choices are `(label, value)`; the value is the mode key, so `_switch` compares keys.
    mode = gr.Radio(
        choices=[(label, key) for key, label in TWIN_MODES],
        value=TWIN_MODES[0][0],
        label="How do you want a twin?",
        elem_classes=["tl-toggle"],
    )

    with gr.Group(elem_classes=["tl-field"]) as existing_box:
        # One picker, and its value IS the selection. The label carries the identity line
        # because a twin id is opaque by design (`CLAUDE.md` rule 8).
        existing = gr.Dropdown(
            choices=[], label="Twin", value=None, filterable=True,
            elem_classes=["tl-picker"],
        )
        existing_note = gr.Markdown("")
        gr.Markdown(
            "Every twin is listed, **including the ones the quality gate dropped** — inspecting "
            "them is what this screen is for. A dropped twin can be asked anything here, but its "
            "answer is never recorded as a result: a twin the gate dropped is dropped from the "
            "panel and from every cell (`docs/03` §9.1)."
        )

    with gr.Group(visible=False, elem_classes=["tl-field"]) as survey_box:
        # Real, consented respondents only. Synthetic rows must not appear (`docs/06` §5).
        survey = gr.Dropdown(
            choices=[], label="Survey answer", value=None, filterable=True,
            elem_classes=["tl-picker"],
        )
        gr.Markdown(
            "Real respondents who agreed to a twin (statement 7) only. Synthetic surveys are "
            "not offered here; make a synthetic twin in the Generator."
        )
        make_from_survey = gr.Button("Create this twin", variant="primary")

    with gr.Group(visible=False, elem_classes=["tl-field"]) as manual_box:
        with gr.Row():
            m_city = gr.Textbox(label="City")
            m_service = gr.Textbox(label="Service")
        with gr.Row():
            m_age = gr.Number(label="Age", precision=0)
            m_gender = gr.Textbox(label="Gender")
        with gr.Row():
            m_tenure = gr.Number(label="Months on Uber", precision=0)
            m_hours = gr.Number(label="Hours a week", precision=0)
        m_note = gr.Textbox(label="Note", lines=2)
        sliders = [
            gr.Slider(
                1, 7, value=4, step=1, label=f"{label} (1–7)",
                elem_classes=["tl-slider-row"],
            )
            for _, label in MANUAL_SLIDERS
        ]
        make_manual = gr.Button("Create this twin", variant="primary")

    def _switch(selected: str):
        return (
            gr.update(visible=selected == "existing"),
            gr.update(visible=selected == "survey"),
            gr.update(visible=selected == "manual"),
        )

    mode.change(_switch, inputs=mode, outputs=[existing_box, survey_box, manual_box])

    return (
        mode,
        existing,
        existing_note,
        survey,
        make_from_survey,
        make_manual,
        m_city,
        m_service,
        m_age,
        m_gender,
        m_tenure,
        m_hours,
        m_note,
        *sliders,
    )


def render_studio(badge: str | None = None) -> None:
    """Build Twin Studio into the enclosing Blocks context, in `docs/06` §5's order."""
    from twinlab.models.reference import LEVER_NAMES
    from twinlab.services.dials import LEVER_ORDER
    from twinlab.services.studio import MANUAL_SLIDERS, MAX_QUESTIONS

    with gr.Column(elem_classes=page_classes("/studio")):
        app_header("Twin Studio", "Ask one twin a what-if question in your own words", badge)
        global_nav("/studio")
        gr.HTML(_mode_notes())

        with gr.Row(equal_height=False):
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["tl-panel"]):
                    controls = _twin_card()
                    (
                        mode,
                        existing,
                        existing_note,
                        survey,
                        make_from_survey,
                        make_manual,
                        m_city,
                        m_service,
                        m_age,
                        m_gender,
                        m_tenure,
                        m_hours,
                        m_note,
                    ) = controls[:13]
                    sliders = list(controls[13:])
                    told_button = gr.Button(
                        "Show what the twin is told", elem_classes=["tl-btn-quiet"]
                    )
                    persona = gr.HTML("")

            with gr.Column(scale=1):
                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("2. Ask a what-if question"))
                    gr.Markdown(
                        "Choose a version of Uber, or write your own change, then ask the twin."
                    )
                    gr.HTML(dial_legend())
                    dials = {
                        lever: gr.Radio(
                            choices=[("0 today", 0), ("1 some", 1), ("2 more", 2)],
                            value=0,
                            label=LEVER_NAMES[lever],
                            elem_classes=["tl-dial-row"],
                        )
                        for lever in LEVER_ORDER
                    }
                    code_display = gr.HTML("")
                    custom = gr.Textbox(
                        label="Or write your own change (leave empty to use the dials)",
                        lines=3,
                        placeholder=_CUSTOM_PLACEHOLDER,
                        info="Free text. Not a Fairwork treatment — the result is a sandbox "
                             "result.",
                    )
                    questions = gr.Textbox(
                        label=(
                            "Your questions for the twin "
                            f"(one per line, up to {MAX_QUESTIONS})"
                        ),
                        lines=4,
                        placeholder=_ASK_PLACEHOLDER,
                    )
                    battery = gr.Checkbox(
                        label="Also ask the 37 survey questions and show the change", value=False
                    )
                    ask = gr.Button("Ask the twin", variant="primary")
                    # `ARCHITECTURE_UPDATE.md` §4.2. Before this, a version with no stored
                    # Checker-passed variant was a dead end: the Studio refused (correctly — I3 has
                    # no sandbox exemption) and the only way to produce one was to run the whole
                    # frozen panel from the Dial board to answer a one-twin question. Rendering was
                    # never forbidden, only expensive.
                    render_state = gr.HTML("")
                    render_budget = gr.HTML("")
                    render_button = gr.Button(
                        "Render this version now",
                        variant="secondary",
                        visible=False,
                    )
                    render_note = gr.Markdown("")

        gr.HTML(section_title("What the twin said"))
        sandbox_flag = gr.HTML("")
        meta = gr.Markdown("")
        said = gr.HTML(
            empty_state(
                "Nothing asked yet.",
                "Choose a twin, set the dials or write a change, then press Ask the twin.",
            )
        )
        with gr.Accordion("The change the twin was told about", open=False):
            told = gr.HTML("")

        dial_inputs = [dials[lever] for lever in LEVER_ORDER]

        def _on_dial(*values: int):
            """Pure: the same frozen lookup the Dial board uses (I1). No network call."""
            from twinlab.services.dials import dial_board

            board = dial_board(dict(zip(LEVER_ORDER, values, strict=True)))
            return (
                '<div class="tl-version-line">Version code: '
                f'<strong class="tl-version-code">{esc(board.version_code)}</strong> '
                "<span>(00000 means Uber today)</span>"
                f"<div class=\"tl-caption\">{esc(board.fairwork_text)}</div></div>"
            )

        async def _render_state(custom_text: str, *values: int):
            """Is this version renderable, rendered, or already verified? **One read, no writes.**

            `docs/06` §9 and `ARCHITECTURE_UPDATE.md` §4.2 point 4: the budget is shown *before* the
            button, and the button never renders blind. A custom free-text change has no version to
            render, so the whole group disappears rather than offering something meaningless.
            """
            from twinlab.services.dials import code_from_dials
            from twinlab.services.studio import variant_status

            if (custom_text or "").strip():
                return "", "", gr.update(visible=False), ""
            code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
            if code == "00000":
                # `00000` is Uber today: there is nothing to render and nothing to ask.
                return "", "", gr.update(visible=False), ""
            state = await variant_status(code)
            if state["passed"]:
                return (
                    status_dot("complete", f"{code} is rendered and passed the Checker"),
                    "",
                    gr.update(visible=False),
                    "",
                )
            if state["rendering"]:
                return (
                    status_dot("running", f"{code} is being rendered"),
                    "",
                    gr.update(visible=False),
                    "Watch it in **Twin Lab → Agents → What the agents said**.",
                )
            if state["exists"]:
                # Rendered and failed. I3: it must not reach a twin, and `render_and_check` will
                # return the stored failure rather than re-rolling, which is `docs/03` §5's halt.
                return (
                    status_dot("failed", f"{code} did not pass the Checker"),
                    "",
                    gr.update(visible=False),
                    f"It must not be shown to a twin (I3). {esc(state['notes'][:300])}",
                )
            return (
                status_dot("pending", f"{code} has never been rendered"),
                budget_summary(state["budget"]),
                gr.update(visible=True),
                "",
            )

        async def _start_render(custom_text: str, *values: int):
            """Enqueue the render and return. **No model call in this handler** (rule 12)."""
            from twinlab.services.dials import code_from_dials
            from twinlab.services.studio import StudioError, start_render

            if (custom_text or "").strip():
                return (
                    "A change you wrote yourself is not a version, so there is nothing to render."
                )
            code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
            try:
                session_id = await start_render(code)
            except StudioError as exc:
                return f"**Not started.** {exc}"
            except Exception as exc:  # noqa: BLE001 — name it rather than a dead button
                return f"**Not started.** {type(exc).__name__}: {exc}"
            return (
                f"Rendering `{code}` as session `{session_id[:8]}`. It runs in the background and "
                "continues if you change tab — watch it in **Twin Lab → Agents**. Press *Ask the "
                "twin* once it has passed the Checker."
            )

        render_inputs = [custom, *dial_inputs]
        render_outputs = [render_state, render_budget, render_button, render_note]
        render_button.click(_start_render, inputs=render_inputs, outputs=render_note)

        for radio in dial_inputs:
            radio.change(_on_dial, inputs=dial_inputs, outputs=code_display)
            radio.change(_render_state, inputs=render_inputs, outputs=render_outputs)
        custom.change(_render_state, inputs=render_inputs, outputs=render_outputs)

        async def _load_selectors():
            from twinlab.services.studio import studio_selectors

            picked = await studio_selectors()
            return (
                gr.update(choices=picked["twin_labels"]),
                gr.update(choices=picked["survey_labels"]),
                picked["line"],
            )

        async def _create_from_survey(label: str | None):
            """Create, then re-read the pickers so the new twin is selectable and selected."""
            from twinlab.services.studio import create_twin_from_survey, twin_id_of

            if not label:
                return gr.update(), gr.update(), "Pick a survey answer first."
            twin = await create_twin_from_survey(twin_id_of(label))
            twins, surveys, line = await _load_selectors()
            match = next(
                (
                    choice for choice in (twins.get("choices") or [])
                    if twin_id_of(choice) == twin.twin_id
                ),
                twin.twin_id,
            )
            return gr.update(choices=twins.get("choices"), value=match), surveys, line

        make_from_survey.click(
            _create_from_survey, inputs=survey, outputs=[existing, survey, existing_note]
        )

        async def _create_manual(city, service, age, gender, tenure, hours, note, *values):
            from twinlab.services.studio import create_manual_twin, twin_id_of

            twin = await create_manual_twin(
                city=city or "",
                service=service or "",
                age=int(age) if age else None,
                gender=gender or None,
                tenure_months=int(tenure) if tenure else None,
                hours_per_week=int(hours) if hours else None,
                note=note or "",
                sliders={code: int(v) for (code, _), v in zip(MANUAL_SLIDERS, values, strict=True)},
            )
            twins, _surveys, line = await _load_selectors()
            match = next(
                (
                    choice for choice in (twins.get("choices") or [])
                    if twin_id_of(choice) == twin.twin_id
                ),
                twin.twin_id,
            )
            return gr.update(choices=twins.get("choices"), value=match), line

        make_manual.click(
            _create_manual,
            inputs=[m_city, m_service, m_age, m_gender, m_tenure, m_hours, m_note, *sliders],
            outputs=[existing, existing_note],
        )

        async def _show_persona(label: str | None) -> str:
            """*Show what the twin is told* — the stored passage, never a rebuilt one."""
            from twinlab.services.studio import studio_persona, twin_id_of

            twin_id = twin_id_of(label)
            if not twin_id:
                return empty_state(
                    "No twin chosen.", "Pick or create a twin in the card above."
                )
            try:
                passage = await studio_persona(twin_id)
            except Exception as exc:  # noqa: BLE001
                from ..components import error_state

                return error_state(
                    "Could not read the persona.", type(exc).__name__, str(exc)[:200]
                )
            return (
                '<div class="tl-persona-panel">'
                '<div class="tl-persona-head">What the twin is told about itself</div>'
                f'<pre class="tl-persona tl-scroll">{esc(passage)}</pre></div>'
            )

        told_button.click(_show_persona, inputs=existing, outputs=persona)

        async def _show_told(*values: int):
            from twinlab.services.dials import code_from_dials
            from twinlab.services.lab import scenario_paragraphs

            code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
            return scenario_text_block(await scenario_paragraphs(code))

        async def _ask(label, custom_text, question_text, include_battery, *values):
            """`docs/06` §5's *Ask the twin*. Quarantined — see `services.studio`.

            The whole action is `services.studio.ask_studio`; this renders what it returns
            (`docs/05` §8.4 rule 1). No metric is computed here.
            """
            from twinlab.services.dials import code_from_dials
            from twinlab.services.studio import StudioBlocked, ask_studio, twin_id_of

            twin_id = twin_id_of(label)
            if not twin_id:
                return (
                    "",
                    "",
                    empty_state(
                        "No twin chosen.", "Pick or create a twin in the card on the left."
                    ),
                    "",
                )

            code = code_from_dials(dict(zip(LEVER_ORDER, values, strict=True)))
            custom = (custom_text or "").strip()
            asked = [q.strip() for q in (question_text or "").splitlines() if q.strip()]
            try:
                result = await ask_studio(
                    twin_id=twin_id,
                    version_code=None if custom else code,
                    custom_change=custom,
                    questions=asked,
                    include_battery=bool(include_battery),
                )
            except StudioBlocked as exc:
                return (
                    "",
                    "",
                    error_state("Nothing was asked.", "Checker", str(exc)[:400]),
                    "",
                )
            except Exception as exc:  # noqa: BLE001 — name the failure rather than go blank
                return (
                    "",
                    "",
                    error_state(
                        "The twin could not be asked.", type(exc).__name__, str(exc)[:400]
                    ),
                    "",
                )

            # Two mutually exclusive strips, and which one appears is the whole of
            # `ARCHITECTURE_UPDATE.md` §1.1 made visible on the screen that produced the number.
            if result.sandbox:
                flag = (
                    f'<div class="tl-warn-strip" role="alert">{esc(result.label)}. '
                    "A change you wrote yourself bypasses the version lookup and the Checker, so "
                    "this is a conversation, not a measurement. It is never filed as a result."
                    "</div>"
                )
            elif result.run_id:
                flag = (
                    '<div class="tl-note-strip" role="note">'
                    f"Filed as a result for <strong>{esc(code)}</strong> — run "
                    f"<code>{esc(result.run_id[:8])}</code>, <strong>n = {result.twins_n}</strong>"
                    + (
                        f", index {result.index_value:.3f}"
                        if result.index_value is not None
                        else ""
                    )
                    + ". It appears in Results with origin <em>Studio</em>. One twin is not the "
                    "frozen panel, and a later Dial board run for this version supersedes it."
                    "</div>"
                )
            elif result.not_filed:
                flag = (
                    '<div class="tl-note-strip" role="note">Not filed as a result. '
                    f"{esc(result.not_filed)}</div>"
                )
            else:
                flag = ""
            shown = "your own change" if result.sandbox else code
            line = (
                f"**Twin** {result.twin_id} · **model** {result.model} · **version** {shown}"
            )
            return flag, line, _said_html(result), scenario_text_block(result.scenario_text)

        told_button.click(_show_told, inputs=dial_inputs, outputs=told)
        ask.click(
            _ask,
            inputs=[existing, custom, questions, battery, *dial_inputs],
            outputs=[sandbox_flag, meta, said, told],
        )

        gr.HTML(section_title("Earlier answers"))
        past = gr.HTML("")

        async def _history():
            from twinlab.services.studio import studio_history

            rows = await studio_history()
            return data_table(
                ["When", "Twin", "Version", "Questions", "Kind", "Current?"],
                [
                    [
                        esc(str(r.get("created_at"))[:19]),
                        esc(r.get("twin_id")),
                        esc(r.get("version_code") or "—"),
                        str(len(r.get("questions") or [])),
                        status_dot(
                            "pending" if r.get("custom_change") else "complete",
                            "sandbox" if r.get("custom_change") else "version",
                        ),
                        # `ARCHITECTURE_UPDATE.md` §4.4: a second ask for the same
                        # (twin, version, wording) appends and moves the pointer, and the earlier
                        # row survives. The column is how a researcher can see both rows and tell
                        # which one is the current answer — without it the table reads as a
                        # duplicate rather than as a history.
                        status_dot("complete", "current")
                        if r.get("is_latest_for_twin_version")
                        else status_dot("pending", "superseded"),
                    ]
                    for r in rows
                ],
                empty=empty_state("Nothing yet.", "Ask a twin something to see it here."),
            )

        load_once(_load_selectors, outputs=[existing, survey, existing_note])
        load_once(_on_dial, inputs=dial_inputs, outputs=code_display)
        load_once(_render_state, inputs=render_inputs, outputs=render_outputs)
        load_once(_history, outputs=past)


__all__ = ["render_studio"]
