"""The live twin path. `docs/02` §4.2, `docs/03` §4 and §8, `docs/04` §3 and §6.

Everything above this module — `SessionRunner`, the quality gate, Twin Studio, the six validity
tests that need fresh calls — takes its model work as an **injected callable** so that layer stays
testable without a provider. This is the one module that supplies those callables, which is why it
is the only place in `services/` that reaches `agents/` and `variant/`.

Four contracts hold here rather than in a caller:

* **A cache hit is never re-rendered and never re-checked** (I4, `docs/04` §6). `lever_paragraphs`
  is the durable paragraph cache and `variants` the durable cell cache; both survive a restart,
  which is what makes a sweep resumable without re-paying the design agent or the coverage probes.
* **An unverified variant never reaches a twin** (I3). :func:`render_and_check` returns the
  Checker's report beside the variant and never repairs a paragraph; the orchestrator fails the
  cell on ``passed is False``.
* **Nothing is coerced into validity** (I13). A twin round goes through `run_answer_ladder`, so a
  defective vector gets one targeted repair and then **fails for that cell only**. There is no
  branch here that pads, clamps or rounds an answer.
* **The round prompt is rebuilt, never stored** (I11). `twin_answers` keeps the seed, the lever
  order and the wording; :func:`round_seed` is deterministic over `(session, twin, code)` so the
  same round regenerates byte-identically.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from twinlab.agents.contract import ContractError, run_answer_ladder
from twinlab.agents.registry import (
    AgentDisabled,
    get_client,
    live_agent,
    resolve_prompt,
)
from twinlab.agents.twin import (
    RoundPromptError,
    assert_no_forbidden_content,
    build_round_prompt,
    build_user_prompt,
)
from twinlab.db.client import DbBackend, get_backend
from twinlab.db.repositories import AnswerRepo, RunRepo, VariantRepo
from twinlab.ingest.reference_store import ReferenceData, reference
from twinlab.models.agent import AgentConfig
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.models.run import Session
from twinlab.models.twin import (
    OWN_WORDS_IDS,
    WHY_PROBE_IDS,
    AnswerVector,
    BatteryItem,
    PanelCandidate,
    QualityAnswerSet,
    RoundPrompt,
    TwinAnswerSet,
)
from twinlab.models.variant import (
    SHAM_DIAL,
    CheckerReport,
    LeverParagraph,
    RenderedVariant,
)
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE, dials
from twinlab.variant.checker import check_variant
from twinlab.variant.render import ParagraphPool

log = logging.getLogger(__name__)


class TwinPathError(RuntimeError):
    """A live twin call that must not be made, or a result that must not be recorded."""


# ============================================================ the paragraph cache


class StoredParagraphPool(ParagraphPool):
    """:class:`ParagraphPool` with `lever_paragraphs` behind it. `docs/04` §6.

    The in-memory pool alone means the ten design calls are re-paid on every restart, and on a
    free Space a restart is routine. **This does not add a fourth cache** (`CLAUDE.md` — "do not
    invent a fourth"): it is the same `(lever, dial, style_version)` key the table already
    declares, made durable.

    A paragraph is written back exactly once, at the miss. A hit — in memory or in the table — is
    never re-rendered, which is I4 stated as a measurement rather than an intention.
    """

    def __init__(self, *, backend: DbBackend | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.db = backend or get_backend()
        self._loaded = False
        #: Key → the `attempts` value the next :meth:`_store` must write. Only ever populated
        #: between a re-render's eviction and its write-back, so the count is in memory for the
        #: span of one call and durable either side of it.
        self._pending_attempts: dict[tuple[str, int, str], int] = {}

    async def _load(self) -> None:
        """Warm the in-memory cache from the table. Once per pool."""
        if self._loaded:
            return
        self._loaded = True
        rows = await self.db.select(
            "lever_paragraphs", [("eq", "style_version", self.style_version)]
        )
        for row in rows:
            key = (str(row["lever"]), int(row["dial"]), self.style_version)
            if key in self._cache:
                continue
            self._cache[key] = LeverParagraph(text=str(row["text"]))
            if int(row.get("attempts") or 1) >= RENDER_ATTEMPTS_MAX:
                # The re-render was spent in an earlier process. Without this the budget resets
                # on every restart and I4's design-call count has no denominator (§3.2).
                _rerendered.add(key)

    async def get(self, brief: Any) -> LeverParagraph:
        await self._load()
        before = self.key(brief.lever, brief.dial) in self._cache
        paragraph = await super().get(brief)
        if before or brief.dial == 0 or paragraph.status != "ok":
            # Dial 0 is a constant and is never generated, so it is never stored (I5). A refusal
            # is not a paragraph and must not become a cache hit for the next cell.
            return paragraph
        await self._store(brief, paragraph)
        return paragraph

    async def _store(self, brief: Any, paragraph: LeverParagraph) -> None:
        """Write the paragraph back to `lever_paragraphs`, keyed `(lever, dial, style_version)`.

        **Upserted, not inserted.** The table carries a unique index on that key, and the
        in-memory cache can legitimately be behind it — a re-render deletes the row then writes a
        new one, and a second process may have filled the key since this pool warmed. A duplicate
        key is not a data defect here; it is the cache doing its job, and failing a render over it
        threw away a paragraph that had already been paid for.
        """
        key = self.key(brief.lever, brief.dial)
        await self.db.upsert(
            "lever_paragraphs",
            [{
                "lever": brief.lever,
                "dial": brief.dial,
                "style_version": self.style_version,
                "text": paragraph.text,
                "word_count": paragraph.word_count,
                "delta_hash": _hash(paragraph.text),
                "checker_pass": False,  # the cell's Checker verdict lives on `variants`
                # A first render is 1; a re-render carries the count it was charged, so the
                # design calls this paragraph has cost survive the process that paid for them.
                "attempts": self._pending_attempts.pop(key, 1),
            }],
            on_conflict="lever,dial,style_version",
        )


    async def rerender(
        self,
        brief: Any,
        *,
        instruction: str | None = None,
        missing: dict[str, str] | None = None,
    ) -> LeverParagraph:
        """Spend the **one** re-render `docs/03` §5 allows on a gate failure, for this key.

        Evicts the key from memory and from `lever_paragraphs`, renders again with ``instruction``
        appended, and stores whatever comes back — including a second failing paragraph, which is
        then cached as failed and fails every cell that uses it, loudly (`docs/DECISIONS.md`,
        2026-09-22). Re-rendering for every cell that uses a failing paragraph would call the
        design agent once per code and break I4 outright.

        **The budget is durable** (`lever_paragraphs.attempts`, RESEARCHER 2026-10-01). It was a
        module-level set until then, so a restart handed every key a fresh re-render and the design
        calls a paragraph had cost were recorded nowhere. The attempt is charged to the table
        **before** the design call, not after: a re-render that crashes, times out or comes back
        `cannot_render` has still been paid for, and must not buy a second one on the next run.

        ``instruction`` names only what the previous attempt missed **of its own contract**. It
        cannot change what the paragraph may say — the brief's commitments and do-not-say list are
        untouched — so this is the design agent's targeted repair, not the Checker steering the
        text it grades.
        """
        key = self.key(brief.lever, brief.dial)
        if brief.dial == 0:
            return await self.get(brief)
        await self._load()
        spent = await self._attempts(brief)
        if key in _rerendered or spent >= RENDER_ATTEMPTS_MAX:
            return await self.get(brief)

        # Charge it first, in the table, while there is still a row to charge. `spent + 1` is 1
        # when no row exists, which is the truth as far as the table is concerned: an earlier
        # refusal stored nothing, because a refusal is not a paragraph and must never become a
        # cache hit for the next cell.
        charged = spent + 1
        self._pending_attempts[key] = charged
        filters = [
            ("eq", "lever", brief.lever),
            ("eq", "dial", brief.dial),
            ("eq", "style_version", self.style_version),
        ]
        if spent:
            await self.db.update("lever_paragraphs", {"attempts": charged}, filters)
        current = self.cached().get(key)
        _rerendered.add(key)
        self._cache.pop(key, None)

        if missing and current is not None and current.status == "ok":
            # The one repair, targeted: the same design agent writes only the sentences the
            # paragraph left out, and they are appended to the text already written. The rest of
            # the paragraph is not regenerated, so a fix for one commitment cannot break another.
            # The Checker judges the combined text on the next pass (I3).
            from twinlab.agents.design import missing_instruction, run_design

            addition = await run_design(
                live_agent("design"), brief, self.client,
                instruction=missing_instruction(missing),
            )
            if addition.status != "ok":
                # Same refusal semantics as a full re-render: the old row stays, marked spent.
                self._cache[key] = addition
                return addition
            paragraph = LeverParagraph(text=f"{current.text} {addition.text}", status="ok")
            self._cache[key] = paragraph
            await self._store(brief, paragraph)
            return paragraph

        if not instruction:
            # No repair to make, so the key is evicted outright and re-rendered from the brief.
            # `_store` writes `charged` back, so eviction does not refund the attempt.
            await self.db.delete("lever_paragraphs", filters)
            return await self.get(brief)

        from twinlab.agents.design import run_design

        # The **live** config (WP-8). A disabled design agent fails the render loudly: there
        # is no rule-based fallback, because replacing the rendering half with a template would
        # turn the stimulus from Uber-voice prose into a bulleted list of commitments, which is a
        # different experiment (plan §3.3).
        paragraph = await run_design(
            live_agent("design"), brief, self.client, instruction=instruction
        )
        self._cache[key] = paragraph
        if paragraph.status == "ok":
            # Upserted onto the same key, so the row is replaced rather than deleted and
            # re-inserted. The charge written above stays written.
            await self._store(brief, paragraph)
        # A refusal deliberately leaves the previous row in place, now marked as having spent its
        # re-render. The refusal fails *this* cell through the in-memory cache, and the next
        # process reloads the old failing paragraph and declines to pay for it again — which is
        # the loud, once-only failure `docs/03` §5 asks for. Deleting the row here would refund
        # the attempt and the paragraph would be re-rendered on every restart.
        return paragraph


    async def _attempts(self, brief: Any) -> int:
        """Design calls already charged to this key, from the table. 0 when there is no row.

        Read rather than remembered, so two processes cannot each spend the same re-render.
        """
        rows = await self.db.select(
            "lever_paragraphs",
            [
                ("eq", "lever", brief.lever),
                ("eq", "dial", brief.dial),
                ("eq", "style_version", self.style_version),
            ],
        )
        return max((int(r.get("attempts") or 1) for r in rows), default=0)


#: Design calls one `(lever, dial, style_version)` paragraph may ever cost: the first render plus
#: the one re-render `docs/03` §5 allows. `lever_paragraphs.attempts` carries the same ceiling as
#: a check constraint, so the data cannot say something this code will not.
RENDER_ATTEMPTS_MAX = 2

#: Keys that have spent their one re-render, in **this** process. A short-circuit over
#: :meth:`StoredParagraphPool._attempts`, not the record: the record is the `attempts` column, and
#: :meth:`StoredParagraphPool._load` refills this set from it at startup.
_rerendered: set[tuple[str, int, str]] = set()

_pool: StoredParagraphPool | None = None


def paragraph_pool(*, backend: DbBackend | None = None) -> StoredParagraphPool:
    """The process's one pool. Shared so two sessions cannot each pay for the same paragraph."""
    global _pool
    if _pool is None:
        _pool = StoredParagraphPool(backend=backend)
    return _pool


def reset_pool() -> None:
    """Test hook, and what a `style_version` bump would call. The application does not."""
    global _pool
    _pool = None
    _rerendered.clear()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ================================================================ render and check


def _dials_for(code: str) -> dict[str, int]:
    """Per-lever dial, with :data:`SHAM_DIAL` for the sham's five slots."""
    if code == SHAM_CODE:
        return {lever: SHAM_DIAL for lever in LEVER_BY_POSITION}
    return dials(code)


def _variant_from_row(row: dict) -> RenderedVariant:
    """Rebuild a :class:`RenderedVariant` from its stored `variants` row.

    The stored paragraphs are what the twins were shown (`docs/09` §2), so a cached cell is
    replayed from the table rather than re-rendered — a re-render could differ, and nothing on
    screen would say so.
    """
    code = str(row["version_code"])
    stored = dict(row.get("paragraphs") or {})
    paragraphs: dict[str, LeverParagraph] = {}
    for lever in LEVER_BY_POSITION:
        if lever not in stored:
            raise TwinPathError(
                f"stored variant {code} has no paragraph for {lever}. A cell missing a lever is "
                "not a cell; delete the row and re-render rather than showing a twin four "
                "paragraphs."
            )
        entry = stored[lever]
        text = entry.get("text", "") if isinstance(entry, dict) else str(entry or "")
        if not text:
            # A stored empty lever is a **refusal** the design agent returned, not a missing row
            # (`_render_stimuli` writes refusals as empty text). Keep it as one, so the stored
            # failing report stands and no twin is shown an empty paragraph (I3).
            paragraphs[lever] = LeverParagraph(
                text="", status="cannot_render", reason="stored refusal (empty paragraph)"
            )
            continue
        paragraphs[lever] = LeverParagraph(text=text)
    return RenderedVariant(
        version_code=code,
        style_version=str(row["style_version"]),
        delta_hash=str(row["delta_hash"]),
        paragraphs=paragraphs,
        dials=_dials_for(code),
    )


async def render_and_check(
    code: str,
    style_version: str,
    *,
    backend: DbBackend | None = None,
    events: Any = None,
) -> tuple[RenderedVariant, CheckerReport]:
    """`SessionRunner`'s ``render_and_check``. Returns the variant **and its verdict**.

    A stored `(version_code, style_version)` row that **passed** short-circuits both the render
    and the Checker. That is the `variants` cache of `docs/04` §6 doing its job: the coverage probe
    is one model call per commitment, so re-checking a passing cell would be the single most
    expensive thing this module could do for no new information.

    **A stored row that did not pass is a cache of the verdict, not of the attempt** (M19 WP-2,
    decision D1). Until 2026-10-03 the short-circuit was unconditional, which combined with "store
    the report pass or fail" to make a cell that failed once fail for ever — no path in the
    application to clear it, no event saying a second attempt was a cache hit, and nothing on
    screen distinguishing "genuinely unrenderable" from "unlucky once in September".

    What bounds the cost is the **durable paragraph budget** (`lever_paragraphs.attempts`,
    :data:`RENDER_ATTEMPTS_MAX`), which survives a restart. So a re-entry on a stored failure
    either re-renders inside that budget or returns the stored verdict having made **zero** model
    calls — not even a coverage probe, which is why the budget is tested before anything is
    re-assembled. I3 is untouched: the refusal is at every *read* of a non-passing variant, and
    this re-opens the attempt, never the verdict.

    ``events`` is an optional :class:`orchestrator.events.EventLog`. When supplied, a re-entry on a
    stored failure emits a row, so a second press is visibly a second press.
    """
    db = backend or get_backend()
    cached = await VariantRepo(db).get(code, style_version)
    stored_report: CheckerReport | None = None
    if cached is not None:
        stored_report = CheckerReport(**dict(cached.get("checker") or {}))
        if stored_report.passed:
            return _variant_from_row(cached), stored_report

    pool = paragraph_pool(backend=db)
    if pool.style_version != style_version:
        raise TwinPathError(
            f"session asks for style_version {style_version!r} but the paragraph pool is built "
            f"on {pool.style_version!r}. The cache key is built from it, so the two must never "
            "disagree — bump `config/style_contract.yaml` and `settings.style_version` together."
        )
    from twinlab.variant.render import render_variant

    if cached is not None and stored_report is not None:
        # Re-entry on a stored failure. The budget is read **first** and nothing is assembled or
        # probed until it is known to be spendable: `_rerender_cell` would also decline to spend
        # a design call, but it hands back a re-assembled variant and the caller then pays a
        # coverage probe per commitment — 24 of them on `12220` — for a verdict already on record.
        stored_variant = _variant_from_row(cached)
        remaining = await _levers_with_budget(code, pool)
        if events is not None:
            await _emit_recheck(code, stored_report, remaining, events)
        if not remaining:
            return stored_variant, stored_report
        second = await _rerender_cell(code, pool, stored_report)
        if second is None:
            return stored_variant, stored_report
        recheck = await check_variant(
            second, client=pool.client, style=pool.style, ref=pool.ref
        )
        return second, recheck

    variant = await render_variant(code, pool)
    report = await check_variant(variant, client=pool.client, style=pool.style, ref=pool.ref)
    if report.passed:
        return variant, report

    # `docs/03` §5: **fail any gate → re-render once → then halt that cell.** The second pass was
    # specified and never implemented, so a cell that failed on one stochastic bad paragraph
    # failed permanently — and, because the paragraph is cached, so did every other cell using it.
    second = await _rerender_cell(code, pool, report)
    if second is None:
        return variant, report
    recheck = await check_variant(second, client=pool.client, style=pool.style, ref=pool.ref)
    return second, recheck


async def _levers_with_budget(code: str, pool: StoredParagraphPool) -> list[str]:
    """The non-dial-0 levers of ``code`` that still have their one durable re-render. WP-2.

    Read **before** anything is re-assembled or re-probed, because the whole point of WP-2 is that
    a re-entry on an exhausted cell costs nothing. `_rerender_cell` would also decline to spend a
    design call, but it would hand back a re-assembled variant and the caller would then pay a
    coverage probe per commitment — 24 of them on `12220` — for a verdict already on record.
    """
    await pool._load()
    out: list[str] = []
    for lever, dial in _dials_for(code).items():
        if dial == 0:
            continue
        if pool.key(lever, dial) not in _rerendered:
            out.append(lever)
    return out


async def _emit_recheck(
    code: str, stored: CheckerReport, remaining: list[str], events: Any
) -> None:
    """Say out loud that this is a second look at a cell that already failed. WP-2 item 2.

    The 04:44/04:48 experience — the identical error twice, the second free and uninformative —
    was possible because a cache hit on a failure emitted nothing. A press that costs nothing must
    still say so.
    """
    if remaining:
        label = (
            f"{code} failed the Checker before; re-rendering "
            f"{len(remaining)} lever paragraph(s) that still have a re-render available "
            f"({', '.join(remaining)})"
        )
        status = "running"
    else:
        label = (
            f"{code} failed the Checker before and every lever paragraph has spent its one "
            f"re-render, so this attempt makes no model call and the verdict stands: "
            f"{str(stored.notes or '')[:200]}"
        )
        status = "error"
    try:
        await events.emit(stage="check", agent="checker", label=label[:400], status=status)
    except Exception:  # noqa: BLE001 — a log that cannot write must not fail the render
        log.warning("could not emit the re-check event for %s", code, exc_info=True)


async def _rerender_cell(
    code: str, pool: StoredParagraphPool, report: CheckerReport
) -> RenderedVariant | None:
    """The one re-render. ``None`` when every lever has already spent it.

    Only the non-dial-0 levers are re-rendered: dial 0 is a constant and is never generated (I5).
    Each is given a repair naming what **its own** paragraph missed, computed per lever rather
    than parsed out of `report.notes` — a reworded note must never be able to change what a lever
    is asked to fix.
    """
    from twinlab.variant.lookup import lookup
    from twinlab.variant.render import build_brief, render_variant, sham_briefs

    if code == SHAM_CODE:
        briefs = sham_briefs(pool.ref, pool.style)
    else:
        spec = lookup(code, pool.ref)
        briefs = {
            lever: build_brief(spec, lever, pool.ref, pool.style)
            for lever in LEVER_BY_POSITION
        }
    spent = 0
    for lever, brief in briefs.items():
        if brief.dial == 0 or pool.key(lever, brief.dial) in _rerendered:
            continue
        repair = _repair_for(brief, pool, report)
        if repair is None:
            # **This lever's paragraph passed every gate it is judged on, so it is left alone.**
            # `_repair_for` documents `None` as "it missed nothing", but the return value used to
            # be passed straight through, and `rerender(instruction=None)` deletes the row and
            # re-renders from the brief with no repair. So one failing lever threw away and
            # re-rolled the paragraphs of *every* lever in the cell — spending each one's single
            # durable re-render on a blind re-roll of text that was already good.
            #
            # That is the mechanism behind the "the re-render made several of these WORSE"
            # observation in `HANDOFF_M15_LIVE_PATH.md` §2.4 (L1 dial 1: 11.48 before, 18.07
            # after). It was read there as the repair failing to converge; it was a passing
            # paragraph being discarded and re-sampled without an instruction.
            continue
        missing = {
            gap_id: brief.commitments[gap_id]
            for gap_id in sorted(brief.commitments)
            if report.coverage.get(gap_id) is False
        }
        await pool.rerender(brief, instruction=repair, missing=missing or None)
        spent += 1
    if not spent:
        return None
    log.info("%s: re-rendered %d lever paragraph(s) after a Checker failure", code, spent)
    return await render_variant(code, pool)


def _repair_for(brief: Any, pool: StoredParagraphPool, report: CheckerReport) -> str | None:
    """What this lever's paragraph missed, as an instruction. ``None`` when it missed nothing.

    Deliberately narrow. It states which commitments were not carried, which forbidden
    intensifiers were used, and — when the register band was breached — asks for shorter sentences
    and plainer words.

    **No number from the style contract is quoted**, and that is now a measured choice rather than
    an inherited one. Since 2026-10-01 the agent *is* shown the band (`STYLE_KEYS_SHOWN`), so the
    old reason for withholding it here had lapsed; quoting the measured grade was therefore tried
    against the alternative on `L4` dial 1, the one paragraph the band alone does not fix. Both
    cleared gate 3 three times out of three (wordless 9.09/10.09/8.37, numbered 11.37/8.36/11.19).
    The wordless instruction is kept because it is no worse and puts no digit near prose that
    rule 6 forbids digits in.
    """
    from twinlab.variant.checker import check_invariance, word_count

    current = pool.cached().get(pool.key(brief.lever, brief.dial))
    parts: list[str] = []

    uncovered = sorted(
        gap_id
        for gap_id in brief.commitments
        if report.coverage.get(gap_id) is False
    )
    if uncovered:
        parts.append(
            "The previous version did not state these commitments plainly enough for a reader to "
            "recognise them. State each one in its own short sentence:"
            + "".join(f"\n- {brief.commitments[gap_id]}" for gap_id in uncovered)
        )

    if current is not None and current.status == "ok":
        # `brief.style_contract`, not `pool.style`: from style_version v3 the word band is
        # resolved per (lever, dial) from the commitment count, and the brief's copy is the
        # resolved one — the same two numbers the agent was shown and gate 3 graded against.
        in_band, _grade, violations = check_invariance(current.text, brief.style_contract)
        for violation in violations:
            if violation.startswith("reading grade"):
                parts.append(
                    "The previous version reads too densely. Use shorter sentences — one idea "
                    "each — and everyday words a driver would use. Do not drop anything; say the "
                    "same things more plainly."
                )
            elif violation.startswith("forbidden"):
                term = violation.split("'")[1] if "'" in violation else ""
                parts.append(
                    f"Do not use the word {term!r}." if term else "Remove the flagged wording."
                )
        if not in_band:
            count = word_count(current.text)
            parts.append(
                f"The previous version was {count} words, outside "
                f"{brief.style_contract['word_min']}-{brief.style_contract['word_max']}. "
                "Write within that range."
            )

    if not parts:
        return None
    return (
        "<<<REPAIR>>>\nThis is a second attempt. Keep to the same commitments and the same "
        "do-not-say list; change only what is named here.\n"
        + "\n".join(parts)
        + "\n<<<END REPAIR>>>"
    )


# ===================================================================== the twin


def round_seed(session_id: str, twin_id: str, version_code: str) -> int:
    """The per-round seed. Deterministic over `(session, twin, code)`, stored on the answer.

    The lever order is drawn from this seed and **checked against it** when the round is rebuilt
    (I11, `agents/twin.rebuild_round_prompt`), so it may not be random per call: a round that
    cannot be regenerated cannot be attributed to a known stimulus.
    """
    digest = hashlib.sha256(f"{session_id}|{twin_id}|{version_code}".encode()).hexdigest()
    return int(digest[:8], 16)


def battery_for(ref: ReferenceData | None = None) -> dict[str, BatteryItem]:
    """The 37-item battery as `item_id → BatteryItem`, in register order.

    Each item's **own** range and anchors travel with it (`docs/02` §4.2 rule 6). The prototype's
    prompt said "1 to 7" for every item and three of its nine constructs were 5-point; this build
    said "1 to 7" correctly and never said which end was which (`docs/DECISIONS.md` 2026-10-12).
    """
    ref = ref or reference()
    return {i: ref.battery_item(i) for i in ref.battery_item_ids}


async def twin_row(twin_id: str, db: DbBackend) -> dict:
    rows = await db.select("twins", [("eq", "twin_id", twin_id)], limit=1)
    if not rows:
        raise TwinPathError(f"no twin {twin_id!r}")
    return rows[0]


async def driver_answers(twin_id: str, db: DbBackend) -> dict[str, int]:
    """The human's own survey answers, by item id. Never imputed, never defaulted.

    ``twin_id`` matches ``submission_id`` by convention where the column is absent, which is what
    `services/lab._driver_answers` already relies on.
    """
    row = await twin_row(twin_id, db)
    submission = str(row.get("submission_id") or twin_id)
    rows = await db.select("survey_answers", [("eq", "submission_id", submission)])
    return {r["item_id"]: int(r["value_num"]) for r in rows if r.get("value_num") is not None}


async def persona_for(twin_id: str, db: DbBackend) -> str:
    """The stored passage. **Never rebuilt here** — the twin must be given what it was given.

    A hand-built twin has no persona (`docs/06` §5), so it is described from its stored profile
    instead. That passage is not a reconstruction of a driver and is never hashed into `twins`.
    """
    row = await twin_row(twin_id, db)
    passage = row.get("persona_passage")
    if passage:
        return str(passage)
    if row.get("source") != "manual":
        raise TwinPathError(
            f"{twin_id} has no persona passage and is not a manual twin. A real or synthetic twin "
            "without a persona cannot be asked anything — rebuild it from its survey row."
        )
    return _manual_persona(row)


def _manual_persona(row: dict) -> str:
    """What a hand-built twin is told about itself: its profile and its sliders, and nothing else.

    Written in the first person like a real persona so the twin agent's `<<<PERSONA>>>` fence
    reads the same either way, but it is **not** a reconstruction and it carries no hash: there is
    no driver behind it to be lossless about (I6).
    """
    from twinlab.services.studio import MANUAL_SLIDERS

    background = row.get("background") or {}
    sliders = dict(background.get("sliders") or {})
    labels = dict(MANUAL_SLIDERS)
    bits = ["Who I am"]
    who = [
        f"I am {row['age']} years old." if row.get("age") else "",
        f"I describe my gender as {row['gender']}." if row.get("gender") else "",
        f"I drive {row['service']} in {row['city']}."
        if row.get("service") and row.get("city")
        else "",
        f"I have been driving with Uber for {row['tenure_months']} months."
        if row.get("tenure_months")
        else "",
        f"I work about {row['hours_per_week']} hours a week."
        if row.get("hours_per_week")
        else "",
    ]
    bits.append(" ".join(w for w in who if w))
    if sliders:
        bits.append("\nHow I see the work, on a scale of one to seven")
        bits.extend(
            f"{labels.get(code, code)}: {value} out of 7."
            for code, value in sliders.items()
        )
    if background.get("note"):
        bits.append("\nIn my own words\n" + str(background["note"]))
    return "\n".join(b for b in bits if b)


def _why_texts(row: dict) -> list[str]:
    """The twin's own why-text and open answers, for I8's stimulus scan.

    They belong in the persona and nowhere else (`docs/03` §8): a twin re-reading its own
    justifications under every counterfactual restates them and looks immovable no matter what it
    is shown — which is the signal, destroyed.
    """
    background = row.get("background") or {}
    out: list[str] = []
    for key in (*WHY_PROBE_IDS, *OWN_WORDS_IDS):
        value = background.get(key) or (background.get("own_words") or {}).get(key)
        if isinstance(value, str) and value.strip():
            out.append(value)
    return out


#: The H3 gate's own system prompt. A sibling of `twin_v1.md`, not an edit of it: the H3 round has
#: three fences rather than four and asks the twin to hold six worlds side by side, so one prompt
#: could not describe both without describing each of them loosely. Both go through
#: `resolve_prompt`, so both are held to the six-section skeleton and both are hashed onto the run.
H3_PROMPT_REF = "file:twin_h3_v4.md"

#: What `twin_quality_runs.detail["protocol"]` records. Six-in-one-context and six-in-isolation are
#: **different measurements** and must never be pooled: a row that does not say which presentation
#: produced it cannot be excluded later, so the name is written on every row rather than inferred.
H3_PROTOCOL = "h3_single_call_v1"

#: The name the **six-call** protocol records. `h3_six_calls_v1`, restored 2026-10-14.
#:
#: This was the protocol before M19 WP-3 replaced it with one call. It is back as a selectable
#: alternative, not as a replacement, because the stage-7 error decomposition pointed at it: every
#: twin's 18 H3 errors reduce to a **per-outcome offset of ~1.0 scale points plus scatter of
#: ~0.65**, and scatter alone is comfortably inside the gate. A constant per outcome with almost
#: no version signal is exactly what one impression emitted six times looks like, which is what a
#: single context invites (`docs/DECISIONS.md`, 2026-10-13 stage 7).
#:
#: **The two are different measurements and must never be pooled.** That is why the name is
#: written onto every row rather than inferred, and why `config_match.current_config` carries it:
#: without that the gate would report "already scored under this config" and skip every twin.
H3_PROTOCOL_ISOLATED = "h3_six_calls_v1"

#: Which protocol the gate uses. `TWINLAB_H3_PROTOCOL=six` selects the six-call one; anything else
#: leaves the shipped single call in place. An environment switch rather than a new config column
#: because this is a **research comparison being run**, not a setting the study has adopted: the
#: default is unchanged, and whichever ran is recorded on the row either way.
def h3_protocol_is_isolated() -> bool:
    """``True`` when the six-call protocol is selected. Read at call time, never cached."""
    import os

    return os.environ.get("TWINLAB_H3_PROTOCOL", "").strip().lower() in {"six", "isolated"}


def twin_agent_config(
    *,
    temperature: float | None = None,
    model: str | None = None,
    prompt_ref: str | None = None,
) -> AgentConfig:
    """The twin agent's config, with the **live** temperature applied. `docs/09` §4.

    `agents.default.yaml` seeds a temperature and `TwinConfig` carries the live one; they are two
    declarations of the same value, and the live one wins because it is what a session freezes
    onto its `config` column and reports with its results.

    ``prompt_ref`` swaps the system prompt for a sibling file — :data:`H3_PROMPT_REF` is the only
    caller. It goes through `resolve_prompt` like any other, so the replacement is held to the same
    six-section skeleton and its own hash is frozen onto the run.
    """
    from twinlab.services.config import load_twin_config

    # The **live** config (WP-8), so a prompt, model, output mode or retry policy edited in
    # Agent Studio governs the next thing asked. A disabled twin raises: nothing can be asked, and
    # asking anyway would make the toggle a lie in the other direction.
    cfg = live_agent("twin")
    temp = load_twin_config().temperature if temperature is None else float(temperature)
    update: dict[str, Any] = {"temperature": temp}
    if model:
        update["name"] = model
    copy: dict[str, Any] = {"model": cfg.model.model_copy(update=update)}
    if prompt_ref:
        copy["system_prompt"] = prompt_ref
    return cfg.model_copy(update=copy)


async def ask_items(
    *,
    twin_id: str,
    paragraphs: dict[str, str],
    items: dict[str, BatteryItem],
    baseline: dict[str, int],
    seed: int,
    wording: str = "A",
    show_baseline: bool = True,
    persona_text: str | None = None,
    temperature: float | None = None,
    model: str | None = None,
    version_code: str | None = None,
    reverse_order: bool = False,
    system_prompt: str | None = None,
    backend: DbBackend | None = None,
) -> tuple[dict[str, int], dict[str, Any]]:
    """One twin round over an arbitrary item set. Returns ``(answers, telemetry)``.

    This is the single place a twin is actually called. The battery round, the quality gate's
    three-item H3 rounds, the Studio and the validity tests all come through here, so I8's guard
    and the repair ladder cannot be skipped by one of them.

    **Raises** :class:`~twinlab.agents.contract.ContractError` when the ladder cannot produce a
    valid vector after its one targeted repair. That is the correct outcome: the twin fails for
    this cell and nothing is padded, clamped or rounded into validity (`CLAUDE.md`).
    """
    db = backend or get_backend()
    ref = reference()
    row = await twin_row(twin_id, db)
    persona = persona_text if persona_text is not None else await persona_for(twin_id, db)
    if not persona.strip():
        raise TwinPathError(f"{twin_id} has an empty persona passage; there is nobody to ask")

    prompt = build_round_prompt(
        persona_hash=str(row.get("persona_hash") or ""),
        paragraphs=paragraphs,
        baseline={k: v for k, v in baseline.items() if k in items},
        battery=items,
        seed=seed,
        wording=wording,
        show_baseline=show_baseline,
    )
    if reverse_order:
        # Validity test 5 shows the same cell with the paragraphs reversed. The stored
        # `lever_order` still describes what was shown, so the round stays reconstructible.
        prompt = RoundPrompt(
            **{
                **prompt.model_dump(),
                "scenario": list(reversed(prompt.scenario)),
                "lever_order": list(reversed(prompt.lever_order)),
            }
        )

    assembled = build_user_prompt(prompt, persona)
    # I8, one string scan per round. The failure it prevents — a twin that has seen its own
    # holdout answers — invalidates that twin silently and permanently.
    assert_no_forbidden_content(
        assembled,
        holdout_ids=[i for i in ref.holdout_h3_item_ids + ref.holdout_h2_item_ids
                     if i not in items],
        why_texts=_why_texts(row),
        version_code=version_code,
    )

    cfg = twin_agent_config(temperature=temperature, model=model)
    # `resolve_prompt` also checks the six-section skeleton (`docs/02` §3.2), so an override is
    # held to the same contract as the file it replaces. Agent Studio's *saved vs your edit*
    # comparison is the only caller that passes one.
    resolved, prompt_hash = resolve_prompt(cfg)
    if system_prompt is not None:
        from twinlab.agents.registry import check_prompt_skeleton
        from twinlab.agents.registry import prompt_hash as _hash_prompt

        check_prompt_skeleton(system_prompt, where="twin (edited in Agent Studio)")
        resolved, prompt_hash = system_prompt, _hash_prompt(system_prompt)
    system_prompt = resolved
    client = get_client()
    expected = list(items)
    points_for = {item_id: item.points for item_id, item in items.items()}
    calls = 0

    async def ask(instruction: str | None):
        nonlocal calls
        calls += 1
        body = assembled if instruction is None else f"{assembled}\n\n{instruction}"
        result = await client.run(
            # The permissive transport shape, never the validating one. Handing the
            # provider `TwinAnswerSet` makes pydantic-ai validate the 37-item register before
            # the ladder sees the reply, which bypasses the whole of `docs/02` §5.4 and
            # contradicts `CLAUDE.md` rule 4. Validation happens below, in Python.
            cfg, system_prompt=system_prompt, user_prompt=body, output_type=AnswerVector
        )
        return result.output

    # The battery round validates through `TwinAnswerSet`, which checks the whole 37-item
    # register; any other item set validates through `QualityAnswerSet`, which checks the ids the
    # caller named. Both read each item's range from the frozen register, never from a constant.
    whole_battery = set(expected) == set(ref.battery_item_ids)
    outcome = await run_answer_ladder(
        ask,
        expected=expected,
        points_for=points_for,
        schema=TwinAnswerSet if whole_battery else QualityAnswerSet,
        attempts=cfg.retry.attempts,
        schema_extra=None if whole_battery else {
            "holdout_set": "H3", "expected_items": expected
        },
    )
    if not outcome.ok or outcome.output is None:
        raise ContractError(
            outcome.reason or "; ".join(str(d) for d in outcome.defects)
            or "the twin did not produce a valid answer vector"
        )

    answers = {k: int(v) for k, v in outcome.output.answers.items()}
    telemetry = {
        "lever_order": list(prompt.lever_order),
        "seed": seed,
        "wording": wording,
        "model": cfg.model.name,
        "prompt_version": prompt_hash[:16],
        "retries": outcome.retries,
        "calls": calls,
        "rationale": getattr(outcome.output, "rationale", ""),
    }
    return answers, telemetry


async def ask_h3_round(
    *,
    twin_id: str,
    paragraphs_by_version: dict[int, dict[str, str]],
    items_by_version: dict[int, dict[str, BatteryItem]],
    seed: int,
    wording: str = "A",
    persona_text: str | None = None,
    temperature: float | None = None,
    model: str | None = None,
    backend: DbBackend | None = None,
) -> tuple[dict[str, int], dict[str, Any]]:
    """The whole of Part 17 in **one** twin call. Returns ``(answers, telemetry)``. M19 WP-3.

    A sibling of :func:`ask_items`, not a replacement for it: the battery round, the Studio and the
    validity tests all still go through that. This exists because the H3 gate is the one place the
    human answered **six stimuli in one sitting** (`docs/01` §3.6) and is scored on whether the
    twin *orders* those six the way its driver did (`docs/08` §3.3). Six isolated calls cannot
    produce an ordering by comparison, and they cost six times as much.

    **No new validation path.** It reuses :func:`run_answer_ladder` with
    :class:`QualityAnswerSet` over the 18 named ids, so the existing targeted repair asks only for
    whatever is missing and a vector that cannot be made valid **fails the repeat** — it is never
    padded, clamped or part-scored (I13, I15).

    I8's guard runs over the assembled prompt exactly as it does for a battery round: no version
    code reaches the text, no why-text travels with the stimulus, and no holdout item outside the
    18 being asked is named.
    """
    from twinlab.agents.twin import build_h3_prompt, build_h3_user_prompt

    db = backend or get_backend()
    ref = reference()
    row = await twin_row(twin_id, db)
    persona = persona_text if persona_text is not None else await persona_for(twin_id, db)
    if not persona.strip():
        raise TwinPathError(f"{twin_id} has an empty persona passage; there is nobody to ask")

    prompt = build_h3_prompt(
        persona_hash=str(row.get("persona_hash") or ""),
        paragraphs_by_version=paragraphs_by_version,
        items_by_version=items_by_version,
        seed=seed,
        wording=wording,
    )
    expected = prompt.item_ids
    assembled = build_h3_user_prompt(prompt, persona)
    # The H3 round asks 18 holdout items, so those 18 are legitimately named; every *other*
    # holdout item — the 16 H2 ones — is still forbidden, as is any version code.
    assert_no_forbidden_content(
        assembled,
        holdout_ids=[
            i
            for i in ref.holdout_h3_item_ids + ref.holdout_h2_item_ids
            if i not in expected
        ],
        why_texts=_why_texts(row),
        version_code=None,
    )
    for code in {
        c for c in _h3_codes_shown(paragraphs_by_version, ref) if c
    }:
        # Checked per code rather than by passing one: the round shows six, and
        # `assert_no_forbidden_content` takes a single code.
        if code in assembled:
            raise TwinPathError(
                f"the H3 round prompt names the version code {code} (I8). The six blocks are "
                "labelled by position only."
            )

    cfg = twin_agent_config(temperature=temperature, model=model, prompt_ref=H3_PROMPT_REF)
    resolved, prompt_hash = resolve_prompt(cfg)
    client = get_client()
    points_for = {
        item_id: item.points
        for version in sorted(prompt.battery)
        for item_id, item in prompt.battery[version].items()
    }
    calls = 0

    async def ask(instruction: str | None):
        nonlocal calls
        calls += 1
        body = assembled if instruction is None else f"{assembled}\n\n{instruction}"
        result = await client.run(
            # The permissive transport shape, never the validating one (`CLAUDE.md` rule 4).
            cfg, system_prompt=resolved, user_prompt=body, output_type=AnswerVector
        )
        return result.output

    outcome = await run_answer_ladder(
        ask,
        expected=expected,
        points_for=points_for,
        schema=QualityAnswerSet,
        attempts=cfg.retry.attempts,
        schema_extra={"holdout_set": "H3", "expected_items": expected},
    )
    if not outcome.ok or outcome.output is None:
        raise ContractError(
            outcome.reason or "; ".join(str(d) for d in outcome.defects)
            or "the twin did not produce a valid 18-item Part 17 vector"
        )

    answers = {k: int(v) for k, v in outcome.output.answers.items()}
    telemetry = {
        # Keyed by version, because there are six orders in this round and not one. Stored so the
        # round reconstructs through `agents.twin.rebuild_h3_prompt` (I11).
        "lever_order": {str(k): v for k, v in prompt.lever_order.items()},
        "seed": seed,
        "wording": wording,
        "model": cfg.model.name,
        "prompt_version": prompt_hash[:16],
        "retries": outcome.retries,
        "calls": calls,
        "protocol": H3_PROTOCOL,
        "rationale": getattr(outcome.output, "rationale", ""),
    }
    return answers, telemetry


async def ask_h3_round_isolated(
    *,
    twin_id: str,
    paragraphs_by_version: dict[int, dict[str, str]],
    items_by_version: dict[int, dict[str, BatteryItem]],
    seed: int,
    wording: str = "A",
    persona_text: str | None = None,
    temperature: float | None = None,
    model: str | None = None,
    backend: DbBackend | None = None,
) -> tuple[dict[str, int], dict[str, Any]]:
    """Part 17 as **six calls, one per version**. Returns ``(answers, telemetry)``.

    The pre-WP-3 protocol, restored as a selectable alternative because the stage-7 decomposition
    implicated the single-context one: the twin's whole residual error is a **per-outcome offset**
    of about one scale point, with scatter of 0.65 that the gate would pass comfortably. A
    constant per outcome and almost no version signal is the signature of one impression emitted
    six times, and a single context is what invites that.

    Each version is asked in its own context through :func:`ask_items` — **the one place a twin is
    called** — so I8's guard, the repair ladder and the output contract are the same ones the
    battery round uses, and no new validation path exists for this to drift through. The six
    three-item vectors are merged into the 18-item vector the scorer expects.

    **A version that cannot be answered fails the whole round**, exactly as the single call does
    when its ladder is refused: a 15-item vector is a different measurement from an 18-item one
    and the missing items are never imputed (I15, I17). The caller discards the repeat.

    ``show_baseline`` is **False** for every call. The driver's own battery answers are in the
    persona as words (I7) and must not arrive as numbers beside a counterfactual question — and
    the single-call protocol shows no baseline either, so this keeps the two comparable in the one
    respect that is not meant to differ.
    """
    ref = reference()
    codes = list(ref.h3_version_codes)
    answers: dict[str, int] = {}
    lever_order: dict[str, Any] = {}
    calls = 0
    retries = 0
    for position in sorted(items_by_version):
        items = items_by_version[position]
        paragraphs = paragraphs_by_version[position]
        code = codes[position - 1] if 1 <= position <= len(codes) else None
        vector, telemetry = await ask_items(
            twin_id=twin_id,
            paragraphs=paragraphs,
            items=items,
            baseline={},
            # Each version gets its own seed, so paragraph position cannot become a confound
            # within a version and the six orders are not identical to one another — the same
            # property `build_h3_prompt` gives the single call.
            seed=seed + position,
            wording=wording,
            show_baseline=False,
            persona_text=persona_text,
            temperature=temperature,
            model=model,
            version_code=code,
            backend=backend,
        )
        answers.update(vector)
        lever_order[str(position)] = telemetry.get("lever_order")
        calls += int(telemetry.get("calls") or 0)
        retries += int(telemetry.get("retries") or 0)

    expected = set(ref.holdout_h3_item_ids)
    missing = sorted(expected - set(answers))
    if missing:
        raise ContractError(
            f"the six-call Part 17 round produced {len(answers)} of {len(expected)} items; "
            f"missing {missing}. A part-scored round is a different measurement and is discarded "
            "rather than imputed (I15, I17)."
        )

    return answers, {
        "lever_order": lever_order,
        "seed": seed,
        "wording": wording,
        "model": (model or twin_agent_config().model.name),
        "retries": retries,
        "calls": calls,
        "protocol": H3_PROTOCOL_ISOLATED,
        "rationale": "",
    }


def _h3_codes_shown(
    paragraphs_by_version: dict[int, dict[str, str]], ref: ReferenceData
) -> list[str]:
    """The version codes this round's blocks stand for, by position. Never shown to the twin."""
    codes = list(ref.h3_version_codes)
    return [
        codes[position - 1] if 1 <= position <= len(codes) else ""
        for position in sorted(paragraphs_by_version)
    ]


async def ask_twin(
    session: Session,
    run_id: str,
    code: str,
    variant: RenderedVariant,
    member: Any,
    *,
    backend: DbBackend | None = None,
) -> dict | None:
    """`SessionRunner`'s ``ask_twin``: one twin, one cell, appended to `twin_answers`.

    Returns the stored row, or ``None`` when the twin failed **for this cell only** — it stays on
    the panel and in the study, because only the quality gate drops twins (`docs/02` §5.4).
    """
    db = backend or get_backend()
    ref = reference()
    twin_id = member.twin_id
    baseline = await driver_answers(twin_id, db)
    battery = battery_for(ref)
    missing = [i for i in battery if i not in baseline]
    if missing:
        # Not padded from anywhere. A twin with no baseline for an item cannot be anchored on it,
        # and the shift for that item would be a number standing in for a measurement.
        log.info(
            "%s: no baseline for %d battery item(s); asking without them",
            twin_id,
            len(missing),
        )

    seed = round_seed(session.session_id, twin_id, code)
    wording = str(session.config.get("wording", "A"))
    show_baseline = bool(session.config.get("show_baseline", True))

    try:
        answers, telemetry = await ask_items(
            twin_id=twin_id,
            paragraphs={k: v.text for k, v in variant.paragraphs.items()},
            items=battery,
            baseline=baseline,
            seed=seed,
            wording=wording,
            show_baseline=show_baseline,
            version_code=code,
            backend=db,
        )
    except (ContractError, TwinPathError) as exc:
        log.warning("%s failed for %s: %s", twin_id, code, exc)
        return None

    return await AnswerRepo(db).record(
        run_id=run_id,
        twin_id=twin_id,
        answers=answers,
        lever_order=telemetry["lever_order"],
        seed=seed,
        wording=wording,
        model=telemetry["model"],
        prompt_version=telemetry["prompt_version"],
        retries=telemetry["retries"],
    )


# ==================================================================== the panel


async def candidates(session: Session, *, backend: DbBackend | None = None) -> list[PanelCandidate]:
    """`SessionRunner`'s ``candidates``: who the panel may be drawn from. `docs/03` §9.1.

    The two filters the draw applies — source and the H3 verdict — live in
    `orchestrator.panel.eligible_candidates`, which is pure. This only reports what the database
    knows, including twins that failed, so the filtering stays in one tested place.
    """
    from twinlab.services.config_match import current_fingerprint, qualified_twin_ids

    db = backend or get_backend()
    rows = await db.select("twins", None, order=("twin_id", False))
    # Qualified under the **live** config only (`005`). A verdict from another model or temperature
    # does not put a twin on a panel, however recently it was kept.
    kept = await qualified_twin_ids(await current_fingerprint(db), db)
    return [
        PanelCandidate(
            twin_id=str(r["twin_id"]),
            source=str(r.get("source") or ""),
            city=r.get("city"),
            service=r.get("service"),
            quality_passed=str(r["twin_id"]) in kept,
        )
        for r in rows
    ]


# ====================================================================== analysis


async def analyse(run_id: str, *, backend: DbBackend | None = None) -> tuple[dict, float, str]:
    """`SessionRunner`'s ``analyse``: the cell's shifts, its index and the Analyst's reading.

    **Every number is computed in Python** (`CLAUDE.md` rule 3). The Analyst is given the finished
    bundle and writes prose *about* it, and that prose is numerically grounded against the bundle
    before it is stored (`docs/02` §6).

    The baseline is each twin's **own driver's** survey answers, so every driver is their own
    control (`docs/07` §3.1), and the twin set is the intersection taken once and used for both
    sides.
    """
    db = backend or get_backend()
    ref = reference()
    run = await RunRepo(db).get(run_id)
    code = run.version_code

    rows = await AnswerRepo(db).for_run(run_id)
    variant_vectors = {
        str(r["twin_id"]): {k: int(v) for k, v in dict(r["answers"]).items()} for r in rows
    }
    battery = ref.battery_item_ids
    baseline_vectors: dict[str, dict[str, int]] = {}
    for twin_id in variant_vectors:
        answers = await driver_answers(twin_id, db)
        vector = {i: answers[i] for i in battery if i in answers}
        # A metric is never computed over a subset (`docs/07` §2.3), so an incomplete baseline
        # excludes that twin from this cell rather than being completed from anywhere.
        if len(vector) == len(battery):
            baseline_vectors[twin_id] = vector

    from twinlab.analysis.metrics import compute_shifts

    weights = await _index_weights(db)
    shifts = compute_shifts(
        baseline_vectors=baseline_vectors,
        variant_vectors=variant_vectors,
        version_code=code,
        weights=weights or None,
        ref=ref,
    )
    metrics = {
        "shifts": dict(shifts.shifts),
        "baselines": dict(shifts.baselines),
        "twin_ids": list(shifts.twin_ids),
        "weights": dict(shifts.weights),
    }
    prose = await _reading(run.session_id, code, shifts, db, ref)
    return metrics, shifts.index_value, prose


async def _index_weights(db: DbBackend) -> dict[str, float]:
    """The Analyst score weights from `app_config['rules']`, or ``{}`` for the unweighted default.

    **The default is unweighted and that is what the paper reports** (`docs/07` §4.1). A non-
    default weight set is recorded on the run, so a reweighted index cannot be mistaken for the
    headline one.
    """
    rows = await db.select("app_config", [("eq", "key", "rules")], limit=1)
    stored = (rows[0].get("value") if rows else None) or {}
    weights = stored.get("weights") if isinstance(stored, dict) else None
    if not isinstance(weights, dict):
        return {}
    return {str(k): float(v) for k, v in weights.items()}


async def _reading(
    session_id: str, code: str, shifts: Any, db: DbBackend, ref: ReferenceData
) -> str:
    """The Analyst's grounded prose, or the deterministic template. `docs/02` §6.2.

    A raised Analyst never fails the run: the cell's numbers are already computed and stored, and
    the reading is prose about them. The fallback carries `FALLBACK_PREFIX` so a reader always
    knows which one they are looking at.
    """
    from twinlab.analysis.report import (
        FALLBACK_PREFIX,
        build_bundle,
        template_reading,
        write_analysis,
    )

    bundle = build_bundle(
        shifts=shifts,
        fairwork_score=0 if code == SHAM_CODE else sum(int(d) for d in code),
        commitment_summary=_commitments(code, ref),
        scenario_text=await _scenario(code, db),
        interactions=None,
        sham_floor=await _sham_floor(session_id, db),
    )
    # RESEARCHER 2026-10-05. The two control floors are not versions: nothing is read from their prose
    # except to label them, and the Analyst's job is prose about a dialled cell. They get the
    # deterministic writer, so a session makes no model call for them. The numbers are the same
    # either way, because the prose never produces one (I12).
    if code in (CONTROL_CODE, SHAM_CODE):
        return f"{FALLBACK_PREFIX} {template_reading(bundle)}"
    try:
        analyst = live_agent("analyst")
    except AgentDisabled:
        # WP-8 item 4. The one agent whose switch has a defined, already-tested meaning: the
        # deterministic template, carrying `FALLBACK_PREFIX` so a reader always knows which they
        # are looking at. **No model call is made** — that is what the switch now buys.
        log.info(
            "the Results Analyst is switched off; using the deterministic template for %s", code
        )
        return f"{FALLBACK_PREFIX} {template_reading(bundle)}"
    try:
        result, used_fallback = await write_analysis(analyst, bundle, get_client())
    except Exception as exc:  # noqa: BLE001 — a raised analyst falls back, never fails the cell
        log.warning("analyst failed for %s: %r", code, exc)
        return f"{FALLBACK_PREFIX} {template_reading(bundle)}"
    return f"{FALLBACK_PREFIX} {result.prose}" if used_fallback else result.prose


def _commitments(code: str, ref: ReferenceData) -> dict[str, list[str]]:
    """Lever → the commitments this cell actually carries, as prose. The Analyst's `TOLD` block."""
    if code in (CONTROL_CODE, SHAM_CODE):
        return {}
    from twinlab.variant.lookup import lookup

    spec = lookup(code, ref)
    return {
        lever: [ref.gaps[g].commitment for g in gap_ids]
        for lever, gap_ids in spec.gaps_by_lever.items()
        if gap_ids
    }


async def _scenario(code: str, db: DbBackend) -> list[str]:
    from twinlab.services.lab import scenario_paragraphs

    return await scenario_paragraphs(code, backend=db)


async def _sham_floor(session_id: str, db: DbBackend) -> float | None:
    """``index(SHAM) − index(00000)`` for **this** session. `docs/07` §6.

    Never pooled across sessions: a floor drawn from a different panel describes different twins,
    and a cell reported against it is reported against nothing.
    """
    from twinlab.analysis.metrics import demand_floor

    async def index_of(code: str) -> float | None:
        rows = await db.select(
            "runs",
            [
                ("eq", "session_id", session_id),
                ("eq", "version_code", code),
                ("eq", "status", "completed"),
            ],
            order=("started_at", True),
            limit=1,
        )
        value = rows[0].get("index_value") if rows else None
        return None if value is None else float(value)

    return demand_floor(await index_of(SHAM_CODE), await index_of(CONTROL_CODE))


# ============================================================== the injected set


def runner_callables(*, backend: DbBackend | None = None) -> dict[str, Any]:
    """What `SessionRunner` needs, in one place. `docs/04` §3.

    The runner takes these injected rather than importing them so the orchestrator's sequencing
    and checkpointing stay testable without a provider (M7). This is the production set.
    """
    db = backend or get_backend()

    async def _render(code: str, style_version: str):
        return await render_and_check(code, style_version, backend=db)

    async def _ask(session, run_id, code, variant, member):
        return await ask_twin(session, run_id, code, variant, member, backend=db)

    async def _analyse(run_id: str):
        return await analyse(run_id, backend=db)

    async def _candidates(session):
        return await candidates(session, backend=db)

    return {
        "render_and_check": _render,
        "ask_twin": _ask,
        "analyse": _analyse,
        "candidates": _candidates,
    }


# ========================================================== the validity `ask`


async def ask_panel_twins(
    *,
    twin_ids: list[str],
    paragraphs: dict[str, str],
    purpose: str,
    temperature: float | None = None,
    wording: str = "A",
    reverse_order: bool = False,
    personas: dict[str, str] | None = None,
    model: str | None = None,
    backend: DbBackend | None = None,
) -> dict[str, dict[str, int]]:
    """`services.validity`'s injected ``ask``. `docs/08` §4.

    Returns ``twin_id → validated answer vector`` over the 37-item battery. **A twin that fails is
    absent from the result**, never present with a partial or invented vector: the tests take the
    intersection of what they got, and a fabricated row would make a failure look like a finding.

    Nothing here is written to `twin_answers`. These are stimuli built for a validity test — test
    4's probe bypassed the lookup and the Checker by construction — and filing them as evidence is
    exactly what `assert_not_a_probe` exists to refuse.

    ``show_baseline`` is read from the **live** `TwinConfig`, never hard-coded. A validity test puts
    the live instrument to the panel; a test that quietly ran a different elicitation than the one
    the live config actually uses would be testing an instrument the study is not running
    (`docs/DECISIONS.md`, 2026-10-07).
    """
    from twinlab.services.config import load_twin_config

    db = backend or get_backend()
    ref = reference()
    battery = battery_for(ref)
    show_baseline = load_twin_config().show_baseline
    out: dict[str, dict[str, int]] = {}
    for twin_id in twin_ids:
        baseline = await driver_answers(twin_id, db)
        try:
            answers, _ = await ask_items(
                twin_id=twin_id,
                paragraphs=paragraphs,
                items=battery,
                baseline=baseline,
                seed=round_seed(purpose, twin_id, wording),
                wording=wording,
                show_baseline=show_baseline,
                persona_text=(personas or {}).get(twin_id),
                temperature=temperature,
                model=model,
                reverse_order=reverse_order,
                backend=db,
            )
        except (ContractError, TwinPathError, RoundPromptError) as exc:
            # `RoundPromptError` added M19 WP-6. It was caught **nowhere** in the codebase —
            # grep-confirmed — so a malformed round killed the whole validity test instead of
            # that twin's turn in it, inside a task that was not being held. It is a `ValueError`,
            # so it slipped past this clause's two named types.
            log.warning("validity %s: %s failed: %s", purpose, twin_id, exc)
            continue
        out[twin_id] = answers
    return out


__all__ = [
    "StoredParagraphPool",
    "TwinPathError",
    "analyse",
    "ask_items",
    "ask_panel_twins",
    "ask_twin",
    "battery_for",
    "candidates",
    "driver_answers",
    "paragraph_pool",
    "persona_for",
    "render_and_check",
    "reset_pool",
    "round_seed",
    "runner_callables",
    "twin_agent_config",
]
