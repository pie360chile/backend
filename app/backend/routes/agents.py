from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.backend.classes.agent_class import AgentClass
from app.backend.core.cors_utils import cors_headers_for_origin
from app.backend.db.database import SessionLocal, get_db
from app.backend.schemas.agents import AgentChatRequest, AgentCreate, AgentKnowledgeSearch, AgentUpdate
from app.backend.services.agent_chat_service import chat_with_agent, iter_chat_with_agent_events
from app.backend.utils.agent_document_index import search_agent_knowledge

agents = APIRouter(prefix="/agents", tags=["Agents"])


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": status_code, "message": message, "data": None},
    )


@agents.get("")
async def list_agents(db: Session = Depends(get_db)):
    result = AgentClass(db).list_all()
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Agentes encontrados", "data": result},
    )


@agents.post("")
async def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    result = AgentClass(db).store(payload.id, payload.name, payload.role_instructions)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_400_BAD_REQUEST, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"status": 201, "message": "Agente creado", "data": result},
    )


@agents.get("/{agent_id}")
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).get(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "No encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Agente encontrado", "data": result},
    )


@agents.patch("/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)):
    result = AgentClass(db).update(agent_id, payload.name, payload.role_instructions)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "No encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Agente actualizado", "data": result},
    )


@agents.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).delete(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "No encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Agente eliminado", "data": None},
    )


@agents.post("/{agent_id}/knowledge/search")
async def search_agent_knowledge_route(
    agent_id: str,
    payload: AgentKnowledgeSearch,
    db: Session = Depends(get_db),
):
    agent = AgentClass(db).get(agent_id)
    if isinstance(agent, dict) and agent.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, agent.get("message", "No encontrado"))

    query = payload.query.strip()
    if not query:
        return _error(status.HTTP_400_BAD_REQUEST, "La consulta está vacía")

    chunks = search_agent_knowledge(db, agent_id, query, top_k=payload.top_k)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Búsqueda completada",
            "data": {"query": query, "chunks": chunks, "total": len(chunks)},
        },
    )


@agents.post("/{agent_id}/knowledge/reindex")
async def reindex_agent_files(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).reindex_files(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "No encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Archivos reindexados", "data": result},
    )


@agents.post("/{agent_id}/chat")
async def chat_with_agent_route(agent_id: str, payload: AgentChatRequest, db: Session = Depends(get_db)):
    result = chat_with_agent(db, agent_id, payload.message, top_k=payload.top_k)
    if isinstance(result, dict) and result.get("status") == "error":
        code = status.HTTP_404_NOT_FOUND if "no encontrado" in result.get("message", "").lower() else status.HTTP_400_BAD_REQUEST
        return _error(code, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Respuesta generada", "data": result},
    )


@agents.post("/{agent_id}/chat/stream")
async def chat_with_agent_stream_route(agent_id: str, payload: AgentChatRequest, request: Request):
    import json

    origin = request.headers.get("origin")
    stream_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        **cors_headers_for_origin(origin),
    }

    def event_stream():
        db = SessionLocal()
        try:
            for event in iter_chat_with_agent_events(db, agent_id, payload.message, top_k=payload.top_k):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=stream_headers,
    )
