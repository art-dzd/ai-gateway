"""Best-effort расчёт стоимости по `pricing.json` (RUB)."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class ModelPrice:
    prompt_per_1k_rub: Decimal
    completion_per_1k_rub: Decimal


@lru_cache(maxsize=1)
def load_pricing() -> dict:
    text = resources.files("ai_gateway").joinpath("data/pricing.json").read_text(encoding="utf-8")
    return json.loads(text)


def price_for_model(model: str, pricing: dict) -> ModelPrice:
    defaults = pricing.get("defaults") or {}
    prompt_default = Decimal(str(defaults.get("prompt_per_1k_rub", 0.0)))
    completion_default = Decimal(str(defaults.get("completion_per_1k_rub", 0.0)))

    for row in pricing.get("models") or []:
        if not isinstance(row, dict):
            continue
        pat = row.get("match")
        if not isinstance(pat, str):
            continue
        if re.fullmatch(pat, model or ""):
            return ModelPrice(
                prompt_per_1k_rub=Decimal(str(row.get("prompt_per_1k_rub", prompt_default))),
                completion_per_1k_rub=Decimal(
                    str(row.get("completion_per_1k_rub", completion_default))
                ),
            )

    return ModelPrice(prompt_per_1k_rub=prompt_default, completion_per_1k_rub=completion_default)


def calc_cost_rub(
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    pricing: dict,
) -> Decimal | None:
    if prompt_tokens is None and completion_tokens is None:
        return None
    p = price_for_model(model, pricing)
    pt = Decimal(prompt_tokens or 0) / Decimal(1000)
    ct = Decimal(completion_tokens or 0) / Decimal(1000)
    return (pt * p.prompt_per_1k_rub) + (ct * p.completion_per_1k_rub)
