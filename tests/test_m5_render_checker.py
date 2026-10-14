"""M5 — the design agent and the Checker. `docs/11` M5.

The eight acceptance criteria are implemented verbatim, each named in its test. Beside them sit the
tests that prove each gate can **fail**: a gate that cannot fail is not a gate
(`HANDOFF.md` §2.4).

Nothing here calls a live LLM. Every model step goes through :class:`StubModelClient`, which counts
calls per `agent_id` — which is what "the design agent was called exactly 10 times" needs.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from twinlab.agents.design import BLOCK_ORDER, build_user_prompt
from twinlab.agents.registry import (
    ConfigError,
    StubModelClient,
    build_agent,
    default_agent_configs,
)
from twinlab.ingest.reference_store import reference
from twinlab.models.reference import LEVER_BY_POSITION, MET_CRITERIA
from twinlab.models.variant import (
    DIAL_ZERO_TEXT,
    SHAM_DIAL,
    CoverageProbe,
    CoverageVerdict,
    LeverParagraph,
)
from twinlab.orchestrator.odometer import SHAM_CODE, all_codes, dials
from twinlab.variant import checker as ck
from twinlab.variant.lookup import commitments_for_lever, lookup
from twinlab.variant.render import (
    ParagraphPool,
    band_for,
    build_brief,
    forbidden_for,
    load_style_contract,
    render_all,
    render_variant,
    resolved_style,
    select_anchors,
    sham_briefs,
)

#: The band most of these tests are graded against: `L2` at dial 1, three commitments. From
#: `style_version: v3` there is no global `word_min`/`word_max` to pass, because there is no
#: global band — the band is resolved per `(lever, dial)` from the commitment count, and
#: `check_invariance` takes the resolved pair. Three is used because it is the modal dial-1 count.
COMMITMENTS_L2_D1 = 3


def graded_style(n: int = COMMITMENTS_L2_D1) -> dict:
    """The style contract with the band resolved for ``n`` commitments."""
    return resolved_style(load_style_contract(), n)


def bands(n: int = COMMITMENTS_L2_D1, lever: str = "L2") -> dict[str, tuple[int, int]]:
    """``build_report``'s per-lever band argument, for one lever at ``n`` commitments."""
    return {lever: band_for(n, load_style_contract())}

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS = REPO_ROOT / "src" / "twinlab" / "agents" / "prompts"

#: The specification's own `01000` Conditions render, `docs/03` §4.2. Transcribed verbatim, em
#: dashes included. The single most useful fixture in the suite: it is text the specification calls
#: correct, so any gate that rejects it is wrong about something.
SPEC_RENDER = (
    "Uber now gives you the safety equipment you need for your vehicle, and pays for your "
    "training instead of expecting you to arrive with it. The safety support already in the app "
    "— the emergency button, trip sharing, round-the-clock help — is now something you "
    "can count on rather than something Uber can withdraw. And if you are hurt while working, "
    "Uber's cover pays, with the amount and the claim steps written down."
)

#: A 59-word paragraph that clears every gate, for tests about plumbing rather than prose.
#:
#: Deliberately about **nothing in the codebook**. An earlier version of this fixture read like
#: ordinary Conditions prose and tripped containment on `2.1.a` in every cell that does not carry
#: it — the gate working correctly on a careless fixture. A fixture that has to dodge the gate is
#: the wrong fixture; this one carries no commitment vocabulary at all.
FILLER = (
    "The way this works for you is changing from today onwards, and the notes below explain what "
    "that means in ordinary language. You can read them whenever you like, and they stay in the "
    "same place so you can find them again later. Nothing here asks anything further of you, and "
    "you can carry on driving exactly as before."
)


#: Plain, commitment-free clause stock for :func:`filler_words`. Everyday words only, so a
#: generated paragraph sits near the middle of the reading-grade band whatever its length.
_FILLER_CLAUSES: tuple[str, ...] = (
    "the way this works for you is changing from today onwards",
    "the notes below explain what that means in ordinary language",
    "you can read them whenever you like and find them again later",
    "they stay in the same place so you always know where they are",
    "nothing here asks anything further of you at any point whatsoever",
    "you can carry on driving exactly as you did before",
    "there is no form to fill in and no one to call",
    "the wording below is identical to the wording everybody else is shown",
)


def filler_words(count: int) -> str:
    """A gate-clearing paragraph of exactly ``count`` words.

    **Needed from `style_version: v3`**, where the word band is resolved per `(lever, dial)` from
    the commitment count and runs `[51, 85]` at two commitments to `[159, 265]` at eight. Those
    bands are disjoint, so there is no longer any single fixed string a stub can return for all
    ten lever paragraphs — the old 59-word `FILLER` now fails gate 3 for seven of them. A stub
    that returned it would make every v3 render test fail for a reason that has nothing to do
    with what the test is about.

    Carries no commitment vocabulary at all, for the reason recorded on :data:`FILLER`: a fixture
    that has to dodge the containment gate is the wrong fixture.
    """
    words: list[str] = []
    index = 0
    while len(words) < count:
        clause = _FILLER_CLAUSES[index % len(_FILLER_CLAUSES)].split()
        index += 1
        words.extend(clause)
        if len(words) >= count:
            break
        words.append("and")
    words = words[:count]
    # A full stop every sixteen words. The length is set by gate 3's *other* half: at eight-word
    # sentences of everyday one-syllable words the Flesch-Kincaid grade comes out near 2.5, below
    # the 4.0 floor, and the fixture would fail the register band it is meant to clear.
    out: list[str] = []
    for position, word in enumerate(words, start=1):
        out.append(word)
        if position % 16 == 0 and position != len(words):
            out[-1] = word + "."
    return " ".join(out).capitalize() + "."


def _paragraph(text: str | None = None) -> LeverParagraph:
    """A paragraph that clears gate 3 for a three-commitment brief — the common test case."""
    return LeverParagraph(text=text if text is not None else filler_words(80))


def _band_in_prompt(prompt: str) -> tuple[int, int]:
    """The resolved word band the design prompt's STYLE block actually asked for.

    Read back out of the prompt rather than recomputed from the brief, which makes it a check as
    well as a convenience: if `build_brief` ever stopped resolving the band, the stub would emit
    the wrong length and gate 3 would fail the test.
    """
    low = int(re.search(r'"word_min":\s*(\d+)', prompt).group(1))
    high = int(re.search(r'"word_max":\s*(\d+)', prompt).group(1))
    return low, high


def design_stub(text: str | None = None):
    """A client whose design calls return a band-fitting paragraph and whose probes all pass.

    With ``text``, that exact string is returned for every lever — for tests that are about the
    text. Without it, each paragraph is generated to sit inside **that brief's own** resolved
    band, which is the only way one stub can serve all ten paragraphs under v3.
    """

    def handler(cfg, prompt, out):
        if out is LeverParagraph:
            if text is not None:
                return LeverParagraph(text=text)
            low, high = _band_in_prompt(prompt)
            return LeverParagraph(text=filler_words((low + high) // 2))
        if out is CoverageVerdict:
            return CoverageVerdict(entailed=True, reason="stub")
        raise AssertionError(f"unexpected output type {out}")

    return StubModelClient(handler)


# ---------------------------------------------------------------- I4: ten calls, not 243


async def test_rendering_all_243_codes_calls_the_design_agent_exactly_ten_times():
    """I4 — ten non-zero lever paragraphs plus one fixed string serve all 243 cells.

    Asserted on the call counter, not wall time (`docs/11` M5). Ten is 5 levers x 2 non-zero
    dials; dial 0 is never generated.
    """
    client = design_stub()
    pool = ParagraphPool(client=client)
    variants = await render_all(all_codes(), pool)

    assert len(variants) == 243
    assert client.call_count("design") == 10
    assert len(pool.cached()) == 10
    assert {dial for _, dial, _ in pool.cached()} == {1, 2}


async def test_every_cell_with_the_same_dial_shows_the_byte_identical_paragraph():
    """I4's purpose, not just its cost: there is no per-cell wording to confound a lever."""
    client = design_stub()
    pool = ParagraphPool(client=client)

    # Two codes differing everywhere except Conditions, which is 1 in both.
    a = await render_variant("01000", pool)
    b = await render_variant("21222", pool)
    assert a.paragraphs["L2"].text == b.paragraphs["L2"].text
    assert a.paragraphs["L1"].text != b.paragraphs["L1"].text


async def test_a_cache_hit_is_never_re_rendered():
    """`docs/DECISIONS.md` — a re-render on a cache *hit* would call design once per cell."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    await render_variant("11111", pool)
    assert client.call_count("design") == 5
    for _ in range(20):
        await render_variant("11111", pool)
    assert client.call_count("design") == 5


async def test_concurrent_cells_wanting_one_paragraph_spend_one_design_call():
    """I4 at the concurrency boundary: the pool re-checks under its lock."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    await asyncio.gather(*(render_variant("01000", pool) for _ in range(8)))
    assert client.call_count("design") == 1


# ---------------------------------------------------------------- I5: the fixed dial-0 string


async def test_every_dial_zero_lever_renders_the_byte_identical_fixed_string():
    """I5 — `"No change from today."`, never generated, byte-identical everywhere."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    variants = await render_all(all_codes(), pool)

    seen = 0
    for code, variant in variants.items():
        for lever, dial in dials(code).items():
            if dial == 0:
                assert variant.paragraphs[lever].text == DIAL_ZERO_TEXT
                seen += 1
    assert seen == sum(code.count("0") for code in all_codes())


async def test_the_all_zero_control_spends_no_design_call():
    """Dial 0 is never generated (I5), so `00000` costs nothing and cannot drift."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    variant = await render_variant("00000", pool)
    assert client.call_count("design") == 0
    assert {p.text for p in variant.paragraphs.values()} == {DIAL_ZERO_TEXT}


def test_the_null_identity_gate_rejects_an_altered_dial_zero_line():
    """Gate 4 can fail. `"No change from today"` without the stop is a different stimulus."""
    paragraphs = {lever: _paragraph(DIAL_ZERO_TEXT) for lever in LEVER_BY_POSITION}
    zero = {lever: 0 for lever in LEVER_BY_POSITION}
    assert ck.dial_zero_identical(paragraphs, zero)

    paragraphs["L3"] = _paragraph("No change from today")
    assert not ck.dial_zero_identical(paragraphs, zero)


def test_the_style_contract_and_the_constant_cannot_drift():
    """A `dial_zero_text` edit in YAML that did not reach the constant would break I5 silently."""
    assert load_style_contract()["dial_zero_text"] == DIAL_ZERO_TEXT


def test_the_style_contract_guards_reject_a_drifted_or_empty_contract():
    """The three `load_style_contract()` guards can each actually fail.

    `style_version` is declared twice — in the contract and in `config/settings.py` — and the render
    cache key is built from it, so a disagreement means two different contracts competing for one
    cache slot. Nothing reads the settings copy today, which is precisely how it would drift.
    """
    from config.settings import settings
    from twinlab.variant.render import RenderFailed, validate_style_contract

    good = load_style_contract()
    assert good["style_version"] == settings.style_version
    assert validate_style_contract(dict(good)) == good

    for mutation, expected in (
        ({"dial_zero_text": "No change from today"}, "I5"),
        ({"style_version": "v99"}, "style_version"),
        # The clamp, inverted. Not a band scalar: from v3 there are none.
        ({"word_floor": good["word_ceiling"] + 1}, "clamp"),
        # Coefficients that cross over. This is the v3-specific failure the guard exists for: a
        # per-commitment pair can be valid at one commitment count and empty at another, and the
        # cell that hit it would be the first to know. `validate_style_contract` therefore probes
        # the whole range the frozen lookup can produce rather than one value.
        ({"word_max_per_commitment": 0, "word_max_base": 30}, "empty band"),
    ):
        with pytest.raises(RenderFailed, match=expected):
            validate_style_contract({**good, **mutation})

    # And a coefficient that is simply absent must be refused rather than defaulted: a missing
    # one would not fail, it would quietly become a *different* band, which is the confound the
    # `style_version` key exists to prevent.
    for key in (
        "word_min_base",
        "word_min_per_commitment",
        "word_max_base",
        "word_max_per_commitment",
        "word_floor",
        "word_ceiling",
    ):
        missing = {k: v for k, v in good.items() if k != key}
        with pytest.raises(RenderFailed, match="missing"):
            validate_style_contract(missing)


def test_the_word_band_is_a_function_of_the_commitment_count():
    """WP-1. The calibration table from the plan's Q1, as an executable assertion.

    One band of `[45, 150]` served commitment sets of 2 to 8, giving `L1` dial 1 seventy-five
    words per commitment and `L3`/`L4` dial 2 nineteen. The design prompt asks for each commitment
    in its own short sentence and the Checker probes each one for entailment, so at eight
    commitments the model had to compress and the compression lost the entailments.

    The formula is **calibrated against the eight paragraphs this project actually rendered**: it
    accepts all six that passed and rejects both that failed, and it rejects them for being too
    *short*, which is the correct diagnosis.
    """
    style = load_style_contract()
    observed = [
        (2, 77, True),      # L1 dial 1 — passed
        (3, 88, True),      # L2 dial 1 — passed
        (3, 92, True),      # L1 dial 2 — passed
        (3, 96, True),      # L5 dial 1 — passed
        (3, 109, True),     # L4 dial 1 — passed
        (6, 138, True),     # L2 dial 2 — passed
        (8, 150, False),    # L3 dial 2 — FAILED on coverage
        (8, 152, False),    # L4 dial 2 — FAILED on band and coverage
    ]
    for n, words, should_pass in observed:
        low, high = band_for(n, style)
        assert (low <= words <= high) is should_pass, (
            f"{n} commitments, {words} words: band [{low}, {high}]"
        )
        if not should_pass:
            assert words < low, "both historical failures were too SHORT, not too long"

    # Monotonic, so more commitments never buys less room.
    for n in range(2, 9):
        assert band_for(n, style)[0] <= band_for(n + 1, style)[0]
        assert band_for(n, style)[1] <= band_for(n + 1, style)[1]

    # Constant for a given commitment count, so it cannot vary with the cell (I4 untouched).
    assert band_for(4, style) == band_for(4, style)


def test_the_resolved_band_is_what_the_agent_is_shown_and_what_the_gate_uses():
    """WP-1. One pair of numbers, reaching the prompt and gate 3 from the same place.

    The brief carries the resolved band, `agents.design.style_block` shows it, and
    `check_invariance` reads the same two keys — so the agent cannot be graded against a band it
    was not told about, which is what happened at eight commitments under v2.
    """
    style = load_style_contract()
    for code, lever, expected_n in (("01000", "L2", 3), ("02000", "L2", 6), ("22222", "L3", 8)):
        brief = build_brief(lookup(code), lever)
        assert len(brief.commitments) == expected_n
        assert (
            brief.style_contract["word_min"],
            brief.style_contract["word_max"],
        ) == band_for(expected_n, style)
        shown = build_user_prompt(brief)
        assert f'"word_min": {band_for(expected_n, style)[0]}' in shown
        assert f'"word_max": {band_for(expected_n, style)[1]}' in shown


def test_the_sham_is_held_to_its_levers_dial_one_band():
    """`ARCHITECTURE.md` §5.2 — "same word band and voice as a live cell". WP-1.

    The sham announces one or two slots per lever, so resolving its band from its own count would
    put four of its five levers in `[45, 55]` while every live lever sits at `[51, 85]` or wider.
    The sham would then be the shortest cell in the study and recognisable as the control by
    length alone — and a twin that can tell it is looking at a control is not measuring the demand
    characteristic the cell exists to measure.
    """
    style = load_style_contract()
    ref = reference()
    briefs = sham_briefs()
    for lever, brief in briefs.items():
        dial_one_n = len(ref.dial_lookup[lever]["1"])
        assert (
            brief.style_contract["word_min"],
            brief.style_contract["word_max"],
        ) == band_for(dial_one_n, style), lever
        # Which is a real live cell's band, not a band of its own.
        assert brief.style_contract["word_min"] >= band_for(2, style)[0]


# ---------------------------------------------------------------- I3: containment


def test_a_poisoned_render_containing_2_2_language_fails_containment_for_01000():
    """I3 as amended 2026-10-04 (researcher decision): a containment hit is **recorded**, not
    enforced, because two predefined commitments can share wording. The hit must still be
    detected and reported verbatim, so the overlap stays visible in the data.

    The poison is threshold 2.2 material, which `01000` must not carry.
    """
    spec = lookup("01000")
    allowed = commitments_for_lever(spec, "L2")
    forbidden = forbidden_for(spec, "L2")

    poisoned = SPEC_RENDER + (
        " Uber will also extend e-Shram support beyond the first 10,000 drivers and state what "
        "it contributes to social protection."
    )
    hits = ck.containment_hits(poisoned, forbidden, allowed)
    assert "2.2.a" in hits

    report = ck.build_report(
        paragraphs={"L2": _paragraph(poisoned)},
        dials={"L2": 1},
        style=load_style_contract(),
        coverage={g: True for g in allowed},
        containment=hits,
        bands=bands(len(allowed)),
    )
    assert report.containment == hits
    assert "info: containment hit" in report.notes


def test_a_containment_hit_is_recorded_and_does_not_fail_the_cell():
    """Amended I3 (2026-10-04): containment is informational. A hit is reported, never hidden."""
    report = ck.build_report(
        paragraphs={"L2": _paragraph()},
        dials={"L2": 1},
        style=load_style_contract(),
        coverage={"2.1.a": True},
        containment=["2.2.a"],
        bands=bands(),
    )
    assert report.passed
    assert report.containment == ["2.2.a"]


def test_the_specifications_own_known_good_render_passes_containment():
    """The false-positive guard, and the reason containment matches **pairs** not words.

    A single-content-word rule flags 16 of the 27 forbidden commitments on this paragraph — the
    specification's own correct output — because `uber`, `trip`, `app`, `claim` and `written` are
    shared vocabulary. A gate that fails every cell is not a gate.
    """
    spec = lookup("01000")
    allowed = commitments_for_lever(spec, "L2")
    forbidden = forbidden_for(spec, "L2")
    assert ck.containment_hits(SPEC_RENDER, forbidden, allowed) == []


def test_no_forbidden_commitment_has_an_empty_signature():
    """An empty signature is a commitment that could leak **undetected**.

    Checked across every (lever, dial, forbidden) combination over the frozen reference data, and
    each forbidden commitment dropped in verbatim must be caught.
    """
    ref = reference()
    checked = 0
    for lever in LEVER_BY_POSITION:
        for dial in ("1", "2"):
            spec = lookup("".join(dial if lv == lever else "0" for lv in LEVER_BY_POSITION))
            allowed = commitments_for_lever(spec, lever)
            allowed_text = " ".join(allowed.values())
            forbidden = forbidden_for(spec, lever, ref)
            for identifier, text in forbidden.items():
                checked += 1
                signature = ck.signature(text, allowed_text)
                assert signature, f"{identifier} has no distinctive bigram against {lever}/{dial}"
                # The pairs this commitment shares with no OTHER forbidden commitment. Gate 2
                # fires on these alone (researcher decision, 2026-09-30), so an empty one is a
                # commitment that could leak undetected — the same failure the line above rules
                # out, one level up. Over the frozen data there are none, and that is the whole
                # cost of the narrowing.
                distinctive = ck.distinctive_signatures(forbidden, allowed_text)[identifier]
                assert distinctive, (
                    f"{identifier} shares every bigram with another forbidden commitment against "
                    f"{lever}/{dial}, so it could leak undetected"
                )
                # And dropping that commitment in verbatim is actually caught.
                assert identifier in ck.containment_hits(text, forbidden, allowed)
    assert checked == 285


def test_a_bigram_shared_between_commitments_is_not_a_leak():
    """Gate 2 fires on **distinctive** vocabulary. Researcher decision, 2026-09-30.

    ``("driver", "app")`` occurs in four different commitments because *Driver app* is Uber's own
    name for the thing. A pair that cannot say which commitment leaked is shared vocabulary, not
    evidence that one did — and before this, it failed almost every cell in the sweep.
    """
    ref = reference()
    spec = lookup("00010")
    allowed = commitments_for_lever(spec, "L4")
    forbidden = forbidden_for(spec, "L4", ref)

    shared = ("driver", "app")
    raw = {i: ck.signature(t, " ".join(allowed.values())) for i, t in forbidden.items()}
    carriers = sorted(i for i, pairs in raw.items() if shared in pairs)
    assert len(carriers) > 1, (
        "this test is pinned to a bigram that several forbidden commitments share; if the "
        "frozen data no longer shares it, pick another shared pair rather than deleting the test"
    )

    # A paragraph whose only forbidden-signature overlap is the shared pair passes...
    assert ck.containment_hits("The Driver app now shows this.", forbidden, allowed) == []
    # ...while a verbatim commitment is still caught by name.
    assert carriers[0] in ck.containment_hits(forbidden[carriers[0]], forbidden, allowed)


# ---------------------------------------------------------------- gate 3: invariance


@pytest.mark.parametrize("count", [41, 44, 68, 116, 151, 200])
def test_an_out_of_band_render_fails_in_band(count: int):
    """`docs/11` M5's word-band criterion, re-expressed twice as the band changed.

    **`docs/11` M5 says verbatim: "A 41-word or 80-word render fails `in_band`."** That was
    written against a 45-70 band. The researcher widened it to 45-150 on 2026-09-29, and on
    2026-10-03 replaced it with a **function of the commitment count** (`style_version: v3`, M19
    WP-1) because one band could not serve sets of 2 to 8 commitments.

    So there is no longer one band to assert against, and the criterion's **intent** — the gate
    rejects a render that is too short or too long, at both ends — is what is tested, against the
    band for three commitments, `[69, 115]`: 41, 44 and 68 fail below; 116, 151 and 200 fail
    above. 68 and 116 are the just-outside cases, which is where an off-by-one would hide.

    **`docs/11` M5's literal numbers are superseded and need updating**; the decisions are in
    `docs/DECISIONS.md`.
    """
    in_band, _, _ = ck.check_invariance(" ".join(["policy"] * count), graded_style())
    assert not in_band


@pytest.mark.parametrize("count", [69, 71, 80, 115])
def test_a_render_inside_the_band_passes_in_band(count: int):
    """The band is inclusive at both ends, so the gate admits what it is meant to admit.

    Against the three-commitment band `[69, 115]`. 69 and 115 are the ends, asserted inclusive.
    71 is the length of the specification's own exemplar (`docs/03` §4.2), which must stay
    admissible under every band the project has had — it is the one piece of known-good output in
    the repository. **80 is here to make a supersession explicit and executable**: `docs/11` M5
    says an 80-word render must fail, and it must now pass.
    """
    in_band, _, _ = ck.check_invariance(" ".join(["policy"] * count), graded_style())
    assert in_band


def test_the_word_count_does_not_count_a_bare_em_dash_as_a_word():
    """Punctuation is not a word: an identical sentence must not pass or fail on its dashes.

    This is also where the specification's own exemplar is measured. `docs/03` §4.2 and
    `additional_data/worked_out_eg.txt` both call it 66 words; it is **71**. It failed the original
    45-70 band, and the researcher widened the band to 45-75 rather than have the gate reject the
    one piece of known-good output in the repository (`docs/DECISIONS.md`, 2026-09-29).

    The 71 is asserted, not the band, so the count rule stays pinned even if the band moves again.
    """
    assert ck.word_count("a — b") == 2
    assert ck.word_count(SPEC_RENDER) == 71
    assert ck.check_invariance(SPEC_RENDER, graded_style())[0]


def test_a_forbidden_term_fails_the_invariance_gate():
    """`docs/02` §3.5 — `forbidden_terms` apply to everything a twin can see."""
    style = graded_style()
    text = " ".join(["policy"] * 80) + " this meets the Fairwork threshold today."
    _, _, violations = ck.check_invariance(text, style)
    assert any("Fairwork" in v for v in violations)
    assert any("threshold" in v for v in violations)


def test_a_forbidden_intensifier_fails_the_invariance_gate():
    """Cell-specific drama is a confound: one cell must not read as more triumphant than another."""
    style = graded_style()
    text = " ".join(["policy"] * 80) + " this is a dramatically unprecedented change today."
    _, _, violations = ck.check_invariance(text, style)
    assert any("dramatically" in v for v in violations)
    assert any("unprecedented" in v for v in violations)


def test_a_clean_paragraph_raises_no_invariance_violation():
    """The gate admits ordinary policy prose — including the specification's own exemplar."""
    _, grade, violations = ck.check_invariance(SPEC_RENDER, graded_style())
    assert violations == []
    assert 4.0 <= grade <= 16.0


def test_reading_grade_outside_the_band_is_a_violation():
    """Gate 3's grade half can fail, in both directions."""
    style = graded_style()
    dense = (
        "Notwithstanding aforementioned indemnification obligations, remuneration recalibration "
        "necessitates comprehensive administrative reconsideration internationally whenever "
        "extraordinary circumstances materialise unpredictably throughout jurisdictions."
    )
    _, grade, violations = ck.check_invariance(dense, style)
    assert grade > style["reading_grade_max"]
    assert any("reading grade" in v for v in violations)


def test_a_cannot_render_paragraph_fails_the_report():
    """`docs/02` §4.1 — the cell is marked failed and logged, never generically filled.

    No `bands`: a refusal is rejected before gate 3, so the report must not need a word band to
    refuse one. If that stopped being true this would raise `CheckerMisuse`.
    """
    report = ck.build_report(
        paragraphs={"L2": LeverParagraph(text="", status="cannot_render", reason="blocked")},
        dials={"L2": 1},
        style=load_style_contract(),
        coverage={},
        containment=[],
    )
    assert not report.passed
    assert "cannot_render" in report.notes


# ---------------------------------------------------------------- coverage fails closed


async def test_a_coverage_probe_that_cannot_decide_returns_entailed_false():
    """`docs/11` M5 — uncertainty fails closed. Three ways a probe can fail to decide."""
    from twinlab.agents.checker import run_coverage_probe

    cfg = default_agent_configs()["checker"]
    probe = CoverageProbe(gap_id="2.1.a", commitment="Supply equipment.", paragraph=FILLER)

    unparseable = StubModelClient(lambda c, p, o: "I am not sure, possibly?")
    assert not (await run_coverage_probe(cfg, probe, unparseable)).entailed

    wrong_shape = StubModelClient(lambda c, p, o: {"verdict": "maybe"})
    assert not (await run_coverage_probe(cfg, probe, wrong_shape)).entailed

    def boom(c, p, o):
        raise RuntimeError("provider exploded")

    assert not (await run_coverage_probe(cfg, probe, StubModelClient(boom))).entailed


def test_an_unparseable_verdict_is_not_retried():
    """`docs/02` §5.5 — re-asking a gate until it answers cleanly is how it stops being one."""
    cfg = default_agent_configs()["checker"]
    assert cfg.retry.attempts == 1
    assert cfg.retry.repair_mode == "none"
    assert cfg.model.temperature == 0.0


def test_a_missing_verdict_counts_as_not_entailed():
    """`verdicts_to_coverage` never invents a pass for a probe that did not run."""
    assert ck.verdicts_to_coverage({}) == {}
    coverage = ck.verdicts_to_coverage({"2.1.a": CoverageVerdict(entailed=False, reason="unsure")})
    report = ck.build_report(
        paragraphs={"L2": _paragraph()},
        dials={"L2": 1},
        style=load_style_contract(),
        coverage=coverage,
        containment=[],
        bands=bands(),
    )
    assert not report.passed
    assert "not entailed" in report.notes


async def test_a_live_cell_is_probed_once_per_commitment():
    """Coverage is one call per commitment, and dial-0 levers are not probed at all."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    variant = await render_variant("01000", pool)
    report = await ck.check_variant(variant, client=client)
    assert client.call_count("checker") == 3          # threshold 2.1 has three gaps
    assert sorted(report.coverage) == ["2.1.a", "2.1.b", "2.1.c"]


async def test_the_all_zero_control_is_probed_not_at_all():
    """`00000` has no commitments, so there is nothing to entail and no model call to make."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    variant = await render_variant("00000", pool)
    report = await ck.check_variant(variant, client=client)
    assert client.call_count("checker") == 0
    assert report.coverage == {}
    assert report.dial_zero_identical
    assert report.passed


# ---------------------------------------------------------------- the sham


async def test_sham_passes_every_gate_has_no_null_line_and_occupies_dial_three():
    """`docs/11` M5, verbatim. `docs/03` §6.2.

    The sham measures how much a twin moves simply because it was shown change-shaped text, so a
    `"No change from today."` line would give it away and it must clear the gates a live cell
    clears.
    """
    client = design_stub()
    pool = ParagraphPool(client=client)
    variant = await render_variant(SHAM_CODE, pool)

    assert set(variant.dials.values()) == {SHAM_DIAL} == {3}
    assert DIAL_ZERO_TEXT not in {p.text for p in variant.paragraphs.values()}
    assert ck.no_dial_zero_line(variant.paragraphs)

    report = await ck.check_variant(variant, client=client)
    assert report.sham_indistinguishable is True
    assert report.containment == []
    assert report.passed


async def test_the_sham_spends_its_own_five_paragraph_slots():
    """`dial = 3` is a cache slot that cannot collide with a live dial-0/1/2 paragraph."""
    client = design_stub()
    pool = ParagraphPool(client=client)
    await render_variant(SHAM_CODE, pool)
    assert {dial for _, dial, _ in pool.cached()} == {SHAM_DIAL}
    assert client.call_count("design") == 5

    # I4 still counts only dials 1 and 2: the sham does not inflate the ten.
    await render_all(all_codes(), pool)
    live = [k for k in pool.cached() if k[1] in (1, 2)]
    assert len(live) == 10


def test_the_sham_has_zero_free_parameters():
    """Its content is the three `Met` criteria plus one chunk per unfilled lever, by frozen id.

    Nothing here was chosen for plausibility: `3.1.a` and `3.1.c` sit on Contracts and `4.1.c` on
    Management because that is where the codebook puts them, and the remaining three levers take
    their lowest-numbered driver-audience chunk (researcher decision, 2026-09-22).
    """
    ref = reference()
    briefs = sham_briefs(ref)
    assert set(briefs) == set(LEVER_BY_POSITION)
    assert sorted(briefs["L3"].commitments) == ["3.1.a", "3.1.c"]
    assert sorted(briefs["L4"].commitments) == ["4.1.c"]
    assert set(MET_CRITERIA) == set(briefs["L3"].commitments) | set(briefs["L4"].commitments)

    for lever in ("L1", "L2", "L5"):
        (chunk_id,) = briefs[lever].commitments
        candidates = sorted(
            c.chunk_id for c in ref.chunks.values()
            if c.lever == lever and c.audience == "driver"
        )
        assert chunk_id == candidates[0]

    # Every real gap is forbidden: the sham may announce existing policy and nothing else.
    for brief in briefs.values():
        assert len(brief.do_not_say) == len(ref.gaps) == 30

    # Derived from frozen data alone, so it is byte-stable.
    assert sham_briefs(ref) == briefs


def test_the_sham_containment_gate_still_fails_on_a_real_gap_commitment():
    """`docs/DECISIONS.md` — scoping containment to existing policy does not disarm it."""
    from twinlab.variant.render import sham_allowed

    ref = reference()
    allowed = sham_allowed(ref)
    forbidden = {gap_id: ref.gaps[gap_id].commitment for gap_id in sorted(ref.gaps)}
    leaked = ref.gaps["2.1.c"].commitment
    assert "2.1.c" in ck.containment_hits(leaked, forbidden, allowed)


# ---------------------------------------------------------------- I2: the design agent's tools


def test_the_design_agent_has_no_tools_and_build_agent_raises_if_one_is_added():
    """I2, `docs/11` M5 verbatim. Re-asserted here beside the others; the guard is M2's."""
    cfg = default_agent_configs()["design"]
    assert cfg.tools == []
    assert cfg.react is False

    with pytest.raises(ConfigError, match="I2"):
        build_agent(cfg.model_copy(update={"tools": ["session_state"]}))


def test_the_design_brief_carries_exactly_four_blocks_and_no_dial_digit():
    """`docs/02` §4.1 and §3.3 — four labelled fences, in a fixed order.

    The lever and the dial are deliberately absent from the prompt: a digit telling the agent it is
    writing "the strong version" is a channel into the prose and therefore a confound.
    """
    brief = build_brief(lookup("01000"), "L2")
    prompt = build_user_prompt(brief)

    assert [m.group(1) for m in re.finditer(r"<<<([A-Z_]+)>>>", prompt)] == list(BLOCK_ORDER)
    assert len(BLOCK_ORDER) == 4
    assert "L2" not in prompt
    assert "01000" not in prompt
    for gap_id in ("2.1.a", "2.2.a"):
        assert gap_id not in prompt          # ids never reach the agent, only prose


def test_the_brief_holds_this_levers_commitments_and_forbids_every_other():
    """The containment boundary, as the agent actually receives it."""
    ref = reference()
    brief = build_brief(lookup("01000"), "L2", ref)
    assert sorted(brief.commitments) == ["2.1.a", "2.1.b", "2.1.c"]

    forbidden = set(brief.do_not_say)
    for gap_id in ("2.2.a", "2.2.b", "2.2.c"):
        assert ref.gaps[gap_id].commitment in forbidden
    for criterion_id in MET_CRITERIA:
        assert ref.findings[criterion_id].reason in forbidden


def test_anchor_selection_is_capped_deterministic_and_covers_every_source():
    """CONFIG, recorded in `docs/DECISIONS.md`: uncapped, one brief carries ~24,000 tokens.

    Round-robin rather than truncation, so a gap's anchor sources each contribute the voice they
    were named for.
    """
    ref = reference()
    gap_ids = ref.dial_lookup["L4"]["2"]
    chunks = ref.anchor_chunks(gap_ids)
    assert len(chunks) > 20                       # uncapped this brief is enormous

    picked = select_anchors(chunks)
    assert len(picked) == 9
    assert picked == select_anchors(chunks)        # deterministic

    by_text = {c.verbatim_text: c.source_id for c in chunks}
    sources_present = {by_text[t] for t in picked}
    all_sources = {c.source_id for c in chunks}
    assert sources_present == all_sources or len(all_sources) > 9


# ---------------------------------------------------------------- prompts


@pytest.mark.parametrize("agent", ["design", "twin"])
def test_no_prompt_file_for_design_or_twin_contains_a_few_shot_example(agent: str):
    """`docs/11` M5 verbatim, `docs/02` §3.4. A containment rule, not a style preference.

    An example paragraph necessarily contains commitments, and any commitment in an example can
    bleed into a cell that does not include it — arriving through the one door the Checker does not
    watch.
    """
    for path in sorted(PROMPTS.glob(f"{agent}_v*.md")):
        text = open(path, encoding="utf-8").read()
        lowered = text.lower()
        for marker in (
            "example",
            "for instance",
            "e.g.",
            "sample output",
            "illustration",
            "here is how",
        ):
            assert marker not in lowered, f"{path.name} contains {marker!r}"
        # A worked example is most often smuggled in as a fenced block of prose or JSON showing
        # what "good" looks like. The refusal payload under `# IF YOU CANNOT` is the one exception.
        body = lowered.split("# if you cannot")[0]
        assert "```" not in body, f"{path.name} has a fenced block outside # IF YOU CANNOT"


def test_the_design_and_twin_prompts_use_none_of_the_forbidden_vocabulary():
    """`docs/02` §3.5 — it applies to the prompt files themselves, not only to the output."""
    forbidden = load_style_contract()["forbidden_terms"]
    for agent in ("design", "twin"):
        for path in sorted(PROMPTS.glob(f"{agent}_v*.md")):
            text = open(path, encoding="utf-8").read()
            body = text.split("---", 2)[-1]       # the front matter names the agent, e.g. `twin`
            hits = ck.term_hits(body, forbidden)
            assert hits == [], f"{path.name} contains {hits}"


def test_the_checker_prompt_may_and_does_use_examples():
    """`docs/02` §3.4 — the Checker produces neither stimulus nor data, and benefits from them."""
    text = open(PROMPTS / "checker_v1.md", encoding="utf-8").read()
    assert "entailed" in text.lower()
    assert "illustration" in text.lower() or "example" in text.lower()


# ---------------------------------------------------------------- reproducibility


def test_the_design_prompt_is_byte_identical_in_a_fresh_interpreter():
    """Anything claimed reproducible across processes gets a subprocess test (`HANDOFF.md` §2.4).

    Run with `PYTHONHASHSEED=random`, because a prompt assembled over set iteration order passes
    in-process and then differs on the run that rebuilds a cached paragraph — the exact failure
    mode that only shows up in production.
    """
    script = textwrap.dedent(
        """
        import hashlib, json, sys
        from twinlab.agents.design import build_user_prompt
        from twinlab.variant.render import build_brief, sham_briefs
        from twinlab.variant.lookup import lookup
        out = {}
        for code, lever in (("01000", "L2"), ("22222", "L4"), ("12012", "L1")):
            prompt = build_user_prompt(build_brief(lookup(code), lever))
            out[code + lever] = hashlib.sha256(prompt.encode()).hexdigest()
        for lever, brief in sham_briefs().items():
            out["SHAM" + lever] = hashlib.sha256(
                build_user_prompt(brief).encode()
            ).hexdigest()
        print(json.dumps(out, sort_keys=True))
        """
    )

    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(["src", "."]),
        "PYTHONHASHSEED": "random",
    }

    def run() -> str:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT, capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        return proc.stdout.strip()

    first, second = run(), run()
    assert first == second
    assert len(json.loads(first)) == 8


def test_the_style_contract_is_constant_across_every_cell():
    """`docs/03` §4.2 — anything that varies **with the cell** is a confound.

    From `style_version: v3` the contract a brief carries is not byte-identical across all five
    levers, because the word band is resolved from that `(lever, dial)`'s commitment count. The
    property that matters is unchanged and is what is asserted: the contract is a function of
    `(lever, dial)` **only**, so every one of the 243 cells that uses a given lever paragraph
    shows the byte-identical contract, and no cell can be given a band another cell was not.

    Asserted as "group by (lever, dial), and each group has exactly one contract" rather than
    "there is exactly one contract overall". The weaker-looking form is the stronger assertion
    here: the old version would also have passed if the band had been dropped from the brief
    altogether.
    """
    by_key: dict[tuple[str, int], set[str]] = {}
    for code in ("01000", "02000", "22222", "11111", "21012", "00000"):
        for lever in LEVER_BY_POSITION:
            brief = build_brief(lookup(code), lever)
            key = (lever, brief.dial)
            body = json.dumps(brief.style_contract, sort_keys=True)
            by_key.setdefault(key, set()).add(body)

    for key, bodies in sorted(by_key.items()):
        assert len(bodies) == 1, f"{key} was shown {len(bodies)} different style contracts"

    # And the only thing that differs between groups is the band — not the person, the tense, the
    # forbidden terms or the reading-grade band, any of which varying would be a real confound.
    # `json.dumps` per value, because `forbidden_terms` is a list and lists are not hashable.
    contracts = [json.loads(next(iter(bodies))) for bodies in by_key.values()]
    varying = {
        key
        for key in contracts[0]
        if len({json.dumps(c.get(key), sort_keys=True) for c in contracts}) > 1
    }
    assert varying <= {"word_min", "word_max"}, varying
