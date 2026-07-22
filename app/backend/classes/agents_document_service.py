"""Agents document generation: Word/PDF template → file → folders table."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.documents_class import DocumentsClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.core.config import settings
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel
from app.backend.utils.agents_familia_pie360 import (
    FAMILIA_DOCUMENT_ID,
    build_familia_pie360_context,
    is_familia_document,
    merge_pie360_fallback_into_replacements,
)
from app.backend.utils import agents_storage as storage
from app.backend.utils.agents_familia_fill import fill_familia_template, validate_docx
from app.backend.utils.agents_family_report_store import (
    link_folder_to_family_report,
    persist_family_report_from_agent,
)

_FAMILIA_DOCUMENT_ID = FAMILIA_DOCUMENT_ID
_WORD_PLACEHOLDERS = (
    "Haz clic o pulse aquí para escribir texto.",
    "Click or tap here to enter text.",
)


def _student_context(db: Session, student_id: int, document_id: int | None = None) -> dict[str, Any]:
    if is_familia_document(document_id):
        return build_familia_pie360_context(db, student_id)
    return _basic_student_context(db, student_id)


def _basic_student_context(db: Session, student_id: int) -> dict[str, Any]:
    from app.backend.db.models.pie_core import (
        StudentAcademicInfoModel,
        StudentModel,
        StudentPersonalInfoModel,
    )

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


def _resolve_template_absolute(template: AgentDocumentTemplateModel) -> Path | None:
    """Resuelve la plantilla en disco; prueba rutas alternativas si la registrada falló."""
    rel = (template.template_path or "").replace("\\", "/").lstrip("/")
    ext = (template.format_type or "docx").lower()
    if ext not in {"docx", "pdf"}:
        ext = "docx"
    doc_id = int(template.document_id)

    roots = [storage.files_dir()]
    try:
        alt = Path(settings.files_dir)
        if alt.resolve() != storage.files_dir():
            roots.append(alt)
    except Exception:
        pass

    candidates: list[Path] = []
    for root in roots:
        if rel:
            candidates.append(root / rel)
        parts = [p for p in rel.split("/") if p]
        # agents / c{N} / AgentName / documentos / {id} / formato.ext
        if len(parts) >= 3:
            agent_root = root / parts[0] / parts[1] / parts[2]
            candidates.append(agent_root / "documentos" / str(doc_id) / f"formato.{ext}")

    agents_root = storage.files_dir() / "agents"
    if agents_root.is_dir():
        for customer_dir in agents_root.iterdir():
            if not customer_dir.is_dir():
                continue
            for agent_dir in customer_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                hit = agent_dir / "documentos" / str(doc_id) / f"formato.{ext}"
                if hit.is_file():
                    candidates.append(hit)

    seen: set[str] = set()
    for cand in candidates:
        try:
            key = str(cand).lower()
            if key in seen:
                continue
            seen.add(key)
            if cand.is_file():
                return cand.resolve()
        except Exception:
            continue
    return None


def generate_and_save_document(
    db: Session,
    template: AgentDocumentTemplateModel,
    student_id: int,
    replacements: dict[str, str],
) -> dict[str, Any]:
    expected = (storage.files_dir() / (template.template_path or "").replace("\\", "/").lstrip("/"))
    template_abs = _resolve_template_absolute(template)
    if template_abs is None:
        return {
            "status": "error",
            "message": (
                f"No se encontró la plantilla en el servidor "
                f"({template.document_name}, document_id={template.document_id}). "
                f"Ruta esperada: {expected}. "
                "Ve a Agente → Documentos, selecciona ese documento y vuelve a subir "
                "el modelo (.docx o .pdf). Si ya la subiste, abre un chat nuevo e inténtalo otra vez."
            ),
            "http_status": 404,
        }

    # Si se encontró por fallback, alinea template_path para próximos usos.
    try:
        rel_ok = str(template_abs.relative_to(storage.files_dir())).replace("\\", "/")
        if rel_ok and rel_ok != (template.template_path or "").replace("\\", "/"):
            template.template_path = rel_ok
            db.add(template)
            db.commit()
    except Exception:
        pass

    student_ctx = _student_context(db, student_id, int(template.document_id))
    if is_familia_document(int(template.document_id)):
        replacements = merge_pie360_fallback_into_replacements(replacements, student_ctx)
    output_dir = Path(settings.files_dir) / "system" / "students"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_student = (student_ctx.get("student_fullname") or "estudiante").replace(" ", "_")
    ext = template.format_type.lower()
    filename = f"agentv2_{template.document_id}_{student_id}_{uuid.uuid4().hex[:8]}.{ext}"
    output_path = output_dir / filename

    if ext == "docx":
        if int(template.document_id) == _FAMILIA_DOCUMENT_ID:
            result = fill_familia_template(
                template_abs,
                output_path,
                replacements,
                student_context=student_ctx,
            )
        else:
            shutil.copy2(template_abs, output_path)
            result = DocumentsClass.fill_docx_form(
                str(output_path),
                replacements,
                str(output_path),
                remove_literal_strings=list(_WORD_PLACEHOLDERS),
                preserve_empty_content_controls=True,
            )
            if result.get("status") != "error" and not validate_docx(output_path):
                result = {
                    "status": "error",
                    "message": "The generated Word file is corrupt. Check the template.",
                }
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
        return {"status": "error", "message": f"Unsupported format: {ext}"}

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

    family_report_id: int | None = None
    if int(template.document_id) == _FAMILIA_DOCUMENT_ID:
        fr_result = persist_family_report_from_agent(
            db,
            student_id,
            replacements,
            student_context=student_ctx,
        )
        if fr_result.get("status") == "error":
            return {
                "status": "error",
                "message": (
                    "The Word file was generated but the form could not be saved to the "
                    f"student record: {fr_result.get('message', 'unknown error')}"
                ),
                "filename": filename,
            }
        family_report_id = fr_result.get("id")
        link_folder_to_family_report(db, folder_result.get("id"), family_report_id)

    folder_id = folder_result.get("id") if isinstance(folder_result, dict) else None
    download_url = f"/files/system/students/{filename}" if filename else None
    return {
        "status": "success",
        "message": "Document generated and saved.",
        "filename": filename,
        "downloadUrl": download_url,
        "folderId": folder_id,
        "documentId": template.document_id,
        "documentName": template.document_name,
        "formatType": template.format_type,
        "studentId": student_id,
        "familyReportId": family_report_id,
    }
