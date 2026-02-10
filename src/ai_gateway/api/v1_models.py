"""Models discovery (`/v1/models`) + кэш в Redis."""

import json
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
from ai_gateway.metrics import request_latency_seconds, requests_total
from ai_gateway.providers.factory import get_provider
from ai_gateway.services.errors import error_payload, map_provider_exception
from ai_gateway.services.limits import enforce_rpm_limit
from ai_gateway.services.redaction import redact_result_summary, sha256_hex
from ai_gateway.settings import get_settings

router = APIRouter()
log = structlog.get_logger()


def _cache_key(provider: str, base_url: str | None) -> str:
    suffix = sha256_hex(base_url) if base_url else "-"
    return f"models:{provider}:{suffix}"


@router.get("/models")
def list_models(
    x_provider: str | None = Header(default=None, alias="X-Provider"),
    authed: AuthedKey = Depends(require_api_key),
) -> dict:
    settings = get_settings()
    provider_name = x_provider or settings.default_provider

    endpoint = "models"
    r = get_redis()
    enforce_rpm_limit(r, authed.api_key_id, endpoint, authed.rpm_limit)

    cache_key = _cache_key(
        provider_name,
        settings.openai_base_url if provider_name == "openai" else None,
    )
    cached = r.get(cache_key)
    if cached:
        data = json.loads(cached)
        data = dict(data)
        data["meta"] = {"cached": True, "provider": provider_name}
        return data

    session: Session = SessionLocal()
    try:
        t0 = time.time()
        status = "failed"
        http_status = 502
        err_code = None
        err_text = None
        try:
            provider = get_provider(provider_name)
            data = provider.list_models()
            status = "succeeded"
            http_status = 200
        except Exception as e:
            pub = map_provider_exception(e)
            log.warning(
                "provider_error",
                endpoint=endpoint,
                provider=provider_name,
                code=pub.code,
                err=str(e),
            )
            data = error_payload(pub)
            err_code = pub.code
            err_text = str(e)
            http_status = pub.status_code

        latency_ms = int((time.time() - t0) * 1000)

        req = RequestLog(
            api_key_id=uuid.UUID(authed.api_key_id),
            kind="models",
            provider=provider_name,
            model="",
            status=status,
            error_code=err_code,
            error_text=err_text,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            cost_rub=None,
            latency_ms=latency_ms,
            request_payload_redacted=None,
            response_payload_redacted=(
                redact_result_summary(data) if isinstance(data, dict) else None
            ),
        )
        session.add(req)
        session.commit()

        requests_total.labels(endpoint=endpoint, provider=provider_name, status=status).inc()
        request_latency_seconds.labels(endpoint=endpoint, provider=provider_name).observe(
            time.time() - t0
        )

        data = dict(data) if isinstance(data, dict) else {"data": data}
        data["meta"] = {"request_id": str(req.id), "provider": provider_name, "cached": False}

        if status == "succeeded":
            r.setex(cache_key, settings.models_cache_ttl_seconds, json.dumps(data))
            return data

        return JSONResponse(status_code=http_status, content=data)
    finally:
        session.close()
