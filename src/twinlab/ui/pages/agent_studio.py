"""Agent Studio — `docs/06` §6.

Configure and test each agent. **Not the execution engine** — the study runs from Twin Lab, and
the sharpest line in §6 is the last one:

    Run Manager's test button builds a plan; it never launches a sweep.

That button calls :func:`twinlab.services.agent_config.manager_plan`, which is arithmetic over
counts and settings and creates no session. The acceptance test asserts the `sessions` table is
unchanged across the call.

Two further rules are the service layer's, not this page's, because a disabled control is not a
guarantee: a **frozen agent cannot be edited while a session is running**, and **`native` is never
offered** as an output mode — `OUTPUT_MODES` holds two entries, so the option cannot appear even
by accident (`docs/02` §5.1, I13).

`docs/06` §6 also retires the prototype's `rules only` / `uses AI` badges: they described the
prototype, not the architecture. Each card shows the agent's **actual** model usage from its
config.
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
    load_js,
    load_once,
    num,
    pill,
    section_title,
    status_dot,
)
from ..theme import page_classes

#: Bridges a click on an agent card into the hidden radio that actually holds the selection.
#: `docs/06` §6 asks for "five selectable `agent_card`s", and `gr.HTML` emits no events — the
#: same constraint `docs/05` §8.3 solves this way for the 243-grid. The radio stays in the DOM
#: and keeps the keyboard and screen-reader behaviour; only its default rendering is hidden.
_AGENT_PICK_JS = """
() => {
  if (window.__tlAgentBound) return;
  window.__tlAgentBound = true;
  document.addEventListener("click", (event) => {
    const card = event.target.closest(".tl-agent-card[data-agent]");
    if (!card) return;
    const radio = document.querySelector(
      '#tl-agent-pick input[type="radio"][value="' + card.dataset.agent + '"]'
    );
    if (radio && !radio.checked) radio.click();
  });
}
"""


def _checker_html(view: dict) -> str:
    """The *Quality Checker* view of `docs/06` §6: the two contract checks, the score, the
    per-item comparison and the keep/drop decision.

    ``Not tested`` where a side is absent, never a zero: an item only one of them answered is not
    scored, and a difference against a blank would be a number standing in for a measurement
    (I17).
    """
    if not view.get("has_run"):
        return empty_state(
            f"{view['twin_id']} has no quality run.",
            "Run the twin quality test from Twin Lab → Twins.",
        )

    kept = view["kept"]
    decision = (
        status_dot("complete", "Kept") if kept
        else status_dot("failed", "Dropped") if kept is False
        else status_dot("pending", "No verdict")
    )
    checks = kv_table(
        [
            (
                "Every holdout item present",
                status_dot("complete", "pass") if view["complete"]
                else status_dot("failed", f"missing {', '.join(view['missing'][:6])}"),
            ),
            (
                "Every answer inside its own scale",
                status_dot("complete", "pass") if view["in_scale"]
                else status_dot(
                    "failed", f"outside range: {', '.join(view['out_of_range'][:6])}"
                ),
            ),
            # `ARCHITECTURE_UPDATE.md` §5.3: each threshold row carries its `must be …` caption,
            # read
            # from the live config rather than written into the screen. The verdict beside the
            # number
            # is per-threshold; the keep/drop decision below is the **AND** of the two.
            # `kv_table` escapes the label and trusts the value, so the caption rides in the value
            # cell beside the number — which is also where it is read.
            (
                "Average error",
                (
                    status_dot(
                        "complete" if view["mae"] <= view["mae_max"] else "failed",
                        num(view["mae"], signed=False),
                    )
                    if view["mae"] is not None
                    else num(None)
                )
                + f' <small>must be {esc(view["mae_max"])} or less</small>',
            ),
            (
                "Share within 1 point",
                (
                    status_dot(
                        "complete"
                        if view["pct_within_1"] >= view["pct_within_1_min"]
                        else "failed",
                        f"{view['pct_within_1'] * 100:.0f}%",
                    )
                    if view["pct_within_1"] is not None
                    else num(None)
                )
                + f' <small>must be {view["pct_within_1_min"] * 100:.0f}% or more</small>',
            ),
            ("Items scored", str(view["items_n"])),
            ("Repeats averaged", str(view["repeats"])),
            ("Model", esc(view["model"])),
            # Screenshot 6's explicit `Decision: Keep this twin` line, with the rule beside it so
            # the
            # conjunction is visible. D-4: the decision is both thresholds, never either.
            (
                "Decision",
                f"{decision} <small>{esc(view['decision_rule'])}</small>",
            ),
        ],
        caption="Completeness, scale and the keep/drop decision",
    )
    table = data_table(
        ["Held-out item", "Question", "Driver said", "Twin said", "Error"],
        [
            [
                esc(row["item_id"]),
                esc(row["question"]),
                "—" if row["driver"] is None else str(row["driver"]),
                "—" if row["twin"] is None else str(row["twin"]),
                num(None if row["error"] is None else float(row["error"]), signed=False),
            ]
            for row in view["comparison"]
        ],
    )
    correlations = view.get("correlations") or {}
    r_table = (
        kv_table(
            [
                (name.capitalize(), num(value, signed=False))
                for name, value in sorted(correlations.items())
            ],
            caption="Twin and driver move together (r)",
        )
        if correlations
        else ""
    )
    return checks + r_table + section_title("Held-out answers") + table


def _twin_html(view: dict) -> str:
    """The *Twin Interviewer* view. `docs/06` §6, `ARCHITECTURE_UPDATE.md` §5.1.

    One row **per instruction variant** — the saved prompt and the edit — with `Answer checked?`,
    the six metrics and the reason the twin gave. The previous build transposed this into one row
    per metric with `Saved / Your edit / Difference` columns, which had no pass/fail and no reason.

    The answers table shows **what the twin said**, with the driver's value beside it. It used to
    show the driver's column alone — the panel's input rather than its result, which is the defect
    that mattered here.
    """
    metrics = view.get("metrics") or []
    body = ""
    variants = view.get("variants") or []
    if variants:
        body += section_title("What each set of instructions produced") + data_table(
            [
                "Instructions",
                "Answer checked?",
                *(m.capitalize() for m in metrics),
                "A reason it gave",
            ],
            [
                [
                    esc(str(row["which"]).capitalize()),
                    (
                        status_dot(
                            "complete",
                            "pass"
                            + (
                                f" ({row['retries']} repair)"
                                if row.get("retries")
                                else ""
                            ),
                        )
                        if row["checked"]
                        # Never coerced into a pass. A twin that cannot produce 37 valid integers
                        # after its one targeted repair has failed, and that is the right outcome.
                        else status_dot("failed", "no valid answer")
                    ),
                    *(num((row.get("scores") or {}).get(m), signed=False) for m in metrics),
                    esc(row.get("reason") or ""),
                ]
                for row in variants
            ],
        )
        driver = view.get("driver_scores") or {}
        if driver:
            body += kv_table(
                [(m.capitalize(), num(driver.get(m), signed=False)) for m in metrics],
                caption="This twin's own driver, for comparison (Uber today)",
            )
    if view.get("note"):
        body += f'<div class="tl-card">{esc(view["note"])}</div>'
    body += section_title("Some of the 37 answers it gave")
    body += data_table(
        ["Item", "Question", "Twin said", "Driver said"],
        [
            [
                esc(row["item_id"]),
                esc(row["question"]),
                # `Not tested` rather than a zero on either side: an item only one of them answered
                # is not scored, and a blank standing in for a measurement is I17's failure.
                num(row["twin"], signed=False) if row["twin"] is not None else _absent(),
                num(row["driver"], signed=False) if row["driver"] is not None else _absent(),
            ]
            for row in view["answers"]
        ],
        empty=empty_state(
            "Nothing was asked.",
            "Choose a twin and a rendered version above, then press Test this agent.",
        ),
    )
    return body


def _absent() -> str:
    """The *Not tested* marker, so the two sides of the answers table cannot word it differently."""
    return '<span class="tl-absent">Not tested</span>'


def _history_model(row: dict) -> str:
    """The model this history entry was saved against, from its own snapshot. §5.6.

    Off the snapshot rather than the current config, so a later edit or seed correction cannot
    retroactively change what an old entry says it was saved with — which is the only reason an
    append-only audit log is worth keeping.
    """
    snapshot = row.get("snapshot") or {}
    model = (snapshot.get("model") or {}) if isinstance(snapshot, dict) else {}
    name = str(model.get("name") or "")
    if not name:
        return ""
    temp = model.get("temperature")
    suffix = f" at {temp}" if temp is not None else ""
    return f" · <code>{esc(name)}</code>{esc(suffix)}"


def _design_html(view: dict) -> str:
    """The *Policy Designer* view. `docs/06` §6, `ARCHITECTURE_UPDATE.md` §5.2.

    `Text used` carries the **rendered paragraph** — what a twin is shown — with the researcher-
    facing
    bullet summary in its own column beside it. The panel used to put the bullets under `Text used`,
    which made two artefacts `docs/03` §4.3 keeps deliberately apart look interchangeable on the one
    screen whose job is to show what the design agent produced.
    """
    rows = [
        [
            esc(lever["lever_name"]),
            esc(str(lever["dial"])),
            esc(lever["paragraph"]) or _absent(),
            esc("; ".join(lever["bullets"]) or "No change from today."),
        ]
        for lever in view["levers"]
    ]
    body = (
        data_table(
            [
                "Dial",
                "Setting",
                # The twin's artefact and the researcher's, named so they cannot be confused.
                "Text used (what the twin is shown)",
                "Bullet summary (never shown to a twin)",
            ],
            rows,
        )
        + kv_table([("Fairwork score", esc(view["fairwork_text"]))])
    )

    # §5.2 item 2: labelled Wording A and Wording B blocks. Wording is a real experimental factor
    # (validity test 5), so one unlabelled set of cards understates what is being varied.
    body += section_title("The whole scenario, in both wordings")
    wordings = view.get("wordings") or {}
    if not wordings:
        body += empty_state(
            "No scenario rendered for this version yet.",
            "Render it in Twin Studio, or ask the twins for it in Twin Lab → Dial board.",
        )
    else:
        for label, paragraphs in wordings.items():
            body += (
                f'<div class="tl-wording"><div class="tl-wording-head">Wording {esc(label)}'
                + (
                    " — as rendered"
                    if label == "A"
                    else " — the same five paragraphs in reverse order (validity test 5)"
                )
                + "</div>"
                + "".join(f'<div class="tl-card">{esc(p)}</div>' for p in paragraphs)
                + "</div>"
            )

    # §5.2 item 3: absent entirely before this. Read-only, and the `Why` column says these come from
    # the odometer rather than from the agent choosing — a reader who thinks otherwise has
    # misunderstood the design.
    body += section_title("Versions it would test next")
    body += data_table(
        ["Version", "Why"],
        [[esc(row["code"]), esc(row["why"])] for row in view["next_versions"]],
        caption="The next odometer positions from here. Nothing is started by looking at this.",
    )
    return body


def _in_force_line(view: dict) -> str:
    """What this agent is actually run with, and where each value comes from. §5.5 item 3.

    Stated whether or not it differs from the stored row — a researcher reading a temperature needs
    to know which temperature it is every time, not only on the screens where the two happen to
    disagree. When they do disagree the line leads with that, because the stored number is then not
    the one in force and the screen must not let it pass for one.
    """
    force = view.get("in_force") or {}
    if not force.get("model_name"):
        return ""
    head = (
        "**The stored values above are not what runs.** "
        if view.get("in_force_differs")
        else "Actually in force: "
    )
    return (
        f"{head}`{force['provider']}` · `{force['model_name']}` · "
        f"temperature **{force['temperature']}**  \n"
        f"<small>Read from {esc(force['source'])}. Editing the boxes above changes the stored "
        "record and the audit log; it does not change what the runtime loads.</small>"
    )


def _rules_panel() -> None:
    """*Rules everyone follows* — the shared panel below the agent card. `docs/06` §6."""
    from twinlab.services.agent_config import CHECKER_RULES, WEIGHT_METRICS

    gr.HTML(section_title("Rules everyone follows"))
    with gr.Row():
        with gr.Column():
            gr.Markdown("**Checker rules**")
            checker_inputs = [
                gr.Number(value=default, label=label, elem_id=f"tl-rule-{key}")
                for key, label, default in CHECKER_RULES
            ]
        with gr.Column():
            gr.Markdown(
                "**Analyst score weights** — each defaults to 1. "
                "**A weight of 0 omits that metric from the index.**"
            )
            weight_inputs = [
                gr.Number(value=1, label=metric.capitalize(), elem_id=f"tl-weight-{metric}")
                for metric in WEIGHT_METRICS
            ]

    save_rules_button = gr.Button("Save rules", variant="primary")
    rules_note = gr.Markdown("")

    async def _save(*values):
        from twinlab.services.agent_config import save_rules

        n = len(CHECKER_RULES)
        checker = {key: float(v) for (key, _, _), v in zip(CHECKER_RULES, values[:n], strict=True)}
        weights = {metric: float(v) for metric, v in zip(WEIGHT_METRICS, values[n:], strict=True)}
        version = await save_rules(checker=checker, weights=weights)
        return (
            f"Saved. New `app_config` version **{version}**, recorded on every subsequent run. "
            "**Historical runs are untouched** — a run stores the config version it ran under."
        )

    save_rules_button.click(_save, inputs=[*checker_inputs, *weight_inputs], outputs=rules_note)


def _test_panel(
    selected: gr.components.Component, prompt_box: gr.components.Component
) -> None:
    """*Test this agent* — one view per agent. `docs/06` §6's table.

    ``prompt_box`` is the *What this agent is told* textarea, passed in so the Twin Interviewer's
    test can compare **saved versus your edit** without the edit having to be saved first — which
    is the point of a test screen.
    """
    gr.HTML(section_title("Test this agent"))
    with gr.Row():
        twin_for_test = gr.Dropdown([], label="Twin", value=None)
        version_for_test = gr.Textbox(value="01000", label="Version")
    run_test = gr.Button("Test this agent", variant="secondary")
    test_out = gr.HTML("")

    async def _test(
        agent_id: str, twin_id: str | None, version_code: str, prompt_text: str
    ):
        from twinlab.services.agent_config import manager_plan

        if agent_id == "manager":
            # Builds a plan and starts nothing (docs/06 §6). No session is created here.
            from twinlab.services.agent_config import manager_log_preview

            plan = await manager_plan(version_code)
            return (
                kv_table([(r.label, esc(r.value)) for r in plan], caption="The plan")
                # `ARCHITECTURE_UPDATE.md` §5.4: the one section screenshot 7 has and the panel did
                # not. It is a dry run, so this previews the log's shape without producing one.
                + section_title("What it would write to the log")
                + kv_table(
                    [(r.label, esc(r.value)) for r in manager_log_preview(version_code)],
                    caption="One line per agent, in the order they would run",
                )
                + '<div class="tl-card">This is a plan only. Nothing has been started; a sweep '
                "runs from Twin Lab → Agents.</div>"
            )

        if agent_id == "design":
            from twinlab.services.agent_config import design_test_view

            return _design_html(await design_test_view(version_code))

        if agent_id == "analyst":
            from twinlab.services.results import results_panel

            if not version_code:
                return empty_state("No version given.", "Type a version code above.")
            panel = await results_panel(version_code)
            from ..components import metric_bars

            return metric_bars(panel.bars) + (
                f'<div class="tl-card">{esc(panel.analysis)}</div>'
                if panel.analysis
                else empty_state(
                    "No prose for this version yet.",
                    "The analyst writes one when the cell completes.",
                )
            )

        if agent_id == "checker":
            if not twin_id:
                return empty_state("No twin selected.", "Choose a twin above to test this agent.")
            from twinlab.services.agent_config import checker_test_view

            return _checker_html(await checker_test_view(twin_id))

        if agent_id == "twin":
            if not twin_id:
                return empty_state("No twin selected.", "Choose a twin above to test this agent.")
            from twinlab.services.agent_config import twin_test_view

            try:
                view = await twin_test_view(
                    twin_id, version_code or "", edited_prompt=prompt_text
                )
            except Exception as exc:  # noqa: BLE001 — name it rather than render an empty card
                from ..components import error_state

                return error_state(
                    "Could not test the twin agent.", type(exc).__name__, str(exc)[:300]
                )
            return _twin_html(view)

        return empty_state("Nothing to test.", "Select an agent on the left.")

    run_test.click(
        _test,
        inputs=[selected, twin_for_test, version_for_test, prompt_box],
        outputs=test_out,
    )

    async def _twins():
        from twinlab.services.studio import studio_twins

        return gr.update(choices=[t.twin_id for t in await studio_twins()])

    load_once(_twins, outputs=twin_for_test)


def render_agent_studio(badge: str | None = None) -> None:
    """Build Agent Studio into the enclosing Blocks context, in `docs/06` §6's order."""
    from twinlab.services.agent_config import OUTPUT_MODES, PROVIDERS, STUDIO_AGENT_ORDER

    with gr.Column(elem_classes=page_classes("/agents")):
        app_header(
            "Agent Studio",
            "Agent instructions, models and the freeze — not the execution engine",
            badge,
        )
        global_nav("/agents")

        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML(section_title("The five agents"))
                # Left: five selectable cards, in `docs/06` §6's order — Twin Interviewer first.
                selected = gr.Radio(
                    choices=list(STUDIO_AGENT_ORDER),
                    value=STUDIO_AGENT_ORDER[0],
                    label="Agent",
                    elem_id="tl-agent-pick",
                    elem_classes=["tl-agent-pick"],
                )
                # The cards ARE the selector (`docs/06` §6); the radio above is the control
                # they drive, kept in the DOM for the keyboard and the screen reader.
                cards = gr.HTML("")
                load_js(_AGENT_PICK_JS)

            with gr.Column(scale=2):
                gr.HTML(section_title("This agent"))
                name = gr.Textbox(label="Name", interactive=False)
                purpose = gr.Textbox(label="Purpose", lines=2)
                # The prototype sets the prompt body in monospace: it is read as code, and a
                # proportional face hides the indentation the JSON contract depends on.
                prompt = gr.Textbox(
                    label="What this agent is told",
                    lines=16,
                    elem_classes=["tl-resize", "tl-mono"],
                )
                with gr.Row():
                    # Built **from `ModelRef.provider`'s Literal**, never a hand-written list
                    # (`ARCHITECTURE_UPDATE.md` §5.5 item 1). `Mistral` used to be offerable here
                    # and `ModelRef` rejects it, so the screen could produce a row the model
                    # refuses to load.
                    provider = gr.Dropdown(choices=list(PROVIDERS), label="AI provider")
                    model_name = gr.Textbox(label="Model name")
                with gr.Row():
                    temperature = gr.Slider(0.0, 1.5, step=0.05, label="Temperature")
                    # `native` is absent by construction, not filtered out (docs/02 §5.1, I13).
                    output_mode = gr.Dropdown(choices=list(OUTPUT_MODES), label="Output mode")
                # §5.5 item 3. The three boxes above are the stored, editable row. This line is what
                # the agent is **actually run with**, and where each value comes from. A screen that
                # shows a number the runtime silently discards is worse than one that shows nothing:
                # Agent Studio read `Mistral / mistral-small-latest / temperature 1` while the twin
                # ran `gpt-oss:120b` at 0.25.
                in_force_note = gr.Markdown("")
                with gr.Row():
                    save = gr.Button("Save this agent", variant="primary")
                    restore = gr.Button("Put the original text back", variant="secondary")
                    freeze = gr.Button("Freeze for the main study", variant="secondary")
                stamp = gr.Markdown("")

        _rules_panel()
        _test_panel(selected, prompt)

        gr.HTML(section_title("What was changed"))
        changelog = gr.HTML("")

        async def _load(agent_id: str):
            from twinlab.services.agent_config import STUDIO_AGENT_ORDER as order
            from twinlab.services.agent_config import agent_view

            views = [await agent_view(a) for a in order]
            card_html = "".join(
                f'<div class="tl-card tl-agent-card'
                f'{" tl-on" if v["agent_id"] == agent_id else ""}" '
                f'data-agent="{esc(v["agent_id"])}" role="button" tabindex="-1">'
                f'<div class="tl-agent-name">{esc(v["name"])} '
                f"{pill('frozen', 'amber') if v['frozen'] else pill('editable', 'grey')}</div>"
                f'<div class="tl-agent-role">{esc(v["role"])}</div>'
                f'<div class="tl-agent-latest">{
                    status_dot(
                        "complete" if v["enabled"] else "pending",
                        "enabled" if v["enabled"] else "not enabled",
                    )
                } '
                f"{esc(v['model_name']) if v['uses_model'] else 'no model'}</div></div>"
                for v in views
            )
            v = next(x for x in views if x["agent_id"] == agent_id)
            return (
                card_html,
                v["name"],
                v["role"],
                v["prompt"],
                v["provider"],
                v["model_name"],
                v["temperature"],
                v["output_mode"],
                f"Prompt version: v{v['version']} · hash {v['prompt_hash'][:8]}…"
                + ("  ·  **frozen for the main study**" if v["frozen"] else ""),
                _in_force_line(v),
            )

        outputs = [
            cards,
            name,
            purpose,
            prompt,
            provider,
            model_name,
            temperature,
            output_mode,
            stamp,
            in_force_note,
        ]
        selected.change(_load, inputs=selected, outputs=outputs)

        async def _changelog():
            from twinlab.services.agent_config import history

            rows = await history()
            return data_table(
                ["When", "Agent", "What was saved"],
                [
                    [
                        esc(str(r.get("created_at"))[:19]),
                        # Upper-cased, as screenshot 4's log has them: `MANAGER`, `ANALYST`,
                        # `CHECKER`. The agent is the column's subject and reads as a label.
                        esc(str(r.get("agent_id") or "").upper()),
                        # `ARCHITECTURE_UPDATE.md` §5.6: a truncated summary **with the model
                        # appended**. The model was the missing field, and it is the one that makes
                        # the log answer the question it is read for — which model was this saved
                        # against. Read from the row's own snapshot, so a later seed correction
                        # cannot retroactively change what an old entry says it was saved with.
                        f"{esc(r.get('action'))} — "
                        f"{esc(', '.join(r.get('changed_fields') or []) or 'no field changed')}"
                        f" (v{esc(r.get('version'))})"
                        + _history_model(r),
                    ]
                    for r in rows
                ],
                empty=empty_state(
                    "Nothing has been changed yet.",
                    "Save, restore or freeze an agent to start the log.",
                ),
            )

        async def _save(agent_id, role, prompt_text, prov, mname, temp, mode):
            from twinlab.services.agent_config import AgentFrozen, save_agent

            try:
                await save_agent(
                    agent_id,
                    {
                        "role": role,
                        "system_prompt": prompt_text,
                        "model": {"provider": prov, "name": mname, "temperature": float(temp)},
                        "output_mode": mode,
                    },
                )
            except AgentFrozen as exc:
                return f"**Refused.** {exc}", await _changelog()
            except Exception as exc:  # noqa: BLE001 — surface the validation reason verbatim.
                return f"**Not saved.** {exc}", await _changelog()
            return "Saved.", await _changelog()

        save.click(
            _save,
            inputs=[selected, purpose, prompt, provider, model_name, temperature, output_mode],
            outputs=[stamp, changelog],
        )

        async def _restore(agent_id):
            from twinlab.services.agent_config import AgentFrozen, restore_agent

            try:
                await restore_agent(agent_id)
            except AgentFrozen as exc:
                return f"**Refused.** {exc}", await _changelog()
            return "Original text restored.", await _changelog()

        restore.click(_restore, inputs=selected, outputs=[stamp, changelog])

        async def _freeze(agent_id):
            from twinlab.services.agent_config import AgentFrozen, load_agent, set_frozen

            current = await load_agent(agent_id)
            try:
                after = await set_frozen(agent_id, not current.frozen)
            except AgentFrozen as exc:
                return f"**Refused.** {exc}", await _changelog()
            state = "frozen for the main study" if after.frozen else "unfrozen"
            return f"Now {state}.", await _changelog()

        freeze.click(_freeze, inputs=selected, outputs=[stamp, changelog])

        load_once(_load, inputs=selected, outputs=outputs)
        load_once(_changelog, outputs=changelog)


__all__ = ["render_agent_studio"]
