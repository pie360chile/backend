"""Cliente OpenAI para Agent v2 (chat y extracción JSON)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

from app.backend.core.config import load_backend_env, settings


def _openai_api_key() -> str:
    load_backend_env()
    return (os.getenv("OPENAI_API_KEY") or settings.openai_api_key or "").strip()


def openai_api_key_configured() -> bool:
    return bool(_openai_api_key())


def _client():
    from openai import OpenAI

    api_key = _openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada en el backend.")
    return OpenAI(api_key=api_key)


def stream_chat_completion(messages: list[dict[str, str]]) -> Iterator[str]:
    client = _client()
    stream = client.chat.completions.create(
        model=settings.agent_v2_model,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


def json_chat_completion(messages: list[dict[str, str]]) -> dict[str, Any]:
    client = _client()
    response = client.chat.completions.create(
        model=settings.agent_v2_model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("El modelo no devolvió JSON válido.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("El modelo devolvió un JSON que no es un objeto.")
    return parsed
