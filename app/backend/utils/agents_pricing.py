"""Precios estimados del modelo de agentes (USD por 1M tokens)."""

from __future__ import annotations

from dataclasses import dataclass

from app.backend.core.config import settings


@dataclass(frozen=True)
class ModelPricing:
    model: str
    input_per_1m_usd: float
    output_per_1m_usd: float
    cached_input_per_1m_usd: float | None = None


# Precios públicos OpenAI (tier estándar) — jul 2026.
_MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5.5": ModelPricing(
        model="gpt-5.5",
        input_per_1m_usd=5.0,
        output_per_1m_usd=30.0,
        cached_input_per_1m_usd=0.5,
    ),
    "gpt-5.4": ModelPricing(
        model="gpt-5.4",
        input_per_1m_usd=2.5,
        output_per_1m_usd=15.0,
        cached_input_per_1m_usd=0.25,
    ),
}


def pricing_for_model(model: str | None = None) -> ModelPricing:
    key = (model or settings.agents_model or "gpt-5.5").strip().lower()
    if key in _MODEL_PRICING:
        return _MODEL_PRICING[key]
    return ModelPricing(
        model=key,
        input_per_1m_usd=5.0,
        output_per_1m_usd=30.0,
        cached_input_per_1m_usd=0.5,
    )


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    model: str | None = None,
) -> float:
    p = pricing_for_model(model)
    return (prompt_tokens / 1_000_000) * p.input_per_1m_usd + (
        completion_tokens / 1_000_000
    ) * p.output_per_1m_usd
