"""Lógica para dynamic_forms (formularios dinámicos con definición JSON)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import case, desc
from sqlalchemy.orm import Session

from app.backend.classes.whatsapp_meta_class import notify_guardians_for_form
from app.backend.db.models import (
    DynamicFormModel,
    DynamicFormSubmissionModel,
    StudentGuardianModel,
    StudentPersonalInfoModel,
)


def _iso_dt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _row_to_api(row: DynamicFormModel) -> dict:
    try:
        fields = json.loads(row.fields_json) if row.fields_json else []
        if not isinstance(fields, list):
            fields = []
    except (json.JSONDecodeError, TypeError):
        fields = []
    return {
        "id": row.id,
        "name": row.name or "",
        "description": (row.description or "").strip(),
        "fields": fields,
        "courseId": row.course_id,
        "periodYear": row.period_year,
        "createdAt": _iso_dt(row.added_date),
        "updatedAt": _iso_dt(row.updated_date),
    }


class DynamicFormClass:
    def __init__(self, db: Session):
        self.db = db

    def _base_query(self, school_id: Optional[int], period_year: Optional[int] = None):
        q = self.db.query(DynamicFormModel).filter(DynamicFormModel.deleted_date.is_(None))
        if school_id is not None:
            q = q.filter(DynamicFormModel.school_id == school_id)
        if period_year is not None:
            q = q.filter(DynamicFormModel.period_year == period_year)
        return q

    def _guardian_cell(self, student_id: int) -> Optional[str]:
        g = (
            self.db.query(StudentGuardianModel)
            .filter(StudentGuardianModel.student_id == student_id)
            .order_by(desc(StudentGuardianModel.id))
            .first()
        )
        if not g or not g.celphone:
            return None
        return str(g.celphone).strip()

    def _student_display_name(self, student_id: int) -> str:
        p = (
            self.db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == student_id)
            .first()
        )
        if not p:
            return ""
        parts = [(p.names or "").strip(), (p.father_lastname or "").strip(), (p.mother_lastname or "").strip()]
        return " ".join(x for x in parts if x).strip()

    def _parse_notify_ids(self, data: dict) -> Optional[List[int]]:
        nids = data.get("notifyStudentIds")
        if nids is None:
            nids = data.get("notify_student_ids")
        if nids is None:
            return None
        if not isinstance(nids, list):
            return None
        out: List[int] = []
        for x in nids:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out

    def _parse_course_id(self, data: dict) -> Optional[int]:
        cid = data.get("courseId")
        if cid is None:
            cid = data.get("course_id")
        if cid is None or cid == "":
            return None
        try:
            return int(cid)
        except (TypeError, ValueError):
            return None

    def _parse_period_year(self, data: dict) -> Optional[int]:
        v = data.get("periodYear")
        if v is None:
            v = data.get("period_year")
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def _run_whatsapp_notify(self, student_ids: List[int], form_name: str) -> Any:
        if not student_ids:
            return None

        def label(sid: int) -> str:
            return self._student_display_name(sid) or "Estudiante"

        def phone(sid: int) -> Optional[str]:
            return self._guardian_cell(sid)

        return notify_guardians_for_form(self.db, student_ids, form_name, label, phone)

    def get_course_recipients(
        self,
        course_id: int,
        school_id: Optional[int],
        customer_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        """Estudiantes del curso con apoderado y celular (para UI checkboxes)."""
        try:
            from app.backend.classes.school_class import SchoolClass
            from app.backend.classes.student_class import StudentClass

            resolved_school = school_id
            if customer_id and not resolved_school:
                schools_list = SchoolClass(self.db).get_all(page=0, customer_id=customer_id)
                if isinstance(schools_list, list) and len(schools_list) > 0:
                    resolved_school = schools_list[0].get("id")

            raw = StudentClass(self.db).get_all(
                page=0,
                items_per_page=5000,
                school_id=resolved_school,
                course_id=course_id,
                period_year=period_year,
            )
            if isinstance(raw, dict) and raw.get("status") == "error":
                return {"status": "error", "message": raw.get("message", "Error"), "data": []}
            students = raw if isinstance(raw, list) else []

            out: List[dict] = []
            for st in students:
                sid = st.get("id")
                if sid is None:
                    continue
                pd = st.get("personal_data") or {}
                names = (pd.get("names") or "").strip()
                fl = (pd.get("father_lastname") or "").strip()
                ml = (pd.get("mother_lastname") or "").strip()
                full = " ".join(x for x in [names, fl, ml] if x)
                rut = (pd.get("identification_number") or st.get("identification_number") or "").strip()

                g = (
                    self.db.query(StudentGuardianModel)
                    .filter(StudentGuardianModel.student_id == sid)
                    .order_by(desc(StudentGuardianModel.id))
                    .first()
                )
                g_name = ""
                g_phone = ""
                if g:
                    gn = (g.names or "").strip()
                    gf = (g.father_lastname or "").strip()
                    gm = (g.mother_lastname or "").strip()
                    g_name = " ".join(x for x in [gn, gf, gm] if x)
                    g_phone = (g.celphone or "").strip()

                out.append(
                    {
                        "studentId": sid,
                        "studentName": full or "—",
                        "studentRut": rut or "—",
                        "guardianName": g_name or "—",
                        "guardianPhone": g_phone or "—",
                    }
                )
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_all(
        self,
        page: int = 0,
        items_per_page: int = 100,
        search: Optional[str] = None,
        school_id: Optional[int] = None,
        period_year: Optional[int] = None,
    ) -> Any:
        """Lista formularios activos. page=0 sin paginación (como support_areas). Filtra por period_year si se indica."""
        try:
            query = self._base_query(school_id, period_year)
            if search and str(search).strip():
                s = f"%{search.strip()}%"
                query = query.filter(
                    (DynamicFormModel.name.like(s)) | (DynamicFormModel.description.like(s))
                )
            query = query.order_by(
                case((DynamicFormModel.updated_date.is_(None), 1), else_=0),
                DynamicFormModel.updated_date.desc(),
            )
            if page > 0 and items_per_page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page or 1
                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": [],
                    }
                rows = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
                data = [_row_to_api(r) for r in rows]
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": data,
                }
            rows = query.all()
            return [_row_to_api(r) for r in rows]
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id: int, school_id: Optional[int], period_year: Optional[int] = None) -> Any:
        try:
            q = self.db.query(DynamicFormModel).filter(
                DynamicFormModel.id == id,
                DynamicFormModel.deleted_date.is_(None),
            )
            if school_id is not None:
                q = q.filter(DynamicFormModel.school_id == school_id)
            if period_year is not None:
                q = q.filter(DynamicFormModel.period_year == period_year)
            row = q.first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {"status": "success", "data": _row_to_api(row)}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def _fields_to_json(self, fields: List[Any]) -> str:
        out = []
        for f in fields:
            if hasattr(f, "model_dump"):
                out.append(f.model_dump(by_alias=True))
            elif isinstance(f, dict):
                out.append(f)
        return json.dumps(out, ensure_ascii=False)

    def store(self, data: dict, school_id: Optional[int]) -> Any:
        try:
            name = (data.get("name") or "").strip()
            if not name:
                return {"status": "error", "message": "El nombre es obligatorio."}
            fields = data.get("fields") or []
            if not isinstance(fields, list) or len(fields) == 0:
                return {"status": "error", "message": "Debe incluir al menos un campo."}
            now = datetime.now()
            desc = (data.get("description") or "").strip() or None
            fields_json = self._fields_to_json(fields)
            course_id = self._parse_course_id(data)
            if course_id is None or course_id < 1:
                return {"status": "error", "message": "Debe indicar un curso asociado (courseId)."}
            period_year = self._parse_period_year(data)
            if period_year is None:
                return {"status": "error", "message": "Debe indicar el período escolar (periodYear)."}
            row = DynamicFormModel(
                school_id=school_id,
                course_id=course_id,
                period_year=period_year,
                name=name,
                description=desc,
                fields_json=fields_json,
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)

            notify_ids = self._parse_notify_ids(data)
            whatsapp_summary = None
            if notify_ids is not None and len(notify_ids) > 0:
                whatsapp_summary = self._run_whatsapp_notify(notify_ids, name)

            return {
                "status": "success",
                "message": "Formulario creado.",
                "id": row.id,
                "whatsapp": whatsapp_summary,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict, school_id: Optional[int]) -> Any:
        try:
            period_year = self._parse_period_year(data)
            if period_year is None:
                return {"status": "error", "message": "Debe indicar el período escolar (periodYear)."}
            q = self.db.query(DynamicFormModel).filter(DynamicFormModel.id == id)
            if school_id is not None:
                q = q.filter(DynamicFormModel.school_id == school_id)
            q = q.filter(DynamicFormModel.period_year == period_year)
            row = q.first()
            if not row or row.deleted_date is not None:
                return {"status": "error", "message": "Registro no encontrado."}
            if "name" in data and data["name"] is not None:
                n = str(data["name"]).strip()
                if n:
                    row.name = n
            if "description" in data:
                row.description = (str(data["description"]).strip() if data["description"] is not None else None) or None
            if "fields" in data and data["fields"] is not None:
                fields = data["fields"]
                if not isinstance(fields, list) or len(fields) == 0:
                    return {"status": "error", "message": "Debe incluir al menos un campo."}
                row.fields_json = self._fields_to_json(fields)
            if "courseId" in data or "course_id" in data:
                row.course_id = self._parse_course_id(data)
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)

            notify_ids = None
            if "notifyStudentIds" in data or "notify_student_ids" in data:
                tmp = self._parse_notify_ids(data)
                notify_ids = tmp if tmp is not None else []
            whatsapp_summary = None
            if notify_ids is not None and len(notify_ids) > 0:
                whatsapp_summary = self._run_whatsapp_notify(notify_ids, row.name or "Formulario")

            return {
                "status": "success",
                "message": "Formulario actualizado.",
                "id": id,
                "whatsapp": whatsapp_summary,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int, school_id: Optional[int], period_year: Optional[int] = None) -> Any:
        try:
            q = self.db.query(DynamicFormModel).filter(DynamicFormModel.id == id)
            if school_id is not None:
                q = q.filter(DynamicFormModel.school_id == school_id)
            if period_year is not None:
                q = q.filter(DynamicFormModel.period_year == period_year)
            row = q.first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def _get_form_row(
        self,
        form_id: int,
        school_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Optional[DynamicFormModel]:
        q = self.db.query(DynamicFormModel).filter(
            DynamicFormModel.id == form_id,
            DynamicFormModel.deleted_date.is_(None),
        )
        if school_id is not None:
            q = q.filter(DynamicFormModel.school_id == school_id)
        if period_year is not None:
            q = q.filter(DynamicFormModel.period_year == period_year)
        return q.first()

    def _course_student_ids(self, course_id: int, school_id: Optional[int], customer_id: Optional[int], period_year: Optional[int]) -> set:
        cr = self.get_course_recipients(course_id, school_id, customer_id, period_year)
        if cr.get("status") != "success":
            return set()
        out: set = set()
        for r in cr.get("data") or []:
            sid = r.get("studentId")
            if sid is not None:
                try:
                    out.add(int(sid))
                except (TypeError, ValueError):
                    continue
        return out

    def _validate_answers_payload(self, fields: List[dict], answers: dict) -> Optional[str]:
        if not isinstance(answers, dict):
            return "Las respuestas deben ser un objeto."
        for f in fields:
            fid = str(f.get("id") or "")
            ft = str(f.get("fieldType") or f.get("field_type") or "text")
            req = bool(f.get("required"))
            if not fid:
                continue
            val = answers.get(fid)
            if req:
                if val is None or val == "" or val == []:
                    return f'Falta responder el campo obligatorio: "{f.get("question", fid)}".'
            if val is None or val == "":
                continue
            if ft == "checkbox":
                if not isinstance(val, list):
                    return f'El campo "{f.get("question", fid)}" requiere una lista de opciones.'
            elif isinstance(val, list):
                return f'El campo "{f.get("question", fid)}" no admite múltiples valores.'
        return None

    def list_students_status(
        self,
        form_id: int,
        school_id: Optional[int],
        customer_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        """Estudiantes del curso del formulario con estado respondido / en_espera."""
        try:
            row = self._get_form_row(form_id, school_id, period_year)
            if not row:
                return {"status": "error", "message": "Formulario no encontrado."}
            if not row.course_id:
                return {"status": "error", "message": "El formulario no tiene curso asociado."}
            cr = self.get_course_recipients(int(row.course_id), school_id, customer_id, period_year)
            if cr.get("status") != "success":
                return {"status": "error", "message": cr.get("message", "Error al listar estudiantes."), "data": []}

            subs = (
                self.db.query(DynamicFormSubmissionModel)
                .filter(DynamicFormSubmissionModel.dynamic_form_id == form_id)
                .all()
            )
            by_student = {int(s.student_id): s for s in subs}

            out: List[dict] = []
            for r in cr.get("data") or []:
                sid = r.get("studentId")
                if sid is None:
                    continue
                try:
                    sid_int = int(sid)
                except (TypeError, ValueError):
                    continue
                sub = by_student.get(sid_int)
                out.append(
                    {
                        "studentId": sid_int,
                        "studentName": r.get("studentName") or "—",
                        "studentRut": r.get("studentRut") or "—",
                        "status": "respondido" if sub else "en_espera",
                        "submissionId": sub.id if sub else None,
                    }
                )
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_submission_detail(
        self,
        form_id: int,
        submission_id: int,
        school_id: Optional[int],
        customer_id: Optional[int] = None,
        period_year: Optional[int] = None,
    ) -> Any:
        try:
            q = self.db.query(DynamicFormSubmissionModel).filter(
                DynamicFormSubmissionModel.id == submission_id,
                DynamicFormSubmissionModel.dynamic_form_id == form_id,
            )
            sub = q.first()
            if not sub:
                return {"status": "error", "message": "Respuesta no encontrada.", "data": None}
            form_row = self._get_form_row(form_id, school_id, period_year)
            if not form_row:
                return {"status": "error", "message": "Formulario no encontrado.", "data": None}
            try:
                answers = json.loads(sub.answers_json) if sub.answers_json else {}
                if not isinstance(answers, dict):
                    answers = {}
            except (json.JSONDecodeError, TypeError):
                answers = {}
            if period_year is not None:
                if sub.period_year is not None and int(sub.period_year) != int(period_year):
                    return {"status": "error", "message": "Respuesta no encontrada.", "data": None}
            sid = sub.student_id
            name = self._student_display_name(int(sid)) if sid is not None else ""
            if not name:
                cr = self.get_course_recipients(int(form_row.course_id or 0), school_id, customer_id, None)
                if cr.get("status") == "success":
                    for r in cr.get("data") or []:
                        if int(r.get("studentId") or 0) == int(sub.student_id):
                            name = str(r.get("studentName") or "")
                            break
            data = {
                "submissionId": sub.id,
                "studentId": sub.student_id,
                "studentName": name or "—",
                "submittedAt": _iso_dt(sub.added_date),
                "answers": answers,
                "form": _row_to_api(form_row),
            }
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def submit_answers(
        self,
        form_id: int,
        school_id: Optional[int],
        customer_id: Optional[int],
        student_id: int,
        answers: dict,
        user_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        try:
            form_row = self._get_form_row(form_id, school_id, period_year)
            if not form_row:
                return {"status": "error", "message": "Formulario no encontrado."}
            if not form_row.course_id:
                return {"status": "error", "message": "El formulario no tiene curso asociado."}
            allowed = self._course_student_ids(int(form_row.course_id), school_id, customer_id, period_year)
            if student_id not in allowed:
                return {"status": "error", "message": "El estudiante no pertenece al curso de este formulario."}
            try:
                fields = json.loads(form_row.fields_json) if form_row.fields_json else []
                if not isinstance(fields, list):
                    fields = []
            except (json.JSONDecodeError, TypeError):
                fields = []
            err = self._validate_answers_payload(fields, answers)
            if err:
                return {"status": "error", "message": err}
            now = datetime.now()
            payload = json.dumps(answers, ensure_ascii=False)
            existing = (
                self.db.query(DynamicFormSubmissionModel)
                .filter(
                    DynamicFormSubmissionModel.dynamic_form_id == form_id,
                    DynamicFormSubmissionModel.student_id == student_id,
                )
                .first()
            )
            if existing:
                return {
                    "status": "error",
                    "message": "Este formulario ya fue respondido para este estudiante. Elimine las respuestas desde el listado de estudiantes (icono papelera) si debe volver a completarlo.",
                }
            row = DynamicFormSubmissionModel(
                dynamic_form_id=form_id,
                student_id=student_id,
                school_id=school_id,
                period_year=form_row.period_year,
                answers_json=payload,
                submitted_by_user_id=user_id,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Respuestas guardadas.", "submissionId": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def submission_for_student(
        self,
        form_id: int,
        student_id: int,
        school_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        """Indica si el estudiante ya tiene respuestas guardadas (para bloquear nueva carga)."""
        try:
            if not self._get_form_row(form_id, school_id, period_year):
                return {"status": "error", "message": "Formulario no encontrado."}
            sub = (
                self.db.query(DynamicFormSubmissionModel)
                .filter(
                    DynamicFormSubmissionModel.dynamic_form_id == form_id,
                    DynamicFormSubmissionModel.student_id == student_id,
                )
                .first()
            )
            return {
                "status": "success",
                "data": {
                    "hasSubmission": sub is not None,
                    "submissionId": sub.id if sub else None,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_submission(
        self,
        form_id: int,
        submission_id: int,
        school_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        """Elimina las respuestas de un estudiante para poder volver a completar el formulario."""
        try:
            sub = (
                self.db.query(DynamicFormSubmissionModel)
                .filter(
                    DynamicFormSubmissionModel.id == submission_id,
                    DynamicFormSubmissionModel.dynamic_form_id == form_id,
                )
                .first()
            )
            if not sub:
                return {"status": "error", "message": "Respuesta no encontrada."}
            if period_year is not None and sub.period_year is not None and int(sub.period_year) != int(period_year):
                return {"status": "error", "message": "Respuesta no encontrada."}
            if not self._get_form_row(form_id, school_id, period_year):
                return {"status": "error", "message": "Formulario no encontrado."}
            self.db.delete(sub)
            self.db.commit()
            return {"status": "success", "message": "Respuestas eliminadas."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def resend_whatsapp_to_guardian(
        self,
        form_id: int,
        student_id: int,
        school_id: Optional[int],
        customer_id: Optional[int],
        period_year: Optional[int] = None,
    ) -> Any:
        """Reenvía la plantilla WhatsApp al apoderado (solo estudiantes del curso sin respuesta aún)."""
        try:
            form_row = self._get_form_row(form_id, school_id, period_year)
            if not form_row:
                return {"status": "error", "message": "Formulario no encontrado."}
            if not form_row.course_id:
                return {"status": "error", "message": "El formulario no tiene curso asociado."}
            allowed = self._course_student_ids(int(form_row.course_id), school_id, customer_id, period_year)
            if student_id not in allowed:
                return {"status": "error", "message": "El estudiante no pertenece al curso de este formulario."}
            existing = (
                self.db.query(DynamicFormSubmissionModel)
                .filter(
                    DynamicFormSubmissionModel.dynamic_form_id == form_id,
                    DynamicFormSubmissionModel.student_id == student_id,
                )
                .first()
            )
            if existing:
                return {
                    "status": "error",
                    "message": "Solo se puede reenviar cuando el estudiante está en espera (sin respuestas guardadas).",
                }
            whatsapp_summary = self._run_whatsapp_notify([student_id], form_row.name or "Formulario")
            return {
                "status": "success",
                "message": "Notificación enviada al apoderado.",
                "whatsapp": whatsapp_summary,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
