"""ZeroGPU background-task probe. `docs/11_BUILD_PLAN.md` -> M1, `ARCHITECTURE.md` section 8.1.

Answers one undocumented question, and nothing else:

    Does a background `asyncio` task survive at least 30 minutes on a free ZeroGPU Gradio
    Space, with no browser connected?

Everything from M7 onward assumes it does. ZeroGPU is built for request-scoped GPU bursts, so
the assumption is not safe until measured. This is throwaway scaffolding: delete `_probe/` once
M1 closes.

Deliberately self-contained -- it imports nothing from `twinlab` and needs only `gradio`, so a
failure here is a fact about the platform rather than about our dependency set.

Three things are measured at once:

* **survival**  -- the tick counter keeps climbing while nobody is watching;
* **continuity** -- no gap between ticks longer than `GAP_SECONDS`, which would mean the Space
  was suspended and resumed rather than left running;
* **identity**  -- the process boot id is unchanged, which distinguishes "the task kept running"
  from "the Space restarted and began a fresh 30 minutes".

The verdict reads `INCONCLUSIVE` until the full window has elapsed. It never reads `PASS` early,
for the same reason a validity test on zero twins is `INCONCLUSIVE` and never `PASS` (I15): a
gate that can pass without evidence is not a gate.
"""

from __future__ import annotations

import asyncio
import os
import platform
import sys
import time
import uuid

# `datetime.UTC` is 3.11+. The ZeroGPU image is Python 3.10 and ignores the Space card's
# `python_version`, so this file must stay 3.10-compatible. See docs/DECISIONS.md.
from datetime import datetime, timezone

import gradio as gr

# The task ticks at this interval; a silence longer than GAP_SECONDS counts as a suspension.
TICK_SECONDS = 10.0
GAP_SECONDS = 30.0
# The window the build plan requires. Reported in full; not rounded down to a friendlier number.
REQUIRED_SECONDS = 30 * 60

BOOT_ID = uuid.uuid4().hex[:8]
BOOT_WALL = datetime.now(timezone.utc)

STATE: dict[str, object] = {
    "ticks": 0,
    "started_monotonic": None,
    "last_tick_monotonic": None,
    "gaps": [],  # (tick_number, seconds_of_silence)
}

# A strong reference. A task held only by the event loop can be garbage collected mid-flight,
# which would look exactly like the platform killing it -- the one confusion this must avoid.
_task: asyncio.Task[None] | None = None


async def _heartbeat() -> None:
    """Tick forever, recording any silence longer than `GAP_SECONDS`."""
    while True:
        await asyncio.sleep(TICK_SECONDS)
        now = time.monotonic()
        silence = now - float(STATE["last_tick_monotonic"])  # type: ignore[arg-type]
        if silence > GAP_SECONDS:
            STATE["gaps"].append((STATE["ticks"] + 1, round(silence, 1)))  # type: ignore[union-attr]
        STATE["last_tick_monotonic"] = now
        STATE["ticks"] = int(STATE["ticks"]) + 1  # type: ignore[arg-type]


async def start_probe() -> str:
    """Start the heartbeat once, on the first page load.

    Started here rather than at import because there is no event loop at import time, and
    rather than from a `gr.Timer` because a Timer only fires while a browser is attached --
    which would measure the opposite of what this probe is for.
    """
    global _task
    if _task is None or _task.done():
        # Set the clock here, synchronously, so the first report is never a confusing
        # "not started" -- the task exists the moment this returns.
        STATE["started_monotonic"] = time.monotonic()
        STATE["last_tick_monotonic"] = time.monotonic()
        _task = asyncio.create_task(_heartbeat())
    return _render()


def _spaces_state() -> str:
    """ARCHITECTURE.md section 8.2 rule 4: `spaces` is never imported."""
    return "IMPORTED - this is a bug" if "spaces" in sys.modules else "not imported (correct)"


def _render() -> str:
    """The report. Plain text, so it can be pasted into a decision record verbatim."""
    ticks = int(STATE["ticks"])  # type: ignore[arg-type]
    started = STATE["started_monotonic"]
    gaps = list(STATE["gaps"])  # type: ignore[arg-type]

    if started is None:
        return "Probe has not started. Reload the page once."

    elapsed = time.monotonic() - float(started)
    expected = int(elapsed // TICK_SECONDS)
    alive = _task is not None and not _task.done()

    if not alive:
        verdict = "FAIL - the task is no longer running in this process."
    elif gaps:
        verdict = f"FAIL - {len(gaps)} suspension(s); the task stalled and resumed."
    elif elapsed < REQUIRED_SECONDS:
        remaining = int((REQUIRED_SECONDS - elapsed) // 60) + 1
        verdict = f"INCONCLUSIVE - {remaining} more minute(s) needed. Close the tab and return."
    elif ticks < expected - 2:
        verdict = f"FAIL - {expected - ticks} ticks missing; the task was throttled."
    else:
        verdict = "PASS - the task ran unbroken for the full window."

    return "\n".join(
        [
            f"VERDICT   {verdict}",
            "",
            f"boot id           {BOOT_ID}   <- if this changes, the Space restarted",
            f"booted at         {BOOT_WALL.isoformat(timespec='seconds')}",
            f"checked at        {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            "",
            f"task alive        {alive}",
            f"elapsed           {elapsed / 60:.1f} min of {REQUIRED_SECONDS / 60:.0f} required",
            f"ticks recorded    {ticks}",
            f"ticks expected    {expected}   (one every {TICK_SECONDS:.0f}s)",
            f"suspensions       {len(gaps)}   {gaps if gaps else ''}",
            "",
            f"python            {sys.version.split()[0]}"
            "   <- 3.13 is the target; 3.12 is the documented fallback",
            f"platform          {platform.platform()}",
            f"pid               {os.getpid()}",
            f"spaces package    {_spaces_state()}",
        ]
    )


with gr.Blocks(title="ZeroGPU background-task probe") as demo:
    gr.Markdown(
        "## ZeroGPU background-task probe\n"
        "**M1 gate — `ARCHITECTURE.md` §8.1 / §10 question 6.**\n\n"
        "1. This page starts a background task on first load.\n"
        "2. **Close the tab.** Leave it closed for at least 30 minutes — the point is that the "
        "task survives with no browser attached.\n"
        "3. Come back and press **Check**. Read the verdict.\n\n"
        "If the boot id has changed when you return, the Space restarted and the window starts "
        "again. That is itself a finding worth recording."
    )
    report = gr.Textbox(label="Report", lines=18, max_lines=18, interactive=False)
    gr.Button("Check", variant="primary").click(_render, outputs=report)
    demo.load(start_probe, outputs=report)

if __name__ == "__main__":
    demo.launch()
