"""Design tokens and global CSS. `docs/05_DESIGN_SYSTEM.md` §2, §3.

Tokens are declared once, here, as CSS custom properties. **No component may carry a literal
hex value** — §2. A colour that is not in this file is a bug in the component, not a missing
token.

Every value below was **measured off the prototype screenshots**
(`additional_data/screenshots of the prototype - Google Docs.pdf`), not chosen. The researcher
asked for visual parity with that prototype; `docs/DECISIONS.md` → D-UI-01 records the reversal
of the earlier "reproduce the hierarchy, not the styling" rule and why.
"""

from __future__ import annotations

# The eight top-level routes, in the mandatory order of `docs/06` §0.
# "Google Sheet is removed": there is no route, card or label naming a sheet anywhere.
ROUTES: tuple[tuple[str, str], ...] = (
    ("Main menu", "/"),
    ("Driver survey", "/survey"),
    ("Twin Lab", "/lab"),
    ("Generator", "/generator"),
    ("Twin Studio", "/studio"),
    ("Agent Studio", "/agents"),
    ("Statistics", "/statistics"),
    ("Research model", "/research"),
)

#: The prototype gives every app its own accent, and uses it for the page title, the section
#: heading bars, the primary button, the active tab underline and the table header tint.
#: Measured, per app, off the screenshots. Keyed by route path so `ui/app.py` can set the
#: matching body class without a second copy of this mapping existing anywhere.
ROUTE_ACCENTS: dict[str, str] = {
    "/": "blue",
    "/survey": "blue",
    "/take": "blue",
    "/lab": "green",
    "/generator": "purple",
    "/studio": "orange",
    "/agents": "teal",
    "/statistics": "indigo",
    "/research": "red",
}

#: Driver-facing routes. Real URLs (`ui/app.py` builds them with `demo.route()`), deliberately
#: absent from :data:`ROUTES` — a driver sent the questionnaire link must not be given a strip of
#: links into the researcher's application, and the nav strip is built from ROUTES alone.
PARTICIPANT_ROUTES: tuple[tuple[str, str], ...] = (
    ("Your work with Uber", "/take"),
)

APP_TITLE = "Twin Lab"
APP_SUBTITLE = "Uber Driver Study with Digital Twins"


def page_classes(path: str) -> list[str]:
    """The `elem_classes` for a route's page wrapper: the base class plus its accent.

    Every page calls this rather than writing its own accent class, so
    :data:`ROUTE_ACCENTS` stays the single place the per-app colour is decided (`docs/05` §4).
    An unknown path raises: a screen with no accent would silently inherit the Main menu's blue
    and look like a different app's page (CLAUDE.md — never silently skip).
    """
    try:
        accent = ROUTE_ACCENTS[path]
    except KeyError:
        raise KeyError(
            f"no accent for route {path!r}; add it to ROUTE_ACCENTS (docs/05 §2.1)"
        ) from None
    return ["tl-page", f"tl-route-{accent}"]


#: Roboto is the prototype's typeface and the researcher asked for it exactly (D-UI-01).
#: `display=swap` plus the full system fallback in `--tl-font` means a cold-starting Space
#: paints in the fallback and swaps when the font lands — the font never gates first paint,
#: which was the original reason `docs/05` banned a webfont.
FONT_HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" '
    'href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&'
    'family=Roboto+Mono:wght@400;500&display=swap">'
)

TWINLAB_CSS = """
:root{
  /* ---- neutrals: the prototype's Google-Material greys, sampled off the screenshots ---- */
  --tl-grey-900:#202124;   /* body text, section headings */
  --tl-grey-700:#3C4043;   /* secondary body */
  --tl-grey-500:#5F6368;   /* captions, inactive tabs, sub-labels */
  --tl-grey-300:#DADCE0;   /* input borders, pill-group outline */
  --tl-grey-200:#E9EAED;   /* card border */
  --tl-grey-100:#ECEDEF;   /* rules, table row separators */
  --tl-grey-50 :#F8F9FA;   /* page background */
  --tl-white   :#FFFFFF;

  /* ---- per-app accents (docs/05 §2.1). --tl-accent is re-pointed per route below. ---- */
  --tl-blue   :#3F72E9;  --tl-blue-dark  :#2D4DA7;  --tl-blue-tint  :#E9F0FE;
  --tl-purple :#9130E7;  --tl-purple-dark:#7524BC;  --tl-purple-tint:#F3EDF9;
  --tl-green  :#2B8043;  --tl-green-dark :#1E6332;  --tl-green-tint :#EEF5F0;
  --tl-orange :#DD7100;  --tl-orange-dark:#B85C00;  --tl-orange-tint:#FCF4EB;
  --tl-teal   :#30838F;  --tl-teal-dark  :#24646D;  --tl-teal-tint  :#EAF2F4;
  --tl-indigo :#4950B6;  --tl-indigo-dark:#383E93;  --tl-indigo-tint:#EDEEF8;
  --tl-red    :#BA221B;  --tl-red-dark   :#8F1A14;  --tl-red-tint   :#FAEEED;

  /* Default accent: the Main menu's blue. Every `.tl-route-*` class overrides all four. */
  --tl-accent:var(--tl-blue);
  --tl-accent-dark:var(--tl-blue-dark);
  --tl-accent-tint:var(--tl-blue-tint);
  --tl-accent-wash:#F1F5FB;   /* the header's pale gradient end */

  /* ---- semantic: fixed meanings that do NOT follow the route accent (docs/05 §7) ---- */
  --tl-ok    :#308038;  --tl-ok-tint  :#E7F4EA;   /* Kept, PASS, complete, good for the driver */
  --tl-warn  :#E8A33D;  --tl-warn-tint:#FCF7E0;   /* running, cached, CHECK */
  --tl-bad   :#CD3021;  --tl-bad-tint :#FAE8E6;   /* Dropped, FAIL, bad for the driver */
  --tl-info  :#3F72E9;  --tl-info-tint:#E9F0FE;   /* links, neutral notices */
  --tl-gold  :#C79A00;                            /* best index outline on the 243 grid */

  /* Dial states are a traffic light for PROTECTION LEVEL, never for sign (§7 rule 1). */
  --tl-dial-0:var(--tl-bad);    /* 0 = as Uber is today */
  --tl-dial-1:#F0B429;          /* 1 = some protection  */
  --tl-dial-2:var(--tl-ok);     /* 2 = more protection  */

  /* ---- surface aliases ---- */
  --tl-bg:var(--tl-grey-50);
  --tl-surface:var(--tl-white);
  --tl-border:var(--tl-grey-200);

  /* ---- type (docs/05 §2.2). Roboto, as the prototype. ---- */
  --tl-font: Roboto, "Helvetica Neue", Arial, "Segoe UI", system-ui, sans-serif;
  --tl-mono: "Roboto Mono", ui-monospace, "Cascadia Mono", Menlo, monospace;
  --tl-fs-xs:11px; --tl-fs-sm:12px; --tl-fs-md:13px;    /* md is body: dense by design */
  --tl-fs-lg:15px; --tl-fs-xl:18px; --tl-fs-2xl:24px; --tl-fs-code:32px;
  --tl-lh-tight:1.25; --tl-lh-body:1.5;

  /* ---- space, radius, elevation. The prototype is low-chrome: 8px radius, hairline
         borders, and a shadow only where something floats. ---- */
  --tl-s1:4px; --tl-s2:8px; --tl-s3:12px; --tl-s4:16px; --tl-s5:24px; --tl-s6:32px;
  --tl-r-sm:4px; --tl-r-md:8px; --tl-r-pill:999px;
  --tl-shadow-card:none;
  --tl-shadow-hover:0 1px 3px rgba(60,64,67,.16);
  --tl-shadow-panel:0 2px 10px rgba(60,64,67,.20);

  /* ---- motion (docs/05 §3) ---- */
  --tl-dur-fast:120ms; --tl-dur-base:180ms; --tl-dur-slow:260ms;
  --tl-ease:cubic-bezier(.2,.7,.3,1);
}

/* ---- per-route accent. `ui/app.py` puts one of these on the page wrapper. ---- */
.tl-route-blue  { --tl-accent:var(--tl-blue);   --tl-accent-dark:var(--tl-blue-dark);
                  --tl-accent-tint:var(--tl-blue-tint);   --tl-accent-wash:#F1F5FB; }
.tl-route-purple{ --tl-accent:var(--tl-purple); --tl-accent-dark:var(--tl-purple-dark);
                  --tl-accent-tint:var(--tl-purple-tint); --tl-accent-wash:#FAF8FD; }
.tl-route-green { --tl-accent:var(--tl-green);  --tl-accent-dark:var(--tl-green-dark);
                  --tl-accent-tint:var(--tl-green-tint);  --tl-accent-wash:#F0F6F3; }
.tl-route-orange{ --tl-accent:var(--tl-orange); --tl-accent-dark:var(--tl-orange-dark);
                  --tl-accent-tint:var(--tl-orange-tint); --tl-accent-wash:#FDF7F0; }
.tl-route-teal  { --tl-accent:var(--tl-teal);   --tl-accent-dark:var(--tl-teal-dark);
                  --tl-accent-tint:var(--tl-teal-tint);   --tl-accent-wash:#F1F7F8; }
.tl-route-indigo{ --tl-accent:var(--tl-indigo); --tl-accent-dark:var(--tl-indigo-dark);
                  --tl-accent-tint:var(--tl-indigo-tint); --tl-accent-wash:#F2F3FA; }
.tl-route-red   { --tl-accent:var(--tl-red);    --tl-accent-dark:var(--tl-red-dark);
                  --tl-accent-tint:var(--tl-red-tint);    --tl-accent-wash:#FCF4F3; }

gradio-app{ background:var(--tl-bg) !important; }
body, .gradio-container{
  font-family:var(--tl-font);
  font-size:var(--tl-fs-md);
  line-height:var(--tl-lh-body);
  color:var(--tl-grey-900);
  background:var(--tl-bg);
}
/* Gradio centres and caps its container; the prototype runs edge to edge with a 16px gutter. */
.gradio-container{ max-width:none !important; padding:0 var(--tl-s4) var(--tl-s6) !important; }
.gradio-container > .main, .gradio-container .contain, .gradio-container .wrap.svelte-1parkyx{
  max-width:none !important; width:100% !important;
}

/* Gradio wraps every `gr.HTML` in a white, padded, overflow-auto `.block`. Left alone that
   turns each of our HTML regions into a card with its own scrollbar, so a page of six regions
   reads as six stacked boxes instead of one document — which is not what the prototype is.
   `hide-container` is the class Gradio puts on a block whose component draws its own chrome,
   so this only strips the wrapper, never a real input's. */
.tl-page .block.hide-container,
.tl-page .html-container{
  background:transparent !important; border:none !important; padding:0 !important;
  overflow:visible !important; box-shadow:none !important; min-width:0 !important;
}
/* Gradio's own route strip duplicates `global_nav`, which carries the accent underline and the
   `< Main menu` back link the prototype has on every screen. `gr.Navbar(visible=False)` is set
   too, but Gradio 5 still renders the element, so it is hidden here as well. One navbar, not
   two. `.tl-nav` is also a <nav> and must not match, hence the `.fillable` qualifier. */
nav.fillable{ display:none !important; }

/* The header and the navbar run to the page edge, inside a column that already has the
   container's 16px gutter. They pull back out to it rather than sitting indented. */
.tl-header, .tl-nav{ margin-left:calc(-1 * var(--tl-s4)); margin-right:calc(-1 * var(--tl-s4)); }

/* A column of +1.62 / -0.98 / +0.07 does not align without this and cannot be scanned (§2.2). */
.tl-num, table td, table th, .tl-metric{ font-variant-numeric:tabular-nums; }

/* ================================ shell ================================= */

/* The prototype's page header: title in the app's accent, badge beside it, build line pushed
   right, a pale wash behind, and a 2px accent rule under the whole thing. */
.tl-header{
  display:flex; align-items:baseline; flex-wrap:wrap; gap:var(--tl-s3);
  padding:var(--tl-s4) var(--tl-s4) var(--tl-s3);
  background:linear-gradient(180deg, var(--tl-white) 0%, var(--tl-accent-wash) 100%);
  border-bottom:2px solid var(--tl-accent);
}
.tl-header h1{
  margin:0; font-size:var(--tl-fs-2xl); line-height:var(--tl-lh-tight);
  color:var(--tl-accent-dark); font-weight:700; letter-spacing:-.2px;
}
.tl-header .tl-sub{
  color:var(--tl-grey-500); font-size:var(--tl-fs-md);
  flex:1 1 100%; order:3; margin-top:calc(-1 * var(--tl-s2));
}
.tl-header .tl-build{
  margin-left:auto; color:var(--tl-grey-500); font-size:var(--tl-fs-xs);
}

/* The badge is a soft accent-tinted pill, never a filled chip (prototype: "Mock model"). */
.tl-badge{
  display:inline-block; padding:3px var(--tl-s3); border-radius:var(--tl-r-pill);
  font-size:var(--tl-fs-xs); font-weight:500; letter-spacing:.01em;
  background:var(--tl-accent-tint); color:var(--tl-accent-dark);
  border:none;
}
/* A live model is not the resting state and must not read like one (docs/06 §0). */
/* The dark red, not the mid red: 11px of `--tl-bad` on `--tl-bad-tint` is 4.39:1, just under
   the 4.5:1 floor small text has to clear (docs/05 §6). Same pattern as `.tl-pill-amber`. */
.tl-badge-live{ background:var(--tl-bad-tint); color:var(--tl-red-dark); font-weight:700; }

/* Top nav and sub nav: plain text tabs, inactive grey, active in the accent with a 2px
   underline. No pills, no boxes — the prototype's navbar is a rule with labels on it. */
.tl-nav{
  display:flex; gap:var(--tl-s5); flex-wrap:wrap;
  padding:0 var(--tl-s4);
  border-bottom:1px solid var(--tl-grey-100); background:var(--tl-white);
}
.tl-nav a{
  padding:var(--tl-s3) 0 10px; font-size:var(--tl-fs-md); color:var(--tl-grey-500);
  text-decoration:none; border-bottom:2px solid transparent; margin-bottom:-1px;
  transition:color var(--tl-dur-fast) var(--tl-ease);
}
/* `.tl-page a` further down sets every page link to `--tl-info`, and at equal specificity the
   later rule wins — so the navbar rendered as eight blue links instead of the prototype's grey
   strip with one accented item, and 13px of `--tl-info` on white is 4.38:1, under the floor.
   `.tl-nav` is raised above it here rather than lowering `.tl-page a`, because a link inside a
   page body SHOULD be `--tl-info`; it is the navbar that is not body text. */
.tl-nav a, .tl-page .tl-nav a{ color:var(--tl-grey-500); }
.tl-nav a:hover, .tl-page .tl-nav a:hover{ color:var(--tl-grey-900); }
.tl-nav a.tl-nav-on, .tl-page .tl-nav a.tl-nav-on{
  color:var(--tl-accent-dark); border-bottom-color:var(--tl-accent);
}
.tl-nav a.tl-nav-back, .tl-page .tl-nav a.tl-nav-back{ color:var(--tl-grey-500); }

/* ================================ cards ================================= */

.tl-card{
  background:var(--tl-surface); border:1px solid var(--tl-border);
  border-radius:var(--tl-r-md); padding:var(--tl-s4);
  box-shadow:var(--tl-shadow-card);
  transition:box-shadow var(--tl-dur-fast) var(--tl-ease);
}
.tl-card:hover{ box-shadow:var(--tl-shadow-hover); }
/* Card text carries its own colour. Gradio styles bare `strong`, `span` and `div` inside an
   HTML block near-white against this light surface, and an inherited colour loses to it —
   which silently drops every card title below the 4.5:1 floor (docs/05 §6). */
.tl-card, .tl-card div{ color:var(--tl-grey-700); }
.tl-card > strong{
  color:var(--tl-grey-900); font-size:var(--tl-fs-lg); font-weight:500;
  display:block; margin-bottom:var(--tl-s2);
}

/* Main menu card groups (docs/06 §1.1, §1.2). */
/* When `tl-card-grid` arrives via `elem_classes` it lands on Gradio's block wrapper, two divs
   above the cards; `display:contents` makes those two transparent to layout so the grid
   actually reaches them. Without it the five agent cards stack in one narrow column. */
.block.tl-card-grid > .html-container,
.block.tl-card-grid > .html-container > .prose{ display:contents; }
.tl-card-grid{
  display:grid; gap:var(--tl-s3); margin-top:var(--tl-s3);
  grid-template-columns:repeat(auto-fill, minmax(260px, 1fr));
}
/* A card inside a group is a flat tinted panel, not a second raised card (prototype §1.1). */
.tl-card-grid .tl-card{
  background:var(--tl-grey-50); border-color:var(--tl-grey-100); padding:var(--tl-s3);
}
/* A destination card is a BUTTON, not a line of link text. It used to render the route as a
   small `<a>` inside the card, so the only clickable thing on a 260px tile was a 60px string of
   accent-coloured text — the title and the description did nothing. The whole card is now the
   control: one `<a>` styled as a tile, with the route kept as a quiet caption because
   `docs/06` §1.1 makes title, description AND destination mandatory. Nothing is underlined;
   the affordance is the tile, its hover lift and its focus ring. */
a.tl-link-card{
  display:block; text-decoration:none; cursor:pointer;
  border:1px solid var(--tl-grey-300); background:var(--tl-white);
  transition:border-color var(--tl-dur-fast) var(--tl-ease),
             box-shadow var(--tl-dur-fast) var(--tl-ease),
             transform var(--tl-dur-fast) var(--tl-ease);
}
a.tl-link-card:hover{
  border-color:var(--tl-accent); background:var(--tl-accent-tint);
  box-shadow:var(--tl-shadow-hover); transform:translateY(-1px);
}
a.tl-link-card:active{ transform:none; box-shadow:var(--tl-shadow-card); }
a.tl-link-card:focus-visible{ outline:2px solid var(--tl-accent); outline-offset:2px; }
.tl-link-card strong{
  color:var(--tl-accent-dark); font-size:var(--tl-fs-md); font-weight:500;
  margin-bottom:var(--tl-s1); display:block;
}
.tl-link-desc{ color:var(--tl-grey-700); font-size:var(--tl-fs-sm); margin:var(--tl-s1) 0; }
/* The destination is provenance, not a second control: no underline, no link colour. */
.tl-link-dest{
  color:var(--tl-grey-500) !important; font-size:var(--tl-fs-xs);
  font-family:var(--tl-mono); margin-top:var(--tl-s2);
}
.tl-quickstart{ color:var(--tl-grey-700); padding-left:var(--tl-s5); }
.tl-quickstart li{ margin:var(--tl-s1) 0; }
.tl-persona{ white-space:pre-wrap; font-family:var(--tl-mono); font-size:var(--tl-fs-sm);
             color:var(--tl-grey-700); }

/* The version code is the primary identifier in this study and should read like one (§2.2).
   The prototype sets it in Roboto Bold with wide tracking, centred — not in mono. */
.tl-code{
  font-family:var(--tl-font); font-size:var(--tl-fs-code); font-weight:700;
  letter-spacing:.16em; color:var(--tl-grey-900);
}

/* Gradio cannot do drag-to-resize splitters or virtualised scroll; these are the accepted
   substitutes recorded in docs/DECISIONS.md -> Degradations accepted. */
.tl-scroll{ max-height:420px; overflow-y:auto; }
.tl-resize{ resize:vertical; overflow:auto; min-height:160px; }

.tl-placeholder{
  padding:var(--tl-s5); border:1px dashed var(--tl-grey-300);
  border-radius:var(--tl-r-md); background:var(--tl-surface);
  color:var(--tl-grey-500);
}

/* Route and tab changes: an 8px rise and a fade (§3). Decoration only — it never gates data. */
.tl-page{ animation:tl-rise var(--tl-dur-base) var(--tl-ease); }
@keyframes tl-rise{ from{ opacity:0; transform:translateY(8px);} to{ opacity:1; transform:none;} }

/* ============================== primitives ==============================
   docs/05 §4.2. Every one carries text; none encodes by colour alone. */
.tl-pill{
  display:inline-block; padding:1px var(--tl-s2); border-radius:var(--tl-r-sm);
  font-size:var(--tl-fs-xs); font-weight:500; border:none;
}
/* A pill's LETTERS take the dark variant of its own hue; its FILL keeps the measured tint.
   `--tl-ok` on `--tl-ok-tint` is 4.34:1 and `--tl-bad` on `--tl-bad-tint` is 4.39:1 — both
   under the 4.5:1 floor for text this small, and `tl-pill-green` alone appears 267 times on
   one Statistics page. The hue is unchanged, so the prototype's colour language (D-UI-01) is
   intact; only the ink is darkened. `.tl-pill-amber` already did exactly this. */
.tl-pill-green{ background:var(--tl-ok-tint);   color:var(--tl-green-dark); }
.tl-pill-amber{ background:var(--tl-warn-tint); color:#8A5A00;              }
.tl-pill-red  { background:var(--tl-bad-tint);  color:var(--tl-red-dark);   }
.tl-pill-grey { background:var(--tl-grey-50);   color:var(--tl-grey-500);
                border:1px solid var(--tl-grey-200); }

.tl-dot-wrap{ display:inline-flex; align-items:center; gap:var(--tl-s1); }
.tl-dot{ width:8px; height:8px; border-radius:50%; flex:0 0 8px; }
.tl-dot-label{ font-size:var(--tl-fs-xs); color:var(--tl-grey-700); }
.tl-empty strong, .tl-error strong, .tl-caption, .tl-index,
.tl-told-head, .tl-bar-label, .tl-bar-value{ color:var(--tl-grey-900); }
.tl-caption, .tl-empty-action{ color:var(--tl-grey-500); }

.tl-empty, .tl-error, .tl-loading{
  padding:var(--tl-s4); border-radius:var(--tl-r-md); border:1px solid var(--tl-border);
  background:var(--tl-surface);
}
.tl-empty-action{ color:var(--tl-grey-500); margin-top:var(--tl-s1); }
.tl-error{ border-color:var(--tl-bad); background:var(--tl-bad-tint); }
.tl-error-meta{ font-family:var(--tl-mono); font-size:var(--tl-fs-xs); margin-top:var(--tl-s1); }
.tl-spinner{
  display:inline-block; width:10px; height:10px; margin-right:var(--tl-s2);
  border:2px solid var(--tl-grey-200); border-top-color:var(--tl-accent); border-radius:50%;
  animation:tl-spin 700ms linear infinite;
}
@keyframes tl-spin{ to{ transform:rotate(360deg); } }

/* An absent measurement must never look like a measured zero (I17). */
.tl-absent{ color:var(--tl-grey-500); font-style:italic; }

/* The prototype's signature: every section heading is a 3px accent bar, a near-black bold
   title, and an optional grey one-liner beneath. One component, every screen. */
.tl-section{ margin:var(--tl-s5) 0 var(--tl-s3); }
.tl-section-title{
  display:flex; align-items:center; gap:var(--tl-s2);
  font-weight:500; color:var(--tl-grey-900); font-size:var(--tl-fs-xl);
  margin:0; line-height:var(--tl-lh-tight);
}
.tl-section-title::before{
  content:""; flex:0 0 3px; align-self:stretch; min-height:1em;
  background:var(--tl-accent); border-radius:1px;
}
.tl-section-sub{
  color:var(--tl-grey-500); font-size:var(--tl-fs-md);
  margin:var(--tl-s1) 0 0 11px;
}

/* Prose inside a page. Gradio's prose colour is near-white on this light surface, which drops
   a screen's own title below the 4.5:1 floor (docs/05 §6). */
.tl-page h1, .tl-page h2, .tl-page h3{ color:var(--tl-grey-900); font-weight:500; }
.tl-page p, .tl-page li{ color:var(--tl-grey-700); }
.tl-page em{ color:var(--tl-grey-500); }
.tl-page a{ color:var(--tl-info); }

/* ============================== callouts ================================
   Three tinted note blocks, lifted from the prototype's Agent Studio and Validation screens.
   Each is a tint plus a 3px left rule; none of them is colour alone — every one carries its
   own leading sentence. */
.tl-note{
  padding:var(--tl-s3); border-radius:var(--tl-r-sm); margin:var(--tl-s2) 0;
  font-size:var(--tl-fs-md); color:var(--tl-grey-900);
  border-left:3px solid transparent;
}
.tl-note-warn{ background:var(--tl-warn-tint); border-left-color:var(--tl-warn); }
.tl-note-ok  { background:var(--tl-ok-tint);   border-left-color:var(--tl-ok);   }
.tl-note-info{ background:var(--tl-info-tint); border-left-color:var(--tl-info); }
.tl-note-bad { background:var(--tl-bad-tint);  border-left-color:var(--tl-bad);  }

/* ---- Statistics: the legend every stats table carries (docs/05 §4.4) ----
   rho_A and AVE are not self-explanatory even to the intended reader (docs/05 §6), so the
   abbreviation is explained ABOVE the table as well as in the column's title attribute. This is
   content, not decoration: stats_table raises when a spec arrives without one. */
.tl-stats-table{ margin:var(--tl-s4) 0; }
.tl-legend{
  display:flex; flex-wrap:wrap; gap:var(--tl-s2) var(--tl-s4);
  margin:0 0 var(--tl-s2); padding:var(--tl-s2);
  background:var(--tl-grey-50); border:1px solid var(--tl-grey-100);
  border-radius:var(--tl-r-md); font-size:var(--tl-fs-sm);
}
.tl-legend-item{ display:flex; gap:var(--tl-s1); align-items:baseline; max-width:46ch; }
.tl-legend dt{ font-weight:500; color:var(--tl-grey-900); white-space:nowrap; }
.tl-legend dd{ margin:0; color:var(--tl-grey-700); }

/* The UNVALIDATED banner (docs/07 §10). Never colour alone — it carries its text (docs/05 §6). */
.tl-banner{
  padding:var(--tl-s3); border-radius:var(--tl-r-sm); margin:var(--tl-s3) 0;
  border-left:3px solid transparent;
}
.tl-banner-warn{
  background:var(--tl-warn-tint); border-left-color:var(--tl-warn); color:var(--tl-grey-900);
}
.tl-banner-warn strong{ color:var(--tl-grey-900); letter-spacing:.04em; }

/* =============================== tables =================================
   The prototype's tables have no vertical rules, an accent-tinted header row, hairline row
   separators and generous cell padding. Sticky headers and horizontal scroll are ours
   (docs/05 §6). */
.tl-table-wrap{ overflow:auto; border:1px solid var(--tl-grey-100); border-radius:var(--tl-r-md); }
table.tl-data, table.tl-kv{ border-collapse:collapse; width:100%; font-size:var(--tl-fs-sm); }
table.tl-data th{
  text-align:left; font-weight:500; color:var(--tl-grey-900);
  background:var(--tl-accent-tint); padding:var(--tl-s2) var(--tl-s3); white-space:nowrap;
}
table.tl-data thead th{ position:sticky; top:0; z-index:1; }
table.tl-data td{
  padding:var(--tl-s2) var(--tl-s3); border-top:1px solid var(--tl-grey-100);
  vertical-align:top;
  /* Explicit: Gradio's prose colour is near-white here and a table of unreadable numbers is
     the one thing a research instrument cannot ship (docs/05 §6). */
  color:var(--tl-grey-900);
}
table.tl-data tbody tr:hover{ background:var(--tl-grey-50); }
/* A row the reader can open. `gr.HTML` emits no events, so the click is bridged into a Gradio
   component by the page's `load_js`; this is only what makes it look and focus like a control,
   which `docs/05` §6 requires of anything clickable. */
table.tl-data tbody tr.tl-row-pick{ cursor:pointer; }
table.tl-data tbody tr.tl-row-pick:hover{ background:var(--tl-accent-wash, var(--tl-grey-100)); }
table.tl-data tbody tr.tl-row-pick:focus-visible{
  outline:2px solid var(--tl-accent); outline-offset:-2px;
}
table.tl-data tbody tr.tl-row-pick.tl-row-on{
  background:var(--tl-accent-wash, var(--tl-grey-100));
  box-shadow:inset 3px 0 0 var(--tl-accent);
}
table.tl-data caption, table.tl-kv caption{
  text-align:left; color:var(--tl-grey-700); font-weight:500;
  padding:var(--tl-s2) var(--tl-s2) var(--tl-s1);
}
/* The key/value table: the prototype tints the LABEL column, not the header row. */
table.tl-kv th{
  width:38%; text-align:left; font-weight:400; color:var(--tl-grey-900);
  background:var(--tl-accent-tint); padding:var(--tl-s2) var(--tl-s3);
  border-bottom:1px solid var(--tl-white);
}
table.tl-kv td{
  padding:var(--tl-s2) var(--tl-s3); color:var(--tl-grey-900);
  border-bottom:1px solid var(--tl-grey-100);
}

/* ============================== dial board ==============================
   docs/06 §3.2. The prototype's dial is one pill-shaped group with a hairline outline; the
   chosen step is a solid fill inside it, and the two ends inherit the group's rounding. */
/* The `00000` strip and the synthetic-data warning are body text a researcher has to read,
   not chrome, so the letters take the dark red while the rule and the fill keep the mid one. */
.tl-warn-strip{
  background:var(--tl-bad-tint); color:var(--tl-red-dark); border-left:3px solid var(--tl-bad);
  border-radius:var(--tl-r-sm); padding:var(--tl-s3); font-weight:500;
  margin-bottom:var(--tl-s3);
}
/* The same strip in a neutral weight. `ARCHITECTURE_UPDATE.md` §4.3 item 4 asks for an explicit
   badge naming `n` on a Twin Studio result — and that is NOT a warning. A Studio number is a real
   measurement over one twin; what the badge says is which quantity it is. Red would read as "this
   number is wrong", which is the opposite of true and would train the researcher to dismiss it. */
.tl-note-strip{
  background:var(--tl-grey-50); color:var(--tl-grey-700);
  border-left:3px solid var(--tl-grey-300); border-radius:var(--tl-r-sm);
  padding:var(--tl-s3); font-weight:500; margin-bottom:var(--tl-s3);
}
.tl-note-strip strong, .tl-note-strip code{ color:var(--tl-ink); }

/* Labelled Wording A / Wording B blocks in Agent Studio (§5.2 item 2). Wording is a real
   experimental factor (validity test 5), so the two sets are visibly two sets. */
.tl-wording{ margin-bottom:var(--tl-s4); }
.tl-wording-head{
  font-size:var(--tl-fs-xs); font-weight:500; letter-spacing:.06em; text-transform:uppercase;
  color:var(--tl-grey-700); margin-bottom:var(--tl-s2);
}

.tl-code-block{ text-align:center; padding:var(--tl-s4) 0; }
.tl-code-label{ color:var(--tl-grey-500); font-size:var(--tl-fs-md); }
.tl-code-sub{ color:var(--tl-grey-500); font-size:var(--tl-fs-md); margin-top:var(--tl-s1); }
.tl-legend{ display:flex; flex-wrap:wrap; gap:var(--tl-s3); font-size:var(--tl-fs-sm);
            color:var(--tl-grey-700); margin:var(--tl-s2) 0; }
/* Set on the item, not only the container: Gradio styles bare `span` near-white, and an
   inherited colour loses to it. Same reason `.tl-dot-label` carries its own. */
.tl-legend-item{
  display:inline-flex; align-items:center; gap:var(--tl-s1);
  color:var(--tl-grey-700);
}

/* Dial colours are a traffic light for protection level, never for sign (docs/05 §7 rule 1).
   The legend swatches are 10px squares in the prototype, not dots. */
.tl-legend-item.tl-dial-0::before,
.tl-legend-item.tl-dial-1::before,
.tl-legend-item.tl-dial-2::before{
  content:""; width:10px; height:10px; border-radius:2px;
}
.tl-legend-item.tl-dial-0::before{ background:var(--tl-dial-0); }
.tl-legend-item.tl-dial-1::before{ background:var(--tl-dial-1); }
.tl-legend-item.tl-dial-2::before{ background:var(--tl-dial-2); }

.tl-told{ display:flex; flex-direction:column; gap:var(--tl-s2); }
.tl-told-lever{
  border-left:3px solid var(--tl-grey-200); padding-left:var(--tl-s3);
}
.tl-told-lever.tl-dial-1{ border-left-color:var(--tl-dial-1); }
.tl-told-lever.tl-dial-2{ border-left-color:var(--tl-dial-2); }
.tl-told-head{ font-weight:500; color:var(--tl-grey-900); }
.tl-told ul{ margin:var(--tl-s1) 0 0; padding-left:var(--tl-s4); }
.tl-gap-id{ font-family:var(--tl-mono); font-size:var(--tl-fs-xs); color:var(--tl-grey-500); }

.tl-scenario p{ margin:0 0 var(--tl-s3); }

/* ---- metric bars (docs/05 §4.5). Colour = good for the driver, NOT sign. ---- */
.tl-bar-row{ display:flex; align-items:center; gap:var(--tl-s3); padding:3px 0; }
.tl-bar-label{ flex:0 0 96px; font-size:var(--tl-fs-sm); color:var(--tl-grey-700); }
.tl-bar-track{
  flex:1 1 auto; position:relative; height:12px; background:var(--tl-grey-50);
  border-radius:2px;
}
/* Zero is a centre line: positive extends right of it, negative left. */
.tl-bar-track::before{
  content:""; position:absolute; left:50%; top:0; bottom:0; width:1px;
  background:var(--tl-grey-300);
}
.tl-bar{ position:absolute; top:1px; bottom:1px; border-radius:1px; }
.tl-bar-right{ left:50%; }
.tl-bar-left { right:50%; }
.tl-bar-good { background:var(--tl-ok); }
.tl-bar-bad  { background:var(--tl-bad); }
.tl-bar-flat { background:var(--tl-grey-200); }
.tl-bar-value{ flex:0 0 64px; text-align:right; font-size:var(--tl-fs-sm); }
.tl-index{ margin-top:var(--tl-s3); font-size:var(--tl-fs-md); color:var(--tl-grey-900); }
.tl-index strong{ font-weight:700; }
.tl-caption{ color:var(--tl-grey-500); margin-top:var(--tl-s1); font-size:var(--tl-fs-sm); }
.tl-floor-note{
  margin-top:var(--tl-s2); padding:var(--tl-s2); border-radius:var(--tl-r-sm);
  background:var(--tl-warn-tint); color:var(--tl-grey-900); font-size:var(--tl-fs-sm);
  border-left:3px solid var(--tl-warn);
}

/* ---- the 243 grid (docs/05 §8.3) ----

   `docs/05` §8.3: "untested cells grey; tested filled white->green by index". The fill is one
   colour at a varying alpha, set per cell as `--tl-cell-depth` by `components.domain.grid_243`
   from that cell's `intensity`. Colour is a SECOND channel only -- the exact index is in every
   cell's `title` and `aria-label` and again in the Tested versions table below, because the grid
   may never encode anything by colour alone (docs/05 §6).

   The cells were 14px with 1px gaps, which is 243 squares in a 420px block: unreadable, and the
   row axis carried no labels at all, so a reader could not tell which cell was which without
   hovering every one. */
.tl-grid-wrap{ overflow-x:auto; padding:var(--tl-s2) 0; }
table.tl-grid{ border-collapse:separate; border-spacing:2px; }
table.tl-grid td{ padding:0; }
.tl-grid-rowlab{
  font-size:var(--tl-fs-xs); font-weight:400; color:var(--tl-grey-500);
  text-align:right; padding-right:var(--tl-s2); white-space:nowrap;
  font-family:var(--tl-mono);
}
/* `.tl-page` raises specificity above any `.tl-subnav`-style panel rule: the grid is the one
   place in this design where a `<button>` is a data mark, and a tab rule must never blank it. */
.tl-page .tl-cell{
  width:20px; height:20px; padding:0; border:1px solid transparent !important;
  border-radius:2px !important; background:var(--tl-grey-100) !important; cursor:pointer;
  transition:transform var(--tl-dur-fast) var(--tl-ease);
}
.tl-cell:hover{ transform:scale(1.25); }
/* `--tl-cell-depth` runs 0.18 (lowest tested index) to 1.0 (highest). The floor keeps the palest
   tested cell clearly darker than an untested one: "tested and worst" and "not tested" are
   different facts and must not render as the same square. */
.tl-page .tl-cell-tested{
  background:rgba(45, 122, 106, var(--tl-cell-depth, 1)) !important;
  border-color:rgba(45, 122, 106, calc(var(--tl-cell-depth, 1) * .55)) !important;
}
.tl-page .tl-cell-control{ outline:2px solid var(--tl-bad) !important; outline-offset:0; }
.tl-page .tl-cell-best{ outline:2px solid var(--tl-gold) !important; outline-offset:0; }
.tl-cell:focus-visible{ outline:2px solid var(--tl-accent); outline-offset:2px; }
.tl-grid-caption{
  margin-top:var(--tl-s3); color:var(--tl-grey-500); font-size:var(--tl-fs-sm);
  line-height:1.5;
}

.tl-interactions{ list-style:none; padding:0; margin:0; }
.tl-interactions li{ padding:var(--tl-s2) 0; border-top:1px solid var(--tl-grey-100); }

.tl-side-panel{ border:1px solid var(--tl-border); border-radius:var(--tl-r-md);
                background:var(--tl-surface); box-shadow:var(--tl-shadow-panel); }
.tl-side-head{ padding:var(--tl-s3); border-bottom:1px solid var(--tl-grey-100);
               font-weight:500; color:var(--tl-grey-900); }
.tl-side-body{ padding:var(--tl-s3); }

/* ---- Agent Studio's left rail: one selectable card per agent (prototype p15-p21) ---- */
.tl-agent-card{
  min-height:56px; padding:var(--tl-s3); margin-bottom:var(--tl-s2);
  border:1px solid var(--tl-border); border-radius:var(--tl-r-md);
  background:var(--tl-surface); cursor:pointer;
}
.tl-agent-card.tl-on{ border-color:var(--tl-info); background:var(--tl-info-tint); }
/* The cards are the selector (`docs/06` §6) and the radio behind them is the control. It stays
   in the DOM — hiding it with `display:none` would take the agent list away from the keyboard
   and from a screen reader — but it is clipped out of the visual flow. */
.tl-agent-pick{
  position:absolute !important; width:1px !important; height:1px !important;
  overflow:hidden !important; clip:rect(0 0 0 0) !important; white-space:nowrap !important;
  border:none !important; padding:0 !important; margin:-1px !important;
}
/* Keyboard focus must still be visible, so the focused radio's card is outlined. */
.tl-agent-pick input:focus-visible ~ *{ outline:2px solid var(--tl-accent); }
.tl-agent-name{ font-weight:500; color:var(--tl-grey-900); }
.tl-agent-role{ color:var(--tl-grey-500); font-size:var(--tl-fs-sm); margin:var(--tl-s1) 0 0; }
/* "uses AI" / "rules only" — the distinction the whole screen turns on, so it is a label. */
.tl-agent-kind{
  display:inline-block; margin-left:var(--tl-s2); padding:0 var(--tl-s1);
  border-radius:var(--tl-r-sm); font-size:var(--tl-fs-xs); font-weight:500;
}
.tl-agent-kind-ai{ background:var(--tl-ok-tint); color:var(--tl-ok); }
.tl-agent-kind-rules{ background:var(--tl-info-tint); color:var(--tl-accent-dark); }

/* M19 WP-8 item 6. Each agent's two steps: the deterministic one and the one that costs a model
   call. The Policy Designer is why this exists -- choosing what changes is a frozen lookup with
   no model in it (I1), and the card previously showed one undifferentiated "renders" line. */
.tl-agent-steps{ margin:var(--tl-s2) 0 0; display:flex; flex-direction:column; gap:var(--tl-s1); }
.tl-agent-step{ font-size:var(--tl-fs-sm); color:var(--tl-grey-700); line-height:1.45; }
.tl-agent-step .tl-pill{ margin-right:var(--tl-s1); vertical-align:baseline; }
/* The Checker's switch is absent rather than shown and refused, so the reason has to be on the
   card: a control that is simply missing with no explanation is its own kind of lie. */
.tl-agent-locked{
  margin:var(--tl-s2) 0 0; padding:var(--tl-s1) var(--tl-s2);
  background:var(--tl-info-tint); border-left:3px solid var(--tl-accent);
  font-size:var(--tl-fs-xs); color:var(--tl-grey-700);
}
/* The config version actually in force. Blue, matching the other provenance chips: this is a
   "where did this come from" badge, not a status. */
.tl-pill-blue{ background:var(--tl-info-tint); color:var(--tl-accent-dark); }
/* The validity cards' readiness line (WP-6 item 5). */
.tl-validity-ready{ font-size:var(--tl-fs-xs); color:var(--tl-grey-700); margin:var(--tl-s1) 0; }

.tl-budget-warnings{ margin:var(--tl-s2) 0 0; padding-left:var(--tl-s4); }
.tl-budget-warning{ color:#8A5A00; }

/* `--tl-info` on the grey-50 panel is 4.15:1 at this size; the dark blue clears the floor. */
.tl-prov{ font-size:var(--tl-fs-xs); color:var(--tl-blue-dark); text-decoration:none; }
.tl-prov:hover{ text-decoration:underline; }
.tl-hidden-flag{
  display:inline-block; padding:0 var(--tl-s1); border-radius:var(--tl-r-sm);
  font-size:var(--tl-fs-xs); color:var(--tl-grey-500); background:var(--tl-grey-50);
}

.tl-twin-id{ font-family:var(--tl-mono); color:var(--tl-grey-500);
             font-size:var(--tl-fs-xs); }
.tl-twin-identity{ font-weight:500; color:var(--tl-accent-dark); }
.tl-twin-background, .tl-twin-quality{ color:var(--tl-grey-700); margin-top:var(--tl-s2); }

/* ---- contrast floors (docs/05 §6): body >= 4.5:1, chrome and large text >= 3:1 ----
   Gradio's own defaults render inactive tab labels and nested list text near-invisible against
   this light surface. These are testable minimums, not taste, so they are overridden here rather
   than accepted as a degradation. */
.tl-told li, .tl-told li em, .tl-scenario p{ color:var(--tl-grey-700); }
.tl-told li.tl-absent, .tl-told .tl-absent{ color:var(--tl-grey-500); }
.tl-gap-id{ color:var(--tl-grey-700); font-weight:500; }

/* Gradio's own tab strip, restyled as the prototype's underlined text tabs. The buttons sit
   in `.tab-container`, which is not flexed by default — without this the eight Twin Lab tabs
   run together as one word. */
.tl-subnav .tab-wrapper{ border-bottom:1px solid var(--tl-grey-100) !important; }
.tl-subnav .tab-container{
  display:flex !important; gap:var(--tl-s5) !important; flex-wrap:wrap;
  border:none !important; background:transparent !important;
}
.tl-subnav .tabitem{ border:none !important; padding:var(--tl-s3) 0 0 !important;
                     background:transparent !important; }

/* Statistics' ten sections are pill tabs in the prototype, not underlined text tabs
   (prototype p22): hairline outline pills that fill with blue when selected, wrapping onto a
   second row rather than scrolling. */
.tl-pilltabs .tab-wrapper{ border:none !important; }
.tl-pilltabs .tab-container{
  display:flex !important; flex-wrap:wrap; gap:var(--tl-s2) !important;
  border:none !important; background:transparent !important;
}
.tl-pilltabs button{
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  background:var(--tl-white) !important; color:var(--tl-grey-900) !important;
  padding:6px var(--tl-s4) !important; font-size:var(--tl-fs-md) !important;
  font-weight:400 !important;
}
.tl-pilltabs button.selected, .tl-pilltabs button[aria-selected="true"]{
  background:var(--tl-info) !important; border-color:var(--tl-info) !important;
  color:var(--tl-white) !important; font-weight:500 !important;
}
.tl-pilltabs .tabitem{ border:none !important; background:transparent !important;
                       padding:var(--tl-s4) 0 0 !important; }
/* Scoped to `.tab-container`, which is the tab STRIP.
   `.tl-subnav button` matched every button in the whole tab panel, not only the eight tab
   labels -- including all 243 cells of the Results grid, each of which is a `<button>`. It set
   `background:transparent !important` on them, so the grid painted no fill at all and read as an
   empty outlined table whatever its data said. `docs/05` section 8.3's "tested filled
   white->green by index" could not have been visible on this page. */
.tl-subnav .tab-container button{
  color:var(--tl-grey-500) !important; opacity:1 !important;
  background:transparent !important; border:none !important;
  border-bottom:2px solid transparent !important; border-radius:0 !important;
  font-size:var(--tl-fs-md) !important; font-weight:400 !important;
  padding:var(--tl-s3) 0 10px !important;
}
.tl-subnav .tab-container button.selected,
.tl-subnav .tab-container button[aria-selected="true"]{
  color:var(--tl-accent) !important; font-weight:500 !important;
  border-bottom-color:var(--tl-accent) !important;
}

/* Gradio fills `.block` and every radio/checkbox label with rgb(39,39,42), a near-black slab.
   Against this light surface that puts grey text on near-black and makes whole controls
   unreadable, so the override is page-wide rather than per-component — a later screen must not
   have to rediscover it. */
.tl-page .block,
.tl-page fieldset,
.tl-page .form,
.tl-page .gr-group,
.tl-page .styler,
.tl-page .panel,
.tl-page .wrap{ background:var(--tl-surface) !important; border-color:var(--tl-border); }
/* The label is the caption above a field, not a box around it. It used to carry a surface fill
   AND a 1px border, which drew a second frame around every control — a box inside a box, with
   the label's own trailing space below the input. That was a symptom patch for the near-black
   slab described above, and the slab is now fixed at the token layer (see the `.dark` block at
   the end of this file), so the patch can go and the field is a single framed input again. */
.tl-page label{
  background:transparent !important; color:var(--tl-grey-700) !important;
  border:none !important;
}
.tl-page label span,
.tl-page fieldset > span,
.tl-page .block > span{ color:var(--tl-grey-500) !important; background:transparent !important;
                        font-size:var(--tl-fs-sm) !important; font-weight:500 !important; }
.tl-page textarea,
.tl-page input[type="text"],
.tl-page input[type="number"],
.tl-page select{
  background:var(--tl-surface) !important; color:var(--tl-grey-900) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-sm) !important;
  font-family:var(--tl-font) !important; font-size:var(--tl-fs-md) !important;
}
/* Prompt bodies are read as code in the prototype and are monospaced there. */
.tl-mono textarea{ font-family:var(--tl-mono) !important; font-size:var(--tl-fs-sm) !important; }
.tl-page textarea::placeholder,
.tl-page input::placeholder{ color:var(--tl-grey-500) !important; }
.tl-page code{
  background:var(--tl-grey-50); color:var(--tl-grey-900);
  padding:1px var(--tl-s1); border-radius:var(--tl-r-sm);
  font-family:var(--tl-mono); font-size:var(--tl-fs-sm);
}

/* ---- buttons. The prototype: a filled accent pill for the primary action, a hairline
        outline pill for the secondary, and a red-lettered outline for the destructive. ---- */
.tl-page button.primary, .tl-page .tl-btn-primary button, button.tl-btn-primary{
  background:var(--tl-accent) !important; color:var(--tl-white) !important;
  border:1px solid var(--tl-accent) !important; border-radius:var(--tl-r-pill) !important;
  font-weight:500 !important; font-size:var(--tl-fs-md) !important;
  padding:var(--tl-s2) var(--tl-s5) !important; box-shadow:none !important;
}
.tl-page button.primary:hover, .tl-page .tl-btn-primary button:hover{
  background:var(--tl-accent-dark) !important; border-color:var(--tl-accent-dark) !important;
}
.tl-page button.secondary, .tl-page .tl-btn-secondary button{
  background:var(--tl-white) !important; color:var(--tl-accent) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  font-weight:500 !important; font-size:var(--tl-fs-md) !important;
  padding:var(--tl-s2) var(--tl-s5) !important; box-shadow:none !important;
}
.tl-page button.secondary:hover, .tl-page .tl-btn-secondary button:hover{
  background:var(--tl-accent-tint) !important;
}
.tl-page .tl-btn-danger button{
  background:var(--tl-white) !important; color:var(--tl-bad) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
}
.tl-page .tl-btn-danger button:hover{ background:var(--tl-bad-tint) !important; }
/* A disabled action still has to say it is disabled, not merely look faint (docs/05 §5). */
.tl-page button:disabled{ opacity:.45 !important; cursor:not-allowed !important; }

/* The dial row: one pill-shaped group, the chosen step filled inside it (prototype p6). */
.tl-dial-row{
  border:none !important; padding:0 !important; background:transparent !important;
  display:flex !important; align-items:center; gap:var(--tl-s3); margin-bottom:var(--tl-s2);
}
/* The lever name sits to the LEFT of the pill group (prototype p6), not above it. */
.tl-dial-row > span{
  flex:0 0 110px; font-weight:500 !important; color:var(--tl-grey-900) !important;
  font-size:var(--tl-fs-md) !important;
}
.tl-dial-row > .wrap.hide{ display:none !important; }
/* `:has(> label)` picks the radio group's own wrap. A `gr.Radio` fieldset also contains
   Gradio's loading overlay, which is a `.wrap` too — giving that one a pill border draws a
   stray empty capsule above every dial. */
.tl-dial-row .wrap:has(> label){
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  overflow:hidden; display:flex !important; gap:0 !important;
  background:var(--tl-white) !important; width:100%;
}
.tl-dial-row label{
  flex:0 0 auto; border:none !important; border-radius:0 !important;
  background:transparent !important; color:var(--tl-grey-900) !important;
  padding:var(--tl-s2) var(--tl-s4) !important; margin:0 !important;
  font-size:var(--tl-fs-md) !important; box-shadow:none !important;
}
/* The segment's text lives in a `span`, and the page-wide `.tl-page .block > span` rule paints
   every such span grey-500. On a filled segment that is #5F6368 on #CD3021 -- about 1.6:1,
   well under the 4.5:1 floor (docs/05 §6) -- so each segment's span carries its own colour
   rather than inheriting the label's. */
.tl-dial-row label span, .tl-toggle label span{
  color:var(--tl-grey-900) !important; font-size:var(--tl-fs-md) !important;
  font-weight:400 !important; white-space:nowrap;
}
.tl-dial-row label:nth-of-type(1).selected span,
.tl-dial-row label:nth-of-type(3).selected span,
.tl-toggle label.selected span{ color:var(--tl-white) !important; font-weight:500 !important; }
.tl-dial-row label:nth-of-type(2).selected span{
  color:#3C2A00 !important; font-weight:500 !important;
}

/* The native radio dot is replaced by the filled segment; leaving it visible puts a bullet
   inside each pill, which the prototype does not have. */
.tl-dial-row label input[type="radio"], .tl-toggle label input[type="radio"]{
  appearance:none !important; -webkit-appearance:none !important;
  position:absolute !important; opacity:0 !important; width:0 !important; height:0 !important;
  margin:0 !important; border:none !important;
}

/* `docs/05` §7 rule 1: dials are red / amber / green for 0 / 1 / 2 — a traffic light for
   PROTECTION LEVEL, matching the legend, never for sign. The three options are one radio group,
   so the step is identified by position: first label is dial 0, third is dial 2. */
.tl-dial-row label:nth-of-type(1).selected{
  background:var(--tl-dial-0) !important; color:var(--tl-white) !important; font-weight:500;
  border-radius:var(--tl-r-pill) 0 0 var(--tl-r-pill) !important;
}
.tl-dial-row label:nth-of-type(2).selected{
  background:var(--tl-dial-1) !important; color:#3C2A00 !important; font-weight:500;
}
.tl-dial-row label:nth-of-type(3).selected{
  background:var(--tl-dial-2) !important; color:var(--tl-white) !important; font-weight:500;
}

/* Twin Studio's mode switch and Statistics' tab strip are pill toggles, not dials: the
   selected one is a filled blue pill, the rest are hairline outlines (prototype p12, p22). */
.tl-toggle{ border:none !important; padding:0 !important; background:transparent !important; }
.tl-toggle .wrap:has(> label){ display:flex !important; gap:var(--tl-s2) !important;
                  flex-wrap:wrap; border:none !important; background:transparent !important; }
.tl-toggle label{
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  padding:var(--tl-s2) var(--tl-s4) !important; background:var(--tl-white) !important;
  color:var(--tl-grey-900) !important; font-size:var(--tl-fs-md) !important;
}
.tl-toggle label.selected{
  background:var(--tl-info) !important; border-color:var(--tl-info) !important;
  color:var(--tl-white) !important; font-weight:500;
}
.tl-toggle label input{ position:absolute; opacity:0; width:0; height:0; }

/* M14 — the Research model page (docs/06 §8).

   The diagram degrades to a layered board and its edges are always listed beneath it
   (CLAUDE.md: degrade the styling, never the content). It scrolls horizontally rather than
   wrapping, because a wrapped layer stops being a layer. */
.tl-lede{ font-size:var(--tl-fs-lg); color:var(--tl-grey-900); }
.tl-muted{ color:var(--tl-grey-500); font-style:italic; }
.tl-diagram{
  display:flex; gap:var(--tl-s5); overflow-x:auto; padding:var(--tl-s4) 0;
  align-items:flex-start;
}
.tl-layer{ display:flex; flex-direction:column; gap:var(--tl-s3); min-width:180px; }
.tl-layer-head{
  font-size:var(--tl-fs-sm); font-weight:500; color:var(--tl-grey-900);
  text-transform:uppercase; letter-spacing:.06em; text-align:center;
}
.tl-layer-sub{ font-size:var(--tl-fs-xs); color:var(--tl-accent); font-style:italic;
               text-align:center; margin-top:2px; }
.tl-node{
  background:var(--tl-surface); border:1px solid var(--tl-grey-300);
  border-radius:var(--tl-r-sm); padding:var(--tl-s2) var(--tl-s3); text-align:center;
}
.tl-node, .tl-node div{ color:var(--tl-grey-700); }
.tl-node > strong{ color:var(--tl-grey-900); font-weight:700; }
.tl-node-sub{ font-size:var(--tl-fs-xs); color:var(--tl-accent); }
/* The gap badges on the Research model page (prototype p31-p33). */
.tl-gap-badge{
  display:inline-block; padding:1px var(--tl-s2); border-radius:var(--tl-r-sm);
  background:var(--tl-red); color:var(--tl-white);
  font-size:var(--tl-fs-xs); font-weight:500; margin-right:var(--tl-s2);
}
/* An RQ card carries a 3px accent rule on its left edge, as the prototype does. */
.tl-rq{ border-left:3px solid var(--tl-accent); padding-left:var(--tl-s3); }
.tl-rq-id{ color:var(--tl-accent); font-weight:700; margin-right:var(--tl-s2); }
.tl-rq-kicker{ color:var(--tl-grey-500); font-size:var(--tl-fs-xs);
               text-transform:uppercase; letter-spacing:.06em; }

/* Visible focus ring on every interactive element (docs/05 §6). */
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible,
textarea:focus-visible{ outline:2px solid var(--tl-accent); outline-offset:2px; }


/* ==================================================================================
   DARK MODE, NEUTRALISED. Read this before changing any colour above.

   Gradio applies a `.dark` class from the browser's `prefers-color-scheme`, and its dark theme
   re-points ~234 of its own custom properties. Twin Lab is a light design measured off the
   prototype (D-UI-01): every surface above is forced white. The two together put dark-theme
   TEXT on forced-WHITE surfaces — the help accordion's labels computed to #F4F4F5 on #FFFFFF,
   a contrast ratio of 1.05:1, which is invisible. The researcher reported it as "I cannot see
   the headings", and it was also why dropdown labels read paler than textbox labels: only the
   selectors the overrides happened to catch were being repaired, one at a time.

   Fixed at the token layer rather than per component, because a per-component repair is a list
   that is never finished. Every Gradio token that carries a colour in dark mode is re-pointed
   here to the twinlab token that means the same thing in the light design. Tokens that DERIVE
   from these (`--accordion-text-color`, `--table-text-color`, `--checkbox-label-text-color`,
   `--block-info-text-color` and the rest) follow automatically and are deliberately not listed.

   A JS redirect to `?__theme=light` is the approach Gradio documents. It is not used: it costs
   a full reload on every one of the eight routes, and a screen that flashes dark then reloads
   is worse than one that was never dark. This has no reload and no flash.

   `tests/test_m10_ui.py` walks the rendered DOM and fails on any text below the 4.5:1 floor
   `docs/05` §6 states, so a token missed here is caught rather than shipped.
   ================================================================================== */
.dark, gradio-app.dark, .dark .gradio-container{
  /* text */
  --body-text-color:var(--tl-grey-900);
  --body-text-color-subdued:var(--tl-grey-500);
  --block-label-text-color:var(--tl-grey-700);
  --block-title-text-color:var(--tl-grey-700);
  --input-placeholder-color:var(--tl-grey-500);

  /* surfaces */
  --background-fill-primary:var(--tl-white);
  --background-fill-secondary:var(--tl-grey-50);
  --body-background-fill:var(--tl-bg);
  --block-background-fill:var(--tl-surface);
  --panel-background-fill:var(--tl-surface);
  --block-label-background-fill:var(--tl-surface);
  --block-title-background-fill:transparent;
  --input-background-fill:var(--tl-surface);
  --input-background-fill-focus:var(--tl-surface);
  --input-background-fill-hover:var(--tl-surface);
  --code-background-fill:var(--tl-grey-50);
  --stat-background-fill:var(--tl-accent-tint);

  /* borders */
  --border-color-primary:var(--tl-border);
  --border-color-accent:var(--tl-accent);
  --block-border-color:var(--tl-border);
  --panel-border-color:var(--tl-border);
  --block-label-border-color:var(--tl-border);
  --input-border-color:var(--tl-grey-300);
  --input-border-color-focus:var(--tl-accent);
  --input-border-color-hover:var(--tl-grey-300);

  /* tables */
  --table-text-color:var(--tl-grey-900);
  --table-border-color:var(--tl-grey-100);
  --table-even-background-fill:var(--tl-white);
  --table-odd-background-fill:var(--tl-grey-50);

  /* controls. The secondary button's dark text colour is a literal `white`, which the
     twinlab button rules above already override — it is re-pointed anyway so a Gradio
     control this design has not styled yet does not arrive unreadable. */
  --button-secondary-text-color:var(--tl-accent);
  --button-secondary-text-color-hover:var(--tl-accent-dark);
  --button-secondary-background-fill:var(--tl-white);
  --button-secondary-background-fill-hover:var(--tl-accent-tint);
  --button-secondary-border-color:var(--tl-grey-300);
  --button-cancel-text-color:var(--tl-bad);
  --button-cancel-background-fill:var(--tl-white);
  --checkbox-background-color:var(--tl-surface);
  --checkbox-background-color-hover:var(--tl-grey-50);
  --checkbox-border-color:var(--tl-grey-300);
  --checkbox-label-background-fill:var(--tl-surface);
  --checkbox-label-background-fill-hover:var(--tl-grey-50);

  /* semantic. These keep their fixed meanings (docs/05 §7) and never follow the route accent. */
  --link-text-color:var(--tl-info);
  --link-text-color-hover:var(--tl-info);
  --link-text-color-active:var(--tl-info);
  --link-text-color-visited:var(--tl-info);
  --error-text-color:var(--tl-bad);
  --error-background-fill:var(--tl-bad-tint);
  --error-border-color:var(--tl-bad);
  --error-icon-color:var(--tl-bad);
  --loader-color:var(--tl-accent);
  --slider-color:var(--tl-accent);
}
/* The accordion is what the researcher actually could not read. Gradio's `.label-wrap` is a
   `<span>`, so it is caught by neither `.tl-page label span` nor `.tl-page .block > span`. */
.tl-page .label-wrap,
.tl-page .label-wrap > span{
  color:var(--tl-grey-900) !important; background:transparent !important;
  font-size:var(--tl-fs-md) !important; font-weight:500 !important;
}
.tl-page .label-wrap .icon{ color:var(--tl-grey-500) !important; }

/* Gradio ships a `visually-hidden` duplicate of every tab strip for screen readers. The two
   rules below used to set `display:flex !important` on `.tab-container` unconditionally, which
   beat the clip that hides it — so every tab label rendered twice, on Twin Lab and on
   Statistics. Excluding the hidden copy restores it to screen readers only. */
.tl-subnav .tab-container.visually-hidden,
.tl-pilltabs .tab-container.visually-hidden{
  display:none !important;
}

/* ==================================================================================
   D-UI-02 — the surfaces added when the Generator, the Studio, the validity board and the
   Results grid were brought to parity with the prototype. See `docs/DECISIONS.md`.
   ================================================================================== */

/* ---- a bordered panel: the prototype groups controls into titled cards, not bare stacks.
   `elem_classes` on a `gr.Group` lands on Gradio's own wrapper, which already draws a border and
   a radius, so this repaints rather than nests. ---- */
.tl-page .tl-panel{
  background:var(--tl-surface) !important; border:1px solid var(--tl-border) !important;
  border-radius:var(--tl-r-md) !important; padding:var(--tl-s4) !important;
  margin-bottom:var(--tl-s4) !important; box-shadow:var(--tl-shadow-card) !important;
  overflow:visible !important;
}
/* A panel's own section title must not carry the page-level top margin, or every card opens
   with a gap the prototype does not have. */
.tl-page .tl-panel .tl-section:first-child{ margin-top:0; }

/* ---- a slider row: label left, track right, value at the end (prototype p2, p4).
   Gradio stacks the label above a full-width track, which at nine sliders in a column reads as a
   wall. The label is given a fixed column so the tracks line up and the row is scannable. ---- */
.tl-page .tl-slider-row{ margin-bottom:var(--tl-s2) !important; }
.tl-page .tl-slider-row > label{
  display:flex !important; align-items:center !important; gap:var(--tl-s3) !important;
  margin:0 !important;
}
.tl-page .tl-slider-row > label > span{
  flex:0 0 156px; color:var(--tl-grey-900) !important; font-size:var(--tl-fs-md) !important;
  font-weight:400 !important; line-height:1.35; white-space:normal;
}
/* Gradio puts the track and the number box in the same flex line as the label's text. */
.tl-page .tl-slider-row input[type="range"]{ flex:1 1 auto !important; min-width:80px; }
.tl-page .tl-slider-row input[type="number"]{
  flex:0 0 52px !important; text-align:right; padding:2px var(--tl-s2) !important;
  border:none !important; background:transparent !important; box-shadow:none !important;
  color:var(--tl-grey-900) !important; font-size:var(--tl-fs-md) !important;
}

/* The 1-7 anchors above the construct sliders (prototype p1). */
.tl-scale-ends{
  display:flex; justify-content:space-between; color:var(--tl-grey-500);
  font-size:var(--tl-fs-xs); margin:var(--tl-s2) 0 var(--tl-s1);
  padding-left:156px;
}

/* ---- Twin Studio's pickers.
   The dropdown and the "Twin in use" box both rendered as unlabelled fields with number-spinner
   arrows, and long option text ran outside the box -- which is what the researcher reported as
   "some letters are not even in the box". The label is forced back to a block above the control,
   the spinners are removed from controls that are not numbers, and the option text wraps
   instead of overflowing. ---- */
.tl-page .tl-field{ border:none !important; background:transparent !important;
                    padding:0 !important; }
.tl-page .tl-picker label > span,
.tl-page .tl-field label > span{
  display:block !important; color:var(--tl-grey-700) !important;
  font-size:var(--tl-fs-sm) !important; font-weight:500 !important;
  margin-bottom:var(--tl-s1) !important;
}
.tl-page .tl-picker input,
.tl-page .tl-picker .wrap-inner{
  min-height:34px; font-size:var(--tl-fs-md) !important;
  color:var(--tl-grey-900) !important;
}
/* A `gr.Dropdown` is a text input plus a listbox; it must never show number spinners. */
.tl-page .tl-picker input[type="number"]::-webkit-outer-spin-button,
.tl-page .tl-picker input[type="number"]::-webkit-inner-spin-button{
  -webkit-appearance:none !important; margin:0 !important;
}
.tl-page .tl-picker ul.options li,
.tl-page .tl-picker .item{
  white-space:normal !important; word-break:break-word; line-height:1.4;
  font-size:var(--tl-fs-md) !important;
}

/* The persona panel: monospace, scrolling, and headed in the prototype's words. */
.tl-persona-panel{
  border:1px solid var(--tl-border); border-radius:var(--tl-r-md);
  background:var(--tl-grey-50); margin-top:var(--tl-s3); overflow:hidden;
}
.tl-persona-head{
  padding:var(--tl-s2) var(--tl-s3); border-bottom:1px solid var(--tl-grey-100);
  font-size:var(--tl-fs-xs); font-weight:500; letter-spacing:.06em;
  text-transform:uppercase; color:var(--tl-grey-700); background:var(--tl-surface);
}
.tl-persona-panel .tl-persona{ margin:0; padding:var(--tl-s3); }

/* The version line under the Studio's dials, in the prototype's own words. */
.tl-version-line{ margin:var(--tl-s3) 0; color:var(--tl-grey-700);
                  font-size:var(--tl-fs-md); }
.tl-version-code{ font-family:var(--tl-mono); font-size:var(--tl-fs-lg);
                  color:var(--tl-grey-900); letter-spacing:.12em; }

/* ---- the validity board (docs/05 §8, docs/06 §3.5).
   Each card holds its own Run control, so the eight cards ARE the eight controls and there is no
   separate button list to match up by hand. ---- */
.tl-page .tl-validity-grid{ flex-wrap:wrap !important; gap:var(--tl-s3) !important; }
.tl-page .tl-validity-card{
  background:var(--tl-surface) !important; border:1px solid var(--tl-border) !important;
  border-radius:var(--tl-r-md) !important; padding:var(--tl-s4) !important;
  box-shadow:var(--tl-shadow-card) !important; height:100%;
  display:flex !important; flex-direction:column !important;
}
.tl-validity-head{
  display:flex; align-items:baseline; gap:var(--tl-s2); flex-wrap:wrap;
  margin-bottom:var(--tl-s2);
}
.tl-validity-name{ font-weight:500; color:var(--tl-grey-900); font-size:var(--tl-fs-lg); }
.tl-validity-q{ color:var(--tl-grey-900); font-weight:500; margin-bottom:var(--tl-s2); }
.tl-validity-what{ color:var(--tl-grey-700); font-size:var(--tl-fs-sm); line-height:1.55; }
/* The button is pushed to the card's foot so eight cards of different text lengths still line
   their controls up. */
.tl-page .tl-validity-card .tl-run-pill{ margin-top:auto !important; }

/* The Run control: a filled green pill with white text and an arrow. Green is `--tl-ok`, whose
   fixed meaning (docs/05 §7) is PASS / good -- correct for "run this check", and deliberately
   not the route accent. */
.tl-page .tl-run-pill button,
.tl-page button.tl-run-pill{
  background:var(--tl-ok) !important; border:1px solid var(--tl-ok) !important;
  color:var(--tl-white) !important; border-radius:var(--tl-r-pill) !important;
  font-weight:500 !important; font-size:var(--tl-fs-md) !important;
  padding:var(--tl-s2) var(--tl-s5) !important; box-shadow:none !important;
  align-self:flex-start; margin-top:var(--tl-s3) !important;
}
.tl-page .tl-run-pill button:hover,
.tl-page button.tl-run-pill:hover{
  background:#256A2D !important; border-color:#256A2D !important;
}
.tl-page .tl-run-pill button:disabled{ opacity:.45 !important; }

/* A quiet secondary action: hairline pill, accent text. Used for "Preview 3 drivers" and
   "Show what the twin is told", both of which the prototype draws as outlines. */
.tl-page .tl-btn-quiet button,
.tl-page button.tl-btn-quiet{
  background:var(--tl-white) !important; color:var(--tl-accent) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  font-weight:500 !important; box-shadow:none !important;
}
.tl-page .tl-btn-quiet button:hover,
.tl-page button.tl-btn-quiet:hover{ background:var(--tl-accent-tint) !important; }

@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{ animation-duration:.01ms !important;
                        transition-duration:.01ms !important; }
}

/* ===================================================================== the hosted survey
   The driver-facing questionnaire (/take). A different reader from every other page in this
   application: one person on a phone, once, who is not a researcher and has no nav strip. So the
   page is a single narrow column, the type is larger than the researcher screens, and the only
   two controls always on screen are Back and Continue.

   docs/05 is a researcher design system; where the two disagree the driver wins here, because a
   mis-tapped rating is a data defect and a cramped researcher table is an inconvenience. */

.tl-survey{ max-width:720px; margin:0 auto; padding:0 var(--tl-s4) 7rem; }
.tl-survey .tl-sv-kicker{
  display:flex; justify-content:space-between; align-items:baseline;
  font-size:var(--tl-fs-sm); font-weight:600; color:var(--tl-grey-700);
  padding-top:var(--tl-s4);
}
.tl-survey .tl-sv-kicker span:last-child{ font-weight:400; color:var(--tl-grey-500); }

/* The progress rail: one dot per stop, filled up to the current one. A bar alone cannot say
   "nine stops" and the reference screens show both, so both are drawn. */
.tl-sv-rail{ display:flex; align-items:center; gap:0; margin:var(--tl-s2) 0 var(--tl-s3); }
.tl-sv-rail .dot{
  width:11px; height:11px; border-radius:50%; flex:0 0 auto;
  background:var(--tl-white); border:2px solid var(--tl-grey-300);
}
.tl-sv-rail .dot.done{ background:var(--tl-accent); border-color:var(--tl-accent); }
.tl-sv-rail .seg{ height:2px; flex:1 1 auto; background:var(--tl-grey-300); }
.tl-sv-rail .seg.done{ background:var(--tl-accent); }
.tl-sv-underline{ height:3px; background:var(--tl-grey-200); border-radius:2px; overflow:hidden; }
.tl-sv-underline i{ display:block; height:3px; background:var(--tl-orange); border-radius:2px; }

.tl-survey h1.tl-sv-title{
  font-family:var(--tl-font-head); font-size:1.75rem; line-height:1.25;
  margin:var(--tl-s2) 0 var(--tl-s2); color:var(--tl-grey-900);
}
.tl-survey .tl-sv-part{
  font-size:var(--tl-fs-sm); color:var(--tl-grey-500); margin-top:var(--tl-s3);
}
.tl-survey .tl-sv-intro{ color:var(--tl-grey-700); line-height:1.6; margin-bottom:var(--tl-s3); }
.tl-survey .tl-sv-body p{ color:var(--tl-grey-700); line-height:1.65; margin:0 0 var(--tl-s2); }
.tl-survey .tl-sv-body h3{
  font-size:1rem; margin:var(--tl-s4) 0 var(--tl-s2);
  padding-left:var(--tl-s2); border-left:3px solid var(--tl-accent);
}
.tl-sv-callout{
  background:var(--tl-white); border:1px solid var(--tl-grey-300);
  border-radius:var(--tl-r-md); padding:var(--tl-s3) var(--tl-s4); margin:var(--tl-s3) 0;
}
.tl-sv-callout strong{ display:block; margin-bottom:var(--tl-s2); }
.tl-sv-callout ul{ margin:0; padding-left:1.1rem; }
.tl-sv-callout li{ color:var(--tl-accent-dark); margin:var(--tl-s1) 0; }

/* A block heading, and the scale note that governs the items under it. The note is stated once
   per block because that is how the instrument reads on paper; repeating it under every item
   would be a different questionnaire to answer. */
.tl-sv-block{ margin:var(--tl-s5) 0 var(--tl-s2); }
.tl-sv-block h2{
  font-family:var(--tl-font-head); font-size:1.15rem; margin:0 0 var(--tl-s1);
  color:var(--tl-grey-900);
}
.tl-sv-block .note{ font-size:var(--tl-fs-sm); color:var(--tl-grey-500); }
.tl-sv-block .lever{ margin:var(--tl-s1) 0; color:var(--tl-grey-700); line-height:1.55; }

/* One question, one card. Gradio wraps every component in its own div, so the card is drawn on
   the Group and the inner wrappers are flattened rather than fought with. */
.tl-survey .tl-q{
  background:var(--tl-white); border:1px solid var(--tl-grey-300);
  border-radius:var(--tl-r-md); padding:var(--tl-s3) var(--tl-s4);
  margin-bottom:var(--tl-s3); box-shadow:none;
}
.tl-survey .tl-q .tl-q-stem{
  font-size:1rem; color:var(--tl-grey-900); line-height:1.5; margin-bottom:var(--tl-s2);
}
.tl-survey .tl-q .tl-q-anchors{
  display:flex; justify-content:space-between; gap:var(--tl-s2);
  font-size:var(--tl-fs-xs); color:var(--tl-grey-500);
}
.tl-survey .tl-q .tl-q-help{ font-size:var(--tl-fs-xs); color:var(--tl-grey-500); }

/* Likert, drawn as a row of numbered boxes. Gradio has no button-group control, so this is a
   radio restyled — docs/05's rule is to degrade the styling and never the content, and the
   content here is "N boxes, one per scale point, numbered and selectable". */
.tl-survey .tl-likert .wrap,
.tl-survey .tl-likert > div:last-child{
  display:grid !important; grid-auto-flow:column; grid-auto-columns:1fr;
  gap:var(--tl-s2); align-items:stretch;
}
.tl-survey .tl-likert label{
  display:flex !important; align-items:center; justify-content:center;
  min-height:44px; margin:0 !important; padding:var(--tl-s2) 0 !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-sm) !important;
  background:var(--tl-white) !important; cursor:pointer; font-weight:500;
  font-variant-numeric:tabular-nums;
}
.tl-survey .tl-likert label:hover{ border-color:var(--tl-accent) !important; }
.tl-survey .tl-likert label.selected,
.tl-survey .tl-likert label:has(input:checked){
  background:var(--tl-accent) !important; border-color:var(--tl-accent) !important;
  color:var(--tl-white) !important;
}
.tl-survey .tl-likert label.selected span,
.tl-survey .tl-likert label:has(input:checked) span{ color:var(--tl-white) !important; }
.tl-survey .tl-likert input[type="radio"]{ position:absolute; opacity:0; width:0; height:0; }
.tl-survey .tl-likert span{ font-size:1rem; }

/* Yes/No and the consent ticks: wide boxes and a full-width row, not a cramped inline pair. */
.tl-survey .tl-yesno .wrap,
.tl-survey .tl-yesno > div:last-child{
  display:grid !important; grid-template-columns:1fr 1fr; gap:var(--tl-s3);
}
.tl-survey .tl-yesno label{
  display:flex !important; align-items:center; gap:var(--tl-s2);
  min-height:48px; margin:0 !important; padding:0 var(--tl-s3) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-sm) !important;
  background:var(--tl-white) !important; cursor:pointer;
}
.tl-survey .tl-yesno label:has(input:checked){
  border-color:var(--tl-accent) !important; background:var(--tl-accent-tint) !important;
}
.tl-survey .tl-consent label{
  display:flex !important; align-items:flex-start; gap:var(--tl-s3);
  padding:var(--tl-s3) var(--tl-s4) !important; line-height:1.5;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-sm) !important;
  background:var(--tl-white) !important;
}
.tl-survey .tl-consent label span{ color:var(--tl-accent-dark); }
.tl-survey .tl-choice label{
  display:flex !important; align-items:center; gap:var(--tl-s2);
  min-height:44px; padding:0 var(--tl-s3) !important; margin:0 0 var(--tl-s2) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-sm) !important;
  background:var(--tl-white) !important; cursor:pointer;
}
.tl-survey .tl-choice label:has(input:checked){
  border-color:var(--tl-accent) !important; background:var(--tl-accent-tint) !important;
}

/* The footer is sticky because the reference screens fix it: on a phone the driver must be able
   to leave a long stop without scrolling to its end. */
.tl-sv-footer{
  position:sticky; bottom:0; z-index:40;
  background:var(--tl-white); border-top:1px solid var(--tl-grey-300);
  padding:var(--tl-s3) var(--tl-s4); margin:var(--tl-s4) calc(-1 * var(--tl-s4)) 0;
  display:flex; gap:var(--tl-s3); align-items:center;
}
.tl-sv-footer .tl-sv-back button{
  background:var(--tl-white) !important; color:var(--tl-grey-700) !important;
  border:1px solid var(--tl-grey-300) !important; border-radius:var(--tl-r-pill) !important;
  min-width:96px;
}
.tl-sv-footer .tl-sv-next{ flex:1 1 auto; }
.tl-sv-footer .tl-sv-next button{
  background:var(--tl-accent) !important; color:var(--tl-white) !important;
  border:none !important; border-radius:var(--tl-r-pill) !important;
  min-height:52px; font-size:1.05rem; font-weight:600;
}
.tl-sv-footer .tl-sv-next button:hover{ background:var(--tl-accent-dark) !important; }

.tl-sv-error{
  background:#FDECEC; border:1px solid var(--tl-bad); color:#8A1C1C;
  border-radius:var(--tl-r-sm); padding:var(--tl-s3) var(--tl-s4); margin:var(--tl-s3) 0;
  line-height:1.5;
}
.tl-sv-done{
  background:var(--tl-white); border:1px solid var(--tl-grey-300);
  border-radius:var(--tl-r-md); padding:var(--tl-s5);
}
.tl-sv-done .ref{
  font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:1.15rem;
  letter-spacing:.02em; background:var(--tl-grey-100); border:1px dashed var(--tl-grey-300);
  border-radius:var(--tl-r-sm); padding:var(--tl-s3); margin:var(--tl-s3) 0; word-break:break-all;
}

@media (max-width:560px){
  .tl-survey{ padding:0 var(--tl-s3) 7rem; }
  .tl-survey h1.tl-sv-title{ font-size:1.45rem; }
  /* Seven boxes do not fit a phone in one row, so the Likert row wraps rather than shrinking the
     tap targets below 44px. A mis-tap is a data defect, not a cosmetic problem. */
  .tl-survey .tl-likert .wrap,
  .tl-survey .tl-likert > div:last-child{
    grid-auto-flow:row; grid-template-columns:repeat(4, 1fr);
  }
  .tl-survey .tl-yesno .wrap,
  .tl-survey .tl-yesno > div:last-child{ grid-template-columns:1fr; }
}

/* A why-probe is a continuation of the rating above it, not a question in its own right: it
   joins the card above by losing its top border and its gap, and its wording is quiet. The
   driver should read "rate this, and optionally say why", not "answer two questions". */
.tl-survey .tl-q-why{
  margin-top:calc(-1 * var(--tl-s3) - 1px);
  border-top-left-radius:0; border-top-right-radius:0;
  border-top:1px dashed var(--tl-grey-300);
  padding-top:var(--tl-s2);
}
.tl-survey .tl-q-why-stem{
  font-size:var(--tl-fs-sm); color:var(--tl-grey-500); font-weight:500;
  margin-bottom:var(--tl-s1);
}
.tl-survey .tl-q-why textarea{ font-size:var(--tl-fs-sm); }

/* A consent statement is its own tick-box label; the card would be a second box around it. */
.tl-survey .tl-q-bare{
  background:transparent; border:none; padding:0; margin-bottom:var(--tl-s3); box-shadow:none;
}

/* A numeric answer is a text box (see ui/pages/survey_take.py), so it is narrowed here rather
   than stretching a four-character answer across the whole column. */
.tl-survey .tl-numbox input{ max-width:220px; }

/* The Part 15/16 stimulus. Set apart as a quotation because it is the one thing on the page the
   driver is asked to treat as true rather than to answer — and because which story appears here
   is the experiment (docs/01 section 5). */
.tl-survey .tl-sv-story{
  border-left:4px solid var(--tl-accent); background:var(--tl-accent-tint);
  border-radius:0 var(--tl-r-sm) var(--tl-r-sm) 0;
  padding:var(--tl-s3) var(--tl-s4); margin:var(--tl-s3) 0;
  color:var(--tl-grey-900); line-height:1.6; font-size:1.02rem;
}
"""
