"""Нормализация ошибок провайдера (стабильные code/message)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class PublicError:
    """Публичная ошибка для ответа клиенту."""

    status_code: int
    code: str
    message: str
    type: str = "gateway_error"


def map_provider_exception(exc: Exception) -> PublicError:
    """Преобразует исключение в стабильный публичный формат (без утечек деталей)."""
    if isinstance(exc, ValueError) and str(exc).startswith("Unknown provider:"):
        return PublicError(
            status_code=400,
            code="unknown_provider",
            message="Неизвестный провайдер",
            type="invalid_request_error",
        )

    if isinstance(exc, RuntimeError):
        text = str(exc)
        if "OPENAI_BASE_URL" in text or "OPENAI_API_KEY" in text:
            return PublicError(
                status_code=500,
                code="provider_not_configured",
                message="Провайдер не настроен",
            )

    if isinstance(exc, httpx.TimeoutException):
        return PublicError(
            status_code=502,
            code="upstream_timeout",
            message="Upstream не ответил вовремя",
            type="upstream_error",
        )

    if isinstance(exc, httpx.HTTPStatusError):
        sc = int(getattr(exc.response, "status_code", 0) or 0)
        if 400 <= sc < 500:
            group = "upstream_4xx"
        elif sc >= 500:
            group = "upstream_5xx"
        else:
            group = "upstream_error"
        msg = f"Upstream вернул {sc}" if sc else "Upstream вернул ошибку"
        return PublicError(
            status_code=502,
            code=group,
            message=msg,
            type="upstream_error",
        )

    if isinstance(exc, httpx.TransportError):
        return PublicError(
            status_code=502,
            code="upstream_unreachable",
            message="Не удалось подключиться к upstream",
            type="upstream_error",
        )

    return PublicError(
        status_code=502,
        code="provider_error",
        message="Ошибка провайдера",
    )


def error_payload(err: PublicError) -> dict:
    """Формирует JSON `{error:{...}}` для клиента."""
    return {"error": {"code": err.code, "message": err.message, "type": err.type}}
