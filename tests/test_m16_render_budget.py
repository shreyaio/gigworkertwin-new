"""M16 — the durable re-render budget, and the design agent's view of the register band.

Both changes here are RESEARCHER decisions taken on 2026-10-01 against
`HANDOFF_M15_LIVE_PATH.md` §3.2 and §4.1. See `docs/DECISIONS.md` → M16.

`services/twin_runtime.py` had no tests at all before this file, so the setup is spelled out
rather than shared: a stub design client, an in-memory backend, and a real
:class:`StoredParagraphPool` over both. No live LLM and no live DB (`docs/11` → Ground rules).
"""

from __future__ import annotations

import pytest

from twinlab.agents.registry import StubModelClient
from twinlab.models.variant import CoverageVerdict, LeverBrief
from twinlab.models.variant import LeverParagraph as LP
from twinlab.services import twin_runtime
from twinlab.services.twin_runtime import RENDER_ATTEMPTS_MAX, StoredParagraphPool
from twinlab.variant.render import load_style_contract


@pytest.fixture(autouse=True)
def _fresh_budget():
    """The process-level short-circuit is global state; no test may inherit another's."""
    twin_runtime.reset_pool()
    yield
    twin_runtime.reset_pool()


def _brief(lever: str = "L1", dial: int = 1) -> LeverBrief:
    return LeverBrief(
        lever=lever,
        dial=dial,
        commitments={"1.1.a": "Uber will tell you the fare before you accept a trip."},
        anchor_chunks=["You can see your earnings in the app."],
        style_contract=load_style_contract(),
        do_not_say=["Uber will recognise a drivers association."],
    )


def _client(texts: list[str]) -> StubModelClient:
    """A design client returning ``texts`` in order, then repeating the last one."""
    calls: list[int] = []

    def handler(cfg, prompt, out):
        if out is not LP:
            return CoverageVerdict(entailed=True, reason="stub")
        calls.append(1)
        return LP(text=texts[min(len(calls) - 1, len(texts) - 1)])

    return StubModelClient(handler)


async def _rows(backend) -> list[dict]:
    return await backend.select("lever_paragraphs", [])


# ------------------------------------------------------------------ the durable budget (§3.2)


async def test_a_first_render_records_one_attempt(backend):
    """`attempts` is the denominator I4's design-call count needs. A fresh paragraph costs 1."""
    client = _client(["first paragraph"])
    pool = StoredParagraphPool(backend=backend, client=client)

    await pool.get(_brief())

    rows = await _rows(backend)
    assert len(rows) == 1
    assert rows[0]["attempts"] == 1, "a first render must not look like a re-render"
    assert client.call_count("design") == 1


async def test_a_rerender_charges_the_attempt_to_the_table(backend):
    """The one re-render `docs/03` §5 allows, recorded where a restart cannot lose it."""
    client = _client(["first paragraph", "second paragraph"])
    pool = StoredParagraphPool(backend=backend, client=client)

    await pool.get(_brief())
    again = await pool.rerender(_brief(), instruction="Use shorter sentences.")

    assert again.text == "second paragraph"
    rows = await _rows(backend)
    assert len(rows) == 1, "the re-render must replace the row, not add a second one"
    assert rows[0]["attempts"] == RENDER_ATTEMPTS_MAX
    assert rows[0]["text"] == "second paragraph"
    assert client.call_count("design") == 2


async def test_the_budget_survives_a_restart(backend):
    """§3.2, the defect itself. A new process must not hand the key a fresh re-render.

    `_rerendered` was a module-level set, so this was the whole bug: on a free Space a restart is
    routine, and every restart bought every paragraph another design call.
    """
    client = _client(["first paragraph", "second paragraph"])
    pool = StoredParagraphPool(backend=backend, client=client)
    await pool.get(_brief())
    await pool.rerender(_brief(), instruction="Use shorter sentences.")
    assert client.call_count("design") == 2

    # A restart: the module-level set is cleared and a new pool warms from the same table.
    twin_runtime.reset_pool()
    restarted = StoredParagraphPool(backend=backend, client=client)
    after = await restarted.rerender(_brief(), instruction="Use shorter sentences again.")

    assert client.call_count("design") == 2, (
        "a restart refunded the re-render; the budget is not durable"
    )
    assert after.text == "second paragraph", "the stored paragraph must be served, not re-rendered"
    rows = await _rows(backend)
    assert rows[0]["attempts"] == RENDER_ATTEMPTS_MAX


async def test_a_refused_rerender_does_not_buy_another_one(backend):
    """A `cannot_render` re-render has still been paid for.

    This is the case the handoff actually hit: `L4` dial 2 refused its re-render. Charging after
    the call would have lost the record, and the paragraph would be re-rendered on every restart
    forever.
    """
    calls: list[int] = []

    def handler(cfg, prompt, out):
        if out is not LP:
            return CoverageVerdict(entailed=True, reason="stub")
        calls.append(1)
        if len(calls) == 1:
            return LP(text="first paragraph")
        return LP(text="", status="cannot_render", reason="conflicts with a prohibited statement")

    client = StubModelClient(handler)
    pool = StoredParagraphPool(backend=backend, client=client)
    await pool.get(_brief())

    refused = await pool.rerender(_brief(), instruction="Use shorter sentences.")
    assert refused.status == "cannot_render", "the refusal must reach the caller, not be swallowed"

    rows = await _rows(backend)
    assert len(rows) == 1, "a refusal must not delete the row that records the spend"
    assert rows[0]["attempts"] == RENDER_ATTEMPTS_MAX
    assert rows[0]["text"] == "first paragraph", (
        "a refusal is not a paragraph and must never be stored as one"
    )

    twin_runtime.reset_pool()
    restarted = StoredParagraphPool(backend=backend, client=client)
    await restarted.rerender(_brief(), instruction="Try once more.")
    assert client.call_count("design") == 2, "a refused re-render was refunded on restart"


async def test_dial_zero_never_spends_a_render(backend):
    """I5 — the dial-0 string is a constant and is never generated, so it cannot be re-rendered."""
    client = _client(["never used"])
    pool = StoredParagraphPool(backend=backend, client=client)

    await pool.rerender(_brief(dial=0), instruction="Use shorter sentences.")

    assert client.call_count("design") == 0
    assert await _rows(backend) == []


async def test_the_attempts_ceiling_is_the_specifications_own(backend):
    """`docs/03` §5 — re-render **once**. Two design calls per paragraph, ever, and no third."""
    assert RENDER_ATTEMPTS_MAX == 2

    client = _client(["one", "two", "three"])
    pool = StoredParagraphPool(backend=backend, client=client)
    await pool.get(_brief())
    await pool.rerender(_brief(), instruction="again")
    # Same pool, same key, asked a third time.
    await pool.rerender(_brief(), instruction="and again")

    assert client.call_count("design") == RENDER_ATTEMPTS_MAX


# ------------------------------------------------- the design agent sees the band (§4.1)


def test_the_design_agent_is_shown_the_reading_grade_band():
    """§4.1, RESEARCHER 2026-10-01 — option 3, give the design agent the band.

    The band was withheld on the theory that a number a model cannot act on ends up in the prose.
    Measurement overtook it: every dense lever failed gate 3 at 17.1-18.1 against a 16.0 ceiling
    while the agent was never told the ceiling existed.
    """
    from twinlab.agents.design import STYLE_KEYS_SHOWN, style_block

    style = load_style_contract()
    shown = style_block(style)

    assert "reading_grade_max" in STYLE_KEYS_SHOWN
    assert "reading_grade_min" in STYLE_KEYS_SHOWN, "gate 3 tests both bounds"
    assert shown["reading_grade_max"] == style["reading_grade_max"]
    assert shown["reading_grade_min"] == style["reading_grade_min"]


def test_the_agent_is_still_not_shown_the_lever_ordering():
    """Showing the band is not a licence to show everything.

    `lever_order_to_twin` is an orchestrator concern the agent cannot act on, and `style_version`
    would tell it which contract generation it is serving — a channel into the prose.
    """
    from twinlab.agents.design import STYLE_KEYS_SHOWN

    for key in ("style_version", "lever_order_in_text", "lever_order_to_twin", "dial_zero_text"):
        assert key not in STYLE_KEYS_SHOWN


def test_the_style_block_stays_byte_stable():
    """The render cache key describes a prompt, so the prompt must be reproducible (I11)."""
    from twinlab.agents.design import build_user_prompt

    assert build_user_prompt(_brief()) == build_user_prompt(_brief())


# --------------------------------------------------------- the style_version bump (§4.2)


def test_the_style_contract_and_settings_agree_on_v2():
    """§4.2 — the contract's own MUST, honoured. `style_contract.yaml` bumped, so settings did.

    Paragraphs persisted for the first time in M15, and the §4.1 change alters what the design
    agent is shown, so a v1 paragraph and a v2 paragraph are not written to the same contract.
    """
    from config.settings import settings

    style = load_style_contract()
    assert style["style_version"] == "v2"
    assert settings.style_version == "v2", (
        "a paragraph cached under one style_version served under another is the exact silent "
        "confound the (lever, dial, style_version) key exists to prevent"
    )


# ------------------------------------------------- the boot gate for migration 003


def _prefix_row() -> dict:
    """A `lever_paragraphs` row as a database that has not run 003 would return it."""
    return {
        "lever": "L1", "dial": 1, "style_version": "v2", "text": "x",
        "word_count": 50, "delta_hash": "h", "checker_pass": False,
    }


async def test_boot_refuses_a_database_without_the_attempts_column(backend):
    """Migrations are applied by hand, so the code and the database can disagree.

    Failing at boot is the point: a render that dies on its write has already paid for a design
    call, and a database silently lacking the column reverts the budget to per-process — the exact
    thing `attempts` exists to replace.
    """
    from twinlab.db.client import DbError
    from twinlab.services.config import _check_schema

    backend.tables.setdefault("lever_paragraphs", []).append(_prefix_row())

    with pytest.raises(DbError, match="003_render_attempts.sql"):
        await _check_schema(backend)


async def test_boot_passes_once_the_column_exists(backend):
    from twinlab.services.config import _check_schema

    row = _prefix_row() | {"attempts": 1}
    backend.tables.setdefault("lever_paragraphs", []).append(row)
    await _check_schema(backend)      # must not raise


async def test_an_empty_table_does_not_block_boot(backend):
    """A table with no rows says nothing about its columns, and must not stop the UI booting."""
    from twinlab.services.config import _check_schema

    backend.tables["lever_paragraphs"] = []
    await _check_schema(backend)      # must not raise


# ----------------------------------------- the variant lookup uses the WHOLE key (§2.3 fallout)
#
# `variants` is keyed `(version_code, style_version)`, but four service-layer lookups filtered on
# the version code alone and took the newest row by `created_at`. That was harmless while only one
# style_version had ever existed. The moment v2 arrived it meant a v1 paragraph could be served to
# a v2 app -- a stimulus verified under a style contract it was not written to, which is the exact
# confound `config/style_contract.yaml` bumps the key to prevent.


async def _put_variant(backend, code: str, version: str, *, passed: bool = True) -> None:
    from twinlab.db.repositories import VariantRepo
    from twinlab.models.reference import LEVER_BY_POSITION

    await VariantRepo(backend).put(
        version_code=code,
        style_version=version,
        delta_spec={"version_code": code},
        delta_hash="h",
        paragraphs={lever: {"text": f"{version} text for {lever}"}
                    for lever in LEVER_BY_POSITION},
        checker={"passed": passed},
    )


async def test_twin_studio_will_not_serve_a_variant_from_another_style_version(backend):
    """I3 has no style_version exemption: verified under v1 is not verified under v2."""
    from twinlab.services.studio import StudioBlocked, _stimulus

    await _put_variant(backend, "01000", "v1")      # the orphaned M15 row

    with pytest.raises(StudioBlocked, match="never been rendered"):
        await _stimulus("01000", "", backend)


async def test_twin_studio_serves_the_current_style_version(backend):
    """And it must still work once the cell exists under the version the app is running."""
    from twinlab.services.studio import _stimulus

    await _put_variant(backend, "01000", "v1")
    await _put_variant(backend, "01000", "v2")

    paragraphs, scenario, sandbox = await _stimulus("01000", "", backend)

    assert sandbox is False
    assert all("v2 text" in text for text in paragraphs.values()), (
        f"served a paragraph from the wrong style_version: {paragraphs}"
    )
    assert len(scenario) == 5


async def test_the_scenario_reader_ignores_another_style_versions_row(backend):
    """`services/lab.scenario_paragraphs` — what is shown must be what a twin could be shown."""
    from twinlab.services.lab import scenario_paragraphs

    await _put_variant(backend, "01000", "v1")
    assert await scenario_paragraphs("01000", backend=backend) == []

    await _put_variant(backend, "01000", "v2")
    shown = await scenario_paragraphs("01000", backend=backend)
    assert shown and all("v2 text" in text for text in shown)


async def test_the_validity_stimulus_reader_uses_the_whole_key(backend):
    """Validity tests 4-8 put these paragraphs straight to a twin."""
    from twinlab.services.validity import _paragraphs_for

    await _put_variant(backend, "01000", "v1")
    assert await _paragraphs_for("01000", backend) == {}

    await _put_variant(backend, "01000", "v2")
    found = await _paragraphs_for("01000", backend)
    assert found and all("v2 text" in text for text in found.values())


# -------------------------------------- a passing lever is not re-rolled (the M16 §9 defect)


async def test_a_lever_with_nothing_to_repair_is_not_re_rolled(backend):
    """`_rerender_cell` must leave a paragraph that passed every gate it is judged on alone.

    The defect: `_repair_for` returns `None` for a lever that "missed nothing", that `None` was
    passed straight to `rerender`, and `rerender(instruction=None)` **deletes the row and
    re-renders from the brief**. So one failing lever threw away and re-rolled every *other*
    lever's paragraph in the same cell, spending each one's single durable re-render on a blind
    re-sample of text that had already passed.

    Measured live on 2026-10-01: `L2` dial 1 stored at grade 9.87 and still sat at `attempts = 2`,
    and `L1` dial 1 measured 13.26 in isolation but stored at 17.79 after an instruction-less
    re-roll. `HANDOFF_M15_LIVE_PATH.md` §2.4 read that as the repair failing to converge.
    """
    from twinlab.models.variant import CheckerReport
    from twinlab.services import twin_runtime as tr

    # `01000` has exactly one non-zero lever, L2 at dial 1, so the cell's only paragraph is the
    # one under test and nothing else can account for a design call.
    code = "01000"
    # Measured to pass gate 3: 107 words, Flesch-Kincaid 5.70, inside [4.0, 16.0] and [45, 150],
    # no forbidden term and no forbidden intensifier. It has to genuinely pass, because
    # `_repair_for` re-checks the stored text and would otherwise legitimately ask for a repair.
    clean = (
        "You will receive safety equipment at no cost to you, including a helmet and a jacket. "
        "You will not pay anything for this equipment, now or later. "
        "We will cover you for injury while you are working, starting on your first trip. "
        "The terms of that cover are written in the app so you can read them whenever you want. "
        "We will pay you for the time you spend in training, at the same rate as your trips. "
        "You may ask for a copy of the cover note and we will send it within one working day. "
        "None of this can be withdrawn without telling you first. "
    )
    client = _client([clean, "a worse re-roll"])
    pool = StoredParagraphPool(backend=backend, client=client)

    from twinlab.variant.lookup import lookup
    from twinlab.variant.render import build_brief

    brief = build_brief(lookup(code, pool.ref), "L2", pool.ref, pool.style)
    await pool.get(brief)
    assert client.call_count("design") == 1
    stored_before = await _rows(backend)
    assert len(stored_before) == 1

    # A report that fails the CELL but names nothing wrong with this lever's own paragraph:
    # every commitment covered, no containment hit. `_repair_for` must return None for it.
    report = CheckerReport(
        coverage=dict.fromkeys(brief.commitments, True),
        containment=[],
        word_count=len(clean.split()),
        in_band=True,
        reading_grade=8.0,
        dial_zero_identical=True,
        sham_indistinguishable=True,
        passed=False,
        notes="the cell failed on a gate that is not this lever's paragraph",
    )
    assert tr._repair_for(brief, pool, report) is None, (
        "fixture: this lever must have nothing to repair or the test proves nothing"
    )

    result = await tr._rerender_cell(code, pool, report)

    assert client.call_count("design") == 1, "a passing paragraph was re-rolled"
    assert result is None, "no lever had a repair to make, so there was nothing to re-render"
    after = await _rows(backend)
    assert len(after) == 1
    assert after[0]["text"] == stored_before[0]["text"], "a passing paragraph was replaced"
    assert after[0]["attempts"] == 1, (
        "a passing paragraph spent its durable re-render for nothing"
    )
