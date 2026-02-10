"""Мини-дашборд (HTML) с Basic Auth."""

from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ai_gateway.db.models import Job, RequestLog, WebhookDelivery
from ai_gateway.infrastructure.db import SessionLocal
from ai_gateway.settings import get_settings

router = APIRouter()
security = HTTPBasic(auto_error=False)

_templates_dir = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _require_dashboard_auth(
    creds: HTTPBasicCredentials | None = Depends(security),
) -> None:
    settings = get_settings()
    if creds is None:
        raise HTTPException(
            status_code=401,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Basic"},
        )

    ok_user = secrets.compare_digest(creds.username, settings.dashboard_login)
    ok_pass = secrets.compare_digest(creds.password, settings.dashboard_password)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Basic"},
        )


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _load_dashboard_data(limit: int = 30) -> dict:
    session: Session = SessionLocal()
    try:
        requests = (
            session.query(RequestLog)
            .order_by(desc(RequestLog.created_at))
            .limit(limit)
            .all()
        )
        jobs = session.query(Job).order_by(desc(Job.created_at)).limit(limit).all()
        webhooks = (
            session.query(WebhookDelivery)
            .order_by(desc(WebhookDelivery.created_at))
            .limit(limit)
            .all()
        )

        def req_row(r: RequestLog) -> dict:
            return {
                "id": str(r.id),
                "api_key_id": str(r.api_key_id),
                "kind": r.kind,
                "provider": r.provider,
                "model": r.model,
                "status": r.status,
                "error_code": r.error_code,
                "error_text": r.error_text,
                "latency_ms": r.latency_ms,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost_rub": float(r.cost_rub) if r.cost_rub is not None else None,
                "request_payload": r.request_payload_redacted,
                "response_payload": r.response_payload_redacted,
                "created_at": _iso(r.created_at),
            }

        def job_row(j: Job) -> dict:
            return {
                "id": str(j.id),
                "api_key_id": str(j.api_key_id),
                "kind": j.kind,
                "provider": j.provider,
                "model": j.model,
                "status": j.status,
                "idempotency_key": j.idempotency_key,
                "error_code": j.error_code,
                "error_text": j.error_text,
                "payload": j.payload_redacted,
                "result": j.result_redacted,
                "created_at": _iso(j.created_at),
                "updated_at": _iso(j.updated_at),
                "webhook_url": j.webhook_url,
                "webhook_headers": j.webhook_headers,
                "webhook_secret_set": bool(j.webhook_secret),
            }

        def wh_row(w: WebhookDelivery) -> dict:
            return {
                "id": str(w.id),
                "job_id": str(w.job_id),
                "attempt": w.attempt,
                "url": w.url,
                "status_code": w.status_code,
                "error_text": w.error_text,
                "latency_ms": w.latency_ms,
                "created_at": _iso(w.created_at),
            }

        req_rows = [req_row(r) for r in requests]
        job_rows = [job_row(j) for j in jobs]
        wh_rows = [wh_row(w) for w in webhooks]

        stats = {
            "requests_ok": sum(1 for r in req_rows if r.get("status") == "succeeded"),
            "requests_err": sum(1 for r in req_rows if r.get("status") != "succeeded"),
            "jobs_queued": sum(1 for j in job_rows if j.get("status") == "queued"),
            "jobs_running": sum(1 for j in job_rows if j.get("status") == "running"),
            "jobs_ok": sum(1 for j in job_rows if j.get("status") == "succeeded"),
            "jobs_err": sum(1 for j in job_rows if j.get("status") == "failed"),
            "webhooks_ok": sum(
                1
                for w in wh_rows
                if isinstance(w.get("status_code"), int) and w["status_code"] < 300
            ),
            "webhooks_err": sum(
                1
                for w in wh_rows
                if not (isinstance(w.get("status_code"), int) and w["status_code"] < 300)
            ),
        }

        return {
            "requests": req_rows,
            "jobs": job_rows,
            "webhooks": wh_rows,
            "stats": stats,
        }
    finally:
        session.close()


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    dependencies=[Depends(_require_dashboard_auth)],
)
def dashboard(request: Request) -> HTMLResponse:
    data = _load_dashboard_data()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "data": data,
        },
    )


@router.get("/dashboard/data", dependencies=[Depends(_require_dashboard_auth)])
def dashboard_data() -> JSONResponse:
    return JSONResponse(content=_load_dashboard_data())
