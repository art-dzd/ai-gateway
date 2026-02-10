"""Проверка `X-API-Key` (bcrypt-хэш в БД)."""

from dataclasses import dataclass
from decimal import Decimal

import bcrypt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ai_gateway.db.models import ApiKey
from ai_gateway.infrastructure.db import SessionLocal


@dataclass(frozen=True)
class AuthedKey:
    api_key_id: str
    rpm_limit: int | None
    daily_budget_rub: Decimal | None
    monthly_budget_rub: Decimal | None


def _parse_api_key(value: str) -> tuple[str | None, str]:
    """Парсит ключ: либо legacy-токен, либо формат `<id>.<secret>`."""
    if "." not in value:
        return None, value

    prefix, secret = value.split(".", 1)
    prefix = prefix.strip()
    secret = secret.strip()
    if prefix.startswith("agw_"):
        prefix = prefix[len("agw_") :]

    if not prefix or not secret:
        return None, value
    return prefix, secret


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> AuthedKey:
    """FastAPI dependency: проверяет `X-API-Key` и возвращает лимиты/бюджеты."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Нет заголовка X-API-Key")

    key_id, secret_or_legacy = _parse_api_key(x_api_key)
    session: Session = SessionLocal()
    try:
        if key_id is not None:
            k = (
                session.query(ApiKey)
                .filter(
                    ApiKey.is_active.is_(True),
                    ApiKey.key_id == key_id,
                )
                .one_or_none()
            )
            if k is not None and bcrypt.checkpw(
                secret_or_legacy.encode("utf-8"), k.key_hash.encode("utf-8")
            ):
                return AuthedKey(
                    api_key_id=str(k.id),
                    rpm_limit=k.rpm_limit,
                    daily_budget_rub=k.daily_budget_rub,
                    monthly_budget_rub=k.monthly_budget_rub,
                )

        # Legacy: старые ключи без `key_id` (там bcrypt от всего токена).
        keys = (
            session.query(ApiKey)
            .filter(
                ApiKey.is_active.is_(True),
                ApiKey.key_id.is_(None),
            )
            .all()
        )
        for k in keys:
            if bcrypt.checkpw(secret_or_legacy.encode("utf-8"), k.key_hash.encode("utf-8")):
                return AuthedKey(
                    api_key_id=str(k.id),
                    rpm_limit=k.rpm_limit,
                    daily_budget_rub=k.daily_budget_rub,
                    monthly_budget_rub=k.monthly_budget_rub,
                )
    finally:
        session.close()

    raise HTTPException(status_code=401, detail="Неверный API ключ")


Authed = Depends(require_api_key)
