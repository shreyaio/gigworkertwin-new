"""Application settings.

Secrets and deployment-level values come from the environment (`ARCHITECTURE.md` §8.3).
Values marked *CONFIG* that the researcher edits from the UI live in the `app_config` table and
in the YAML files beside this module; the fields here are their process-level defaults, used
before a database is reachable and as the seed for a fresh install.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"

# I16: the Space's disk is ephemeral and resets on restart. Nothing durable is written here —
# this is scratch space for a single request, and no code may treat it as storage.
TEMP_DIR = DATA_DIR / "temp"


class Settings(BaseSettings):
    """Environment-backed settings. See ``ARCHITECTURE.md`` §8.3 for the variable list."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database ---
    supabase_url: str = ""
    supabase_service_key: str = ""

    # --- LLM ---
    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com/v1"
    twinlab_model: str = "gpt-oss:120b"

    #: A **genuinely different** OpenAI-compatible endpoint, for `ModelRef.provider = "openai"`.
    #:
    #: Empty by default, and `agents.registry.resolve_model` refuses that provider while it is
    #: empty rather than falling back. Ollama Cloud speaks the OpenAI wire format, so `openai`
    #: used to resolve through the **same** `OpenAIProvider(base_url=ollama_base_url,
    #: api_key=ollama_api_key)` as `ollama` — selecting it in Agent Studio changed nothing, sent
    #: the Ollama key to Ollama, and recorded a provider the call never reached. Harmless while
    #: both landed somewhere real; a silent misattribution in the evidence the moment a second
    #: endpoint exists, which validity test 7 is the reason to want (`docs/DECISIONS.md`
    #: 2026-10-08).
    openai_base_url: str = ""
    openai_api_key: str = ""

    # --- Telemetry ---
    logfire_token: str = ""

    # --- Intake ---
    intake_hmac_secret: str = ""
    #: The driver-facing Google Form. `docs/06` §2 requires the Driver survey screen to show the
    #: form link; the link is deployment configuration, not a constant, so it is not hard-coded.
    #: Empty means "not configured yet", which the screen states rather than rendering a dead
    #: link.
    survey_form_url: str = ""
    #: The Supabase Edge Function that receives submissions (`docs/04` §8). The Driver survey
    #: screen reports whether intake is configured; it never calls this from the Space.
    survey_intake_url: str = ""

    # --- Access control. Replaces the prototype's passcode (ARCHITECTURE §8.1). ---
    hf_oauth_org: str = ""

    # --- Orchestrator (CONFIG) ---
    # 00000 runs once per session as the control cell; the sweep proper starts here (§5.1).
    start_code: str = "10000"
    max_active_sessions: int = 1
    # The free Ollama Cloud tier permits ONE concurrent request (§7.1). 1 is the tested default,
    # not an edge case; the pool exists so a paid plan becomes 3 or 10 without a code change.
    max_concurrency: int = 1
    delay_seconds: float = 0.0
    yield_every: int = 0

    # --- The database boundary (ARCHITECTURE_UPDATE.md §3.2) ---
    # supabase-py is synchronous and every call runs in `asyncio.to_thread`, so one HTTP client is
    # shared across an unbounded thread pool. `max_concurrency` above bounds the *provider*;
    # nothing bounded the database, and 133 HTTP/2 streams on one connection is what the
    # `ConnectionTerminated` / `WinError 10035` pair was reporting.
    db_max_concurrency: int = 4
    # HTTP/1.1 keep-alive suits many small sequential requests; the study's query volume never
    # needs multiplexing. Settable so a deployment that sees the opposite can turn it back on.
    db_http2_disabled: bool = True

    # --- The frozen analysis panel (I14, §7.3) ---
    panel_size: int = 20

    # --- Versioned artefacts frozen onto every run (I11) ---
    # v2 from 2026-10-01: the design agent is now shown the reading-grade band.
    # v3 from 2026-10-03: the word band is resolved per (lever, dial) from the commitment
    # count rather than being one pair of scalars. See `config/style_contract.yaml` HISTORY.
    # Must equal `style_contract.yaml`'s own key; a test asserts it.
    style_version: str = "v9"
    persona_template_version: str = "v1"

    # --- UI ---
    # gr.Timer polling interval for the log tree (§3.3). Not websockets.
    log_poll_seconds: float = 1.0

    @property
    def logfire_enabled(self) -> bool:
        return bool(self.logfire_token)

    @property
    def db_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def model_badge(self) -> str:
        """Header badge text (`docs/06` §0). Absent key ⇒ nothing live can be called."""
        return f"Live: {self.twinlab_model}" if self.ollama_api_key else "Mock model"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
