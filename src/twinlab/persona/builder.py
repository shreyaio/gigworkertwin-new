"""The persona passage builder. Deterministic, Python only, no LLM. `docs/03` §7.

Contract, in full:

* **Lossless over the battery** (I6, as amended in 2.0 — there is no item-level holdout). All 37
  battery items contribute a clause. A field with no template raises
  :class:`PersonaTemplateMissing`; a battery item with no *answer* raises
  :class:`PersonaIncomplete`. Neither is ever silently skipped.
* **First person, plain register.** The passage reads as the driver speaking.
* **Words, not numbers** (I7). Every quantity — Likert answers, ages, hours, dependants — is spelled
  out, so no bare numeral can be mistaken for a rating. The only digits that may appear are inside
  a driver's own verbatim words, which are never edited.
* **Whys verbatim.** Never paraphrased, never translated in place; a non-English answer carries the
  original with a bracketed translation.
* **Fixed order.** identity → work context → household and dependence → how the app manages me →
  how the app guides me → fairness → clarity → satisfaction → staying → working around it →
  leaving → own words.
* **Excludes Parts 15, 16 and 17 absolutely** (I6). Part 17 is the fidelity holdout; a twin that has
  read its own holdout answers cannot be validated.
* **Deterministic and hashable.** Same row in, byte-identical passage out.

**Why no LLM here** (`docs/03` §7.2): a model-written persona is a paraphrase, and a paraphrase is
lossy in a way nobody can audit. Determinism is also what makes the passage hashable, and the hash
is what ties a result back to the exact text that produced it (I11).
"""

from __future__ import annotations

import hashlib

from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.twin import (
    OWN_WORDS_IDS,
    WHY_PROBE_ANCHOR,
    WHY_PROBE_IDS,
    PersonaPassage,
    SurveyResponse,
    Twin,
)
from twinlab.persona.templates import (
    BLOCK_SECTION,
    EXCLUDED_FROM_PERSONA,
    HOUSEHOLD_TEMPLATES,
    IDENTITY_TEMPLATES,
    OWN_WORDS_PROMPTS,
    SECTION_ORDER,
    TEMPLATE_VERSION,
    WHY_PROBE_PROMPTS,
    WORK_CONTEXT_TEMPLATES,
    PersonaTemplateMissing,
    anchor_for,
    template_for,
)

#: Parts whose content never enters the passage. 15 is the human manipulation check; 16 and 17 are
#: the holdouts (I6).
HOLDOUT_PARTS: frozenset[int] = frozenset({15, 16, 17})


class PersonaIncomplete(ValueError):
    """A battery item has no answer, so the passage cannot be lossless over the battery.

    Raised rather than building a shorter passage. I6 as amended in 2.0 requires all 37 items to
    contribute, and a persona quietly missing three clauses is indistinguishable downstream from
    one that never had them — while the twin built on it would answer those items with no
    experience behind them. A respondent whose row is incomplete should not have become a twin;
    this is where that shows up.
    """


_UNITS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
#: Index is the tens digit; 0 and 1 are unreachable (handled by `_UNITS`).
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def spell(n: float | int) -> str:
    """Spell a quantity in words, so the passage carries no bare numeral (I7).

    Handles 0–999 and one decimal place, which covers every quantity the survey collects — age,
    months of tenure, hours a week, dependants, years driving. Anything outside that range raises
    rather than falling back to digits.

    I7 only requires this of Likert values. Doing it for every quantity makes "no bare numeral" a
    property of the whole passage, so the I7 test needs no exceptions.
    """
    if isinstance(n, float) and not n.is_integer():
        whole, frac = str(round(n, 1)).split(".")
        return f"{spell(int(whole))} point {_UNITS[int(frac)]}"
    n = int(n)
    if n < 0 or n > 999:
        raise PersonaTemplateMissing(
            f"cannot spell {n} in words; extend spell() rather than printing a numeral into the "
            "passage (I7)"
        )
    if n < 20:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        word = _TENS[tens]
        return word if unit == 0 else f"{word}-{_UNITS[unit]}"
    hundreds, rest = divmod(n, 100)
    head = f"{_UNITS[hundreds]} hundred"
    return head if rest == 0 else f"{head} and {spell(rest)}"


def _wordify(value: object) -> str:
    """Render an answer value as words.

    A categorical answer that is itself a numeral — `"2"` for the number of platform apps — is
    spelled too, so the passage holds no bare digit. A verbatim option label that happens to
    contain digits, such as `"Class 12"`, keeps them: rewriting the driver's own answer would be
    paraphrasing.
    """
    if isinstance(value, (int, float)):
        return spell(value)
    text = str(value)
    if text.isdigit():
        return spell(int(text))
    return text


def _verbatim(text: str, translation: str | None) -> str:
    """A driver's own words, whole. A translation is bracketed beside the original, not instead."""
    quoted = f"'{text.strip()}'"
    if translation:
        return f"{quoted} [in English: '{translation.strip()}']"
    return quoted


class PersonaBuilder:
    """Builds one passage. Holds no state between builds beyond the reference data."""

    def __init__(self, ref: ReferenceData | None = None) -> None:
        self.ref = ref or reference()

    def build(self, twin: Twin, response: SurveyResponse) -> PersonaPassage:
        sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}
        items_used: list[str] = []

        self._identity(twin, sections)
        self._work_context(twin, sections)
        self._household(twin, sections)
        self._battery(response, sections, items_used)
        self._own_words(twin, response, sections)

        blocks: list[str] = []
        for key, heading in SECTION_ORDER:
            lines = sections[key]
            if not lines:
                continue
            blocks.append(f"{heading}\n" + " ".join(lines))
        text = "\n\n".join(blocks) + "\n"

        clause_count = sum(len(v) for v in sections.values())
        return PersonaPassage(
            twin_id=twin.twin_id,
            text=text,
            persona_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            template_version=TEMPLATE_VERSION,
            clause_count=clause_count,
            items_used=items_used,
        )

    # --- sections ---------------------------------------------------------

    def _render_fields(
        self,
        templates: dict[str, str],
        values: dict[str, object],
        section: str,
        sections: dict[str, list[str]],
    ) -> None:
        """Render a block of optional fields in template order.

        ``None`` and empty string are skipped, which is not a loss: an unanswered optional question
        has nothing to carry. A *battery* item is different and is handled in :meth:`_battery`,
        where a missing answer raises.
        """
        for field, template in templates.items():
            value = values[field]
            if value is None or value == "":
                continue
            sections[section].append(template.format(value=_wordify(value)))

    def _identity(self, twin: Twin, sections: dict[str, list[str]]) -> None:
        self._render_fields(
            IDENTITY_TEMPLATES,
            {
                "age": twin.age,
                "gender": twin.gender,
                "city": twin.city,
                "service": twin.service,
            },
            "identity",
            sections,
        )

    def _work_context(self, twin: Twin, sections: dict[str, list[str]]) -> None:
        bg = twin.background
        self._render_fields(
            WORK_CONTEXT_TEMPLATES,
            {
                "tenure_months": twin.tenure_months,
                "hours_per_week": twin.hours_per_week,
                "platform_count": bg.platform_count,
                "other_apps": bg.other_apps,
                "vehicle_arrangement": bg.vehicle_arrangement,
                "years_driving_before_uber": bg.years_driving_before_uber,
            },
            "work_context",
            sections,
        )

    def _household(self, twin: Twin, sections: dict[str, list[str]]) -> None:
        bg = twin.background
        self._render_fields(
            HOUSEHOLD_TEMPLATES,
            {
                "dependants": bg.dependants,
                "other_household_income": bg.other_household_income,
                "education": bg.education,
            },
            "household",
            sections,
        )

    def _battery(
        self,
        response: SurveyResponse,
        sections: dict[str, list[str]],
        items_used: list[str],
    ) -> None:
        """One clause per battery item, in item order. Nothing is skipped, silently or otherwise."""
        missing = [i for i in self.ref.battery_item_ids if i not in response.answers]
        if missing:
            raise PersonaIncomplete(
                f"{response.twin_id}: no answer for battery item(s) {missing}. The persona must be "
                "lossless over all 37 items (I6); it is not built from a partial row."
            )

        for item_id in self.ref.battery_item_ids:
            item = self.ref.items[item_id]
            if item.part in HOLDOUT_PARTS:  # pragma: no cover — the battery excludes holdouts
                raise PersonaTemplateMissing(
                    f"{item_id} is Part {item.part} holdout material and must not reach a "
                    "persona (I6)"
                )
            if item_id in EXCLUDED_FROM_PERSONA:  # pragma: no cover — not in the battery
                continue
            if item.scale_id is None:
                raise PersonaTemplateMissing(f"{item_id} has no scale")
            clause = template_for(item_id).format(
                anchor=anchor_for(item.scale_id, response.answers[item_id])
            )
            why = self._why_for(item_id, response)
            sections[BLOCK_SECTION[item.block]].append(f"{clause} {why}" if why else clause)
            items_used.append(item_id)

    def _why_for(self, item_id: str, response: SurveyResponse) -> str:
        """This item's own why answer, verbatim, as the tail of its clause.

        `SURVEY_SCALES_AND_WHY_PROBES.md` §4.2 fixes this shape — the why belongs to the sentence
        its rating is in. The whys used to be appended at the end of the block's section instead,
        which was readable while only three existed; with one probe per battery item it would put
        eleven unattributed "In my own words: …" clauses in a row at the end of the PAC section,
        and nothing in the passage would say which rating each explained.
        """
        for probe_id in self._probes_for(item_id):
            text = response.whys.get(probe_id)
            if text:
                return (
                    f"{WHY_PROBE_PROMPTS[probe_id]} "
                    f"{_verbatim(text, response.translations.get(probe_id))}"
                )
        return ""

    def _probes_for(self, item_id: str) -> list[str]:
        """The probe ids anchored to one item. At most one is ever answered — the schema has one
        `why_text` column per item — but the lookup is a list so an anchor table with two entries
        for one item fails visibly in a test rather than silently preferring whichever came first.
        """
        return [p for p in WHY_PROBE_IDS if WHY_PROBE_ANCHOR[p] == item_id]

    def _own_words(
        self, twin: Twin, response: SurveyResponse, sections: dict[str, list[str]]
    ) -> None:
        """Part 14, verbatim, as the closing section. `docs/03` §7.1.

        Read from `twins.background.own_words`, which is where Part 14 lives because it has no
        `item_id` and the register is frozen. ``response.own_words`` is accepted as well so an
        intake path that carries them there does not silently lose them; the two are merged with
        the background winning, because that is the stored copy a rebuild would read.
        """
        merged = {**response.own_words, **twin.background.own_words}
        translations = {**response.translations, **twin.background.translations}
        for own_id in OWN_WORDS_IDS:
            text = merged.get(own_id)
            if not text:
                continue
            sections["own_words"].append(
                f"{OWN_WORDS_PROMPTS[own_id]} {_verbatim(text, translations.get(own_id))}"
            )


def build_persona(
    twin: Twin, response: SurveyResponse, ref: ReferenceData | None = None
) -> PersonaPassage:
    """Build one persona passage. Same row in, byte-identical passage out."""
    return PersonaBuilder(ref).build(twin, response)
