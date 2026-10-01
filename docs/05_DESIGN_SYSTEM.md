# 05 — Design system

Tokens, motion, components, states, accessibility, and the Gradio mechanics that deliver them.

Normative for **tokens, component names, states and the three semantic rules in §7**. Advisory for
exact pixel values.

---

## 1. What this interface is

A research console. The prototype is information-dense on purpose: a researcher operating a
243-cell sweep needs to see counts, statuses and numbers at a glance, not one card per screenful.

**Reproduce the prototype.** Not only its density and hierarchy — its typeface, its palette, its
box geometry. Every value in §2 was *measured* off
`additional_data/screenshots of the prototype - Google Docs.pdf`, not chosen. This reverses the
earlier rule ("reproduce the hierarchy, not the Apps Script styling"); `docs/DECISIONS.md` →
**D-UI-01** records why.

Four consequences:

- **Tables over cards** wherever there is more than one row of the same thing.
- **Numbers are right-aligned and tabular-figured.** A column of shifts must be scannable.
- **Nothing is hidden behind a hover.** Hover may *add* (a tooltip with provenance); it may never
  be the only way to read a value. `docs/06` restates this per screen.
- **Where the prototype and a rule in this document disagree, the rule wins.** The prototype has
  no `00000` warning strip and labels agents `rules only`; §7 rule 3 and `docs/06` §6 override
  both. Visual parity is not licence to reintroduce a content decision that was made against it.

And one more, which is the point of the whole product: **the chain is inspectable.** Every number
on every screen can be traced to what produced it, in at most two clicks.

---

## 2. Tokens

`src/twinlab/ui/theme.py` → `TWINLAB_CSS`. Defined once as CSS custom properties; never a literal
hex in a component.

### 2.1 Colour

The prototype is built on Google's Material neutrals with **one accent per app**. The accent is
not decoration: it is how a researcher knows, at a glance and without reading the title, which of
the eight apps they are in.

```css
:root{
  /* neutrals, sampled off the screenshots */
  --tl-grey-900:#202124;   /* body text, section headings */
  --tl-grey-700:#3C4043;   /* secondary body */
  --tl-grey-500:#5F6368;   /* captions, inactive tabs, sub-labels */
  --tl-grey-300:#DADCE0;   /* input borders, pill-group outline */
  --tl-grey-200:#E9EAED;   /* card border */
  --tl-grey-100:#ECEDEF;   /* rules, table row separators */
  --tl-grey-50 :#F8F9FA;   /* page background */
  --tl-white   :#FFFFFF;
}
```

**Per-app accent.** Each route carries a `tl-route-<name>` class that re-points four variables:
`--tl-accent`, `--tl-accent-dark` (the page title), `--tl-accent-tint` (table headers, badges)
and `--tl-accent-wash` (the header gradient). `ROUTE_ACCENTS` in `theme.py` is the only place the
mapping exists; `page_classes(path)` is the only way a page gets it, and an unknown path raises.

| Route | Accent | Base | Dark | Tint |
|---|---|---|---|---|
| `/` Main menu, `/survey` Driver survey | blue | `#3F72E9` | `#2D4DA7` | `#E9F0FE` |
| `/lab` Twin Lab | green | `#2B8043` | `#1E6332` | `#EEF5F0` |
| `/generator` Generator | purple | `#9130E7` | `#7524BC` | `#F3EDF9` |
| `/studio` Twin Studio | orange | `#DD7100` | `#B85C00` | `#FCF4EB` |
| `/agents` Agent Studio | teal | `#30838F` | `#24646D` | `#EAF2F4` |
| `/statistics` Statistics | indigo | `#4950B6` | `#383E93` | `#EDEEF8` |
| `/research` Research model | red | `#BA221B` | `#8F1A14` | `#FAEEED` |

The accent drives: the page title, the 2px rule under the header, the 3px bar on every section
heading, the active nav underline, the primary button fill, the table header tint, and the focus
ring.

**Semantic colours do not follow the accent.** They mean the same thing on every screen:

```css
--tl-ok  :#308038;  --tl-ok-tint  :#E7F4EA;  /* Kept, PASS, complete, good for the driver */
--tl-warn:#E8A33D;  --tl-warn-tint:#FCF7E0;  /* running, cached, CHECK */
--tl-bad :#CD3021;  --tl-bad-tint :#FAE8E6;  /* Dropped, FAIL, bad for the driver */
--tl-info:#3F72E9;  --tl-info-tint:#E9F0FE;  /* links, neutral notices */
--tl-gold:#C79A00;                           /* best index outline on the 243 grid */
```

Twin Lab's accent is green and `--tl-ok` is green, and that collision is in the prototype too.
It is tolerable only because **no metric bar, pill or verdict is ever colour alone** (§6): every
one carries `Kept (0.56)`, `PASS`, `+1.62`. Read §7 rule 2 before touching either value.

Dial states are a traffic light for protection level, matching the prototype's legend:

```css
--tl-dial-0:var(--tl-bad);    /* 0 = as Uber is today */
--tl-dial-1:#F0B429;          /* 1 = some protection  */
--tl-dial-2:var(--tl-ok);     /* 2 = more protection  */
```

### 2.2 Type

**Roboto**, as the prototype, loaded from Google Fonts through `gr.Blocks(head=FONT_HEAD)` with
`display=swap`.

```css
--tl-font: Roboto, "Helvetica Neue", Arial, "Segoe UI", system-ui, sans-serif;
--tl-mono: "Roboto Mono", ui-monospace, "Cascadia Mono", Menlo, monospace;

--tl-fs-xs:11px; --tl-fs-sm:12px; --tl-fs-md:13px;    /* md is body: dense by design */
--tl-fs-lg:15px; --tl-fs-xl:18px; --tl-fs-2xl:24px; --tl-fs-code:32px;  /* version code */
--tl-lh-tight:1.25; --tl-lh-body:1.5;
```

The earlier version of this section banned a webfont, on the grounds that a Space cold-starting
on free hardware should not wait on one. That reason still holds and is answered rather than
ignored: the fallback stack is complete, `display=swap` paints in it immediately, and the font
swaps in when it lands. **The font must never gate first paint** — if it ever does, drop the
`<link>`, not the fallback.

**All numerals use `font-variant-numeric: tabular-nums`.** Without it a column of `+1.62 / -0.98 /
+0.07` does not align and cannot be scanned.

Version codes render in **`--tl-font` at `--tl-fs-code`, weight 700, `letter-spacing:.16em`**,
centred — exactly as the prototype's `2 0 0 0 0`. They are *not* monospaced; the prototype sets
them in Roboto Bold and the tracking is what makes five digits read as one identifier.

### 2.3 Space, radius, elevation

```css
--tl-s1:4px; --tl-s2:8px; --tl-s3:12px; --tl-s4:16px; --tl-s5:24px; --tl-s6:32px;
--tl-r-sm:4px; --tl-r-md:8px; --tl-r-pill:999px;
--tl-shadow-card:none;
--tl-shadow-hover:0 1px 3px rgba(60,64,67,.16);
--tl-shadow-panel:0 2px 10px rgba(60,64,67,.20);
```

Lower chrome than v1.0. The prototype's cards are **a 1px `--tl-grey-200` border and an 8px
radius with no resting shadow** — the shadow appears on hover and on anything that floats. A card
that is raised at rest reads as a control; in a screen of thirty cards, nothing should.

---

## 3. Motion

Transitions make state changes legible in an interface where a lot changes at once. They must never
gate data.

```css
--tl-dur-fast:120ms;   /* hover, focus, dial select */
--tl-dur-base:180ms;   /* tab change, badge, row expand */
--tl-dur-slow:260ms;   /* panel open, route cross-fade */
--tl-ease:cubic-bezier(.2,.7,.3,1);
```

| Element | Motion |
|---|---|
| Button, row, card hover | background + shadow, `--tl-dur-fast` |
| Dial select | pill slides to the chosen segment, `--tl-dur-fast` |
| Tab / route change | 8px rise + fade in, `--tl-dur-base` |
| Accordion, log row expand | height + opacity, `--tl-dur-base` |
| Side panel open | slide from right + fade, `--tl-dur-slow` |
| Running status dot | 1.2 s opacity pulse, infinite |
| Metric bar | width grows from the centre line on first paint, `--tl-dur-slow` |
| 243-grid cell fill | fade on value arrival, `--tl-dur-base` |
| Counter update | brief `--tl-blue-50` flash, then fade |

Three rules:

1. **Motion never delays content.** Data renders immediately; the transition decorates its arrival.
   A spinner that outlives its data is a bug.
2. **Nothing moves on a timer poll unless the value changed.** The log tree ticks every second; if
   every tick re-animated, the page would never settle. Diff, then animate only the delta.
3. **`prefers-reduced-motion` is honoured.**

```css
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{ animation-duration:.01ms !important;
                        transition-duration:.01ms !important; }
}
```

---

## 4. Components

`src/twinlab/ui/components/`. Every one is a function returning Gradio components plus an update
function. **Nothing below is defined twice anywhere in the app.**

### 4.1 Shell

| Component | Notes |
|---|---|
| `app_header` | Title in `--tl-accent-dark`, subtitle, model badge, build line right. Accent wash behind, 2px accent rule beneath. The badge is accent-tinted for a mock model and **red for a live one** — it is the only thing on screen saying whether a press costs money |
| `global_nav` | The prototype's text strip: `&lsaquo; Main menu` then the seven apps, active one in the accent with a 2px underline. `gr.Navbar` is mounted but hidden — `demo.route()` makes the URLs real, and Gradio's own strip carries neither the underline nor the back link |
| `sub_nav` | `gr.Tabs` within a section, as underlined text tabs (Twin Lab's 8) |
| `tl-pilltabs` | The same `gr.Tabs`, as the prototype's outline-pill strip (Statistics' 10) |
| `section` | **3px accent bar · near-black title · optional grey one-liner.** The prototype opens every region this way, and this is the component that makes Twin Lab read green and Twin Studio orange |
| `section_card` | White surface, 1px border, 8px radius, title |

`page_classes(path)` returns `["tl-page", "tl-route-<accent>"]` and every page wrapper uses it.
A page that builds its own `elem_classes` list is a bug: the accent would silently fall back to
the Main menu's blue and the screen would look like a different app's.

### 4.2 Primitives

`pill` · `status_dot` · `badge_cached` · `btn_primary` · `btn_secondary` · `btn_danger` ·
`confirm_dialog` · `empty_state` · `error_state` · `loading_state` · `help_accordion`

Status dots are 8px circles: **green = complete, amber = running, red = failed, grey = pending** —
always beside a text label, never alone (§6).

### 4.3 Fields

`field_text` · `field_number` · `field_slider` (label + slider + live numeric) · `field_dropdown` ·
`field_textarea` · `field_checkbox` · `field_weight_row`

Every slider shows its numeric value beside it and its anchor labels beneath
(`1 strongly disagree ———— 7 strongly agree`). A slider whose value you cannot read is not a
research control.

### 4.4 Domain

| Component | Used by |
|---|---|
| `dial_row(lever, value)` | Dial board, Twin Studio |
| `version_code_display(code)` | Dial board, Results, Twins, Studio |
| `what_twins_are_told(code)` | **Dial board, Results panel, Twins panel** |
| `scenario_text_block(variant)` | Results panel, Twins panel, Quality, Studio |
| `metric_bars(shifts, index)` | Dial board, Results panel |
| `grid_243(cells)` | Results |
| `twin_table(twins)` · `twin_profile_card(twin)` | Twins, Quality, Studio |
| `answer_compare(driver, baseline, variant)` | Twins panel |
| `log_tree(events)` · `side_panel(title, body)` | Agents, Quality, Results, Twins |
| `agent_card(agent)` · `agent_selector` | Agents tab, Agent Studio |
| `validity_test_card(test)` | Validity tests |
| `stats_table(spec, rows)` | All ten Statistics tabs |
| `budget_summary(budget)` | Every confirm step |
| `provenance_link(kind, id)` | Everywhere a number appears |

**`what_twins_are_told` is one component used in three places.** The Dial board, the Results side
panel and the Twins side panel must show identical text for the same code. One function, one source
(`gaps.commitment` for the selected gap ids), no drift.

**`provenance_link` is the product principle made into a widget.** Beside a shift it opens the run;
beside a run it opens the variant; beside a paragraph it opens the commitments and their corpus
citations. Two clicks from any number to Uber's own words.

### 4.5 `metric_bars` — the detail that is easy to get wrong

Six rows, each `label · divergent bar · signed value to 2 dp`, then `Index X.XXX` and a plain
sentence.

- Zero is a **centre line**. Positive extends right, negative left.
- **Colour encodes "good for the driver", not sign.** `leaving −0.59` extends left and is
  **green**. `pushback +1.20` extends right and is **red**.
- Bar length scales to the largest absolute shift on screen, so cells are comparable within a view.
- Every row carries its number; the bar is redundant encoding, never the only encoding.

Getting the colour rule backwards inverts the headline finding on every screen that shows it.

---

## 5. States

Every operational screen supports all seven. `docs/06` names the exact copy per screen.

| State | Must show |
|---|---|
| **Loading** | Skeleton or spinner, plus what is loading |
| **Empty** | Why it is empty and the single action that fixes it |
| **Ready** | Controls enabled |
| **Running** | Progress, current stage and agent, live log, **start disabled** |
| **Partial** | Completed count, pending count, and completed evidence retained |
| **Success** | Updated counters, the new result, an appended audit row |
| **Error** | Friendly summary, category, `event_id`, and a retry only where retrying is safe |

Empty states name the fix rather than stating the obvious:

> **No tested versions yet.** Set the dials and press *Ask the twins*, or let the agents choose six
> versions.

Error states always carry the `event_id` (`docs/04` §9), so "it failed" is always followed by
"here is exactly where".

### 5.1 Destructive actions

Delete all synthetic surveys · clear runs · load demo twins · reset an agent config · stop a
background job.

Each requires a confirm dialog naming **scope and count** — *"Delete 312 synthetic surveys and
their twins. Real surveys and all runs are untouched."* — and a typed confirmation for anything
touching more than 100 rows.

**Evidence is never deletable from the UI.** `runs`, `run_events`, `twin_answers`,
`twin_quality_runs` and `validity_results` are append-only (I9). "Clear runs" is a database
operation a researcher performs deliberately, not a button; the UI says so where the prototype had
one.

---

## 6. Accessibility

Minimums, all testable:

- **Never colour alone.** Every dot, pill, cell and bar carries text: `Kept (0.56)`,
  `Dropped (1.1)`, `PASS`, `Not tested`, `+1.62`.
- Every input has an associated `<label>`.
- Visible focus ring on every interactive element: `2px solid var(--tl-blue-600)`, `2px` offset.
- Body text ≥ 4.5:1 contrast; large text and UI chrome ≥ 3:1.
- Tables scroll horizontally on narrow screens; headers are sticky.
- Long log and prompt areas scroll vertically within a fixed height.
- Keyboard: tab order follows reading order; dials are a radio group navigable with arrow keys;
  Escape closes any panel or dialog.
- Statistical abbreviations carry a `title` **and** a visible legend above the table. `rho_A` and
  `AVE` are not self-explanatory even to the intended user.

The 243-grid is the hard case: 243 focusable cells is a keyboard trap. It gets arrow-key navigation
within a roving `tabindex`, an accessible name per cell (`version 21122, index 1.245`), and — the
real answer — the **Tested versions table below it carries the same data in linear, sortable,
screen-readable form**. The grid is the overview; the table is the equivalent.

---

## 7. Three semantic rules that must not be broken

Repeated here because each has already been got wrong once, in the prototype or in v1.0.

1. **Dials are red / amber / green for 0 / 1 / 2** — protection level, matching the legend
   `0 = as Uber is today · 1 = some protection · 2 = more protection`.
2. **Metric bars are coloured by "good for the driver", not by sign** (§4.5).
3. **`00000` is a control, not a cell.** The Dial board shows a red warning strip and disables
   *Ask the twins* when all five dials are 0. On the Results grid it carries a **red outline**
   ("Uber today"); the current best index carries a **gold outline**.

---

## 8. Gradio mechanics

### 8.1 What is achievable

| Requirement | Mechanism |
|---|---|
| Eight top-level sections with URLs | `demo.route()` + `gr.Navbar` (Gradio 5 native) |
| Sub-tabs inside a section | `gr.Tabs` — state survives tab change |
| Collapsible | `gr.Accordion` |
| Scrollable region | `elem_classes=["tl-scroll"]` + CSS `max-height` / `overflow-y` |
| Resizable | `elem_classes=["tl-resize"]`, CSS `resize: vertical`. **Vertical only.** |
| Live log | `gr.Timer` polling `events(after_id)`, rendering HTML into `gr.HTML` |
| 243 grid, hover + click | Plotly heatmap in `gr.Plot` with `.select()` |
| Confirm dialog | `gr.Group(visible=…)` overlay + explicit confirm/cancel |
| Toast | `gr.Info` / `gr.Warning` / `gr.Error` |

### 8.2 What is not, and what ships instead

| Cannot | Ships instead |
|---|---|
| Drag-to-resize splitters | `gr.Column(scale=…)` proportions + vertical CSS resize |
| Freely draggable windows | Fixed two-column layouts |
| Virtualised infinite scroll | Scroll-capped containers + pagination; `after_id` log polling |
| True modals | Visibility-toggled overlay groups |

**Styling may degrade; content and ordering may not.** If a layout cannot be achieved, render the
same content in a plainer container — never drop it, never reorder it — and record the degradation
in `docs/DECISIONS.md`.

### 8.3 Grid implementation

Primary: Plotly heatmap, 9 rows × 27 columns, `.select()` for click, native hover tooltips.

```python
row = pay * 3 + conditions                      # 0..8
col = contracts * 9 + management * 3 + repr     # 0..26
code = f"{row // 3}{row % 3}{col // 9}{(col // 3) % 3}{col % 3}"
```

Fallback if `.select()` misbehaves on the pinned Gradio version: `gr.Dataframe` 9×27 with a pandas
`Styler` gradient, whose `.select()` yields `SelectData.index` as `(row, col)`. **Never ship a grid
without click handling** — the click is how a researcher reaches the scenario text, and without it
the grid is decoration.

### 8.4 Frontend rules

1. **No business logic in `ui/`.** A handler calls a service and formats the result. Metric maths,
   lookups and hashing live in `analysis/`, `variant/`, `persona/`.
2. **No LLM call in a handler's synchronous path.** Enqueue, return, let the Timer poll.
3. **One source per value.** `what_twins_are_told` has one implementation used in three places.
4. **Every list that can grow is paginated or scroll-capped.** 243 rows, 500 twins, tens of
   thousands of events.
5. **Never render a metric the backend did not compute.** No client-side arithmetic on shifts —
   including "just" a sum or a percentage.
6. **The dial board does no network work.** Changing a dial recomputes the code, the Fairwork score
   and "What the twins are told" from reference data already in process. It must feel instant.
