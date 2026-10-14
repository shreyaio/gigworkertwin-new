"""M4 acceptance tests — the persona builder. `docs/11` → M4.

Two of these tests are the reason the module exists rather than a prompt: the passage is asserted
**byte-identical across two processes** (I11 — the hash is what ties a result to the text that
produced it), and it is asserted to contain **no Part 15, 16 or 17 material** (I6 — a twin that has
read its own holdout answers cannot be validated).

The per-item losslessness test asserts per item rather than in aggregate, deliberately. A count of
37 clauses would pass against a builder that rendered `FAIR1` twice and `FAIR4` not at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from twinlab.ingest.reference_store import reference
from twinlab.models.twin import (
    OWN_WORDS_IDS,
    WHY_PROBE_IDS,
    Background,
    PersonaPassage,
    SurveyResponse,
    Twin,
)
from twinlab.persona.builder import (
    HOLDOUT_PARTS,
    PersonaIncomplete,
    build_persona,
    spell,
)
from twinlab.persona.templates import (
    ANCHOR_CLAUSES,
    EXCLUDED_FROM_PERSONA,
    SECTION_ORDER,
    TEMPLATES,
    PersonaTemplateMissing,
    anchor_for,
    template_for,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A twin whose every free-text field is deliberately digit-free, so the I7 scan can be absolute.
TWIN_KWARGS = dict(
    twin_id="UBR-TEST",
    city="Mumbai",
    service="cab",
    age=34,
    gender="Male",
    tenure_months=28,
    hours_per_week=58,
)

BACKGROUND_KWARGS = dict(
    platform_count="2",
    other_apps="Ola and Rapido",
    vehicle_arrangement="rent from a fleet owner",
    dependants=4,
    other_household_income="none",
    education="secondary school",
    years_driving_before_uber=3.5,
)


def _twin(**overrides) -> Twin:
    background = Background(**{**BACKGROUND_KWARGS, **overrides.pop("background", {})})
    return Twin(**{**TWIN_KWARGS, **overrides}, background=background)


def _answers(value_5: int = 4, value_7: int = 5, *, holdouts: bool = False) -> dict[str, int]:
    """A complete battery, and optionally the holdout answers a real row also carries."""
    ref = reference()
    out = {
        item_id: (value_5 if ref.scale_points(item_id) == 5 else value_7)
        for item_id in ref.battery_item_ids
    }
    if holdouts:
        for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
            out[item_id] = value_5 if ref.scale_points(item_id) == 5 else value_7
    return out


def _response(**overrides) -> SurveyResponse:
    base = {"twin_id": "UBR-TEST", "answers": _answers()}
    return SurveyResponse(**{**base, **overrides})


def _built(**overrides) -> PersonaPassage:
    return build_persona(_twin(), _response(**overrides))


# --------------------------------------------------------------------------- determinism


def test_the_same_row_gives_a_byte_identical_passage():
    """`docs/11` → M4, and I11 — the hash ties a result to the exact text that produced it."""
    first, second = _built(), _built()
    assert first.text == second.text
    assert first.persona_hash == second.persona_hash
    assert len(first.persona_hash) == 64


def test_the_same_row_gives_a_byte_identical_passage_across_processes():
    """`docs/11` → M4: "across two processes".

    Run with a randomised string-hash seed. A builder that iterated a set anywhere would pass the
    in-process test and produce a different passage — and a different `persona_hash` — on the run
    that rebuilt a missing persona.
    """
    snippet = (
        "from twinlab.ingest.reference_store import reference;"
        "from twinlab.models.twin import Background, SurveyResponse, Twin;"
        "from twinlab.persona.builder import build_persona;"
        f"tk={TWIN_KWARGS!r};bk={BACKGROUND_KWARGS!r};"
        "ref=reference();"
        "t=Twin(**tk, background=Background(**bk));"
        "a={i:(4 if ref.scale_points(i)==5 else 5) for i in ref.battery_item_ids};"
        "r=SurveyResponse(twin_id='UBR-TEST', answers=a);"
        "print(build_persona(t,r).persona_hash)"
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(["src", "."]),
        "PYTHONHASHSEED": "random",
    }
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == _built().persona_hash


def test_a_different_answer_gives_a_different_passage():
    """Otherwise the hash is decoration and provenance means nothing."""
    a = build_persona(_twin(), _response(answers=_answers(4, 5)))
    b = build_persona(_twin(), _response(answers=_answers(2, 2)))
    assert a.persona_hash != b.persona_hash
    assert a.text != b.text


# --------------------------------------------------------------------------- I6 losslessness


def test_every_one_of_the_37_battery_items_contributes_a_clause():
    """`docs/11` → M4: assert **per item**, not in aggregate. I6 as amended in 2.0.

    A count of 37 would pass against a builder that rendered one item twice and another not at all.
    """
    ref = reference()
    passage = _built()
    assert len(ref.battery_item_ids) == 37

    for item_id in ref.battery_item_ids:
        expected = template_for(item_id).format(
            anchor=anchor_for(ref.items[item_id].scale_id, _answers()[item_id])
        )
        assert expected in passage.text, f"{item_id} contributed no clause"
        assert item_id in passage.items_used, item_id

    assert passage.items_used == ref.battery_item_ids
    assert len(set(passage.items_used)) == 37


def test_a_template_exists_for_every_battery_item_and_for_nothing_else():
    """I6 — a field with no template raises rather than being skipped, so none may be missing."""
    ref = reference()
    assert set(TEMPLATES) == set(ref.battery_item_ids)
    assert len(TEMPLATES) == 37


def test_a_missing_template_raises_persona_template_missing(monkeypatch):
    """`docs/11` → M4: nothing is silently dropped (I6).

    A gate that cannot fail is not a gate, so the template is actually removed and the build
    re-run.
    """
    import twinlab.persona.templates as templates

    stripped = {k: v for k, v in TEMPLATES.items() if k != "PAC7"}
    monkeypatch.setattr(templates, "TEMPLATES", stripped)
    with pytest.raises(PersonaTemplateMissing, match="PAC7"):
        _built()


def test_a_missing_battery_answer_raises_rather_than_shortening_the_passage():
    """I6 — the passage is lossless over all 37 items or it is not built.

    A persona quietly missing three clauses is indistinguishable downstream from one that never had
    them, while the twin built on it would answer those items with no experience behind them.
    """
    incomplete = {k: v for k, v in _answers().items() if k not in ("PAC4", "SAT2")}
    with pytest.raises(PersonaIncomplete, match=r"PAC4"):
        build_persona(_twin(), _response(answers=incomplete))
    with pytest.raises(PersonaIncomplete, match=r"SAT2"):
        build_persona(_twin(), _response(answers=incomplete))


def test_an_out_of_range_likert_value_raises_rather_than_being_guessed():
    """A `6` on a 5-point item has no anchor. Inventing one would be the forbidden coercion."""
    with pytest.raises(PersonaTemplateMissing, match="agree5"):
        build_persona(_twin(), _response(answers={**_answers(), "PAC1": 6}))


def test_the_attention_checks_contribute_nothing_and_say_so():
    """I10 — declared exclusions, not implicit ones. They carry no experiential content."""
    assert set(EXCLUDED_FROM_PERSONA) == {"AMQ6", "ALGO5"}
    for item_id, reason in EXCLUDED_FROM_PERSONA.items():
        assert "I10" in reason
        assert item_id not in TEMPLATES
    assert all(i not in _built().items_used for i in EXCLUDED_FROM_PERSONA)


# --------------------------------------------------------------------------- I7 words not numbers


def test_the_passage_contains_no_digit_derived_from_a_likert_value():
    """`docs/11` → M4, and I7.

    Built from a row whose every free-text field is digit-free, so the scan can be absolute: a twin
    shown numbers does arithmetic instead of reasoning from experience.
    """
    text = _built().text
    digits = re.findall(r"\d", text)
    assert digits == [], f"the passage carries bare numerals: {text[:400]}"


def test_no_likert_value_renders_as_a_digit_for_any_item_at_any_value():
    """I7, exhaustively: every battery item at every value on its own scale.

    The blanket scan above depends on the fixture's answers. This one does not.
    """
    ref = reference()
    for item_id in ref.battery_item_ids:
        scale_id = ref.items[item_id].scale_id
        for value in range(1, ref.scale_points(item_id) + 1):
            clause = template_for(item_id).format(anchor=anchor_for(scale_id, value))
            assert not re.search(r"\d", clause), f"{item_id}={value} rendered a digit: {clause}"


def test_quantities_are_spelled_in_words():
    """I7 applied to every quantity, so "no bare numeral" is a property of the whole passage."""
    assert spell(0) == "zero"
    assert spell(4) == "four"
    assert spell(28) == "twenty-eight"
    assert spell(58) == "fifty-eight"
    assert spell(3.5) == "three point five"
    assert spell(100) == "one hundred"
    assert spell(342) == "three hundred and forty-two"
    text = _built().text
    assert "thirty-four years old" in text
    assert "twenty-eight months" in text
    assert "four people who depend" in text


def test_an_unspellable_quantity_raises_rather_than_printing_a_numeral():
    """I7 — the fallback is a build failure, never a digit in the passage."""
    with pytest.raises(PersonaTemplateMissing, match="extend spell"):
        spell(1000)
    with pytest.raises(PersonaTemplateMissing):
        spell(-1)


def test_a_verbatim_option_label_keeps_its_own_digits():
    """The one deliberate exception: rewriting the driver's own answer would be paraphrasing.

    `docs/DECISIONS.md` (M2, 2026-09-22). The I7 rule is about *Likert values*; a stored option
    label such as "Class 12" is the respondent's answer, not a rating.
    """
    passage = build_persona(_twin(background={"education": "Class 12"}), _response())
    assert "Class 12" in passage.text


def test_a_categorical_numeral_is_spelled():
    """`"2"` platform apps is a category whose label happens to be a numeral; it is spelled."""
    passage = build_persona(_twin(background={"platform_count": "3"}), _response())
    assert "three platform app" in passage.text
    assert "3 platform" not in passage.text


# --------------------------------------------------------------------------- I6 holdout exclusion


def test_no_holdout_item_contributes_to_the_passage():
    """`docs/11` → M4: no Part 15, 16 or 17 material reaches the persona. I6.

    The row carries the holdout answers, as a real row does — the exclusion is a property of the
    builder, not of whoever assembled the input.

    **On the acceptance criterion's wording.** `docs/11` M4 asks that "none of the 34 holdout item
    stems appears". That is satisfiable for H3's 18 but *not* for H2's 16: each H2 item `mirrors` a
    battery item and carries **the same stem by construction** (`docs/01` §3.5), and I6 requires the
    persona to carry that battery item. So the H2 half of the criterion contradicts the invariant it
    is meant to protect. What is actually at stake is that no holdout *answer* can influence the
    passage, which is asserted here and in the test below. See `docs/DECISIONS.md`.
    """
    ref = reference()
    holdouts = ref.holdout_h2_item_ids + ref.holdout_h3_item_ids
    assert len(holdouts) == 34

    passage = build_persona(_twin(), _response(answers=_answers(holdouts=True)))
    for item_id in holdouts:
        assert item_id not in passage.items_used, item_id
        assert item_id not in passage.text, f"{item_id} was named in the persona"

    # H3's stems are unique to Part 17, so for those the literal criterion does hold.
    for item_id in ref.holdout_h3_item_ids:
        assert ref.items[item_id].stem not in passage.text, f"{item_id} stem leaked"


def test_a_holdout_answer_cannot_change_the_passage():
    """I6, sharply — the test the stem scan is standing in for.

    A twin that has read its own holdout answers cannot be validated. Two rows differing **only**
    in every holdout answer must produce the byte-identical passage and the same hash.
    """
    low = build_persona(_twin(), _response(answers=_answers(holdouts=True)))
    high = _answers(holdouts=True)
    ref = reference()
    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        high[item_id] = 1 if high[item_id] != 1 else 2
    changed = build_persona(_twin(), _response(answers=high))

    assert low.text == changed.text
    assert low.persona_hash == changed.persona_hash
    # And the same passage the battery alone produces, with no holdouts in the row at all.
    assert low.persona_hash == _built().persona_hash


def test_no_holdout_item_has_a_persona_template():
    """I6 — there is no template that *could* render holdout material."""
    ref = reference()
    for item_id in ref.holdout_h2_item_ids + ref.holdout_h3_item_ids:
        assert item_id not in TEMPLATES
        with pytest.raises(PersonaTemplateMissing):
            template_for(item_id)


def test_the_holdout_parts_are_declared():
    """I6 — Part 15 is the human manipulation check; 16 and 17 are the holdouts."""
    assert HOLDOUT_PARTS == frozenset({15, 16, 17})


def test_no_h3_version_code_appears_in_the_passage():
    """I6 and `docs/03` §8 — the twin never sees a version code, least of all a holdout's."""
    ref = reference()
    passage = build_persona(_twin(), _response(answers=_answers(holdouts=True)))
    for code in ref.h3_version_codes:
        assert code not in passage.text


# --------------------------------------------------------------------------- per-scale anchors


def test_anchor_clauses_are_per_scale():
    """`docs/11` → M4, and `docs/03` §7.1.

    Using the 7-point wording for a 5-point item would render a `4` as "I agree" in one block and
    "I neither agree nor disagree" in another — the same number meaning two different things inside
    one passage.
    """
    assert anchor_for("agree5", 4) == "I agree"
    assert anchor_for("agree7", 4) == "I neither agree nor disagree"
    assert anchor_for("agree5", 4) != anchor_for("agree7", 4)


def test_every_scale_has_an_anchor_for_every_point_and_no_more():
    """A missing anchor would raise mid-build; a spare one would be an unreachable wording."""
    ref = reference()
    for scale_id, scale in ref.scales.items():
        anchors = ANCHOR_CLAUSES[scale_id]
        assert sorted(anchors) == list(range(1, scale.points + 1)), scale_id
    assert set(ANCHOR_CLAUSES) == set(ref.scales)


def test_a_four_renders_differently_on_a_five_point_and_a_seven_point_item():
    """The same assertion, through the builder rather than the table."""
    ref = reference()
    assert ref.scale_points("PAC1") == 5 and ref.scale_points("SAT1") == 7
    passage = build_persona(
        _twin(), _response(answers={**_answers(), "PAC1": 4, "SAT1": 4})
    ).text
    assert "I agree that the app's algorithm gives out work intelligently." in passage
    assert "I neither agree nor disagree that, all in all, I am satisfied with my job." in passage


def test_the_extent_and_likelihood_scales_read_as_phrases_not_agreement():
    """`extent7` and `likely7` items are not agreement items and must not borrow its wording."""
    passage = build_persona(_twin(), _response(answers={**_answers(), "FAIR1": 7, "TURN3": 1})).text
    assert "to a very large extent" in passage
    assert "not at all likely" in passage


# --------------------------------------------------------------------------- whys and own words


def test_part_14_own_words_close_the_passage_verbatim_from_background():
    """`docs/11` → M4: Part 14 appears verbatim as the closing section, from `twins.background`.

    It has no `item_id` and the register is frozen, so without this the persona silently loses the
    driver's own words.
    """
    words = {
        "OWN1": "A day when the app gives long trips near my home.",
        "OWN5": "My wife and my parents depend on me; I want my own car.",
    }
    passage = build_persona(_twin(background={"own_words": words}), _response()).text
    heading = dict(SECTION_ORDER)["own_words"]
    last_block = passage.rstrip().split("\n\n")[-1]
    assert last_block.startswith(heading), "own words must close the passage"
    for text in words.values():
        assert text in passage, "Part 14 must be verbatim"


def test_the_why_probes_are_carried_word_for_word():
    """`docs/03` §7.1 — whys verbatim, never paraphrased."""
    whys = {
        "WHY_CONTROL": "The app decides everything; I only drive where it says.",
        "WHY_SATISFACTION": "The money is alright but the hours are long.",
        "WHY_OTHER_WORK": "I have no other skill, so leaving is hard.",
    }
    passage = build_persona(_twin(), _response(whys=whys)).text
    for text in whys.values():
        assert text in passage


def test_a_non_english_answer_keeps_the_original_with_a_bracketed_translation():
    """`docs/03` §7.1 — the original is kept, and the translation sits beside it, not instead."""
    passage = build_persona(
        _twin(),
        _response(
            whys={"WHY_CONTROL": "ऐप ही सब तय करता है"},
            translations={"WHY_CONTROL": "The app decides everything"},
            language="hi",
        ),
    ).text
    assert "ऐप ही सब तय करता है" in passage
    assert "[in English: 'The app decides everything']" in passage


def test_an_unknown_why_probe_or_own_words_id_is_rejected():
    """Losslessness cuts both ways: an unmapped key must not be quietly ignored."""
    with pytest.raises(ValueError, match="unknown why-probe"):
        _response(whys={"WHY_SOMETHING": "text"})
    with pytest.raises(ValueError, match="unknown own-words"):
        _response(own_words={"OWN9": "text"})
    # One probe per battery item since 2026-10-08, plus Part 14's five own-words fields.
    assert len(WHY_PROBE_IDS) == 37 and len(OWN_WORDS_IDS) == 5


def test_an_absent_optional_field_is_skipped_without_error():
    """An unanswered optional question has nothing to carry — unlike a battery item."""
    bare = Twin(twin_id="UBR-TEST", city="Mumbai", service="cab")
    passage = build_persona(bare, _response()).text
    assert "years old" not in passage
    assert "I drive in Mumbai." in passage


# --------------------------------------------------------------------------- shape and order


def test_the_sections_appear_in_the_fixed_order():
    """`docs/03` §7.1 — the order is part of the contract, not a presentation choice."""
    passage = build_persona(
        _twin(background={"own_words": {"OWN1": "A quiet morning near home."}}),
        _response(whys={"WHY_CONTROL": "The app decides."}),
    ).text
    headings = [heading for _, heading in SECTION_ORDER]
    positions = [passage.find(h) for h in headings]
    present = [p for p in positions if p >= 0]
    assert present == sorted(present)
    assert len(present) == len(headings), "every section should have content in this fixture"


def test_the_passage_is_first_person_throughout():
    """`docs/03` §7.1 — the passage reads as the driver speaking."""
    passage = _built().text
    headings = tuple(heading for _, heading in SECTION_ORDER)
    body = [
        line for line in passage.split("\n") if line and not line.startswith(headings)
    ]
    assert body, "expected clause lines"
    for line in body:
        assert re.search(r"\bI\b|\bmy\b|\bme\b", line), line


def test_the_clause_count_and_items_used_are_reported():
    """The passage is auditable: what went in is recorded beside the hash."""
    passage = _built()
    assert passage.clause_count >= 37
    assert passage.template_version == "v2"
    assert passage.twin_id == "UBR-TEST"


def test_the_builder_reaches_no_model_and_no_network():
    """`docs/03` §7.2 — deterministic, Python only, no LLM.

    A model-written persona would be a paraphrase, and a paraphrase is lossy in a way nobody can
    audit. Asserted at the source level so it cannot quietly stop being true.
    """
    import ast

    for name in ("builder.py", "templates.py"):
        path = REPO_ROOT / "src" / "twinlab" / "persona" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for banned in ("httpx", "requests", "openai", "pydantic_ai", "supabase", "random"):
            assert banned not in imported, f"persona/{name} imports {banned}"
