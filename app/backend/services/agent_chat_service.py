"""Chat del agente con GPT 5.5, archivos OpenAI y code interpreter."""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentModel
from app.backend.services.openai_agent_service import (
    chat_with_openai_responses,
    is_container_expired,
    stream_chat_with_openai_responses,
    sync_agent_openai_files,
)
from app.backend.utils.agent_document_index import search_agent_knowledge, strip_html
from app.backend.utils.agent_file_selection import select_agent_file_rows

def _prepare_openai_files(
    db: Session,
    agent: AgentModel,
    message: str,
    hits: list[dict[str, Any]],
) -> tuple[list[str], list[str], int]:
    """Devuelve (openai_file_ids, nombres usados, total archivos del agente)."""
    from app.backend.db.models import AgentFileModel

    total = (
        db.query(AgentFileModel)
        .filter(AgentFileModel.agent_id == agent.id)
        .count()
    )
    selected_rows = select_agent_file_rows(db, agent.id, message, hits)
    selected_names = [row.display_name for row in selected_rows if row.display_name]

    if total and len(selected_rows) < total:
        agent.openai_container_id = None
        agent.openai_container_updated_at = None
        db.flush()

    openai_file_ids = sync_agent_openai_files(db, agent.id, only_rows=selected_rows)
    return openai_file_ids, selected_names, total


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

        openai_file_ids, _, total_files = _prepare_openai_files(db, agent, trimmed, hits)
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
            "responseFilesWarning": result.get("responseFilesWarning"),
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


def iter_chat_with_agent_events(
    db: Session,
    agent_id: str,
    message: str,
    top_k: int = 5,
) -> Iterator[dict[str, Any]]:
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        yield {"type": "error", "message": "Agente no encontrado"}
        return

    trimmed = (message or "").strip()
    if not trimmed:
        yield {"type": "error", "message": "El mensaje está vacío"}
        return

    yield {"type": "step", "message": "Buscando fragmentos relevantes en tus documentos…"}
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
    if hits:
        yield {
            "type": "step",
            "message": f"Se encontraron {len(hits)} fragmento(s) relacionados en los archivos indexados.",
        }

    if not settings.openai_api_key:
        yield {
            "type": "done",
            "data": {
                "reply": _fallback_reply(trimmed, hits, "Configure OPENAI_API_KEY"),
                "citations": citations,
                "usedChunks": len(hits),
            },
        }
        return

    try:
        if is_container_expired(agent.openai_container_updated_at):
            agent.openai_container_id = None
            agent.openai_container_updated_at = None
            db.flush()

        yield {"type": "step", "message": "Preparando archivos relevantes para esta consulta…"}
        openai_file_ids, selected_names, total_files = _prepare_openai_files(db, agent, trimmed, hits)
        db.commit()
        db.refresh(agent)

        if openai_file_ids:
            if total_files and len(openai_file_ids) < total_files:
                names_preview = ", ".join(selected_names[:4])
                extra = f" ({names_preview})" if names_preview else ""
                yield {
                    "type": "step",
                    "message": (
                        f"Usando {len(openai_file_ids)} de {total_files} archivos relevantes"
                        f"{extra}."
                    ),
                }
            else:
                yield {
                    "type": "step",
                    "message": f"{len(openai_file_ids)} archivo(s) listos para el análisis.",
                }
        else:
            yield {"type": "step", "message": "No hay archivos adjuntos; responderé solo con el rol del agente."}

        for event in stream_chat_with_openai_responses(
            db, agent, trimmed, openai_file_ids, instruction_file_names=selected_names
        ):
            if not event:
                continue
            if event.get("type") == "done":
                payload = event["data"]
                db.commit()
                yield {
                    "type": "done",
                    "data": {
                        "reply": payload["reply"],
                        "citations": citations,
                        "usedChunks": len(hits),
                        "openaiFilesUsed": payload.get("openaiFilesUsed", 0),
                        "containerId": payload.get("containerId"),
                        "model": payload.get("model"),
                        "responseFiles": payload.get("responseFiles") or [],
                        "responseFilesWarning": payload.get("responseFilesWarning"),
                    },
                }
            else:
                yield event
    except Exception as exc:
        db.rollback()
        yield {
            "type": "done",
            "data": {
                "reply": _fallback_reply(trimmed, hits, f"No se pudo usar OpenAI: {exc}"),
                "citations": citations,
                "usedChunks": len(hits),
                "warning": str(exc),
            },
        }
