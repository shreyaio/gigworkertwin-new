"""Shared test helpers for the config-matched quality test (`005`, RESEARCHER 2026-10-05).

A twin is qualified for a config only by a latest H3 verdict made under its fingerprint
and both control answers under it. Every test that needs a qualified twin goes through here, so the
shape of a qualification lives in one place and cannot drift from the production rule.
"""

from __future__ import annotations

from twinlab.db.repositories import ControlAnswerRepo
from twinlab.orchestrator.odometer import CONTROL_CODE, SHAM_CODE
from twinlab.services.config_match import current_fingerprint

#: A fixed fingerprint for tests that build sessions without the live config.
TEST_FINGERPRINT = "test-fp"


async def qualify(
    backend,
    twin_id: str,
    *,
    kept: bool = True,
    fingerprint: str | None = None,
    item_ids: list[str] | None = None,
) -> str:
    """Give a twin a latest H3 verdict and both control answers under ``fingerprint``.

    Defaults to the live fingerprint, which is what a real gate run produces. Returns the
    fingerprint used, so a test can assert against it.
    """
    fp = fingerprint or await current_fingerprint(backend)
    await backend.insert(
        "twin_quality_runs",
        [{
            "twin_id": twin_id, "holdout_set": "H3", "mae": 0.4, "pct_within_1": 0.95,
            "kept": kept, "items_n": 18, "detail": {}, "is_latest": True,
            "config_fingerprint": fp,
        }],
    )
    repo = ControlAnswerRepo(backend)
    for code in (CONTROL_CODE, SHAM_CODE):
        await repo.record(
            twin_id=twin_id, control_code=code, fingerprint=fp,
            answers={item: 3 for item in (item_ids or ["AMQ1"])},
            lever_order=[0, 1, 2, 3, 4], seed=1, wording="A", model="stub",
            prompt_version=None, retries=0, session_id=None,
        )
    return fp
