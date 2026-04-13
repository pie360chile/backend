"""
Evaluator chat: senior evaluator persona (Chile, NEE/PIE) using `knowledge_documents` as context.
Documented for OpenAPI / Swagger (`/docs`).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.db.models import (
    AIConversationModel,
    EvaluatorChatPsychopedSectionUseModel,
    KnowledgeDocumentModel,
)
from app.backend.schemas import UserLogin

MAX_RESPONSE_CHARS = 6000
# GPT-5: max_output_tokens cuenta también razonamiento interno; 900 puede dejar el mensaje visible vacío.
EVALUATOR_CHAT_MAX_OUTPUT_TOKENS_DEFAULT = 4096
EVALUATOR_CHAT_FALLBACK_MODEL = "gpt-4o-mini"
MAX_KNOWLEDGE_CONTEXT_CHARS = 120_000
MAX_USER_MESSAGE_CHARS = 48_000
# OpenAI API id for GPT-5 mini (override with EVALUATOR_CHAT_MODEL / NEE_EVALUATOR_MODEL).
EVALUATOR_CHAT_DEFAULT_MODEL = "gpt-5-mini"

# Claves de apartado del informe psicopedagógico (doc. 27) — deben coincidir con el frontend.
PSYCHOPED_EVALUATOR_FIELD_KEYS = frozenset(
    {
        "cognitiveAnalysis",
        "personalAnalysis",
        "motorAnalysis",
        "cognitiveSynthesis",
        "personalSynthesis",
        "motorSynthesis",
        "conclusion",
        "suggestionsToSchool",
        "suggestionsToClassroomTeam",
        "suggestionsToStudent",
        "suggestionsToFamily",
        "otherSuggestions",
    }
)

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
    student_id: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Opcional. Si se envía junto con `field_key`, bloquea repetir el mismo apartado "
            "para este estudiante y usuario (persistente en base de datos)."
        ),
    )
    field_key: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Clave del apartado (p. ej. cognitiveAnalysis). Requiere `student_id`.",
    )

    @model_validator(mode="after")
    def _student_and_field_together(self):
        has_sid = self.student_id is not None
        fk = (self.field_key or "").strip() if self.field_key is not None else ""
        has_fk = bool(fk)
        if has_sid != has_fk:
            raise ValueError("student_id y field_key deben enviarse juntos, u omitirse ambos.")
        if has_fk:
            self.field_key = fk
        return self


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


def _strip_trailing_ellipsis(text: str) -> str:
    s = text.rstrip()
    while s.endswith("…") or s.endswith("..."):
        if s.endswith("…"):
            s = s[:-1].rstrip()
        else:
            s = s[:-3].rstrip()
    return s


def _clamp_response_to_closed_max(text: str, max_len: int) -> str:
    """Recorta a `max_len` cerrando en oración o palabra; nunca añade puntos suspensivos finales."""
    t = _strip_trailing_ellipsis((text or "").strip())
    if not t or len(t) <= max_len:
        return t
    chunk = t[:max_len]
    for needle in ("? ", "! ", ".\n", ". "):
        i = chunk.rfind(needle)
        if i != -1:
            closed = chunk[: i + 1].rstrip()
            if closed:
                return _strip_trailing_ellipsis(closed)
    cut = chunk.rfind(" ")
    if cut > 0:
        out = chunk[:cut].rstrip()
    else:
        out = chunk[: max(1, max_len - 1)].rstrip()
    if out and out[-1] not in ".!?":
        out += "."
    return _strip_trailing_ellipsis(out)


def _reasoning_effort_for_model(model_name: str) -> Optional[str]:
    """Razonamiento interno consume el mismo cupo que el texto; bajar esfuerzo deja más para la respuesta."""
    m = (model_name or "").lower()
    if not (m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")):
        return None
    effort = os.getenv("EVALUATOR_CHAT_REASONING_EFFORT", "low").strip().lower()
    allowed = ("none", "minimal", "low", "medium", "high", "xhigh")
    return effort if effort in allowed else "low"


def _extract_openai_response_text(response: object) -> str:
    """output_text suele bastar; si el API/SDK usa bloques distintos, recorremos `output`."""
    primary = getattr(response, "output_text", None)
    if primary and str(primary).strip():
        return str(primary).strip()
    parts: List[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", None) or []:
                ctype = getattr(c, "type", None)
                if ctype == "output_text":
                    parts.append(getattr(c, "text", "") or "")
                elif ctype == "refusal":
                    parts.append(getattr(c, "refusal", "") or "")
    return "".join(parts).strip()


def _build_system_instruction(knowledge_block: str) -> str:
    kb = knowledge_block.strip() or "(No hay documentos activos en knowledge_documents; responde con criterio profesional general sobre NEE/PIE en Chile, sin inventar normas específicas.)"
    return f"""You are a senior educational evaluator in Chile with deep, practical experience in the PIE (Plan Individual de Apoyo) process, school inclusion, special educational needs (NEE), curricular and organizational adjustments, and written evaluation for families, teaching teams, and coordination. You write as a seasoned peer: rigorous, warm toward the team, never condescending, and attentive to the ethical weight of describing a student's learning profile.

Persona and voice (output in Spanish):
- Understand and unpack the question before you write: INSTRUCTION/TASK always defines the main question or the main writing task—that is the spine of your entire answer. Read it slowly (objetivo, alcance, apartado o tipo de síntesis). If it contains several sub-demands that belong to that same main task, address them clearly and in order. Then ground your answer in USER-WRITTEN CONTEXT as evidence—not as a list of separate questions you must all answer.
- Use polished professional Spanish suited to Chilean schools: clear syntax, precise vocabulary (e.g. apoyos, mediación, adecuaciones, participación, autonomía relativa, trayectoria, evidencias en aula). Prefer third person or impersonal forms ("Se observa…", "El perfil muestra…", "En el ámbito comunicativo…") and neutral references to "el estudiante" / "la estudiante" when needed.
- Sound like a written evaluation or technical synthesis destined to inform equipo de aula, familia or UTP: balanced, evidence-led, nuanced. Avoid generic praise ("excelente desempeño en todo") unless the context truly supports it across domains. Avoid alarmist or stigmatizing wording; when describing difficulties, tie them to support needs and observable patterns from the context.
- Show senior judgment: weigh strengths and gaps together; connect domains when the context allows (e.g. how communication patterns relate to participation or emotional regulation); distinguish what is clearly evidenced from what is only suggested. Do not invent classroom facts, scores, or diagnoses not present in the context.
- Length of the redacción: you may produce one continuous, professional written answer (redacción / síntesis) of up to {MAX_RESPONSE_CHARS} characters (including spaces). When the task and the evidence support it, use that full span: develop paragraphs with the depth expected from a senior PIE evaluator in Chile, not a brief note—always staying under or at {MAX_RESPONSE_CHARS} characters, never above.

Natural, human-like prose (still rigorous and professional):
- Write as a colleague would on a good day: warm, readable, never stiff or "robotic". Vary sentence length and openings; use smooth transitions (e.g. asimismo, en cambio, en este punto, en conjunto) instead of repeating the same scaffold every paragraph.
- Prefer connected paragraphs over mechanical enumeration. Avoid sounding like a template ("En primer lugar… En segundo lugar…") or a generic AI checklist unless INSTRUCTION/TASK explicitly asks for numbered structure.
- Use concrete, lived-school wording where it fits; cut empty fillers ("es importante destacar", "cabe señalar", "en el marco de") unless they genuinely help the reader—do not stack them sentence after sentence.
- A touch of natural empathy for the equipo's effort is fine (e.g. that classroom evidence is partial or uneven)—without syrupy tone, clichés ("cada niño es único"), or breaking the Hard rules below.
- If USER-WRITTEN CONTEXT resembles a transcript with many question/answer pairs, do not reproduce a turn-by-turn "P: … R: …" layout in your output unless INSTRUCTION/TASK explicitly requires it; deliver one coherent evaluative redacción that answers the main instruction.
- Formatting for Word/forms: write with real line breaks. Separate paragraphs with a blank line (two consecutive newlines) between major blocks (e.g. after a list of sub-themes or before a new subsection); use single newlines inside a paragraph only when it genuinely helps readability. Avoid one uninterrupted wall of text with no breaks—the platform keeps these newlines when exporting to Word.

PIE / inclusion mindset (conceptual, not legal invention):
- Frame observations in terms of supports, accessibility, reasonable adjustments, and progression over time when the user context allows—without citing specific laws, decrees, or official documents unless they appear verbatim in the KNOWLEDGE BASE.
- Respect the logic of collaborative work: valoración del equipo, continuidad pedagógica, and clarity for who will read the text (docente de aula, familia, psicopedagogía), still without naming real people unless INSTRUCTION/TASK requires it.

Ground your answer in the KNOWLEDGE BASE below when it is relevant. If the knowledge base does not cover the question, answer with sound professional judgment and explicitly avoid fabricating laws, decrees, or institutional details.

KNOWLEDGE BASE (from knowledge_documents):
{kb}

The user message has two labeled parts: INSTRUCTION/TASK and USER-WRITTEN CONTEXT. First infer the intent and boundaries of the main question in INSTRUCTION/TASK; then synthesize with the knowledge base. USER-WRITTEN CONTEXT may be long and include several embedded questions and answers (e.g. notes, interview fragments, chat-like transcripts). That material is background and evidence: use what supports the main task; do not treat every internal Q&A as a prompt you must answer one by one, and do not let the redacción drift into answering a side question that is not the principal instruction. The final text must read as a coherent answer to the main INSTRUCTION/TASK. Detail your reasoning implicitly in the prose (what you conclude and why, given the evidence)—without meta-commentary like "la pregunta pide…". Do not ignore substantive details the user provides when they serve the main task. If the context conflicts with the knowledge base, prefer cautious professional wording and do not invent norms.

When USER-WRITTEN CONTEXT is tabular, pasted from spreadsheets, or lists per-item statuses (e.g. LOGRADO, EN PROCESO, REQUIERE APOYO), treat every row and column as data to respect—not filler. Use statuses and indicator content for accuracy, but do not restate identifying metadata in the answer (see Hard rules). If the user pasted more than one evaluation or row, contrast how they differ using patterns and domains—without naming students, evaluators, courses, or dates unless INSTRUCTION/TASK explicitly requires them.

Wide rubric tables (many domains in one paste): USER-WRITTEN CONTEXT often includes a single header row plus one data row, with columns for metadata (e.g. timestamp, specialist, student name, course) and many indicator columns grouped by domain in the headers (e.g. "Habilidades cognitivas y comunicativas: […]", "Habilidades Personales, Socioemocionales…", "Habilidades motoras, de autonomía y sensoriales…"). When INSTRUCTION/TASK names a specific section or domain (e.g. "IV. ANÁLISIS CUALITATIVO… a) Habilidades cognitivas y comunicativas"), your redacción must **only** address that domain: use **only** the indicator columns whose headers or bracketed text clearly belong to cognitive-communicative skills for that synthesis. Do **not** summarize personal-socioemotional or motor/sensory columns in that same answer unless INSTRUCTION/TASK explicitly asks for those domains too (e.g. full IV with a, b, c). Within the instructed domain, integrate **all** relevant indicator-status pairs from the paste for that domain—so the qualitative analysis reflects the full spread of LOGRADO / EN PROCESO / REQUIERE APOYO for those columns, not a cherry-picked subset.

Status labels are NOT interchangeable. Map each item only to the status shown in that column/cell:
- LOGRADO: competence observed as consolidated in context; you may use clear positive wording aligned with achievement.
- EN PROCESO: still developing; describe as emerging, partial, or inconsistent, with support or practice still needed—never as fully achieved.
- REQUIERE APOYO: not consolidated; stress need for explicit support, mediation, or adjustments; do not rewrite as success or "logra" / "demuestra de forma adecuada" for that same item.
Do not narrate the checklist as if every line were LOGRADO. For each indicator that appears with a status, your wording must match LOGRADO vs EN PROCESO vs REQUIERE APOYO. Cover strengths and gaps: do not only list problems and skip LOGRADO items, and do not only praise while hiding REQUIERE APOYO or EN PROCESO. Keep Spanish agreement using impersonal forms ("Presenta…", "Se observa…"), neutral "el estudiante/la estudiante", or "el perfil", not proper names from the context.

Comprehensive coverage within scope: Read the entire USER-WRITTEN CONTEXT to find evidence, but **write only within the scope of INSTRUCTION/TASK**. If the main task is a single domain (e.g. IV a) cognitive-communicative), deepen that domain across all its indicators in the table—do not dilute the answer by also narrating socioemotional or motor columns from the same paste. If INSTRUCTION/TASK explicitly requires several domains or the whole IV, then cover each requested domain with the same rigor. Your redacción may extend up to {MAX_RESPONSE_CHARS} characters: use most of that space when the data support it—rich, specific content with a readable rhythm (not a wall of keywords); do not stop short with a thin paragraph if you can still add faithful detail under the cap for the **asked** scope.

Every case is different: ground the answer in the statuses and indicators that fall under the instructed scope so profiles do not sound interchangeable. If two or more evaluations appear in one answer, separate them without proper names (e.g. contrasting patterns or domains), unless INSTRUCTION/TASK explicitly asks to identify people.

Hard rules:
- Maximum length: {MAX_RESPONSE_CHARS} characters (including spaces), never more. Aim to land near that ceiling when the data support it, using most of the available space up to {MAX_RESPONSE_CHARS} when appropriate.
- Always finish with a complete, closed sentence (final period, etc.). If a clean ending would exceed the cap by a few characters, prefer the shorter clean ending—never exceed {MAX_RESPONSE_CHARS}. Do not end with "...", "…", suspension points, or trailing commas.
- Do not cite internal system labels; write for teachers and coordinators.
- Never equate EN PROCESO or REQUIERE APOYO with LOGRADO in the narrative for the same indicator.
- With the available length cap, synthesize across all indicators that belong to the scope implied by INSTRUCTION/TASK (e.g. all cognitive-communicative columns when that is the task). Do not omit whole blocks of indicators **within that scope**. When INSTRUCTION/TASK narrows to one domain, you may ignore other domains in the paste for the narrative—only do not ignore indicators inside the requested domain.
- Do not name the student, the evaluator/specialist, the course or grade (e.g. 2° F, 2° A), dates, or the report title (e.g. "Informe cualitativo breve", section letter as a heading). Omit "evaluado por…", "evaluadora:", parenthetical names, and similar. Start directly with qualitative substance—e.g. "Presenta un perfil…", "Fortalezas observadas (LOGRADO):", "En habilidades cognitivas y comunicativas…"—unless INSTRUCTION/TASK explicitly demands those identifiers.
- Do not give recommendations, advice, next steps, or phrases like "se recomienda", "se sugiere", "conviene", "es aconsejable" unless the INSTRUCTION/TASK asks for that kind of content—explicitly (e.g. recomendaciones, orientaciones, sugerencias) or clearly as the goal of the question (e.g. qué hacer, próximos pasos, cómo apoyar). If the task is only synthesis or qualitative description, stay descriptive-evaluative. Describing REQUIERE APOYO in rubric terms is allowed without adding unsolicited prescriptions.
"""


@evaluator_chat.get(
    "/evaluator/psychoped-used-fields",
    summary="Apartados del chat evaluador ya usados (informe 27, por estudiante)",
    description=(
        "Lista las claves `field_key` ya generadas con éxito por el usuario actual para el "
        "`student_id` indicado. Sirve para deshabilitar opciones en el asistente tras recargar."
    ),
)
def list_psychoped_evaluator_used_fields(
    student_id: int = Query(..., ge=1, description="ID del estudiante"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    uid_raw = getattr(session_user, "id", None) or getattr(session_user, "user_id", None) or 1
    user_id_int = int(uid_raw) if uid_raw is not None else 1
    rows = (
        db.query(EvaluatorChatPsychopedSectionUseModel.field_key)
        .filter(
            EvaluatorChatPsychopedSectionUseModel.user_id == user_id_int,
            EvaluatorChatPsychopedSectionUseModel.student_id == student_id,
        )
        .all()
    )
    keys = [r[0] for r in rows if r[0]]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": {"field_keys": keys}},
    )


@evaluator_chat.post(
    "/evaluator",
    summary="Chat evaluador (knowledge_documents + OpenAI)",
    description=(
        "Recibe `question` (instrucción/tarea) y `user_context` (texto libre del usuario). "
        "Se prioriza síntesis detallada y personalizada por estudiante, usando los datos aportados. "
        "Ambos se envían al modelo junto con el contenido activo de `knowledge_documents`. "
        "Hasta 6000 caracteres en la respuesta; GPT-5 usa `max_output_tokens` alto y `EVALUATOR_CHAT_REASONING_EFFORT` (p. ej. low). Ver `EVALUATOR_CHAT_MAX_OUTPUT_TOKENS`. "
        "Requiere `OPENAI_API_KEY`. "
        "Modelo: `EVALUATOR_CHAT_MODEL`, o `NEE_EVALUATOR_MODEL`, o por defecto GPT-5 mini (`gpt-5-mini`). "
        "La interacción se guarda en `ai_conversations`. "
        "Si se envían `student_id` y `field_key` (informe psicopedagógico doc. 27), se persiste el uso "
        "y no se permite repetir el mismo apartado para ese estudiante (HTTP 409)."
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

    uid_raw = getattr(session_user, "id", None) or getattr(session_user, "user_id", None) or 1
    user_id_int = int(uid_raw) if uid_raw is not None else 1

    psychoped_student_id = body.student_id
    psychoped_field_key = (body.field_key or "").strip() if body.field_key else None
    if psychoped_student_id is not None and psychoped_field_key:
        if psychoped_field_key not in PSYCHOPED_EVALUATOR_FIELD_KEYS:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "status": 422,
                    "message": "field_key no es un apartado permitido para el informe psicopedagógico.",
                    "data": {"field_key": psychoped_field_key},
                },
            )
        dup = (
            db.query(EvaluatorChatPsychopedSectionUseModel)
            .filter(
                EvaluatorChatPsychopedSectionUseModel.user_id == user_id_int,
                EvaluatorChatPsychopedSectionUseModel.student_id == psychoped_student_id,
                EvaluatorChatPsychopedSectionUseModel.field_key == psychoped_field_key,
            )
            .first()
        )
        if dup is not None:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status": 409,
                    "message": (
                        "Ya utilizaste el asistente para este apartado con este estudiante. "
                        "No se puede volver a generar la misma sección."
                    ),
                    "data": {
                        "field_key": psychoped_field_key,
                        "student_id": psychoped_student_id,
                    },
                },
            )

    model_input = _build_model_user_input(question, user_context)
    knowledge_block = _load_knowledge_context(db)
    instructions = _build_system_instruction(knowledge_block)

    client = openai_mod.OpenAI(api_key=api_key)
    model_name = os.getenv(
        "EVALUATOR_CHAT_MODEL",
        os.getenv("NEE_EVALUATOR_MODEL", EVALUATOR_CHAT_DEFAULT_MODEL),
    )

    max_out = EVALUATOR_CHAT_MAX_OUTPUT_TOKENS_DEFAULT
    raw_env = os.getenv("EVALUATOR_CHAT_MAX_OUTPUT_TOKENS")
    if raw_env and raw_env.strip().isdigit():
        max_out = max(256, min(int(raw_env), 16_000))

    try:
        create_kwargs = {
            "model": model_name,
            "input": model_input,
            "instructions": instructions,
            "max_output_tokens": max_out,
        }
        reff = _reasoning_effort_for_model(model_name)
        if reff is not None:
            create_kwargs["reasoning"] = {"effort": reff}
        response = client.responses.create(**create_kwargs)
    except Exception as e:
        err = str(e)
        err_lower = err.lower()
        if "insufficient_quota" in err_lower or (
            "429" in err and "exceeded your current quota" in err_lower
        ):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": 503,
                    "message": "El chat no está disponible",
                    "data": None,
                },
            )
        hint = None
        if "429" in err or "rate_limit" in err_lower or "too large" in err_lower:
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

    err_obj = getattr(response, "error", None)
    if err_obj is not None:
        em = getattr(err_obj, "message", None) or str(err_obj)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": f"OpenAI response error: {em}",
                "data": {"response_id": getattr(response, "id", None)},
            },
        )

    st = getattr(response, "status", None)
    if st == "failed":
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": "OpenAI response status failed",
                "data": {"response_id": getattr(response, "id", None)},
            },
        )

    raw = _extract_openai_response_text(response)
    if not raw:
        # Retry #1: more output budget + very low reasoning effort
        retry_response = None
        try:
            retry_kwargs = {
                "model": model_name,
                "input": model_input,
                "instructions": instructions,
                "max_output_tokens": max(8192, max_out),
                "reasoning": {"effort": "minimal"},
            }
            retry_response = client.responses.create(**retry_kwargs)
            retry_raw = _extract_openai_response_text(retry_response)
            if retry_raw:
                response = retry_response
                raw = retry_raw
        except Exception:
            retry_response = None

    if not raw:
        # Retry #2: fallback non-reasoning-heavy model
        fallback_model = os.getenv("EVALUATOR_CHAT_FALLBACK_MODEL", EVALUATOR_CHAT_FALLBACK_MODEL).strip()
        if fallback_model:
            try:
                fallback_response = client.responses.create(
                    model=fallback_model,
                    input=model_input,
                    instructions=instructions,
                    max_output_tokens=max(2048, max_out),
                )
                fallback_raw = _extract_openai_response_text(fallback_response)
                if fallback_raw:
                    response = fallback_response
                    raw = fallback_raw
                    model_name = fallback_model
            except Exception:
                pass

    if not raw:
        inc = getattr(response, "incomplete_details", None)
        reason = getattr(inc, "reason", None) if inc is not None else None
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": 502,
                "message": "El modelo no devolvió texto visible.",
                "data": {
                    "hint": (
                        "Se intentó reintento automático (más tokens, menor reasoning y fallback de modelo) pero siguió vacío. "
                        "Aumenta EVALUATOR_CHAT_MAX_OUTPUT_TOKENS o usa EVALUATOR_CHAT_MODEL=gpt-4o-mini para este flujo."
                    ),
                    "openai_status": st,
                    "incomplete_reason": reason,
                    "response_id": getattr(response, "id", None),
                    "max_output_tokens_used": max_out,
                },
            },
        )

    raw = _clamp_response_to_closed_max(raw, MAX_RESPONSE_CHARS)

    session_uuid = str(uuid.uuid4())
    tokens_used = None
    if hasattr(response, "usage") and response.usage:
        tokens_used = getattr(response.usage, "total_tokens", None)

    stored_input = f"[question]\n{question}\n\n[user_context]\n{user_context}"
    if len(stored_input) > 65000:
        stored_input = stored_input[:64900] + "\n\n[... truncado ...]"

    def _build_ai_row() -> AIConversationModel:
        return AIConversationModel(
            user_id=user_id_int,
            session_id=session_uuid,
            previous_response_id=getattr(response, "id", None),
            input_text=stored_input,
            instruction="evaluator_chat",
            response_text=raw,
            model=model_name,
            tokens_used=tokens_used,
            added_date=datetime.now(),
            updated_date=datetime.now(),
        )

    conv_id = None
    try:
        row = _build_ai_row()
        db.add(row)
        if psychoped_student_id is not None and psychoped_field_key:
            ql = question if len(question) <= 512 else question[:512]
            db.add(
                EvaluatorChatPsychopedSectionUseModel(
                    user_id=user_id_int,
                    student_id=psychoped_student_id,
                    field_key=psychoped_field_key,
                    question_label=ql,
                    created_at=datetime.now(),
                )
            )
        db.commit()
        db.refresh(row)
        conv_id = row.id
    except IntegrityError:
        db.rollback()
        try:
            row_only = _build_ai_row()
            db.add(row_only)
            db.commit()
            db.refresh(row_only)
            conv_id = row_only.id
        except Exception:
            db.rollback()
            conv_id = None
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
