from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from app.backend.db.models import CommuneModel, ProvinceModel, RegionModel


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


def _commune_name_from_row(row: Dict[str, Any]) -> Optional[str]:
    for k in ("nombre", "commune", "comuna", "name", "glosa"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:255]
    return None


def _region_id_from_row(row: Dict[str, Any]) -> Optional[int]:
    """Si la API ya trae la región (poco frecuente en listado/comunas)."""
    for k in ("region_id", "id_region", "idRegion", "regionId"):
        n = _inspection_int(row.get(k))
        if n is not None:
            return n
    return None


def _provincia_id_from_row(row: Dict[str, Any]) -> Optional[int]:
    """Inspection `GET listado/comunas`: cada fila trae `provincia_id`, no `region_id`."""
    for k in ("provincia_id", "id_provincia", "provinciaId", "idProvincia"):
        n = _inspection_int(row.get(k))
        if n is not None:
            return n
    return None


def _resolve_region_id_for_commune_import(db, row: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    """
    Devuelve (region_id, None) o (None, mensaje de error).
    Resuelve provincia_id → region_id vía tabla `provinces` (mismos ids remotos que Inspection).
    """
    rid = _region_id_from_row(row)
    if rid is not None:
        return rid, None

    pid = _provincia_id_from_row(row)
    if pid is None:
        return None, "Fila sin region_id ni provincia_id (formato Inspection listado/comunas)"

    prov = db.query(ProvinceModel).filter(ProvinceModel.id == pid).first()
    if prov is None:
        return None, (
            f"No existe provincia en BD con id={pid} para resolver la región. "
            "Importe provincias desde Inspection antes que las comunas."
        )
    if prov.region_id is None:
        return None, f"La provincia id={pid} no tiene region_id en BD"

    return int(prov.region_id), None


class CommuneClass:
    def __init__(self, db):
        self.db = db

    def _base_query(self, commune_name=None, region_id=None):
        q = self.db.query(
            CommuneModel.id,
            CommuneModel.region_id,
            CommuneModel.commune,
            CommuneModel.added_date,
            CommuneModel.updated_date,
            RegionModel.region,
        ).outerjoin(RegionModel, CommuneModel.region_id == RegionModel.id)

        if commune_name and commune_name.strip():
            q = q.filter(CommuneModel.commune.like(f"%{commune_name.strip()}%"))

        if region_id is not None:
            q = q.filter(CommuneModel.region_id == region_id)

        return q.order_by(CommuneModel.id)

    def get_all(self, commune_name=None, region_id=None, page=0, items_per_page=10):
        try:
            query = self._base_query(commune_name=commune_name, region_id=region_id)
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
                    "id": commune.id,
                    "region_id": commune.region_id,
                    "commune": commune.commune,
                    "region": commune.region,
                    "added_date": commune.added_date.strftime("%Y-%m-%d %H:%M:%S") if commune.added_date else None,
                    "updated_date": commune.updated_date.strftime("%Y-%m-%d %H:%M:%S") if commune.updated_date else None,
                }
                for commune in data
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
            data_query = self._base_query().filter(CommuneModel.id == id).first()

            if data_query:
                commune_data = {
                    "id": data_query.id,
                    "region_id": data_query.region_id,
                    "commune": data_query.commune,
                    "region": data_query.region,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None,
                }

                return {"commune_data": commune_data}

            else:
                return {"error": "No se encontraron datos para la commune especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, commune_inputs):
        try:
            row_kwargs = {
                "region_id": commune_inputs["region_id"],
                "commune": commune_inputs["commune"],
                "added_date": datetime.now(),
                "updated_date": datetime.now(),
            }
            if commune_inputs.get("id") is not None:
                row_kwargs["id"] = int(commune_inputs["id"])
            else:
                max_id = self.db.query(func.max(CommuneModel.id)).scalar()
                row_kwargs["id"] = (int(max_id) if max_id is not None else 0) + 1

            new_commune = CommuneModel(**row_kwargs)

            self.db.add(new_commune)
            self.db.commit()
            self.db.refresh(new_commune)

            return {
                "status": "success",
                "message": "Commune created successfully",
                "commune_id": new_commune.id,
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
                name = _commune_name_from_row(row)
                if not name:
                    continue
                inspection_id = _inspection_int(row.get("id"))
                if inspection_id is None:
                    errors.append({"name": str(row), "message": "Fila sin id de Inspection"})
                    continue

                rid, rid_err = _resolve_region_id_for_commune_import(self.db, row)
                if rid is None:
                    errors.append({"name": name, "message": rid_err or "Sin región para la comuna"})
                    continue

                name_norm = name.strip().lower()
                existing = self.db.query(CommuneModel).filter(CommuneModel.id == inspection_id).first()

                if existing:
                    same = (existing.commune or "").strip().lower() == name_norm
                    same_r = (existing.region_id or None) == rid
                    if same and same_r:
                        skipped += 1
                        continue
                    existing.commune = name
                    existing.region_id = rid
                    existing.updated_date = datetime.now()
                    self.db.commit()
                    imported += 1
                    continue

                res = self.store({"id": inspection_id, "region_id": rid, "commune": name})
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
            data = self.db.query(CommuneModel).filter(CommuneModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Commune deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, commune_inputs):
        try:
            existing_commune = self.db.query(CommuneModel).filter(CommuneModel.id == id).one_or_none()

            if not existing_commune:
                return {"status": "error", "message": "No data found"}

            for key, value in commune_inputs.items():
                setattr(existing_commune, key, value)

            existing_commune.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_commune)

            return {"status": "success", "message": "Commune updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
