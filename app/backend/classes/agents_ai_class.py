import os
from typing import Any, Dict, List, Optional, Tuple

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


AGENT_PIE_INSTRUCTIONS = """Eres Agente Pie, asistente para equipos del Programa de Integración Escolar (PIE) en Chile.

ÁMBITO DE TRABAJO — Todo lo relacionado con el PIE chileno está dentro de tu alcance. Eres un apoyo
profesional para el trabajo diario del equipo PIE del establecimiento. Ayuda con cualquier consulta
vinculada a inclusión escolar, NEE y procesos PIE, incluyendo (sin limitarte a esto):

• Normativa y marco PIE: Decreto 170, orientaciones MINEDUC, procedimientos del establecimiento
• Equipo PIE: coordinación, roles profesionales, reuniones, planificación y seguimiento
• Estudiantes con NEE: identificación, evaluación, apoyos, adecuaciones curriculares y accesibilidad
• Documentación e informes del PIE: evaluaciones (psicopedagógica, psicológica, fonoaudiológica,
  social, médica, etc.), anamnesis, PAI, informes de avance, interconsultas, certificados, actas,
  informes a familias, informes de egreso y cualquier otro documento del proceso PIE
• Redacción y orientación: estructura de informes, borradores, síntesis, conclusiones, recomendaciones
• Apoyos en el aula: estrategias pedagógicas, coordinación con docentes, material adaptado
• Familia y comunidad escolar: orientación, comunicación y acompañamiento en el marco PIE
• Dificultades específicas del aprendizaje, TEA, TDAH, discapacidad intelectual, DEA, TEL y otras NEE
  en contexto escolar chileno

Si el usuario ofrece datos para redactar o completar cualquier documento o consulta del ámbito PIE,
ayúdale: indica qué información necesitas, propón estructura o borrador, y recuerda que debe revisar
y validar el texto profesionalmente.

FUERA DE ALCANCE — rechaza ÚNICAMENTE lo que no tenga relación con el PIE escolar chileno:
entretenimiento, deportes, cocina, viajes, clima, actualidad general, tareas escolares ajenas a PIE/NEE,
consultas personales de salud/legal/finanzas sin vínculo con el establecimiento, o educación especial
de otros países como tema principal.

Regla clave: el PIE abarca muchas áreas y documentos. No rechaces una consulta solo porque no aparece
en una lista de ejemplos. Si tiene relación razonable con inclusión escolar, NEE, apoyos o documentación
PIE en Chile, debes ayudar. En caso de duda, responde; no rechaces por precaución.

Responde siempre en español, con claridad y tono profesional. Si usas contexto documental, priorízalo.
Si no tienes certeza o falta información del colegio, indícalo explícitamente. No inventes datos de
estudiantes ni normativa."""

DEFAULT_MODEL = os.getenv('AGENTS_CHAT_MODEL', 'gpt-4o-mini')
RAG_N_RESULTS = int(os.getenv('AGENTS_RAG_N_RESULTS', '3') or '3')
HISTORY_CONTEXT_LIMIT = int(os.getenv('AGENTS_HISTORY_LIMIT', '20') or '20')


def _openai_api_key() -> Optional[str]:
    return os.getenv('OPENAI_API_KEY2') or os.getenv('OPENAI_API_KEY')


def _get_chroma_collection():
    try:
        from app.backend.routes import artificial_intelligence as ai_routes

        if getattr(ai_routes, 'CHROMADB_AVAILABLE', False) and getattr(
            ai_routes, 'chroma_collection', None
        ):
            return ai_routes.chroma_collection
    except Exception:
        pass
    return None


def _rag_context(question: str, n_results: int = RAG_N_RESULTS) -> str:
    collection = _get_chroma_collection()
    if not collection:
        return ''

    try:
        results = collection.query(query_texts=[question], n_results=n_results)
        docs = results.get('documents') or []
        if not docs or not docs[0]:
            return ''

        block = 'Contexto de la base de conocimiento PIE360:\n\n'
        metas = results.get('metadatas') or [[]]
        for i, doc in enumerate(docs[0]):
            meta = metas[0][i] if i < len(metas[0]) else {}
            title = (meta or {}).get('title') or f'Documento {i + 1}'
            block += f'{i + 1}. {title}:\n{doc}\n\n'
        return block.strip()
    except Exception:
        return ''


def _format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return ''

    lines = ['Historial reciente de esta conversación (máximo 20 mensajes):']
    for msg in history[-HISTORY_CONTEXT_LIMIT:]:
        role = 'Usuario' if msg.get('role') == 'user' else 'Agente Pie'
        content = (msg.get('content') or '').strip()
        if content:
            lines.append(f'{role}: {content}')
    return '\n'.join(lines)


class AgentsAiClass:
    def generate_reply(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        attachments_context: Optional[str] = None,
        image_attachments: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        text = (user_message or '').strip()
        images = image_attachments or []
        has_docs = bool((attachments_context or '').strip())
        has_images = len(images) > 0

        if not text and not has_docs and not has_images:
            return None, 'Message or files are required'

        if not OPENAI_AVAILABLE:
            return None, 'La librería openai no está instalada en el backend.'

        api_key = _openai_api_key()
        if not api_key:
            return None, 'OPENAI_API_KEY / OPENAI_API_KEY2 no configurada en el backend.'

        try:
            client = openai.OpenAI(api_key=api_key)

            instructions = AGENT_PIE_INSTRUCTIONS
            rag_block = _rag_context(text or 'documento o imagen PIE adjunto')
            if rag_block:
                instructions = (
                    f'{instructions}\n\nUsa como referencia principal la base de conocimiento '
                    f'cuando el contexto responda o enriquezca la pregunta:\n\n{rag_block}'
                )

            attach_block = (attachments_context or '').strip()
            if attach_block:
                instructions = (
                    f'{instructions}\n\n{attach_block}\n\n'
                    'Instrucción: El usuario adjuntó documento(s) de texto. Léelos y úsalos para '
                    'analizar, resumir, redactar informes PIE o responder según su mensaje.'
                )

            if has_images:
                instructions = (
                    f'{instructions}\n\n'
                    'El usuario adjuntó imagen(es). Obsérvalas con atención: pueden ser informes '
                    'escaneados, formularios, capturas o material del establecimiento. Extrae el texto '
                    'visible y responde en el marco del PIE chileno. Si la imagen no es legible, '
                    'indícalo y pide una mejor foto o un PDF/DOCX.'
                )

            history_block = _format_history(history or [])
            if history_block:
                instructions = f'{instructions}\n\n{history_block}'

            if has_images:
                user_input = text or 'Analiza las imágenes adjuntas y responde según el contexto PIE chileno.'
                if has_docs:
                    user_input += ' También considera los documentos de texto adjuntos en las instrucciones.'
                image_names = ', '.join(img.get('filename', 'imagen') for img in images)
                user_input += f'\n\nImágenes adjuntas: {image_names}.'

                content_parts: List[Dict[str, Any]] = [
                    {'type': 'input_text', 'text': user_input},
                ]
                for img in images:
                    content_parts.append(
                        {
                            'type': 'input_image',
                            'image_url': img['image_url'],
                        }
                    )
                api_input: Any = [{'role': 'user', 'content': content_parts}]
            else:
                user_input = text or 'Analiza los documentos adjuntos y responde según el contexto PIE chileno.'
                api_input = user_input

            response = client.responses.create(
                model=DEFAULT_MODEL,
                input=api_input,
                instructions=instructions,
            )
            reply = (getattr(response, 'output_text', None) or '').strip()
            if not reply:
                return None, 'OpenAI devolvió una respuesta vacía.'
            return reply, None
        except Exception as e:
            return None, str(e)
