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
          + persiste el formulario asociado a ese tipo (ej. familia → family_reports)
        """
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
        return {
            "status": "success",
            "message": (
                f"Documento «{template.document_name}» (document_id={template.document_id}) "
                "generado con su plantilla, guardado en el estudiante y formulario actualizado."
            ),
            "data": {
                "save": save,
                "responseFiles": data.get("responseFiles") or [],
                "formFilled": bool(save.get("status") == "generated"),
                "documentId": int(template.document_id),
                "documentName": template.document_name,
                "familyReportId": None,
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
        """Instrucciones: plantilla Documentos ↔ document_id ↔ formulario."""
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
            "Documentos del agente (regla fija):",
            "- Cada MODELO se carga en Agente → Documentos.",
            "- Cada modelo está asociado a UN tipo de documento PIE360 (document_id)",
            "  y a SU formulario (al generar se rellena ese formulario).",
            "- create_document SIEMPRE usa la plantilla de ese document_id (no inventes otra).",
            "",
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
            "  (`received_person_*`) = reporte interactivo de la sede. Prioriza reporte",
            "  interactivo ante discrepancias de identificación. Completa RUT/curso si",
            "  aparecen de forma verificable; no los omitas.",
            "- Si en ESTE turno hay bloque ARCHIVOS / texto derivado del estudiante, ÚSALO:",
            "  no digas que «no se adjuntó» el documento de evaluación ni que faltan antecedentes.",
            "- NO dejes el informe solo con datos personales (nombre, RUT, curso, fechas).",
            "  Eso no es un informe completo.",
            "- Si un dato no está en los archivos, ese campo va \"\" (vacío). No inventes.",
            "- FIDELIDAD DOCUMENTAL: nunca presentes como hecho algo que no esté en los archivos;",
            "  nunca mezcles antecedentes entre estudiantes distintos. Si hay varios estudiantes",
            "  en los archivos, sepáralos y un informe por cada uno. Sin RUT/ficha claros,",
            "  pide confirmación/RUT antes de generar el documento final nominado.",
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
            "",
            "Flujo:",
            "1) Lee tu ROL y los ARCHIVOS/JSON del agente.",
            "2) Redacta un resumen breve en el chat.",
            "3) Si hay que generar el documento, al FINAL un bloque JSON con TODOS los campos",
            "   de la plantilla de ese document_id (narrativos incluidos):",
            "```json",
            '{"fields": {"nombre_campo": "texto completo", ...}}',
            "```",
            "   El servidor ejecuta create_document → Word/PDF con esa plantilla →",
            "   carpeta del estudiante → formulario del tipo de documento → link en el chat.",
            "",
            f"IDs: agent_id={agent.id}, customer_id={int(customer_id)}",
            f"MCP create_document URL: {mcp_url}",
        ]
        if student_id:
            lines.append(f"- student_id del contexto: {int(student_id)}")
        if student_rut:
            lines.append(f"- student_rut del contexto: {student_rut}")
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
        if document_id:
            lines.append(
                f"- document_id prioritario (tipo + formulario + plantilla): {int(document_id)}"
            )

        lines.append("")
        lines.append("Plantillas configuradas (document_id → campos del formulario/plantilla):")
        if not templates:
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
                else:
                    lines.append("  · (sin campos detectados en la plantilla)")
                example_fields = {f: f"<{f}>" for f in (fields[:8] if fields else ["campo"])}
                lines.append(
                    "  Ejemplo: "
                    + json.dumps({"fields": example_fields}, ensure_ascii=False)
                )

        return "\n".join(lines)
