"""Rate limit (requests per minute) через Redis."""

from datetime import UTC, datetime

import redis
from fastapi import HTTPException

from ai_gateway.settings import get_settings


def _minute_key(api_key_id: str, endpoint: str, now: datetime) -> str:
    ts = now.strftime("%Y%m%d%H%M")
    return f"rl:{api_key_id}:{endpoint}:{ts}"


def enforce_rpm_limit(
    r: redis.Redis,
    api_key_id: str,
    endpoint: str,
    rpm_limit: int | None,
) -> None:
    """Проверяет RPM лимит и кидает 429, если превышено."""
    settings = get_settings()
    limit = rpm_limit if rpm_limit is not None else settings.default_rpm_limit
    if limit <= 0:
        return

    now = datetime.now(UTC)
    key = _minute_key(api_key_id, endpoint, now)
    value = int(r.incr(key))
    if value == 1:
        # TTL чуть больше минуты, чтобы не ловить дрейф по времени.
        r.expire(key, 120)

    if value > limit:
        raise HTTPException(status_code=429, detail="Превышен лимит запросов")
