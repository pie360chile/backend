"""Texto del informe psicopedagógico (u otro doc) desde la ficha/carpeta del estudiante."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models.pie_core import FolderModel
from app.backend.utils import agents_file_context as file_ctx

# Catálogo: Informe de Evaluación Psicopedagógica
PSYCHOPED_CATALOG_DOCUMENT_ID = 27

_PSYCHOPED_PATH_MARKERS = (
    "psicopedag",
    "evaluacion_psico",
    "evaluación_psico",
    "evaluacion psic",
    "informe_psico",
    "informe psico",
    "2__e_",
    "psychopedagog",
)

_MAX_CHARS = 18_000


def _student_files_dir() -> Path:
    base = Path(settings.files_dir or "files")
    # Producción suele montar FILES_DIR; en local también existe files/system/students
    candidates = [
        base / "system" / "students",
        Path("files") / "system" / "students",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def files_context_has_student_psychoped(
    files_block: str,
    *,
    student_name: str | None = None,
    student_rut: str | None = None,
) -> bool:
    """True si el contexto de Files del agente ya trae un psicopedagógico usable del caso."""
    text = (files_block or "").strip()
    if len(text) < 400:
        return False
    low = text.lower()
    if not any(m in low for m in _PSYCHOPED_PATH_MARKERS):
        # A veces el nombre del archivo no trae "psico" pero el cuerpo sí
        body_hints = (
            "evaluación psicopedagógica",
            "evaluacion psicopedagogica",
            "informe de evaluación psicopedagógica",
            "área pedagógica",
            "area pedagogica",
            "instrumentos aplicados",
        )
        if not any(h in low for h in body_hints):
            return False

    name_tokens = [
        t
        for t in re.split(r"[^\wáéíóúñü]+", (student_name or "").lower(), flags=re.IGNORECASE)
        if len(t) >= 3
    ]
    if name_tokens:
        hits = sum(1 for t in name_tokens if t in low)
        if hits >= min(2, len(name_tokens)):
            return True

    rut_digits = re.sub(r"\D", "", student_rut or "")
    if len(rut_digits) >= 8:
        compact = re.sub(r"\D", "", low)
        if rut_digits in compact or rut_digits[:-1] in compact:
            return True

    # Hay marcadores de psicopedagógico y el bloque es grande: asumir usable
    return len(text) >= 2500 and any(m in low for m in _PSYCHOPED_PATH_MARKERS)


def resolve_student_folder_file_path(filename: str) -> Path | None:
    name = (filename or "").strip().replace("\\", "/").split("/")[-1]
    if not name or name in {".", ".."}:
        return None
    path = _student_files_dir() / name
    if path.is_file():
        return path
    return None


def get_latest_folder_file(
    db: Session,
    *,
    student_id: int,
    document_id: int = PSYCHOPED_CATALOG_DOCUMENT_ID,
) -> FolderModel | None:
    """
    Devuelve el ÚLTIMO archivo de la ficha para ese estudiante + document_id.

    Criterio (si hay varios): más reciente por updated_date / added_date,
    luego version_id, luego id.
    """
    from sqlalchemy import func

    q = db.query(FolderModel).filter(
        FolderModel.student_id == int(student_id),
        FolderModel.document_id == int(document_id),
        FolderModel.file.isnot(None),
        FolderModel.file != "",
    )
    try:
        q = q.filter(FolderModel.deleted_date.is_(None))
    except Exception:
        pass

    # Último cargado/creado: fecha de actualización o alta; desempate por versión e id
    last_touch = func.coalesce(FolderModel.updated_date, FolderModel.added_date)
    return q.order_by(
        last_touch.desc(),
        FolderModel.version_id.desc(),
        FolderModel.id.desc(),
    ).first()


def extract_student_catalog_document_text(
    db: Session,
    *,
    student_id: int,
    document_id: int = PSYCHOPED_CATALOG_DOCUMENT_ID,
    max_chars: int = _MAX_CHARS,
) -> dict[str, Any]:
    """
    Lee el ÚLTIMO archivo de la ficha (folders) para student_id + document_id.
    Si hay varias versiones, usa la más reciente (fecha / version_id).
    Por defecto document_id=27 (informe psicopedagógico).
    """
    if int(student_id) < 1:
        return {"ok": False, "message": "student_id inválido.", "http_status": 400}

    row = get_latest_folder_file(db, student_id=int(student_id), document_id=int(document_id))
    if not row or not (row.file or "").strip():
        return {
            "ok": False,
            "message": (
                f"No hay archivo en la ficha del estudiante para document_id={int(document_id)} "
                "(sube el informe psicopedagógico en la carpeta del estudiante)."
            ),
            "http_status": 404,
        }

    filename = str(row.file).strip()
    path = resolve_student_folder_file_path(filename)
    if not path:
        return {
            "ok": False,
            "message": f"El archivo «{filename}» figura en la ficha pero no está en disco.",
            "http_status": 404,
            "filename": filename,
            "folderId": row.id,
            "versionId": row.version_id,
        }

    try:
        content = (file_ctx.extract_file_text(path) or "").strip()
    except Exception as exc:
        return {
            "ok": False,
            "message": f"No se pudo leer el archivo de la ficha: {exc}",
            "http_status": 500,
            "filename": filename,
        }

    if not content:
        return {
            "ok": False,
            "message": f"El archivo «{filename}» no tiene texto extraíble.",
            "http_status": 404,
            "filename": filename,
        }

    truncated = False
    if len(content) > max_chars:
        content = content[:max_chars] + "\n… [contenido truncado]"
        truncated = True

    added = getattr(row, "added_date", None)
    updated = getattr(row, "updated_date", None)
    when = updated or added
    when_s = when.isoformat(sep=" ", timespec="seconds") if hasattr(when, "isoformat") else str(when or "")

    header = (
        "INFORME PSICOPEDAGÓGICO DESDE FICHA DEL ESTUDIANTE "
        f"(document_id={int(document_id)}, archivo={filename}, "
        f"versión={row.version_id}, último_cargado={when_s or 'n/d'}). "
        "Es la ÚLTIMA versión en la ficha (si había varias). "
        "No estaba (o no era usable) en Files del agente; usa ESTE texto como fuente principal "
        "de los campos narrativos del Informe a la Familia.\n\n"
    )
    return {
        "ok": True,
        "message": "Último documento de la ficha leído.",
        "studentId": int(student_id),
        "documentId": int(document_id),
        "folderId": int(row.id),
        "versionId": int(row.version_id or 1),
        "filename": filename,
        "downloadUrl": f"/files/system/students/{filename}",
        "addedDate": added.isoformat() if hasattr(added, "isoformat") else None,
        "updatedDate": updated.isoformat() if hasattr(updated, "isoformat") else None,
        "truncated": truncated,
        "chars": len(content),
        "context": header + content,
        "text": content,
        "isLatest": True,
    }


def maybe_build_ficha_psychoped_block(
    db: Session,
    *,
    student_id: int | None,
    document_id: int | None,
    files_block: str,
    student_name: str | None = None,
    student_rut: str | None = None,
    force: bool = False,
) -> str:
    """
    Si Files no trae psicopedagógico del estudiante, inyecta el de la ficha (doc 27).

    Se usa cuando:
    - force=True, o
    - document_id es Informe a la Familia (7), o
    - document_id aún no está definido (None) — típico del agente Familia.
    """
    if not student_id or int(student_id) < 1:
        return ""

    doc = int(document_id) if document_id is not None else None
    # Solo para Informe a la Familia: el psicopedagógico se lee desde ficha como fuente.
    # Si el agente ES el psicopedagógico (doc 27), no inyectar la ficha como input.
    allow = force or doc == 7
    if not allow:
        return ""

    if files_context_has_student_psychoped(
        files_block,
        student_name=student_name,
        student_rut=student_rut,
    ):
        return ""

    result = extract_student_catalog_document_text(
        db,
        student_id=int(student_id),
        document_id=PSYCHOPED_CATALOG_DOCUMENT_ID,
    )
    if not result.get("ok"):
        return ""
    return str(result.get("context") or "").strip()
