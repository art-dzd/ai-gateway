"""Бюджеты по ключу (day/month) на основе аудита запросов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_gateway.db.models import RequestLog


@dataclass(frozen=True)
class BudgetLimits:
    daily_budget_rub: Decimal | None
    monthly_budget_rub: Decimal | None


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def enforce_budgets(session: Session, api_key_id: str, limits: BudgetLimits) -> None:
    """Проверяет бюджеты и кидает 429, если лимит уже выбит."""
    now = datetime.now(UTC)
    if limits.daily_budget_rub is not None:
        start = _day_start(now)
        spent = (
            session.query(func.coalesce(func.sum(RequestLog.cost_rub), 0))
            .filter(
                RequestLog.api_key_id == api_key_id,
                RequestLog.status == "succeeded",
                RequestLog.created_at >= start,
            )
            .scalar()
        )
        if spent is not None and Decimal(spent) >= limits.daily_budget_rub:
            raise HTTPException(status_code=429, detail="Превышен дневной бюджет")

    if limits.monthly_budget_rub is not None:
        start = _month_start(now)
        spent = (
            session.query(func.coalesce(func.sum(RequestLog.cost_rub), 0))
            .filter(
                RequestLog.api_key_id == api_key_id,
                RequestLog.status == "succeeded",
                RequestLog.created_at >= start,
            )
            .scalar()
        )
        if spent is not None and Decimal(spent) >= limits.monthly_budget_rub:
            raise HTTPException(status_code=429, detail="Превышен месячный бюджет")
