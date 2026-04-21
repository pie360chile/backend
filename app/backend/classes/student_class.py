from datetime import datetime, date
from typing import Any, Dict, List

from app.backend.db.models import (
    StudentModel,
    StudentAcademicInfoModel,
    StudentPersonalInfoModel,
    SpecialEducationalNeedModel,
    CourseModel,
    SchoolModel,
    CommuneModel,
    FolderModel,
)
from sqlalchemy import and_
from sqlalchemy.orm import aliased


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    """Convierte fecha/datetime a string; si ya es str lo devuelve tal cual."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str) and v.strip():
        try:
            return datetime.strptime(v.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _period_year_int(v):
    """Convierte period_year (BD string) a int para la API; None si no es numérico."""
    if v is None:
        return None
    try:
        s = str(v).strip()
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def _extract_inspection_students_rows(inspection_body: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = inspection_body.get("data")
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        inner = raw.get("data")
        if isinstance(inner, list):
            return [r for r in inner if isinstance(r, dict)]
    return []


def _inspection_int(v):
    if v is None or (isinstance(v, str) and not str(v).strip()):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


class StudentClass:
    def __init__(self, db):
        self.db = db

    def _parse_date(self, v):
        return _parse_date(v)

    def _resolve_region_id_from_commune(self, commune_id: Any) -> Any:
        if commune_id is None:
            return None
        try:
            cid = int(commune_id)
        except (TypeError, ValueError):
            return None
        row = self.db.query(CommuneModel).filter(CommuneModel.id == cid).first()
        if row is not None and getattr(row, "region_id", None) is not None:
            return int(row.region_id)
        return None

    def _provision_inspection_import_extras(
        self,
        student_id: int,
        school_id: int,
        course_id: int,
        period_year: int,
        student_inputs: Dict[str, Any],
    ) -> None:
        """
        After Inspection import: align folders (health doc id=4) with school/course/period,
        and create a minimal health_evaluations + folders row when missing (same path as HealthEvaluationClass.store).
        """
        from app.backend.classes.health_evaluation_class import HealthEvaluationClass

        py_str = str(int(period_year)) if period_year is not None else None

        existing = (
            self.db.query(FolderModel)
            .filter(FolderModel.student_id == student_id, FolderModel.document_id == 4)
            .order_by(FolderModel.id.desc())
            .first()
        )
        if existing:
            existing.school_id = school_id
            existing.course_id = course_id
            if py_str is not None:
                existing.period_year = py_str
            existing.updated_date = datetime.now()
            self.db.commit()
            return

        full_name = " ".join(
            p
            for p in (
                (student_inputs.get("names") or "").strip(),
                (student_inputs.get("father_lastname") or "").strip(),
                (student_inputs.get("mother_lastname") or "").strip(),
            )
            if (p or "").strip()
        ).strip()

        hev = HealthEvaluationClass(self.db)
        res = hev.store(
            {
                "student_id": student_id,
                "gender_id": student_inputs.get("gender_id"),
                "nationality_id": student_inputs.get("nationality_id"),
                "full_name": full_name or None,
                "identification_number": student_inputs.get("identification_number"),
                "born_date": student_inputs.get("born_date"),
            }
        )
        if isinstance(res, dict) and res.get("status") == "error":
            raise RuntimeError(str(res.get("message") or "health evaluation stub failed"))

        fld = (
            self.db.query(FolderModel)
            .filter(FolderModel.student_id == student_id, FolderModel.document_id == 4)
            .order_by(FolderModel.id.desc())
            .first()
        )
        if fld:
            fld.school_id = school_id
            fld.course_id = course_id
            if py_str is not None:
                fld.period_year = py_str
            fld.updated_date = datetime.now()
            self.db.commit()

    def get_all(self, page=0, items_per_page=10, school_id=None, rut=None, names=None, identification_number=None, course_id=None, period_year=None):
        try:
            query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.period_year,
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.platform_status_id,
                StudentAcademicInfoModel.resolution_number,
                StudentAcademicInfoModel.sip_admission_year,
                StudentAcademicInfoModel.diagnostic_date,
                StudentAcademicInfoModel.psychopedagogical_evaluation_status,
                StudentAcademicInfoModel.psychopedagogical_evaluation_year,
                SpecialEducationalNeedModel.special_educational_needs.label('special_educational_need_name'),
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality_id,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).outerjoin(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                SpecialEducationalNeedModel,
                StudentAcademicInfoModel.special_educational_need_id == SpecialEducationalNeedModel.id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(StudentModel.deleted_status_id == 0)

            # Filtrar por school_id solo si NO se proporciona course_id
            # Si hay course_id, el profesional debe ver todos los estudiantes de ese curso sin importar la escuela
            if school_id and not course_id:
                query = query.filter(StudentModel.school_id == school_id)

            # Aplicar filtros de búsqueda
            if rut and rut.strip():
                query = query.filter(StudentModel.identification_number.like(f"%{rut.strip()}%"))
            
            if names and names.strip():
                query = query.filter(StudentPersonalInfoModel.names.like(f"%{names.strip()}%"))
            
            if identification_number and identification_number.strip():
                query = query.filter(StudentPersonalInfoModel.identification_number.like(f"%{identification_number.strip()}%"))
            
            if course_id:
                query = query.filter(StudentAcademicInfoModel.course_id == course_id)

            if period_year is not None and str(period_year).strip():
                query = query.filter(StudentModel.period_year == str(period_year).strip())

            query = query.order_by(StudentModel.id.desc())

            if page > 0:
                if page < 1:
                    page = 1

                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0

                if total_items == 0 or total_pages == 0 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": student.id,
                    "deleted_status_id": student.deleted_status_id,
                    "school_id": student.school_id,
                    "identification_number": student.student_identification_number,
                    "period_year": _period_year_int(getattr(student, "period_year", None)),
                    "added_date": student.added_date.strftime("%Y-%m-%d %H:%M:%S") if student.added_date else None,
                    "updated_date": student.updated_date.strftime("%Y-%m-%d %H:%M:%S") if student.updated_date else None,
                    "academic_info": {
                        "id": student.academic_id,
                        "special_educational_need_id": student.special_educational_need_id,
                        "special_educational_need_name": (getattr(student, "special_educational_need_name", None) or "").strip() or None,
                        "course_id": student.course_id,
                        "platform_status_id": getattr(student, "platform_status_id", None),
                        "resolution_number": getattr(student, "resolution_number", None),
                        "sip_admission_year": student.sip_admission_year,
                        "diagnostic_date": student.diagnostic_date.isoformat() if getattr(student, "diagnostic_date", None) else None,
                        "psychopedagogical_evaluation_status": getattr(student, "psychopedagogical_evaluation_status", None),
                        "psychopedagogical_evaluation_year": getattr(student, "psychopedagogical_evaluation_year", None),
                    } if student.academic_id else None,
                    "personal_data": {
                        "id": student.personal_id,
                        "region_id": student.region_id,
                        "commune_id": student.commune_id,
                        "gender_id": student.gender_id,
                        "proficiency_native_language_id": student.proficiency_native_language_id,
                        "proficiency_language_used_id": student.proficiency_language_used_id,
                        "identification_number": student.identification_number,
                        "names": student.names,
                        "father_lastname": student.father_lastname,
                        "mother_lastname": student.mother_lastname,
                        "social_name": student.social_name,
                        "born_date": student.born_date,
                        "nationality_id": student.nationality_id,
                        "address": student.address,
                        "phone": student.phone,
                        "email": student.email,
                        "native_language": student.native_language,
                        "language_usually_used": student.language_usually_used
                    } if student.personal_id else None
                } for student in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": student.id,
                    "deleted_status_id": student.deleted_status_id,
                    "school_id": student.school_id,
                    "identification_number": student.student_identification_number,
                    "period_year": _period_year_int(getattr(student, "period_year", None)),
                    "added_date": student.added_date.strftime("%Y-%m-%d %H:%M:%S") if student.added_date else None,
                    "updated_date": student.updated_date.strftime("%Y-%m-%d %H:%M:%S") if student.updated_date else None,
                    "academic_info": {
                        "id": student.academic_id,
                        "special_educational_need_id": student.special_educational_need_id,
                        "special_educational_need_name": (getattr(student, "special_educational_need_name", None) or "").strip() or None,
                        "course_id": student.course_id,
                        "platform_status_id": getattr(student, "platform_status_id", None),
                        "resolution_number": getattr(student, "resolution_number", None),
                        "sip_admission_year": student.sip_admission_year,
                        "diagnostic_date": student.diagnostic_date.isoformat() if getattr(student, "diagnostic_date", None) else None,
                        "psychopedagogical_evaluation_status": getattr(student, "psychopedagogical_evaluation_status", None),
                        "psychopedagogical_evaluation_year": getattr(student, "psychopedagogical_evaluation_year", None),
                    } if student.academic_id else None,
                    "personal_data": {
                        "id": student.personal_id,
                        "region_id": student.region_id,
                        "commune_id": student.commune_id,
                        "gender_id": student.gender_id,
                        "proficiency_native_language_id": student.proficiency_native_language_id,
                        "proficiency_language_used_id": student.proficiency_language_used_id,
                        "identification_number": student.identification_number,
                        "names": student.names,
                        "father_lastname": student.father_lastname,
                        "mother_lastname": student.mother_lastname,
                        "social_name": student.social_name,
                        "born_date": student.born_date,
                        "nationality_id": student.nationality_id,
                        "address": student.address,
                        "phone": student.phone,
                        "email": student.email,
                        "native_language": student.native_language,
                        "language_usually_used": student.language_usually_used
                    } if student.personal_id else None
                } for student in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_school_course_with_sen(self, school_id, course_id, page=0, items_per_page=100):
        """Lista estudiantes filtrados por school_id, course_id y con special_educational_need_id no nulo."""
        try:
            if not school_id or not course_id:
                return {"status": "error", "message": "school_id y course_id son requeridos.", "data": []}
            query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.period_year,
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.platform_status_id,
                StudentAcademicInfoModel.resolution_number,
                StudentAcademicInfoModel.sip_admission_year,
                StudentAcademicInfoModel.diagnostic_date,
                StudentAcademicInfoModel.psychopedagogical_evaluation_status,
                StudentAcademicInfoModel.psychopedagogical_evaluation_year,
                SpecialEducationalNeedModel.special_educational_needs.label('special_educational_need_name'),
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality_id,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).join(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                SpecialEducationalNeedModel,
                StudentAcademicInfoModel.special_educational_need_id == SpecialEducationalNeedModel.id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(
                StudentModel.deleted_status_id == 0,
                StudentModel.school_id == school_id,
                StudentAcademicInfoModel.course_id == course_id,
                StudentAcademicInfoModel.special_educational_need_id.isnot(None),
                SpecialEducationalNeedModel.deleted_status_id == 0,
                SpecialEducationalNeedModel.special_educational_need_type_id.in_([1, 2]),
            )
            query = query.order_by(
                SpecialEducationalNeedModel.special_educational_need_type_id.desc(),
                SpecialEducationalNeedModel.special_educational_needs.asc(),
                StudentPersonalInfoModel.names.asc(),
                StudentPersonalInfoModel.father_lastname.asc(),
            )
            if page > 0 and items_per_page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0
                if page < 1 or page > max(1, total_pages):
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages or 1,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }
                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
            else:
                data = query.all()
                total_items = len(data)
                total_pages = 1
            serialized_data = [{
                "id": student.id,
                "deleted_status_id": student.deleted_status_id,
                "school_id": student.school_id,
                "identification_number": student.student_identification_number,
                "period_year": _period_year_int(getattr(student, "period_year", None)),
                "added_date": _date_str(student.added_date),
                "updated_date": _date_str(student.updated_date),
"academic_info": {
                        "id": student.academic_id,
                        "special_educational_need_id": student.special_educational_need_id,
                        "special_educational_need_name": (getattr(student, "special_educational_need_name", None) or "").strip() or None,
                        "course_id": student.course_id,
                        "platform_status_id": getattr(student, "platform_status_id", None),
                        "resolution_number": getattr(student, "resolution_number", None),
                        "sip_admission_year": student.sip_admission_year,
                        "diagnostic_date": student.diagnostic_date.isoformat() if getattr(student, "diagnostic_date", None) else None,
                        "psychopedagogical_evaluation_status": getattr(student, "psychopedagogical_evaluation_status", None),
                        "psychopedagogical_evaluation_year": getattr(student, "psychopedagogical_evaluation_year", None),
                    } if student.academic_id else None,
                    "personal_data": {
                    "id": student.personal_id,
                    "region_id": student.region_id,
                    "commune_id": student.commune_id,
                    "gender_id": student.gender_id,
                    "proficiency_native_language_id": student.proficiency_native_language_id,
                    "proficiency_language_used_id": student.proficiency_language_used_id,
                    "identification_number": student.identification_number,
                    "names": student.names,
                    "father_lastname": student.father_lastname,
                    "mother_lastname": student.mother_lastname,
                    "social_name": student.social_name,
                    "born_date": _date_str(student.born_date, "%Y-%m-%d"),
                    "nationality_id": student.nationality_id,
                    "address": student.address,
                    "phone": student.phone,
                    "email": student.email,
                    "native_language": student.native_language,
                    "language_usually_used": student.language_usually_used
                } if student.personal_id else None
            } for student in data]
            if page > 0 and items_per_page > 0:
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }
            return serialized_data
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_counts_by_sen_type_and_pie_years(self, school_id=None):
        """
        Counts students by course and NEE type, split by años en PIE:
        one_year = primer año (years_in_pie == 0, ingresó en el año actual);
        more_than_one_year = segundo año o más (years_in_pie >= 1). Returns by_course.
        """
        try:
            from datetime import date
            current_year = date.today().year
            query = (
                self.db.query(
                    StudentAcademicInfoModel.student_id,
                    StudentAcademicInfoModel.course_id,
                    StudentAcademicInfoModel.sip_admission_year,
                    SpecialEducationalNeedModel.special_educational_need_type_id,
                    CourseModel.course_name,
                )
                .join(
                    StudentModel,
                    StudentModel.id == StudentAcademicInfoModel.student_id,
                )
                .join(
                    SpecialEducationalNeedModel,
                    SpecialEducationalNeedModel.id == StudentAcademicInfoModel.special_educational_need_id,
                )
                .outerjoin(
                    CourseModel,
                    and_(
                        CourseModel.id == StudentAcademicInfoModel.course_id,
                        CourseModel.deleted_status_id == 0,
                    ),
                )
                .filter(
                    StudentModel.deleted_status_id == 0,
                    StudentAcademicInfoModel.special_educational_need_id.isnot(None),
                    SpecialEducationalNeedModel.deleted_status_id == 0,
                )
            )
            if school_id:
                query = query.filter(StudentModel.school_id == school_id)
            rows = query.all()

            # by_course: course_id -> { course_name, by_type: { type_id -> { one_year, more_than_one_year } }, totals }
            by_course = {}
            for row in rows:
                course_id = row.course_id or 0
                course_name = (row.course_name or "").strip() if row.course_name else ""
                type_id = row.special_educational_need_type_id
                if type_id is None:
                    continue
                if course_id not in by_course:
                    by_course[course_id] = {
                        "course_name": course_name,
                        "by_type": {},
                        "total_one_year": 0,
                        "total_more_than_one_year": 0,
                    }
                if course_name and not by_course[course_id]["course_name"]:
                    by_course[course_id]["course_name"] = course_name
                sip_year = row.sip_admission_year
                years_in_pie = (current_year - sip_year) if sip_year else 0
                t = by_course[course_id]["by_type"].setdefault(type_id, {"one_year": 0, "more_than_one_year": 0})
                if years_in_pie == 0:
                    t["one_year"] += 1
                    by_course[course_id]["total_one_year"] += 1
                else:
                    t["more_than_one_year"] += 1
                    by_course[course_id]["total_more_than_one_year"] += 1

            by_course_list = []
            for cid in sorted(by_course.keys()):
                info = by_course[cid]
                by_type_list = [
                    {
                        "special_educational_need_type_id": tid,
                        "one_year": data["one_year"],
                        "more_than_one_year": data["more_than_one_year"],
                        "total": data["one_year"] + data["more_than_one_year"],
                    }
                    for tid, data in sorted(info["by_type"].items())
                ]
                by_course_list.append({
                    "course_id": cid if cid else None,
                    "course_name": info["course_name"],
                    "by_type": by_type_list,
                    "total_one_year": info["total_one_year"],
                    "total_more_than_one_year": info["total_more_than_one_year"],
                })
            return {
                "by_course": by_course_list,
                "current_year": current_year,
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_counts_by_sen_type_and_pie_years_by_school(self, customer_id=None):
        """
        Same as get_counts_by_sen_type_and_pie_years but grouped by school (colegio).
        Returns by_school: each school has school_id, school_name, by_course (same structure), totals.
        If customer_id is provided, only schools of that customer are included.
        """
        try:
            from datetime import date
            current_year = date.today().year
            query = (
                self.db.query(
                    StudentModel.school_id,
                    SchoolModel.school_name,
                    StudentAcademicInfoModel.student_id,
                    StudentAcademicInfoModel.course_id,
                    StudentAcademicInfoModel.sip_admission_year,
                    SpecialEducationalNeedModel.special_educational_need_type_id,
                    CourseModel.course_name,
                )
                .join(
                    StudentModel,
                    StudentModel.id == StudentAcademicInfoModel.student_id,
                )
                .join(
                    SchoolModel,
                    SchoolModel.id == StudentModel.school_id,
                )
                .join(
                    SpecialEducationalNeedModel,
                    SpecialEducationalNeedModel.id == StudentAcademicInfoModel.special_educational_need_id,
                )
                .outerjoin(
                    CourseModel,
                    and_(
                        CourseModel.id == StudentAcademicInfoModel.course_id,
                        CourseModel.deleted_status_id == 0,
                    ),
                )
                .filter(
                    StudentModel.deleted_status_id == 0,
                    StudentAcademicInfoModel.special_educational_need_id.isnot(None),
                    SpecialEducationalNeedModel.deleted_status_id == 0,
                )
            )
            if customer_id is not None:
                query = query.filter(SchoolModel.customer_id == customer_id)
            rows = query.all()

            # by_school: school_id -> { school_name, by_course: { course_id -> { ... } }, totals }
            by_school = {}
            for row in rows:
                school_id = row.school_id or 0
                school_name = (row.school_name or "").strip() if row.school_name else ""
                course_id = row.course_id or 0
                course_name = (row.course_name or "").strip() if row.course_name else ""
                type_id = row.special_educational_need_type_id
                if type_id is None:
                    continue
                if school_id not in by_school:
                    by_school[school_id] = {
                        "school_name": school_name,
                        "by_course": {},
                        "total_one_year": 0,
                        "total_more_than_one_year": 0,
                    }
                if school_name and not by_school[school_id]["school_name"]:
                    by_school[school_id]["school_name"] = school_name
                if course_id not in by_school[school_id]["by_course"]:
                    by_school[school_id]["by_course"][course_id] = {
                        "course_name": course_name,
                        "by_type": {},
                        "total_one_year": 0,
                        "total_more_than_one_year": 0,
                    }
                if course_name and not by_school[school_id]["by_course"][course_id]["course_name"]:
                    by_school[school_id]["by_course"][course_id]["course_name"] = course_name
                sip_year = row.sip_admission_year
                years_in_pie = (current_year - sip_year) if sip_year else 0
                c = by_school[school_id]["by_course"][course_id]
                t = c["by_type"].setdefault(type_id, {"one_year": 0, "more_than_one_year": 0})
                if years_in_pie == 0:
                    t["one_year"] += 1
                    c["total_one_year"] += 1
                    by_school[school_id]["total_one_year"] += 1
                else:
                    t["more_than_one_year"] += 1
                    c["total_more_than_one_year"] += 1
                    by_school[school_id]["total_more_than_one_year"] += 1

            by_school_list = []
            for sid in sorted(by_school.keys()):
                info = by_school[sid]
                by_course_list = []
                for cid in sorted(info["by_course"].keys()):
                    cinfo = info["by_course"][cid]
                    by_type_list = [
                        {
                            "special_educational_need_type_id": tid,
                            "one_year": data["one_year"],
                            "more_than_one_year": data["more_than_one_year"],
                            "total": data["one_year"] + data["more_than_one_year"],
                        }
                        for tid, data in sorted(cinfo["by_type"].items())
                    ]
                    by_course_list.append({
                        "course_id": cid if cid else None,
                        "course_name": cinfo["course_name"],
                        "by_type": by_type_list,
                        "total_one_year": cinfo["total_one_year"],
                        "total_more_than_one_year": cinfo["total_more_than_one_year"],
                    })
                by_school_list.append({
                    "school_id": sid if sid else None,
                    "school_name": info["school_name"],
                    "by_course": by_course_list,
                    "total_one_year": info["total_one_year"],
                    "total_more_than_one_year": info["total_more_than_one_year"],
                })
            return {
                "by_school": by_school_list,
                "current_year": current_year,
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get(self, id):
        try:
            data_query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.period_year,
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.platform_status_id,
                StudentAcademicInfoModel.resolution_number,
                StudentAcademicInfoModel.sip_admission_year,
                StudentAcademicInfoModel.diagnostic_date,
                StudentAcademicInfoModel.psychopedagogical_evaluation_status,
                StudentAcademicInfoModel.psychopedagogical_evaluation_year,
                SpecialEducationalNeedModel.special_educational_needs.label('special_educational_need_name'),
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality_id,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).outerjoin(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                SpecialEducationalNeedModel,
                StudentAcademicInfoModel.special_educational_need_id == SpecialEducationalNeedModel.id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(
                StudentModel.id == id,
                StudentModel.deleted_status_id == 0
            ).first()

            if data_query:
                student_data = {
                    "id": data_query.id,
                    "deleted_status_id": data_query.deleted_status_id,
                    "school_id": data_query.school_id,
                    "identification_number": data_query.student_identification_number,
                    "period_year": _period_year_int(getattr(data_query, "period_year", None)),
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None,
                    "academic_info": {
                        "id": data_query.academic_id,
                        "special_educational_need_id": data_query.special_educational_need_id,
                        "special_educational_need_name": (getattr(data_query, "special_educational_need_name", None) or "").strip() or None,
                        "course_id": data_query.course_id,
                        "platform_status_id": getattr(data_query, "platform_status_id", None),
                        "resolution_number": getattr(data_query, "resolution_number", None),
                        "sip_admission_year": data_query.sip_admission_year,
                        "diagnostic_date": data_query.diagnostic_date.isoformat() if getattr(data_query, "diagnostic_date", None) else None,
                        "psychopedagogical_evaluation_status": getattr(data_query, "psychopedagogical_evaluation_status", None),
                        "psychopedagogical_evaluation_year": getattr(data_query, "psychopedagogical_evaluation_year", None),
                    } if data_query.academic_id else None,
                    "personal_data": {
                        "id": data_query.personal_id,
                        "region_id": data_query.region_id,
                        "commune_id": data_query.commune_id,
                        "gender_id": data_query.gender_id,
                        "proficiency_native_language_id": data_query.proficiency_native_language_id,
                        "proficiency_language_used_id": data_query.proficiency_language_used_id,
                        "identification_number": data_query.identification_number,
                        "names": data_query.names,
                        "father_lastname": data_query.father_lastname,
                        "mother_lastname": data_query.mother_lastname,
                        "social_name": data_query.social_name,
                        "born_date": data_query.born_date,
                        "nationality_id": data_query.nationality_id,
                        "address": data_query.address,
                        "phone": data_query.phone,
                        "email": data_query.email,
                        "native_language": data_query.native_language,
                        "language_usually_used": data_query.language_usually_used
                    } if data_query.personal_id else None
                }

                return {"student_data": student_data}

            else:
                return {"error": "No se encontraron datos para el estudiante especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, student_inputs):
        try:
            school_id = student_inputs.get('school_id')
            identification_number = (student_inputs.get('identification_number') or '').strip()
            period_year = student_inputs.get('period_year')
            if period_year is not None and not isinstance(period_year, str):
                period_year = str(period_year).strip() if period_year else None
            elif period_year is not None:
                period_year = (period_year or '').strip() or None
            course_id = student_inputs.get('course_id')

            if not identification_number:
                return {"status": "error", "message": "El RUT/número de identificación es requerido."}

            forced_id_int = None
            raw_id = student_inputs.get("id")
            if raw_id is not None and str(raw_id).strip() != "":
                try:
                    forced_id_int = int(raw_id)
                except (TypeError, ValueError):
                    return {"status": "error", "message": "Invalid student id"}

            # Validar que no exista ya un estudiante con el mismo RUT, curso y periodo en el mismo colegio
            duplicate_query = self.db.query(StudentModel).filter(
                StudentModel.school_id == school_id,
                StudentModel.identification_number == identification_number,
                StudentModel.deleted_status_id == 0,
            )
            if period_year is not None and str(period_year):
                duplicate_query = duplicate_query.filter(StudentModel.period_year == str(period_year))
            else:
                duplicate_query = duplicate_query.filter(StudentModel.period_year.is_(None))

            if course_id:
                duplicate_query = duplicate_query.join(
                    StudentAcademicInfoModel,
                    (StudentAcademicInfoModel.student_id == StudentModel.id)
                    & (StudentAcademicInfoModel.course_id == course_id),
                )
            existing = duplicate_query.first()

            dup_msg = "Ya existe un estudiante con ese RUT en el mismo curso y período."
            if existing:
                if forced_id_int is not None and int(existing.id) != int(forced_id_int):
                    return {
                        "status": "error",
                        "message": (
                            f"Identification number already enrolled (student id={existing.id}); "
                            f"Inspection row expects id={forced_id_int}"
                        ),
                    }
                return {"status": "error", "message": dup_msg}

            if forced_id_int is not None:
                by_id = self.db.query(StudentModel).filter(StudentModel.id == forced_id_int).first()
                if by_id:
                    if int(by_id.deleted_status_id or 0) != 0:
                        return {
                            "status": "error",
                            "message": "Student id exists but is deleted; restore manually before import.",
                        }
                    if int(by_id.school_id or 0) != int(school_id or 0):
                        return {
                            "status": "error",
                            "message": "Student id already belongs to another school",
                        }
                    if (by_id.identification_number or "").strip() != identification_number:
                        return {
                            "status": "error",
                            "message": "Student id already assigned to a different identification number",
                        }
                    return {"status": "error", "message": dup_msg}

            # Crear el estudiante principal (period_year en BD es string); id opcional (import Inspection)
            py = student_inputs.get('period_year')
            period_year_db = str(py).strip() if py is not None else None
            row_kwargs = dict(
                deleted_status_id=0,
                school_id=student_inputs.get('school_id'),
                identification_number=student_inputs.get('identification_number'),
                period_year=period_year_db,
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
            if forced_id_int is not None:
                row_kwargs["id"] = forced_id_int
            new_student = StudentModel(**row_kwargs)

            self.db.add(new_student)
            self.db.commit()
            self.db.refresh(new_student)

            region_id = student_inputs.get("region_id")
            if region_id is None and student_inputs.get("commune_id") is not None:
                region_id = self._resolve_region_id_from_commune(student_inputs.get("commune_id"))

            # Crear información personal con los campos enviados (email/tel/fecha pueden venir de sync Inspection)
            now_ts = datetime.now()
            new_personal = StudentPersonalInfoModel(
                student_id=new_student.id,
                region_id=region_id,
                identification_number=student_inputs.get('identification_number'),
                names=student_inputs.get('names'),
                father_lastname=student_inputs.get('father_lastname'),
                mother_lastname=student_inputs.get('mother_lastname'),
                nationality_id=student_inputs.get('nationality_id'),
                gender_id=student_inputs.get('gender_id'),
                commune_id=student_inputs.get('commune_id'),
                address=student_inputs.get('address'),
                email=student_inputs.get('email'),
                phone=student_inputs.get('phone'),
                born_date=student_inputs.get('born_date'),
                added_date=now_ts,
                updated_date=now_ts,
            )
            self.db.add(new_personal)

            # Crear información académica si viene course_id
            course_id = student_inputs.get('course_id')
            if course_id:
                new_academic = StudentAcademicInfoModel(
                    student_id=new_student.id,
                    course_id=course_id,
                    special_educational_need_id=student_inputs.get('special_educational_need_id'),
                    sip_admission_year=student_inputs.get('sip_admission_year'),
                    platform_status_id=student_inputs.get('platform_status_id'),
                    resolution_number=student_inputs.get('resolution_number'),
                    diagnostic_date=self._parse_date(student_inputs.get('diagnostic_date')),
                    psychopedagogical_evaluation_status=student_inputs.get('psychopedagogical_evaluation_status'),
                    psychopedagogical_evaluation_year=student_inputs.get('psychopedagogical_evaluation_year'),
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                if getattr(new_academic, "psychopedagogical_evaluation_status", None) != 'realizada':
                    new_academic.psychopedagogical_evaluation_year = None
                self.db.add(new_academic)

            self.db.commit()

            return {
                "status": "success",
                "message": "Student created successfully",
                "student_id": new_student.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(StudentModel).filter(StudentModel.id == id).first()
            if data and data.deleted_status_id == 0:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Student deleted successfully"}
            elif data:
                return {"status": "error", "message": "No data found"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, student_inputs):
        try:
            existing_student = self.db.query(StudentModel).filter(
                StudentModel.id == id
            ).one_or_none()

            if not existing_student:
                return {"status": "error", "message": "No data found"}

            # Valores efectivos tras la actualización (para validar duplicado)
            eff_rut = (student_inputs.get('identification_number') or existing_student.identification_number or '').strip()
            eff_period = student_inputs.get('period_year') if 'period_year' in student_inputs else existing_student.period_year
            if eff_period is not None and not isinstance(eff_period, str):
                eff_period = str(eff_period).strip() or None
            elif eff_period is not None:
                eff_period = (eff_period or '').strip() or None
            eff_school = student_inputs.get('school_id') or existing_student.school_id
            eff_course_id = None
            if 'academic_info' in student_inputs and student_inputs['academic_info'] and student_inputs['academic_info'].get('course_id') is not None:
                eff_course_id = student_inputs['academic_info']['course_id']
            else:
                existing_academic_for_check = self.db.query(StudentAcademicInfoModel).filter(
                    StudentAcademicInfoModel.student_id == id
                ).first()
                if existing_academic_for_check:
                    eff_course_id = existing_academic_for_check.course_id

            if eff_rut:
                dup_query = self.db.query(StudentModel).filter(
                    StudentModel.id != id,
                    StudentModel.school_id == eff_school,
                    StudentModel.identification_number == eff_rut,
                    StudentModel.deleted_status_id == 0,
                )
                if eff_period:
                    dup_query = dup_query.filter(StudentModel.period_year == eff_period)
                else:
                    dup_query = dup_query.filter(StudentModel.period_year.is_(None))
                if eff_course_id:
                    dup_query = dup_query.join(
                        StudentAcademicInfoModel,
                        (StudentAcademicInfoModel.student_id == StudentModel.id)
                        & (StudentAcademicInfoModel.course_id == eff_course_id),
                    )
                if dup_query.first():
                    return {
                        "status": "error",
                        "message": "Ya existe un estudiante con ese RUT en el mismo curso y período.",
                    }

            # Actualizar school_id si está presente
            if 'school_id' in student_inputs and student_inputs['school_id']:
                existing_student.school_id = student_inputs['school_id']

            # Actualizar identification_number si está presente
            if 'identification_number' in student_inputs and student_inputs['identification_number']:
                existing_student.identification_number = student_inputs['identification_number']

            # Actualizar period_year si está presente (en BD es string)
            if 'period_year' in student_inputs:
                py = student_inputs.get('period_year')
                existing_student.period_year = str(py).strip() if py is not None else None

            existing_student.updated_date = datetime.now()

            # Actualizar información académica
            if 'academic_info' in student_inputs and student_inputs['academic_info']:
                academic_info = student_inputs['academic_info']
                existing_academic = self.db.query(StudentAcademicInfoModel).filter(
                    StudentAcademicInfoModel.student_id == id
                ).first()

                if existing_academic:
                    # Actualizar registro existente
                    if 'special_educational_need_id' in academic_info:
                        existing_academic.special_educational_need_id = academic_info['special_educational_need_id']
                    if 'course_id' in academic_info:
                        existing_academic.course_id = academic_info['course_id']
                    if 'platform_status_id' in academic_info:
                        existing_academic.platform_status_id = academic_info['platform_status_id']
                    if 'resolution_number' in academic_info:
                        existing_academic.resolution_number = academic_info['resolution_number']
                    if 'sip_admission_year' in academic_info:
                        existing_academic.sip_admission_year = academic_info['sip_admission_year']
                    if 'diagnostic_date' in academic_info:
                        existing_academic.diagnostic_date = self._parse_date(academic_info['diagnostic_date'])
                    if 'psychopedagogical_evaluation_status' in academic_info:
                        existing_academic.psychopedagogical_evaluation_status = academic_info['psychopedagogical_evaluation_status']
                    if 'psychopedagogical_evaluation_year' in academic_info:
                        existing_academic.psychopedagogical_evaluation_year = academic_info['psychopedagogical_evaluation_year']
                    status_value = getattr(existing_academic, "psychopedagogical_evaluation_status", None)
                    if status_value != 'realizada':
                        existing_academic.psychopedagogical_evaluation_year = None
                    existing_academic.updated_date = datetime.now()
                else:
                    # Crear nuevo registro
                    new_academic = StudentAcademicInfoModel(
                        student_id=id,
                        special_educational_need_id=academic_info.get('special_educational_need_id'),
                        course_id=academic_info.get('course_id'),
                        platform_status_id=academic_info.get('platform_status_id'),
                        resolution_number=academic_info.get('resolution_number'),
                        sip_admission_year=academic_info.get('sip_admission_year'),
                        diagnostic_date=self._parse_date(academic_info.get('diagnostic_date')),
                        psychopedagogical_evaluation_status=academic_info.get('psychopedagogical_evaluation_status'),
                        psychopedagogical_evaluation_year=academic_info.get('psychopedagogical_evaluation_year'),
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    if getattr(new_academic, "psychopedagogical_evaluation_status", None) != 'realizada':
                        new_academic.psychopedagogical_evaluation_year = None
                    self.db.add(new_academic)

            # Actualizar información personal
            if 'personal_data' in student_inputs and student_inputs['personal_data']:
                personal_data = student_inputs['personal_data']
                
                existing_personal = self.db.query(StudentPersonalInfoModel).filter(
                    StudentPersonalInfoModel.student_id == id
                ).first()

                if existing_personal:
                    # Actualizar registro existente
                    if 'region_id' in personal_data:
                        existing_personal.region_id = personal_data['region_id']
                    if 'commune_id' in personal_data:
                        existing_personal.commune_id = personal_data['commune_id']
                    if 'gender_id' in personal_data:
                        existing_personal.gender_id = personal_data['gender_id']
                    if 'proficiency_native_language_id' in personal_data:
                        existing_personal.proficiency_native_language_id = personal_data['proficiency_native_language_id']
                    if 'proficiency_language_used_id' in personal_data:
                        existing_personal.proficiency_language_used_id = personal_data['proficiency_language_used_id']
                    if 'identification_number' in personal_data:
                        existing_personal.identification_number = personal_data['identification_number']
                    if 'names' in personal_data:
                        existing_personal.names = personal_data['names']
                    if 'father_lastname' in personal_data:
                        existing_personal.father_lastname = personal_data['father_lastname']
                    if 'mother_lastname' in personal_data:
                        existing_personal.mother_lastname = personal_data['mother_lastname']
                    if 'social_name' in personal_data:
                        existing_personal.social_name = personal_data['social_name']
                    if 'born_date' in personal_data:
                        existing_personal.born_date = personal_data['born_date']
                    if 'nationality_id' in personal_data:
                        existing_personal.nationality_id = personal_data['nationality_id']
                    if 'address' in personal_data:
                        existing_personal.address = personal_data['address']
                    if 'phone' in personal_data:
                        existing_personal.phone = personal_data['phone']
                    if 'email' in personal_data:
                        existing_personal.email = personal_data['email']
                    if 'native_language' in personal_data:
                        existing_personal.native_language = personal_data['native_language']
                    if 'language_usually_used' in personal_data:
                        existing_personal.language_usually_used = personal_data['language_usually_used']
                else:
                    # Crear nuevo registro
                    new_personal = StudentPersonalInfoModel(
                        student_id=id,
                        region_id=personal_data.get('region_id'),
                        commune_id=personal_data.get('commune_id'),
                        gender_id=personal_data.get('gender_id'),
                        proficiency_native_language_id=personal_data.get('proficiency_native_language_id'),
                        proficiency_language_used_id=personal_data.get('proficiency_language_used_id'),
                        identification_number=personal_data.get('identification_number'),
                        names=personal_data.get('names'),
                        father_lastname=personal_data.get('father_lastname'),
                        mother_lastname=personal_data.get('mother_lastname'),
                        social_name=personal_data.get('social_name'),
                        born_date=personal_data.get('born_date'),
                        nationality_id=personal_data.get('nationality_id'),
                        address=personal_data.get('address'),
                        phone=personal_data.get('phone'),
                        email=personal_data.get('email'),
                        native_language=personal_data.get('native_language'),
                        language_usually_used=personal_data.get('language_usually_used')
                    )
                    self.db.add(new_personal)

            self.db.commit()
            self.db.refresh(existing_student)

            return {"status": "success", "message": "Student updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(
        self, school_id: int, inspection_body: Dict[str, Any], default_period_year: int
    ) -> Dict[str, Any]:
        """
        Import students from Inspection list payload (data[]).
        Each row must include id (stored as students.id), colegio_id (must match session school_id),
        rut, curso_id, and year fields per Inspection API.
        """
        try:
            rows = _extract_inspection_students_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                rut_raw = (row.get("rut") or row.get("identification_number") or "").strip()
                if not rut_raw:
                    errors.append({"name": "(no RUT)", "message": "Row missing RUT"})
                    continue

                ext_id = _inspection_int(row.get("id"))
                if ext_id is None:
                    errors.append({"name": rut_raw, "message": "Row missing Inspection student id"})
                    continue

                rid_col = row.get("colegio_id")
                if rid_col is None or str(rid_col).strip() == "":
                    errors.append({"name": rut_raw, "message": "Row missing colegio_id"})
                    continue
                try:
                    if int(rid_col) != int(school_id):
                        errors.append(
                            {
                                "name": rut_raw,
                                "message": f"colegio_id {rid_col} does not match session school_id {school_id}",
                            }
                        )
                        continue
                except (TypeError, ValueError):
                    errors.append({"name": rut_raw, "message": "Invalid colegio_id"})
                    continue

                course_remote = _inspection_int(row.get("curso_id"))
                if course_remote is None:
                    errors.append({"name": rut_raw, "message": "Row missing curso_id"})
                    continue

                course_row = (
                    self.db.query(CourseModel)
                    .filter(
                        CourseModel.id == course_remote,
                        CourseModel.school_id == school_id,
                        CourseModel.deleted_status_id == 0,
                    )
                    .first()
                )
                if not course_row:
                    errors.append(
                        {
                            "name": rut_raw,
                            "message": f"No course id={course_remote} for this school; import courses first",
                        }
                    )
                    continue

                py_raw = row.get("anio")
                if py_raw is not None and str(py_raw).strip() != "":
                    period_year = _inspection_int(py_raw)
                    if period_year is None:
                        period_year = default_period_year
                else:
                    period_year = default_period_year

                nombres = str(row.get("nombres") or "").strip()
                paterno = str(row.get("paterno") or "").strip()
                materno = str(row.get("materno") or "").strip()
                if not nombres and not paterno and not materno:
                    errors.append({"name": rut_raw, "message": "Row missing name fields"})
                    continue

                born = row.get("fecha_nacimiento")
                born_str = str(born).strip()[:10] if born is not None and str(born).strip() else None

                nat = _inspection_int(row.get("nacionalidad_id"))
                sex = _inspection_int(row.get("sexo"))
                comuna = _inspection_int(row.get("comuna_id"))

                student_inputs: Dict[str, Any] = {
                    "id": ext_id,
                    "school_id": school_id,
                    "identification_number": rut_raw,
                    "period_year": period_year,
                    "course_id": course_remote,
                    "names": nombres or "—",
                    "father_lastname": paterno or "",
                    "mother_lastname": materno or "",
                    "born_date": born_str,
                    "email": (str(row.get("email")).strip() if row.get("email") else None) or None,
                    "phone": (str(row.get("telefono")).strip() if row.get("telefono") else None) or None,
                    "address": (str(row.get("direccion")).strip() if row.get("direccion") else None) or None,
                    "nationality_id": nat,
                    "gender_id": sex,
                    "commune_id": comuna,
                }

                result = self.store(student_inputs)
                if isinstance(result, dict) and result.get("status") == "success":
                    sid = result.get("student_id")
                    if sid is not None:
                        try:
                            self._provision_inspection_import_extras(
                                int(sid), int(school_id), int(course_remote), int(period_year), student_inputs
                            )
                        except Exception as pe:
                            errors.append(
                                {
                                    "name": rut_raw,
                                    "message": f"Student saved; post-import provisioning failed: {pe}",
                                }
                            )
                    imported += 1
                    continue

                msg = (result or {}).get("message") or ""
                if isinstance(msg, str) and "Ya existe un estudiante" in msg:
                    skipped += 1
                    continue

                errors.append(
                    {
                        "name": rut_raw,
                        "message": str(msg) if msg else "Error al guardar",
                    }
                )

            return {
                "status": "success",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get_totals(self, customer_id=None, school_id=None, rol_id=None):
        try:
            from app.backend.db.models import SchoolModel
            
            query = self.db.query(StudentModel).filter(StudentModel.deleted_status_id == 0)
            
            # Si rol_id = 1 (administrador), devolver todos sin filtrar
            # Si es rol_id = 2, filtrar por customer_id
            # Si es cualquier otro rol, filtrar por school_id
            if rol_id == 2 and customer_id:
                query = query.join(SchoolModel, StudentModel.school_id == SchoolModel.id)
                query = query.filter(SchoolModel.customer_id == customer_id)
            elif rol_id not in [1, 2] and school_id:
                query = query.filter(StudentModel.school_id == school_id)
            
            total = query.count()
            
            return {"total": total}

        except Exception as e:
            return {"status": "error", "message": str(e)}
