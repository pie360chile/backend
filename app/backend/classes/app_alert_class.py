"""CRUD y reglas para la tabla `alerts` (campana / notificaciones revisables)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.db.models import AlertModel, CourseModel, ProfessionalDocumentAssignmentModel

REF_KIND_PDA = "professional_document_assignment"
REF_KIND_SCOPE = "assignment_scope"
ALERT_TYPE_DOCUMENT_PENDING = "document_assignment_pending"
ALERT_TYPE_SCOPE_SUMMARY = "document_assignments_pending"


def scope_reference_id(period_year: int, course_id: int, professional_id: int) -> int:
    """ID estable y único por (año escolar, curso, profesional) para una sola fila de alerta resumen."""
    return int(period_year) * 10**12 + int(course_id) * 10**6 + int(professional_id)


class AppAlertClass:
    def __init__(self, db: Session):
        self.db = db

    def _school_id_for_course(self, course_id: int) -> Optional[int]:
        """Obtiene school_id desde `courses` si no viene en el request."""
        try:
            cid = int(course_id)
            row = self.db.query(CourseModel).filter(CourseModel.id == cid).first()
            if row is None or row.school_id is None:
                return None
            return int(row.school_id)
        except Exception:
            return None

    def delete_alerts_for_assignment_scope(
        self,
        *,
        period_year: int,
        course_id: int,
        professional_id: int,
    ) -> None:
        """Quita todas las alertas de ese curso/período/profesional (resumen y legado por fila)."""
        py, cid, pid = int(period_year), int(course_id), int(professional_id)
        self.db.query(AlertModel).filter(
            AlertModel.period_year == py,
            AlertModel.course_id == cid,
            AlertModel.professional_id == pid,
        ).delete(synchronize_session=False)

    def upsert_scope_summary(
        self,
        *,
        period_year: int,
        course_id: int,
        professional_id: int,
        pending_count: int,
        school_id: Optional[int] = None,
    ) -> None:
        """Una sola alerta por (período, curso, profesional) con el total de documentos pendientes."""
        py, cid, pid = int(period_year), int(course_id), int(professional_id)
        n = int(pending_count)
        # Elimina alertas antiguas (una por fila de asignación); el resumen usa REF_KIND_SCOPE
        self.db.query(AlertModel).filter(
            AlertModel.period_year == py,
            AlertModel.course_id == cid,
            AlertModel.professional_id == pid,
            AlertModel.reference_kind == REF_KIND_PDA,
        ).delete(synchronize_session=False)
        ref_id = scope_reference_id(py, cid, pid)
        row = (
            self.db.query(AlertModel)
            .filter(
                AlertModel.reference_kind == REF_KIND_SCOPE,
                AlertModel.reference_id == ref_id,
            )
            .first()
        )
        if n <= 0:
            if row:
                self.db.delete(row)
            return

        resolved_school_id = school_id if school_id is not None else self._school_id_for_course(cid)

        if n == 1:
            message = "Tienes 1 documento asignado pendiente de subir a la carpeta del estudiante."
        else:
            message = f"Tienes {n} documentos asignados pendientes de subir a la carpeta del estudiante."
        title = "Documentos pendientes por cargar"
        extra = {
            "pending_count": n,
            "period_year": py,
            "course_id": cid,
            "professional_id": pid,
        }
        if resolved_school_id is not None:
            extra["school_id"] = resolved_school_id
        now = datetime.now()
        if row:
            row.alert_type = ALERT_TYPE_SCOPE_SUMMARY
            row.title = title
            row.message = message
            row.extra = json.dumps(extra, ensure_ascii=False)
            row.status_id = 0
            row.updated_date = now
            if resolved_school_id is not None:
                row.school_id = resolved_school_id
        else:
            self.db.add(
                AlertModel(
                    school_id=resolved_school_id,
                    professional_id=pid,
                    course_id=cid,
                    period_year=py,
                    alert_type=ALERT_TYPE_SCOPE_SUMMARY,
                    title=title,
                    message=message,
                    reference_kind=REF_KIND_SCOPE,
                    reference_id=ref_id,
                    status_id=0,
                    extra=json.dumps(extra, ensure_ascii=False),
                    added_date=now,
                    updated_date=now,
                )
            )

    def sync_scope_summary_from_assignments(
        self,
        *,
        period_year: int,
        course_id: int,
        professional_id: int,
    ) -> None:
        """Recalcula el resumen según filas pendientes en professional_document_assignments (p.ej. tras subir a carpeta)."""
        self.db.flush()
        py, cid, pid = int(period_year), int(course_id), int(professional_id)
        n = (
            self.db.query(ProfessionalDocumentAssignmentModel)
            .filter(
                ProfessionalDocumentAssignmentModel.period_year == py,
                ProfessionalDocumentAssignmentModel.course_id == cid,
                ProfessionalDocumentAssignmentModel.professional_id == pid,
                ProfessionalDocumentAssignmentModel.status_id == 0,
            )
            .count()
        )
        self.upsert_scope_summary(
            period_year=py,
            course_id=cid,
            professional_id=pid,
            pending_count=n,
        )

    def count_unread(self, professional_id: int) -> Dict[str, Any]:
        try:
            pid = int(professional_id)
            n = (
                self.db.query(AlertModel)
                .filter(AlertModel.professional_id == pid, AlertModel.status_id == 0)
                .count()
            )
            return {"status": "success", "count": n}
        except Exception as e:
            return {"status": "error", "message": str(e), "count": 0}

    def has_any_alert_for_professional(self, professional_id: int) -> bool:
        """True si ya existe al menos una alerta para el profesional (migración / uso de tabla)."""
        try:
            pid = int(professional_id)
            c = (
                self.db.query(AlertModel)
                .filter(AlertModel.professional_id == pid)
                .count()
            )
            return c > 0
        except Exception:
            return False

    def list_alerts(
        self,
        *,
        professional_id: int,
        status_id: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        try:
            pid = int(professional_id)
            q = self.db.query(AlertModel).filter(AlertModel.professional_id == pid)
            if status_id is not None:
                q = q.filter(AlertModel.status_id == int(status_id))
            rows = q.order_by(AlertModel.id.desc()).limit(min(int(limit), 500)).all()
            data: List[Dict[str, Any]] = []
            for r in rows:
                extra_obj: Any = None
                if r.extra:
                    try:
                        extra_obj = json.loads(r.extra)
                    except Exception:
                        extra_obj = r.extra
                added = r.added_date.isoformat() if r.added_date else None
                upd = r.updated_date.isoformat() if r.updated_date else None
                st = int(r.status_id or 0)
                data.append(
                    {
                        "id": int(r.id),
                        "school_id": r.school_id,
                        "professional_id": int(r.professional_id),
                        "course_id": int(r.course_id),
                        "period_year": int(r.period_year),
                        "alert_type": r.alert_type,
                        "title": r.title,
                        "message": r.message,
                        "reference_kind": r.reference_kind,
                        "reference_id": int(r.reference_id),
                        "status_id": st,
                        "extra": extra_obj,
                        "added_date": added,
                        "updated_date": upd,
                        # Compat. front antiguo
                        "created_at": added,
                        "reviewed_at": upd if st == 1 else None,
                    }
                )
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def mark_reviewed(self, alert_id: int, professional_id: int) -> Dict[str, Any]:
        """Marca una alerta como revisada (solo si pertenece al profesional)."""
        try:
            pid = int(professional_id)
            row = (
                self.db.query(AlertModel)
                .filter(AlertModel.id == int(alert_id), AlertModel.professional_id == pid)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Alerta no encontrada."}
            if int(row.status_id or 0) == 1:
                return {"status": "success", "message": "Ya estaba revisada."}
            row.status_id = 1
            row.updated_date = datetime.now()
            self.db.flush()
            return {"status": "success", "message": "Actualizado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def mark_all_reviewed_for_professional(self, professional_id: int) -> Dict[str, Any]:
        """Marca todas las alertas no revisadas del profesional (p. ej. al abrir la campana)."""
        try:
            pid = int(professional_id)
            now = datetime.now()
            rows = (
                self.db.query(AlertModel)
                .filter(AlertModel.professional_id == pid, AlertModel.status_id == 0)
                .all()
            )
            for row in rows:
                row.status_id = 1
                row.updated_date = now
            self.db.flush()
            return {"status": "success", "updated": len(rows)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
