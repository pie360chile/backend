from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from app.backend.db.models import CustomerModel
from app.backend.db.models.agents_usage import AgentsTokenUsageModel


def _budget_float(value) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return 0.0
    return round(n, 2)


def _parse_budget_input(raw) -> float | None:
    """None o string vacío = sin tope."""
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    return _budget_float(raw)


class CustomerClass:
    def __init__(self, db):
        self.db = db

    def agents_spent_usd(self, customer_id: int) -> float:
        total = (
            self.db.query(func.coalesce(func.sum(AgentsTokenUsageModel.estimated_cost_usd), 0))
            .filter(AgentsTokenUsageModel.customer_id == int(customer_id))
            .scalar()
        )
        try:
            return float(total or 0)
        except (TypeError, ValueError):
            return 0.0

    def get_all(self, page=0, items_per_page=10, identification_number=None, names=None, company_name=None):
        try:
            query = self.db.query(
                CustomerModel.id,
                CustomerModel.country_id,
                CustomerModel.region_id,
                CustomerModel.commune_id,
                CustomerModel.package_id,
                CustomerModel.bill_or_ticket_id,
                CustomerModel.deleted_status_id,
                CustomerModel.identification_number,
                CustomerModel.names,
                CustomerModel.lastnames,
                CustomerModel.address,
                CustomerModel.company_name,
                CustomerModel.phone,
                CustomerModel.email,
                CustomerModel.agents_budget_usd_max,
                CustomerModel.license_time,
                CustomerModel.added_date,
                CustomerModel.updated_date
            )

            query = query.filter(CustomerModel.deleted_status_id == 0)

            if identification_number and identification_number.strip():
                query = query.filter(CustomerModel.identification_number.like(f"%{identification_number.strip()}%"))

            if names and names.strip():
                query = query.filter(CustomerModel.names.like(f"%{names.strip()}%"))

            if company_name and company_name.strip():
                query = query.filter(CustomerModel.company_name.like(f"%{company_name.strip()}%"))

            query = query.order_by(CustomerModel.id.desc())

            def _serialize(customer) -> dict:
                return {
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
                    "agents_budget_usd_max": _budget_float(
                        getattr(customer, "agents_budget_usd_max", None)
                    ),
                    "license_time": customer.license_time.strftime("%Y-%m-%d") if customer.license_time else None,
                    "added_date": customer.added_date.strftime("%Y-%m-%d %H:%M:%S") if customer.added_date else None,
                    "updated_date": customer.updated_date.strftime("%Y-%m-%d %H:%M:%S") if customer.updated_date else None,
                }

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
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": [_serialize(customer) for customer in data]
                }

            data = query.all()
            serialized_data = []
            for customer in data:
                row = _serialize(customer)
                row["deleted_status_id"] = customer.deleted_status_id
                serialized_data.append(row)
            return serialized_data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self.db.query(CustomerModel).filter(
                CustomerModel.id == id,
                CustomerModel.deleted_status_id == 0
            ).first()

            if data_query:
                budget = _budget_float(getattr(data_query, "agents_budget_usd_max", None))
                spent = self.agents_spent_usd(int(data_query.id))
                customer_data = {
                    "id": data_query.id,
                    "country_id": data_query.country_id,
                    "region_id": data_query.region_id,
                    "commune_id": data_query.commune_id,
                    "package_id": data_query.package_id,
                    "bill_or_ticket_id": data_query.bill_or_ticket_id,
                    "deleted_status_id": data_query.deleted_status_id,
                    "identification_number": data_query.identification_number,
                    "names": data_query.names,
                    "lastnames": data_query.lastnames,
                    "address": data_query.address,
                    "company_name": data_query.company_name,
                    "phone": data_query.phone,
                    "email": data_query.email,
                    "agents_budget_usd_max": budget,
                    "agents_spent_usd": spent,
                    "agents_budget_remaining_usd": (
                        round(max(0.0, budget - spent), 2) if budget is not None else None
                    ),
                    "license_time": data_query.license_time.strftime("%Y-%m-%d") if data_query.license_time else None,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }
                return {"customer_data": customer_data}

            return {"error": "No se encontraron datos para el customer especificado."}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, customer_inputs):
        try:
            budget = _parse_budget_input(customer_inputs.get("agents_budget_usd_max"))
            new_customer = CustomerModel(
                country_id=customer_inputs.get('country_id'),
                region_id=customer_inputs.get('region_id'),
                commune_id=customer_inputs.get('commune_id'),
                package_id=customer_inputs.get('package_id'),
                bill_or_ticket_id=customer_inputs.get('bill_or_ticket_id'),
                deleted_status_id=0,
                identification_number=customer_inputs['identification_number'],
                names=customer_inputs.get('names'),
                lastnames=customer_inputs.get('lastnames'),
                address=customer_inputs.get('address'),
                company_name=customer_inputs.get('company_name'),
                phone=customer_inputs.get('phone'),
                email=customer_inputs.get('email'),
                agents_budget_usd_max=(
                    Decimal(str(budget)) if budget is not None else None
                ),
                license_time=customer_inputs.get('license_time'),
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
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Customer deleted successfully"}
            return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id, customer_inputs):
        try:
            existing_customer = self.db.query(CustomerModel).filter(CustomerModel.id == id).one_or_none()

            if not existing_customer:
                return {"status": "error", "message": "No data found"}

            for key, value in customer_inputs.items():
                if key == "agents_budget_usd_max":
                    budget = _parse_budget_input(value)
                    existing_customer.agents_budget_usd_max = (
                        Decimal(str(budget)) if budget is not None else None
                    )
                    continue
                if value is not None:
                    setattr(existing_customer, key, value)

            existing_customer.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(existing_customer)
            return {"status": "success", "message": "Customer updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
