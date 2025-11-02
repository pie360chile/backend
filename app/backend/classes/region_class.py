from datetime import datetime
from app.backend.db.models import RegionModel

class RegionClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, region_name=None):
        try:
            query = self.db.query(
                RegionModel.id,
                RegionModel.region,
                RegionModel.region_remuneration_code,
                RegionModel.added_date,
                RegionModel.updated_date
            )

            # Aplicar filtro de búsqueda si se proporciona region_name
            if region_name and region_name.strip():
                query = query.filter(RegionModel.region.like(f"%{region_name.strip()}%"))

            query = query.order_by(RegionModel.id)
            data = query.all()

            serialized_data = [{
                "id": region.id,
                "region": region.region,
                "region_remuneration_code": region.region_remuneration_code,
                "added_date": region.added_date.strftime("%Y-%m-%d %H:%M:%S") if region.added_date else None,
                "updated_date": region.updated_date.strftime("%Y-%m-%d %H:%M:%S") if region.updated_date else None
            } for region in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                RegionModel.id,
                RegionModel.region,
                RegionModel.region_remuneration_code,
                RegionModel.added_date,
                RegionModel.updated_date
            ).filter(RegionModel.id == id).first()

            if data_query:
                region_data = {
                    "id": data_query.id,
                    "region": data_query.region,
                    "region_remuneration_code": data_query.region_remuneration_code,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"region_data": region_data}

            else:
                return {"error": "No se encontraron datos para la region especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, region_inputs):
        try:
            new_region = RegionModel(
                region=region_inputs['region'],
                region_remuneration_code=region_inputs['region_remuneration_code'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_region)
            self.db.commit()
            self.db.refresh(new_region)

            return {
                "status": "success",
                "message": "Region created successfully",
                "region_id": new_region.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(RegionModel).filter(RegionModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Region deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, region_inputs):
        try:
            existing_region = self.db.query(RegionModel).filter(RegionModel.id == id).one_or_none()

            if not existing_region:
                return {"status": "error", "message": "No data found"}

            for key, value in region_inputs.items():
                setattr(existing_region, key, value)

            existing_region.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_region)

            return {"status": "success", "message": "Region updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
