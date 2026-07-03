"""Generación de documentos Agent v2: plantilla Word/PDF → archivo → tabla folders."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.core.config import settings
from app.backend.db.models.agent_v2_documents import AgentV2DocumentTemplateModel
from app.backend.db.models.pie_core import (
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from app.backend.utils import agent_v2_storage as storage
from app.backend.utils.agent_v2_template_inspector import fields_from_json


def _student_context(db: Session, student_id: int) -> dict[str, Any]:
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .first()
    )
    academic = (
        db.query(StudentAcademicInfoModel)
        .filter(StudentAcademicInfoModel.student_id == student_id)
        .order_by(StudentAcademicInfoModel.id.desc())
        .first()
    )
    names = (personal.names or "").strip() if personal else ""
    father = (personal.father_lastname or "").strip() if personal else ""
    mother = (personal.mother_lastname or "").strip() if personal else ""
    full_name = f"{names} {father} {mother}".strip()
    return {
        "student_id": student_id,
        "student_name": names,
        "student_fullname": full_name,
        "identification_number": (personal.identification_number or "").strip() if personal else "",
        "school_id": getattr(student, "school_id", None) if student else None,
        "course_id": getattr(academic, "course_id", None) if academic else None,
        "period_year": getattr(student, "period_year", None) if student else None,
    }


def generate_and_save_document(
    db: Session,
    template: AgentV2DocumentTemplateModel,
    student_id: int,
    replacements: dict[str, str],
) -> dict[str, Any]:
    template_abs = (storage.files_dir() / template.template_path).resolve()
    if not template_abs.is_file():
        return {"status": "error", "message": "Plantilla no encontrada en disco."}

    student_ctx = _student_context(db, student_id)
    output_dir = Path(settings.files_dir) / "system" / "students"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_student = (student_ctx.get("student_fullname") or "estudiante").replace(" ", "_")
    ext = template.format_type.lower()
    filename = f"agentv2_{template.document_id}_{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
    output_path = output_dir / filename

    if ext == "docx":
        result = DocumentsClass.fill_docx_form(
            str(template_abs),
            replacements,
            str(output_path),
        )
        if result.get("status") == "error":
            return result
    elif ext == "pdf":
        tag_map: dict[str, str] = {}
        for key, value in replacements.items():
            val = str(value) if value is not None else ""
            tag_map[f"{{{key}}}"] = val
            tag_map[f"[{key}]"] = val
            tag_map[f"<<{key}>>"] = val
            tag_map[f"{{{{{key}}}}}"] = val
        result = DocumentsClass._generate_pdf_from_template(
            str(template_abs),
            tag_map,
            int(template.document_id),
            student_ctx,
            str(output_dir),
        )
        if result.get("status") == "error":
            return result
        filename = result.get("filename") or filename
    else:
        return {"status": "error", "message": f"Formato no soportado: {ext}"}

    folder_result = FolderClass(db).store(
        student_id=student_id,
        document_id=int(template.document_id),
        file_path=filename,
        school_id=student_ctx.get("school_id"),
        course_id=student_ctx.get("course_id"),
        period_year=student_ctx.get("period_year"),
    )
    if isinstance(folder_result, dict) and folder_result.get("status") == "error":
        return folder_result

    return {
        "status": "success",
        "message": "Documento generado y guardado.",
        "filename": filename,
        "documentId": template.document_id,
        "documentName": template.document_name,
        "formatType": template.format_type,
        "studentId": student_id,
    }


def build_fields_prompt(template: AgentV2DocumentTemplateModel) -> str:
    fields = fields_from_json(template.detected_fields)
    if not fields:
        return "No hay campos detectados en la plantilla."
    lines = [f"- {field}" for field in fields]
    return "\n".join(lines)
