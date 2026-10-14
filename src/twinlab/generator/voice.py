"""Deterministic free-text for synthetic respondents. `docs/06` §4, generator `v6`.

**No LLM call, ever** — for the same reason as the rest of `generator/`: a model-written answer
is unreproducible, costs a call per respondent, and smuggles the model's own priors into the data
the twins are built from.

What this module exists to fix. Up to `v5` a synthetic respondent's 39 free-text answers came from
two tiny constant banks: the 37 why-probes from a flat four-string tuple with no reference to the
item or to the value just drawn, and Part 14 from a fixed five-tuple with **no RNG call at all** —
byte-identical for every respondent, in every batch, at every seed. Two consequences, and both
matter more than the repetition does:

* **Incoherence.** A respondent who had just strongly agreed that the app controls their work had
  a one-in-four chance of explaining it with "sometimes it feels fair and sometimes it does not".
  The text therefore did not predict the numbers, which is the opposite of what a persona is for.
* **No individuality.** "In my own words" is the longest unstructured block in the passage and its
  closing section — the most attributable text a reader has. Identical across the whole panel, it
  gave a wrong-person comparison nothing to discriminate on.

How it is fixed, without a model. Every answer is **composed** from the respondent's own drawn
state rather than sampled from a bank of finished sentences::

    [stance: block x band] + [circumstance: this respondent's own facts] + [consequence: band]

``band`` is this respondent's own answer to that item, read as a position on its own scale, so an
explanation cannot contradict the clause it is attached to. ``circumstance`` is filled from what
the generator already drew for them — city, service, tenure, dependants, the vehicle loan,
multi-apping, economic dependence — which is what makes two respondents distinguishable and what
makes the text carry construct signal rather than decoration. A :class:`Voice`, drawn once per
respondent, fixes verbosity, register and one or two recurring motifs across all 39 answers, so
the passage reads as one person rather than as thirty-nine independent samples.

**Everything here is digit-free.** I7 wants no bare numeral in a persona passage, and the persona
builder quotes a driver's words verbatim without editing them — so this module is the only guard.
Quantities are banded into words ("a houseful of people"), never spelled from a number, which also
keeps `generator/` from needing anything out of `persona/`.

**Determinism.** Every draw comes from the caller's `random.Random`, consumed in a fixed order; no
set is iterated and every bank is a tuple, or a dict read by an explicit key. Same seed in,
byte-identical text out.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

#: Bumped whenever a bank's **contents** change, not only its shape. Recorded on every batch
#: beside `GENERATOR_VERSION`, so a later reader can tell which prose produced a persona hash.
VOICE_VERSION = "v4"


class VoiceBankIncomplete(KeyError):
    """A (block, band) cell or an own-words cell has no text.

    Raised, never filled from a neighbouring band (`CLAUDE.md` rule 7). A silent fallback would put
    a mid-band explanation under a very-high rating, which is the `v5` defect this module exists to
    remove.
    """


#: Five bands, low to high, on whatever scale the item uses. Five rather than the scale's own
#: length so a 5-point and a 7-point item band the same way and one bank serves both.
BANDS: tuple[str, ...] = ("very_low", "low", "mid", "high", "very_high")

#: The `OWN3` cell for a respondent with no support or deactivation story. **Not a band** --
#: it is keyed beside them because the question is not answerable on a scale: either there is an
#: incident to narrate or there is not. See the cell itself for why this is not the top band.
NO_INCIDENT = "no_incident"

#: Upper bounds on the item's scale *position* in ``[0, 1]``. The mid band is the widest because
#: the midpoint of an agreement scale is a genuine answer rather than a rounding artefact.
_BAND_EDGES: tuple[tuple[float, str], ...] = (
    (0.125, "very_low"),
    (0.375, "low"),
    (0.625, "mid"),
    (0.875, "high"),
)


def band_of(value: int, points: int, *, reverse_coded: bool = False) -> str:
    """Which band a raw answer falls in, as a position on its own scale.

    ``reverse_coded`` mirrors the position before banding, so `SAT2` ("in general I do not like my
    job") answered **two** bands as *satisfied* rather than as dissatisfied. Reading the raw value
    here would attach a sour explanation to a contented respondent and destroy the SAT block's
    internal consistency — the same way drawing reverse items forward did before `v3`.
    """
    if points < 2:
        raise VoiceBankIncomplete(f"a {points}-point scale cannot be banded")
    position = (max(1, min(points, value)) - 1) / (points - 1)
    if reverse_coded:
        position = 1.0 - position
    for edge, name in _BAND_EDGES:
        if position < edge:
            return name
    return "very_high"


def band_of_target(target_1_to_7: float) -> str:
    """The band of a construct *target* on the dashboard's common 1-7 scale.

    Used by the Part 14 narratives, which speak about a construct as a whole rather than about one
    item, so there is no single raw answer to read.
    """
    position = (max(1.0, min(7.0, target_1_to_7)) - 1.0) / 6.0
    for edge, name in _BAND_EDGES:
        if position < edge:
            return name
    return "very_high"


#: The two cuts on `GeneratorSpec.reactivity_spread`'s draw, which is centred on 1.0. `v8`.
#:
#: Absolute rather than relative to the batch's own spread, deliberately: a respondent who would
#: barely be moved by an announcement should say so in the same words whatever the rest of the
#: batch looks like. With the default spread of `0.5` the draw is uniform on ``[0.5, 1.5]``, so
#: these put roughly a third of respondents in each band; at a spread of `0.0` every respondent is
#: `mid`, which is correct — there is then no variation to speak of.
_REACTIVITY_EDGES: tuple[tuple[float, str], ...] = ((0.85, "low"), (1.15, "mid"))


def reactivity_tag(reactivity: float) -> str:
    """``react:low|mid|high`` for one respondent's drawn reactivity. `v8`.

    The circumstance tag that lets a twin read **how far this person would move**, which until
    `v8` was a batch constant held nowhere in the persona. See the `react:*` entries in
    :data:`CIRCUMSTANCE` for why this is a disposition and not a leaked answer.
    """
    for edge, name in _REACTIVITY_EDGES:
        if reactivity < edge:
            return f"react:{name}"
    return "react:high"


#: ``lever id -> the circumstance family that speaks for it``. `v10`.
#:
#: Named for **the thing, not the lever**: a tag of `salience:pay` keys clauses about money, and
#: nothing anywhere renders the lever id itself. `docs/06` §4's own labels for the five, in the
#: odometer's frozen order (I2).
SALIENCE_BY_LEVER: dict[str, str] = {
    "L1": "salience:pay",
    "L2": "salience:conditions",
    "L3": "salience:contracts",
    "L4": "salience:appeals",
    "L5": "salience:forum",
}


def salience_tag(lever_weights: dict[str, float]) -> str | None:
    """``salience:*`` for **the lever this respondent weights highest**. `v10`.

    The circumstance tag that lets a twin read *which* described change would matter to this
    person, which until `v10` was a hidden batch constant: `lever_reactions` double-weighted pay
    for every respondent and no persona said so, so a twin could rank the six Part 17 versions
    correctly only by guessing the population's weighting. See the `salience:*` entries in
    :data:`CIRCUMSTANCE`.

    ``None`` when **no** lever is weighted above zero, which is `docs/06` §4's no-reaction null:
    a respondent nothing would move has no lever that matters most, and giving them one would be
    a claim the generator did not draw (`CLAUDE.md` rule 7 — raise or say nothing, never invent).

    Ties resolve in the odometer's frozen order, so the tag is a deterministic function of the
    weights rather than of dictionary order.
    """
    best: str | None = None
    best_weight = 0.0
    for lever, tag in SALIENCE_BY_LEVER.items():
        weight = lever_weights.get(lever)
        if weight is None:
            raise VoiceBankIncomplete(
                f"no drawn salience weight for lever {lever!r}; all five are required before a "
                "respondent can say which change matters most to them (docs/06 §4)"
            )
        if weight > best_weight:
            best, best_weight = tag, weight
    return best


# --------------------------------------------------------------------------- the stance bank

#: ``block -> band -> variants``. The opening clause of a why answer: what this respondent thinks
#: about the thing the item asked, at the strength they actually answered.
#:
#: Keyed on the **item block**, not the construct code — they are different namespaces
#: (`docs/01` §3.3), and the generator holds an `Item`, which carries `block`. Nine blocks, five
#: bands, three variants: enough that a block of eleven items does not repeat a sentence within one
#: respondent, without a bespoke line per item — which would make the bank unmaintainable and the
#: whys no more individual, since individuality comes from the band and the circumstance rather
#: than from the item.
#:
#: Lower case, no closing full stop: the persona builder quotes these inside single quotes as the
#: driver's own words, and an edited capital would read as exactly that, an edit.
STANCE: dict[str, dict[str, tuple[str, ...]]] = {
    # Part 5, automated management: how much of my work a system decides.
    "AMQ": {
        "very_low": (
            "no system is deciding this for me, I choose when I drive and what I take",
            "that part is in my own hands and the app has nothing to do with it",
            "I have never felt a machine standing over my shoulder in this",
        ),
        "low": (
            "the app suggests things but the deciding is mostly mine",
            "it is there in the background and not much more than that",
            "I would not say a system runs this part of my day",
        ),
        "mid": (
            "some of it is the app and some of it is me, depending on the day",
            "the app has a hand in it but not the whole hand",
            "it is half the app and half my own judgement",
        ),
        "high": (
            "the app does most of the deciding and I work around what it gives me",
            "a system handles this and I mostly follow what it puts in front of me",
            "the deciding sits with the app far more than with me",
        ),
        "very_high": (
            "the app decides and I only find out afterwards",
            "there is a machine running my whole day and I am only the hands",
            "nothing in this is mine to decide, the system settles it and I drive",
        ),
    },
    # Part 6, platform algorithmic control: how closely the app guides, watches and pays me.
    "PAC": {
        "very_low": (
            "that is left entirely to me, the app has no part in it",
            "nothing of that reaches me from the app at all",
            "it gives me almost nothing to go on and I work it out myself",
            "there is no guidance in it worth the name",
            "I am not told or shown much of anything there",
        ),
        "low": (
            "it makes a gesture at it and leaves the rest to me",
            "barely, and never when it would actually help",
            "there is a little of it, not enough to lean on",
            "it does that in a thin way, more for show than for use",
            "it happens but I would not call it close attention",
        ),
        "mid": (
            "it manages that much, no more and no less",
            "it covers part of that and I fill in the rest myself",
            "it does some of that, some days more than others",
            "it is there in part, neither close nor absent",
            "a bit of it, enough to notice and not enough to depend on",
        ),
        "high": (
            "it stays close to that and I feel it over my shoulder",
            "it does that thoroughly, and I am aware of it all day",
            "it keeps a close eye on that and I know where I stand",
            "it is on top of that most of the time",
            "it watches that carefully and I can feel it watching",
        ),
        "very_high": (
            "that is measured constantly and I am never out of its sight",
            "it misses nothing there, every minute of it is counted",
            "it follows every bit of that, there is nothing it does not see",
            "that is tracked to the minute and nothing escapes it",
            "the whole day is recorded and that part most of all",
        ),
    },
    # Part 7, fairness: whether the matching and the assessing are done straight.
    "FAIR": {
        "very_low": (
            "nobody explains the reason and there is no one to ask",
            "there is nothing fair in how that is handled and no way to argue it",
            "it is done to me and I have no say in it at all",
        ),
        "low": (
            "it is unfair more often than not, and saying so changes nothing",
            "that side of it is poor and I have stopped expecting better",
            "it leans against me and I have learned to live with it",
        ),
        "mid": (
            "sometimes it feels fair and sometimes it does not, with no pattern I can see",
            "it is fair on a good day and not on a bad one",
            "I would call it middling, neither honest nor crooked",
        ),
        "high": (
            "it is mostly straight with me and I can usually see why",
            "that part is handled fairly enough, by and large",
            "I have little to complain of there in most weeks",
        ),
        "very_high": (
            "that is handled properly and I have never had cause to doubt it",
            "it is entirely fair there, and I would say so to anyone who asked",
            "I am treated right in that and I always know where I stand",
        ),
    },
    # Part 8, clarity: whether I can see how a decision was reached.
    "CLAR": {
        "very_low": (
            "I have no idea how any of it is worked out and nothing tells me",
            "it is a closed box, I see the outcome and never the reason",
            "no one has ever explained how that is decided",
        ),
        "low": (
            "I have a rough guess at it and nothing firmer than that",
            "little of it is explained and most of it I have to infer",
            "I know a piece of how it works, not enough to rely on",
        ),
        "mid": (
            "I understand part of it and the rest I have pieced together",
            "some of it is clear and some of it is guesswork",
            "I can follow it halfway and then it goes dark",
        ),
        "high": (
            "I have driven long enough to know when a good trip is being held back from me",
            "I can mostly explain how that works, I have watched it long enough",
            "it is reasonably open and I can follow the reasoning",
        ),
        "very_high": (
            "I could explain exactly how that is decided, I have studied it for years",
            "it is all plain to me, there is no mystery left in it",
            "I know that system inside out and could teach it to a new driver",
        ),
    },
    # Part 9, satisfaction.
    "SAT": {
        "very_low": (
            "I am tired of this work and it has taken more than it ever gave",
            "there is nothing in this job I am glad of any more",
            "I do it because I must, not because I like it",
        ),
        "low": (
            "it is not what I hoped for and most weeks I am unhappy in it",
            "I have more complaint than praise for this work",
            "the good days do not make up for the rest of them",
        ),
        "mid": (
            "some weeks I am glad of it and some weeks I am not",
            "it is work, no better and no worse than that",
            "I take the good with the bad and do not think too hard about it",
        ),
        "high": (
            "on the whole I am content with this work",
            "it suits me well enough and I am not looking elsewhere",
            "there is more to like in it than to dislike",
        ),
        "very_high": (
            "a quiet shift with steady trips and no trouble from anyone is all I ask",
            "this work has been good to me and I am glad of it",
            "I am happy in it, and I say that after many years of driving",
        ),
    },
    # Part 10, wanting the job to continue.
    "CONT": {
        "very_low": (
            "I do not see myself in this work much longer",
            "I hope this does not have to go on",
            "I am counting the months, not planning the years",
        ),
        "low": (
            "I would rather it did not have to continue, if something else came up",
            "I hope for something better than this carrying on",
            "I am not planning on this lasting",
        ),
        "mid": (
            "I will see how it goes, I have not decided either way",
            "it may carry on and it may not, I take it as it comes",
            "I have no firm plan about staying or going",
        ),
        "high": (
            "I hope to keep at this, it has worked out well enough so far",
            "I would like this to carry on a good while yet",
            "I am planning on staying, as things stand",
        ),
        "very_high": (
            "my family depends on what I earn and I hope to keep driving",
            "I want this to carry on as long as I am able to drive",
            "this is my work now and I intend to keep it",
        ),
    },
    # Part 11, working around the app: resenting algorithmic supervision, and gaming it.
    "ALGO": {
        "very_low": (
            "being managed this way does not trouble me at all",
            "I have no quarrel with the app running things",
            "I take what comes and never try to play it",
        ),
        "low": (
            "it bothers me a little, not enough to act on",
            "I would prefer a person sometimes, but it is a small thing",
            "I rarely bother trying to outsmart it",
        ),
        "mid": (
            "some days it grates on me and some days it does not",
            "I mind it in part, and I do work around it now and then",
            "it is a middling annoyance and I handle it when I must",
        ),
        "high": (
            "I would far rather a person decided this than a machine",
            "I have learned where to sit and when to go online to get better work",
            "it wears on me and I do what I can to turn it in my favour",
        ),
        "very_high": (
            "I will not be ruled by a machine that cannot be reasoned with",
            "I have worked out every trick there is to get better jobs out of it",
            "being managed like this is the worst part of the work and I fight it daily",
        ),
    },
    # Part 12, leaving.
    "TURN": {
        "very_low": (
            "leaving has not crossed my mind",
            "I am not looking anywhere else, this is where I am",
            "I have no plans at all to go",
        ),
        "low": (
            "I think about it rarely, and never seriously",
            "the thought comes and goes and I let it go",
            "I am not actively looking, though I would hear out an offer",
        ),
        "mid": (
            "it is on my mind some weeks and not others",
            "I think about leaving, I have not done anything about it",
            "I keep half an eye out and nothing more than that",
        ),
        "high": (
            "I have been asking around about other work",
            "I expect to be gone within the year if something turns up",
            "I have been looking, and looking seriously",
        ),
        "very_high": (
            "I am looking for a way out of this as fast as I can find one",
            "I will take the first decent thing that comes and leave",
            "I am done with this work, it is only a question of when",
        ),
    },
    # Part 13, economic dependence on the platform.
    "DEP": {
        "very_low": (
            "I could walk away tomorrow and find something else",
            "I am not tied to this, there is other work out there for me",
            "my living does not hang on this app",
        ),
        "low": (
            "I could find something, it would only take me a little while",
            "I am not trapped, though it would be a scramble for a month",
            "there are other options for me if it came to that",
        ),
        "mid": (
            "I could manage something else, it would not be easy",
            "I am tied to it in part, not completely",
            "it would hurt to lose this but it would not finish me",
        ),
        "high": (
            "I need this work to keep the house running",
            "there is not much else I could step into, so I stay",
            "what I earn here is what we live on",
        ),
        "very_high": (
            "without this there is nothing, I have no other way to feed them",
            "I have no choice in it, this app is the whole of my income",
            "everything we have comes out of this work and out of nothing else",
        ),
    },
}


# --------------------------------------------------------------------------- circumstance

#: ``fact tag -> variants``. The middle clause: a detail out of **this respondent's own drawn
#: record**, which is what makes two respondents with the same band read as two people.
#:
#: This is the clause that does the work in a wrong-person comparison. A stance clause is shared
#: by every respondent in its band; a circumstance clause is shared only by respondents who drew
#: the same city, service, tenure, household and dependence — and because those same draws moved
#: the construct targets, the detail is *correlated with the numbers* rather than ornamental.
#:
#: Digit-free by construction (I7): quantities arrive here already banded into words, so nothing
#: in this module has to spell a number and `generator/` needs nothing out of `persona/`.
CIRCUMSTANCE: dict[str, tuple[str, ...]] = {
    # --- service
    "service:cab": (
        "a cab costs me more to run than people think",
        "with a cab the long airport trips are what make the week",
        "in a cab you carry whoever you are given, and most days that is fine",
    ),
    "service:auto": (
        "in an auto the short trips are all I get and they barely cover the fuel",
        "an auto driver knows every lane, and the app still sends me the long way",
        "with an auto I am out in the heat and the rain both",
    ),
    "service:bike": (
        "on a bike it is parcels and passengers and no shelter from either",
        "on two wheels the day is quick money and quick risk",
        "a bike means more trips for less each, and more hours on the road",
    ),
    # --- city
    "city:Mumbai": (
        "in Mumbai the traffic eats the hour I was paid for",
        "Mumbai is a city where the rent goes up and the fare does not",
    ),
    "city:Pune": (
        "Pune has grown faster than the roads have",
        "in Pune the office crowd is the whole of my morning",
    ),
    "city:Delhi NCR": (
        "in Delhi the winter and the policing both cost me days",
        "across the NCR a trip can cross three borders and I pay for all of them",
    ),
    "city:Jaipur": (
        "Jaipur runs on the season, and in the off months there is nothing",
        "in Jaipur the tourist months carry the rest of the year",
    ),
    "city:Bengaluru": (
        "in Bengaluru I sit in traffic for half of what the app calls a trip",
        "Bengaluru has the work, it just takes two hours to reach it",
    ),
    # --- tenure
    "tenure:new": (
        "I am still new to this and much of it I am learning as I go",
        "I have only been at this a few months and I am still finding my feet",
    ),
    "tenure:settled": (
        "I have been at this a couple of years now and I know the pattern of it",
        "after a year or two you stop being surprised by it",
    ),
    "tenure:veteran": (
        "I have been driving on this app since the early days, when it paid properly",
        "I have been at this for years, and it was a different job when I started",
    ),
    # --- the vehicle
    "vehicle:loan": (
        "the instalment on the vehicle goes out whether I drive or not",
        "I took a loan for the vehicle and that payment comes first, before the house",
    ),
    "vehicle:owned": (
        "the vehicle is mine outright, which is the one thing in my favour",
        "at least the vehicle is paid for and nobody can take it",
    ),
    "vehicle:rented": (
        "I rent the vehicle from a fleet owner, so the first hours of the day are his",
        "the fleet owner takes his cut before I have earned anything of my own",
    ),
    # --- multi-apping
    "apps:multi": (
        "I keep the other apps open beside this one and take whichever pays",
        "I run two apps at once now, because one of them alone is not enough",
    ),
    "apps:single": (
        "this is the only app I drive on, so what it decides is what I get",
        "I do not run the other apps, which means I have no second place to go",
    ),
    # --- household
    "house:alone": (
        "it is only myself to feed, which is the one mercy in it",
        "I have nobody depending on me, so a bad week is only a bad week",
    ),
    "house:some": (
        "there are a few at home waiting on what I bring back",
        "my household is small but it still has to eat every day",
    ),
    "house:many": (
        "there is a houseful of people living on what this app pays me",
        "between the children and my parents there are many mouths on this one income",
    ),
    # --- economic dependence
    "need:low": (
        "I have other things I could turn to, so I am not afraid of it",
        "I do this by choice more than by need",
    ),
    "need:high": (
        "there is no other income in the house, so I cannot afford to be choosy",
        "I take what the app gives because I have nothing else to take",
    ),
    # --- how far an announced change would move this respondent (`v8`)
    #
    # **This is the one circumstance family the twin genuinely needs and never had.** Part 17 asks
    # how a respondent would answer under six described versions, and the answer is their baseline
    # moved by their own reactivity. The baseline is all over the persona; the reactivity was a
    # hidden batch constant, so a twin was asked for a quantity nobody had told it
    # (`docs/DECISIONS.md`, 2026-10-13).
    #
    # These are **dispositions, not answers.** None of them names a version, a lever, a dial or a
    # number, and the twin still has to work out which of six specific packages would matter to
    # this person and by how much. That is the same standing I8 already gives the baseline
    # attitudes: the whys live in the persona precisely so the twin can read "who this person is".
    "react:low": (
        "they announce things every few months and on the road nothing changes for me",
        "I have heard promises from this app before, and I judge it by what reaches my account",
        "a notice in the app is a notice in the app, it does not move me much either way",
        "whatever they put out, my week comes out about the same, so I have stopped reading them",
        "I would believe a change when I saw it in my earnings and not one day before",
    ),
    "react:mid": (
        "a real change would register with me, though I would want to see it hold for a while",
        "some of what they have announced made a difference and some of it made none",
        "if something actually changed I would notice, without expecting the work to transform",
        "I would give them some credit for a real change and keep the rest of my opinion",
        "it would shift how I see them a little, not all the way",
    ),
    "react:high": (
        "if they fixed the things that are wrong I would feel completely differently about this",
        "a proper change to the pay or the rules would turn this job around for me",
        "I am ready to think better of them the day they actually do something about it",
        "put the money and the rules right and this becomes a job I would speak well of",
        "one real change on the things that matter and my whole view of this work turns over",
    ),
    # --- which announced change would matter most to this respondent (`v10`)
    #
    # **The second hidden batch constant, and the one that was left.** `lever_reactions` carried
    # `{L1: 2.0, L2..L5: 1.0}` — pay double-weighted for the whole batch, mentioned in no
    # persona. The twin learned to tell the six Part 17 versions apart (its spread across them
    # more than doubled at stage 3) and ranked them in the wrong order, putting a version that
    # raises no pay second where its driver put it fifth. Which lever a driver weights is now
    # drawn per respondent and spoken here (`docs/DECISIONS.md`, 2026-10-13).
    #
    # Like `react:*` these are **dispositions, not answers.** None names a version, a lever id, a
    # dial or a number; each names the thing in the driver's own terms, and the twin still has to
    # work out which of six specific packages touches it and by how much. That is the standing I8
    # already gives the baseline attitudes.
    "salience:pay": (
        "the money is the only thing that would really change my mind about this",
        "fix the fare and I would forgive the rest of it",
        "what I care about is what lands in my account at the end of the week, not the policies",
        "everything else is talk; the rate per kilometre is the job",
        "I would take worse conditions for better pay, and that is the honest truth of it",
    ),
    "salience:conditions": (
        "what weighs on me is the safety of it, more than the money",
        "an insurance that actually paid out would mean more to me than a fare rise",
        "I think about what happens to my family if something happens to me on the road",
        "the hours and the risk are what wear me down, not the earnings",
        "give me a safer day on the road and I would not be asking about the rate",
    ),
    "salience:contracts": (
        "what I want is to know the rules, not to be guessed at",
        "if they told me plainly how the pay is worked out I would be a different driver",
        "it is the not knowing that gets me, more than the amount",
        "I could live with the money if I understood how it was decided",
        "show me the terms in writing and in my own language and that would matter most to me",
    ),
    "salience:appeals": (
        "it is the disrespect, not the money",
        "give me somewhere to appeal and a person to answer me and I would feel differently",
        "being switched off with no explanation is the thing I cannot accept",
        "what I want is to be heard by a human being when something goes wrong",
        "the money I can argue about; being treated as nobody is what I cannot",
    ),
    "salience:forum": (
        "alone I am nothing to them, and that is what needs to change",
        "what would matter is drivers having a body that speaks for us",
        "one driver complaining is noise; all of us together would be heard",
        "I would want us organised before I would want a few rupees more",
        "until there is someone to speak for drivers, the rest of it does not hold",
    ),
}


#: ``band -> variants``. The closing clause, when the respondent is talkative enough to add one.
#: Keyed on band alone rather than on the block: a consequence is about how strongly the person
#: feels, and nine block-specific banks would add length without adding discrimination.
CONSEQUENCE: dict[str, tuple[str, ...]] = {
    "very_low": (
        "so I have never had to think much about it",
        "and I would be surprised if it ever changed",
        "so it is simply not something that comes up for me",
    ),
    "low": (
        "so I let it go most of the time",
        "and complaining about it has never got me anywhere",
        "so I work around it and say nothing",
    ),
    "mid": (
        "so I take it as it comes",
        "and I have stopped trying to predict which it will be",
        "so some weeks I mind it and some weeks I do not",
    ),
    "high": (
        "so it is on my mind most days",
        "and it shapes how I plan the week",
        "so I have had to change how I work because of it",
    ),
    "very_high": (
        "and it is the thing I would change first if anyone asked me",
        "so it decides how the whole of my week goes",
        "and nothing else about this work weighs on me as much",
    ),
}

#: One or two of these are drawn **per respondent** and recur across their answers. A recurring
#: preoccupation is the cheapest signal that a passage is one person rather than thirty-nine
#: samples, and attribution is exactly what a wrong-person comparison tests.
MOTIFS: tuple[str, ...] = (
    "the waiting between trips is the part nobody counts",
    "my rating sits there and I can never tell what moved it",
    "the cancellations are counted against me even when the rider cancels",
    "the incentive target moves just as I get near it",
    "the support chat answers with the same written lines every time",
    "the fuel price goes up on its own and the fare never follows",
    "the surge shows on the map and is gone by the time I reach it",
    "I am logged in far longer than I am paid for",
)

#: How a respondent talks, drawn once and held for all 39 answers.
REGISTERS: tuple[str, ...] = ("terse", "explaining", "aggrieved")

#: Connectors, per register. A terse respondent joins with a comma, an explaining one spells the
#: link out, an aggrieved one leads with the grievance.
_JOIN: dict[str, tuple[str, str]] = {
    "terse": (", ", ", "),
    "explaining": (", and ", ", so "),
    "aggrieved": (" and ", " and honestly "),
}


# --------------------------------------------------------------------------- Part 14

#: ``own_words id -> band -> variants``. Part 14 asks five open questions and each is **banded on
#: the construct it actually asks about**, not on a shared disposition:
#:
#: ===== ========================================= ==========================================
#: id    the prompt (`templates.OWN_WORDS_PROMPTS`) banded on
#: ===== ========================================= ==========================================
#: OWN1  my least difficult day                     SATI, happiness
#: OWN2  how the app decides pay and who gets it    TRAN, clarity
#: OWN3  needing help, or being blocked             FAIR, fairness
#: OWN4  what drivers and I do about a problem      VOIC, pushback
#: OWN5  who depends on me, and the next year or two EXIT, leaving
#: ===== ========================================= ==========================================
#:
#: OWN5 is the one that earns the most: a respondent high on leaving and low on dependence says
#: something structurally different from one low on leaving and high on dependence, and those are
#: precisely the H2 answers a wrong-person comparison scores a twin against. Before `v6` all five
#: were one constant tuple, identical for every twin in the panel.
OWN_WORDS_BANK: dict[str, dict[str, tuple[str, ...]]] = {
    "OWN1": {
        "very_low": (
            "there is no easy day in this work any more, the best I get is one that ends",
            "even my good days are only days where nothing went badly wrong",
        ),
        "low": (
            "an easy day is a rare thing, mostly it is one long stretch of waiting and driving",
            "the least difficult day is still eleven hours out of the house",
        ),
        "mid": (
            "an easy day is one where the trips come one after another and nobody argues",
            "on a good day I finish the target early and go home while it is still light",
        ),
        "high": (
            "a good day is steady trips, a decent fare on each, and home in time to eat",
            "my easiest days are the ones where the app and I want the same thing",
        ),
        "very_high": (
            "a quiet shift with steady trips and no trouble from anyone",
            "most days are good ones, I drive, I earn what I expected, and I go home",
        ),
    },
    "OWN2": {
        "very_low": (
            "I have no idea how it decides, I open the app and take what appears",
            "nobody has ever told me how the fare is worked out and I have stopped asking",
        ),
        "low": (
            "I think it goes by distance and something else that nobody explains",
            "the app gives the trip to whoever is closest, or so I am told",
        ),
        "mid": (
            "I believe it is distance and time and how busy the area is, mostly",
            "I have worked out part of it, the rest changes before I can learn it",
        ),
        "high": (
            "it is distance, time and demand, and it favours the drivers who stay logged in",
            "I have watched it long enough to predict most of what it will offer me",
        ),
        "very_high": (
            "I can tell you exactly how it decides, I have tracked it trip by trip for years",
            "it goes by distance, waiting time and the acceptance record, and I know my own",
        ),
    },
    "OWN3": {
        "very_low": (
            "my account was blocked once and it took many days to hear back",
            "when I needed help there was nobody there, only the same written reply again",
        ),
        "low": (
            "I wrote to support about a wrong fare and the answer never addressed it",
            "I was penalised for a cancellation that was not mine and could not get it undone",
        ),
        "mid": (
            "I have needed help twice, once it was sorted and once it was not",
            "support is slow but it has come through for me in the end before",
        ),
        "high": (
            "the one time I was blocked it was lifted after I explained it",
            "I have had an issue or two and they were put right without much trouble",
        ),
        "very_high": (
            "I have never been blocked and the one time I asked for help it was handled at once",
            "I have had no trouble of that kind, and when I asked a question it was answered",
        ),
        #: Not a band. :data:`NO_INCIDENT` is the cell for a respondent drawn **without** a
        #: support or deactivation story, whatever they think of the platform's fairness.
        #:
        #: It cannot be the `very_high` cell, which is what `v6` first did: that text asserts a
        #: *good* support experience, so a respondent who rated fairness at the floor and happened
        #: to be drawn without an incident claimed their one request for help was handled at once.
        #: A persona that contradicts its own fairness block is the `v5` defect again in a new
        #: place. These say only that there is nothing to report, which is the truthful thing for
        #: a driver who has never had to ask.
        NO_INCIDENT: (
            "I have never had to ask them for anything, so I could not tell you how it would go",
            "nothing like that has happened to me, I have been lucky in that much at least",
            "I have not been blocked or penalised, so I have no story to tell there",
        ),
    },
    "OWN4": {
        "very_low": (
            "there is nothing we can do about it, so we do nothing and keep driving",
            "we complain among ourselves and that is where it ends",
        ),
        "low": (
            "we talk about it at the tea stall and nobody takes it further",
            "a few of us grumble, but no one wants to be the one who is noticed",
        ),
        "mid": (
            "we talk among ourselves and share what we learn about the app",
            "there is a group on the phone where we warn each other, and sometimes that is enough",
        ),
        "high": (
            "we organise on the phone group, and when it is bad enough we go to the office",
            "we share what works, and we have gone offline together more than once to make a point",
        ),
        "very_high": (
            "we are organised now, we go to the office as a body and we have stopped work before",
            "when they push us we all log off on the same morning, and they notice that",
        ),
    },
    "OWN5": {
        "very_low": (
            "my family depends on what I earn and I hope to keep driving",
            "those at home are counting on this and I plan to be doing it for years yet",
        ),
        "low": (
            "I have people to feed and no plan to change what I do",
            "this is the work I have, and in a year or two I expect to be doing the same",
        ),
        "mid": (
            "there are people at home on this income, and where I will be in a year I cannot say",
            "I support my household with it and I am keeping my options open beyond that",
        ),
        "high": (
            "they depend on me, which is the only reason I am still here, and I am looking",
            "I have a household to carry and I am trying to find a way to carry it differently",
        ),
        "very_high": (
            "the house runs on this and I still mean to be out of it within the year",
            "people depend on me and I am taking the first thing that lets me stop driving",
        ),
    },
}


@dataclass(frozen=True)
class Voice:
    """How one synthetic respondent talks. Drawn once, held across all 39 free-text answers.

    The passage-level consistency is the point. Thirty-nine independently sampled good sentences
    still read as a committee; the same thirty-nine in one voice, with one or two recurring
    preoccupations, read as a driver — and attribution is what a wrong-person comparison measures.

    Frozen, so a composition step cannot quietly re-draw a respondent's register halfway through
    the passage.
    """

    #: One, two or three clauses per answer: stance alone, stance and circumstance, or all three.
    verbosity: int
    #: One of :data:`REGISTERS`, which fixes the connectors.
    register: str
    #: One or two of :data:`MOTIFS`, this respondent's recurring complaints.
    motifs: tuple[str, ...]
    #: The circumstance tags this respondent is entitled to, in a fixed order.
    facts: tuple[str, ...]
    #: Where in :attr:`facts` this respondent's rotation starts. Without it the rotation is
    #: positional and therefore identical across the panel — every respondent's `OWN1` would
    #: open on their tenure and every `WHY_AMQ1` on their city, which is a formulaic pattern a
    #: reader would spot at once even though no two sentences matched.
    fact_offset: int
    #: Whether this respondent has a support or deactivation story at all. Drawn rather than
    #: inferred, because it changes OWN3 **structurally** and not only in wording — some drivers
    #: have been blocked and some have not, and that is a larger individuality signal than any
    #: amount of paraphrase variety.
    had_incident: bool


def facts_of(
    *,
    city: str,
    service: str,
    tenure_months: int,
    dependants: int,
    vehicle_arrangement: str,
    multi_apping: bool,
    edep_position: float,
    reactivity: float,
    lever_weights: dict[str, float],
) -> tuple[str, ...]:
    """The circumstance tags a respondent is entitled to, from their own drawn record.

    Read in a fixed order so the batch stays deterministic. Every tag must exist in
    :data:`CIRCUMSTANCE`; an unmapped service or city raises from :func:`circumstance_for` rather
    than contributing a silently empty clause (`CLAUDE.md` rule 7).
    """
    if service.startswith("Cab"):
        service_tag = "service:cab"
    elif service.startswith("Auto"):
        service_tag = "service:auto"
    elif service.startswith("Motorcycle"):
        service_tag = "service:bike"
    else:
        raise VoiceBankIncomplete(
            f"no circumstance tag for service {service!r}; add one rather than letting a "
            "respondent carry no service detail"
        )

    if tenure_months < 12:
        tenure_tag = "tenure:new"
    elif tenure_months < 36:
        tenure_tag = "tenure:settled"
    else:
        tenure_tag = "tenure:veteran"

    if vehicle_arrangement.startswith("Own with"):
        vehicle_tag = "vehicle:loan"
    elif vehicle_arrangement.startswith("Own"):
        vehicle_tag = "vehicle:owned"
    elif vehicle_arrangement.startswith("Rent"):
        vehicle_tag = "vehicle:rented"
    else:
        raise VoiceBankIncomplete(
            f"no circumstance tag for vehicle arrangement {vehicle_arrangement!r}"
        )

    if dependants == 0:
        house_tag = "house:alone"
    elif dependants <= 3:
        house_tag = "house:some"
    else:
        house_tag = "house:many"

    salience = salience_tag(lever_weights)

    return (
        f"city:{city}",
        service_tag,
        tenure_tag,
        vehicle_tag,
        house_tag,
        "apps:multi" if multi_apping else "apps:single",
        "need:high" if edep_position >= 0.5 else "need:low",
        # **Three slots, not one** (`v9`). The rotation gives each tag roughly an equal share of
        # the 42 free-text answers, so at one slot in eight the reactivity clause appeared one to
        # three times in a passage of 1,700–2,450 words — once, in one case, at 93% of the way
        # through. With the H3 prompt directing the twin to find it (`twin_h3_v3.md`) the twin
        # began varying its answers per driver but tracked the real reactivity only weakly
        # (r +0.20 against a +0.59 ceiling) while overshooting its drivers' spread by 90%: it was
        # hunting for a signal it could not reliably locate. Three slots put the clause early for
        # most respondents and repeat it often enough to be unmissable.
        #
        # Repeated rather than given its own persona heading **on purpose**. A dedicated section
        # would be the obvious fix, and a real driver has no such field — a synthetic persona
        # would then carry a shape no real one does, which is the parity `CLAUDE.md` insists on
        # when it refuses a respondent who answered three of 37 probes. Legibility has to come
        # from placement inside the shape real personas already have.
        reactivity_tag(reactivity),
        reactivity_tag(reactivity),
        reactivity_tag(reactivity),
        # **Three slots for lever salience too** (`v10`), on the precedent that three is what
        # reactivity needed before the twin could track it: at one slot the clause surfaced one to
        # three times in a passage of 1,700–2,450 words and tracked at r +0.20; at three it
        # tracked at +0.87. Salience is asked for by the same question — Part 17 wants the
        # baseline moved by *this* person's reaction to *that* package — so it needs comparable
        # prominence, and the mention-count measurement in the handoff §7 is how it gets checked.
        #
        # In the existing free-text shape, like reactivity and for the same reason: a real driver
        # has no "which change matters most to me" field, so a synthetic persona with one would
        # carry a shape no real persona does.
        #
        # Omitted entirely when `salience_tag` returns `None` — a batch with every reaction
        # slider at zero (`docs/06` §4's null) has no lever that matters most, and the tuple being
        # shorter there is correct rather than something to pad.
    ) + ((salience,) * 3 if salience else ())


def draw_voice(
    rng: random.Random, *, facts: tuple[str, ...], incident_share: float
) -> Voice:
    """One respondent's voice. Every value is drawn from ``rng``, in a fixed order.

    The order is fixed, not the *count*: `rng.choice` and `rng.sample` reach `_randbelow`, whose
    rejection sampling consumes a variable number of primitive values by design, so no
    composition built on them has a constant draw count. What the reproducibility guarantee
    (`docs/09` §2) needs is weaker and sufficient — the draws are a deterministic function of the
    seed, so nothing here can shift a later answer except through the seed and the spec. Nothing
    reads the global RNG, no set is iterated, and :attr:`Voice.motifs` is sorted before it is
    frozen so the sample's order cannot leak into the text.
    """
    verbosity = rng.choice((1, 2, 2, 3, 3))
    register = rng.choice(REGISTERS)
    motif_count = rng.choice((1, 1, 2))
    motifs = tuple(sorted(rng.sample(MOTIFS, motif_count)))
    had_incident = rng.random() < incident_share
    fact_offset = rng.randrange(len(facts)) if facts else 0
    return Voice(
        verbosity=verbosity,
        register=register,
        motifs=motifs,
        facts=facts,
        fact_offset=fact_offset,
        had_incident=had_incident,
    )


def _fact_at(voice: Voice, index: int) -> str:
    """The circumstance tag at ``index`` of this respondent's own rotation."""
    return voice.facts[(index + voice.fact_offset) % len(voice.facts)]


#: A respondent's draw-without-replacement queues, keyed by bank cell. Handed to each
#: composition call and mutated in place.
Queues = dict[str, list[str]]


def _without_replacement(
    rng: random.Random, queues: Queues, key: str, variants: tuple[str, ...]
) -> str:
    """One variant, cycling through the cell before any of it repeats.

    `PAC` is an eleven-item block, and a respondent's eleven answers mostly land in **one** band —
    that is what having a disposition means. Drawing independently from a three-variant cell then
    put the same sentence in the block five times, which reads as a template rather than as a
    person however well the bank is written.

    Refilled with a fresh shuffle when exhausted, so a cell smaller than its block still spreads
    rather than clustering. The shuffle comes from the respondent's own ``rng``, so this costs
    determinism nothing.
    """
    queue = queues.get(key)
    if not queue:
        queue = list(variants)
        rng.shuffle(queue)
        queues[key] = queue
    return queue.pop()


def stance_for(
    block: str, band: str, rng: random.Random, queues: Queues | None = None
) -> str:
    """One stance clause. Raises on an unknown block or band rather than falling back."""
    try:
        variants = STANCE[block][band]
    except KeyError as exc:
        raise VoiceBankIncomplete(
            f"no stance text for block {block!r} band {band!r}. Add the cell to STANCE; a "
            "fallback to a neighbouring band would put the wrong strength of explanation under "
            "this rating, which is the v5 defect voice.py exists to remove."
        ) from exc
    if queues is None:
        return rng.choice(variants)
    return _without_replacement(rng, queues, f"stance:{block}:{band}", variants)


def circumstance_for(
    tag: str, rng: random.Random, queues: Queues | None = None
) -> str:
    """One circumstance clause for a tag. Raises on an unmapped tag (`CLAUDE.md` rule 7)."""
    try:
        variants = CIRCUMSTANCE[tag]
    except KeyError as exc:
        raise VoiceBankIncomplete(
            f"no circumstance text for {tag!r}; add it rather than letting the respondent carry "
            "no detail for a fact they were drawn with"
        ) from exc
    if queues is None:
        return rng.choice(variants)
    return _without_replacement(rng, queues, f"fact:{tag}", variants)


def _assemble(parts: list[str], register: str) -> str:
    """Join one to three clauses with this register's connectors.

    The third connector falls back to a plain *and* when the clause before it already contains a
    *so*: several circumstance fragments carry their own consequence ("so I cannot afford to be
    choosy"), and "so X, so Y" reads as a machine rather than a driver.
    """
    if not parts:  # pragma: no cover — stance is always present
        raise VoiceBankIncomplete("an answer must have at least a stance clause")
    first, second = _JOIN[register]
    text = parts[0]
    if len(parts) > 1:
        text = f"{text}{first}{parts[1]}"
    if len(parts) > 2:
        if " so " in parts[1] and " so " in second:
            second = ", and "
        text = f"{text}{second}{parts[2]}"
    return text


def compose_why(
    rng: random.Random,
    voice: Voice,
    *,
    block: str,
    band: str,
    facts_index: int,
    queues: Queues | None = None,
) -> str:
    """One why answer: stance at this item's own band, then the respondent's own circumstance.

    ``facts_index`` walks the respondent's fact tuple so a block of eleven items does not lean on
    the same detail eleven times. It rotates from the respondent's own :attr:`Voice.fact_offset`
    rather than being drawn, so the rotation costs no randomness at all while still starting each
    respondent somewhere different -- without the offset the rotation would be positional and
    therefore identical across the panel.

    A **terse** respondent (verbosity one) still gets a circumstance clause on some of their whys
    rather than none. A genuinely terse real respondent writes four words and stops, but a terse
    *synthetic* respondent with stance only would carry no individuality at all — they would be
    the one group in the panel that a wrong-person comparison could not tell apart, which is the
    defect this module exists to remove. They are terse in most answers and identifiable across
    the set.
    """
    parts = [stance_for(block, band, rng, queues)]
    # Drawn unconditionally, so the *sequence* of draws does not depend on the branch taken.
    terse_roll = rng.random()
    wants_circumstance = voice.verbosity >= 2 or terse_roll < 0.4
    if wants_circumstance and voice.facts:
        parts.append(circumstance_for(_fact_at(voice, facts_index), rng, queues))
    if voice.verbosity >= 3:
        # A motif displaces the generic consequence now and then, which is what makes a
        # preoccupation recur without making every third answer identical.
        if voice.motifs and rng.random() < 0.35:
            parts.append(rng.choice(voice.motifs))
        else:
            parts.append(rng.choice(CONSEQUENCE[band]))
    return _assemble(parts, voice.register)


def compose_own_words(
    rng: random.Random,
    voice: Voice,
    *,
    own_id: str,
    band: str,
    facts_index: int,
    queues: Queues | None = None,
) -> str:
    """One Part 14 narrative: the banded story, then this respondent's own circumstance.

    OWN3 is the one case where the band is not the whole story: a respondent drawn **without** an
    incident has no deactivation to narrate however unfairly they rate the platform, so the band
    is lifted to the top of the bank for them. That is not a repair of a bad answer — there is no
    answer being altered — it is the generator refusing to write a story the respondent does not
    have.
    """
    try:
        bank = OWN_WORDS_BANK[own_id]
    except KeyError as exc:
        raise VoiceBankIncomplete(
            f"no Part 14 bank for {own_id!r}; every id in OWN_WORDS_IDS needs one, since a "
            "persona missing a Part 14 answer is lossy (I6)"
        ) from exc
    if own_id == "OWN3" and not voice.had_incident:
        band = NO_INCIDENT
    try:
        variants = bank[band]
    except KeyError as exc:
        raise VoiceBankIncomplete(f"no {own_id!r} text for band {band!r}") from exc

    parts = [rng.choice(variants)]
    # Part 14 is the passage's longest block and the one a reader attributes from, so it carries
    # a circumstance clause at every verbosity rather than only from two upwards.
    if voice.facts:
        parts.append(circumstance_for(_fact_at(voice, facts_index), rng, queues))
    # A motif on *some* of the five, never all five. Appended unconditionally it produced a
    # respondent who closed every one of their Part 14 answers with the same complaint — a broken
    # record rather than a voice, and five identical tails are easier to pattern-match than they
    # are to attribute.
    motif_roll = rng.random()
    if voice.verbosity >= 2 and voice.motifs and motif_roll < 0.4:
        parts.append(rng.choice(voice.motifs))
    return _assemble(parts, voice.register)


def assert_banks_complete(blocks: tuple[str, ...], own_ids: tuple[str, ...]) -> None:
    """Every (block, band) and (own id, band) cell is populated, and nothing holds a digit.

    Called from the test suite rather than at import: a missing cell is a programming error in
    this module, and raising at import time would take down a Space on a typo in prose. The digit
    check is I7's — the persona builder quotes these verbatim, so this module is the only guard.
    """
    for block in blocks:
        for band in BANDS:
            variants = STANCE.get(block, {}).get(band)
            if not variants:
                raise VoiceBankIncomplete(f"STANCE[{block!r}][{band!r}] is empty")
    for own_id in own_ids:
        for band in BANDS:
            variants = OWN_WORDS_BANK.get(own_id, {}).get(band)
            if not variants:
                raise VoiceBankIncomplete(f"OWN_WORDS_BANK[{own_id!r}][{band!r}] is empty")
    if not OWN_WORDS_BANK.get("OWN3", {}).get(NO_INCIDENT):
        raise VoiceBankIncomplete(
            "OWN_WORDS_BANK['OWN3'] has no no-incident cell, so a respondent drawn without a "
            "support story would have to borrow a band that asserts one"
        )

    every: list[str] = [t for cell in STANCE.values() for v in cell.values() for t in v]
    every += [t for cell in OWN_WORDS_BANK.values() for v in cell.values() for t in v]
    every += [t for v in CIRCUMSTANCE.values() for t in v]
    every += [t for v in CONSEQUENCE.values() for t in v]
    every += list(MOTIFS)
    offenders = [t for t in every if any(ch.isdigit() for ch in t)]
    if offenders:
        raise VoiceBankIncomplete(
            f"these fragments carry a digit, which would put a bare numeral in a persona "
            f"passage (I7): {offenders}"
        )
