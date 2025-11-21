import uuid
from pathlib import Path
import fitz  # PyMuPDF

class DocumentsClass:
    def __init__(self):
        pass

    def parent_authorization(self, original_file_path: str, student_name: str, output_directory: str = "files/original_student_files"):
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

