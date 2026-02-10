"""Фабрика провайдеров (с кэшем инстансов на процесс)."""

from ai_gateway.providers.base import ProviderClient
from ai_gateway.providers.mock import MockProvider
from ai_gateway.providers.openai_compat import OpenAICompatibleProvider

_cache: dict[str, ProviderClient] = {}


def get_provider(name: str) -> ProviderClient:
    """Возвращает провайдера по имени (`mock`, `openai`)."""
    cached = _cache.get(name)
    if cached is not None:
        return cached

    if name == "mock":
        p = MockProvider()
        _cache[name] = p
        return p
    if name == "openai":
        p = OpenAICompatibleProvider()
        _cache[name] = p
        return p
    raise ValueError(f"Unknown provider: {name}")
