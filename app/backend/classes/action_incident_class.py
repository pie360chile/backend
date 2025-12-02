from datetime import datetime
from app.backend.db.models import ActionIncidentModel

class ActionIncidentClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, student_id=None, title=None, school_id=None):
        try:
            query = self.db.query(ActionIncidentModel).filter(
                ActionIncidentModel.school_id == school_id,
                ActionIncidentModel.deleted_status_id == 0
            ) if school_id else self.db.query(ActionIncidentModel).filter(ActionIncidentModel.deleted_status_id == 0)

            # Filtrar por student_id si se proporciona
            if student_id is not None:
                query = query.filter(ActionIncidentModel.student_id == student_id)

            # Filtrar por title si se proporciona
            if title and title.strip():
                query = query.filter(ActionIncidentModel.title.like(f"%{title.strip()}%"))

            query = query.order_by(ActionIncidentModel.id.desc())

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
                    "id": action.id,
                    "school_id": action.school_id,
                    "student_id": action.student_id,
                    "professional_id": action.professional_id,
                    "action_incident_type_id": action.action_incident_type_id,
                    "status_id": action.status_id,
                    "title": action.title,
                    "incident_date": action.incident_date.strftime("%Y-%m-%d") if action.incident_date else None,
                    "incident_time": str(action.incident_time) if action.incident_time else None,
                    "background": action.background,
                    "conduct": action.conduct,
                    "consequences": action.consequences,
                    "recommendations": action.recommendations,
                    "added_date": action.added_date.strftime("%Y-%m-%d %H:%M:%S") if action.added_date else None,
                    "updated_date": action.updated_date.strftime("%Y-%m-%d %H:%M:%S") if action.updated_date else None
                } for action in data]

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
                    "id": action.id,
                    "school_id": action.school_id,
                    "student_id": action.student_id,
                    "professional_id": action.professional_id,
                    "action_incident_type_id": action.action_incident_type_id,
                    "status_id": action.status_id,
                    "title": action.title,
                    "incident_date": action.incident_date.strftime("%Y-%m-%d") if action.incident_date else None,
                    "incident_time": str(action.incident_time) if action.incident_time else None,
                    "background": action.background,
                    "conduct": action.conduct,
                    "consequences": action.consequences,
                    "recommendations": action.recommendations,
                    "added_date": action.added_date.strftime("%Y-%m-%d %H:%M:%S") if action.added_date else None,
                    "updated_date": action.updated_date.strftime("%Y-%m-%d %H:%M:%S") if action.updated_date else None
                } for action in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            data = self.db.query(ActionIncidentModel).filter(
                ActionIncidentModel.id == id,
                ActionIncidentModel.deleted_status_id == 0
            ).first()
            
            if not data:
                return {"status": "error", "message": "No data found"}
            
            result = {
                "id": data.id,
                "school_id": data.school_id,
                "student_id": data.student_id,
                "professional_id": data.professional_id,
                "action_incident_type_id": data.action_incident_type_id,
                "status_id": data.status_id,
                "title": data.title,
                "incident_date": data.incident_date.strftime("%Y-%m-%d") if data.incident_date else None,
                "incident_time": str(data.incident_time) if data.incident_time else None,
                "background": data.background,
                "conduct": data.conduct,
                "consequences": data.consequences,
                "recommendations": data.recommendations,
                "added_date": data.added_date.strftime("%Y-%m-%d %H:%M:%S") if data.added_date else None,
                "updated_date": data.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data.updated_date else None
            }
            
            return result

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, action_inputs, school_id=None):
        try:
            new_action = ActionIncidentModel(
                school_id=school_id,
                student_id=action_inputs.get('student_id'),
                professional_id=action_inputs.get('professional_id'),
                action_incident_type_id=action_inputs.get('action_incident_type_id'),
                status_id=action_inputs.get('status_id'),
                deleted_status_id=0,
                title=action_inputs.get('title'),
                incident_date=datetime.strptime(action_inputs.get('incident_date'), "%Y-%m-%d") if action_inputs.get('incident_date') else None,
                incident_time=action_inputs.get('incident_time'),
                background=action_inputs.get('background'),
                conduct=action_inputs.get('conduct'),
                consequences=action_inputs.get('consequences'),
                recommendations=action_inputs.get('recommendations'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_action)
            self.db.commit()
            self.db.refresh(new_action)

            return {"status": "success", "message": "Action incident saved successfully", "id": new_action.id}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def delete(self, id):
        try:
            data = self.db.query(ActionIncidentModel).filter(ActionIncidentModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Action incident deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, action_inputs):
        try:
            existing_action = self.db.query(ActionIncidentModel).filter(ActionIncidentModel.id == id).one_or_none()

            if not existing_action:
                return {"status": "error", "message": "No data found"}

            for key, value in action_inputs.items():
                if value is not None:
                    if key == 'incident_date' and isinstance(value, str):
                        value = datetime.strptime(value, "%Y-%m-%d")
                    setattr(existing_action, key, value)

            existing_action.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_action)

            return {"status": "success", "message": "Action incident updated successfully"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
