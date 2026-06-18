from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models import AgentFileModel, AgentModel, AgentResponseFileModel
from app.backend.services.openai_agent_service import (
    OpenAIUploadError,
    attach_file_to_container,
    clear_agent_container,
    delete_openai_file,
    is_container_expired,
    require_openai_file_upload,
    sync_agent_openai_files,
)
from app.backend.utils.agent_document_index import delete_file_chunks, index_agent_file
from app.backend.utils.agent_files import (
    AgentFileError,
    agent_dir,
    build_agent_storage_path,
    ensure_agent_dir,
    path_in_folder,
    safe_display_name,
    validate_agent_id,
    validate_folder_path,
    validate_stored_filename,
)


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _file_dict(row: AgentFileModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.display_name,
        "size": int(row.size_bytes or 0),
        "uploadedAt": _iso(row.uploaded_at),
    }


def _response_file_dict(row: AgentResponseFileModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.display_name,
        "size": int(row.size_bytes or 0),
        "createdAt": _iso(row.created_at),
    }


def _agent_dict(agent: AgentModel, files: list[AgentFileModel]) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "roleInstructions": agent.role_instructions or "",
        "createdAt": _iso(agent.created_at),
        "updatedAt": _iso(agent.updated_at),
        "files": [_file_dict(f) for f in files],
    }


class AgentClass:
    def __init__(self, db: Session):
        self.db = db

    def _files_for(self, agent_id: str) -> list[AgentFileModel]:
        return (
            self.db.query(AgentFileModel)
            .filter(AgentFileModel.agent_id == agent_id)
            .order_by(AgentFileModel.uploaded_at.desc())
            .all()
        )

    def list_all(self) -> list[dict[str, Any]] | dict[str, str]:
        try:
            agents = self.db.query(AgentModel).order_by(AgentModel.updated_at.desc()).all()
            return [_agent_dict(agent, self._files_for(agent.id)) for agent in agents]
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def get(self, agent_id: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}
            return _agent_dict(agent, self._files_for(agent.id))
        except AgentFileError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def store(self, agent_id: str | None, name: str, role_instructions: str) -> dict[str, Any] | dict[str, str]:
        try:
            new_id = agent_id or f"agent-{uuid.uuid4().hex[:12]}"
            validate_agent_id(new_id)

            existing = self.db.query(AgentModel).filter(AgentModel.id == new_id).first()
            if existing:
                return {"status": "error", "message": "Ya existe un agente con ese id"}

            now = datetime.utcnow()
            agent = AgentModel(
                id=new_id,
                name=(name or "Nuevo agente").strip() or "Nuevo agente",
                role_instructions=role_instructions or "",
                created_at=now,
                updated_at=now,
            )
            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)
            ensure_agent_dir(new_id)
            return _agent_dict(agent, [])
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def update(self, agent_id: str, name: str | None, role_instructions: str | None) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}

            if name is not None:
                trimmed = name.strip()
                if trimmed:
                    agent.name = trimmed
            if role_instructions is not None:
                agent.role_instructions = role_instructions

            agent.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(agent)
            return _agent_dict(agent, self._files_for(agent.id))
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def delete(self, agent_id: str) -> dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}

            directory = agent_dir(agent_id)
            if directory.is_dir():
                shutil.rmtree(directory)

            self.db.delete(agent)
            self.db.commit()
            return {"status": "success", "message": "Agente eliminado"}
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def list_files(self, agent_id: str) -> list[dict[str, Any]] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}
            return [_file_dict(row) for row in self._files_for(agent_id)]
        except AgentFileError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def list_response_files(self, agent_id: str) -> list[dict[str, Any]] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}
            rows = (
                self.db.query(AgentResponseFileModel)
                .filter(AgentResponseFileModel.agent_id == agent_id)
                .order_by(AgentResponseFileModel.created_at.desc())
                .all()
            )
            return [_response_file_dict(row) for row in rows]
        except AgentFileError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def resolve_response_file(self, agent_id: str, stored_filename: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            safe_name = validate_stored_filename(stored_filename)
            if not safe_name.startswith("responses/"):
                return {"status": "error", "message": "Archivo de respuesta no encontrado"}
            row = (
                self.db.query(AgentResponseFileModel)
                .filter(AgentResponseFileModel.agent_id == agent_id, AgentResponseFileModel.id == safe_name)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Archivo de respuesta no encontrado"}
            target = agent_dir(agent_id) / safe_name
            if not target.is_file():
                return {"status": "error", "message": "Archivo de respuesta no encontrado en disco"}
            return {"path": str(target), "filename": row.display_name}
        except AgentFileError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def add_files(self, agent_id: str, uploads: list[tuple[str | None, bytes]]) -> list[dict[str, Any]] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}
            if not uploads:
                return {"status": "error", "message": "No se enviaron archivos"}

            directory = ensure_agent_dir(agent_id)
            saved: list[dict[str, Any]] = []
            uploaded_openai_ids: list[str] = []
            written_paths: list[Path] = []

            try:
                for original_name, content in uploads:
                    try:
                        storage_path, display_name = build_agent_storage_path(original_name)
                    except AgentFileError:
                        continue

                    openai_file_id = require_openai_file_upload(content, display_name)
                    uploaded_openai_ids.append(openai_file_id)

                    destination = directory / storage_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(content)
                    written_paths.append(destination)

                    now = datetime.utcnow()
                    row = AgentFileModel(
                        id=storage_path,
                        agent_id=agent_id,
                        display_name=display_name,
                        size_bytes=len(content),
                        openai_file_id=openai_file_id,
                        openai_upload_error=None,
                        uploaded_at=now,
                    )
                    self.db.add(row)
                    self.db.flush()
                    try:
                        index_agent_file(self.db, agent_id, storage_path, destination, display_name)
                    except Exception:
                        delete_file_chunks(self.db, agent_id, storage_path)
                        raise

                    if agent.openai_container_id and not is_container_expired(
                        agent.openai_container_updated_at
                    ):
                        try:
                            attach_file_to_container(agent.openai_container_id, openai_file_id)
                        except Exception:
                            clear_agent_container(agent)

                    saved.append(_file_dict(row))

                if not saved:
                    return {"status": "error", "message": "No se subieron archivos válidos"}

                agent.updated_at = datetime.utcnow()
                self.db.commit()
                return saved
            except OpenAIUploadError as exc:
                self.db.rollback()
                for path in written_paths:
                    if path.is_file():
                        path.unlink()
                    parent = path.parent
                    if parent != directory and parent.is_dir() and not any(parent.iterdir()):
                        parent.rmdir()
                for openai_id in uploaded_openai_ids:
                    delete_openai_file(openai_id)
                return {"status": "error", "message": f"No se pudo subir a OpenAI: {exc}"}
            except Exception:
                self.db.rollback()
                for path in written_paths:
                    if path.is_file():
                        path.unlink()
                for openai_id in uploaded_openai_ids:
                    delete_openai_file(openai_id)
                raise
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def resolve_file(self, agent_id: str, stored_filename: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            safe_name = validate_stored_filename(stored_filename)
            row = (
                self.db.query(AgentFileModel)
                .filter(AgentFileModel.agent_id == agent_id, AgentFileModel.id == safe_name)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Archivo no encontrado"}

            target = agent_dir(agent_id) / safe_name
            if not target.is_file():
                return {"status": "error", "message": "Archivo no encontrado"}

            return {
                "path": str(target),
                "filename": Path(row.display_name.replace("\\", "/")).name,
            }
        except AgentFileError as exc:
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def delete_folder(self, agent_id: str, folder_path: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            folder_prefix = validate_folder_path(folder_path)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}

            rows = [
                row
                for row in self._files_for(agent_id)
                if path_in_folder(row.id, folder_prefix) or path_in_folder(row.display_name, folder_prefix)
            ]
            if not rows:
                return {"status": "error", "message": "Carpeta no encontrada"}

            for row in rows:
                delete_file_chunks(self.db, agent_id, row.id)
                delete_openai_file(row.openai_file_id)
                target = agent_dir(agent_id) / row.id
                if target.is_file():
                    target.unlink()
                self.db.delete(row)

            folder_on_disk = agent_dir(agent_id) / folder_prefix
            if folder_on_disk.is_dir():
                shutil.rmtree(folder_on_disk)

            clear_agent_container(agent)

            agent.updated_at = datetime.utcnow()
            self.db.commit()
            return {"path": folder_prefix, "deletedFiles": len(rows)}
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def delete_file(self, agent_id: str, stored_filename: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            safe_name = validate_stored_filename(stored_filename)
            row = (
                self.db.query(AgentFileModel)
                .filter(AgentFileModel.agent_id == agent_id, AgentFileModel.id == safe_name)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Archivo no encontrado"}

            delete_file_chunks(self.db, agent_id, safe_name)
            delete_openai_file(row.openai_file_id)

            target = agent_dir(agent_id) / safe_name
            if target.is_file():
                target.unlink()

            self.db.delete(row)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if agent:
                agent.updated_at = datetime.utcnow()
            self.db.commit()
            return {"id": safe_name}
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def reindex_files(self, agent_id: str) -> dict[str, Any] | dict[str, str]:
        try:
            validate_agent_id(agent_id)
            agent = self.db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                return {"status": "error", "message": "Agente no encontrado"}

            indexed = 0
            chunks_total = 0
            for row in self._files_for(agent_id):
                path = agent_dir(agent_id) / row.id
                if not path.is_file():
                    continue
                count = index_agent_file(self.db, agent_id, row.id, path, row.display_name)
                indexed += 1
                chunks_total += count

            openai_file_ids = sync_agent_openai_files(self.db, agent_id)

            agent.updated_at = datetime.utcnow()
            self.db.commit()
            return {
                "indexedFiles": indexed,
                "chunks": chunks_total,
                "openaiFiles": len(openai_file_ids),
            }
        except AgentFileError as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
