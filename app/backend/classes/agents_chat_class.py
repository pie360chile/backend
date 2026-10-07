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
from app.backend.utils.agents_bulk_reports import (
    FAMILIA_DOCUMENT_ID as _FAMILIA_DOCUMENT_ID,
    MAX_BULK_STUDENTS,
    PSYCHOPED_DOCUMENT_ID as _PSYCHOPED_DOCUMENT_ID,
    bulk_confirm_ask,
    bulk_document_label,
    files_mention_student,
    looks_like_bulk_request,
    resolve_bulk_plan,
    user_confirmed_bulk,
    zip_generated_files,
)
from app.backend.utils.agents_chat_context import (
    resolve_document_id_for_agent,
    resolve_student_id,
    student_identification_hint,
    wants_document_generation,
    build_ask_rut_reply,
    build_invalid_rut_reply,
)
from app.backend.utils.agents_code_guard import (
    CODE_REJECT_REPLY,
    message_is_html_or_code,
    strip_html_and_code_blocks,
)
from app.backend.utils.agents_scope_guard import (
    SCOPE_REJECT_REPLY,
    message_is_off_topic,
)
from app.backend.utils.agents_llm_client import (
    estimate_tokens_from_text,
    normalize_usage,
    stream_chat_completion,
)
from app.backend.utils.agents_mcp_fields import (
    extract_fields_from_reply,
    is_content_too_thin,
    sanitize_psychoped_fields,
    strip_fields_json_from_reply,
)

def _missing_form_answers_reply() -> str:
    return (
        "No es posible elaborar el Informe de Evaluación Psicopedagógica. "
        "El formulario de este estudiante no tiene respuestas registradas. "
        "Mientras el cuestionario no esté contestado, no se emite el informe."
    )


def _is_psychoped_report(document_id: int | None, agent_name: str | None) -> bool:
    if document_id is not None and int(document_id) == _PSYCHOPED_DOCUMENT_ID:
        return True
    name = (agent_name or "").lower()
    return "psicoped" in name and "familia" not in name


def _psychoped_blocked_without_form(
    db: Session,
    *,
    document_id: int | None,
    agent_name: str | None,
    student_id: int | None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> bool:
    if not student_id or not _is_psychoped_report(document_id, agent_name):
        return False
    from app.backend.utils.agents_dynamic_form_context import (
        student_has_nonempty_form_answers,
    )

    return not student_has_nonempty_form_answers(
        db,
        student_id=int(student_id),
        school_id=int(school_id) if school_id else None,
        period_year=int(period_year) if period_year else None,
    )


def _missing_psychoped_files_reply() -> str:
    return (
        "No es posible elaborar el Informe de Evaluación Psicopedagógica: "
        "no dispongo de antecedentes documentales del estudiante en Files "
        "(cuestionarios, pautas, anamnesis u otras evidencias) ni de respuestas "
        "en Formularios (Inf. Eval. Psicopedagógica).\n\n"
        "Sin esa información no puedo redactar ni emitir el informe."
    )


def _missing_family_sources_reply() -> str:
    return _missing_psychoped_for_family_reply()


def _missing_psychoped_for_family_reply() -> str:
    return (
        "No es posible elaborar el Informe a la Familia. "
        "El estudiante debe contar previamente con el Informe de Evaluación "
        "Psicopedagógica, con el análisis y las sugerencias registrados en su ficha. "
        "Mientras ese informe no esté generado y guardado, no se emite el documento "
        "para la familia."
    )


def _is_family_report(document_id: int | None, agent_name: str | None) -> bool:
    if document_id is not None and int(document_id) == _FAMILIA_DOCUMENT_ID:
        return True
    return "familia" in (agent_name or "").lower()


_PSYCHOPED_DODGE_MARKERS = (
    "quedan pendientes",
    "queda pendiente",
    "quedan vacíos",
    "quedan vacios",
    "no figuran",
    "no hay antecedentes",
    "otros estudiantes",
    "rut distinto",
    "no trae el formulario",
    "campos narrativos",
    "quedan en blanco",
)


def _reply_dodges_saved_psychoped(text: str) -> bool:
    low = (text or "").lower()
    return any(marker in low for marker in _PSYCHOPED_DODGE_MARKERS)


def _family_blocked_without_psychoped(
    db: Session,
    *,
    document_id: int | None,
    agent_name: str | None,
    student_id: int | None,
) -> bool:
    if not student_id or not _is_family_report(document_id, agent_name):
        return False
    from app.backend.utils.agents_saved_psychoped_context import (
        student_has_usable_psychoped_report,
    )

    return not student_has_usable_psychoped_report(db, int(student_id))


def _load_student_name_rut(db: Session, student_id: int) -> tuple[str | None, str | None]:
    from app.backend.db.models.pie_core import StudentModel, StudentPersonalInfoModel

    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == int(student_id))
        .first()
    )
    student = db.query(StudentModel).filter(StudentModel.id == int(student_id)).first()
    name = None
    rut = None
    if personal:
        name = " ".join(
            p
            for p in (
                getattr(personal, "names", None),
                getattr(personal, "father_lastname", None),
                getattr(personal, "mother_lastname", None),
            )
            if p
        ).strip() or None
        rut = (getattr(personal, "identification_number", None) or "").strip() or None
    if not rut and student:
        rut = (getattr(student, "identification_number", None) or "").strip() or None
    return name, rut


def _student_has_report_sources(
    *,
    db: Session,
    agent_name: str,
    customer_id: int,
    student_id: int,
    student_name: str | None,
    student_rut: str | None,
    document_id: int | None,
    school_id: int | None = None,
    period_year: int | None = None,
) -> bool:
    files_block = ""
    try:
        from app.backend.utils import agents_derived_storage as derived

        files_block, _n = derived.build_selective_files_context(
            agent_name or "",
            query=student_name or "",
            student_rut=student_rut,
            student_name=student_name,
            customer_id=int(customer_id),
        )
    except Exception:
        files_block = ""

    if files_mention_student(files_block, student_name or "", student_rut):
        return True

    doc = int(document_id) if document_id else None
    if doc == _PSYCHOPED_DOCUMENT_ID:
        try:
            from app.backend.utils.agents_dynamic_form_context import (
                student_has_dynamic_form_answers,
            )

            return student_has_dynamic_form_answers(
                db,
                student_id=int(student_id),
                school_id=int(school_id) if school_id else None,
                period_year=int(period_year) if period_year else None,
            )
        except Exception:
            return False

    # Familia: puede usar el psicopedagógico de la ficha.
    try:
        from app.backend.utils.agents_student_folder_context import (
            maybe_build_ficha_psychoped_block,
        )

        ficha = maybe_build_ficha_psychoped_block(
            db,
            student_id=int(student_id),
            document_id=doc or _FAMILIA_DOCUMENT_ID,
            files_block=files_block or "",
            student_name=student_name,
            student_rut=student_rut,
        )
        return bool((ficha or "").strip())
    except Exception:
        return False


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
    school_id: int | None = None,
    period_year: int | None = None,
) -> str:
    parts: list[str] = []
    instructions = (agent.role_instructions or "").strip()
    if instructions:
        parts.append(instructions)
    parts.append(
        "RUT (ambos informes: familia y psicopedagógico): coincidencia exacta con PIE360. "
        "Si el usuario entrega un RUT que no existe, responde que el RUT es incorrecto y "
        "no identifiques a nadie ni generes el documento. "
        "Prohibido completar, prefijar o corregir dígitos con la nómina u otros archivos."
    )
    parts.append(
        "SIN INTERNET / SIN BÚSQUEDA WEB (regla dura, ambos agentes): "
        "está PROHIBIDO buscar en internet, navegar la web, usar buscadores, citar sitios "
        "externos o consultar fuentes online. Solo puedes usar: (1) archivos del agente y su "
        "texto derivado en el contexto, (2) mensajes del chat, (3) datos PIE360 / ficha "
        "inyectados. Si falta un dato, dilo y deja el campo vacío; no lo busques en la red."
    )
    parts.append(
        "SIN HTML NI CÓDIGO (regla dura, ambos agentes): está PROHIBIDO escribir, aceptar o "
        "devolver HTML, CSS, JavaScript, Python, SQL u otro lenguaje de programación. "
        "Responde solo en español, prosa profesional. El único JSON permitido es el bloque "
        "`fields` al final cuando hay que generar el documento (eso lo consume el servidor, "
        "no es código para el usuario). Nunca uses etiquetas <p>, <div>, <script> ni fences "
        "de código (```html, ```python, etc.)."
    )
    parts.append(
        "ÁMBITO PIE CHILE (regla dura, ambos agentes): solo atiendes el Programa de "
        "Integración Escolar de Chile y PIE360: informes psicopedagógicos, informes a la "
        "familia, estudiantes, NEE, Decreto 170 y documentación del establecimiento. "
        "Si preguntan cualquier otra cosa (clima, recetas, noticias, cultura general, "
        "programación, deporte, etc.), NO respondas el contenido: indica con profesionalismo "
        "que solo contestas temas de PIE Chile y ofrece continuar con un informe o un dato "
        "de un estudiante del programa."
    )

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

        # Formularios PIE360: evaluación de este student_id aunque el Excel no traiga el RUT.
        doc_int = int(document_id) if document_id is not None else None
        agent_name_l = (agent.name or "").lower()
        wants_form_answers = doc_int in (_PSYCHOPED_DOCUMENT_ID, _FAMILIA_DOCUMENT_ID) or (
            "psicoped" in agent_name_l or "familia" in agent_name_l
        )
        if student_id and wants_form_answers:
            try:
                mcp_form = AgentsMcpClass(db).get_student_psychopedagogical_form_answers(
                    agent_id=str(agent.id),
                    customer_id=int(customer_id),
                    student_id=int(student_id),
                    school_id=int(school_id) if school_id else None,
                    period_year=int(period_year) if period_year else None,
                    student_name=student_name,
                    student_rut=student_rut,
                )
                if mcp_form.get("status") == "success":
                    ctx = (mcp_form.get("data") or {}).get("context") or ""
                    if str(ctx).strip():
                        parts.append(str(ctx).strip())
            except Exception:
                pass

            try:
                mcp_history = AgentsMcpClass(db).get_student_school_history(
                    agent_id=str(agent.id),
                    customer_id=int(customer_id),
                    student_id=int(student_id),
                    school_id=int(school_id) if school_id else None,
                    period_year=int(period_year) if period_year else None,
                    student_name=student_name,
                    student_rut=student_rut,
                )
                if mcp_history.get("status") == "success":
                    hist_ctx = (mcp_history.get("data") or {}).get("context") or ""
                    if str(hist_ctx).strip():
                        parts.append(str(hist_ctx).strip())
            except Exception:
                pass

        wants_family = doc_int == _FAMILIA_DOCUMENT_ID or "familia" in agent_name_l
        if student_id and wants_family:
            try:
                saved = AgentsMcpClass(db).get_saved_psychopedagogical_evaluation(
                    agent_id=str(agent.id),
                    customer_id=int(customer_id),
                    student_id=int(student_id),
                    student_name=student_name,
                    student_rut=student_rut,
                )
                if saved.get("status") == "success":
                    saved_ctx = (saved.get("data") or {}).get("context") or ""
                    if str(saved_ctx).strip():
                        parts.append(str(saved_ctx).strip())
            except Exception:
                pass

        # Informe a la familia: siempre el último psicopedagógico de la carpeta (doc 27).
        try:
            from app.backend.utils.agents_student_folder_context import (
                maybe_build_ficha_psychoped_block,
            )

            ficha_block = maybe_build_ficha_psychoped_block(
                db,
                student_id=student_id,
                document_id=document_id,
                files_block=files_block or "",
                student_name=student_name,
                student_rut=student_rut,
            )
            if ficha_block:
                parts.append(ficha_block)
        except Exception:
            pass
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
        period_year: int | None = None,
    ) -> None:
        self.db = db
        self.customer_id = customer_id
        self.school_id = school_id
        self.user_id = user_id
        self.period_year = period_year

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

        if message_is_html_or_code(text):
            ask = CODE_REJECT_REPLY
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        if message_is_off_topic(text):
            ask = SCOPE_REJECT_REPLY
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        resolved_document_id = resolve_document_id_for_agent(
            self.db,
            agent_id=agent_id,
            agent_name=agent_row.name,
            requested_document_id=document_id,
            message=text,
            history=history,
        )
        want_doc_early = wants_document_generation(text, history)
        bulk_request = looks_like_bulk_request(text, history)
        # Psicopedagógico: no rechazar solo por falta de Files; el estudiante puede tener
        # respuestas vía MCP get_student_psychopedagogical_form_answers (se valida abajo).

        if bulk_request:
            yield from self._stream_bulk_reports(
                agent_id=agent_id,
                agent_row=agent_row,
                text=text,
                history=history,
                document_id=resolved_document_id,
            )
            return

        # Uno a uno: si no hay ficha/RUT, se pide el RUT más abajo.

        resolved_student_id, rut_used, student_issue = resolve_student_id(
            self.db,
            student_id=student_id,
            student_rut=student_rut,
            message=text,
            history=history,
            customer_id=int(self.customer_id) if self.customer_id else None,
            school_id=int(self.school_id) if self.school_id else None,
            period_year=int(self.period_year) if self.period_year else None,
        )
        effective_rut = (student_rut or rut_used or "").strip() or None
        student_name: str | None = None
        if resolved_student_id:
            student_name, personal_rut = _load_student_name_rut(
                self.db, int(resolved_student_id)
            )
            effective_rut = effective_rut or personal_rut

        # Informe a la familia: sin psicopedagógico usable no se llama al modelo ni se arma el Word.
        if (
            want_doc_early
            and resolved_student_id
            and _family_blocked_without_psychoped(
                self.db,
                document_id=resolved_document_id,
                agent_name=agent_row.name or "",
                student_id=int(resolved_student_id),
            )
        ):
            ask = _missing_psychoped_for_family_reply()
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        # Psicopedagógico: formulario vacío → no se llama al modelo ni se arma el Word.
        if (
            want_doc_early
            and resolved_student_id
            and _psychoped_blocked_without_form(
                self.db,
                document_id=resolved_document_id,
                agent_name=agent_row.name or "",
                student_id=int(resolved_student_id),
                school_id=int(self.school_id) if self.school_id else None,
                period_year=int(self.period_year) if self.period_year else None,
            )
        ):
            ask = _missing_form_answers_reply()
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        # Estudiante identificado pero sin fuentes: rechazar. No pedir RUT.
        has_report_sources = False
        if want_doc_early and resolved_student_id:
            has_report_sources = _student_has_report_sources(
                db=self.db,
                agent_name=agent_row.name or "",
                customer_id=int(self.customer_id),
                student_id=int(resolved_student_id),
                student_name=student_name,
                student_rut=effective_rut,
                document_id=resolved_document_id,
                school_id=int(self.school_id) if self.school_id else None,
                period_year=int(self.period_year) if self.period_year else None,
            )
            if not has_report_sources:
                if resolved_document_id == _PSYCHOPED_DOCUMENT_ID:
                    ask = _missing_psychoped_files_reply()
                else:
                    ask = _missing_family_sources_reply()
                yield {"type": "text_delta", "delta": ask}
                yield {
                    "type": "done",
                    "data": {
                        "reply": ask,
                        "usage": None,
                        "model": None,
                        "responseFiles": [],
                        "warning": None,
                    },
                }
                return
        elif resolved_student_id:
            has_report_sources = _student_has_report_sources(
                db=self.db,
                agent_name=agent_row.name or "",
                customer_id=int(self.customer_id),
                student_id=int(resolved_student_id),
                student_name=student_name,
                student_rut=effective_rut,
                document_id=resolved_document_id,
                school_id=int(self.school_id) if self.school_id else None,
                period_year=int(self.period_year) if self.period_year else None,
            )

        # RUT informado y no existe: no llamar al LLM ni adivinar otro número.
        if student_issue == "not_found" and not resolved_student_id:
            ask = build_invalid_rut_reply(rut_used)
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        # Sin identificar al estudiante: pedir RUT antes de llamar al LLM.
        if (
            want_doc_early
            and not resolved_student_id
            and student_issue == "needs_rut"
        ):
            ask = build_ask_rut_reply(
                text,
                document_id=resolved_document_id,
                agent_name=agent_row.name,
            )
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        llm = AgentsLlmModelsClass(self.db)
        model_code = llm.get_selected_model_code()
        yield {"type": "step", "message": "Preparando contexto del estudiante…"}

        system_prompt = _build_system_prompt(
            db=self.db,
            agent=agent_row,
            customer_id=int(self.customer_id),
            student_id=resolved_student_id,
            student_rut=effective_rut,
            document_id=resolved_document_id,
            message=text,
            school_id=int(self.school_id) if self.school_id else None,
            period_year=int(self.period_year) if self.period_year else None,
        )
        messages = _build_messages(
            system_prompt=system_prompt,
            message=text,
            history=history,
        )

        yield {"type": "step", "message": "Redactando respuesta…"}

        want_doc = wants_document_generation(text, history)
        llm_timeout = 240 if want_doc else 120
        llm_max_tokens = 8192 if want_doc else None

        reply_text = ""
        usage: dict[str, Any] | None = None
        first_token = True
        for event in stream_chat_completion(
            messages,
            model=model_code,
            db=self.db,
            timeout=llm_timeout,
            max_tokens=llm_max_tokens,
        ):
            if event.get("type") == "text_delta":
                if first_token:
                    first_token = False
                    yield {"type": "step", "message": "Escribiendo respuesta…"}
                reply_text += event.get("delta") or ""
                yield event
            elif event.get("type") == "done":
                data = event.get("data") or {}
                reply_text = data.get("reply") or reply_text
                usage = normalize_usage(
                    data.get("usage") if isinstance(data.get("usage"), dict) else None
                )
            elif event.get("type") == "error":
                # Si ya hubo tokens parciales, igual registramos el uso estimado.
                if self.customer_id and (reply_text or usage):
                    self._record_llm_usage(
                        agent_id=agent_id,
                        model_code=model_code,
                        usage=usage,
                        messages=messages,
                        reply_text=reply_text,
                        input_text=text,
                        output_text=reply_text,
                        request_kind="chat",
                    )
                yield event
                return
            else:
                yield event

        visible_reply = reply_text
        response_files: list[dict[str, Any]] = []
        warning: str | None = None
        fields = extract_fields_from_reply(reply_text)

        family_has_psychoped = bool(
            resolved_student_id
            and _is_family_report(resolved_document_id, agent_row.name or "")
            and not _family_blocked_without_psychoped(
                self.db,
                document_id=resolved_document_id,
                agent_name=agent_row.name or "",
                student_id=int(resolved_student_id),
            )
        )
        dodged_psychoped = family_has_psychoped and _reply_dodges_saved_psychoped(reply_text)

        # Si pidió el informe y el modelo se quedó en la intro sin JSON → 1 reintento forzado.
        if (
            want_doc
            and resolved_student_id
            and resolved_document_id
            and has_report_sources
            and (not fields or dodged_psychoped)
        ):
            yield {
                "type": "step",
                "message": "Completando campos del documento (reintento)…",
            }
            if family_has_psychoped:
                retry_msg = (
                    "La ficha PIE360 de este estudiante SÍ tiene Informe de Evaluación "
                    "Psicopedagógica (conclusión y sugerencias). Eso es la evaluación. "
                    "Ignora el reporte interactivo y la nómina de otros RUT. "
                    "Responde AHORA solo con ```json\n{\"fields\": {...}}\n``` del Informe "
                    "a la Familia, redactado desde esa ficha. Prohibido decir que no hay "
                    "evaluación o que los campos quedan pendientes."
                )
            else:
                retry_msg = (
                    "Tu respuesta anterior NO incluyó el bloque JSON `fields` y por eso "
                    "NO se generó el documento. Responde AHORA solo con el bloque "
                    '```json\n{"fields": {...}}\n``` completo (todos los campos de la '
                    "plantilla, narrativos detallados). Prohibido intro larga; máximo "
                    "1 oración antes del JSON. Usa Files, formulario MCP y ficha; "
                    "no inventes datos."
                )
            retry_messages = list(messages) + [
                {"role": "assistant", "content": reply_text or "(sin JSON)"},
                {"role": "user", "content": retry_msg},
            ]
            retry_reply = ""
            for event in stream_chat_completion(
                retry_messages,
                model=model_code,
                db=self.db,
                timeout=llm_timeout,
                max_tokens=llm_max_tokens,
            ):
                if event.get("type") == "text_delta":
                    delta = event.get("delta") or ""
                    retry_reply += delta
                    yield event
                elif event.get("type") == "done":
                    data = event.get("data") or {}
                    retry_reply = data.get("reply") or retry_reply
                    retry_usage = normalize_usage(
                        data.get("usage")
                        if isinstance(data.get("usage"), dict)
                        else None
                    )
                    if retry_usage and usage:
                        usage = {
                            "prompt_tokens": int(usage.get("prompt_tokens") or 0)
                            + int(retry_usage.get("prompt_tokens") or 0),
                            "completion_tokens": int(usage.get("completion_tokens") or 0)
                            + int(retry_usage.get("completion_tokens") or 0),
                            "total_tokens": int(usage.get("total_tokens") or 0)
                            + int(retry_usage.get("total_tokens") or 0),
                            "prompt_cache_hit_tokens": int(
                                usage.get("prompt_cache_hit_tokens") or 0
                            )
                            + int(retry_usage.get("prompt_cache_hit_tokens") or 0),
                            "prompt_cache_miss_tokens": int(
                                usage.get("prompt_cache_miss_tokens") or 0
                            )
                            + int(retry_usage.get("prompt_cache_miss_tokens") or 0),
                        }
                    elif retry_usage:
                        usage = retry_usage
                elif event.get("type") == "error":
                    yield event
                    return
            if retry_reply:
                fields = extract_fields_from_reply(retry_reply) or extract_fields_from_reply(
                    reply_text
                )
                if family_has_psychoped and _reply_dodges_saved_psychoped(reply_text):
                    visible_reply = retry_reply
                    reply_text = retry_reply
                else:
                    reply_text = ((reply_text or "").rstrip() + "\n\n" + retry_reply).strip()
                    visible_reply = reply_text

        if family_has_psychoped and resolved_student_id:
            from app.backend.utils.agents_saved_psychoped_context import (
                family_fields_from_saved_psychoped,
            )

            saved_fields = family_fields_from_saved_psychoped(
                self.db, int(resolved_student_id)
            )
            if saved_fields:
                merged_fields = dict(fields or {})
                for key, value in saved_fields.items():
                    if not str(merged_fields.get(key) or "").strip():
                        merged_fields[key] = value
                if merged_fields:
                    fields = merged_fields
                    if _reply_dodges_saved_psychoped(visible_reply):
                        visible_reply = (
                            "El Informe a la Familia se elaboró con el Informe de "
                            "Evaluación Psicopedagógica guardado en la ficha. "
                            "Se usaron la conclusión y las sugerencias que están "
                            "registradas. No se completaron los apartados que esa "
                            "ficha tiene vacíos."
                        )

        if want_doc or fields:
            if not resolved_student_id:
                # No reemplazar la respuesta del modelo pidiendo RUT.
                warning = None
            elif not resolved_document_id:
                warning = (
                    "Falta document_id / plantilla del agente. "
                    "Sube el modelo en Documentos del agente."
                )
            elif (
                int(resolved_document_id) == _PSYCHOPED_DOCUMENT_ID
                and not has_report_sources
            ):
                visible_reply = _missing_psychoped_files_reply()
                warning = None
            elif _psychoped_blocked_without_form(
                self.db,
                document_id=resolved_document_id,
                agent_name=agent_row.name or "",
                student_id=int(resolved_student_id),
                school_id=int(self.school_id) if self.school_id else None,
                period_year=int(self.period_year) if self.period_year else None,
            ):
                visible_reply = _missing_form_answers_reply()
                warning = None
            elif _family_blocked_without_psychoped(
                self.db,
                document_id=resolved_document_id,
                agent_name=agent_row.name or "",
                student_id=int(resolved_student_id),
            ):
                visible_reply = _missing_psychoped_for_family_reply()
                warning = None
            elif not fields:
                warning = (
                    "El agente redactó pero no envió el bloque JSON de fields. "
                    "Pide de nuevo «genera el informe» o completa los campos."
                )
            else:
                yield {"type": "step", "message": "Creando documento…"}
                try:
                    yield {
                        "type": "step",
                        "message": "Rellenando plantilla y guardando en la carpeta…",
                    }
                    payload_fields = fields
                    if int(resolved_document_id) == _PSYCHOPED_DOCUMENT_ID:
                        payload_fields = sanitize_psychoped_fields(fields)
                    created = AgentsMcpClass(self.db).create_document(
                        agent_id=agent_id,
                        customer_id=int(self.customer_id),
                        student_id=int(resolved_student_id),
                        document_id=int(resolved_document_id),
                        fields=payload_fields,
                    )
                    if created.get("status") == "error":
                        warning = created.get("message") or "No se pudo generar el documento."
                    else:
                        data = created.get("data") or {}
                        response_files = list(data.get("responseFiles") or [])
                        visible_reply = strip_fields_json_from_reply(reply_text)
                        if data.get("googleDrive") and data["googleDrive"].get("drive_path"):
                            yield {
                                "type": "step",
                                "message": "Documento subido a Google Drive…",
                            }
                        elif data.get("googleDriveError"):
                            yield {
                                "type": "step",
                                "message": "Documento listo (Drive no disponible)…",
                            }
                        else:
                            yield {"type": "step", "message": "Documento listo…"}
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

        # Nunca mostrar el JSON de fields en el chat (solo la redacción).
        if fields or extract_fields_from_reply(visible_reply):
            visible_reply = strip_fields_json_from_reply(visible_reply)
        elif "```json" in (visible_reply or "").lower() or '{"fields"' in (
            visible_reply or ""
        ):
            visible_reply = strip_fields_json_from_reply(visible_reply)
        visible_reply = strip_html_and_code_blocks(visible_reply)

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

        self._record_llm_usage(
            agent_id=agent_id,
            model_code=model_code,
            usage=usage,
            messages=messages,
            reply_text=reply_text,
            input_text=text,
            output_text=visible_reply,
            request_kind="chat",
        )

    def _stream_bulk_reports(
        self,
        *,
        agent_id: str,
        agent_row: AgentModel,
        text: str,
        history: list[dict[str, str]] | None,
        document_id: int | None,
    ) -> Iterator[dict[str, Any]]:
        plan = resolve_bulk_plan(
            self.db,
            customer_id=int(self.customer_id),
            message=text,
            history=history,
            document_id=document_id,
            agent_name=agent_row.name,
            default_year=int(self.period_year) if self.period_year else None,
            session_school_id=int(self.school_id) if self.school_id else None,
        )
        if plan is None:
            ask = (
                "Para continuar con los informes del curso, indica el liceo, "
                "el año (ej. 2026) y el curso (ej. 1° Medio A)."
            )
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        if plan.ask and not plan.students:
            yield {"type": "text_delta", "delta": plan.ask}
            yield {
                "type": "done",
                "data": {
                    "reply": plan.ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        if not document_id:
            ask = (
                "No hay plantilla asociada a este agente. "
                "Sube el modelo en Documentos del agente e inténtalo de nuevo."
            )
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        students = list(plan.students or [])
        if len(students) > MAX_BULK_STUDENTS and not user_confirmed_bulk(text):
            ask = bulk_confirm_ask(
                course_name=(plan.course_name or "").strip() or "curso",
                school_name=(plan.school_name or "").strip() or "establecimiento",
                year=int(plan.year or 0),
                total=len(students),
            )
            yield {"type": "text_delta", "delta": ask}
            yield {
                "type": "done",
                "data": {
                    "reply": ask,
                    "usage": None,
                    "model": None,
                    "responseFiles": [],
                    "warning": None,
                },
            }
            return

        batch = students[:MAX_BULK_STUDENTS]
        label = bulk_document_label(document_id, agent_row.name)
        course_title = (plan.course_name or "").strip() or "curso"
        school_title = (plan.school_name or "").strip()
        year_title = plan.year
        roster = "\n".join(
            f"{i}. {s.get('name') or ('Estudiante ' + str(s.get('id')))}"
            for i, s in enumerate(batch, start=1)
        )
        header = (
            f"Curso **{course_title}**"
            f"{f' ({school_title}, {year_title})' if school_title else ''}: "
            f"**{len(batch)}** estudiante(s). Generaré el {label} uno a uno "
            "y lo guardaré en cada ficha.\n\n"
            f"{roster}\n"
        )
        if len(students) > MAX_BULK_STUDENTS:
            header += (
                f"\n(Tanda 1 de {MAX_BULK_STUDENTS}; quedan "
                f"{len(students) - MAX_BULK_STUDENTS} para otra tanda.)\n"
            )
        yield {"type": "text_delta", "delta": header}
        yield {"type": "step", "message": f"0/{len(batch)} preparando generación…"}

        llm = AgentsLlmModelsClass(self.db)
        model_code = llm.get_selected_model_code()
        ok_names: list[str] = []
        omitted: list[tuple[str, str]] = []
        filenames: list[str] = []
        usage_acc: dict[str, Any] | None = None

        for index, student in enumerate(batch, start=1):
            sid = int(student.get("id") or 0)
            sname = (student.get("name") or f"Estudiante {sid}").strip()
            srut = (student.get("rut") or "").strip() or None
            yield {
                                "type": "step",
                "message": f"{index}/{len(batch)} {sname}…",
            }
            if not sid:
                omitted.append((sname, "ficha incompleta"))
                continue

            result = self._generate_one_bulk_document(
                agent_id=agent_id,
                agent_row=agent_row,
                student_id=sid,
                student_name=sname,
                student_rut=srut,
                document_id=int(document_id),
                label=label,
                model_code=model_code,
            )
            usage_acc = _merge_usage(usage_acc, result.get("usage"))
            if result.get("template_missing"):
                ask = result.get("reason") or "No hay plantilla en Documentos del agente."
                yield {"type": "text_delta", "delta": f"\n\n{ask}"}
                yield {
                    "type": "done",
                    "data": {
                        "reply": header + "\n" + ask,
                        "usage": usage_acc,
                        "model": model_code,
                        "responseFiles": [],
                        "warning": ask,
                    },
                }
                self._record_bulk_usage(
                    agent_id=agent_id,
                    model_code=model_code,
                    usage=usage_acc,
                    input_text=text,
                    output_text=header + "\n" + ask,
                    messages_hint=None,
                    reply_hint=ask,
                )
                return
            if result.get("ok"):
                ok_names.append(sname)
                fname = (result.get("filename") or "").strip()
                if fname:
                    filenames.append(fname)
            else:
                omitted.append((sname, result.get("reason") or "no se pudo generar"))

        zip_file = zip_generated_files(filenames)
        response_files = [zip_file] if zip_file else []
        lines = [
            header,
            f"**Generados:** {len(ok_names)}",
        ]
        if ok_names:
            lines.append(", ".join(ok_names))
        if omitted:
            lines.append(f"\n**Omitidos:** {len(omitted)}")
            for name, reason in omitted:
                lines.append(f"- {name}: {reason}")
        if zip_file:
            lines.append(
                "\nZIP con los Word generados listo para descargar. "
                "Cada informe quedó también en la ficha del estudiante."
            )
        elif ok_names:
            lines.append(
                "\nLos informes se guardaron en la ficha de cada estudiante."
            )
        else:
            lines.append("\nNo se generó ningún informe en esta tanda.")

        reply = "\n".join(lines).strip()
        yield {"type": "text_delta", "delta": "\n\n" + reply[len(header) :].lstrip()}
        yield {
                "type": "done",
                "data": {
                "reply": reply,
                "usage": usage_acc,
                "model": model_code,
                    "responseFiles": response_files,
                "warning": None,
            },
        }
        self._record_bulk_usage(
            agent_id=agent_id,
            model_code=model_code,
            usage=usage_acc,
            input_text=text,
            output_text=reply,
        )

    def _generate_one_bulk_document(
        self,
        *,
        agent_id: str,
        agent_row: AgentModel,
        student_id: int,
        student_name: str,
        student_rut: str | None,
        document_id: int,
        label: str,
        model_code: str,
    ) -> dict[str, Any]:
        empty: dict[str, Any] = {
            "ok": False,
            "filename": None,
            "reason": None,
            "usage": None,
            "template_missing": False,
        }
        if document_id == _FAMILIA_DOCUMENT_ID and _family_blocked_without_psychoped(
            self.db,
            document_id=document_id,
            agent_name=agent_row.name or "",
            student_id=int(student_id),
        ):
            empty["reason"] = _missing_psychoped_for_family_reply()
            return empty

        if document_id == _PSYCHOPED_DOCUMENT_ID and _psychoped_blocked_without_form(
            self.db,
            document_id=document_id,
            agent_name=agent_row.name or "",
            student_id=int(student_id),
            school_id=int(self.school_id) if self.school_id else None,
            period_year=int(self.period_year) if self.period_year else None,
        ):
            empty["reason"] = _missing_form_answers_reply()
            return empty

        if document_id == _PSYCHOPED_DOCUMENT_ID:
            files_block = ""
            try:
                from app.backend.utils import agents_derived_storage as derived

                files_block, _n = derived.build_selective_files_context(
                    agent_row.name or "",
                    query=student_name,
                    student_rut=student_rut,
                    student_name=student_name,
                    customer_id=int(self.customer_id),
                )
            except Exception:
                files_block = ""
            has_files = files_mention_student(files_block, student_name, student_rut)
            has_form = False
            if not has_files:
                try:
                    from app.backend.utils.agents_dynamic_form_context import (
                        student_has_dynamic_form_answers,
                    )

                    has_form = student_has_dynamic_form_answers(
                        self.db,
                        student_id=int(student_id),
                        school_id=int(self.school_id) if self.school_id else None,
                        period_year=int(self.period_year) if self.period_year else None,
                    )
                except Exception:
                    has_form = False
            has_history = False
            if not has_files and not has_form:
                try:
                    from app.backend.utils.agents_school_history_context import (
                        build_school_history_context,
                    )

                    has_history = (
                        build_school_history_context(
                            self.db,
                            student_id=int(student_id),
                            student_name=student_name,
                            student_rut=student_rut,
                            school_id=int(self.school_id) if self.school_id else None,
                            period_year=int(self.period_year) if self.period_year else None,
                        )
                        is not None
                    )
                except Exception:
                    has_history = False
            if not has_files and not has_form and not has_history:
                empty["reason"] = (
                    "sin antecedentes en Files, formulario ni anamnesis; no se emite el informe"
                )
                return empty

        system_prompt = _build_system_prompt(
            db=self.db,
            agent=agent_row,
            customer_id=int(self.customer_id),
            student_id=student_id,
            student_rut=student_rut,
            document_id=document_id,
            message=f"Genera el {label} de {student_name}",
            school_id=int(self.school_id) if self.school_id else None,
            period_year=int(self.period_year) if self.period_year else None,
        )
        user_msg = (
            f"Genera ahora el {label} de {student_name}"
            f"{f' (RUT {student_rut})' if student_rut else ''} "
            f"(student_id={student_id}). "
            "Incluye el bloque JSON con \"fields\" para rellenar la plantilla. "
            "Usa Files, formulario MCP, anamnesis (historia escolar) y ficha; no inventes datos."
        )
        messages = _build_messages(
            system_prompt=system_prompt,
            message=user_msg,
            history=None,
        )
        reply_text = ""
        usage: dict[str, Any] | None = None
        for event in stream_chat_completion(
            messages,
            model=model_code,
            db=self.db,
            timeout=240,
            max_tokens=8192,
        ):
            if event.get("type") == "text_delta":
                reply_text += event.get("delta") or ""
            elif event.get("type") == "done":
                data = event.get("data") or {}
                reply_text = data.get("reply") or reply_text
                usage = normalize_usage(
                    data.get("usage") if isinstance(data.get("usage"), dict) else None
                )
            elif event.get("type") == "error":
                empty["reason"] = event.get("message") or "error del modelo"
                empty["usage"] = _usage_or_estimate(usage, messages, reply_text)
                return empty

        fields = extract_fields_from_reply(reply_text)
        if not fields:
            # Reintento: el modelo a veces se queda en la intro sin JSON.
            retry_msg = (
                "Responde AHORA solo con ```json {\"fields\": {...}} ``` completo "
                "para la plantilla. Sin intro. Narrativos detallados; no inventes datos."
            )
            retry_messages = list(messages) + [
                {"role": "assistant", "content": reply_text or "(sin JSON)"},
                {"role": "user", "content": retry_msg},
            ]
            retry_reply = ""
            for event in stream_chat_completion(
                retry_messages,
                model=model_code,
                db=self.db,
                timeout=240,
                max_tokens=8192,
            ):
                if event.get("type") == "text_delta":
                    retry_reply += event.get("delta") or ""
                elif event.get("type") == "done":
                    data = event.get("data") or {}
                    retry_reply = data.get("reply") or retry_reply
                    retry_usage = normalize_usage(
                        data.get("usage")
                        if isinstance(data.get("usage"), dict)
                        else None
                    )
                    if retry_usage and usage:
                        usage = {
                            "prompt_tokens": int(usage.get("prompt_tokens") or 0)
                            + int(retry_usage.get("prompt_tokens") or 0),
                            "completion_tokens": int(usage.get("completion_tokens") or 0)
                            + int(retry_usage.get("completion_tokens") or 0),
                            "total_tokens": int(usage.get("total_tokens") or 0)
                            + int(retry_usage.get("total_tokens") or 0),
                            "prompt_cache_hit_tokens": int(
                                usage.get("prompt_cache_hit_tokens") or 0
                            )
                            + int(retry_usage.get("prompt_cache_hit_tokens") or 0),
                            "prompt_cache_miss_tokens": int(
                                usage.get("prompt_cache_miss_tokens") or 0
                            )
                            + int(retry_usage.get("prompt_cache_miss_tokens") or 0),
                        }
                    elif retry_usage:
                        usage = retry_usage
                elif event.get("type") == "error":
                    empty["reason"] = event.get("message") or "error del modelo"
                    empty["usage"] = _usage_or_estimate(
                        usage, retry_messages, reply_text + "\n" + retry_reply
                    )
                    return empty
            fields = extract_fields_from_reply(retry_reply)
            if retry_reply:
                reply_text = retry_reply
        if not fields:
            empty["reason"] = "el modelo no entregó los campos del informe"
            empty["usage"] = _usage_or_estimate(usage, messages, reply_text)
            return empty

        try:
            payload_fields = fields
            if int(document_id) == _PSYCHOPED_DOCUMENT_ID:
                payload_fields = sanitize_psychoped_fields(fields)
            created = AgentsMcpClass(self.db).create_document(
                agent_id=agent_id,
                customer_id=int(self.customer_id),
                student_id=int(student_id),
                document_id=int(document_id),
                fields=payload_fields,
            )
        except Exception as exc:
            empty["reason"] = f"error al guardar: {exc}"
            empty["usage"] = _usage_or_estimate(usage, messages, reply_text)
            return empty

        if created.get("status") == "error":
            msg = created.get("message") or "no se pudo generar el documento"
            empty["reason"] = msg
            empty["usage"] = _usage_or_estimate(usage, messages, reply_text)
            if "plantilla" in msg.lower():
                empty["template_missing"] = True
            return empty

        data = created.get("data") or {}
        files = list(data.get("responseFiles") or [])
        filename = ""
        if files:
            filename = str(files[0].get("name") or "")
        return {
            "ok": True,
            "filename": filename,
            "reason": None,
            "usage": _usage_or_estimate(usage, messages, reply_text),
            "template_missing": False,
        }

    def _record_llm_usage(
        self,
        *,
        agent_id: str,
        model_code: str,
        usage: dict[str, Any] | None,
        messages: list[dict[str, Any]] | None,
        reply_text: str,
        input_text: str,
        output_text: str,
        request_kind: str = "chat",
    ) -> None:
        if not self.customer_id:
            return
        ensured = _usage_or_estimate(usage, messages, reply_text)
        if not ensured:
            return
        try:
            AgentsUsageClass(self.db).record_chat(
                customer_id=int(self.customer_id),
                school_id=int(self.school_id) if self.school_id else None,
                user_id=int(self.user_id) if self.user_id else None,
                agent_id=agent_id,
                model=model_code,
                prompt_tokens=int(ensured.get("prompt_tokens") or 0),
                completion_tokens=int(ensured.get("completion_tokens") or 0),
                total_tokens=int(ensured.get("total_tokens") or 0),
                prompt_cache_hit_tokens=int(ensured.get("prompt_cache_hit_tokens") or 0),
                prompt_cache_miss_tokens=int(ensured.get("prompt_cache_miss_tokens") or 0),
                input_text=input_text,
                output_text=output_text,
                request_kind=request_kind,
            )
        except Exception:
            self.db.rollback()

    def _record_bulk_usage(
        self,
        *,
        agent_id: str,
        model_code: str,
        usage: dict[str, Any] | None,
        input_text: str,
        output_text: str,
        messages_hint: list[dict[str, Any]] | None = None,
        reply_hint: str | None = None,
    ) -> None:
        ensured = _usage_or_estimate(usage, messages_hint, reply_hint or output_text)
        self._record_llm_usage(
            agent_id=agent_id,
            model_code=model_code,
            usage=ensured,
            messages=messages_hint,
            reply_text=reply_hint or output_text or "",
            input_text=input_text,
            output_text=output_text,
            request_kind="bulk",
        )


def _usage_or_estimate(
    usage: dict[str, Any] | None,
    messages: list[dict[str, Any]] | None,
    reply_text: str | None,
) -> dict[str, Any] | None:
    """Usa usage del proveedor; si falta, estima para no perder el gasto."""
    if usage and (
        int(usage.get("prompt_tokens") or 0) > 0
        or int(usage.get("completion_tokens") or 0) > 0
        or int(usage.get("total_tokens") or 0) > 0
    ):
        return usage
    prompt_chars = "\n".join(
        str(m.get("content") or "") for m in (messages or []) if isinstance(m, dict)
    )
    reply = reply_text or ""
    if not prompt_chars and not reply:
        return usage
    pt = estimate_tokens_from_text(prompt_chars) if prompt_chars else 0
    ct = estimate_tokens_from_text(reply) if reply else 0
    if pt <= 0 and ct <= 0:
        return usage
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": pt + ct,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": pt,
    }


def _merge_usage(
    acc: dict[str, Any] | None, extra: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not extra:
        return acc
    if not acc:
        return {
            "prompt_tokens": int(extra.get("prompt_tokens") or 0),
            "completion_tokens": int(extra.get("completion_tokens") or 0),
            "total_tokens": int(extra.get("total_tokens") or 0),
            "prompt_cache_hit_tokens": int(extra.get("prompt_cache_hit_tokens") or 0),
            "prompt_cache_miss_tokens": int(extra.get("prompt_cache_miss_tokens") or 0),
        }
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
    ):
        acc[key] = int(acc.get(key) or 0) + int(extra.get(key) or 0)
    return acc
