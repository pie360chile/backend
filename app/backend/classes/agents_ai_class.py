import os
from typing import Any, Dict, List, Optional, Tuple

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

AGENT_PIE_INSTRUCTIONS = """Eres Agente Pie, asistente para equipos del Programa de Integración Escolar (PIE) en Chile.

Tu rol es apoyar a docentes, profesionales PIE y equipos educativos con orientación sobre:
- Necesidades Educativas Especiales (NEE) y apoyos en el aula
- Informes, planes de apoyo, evaluaciones y documentación PIE
- Procesos del establecimiento alineados a la normativa chilena

Responde siempre en español, con claridad y tono profesional. Si usas contexto documental,
priorízalo. Si no tienes certeza o falta información del colegio, indícalo explícitamente.
No inventes datos de estudiantes ni normativa."""

DEFAULT_MODEL = os.getenv('AGENTS_CHAT_MODEL', 'gpt-4o-mini')
DEFAULT_TEMPERATURE = 0.3
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
    ) -> Tuple[Optional[str], Optional[str]]:
        text = (user_message or '').strip()
        if not text:
            return None, 'Message is required'

        if not OPENAI_AVAILABLE:
            return None, 'La librería openai no está instalada en el backend.'

        api_key = _openai_api_key()
        if not api_key:
            return None, 'OPENAI_API_KEY / OPENAI_API_KEY2 no configurada en el backend.'

        try:
            client = openai.OpenAI(api_key=api_key)

            instructions = AGENT_PIE_INSTRUCTIONS
            rag_block = _rag_context(text)
            if rag_block:
                instructions = (
                    f'{instructions}\n\nUsa como referencia principal la base de conocimiento '
                    f'si responde la pregunta:\n\n{rag_block}'
                )

            history_block = _format_history(history or [])
            if history_block:
                instructions = f'{instructions}\n\n{history_block}'

            response = client.responses.create(
                model=DEFAULT_MODEL,
                input=text,
                instructions=instructions,
                temperature=DEFAULT_TEMPERATURE,
            )
            reply = (getattr(response, 'output_text', None) or '').strip()
            if not reply:
                return None, 'OpenAI devolvió una respuesta vacía.'
            return reply, None
        except Exception as e:
            return None, str(e)
