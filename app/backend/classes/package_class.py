from datetime import datetime
from app.backend.db.models import PackageModel

class PackageClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, package_name=None):
        try:
            query = self.db.query(
                PackageModel.id,
                PackageModel.deleted_status_id,
                PackageModel.package_name,
                PackageModel.students_per_package,
                PackageModel.professionals_per_package,
                PackageModel.added_date,
                PackageModel.updated_date
            ).filter(PackageModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona package_name
            if package_name and package_name.strip():
                query = query.filter(PackageModel.package_name.like(f"%{package_name.strip()}%"))

            query = query.order_by(PackageModel.id.desc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0

                if total_items == 0:
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": package.id,
                    "deleted_status_id": package.deleted_status_id,
                    "package_name": package.package_name,
                    "students_per_package": package.students_per_package,
                    "professionals_per_package": package.professionals_per_package,
                    "added_date": package.added_date.strftime("%Y-%m-%d %H:%M:%S") if package.added_date else None,
                    "updated_date": package.updated_date.strftime("%Y-%m-%d %H:%M:%S") if package.updated_date else None
                } for package in data]

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
                    "id": package.id,
                    "deleted_status_id": package.deleted_status_id,
                    "package_name": package.package_name,
                    "students_per_package": package.students_per_package,
                    "professionals_per_package": package.professionals_per_package,
                    "added_date": package.added_date.strftime("%Y-%m-%d %H:%M:%S") if package.added_date else None,
                    "updated_date": package.updated_date.strftime("%Y-%m-%d %H:%M:%S") if package.updated_date else None
                } for package in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(PackageModel).filter(PackageModel.id == id, PackageModel.deleted_status_id == 0).first()

            if data_query:
                package_data = {
                    "id": data_query.id,
                    "deleted_status_id": data_query.deleted_status_id,
                    "package_name": data_query.package_name,
                    "students_per_package": data_query.students_per_package,
                    "professionals_per_package": data_query.professionals_per_package,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"package_data": package_data}

            else:
                return {"error": "No se encontraron datos para el paquete especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, package_inputs):
        try:
            new_package = PackageModel(
                deleted_status_id=0,
                package_name=package_inputs.get('package_name'),
                students_per_package=package_inputs.get('students_per_package'),
                professionals_per_package=package_inputs.get('professionals_per_package'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_package)
            self.db.commit()
            self.db.refresh(new_package)

            return {
                "status": "success",
                "message": "Package created successfully",
                "package_id": new_package.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            data = self.db.query(PackageModel).filter(PackageModel.id == id).first()
            if data and data.deleted_status_id == 0:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Package deleted successfully"}
            elif data:
                return {"status": "error", "message": "No data found"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, package_inputs):
        try:
            existing_package = self.db.query(PackageModel).filter(PackageModel.id == id).one_or_none()

            if not existing_package:
                return {"status": "error", "message": "No data found"}

            for key, value in package_inputs.items():
                if value is not None:
                    setattr(existing_package, key, value)

            existing_package.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_package)

            return {"status": "success", "message": "Package updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
