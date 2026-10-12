from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default: real OpenAI-compatible LLM. Set LLM_PROVIDER=mock only for offline demos.
    llm_provider: str = "openai"  # openai | mock
    openai_api_key: str = ""
    openai_base_url: str = "http://HOST:7863/v1"
    openai_model: str = "glm-5.3-flash"
    max_agent_steps: int = 8
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Reliability (Week1 Day4)
    llm_timeout_s: float = 60.0
    llm_max_retries: int = 3  # retries after the first attempt (total attempts = 1 + this)
    llm_retry_backoff_s: float = 0.8  # base for exponential backoff: base * 2^attempt
    tool_timeout_s: float = 15.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
