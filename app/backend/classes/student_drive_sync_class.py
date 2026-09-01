"""Persistencia y ejecución de la cola Drive para documentos de estudiantes."""

from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import (
    CourseModel,
    DocumentModel,
    FolderModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentDriveSyncJobModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from app.backend.utils.google_drive_storage import upload_student_document_tree


logger = logging.getLogger(__name__)
_ACTIVE_STATUSES = ("pending", "retry")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def student_files_dir() -> Path:
    path = Path(settings.files_dir) / "system" / "students"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _relative_student_file_path(file_path: str | Path) -> str:
    """Guarda una referencia estable relativa a FILES_DIR siempre que sea posible."""
    raw = Path(file_path)
    if raw.is_absolute():
        try:
            return raw.resolve().relative_to(Path(settings.files_dir).resolve()).as_posix()
        except ValueError:
            return raw.as_posix()
    normalized = raw.as_posix().lstrip("/")
    if normalized.startswith("files/"):
        normalized = normalized[6:]
    if "/" not in normalized:
        return f"system/students/{Path(normalized).name}"
    return normalized


class StudentDriveSyncClass:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(
        self,
        *,
        folder_id: int,
        student_id: int,
        document_id: int,
        file_path: str | Path,
        mime_type: str | None = None,
    ) -> StudentDriveSyncJobModel:
        """Encola solo archivos creados después de instalar esta integración."""
        relative_path = _relative_student_file_path(file_path)
        now = _utcnow()
        existing = (
            self.db.query(StudentDriveSyncJobModel)
            .filter(
                StudentDriveSyncJobModel.folder_id == int(folder_id),
                StudentDriveSyncJobModel.file_path == relative_path,
                StudentDriveSyncJobModel.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(StudentDriveSyncJobModel.id.desc())
            .first()
        )
        if existing:
            existing.mime_type = mime_type or existing.mime_type
            existing.status = "pending"
            existing.next_attempt_at = now
            existing.last_error = None
            existing.updated_at = now
            job = existing
        else:
            job = StudentDriveSyncJobModel(
                folder_id=int(folder_id),
                student_id=int(student_id),
                document_id=int(document_id),
                file_path=relative_path,
                mime_type=mime_type,
                status="pending",
                attempts=0,
                next_attempt_at=now,
                created_at=now,
                updated_at=now,
            )
            self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def claim_due_job(self) -> int | None:
        """Reclama una tarea con bloqueo de fila; es seguro con varios workers."""
        now = _utcnow()
        stale_at = now - timedelta(minutes=15)
        query = (
            self.db.query(StudentDriveSyncJobModel)
            .filter(
                or_(
                    (
                        StudentDriveSyncJobModel.status.in_(_ACTIVE_STATUSES)
                        & (StudentDriveSyncJobModel.next_attempt_at <= now)
                    ),
                    (
                        (StudentDriveSyncJobModel.status == "processing")
                        & (StudentDriveSyncJobModel.locked_at <= stale_at)
                    ),
                )
            )
            .order_by(
                StudentDriveSyncJobModel.next_attempt_at.asc(),
                StudentDriveSyncJobModel.id.asc(),
            )
        )
        try:
            job = query.with_for_update(skip_locked=True).first()
        except Exception:
            self.db.rollback()
            job = query.with_for_update().first()
        if not job:
            self.db.rollback()
            return None
        job.status = "processing"
        job.locked_at = now
        job.updated_at = now
        self.db.commit()
        return int(job.id)

    def process(self, job_id: int) -> dict[str, Any]:
        job = (
            self.db.query(StudentDriveSyncJobModel)
            .filter(StudentDriveSyncJobModel.id == int(job_id))
            .first()
        )
        if not job:
            return {"ok": False, "message": "Tarea de Drive no encontrada"}

        try:
            metadata = self._metadata(job)
            local_path = self._absolute_file(job.file_path)
            data = local_path.read_bytes()
            extension = local_path.suffix.lower().lstrip(".") or "bin"
            payload = upload_student_document_tree(
                db=self.db,
                customer_id=metadata["customer_id"],
                school_name=metadata["school_name"],
                year=metadata["year"],
                course_name=metadata["course_name"],
                student_rut=metadata["student_rut"],
                document_type_name=metadata["document_type_name"],
                data=data,
                file_extension=extension,
                mime_type=job.mime_type or mimetypes.guess_type(local_path.name)[0],
            )
        except Exception as exc:
            self.db.rollback()
            job = (
                self.db.query(StudentDriveSyncJobModel)
                .filter(StudentDriveSyncJobModel.id == int(job_id))
                .first()
            )
            if job:
                attempts = int(job.attempts or 0) + 1
                delay_minutes = min(360, 2 ** min(attempts, 8))
                job.status = "retry"
                job.attempts = attempts
                job.next_attempt_at = _utcnow() + timedelta(minutes=delay_minutes)
                job.locked_at = None
                job.last_error = str(exc)[:4000]
                job.updated_at = _utcnow()
                self.db.commit()
            logger.warning("Drive pendiente para tarea %s: %s", job_id, exc)
            return {"ok": False, "message": str(exc)}

        job.status = "completed"
        job.attempts = int(job.attempts or 0) + 1
        job.drive_file_id = payload.get("file_id")
        job.drive_path = payload.get("drive_path")
        job.last_error = None
        job.locked_at = None
        job.completed_at = _utcnow()
        job.updated_at = _utcnow()
        self.db.commit()
        return {"ok": True, "data": payload}

    @staticmethod
    def _absolute_file(file_path: str) -> Path:
        raw = Path(file_path)
        candidates = [raw] if raw.is_absolute() else [
            Path(settings.files_dir) / raw,
            student_files_dir() / raw.name,
            Path(file_path),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        raise FileNotFoundError(f"Archivo local no encontrado: {file_path}")

    def _metadata(self, job: StudentDriveSyncJobModel) -> dict[str, Any]:
        folder = (
            self.db.query(FolderModel)
            .filter(FolderModel.id == int(job.folder_id))
            .first()
        )
        student = (
            self.db.query(StudentModel)
            .filter(StudentModel.id == int(job.student_id))
            .first()
        )
        document = (
            self.db.query(DocumentModel)
            .filter(DocumentModel.id == int(job.document_id))
            .first()
        )
        if not folder or not student or not document:
            raise ValueError("Faltan datos del documento, estudiante o carpeta.")

        academic = (
            self.db.query(StudentAcademicInfoModel)
            .filter(StudentAcademicInfoModel.student_id == int(student.id))
            .order_by(StudentAcademicInfoModel.id.desc())
            .first()
        )
        school_id = int(folder.school_id or student.school_id or 0)
        course_id = int(folder.course_id or getattr(academic, "course_id", 0) or 0)
        school = (
            self.db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
            if school_id
            else None
        )
        course = (
            self.db.query(CourseModel).filter(CourseModel.id == course_id).first()
            if course_id
            else None
        )
        year_raw = folder.period_year or getattr(course, "period_year", None) or student.period_year
        personal = (
            self.db.query(StudentPersonalInfoModel)
            .filter(StudentPersonalInfoModel.student_id == int(student.id))
            .order_by(StudentPersonalInfoModel.id.desc())
            .first()
        )
        rut = getattr(personal, "identification_number", None) or student.identification_number
        if not school or not int(school.customer_id or 0):
            raise ValueError("No se pudo determinar el liceo o cliente del estudiante.")
        if not course:
            raise ValueError("No se pudo determinar el curso del estudiante.")
        if not year_raw or not str(year_raw).strip().isdigit():
            raise ValueError("No se pudo determinar el año escolar del documento.")
        if not rut:
            raise ValueError("El estudiante no tiene RUT registrado.")

        return {
            "customer_id": int(school.customer_id),
            "school_name": school.school_name or f"Liceo {school.id}",
            "year": int(str(year_raw).strip()),
            "course_name": course.course_name or f"Curso {course.id}",
            "student_rut": str(rut),
            "document_type_name": document.document or f"Documento {document.id}",
        }
