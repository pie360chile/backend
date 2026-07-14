"""Agents chat via Workspace ChatGPT (trigger API)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.classes.workspace_agent_class import WorkspaceAgentClass


def _extract_workspace_reply(body: Any) -> str:
    """Intenta sacar el texto útil de distintas formas de respuesta del trigger."""
    if body is None:
        return ""
    if isinstance(body, str):
        return body.strip()
    if isinstance(body, list):
        parts = [_extract_workspace_reply(item) for item in body]
        return "\n".join(p for p in parts if p).strip()
    if not isinstance(body, dict):
        return str(body).strip()

    for key in (
        "output_text",
        "output",
        "text",
        "message",
        "content",
        "reply",
        "result",
        "response",
        "raw",
    ):
        if key not in body:
            continue
        value = body[key]
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (dict, list)):
            nested = _extract_workspace_reply(value)
            if nested:
                return nested

    # OpenAI-ish: choices[0].message.content
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"].strip()
            if isinstance(first.get("text"), str):
                return first["text"].strip()

    # data / output nested
    for key in ("data", "output"):
        if key in body:
            nested = _extract_workspace_reply(body[key])
            if nested:
                return nested

    try:
        dumped = json.dumps(body, ensure_ascii=False, indent=2)
    except Exception:
        dumped = str(body)
    return dumped.strip()


def _build_workspace_input(
    *,
    role_instructions: str,
    message: str,
    history: list[dict[str, str]] | None,
    student_id: int | None,
    student_rut: str | None,
    document_id: int | None,
) -> str:
    parts: list[str] = []
    instructions = (role_instructions or "").strip()
    if instructions:
        parts.append("Instrucciones del agente:\n" + instructions)

    hist_lines: list[str] = []
    for item in history or []:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            label = "Usuario" if role == "user" else "Asistente"
            hist_lines.append(f"{label}: {content}")
    if hist_lines:
        # Limitar historial para no inflar el input del Workspace Agent.
        clipped = hist_lines[-12:]
        parts.append("Historial reciente:\n" + "\n".join(clipped))

    extras: list[str] = []
    if student_id:
        extras.append(f"student_id={student_id}")
    if student_rut:
        extras.append(f"student_rut={student_rut}")
    if document_id:
        extras.append(f"document_id={document_id}")

    user_block = (message or "").strip()
    if extras:
        user_block = f"{user_block}\n\n[Contexto PIE360: {', '.join(extras)}]"
    parts.append("Mensaje actual del usuario:\n" + user_block)
    return "\n\n".join(parts).strip()


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

        model_code = "workspace-chatgpt"
        yield {"type": "step", "message": "Consultando Workspace ChatGPT…"}

        user_input = _build_workspace_input(
            role_instructions=agent_row.role_instructions or "",
            message=text,
            history=history,
            student_id=student_id,
            student_rut=student_rut,
            document_id=document_id,
        )

        result = WorkspaceAgentClass(self.db).trigger_chat(user_input)
        if result.get("status") == "error":
            yield {
                "type": "error",
                "message": result.get("message") or "Error al consultar Workspace ChatGPT.",
                "code": "workspace_agent_error",
            }
            return

        body = (result.get("data") or {}).get("body")
        reply_text = _extract_workspace_reply(body)
        if not reply_text:
            reply_text = "El Workspace Agent respondió sin texto útil."

        # El trigger no es streaming: un solo bloque compatible con la UI SSE.
        yield {"type": "text_delta", "delta": reply_text}
        yield {"type": "done", "data": {"reply": reply_text}}

        if not self.customer_id:
            return

        try:
            AgentsUsageClass(self.db).record_chat(
                customer_id=int(self.customer_id),
                school_id=int(self.school_id) if self.school_id else None,
                user_id=int(self.user_id) if self.user_id else None,
                agent_id=agent_id,
                model=model_code,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                input_text=text,
                output_text=reply_text,
            )
        except Exception:
            self.db.rollback()
