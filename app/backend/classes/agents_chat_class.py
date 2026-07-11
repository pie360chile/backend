"""Agents chat: prompt from DB + OpenAI + Word/PDF generation + save to folders."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.agents_document_service import (
    build_fields_prompt,
    generate_and_save_document,
)
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.core.config import settings
from app.backend.db.models.agent import AgentModel
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel
from app.backend.db.models.pie_core import StudentPersonalInfoModel
from app.backend.services import agents_openai
from app.backend.services.agents_openai import OpenAIUsage, openai_api_key_configured
from app.backend.utils import agents_storage as storage
from app.backend.utils.agents_file_context import build_agent_files_context
from app.backend.utils.agents_prompt_sanitize import (
    CHAT_OUTPUT_OVERRIDE,
    DOCUMENT_FIELD_EXTRACTION_GUIDE,
    extract_priority_directives_from_prompt,
    sanitize_role_instructions_for_chat,
)
from app.backend.utils.agents_chat_context import (
    infer_document_id,
    resolve_student_id,
    student_identification_hint,
    wants_document_generation,
)
from app.backend.utils.agents_template_inspector import fields_from_json


def _sse(event: dict[str, Any]) -> dict[str, Any]:
    return event


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
        self._usage = AgentsUsageClass(db)

    def _record_usage(
        self,
        *,
        agent_id: str,
        request_kind: str,
        usage: OpenAIUsage | None,
    ) -> None:
        if not usage or not self.customer_id:
            return
        try:
            self._usage.record(
                customer_id=self.customer_id,
                school_id=self.school_id,
                user_id=self.user_id,
                agent_id=agent_id,
                request_kind=request_kind,
                model=usage.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        except Exception:
            # Do not interrupt chat if usage metrics fail.
            self.db.rollback()


    def _get_agent(self, agent_id: str) -> AgentModel | None:
        return self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()

    def _get_template(self, agent_id: str, document_id: int) -> AgentDocumentTemplateModel | None:
        return (
            self.db.query(AgentDocumentTemplateModel)
            .filter(
                AgentDocumentTemplateModel.agent_id == agent_id,
                AgentDocumentTemplateModel.document_id == document_id,
            )
            .first()
        )

    def _list_templates_summary(self, agent_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AgentDocumentTemplateModel)
            .filter(AgentDocumentTemplateModel.agent_id == agent_id)
            .order_by(AgentDocumentTemplateModel.document_name.asc())
            .all()
        )
        return [
            {
                "documentId": row.document_id,
                "documentName": row.document_name,
                "formatType": row.format_type,
                "fieldCount": len(fields_from_json(row.detected_fields)),
            }
            for row in rows
        ]

    def _build_system_prompt(
        self,
        agent: AgentModel,
        document_id: int | None,
        files_context: str = "",
        files_included: int = 0,
        student_hint: str = "",
        pending_rut: bool = False,
    ) -> str:
        templates = self._list_templates_summary(agent.id)
        templates_text = (
            json.dumps(templates, ensure_ascii=False, indent=2)
            if templates
            else "[]"
        )
        doc_hint = ""
        if document_id is not None:
            template = self._get_template(agent.id, document_id)
            if template:
                doc_hint = (
                    f"\n\nDocumento activo: {template.document_name} (id {document_id}), "
                    f"formato {template.format_type.upper()}.\n"
                    f"Campos de la plantilla:\n{build_fields_prompt(template)}"
                )
            else:
                doc_hint = (
                    f"\n\nDocumento solicitado (id {document_id}) sin plantilla configurada "
                    "para este agente."
                )

        file_count = storage.count_files(agent.name)
        files_block = ""
        if files_context:
            files_block = f"\n\n{files_context}\n"
        elif files_included == 0 and file_count > 0:
            files_block = (
                "\n\nNota: hay archivos en Files pero no se pudo extraer texto "
                "(formatos no soportados o vacíos). Formatos soportados: .txt, .md, "
                ".docx, .pdf, .json, .csv, .xls, .xlsx.\n"
            )

        role_text = sanitize_role_instructions_for_chat(agent.role_instructions)
        priority_directives = extract_priority_directives_from_prompt(agent.role_instructions)
        student_block = ""
        if student_hint:
            student_block = f"\n\n{student_hint}\n"
        elif pending_rut:
            student_block = (
                "\n\nEl estudiante aún no está identificado en PIE360. "
                "Debes pedir el RUT o IPE para ubicarlo en la plataforma antes de "
                "indicar que el documento Word fue generado.\n"
            )

        priority_block = ""
        if priority_directives:
            priority_block = f"\n\n{priority_directives}\n"

        return (
            f"Eres el agente «{agent.name}» de PIE360.\n\n"
            f"## Instrucciones del agente (configuradas por el usuario — prioridad en fuentes y redacción)\n"
            f"{role_text}\n\n"
            f"{CHAT_OUTPUT_OVERRIDE}\n"
            f"Archivos en Files del agente: {file_count} "
            f"({files_included} incluidos en este contexto).\n"
            f"{files_block}"
            f"{priority_block}"
            f"Plantillas de documentos configuradas:\n{templates_text}"
            f"{doc_hint}"
            f"{student_block}\n\n"
            "Responde en español. Las instrucciones del agente sobre archivos, fuentes y redacción "
            "tienen prioridad sobre la brevedad del chat. "
            "Usa ARCHIVOS DE CONTEXTO, DATOS EXTRAÍDOS DE EXCEL y la ficha del estudiante. "
            "No inventes datos que no estén en esas fuentes ni en el mensaje del usuario."
        )

    def _build_messages(
        self,
        agent: AgentModel,
        message: str,
        history: list[dict[str, str]] | None,
        document_id: int | None,
        files_context: str = "",
        files_included: int = 0,
        student_hint: str = "",
        pending_rut: bool = False,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self._build_system_prompt(
                    agent,
                    document_id,
                    files_context,
                    files_included,
                    student_hint,
                    pending_rut,
                ),
            },
        ]
        for item in history or []:
            role = item.get("role", "user")
            content = (item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message.strip()})
        return messages

    def _extract_replacements(
        self,
        agent: AgentModel,
        template: AgentDocumentTemplateModel,
        user_message: str,
        assistant_reply: str,
        files_context: str = "",
    ) -> dict[str, str]:
        fields = fields_from_json(template.detected_fields)
        if not fields:
            return {}

        files_section = f"\n\nArchivos de contexto (Files):\n{files_context}" if files_context else ""
        role_text = sanitize_role_instructions_for_chat(agent.role_instructions)
        priority_directives = extract_priority_directives_from_prompt(agent.role_instructions)
        prompt = (
            "Devuelve SOLO un objeto JSON donde cada clave es exactamente el nombre del campo "
            "y el valor es el texto a insertar en la plantilla.\n"
            f"Campos requeridos:\n{build_fields_prompt(template)}\n\n"
            f"## Instrucciones del agente (prioridad en fuentes y redacción)\n{role_text}\n\n"
        )
        if priority_directives:
            prompt += f"{priority_directives}\n\n"
        prompt += (
            f"{DOCUMENT_FIELD_EXTRACTION_GUIDE}\n"
            f"{files_section}\n\n"
            f"Mensaje del usuario:\n{user_message}\n\n"
            f"Respuesta del asistente (puede ser breve; no limites el Word a esto):\n{assistant_reply}\n\n"
            "Obedece las directrices del agente sobre archivos y fuentes. "
            "Prioriza archivos de contexto, Excel extraído y ficha PIE360. "
            "Expande los campos narrativos con redacción completa. "
            "Si no hay información para un campo, usa cadena vacía."
        )
        raw, usage = agents_openai.json_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres un redactor-extractor para formularios PIE360. "
                        "Rellenas cada campo del JSON con el texto final del informe, "
                        "desarrollado y listo para imprimir en Word."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        self._record_usage(
            agent_id=agent.id,
            request_kind="json_extract",
            usage=usage,
        )
        replacements: dict[str, str] = {}
        for field in fields:
            value = raw.get(field)
            if value is None:
                for key, val in raw.items():
                    if key.strip().lower() == field.strip().lower():
                        value = val
                        break
            replacements[field] = str(value) if value is not None else ""
        return replacements

    def stream_chat(
        self,
        agent_id: str,
        message: str,
        student_id: int | None = None,
        student_rut: str | None = None,
        document_id: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        if not openai_api_key_configured():
            yield _sse(
                {
                    "type": "error",
                    "message": "OPENAI_API_KEY is not configured on the backend.",
                }
            )
            return

        agent = self._get_agent(agent_id)
        if not agent:
            yield _sse({"type": "error", "message": "Agent not found."})
            return

        file_count = storage.count_files(agent.name)
        if file_count > 0:
            yield _sse({"type": "step", "message": "Reading Files…"})

        resolved_student_id, rut_used, student_issue = resolve_student_id(
            self.db,
            student_id=student_id,
            student_rut=student_rut,
            message=message,
            history=history,
        )

        rut_for_excel = rut_used
        if not rut_for_excel and resolved_student_id:
            personal = (
                self.db.query(StudentPersonalInfoModel)
                .filter(StudentPersonalInfoModel.student_id == resolved_student_id)
                .first()
            )
            if personal and (personal.identification_number or "").strip():
                rut_for_excel = (personal.identification_number or "").strip()

        files_context, files_included = build_agent_files_context(
            agent.name,
            student_rut=rut_for_excel,
        )

        resolved_document_id = document_id or infer_document_id(
            self.db, agent_id, message, history
        )
        should_generate = bool(
            resolved_document_id and wants_document_generation(message, history)
        )
        student_hint = ""
        pending_rut = False
        if resolved_student_id:
            student_hint = student_identification_hint(
                self.db,
                resolved_student_id,
                resolved_document_id,
            )
        elif should_generate and student_issue == "needs_rut":
            pending_rut = True

        yield _sse({"type": "step", "message": f"Consulting {settings.agents_model}…"})

        messages = self._build_messages(
            agent,
            message,
            history,
            resolved_document_id,
            files_context,
            files_included,
            student_hint,
            pending_rut,
        )
        full_reply = ""
        usage_out: list[OpenAIUsage] = []
        try:
            for delta in agents_openai.stream_chat_completion(messages, usage_out=usage_out):
                full_reply += delta
                yield _sse({"type": "text_delta", "delta": delta})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        if usage_out:
            self._record_usage(
                agent_id=agent_id,
                request_kind="chat",
                usage=usage_out[0],
            )

        response_files: list[dict[str, Any]] = []
        warning: str | None = None

        if should_generate and student_issue == "not_found":
            warning = (
                f"No student found with RUT/IPE {rut_used} on the platform. "
                "Check the value and try again."
            )
        elif should_generate and student_issue == "needs_rut":
            warning = None
        elif should_generate and not resolved_document_id:
            warning = (
                "Could not determine which document to generate. Configure templates in "
                "Agent Documents or specify the report type."
            )
        elif resolved_student_id and resolved_document_id and should_generate:
            template = self._get_template(agent_id, resolved_document_id)
            if not template:
                warning = (
                    f"No template configured for document {resolved_document_id}. "
                    "Configure it in Agent Documents."
                )
            else:
                yield _sse(
                    {
                        "type": "step",
                        "message": f"Generating {template.format_type.upper()}…",
                    }
                )
                try:
                    replacements = self._extract_replacements(
                        agent, template, message, full_reply, files_context
                    )
                    gen = generate_and_save_document(
                        self.db, template, resolved_student_id, replacements
                    )
                    if gen.get("status") == "error":
                        warning = gen.get("message", "Failed to generate the document.")
                    else:
                        yield _sse(
                            {
                                "type": "step",
                                "message": "Document ready to download.",
                            }
                        )
                        doc_label = gen.get("documentName") or "Generated file"
                        response_files.append(
                            {
                                "id": gen.get("filename", ""),
                                "name": gen.get("filename", ""),
                                "documentId": gen.get("documentId"),
                                "documentName": doc_label,
                                "downloadUrl": f"/files/system/students/{gen.get('filename', '')}",
                            }
                        )
                except Exception as exc:
                    warning = f"Could not generate the document: {exc}"

        yield _sse(
            {
                "type": "done",
                "data": {
                    "reply": full_reply,
                    "responseFiles": response_files,
                    "warning": warning,
                },
            }
        )
