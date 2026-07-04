"""Extrae texto de los archivos de contexto del agente (carpeta Files, no plantillas)."""

from __future__ import annotations

from pathlib import Path

from app.backend.utils import agent_v2_storage as storage

# Límites para no saturar el contexto del modelo
MAX_FILES = 25
MAX_CHARS_PER_FILE = 24_000
MAX_TOTAL_CHARS = 120_000

_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".xml",
    ".html",
    ".htm",
    ".log",
    ".yaml",
    ".yml",
}
_BINARY_EXTENSIONS = {".docx", ".pdf"}
_SPREADSHEET_EXTENSIONS = {".xls", ".xlsx", ".xlsm"}


def _is_context_file(path: Path, agent_root: Path) -> bool:
    if not path.is_file():
        return False
    rel = path.relative_to(agent_root).as_posix()
    if rel.startswith("documentos/"):
        return False
    ext = path.suffix.lower()
    return ext in _TEXT_EXTENSIONS or ext in _BINARY_EXTENSIONS or ext in _SPREADSHEET_EXTENSIONS


def list_context_file_paths(agent_name: str) -> list[Path]:
    root = storage.agent_folder(agent_name)
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if _is_context_file(p, root)]
    return sorted(files, key=lambda p: p.as_posix().lower())[:MAX_FILES]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [((cell.text or "").strip()) for cell in row.cells]
            line = " | ".join(c for c in cells if c)
            if line:
                parts.append(line)
    return "\n".join(parts)


def _read_pdf(path: Path) -> str:
    import fitz

    doc = fitz.open(str(path))
    try:
        parts: list[str] = []
        for page in doc:
            text = (page.get_text() or "").strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    finally:
        doc.close()


def _read_excel(path: Path) -> str:
    """Convierte hojas Excel (.xls / .xlsx) a texto tabular para el contexto del modelo."""
    import pandas as pd

    ext = path.suffix.lower()
    engine: str | None = None
    if ext == ".xls":
        engine = "xlrd"
    elif ext in {".xlsx", ".xlsm"}:
        engine = "openpyxl"

    read_kwargs: dict = {"sheet_name": None, "header": None, "dtype": str}
    if engine:
        read_kwargs["engine"] = engine

    try:
        sheets = pd.read_excel(path, **read_kwargs)
    except Exception as first_exc:
        try:
            sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
        except Exception as second_exc:
            raise RuntimeError(f"{first_exc}; reintento: {second_exc}") from first_exc

    if not isinstance(sheets, dict):
        sheets = {"Hoja1": sheets}

    parts: list[str] = []
    max_rows = 600
    for sheet_name, df in sheets.items():
        df = df.fillna("")
        label = str(sheet_name)
        parts.append(f"## Hoja: {label}")
        if len(df) > max_rows:
            df = df.head(max_rows)
            parts.append(f"[Mostrando primeras {max_rows} filas de {label}]")
        # TSV legible para el modelo (apoderados, reportes interactivos, etc.)
        parts.append(df.to_csv(index=False, sep="\t", lineterminator="\n"))
    return "\n".join(parts)


def extract_file_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _TEXT_EXTENSIONS:
        return _read_text_file(path)
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext in _SPREADSHEET_EXTENSIONS:
        return _read_excel(path)
    return ""


def build_agent_files_context(agent_name: str) -> tuple[str, int]:
    """
    Devuelve (bloque de texto para el prompt, cantidad de archivos incluidos).
    Solo archivos subidos en Files; excluye plantillas en documentos/.
    """
    root = storage.agent_folder(agent_name)
    paths = list_context_file_paths(agent_name)
    if not paths:
        return "", 0

    index_lines = [p.relative_to(root).as_posix() for p in paths]
    sections: list[str] = []
    total_chars = 0
    included = 0

    for path in paths:
        rel = path.relative_to(root).as_posix()
        ext = path.suffix.lower()
        try:
            content = extract_file_text(path).strip()
        except Exception as exc:
            content = f"[No se pudo leer el archivo: {exc}]"

        if not content:
            if ext in _TEXT_EXTENSIONS | _BINARY_EXTENSIONS | _SPREADSHEET_EXTENSIONS:
                content = "[Archivo sin texto extraíble o vacío]"
            else:
                continue

        if len(content) > MAX_CHARS_PER_FILE:
            content = content[:MAX_CHARS_PER_FILE] + "\n… [contenido truncado]"

        block = f"### Archivo: {rel}\n\n{content}"
        if total_chars + len(block) > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total_chars
            if remaining > 200:
                sections.append(block[:remaining] + "\n… [contexto total truncado]")
            break

        sections.append(block)
        total_chars += len(block)
        included += 1

    if not sections:
        return "", 0

    header = (
        "ARCHIVOS DE CONTEXTO (subidos en Files del agente). "
        "Cuando las instrucciones pidan revisar, buscar o usar archivos adjuntos, "
        "utiliza ÚNICAMENTE el contenido de estos archivos como fuente.\n"
        f"Índice de archivos elegibles ({len(index_lines)}): "
        + ", ".join(index_lines)
        + "\n"
    )
    return header + "\n\n---\n\n".join(sections), included
