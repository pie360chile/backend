from app.backend.db.models import ContactModel
from datetime import datetime

class ContactClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, names=None, subject_type_id=None, schedule_type_id=None):
        try:
            query = self.db.query(ContactModel)

            # Filtros
            if names:
                query = query.filter(ContactModel.names.like(f'%{names}%'))
            
            if subject_type_id:
                query = query.filter(ContactModel.subject_type_id == subject_type_id)
            
            if schedule_type_id:
                query = query.filter(ContactModel.schedule_type_id == schedule_type_id)

            # Ordenar por fecha de creación descendente
            query = query.order_by(ContactModel.added_date.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            offset = page * items_per_page
            contacts = query.offset(offset).limit(items_per_page).all()

            if not contacts:
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
            contacts_list = []
            for contact in contacts:
                contact_dict = {
                    "id": contact.id,
                    "subject_type_id": contact.subject_type_id,
                    "schedule_type_id": contact.schedule_type_id,
                    "names": contact.names,
                    "lastnames": contact.lastnames,
                    "email": contact.email,
                    "celphone": contact.celphone,
                    "message": contact.message,
                    "added_date": contact.added_date.strftime('%Y-%m-%d %H:%M:%S') if contact.added_date else None,
                    "updated_date": contact.updated_date.strftime('%Y-%m-%d %H:%M:%S') if contact.updated_date else None
                }
                contacts_list.append(contact_dict)

            return {
                "status": "success",
                "data": contacts_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, contact_id):
        try:
            contact = self.db.query(ContactModel).filter(
                ContactModel.id == contact_id
            ).first()

            if not contact:
                return {
                    "status": "error",
                    "message": "Contact not found"
                }

            contact_dict = {
                "id": contact.id,
                "subject_type_id": contact.subject_type_id,
                "schedule_type_id": contact.schedule_type_id,
                "names": contact.names,
                "lastnames": contact.lastnames,
                "email": contact.email,
                "celphone": contact.celphone,
                "message": contact.message,
                "added_date": contact.added_date.strftime('%Y-%m-%d %H:%M:%S') if contact.added_date else None,
                "updated_date": contact.updated_date.strftime('%Y-%m-%d %H:%M:%S') if contact.updated_date else None
            }

            return contact_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, contact_data):
        try:
            new_contact = ContactModel(
                subject_type_id=contact_data.get('subject_type_id'),
                schedule_type_id=contact_data.get('schedule_type_id'),
                names=contact_data.get('names'),
                lastnames=contact_data.get('lastnames'),
                email=contact_data.get('email'),
                celphone=contact_data.get('celphone'),
                message=contact_data.get('message'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_contact)
            self.db.commit()
            self.db.refresh(new_contact)

            return {
                "status": "success",
                "message": "Contact created successfully",
                "data": {
                    "id": new_contact.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, contact_id, contact_data):
        try:
            contact = self.db.query(ContactModel).filter(
                ContactModel.id == contact_id
            ).first()

            if not contact:
                return {
                    "status": "error",
                    "message": "Contact not found"
                }

            # Actualizar campos
            if contact_data.get('subject_type_id') is not None:
                contact.subject_type_id = contact_data.get('subject_type_id')
            
            if contact_data.get('schedule_type_id') is not None:
                contact.schedule_type_id = contact_data.get('schedule_type_id')
            
            if contact_data.get('names') is not None:
                contact.names = contact_data.get('names')
            
            if contact_data.get('lastnames') is not None:
                contact.lastnames = contact_data.get('lastnames')
            
            if contact_data.get('email') is not None:
                contact.email = contact_data.get('email')
            
            if contact_data.get('celphone') is not None:
                contact.celphone = contact_data.get('celphone')
            
            if contact_data.get('message') is not None:
                contact.message = contact_data.get('message')

            contact.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Contact updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, contact_id):
        try:
            contact = self.db.query(ContactModel).filter(
                ContactModel.id == contact_id
            ).first()

            if not contact:
                return {
                    "status": "error",
                    "message": "Contact not found"
                }

            # Hard delete
            self.db.delete(contact)
            self.db.commit()

            return {
                "status": "success",
                "message": "Contact deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
