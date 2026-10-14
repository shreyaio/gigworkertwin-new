"""Regression tests for the Dial board / Agents wiring fixes (M20).

Each test names the defect it guards. These are the places where a researcher's screen showed the
wrong thing without any error: a resume that picked an arbitrary session, and an Ask budget that
priced paragraphs already stored as if they had to be written again.
"""

from __future__ import annotations

import asyncio

from config.settings import settings
from twinlab.db.repositories import SessionRepo
from twinlab.models.reference import LEVER_BY_POSITION
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE, dials
from twinlab.services.runs import (
    missing_paragraph_calls,
    paused_sessions,
    sweep_budget_view,
    sweep_codes,
)


async def test_paused_sessions_come_back_newest_first(backend):
    """Resume must take the session the researcher just stopped, not an arbitrary one.

    Defect: `paused_sessions` sorted by `session_id` (a uuid, so random order) and the Agents
    resume button took the last element. Four sessions make a uuid-order accident very unlikely to
    pass by chance.
    """
    repo = SessionRepo(backend)
    created = []
    for n in range(4):
        session = await repo.create(name=f"run {n}", kind="sweep", iterations=1)
        await repo.set_status(session.session_id, "paused")
        created.append(session.session_id)
        await asyncio.sleep(0.01)  # distinct created_at, so the order is observable

    got = [s.session_id for s in await paused_sessions(backend)]
    assert got == list(reversed(created))


async def test_a_stored_lever_paragraph_is_not_costed_again(backend):
    """Defect: the Ask confirm priced all ten-plus-five paragraphs on every press, so a cell
    whose paragraphs were already written showed 30 calls for five twins.

    I4: a paragraph is keyed (lever, dial, style_version) and written once.
    """
    cells = [CONTROL_CODE, SHAM_CODE, "01000"]
    before = await missing_paragraph_calls(cells, backend=backend)
    # SHAM needs five slots at its own dial; 01000 needs one non-zero lever. Dial 0 needs nothing.
    assert before == 6

    rows = [
        {
            "lever": lever,
            "dial": dial,
            "style_version": settings.style_version,
            "text": "stored",
            "word_count": 1,
        }
        for lever, dial in [
            *[(lever, 3) for lever in LEVER_BY_POSITION],
            *[(lever, d) for lever, d in dials("01000").items() if d != 0],
        ]
    ]
    await backend.insert("lever_paragraphs", rows)
    assert await missing_paragraph_calls(cells, backend=backend) == 0


async def test_an_ask_costs_three_cells_of_twins_and_only_unwritten_paragraphs(backend):
    """The Ask confirm for one version with five twins: 3 cells × 5 = 15 twin calls, plus paragraph
    calls only for what is not yet stored. The twin figure is the research cost; the paragraph
    figure is cache-dependent and must drop to zero once written.
    """
    view = await sweep_budget_view(iterations=1, panel_size=5, start_code="01000", backend=backend)
    # Sessions ask only their version now: 5 twin calls. 01000 has one non-zero lever.
    assert view.calls == 5 + 1
    assert "5 twin call(s)" in view.breakdown
    assert "1 lever paragraph(s) not yet written" in view.breakdown

    await backend.insert(
        "lever_paragraphs",
        [
            {
                "lever": lever,
                "dial": dial,
                "style_version": settings.style_version,
                "text": "stored",
                "word_count": 1,
            }
            for lever, dial in [
                *[(lever, 3) for lever in LEVER_BY_POSITION],
                *[(lever, d) for lever, d in dials("01000").items() if d != 0],
            ]
        ],
    )
    cached = await sweep_budget_view(
        iterations=1, panel_size=5, start_code="01000", backend=backend
    )
    assert cached.calls == 5


def test_sweep_codes_walk_from_the_start_code():
    """The budget must cost the cells the session will actually answer, in walk order."""
    assert sweep_codes(1, "01000") == ["01000"]
    assert sweep_codes(3, "00000") == ["00000", "00001", "00002"]
    assert sweep_codes(0, "01000") == []
