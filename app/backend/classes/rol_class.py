from datetime import datetime

from sqlalchemy import func

from app.backend.db.models import RolModel, RolPermissionModel, PermissionModel, SchoolModel
from app.backend.classes.school_class import SchoolClass

# Roles por establecimiento (cliente): se crean por cada `school_id` con permisos en `rols_permissions`.
INSTITUTION_ROLE_NAMES = ("Administrador", "Evaluador", "Coordinador", "Profesional")


class RolClass:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def default_permission_ids_for_institution_role(rol_display_name: str) -> list:
        """Permisos por defecto si el cliente aún no tiene otro rol del mismo nombre para copiar."""
        name = (rol_display_name or "").strip()
        mapping = {
            "Profesional": [40, 41],
            "Coordinador": [1, 2, 3, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 40, 41],
            "Evaluador": [1, 2, 3, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 40, 41],
            # Alineado con scripts/seed_liceo_mixto_san_felipe_users.py (rol Administrador institución)
            "Administrador": [1, 2, 3, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 40, 41, 43, 44, 56],
        }
        return list(mapping.get(name, []))

    def _permission_ids_for_rol(self, rol_id: int) -> list:
        rows = (
            self.db.query(RolPermissionModel.permission_id)
            .filter(RolPermissionModel.rol_id == rol_id)
            .all()
        )
        return [r[0] for r in rows]

    def _template_rol_id_same_name(self, customer_id: int, target_school_id: int, rol_name: str):
        """
        Busca otro rol del mismo cliente con el mismo nombre (insensible a mayúsculas)
        para reutilizar los mismos permission_id en rols_permissions.
        Prioriza otra escuela activa; luego cualquier otra escuela; luego la misma escuela si aplica.
        """
        key = (rol_name or "").strip().lower()
        if not key:
            return None

        q1 = (
            self.db.query(RolModel.id)
            .join(SchoolModel, SchoolModel.id == RolModel.school_id)
            .filter(
                RolModel.customer_id == customer_id,
                RolModel.deleted_status_id == 0,
                SchoolModel.deleted_status_id == 0,
                func.lower(func.trim(RolModel.rol)) == key,
                RolModel.school_id != target_school_id,
            )
            .order_by(RolModel.id)
            .first()
        )
        if q1:
            return q1[0]

        q2 = (
            self.db.query(RolModel.id)
            .filter(
                RolModel.customer_id == customer_id,
                RolModel.deleted_status_id == 0,
                func.lower(func.trim(RolModel.rol)) == key,
                RolModel.school_id != target_school_id,
            )
            .order_by(RolModel.id)
            .first()
        )
        if q2:
            return q2[0]

        q3 = (
            self.db.query(RolModel.id)
            .filter(
                RolModel.customer_id == customer_id,
                RolModel.deleted_status_id == 0,
                func.lower(func.trim(RolModel.rol)) == key,
            )
            .order_by(RolModel.id)
            .first()
        )
        return q3[0] if q3 else None

    def _resolve_permissions_for_new_institution_role(
        self, customer_id: int, target_school_id: int, rol_name: str
    ) -> list:
        template_rol_id = self._template_rol_id_same_name(customer_id, target_school_id, rol_name)
        if template_rol_id:
            ids = self._permission_ids_for_rol(template_rol_id)
            if ids:
                return ids
        return self.default_permission_ids_for_institution_role(rol_name)

    def institution_role_exists_at_school(self, customer_id: int, school_id: int, rol_name: str) -> bool:
        key = (rol_name or "").strip().lower()
        row = (
            self.db.query(RolModel.id)
            .filter(
                RolModel.customer_id == customer_id,
                RolModel.school_id == school_id,
                RolModel.deleted_status_id == 0,
                func.lower(func.trim(RolModel.rol)) == key,
            )
            .first()
        )
        return row is not None

    def ensure_institution_roles_for_school(self, customer_id: int, school_id: int) -> dict:
        """
        Crea en `rols` (con `school_id` y `customer_id`) los cuatro roles de institución si faltan,
        y rellena `rols_permissions` copiando los permisos de un rol homónimo del mismo cliente
        cuando exista; si no, usa permisos por defecto.
        """
        details = []
        for rol_name in INSTITUTION_ROLE_NAMES:
            if self.institution_role_exists_at_school(customer_id, school_id, rol_name):
                details.append({"rol": rol_name, "action": "skipped", "reason": "already_exists"})
                continue
            perms = self._resolve_permissions_for_new_institution_role(customer_id, school_id, rol_name)
            res = self.store(
                {
                    "customer_id": customer_id,
                    "school_id": school_id,
                    "rol": rol_name,
                    "permissions": perms,
                }
            )
            details.append({"rol": rol_name, "result": res})
        return {"status": "success", "school_id": school_id, "details": details}

    def ensure_institution_roles_for_all_customer_schools(self, customer_id: int) -> dict:
        """Asegura los cuatro roles en cada escuela activa del cliente."""
        school_ids = [
            r[0]
            for r in self.db.query(SchoolModel.id)
            .filter(SchoolModel.customer_id == customer_id, SchoolModel.deleted_status_id == 0)
            .order_by(SchoolModel.id)
            .all()
        ]
        out = []
        for sid in school_ids:
            out.append(self.ensure_institution_roles_for_school(customer_id, sid))
        return {"status": "success", "customer_id": customer_id, "schools": out}

    def get_all(self, page=0, items_per_page=10, customer_id=None, school_id=None, rol=None):
        try:
            # Si viene customer_id, obtener el school específico para validar la relación
            if customer_id and not school_id:
                school_result = SchoolClass(self.db).get(customer_id=customer_id)
                # Si no existe el school o no pertenece al customer, retornar vacío
                if "error" in school_result or "status" in school_result:
                    if page > 0:
                        return {
                            "total_items": 0,
                            "total_pages": 0,
                            "current_page": page,
                            "items_per_page": items_per_page,
                            "data": []
                        }
                    else:
                        return []
                
                school_id = school_result.get('school_data', {}).get('id')
            
            query = self.db.query(
                RolModel.id,
                RolModel.customer_id,
                RolModel.school_id,
                RolModel.deleted_status_id,
                RolModel.rol,
                RolModel.added_date,
                RolModel.updated_date
            ).filter(RolModel.deleted_status_id == 0)
            
            if school_id:
                query = query.filter(RolModel.school_id == school_id)
            
            # Aplicar filtro de búsqueda si se proporciona rol
            if rol and rol.strip():
                query = query.filter(RolModel.rol.like(f"%{rol.strip()}%"))

            query = query.order_by(RolModel.id)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if total_items == 0 or (page < 1 or page > total_pages):
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": rol_item.id,
                    "customer_id": rol_item.customer_id,
                    "school_id": rol_item.school_id,
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

                if not data:
                    return []

                serialized_data = [{
                    "id": rol_item.id,
                    "customer_id": rol_item.customer_id,
                    "school_id": rol_item.school_id,
                    "rol": rol_item.rol,
                    "added_date": rol_item.added_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.added_date else None,
                    "updated_date": rol_item.updated_date.strftime("%Y-%m-%d %H:%M:%S") if rol_item.updated_date else None
                } for rol_item in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, rol_id):
        try:
            data_query = self.db.query(
                RolModel.id,
                RolModel.customer_id,
                RolModel.school_id,
                RolModel.deleted_status_id,
                RolModel.rol,
                RolModel.added_date,
                RolModel.updated_date
            ).filter(RolModel.id == rol_id, RolModel.deleted_status_id == 0).first()

            if not data_query:
                return {"error": "No se encontraron datos para el rol especificado."}

            # Obtener los permisos asociados al rol
            permissions_query = self.db.query(
                RolPermissionModel.permission_id
            ).filter(RolPermissionModel.rol_id == rol_id).all()
            
            # Extraer solo los IDs de permisos
            permissions = [perm.permission_id for perm in permissions_query]
            
            rol_data = {
                "id": data_query.id,
                "customer_id": data_query.customer_id,
                "school_id": data_query.school_id,
                "rol": data_query.rol,
                "permissions": permissions,
                "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
            }

            return {"rol_data": rol_data}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, rol_inputs):
        try:
            new_rol = RolModel(
                customer_id=rol_inputs.get('customer_id'),
                school_id=rol_inputs.get('school_id'),
                rol=rol_inputs['rol'],
                deleted_status_id=0,
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
            if data and data.deleted_status_id == 0:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Rol deleted successfully"}
            elif data:
                return {"status": "error", "message": "No data found"}
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