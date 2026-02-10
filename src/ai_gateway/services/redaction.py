"""Редактирование payload/result перед записью в БД (без сырых текстов)."""

import hashlib
from typing import Any

REDACTED_TEXT = "<redacted>"


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_chat_payload(payload: dict) -> dict:
    p = dict(payload)
    msgs = p.get("messages")
    if isinstance(msgs, list):
        out_msgs = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            content = m.get("content")
            if isinstance(content, str):
                out_msgs.append(
                    {
                        "role": m.get("role"),
                        "content": REDACTED_TEXT,
                        "content_len": len(content),
                        "content_sha256": sha256_hex(content),
                    }
                )
            else:
                out_msgs.append({"role": m.get("role"), "content": REDACTED_TEXT})
        p["messages"] = out_msgs
    return p


def _redact_any(value: Any) -> Any:
    if isinstance(value, str):
        return {"redacted": True, "len": len(value), "sha256": sha256_hex(value)}
    if isinstance(value, list):
        return [_redact_any(v) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            # Поля, где чаще всего лежит пользовательский текст (OpenAI-like payload).
            if k in {"content", "input", "text", "instructions"}:
                out[k] = _redact_any(v)
            else:
                out[k] = _redact_any(v) if isinstance(v, (str, list, dict)) else v
        return out
    return value


def redact_responses_payload(payload: dict) -> dict:
    return _redact_any(payload) if isinstance(payload, dict) else {"redacted": True}


def redact_result_summary(result: dict) -> dict:
    # Храним минимум для отладки (без текста).
    try:
        raw = repr(result)
    except Exception:
        raw = "<unrepr>"
    return {
        "sha256": sha256_hex(raw),
        "keys": (
            sorted([k for k in result if isinstance(k, str)])
            if isinstance(result, dict)
            else []
        ),
    }
