"""Cliente LLM genérico (chat completions estilo OpenAI, streaming)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.backend.core.config import settings

DEFAULT_MODEL_CODE = "deepseek-v4-pro"


def resolve_llm_api_key(db: Session | None = None) -> str:
    """Prioridad: clave en BD (DeepSeek Token) → AGENTS_LLM_API_KEY en .env."""
    if db is not None:
        try:
            from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass

            key = AgentsLlmModelsClass(db).get_llm_api_key()
            if key:
                return key
        except Exception:
            pass
    return (settings.agents_llm_api_key or "").strip()


def llm_chat_completions_url() -> str:
    base = (settings.agents_llm_api_base or "https://api.deepseek.com").rstrip("/")
    return f"{base}/chat/completions"


def normalize_usage(raw: dict[str, Any] | None) -> dict[str, int] | None:
    """Normaliza usage de DeepSeek/OpenAI a prompt/completion/total."""
    if not isinstance(raw, dict) or not raw:
        return None
    prompt = int(
        raw.get("prompt_tokens")
        or raw.get("input_tokens")
        or raw.get("promptTokens")
        or 0
    )
    completion = int(
        raw.get("completion_tokens")
        or raw.get("output_tokens")
        or raw.get("completionTokens")
        or 0
    )
    total = int(raw.get("total_tokens") or raw.get("totalTokens") or 0)
    if prompt <= 0 and completion <= 0 and total <= 0:
        return None
    if total <= 0:
        total = prompt + completion
    return {
        "prompt_tokens": max(0, prompt),
        "completion_tokens": max(0, completion),
        "total_tokens": max(0, total),
    }


def estimate_tokens_from_text(text: str) -> int:
    """Estimación rough (~4 chars/token) si el proveedor no envía usage."""
    return max(0, (len(text or "") + 3) // 4)


def stream_chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    api_key: str | None = None,
    db: Session | None = None,
    timeout: int = 120,
) -> Iterator[dict[str, Any]]:
    """
    Yields:
      {"type": "text_delta", "delta": "..."}
      {"type": "done", "data": {"reply": "...", "usage": {...}}}
      {"type": "error", "message": "...", "code": "..."}
    """
    key = (api_key or "").strip() or resolve_llm_api_key(db)
    if not key:
        yield {
            "type": "error",
            "message": (
                "Falta el DeepSeek Token. "
                "Configúralo en Agentes → DeepSeek Token."
            ),
            "code": "missing_api_key",
        }
        return

    model_code = (model or DEFAULT_MODEL_CODE).strip() or DEFAULT_MODEL_CODE
    try:
        response = requests.post(
            llm_chat_completions_url(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_code,
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            },
            stream=True,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        yield {
            "type": "error",
            "message": f"No se pudo conectar con el proveedor LLM: {exc}",
            "code": "llm_network",
        }
        return

    if response.status_code >= 400:
        detail = response.text[:400]
        try:
            payload = response.json()
            detail = (
                payload.get("error", {}).get("message")
                or payload.get("message")
                or detail
            )
        except Exception:
            pass
        yield {
            "type": "error",
            "message": f"Error del proveedor LLM ({response.status_code}): {detail}",
            "code": "llm_http",
        }
        return

    full_reply = ""
    usage_raw: dict[str, Any] | None = None
    try:
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            chunk_usage = chunk.get("usage")
            if isinstance(chunk_usage, dict) and chunk_usage:
                usage_raw = chunk_usage
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = (choices[0].get("delta") or {}).get("content") or ""
            if not delta:
                continue
            full_reply += delta
            yield {"type": "text_delta", "delta": delta}
    except requests.RequestException as exc:
        yield {
            "type": "error",
            "message": f"Error leyendo stream del LLM: {exc}",
            "code": "llm_stream",
        }
        return

    done_payload: dict[str, Any] = {"reply": full_reply}
    normalized = normalize_usage(usage_raw)
    if normalized:
        done_payload["usage"] = normalized
    yield {"type": "done", "data": done_payload}
