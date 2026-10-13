from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.audit import router as audit_router
from app.api.domain import router as domain_router
from app.api.health import router as health_router
from app.config import settings
from app.db.seed import seed_if_empty
from app.db.session import SessionLocal


def _run_migrations() -> None:
    if settings.database_url.startswith("sqlite:///./"):
        Path("data").mkdir(parents=True, exist_ok=True)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ehs-agent-console", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(domain_router)
    app.include_router(audit_router)
    app.include_router(agent_router)
    return app


app = create_app()
