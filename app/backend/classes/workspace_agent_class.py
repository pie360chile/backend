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
)


class WorkspaceAgentClass:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def _trigger_url(self) -> str:
        base = settings.workspace_agent_api_base.rstrip("/")
        agent_id = settings.workspace_agent_id.strip()
        return f"{base}/{agent_id}/trigger"

    def trigger_chat(self, user_input: str) -> dict[str, Any]:
        token = settings.agent_access_token
        if not token:
            return {
                "status": "error",
                "message": "AGENT_ACCESS_TOKEN no está configurado en el servidor.",
                "http_status": 500,
            }

        try:
            response = requests.post(
                self._trigger_url(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"input": user_input},
                timeout=60,
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
            return {
                "status": "error",
                "message": f"Workspace Agent devolvió HTTP {response.status_code}",
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
