"""Assembling a cell's five paragraphs. `docs/03` §4 and §6. Implements I4, enforces I5.

A version code's five paragraphs are assembled from a pool of exactly **11 strings**: ten non-zero
lever paragraphs (5 levers × 2 dials) plus the one fixed dial-0 line. Cached on
`(lever, dial, style_version)`.

**So the design agent runs 10 times per style version, not 243.** All 243 cells are permutations of
those 11 strings, which buys the thing that matters more than the cost: every cell with
Conditions = 1 shows the **byte-identical** Conditions paragraph, so there is no per-cell wording
variation to confound a lever comparison. Bumping `style_version` invalidates all ten and nothing
else.

**Dial 0 is never generated.** `"No change from today."` is a constant (I5).
"""

from __future__ import annotations

import asyncio
from functools import lru_cache

import yaml

from config.settings import CONFIG_DIR, settings
from twinlab.agents.design import run_design
from twinlab.agents.registry import ModelClient, default_agent_configs, get_client
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.reference import LEVER_BY_POSITION, MET_CRITERIA, Chunk
from twinlab.models.variant import (
    DIAL_ZERO_TEXT,
    SHAM_DIAL,
    DeltaSpec,
    LeverBrief,
    LeverParagraph,
    RenderedVariant,
)
from twinlab.orchestrator.odometer import SHAM_CODE, dials, validate_code
from twinlab.variant.lookup import commitments_for_lever, do_not_say, lookup

#: How many corpus chunks reach one design brief. **CONFIG**, not specification.
#:
#: `docs/02` §4.1 says "anchor chunks … for register only" and names no count. Taken literally, a
#: `L4` dial-2 brief carries 93 chunks — 95,000 characters, roughly 24,000 tokens against
#: `docs/10`'s 2,300-token per-call estimate. Ten times the planned prompt for material whose only
#: job is to show the voice. Capped deterministically, following the selection idiom the researcher
#: already approved for the sham: ordered by `chunk_id`, round-robin across the gap's own anchor
#: sources so every named source contributes. Constant for a given `(lever, dial)`, so it cannot
#: vary with the cell and cannot confound a lever comparison. See `docs/DECISIONS.md`.
ANCHOR_CHUNKS_PER_BRIEF = 9

#: One chunk per unfilled sham lever, driver audience, ordered by `chunk_id` (researcher decision,
#: 2026-09-22). Deterministic and minimal: the sham must have zero free parameters.
SHAM_CHUNKS_PER_LEVER = 1


class RenderFailed(RuntimeError):
    """A paragraph that could not be rendered. The cell fails; it is never generically filled."""


@lru_cache(maxsize=1)
def load_style_contract() -> dict:
    """`config/style_contract.yaml`, read once.

    **Constant across all 243 cells** — anything that varies with the cell is a confound
    (`docs/03` §4.2). It is loaded rather than inlined so a `style_version` bump is a config edit
    that invalidates exactly the ten cached paragraphs.
    """
    path = CONFIG_DIR / "style_contract.yaml"
    return validate_style_contract(yaml.safe_load(path.read_text(encoding="utf-8")))


def validate_style_contract(contract: dict) -> dict:
    """Every check the contract must pass before it can gate a render. Raises :class:`RenderFailed`.

    Pure, and separate from the file read, so the guards can be tested on a mutated dict without
    writing to the repository's own config — nothing durable on the filesystem (I16), and a test
    that crashed mid-way could otherwise leave the real contract corrupted.
    """
    if contract["dial_zero_text"] != DIAL_ZERO_TEXT:
        raise RenderFailed(
            f"style_contract dial_zero_text {contract['dial_zero_text']!r} disagrees with the "
            f"constant {DIAL_ZERO_TEXT!r} (I5) — the two must never drift"
        )
    # `settings.style_version` is a second declaration of the same value. Nothing reads it today,
    # which is exactly how it would come to disagree with the contract unnoticed — and the cache key
    # is built from `style_version`, so a disagreement means two different contracts competing for
    # one cache slot.
    if contract["style_version"] != settings.style_version:
        raise RenderFailed(
            f"style_contract style_version {contract['style_version']!r} disagrees with "
            f"settings.style_version {settings.style_version!r} — the cache key is built from it, "
            "so the two must never drift"
        )
    if not contract["word_min"] <= contract["word_max"]:
        raise RenderFailed(
            f"style_contract word band [{contract['word_min']}, {contract['word_max']}] is empty"
        )
    return contract


def select_anchors(chunks: list[Chunk], limit: int = ANCHOR_CHUNKS_PER_BRIEF) -> list[str]:
    """Up to ``limit`` chunk texts, round-robin across sources, ordered by ``chunk_id``.

    Round-robin rather than truncation: a gap's anchor sources do different jobs — `S15` shows the
    voice, `S32` shows what the Services Agreement already says — and taking the first nine chunks
    of a 51-chunk list would silently drop whole sources. Deterministic in every process: no set
    iteration, no `hash()`.
    """
    by_source: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        by_source.setdefault(chunk.source_id, []).append(chunk)
    for source in by_source:
        by_source[source].sort(key=lambda c: c.chunk_id)

    out: list[str] = []
    depth = 0
    while len(out) < limit:
        added = False
        for source in by_source:  # insertion order = the gap's own anchor_sources order
            if depth < len(by_source[source]) and len(out) < limit:
                out.append(by_source[source][depth].verbatim_text)
                added = True
        if not added:
            break
        depth += 1
    return out


def build_brief(
    spec: DeltaSpec,
    lever: str,
    ref: ReferenceData | None = None,
    style: dict | None = None,
) -> LeverBrief:
    """The four inputs, and nothing else. `docs/02` §4.1.

    The commitments are **this lever's only**, so the agent has no way to reach another lever's
    material — that is what makes I2 and I3 structural. ``do_not_say`` carries every commitment
    outside this lever's set plus the three already-met criteria, as text rather than as ids: the
    agent cannot act on `2.2.a`, only on the sentence it stands for.
    """
    ref = ref or reference()
    style = style or load_style_contract()
    commitments = commitments_for_lever(spec, lever)
    gap_ids = spec.gaps_by_lever[lever]
    return LeverBrief(
        lever=lever,
        dial=int(spec.version_code[LEVER_BY_POSITION.index(lever)]),
        commitments=commitments,
        anchor_chunks=select_anchors(ref.anchor_chunks(gap_ids)),
        style_contract=style,
        do_not_say=[_text_of(identifier, ref) for identifier in do_not_say(spec, lever, ref)],
    )


def _text_of(identifier: str, ref: ReferenceData) -> str:
    """A gap id → its commitment; a Met criterion id → what Uber already does.

    The two namespaces meet only in the do-not-say list, and both must arrive as prose: a model
    given `3.1.a` cannot avoid saying what `3.1.a` says.
    """
    if identifier in ref.gaps:
        return ref.gaps[identifier].commitment
    return ref.findings[identifier].reason


# --------------------------------------------------------------------------- the sham


def sham_briefs(
    ref: ReferenceData | None = None, style: dict | None = None
) -> dict[str, LeverBrief]:
    """The sham's five briefs. **Zero free parameters.** `docs/03` §6.2.

    Its content is the three `Met` criteria read straight out of `criterion_findings.json`. We did
    not pick a plausible-sounding placebo; the codebook named it. Those three sit on Contracts and
    Management only, yet the cell needs five ordinary paragraphs, so Pay, Conditions and
    Representation announce — as though new — what that lever's driver-facing corpus already says.
    That is the sham's whole purpose: it measures how much a twin moves simply because it was shown
    change-shaped text.

    Selection is deterministic and minimal throughout: the Met criteria by their frozen ids, and
    one driver-audience chunk per unfilled lever ordered by ``chunk_id``
    (:data:`SHAM_CHUNKS_PER_LEVER`, researcher decision 2026-09-22).

    ``do_not_say`` is every real gap commitment. The sham may announce existing policy and nothing
    else, so a gap's distinctive vocabulary appearing in it is the same failure it would be in a
    live cell.
    """
    ref = ref or reference()
    style = style or load_style_contract()

    met_by_lever: dict[str, list[str]] = {}
    for criterion_id in MET_CRITERIA:
        lever = _lever_of_criterion(criterion_id, ref)
        met_by_lever.setdefault(lever, []).append(criterion_id)

    forbidden_everything = [ref.gaps[gap_id].commitment for gap_id in sorted(ref.gaps)]

    briefs: dict[str, LeverBrief] = {}
    for lever in LEVER_BY_POSITION:
        if lever in met_by_lever:
            commitments = {
                criterion_id: ref.findings[criterion_id].reason
                for criterion_id in met_by_lever[lever]
            }
        else:
            commitments = {
                chunk.chunk_id: chunk.verbatim_text
                for chunk in _existing_policy_chunks(lever, ref)
            }
        briefs[lever] = LeverBrief(
            lever=lever,
            dial=SHAM_DIAL,
            commitments=commitments,
            anchor_chunks=select_anchors(_lever_chunks(lever, ref)),
            style_contract=style,
            do_not_say=forbidden_everything,
        )
    return briefs


def _lever_of_criterion(criterion_id: str, ref: ReferenceData) -> str:
    """A criterion's lever, via its Fairwork principle. `L{principle}` by construction."""
    return f"L{ref.criteria[criterion_id].principle}"


def _lever_chunks(lever: str, ref: ReferenceData) -> list[Chunk]:
    """This lever's driver-facing chunks, ordered by ``chunk_id``."""
    return sorted(
        (c for c in ref.chunks.values() if c.lever == lever and c.audience == "driver"),
        key=lambda c: c.chunk_id,
    )


def _existing_policy_chunks(lever: str, ref: ReferenceData) -> list[Chunk]:
    """The chunk(s) an unfilled sham lever announces. One, by ``chunk_id``."""
    chunks = _lever_chunks(lever, ref)
    if not chunks:
        raise RenderFailed(
            f"{lever} has no driver-audience chunk, so the sham cannot announce its existing "
            "policy without a free parameter (docs/03 §6.2)"
        )
    return chunks[:SHAM_CHUNKS_PER_LEVER]


def sham_allowed(ref: ReferenceData | None = None) -> dict[str, str]:
    """What the sham may say: the containment gate's allowed set (`docs/DECISIONS.md`).

    Containment asks "is there a commitment here beyond what this cell may say?" For the sham, what
    it may say **is** the existing policy, so that text is the allowed set. No second containment
    path and no extra LLM call.
    """
    allowed: dict[str, str] = {}
    for brief in sham_briefs(ref).values():
        allowed.update(brief.commitments)
    return allowed


# --------------------------------------------------------------------------- the cache


class ParagraphPool:
    """The 11-string pool, keyed `(lever, dial, style_version)`. I4.

    A cache **hit is never re-rendered.** `docs/02` §4.5 allows one re-render on gate failure;
    applying it to a hit would call the design agent once per cell and break I4 outright. A failed
    paragraph is cached **as failed**, and every cell using it fails loudly
    (`docs/DECISIONS.md`, 2026-09-22).
    """

    def __init__(
        self,
        *,
        client: ModelClient | None = None,
        style: dict | None = None,
        ref: ReferenceData | None = None,
    ) -> None:
        self.style = style or load_style_contract()
        self.style_version: str = self.style["style_version"]
        self.ref = ref or reference()
        self._client = client
        self._cache: dict[tuple[str, int, str], LeverParagraph] = {}
        self._locks: dict[tuple[str, int, str], asyncio.Lock] = {}

    @property
    def client(self) -> ModelClient:
        return self._client or get_client()

    def key(self, lever: str, dial: int) -> tuple[str, int, str]:
        return (lever, dial, self.style_version)

    def cached(self) -> dict[tuple[str, int, str], LeverParagraph]:
        return dict(self._cache)

    async def get(self, brief: LeverBrief) -> LeverParagraph:
        """The paragraph for this brief's `(lever, dial)`, rendered at most once ever.

        Dial 0 short-circuits to the constant **before** any cache or client is touched: the fixed
        string is never generated, not even once (I5).
        """
        if brief.dial == 0:
            return LeverParagraph(text=DIAL_ZERO_TEXT)

        key = self.key(brief.lever, brief.dial)
        if key in self._cache:
            return self._cache[key]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            # Re-checked under the lock: two cells wanting the same paragraph must not each
            # spend a design call on it, which is I4 at the concurrency boundary.
            if key in self._cache:
                return self._cache[key]
            cfg = default_agent_configs()["design"]
            paragraph = await run_design(cfg, brief, self.client)
            self._cache[key] = paragraph
            return paragraph


# --------------------------------------------------------------------------- assembly


async def render_variant(
    version_code: str,
    pool: ParagraphPool,
) -> RenderedVariant:
    """One cell's five paragraphs, assembled from the pool. `docs/03` §4.3.

    `SHAM` is assembled from its own five briefs at :data:`SHAM_DIAL`; every other code is a
    permutation of the 11 strings. Nothing is generated here that a cache hit could have supplied.
    """
    if version_code == SHAM_CODE:
        return await _render_sham(pool)

    validate_code(version_code)
    spec = lookup(version_code, pool.ref)
    per_lever = dials(version_code)
    paragraphs: dict[str, LeverParagraph] = {}
    for lever in LEVER_BY_POSITION:
        brief = build_brief(spec, lever, pool.ref, pool.style)
        paragraphs[lever] = await pool.get(brief)
    return RenderedVariant(
        version_code=version_code,
        style_version=pool.style_version,
        delta_hash=spec.delta_hash,
        paragraphs=paragraphs,
        dials=per_lever,
    )


async def _render_sham(pool: ParagraphPool) -> RenderedVariant:
    """The sham's five paragraphs, all at :data:`SHAM_DIAL`.

    Its ``delta_hash`` is taken over its five slots so the sham has provenance like any other cell
    without pretending to be a `dial_lookup` row — `lookup("SHAM")` raises on purpose.
    """
    briefs = sham_briefs(pool.ref, pool.style)
    paragraphs: dict[str, LeverParagraph] = {}
    for lever in LEVER_BY_POSITION:
        paragraphs[lever] = await pool.get(briefs[lever])
    gaps_by_lever = {lever: sorted(briefs[lever].commitments) for lever in LEVER_BY_POSITION}
    return RenderedVariant(
        version_code=SHAM_CODE,
        style_version=pool.style_version,
        delta_hash=DeltaSpec.hash_of(gaps_by_lever),
        paragraphs=paragraphs,
        dials={lever: SHAM_DIAL for lever in LEVER_BY_POSITION},
    )


async def render_all(
    codes: list[str],
    pool: ParagraphPool,
) -> dict[str, RenderedVariant]:
    """Every code, sharing one pool. Serial: the free provider tier permits one request.

    Rendering all 243 codes through here spends **exactly ten** design calls, which is I4 stated as
    a measurement rather than an intention.
    """
    return {code: await render_variant(code, pool) for code in codes}


def forbidden_for(spec: DeltaSpec, lever: str, ref: ReferenceData | None = None) -> dict[str, str]:
    """The containment gate's forbidden set for one lever: id → text.

    The same list the agent was shown as ``do_not_say``, keyed by id so a hit can be named.
    """
    ref = ref or reference()
    return {
        identifier: _text_of(identifier, ref)
        for identifier in do_not_say(spec, lever, ref)
    }
