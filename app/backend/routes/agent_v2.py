import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.classes.agent_v2_chat_class import AgentV2ChatClass
from app.backend.classes.agent_v2_class import AgentV2Class
from app.backend.core.responses import api_error, api_response
from app.backend.db.database import get_db
from app.backend.schemas.agent_v2 import (
    AgentV2ChatRequest,
    AgentV2CreateFolderRequest,
    AgentV2CreateRequest,
)

agent_v2 = APIRouter(
    prefix="/agent-v2",
    tags=["AgentV2"],
)


@agent_v2.get("/documents/catalog")
def list_catalog_documents_v2(db: Session = Depends(get_db)):
    result = AgentV2Class(db).list_catalog_documents()
    return api_response(data=result.get("data", []))


@agent_v2.get("/agents/{agent_id}/document-templates")
def list_agent_document_templates(agent_id: str, db: Session = Depends(get_db)):
    result = AgentV2Class(db).list_document_templates(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data", []))


@agent_v2.post("/agents/{agent_id}/document-templates/{document_id}")
async def upload_agent_document_template(
    agent_id: str,
    document_id: int,
    file: UploadFile = File(...),
    document_name: str = Form(""),
    db: Session = Depends(get_db),
):
    data = await file.read()
    result = AgentV2Class(db).save_document_template(
        agent_id,
        document_id,
        document_name,
        data,
        file.filename or "formato.docx",
    )
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agent_v2.post("/agents/{agent_id}/chat")
def chat_agent_v2(
    agent_id: str,
    body: AgentV2ChatRequest,
    db: Session = Depends(get_db),
):
    history = [{"role": m.role, "content": m.content} for m in body.history]

    def event_stream():
        chat = AgentV2ChatClass(db)
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


@agent_v2.get("/agents/{agent_id}")
def get_agent_v2(agent_id: str, db: Session = Depends(get_db)):
    result = AgentV2Class(db).get_agent(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agent_v2.put("/agents/{agent_id}")
def update_agent_v2(agent_id: str, body: AgentV2CreateRequest, db: Session = Depends(get_db)):
    result = AgentV2Class(db).update_agent(agent_id, body.name, body.role_instructions)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agent_v2.get("/agents")
def list_agents_v2(db: Session = Depends(get_db)):
    result = AgentV2Class(db).list_agents()
    return api_response(data=result.get("data", []))


@agent_v2.post("/agents")
def create_agent_v2(body: AgentV2CreateRequest, db: Session = Depends(get_db)):
    result = AgentV2Class(db).create_agent(body.name, body.role_instructions)
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


@agent_v2.delete("/agents/{agent_id}")
def delete_agent_v2(agent_id: str, db: Session = Depends(get_db)):
    result = AgentV2Class(db).delete_agent(agent_id)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))


@agent_v2.get("/agents/{agent_id}/files")
def list_agent_files_v2(
    agent_id: str,
    path: str = Query(""),
    db: Session = Depends(get_db),
):
    result = AgentV2Class(db).list_files(agent_id, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_404_NOT_FOUND),
            message=result.get("message", "Error"),
        )
    return api_response(data=result.get("data"))


@agent_v2.post("/agents/{agent_id}/files/folder")
def create_agent_folder_v2(
    agent_id: str,
    body: AgentV2CreateFolderRequest,
    db: Session = Depends(get_db),
):
    result = AgentV2Class(db).create_folder(agent_id, body.name, body.parent_path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agent_v2.post("/agents/{agent_id}/files/upload")
async def upload_agent_files_v2(
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
            message="relative_paths debe ser un JSON array.",
        )
    if not isinstance(paths, list):
        return api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="relative_paths debe ser un JSON array.",
        )

    payload: list[tuple[str, bytes]] = []
    for index, upload in enumerate(files):
        data = await upload.read()
        rel = str(paths[index] if index < len(paths) else upload.filename or "archivo")
        payload.append((rel, data))

    result = AgentV2Class(db).upload_files(agent_id, payload)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"), data=result.get("data"))


@agent_v2.delete("/agents/{agent_id}/files")
def delete_agent_file_v2(
    agent_id: str,
    path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    result = AgentV2Class(db).delete_file(agent_id, path)
    if result.get("status") == "error":
        return api_error(
            status_code=result.get("http_status", status.HTTP_400_BAD_REQUEST),
            message=result.get("message", "Error"),
        )
    return api_response(message=result.get("message", "OK"))
