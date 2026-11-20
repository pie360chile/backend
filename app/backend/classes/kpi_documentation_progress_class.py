"""
KPI: avance de documentación del alumno con NEE.

Incluye:
- sección transversal (document_type_id = 1)
- Informe a la familia (catálogo id 7) e Informe de Evaluación Psicopedagógica (id 27),
  contados por archivo en carpeta del período (aunque no sean transversales)

Misma lógica de existencia que FolderClass.check_document_existence para transversales.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.backend.classes.student_class import StudentClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.db.models import CourseModel, DocumentModel, FolderModel, SchoolModel

# Misma convención que documents/list y EditStudent.
DOCUMENT_SECTION_TRANSVERSAL = 1

# Catálogo: deben contar en el KPI aunque no sean transversales.
# 7 = Informe a la familia, 27 = Informe de Evaluación Psicopedagógica
KPI_EXTRA_CATALOG_IDS = frozenset({7, 27})


def _student_label(row: Dict[str, Any]) -> str:
    pd = row.get("personal_data") or {}
    parts = [
        (pd.get("names") or "").strip(),
        (pd.get("father_lastname") or "").strip(),
        (pd.get("mother_lastname") or "").strip(),
    ]
    name = " ".join(p for p in parts if p).strip()
    return name or f"Estudiante #{row.get('id')}"


def _counts_excluding_catalog_ids(
    result: Dict[str, Any] | None, exclude_ids: frozenset[int]
) -> Tuple[int, int]:
    """Totales de check_document_existence sin los document_id exclusivos del KPI extra."""
    if not isinstance(result, dict) or result.get("status") == "error":
        return 0, 0
    loaded = 0
    for item in result.get("data") or []:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("document_id") or 0) in exclude_ids:
                continue
        except Exception:
            continue
        loaded += 1
    missing = 0
    for item in result.get("missing") or []:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("document_id") or 0) in exclude_ids:
                continue
        except Exception:
            continue
        missing += 1
    return loaded, missing


def _extra_catalog_doc_loaded(
    db, student_id: int, document_id: int, period_year: int
) -> bool:
    """True si hay carpeta del período con archivo para ese document_id."""
    py = str(int(period_year))
    row = (
        db.query(FolderModel.id)
        .filter(
            FolderModel.student_id == int(student_id),
            FolderModel.document_id == int(document_id),
            FolderModel.deleted_date.is_(None),
            FolderModel.file.isnot(None),
            FolderModel.period_year == py,
        )
        .order_by(FolderModel.version_id.desc())
        .first()
    )
    return row is not None


def _student_doc_counts(
    folder: FolderClass, student_id: int, period_year: int
) -> Tuple[int, int]:
    """Cargados / faltantes: transversales + familia (7) + psicopedagógico (27)."""
    sid = int(student_id)
    py = int(period_year)
    loaded, missing = _counts_excluding_catalog_ids(
        folder.check_document_existence(sid, DOCUMENT_SECTION_TRANSVERSAL, py),
        KPI_EXTRA_CATALOG_IDS,
    )
    # Contar 7 y 27 por existencia en carpeta (independiente de la sección del catálogo).
    active_extra = {
        int(r.id)
        for r in folder.db.query(DocumentModel.id)
        .filter(
            DocumentModel.id.in_(list(KPI_EXTRA_CATALOG_IDS)),
            DocumentModel.deleted_date.is_(None),
        )
        .all()
    }
    for doc_id in sorted(KPI_EXTRA_CATALOG_IDS):
        if doc_id not in active_extra:
            continue
        if _extra_catalog_doc_loaded(folder.db, sid, doc_id, py):
            loaded += 1
        else:
            missing += 1
    return loaded, missing


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
        # KPI solo considera estudiantes con NEE asignada en academic_info.
        out: List[Dict[str, Any]] = []
        for x in raw:
            if not isinstance(x, dict) or x.get("id") is None:
                continue
            academic = x.get("academic_info") or {}
            nee_id = academic.get("special_educational_need_id")
            if nee_id is None:
                continue
            try:
                if int(nee_id) <= 0:
                    continue
            except Exception:
                continue
            out.append(x)
        return out

    def by_course(
        self,
        *,
        school_id: int,
        period_year: int,
    ) -> Dict[str, Any]:
        """Una fila por curso: transversales + familia + psicopedagógico."""
        try:
            py = int(period_year)
            courses = (
                self.db.query(CourseModel)
                .filter(CourseModel.school_id == int(school_id), CourseModel.deleted_status_id == 0)
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
                    loaded, missing = _student_doc_counts(folder, int(row["id"]), py)
                    total_loaded += loaded
                    total_missing += missing

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

    def by_school(
        self,
        *,
        school_ids: List[int],
        period_year: int,
    ) -> Dict[str, Any]:
        """Una fila por establecimiento (alumnos con NEE)."""
        try:
            py = int(period_year)
            ids = sorted({int(s) for s in school_ids if s is not None and int(s) > 0})
            out: List[Dict[str, Any]] = []

            for sid in ids:
                sch = (
                    self.db.query(SchoolModel)
                    .filter(SchoolModel.id == sid)
                    .first()
                )
                sname = (
                    (sch.school_name or "").strip() or f"Colegio #{sid}"
                    if sch
                    else f"Colegio #{sid}"
                )
                res = self.by_course(school_id=sid, period_year=py)
                rows = res.get("data") or [] if res.get("status") == "success" else []
                if not rows:
                    out.append(
                        {
                            "school_id": sid,
                            "school_name": sname,
                            "student_count": 0,
                            "loaded": 0,
                            "missing": 0,
                            "expected_total": 0,
                            "rate_percent": 0.0,
                        }
                    )
                    continue
                tot_students = sum(int(r.get("student_count") or 0) for r in rows)
                tot_loaded = sum(int(r.get("loaded") or 0) for r in rows)
                tot_missing = sum(int(r.get("missing") or 0) for r in rows)
                expected = tot_loaded + tot_missing
                rate = (
                    round(100.0 * tot_loaded / expected, 1) if expected > 0 else 0.0
                )
                out.append(
                    {
                        "school_id": sid,
                        "school_name": sname,
                        "student_count": tot_students,
                        "loaded": tot_loaded,
                        "missing": tot_missing,
                        "expected_total": expected,
                        "rate_percent": rate,
                    }
                )

            out.sort(key=lambda x: (x.get("school_name") or "").lower())
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
                    CourseModel.deleted_status_id == 0,
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
                loaded, missing = _student_doc_counts(folder, sid, py)
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
