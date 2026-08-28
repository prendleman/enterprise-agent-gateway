"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiKeyEntry(BaseModel):
    """Hashed demo API key mapped to tenant and role."""

    hash: str
    subject: str
    tenant_id: str
    role: Literal["employee", "analyst", "facilities_manager", "platform_admin"]


# Pre-computed SHA-256 hashes of local-only demo keys (plaintext keys documented in README).
_DEMO_API_KEYS: list[ApiKeyEntry] = [
    ApiKeyEntry(
        hash="9fd4741530be63f525a251203450d862bfebe821038ee3112aa4293b75930fa6",
        subject="employee-northstar",
        tenant_id="northstar-facilities",
        role="employee",
    ),
    ApiKeyEntry(
        hash="3081b869e862cf18b788f53dbedab8a5973e16118fd2f7a851a5fa11ac194e26",
        subject="analyst-northstar",
        tenant_id="northstar-facilities",
        role="analyst",
    ),
    ApiKeyEntry(
        hash="14db7fe0f5af479835f5c66f8c061f54bd0d2d70118f714dc3afe669b847baf6",
        subject="fm-northstar",
        tenant_id="northstar-facilities",
        role="facilities_manager",
    ),
    ApiKeyEntry(
        hash="f44168ca47410137ebec8c1e6785ccde618168c4d633677b784ece948870dfda",
        subject="analyst-lakeshore",
        tenant_id="lakeshore-properties",
        role="analyst",
    ),
    ApiKeyEntry(
        hash="cce7a2cf1ae045989cfc914fb95a41526f167a838b3c7d33745143614abace7c",
        subject="platform-admin",
        tenant_id="northstar-facilities",
        role="platform_admin",
    ),
]


class Settings(BaseSettings):
    """Runtime settings with demo-mode defaults suitable for local development."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Enterprise Agent Gateway", alias="APP_NAME")
    app_env: Literal["demo", "dev", "staging", "production"] = Field(
        default="demo",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./artifacts/agent_gateway.db",
        alias="DATABASE_URL",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    log_json: bool = Field(default=True, alias="LOG_JSON")

    demo_mode: bool = Field(default=True, alias="DEMO_MODE")

    request_id_header: str = Field(default="X-Request-ID", alias="REQUEST_ID_HEADER")

    readiness_db_check: bool = Field(default=True, alias="READINESS_DB_CHECK")

    datasets_dir: str = Field(default="datasets", alias="DATASETS_DIR")
    artifacts_dir: str = Field(default="artifacts", alias="ARTIFACTS_DIR")

    model_pricing_path: str = Field(
        default="config/model_pricing.example.yaml",
        alias="MODEL_PRICING_PATH",
    )
    models_config_path: str = Field(
        default="config/models.example.yaml",
        alias="MODELS_CONFIG_PATH",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_default_model: str | None = Field(default=None, alias="OPENAI_DEFAULT_MODEL")
    anthropic_default_model: str | None = Field(
        default=None,
        alias="ANTHROPIC_DEFAULT_MODEL",
    )
    use_fake_providers: bool = Field(default=False, alias="USE_FAKE_PROVIDERS")

    policies_path: str = Field(default="config/policies.yaml", alias="POLICIES_PATH")
    tool_permissions_path: str = Field(
        default="config/tool_permissions.yaml",
        alias="TOOL_PERMISSIONS_PATH",
    )
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    api_key_entries: list[ApiKeyEntry] = Field(default_factory=lambda: list(_DEMO_API_KEYS))

    max_query_length: int = Field(default=2000, alias="MAX_QUERY_LENGTH")
    max_tool_steps: int = Field(default=3, alias="MAX_TOOL_STEPS")
    default_max_cost_usd: float = Field(default=0.05, alias="DEFAULT_MAX_COST_USD")
    provider_timeout_seconds: float = Field(default=30.0, alias="PROVIDER_TIMEOUT_SECONDS")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_demo(self) -> bool:
        """True when running in demo mode (synthetic data, no external LLM calls)."""
        return self.demo_mode or self.app_env == "demo"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def problem_type_base(self) -> str:
        """Base URI for RFC 9457 problem type identifiers."""
        return "https://agent-gateway.example.com/problems"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
