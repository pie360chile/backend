"""Lógica para differentiated_strategies_implementations."""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.backend.db.models import DifferentiatedStrategiesImplementationModel


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


class DifferentiatedStrategiesImplementationClass:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, page: int = 0, items_per_page: int = 100, actions_taken: Optional[str] = None, applied_strategies: Optional[str] = None) -> Any:
        """Lista implementaciones activas (deleted_date is None)."""
        try:
            query = self.db.query(DifferentiatedStrategiesImplementationModel).filter(
                DifferentiatedStrategiesImplementationModel.deleted_date.is_(None)
            )
            if actions_taken and str(actions_taken).strip():
                query = query.filter(DifferentiatedStrategiesImplementationModel.actions_taken.like(f"%{actions_taken.strip()}%"))
            if applied_strategies and str(applied_strategies).strip():
                query = query.filter(DifferentiatedStrategiesImplementationModel.applied_strategies.like(f"%{applied_strategies.strip()}%"))
            query = query.order_by(DifferentiatedStrategiesImplementationModel.id.desc())
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
                        "period_id": r.period_id,
                        "actions_taken": r.actions_taken,
                        "applied_strategies": r.applied_strategies,
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
                    "period_id": r.period_id,
                    "actions_taken": r.actions_taken,
                    "applied_strategies": r.applied_strategies,
                    "added_date": _date_str(r.added_date),
                    "updated_date": _date_str(r.updated_date),
                }
                for r in rows
            ]
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id: int) -> Any:
        """Obtiene una implementación por id."""
        try:
            row = (
                self.db.query(DifferentiatedStrategiesImplementationModel)
                .filter(
                    DifferentiatedStrategiesImplementationModel.id == id,
                    DifferentiatedStrategiesImplementationModel.deleted_date.is_(None),
                )
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            return {
                "status": "success",
                "data": {
                    "id": row.id,
                    "period_id": row.period_id,
                    "actions_taken": row.actions_taken,
                    "applied_strategies": row.applied_strategies,
                    "added_date": _date_str(row.added_date),
                    "updated_date": _date_str(row.updated_date),
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> Any:
        """Crea una implementación."""
        try:
            period_id = data.get("period_id")
            period_id = int(period_id) if period_id is not None else None
            actions_taken = (data.get("actions_taken") or "").strip() or None
            applied_strategies = (data.get("applied_strategies") or "").strip() or None
            now = datetime.now()
            row = DifferentiatedStrategiesImplementationModel(
                period_id=period_id,
                actions_taken=actions_taken,
                applied_strategies=applied_strategies,
                added_date=now,
                updated_date=now,
                deleted_date=None,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro creado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una implementación por id."""
        try:
            row = self.db.query(DifferentiatedStrategiesImplementationModel).filter(DifferentiatedStrategiesImplementationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "period_id" in data:
                row.period_id = int(data["period_id"]) if data["period_id"] is not None else None
            if "actions_taken" in data:
                row.actions_taken = (data["actions_taken"] or "").strip() or None
            if "applied_strategies" in data:
                row.applied_strategies = (data["applied_strategies"] or "").strip() or None
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
            row = self.db.query(DifferentiatedStrategiesImplementationModel).filter(DifferentiatedStrategiesImplementationModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = row.deleted_date
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado.", "id": id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
