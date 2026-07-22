"""Google Drive helpers used by the agents panel (upload/list under school path).

Legacy Workspace ChatGPT trigger + local files/agents MCP upload were removed.
Document generation is MCP create_document / agents_document_service.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.backend.utils import google_drive_storage as drive_storage
from app.backend.utils.school_drive_config import drive_configured, load_drive_config


class WorkspaceAgentClass:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

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
