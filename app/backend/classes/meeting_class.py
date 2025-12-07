from app.backend.db.models import MeetingModel
from datetime import datetime
from sqlalchemy import or_, and_
from app.backend.classes.email_class import EmailClass

class MeetingClass:
    def __init__(self, db):
        self.db = db
        self.email_class = EmailClass()

    def get_all(self, page=0, items_per_page=10, schedule_id=None, names=None):
        try:
            query = self.db.query(MeetingModel)

            # Filtrar por schedule_id si se proporciona
            if schedule_id is not None:
                query = query.filter(MeetingModel.schedule_id == schedule_id)

            # Filtrar por nombres si se proporciona
            if names:
                query = query.filter(MeetingModel.names.like(f'%{names}%'))

            # Ordenar por fecha de creación descendente
            query = query.order_by(MeetingModel.added_date.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            offset = page * items_per_page
            meetings = query.offset(offset).limit(items_per_page).all()

            if not meetings:
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
            meetings_list = []
            for meeting in meetings:
                meeting_dict = {
                    "id": meeting.id,
                    "schedule_id": meeting.schedule_id,
                    "names": meeting.names,
                    "lastnames": meeting.lastnames,
                    "email": meeting.email,
                    "celphone": meeting.celphone,
                    "reason": meeting.reason,
                    "added_date": meeting.added_date.strftime('%Y-%m-%d %H:%M:%S') if meeting.added_date else None,
                    "updated_date": meeting.updated_date.strftime('%Y-%m-%d %H:%M:%S') if meeting.updated_date else None
                }
                meetings_list.append(meeting_dict)

            return {
                "status": "success",
                "data": meetings_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, meeting_id):
        try:
            meeting = self.db.query(MeetingModel).filter(
                MeetingModel.id == meeting_id
            ).first()

            if not meeting:
                return {
                    "status": "error",
                    "message": "Meeting not found"
                }

            meeting_dict = {
                "id": meeting.id,
                "schedule_id": meeting.schedule_id,
                "names": meeting.names,
                "lastnames": meeting.lastnames,
                "email": meeting.email,
                "celphone": meeting.celphone,
                "reason": meeting.reason,
                "added_date": meeting.added_date.strftime('%Y-%m-%d %H:%M:%S') if meeting.added_date else None,
                "updated_date": meeting.updated_date.strftime('%Y-%m-%d %H:%M:%S') if meeting.updated_date else None
            }

            return meeting_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, meeting_data):
        try:
            new_meeting = MeetingModel(
                schedule_id=meeting_data.get('schedule_id'),
                names=meeting_data.get('names'),
                lastnames=meeting_data.get('lastnames'),
                email=meeting_data.get('email'),
                celphone=meeting_data.get('celphone'),
                reason=meeting_data.get('reason'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_meeting)
            self.db.commit()
            self.db.refresh(new_meeting)

            # Enviar notificación por correo
            try:
                self.email_class.send_meeting_notification(meeting_data)
            except Exception as email_error:
                print(f"Error enviando correo de notificación: {str(email_error)}")

            return {
                "status": "success",
                "message": "Meeting created successfully",
                "data": {
                    "id": new_meeting.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, meeting_id, meeting_data):
        try:
            meeting = self.db.query(MeetingModel).filter(
                MeetingModel.id == meeting_id
            ).first()

            if not meeting:
                return {
                    "status": "error",
                    "message": "Meeting not found"
                }

            # Actualizar campos
            if meeting_data.get('schedule_id') is not None:
                meeting.schedule_id = meeting_data.get('schedule_id')
            
            if meeting_data.get('names') is not None:
                meeting.names = meeting_data.get('names')
            
            if meeting_data.get('lastnames') is not None:
                meeting.lastnames = meeting_data.get('lastnames')
            
            if meeting_data.get('email') is not None:
                meeting.email = meeting_data.get('email')
            
            if meeting_data.get('celphone') is not None:
                meeting.celphone = meeting_data.get('celphone')
            
            if meeting_data.get('reason') is not None:
                meeting.reason = meeting_data.get('reason')

            meeting.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Meeting updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, meeting_id):
        try:
            meeting = self.db.query(MeetingModel).filter(
                MeetingModel.id == meeting_id
            ).first()

            if not meeting:
                return {
                    "status": "error",
                    "message": "Meeting not found"
                }

            # Hard delete
            self.db.delete(meeting)
            self.db.commit()

            return {
                "status": "success",
                "message": "Meeting deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
