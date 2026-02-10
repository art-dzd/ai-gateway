"""Подписи вебхуков (HMAC-SHA256)."""

import hashlib
import hmac


def hmac_sha256_signature(secret: str, body: bytes) -> str:
    """Возвращает строку вида `sha256=<hex>` для заголовка `X-AI-Gateway-Signature`."""
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"
