from app.backend.db.models import SettingCompanyModel
from datetime import datetime

class SettingCompanyClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = self.db.query(SettingCompanyModel)

            # Ordenar por fecha de creación descendente
            query = query.order_by(SettingCompanyModel.added_date.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            offset = page * items_per_page
            settings = query.offset(offset).limit(items_per_page).all()

            if not settings:
                return {
                    "status": "error",
                    "message": "No data found",
                    "data": None,
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page
                }

            # Calcular total de páginas
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Convertir a diccionarios
            settings_list = []
            for setting in settings:
                setting_dict = {
                    "id": setting.id,
                    "company_email": setting.company_email,
                    "company_phone": setting.company_phone,
                    "company_whatsapp": setting.company_whatsapp,
                    "added_date": setting.added_date.strftime('%Y-%m-%d %H:%M:%S') if setting.added_date else None,
                    "updated_date": setting.updated_date.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_date else None
                }
                settings_list.append(setting_dict)

            return {
                "status": "success",
                "data": settings_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, setting_id):
        try:
            setting = self.db.query(SettingCompanyModel).filter(
                SettingCompanyModel.id == setting_id
            ).first()

            if not setting:
                return {
                    "status": "error",
                    "message": "Setting not found"
                }

            setting_dict = {
                "id": setting.id,
                "company_email": setting.company_email,
                "company_phone": setting.company_phone,
                "company_whatsapp": setting.company_whatsapp,
                "added_date": setting.added_date.strftime('%Y-%m-%d %H:%M:%S') if setting.added_date else None,
                "updated_date": setting.updated_date.strftime('%Y-%m-%d %H:%M:%S') if setting.updated_date else None
            }

            return setting_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, setting_data):
        try:
            new_setting = SettingCompanyModel(
                company_email=setting_data.get('company_email'),
                company_phone=setting_data.get('company_phone'),
                company_whatsapp=setting_data.get('company_whatsapp'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_setting)
            self.db.commit()
            self.db.refresh(new_setting)

            return {
                "status": "success",
                "message": "Setting created successfully",
                "data": {
                    "id": new_setting.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, setting_id, setting_data):
        try:
            setting = self.db.query(SettingCompanyModel).filter(
                SettingCompanyModel.id == setting_id
            ).first()

            if not setting:
                return {
                    "status": "error",
                    "message": "Setting not found"
                }

            # Actualizar campos
            if setting_data.get('company_email') is not None:
                setting.company_email = setting_data.get('company_email')
            
            if setting_data.get('company_phone') is not None:
                setting.company_phone = setting_data.get('company_phone')
            
            if setting_data.get('company_whatsapp') is not None:
                setting.company_whatsapp = setting_data.get('company_whatsapp')

            setting.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Setting updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, setting_id):
        try:
            setting = self.db.query(SettingCompanyModel).filter(
                SettingCompanyModel.id == setting_id
            ).first()

            if not setting:
                return {
                    "status": "error",
                    "message": "Setting not found"
                }

            # Hard delete
            self.db.delete(setting)
            self.db.commit()

            return {
                "status": "success",
                "message": "Setting deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
