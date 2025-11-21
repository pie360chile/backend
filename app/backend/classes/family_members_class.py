from datetime import datetime
from app.backend.db.models import FamilyMemberModel

class FamilyMembersClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, family_member=None):
        try:
            query = self.db.query(
                FamilyMemberModel.id,
                FamilyMemberModel.family_member,
                FamilyMemberModel.added_date,
                FamilyMemberModel.updated_date
            ).filter(FamilyMemberModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona family_member
            if family_member and family_member.strip():
                query = query.filter(FamilyMemberModel.family_member.like(f"%{family_member.strip()}%"))

            query = query.order_by(FamilyMemberModel.id)

            if page > 0:
                if page < 1:
                    page = 1

                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0

                if total_items == 0 or total_pages == 0 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": member.id,
                    "family_member": member.family_member,
                    "added_date": member.added_date.strftime("%Y-%m-%d %H:%M:%S") if member.added_date else None,
                    "updated_date": member.updated_date.strftime("%Y-%m-%d %H:%M:%S") if member.updated_date else None
                } for member in data]

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
                    "id": member.id,
                    "family_member": member.family_member,
                    "added_date": member.added_date.strftime("%Y-%m-%d %H:%M:%S") if member.added_date else None,
                    "updated_date": member.updated_date.strftime("%Y-%m-%d %H:%M:%S") if member.updated_date else None
                } for member in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todos los family members sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                FamilyMemberModel.id,
                FamilyMemberModel.family_member,
                FamilyMemberModel.added_date,
                FamilyMemberModel.updated_date
            ).filter(FamilyMemberModel.deleted_status_id == 0).order_by(FamilyMemberModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": member.id,
                "family_member": member.family_member,
                "added_date": member.added_date.strftime("%Y-%m-%d %H:%M:%S") if member.added_date else None,
                "updated_date": member.updated_date.strftime("%Y-%m-%d %H:%M:%S") if member.updated_date else None
            } for member in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(FamilyMemberModel).filter(FamilyMemberModel.id == id).first()

            if data_query:
                member_data = {
                    "id": data_query.id,
                    "family_member": data_query.family_member,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"member_data": member_data}

            else:
                return {"error": "No se encontraron datos para el family member especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, member_inputs):
        try:
            new_member = FamilyMemberModel(
                family_member=member_inputs['family_member'],
                deleted_status_id=0,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_member)
            self.db.commit()
            self.db.refresh(new_member)

            return {
                "status": "success",
                "message": "Family member created successfully",
                "member_id": new_member.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(FamilyMemberModel).filter(FamilyMemberModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Family member deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, member_inputs):
        try:
            existing_member = self.db.query(FamilyMemberModel).filter(FamilyMemberModel.id == id).one_or_none()

            if not existing_member:
                return {"status": "error", "message": "No data found"}

            for key, value in member_inputs.items():
                setattr(existing_member, key, value)

            existing_member.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_member)

            return {"status": "success", "message": "Family member updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

