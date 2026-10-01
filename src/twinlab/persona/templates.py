"""Persona clause templates. FROZEN and versioned. docs/02 §5.

One template per battery item, plus the demographic and background lines. The passage carries
**words, not numbers** (I7): a `5` on a 7-point agreement item becomes "I somewhat agree that…",
never "I rated this 5 out of 7". A twin shown numbers does arithmetic instead of reasoning from
experience.

Attention checks (`AMQ6`, `ALGO5`) have no template: they are a human data-quality device with no
experiential content and are never put to a twin (I10). Holdout items (Parts 16 and 17) have no
template either — the persona must not contain holdout material (I6).

A missing template raises ``PersonaTemplateMissing``. There is no fallback: a silent skip would
make the passage lossy, and losslessness is the whole point.
"""

from __future__ import annotations

TEMPLATE_VERSION = "v1"


class PersonaTemplateMissing(KeyError):
    """An answered item has no clause template. Raised, never swallowed (CLAUDE.md rule 6)."""


#: Anchor vocabulary per scale. Index is the raw survey value.
ANCHOR_CLAUSES: dict[str, dict[int, str]] = {
    "agree7": {
        1: "I strongly disagree",
        2: "I disagree",
        3: "I somewhat disagree",
        4: "I neither agree nor disagree",
        5: "I somewhat agree",
        6: "I agree",
        7: "I strongly agree",
    },
    "agree5": {
        1: "I strongly disagree",
        2: "I disagree",
        3: "I neither agree nor disagree",
        4: "I agree",
        5: "I strongly agree",
    },
    "extent7": {
        1: "to a very small extent",
        2: "to a small extent",
        3: "to a somewhat small extent",
        4: "to a moderate extent",
        5: "to a somewhat large extent",
        6: "to a large extent",
        7: "to a very large extent",
    },
    "likely7": {
        1: "not at all likely",
        2: "slightly likely",
        3: "somewhat likely",
        4: "moderately likely",
        5: "quite likely",
        6: "very likely",
        7: "extremely likely",
    },
    "fair7": {
        1: "very unfair",
        2: "unfair",
        3: "somewhat unfair",
        4: "neither fair nor unfair",
        5: "somewhat fair",
        6: "fair",
        7: "very fair",
    },
}

#: One clause per battery item. ``{anchor}`` is filled from ANCHOR_CLAUSES for that item's scale.
TEMPLATES: dict[str, str] = {
    # --- Part 5, how work reaches me (agree7) ---
    "AMQ1": "{anchor} that an automated system tracks me carefully to make sure I finish my tasks.",
    "AMQ2": "{anchor} that my daily tasks are given to me by an automated system.",
    "AMQ3": "{anchor} that my work schedule is made by an automated system.",
    "AMQ4": "{anchor} that an electronic system handles the evaluation of how I work.",
    "AMQ5": "{anchor} that a large part of what I earn is decided by an automated system.",
    # --- Part 6, how the app guides me (agree5) ---
    "PAC1": "{anchor} that the app's algorithm gives out work intelligently.",
    "PAC2": "{anchor} that it tells me how the platform expects the work to be done.",
    "PAC3": "{anchor} that it gives me a good deal of information to help me finish a job.",
    "PAC4": "{anchor} that it gives me feedback on how I am performing as I go.",
    "PAC5": "{anchor} that it follows where I am at every moment.",
    "PAC6": "{anchor} that it keeps track of how far along my work is.",
    "PAC7": "{anchor} that it watches my attitude to the work as I go.",
    "PAC8": "{anchor} that it judges the quality of my service by itself.",
    "PAC9": "{anchor} that it ranks me against how I have performed.",
    "PAC10": "{anchor} that it offers me money to work hard over a set stretch of time.",
    "PAC11": "{anchor} that it fines me when I do not meet what the platform asks.",
    # --- Part 7, how fair the app is (extent7) ---
    "FAIR1": "The app matches me to work on accurate information {anchor}.",
    "FAIR2": "I have been able to say what I think and how I feel while being assessed {anchor}.",
    "FAIR3": "I am able to appeal against the rides the app gives me {anchor}.",
    "FAIR4": "The way the app matches me to work is free of bias {anchor}.",
    # --- Part 8, how clear the app is (agree5) ---
    "CLAR1": "{anchor} that I could explain well how the platform's algorithms reach a decision.",
    "CLAR2": "{anchor} that I can see through how those decisions get made.",
    "CLAR3": "{anchor} that the way those decisions get made is clear and open.",
    # --- Part 9, my job (agree7) ---
    "SAT1": "{anchor} that, all in all, I am satisfied with my job.",
    "SAT2": "{anchor} that, in general, I do not like my job.",
    "SAT3": "{anchor} that, in general, I like working here.",
    # --- Part 10, staying (agree5) ---
    "CONT1": "{anchor} that I hope this job carries on in the future.",
    "CONT2": "{anchor} that I hope my job carries on in the future.",
    # --- Part 11, working around the app (agree7) ---
    "ALGO1": "{anchor} that I do not enjoy working under the supervision of algorithms.",
    "ALGO2": "{anchor} that I find the platform's algorithms unfair.",
    "ALGO3": "{anchor} that I would rather be managed by people than by an algorithm.",
    "ALGO4": "{anchor} that I deliberately change how I work to be given better jobs.",
    # --- Part 12, leaving (agree7 / likely7) ---
    "TURN1": "{anchor} that I will probably look for a new job in the next year.",
    "TURN2": "{anchor} that I often think about quitting.",
    "TURN3": "Actively looking for a new job in the next year is {anchor} for me.",
    # --- Part 13, my income (agree7) ---
    "DEP1": "{anchor} that I could easily get another job outside platform work if I wanted one.",
    "DEP2": "{anchor} that I have to keep working through a platform to live the way I want to.",
}

#: Items that are answered but deliberately contribute no persona clause, with the reason.
EXCLUDED_FROM_PERSONA: dict[str, str] = {
    "AMQ6": "attention check — human data-quality device, never put to a twin (I10)",
    "ALGO5": "attention check — human data-quality device, never put to a twin (I10)",
}

#: Demographic and background lines, in passage order. ``None`` values are skipped, which is not a
#: loss: an unanswered optional question has nothing to carry.
IDENTITY_TEMPLATES: dict[str, str] = {
    "age": "I am {value} years old.",
    "gender": "I describe my gender as {value}.",
    "city": "I drive in {value}.",
    "service": "I drive {value} for Uber.",
}

WORK_CONTEXT_TEMPLATES: dict[str, str] = {
    "tenure_months": "I have been driving with Uber for {value} months.",
    "hours_per_week": "In a normal week I work about {value} hours through platform apps.",
    "platform_count": "I take work from {value} platform app or apps at the moment.",
    "other_apps": "The other apps I use for work are {value}.",
    "vehicle_arrangement": "The vehicle I drive I {value}.",
    "years_driving_before_uber": "Before Uber I drove for a living for {value} years.",
}

HOUSEHOLD_TEMPLATES: dict[str, str] = {
    "dependants": "There are {value} people who depend on what I earn.",
    "other_household_income": "Apart from platform work, my household's other income is {value}.",
    "education": "I finished my education at {value}.",
}

#: Part 14. Prompt text is the driver's, kept whole; the answer follows verbatim.
OWN_WORDS_PROMPTS: dict[str, str] = {
    "OWN1": "My least difficult day driving with Uber:",
    "OWN2": "How I think the app decides what a trip pays and who gets it:",
    "OWN3": "A time I needed help from Uber, or my account was blocked or penalised:",
    "OWN4": "What other drivers and I do when we have a problem with the platform:",
    "OWN5": "Who depends on my earnings, and where I see myself in a year or two:",
}

WHY_PROBE_PROMPTS: dict[str, str] = {
    "WHY_CONTROL": "What makes me feel the app controls, or does not control, how I work:",
    "WHY_SATISFACTION": "The main reason for how satisfied I am:",
    "WHY_OTHER_WORK": "Why finding other work is easy or hard for me:",
}

#: Section headings, in the fixed order of docs/02 §5.
SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("identity", "Who I am"),
    ("work_context", "My work"),
    ("household", "My household and what I depend on"),
    ("amq", "How the app manages me"),
    ("pac", "How the app guides me"),
    ("fair", "How fair the app is"),
    ("clar", "How clear the app is"),
    ("sat", "My job"),
    ("cont", "Staying"),
    ("algo", "Working around the app"),
    ("turn", "Leaving"),
    ("own_words", "In my own words"),
)

#: Which battery block feeds which section.
BLOCK_SECTION: dict[str, str] = {
    "AMQ": "amq",
    "PAC": "pac",
    "FAIR": "fair",
    "CLAR": "clar",
    "SAT": "sat",
    "CONT": "cont",
    "ALGO": "algo",
    "TURN": "turn",
    "DEP": "household",
}


def anchor_for(scale_id: str, value: int) -> str:
    """The word form of a Likert value. Raises rather than guessing an out-of-range value."""
    try:
        return ANCHOR_CLAUSES[scale_id][value]
    except KeyError as exc:  # pragma: no cover - defensive
        raise PersonaTemplateMissing(
            f"no anchor for scale {scale_id!r} value {value!r}"
        ) from exc


def template_for(item_id: str) -> str:
    """The clause template for an item. Raises if there is none (CLAUDE.md rule 6)."""
    try:
        return TEMPLATES[item_id]
    except KeyError as exc:
        raise PersonaTemplateMissing(
            f"no persona template for item {item_id!r}; add one to templates.py rather than "
            "letting the answer be dropped"
        ) from exc
