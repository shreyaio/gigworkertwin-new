"""The Checker — five gates. `docs/03` §5. Implements I3, and enforces I5.

Every render passes before any twin sees it. Fail any gate → re-render **once** → then halt that
cell, mark the run `failed`, log it, and continue to the next code. **An unverified variant never
reaches a twin.**

Four of the five gates are deterministic and live here. Only **coverage** consults a model, one
call per commitment at temperature 0.0, through `agents/checker.py`.

**Gate 2 is asymmetric on purpose.** Coverage failing means the stimulus is weaker than intended:
bad, recoverable, and detectable in the data. Containment failing means two cells are no longer
distinguishable, which silently destroys a lever comparison and is **not** detectable downstream.
One containment hit fails the cell; there is no threshold and no tolerance.

Nothing in this module repairs a paragraph. A gate that could rewrite its input to pass would
convert a detectable failure into an undetectable fabrication, which is the one thing `CLAUDE.md`
forbids above all others. The gates measure; the cell fails.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from twinlab.models.variant import (
    DIAL_ZERO_TEXT,
    CheckerReport,
    CoverageProbe,
    CoverageVerdict,
    LeverParagraph,
)

if TYPE_CHECKING:
    from twinlab.agents.registry import ModelClient
    from twinlab.ingest.reference_store import ReferenceData
    from twinlab.models.variant import RenderedVariant

#: Words carrying no topic. Excluded before a signature is formed so the distinctive vocabulary of
#: a commitment is its *content*, not its grammar. Frozen: changing it changes every containment
#: verdict, so it is a constant here rather than config.
STOPWORDS: frozenset[str] = frozenset("""
a an the and or but if of to in on at for from by with without as is are was were be been being
this that these those it its his her their our your you we they he she i not no nor so than then
there here what which who whom whose when where why how all any both each few more most other some
such only own same too very can will just should now does do did doing have has had having would
could may might must shall about into over under again further once during before after above below
up down out off them him us me my mine yours ours theirs
""".split())

class CheckerMisuse(RuntimeError):
    """A report asked to grade a paragraph it was given no band for.

    Not a gate failure — a wiring failure. From `style_version: v3` the word band is resolved per
    `(lever, dial)` from the commitment count, so :func:`build_report` cannot fall back to a global
    pair of scalars: there is no longer one to fall back to. Grading a paragraph against a guessed
    band, or skipping gate 3 because no band arrived, would both let an ungraded stimulus reach a
    twin. Raising is the only safe outcome (I3).
    """


_WORD = re.compile(r"[a-z0-9][a-z0-9'-]*")
_SENTENCE = re.compile(r"[.!?]+")
_VOWELS = re.compile(r"[aeiouy]+")


# --------------------------------------------------------------------------- tokenising


def content_words(text: str) -> list[str]:
    """Lower-cased content words, in order. Punctuation and stopwords dropped."""
    return [w for w in _WORD.findall(text.lower()) if w not in STOPWORDS]


def bigrams(text: str) -> set[tuple[str, str]]:
    """Adjacent content-word pairs.

    A **pair**, not a single word, is the unit of containment. A single-word rule was measured
    against the specification's own known-good `01000` render (`docs/03` §4.2) and flagged 16 of
    the 27 forbidden commitments on a paragraph the specification calls correct — "uber", "trip",
    "app", "claim" and "written" are shared vocabulary, not distinctive vocabulary. The pair rule
    passes that render with zero hits and still catches a verbatim leak. See `docs/DECISIONS.md`.
    """
    words = content_words(text)
    return set(zip(words, words[1:], strict=False))


def signature(forbidden_text: str, allowed_text: str) -> set[tuple[str, str]]:
    """The content bigrams that belong to ``forbidden_text`` and to nothing the cell may say.

    Subtracting the allowed text is what makes the gate specific: a commitment the cell *does*
    carry shares vocabulary with one it does not, and only the difference identifies a leak.

    Never empty for any of the 285 (lever, dial, forbidden) combinations over the frozen reference
    data — an empty signature would be a commitment that could leak undetected, so
    `tests/test_m5_render_checker.py` asserts that across all of them.
    """
    return bigrams(forbidden_text) - bigrams(allowed_text)


# --------------------------------------------------------------------------- gate 3 helpers


def word_count(text: str) -> int:
    """Whitespace-separated tokens carrying at least one letter or digit.

    A bare em dash between two clauses is punctuation, not a word, and a plain ``split()`` counts
    it as one — which would make an identical sentence pass or fail on its dashes.

    **The specification's own exemplar did not satisfy its own band.** The `01000` paragraph in
    `docs/03` §4.2 and `additional_data/worked_out_eg.txt` is called 66 words by both; it measures
    **71** by this rule (73 by naive `split()`), against a band that was 45–70. The researcher
    widened the band to **45–75** on 2026-09-29 rather than have the gate reject the one piece of
    known-good output in the repository. The band lives in `config/style_contract.yaml`; this
    function reads it and never hard-codes it. From `style_version: v3` it is resolved per
    `(lever, dial)` from the commitment count and the floor is 45, so the exemplar stays
    admissible. See `docs/DECISIONS.md`.
    """
    return len([t for t in text.split() if _WORD.search(t.lower())])


def syllables(word: str) -> int:
    """Vowel groups, less a silent trailing ``e``, minimum one.

    The standard heuristic. Implemented here rather than taken from a dependency because the
    reading-grade band is a gate: a library version bump that changed a syllable count would move
    every cell's grade, and `requirements.txt` is the wrong place to record a research threshold.
    """
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count = len(_VOWELS.findall(word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def flesch_kincaid(text: str) -> float:
    """Flesch–Kincaid grade level. Band `[4.0, 16.0]` from `config/style_contract.yaml`.

    Returns ``0.0`` for text with no words or no sentences rather than dividing by zero; such a
    text fails the word-count gate anyway, so the grade is never the only thing standing between
    an empty render and a twin.
    """
    words = _WORD.findall(text.lower())
    sentences = [s for s in _SENTENCE.split(text) if s.strip()]
    if not words or not sentences:
        return 0.0
    total_syllables = sum(syllables(w) for w in words)
    return (
        0.39 * (len(words) / len(sentences))
        + 11.8 * (total_syllables / len(words))
        - 15.59
    )


def term_hits(text: str, terms: list[str]) -> list[str]:
    """Forbidden terms or intensifiers present, matched whole-word and case-insensitively.

    `docs/02` §3.5: `forbidden_terms` apply to **everything a twin can see**. A twin told it is in
    a study answers like a participant, not like a driver.
    """
    lowered = text.lower()
    hits: list[str] = []
    for term in terms:
        pattern = r"\b" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, lowered):
            hits.append(term)
    return hits


# --------------------------------------------------------------------------- the gates


def distinctive_signatures(
    forbidden: dict[str, str], allowed_text: str
) -> dict[str, set[tuple[str, str]]]:
    """Each forbidden commitment's signature, **less every pair it shares with another one.**

    `docs/DECISIONS.md`, 2026-09-30 (researcher decision). :func:`signature` subtracts what the
    cell *may* say, which makes a pair specific to the forbidden set; this subtracts what the
    forbidden set shares with itself, which makes a pair specific to **one** commitment.

    Without it, gate 2 failed almost every cell on one pair. On `11010` the `L4` paragraph was
    flagged for leaking `3.1.b`, `3.1.c`, `5.1.b` and `5.2.b`, and every hit was ``("driver",
    "app")`` — a pair that occurs in four different commitments because *Driver app* is Uber's own
    name for the thing. A pair that cannot say **which** commitment leaked is not evidence that
    one did; it is shared vocabulary. That is the same argument `docs/DECISIONS.md` already used
    on 2026-09-22 to reject the single-word rule in favour of pairs, applied one level up.

    **This narrows the gate and the narrowing is recorded, not hidden.** A commitment whose every
    pair is shared has an empty distinctive signature and could leak undetected;
    `tests/test_m5_render_checker.py` pins how many of the 285 (lever, dial, forbidden)
    combinations that is, so the number cannot grow without a test failing.
    """
    raw = {
        identifier: signature(text, allowed_text)
        for identifier, text in forbidden.items()
    }
    seen: dict[tuple[str, str], int] = {}
    for pairs in raw.values():
        for pair in pairs:
            seen[pair] = seen.get(pair, 0) + 1
    return {
        identifier: {pair for pair in pairs if seen[pair] == 1}
        for identifier, pairs in raw.items()
    }


def containment_hits(
    paragraph: str,
    forbidden: dict[str, str],
    allowed: dict[str, str],
) -> list[str]:
    """Gate 2. The ids of every forbidden commitment detectable in ``paragraph``. Empty = pass.

    ``forbidden`` and ``allowed`` map an id to its commitment text: for a live cell, every
    commitment outside this lever's set plus the three already-met criteria, against this lever's
    own commitments. For the sham, the allowed set **is** the existing policy it announces
    (`docs/DECISIONS.md`, 2026-09-22) — the gate still fails on any real gap commitment, because a
    gap's distinctive vocabulary is by definition absent from the policy it falls short of.

    A hit needs a pair from that commitment's **distinctive** signature
    (:func:`distinctive_signatures`): a pair shared with another forbidden commitment names no
    particular leak.

    **One hit fails the cell.** This function returns every hit so the failure is inspectable, not
    because some number of them is tolerable.
    """
    present = bigrams(paragraph)
    distinctive = distinctive_signatures(forbidden, " ".join(allowed.values()))
    return [
        identifier
        for identifier in sorted(forbidden)
        if distinctive[identifier] & present
    ]


def dial_zero_identical(paragraphs: dict[str, LeverParagraph], dials: dict[str, int]) -> bool:
    """Gate 4. Every dial-0 lever carries the byte-identical fixed string. I5.

    A byte comparison against the constant, not a similarity test. `"No change from today"` without
    the full stop is a different stimulus in four cells out of five and would not be caught by
    anything downstream.
    """
    return all(
        paragraphs[lever].text == DIAL_ZERO_TEXT
        for lever, dial in dials.items()
        if dial == 0
    )


def no_dial_zero_line(paragraphs: dict[str, LeverParagraph]) -> bool:
    """Gate 5's distinctive half: the sham carries **no** `"No change from today."` line.

    A sham with a null line would be recognisable as a control, and a twin that can tell it is
    looking at a control is not measuring the demand characteristic the cell exists to measure.
    """
    return all(p.text.strip() != DIAL_ZERO_TEXT for p in paragraphs.values())


def check_invariance(
    text: str, style: dict
) -> tuple[bool, float, list[str]]:
    """Gate 3. ``(in_band, reading_grade, violations)``.

    ``in_band`` is the word count alone. The reading grade and the forbidden vocabulary are
    reported separately so a failure names which of the three went wrong.

    ``style`` must carry ``word_min`` and ``word_max`` already **resolved** for the brief being
    graded — :func:`variant.render.resolved_style` is what produces it, and it is the same dict
    the design agent was shown. The loaded contract does not carry those two keys from
    `style_version: v3`, so passing it raw is a :class:`KeyError` rather than a silently wrong
    band.
    """
    count = word_count(text)
    in_band = style["word_min"] <= count <= style["word_max"]
    grade = flesch_kincaid(text)
    violations: list[str] = []
    if not style["reading_grade_min"] <= grade <= style["reading_grade_max"]:
        violations.append(
            f"reading grade {grade:.1f} outside "
            f"[{style['reading_grade_min']}, {style['reading_grade_max']}]"
        )
    for term in term_hits(text, list(style.get("forbidden_terms", []))):
        violations.append(f"forbidden term {term!r}")
    for term in term_hits(text, list(style.get("forbidden_intensifiers", []))):
        violations.append(f"forbidden intensifier {term!r}")
    return in_band, grade, violations


# --------------------------------------------------------------------------- the report


def build_report(
    *,
    paragraphs: dict[str, LeverParagraph],
    dials: dict[str, int],
    style: dict,
    coverage: dict[str, bool],
    containment: list[str],
    bands: dict[str, tuple[int, int]] | None = None,
    is_sham: bool = False,
) -> CheckerReport:
    """The five gates combined into one report. `docs/03` §5.

    ``passed`` is a conjunction and nothing weakens it: every commitment entailed, no containment
    hit, every paragraph inside the band and the grade band with no forbidden vocabulary, every
    dial-0 line byte-identical, and — for the sham — no null line anywhere.

    A ``cannot_render`` paragraph fails the report. `docs/02` §4.1: the cell is marked `failed` and
    logged, and is **never** filled with a generic paragraph.
    """
    notes: list[str] = []
    in_band = True
    grades: list[float] = []
    #: Gate-3 failures other than the word band, and any refusal. Tracked as a flag rather than
    #: inferred from `notes`, so a reworded note can never quietly turn a failure into a pass.
    style_ok = True

    for lever in paragraphs:
        paragraph = paragraphs[lever]
        if paragraph.status != "ok":
            in_band = False
            style_ok = False
            notes.append(f"{lever}: {paragraph.status} — {paragraph.reason}")
            continue
        # The fixed dial-0 string is 4 words and is exempt from the band by construction: it is a
        # constant, never a render, and gate 4 is what holds it to account (I5).
        if dials.get(lever) == 0:
            continue
        band = (bands or {}).get(lever)
        if band is None:
            raise CheckerMisuse(
                f"no word band was supplied for {lever}, so gate 3 cannot grade its paragraph. "
                "From style_version v3 the band is resolved per (lever, dial) from the "
                "commitment count — pass `bands={lever: variant.render.band_for(n, style)}` for "
                "every lever being graded."
            )
        lever_style = {**style, "word_min": band[0], "word_max": band[1]}
        lever_in_band, grade, violations = check_invariance(paragraph.text, lever_style)
        grades.append(grade)
        # Word band and reading grade are reported, not enforced (researcher decision, 2026-10-04):
        # they measure style, not content, and a style miss does not fail the cell.
        if not lever_in_band:
            notes.append(
                f"info: {lever}: {word_count(paragraph.text)} words outside [{band[0]}, {band[1]}]"
            )
        for violation in violations:
            # Reading grade and forbidden *terms* are warnings (researcher decision, 2026-10-04): the
            # design prompt still tells the agent to avoid them, and the report says when it did not.
            # Forbidden *intensifiers* remain enforced.
            if violation.startswith(("reading grade", "forbidden term")):
                notes.append(f"info: {lever}: {violation}")
                continue
            style_ok = False
            notes.append(f"{lever}: {violation}")

    zero_ok = dial_zero_identical(paragraphs, dials)
    if not zero_ok:
        notes.append("a dial-0 lever does not carry the fixed string (I5)")

    sham_ok: bool | None = None
    if is_sham:
        sham_ok = no_dial_zero_line(paragraphs)
        if not sham_ok:
            notes.append("the sham carries a 'No change from today.' line")

    uncovered = sorted(g for g, ok in coverage.items() if not ok)
    if uncovered:
        notes.append(f"not entailed: {', '.join(uncovered)}")
    if containment:
        # Recorded, not enforced (researcher decision, 2026-10-04): two predefined commitments can
        # legitimately share wording, so a hit is reported for the reader and does not fail the cell.
        notes.append(f"info: containment hit (recorded, not enforced): {', '.join(containment)}")

    # Every violation noted above is fatal. There is no gate whose failure is a warning.
    passed = (
        not uncovered
        and style_ok
        and zero_ok
        and (sham_ok is not False)
    )

    return CheckerReport(
        coverage=coverage,
        containment=containment,
        word_count=sum(word_count(p.text) for p in paragraphs.values()),
        in_band=in_band,
        reading_grade=round(max(grades), 3) if grades else 0.0,
        dial_zero_identical=zero_ok,
        sham_indistinguishable=sham_ok,
        passed=passed,
        notes="; ".join(notes),
    )


def verdicts_to_coverage(verdicts: dict[str, CoverageVerdict]) -> dict[str, bool]:
    """``gap_id → entailed``. A missing verdict is **not** entailed — uncertainty fails closed."""
    return {gap_id: verdict.entailed for gap_id, verdict in verdicts.items()}


# --------------------------------------------------------------------------- orchestration


async def check_variant(
    variant: RenderedVariant,
    *,
    client: ModelClient,
    style: dict | None = None,
    ref: ReferenceData | None = None,
) -> CheckerReport:
    """All five gates over one assembled cell. `docs/03` §5. **Every render passes here** (I3).

    Coverage is the only model step: one call per commitment, so a live cell costs as many probes as
    it has commitments and `00000` costs none. Containment, invariance, null identity and the sham
    check are deterministic and cost nothing.

    The dial-0 levers are not probed and not scanned. There is nothing to entail and nothing that
    could leak: the text is a constant, and gate 4 is what holds it to account.
    """
    from twinlab.agents.checker import run_coverage_probe
    from twinlab.agents.registry import live_agent
    from twinlab.ingest.reference_store import reference
    from twinlab.orchestrator.odometer import SHAM_CODE
    from twinlab.variant.lookup import commitments_for_lever, lookup
    from twinlab.variant.render import forbidden_for, load_style_contract, sham_allowed

    style = style or load_style_contract()
    ref = ref or reference()
    # The **live** config (WP-8). The Checker cannot be disabled — `services.agent_config`
    # refuses that at save time, naming I3 — so this uses `live_agent` and lets an `AgentDisabled`
    # propagate: a coverage probe that did not run must never look like one that passed.
    cfg = live_agent("checker")
    is_sham = variant.version_code == SHAM_CODE

    if is_sham:
        from twinlab.variant.render import sham_briefs

        briefs = sham_briefs(ref, style)
        # Coverage is per lever: each sham paragraph must entail the existing policy IT announces.
        coverage_by_lever = {lever: dict(b.commitments) for lever, b in briefs.items()}
        # Containment is scoped to the whole of the existing policy the cell announces, not to one
        # lever's share of it (`docs/DECISIONS.md`, 2026-09-22): a sham paragraph echoing another
        # sham lever's policy is still only existing policy, which is what the cell may say.
        # Read off the brief rather than recomputed: the sham's band is its lever's *dial-1*
        # band, not a function of the slots it announces (`render._sham_band_n`), and that
        # decision must live in exactly one place or the agent and the gate will disagree.
        sham_bands = {
            lever: (b.style_contract["word_min"], b.style_contract["word_max"])
            for lever, b in briefs.items()
        }
        whole_allowed = sham_allowed(ref)
        allowed_by_lever = {lever: whole_allowed for lever in variant.paragraphs}
        # The sham may say the existing policy and nothing else, so every real gap is forbidden.
        forbidden_by_lever = {
            lever: {gap_id: ref.gaps[gap_id].commitment for gap_id in sorted(ref.gaps)}
            for lever in variant.paragraphs
        }
    else:
        spec = lookup(variant.version_code, ref)
        allowed_by_lever = {
            lever: commitments_for_lever(spec, lever) for lever in variant.paragraphs
        }
        coverage_by_lever = allowed_by_lever
        forbidden_by_lever = {
            lever: forbidden_for(spec, lever, ref) for lever in variant.paragraphs
        }

    # Gate 3's band, per lever. For a live cell it is a function of that lever's own commitment
    # count, taken from `coverage_by_lever` rather than re-derived so the band the Checker grades
    # against and the band the design agent was shown cannot come from two different counts. For
    # the sham it comes off the brief, for the reason given above.
    from twinlab.variant.render import band_for

    if is_sham:
        bands = dict(sham_bands)
    else:
        bands = {
            lever: band_for(len(coverage_by_lever[lever]), style)
            for lever in variant.paragraphs
        }

    coverage: dict[str, bool] = {}
    containment: list[str] = []

    for lever, paragraph in variant.paragraphs.items():
        if variant.dials.get(lever) == 0 or paragraph.status != "ok":
            continue
        for identifier, commitment in sorted(coverage_by_lever[lever].items()):
            verdict = await run_coverage_probe(
                cfg,
                CoverageProbe(
                    gap_id=identifier, commitment=commitment, paragraph=paragraph.text
                ),
                client,
            )
            coverage[identifier] = verdict.entailed
        for hit in containment_hits(
            paragraph.text, forbidden_by_lever[lever], allowed_by_lever[lever]
        ):
            if hit not in containment:
                containment.append(hit)

    return build_report(
        paragraphs=variant.paragraphs,
        dials=variant.dials,
        style=style,
        coverage=coverage,
        containment=containment,
        bands=bands,
        is_sham=is_sham,
    )
