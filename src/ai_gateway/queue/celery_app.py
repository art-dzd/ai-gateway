"""Celery приложение (broker/backend в Redis)."""

from __future__ import annotations

from celery import Celery
from prometheus_client import start_http_server

from ai_gateway.metrics import registry
from ai_gateway.settings import get_settings


def create_celery() -> Celery:
    """Создаёт Celery app."""
    settings = get_settings()
    broker = settings.celery_broker_url or settings.redis_url
    backend = settings.celery_result_backend or settings.redis_url

    app = Celery("ai_gateway", broker=broker, backend=backend, include=["ai_gateway.queue.tasks"])
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )

    if settings.worker_metrics_port:
        # Если хочешь — можно скрейпить метрики прямо с воркера на отдельном порту.
        start_http_server(settings.worker_metrics_port, registry=registry)

    return app


celery_app = create_celery()
