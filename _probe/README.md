---
title: Twin Lab ZeroGPU Probe
emoji: ⏱️
colorFrom: gray
colorTo: blue
sdk: gradio
# No python_version pin: ZeroGPU ignores it and serves Python 3.10 regardless
# (measured 2026-09-28). Claiming 3.13 here would be a card that lies.
app_file: app.py
pinned: false
short_description: M1 gate - does a background asyncio task survive on ZeroGPU?
---

# ZeroGPU background-task probe

Throwaway diagnostic for **Twin Lab** M1 (`ARCHITECTURE.md` §8.1, §10 question 6).

Everything from M7 onward assumes a multi-hour background `asyncio` sweep survives on a free
ZeroGPU Gradio Space. Hugging Face does not document whether it does. This measures it.

**How to run it:** open the Space, then close the tab. Wait 30+ minutes. Reopen and press
**Check**.

The report prints the interpreter version, which is the second thing being measured: the
ZeroGPU image is Python 3.10, below the 3.12 fallback named in `ARCHITECTURE.md` §10.

Delete this Space once the answer is recorded.
