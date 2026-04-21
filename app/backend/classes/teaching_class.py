from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.backend.db.models import TeachingModel, ProfessionalTeachingCourseModel


def _extract_teachings_rows(inspection_body: Dict[str, Any]) -> List[Any]:
    if not inspection_body.get("ok"):
        return []
    data = inspection_body.get("data")
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("ensenanzas", "enseñanzas", "teachings", "items", "list", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def _inspection_catalog_id_from_row(row: Any) -> Optional[int]:
    """ID del registro en Inspection (p. ej. tipos-ensenanzas: campo `id`)."""
    if isinstance(row, dict) and row.get("id") is not None:
        try:
            return int(row["id"])
        except (TypeError, ValueError):
            return None
    return None


def _teaching_name_from_row(row: Any) -> Optional[str]:
    if isinstance(row, str):
        s = row.strip()
        return s[:255] if s else None
    if not isinstance(row, dict):
        return None
    for k in (
        "nombre",
        "name",
        "teaching_name",
        "descripcion",
        "NOMBRE",
        "ensenanza",
        "enseñanza",
        "tipo_ensenanza",
    ):
        v = row.get(k)
        if v is not None:
            s = str(v).strip()
            if s:
                return s[:255]
    return None


def _normalize_school_id(school_id: Any) -> Optional[int]:
    """Convierte school_id de sesión/token a int para el filtro SQL; None si no aplica."""
    if school_id is None:
        return None
    if isinstance(school_id, str) and not school_id.strip():
        return None
    try:
        return int(school_id)
    except (TypeError, ValueError):
        return None


def _teaching_type_id_from_row(row: Any) -> int:
    if isinstance(row, dict):
        for k in ("teaching_type_id", "tipo_id", "tipo_ensenanza_id", "id_tipo", "nivel_id"):
            v = row.get(k)
            if v is not None:
                try:
                    n = int(v)
                    if 1 <= n <= 3:
                        return n
                except (TypeError, ValueError):
                    pass
        nivel = str(row.get("nivel") or row.get("tipo") or "").lower()
        if "pre" in nivel:
            return 1
        if "media" in nivel:
            return 3
        if "básica" in nivel or "basica" in nivel:
            return 2
    return 2

class TeachingClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_id=None, teaching_name=None):
        try:        
            query = self.db.query(
                TeachingModel.id,
                TeachingModel.school_id,
                TeachingModel.teaching_type_id,
                TeachingModel.teaching_name,
                TeachingModel.added_date,
                TeachingModel.updated_date
            ).filter(TeachingModel.deleted_status_id == 0)

            sid = _normalize_school_id(school_id)
            if sid is not None:
                query = query.filter(TeachingModel.school_id == sid)

            # Aplicar filtro de búsqueda si se proporciona teaching_name
            if teaching_name and teaching_name.strip():
                query = query.filter(TeachingModel.teaching_name.like(f"%{teaching_name.strip()}%"))

            query = query.order_by(TeachingModel.id)

            if page > 0:
                total_items = query.count()
                print(f"Total items found: {total_items}")
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0

                if total_items == 0:
                    print("No teachings found for the criteria")
                    print("===========================================")

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
                    "id": teaching.id,
                    "school_id": teaching.school_id,
                    "teaching_type_id": teaching.teaching_type_id,
                    "teaching_name": teaching.teaching_name,
                    "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                    "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
                } for teaching in data]

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
                    "id": teaching.id,
                    "school_id": teaching.school_id,
                    "teaching_type_id": teaching.teaching_type_id,
                    "teaching_name": teaching.teaching_name,
                    "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                    "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
                } for teaching in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self, school_id=None):
        """Retorna todos los teachings sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                TeachingModel.id,
                TeachingModel.school_id,
                TeachingModel.teaching_type_id,
                TeachingModel.teaching_name,
                TeachingModel.added_date,
                TeachingModel.updated_date
            ).filter(TeachingModel.deleted_status_id == 0)

            sid = _normalize_school_id(school_id)
            if sid is not None:
                query = query.filter(TeachingModel.school_id == sid)

            query = query.order_by(TeachingModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": teaching.id,
                "school_id": teaching.school_id,
                "teaching_type_id": teaching.teaching_type_id,
                "teaching_name": teaching.teaching_name,
                "added_date": teaching.added_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.added_date else None,
                "updated_date": teaching.updated_date.strftime("%Y-%m-%d %H:%M:%S") if teaching.updated_date else None
            } for teaching in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(TeachingModel).filter(TeachingModel.id == id).first()

            if data_query:
                teaching_data = {
                    "id": data_query.id,
                    "school_id": data_query.school_id,
                    "teaching_type_id": data_query.teaching_type_id,
                    "teaching_name": data_query.teaching_name,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"teaching_data": teaching_data}

            else:
                return {"error": "No se encontraron datos para el teaching especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, teaching_inputs):
        try:
            row_kwargs: Dict[str, Any] = {
                "school_id": teaching_inputs.get("school_id"),
                "teaching_type_id": teaching_inputs.get("teaching_type_id"),
                "teaching_name": teaching_inputs["teaching_name"],
                "deleted_status_id": 0,
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
            }
            if teaching_inputs.get("id") is not None:
                row_kwargs["id"] = int(teaching_inputs["id"])

            new_teaching = TeachingModel(**row_kwargs)

            self.db.add(new_teaching)
            self.db.commit()
            self.db.refresh(new_teaching)

            return {
                "status": "success",
                "message": "Teaching created successfully",
                "teaching_id": new_teaching.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(TeachingModel).filter(TeachingModel.id == id).first()
            if data:
                # Marcar como eliminado en professionals_teachings_courses
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.teaching_id == id
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                })
                
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Teaching deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, teaching_inputs):
        try:
            existing_teaching = self.db.query(TeachingModel).filter(TeachingModel.id == id).one_or_none()

            if not existing_teaching:
                return {"status": "error", "message": "No data found"}

            for key, value in teaching_inputs.items():
                setattr(existing_teaching, key, value)

            existing_teaching.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_teaching)

            return {"status": "success", "message": "Teaching updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(self, school_id: int, inspection_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserta enseñanzas desde Inspection usando el **id remoto** como PK local (`teachings.id`).
        - Si ya existe el mismo id activo, mismo colegio y mismo nombre (sin distinguir mayúsculas): omite.
        - Si ya existe el mismo id activo, mismo colegio y distinto nombre: error en listado.
        - Si el id está en otro colegio: no inserta (error).
        - Si existe el mismo id pero eliminado (soft): reactiva y actualiza datos.
        """
        try:
            rows = _extract_teachings_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                name = _teaching_name_from_row(row)
                if not name:
                    continue
                inspection_id = _inspection_catalog_id_from_row(row)
                if inspection_id is None:
                    errors.append({"name": name, "message": "Fila sin id de Inspection"})
                    continue

                type_id = _teaching_type_id_from_row(row)
                name_norm = name.strip().lower()

                existing = (
                    self.db.query(TeachingModel)
                    .filter(TeachingModel.id == inspection_id)
                    .first()
                )

                if existing:
                    if existing.deleted_status_id != 0:
                        existing.school_id = school_id
                        existing.teaching_name = name
                        existing.teaching_type_id = type_id
                        existing.deleted_status_id = 0
                        existing.updated_date = datetime.now()
                        self.db.commit()
                        imported += 1
                        continue

                    same_school = existing.school_id == school_id
                    same_name = (existing.teaching_name or "").strip().lower() == name_norm
                    if same_school and same_name:
                        skipped += 1
                        continue
                    if same_school and not same_name:
                        errors.append(
                            {
                                "name": name,
                                "message": (
                                    f"Ya existe enseñanza id={inspection_id} con otro nombre "
                                    f"({existing.teaching_name!r})"
                                ),
                            }
                        )
                        continue

                    errors.append(
                        {
                            "name": name,
                            "message": (
                                f"El id {inspection_id} de Inspection ya está asignado a otro colegio "
                                f"(school_id={existing.school_id})"
                            ),
                        }
                    )
                    continue

                res = self.store(
                    {
                        "id": inspection_id,
                        "school_id": school_id,
                        "teaching_type_id": type_id,
                        "teaching_name": name,
                    }
                )
                if res.get("status") == "success":
                    imported += 1
                else:
                    errors.append({"name": name, "message": str(res.get("message", "Error"))})

            return {
                "status": "success",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

