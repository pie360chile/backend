"""Chat del agente con GPT 5.5, archivos OpenAI y code interpreter."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentModel
from app.backend.services.openai_agent_service import (
    chat_with_openai_responses,
    is_container_expired,
    sync_agent_openai_files,
)
from app.backend.utils.agent_document_index import search_agent_knowledge, strip_html


def _fallback_reply(message: str, hits: list[dict[str, Any]], reason: str | None = None) -> str:
    if hits:
        intro = "Según los documentos indexados localmente de este agente:\n\n"
        body = "\n\n---\n\n".join(
            f"**{hit['fileName']}** (fragmento {hit['chunkIndex'] + 1})\n{hit['content'][:700]}"
            for hit in hits
        )
        suffix = f"\n\n_({reason or 'Respuesta sin OpenAI'})._"
        return f"{intro}{body}{suffix}"

    return (
        "No encontré información relevante en los documentos de este agente. "
        "Sube archivos en la configuración del agente o reformula la pregunta."
        + (f" ({reason})" if reason else "")
    )


def chat_with_agent(
    db: Session,
    agent_id: str,
    message: str,
    top_k: int = 5,
) -> dict[str, Any] | dict[str, str]:
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        return {"status": "error", "message": "Agente no encontrado"}

    trimmed = (message or "").strip()
    if not trimmed:
        return {"status": "error", "message": "El mensaje está vacío"}

    hits = search_agent_knowledge(db, agent_id, trimmed, top_k=top_k)
    citations = [
        {
            "fileId": hit["fileId"],
            "fileName": hit["fileName"],
            "chunkIndex": hit["chunkIndex"],
            "score": hit["score"],
        }
        for hit in hits
    ]

    if not settings.openai_api_key:
        return {
            "reply": _fallback_reply(trimmed, hits, "Configure OPENAI_API_KEY"),
            "citations": citations,
            "usedChunks": len(hits),
        }

    try:
        if is_container_expired(agent.openai_container_updated_at):
            agent.openai_container_id = None
            agent.openai_container_updated_at = None
            db.flush()

        openai_file_ids = sync_agent_openai_files(db, agent_id)
        db.commit()
        db.refresh(agent)

        result = chat_with_openai_responses(db, agent, trimmed, openai_file_ids)
        db.commit()

        return {
            "reply": result["reply"],
            "citations": citations,
            "usedChunks": len(hits),
            "openaiFilesUsed": result.get("openaiFilesUsed", 0),
            "containerId": result.get("containerId"),
            "model": result.get("model"),
            "responseFiles": result.get("responseFiles") or [],
        }
    except Exception as exc:
        db.rollback()
        role_preview = strip_html(agent.role_instructions or "")[:120]
        return {
            "reply": _fallback_reply(trimmed, hits, f"No se pudo usar OpenAI: {exc}"),
            "citations": citations,
            "usedChunks": len(hits),
            "warning": str(exc),
            "rolePreview": role_preview or None,
        }
