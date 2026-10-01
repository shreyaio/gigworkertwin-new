---
title: Twin Lab
emoji: 🧭
colorFrom: blue
colorTo: green
sdk: gradio
python_version: "3.13"
app_file: app.py
hf_oauth: true
startup_duration_timeout: 30m
pinned: false
license: gpl-3.0
---

# Twin Lab

A researcher workbench that tests 243 versions of Uber's rules on digital twins of real drivers.

A research instrument for *Digital Platform Algorithmic Management: attrition and voice of gig
workers in India*. A driver survey becomes a deterministic persona passage — no LLM. A five-digit
version code selects a frozen set of Fairwork commitments. The platform renders those commitments
into driver-facing scenario text in Uber's voice, shows it to every twin alongside the twin's own
baseline answers, and measures the shift in six outcome metrics.

**The numbers this produces go into a peer-reviewed paper.** Every ambiguity resolves toward
halting: see the seventeen invariants in `ARCHITECTURE.md` §2.

Build specification: `ARCHITECTURE.md` and `docs/01`–`docs/11`. Rules for contributors and coding
agents: `CLAUDE.md`. Work order: `docs/11_BUILD_PLAN.md`.

## Licence

GPL-3.0. The PLS-SEM engine (`openpls-engine`) is GPL-3.0, inherited from `plspm-python`, and
linking it makes this application GPL-3.0 too. This is accepted knowingly for an academic research
instrument — `ARCHITECTURE.md` §3.1.

## Running locally

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r requirements.txt
cp .env.example .env                                # then fill it in
python app.py
```

`app.py` is the Gradio-SDK entrypoint used by the Space. `app_docker.py` mounts the same
`gr.Blocks` under FastAPI for the Docker target. Neither holds logic — `ARCHITECTURE.md` §8.2.

## Access

Access control is Hugging Face OAuth (`hf_oauth: true`), restricted to an organisation via
`hf_oauth_authorized_org` in the Space card. This replaces the prototype's shared passcode.
