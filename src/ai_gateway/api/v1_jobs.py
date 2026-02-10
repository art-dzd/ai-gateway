"""Async jobs API: создать задачу и получить статус/результат."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ai_gateway.auth.apikey import AuthedKey, require_api_key
from ai_gateway.db.models import Job
from ai_gateway.infrastructure.db import SessionLocal
from ai_gateway.infrastructure.redis import get_redis
from ai_gateway.queue.tasks import process_job
from ai_gateway.services.budgets import BudgetLimits, enforce_budgets
from ai_gateway.services.limits import enforce_rpm_limit
from ai_gateway.services.redaction import redact_chat_payload, redact_responses_payload
from ai_gateway.settings import get_settings

router = APIRouter()


class WebhookCfg(BaseModel):
    url: str
    secret: str | None = None
    headers: dict[str, str] | None = None


class JobCreate(BaseModel):
    kind: Literal["responses", "chat.completions"]
    provider: str | None = None
    model: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    webhook: WebhookCfg | None = None
    idempotency_key: str | None = None


def _payload_redacted(kind: str, payload: dict) -> dict:
    if kind == "chat.completions":
        return redact_chat_payload(payload)
    return redact_responses_payload(payload)


@router.post("/jobs")
def create_job(
    body: JobCreate,
    x_provider: str | None = Header(default=None, alias="X-Provider"),
    authed: AuthedKey = Depends(require_api_key),
) -> dict:
    settings = get_settings()
    provider_name = body.provider or x_provider or settings.default_provider
    model = body.model or str(body.payload.get("model") or "")

    endpoint = "jobs.create"
    r = get_redis()
    enforce_rpm_limit(r, authed.api_key_id, endpoint, authed.rpm_limit)

    session: Session = SessionLocal()
    try:
        enforce_budgets(
            session,
            authed.api_key_id,
            BudgetLimits(
                daily_budget_rub=authed.daily_budget_rub,
                monthly_budget_rub=authed.monthly_budget_rub,
            ),
        )

        if body.idempotency_key:
            existing = (
                session.query(Job)
                .filter(
                    and_(
                        Job.api_key_id == uuid.UUID(authed.api_key_id),
                        Job.idempotency_key == body.idempotency_key,
                    )
                )
                .one_or_none()
            )
            if existing:
                return {"job_id": str(existing.id), "status": existing.status}

        job = Job(
            api_key_id=uuid.UUID(authed.api_key_id),
            kind=body.kind,
            provider=provider_name,
            model=model,
            status="queued",
            idempotency_key=body.idempotency_key,
            payload_redacted=_payload_redacted(body.kind, body.payload),
            webhook_url=body.webhook.url if body.webhook else None,
            webhook_secret=body.webhook.secret if body.webhook else None,
            webhook_headers=body.webhook.headers if body.webhook else None,
        )
        session.add(job)
        session.commit()

        # Сырой payload уходит через брокер (Redis), а в БД мы храним только redacted.
        process_job.delay(str(job.id), body.payload)
        return {"job_id": str(job.id), "status": job.status}
    finally:
        session.close()


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    authed: AuthedKey = Depends(require_api_key),
) -> dict:
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Задача не найдена") from None

    session: Session = SessionLocal()
    try:
        job = (
            session.query(Job)
            .filter(and_(Job.id == job_uuid, Job.api_key_id == uuid.UUID(authed.api_key_id)))
            .one_or_none()
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        return {
            "job_id": str(job.id),
            "status": job.status,
            "kind": job.kind,
            "provider": job.provider,
            "model": job.model,
            "error_code": job.error_code,
            "error_text": job.error_text,
            "result": job.result_redacted,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "webhook_url": job.webhook_url,
        }
    finally:
        session.close()
