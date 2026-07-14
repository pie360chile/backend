"""Lógica de negocio: Workspace Agent (trigger ChatGPT + listado de archivos)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.utils.agent_workspace_storage import (
    agent_folder,
    default_agent_id,
    list_agent_files as storage_list_files,
    resolve_agent_id,
    save_uploaded_bytes,
)
from app.backend.utils import google_drive_storage as drive_storage
from app.backend.utils.school_drive_config import drive_configured, load_drive_config


class WorkspaceAgentClass:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def _trigger_url(self, override_url: str | None = None) -> str:
        custom = (override_url or "").strip()
        if custom:
            return custom.rstrip("/")
        base = settings.workspace_agent_api_base.rstrip("/")
        agent_id = settings.workspace_agent_id.strip()
        return f"{base}/{agent_id}/trigger"

    def _resolve_access_token(self) -> str:
        if self.db is not None:
            try:
                from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass

                key = AgentsLlmModelsClass(self.db).get_workspace_access_token()
                if key:
                    return key
            except Exception:
                pass
        return (settings.agent_access_token or "").strip()

    def trigger_chat(
        self, user_input: str, *, trigger_url: str | None = None
    ) -> dict[str, Any]:
        token = self._resolve_access_token()
        if not token:
            return {
                "status": "error",
                "message": (
                    "Falta el token de Workspace ChatGPT. "
                    "Configúralo en Agentes → Configuraciones."
                ),
                "http_status": 500,
            }

        url = self._trigger_url(trigger_url)
        if not url:
            return {
                "status": "error",
                "message": (
                    "Falta la URL del endpoint Workspace de este agente. "
                    "Configúrala en el detalle del agente."
                ),
                "http_status": 400,
            }

        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"input": user_input},
                timeout=180,
            )
        except requests.RequestException as exc:
            return {
                "status": "error",
                "message": f"Error al llamar al Workspace Agent: {exc}",
                "http_status": 502,
            }

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text or ""}

        if not response.ok:
            detail = ""
            if isinstance(body, dict):
                detail = str(
                    body.get("error")
                    or body.get("message")
                    or body.get("detail")
                    or ""
                )
            return {
                "status": "error",
                "message": (
                    f"Workspace Agent devolvió HTTP {response.status_code}"
                    + (f": {detail}" if detail else "")
                ),
                "http_status": 502,
                "data": {"status_code": response.status_code, "body": body},
            }

        return {
            "status": "success",
            "message": "Trigger ejecutado correctamente.",
            "http_status": 200,
            "data": {"status_code": response.status_code, "body": body},
        }

    def list_agents(self) -> dict[str, Any]:
        agent_id = default_agent_id()
        folder = agent_folder(agent_id)
        updated_at = None
        if folder.exists():
            try:
                latest = max(
                    (f.stat().st_mtime for f in folder.iterdir() if f.is_file()),
                    default=0,
                )
                if latest:
                    updated_at = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()
            except OSError:
                updated_at = None

        return {
            "status": "success",
            "data": [
                {
                    "id": agent_id,
                    "name": settings.workspace_agent_name,
                    "updatedAt": updated_at,
                }
            ],
        }

    def list_files(self, agent_id: str | None = None) -> dict[str, Any]:
        aid = resolve_agent_id(agent_id)
        files = storage_list_files(aid)
        return {
            "status": "success",
            "data": {
                "agent_id": aid,
                "folder": str(agent_folder(aid)),
                "files": files,
            },
        }

    def upload_file(
        self,
        filename: str,
        data: bytes,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        if not data:
            return {
                "status": "error",
                "message": "El archivo está vacío.",
                "http_status": 400,
            }
        name = (filename or "").strip()
        if not name:
            return {
                "status": "error",
                "message": "filename es obligatorio.",
                "http_status": 400,
            }
        result = save_uploaded_bytes(agent_id, name, data)
        return {"status": "success", "message": "Archivo guardado.", "data": result}

    def upload_to_drive(
        self,
        *,
        school_id: int,
        year: int | None,
        flow: str,
        document_id: int,
        student_id: int,
        filename: str,
        data: bytes,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        if not drive_configured(self.db, school_id):
            return {
                "status": "error",
                "message": (
                    f"Google Drive no está configurado para el colegio {school_id}. "
                    "Configura schools_settings (google_drive_root_folder_id y "
                    "google_service_account_json)."
                ),
                "http_status": 503,
            }
        try:
            drive_cfg = load_drive_config(self.db, school_id)
            payload = drive_storage.upload_bytes(
                config=drive_cfg,
                school_id=school_id,
                year=year,
                flow=flow,
                document_id=document_id,
                student_id=student_id,
                filename=filename,
                data=data,
                mime_type=mime_type,
            )
        except ValueError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "http_status": 400,
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Error al subir a Google Drive: {exc}",
                "http_status": 502,
            }
        return {
            "status": "success",
            "message": "Archivo subido a Google Drive.",
            "data": payload,
        }

    def list_drive_files(
        self,
        *,
        school_id: int,
        year: int | None,
        flow: str,
        document_id: int,
        student_id: int,
    ) -> dict[str, Any]:
        if not drive_configured(self.db, school_id):
            return {
                "status": "error",
                "message": (
                    f"Google Drive no está configurado para el colegio {school_id}. "
                    "Configura schools_settings (google_drive_root_folder_id y "
                    "google_service_account_json)."
                ),
                "http_status": 503,
            }
        try:
            drive_cfg = load_drive_config(self.db, school_id)
            payload = drive_storage.list_folder_files(
                config=drive_cfg,
                school_id=school_id,
                year=year,
                flow=flow,
                document_id=document_id,
                student_id=student_id,
            )
        except ValueError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "http_status": 400,
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Error al listar Google Drive: {exc}",
                "http_status": 502,
            }
        return {"status": "success", "data": payload}
