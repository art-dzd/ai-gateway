"""Интерфейс провайдера (responses/chat/models)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResult:
    """Результат вызова провайдера + usage (если получилось достать)."""

    json: dict
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ProviderClient:
    """Базовый интерфейс провайдера."""

    name: str

    def responses(self, payload: dict) -> ProviderResult:
        raise NotImplementedError

    def chat_completions(self, payload: dict) -> ProviderResult:
        raise NotImplementedError

    def list_models(self) -> dict:
        raise NotImplementedError
