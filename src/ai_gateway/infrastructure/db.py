"""Подключение к БД и фабрика сессий SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_gateway.settings import get_settings


def create_session_factory() -> sessionmaker:
    """Создаёт `sessionmaker` на основе `DATABASE_URL`."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = create_session_factory()
