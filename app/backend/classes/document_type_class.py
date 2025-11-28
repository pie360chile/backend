from datetime import datetime
from app.backend.db.models import DocumentTypeModel

class DocumentTypeClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, document=None):
        try:
            query = self.db.query(DocumentTypeModel)

            # Aplicar filtro de búsqueda
            if document and document.strip():
                query = query.filter(DocumentTypeModel.document.like(f"%{document.strip()}%"))

            query = query.order_by(DocumentTypeModel.document.asc())

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
                    "id": doc.id,
                    "document_type_id": doc.document_type_id,
                    "document": doc.document,
                    "added_date": doc.added_date.strftime("%Y-%m-%d %H:%M:%S") if doc.added_date else None,
                    "updated_date": doc.updated_date.strftime("%Y-%m-%d %H:%M:%S") if doc.updated_date else None
                } for doc in data]

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
                    "id": doc.id,
                    "document_type_id": doc.document_type_id,
                    "document": doc.document,
                    "added_date": doc.added_date.strftime("%Y-%m-%d %H:%M:%S") if doc.added_date else None,
                    "updated_date": doc.updated_date.strftime("%Y-%m-%d %H:%M:%S") if doc.updated_date else None
                } for doc in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            doc = self.db.query(DocumentTypeModel).filter(
                DocumentTypeModel.id == id
            ).first()

            if doc:
                return {
                    "id": doc.id,
                    "document_type_id": doc.document_type_id,
                    "document": doc.document,
                    "added_date": doc.added_date.strftime("%Y-%m-%d %H:%M:%S") if doc.added_date else None,
                    "updated_date": doc.updated_date.strftime("%Y-%m-%d %H:%M:%S") if doc.updated_date else None
                }
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            error_message = str(e)
            return {"error": error_message}

    def store(self, doc_inputs):
        try:
            new_doc = DocumentTypeModel(
                document_type_id=doc_inputs.get('document_type_id'),
                document=doc_inputs.get('document'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_doc)
            self.db.commit()
            self.db.refresh(new_doc)

            return {
                "status": "success",
                "message": "Document type created successfully",
                "doc_id": new_doc.id
            }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, doc_inputs):
        try:
            existing_doc = self.db.query(DocumentTypeModel).filter(
                DocumentTypeModel.id == id
            ).one_or_none()

            if not existing_doc:
                return {"status": "error", "message": "No data found"}

            if 'document_type_id' in doc_inputs:
                existing_doc.document_type_id = doc_inputs['document_type_id']
            if 'document' in doc_inputs:
                existing_doc.document = doc_inputs['document']

            existing_doc.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_doc)

            return {"status": "success", "message": "Document type updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            doc = self.db.query(DocumentTypeModel).filter(
                DocumentTypeModel.id == id
            ).first()

            if doc:
                self.db.delete(doc)
                self.db.commit()
                return {"status": "success", "message": "Document type deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
