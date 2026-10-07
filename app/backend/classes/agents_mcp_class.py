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
                "formFilled": bool(result.get("formFilled")),
                "familyReportId": result.get("familyReportId"),
                "psychopedEvaluationId": result.get("psychopedEvaluationId"),
            },
        }

    def search_agent_files(
        self,
        *,
        agent_id: str,
        customer_id: int,
        query: str,
        student_rut: str | None = None,
    ) -> dict[str, Any]:
        """Retrieval barato sobre textos derivados del agente (_derived/)."""
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}

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

        from app.backend.utils import agents_derived_storage as derived

        text, file_count = derived.build_selective_files_context(
            agent.name or "",
            query=query or "",
            student_rut=student_rut,
            customer_id=int(customer_id),
        )
        return {
            "status": "success",
            "message": "Búsqueda en archivos del agente.",
            "data": {
                "agentId": agent.id,
                "agentName": agent.name,
                "fileCount": file_count,
                "query": (query or "").strip(),
                "studentRut": (student_rut or "").strip() or None,
                "context": text,
            },
        }

    def get_student_psychopedagogical_evaluation(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Lee el último informe psicopedagógico de la carpeta del estudiante
        (tabla folders, document_id 27). El informe a la familia lo usa siempre.
        """
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}
        if int(student_id) < 1:
            return {"status": "error", "message": "student_id inválido.", "http_status": 400}

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

        from app.backend.utils.agents_student_folder_context import (
            PSYCHOPED_CATALOG_DOCUMENT_ID,
            extract_student_catalog_document_text,
        )

        doc_id = int(document_id) if document_id and int(document_id) > 0 else PSYCHOPED_CATALOG_DOCUMENT_ID
        result = extract_student_catalog_document_text(
            self.db,
            student_id=int(student_id),
            document_id=doc_id,
        )
        if not result.get("ok"):
            return {
                "status": "error",
                "message": result.get("message") or "No se encontró el documento en la ficha.",
                "http_status": int(result.get("http_status") or 404),
                "data": {
                    "agentId": agent.id,
                    "studentId": int(student_id),
                    "documentId": doc_id,
                    "filename": result.get("filename"),
                },
            }
        return {
            "status": "success",
            "message": result.get("message") or "OK",
            "data": {
                "agentId": agent.id,
                "agentName": agent.name,
                "studentId": result.get("studentId"),
                "documentId": result.get("documentId"),
                "folderId": result.get("folderId"),
                "versionId": result.get("versionId"),
                "filename": result.get("filename"),
                "downloadUrl": result.get("downloadUrl"),
                "truncated": result.get("truncated"),
                "chars": result.get("chars"),
                "context": result.get("context"),
                "source": "student_folder",
                "isLatest": True,
                "addedDate": result.get("addedDate"),
                "updatedDate": result.get("updatedDate"),
            },
        }

    def get_student_psychopedagogical_form_answers(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        school_id: int | None = None,
        period_year: int | None = None,
        student_name: str | None = None,
        student_rut: str | None = None,
    ) -> dict[str, Any]:
        """
        Lee respuestas de formularios dinámicos (Inf. Eval. Psicopedagógica → Formularios).

        Usar cuando el cuestionario/Excel en Files del agente no trae la fila del estudiante.
        """
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}
        if int(student_id) < 1:
            return {"status": "error", "message": "student_id inválido.", "http_status": 400}

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

        from app.backend.utils.agents_dynamic_form_context import (
            collect_dynamic_form_answers_payload,
        )

        payload = collect_dynamic_form_answers_payload(
            self.db,
            student_id=int(student_id),
            student_name=student_name,
            student_rut=student_rut,
            school_id=int(school_id) if school_id else None,
            period_year=int(period_year) if period_year else None,
        )
        if not payload:
            return {
                "status": "error",
                "message": "No hay respuestas de formulario para este estudiante.",
                "http_status": 404,
                "data": {
                    "agentId": agent.id,
                    "studentId": int(student_id),
                    "source": "dynamic_forms",
                },
            }
        return {
            "status": "success",
            "message": "Respuestas de formulario obtenidas.",
            "data": {
                "agentId": agent.id,
                "agentName": agent.name,
                **payload,
            },
        }

    def get_student_school_history(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        school_id: int | None = None,
        period_year: int | None = None,
        student_name: str | None = None,
        student_rut: str | None = None,
    ) -> dict[str, Any]:
        """
        Lee la anamnesis (historia escolar y apoyo familiar) y el formulario del apoderado.

        Esa evidencia es la fuente de `school_history_background`.
        """
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}
        if int(student_id) < 1:
            return {"status": "error", "message": "student_id inválido.", "http_status": 400}

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

        from app.backend.utils.agents_school_history_context import (
            build_school_history_context,
        )

        payload = build_school_history_context(
            self.db,
            student_id=int(student_id),
            student_name=student_name,
            student_rut=student_rut,
            school_id=int(school_id) if school_id else None,
            period_year=int(period_year) if period_year else None,
        )
        if not payload:
            return {
                "status": "error",
                "message": "No hay anamnesis ni formulario del apoderado para este estudiante.",
                "http_status": 404,
                "data": {
                    "agentId": agent.id,
                    "studentId": int(student_id),
                    "source": "anamnesis_and_guardian_form",
                },
            }
        return {
            "status": "success",
            "message": "Historia escolar y antecedentes familiares obtenidos.",
            "data": {
                "agentId": agent.id,
                "agentName": agent.name,
                **payload,
            },
        }

    def get_saved_psychopedagogical_evaluation(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        student_name: str | None = None,
        student_rut: str | None = None,
    ) -> dict[str, Any]:
        """Lee la ficha psychopedagogical_evaluation_info guardada al generar el informe."""
        aid = (agent_id or "").strip()
        if not aid:
            return {"status": "error", "message": "agent_id es requerido.", "http_status": 400}
        if int(customer_id) < 1:
            return {"status": "error", "message": "customer_id inválido.", "http_status": 400}
        if int(student_id) < 1:
            return {"status": "error", "message": "student_id inválido.", "http_status": 400}

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

        from app.backend.utils.agents_saved_psychoped_context import (
            build_saved_psychoped_context,
        )

        payload = build_saved_psychoped_context(
            self.db,
            student_id=int(student_id),
            student_name=student_name,
            student_rut=student_rut,
        )
        if not payload:
            return {
                "status": "error",
                "message": "No hay informe psicopedagógico guardado en la ficha de este estudiante.",
                "http_status": 404,
                "data": {
                    "agentId": agent.id,
                    "studentId": int(student_id),
                    "source": "psychopedagogical_evaluation_info",
                },
            }
        return {
            "status": "success",
            "message": "Informe psicopedagógico guardado en la ficha.",
            "data": {
                "agentId": agent.id,
                "agentName": agent.name,
                **payload,
            },
        }

    def create_document(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        fields: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Genera con la plantilla cargada en Documentos del agente.

        Asociación obligatoria:
        - document_id = tipo de documento PIE360 (catálogo)
        - plantilla .docx/.pdf subida en Agente → Documentos para ese document_id
        - al generar: rellena Word/PDF + guarda en carpeta del estudiante
          + persiste el formulario asociado a ese tipo
            (familia → family_reports; psicoped → psychopedagogical_evaluation_info)
        """
        from app.backend.utils.agents_code_guard import strip_html_tags

        clean_fields: dict[str, Any] = {}
        for key, val in (fields or {}).items():
            if isinstance(val, str):
                clean_fields[str(key)] = strip_html_tags(val)
            else:
                clean_fields[str(key)] = val
        fields = clean_fields

        aid = (agent_id or "").strip()
        template = (
            self.db.query(AgentDocumentTemplateModel)
            .filter(
                AgentDocumentTemplateModel.agent_id == aid,
                AgentDocumentTemplateModel.document_id == int(document_id),
            )
            .first()
        )
        if not template:
            return {
                "status": "error",
                "message": (
                    f"No hay plantilla en Documentos del agente para document_id={int(document_id)}. "
                    "Sube el modelo (.docx/.pdf) asociado a ese tipo de documento."
                ),
                "http_status": 404,
            }

        store = self.store_data(
            agent_id=agent_id,
            customer_id=customer_id,
            student_id=student_id,
            document_id=document_id,
            fields=fields,
            meta=meta,
        )
        if store.get("status") == "error":
            return store
        save_data = store.get("data") or {}
        save_id = save_data.get("id")
        if not save_id:
            return {
                "status": "error",
                "message": "No se pudo crear el registro pending.",
                "http_status": 500,
            }
        generated = self.generate_save(
            agent_id=agent_id,
            customer_id=customer_id,
            save_id=int(save_id),
        )
        if generated.get("status") == "error":
            return generated
        data = generated.get("data") or {}
        save = data.get("save") or {}

        msg = (
            f"Documento «{template.document_name}» (document_id={template.document_id}) "
            "generado con su plantilla, guardado en el estudiante y pendiente de sincronización "
            "automática con Google Drive."
        )

        return {
            "status": "success",
            "message": msg,
            "data": {
                "save": save,
                "responseFiles": data.get("responseFiles") or [],
                "formFilled": bool(
                    data.get("formFilled")
                    or data.get("familyReportId")
                    or data.get("psychopedEvaluationId")
                    or save.get("status") == "generated"
                ),
                "documentId": int(template.document_id),
                "documentName": template.document_name,
                "familyReportId": data.get("familyReportId"),
                "psychopedEvaluationId": data.get("psychopedEvaluationId"),
                "googleDrive": {"status": "pending"},
                "googleDriveError": None,
            },
        }

    def save_document_to_google_drive(
        self,
        *,
        agent_id: str,
        customer_id: int,
        student_id: int,
        document_id: int,
        save_id: int | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Sube el documento generado a Drive:
        Liceo > Año > Curso > RUT numérico > RUT_Tipo de documento.ext
        """
        from pathlib import Path

        from app.backend.core.config import settings
        from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
        from app.backend.db.models import FolderModel

        aid = (agent_id or "").strip()
        if not aid or int(customer_id) < 1 or int(student_id) < 1 or int(document_id) < 1:
            return {
                "status": "error",
                "message": "agent_id, customer_id, student_id y document_id son obligatorios.",
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

        # Localizar archivo generado
        local_name = (file_name or "").strip() or None
        if save_id is not None and int(save_id) > 0:
            row = (
                self.db.query(AgentsMcpSaveModel)
                .filter(
                    AgentsMcpSaveModel.id == int(save_id),
                    AgentsMcpSaveModel.agent_id == aid,
                    AgentsMcpSaveModel.customer_id == int(customer_id),
                    AgentsMcpSaveModel.student_id == int(student_id),
                )
                .first()
            )
            if not row:
                return {"status": "error", "message": "Save no encontrado.", "http_status": 404}
            if row.status != "generated" or not (row.file_name or "").strip():
                return {
                    "status": "error",
                    "message": "El documento aún no está generado. Usa create_document primero.",
                    "http_status": 409,
                }
            local_name = (row.file_name or "").strip()
            document_id = int(row.document_id or document_id)

        if not local_name:
            return {
                "status": "error",
                "message": "No hay archivo local para subir (file_name / save_id).",
                "http_status": 400,
            }

        local_path = Path(settings.files_dir) / "system" / "students" / Path(local_name).name
        if not local_path.is_file():
            return {
                "status": "error",
                "message": f"No se encontró el archivo generado en el servidor: {local_path.name}",
                "http_status": 404,
            }

        folder = (
            self.db.query(FolderModel)
            .filter(
                FolderModel.student_id == int(student_id),
                FolderModel.document_id == int(document_id),
                FolderModel.file == local_path.name,
                FolderModel.deleted_date.is_(None),
            )
            .order_by(FolderModel.version_id.desc())
            .first()
        )
        if not folder:
            return {
                "status": "error",
                "message": "El archivo generado no está registrado en la carpeta del estudiante.",
                "http_status": 409,
            }

        sync = StudentDriveSyncClass(self.db)
        job = sync.enqueue(
            folder_id=int(folder.id),
            student_id=int(student_id),
            document_id=int(document_id),
            file_path=f"system/students/{local_path.name}",
        )
        result = sync.process(int(job.id))
        if not result.get("ok"):
            return {
                "status": "error",
                "message": (
                    "El documento quedó guardado y pendiente de reintento en Google Drive: "
                    f"{result.get('message')}"
                ),
                "http_status": 503,
            }
        payload = result.get("data") or {}
        return {
            "status": "success",
            "message": f"Documento subido a Google Drive: {payload.get('drive_path')}",
            "data": payload,
        }

    def _prompt_content_rules_for_document(self, document_id: int | None) -> list[str]:
        """Reglas de contenido según tipo de documento (familia vs psicopedagógico)."""
        doc = int(document_id) if document_id is not None else None
        if doc == 27:
            return [
                "Contenido obligatorio del INFORME DE EVALUACIÓN PSICOPEDAGÓGICA (document_id=27):",
                "- AUTORIDAD DE CAMPOS: usa SOLO los nombres listados en «Plantillas configuradas»",
                "  (tags de la plantilla Word cargada en Agente → Documentos). Esos son los únicos",
                "  nombres válidos en el JSON `fields`.",
                "- NO inventes ni uses nombres del formulario web si la plantilla tiene otros",
                "  (ej. no uses `diagnosis` si la plantilla pide `diagnostic`; no uses `social_name`",
                "  / `age` si pide `student_social_name` / `student_age`; no uses `admission_type`",
                "  si pide `admission_type_1`/`_2`/`_3`; no uses `pedagogical_scale_*` si la",
                "  plantilla no los lista).",
                "- Rellena los campos NARRATIVOS de ESA plantilla con texto respaldado en los",
                "  ARCHIVOS del agente / texto derivado (cuestionarios, pautas, anamnesis, etc.).",
                "- REDACCIÓN HUMANA (obligatorio): está PROHIBIDO copiar etiquetas de escala",
                "  del cuestionario: no escribas «LOGRADO», «EN PROCESO», «REQUIERE APOYO»,",
                "  «NO OBSERVADO» ni las pongas entre paréntesis. Tradúcelas a prosa",
                "  profesional: describe cómo se desempeña ESTE estudiante (qué logra con",
                "  autonomía, dónde necesita mediación, con qué frecuencia, en qué tipo de",
                "  tarea). El informe debe leerse como evaluación cualitativa, no como pauta.",
                "- DETALLE DEL CASO: nombra al estudiante, ancla cada párrafo a SUS",
                "  características (memoria de trabajo, planificación, impulsos, lenguaje,",
                "  socioemocional, motricidad, autonomía, sensorial). Evita textos genéricos",
                "  que servirían para cualquier alumno. No copies los títulos largos del",
                "  cuestionario (listas entre paréntesis) como relleno.",
                "- APODERADO Y PROFESIONAL (obligatorio si hay más de una fuente):",
                "  Las respuestas de formulario se distinguen por quién contesta:",
                "  Apoderado o Profesional. No las llames Fonoaudiología, Terapia",
                "  Ocupacional ni otra especialidad clínica.",
                "  El informe DEBE integrar TODAS: en análisis/síntesis/conclusión di",
                "  qué observó el apoderado y qué observó el profesional (si hay varios",
                "  profesionales, nómbralos por su nombre), qué coincide y qué difiere.",
                "  Prohibido redactar como si hubiera una sola pauta.",
                "  En `instruments_applied` lista el cuestionario del apoderado y el del",
                "  profesional por separado.",
                "- EXTENSIÓN: cada narrativo DETALLADO (aprox. 120–220 palabras; 3 a 6 oraciones).",
                "  Prohibido una sola frase corta si hay evidencia en los archivos.",
                "- INSTRUMENTOS: si el campo existe en la plantilla, lista con guion (-), un ítem",
                "  por línea.",
                "- SUGERENCIAS / RECOMENDACIONES (suggestions_to_school, suggestions_to_classroom_team,",
                "  suggestions_to_student, suggestions_to_family, other_suggestions):",
                "  formato OBLIGATORIO lista con guion medio, un ítem por línea, así:",
                "  - Primera recomendación concreta…",
                "  - Segunda recomendación concreta…",
                "  Prohibido numerar (1.- 2.-) o un solo párrafo. Cada ítem específico al estudiante.",
                "- ANÁLISIS / SÍNTESIS / CONCLUSIÓN: completa cada campo narrativo",
                "  que aparezca en la lista de la plantilla cuando haya evidencia o datos PIE360.",
                "- FECHAS (evaluación, emisión de diagnóstico, nacimiento y cualquier",
                "  campo fecha): formato obligatorio **dd-mm-YYYY** (ej. 07-04-2026).",
                "  No uses 2026-04-07, 07/04/2026 ni «07 de abril de 2026».",
                "- DATOS DEL SISTEMA: si el cuestionario no trae identificación, curso,",
                "  establecimiento, NEE, fechas, profesional o apoderado, USA el bloque",
                "  «DATOS DEL SISTEMA PIE360» / ficha (equivalente a consultar MCP/ficha).",
                "  No dejes esos campos vacíos si están en ese bloque.",
                "- Checkboxes / tipos de ingreso / escalas de la PLANTILLA Word: solo si",
                "  aparecen en la lista de tags; no uses las escalas del Excel en el narrativo.",
                "- NO uses campos de Informe a la Familia (agreements, collaborative_work,",
                "  supports de hogar).",
                "- Si en ESTE turno hay bloque ARCHIVOS / Excel / texto derivado del estudiante,",
                "  ÚSALO: no digas que faltan cuestionarios si las respuestas están en el contexto.",
                "- Si aparece el bloque «RESPUESTAS DEL FORMULARIO PIE360», ESO es la",
                "  evaluación de este RUT (MCP get_student_psychopedagogical_form_answers).",
                "  Está filtrado por student_id. No importa que el Excel, el Reporte",
                "  Interactivo o la nómina no traigan este RUT o traigan otros.",
                "  Prohibido decir que no hay antecedentes de evaluación.",
                "  Prohibido dejar los campos narrativos en blanco: redacta análisis,",
                "  síntesis, instrumentos y sugerencias desde esas respuestas",
                "  (traduce LOGRADO/EN PROCESO/REQUIERE APOYO a prosa).",
                "  Si hay Excel Y formulario, o respuestas de apoderado y de profesional,",
                "  integra ambas fuentes en el narrativo. No las renombres como especialidad.",
                "- HISTORIA ESCOLAR (`school_history_background`): usa el bloque",
                "  «HISTORIA ESCOLAR Y ANTECEDENTES FAMILIARES»",
                "  (MCP get_student_school_history: anamnesis + formulario del apoderado).",
                "  Redacta uno o dos párrafos. Empieza con el nombre, el curso y el",
                "  establecimiento si constan. Sigue con «De acuerdo con los antecedentes",
                "  aportados por su familia, …» e integra solo hechos de ese bloque:",
                "  jardín, escuela de lenguaje, repitencia, colegios, apoyos, tareas en casa,",
                "  intereses, descripción familiar y medicación.",
                "  Prohibido inventar cualquiera de esos hechos si el bloque no los trae.",
                "  Las escalas LOGRADO / EN PROCESO / REQUIERE APOYO / NO OBSERVADO",
                "  no son historia escolar: no las uses en este campo.",
                "  Si el bloque no trae trayectoria ni antecedentes familiares, el campo va \"\".",
                "- NO dejes el informe solo con datos personales (nombre, RUT, curso, fechas).",
                "- No inventes evaluaciones que no estén en Files, formulario MCP ni ficha PIE360.",
                "- FIDELIDAD DOCUMENTAL: nunca presentes como hecho algo que no esté en los archivos;",
                "  nunca mezcles antecedentes entre estudiantes distintos.",
                "- REDACCIÓN: español latino, formal e inclusivo; sin lenguaje estigmatizante;",
                "  en TDA/TEA/DIL describe cualitativamente (sin puntuaciones numéricas inventadas).",
                "  Diagnósticos documentados con Mayúscula Inicial En Cada Palabra;",
                "  «años»/«meses» en minúscula. Tipografía la define la plantilla PIE360.",
                "- Tú solo entregas fields; PIE360 genera el archivo.",
            ]

        # Default / Informe a la Familia (7) u otros
        return [
            "Contenido obligatorio del informe:",
            "- Debes rellenar los campos NARRATIVOS de la plantilla (motivos, instrumentos,",
            "  diagnóstico general, fortalezas, apoyos, acuerdos, etc.) con texto respaldado",
            "  en los ARCHIVOS del agente / texto derivado.",
            "- EXTENSIÓN: cada campo narrativo debe ir DETALLADO (aprox. 80–180 palabras;",
            "  2 a 5 oraciones). Prohibido responder con una sola frase corta si hay evidencia",
            "  en los archivos. Integra hallazgos concretos (áreas, instrumentos, ejemplos).",
            "- SEPARACIÓN: fortalezas ≠ necesidades. No mezcles dificultades dentro del",
            "  campo de fortalezas; las necesidades van en su campo de apoyos/necesidades.",
            "- INSTRUMENTOS APLICADOS (campo `applied_instruments`):",
            "  lista con guion (-), **un instrumento por línea**. Ejemplo:",
            "  - Cuestionario de Observación Psicopedagógica en el Contexto Escolar",
            "  - Entrevista a la familia / Anamnesis",
            "  - Pauta de Evaluación y Observación Pedagógica del Estudiante en el Contexto Escolar",
            "  Prohibido juntarlos en un solo párrafo separados solo por comas.",
            "- TRABAJO COLABORATIVO EN LA ESCUELA (campo `collaborative_work`):",
            "  «Trabajo colaborativo y apoyos educativos para la inclusión» en aula regular,",
            "  sala de recursos, comunidad educativa, articulación entre profesionales, etc.",
            "  Formato: lista 1) 2) 3) 4)… o guiones; mínimo 4 ítems extensos (40–80 palabras).",
            "  NUNCA pongas aquí apoyos del hogar.",
            "  ESPECÍFICO AL CASO (obligatorio): cada ítem debe nombrar la dificultad o área",
            "  documentada del estudiante (p. ej. cálculo/DEA, resolución de problemas,",
            "  funciones ejecutivas, comprensión lectora, escritura, motivación) y la acción",
            "  concreta (estrategia, material, frecuencia, asignatura). Prohibido rellenar con",
            "  solo «coordinación semanal», «reuniones periódicas», «trabajo en aula» o",
            "  «articulación con convivencia» sin vincularlo a SU problema de aprendizaje.",
            "  Un texto que sirva para cualquier alumno = incorrecto; reescríbelo anclado al expediente.",
            "- APOYOS EN EL HOGAR (campo `supports` / `home_based_description` / `home_support`):",
            "  Solo lo que la familia debe hacer en casa (autoestima, asistencia regular,",
            "  apoyo escolar en el hogar, apoyo afectivo, hábitos, higiene, participación,",
            "  controles de salud / redes externas, etc.). Formato: lista 1) 2) 3) 4)…;",
            "  mínimo 4 ítems extensos. NUNCA pongas aquí aula regular, sala de recursos,",
            "  adecuaciones curriculares ni trabajo de la educadora diferencial en la escuela.",
            "  Cada ítem debe vincularse a su dificultad real (p. ej. matemática en casa,",
            "  rutina de estudio por pasos, refuerzo afectivo ante frustración).",
            "- ACUERDOS Y COMPROMISOS (campo `agreements` — escuela y familia):",
            "  Exactamente 3 viñetas (1 escuela, 2 familia, 3 compartida).",
            "  Cada ítem MUY extenso y detallado (aprox. 60–120 palabras) y ESPECÍFICO al",
            "  estudiante: cita sus dificultades/fortalezas documentadas (p. ej. cálculo,",
            "  resolución de problemas, funciones ejecutivas, comprensión lectora, motivación).",
            "  Prohibido texto genérico tipo «apoyos psicopedagógicos», «adecuaciones»,",
            "  «comunicación fluida» sin decir QUÉ harán concreto para ESE caso.",
            "  Cada viñeta debe nombrar al estudiante y vincular la acción a su necesidad.",
            "  No uses mínimo 5: son exactamente 3, una por cada parte.",
            "- INFORME DE FAMILIA: Contrasta con la normativa del agente",
            "  («Normativa Informe para la familia.pdf») si está en el contexto derivado.",
            "  PIE360 aplica la plantilla: no inventes secciones ni omitas campos.",
            "- FECHAS DE AVANCES (`evaluation_date_1`…): solo la fecha, sin notas. Si el informe",
            "  es antes de julio → 4 fechas: Junio año actual, Dic. año actual, Junio año+1,",
            "  Dic. año+1. Si es después de julio → Junio año+1 y Dic. año+1. Fecha de",
            "  evaluación del informe = fecha del psicopedagógico del mismo estudiante si existe.",
            "- DATOS COMPLEMENTARIOS: las fuentes son el TEXTO DERIVADO / JSON del contexto",
            "  (no se «abre» el Excel). Educadora que entrega (`professional_*`) = nómina PIE",
            "  del estudiante; si no está, déjala en blanco. Apoderado que recibe",
            "  (`received_person_*`) = reporte interactivo de la sede.",
            "- RUT DEL ESTUDIANTE: solo el que escribió el usuario o el de PIE360, coincidencia",
            "  exacta. PROHIBIDO completar o corregir dígitos con la nómina o el reporte",
            "  (p. ej. no pases 3.012.603-8 a 23.012.603-8). Si no coincide, el RUT es",
            "  incorrecto: no identifiques a nadie ni envíes JSON fields.",
            "  Curso y RUT de plantilla: usa ficha PIE360 si el estudiante ya está identificado.",
            "- PSICOPEDAGÓGICO OBLIGATORIO: PIE360 inyecta la ficha guardada en la base",
            "  (bloque «INFORME PSICOPEDAGÓGICO GUARDADO EN PIE360»,",
            "  MCP get_saved_psychopedagogical_evaluation) y el último Word de la",
            "  carpeta (MCP get_student_psychopedagogical_evaluation).",
            "  Esa ficha es la fuente principal de los narrativos del Informe a la Familia.",
            "  Prohibido ignorarla o decir que no hay antecedentes de evaluación",
            "  si el bloque trae párrafos.",
            "  Si Files, el Reporte Interactivo o la nómina traen otros RUT, no uses esas",
            "  filas para este estudiante: manda el psicopedagógico de la ficha.",
            "- Si en ESTE turno hay bloque ARCHIVOS / texto derivado del estudiante, úsalo",
            "  solo como complemento y solo si el RUT coincide. No sustituye al",
            "  psicopedagógico de la ficha.",
            "- NO dejes el informe solo con datos personales (nombre, RUT, curso, fechas).",
            "  Eso no es un informe completo.",
            "- Si un dato no está en los archivos, ese campo va \"\" (vacío). No inventes.",
            "- FIDELIDAD DOCUMENTAL: nunca presentes como hecho algo que no esté en los archivos;",
            "  nunca mezcles antecedentes entre estudiantes distintos. Si hay varios estudiantes",
            "  en los archivos, sepáralos y un informe por cada uno. Sin RUT/ficha claros,",
            "  pide el RUT; no adivines ni completes el número. Si el RUT no existe en PIE360,",
            "  di que es incorrecto y no generes el documento.",
            "- ANÁLISIS DE ANTECEDENTES: con una sola fuente, igual elabora con rigor. Con varias,",
            "  cruza informantes (coincidencias, diferencias, complementariedades). Si hay",
            "  discrepancias, expónlas con profesionalismo; no elijas una versión al azar.",
            "  En historia escolar / `enter_evaluation`: solo cuestionario familiar; no uses",
            "  fórmulas administrativas tipo «NEEP año 2» / «año 2»; diagnóstico solo si está",
            "  respaldado en los archivos.",
            "- REDACCIÓN: español latino, formal e inclusivo; sin lenguaje estigmatizante;",
            "  necesidades en perspectiva funcional/contextual; sin diagnósticos clínicos no",
            "  documentados; en TDA/TEA/DIL describe cualitativamente (sin puntuaciones",
            "  numéricas). Diagnósticos documentados con Mayúscula Inicial En Cada Palabra;",
            "  «años»/«meses» en minúscula. No escribas tipografía (Arial) en los fields:",
            "  eso lo define la plantilla PIE360.",
            "- No digas errores del sistema (plantilla, disco, etc.) salvo que el propio",
            "  contexto te lo indique en ESTE turno: tú solo entregas fields; PIE360 genera el archivo.",
            "- Si en un mensaje anterior falló la plantilla pero ahora el usuario pide generar de nuevo,",
            "  vuelve a enviar el JSON fields completo (con narrativo); no asumas que sigue fallando.",
        ]

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
        """Instrucciones: plantilla Documentos ↔ document_id ↔ formulario."""
        q = self.db.query(AgentDocumentTemplateModel).filter(
            AgentDocumentTemplateModel.agent_id == agent.id
        )
        all_templates = q.order_by(AgentDocumentTemplateModel.document_name.asc()).all()
        template_ids = {int(t.document_id) for t in all_templates}
        requested = int(document_id) if document_id is not None and int(document_id) > 0 else None
        if requested and requested in template_ids:
            templates = [t for t in all_templates if int(t.document_id) == requested]
        else:
            templates = all_templates

        # El tipo lo define la plantilla del agente, no un document_id ajeno (p. ej. URL de Familia).
        if len(template_ids) == 1:
            effective_doc = next(iter(template_ids))
        elif requested and requested in template_ids:
            effective_doc = requested
        else:
            aname = (agent.name or "").lower()
            if "psicoped" in aname:
                effective_doc = 27
            elif "familia" in aname:
                effective_doc = 7
            else:
                effective_doc = requested

        lines: list[str] = [
            "Documentos del agente (regla fija):",
            "- Cada MODELO se carga en Agente → Documentos.",
            "- Cada modelo está asociado a UN tipo de documento PIE360 (document_id)",
            "  y a SU formulario (al generar se rellena ese formulario).",
            "- create_document SIEMPRE usa la plantilla de ese document_id (no inventes otra).",
            "",
        ]
        lines.extend(self._prompt_content_rules_for_document(effective_doc))
        lines.extend(
            [
                "",
                "Fuentes (regla dura):",
                "- PROHIBIDO buscar en internet, navegar la web o usar buscadores.",
                "- Solo archivos del agente / texto derivado, el chat, datos PIE360 del contexto",
                "  y tools MCP (get_student_psychopedagogical_form_answers,",
                "  get_student_school_history).",
                "- PROHIBIDO HTML y código (CSS, JS, Python, SQL, etc.). Solo prosa en español.",
                "  El único JSON permitido es el bloque fields para generar el documento.",
                "- Solo atiendes PIE Chile (informes, estudiantes, NEE, Decreto 170, PIE360).",
                "  Si el tema no es de PIE Chile, no respondas el contenido: indica que solo",
                "  contestas consultas de PIE Chile.",
                "",
                "Flujo:",
                "1) Lee tu ROL y los ARCHIVOS/JSON del agente / formulario MCP / anamnesis / ficha.",
                "2) Si el usuario pide generar el informe/documento:",
                "   a) PRIORIDAD ABSOLUTA: entrega YA el bloque JSON completo con TODOS los",
                "      campos de la plantilla (mismos nombres EXACTOS; narrativos incluidos).",
                "      El JSON debe ir PRIMERO o, como máximo, tras 1–2 oraciones cortas.",
                "```json",
                '{"fields": {"nombre_campo": "texto completo", ...}}',
                "```",
                "   b) PROHIBIDO quedarte en una intro anunciando el informe sin enviar el JSON",
                "      (p. ej. «A continuación se redacta el contenido de cada campo…»).",
                "      Eso NO genera el documento. Sin `fields` el informe no se crea.",
                "   c) El contenido largo va DENTRO de cada campo del JSON, no como prosa previa.",
                "3) Si solo es una consulta (sin generar documento), responde en prosa sin JSON.",
                "   El servidor ejecuta create_document → Word/PDF con esa plantilla →",
                "   carpeta del estudiante → formulario → Google Drive",
                "   (Liceo/Año/Curso/RUT/RUT_TipoDocumento.ext).",
                "",
                f"IDs: agent_id={agent.id}, customer_id={int(customer_id)}",
                f"MCP create_document URL: {mcp_url}",
            ]
        )
        if student_id:
            lines.append(f"- student_id del contexto: {int(student_id)}")
        if student_rut:
            lines.append(f"- student_rut del contexto: {student_rut}")
        lines.extend(
            [
                "",
                "RUT (regla dura):",
                "- Usa el RUT tal como lo escribió el usuario o el que entrega PIE360.",
                "- PROHIBIDO completar, prefijar, acortar o 'corregir' un RUT (p. ej. no pases",
                "  de 3.012.603-8 a 23.012.603-8 porque 'parece' el de la nómina).",
                "- Si el número no coincide exactamente con un estudiante de PIE360, no identifiques",
                "  a nadie, no redactes el informe y no envíes JSON fields.",
            ]
        )
        if not student_id and not student_rut:
            lines.extend(
                [
                    "",
                    "Identificación del estudiante:",
                    "- Si NO hay student_id ni RUT en el contexto, NO generes el informe ni",
                    "  envíes el JSON fields. Pregunta el RUT con dígito verificador",
                    "  (ej. 12.345.678-9) para identificar al estudiante con certeza.",
                    "- El nombre solo no basta (puede haber homónimos).",
                ]
            )
        if effective_doc:
            lines.append(
                f"- document_id prioritario (tipo + formulario + plantilla): {int(effective_doc)}"
            )

        lines.append("")
        lines.append(
            "Plantillas configuradas (document_id → CAMPOS OBLIGATORIOS del Word;"
            " usa exactamente estos nombres en `fields`):"
        )
        if not templates:
            if effective_doc == 27:
                lines.append(
                    "- (ninguna plantilla subida aún) Sube el modelo en Agente → Documentos"
                    " (document_id=27). Sin plantilla no hay lista de campos fiable."
                )
            else:
                lines.append(
                    "- (ninguna) Sube el modelo en Documentos del agente asociado al tipo de documento."
                )
        else:
            for tpl in templates:
                fields = fields_from_json(tpl.detected_fields)
                lines.append(
                    f"- document_id={tpl.document_id} | «{tpl.document_name}» | {tpl.format_type}:"
                )
                if fields:
                    for field in fields:
                        lines.append(f"  · {field}")
                    lines.append(
                        "  → El JSON `fields` debe usar ESTOS nombres (no los del formulario web)."
                    )
                else:
                    lines.append("  · (sin campos detectados en la plantilla)")
                example_fields = {f: f"<{f}>" for f in (fields[:8] if fields else ["campo"])}
                lines.append(
                    "  Ejemplo: "
                    + json.dumps({"fields": example_fields}, ensure_ascii=False)
                )

        return "\n".join(lines)
