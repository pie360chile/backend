"""Chat del agente con GPT 5.5, archivos OpenAI y code interpreter."""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import AgentModel
from app.backend.services.agent_familia_generate_service import (
    can_use_familia_hybrid,
    create_familia_base_for_gpt,
    try_deterministic_familia_report,
)
from app.backend.services.openai_agent_service import (
    attach_file_to_container,
    chat_with_openai_responses,
    is_container_expired,
    stream_chat_with_openai_responses,
    upload_local_file_to_openai,
)
from app.backend.utils.agent_document_index import search_agent_knowledge, strip_html
from app.backend.utils.agent_file_selection import (
    select_agent_file_rows,
    trim_rows_for_familia_hybrid_speed,
)
from app.backend.utils.agent_files import agent_dir, ensure_responses_dir
from app.backend.utils.agent_student_lookup import (
    check_familia_rut_requirement,
    extract_rut_from_message,
    is_familia_report_request,
    resolve_student_context_for_agent,
)

def _prepare_openai_files(
    db: Session,
    agent: AgentModel,
    message: str,
    hits: list[dict[str, Any]],
) -> tuple[list[str], list[str], int, list]:
    """Devuelve (openai_file_ids, nombres usados, total archivos del agente, filas seleccionadas)."""
    from app.backend.db.models import AgentFileModel
    from app.backend.services.openai_agent_service import ensure_openai_file_for_row

    ensure_responses_dir(agent.id)

    total = (
        db.query(AgentFileModel)
        .filter(AgentFileModel.agent_id == agent.id)
        .count()
    )
    selected_rows = select_agent_file_rows(db, agent.id, message, hits)
    if settings.openai_agent_familia_fast and is_familia_report_request(message):
        selected_rows = trim_rows_for_familia_hybrid_speed(selected_rows, agent.id)
    selected_names: list[str] = []

    if total and len(selected_rows) < total:
        agent.openai_container_id = None
        agent.openai_container_updated_at = None
        db.flush()

    openai_file_ids: list[str] = []
    for row in selected_rows:
        disk_path = agent_dir(agent.id) / row.id
        if not disk_path.is_file():
            continue
        openai_id = ensure_openai_file_for_row(db, agent, row, disk_path)
        if openai_id:
            openai_file_ids.append(openai_id)
            if row.display_name:
                selected_names.append(row.display_name)
    return openai_file_ids, selected_names, total, selected_rows


def _file_preparation_step_messages(
    openai_file_ids: list[str],
    selected_names: list[str],
    total_in_agent: int,
    *,
    base_doc_name: str | None = None,
) -> list[str]:
    """Mensajes claros: conteo alineado con los archivos realmente enviados a OpenAI."""
    names = list(selected_names)
    n = len(openai_file_ids)
    if len(names) != n:
        names = names[:n]

    case_names = [nm for nm in names if nm != base_doc_name]
    has_base = bool(base_doc_name and base_doc_name in names)
    case_count = len(case_names)

    if has_base and case_count:
        summary = (
            f"Enviando {n} archivo(s) al modelo "
            f"(1 base PIE360 + {case_count} del caso). "
            f"El agente tiene {total_in_agent} archivo(s) en total."
        )
    elif total_in_agent and n < total_in_agent:
        summary = (
            f"Enviando {n} de {total_in_agent} archivo(s) del agente al modelo."
        )
    else:
        summary = f"Enviando {n} archivo(s) al modelo para esta consulta."

    steps = [summary]
    for name in names[:8]:
        if name == base_doc_name:
            steps.append(f"Base PIE360: {name}")
        else:
            steps.append(f"Archivo del caso: {name}")
    return steps


def _attach_familia_hybrid_base(
    agent: AgentModel,
    agent_id: str,
    message: str,
    student_context: dict[str, Any] | None,
    selected_rows: list,
    openai_file_ids: list[str],
    selected_names: list[str],
) -> tuple[list[str], list[str], str | None, str | None]:
    """
    Si aplica informe familia híbrido, sube base con identificación PIE360 para que GPT redacte.
    Devuelve (file_ids, names, base_doc_name, template_name).
    """
    template_path = can_use_familia_hybrid(message, student_context, selected_rows, agent_id)
    if not template_path or not student_context or not settings.openai_api_key:
        return openai_file_ids, selected_names, None, None

    base = create_familia_base_for_gpt(agent_id, student_context, template_path)
    file_id = upload_local_file_to_openai(base["disk_path"], base["display_name"])
    if agent.openai_container_id and not is_container_expired(agent.openai_container_updated_at):
        try:
            attach_file_to_container(agent.openai_container_id, file_id)
        except Exception:
            pass
    return (
        [file_id, *openai_file_ids],
        [base["display_name"], *selected_names],
        base["display_name"],
        base["template_name"],
    )


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

    rut_prompt = check_familia_rut_requirement(db, trimmed)
    if rut_prompt:
        return {
            "reply": rut_prompt,
            "citations": citations,
            "usedChunks": len(hits),
        }

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

        openai_file_ids, selected_names, base_doc_name, _tpl = _attach_familia_hybrid_base(
            agent,
            agent.id,
            trimmed,
            student_context,
            selected_rows,
            openai_file_ids,
            selected_names,
        )

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
            familia_base_doc_name=base_doc_name,
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

    rut_prompt = check_familia_rut_requirement(db, trimmed)
    if rut_prompt:
        yield {
            "type": "done",
            "data": {
                "reply": rut_prompt,
                "citations": citations,
                "usedChunks": len(hits),
            },
        }
        return

    if not settings.openai_api_key:
        try:
            _, _, _, selected_rows = _prepare_openai_files(db, agent, trimmed, hits)
            student_context = resolve_student_context_for_agent(db, trimmed)
            deterministic = try_deterministic_familia_report(
                db, agent.id, trimmed, selected_rows, student_context
            )
            if deterministic:
                db.commit()
                yield {
                    "type": "done",
                    "data": {
                        "reply": deterministic["reply"],
                        "citations": citations,
                        "usedChunks": len(hits),
                        "openaiFilesUsed": 0,
                        "responseFiles": deterministic.get("responseFiles") or [],
                    },
                }
                return
        except Exception as exc:
            db.rollback()
            yield {
                "type": "done",
                "data": {
                    "reply": _fallback_reply(trimmed, hits, str(exc)),
                    "citations": citations,
                    "usedChunks": len(hits),
                    "warning": str(exc),
                },
            }
            return
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
        openai_file_ids, selected_names, total_files, selected_rows = _prepare_openai_files(
            db, agent, trimmed, hits
        )
        from app.backend.utils.agent_familia_template import resolve_familia_template_from_rows

        base_tpl, tpl_kind = resolve_familia_template_from_rows(agent.id, selected_rows)
        if tpl_kind == "form" and base_tpl:
            yield {
                "type": "step",
                "message": f"Plantilla formulario detectada: {base_tpl}.",
            }

        student_context = resolve_student_context_for_agent(db, trimmed)
        if student_context:
            student_name = student_context.get("student_full_name") or "el estudiante"
            student_rut = student_context.get("student_identification_number") or ""
            rut_part = f" (RUT {student_rut})" if student_rut else ""
            yield {
                "type": "step",
                "message": f"Estudiante encontrado en PIE360: {student_name}{rut_part}.",
            }
        elif is_familia_report_request(trimmed):
            rut = extract_rut_from_message(trimmed)
            if not rut:
                yield {
                    "type": "step",
                    "message": (
                        "Informe familia: incluye el RUT del estudiante en el mensaje "
                        "(ej. RUT 23.442.145-K)."
                    ),
                }
            else:
                yield {
                    "type": "step",
                    "message": (
                        f"No se encontró estudiante en PIE360 con el RUT {rut}. "
                        "Verifica el RUT en la plataforma."
                    ),
                }

        openai_file_ids, selected_names, base_doc_name, template_used = _attach_familia_hybrid_base(
            agent,
            agent.id,
            trimmed,
            student_context,
            selected_rows,
            openai_file_ids,
            selected_names,
        )
        if base_doc_name and template_used:
            yield {
                "type": "step",
                "message": (
                    f"Identificación cargada desde PIE360 en «{base_doc_name}». "
                    f"GPT redactará el contenido según el rol usando la cartilla y archivos del caso…"
                ),
            }

        db.commit()
        db.refresh(agent)

        if openai_file_ids and selected_names:
            for step_msg in _file_preparation_step_messages(
                openai_file_ids,
                selected_names,
                total_files,
                base_doc_name=base_doc_name,
            ):
                yield {"type": "step", "message": step_msg}
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
            familia_base_doc_name=base_doc_name,
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
