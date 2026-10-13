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

    # RAG (Week2)
    openai_embedding_model: str = ""  # e.g. text-embedding-3-small; empty → skip gateway
    rag_embedding_prefer: str = "openai"  # openai | local — openai tries gateway then falls back
    rag_top_k: int = 3
    rag_chunk_chars: int = 280
    rag_chunk_overlap: int = 60
    rag_index_dir: str = str(_BACKEND_DIR / "data" / "rag")
    rag_regs_path: str = str(_BACKEND_DIR / "app" / "data" / "ehs_regs.md")
    rag_load_persisted: bool = True

    # Persistence (eng-1)
    database_url: str = "sqlite:///./data/ehs.db"

    # Observability + auth (eng-3)
    log_level: str = "INFO"
    auth_mode: str = "hybrid"  # headers | hybrid | strict
    jwt_secret: str = "dev-change-me-ehs-agent-console-32b!"
    jwt_ttl_s: int = 86400
    # key:tenant:role,...
    api_keys: str = (
        "demo-admin:default:admin,"
        "demo-engineer:default:ehs_engineer,"
        "demo-viewer:default:viewer,"
        "demo-plant-a:plant_a:ehs_engineer,"
        "demo-plant-b:plant_b:viewer"
    )
    auth_allow_demo_login: bool = True
    demo_login_secret: str = "ehs-demo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
