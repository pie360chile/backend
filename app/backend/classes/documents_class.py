import uuid
import re
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.backend.db.models import DocumentModel, BirthCertificateDocumentModel, HealthEvaluationModel, FolderModel


class DocumentsClass:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def parent_authorization(
        original_file_path: str, 
        student_fullname: str,
        parent_relation: str = "",
        student_course_school: str = "",
        parent_fullname: str = "",
        parent_rut: str = "",
        city: str = "",
        day: str = "",
        month: str = "",
        year: str = "",  # Año (últimos 2 dígitos)
        parent_signature: str = "",
        yes_marker: str = "●",  # Punto negro para [Y]
        no_marker: str = "",  # En blanco para [N]
        output_directory: str = "files/system/students"
    ):
        """
        Procesa un documento PDF de autorización de padres, reemplazando los tags con los valores correspondientes.
        
        Args:
            original_file_path: Ruta del archivo PDF original
            student_fullname: Nombre completo del estudiante
            parent_relation: Relación con el estudiante (ej: "Padre", "Madre", "Tutor")
            student_course_school: Curso y establecimiento (ej: "3ro A - Escuela San Juan")
            parent_fullname: Nombre completo del padre/madre/tutor
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
            unique_filename = f"autorizacion_{student_fullname.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Abrir el archivo PDF
            pdf_document = fitz.open(original_file)
            
            # Mapeo de tags a valores (si está vacío, usar string vacío en lugar de saltar)
            tag_replacements = {
                "[STUDENT_FULLNAME]": student_fullname or "",
                "[PARENT_RELATION]": parent_relation or "",
                "[STUDENT_COURSE_SCHOOL_LOCATION]": student_course_school or "",
                "[PARENT_FULLNAME]": parent_fullname or "",
                "[PARENT_RUT]": parent_rut or "",
                "[PARENT_SIGNATURE]": "",  # Firma del padre/madre (se deja en blanco)
                "[CITY]": city or "",
                "[DAY]": day or "",
                "[MONTH]": month or "",
                "[YEAR]": year or "",  # Año (últimos 2 dígitos)
                "[Y]": yes_marker or "●",  # Punto negro para [Y]
                "[N]": no_marker or ""  # En blanco para [N]
            }
            
            found_and_modified = False
            
            # Procesar cada página del PDF
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Obtener todo el texto de la página en formato dict para búsqueda más precisa
                page_dict = None
                try:
                    page_dict = page.get_text("dict")
                except:
                    pass
                
                # Reemplazar cada tag
                for tag, value in tag_replacements.items():
                    # Siempre reemplazar, incluso si el valor está vacío (dejará el campo vacío)
                    text_instances = []
                    
                    # Intentar diferentes variaciones del tag
                    # Para [Y] y [N] solo buscar con corchetes para evitar reemplazos incorrectos
                    if tag == "[Y]" or tag == "[N]":
                        tag_variations = [
                            tag,  # Tag original con corchetes
                            tag.upper(),  # Mayúsculas
                            tag.lower(),  # Minúsculas
                        ]
                    else:
                        tag_variations = [
                            tag,  # Tag original con corchetes
                            tag.replace("[", "").replace("]", ""),  # Sin corchetes
                            tag.upper(),  # Mayúsculas
                            tag.lower(),  # Minúsculas
                            tag.replace("[", "").replace("]", "").upper(),  # Sin corchetes, mayúsculas
                            tag.replace("[", "").replace("]", "").lower(),  # Sin corchetes, minúsculas
                        ]
                    
                    # Buscar cada variación usando search_for
                    for tag_variant in tag_variations:
                        try:
                            # Buscar con flags de case insensitive y dehyphenate
                            found = page.search_for(tag_variant, flags=fitz.TEXT_DEHYPHENATE | fitz.TEXT_IGNORECASE)
                            if found:
                                text_instances.extend(found)
                                break  # Si se encuentra, no buscar más variaciones con search_for
                        except:
                            try:
                                # Si falla con flags, intentar sin flags
                                found = page.search_for(tag_variant)
                                if found:
                                    text_instances.extend(found)
                                    break
                            except:
                                pass
                    
                    # Si aún no se encuentra, buscar usando get_text("dict") para posición exacta
                    # Este método es más preciso cuando el tag está dividido en múltiples partes
                    if not text_instances and page_dict:
                        try:
                            # Buscar en bloques de texto
                            for block in page_dict.get("blocks", []):
                                if "lines" in block:
                                    for line in block["lines"]:
                                        full_line_text = ""
                                        line_spans = []
                                        for span in line.get("spans", []):
                                            span_text = span.get("text", "")
                                            full_line_text += span_text
                                            line_spans.append((span, span_text))
                                        
                                        # Buscar tag en el texto completo de la línea (case insensitive)
                                        full_line_text_upper = full_line_text.upper()
                                        for tag_variant in tag_variations:
                                            tag_variant_upper = tag_variant.upper()
                                            # Buscar con case insensitive
                                            if tag_variant_upper in full_line_text_upper:
                                                # Encontrar qué span(s) contiene(n) el tag
                                                # Si el tag está en múltiples spans, calcular el rectángulo combinado
                                                matching_spans = []
                                                for span, span_text in line_spans:
                                                    span_text_upper = span_text.upper()
                                                    if tag_variant_upper in span_text_upper:
                                                        matching_spans.append(span)
                                                
                                                if matching_spans:
                                                    # Calcular el rectángulo que cubre todos los spans que contienen el tag
                                                    x0 = min(s.get("bbox", [0, 0, 0, 0])[0] for s in matching_spans)
                                                    y0 = min(s.get("bbox", [0, 0, 0, 0])[1] for s in matching_spans)
                                                    x1 = max(s.get("bbox", [0, 0, 0, 0])[2] for s in matching_spans)
                                                    y1 = max(s.get("bbox", [0, 0, 0, 0])[3] for s in matching_spans)
                                                    rect = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
                                                    text_instances.append(rect)
                                                break
                                        
                                        # Solo buscar sin espacios si el tag es lo suficientemente largo para evitar falsos positivos
                                        # No buscar sin espacios para tags cortos como [Y] o [N]
                                        if len(tag.replace("[", "").replace("]", "")) > 3:
                                            full_line_clean = full_line_text.replace(" ", "").replace("_", "").replace("-", "").upper()
                                            for tag_variant in tag_variations:
                                                tag_clean = tag_variant.replace("[", "").replace("]", "").replace(" ", "").replace("_", "").replace("-", "").upper()
                                                if len(tag_clean) > 3 and tag_clean in full_line_clean:
                                                    # Encontrar spans que contengan partes del tag
                                                    matching_spans = []
                                                    for span, span_text in line_spans:
                                                        span_clean = span_text.replace(" ", "").replace("_", "").replace("-", "").upper()
                                                        if tag_clean in span_clean:
                                                            matching_spans.append(span)
                                                    
                                                    if matching_spans:
                                                        x0 = min(s.get("bbox", [0, 0, 0, 0])[0] for s in matching_spans)
                                                        y0 = min(s.get("bbox", [0, 0, 0, 0])[1] for s in matching_spans)
                                                        x1 = max(s.get("bbox", [0, 0, 0, 0])[2] for s in matching_spans)
                                                        y1 = max(s.get("bbox", [0, 0, 0, 0])[3] for s in matching_spans)
                                                        rect = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
                                                        text_instances.append(rect)
                                                    break
                        except Exception as e:
                            pass
                    
                    # Reemplazar todas las instancias encontradas
                    if text_instances:
                        # Eliminar duplicados manteniendo el orden
                        seen_rects = set()
                        unique_instances = []
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        for rect in text_instances:
                            # Validar que el rectángulo esté dentro de los límites de la página
                            if (rect.x0 >= 0 and rect.y0 >= 0 and 
                                rect.x1 <= page_width and rect.y1 <= page_height and
                                rect.x1 > rect.x0 and rect.y1 > rect.y0):
                                
                                # Validar que el rectángulo no sea demasiado grande (más del 50% de la página)
                                rect_width = rect.x1 - rect.x0
                                rect_height = rect.y1 - rect.y0
                                if rect_width < page_width * 0.5 and rect_height < page_height * 0.5:
                                    rect_key = (round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2))
                                    if rect_key not in seen_rects:
                                        seen_rects.add(rect_key)
                                        unique_instances.append(rect)
                        
                        # Aplicar redacciones primero (cubrir tags originales) solo si hay instancias válidas
                        if unique_instances:
                            for rect in unique_instances:
                                try:
                                    page.add_redact_annot(rect, fill=(1, 1, 1))  # Blanco
                                except:
                                    pass
                            
                            # Aplicar todas las redacciones de una vez
                            try:
                                page.apply_redactions()
                            except:
                                pass
                        
                        # Luego insertar los nuevos valores
                        for rect in unique_instances:
                            try:
                                # Insertar el nuevo texto en la misma posición
                                text_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
                                
                                # Si el valor es el punto negro [Y], usar tamaño de fuente más grande
                                fontsize = 18 if value == "●" else 10
                                
                                # Intentar insertar con textbox
                                rc = page.insert_textbox(
                                    text_rect,
                                    value,
                                    fontsize=fontsize,
                                    color=(0, 0, 0),
                                    align=0,
                                    overlay=True
                                )
                                
                                # Si no cabe o falla, usar insert_text con el tamaño apropiado
                                if rc < 0:
                                    page.insert_text(
                                        (rect.x0, rect.y1 - 2),
                                        value,
                                        fontsize=fontsize,
                                        color=(0, 0, 0),
                                        overlay=True
                                    )
                            except Exception as e:
                                # Si falla, intentar solo con insert_text en la posición
                                try:
                                    fontsize = 18 if value == "●" else 10
                                    page.insert_text(
                                        (rect.x0, rect.y1 - 2),
                                        value,
                                        fontsize=fontsize,
                                        color=(0, 0, 0),
                                        overlay=True
                                    )
                                except:
                                    pass
                        
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
                    "career_type_id": document.career_type_id,
                    "document": document.document,
                    "added_date": document.added_date.strftime("%Y-%m-%d %H:%M:%S") if document.added_date else None,
                    "updated_date": document.updated_date.strftime("%Y-%m-%d %H:%M:%S") if document.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el documento especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, document_type_id: Optional[int] = None, career_type_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de documentos almacenados.
        """
        try:
            query = self.db.query(DocumentModel)

            if document_type_id is not None:
                query = query.filter(DocumentModel.document_type_id == document_type_id)
            
            # Filtrar por career_type_id solo si se proporciona y no está vacío
            if career_type_id is not None and career_type_id != 0:
                query = query.filter(DocumentModel.career_type_id == career_type_id)

            documents = query.order_by(DocumentModel.document.asc()).all()

            return [
                {
                    "document_type_id": doc.document_type_id,
                    "career_type_id": doc.career_type_id,
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
        - Si document_type_id == 1 (birth certificate), guarda en birth_certificate_documents y folders
        - Para otros tipos, solo guarda en folders
        """
        try:
            # Buscar el document_id correspondiente al document_type_id
            document = self.db.query(DocumentModel).filter(
                DocumentModel.document_type_id == document_type_id
            ).first()
            
            if not document:
                return {
                    "status": "error",
                    "message": f"No se encontró documento con document_type_id {document_type_id}"
                }
            
            detail_id = None
            
            # Si es document_type_id == 1 (birth certificate), guardar primero en birth_certificate_documents
            if document_type_id == 1:
                # Crear registro en birth_certificate_documents
                new_birth_cert = BirthCertificateDocumentModel(
                    student_id=student_id,
                    birth_certificate=file_path,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_birth_cert)
                self.db.flush()  # Para obtener el ID sin hacer commit completo aún
                detail_id = new_birth_cert.id
            
            # Si es health evaluation (document_id = 4), actualizar registro existente en lugar de crear nuevo
            if document.id == 4:
                # Buscar registro con file vacío (null) para este estudiante y documento
                folder_without_file = self.db.query(FolderModel).filter(
                    FolderModel.student_id == student_id,
                    FolderModel.document_id == document.id,
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
                        "message": "Documento actualizado exitosamente",
                        "document_id": folder_without_file.id,
                        "version_id": folder_without_file.version_id
                    }
                else:
                    # Si no hay registro con file vacío, actualizar la versión más reciente
                    last_version = self.db.query(FolderModel).filter(
                        FolderModel.student_id == student_id,
                        FolderModel.document_id == document.id
                    ).order_by(FolderModel.version_id.desc()).first()
                    
                    if last_version:
                        # Actualizar el registro más reciente
                        last_version.file = file_path
                        last_version.updated_date = datetime.now()
                        
                        self.db.commit()
                        self.db.refresh(last_version)
                        
                        return {
                            "status": "success",
                            "message": "Documento actualizado exitosamente",
                            "document_id": last_version.id,
                            "version_id": last_version.version_id
                        }
            
            # Para otros documentos, crear nueva versión
            # Buscar la última versión para este estudiante y documento
            last_version = self.db.query(FolderModel).filter(
                FolderModel.student_id == student_id,
                FolderModel.document_id == document.id
            ).order_by(FolderModel.version_id.desc()).first()
            
            # Determinar el nuevo version_id
            if last_version:
                new_version_id = last_version.version_id + 1
            else:
                new_version_id = 1
            
            # Crear el nuevo registro en folders
            new_folder = FolderModel(
                student_id=student_id,
                document_id=document.id,
                version_id=new_version_id,
                detail_id=detail_id,  # ID de birth_certificate_documents si es tipo 1
                file=file_path,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            
            self.db.add(new_folder)
            self.db.commit()
            self.db.refresh(new_folder)
            
            return {
                "status": "success",
                "message": "Documento creado exitosamente",
                "document_id": new_folder.id,
                "version_id": new_version_id
            }
                
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    @staticmethod
    @staticmethod
    def generate_health_evaluation_pdf(
        template_path: str,
        evaluation_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de evaluación de salud a partir de un template PDF.
        Reemplaza las etiquetas entre corchetes [] con los datos de la evaluación.
        
        Args:
            template_path: Ruta del archivo PDF template
            evaluation_data: Diccionario con los datos de la evaluación de salud
            db: Sesión de base de datos (opcional, para obtener datos relacionados)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        try:
            template_file = Path(template_path)
            
            if not template_file.exists():
                return {
                    "status": "error",
                    "message": "Template PDF no encontrado",
                    "filename": None,
                    "file_path": None
                }
            
            # Validar que sea PDF
            if template_file.suffix.lower() != '.pdf':
                return {
                    "status": "error",
                    "message": f"El template debe ser un archivo PDF, se encontró: {template_file.suffix}",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear nombre único para el archivo generado
            student_name = evaluation_data.get("full_name", "estudiante").replace(" ", "_")
            unique_filename = f"evaluacion_salud_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Abrir el archivo PDF
            pdf_document = fitz.open(template_file)
            
            # Función auxiliar para formatear fechas
            def format_date(date_str: Optional[str]) -> str:
                if not date_str:
                    return ""
                try:
                    if isinstance(date_str, str):
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        return date_obj.strftime("%d/%m/%Y")
                    return ""
                except:
                    return str(date_str) if date_str else ""
            
            # Función auxiliar para obtener valor o string vacío
            def get_value(key: str, default: str = "") -> str:
                value = evaluation_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
            # Obtener género (F o M)
            gender_marker = ""
            gender_name = evaluation_data.get("gender_name", "")
            if gender_name:
                gender_upper = gender_name.upper()
                if "FEMENINO" in gender_upper or "F" in gender_upper:
                    gender_marker = "F"
                elif "MASCULINO" in gender_upper or "M" in gender_upper:
                    gender_marker = "M"
            
            # Obtener procedencia
            procedence_id = evaluation_data.get("procedence_id")
            procedence_markers = {
                "Salud pública": "",
                "Particular": "",
                "Escuela": "",
                "Otro": ""
            }
            if procedence_id:
                # Mapear procedence_id a opciones (1=Salud pública, 2=Particular, 3=Escuela, 4=Otro)
                if procedence_id == 1:
                    procedence_markers["Salud pública"] = "●"
                elif procedence_id == 2:
                    procedence_markers["Particular"] = "●"
                elif procedence_id == 3:
                    procedence_markers["Escuela"] = "●"
                elif procedence_id == 4:
                    procedence_markers["Otro"] = "●"
            
            # Mapeo de tags a valores
            tag_replacements = {
                "[STUDENT_FULLNAME]": get_value("full_name"),
                "[STUDENT_RUT]": get_value("identification_number"),
                "[STUDENT_BIRTH]": format_date(get_value("born_date")),
                "[STUDENT_AGE]": get_value("age"),
                "[NATIONALITY]": evaluation_data.get("nationality_name", ""),
                "[PROFESSIONAL_PHONE]": get_value("professional_contact"),
                "[EVALUATION_DATE]": format_date(get_value("evaluation_date")),
                "[REEVALUATION_DATE]": format_date(get_value("reevaluation_date")),
                "[INDICATIONS]": get_value("indications"),
                "[DIAGNOSTIC]": get_value("diagnosis"),
                "[PROFESSIONAL_FULLNAME]": evaluation_data.get("professional_fullname", ""),
                "[PRO_RUT]": get_value("professional_identification_number"),
                "[RE_NUMBER]": get_value("professional_registration_number"),
                "[SPECIALITY]": get_value("professional_specialty"),
                "[GENERAL_ASSESMENT]": get_value("general_assessment"),
                "[GENERAL_ASSESSMENT]": get_value("general_assessment"),  # Variante correcta
                # Campos adicionales
                "[NATIVE_LANGUAGE]": get_value("native_language"),
                "[LANGUAGE_USUALLY_USED]": get_value("language_usually_used"),
                "[CONSULTATION_REASON]": get_value("consultation_reason_detail"),
                "[PROCEDENCE_OTHER]": get_value("procedence_other"),
                # Género
                "[GENDER_F]": "●" if gender_marker == "F" else "",
                "[GENDER_M]": "●" if gender_marker == "M" else "",
                # Procedencia
                "[PROCEDENCE_PUBLIC]": procedence_markers.get("Salud pública", ""),
                "[PROCEDENCE_PRIVATE]": procedence_markers.get("Particular", ""),
                "[PROCEDENCE_SCHOOL]": procedence_markers.get("Escuela", ""),
                "[PROCEDENCE_OTHER_MARKER]": procedence_markers.get("Otro", ""),
            }
            
            found_and_modified = False
            
            # Procesar cada página del PDF
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Obtener todo el texto de la página en formato dict para búsqueda más precisa
                page_dict = None
                try:
                    page_dict = page.get_text("dict")
                except:
                    pass
                
                # Reemplazar cada tag
                for tag, value in tag_replacements.items():
                    # Siempre reemplazar, incluso si el valor está vacío (dejará el campo vacío)
                    text_instances = []
                    
                    # Intentar diferentes variaciones del tag
                    tag_variations = [
                        tag,  # Tag original con corchetes
                        tag.upper(),  # Mayúsculas
                        tag.lower(),  # Minúsculas
                    ]
                    
                    # Buscar cada variación usando search_for
                    for tag_variant in tag_variations:
                        try:
                            # Buscar con flags de case insensitive y dehyphenate
                            found = page.search_for(tag_variant, flags=fitz.TEXT_DEHYPHENATE | fitz.TEXT_IGNORECASE)
                            if found:
                                text_instances.extend(found)
                                break  # Si se encuentra, no buscar más variaciones con search_for
                        except:
                            try:
                                # Si falla con flags, intentar sin flags
                                found = page.search_for(tag_variant)
                                if found:
                                    text_instances.extend(found)
                                    break
                            except:
                                pass
                    
                    # Si aún no se encuentra, buscar usando get_text("dict") para posición exacta
                    if not text_instances and page_dict:
                        try:
                            # Buscar en bloques de texto
                            for block in page_dict.get("blocks", []):
                                if "lines" in block:
                                    for line in block["lines"]:
                                        full_line_text = ""
                                        line_spans = []
                                        for span in line.get("spans", []):
                                            span_text = span.get("text", "")
                                            full_line_text += span_text
                                            line_spans.append((span, span_text))
                                        
                                        # Buscar tag en el texto completo de la línea (case insensitive)
                                        full_line_text_upper = full_line_text.upper()
                                        for tag_variant in tag_variations:
                                            tag_variant_upper = tag_variant.upper()
                                            # Buscar con case insensitive
                                            if tag_variant_upper in full_line_text_upper:
                                                # Encontrar qué span(s) contiene(n) el tag
                                                matching_spans = []
                                                for span, span_text in line_spans:
                                                    span_text_upper = span_text.upper()
                                                    if tag_variant_upper in span_text_upper:
                                                        matching_spans.append(span)
                                                
                                                if matching_spans:
                                                    # Calcular el rectángulo que cubre todos los spans que contienen el tag
                                                    x0 = min(s.get("bbox", [0, 0, 0, 0])[0] for s in matching_spans)
                                                    y0 = min(s.get("bbox", [0, 0, 0, 0])[1] for s in matching_spans)
                                                    x1 = max(s.get("bbox", [0, 0, 0, 0])[2] for s in matching_spans)
                                                    y1 = max(s.get("bbox", [0, 0, 0, 0])[3] for s in matching_spans)
                                                    rect = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
                                                    text_instances.append(rect)
                                                break
                        except Exception as e:
                            pass
                    
                    # Reemplazar todas las instancias encontradas
                    if text_instances:
                        # Eliminar duplicados manteniendo el orden
                        seen_rects = set()
                        unique_instances = []
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        for rect in text_instances:
                            # Validar que el rectángulo esté dentro de los límites de la página
                            if (rect.x0 >= 0 and rect.y0 >= 0 and 
                                rect.x1 <= page_width and rect.y1 <= page_height and
                                rect.x1 > rect.x0 and rect.y1 > rect.y0):
                                
                                rect_key = (round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1))
                                if rect_key not in seen_rects:
                                    seen_rects.add(rect_key)
                                    unique_instances.append(rect)
                        
                        # Reemplazar cada instancia única
                        for rect in unique_instances:
                            found_and_modified = True
                            
                            # Validar el rectángulo antes de aplicar redacción
                            if rect.x1 > rect.x0 and rect.y1 > rect.y0:
                                # Redactar el texto original (cubrir con blanco)
                                page.add_redact_annot(rect, fill=(1, 1, 1))
                                page.apply_redactions()
                                
                                # Insertar el nuevo texto
                                # Para puntos negros (género, procedencia), usar un tamaño de fuente más grande
                                if value == "●":
                                    fontsize = 18
                                else:
                                    fontsize = 10
                                
                                try:
                                    # Intentar insertar el texto en un textbox
                                    text_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
                                    rc = page.insert_textbox(
                                        text_rect,
                                        value,
                                        fontsize=fontsize,
                                        color=(0, 0, 0),
                                        align=0,
                                        overlay=True
                                    )
                                    
                                    # Si el texto no cabe, usar insert_text como fallback
                                    if rc < 0:
                                        page.insert_text(
                                            (rect.x0 + 2, rect.y0 + fontsize),
                                            value,
                                            fontsize=fontsize,
                                            color=(0, 0, 0),
                                            overlay=True
                                        )
                                except Exception as e:
                                    # Si falla, intentar método alternativo
                                    try:
                                        page.insert_text(
                                            (rect.x0 + 2, rect.y0 + fontsize),
                                            value,
                                            fontsize=fontsize,
                                            color=(0, 0, 0),
                                            overlay=True
                                        )
                                    except:
                                        pass
            
            # Guardar el PDF modificado
            pdf_document.save(output_file)
            pdf_document.close()
            
            return {
                "status": "success",
                "message": "PDF generado exitosamente",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF: {str(e)}",
                "filename": None,
                "file_path": None
            }

    @staticmethod
    def generate_health_evaluation_document(
        template_path: str,
        evaluation_data: Dict[str, Any],
        output_directory: str = "files/original_student_files"
    ) -> Dict[str, Any]:
        """
        Genera un documento Word de evaluación de salud a partir de un template.
        Reemplaza los campos del template con los datos de la evaluación.
        
        Los campos pueden identificarse de varias formas:
        1. Campos de formulario (form fields) con nombres específicos
        2. Placeholders de texto como [FULL_NAME], {full_name}, etc.
        3. Texto que identifica la posición seguido de un campo
        
        Args:
            template_path: Ruta del archivo Word template
            evaluation_data: Diccionario con los datos de la evaluación de salud
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        converted_path = None  # Variable para rastrear archivos temporales
        try:
            template_file = Path(template_path)
            
            if not template_file.exists():
                return {
                    "status": "error",
                    "message": "Template no encontrado",
                    "filename": None,
                    "file_path": None
                }
            
            # Validar y convertir si es necesario
            file_extension = template_file.suffix.lower()
            
            # Si es .doc, intentar convertirlo a .docx temporalmente
            if file_extension == '.doc':
                import platform
                import subprocess
                import tempfile
                import os
                
                converted_path = None
                temp_dir = tempfile.gettempdir()
                temp_docx = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex[:8]}.docx")
                
                # Detectar el sistema operativo
                is_windows = platform.system() == "Windows"
                
                # Intentar convertir usando LibreOffice (funciona en Windows y Linux)
                try:
                    # En Linux, el comando puede ser 'libreoffice' o 'soffice'
                    # En Windows, generalmente es 'soffice.exe' o la ruta completa
                    libreoffice_cmd = None
                    
                    if is_windows:
                        # Intentar diferentes rutas comunes en Windows
                        # Buscar en el PATH primero, luego en ubicaciones comunes
                        possible_paths = [
                            "soffice.exe",  # En PATH
                            "soffice",      # En PATH sin extensión
                            r"C:\Program Files\LibreOffice\program\soffice.exe",
                            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                            r"C:\Program Files\LibreOffice 7\program\soffice.exe",
                            r"C:\Program Files\LibreOffice 6\program\soffice.exe",
                            r"C:\Program Files\LibreOffice 5\program\soffice.exe",
                        ]
                        # También buscar en AppData (instalaciones portables)
                        import os
                        appdata = os.getenv('LOCALAPPDATA', '')
                        if appdata:
                            possible_paths.append(os.path.join(appdata, r"Programs\LibreOffice\program\soffice.exe"))
                    else:
                        # En Linux, generalmente está en el PATH
                        possible_paths = ["libreoffice", "soffice", "/usr/bin/libreoffice", "/usr/bin/soffice"]
                    
                    # Buscar el comando disponible
                    for cmd in possible_paths:
                        try:
                            result = subprocess.run(
                                [cmd, "--version"],
                                capture_output=True,
                                timeout=5
                            )
                            if result.returncode == 0:
                                libreoffice_cmd = cmd
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    
                    if not libreoffice_cmd:
                        # Si no se encuentra LibreOffice, intentar win32com solo en Windows
                        if is_windows:
                            try:
                                import win32com.client
                                
                                # Abrir Word y convertir
                                word = win32com.client.Dispatch("Word.Application")
                                word.Visible = False
                                doc = word.Documents.Open(str(template_file.absolute()))
                                doc.SaveAs2(temp_docx, FileFormat=16)  # 16 = wdFormatXMLDocument (.docx)
                                doc.Close()
                                word.Quit()
                                
                                template_file = Path(temp_docx)
                                converted_path = temp_docx
                            except ImportError:
                                # pywin32 no está instalado
                                if is_windows:
                                    return {
                                        "status": "error",
                                        "message": "No se encontró LibreOffice ni pywin32 para usar Microsoft Word. Opciones: 1) Instala LibreOffice (recomendado), 2) Instala pywin32: pip install pywin32 (requiere Word instalado), 3) Convierte el archivo manualmente a .docx.",
                                        "filename": None,
                                        "file_path": None
                                    }
                                else:
                                    return {
                                        "status": "error",
                                        "message": "LibreOffice no está instalado. Para convertir archivos .doc a .docx en Ubuntu/Linux, instala LibreOffice: sudo apt-get update && sudo apt-get install -y libreoffice",
                                        "filename": None,
                                        "file_path": None
                                    }
                            except Exception as e:
                                error_str = str(e)
                                # Detectar si el error es porque Word no está instalado
                                if "Word.Application" in error_str or "COM" in error_str or "0x80040154" in error_str:
                                    return {
                                        "status": "error",
                                        "message": "Microsoft Word no está instalado o no está disponible. Opciones: 1) Instala LibreOffice (recomendado, gratuito): https://www.libreoffice.org/download/, 2) Instala Microsoft Word, 3) Convierte el archivo FU_EVALUACION-DE_SALUD_2024-3.doc manualmente a .docx usando Word o LibreOffice.",
                                        "filename": None,
                                        "file_path": None
                                    }
                                else:
                                    return {
                                        "status": "error",
                                        "message": f"Error al convertir .doc a .docx usando Word: {error_str}. Asegúrate de tener Microsoft Word instalado o instala LibreOffice (gratis): https://www.libreoffice.org/download/",
                                        "filename": None,
                                        "file_path": None
                                    }
                        else:
                            return {
                                "status": "error",
                                "message": "LibreOffice no está instalado. Para convertir archivos .doc a .docx en Ubuntu, instala LibreOffice: sudo apt-get update && sudo apt-get install -y libreoffice",
                                "filename": None,
                                "file_path": None
                            }
                    else:
                        # Convertir usando LibreOffice
                        result = subprocess.run([
                            libreoffice_cmd, "--headless", "--convert-to", "docx",
                            "--outdir", temp_dir,
                            str(template_file.absolute())
                        ], capture_output=True, timeout=30)
                        
                        if result.returncode == 0:
                            # LibreOffice crea el archivo con el mismo nombre pero .docx
                            converted_docx = Path(temp_dir) / f"{template_file.stem}.docx"
                            if converted_docx.exists():
                                converted_docx.rename(temp_docx)
                                template_file = Path(temp_docx)
                                converted_path = temp_docx
                            else:
                                return {
                                    "status": "error",
                                    "message": "No se pudo crear el archivo convertido. Verifica los permisos del directorio temporal.",
                                    "filename": None,
                                    "file_path": None
                                }
                        else:
                            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else 'Error desconocido'
                            return {
                                "status": "error",
                                "message": f"Error al convertir .doc a .docx con LibreOffice: {error_msg}",
                                "filename": None,
                                "file_path": None
                            }
                            
                except subprocess.TimeoutExpired:
                    return {
                        "status": "error",
                        "message": "Timeout al convertir el archivo .doc. El proceso tardó demasiado.",
                        "filename": None,
                        "file_path": None
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Error inesperado al convertir .doc a .docx: {str(e)}",
                        "filename": None,
                        "file_path": None
                    }
            
            elif file_extension != '.docx':
                return {
                    "status": "error",
                    "message": f"Formato de archivo no soportado: {file_extension}. Solo se soporta .docx o .doc",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear nombre único para el archivo generado (PDF en lugar de DOCX)
            student_name = evaluation_data.get("full_name", "estudiante").replace(" ", "_")
            unique_filename_docx = f"evaluacion_salud_{student_name}_{uuid.uuid4().hex[:8]}.docx"
            unique_filename = f"evaluacion_salud_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file_docx = Path(output_directory) / unique_filename_docx
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Abrir el documento template
            try:
                doc = Document(template_file)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error al abrir el template. Asegúrate de que es un archivo .docx válido: {str(e)}",
                    "filename": None,
                    "file_path": None
                }
            
            # Función auxiliar para formatear fechas
            def format_date(date_str: Optional[str]) -> str:
                if not date_str:
                    return ""
                try:
                    if isinstance(date_str, str):
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        return date_obj.strftime("%d/%m/%Y")
                    return ""
                except:
                    return str(date_str) if date_str else ""
            
            # Función auxiliar para obtener valor o string vacío
            def get_value(key: str, default: str = "") -> str:
                value = evaluation_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
            # Mapeo de campos: diferentes formas de identificar cada campo
            # Cada campo puede tener múltiples identificadores
            field_mapping = {
                "full_name": {
                    "value": get_value("full_name"),
                    "placeholders": ["[FULL_NAME]", "{full_name}", "[NOMBRE_COMPLETO]", "{nombre_completo}", "FULL_NAME", "full_name"]
                },
                "identification_number": {
                    "value": get_value("identification_number"),
                    "placeholders": ["[IDENTIFICATION_NUMBER]", "{identification_number}", "[RUT]", "{rut}", "[IDENTIFICACION]", "{identificacion}"]
                },
                "born_date": {
                    "value": format_date(get_value("born_date")),
                    "placeholders": ["[BORN_DATE]", "{born_date}", "[FECHA_NACIMIENTO]", "{fecha_nacimiento}", "[FECHA_NAC]", "{fecha_nac}"]
                },
                "age": {
                    "value": get_value("age"),
                    "placeholders": ["[AGE]", "{age}", "[EDAD]", "{edad}"]
                },
                "native_language": {
                    "value": get_value("native_language"),
                    "placeholders": ["[NATIVE_LANGUAGE]", "{native_language}", "[LENGUA_NATIVA]", "{lengua_nativa}", "[LENGUA_FAMILIA]", "{lengua_familia}"]
                },
                "language_usually_used": {
                    "value": get_value("language_usually_used"),
                    "placeholders": ["[LANGUAGE_USUALLY_USED]", "{language_usually_used}", "[LENGUA_HABITUAL]", "{lengua_habitual}", "[LENGUA_USO]", "{lengua_uso}"]
                },
                "consultation_reason_detail": {
                    "value": get_value("consultation_reason_detail"),
                    "placeholders": ["[CONSULTATION_REASON_DETAIL]", "{consultation_reason_detail}", "[MOTIVO_CONSULTA]", "{motivo_consulta}", "[DETALLE_MOTIVO]", "{detalle_motivo}"]
                },
                "professional_identification_number": {
                    "value": get_value("professional_identification_number"),
                    "placeholders": ["[PROFESSIONAL_IDENTIFICATION_NUMBER]", "{professional_identification_number}", "[RUT_PROFESIONAL]", "{rut_profesional}", "[RUT_MEDICO]", "{rut_medico}"]
                },
                "professional_registration_number": {
                    "value": get_value("professional_registration_number"),
                    "placeholders": ["[PROFESSIONAL_REGISTRATION_NUMBER]", "{professional_registration_number}", "[REGISTRO_PROFESIONAL]", "{registro_profesional}", "[N_REGISTRO]", "{n_registro}"]
                },
                "professional_specialty": {
                    "value": get_value("professional_specialty"),
                    "placeholders": ["[PROFESSIONAL_SPECIALTY]", "{professional_specialty}", "[ESPECIALIDAD]", "{especialidad}", "[ESPECIALIDAD_PROFESIONAL]", "{especialidad_profesional}"]
                },
                "procedence_other": {
                    "value": get_value("procedence_other"),
                    "placeholders": ["[PROCEDENCE_OTHER]", "{procedence_other}", "[PROCEDENCIA_OTRO]", "{procedencia_otro}", "[OTRO_PROCEDENCIA]", "{otro_procedencia}"]
                },
                "professional_contact": {
                    "value": get_value("professional_contact"),
                    "placeholders": ["[PROFESSIONAL_CONTACT]", "{professional_contact}", "[CONTACTO_PROFESIONAL]", "{contacto_profesional}", "[FONO_EMAIL]", "{fono_email}"]
                },
                "evaluation_date": {
                    "value": format_date(get_value("evaluation_date")),
                    "placeholders": ["[EVALUATION_DATE]", "{evaluation_date}", "[FECHA_EVALUACION]", "{fecha_evaluacion}", "[FECHA_EVAL]", "{fecha_eval}"]
                },
                "reevaluation_date": {
                    "value": format_date(get_value("reevaluation_date")),
                    "placeholders": ["[REEVALUATION_DATE]", "{reevaluation_date}", "[FECHA_REEVALUACION]", "{fecha_reevaluacion}", "[FECHA_REVAL]", "{fecha_reval}"]
                },
                "general_assessment": {
                    "value": get_value("general_assessment"),
                    "placeholders": ["[GENERAL_ASSESSMENT]", "{general_assessment}", "[VALORACION_GENERAL]", "{valoracion_general}", "[VALORACION]", "{valoracion}"]
                },
                "diagnosis": {
                    "value": get_value("diagnosis"),
                    "placeholders": ["[DIAGNOSIS]", "{diagnosis}", "[DIAGNOSTICO]", "{diagnostico}"]
                },
                "indications": {
                    "value": get_value("indications"),
                    "placeholders": ["[INDICATIONS]", "{indications}", "[INDICACIONES]", "{indicaciones}"]
                }
            }
            
            # Función para reemplazar todos los placeholders en un texto
            def replace_placeholders(text: str) -> str:
                result = text
                for field_data in field_mapping.values():
                    for placeholder in field_data["placeholders"]:
                        result = result.replace(placeholder, field_data["value"])
                return result
            
            # Reemplazar texto en párrafos
            for paragraph in doc.paragraphs:
                original_text = paragraph.text
                new_text = replace_placeholders(original_text)
                if original_text != new_text:
                    # Limpiar el párrafo y agregar el nuevo texto
                    paragraph.clear()
                    paragraph.add_run(new_text)
            
            # Reemplazar texto en tablas
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            original_text = paragraph.text
                            new_text = replace_placeholders(original_text)
                            if original_text != new_text:
                                # Limpiar el párrafo y agregar el nuevo texto
                                paragraph.clear()
                                paragraph.add_run(new_text)
            
            # Intentar reemplazar campos de formulario (form fields)
            # Esto requiere acceso al XML del documento
            try:
                from docx.oxml.text.paragraph import CT_P
                from docx.oxml.ns import qn
                
                # Buscar campos de formulario en el documento
                for paragraph in doc.paragraphs:
                    for run in paragraph.runs:
                        # Buscar campos de formulario por nombre
                        for field_name, field_data in field_mapping.items():
                            # Los campos de formulario pueden tener diferentes nombres
                            # Intentar buscar por el nombre del campo o variaciones
                            pass  # python-docx tiene limitaciones con campos de formulario
            except:
                # Si no se pueden procesar campos de formulario, continuar con placeholders
                pass
            
            # Guardar el documento Word generado temporalmente
            doc.save(str(output_file_docx))
            
            # Limpiar archivo temporal si se convirtió de .doc
            if converted_path and Path(converted_path).exists():
                try:
                    import os
                    os.unlink(converted_path)
                except:
                    pass
            
            # Convertir el Word a PDF usando LibreOffice
            import platform
            import subprocess
            
            is_windows = platform.system() == "Windows"
            libreoffice_cmd = None
            
            # Buscar LibreOffice
            if is_windows:
                possible_paths = [
                    "soffice.exe",
                    "soffice",
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                    r"C:\Program Files\LibreOffice 7\program\soffice.exe",
                    r"C:\Program Files\LibreOffice 6\program\soffice.exe",
                ]
                import os
                appdata = os.getenv('LOCALAPPDATA', '')
                if appdata:
                    possible_paths.append(os.path.join(appdata, r"Programs\LibreOffice\program\soffice.exe"))
            else:
                possible_paths = ["libreoffice", "soffice", "/usr/bin/libreoffice", "/usr/bin/soffice"]
            
            # Buscar el comando disponible
            for cmd in possible_paths:
                try:
                    result = subprocess.run(
                        [cmd, "--version"],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        libreoffice_cmd = cmd
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            if not libreoffice_cmd:
                # Si no hay LibreOffice, intentar usar Word para convertir a PDF (solo Windows)
                if is_windows:
                    try:
                        import win32com.client
                        
                        # Abrir Word y convertir a PDF
                        word = win32com.client.Dispatch("Word.Application")
                        word.Visible = False
                        doc = word.Documents.Open(str(output_file_docx.absolute()))
                        # 17 = wdFormatPDF
                        doc.SaveAs2(str(output_file.absolute()), FileFormat=17)
                        doc.Close()
                        word.Quit()
                        
                        # Eliminar el archivo Word temporal
                        try:
                            import os
                            if output_file_docx.exists():
                                os.unlink(output_file_docx)
                        except:
                            pass
                        
                        if output_file.exists():
                            return {
                                "status": "success",
                                "message": "PDF generado exitosamente usando Microsoft Word",
                                "filename": unique_filename,
                                "file_path": str(output_file)
                            }
                        else:
                            return {
                                "status": "error",
                                "message": "No se pudo crear el archivo PDF con Word. Verifica los permisos del directorio.",
                                "filename": None,
                                "file_path": None
                            }
                    except ImportError:
                        # pywin32 no está disponible
                        try:
                            import os
                            if output_file_docx.exists():
                                os.unlink(output_file_docx)
                        except:
                            pass
                        return {
                            "status": "error",
                            "message": "LibreOffice no está instalado y pywin32 no está disponible. Se requiere LibreOffice o Microsoft Word (con pywin32) para convertir Word a PDF. Instala LibreOffice (recomendado) o pywin32: pip install pywin32",
                            "filename": None,
                            "file_path": None
                        }
                    except Exception as e:
                        # Error al usar Word
                        error_str = str(e)
                        try:
                            import os
                            if output_file_docx.exists():
                                os.unlink(output_file_docx)
                        except:
                            pass
                        
                        # Detectar si el error es porque Word no está instalado
                        if "Word.Application" in error_str or "COM" in error_str or "0x80040154" in error_str or "Invalid class string" in error_str:
                            return {
                                "status": "error",
                                "message": "Microsoft Word no está instalado. Para convertir Word a PDF necesitas: 1) Instalar LibreOffice (gratis, recomendado): https://www.libreoffice.org/download/, 2) Instalar Microsoft Word, 3) O usar un servicio de conversión externo.",
                                "filename": None,
                                "file_path": None
                            }
                        else:
                            return {
                                "status": "error",
                                "message": f"Error al convertir Word a PDF usando Microsoft Word: {error_str}. Asegúrate de tener Word instalado o instala LibreOffice (gratis): https://www.libreoffice.org/download/",
                                "filename": None,
                                "file_path": None
                            }
                else:
                    # Linux sin LibreOffice
                    try:
                        import os
                        if output_file_docx.exists():
                            os.unlink(output_file_docx)
                    except:
                        pass
                    return {
                        "status": "error",
                        "message": "LibreOffice no está instalado. Para convertir Word a PDF en Ubuntu/Linux, instala LibreOffice: sudo apt-get update && sudo apt-get install -y libreoffice",
                        "filename": None,
                        "file_path": None
                    }
            
            # Convertir Word a PDF
            try:
                result = subprocess.run([
                    libreoffice_cmd, "--headless", "--convert-to", "pdf",
                    "--outdir", str(output_file.parent),
                    str(output_file_docx.absolute())
                ], capture_output=True, timeout=30)
                
                if result.returncode == 0:
                    # LibreOffice crea el PDF con el mismo nombre base
                    pdf_file = output_file_docx.with_suffix('.pdf')
                    if pdf_file.exists():
                        # Mover/renombrar al nombre final deseado
                        pdf_file.rename(output_file)
                        
                        # Eliminar el archivo Word temporal
                        try:
                            import os
                            if output_file_docx.exists():
                                os.unlink(output_file_docx)
                        except:
                            pass
                        
                        return {
                            "status": "success",
                            "message": "PDF generado exitosamente",
                            "filename": unique_filename,
                            "file_path": str(output_file)
                        }
                    else:
                        return {
                            "status": "error",
                            "message": "No se pudo crear el archivo PDF. Verifica los permisos del directorio.",
                            "filename": None,
                            "file_path": None
                        }
                else:
                    error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else 'Error desconocido'
                    # Limpiar archivo Word temporal
                    try:
                        import os
                        if output_file_docx.exists():
                            os.unlink(output_file_docx)
                    except:
                        pass
                    return {
                        "status": "error",
                        "message": f"Error al convertir Word a PDF: {error_msg}",
                        "filename": None,
                        "file_path": None
                    }
            except subprocess.TimeoutExpired:
                # Limpiar archivo Word temporal
                try:
                    import os
                    if output_file_docx.exists():
                        os.unlink(output_file_docx)
                except:
                    pass
                return {
                    "status": "error",
                    "message": "Timeout al convertir Word a PDF. El proceso tardó demasiado.",
                    "filename": None,
                    "file_path": None
                }
            except Exception as e:
                # Limpiar archivo Word temporal
                try:
                    import os
                    if output_file_docx.exists():
                        os.unlink(output_file_docx)
                except:
                    pass
                return {
                    "status": "error",
                    "message": f"Error inesperado al convertir Word a PDF: {str(e)}",
                    "filename": None,
                    "file_path": None
                }
            
        except Exception as e:
            # Limpiar archivo temporal si existe
            if converted_path and Path(converted_path).exists():
                try:
                    import os
                    os.unlink(converted_path)
                except:
                    pass
            
            return {
                "status": "error",
                "message": f"Error generando documento: {str(e)}",
                "filename": None,
                "file_path": None
            }

    @staticmethod
    def inspect_pdf_form_fields(template_path: str) -> Dict[str, Any]:
        """
        Inspecciona un PDF para identificar qué campos de formulario contiene.
        Útil para entender cómo están estructurados los campos en el template PDF.
        
        Args:
            template_path: Ruta del archivo PDF template
        
        Returns:
            dict: Información sobre los campos de formulario encontrados
        """
        try:
            template_file = Path(template_path)
            
            if not template_file.exists():
                return {
                    "status": "error",
                    "message": "Template PDF no encontrado",
                    "fields": []
                }
            
            pdf_document = fitz.open(template_file)
            
            form_fields = []
            text_placeholders = set()
            
            # Buscar campos de formulario en todas las páginas
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Obtener widgets (campos de formulario)
                widgets = page.widgets()
                for widget in widgets:
                    field_info = {
                        "field_name": widget.field_name,
                        "field_type": widget.field_type_string,
                        "field_value": widget.field_value if hasattr(widget, 'field_value') else None,
                        "rect": {
                            "x0": widget.rect.x0,
                            "y0": widget.rect.y0,
                            "x1": widget.rect.x1,
                            "y1": widget.rect.y1
                        },
                        "page": page_num + 1
                    }
                    form_fields.append(field_info)
                
                # También buscar placeholders de texto
                text = page.get_text()
                placeholders_brackets = re.findall(r'\[([^\]]+)\]', text)
                placeholders_braces = re.findall(r'\{([^\}]+)\}', text)
                
                for p in placeholders_brackets:
                    text_placeholders.add(f"[{p}]")
                for p in placeholders_braces:
                    text_placeholders.add(f"{{{p}}}")
            
            pdf_document.close()
            
            return {
                "status": "success",
                "message": "PDF inspeccionado exitosamente",
                "form_fields": form_fields,
                "text_placeholders": list(text_placeholders),
                "total_form_fields": len(form_fields)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error inspeccionando PDF: {str(e)}",
                "fields": []
            }

    @staticmethod
    def inspect_template_fields(template_path: str) -> Dict[str, Any]:
        """
        Inspecciona un template Word para identificar qué campos contiene.
        Útil para entender cómo están estructurados los campos en el template.
        
        Args:
            template_path: Ruta del archivo Word template
        
        Returns:
            dict: Información sobre los campos encontrados en el template
        """
        try:
            template_file = Path(template_path)
            
            if not template_file.exists():
                return {
                    "status": "error",
                    "message": "Template no encontrado",
                    "fields": []
                }
            
            doc = Document(template_file)
            
            found_placeholders = set()
            found_text = []
            
            # Buscar placeholders en párrafos
            for paragraph in doc.paragraphs:
                text = paragraph.text
                # Buscar placeholders con formato [CAMPO] o {campo}
                placeholders_brackets = re.findall(r'\[([^\]]+)\]', text)
                placeholders_braces = re.findall(r'\{([^\}]+)\}', text)
                
                for p in placeholders_brackets:
                    found_placeholders.add(f"[{p}]")
                for p in placeholders_braces:
                    found_placeholders.add(f"{{{p}}}")
                
                if text.strip():
                    found_text.append(text[:100])  # Primeros 100 caracteres
            
            # Buscar en tablas
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            text = paragraph.text
                            placeholders_brackets = re.findall(r'\[([^\]]+)\]', text)
                            placeholders_braces = re.findall(r'\{([^\}]+)\}', text)
                            
                            for p in placeholders_brackets:
                                found_placeholders.add(f"[{p}]")
                            for p in placeholders_braces:
                                found_placeholders.add(f"{{{p}}}")
            
            # Intentar encontrar campos de formulario (form fields)
            form_fields = []
            try:
                # python-docx tiene limitaciones para acceder a campos de formulario
                # Necesitaríamos usar lxml directamente para esto
                pass
            except:
                pass
            
            return {
                "status": "success",
                "message": "Template inspeccionado exitosamente",
                "placeholders_found": list(found_placeholders),
                "form_fields_found": form_fields,
                "sample_text": found_text[:10]  # Primeros 10 textos como muestra
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error inspeccionando template: {str(e)}",
                "fields": []
            }
