"""Generate apps_script/build_form.gs — an Apps Script that builds the whole Form.

Titles come straight out of config/form_map.yaml and the narratives out of the survey document,
so nothing is ever transcribed by hand. That is the point: a Form built by this script cannot
have a stray em dash in it.
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(".")
MAP = yaml.safe_load((ROOT / "config/form_map.yaml").read_text(encoding="utf-8"))["map"]
INSTRUMENT = json.loads((ROOT / "data/reference/instrument.json").read_text(encoding="utf-8"))
ITEMS = {i["item_id"]: i for i in INSTRUMENT["items"]}
SCALES = INSTRUMENT["scales"]
SURVEY = (ROOT / "additional_data/Survey_Research_GIGWORKER_v2.md").read_text(encoding="utf-8")

EM = "—"


# ----------------------------------------------------------------- narratives


def unwrap(text: str) -> str:
    """Markdown hard-wraps at 100 columns; a Form description should flow."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    out = []
    for block in text.split("\n\n"):
        out.append(" ".join(line.strip() for line in block.splitlines() if line.strip()))
    return "\n\n".join(b for b in out if b)


def part15_story() -> str:
    block = SURVEY[SURVEY.index("## PART 15"): SURVEY.index("## PART 16")]
    quoted = [ln.lstrip("> ").rstrip() for ln in block.splitlines() if ln.startswith(">")]
    return " ".join(q for q in quoted if q)


def part16_intro() -> str:
    return (
        part15_story()
        + "\n\nPlease answer every statement again, as if the story were true."
    )


def version_narratives() -> dict[int, str]:
    tail = SURVEY[SURVEY.index("### Version 1 of 6"):]
    chunks = re.split(r"### Version (\d) of 6", tail)
    out = {}
    for i in range(1, len(chunks), 2):
        body = chunks[i + 1].split("\n---")[0].strip()
        out[int(chunks[i])] = unwrap(body)
    return out


NARRATIVES = version_narratives()
assert len(NARRATIVES) == 6

SECTION_INTRO = {
    f"PART 1 {EM} A FEW QUICK CHECKS": "Please answer each question.",
    f"PART 2 {EM} YOUR AGREEMENT": (
        "Please read each statement and tick the box to show you agree. "
        "You must agree to all of them to take part."
    ),
    f"PART 5 {EM} THE APP AND YOUR WORK": (
        "Please select the number that best matches your experience."
    ),
    f"PART 6 {EM} HOW THE APP GUIDES YOU": (
        "The next statements are about the Uber app's algorithm. "
        "Please select the number that best matches your experience."
    ),
    f"PART 7 {EM} HOW FAIR THE APP IS": (
        "Please answer each question about how the app matches you to work and evaluates you."
    ),
    f"PART 9 {EM} YOUR JOB": "Please think about your work with Uber as your job when you answer.",
    f"PART 14 {EM} YOUR WORK IN YOUR OWN WORDS": (
        "Write a few sentences for each question. You may skip any question."
    ),
    f"PART 15 {EM} IMAGINE A CHANGE": (
        "Please read the short story below carefully and imagine it is true for your work "
        "with Uber.\n\n" + part15_story()
    ),
    f"PART 16 {EM} IMAGINING THE STORY IS TRUE": part16_intro(),
    **{
        f"PART 17 {EM} SIX VERSIONS {EM} Version {n} of 6": NARRATIVES[n]
        for n in range(1, 7)
    },
}


# --------------------------------------------------------------- the questions

SECTION_ORDER = [
    f"PART 1 {EM} A FEW QUICK CHECKS",
    f"PART 2 {EM} YOUR AGREEMENT",
    f"PART 3 {EM} ABOUT YOU AND YOUR WORK",
    f"PART 4 {EM} YOUR BACKGROUND",
    f"PART 5 {EM} THE APP AND YOUR WORK",
    f"PART 6 {EM} HOW THE APP GUIDES YOU",
    f"PART 7 {EM} HOW FAIR THE APP IS",
    f"PART 8 {EM} HOW CLEAR THE APP IS",
    f"PART 9 {EM} YOUR JOB",
    f"PART 10 {EM} STAYING WITH UBER",
    f"PART 11 {EM} WORKING AROUND THE APP",
    f"PART 12 {EM} LEAVING UBER",
    f"PART 13 {EM} YOUR INCOME",
    f"PART 14 {EM} YOUR WORK IN YOUR OWN WORDS",
    f"PART 15 {EM} IMAGINE A CHANGE",
    f"PART 16 {EM} IMAGINING THE STORY IS TRUE",
    *[f"PART 17 {EM} SIX VERSIONS {EM} Version {n} of 6" for n in range(1, 7)],
]

CHOICES = {
    "field:service": ["Cab (Uber Go or Premier)", "Auto rickshaw", "Motorcycle"],
    "field:city": ["Mumbai", "Pune", "Delhi NCR", "Jaipur", "Bengaluru"],
    "field:gender": ["Woman", "Man", "Another identity", "Prefer not to say"],
    "background:platform_count": ["1", "2", "3 or more"],
    "background:vehicle_arrangement": [
        "Own outright",
        "Own with a loan",
        "Rent from an Uber fleet partner",
        "Rent from someone else",
    ],
    "background:other_household_income": [
        "None",
        "Another member's job",
        "My other work",
        "Other",
    ],
    "background:education": [
        "Up to class 10",
        "Class 12",
        "Diploma",
        "Graduate or above",
    ],
    # English only for this round. The title is untouched; only the options narrow.
    "meta:language": ["English"],
    "consent:participate": [
        "Yes, I agree to take part",
        "No, I do not agree. End the survey.",
    ],
    "check:manipulation": [
        "No change",
        "Human appeals with no penalty for complaints",
        "Safety equipment, training, and accident cover",
        "A drivers' forum and union recognition",
    ],
}

NUMERIC = {
    "field:tenure_years": "In years",
    "field:hours_per_week": "In hours",
    "field:age": "In years",
    "background:dependants": "In people",
    "background:years_driving_before_uber": "In years",
}

OPTIONAL_TEXT = {"background:other_apps": "You may leave this blank."}


def section_entries(section: str):
    return [
        (title, target)
        for key, target in MAP.items()
        for sec, _, title in [key.partition("|")]
        if sec == section
    ]


def build_question(title: str, target: str) -> dict:
    if target in NUMERIC:
        return {
            "type": "number",
            "title": title,
            "help": NUMERIC[target],
            "required": True,
        }
    if target in OPTIONAL_TEXT:
        return {"type": "text", "title": title, "help": OPTIONAL_TEXT[target],
                "required": False}
    if target in CHOICES:
        return {
            "type": "choice",
            "title": title,
            "options": CHOICES[target],
            "required": True,
        }
    if target.startswith("screen:"):
        return {"type": "choice", "title": title, "options": ["Yes", "No"], "required": True}
    if target.startswith("consent:"):
        return {
            "type": "checkbox",
            "title": title,
            "options": ["I agree"],
            "required": True,
            "help": "Tick to show you agree.",
        }
    if target.startswith(("why:", "own_words:")):
        return {
            "type": "paragraph",
            "title": title,
            "required": False,
            "help": "Optional, but it helps us understand your answers.",
        }
    raise AssertionError(f"no question type for {target!r}")


def scale_help(scale_id: str) -> str:
    s = SCALES[scale_id]
    return f"1 = {s['anchors'][0]} · {s['points']} = {s['anchors'][-1]}"


def item_groups(section: str):
    """Consecutive runs of the same (block, scale), in instrument order.

    Grouping by block as well as scale keeps the survey's own sub-headings intact: Part 16's
    fairness, job, working-around, leaving and staying blocks stay separate rather than melting
    into one nine-row grid.
    """
    rows = [(t, v) for t, v in section_entries(section) if v in ITEMS]
    rows.sort(key=lambda r: (ITEMS[r[1]]["part"], ITEMS[r[1]].get("version_shown") or 0,
                             ITEMS[r[1]]["ordinal"]))
    groups = []
    for title, item_id in rows:
        key = (ITEMS[item_id]["block"], ITEMS[item_id]["scale_id"])
        if groups and groups[-1]["key"] == key:
            groups[-1]["rows"].append(title)
        else:
            groups.append({"key": key, "scale": ITEMS[item_id]["scale_id"], "rows": [title]})
    return groups


def build_section(section: str) -> dict:
    entries = section_entries(section)
    item_titles = {t for t, v in entries if v in ITEMS}
    questions = []

    # Scale items first, then the section's free-text and single questions, as the survey orders
    # them: the why-probe is always the last question of its part.
    for group in item_groups(section):
        scale = SCALES[group["scale"]]
        if len(group["rows"]) == 1:
            questions.append(
                {
                    "type": "scale",
                    "title": group["rows"][0],
                    "points": scale["points"],
                    "low": scale["anchors"][0],
                    "high": scale["anchors"][-1],
                    "required": True,
                }
            )
        else:
            questions.append(
                {
                    "type": "grid",
                    "title": "Please select the number that best matches your situation.",
                    "help": scale_help(group["scale"]),
                    "columns": [str(n) for n in range(1, scale["points"] + 1)],
                    "rows": group["rows"],
                    "required": True,
                }
            )

    for title, target in entries:
        if title in item_titles:
            continue
        questions.append(build_question(title, target))

    return {
        "header": section,
        "description": SECTION_INTRO.get(section, ""),
        "questions": questions,
    }


DEFINITION = [build_section(s) for s in SECTION_ORDER]

# Every mapped question must appear exactly once in the definition.
emitted = []
for sec in DEFINITION:
    for q in sec["questions"]:
        emitted += [(sec["header"], r) for r in q["rows"]] if q["type"] == "grid" \
            else [(sec["header"], q["title"])]
keys = {f"{h}|{t}" for h, t in emitted}
assert keys == set(MAP), sorted(keys ^ set(MAP))[:5]
assert len(emitted) == len(MAP) == 112

FORM_TITLE = "Research survey — Your work with Uber"
FORM_DESCRIPTION = (
    "This survey is part of academic research on algorithmic management of gig workers in "
    "India. It takes about 25 minutes. Your answers are anonymous: we do not ask for your "
    "name, your phone number or your email address.\n\n"
    "Please replace this text with the full participant information sheet before you send the "
    "form to anyone."
)
CONFIRMATION = (
    "Thank you. Your answers have been sent.\n\n"
    "Save the link on this page. It is the only way to find your response again if you want to "
    "withdraw it within 14 days."
)

GS = '''/**
 * Twin Lab — builds the driver survey Form.
 *
 * GENERATED by the repo, from config/form_map.yaml and data/reference/instrument.json.
 * Do not hand-edit a question title here: intake matches on "<section>|<title>", so a title
 * edited in one place and not the other is a 422.
 *
 * Run `buildForm` once. It creates a NEW form every time it runs and logs the two URLs.
 */

const FORM_TITLE = %(title)s;
const FORM_DESCRIPTION = %(description)s;
const CONFIRMATION = %(confirmation)s;

const DEFINITION = %(definition)s;

/** Build the whole survey. Logs the edit URL and the public URL. */
function buildForm() {
  const form = FormApp.create(FORM_TITLE)
    .setTitle(FORM_TITLE)
    .setDescription(FORM_DESCRIPTION)
    .setConfirmationMessage(CONFIRMATION)
    .setCollectEmail(false)          // twin_id is the response id; no identity is collected
    .setAllowResponseEdits(true)     // the driver's only route back for a 14-day withdrawal
    .setProgressBar(true)
    .setShuffleQuestions(false)      // row order inside a grid is fixed by the instrument
    .setLimitOneResponsePerUser(false);

  let count = 0;
  DEFINITION.forEach(function (section, index) {
    // The first section is the form's own first page; every later one needs a page break.
    if (index > 0) {
      const page = form.addPageBreakItem().setTitle(section.header);
      if (section.description) page.setHelpText(section.description);
    } else if (section.description) {
      form.addSectionHeaderItem()
        .setTitle(section.header)
        .setHelpText(section.description);
    }
    section.questions.forEach(function (q) {
      addQuestion(form, q);
      count += (q.type === 'grid') ? q.rows.length : 1;
    });
  });

  Logger.log('Built %%s questions in %%s sections.', count, DEFINITION.length);
  Logger.log('EDIT: %%s', form.getEditUrl());
  Logger.log('LIVE: %%s', form.getPublishedUrl());
  Logger.log('Form id: %%s', form.getId());
  return form;
}

function addQuestion(form, q) {
  switch (q.type) {
    case 'grid': {
      const item = form.addGridItem()
        .setTitle(q.title)
        .setRows(q.rows)
        .setColumns(q.columns)
        .setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      return item;
    }
    case 'scale': {
      const item = form.addScaleItem()
        .setTitle(q.title)
        .setBounds(1, q.points)
        .setLabels(q.low, q.high)
        .setRequired(q.required);
      return item;
    }
    case 'choice': {
      const item = form.addMultipleChoiceItem()
        .setTitle(q.title)
        .setChoiceValues(q.options)
        .setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      return item;
    }
    case 'checkbox': {
      const item = form.addCheckboxItem()
        .setTitle(q.title)
        .setChoiceValues(q.options)
        .setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      return item;
    }
    case 'number': {
      const item = form.addTextItem().setTitle(q.title).setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      item.setValidation(
        FormApp.createTextValidation()
          .setHelpText('Please enter a number.')
          .requireNumber()
          .build()
      );
      return item;
    }
    case 'text': {
      const item = form.addTextItem().setTitle(q.title).setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      return item;
    }
    case 'paragraph': {
      const item = form.addParagraphTextItem().setTitle(q.title).setRequired(q.required);
      if (q.help) item.setHelpText(q.help);
      return item;
    }
    default:
      throw new Error('unknown question type: ' + q.type);
  }
}

/**
 * Check a form against the definition without sending anything anywhere.
 * Prints every "<section>|<title>" key the form would produce, and flags any that the
 * definition does not contain. Run this after any manual edit in the Forms UI.
 */
function verifyForm() {
  const form = FormApp.getActiveForm();
  if (!form) throw new Error('Open this script from the Form (Extensions > Apps Script).');

  const expected = {};
  DEFINITION.forEach(function (section) {
    section.questions.forEach(function (q) {
      if (q.type === 'grid') {
        q.rows.forEach(function (r) { expected[section.header + '|' + r] = true; });
      } else {
        expected[section.header + '|' + q.title] = true;
      }
    });
  });

  const found = [];
  let current = DEFINITION[0].header;
  form.getItems().forEach(function (item) {
    const type = item.getType();
    if (type === FormApp.ItemType.PAGE_BREAK) {
      current = item.getTitle();
      return;
    }
    if (type === FormApp.ItemType.SECTION_HEADER) return;
    if (type === FormApp.ItemType.GRID) {
      item.asGridItem().getRows().forEach(function (r) { found.push(current + '|' + r); });
    } else {
      found.push(current + '|' + item.getTitle());
    }
  });

  const unexpected = found.filter(function (k) { return !expected[k]; });
  const seen = {};
  found.forEach(function (k) { seen[k] = true; });
  const missing = Object.keys(expected).filter(function (k) { return !seen[k]; });

  Logger.log('%%s questions on the form, %%s expected.', found.length,
             Object.keys(expected).length);
  if (unexpected.length) Logger.log('NOT IN THE MAP (%%s):\\n%%s', unexpected.length,
                                    unexpected.join('\\n'));
  if (missing.length) Logger.log('MISSING FROM THE FORM (%%s):\\n%%s', missing.length,
                                 missing.join('\\n'));
  if (!unexpected.length && !missing.length) Logger.log('OK — every key matches.');
  return { found: found.length, unexpected: unexpected, missing: missing };
}
''' % {
    "title": json.dumps(FORM_TITLE, ensure_ascii=False),
    "description": json.dumps(FORM_DESCRIPTION, ensure_ascii=False),
    "confirmation": json.dumps(CONFIRMATION, ensure_ascii=False),
    "definition": json.dumps(DEFINITION, ensure_ascii=False, indent=2),
}

out = ROOT / "apps_script" / "build_form.gs"
out.parent.mkdir(exist_ok=True)
out.write_text(GS, encoding="utf-8")
print("wrote", out, len(GS.splitlines()), "lines")
print("questions:", len(emitted), "sections:", len(DEFINITION))
