"""Подключение к Redis."""

import redis

from ai_gateway.settings import get_settings


def get_redis() -> redis.Redis:
    """Возвращает клиент Redis (decode_responses=True)."""
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)
