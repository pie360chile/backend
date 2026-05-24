from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.backend.db.models import ChatDetailModel, ChatModel
from app.backend.classes.agents_ai_class import AgentsAiClass

CHAT_TYPE_USER = 1
CHAT_TYPE_ASSISTANT = 2
HISTORY_CONTEXT_LIMIT = 20


def _format_dt(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    return value.strftime('%Y-%m-%d %H:%M:%S')


def _title_from_text(text: str, max_len: int = 512) -> str:
    t = (text or '').strip()
    if not t:
        return 'Chat nuevo'
    return t[:max_len]


def _detail_role(chat_type_id: int) -> str:
    return 'user' if chat_type_id == CHAT_TYPE_USER else 'assistant'


def _normalize_session_id(session_id: Optional[str]) -> Optional[str]:
    s = (session_id or '').strip()
    return s if s else None


class AgentsClass:
    def __init__(self, db):
        self.db = db

    def _ownership_query(self, user_id: int, session_id: Optional[str]):
        sid = _normalize_session_id(session_id)
        query = self.db.query(ChatModel)
        if user_id and int(user_id) > 0:
            return query.filter(ChatModel.user_id == int(user_id))
        if sid:
            return query.filter(ChatModel.user_id == 0, ChatModel.session_id == sid)
        return query.filter(ChatModel.id == -1)

    def _find_chat(self, chat_id: int, user_id: int, session_id: Optional[str]):
        return self._ownership_query(user_id, session_id).filter(ChatModel.id == chat_id).first()

    def _get_recent_history(
        self,
        chat_id: int,
        limit: int = HISTORY_CONTEXT_LIMIT,
    ) -> List[Dict[str, str]]:
        """
        Últimos N registros de chat_details (preguntas y respuestas),
        en orden cronológico, para mantener el hilo de la conversación.
        """
        rows = (
            self.db.query(ChatDetailModel)
            .filter(ChatDetailModel.chat_id == chat_id)
            .order_by(ChatDetailModel.id.desc())
            .limit(limit)
            .all()
        )
        chronological = list(reversed(rows))
        return [
            {
                'role': _detail_role(d.chat_type_id),
                'content': d.message,
                'chat_type_id': d.chat_type_id,
            }
            for d in chronological
        ]

    def answers(
        self,
        user_id: int,
        message: str,
        chat_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Union[Dict[str, Any], Dict[str, str]]:
        """
        Lee el historial guardado en BD (hasta 20 mensajes: usuario + agente)
        y genera la respuesta de la IA usando ese contexto.
        """
        text = (message or '').strip()
        if not text:
            return {'status': 'error', 'message': 'Message is required'}

        history: List[Dict[str, str]] = []
        if chat_id:
            chat = self._find_chat(chat_id, user_id, session_id)
            if not chat:
                return {'status': 'error', 'message': 'Chat not found'}
            history = self._get_recent_history(chat_id, HISTORY_CONTEXT_LIMIT)

        ai_reply, ai_error = AgentsAiClass().generate_reply(text, history)
        if ai_error or not ai_reply:
            return {
                'status': 'error',
                'message': ai_error or 'No se pudo generar la respuesta del agente.',
            }

        return {
            'reply': ai_reply,
            'history_used': len(history),
        }

    def get_all(
        self,
        user_id: int,
        page: int = 0,
        items_per_page: int = 50,
        session_id: Optional[str] = None,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        try:
            query = self._ownership_query(user_id, session_id).with_entities(
                ChatModel.id,
                ChatModel.title,
                ChatModel.added_date,
                ChatModel.updated_date,
            ).order_by(ChatModel.updated_date.desc(), ChatModel.id.desc())

            page_val = 0 if page is None else int(page)
            if page_val > 0:
                ipp = items_per_page or 50
                total_items = query.count()
                total_pages = (total_items + ipp - 1) // ipp if ipp else 0
                if total_items == 0:
                    return {
                        'total_items': 0,
                        'total_pages': 0,
                        'current_page': page_val,
                        'items_per_page': ipp,
                        'data': [],
                    }
                data = query.offset((page_val - 1) * ipp).limit(ipp).all()
                serialized = [
                    {
                        'id': row.id,
                        'title': row.title,
                        'added_date': _format_dt(row.added_date),
                        'updated_date': _format_dt(row.updated_date),
                    }
                    for row in data
                ]
                return {
                    'total_items': total_items,
                    'total_pages': total_pages,
                    'current_page': page_val,
                    'items_per_page': ipp,
                    'data': serialized,
                }

            rows = query.all()
            return [
                {
                    'id': row.id,
                    'title': row.title,
                    'added_date': _format_dt(row.added_date),
                    'updated_date': _format_dt(row.updated_date),
                }
                for row in rows
            ]
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get(
        self,
        chat_id: int,
        user_id: int,
        session_id: Optional[str] = None,
    ) -> Union[Dict[str, Any], Dict[str, str]]:
        try:
            chat = self._find_chat(chat_id, user_id, session_id)
            if not chat:
                return {'status': 'error', 'message': 'Chat not found'}

            details = (
                self.db.query(ChatDetailModel)
                .filter(ChatDetailModel.chat_id == chat_id)
                .order_by(ChatDetailModel.id.asc())
                .all()
            )

            return {
                'id': chat.id,
                'title': chat.title,
                'added_date': _format_dt(chat.added_date),
                'updated_date': _format_dt(chat.updated_date),
                'details': [
                    {
                        'id': d.id,
                        'chat_id': d.chat_id,
                        'chat_type_id': d.chat_type_id,
                        'role': _detail_role(d.chat_type_id),
                        'message': d.message,
                        'added_date': _format_dt(d.added_date),
                    }
                    for d in details
                ],
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def save_chat(
        self,
        user_id: int,
        customer_id: Optional[int],
        title: str,
        chat_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        """Guarda cabecera de chat (p. ej. borrador sin mensajes enviados aún)."""
        try:
            title_val = _title_from_text(title)
            now = datetime.now()
            sid = _normalize_session_id(session_id)
            uid = int(user_id) if user_id and int(user_id) > 0 else 0

            if chat_id:
                chat = self._find_chat(chat_id, user_id, session_id)
                if not chat:
                    return {'status': 'error', 'message': 'Chat not found'}
                chat.title = title_val
                chat.updated_date = now
            else:
                chat = ChatModel(
                    user_id=uid,
                    customer_id=customer_id,
                    session_id=sid if uid == 0 else None,
                    title=title_val,
                    added_date=now,
                    updated_date=now,
                )
                self.db.add(chat)

            self.db.commit()
            self.db.refresh(chat)
            return {
                'id': chat.id,
                'title': chat.title,
                'added_date': _format_dt(chat.added_date),
                'updated_date': _format_dt(chat.updated_date),
            }
        except Exception as e:
            self.db.rollback()
            return {'status': 'error', 'message': str(e)}

    def send_message(
        self,
        user_id: int,
        customer_id: Optional[int],
        message: str,
        chat_id: Optional[int] = None,
        assistant_reply: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        text = (message or '').strip()
        if not text:
            return {'status': 'error', 'message': 'Message is required'}

        sid = _normalize_session_id(session_id)
        uid = int(user_id) if user_id and int(user_id) > 0 else 0
        if uid == 0 and not sid:
            return {'status': 'error', 'message': 'session_id is required'}

        now = datetime.now()

        try:
            if chat_id:
                chat = self._find_chat(chat_id, user_id, session_id)
                if not chat:
                    return {'status': 'error', 'message': 'Chat not found'}
            else:
                chat = ChatModel(
                    user_id=uid,
                    customer_id=customer_id,
                    session_id=sid if uid == 0 else None,
                    title=_title_from_text(text),
                    added_date=now,
                    updated_date=now,
                )
                self.db.add(chat)
                self.db.flush()

            if assistant_reply is not None:
                reply = assistant_reply.strip()
            else:
                answer_result = self.answers(
                    user_id, text, chat_id=chat.id, session_id=session_id
                )
                if answer_result.get('status') == 'error':
                    reply = (
                        'No pude generar una respuesta en este momento. '
                        f"Detalle: {answer_result.get('message', 'error desconocido')}"
                    )
                else:
                    reply = answer_result['reply']

            has_details = (
                self.db.query(ChatDetailModel.id)
                .filter(ChatDetailModel.chat_id == chat.id)
                .limit(1)
                .first()
            )
            if not has_details:
                chat.title = _title_from_text(text)

            user_detail = ChatDetailModel(
                chat_id=chat.id,
                chat_type_id=CHAT_TYPE_USER,
                message=text,
                added_date=now,
            )
            assistant_detail = ChatDetailModel(
                chat_id=chat.id,
                chat_type_id=CHAT_TYPE_ASSISTANT,
                message=reply,
                added_date=now,
            )
            self.db.add(user_detail)
            self.db.add(assistant_detail)
            chat.updated_date = now

            self.db.commit()
            self.db.refresh(chat)

            result = self.get(chat.id, user_id, session_id=session_id)
            if isinstance(result, dict) and result.get('status') == 'error':
                return result
            return {
                'chat_id': chat.id,
                'title': chat.title,
                **result,
            }
        except Exception as e:
            self.db.rollback()
            return {'status': 'error', 'message': str(e)}
