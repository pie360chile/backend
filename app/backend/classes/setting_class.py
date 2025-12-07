from app.backend.db.models import SettingModel
from datetime import datetime
import requests

class SettingClass:
    def __init__(self, db):
        self.db = db

    def update(self, id, form_data):
        existing_setting = self.db.query(SettingModel).filter(SettingModel.id == id).one_or_none()

        if not existing_setting:
            return {"status": "error", "message": "No data found"}

        try:
            for key, value in form_data.items():
                setattr(existing_setting, key, value)
            
            existing_setting.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_setting)
            return {"status": "success", "message": "Settings updated successfully"}
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            data_query = self.db.query(
                SettingModel
            ).filter(SettingModel.id == id).first()

            if data_query:
                setting_data = {
                    "id": data_query.id,
                    "company_email": data_query.company_email,
                    "company_phone": data_query.company_phone,
                    "company_whatsapp": data_query.company_whatsapp
                }

                return {"setting_data": setting_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}