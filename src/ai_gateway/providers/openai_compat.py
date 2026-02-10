"""OpenAI-compatible провайдер (proxy к upstream /v1/*)."""

from __future__ import annotations

import time

import httpx

from ai_gateway.providers.base import ProviderClient, ProviderResult
from ai_gateway.settings import get_settings


def _encode_header_value(value: str) -> str | bytes:
    """Кодирует заголовок в ASCII или UTF-8 (байты), если там есть не-ASCII."""
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        return value.encode("utf-8")


class OpenAICompatibleProvider(ProviderClient):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_base_url or not settings.openai_api_key:
            raise RuntimeError("Нужны OPENAI_BASE_URL/OPENAI_API_KEY для provider=openai")
        base = settings.openai_base_url.rstrip("/")
        # Разрешаем как "https://api.openai.com", так и "https://api.openai.com/v1".
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        self._base_url = base.rstrip("/")
        self._api_key = settings.openai_api_key
        self._timeout = float(settings.openai_timeout_seconds)
        self._retries = int(settings.openai_retries)
        self._headers: list[tuple[str, str | bytes]] = [
            ("Authorization", f"Bearer {self._api_key}"),
        ]
        if settings.openai_http_referer:
            self._headers.append(("HTTP-Referer", settings.openai_http_referer))
        if settings.openai_title:
            self._headers.append(("X-Title", _encode_header_value(settings.openai_title)))
        self._client = httpx.Client(
            timeout=httpx.Timeout(self._timeout),
        )

    def _request(self, method: str, path: str, json_body: dict | None = None) -> httpx.Response:
        url = f"{self._base_url}{path}"
        retryable = {408, 409, 425, 429, 500, 502, 503, 504}

        for attempt in range(self._retries + 1):
            try:
                r = self._client.request(
                    method,
                    url,
                    json=json_body,
                    headers=self._headers,
                )
                if r.status_code >= 400 and r.status_code in retryable and attempt < self._retries:
                    time.sleep(min(2.0, 0.2 * (2**attempt)))
                    continue
                r.raise_for_status()
                return r
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt < self._retries:
                    time.sleep(min(2.0, 0.2 * (2**attempt)))
                    continue
                raise

    def responses(self, payload: dict) -> ProviderResult:
        p = dict(payload)
        if "store" not in p:
            p["store"] = False

        r = self._request("POST", "/v1/responses", json_body=p)
        data = r.json()
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        return ProviderResult(
            json=data,
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            total_tokens=int(total_tokens) if total_tokens is not None else None,
        )

    def chat_completions(self, payload: dict) -> ProviderResult:
        r = self._request("POST", "/v1/chat/completions", json_body=payload)
        data = r.json()
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        return ProviderResult(
            json=data,
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            total_tokens=int(total_tokens) if total_tokens is not None else None,
        )

    def list_models(self) -> dict:
        r = self._request("GET", "/v1/models")
        return r.json()
