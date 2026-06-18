"""Extracción, chunking e indexación de documentos por agente."""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from sqlalchemy.orm import Session

from app.backend.db.models import AgentFileChunkModel, AgentFileModel

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
MIN_TERM_LEN = 3
DEFAULT_TOP_K = 5


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return unescape(re.sub(r"\s+", " ", text)).strip()


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md", ".csv"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        import fitz

        doc = fitz.open(file_path)
        try:
            return "\n".join(page.get_text("text") for page in doc)
        finally:
            doc.close()

    if suffix == ".docx":
        from docx import Document

        document = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

    if suffix == ".xlsx":
        import pandas as pd

        sheets = pd.read_excel(file_path, sheet_name=None)
        parts: list[str] = []
        for sheet_name, frame in sheets.items():
            parts.append(f"Hoja: {sheet_name}\n{frame.fillna('').to_string(index=False)}")
        return "\n\n".join(parts)

    return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def delete_file_chunks(db: Session, agent_id: str, file_id: str) -> None:
    db.query(AgentFileChunkModel).filter(
        AgentFileChunkModel.agent_id == agent_id,
        AgentFileChunkModel.file_id == file_id,
    ).delete(synchronize_session=False)


def index_agent_file(
    db: Session,
    agent_id: str,
    file_id: str,
    file_path: Path,
    display_name: str,
) -> int:
    delete_file_chunks(db, agent_id, file_id)
    raw_text = extract_text_from_file(file_path)
    if not raw_text.strip():
        return 0

    header = f"Archivo: {display_name}\n"
    chunks = chunk_text(raw_text)
    for index, content in enumerate(chunks):
        db.add(
            AgentFileChunkModel(
                agent_id=agent_id,
                file_id=file_id,
                chunk_index=index,
                content=f"{header}{content}",
            )
        )
    return len(chunks)


def _query_terms(query: str) -> list[str]:
    return [term for term in re.findall(r"\w+", query.lower()) if len(term) >= MIN_TERM_LEN]


def search_agent_knowledge(
    db: Session,
    agent_id: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    terms = _query_terms(query)
    if not terms:
        return []

    chunks = (
        db.query(AgentFileChunkModel, AgentFileModel.display_name)
        .join(AgentFileModel, AgentFileModel.id == AgentFileChunkModel.file_id)
        .filter(AgentFileChunkModel.agent_id == agent_id)
        .all()
    )

    scored: list[tuple[float, AgentFileChunkModel, str]] = []
    for chunk, display_name in chunks:
        haystack = chunk.content.lower()
        score = 0.0
        for term in terms:
            if term in haystack:
                score += haystack.count(term) * 2
            if any(term in word for word in haystack.split()):
                score += 1
        if score > 0:
            scored.append((score, chunk, display_name))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_index))
    results: list[dict] = []
    for score, chunk, display_name in scored[: max(top_k, 1)]:
        results.append(
            {
                "chunkId": chunk.id,
                "fileId": chunk.file_id,
                "fileName": display_name,
                "chunkIndex": chunk.chunk_index,
                "score": round(score, 2),
                "content": chunk.content,
            }
        )
    return results
