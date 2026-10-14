"""The questionnaire a driver fills in. `/take`, `docs/06` §2.1.

**This is the only page in the application whose reader is not the researcher.** One driver, on a
phone, once. That shapes every choice here and several of them are deliberately unlike the rest of
the UI:

* **No navigation strip.** `/take` is absent from :data:`~twinlab.ui.theme.ROUTES`, so the link a
  driver is sent opens the questionnaire and offers no way into the Dial board or the Twin Lab.
* **Every stop is built up front and hidden**, rather than re-rendered on each step. Gradio has no
  server-side page swap; a `gr.Column` whose `visible` is toggled keeps the driver's earlier
  answers alive in their components, so going Back and forward again cannot lose a stop's work.
* **Answers are gathered from the components on every navigation**, into one
  :class:`~twinlab.models.survey.SurveyProgress` keyed by `form_map.yaml` key. The page therefore
  accumulates the exact object `survey.payload.build_payload` needs; there is no second shape.
* **Nothing is written until the driver presses send.** The cover sheet says a driver may stop at
  any time and that no partial response is retained, so a half-finished questionnaire must leave
  no row — which means no autosave, not even a draft table.

**No LLM call is anywhere in this path** (`CLAUDE.md` rule 12 could not be violated here even in
principle): the persona is pure Python, so pressing send does storage, two inserts and a
deterministic string build.

The one thing the page validates is the two gates the instrument itself imposes — the Part 1
screeners and the Part 2 consents must be answered to go on. Everything else may be skipped,
because the cover sheet promises exactly that. A skipped battery item makes the submission
`partial`, which is recorded honestly and simply does not become a twin (`services.hosted_survey`).
"""

from __future__ import annotations

import logging

import gradio as gr

from twinlab.models.survey import Question, Stop

from ..components import esc, load_once
from ..theme import page_classes

log = logging.getLogger(__name__)

#: The two stops a driver may not pass without answering. Everything else is skippable by design.
GATED_STOPS = (2, 3)

#: The option on Part 2's final question that ends the survey. Matched exactly, never by prefix:
#: "No, I do not agree" and "Yes, I agree" share no prefix, but a future reword might.
DECLINE = "No, I do not agree. End the survey."


class StaleSession(RuntimeError):
    """The browser is answering a version of the questionnaire this process no longer serves.

    A Gradio client caches the component tree it loaded with and replays it on every click. A tab
    left open across a restart that changed the instrument — 112 questions became 146 when the
    why-probe layer landed — therefore posts a value list that no longer lines up with the
    questions, and may render the stale tree on top of the new one.

    Raised rather than worked around. The values arrive positionally and nothing identifies which
    question each belongs to, so a shorter list cannot be realigned; pairing the first *n* would
    file real answers under the wrong questions. The page says to reload, and nothing is stored.
    """


# --------------------------------------------------------------------------- static markup


def _rail(index: int, total: int, kicker: str) -> str:
    """The kicker line, the dot rail and the accent underline. The reference screens show all three.

    ``Stop 5 of 9`` is stated in words as well as drawn, because a rail of dots alone does not
    tell a driver how much is left — and "how much is left" is the question that decides whether
    they finish.
    """
    parts: list[str] = []
    for n in range(1, total + 1):
        if n > 1:
            parts.append(f'<span class="seg{" done" if n <= index else ""}"></span>')
        parts.append(f'<span class="dot{" done" if n <= index else ""}"></span>')
    pct = int(round(100 * index / total))
    return (
        f'<div class="tl-sv-kicker"><span>{esc(kicker)}</span>'
        f"<span>Stop {index} of {total}</span></div>"
        f'<div class="tl-sv-rail">{"".join(parts)}</div>'
        f'<div class="tl-sv-underline"><i style="width:{pct}%"></i></div>'
    )


def _stop_heading(stop: Stop) -> str:
    out = ""
    if stop.part:
        out += f'<div class="tl-sv-part">{esc(stop.part)}</div>'
    if stop.title:
        out += f'<h1 class="tl-sv-title">{esc(stop.title)}</h1>'
    if stop.intro:
        out += f'<div class="tl-sv-intro">{esc(stop.intro)}</div>'
    if stop.callout_points:
        points = "".join(f"<li>{esc(p)}</li>" for p in stop.callout_points)
        out += (
            f'<div class="tl-sv-callout"><strong>{esc(stop.callout_title)}</strong>'
            f"<ul>{points}</ul></div>"
        )
    if stop.body:
        # The cover sheet's first body line is its heading; the rest are paragraphs. Keeping the
        # distinction means the participant information sheet reads as a document, not a wall.
        body = "".join(
            f"<h3>{esc(line)}</h3>" if i == 0 else f"<p>{esc(line)}</p>"
            for i, line in enumerate(stop.body)
        )
        out += f'<div class="tl-sv-body">{body}</div>'
    return out


def _story_html(arm: str | None) -> str:
    """The Part 15/16 stimulus for this driver's arm, drawn as a quoted block.

    Rendered per session rather than baked into the page: `docs/01` §5 is a four-arm
    between-subjects design, so which story a driver reads is drawn for them. Until the arm exists
    the slot is empty — it cannot be filled before the city and service that stratify the draw are
    answered, and both come three stops earlier than the story.
    """
    from twinlab.survey.instrument import arm_story

    text = arm_story(arm)
    return f'<div class="tl-sv-story">{esc(text)}</div>' if arm else ""


def _block_heading(heading: str, intro: str, scale_note: str) -> str:
    out = '<div class="tl-sv-block">'
    if heading:
        out += f"<h2>{esc(heading)}</h2>"
    if intro:
        # A Part 17 stimulus arrives as "**Pay:** ..." lines. Each becomes its own paragraph with
        # the lever name in bold, which is how the instrument prints it.
        for line in intro.split("\n"):
            if line.startswith("**") and ":**" in line:
                name, _, text = line.partition(":**")
                out += (
                    f'<p class="lever"><strong>{esc(name.strip("*"))}:</strong>'
                    f"{esc(text)}</p>"
                )
            else:
                out += f'<p class="lever">{esc(line)}</p>'
    if scale_note:
        out += f'<div class="note">{esc(scale_note)}</div>'
    return out + "</div>"


# --------------------------------------------------------------------------- controls


def _control(question: Question) -> gr.components.Component:
    """One Gradio control for one question, drawn inside its own card.

    The stem is a `gr.HTML` rather than the control's own label: Gradio renders a long label as
    one cramped line above the input, and several of these stems are two lines of prose. The
    anchors are drawn under the row for the same reason — the reference screens put
    "1 = Strongly disagree" and "7 = Strongly agree" at the ends of the row, which no Gradio
    label can do.
    """
    # A consent statement is its own tick-box label, so wrapping it in a card would draw two
    # nested boxes around one sentence.
    classes = ["tl-q-bare"] if question.kind == "consent" else ["tl-q"]
    # A why-probe belongs to the rating above it, visually and in the data. It is drawn as a
    # continuation of that card rather than a card of its own.
    if question.is_why:
        classes = ["tl-q", "tl-q-why"]

    with gr.Group(elem_classes=classes):
        if question.kind != "consent":
            stem = esc(question.shown)
            if question.unit:
                stem += f' <span class="tl-q-help">({esc(question.unit)})</span>'
            css = "tl-q-stem tl-q-why-stem" if question.is_why else "tl-q-stem"
            gr.HTML(f'<div class="{css}">{stem}</div>')

        control = _input_for(question)

        if question.kind == "likert":
            gr.HTML(
                f'<div class="tl-q-anchors"><span>1 = {esc(question.low_anchor)}</span>'
                f"<span>{question.points} = {esc(question.high_anchor)}</span></div>"
            )
        if question.help_text:
            gr.HTML(f'<div class="tl-q-help">{esc(question.help_text)}</div>')
    return control


def _input_for(question: Question) -> gr.components.Component:
    """The control alone. ``value=None`` everywhere: nothing is pre-selected, ever.

    A pre-selected midpoint would be indistinguishable in the data from a driver who chose it,
    and the whole instrument turns on telling a real answer from an absent one
    (`CLAUDE.md`, "never coerce a bad answer into a good one").
    """
    common = {"show_label": False, "container": False, "value": None}
    kind = question.kind

    if kind == "likert":
        assert question.points is not None  # guaranteed by the Question validator
        return gr.Radio(
            choices=[(str(n), n) for n in range(1, question.points + 1)],
            elem_classes=["tl-likert"],
            **common,
        )
    if kind == "yes_no":
        return gr.Radio(choices=["Yes", "No"], elem_classes=["tl-yesno"], **common)
    if kind == "consent":
        # The statement is the checkbox's own label here, because a tick-box and the sentence it
        # agrees to must be one target: a driver tapping the text expects it to tick.
        return gr.Checkbox(
            label=question.title, value=False, container=False, elem_classes=["tl-consent"]
        )
    if kind == "choice":
        return gr.Radio(
            choices=list(question.options), elem_classes=["tl-choice"], **common
        )
    if kind in ("integer", "decimal"):
        # **A text box, not `gr.Number`.** Gradio renders a `Number` whose value is ``None`` as a
        # box containing `0`, and a driver who skipped "how many people depend on your earnings"
        # would submit a zero that is a real and very different answer. A text box renders empty,
        # and `survey.payload` parses it — which is also what the Google Form sent, so the two
        # channels stay byte-comparable through `build_rows`.
        return gr.Textbox(
            placeholder=question.unit or "Number", elem_classes=["tl-numbox"], **common
        )
    if kind == "short_text":
        return gr.Textbox(placeholder=question.placeholder or "Your answer", **common)
    if kind == "long_text":
        return gr.Textbox(
            lines=2 if question.is_why else 3,
            placeholder=(
                question.placeholder
                or ("Optional" if question.is_why else "Your answer in your own words")
            ),
            **common,
        )
    raise ValueError(f"no control for question kind {kind!r}")  # pragma: no cover


# --------------------------------------------------------------------------- the page


def render_survey_take(badge: str | None = None) -> None:
    """Build the driver-facing questionnaire. ``badge`` is accepted and ignored.

    Every route renderer takes the model badge so `ui/app.py` can call them uniformly. This page
    does not show it: the provider a researcher happens to be pointed at is not a driver's
    business, and the reference screens carry no such strip.
    """
    from twinlab.survey.instrument import hosted_instrument

    instrument = hosted_instrument()
    total = len(instrument.stops)

    with gr.Column(elem_classes=[*page_classes("/take"), "tl-survey"]):
        progress = gr.State(None)
        header = gr.HTML(_rail(1, total, instrument.stops[0].kicker))
        error = gr.HTML("")

        columns: list[gr.Column] = []
        controls: list[gr.components.Component] = []
        keys: list[str] = []
        story_slots: list[gr.HTML] = []

        for stop in instrument.stops:
            with gr.Column(visible=stop.index == 1) as column:
                gr.HTML(_stop_heading(stop))
                for block in stop.blocks:
                    if block.heading or block.intro or block.scale_note:
                        gr.HTML(_block_heading(block.heading, block.intro, block.scale_note))
                    if block.arm_story:
                        # Filled per session once the arm is drawn. Built empty rather than with
                        # one arm's text, so a page that somehow never assigns an arm shows no
                        # story at all instead of silently showing everyone the same one.
                        story_slots.append(gr.HTML(""))
                    for question in block.questions:
                        controls.append(_control(question))
                        keys.append(question.key)
            columns.append(column)

        # Two terminal screens that are not stops: the rail still reads "9 of 9" behind them,
        # because they are what happens after the questionnaire rather than part of it.
        with gr.Column(visible=False) as done_column:
            done_html = gr.HTML("")
        with gr.Column(visible=False) as ended_column:
            gr.HTML(
                '<div class="tl-sv-done"><h1 class="tl-sv-title">Thank you</h1>'
                "<p>You chose not to take part, so nothing has been recorded. "
                "You can close this page.</p></div>"
            )

        with gr.Row(elem_classes=["tl-sv-footer"]):
            back = gr.Button("Back", elem_classes=["tl-sv-back"], visible=False)
            forward = gr.Button("Start the survey", elem_classes=["tl-sv-next"])

        _wire(
            instrument=instrument,
            progress=progress,
            header=header,
            error=error,
            columns=columns,
            done_column=done_column,
            ended_column=ended_column,
            done_html=done_html,
            back=back,
            forward=forward,
            controls=controls,
            keys=keys,
            story_slots=story_slots,
        )


def _wire(*, instrument, progress, header, error, columns, done_column, ended_column,
          done_html, back, forward, controls, keys, story_slots) -> None:
    """Attach the two navigation handlers. Split out of the renderer for length only."""
    total = len(instrument.stops)
    outputs = [
        progress, header, error, done_html, back, forward, done_column, ended_column,
        *columns, *story_slots,
    ]

    def _frame(
        state, *, index: int, message: str = "", done: str = "", ended: bool = False
    ) -> list:
        """One screen's worth of component updates. The single place visibility is decided."""
        showing_terminal = bool(done) or ended
        stop = instrument.stops[min(index, total) - 1]
        return [
            state,
            _rail(index, total, stop.kicker),
            f'<div class="tl-sv-error">{esc(message)}</div>' if message else "",
            done,
            gr.update(visible=1 < index <= total and not showing_terminal),
            gr.update(
                value=(
                    "Start the survey" if index == 1
                    else "Send my answers" if index == total
                    else "Continue"
                ),
                visible=not showing_terminal,
            ),
            gr.update(visible=bool(done)),
            gr.update(visible=ended),
            *[
                gr.update(visible=(s.index == index) and not showing_terminal)
                for s in instrument.stops
            ],
            # The stimulus, repainted on every frame from whatever arm the state carries. One
            # source for both slots, so Part 15 and Part 16 cannot drift apart and show a driver
            # two different worlds.
            *[
                gr.update(value=_story_html(getattr(state, "arm", None)))
                for _ in story_slots
            ],
        ]

    def _gather(state, values: tuple) -> object:
        """Fold the components' current values into the driver's progress object.

        Every control is read on every navigation, not only the current stop's. A driver who goes
        Back two stops and edits an answer has changed it; reading only the visible stop would
        keep the earlier value and silently discard the correction.

        **A count mismatch refuses rather than pairing what it can.** The values arrive
        positionally, so if the browser sends a different number than this page registered, the
        alignment between question and answer is unknown — pairing the first *n* would file real
        answers under the wrong questions, which is a fabricated record and far worse than an
        error. It happens when a tab is left open across a restart that changed the instrument:
        the client replays the component tree it loaded with, and that tree no longer exists.
        """
        from twinlab.survey.payload import new_progress

        if len(values) != len(keys):
            raise StaleSession(
                f"this page sent {len(values)} answers for {len(keys)} questions. The "
                "questionnaire was updated after this page was opened, so the answers can no "
                "longer be matched to their questions reliably."
            )
        state = state or new_progress()
        for key, value in zip(keys, values, strict=True):
            state.answers[key] = value
        return state

    def _missing(state, index: int) -> list[str]:
        """Unanswered required questions on this stop, as their own stems."""
        if index not in GATED_STOPS:
            return []
        return [
            q.title for q in instrument.stops[index - 1].questions
            if q.required and state.answers.get(q.key) in (None, "", False, [], ())
        ]

    async def _navigate(state, values, *, forward: bool):
        """Every handler failure becomes a message **on the page**, never a Gradio toast.

        Gradio renders an uncaught handler exception as a bare red "Error" chip with no text. A
        researcher can read a terminal; a driver on a phone sees a word they can do nothing with,
        and the likely cause — a tab left open across a restart — has an obvious remedy nobody
        would guess. So the wrapper catches everything and says what to do.
        """
        try:
            return await (_forward(state, values) if forward else _step_back(state, values))
        except StaleSession as exc:
            log.warning("stale session on %s: %s", getattr(state, "response_id", "?"), exc)
            return _frame(
                state,
                index=getattr(state, "stop_index", 1),
                message=(
                    "This page is out of date with the questionnaire and your answers can no "
                    "longer be matched to their questions. Please reload the page and start "
                    "again. Nothing has been saved."
                ),
            )
        except Exception as exc:  # noqa: BLE001 — named on the page, logged in full.
            log.exception("hosted survey navigation failed")
            return _frame(
                state,
                index=getattr(state, "stop_index", 1),
                message=(
                    f"Something went wrong ({type(exc).__name__}). Nothing has been saved. "
                    "Please reload the page; if it keeps happening, tell the researcher."
                ),
            )

    #: The stop that collects city and service. The arm is stratified on them (`docs/01` §5.2),
    #: so it cannot be drawn before this stop is left — and must be drawn before the stimulus.
    demographics_stop = next(
        s.index for s in instrument.stops
        if any(q.target == "field:city" for q in s.questions)
    )
    city_key = next(q.key for q in instrument.questions if q.target == "field:city")
    service_key = next(q.key for q in instrument.questions if q.target == "field:service")

    async def _ensure_arm(state) -> None:
        """Draw this driver's arm once, as soon as the stratum is known. `docs/01` §5.

        **Once.** The arm decides which story they are shown, so redrawing it later could leave
        the story they read and the arm stored against their answers disagreeing — which
        `docs/08` §3.1 calls a bug rather than a variation, because every H2 comparison built on
        that row would then be wrong with nothing able to detect it.

        A driver who skipped city or service still gets an arm: they land in the `unknown`
        stratum, the same convention `PanelCandidate.stratum` uses. Leaving them unassigned would
        mean no stimulus at all, and a questionnaire that silently drops its experimental
        manipulation is worse than one balanced over a vaguer stratum.
        """
        if state.arm is not None:
            return
        from twinlab.services.hosted_survey import assign_arm

        state.arm, state.arm_source = await assign_arm(
            state.answers.get(city_key), state.answers.get(service_key)
        )
        log.info("arm %s assigned to %s (%s)", state.arm, state.response_id, state.arm_source)

    async def _forward(state, values):
        from twinlab.services.hosted_survey import submit

        state = _gather(state, values)
        index = state.stop_index

        missing = _missing(state, index)
        if missing:
            shown = "; ".join(missing[:3]) + ("…" if len(missing) > 3 else "")
            return _frame(
                state,
                index=index,
                message=(
                    f"Please answer {len(missing)} more "
                    f"{'question' if len(missing) == 1 else 'questions'} before going on: {shown}"
                ),
            )

        # Part 2's final question is the one answer that ends the questionnaire rather than
        # advancing it. Nothing is stored: the cover sheet says no partial response is retained.
        declined = any(
            q.target == "consent:participate" and state.answers.get(q.key) == DECLINE
            for q in instrument.stops[index - 1].questions
        )
        if declined:
            return _frame(state, index=index, ended=True)

        if index >= demographics_stop:
            # Drawn on leaving the demographics stop, which is several stops before the stimulus
            # is shown — so by the time Part 15 is rendered the arm always exists.
            await _ensure_arm(state)

        if index < total:
            state.stop_index = index + 1
            return _frame(state, index=state.stop_index)

        try:
            receipt = await submit(state)
        except Exception as exc:  # noqa: BLE001 — the driver is told, and nothing is half-written.
            log.exception("hosted survey submit failed for %s", state.response_id)
            return _frame(
                state,
                index=index,
                message=(
                    f"Your answers could not be sent ({type(exc).__name__}). Nothing was saved. "
                    "Please press Send again, or tell the researcher this reference: "
                    f"{state.response_id}."
                ),
            )
        state.submitted = True
        return _frame(state, index=index, done=_receipt_html(receipt), ended=False)

    async def _step_back(state, values):
        state = _gather(state, values)
        state.stop_index = max(1, state.stop_index - 1)
        return _frame(state, index=state.stop_index)

    async def _on_forward(state, *values):
        return await _navigate(state, values, forward=True)

    async def _on_back(state, *values):
        return await _navigate(state, values, forward=False)

    forward.click(_on_forward, inputs=[progress, *controls], outputs=outputs)
    back.click(_on_back, inputs=[progress, *controls], outputs=outputs)

    def _start():
        """A fresh questionnaire per session.

        `gr.State` deep-copies its initial value for every session, so a progress object built at
        render time would hand every driver a **copy of one `response_id`** — every submission
        upserting over the last. The id is therefore minted on load, once per session.
        """
        from twinlab.survey.payload import new_progress

        return new_progress()

    load_once(_start, outputs=[progress])


def _receipt_html(receipt) -> str:
    """The closing screen. The reference number is the point of it.

    The driver is not told whether a twin was built: that is a research-side outcome, it depends
    on gates they were not asked about, and the cover sheet promised them a reference number and
    nothing else. The researcher sees all of it on the Driver survey page instead.
    """
    return (
        '<div class="tl-sv-done">'
        '<h1 class="tl-sv-title">Thank you</h1>'
        "<p>Your answers have been sent. Please note down this reference number. You need it if "
        "you want to withdraw your answers within 14 days.</p>"
        f'<div class="ref">{esc(receipt.reference)}</div>'
        "<p>You can close this page now.</p>"
        "</div>"
    )


__all__ = ["render_survey_take"]
