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
from twinlab.generator.voice import (
    SALIENCE_BY_LEVER,
    VOICE_VERSION,
    band_of,
    band_of_target,
    compose_own_words,
    compose_why,
    draw_voice,
    facts_of,
    salience_tag,
)
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.ingest.survey_intake import build_rows, form_map, raw_object_path
from twinlab.models.reference import (
    CONSTRUCTS,
    LEVER_BY_POSITION,
    construct_code_for,
)
from twinlab.models.view import (
    GENERATOR_CITIES,
    GENERATOR_SERVICES,
    GeneratorSpec,
    ReactionGainFit,
    ReactionModelFit,
)

#: `docs/06` §4's three presets, as a shift of the respondent-level disposition in units of the
#: disposition's own range. "Mixed" is the midpoint, which is what the generator always drew.
SENTIMENT_CENTRE: dict[str, float] = {
    "frustrated": -0.55,
    "mixed": 0.0,
    "content": 0.55,
}

#: Which construct each Part 14 prompt is banded on (`v6`). The prompt text is in
#: `persona/templates.OWN_WORDS_PROMPTS` and each of these is the construct that prompt asks
#: about — not one shared disposition, which is what made all five answers interchangeable.
#:
#: `OWN5` ("who depends on my earnings, and where I see myself in a year or two") earns the most:
#: banded on `EXIT`, a respondent who wants out says something structurally different from one
#: who means to stay, and those are precisely the H2 answers a wrong-person comparison scores the
#: twin against.
OWN_WORDS_CONSTRUCT: dict[str, str] = {
    "OWN1": "SATI",  # my least difficult day — happiness
    "OWN2": "TRAN",  # how the app decides pay and who gets it — clarity
    "OWN3": "FAIR",  # needing help, or being blocked — fairness
    "OWN4": "VOIC",  # what drivers and I do about a problem — pushback
    "OWN5": "EXIT",  # who depends on me, and the next year or two — leaving
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
#:
#: `v4` answers all 37 why-probes rather than the three the instrument began with
#: (`SURVEY_SCALES_AND_WHY_PROBES.md` §3.1, applied 2026-10-08). That is 34 further draws from
#: the same generator, so **a `v3` seed does not reproduce under `v4`** either.
#:
#: `v5` gives each lever its own construct effects (`GeneratorSpec.lever_effects`), a diminishing
#: second dial step and the two lever interactions, all ported from the Apps Script prototype
#: (`docs/AUDIT_PROTOTYPE_PARITY.md` §A6, 2026-10-11). `v4` moved every construct by one shared
#: scalar, so every interaction was exactly additive by construction and no lever was
#: distinguishable from another by its effects. The draw order is unchanged — the matrix consumes
#: no randomness — but **every holdout answer moves**, so a `v4` seed does not reproduce under
#: `v5`.
#:
#: `v6` makes a synthetic respondent an individual (2026-10-11). Three changes, and every one of
#: them moves answers:
#:
#: * **`between_driver_swing` replaces a hard-coded `1.5`**, default `2.4`. At `1.5` a construct
#:   target had a between-driver SD of ~0.62 points, so after `centre_for_points` four respondents
#:   in five answered a 5-point item with the *same integer* and the whole panel rendered
#:   near-identical persona clauses. No draw order changes, but every battery answer moves.
#: * **The 37 why-probes are composed, not sampled** — `generator/voice.py`, keyed on the item's
#:   own block and on the band of the answer just drawn, plus a clause from the respondent's own
#:   record. Before this they came from a flat four-string tuple with no reference to the item or
#:   the value, so a respondent who had just strongly agreed the app controls them had a one in
#:   four chance of explaining it with "sometimes it feels fair and sometimes it does not".
#: * **Part 14 is composed too.** It had **no RNG call at all**: `_OWN_WORDS` was a fixed
#:   five-tuple, so the passage's longest and most attributable block was byte-identical for
#:   every respondent in every batch at every seed.
#:
#: The voice is drawn between the background block and the battery loop, and each free-text answer
#: now consumes several values rather than one, so **a `v5` seed does not reproduce under `v6`**.
#:
#: `v7` corrects the construct Part 17's *staying* question reads (2026-10-12). `H3_V{n}_KEEP`
#: asks *"how likely would you be to keep driving with Uber?"* and was answered from `LOYA`
#: (*"I hope this job carries on"*). Hope is not likelihood, and for a driver with dependants, a
#: financed vehicle and no other household income the two point **opposite ways** — so the
#: generator was describing its most economically captive respondents as the ones about to leave,
#: inverting the moderation `EDEP` exists to carry. `KEEP` now reads `EXIT`, the behavioural
#: block, mirrored on the 1–7 scale. See :data:`_H3_MIRRORED`.
#:
#: The draw order is unchanged — the mapping consumes no randomness — but **every `KEEP` holdout
#: answer moves**, so a `v6` seed does not reproduce under `v7`. `v7` also adds
#: :func:`clipping_share`, which reads a spec and reports nothing about a drawn batch, so it
#: cannot affect reproduction either way.
#:
#: `v8` makes a respondent's **reaction** real and legible (2026-10-13). Two changes, and between
#: them they are why no synthetic twin could pass the H3 gate:
#:
#: * **`reaction_gain`, calibrated against a real respondent rather than typed.** `lever_effects`
#:   asserts how far a described change moves a driver and that assertion had never been checked
#:   against one. At the inherited gain the matrix predicted the single real respondent on record
#:   at MAE 1.504 — it could not reproduce a real person. Fitted gain `2.11`, corroborated by the
#:   H2 block with no method confound (0.375 scale points moved per mirrored item against a
#:   predicted 0.112). Fitted to **survey answers, never to twin output**; see
#:   :func:`calibrate_reaction_gain`. No draw changes, but every holdout answer moves.
#: * **`reactivity_spread`, so respondents differ in how far they move — and say so.** The shift
#:   was a batch constant: across the whole range of `EDEP`, its only respondent-level input, the
#:   fairness shift varied by at most 0.16 points and by exactly 0.00 on four of the six Part 17
#:   versions. Nothing in any persona said how reactive its respondent was, so a twin was asked
#:   for a hidden constant it had never been given and could only pass by guessing it. Reactivity
#:   is now drawn per respondent and spoken in their persona through `voice`'s `react:*` clauses.
#:
#: The reactivity draw sits between the background block and the construct targets, so **a `v7`
#: seed does not reproduce under `v8`**. `VOICE_VERSION` goes to `v2` for the new clauses.
#:
#: `v9` makes the reactivity clause **legible** rather than merely present (2026-10-13). `v8` put
#: it in one of eight circumstance slots, so it surfaced one to three times in a 1,700–2,450 word
#: passage — once at 93% of the way through. Directed to find it by `twin_h3_v3.md`, the twin
#: started varying per driver but tracked the real reactivity at only r +0.20 against a +0.59
#: ceiling while overshooting its drivers' spread by 90%: hunting a signal it could not locate.
#: Reactivity now holds three of ten slots and each band carries five phrasings rather than
#: three. `facts_of` returns a longer tuple, so `fact_offset` draws from a different range and
#: **a `v8` seed does not reproduce under `v9`**. `VOICE_VERSION` goes to `v3`.
#:
#: `v10` removes the **last hidden batch constant** (2026-10-13). `GeneratorSpec.lever_reactions`
#: carried `{L1: 2.0, L2..L5: 1.0}` — pay double-weighted for every respondent in the batch, and
#: disclosed in no persona. Same defect class as `reaction_gain` before it was calibrated and as
#: the reaction before it was drawn per respondent: a quantity the gate scored twins on and no
#: twin had been given. It was the binding obstacle. Across stages 1–3 every other targeted
#: metric moved and `r(driver version means, twin version means)` stayed at +0.09 → +0.07: the
#: twin had learnt to tell the six Part 17 versions apart and ranked them **wrong**, putting
#: `02211` — which raises no pay at all — second where its driver put it fifth.
#:
#: Each respondent now draws their own salience per lever (:func:`respondent_lever_weights`) and
#: **says which lever matters most** through `voice`'s `salience:*` clauses. The draw is
#: multiplicative and centred on `lever_reactions`, so the batch's mean salience on every lever is
#: unchanged: this admits that drivers differ, it does not re-weight the population, and
#: re-tuning those means against a twin pass rate would be the circularity `docs/08` §2.4
#: forbids. Not calibrated, because it cannot be at n=1 — five weights plus a gain is six
#: parameters against one respondent's eighteen Part 17 answers.
#:
#: The salience draw sits with the other respondent-level draws, before the construct targets, so
#: **a `v9` seed does not reproduce under `v10`**. `VOICE_VERSION` goes to `v4` for the new
#: clauses.
#:
#: `v11` fixes **what `v10` got wrong about which axis to grow** (2026-10-13). The diagnosis that
#: followed the `v10` gate run found that the twins were not failing on the persona at all — on
#: the control cells they reproduce their driver's 37 battery answers to **0.18** of a scale
#: point — but on one axis only: the twin gives nearly the same answer to all six Part 17
#: versions, and the generator made its drivers differentiate those versions sharply. The one
#: real respondent on record **does not differentiate them either**: a range of exactly one scale
#: point across six described worlds, while moving 2.47 points from their own baseline. A
#: version-blind twin scores 0.50 against that driver and 1.01 against a synthetic one, which is
#: the whole of the one pass and the ten failures.
#:
#: So `v10` had amplified exactly the wrong thing — per-respondent lever salience widened the
#: between-version spread (0.475 to 0.604) and moved the synthetic driver further from the only
#: real behaviour on record, which is why its version correlation went +0.07 to −0.08.
#:
#: `GeneratorSpec.holdout_version_differentiation` shrinks the between-version spread of the
#: HOLDOUT ANSWERS toward
#: :func:`mean_shift`, and it is **calibrated against the real respondent's own Part 17 answers**
#: by :func:`calibrate_reaction_model` — never against a twin's output or a pass rate. The joint
#: fit is gain `2.40`, differentiation `0.18`, and it **halves the error on those answers, 0.863
#: to 0.392**: the generator can now reproduce a real driver well inside the gate's own cap.
#:
#: The shrinkage consumes no randomness, so the draw order is unchanged — but **every holdout
#: answer moves**, so a `v10` seed does not reproduce under `v11`. `VOICE_VERSION` stays at `v4`:
#: no bank changed.
#:
#: `v12` stops the generator putting respondents on the ends of the scale (2026-10-14). `_likert`
#: **clamped** a rounded normal draw, so every respondent whose latent position sat past an end
#: landed exactly on it: the ends carried a pile-up the clamp itself created, 14-19% of
#: seven-point answers. Under-using the outermost options is a documented property of Likert
#: response, and the one real respondent on record used an endpoint **0 times in 39 seven-point
#: answers** - 21 battery and 18 Part 17. The generator was asserting a response style no human in
#: the data exhibits, and the endpoints are where a twin's error concentrates.
#:
#: `GeneratorSpec.endpoint_avoidance` is `0.70`, the smallest value that brings endpoint use inside
#: what 0 of 39 supports (5% on the battery, 7% on Part 17, against a 95% upper bound of about
#: 9%). Chosen against that stated criterion and **not** against a twin pass rate, which is
#: `docs/08` §2.4's circularity; 93% of Part 17 answers now fall in 2-6, against 78% before.
#:
#: Applied to every Likert answer the respondent gives, battery and both holdout blocks, because a
#: response style is a property of the person: someone who avoids the ends when describing today
#: does not stop avoiding them when imagining a change.
#:
#: `_likert` draws one extra uniform per item, so **a `v11` seed does not reproduce under `v12`**.
#: `VOICE_VERSION` stays at `v4`; no bank changed.
GENERATOR_VERSION = "v12"
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


def respondent_lever_weights(
    rng: random.Random, spec: GeneratorSpec
) -> dict[str, float]:
    """This respondent's own salience per lever. `v10`.

    :attr:`GeneratorSpec.lever_reactions` is the **batch mean** for each lever; this spreads it
    per respondent so that *which* described change moves a driver is a property of the driver.
    Until `v10` it was a batch constant — pay double-weighted for everyone, stated in no persona —
    and it is why the twin ranked the six Part 17 versions in the wrong order while differentiating
    them correctly in magnitude (:data:`GENERATOR_VERSION`, `v10`).

    **Multiplicative and symmetric about the mean**, for three reasons that are each load-bearing:

    * the batch's mean salience on every lever is unchanged, so this adds between-driver variance
      without re-weighting the population — the same centring `reactivity_spread` uses, and what
      keeps the change non-circular;
    * a lever whose slider is at `0.0` stays at `0.0` for every respondent, so `docs/06` §4's
      no-reaction null stays null;
    * no weight can turn negative, which would invert that lever's sign for one respondent and
      make a pay rise lower their satisfaction.

    Drawn in the odometer's frozen order (I2) from the respondent's own RNG, so the batch stays
    deterministic in ``(seed, index, spec)``.
    """
    return {
        lever: spec.reaction(lever)
        * (1.0 + rng.uniform(-1.0, 1.0) * spec.salience_spread)
        for lever in LEVER_BY_POSITION
    }


#: Every dial a lever can carry, and how many codes there are. `dials_of_code` reads a five-digit
#: string over ``{0, 1, 2}``, so the odometer is 3**5 (I2).
_DIALS: tuple[int, ...] = (0, 1, 2)
_CODES_N: int = len(_DIALS) ** len(LEVER_BY_POSITION)


def mean_shift(
    spec: GeneratorSpec,
    *,
    economic_dependence: float,
    reactivity: float = 1.0,
    lever_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """The mean of :func:`reaction_shift` over **every code that raises something**. `v11`.

    This is what :attr:`GeneratorSpec.holdout_version_differentiation` shrinks towards, and
    the reason it
    can: the mean is a property of the spec and of this respondent, **not** of whichever code is
    being asked about. So the parameter means the same thing for Part 16's arm codes, Part 17's
    six and the sweep's 243, and the mean shift over the code space is preserved exactly at every
    value of it — which is what keeps the shrinkage close to orthogonal to `reaction_gain`.

    `00000` is **excluded**, not averaged in: being shown nothing moves nobody, and that is an
    invariant rather than a value this mean should dilute.

    Computed in closed form rather than by enumerating 243 codes, because `reaction_shift` is
    called once per holdout item per respondent. Over all codes each lever's dial is uniform on
    ``{0, 1, 2}``, so a lever contributes ``(1 + second_step_factor) / 3`` steps on average and is
    raised with probability ``2/3``; the two synergy terms need both their levers raised, which is
    ``4/9``. Dropping the all-zero code rescales by ``243 / 242``, since that code contributes
    nothing to either sum. :func:`_mean_shift_by_enumeration` is the brute-force equivalent and
    the test asserts they agree.
    """
    steps_mean = (1.0 + spec.second_step_factor) / len(_DIALS)
    raised = 2.0 / 3.0
    both_raised = raised * raised

    shift: dict[str, float] = {c.code: 0.0 for c in CONSTRUCTS}
    for lever in LEVER_BY_POSITION:
        weight = _weight_of(lever, spec, lever_weights, economic_dependence)
        for construct, per_step in spec.effects(lever).items():
            shift[construct] += per_step * steps_mean * weight
    if spec.lever_synergy:
        shift["VOIC"] -= spec.lever_synergy * both_raised
        shift["LOYA"] -= spec.lever_synergy / 2.0 * both_raised

    # The all-zero code contributes zero to every term above, so excluding it is one rescale.
    scale = spec.reaction_gain * reactivity * _CODES_N / (_CODES_N - 1)
    return {construct: value * scale for construct, value in shift.items()}


def _mean_shift_by_enumeration(
    spec: GeneratorSpec,
    *,
    economic_dependence: float,
    reactivity: float = 1.0,
    lever_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """:func:`mean_shift` the slow way, over all 242 raising codes. **Tests only.**

    Kept beside the closed form it checks: the closed form is four lines of probability and a
    wrong constant in it would bias every holdout answer in a way no other test would catch.
    Calls :func:`reaction_shift` with the shrinkage off, which is what the mean is the mean of.
    """
    flat = spec.model_copy(update={"holdout_version_differentiation": 1.0})
    totals: dict[str, float] = {c.code: 0.0 for c in CONSTRUCTS}
    n = 0
    for code_n in range(_CODES_N):
        digits = []
        rest = code_n
        for _ in LEVER_BY_POSITION:
            digits.append(rest % len(_DIALS))
            rest //= len(_DIALS)
        code = "".join(str(d) for d in reversed(digits))
        if code == "0" * len(LEVER_BY_POSITION):
            continue
        n += 1
        one = reaction_shift(
            code,
            flat,
            economic_dependence=economic_dependence,
            reactivity=reactivity,
            lever_weights=lever_weights,
        )
        for construct, value in one.items():
            totals[construct] += value
    return {construct: value / n for construct, value in totals.items()}


def _weight_of(
    lever: str,
    spec: GeneratorSpec,
    lever_weights: dict[str, float] | None,
    economic_dependence: float,
) -> float:
    """One lever's weight in force: this respondent's drawn salience, or the batch mean. `v11`.

    Lifted out of :func:`reaction_shift` so that function and :func:`mean_shift` cannot disagree
    about which weight applies — the captive-voice multiplier in particular, which belongs to
    `docs/06` §4 and lands on `L5` only.
    """
    if lever_weights is None:
        weight = spec.reaction(lever)
    else:
        try:
            weight = lever_weights[lever]
        except KeyError:
            raise KeyError(
                f"no drawn salience weight for lever {lever!r}; all five are required "
                f"(docs/06 §4). Have: {sorted(lever_weights)}"
            ) from None
    if lever == "L5" and spec.captive_voice:
        # A multiplier in [1.0, 2.0]: at EDEP 1.0 the forum lands twice as hard.
        weight *= 1.0 + max(0.0, min(1.0, economic_dependence))
    return weight


def reaction_shift(
    version_code: str,
    spec: GeneratorSpec,
    *,
    economic_dependence: float,
    reactivity: float = 1.0,
    lever_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """How far each construct moves under ``version_code``, in **signed** 1–7 scale points.

    This is what `docs/06` §4's *how strongly they react to each change* sliders **do**. Each
    raised lever contributes its own row of :attr:`GeneratorSpec.lever_effects` — which construct
    it moves and by how much per step — scaled by that lever's reaction weight.

    Signed, and the sign comes from the matrix. **Before `v5` this returned one scalar magnitude
    and the caller applied the construct's `index_sign`** to give it a direction
    (`docs/AUDIT_PROTOTYPE_PARITY.md` §A6). That made every lever move every construct by the same
    amount: a pay rise moved *clarity* exactly as much as *happiness*, so no path estimated on
    synthetic data corresponded to anything, and the lever sliders had nothing lever-specific to
    bind to. A construct absent from a lever's row does not move — conditions (L2) has no path to
    clarity, and that zero is a claim.

    Three things shape the result, all ported from the prototype:

    * **a diminishing second step** — :attr:`GeneratorSpec.second_step_factor`, `1.6` rather than
      `2.0`, because nothing-to-minimum-wage is a bigger change than minimum-to-living-wage;
    * **captive voice** — ``economic_dependence`` is the respondent's own EDEP position in
      ``[0, 1]`` and, with ``spec.captive_voice`` on, raises the **representation** lever's weight
      only: a driver who needs the money reacts more to a drivers' forum. §4's checkbox, and a
      property of the synthetic *respondent* — no twin, no model call, nothing reading a metric;
    * **two lever interactions** — :attr:`GeneratorSpec.lever_synergy`. These are what let a
      synthetic batch exhibit the sub-additivity `docs/07` §5 calls the study's contribution;
      without them every interaction is exactly additive by construction.

    ``lever_weights`` is **this respondent's own salience** per lever, from
    :func:`respondent_lever_weights`, and replaces the batch-level :meth:`GeneratorSpec.reaction`
    when given (`v10`). Omitting it falls back to the batch means, which is what
    :func:`calibrate_reaction_gain` wants: a real respondent's salience is unknown, so the fit is
    of the batch's gain against the batch's weighting and must not invent a per-person one. An
    incomplete dict raises rather than defaulting a missing lever to "normal" (`CLAUDE.md` rule 7),
    for the same reason :meth:`GeneratorSpec.reaction` does.
    """
    dials = dials_of_code(version_code)
    shift: dict[str, float] = {c.code: 0.0 for c in CONSTRUCTS}

    for lever, dial in dials.items():
        if not dial:
            continue
        # `captive_voice` multiplies whichever weight is in force — the batch mean or this
        # respondent's own. Shared with `mean_shift` so the two cannot disagree about it.
        weight = _weight_of(lever, spec, lever_weights, economic_dependence)
        # Dial 1 is one step; dial 2 is `second_step_factor` steps, not two.
        steps = 1.0 if dial == 1 else spec.second_step_factor
        for construct, per_step in spec.effects(lever).items():
            shift[construct] += per_step * steps * weight

    # The two interactions, applied once per version rather than per lever. Both are negative:
    # pushback falls further when appeals and a forum arrive together (somewhere to take a
    # complaint plus a body to take it to), and staying rises less when pay and safety arrive
    # together than the sum of the two alone (they substitute).
    if spec.lever_synergy:
        if dials["L4"] and dials["L5"]:
            shift["VOIC"] -= spec.lever_synergy
        if dials["L1"] and dials["L2"]:
            shift["LOYA"] -= spec.lever_synergy / 2.0

    # `v8`. The gain and this respondent's own reactivity scale the **finished** shift, after the
    # interactions, so sub-additivity is preserved as a proportion rather than being flattened:
    # scaling the per-lever contributions but not the synergy term would quietly change how
    # sub-additive the population is, which is `docs/07` §5's headline claim.
    #
    # One multiplier over every construct, so `lever_effects`' structure — which lever moves what,
    # in what proportion, with which sign — is untouched. Only the overall responsiveness moves,
    # and that is the part with an external check (`GeneratorSpec.reaction_gain`).
    scale = spec.reaction_gain * reactivity
    if scale != 1.0:
        shift = {construct: value * scale for construct, value in shift.items()}

    return shift


def _likert(
    rng: random.Random,
    points: int,
    centre: float,
    sd: float = 1.1,
    endpoint_avoidance: float = 0.0,
) -> int:
    """A plausible Likert answer: a rounded normal draw clamped to the scale.

    Clamping is correct here and forbidden elsewhere. This is **generation**, not repair: there is
    no respondent whose answer is being altered, and `docs/02` §5.3's ban on clamping is about
    coercing a
    *model's* output into validity, which would hide a real failure.

    ``endpoint_avoidance`` is `v12`, and it exists because the clamp above **creates** endpoint
    answers: every respondent whose latent position sits past an end lands exactly on it. Real
    respondents do the opposite — under-using the outermost options is a documented property of
    Likert data, and the one real respondent on record used an endpoint **0 times in 39
    seven-point answers** while the synthetic batch beside them used one 14–19% of the time. At
    `1.0` an endpoint answer is always moved one step inward; at `0.0` this is the inherited
    behaviour exactly.

    The uniform is drawn **unconditionally**, even when the answer is not at an end, so the number
    of values consumed per item does not depend on the answer. A conditional draw would make the
    RNG stream depend on the content of earlier answers, and every later answer in the payload
    would shift — reproducibility would still hold (`docs/09` §2) but a one-item change would
    cascade, which makes a batch impossible to reason about.
    """
    value = max(1, min(points, round(rng.gauss(centre, sd))))
    moves = rng.random() < endpoint_avoidance
    if moves and value == 1:
        return 2
    if moves and value == points:
        return points - 1
    return value


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
    # `v8`. How far an announced change moves THIS respondent, centred on 1.0 so the spread
    # widens the panel without moving the batch's mean reaction — `reaction_gain` is the only
    # thing that sets level. Drawn here, with the other respondent-level draws and before the
    # construct targets, so the draw order is fixed whatever the voice banks later contain.
    reactivity = 1.0 + rng.uniform(-1.0, 1.0) * spec.reactivity_spread
    # `v10`. WHICH announced change moves this respondent most, centred on the batch's
    # `lever_reactions` so the mean salience per lever is unchanged. Drawn here with the other
    # respondent-level values and before the construct targets, so the draw order is fixed
    # whatever the voice banks later contain.
    lever_weights = respondent_lever_weights(rng, spec)

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
    # Held in a local as well because the respondent's own voice reads their tenure (`v6`).
    tenure_months = rng.randint(*spec.tenure_months_range)
    put("field:tenure_years", years_from_months(tenure_months))
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
        vehicle_arrangement = "Own with a loan"
    else:
        vehicle_arrangement = rng.choice(("Own outright", "Rent from a fleet owner"))
    put("background:vehicle_arrangement", vehicle_arrangement)
    dependants = rng.randint(0, 6)
    put("background:dependants", str(dependants))
    put("background:other_household_income", rng.choice(_HOUSEHOLD))
    put("background:education", rng.choice(_EDUCATION))
    put("background:years_driving_before_uber", str(rng.randint(0, 12)))

    # This respondent's voice, drawn **once** and held for all 39 free-text answers (`v6`). Here
    # rather than beside the free text because it reads the background block above, and before
    # the battery loop so the draw order is fixed whatever the banks later contain.
    #
    # Passage-level consistency is the point: thirty-nine independently sampled sentences read as
    # a committee, and attribution to one person is exactly what `docs/08` §4 test 1 measures.
    voice = draw_voice(
        rng,
        facts=facts_of(
            city=city,
            service=service,
            tenure_months=tenure_months,
            dependants=dependants,
            vehicle_arrangement=vehicle_arrangement,
            multi_apping=multi_apping,
            edep_position=edep_position,
            reactivity=reactivity,
            lever_weights=lever_weights,
        ),
        incident_share=spec.incident_share,
    )

    # Every register item, including the holdouts, on its own scale.
    attention = _attention_answers(ref)
    #: The integer actually drawn for each item, so a why-probe can be banded on the answer it is
    #: explaining rather than on a disposition the respondent never showed on that item.
    drawn: dict[str, int] = {}
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
            reactivity=reactivity, lever_weights=lever_weights,
        )
        centre = centre_for_points(target, points)
        # A reverse-coded item asks the opposite question, so its answer is the mirror. Drawing
        # it forward -- which is what every batch before `v3` did -- makes `SAT2` ("In general, I
        # don't like my job") RISE with satisfaction, so the SAT block contradicts itself and the
        # construct's reliability is destroyed before any analysis runs. `reverse_coded` is on the
        # frozen register; this reads it rather than re-deciding it.
        if item.reverse_coded:
            centre = points + 1 - centre
        value = _likert(
            rng, points, centre, spec.likert_sd, spec.endpoint_avoidance
        )
        drawn[item_id] = value
        put(item_id, str(value))

    # Open text. **Every probe the register defines**, not the three the instrument began with:
    # a synthetic respondent who answered only three of 37 probes would build a persona with a
    # different shape from a real one, and the generator exists to exercise the real path.
    from twinlab.models.twin import OWN_WORDS_IDS, WHY_PROBE_ANCHOR, WHY_PROBE_IDS

    # Each why is banded on **the item it is anchored to**, reverse-coded items on their mirrored
    # position (`voice.band_of`), so the explanation cannot contradict the clause the persona
    # builder attaches it to. `enumerate` supplies the index that walks the respondent's facts, so
    # a block of eleven items does not lean on the same circumstance eleven times.
    # One set of draw-without-replacement queues for the whole respondent, so an eleven-item
    # block cycles through a cell before any of it repeats. A respondent's eleven PAC answers
    # mostly land in one band -- that is what having a disposition means -- and independent draws
    # from a three-variant cell put the same sentence in the block five times.
    queues: dict[str, list[str]] = {}
    for position, probe in enumerate(WHY_PROBE_IDS):
        anchor = WHY_PROBE_ANCHOR[probe]
        if anchor not in drawn:
            raise GeneratorError(
                f"{probe} is anchored to {anchor}, which this respondent did not answer, so its "
                "why cannot be banded on the rating it explains. A why written against an "
                "unanswered item would contradict the persona it lands in."
            )
        anchored = ref.items[anchor]
        band = band_of(
            drawn[anchor],
            ref.scale_points(anchor),
            reverse_coded=anchored.reverse_coded,
        )
        put(
            f"why:{probe}",
            compose_why(
                rng,
                voice,
                block=anchored.block,
                band=band,
                facts_index=position,
                queues=queues,
            ),
        )

    # Part 14, banded on the construct each prompt actually asks about rather than on one shared
    # mood — `OWN_WORDS_CONSTRUCT` records which, and why it is that one.
    for n, own_id in enumerate(OWN_WORDS_IDS):
        put(
            f"own_words:{own_id}",
            compose_own_words(
                rng,
                voice,
                own_id=own_id,
                band=band_of_target(targets[OWN_WORDS_CONSTRUCT[own_id]]),
                facts_index=n + 2,
                queues=queues,
            ),
        )

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
    #: A `GeneratorSpec` dial since `v6` — see `GeneratorSpec.between_driver_swing` for why a
    #: hard-coded `1.5` made the panel too uniform to be told apart.
    swing = spec.between_driver_swing
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


#: The gain scan's bounds and step. A scan rather than a closed form because the target is
#: **clamped** to the 1–7 scale, which makes the residual piecewise linear in the gain and the
#: normal equations wrong near either end. 801 points at 0.01 is exact to the step and costs
#: nothing at this sample size.
_GAIN_SCAN: tuple[float, float, float] = (0.0, 8.0, 0.01)


def calibrate_reaction_gain(
    humans: dict[str, dict[str, int]],
    *,
    ref: ReferenceData | None = None,
    spec: GeneratorSpec | None = None,
) -> ReactionGainFit:
    """Fit :attr:`GeneratorSpec.reaction_gain` to **real** Part 17 responses. `v8`, 2026-10-13.

    ``humans`` is ``submission_id -> {item_id: value}`` for real respondents, carrying both their
    battery answers (which give each construct's baseline) and their `H3_V{n}_*` answers (which
    say where that baseline actually went). One gain is fitted across all of them by least
    squares, exactly as `_item_target` would apply it.

    **Why this function exists rather than a constant.** `lever_effects` asserts how far a
    described change moves a driver, and that assertion had never been checked against a driver.
    At the inherited gain of `1.0` the matrix predicted the one real respondent on record at
    MAE 1.504 — the generator could not reproduce a real person and would have failed its own
    quality gate against them. The fit is the non-circular correction: its inputs are **survey
    answers**, never a twin's output. Tuning the gain until twins pass is the circularity
    `docs/08` §2.4 forbids, and nothing in this function can see a twin.

    Returns the fit with ``respondents_n`` on it, because a gain from one respondent and a gain
    from two hundred are not the same claim and the caller must be able to tell them apart.
    Raises rather than returning a gain of 1.0 when nothing is scorable: an unfitted gain reported
    as a fit is the same defect as I15's perfect score over zero items.
    """
    ref = ref or reference()
    spec = spec or GeneratorSpec(seed=0)
    # **At unit gain, whatever the caller's spec carries.** `reaction_shift` applies
    # `spec.reaction_gain` itself, so fitting against a spec already carrying a gain would return
    # the gain *on top of* it — a fit of 1.00 against a spec at 2.11 reads as "no correction
    # needed" while meaning "2.11 was right". The returned gain is absolute and goes straight into
    # `GeneratorSpec.reaction_gain`, so re-running the fit on an already-calibrated spec must give
    # the same answer rather than compounding. Reactivity is left at 1.0 for the same reason: the
    # fit is of the batch's gain, not of one respondent's own deviation from it.
    spec = spec.model_copy(update={"reaction_gain": 1.0})

    # (actual, baseline on 1-7, unit-gain shift) per scored item, pooled across respondents.
    observations: list[tuple[int, float, float]] = []
    scored_respondents = 0
    for answers in humans.values():
        baselines: dict[str, list[float]] = {}
        for item_id in ref.battery_item_ids:
            if item_id not in answers:
                continue
            construct = construct_code_for(ref.items[item_id])
            if construct is None:
                continue
            points = ref.scale_points(item_id)
            # Onto the dashboard's common 1-7 scale, which is what the shift is denominated in.
            position = (answers[item_id] - 1) / (points - 1)
            baselines.setdefault(construct, []).append(1.0 + position * 6.0)
        means = {c: sum(v) / len(v) for c, v in baselines.items()}
        if "EDEP" not in means:
            # The captive-voice multiplier reads EDEP. Without it this respondent's shift is not
            # the shift the generator would have applied, so they are not scored (never defaulted
            # to a midpoint — `CLAUDE.md` rule 5).
            continue
        edep = max(0.0, min(1.0, (means["EDEP"] - 1.0) / 6.0))
        before = len(observations)
        for item_id in ref.holdout_h3_item_ids:
            if item_id not in answers or not ref.items[item_id].version_code:
                continue
            suffix = item_id.rsplit("_", 1)[-1]
            construct = _H3_SUFFIX.get(suffix)
            if construct is None or construct not in means:
                continue
            shift = reaction_shift(
                str(ref.items[item_id].version_code), spec, economic_dependence=edep
            )[construct]
            baseline = means[construct]
            if _H3_MIRRORED[suffix]:
                # The question runs opposite to its construct, so both the baseline it starts
                # from and the direction it moves in are mirrored (see `_H3_MIRRORED`).
                baseline, shift = 8.0 - baseline, -shift
            observations.append((answers[item_id], baseline, shift))
        if len(observations) > before:
            scored_respondents += 1

    if not observations:
        raise GeneratorError(
            "no real respondent supplied both a construct baseline and a Part 17 answer, so "
            "there is nothing to fit the reaction gain to. A gain reported without a fit behind "
            "it is the defect I15 exists to prevent."
        )

    def mae_at(gain: float) -> float:
        return sum(
            abs(actual - max(1.0, min(7.0, baseline + gain * shift)))
            for actual, baseline, shift in observations
        ) / len(observations)

    def sse_at(gain: float) -> float:
        return sum(
            (actual - max(1.0, min(7.0, baseline + gain * shift))) ** 2
            for actual, baseline, shift in observations
        )

    low, high, step = _GAIN_SCAN
    steps = round((high - low) / step)
    best = min(range(steps + 1), key=lambda i: (sse_at(low + i * step), i))
    gain = round(low + best * step, 2)

    return ReactionGainFit(
        gain=gain,
        respondents_n=scored_respondents,
        items_n=len(observations),
        mae_at_gain=round(mae_at(gain), 3),
        mae_at_unit_gain=round(mae_at(1.0), 3),
        headline=(
            f"Gain {gain:.2f} from {scored_respondents} real respondent"
            f"{'' if scored_respondents == 1 else 's'} over {len(observations)} Part 17 items: "
            f"mean error {mae_at(gain):.3f} against {mae_at(1.0):.3f} at a gain of 1.00."
            + (
                " One respondent fixes the direction and the rough gain, not the second decimal."
                if scored_respondents < 2
                else ""
            )
        ),
    )


#: The grid `calibrate_reaction_model` scans for `holdout_version_differentiation`. `v11`.
#:
#: Coarse on purpose, at 0.01: the parameter is bounded in ``[0, 1]`` and fitted on one
#: respondent's eighteen answers, so a finer grid would be reporting precision the data does not
#: carry. The gain is solved in closed form at each point rather than scanned with it.
_DIFFERENTIATION_SCAN: tuple[float, float, float] = (0.0, 1.0, 0.01)


def calibrate_reaction_model(
    humans: dict[str, dict[str, int]],
    *,
    spec: GeneratorSpec | None = None,
    ref: ReferenceData | None = None,
) -> ReactionModelFit:
    """Fit `reaction_gain` **and** `holdout_version_differentiation` to real Part 17 answers. `v11`.

    :func:`calibrate_reaction_gain` fits the level a described change moves a driver to, and
    cannot see the defect the 2026-10-13 diagnosis found: a gain that matches the *average*
    movement still spread the six Part 17 codes four times more widely than the one real
    respondent did. The level was right and the shape was not, so the shape needs a parameter and
    the parameter needs the same external check the gain has.

    **Fitted to survey answers, never to a twin's output or to a pass rate.** That distinction is
    `docs/08` §2.4's and it is the whole licence for this function: a parameter chosen by watching
    twins pass would make every path estimated on synthetic data an artefact of what the model
    cannot do. Nothing here reads `twin_answers`, `twin_quality_runs` or a verdict.

    The fit is a scan over the differentiation with the gain solved **in closed form** at each
    point, which is exact rather than a nested search: the shrunk shift is linear in the gain
    (both the shift and the mean it shrinks toward scale with it), so for a fixed differentiation
    the least-squares gain is ``Σ(residual·shift) / Σ(shift²)`` over the unclamped predictions.
    The reported errors are computed on the clamped predictions, which is what the generator
    actually emits.

    Returns the respondents' own spread across the six version codes beside the generator's at
    the fit, because those two numbers are the thing this parameter reconciles and a reader should
    not have to take the fitted value on trust.

    Reactivity is held at 1.0 and the batch's own `lever_reactions` are used, for the same reason
    :func:`calibrate_reaction_gain` does: the fit is of the batch's parameters, and a real
    respondent's personal reactivity and salience are not observable (`CLAUDE.md` rule 5 — no
    imputation).
    """
    ref = ref or reference()
    spec = spec or GeneratorSpec(seed=0)
    # At unit gain and full differentiation, so the scan below sets both absolutely rather than
    # on top of whatever the caller's spec already carries — the trap `calibrate_reaction_gain`
    # documents and its idempotence test guards.
    base = spec.model_copy(update={"reaction_gain": 1.0, "holdout_version_differentiation": 1.0})

    # (actual, baseline, unit-gain shift, mean unit-gain shift, version_code) per scored item.
    obs: list[tuple[int, float, float, float, str]] = []
    scored_respondents = 0
    observed_by_code: dict[str, list[float]] = {}

    for answers in humans.values():
        baselines: dict[str, list[float]] = {}
        for item_id in ref.battery_item_ids:
            if item_id not in answers:
                continue
            construct = construct_code_for(ref.items[item_id])
            if construct is None:
                continue
            points = ref.scale_points(item_id)
            position = (answers[item_id] - 1) / (points - 1)
            baselines.setdefault(construct, []).append(1.0 + position * 6.0)
        means = {c: sum(v) / len(v) for c, v in baselines.items()}
        if "EDEP" not in means:
            continue
        edep = max(0.0, min(1.0, (means["EDEP"] - 1.0) / 6.0))
        mean_unit = mean_shift(base, economic_dependence=edep)
        before = len(obs)
        for item_id in ref.holdout_h3_item_ids:
            if item_id not in answers or not ref.items[item_id].version_code:
                continue
            suffix = item_id.rsplit("_", 1)[-1]
            construct = _H3_SUFFIX.get(suffix)
            if construct is None or construct not in means:
                continue
            code = str(ref.items[item_id].version_code)
            shift = reaction_shift(code, base, economic_dependence=edep)[construct]
            mean_c = mean_unit[construct]
            baseline = means[construct]
            if _H3_MIRRORED[suffix]:
                baseline, shift, mean_c = 8.0 - baseline, -shift, -mean_c
            obs.append((answers[item_id], baseline, shift, mean_c, code))
            observed_by_code.setdefault(code, []).append(float(answers[item_id]))
        if len(obs) > before:
            scored_respondents += 1

    if not obs:
        raise GeneratorError(
            "no real respondent supplied both a construct baseline and a Part 17 answer, so "
            "there is nothing to fit the reaction model to. A model reported without a fit "
            "behind it is the defect I15 exists to prevent."
        )

    def predict(gain: float, lam: float) -> list[float]:
        return [
            max(1.0, min(7.0, baseline + gain * (mean_c + lam * (shift - mean_c))))
            for _, baseline, shift, mean_c, _ in obs
        ]

    def gain_at(lam: float) -> float:
        """Least squares on the unclamped prediction, which is linear in the gain."""
        num = sum(
            (actual - baseline) * (mean_c + lam * (shift - mean_c))
            for actual, baseline, shift, mean_c, _ in obs
        )
        den = sum(
            (mean_c + lam * (shift - mean_c)) ** 2 for _, _, shift, mean_c, _ in obs
        )
        if den <= 0:
            return 0.0
        return max(0.0, min(8.0, num / den))

    def sse(gain: float, lam: float) -> float:
        return sum(
            (actual - p) ** 2 for (actual, *_), p in zip(obs, predict(gain, lam), strict=True)
        )

    def mae(gain: float, lam: float) -> float:
        return sum(
            abs(actual - p) for (actual, *_), p in zip(obs, predict(gain, lam), strict=True)
        ) / len(obs)

    low, high, step = _DIFFERENTIATION_SCAN
    steps = round((high - low) / step)
    candidates = [round(low + i * step, 2) for i in range(steps + 1)]
    best_lam = min(candidates, key=lambda lam: (sse(gain_at(lam), lam), lam))
    best_gain = round(gain_at(best_lam), 2)

    # The two spreads this parameter reconciles: across the six codes, pooled over respondents.
    def spread(values_by_code: dict[str, list[float]]) -> float:
        means_ = [
            sum(v) / len(v) for _, v in sorted(values_by_code.items()) if v
        ]
        if len(means_) < 2:
            return 0.0
        mu = sum(means_) / len(means_)
        return (sum((m - mu) ** 2 for m in means_) / len(means_)) ** 0.5

    fitted_by_code: dict[str, list[float]] = {}
    for (_, _, _, _, code), p in zip(obs, predict(best_gain, best_lam), strict=True):
        fitted_by_code.setdefault(code, []).append(p)

    full_gain = round(gain_at(1.0), 2)
    return ReactionModelFit(
        gain=best_gain,
        holdout_version_differentiation=best_lam,
        respondents_n=scored_respondents,
        items_n=len(obs),
        mae_at_fit=round(mae(best_gain, best_lam), 3),
        mae_at_full_differentiation=round(mae(full_gain, 1.0), 3),
        observed_version_spread=round(spread(observed_by_code), 3),
        fitted_version_spread=round(spread(fitted_by_code), 3),
        headline=(
            f"Gain {best_gain:.2f} and version differentiation {best_lam:.2f} from "
            f"{scored_respondents} real respondent"
            f"{'' if scored_respondents == 1 else 's'} over {len(obs)} Part 17 items: "
            f"mean error {mae(best_gain, best_lam):.3f} against "
            f"{mae(full_gain, 1.0):.3f} at full differentiation. Their own spread across the six "
            f"versions is {spread(observed_by_code):.3f}; the generator's at this fit is "
            f"{spread(fitted_by_code):.3f}."
            + (
                " One respondent fixes the direction and the rough size, not the second decimal."
                if scored_respondents < 2
                else ""
            )
        ),
    )


def clipping_share(spec: GeneratorSpec, *, samples: int = 4000) -> dict[str, float]:
    """Per construct, the share of a batch this spec would pin to **1.0 or 7.0**. `v7`.

    The clamp in :func:`_respondent_targets` is correct — a target off the scale is not a target —
    but it is **silent**, and silently it undoes the one thing `between_driver_swing` exists to
    do. A construct slider at 2.0 with the `frustrated` preset and swing `2.4` lands 38% of
    respondents on the exact floor: the panel's between-driver SD rises by a fifth while more than
    twice as many respondents become *identical at the wall*. The batch then looks individual on
    the dial and is not, and the first place that shows up is a wrong-person test with no ceiling
    (`docs/08` §4 test 1) — which is how the 2026-10-12 batch was diagnosed, after the twin calls
    were spent rather than before.

    Pure arithmetic over the spec, no model, no I/O, and its own RNG so it cannot disturb a
    batch's draw order. Surfaced in the Generator screen as a pre-flight warning: the researcher
    sees the number *before* spending the calls. It is a diagnostic and never a correction — a
    high share is a spec the researcher may well want, and nothing here changes a drawn value.

    **Baseline targets only, deliberately.** Extending it to the holdout answers was tried in
    `v8` and reverted: at a calibrated `reaction_gain` the shifts are large enough that nearly
    every respondent reaches an end of the scale on at least one of the six Part 17 versions, so
    the measure fired on the *default* spec (pushback 84%) and carried no information. That
    saturation is also not the same defect — a driver already very low on pushback who is shown a
    near-total package and lands at "not at all likely" is answering correctly, whereas a
    respondent pinned at baseline is one whose *persona* cannot distinguish them from the next
    respondent. This measures the second.
    """
    rng = random.Random(f"clip:{spec.seed}")
    hits: dict[str, int] = {c.code: 0 for c in CONSTRUCTS}
    centre_shift = SENTIMENT_CENTRE[spec.sentiment]
    for _ in range(samples):
        disposition = centre_shift + rng.uniform(-1.0, 1.0) * spec.disposition_spread
        disposition = max(-1.0, min(1.0, disposition))
        for code, target in _respondent_targets(rng, spec, disposition).items():
            if target <= 1.0 or target >= 7.0:
                hits[code] += 1
    return {code: n / samples for code, n in hits.items()}


def salience_mix(spec: GeneratorSpec, *, samples: int = 4000) -> dict[str, float]:
    """Per lever, the share of a batch that would **weight it highest**. `v10`.

    The pre-flight that :func:`clipping_share` is for the baseline, and it exists because the
    `v10` draw is honest about something a researcher needs to see. `salience_spread` is centred
    on :attr:`GeneratorSpec.lever_reactions`, so the batch's mean salience per lever is unchanged
    — that is what keeps Route A non-circular (`docs/08` §2.4). The consequence is that a batch
    whose mean weights pay at `2.0` against `1.0` for the rest **still weights pay highest for
    most of its respondents**: at the default spread of `0.5`, 84% of them, because `L1`'s draw
    spans `[1.0, 3.0]` and every other lever's spans `[0.5, 1.5]`.

    That is not a defect in the draw. It is the researcher's own weighting, now **stated in every
    persona** instead of being a constant no twin had been told — which is the defect `v10`
    repairs. But "every persona says pay" and "drivers differ in what matters to them" are
    different claims, and only the first is bought by spreading a `2.0` mean. Which of them a
    batch carries is visible here before any twin call is spent:

    * at `salience_spread` 0.0–0.3 the mix is **100% pay** — the clause is still a batch constant,
      disclosed rather than hidden, and no twin can discriminate drivers by it;
    * at 0.5 it is 84/4/4/4/4;
    * at 0.9 it is 62/10/10/10/9.

    Real rank variation needs either a wider spread or **flatter `lever_reactions`**, and
    flattening the means is a claim about the population that belongs to the researcher
    (`CLAUDE.md`, "when the spec is silent" — stop and ask). Nothing here changes a drawn value.

    The shares are shares **of the batch**, not of the respondents who had a lever that mattered:
    under `docs/06` §4's no-reaction null nobody does, and this reports five zeros rather than
    100% on whichever lever happened to come first.

    Pure arithmetic over the spec, no model, no I/O, and its own RNG so it cannot disturb a
    batch's draw order — the same contract as :func:`clipping_share`.
    """
    by_tag = {tag: lever for lever, tag in SALIENCE_BY_LEVER.items()}
    rng = random.Random(f"salience:{spec.seed}")
    hits: dict[str, int] = {lever: 0 for lever in LEVER_BY_POSITION}
    for _ in range(samples):
        tag = salience_tag(respondent_lever_weights(rng, spec))
        if tag is not None:
            hits[by_tag[tag]] += 1
    return {lever: n / samples for lever, n in hits.items()}


#: `H3_V{n}_{FAIR,PUSH,KEEP}` → the construct whose baseline the question re-asks. `docs/01` §3.6:
#: Part 17 asks three questions about each of six real version codes, and they are the fairness,
#: pushback and staying questions.
#:
#: **The sign left this mapping in `v5`** and lives in `GeneratorSpec.lever_effects` instead. It
#: used to be carried here as a second tuple element and multiplied into a direction-free
#: magnitude; now the matrix is signed, so a sign here as well would double-apply it and silently
#: invert pushback. The **direction of the question** is a separate thing and lives in
#: :data:`_H3_MIRRORED`.

#: ``True`` where the Part 17 question runs **opposite** to its construct, so the target is the
#: construct's mirror on the 1–7 scale rather than the construct itself.
#:
#: `KEEP` is the one case, and it is `v7`'s correction. *"How likely would you be to keep driving
#: with Uber?"* is a **behavioural intention**; `LOYA` — the block it used to read — is
#: *"I hope this job carries on in the future"*, which is **affective commitment**. Those two
#: diverge, and for this study's own population they diverge in *opposite directions*: a driver
#: with dependants, a vehicle on finance and no other household income does not hope the job
#: continues and is nevertheless extremely likely to keep driving. Reading likelihood off hope
#: made the generator describe the captive driver as about to leave — the exact relationship
#: `EDEP` is the moderator for (`stats/spec.py`), inverted inside the data meant to exercise it.
#:
#: `EXIT` is the behavioural block (*"I will probably look for a new job in the next year"*,
#: *"Actively looking for a new job in the next year is quite likely for me"*), so likelihood of
#: **staying** is its mirror. Measured against the stored H3 vectors of the 2026-10-12 batch, this
#: cut the `KEEP` gap from 3.53 to 1.90 scale points (`docs/DECISIONS.md`).
_H3_MIRRORED: dict[str, bool] = {"FAIR": False, "PUSH": False, "KEEP": True}

_H3_SUFFIX: dict[str, str] = {
    "FAIR": "FAIR",
    "PUSH": "VOIC",
    # `v7`: was `LOYA`. See `_H3_MIRRORED` — the question asks likelihood, not hope.
    "KEEP": "EXIT",
}

if set(_H3_SUFFIX) != set(_H3_MIRRORED):  # pragma: no cover - import-time guard
    raise GeneratorError(
        "_H3_SUFFIX and _H3_MIRRORED must name the same three Part 17 questions; a suffix "
        "present in one and absent from the other would be scored forward by default, which is "
        "the defect v7 corrects."
    )


def _item_target(
    item: Any,
    ref: ReferenceData,
    *,
    targets: dict[str, float],
    spec: GeneratorSpec,
    arm: str,
    edep_position: float,
    reactivity: float = 1.0,
    lever_weights: dict[str, float] | None = None,
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
    mirrored = False
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
        version_code = _arm_version_code(ref, arm)
    elif item.role == "holdout_h3":
        suffix = item.item_id.rsplit("_", 1)[-1]
        try:
            construct = _H3_SUFFIX[suffix]
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
        mirrored = _H3_MIRRORED[suffix]
        version_code = item.version_code
    else:
        construct = construct_code_for(item)
        if construct is None:
            # An item with no construct and no holdout role takes the midpoint. Nothing in the
            # frozen register is in this case today; it is not an error if one is added.
            return 4.0
        return targets[construct]

    # `+ shift[construct]`, with no `sign *`: the matrix is signed (`v5`), so applying
    # `index_sign` here as well would double-apply it and invert pushback, leaving and control.
    shift = reaction_shift(
        version_code,
        spec,
        economic_dependence=edep_position,
        reactivity=reactivity,
        lever_weights=lever_weights,
    )
    # `v11`. **How much of a holdout ANSWER depends on which package was described.**
    #
    # Applied here and deliberately **not** inside `reaction_shift`. The one real respondent on
    # record moved 2.47 points from their own baseline — a large, real effect, and what
    # `reaction_gain` fitted — while answering the six Part 17 versions within a range of
    # **exactly one scale point**. Those are two different facts about the same person: the
    # protections moved them a long way, and they *reported* six hypotheticals coarsely, in two
    # response patterns. Conflating them is a mistake that was made and measured before this
    # landed: shrinking the shift inside `reaction_shift` reproduced the respondent beautifully
    # (error 0.863 → 0.392) and, because it mixes every lever's row into every code, it moved a
    # conditions-only code's effect on clarity from the matrix's `0.000` to `+1.028` and
    # **inverted** sub-additivity from −0.72 to +2.10. That is the pre-`v5` defect — no lever
    # distinguishable from another — and it would make every path estimated on synthetic data an
    # artefact (`docs/DECISIONS.md`, 2026-10-13 v11).
    #
    # So the compression is a claim about **reporting a hypothetical**, which is what Parts 16
    # and 17 ask for, and it touches nothing else. `reaction_shift` keeps the full lever matrix,
    # its signs, its zeros and its two interactions, so the sweep, `analysis/interactions.py` and
    # the PLS-SEM are untouched by it.
    #
    # Shrunk toward `mean_shift` — the mean over every code that raises something, a property of
    # the spec and this respondent rather than of the code being asked about — so the mean holdout
    # answer is preserved exactly and only the spread between packages moves. The respondent's own
    # reactivity sits inside that mean, so person-discrimination is untouched.
    # **Part 17 only, and that scope is the point.** The parameter is fitted to the respondent's
    # spread ACROSS the six Part 17 versions, which is a within-person comparison. Part 16 asks
    # one hypothetical — the respondent's own assigned arm — so there is no across-version spread
    # there to compress, and shrinking a single code toward the mean over all codes is not a
    # compression at all but a LEVEL SHIFT away from what that arm implies. Measured, not
    # assumed: applying it to H2 as well moved `mae_own` on the H2 block from 0.95 to 2.00 and
    # took validity test 1 from CHECK to FAIL, because every respondent's H2 answers converged
    # on the same mean and the between-person distance the test reads fell from 1.44 to 1.20
    # (`docs/DECISIONS.md`, 2026-10-13 v11). The level of an H2 answer is `reaction_gain`'s to
    # set, and it is calibrated.
    lam = spec.holdout_version_differentiation
    moved_shift = shift[construct]
    if item.role == "holdout_h3" and lam != 1.0 and any(dials_of_code(version_code).values()):
        mean = mean_shift(
            spec,
            economic_dependence=edep_position,
            reactivity=reactivity,
            lever_weights=lever_weights,
        )[construct]
        moved_shift = mean + lam * (moved_shift - mean)
    moved = targets[construct] + moved_shift
    # An H3 question that runs opposite to its construct is mirrored **after** the shift, not
    # before (`v7`): the lever matrix moves the construct, and the question then reads that moved
    # construct backwards. Mirroring first would apply the shift in the wrong direction and turn a
    # version that reduces the wish to leave into one that reduces the likelihood of staying.
    if mirrored:
        moved = 8.0 - moved
    return max(1.0, min(7.0, moved))


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
        "woman_share", "second_step_factor", "lever_synergy",
        "between_driver_swing", "incident_share",
        # `v8`. Listed here or the config file could carry a gain the generator ignored, which is
        # the exact defect this docstring describes: a batch recording a configuration that did
        # not describe it.
        "reaction_gain", "reactivity_spread", "salience_spread",
        "holdout_version_differentiation", "endpoint_avoidance",
    ):
        if key in config:
            fields[key] = float(config[key])
    if "captive_voice" in config:
        fields["captive_voice"] = bool(config["captive_voice"])
    if "lever_reactions" in config:
        fields["lever_reactions"] = {
            str(k): float(v) for k, v in dict(config["lever_reactions"]).items()
        }
    if "lever_effects" in config:
        # The spec's validator refuses an unknown lever or construct key, so a typo in the file
        # fails at construction rather than contributing nothing to a batch that looks correct.
        fields["lever_effects"] = {
            str(lever): {str(c): float(v) for c, v in dict(row or {}).items()}
            for lever, row in dict(config["lever_effects"]).items()
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
                # The prose banks are versioned separately from the draw order: a reworded bank
                # changes every persona hash without changing which values were drawn, and a
                # later reader needs to be able to tell those two apart.
                "voice_version": VOICE_VERSION,
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
