"""
KPI de asignaciones de documentos a especialistas: conteos por curso y por profesional.
Filtro temporal: mes/año calendario sobre `added_date` de professional_document_assignments.
- asignados: filas con added_date en el rango
- cargados: mismas filas con status_id == 1
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

from app.backend.db.models import (
    CourseModel,
    DocumentModel,
    DocumentTypeModel,
    ProfessionalDocumentAssignmentModel,
    ProfessionalModel,
    SchoolModel,
)


def _month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    """Rango [start, end) sobre added_date (mes calendario completo)."""
    start = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_excl = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_excl = datetime(year, month + 1, 1, 0, 0, 0)
    return start, end_excl


class KpiDocumentAssignmentsClass:
    def __init__(self, db: Session):
        self.db = db

    def by_course(
        self,
        *,
        period_year: Optional[int],
        year: int,
        month: int,
        professional_id_filter: Optional[int] = None,
        school_id_filter: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            y = int(year)
            m = int(month)
            if m < 1 or m > 12:
                return {"status": "error", "message": "Mes inválido", "data": []}
            start, end_excl = _month_bounds(y, m)

            loaded_expr = func.sum(
                case((ProfessionalDocumentAssignmentModel.status_id == 1, 1), else_=0)
            ).label("loaded")

            filters = [
                ProfessionalDocumentAssignmentModel.added_date.isnot(None),
                ProfessionalDocumentAssignmentModel.added_date >= start,
                ProfessionalDocumentAssignmentModel.added_date < end_excl,
            ]
            if professional_id_filter is not None:
                filters.append(
                    ProfessionalDocumentAssignmentModel.professional_id == int(professional_id_filter)
                )
            if period_year is not None:
                filters.insert(0, ProfessionalDocumentAssignmentModel.period_year == int(period_year))

            base_q = self.db.query(
                ProfessionalDocumentAssignmentModel.course_id.label("course_id"),
                func.count(ProfessionalDocumentAssignmentModel.id).label("assigned"),
                loaded_expr,
            ).filter(*filters)

            if school_id_filter is not None:
                base_q = base_q.join(
                    CourseModel,
                    CourseModel.id == ProfessionalDocumentAssignmentModel.course_id,
                ).filter(CourseModel.school_id == int(school_id_filter))

            q = base_q.group_by(ProfessionalDocumentAssignmentModel.course_id)

            rows = q.all()
            course_ids = [int(r.course_id) for r in rows if r.course_id is not None]
            names: Dict[int, str] = {}
            if course_ids:
                for c in (
                    self.db.query(CourseModel)
                    .filter(CourseModel.id.in_(course_ids))
                    .all()
                ):
                    names[int(c.id)] = (c.course_name or "").strip() or f"Curso #{c.id}"

            out: List[Dict[str, Any]] = []
            for r in rows:
                cid = int(r.course_id)
                assigned = int(r.assigned or 0)
                loaded = int(r.loaded or 0)
                pct = round(100.0 * loaded / assigned, 1) if assigned > 0 else 0.0
                out.append(
                    {
                        "course_id": cid,
                        "course_name": names.get(cid, f"Curso #{cid}"),
                        "assigned": assigned,
                        "loaded": loaded,
                        "rate_percent": pct,
                    }
                )
            out.sort(key=lambda x: x["course_name"].lower())
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def by_school(
        self,
        *,
        period_year: Optional[int],
        year: int,
        month: int,
        professional_id_filter: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Agrega asignaciones por establecimiento (school_id del curso)."""
        try:
            y = int(year)
            m = int(month)
            if m < 1 or m > 12:
                return {"status": "error", "message": "Mes inválido", "data": []}
            start, end_excl = _month_bounds(y, m)

            loaded_expr = func.sum(
                case((ProfessionalDocumentAssignmentModel.status_id == 1, 1), else_=0)
            ).label("loaded")

            filters = [
                ProfessionalDocumentAssignmentModel.added_date.isnot(None),
                ProfessionalDocumentAssignmentModel.added_date >= start,
                ProfessionalDocumentAssignmentModel.added_date < end_excl,
            ]
            if professional_id_filter is not None:
                filters.append(
                    ProfessionalDocumentAssignmentModel.professional_id == int(professional_id_filter)
                )
            if period_year is not None:
                filters.insert(0, ProfessionalDocumentAssignmentModel.period_year == int(period_year))

            q = (
                self.db.query(
                    CourseModel.school_id.label("school_id"),
                    func.count(ProfessionalDocumentAssignmentModel.id).label("assigned"),
                    loaded_expr,
                )
                .select_from(ProfessionalDocumentAssignmentModel)
                .join(CourseModel, CourseModel.id == ProfessionalDocumentAssignmentModel.course_id)
                .filter(*filters)
                .group_by(CourseModel.school_id)
            )

            rows = q.all()
            school_ids = []
            for r in rows:
                sid = r.school_id
                if sid is not None:
                    school_ids.append(int(sid))
            names: Dict[int, str] = {}
            if school_ids:
                for s in self.db.query(SchoolModel).filter(SchoolModel.id.in_(school_ids)).all():
                    names[int(s.id)] = (s.school_name or "").strip() or f"Colegio #{s.id}"

            out: List[Dict[str, Any]] = []
            for r in rows:
                sid_raw = r.school_id
                sid = int(sid_raw) if sid_raw is not None else 0
                assigned = int(r.assigned or 0)
                loaded = int(r.loaded or 0)
                pct = round(100.0 * loaded / assigned, 1) if assigned > 0 else 0.0
                label = names.get(sid, f"Colegio #{sid}") if sid > 0 else "Sin establecimiento"
                out.append(
                    {
                        "school_id": sid,
                        "school_name": label,
                        "assigned": assigned,
                        "loaded": loaded,
                        "rate_percent": pct,
                    }
                )
            out.sort(key=lambda x: x["school_name"].lower())
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def by_professional(
        self,
        *,
        period_year: Optional[int],
        course_id: int,
        year: int,
        month: int,
        professional_id_filter: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            cid = int(course_id)
            y = int(year)
            m = int(month)
            if m < 1 or m > 12:
                return {"status": "error", "message": "Mes inválido", "data": []}
            start, end_excl = _month_bounds(y, m)

            loaded_expr = func.sum(
                case((ProfessionalDocumentAssignmentModel.status_id == 1, 1), else_=0)
            ).label("loaded")

            filters = [
                ProfessionalDocumentAssignmentModel.course_id == cid,
                ProfessionalDocumentAssignmentModel.added_date.isnot(None),
                ProfessionalDocumentAssignmentModel.added_date >= start,
                ProfessionalDocumentAssignmentModel.added_date < end_excl,
            ]
            if professional_id_filter is not None:
                filters.append(
                    ProfessionalDocumentAssignmentModel.professional_id == int(professional_id_filter)
                )
            if period_year is not None:
                filters.insert(0, ProfessionalDocumentAssignmentModel.period_year == int(period_year))

            q = (
                self.db.query(
                    ProfessionalDocumentAssignmentModel.professional_id.label("professional_id"),
                    func.count(ProfessionalDocumentAssignmentModel.id).label("assigned"),
                    loaded_expr,
                )
                .filter(*filters)
                .group_by(ProfessionalDocumentAssignmentModel.professional_id)
            )

            rows = q.all()
            pids = [int(r.professional_id) for r in rows if r.professional_id is not None]
            prof_names: Dict[int, str] = {}
            if pids:
                for p in (
                    self.db.query(ProfessionalModel).filter(ProfessionalModel.id.in_(pids)).all()
                ):
                    fn = (p.names or "").strip()
                    ln = (p.lastnames or "").strip()
                    prof_names[int(p.id)] = (f"{fn} {ln}").strip() or f"Profesional #{p.id}"

            out: List[Dict[str, Any]] = []
            for r in rows:
                pid = int(r.professional_id)
                assigned = int(r.assigned or 0)
                loaded = int(r.loaded or 0)
                pct = round(100.0 * loaded / assigned, 1) if assigned > 0 else 0.0
                out.append(
                    {
                        "professional_id": pid,
                        "professional_name": prof_names.get(pid, f"Profesional #{pid}"),
                        "assigned": assigned,
                        "loaded": loaded,
                        "rate_percent": pct,
                    }
                )
            out.sort(key=lambda x: x["professional_name"].lower())
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def by_document(
        self,
        *,
        period_year: Optional[int],
        course_id: int,
        year: int,
        month: int,
        professional_id_filter: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Por tipo de documento (catálogo `documents` o `document_types` si no hay catálogo).
        Agrupa por document_catalog_id cuando es > 0; si no, por document_type_id.
        """
        try:
            cid = int(course_id)
            y = int(year)
            m = int(month)
            if m < 1 or m > 12:
                return {"status": "error", "message": "Mes inválido", "data": []}
            start, end_excl = _month_bounds(y, m)

            # Un bucket por catálogo; si catalog_id = 0, por tipo de documento.
            bucket_catalog = case(
                (
                    ProfessionalDocumentAssignmentModel.document_catalog_id > 0,
                    ProfessionalDocumentAssignmentModel.document_catalog_id,
                ),
                else_=literal(0),
            )
            bucket_type = case(
                (ProfessionalDocumentAssignmentModel.document_catalog_id > 0, literal(0)),
                else_=ProfessionalDocumentAssignmentModel.document_type_id,
            )

            loaded_expr = func.sum(
                case((ProfessionalDocumentAssignmentModel.status_id == 1, 1), else_=0)
            ).label("loaded")

            filters = [
                ProfessionalDocumentAssignmentModel.course_id == cid,
                ProfessionalDocumentAssignmentModel.added_date.isnot(None),
                ProfessionalDocumentAssignmentModel.added_date >= start,
                ProfessionalDocumentAssignmentModel.added_date < end_excl,
            ]
            if professional_id_filter is not None:
                filters.append(
                    ProfessionalDocumentAssignmentModel.professional_id
                    == int(professional_id_filter)
                )
            if period_year is not None:
                filters.insert(
                    0,
                    ProfessionalDocumentAssignmentModel.period_year == int(period_year),
                )

            q = (
                self.db.query(
                    bucket_catalog.label("bucket_catalog_id"),
                    bucket_type.label("bucket_type_id"),
                    func.count(ProfessionalDocumentAssignmentModel.id).label("assigned"),
                    loaded_expr,
                )
                .filter(*filters)
                .group_by(bucket_catalog, bucket_type)
            )

            rows = q.all()
            catalog_ids = list(
                {int(r.bucket_catalog_id or 0) for r in rows if int(r.bucket_catalog_id or 0) > 0}
            )
            type_ids = list(
                {
                    int(r.bucket_type_id or 0)
                    for r in rows
                    if int(r.bucket_catalog_id or 0) == 0 and int(r.bucket_type_id or 0) > 0
                }
            )

            doc_names: Dict[int, str] = {}
            if catalog_ids:
                for d in (
                    self.db.query(DocumentModel).filter(DocumentModel.id.in_(catalog_ids)).all()
                ):
                    doc_names[int(d.id)] = (d.document or "").strip() or f"Documento #{d.id}"

            type_names: Dict[int, str] = {}
            if type_ids:
                for t in (
                    self.db.query(DocumentTypeModel).filter(DocumentTypeModel.id.in_(type_ids)).all()
                ):
                    type_names[int(t.id)] = (t.document or "").strip() or f"Tipo #{t.id}"

            out: List[Dict[str, Any]] = []
            for r in rows:
                bc = int(r.bucket_catalog_id or 0)
                bt = int(r.bucket_type_id or 0)
                assigned = int(r.assigned or 0)
                loaded = int(r.loaded or 0)
                pct = round(100.0 * loaded / assigned, 1) if assigned > 0 else 0.0
                if bc > 0:
                    dname = doc_names.get(bc, f"Documento #{bc}")
                elif bt > 0:
                    dname = type_names.get(bt, f"Tipo de documento #{bt}")
                else:
                    dname = "Documento (sin catálogo)"

                out.append(
                    {
                        "document_catalog_id": bc,
                        "document_type_id": bt,
                        "document_name": dname,
                        "assigned": assigned,
                        "loaded": loaded,
                        "rate_percent": pct,
                    }
                )
            out.sort(key=lambda x: x["document_name"].lower())
            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}
