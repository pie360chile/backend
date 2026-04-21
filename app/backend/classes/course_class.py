from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, case

from app.backend.classes.teaching_class import _normalize_school_id
from app.backend.db.models import CourseModel, TeachingModel, ProfessionalTeachingCourseModel, StudentModel, StudentAcademicInfoModel, SpecialEducationalNeedModel


def _extract_courses_rows(inspection_body: Dict[str, Any]) -> List[Any]:
    if not inspection_body.get("ok"):
        return []
    data = inspection_body.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("cursos", "items", "list", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def _inspection_course_id_from_row(row: Any) -> Optional[int]:
    if isinstance(row, dict) and row.get("id") is not None:
        try:
            return int(row["id"])
        except (TypeError, ValueError):
            return None
    return None

class CourseClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_id=None, course=None, teaching_id=None, period_year=None):
        try:
            query = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.period_year,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name,
                func.count(StudentModel.id).label('total_students'),
                func.count(case((SpecialEducationalNeedModel.special_educational_need_type_id == 1, 1))).label('total_students_sen'),
                func.count(case((SpecialEducationalNeedModel.special_educational_need_type_id == 2, 1))).label('total_students_tsen'),
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            ).outerjoin(
                StudentAcademicInfoModel, CourseModel.id == StudentAcademicInfoModel.course_id
            ).outerjoin(
                StudentModel,
                (StudentAcademicInfoModel.student_id == StudentModel.id) & (StudentModel.deleted_status_id == 0)
            ).outerjoin(
                SpecialEducationalNeedModel,
                (StudentAcademicInfoModel.special_educational_need_id == SpecialEducationalNeedModel.id)
                & (SpecialEducationalNeedModel.deleted_status_id == 0),
            )

            query = query.filter(CourseModel.deleted_status_id == 0)

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(CourseModel.school_id == school_id)

            # Aplicar filtro de búsqueda si se proporciona course
            if course and course.strip():
                query = query.filter(CourseModel.course_name.like(f"%{course.strip()}%"))
            
            # Aplicar filtro por teaching_id si se proporciona
            if teaching_id is not None:
                query = query.filter(CourseModel.teaching_id == teaching_id)

            if period_year is not None:
                query = query.filter(CourseModel.period_year == int(period_year))

            query = query.group_by(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.period_year,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).order_by(CourseModel.id)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0

                if total_items == 0:
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": course.id,
                    "teaching_id": course.teaching_id,
                    "course_name": course.course_name,
                    "periodYear": getattr(course, "period_year", None),
                    "teaching_name": course.teaching_name,
                    "total_students": course.total_students,
                    "total_students_sen": getattr(course, "total_students_sen", 0) or 0,
                    "total_students_tsen": getattr(course, "total_students_tsen", 0) or 0,
                    "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                    "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
                } for course in data]

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
                    "id": course.id,
                    "school_id": course.school_id,
                    "teaching_id": course.teaching_id,
                    "course_name": course.course_name,
                    "periodYear": getattr(course, "period_year", None),
                    "teaching_name": course.teaching_name,
                    "total_students": course.total_students,
                    "total_students_sen": getattr(course, "total_students_sen", 0) or 0,
                    "total_students_tsen": getattr(course, "total_students_tsen", 0) or 0,
                    "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                    "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
                } for course in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self, school_id=None, teaching_id=None, period_year=None):
        """Retorna todos los courses sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.period_year,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            )

            query = query.filter(CourseModel.deleted_status_id == 0)

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(CourseModel.school_id == school_id)
            
            # Filtrar por teaching_id si se proporciona
            if teaching_id:
                query = query.filter(CourseModel.teaching_id == teaching_id)

            if period_year is not None:
                query = query.filter(CourseModel.period_year == int(period_year))

            query = query.order_by(CourseModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": course.id,
                "school_id": course.school_id,
                "teaching_id": course.teaching_id,
                "course_name": course.course_name,
                "periodYear": getattr(course, "period_year", None),
                "teaching_name": course.teaching_name,
                "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
            } for course in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id, period_year=None):
        try:
            q = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.period_year,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            ).filter(CourseModel.id == id, CourseModel.deleted_status_id == 0)
            if period_year is not None:
                q = q.filter(CourseModel.period_year == int(period_year))
            data_query = q.first()

            if data_query:
                course_data = {
                    "id": data_query.id,
                    "school_id": data_query.school_id,
                    "teaching_id": data_query.teaching_id,
                    "course_name": data_query.course_name,
                    "periodYear": getattr(data_query, "period_year", None),
                    "teaching_name": data_query.teaching_name,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"course_data": course_data}

            else:
                return {"error": "No se encontraron datos para el course especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, course_inputs):
        try:
            py = course_inputs.get('period_year')
            period_year_val = None
            if py is not None and str(py).strip() != '':
                try:
                    period_year_val = int(py)
                except (TypeError, ValueError):
                    period_year_val = None
            row_kwargs: Dict[str, Any] = {
                "school_id": course_inputs.get("school_id"),
                "teaching_id": course_inputs["teaching_id"],
                "course_name": course_inputs["course_name"],
                "period_year": period_year_val,
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
                "deleted_status_id": 0,
            }
            if course_inputs.get("id") is not None:
                row_kwargs["id"] = int(course_inputs["id"])

            new_course = CourseModel(**row_kwargs)

            self.db.add(new_course)
            self.db.commit()
            self.db.refresh(new_course)

            return {
                "status": "success",
                "message": "Course created successfully",
                "course_id": new_course.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = (
                self.db.query(CourseModel)
                .filter(CourseModel.id == id, CourseModel.deleted_status_id == 0)
                .first()
            )
            if data:
                # Marcar como eliminado en professionals_teachings_courses
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.course_id == id
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                })

                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Course deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, course_inputs):
        try:
            existing_course = (
                self.db.query(CourseModel)
                .filter(CourseModel.id == id, CourseModel.deleted_status_id == 0)
                .one_or_none()
            )

            if not existing_course:
                return {"status": "error", "message": "No data found"}

            for key, value in course_inputs.items():
                if key in ('school_id', 'teaching_id', 'course_name', 'period_year'):
                    setattr(existing_course, key, value)

            existing_course.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_course)

            return {"status": "success", "message": "Course updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(
        self, school_id: int, inspection_body: Dict[str, Any], default_period_year: int
    ) -> Dict[str, Any]:
        """
        Inserta cursos desde Inspection usando el id remoto como PK (`courses.id`).
        Requiere que exista la enseñanza (`tipo_ensenanza_id` = `teachings.id`) del mismo colegio.
        """
        try:
            rows = _extract_courses_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                if not isinstance(row, dict):
                    continue
                ext_id = _inspection_course_id_from_row(row)
                nombre = str(row.get("nombre") or "").strip()
                if ext_id is None or not nombre:
                    continue

                tipo_tid = row.get("tipo_ensenanza_id")
                if tipo_tid is None:
                    errors.append({"name": nombre, "message": "Fila sin tipo_ensenanza_id"})
                    continue
                try:
                    teaching_id = int(tipo_tid)
                except (TypeError, ValueError):
                    errors.append({"name": nombre, "message": "tipo_ensenanza_id inválido"})
                    continue

                teaching = (
                    self.db.query(TeachingModel)
                    .filter(
                        TeachingModel.id == teaching_id,
                        TeachingModel.school_id == school_id,
                        TeachingModel.deleted_status_id == 0,
                    )
                    .first()
                )
                if not teaching:
                    errors.append(
                        {
                            "name": nombre,
                            "message": f"No existe enseñanza id={teaching_id} para este colegio; importe tipos primero",
                        }
                    )
                    continue

                rid_col = row.get("colegio_id")
                if rid_col is not None:
                    try:
                        if int(rid_col) != int(school_id):
                            errors.append(
                                {
                                    "name": nombre,
                                    "message": f"colegio_id {rid_col} no coincide con el colegio de sesión",
                                }
                            )
                            continue
                    except (TypeError, ValueError):
                        pass

                py_raw = row.get("anio")
                if py_raw is not None and str(py_raw).strip() != "":
                    try:
                        period_year = int(py_raw)
                    except (TypeError, ValueError):
                        period_year = default_period_year
                else:
                    period_year = default_period_year

                name_norm = nombre.lower()
                existing = self.db.query(CourseModel).filter(CourseModel.id == ext_id).first()
                if existing:
                    if int(existing.deleted_status_id or 0) != 0:
                        existing.school_id = school_id
                        existing.teaching_id = teaching_id
                        existing.course_name = nombre
                        existing.period_year = period_year
                        existing.deleted_status_id = 0
                        existing.updated_date = datetime.now()
                        self.db.commit()
                        imported += 1
                        continue

                    same_school = int(existing.school_id or 0) == int(school_id)
                    same_name = (existing.course_name or "").strip().lower() == name_norm
                    if same_school and same_name:
                        skipped += 1
                        continue
                    if same_school and not same_name:
                        errors.append(
                            {
                                "name": nombre,
                                "message": (
                                    f"Ya existe curso id={ext_id} con otro nombre ({existing.course_name!r})"
                                ),
                            }
                        )
                        continue
                    errors.append(
                        {
                            "name": nombre,
                            "message": (
                                f"El id {ext_id} ya está asignado a otro colegio (school_id={existing.school_id})"
                            ),
                        }
                    )
                    continue

                res = self.store(
                    {
                        "id": ext_id,
                        "school_id": school_id,
                        "teaching_id": teaching_id,
                        "course_name": nombre,
                        "period_year": period_year,
                    }
                )
                if res.get("status") == "success":
                    imported += 1
                else:
                    errors.append({"name": nombre, "message": str(res.get("message", "Error"))})

            return {
                "status": "success",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}