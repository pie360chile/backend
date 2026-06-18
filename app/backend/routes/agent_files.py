"""Archivos por agente en files/agents/{agent_id}/ + metadata en BD."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.backend.classes.agent_class import AgentClass
from app.backend.db.database import get_db

agent_files = APIRouter(prefix="/agent-files", tags=["Agent Files"])


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": status_code, "message": message, "data": None},
    )


@agent_files.get("/{agent_id}")
async def list_files(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).list_files(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        code = status.HTTP_404_NOT_FOUND if "no encontrado" in result.get("message", "").lower() else status.HTTP_400_BAD_REQUEST
        return _error(code, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Archivos del agente", "data": result},
    )


@agent_files.post("/{agent_id}/upload")
async def upload_files(
    agent_id: str,
    files: Annotated[list[UploadFile], File()],
    relative_paths: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
):
    if not files:
        return _error(status.HTTP_400_BAD_REQUEST, "No se enviaron archivos")

    paths: list[str] = []
    if relative_paths:
        try:
            parsed = json.loads(relative_paths)
            if isinstance(parsed, list):
                paths = [str(item) for item in parsed]
        except json.JSONDecodeError:
            return _error(status.HTTP_400_BAD_REQUEST, "Rutas de carpeta inválidas")

    uploads: list[tuple[str | None, bytes]] = []
    for index, upload in enumerate(files):
        rel_path = paths[index] if index < len(paths) else None
        original_name = rel_path or upload.filename
        uploads.append((original_name, await upload.read()))

    result = AgentClass(db).add_files(agent_id, uploads)
    if isinstance(result, dict) and result.get("status") == "error":
        code = status.HTTP_404_NOT_FOUND if "no encontrado" in result.get("message", "").lower() else status.HTTP_400_BAD_REQUEST
        return _error(code, result.get("message", "Error"))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"status": 201, "message": "Archivos subidos correctamente", "data": result},
    )


@agent_files.get("/{agent_id}/responses")
async def list_response_files(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).list_response_files(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        code = status.HTTP_404_NOT_FOUND if "no encontrado" in result.get("message", "").lower() else status.HTTP_400_BAD_REQUEST
        return _error(code, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Archivos generados por el agente", "data": result},
    )


@agent_files.get("/{agent_id}/responses/download/{stored_filename:path}")
async def download_response_file(agent_id: str, stored_filename: str, db: Session = Depends(get_db)):
    stored_path = stored_filename if stored_filename.startswith("responses/") else f"responses/{stored_filename}"
    result = AgentClass(db).resolve_response_file(agent_id, stored_path)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Archivo no encontrado"))
    return FileResponse(path=result["path"], filename=result["filename"])


@agent_files.delete("/{agent_id}/responses")
async def delete_all_response_files(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).delete_all_response_files(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        code = status.HTTP_404_NOT_FOUND if "no encontrado" in result.get("message", "").lower() else status.HTTP_400_BAD_REQUEST
        return _error(code, result.get("message", "Error"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Respuestas generadas eliminadas", "data": result},
    )


@agent_files.delete("/{agent_id}/responses/{stored_filename:path}")
async def delete_response_file(agent_id: str, stored_filename: str, db: Session = Depends(get_db)):
    stored_path = stored_filename if stored_filename.startswith("responses/") else f"responses/{stored_filename}"
    result = AgentClass(db).delete_response_file(agent_id, stored_path)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Archivo no encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Archivo de respuesta eliminado", "data": result},
    )


@agent_files.get("/{agent_id}/download/{stored_filename:path}")
async def download_file(agent_id: str, stored_filename: str, db: Session = Depends(get_db)):
    result = AgentClass(db).resolve_file(agent_id, stored_filename)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Archivo no encontrado"))
    return FileResponse(path=result["path"], filename=result["filename"])


@agent_files.delete("/{agent_id}/folders/{folder_path:path}")
async def delete_folder(agent_id: str, folder_path: str, db: Session = Depends(get_db)):
    result = AgentClass(db).delete_folder(agent_id, folder_path)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Carpeta no encontrada"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Carpeta eliminada", "data": result},
    )


@agent_files.delete("/{agent_id}/{stored_filename:path}")
async def delete_file(agent_id: str, stored_filename: str, db: Session = Depends(get_db)):
    result = AgentClass(db).delete_file(agent_id, stored_filename)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Archivo no encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Archivo eliminado", "data": result},
    )


@agent_files.delete("/{agent_id}")
async def delete_agent_folder(agent_id: str, db: Session = Depends(get_db)):
    result = AgentClass(db).delete(agent_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return _error(status.HTTP_404_NOT_FOUND, result.get("message", "Agente no encontrado"))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Agente y archivos eliminados", "data": None},
    )
