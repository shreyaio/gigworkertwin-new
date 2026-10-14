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
    """The *Quality Checker* view: the codebook policy beside the design agent's framing.

    One row per area. The left column is what the codebook says this version commits to. The right
    column is the paragraph the design agent wrote for that area, as stored. Nothing is scored here.
    """
    if not view.get("rendered"):
        return empty_state(
            f"{view['version_code']} has not been rendered.",
            "Render it in Twin Studio, or on the Dial board, before it can be compared.",
        )
    rows = []
    for r in view["rows"]:
        if r["status"] == "fixed":
            policy = esc("No change in this area.")
            framed = _absent()
        else:
            policy = "<br>".join(esc(c) for c in r["policy"]) or _absent()
            if r["status"] == "ok" and r["framed"].strip():
                framed = esc(r["framed"])
            else:
                framed = status_dot("failed", f"refused: {r.get('reason') or 'no reason given'}")
        rows.append([esc(r["lever"]), policy, framed])
    return data_table(
        ["Area", "Codebook policy (what this version commits to)", "How the agent framed it"],
        rows,
    )


def _twin_html(view: dict) -> str:
    """The *Twin Interviewer* view: what the driver said and what the twin said.

    The twin column is the twin acting on this version. A failed twin leaves that column *Not
    tested* and says why in the note; it is never filled with a number (I13, I17).
    """
    body = ""
    if view.get("note"):
        body += f'<div class="tl-card">{esc(view["note"])}</div>'
    return body + data_table(
        ["Item", "Question", "Driver said", "Twin said"],
        [
            [
                esc(item["item_id"]),
                esc(f"{item['question']} (answer 1 to {item['points']})"),
                str(item["driver"]) if item["driver"] is not None else _absent(),
                str(item["twin"]) if item["twin"] is not None else _absent(),
            ]
            for item in view["items"]
        ],
    )


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
    """The *Policy Designer* view: the paragraph the design agent wrote for each area, now.

    Words are shown against the band the brief allowed, so a paragraph that ran long or short is
    visible at a glance. A refusal is shown as a refusal, with its reason, and is not replaced by
    anything.
    """
    rows = []
    for r in view["rows"]:
        if r["status"] == "fixed":
            status = status_dot("pending", "fixed text")
        elif r["status"] == "ok":
            status = status_dot("complete", "written")
        else:
            status = status_dot("failed", f"refused: {r['reason']}")
        words = "—" if r["words"] is None else f"{r['words']} (band {r['band'][0]}–{r['band'][1]})"
        rows.append(
            [
                esc(r["lever"]),
                esc(str(r["dial"])),
                esc(r["text"]) or _absent(),
                esc(words),
                status,
            ]
        )
    return (
        '<div class="tl-card">Nothing was stored. These are new drafts from the prompt in the box. '
        "The paragraphs a twin is shown are the ones already in the render cache.</div>"
        + data_table(["Area", "Dial", "Paragraph the design agent wrote", "Words", "Status"], rows)
    )


def _in_force_line(view: dict) -> str:
    """What this agent is actually run with, and where each value comes from.

    Stated whether or not it differs from the seed — a researcher reading a temperature needs to
    know which temperature it is every time, not only on the screens where two numbers happen to
    disagree.

    **The closing sentence was false from M19 WP-8 and is now the opposite.** It read *"Editing
    the boxes above changes the stored record and the audit log; it does not change what the
    runtime loads."* That was true while every call site built its agent from
    `config/agents.default.yaml`; the five call sites now read `registry.live_agent_configs`, so
    a save governs the next session, gate, Studio ask and validity test. Leaving the old sentence
    would be worse than the original defect: it would tell a researcher their edit is inert at
    the moment it starts changing results.
    """
    force = view.get("in_force") or {}
    if not force.get("model_name"):
        return ""
    version = force.get("version")
    if version is None:
        head = "Actually in force (the shipped default, nothing saved here yet): "
    elif force.get("differs_from_seed"):
        head = f"**Actually in force — your saved version {version}, not the shipped default.** "
    else:
        head = f"Actually in force (saved version {version}): "
    temperature_note = (
        " The twin's temperature is set in Twin Lab → Settings, because it is frozen onto "
        "every session and is the subject of validity test 8."
        if view.get("temperature_read_only")
        else ""
    )
    return (
        f"{head}`{force['provider']}` · `{force['model_name']}` · "
        f"temperature **{force['temperature']}**  \n"
        f"<small>Read from {esc(force['source'])}. Editing the boxes above and saving changes "
        "what the next session, quality gate, Studio ask and validity test actually do, and the "
        f"version is frozen onto every run that used it.{esc(temperature_note)}</small>"
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

    ``prompt_box`` is the *What this agent is told* textarea, passed in so a test runs the prompt
    **as it is in the box**, edited or not, without the edit having to be saved first.

    The three model-calling tests (Twin, Policy Designer, Quality Checker) run as background jobs.
    *Test this agent* starts one and returns at once; *Show the result* reads it back. A model call
    on the handler's own path would hold the screen for the whole call (`CLAUDE.md` rule 12).
    """
    gr.HTML(section_title("Test this agent"))
    with gr.Row():
        twin_for_test = gr.Dropdown([], label="Twin", value=None)
        version_for_test = gr.Textbox(value="01000", label="Version")
    with gr.Row():
        run_test = gr.Button("Test this agent", variant="secondary")
        show_test = gr.Button("Show the result", variant="secondary")
    job = gr.State(None)
    test_out = gr.HTML("")

    async def _test(agent_id: str, twin_id: str | None, version_code: str, prompt_text: str):
        from twinlab.services.agent_config import start_agent_test

        if agent_id == "manager":
            # Builds a plan and starts nothing (docs/06 §6). No session is created here, and no
            # model is called, so it stays on the handler's own path.
            from twinlab.services.agent_config import manager_log_preview, manager_plan

            plan = await manager_plan(version_code)
            html = (
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
            return html, None

        if agent_id == "analyst":
            # The reading the analyst wrote for this version, beside the computed numbers it was
            # given: the six movements, the index and the floors. It is read from the stored result:
            # the analyst's input is a cell's computed shifts, which exist only once a cell has run,
            # so this screen shows the reading rather than calling the model.
            from twinlab.services.results import results_panel

            from ..components import metric_bars

            if not version_code:
                return empty_state("No version given.", "Type a version code above."), None
            panel = await results_panel(version_code)
            numbers = metric_bars(panel.bars)
            if not panel.analysis:
                return (
                    numbers
                    + empty_state(
                        "No reading for this version yet.",
                        "The analyst writes one when the cell completes.",
                    ),
                    None,
                )
            return numbers + f'<div class="tl-card">{esc(panel.analysis)}</div>', None

        if agent_id == "checker":
            # Reads the codebook and the stored render, and calls no model, so it runs here.
            from twinlab.services.agent_config import checker_test_view

            return _checker_html(await checker_test_view(version_code or "")), None

        if agent_id not in ("twin", "design"):
            return empty_state("Nothing to test.", "Select an agent on the left."), None
        if agent_id == "twin" and not twin_id:
            return empty_state("No twin selected.", "Choose a twin above to test this agent."), None

        started = start_agent_test(
            agent_id,
            twin_id=twin_id,
            version_code=version_code or "",
            prompt_text=prompt_text or "",
        )
        return (
            '<div class="tl-card">Running. The model is asked in the background and this takes a '
            "while. Press <b>Show the result</b> when it is done.</div>",
            started,
        )

    run_test.click(
        _test,
        inputs=[selected, twin_for_test, version_for_test, prompt_box],
        outputs=[test_out, job],
    )

    async def _show(started: str | None):
        from twinlab.services.agent_config import agent_test_result

        if not started:
            return empty_state("Nothing has been tested yet.", "Press Test this agent first.")
        result = agent_test_result(started)
        if result["status"] == "running":
            return (
                '<div class="tl-card">Still running. Press Show the result again in a moment.</div>'
            )
        if result["status"] == "unknown":
            return empty_state(
                "That test is no longer in memory.", "Press Test this agent again."
            )
        if result["status"] == "failed":
            from ..components import error_state

            message = result["view"]["error"]
            return error_state("Could not run this test.", "test", message)
        view = result["view"]
        renderers = {"twin": _twin_html, "design": _design_html}
        return renderers[result["agent_id"]](view)

    show_test.click(_show, inputs=job, outputs=test_out)

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
                # WP-8 item 5. The twin's temperature is owned by `app_config['twin']` (Twin Lab
                # → Settings), because that is the value a session freezes onto its config column
                # and the subject of validity test 8. The box showed `1` while the twin ran at
                # 0.25; now it shows the value in force and **cannot be edited here**, so there is
                # one owner rather than a control whose number the runtime discards.
                gr.update(
                    value=v["temperature"],
                    interactive=not v["temperature_read_only"],
                    label=(
                        "Temperature (set in Twin Lab → Settings)"
                        if v["temperature_read_only"]
                        else "Temperature"
                    ),
                ),
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

            # WP-8 item 5, completed. The twin's temperature box is read-only and shows the value
            # in force from `app_config['twin']`, so sending it here would copy that number into
            # the `agent_configs` row and leave two places holding it — the very shape of problem
            # the read-only box removed. The key is omitted instead and `save_agent` merges `model`
            # field-by-field, so the row keeps whatever temperature it had. One owner, one place.
            ref = {"provider": prov, "name": mname}
            if agent_id != "twin":
                ref["temperature"] = float(temp)
            try:
                await save_agent(
                    agent_id,
                    {
                        "role": role,
                        "system_prompt": prompt_text,
                        "model": ref,
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
