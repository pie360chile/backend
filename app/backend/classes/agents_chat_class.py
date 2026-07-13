"""Agents chat stub: OpenAI LLM integration removed."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

_DISABLED_MESSAGE = (
    "La generación con IA está desactivada. "
    "El módulo Agentes ya no usa OpenAI para chat ni para rellenar informes."
)


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
        yield {
            "type": "error",
            "message": _DISABLED_MESSAGE,
            "code": "llm_disabled",
        }
