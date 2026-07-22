"""Agents chat via DeepSeek (OpenAI-compatible streaming)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass
from app.backend.classes.agents_mcp_class import AgentsMcpClass
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.core.config import settings
from app.backend.db.models.agent import AgentModel
from app.backend.utils.agents_chat_context import (
    infer_document_id,
    resolve_student_id,
    student_identification_hint,
    wants_document_generation,
)
from app.backend.utils.agents_llm_client import (
    estimate_tokens_from_text,
    normalize_usage,
    stream_chat_completion,
)
from app.backend.utils.agents_mcp_fields import (
    extract_fields_from_reply,
    is_content_too_thin,
    strip_fields_json_from_reply,
)


def _drive_path_block(*, customer_id: int, agent_name: str) -> str:
    name = (agent_name or "").strip() or "agente"
    path = f"{int(customer_id)}/{name}/"
    return (
        "Google Drive del agente:\n"
        f"- Ruta bajo la carpeta raíz de Agentes: {path}\n"
        "- Usa esos archivos cuando necesites plantillas, anexos o contexto del agente.\n"
        "- No uses el Drive de colegios (school_id/año/…)."
    )


def _build_system_prompt(
    *,
    db: Session,
    agent: AgentModel,
    customer_id: int,
    student_id: int | None,
    student_rut: str | None,
    document_id: int | None,
    message: str = "",
) -> str:
    parts: list[str] = []
    instructions = (agent.role_instructions or "").strip()
    if instructions:
        parts.append(instructions)

    mcp_base = (settings.api_public_base or "").rstrip("/")
    mcp_url = f"{mcp_base}/mcp" if mcp_base else "/api/mcp"
    parts.append(
        AgentsMcpClass(db).build_store_data_prompt_block(
            agent=agent,
            customer_id=int(customer_id),
            document_id=document_id,
            student_id=student_id,
            student_rut=student_rut,
            mcp_url=mcp_url,
        )
    )
    parts.append(_drive_path_block(customer_id=int(customer_id), agent_name=agent.name or ""))

    try:
        from app.backend.utils import agents_derived_storage as derived

        student_name = None
        if student_id:
            try:
                from app.backend.db.models.pie_core import StudentPersonalInfoModel

                spi = (
                    db.query(StudentPersonalInfoModel)
                    .filter(StudentPersonalInfoModel.student_id == int(student_id))
                    .first()
                )
                if spi:
                    student_name = " ".join(
                        p
                        for p in (
                            getattr(spi, "names", None),
                            getattr(spi, "father_lastname", None),
                            getattr(spi, "mother_lastname", None),
                        )
                        if p
                    ).strip() or None
            except Exception:
                student_name = None

        files_block, _n = derived.build_selective_files_context(
            agent.name or "",
            query=message or "",
            student_rut=student_rut,
            student_name=student_name,
            customer_id=int(customer_id),
        )
        if files_block:
            parts.append(files_block)
    except Exception:
        pass

    if student_id:
        try:
            parts.append(
                student_identification_hint(db, int(student_id), document_id)
            )
        except Exception:
            pass

    extras: list[str] = []
    if student_id:
        extras.append(f"student_id={student_id}")
    if student_rut:
        extras.append(f"student_rut={student_rut}")
    if document_id:
        extras.append(f"document_id={document_id}")
    if extras:
        parts.append("Contexto PIE360: " + ", ".join(extras))

    return "\n\n".join(parts).strip()


def _build_messages(
    *,
    system_prompt: str,
    message: str,
    history: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for item in history or []:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": (message or "").strip()})
    return messages


class AgentsChatClass:
    def __init__(
        self,
        db: Session,
        *,
        customer_id: int | None = None,
        school_id: int | None = None,
        user_id: int | None = None,
    ) -> None:
        self.db = db
        self.customer_id = customer_id
        self.school_id = school_id
        self.user_id = user_id

    def stream_chat(
        self,
        agent_id: str,
        message: str,
        student_id: int | None = None,
        student_rut: str | None = None,
        document_id: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        if not self.customer_id:
            yield {
                "type": "error",
                "message": "customer_id es requerido para chatear con el agente.",
                "code": "missing_customer",
            }
            return

        agent_row = AgentsClass(self.db)._get_agent(agent_id, int(self.customer_id))
        if not agent_row:
            yield {
                "type": "error",
                "message": "Agente no encontrado.",
                "code": "agent_not_found",
            }
            return

        text = (message or "").strip()
        if not text:
            yield {
                "type": "error",
                "message": "El mensaje está vacío.",
                "code": "empty_message",
            }
            return

        resolved_student_id, rut_used, student_issue = resolve_student_id(
            self.db,
            student_id=student_id,
            student_rut=student_rut,
            message=text,
            history=history,
            customer_id=int(self.customer_id) if self.customer_id else None,
            school_id=int(self.school_id) if self.school_id else None,
        )
        resolved_document_id = document_id or infer_document_id(
            self.db, agent_id, text, history
        )
        effective_rut = (student_rut or rut_used or "").strip() or None

        llm = AgentsLlmModelsClass(self.db)
        model_code = llm.get_selected_model_code()
        yield {"type": "step", "message": f"Consultando DeepSeek ({model_code})…"}

        system_prompt = _build_system_prompt(
            db=self.db,
            agent=agent_row,
            customer_id=int(self.customer_id),
            student_id=resolved_student_id,
            student_rut=effective_rut,
            document_id=resolved_document_id,
            message=text,
        )
        messages = _build_messages(
            system_prompt=system_prompt,
            message=text,
            history=history,
        )

        reply_text = ""
        usage: dict[str, Any] | None = None
        for event in stream_chat_completion(messages, model=model_code, db=self.db):
            if event.get("type") == "text_delta":
                reply_text += event.get("delta") or ""
                yield event
            elif event.get("type") == "done":
                data = event.get("data") or {}
                reply_text = data.get("reply") or reply_text
                usage = normalize_usage(
                    data.get("usage") if isinstance(data.get("usage"), dict) else None
                )
            elif event.get("type") == "error":
                yield event
                return
            else:
                yield event

        visible_reply = reply_text
        response_files: list[dict[str, Any]] = []
        warning: str | None = None
        want_doc = wants_document_generation(text, history)
        fields = extract_fields_from_reply(reply_text)

        if want_doc or fields:
            if student_issue == "needs_rut" and not resolved_student_id:
                warning = (
                    "Para generar el documento indica el nombre o RUT del estudiante "
                    "o ábrelo desde la ficha (student_id en la URL)."
                )
            elif student_issue == "not_found":
                warning = f"No encontré estudiante con RUT {rut_used}."
            elif not resolved_student_id:
                warning = "Falta student_id para generar el documento."
            elif not resolved_document_id:
                warning = (
                    "Falta document_id / plantilla del agente. "
                    "Sube el modelo en Documentos del agente."
                )
            elif not fields:
                warning = (
                    "El agente redactó pero no envió el bloque JSON de fields. "
                    "Pide de nuevo «genera el informe» o completa los campos."
                )
            else:
                yield {"type": "step", "message": "Generando documento (create_document)…"}
                try:
                    created = AgentsMcpClass(self.db).create_document(
                        agent_id=agent_id,
                        customer_id=int(self.customer_id),
                        student_id=int(resolved_student_id),
                        document_id=int(resolved_document_id),
                        fields=fields,
                    )
                    if created.get("status") == "error":
                        warning = created.get("message") or "No se pudo generar el documento."
                    else:
                        data = created.get("data") or {}
                        response_files = list(data.get("responseFiles") or [])
                        visible_reply = strip_fields_json_from_reply(reply_text)
                        if is_content_too_thin(fields):
                            warning = (
                                "El documento se generó, pero el contenido narrativo quedó "
                                "corto o incompleto. Pide de nuevo: «reescribe todos los "
                                "campos narrativos con párrafos detallados (2 a 5 oraciones "
                                "cada uno) usando el archivo de evaluación del estudiante "
                                "y genera el documento»."
                            )
                        elif data.get("formFilled"):
                            visible_reply = (
                                visible_reply.rstrip()
                                + "\n\nDocumento generado y datos del formulario guardados "
                                "en la carpeta del estudiante."
                            )
                except Exception as exc:
                    warning = f"Error al generar documento: {exc}"

        done_data: dict[str, Any] = {
            "reply": visible_reply,
            "usage": usage,
            "model": model_code,
            "responseFiles": response_files,
        }
        if warning:
            done_data["warning"] = warning
        yield {"type": "done", "data": done_data}

        if not self.customer_id:
            return

        if not usage:
            prompt_chars = "\n".join(
                str(m.get("content") or "") for m in messages if isinstance(m, dict)
            )
            pt = estimate_tokens_from_text(prompt_chars)
            ct = estimate_tokens_from_text(reply_text)
            usage = {
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": pt + ct,
            }

        try:
            AgentsUsageClass(self.db).record_chat(
                customer_id=int(self.customer_id),
                school_id=int(self.school_id) if self.school_id else None,
                user_id=int(self.user_id) if self.user_id else None,
                agent_id=agent_id,
                model=model_code,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                input_text=text,
                output_text=visible_reply,
            )
        except Exception:
            self.db.rollback()
