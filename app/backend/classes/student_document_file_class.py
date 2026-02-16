from typing import Optional, Any, List, Dict
from sqlalchemy.orm import Session
from datetime import datetime
from app.backend.db.models import FolderModel, DocumentModel, BirthCertificateDocumentModel, HealthEvaluationModel


class FolderClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """
        Obtiene un documento por su ID.
        """
        try:
            document_file = self.db.query(FolderModel).filter(
                FolderModel.id == id
            ).first()

            if document_file:
                return {
                    "id": document_file.id,
                    "student_id": document_file.student_id,
                    "document_id": document_file.document_id,
                    "version_id": document_file.version_id,
                    "file": document_file.file,
                    "added_date": document_file.added_date.strftime("%Y-%m-%d %H:%M:%S") if document_file.added_date else None,
                    "updated_date": document_file.updated_date.strftime("%Y-%m-%d %H:%M:%S") if document_file.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el archivo de documento especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_student_and_document(self, student_id: int, document_id: int) -> Any:
        """
        Obtiene todos los archivos de documento para un estudiante y documento específico.
        Solo retorna documentos que tienen archivo (file no null).
        """
        try:
            document_files = self.db.query(FolderModel).filter(
                FolderModel.student_id == student_id,
                FolderModel.document_id == document_id,
                FolderModel.file.isnot(None)  # Solo documentos con archivo
            ).order_by(FolderModel.version_id.desc()).all()

            return [
                {
                    "id": doc_file.id,
                    "student_id": doc_file.student_id,
                    "document_id": doc_file.document_id,
                    "version_id": doc_file.version_id,
                    "detail_id": doc_file.detail_id,
                    "file": doc_file.file,
                    "added_date": doc_file.added_date.strftime("%Y-%m-%d %H:%M:%S") if doc_file.added_date else None,
                    "updated_date": doc_file.updated_date.strftime("%Y-%m-%d %H:%M:%S") if doc_file.updated_date else None
                }
                for doc_file in document_files
            ]

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_all(self, student_id: Optional[int] = None, document_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de archivos de documentos almacenados.
        """
        try:
            query = self.db.query(FolderModel)

            if student_id is not None:
                query = query.filter(FolderModel.student_id == student_id)
            
            if document_id is not None:
                query = query.filter(FolderModel.document_id == document_id)

            document_files = query.order_by(FolderModel.id.desc()).all()

            return [
                {
                    "id": doc_file.id,
                    "student_id": doc_file.student_id,
                    "document_id": doc_file.document_id,
                    "version_id": doc_file.version_id,
                    "file": doc_file.file,
                    "added_date": doc_file.added_date.strftime("%Y-%m-%d %H:%M:%S") if doc_file.added_date else None,
                    "updated_date": doc_file.updated_date.strftime("%Y-%m-%d %H:%M:%S") if doc_file.updated_date else None
                }
                for doc_file in document_files
            ]

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, student_id: int, document_id: int, file_path: str) -> Any:
        """
        Almacena un archivo de documento con control de versiones.
        Para health evaluations (document_id = 4), actualiza el registro existente con file vacío,
        o actualiza la versión más reciente si no hay ninguno con file vacío.
        """
        try:
            # Si es health evaluation (document_id = 4), buscar registro con file vacío para actualizar
            if document_id == 4:
                # Buscar registro con file vacío (null) para este estudiante y documento
                folder_without_file = self.db.query(FolderModel).filter(
                    FolderModel.student_id == student_id,
                    FolderModel.document_id == document_id,
                    FolderModel.file.is_(None)
                ).first()
                
                if folder_without_file:
                    # Actualizar el registro existente con file vacío
                    folder_without_file.file = file_path
                    folder_without_file.updated_date = datetime.now()
                    
                    self.db.commit()
                    self.db.refresh(folder_without_file)
                    
                    return {
                        "status": "success",
                        "message": "Archivo de documento actualizado exitosamente",
                        "id": folder_without_file.id,
                        "version_id": folder_without_file.version_id
                    }
                else:
                    # Si no hay registro con file vacío, actualizar la versión más reciente
                    last_version = self.db.query(FolderModel).filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == document_id
                    ).order_by(FolderModel.version_id.desc()).first()
                    
                    if last_version:
                        # Actualizar el registro más reciente
                        last_version.file = file_path
                        last_version.updated_date = datetime.now()
                        
                        self.db.commit()
                        self.db.refresh(last_version)
                        
                        return {
                            "status": "success",
                            "message": "Archivo de documento actualizado exitosamente",
                            "id": last_version.id,
                            "version_id": last_version.version_id
                        }
                    else:
                        # Si no existe ningún registro, crear uno nuevo (no debería pasar para health evaluations)
                        new_document_file = FolderModel(
                            student_id=student_id,
                            document_id=document_id,
                            version_id=1,
                            file=file_path,
                            added_date=datetime.now(),
                            updated_date=datetime.now()
                        )
                        
                        self.db.add(new_document_file)
                        self.db.commit()
                        self.db.refresh(new_document_file)
                        
                        return {
                            "status": "success",
                            "message": "Archivo de documento creado exitosamente",
                            "id": new_document_file.id,
                            "version_id": 1
                        }
            else:
                # Para otros documentos, crear nueva versión como antes
                # Buscar la última versión para este estudiante y documento
                last_version = self.db.query(FolderModel).filter(
                    FolderModel.student_id == student_id,
                    FolderModel.document_id == document_id
                ).order_by(FolderModel.version_id.desc()).first()
                
                # Determinar el nuevo version_id
                if last_version:
                    new_version_id = last_version.version_id + 1
                else:
                    new_version_id = 1
                
                # Crear el nuevo registro
                new_document_file = FolderModel(
                    student_id=student_id,
                    document_id=document_id,
                    version_id=new_version_id,
                    file=file_path,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                
                self.db.add(new_document_file)
                self.db.commit()
                self.db.refresh(new_document_file)
                
                return {
                    "status": "success",
                    "message": "Archivo de documento creado exitosamente",
                    "id": new_document_file.id,
                    "version_id": new_version_id
                }
                
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, id: int, file_path: Optional[str] = None) -> Any:
        """
        Actualiza un archivo de documento existente.
        """
        try:
            document_file = self.db.query(FolderModel).filter(
                FolderModel.id == id
            ).first()

            if not document_file:
                return {
                    "status": "error",
                    "message": "Archivo de documento no encontrado"
                }

            if file_path is not None:
                document_file.file = file_path
            
            document_file.updated_date = datetime.now()
            
            self.db.commit()
            self.db.refresh(document_file)
            
            return {
                "status": "success",
                "message": "Archivo de documento actualizado exitosamente",
                "id": document_file.id
            }
                
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def check_document_existence(self, student_id: int, document_type_id: int) -> Any:
        """
        Verifica si un estudiante ya tiene documentos de un tipo específico.
        Busca TODOS los document_id que pertenecen al document_type_id solicitado en la tabla documents,
        y luego busca en cada tabla correspondiente:
        - document_id = 1: busca en birth_certificate_documents
        - document_id = 4: busca en health_evaluations
        - Otros: busca en folders
        Retorna todos los documentos encontrados del tipo solicitado y también los que NO tiene.
        """
        try:
            all_documents = []
            missing_documents = []
            
            # Obtener TODOS los document_id de este document_type_id (incluye deleted_date NULL o con valor)
            document_records = self.db.query(
                DocumentModel.id,
                DocumentModel.document,
                DocumentModel.document_type_id
            ).filter(
                DocumentModel.document_type_id == document_type_id
            ).all()
            
            # Convertir a lista de IDs e información
            document_id_list = [doc.id for doc in document_records]
            document_info_dict = {doc.id: doc for doc in document_records}
            
            if not document_id_list:
                return {
                    "status": "success",
                    "exists": False,
                    "message": f"No se encontraron documentos de tipo {document_type_id}",
                    "total": 0,
                    "total_missing": 0,
                    "data": [],
                    "missing": []
                }

            # Para cada document_id, buscar en su tabla correspondiente
            for document_id in document_id_list:
                doc_info = document_info_dict.get(document_id)
                document_name = doc_info.document if doc_info else None
                found = False
                
                # Si es document_id = 1, buscar en birth_certificate_documents
                if document_id == 1:
                    birth_cert = self.db.query(BirthCertificateDocumentModel).filter(
                        BirthCertificateDocumentModel.student_id == student_id
                    ).order_by(BirthCertificateDocumentModel.id.desc()).first()
                    
                    if birth_cert:
                        # Buscar el registro correspondiente en folders para obtener file y version_id
                        folder_record = self.db.query(FolderModel).filter(
                            FolderModel.student_id == student_id,
                            FolderModel.detail_id == birth_cert.id,
                            FolderModel.file.isnot(None)  # Solo si tiene archivo
                        ).order_by(FolderModel.version_id.desc()).first()
                        
                        # Obtener el document_name desde la tabla documents (solo no eliminados)
                        doc_info = self.db.query(DocumentModel).filter(
                            DocumentModel.id == document_id,
                            DocumentModel.deleted_date.is_(None)
                        ).first()
                        document_name = doc_info.document if doc_info else "Certificado de Nacimiento"
                        
                        all_documents.append({
                            "id": birth_cert.id,
                            "student_id": birth_cert.student_id,
                            "document_id": document_id,
                            "document_type_id": document_type_id,
                            "detail_id": birth_cert.id,
                            "file": birth_cert.birth_certificate if birth_cert.birth_certificate else (folder_record.file if folder_record else None),
                            "version_id": folder_record.version_id if folder_record else None,
                            "document_name": document_name,
                            "birth_certificate": birth_cert.birth_certificate,
                            "added_date": birth_cert.added_date.strftime("%Y-%m-%d %H:%M:%S") if birth_cert.added_date else None,
                            "updated_date": birth_cert.updated_date.strftime("%Y-%m-%d %H:%M:%S") if birth_cert.updated_date else None
                        })
                        found = True
                
                # Si es document_id = 4, buscar en health_evaluations
                elif document_id == 4:
                    health_eval = self.db.query(HealthEvaluationModel).filter(
                        HealthEvaluationModel.student_id == student_id
                    ).order_by(HealthEvaluationModel.id.desc()).first()
                    
                    if health_eval:
                        # Buscar el registro correspondiente en folders para obtener file y version_id
                        folder_record = self.db.query(FolderModel).filter(
                            FolderModel.student_id == student_id,
                            FolderModel.detail_id == health_eval.id,
                            FolderModel.file.isnot(None)  # Solo si tiene archivo
                        ).order_by(FolderModel.version_id.desc()).first()
                        
                        # Obtener el document_name desde la tabla documents (solo no eliminados)
                        doc_info = self.db.query(DocumentModel).filter(
                            DocumentModel.id == document_id,
                            DocumentModel.deleted_date.is_(None)
                        ).first()
                        document_name = doc_info.document if doc_info else "Evaluación de Salud"
                        
                        all_documents.append({
                            "id": health_eval.id,
                            "student_id": health_eval.student_id,
                            "document_id": document_id,
                            "document_type_id": document_type_id,
                            "detail_id": health_eval.id,
                            "file": folder_record.file if folder_record else None,
                            "version_id": folder_record.version_id if folder_record else None,
                            "document_name": document_name,
                            "full_name": health_eval.full_name,
                            "identification_number": health_eval.identification_number,
                            "born_date": health_eval.born_date.strftime("%Y-%m-%d") if health_eval.born_date else None,
                            "age": health_eval.age,
                            "evaluation_date": health_eval.evaluation_date.strftime("%Y-%m-%d") if health_eval.evaluation_date else None,
                            "reevaluation_date": health_eval.reevaluation_date.strftime("%Y-%m-%d") if health_eval.reevaluation_date else None,
                            "diagnosis": health_eval.diagnosis,
                            "added_date": health_eval.added_date.strftime("%Y-%m-%d %H:%M:%S") if health_eval.added_date else None,
                            "updated_date": health_eval.updated_date.strftime("%Y-%m-%d %H:%M:%S") if health_eval.updated_date else None
                        })
                        found = True
                
                # Para document_id 7 y otros: existencia = está en folders; si no está, va a missing
                else:
                    folder_records = self.db.query(
                        FolderModel.id,
                        FolderModel.student_id,
                        FolderModel.document_id,
                        FolderModel.version_id,
                        FolderModel.detail_id,
                        FolderModel.file,
                        FolderModel.added_date,
                        FolderModel.updated_date,
                        DocumentModel.document_type_id,
                        DocumentModel.document.label('document_name')
                    ).join(
                        DocumentModel,
                        FolderModel.document_id == DocumentModel.id
                    ).filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == document_id,
                        DocumentModel.deleted_date.is_(None),  # Solo documentos no eliminados
                        FolderModel.file.isnot(None)  # Solo documentos con archivo
                    ).order_by(
                        FolderModel.version_id.desc()
                    ).all()
                    
                    # Obtener solo la última versión de este document_id
                    if folder_records:
                        folder_record = folder_records[0]  # Ya está ordenado por version_id desc
                        all_documents.append({
                            "id": folder_record.id,
                            "student_id": folder_record.student_id,
                            "document_id": folder_record.document_id,
                            "document_type_id": folder_record.document_type_id,
                            "version_id": folder_record.version_id,
                            "detail_id": folder_record.detail_id,
                            "file": folder_record.file,
                            "document_name": folder_record.document_name,
                            "added_date": folder_record.added_date.strftime("%Y-%m-%d %H:%M:%S") if folder_record.added_date else None,
                            "updated_date": folder_record.updated_date.strftime("%Y-%m-%d %H:%M:%S") if folder_record.updated_date else None
                        })
                        found = True
                
                # Si no se encontró el documento, agregarlo a la lista de faltantes
                if not found:
                    missing_documents.append({
                        "document_id": document_id,
                        "document_type_id": document_type_id,
                        "document_name": document_name or f"Documento {document_id}",
                        "student_id": student_id
                    })
            
            # Ordenar por document_id para mantener consistencia
            all_documents.sort(key=lambda x: x.get("document_id", 0))
            missing_documents.sort(key=lambda x: x.get("document_id", 0))
            
            # Construir respuesta
            response = {
                "status": "success",
                "exists": len(all_documents) > 0,
                "message": f"El estudiante tiene {len(all_documents)} documento(s) de tipo {document_type_id} y faltan {len(missing_documents)}",
                "total": len(all_documents),
                "total_missing": len(missing_documents),
                "data": all_documents,
                "missing": missing_documents
            }
            
            return response
                
        except Exception as e:
            return {
                "status": "error",
                "exists": False,
                "message": str(e),
                "total": 0,
                "data": None
            }
