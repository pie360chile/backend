from dataclasses import dataclass
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_optional_current_user
from app.backend.classes.agents_class import AgentsClass
from app.backend.db.database import get_db
from app.backend.db.models import UserModel
from app.backend.schemas import AgentsChatList, AgentsSaveChat, AgentsSendMessage


agents = APIRouter(prefix='/agents', tags=['Agents'])


@dataclass
class AgentActor:
    user_id: int
    customer_id: Optional[int]
    session_id: Optional[str]


def _resolve_session_id(header_value: Optional[str], body_value: Optional[str]) -> Optional[str]:
    for raw in (header_value, body_value):
        s = (raw or '').strip()
        if s:
            return s
    return None


def get_agent_actor(
    session_user: Optional[UserModel] = Depends(get_optional_current_user),
    x_agent_session: Optional[str] = Header(None, alias='X-Agent-Session'),
) -> AgentActor:
    if session_user and getattr(session_user, 'id', None):
        return AgentActor(
            user_id=int(session_user.id),
            customer_id=getattr(session_user, 'customer_id', None),
            session_id=None,
        )
    sid = (x_agent_session or '').strip()
    if not sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='X-Agent-Session header or session_id is required when not logged in',
        )
    return AgentActor(user_id=0, customer_id=None, session_id=sid)


def _error_response(result: dict, default_status: int = status.HTTP_400_BAD_REQUEST):
    return JSONResponse(
        status_code=default_status,
        content={
            'status': default_status,
            'message': result.get('message', 'Error'),
            'data': None,
        },
    )


@agents.post('/')
def index(
    body: AgentsChatList,
    actor: AgentActor = Depends(get_agent_actor),
    db: Session = Depends(get_db),
):
    session_id = _resolve_session_id(None, body.session_id) or actor.session_id
    page_value = 0 if body.page is None else body.page
    result = AgentsClass(db).get_all(
        user_id=actor.user_id,
        page=page_value,
        items_per_page=body.per_page,
        session_id=session_id,
    )

    if isinstance(result, dict) and result.get('status') == 'error':
        return _error_response(result, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Chats retrieved successfully',
            'data': result,
        },
    )


@agents.get('/edit/{id}')
def edit(
    id: int,
    session_id: Optional[str] = None,
    actor: AgentActor = Depends(get_agent_actor),
    db: Session = Depends(get_db),
):
    sid = _resolve_session_id(None, session_id) or actor.session_id
    result = AgentsClass(db).get(chat_id=id, user_id=actor.user_id, session_id=sid)

    if isinstance(result, dict) and result.get('status') == 'error':
        return _error_response(result, status.HTTP_404_NOT_FOUND)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Chat retrieved successfully',
            'data': result,
        },
    )


@agents.post('/save')
def save(
    body: AgentsSaveChat,
    actor: AgentActor = Depends(get_agent_actor),
    db: Session = Depends(get_db),
):
    session_id = _resolve_session_id(None, body.session_id) or actor.session_id
    result = AgentsClass(db).save_chat(
        user_id=actor.user_id,
        customer_id=actor.customer_id,
        title=body.title,
        chat_id=body.chat_id,
        session_id=session_id,
    )

    if isinstance(result, dict) and result.get('status') == 'error':
        return _error_response(result, status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Chat saved successfully',
            'data': result,
        },
    )


def _parse_form_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


async def _read_uploaded_files(form) -> List[tuple]:
    """Lee archivos del multipart de forma compatible con proxy/apache."""
    file_payload: List[tuple] = []
    candidates = []

    for key, value in form.multi_items():
        if key in ('files', 'file', 'files[]') and hasattr(value, 'read'):
            candidates.append(value)

    if not candidates:
        for key in ('files', 'file', 'files[]'):
            candidates.extend(form.getlist(key))

    seen = set()
    for upload in candidates:
        if not hasattr(upload, 'read'):
            continue
        filename = (getattr(upload, 'filename', None) or '').strip()
        if not filename or filename in seen:
            continue
        content = await upload.read()
        if content:
            file_payload.append((filename, content))
            seen.add(filename)

    return file_payload


@agents.post('/send')
async def send(
    request: Request,
    actor: AgentActor = Depends(get_agent_actor),
    db: Session = Depends(get_db),
):
    form = await request.form()
    message = str(form.get('message') or '')
    chat_id = _parse_form_int(form.get('chat_id'))
    session_id = _resolve_session_id(None, str(form.get('session_id') or '') or None) or actor.session_id

    attachments_context = None
    attachment_names: List[str] = []
    image_attachments: List[Dict[str, str]] = []
    file_payload = await _read_uploaded_files(form)

    if file_payload:
        from app.backend.utils.agent_document_extractor import process_uploaded_files

        attachments_context, image_attachments, attachment_names, extract_error = (
            process_uploaded_files(file_payload)
        )
        if extract_error:
            return _error_response({'status': 'error', 'message': extract_error})

    text = (message or '').strip()
    if not text and (attachment_names or image_attachments):
        text = 'Analiza los archivos adjuntos en el contexto del PIE chileno.'

    result = AgentsClass(db).send_message(
        user_id=actor.user_id,
        customer_id=actor.customer_id,
        message=text,
        chat_id=chat_id,
        session_id=session_id,
        attachments_context=attachments_context,
        attachment_names=attachment_names,
        image_attachments=image_attachments,
    )

    if isinstance(result, dict) and result.get('status') == 'error':
        return _error_response(result, status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Message sent successfully',
            'data': result,
        },
    )


@agents.post('/send/json')
def send_json(
    body: AgentsSendMessage,
    actor: AgentActor = Depends(get_agent_actor),
    db: Session = Depends(get_db),
):
    """Compatibilidad: envío solo texto sin archivos."""
    session_id = _resolve_session_id(None, body.session_id) or actor.session_id
    result = AgentsClass(db).send_message(
        user_id=actor.user_id,
        customer_id=actor.customer_id,
        message=body.message,
        chat_id=body.chat_id,
        session_id=session_id,
    )

    if isinstance(result, dict) and result.get('status') == 'error':
        return _error_response(result, status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'status': 200,
            'message': 'Message sent successfully',
            'data': result,
        },
    )
