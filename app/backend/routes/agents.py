import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.agents_chat_class import AgentsChatClass
from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.db.models import UserModel
from app.backend.schemas.agents import (
    AgentChatRequest,
    AgentCreateFolderRequest,
    AgentCreateRequest,
)

agents = APIRouter(
    prefix="/agents",
    tags=["Agents"],
)


@agents.get("/usage/summary")
def agents_usage_summary(
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    rol_id = getattr(session_user, "rol_id", None)
    if int(rol_id or 0) != 1:
        return api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the superadministrator can view agent spending.",
        )
    data = AgentsUsageClass(db).summary_by_customer()
    return api_response(data=data)


@agents.get("/documents/catalog")
def list_catalog_documents(db: Session = Depends(get_db)):
    result = AgentsClass(db).list_catalog_documents()
    return api_response(data=result.get("data", []))


@agents.get("")
def list_agents(db: Session = Depends(get_db)):
    result = AgentsClass(db).list_agents()
    return api_response(data=result.get("data", []))


@agents.post("")
def create_agent(body: AgentCreateRequest, db: Session = Depends(get_db)):
    result = AgentsClass(db).create_agent(body.name, body.role_instructions)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message=result.get("message", "OK"),
        data=result.get("data"),
    )


@agents.get("/{agent_id}/document-templates")
def list_agent_document_templates(agent_id: str, db: Session = Depends(get_db)):
    result = AgentsClass(db).list_document_templates(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data", []))


@agents.post("/{agent_id}/document-templates/{document_id}")
async def upload_agent_document_template(
    agent_id: str,
    document_id: int,
    file: UploadFile = File(...),
    document_name: str = Form(""),
    db: Session = Depends(get_db),
):
    data = await file.read()
    result = AgentsClass(db).save_document_template(
        agent_id,
        document_id,
        document_name,
        data,
        file.filename or "template.docx",
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.post("/{agent_id}/chat")
def chat_agent(
    agent_id: str,
    body: AgentChatRequest,
    db: Session = Depends(get_db),
    session_user: UserModel = Depends(get_current_active_user),
):
    history = [{"role": m.role, "content": m.content} for m in body.history]
    customer_id = getattr(session_user, "customer_id", None)
    school_id = getattr(session_user, "school_id", None)
    user_id = getattr(session_user, "id", None)

    def event_stream():
        chat = AgentsChatClass(
            db,
            customer_id=int(customer_id) if customer_id else None,
            school_id=int(school_id) if school_id else None,
            user_id=int(user_id) if user_id else None,
        )
        for event in chat.stream_chat(
            agent_id,
            body.message,
            student_id=body.student_id,
            student_rut=body.student_rut,
            document_id=body.document_id,
            history=history,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@agents.get("/{agent_id}/files")
def list_agent_files(
    agent_id: str,
    path: str = Query(""),
    db: Session = Depends(get_db),
):
    result = AgentsClass(db).list_files(agent_id, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agents.post("/{agent_id}/files/folder")
def create_agent_folder(
    agent_id: str,
    body: AgentCreateFolderRequest,
    db: Session = Depends(get_db),
):
    result = AgentsClass(db).create_folder(agent_id, body.name, body.parent_path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.post("/{agent_id}/files/upload")
async def upload_agent_files(
    agent_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: str = Form("[]"),
    db: Session = Depends(get_db),
):
    try:
        paths = json.loads(relative_paths)
    except json.JSONDecodeError:
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="relative_paths must be a JSON array.",
        )
    if not isinstance(paths, list):
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="relative_paths must be a JSON array.",
        )

    payload: list[tuple[str, bytes]] = []
    for index, upload in enumerate(files):
        data = await upload.read()
        rel = str(paths[index] if index < len(paths) else upload.filename or "file")
        payload.append((rel, data))

    result = AgentsClass(db).upload_files(agent_id, payload)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.delete("/{agent_id}/files")
def delete_agent_file(
    agent_id: str,
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    result = AgentsClass(db).delete_file(agent_id, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))


@agents.get("/{agent_id}")
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    result = AgentsClass(db).get_agent(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agents.put("/{agent_id}")
def update_agent(agent_id: str, body: AgentCreateRequest, db: Session = Depends(get_db)):
    result = AgentsClass(db).update_agent(agent_id, body.name, body.role_instructions)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agents.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    result = AgentsClass(db).delete_agent(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))
