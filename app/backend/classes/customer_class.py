from datetime import datetime
from app.backend.db.models import CustomerModel

class CustomerClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, identification_number=None, names=None, company_name=None):
        try:
            query = self.db.query(
                CustomerModel.id,
                CustomerModel.country_id,
                CustomerModel.region_id,
                CustomerModel.commune_id,
                CustomerModel.package_id,
                CustomerModel.bill_or_ticket_id,
                CustomerModel.identification_number,
                CustomerModel.names,
                CustomerModel.lastnames,
                CustomerModel.address,
                CustomerModel.company_name,
                CustomerModel.phone,
                CustomerModel.email,
                CustomerModel.added_date,
                CustomerModel.updated_date
            )

            # Aplicar filtros de búsqueda
            if identification_number and identification_number.strip():
                query = query.filter(CustomerModel.identification_number.like(f"%{identification_number.strip()}%"))
            
            if names and names.strip():
                query = query.filter(CustomerModel.names.like(f"%{names.strip()}%"))
            
            if company_name and company_name.strip():
                query = query.filter(CustomerModel.company_name.like(f"%{company_name.strip()}%"))

            query = query.order_by(CustomerModel.id.desc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": customer.id,
                    "country_id": customer.country_id,
                    "region_id": customer.region_id,
                    "commune_id": customer.commune_id,
                    "package_id": customer.package_id,
                    "bill_or_ticket_id": customer.bill_or_ticket_id,
                    "identification_number": customer.identification_number,
                    "names": customer.names,
                    "lastnames": customer.lastnames,
                    "address": customer.address,
                    "company_name": customer.company_name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "added_date": customer.added_date.strftime("%Y-%m-%d %H:%M:%S") if customer.added_date else None,
                    "updated_date": customer.updated_date.strftime("%Y-%m-%d %H:%M:%S") if customer.updated_date else None
                } for customer in data]

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
                    "id": customer.id,
                    "country_id": customer.country_id,
                    "region_id": customer.region_id,
                    "commune_id": customer.commune_id,
                    "package_id": customer.package_id,
                    "bill_or_ticket_id": customer.bill_or_ticket_id,
                    "identification_number": customer.identification_number,
                    "names": customer.names,
                    "lastnames": customer.lastnames,
                    "address": customer.address,
                    "company_name": customer.company_name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "added_date": customer.added_date.strftime("%Y-%m-%d %H:%M:%S") if customer.added_date else None,
                    "updated_date": customer.updated_date.strftime("%Y-%m-%d %H:%M:%S") if customer.updated_date else None
                } for customer in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(CustomerModel).filter(CustomerModel.id == id).first()

            if data_query:
                customer_data = {
                    "id": data_query.id,
                    "country_id": data_query.country_id,
                    "region_id": data_query.region_id,
                    "commune_id": data_query.commune_id,
                    "package_id": data_query.package_id,
                    "bill_or_ticket_id": data_query.bill_or_ticket_id,
                    "identification_number": data_query.identification_number,
                    "names": data_query.names,
                    "lastnames": data_query.lastnames,
                    "address": data_query.address,
                    "company_name": data_query.company_name,
                    "phone": data_query.phone,
                    "email": data_query.email,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"customer_data": customer_data}

            else:
                return {"error": "No se encontraron datos para el customer especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, customer_inputs):
        try:
            new_customer = CustomerModel(
                country_id=customer_inputs.get('country_id'),
                region_id=customer_inputs.get('region_id'),
                commune_id=customer_inputs.get('commune_id'),
                package_id=customer_inputs.get('package_id'),
                bill_or_ticket_id=customer_inputs.get('bill_or_ticket_id'),
                identification_number=customer_inputs['identification_number'],
                names=customer_inputs.get('names'),
                lastnames=customer_inputs.get('lastnames'),
                address=customer_inputs.get('address'),
                company_name=customer_inputs.get('company_name'),
                phone=customer_inputs.get('phone'),
                email=customer_inputs.get('email'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_customer)
            self.db.commit()
            self.db.refresh(new_customer)

            return {
                "status": "success",
                "message": "Customer created successfully",
                "customer_id": new_customer.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(CustomerModel).filter(CustomerModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Customer deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, customer_inputs):
        try:
            existing_customer = self.db.query(CustomerModel).filter(CustomerModel.id == id).one_or_none()

            if not existing_customer:
                return {"status": "error", "message": "No data found"}

            for key, value in customer_inputs.items():
                if value is not None:
                    setattr(existing_customer, key, value)

            existing_customer.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_customer)

            return {"status": "success", "message": "Customer updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
