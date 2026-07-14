"""MCP store_data: persist agent field payloads and generate documents."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.agents_document_service import generate_and_save_document
from app.backend.db.models.agent import AgentModel
from app.backend.db.models.agents_documents import AgentDocumentTemplateModel
from app.backend.db.models.agents_mcp_saves import AgentsMcpSaveModel
from app.backend.utils.agents_template_inspector import fields_from_json


def _serialize_save(row: AgentsMcpSaveModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "agentId": row.agent_id,
        "customerId": row.customer_id,
        "studentId": row.student_id,
        "documentId": row.document_id,
        "origin": row.origin,
        "status": row.status,
        "folderId": row.folder_id,
        "downloadUrl": row.download_url,
        "fileName": row.file_name,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _parse_since(since: str | None) -> datetime | None:
    if not since or not str(since).strip():
        return None
    raw = str(since).strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        return None


class AgentsMcpClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def store_data(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        fields: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}
        if int(student_id) < 1:
            return {"status": "error", "message": "student_id inválido.", "http_status": 400}
        if int(document_id) < 1:
            return {"status": "error", "message": "document_id inválido.", "http_status": 400}
        if not isinstance(fields, dict) or not fields:
            return {
                "status": "error",
                "message": "fields debe ser un objeto con al menos un campo.",
                "http_status": 400,
            }

        agent = (
            self.db.query(AgentModel)
            .filter(
                AgentModel.id == aid,
                AgentModel.customer_id == int(customer_id),
            )
            .first()
        )
        if not agent:
            return {"status": "error", "message": "Agente no encontrado.", "http_status": 404}

        payload = {
            "fields": {str(k): ("" if v is None else v) for k, v in fields.items()},
            "meta": meta if isinstance(meta, dict) else {},
        }
        now = datetime.utcnow()
        row = AgentsMcpSaveModel(
            agent_id=aid,
            customer_id=int(customer_id),
            student_id=int(student_id),
            document_id=int(document_id),
            payload_json=json.dumps(payload, ensure_ascii=False),
            origin="agent",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return {
            "status": "success",
            "message": "Datos guardados (pending).",
            "data": _serialize_save(row),
        }

    def list_pending(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int | None = None,
        document_id: int | None = None,
        since: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        q = self.db.query(AgentsMcpSaveModel).filter(
            AgentsMcpSaveModel.agent_id == (agent_id or "").strip(),
            AgentsMcpSaveModel.customer_id == int(customer_id),
            AgentsMcpSaveModel.origin == "agent",
            AgentsMcpSaveModel.status == "pending",
        )
        if student_id is not None and int(student_id) > 0:
            q = q.filter(AgentsMcpSaveModel.student_id == int(student_id))
        if document_id is not None and int(document_id) > 0:
            q = q.filter(AgentsMcpSaveModel.document_id == int(document_id))
        since_dt = _parse_since(since)
        if since_dt is not None:
            q = q.filter(AgentsMcpSaveModel.created_at >= since_dt)
        rows = (
            q.order_by(AgentsMcpSaveModel.created_at.asc())
            .limit(max(1, min(int(limit or 10), 50)))
            .all()
        )
        return {"status": "success", "data": [_serialize_save(r) for r in rows]}

    def generate_save(
        self,
        *,
        agent_id: str,
        customer_id: int,
        save_id: int,
    ) -> dict[str, Any]:
        row = (
            self.db.query(AgentsMcpSaveModel)
            .filter(
                AgentsMcpSaveModel.id == int(save_id),
                AgentsMcpSaveModel.agent_id == (agent_id or "").strip(),
                AgentsMcpSaveModel.customer_id == int(customer_id),
                AgentsMcpSaveModel.origin == "agent",
            )
            .first()
        )
        if not row:
            return {"status": "error", "message": "Save no encontrado.", "http_status": 404}
        if row.status == "generated" and row.download_url:
            return {
                "status": "success",
                "message": "Documento ya generado.",
                "data": {
                    "save": _serialize_save(row),
                    "responseFiles": [
                        {
                            "id": str(row.folder_id or row.id),
                            "name": row.file_name or "",
                            "documentName": None,
                            "downloadUrl": row.download_url,
                        }
                    ],
                },
            }
        if row.status != "pending":
            return {
                "status": "error",
                "message": f"Save en estado '{row.status}', no se puede generar.",
                "http_status": 409,
            }

        template = (
            self.db.query(AgentDocumentTemplateModel)
            .filter(
                AgentDocumentTemplateModel.agent_id == row.agent_id,
                AgentDocumentTemplateModel.document_id == row.document_id,
            )
            .first()
        )
        if not template:
            row.status = "error"
            row.updated_at = datetime.utcnow()
            self.db.commit()
            return {
                "status": "error",
                "message": "Plantilla del documento no encontrada para este agente.",
                "http_status": 404,
            }

        try:
            payload = json.loads(row.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        fields_raw = payload.get("fields") if isinstance(payload, dict) else {}
        if not isinstance(fields_raw, dict):
            fields_raw = {}
        replacements = {str(k): "" if v is None else str(v) for k, v in fields_raw.items()}

        result = generate_and_save_document(
            self.db, template, int(row.student_id), replacements
        )
        if result.get("status") == "error":
            row.status = "error"
            row.updated_at = datetime.utcnow()
            self.db.commit()
            return {
                "status": "error",
                "message": result.get("message") or "Error al generar documento.",
                "http_status": 400,
                "data": {"save": _serialize_save(row)},
            }

        filename = result.get("filename") or ""
        download_url = result.get("downloadUrl") or (
            f"/files/system/students/{filename}" if filename else None
        )
        row.status = "generated"
        row.folder_id = result.get("folderId")
        row.file_name = filename or None
        row.download_url = download_url
        row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)

        return {
            "status": "success",
            "message": "Documento generado.",
            "data": {
                "save": _serialize_save(row),
                "responseFiles": [
                    {
                        "id": str(row.folder_id or row.id),
                        "name": row.file_name or filename,
                        "documentName": result.get("documentName"),
                        "downloadUrl": row.download_url,
                    }
                ],
            },
        }

    def build_store_data_prompt_block(
        self,
        *,
        agent: AgentModel,
        customer_id: int,
        document_id: int | None = None,
        student_id: int | None = None,
        student_rut: str | None = None,
        mcp_url: str,
    ) -> str:
        """Instrucciones MCP + campos de plantilla para el trigger Workspace."""
        q = self.db.query(AgentDocumentTemplateModel).filter(
            AgentDocumentTemplateModel.agent_id == agent.id
        )
        if document_id is not None and int(document_id) > 0:
            preferred = q.filter(
                AgentDocumentTemplateModel.document_id == int(document_id)
            ).all()
            templates = preferred or q.order_by(
                AgentDocumentTemplateModel.document_name.asc()
            ).all()
        else:
            templates = q.order_by(AgentDocumentTemplateModel.document_name.asc()).all()

        lines: list[str] = [
            "Herramienta MCP store_data:",
            f"- URL MCP: {mcp_url}",
            "- Tool: store_data",
            "- Auth: parámetro secret = MCP_SECRET del connector (mismo secret que Authorization Bearer).",
            "- Cuando tengas todos los campos del informe, llama store_data (no inventes IDs).",
            "- Campos: agent_id, customer_id, student_id, document_id, fields (objeto nombre→valor), meta opcional.",
            f"- agent_id fijo: {agent.id}",
            f"- customer_id fijo: {int(customer_id)}",
        ]
        if student_id:
            lines.append(f"- student_id del contexto: {int(student_id)}")
        if student_rut:
            lines.append(f"- student_rut del contexto: {student_rut}")
        if document_id:
            lines.append(f"- document_id prioritario: {int(document_id)}")

        lines.append("")
        lines.append("Esquema fields según plantilla(s):")
        if not templates:
            lines.append("- (sin plantillas cargadas en el agente)")
        else:
            for tpl in templates:
                fields = fields_from_json(tpl.detected_fields)
                lines.append(
                    f"- document_id={tpl.document_id} ({tpl.document_name}, {tpl.format_type}):"
                )
                if fields:
                    for field in fields:
                        lines.append(f"  · {field}")
                else:
                    lines.append("  · (sin campos detectados)")
                example_fields = {f: f"<{f}>" for f in (fields[:8] if fields else ["campo"])}
                example = {
                    "agent_id": agent.id,
                    "customer_id": int(customer_id),
                    "student_id": int(student_id or 0) or "<student_id>",
                    "document_id": int(tpl.document_id),
                    "fields": example_fields,
                }
                lines.append(
                    "  Ejemplo JSON: "
                    + json.dumps(example, ensure_ascii=False)
                )

        return "\n".join(lines)
