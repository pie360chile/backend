"""Plantillas de pruebas informales reutilizables por colegio."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.backend.db.models import (
    FolderModel,
    InformalTestTemplateModel,
    InformalTestTemplateQuestionModel,
    InformalTestSubmissionModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)

INFORMAL_TEST_FOLDER_DOCUMENT_ID = 43


def _reportlab_paragraph_text(value: Any) -> str:
    """Escape text for ReportLab Paragraph (XML subset); prevents errors on <, &, etc."""
    return escape("" if value is None else str(value))


_VALID_QUESTION_TYPES = {
    "short_text",
    "long_text",
    "single_choice",
    "multiple_choice",
    "number",
    "date",
}


def _iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


class InformalTestTemplateClass:
    def __init__(self, db: Session):
        self.db = db

    def _query_templates(self, school_id: int):
        return (
            self.db.query(InformalTestTemplateModel)
            .filter(
                InformalTestTemplateModel.school_id == school_id,
                InformalTestTemplateModel.deleted_date.is_(None),
            )
        )

    def _parse_options(self, raw: Optional[str]) -> List[Dict[str, str]]:
        if not raw:
            return []
        try:
            arr = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(arr, list):
            return []
        out: List[Dict[str, str]] = []
        for x in arr:
            if not isinstance(x, dict):
                continue
            label = str(x.get("label") or "").strip()
            value = str(x.get("value") or "").strip()
            if not label and not value:
                continue
            out.append({"label": label or value, "value": value or label})
        return out

    def _questions_for_template(self, template_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(InformalTestTemplateQuestionModel)
            .filter(InformalTestTemplateQuestionModel.template_id == template_id)
            .order_by(InformalTestTemplateQuestionModel.question_order.asc(), InformalTestTemplateQuestionModel.id.asc())
            .all()
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "question_text": r.question_text or "",
                    "question_type": r.question_type or "short_text",
                    "required": bool(r.required),
                    "options": self._parse_options(r.options_json),
                }
            )
        return out

    def _get_student_display_name(self, student_id: int) -> str:
        """Display name from student_personal_data (StudentModel has no given names on the row)."""
        personal_info = (
            self.db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == student_id)
            .first()
        )
        if not personal_info:
            return ""
        names = (personal_info.names or "").strip()
        father = (personal_info.father_lastname or "").strip()
        mother = (personal_info.mother_lastname or "").strip()
        lastnames = f"{father} {mother}".strip()
        return f"{names} {lastnames}".strip()

    def _get_student_identification_number(self, student_id: int) -> str:
        personal_info = (
            self.db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == student_id)
            .first()
        )
        if personal_info and (personal_info.identification_number or "").strip():
            return (personal_info.identification_number or "").strip()
        student_row = self.db.query(StudentModel).filter(StudentModel.id == student_id).first()
        if student_row and (student_row.identification_number or "").strip():
            return (student_row.identification_number or "").strip()
        return ""

    def _parse_birth_date(self, birth_date_raw: Any) -> Optional[date]:
        if birth_date_raw is None or birth_date_raw == "":
            return None
        try:
            if isinstance(birth_date_raw, datetime):
                return birth_date_raw.date()
            if isinstance(birth_date_raw, date):
                return birth_date_raw
            s = str(birth_date_raw).strip()[:10]
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    def _format_student_age_years_months(self, student_id: int) -> str:
        """
        Age at PDF build time, as years and months (same idea as in documents).
        Birth date: student_personal_data.born_date
        """
        personal_info = (
            self.db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == student_id)
            .first()
        )
        if not personal_info:
            return ""
        birth_date = self._parse_birth_date(personal_info.born_date)
        if not birth_date:
            return ""
        today = date.today()
        if birth_date > today:
            return ""
        total_months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
        if today.day < birth_date.day:
            total_months -= 1
        years = total_months // 12
        months = total_months % 12
        if years < 0:
            return ""

        def _month_unit_word(count: int) -> str:
            return "mes" if count == 1 else "meses"

        def _year_unit_word(count: int) -> str:
            return "año" if count == 1 else "años"

        if years == 0:
            if months == 0:
                return ""
            return f"{months} {_month_unit_word(months)}"
        if months:
            return f"{years} {_year_unit_word(years)} {months} {_month_unit_word(months)}"
        return f"{years} {_year_unit_word(years)}"

    def _template_to_dict(self, row: InformalTestTemplateModel) -> Dict[str, Any]:
        return {
            "id": row.id,
            "school_id": row.school_id,
            "name": row.name or "",
            "description": row.description or "",
            "questions": self._questions_for_template(row.id),
            "added_date": _iso(row.added_date),
            "updated_date": _iso(row.updated_date),
        }

    def _normalize_questions(self, questions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for i, q in enumerate(questions or []):
            if not isinstance(q, dict):
                continue
            question_text = str(q.get("question_text") or "").strip()
            question_type = str(q.get("question_type") or "").strip()
            required = bool(q.get("required"))
            options_raw = q.get("options") or []
            if not question_text:
                raise ValueError(f"La pregunta #{i + 1} no tiene texto.")
            if question_type not in _VALID_QUESTION_TYPES:
                raise ValueError(f"Tipo inválido en pregunta #{i + 1}.")
            options: List[Dict[str, str]] = []
            if question_type in ("single_choice", "multiple_choice"):
                if not isinstance(options_raw, list):
                    raise ValueError(f"La pregunta #{i + 1} requiere opciones.")
                for op in options_raw:
                    if not isinstance(op, dict):
                        continue
                    label = str(op.get("label") or "").strip()
                    value = str(op.get("value") or "").strip()
                    if not label and not value:
                        continue
                    options.append({"label": label or value, "value": value or label})
                if len(options) < 2:
                    raise ValueError(f"La pregunta #{i + 1} requiere al menos 2 opciones.")
            out.append(
                {
                    "question_order": i + 1,
                    "question_text": question_text,
                    "question_type": question_type,
                    "required": required,
                    "options_json": json.dumps(options, ensure_ascii=False) if options else None,
                }
            )
        return out

    def get_all(self, school_id: int) -> List[Dict[str, Any]]:
        rows = self._query_templates(school_id).order_by(InformalTestTemplateModel.id.desc()).all()
        return [self._template_to_dict(r) for r in rows]

    def get_by_id(self, id: int, school_id: int) -> Any:
        row = self._query_templates(school_id).filter(InformalTestTemplateModel.id == id).first()
        if not row:
            return {"status": "error", "message": "Plantilla no encontrada.", "data": None}
        return {"status": "success", "data": self._template_to_dict(row)}

    def store(self, payload: Dict[str, Any], school_id: int) -> Any:
        try:
            name = str(payload.get("name") or "").strip()
            description = str(payload.get("description") or "").strip() or None
            student_id = int(payload.get("student_id") or 0) or None
            professional_id = int(payload.get("professional_id") or 0) or 0
            session_course_id = int(payload.get("session_course_id") or 0) or None
            session_period_year = str(payload.get("session_period_year") or "").strip() or None
            if not name:
                return {"status": "error", "message": "El nombre es obligatorio.", "data": None}
            questions = self._normalize_questions(payload.get("questions"))
            now = datetime.utcnow()
            row = InformalTestTemplateModel(
                school_id=school_id,
                name=name,
                description=description,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.flush()
            for q in questions:
                self.db.add(
                    InformalTestTemplateQuestionModel(
                        template_id=row.id,
                        question_order=q["question_order"],
                        question_text=q["question_text"],
                        question_type=q["question_type"],
                        options_json=q["options_json"],
                        required=q["required"],
                        added_date=now,
                        updated_date=now,
                    )
                )
            if student_id:
                student = self.db.query(StudentModel).filter(StudentModel.id == student_id).first()
                if student:
                    latest_folder = (
                        self.db.query(FolderModel)
                        .filter(
                            FolderModel.student_id == student_id,
                            FolderModel.document_id == INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                            FolderModel.deleted_date.is_(None),
                        )
                        .order_by(FolderModel.version_id.desc(), FolderModel.id.desc())
                        .first()
                    )
                    student_academic = (
                        self.db.query(StudentAcademicInfoModel)
                        .filter(StudentAcademicInfoModel.student_id == student_id)
                        .order_by(StudentAcademicInfoModel.id.desc())
                        .first()
                    )
                    resolved_school_id = (
                        int(school_id or 0)
                        or int(getattr(student, "school_id", 0) or 0)
                        or int(getattr(latest_folder, "school_id", 0) or 0)
                    )
                    resolved_course_id = (
                        int(getattr(student, "course_id", 0) or 0)
                        or int(getattr(student_academic, "course_id", 0) or 0)
                        or int(session_course_id or 0)
                        or int(getattr(latest_folder, "course_id", 0) or 0)
                        or None
                    )
                    resolved_period_year = (
                        str(session_period_year).strip() if session_period_year not in (None, "") else None
                    ) or (
                        str(getattr(latest_folder, "period_year", "")).strip() if latest_folder and getattr(latest_folder, "period_year", None) else None
                    ) or str(now.year)
                    empty_submission = InformalTestSubmissionModel(
                        informal_test_template_id=row.id,
                        school_id=resolved_school_id,
                        student_id=student_id,
                        professional_id=professional_id,
                        answers_json=json.dumps({}, ensure_ascii=False),
                        added_date=now,
                        updated_date=now,
                        deleted_date=None,
                    )
                    self.db.add(empty_submission)
                    self.db.flush()
                    last_version = (
                        self.db.query(FolderModel)
                        .filter(
                            FolderModel.student_id == student_id,
                            FolderModel.document_id == INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                        )
                        .order_by(FolderModel.version_id.desc())
                        .first()
                    )
                    new_version = (last_version.version_id + 1) if last_version else 1
                    self.db.add(
                        FolderModel(
                            school_id=resolved_school_id,
                            course_id=resolved_course_id,
                            student_id=student_id,
                            document_id=INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                            version_id=new_version,
                            detail_id=empty_submission.id,
                            professional_id=professional_id,
                            file="informal_test_submission",
                            period_year=resolved_period_year,
                            added_date=now,
                            updated_date=now,
                            deleted_date=None,
                        )
                    )
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Plantilla creada.", "id": row.id}
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, payload: Dict[str, Any], school_id: int) -> Any:
        try:
            row = self._query_templates(school_id).filter(InformalTestTemplateModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Plantilla no encontrada.", "data": None}
            if "name" in payload:
                name = str(payload.get("name") or "").strip()
                if not name:
                    return {"status": "error", "message": "El nombre es obligatorio.", "data": None}
                row.name = name
            if "description" in payload:
                row.description = str(payload.get("description") or "").strip() or None
            if "questions" in payload:
                questions = self._normalize_questions(payload.get("questions"))
                self.db.query(InformalTestTemplateQuestionModel).filter(
                    InformalTestTemplateQuestionModel.template_id == row.id
                ).delete(synchronize_session=False)
                now = datetime.utcnow()
                for q in questions:
                    self.db.add(
                        InformalTestTemplateQuestionModel(
                            template_id=row.id,
                            question_order=q["question_order"],
                            question_text=q["question_text"],
                            question_type=q["question_type"],
                            options_json=q["options_json"],
                            required=q["required"],
                            added_date=now,
                            updated_date=now,
                        )
                    )
            row.updated_date = datetime.utcnow()
            self.db.commit()
            return {"status": "success", "message": "Plantilla actualizada.", "id": row.id}
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def delete(self, id: int, school_id: int) -> Any:
        try:
            row = self._query_templates(school_id).filter(InformalTestTemplateModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Plantilla no encontrada.", "data": None}
            row.deleted_date = datetime.utcnow()
            row.updated_date = datetime.utcnow()
            self.db.commit()
            return {"status": "success", "message": "Plantilla eliminada."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def submit_answers(
        self,
        template_id: int,
        school_id: int,
        student_id: int,
        professional_id: Optional[int],
        answers: Dict[str, Any],
        session_course_id: Optional[int] = None,
        session_period_year: Optional[str] = None,
    ) -> Any:
        try:
            student = (
                self.db.query(StudentModel)
                .filter(StudentModel.id == student_id)
                .first()
            )
            if not student:
                return {"status": "error", "message": "Estudiante no encontrado.", "data": None}

            latest_folder = (
                self.db.query(FolderModel)
                .filter(
                    FolderModel.student_id == student_id,
                    FolderModel.deleted_date.is_(None),
                )
                .order_by(FolderModel.version_id.desc(), FolderModel.id.desc())
                .first()
            )
            student_academic = (
                self.db.query(StudentAcademicInfoModel)
                .filter(StudentAcademicInfoModel.student_id == student_id)
                .order_by(StudentAcademicInfoModel.id.desc())
                .first()
            )

            resolved_school_id = (
                int(school_id or 0)
                or int(getattr(student, "school_id", 0) or 0)
                or int(getattr(latest_folder, "school_id", 0) or 0)
            )
            resolved_course_id = (
                int(getattr(student, "course_id", 0) or 0)
                or int(getattr(student_academic, "course_id", 0) or 0)
                or int(session_course_id or 0)
                or int(getattr(latest_folder, "course_id", 0) or 0)
                or None
            )
            resolved_period_year = (
                str(session_period_year).strip() if session_period_year not in (None, "") else None
            ) or (
                str(getattr(latest_folder, "period_year", "")).strip() if latest_folder and getattr(latest_folder, "period_year", None) else None
            ) or str(datetime.utcnow().year)
            resolved_professional_id = int(professional_id or 0) or 0

            template = self._query_templates(resolved_school_id).filter(InformalTestTemplateModel.id == template_id).first()
            if not template:
                return {"status": "error", "message": "Plantilla no encontrada.", "data": None}

            now = datetime.utcnow()
            payload = answers if isinstance(answers, dict) else {}
            row = (
                self.db.query(InformalTestSubmissionModel)
                .filter(
                    InformalTestSubmissionModel.informal_test_template_id == template_id,
                    InformalTestSubmissionModel.school_id == resolved_school_id,
                    InformalTestSubmissionModel.student_id == student_id,
                    InformalTestSubmissionModel.deleted_date.is_(None),
                )
                .order_by(InformalTestSubmissionModel.id.desc())
                .first()
            )
            if row:
                row.professional_id = resolved_professional_id
                row.answers_json = json.dumps(payload, ensure_ascii=False)
                row.updated_date = now
            else:
                row = InformalTestSubmissionModel(
                    informal_test_template_id=template_id,
                    school_id=resolved_school_id,
                    student_id=student_id,
                    professional_id=resolved_professional_id,
                    answers_json=json.dumps(payload, ensure_ascii=False),
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(row)
                self.db.flush()

            # Registrar también en folders para trazabilidad por estudiante.
            linked_folder = (
                self.db.query(FolderModel)
                .filter(
                    FolderModel.student_id == student_id,
                    FolderModel.document_id == INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                    FolderModel.detail_id == row.id,
                    FolderModel.deleted_date.is_(None),
                )
                .order_by(FolderModel.version_id.desc(), FolderModel.id.desc())
                .first()
            )
            if linked_folder:
                linked_folder.school_id = resolved_school_id
                linked_folder.course_id = resolved_course_id
                linked_folder.professional_id = resolved_professional_id
                linked_folder.period_year = resolved_period_year
                linked_folder.file = "informal_test_submission"
                linked_folder.updated_date = now
            else:
                last_version = (
                    self.db.query(FolderModel)
                    .filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                    )
                    .order_by(FolderModel.version_id.desc())
                    .first()
                )
                new_version = (last_version.version_id + 1) if last_version else 1
                folder_row = FolderModel(
                    school_id=resolved_school_id,
                    course_id=resolved_course_id,
                    student_id=student_id,
                    document_id=INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                    version_id=new_version,
                    detail_id=row.id,
                    professional_id=resolved_professional_id,
                    file="informal_test_submission",
                    period_year=resolved_period_year,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(folder_row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Respuestas guardadas.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def get_student_submissions(self, school_id: int, student_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(InformalTestSubmissionModel, InformalTestTemplateModel)
            .join(
                InformalTestTemplateModel,
                InformalTestTemplateModel.id == InformalTestSubmissionModel.informal_test_template_id,
            )
            .join(
                FolderModel,
                FolderModel.detail_id == InformalTestSubmissionModel.id,
            )
            .filter(
                InformalTestSubmissionModel.school_id == school_id,
                InformalTestSubmissionModel.student_id == student_id,
                InformalTestSubmissionModel.deleted_date.is_(None),
                InformalTestTemplateModel.deleted_date.is_(None),
                FolderModel.student_id == student_id,
                FolderModel.document_id == INFORMAL_TEST_FOLDER_DOCUMENT_ID,
                FolderModel.deleted_date.is_(None),
            )
            .order_by(InformalTestSubmissionModel.id.desc())
            .all()
        )
        latest_by_template: Dict[int, Dict[str, Any]] = {}
        for submission, template in rows:
            t_id = int(template.id)
            if t_id in latest_by_template:
                continue
            latest_by_template[t_id] = {
                "submission_id": submission.id,
                "template_id": template.id,
                "name": template.name or f"Prueba {template.id}",
                "description": template.description or "",
                "added_date": _iso(submission.added_date),
            }
        return list(latest_by_template.values())

    def get_latest_submission_answers(self, school_id: int, template_id: int, student_id: int) -> Dict[str, Any]:
        row = (
            self.db.query(InformalTestSubmissionModel)
            .filter(
                InformalTestSubmissionModel.school_id == school_id,
                InformalTestSubmissionModel.informal_test_template_id == template_id,
                InformalTestSubmissionModel.student_id == student_id,
                InformalTestSubmissionModel.deleted_date.is_(None),
            )
            .order_by(InformalTestSubmissionModel.id.desc())
            .first()
        )
        if not row:
            return {"status": "success", "data": None}
        try:
            answers = json.loads(row.answers_json or "{}")
        except (json.JSONDecodeError, TypeError):
            answers = {}
        if not isinstance(answers, dict):
            answers = {}
        return {
            "status": "success",
            "data": {
                "id": row.id,
                "answers": answers,
                "updated_date": _iso(row.updated_date),
            },
        }

    def generate_submission_pdf(self, school_id: int, template_id: int, student_id: int) -> Dict[str, Any]:
        """
        Genera PDF de la última submission del estudiante para la plantilla.
        No exige que school_id coincida con el del estudiante: se toma el de la submission (o respaldo).
        """
        submission = (
            self.db.query(InformalTestSubmissionModel)
            .filter(
                InformalTestSubmissionModel.informal_test_template_id == template_id,
                InformalTestSubmissionModel.student_id == student_id,
                InformalTestSubmissionModel.deleted_date.is_(None),
            )
            .order_by(InformalTestSubmissionModel.id.desc())
            .first()
        )
        if not submission:
            return {"status": "error", "message": "No se encontraron respuestas para generar el documento.", "data": None}

        resolved_school = int(submission.school_id or 0) or int(school_id or 0)
        if not resolved_school:
            return {"status": "error", "message": "No se pudo determinar el colegio de la evaluación.", "data": None}

        template_row = (
            self._query_templates(resolved_school)
            .filter(InformalTestTemplateModel.id == template_id)
            .first()
        )
        if not template_row:
            return {"status": "error", "message": "Plantilla no encontrada.", "data": None}

        try:
            answers = json.loads(submission.answers_json or "{}")
        except (json.JSONDecodeError, TypeError):
            answers = {}
        if not isinstance(answers, dict):
            answers = {}

        student_name = self._get_student_display_name(student_id)
        student_identification_number = self._get_student_identification_number(student_id)
        student_age = self._format_student_age_years_months(student_id)
        header_title = (template_row.name or "").strip() or "Documento"

        questions = self._questions_for_template(template_id)

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp_path = Path(tmp.name)
            tmp.close()

            # Mismo criterio visual que documents_class (PDF desde cero / Estado de avance)
            doc = SimpleDocTemplate(
                str(tmp_path),
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "InformalPdfTitle",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#000000"),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
            section_style = ParagraphStyle(
                "InformalPdfSection",
                parent=styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#000000"),
                spaceAfter=12,
                spaceBefore=15,
                fontName="Helvetica-Bold",
                alignment=TA_LEFT,
                backColor=colors.HexColor("#E8E8E8"),
                borderPadding=6,
            )
            normal_style = ParagraphStyle(
                "InformalPdfNormal",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#000000"),
                alignment=TA_JUSTIFY,
                leading=14,
            )

            def _table_style() -> TableStyle:
                return TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )

            col_widths = [5 * cm, 11 * cm]
            story = []

            story.append(Paragraph(_reportlab_paragraph_text(header_title), title_style))
            story.append(Spacer(1, 0.3 * inch))

            story.append(Paragraph("I. IDENTIFICACIÓN", section_style))
            story.append(Spacer(1, 0.15 * inch))

            meta_rows: List[Any] = [
                ["RUT:", Paragraph(_reportlab_paragraph_text(student_identification_number or "-"), normal_style)],
                ["Estudiante:", Paragraph(_reportlab_paragraph_text(student_name or "-"), normal_style)],
                [
                    "Edad:",
                    Paragraph(_reportlab_paragraph_text(student_age or "-"), normal_style),
                ],
                [
                    "Fecha:",
                    Paragraph(
                        _reportlab_paragraph_text(datetime.now().strftime("%d/%m/%Y %H:%M")),
                        normal_style,
                    ),
                ],
            ]
            meta_table = Table(meta_rows, colWidths=col_widths)
            meta_table.setStyle(_table_style())
            story.append(meta_table)
            story.append(Spacer(1, 0.25 * inch))

            story.append(Paragraph("II. RESPUESTAS DEL CUESTIONARIO", section_style))
            story.append(Spacer(1, 0.15 * inch))

            question_rows: List[Any] = []
            if not questions:
                question_rows.append(
                    [
                        "Nota:",
                        Paragraph(_reportlab_paragraph_text("Esta plantilla no tiene preguntas registradas."), normal_style),
                    ]
                )
            for idx, question in enumerate(questions, 1):
                key = str(question.get("id") or f"q_{idx}")
                raw = answers.get(key)
                if isinstance(raw, list):
                    value = ", ".join([str(x) for x in raw if str(x).strip()]) or "-"
                else:
                    value = str(raw).strip() if raw is not None and str(raw).strip() else "-"
                question_text = (question.get("question_text") or "").strip() or "-"
                question_rows.append(
                    [
                        f"Pregunta {idx}:",
                        Paragraph(_reportlab_paragraph_text(question_text), normal_style),
                    ]
                )
                question_rows.append(
                    [
                        "Respuesta:",
                        Paragraph(_reportlab_paragraph_text(value), normal_style),
                    ]
                )

            questions_table = Table(question_rows, colWidths=col_widths)
            questions_table.setStyle(_table_style())
            story.append(questions_table)

            doc.build(story)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al generar el PDF: {str(e)}",
                "http_status": 500,
                "data": None,
            }

        filename = f"informal_test_{student_id}_{template_id}.pdf"
        return {
            "status": "success",
            "data": {
                "file_path": str(tmp_path),
                "filename": filename,
            },
        }
