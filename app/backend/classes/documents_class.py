import uuid
import re
import os
import platform
import subprocess
import tempfile
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.backend.db.models import DocumentModel, BirthCertificateDocumentModel, HealthEvaluationModel, FolderModel

# pypdf imports (opcional, solo si está instalado)
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, NumberObject, BooleanObject, TextStringObject
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    NameObject = None
    NumberObject = None
    BooleanObject = None
    TextStringObject = None

# ReportLab imports (opcional, solo si está instalado)
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Win32 imports (opcional, solo Windows)
try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# docx imports adicionales
try:
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.ns import qn
    DOCX_EXTRA_AVAILABLE = True
except ImportError:
    DOCX_EXTRA_AVAILABLE = False


class DocumentsClass:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_document_pdf(
        document_id: int,
        document_data: Dict[str, Any],
        db: Optional[Session] = None,
        template_path: Optional[str] = None,
        tag_replacements: Optional[Dict[str, str]] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Función general para generar PDFs de cualquier documento.
        Dependiendo de si hay template_path:
        - Si hay template_path: Sustituye datos en el template PDF usando tag_replacements
        - Si no hay template_path: Crea el PDF desde cero usando ReportLab
        
        Args:
            document_id: ID del documento
            document_data: Diccionario con los datos del documento
            db: Sesión de base de datos (opcional)
            template_path: Ruta del archivo PDF template (opcional, si es None se crea desde cero)
            tag_replacements: Diccionario con mapeo de etiquetas a valores (opcional, se genera automáticamente si es None)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        try:
            # Si es documento 19 (Estado de Avance), usar función específica
            if document_id == 19:
                return DocumentsClass._generate_progress_status_from_scratch(
                    document_id=document_id,
                    progress_status_data=document_data,
                    db=db,
                    output_directory=output_directory
                )
            
            # Si es documento 18 (Estado de Avance), usar función específica
            if document_id == 18:
                return DocumentsClass._generate_progress_status_from_scratch(
                    document_id=document_id,
                    progress_status_data=document_data,
                    db=db,
                    output_directory=output_directory
                )
            
            # Si es documento 22 (Plan de Apoyo Individual), usar función específica
            if document_id == 22:
                return DocumentsClass._generate_individual_support_plan_from_scratch(
                    document_id=document_id,
                    isp_data=document_data,
                    db=db,
                    output_directory=output_directory
                )
            
            # Si es documento 8 (Informe Fonoaudiológico), usar función específica
            if document_id == 8:
                return DocumentsClass._generate_fonoaudiological_report_from_scratch(
                    document_id=document_id,
                    report_data=document_data,
                    db=db,
                    output_directory=output_directory
                )
            
            # Si hay template_path, usar método de sustitución
            if template_path:
                # Si no se proporcionan tag_replacements, generar automáticamente desde document_data
                if tag_replacements is None:
                    tag_replacements = DocumentsClass._generate_tag_replacements(document_data)
                
                return DocumentsClass._generate_pdf_from_template(
                    template_path=template_path,
                    tag_replacements=tag_replacements,
                    document_id=document_id,
                    document_data=document_data,
                    output_directory=output_directory
                )
            else:
                # Si no hay template, crear desde cero usando ReportLab
                return DocumentsClass._generate_pdf_from_scratch(
                    document_id=document_id,
                    document_data=document_data,
                    db=db,
                    output_directory=output_directory
                )
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF: {str(e)}",
                "filename": None,
                "file_path": None
            }
    
    @staticmethod
    def _generate_tag_replacements(document_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Genera automáticamente el mapeo de etiquetas a valores desde document_data.
        Convierte todas las claves del diccionario a formato [KEY] y sus valores a string.
        """
        tag_replacements = {}
        
        # Función auxiliar para formatear fechas
        def format_date(value: Any) -> str:
            if not value:
                return ""
            try:
                if isinstance(value, str):
                    date_obj = datetime.strptime(value, "%Y-%m-%d").date()
                    return date_obj.strftime("%d/%m/%Y")
                elif hasattr(value, 'strftime'):
                    return value.strftime("%d/%m/%Y")
                return ""
            except:
                return str(value) if value else ""
        
        # Generar etiquetas para cada campo
        for key, value in document_data.items():
            if value is not None:
                # Si es una fecha, formatearla
                if 'date' in key.lower() or 'fecha' in key.lower():
                    tag_replacements[f"[{key.upper()}]"] = format_date(value)
                else:
                    tag_replacements[f"[{key.upper()}]"] = str(value) if value else ""
        
        return tag_replacements
    
    @staticmethod
    def _generate_pdf_from_template(
        template_path: str,
        tag_replacements: Dict[str, str],
        document_id: int,
        document_data: Dict[str, Any],
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF sustituyendo datos en un template PDF existente.
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
            student_name = document_data.get("student_fullname", document_data.get("student_name", "documento")).replace(" ", "_")
            unique_filename = f"documento_{document_id}_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Abrir el archivo PDF
            pdf_document = fitz.open(template_file)
            
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
                            found = page.search_for(tag_variant, flags=fitz.TEXT_DEHYPHENATE)
                            if found:
                                text_instances.extend(found)
                                break
                        except:
                            try:
                                found = page.search_for(tag_variant)
                                if found:
                                    text_instances.extend(found)
                                    break
                            except:
                                pass
                    
                    # Si aún no se encuentra, buscar usando get_text("dict")
                    if not text_instances and page_dict:
                        try:
                            for block in page_dict.get("blocks", []):
                                if "lines" in block:
                                    for line in block["lines"]:
                                        full_line_text = ""
                                        line_spans = []
                                        for span in line.get("spans", []):
                                            span_text = span.get("text", "")
                                            full_line_text += span_text
                                            line_spans.append((span, span_text))
                                        
                                        full_line_text_upper = full_line_text.upper()
                                        for tag_variant in tag_variations:
                                            tag_variant_upper = tag_variant.upper()
                                            if tag_variant_upper in full_line_text_upper:
                                                matching_spans = []
                                                for span, span_text in line_spans:
                                                    span_text_upper = span_text.upper()
                                                    if tag_variant_upper in span_text_upper:
                                                        matching_spans.append(span)
                                                
                                                if matching_spans:
                                                    x0 = min(s.get("bbox", [0, 0, 0, 0])[0] for s in matching_spans)
                                                    y0 = min(s.get("bbox", [0, 0, 0, 0])[1] for s in matching_spans)
                                                    x1 = max(s.get("bbox", [0, 0, 0, 0])[2] for s in matching_spans)
                                                    y1 = max(s.get("bbox", [0, 0, 0, 0])[3] for s in matching_spans)
                                                    rect = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
                                                    text_instances.append(rect)
                                                break
                        except:
                            pass
                    
                    # Reemplazar todas las instancias encontradas
                    if text_instances:
                        seen_rects = set()
                        unique_instances = []
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        for rect in text_instances:
                            if isinstance(rect, (list, tuple)) and len(rect) == 4:
                                rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])
                            
                            if (rect.x0 >= 0 and rect.y0 >= 0 and 
                                rect.x1 <= page_width and rect.y1 <= page_height and
                                rect.x1 > rect.x0 and rect.y1 > rect.y0):
                                
                                rect_key = (round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1))
                                if rect_key not in seen_rects:
                                    seen_rects.add(rect_key)
                                    unique_instances.append(rect)
                        
                        for rect in unique_instances:
                            if rect.x1 > rect.x0 and rect.y1 > rect.y0:
                                page.add_redact_annot(rect, fill=(1, 1, 1))
                                page.apply_redactions()
                                
                                fontsize = 10
                                try:
                                    text_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
                                    rc = page.insert_textbox(
                                        text_rect,
                                        value,
                                        fontsize=fontsize,
                                        color=(0, 0, 0),
                                        align=0,
                                        overlay=True
                                    )
                                    
                                    if rc < 0:
                                        page.insert_text(
                                            (rect.x0 + 2, rect.y0 + fontsize),
                                            value,
                                            fontsize=fontsize,
                                            color=(0, 0, 0),
                                            overlay=True
                                        )
                                except:
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
                "message": "PDF generado exitosamente desde template",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF desde template: {str(e)}",
                "filename": None,
                "file_path": None
            }
    
    @staticmethod
    def _generate_pdf_from_scratch(
        document_id: int,
        document_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF desde cero usando ReportLab.
        """
        try:
            if not REPORTLAB_AVAILABLE:
                return {
                    "status": "error",
                    "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear nombre único para el archivo generado
            student_name = document_data.get("student_fullname", document_data.get("student_name", "documento")).replace(" ", "_")
            unique_filename = f"documento_{document_id}_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Crear el documento PDF
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Estilos personalizados
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#000000'),
                spaceAfter=10,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_JUSTIFY,
                leading=14
            )
            
            # Función auxiliar para obtener valor
            def get_value(key: str, default: str = "") -> str:
                value = document_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
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
            
            # Título genérico
            document_title = document_data.get("document_title", f"DOCUMENTO {document_id}")
            elements.append(Paragraph(document_title, title_style))
            elements.append(Spacer(1, 0.3*inch))
            
            # Crear tabla con todos los datos del documento
            table_data = []
            for key, value in document_data.items():
                if value and key not in ['document_title']:
                    # Formatear la clave para mostrar
                    display_key = key.replace('_', ' ').title()
                    display_value = format_date(value) if 'date' in key.lower() or 'fecha' in key.lower() else str(value)
                    table_data.append([display_key + ":", display_value])
            
            if table_data:
                data_table = Table(table_data, colWidths=[5*cm, 11*cm])
                data_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(data_table)
            
            # Construir PDF
            doc.build(elements)
            
            return {
                "status": "success",
                "message": "PDF generado exitosamente desde cero",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except ImportError:
            return {
                "status": "error",
                "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                "filename": None,
                "file_path": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF desde cero: {str(e)}",
                "filename": None,
                "file_path": None
            }

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
                            found = page.search_for(tag_variant, flags=fitz.TEXT_DEHYPHENATE)
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
                DocumentModel.id == id,
                DocumentModel.deleted_date.is_(None)
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
        Solo devuelve documentos que no tienen deleted_date (no eliminados).
        """
        try:
            query = self.db.query(DocumentModel).filter(DocumentModel.deleted_date.is_(None))

            if document_type_id is not None:
                query = query.filter(DocumentModel.document_type_id == document_type_id)
            
            # Filtrar por career_type_id solo si se proporciona y no está vacío
            if career_type_id is not None and career_type_id != 0:
                query = query.filter(DocumentModel.career_type_id == career_type_id)

            documents = query.order_by(DocumentModel.document.asc()).all()

            return [
                {
                    "id": doc.id,
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
            # Buscar el document_id correspondiente al document_type_id (solo no eliminados)
            document = self.db.query(DocumentModel).filter(
                DocumentModel.document_type_id == document_type_id,
                DocumentModel.deleted_date.is_(None)
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
    def generate_health_evaluation_pdf(
        template_path: str,
        evaluation_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de evaluación de salud rellenando campos de formulario AcroForm.
        Usa pypdf para leer y rellenar los campos del formulario.
        
        Args:
            template_path: Ruta del archivo PDF template con campos AcroForm
            evaluation_data: Diccionario con los datos de la evaluación de salud
            db: Sesión de base de datos (opcional, para obtener datos relacionados)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        if not PYPDF_AVAILABLE:
            return {
                "status": "error",
                "message": "pypdf no está instalado. Instálelo con: pip install pypdf",
                "filename": None,
                "file_path": None
            }
        
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
            
            # Leer el PDF template
            reader = PdfReader(template_file)
            writer = PdfWriter()
            
            # Copiar las páginas
            for page in reader.pages:
                writer.add_page(page)
            
            # Copiar el AcroForm del reader al writer
            # Necesitamos copiar el AcroForm después de agregar las páginas
            try:
                # Primero, obtener el AcroForm del reader
                reader_root = reader.trailer.get("/Root", {})
                if "/AcroForm" in reader_root:
                    reader_acro_form = reader_root["/AcroForm"]
                    
                    # Crear el root del writer si no existe
                    if not hasattr(writer, '_root_object') or writer._root_object is None:
                        from pypdf.generic import DictionaryObject
                        writer._root_object = DictionaryObject()
                        # Copiar otras propiedades del root si existen
                        for key, value in reader_root.items():
                            if key != "/AcroForm":
                                writer._root_object[NameObject(key)] = value
                    
                    # Intentar clonar el AcroForm usando el método de pypdf
                    try:
                        cloned_acro_form = reader_acro_form.clone(writer, force_duplicate=True)
                        writer._root_object[NameObject("/AcroForm")] = cloned_acro_form
                    except Exception as clone_error:
                        # Si falla, el AcroForm puede no estar disponible en el writer
                        # pero los campos deberían estar en las páginas
                        pass
            except Exception as e:
                # Continuar de todas formas, puede que los campos estén en las páginas
                pass
            
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
            
            # Calcular edad en años y meses desde fecha de nacimiento
            def age_years_months(born_date_val, reference_date_val=None):
                if not born_date_val:
                    return ""
                try:
                    from datetime import date
                    if isinstance(born_date_val, str):
                        born = datetime.strptime(born_date_val.strip()[:10], "%Y-%m-%d").date()
                    else:
                        born = born_date_val
                    if reference_date_val:
                        ref = (
                            datetime.strptime(str(reference_date_val).strip()[:10], "%Y-%m-%d").date()
                            if isinstance(reference_date_val, str)
                            else reference_date_val
                        )
                    else:
                        ref = date.today()
                    if born > ref:
                        return ""
                    total_months = (ref.year - born.year) * 12 + (ref.month - born.month)
                    if ref.day < born.day:
                        total_months -= 1
                    years = total_months // 12
                    months = total_months % 12
                    if months == 0:
                        return f"{years} años"
                    return f"{years} años {months} meses"
                except Exception:
                    return ""
            
            # Fecha de referencia para la edad (evaluación o hoy)
            ref_date = evaluation_data.get("evaluation_date") or None
            age_str = age_years_months(evaluation_data.get("born_date"), ref_date)
            if not age_str and evaluation_data.get("age") is not None:
                age_str = str(evaluation_data.get("age"))  # fallback solo años
            
            # Inspeccionar los campos del formulario en el PDF
            form_fields = {}
            try:
                # Método 1: Obtener campos de texto usando get_form_text_fields()
                text_fields = reader.get_form_text_fields()
                if text_fields:
                    form_fields.update(text_fields)
                
                # Método 2: Obtener todos los campos accediendo directamente al AcroForm
                root = reader.trailer.get("/Root", {})
                if "/AcroForm" in root:
                    acro_form = root["/AcroForm"]
                    if "/Fields" in acro_form:
                        fields = acro_form["/Fields"]
                        
                        def extract_field_names(field_list):
                            for field_ref in field_list:
                                field = field_ref.get_object()
                                if "/Kids" in field:
                                    extract_field_names(field["/Kids"])
                                if "/T" in field:
                                    field_name = field["/T"]
                                    if field_name:
                                        form_fields[field_name] = None
                        
                        extract_field_names(fields)
                
                # Método 3: También buscar en las anotaciones de cada página
                for page_num, page in enumerate(reader.pages):
                    if "/Annots" in page:
                        for annot in page["/Annots"]:
                            annot_obj = annot.get_object()
                            if "/FT" in annot_obj and "/T" in annot_obj:
                                field_name = annot_obj.get("/T")
                                if field_name:
                                    form_fields[field_name] = None
            except Exception as e:
                pass
            
            # Obtener género (F o M)
            gender_marker = ""
            gender_name = evaluation_data.get("gender_name", "")
            if gender_name:
                gender_upper = gender_name.upper()
                if "FEMENINO" in gender_upper or "F" in gender_upper:
                    gender_marker = "F"
                elif "MASCULINO" in gender_upper or "M" in gender_upper:
                    gender_marker = "M"
            
            # Obtener valores para checkboxes basado en consultation_reason_id
            # Si consultation_reason_id == 1, marcar EGS (Examen General de Salud)
            # Si consultation_reason_id != 1, marcar DDD (Diagnóstico de Discapacidad o Déficit)
            consultation_reason_id = evaluation_data.get("consultation_reason_id")
            is_egs = (consultation_reason_id == 1)
            is_ddd = (consultation_reason_id != 1 and consultation_reason_id is not None)
            
            # EGS = Examen General de Salud (checkbox)
            # DDD = Diagnóstico de Discapacidad o Déficit (checkbox)
            
            # Procedencia: procedence_id 1=SP, 2=P, 3=E, 4=O (checkboxes)
            procedence_id = evaluation_data.get("procedence_id")
            is_sp = (procedence_id == 1)
            is_p = (procedence_id == 2)   # Particular
            is_e = (procedence_id == 3)   # Escuela
            is_o = (procedence_id == 4)   # Otro
            # OE = texto "otro": solo si O está marcado (procedence_id==4) usar procedence_other; si no, en blanco
            oe_value = get_value("procedence_other", "") if is_o else ""
            
            # Preparar datos para los campos del formulario
            # Mapeo según los nombres reales de los campos encontrados en el PDF
            field_mapping = {
                # Identificación del estudiante
                "Nombres y Apellidos": get_value("full_name", ""),
                "RUN": get_value("identification_number", ""),
                "Nacionalidad": evaluation_data.get("nationality_name", ""),
                "Fecha de Nacimiento": format_date(evaluation_data.get("born_date")),
                "BD": format_date(evaluation_data.get("born_date")),  # Campo real del formulario PDF
                "Edad": age_str,
                "Age": age_str,  # Campo real del formulario PDF (edad en años y meses desde fecha nacimiento)
                # Lenguas
                "OL": get_value("native_language", ""),  # Lengua de origen / nativa
                "HL": get_value("language_usually_used", ""),  # Lengua habitual
                # Género (botones de radio) - usar strings para update_page_form_field_values
                "F": "/Yes" if gender_marker == "F" else "/Off",
                "M": "/Yes" if gender_marker == "M" else "/Off",
                # Motivo de consulta
                "MOTIVO DE CONSULTA": get_value("consultation_reason_detail", ""),
                "DD": get_value("consultation_reason_detail", ""),  # Campo real del formulario PDF
                # Identificación del profesional
                "Nombres y Apellidos_2": evaluation_data.get("professional_fullname", ""),
                "Rut": get_value("professional_identification_number", ""),
                "PRN": get_value("professional_registration_number", ""),  # Nº registro profesional
                "Especialidad": evaluation_data.get("professional_specialty_name", get_value("professional_specialty", "")),
                "Procedencia Salud pública Particular Escuela Otro": get_value("procedence_other", ""),
                # Procedencia checkboxes: 1=SP, 2=P, 3=E, 4=O
                "SP": "/Yes" if is_sp else "/Off",
                "E": "/Yes" if is_e else "/Off",
                "P": "/Yes" if is_p else "/Off",
                "O": "/Yes" if is_o else "/Off",
                # OE = texto "otro": solo con valor si O está marcado (procedence_id==4)
                "OE": oe_value,
                "FonoEmail contacto": get_value("professional_contact", ""),
                # Fechas
                "Fecha evaluación": format_date(get_value("evaluation_date")),
                "Fecha reevaluación": format_date(get_value("reevaluation_date")),
                # Examen del estado de salud
                "EXÁMEN DEL ESTADO DE SALUD GENERAL DEL ESTUDIANTE Presenciaausencia de patologías o dificultades de salud que incidan en o expliquen sus necesidades educativas especiales por ejemplo bronquitis crónica problemas sensoriales etcRow1": get_value("general_assessment", ""),
                # Diagnóstico
                "DIAGNÓSTICO  Presencia de un trastorno déficit o discapacidad": get_value("diagnosis", ""),
                "Considere especificaciones del grado y etiología del déficit y pronóstico": get_value("diagnosis", ""),
                # Indicaciones
                "INDICACIONES": get_value("indications", ""),
                "Señale tratamiento médico necesidades de interconsulta exámenes o ayudas técnicas cuando sea el caso u otras recomendaciones u observaciones relevantes para ella estudiante en función de su diagnóstico": get_value("indications", ""),
                # Diagnóstico de discapacidad (campo de texto)
                "DIAGNÓSTICO DE DISCAPACIDAD O DÉFICIT señale cual": get_value("diagnosis", ""),
                # Checkboxes - Basado en consultation_reason_id
                # Si consultation_reason_id == 1: marcar EGS, desmarcar DDD
                # Si consultation_reason_id != 1: marcar DDD, desmarcar EGS
                "EXAMEN GENERAL DE SALUD": "/Yes" if is_egs else "/Off",
                "EGS": "/Yes" if is_egs else "/Off",
                "DDD": "/Yes" if is_ddd else "/Off",
            }
            
            # Construir el diccionario final de datos a rellenar
            # Solo incluir campos que realmente existen en el PDF
            form_data = {}
            
            # Mapeo normalizado (minúsculas, sin espacios) para coincidir con nombres del PDF
            field_mapping_normalized = {k.strip().lower(): k for k in field_mapping.keys()}
            
            for field_name in form_fields.keys():
                value = None
                # 1) Coincidencia exacta
                if field_name in field_mapping:
                    value = field_mapping[field_name]
                # 2) Coincidencia sin distinguir mayúsculas/minúsculas (BD, DD, Age, etc.)
                elif field_name.strip().lower() in field_mapping_normalized:
                    canonical_key = field_mapping_normalized[field_name.strip().lower()]
                    value = field_mapping[canonical_key]
                
                if value is not None:
                    # Checkboxes y radio: siempre agregar
                    if value == "/Off" or value == "/Yes":
                        form_data[field_name] = value
                    # DD y OE: siempre agregar para que el campo aparezca (vacío o con valor)
                    elif field_name.strip().lower() in ("dd", "oe"):
                        form_data[field_name] = value if isinstance(value, str) else (value or "")
                    elif isinstance(value, str) and value.strip():
                        # Resto de campos de texto: solo si tiene contenido
                        form_data[field_name] = value
                else:
                    # Intentar mapeo por palabras clave si no hay coincidencia exacta
                    field_lower = field_name.strip().lower()
                    if "nombre" in field_lower and "apellido" in field_lower and "2" not in field_name:
                        # Es el campo de nombres del estudiante
                        value = get_value("full_name", "")
                        if value:
                            form_data[field_name] = value
                    elif "run" in field_lower and field_name.strip().upper() == "RUN":
                        value = get_value("identification_number", "")
                        if value:
                            form_data[field_name] = value
                    elif "nacionalidad" in field_lower:
                        value = evaluation_data.get("nationality_name", "")
                        if value:
                            form_data[field_name] = value
                    elif field_lower == "dd" or field_lower.endswith(".dd") or ("." in field_lower and field_lower.split(".")[-1].strip() == "dd"):
                        # Campo DD = detalle / motivo de consulta (siempre agregar, vacío o con valor)
                        form_data[field_name] = get_value("consultation_reason_detail", "")
                    elif field_lower == "bd" or field_lower.endswith(".bd") or ("." in field_lower and field_lower.split(".")[-1].strip() == "bd"):
                        value = format_date(evaluation_data.get("born_date"))
                        if value:
                            form_data[field_name] = value
                    elif field_lower == "age" or field_lower.endswith(".age") or ("." in field_lower and field_lower.split(".")[-1].strip() == "age"):
                        if age_str:
                            form_data[field_name] = age_str
                    elif field_name == "F" or field_name == "M":
                        # Botones de radio para género - usar strings
                        if field_name == "F":
                            form_data[field_name] = "/Yes" if gender_marker == "F" else "/Off"
                        elif field_name == "M":
                            form_data[field_name] = "/Yes" if gender_marker == "M" else "/Off"
            
            # Log: campos detectados del PDF y valores de BD
            print(f"--- Campos del PDF detectados: {list(form_fields.keys())}")
            print(f"--- native_language en BD: '{evaluation_data.get('native_language', '')}'")
            print(f"--- language_usually_used en BD: '{evaluation_data.get('language_usually_used', '')}'")
            print("--- PDF Health Evaluation: campo -> valor ---")
            for fn, val in sorted(form_data.items()):
                print(f"Campo: {fn} -> Valor: {val}")
            print("---")
            
            # Rellenar los campos del formulario y hacerlos de solo lectura
            if form_data:
                # Separar campos de texto, radio buttons y checkboxes
                text_fields = {}
                radio_fields = {}
                checkbox_fields = {}
                for field_name, value in form_data.items():
                    if field_name in ["F", "M"]:
                        radio_fields[field_name] = value
                    elif isinstance(value, str) and value in ["/Yes", "/Off"]:
                        # Es un checkbox (botón que puede estar marcado o no)
                        checkbox_fields[field_name] = value
                    else:
                        # Campos de texto: con valor; DD y OE siempre (para vacío cuando corresponda)
                        fn_lower = field_name.strip().lower()
                        if value and str(value).strip() or fn_lower == "dd" or fn_lower == "oe":
                            text_fields[field_name] = value if isinstance(value, str) else (value or "")
                
                # Lookup normalizado: algunos visores/PDFs usan nombres con encoding distinto
                text_fields_normalized = {k.strip().lower(): (k, v) for k, v in text_fields.items()}
                checkbox_fields_normalized = {k.strip().lower(): v for k, v in checkbox_fields.items()}
                radio_fields_normalized = {k.strip().lower(): v for k, v in radio_fields.items()}
                def get_text_value(name_str):
                    if name_str in text_fields:
                        return text_fields[name_str]
                    norm = name_str.strip().lower()
                    if norm in text_fields_normalized:
                        return text_fields_normalized[norm][1]
                    return None
                def _norm(name):
                    return (name or "").strip().lstrip("/").lower()
                def get_checkbox_value(name_str):
                    n = (name_str or "").strip().lstrip("/")
                    if n in checkbox_fields:
                        return checkbox_fields[n]
                    return checkbox_fields_normalized.get(_norm(name_str))
                def get_radio_value(name_str):
                    n = (name_str or "").strip().lstrip("/")
                    if n in radio_fields:
                        return radio_fields[n]
                    return radio_fields_normalized.get(_norm(name_str))
                
                # Pedir al visor que regenere apariencia desde /V (algunos PDFs no muestran valor si no)
                try:
                    if hasattr(writer, '_root_object') and writer._root_object and "/AcroForm" in writer._root_object:
                        af = writer._root_object["/AcroForm"]
                        af[NameObject("/NeedAppearances")] = BooleanObject(True)
                except Exception:
                    pass
                
                # Rellenar todos los campos directamente desde las anotaciones de las páginas
                # Este método es más confiable que usar el AcroForm del root
                try:
                    for page_num in range(len(writer.pages)):
                        page = writer.pages[page_num]
                        if "/Annots" in page:
                            annotations = page["/Annots"]
                            if annotations:
                                for annot_ref in annotations:
                                    try:
                                        annot = annot_ref.get_object()
                                        if "/T" in annot and "/FT" in annot:
                                            # Normalizar a str: pypdf puede devolver NameObject/TextStringObject
                                            field_name = annot["/T"]
                                            field_name_str = str(field_name).strip() if field_name else ""
                                            field_type = annot["/FT"]
                                            field_type_str = str(field_type).strip() if field_type else ""
                                            
                                            # Rellenar campos de texto (DD y OE siempre; resto solo si tiene contenido)
                                            if field_type_str == "/Tx":
                                                value = get_text_value(field_name_str)
                                                fn_lower = field_name_str.strip().lower()
                                                is_dd_or_oe = fn_lower == "dd" or fn_lower == "oe"
                                                if value is not None and (is_dd_or_oe or (value and str(value).strip())):
                                                    val_str = str(value).strip() if value else ""
                                                    annot[NameObject("/V")] = TextStringObject(val_str)
                                                    # Algunos visores usan el padre: actualizar también si tiene /Parent
                                                    if "/Parent" in annot and (is_dd_or_oe or (value and str(value).strip())):
                                                        try:
                                                            parent = annot["/Parent"].get_object()
                                                            parent[NameObject("/V")] = TextStringObject(val_str)
                                                        except Exception:
                                                            pass
                                            
                                            # Rellenar radio buttons (género F/M) y checkboxes (procedencia SP,E,P,O; EGS, DDD)
                                            if field_type_str == "/Btn":
                                                radio_val = get_radio_value(field_name_str)
                                                if radio_val is not None:
                                                    if radio_val == "/Yes":
                                                        annot[NameObject("/V")] = NameObject("/Yes")
                                                        annot[NameObject("/AS")] = NameObject("/Yes")
                                                    else:
                                                        annot[NameObject("/V")] = NameObject("/Off")
                                                        annot[NameObject("/AS")] = NameObject("/Off")
                                                else:
                                                    cb_val = get_checkbox_value(field_name_str)
                                                    if cb_val is not None:
                                                        if cb_val == "/Yes":
                                                            annot[NameObject("/V")] = NameObject("/Yes")
                                                            annot[NameObject("/AS")] = NameObject("/Yes")
                                                        else:
                                                            annot[NameObject("/V")] = NameObject("/Off")
                                                            annot[NameObject("/AS")] = NameObject("/Off")
                                    except Exception as e:
                                        continue
                    
                    # Escribir también en el árbol AcroForm /Fields (algunos visores solo leen /V del campo, no del widget)
                    try:
                        writer_root = writer._root_object
                        if writer_root and "/AcroForm" in writer_root:
                            acro_form = writer_root["/AcroForm"]
                            if "/Fields" in acro_form:
                                def set_text_in_fields(field_list):
                                    if not field_list:
                                        return
                                    for field_ref in field_list:
                                        try:
                                            field = field_ref.get_object()
                                            if "/Kids" in field and field["/Kids"]:
                                                set_text_in_fields(field["/Kids"])
                                            if "/T" in field and "/FT" in field:
                                                fn = str(field["/T"]).strip() if field["/T"] else ""
                                                ft = str(field["/FT"]).strip() if field["/FT"] else ""
                                                if ft == "/Tx":
                                                    val = get_text_value(fn)
                                                    fn_low = fn.strip().lower()
                                                    is_dd_oe = fn_low == "dd" or fn_low == "oe"
                                                    if val is not None and (is_dd_oe or (val and str(val).strip())):
                                                        field[NameObject("/V")] = TextStringObject(str(val).strip() if val else "")
                                        except Exception:
                                            continue
                                set_text_in_fields(acro_form["/Fields"])
                    except Exception:
                        pass
                except Exception as e:
                    
                    # Método alternativo: intentar desde el AcroForm del root
                    try:
                        writer_root = writer._root_object
                        if writer_root and "/AcroForm" in writer_root:
                            acro_form = writer_root["/AcroForm"]
                            if "/Fields" in acro_form:
                                fields = acro_form["/Fields"]
                                
                                def process_all_fields(field_list):
                                    if not field_list:
                                        return
                                    try:
                                        for field_ref in field_list:
                                            try:
                                                field = field_ref.get_object()
                                                if "/Kids" in field and field["/Kids"]:
                                                    process_all_fields(field["/Kids"])
                                                if "/T" in field:
                                                    field_name = field["/T"]
                                                    field_name_str = str(field_name).strip() if field_name else ""
                                                    value_t = get_text_value(field_name_str)
                                                    fn_alt = field_name_str.strip().lower()
                                                    is_dd_oe_alt = fn_alt == "dd" or fn_alt == "oe"
                                                    if value_t is not None and (is_dd_oe_alt or (value_t and str(value_t).strip())):
                                                        field[NameObject("/V")] = TextStringObject(str(value_t).strip() if value_t else "")
                                                    rv = get_radio_value(field_name_str)
                                                    if rv is not None:
                                                        field[NameObject("/V")] = NameObject("/Yes" if rv == "/Yes" else "/Off")
                                                        field[NameObject("/AS")] = NameObject("/Yes" if rv == "/Yes" else "/Off")
                                                    else:
                                                        cv = get_checkbox_value(field_name_str)
                                                        if cv is not None:
                                                            field[NameObject("/V")] = NameObject("/Yes" if cv == "/Yes" else "/Off")
                                                            field[NameObject("/AS")] = NameObject("/Yes" if cv == "/Yes" else "/Off")
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                process_all_fields(fields)
                    except Exception as e2:
                        pass
                
                # Manejar radio buttons directamente desde el AcroForm (si aún no se procesaron)
                if radio_fields:
                    try:
                        writer_root = writer._root_object
                        if writer_root and "/AcroForm" in writer_root:
                            acro_form = writer_root["/AcroForm"]
                            if "/Fields" in acro_form:
                                fields = acro_form["/Fields"]
                                
                                # Validar que fields no esté vacío
                                if not fields or len(fields) == 0:
                                    return
                                
                                # Función recursiva para procesar campos (incluyendo campos anidados)
                                def process_radio_fields(field_list):
                                    if not field_list:
                                        return
                                    if not isinstance(field_list, list):
                                        return
                                    try:
                                        for i, field_ref in enumerate(field_list):
                                            try:
                                                if field_ref is None:
                                                    continue
                                                
                                                field = field_ref.get_object()
                                                
                                                # Si el campo tiene subcampos (Kids), procesarlos recursivamente
                                                if "/Kids" in field and field["/Kids"]:
                                                    process_radio_fields(field["/Kids"])
                                                
                                                # Si el campo tiene nombre: radio (F/M) o checkbox (SP,E,P,O,EGS,DDD)
                                                if "/T" in field:
                                                    field_name = field["/T"]
                                                    field_name_str = (str(field_name).strip().lstrip("/") if field_name else "") or ""
                                                    rv = get_radio_value(field_name_str)
                                                    if rv is not None:
                                                        field[NameObject("/V")] = NameObject("/Yes" if rv == "/Yes" else "/Off")
                                                        field[NameObject("/AS")] = NameObject("/Yes" if rv == "/Yes" else "/Off")
                                                    else:
                                                        cv = get_checkbox_value(field_name_str)
                                                        if cv is not None:
                                                            field[NameObject("/V")] = NameObject("/Yes" if cv == "/Yes" else "/Off")
                                                            field[NameObject("/AS")] = NameObject("/Yes" if cv == "/Yes" else "/Off")
                                            except Exception as e:
                                                continue
                                    except Exception as e:
                                        pass
                                
                                # Procesar todos los campos
                                process_radio_fields(fields)
                    except Exception as e:
                        pass
                
                # Hacer los campos de solo lectura después de rellenarlos
                try:
                    # Acceder al AcroForm del writer
                    if hasattr(writer, '_root_object') and writer._root_object is not None:
                        writer_root = writer._root_object
                        if "/AcroForm" in writer_root:
                            acro_form = writer_root["/AcroForm"]
                            if "/Fields" in acro_form:
                                fields = acro_form["/Fields"]
                                
                                # Validar que fields no esté vacío y sea una lista
                                if fields and isinstance(fields, list):
                                    # Función recursiva para procesar campos (incluyendo campos anidados)
                                    def process_fields(field_list):
                                        if not field_list:
                                            return
                                        if not isinstance(field_list, list):
                                            return
                                        try:
                                            for i, field_ref in enumerate(field_list):
                                                try:
                                                    if field_ref is None:
                                                        continue
                                                    
                                                    field = field_ref.get_object()
                                                    
                                                    # Si el campo tiene subcampos (Kids), procesarlos recursivamente
                                                    if "/Kids" in field and field["/Kids"]:
                                                        process_fields(field["/Kids"])
                                                    
                                                    # Si el campo tiene nombre, hacerlo de solo lectura
                                                    if "/T" in field:
                                                        field_name = field["/T"]
                                                        field_name_str = str(field_name).strip() if field_name else ""
                                                        if field_name_str in form_data:
                                                            # Hacer el campo de solo lectura (bit 1 = ReadOnly)
                                                            if "/Ff" in field:
                                                                current_flags = int(field["/Ff"])
                                                                field[NameObject("/Ff")] = NumberObject(current_flags | 1)
                                                            else:
                                                                field[NameObject("/Ff")] = NumberObject(1)
                                                except Exception as e:
                                                    continue
                                        except Exception as e:
                                            pass
                                
                                # Procesar todos los campos
                                process_fields(fields)
                except Exception as e2:
                    pass
                    import traceback
                    traceback.print_exc()
                else:
                    pass
            
            # Guardar el PDF rellenado
            try:
                with open(output_file, "wb") as output_stream:
                    writer.write(output_stream)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {
                    "status": "error",
                    "message": f"Error guardando PDF: {str(e)}",
                    "filename": None,
                    "file_path": None
                }
            
            return {
                "status": "success",
                "message": "PDF generado exitosamente",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            return {
                "status": "error",
                "message": f"Error generando PDF: {str(e)}",
                "filename": None,
                "file_path": None
            }

    @staticmethod
    def generate_progress_status_pdf(
        document_id: int,
        progress_status_data: Dict[str, Any],
        db: Optional[Session] = None,
        template_path: Optional[str] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance (documento 18).
        Dependiendo del document_id:
        - Si hay template_path: Sustituye datos en el template PDF
        - Si no hay template_path o document_id específico: Crea el PDF desde cero
        
        Args:
            document_id: ID del documento (18 para estado de avance)
            progress_status_data: Diccionario con los datos del estado de avance
            db: Sesión de base de datos (opcional)
            template_path: Ruta del archivo PDF template (opcional)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        # El método generate_progress_status_pdf ya existe más abajo
        # Este código duplicado debe eliminarse
        pass

    @staticmethod
    def generate_progress_status_pdf(
        document_id: int,
        progress_status_data: Dict[str, Any],
        db: Optional[Session] = None,
        template_path: Optional[str] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance (documento 18).
        Dependiendo del document_id:
        - Si hay template_path: Sustituye datos en el template PDF
        - Si no hay template_path o document_id específico: Crea el PDF desde cero
        
        Args:
            document_id: ID del documento (18 para estado de avance)
            progress_status_data: Diccionario con los datos del estado de avance
            db: Sesión de base de datos (opcional)
            template_path: Ruta del archivo PDF template (opcional)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        # Este método debe delegar a _generate_pdf_from_template o _generate_pdf_from_scratch
        # según corresponda. El código duplicado de tag replacement fue eliminado.
        if template_path:
            return DocumentsClass._generate_pdf_from_template(
                template_path=template_path,
                document_data=progress_status_data,
                output_directory=output_directory
            )
        else:
            return DocumentsClass._generate_progress_status_from_scratch(
                progress_status_data=progress_status_data,
                db=db,
                output_directory=output_directory
            )

    @staticmethod
    def generate_progress_status_pdf(
        document_id: int,
        progress_status_data: Dict[str, Any],
        db: Optional[Session] = None,
        template_path: Optional[str] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance (documento 18).
        Dependiendo del document_id:
        - Si hay template_path: Sustituye datos en el template PDF
        - Si no hay template_path o document_id específico: Crea el PDF desde cero
        
        Args:
            document_id: ID del documento (18 para estado de avance)
            progress_status_data: Diccionario con los datos del estado de avance
            db: Sesión de base de datos (opcional)
            template_path: Ruta del archivo PDF template (opcional)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        # Este método debe delegar a _generate_pdf_from_template o _generate_pdf_from_scratch
        # según corresponda. El código duplicado de tag replacement fue eliminado.
        if template_path:
            return DocumentsClass._generate_pdf_from_template(
                template_path=template_path,
                document_data=progress_status_data,
                output_directory=output_directory
            )
        else:
            return DocumentsClass._generate_progress_status_from_scratch(
                progress_status_data=progress_status_data,
                db=db,
                output_directory=output_directory
            )

    @staticmethod
    def generate_progress_status_pdf(
        document_id: int,
        progress_status_data: Dict[str, Any],
        db: Optional[Session] = None,
        template_path: Optional[str] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance (documento 18).
        Dependiendo del document_id:
        - Si hay template_path: Sustituye datos en el template PDF
        - Si no hay template_path o document_id específico: Crea el PDF desde cero
        
        Args:
            document_id: ID del documento (determina el método de generación)
            progress_status_data: Diccionario con los datos del estado de avance
            db: Sesión de base de datos (opcional, para obtener datos relacionados)
            template_path: Ruta del archivo PDF template (opcional, si es None se crea desde cero)
            output_directory: Directorio donde se guardará el archivo generado
        
        Returns:
            dict: Diccionario con status, message, filename y file_path
        """
        try:
            # Si hay template_path, usar método de sustitución
            if template_path:
                return DocumentsClass._generate_progress_status_from_template(
                    template_path=template_path,
                    progress_status_data=progress_status_data,
                    output_directory=output_directory
                )
            else:
                # Si no hay template, crear desde cero usando ReportLab
                return DocumentsClass._generate_progress_status_from_scratch(
                    document_id=document_id,
                    progress_status_data=progress_status_data,
                    db=db,
                    output_directory=output_directory
                )
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF: {str(e)}",
                "filename": None,
                "file_path": None
            }
    
    @staticmethod
    def _generate_progress_status_from_template(
        template_path: str,
        progress_status_data: Dict[str, Any],
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance sustituyendo datos en un template PDF existente.
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
            student_name = progress_status_data.get("student_fullname", "estudiante").replace(" ", "_")
            unique_filename = f"estado_avance_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
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
                value = progress_status_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
            # Mapeo de etiquetas a valores
            tag_replacements = {
                "[STUDENT_FULLNAME]": get_value("student_fullname", ""),
                "[STUDENT_NAME]": get_value("student_name", ""),
                "[STUDENT_LASTNAME]": get_value("student_lastname", ""),
                "[PROGRESS_DATE]": format_date(get_value("progress_date", "")),
                "[PEDAGOGICAL_LANGUAGE]": get_value("pedagogical_language", ""),
                "[PEDAGOGICAL_MATHEMATICS]": get_value("pedagogical_mathematics", ""),
                "[PSYCHOPEDAGOGICAL]": get_value("psychopedagogical", ""),
                "[SPEECH_THERAPY]": get_value("speech_therapy", ""),
                "[PSYCHOLOGICAL]": get_value("psychological", ""),
                "[KINESIOLOGY]": get_value("kinesiology", ""),
                "[OCCUPATIONAL_THERAPY]": get_value("occupational_therapy", ""),
                "[DEAF_CO_EDUCATOR]": get_value("deaf_co_educator", ""),
                "[SYNTHESIS_COMMENTS]": get_value("synthesis_comments", ""),
                "[SUGGESTIONS_FAMILY]": get_value("suggestions_family", ""),
                "[SUGGESTIONS_ESTABLISHMENT]": get_value("suggestions_establishment", ""),
                "[GUARDIAN_NAME]": get_value("guardian_name", ""),
                "[GUARDIAN_LASTNAME]": get_value("guardian_lastname", ""),
                "[RESPONSIBLE_PROFESSIONALS]": get_value("responsible_professionals", ""),
            }
            
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
                            found = page.search_for(tag_variant, flags=fitz.TEXT_DEHYPHENATE)
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
                            # Convertir a Rect si es una tupla
                            if isinstance(rect, (list, tuple)) and len(rect) == 4:
                                rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])
                            
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
                            # Validar el rectángulo antes de aplicar redacción
                            if rect.x1 > rect.x0 and rect.y1 > rect.y0:
                                # Redactar el texto original (cubrir con blanco)
                                page.add_redact_annot(rect, fill=(1, 1, 1))
                                page.apply_redactions()
                                
                                # Insertar el nuevo texto
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
                "message": "PDF generado exitosamente desde template",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF desde template: {str(e)}",
                "filename": None,
                "file_path": None
            }
    
    @staticmethod
    def _generate_progress_status_from_scratch(
        document_id: int,
        progress_status_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de estado de avance desde cero usando ReportLab.
        """
        try:
            if not REPORTLAB_AVAILABLE:
                return {
                    "status": "error",
                    "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear nombre único para el archivo generado
            student_name = progress_status_data.get("student_fullname", "estudiante").replace(" ", "_")
            unique_filename = f"estado_avance_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Crear el documento PDF con márgenes iguales a ambos lados para centrar el contenido
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=A4,
                rightMargin=2.5*cm,  # Márgenes iguales a ambos lados
                leftMargin=2.5*cm,   # Márgenes iguales a ambos lados
                topMargin=3*cm,
                bottomMargin=2.5*cm
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Estilos personalizados para documento gubernamental (estilo formulario)
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                spaceAfter=25,
                spaceBefore=15,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            section_style = ParagraphStyle(
                'SectionStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#000000'),
                spaceAfter=12,
                spaceBefore=15,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT,
                backColor=colors.HexColor('#E8E8E8'),
                borderPadding=6
            )
            
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                spaceAfter=6,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                leading=12,
                spaceAfter=4
            )
            
            label_style = ParagraphStyle(
                'LabelStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                backColor=colors.HexColor('#F5F5F5'),
                borderPadding=4
            )
            
            # Función auxiliar para obtener valor
            def get_value(key: str, default: str = "") -> str:
                value = progress_status_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
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
            
            # Título principal
            elements.append(Paragraph("ESTADO DE AVANCE", title_style))
            elements.append(Spacer(1, 0.4*inch))
            
            # I. IDENTIFICACIÓN DEL ESTUDIANTE
            elements.append(Paragraph("I. IDENTIFICACIÓN DEL ESTUDIANTE", section_style))
            elements.append(Spacer(1, 0.2*inch))
            
            student_fullname = get_value("student_fullname", "")
            student_rut = get_value("student_rut", "")
            student_age = get_value("student_age", "")
            progress_date = format_date(get_value("progress_date", ""))
            school_name = get_value("school_name", "")
            course_name = get_value("course_name", "")
            nee_name = get_value("nee_name", "")
            guardian_name = get_value("guardian_name", "")
            guardian_lastname = get_value("guardian_lastname", "")
            guardian_relationship = get_value("guardian_relationship", "")
            guardian_fullname = f"{guardian_name} {guardian_lastname}".strip() if (guardian_name or guardian_lastname) else ""
            
            # Información del estudiante en formato vertical (etiqueta arriba, valor abajo)
            # Estructura: 2 columnas de ancho, cada campo tiene etiqueta en una fila y valor en otra
            identification_data = []
            spans = []  # Lista para almacenar los SPANs

            # Par 1: RUT y Nombre (lado a lado)
            # Fila 1: Etiquetas
            if student_rut or student_fullname:
                row1_labels = [
                    Paragraph("<b>RUT:</b>", label_style) if student_rut else "",
                    Paragraph("<b>Nombre:</b>", label_style) if student_fullname else ""
                ]
                identification_data.append(row1_labels)
                
                # Fila 2: Valores
                row1_values = [
                    Paragraph(student_rut, normal_style) if student_rut else "",
                    Paragraph(student_fullname, normal_style) if student_fullname else ""
                ]
                identification_data.append(row1_values)

            # Par 2: Edad y Fecha Estado Avance
            if student_age or progress_date:
                row2_labels = [
                    Paragraph("<b>Edad:</b>", label_style) if student_age else "",
                    Paragraph("<b>Fecha Estado Avance:</b>", label_style) if progress_date else ""
                ]
                identification_data.append(row2_labels)
                
                row2_values = [
                    Paragraph(student_age, normal_style) if student_age else "",
                    Paragraph(progress_date, normal_style) if progress_date else ""
                ]
                identification_data.append(row2_values)

            # Par 3: Educacional y Curso
            if school_name or course_name:
                row3_labels = [
                    Paragraph("<b>Educacional:</b>", label_style) if school_name else "",
                    Paragraph("<b>Curso:</b>", label_style) if course_name else ""
                ]
                identification_data.append(row3_labels)
                
                row3_values = [
                    Paragraph(school_name, normal_style) if school_name else "",
                    Paragraph(course_name, normal_style) if course_name else ""
                ]
                identification_data.append(row3_values)

            # NEE: Ocupa 2 filas y 2 columnas (todo el ancho)
            if nee_name:
                # Fila NEE-1: Etiqueta (ocupa 2 columnas)
                identification_data.append([
                    Paragraph("<b>Necesidad Educativa Especial (NEE):</b>", label_style),
                    ""  # Columna vacía que se unirá
                ])
                nee_label_row = len(identification_data) - 1
                spans.append(('SPAN', (0, nee_label_row), (1, nee_label_row)))
                
                # Fila NEE-2: Valor (ocupa 2 columnas)
                identification_data.append([
                    Paragraph(nee_name, normal_style),
                    ""  # Columna vacía que se unirá
                ])
                nee_value_row = len(identification_data) - 1
                spans.append(('SPAN', (0, nee_value_row), (1, nee_value_row)))

            # Par 4: Relación con Estudiante y Apoderado/Guardián
            if guardian_relationship or guardian_fullname:
                row4_labels = [
                    Paragraph("<b>Relación con Estudiante:</b>", label_style) if guardian_relationship else "",
                    Paragraph("<b>Apoderado/Guardián:</b>", label_style) if guardian_fullname else ""
                ]
                identification_data.append(row4_labels)
                
                row4_values = [
                    Paragraph(guardian_relationship, normal_style) if guardian_relationship else "",
                    Paragraph(guardian_fullname, normal_style) if guardian_fullname else ""
                ]
                identification_data.append(row4_values)
            
            # Crear tabla con formato vertical (2 columnas de ancho)
            if identification_data:
                identification_table = Table(identification_data, colWidths=[7.5*cm, 7.5*cm])
                # Estilos base
                table_style = [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),  # Bordes sutiles
                ]
                # Agregar estilos de unión de celdas (solo para NEE - horizontal)
                table_style.extend(spans)
                identification_table.setStyle(TableStyle(table_style))
                elements.append(identification_table)
            
            
            elements.append(Spacer(1, 0.3*inch))
            
            # II. PROFESIONALES RESPONSABLES
            responsible_professionals = get_value("responsible_professionals_names", get_value("responsible_professionals", ""))
            if responsible_professionals:
                elements.append(Paragraph("II. PROFESIONALES RESPONSABLES", section_style))
                elements.append(Spacer(1, 0.15*inch))
                elements.append(Paragraph(responsible_professionals, normal_style))
                elements.append(Spacer(1, 0.3*inch))
            
            # III. ESTADO DE AVANCE POR ÁREA
            elements.append(Paragraph("III. ESTADO DE AVANCE POR ÁREA", section_style))
            elements.append(Spacer(1, 0.2*inch))
            
            areas = [
                ("Área Pedagógica - Lenguaje", get_value("pedagogical_language", "")),
                ("Área Pedagógica - Matemática", get_value("pedagogical_mathematics", "")),
                ("Área Psicopedagógica", get_value("psychopedagogical", "")),
                ("Área Fonoaudiológica", get_value("speech_therapy", "")),
                ("Área Psicológica", get_value("psychological", "")),
                ("Área Kinesiológica", get_value("kinesiology", "")),
                ("Área Terapia Ocupacional", get_value("occupational_therapy", "")),
                ("Área Co-educador Sordo/a", get_value("deaf_co_educator", ""))
            ]
            
            areas_with_content = [(name, content) for name, content in areas if content]
            
            if areas_with_content:
                for idx, (area_name, area_content) in enumerate(areas_with_content):
                    elements.append(Paragraph(f"<b>{area_name}</b>", subtitle_style))
                    elements.append(Paragraph(area_content, normal_style))
                    if idx < len(areas_with_content) - 1:
                        elements.append(Spacer(1, 0.2*inch))
            else:
                elements.append(Paragraph("No se registra información en esta sección.", normal_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # IV. SÍNTESIS, COMENTARIOS U OBSERVACIONES
            synthesis = get_value("synthesis_comments", "")
            if synthesis:
                elements.append(Paragraph("IV. SÍNTESIS, COMENTARIOS U OBSERVACIONES", section_style))
                elements.append(Spacer(1, 0.15*inch))
                elements.append(Paragraph(synthesis, normal_style))
                elements.append(Spacer(1, 0.3*inch))
            
            # V. SUGERENCIAS
            suggestions_family = get_value("suggestions_family", "")
            suggestions_establishment = get_value("suggestions_establishment", "")
            
            if suggestions_family or suggestions_establishment:
                elements.append(Paragraph("V. SUGERENCIAS", section_style))
                elements.append(Spacer(1, 0.15*inch))
                
                if suggestions_family:
                    elements.append(Paragraph("<b>a) Sugerencias a la familia:</b>", subtitle_style))
                    elements.append(Paragraph(suggestions_family, normal_style))
                    elements.append(Spacer(1, 0.2*inch))
                
                if suggestions_establishment:
                    elements.append(Paragraph("<b>b) Sugerencias al establecimiento educacional:</b>", subtitle_style))
                    elements.append(Paragraph(suggestions_establishment, normal_style))
                    elements.append(Spacer(1, 0.2*inch))
            
            # Construir PDF (sin espacio final excesivo que cause página en blanco)
            doc.build(elements)
            
            return {
                "status": "success",
                "message": "PDF generado exitosamente desde cero",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except ImportError:
            return {
                "status": "error",
                "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                "filename": None,
                "file_path": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF desde cero: {str(e)}",
                "filename": None,
                "file_path": None
            }

    @staticmethod
    def _generate_individual_support_plan_from_scratch(
        document_id: int,
        isp_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de Plan de Apoyo Individual (PAI) desde cero usando ReportLab.
        """
        try:
            if not REPORTLAB_AVAILABLE:
                return {
                    "status": "error",
                    "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                    "filename": None,
                    "file_path": None
                }
            
            # Crear nombre único para el archivo generado
            student_name = isp_data.get("student_full_name", "estudiante").replace(" ", "_")
            unique_filename = f"plan_apoyo_individual_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            
            # Asegurar que el directorio de salida existe
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Crear el documento PDF con márgenes iguales a ambos lados para centrar el contenido
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=A4,
                rightMargin=2.5*cm,
                leftMargin=2.5*cm,
                topMargin=3*cm,
                bottomMargin=2.5*cm
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Estilos personalizados para documento gubernamental
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                spaceAfter=25,
                spaceBefore=15,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            section_style = ParagraphStyle(
                'SectionStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#000000'),
                spaceAfter=12,
                spaceBefore=15,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT,
                backColor=colors.HexColor('#E8E8E8'),
                borderPadding=6
            )
            
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                spaceAfter=6,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                leading=12,
                spaceAfter=4
            )
            
            label_style = ParagraphStyle(
                'LabelStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                backColor=colors.HexColor('#F5F5F5'),
                borderPadding=4
            )
            
            # Función auxiliar para obtener valor
            def get_value(key: str, default: str = "") -> str:
                value = isp_data.get(key)
                if value is None:
                    return default
                return str(value) if value else default
            
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
            
            # Título principal
            elements.append(Paragraph("PLAN DE APOYO INDIVIDUAL (PAI)", title_style))
            elements.append(Spacer(1, 0.4*inch))
            
            # I. IDENTIFICACIÓN DEL ESTUDIANTE
            elements.append(Paragraph("I. IDENTIFICACIÓN DEL ESTUDIANTE", section_style))
            elements.append(Spacer(1, 0.2*inch))
            
            student_fullname = get_value("student_full_name", "")
            student_rut = get_value("student_identification_number", "")
            student_age = get_value("student_age", "")
            student_born_date = format_date(get_value("student_born_date", ""))
            elaboration_date = format_date(get_value("elaboration_date", ""))
            school_name = get_value("student_school", "")
            course_name = get_value("course_name", "")
            nee_name = get_value("nee_name", "")
            
            # Información del estudiante en formato vertical (2 columnas)
            identification_data = []
            spans = []
            
            # Par 1: RUT y Nombre
            if student_rut or student_fullname:
                row1_labels = [
                    Paragraph("<b>RUT:</b>", label_style) if student_rut else "",
                    Paragraph("<b>Nombre:</b>", label_style) if student_fullname else ""
                ]
                identification_data.append(row1_labels)
                
                row1_values = [
                    Paragraph(student_rut, normal_style) if student_rut else "",
                    Paragraph(student_fullname, normal_style) if student_fullname else ""
                ]
                identification_data.append(row1_values)
            
            # Par 2: Fecha de Nacimiento y Edad
            if student_born_date or student_age:
                row2_labels = [
                    Paragraph("<b>Fecha de Nacimiento:</b>", label_style) if student_born_date else "",
                    Paragraph("<b>Edad:</b>", label_style) if student_age else ""
                ]
                identification_data.append(row2_labels)
                
                row2_values = [
                    Paragraph(student_born_date, normal_style) if student_born_date else "",
                    Paragraph(student_age, normal_style) if student_age else ""
                ]
                identification_data.append(row2_values)
            
            # Par 3: Establecimiento Educacional y Curso
            if school_name or course_name:
                row3_labels = [
                    Paragraph("<b>Establecimiento Educacional:</b>", label_style) if school_name else "",
                    Paragraph("<b>Curso:</b>", label_style) if course_name else ""
                ]
                identification_data.append(row3_labels)
                
                row3_values = [
                    Paragraph(school_name, normal_style) if school_name else "",
                    Paragraph(course_name, normal_style) if course_name else ""
                ]
                identification_data.append(row3_values)
            
            # NEE: Ocupa 2 columnas
            if nee_name:
                identification_data.append([
                    Paragraph("<b>Necesidad Educativa Especial (NEE):</b>", label_style),
                    ""
                ])
                nee_label_row = len(identification_data) - 1
                spans.append(('SPAN', (0, nee_label_row), (1, nee_label_row)))
                
                identification_data.append([
                    Paragraph(nee_name, normal_style),
                    ""
                ])
                nee_value_row = len(identification_data) - 1
                spans.append(('SPAN', (0, nee_value_row), (1, nee_value_row)))
            
            # Fecha de Elaboración
            if elaboration_date:
                row4_labels = [
                    Paragraph("<b>Fecha de Elaboración:</b>", label_style),
                    ""
                ]
                identification_data.append(row4_labels)
                row4_label_row = len(identification_data) - 1
                spans.append(('SPAN', (0, row4_label_row), (1, row4_label_row)))
                
                row4_values = [
                    Paragraph(elaboration_date, normal_style),
                    ""
                ]
                identification_data.append(row4_values)
                row4_value_row = len(identification_data) - 1
                spans.append(('SPAN', (0, row4_value_row), (1, row4_value_row)))
            
            # Crear tabla de identificación
            if identification_data:
                identification_table = Table(identification_data, colWidths=[7.5*cm, 7.5*cm])
                table_style = [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ]
                table_style.extend(spans)
                identification_table.setStyle(TableStyle(table_style))
                elements.append(identification_table)
            
            elements.append(Spacer(1, 0.3*inch))
            
            # II. PROFESIONALES ASOCIADOS
            professionals = isp_data.get("professionals", [])
            if professionals:
                elements.append(Paragraph("II. PROFESIONALES ASOCIADOS", section_style))
                elements.append(Spacer(1, 0.2*inch))
                
                # Crear tabla con profesionales, 1 columna, misma estructura que identificación
                professionals_data = []
                professionals_spans = []
                
                for idx, prof in enumerate(professionals):
                    prof_name = prof.get("professional_name", "")
                    prof_career = prof.get("career_type_name", "")
                    prof_reg = prof.get("registration_number", "")
                    prof_days = prof.get("days_hours", "")
                    prof_from = format_date(prof.get("from_date", ""))
                    prof_to = format_date(prof.get("to_date", ""))
                    prof_period = f"{prof_from} - {prof_to}" if (prof_from and prof_to) else (prof_from or prof_to or "")
                    prof_modality = prof.get("support_modality", "")
                    
                    # Nombre del Profesional (ocupa 1 columna completa)
                    if prof_name:
                        professionals_data.append([
                            Paragraph(f"<b>Profesional {idx + 1}:</b>", label_style),
                            ""
                        ])
                        prof_name_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, prof_name_label_row), (1, prof_name_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_name, normal_style),
                            ""
                        ])
                        prof_name_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, prof_name_value_row), (1, prof_name_value_row)))
                    
                    # Especialidad (ocupa 2 columnas - ancho completo)
                    if prof_career:
                        professionals_data.append([
                            Paragraph("<b>Especialidad:</b>", label_style),
                            ""
                        ])
                        career_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, career_label_row), (1, career_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_career, normal_style),
                            ""
                        ])
                        career_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, career_value_row), (1, career_value_row)))
                    
                    # N° Registro (ocupa 2 columnas - ancho completo)
                    if prof_reg:
                        professionals_data.append([
                            Paragraph("<b>N° Registro:</b>", label_style),
                            ""
                        ])
                        reg_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, reg_label_row), (1, reg_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_reg, normal_style),
                            ""
                        ])
                        reg_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, reg_value_row), (1, reg_value_row)))
                    
                    # Días y Horarios (ocupa 2 columnas - ancho completo)
                    if prof_days:
                        professionals_data.append([
                            Paragraph("<b>Días y Horarios:</b>", label_style),
                            ""
                        ])
                        days_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, days_label_row), (1, days_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_days, normal_style),
                            ""
                        ])
                        days_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, days_value_row), (1, days_value_row)))
                    
                    # Período (ocupa 2 columnas - ancho completo)
                    if prof_period:
                        professionals_data.append([
                            Paragraph("<b>Período:</b>", label_style),
                            ""
                        ])
                        period_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, period_label_row), (1, period_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_period, normal_style),
                            ""
                        ])
                        period_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, period_value_row), (1, period_value_row)))
                    
                    # Modalidad (ocupa 2 columnas)
                    if prof_modality:
                        professionals_data.append([
                            Paragraph("<b>Modalidad de Apoyo:</b>", label_style),
                            ""
                        ])
                        modality_label_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, modality_label_row), (1, modality_label_row)))
                        
                        professionals_data.append([
                            Paragraph(prof_modality, normal_style),
                            ""
                        ])
                        modality_value_row = len(professionals_data) - 1
                        professionals_spans.append(('SPAN', (0, modality_value_row), (1, modality_value_row)))
                    
                    # Agregar espacio entre profesionales
                    if idx < len(professionals) - 1:
                        professionals_data.append(["", ""])
                
                # Crear tabla con 2 columnas (pero cada profesional usa ambas cuando es necesario)
                if professionals_data:
                    professionals_table = Table(professionals_data, colWidths=[7.5*cm, 7.5*cm])
                    professionals_table_style = [
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                    ]
                    professionals_table_style.extend(professionals_spans)
                    professionals_table.setStyle(TableStyle(professionals_table_style))
                    elements.append(professionals_table)
                
                elements.append(Spacer(1, 0.3*inch))
            
            # III. FORTALEZAS DEL ESTUDIANTE
            social_affective = get_value("social_affective_strengths", "")
            cognitive = get_value("cognitive_strengths", "")
            curricular = get_value("curricular_strengths", "")
            family = get_value("family_strengths", "")
            
            if social_affective or cognitive or curricular or family:
                elements.append(Paragraph("III. FORTALEZAS DEL/LA ESTUDIANTE", section_style))
                elements.append(Spacer(1, 0.2*inch))
                
                if social_affective:
                    elements.append(Paragraph("<b>a) Fortalezas Socioafectivas:</b>", subtitle_style))
                    elements.append(Paragraph(social_affective, normal_style))
                    elements.append(Spacer(1, 0.15*inch))
                
                if cognitive:
                    elements.append(Paragraph("<b>b) Fortalezas Cognitivas:</b>", subtitle_style))
                    elements.append(Paragraph(cognitive, normal_style))
                    elements.append(Spacer(1, 0.15*inch))
                
                if curricular:
                    elements.append(Paragraph("<b>c) Fortalezas Curriculares:</b>", subtitle_style))
                    elements.append(Paragraph(curricular, normal_style))
                    elements.append(Spacer(1, 0.15*inch))
                
                if family:
                    elements.append(Paragraph("<b>d) Fortalezas Familiares:</b>", subtitle_style))
                    elements.append(Paragraph(family, normal_style))
                    elements.append(Spacer(1, 0.15*inch))
                
                elements.append(Spacer(1, 0.3*inch))
            
            # IV. PROPUESTA DE INTERVENCIÓN
            elements.append(Paragraph("IV. PROPUESTA DE INTERVENCIÓN", section_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Áreas de intervención
            intervention_areas = [
                ("Educación Diferencial", get_value("intervention_ed_diferencial", ""), get_value("intervention_ed_diferencial_strategies", "")),
                ("Psicopedagogía", get_value("intervention_psicopedagogia", ""), get_value("intervention_psicopedagogia_strategies", "")),
                ("Fonoaudiología", get_value("intervention_fonoaudiologia", ""), get_value("intervention_fonoaudiologia_strategies", "")),
                ("Psicología", get_value("intervention_psicologia", ""), get_value("intervention_psicologia_strategies", "")),
                ("Terapia Ocupacional", get_value("intervention_terapia_ocupacional", ""), get_value("intervention_terapia_ocupacional_strategies", "")),
                ("Kinesiología", get_value("intervention_kinesiologia", ""), get_value("intervention_kinesiologia_strategies", "")),
                ("Co-educador Sordo", get_value("intervention_coeducador_sordo", ""), get_value("intervention_coeducador_sordo_strategies", "")),
                ("Intérprete Lengua de Señas", get_value("intervention_int_lengua_senas", ""), get_value("intervention_int_lengua_senas_strategies", ""))
            ]
            
            areas_with_content = [(name, objectives, strategies) for name, objectives, strategies in intervention_areas if objectives or strategies]
            
            if areas_with_content:
                for idx, (area_name, objectives, strategies) in enumerate(areas_with_content):
                    elements.append(Paragraph(f"<b>{area_name}</b>", subtitle_style))
                    if objectives:
                        elements.append(Paragraph("<b>Objetivos:</b>", subtitle_style))
                        elements.append(Paragraph(objectives, normal_style))
                        elements.append(Spacer(1, 0.1*inch))
                    if strategies:
                        elements.append(Paragraph("<b>Estrategias:</b>", subtitle_style))
                        elements.append(Paragraph(strategies, normal_style))
                    if idx < len(areas_with_content) - 1:
                        elements.append(Spacer(1, 0.2*inch))
            else:
                elements.append(Paragraph("No se registra información en esta sección.", normal_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # V. SEGUIMIENTO DEL PAI
            follow_up = get_value("follow_up_pai", "")
            if follow_up:
                elements.append(Paragraph("IV. SEGUIMIENTO DEL PAI", section_style))
                elements.append(Spacer(1, 0.15*inch))
                elements.append(Paragraph(follow_up, normal_style))
            
            # Construir PDF
            doc.build(elements)
            
            return {
                "status": "success",
                "message": "PDF generado exitosamente desde cero",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
            
        except ImportError:
            return {
                "status": "error",
                "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                "filename": None,
                "file_path": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando PDF desde cero: {str(e)}",
                "filename": None,
                "file_path": None
            }

    @staticmethod
    def _escape_html_for_paragraph(s: Optional[str]) -> str:
        """Escapa caracteres HTML para usar en ReportLab Paragraph."""
        if s is None or not isinstance(s, str):
            return ""
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _generate_fonoaudiological_report_from_scratch(
        document_id: int,
        report_data: Dict[str, Any],
        db: Optional[Session] = None,
        output_directory: str = "files/system/students"
    ) -> Dict[str, Any]:
        """
        Genera un PDF de Informe Fonoaudiológico (Documento 8) desde cero usando ReportLab.
        Mismo estilo que PAI y Estado de Avance.
        """
        try:
            if not REPORTLAB_AVAILABLE:
                return {
                    "status": "error",
                    "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                    "filename": None,
                    "file_path": None
                }

            student_name = report_data.get("student_full_name", "estudiante").replace(" ", "_")
            unique_filename = f"informe_fonoaudologico_{student_name}_{uuid.uuid4().hex[:8]}.pdf"
            output_file = Path(output_directory) / unique_filename
            output_file.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=A4,
                rightMargin=2.5*cm,
                leftMargin=2.5*cm,
                topMargin=3*cm,
                bottomMargin=2.5*cm
            )
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                spaceAfter=25,
                spaceBefore=15,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            section_style = ParagraphStyle(
                'SectionStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#000000'),
                spaceAfter=12,
                spaceBefore=15,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT,
                backColor=colors.HexColor('#E8E8E8'),
                borderPadding=6
            )
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                spaceAfter=6,
                spaceBefore=10,
                fontName='Helvetica-Bold'
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                leading=12,
                spaceAfter=4
            )
            label_style = ParagraphStyle(
                'LabelStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#000000'),
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                backColor=colors.HexColor('#F5F5F5'),
                borderPadding=4
            )

            def get_value(key: str, default: str = "") -> str:
                v = report_data.get(key)
                if v is None:
                    return default
                return str(v).strip() if v else default

            def format_date(date_val) -> str:
                if not date_val:
                    return ""
                try:
                    if isinstance(date_val, str):
                        dt = datetime.strptime(date_val, "%Y-%m-%d").date()
                        return dt.strftime("%d-%m-%Y")
                    return ""
                except Exception:
                    return str(date_val) if date_val else ""

            def add_section(title: str):
                elements.append(Paragraph(title, section_style))
                elements.append(Spacer(1, 0.2*inch))

            def add_text_block(label: str, text: str):
                if not text:
                    return
                elements.append(Paragraph(f"<b>{label}</b>", subtitle_style))
                elements.append(Paragraph(DocumentsClass._escape_html_for_paragraph(text), normal_style))
                elements.append(Spacer(1, 0.15*inch))

            # Título
            elements.append(Paragraph("Informe Fonoaudiológico (informal)", title_style))
            elements.append(Spacer(1, 0.4*inch))

            # I. IDENTIFICACIÓN DEL/LA ESTUDIANTE
            # Orden: Nombre, RUT, Fecha nacimiento, Establecimiento ID, Curso, Profesional/es responsable/s, Fecha Informe, Tipo
            add_section("I. Identificación del/la estudiante")
            student_fullname = get_value("student_full_name", "")
            student_rut = get_value("student_identification_number", "")
            student_born = format_date(get_value("student_born_date", ""))
            establishment = get_value("establishment_id", "")
            course_name = get_value("course_name", "")
            prof_names = get_value("responsible_professionals_names", "")
            report_date = format_date(get_value("report_date", ""))
            type_id = report_data.get("type_id")
            type_label = "Ingreso" if type_id == 1 else ("Reevaluación" if type_id == 2 else get_value("type_label", ""))

            id_data = []
            id_spans = []

            def _add_row(lbl: str, val: str):
                if not val:
                    return
                r = len(id_data)
                id_data.append([Paragraph(f"<b>{lbl}</b>", label_style), ""])
                id_spans.append(('SPAN', (0, r), (1, r)))
                id_data.append([Paragraph(DocumentsClass._escape_html_for_paragraph(val), normal_style), ""])
                id_spans.append(('SPAN', (0, r + 1), (1, r + 1)))

            _add_row("Nombre", student_fullname)
            _add_row("RUT", student_rut)
            _add_row("Fecha de nacimiento", student_born)
            _add_row("Establecimiento ID", establishment)
            _add_row("Curso", course_name)
            _add_row("Profesional/es responsable/s", prof_names)
            _add_row("Fecha de Informe", report_date)
            _add_row("Tipo", type_label)

            if id_data:
                tbl = Table(id_data, colWidths=[7.5*cm, 7.5*cm])
                tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ] + id_spans))
                elements.append(tbl)
            elements.append(Spacer(1, 0.3*inch))

            # II. DESARROLLO DEL INFORME
            add_section("II. Desarrollo del Informe")
            add_text_block("Motivo de la evaluación", get_value("reason_evaluation", ""))
            add_text_block("Instrumentos de evaluación utilizado", get_value("evaluation_instruments", ""))
            add_text_block("Antecedentes relevantes", get_value("relevant_background", ""))
            add_text_block("Conductas observadas durante la evaluación", get_value("behaviors_observed", ""))

            # III. ANÁLISIS DE ÁREAS
            add_section("III. Análisis de áreas")
            add_text_block("Estructuras y funciones orofaciales y auditivas", get_value("orofacial_auditory", ""))
            add_text_block("Nivel fonológico", get_value("phonological_level", ""))
            add_text_block("Nivel morfosintáctico", get_value("morphosyntactic_level", ""))
            add_text_block("Nivel semántico", get_value("semantic_level", ""))
            add_text_block("Nivel pragmático", get_value("pragmatic_level", ""))
            add_text_block("Observaciones adicionales", get_value("additional_observations", ""))

            # IV. SÍNTESIS DIAGNÓSTICA Y/O CONCLUSIONES
            add_section("IV. Síntesis diagnóstica y/o conclusiones")
            diag = get_value("diagnostic_synthesis", "")
            if diag:
                add_text_block("Síntesis diagnóstica y/o conclusiones", diag)

            # V. SUGERENCIAS
            sug_fam = get_value("suggestions_family", "")
            sug_est = get_value("suggestions_establishment", "")
            if sug_fam or sug_est:
                add_section("V. Sugerencias")
                if sug_fam:
                    add_text_block("Sugerencias a la familia", sug_fam)
                if sug_est:
                    add_text_block("Sugerencias al establecimiento", sug_est)

            doc.build(elements)
            return {
                "status": "success",
                "message": "PDF generado exitosamente",
                "filename": unique_filename,
                "file_path": str(output_file)
            }
        except ImportError:
            return {
                "status": "error",
                "message": "ReportLab no está instalado. Instala con: pip install reportlab",
                "filename": None,
                "file_path": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generando informe fonoaudiológico: {str(e)}",
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
                                if not WIN32_AVAILABLE:
                                    raise ImportError("win32com no disponible")
                                
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
                if not DOCX_EXTRA_AVAILABLE:
                    raise ImportError("docx.oxml no disponible")
                
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
                    os.unlink(converted_path)
                except:
                    pass
            
            # Convertir el Word a PDF usando LibreOffice
            
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
                        if not WIN32_AVAILABLE:
                            raise ImportError("win32com no disponible")
                        
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
