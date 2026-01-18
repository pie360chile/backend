from app.backend.db.models import EventModel
from datetime import datetime

class EventClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = self.db.query(EventModel).order_by(EventModel.start_date.desc())

            # Si page es None, 0 o no se proporciona, devolver todos sin paginación
            if not page or page == 0:
                data = query.all()
                serialized_data = [{
                    "id": event.id,
                    "title": event.title,
                    "color": event.color,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "end_date": event.end_date.isoformat() if event.end_date else None,
                    "description": event.description,
                    "added_date": event.added_date.isoformat() if event.added_date else None,
                    "updated_date": event.updated_date.isoformat() if event.updated_date else None
                } for event in data]

                return serialized_data
            else:
                # Paginación activa
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1

                if page < 1:
                    return {"status": "error", "message": "Invalid page number"}
                
                if total_items > 0 and page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": event.id,
                    "title": event.title,
                    "color": event.color,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "end_date": event.end_date.isoformat() if event.end_date else None,
                    "description": event.description,
                    "added_date": event.added_date.isoformat() if event.added_date else None,
                    "updated_date": event.updated_date.isoformat() if event.updated_date else None
                } for event in data]

                return {
                    "data": serialized_data,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page
                }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all_by_month(self):
        """
        Obtiene todos los eventos agrupados por mes.
        Retorna un diccionario donde las claves son 'YYYY-MM' y los valores son listas de eventos.
        """
        try:
            query = self.db.query(EventModel).order_by(EventModel.start_date.asc())
            data = query.all()
            
            # Agrupar eventos por mes
            events_by_month = {}
            
            for event in data:
                if event.start_date:
                    # Obtener año-mes en formato 'YYYY-MM'
                    month_key = event.start_date.strftime('%Y-%m')
                    
                    if month_key not in events_by_month:
                        events_by_month[month_key] = []
                    
                    events_by_month[month_key].append({
                        "id": event.id,
                        "title": event.title,
                        "color": event.color,
                        "start_date": event.start_date.isoformat() if event.start_date else None,
                        "end_date": event.end_date.isoformat() if event.end_date else None,
                        "description": event.description,
                        "added_date": event.added_date.isoformat() if event.added_date else None,
                        "updated_date": event.updated_date.isoformat() if event.updated_date else None
                    })
            
            return events_by_month

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            data_query = self.db.query(EventModel).filter(EventModel.id == id).first()

            if not data_query:
                return {"status": "error", "message": "Event not found"}

            return {
                "id": data_query.id,
                "title": data_query.title,
                "color": data_query.color,
                "start_date": data_query.start_date.isoformat() if data_query.start_date else None,
                "end_date": data_query.end_date.isoformat() if data_query.end_date else None,
                "description": data_query.description,
                "added_date": data_query.added_date.isoformat() if data_query.added_date else None,
                "updated_date": data_query.updated_date.isoformat() if data_query.updated_date else None
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, event_inputs):
        try:
            new_event = EventModel(
                title=event_inputs.get('title'),
                color=event_inputs.get('color'),
                start_date=event_inputs.get('start_date'),
                end_date=event_inputs.get('end_date'),
                description=event_inputs.get('description'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_event)
            self.db.commit()
            self.db.refresh(new_event)

            return {
                "status": "success",
                "message": "Event created successfully",
                "id": new_event.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, event_inputs):
        try:
            event = self.db.query(EventModel).filter(EventModel.id == id).first()

            if not event:
                return {"status": "error", "message": "Event not found"}

            if 'title' in event_inputs and event_inputs['title'] is not None:
                event.title = event_inputs['title']
            if 'color' in event_inputs and event_inputs['color'] is not None:
                event.color = event_inputs['color']
            if 'start_date' in event_inputs and event_inputs['start_date'] is not None:
                event.start_date = event_inputs['start_date']
            if 'end_date' in event_inputs and event_inputs['end_date'] is not None:
                event.end_date = event_inputs['end_date']
            if 'description' in event_inputs:
                event.description = event_inputs['description']
            
            event.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(event)

            return {
                "status": "success",
                "message": "Event updated successfully",
                "id": event.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def delete(self, id):
        try:
            event = self.db.query(EventModel).filter(EventModel.id == id).first()

            if not event:
                return {"status": "error", "message": "Event not found"}

            self.db.delete(event)
            self.db.commit()

            return {"status": "success", "message": "Event deleted successfully"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
