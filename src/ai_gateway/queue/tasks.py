"""Celery задачи: обработка job и доставка webhook."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx
import structlog
from celery import Task
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_gateway.db.models import Job, JobAttempt, RequestLog, WebhookDelivery
from ai_gateway.infrastructure.db import SessionLocal
from ai_gateway.metrics import cost_rub_total, jobs_total, tokens_total, webhook_deliveries_total
from ai_gateway.providers.factory import get_provider
from ai_gateway.services.errors import error_payload, map_provider_exception
from ai_gateway.services.pricing import calc_cost_rub, load_pricing
from ai_gateway.services.redaction import (
    redact_chat_payload,
    redact_responses_payload,
    redact_result_summary,
)
from ai_gateway.services.webhooks import hmac_sha256_signature
from ai_gateway.settings import get_settings

from .celery_app import celery_app

log = structlog.get_logger()


def _attempt_next(session: Session, job_id: uuid.UUID) -> int:
    last = (
        session.query(func.coalesce(func.max(JobAttempt.attempt), 0))
        .filter(JobAttempt.job_id == job_id)
        .scalar()
    )
    return int(last or 0) + 1


def _wh_attempt_next(session: Session, job_id: uuid.UUID) -> int:
    last = (
        session.query(func.coalesce(func.max(WebhookDelivery.attempt), 0))
        .filter(WebhookDelivery.job_id == job_id)
        .scalar()
    )
    return int(last or 0) + 1


def _job_payload_redacted(kind: str, payload: dict[str, Any]) -> dict:
    if kind == "chat.completions":
        return redact_chat_payload(payload)
    return redact_responses_payload(payload)


def _retryable_http_status(code: int) -> bool:
    return code in {408, 409, 425, 429, 500, 502, 503, 504}


@celery_app.task(bind=True, name="ai_gateway.process_job", max_retries=3)
def process_job(self: Task, job_id: str, payload: dict[str, Any]) -> None:
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        log.warning("job_invalid_id", job_id=job_id)
        return

    session: Session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_uuid).with_for_update().one_or_none()
        if job is None:
            log.warning("job_not_found", job_id=job_id)
            return

        if job.status in {"succeeded", "failed"}:
            return

        attempt_n = _attempt_next(session, job_uuid)
        job.status = "running"
        session.flush()

        t0 = time.time()
        status = "failed"
        err_code = None
        err_text = None
        public_err_msg = None
        resp_json: dict[str, Any] | None = None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None

        try:
            provider = get_provider(job.provider)
            if job.kind == "chat.completions":
                res = provider.chat_completions(payload)
            else:
                res = provider.responses(payload)
            status = "succeeded"
            resp_json = res.json
            prompt_tokens = res.prompt_tokens
            completion_tokens = res.completion_tokens
            total_tokens = res.total_tokens
        except Exception as e:
            pub = map_provider_exception(e)
            err_code = pub.code
            err_text = str(e)
            public_err_msg = pub.message
            resp_json = error_payload(pub)

        latency_ms = int((time.time() - t0) * 1000)
        pricing = load_pricing()
        cost = calc_cost_rub(job.model, prompt_tokens, completion_tokens, pricing)

        req = RequestLog(
            api_key_id=job.api_key_id,
            kind=job.kind,
            provider=job.provider,
            model=job.model,
            status=status,
            error_code=err_code,
            error_text=err_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_rub=cost,
            latency_ms=latency_ms,
            request_payload_redacted=_job_payload_redacted(job.kind, payload),
            response_payload_redacted=redact_result_summary(resp_json or {}),
        )
        session.add(req)
        session.flush()  # чтобы req.id был доступен для meta/webhook

        job_attempt = JobAttempt(
            job_id=job_uuid,
            attempt=attempt_n,
            status=status,
            error_text=err_text,
            latency_ms=latency_ms,
        )
        session.add(job_attempt)

        job.status = status
        job.error_code = err_code
        job.error_text = err_text
        req_id = str(req.id) if req.id is not None else None
        job.result_redacted = {
            "request_id": req_id,
            "provider": job.provider,
            "model": job.model,
            "latency_ms": latency_ms,
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
            },
            "cost_rub": float(cost) if cost is not None else None,
            "result": redact_result_summary(resp_json or {}),
        }

        session.commit()

        jobs_total.labels(provider=job.provider, status=status).inc()
        if total_tokens is not None:
            tokens_total.labels(
                provider=job.provider,
                model=job.model or "-",
                kind="total",
            ).inc(total_tokens)
        if cost is not None:
            cost_rub_total.labels(provider=job.provider, model=job.model or "-").inc(float(cost))

        if job.webhook_url:
            body: dict[str, Any] = {
                "job_id": str(job.id),
                "status": job.status,
                "meta": {
                    "request_id": req_id,
                    "provider": job.provider,
                    "model": job.model,
                    "latency_ms": latency_ms,
                    "cost_rub": float(cost) if cost is not None else None,
                    "attempt": attempt_n,
                },
            }
            if status == "succeeded":
                body["result"] = resp_json
            else:
                body["error"] = {
                    "code": err_code,
                    "message": public_err_msg or "Ошибка провайдера",
                }

            deliver_webhook.delay(str(job.id), body)
    except Exception as e:
        # Ретраим только если упала сама задача (БД/код), а не “смысл” ответа провайдера.
        log.warning("process_job_failed", job_id=job_id, err=str(e))
        raise self.retry(exc=e, countdown=min(60, 2**self.request.retries))
    finally:
        session.close()


@celery_app.task(bind=True, name="ai_gateway.deliver_webhook", max_retries=5)
def deliver_webhook(self: Task, job_id: str, body: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        log.warning("webhook_invalid_job_id", job_id=job_id)
        return

    session: Session = SessionLocal()
    try:
        job = session.get(Job, job_uuid)
        if job is None or not job.webhook_url:
            return

        attempt_n = _wh_attempt_next(session, job_uuid)

        body_bytes = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if isinstance(job.webhook_headers, dict):
            for k, v in job.webhook_headers.items():
                if isinstance(k, str) and isinstance(v, str):
                    headers[k] = v

        if job.webhook_secret:
            headers["X-AI-Gateway-Signature"] = hmac_sha256_signature(
                job.webhook_secret,
                body_bytes,
            )

        t0 = time.time()
        status_code = None
        err_text = None
        try:
            r = httpx.post(
                job.webhook_url,
                content=body_bytes,
                headers=headers,
                timeout=httpx.Timeout(settings.webhook_timeout_seconds),
            )
            status_code = r.status_code
            if status_code < 200 or status_code >= 300:
                err_text = f"HTTP {status_code}: {r.text[:300]}"
                if _retryable_http_status(status_code):
                    raise RuntimeError(err_text)

                # Неретраибельные (обычно 4xx): записываем и не ретраим.
                latency_ms = int((time.time() - t0) * 1000)
                session.add(
                    WebhookDelivery(
                        job_id=job_uuid,
                        attempt=attempt_n,
                        url=job.webhook_url,
                        status_code=status_code,
                        error_text=err_text,
                        latency_ms=latency_ms,
                    )
                )
                session.commit()
                webhook_deliveries_total.labels(status="failed").inc()
                return
        except Exception as e:
            if err_text is None:
                err_text = str(e)
            latency_ms = int((time.time() - t0) * 1000)
            session.add(
                WebhookDelivery(
                    job_id=job_uuid,
                    attempt=attempt_n,
                    url=job.webhook_url,
                    status_code=status_code,
                    error_text=err_text,
                    latency_ms=latency_ms,
                )
            )
            session.commit()
            webhook_deliveries_total.labels(status="failed").inc()
            raise self.retry(exc=e, countdown=min(300, 2**self.request.retries))

        latency_ms = int((time.time() - t0) * 1000)
        session.add(
            WebhookDelivery(
                job_id=job_uuid,
                attempt=attempt_n,
                url=job.webhook_url,
                status_code=status_code,
                error_text=None,
                latency_ms=latency_ms,
            )
        )
        session.commit()
        webhook_deliveries_total.labels(status="succeeded").inc()
    finally:
        session.close()
