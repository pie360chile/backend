"""
Asignaciones documento–estudiante–profesional–curso por período.
Al subir archivo a carpeta (folders), status_id pasa a 1 si coincide tipo/catálogo.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.backend.classes.app_alert_class import AppAlertClass
from app.backend.db.models import (
    ProfessionalDocumentAssignmentModel,
    ProfessionalTeachingCourseModel,
    StudentAcademicInfoModel,
    StudentModel,
)


def _parse_deadline(s: Optional[str]) -> Optional[date]:
    if not s or not str(s).strip():
        return None
    t = str(s).strip()[:10]
    try:
        y, m, d = t.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _period_int(period_year: Optional[int]) -> Optional[int]:
    if period_year is None:
        return None
    try:
        return int(period_year)
    except (TypeError, ValueError):
        return None


class ProfessionalDocumentAssignmentClass:
    def __init__(self, db: Session):
        self.db = db

    def get_grouped(
        self,
        *,
        period_year: int,
        course_id: int,
        professional_id: int,
    ) -> Dict[str, Any]:
        """Devuelve items agrupados como espera el front (document_type_id, document_id, student_ids, student_statuses)."""
        try:
            py = int(period_year)
            rows = (
                self.db.query(ProfessionalDocumentAssignmentModel)
                .filter(
                    ProfessionalDocumentAssignmentModel.period_year == py,
                    ProfessionalDocumentAssignmentModel.course_id == int(course_id),
                    ProfessionalDocumentAssignmentModel.professional_id == int(professional_id),
                )
                .all()
            )
            # key: (document_type_id, document_catalog_id)
            buckets: Dict[Tuple[int, int], Dict[str, Any]] = {}
            for r in rows:
                cat = int(r.document_catalog_id or 0)
                key = (int(r.document_type_id), cat)
                if key not in buckets:
                    buckets[key] = {
                        "document_type_id": int(r.document_type_id),
                        "document_id": cat if cat > 0 else None,
                        "student_ids": [],
                        "student_statuses": {},
                        "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
                    }
                sid = int(r.student_id)
                if sid not in buckets[key]["student_ids"]:
                    buckets[key]["student_ids"].append(sid)
                buckets[key]["student_statuses"][str(sid)] = int(r.status_id or 0)
                # deadline: última no nula
                if r.deadline_at and not buckets[key]["deadline_at"]:
                    buckets[key]["deadline_at"] = r.deadline_at.isoformat()

            items = list(buckets.values())
            for it in items:
                it["student_ids"] = sorted(it["student_ids"])

            return {"status": "success", "data": {"items": items}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": {"items": []}}

    def sync_replace(
        self,
        *,
        period_year: int,
        course_id: int,
        professional_id: int,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Reemplaza asignaciones para (period, course, professional).
        Conserva status_id=1 y completed_at si la misma clave (student, type, catalog) sigue en el payload.
        """
        try:
            py = int(period_year)
            cid = int(course_id)
            pid = int(professional_id)

            AppAlertClass(self.db).delete_alerts_for_assignment_scope(
                period_year=py, course_id=cid, professional_id=pid
            )

            existing = (
                self.db.query(ProfessionalDocumentAssignmentModel)
                .filter(
                    ProfessionalDocumentAssignmentModel.period_year == py,
                    ProfessionalDocumentAssignmentModel.course_id == cid,
                    ProfessionalDocumentAssignmentModel.professional_id == pid,
                )
                .all()
            )
            old_map: Dict[Tuple[int, int, int], Tuple[int, Optional[datetime]]] = {}
            for r in existing:
                key = (int(r.student_id), int(r.document_type_id), int(r.document_catalog_id or 0))
                old_map[key] = (int(r.status_id or 0), r.completed_at)

            self.db.query(ProfessionalDocumentAssignmentModel).filter(
                ProfessionalDocumentAssignmentModel.period_year == py,
                ProfessionalDocumentAssignmentModel.course_id == cid,
                ProfessionalDocumentAssignmentModel.professional_id == pid,
            ).delete(synchronize_session=False)

            now = datetime.now()
            for raw in items:
                dtid = int(raw.get("document_type_id") or 0)
                if dtid <= 0:
                    continue
                did = raw.get("document_id")
                catalog = int(did) if did is not None and int(did) > 0 else 0
                sids = raw.get("student_ids") or []
                if not isinstance(sids, list):
                    continue
                dl = _parse_deadline(raw.get("deadline_at"))
                for sid in sids:
                    try:
                        student_id = int(sid)
                    except (TypeError, ValueError):
                        continue
                    if student_id <= 0:
                        continue
                    key = (student_id, dtid, catalog)
                    prev_status, prev_completed = old_map.get(key, (0, None))
                    st = prev_status if prev_status == 1 else 0
                    comp = prev_completed if st == 1 else None
                    row = ProfessionalDocumentAssignmentModel(
                        period_year=py,
                        course_id=cid,
                        professional_id=pid,
                        student_id=student_id,
                        document_type_id=dtid,
                        document_catalog_id=catalog,
                        status_id=st,
                        deadline_at=dl,
                        completed_at=comp,
                        added_date=now,
                        updated_date=now,
                    )
                    self.db.add(row)

            # Sin flush, el COUNT() no ve las filas nuevas en sesión → pending_n=0 y no se crea la alerta.
            self.db.flush()

            pending_n = (
                self.db.query(ProfessionalDocumentAssignmentModel)
                .filter(
                    ProfessionalDocumentAssignmentModel.period_year == py,
                    ProfessionalDocumentAssignmentModel.course_id == cid,
                    ProfessionalDocumentAssignmentModel.professional_id == pid,
                    ProfessionalDocumentAssignmentModel.status_id == 0,
                )
                .count()
            )
            AppAlertClass(self.db).upsert_scope_summary(
                period_year=py,
                course_id=cid,
                professional_id=pid,
                pending_count=pending_n,
            )

            self.db.commit()
            return {"status": "success", "message": "Sincronizado"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def count_pending(
        self,
        *,
        professional_id: int,
        period_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Cuenta asignaciones con status_id=0 (documento pendiente de cargar en carpeta)."""
        try:
            pid = int(professional_id)
            q = self.db.query(ProfessionalDocumentAssignmentModel).filter(
                ProfessionalDocumentAssignmentModel.professional_id == pid,
                ProfessionalDocumentAssignmentModel.status_id == 0,
            )
            if period_year is not None:
                q = q.filter(
                    ProfessionalDocumentAssignmentModel.period_year == int(period_year)
                )
            count = q.count()
            return {"status": "success", "count": count}
        except Exception as e:
            return {"status": "error", "message": str(e), "count": 0}

    def mark_completed_after_folder_upload(
        self,
        *,
        period_year: Optional[int],
        student_id: int,
        document_catalog_id: int,
        document_type_id: int,
        professional_id: Optional[int],
        course_id: Optional[int],
    ) -> None:
        """Marca filas pendientes cuando hay archivo en carpeta (mismo catálogo o catálogo 0 + mismo tipo)."""
        py = _period_int(period_year)
        if py is None:
            return
        dc = int(document_catalog_id)
        dt = int(document_type_id)
        sid = int(student_id)

        q = self.db.query(ProfessionalDocumentAssignmentModel).filter(
            ProfessionalDocumentAssignmentModel.period_year == py,
            ProfessionalDocumentAssignmentModel.student_id == sid,
            ProfessionalDocumentAssignmentModel.status_id == 0,
        )

        if course_id is not None and int(course_id) > 0:
            q = q.filter(ProfessionalDocumentAssignmentModel.course_id == int(course_id))

        if professional_id is not None and int(professional_id) > 0:
            q = q.filter(ProfessionalDocumentAssignmentModel.professional_id == int(professional_id))

        q = q.filter(
            or_(
                ProfessionalDocumentAssignmentModel.document_catalog_id == dc,
                and_(
                    ProfessionalDocumentAssignmentModel.document_catalog_id == 0,
                    ProfessionalDocumentAssignmentModel.document_type_id == dt,
                ),
            )
        )

        rows = q.all()
        if not rows:
            return
        now = datetime.now()
        for r in rows:
            r.status_id = 1
            r.completed_at = now
            r.updated_date = now
        r0 = rows[0]
        AppAlertClass(self.db).sync_scope_summary_from_assignments(
            period_year=int(r0.period_year),
            course_id=int(r0.course_id),
            professional_id=int(r0.professional_id),
        )
        self.db.commit()

    def home_stats(
        self,
        *,
        professional_id: int,
        period_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Resumen para home del profesional: documentos asignados/cargados (filas PDA),
        cursos en professionals_teachings_courses y suma de estudiantes por curso (puede repetir alumno entre cursos).
        """
        try:
            pid = int(professional_id)
            py = _period_int(period_year)

            q_pda = self.db.query(ProfessionalDocumentAssignmentModel).filter(
                ProfessionalDocumentAssignmentModel.professional_id == pid
            )
            if py is not None:
                q_pda = q_pda.filter(ProfessionalDocumentAssignmentModel.period_year == py)

            assigned_documents = int(q_pda.count())
            loaded_documents = int(
                q_pda.filter(ProfessionalDocumentAssignmentModel.status_id == 1).count()
            )

            course_rows = (
                self.db.query(ProfessionalTeachingCourseModel.course_id)
                .filter(
                    ProfessionalTeachingCourseModel.professional_id == pid,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0,
                )
                .distinct()
                .all()
            )
            course_ids = [int(r.course_id) for r in course_rows if r.course_id is not None]
            courses_assigned = len(course_ids)

            students_in_courses = 0
            for cid in course_ids:
                sq = (
                    self.db.query(StudentModel)
                    .join(
                        StudentAcademicInfoModel,
                        StudentAcademicInfoModel.student_id == StudentModel.id,
                    )
                    .filter(
                        StudentAcademicInfoModel.course_id == cid,
                        StudentModel.deleted_status_id == 0,
                    )
                )
                if py is not None:
                    sq = sq.filter(StudentModel.period_year == str(py))
                students_in_courses += int(sq.count())

            return {
                "status": "success",
                "data": {
                    "assigned_documents": assigned_documents,
                    "loaded_documents": loaded_documents,
                    "courses_assigned": courses_assigned,
                    "students_in_courses": students_in_courses,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
