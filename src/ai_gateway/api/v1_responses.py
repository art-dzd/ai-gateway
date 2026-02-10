"""Эндпоинт `/v1/responses` (основной sync proxy)."""

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ai_gateway.auth.apikey import AuthedKey, require_api_key
from ai_gateway.db.models import RequestLog
from ai_gateway.infrastructure.db import SessionLocal
from ai_gateway.infrastructure.redis import get_redis
from ai_gateway.metrics import cost_rub_total, request_latency_seconds, requests_total, tokens_total
from ai_gateway.providers.factory import get_provider
from ai_gateway.services.budgets import BudgetLimits, enforce_budgets
from ai_gateway.services.errors import error_payload, map_provider_exception
from ai_gateway.services.limits import enforce_rpm_limit
from ai_gateway.services.pricing import calc_cost_rub, load_pricing
from ai_gateway.services.redaction import redact_responses_payload, redact_result_summary
from ai_gateway.settings import get_settings

router = APIRouter()
log = structlog.get_logger()


@router.post("/responses")
def responses(
    payload: dict,
    x_provider: str | None = Header(default=None, alias="X-Provider"),
    authed: AuthedKey = Depends(require_api_key),
) -> dict:
    settings = get_settings()
    provider_name = x_provider or settings.default_provider

    endpoint = "responses"
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

        t0 = time.time()
        status = "failed"
        http_status = 502
        err_code = None
        err_text = None
        model = str(payload.get("model") or "")

        try:
            provider = get_provider(provider_name)
            res = provider.responses(payload)
            status = "succeeded"
            http_status = 200
            resp_json = res.json
            prompt_tokens = res.prompt_tokens
            completion_tokens = res.completion_tokens
            total_tokens = res.total_tokens
        except Exception as e:
            pub = map_provider_exception(e)
            log.warning(
                "provider_error",
                endpoint=endpoint,
                provider=provider_name,
                code=pub.code,
                err=str(e),
            )
            resp_json = error_payload(pub)
            err_code = pub.code
            err_text = str(e)
            http_status = pub.status_code
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None

        latency_ms = int((time.time() - t0) * 1000)
        pricing = load_pricing()
        cost = calc_cost_rub(model, prompt_tokens, completion_tokens, pricing)

        req = RequestLog(
            api_key_id=uuid.UUID(authed.api_key_id),
            kind="responses",
            provider=provider_name,
            model=model,
            status=status,
            error_code=err_code,
            error_text=err_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_rub=cost,
            latency_ms=latency_ms,
            request_payload_redacted=redact_responses_payload(payload),
            response_payload_redacted=redact_result_summary(resp_json),
        )
        session.add(req)
        session.commit()

        requests_total.labels(endpoint=endpoint, provider=provider_name, status=status).inc()
        request_latency_seconds.labels(endpoint=endpoint, provider=provider_name).observe(
            time.time() - t0
        )
        if total_tokens is not None:
            tokens_total.labels(
                provider=provider_name,
                model=model or "-",
                kind="total",
            ).inc(total_tokens)
        if cost is not None:
            cost_rub_total.labels(provider=provider_name, model=model or "-").inc(float(cost))

        resp_json = dict(resp_json)
        resp_json["meta"] = {
            "request_id": str(req.id),
            "provider": provider_name,
            "latency_ms": latency_ms,
            "cost_rub": float(cost) if cost is not None else None,
        }

        if status != "succeeded":
            return JSONResponse(status_code=http_status, content=resp_json)

        return resp_json
    finally:
        session.close()
