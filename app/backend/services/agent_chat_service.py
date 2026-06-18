"""Chat del agente con GPT 5.5, archivos OpenAI y code interpreter."""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentModel
from app.backend.services.agent_familia_generate_service import try_deterministic_familia_report
from app.backend.services.openai_agent_service import (
    chat_with_openai_responses,
    is_container_expired,
    stream_chat_with_openai_responses,
    sync_agent_openai_files,
)
from app.backend.utils.agent_document_index import search_agent_knowledge, strip_html
from app.backend.utils.agent_file_selection import select_agent_file_rows
from app.backend.utils.agent_files import ensure_responses_dir
from app.backend.utils.agent_student_lookup import resolve_student_context_for_agent

def _prepare_openai_files(
    db: Session,
    agent: AgentModel,
    message: str,
    hits: list[dict[str, Any]],
) -> tuple[list[str], list[str], int, list]:
    """Devuelve (openai_file_ids, nombres usados, total archivos del agente, filas seleccionadas)."""
    from app.backend.db.models import AgentFileModel

    ensure_responses_dir(agent.id)

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
    return openai_file_ids, selected_names, total, selected_rows


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
        try:
            _, _, _, selected_rows = _prepare_openai_files(db, agent, trimmed, hits)
            student_context = resolve_student_context_for_agent(db, trimmed)
            deterministic = try_deterministic_familia_report(
                db, agent.id, trimmed, selected_rows, student_context
            )
            if deterministic:
                db.commit()
                return {
                    "reply": deterministic["reply"],
                    "citations": citations,
                    "usedChunks": len(hits),
                    "openaiFilesUsed": 0,
                    "responseFiles": deterministic.get("responseFiles") or [],
                }
        except Exception:
            db.rollback()
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

        openai_file_ids, selected_names, total_files, selected_rows = _prepare_openai_files(
            db, agent, trimmed, hits
        )
        student_context = resolve_student_context_for_agent(db, trimmed)

        deterministic = try_deterministic_familia_report(
            db, agent.id, trimmed, selected_rows, student_context
        )
        if deterministic:
            db.commit()
            return {
                "reply": deterministic["reply"],
                "citations": citations,
                "usedChunks": len(hits),
                "openaiFilesUsed": 0,
                "containerId": None,
                "model": deterministic.get("model"),
                "responseFiles": deterministic.get("responseFiles") or [],
                "responseFilesWarning": None,
            }

        db.commit()
        db.refresh(agent)

        result = chat_with_openai_responses(
            db,
            agent,
            trimmed,
            openai_file_ids,
            student_context=student_context,
            selected_rows=selected_rows,
            instruction_file_names=selected_names,
        )
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

    try:
        yield {"type": "step", "message": "Preparando archivos relevantes para esta consulta…"}
        openai_file_ids, selected_names, total_files, selected_rows = _prepare_openai_files(
            db, agent, trimmed, hits
        )
        from app.backend.utils.agent_familia_template import resolve_familia_template_from_rows

        base_tpl, tpl_kind = resolve_familia_template_from_rows(agent.id, selected_rows)
        if tpl_kind == "form" and base_tpl:
            yield {
                "type": "step",
                "message": f"Plantilla formulario detectada: {base_tpl}. Se excluye formato ministerial de tablas.",
            }

        student_context = resolve_student_context_for_agent(db, trimmed)
        if student_context:
            student_name = student_context.get("student_full_name") or "el estudiante"
            yield {
                "type": "step",
                "message": f"Estudiante encontrado en PIE360: {student_name}.",
            }
        else:
            yield {
                "type": "step",
                "message": "No se encontró estudiante en la base de datos por el nombre del mensaje.",
            }

        deterministic = try_deterministic_familia_report(
            db, agent.id, trimmed, selected_rows, student_context
        )
        if deterministic:
            yield {
                "type": "step",
                "message": (
                    f"Generando informe con plantilla formulario "
                    f"«{deterministic.get('templateUsed')}» y datos de la base de datos…"
                ),
            }
            db.commit()
            yield {
                "type": "done",
                "data": {
                    "reply": deterministic["reply"],
                    "citations": citations,
                    "usedChunks": len(hits),
                    "openaiFilesUsed": 0,
                    "containerId": None,
                    "model": deterministic.get("model"),
                    "responseFiles": deterministic.get("responseFiles") or [],
                    "responseFilesWarning": None,
                },
            }
            return
    except Exception as exc:
        db.rollback()
        yield {
            "type": "done",
            "data": {
                "reply": _fallback_reply(trimmed, hits, f"No se pudo generar el informe: {exc}"),
                "citations": citations,
                "usedChunks": len(hits),
                "warning": str(exc),
            },
        }
        return

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

        openai_file_ids, selected_names, total_files, selected_rows = _prepare_openai_files(
            db, agent, trimmed, hits
        )
        student_context = resolve_student_context_for_agent(db, trimmed)

        if openai_file_ids and selected_names:
            yield {
                "type": "step",
                "message": (
                    f"Usando {len(openai_file_ids)} de {total_files} archivos del agente."
                    if total_files and len(openai_file_ids) < total_files
                    else f"{len(openai_file_ids)} archivo(s) listos para el análisis."
                ),
            }
            for name in selected_names:
                yield {"type": "step", "message": f"Leyendo archivo: {name}"}
        elif not openai_file_ids:
            yield {"type": "step", "message": "No hay archivos adjuntos; responderé solo con el rol del agente."}

        for event in stream_chat_with_openai_responses(
            db,
            agent,
            trimmed,
            openai_file_ids,
            instruction_file_names=selected_names,
            student_context=student_context,
            selected_rows=selected_rows,
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
