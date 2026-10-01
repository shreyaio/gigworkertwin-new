"""The tool allow-list. `docs/02` §2.

``TOOL_REGISTRY`` is the *only* place a tool name resolves. `build_agent()` looks every name in a
config's ``tools`` list up here and raises on an unknown one, which is why the list is an
allow-list rather than a set of capability flags: one check, in one place, and a config diff shows
the whole surface.

**Design and Twin hold no tools, ever** (I2, I6) — not by omission from this file, but because
`registry.TOOLLESS_AGENTS` refuses to build them with any. A tool added here can never reach them.

The Manager's session tools are M7 and the Analyst's metric readers are M8. Registering one is a
single line; the registry exists at M2 so that later milestones add to it rather than rewriting
five agents around it.
"""

from __future__ import annotations

from collections.abc import Callable

#: name → callable.
TOOL_REGISTRY: dict[str, Callable] = {}


def _not_until(milestone: str, what: str) -> Callable:
    """A registered name whose implementation belongs to a later milestone.

    It raises. A tool that returned a plausible empty answer would let the Manager route on
    fiction, and routing on fiction is not distinguishable downstream from routing correctly.
    Failing loudly is the specified behaviour (`CLAUDE.md` → "fail loudly and stop").
    """

    def _stub(*_args: object, **_kwargs: object) -> object:
        raise NotImplementedError(
            f"{what} is not implemented yet — it belongs to {milestone}. "
            "The name is registered so config/agents.default.yaml is the real config from M2."
        )

    _stub.__name__ = what
    _stub.__doc__ = f"{what} — implemented in {milestone}."
    return _stub


def register_tool(name: str, fn: Callable) -> None:
    """One-line registration for a new agent's tool (`docs/02` §2.1).

    Re-registering a name raises: two different callables answering to one tool name would make
    `agent_configs.tools` ambiguous, and a run's provenance would no longer say what it ran.
    """
    if name in TOOL_REGISTRY and TOOL_REGISTRY[name] is not fn:
        raise ValueError(f"tool {name!r} is already registered to something else")
    TOOL_REGISTRY[name] = fn


# The Manager's three session tools. `docs/02` §1: "Its tools read and advance session state; that
# is all." They are named here so the Manager's seed config is its real config from M2, and they
# raise until M7 builds the session state machine behind them.
#
# Note what is NOT here and never will be: anything that could choose what a setting means, change
# who answers, alter a limit, or pass over a gate (`docs/02` §4.5).
register_tool("session_state", _not_until("M7", "session_state"))
register_tool("advance_cursor", _not_until("M7", "advance_cursor"))
register_tool("record_decision", _not_until("M7", "record_decision"))
