"""FastAPI приложение (роутеры + логирование)."""

from fastapi import FastAPI

from ai_gateway import __version__
from ai_gateway.api.dashboard import router as dashboard_router
from ai_gateway.api.v1 import router as v1_router
from ai_gateway.api.well_known import router as well_known_router
from ai_gateway.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    """Собирает FastAPI приложение."""
    configure_logging()

    app = FastAPI(title="AI Gateway", version=__version__)

    app.include_router(well_known_router)
    app.include_router(v1_router, prefix="/v1")
    app.include_router(dashboard_router)
    return app


app = create_app()
