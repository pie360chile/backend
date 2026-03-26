"""
Evaluator chat: senior evaluator persona (Chile, NEE/PIE) using `knowledge_documents` as context.
Documented for OpenAPI / Swagger (`/docs`).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import List

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.db.models import AIConversationModel, KnowledgeDocumentModel
from app.backend.schemas import UserLogin

MAX_RESPONSE_CHARS = 1450
MAX_KNOWLEDGE_CONTEXT_CHARS = 120_000
MAX_USER_MESSAGE_CHARS = 48_000
# OpenAI API id for GPT-5 mini (override with EVALUATOR_CHAT_MODEL / NEE_EVALUATOR_MODEL).
EVALUATOR_CHAT_DEFAULT_MODEL = "gpt-5-mini"

evaluator_chat = APIRouter(
    prefix="/chat",
    tags=["Evaluator chat"],
)


class EvaluatorChatRequest(BaseModel):
    """Request body for evaluator chat (appears in OpenAPI schema)."""

    question: str = Field(
        ...,
        min_length=1,
        description=(
            "Instrucción o tarea (p. ej. apartado del informe a redactar, pregunta técnica). "
            "Se analiza junto con `user_context` y la base de conocimiento."
        ),
        json_schema_extra={
            "example": "Redacta el apartado «IV … — a) Habilidades cognitivas…» para un informe psicopedagógico."
        },
    )
    user_context: str = Field(
        ...,
        min_length=1,
        description=(
            "Texto libre que escribe el usuario: antecedentes, notas de evaluación, observaciones, etc. "
            "El modelo debe integrar todo el contexto relevante con la instrucción y los knowledge_documents."
        ),
        json_schema_extra={"example": "Estudiante con TEL; observaciones de aula: participa con apoyo visual…"},
    )


def _load_knowledge_context(db: Session) -> str:
    rows: List[KnowledgeDocumentModel] = (
        db.query(KnowledgeDocumentModel)
        .filter(KnowledgeDocumentModel.is_active == True)  # noqa: E712
        .order_by(KnowledgeDocumentModel.id.asc())
        .all()
    )
    parts: List[str] = []
    for r in rows:
        title = (r.title or "").strip() or f"Documento {r.id}"
        body = (r.content or "").strip()
        if not body:
            continue
        meta = []
        if r.document_type:
            meta.append(f"type: {r.document_type}")
        if r.category:
            meta.append(f"category: {r.category}")
        head = f"## {title}"
        if meta:
            head += f" ({', '.join(meta)})"
        parts.append(f"{head}\n{body}")
    joined = "\n\n---\n\n".join(parts)
    if len(joined) > MAX_KNOWLEDGE_CONTEXT_CHARS:
        joined = joined[: MAX_KNOWLEDGE_CONTEXT_CHARS] + "\n\n[... context truncated ...]"
    return joined


def _try_import_openai():
    """Import at call time so the same interpreter as the request handles missing installs."""
    try:
        import openai

        return openai, None
    except ImportError as e:
        return None, str(e)


def _build_model_user_input(question: str, user_context: str) -> str:
    """Arma el mensaje de usuario para el modelo: tarea + contexto escrito, separados y claros."""
    q = (question or "").strip()
    ctx = (user_context or "").strip()
    block = (
        "### Instrucción / tarea\n"
        f"{q}\n\n"
        "### Contexto aportado por el usuario\n"
        f"{ctx}"
    )
    if len(block) > MAX_USER_MESSAGE_CHARS:
        block = block[: MAX_USER_MESSAGE_CHARS - 40] + "\n\n[... mensaje truncado por límite ...]"
    return block


def _build_system_instruction(knowledge_block: str) -> str:
    kb = knowledge_block.strip() or "(No hay documentos activos en knowledge_documents; responde con criterio profesional general sobre NEE/PIE en Chile, sin inventar normas específicas.)"
    return f"""You are a senior educational evaluator in Chile. Your expertise is special educational needs (NEE), inclusive education, PIE (Plan Individual de Apoyo), curricular adjustments, and evaluation aligned with Chilean school reality.

Respond in clear Spanish. Be precise, supportive, and professional—like an experienced evaluator who supports teams working with NEE students.

Ground your answer in the KNOWLEDGE BASE below when it is relevant. If the knowledge base does not cover the question, answer with sound professional judgment and explicitly avoid fabricating laws, decrees, or institutional details.

KNOWLEDGE BASE (from knowledge_documents):
{kb}

The user message has two labeled parts: INSTRUCTION/TASK and USER-WRITTEN CONTEXT. Synthesize both with the knowledge base: use the context as factual or clinical input when relevant; do not ignore substantive details the user provides. If the context conflicts with the knowledge base, prefer cautious professional wording and do not invent norms.

When USER-WRITTEN CONTEXT is tabular, pasted from spreadsheets, or lists per-item statuses (e.g. LOGRADO, EN PROCESO, REQUIERE APOYO), treat every row and column as data to respect—not filler. Name the specialist role, discipline, date(s), student/course identifiers, and the concrete status per area or item when that information appears. If the user pasted more than one evaluation or row (different dates or professionals), explicitly contrast how they differ; do not reuse the same generic paragraph you would use for another row. If two inputs differ only in subtle ways, still point out at least two specific divergences (e.g. domains or items that changed status).

Status labels are NOT interchangeable. Map each item only to the status shown in that column/cell:
- LOGRADO: competence observed as consolidated in context; you may use clear positive wording aligned with achievement.
- EN PROCESO: still developing; describe as emerging, partial, or inconsistent, with support or practice still needed—never as fully achieved.
- REQUIERE APOYO: not consolidated; stress need for explicit support, mediation, or adjustments; do not rewrite as success or "logra" / "demuestra de forma adecuada" for that same item.
Do not narrate the checklist as if every line were LOGRADO. For each indicator that appears with a status, your wording must match LOGRADO vs EN PROCESO vs REQUIERE APOYO. Cover strengths and gaps: do not only list problems and skip LOGRADO items, and do not only praise while hiding REQUIERE APOYO or EN PROCESO. If the same student name appears in context, use it and keep grammatical agreement in Spanish.

Comprehensive coverage: Read the entire USER-WRITTEN CONTEXT. The answer is strictly short ({MAX_RESPONSE_CHARS} characters max), so you cannot quote every indicator; still, do not fixate on one domain while ignoring others—at least briefly address each major domain or evaluation row present (cognitive-communicative, socioemotional, motor/sensory/autonomy, etc.), summarizing the real mix of LOGRADO / EN PROCESO / REQUIERE APOYO. Prefer dense, specific wording over generic filler.

Every student is different: build the answer only from what this context shows for this learner (name, course, dates, specialist, pattern of statuses). Never recycle a template paragraph suitable for "any student." If two or more students appear, keep them clearly separated (by name) with distinct characterizations; do not merge them into one profile.

Hard rules:
- Maximum length of your answer: {MAX_RESPONSE_CHARS} characters (including spaces). Do not exceed this limit.
- Do not cite internal system labels; write for teachers and coordinators.
- Never equate EN PROCESO or REQUIERE APOYO with LOGRADO in the narrative for the same indicator.
- With the short length cap, synthesize across the whole context the user sent: no omitting entire domains or whole evaluation rows unless INSTRUCTION/TASK narrows scope.
"""


@evaluator_chat.post(
    "/evaluator",
    summary="Chat evaluador (knowledge_documents + OpenAI)",
    description=(
        "Recibe `question` (instrucción/tarea) y `user_context` (texto libre del usuario). "
        "Se prioriza síntesis detallada y personalizada por estudiante, usando los datos aportados. "
        "Ambos se envían al modelo junto con el contenido activo de `knowledge_documents`. "
        "La respuesta se limita a 1450 caracteres. Requiere `OPENAI_API_KEY`. "
        "Modelo: `EVALUATOR_CHAT_MODEL`, o `NEE_EVALUATOR_MODEL`, o por defecto GPT-5 mini (`gpt-5-mini`). "
        "La interacción se guarda en `ai_conversations`."
    ),
)
def evaluator_chat_message(
    body: EvaluatorChatRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    openai_mod, openai_import_error = _try_import_openai()
    if openai_mod is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": (
                    "Python package 'openai' is not available in this environment. "
                    "Install with the same interpreter as the app: "
                    "pip install 'openai>=2.0.0' or pip install -r requirements.txt "
                    "(on Linux/systemd: activate the project venv first, then restart gunicorn/uvicorn)."
                ),
                "data": {"import_error": openai_import_error} if openai_import_error else None,
            },
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": "OPENAI_API_KEY not configured",
                "data": None,
            },
        )

    question = (body.question or "").strip()
    user_context = (body.user_context or "").strip()
    if not question:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"status": 422, "message": "question is required", "data": None},
        )
    if not user_context:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"status": 422, "message": "user_context is required", "data": None},
        )

    model_input = _build_model_user_input(question, user_context)
    knowledge_block = _load_knowledge_context(db)
    instructions = _build_system_instruction(knowledge_block)

    client = openai_mod.OpenAI(api_key=api_key)
    model_name = os.getenv(
        "EVALUATOR_CHAT_MODEL",
        os.getenv("NEE_EVALUATOR_MODEL", EVALUATOR_CHAT_DEFAULT_MODEL),
    )

    try:
        response = client.responses.create(
            model=model_name,
            input=model_input,
            instructions=instructions,
        )
        raw = (response.output_text or "").strip()
    except Exception as e:
        err = str(e)
        hint = None
        if "429" in err or "rate_limit" in err.lower() or "too large" in err.lower():
            hint = (
                "Límite de tokens (TPM) o contexto demasiado grande. "
                "Acorta `user_context`, desactiva knowledge_documents que no necesites, o aumenta límites en https://platform.openai.com/account/rate-limits"
            )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": f"OpenAI error: {err}",
                "data": {"hint": hint} if hint else None,
            },
        )

    if len(raw) > MAX_RESPONSE_CHARS:
        raw = raw[: MAX_RESPONSE_CHARS - 1].rstrip() + "…"

    uid = getattr(session_user, "id", None) or getattr(session_user, "user_id", None) or 1
    sid = str(uuid.uuid4())
    tokens_used = None
    if hasattr(response, "usage") and response.usage:
        tokens_used = getattr(response.usage, "total_tokens", None)

    try:
        stored_input = f"[question]\n{question}\n\n[user_context]\n{user_context}"
        if len(stored_input) > 65000:
            stored_input = stored_input[:64900] + "\n\n[... truncado ...]"
        row = AIConversationModel(
            user_id=int(uid) if uid is not None else 1,
            session_id=sid,
            previous_response_id=getattr(response, "id", None),
            input_text=stored_input,
            instruction="evaluator_chat",
            response_text=raw,
            model=model_name,
            tokens_used=tokens_used,
            added_date=datetime.now(),
            updated_date=datetime.now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        conv_id = row.id
    except Exception:
        db.rollback()
        conv_id = None

    payload = {
        "status": 200,
        "message": "OK",
        "data": {
            "response": raw,
            "response_length": len(raw),
            "max_length": MAX_RESPONSE_CHARS,
            "knowledge_documents_used": bool(knowledge_block.strip()),
            "conversation_id": conv_id,
            "model": model_name,
            "question_length": len(question),
            "user_context_length": len(user_context),
        },
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
