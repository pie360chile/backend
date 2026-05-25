"""Extrae texto y prepara imágenes de archivos adjuntos al chat del Agente Pie."""
import base64
import io
import os
from typing import Dict, List, Optional, Tuple

MAX_FILES = int(os.getenv('AGENTS_MAX_FILES', '5') or '5')
MAX_FILE_BYTES = int(os.getenv('AGENTS_MAX_FILE_MB', '10') or '10') * 1024 * 1024
MAX_CHARS_PER_FILE = int(os.getenv('AGENTS_MAX_CHARS_PER_FILE', '12000') or '12000')
MAX_TOTAL_CHARS = int(os.getenv('AGENTS_MAX_ATTACHMENT_CHARS', '40000') or '40000')
MAX_IMAGE_BYTES = int(os.getenv('AGENTS_MAX_IMAGE_MB', '5') or '5') * 1024 * 1024

DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

MIME_BY_EXT = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
    '.gif': 'image/gif',
}


def _truncate(text: str, limit: int) -> str:
    t = (text or '').strip()
    if len(t) <= limit:
        return t
    return t[: limit - 80] + '\n\n[... texto truncado por límite de contexto ...]'


def _file_ext(filename: str) -> str:
    return os.path.splitext((filename or '').lower())[1]


def is_image_file(filename: str) -> bool:
    return _file_ext(filename) in IMAGE_EXTENSIONS


def _extract_pdf(content: bytes) -> str:
    try:
        import fitz

        doc = fitz.open(stream=content, filetype='pdf')
        parts = [page.get_text() for page in doc]
        doc.close()
        return '\n'.join(parts)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or '')
        return '\n'.join(parts)
    except Exception as e:
        raise ValueError(f'No se pudo leer el PDF: {e}') from e


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document

        doc = Document(io.BytesIO(content))
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise ValueError(f'No se pudo leer el DOCX: {e}') from e


def _extract_plain(content: bytes) -> str:
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError('No se pudo decodificar el archivo de texto')


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    if not content:
        raise ValueError('El archivo está vacío')
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f'El archivo supera el límite de {MAX_FILE_BYTES // (1024 * 1024)} MB')

    ext = _file_ext(filename)
    if ext not in DOCUMENT_EXTENSIONS:
        raise ValueError(f'No es un documento de texto soportado: {ext}')

    if ext == '.pdf':
        text = _extract_pdf(content)
    elif ext == '.docx':
        text = _extract_docx(content)
    else:
        text = _extract_plain(content)

    if not (text or '').strip():
        raise ValueError('El archivo no contiene texto extraíble')

    return _truncate(text, MAX_CHARS_PER_FILE)


def encode_image_data_url(filename: str, content: bytes) -> str:
    if not content:
        raise ValueError('La imagen está vacía')
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError(f'La imagen supera el límite de {MAX_IMAGE_BYTES // (1024 * 1024)} MB')

    ext = _file_ext(filename)
    mime = MIME_BY_EXT.get(ext)
    if not mime:
        raise ValueError(f'Formato de imagen no permitido: {ext}')

    b64 = base64.b64encode(content).decode('utf-8')
    return f'data:{mime};base64,{b64}'


def _build_documents_context(doc_files: List[Tuple[str, bytes]]) -> Tuple[str, List[str], Optional[str]]:
    if not doc_files:
        return '', [], None

    names: List[str] = []
    blocks: List[str] = []
    total = 0

    for filename, content in doc_files:
        try:
            text = extract_text_from_bytes(filename, content)
        except ValueError as e:
            return '', [], str(e)

        names.append(filename)
        block = f'### Archivo adjunto: {filename}\n{text}'
        if total + len(block) > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total
            if remaining < 200:
                return '', [], 'El contenido total de los archivos supera el límite permitido'
            block = _truncate(block, remaining)
        blocks.append(block)
        total += len(block)

    context = (
        'DOCUMENTOS ADJUNTOS POR EL USUARIO (analízalos para responder; '
        'prioriza su contenido si la pregunta lo requiere):\n\n'
        + '\n\n---\n\n'.join(blocks)
    )
    return context, names, None


def process_uploaded_files(
    files: List[Tuple[str, bytes]],
) -> Tuple[str, List[Dict[str, str]], List[str], Optional[str]]:
    """
    Devuelve (contexto_texto_documentos, imágenes_para_vision, todos_los_nombres, error).
    Cada imagen: {"filename": str, "image_url": data_url}.
    """
    if not files:
        return '', [], [], None
    if len(files) > MAX_FILES:
        return '', [], [], f'Máximo {MAX_FILES} archivos por mensaje'

    doc_files: List[Tuple[str, bytes]] = []
    image_items: List[Dict[str, str]] = []
    all_names: List[str] = []

    for filename, content in files:
        ext = _file_ext(filename)
        if ext not in ALLOWED_EXTENSIONS:
            return (
                '',
                [],
                [],
                f'Formato no permitido ({ext or "sin extensión"}). '
                f'Usa PDF, DOCX, TXT, JPG, PNG o WEBP.',
            )

        if is_image_file(filename):
            try:
                data_url = encode_image_data_url(filename, content)
            except ValueError as e:
                return '', [], [], str(e)
            image_items.append({'filename': filename, 'image_url': data_url})
            all_names.append(filename)
        else:
            doc_files.append((filename, content))

    text_context, doc_names, doc_error = _build_documents_context(doc_files)
    if doc_error:
        return '', [], [], doc_error

    all_names = doc_names + [i['filename'] for i in image_items]
    return text_context, image_items, all_names, None


def build_attachments_context(
    files: List[Tuple[str, bytes]],
) -> Tuple[str, List[str], Optional[str]]:
    """Compatibilidad: solo documentos de texto."""
    text_context, _, names, error = process_uploaded_files(files)
    return text_context, names, error


def format_user_message_with_attachments(message: str, filenames: List[str]) -> str:
    text = (message or '').strip()
    if not filenames:
        return text
    files_line = ', '.join(filenames)
    if text:
        return f'{text}\n\n📎 Archivos adjuntos: {files_line}'
    return f'📎 Archivos adjuntos: {files_line}\n(El usuario envió archivos para analizar)'
