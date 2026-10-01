"""Shared test setup.

Ground rule (`docs/11` → Ground rules): **never call a live LLM or a live DB in a test.** This
module installs a fresh in-memory backend per test, so no test can reach Supabase even if the
environment happens to carry credentials.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (REPO_ROOT, REPO_ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session", autouse=True)
def _no_live_database():
    """**Nothing in the suite may construct a Supabase client.** Session-scoped, so nothing escapes.

    The per-test fixture below is function-scoped, which means a ``module``- or ``session``-scoped
    fixture that touches the database runs *before* it and gets whatever `get_backend()` builds —
    a live `SupabaseBackend` when the environment carries credentials. That is not hypothetical:
    an M12 integration fixture reached the researcher's real project this way and failed on
    `PGRST205`, because `.env` is populated and the migrations are not applied.

    So the ban is enforced at the factory instead of at the fixture: `SupabaseBackend` raises if
    anything in the suite tries to build one, whatever the fixture scope.
    `tests/test_m12_service.py` asserts it rejects an attempt, because a gate that cannot fail is
    not a gate.
    """
    import twinlab.db.client as client

    def _refuse(*_args, **_kwargs):
        raise AssertionError(
            "a test tried to construct a live SupabaseBackend. No test may reach a live database "
            "(HANDOFF.md §2.4). If this came from a module- or session-scoped fixture, install an "
            "InMemoryBackend inside that fixture rather than relying on the per-test one."
        )

    original = client.SupabaseBackend
    client.SupabaseBackend = _refuse  # type: ignore[assignment]
    client.set_backend(client.InMemoryBackend())
    yield
    client.SupabaseBackend = original  # type: ignore[assignment]
    client.set_backend(None)


@pytest.fixture(autouse=True)
def backend():
    """A fresh :class:`InMemoryBackend` for every test, torn down afterwards.

    Autouse and unconditional: a test that forgot to ask for it still cannot reach a live
    database, which is the point.

    A higher-scoped fixture is **not** covered by this one — see :func:`_no_live_database`, which
    is what actually makes the guarantee hold.
    """
    from twinlab.db.client import InMemoryBackend, set_backend

    instance = InMemoryBackend()
    set_backend(instance)
    yield instance
    set_backend(None)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Run coroutine tests without pytest-asyncio.

    A skipped invariant test is an invariant that is not being guarded
    (`docs/DECISIONS.md` → M1), so the suite drives its own loop rather than depending on a
    plugin being installed and configured.
    """
    func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(func):
        return None
    kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    asyncio.run(func(**kwargs))
    return True
