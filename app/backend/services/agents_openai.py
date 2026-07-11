"""OpenAI client for Agents (chat and JSON extraction)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from app.backend.core.config import load_backend_env, settings


@dataclass(frozen=True)
class OpenAIUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


def _openai_api_key() -> str:
    load_backend_env()
    return (os.getenv("OPENAI_API_KEY") or settings.openai_api_key or "").strip()


def openai_api_key_configured() -> bool:
    return bool(_openai_api_key())


def _client():
    from openai import OpenAI

    api_key = _openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured on the backend.")
    return OpenAI(api_key=api_key)


def _usage_from_response(usage: Any, model: str) -> OpenAIUsage | None:
    if usage is None:
        return None
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or (prompt + completion))
    return OpenAIUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        model=model,
    )


def stream_chat_completion(
    messages: list[dict[str, str]],
    usage_out: list[OpenAIUsage] | None = None,
) -> Iterator[str]:
    client = _client()
    model = settings.agents_model
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        if usage_out is not None and getattr(chunk, "usage", None):
            parsed = _usage_from_response(chunk.usage, model)
            if parsed:
                usage_out.clear()
                usage_out.append(parsed)
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


def json_chat_completion(
    messages: list[dict[str, str]],
) -> tuple[dict[str, Any], OpenAIUsage | None]:
    client = _client()
    model = settings.agents_model
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The model did not return valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("The model returned JSON that is not an object.")
    return parsed, _usage_from_response(response.usage, model)
