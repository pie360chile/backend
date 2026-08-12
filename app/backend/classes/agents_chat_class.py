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
)
from app.backend.utils.agents_llm_client import (
    estimate_tokens_from_text,
    normalize_usage,
    stream_chat_completion,
)
from app.backend.utils.agents_file_context import agent_files_have_evaluation_evidence
from app.backend.utils.agents_mcp_fields import (
    extract_fields_from_reply,
    is_content_too_thin,
    strip_fields_json_from_reply,
)

def _missing_psychoped_files_reply() -> str:
    return (
        "No es posible elaborar el Informe de Evaluación Psicopedagógica: "
        "no dispongo de antecedentes documentales del estudiante en Files "
        "(cuestionarios, pautas, anamnesis u otras evidencias de evaluación).\n\n"
        "Sin esa información no puedo redactar ni emitir el informe."
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

        # Si Files no trae el psicopedagógico del caso → leer ficha del estudiante (doc 27)
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
        has_eval_files = agent_files_have_evaluation_evidence(
            agent_row.name or "", int(self.customer_id)
        )
        if (
            (want_doc_early or bulk_request)
            and resolved_document_id == _PSYCHOPED_DOCUMENT_ID
            and not has_eval_files
        ):
            ask = _missing_psychoped_files_reply()
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
        )
        effective_rut = (student_rut or rut_used or "").strip() or None

        # Sin RUT/ficha: pedir RUT antes de llamar al LLM / generar documento.
        if (
            want_doc_early
            and not resolved_student_id
            and student_issue in {"needs_rut", "not_found"}
        ):
            if student_issue == "not_found":
                ask = (
                    f"No encontré un estudiante con RUT **{rut_used}**. "
                    "Verifica el número (con dígito verificador) e inténtalo de nuevo, "
                    "o abre el chat desde la ficha del estudiante."
                )
            else:
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
        )
        messages = _build_messages(
            system_prompt=system_prompt,
            message=text,
            history=history,
        )

        yield {"type": "step", "message": "Redactando respuesta…"}

        reply_text = ""
        usage: dict[str, Any] | None = None
        first_token = True
        for event in stream_chat_completion(messages, model=model_code, db=self.db):
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
                visible_reply = build_ask_rut_reply(
                    text,
                    document_id=resolved_document_id,
                    agent_name=agent_row.name,
                )
                warning = None
            elif student_issue == "not_found":
                visible_reply = (
                    f"No encontré un estudiante con RUT **{rut_used}**. "
                    "Verifica el número e inténtalo de nuevo."
                )
                warning = None
            elif not resolved_student_id:
                warning = "Falta student_id para generar el documento."
            elif not resolved_document_id:
                warning = (
                    "Falta document_id / plantilla del agente. "
                    "Sube el modelo en Documentos del agente."
                )
            elif (
                int(resolved_document_id) == _PSYCHOPED_DOCUMENT_ID
                and not has_eval_files
            ):
                visible_reply = _missing_psychoped_files_reply()
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
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": pt,
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
                prompt_cache_hit_tokens=int(usage.get("prompt_cache_hit_tokens") or 0),
                prompt_cache_miss_tokens=int(usage.get("prompt_cache_miss_tokens") or 0),
                input_text=text,
                output_text=visible_reply,
            )
        except Exception:
            self.db.rollback()

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
            if not files_mention_student(files_block, student_name, student_rut):
                empty["reason"] = (
                    "sin antecedentes documentales en Files; no se emite el informe"
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
        )
        user_msg = (
            f"Genera ahora el {label} de {student_name}"
            f"{f' (RUT {student_rut})' if student_rut else ''} "
            f"(student_id={student_id}). "
            "Incluye el bloque JSON con \"fields\" para rellenar la plantilla. "
            "Usa solo Files y la ficha; no inventes datos."
        )
        messages = _build_messages(
            system_prompt=system_prompt,
            message=user_msg,
            history=None,
        )
        reply_text = ""
        usage: dict[str, Any] | None = None
        for event in stream_chat_completion(
            messages, model=model_code, db=self.db, timeout=180
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
                empty["usage"] = usage
                return empty

        fields = extract_fields_from_reply(reply_text)
        if not fields:
            empty["reason"] = "el modelo no entregó los campos del informe"
            empty["usage"] = usage
            return empty

        try:
            created = AgentsMcpClass(self.db).create_document(
                agent_id=agent_id,
                customer_id=int(self.customer_id),
                student_id=int(student_id),
                document_id=int(document_id),
                fields=fields,
            )
        except Exception as exc:
            empty["reason"] = f"error al guardar: {exc}"
            empty["usage"] = usage
            return empty

        if created.get("status") == "error":
            msg = created.get("message") or "no se pudo generar el documento"
            empty["reason"] = msg
            empty["usage"] = usage
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
            "usage": usage,
            "template_missing": False,
        }

    def _record_bulk_usage(
        self,
        *,
        agent_id: str,
        model_code: str,
        usage: dict[str, Any] | None,
        input_text: str,
        output_text: str,
    ) -> None:
        if not self.customer_id or not usage:
            return
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
                prompt_cache_hit_tokens=int(usage.get("prompt_cache_hit_tokens") or 0),
                prompt_cache_miss_tokens=int(usage.get("prompt_cache_miss_tokens") or 0),
                input_text=input_text,
                output_text=output_text,
            )
        except Exception:
            self.db.rollback()


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
