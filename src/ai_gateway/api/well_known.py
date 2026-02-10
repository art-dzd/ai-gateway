"""Служебные эндпоинты: health/ready/metrics."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ai_gateway.infrastructure.health import check_readiness
from ai_gateway.metrics import registry

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    """Простой healthcheck: процесс жив."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict:
    """Readiness: проверяем БД и Redis."""
    check_readiness()
    return {"status": "ready"}


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus метрики."""
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
