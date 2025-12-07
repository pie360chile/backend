from datetime import datetime
from app.backend.db.models import MessageModel, CustomerModel

class MessageClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, subject=None, message_type_id=None, customer_id=None, rol_id=None):
        try:
            query = self.db.query(
                MessageModel.id,
                MessageModel.customer_id,
                MessageModel.message_type_id,
                MessageModel.response_id,
                MessageModel.message_response_id,
                MessageModel.subject,
                MessageModel.message,
                MessageModel.added_date,
                MessageModel.updated_date,
                CustomerModel.company_name
            ).join(
                CustomerModel, MessageModel.customer_id == CustomerModel.id
            ).filter(
                MessageModel.deleted_status_id == 0,
                MessageModel.response_id == 0
            )

            # Filtrar por customer_id solo si rol_id es 2
            if rol_id == 2 and customer_id is not None:
                query = query.filter(MessageModel.customer_id == customer_id)

            # Aplicar filtro de búsqueda si se proporciona subject
            if subject and subject.strip():
                query = query.filter(MessageModel.subject.like(f"%{subject.strip()}%"))
            
            # Aplicar filtro por message_type_id si se proporciona
            if message_type_id is not None:
                query = query.filter(MessageModel.message_type_id == message_type_id)

            query = query.order_by(MessageModel.added_date.desc())

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

                serialized_data = []
                for message in data:
                    # Verificar si existe una respuesta para este mensaje
                    has_reply = self.db.query(MessageModel).filter(
                        MessageModel.message_response_id == message.id,
                        MessageModel.response_id == 1,
                        MessageModel.deleted_status_id == 0
                    ).first()
                    
                    serialized_data.append({
                        "id": message.id,
                        "customer_id": message.customer_id,
                        "message_type_id": message.message_type_id,
                        "response_id": message.response_id,
                        "message_response_id": message.message_response_id,
                        "message_answered_id": 1 if has_reply else 0,
                        "subject": message.subject,
                        "message": message.message,
                        "company_name": message.company_name,
                        "added_date": message.added_date.strftime("%Y-%m-%d %H:%M:%S") if message.added_date else None,
                        "updated_date": message.updated_date.strftime("%Y-%m-%d %H:%M:%S") if message.updated_date else None
                    })

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = []
                for message in data:
                    # Verificar si existe una respuesta para este mensaje
                    has_reply = self.db.query(MessageModel).filter(
                        MessageModel.message_response_id == message.id,
                        MessageModel.response_id == 1,
                        MessageModel.deleted_status_id == 0
                    ).first()
                    
                    serialized_data.append({
                        "id": message.id,
                        "customer_id": message.customer_id,
                        "message_type_id": message.message_type_id,
                        "response_id": message.response_id,
                        "message_response_id": message.message_response_id,
                        "message_answered_id": 1 if has_reply else 0,
                        "subject": message.subject,
                        "message": message.message,
                        "company_name": message.company_name,
                        "added_date": message.added_date.strftime("%Y-%m-%d %H:%M:%S") if message.added_date else None,
                        "updated_date": message.updated_date.strftime("%Y-%m-%d %H:%M:%S") if message.updated_date else None
                    })
                
                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self):
        """Retorna todos los messages sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                MessageModel.id,
                MessageModel.customer_id,
                MessageModel.message_type_id,
                MessageModel.response_id,
                MessageModel.message_response_id,
                MessageModel.subject,
                MessageModel.message,
                MessageModel.added_date,
                MessageModel.updated_date
            ).filter(MessageModel.deleted_status_id == 0).order_by(MessageModel.id)

            data = query.all()

            serialized_data = [{
                "id": message.id,
                "customer_id": message.customer_id,
                "message_type_id": message.message_type_id,
                "response_id": message.response_id,
                "message_response_id": message.message_response_id,
                "subject": message.subject,
                "message": message.message,
                "added_date": message.added_date.strftime("%Y-%m-%d %H:%M:%S") if message.added_date else None,
                "updated_date": message.updated_date.strftime("%Y-%m-%d %H:%M:%S") if message.updated_date else None
            } for message in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            # Obtener el mensaje principal con company_name
            data = self.db.query(
                MessageModel.id,
                MessageModel.customer_id,
                MessageModel.message_type_id,
                MessageModel.response_id,
                MessageModel.message_response_id,
                MessageModel.subject,
                MessageModel.message,
                MessageModel.added_date,
                MessageModel.updated_date,
                CustomerModel.company_name
            ).join(
                CustomerModel, MessageModel.customer_id == CustomerModel.id
            ).filter(
                MessageModel.id == id,
                MessageModel.deleted_status_id == 0
            ).first()
            
            if not data:
                return {"status": "error", "message": "No data found"}
            
            result = {
                "id": data.id,
                "customer_id": data.customer_id,
                "message_type_id": data.message_type_id,
                "response_id": data.response_id,
                "message_response_id": data.message_response_id if data.message_response_id else 0,
                "subject": data.subject,
                "message": data.message,
                "company_name": data.company_name,
                "added_date": data.added_date.strftime("%Y-%m-%d %H:%M:%S") if data.added_date else None,
                "updated_date": data.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data.updated_date else None
            }
            
            # Si response_id=0 (mensaje original), buscar si hay una respuesta
            if data.response_id == 0:
                reply_message = self.db.query(
                    MessageModel.id,
                    MessageModel.customer_id,
                    MessageModel.message_type_id,
                    MessageModel.response_id,
                    MessageModel.message_response_id,
                    MessageModel.subject,
                    MessageModel.message,
                    MessageModel.added_date,
                    MessageModel.updated_date,
                    CustomerModel.company_name
                ).join(
                    CustomerModel, MessageModel.customer_id == CustomerModel.id
                ).filter(
                    MessageModel.message_response_id == data.id,
                    MessageModel.response_id == 1,
                    MessageModel.deleted_status_id == 0
                ).first()
                
                if reply_message:
                    result["response_message"] = {
                        "id": reply_message.id,
                        "customer_id": reply_message.customer_id,
                        "message_type_id": reply_message.message_type_id,
                        "response_id": reply_message.response_id,
                        "message_response_id": reply_message.message_response_id if reply_message.message_response_id else 0,
                        "subject": reply_message.subject,
                        "message": reply_message.message,
                        "company_name": reply_message.company_name,
                        "added_date": reply_message.added_date.strftime("%Y-%m-%d %H:%M:%S") if reply_message.added_date else None,
                        "updated_date": reply_message.updated_date.strftime("%Y-%m-%d %H:%M:%S") if reply_message.updated_date else None
                    }
                else:
                    result["response_message"] = None
            # Si response_id=1 (es una respuesta), buscar el mensaje original
            elif data.response_id == 1 and data.message_response_id:
                original_message = self.db.query(
                    MessageModel.id,
                    MessageModel.customer_id,
                    MessageModel.message_type_id,
                    MessageModel.response_id,
                    MessageModel.message_response_id,
                    MessageModel.subject,
                    MessageModel.message,
                    MessageModel.added_date,
                    MessageModel.updated_date,
                    CustomerModel.company_name
                ).join(
                    CustomerModel, MessageModel.customer_id == CustomerModel.id
                ).filter(
                    MessageModel.id == data.message_response_id,
                    MessageModel.deleted_status_id == 0
                ).first()
                
                if original_message:
                    result["response_message"] = {
                        "id": original_message.id,
                        "customer_id": original_message.customer_id,
                        "message_type_id": original_message.message_type_id,
                        "response_id": original_message.response_id,
                        "message_response_id": original_message.message_response_id if original_message.message_response_id else 0,
                        "subject": original_message.subject,
                        "message": original_message.message,
                        "company_name": original_message.company_name,
                        "added_date": original_message.added_date.strftime("%Y-%m-%d %H:%M:%S") if original_message.added_date else None,
                        "updated_date": original_message.updated_date.strftime("%Y-%m-%d %H:%M:%S") if original_message.updated_date else None
                    }
                else:
                    result["response_message"] = None
            else:
                result["response_message"] = None
            
            return result

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def store(self, message_inputs):
        try:
            new_message = MessageModel(
                customer_id=message_inputs.get('customer_id'),
                message_type_id=message_inputs.get('message_type_id'),
                response_id=message_inputs.get('response_id'),
                message_response_id=message_inputs.get('message_response_id'),
                deleted_status_id=0,
                subject=message_inputs.get('subject'),
                message=message_inputs.get('message'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_message)
            self.db.commit()
            self.db.refresh(new_message)

            return {"status": "success", "message": "Message saved successfully", "id": new_message.id}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def delete(self, id):
        try:
            data = self.db.query(MessageModel).filter(MessageModel.id == id).first()
            if data:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Message deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, message_inputs):
        try:
            existing_message = self.db.query(MessageModel).filter(MessageModel.id == id).one_or_none()

            if not existing_message:
                return {"status": "error", "message": "No data found"}

            for key, value in message_inputs.items():
                if value is not None:
                    setattr(existing_message, key, value)

            existing_message.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_message)

            return {"status": "success", "message": "Message updated successfully"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
