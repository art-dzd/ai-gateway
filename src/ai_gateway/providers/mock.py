"""Mock провайдер для демо (без внешних ключей)."""

from __future__ import annotations

import time
import uuid

from ai_gateway.providers.base import ProviderClient, ProviderResult


def _now_ts() -> int:
    return int(time.time())


class MockProvider(ProviderClient):
    name = "mock"

    def responses(self, payload: dict) -> ProviderResult:
        model = str(payload.get("model") or "mock-1")
        user_text = ""
        inp = payload.get("input")
        if isinstance(inp, str):
            user_text = inp
        elif isinstance(inp, list) and inp:
            # пробуем вытащить текст из структуры “похоже на messages”
            last = inp[-1]
            if isinstance(last, dict):
                user_text = str(last.get("content") or "")

        out_text = f"[mock] ok: {user_text[:120]}"
        prompt_tokens = max(1, len(user_text) // 4)
        completion_tokens = max(1, len(out_text) // 4)
        total_tokens = prompt_tokens + completion_tokens

        result = {
            "id": f"resp_{uuid.uuid4().hex}",
            "object": "response",
            "created": _now_ts(),
            "model": model,
            "output": [
                {
                    "id": f"msg_{uuid.uuid4().hex}",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": out_text}],
                }
            ],
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
        return ProviderResult(
            json=result,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def chat_completions(self, payload: dict) -> ProviderResult:
        model = str(payload.get("model") or "mock-1")
        messages = payload.get("messages") or []
        user_text = ""
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict):
                user_text = str(last.get("content") or "")

        out_text = f"[mock] ok: {user_text[:120]}"
        prompt_tokens = max(1, len(user_text) // 4)
        completion_tokens = max(1, len(out_text) // 4)
        total_tokens = prompt_tokens + completion_tokens

        result = {
            "id": f"chatcmpl_{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": _now_ts(),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": out_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
        return ProviderResult(
            json=result,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def list_models(self) -> dict:
        return {
            "object": "list",
            "data": [
                {"id": "mock-1", "object": "model", "created": _now_ts(), "owned_by": "ai-gateway"},
                {"id": "mock-2", "object": "model", "created": _now_ts(), "owned_by": "ai-gateway"},
            ],
        }
