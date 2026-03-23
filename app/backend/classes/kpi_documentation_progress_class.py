"""
KPI: avance de documentación transversal (document_type_id = 1 en catálogo `documents`).

Por estudiante: cuenta documentos cargados vs faltantes en carpeta / tablas asociadas
(misma lógica que FolderClass.check_document_existence para ese tipo).
Agregado por curso: suma de cargados y faltantes de todos los estudiantes del curso en el período.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.classes.student_class import StudentClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.db.models import CourseModel

# Misma convención que documents/list y EditStudent: sección transversal.
DOCUMENT_SECTION_TRANSVERSAL = 1


def _student_label(row: Dict[str, Any]) -> str:
    pd = row.get("personal_data") or {}
    parts = [
        (pd.get("names") or "").strip(),
        (pd.get("father_lastname") or "").strip(),
        (pd.get("mother_lastname") or "").strip(),
    ]
    name = " ".join(p for p in parts if p).strip()
    return name or f"Estudiante #{row.get('id')}"


class KpiDocumentationProgressClass:
    def __init__(self, db: Session):
        self.db = db

    def _students_for_course(
        self, course_id: int, period_year: int
    ) -> List[Dict[str, Any]]:
        st = StudentClass(self.db)
        raw = st.get_all(
            page=0,
            items_per_page=5000,
            course_id=int(course_id),
            period_year=int(period_year),
        )
        if isinstance(raw, dict) and raw.get("status") == "error":
            return []
        if not isinstance(raw, list):
            return []
        return [x for x in raw if isinstance(x, dict) and x.get("id") is not None]

    def by_course(
        self,
        *,
        school_id: int,
        period_year: int,
    ) -> Dict[str, Any]:
        """Una fila por curso del colegio: totales de docs cargados / faltantes (tipo transversal)."""
        try:
            py = int(period_year)
            courses = (
                self.db.query(CourseModel)
                .filter(CourseModel.school_id == int(school_id))
                .order_by(CourseModel.course_name.asc())
                .all()
            )
            folder = FolderClass(self.db)
            out: List[Dict[str, Any]] = []

            for c in courses:
                cid = int(c.id)
                students = self._students_for_course(cid, py)
                n_students = len(students)
                total_loaded = 0
                total_missing = 0
                for row in students:
                    sid = int(row["id"])
                    r = folder.check_document_existence(
                        sid, DOCUMENT_SECTION_TRANSVERSAL, py
                    )
                    if isinstance(r, dict) and r.get("status") == "error":
                        continue
                    total_loaded += int(r.get("total") or 0)
                    total_missing += int(r.get("total_missing") or 0)

                expected_slots = total_loaded + total_missing
                rate = (
                    round(100.0 * total_loaded / expected_slots, 1)
                    if expected_slots > 0
                    else 0.0
                )
                cname = (c.course_name or "").strip() or f"Curso #{cid}"
                out.append(
                    {
                        "course_id": cid,
                        "course_name": cname,
                        "student_count": n_students,
                        "loaded": total_loaded,
                        "missing": total_missing,
                        "expected_total": expected_slots,
                        "rate_percent": rate,
                    }
                )

            return {"status": "success", "data": out}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def students_detail(
        self,
        *,
        school_id: int,
        course_id: int,
        period_year: int,
    ) -> Dict[str, Any]:
        """Detalle por estudiante del curso (torta: cargados vs pendientes)."""
        try:
            cid = int(course_id)
            py = int(period_year)
            c = (
                self.db.query(CourseModel)
                .filter(
                    CourseModel.id == cid,
                    CourseModel.school_id == int(school_id),
                )
                .first()
            )
            if not c:
                return {
                    "status": "error",
                    "message": "Curso no encontrado",
                    "data": None,
                }

            students = self._students_for_course(cid, py)
            folder = FolderClass(self.db)
            rows: List[Dict[str, Any]] = []

            for row in students:
                sid = int(row["id"])
                r = folder.check_document_existence(
                    sid, DOCUMENT_SECTION_TRANSVERSAL, py
                )
                if isinstance(r, dict) and r.get("status") == "error":
                    continue
                loaded = int(r.get("total") or 0)
                missing = int(r.get("total_missing") or 0)
                expected = loaded + missing
                pct = round(100.0 * loaded / expected, 1) if expected > 0 else 0.0
                rows.append(
                    {
                        "student_id": sid,
                        "student_name": _student_label(row),
                        "loaded": loaded,
                        "missing": missing,
                        "expected": expected,
                        "rate_percent": pct,
                    }
                )

            rows.sort(key=lambda x: (x["student_name"] or "").lower())

            cname = (c.course_name or "").strip() or f"Curso #{cid}"
            return {
                "status": "success",
                "data": {
                    "course_id": cid,
                    "course_name": cname,
                    "students": rows,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
