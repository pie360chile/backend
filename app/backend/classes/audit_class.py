from datetime import datetime
from sqlalchemy.orm import Session
from app.backend.db.models import AuditModel
from typing import Any, Optional

class AuditClass:
    def __init__(self, db: Session):
        self.db = db

    def store(self, user_id: int, rol_id: Optional[int] = None) -> dict:
        """
        Crea un nuevo registro de auditoría (login).
        """
        try:
            new_audit = AuditModel(
                user_id=user_id,
                rol_id=rol_id,
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow()
            )
            
            self.db.add(new_audit)
            self.db.commit()
            self.db.refresh(new_audit)
            
            return {
                "status": "success",
                "message": "Registro de auditoría creado exitosamente",
                "audit_data": {
                    "id": new_audit.id,
                    "user_id": new_audit.user_id,
                    "rol_id": new_audit.rol_id,
                    "added_date": new_audit.added_date.strftime("%Y-%m-%d %H:%M:%S") if new_audit.added_date else None,
                    "updated_date": new_audit.updated_date.strftime("%Y-%m-%d %H:%M:%S") if new_audit.updated_date else None
                }
            }
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, user_id: Optional[int] = None, page: int = 0, items_per_page: int = 10) -> Any:
        """
        Obtiene todos los registros de auditoría, opcionalmente filtrados por user_id.
        """
        try:
            filters = []
            if user_id is not None:
                filters.append(AuditModel.user_id == user_id)

            query = self.db.query(AuditModel).filter(*filters).order_by(AuditModel.added_date.desc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or (total_items > 0 and page > total_pages):
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                serialized_data = [{
                    "id": audit.id,
                    "user_id": audit.user_id,
                    "rol_id": audit.rol_id,
                    "added_date": audit.added_date.strftime("%Y-%m-%d %H:%M:%S") if audit.added_date else None,
                    "updated_date": audit.updated_date.strftime("%Y-%m-%d %H:%M:%S") if audit.updated_date else None
                } for audit in data]

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
                    "id": audit.id,
                    "user_id": audit.user_id,
                    "rol_id": audit.rol_id,
                    "added_date": audit.added_date.strftime("%Y-%m-%d %H:%M:%S") if audit.added_date else None,
                    "updated_date": audit.updated_date.strftime("%Y-%m-%d %H:%M:%S") if audit.updated_date else None
                } for audit in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, audit_id: int) -> dict:
        """
        Obtiene un registro de auditoría por su ID.
        """
        try:
            audit = self.db.query(AuditModel).filter(AuditModel.id == audit_id).first()

            if audit:
                return {
                    "status": "success",
                    "audit_data": {
                        "id": audit.id,
                        "user_id": audit.user_id,
                        "rol_id": audit.rol_id,
                        "added_date": audit.added_date.strftime("%Y-%m-%d %H:%M:%S") if audit.added_date else None,
                        "updated_date": audit.updated_date.strftime("%Y-%m-%d %H:%M:%S") if audit.updated_date else None
                    }
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el registro de auditoría especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
