from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/ehs.db"
    app_name: str = "ehs-agent-console"

    # LLM: default mock for tests/CI; set LLM_PROVIDER=openai for real gateway
    llm_provider: str = "mock"  # mock | openai
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    max_agent_steps: int = 8
    llm_timeout_s: float = 60.0
    llm_max_retries: int = 2
    llm_retry_backoff_s: float = 0.4
    tool_timeout_s: float = 15.0

    # HITL (Ch5): gate write tools
    hitl_enabled: bool = True
    hitl_write_tools: str = "create_corrective_ticket,advance_corrective_ticket"

    # Auth (Ch8): hybrid JWT / API key / demo headers
    jwt_secret: str = "ehs-dev-secret-change-me-32b-min!!!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    api_keys_json: str = '{"demo-key":{"tenant_id":"demo-plant","role":"ehs_engineer","actor":"api-key-demo"}}'
    auth_require_credential: bool = False  # False = allow X-Tenant-Id demo headers

    # Observability (Ch8)
    access_log_json: bool = True

    # Memory (Ch10)
    memory_max_chars: int = 2000
    memory_keep_recent: int = 4

    @property
    def hitl_write_tool_set(self) -> set[str]:
        return {x.strip() for x in self.hitl_write_tools.split(",") if x.strip()}

    @property
    def api_key_map(self) -> dict:
        import json
        try:
            data = json.loads(self.api_keys_json or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


settings = Settings()
