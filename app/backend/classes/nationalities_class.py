from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.backend.db.models import NationalityModel


def _extract_inspection_nationality_rows(inspection_body: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not inspection_body.get("ok"):
        return []
    raw = inspection_body.get("data")
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return []


def _inspection_int(v: Any) -> Optional[int]:
    if v is None or (isinstance(v, str) and not str(v).strip()):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _nationality_label_from_inspection_row(row: Dict[str, Any]) -> Optional[str]:
    """Prioriza país legible; si no, gentilicio; si no, ISO."""
    pais = str(row.get("pais") or "").strip()
    if pais:
        return pais[:255]
    gent = str(row.get("gentilicio") or "").strip()
    if gent:
        return gent[:255]
    iso = str(row.get("iso") or "").strip()
    if iso:
        return iso[:255]
    return None

class NationalitiesClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, nationality=None):
        try:
            query = self.db.query(
                NationalityModel.id,
                NationalityModel.nationality,
                NationalityModel.added_date,
                NationalityModel.updated_date
            ).filter(NationalityModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona nationality
            if nationality and nationality.strip():
                query = query.filter(NationalityModel.nationality.like(f"%{nationality.strip()}%"))

            query = query.order_by(NationalityModel.id)

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
                    "id": nat.id,
                    "nationality": nat.nationality,
                    "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                    "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
                } for nat in data]

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
                    "id": nat.id,
                    "nationality": nat.nationality,
                    "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                    "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
                } for nat in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todas las nationalities sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                NationalityModel.id,
                NationalityModel.nationality,
                NationalityModel.added_date,
                NationalityModel.updated_date
            ).filter(NationalityModel.deleted_status_id == 0).order_by(NationalityModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": nat.id,
                "nationality": nat.nationality,
                "added_date": nat.added_date.strftime("%Y-%m-%d %H:%M:%S") if nat.added_date else None,
                "updated_date": nat.updated_date.strftime("%Y-%m-%d %H:%M:%S") if nat.updated_date else None
            } for nat in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(NationalityModel).filter(NationalityModel.id == id).first()

            if data_query:
                nationality_data = {
                    "id": data_query.id,
                    "nationality": data_query.nationality,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"nationality_data": nationality_data}

            else:
                return {"error": "No se encontraron datos para la nationality especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, nationality_inputs):
        try:
            row_kwargs: Dict[str, Any] = {
                "nationality": nationality_inputs["nationality"],
                "deleted_status_id": int(nationality_inputs.get("deleted_status_id", 0)),
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
            }
            if nationality_inputs.get("id") is not None:
                row_kwargs["id"] = int(nationality_inputs["id"])
            else:
                max_id = self.db.query(func.max(NationalityModel.id)).scalar()
                row_kwargs["id"] = (int(max_id) if max_id is not None else 0) + 1

            new_nationality = NationalityModel(**row_kwargs)

            self.db.add(new_nationality)
            self.db.commit()
            self.db.refresh(new_nationality)

            return {
                "status": "success",
                "message": "Nationality created successfully",
                "nationality_id": new_nationality.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(self, inspection_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserta nacionalidades desde Inspection (`GET listado/nacionalidades`) usando el **id remoto**
        como PK local (`nationalities.id`). Campo `nationality`: preferente `pais`, luego `gentilicio` / `iso`.
        """
        try:
            rows = _extract_inspection_nationality_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                name = _nationality_label_from_inspection_row(row)
                if not name:
                    continue
                inspection_id = _inspection_int(row.get("id"))
                if inspection_id is None:
                    errors.append({"name": name, "message": "Fila sin id de Inspection"})
                    continue

                name_norm = name.strip().lower()

                existing = self.db.query(NationalityModel).filter(NationalityModel.id == inspection_id).first()

                if existing:
                    if int(existing.deleted_status_id or 0) != 0:
                        existing.nationality = name
                        existing.deleted_status_id = 0
                        existing.updated_date = datetime.now()
                        self.db.commit()
                        imported += 1
                        continue

                    same_name = (existing.nationality or "").strip().lower() == name_norm
                    if same_name:
                        skipped += 1
                        continue

                    errors.append(
                        {
                            "name": name,
                            "message": (
                                f"Ya existe nacionalidad id={inspection_id} con otro nombre "
                                f"({existing.nationality!r})"
                            ),
                        }
                    )
                    continue

                res = self.store({"id": inspection_id, "nationality": name, "deleted_status_id": 0})
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
    
    def delete(self, id):
        try:
            data = self.db.query(NationalityModel).filter(NationalityModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Nationality deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, nationality_inputs):
        try:
            existing_nationality = self.db.query(NationalityModel).filter(NationalityModel.id == id).one_or_none()

            if not existing_nationality:
                return {"status": "error", "message": "No data found"}

            for key, value in nationality_inputs.items():
                setattr(existing_nationality, key, value)

            existing_nationality.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_nationality)

            return {"status": "success", "message": "Nationality updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

