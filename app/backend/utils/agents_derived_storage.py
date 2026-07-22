"""Derivados de archivos del agente: texto plano + meta para retrieval barato en tokens."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.backend.utils import agents_file_context as file_ctx
from app.backend.utils import agents_storage as storage

DERIVED_DIR_NAME = "_derived"
PREVIEW_CHARS = 400
# Presupuesto de contexto de archivos en el chat (~3–4k tokens).
CHAT_BUDGET_CHARS = 14_000
CHAT_INDEX_MAX_FILES = 80
CHUNK_SIZE = 900
CHUNK_OVERLAP = 100
MAX_CHUNKS_RETURNED = 16

_STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "lo",
    "los",
    "para",
    "por",
    "que",
    "se",
    "un",
    "una",
    "y",
    "o",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
}

# Palabras del pedido de chat que no identifican al estudiante.
_QUERY_NOISE = _STOPWORDS | {
    "haz",
    "hacer",
    "genera",
    "generar",
    "completa",
    "completar",
    "rellena",
    "rellenar",
    "informe",
    "informes",
    "documento",
    "documentos",
    "familia",
    "estudiante",
    "alumna",
    "alumno",
    "word",
    "docx",
    "pdf",
    "por",
    "favor",
    "necesito",
    "quiero",
    "puedes",
    "con",
    "todos",
    "campos",
    "narrativos",
}


def derived_root(agent_name: str, customer_id: int | None = None) -> Path:
    return storage.agent_folder(agent_name, customer_id) / DERIVED_DIR_NAME


def _derived_paths(
    agent_name: str, relative_path: str, customer_id: int | None = None
) -> tuple[Path, Path]:
    rel = storage._safe_relative_path(relative_path)
    if not rel:
        raise ValueError("relative_path is required.")
    root = derived_root(agent_name, customer_id)
    txt = (root / f"{rel}.txt").resolve()
    meta = (root / f"{rel}.meta.json").resolve()
    if not str(txt).startswith(str(root.resolve())) or not str(meta).startswith(
        str(root.resolve())
    ):
        raise ValueError("Derived path not allowed.")
    return txt, meta


def write_derived_for_file(
    agent_name: str,
    relative_path: str,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """Extrae texto del original y escribe .txt + .meta.json bajo _derived/."""
    rel = storage._safe_relative_path(relative_path)
    original = storage.resolve_target(agent_name, rel, customer_id)
    txt_path, meta_path = _derived_paths(agent_name, rel, customer_id)
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta: dict[str, Any] = {
        "path": rel,
        "name": Path(rel).name,
        "ok": False,
        "chars": 0,
        "preview": "",
        "extracted_at": now,
        "error": None,
    }

    if not original.is_file():
        meta["error"] = "Original not found."
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    try:
        text = (file_ctx.extract_file_text(original) or "").strip()
        if not text:
            meta["error"] = "No extractable text."
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if txt_path.exists():
                txt_path.unlink()
            return meta
        txt_path.write_text(text, encoding="utf-8")
        meta["ok"] = True
        meta["chars"] = len(text)
        meta["preview"] = text[:PREVIEW_CHARS].replace("\n", " ").strip()
        meta["error"] = None
    except Exception as exc:
        meta["error"] = str(exc)[:500]
        if txt_path.exists():
            txt_path.unlink()

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def delete_derived(
    agent_name: str, relative_path: str, customer_id: int | None = None
) -> None:
    """Borra sidecars de un archivo o de una carpeta entera bajo _derived/."""
    rel = storage._safe_relative_path(relative_path)
    if not rel:
        return
    root = derived_root(agent_name, customer_id)
    if not root.exists():
        return

    txt_path, meta_path = _derived_paths(agent_name, rel, customer_id)
    if txt_path.is_file():
        txt_path.unlink()
    if meta_path.is_file():
        meta_path.unlink()

    folder = (root / rel).resolve()
    if str(folder).startswith(str(root.resolve())) and folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)

    prefix = f"{rel}/"
    for meta in list(root.rglob("*.meta.json")):
        try:
            key = meta.relative_to(root).as_posix()
            if not key.endswith(".meta.json"):
                continue
            source_rel = key[: -len(".meta.json")]
            if source_rel == rel or source_rel.startswith(prefix):
                txt_candidate = Path(str(meta)[: -len(".meta.json")] + ".txt")
                if txt_candidate.is_file():
                    txt_candidate.unlink()
                if meta.is_file():
                    meta.unlink()
        except Exception:
            continue


def list_derived_metas(
    agent_name: str, customer_id: int | None = None
) -> list[dict[str, Any]]:
    root = derived_root(agent_name, customer_id)
    if not root.exists():
        return []
    items: list[dict[str, Any]] = []
    for meta_path in sorted(root.rglob("*.meta.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("path"):
                items.append(data)
        except Exception:
            continue
    return items


def _tokenize(text: str) -> set[str]:
    raw = re.findall(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", (text or "").lower())
    return {t for t in raw if t not in _STOPWORDS}


def _chunk_text(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= CHUNK_SIZE:
            chunks.append(para)
            continue
        start = 0
        while start < len(para):
            end = min(len(para), start + CHUNK_SIZE)
            chunks.append(para[start:end])
            if end >= len(para):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def retrieve_relevant_chunks(
    agent_name: str,
    *,
    query: str = "",
    student_rut: str | None = None,
    student_name: str | None = None,
    customer_id: int | None = None,
    budget_chars: int = CHAT_BUDGET_CHARS,
) -> dict[str, Any]:
    """Índice corto + top chunks por overlap de keywords / RUT / nombre (sin embeddings)."""
    metas = list_derived_metas(agent_name, customer_id)
    ok_metas = [m for m in metas if m.get("ok")]
    index_paths = [str(m.get("path") or "") for m in ok_metas[:CHAT_INDEX_MAX_FILES]]

    query_tokens = _tokenize(query)
    name_tokens = _tokenize(student_name or "")
    # Nombre de ficha + posibles apellidos/nombres en el mensaje («isabella diaz»).
    query_tokens |= name_tokens
    person_tokens = {
        t for t in (name_tokens | query_tokens) if t not in _QUERY_NOISE and len(t) >= 3
    }

    rut_norm = file_ctx._normalize_rut(student_rut or "")
    if len(rut_norm) >= 8:
        query_tokens.add(rut_norm.lower())
        if len(rut_norm) > 1:
            query_tokens.add(rut_norm[:-1].lower())

    scored: list[tuple[float, str, str]] = []
    root = derived_root(agent_name, customer_id)

    _GENERIC_PATH_MARKERS = (
        "ejemplo_",
        "ejemplo-",
        "formato_",
        "formato-",
        "glosario",
        "decreto",
        "orientaciones",
        "cartilla",
        "normativa",
        "base_institucional",
    )

    for meta in ok_metas:
        rel = str(meta.get("path") or "")
        rel_l = rel.lower()
        txt_path = (root / f"{rel}.txt").resolve()
        if not txt_path.is_file():
            continue
        try:
            text = txt_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        file_bonus = 0.0
        path_tokens = _tokenize(rel.replace("/", " ").replace("_", " ").replace("-", " "))
        if person_tokens and (person_tokens & path_tokens):
            # p.ej. mensaje «isabella diaz» → 2__E_ISABELLA_DIAZ.docx
            file_bonus += 120.0
        if person_tokens:
            text_l = text.lower()
            hits = sum(1 for t in person_tokens if t in text_l)
            if hits:
                file_bonus += 40.0 + (10.0 * hits)
        if rut_norm and rut_norm in file_ctx._normalize_rut(text):
            file_bonus += 80.0
        elif any(marker in rel_l for marker in file_ctx._INTERACTIVE_REPORT_MARKERS):
            file_bonus += 5.0

        if any(marker in rel_l for marker in _GENERIC_PATH_MARKERS):
            # Bajar prioridad de plantillas/ejemplos cuando el pedido nombra a alguien.
            file_bonus -= 25.0 if (person_tokens or rut_norm) else 0.0

        for chunk in _chunk_text(text):
            chunk_tokens = _tokenize(chunk)
            overlap = len(query_tokens & chunk_tokens) if query_tokens else 0
            if not query_tokens:
                score = file_bonus + (3.0 if file_bonus else 1.0)
            else:
                score = float(overlap) + file_bonus
                if rut_norm and rut_norm in file_ctx._normalize_rut(chunk):
                    score += 30.0
                if person_tokens and (person_tokens & chunk_tokens):
                    score += 20.0
            # Con estudiante identificado, no descartar chunks del archivo del estudiante
            # aunque el mensaje sea genérico («genera el informe»).
            if score <= 0 and query_tokens and file_bonus < 50:
                continue
            if score <= 0:
                continue
            scored.append((score, rel, chunk))

    scored.sort(key=lambda x: (-x[0], x[1]))

    sections: list[str] = []
    used = 0
    used_chunks = 0
    seen: set[str] = set()
    for _score, rel, chunk in scored:
        key = f"{rel}:{chunk[:80]}"
        if key in seen:
            continue
        seen.add(key)
        block = f"### Archivo: {rel}\n\n{chunk.strip()}"
        if used + len(block) > budget_chars:
            remaining = budget_chars - used
            if remaining > 200:
                sections.append(block[:remaining] + "\n… [truncado]")
                used = budget_chars
            break
        sections.append(block)
        used += len(block)
        used_chunks += 1
        if used_chunks >= MAX_CHUNKS_RETURNED:
            break

    index_line = ", ".join(index_paths) if index_paths else "(sin textos derivados)"
    header = (
        "ARCHIVOS DEL AGENTE (índice + trozos relevantes; presupuesto bajo de tokens).\n"
        f"Índice ({len(ok_metas)} con texto): {index_line}\n"
        f"Trozos incluidos: {used_chunks} (~{used} caracteres).\n"
        "Usa SOLO estos datos como fuente documental; no inventes contenido de archivos no listados.\n"
        "Si hay un archivo del estudiante (nombre/RUT en el nombre o en el texto), "
        "prioridad absoluta para los campos narrativos del informe.\n"
    )
    body = (
        ("\n\n---\n\n".join(sections))
        if sections
        else "(Sin trozos relevantes para este mensaje.)"
    )
    return {
        "text": header + "\n" + body,
        "file_count": len(ok_metas),
        "chunk_count": used_chunks,
        "chars": used,
        "index": index_paths,
    }


def build_selective_files_context(
    agent_name: str,
    *,
    query: str = "",
    student_rut: str | None = None,
    student_name: str | None = None,
    customer_id: int | None = None,
) -> tuple[str, int]:
    """(texto para prompt, n archivos indexados)."""
    parts: list[str] = []
    if student_rut and student_rut.strip():
        rut_block, _ = file_ctx.extract_spreadsheet_hint_for_rut(
            agent_name, student_rut, customer_id
        )
        if rut_block:
            if len(rut_block) > 4_000:
                rut_block = rut_block[:4_000] + "\n… [RUT hint truncado]"
            parts.append(rut_block)

    remaining = max(2_000, CHAT_BUDGET_CHARS - sum(len(p) for p in parts))
    retrieved = retrieve_relevant_chunks(
        agent_name,
        query=query,
        student_rut=student_rut,
        student_name=student_name,
        customer_id=customer_id,
        budget_chars=remaining,
    )
    parts.append(retrieved["text"])
    return "\n\n".join(parts).strip(), int(retrieved.get("file_count") or 0)


def rebuild_all_derived(
    agent_name: str, customer_id: int | None = None
) -> dict[str, Any]:
    """Regenera _derived para todos los archivos de contexto del agente."""
    paths = file_ctx.list_all_context_file_paths(agent_name, customer_id)
    root = storage.agent_folder(agent_name, customer_id)
    ok = 0
    errors: list[str] = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        meta = write_derived_for_file(agent_name, rel, customer_id)
        if meta.get("ok"):
            ok += 1
        else:
            errors.append(f"{rel}: {meta.get('error') or 'failed'}")
    return {
        "ok": True,
        "processed": len(paths),
        "derivedOk": ok,
        "derivedErrors": errors,
    }
