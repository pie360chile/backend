from datetime import datetime
from app.backend.db.models import RolModel, RolPermissionModel, PermissionModel

class RolClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, rol=None):
        try:
            query = self.db.query(
                RolModel.id,
                RolModel.rol,
                RolModel.added_date,
                RolModel.updated_date
            )

            # Aplicar filtro de búsqueda si se proporciona rol
            if rol and rol.strip():
                query = query.filter(RolModel.rol.like(f"%{rol.strip()}%"))

            query = query.order_by(RolModel.id)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": rol_item.id,
                    "rol": rol_item.rol,
                    "added_date": rol_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.added_date else None,
                    "updated_date": rol_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.updated_date else None
                } for rol_item in data]

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
                    "id": rol_item.id,
                    "rol": rol_item.rol,
                    "added_date": rol_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.added_date else None,
                    "updated_date": rol_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.updated_date else None
                } for rol_item in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todos los rols sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                RolModel.id,
                RolModel.rol,
                RolModel.added_date,
                RolModel.updated_date
            ).order_by(RolModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": rol_item.id,
                "rol": rol_item.rol,
                "added_date": rol_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.added_date else None,
                "updated_date": rol_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.updated_date else None
            } for rol_item in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                RolModel.id,
                RolModel.rol,
                RolModel.added_date,
                RolModel.updated_date
            ).filter(RolModel.id == id).first()

            if data_query:
                # Obtener los permisos asociados al rol
                permissions_query = self.db.query(
                    RolPermissionModel.permission_id
                ).filter(RolPermissionModel.rol_id == id).all()
                
                # Extraer solo los IDs de permisos
                permissions = [perm.permission_id for perm in permissions_query]
                
                rol_data = {
                    "id": data_query.id,
                    "rol": data_query.rol,
                    "permissions": permissions,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"rol_data": rol_data}

            else:
                return {"error": "No se encontraron datos para el rol especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, rol_inputs):
        try:
            new_rol = RolModel(
                rol=rol_inputs['rol'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_rol)
            self.db.flush()  # Para obtener el ID sin hacer commit
            
            # Si se proporcionan permisos, crear las relaciones
            permissions = rol_inputs.get('permissions', [])
            if permissions:
                for permission_id in permissions:
                    # Verificar que el permiso existe
                    permission = self.db.query(PermissionModel).filter(PermissionModel.id == permission_id).first()
                    if permission:
                        rol_permission = RolPermissionModel(
                            rol_id=new_rol.id,
                            permission_id=permission_id,
                            added_date=datetime.now(),
                            updated_date=datetime.now()
                        )
                        self.db.add(rol_permission)
            
            self.db.commit()
            self.db.refresh(new_rol)

            return {
                "status": "success",
                "message": "Rol created successfully",
                "rol_id": new_rol.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(RolModel).filter(RolModel.id == id).first()
            if data:
                # Eliminar relaciones con permisos primero
                self.db.query(RolPermissionModel).filter(RolPermissionModel.rol_id == id).delete()
                # Eliminar el rol
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Rol deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, rol_inputs):
        try:
            existing_rol = self.db.query(RolModel).filter(RolModel.id == id).one_or_none()

            if not existing_rol:
                return {"status": "error", "message": "No data found"}

            # Actualizar campos del rol (excepto permissions)
            permissions = None
            if 'permissions' in rol_inputs:
                permissions = rol_inputs.pop('permissions')
            
            for key, value in rol_inputs.items():
                if value is not None:
                    setattr(existing_rol, key, value)

            existing_rol.updated_date = datetime.now()

            # Si se proporcionan permisos, actualizar las relaciones
            if permissions is not None:
                # Eliminar relaciones existentes
                self.db.query(RolPermissionModel).filter(RolPermissionModel.rol_id == id).delete()
                
                # Crear nuevas relaciones
                for permission_id in permissions:
                    # Verificar que el permiso existe
                    permission = self.db.query(PermissionModel).filter(PermissionModel.id == permission_id).first()
                    if permission:
                        rol_permission = RolPermissionModel(
                            rol_id=id,
                            permission_id=permission_id,
                            added_date=datetime.now(),
                            updated_date=datetime.now()
                        )
                        self.db.add(rol_permission)

            self.db.commit()
            self.db.refresh(existing_rol)

            return {"status": "success", "message": "Rol updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}