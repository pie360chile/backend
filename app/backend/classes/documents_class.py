import uuid
from pathlib import Path
import fitz  # PyMuPDF
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.backend.db.models import DocumentModel, BirthCertificateDocumentModel


class DocumentsClass:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def parent_authorization(original_file_path: str, student_name: str, output_directory: str = "files/original_student_files"):
        """
        Procesa un documento PDF de autorización de padres, reemplazando [STUDENT_NAMES] con el nombre del estudiante.
        
        Args:
            original_file_path: Ruta del archivo PDF original
            student_name: Nombre del estudiante a insertar en el documento
            output_directory: Directorio donde se guardará el archivo procesado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        try:
            original_file = Path(original_file_path)
            
            if not original_file.exists():
                return {
                    "status": "error",
                    "message": "Documento original no encontrado",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear una copia del documento con un nombre único
            unique_filename = f"autorizacion_{student_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Abrir el archivo PDF y buscar [STUDENT_NAMES]
            pdf_document = fitz.open(original_file)
            
            found_and_modified = False
            
            # Procesar cada página del PDF
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Buscar texto [STUDENT_NAMES] en la página
                text_instances = page.search_for("[STUDENT_NAMES]")
                
                if text_instances:
                    # Reemplazar cada instancia encontrada
                    for rect in text_instances:
                        # Crear un rectángulo blanco para cubrir el texto original
                        page.add_redact_annot(rect, fill=(1, 1, 1))  # Blanco
                        page.apply_redactions()
                        
                        # Insertar el nuevo texto en la misma posición con formato
                        # Crear un rectángulo para el texto con un poco de margen
                        text_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
                        
                        # Usar insert_textbox sin especificar fuente (usará la por defecto)
                        rc = page.insert_textbox(
                            text_rect,
                            student_name,
                            fontsize=10,
                            color=(0, 0, 0),  # Negro
                            align=0,  # Alineación izquierda
                            overlay=True
                        )
                        
                        # Si el texto no cabe, usar insert_text como fallback
                        if rc < 0:
                            page.insert_text(
                                (rect.x0, rect.y1 - 2),  # Posición ligeramente arriba
                                student_name,
                                fontsize=10,
                                color=(0, 0, 0),  # Negro
                                overlay=True
                            )
                    
                    found_and_modified = True
            
            # Guardar el PDF modificado
            pdf_document.save(output_file)
            pdf_document.close()
            
            return {
                "status": "success",
                "message": "Documento procesado exitosamente",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error procesando el documento: {str(e)}",
                "filename": None,
                "file_path": None
            }

    def get(self, id: int) -> Any:
        """
        Obtiene un documento por su ID.
        """
        try:
            document = self.db.query(DocumentModel).filter(
                DocumentModel.id == id
            ).first()

            if document:
                return {
                    "id": document.id,
                    "document_type_id": document.document_type_id,
                    "document": document.document,
                    "added_date": document.added_date.strftime("%Y-%m-%d %H:%M:%S") if document.added_date else None,
                    "updated_date": document.updated_date.strftime("%Y-%m-%d %H:%M:%S") if document.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el documento especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, document_type_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de documentos almacenados.
        """
        try:
            query = self.db.query(DocumentModel)

            if document_type_id is not None:
                query = query.filter(DocumentModel.document_type_id == document_type_id)

            documents = query.order_by(DocumentModel.document.asc()).all()

            return [
                {
                    "document_type_id": doc.document_type_id,
                    "document": doc.document
                }
                for doc in documents
            ]

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, student_id: int, document_type_id: int, file_path: str) -> Any:
        """
        Almacena un documento dependiendo del tipo.
        Si es tipo 1, se guarda en birth_certificate_documents con control de versiones.
        """
        try:
            if document_type_id == 1:
                # Buscar la última versión para este estudiante
                last_version = self.db.query(BirthCertificateDocumentModel).filter(
                    BirthCertificateDocumentModel.student_id == student_id
                ).order_by(BirthCertificateDocumentModel.version_id.desc()).first()
                
                # Determinar el nuevo version_id
                if last_version:
                    new_version_id = last_version.version_id + 1
                else:
                    new_version_id = 1
                
                # Crear el nuevo registro
                new_document = BirthCertificateDocumentModel(
                    student_id=student_id,
                    version_id=new_version_id,
                    birth_certificate=file_path,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                
                self.db.add(new_document)
                self.db.commit()
                self.db.refresh(new_document)
                
                return {
                    "status": "success",
                    "message": "Documento creado exitosamente",
                    "document_id": new_document.id,
                    "version_id": new_version_id
                }
            else:
                # Para otros tipos de documentos, se puede implementar lógica adicional aquí
                return {
                    "status": "error",
                    "message": f"Tipo de documento {document_type_id} no implementado aún"
                }
                
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
