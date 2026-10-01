"""Pre-flight cost estimates. `docs/04` §5.4, `docs/10` §7.

**No researcher should discover the cost of a sweep by running one.** Every long action is costed
before it starts, and the estimate is stored on `sessions.budget` so predicted and actual can be
compared afterwards — which is how the assumptions below get calibrated.

Two properties matter more than the arithmetic:

* **It counts cache hits.** "1,240 of 4,860 already answered" turns a re-run from frightening into
  routine, and makes the value of the cache visible.
* **It warns before it blocks.** A warning is information; refusing to start would just move the
  researcher's decision out of their hands.

Everything here is **deterministic Python**. No model is consulted about what anything costs, and
nothing here is a metric (I12) — it is an estimate, labelled as one.
"""

from __future__ import annotations

from twinlab.models.run import Budget
from twinlab.orchestrator.odometer import N_CODES

#: Per-call assumptions. **Not measured** — `docs/10` §3 states them as placeholders and `docs/10`
#: §9 step 2 says to replace them from 20 real calls. Named constants so that replacement is one
#: edit and every estimate moves with it.
SECONDS_PER_CALL = 8
TOKENS_IN_PER_CALL = 2300
TOKENS_OUT_PER_CALL = 400

#: A design call is one paragraph: shorter out, and a brief that carries anchor chunks in.
DESIGN_TOKENS_IN = 3000
DESIGN_TOKENS_OUT = 150

#: The 18 H3 numbers come from six rounds of three items, so a quality repeat is 6 calls, not 18.
H3_CALLS_PER_REPEAT = 6

#: Ten non-zero lever paragraphs per style version, plus the one fixed dial-0 string (I4).
DESIGN_CALLS_PER_STYLE_VERSION = 10

#: Seconds over which a sweep earns a warning. `docs/10` §7 — "a sweep over 24 h".
LONG_RUN_SECONDS = 24 * 3600


def _budget(
    *,
    calls: int,
    cache_hits: int = 0,
    tokens_in_per_call: int = TOKENS_IN_PER_CALL,
    tokens_out_per_call: int = TOKENS_OUT_PER_CALL,
    warnings: list[str] | None = None,
) -> Budget:
    """Assemble a :class:`Budget`. ``calls`` is what will actually be made, hits excluded."""
    return Budget(
        calls=calls,
        tokens_in=calls * tokens_in_per_call,
        tokens_out=calls * tokens_out_per_call,
        est_seconds=calls * SECONDS_PER_CALL,
        est_credits=None,          # the free-tier rate is unpublished (docs/10 §3.3)
        cache_hits=cache_hits,
        warnings=list(warnings or []),
    )


def sweep_budget(
    *,
    iterations: int,
    panel_size: int,
    answered_already: int = 0,
    paragraphs_cached: int = 0,
    include_controls: bool = True,
    dropped_twins_in_panel: list[str] | None = None,
    config_changed: bool = False,
) -> Budget:
    """The cost of a sweep. `docs/10` §2.

    ``answered_already`` is the number of (run, twin) pairs `twin_answers` already holds — the
    resume saving, counted as cache hits because they are calls this action will **not** make.

    The control cells are counted: `00000` and `SHAM` run once per session before the sweep and do
    not consume an iteration (`docs/03` §6.1), so they add panel_size calls each but no dials.
    `00000` needs no design call at all — dial 0 is never generated (I5).
    """
    cells = max(iterations, 0) + (2 if include_controls else 0)
    twin_calls = cells * panel_size

    design_calls = max(DESIGN_CALLS_PER_STYLE_VERSION - paragraphs_cached, 0)
    if include_controls:
        design_calls += 5          # the sham's five slots at SHAM_DIAL

    total = twin_calls + design_calls
    hits = min(answered_already, twin_calls) + min(
        paragraphs_cached, DESIGN_CALLS_PER_STYLE_VERSION
    )
    calls = max(total - min(answered_already, twin_calls), 0)

    warnings: list[str] = []
    est_seconds = calls * SECONDS_PER_CALL
    if est_seconds > LONG_RUN_SECONDS:
        warnings.append(
            f"about {est_seconds / 3600:.1f} h at one concurrent request. The free provider tier "
            "permits one, so this is serial; consider fewer iterations or a smaller panel."
        )
    if dropped_twins_in_panel:
        warnings.append(
            f"{len(dropped_twins_in_panel)} twin(s) in this session's frozen panel have since been "
            f"dropped by the quality gate: {sorted(dropped_twins_in_panel)}. The panel is not "
            "redrawn (I14) — a cell answered by a different set of twins is a different experiment."
        )
    if config_changed:
        warnings.append(
            "the config has changed since this session's last run, so its results will not be "
            "directly comparable with the earlier ones."
        )

    budget = _budget(calls=calls, cache_hits=hits, warnings=warnings)
    return budget


def full_sweep_budget(*, panel_size: int, **kwargs) -> Budget:
    """All 243 cells. The number `docs/10` §2 quotes as ~4,860 twin calls at K=20."""
    return sweep_budget(iterations=N_CODES, panel_size=panel_size, **kwargs)


def quality_budget(
    *, twins: int, repeats: int, already_scored: int = 0
) -> Budget:
    """The H3 gate over a population. **The dominant cost of the study**, not the sweep.

    `docs/10`: 18 calls per twin at the default repeats — six version codes per repeat, three
    outcomes read from each round. At N=500 and 3 repeats that is 9,000 calls, which is why
    `CLAUDE.md` asks whether a new call multiplies by the panel before it is added.
    """
    per_twin = H3_CALLS_PER_REPEAT * max(repeats, 1)
    remaining = max(twins - already_scored, 0)
    warnings: list[str] = []
    est_seconds = remaining * per_twin * SECONDS_PER_CALL
    if est_seconds > LONG_RUN_SECONDS:
        warnings.append(
            f"about {est_seconds / 3600:.1f} h for {remaining} twin(s) at {repeats} repeat(s). "
            "This is the study's dominant cost; reducing `quality_runs_per_twin` is a research "
            "decision, not a tuning knob (docs/08 §2.1)."
        )
    return _budget(
        calls=remaining * per_twin,
        cache_hits=already_scored * per_twin,
        warnings=warnings,
    )


def render_budget(*, paragraphs_cached: int = 0) -> Budget:
    """Rendering the ten lever paragraphs. I4 — ten per style version, never 243."""
    calls = max(DESIGN_CALLS_PER_STYLE_VERSION - paragraphs_cached, 0)
    return _budget(
        calls=calls,
        cache_hits=min(paragraphs_cached, DESIGN_CALLS_PER_STYLE_VERSION),
        tokens_in_per_call=DESIGN_TOKENS_IN,
        tokens_out_per_call=DESIGN_TOKENS_OUT,
    )


def ask_budget(*, panel_size: int, answered_already: int = 0) -> Budget:
    """One cell put to the panel — the Dial board's "Ask the twins" confirm step."""
    remaining = max(panel_size - answered_already, 0)
    return _budget(calls=remaining, cache_hits=min(answered_already, panel_size))
