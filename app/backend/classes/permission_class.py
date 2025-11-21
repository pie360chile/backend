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
                PermissionModel.permission_type_id,
                PermissionModel.permission_order_id,
                PermissionModel.added_date,
                PermissionModel.updated_date
            )

            # Aplicar filtro de búsqueda si se proporciona permission
            if permission and permission.strip():
                query = query.filter(PermissionModel.permission.like(f"%{permission.strip()}%"))

            # Ordenar por permission_type_id y permission_order_id
            query = query.order_by(PermissionModel.permission_type_id.asc(), PermissionModel.permission_order_id.asc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                # Agrupar por permission_type_id
                grouped_data = {}
                for permission_item in data:
                    type_id = permission_item.permission_type_id
                    if type_id not in grouped_data:
                        grouped_data[type_id] = []
                    grouped_data[type_id].append({
                        "id": permission_item.id,
                        "permission": permission_item.permission,
                        "permission_type_id": permission_item.permission_type_id,
                        "permission_order_id": permission_item.permission_order_id,
                        "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                        "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
                    })

                # Convertir a lista ordenada por permission_type_id
                serialized_data = []
                for type_id in sorted(grouped_data.keys(), key=lambda x: (x is None, x)):
                    serialized_data.extend(grouped_data[type_id])

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                # Agrupar por permission_type_id
                grouped_data = {}
                for permission_item in data:
                    type_id = permission_item.permission_type_id
                    if type_id not in grouped_data:
                        grouped_data[type_id] = []
                    grouped_data[type_id].append({
                        "id": permission_item.id,
                        "permission": permission_item.permission,
                        "permission_type_id": permission_item.permission_type_id,
                        "permission_order_id": permission_item.permission_order_id,
                        "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                        "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
                    })

                # Convertir a lista ordenada por permission_type_id
                serialized_data = []
                for type_id in sorted(grouped_data.keys(), key=lambda x: (x is None, x)):
                    serialized_data.extend(grouped_data[type_id])

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self, permission_type_id=None):
        """Retorna todos los permissions sin paginación ni búsqueda, agrupados por permission_type_id
        Si permission_type_id se proporciona, filtra solo esos permisos"""
        try:
            query = self.db.query(
                PermissionModel.id,
                PermissionModel.permission,
                PermissionModel.permission_type_id,
                PermissionModel.permission_order_id,
                PermissionModel.added_date,
                PermissionModel.updated_date
            )
            
            # Filtrar por permission_type_id si se proporciona
            if permission_type_id is not None:
                query = query.filter(PermissionModel.permission_type_id == permission_type_id)
            
            query = query.order_by(PermissionModel.permission_type_id.asc(), PermissionModel.permission_order_id.asc())
            
            data = query.all()

            # Agrupar por permission_type_id
            grouped_data = {}
            for permission_item in data:
                type_id = permission_item.permission_type_id
                if type_id not in grouped_data:
                    grouped_data[type_id] = []
                grouped_data[type_id].append({
                    "id": permission_item.id,
                    "permission": permission_item.permission,
                    "permission_type_id": permission_item.permission_type_id,
                    "permission_order_id": permission_item.permission_order_id,
                    "added_date": permission_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.added_date else None,
                    "updated_date": permission_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if permission_item.updated_date else None
                })

            # Convertir a lista ordenada por permission_type_id
            serialized_data = []
            for type_id in sorted(grouped_data.keys(), key=lambda x: (x is None, x)):
                serialized_data.extend(grouped_data[type_id])

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                PermissionModel.id,
                PermissionModel.permission,
                PermissionModel.permission_type_id,
                PermissionModel.permission_order_id,
                PermissionModel.added_date,
                PermissionModel.updated_date
            ).filter(PermissionModel.id == id).first()

            if data_query:
                permission_data = {
                    "id": data_query.id,
                    "permission": data_query.permission,
                    "permission_type_id": data_query.permission_type_id,
                    "permission_order_id": data_query.permission_order_id,
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
                permission_type_id=permission_inputs.get('permission_type_id'),
                permission_order_id=permission_inputs.get('permission_order_id'),
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

