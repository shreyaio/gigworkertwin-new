"""Gradio-SDK entrypoint. `ARCHITECTURE.md` §8.2 rule 1.

This is the Hugging Face Space's `app_file`. It holds **no logic**: it builds the Blocks and
launches it. Everything it could be tempted to do belongs in `services/`, so that switching to
`sdk: docker` costs a commit rather than a port.

`spaces` is never imported and nothing is decorated with `@spaces.GPU` (rule 4). All inference is
remote on Ollama Cloud, so no GPU is ever touched. The instrument currently runs locally
(`HANDOFF.md` §0.6); keeping rule 4 is what leaves PRO + Docker a one-commit move.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The package lives under src/ with no install step; this is the smallest shim that makes both
# `python app.py` and `pytest` resolve `twinlab`. docs/DECISIONS.md -> M0.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from twinlab.ui.app import build_ui  # noqa: E402

demo = build_ui()

if __name__ == "__main__":
    demo.launch()
