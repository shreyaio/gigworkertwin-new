# 04 — Frontend (Gradio)

**Content and ordering in this document are mandatory.** Styling may degrade where Gradio cannot do
something; content may not. If a layout is unachievable, render the same content in a plainer
container — never drop it, never reorder it.

## 1. App shell

```python
# src/twinlab/ui/app.py
def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Twin Lab", theme=TWINLAB_THEME, css=TWINLAB_CSS) as demo:
        header()                                   # title + "Mock model" / "Live model" badge
        with gr.Tabs():
            with gr.Tab("Logs"):       logs.render()
            with gr.Tab("Dial board"): dialboard.render()
            with gr.Tab("Twins"):      twins.render()
            with gr.Tab("Results"):    results.render()
            with gr.Tab("Settings"):   settings.render()
        subheader_links()                          # "Driver survey: open | Synthetic generator: open"
    return demo
```

Tab order is fixed: **Logs · Dial board · Twins · Results · Settings.**

## 2. Reusable components

`src/twinlab/ui/components/`. Every one is a function returning Gradio components plus an update
function. Nothing below is defined twice anywhere in the app.

| Component | File | Used by |
|---|---|---|
| `status_dot(status)` | `status.py` | logs, dial board, twins, quality |
| `version_code_display(code)` | `version.py` | dial board, results, twins |
| `dial_row(lever, value)` | `dials.py` | dial board |
| `what_twins_are_told(code)` | `told.py` | dial board, results panel, twins panel |
| `scenario_text_block(variant)` | `scenario.py` | results panel, twins panel, quality |
| `metric_bars(shifts, index)` | `metrics.py` | dial board, results panel |
| `twin_table(twins, selectable)` | `twin_table.py` | twins tab, quality page |
| `answer_compare(baseline, variant)` | `compare.py` | twins panel |
| `log_tree(events)` | `log_tree.py` | logs tab, quality page |
| `side_panel(title, body)` | `panel.py` | logs, twins, results |
| `cached_badge()` | `badges.py` | dial board |
| `search_box(placeholder)` | `search.py` | results |

**`what_twins_are_told` is one component used in three places.** The dial board, the Results side
panel and the Twins side panel must show identical text for the same code. One function, one source
(`gaps.commitment` for the selected gap ids), no drift.

## 3. Tab 1 — Logs

### 3.1 Navbar (top of tab, one row)

Left to right, all present:

| Control | Type | Behaviour |
|---|---|---|
| Session | `gr.Dropdown` | Previous sessions, newest first. Selecting loads its events. |
| Session name | `gr.Textbox` | Name for a new session. |
| Iterations | `gr.Number` | How many version codes this session runs. Min 1, max 243. |
| Start code | `gr.Textbox` | Default `10000`. Validated as 5 digits in 0–2. |
| **Create** | `gr.Button` primary | `POST /api/sessions`. |
| **Start / Resume** | `gr.Button` primary | Label flips to *Resume* when the selected session is `paused` or `stopped`. |
| **Stop** | `gr.Button` secondary | Cooperative stop. |
| **Delete** | `gr.Button` stop-variant | Confirms first. |

A session stopped mid-sweep and restarted **continues from `cursor_index`** — the button says
*Resume*, and the first new log line names the code it is resuming at.

### 3.2 Layout

```
┌── navbar ─────────────────────────────────────────────────────────┐
├── status strip: ● running · 7/20 twins · cell 3 of 10 · 01000 ────┤
├─────────────────────────┬─────────────────────────────────────────┤
│  LOG TREE  (scale=5)    │   SIDE PANEL  (scale=4)                 │
│  scroll, live           │   gr.Accordion, collapsible             │
└─────────────────────────┴─────────────────────────────────────────┘
```

### 3.3 The log tree

`gr.HTML` inside a scrollable wrapper, refreshed by `gr.Timer(1.0).tick`. Each parent event is one
row; children are hidden until the row is selected.

```
● ingestion                                    ok      21:12:44
● reconstruction (T07)                    running      21:12:45   ← label rewrites in place
● lookup 01000                                 ok      21:12:46
● render 01000                            running      21:12:47
○ check
○ ask
○ analyse
```

- `●` green = `ok`, amber = `running`, red = `error`, grey `○` = pending.
- The **reconstruction row's label updates in place** as twins are built — one row, changing
  twin id, exactly as specified. Same for `ask (T12)`.
- Rows are clickable. Clicking writes the `event_id` into a hidden `gr.Textbox`, whose `.change`
  loads the side panel.

**Polling:** `GET /api/sessions/{id}/events?after_id=N` returns only new rows; the component keeps
the rendered tree in `gr.State` and appends. Never re-fetch the whole stream.

### 3.4 The side panel

Opens on row click. Contents depend on the stage, but **always** in this order:

1. **Header** — stage, agent, status dot, timestamp, duration.
2. **Children** — one `gr.Accordion` per child event, stacked vertically, collapsed by default.
3. **Telemetry** — model, prompt tokens, completion tokens, latency, `logfire_span_id`.
4. **Raw** — `input` and `output` JSON, in a collapsed Accordion.

Per stage:

| Stage | Children are | Expanding a child shows |
|---|---|---|
| `reconstruction` | `T01`, `T02`, … | **the reconstructed passage in full**, as plain text |
| `lookup` | the DeltaSpec | gap ids per lever, the commitments, `delta_hash` |
| `render` | `L1`…`L5` | the paragraph, word count, cache hit/miss |
| `check` | the five gates | coverage per commitment, containment hits, band result |
| `ask` | `T01`, `T02`, … | the 37 answers, the lever order shown, seed, wording |
| `analyse` | metrics, interactions, analysis | shifts, index, the written analysis |

This is the requirement "every agent status, routing, decision should be visible" — routing
decisions are `stage='control'` events emitted by the Manager with the decision in `payload`.

## 4. Tab 2 — Dial board

### 4.1 Layout

```
┌── warning strip (red, only when code == 00000) ───────────────────┐
│  "Turn at least one dial above 0."                                │
├───────────────────────────────────┬───────────────────────────────┤
│  DIALS (scale=5)                  │  VERSION CODE (scale=4)       │
│   Pay            [0][1][2]        │        0 1 0 0 0              │
│   Conditions     [0][1][2]        │   Fairwork score 1 of 10      │
│   Contracts      [0][1][2]        │                               │
│   Management     [0][1][2]        │   What the twins are told     │
│   Representation [0][1][2]        │   • Conditions step 1. …      │
│   [ Ask the twins ]  (+ badge)    │   (scrollable)                │
├───────────────────────────────────┴───────────────────────────────┤
│  RESULTS: "Version 01000: change compared with Uber today (17 twins)"│
│  Fairness ▕▏ +0.00   Clarity ▕▎ +0.07  …  Index 0.143              │
└───────────────────────────────────────────────────────────────────┘
```

### 4.2 Live update

Each dial is a `gr.Radio(choices=[0,1,2])` styled as a segmented control. Any dial `.change` fires
one handler that updates **both** the version code display **and** "What the twins are told", from
local reference data — **no network call, no LLM**. This must feel instant.

```python
def on_dial_change(*dials) -> tuple:
    code = "".join(str(d) for d in dials)
    spec = lookup(code)                                  # pure, in-process
    return (code, digit_sum(code), told_markdown(spec), gr.update(visible=(code == "00000")))
```

`told_markdown` renders one bullet per lever at dial > 0:

> **Conditions step 1.** The platform now provides safety equipment and training free of charge,
> supports you when you work alone, and covers significant costs from work related accidents or
> illness.

Text comes from `gaps.commitment`, summarised per threshold — **never** the raw gap id, never the
word "Fairwork", "threshold" or "score" in the twin-facing phrasing.

### 4.3 "Ask the twins"

```
click
  ├─ cache hit  → render results + amber "cached" badge + [ Rerun? ] button beside the main button
  └─ cache miss → create + start session, show "running…", poll, render when complete
```

`Rerun?` creates a **new session** (visible in the Logs tab like any other), re-asks the twins, and
its result becomes `is_latest_for_version`. The superseded run is retained (I9).

`00000` is blocked from this button by the warning strip — it is a control cell run by the
orchestrator, not by hand.

### 4.4 Results block

Per metric: label, a centred divergent bar (zero in the middle, green right, red left), signed value
to 2 dp. Then `Index 0.143` and the sentence `Drivers would stay. Green means better for drivers.`
Derived from the sign of `staying` and `leaving` shifts.

## 5. Tab 3 — Twins

### 5.1 Top block — quality test entry

A single full-width card, **above everything else on the tab**:

```
┌──────────────────────────────────────────────────────────┐
│  Run twin quality test                               →   │
└──────────────────────────────────────────────────────────┘
```

Clicking navigates to the **quality page** (§6). Gradio has no router, so this is a
`gr.Group(visible=…)` swap within the tab: the main view hides, the quality view shows, and a
`← Back to twins` button reverses it. Functionally a page; mechanically a visibility toggle.

### 5.2 Main view

Twin list and side panel are **at the same level**, side by side, both below the card above.

```
┌── Run twin quality test  → ──────────────────────────────┐
├──────────────────────────┬───────────────────────────────┤
│  TWIN LIST (scale=5)     │  TWIN SIDE PANEL (scale=5)    │
│  Twin Service City Age Q │  ...                          │
└──────────────────────────┴───────────────────────────────┘
```

List columns, in order: **Twin · Service · City · Age · Quality**. Quality renders as a pill —
green `Kept (0.56)` / red `Dropped (1.1)` — from `twin_quality_runs` where `is_latest`.

### 5.3 Twin side panel — exact order

1. **Twin id and one-line identity** — `Uber Go (cab) driver in Mumbai, 41 years, Man, 38 months on Uber, about 72 hours a week.`
2. **Vehicle / background line** — `Full time cab driver repaying a car loan.`
3. **Quality line** — `Quality test: average error 0.56, 94% within 1 point.`
4. **Reconstructed passage** — `gr.Accordion("Reconstructed persona", open=False)`; expanding shows
   the full passage as plain text.
5. **Compare with version** — `gr.Dropdown` listing **only version codes that have a completed run**
   (from `runs where is_latest_for_version and status='completed'`), newest first.
6. **Scenario text** — immediately below the dropdown, a short block showing the rendered scenario
   for the selected version, so the reader sees what the twin was told before reading the answers.
7. **Answer comparison**, one table per block, in battery order: *Managed by the app* (AMQ) ·
   *Feels controlled* (PAC) · *Fairness* · *Clarity* · *Job* · *Staying* · *Working around* ·
   *Leaving* · *Income*.

Comparison table columns: **Item · Question · Driver · Twin today · Twin, version NNNNN**.

- *Driver* = the human's own survey answer.
- *Twin today* = the twin's answer under `00000`.
- *Twin, version NNNNN* = the twin's answer under the selected code.

**No "twin reason" column and no reason boxes.** Likert questions and numbers only.

Items not shown to the twin in a given round are marked `hidden` under the item id, matching the
mock.

## 6. The quality-test page

Reached from §5.1. Two blocks, side by side.

```
┌── ← Back to twins ──── [ Select ] [ Run selection ] [ Run all ] ──┐
├────────────────────────────┬──────────────────────────────────────┤
│  TWIN LIST (scale=5)       │  RUN LOG (scale=5)                   │
│  ☐ T01 … Kept (0.56)       │  log_tree for THIS quality session   │
└────────────────────────────┴──────────────────────────────────────┘
```

- **Select** toggles selection mode: the list gains a checkbox column. Twins may be checked in any
  order; the order of checking is preserved and is the run order.
- **Run selection** runs the holdout test for checked twins only.
- **Run all** runs it for every consented twin.
- The right block is the same `log_tree` component as the Logs tab, scoped to the quality session.

**What the test does** (see `docs/02` §7): the persona is passed to the model, which sees the six
holdout versions **for the first time** and answers them from the persona alone. Its 18 numbers are
compared to the driver's. Scores are written to `twin_quality_runs`, the previous `is_latest` is
demoted, and **every surface reading quality updates** — the list here, the list on the Twins tab,
the identity line in the side panel, and `twins_n` in the analyst — because they all read the same
`is_latest` row. There is no second copy to invalidate.

## 7. Tab 4 — Results

### 7.1 Grid

9 rows (`pay × conditions`) × 27 columns (`contracts × management × representation`) = 243.

- Cell fill = index value on a white → green scale; untested = grey.
- **Red outline** on `00000` ("Uber today"). **Gold outline** on the current best index.
- **Hover** shows `version code · index` as a tooltip.
- **Click** opens the side panel for that code.

**Primary implementation:** `gr.Dataframe` 9×27 with `.select()` — `SelectData.index` gives
`(row, col)`, and

```python
code = f"{row // 3}{row % 3}{col // 9}{(col // 3) % 3}{col % 3}"
```

Styling via a pandas `Styler` background gradient. This is guaranteed to work in Gradio and gives
click plus native hover.

**Enhancement (optional):** a Plotly heatmap in `gr.Plot` gives nicer tooltips. Use it only if
`.select()` is confirmed working on the installed Gradio version; otherwise keep the Dataframe. Do
not ship a grid without click handling.

### 7.2 Interactions panel

Beside the grid. Renders only computable interactions (`docs/02` §8.3):

> **Minimum pay and safety cover:** staying changes +0.31 and +0.09 alone, +0.22 together. The extra
> is −0.18, so together they add less than the sum.

Where a leg is missing, it names the code to run instead of estimating.

### 7.3 Tested versions table

Below the grid, unchanged from the mock, **plus a search box**. Columns: Version · Score · Twins ·
Fairness · Clarity · Happiness · Staying · Pushback · Leaving · Index. Sorted by index descending.
Search filters on version code substring. The table is scrollable within a fixed-height container.

### 7.4 Side panel — exact order

Collapsible, opens on grid click:

1. **Version code**, large, with Fairwork score.
2. **What the twins are told** — the same component as the dial board.
3. **Scenario text** — the latest cached rendered text for this version, five lever paragraphs.
4. **Numeric results** — the six shifts, the six baseline means, the index, `twins_n`, and the
   `SHAM − 00000` floor for context.
5. **LLM analysis** — `runs.llm_analysis`, rendered as markdown.

This is deliberately the same bundle the Analyst received (`docs/02` §8.4), in the same order, so
the researcher can read the input and the output together.

## 8. Settings tab

Deferred by the researcher, but the fields exist in the mock and the backend needs them. Build the
form and wire it to `PUT /api/config/twin`; leave refinement for later.

Twin model · AI provider · Model name · Temperature · Wordings · Runs per wording · Quality test runs
per twin · **Save settings**. Right column: data source (real / synthetic / both), **Import twins
from the survey**, **Clear runs and load demo twins**, **How many survey twins are available?**

Import uses only completed surveys where the driver agreed to having a twin (consent statement 7).

## 9. Styling

```css
/* src/twinlab/ui/theme.py -> TWINLAB_CSS */
:root{
  --tl-blue-900:#0B1F3A; --tl-blue-600:#1D4ED8; --tl-blue-50:#EFF5FF;
  --tl-green-600:#15803D; --tl-green-50:#ECFDF5; --tl-amber-500:#F59E0B;
  --tl-red-600:#DC2626; --tl-grey-700:#374151; --tl-grey-200:#E5E7EB;
}
.tl-scroll{ max-height:520px; overflow-y:auto; }
.tl-resize{ resize:vertical; overflow:auto; min-height:220px; }   /* vertical only; Gradio limit */
.tl-panel{ border:1px solid var(--tl-grey-200); border-radius:10px;
           background:#fff; padding:14px; transition:box-shadow .15s ease-out; }
.tl-panel:hover{ box-shadow:0 2px 10px rgba(11,31,58,.06); }
.tl-dot{ width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:8px; }
.tl-dot.ok{background:var(--tl-green-600)} .tl-dot.running{background:var(--tl-amber-500);
  animation:tl-pulse 1.2s infinite} .tl-dot.error{background:var(--tl-red-600)}
.tl-dot.pending{background:var(--tl-grey-200)}
@keyframes tl-pulse{0%,100%{opacity:1}50%{opacity:.35}}
.tl-logrow{ cursor:pointer; padding:6px 10px; border-radius:6px; transition:background .15s ease-out; }
.tl-logrow:hover{ background:var(--tl-blue-50); }
.tl-badge-cached{ background:var(--tl-amber-500); color:#fff; border-radius:999px;
                  padding:2px 10px; font-size:12px; }
```

Apply with `elem_classes=["tl-panel","tl-scroll"]`. Every panel the spec calls scrollable gets
`tl-scroll`; every one called resizable gets `tl-resize`.

**Honest limits, already accepted:** no drag splitters, no free-floating windows, vertical-only
resize. Horizontal proportions come from `gr.Column(scale=…)`.

## 10. Frontend rules

1. **No business logic in `ui/`.** A handler calls a service and formats the result. Metric maths,
   lookups and hashing live in `analysis/`, `variant/`, `persona/`.
2. **No LLM call in a handler's synchronous path.** Enqueue, return, let the Timer poll.
3. **One source per value.** "What the twins are told" has one implementation used in three places.
4. **Every list that can grow is paginated or scroll-capped.** 243 rows, 20 twins, thousands of
   events.
5. **Never render a metric the backend did not compute.** No client-side arithmetic on shifts.
