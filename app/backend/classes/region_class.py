from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.backend.db.models import RegionModel


def _extract_inspection_rows(inspection_body: Dict[str, Any]) -> List[Dict[str, Any]]:
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


def _region_name_from_row(row: Dict[str, Any]) -> Optional[str]:
    for k in ("nombre", "region", "name", "descripcion", "glosa"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:255]
    return None


class RegionClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, region_name=None, page=0, items_per_page=10):
        try:
            query = self.db.query(
                RegionModel.id,
                RegionModel.region,
                RegionModel.added_date,
                RegionModel.updated_date,
            )

            if region_name and region_name.strip():
                query = query.filter(RegionModel.region.like(f"%{region_name.strip()}%"))

            query = query.order_by(RegionModel.id)

            page_val = 0 if page is None else int(page)

            if page_val > 0:
                ipp = items_per_page or 10
                if page_val < 1:
                    page_val = 1

                total_items = query.count()
                total_pages = (total_items + ipp - 1) // ipp if ipp else 0

                if total_items == 0 or total_pages == 0 or page_val > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page_val,
                        "items_per_page": ipp,
                        "data": [],
                    }

                data = query.offset((page_val - 1) * ipp).limit(ipp).all()
            else:
                data = query.all()

            serialized_data = [
                {
                    "id": region.id,
                    "region": region.region,
                    "added_date": region.added_date.strftime("%Y-%m-%d %H:%M:%S") if region.added_date else None,
                    "updated_date": region.updated_date.strftime("%Y-%m-%d %H:%M:%S") if region.updated_date else None,
                }
                for region in data
            ]

            if page_val > 0:
                ipp = items_per_page or 10
                total_items = query.count()
                total_pages = (total_items + ipp - 1) // ipp if ipp else 0
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page_val,
                    "items_per_page": ipp,
                    "data": serialized_data,
                }

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            data_query = (
                self.db.query(
                    RegionModel.id,
                    RegionModel.region,
                    RegionModel.added_date,
                    RegionModel.updated_date,
                )
                .filter(RegionModel.id == id)
                .first()
            )

            if data_query:
                region_data = {
                    "id": data_query.id,
                    "region": data_query.region,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None,
                }

                return {"region_data": region_data}

            else:
                return {"error": "No se encontraron datos para la region especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, region_inputs):
        try:
            row_kwargs = {
                "region": region_inputs["region"],
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
            }
            if region_inputs.get("id") is not None:
                row_kwargs["id"] = int(region_inputs["id"])
            else:
                max_id = self.db.query(func.max(RegionModel.id)).scalar()
                row_kwargs["id"] = (int(max_id) if max_id is not None else 0) + 1

            new_region = RegionModel(**row_kwargs)

            self.db.add(new_region)
            self.db.commit()
            self.db.refresh(new_region)

            return {
                "status": "success",
                "message": "Region created successfully",
                "region_id": new_region.id,
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(self, inspection_body: Dict[str, Any]) -> Dict[str, Any]:
        """Inserta/actualiza regiones usando id remoto como PK local."""
        try:
            rows = _extract_inspection_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                name = _region_name_from_row(row)
                if not name:
                    continue
                inspection_id = _inspection_int(row.get("id"))
                if inspection_id is None:
                    errors.append({"name": str(row), "message": "Fila sin id de Inspection"})
                    continue

                name_norm = name.strip().lower()

                existing = self.db.query(RegionModel).filter(RegionModel.id == inspection_id).first()

                if existing:
                    same = (existing.region or "").strip().lower() == name_norm
                    if same:
                        skipped += 1
                        continue
                    existing.region = name
                    existing.updated_date = datetime.now()
                    self.db.commit()
                    imported += 1
                    continue

                res = self.store(
                    {
                        "id": inspection_id,
                        "region": name,
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

    def delete(self, id):
        try:
            data = self.db.query(RegionModel).filter(RegionModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Region deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, region_inputs):
        try:
            existing_region = self.db.query(RegionModel).filter(RegionModel.id == id).one_or_none()

            if not existing_region:
                return {"status": "error", "message": "No data found"}

            for key, value in region_inputs.items():
                setattr(existing_region, key, value)

            existing_region.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_region)

            return {"status": "success", "message": "Region updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
