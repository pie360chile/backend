from app.backend.db.models import SettingModel
from datetime import datetime
import requests

class SettingClass:
    def __init__(self, db):
        self.db = db

    def get_simplefactura_token(self):
        url = "https://api.simplefactura.cl/token"

        payload = {
            "email": "info@vitrificadoschile.com",
            "password": "23414255Jo"
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if 'accessToken' in data:
                existing_setting = self.db.query(SettingModel).filter(SettingModel.id == 1).one_or_none()
                if existing_setting:
                    existing_setting.simplefactura_token = data['accessToken']
                    self.db.commit()
                return data['accessToken']
            else:
                return {"error": "Token not found in response"}

    def validate_token(self):
        setting_data = self.db.query(SettingModel).filter(SettingModel.id == 1).first()
        token = setting_data.simplefactura_token

        url = "https://api.simplefactura.cl/token/expire"

        payload={}
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code == 200:
            return 1
        else:
            return 0

    def update(self, id, form_data):
        existing_setting = self.db.query(SettingModel).filter(SettingModel.id == id).one_or_none()

        if not existing_setting:
            return "No data found"

        try:
            existing_setting.tax_value = form_data.tax_value
            existing_setting.identification_number = form_data.identification_number
            existing_setting.account_type = form_data.account_type
            existing_setting.account_number = form_data.account_number
            existing_setting.account_name = form_data.account_name
            existing_setting.account_email = form_data.account_email
            existing_setting.bank = form_data.bank
            existing_setting.delivery_cost = form_data.delivery_cost
            existing_setting.shop_address = form_data.shop_address
            existing_setting.payment_card_url = form_data.payment_card_url
            existing_setting.prepaid_discount = form_data.prepaid_discount
            existing_setting.phone = form_data.phone
            existing_setting.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_setting)
            return "Settings updated successfully"
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
                    "tax_value": data_query.tax_value,
                    "identification_number": data_query.identification_number,
                    "account_type": data_query.account_type,
                    "account_number": data_query.account_number,
                    "account_name": data_query.account_name,
                    "account_email": data_query.account_email,
                    "bank": data_query.bank,
                    "delivery_cost": data_query.delivery_cost,
                    "simplefactura_token": data_query.simplefactura_token,
                    "shop_address": data_query.shop_address,
                    "payment_card_url": data_query.payment_card_url,
                    "prepaid_discount": data_query.prepaid_discount,
                    "phone": data_query.phone
                }

                return {"setting_data": setting_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}