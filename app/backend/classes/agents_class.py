"""Configurable agents CRUD (PIE360 Agents) — scoped per customer_id."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.documents_class import DocumentsClass
from app.backend.db.models.agent import AgentModel
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel
from app.backend.utils import agents_storage as storage
from app.backend.utils.agents_template_inspector import (
    fields_from_json,
    fields_to_json,
    inspect_template_fields,
)


SECTION_LABELS = {
    1: "Transversales",
    2: "Evaluación",
    3: "Apoyo",
    4: "Otros",
}

# Preferred display order for evaluation reports (career then specialty list).
EVALUATION_DOC_ORDER = [
    "Informe Fonoaudiológico - Evaluación Informal",
    "Informe Fonoaudiológico - IDTEL",
    "Informe Fonoaudiológico - PEFE",
    "Informe Fonoaudiológico - STSG, TECAL y TEPROSIF",
    "Informe kinesiológico - Evaluación informal",
    "Informe Kinesiológica - Vitor Da Fonseca",
    "Informe de conducta adaptativa – ABAS II",
    "Informe de conducta adaptativa – ICAP",
    "Informe Psicológico – WAIS IV",
    "Informe Psicológico – WISC V",
    "Test de Conners (para docentes abreviada)",
    "Informe Terapia Ocupacional - Evaluación Informal",
    "Informe Terapia Ocupacional - Perfil Sensorial",
    "Informe Terapia Ocupacional - SPM-2",
]


def _maybe_refresh_template_fields(db: Session, row: AgentDocumentTemplateModel) -> None:
    """Re-inspect saved templates that have no detected fields (e.g. content controls only)."""
    if fields_from_json(row.detected_fields):
        return
    if not row.template_path:
        return
    template_abs = (storage.files_dir() / row.template_path).resolve()
    if not template_abs.is_file():
        return
    try:
        inspection = inspect_template_fields(template_abs, row.format_type)
    except ValueError:
        return
    fields = inspection.get("fields") or []
    if not fields:
        return
    row.detected_fields = fields_to_json(fields)
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(row)


def _serialize_template(row: AgentDocumentTemplateModel) -> dict[str, Any]:
    fields = fields_from_json(row.detected_fields)
    return {
        "id": row.id,
        "documentId": row.document_id,
        "documentName": row.document_name,
        "formatType": row.format_type,
        "templatePath": row.template_path,
        "fields": fields,
        "fieldCount": len(fields),
    }


def _cid(agent: AgentModel) -> int | None:
    return int(agent.customer_id) if agent.customer_id is not None else None


def _serialize(agent: AgentModel, db: Session) -> dict[str, Any]:
    updated = agent.updated_at or agent.created_at
    templates = (
        db.query(AgentDocumentTemplateModel)
        .filter(AgentDocumentTemplateModel.agent_id == agent.id)
        .count()
    )
    return {
        "id": agent.id,
        "customerId": _cid(agent),
        "name": agent.name,
        "roleInstructions": agent.role_instructions,
        "workspaceTriggerUrl": (getattr(agent, "workspace_trigger_url", None) or None),
        "updatedAt": updated.isoformat() if updated else None,
        "fileCount": storage.count_files(agent.name, _cid(agent)),
        "documentTemplateCount": templates,
    }


class AgentsClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_agent(
        self, agent_id: str, customer_id: int | None = None
    ) -> AgentModel | None:
        q = self.db.query(AgentModel).filter(AgentModel.id == agent_id)
        if customer_id is not None:
            q = q.filter(AgentModel.customer_id == int(customer_id))
        return q.first()

    def list_agents(self, customer_id: int) -> dict[str, Any]:
        rows = (
            self.db.query(AgentModel)
            .filter(AgentModel.customer_id == int(customer_id))
            .order_by(AgentModel.updated_at.desc())
            .all()
        )
        return {"status": "success", "data": [_serialize(row, self.db) for row in rows]}

    def get_agent(self, agent_id: str, customer_id: int) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        return {"status": "success", "data": _serialize(agent, self.db)}

    def update_agent(
        self,
        agent_id: str,
        customer_id: int,
        name: str,
        role_instructions: str,
        workspace_trigger_url: str | None = None,
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}

        clean_name = name.strip()
        if not clean_name:
            return {"status": "error", "message": "Name is required.", "http_status": 400}

        duplicate = (
            self.db.query(AgentModel)
            .filter(
                AgentModel.customer_id == int(customer_id),
                AgentModel.name == clean_name,
                AgentModel.id != agent_id,
            )
            .first()
        )
        if duplicate:
            return {
                "status": "error",
                "message": "An agent with that name already exists for this client.",
                "http_status": 409,
            }

        old_name = agent.name
        agent.name = clean_name
        agent.role_instructions = role_instructions.strip()
        if workspace_trigger_url is not None:
            url = workspace_trigger_url.strip()
            agent.workspace_trigger_url = url or None
        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(agent)

        if old_name != clean_name:
            try:
                storage.rename_agent_folder(old_name, clean_name, int(customer_id))
            except ValueError:
                pass

        return {"status": "success", "message": "Agent saved.", "data": _serialize(agent, self.db)}

    def create_agent(
        self,
        customer_id: int,
        name: str,
        role_instructions: str,
        workspace_trigger_url: str | None = None,
    ) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            return {"status": "error", "message": "Name is required.", "http_status": 400}

        existing = (
            self.db.query(AgentModel)
            .filter(
                AgentModel.customer_id == int(customer_id),
                AgentModel.name == clean_name,
            )
            .first()
        )
        if existing:
            return {
                "status": "error",
                "message": "An agent with that name already exists for this client.",
                "http_status": 409,
            }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        url = (workspace_trigger_url or "").strip() or None
        agent = AgentModel(
            id=uuid.uuid4().hex,
            customer_id=int(customer_id),
            name=clean_name,
            role_instructions=role_instructions.strip(),
            workspace_trigger_url=url,
            created_at=now,
            updated_at=now,
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        storage.agent_folder(agent.name, int(customer_id))
        return {"status": "success", "message": "Agent created.", "data": _serialize(agent, self.db)}

    def list_catalog_documents(self) -> dict[str, Any]:
        docs_class = DocumentsClass(self.db)
        sections: list[dict[str, Any]] = []
        seen: set[int] = set()
        order_index = {name: i for i, name in enumerate(EVALUATION_DOC_ORDER)}
        for section_id, label in SECTION_LABELS.items():
            result = docs_class.get_all(section_id, None)
            if isinstance(result, dict) and result.get("status") == "error":
                continue
            items = []
            for row in result or []:
                doc_id = int(row["id"])
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                items.append(
                    {
                        "id": doc_id,
                        "name": row.get("document") or "",
                        "sectionId": row.get("document_type_id") or section_id,
                        "sectionLabel": SECTION_LABELS.get(
                            row.get("document_type_id") or section_id, label
                        ),
                        "careerTypeId": row.get("career_type_id"),
                    }
                )
            if section_id == 2:
                items.sort(
                    key=lambda d: (
                        order_index.get(d["name"], 10_000),
                        (d.get("careerTypeId") is None, d.get("careerTypeId") or 0),
                        d["name"].lower(),
                    )
                )
            else:
                items.sort(key=lambda d: d["name"].lower())
            if items:
                sections.append(
                    {"sectionId": section_id, "sectionLabel": label, "documents": items}
                )
        return {"status": "success", "data": sections}

    def list_document_templates(self, agent_id: str, customer_id: int) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        rows = (
            self.db.query(AgentDocumentTemplateModel)
            .filter(AgentDocumentTemplateModel.agent_id == agent_id)
            .order_by(AgentDocumentTemplateModel.document_name.asc())
            .all()
        )
        for row in rows:
            _maybe_refresh_template_fields(self.db, row)
        return {"status": "success", "data": [_serialize_template(row) for row in rows]}

    def save_document_template(
        self,
        agent_id: str,
        customer_id: int,
        document_id: int,
        document_name: str,
        data: bytes,
        filename: str,
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}

        lower = (filename or "").lower()
        if lower.endswith(".docx"):
            format_type = "docx"
        elif lower.endswith(".pdf"):
            format_type = "pdf"
        else:
            return {
                "status": "error",
                "message": "Only .docx or .pdf templates are allowed.",
                "http_status": 400,
            }

        try:
            saved = storage.save_document_template(
                agent.name, document_id, data, format_type, int(customer_id)
            )
            absolute = (storage.files_dir() / saved["relativePath"]).resolve()
            inspection = inspect_template_fields(absolute, format_type)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = (
            self.db.query(AgentDocumentTemplateModel)
            .filter(
                AgentDocumentTemplateModel.agent_id == agent_id,
                AgentDocumentTemplateModel.document_id == document_id,
            )
            .first()
        )
        if row:
            row.document_name = document_name.strip() or row.document_name
            row.format_type = format_type
            row.template_path = saved["relativePath"]
            row.detected_fields = fields_to_json(inspection.get("fields", []))
            row.updated_at = now
        else:
            row = AgentDocumentTemplateModel(
                agent_id=agent_id,
                document_id=document_id,
                document_name=document_name.strip() or f"Document {document_id}",
                format_type=format_type,
                template_path=saved["relativePath"],
                detected_fields=fields_to_json(inspection.get("fields", [])),
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)

        agent.updated_at = now
        self.db.commit()
        self.db.refresh(row)
        payload = _serialize_template(row)
        payload["inspection"] = inspection
        return {"status": "success", "message": "Template saved.", "data": payload}

    def delete_agent(self, agent_id: str, customer_id: int) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        self.db.query(AgentDocumentTemplateModel).filter(
            AgentDocumentTemplateModel.agent_id == agent_id
        ).delete()
        storage.delete_agent_folder(agent.name, int(customer_id))
        self.db.delete(agent)
        self.db.commit()
        return {"status": "success", "message": "Agent deleted."}

    def list_files(self, agent_id: str, customer_id: int, path: str = "") -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        try:
            data = storage.list_entries(agent.name, path, int(customer_id))
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}
        return {"status": "success", "data": data}

    def create_folder(
        self, agent_id: str, customer_id: int, folder_name: str, parent_path: str = ""
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        rel = f"{parent_path}/{folder_name}".strip("/") if parent_path else folder_name.strip()
        try:
            storage.create_folder(agent.name, rel, int(customer_id))
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}
        return {"status": "success", "message": "Folder created.", "data": {"path": rel, "type": "folder"}}

    def upload_files(
        self,
        agent_id: str,
        customer_id: int,
        files: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        if not files:
            return {"status": "error", "message": "No files to upload.", "http_status": 400}

        saved: list[dict[str, Any]] = []
        try:
            for relative_path, data in files:
                saved.append(
                    storage.save_file(agent.name, relative_path, data, int(customer_id))
                )
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}

        drive_uploads: list[dict[str, Any]] = []
        drive_errors: list[str] = []
        drive_configured = False
        try:
            from app.backend.utils import google_drive_storage as drive_storage
            from app.backend.utils.school_drive_config import load_agents_global_drive_config

            load_agents_global_drive_config(self.db)
            drive_configured = True
            for relative_path, data in files:
                try:
                    drive_uploads.append(
                        drive_storage.upload_to_agent_folder(
                            db=self.db,
                            customer_id=int(customer_id),
                            agent_name=agent.name,
                            relative_path=relative_path,
                            data=data,
                        )
                    )
                except Exception as exc:
                    drive_errors.append(f"{relative_path}: {exc}")
        except ValueError:
            # Drive de Agentes no configurado: solo disco local.
            pass
        except Exception as exc:
            drive_errors.append(str(exc))

        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()

        message = f"{len(saved)} file(s) uploaded."
        if drive_configured and drive_errors and not drive_uploads:
            message = (
                f"{len(saved)} archivo(s) en servidor local, pero ninguno llegó a Google Drive. "
                f"{drive_errors[0]}"
            )
        elif drive_configured and drive_errors:
            message = (
                f"{len(saved)} archivo(s) locales; Drive: {len(drive_uploads)} ok, "
                f"{len(drive_errors)} con error. {drive_errors[0]}"
            )
        elif drive_configured and drive_uploads:
            message = (
                f"{len(saved)} archivo(s) subidos (local + Drive: {len(drive_uploads)})."
            )

        return {
            "status": "success",
            "message": message,
            "data": {
                "uploaded": saved,
                "totalFiles": storage.count_files(agent.name, int(customer_id)),
                "driveUploads": drive_uploads,
                "driveErrors": drive_errors,
                "driveConfigured": drive_configured,
            },
        }

    def delete_file(self, agent_id: str, customer_id: int, path: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id, customer_id)
        if not agent:
            return {"status": "error", "message": "Agent not found.", "http_status": 404}
        try:
            storage.delete_entry(agent.name, path, int(customer_id))
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}

        drive_result: dict[str, Any] | None = None
        drive_error: str | None = None
        try:
            from app.backend.utils import google_drive_storage as drive_storage
            from app.backend.utils.school_drive_config import load_agents_global_drive_config

            load_agents_global_drive_config(self.db)
            drive_result = drive_storage.delete_from_agent_folder(
                db=self.db,
                customer_id=int(customer_id),
                agent_name=agent.name,
                relative_path=path,
            )
        except ValueError:
            # Drive no configurado: solo borrado local.
            pass
        except Exception as exc:
            drive_error = str(exc)

        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()

        message = "Deleted."
        if drive_error:
            message = f"Eliminado en local; Drive falló: {drive_error}"
        elif drive_result and not drive_result.get("skipped"):
            message = "Eliminado en local y en Google Drive."
        elif drive_result and drive_result.get("skipped"):
            message = "Eliminado en local (no estaba en Drive o ya no existía)."

        return {
            "status": "success",
            "message": message,
            "data": {
                "drive": drive_result,
                "driveError": drive_error,
            },
        }
