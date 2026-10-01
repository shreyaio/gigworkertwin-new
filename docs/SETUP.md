# Setup — what the researcher does

Everything in the build plan is finished. Nothing here is code work; it is the five things only
you can do, in the order they have to happen.

| # | Step | Blocks |
|---|---|---|
| 1 | Python environment | everything |
| 2 | Supabase project + `001_init.sql` + seed | every run |
| 3 | `.env` | every run |
| 4 | First live smoke run | trusting any number |
| 5 | Google Form + Apps Script | real twins (see `docs/GOOGLE_FORM.md`) |
| 6 | Deploy *(optional)* | unattended intake while you are away from your desk |

Until step 2 is done the app still starts, but it uses an **in-memory backend that keeps nothing
across restarts** and prints a warning saying so. That is fine for clicking around. It is not fine
for a number that goes in the paper.

---

## 1. Python environment

Python **3.11** (the Docker image pins it; 3.13 works locally, which is what the suite has been
run on).

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

Confirm the build is intact before you change anything:

```bash
python -m pytest tests/ -q
```

Expect `212 passed`. Then confirm the frozen reference data still matches its sources:

```bash
python src/twinlab/ingest/build_reference.py --check
```

Expect exit 0. If it fails with `PackageNotFoundError`, one of the `.docx` files is open in Word —
close it and re-run. **Never regenerate or hand-edit `data/reference/*.json`.**

---

## 2. Supabase

### 2.1 Create the project

1. supabase.com → new project. Any region; the free tier is enough.
2. Note the **Project URL** (`https://<ref>.supabase.co`).
3. Settings → API → copy the **`service_role`** key. Not the `anon` key — the app writes.

The `service_role` key bypasses row-level security. It belongs in `.env` and in the Space's secret
store, and **nowhere else**. Never in the repo, never in the Apps Script, never in a screenshot.

### 2.2 Create the schema

Supabase dashboard → **SQL Editor** → New query → paste the whole of
`src/twinlab/db/migrations/001_init.sql` → Run.

It creates 19 tables and two Postgres functions, `runs_complete` and `quality_run_record`. Those
two are not decoration: they are what makes "supersede, never overwrite" atomic (I9). PostgREST
cannot send two statements in one transaction, so the demote and the insert live inside a function.

Verify:

```sql
select count(*) from information_schema.tables where table_schema = 'public';
```

You should see 19. And:

```sql
select proname from pg_proc where proname in ('runs_complete', 'quality_run_record');
```

Both must be listed. If either is missing, re-run the file — a partial schema will fail loudly at
the first completed run, but it is better to find out now.

### 2.3 Seed the reference data

With `.env` filled in (step 3), from the repo root:

```bash
python src/twinlab/ingest/seed_db.py
```

This is idempotent — it upserts on primary key, so running it twice is safe. It ends by asserting
every count in `docs/01` §2: 73 survey items, 10 criteria, the thresholds, the gaps, the corpus
chunks, the three `Met` findings, and the digit-sum identity over all 243 codes. If any assertion
fails it raises `SeedError` and tells you which one. **A database that fails an assertion is not
fit to run a study against** — do not work around it.

To re-check later without writing:

```bash
python src/twinlab/ingest/seed_db.py --check
```

---

## 3. `.env`

Copy `.env.example` to `.env` in the repo root and fill it in. It is gitignored.

| Variable | Required | What it is |
|---|---|---|
| `SUPABASE_URL` | yes | `https://<ref>.supabase.co` |
| `SUPABASE_SERVICE_KEY` | yes | the `service_role` key from step 2.1 |
| `OLLAMA_API_KEY` | yes | your key from ollama.com |
| `OLLAMA_BASE_URL` | no | defaults to `https://ollama.com/v1` |
| `TWINLAB_MODEL` | no | defaults to `gpt-oss:120b` |
| `INTAKE_HMAC_SECRET` | for intake | see below |
| `LOGFIRE_TOKEN` | no | unset disables telemetry entirely; the app runs normally without it |
| `START_CODE` | no | defaults to `10000` — where a fresh sweep begins (ARCHITECTURE §9 Q1) |
| `MAX_CONCURRENCY` | no | defaults to 4 twins in flight |
| `STYLE_VERSION` | no | defaults to `v1`. **Bumping this invalidates every cached paragraph and every variant** — a full re-render. Do it only when you deliberately change the style contract. |

Generate the intake secret once and keep it:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The same value goes in `.env` **and** in the Apps Script (step 5). If they differ, every submission
is rejected with 401 and the driver sees a failure. With the secret unset, the intake route returns
503 rather than accepting unsigned submissions.

The app reads `.env` at import. After editing it, restart the app.

---

## 4. First live smoke run

This is the step that matters most, because **nothing in this repo has ever talked to a real model
or a real database.** All 212 tests run against an in-memory backend and a stub model. The first
live run is where you find out whether Ollama's responses satisfy the checker's schema, whether the
two Postgres functions behave, and what a sweep actually costs.

```bash
uvicorn app:app --reload --port 7860
```

Open `http://127.0.0.1:7860`. The badge at the top should read **Live model**, not Mock model.

Do it in this order, and stop at the first surprise:

1. **Settings tab** → confirm provider `ollama` and the model name. Save.
2. **Logs tab** → Create a session (name it `smoke`, iterations `1`, start code `10000`) → Start.
   The loop runs `00000` and `SHAM` first, as control cells, then `10000`.
3. Watch the tree. You are looking for four things:
   - the `reconstruction` row relabelling through twin ids **on one row**;
   - `render` emitting one child per lever, and only ten design calls in total across the whole
     session — that is I4 holding;
   - `check` passing every gate;
   - `analyse` completing with an index.
4. Click a `render` row. The side panel should show the paragraph and its word count.
5. **Dial board** → set `1 0 0 0 0` → the amber `cached` badge and a `Rerun?` button should appear,
   because you just ran that cell.
6. **Results tab** → `00000` outlined red, `10000` filled, everything else grey.

A twin pool is required for any of this. Until the Form is live, seed demo twins:

```bash
python src/twinlab/ingest/seed_demo_twins.py --count 5
```

They are written with `source = "synthetic"` and ids `DEMO01`… so they can never be mistaken for a
driver or collide with a Form response id. Same `--count` and `--seed`, same twins, always. To
replace them (this removes synthetic rows only — never a real twin, never a run):

```bash
python src/twinlab/ingest/seed_demo_twins.py --count 5 --clear
```

**Delete them before you run anything that goes in the paper.** A synthetic twin is a test double,
not a participant, and the index is meaningless over a pool of them.

### What to watch for on the first live run

- **Checker failures on every cell.** Means the model is not returning the schema the coverage
  probe expects. The event payload shows what it did return. This is the single likeliest failure.
- **Ten design calls, not 243.** If you see more, I4 has broken and the sweep will cost 24× what it
  should. Stop and report it.
- **Cost.** A full sweep is ~4,860 twin calls. Run one cell, read the token counts in the side
  panel, multiply. Do that arithmetic before you start a 243-cell sweep.

---

## 5. Google Form

Its own document: **`docs/GOOGLE_FORM.md`**. It has the exact section names, the exact question
titles, the scales, and the Apps Script to paste in. The question titles are not free text — they
are matched byte for byte against `config/form_map.yaml`, and an unmapped question is rejected with
a 422 rather than silently dropped.

---

## 6. Deploy — optional, and only for unattended intake

**You do not need Docker to use Twin Lab.** Locally the whole app is one command:

```bash
uvicorn app:app --reload --port 7860
```

Deployment buys exactly one thing: a **public URL the Google Form can POST to while you are not at
your desk**. If you are running a pilot and can keep a machine awake, skip this section entirely.

### Do you need it?

| Option | Effort | The catch |
|---|---|---|
| **Hugging Face Space (Docker)** | push the repo, set secrets | first build takes an afternoon |
| **Your machine + a tunnel** (Cloudflare Tunnel, ngrok) | ~10 minutes | the webhook fails whenever the machine is off or asleep |
| **A small VM** running `uvicorn` directly | some sysadmin | no Docker involved |

A failed webhook is **not lost data**: Google keeps every submission in the Form's own responses
sheet whatever happens, and the Apps Script emails you on failure. You re-post it afterwards. So
the tunnel option is a legitimate way to run a pilot, not a shortcut.

### If you do use a Space

It must be the **Docker SDK, not the Gradio SDK** (ARCHITECTURE §7). The Gradio SDK serves a
Gradio app and gives you no way to mount `/api/survey/intake`, which is the whole point of
deploying. **Hugging Face builds the image on their servers from the `Dockerfile` — Docker does
not need to be installed on your machine.**

1. New Space → Docker → blank.
2. Push the repo. The `Dockerfile` is already correct (port 7860, `PYTHONPATH=/app/src`).
3. Space Settings → **Variables and secrets**. Add every `.env` variable as a **secret**, not a
   variable — `SUPABASE_SERVICE_KEY`, `OLLAMA_API_KEY` and `INTAKE_HMAC_SECRET` must never be
   visible in the Space's public config.
4. The Space URL becomes the intake endpoint: `https://<user>-<space>.hf.space/api/survey/intake`.
   That is the URL the Apps Script posts to.

`docker build` has never been run here. Expect the first build to take an afternoon.

### One thing worth de-risking first, Space or not

`requirements.txt` pins `gradio>=5.29,<6.0` per ARCHITECTURE §3, while your environment has 6.x.
The UI is written to work on both, but **the pinned version has never actually been run.** Check it
in a throwaway virtual environment — no Docker needed:

```bash
python -m venv .venv-pinned
```

```bash
.venv-pinned\Scripts\activate; pip install -r requirements.txt; python -m pytest tests/ -q
```

If that passes, the deployed image will behave. If you do have Docker and want the belt-and-braces
version, `docker build -t twinlab .` exercises the real image.

---

## Ongoing: when a submission fails

The intake route writes the raw body to `data/temp/survey_<response_id>.json` **before** it touches
the database, so a database failure leaves a replayable file. To see what is outstanding:

```bash
python src/twinlab/ingest/replay_temp.py
```

To store them:

```bash
python src/twinlab/ingest/replay_temp.py --apply
```

It is idempotent: a mirror whose twin already exists is skipped.

A 422 means a Form question is not in `config/form_map.yaml` — the response body names the exact
question. Add the row, then replay. **The submission is never lost**, which is the whole point of
mirroring first.

On a Hugging Face Space the filesystem is ephemeral: `data/temp` does not survive a restart. If you
run intake in production, either mount persistent storage or download the mirrors regularly.
