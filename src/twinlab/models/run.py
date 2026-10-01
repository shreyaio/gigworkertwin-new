"""Session control shapes. `docs/02` §4.5.

`docs/02` §2.1 names eight registry schemas, and none of them is the Manager's — yet §1 lists the
Manager as one of the five agents. The two shapes it needs are therefore declared here and
registered alongside the eight. See `docs/DECISIONS.md`.

The session state machine, `runs`, `run_events` and the answer records are M7. This module holds
only what the Manager's config needs in order to be the real config from M2.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ManagerState(BaseModel):
    """What the Manager is told about the session. `docs/02` §4.5's three input blocks.

    Deliberately narrow. The Manager cannot choose what a dial means, change a panel, or skip a
    gate, so nothing here describes a dial, a panel or a gate.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    status: str
    cursor_index: int | None = None
    completed: int = 0
    requested: int = 0
    failed_units: list[str] = Field(default_factory=list)
    #: Calls, tokens and estimated time remaining. `orchestrator/budget.py` fills it (M7).
    budget: dict = Field(default_factory=dict)
    #: Stop is cooperative: a flag checked at every checkpoint, never a kill mid-model-call
    #: (`ARCHITECTURE.md` §7.4).
    stop_requested: bool = False


class ManagerDecision(BaseModel):
    """The next single unit of work, or a stop, or a halt. `docs/02` §4.5.

    ``halt`` surfaces the decision to the researcher. A Manager that cannot tell what comes next
    halts; it never guesses a route (`docs/02` §5.5).
    """

    model_config = ConfigDict(extra="forbid")

    action: Literal["run_next", "stop", "halt"]
    unit: str = ""
    #: One line, written to `run_events` with `stage='control'` so routing is inspectable rather
    #: than implicit.
    reason: str = ""


#: `docs/04` §3.1. `created → running → {paused, stopped, completed, failed}`; a paused or stopped
#: session resumes by starting again from its cursor.
SessionStatus = Literal["created", "running", "paused", "stopped", "completed", "failed"]

#: `docs/04` §3.2. A run is `failed` when its checker failed or no twin answered (I15).
RunStatus = Literal["pending", "running", "completed", "failed"]

#: The five per-code stages plus the three session-level ones and `control`. `docs/04` §3.2.
Stage = Literal[
    "lookup", "render", "check", "ask", "analyse",
    "ingestion", "panel", "reconstruction", "control",
]

EventStatus = Literal["running", "ok", "error", "skipped"]


class Budget(BaseModel):
    """A pre-flight cost estimate. `docs/10` §7, `docs/04` §5.4.

    **No researcher should discover the cost of a sweep by running one.** Stored on
    `sessions.budget`, so predicted and actual can be compared afterwards — which is how the
    8 s / 2,300 / 400 assumptions get calibrated.
    """

    model_config = ConfigDict(extra="forbid")

    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_seconds: int = 0
    #: ``None`` until the researcher supplies the rate. The Ollama Cloud free credit allowance is
    #: unpublished (`docs/10` §3.3), and an invented number here would be reported as a cost.
    est_credits: float | None = None
    #: Calls this action will **not** make. "1,240 of 4,860 already answered" turns a re-run from
    #: frightening into routine and makes the cache's value visible (`docs/10` §7).
    cache_hits: int = 0
    warnings: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """One session. `docs/04` §3.1, `docs/01` §6.

    ``panel_size`` and ``panel_seed`` are frozen onto the row: the panel is drawn once and every
    cell in the session uses those twins (I14). A cell answered by a different set of twins is a
    different experiment, so a rerun inherits the original panel unless the researcher explicitly
    chooses otherwise.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    name: str
    status: SessionStatus = "created"
    kind: str = "sweep"
    population: str = "real"
    iterations: int = 1
    start_code: str = "10000"
    #: ``None`` on a fresh session, which is how the loop knows to run the control cells first.
    cursor_index: int | None = None
    completed: int = 0
    panel_size: int = 20
    panel_seed: int = 0
    config: dict = Field(default_factory=dict)
    budget: dict | None = None


class Run(BaseModel):
    """One version code within one session. `docs/01` §6.

    ``twins_n = 0`` with ``status = 'completed'`` is impossible: it is a `failed` run, never a
    result with an index of 0.000 (I15). Enforced in the DDL (`runs_completed_has_twins`), mirrored
    in the in-memory backend, and asserted in the invariant suite.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    session_id: str
    version_code: str
    status: RunStatus = "pending"
    variant_id: str | None = None
    twins_n: int = 0
    metrics: dict | None = None
    index_value: float | None = None
    llm_analysis: str | None = None
    error: str | None = None
    is_latest_for_version: bool = False
    #: ``sweep`` (the frozen panel, from a sweep or a Dial board ask) or ``studio`` (one twin, from
    #: the Twin Studio). `ARCHITECTURE_UPDATE.md` §4.3: a Studio-origin index is computed over one
    #: twin while `00000` and `SHAM` come from the panel, so the two are not the same quantity. The
    #: column makes that live in the data rather than in a reader's head.
    origin: str = "sweep"


class RunEvent(BaseModel):
    """One node of the log tree. `docs/04` §7.

    ``payload`` carries **references and telemetry, never bodies** (§7.2). The DDL caps it at 8 KB
    and `events.redact()` is what keeps it there; the side panel fetches the real artifact from its
    own table when opened.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: int
    session_id: str
    run_id: str | None = None
    parent_event_id: int | None = None
    stage: Stage
    agent: str | None = None
    label: str
    status: EventStatus = "running"
    payload: dict | None = None
