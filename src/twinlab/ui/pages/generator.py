"""Generator — `docs/06` §4.

The Synthetic Survey Generator. Records get an id beginning `SYN-` and
`data_type = 'SYNTHETIC'`, and **no LLM call is ever made** on this page or below it: a synthetic
respondent is drawn from seeded distributions in Python, so the same seed gives the same batch
(`docs/09` §2) and the model's own priors never reach the data the twins are built from.

Content and ordering are mandatory (`docs/06`, preamble). §4's two-column dashboard is built
here in its stated order; the control-to-parameter binding lives in `services/generator.py` so
it is testable without constructing a Gradio app (`docs/05` §8.4 rule 1).

**Every one of §4's controls is now bound.** The five per-lever reaction sliders and the
captive-voice checkbox — previously shown on this page as "not built" — drive the two holdout
blocks: an `H2_*` answer moves by the respondent's assigned arm and an `H3_V{n}_*` answer by that
version's own code, each weighted by the lever sliders. See `docs/DECISIONS.md`.
"""

from __future__ import annotations

import gradio as gr

from ..components import (
    app_header,
    data_table,
    empty_state,
    esc,
    global_nav,
    load_once,
    section_title,
)
from ..theme import page_classes


def _warning_html() -> str:
    """§4's standing warning. Shown on this page and on Validation, in `docs/08` §6.2's words."""
    from twinlab.services.generator import SYNTHETIC_WARNING

    return f'<div class="tl-note tl-note-warn">{esc(SYNTHETIC_WARNING)}</div>'


def _clipping_note(pinned: list) -> str:
    """The `v7` pre-flight note: which sliders this batch would pin to the end of the scale.

    Says so explicitly when nothing is pinned, rather than rendering nothing: an absent note and a
    clean spec would look identical, and the researcher could not tell whether the check ran
    (`CLAUDE.md` rule 7). The shares are already formatted in the service layer.

    A note, never a block: a batch two-fifths on the fairness floor may be exactly what the
    researcher wants, and nothing here prevents generating it.
    """
    if not pinned:
        return (
            '<div class="tl-note tl-note-info">'
            "No construct piles up at an end of the scale in this batch. Drivers will differ by "
            "as much as the spread dials say."
            "</div>"
        )
    worst = ", ".join(f"{esc(c.label)} ({esc(c.share)})" for c in pinned)
    return (
        '<div class="tl-note tl-note-warn">'
        f"<b>Before you generate:</b> {worst} would land on the very end of the scale for that "
        "share of the batch. Those respondents are identical to each other on that construct "
        "however high the spread dials are set, so the batch is less individual than the dials "
        "suggest — and a wrong-person test has that much less room to work in. Move the slider "
        "away from the end, or lower the between-driver spread."
        "</div>"
    )


def _salience_note(mix: list) -> str:
    """The `v10` pre-flight note: which change this batch's drivers would care about most.

    `salience_spread` is centred on the reaction sliders, so the batch's mean salience per lever
    is whatever the researcher set — the condition that keeps the draw from being a re-weighting
    fitted to a twin pass rate. The consequence worth seeing before the calls are spent is that
    spreading a pay weight of 2.0 against four of 1.0 still leaves most of the batch weighting
    pay highest. Every persona then *states* that weighting, which is the repair, but the batch
    does not contain drivers who want different things.

    Says so explicitly when no lever is weighted at all, rather than rendering nothing, for the
    same reason `_clipping_note` does (`CLAUDE.md` rule 7).

    A note, never a block.
    """
    from twinlab.services.generator import SALIENCE_NOTICE_SHARE

    if not mix:
        return (
            '<div class="tl-note tl-note-info">'
            "No reaction slider is above zero, so no driver in this batch has a change that "
            "matters most to them and none of their answers will move under Part 16 or Part 17. "
            "That is the no-reaction null; raise a reaction slider to leave it."
            "</div>"
        )
    spread = ", ".join(f"{esc(s.label)} {esc(s.share)}" for s in mix)
    top = mix[0]
    if top.share_value < SALIENCE_NOTICE_SHARE:
        return (
            '<div class="tl-note tl-note-info">'
            f"Which change matters most, across the batch: {spread}. Drivers differ in what they "
            "care about, and each one says so in their own words."
            "</div>"
        )
    return (
        '<div class="tl-note tl-note-warn">'
        f"<b>Before you generate:</b> {esc(top.share)} of this batch would care most about "
        f"{esc(top.label)} ({spread}). Every persona will say so, which is what a twin needs in "
        "order to rank the six versions — but the batch carries almost no difference between "
        "drivers on <i>what</i> they want, so nothing here lets a twin tell two drivers apart by "
        "it. Widen how much drivers differ in which change matters, or move the reaction sliders "
        "closer together."
        "</div>"
    )


def _filled(values: dict[str, object], key: str, label: str) -> object:
    """A dashboard box's value, or a sentence naming the box that is empty.

    A `gr.Number` sends ``None`` when its box is cleared. Passing that to `int()` raised
    ``int() argument must be ... not 'NoneType'`` on the screen, which names no control. Refusing
    here, rather than substituting a default, is deliberate: an empty seed defaulted silently would
    make the batch look reproducible when it is not (`docs/09` §2).
    """
    value = values[key]
    if value is None or value == "":
        raise ValueError(f"'{label}' is empty. Type a number in that box; nothing is defaulted.")
    return value


def _spec_from_controls(values: dict[str, object]) -> object:
    """Build a `GeneratorSpec` from the dashboard. All logic is in the service layer."""
    from twinlab.models.view import GENERATOR_CITIES, GENERATOR_SERVICES
    from twinlab.services.generator import (
        BATCH_SLIDERS,
        REACTION_SLIDERS,
        SENTIMENT_SLIDERS,
        default_spec,
    )

    def num(key: str, label: str) -> float:
        return float(_filled(values, key, label))  # type: ignore[arg-type]

    def whole(key: str, label: str) -> int:
        return int(_filled(values, key, label))  # type: ignore[arg-type]

    return default_spec(
        whole("seed", "Seed (same seed, same data)"),
        count=whole("count", "How many surveys"),
        name=str(values["name"]),
        attention_fail_share=num("attention_fail_share", "Share failing attention checks"),
        city_weights={c: float(values[f"city:{c}"]) for c in GENERATOR_CITIES},  # type: ignore[arg-type]
        service_weights={
            s: float(values[f"svc:{s}"]) for s in GENERATOR_SERVICES  # type: ignore[arg-type]
        },
        age_range=(whole("age_lo", "Youngest age"), whole("age_hi", "Oldest age")),
        tenure_months_range=(
            whole("ten_lo", "Fewest months on Uber"),
            whole("ten_hi", "Most months on Uber"),
        ),
        hours_per_week_range=(
            whole("hrs_lo", "Fewest hours a week"),
            whole("hrs_hi", "Most hours a week"),
        ),
        woman_share=num("woman_share", "Share of women"),
        multi_app_share=num("multi_app_share", "Use other apps too"),
        vehicle_loan_share=num("vehicle_loan_share", "Car or bike on a loan"),
        need_money=num("need_money", "Need the money (1 to 7)"),
        sentiment=str(values["sentiment"]),
        # Absolute 1-7 targets, not offsets: §4's caption is "average answer on a 1 to 7 scale".
        construct_targets={
            code: float(values[f"sent:{code}"])  # type: ignore[arg-type]
            for _, code in SENTIMENT_SLIDERS
        },
        lever_reactions={
            lever: float(values[f"react:{lever}"])  # type: ignore[arg-type]
            for _, lever in REACTION_SLIDERS
        },
        captive_voice=bool(values["captive_voice"]),
        **{
            field: float(values[f"batch:{field}"])  # type: ignore[arg-type]
            for _, field, _, _, _ in BATCH_SLIDERS
        },
    )


def render_generator(badge: str | None = None) -> None:
    """Build the Generator page into the enclosing Blocks context, in `docs/06` §4's order."""
    from twinlab.models.view import GENERATOR_CITIES, GENERATOR_SERVICES, GeneratorSpec
    from twinlab.services.generator import (
        BATCH_SLIDERS,
        CAPTIVE_VOICE_LABEL,
        PREVIEW_N,
        REACTION_CAPTION,
        REACTION_SLIDERS,
        SENTIMENT_PRESETS,
        SENTIMENT_SLIDERS,
        default_spec,
    )

    # The dashboard opens on the config file's values, so what the researcher sees is what a
    # batch generated without touching a control would actually use. A page carrying its own
    # literal defaults would drift from `config/generator.default.yaml` silently.
    opening: GeneratorSpec = default_spec(20260930)
    preset_values = SENTIMENT_PRESETS[opening.sentiment]

    with gr.Column(elem_classes=page_classes("/generator")):
        app_header("Generator", "Synthetic surveys for testing", badge)
        global_nav("/generator")
        gr.HTML(_warning_html())

        #: Every control, keyed the way `_spec_from_controls` reads it. Gradio handlers take
        #: positional inputs, so the keys and the component list are zipped once, here, rather
        #: than each handler counting arguments.
        controls: dict[str, gr.components.Component] = {}

        with gr.Row(equal_height=False):
            # ------------------------------------------------------------------ left column
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("Batch"))
                    with gr.Row():
                        controls["count"] = gr.Number(
                            value=opening.count, precision=0, minimum=1, maximum=5000,
                            label="How many surveys",
                        )
                        controls["name"] = gr.Textbox(value="test", label="Batch name")
                    with gr.Row():
                        controls["seed"] = gr.Number(
                            value=opening.seed, precision=0, minimum=0,
                            label="Seed (same seed, same data)",
                        )
                        controls["attention_fail_share"] = gr.Number(
                            value=opening.attention_fail_share, minimum=0.0, maximum=1.0,
                            step=0.01, label="Share failing attention checks",
                        )

                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("Where they drive"))
                    gr.Markdown("Relative weights. 0 leaves a city out.")
                    for city in GENERATOR_CITIES:
                        controls[f"city:{city}"] = gr.Slider(
                            0.0, 5.0, value=opening.city_weights.get(city, 1.0), step=0.5,
                            label=city, elem_classes=["tl-slider-row"],
                        )

                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("Who they are"))
                    for service in GENERATOR_SERVICES:
                        controls[f"svc:{service}"] = gr.Slider(
                            0.0, 5.0, value=opening.service_weights.get(service, 1.0), step=0.5,
                            label=f"{service} (weight)", elem_classes=["tl-slider-row"],
                        )
                    with gr.Row():
                        controls["age_lo"] = gr.Number(
                            value=opening.age_range[0], precision=0, label="Youngest age"
                        )
                        controls["age_hi"] = gr.Number(
                            value=opening.age_range[1], precision=0, label="Oldest age"
                        )
                    with gr.Row():
                        controls["ten_lo"] = gr.Number(
                            value=opening.tenure_months_range[0], precision=0,
                            label="Fewest months on Uber",
                        )
                        controls["ten_hi"] = gr.Number(
                            value=opening.tenure_months_range[1], precision=0,
                            label="Most months on Uber",
                        )
                    with gr.Row():
                        controls["hrs_lo"] = gr.Number(
                            value=opening.hours_per_week_range[0], precision=0,
                            label="Fewest hours a week",
                        )
                        controls["hrs_hi"] = gr.Number(
                            value=opening.hours_per_week_range[1], precision=0,
                            label="Most hours a week",
                        )
                    controls["woman_share"] = gr.Slider(
                        0.0, 1.0, value=opening.woman_share, step=0.05,
                        label="Share of women", elem_classes=["tl-slider-row"],
                    )
                    controls["multi_app_share"] = gr.Slider(
                        0.0, 1.0, value=opening.multi_app_share, step=0.05,
                        label="Use other apps too", elem_classes=["tl-slider-row"],
                    )
                    controls["vehicle_loan_share"] = gr.Slider(
                        0.0, 1.0, value=opening.vehicle_loan_share, step=0.05,
                        label="Car or bike on a loan", elem_classes=["tl-slider-row"],
                    )
                    controls["need_money"] = gr.Slider(
                        1.0, 7.0, value=opening.need_money, step=0.5,
                        label="Need the money (1 to 7)", elem_classes=["tl-slider-row"],
                    )

            # ----------------------------------------------------------------- right column
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("How they feel about the app"))
                    gr.Markdown(
                        "Average answer on a 1 to 7 scale (5 point questions are converted). "
                        "Start from a preset or set each slider."
                    )
                    # The presets FILL the sliders (`docs/06` §4) rather than acting beside
                    # them, so pressing one is visible in every value it sets.
                    controls["sentiment"] = gr.Radio(
                        choices=[
                            ("Frustrated drivers", "frustrated"),
                            ("Mixed", "mixed"),
                            ("Content drivers", "content"),
                        ],
                        value=opening.sentiment,
                        show_label=False,
                        elem_classes=["tl-toggle"],
                    )
                    gr.HTML(
                        '<div class="tl-scale-ends">'
                        "<span>1 strongly disagree</span><span>7 strongly agree</span></div>"
                    )
                    for label, code in SENTIMENT_SLIDERS:
                        controls[f"sent:{code}"] = gr.Slider(
                            1.0, 7.0,
                            value=opening.construct_targets.get(code, preset_values[code]),
                            step=0.5, label=label, elem_classes=["tl-slider-row"],
                        )
                    for label, field, low, high, step in BATCH_SLIDERS:
                        controls[f"batch:{field}"] = gr.Slider(
                            low, high, value=getattr(opening, field), step=step,
                            label=label, elem_classes=["tl-slider-row"],
                        )

                with gr.Group(elem_classes=["tl-panel"]):
                    gr.HTML(section_title("How strongly they react to each change"))
                    gr.Markdown(REACTION_CAPTION)
                    for label, lever in REACTION_SLIDERS:
                        controls[f"react:{lever}"] = gr.Slider(
                            0.0, 2.0, value=opening.lever_reactions.get(lever, 1.0), step=0.5,
                            label=label, elem_classes=["tl-slider-row"],
                        )
                    controls["captive_voice"] = gr.Checkbox(
                        value=opening.captive_voice, label=CAPTIVE_VOICE_LABEL
                    )

        # Pressing a preset sets every construct slider. Pure and local — no network, no model.
        sentiment_outputs = [controls[f"sent:{code}"] for _, code in SENTIMENT_SLIDERS]

        def _apply_preset(preset: str) -> tuple[object, ...]:
            values = SENTIMENT_PRESETS[preset]
            return tuple(gr.update(value=values[code]) for _, code in SENTIMENT_SLIDERS)

        controls["sentiment"].change(
            _apply_preset, inputs=controls["sentiment"], outputs=sentiment_outputs
        )

        # ------------------------------------------------------------------------- actions
        with gr.Group(elem_classes=["tl-panel"]):
            with gr.Row():
                preview_button = gr.Button(
                    f"Preview {PREVIEW_N} drivers", elem_classes=["tl-btn-quiet"]
                )
                generate_button = gr.Button("Generate surveys", variant="primary")
                delete_button = gr.Button(
                    "Delete all synthetic surveys", elem_classes=["tl-btn-danger"]
                )
            status = gr.HTML("")

        preview_table = gr.HTML(
            empty_state(
                "No preview yet.",
                f"Press Preview {PREVIEW_N} drivers. Nothing is written to the database.",
            )
        )

        # Delete is confirmed and names the count before it runs (`docs/06` §4).
        with gr.Group(visible=False) as confirm:
            confirm_line = gr.Markdown("")
            # Shown only when the pre-flight found twins that cannot go without changing a stored
            # result (`ARCHITECTURE_UPDATE.md` §3.4 step 3). Unticked, the delete refuses as a
            # whole: a partial delete nobody asked for is worse than a refusal.
            keep_blocked = gr.Checkbox(
                label="Keep the twins that cannot be deleted, and delete the rest",
                value=False,
                visible=False,
            )
            # The other answer to the same refusal: take the synthetic test sessions as well, so
            # every twin goes and nothing is left pointing at a twin that no longer exists.
            # Shown only when the pre-flight found a session that is synthetic through and
            # through — a session mixing these twins with real drivers is refused either way.
            purge_sessions = gr.Checkbox(
                label=(
                    "Also delete their test sessions, runs and validity results "
                    "(clears everything — these results are synthetic-contaminated)"
                ),
                value=False,
                visible=False,
            )
            with gr.Row():
                confirm_go = gr.Button("Delete them", elem_classes=["tl-btn-danger"])
                gr.Button("Cancel").click(
                    lambda: gr.update(visible=False), outputs=confirm
                )

        order = list(controls)
        inputs = [controls[key] for key in order]

        def _spec(values: tuple[object, ...]) -> object:
            return _spec_from_controls(dict(zip(order, values, strict=True)))

        def _preview(*values: object) -> str:
            """Derives only. `docs/06` §4: *Preview 3 drivers* inserts nothing.

            Carries the `v7` and `v10` pre-flight notes above the three rows. Three
            respondents cannot show that a fifth of the batch shares one construct's floor, nor
            that five-sixths of it would care most about the same lever, and finding either out
            after a sweep costs the sweep (`docs/DECISIONS.md`, 2026-10-12 and 2026-10-13).
            """
            from twinlab.services.generator import clipping, preview, salience

            try:
                spec = _spec(values)
                rows = preview(spec)
                pinned = clipping(spec)
                mix = salience(spec)
            except Exception as exc:  # noqa: BLE001 — the screen must say why, not show zeros.
                from ..components import error_state

                return error_state(
                    "Could not derive a preview.", type(exc).__name__, str(exc)[:200]
                )
            return _clipping_note(pinned) + _salience_note(mix) + data_table(
                ["Id", "City", "Service", "Arm", "Age", "Gender", "Hours", "Months", "Mean"],
                [
                    [
                        esc(r.response_id), esc(r.city), esc(r.service), esc(r.arm),
                        esc(r.age), esc(r.gender), esc(r.hours_per_week),
                        esc(r.tenure_months), esc(r.mean_answer),
                    ]
                    for r in rows
                ],
                caption="Derived in memory. Nothing was written.",
                empty=empty_state("Nothing to preview.", "Raise the batch size above zero."),
            )

        async def _counts() -> str:
            """§4's status line. Live Supabase counts; an error says so rather than showing 0."""
            from twinlab.services.generator import survey_counts

            try:
                counts = await survey_counts()
            except Exception as exc:  # noqa: BLE001
                from ..components import error_state

                return error_state(
                    "Could not read the survey counts.", type(exc).__name__, str(exc)[:200]
                )
            return f'<div class="tl-card"><strong>{esc(counts.line)}</strong></div>'

        async def _generate(*values: object) -> str:
            """§4's *Generate surveys*. **Raw objects first, then rows** (I16).

            No model call and no logic here: the whole action is
            `services.generator.generate_and_store` (`docs/05` §8.4 rule 1). A failure says what
            failed and stores nothing, rather than reporting a partial batch as a batch.
            """
            from twinlab.services.generator import generate_and_store

            try:
                result = await generate_and_store(_spec(values))
            except Exception as exc:  # noqa: BLE001
                from ..components import error_state

                return error_state("Nothing was stored.", type(exc).__name__, str(exc)[:300])
            line = (
                f"Stored batch {result['batch_id']}: {result['submissions']:,} surveys, "
                f"{result['answers']:,} answers and {result['raw_objects']:,} raw objects. "
                # The seed, named on screen. It is already on `synthetic_batches.seed`, so the
                # batch is reproducible either way — but `docs/09` §2 makes a batch reproducible
                # from `(seed, count, spec)` and a researcher asked to record the seed should not
                # have to go and look it up.
                f"Seed {result['seed']}, {result['count']} requested — this batch "
                "regenerates from that seed and these settings."
            )
            return f'<div class="tl-note tl-note-ok">{esc(line)}</div>' + await _counts()

        async def _ask_delete() -> tuple[object, str, object]:
            """The confirm step, costed by the **pre-flight** rather than by a guess. §3.4 step 1.

            It used to promise "no run is touched" and say nothing about `studio_runs`, which was
            the table that actually blocked the delete. Now the blocking references are counted
            first and named here, so the refusal arrives before the button rather than as a
            foreign-key traceback after it.
            """
            from twinlab.services.generator import delete_preflight, survey_counts

            counts = await survey_counts()
            if not counts.synthetic:
                return (
                    gr.update(visible=False),
                    "No synthetic surveys to delete.",
                    gr.update(visible=False),
                )
            pre = await delete_preflight()
            held, going = pre["blocked_twin_ids"], pre["deletable_twin_ids"]
            line = (
                f"### Delete {counts.synthetic:,} synthetic surveys?\n"
                "Their answers, any twins built from them and those twins' Twin Studio runs go "
                f"too. **{counts.real:,} real surveys are not touched, and no run, answer or "
                "frozen panel is touched.**"
            )
            purgeable = pre.get("purgeable_session_ids") or []
            mixed = pre.get("mixed_session_ids") or []
            if held:
                reasons = ", ".join(sorted(pre["blocked"]))
                line += (
                    f"\n\n**{len(held)} of {len(pre['twin_ids'])} synthetic twins cannot go**: "
                    f"they are referenced by `{reasons}`. Deleting them would change a stored "
                    f"result. Tick the first box to delete the other {len(going)} and keep these."
                )
            real_at_risk = pre.get("real_twins_at_risk") or []
            if purgeable:
                rows = {s["session_id"]: s for s in pre["dependent_sessions"]}
                named = ", ".join(
                    f"*{rows[s]['name']}* ({rows[s]['runs_n']} run(s))" for s in purgeable[:4]
                )
                line += (
                    f"\n\nOr tick the second box to clear everything: {len(purgeable)} test "
                    f"session(s) — {named} — hold these twins, so their runs and validity "
                    "verdicts go with them. Every one of those results was computed over "
                    "synthetic twins, and synthetic data proves nothing about drivers "
                    "(`docs/08` §6.2), so there is no reportable result in the set."
                )
            if mixed:
                # Deliberately **not** offered here. *Delete all synthetic surveys* means
                # synthetic, so this screen never puts a real driver's rows at risk whatever is
                # ticked. A session that mixes the two is handled one twin at a time in
                # Twin Lab → Twins, where the researcher picks the rows themselves.
                line += (
                    f"\n\n**{len(mixed)} of those session(s) also hold {len(real_at_risk)} real "
                    f"twin(s)** ({', '.join(real_at_risk[:4])}), so they are left alone and the "
                    "synthetic twins on them stay too. This screen only ever deletes synthetic "
                    "rows. To clear those, select the twins yourself in **Twin Lab → Twins**."
                )
            return (
                gr.update(visible=True),
                line,
                gr.update(visible=bool(held), value=False),
                gr.update(visible=bool(purgeable), value=False),
            )

        async def _do_delete(skip: bool, purge: bool) -> tuple[object, str, str]:
            from twinlab.services.generator import DeleteBlocked, delete_all_synthetic

            try:
                removed = await delete_all_synthetic(
                    skip_blocked=bool(skip), purge_sessions=bool(purge)
                )
            except DeleteBlocked as exc:
                # The sentence, **not** the traceback, and exactly once (§3.4 step 3 and §3.3).
                return gr.update(visible=True), f"**Nothing was deleted.** {exc}", await _counts()
            line = (
                f"Deleted {removed['submissions']:,} surveys, {removed['answers']:,} answers, "
                f"{removed['twins']:,} twins and {removed.get('studio_runs', 0):,} Twin Studio "
                "runs."
            )
            purged = removed.get("purged") or {}
            if purged:
                # Said out loud, itemised. A withdrawal of stored results is not something the
                # screen should report as a bare success.
                line += (
                    f" **Also cleared {purged.get('sessions', 0):,} synthetic test session(s)**: "
                    + ", ".join(
                        f"{n:,} {table.replace('_', ' ')}"
                        for table, n in sorted(purged.items())
                        if table != "sessions"
                    )
                    + "."
                )
            if removed.get("blocked"):
                line += (
                    f" **{len(removed['blocked'])} twin(s) kept** because deleting them would "
                    "change a stored result."
                )
            return gr.update(visible=False), line, await _counts()

        preview_button.click(_preview, inputs=inputs, outputs=preview_table)
        generate_button.click(_generate, inputs=inputs, outputs=status)
        delete_button.click(
            _ask_delete, outputs=[confirm, confirm_line, keep_blocked, purge_sessions]
        )
        confirm_go.click(
            _do_delete,
            inputs=[keep_blocked, purge_sessions],
            outputs=[confirm, confirm_line, status],
        )

        # The counts are the only network work on this page and they happen off the render
        # path, never inside it (`docs/05` §8.4 rule 2). Painted once, not on a timer: nothing
        # here changes without the researcher pressing something.
        load_once(_counts, outputs=status)


__all__ = ["render_generator"]
