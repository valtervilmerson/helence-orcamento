from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.db.connection import get_connection
from app.db.migrate import apply_migrations
from app.shared.errors import DomainError, domain_error_handler, unhandled_exception_handler
from app.shared.logging import configure_logging, request_logging_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        apply_migrations(connection)

    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title="Helence Orçamento", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(request_logging_middleware)

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(v1_router)

    return app


app = create_app()
