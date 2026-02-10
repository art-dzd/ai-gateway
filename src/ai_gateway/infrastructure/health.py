"""Readiness-проверки (БД/Redis)."""

from sqlalchemy import text

from ai_gateway.infrastructure.db import SessionLocal
from ai_gateway.infrastructure.redis import get_redis


def check_readiness() -> None:
    """Бросает исключение, если БД или Redis недоступны."""
    # База данных
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
    finally:
        session.close()

    # Redis
    r = get_redis()
    r.ping()
