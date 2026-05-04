from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.backend.db.models import ProvinceModel, RegionModel


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


def _province_name_from_row(row: Dict[str, Any]) -> Optional[str]:
    for k in ("nombre", "province", "provincia", "name", "glosa"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:255]
    return None


def _region_id_from_row(row: Dict[str, Any]) -> Optional[int]:
    for k in ("region_id", "id_region", "idRegion", "regionId", "codigo_region"):
        n = _inspection_int(row.get(k))
        if n is not None:
            return n
    return None


class ProvinceClass:
    def __init__(self, db):
        self.db = db

    def _base_query(self, province_name=None, region_id=None):
        q = self.db.query(
            ProvinceModel.id,
            ProvinceModel.province,
            ProvinceModel.region_id,
            ProvinceModel.added_date,
            ProvinceModel.updated_date,
            RegionModel.region,
        ).outerjoin(RegionModel, ProvinceModel.region_id == RegionModel.id)

        if province_name and province_name.strip():
            q = q.filter(ProvinceModel.province.like(f"%{province_name.strip()}%"))

        if region_id is not None:
            q = q.filter(ProvinceModel.region_id == region_id)

        return q.order_by(ProvinceModel.id)

    def get_all(self, province_name=None, region_id=None, page=0, items_per_page=10):
        try:
            query = self._base_query(province_name=province_name, region_id=region_id)
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
                    "id": p.id,
                    "province": p.province,
                    "region_id": p.region_id,
                    "region": p.region,
                    "added_date": p.added_date.strftime("%Y-%m-%d %H:%M:%S") if p.added_date else None,
                    "updated_date": p.updated_date.strftime("%Y-%m-%d %H:%M:%S") if p.updated_date else None,
                }
                for p in data
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
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self._base_query().filter(ProvinceModel.id == id).first()

            if data_query:
                return {
                    "province_data": {
                        "id": data_query.id,
                        "province": data_query.province,
                        "region_id": data_query.region_id,
                        "region": data_query.region,
                        "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                        "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None,
                    }
                }

            return {"error": "No se encontraron datos para la provincia especificada."}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, province_inputs):
        try:
            row_kwargs = {
                "province": province_inputs["province"],
                "region_id": province_inputs["region_id"],
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
            }
            if province_inputs.get("id") is not None:
                row_kwargs["id"] = int(province_inputs["id"])
            else:
                max_id = self.db.query(func.max(ProvinceModel.id)).scalar()
                row_kwargs["id"] = (int(max_id) if max_id is not None else 0) + 1

            new_row = ProvinceModel(**row_kwargs)
            self.db.add(new_row)
            self.db.commit()
            self.db.refresh(new_row)

            return {
                "status": "success",
                "message": "Province created successfully",
                "province_id": new_row.id,
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def import_from_inspection(self, inspection_body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rows = _extract_inspection_rows(inspection_body)
            imported = 0
            skipped = 0
            errors: List[Dict[str, str]] = []

            for row in rows:
                name = _province_name_from_row(row)
                if not name:
                    continue
                inspection_id = _inspection_int(row.get("id"))
                if inspection_id is None:
                    errors.append({"name": str(row), "message": "Fila sin id de Inspection"})
                    continue

                rid = _region_id_from_row(row)
                if rid is None:
                    errors.append({"name": name, "message": "Fila sin region_id / id_region"})
                    continue

                name_norm = name.strip().lower()
                existing = self.db.query(ProvinceModel).filter(ProvinceModel.id == inspection_id).first()

                if existing:
                    same = (existing.province or "").strip().lower() == name_norm
                    same_r = (existing.region_id or None) == rid
                    if same and same_r:
                        skipped += 1
                        continue
                    existing.province = name
                    existing.region_id = rid
                    existing.updated_date = datetime.now()
                    self.db.commit()
                    imported += 1
                    continue

                res = self.store({"id": inspection_id, "region_id": rid, "province": name})
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
            data = self.db.query(ProvinceModel).filter(ProvinceModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Province deleted successfully"}
            return {"status": "error", "message": "No data found"}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id, province_inputs):
        try:
            existing = self.db.query(ProvinceModel).filter(ProvinceModel.id == id).one_or_none()
            if not existing:
                return {"status": "error", "message": "No data found"}

            for key, value in province_inputs.items():
                setattr(existing, key, value)

            existing.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(existing)

            return {"status": "success", "message": "Province updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
