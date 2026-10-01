"""Docker entrypoint. `ARCHITECTURE.md` §8.2 rule 1.

The same `gr.Blocks` as `app.py`, mounted under FastAPI so the optional `api/` routers can be
served alongside it. It holds **no logic** either: if these two files ever diverge in behaviour,
portability rule 1 has been broken.

The API is a wrapper, never load-bearing (rule 3) — this file must remain deletable without
costing a feature.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import gradio as gr  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from twinlab.ui.app import build_ui  # noqa: E402

app = FastAPI(title="Twin Lab")
app = gr.mount_gradio_app(app, build_ui(), path="/")
