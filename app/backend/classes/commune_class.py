from datetime import datetime
from app.backend.db.models import CommuneModel, RegionModel

class CommuneClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, commune_name=None, region_id=None):
        try:
            query = self.db.query(
                CommuneModel.id,
                CommuneModel.region_id,
                CommuneModel.commune,
                CommuneModel.added_date,
                CommuneModel.updated_date,
                RegionModel.region
            ).join(
                RegionModel, CommuneModel.region_id == RegionModel.id
            )

            # Aplicar filtro de búsqueda si se proporciona commune_name
            if commune_name and commune_name.strip():
                query = query.filter(CommuneModel.commune.like(f"%{commune_name.strip()}%"))
            
            # Aplicar filtro por region_id si se proporciona
            if region_id is not None:
                query = query.filter(CommuneModel.region_id == region_id)

            query = query.order_by(CommuneModel.id)
            data = query.all()

            serialized_data = [{
                "id": commune.id,
                "region_id": commune.region_id,
                "commune": commune.commune,
                "region": commune.region,
                "added_date": commune.added_date.strftime("%Y-%m-%d %H:%M:%S") if commune.added_date else None,
                "updated_date": commune.updated_date.strftime("%Y-%m-%d %H:%M:%S") if commune.updated_date else None
            } for commune in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                CommuneModel.id,
                CommuneModel.region_id,
                CommuneModel.commune,
                CommuneModel.added_date,
                CommuneModel.updated_date,
                RegionModel.region
            ).join(
                RegionModel, CommuneModel.region_id == RegionModel.id
            ).filter(CommuneModel.id == id).first()

            if data_query:
                commune_data = {
                    "id": data_query.id,
                    "region_id": data_query.region_id,
                    "commune": data_query.commune,
                    "region": data_query.region,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"commune_data": commune_data}

            else:
                return {"error": "No se encontraron datos para la commune especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, commune_inputs):
        try:
            new_commune = CommuneModel(
                region_id=commune_inputs['region_id'],
                commune=commune_inputs['commune'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_commune)
            self.db.commit()
            self.db.refresh(new_commune)

            return {
                "status": "success",
                "message": "Commune created successfully",
                "commune_id": new_commune.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(CommuneModel).filter(CommuneModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Commune deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, commune_inputs):
        try:
            existing_commune = self.db.query(CommuneModel).filter(CommuneModel.id == id).one_or_none()

            if not existing_commune:
                return {"status": "error", "message": "No data found"}

            for key, value in commune_inputs.items():
                setattr(existing_commune, key, value)

            existing_commune.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_commune)

            return {"status": "success", "message": "Commune updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
