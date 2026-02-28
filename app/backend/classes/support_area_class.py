"""Lógica para support_areas (áreas de apoyo)."""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import case
from sqlalchemy.orm import Session
from app.backend.db.models import SupportAreaModel


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


class SupportAreaClass:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, page: int = 0, items_per_page: int = 100, support_area: Optional[str] = None) -> Any:
        """Lista áreas de apoyo activas (deleted_date is None)."""
        try:
            query = self.db.query(SupportAreaModel).filter(SupportAreaModel.deleted_date.is_(None))
            if support_area and str(support_area).strip():
                query = query.filter(SupportAreaModel.support_area.like(f"%{support_area.strip()}%"))
            # Orden alfabético por nombre; en MySQL NULLS LAST no existe, usamos CASE para poner nulos al final
            query = query.order_by(
                case((SupportAreaModel.support_area.is_(None), 1), else_=0),
                SupportAreaModel.support_area.asc(),
            )
            if page > 0 and items_per_page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page or 1
                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": [],
                    }
                rows = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
                data = [
                    {
                        "id": r.id,
                        "support_area": r.support_area,
                        "added_date": _date_str(r.added_date),
                        "updated_date": _date_str(r.updated_date),
                    }
                    for r in rows
                ]
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": data,
                }
            rows = query.all()
            return [
                {
                    "id": r.id,
                    "support_area": r.support_area,
                    "added_date": _date_str(r.added_date),
                    "updated_date": _date_str(r.updated_date),
                }
                for r in rows
            ]
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id: int) -> Any:
        """Obtiene un área de apoyo por id."""
        try:
            row = (
                self.db.query(SupportAreaModel)
                .filter(SupportAreaModel.id == id, SupportAreaModel.deleted_date.is_(None))
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {
                "status": "success",
                "data": {
                    "id": row.id,
                    "support_area": row.support_area,
                    "added_date": _date_str(row.added_date),
                    "updated_date": _date_str(row.updated_date),
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea un área de apoyo."""
        try:
            support_area = (data.get("support_area") or "").strip() or None
            now = datetime.now()
            row = SupportAreaModel(
                support_area=support_area,
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Área de apoyo creada.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza un área de apoyo por id."""
        try:
            row = self.db.query(SupportAreaModel).filter(SupportAreaModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "support_area" in data:
                row.support_area = (data["support_area"] or "").strip() or None
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico (deleted_date)."""
        try:
            row = self.db.query(SupportAreaModel).filter(SupportAreaModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
