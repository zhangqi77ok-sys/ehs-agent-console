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

    @property
    def hitl_write_tool_set(self) -> set[str]:
        return {x.strip() for x in self.hitl_write_tools.split(",") if x.strip()}


settings = Settings()
