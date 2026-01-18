from fastapi import APIRouter, Depends, status, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, KnowledgeDocumentList
from app.backend.db.database import get_db
from app.backend.db.models import AIConversationModel, KnowledgeDocumentModel

# Inicializar ChromaDB
try:
    import chromadb
    CHROMADB_AVAILABLE = True
    # Configurar ChromaDB (persistente)
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = chroma_client.get_or_create_collection(
        name="documentos_pie",
        metadata={"description": "Base de conocimiento PIE360"}
    )
except ImportError:
    CHROMADB_AVAILABLE = False
    chroma_client = None
    chroma_collection = None

artificial_intelligence = APIRouter(
    prefix="/artificial_intelligence",
    tags=["Artificial Intelligence"]
)

@artificial_intelligence.get("/analyze/{escrito}")
async def analyze_text(
    escrito: str,
    instruction: Optional[str] = None,
    use_rag: Optional[bool] = True,  # Usar RAG (base de conocimiento) si está disponible
    n_results: Optional[int] = 3,  # Número de documentos a buscar en RAG
    db: Session = Depends(get_db)
):
    """
    Analiza un texto usando inteligencia artificial y devuelve una respuesta.
    Usa RAG (base de conocimiento) cuando está disponible para respuestas más precisas.
    
    Parámetros:
    - escrito: Texto a analizar (en la URL, codificado)
    - instruction: Instrucción opcional para el análisis (query parameter)
    - use_rag: Si usar RAG para buscar en la base de conocimiento (default: true)
    - n_results: Número de documentos a buscar en la base de conocimiento (default: 3)
    
    Nota: La nueva Responses API no acepta max_tokens como parámetro.
    """
    try:
        # Verificar si OpenAI está disponible
        if not OPENAI_AVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "La librería openai no está instalada. Instala con: pip install openai",
                    "data": None
                }
            )
        
        # Obtener API key de OpenAI desde variables de entorno
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "API key de OpenAI no configurada. Configura OPENAI_API_KEY en las variables de entorno.",
                    "data": None
                }
            )
        
        # Configurar cliente de OpenAI
        client = openai.OpenAI(api_key=api_key)
        
        # Construir contexto inicial
        context_instruction = instruction or "Analiza el texto proporcionado y proporciona una respuesta útil."
        documentos_usados = []
        
        # BUSCAR EN LA BASE DE CONOCIMIENTO (RAG) si está habilitado
        if use_rag and CHROMADB_AVAILABLE:
            try:
                # Buscar documentos relevantes en ChromaDB
                results = chroma_collection.query(
                    query_texts=[escrito],
                    n_results=n_results or 3
                )
                
                # Construir contexto RAG con los documentos encontrados
                if results['documents'] and len(results['documents'][0]) > 0:
                    contexto_rag = "\n\n📚 Base de conocimiento (documentos relevantes):\n\n"
                    for i, doc in enumerate(results['documents'][0]):
                        metadata = results.get('metadatas', [[]])[0][i] if results.get('metadatas') else {}
                        titulo = metadata.get('title', f'Documento {i+1}')
                        contexto_rag += f"{i+1}. {titulo}:\n{doc}\n\n"
                        documentos_usados.append({
                            "title": titulo,
                            "content": doc[:200] + "..." if len(doc) > 200 else doc
                        })
                    
                    context_instruction = f"""{context_instruction}

{contexto_rag}

Instrucción: Usa la base de conocimiento proporcionada arriba como referencia principal. Si la información en la base de conocimiento responde la pregunta, úsala. Si no, proporciona una respuesta útil basada en tu conocimiento general."""
            except Exception as rag_error:
                # Si falla RAG, continuar sin él
                print(f"Error en búsqueda RAG: {rag_error}")
        
        # Preparar parámetros para la nueva Responses API
        api_params = {
            "model": "gpt-4o-mini",
            "input": escrito,
            "instructions": context_instruction
        }
        
        # Realizar la petición a OpenAI usando la nueva Responses API
        response = client.responses.create(**api_params)
        
        # Extraer la respuesta usando la propiedad de conveniencia output_text
        ai_response = response.output_text
        
        # Obtener el ID de la respuesta si está disponible
        response_id = None
        if hasattr(response, 'id'):
            response_id = response.id
        
        # Guardar la conversación en la base de datos
        user_id = 1  # Usuario por defecto
        
        # Generar un session_id único para esta conversación
        session_id = str(uuid.uuid4())
        
        try:
            new_conversation = AIConversationModel(
                user_id=user_id,
                session_id=session_id,
                previous_response_id=None,  # No usamos historial
                input_text=escrito,
                instruction=instruction,
                response_text=ai_response,
                model="gpt-4o-mini",
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
        except Exception as db_error:
            # Si falla guardar en BD, continuar de todos modos
            db.rollback()
            print(f"Error guardando conversación en BD: {db_error}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Análisis completado exitosamente",
                "data": {
                    "original_text": escrito,
                    "instruction": instruction,
                    "response": ai_response,
                    "model": "gpt-4o-mini",
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None,
                    "rag_used": len(documentos_usados) > 0,  # Si se usó RAG
                    "documentos_usados": documentos_usados if documentos_usados else None,  # Documentos encontrados
                    "conversation_id": new_conversation.id if 'new_conversation' in locals() else None  # ID de la conversación guardada
                }
            }
        )
        
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        # Log del error completo para debugging
        print(f"Error en analyze_text: {error_type}: {error_message}")
        print(f"Traceback: {error_traceback}")
        
        # Manejar errores específicos de OpenAI
        if OPENAI_AVAILABLE:
            # Verificar si es un error de API de OpenAI
            if hasattr(openai, 'APIError') and isinstance(e, openai.APIError):
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": f"Error en la API de OpenAI: {error_message}",
                        "data": None
                    }
                )
            # Verificar otros tipos de errores de OpenAI
            elif hasattr(openai, 'error') and isinstance(e, openai.error.OpenAIError):
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": 500,
                        "message": f"Error en la API de OpenAI: {error_message}",
                        "data": None
                    }
                )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error procesando la solicitud ({error_type}): {error_message}",
                "data": {
                    "error_type": error_type,
                    "error_details": error_message
                }
            }
        )

@artificial_intelligence.post("/upload")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Sube un documento PDF y lo agrega automáticamente a la base de conocimiento RAG.
    Extrae el texto del PDF y lo guarda en ChromaDB y MySQL.
    
    Parámetros:
    - file: Archivo PDF a subir
    - title: Título del documento (opcional, si no se proporciona se usa el nombre del archivo)
    - document_type: Tipo de documento (opcional, ej: "normativa", "manual", "procedimiento")
    - category: Categoría (opcional, ej: "PIE", "NEE", "evaluación")
    - source: Fuente del documento (opcional)
    """
    try:
        if not CHROMADB_AVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "ChromaDB no está instalado. Instala con: pip install chromadb",
                    "data": None
                }
            )
        
        # Verificar que sea un PDF
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": "Solo se aceptan archivos PDF",
                    "data": None
                }
            )
        
        # Leer el contenido del archivo
        file_content = await file.read()
        
        # Extraer texto del PDF usando PyMuPDF
        try:
            import fitz  # PyMuPDF
            import io
            
            # Abrir el PDF desde bytes
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            # Extraer texto de todas las páginas
            text_content = []
            for page_num, page in enumerate(pdf_document):
                text = page.get_text()
                text_content.append(text)
            
            pdf_document.close()
            full_text = "\n".join(text_content)
            
            if not full_text.strip():
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status": 400,
                        "message": "El PDF no contiene texto extraíble. Asegúrate de que el PDF tenga texto seleccionable.",
                        "data": None
                    }
                )
            
        except ImportError:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "PyMuPDF (fitz) no está instalado. Instala con: pip install pymupdf",
                    "data": None
                }
            )
        except Exception as pdf_error:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": f"Error al leer el PDF: {str(pdf_error)}",
                    "data": None
                }
            )
        
        # Si no se proporcionaron metadatos, extraerlos usando RAG/OpenAI del contenido del documento
        if not title or not document_type or not category:
            try:
                # Preparar prompt para extraer metadatos del contenido
                extraction_prompt = f"""Analiza el siguiente documento y extrae información relevante. Responde SOLO en formato JSON con las siguientes claves:
{{
    "title": "Título descriptivo del documento extraído del contenido (máximo 100 caracteres)",
    "document_type": "Tipo de documento (ej: normativa, manual, procedimiento, guía, ley, decreto)",
    "category": "Categoría temática (ej: PIE, NEE, evaluación, inclusión, educación)",
    "source": "Fuente u origen del documento (ej: LeyChile, Ministerio de Educación)"
}}

Contenido del documento:
{full_text[:5000]}

Responde SOLO con el JSON, sin texto adicional."""

                # Usar OpenAI para extraer metadatos
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key and OPENAI_AVAILABLE:
                    client = openai.OpenAI(api_key=api_key)
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        input=extraction_prompt,
                        instructions="Extrae los metadatos del documento analizando su contenido. El título debe ser extraído del texto del documento, no del nombre del archivo. Responde SOLO con JSON válido, sin texto adicional."
                    )
                    
                    # Intentar parsear la respuesta JSON
                    import json
                    try:
                        # Limpiar la respuesta (puede tener markdown code blocks)
                        response_text = response.output_text.strip()
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.startswith("```"):
                            response_text = response_text[3:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        response_text = response_text.strip()
                        
                        extracted_metadata = json.loads(response_text)
                        
                        # Usar los metadatos extraídos si no se proporcionaron
                        if not title:
                            title = extracted_metadata.get("title", file.filename.replace('.pdf', '').replace('_', ' ').title())
                        if not document_type:
                            document_type = extracted_metadata.get("document_type", "documento")
                        if not category:
                            category = extracted_metadata.get("category", "general")
                        if not source:
                            source = extracted_metadata.get("source", file.filename)
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Error parseando metadatos extraídos: {e}")
                        # Si falla el parseo, usar valores por defecto
                        if not title:
                            title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                        if not document_type:
                            document_type = "documento"
                        if not category:
                            category = "general"
                        if not source:
                            source = file.filename
                else:
                    # Si OpenAI no está disponible, usar valores por defecto
                    if not title:
                        title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                    if not document_type:
                        document_type = "documento"
                    if not category:
                        category = "general"
                    if not source:
                        source = file.filename
            except Exception as extraction_error:
                print(f"Error extrayendo metadatos con RAG: {extraction_error}")
                # Si falla la extracción, usar valores por defecto
                if not title:
                    title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                if not document_type:
                    document_type = "documento"
                if not category:
                    category = "general"
                if not source:
                    source = file.filename
        else:
            # Si se proporcionaron todos los metadatos excepto title, extraer solo el título del contenido
            if not title:
                try:
                    # Extraer solo el título del contenido
                    title_extraction_prompt = f"""Analiza el siguiente documento y extrae SOLO el título descriptivo del documento. 
El título debe ser extraído del contenido del documento, no del nombre del archivo.
Responde SOLO con el título (máximo 100 caracteres), sin JSON, sin comillas, sin texto adicional.

Contenido del documento:
{full_text[:5000]}

Título:"""

                    api_key = os.getenv("OPENAI_API_KEY")
                    if api_key and OPENAI_AVAILABLE:
                        client = openai.OpenAI(api_key=api_key)
                        response = client.responses.create(
                            model="gpt-4o-mini",
                            input=title_extraction_prompt,
                            instructions="Extrae SOLO el título del documento del contenido. Responde únicamente con el título, sin formato JSON, sin comillas, sin texto adicional."
                        )
                        title = response.output_text.strip().strip('"').strip("'")
                        if not title or len(title) == 0:
                            title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                    else:
                        title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                except Exception as title_error:
                    print(f"Error extrayendo título: {title_error}")
                    title = file.filename.replace('.pdf', '').replace('_', ' ').title()
            
            if not source:
                source = file.filename
        
        # Generar ID único para el documento
        doc_id = str(uuid.uuid4())
        
        # Asegurar que title tenga un valor
        if not title:
            title = file.filename.replace('.pdf', '').replace('_', ' ').title()
        
        # Agregar a ChromaDB
        chroma_collection.add(
            documents=[full_text],
            ids=[doc_id],
            metadatas=[{
                "title": title,
                "document_type": document_type or "",
                "category": category or "",
                "source": source or ""
            }]
        )
        
        # Guardar en base de datos MySQL
        new_document = KnowledgeDocumentModel(
            title=title,
            content=full_text,
            document_type=document_type,
            category=category,
            source=source or file.filename,
            chroma_id=doc_id,
            is_active=True,
            added_date=datetime.now(),
            updated_date=datetime.now()
        )
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Documento subido y agregado exitosamente a la base de conocimiento",
                "data": {
                    "id": new_document.id,
                    "chroma_id": doc_id,
                    "title": title,
                    "filename": file.filename,
                    "pages": len(text_content),
                    "characters": len(full_text),
                    "document_type": document_type,
                    "category": category,
                    "source": source or file.filename
                }
            }
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error en upload_knowledge_document: {error_traceback}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error procesando el documento: {str(e)}",
                "data": None
            }
        )

@artificial_intelligence.post("/add")
async def add_knowledge_document(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Agrega un documento de texto a la base de conocimiento para RAG.
    Si no se proporcionan metadatos, se extraen automáticamente usando IA.
    
    Parámetros:
    - content: Contenido del documento (texto grande)
    - title: Título del documento (opcional, se extrae automáticamente si no se proporciona)
    - document_type: Tipo de documento (opcional, se extrae automáticamente si no se proporciona)
    - category: Categoría (opcional, se extrae automáticamente si no se proporciona)
    - source: Fuente del documento (opcional, se extrae automáticamente si no se proporciona)
    """
    try:
        if not CHROMADB_AVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "ChromaDB no está instalado. Instala con: pip install chromadb",
                    "data": None
                }
            )
        
        # Si no se proporcionaron metadatos, extraerlos usando RAG/OpenAI
        final_title = title
        final_document_type = document_type
        final_category = category
        final_source = source
        
        if not title or not document_type or not category:
            try:
                # Preparar prompt para extraer metadatos
                extraction_prompt = f"""Analiza el siguiente documento y extrae información relevante. Responde SOLO en formato JSON con las siguientes claves:
{{
    "title": "Título descriptivo del documento (máximo 100 caracteres)",
    "document_type": "Tipo de documento (ej: normativa, manual, procedimiento, guía, ley, decreto)",
    "category": "Categoría temática (ej: PIE, NEE, evaluación, inclusión, educación)",
    "source": "Fuente u origen del documento (ej: LeyChile, Ministerio de Educación)"
}}

Contenido del documento:
{content[:5000]}

Responde SOLO con el JSON, sin texto adicional."""

                # Usar OpenAI para extraer metadatos
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key and OPENAI_AVAILABLE:
                    client = openai.OpenAI(api_key=api_key)
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        input=extraction_prompt,
                        instructions="Extrae los metadatos del documento y responde SOLO con JSON válido, sin texto adicional."
                    )
                    
                    # Intentar parsear la respuesta JSON
                    import json
                    try:
                        # Limpiar la respuesta (puede tener markdown code blocks)
                        response_text = response.output_text.strip()
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.startswith("```"):
                            response_text = response_text[3:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        response_text = response_text.strip()
                        
                        extracted_metadata = json.loads(response_text)
                        
                        # Usar los metadatos extraídos si no se proporcionaron
                        if not final_title:
                            final_title = extracted_metadata.get("title", "Documento sin título")
                        if not final_document_type:
                            final_document_type = extracted_metadata.get("document_type", "documento")
                        if not final_category:
                            final_category = extracted_metadata.get("category", "general")
                        if not final_source:
                            final_source = extracted_metadata.get("source", "Desconocido")
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Error parseando metadatos extraídos: {e}")
                        # Si falla el parseo, usar valores por defecto
                        if not final_title:
                            final_title = "Documento sin título"
                        if not final_document_type:
                            final_document_type = "documento"
                        if not final_category:
                            final_category = "general"
                        if not final_source:
                            final_source = "Desconocido"
                else:
                    # Si OpenAI no está disponible, usar valores por defecto
                    if not final_title:
                        final_title = "Documento sin título"
                    if not final_document_type:
                        final_document_type = "documento"
                    if not final_category:
                        final_category = "general"
                    if not final_source:
                        final_source = "Desconocido"
            except Exception as extraction_error:
                print(f"Error extrayendo metadatos con RAG: {extraction_error}")
                # Si falla la extracción, usar valores por defecto
                if not final_title:
                    final_title = "Documento sin título"
                if not final_document_type:
                    final_document_type = "documento"
                if not final_category:
                    final_category = "general"
                if not final_source:
                    final_source = "Desconocido"
        else:
            # Si se proporcionaron todos los metadatos, usar valores por defecto para los faltantes
            if not final_title:
                final_title = "Documento sin título"
            if not final_source:
                final_source = "Desconocido"
        
        # Generar ID único para el documento
        doc_id = str(uuid.uuid4())
        
        # Agregar a ChromaDB
        chroma_collection.add(
            documents=[content],
            ids=[doc_id],
            metadatas=[{
                "title": final_title,
                "document_type": final_document_type or "",
                "category": final_category or "",
                "source": final_source or ""
            }]
        )
        
        # Guardar en base de datos MySQL
        new_document = KnowledgeDocumentModel(
            title=final_title,
            content=content,
            document_type=final_document_type,
            category=final_category,
            source=final_source,
            chroma_id=doc_id,
            is_active=True,
            added_date=datetime.now(),
            updated_date=datetime.now()
        )
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Documento agregado exitosamente a la base de conocimiento",
                "data": {
                    "id": new_document.id,
                    "chroma_id": doc_id,
                    "title": final_title,
                    "document_type": final_document_type,
                    "category": final_category,
                    "source": final_source,
                    "metadata_extracted": not (title and document_type and category)  # Indica si se extrajeron metadatos
                }
            }
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error en add_knowledge_document: {error_traceback}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error agregando documento: {str(e)}",
                "data": None
            }
        )

@artificial_intelligence.get("/rag/{pregunta}")
async def consultar_con_rag(
    pregunta: str,
    n_results: Optional[int] = 3,
    instruction: Optional[str] = None,
    session_id: Optional[str] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Consulta usando RAG (Retrieval Augmented Generation).
    Busca documentos relevantes en la base de conocimiento y los usa como contexto.
    """
    try:
        if not OPENAI_AVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "La librería openai no está instalada",
                    "data": None
                }
            )
        
        if not CHROMADB_AVAILABLE:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "ChromaDB no está instalado",
                    "data": None
                }
            )
        
        # Obtener API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "API key de OpenAI no configurada",
                    "data": None
                }
            )
        
        client = openai.OpenAI(api_key=api_key)
        
        # 1. Buscar documentos relevantes en ChromaDB
        results = chroma_collection.query(
            query_texts=[pregunta],
            n_results=n_results or 3
        )
        
        # 2. Construir contexto con los documentos encontrados
        contexto = ""
        documentos_usados = []
        
        if results['documents'] and len(results['documents'][0]) > 0:
            contexto = "Contexto de la base de conocimiento:\n\n"
            for i, doc in enumerate(results['documents'][0]):
                metadata = results.get('metadatas', [[]])[0][i] if results.get('metadatas') else {}
                titulo = metadata.get('title', f'Documento {i+1}')
                contexto += f"{i+1}. {titulo}:\n{doc}\n\n"
                documentos_usados.append({
                    "title": titulo,
                    "content": doc[:200] + "..." if len(doc) > 200 else doc
                })
        
        # 3. Construir instrucción con contexto
        if contexto:
            instruccion_final = f"""{instruction or "Responde la pregunta usando el contexto proporcionado. Si el contexto no contiene información relevante, indica que no tienes esa información en la base de conocimiento."}

{contexto}

Pregunta del usuario:"""
        else:
            instruccion_final = instruction or "Responde la pregunta. Si no tienes información específica, indícalo."
        
        # 4. Realizar petición a OpenAI con contexto
        api_params = {
            "model": "gpt-4o-mini",
            "input": pregunta,
            "instructions": instruccion_final
        }
        
        response = client.responses.create(**api_params)
        ai_response = response.output_text
        
        # 5. Guardar la consulta en el historial
        if not session_id:
            session_id = str(uuid.uuid4())
        
        user_id = getattr(session_user, 'id', None) if session_user else None
        if not user_id and hasattr(session_user, 'customer_id'):
            user_id = session_user.customer_id
        
        try:
            new_conversation = AIConversationModel(
                user_id=user_id,
                session_id=session_id,
                input_text=pregunta,
                instruction=f"RAG - {instruction or 'Consulta con base de conocimiento'}",
                response_text=ai_response,
                model="gpt-4o-mini",
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            db.add(new_conversation)
            db.commit()
        except Exception as db_error:
            db.rollback()
            print(f"Error guardando conversación: {db_error}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Consulta RAG completada exitosamente",
                "data": {
                    "pregunta": pregunta,
                    "respuesta": ai_response,
                    "documentos_usados": documentos_usados,
                    "num_documentos": len(documentos_usados),
                    "model": "gpt-4o-mini",
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None,
                    "session_id": session_id
                }
            }
        )
        
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        print(f"Error en consultar_con_rag: {error_type}: {error_message}")
        print(traceback.format_exc())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error procesando consulta RAG ({error_type}): {error_message}",
                "data": None
            }
        )

@artificial_intelligence.post("/")
async def list_knowledge_documents(
    document_list: KnowledgeDocumentList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los documentos de conocimiento con paginación (10 por defecto).
    
    Parámetros:
    - page: Número de página (opcional, si es None o 0 devuelve todos)
    - per_page: Elementos por página (default: 10)
    """
    try:
        # Si page es None o 0, devolver todos sin paginación
        page = document_list.page if document_list.page is not None and document_list.page > 0 else 0
        per_page = document_list.per_page if document_list.per_page else 10
        
        # Si no hay paginación, devolver todos
        if page == 0:
            documents = db.query(KnowledgeDocumentModel).filter(
                KnowledgeDocumentModel.is_active == True
            ).order_by(
                KnowledgeDocumentModel.added_date.desc()
            ).all()
            
            serialized_documents = [{
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "category": doc.category,
                "source": doc.source,
                "chroma_id": doc.chroma_id,
                "is_active": doc.is_active,
                "added_date": doc.added_date.isoformat() if doc.added_date else None,
                "updated_date": doc.updated_date.isoformat() if doc.updated_date else None,
                "content_preview": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content
            } for doc in documents]
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": "Knowledge documents retrieved successfully",
                    "data": serialized_documents
                }
            )
        
        # Calcular offset para paginación
        offset = (page - 1) * per_page
        
        # Obtener total de documentos activos
        total_items = db.query(KnowledgeDocumentModel).filter(
            KnowledgeDocumentModel.is_active == True
        ).count()
        
        # Calcular total de páginas
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        
        # Obtener documentos paginados
        documents = db.query(KnowledgeDocumentModel).filter(
            KnowledgeDocumentModel.is_active == True
        ).order_by(
            KnowledgeDocumentModel.added_date.desc()
        ).offset(offset).limit(per_page).all()
        
        # Serializar documentos
        serialized_documents = [{
            "id": doc.id,
            "title": doc.title,
            "document_type": doc.document_type,
            "category": doc.category,
            "source": doc.source,
            "chroma_id": doc.chroma_id,
            "is_active": doc.is_active,
            "added_date": doc.added_date.isoformat() if doc.added_date else None,
            "updated_date": doc.updated_date.isoformat() if doc.updated_date else None,
            "content_preview": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content
        } for doc in documents]
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Knowledge documents retrieved successfully",
                "data": {
                    "data": serialized_documents,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": per_page
                }
            }
        )
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error en list_knowledge_documents: {error_traceback}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error retrieving knowledge documents: {str(e)}",
                "data": None
            }
        )
