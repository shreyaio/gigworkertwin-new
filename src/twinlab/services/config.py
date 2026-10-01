"""Configuration service.

`ARCHITECTURE.md` §8.2 rule 3: every capability is a service-layer function. The UI and the
optional API both come through here, so no feature depends on an HTTP route existing.

This layer may import everything below it and must never import ``gradio`` or ``fastapi``
(`ARCHITECTURE.md` §4).
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

import yaml

from config.settings import CONFIG_DIR, settings
from twinlab.db.client import DbBackend, DbError, get_backend
from twinlab.ingest.reference_store import reference, reference_hash
from twinlab.ingest.seed_db import REFERENCE_CONFIG_KEY
from twinlab.models.analysis import AnalysisConfig
from twinlab.models.twin import TwinConfig

log = logging.getLogger(__name__)


class ConfigMissing(RuntimeError):
    """A config file the application refuses to default for."""


class ReferenceMismatch(RuntimeError):
    """The database was seeded from different reference data than this checkout holds.

    Every number the instrument produces is a lookup over `data/reference/`. A database seeded
    from a different build of it would yield results that cannot be traced back to Uber's
    published words, which is the one thing the chain exists to guarantee — so the application
    refuses to boot rather than running (`docs/11` → M1).
    """


async def verify_reference_hash(backend: DbBackend | None = None) -> str | None:
    """Compare the seeded reference digest against this checkout's.

    Returns the stored digest, or ``None`` when nothing has been seeded yet — an unseeded
    database is a setup step, not a mismatch. A *different* digest raises.
    """
    backend = backend or get_backend()
    rows = await backend.select("app_config", [("eq", "key", REFERENCE_CONFIG_KEY)])
    if not rows:
        return None
    stored = rows[0].get("value", {}).get("hash")
    local = reference_hash()
    if stored != local:
        raise ReferenceMismatch(
            f"database reference hash {stored} != data/reference/ hash {local}. "
            "This project was seeded from different reference data; re-seed it or point at the "
            "right project. Refusing to start."
        )
    return stored


def startup_check() -> None:
    """The boot-time gates. Called once while the UI is built, before anything is served.

    Runs its own event loop deliberately: there is no running loop at build time, and this must
    not become a Gradio handler (`docs/DECISIONS.md` — ``asyncio.run`` in a handler closes the
    loop and takes any enqueued session task with it).
    """
    reference()  # loads and validates all ten files; a count mismatch raises here
    backend = get_backend()
    if backend.name != "supabase":
        log.warning("reference hash not verified: no live database configured")
        return
    stored = asyncio.run(verify_reference_hash(backend))
    if stored is None:
        log.warning("database holds no reference digest yet — run ingest/seed_db.py")
    else:
        log.info("reference hash verified: %s", stored[:12])

    asyncio.run(_check_schema(backend))
    asyncio.run(refresh_twin_config(backend))
    asyncio.run(_correct_agent_models(backend))
    asyncio.run(_pause_interrupted(backend))


#: Columns added by a migration later than the one the live project was built from, and the file
#: that adds each. Checked at boot because the alternative is a mid-render failure on the first
#: write — by which point a design call has already been paid for.
_REQUIRED_COLUMNS: dict[str, dict[str, str]] = {
    "lever_paragraphs": {"attempts": "003_render_attempts.sql"},
    # ARCHITECTURE_UPDATE.md §4.3, §4.4 and §7. All three are written by code that now exists, so
    # a database without 004 would fail on the first Twin Studio ask — after the twin call has been
    # paid for, which is the failure this gate exists to move to boot.
    "runs": {"origin": "004_studio_origin.sql"},
    "studio_runs": {"is_latest_for_twin_version": "004_studio_origin.sql"},
    "sessions": {"purpose": "004_studio_origin.sql"},
}


async def _check_schema(backend: DbBackend) -> None:
    """Refuse to boot against a database missing a column the code writes.

    Migrations are applied by hand in the Supabase SQL editor (`HANDOFF.md` §0.7), so the code and
    the database can disagree. This fails **loudly and early**, naming the file to run: a render
    that dies on its write has already spent a design call, and `lever_paragraphs.attempts` is the
    durable re-render budget, so a database without it silently reverts to the per-process budget
    this column exists to replace.
    """
    for table, columns in _REQUIRED_COLUMNS.items():
        try:
            rows = await backend.select(table, [], limit=1)
        except Exception as exc:  # noqa: BLE001 — a missing table is 001/002's problem, not this
            log.warning("could not check %s for new columns: %r", table, exc)
            continue
        if not rows:
            continue  # an empty table tells us nothing about its columns
        for column, migration in columns.items():
            if column not in rows[0]:
                raise DbError(
                    f"`{table}.{column}` is missing from the live database. Run "
                    f"`src/twinlab/db/migrations/{migration}` in the Supabase SQL editor, then "
                    "restart. Nothing is broken and no evidence is at risk — the code writes this "
                    "column and Postgres would reject the write."
                )


async def _correct_agent_models(backend: DbBackend) -> None:
    """`ARCHITECTURE_UPDATE.md` §1.2 and §5.5 item 2: the model is `gpt-oss:120b` only.

    Run at boot rather than offered as a button, because the stale row this repairs is **invalid
    against the code** — `ModelRef.provider` has no `mistral` member — so Agent Studio cannot load
    it
    in order to offer the repair. A seed correction that the damage prevents is not a correction.

    Idempotent: it acts only when a stored row's provider or model name disagrees with
    `config/agents.default.yaml`, skips frozen agents, and writes an `agent_config_history` row for
    everything it touches. Failures are logged and swallowed — this is hygiene, and a database that
    cannot be reached must not stop the UI booting.
    """
    from twinlab.services.agent_config import correct_stale_models

    try:
        corrected = await correct_stale_models(backend=backend)
    except Exception as exc:  # noqa: BLE001 — never block boot on a seed correction
        log.warning("could not correct stale agent models: %r", exc)
        return
    for entry in corrected:
        if entry["skipped"]:
            log.warning(
                "%s still stores %s/%s but is frozen, so it was left alone. Unfreeze it in Agent "
                "Studio to correct it.",
                entry["agent_id"], entry["was"]["provider"], entry["was"]["name"],
            )
        else:
            log.info(
                "corrected %s from %s/%s to %s/%s (ARCHITECTURE_UPDATE.md §1.2)",
                entry["agent_id"],
                entry["was"]["provider"], entry["was"]["name"],
                entry["now"]["provider"], entry["now"]["name"],
            )


async def _pause_interrupted(backend: DbBackend) -> None:
    """`docs/04` §3.4 and §11's `on_startup`: a session found `running` at boot is marked `paused`.

    It was specified, implemented in `orchestrator/loop.py`, tested — and called by nothing. The
    v1.0 FastAPI lifespan that called it did not survive the 2026-09-28 rebuild, so a session
    killed by a restart stayed `running` forever: `active_runners()` is empty after a restart, so
    Stop reports `False` and the session can never be resumed or stopped through the UI.

    **Nothing auto-restarts.** Failures here are logged and swallowed: crash recovery is a
    convenience, and a database that cannot be reached must not stop the UI booting.
    """
    from twinlab.orchestrator.loop import resume_interrupted_sessions

    try:
        paused = await resume_interrupted_sessions(backend)
    except Exception as exc:  # noqa: BLE001 — never block boot on crash recovery
        log.warning("could not pause interrupted sessions: %r", exc)
        return
    if paused:
        log.info("paused %d session(s) interrupted by a restart: %s", len(paused), paused)


def model_badge() -> str:
    """Text for the header badge: ``Mock model`` or ``Live: <model name>`` (`docs/06` §0).

    Nothing is 'live' without a key, so the badge is derived from the key's presence rather
    than from a separate flag that could disagree with it.
    """
    return settings.model_badge


@lru_cache(maxsize=1)
def seed_twin_config() -> TwinConfig:
    """`config/twin.default.yaml` → a validated :class:`TwinConfig`. `ARCHITECTURE.md` §4.

    Validated on load, not on use: `TwinConfig` forbids extras, so a typo'd or invented setting
    fails here rather than being silently ignored and leaving the gate running on defaults the
    researcher did not choose.

    This is the **seed** config. Live values live in `app_config`, and a session freezes whatever it
    ran with onto `sessions.config` (`docs/09` §4), so a threshold change is visible in the data
    rather than silently retroactive.
    """
    path = CONFIG_DIR / "twin.default.yaml"
    if not path.exists():
        raise ConfigMissing(
            f"{path} is absent. It is the seed TwinConfig named by ARCHITECTURE.md §4; the quality "
            "gate's thresholds are not defaulted in code so that a missing file fails loudly "
            "rather than running the gate on invented numbers."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # `seed_db.py` reads `max_concurrency` out of this file to build the `orchestrator` app_config
    # row, so the key lives there although it is not a property of the twin. Popped **by name**
    # rather than by tolerating extras: `TwinConfig` forbids extras so a typo'd threshold fails
    # loudly, and a blanket filter would throw that away.
    concurrency = raw.pop("max_concurrency", None)
    if concurrency is not None and concurrency != settings.max_concurrency:
        raise ConfigMissing(
            f"twin.default.yaml max_concurrency={concurrency} disagrees with "
            f"settings.max_concurrency={settings.max_concurrency}. The value is declared in two "
            "places and both are read — seed_db writes the YAML value to app_config while the "
            "orchestrator honours the settings value, so a disagreement means the recorded "
            "concurrency is not the one that ran."
        )
    return TwinConfig(**raw)


#: The live override read from `app_config['twin']`, and the version it came from.
#:
#: The Settings tab writes a new `app_config` version and **nothing read it back**, so a
#: researcher who changed a quality threshold saw a success message and changed nothing. This is
#: the read path. It is a process-level cache rather than a per-call database read because
#: `load_twin_config()` is called on hot paths (every twin round reads `wording` and
#: `show_baseline`), and it is refreshed at boot, after a save, and at the start of every session
#: and quality run — the three moments at which the live value can differ from the cached one.
_override: dict[str, object] = {}
_override_version: int | None = None


def load_twin_config() -> TwinConfig:
    """The TwinConfig **actually in force**: `app_config['twin']` over the YAML seed.

    `docs/09` §4 makes the YAML the *seed* and `app_config` the live values. Validated through the
    same model either way, so a stored row that no longer satisfies `TwinConfig` fails loudly here
    rather than running the gate on a setting the researcher did not choose.
    """
    if not _override:
        return seed_twin_config()
    merged = {**seed_twin_config().model_dump(), **_override}
    return TwinConfig(**merged)


def twin_config_version() -> int:
    """The `app_config` version the live TwinConfig came from. 1 when nothing is stored.

    Recorded on every `twin_quality_runs` row, so a threshold change is visible in the evidence
    rather than silently retroactive (`docs/08` §2.2).
    """
    return _override_version or 1


async def refresh_twin_config(backend: DbBackend | None = None) -> TwinConfig:
    """Re-read `app_config['twin']` into the process. Returns the config now in force.

    Failures are logged and swallowed: an unreachable database must not stop a UI tick, and the
    seed config is a defined state to fall back to. A **stored row that does not validate** is a
    different thing and raises — running on a config the researcher did not choose is the failure
    this whole module exists to prevent.
    """
    global _override, _override_version
    db = backend or get_backend()
    try:
        rows = await db.select("app_config", [("eq", "key", "twin")], limit=1)
    except Exception as exc:  # noqa: BLE001 — never block a UI tick on a config read
        log.warning("could not read app_config['twin']: %r", exc)
        return load_twin_config()
    if not rows:
        _override, _override_version = {}, None
        return load_twin_config()

    stored = rows[0].get("value") or {}
    if not isinstance(stored, dict):
        raise ConfigMissing(
            f"app_config['twin'].value is {type(stored).__name__}, not an object. The live "
            "TwinConfig is not readable and the gate must not run on the seed as though it were "
            "the researcher's choice."
        )
    known = set(TwinConfig.model_fields)
    # Unknown keys are dropped rather than passed through: `seed_db` writes `max_concurrency` into
    # this row (it is not a TwinConfig field) and `TwinConfig` forbids extras.
    _override = {k: v for k, v in stored.items() if k in known}
    _override_version = int(rows[0].get("version") or 1)
    cfg = load_twin_config()  # validates; raises if the stored row cannot be run
    log.info("live TwinConfig v%s: %s", _override_version, sorted(_override))
    return cfg



@lru_cache(maxsize=1)
def load_analysis_config() -> AnalysisConfig:
    """`config/analysis.default.yaml` → a validated :class:`AnalysisConfig`. `docs/07` §4.1.

    **The default is unweighted and that is what the paper reports.** A non-default weight set is
    recorded on the run and shown in the UI, so a reweighted index cannot be mistaken for the
    headline one.
    """
    path = CONFIG_DIR / "analysis.default.yaml"
    if not path.exists():
        raise ConfigMissing(
            f"{path} is absent. It carries the index weights and the bootstrap floor; neither is "
            "defaulted in code, so a missing file fails loudly rather than reporting an index "
            "computed from invented weights."
        )
    return AnalysisConfig(**(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))
