"""CRUD de agentes configurables (PIE360 Agent v2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.documents_class import DocumentsClass
from app.backend.db.models.agent_v2 import AgentV2Model
from app.backend.db.models.agent_v2_documents import AgentV2DocumentTemplateModel
from app.backend.utils import agent_v2_storage as storage
from app.backend.utils.agent_v2_template_inspector import (
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


def _maybe_refresh_template_fields(db: Session, row: AgentV2DocumentTemplateModel) -> None:
    """Re-inspecciona plantillas guardadas sin campos (p. ej. solo content controls)."""
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


def _serialize_template(row: AgentV2DocumentTemplateModel) -> dict[str, Any]:
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


def _serialize(agent: AgentV2Model, db: Session) -> dict[str, Any]:
    updated = agent.updated_at or agent.created_at
    templates = (
        db.query(AgentV2DocumentTemplateModel)
        .filter(AgentV2DocumentTemplateModel.agent_id == agent.id)
        .count()
    )
    return {
        "id": agent.id,
        "name": agent.name,
        "roleInstructions": agent.role_instructions,
        "updatedAt": updated.isoformat() if updated else None,
        "fileCount": storage.count_files(agent.name),
        "documentTemplateCount": templates,
    }


class AgentV2Class:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_agent(self, agent_id: str) -> AgentV2Model | None:
        return (
            self.db.query(AgentV2Model)
            .filter(AgentV2Model.id == agent_id)
            .first()
        )

    def list_agents(self) -> dict[str, Any]:
        rows = (
            self.db.query(AgentV2Model)
            .order_by(AgentV2Model.updated_at.desc())
            .all()
        )
        return {"status": "success", "data": [_serialize(row, self.db) for row in rows]}

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        return {"status": "success", "data": _serialize(agent, self.db)}

    def update_agent(self, agent_id: str, name: str, role_instructions: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}

        clean_name = name.strip()
        if not clean_name:
            return {"status": "error", "message": "El nombre es obligatorio.", "http_status": 400}

        duplicate = (
            self.db.query(AgentV2Model)
            .filter(AgentV2Model.name == clean_name, AgentV2Model.id != agent_id)
            .first()
        )
        if duplicate:
            return {
                "status": "error",
                "message": "Ya existe un agente con ese nombre.",
                "http_status": 409,
            }

        old_name = agent.name
        agent.name = clean_name
        agent.role_instructions = role_instructions.strip()
        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(agent)

        if old_name != clean_name:
            try:
                storage.rename_agent_folder(old_name, clean_name)
            except ValueError:
                pass

        return {"status": "success", "message": "Agente guardado.", "data": _serialize(agent, self.db)}

    def create_agent(self, name: str, role_instructions: str) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            return {"status": "error", "message": "El nombre es obligatorio.", "http_status": 400}

        existing = (
            self.db.query(AgentV2Model)
            .filter(AgentV2Model.name == clean_name)
            .first()
        )
        if existing:
            return {
                "status": "error",
                "message": "Ya existe un agente con ese nombre.",
                "http_status": 409,
            }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        agent = AgentV2Model(
            id=uuid.uuid4().hex,
            name=clean_name,
            role_instructions=role_instructions.strip(),
            created_at=now,
            updated_at=now,
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        storage.agent_folder(agent.name)
        return {"status": "success", "message": "Agente creado.", "data": _serialize(agent, self.db)}

    def list_catalog_documents(self) -> dict[str, Any]:
        docs_class = DocumentsClass(self.db)
        sections: list[dict[str, Any]] = []
        seen: set[int] = set()
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
                        "sectionLabel": SECTION_LABELS.get(row.get("document_type_id") or section_id, label),
                        "careerTypeId": row.get("career_type_id"),
                    }
                )
            if items:
                sections.append({"sectionId": section_id, "sectionLabel": label, "documents": items})
        return {"status": "success", "data": sections}

    def list_document_templates(self, agent_id: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        rows = (
            self.db.query(AgentV2DocumentTemplateModel)
            .filter(AgentV2DocumentTemplateModel.agent_id == agent_id)
            .order_by(AgentV2DocumentTemplateModel.document_name.asc())
            .all()
        )
        for row in rows:
            _maybe_refresh_template_fields(self.db, row)
        return {"status": "success", "data": [_serialize_template(row) for row in rows]}

    def save_document_template(
        self,
        agent_id: str,
        document_id: int,
        document_name: str,
        data: bytes,
        filename: str,
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}

        lower = (filename or "").lower()
        if lower.endswith(".docx"):
            format_type = "docx"
        elif lower.endswith(".pdf"):
            format_type = "pdf"
        else:
            return {
                "status": "error",
                "message": "Solo se permiten plantillas .docx o .pdf.",
                "http_status": 400,
            }

        try:
            saved = storage.save_document_template(agent.name, document_id, data, format_type)
            absolute = (storage.files_dir() / saved["relativePath"]).resolve()
            inspection = inspect_template_fields(absolute, format_type)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = (
            self.db.query(AgentV2DocumentTemplateModel)
            .filter(
                AgentV2DocumentTemplateModel.agent_id == agent_id,
                AgentV2DocumentTemplateModel.document_id == document_id,
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
            row = AgentV2DocumentTemplateModel(
                agent_id=agent_id,
                document_id=document_id,
                document_name=document_name.strip() or f"Documento {document_id}",
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
        return {"status": "success", "message": "Plantilla guardada.", "data": payload}

    def delete_agent(self, agent_id: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        self.db.query(AgentV2DocumentTemplateModel).filter(
            AgentV2DocumentTemplateModel.agent_id == agent_id
        ).delete()
        storage.delete_agent_folder(agent.name)
        self.db.delete(agent)
        self.db.commit()
        return {"status": "success", "message": "Agente eliminado."}

    def list_files(self, agent_id: str, path: str = "") -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        try:
            data = storage.list_entries(agent.name, path)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}
        return {"status": "success", "data": data}

    def create_folder(self, agent_id: str, folder_name: str, parent_path: str = "") -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        rel = f"{parent_path}/{folder_name}".strip("/") if parent_path else folder_name.strip()
        try:
            storage.create_folder(agent.name, rel)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}
        return {"status": "success", "message": "Carpeta creada.", "data": {"path": rel, "type": "folder"}}

    def upload_files(
        self,
        agent_id: str,
        files: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        if not files:
            return {"status": "error", "message": "No hay archivos para subir.", "http_status": 400}

        saved: list[dict[str, Any]] = []
        try:
            for relative_path, data in files:
                saved.append(storage.save_file(agent.name, relative_path, data))
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}

        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return {
            "status": "success",
            "message": f"{len(saved)} archivo(s) subido(s).",
            "data": {"uploaded": saved, "totalFiles": storage.count_files(agent.name)},
        }

    def delete_file(self, agent_id: str, path: str) -> dict[str, Any]:
        agent = self._get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}
        try:
            storage.delete_entry(agent.name, path)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "http_status": 400}
        agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        return {"status": "success", "message": "Eliminado."}
