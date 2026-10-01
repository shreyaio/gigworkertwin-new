"""Seeded synthetic surveys. `docs/11` M9. Serves I16 and the reproducibility guarantee.

**No LLM call, ever.** A synthetic respondent is drawn from seeded distributions in Python. A
model-written survey would be unreproducible, would cost a call per respondent, and would smuggle
the model's own priors into the data the twins are built from.

The generator emits a payload in **exactly the shape the Google Form sends**, keyed on the same
``"SECTION|TITLE"`` pairs, and then runs it through :func:`ingest.survey_intake.build_rows`. That
is deliberate: the synthetic path and the real path share one row builder, so a synthetic
submission cannot have a shape a real one could not, and every question in `form_map.yaml` is
answered by construction — a generator that missed one would raise :class:`UnmappedQuestion` from
the same code that guards live intake.

**Same seed → identical batch, across processes.** Every draw comes from a local
`random.Random(seed)`; nothing reads the global RNG, no set is iterated, and every dictionary is
built in sorted key order.

Synthetic data is for exercising the machinery. `docs/08` §6.2 — **synthetic data proves nothing**
about drivers, and every surface that shows it says so.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Any

import yaml

from config.settings import CONFIG_DIR
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.ingest.survey_intake import build_rows, form_map, raw_object_path
from twinlab.models.reference import (
    LEVER_BY_POSITION,
    construct_code_for,
)
from twinlab.models.view import GENERATOR_CITIES, GENERATOR_SERVICES, GeneratorSpec

#: `docs/06` §4's three presets, as a shift of the respondent-level disposition in units of the
#: disposition's own range. "Mixed" is the midpoint, which is what the generator always drew.
SENTIMENT_CENTRE: dict[str, float] = {
    "frustrated": -0.55,
    "mixed": 0.0,
    "content": 0.55,
}

#: The id prefix `docs/01` §6 gives synthetic submissions: `SYN-` against `UBR-` for real.
SYNTHETIC_PREFIX = "SYN"

#: `docs/01` §6: synthetic rows carry this `data_type`, and **delete-synthetic keys on it.**
SYNTHETIC_DATA_TYPE = "SYNTHETIC"

#: Which generator drew a batch. **Bump this whenever the draw ORDER changes**, not only when a
#: value changes: "same seed, same batch" (`docs/09` §2) holds within a version, never across
#: one. `v2` added `docs/06` §4's controls, and city and service moved from `random.choice` to a
#: weighted draw — which consumes the respondent's RNG differently, so a `v1` seed does not
#: reproduce under `v2`. Recorded on every batch so the break is visible in the data rather than
#: being something a later reader has to infer. Synthetic rows exist to exercise the machinery
#: and prove nothing about drivers (`docs/08` §6.2), so regenerating a `v1` batch costs nothing
#: but the seconds it takes.
#:
#: `v3` added `docs/06` §4's remaining controls — the fifth city, multi-apping, the vehicle loan,
#: economic dependence, the shared-mood weight and the five lever reactions — reversed the
#: reverse-coded items (which `v2` drew as though they were forward-scored, so `SAT2` rose with
#: satisfaction) and made the two holdout blocks answer the change rather than repeat the
#: baseline. Every one of those changes the draw order. **A `v2` seed does not reproduce under
#: `v3`.**
GENERATOR_VERSION = "v3"

#: Free-text answers. Short, obviously synthetic, and deliberately digit-free so a synthetic persona
#: cannot smuggle a number into the words-not-numbers passage (I7).
_WHY_TEXTS: tuple[str, ...] = (
    "the app decides and I only find out afterwards",
    "sometimes it feels fair and sometimes it does not, with no pattern I can see",
    "I have driven long enough to know when a good trip is being held back from me",
    "nobody explains the reason and there is no one to ask",
)
_OWN_WORDS: tuple[str, ...] = (
    "a quiet shift with steady trips and no trouble from anyone",
    "the app gives the trip to whoever is closest, or so I am told",
    "my account was blocked once and it took many days to hear back",
    "we talk among ourselves and share what we learn about the app",
    "my family depends on what I earn and I hope to keep driving",
)
#: Re-exported from the view model so there is one spelling of each. The Form's own options
#: (`docs/GOOGLE_FORM.md` Part 3): a generated value outside them is one live intake could never
#: receive. The previous list held four cities and spelled Delhi NCR as "Delhi".
_CITIES: tuple[str, ...] = GENERATOR_CITIES
_SERVICES: tuple[str, ...] = GENERATOR_SERVICES
_GENDERS: tuple[str, ...] = ("Man", "Woman", "Prefer not to say")
_EDUCATION: tuple[str, ...] = ("Secondary school", "Higher secondary", "Graduate")
_VEHICLE: tuple[str, ...] = ("Own outright", "Own with a loan", "Rent from a fleet owner")
_HOUSEHOLD: tuple[str, ...] = ("None", "A family member earns", "Some farming income")
_LANGUAGES: tuple[str, ...] = ("English", "Hindi", "Marathi")


class GeneratorError(RuntimeError):
    """A batch that must not be produced."""


@lru_cache(maxsize=1)
def generator_config() -> dict:
    """`config/generator.default.yaml`."""
    path = CONFIG_DIR / "generator.default.yaml"
    if not path.exists():
        raise GeneratorError(f"{path} is absent; it is the seed generator config")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _keys_by_target() -> dict[str, str]:
    """``target → "SECTION|TITLE"``, inverted from `form_map.yaml`.

    Inverting the real map is what guarantees coverage: the generator answers every question the
    map knows about, so it cannot produce a payload that live intake would reject.
    """
    out: dict[str, str] = {}
    for key, target in sorted(form_map().items()):
        out[target] = key
    return out


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """One key, drawn in proportion to its weight. Keys are read in sorted order.

    `random.choices` is not used: its behaviour across Python versions is not something this
    module can pin, and "same seed, same batch, across processes" is a reproducibility
    guarantee (`docs/09` §2), not a convenience.
    """
    items = sorted(weights.items())
    total = sum(weight for _, weight in items)
    landed = rng.random() * total
    running = 0.0
    for key, weight in items:
        running += weight
        if landed < running:
            return key
    return items[-1][0]


def years_from_months(months: int) -> str:
    """The Form's *years* answer for a tenure the dashboard set in months.

    `docs/06` §4's dashboard asks in months — three months is the eligibility floor and
    "0.25 years" is not a quantity a researcher sets — while the Form asks in years and intake
    converts back (`docs/DECISIONS.md`, 2026-09-22). This is the only place the two meet, and it
    **round-trips exactly**: ``round(float(years_from_months(m)) * 12) == m`` for every integer
    month, which is what stops a batch's stored tenure disagreeing with the tenure it was drawn
    with. Two decimal places are enough for that up to 600 months and no more are written.
    """
    if months < 0:
        raise GeneratorError(f"tenure must not be negative, got {months} months")
    return f"{months / 12:.2f}"


def centre_for_points(target_1_to_7: float, points: int) -> float:
    """A 1–7 dashboard target, read as the same *position* on a ``points``-point scale.

    `docs/06` §4's sliders are captioned "average answer on a 1 to 7 scale (5 point questions are
    converted)", and this is that conversion. It is a **linear map of the scale's range**, not a
    clamp: 7/7 becomes 5/5 and 4/7 becomes 3/5, so a slider set to "strongly agree" means
    strongly agree on both of the register's scale lengths.

    This is generation, not repair. `docs/02` §5.3's ban on clamping is about coercing a
    *model's* output into validity; here there is no respondent whose answer is being altered.
    """
    if points < 2:
        raise GeneratorError(f"a {points}-point scale cannot carry an answer")
    position = (max(1.0, min(7.0, target_1_to_7)) - 1.0) / 6.0
    return 1.0 + position * (points - 1)


def dials_of_code(version_code: str) -> dict[str, int]:
    """``'01000'`` → ``{'L1': 0, 'L2': 1, ...}``. The odometer's frozen order (I2).

    Read straight off the string rather than imported from `services.dials`: `generator/` sits
    below the service layer, and the position→lever order is a frozen constant in `models/`.
    """
    if len(version_code) != len(LEVER_BY_POSITION):
        raise GeneratorError(
            f"{version_code!r} is not a five-digit version code; the odometer order is frozen (I2)"
        )
    return {lever: int(version_code[i]) for i, lever in enumerate(LEVER_BY_POSITION)}


def reaction_shift(
    version_code: str, spec: GeneratorSpec, *, economic_dependence: float
) -> float:
    """How far a respondent's answers move under ``version_code``, in 1–7 scale points.

    This is what `docs/06` §4's *how strongly they react to each change* sliders **do**. Each
    lever contributes ``dial × reaction weight``, summed over the five levers and scaled so a
    version with every dial at 2 and every reaction at "normal" moves a respondent about two
    points — the size of a real treatment effect on a seven-point scale, not a ceiling jump.

    ``economic_dependence`` is the respondent's own EDEP position in ``[0, 1]``. With
    ``spec.captive_voice`` on, it raises the weight of the **representation** lever only: a driver
    who needs the money reacts more to a drivers' forum than one who does not. That is §4's
    captive-voice checkbox, and it is a property of the synthetic *respondent* — no twin, no
    model call, and nothing here reads a metric.

    The value is a direction-free magnitude. Its **sign** is applied by the caller, from the
    construct's own `index_sign`, because more protection raises fairness and lowers the wish to
    leave and one number cannot carry both.
    """
    total = 0.0
    for lever, dial in dials_of_code(version_code).items():
        weight = spec.reaction(lever)
        if lever == "L5" and spec.captive_voice:
            # A multiplier in [1.0, 2.0]: at EDEP 1.0 the forum lands twice as hard.
            weight *= 1.0 + max(0.0, min(1.0, economic_dependence))
        total += dial * weight
    # 10 = five levers x dial 2 x weight 1. Two scale points is the full-protection move.
    return 2.0 * total / 10.0


def _likert(rng: random.Random, points: int, centre: float, sd: float = 1.1) -> int:
    """A plausible Likert answer: a rounded normal draw clamped to the scale.

    Clamping is correct here and forbidden elsewhere. This is **generation**, not repair: there is
    no respondent whose answer is being altered, and `docs/02` §5.3's ban on clamping is about
    coercing a
    *model's* output into validity, which would hide a real failure.
    """
    value = round(rng.gauss(centre, sd))
    return max(1, min(points, value))


def synthetic_payload(
    *,
    seed: int,
    index: int,
    arm: str,
    ref: ReferenceData | None = None,
    spec: GeneratorSpec | None = None,
) -> dict[str, Any]:
    """One complete Form-shaped payload. Deterministic in ``(seed, index)``.

    Every key in `form_map.yaml` is answered: the 73 register items (37 battery + 16 H2 + 18 H3 +
    the 2 attention checks), the three why-probes, the five own-words fields, the demographics,
    all eight screeners and all eight consent statements.

    The attention checks are answered **correctly** unless ``spec.attention_fail_share`` says
    otherwise, so a synthetic respondent passes `attention_passed` and is therefore
    quality-testable — a batch that failed its own attention checks could never produce a twin
    and would make the generator useless for exercising the gate. The share is a control rather
    than a constant because exercising the *screening* switch needs it above zero.

    ``spec`` carries `docs/06` §4's dashboard. Omitting it draws exactly the batch this function
    drew before §4's controls existed, so M9's acceptance tests keep their meaning. Every draw
    below still comes from this respondent's own ``rng``, in a fixed order, so the batch stays
    deterministic in ``(seed, index, spec)``.
    """
    ref = ref or reference()
    spec = spec or GeneratorSpec(seed=seed)
    rng = random.Random(f"{seed}:{index}")
    keys = _keys_by_target()

    # A respondent-level disposition, so their answers hang together instead of being noise.
    # The preset moves its centre; the spread is how much respondents differ from each other.
    centre_shift = SENTIMENT_CENTRE[spec.sentiment]
    disposition = centre_shift + rng.uniform(-1.0, 1.0) * spec.disposition_spread
    disposition = max(-1.0, min(1.0, disposition))
    city = _weighted_choice(rng, spec.weighted("city"))
    service = _weighted_choice(rng, spec.weighted("service"))
    language = rng.choice(_LANGUAGES)
    fails_attention = rng.random() < spec.attention_fail_share
    multi_apping = rng.random() < spec.multi_app_share
    on_a_loan = rng.random() < spec.vehicle_loan_share

    # One target per construct for THIS respondent, on the dashboard's common 1-7 scale. Drawn
    # before the item loop because the holdout blocks need the respondent's EDEP to weight the
    # captive-voice interaction, and the answers are not written yet.
    targets = _respondent_targets(rng, spec, disposition)
    edep_position = max(0.0, min(1.0, (targets["EDEP"] - 1.0) / 6.0))

    answers: list[dict[str, Any]] = []

    def put(target: str, value: Any) -> None:
        key = keys.get(target)
        if key is None:
            raise GeneratorError(
                f"form_map.yaml has no question for {target!r}, so the generator cannot answer it. "
                "A partial submission is not quality-testable (docs/11 M9)."
            )
        section, _, title = key.partition("|")
        answers.append({"section": section, "title": title, "value": value})

    # Part 1 screeners: eligible by construction, so a synthetic row is usable.
    for screen in ("age_18_plus", "tenure_3_months", "active_30_days",
                   "reads_survey_language", "in_india"):
        put(f"screen:{screen}", "Yes")
    for screen in ("uber_employee", "earlier_stage", "deactivated"):
        put(f"screen:{screen}", "No")

    # Part 2 consent. Checkboxes answer as a LIST, exactly as the Form sends them.
    for n in range(1, 7):
        put(f"consent:statement_{n}", ["I agree"])
    put("consent:twin", ["I agree"])
    put("consent:participate", "Yes, I agree to take part")

    # Parts 3 and 4.
    put("field:city", city)
    put("field:service", service)
    # The dashboard sets months; the Form asks years. One conversion, and it round-trips (I16's
    # sibling property: the stored record and the record that was drawn must be the same record).
    put("field:tenure_years", years_from_months(rng.randint(*spec.tenure_months_range)))
    put("field:hours_per_week", str(rng.randint(*spec.hours_per_week_range)))
    put("field:age", str(rng.randint(*spec.age_range)))
    # `woman_share` is a share of the batch, so it is drawn before the fallback choice rather
    # than being one option among three: at 0.0 this reproduces the old uniform draw exactly.
    if spec.woman_share > 0 and rng.random() < spec.woman_share:
        put("field:gender", "Woman")
    else:
        put("field:gender", rng.choice(_GENDERS))
    put("meta:language", language)
    # `docs/06` §4's *use other apps too*. The count and the named apps are drawn from ONE
    # decision: a driver who reports one platform and then names two others is a contradiction a
    # real submission could not contain, and the old independent draws produced it routinely.
    if multi_apping:
        put("background:platform_count", str(rng.randint(2, 3)))
        put("background:other_apps", rng.choice(("Ola", "Rapido", "Ola and Rapido")))
    else:
        put("background:platform_count", "1")
        put("background:other_apps", "None")
    # §4's *car or bike on a loan*. The rest split between owning outright and renting.
    if on_a_loan:
        put("background:vehicle_arrangement", "Own with a loan")
    else:
        put(
            "background:vehicle_arrangement",
            rng.choice(("Own outright", "Rent from a fleet owner")),
        )
    put("background:dependants", str(rng.randint(0, 6)))
    put("background:other_household_income", rng.choice(_HOUSEHOLD))
    put("background:education", rng.choice(_EDUCATION))
    put("background:years_driving_before_uber", str(rng.randint(0, 12)))

    # Every register item, including the holdouts, on its own scale.
    attention = _attention_answers(ref)
    for item_id in sorted(ref.items):
        item = ref.items[item_id]
        if item_id in attention:
            correct = attention[item_id]
            if not fails_attention:
                put(item_id, str(correct))
                continue
            # A deliberate miss: the next point up, wrapping at the top of the item's own scale.
            # Never a clamp or a repair — this is generation, and the answer is meant to be wrong.
            points = ref.scale_points(item_id) or 5
            put(item_id, str(correct % points + 1))
            continue
        points = ref.scale_points(item_id) if item.scale_id else None
        if points is None:
            continue
        target = _item_target(
            item, ref,
            targets=targets, spec=spec, arm=arm, edep_position=edep_position,
        )
        centre = centre_for_points(target, points)
        # A reverse-coded item asks the opposite question, so its answer is the mirror. Drawing
        # it forward -- which is what every batch before `v3` did -- makes `SAT2` ("In general, I
        # don't like my job") RISE with satisfaction, so the SAT block contradicts itself and the
        # construct's reliability is destroyed before any analysis runs. `reverse_coded` is on the
        # frozen register; this reads it rather than re-deciding it.
        if item.reverse_coded:
            centre = points + 1 - centre
        put(item_id, str(_likert(rng, points, centre, spec.likert_sd)))

    # Open text.
    for probe in ("WHY_CONTROL", "WHY_SATISFACTION", "WHY_OTHER_WORK"):
        put(f"why:{probe}", rng.choice(_WHY_TEXTS))
    for n, text in enumerate(_OWN_WORDS, start=1):
        put(f"own_words:OWN{n}", text)

    # Part 15: the manipulation check, answered against the assigned arm most of the time, so
    # `mc_correct` is neither always true nor always false.
    put("check:manipulation", arm if rng.random() < spec.mc_correct_rate else "No change")

    return {
        "response_id": f"{SYNTHETIC_PREFIX}-{seed:d}-{index:04d}",
        "submitted_at": "2026-09-29T00:00:00.000Z",
        "completion_seconds": rng.randint(*spec.completion_seconds_range),
        "answers": answers,
    }


def _preset_target(spec: GeneratorSpec) -> float:
    """The 1–7 target a construct takes when `docs/06` §4's slider for it says nothing.

    The three presets are the dashboard's starting points, and in §4 pressing one *fills the
    sliders*. So a spec that carries explicit targets does not consult the preset at all, and one
    that carries none falls back to it rather than to a bare midpoint.
    """
    return 4.0 + SENTIMENT_CENTRE[spec.sentiment] * 2.0


def _respondent_targets(
    rng: random.Random, spec: GeneratorSpec, disposition: float
) -> dict[str, float]:
    """This respondent's target for every construct, on the dashboard's common 1–7 scale.

    Three of `docs/06` §4's controls meet here:

    * **the per-construct sliders** set each construct's batch mean;
    * **how much drivers differ** (``disposition_spread``) is already inside ``disposition``, and
      is how far this respondent sits from that mean;
    * **shared overall mood** splits that distance between one disposition the respondent carries
      across every construct and a per-construct wobble. At 1.0 a respondent is uniformly sour or
      uniformly content; at 0.0 each construct is independent and **no correlation between
      constructs survives**, which would make the batch useless for PLS-SEM — hence the high
      default rather than a midpoint.

    Constructs are read in sorted order so the batch stays deterministic in ``(seed, index,
    spec)``: a dict iterated in insertion order would make the draw depend on how the spec was
    built.
    """
    from twinlab.models.reference import CONSTRUCTS

    #: The full width, in scale points, that a respondent at the extreme sits from the mean.
    swing = 1.5
    out: dict[str, float] = {}
    for construct in sorted(CONSTRUCTS, key=lambda c: c.code):
        # EDEP is the moderator and has its own dashboard control, in its own words.
        base = spec.construct_targets.get(
            construct.code,
            spec.need_money if construct.code == "EDEP" else _preset_target(spec),
        )
        wobble = rng.uniform(-1.0, 1.0)
        shared = spec.shared_mood * disposition + (1.0 - spec.shared_mood) * wobble
        out[construct.code] = max(1.0, min(7.0, base + swing * shared))
    return out


#: `H3_V{n}_{FAIR,PUSH,KEEP}` → the construct whose baseline the question re-asks, and the sign
#: with which more protection moves it. `docs/01` §3.6: Part 17 asks three questions about each of
#: six real version codes, and they are the fairness, pushback and staying questions.
_H3_SUFFIX: dict[str, tuple[str, int]] = {
    "FAIR": ("FAIR", 1),
    "PUSH": ("VOIC", -1),
    "KEEP": ("LOYA", 1),
}


def _item_target(
    item: Any,
    ref: ReferenceData,
    *,
    targets: dict[str, float],
    spec: GeneratorSpec,
    arm: str,
    edep_position: float,
) -> float:
    """The 1–7 target for one item: the baseline, moved when the item asks about a change.

    Three cases, and **the two holdout blocks are the whole point of `docs/06` §4's reaction
    sliders**:

    * a battery or trait item asks about Uber as it is, so it takes the baseline unmoved;
    * an `H2_*` item (Part 16) asks the same question again *imagining the respondent's assigned
      arm is true*, so it moves by that arm's version code;
    * an `H3_V{n}_*` item (Part 17) asks about one of six real version codes, so it moves by that
      code — six different amounts within one respondent, which is what makes H3 a fidelity gate
      rather than a repeat of H2.

    Before `v3` all three cases drew from the same baseline, so a synthetic respondent answered
    Part 17 **identically for all six versions up to noise**. A twin scored against that human
    could not fail the gate for the right reason, and the reaction sliders had nothing to bind to.

    The construct of an `H2_*` item is reached through ``mirrors``; `docs/01` §6.1 declares
    ``construct_code`` null on a holdout row on purpose, so a query for `FAIR` cannot pool Part 7
    with Part 16, and this reads the link rather than re-deriving it.
    """
    if item.role == "holdout_h2":
        if not item.mirrors:
            raise GeneratorError(
                f"{item.item_id} is an H2 holdout with no `mirrors`, so the construct whose "
                "baseline it re-asks cannot be found (docs/01 §3.1). A guessed construct would "
                "move the wrong block."
            )
        construct = construct_code_for(ref.items[item.mirrors])
        if construct is None:
            raise GeneratorError(f"{item.mirrors} has no construct; {item.item_id} cannot move")
        sign = ref.constructs[construct].index_sign or 1
        version_code = _arm_version_code(ref, arm)
    elif item.role == "holdout_h3":
        suffix = item.item_id.rsplit("_", 1)[-1]
        try:
            construct, sign = _H3_SUFFIX[suffix]
        except KeyError:
            raise GeneratorError(
                f"{item.item_id} is an H3 holdout ending {suffix!r}, which is not one of "
                f"{sorted(_H3_SUFFIX)}. The register was renumbered (CLAUDE.md rule 8)."
            ) from None
        if not item.version_code:
            raise GeneratorError(
                f"{item.item_id} carries no `version_code`; Part 17's six scenarios are real "
                "version codes (docs/01 §3.6) and an unlabelled one cannot be answered."
            )
        version_code = item.version_code
    else:
        construct = construct_code_for(item)
        if construct is None:
            # An item with no construct and no holdout role takes the midpoint. Nothing in the
            # frozen register is in this case today; it is not an error if one is added.
            return 4.0
        return targets[construct]

    shift = reaction_shift(version_code, spec, economic_dependence=edep_position)
    return max(1.0, min(7.0, targets[construct] + sign * shift))


def _arm_version_code(ref: ReferenceData, arm: str) -> str:
    """The version code of the arm a respondent was assigned. `docs/01` §5.2.

    An empty arm is the first of :func:`generate_batch`'s two passes — arms are assigned from the
    strata the first pass draws, so there is no arm yet. The control code is correct there and the
    row is redrawn with the real arm before anything is stored. An arm that is not in the frozen
    reference raises rather than falling back to the control, because that would silently record a
    respondent as having seen no change.
    """
    if not arm:
        return "00000"
    try:
        return ref.arms[arm].version_code
    except KeyError:
        raise GeneratorError(
            f"arm {arm!r} is not in the reference data; have {sorted(ref.arms)}"
        ) from None


def _attention_answers(ref: ReferenceData) -> dict[str, int]:
    """The correct answer to each attention check, read from its own stem."""
    from twinlab.ingest.survey_intake import _attention_expectations

    return _attention_expectations(ref)


def assign_arms(
    n: int, *, seed: int, strata: list[str], ref: ReferenceData | None = None
) -> list[str]:
    """Arms, balanced within stratum. `docs/01` §5.2.

    Round-robin over a seeded shuffle of the arm list per stratum, so each stratum gets an even
    split rather than an even split overall — which is what "balanced within `city|service`"
    means, and what makes H2 validation comparable across strata.
    """
    ref = ref or reference()
    arm_ids = sorted(ref.arms)
    if not arm_ids:
        raise GeneratorError("no arms in the reference data")
    rng = random.Random(seed)
    counters: dict[str, list[str]] = {}
    out: list[str] = []
    for i in range(n):
        stratum = strata[i]
        queue = counters.get(stratum)
        if not queue:
            queue = arm_ids.copy()
            rng.shuffle(queue)
            counters[stratum] = queue
        out.append(queue.pop(0))
    return out


def spec_from_config(seed: int, **overrides: Any) -> GeneratorSpec:
    """A :class:`GeneratorSpec` seeded from `config/generator.default.yaml`.

    The config file has always been written into every batch's stored `config` as provenance,
    but **none of its values were ever read** — `likert_sd`, `mc_correct_rate` and the
    completion-second bounds were hard-coded literals that happened to match. A batch therefore
    recorded a configuration that did not describe it. The file is the source now, so the record
    and the batch agree.
    """
    config = generator_config()
    fields: dict[str, Any] = {"seed": seed}
    if "default_count" in config:
        fields["count"] = int(config["default_count"])
    for key in (
        "likert_sd", "attention_fail_share", "shared_mood", "disposition_spread",
        "mc_correct_rate", "need_money", "multi_app_share", "vehicle_loan_share",
        "woman_share",
    ):
        if key in config:
            fields[key] = float(config[key])
    if "captive_voice" in config:
        fields["captive_voice"] = bool(config["captive_voice"])
    if "lever_reactions" in config:
        fields["lever_reactions"] = {
            str(k): float(v) for k, v in dict(config["lever_reactions"]).items()
        }
    low, high = config.get("completion_seconds_min"), config.get("completion_seconds_max")
    if low is not None and high is not None:
        fields["completion_seconds_range"] = (int(low), int(high))
    return GeneratorSpec(**{**fields, **overrides})


def generate_batch(
    *,
    seed: int,
    count: int,
    name: str = "synthetic batch",
    batch_id: str | None = None,
    ref: ReferenceData | None = None,
    spec: GeneratorSpec | None = None,
) -> dict[str, Any]:
    """A whole batch, as rows ready to insert. Deterministic in ``(seed, count, spec)``.

    Returns ``{"batch": …, "submissions": [...], "answers": [...], "payloads": [...]}``. The
    payloads are carried so the caller can write each raw object to Storage **before** its rows,
    exactly as live intake does (I16) — a synthetic row with no replayable object would be a
    different kind of record from a real one.

    ``seed`` and ``count`` stay explicit parameters rather than being read off ``spec``, because
    every existing caller passes them and a batch whose size disagreed with its own spec would
    be the sort of quiet mismatch this module exists to avoid. When both are given, ``spec`` is
    reconciled to them.
    """
    ref = ref or reference()
    if count < 1:
        raise GeneratorError(f"count must be at least 1, got {count}")
    spec = (spec or GeneratorSpec(seed=seed)).model_copy(
        update={"seed": seed, "count": count, "name": name}
    )

    # Strata are drawn first so arms can be balanced within them.
    payloads: list[dict[str, Any]] = []
    for index in range(count):
        payloads.append(synthetic_payload(seed=seed, index=index, arm="", ref=ref, spec=spec))

    strata = [_stratum_of(p) for p in payloads]
    arms = assign_arms(count, seed=seed, strata=strata, ref=ref)

    submissions: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    for index, (payload, arm) in enumerate(zip(payloads, arms, strict=True)):
        # Re-drawn with the arm, so the manipulation check can be scored against it.
        payload = synthetic_payload(seed=seed, index=index, arm=arm, ref=ref, spec=spec)
        payloads[index] = payload
        rows = build_rows(
            payload,
            raw_object_path=raw_object_path(payload["response_id"]),
            data_type=SYNTHETIC_DATA_TYPE,
            batch_id=batch_id,
            arm=arm,
            arm_source="generator",
            ref=ref,
        )
        submissions.append(rows["submission"])
        answers.extend(rows["answers"])

    return {
        "batch": {
            "name": name,
            "seed": seed,
            "requested": count,
            "created_n": len(submissions),
            "rejected_n": 0,
            # The spec is recorded beside the config file, because the spec is what actually
            # produced the batch: a UI run overrides the file's defaults, and reproducing the
            # batch later needs the values used, not the ones on disk.
            "config": {
                "generator_version": GENERATOR_VERSION,
                "generator": generator_config(),
                "spec": spec.model_dump(mode="json"),
                "form_map_version": rows["extras"]["form_map_version"],
            },
        },
        "submissions": submissions,
        "answers": answers,
        "payloads": payloads,
    }


def _stratum_of(payload: dict) -> str:
    """`'Mumbai|Cab (Uber Go or Premier)'` from a payload, without touching the database."""
    keys = _keys_by_target()
    city_key = keys["field:city"]
    service_key = keys["field:service"]
    found: dict[str, str] = {}
    for answer in payload["answers"]:
        key = f"{answer['section']}|{answer['title']}"
        if key == city_key:
            found["city"] = str(answer["value"])
        elif key == service_key:
            found["service"] = str(answer["value"])
    return f"{found.get('city', 'unknown')}|{found.get('service', 'unknown')}"


def delete_synthetic_filters() -> list[tuple[str, str, Any]]:
    """The **only** filter delete-synthetic may use. `docs/11` M9.

    Keyed on `data_type` alone, so it can never reach a real row. The cascade to `survey_answers`
    and `twins` is the DDL's (`on delete cascade`), and **no run is touched**: a `runs` row
    references a session and a variant, never a submission, so deleting synthetic surveys cannot
    remove evidence.
    """
    return [("eq", "data_type", SYNTHETIC_DATA_TYPE)]
