"""Agents chat via proveedor LLM (modelo global de Configuraciones)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.utils import agents_llm_client


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

        model_code = AgentsLlmModelsClass(self.db).get_selected_model_code()
        yield {"type": "step", "message": "Consultando al agente…"}

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (agent_row.role_instructions or "").strip()
                or "Eres un asistente útil para el sistema PIE 360.",
            }
        ]
        for item in history or []:
            role = (item.get("role") or "").strip()
            content = (item.get("content") or "").strip()
            if role in {"user", "assistant", "system"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})

        extras: list[str] = []
        if student_id:
            extras.append(f"student_id={student_id}")
        if student_rut:
            extras.append(f"student_rut={student_rut}")
        if document_id:
            extras.append(f"document_id={document_id}")
        if extras:
            messages[-1]["content"] = f"{text}\n\n[Contexto PIE360: {', '.join(extras)}]"

        reply_text = ""
        usage: dict[str, Any] | None = None
        had_error = False
        for event in agents_llm_client.stream_chat_completion(
            messages, model=model_code, db=self.db
        ):
            if event.get("type") == "done":
                data = event.get("data") or {}
                reply_text = str(data.get("reply") or "")
                usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
            elif event.get("type") == "error":
                had_error = True
            yield event

        if had_error or not self.customer_id:
            return

        prompt_tokens = int((usage or {}).get("prompt_tokens") or 0)
        completion_tokens = int((usage or {}).get("completion_tokens") or 0)
        total_tokens = int((usage or {}).get("total_tokens") or (prompt_tokens + completion_tokens))
        try:
            AgentsUsageClass(self.db).record_chat(
                customer_id=int(self.customer_id),
                school_id=int(self.school_id) if self.school_id else None,
                user_id=int(self.user_id) if self.user_id else None,
                agent_id=agent_id,
                model=model_code,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                input_text=text,
                output_text=reply_text,
            )
        except Exception:
            # No romper el chat si falla la telemetría.
            self.db.rollback()
