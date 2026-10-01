"""Generate config/form_map.yaml from the frozen instrument plus the survey document.

Run once; the YAML is the checked-in config. Re-wording a Form question is an edit there.
"""

import json
from pathlib import Path

items = json.load(open("data/reference/instrument.json", encoding="utf-8"))["items"]


def section(it):
    base = f"PART {it['part']} — {it['part_name']}"
    if it.get("version_shown"):
        return f"{base} — Version {it['version_shown']} of 6"
    return base


P1 = "PART 1 — A FEW QUICK CHECKS"
P2 = "PART 2 — YOUR AGREEMENT"
P3 = "PART 3 — ABOUT YOU AND YOUR WORK"
P4 = "PART 4 — YOUR BACKGROUND"
P14 = "PART 14 — YOUR WORK IN YOUR OWN WORDS"

manual = [
    (P1, "Are you aged 18 years or above?", "screen:age_18_plus"),
    (P1, "Have you driven with Uber, by cab, auto rickshaw, or motorcycle, for at least three continuous months up to today?", "screen:tenure_3_months"),
    (P1, "Has the Uber Driver app, on your own device, given you trip requests in the last 30 days?", "screen:active_30_days"),
    (P1, "Can you read English, Hindi, or Marathi well enough to complete this questionnaire on your own?", "screen:reads_survey_language"),
    (P1, "Are you in India at present?", "screen:in_india"),
    (P1, "Are you a salaried employee on Uber's own payroll (for example ground or engineering staff)?", "screen:uber_employee"),
    (P1, "Have you taken part in an earlier stage of this research?", "screen:earlier_stage"),
    (P1, "Is your Uber account deactivated or suspended at present for a reason other than a voluntary pause?", "screen:deactivated"),

    (P2, "I have read and understood the information about this research on this sheet.", "consent:statement_1"),
    (P2, "I understand my participation is voluntary and I can withdraw at any time during the survey without giving a reason.", "consent:statement_2"),
    (P2, "I understand I can withdraw my responses within 14 days of completing the survey by writing to the principal investigator.", "consent:statement_3"),
    (P2, "I understand my responses will be anonymised and used only for academic research on algorithmic management of gig workers.", "consent:statement_4"),
    (P2, "I understand my data will be retained in encrypted form for five years and then destroyed.", "consent:statement_5"),
    (P2, "I confirm I am aged 18 years or above and meet the eligibility criteria set out in Section II.", "consent:statement_6"),
    (P2, "I agree that my survey answers, including my answers in my own words, may be used to build an anonymised computer model that answers research questions in the way I might. I understand that the model will be used only for this research and that I can ask for it to be deleted within 14 days of completing the survey.", "consent:twin"),
    (P2, "Do you agree to take part?", "consent:participate"),

    (P3, "Which Uber service do you drive for most?", "field:service"),
    (P3, "In which city do you usually drive?", "field:city"),
    (P3, "For how many years have you driven with Uber?", "field:tenure_years"),
    (P3, "In a typical week, how many hours do you work through platform apps?", "field:hours_per_week"),
    (P3, "From how many platform apps do you receive tasks at present?", "background:platform_count"),
    (P3, "Which other ride or delivery apps, if any, do you also use for work?", "background:other_apps"),
    (P3, "What is your age in completed years?", "field:age"),
    (P3, "How do you describe your gender?", "field:gender"),
    (P3, "In which language are you completing this survey?", "meta:language"),

    (P4, "How do you have the vehicle you drive?", "background:vehicle_arrangement"),
    (P4, "How many people depend on your earnings?", "background:dependants"),
    (P4, "Apart from platform work, what other income does your household have?", "background:other_household_income"),
    (P4, "What is the highest level of education you have completed?", "background:education"),
    (P4, "How many years did you drive for a living before joining Uber?", "background:years_driving_before_uber"),

    ("PART 6 — HOW THE APP GUIDES YOU", "What makes you feel the app controls, or does not control, how you work?", "why:WHY_CONTROL"),
    ("PART 9 — YOUR JOB", "What is the main reason for your satisfaction rating?", "why:WHY_SATISFACTION"),
    ("PART 13 — YOUR INCOME", "Why is finding other work easy or hard for you?", "why:WHY_OTHER_WORK"),

    (P14, "Describe your least difficult day driving with Uber. What happened, and what did you do?", "own_words:OWN1"),
    (P14, "In your own words, how does the Uber app decide what a trip pays and which driver gets it?", "own_words:OWN2"),
    (P14, "Tell us about a time you needed help from Uber, or your account was blocked or penalised. How was it handled?", "own_words:OWN3"),
    (P14, "What do you and other drivers do when you have a problem with the platform?", "own_words:OWN4"),
    (P14, "Who depends on your earnings, and where do you see yourself in a year or two?", "own_words:OWN5"),
]

HEADER = """# Google Form question -> what it becomes. docs/03 §6.
#
# Two columns: the key is the Form section and the question title joined by a pipe, the value is
# the item_id or the field it lands in. The section qualifies the title because titles repeat —
# H2_SAT1 asks SAT1's question again in Part 16, and Part 17 asks the same three questions six
# times. The Apps Script sends the section with every answer for exactly that reason.
#
# Value prefixes:
#   (none)        a survey_items.item_id, stored in survey_responses.value_num
#   field:        a twins column (tenure_years is converted to tenure_months at intake)
#   background:   twins.background — Part 3 extras and Part 4, which have no item_id (docs/01 §4.2)
#   why:          a why-probe, stored as why_text on its anchor item (WHY_PROBE_ANCHOR)
#   own_words:    Part 14, verbatim, onto twins.background.own_words
#   consent:      consent:twin is statement 7 — the one that decides whether a twin is built
#   meta:         the submission's own language
#   screen:       Part 1 eligibility. Recorded in the data/temp mirror, which is the immutable
#                 record of the submission; it is not a column and nothing is inferred from it.
#
# A question absent from this file raises at intake; nothing is dropped (CLAUDE.md rule 6).
# Re-wording a Form question is an edit here, not a code change.

version: v1
map:
"""


def key(section_name, title):
    return json.dumps(f"{section_name}|{title}", ensure_ascii=False)


lines = [HEADER.rstrip("\n")]
for sec, title, target in manual:
    lines.append(f"  {key(sec, title)}: {target}")
lines.append("")
lines.append("  # --- the 73-item register, from data/reference/instrument.json (frozen) ---")
for it in sorted(items, key=lambda i: (i["part"], i.get("version_shown") or 0, i["ordinal"])):
    lines.append(f"  {key(section(it), it['stem'])}: {it['item_id']}")
lines.append("")

Path("config/form_map.yaml").write_text("\n".join(lines), encoding="utf-8")

import yaml

data = yaml.safe_load(Path("config/form_map.yaml").read_text(encoding="utf-8"))
mapped = {v for v in data["map"].values() if ":" not in v}
assert mapped == {i["item_id"] for i in items}, sorted(mapped ^ {i["item_id"] for i in items})
print("entries:", len(data["map"]), "| items:", len(mapped), "of", len(items))
