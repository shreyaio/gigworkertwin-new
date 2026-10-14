"""The hosted questionnaire, assembled and checked against the two frozen sources. `docs/06` §2.1.

**Almost none of this file is content.** Of the 112 questions a driver answers, 73 are scored
items and every one of them — its section, its stem, its scale, its number of points and its end
anchors — is *derived* from `data/reference/instrument.json` by :func:`_item_question`. Retyping a
stem here would create a second copy of frozen text that could drift from the register silently,
and the register is what `survey_answers.item_id` is foreign-keyed to.

The 39 questions that are declared literally below are the ones the register does not hold: the
eight Part 1 screeners, the eight Part 2 consents, Part 3 and Part 4's demographics and
background, the three why-probes, Part 14's five own-words questions and Part 15's manipulation
check. They have no `item_id` because the 73-item register is frozen (`CLAUDE.md` rule 8), which
is exactly why `twins.background` exists to carry them.

**The bijection is the safety property.** :func:`hosted_instrument` refuses to return an
instrument whose question keys are not *exactly* the keys of `config/form_map.yaml`. A question
the page draws but the map does not know would raise `UnmappedQuestion` at intake — the driver's
answer accepted on screen and rejected on the way to the table. A map key the page never draws is
a question silently dropped from the instrument. Both are `CLAUDE.md` rule 7 failures, and both
fail here, at import, rather than on the first real submission.

Part 17's six versions are written out as prose because they are **the human-facing stimulus as
administered**, not a render of a version code. The twin-facing paragraphs are produced by
`variant/render.py` from the criteria corpus and are a different artifact for a different reader;
the mapping from these six to their version codes lives in the instrument appendix and is holdout
material (I6), so no code appears anywhere on this page.
"""

from __future__ import annotations

from functools import lru_cache

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.ingest.survey_intake import form_map, form_map_version
from twinlab.models.survey import Block, HostedInstrument, Question, Stop


class InstrumentMismatch(RuntimeError):
    """The hosted questionnaire and `config/form_map.yaml` do not describe the same instrument.

    Raised at build time, never worked around. See the module docstring: a mismatch is a dropped
    answer or a rejected submission, and both are silent until someone audits a construct.
    """


# --------------------------------------------------------------------------- sections

#: `form_map.yaml` section strings for the parts whose questions are not scored items. Derived the
#: same way :func:`_item_question` derives them, so the two cannot disagree.
P1 = "PART 1 — A FEW QUICK CHECKS"
P2 = "PART 2 — YOUR AGREEMENT"
P3 = "PART 3 — ABOUT YOU AND YOUR WORK"
P4 = "PART 4 — YOUR BACKGROUND"
P6 = "PART 6 — HOW THE APP GUIDES YOU"
P9 = "PART 9 — YOUR JOB"
P13 = "PART 13 — YOUR INCOME"
P14 = "PART 14 — YOUR WORK IN YOUR OWN WORDS"
P15 = "PART 15 — IMAGINE A CHANGE"


def _section_for(part: int, part_name: str) -> str:
    """`"PART 5 — THE APP AND YOUR WORK"`. The em dash is the Form's, and it is load-bearing."""
    return f"PART {part} — {part_name}"


# --------------------------------------------------------------------------- scored items


def _item_question(item_id: str, ref: ReferenceData) -> Question:
    """One scored item, read whole from the frozen register.

    Nothing about the item is written down here — not the stem, not the scale, not the range. A
    5-point construct therefore cannot be drawn with seven boxes, which is the defect
    `models/twin.py` records from the prototype ("the prototype's prompt said 1 to 7 for every
    item and three of its nine constructs were 5-point").
    """
    item = ref.items[item_id]
    scale = ref.scales[item.scale_id]
    section = _section_for(item.part, item.part_name)
    if item_id.startswith("H3_"):
        # Part 17 asks the same three questions under six headed stimuli, so the section carries
        # the version — that is how `form_map.yaml` tells the eighteen answers apart.
        version = int(item_id.split("_")[1][1:])
        section = f"{section} — Version {version} of 6"
    return Question(
        section=section,
        title=item.stem,
        kind="likert",
        target=item_id,
        scale_id=item.scale_id,
        points=scale.points,
        low_anchor=scale.anchors[0],
        high_anchor=scale.anchors[-1],
    )


#: The why-probe, verbatim from `SURVEY_SCALES_AND_WHY_PROBES.md` §3.1. **Constant across every
#: item it is attached to**, and deliberately so: a per-item wording would cue content, and a
#: wording like "why are you unhappy with this?" would bias the persona toward grievance and
#: propagate into every counterfactual the twin answers. Neutral on valence is the requirement.
WHY_PROBE_TITLE = "Why did you choose that?"
WHY_PROBE_HELP = (
    "Did something happen that made you pick this number? A trip, a week, something the app did, "
    "something someone said. A sentence or two is enough. You can leave this blank."
)


def _why_question(item_id: str, ref: ReferenceData, mapping: dict[str, str]) -> Question | None:
    """The optional probe paired with one battery item, or ``None`` if it has none.

    Three items — PAC11, SAT1, DEP1 — carry the instrument's own part-level open questions
    instead, and `survey_answers.why_text` is one column per item, so they get no second probe
    (`docs/DECISIONS.md`, 2026-10-08). Their questions are declared with their blocks.

    The *map key* carries the item's stem, because one section holds several items and the probe
    wording is identical across them — five AMQ probes titled "Why did you choose that?" would
    collide into one key and four answers would be lost. The *driver* is shown the constant
    wording alone, via ``prompt``.
    """
    item = ref.items[item_id]
    section = _section_for(item.part, item.part_name)
    title = f"{WHY_PROBE_TITLE} — {item.stem}"
    target = mapping.get(f"{section}|{title}")
    if target is None:
        return None
    return Question(
        section=section,
        title=title,
        prompt=WHY_PROBE_TITLE,
        kind="long_text",
        target=target,
        why_for_item=item_id,
        help_text=WHY_PROBE_HELP,
    )


def _items(ref: ReferenceData, *item_ids: str) -> tuple[Question, ...]:
    """Each item, followed immediately by its own why-probe where it has one.

    Interleaved rather than grouped: the reference screens put the probe box directly under the
    rating it explains, and a driver asked to justify a rating three screens later is answering a
    different question.
    """
    mapping = form_map()
    out: list[Question] = []
    for item_id in item_ids:
        out.append(_item_question(item_id, ref))
        if not ref.items[item_id].attention_check:
            # §3.2 — an attention check is a data-quality device with no experiential content.
            # Asking a driver to justify "please select 2" would be noise in the persona.
            probe = _why_question(item_id, ref, mapping)
            if probe is not None:
                out.append(probe)
    return tuple(out)


def _block_items(ref: ReferenceData, block: str) -> tuple[Question, ...]:
    """One register block, in the register's own ordinal order, each item with its probe."""
    ids = sorted(
        (i for i, item in ref.items.items() if item.block == block),
        key=lambda i: ref.items[i].ordinal,
    )
    return _items(ref, *ids)


def _scale_note(questions: tuple[Question, ...]) -> str:
    """"1 = Strongly disagree · 7 = Strongly agree", when every item in the block shares a scale.

    Returns empty when they do not. Part 12 mixes `agree7` and `likely7`, and a single heading
    claiming one scale over an item measured on the other would mislabel the item — so the note is
    dropped and each item shows its own anchors instead.
    """
    scales = {q.scale_id for q in questions if q.kind == "likert"}
    if len(scales) != 1:
        return ""
    first = next(q for q in questions if q.kind == "likert")
    return f"1 = {first.low_anchor} · {first.points} = {first.high_anchor}"


# --------------------------------------------------------------------------- Part 1, screeners

_SCREENERS: tuple[str, ...] = (
    "Are you aged 18 years or above?",
    "Have you driven with Uber, by cab, auto rickshaw, or motorcycle, for at least three "
    "continuous months up to today?",
    "Has the Uber Driver app, on your own device, given you trip requests in the last 30 days?",
    "Can you read English, Hindi, or Marathi well enough to complete this questionnaire on your "
    "own?",
    "Are you in India at present?",
    "Are you a salaried employee on Uber's own payroll (for example ground or engineering "
    "staff)?",
    "Have you taken part in an earlier stage of this research?",
    "Is your Uber account deactivated or suspended at present for a reason other than a voluntary "
    "pause?",
)

# --------------------------------------------------------------------------- Part 2, consent

_CONSENTS: tuple[str, ...] = (
    "I have read and understood the information about this research on this sheet.",
    "I understand my participation is voluntary and I can withdraw at any time during the survey "
    "without giving a reason.",
    "I understand I can withdraw my responses within 14 days of completing the survey by writing "
    "to the principal investigator.",
    "I understand my responses will be anonymised and used only for academic research on "
    "algorithmic management of gig workers.",
    "I understand my data will be retained in encrypted form for five years and then destroyed.",
    "I confirm I am aged 18 years or above and meet the eligibility criteria set out in "
    "Section II.",
    "I agree that my survey answers, including my answers in my own words, may be used to build "
    "an anonymised computer model that answers research questions in the way I might. I "
    "understand that the model will be used only for this research and that I can ask for it to "
    "be deleted within 14 days of completing the survey.",
)

# --------------------------------------------------------------------------- Part 17, stimuli

_NO_CHANGE = "No change from today."
_PAY = (
    "From next month Uber guarantees that, after fuel and other work costs, you earn at least the "
    "local minimum wage for every active hour, including waiting time, and it pays on time and in "
    "full."
)
_COND_1 = (
    "Uber now provides safety equipment and training free of charge, supports you when you work "
    "alone, and covers significant costs from work related accidents or illness."
)
_COND_2_V1 = (
    _COND_1 + " Uber also takes steps towards your social protection process, your standing if "
    "you cannot work for a long period, and no longer pays more for taking risks."
)
_COND_2 = (
    _COND_1 + " Uber also takes steps towards your social protection, protects your standing if "
    "you cannot work for a long period, and no longer pays more for taking risks."
)
_CONTRACTS = (
    "Your terms are now written in full in clear language, always available in the app, name the "
    "company you contract with, and include a data protection policy. Uber now warns you before "
    "terms change, removes unfair liability clauses, and explains in clear language the data and "
    "calculations it uses for pricing, bonuses, ratings, and job allocation."
)
_MGMT_1 = (
    "You can now reach a human representative and appeal low ratings, payment issues, and "
    "deactivations, even after deactivation, with no penalty for raising concerns."
)
_MGMT_2 = (
    _MGMT_1 + " Uber now enforces an anti-discrimination policy, removes barriers for independent "
    "groups, and checks that its allocation and pay algorithms treat every driver equally."
)
_REP_1 = (
    "Uber now runs a documented forum where all workers can raise shared concerns, and it states "
    "in writing that it will recognise and bargain with an independent workers' body."
)
_REP_2 = (
    _REP_1 + " Uber now formally recognises an independent workers' union or elected council, and "
    "it states in writing that it will recognise and bargain with an independent workers' body."
)

#: The six stimuli, verbatim from the instrument. Their version codes are holdout material and
#: appear nowhere on this page or in this file (I6).
_VERSIONS: tuple[tuple[str, str, str, str, str], ...] = (
    (_PAY, _COND_2_V1, _CONTRACTS, _MGMT_2, _NO_CHANGE),
    (_NO_CHANGE, _NO_CHANGE, _CONTRACTS, _MGMT_2, _REP_2),
    (_PAY, _COND_1, _NO_CHANGE, _MGMT_1, _NO_CHANGE),
    (_PAY, _COND_1, _CONTRACTS, _MGMT_1, _REP_1),
    (_NO_CHANGE, _COND_2, _CONTRACTS, _MGMT_1, _REP_1),
    (_NO_CHANGE, _COND_2, _CONTRACTS, _NO_CHANGE, _NO_CHANGE),
)

_LEVER_NAMES = ("Pay", "Conditions", "Contracts", "Management", "Representation")

#: The Part 15/16 stimulus, **one per arm**. `docs/01` §5: the human survey is a four-arm
#: between-subjects design, each respondent sees their own arm's story and re-answers 16 items
#: under it.
#:
#: Only `REP1` existed in the instrument. The printed questionnaire carries one story because it
#: is one printed copy, and `docs/GOOGLE_FORM.md` §4 says to paste that one — so no
#: real-respondent intake path ever had a second story to show, and none ever recorded an arm.
#: H2 validation consequently skipped every real twin, because it must show a twin *its own
#: driver's arm* (`docs/08` §3.1).
#:
#: The other three are **composed from the instrument's own frozen text, not authored**. Part 17
#: already states each lever's dial-1 commitments in driver-facing prose, and `docs/01` §5.1 maps
#: each arm to exactly those commitments — `CON1` to `2.1.a–c`, `MGT1` to `4.1.a/b/d`, `REP1` to
#: `5.1.a–c`. So each story below is its arm's lever paragraph from Part 17, behind the frozen
#: "Imagine that this is true:" stem. `BASE` is the no-change control and names the five levers
#: so that "nothing changed" is as concrete as the three that did.
#:
#: Approved by the researcher 2026-10-08 (`docs/DECISIONS.md`). **Treat as frozen instrument
#: text**: re-wording one changes what a driver read, and `arm` is stored against their answers.
ARM_STORIES: dict[str, str] = {
    "BASE": (
        "Imagine that this is true: nothing about how Uber works changes. Your pay, your "
        "conditions, your contract, how you are managed, and how your voice is heard all stay "
        "exactly as they are today."
    ),
    # Written out rather than computed from `_COND_1` / `_MGMT_1`. Splicing the lever paragraph in
    # after the stem needs its first letter lowered, and doing that mechanically produced
    # "…this is true: uber now provides safety equipment" — a lowercased proper noun in text a
    # driver reads. These are instrument text; they are spelled, not derived. The test in
    # `tests/test_m22_hosted_survey.py` pins each one to its Part 17 lever paragraph.
    "CON1": (
        "Imagine that this is true: Uber now provides safety equipment and training free of "
        "charge, supports you when you work alone, and covers significant costs from work related "
        "accidents or illness."
    ),
    "MGT1": (
        "Imagine that this is true: you can now reach a human representative and appeal low "
        "ratings, payment issues, and deactivations, even after deactivation, with no penalty for "
        "raising concerns."
    ),
    # Verbatim from the instrument, unchanged. Note it says "serious concerns" where Part 17's
    # lever paragraph says "shared concerns"; the Part 15/16 wording is the one drivers were
    # shown, so it is the one kept.
    "REP1": (
        "Imagine that this is true: Uber now runs a documented forum where all workers can raise "
        "serious concerns, and it states in writing that it will recognise and bargain with an "
        "independent workers' body."
    ),
}

#: Shown while no arm has been assigned yet — it cannot be, until the driver has answered the
#: city and service that stratify the draw. Never shown on a stop that carries the stimulus.
NO_ARM_YET = "…"


def arm_story(arm: str | None) -> str:
    """One arm's Part 15/16 stimulus. Raises on an unknown arm rather than showing the wrong one.

    Showing a driver a story their recorded arm does not match would make every H2 comparison
    built on that row wrong, and nothing downstream could detect it — the same failure
    `docs/08` §3.1 calls "a bug, not a variation" on the twin side.
    """
    if arm is None:
        return NO_ARM_YET
    try:
        return ARM_STORIES[arm]
    except KeyError:
        raise InstrumentMismatch(
            f"no Part 15/16 story for arm {arm!r}; arms are {sorted(ARM_STORIES)}. A respondent "
            "must never be shown a story that does not match the arm stored against their answers."
        ) from None


# --------------------------------------------------------------------------- the nine stops


def _stops(ref: ReferenceData) -> tuple[Stop, ...]:
    """The questionnaire, in answering order. `docs/06` §2.1 and `docs/DECISIONS.md` 2026-10-08.

    **Nine stops, and the partition is a presentation choice, not a research one.** No item moves
    relative to another and no part is split across two screens; the only thing decided here is
    where the page breaks fall. The reference screens fix stops 1, 2, 3 and 5 exactly — *Start*,
    *Check*, *Consent*, and Part 5's AMQ block under the heading "Part 4" — from which the "Part"
    label is one less than the stop index, and the instrument's Parts 3 and 4 share stop 4. The
    remaining grouping follows from that.

    Parts 15, 16 and 17 are deliberately one contiguous stop. They are the holdout (I6) and the
    manipulation check, so keeping them together means the material a twin must never see is one
    block of the instrument rather than something interleaved with persona material.
    """
    yes_no = lambda section, title: Question(  # noqa: E731 — one shape, used eight times
        section=section, title=title, kind="yes_no",
        target=form_map()[f"{section}|{title}"], required=True,
    )

    return (
        Stop(
            index=1,
            kicker="Start",
            title="Your work with Uber",
            intro=(
                "This survey asks how the Uber app manages your work and how changes to Uber's "
                "rules would affect you. It takes about 36 minutes."
            ),
            callout_title="Before you start",
            callout_points=(
                "There are no right or wrong answers.",
                "You can skip any question or stop at any time.",
                "Your answers are anonymous. This research is not run by Uber.",
            ),
            body=(
                "About this research",
                "This research studies how people who drive with Uber in India experience "
                "algorithmic management, the software mediated decisions on trip matching, trip "
                "allocation, pay, and control that the Uber app makes in place of human "
                "supervisors.",
                "Your participation contributes to this research. Participation is voluntary. You "
                "may skip any question or withdraw at any time without giving a reason. Your "
                "responses will be anonymised, aggregated with those of other participants, and "
                "reported only in composite form. No individual worker will be identifiable in "
                "any output from this research.",
                "Your responses will be anonymised at the point of data entry. No identifier "
                "(name, phone number, platform username, vehicle number, or account number) will "
                "be linked to your responses in any research output. Data will be retained in "
                "encrypted form for five years from the date of collection.",
                "You may withdraw at any time during the survey by closing the browser. After "
                "completing the survey, you may withdraw your responses within 14 days by writing "
                "to the principal investigator, quoting the reference number issued at the end.",
            ),
        ),
        Stop(
            index=2,
            kicker="Check",
            part="Part 1",
            title="A few quick checks",
            intro="Please answer each question.",
            blocks=(Block(
                section=P1,
                questions=tuple(yes_no(P1, t) for t in _SCREENERS),
            ),),
        ),
        Stop(
            index=3,
            kicker="Consent",
            part="Part 2",
            title="Your agreement",
            intro=(
                "Please read each statement and tick each box to show you agree. You must agree "
                "to all of them to take part."
            ),
            blocks=(Block(
                section=P2,
                questions=(
                    *(
                        Question(
                            section=P2, title=t, kind="consent",
                            target=form_map()[f"{P2}|{t}"], required=True,
                        )
                        for t in _CONSENTS
                    ),
                    Question(
                        section=P2,
                        title="Do you agree to take part?",
                        kind="choice",
                        target="consent:participate",
                        options=(
                            "Yes, I agree to take part",
                            "No, I do not agree. End the survey.",
                        ),
                        required=True,
                    ),
                ),
            ),),
        ),
        Stop(
            index=4,
            kicker="About you",
            part="Part 3",
            title="About you and your work",
            blocks=(
                Block(section=P3, questions=(
                    Question(
                        section=P3, title="Which Uber service do you drive for most?",
                        kind="choice", target="field:service",
                        options=("Cab (Uber Go or Premier)", "Auto rickshaw", "Motorcycle"),
                    ),
                    Question(
                        section=P3, title="In which city do you usually drive?",
                        kind="choice", target="field:city",
                        options=("Mumbai", "Pune", "Delhi NCR", "Jaipur", "Bengaluru"),
                    ),
                    Question(
                        section=P3, title="For how many years have you driven with Uber?",
                        kind="decimal", target="field:tenure_years", unit="In years",
                    ),
                    Question(
                        section=P3,
                        title=(
                            "In a typical week, how many hours do you work through platform apps?"
                        ),
                        kind="integer", target="field:hours_per_week", unit="In hours",
                    ),
                    Question(
                        section=P3,
                        title="From how many platform apps do you receive tasks at present?",
                        kind="choice", target="background:platform_count",
                        options=("1", "2", "3 or more"),
                    ),
                    Question(
                        section=P3,
                        title=(
                            "Which other ride or delivery apps, if any, do you also use for work?"
                        ),
                        kind="short_text", target="background:other_apps",
                    ),
                    Question(
                        section=P3, title="What is your age in completed years?",
                        kind="integer", target="field:age", unit="In years",
                    ),
                    Question(
                        section=P3, title="How do you describe your gender?",
                        kind="choice", target="field:gender",
                        options=("Woman", "Man", "Another identity", "Prefer not to say"),
                    ),
                    Question(
                        section=P3, title="In which language are you completing this survey?",
                        kind="choice", target="meta:language",
                        options=("English", "Hindi", "Marathi"),
                    ),
                )),
                Block(section=P4, heading="Your background", questions=(
                    Question(
                        section=P4, title="How do you have the vehicle you drive?",
                        kind="choice", target="background:vehicle_arrangement",
                        options=(
                            "Own outright", "Own with a loan",
                            "Rent from an Uber fleet partner", "Rent from someone else",
                        ),
                    ),
                    Question(
                        section=P4, title="How many people depend on your earnings?",
                        kind="integer", target="background:dependants", unit="In people",
                    ),
                    Question(
                        section=P4,
                        title=(
                            "Apart from platform work, what other income does your household "
                            "have?"
                        ),
                        kind="choice", target="background:other_household_income",
                        options=("None", "Another member's job", "My other work", "Other"),
                    ),
                    Question(
                        section=P4,
                        title="What is the highest level of education you have completed?",
                        kind="choice", target="background:education",
                        options=("Up to class 10", "Class 12", "Diploma", "Graduate or above"),
                    ),
                    Question(
                        section=P4,
                        title=(
                            "How many years did you drive for a living before joining Uber?"
                        ),
                        kind="decimal", target="background:years_driving_before_uber",
                        unit="In years",
                    ),
                )),
            ),
        ),
        Stop(
            index=5,
            kicker="Ratings",
            part="Part 4",
            title="The app and your work",
            intro=(
                "The statements below describe how work reaches you on Uber. Please select the "
                "number that best matches your experience."
            ),
            blocks=(_likert_block(ref, "AMQ"),),
        ),
        Stop(
            index=6,
            kicker="The algorithm",
            part="Part 5",
            title="How the app guides you",
            intro=(
                "The next statements are about the Uber app's algorithm. Please select the number "
                "that best matches your experience."
            ),
            blocks=(
                Block(
                    section=P6,
                    heading="How the app guides you",
                    scale_note=_scale_note(_block_items(ref, "PAC")),
                    questions=(
                        *_block_items(ref, "PAC"),
                        Question(
                            section=P6,
                            title=(
                                "What makes you feel the app controls, or does not control, how "
                                "you work?"
                            ),
                            kind="long_text", target="why:WHY_CONTROL",
                            why_for_item="PAC11",
                            help_text="Optional, but it helps us understand your answers.",
                        ),
                    ),
                ),
                _likert_block(
                    ref, "FAIR", heading="How fair the app is",
                    intro=(
                        "Please answer each question about how the app matches you to work and "
                        "evaluates you."
                    ),
                ),
                _likert_block(
                    ref, "CLAR", heading="How clear the app is",
                    intro="Please select the number that best matches your view.",
                ),
            ),
        ),
        Stop(
            index=7,
            kicker="Your job",
            part="Part 6",
            title="Your job, staying, and leaving",
            intro="Please think about your work with Uber as your job when you answer.",
            blocks=(
                Block(
                    section=P9,
                    heading="Your job",
                    scale_note=_scale_note(_block_items(ref, "SAT")),
                    questions=(
                        *_block_items(ref, "SAT"),
                        Question(
                            section=P9,
                            title="What is the main reason for your satisfaction rating?",
                            kind="long_text", target="why:WHY_SATISFACTION",
                            why_for_item="SAT1",
                            help_text="Optional, but it helps us understand your answers.",
                        ),
                    ),
                ),
                _likert_block(ref, "CONT", heading="Staying with Uber"),
                _likert_block(ref, "ALGO", heading="Working around the app"),
                _likert_block(ref, "TURN", heading="Leaving Uber"),
                Block(
                    section=P13,
                    heading="Your income",
                    intro="Please select the number that best matches your situation.",
                    scale_note=_scale_note(_block_items(ref, "DEP")),
                    questions=(
                        *_block_items(ref, "DEP"),
                        Question(
                            section=P13,
                            title="Why is finding other work easy or hard for you?",
                            kind="long_text", target="why:WHY_OTHER_WORK",
                            why_for_item="DEP1",
                            help_text="Optional, but it helps us understand your answers.",
                        ),
                    ),
                ),
            ),
        ),
        Stop(
            index=8,
            kicker="Your own words",
            part="Part 7",
            title="Your work in your own words",
            intro="Write a few sentences for each question. You may skip any question.",
            blocks=(Block(section=P14, questions=tuple(
                Question(section=P14, title=title, kind="long_text", target=f"own_words:OWN{n}")
                for n, title in enumerate((
                    "Describe your least difficult day driving with Uber. What happened, and what "
                    "did you do?",
                    "In your own words, how does the Uber app decide what a trip pays and which "
                    "driver gets it?",
                    "Tell us about a time you needed help from Uber, or your account was blocked "
                    "or penalised. How was it handled?",
                    "What do you and other drivers do when you have a problem with the platform?",
                    "Who depends on your earnings, and where do you see yourself in a year or "
                    "two?",
                ), start=1)
            )),),
        ),
        _holdout_stop(ref),
    )


def _likert_block(
    ref: ReferenceData, block: str, *, heading: str = "", intro: str = ""
) -> Block:
    questions = _block_items(ref, block)
    return Block(
        section=questions[0].section,
        heading=heading,
        intro=intro,
        scale_note=_scale_note(questions),
        questions=questions,
    )


def _holdout_stop(ref: ReferenceData) -> Stop:
    """Parts 15, 16 and 17 — the manipulation check and both holdouts, on one screen (I6).

    Part 16's sixteen items are one `form_map.yaml` section but five sub-blocks with three
    different scales, so they are grouped by register block and each sub-block states its own
    anchors. Part 17's eighteen are three questions under six headed stimuli, and the stimulus
    text is :data:`_VERSIONS`, verbatim.
    """
    h2_section = _section_for(16, ref.items["H2_FAIR1"].part_name)
    h2_groups = (
        ("FAIRNESS", ("H2_FAIR1", "H2_FAIR2", "H2_FAIR3", "H2_FAIR4")),
        ("YOUR JOB", ("H2_SAT1", "H2_SAT2", "H2_SAT3")),
        ("WORKING AROUND THE APP", ("H2_ALGO1", "H2_ALGO2", "H2_ALGO3", "H2_ALGO4")),
        ("LEAVING UBER", ("H2_TURN1", "H2_TURN2", "H2_TURN3")),
        ("STAYING WITH UBER", ("H2_CONT1", "H2_CONT2")),
    )

    blocks: list[Block] = [
        Block(
            section=P15,
            heading="Imagine a change",
            intro=(
                "Please read the short story below carefully and imagine it is true for your work "
                "with Uber."
            ),
            # The story itself depends on the arm this driver was assigned, which is not known
            # when the page is built — only once they have answered the city and service that
            # stratify the draw. The renderer fills it per session.
            arm_story=True,
            questions=(Question(
                section=P15,
                title="Which change did the story describe? Please tick one.",
                kind="choice",
                target="check:manipulation",
                options=(
                    "No change",
                    "Human appeals with no penalty for complaints",
                    "Safety equipment, training, and accident cover",
                    "A drivers' forum and union recognition",
                ),
            ),),
        ),
    ]
    # Part 16 restates the story before re-asking the sixteen items, as the instrument and
    # `docs/GOOGLE_FORM.md` §4 both do: the driver has just answered a manipulation check and
    # must hold the same world in mind for the block that follows.
    blocks.append(Block(section=h2_section, arm_story=True))

    for n, (heading, ids) in enumerate(h2_groups):
        questions = _items(ref, *ids)
        blocks.append(Block(
            section=h2_section,
            heading=heading,
            intro=(
                "Please answer every statement again, as if the story were true." if n == 0 else ""
            ),
            scale_note=_scale_note(questions),
            questions=questions,
        ))

    h3_section_base = _section_for(17, ref.items["H3_V1_FAIR"].part_name)
    for version, levers in enumerate(_VERSIONS, start=1):
        questions = _items(
            ref, f"H3_V{version}_FAIR", f"H3_V{version}_PUSH", f"H3_V{version}_KEEP"
        )
        blocks.append(Block(
            section=f"{h3_section_base} — Version {version} of 6",
            heading=f"Version {version} of 6",
            intro="\n".join(
                f"**{name}:** {text}" for name, text in zip(_LEVER_NAMES, levers, strict=True)
            ),
            questions=questions,
        ))

    return Stop(
        index=9,
        kicker="Imagine a change",
        part="Part 8",
        title="Imagining things were different",
        intro=(
            "One short story, then the same questions again, then six versions of Uber. There are "
            "no right answers here either."
        ),
        blocks=tuple(blocks),
    )


# --------------------------------------------------------------------------- the whole thing


@lru_cache(maxsize=1)
def hosted_instrument() -> HostedInstrument:
    """The questionnaire, built once and checked against `config/form_map.yaml`.

    Raises :class:`InstrumentMismatch` unless the questions drawn and the map's keys are the
    **same set**. See the module docstring for why both directions matter.
    """
    ref = reference()
    instrument = HostedInstrument(
        instrument_version=ref.instrument_version,
        form_map_version=form_map_version(),
        stops=_stops(ref),
    )
    mapping = form_map()
    drawn, mapped = instrument.keys, frozenset(mapping)

    if drawn != mapped:
        unmapped = sorted(drawn - mapped)
        undrawn = sorted(mapped - drawn)
        raise InstrumentMismatch(
            f"the hosted questionnaire draws {len(drawn)} questions and form_map.yaml "
            f"(version {instrument.form_map_version}) maps {len(mapped)}. "
            f"{len(unmapped)} drawn but unmapped — these would be rejected at intake as "
            f"UnmappedQuestion after the driver answered them: {unmapped[:5]}. "
            f"{len(undrawn)} mapped but never drawn — these are questions silently missing from "
            f"the instrument: {undrawn[:5]}. Neither is recoverable after fieldwork "
            "(CLAUDE.md rule 7)."
        )

    # The target a question claims has to be the target the map actually assigns it, or the page
    # is describing one destination and intake is writing to another.
    wrong = sorted(q.key for q in instrument.questions if mapping[q.key] != q.target)
    if wrong:
        raise InstrumentMismatch(
            f"{len(wrong)} question(s) claim a target form_map.yaml does not give them: "
            f"{wrong[:5]}"
        )
    return instrument


def question_for(key: str) -> Question:
    """One question by its `form_map.yaml` key. Raises rather than returning ``None``."""
    for question in hosted_instrument().questions:
        if question.key == key:
            return question
    raise KeyError(f"no hosted question with key {key!r}")


__all__ = ["InstrumentMismatch", "hosted_instrument", "question_for"]
