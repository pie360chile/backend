from datetime import datetime
from app.backend.db.models import PermissionModel

class PermissionClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, permission=None):
        try:
            query = self.db.query(
                PermissionModel.id,
                PermissionModel.permission,
                PermissionModel.added_date,
                PermissionModel.updated_date
            )

            # Aplicar filtro de búsqueda si se proporciona permission
            if permission and permission.strip():
                query = query.filter(PermissionModel.permission.like(f"%{permission.strip()}%"))

            query = query.order_by(PermissionModel.id)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": permission_item.id,
                    "permission": permission_item.permission,
                    "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                    "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
                } for permission_item in data]

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
                    "id": permission_item.id,
                    "permission": permission_item.permission,
                    "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                    "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
                } for permission_item in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todos los permissions sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                PermissionModel.id,
                PermissionModel.permission,
                PermissionModel.added_date,
                PermissionModel.updated_date
            ).order_by(PermissionModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": permission_item.id,
                "permission": permission_item.permission,
                "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
            } for permission_item in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                PermissionModel.id,
                PermissionModel.permission,
                PermissionModel.added_date,
                PermissionModel.updated_date
            ).filter(PermissionModel.id == id).first()

            if data_query:
                permission_data = {
                    "id": data_query.id,
                    "permission": data_query.permission,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"permission_data": permission_data}

            else:
                return {"error": "No se encontraron datos para el permission especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, permission_inputs):
        try:
            new_permission = PermissionModel(
                permission=permission_inputs['permission'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_permission)
            self.db.commit()
            self.db.refresh(new_permission)

            return {
                "status": "success",
                "message": "Permission created successfully",
                "permission_id": new_permission.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(PermissionModel).filter(PermissionModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Permission deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, permission_inputs):
        try:
            existing_permission = self.db.query(PermissionModel).filter(PermissionModel.id == id).one_or_none()

            if not existing_permission:
                return {"status": "error", "message": "No data found"}

            for key, value in permission_inputs.items():
                setattr(existing_permission, key, value)

            existing_permission.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_permission)

            return {"status": "success", "message": "Permission updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

