"""Importa anamnesis desde carpeta Google Drive ANAMNESIS a PIE360 (doc 3).

Uso (BD vía tunnel recomendado):
  set DATABASE_URL=mysql+pymysql://admin:PASS@127.0.0.1:3307/pie360
  python scripts/import_drive_anamnesis.py --dry-run
  python scripts/import_drive_anamnesis.py --apply --limit 5
  python scripts/import_drive_anamnesis.py --apply
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import tempfile
import time
from collections import deque
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tunnel local: el host público 3306 suele rechazar; .env no debe pisar este script.
DEFAULT_TUNNEL_DB_URL = (
    "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)
# IMPORT_DATABASE_URL opcional; si no, tunnel. Se aplica antes y después de dotenv.
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.backend.classes.anamnesis_class import ANAMNESIS_DOCUMENT_ID, AnamnesisClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
from app.backend.db.models import (
    AnamnesisModel,
    CourseModel,
    DocumentModel,
    FolderModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from app.backend.utils.customer_drive_config import load_customer_drive_config
from app.backend.utils.google_drive_storage import (
    _FOLDER_MIME,
    _service_for_config,
    upload_student_document_tree,
)
import unicodedata
import json

# dotenv (override=True en config) pudo restaurar el host remoto: re-forzar tunnel.
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

CUSTOMER_ID = 2
ANAMNESIS_ROOT_FOLDER_ID = "1GpG0_E1AwMKObwFoWzOAqWhu3JHhxpEl"

OUTPUT_DIR = ROOT / "scripts" / "output"
DRY_CSV = OUTPUT_DIR / "anamnesis_dry_run.csv"
APPLY_CSV = OUTPUT_DIR / "anamnesis_apply_result.csv"
# Guardar PDFs en el workspace local (no en ruta de prod Linux del .env)
LOCAL_STUDENT_FILES = ROOT / "files" / "system" / "students"


def _student_files_dir() -> Path:
    LOCAL_STUDENT_FILES.mkdir(parents=True, exist_ok=True)
    return LOCAL_STUDENT_FILES


def _resolve_drive_meta(db: Session, *, student_id: int, period_year: str = "2026") -> dict[str, Any]:
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    if not student:
        raise ValueError("Alumno no encontrado para metadata Drive")
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    academic = (
        db.query(StudentAcademicInfoModel)
        .filter(StudentAcademicInfoModel.student_id == student_id)
        .order_by(StudentAcademicInfoModel.id.desc())
        .first()
    )
    school = (
        db.query(SchoolModel)
        .filter(SchoolModel.id == int(getattr(student, "school_id", 0) or 0))
        .first()
    )
    if not school or not getattr(school, "customer_id", None):
        raise ValueError("No se pudo resolver liceo/cliente para Drive")
    course = None
    if academic and academic.course_id:
        course = db.query(CourseModel).filter(CourseModel.id == int(academic.course_id)).first()
    document = db.query(DocumentModel).filter(DocumentModel.id == ANAMNESIS_DOCUMENT_ID).first()
    rut = (getattr(personal, "identification_number", None) if personal else None) or student.identification_number
    if not rut:
        raise ValueError("El alumno no tiene RUT")
    return {
        "customer_id": int(school.customer_id),
        "school_name": school.school_name or f"Liceo {school.id}",
        "year": int(period_year),
        "course_name": (course.course_name if course else None) or "Curso",
        "student_rut": str(rut),
        "document_type_name": (document.document if document else None) or "Anamnesis",
        "school_id": int(school.id),
        "course_id": int(course.id) if course else None,
    }


DRY_FIELDS = [
    "n",
    "status",
    "message",
    "drive_file_id",
    "archivo",
    "ruta_drive",
    "nombre_archivo",
    "curso_archivo",
    "match_by",
    "rut_digits",
    "student_id",
    "ya_tiene_anamnesis",
    "extractable",
    "text_len",
    "acro_fields",
    "campos_mapeados",
    "sample_student_full_name",
    "sample_interview_reason",
    "sample_diagnosis_detail",
]

APPLY_FIELDS = DRY_FIELDS + ["anamnesis_id", "version", "folder_id", "pdf_filename"]

RUT_FROM_NAME = re.compile(r"(?<!\d)(\d{7,9})(?!\d)")
RUT_IN_TEXT = re.compile(
    r"(?:R\.?\s*U\.?\s*T\.?|RUN)\s*[:\-]?\s*(\d{1,2}\.?\d{3}\.?\d{3}\-?[\dkK]|\d{7,9}\-?[\dkK])",
    re.I,
)


def _db_url() -> str:
    return os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL


def _new_db() -> Session:
    engine = create_engine(_db_url(), pool_pre_ping=True, pool_recycle=3600)
    return sessionmaker(bind=engine)()


def _normalize_rut_digits(v: Any) -> str | None:
    if v is None:
        return None
    s = "".join(c for c in str(v).strip().lower() if c.isalnum())
    if not s:
        return None
    # solo cuerpo numérico (sin DV) para match flexible
    body = re.sub(r"[^0-9]", "", s[:-1] if s[-1].isalpha() or s[-1].isdigit() else s)
    if s[-1].isalpha():
        body = re.sub(r"[^0-9]", "", s[:-1])
    else:
        body = re.sub(r"[^0-9]", "", s)
    # si incluye DV numérico, usar cuerpo de 7-8 dígitos típicos
    if len(body) >= 8:
        # preferir últimos 8 o 9 sin DV: RUT chileno cuerpo 7-8 + DV
        if len(body) == 9:
            return body[:-1]  # drop DV digit
        if len(body) == 8:
            return body  # could be body without DV or body+DV; try as-is
    if 7 <= len(body) <= 9:
        return body if len(body) <= 8 else body[:-1]
    return body or None


def _rut_body(v: Any) -> str | None:
    """Cuerpo RUT sin DV (solo dígitos)."""
    if v is None:
        return None
    s = "".join(c for c in str(v).lower() if c.isalnum())
    if not s:
        return None
    if s[-1].isalpha():
        body = s[:-1]
    else:
        body = s
        # Si 9 dígitos, último suele ser DV
        if len(body) == 9:
            body = body[:-1]
    body = re.sub(r"\D", "", body)
    return body if 7 <= len(body) <= 8 else (body or None)


def _access_token(db: Session) -> str:
    cfg = load_customer_drive_config(db, CUSTOMER_ID)
    oauth = cfg.oauth_info or {}
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": oauth["client_id"],
            "client_secret": oauth["client_secret"],
            "refresh_token": oauth["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _download_drive_file(access_token: str, file_id: str) -> bytes:
    response = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"alt": "media"},
        timeout=180,
    )
    response.raise_for_status()
    return response.content


def _list_anamnesis_pdfs(db: Session) -> list[dict[str, str]]:
    cfg = load_customer_drive_config(db, CUSTOMER_ID)
    service = _service_for_config(cfg)
    q: deque[tuple[str, str]] = deque([(ANAMNESIS_ROOT_FOLDER_ID, "ANAMNESIS")])
    pdfs: list[dict[str, str]] = []
    while q:
        folder_id, path = q.popleft()
        token = None
        while True:
            resp = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    spaces="drive",
                    fields="nextPageToken,files(id,name,mimeType)",
                    pageSize=200,
                    pageToken=token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for f in resp.get("files") or []:
                name = f.get("name") or ""
                if f.get("mimeType") == _FOLDER_MIME:
                    q.append((f["id"], f"{path}/{name}"))
                elif name.lower().endswith(".pdf"):
                    pdfs.append({"id": f["id"], "name": name, "path": path})
            token = resp.get("nextPageToken")
            if not token:
                break
    pdfs.sort(key=lambda x: (x["path"].lower(), x["name"].lower()))
    return pdfs


def _build_student_rut_index(db: Session) -> dict[str, list[int]]:
    """body RUT (sin DV) -> [student_id, ...]."""
    index: dict[str, list[int]] = {}
    rows = (
        db.query(
            StudentModel.id,
            StudentModel.identification_number,
            StudentPersonalInfoModel.identification_number,
        )
        .outerjoin(
            StudentPersonalInfoModel,
            StudentPersonalInfoModel.student_id == StudentModel.id,
        )
        .filter(StudentModel.deleted_status_id == 0)
        .all()
    )
    for sid, stu_rut, per_rut in rows:
        for raw in (stu_rut, per_rut):
            body = _rut_body(raw)
            if not body:
                continue
            index.setdefault(body, [])
            if int(sid) not in index[body]:
                index[body].append(int(sid))
    return index


def _extract_rut_from_filename(name: str) -> str | None:
    # Prefer leading digits before _ Anamnesis
    m = re.match(r"^(\d{7,9})(?:_|\s|-)", name.strip())
    if m:
        return _rut_body(m.group(1))
    found = RUT_FROM_NAME.findall(name)
    if found:
        return _rut_body(found[0])
    return None


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in nk if not unicodedata.combining(c))


def _norm_name(s: str) -> str:
    s = _strip_accents(s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_GRADE_WORD = {
    "1": "primero",
    "2": "segundo",
    "3": "tercero",
    "4": "cuarto",
    "5": "quinto",
    "6": "sexto",
    "7": "septimo",
    "8": "octavo",
    "pk": "prekinder",
    "prek": "prekinder",
    "prekinder": "prekinder",
    "pre-kinder": "prekinder",
    "k": "kinder",
    "ka": "kinder",
    "kb": "kinder",
    "kc": "kinder",
    "kd": "kinder",
    "kinder": "kinder",
    "nt1": "prekinder",
    "nt2": "kinder",
}


def _course_key_from_text(raw: str) -> tuple[str | None, str | None]:
    """Normaliza curso a (grado, letra) p.ej. ('primero','a'), ('kinder','b')."""
    s = _norm_name(raw)
    if not s:
        return None, None
    s = s.replace("°", " ").replace("º", " ")
    s = re.sub(r"\s+", " ", s).strip()

    # KINDER A / PREKINDER B / PRIMERO A
    m = re.search(
        r"\b(pre\s*-?\s*kinder|prekinder|kinder|primero|segundo|tercero|cuarto|quinto|sexto|septimo|octavo)\b"
        r"(?:\s*([a-g]))?\b",
        s,
    )
    if m:
        grade = m.group(1).replace(" ", "").replace("-", "")
        if grade.startswith("pre"):
            grade = "prekinder"
        letter = (m.group(2) or "").lower() or None
        return grade, letter

    # PKA / PKB / PK°B
    m = re.match(r"^pk\s*°?\s*([a-g])\b", s)
    if m:
        return "prekinder", m.group(1).lower()

    # 1A / 7B / KA / KB / 1°A
    m = re.match(r"^(pre?k|k|nt[12]|[1-8])\s*([a-g])?\b", s)
    if m:
        graw = m.group(1).replace(" ", "")
        letter = (m.group(2) or "").lower() or None
        if graw in {"ka", "kb", "kc", "kd"}:
            return "kinder", graw[-1]
        if graw == "k":
            return "kinder", letter
        grade = _GRADE_WORD.get(graw)
        return grade, letter

    # 1 a / 3 c
    m = re.match(r"^([1-8])\s+([a-g])\b", s)
    if m:
        return _GRADE_WORD.get(m.group(1)), m.group(2).lower()

    return None, None


def _parse_filename_meta(filename: str) -> dict[str, Any]:
    """Extrae curso + nombre desde '1A-ANGELINA VALDES.pdf' o '3A Mathieu Vega.pdf'."""
    stem = Path(filename).stem.strip()
    stem = re.sub(r"^\d{7,9}(?:_|\s|-)+", "", stem)
    stem = re.sub(r"(?i)[_-]anamnesis$", "", stem).strip()

    course_grade = None
    course_letter = None
    person = stem

    # Prefijo curso pegado o con separador: 1A-, KA-, 7A , PreK-
    m = re.match(
        r"^(?P<course>pre\s*-?\s*kinder|prekinder|prek|pk\s*°?\s*[a-g]|nt[12]|k[a-d]?|"
        r"[1-8]\s*[a-g]?|[1-8]°\s*[a-g]?)\s*[-_\s.]+(?P<name>.+)$",
        stem,
        flags=re.I,
    )
    if m:
        course_grade, course_letter = _course_key_from_text(m.group("course"))
        # KA / KB / PKA / PKB: letra en el código
        craw = _norm_name(m.group("course")).replace(" ", "").replace("°", "")
        if re.fullmatch(r"k[a-d]", craw):
            course_grade, course_letter = "kinder", craw[-1]
        if re.fullmatch(r"pk[a-g]", craw):
            course_grade, course_letter = "prekinder", craw[-1]
        person = m.group("name").strip()
    else:
        # Intento: primeros tokens son curso
        parts = re.split(r"[\s_-]+", stem, maxsplit=1)
        if len(parts) == 2:
            g, let = _course_key_from_text(parts[0])
            if g:
                course_grade, course_letter = g, let
                person = parts[1]

    person = re.sub(r"[_]+", " ", person)
    person = re.sub(r"\s+", " ", person).strip(" -_")
    return {
        "person_name": person or None,
        "course_grade": course_grade,
        "course_letter": course_letter,
        "course_label": (
            f"{course_grade or ''} {course_letter or ''}".strip() or None
        ),
    }


def _name_from_filename(filename: str) -> str | None:
    return _parse_filename_meta(filename).get("person_name")


def _name_tokens(s: str) -> set[str]:
    stop = {"de", "del", "la", "las", "los", "y", "e", "da", "do", "das", "dos"}
    return {t for t in _norm_name(s).split() if len(t) > 1 and t not in stop}


def _build_student_name_index(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(
            StudentModel.id,
            StudentPersonalInfoModel.names,
            StudentPersonalInfoModel.father_lastname,
            StudentPersonalInfoModel.mother_lastname,
            StudentPersonalInfoModel.identification_number,
            CourseModel.course_name,
        )
        .outerjoin(
            StudentPersonalInfoModel,
            StudentPersonalInfoModel.student_id == StudentModel.id,
        )
        .outerjoin(
            StudentAcademicInfoModel,
            StudentAcademicInfoModel.student_id == StudentModel.id,
        )
        .outerjoin(CourseModel, CourseModel.id == StudentAcademicInfoModel.course_id)
        .filter(StudentModel.deleted_status_id == 0)
        .all()
    )
    out: list[dict[str, Any]] = []
    for sid, names, fl, ml, rut, course_name in rows:
        full = " ".join(p for p in [(names or "").strip(), (fl or "").strip(), (ml or "").strip()] if p)
        if not full:
            continue
        tokens = _name_tokens(full)
        if len(tokens) < 2:
            continue
        cg, cl = _course_key_from_text(course_name or "")
        out.append(
            {
                "student_id": int(sid),
                "full_name": full,
                "tokens": tokens,
                "norm": _norm_name(full),
                "rut_body": _rut_body(rut),
                "course_name": course_name or "",
                "course_grade": cg,
                "course_letter": cl,
            }
        )
    return out


def _match_student_by_name(
    name: str,
    index: list[dict[str, Any]],
    *,
    course_grade: str | None = None,
    course_letter: str | None = None,
) -> tuple[str, list[int], str]:
    """Retorna (status, student_ids, detail). status: ok|ambiguous|not_found."""
    tokens = _name_tokens(name)
    if len(tokens) < 2:
        return "not_found", [], "nombre archivo insuficiente"

    scored: list[tuple[float, int, str, str]] = []
    for row in index:
        inter = tokens & row["tokens"]
        if len(inter) < 2:
            continue
        union = tokens | row["tokens"]
        score = len(inter) / max(len(union), 1)
        if tokens <= row["tokens"]:
            score += 0.35
        if row["tokens"] <= tokens:
            score += 0.15
        last = _norm_name(name).split()[-1]
        if last in row["tokens"]:
            score += 0.1

        # Bonus / penalización por curso
        if course_grade:
            if row.get("course_grade") == course_grade:
                score += 0.45
                if course_letter and row.get("course_letter") == course_letter:
                    score += 0.35
                elif course_letter and row.get("course_letter") and row.get("course_letter") != course_letter:
                    score -= 0.25
            elif row.get("course_grade"):
                # mismo nombre en otro nivel: bajar bastante
                score -= 0.35

        scored.append((score, row["student_id"], row["full_name"], row.get("course_name") or ""))

    if not scored:
        return "not_found", [], "sin overlap de nombre"
    scored.sort(key=lambda x: (-x[0], x[1]))
    best = scored[0]

    # Si hay curso, priorizar contenders con mismo grado
    min_score = 0.45
    if course_grade:
        min_score = 0.55
    contenders = [s for s in scored if s[0] >= best[0] - 0.08 and s[0] >= min_score]

    # Desempate: si el mejor tiene curso alineado y el resto no, quedarse con él
    if course_grade and len(contenders) > 1:
        aligned = [
            s
            for s in contenders
            if any(
                r["student_id"] == s[1]
                and r.get("course_grade") == course_grade
                and (not course_letter or r.get("course_letter") == course_letter)
                for r in index
            )
        ]
        if len(aligned) == 1:
            contenders = aligned
        elif aligned:
            contenders = aligned

    ids = sorted({c[1] for c in contenders})
    if best[0] < min_score:
        return "not_found", [], f"score bajo {best[0]:.2f} vs {best[2]} ({best[3]})"
    if len(ids) > 1:
        return (
            "ambiguous",
            ids,
            f"score={best[0]:.2f} candidates={ids} course={course_grade or '-'}{course_letter or ''}",
        )
    return (
        "ok",
        [best[1]],
        f"score={best[0]:.2f} name={best[2]} course={best[3]}",
    )


def _seed_payload_from_student(db: Session, student_id: int) -> dict[str, Any]:
    """Rellena identificación desde ficha PIE360 (PDFs suelen ser escaneo sin texto)."""
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    academic = (
        db.query(StudentAcademicInfoModel)
        .filter(StudentAcademicInfoModel.student_id == student_id)
        .order_by(StudentAcademicInfoModel.id.desc())
        .first()
    )
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    payload: dict[str, Any] = {"student_id": student_id}
    mapped: list[str] = []
    if personal:
        full = " ".join(
            p
            for p in [
                (personal.names or "").strip(),
                (personal.father_lastname or "").strip(),
                (personal.mother_lastname or "").strip(),
            ]
            if p
        )
        if full:
            payload["student_full_name"] = full
            mapped.append("student_full_name")
        if personal.gender_id:
            payload["gender_id"] = int(personal.gender_id)
            mapped.append("gender_id")
        if personal.born_date:
            parsed = _parse_date_loose(personal.born_date)
            if parsed:
                payload["born_date"] = parsed
                mapped.append("born_date")
        if personal.nationality_id:
            payload["nationality_id"] = int(personal.nationality_id)
            mapped.append("nationality_id")
        if personal.address:
            payload["address"] = str(personal.address).strip()
            mapped.append("address")
        if personal.phone:
            payload["phone"] = str(personal.phone).strip()
            mapped.append("phone")
        if personal.native_language:
            payload["native_language"] = str(personal.native_language).strip()
            mapped.append("native_language")
        if personal.language_usually_used:
            payload["language_used"] = str(personal.language_usually_used).strip()
            mapped.append("language_used")
    if academic and academic.course_id:
        course = db.query(CourseModel).filter(CourseModel.id == academic.course_id).first()
        if course and course.course_name:
            payload["current_schooling"] = course.course_name
            payload["current_level"] = course.course_name
            mapped.extend(["current_schooling", "current_level"])
    if student and student.school_id:
        school = db.query(SchoolModel).filter(SchoolModel.id == student.school_id).first()
        if school and school.school_name:
            payload["school_name"] = school.school_name
            mapped.append("school_name")
    payload["_mapped_keys"] = sorted(set(mapped))
    payload["_seed_from"] = "student_ficha"
    return payload


def _extract_rut_from_text(text: str) -> str | None:
    m = RUT_IN_TEXT.search(text or "")
    if m:
        return _rut_body(m.group(1))
    # fallback: first 7-8 digit run near "estudiante"
    m2 = re.search(r"estudiante.{0,80}?(\d{7,8})", text or "", re.I | re.S)
    if m2:
        return _rut_body(m2.group(1))
    return None


def _normalize_ocr_text(text: str) -> str:
    """Normaliza OCR para matching: minúsculas, sin tildes, espacios colapsados."""
    s = unicodedata.normalize("NFKD", text or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = s.replace("§", "s").replace("|", " ")
    s = re.sub(r"[^\w\s:/.\-áéíóúñ]", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


_OCR_ENGINE = None


def _get_rapidocr():
    global _OCR_ENGINE
    if _OCR_ENGINE is False:
        return None
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR

        _OCR_ENGINE = RapidOCR()
        return _OCR_ENGINE
    except Exception as exc:
        print(f"  OCR no disponible: {exc}", flush=True)
        _OCR_ENGINE = False
        return None


def _ocr_pdf_text(content: bytes, *, zoom: float = 1.8, max_pages: int = 8) -> str:
    """OCR local (RapidOCR) para PDFs escaneados. Sin OpenAI."""
    ocr = _get_rapidocr()
    if ocr is None:
        return ""
    try:
        import fitz
    except Exception:
        return ""
    parts: list[str] = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png = pix.tobytes("png")
            try:
                result, _ = ocr(png)
            except Exception as exc:
                print(f"  OCR page {i+1} error: {exc}", flush=True)
                continue
            if not result:
                continue
            lines = [str(item[1]).strip() for item in result if item and len(item) > 1]
            page_text = "\n".join(ln for ln in lines if ln)
            if page_text:
                parts.append(page_text)
    finally:
        doc.close()
    return "\n\n".join(parts)


def _pdf_text_and_fields(content: bytes) -> tuple[str, dict[str, Any]]:
    text = ""
    fields: dict[str, Any] = {}
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        path = Path(tmp.name)
    try:
        try:
            import fitz

            doc = fitz.open(str(path))
            try:
                parts = []
                for page in doc:
                    t = (page.get_text() or "").strip()
                    if t:
                        parts.append(t)
                text = "\n\n".join(parts)
            finally:
                doc.close()
        except Exception:
            text = ""
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            raw_fields = reader.get_fields() or {}
            for key, meta in raw_fields.items():
                if not isinstance(meta, dict):
                    fields[str(key)] = meta
                    continue
                val = meta.get("/V")
                if hasattr(val, "get_object"):
                    try:
                        val = val.get_object()
                    except Exception:
                        pass
                fields[str(key)] = val
        except Exception:
            pass
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
    # Escaneos: capa de texto vacía → OCR local
    if len((text or "").strip()) < 40:
        ocr_text = _ocr_pdf_text(content)
        if ocr_text:
            text = ocr_text
            print(f"  OCR texto={len(text)} chars", flush=True)
    return text, fields


def _yn_to_int(val: Any) -> int | None:
    if val is None:
        return None
    s = str(val).strip().lower().lstrip("/")
    if s in {"1", "si", "sí", "yes", "true", "x", "on"}:
        return 1
    if s in {"0", "no", "false", "off"}:
        return 0
    if "sí" in s or s == "si":
        return 1
    if s == "no":
        return 0
    return None


def _clean_text(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s or None


def _find_labeled_value(text: str, labels: list[str], max_len: int = 400) -> str | None:
    for label in labels:
        pat = re.compile(
            rf"{re.escape(label)}\s*[:\-]?\s*(.+?)(?=\n[A-ZÁÉÍÓÚÑ][^\n]{{0,40}}[:\-]|\n\n|$)",
            re.I | re.S,
        )
        m = pat.search(text)
        if m:
            val = _clean_text(m.group(1))
            if val:
                return val[:max_len]
    return None


def _parse_date_loose(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y < 50 else 1900
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


# Mapeo AcroForm (nombres del template PIE360 anamnesis_student.pdf) → StoreAnamnesis
ACRO_FIELD_MAP: dict[str, str] = {
    "full_name": "student_full_name",
    "student_full_name": "student_full_name",
    "nombre": "student_full_name",
    "nombre_completo": "student_full_name",
    "nombre estudiante": "student_full_name",
    "nombres_apellidos": "student_full_name",
    "birth_day": "born_date",
    "born_date": "born_date",
    "fecha_nacimiento": "born_date",
    "years": "age",
    "edad": "age",
    "age": "age",
    "address": "address",
    "direccion": "address",
    "domicilio": "address",
    "domicilio_actual": "address",
    "domicilio actual": "address",
    "phone": "phone",
    "telefono": "phone",
    "teléfono": "phone",
    "celular": "phone",
    "mother_language": "native_language",
    "native_language": "native_language",
    "lengua_materna": "native_language",
    "used_language": "language_used",
    "language_used": "language_used",
    "course": "current_schooling",
    "current_schooling": "current_schooling",
    "curso": "current_schooling",
    "school": "school_name",
    "school_name": "school_name",
    "establecimiento": "school_name",
    "interview_reason": "interview_reason",
    "problem_definition": "interview_reason",
    "motivo": "interview_reason",
    "motivo_entrevista": "interview_reason",
    "motivo de la entrevista": "interview_reason",
    "motivo entrevista": "interview_reason",
    "diagnosis_detail": "diagnosis_detail",
    "diagnosisdetail": "diagnosis_detail",
    "detalle diagnóstico": "diagnosis_detail",
    "diagnostico": "diagnosis_detail",
    "diagnosis_has": "diagnosis_has",
    "pdhy": "diagnosis_has",
    "pdhn": "diagnosis_has",
    "first_year_notes": "first_year_notes",
    "birth_reason": "birth_reason",
    "anotherbirthreason": "birth_reason",
    "birth_weight": "birth_weight",
    "birth_height": "birth_height",
    "birthheight": "birth_height",
    "talla_nacimiento": "birth_height",
    "first_year_observations": "first_year_observations",
    "sm_head_control": "sm_head_control",
    "sm_sits_alone": "sm_sits_alone",
    "sm_walks_without_support": "sm_walks_without_support",
    "sm_first_words": "sm_first_words",
    "sm_first_phrases": "sm_first_phrases",
    "sm_dresses_alone": "sm_dresses_alone",
    "sm_bladder_day": "sm_bladder_day",
    "sm_bladder_night": "sm_bladder_night",
    "sm_bowel_day": "sm_bowel_day",
    "sm_bowel_night": "sm_bowel_night",
    "sm_observations_1": "sm_observations_1",
    "sm_motor_activity": "sm_motor_activity",
    "sm_muscle_tone": "sm_muscle_tone",
    "sm_lateral_dominance": "sm_lateral_dominance",
    "sm_observations_2": "sm_observations_2",
    "sm_walking_stability": "sm_walking_stability",
    "sm_frequent_falls": "sm_frequent_falls",
    "sm_fine_grab": "sm_fine_grab",
    "sm_fine_grip": "sm_fine_grip",
    "sm_fine_pinch": "sm_fine_pinch",
    "sm_fine_draw": "sm_fine_draw",
    "sm_fine_write": "sm_fine_write",
    "sm_fine_thread": "sm_fine_thread",
    "sm_cog_reacts_familiar": "sm_cog_reacts_familiar",
    "sm_cog_demands_company": "sm_cog_demands_company",
    "sm_cog_smiles_babbles": "sm_cog_smiles_babbles",
    "sm_cog_manipulates_explores": "sm_cog_manipulates_explores",
    "sm_cog_understands_prohibitions": "sm_cog_understands_prohibitions",
    "sm_cog_poor_eye_hand": "sm_cog_poor_eye_hand",
    "vision_interested_stimuli": "vision_interested_stimuli",
    "vision_irritated_eyes": "vision_irritated_eyes",
    "vision_headaches": "vision_headaches",
    "vision_squints": "vision_squints",
    "vision_follows_movement": "vision_follows_movement",
    "vision_abnormal_movements": "vision_abnormal_movements",
    "vision_erroneous_behaviors": "vision_erroneous_behaviors",
    "vision_diagnosis": "vision_diagnosis",
    "hearing_interested_stimuli": "hearing_interested_stimuli",
    "hearing_recognizes_voices": "hearing_recognizes_voices",
    "hearing_turns_head": "hearing_turns_head",
    "hearing_ears_to_tv": "hearing_ears_to_tv",
    "hearing_covers_ears": "hearing_covers_ears",
    "hearing_earaches": "hearing_earaches",
    "hearing_pronunciation_adequate": "hearing_pronunciation_adequate",
    "hearing_diagnosis": "hearing_diagnosis",
    "vision_hearing_observations": "vision_hearing_observations",
    "language_communication_method": "language_communication_method",
    "language_communication_other": "language_communication_other",
    "language_oral_loss": "language_oral_loss",
    "language_observations": "language_observations",
    "language_exp_babbles": "language_exp_babbles",
    "language_exp_vocalizes_gestures": "language_exp_vocalizes_gestures",
    "language_exp_emits_words": "language_exp_emits_words",
    "language_exp_emits_phrases": "language_exp_emits_phrases",
    "language_exp_relates_experiences": "language_exp_relates_experiences",
    "language_exp_clear_pronunciation": "language_exp_clear_pronunciation",
    "language_comp_identifies_objects": "language_comp_identifies_objects",
    "language_comp_identifies_people": "language_comp_identifies_people",
    "language_comp_understands_abstract": "language_comp_understands_abstract",
    "language_comp_responds_coherently": "language_comp_responds_coherently",
    "language_comp_follows_simple_instructions": "language_comp_follows_simple_instructions",
    "language_comp_follows_complex_instructions": "language_comp_follows_complex_instructions",
    "language_comp_follows_group_instructions": "language_comp_follows_group_instructions",
    "language_comp_understands_stories": "language_comp_understands_stories",
    "social_observations": "social_observations",
    "social_relates_spontaneously": "social_relates_spontaneously",
    "social_explains_behaviors": "social_explains_behaviors",
    "social_participates_groups": "social_participates_groups",
    "social_prefers_individual": "social_prefers_individual",
    "social_echolalic_language": "social_echolalic_language",
    "social_difficulty_adapting": "social_difficulty_adapting",
    "social_relates_collaboratively": "social_relates_collaboratively",
    "social_respects_social_norms": "social_respects_social_norms",
    "social_respects_school_norms": "social_respects_school_norms",
    "social_shows_humor": "social_shows_humor",
    "social_stereotyped_movements": "social_stereotyped_movements",
    "social_frequent_tantrums": "social_frequent_tantrums",
    "health_vaccines_up_to_date": "health_vaccines_up_to_date",
    "health_epilepsy": "health_epilepsy",
    "health_heart_problems": "health_heart_problems",
    "health_paraplegia": "health_paraplegia",
    "health_hearing_loss": "health_hearing_loss",
    "health_vision_loss": "health_vision_loss",
    "health_motor_disorder": "health_motor_disorder",
    "health_bronchorespiratory": "health_bronchorespiratory",
    "health_infectious_disease": "health_infectious_disease",
    "health_emotional_disorder": "health_emotional_disorder",
    "health_behavioral_disorder": "health_behavioral_disorder",
    "health_other": "health_other",
    "health_other_specify": "health_other_specify",
    "health_problems_treatment": "health_problems_treatment",
    "health_diet": "health_diet",
    "health_diet_other": "health_diet_other",
    "health_weight": "health_weight",
    "health_sleep_pattern": "health_sleep_pattern",
    "health_sleep_hours": "health_sleep_hours",
    "health_sleeps_alone": "health_sleeps_alone",
    "health_sleeps_specify": "health_sleeps_specify",
    "health_mood_behavior": "health_mood_behavior",
    "health_mood_other": "health_mood_other",
    "health_current_observations": "health_current_observations",
    "health_sleep_insomnia": "health_sleep_insomnia",
    "health_sleep_nightmares": "health_sleep_nightmares",
    "health_sleep_terrors": "health_sleep_terrors",
    "health_sleep_sleepwalking": "health_sleep_sleepwalking",
    "health_sleep_good_mood": "health_sleep_good_mood",
    "family_health_history": "family_health_history",
    "family_health_observations": "family_health_observations",
    "school_entry_age": "school_entry_age",
    "attended_kindergarten": "attended_kindergarten",
    "schools_count": "schools_count",
    "teaching_modality": "teaching_modality",
    "changes_reason": "changes_reason",
    "repeated_grade": "repeated_grade",
    "repeated_courses": "repeated_courses",
    "repeated_reason": "repeated_reason",
    "current_level": "current_level",
    "nivel": "current_level",
    "learning_difficulty": "learning_difficulty",
    "participation_difficulty": "participation_difficulty",
    "disruptive_behavior": "disruptive_behavior",
    "attends_regularly": "attends_regularly",
    "attends_gladly": "attends_gladly",
    "family_support_homework": "family_support_homework",
    "friends": "friends",
    "family_attitude": "family_attitude",
    "performance_assessment": "performance_assessment",
    "performance_reasons": "performance_reasons",
    "expectations": "expectations",
    "expectativas": "expectations",
    "environment": "environment",
    "ambiente": "environment",
    "final_comments": "final_comments",
    "comentarios": "final_comments",
    "observaciones_finales": "final_comments",
    "birth_medical_assistance": "birth_medical_assistance",
    "first_year_periodic_health_checkups": "first_year_periodic_health_checkups",
    "first_year_vaccines": "first_year_vaccines",
}


TEXT_LABEL_MAP: list[tuple[list[str], str]] = [
    (["Lengua materna", "Lengua matema"], "native_language"),
    (["Lengua de uso"], "language_used"),
    (["Establecimiento", "Estabiecimiento"], "school_name"),
    (["Escolaridad actual", "Escolandad actual"], "current_schooling"),
    (["Peso:"], "birth_weight"),
    (["Talla:"], "birth_height"),
    (["Actitud de la familia", "Actitud dela familia"], "family_attitude"),
    (["Antecedentes de Salud de la Familia", "Antecedentes de Salud de la Famlla"], "family_health_history"),
    (["Edad de ingreso al sistema escolar", "Edaddeingresoalsistemeescolar"], "school_entry_age"),
    (["Nede colegios", "N de colegios en que ha"], "schools_count"),
    (["Motivo de los cambios", "Motivode ios cambios"], "changes_reason"),
    (["Horas que duerme", "Horas quedueme"], "health_sleep_hours"),
    (["Fija la cabeza"], "sm_head_control"),
    (["Se sienta solo", "Se sienta solola"], "sm_sits_alone"),
    (["Camina sin apoyo"], "sm_walks_without_support"),
    (["Primeras palabras"], "sm_first_words"),
    (["Primeras frases", "Primeras freses"], "sm_first_phrases"),
    (["Se viste solo", "Se Viste solola"], "sm_dresses_alone"),
]

# Campos de identidad: siempre ganan los de ficha PIE360 (OCR suele ensuciarlos)
SEED_PREFERRED_KEYS = {
    "student_full_name",
    "gender_id",
    "born_date",
    "age",
    "nationality_id",
    "address",
    "phone",
    "school_name",
    "current_schooling",
    "current_level",
}

# Límites aproximados de columnas String en anamnesis
STRING_LIMITS: dict[str, int] = {
    "student_full_name": 255,
    "age": 50,
    "address": 500,
    "phone": 50,
    "native_language": 100,
    "language_used": 100,
    "current_schooling": 100,
    "school_name": 255,
    "birth_reason": 255,
    "birth_weight": 50,
    "birth_height": 50,
    "sm_head_control": 100,
    "sm_sits_alone": 100,
    "sm_walks_without_support": 100,
    "sm_first_words": 100,
    "sm_first_phrases": 100,
    "sm_dresses_alone": 100,
    "sm_bladder_day": 100,
    "sm_bladder_night": 100,
    "sm_bowel_day": 100,
    "sm_bowel_night": 100,
    "sm_motor_activity": 50,
    "sm_muscle_tone": 50,
    "sm_lateral_dominance": 20,
    "language_communication_method": 50,
    "health_diet": 50,
    "health_weight": 50,
    "health_sleep_pattern": 50,
    "health_sleep_hours": 50,
    "health_sleeps_alone": 50,
    "school_entry_age": 50,
    "schools_count": 50,
    "teaching_modality": 50,
    "repeated_courses": 100,
    "current_level": 100,
    "family_attitude": 255,
    "performance_assessment": 50,
    "expectations": 50,
    "environment": 50,
}


_DOMAIN_TOKEN_MAP = (
    ("comprende", "understand"),
    ("entender", "understand"),
    ("understand", "understand"),
    ("habla", "speak"),
    ("hablar", "speak"),
    ("speak", "speak"),
    ("lee", "read"),
    ("leer", "read"),
    ("read", "read"),
    ("escribe", "write"),
    ("escribir", "write"),
    ("write", "write"),
)


def _parse_language_domain(val: Any) -> list[str]:
    """Extrae grado de dominio (understand/speak/read/write) desde texto OCR o Excel."""
    if val is None:
        return []
    if isinstance(val, (list, tuple, set)):
        out: list[str] = []
        for item in val:
            out.extend(_parse_language_domain(item))
        # unique preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for x in out:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq
    s = _normalize_ocr_text(str(val))
    if not s:
        return []
    found: list[str] = []
    for token, code in _DOMAIN_TOKEN_MAP:
        if re.search(rf"\b{re.escape(token)}\b", s) or token in s.replace(" ", ""):
            if code not in found:
                found.append(code)
    return found


def _looks_like_domain_labels_only(val: str) -> bool:
    """True si el 'valor' es solo etiquetas de grado de dominio (basura OCR)."""
    s = _normalize_ocr_text(val or "")
    if not s:
        return False
    compact = re.sub(r"[\s;,/|\-]+", "", s)
    # quitar tokens de dominio y restos tipicos de la fila
    cleaned = compact
    for token, _ in _DOMAIN_TOKEN_MAP:
        cleaned = cleaned.replace(token, "")
    cleaned = re.sub(r"establecimiento|escolaridad|grado|dominio|lengua|uso|materna", "", cleaned)
    return len(cleaned) <= 2 and bool(_parse_language_domain(val))


def _extract_domain_near_label(norm_text: str, labels: list[str], window: int = 180) -> list[str]:
    for label in labels:
        needle = _normalize_ocr_text(label)
        idx = norm_text.find(needle)
        if idx < 0:
            continue
        chunk = norm_text[idx : idx + len(needle) + window]
        dom = _parse_language_domain(chunk)
        if dom:
            return dom
    return []


def _sanitize_language_fields(payload: dict[str, Any], *, norm_text: str, mapped_keys: list[str]) -> None:
    """Separa lengua (texto) vs grado de dominio (checkboxes)."""
    for text_key, domain_key, labels in (
        ("native_language", "native_language_domain", ["Lengua materna", "Lengua matema"]),
        ("language_used", "language_used_domain", ["Lengua de uso"]),
    ):
        raw = payload.get(text_key)
        domain = payload.get(domain_key)
        parsed_from_raw = _parse_language_domain(raw) if isinstance(raw, str) else []
        parsed_domain = _parse_language_domain(domain) if domain else []

        if parsed_from_raw and _looks_like_domain_labels_only(str(raw)):
            # OCR metió etiquetas de dominio en el input de lengua.
            # Si aparecen las 4, casi seguro son solo labels del formulario → no marcar.
            payload[text_key] = None
            if text_key in mapped_keys:
                mapped_keys.remove(text_key)
            if len(parsed_from_raw) < 4:
                parsed_domain = list(dict.fromkeys([*parsed_domain, *parsed_from_raw]))
        elif isinstance(raw, str) and parsed_from_raw and _looks_like_domain_labels_only(str(raw).split("\n")[0]):
            payload[text_key] = None
            if len(parsed_from_raw) < 4:
                parsed_domain = list(dict.fromkeys([*parsed_domain, *parsed_from_raw]))

        if not parsed_domain:
            near = _extract_domain_near_label(norm_text, labels)
            # Evitar marcar las 4 casillas solo por leer el encabezado del formulario
            if near and len(near) < 4:
                parsed_domain = near

        if parsed_domain:
            payload[domain_key] = parsed_domain
            if domain_key not in mapped_keys:
                mapped_keys.append(domain_key)

        # basura residual en lengua
        if isinstance(payload.get(text_key), str) and _looks_like_domain_labels_only(payload[text_key]):
            payload[text_key] = None


# Etiquetas típicas del formulario Decreto 170 que NUNCA son un valor válido.
_FORM_LABEL_FRAGMENTS = (
    "fecha nacimiento",
    "telefono",
    "domicilio",
    "lengua materna",
    "lengua de uso",
    "grado dominio",
    "grado de dominio",
    "antecedentes",
    "entrevista",
    "estudiante",
    "observaciones",
    "diagnostico medico",
    "estrabismo",
    "hipoacusia",
    "definicion del problema",
    "pais natal",
    "establecimiento",
    "controla esfinter",
    "controla esfínter",
    "esfinter vesical",
    "esfinter anal",
    "fija la cabeza",
    "se sienta",
    "camina sin apoyo",
    "primeras palabras",
    "primeras frases",
    "se viste",
    "motivo de los cambios",
    "ha repetido curso",
    "satisfactorio",
    "insatisfactorio",
    "como evalua la familia",
    "los datos contenidos",
    "seleccione",
    "sintesis de los",
    "decreto 170",
    "ley 20.201",
    "entrevista a la familia",
)

_AGE_FIELD_KEYS = {
    "sm_head_control",
    "sm_sits_alone",
    "sm_walks_without_support",
    "sm_first_words",
    "sm_first_phrases",
    "sm_dresses_alone",
    "sm_bladder_day",
    "sm_bladder_night",
    "sm_bowel_day",
    "sm_bowel_night",
    "school_entry_age",
    "age",
}


def _normalize_age_m_abbrev(val: str) -> str:
    """`5 m` / `6m` / `10 m` / `3 meses` → forma canónica con 'meses' si aplica."""
    token = re.sub(r"\s+", " ", (val or "").strip())
    m = re.fullmatch(r"(\d{1,2})\s*[mM](?:eses?)?", token, flags=re.IGNORECASE)
    if m:
        return f"{int(m.group(1))} meses"
    return token


def _looks_like_plausible_age(val: str) -> bool:
    token = re.sub(r"\s+", " ", (val or "").strip())
    tlow = _normalize_ocr_text(token)
    if not tlow or len(token) > 24:
        return False
    if tlow in {"sm", "s/m", "nr", "n/r", "na", "n/a"}:
        return True
    if re.search(r"controla|esfinter|observa|emite|primera|viste|sienta|camina|cabeza", tlow):
        return False
    if re.fullmatch(r"[a-z]{1,3}", tlow):
        return False
    if not re.search(r"\b\d{1,2}\s*(meses|mes|m|años|anos|ano|año|a)?\b", tlow) and not re.fullmatch(
        r"\d{1,2}\s*(m|a)?", tlow
    ):
        return False
    mnum = re.search(r"(\d{1,3})", tlow)
    if not mnum:
        return False
    n = int(mnum.group(1))
    if "mes" in tlow or re.search(r"\d+\s*m\b", tlow) or re.search(r"\d+m\b", tlow) or tlow.endswith("m"):
        return 0 < n <= 36
    if "a" in tlow or "ano" in tlow or "año" in tlow:
        return 0 < n <= 18
    return 0 < n <= 36


def _is_garbage_ocr_value(val: str, *, dest: str = "") -> bool:
    """True si el valor NO debe guardarse en ningún campo del formulario."""
    s = (val or "").strip()
    if not s:
        return True
    # colapsar saltos: OCR suele pegar la siguiente etiqueta
    compact = re.sub(r"[\r\n]+", " ", s)
    compact = re.sub(r"\s+", " ", compact).strip()
    low = _normalize_ocr_text(compact)

    # 1) etiquetas del formulario → NUNCA como valor
    matched_labels = [j for j in _FORM_LABEL_FRAGMENTS if j in low]
    if matched_labels:
        # si el texto es casi solo la etiqueta, o mezcla varias, descartar
        label_chars = sum(len(j) for j in matched_labels)
        if len(matched_labels) >= 2:
            return True
        if len(low) <= max(len(matched_labels[0]) + 40, 60):
            return True
        if label_chars / max(len(low), 1) >= 0.45:
            return True

    # 2) concatenación de labels sin espacios (esfintervesical, comprendehabla…)
    if re.search(
        r"(esfinter|esfínter).{0,3}(vesical|anal)|(comprende).{0,3}(habla)|(habla).{0,3}(lee)",
        low,
    ):
        return True

    # 3) ratio de alfanuméricos muy bajo / símbolos OCR
    alnum = sum(ch.isalnum() for ch in compact)
    if len(compact) >= 6 and alnum / len(compact) < 0.45:
        return True

    # 4) token muy corto sin sentido (MO, Hx, /a:)
    if len(compact) <= 3 and not compact.isdigit():
        if _normalize_ocr_text(compact) not in {"sm", "si", "sí", "no", "nr", "na"}:
            return True

    # 5) mezcla absurda letras sueltas + "meses/anos" deformado
    if re.search(r"[a-z]\s*meses|[a-z]\s*anos|/a:|musess|\bmo\b", low) and not re.search(
        r"\b\d{1,2}\s*(meses|mes|años|anos)", low
    ):
        return True

    # 6) campos de edad/hitos: reglas estrictas
    if dest in _AGE_FIELD_KEYS:
        return not _looks_like_plausible_age(compact)

    # 7) lenguas
    if dest in {"native_language", "language_used"}:
        if _looks_like_domain_labels_only(s):
            return True
        if len(compact) > 40:
            return True
        if "establecimiento" in low or "comprende" in low or "habla" in low:
            if not re.search(
                r"\b(espanol|español|mapudungun|ingles|inglés|aimara|quechua|creole|haitiano)\b",
                low,
            ):
                return True

    # 8) peso/talla
    if dest in {"birth_weight", "birth_height"} and not re.search(r"\d", compact):
        return True

    # 9) texto multilinea enorme pegado
    if "\n" in s and len(s) > 80:
        return True

    # 10) palabras “valor” que son claramente ruido OCR de 1-2 sílabas raras
    if re.fullmatch(r"[a-z]{1,2}\s+[a-z]{3,8}", low) and not re.search(r"\d", low):
        # ej: "h muses"
        return True

    return False


def _truncate_payload_strings(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    for k, lim in STRING_LIMITS.items():
        if k in out and isinstance(out[k], str):
            out[k] = out[k][:lim]
    # Text fields: cap extreme OCR dumps
    for k, v in list(out.items()):
        if isinstance(v, str) and k not in STRING_LIMITS and len(v) > 4000:
            out[k] = v[:4000]
    return out

# Fragmentos OCR (sin tildes) → campo Sí/No (1=Sí, 2=No en anamnesis PIE360)
OCR_YN_LABELS: list[tuple[str, str]] = [
    ("tiene un diagnostico previo", "diagnosis_has"),
    ("diagnostico previo", "diagnosis_has"),
    ("asistencia medica durante el parto", "birth_medical_assistance"),
    ("tuvo asistencia medica", "birth_medical_assistance"),
    ("controles periodicos de salud", "first_year_periodic_health_checkups"),
    ("vacunas", "first_year_vaccines"),
    ("estabilidad al caminar", "sm_walking_stability"),
    ("caidas frecuente", "sm_frequent_falls"),
    ("prension", "sm_fine_grip"),
    ("pinza", "sm_fine_pinch"),
    ("dibuja", "sm_fine_draw"),
    ("escribe", "sm_fine_write"),
    ("ensarta", "sm_fine_thread"),
    ("reacciona a voces o caras", "sm_cog_reacts_familiar"),
    ("reaccionaa voceso caras", "sm_cog_reacts_familiar"),
    ("demanda objetos y compania", "sm_cog_demands_company"),
    ("demanda objetos ycompania", "sm_cog_demands_company"),
    ("manipula y explora", "sm_cog_manipulates_explores"),
    ("comprende prohibiciones", "sm_cog_understands_prohibitions"),
    ("descoordinacion ojo-mano", "sm_cog_poor_eye_hand"),
    ("descoordinacion ojo mano", "sm_cog_poor_eye_hand"),
    ("estimulos visuales", "vision_interested_stimuli"),
    ("ojos irritados", "vision_irritated_eyes"),
    ("ojos imitados", "vision_irritated_eyes"),
    ("dolores frecuentes de cabeza", "vision_headaches"),
    ("aleja demasiado los objetos", "vision_squints"),
    ("desplazamiento de los", "vision_follows_movement"),
    ("movimientos oculares", "vision_abnormal_movements"),
    ("conductas erroneas", "vision_erroneous_behaviors"),
    ("conductasemoneas", "vision_erroneous_behaviors"),
    ("miopia", "vision_diagnosis"),
    ("estimulos auditivos", "hearing_interested_stimuli"),
    ("voces o sonidos familiares", "hearing_recognizes_voices"),
    ("gira la cabeza", "hearing_turns_head"),
    ("acerca los oidos", "hearing_ears_to_tv"),
    ("tapa o golpea los oidos", "hearing_covers_ears"),
    ("tapaogolpealosoidos", "hearing_covers_ears"),
    ("dolores de oidos", "hearing_earaches"),
    ("pronunciacion oral es adecuada", "hearing_pronunciation_adequate"),
    ("otitis cronica", "hearing_diagnosis"),
    ("hipoacusia", "hearing_diagnosis"),
    ("balbucea", "language_exp_babbles"),
    ("vocaliza", "language_exp_vocalizes_gestures"),
    ("emite palabras", "language_exp_emits_words"),
    ("emite/produce frases", "language_exp_emits_phrases"),
    ("emite produce frases", "language_exp_emits_phrases"),
    ("relata experiencias", "language_exp_relates_experiences"),
    ("pronunciacion/produccion es clara", "language_exp_clear_pronunciation"),
    ("producciones cleara", "language_exp_clear_pronunciation"),
    ("identifica objetos", "language_comp_identifies_objects"),
    ("identifica personas", "language_comp_identifies_people"),
    ("conceptos abstractos", "language_comp_understands_abstract"),
    ("responde en forma coherente", "language_comp_responds_coherently"),
    ("responde en fome coherente", "language_comp_responds_coherently"),
    ("instrucciones simples", "language_comp_follows_simple_instructions"),
    ("instrucciones complejas", "language_comp_follows_complex_instructions"),
    ("instrucciones grupales", "language_comp_follows_group_instructions"),
    ("comprende relatos", "language_comp_understands_stories"),
    ("relaciona espontaneamente", "social_relates_spontaneously"),
    ("explica razones de sus comportamientos", "social_explains_behaviors"),
    ("participa en actividades grupales", "social_participates_groups"),
    ("participa enactividades grupales", "social_participates_groups"),
    ("opta por trabajo individual", "social_prefers_individual"),
    ("lenguaje ecolalico", "social_echolalic_language"),
    ("dificultad para adaptarse", "social_difficulty_adapting"),
    ("forma colaborativa", "social_relates_collaboratively"),
    ("relaciona en forma colaborativa", "social_relates_collaboratively"),
    ("respeta normas sociales", "social_respects_social_norms"),
    ("respeta normas escolares", "social_respects_school_norms"),
    ("sentido del humor", "social_shows_humor"),
    ("movimientos estereotipados", "social_stereotyped_movements"),
    ("pataletas", "social_frequent_tantrums"),
    ("vacunas al dia", "health_vaccines_up_to_date"),
    ("epilepsia", "health_epilepsy"),
    ("problemas cardiacos", "health_heart_problems"),
    ("parapleijia", "health_paraplegia"),
    ("paraplejia", "health_paraplegia"),
    ("perdida auditiva", "health_hearing_loss"),
    ("perdida visual", "health_vision_loss"),
    ("trastomo motor", "health_motor_disorder"),
    ("trastorno motor", "health_motor_disorder"),
    ("bronco-respiratorio", "health_bronchorespiratory"),
    ("infecto-contagiosa", "health_infectious_disease"),
    ("trastomo emocional", "health_emotional_disorder"),
    ("trastorno emocional", "health_emotional_disorder"),
    ("trastomo conductual", "health_behavioral_disorder"),
    ("trastorno conductual", "health_behavioral_disorder"),
    ("asistio a jardin", "attended_kindergarten"),
    ("ha repetido curso", "repeated_grade"),
    ("dificultad para aprendizaje", "learning_difficulty"),
    ("dificultad de aprendizaje", "learning_difficulty"),
    ("dificultad de participar", "participation_difficulty"),
    ("dificultad para participar", "participation_difficulty"),
    ("conducta disruptiva", "disruptive_behavior"),
    ("asiste regularmente", "attends_regularly"),
    ("asiste con agrado", "attends_gladly"),
    ("apoyo familiar en tareas", "family_support_homework"),
    ("apoyofamilliar", "family_support_homework"),
    ("amigos", "friends"),
]


def _find_yn_near_label(norm_text: str, label: str, window: int = 90) -> int | None:
    """Busca Sí/No cerca de una etiqueta OCR. 1=Sí, 2=No (convención anamnesis)."""
    idx = norm_text.find(label)
    if idx < 0:
        return None
    chunk = norm_text[idx : idx + len(label) + window]
    # Preferir token justo después de la etiqueta
    m = re.search(r"\b(si|sí|is|s1|yes)\b", chunk)
    m_no = re.search(r"\bno\b", chunk)
    if m and m_no:
        # el más cercano al final de la etiqueta
        after = len(label)
        d_si = m.start() - after
        d_no = m_no.start() - after
        if d_si >= 0 and (d_no < 0 or d_si <= d_no):
            return 1
        if d_no >= 0:
            return 2
    if m and m.start() >= 0:
        return 1
    if m_no and m_no.start() >= 0:
        return 2
    return None


def _extract_after_label_norm(norm_text: str, labels: list[str], max_len: int = 80) -> str | None:
    for label in labels:
        idx = norm_text.find(_normalize_ocr_text(label))
        if idx < 0:
            continue
        start = idx + len(_normalize_ocr_text(label))
        chunk = norm_text[start : start + max_len].strip(" :.-")
        # cortar en siguiente etiqueta típica
        chunk = re.split(
            r"\b(nombre|fecha|telefono|domicilio|observaciones|sexo|edad|pais)\b",
            chunk,
            maxsplit=1,
        )[0]
        chunk = chunk.strip(" :.-")
        if chunk and len(chunk) >= 1:
            return chunk[:max_len]
    return None


def map_pdf_to_anamnesis_payload(
    *,
    student_id: int,
    text: str,
    fields: dict[str, Any],
    student_name_fallback: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"student_id": student_id}
    mapped_keys: list[str] = []
    norm = _normalize_ocr_text(text or "")

    # 1) AcroForm
    for raw_key, val in (fields or {}).items():
        key_norm = re.sub(r"[_\s]+", " ", str(raw_key).strip().lower())
        key_compact = key_norm.replace(" ", "_")
        target = ACRO_FIELD_MAP.get(key_norm) or ACRO_FIELD_MAP.get(key_compact)
        if not target:
            for alias, dest in ACRO_FIELD_MAP.items():
                if alias in key_norm or alias.replace(" ", "_") in key_compact:
                    target = dest
                    break
        if not target:
            continue
        if target == "born_date":
            parsed = _parse_date_loose(val)
            if parsed:
                payload[target] = parsed
                mapped_keys.append(target)
            continue
        if target in {
            "diagnosis_has",
            "attended_kindergarten",
            "repeated_grade",
            "learning_difficulty",
            "participation_difficulty",
            "disruptive_behavior",
            "attends_regularly",
            "attends_gladly",
            "family_support_homework",
            "friends",
            "birth_medical_assistance",
            "first_year_periodic_health_checkups",
            "first_year_vaccines",
        } or target.startswith(("sm_fine_", "sm_cog_", "sm_walking", "sm_frequent", "vision_", "hearing_", "language_exp_", "language_comp_", "social_", "health_")):
            yn = _yn_to_int(val)
            if yn is not None:
                # anamnesis usa 1=Sí 2=No en varios campos
                payload[target] = 1 if yn == 1 else 2
                mapped_keys.append(target)
            continue
        cleaned = _clean_text(val)
        if cleaned and not _is_garbage_ocr_value(cleaned, dest=target):
            payload[target] = cleaned
            mapped_keys.append(target)

    # 2) Texto etiquetado (capa nativa o OCR)
    for labels, dest in TEXT_LABEL_MAP:
        if dest in payload and payload[dest]:
            continue
        val = _find_labeled_value(text, labels)
        if not val:
            val = _extract_after_label_norm(norm, labels)
        if not val or _is_garbage_ocr_value(val, dest=dest):
            continue
        if dest == "born_date":
            parsed = _parse_date_loose(val)
            if parsed:
                payload[dest] = parsed
                mapped_keys.append(dest)
            continue
        # Lengua: si lo que sigue a la etiqueta son checkboxes de dominio, mapear dominio
        if dest in {"native_language", "language_used"}:
            domain_key = (
                "native_language_domain" if dest == "native_language" else "language_used_domain"
            )
            domain_vals = _parse_language_domain(val)
            if domain_vals and _looks_like_domain_labels_only(val):
                if domain_key not in payload or not payload.get(domain_key):
                    payload[domain_key] = domain_vals
                    mapped_keys.append(domain_key)
                continue
        payload[dest] = val
        mapped_keys.append(dest)

    # 2b) Separar lengua vs grado de dominio (checkboxes)
    _sanitize_language_fields(payload, norm_text=norm, mapped_keys=mapped_keys)

    # 3) Sí/No por etiquetas OCR del formulario Decreto 170
    seen_dest: set[str] = set()
    for label, dest in OCR_YN_LABELS:
        if dest in payload and payload[dest] is not None:
            continue
        if dest in seen_dest and dest != "hearing_diagnosis":
            continue
        yn = _find_yn_near_label(norm, label)
        if yn is None:
            continue
        payload[dest] = yn
        mapped_keys.append(dest)
        seen_dest.add(dest)

    # 4) Tipo de parto / dominio / enums sueltos
    if "birth_type_id" not in payload:
        if re.search(r"\bnormal\b", norm) and "parto" in norm:
            if "cesarea" in norm or "cesárea" in (text or "").lower():
                # si ambos, no forzar
                pass
            payload["birth_type_id"] = 1
            mapped_keys.append("birth_type_id")
        elif "cesarea" in norm or "cesárea" in (text or "").lower():
            payload["birth_type_id"] = 2
            mapped_keys.append("birth_type_id")
        elif "forceps" in norm:
            payload["birth_type_id"] = 4
            mapped_keys.append("birth_type_id")
        elif "inducido" in norm or "asistido" in norm:
            payload["birth_type_id"] = 3
            mapped_keys.append("birth_type_id")

    if "language_communication_method" not in payload:
        if re.search(r"\bmixto\b", norm):
            payload["language_communication_method"] = "Mixto"
            mapped_keys.append("language_communication_method")
        elif re.search(r"\bgestual\b", norm):
            payload["language_communication_method"] = "Gestual"
            mapped_keys.append("language_communication_method")
        elif re.search(r"\boral\b", norm) and "comunica" in norm:
            payload["language_communication_method"] = "Oral"
            mapped_keys.append("language_communication_method")

    if "sm_motor_activity" not in payload:
        for opt in ("hiperactivo", "hipoactivo", "activo", "normal"):
            if opt in norm and "actividad motora" in norm:
                payload["sm_motor_activity"] = opt.capitalize() if opt != "normal" else "Normal"
                if opt == "hiperactivo":
                    payload["sm_motor_activity"] = "Hiperactivo"
                elif opt == "hipoactivo":
                    payload["sm_motor_activity"] = "Hipoactivo"
                elif opt == "activo":
                    payload["sm_motor_activity"] = "Activo"
                mapped_keys.append("sm_motor_activity")
                break

    if "sm_muscle_tone" not in payload:
        if "hipertonico" in norm:
            payload["sm_muscle_tone"] = "Hipertónico"
            mapped_keys.append("sm_muscle_tone")
        elif "hipotonico" in norm:
            payload["sm_muscle_tone"] = "Hipotónico"
            mapped_keys.append("sm_muscle_tone")
        elif "tono muscular" in norm and "normal" in norm:
            payload["sm_muscle_tone"] = "Normal"
            mapped_keys.append("sm_muscle_tone")

    if "sm_lateral_dominance" not in payload:
        if "dominancia lateral" in norm:
            if re.search(r"\b(der|derecha)\b", norm[norm.find("dominancia lateral") : norm.find("dominancia lateral") + 60]):
                payload["sm_lateral_dominance"] = "Der"
                mapped_keys.append("sm_lateral_dominance")
            elif re.search(r"\b(izq|izquierda)\b", norm[norm.find("dominancia lateral") : norm.find("dominancia lateral") + 60]):
                payload["sm_lateral_dominance"] = "Izq"
                mapped_keys.append("sm_lateral_dominance")

    # Alimentación / peso / sueño
    if "health_diet" not in payload:
        if "malo" in norm and "comer" in norm:
            payload["health_diet"] = "Malo"
            mapped_keys.append("health_diet")
        elif "bueno" in norm and "comer" in norm:
            payload["health_diet"] = "Bueno"
            mapped_keys.append("health_diet")
        elif "alimentacion" in norm and "normal" in norm:
            payload["health_diet"] = "Normal"
            mapped_keys.append("health_diet")
    if "health_weight" not in payload:
        if "bajo peso" in norm:
            payload["health_weight"] = "Bajo peso"
            mapped_keys.append("health_weight")
        elif "obesidad" in norm and "peso" in norm:
            payload["health_weight"] = "Obesidad"
            mapped_keys.append("health_weight")
        elif "peso" in norm and "normal" in norm:
            payload["health_weight"] = "Normal"
            mapped_keys.append("health_weight")
    if "health_sleep_pattern" not in payload:
        if "inquieto" in norm and "sueno" in norm:
            payload["health_sleep_pattern"] = "Inquieto"
            mapped_keys.append("health_sleep_pattern")
        elif "sueno" in norm and "normal" in norm:
            payload["health_sleep_pattern"] = "Normal"
            mapped_keys.append("health_sleep_pattern")
    if "health_sleeps_alone" not in payload:
        if "duerme:solo" in norm.replace(" ", "") or "duerme solo" in norm:
            payload["health_sleeps_alone"] = "Solo"
            mapped_keys.append("health_sleeps_alone")
        elif "acompanad" in norm:
            payload["health_sleeps_alone"] = "Acompañado"
            mapped_keys.append("health_sleeps_alone")

    # Condiciones primer año (dict)
    fyc: dict[str, int] = {}
    fyc_map = [
        ("desnutricion", "desnutricion"),
        ("desnuticion", "desnutricion"),
        ("obesidad", "obesidad"),
        ("fiebre alta", "fiebre_alta"),
        ("asma", "asma"),
        ("traumatismos", "traumatismos"),
        ("intoxicacion", "intoxicacion"),
        ("enfermedad respiratoria", "enfermedad_respiratoria"),
        ("hospitalizaciones", "hospitalizaciones"),
        ("encefalitis", "encefalitis"),
        ("meningitis", "meningitis"),
        ("convulsiones", "convulsiones"),
    ]
    for lab, key in fyc_map:
        yn = _find_yn_near_label(norm, lab, window=40)
        if yn is not None:
            fyc[key] = yn
    if fyc:
        payload["first_year_conditions"] = fyc
        mapped_keys.append("first_year_conditions")

    # Identidad: no dejar que OCR pise el nombre
    if student_name_fallback:
        payload["student_full_name"] = student_name_fallback
        mapped_keys.append("student_full_name")

    # Informante (solo si el nombre no parece etiqueta)
    inf_name = _find_labeled_value(text, ["Nombre del informante"])
    inf_rel = _find_labeled_value(text, ["Parentesco", "Relación con el estudiante"])
    if inf_name and not _is_garbage_ocr_value(inf_name, dest="student_full_name"):
        payload["informants"] = [
            {
                "sort_order": 0,
                "name": inf_name[:255],
                "relationship": (inf_rel or "")[:255] or None,
                "presence": None,
                "interview_date": None,
            }
        ]
        mapped_keys.append("informants")

    # Familiares (tabla sección 6)
    household = _extract_household_members(text or "")
    if household:
        payload["household_members"] = household
        mapped_keys.append("household_members")

    # Limpiar basura típica de antecedentes de salud familiar
    fh = payload.get("family_health_history")
    if isinstance(fh, str) and fh.strip():
        cleaned_fh = _clean_family_health_history(fh)
        if cleaned_fh:
            payload["family_health_history"] = cleaned_fh

    # Textos manuscritos frecuentes (OCR ruidoso pero recuperable)
    _fill_common_manuscript_fields(payload, text or "", norm, mapped_keys)

    # Limpiar campos de texto claramente basura de etiquetas
    _drop_garbage_text_fields(payload, mapped_keys)

    if text and len(text) > 200 and not payload.get("final_comments"):
        payload["final_comments"] = (
            "Importado desde PDF escaneado ANAMNESIS (OCR local). "
            "Revisar casillas y textos manuscritos."
        )
        mapped_keys.append("final_comments")

    payload = _truncate_payload_strings(payload)
    payload["_mapped_keys"] = sorted(set(mapped_keys))
    return payload


def _fill_common_manuscript_fields(
    payload: dict[str, Any], text: str, norm: str, mapped_keys: list[str]
) -> None:
    """Recupera frases típicas del formulario aunque el OCR las deforme."""
    if not payload.get("interview_reason"):
        m = re.search(
            r"ingreso\s*al\s*programa\s*pie[^\n.]{0,40}",
            norm,
            flags=re.I,
        )
        if m:
            # reconstruir legible
            payload["interview_reason"] = "Ingreso al Programa PIE."
            mapped_keys.append("interview_reason")

    if not payload.get("rewards"):
        if "expresiones afectivas" in norm or "expresionesafectivas" in norm.replace(" ", ""):
            payload["rewards"] = ["Expresiones afectivas"]
            mapped_keys.append("rewards")

    if not payload.get("health_mood_behavior"):
        if "jugueton" in norm or "bromista" in norm:
            payload["health_mood_behavior"] = "Juguetón/bromista"
            mapped_keys.append("health_mood_behavior")
        elif "alegre" in norm and "humor" in norm:
            payload["health_mood_behavior"] = "Alegre"
            mapped_keys.append("health_mood_behavior")

    if not payload.get("health_problems_treatment"):
        if "pie plano" in norm or "pieplano" in norm.replace(" ", "") or (
            "pie" in norm and "plano" in norm and "ejercicio" in norm
        ):
            payload["health_problems_treatment"] = "Pie plano (ejercicios en el hogar)."
            mapped_keys.append("health_problems_treatment")
        elif re.search(r"pie\s*\{?\s*n?\s*plano|pie\s*\{n", norm):
            payload["health_problems_treatment"] = "Pie plano."
            mapped_keys.append("health_problems_treatment")

    if not payload.get("supporters"):
        found: list[str] = []
        # zona de apoyo: madre/padre marcados cerca de "quien(es) apoyan"
        idx = norm.find("apoyan el proceso") 
        if idx < 0:
            idx = norm.find("quienes apoyan")
        chunk = norm[idx : idx + 220] if idx >= 0 else norm
        if re.search(r"\bmadre\b", chunk):
            found.append("Madre")
        if re.search(r"\bpadre\b", chunk):
            found.append("Padre")
        if re.search(r"herman", chunk):
            found.append("Hermanos/as")
        if "otro" in chunk and "familiar" in chunk:
            found.append("Otros familiares")
        if found:
            payload["supporters"] = found
            mapped_keys.append("supporters")

    if not payload.get("expectations"):
        if "alta (incluye" in norm or "alta(incluye" in norm.replace(" ", ""):
            payload["expectations"] = "alta"
            mapped_keys.append("expectations")
        elif "mediana" in norm and "expectativ" in norm:
            payload["expectations"] = "mediana"
            mapped_keys.append("expectations")
        elif "baja" in norm and "expectativ" in norm:
            payload["expectations"] = "baja"
            mapped_keys.append("expectations")

    # Observaciones "Sin antecedentes" (OCR suele deforma a "Sin auleceu")
    for key in (
        "first_year_observations",
        "sm_observations_1",
        "sm_observations_2",
        "vision_hearing_observations",
        "language_observations",
        "social_observations",
        "health_current_observations",
    ):
        if payload.get(key):
            continue
        # si hay varias menciones deformadas de "sin antecedentes", rellenar genérico
        if re.search(r"sin\s*a[a-z]{0,8}(ced|ule|nte)", norm):
            payload[key] = "Sin antecedentes."
            mapped_keys.append(key)


def _drop_garbage_text_fields(payload: dict[str, Any], mapped_keys: list[str]) -> None:
    """Elimina basura OCR de TODOS los campos string (y limpia household names)."""
    skip = {"final_comments", "student_id", "_mapped_keys", "_seed_from"}
    for key in list(payload.keys()):
        if key in skip:
            continue
        val = payload.get(key)
        if isinstance(val, str):
            if _is_garbage_ocr_value(val, dest=key):
                payload[key] = None
                if key in mapped_keys:
                    try:
                        mapped_keys.remove(key)
                    except ValueError:
                        pass
            elif key in _AGE_FIELD_KEYS:
                payload[key] = _normalize_age_m_abbrev(val)
            continue
        if key == "household_members" and isinstance(val, list):
            cleaned_hh = []
            for i, m in enumerate(val):
                if not isinstance(m, dict):
                    continue
                item = dict(m)
                for fk in ("name", "schooling", "occupation", "age"):
                    fv = item.get(fk)
                    if not isinstance(fv, str):
                        continue
                    if fk == "age":
                        if _is_garbage_ocr_value(fv, dest="age"):
                            item[fk] = None
                        else:
                            item[fk] = _normalize_age_m_abbrev(fv)
                        continue
                    low = _normalize_ocr_text(fv)
                    if (
                        _is_garbage_ocr_value(fv, dest="")
                        or any(j in low for j in _FORM_LABEL_FRAGMENTS)
                        or len(fv.strip()) < 2
                        or re.search(r"desarrollo del|apoyo|expectativ|incluy", low)
                    ):
                        item[fk] = None
                if item.get("name") or item.get("relationship"):
                    item["sort_order"] = len(cleaned_hh)
                    cleaned_hh.append(item)
            payload[key] = cleaned_hh or None
            continue
        if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
            kept = [x for x in val if not _is_garbage_ocr_value(x, dest=key)]
            payload[key] = kept or None


def _normalize_relationship(token: str) -> str | None:
    t = _normalize_ocr_text(token or "")
    t = t.replace(" ", "")
    mapping = (
        (("mama", "madre", "dama"), "Madre"),
        (("papa", "padre"), "Padre"),
        (("hermana", "herman a", "hermana."), "Hermana"),
        (("hermano", "hemmano", "hermano.m", "hermano."), "Hermano"),
        (("abuela",), "Abuela"),
        (("abuelo",), "Abuelo"),
        (("tia", "tía"), "Tía"),
        (("tio", "tío"), "Tío"),
        (("cuidadora", "cuidador"), "Cuidador/a"),
    )
    for keys, label in mapping:
        for k in keys:
            if k.replace(" ", "") in t:
                return label
    return None


def _clean_family_health_history(raw: str) -> str:
    s = raw or ""
    low = _normalize_ocr_text(s)
    parts: list[str] = []
    if "miast" in low or "hiqslemia" in low or "hacking" in low:
        parts.append("Miastenia")
    if "hipot" in low or "hiperti" in low or "ipormid" in low or "iporrid" in low or "porn" in low:
        parts.append("Hipotiroidismo")
    if "mama" in low or "madre" in low:
        parts.append("La mamá")
    if parts:
        return ". ".join(parts) + "."
    # si no reconocemos, devolver limpio corto
    cleaned = re.sub(r"\s+", " ", s).strip()
    return cleaned[:255] if cleaned else ""


def _ocr_fix_schooling(val: str | None) -> str | None:
    if not val:
        return None
    low = _normalize_ocr_text(val)
    if "jardin" in low or "ardin" in low:
        return "Jardín"
    if "bas" in low or "dasi" in low:
        return "Básica"
    if "ens" in low and ("incom" in low or "mka" in low or "mda" in low or "media" in low):
        return "Ens. media incompleta"
    if "ens" in low or "media" in low:
        return "Ens. media"
    if "estu" in low:
        return None  # suele ser ocupación
    cleaned = re.sub(r"\s+", " ", val).strip(" .")
    return cleaned[:80] if cleaned else None


def _ocr_fix_occupation(val: str | None) -> str | None:
    if not val:
        return None
    low = _normalize_ocr_text(val)
    if "duena" in low or "dueña" in low or "casa" in low:
        return "Dueña de casa"
    if "temp" in low or "iemoiem" in low:
        return "Temporal"
    if "estu" in low:
        return "Estudiante"
    if "cesante" in low:
        return "Cesante"
    cleaned = re.sub(r"\s+", " ", val).strip(" .")
    if len(cleaned) < 3:
        return None
    return cleaned[:80]


def _extract_household_members(text: str) -> list[dict[str, Any]]:
    """Parsea la tabla de familiares desde OCR (RapidOCR/EasyOCR)."""
    if not text:
        return []
    norm_lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    start = end = None
    for i, ln in enumerate(norm_lines):
        low = _normalize_ocr_text(ln)
        if start is None and ("antecedentes familiares" in low or "personas que viven" in low):
            start = i
            continue
        if start is not None and (
            "antecedentes de salud de la familia" in low
            or "antecedentes escolares" in low
            or "los datos contenidos" in low
        ):
            end = i
            break
    # Solo dentro del bloque familiar (evitar "madre/padre" de sección apoyo escolar)
    family_block_text = (
        "\n".join(norm_lines[start:end]) if start is not None else ""
    )
    flat = _household_from_flat_blob(family_block_text) if family_block_text else []
    rapid_rows: list[dict[str, Any]] = []
    if start is not None:
        block = norm_lines[start : end if end is not None else start + 50]
        # dividir por marcadores 1. 2. 3. ...
        chunks: list[list[str]] = []
        cur: list[str] = []
        for ln in block:
            if re.fullmatch(r"\d+\.?", ln.strip()):
                if cur:
                    chunks.append(cur)
                cur = []
                continue
            low = _normalize_ocr_text(ln)
            if low in {
                "nombre",
                "parentesco",
                "edad",
                "escolaridad",
                "ocupacion actual",
                "ocupacionactual",
                "6.",
                "antecedentes familiares",
            } or "personas que viven" in low:
                continue
            cur.append(ln.strip())
        if cur:
            chunks.append(cur)
        for idx, lines in enumerate(chunks[:8]):
            name = None
            rel = None
            age = None
            schooling_raw = None
            occupation_raw = None
            for ln in lines:
                r = _normalize_relationship(ln)
                if r and not rel:
                    rel = r
                    continue
                am = re.fullmatch(r"(\d{1,2})\.?", ln.strip())
                if am and not age:
                    age = am.group(1)
                    continue
                low = _normalize_ocr_text(ln)
                if not name and re.search(r"[A-Za-zÁÉÍÓÚáéíóú]{3,}", ln) and not r:
                    # evitar tokens de escolaridad/ocupación como nombre
                    if not any(k in low for k in ("ens", "bas", "dasi", "duena", "temp", "incom", "estu", "cole", "ardin")):
                        name = re.sub(r"\s+", " ", ln).strip(" .")[:120]
                        continue
                if any(k in low for k in ("ens", "bas", "dasi", "jardin", "ardin", "incom", "media")):
                    schooling_raw = (schooling_raw or "") + " " + ln
                    continue
                if any(k in low for k in ("duena", "temp", "iemoiem", "incomg", "estu", "cesante")):
                    occupation_raw = (occupation_raw or "") + " " + ln
                    continue
            if not name and not rel:
                continue
            rapid_rows.append(
                {
                    "sort_order": idx,
                    "name": name,
                    "relationship": rel,
                    "age": age,
                    "schooling": _ocr_fix_schooling(schooling_raw),
                    "occupation": _ocr_fix_occupation(occupation_raw),
                }
            )

    # Merge: flat da relaciones; rapid da nombres más limpios
    by_rel: dict[str, dict[str, Any]] = {}
    for src in (flat, rapid_rows):
        for m in src:
            rel = m.get("relationship")
            if not rel:
                continue
            cur = by_rel.get(rel)
            if not cur:
                by_rel[rel] = dict(m)
                continue
            for k in ("name", "age", "schooling", "occupation"):
                # preferir valor más limpio (sin símbolos raros)
                cand = m.get(k)
                if not cand:
                    continue
                old = cur.get(k)
                if not old:
                    cur[k] = cand
                elif old and cand and sum(ch.isalnum() or ch.isspace() for ch in str(cand)) > sum(
                    ch.isalnum() or ch.isspace() for ch in str(old)
                ):
                    cur[k] = cand

    # Si rapid tiene filas sin rel pero flat tiene Madre/Padre en orden, asignar
    order = ["Madre", "Padre", "Hermana", "Hermano", "Abuela", "Abuelo", "Tía", "Tío"]
    out: list[dict[str, Any]] = []
    for i, rel in enumerate(order):
        if rel not in by_rel:
            continue
        m = by_rel[rel]
        name = m.get("name")
        if isinstance(name, str):
            name = re.sub(r"[^0-9A-Za-zÁÉÍÓÚáéíóúñÑ\s\-]", "", name).strip()
            name = re.sub(r"\s+", " ", name)[:120] or None
        out.append(
            {
                "sort_order": len(out),
                "name": name,
                "relationship": rel,
                "age": m.get("age"),
                "schooling": _ocr_fix_schooling(m.get("schooling")),
                "occupation": _ocr_fix_occupation(m.get("occupation")),
            }
        )
    return out


def _household_from_flat_blob(blob: str) -> list[dict[str, Any]]:
    """Parte un texto continuo usando tokens Madre/Padre/Hermana/Hermano."""
    s = " " + (blob or "") + " "
    # insertar marcadores
    patterns = [
        (r"(?i)\b(mama|madre|dama)\b", "Madre"),
        (r"(?i)\b(papa|padre)\b", "Padre"),
        (r"(?i)\b(herman\s*a|hermana)\b", "Hermana"),
        (r"(?i)\b(herman\s*o|hermano|hemmano)\b", "Hermano"),
    ]
    marks: list[tuple[int, int, str]] = []
    for pat, label in patterns:
        for m in re.finditer(pat, s):
            marks.append((m.start(), m.end(), label))
    marks.sort(key=lambda x: x[0])
    if not marks:
        return []
    members: list[dict[str, Any]] = []
    for i, (a, b, rel) in enumerate(marks):
        prev = marks[i - 1][1] if i else 0
        left = s[prev:a].strip(" |,;.-")
        right = s[b : (marks[i + 1][0] if i + 1 < len(marks) else len(s))].strip(" |,;.-")
        name = None
        # nombre suele estar a la izquierda del parentesco
        left_tokens = [t for t in re.split(r"\s+", left) if t]
        if left_tokens:
            # tomar últimas 2-3 palabras como nombre
            name = " ".join(left_tokens[-3:]).strip(" .")[:120]
            name = re.sub(r"^\d+\.?", "", name).strip()
        age = None
        m_age = re.search(r"\b(\d{1,2})\b", right) or re.search(r"\b(\d{1,2})\b", left)
        if m_age:
            age = m_age.group(1)
        schooling = None
        occupation = None
        right_l = _normalize_ocr_text(right)
        if "ens" in right_l or "bas" in right_l or "estu" in right_l or "jardin" in right_l:
            schooling = re.sub(r"\s+", " ", right).strip()[:80]
        if "temp" in right_l or "incom" in right_l or "duena" in right_l:
            occupation = re.sub(r"\s+", " ", right).strip()[:80]
        if name and _normalize_relationship(name):
            name = None
        members.append(
            {
                "sort_order": len(members),
                "name": name or None,
                "relationship": rel,
                "age": age,
                "schooling": schooling,
                "occupation": occupation,
            }
        )
    return members[:8]


def _student_display_name(db: Session, student_id: int) -> str | None:
    personal = (
        db.query(StudentPersonalInfoModel)
        .filter(StudentPersonalInfoModel.student_id == student_id)
        .order_by(StudentPersonalInfoModel.id.desc())
        .first()
    )
    if not personal:
        return None
    parts = [
        (personal.names or "").strip(),
        (personal.father_lastname or "").strip(),
        (personal.mother_lastname or "").strip(),
    ]
    name = " ".join(p for p in parts if p).strip()
    return name or None


def _has_anamnesis(db: Session, student_id: int) -> bool:
    row = (
        db.query(AnamnesisModel.id)
        .filter(AnamnesisModel.student_id == student_id)
        .order_by(AnamnesisModel.id.desc())
        .first()
    )
    return bool(row)


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _merge_payloads(seed: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    """OCR/AcroForm rellena huecos; identidad de ficha siempre gana. Conserva mapped_keys."""
    seed_keys = set(seed.pop("_mapped_keys", []) or [])
    ext_keys = set(extracted.pop("_mapped_keys", []) or [])
    seed.pop("_seed_from", None)
    extracted.pop("_seed_from", None)
    out = dict(seed)
    for k, v in extracted.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, str) and _is_garbage_ocr_value(v, dest=k):
            continue
        if k in SEED_PREFERRED_KEYS and out.get(k) not in (None, "", []):
            continue
        out[k] = v
        ext_keys.add(k)
    mapped = sorted(seed_keys | ext_keys)
    _drop_garbage_text_fields(out, mapped)
    out = _truncate_payload_strings(out)
    out["_mapped_keys"] = sorted(set(mapped))
    return out


def process(*, apply: bool, limit: int | None, download: bool) -> dict[str, int]:
    db = _new_db()
    counts = {
        "total": 0,
        "ok": 0,
        "not_found": 0,
        "ambiguous": 0,
        "no_name": 0,
        "error": 0,
        "applied": 0,
    }
    rows_out: list[dict] = []
    token = None
    token_at = 0.0
    try:
        print("Listando PDFs en Drive ANAMNESIS...", flush=True)
        pdfs = _list_anamnesis_pdfs(db)
        print(f"PDFs encontrados: {len(pdfs)}", flush=True)
        if limit is not None:
            pdfs = pdfs[: max(0, int(limit))]
            print(f"Limitando a: {len(pdfs)}", flush=True)

        print("Indexando RUTs y nombres...", flush=True)
        rut_index = _build_student_rut_index(db)
        name_index = _build_student_name_index(db)
        existing_anamnesis = {
            int(r[0])
            for r in db.query(AnamnesisModel.student_id).distinct().all()
            if r[0] is not None
        }
        print(
            f"RUTs={len(rut_index)} nombres={len(name_index)} "
            f"con_anamnesis={len(existing_anamnesis)}",
            flush=True,
        )

        do_download = bool(apply or download)
        if do_download:
            token = _access_token(db)
            token_at = time.time()

        for i, pdf in enumerate(pdfs, start=1):
            counts["total"] += 1
            name = pdf["name"]
            drive_id = pdf["id"]
            path = pdf["path"]
            status = "error"
            message = ""
            student_id: int | None = None
            match_by = ""
            meta = _parse_filename_meta(name)
            file_person = meta.get("person_name") or ""
            course_grade = meta.get("course_grade")
            course_letter = meta.get("course_letter")
            course_label = meta.get("course_label") or ""
            rut_digits = _extract_rut_from_filename(name)
            ya_tiene = ""
            extractable = False
            text_len = 0
            acro_n = 0
            mapped_n = 0
            sample_name = ""
            sample_reason = ""
            sample_diag = ""
            anamnesis_id = ""
            version = ""
            folder_id = ""
            pdf_filename = ""
            content: bytes | None = None
            text = ""
            fields: dict[str, Any] = {}

            try:
                # --- match ---
                matches: list[int] = []
                if rut_digits:
                    matches = list(rut_index.get(rut_digits) or [])
                    if not matches and len(rut_digits) == 8:
                        matches = list(rut_index.get(rut_digits[:-1]) or [])
                    if matches:
                        match_by = "rut"

                if not matches and file_person:
                    st, ids, detail = _match_student_by_name(
                        file_person,
                        name_index,
                        course_grade=course_grade,
                        course_letter=course_letter,
                    )
                    if st == "ok":
                        matches = ids
                        match_by = "name+course" if course_grade else "name"
                        message = detail
                    elif st == "ambiguous":
                        status = "ambiguous"
                        message = detail
                        counts["ambiguous"] += 1
                    else:
                        message = detail

                if status == "ambiguous":
                    pass
                elif not matches:
                    if not file_person and not rut_digits:
                        status = "no_name"
                        message = "Sin RUT ni nombre usable en archivo"
                        counts["no_name"] += 1
                    else:
                        status = "not_found"
                        message = message or (
                            f"No match para '{file_person or rut_digits}' "
                            f"curso={course_label or '-'}"
                        )
                        counts["not_found"] += 1
                elif len(matches) > 1:
                    status = "ambiguous"
                    message = f"múltiples students={matches}"
                    counts["ambiguous"] += 1
                else:
                    student_id = matches[0]
                    ya_tiene = "si" if student_id in existing_anamnesis else "no"
                    sample_name = next(
                        (r["full_name"] for r in name_index if r["student_id"] == student_id),
                        "",
                    )[:120]

                    if do_download:
                        if token is None or time.time() - token_at > 3000:
                            token = _access_token(db)
                            token_at = time.time()
                        assert token is not None
                        content = _download_drive_file(token, drive_id)
                        text, fields = _pdf_text_and_fields(content)
                        text_len = len(text or "")
                        acro_n = len(fields or {})
                        extractable = text_len > 40 or acro_n > 0
                        if not rut_digits:
                            rut_digits = _extract_rut_from_text(text) or rut_digits

                    if not apply:
                        # Dry-run rápido: solo match (curso+nombre). Seed/PDF en --apply.
                        mapped_n = 0
                        status = "ok"
                        message = (
                            f"dry-run; match={match_by}; curso={course_label or '-'}; "
                            f"prev={ya_tiene}"
                        )
                        counts["ok"] += 1
                    else:
                        if token is None or time.time() - token_at > 3000:
                            token = _access_token(db)
                            token_at = time.time()
                        assert token is not None
                        content = _download_drive_file(token, drive_id)
                        text, fields = _pdf_text_and_fields(content)
                        text_len = len(text or "")
                        acro_n = len(fields or {})
                        extractable = text_len > 40 or acro_n > 0

                        seed = _seed_payload_from_student(db, student_id)
                        extracted = map_pdf_to_anamnesis_payload(
                            student_id=student_id,
                            text=text,
                            fields=fields,
                            student_name_fallback=_student_display_name(db, student_id),
                        )
                        payload = _merge_payloads(seed, extracted)
                        mapped_keys = payload.pop("_mapped_keys", [])
                        mapped_n = len(mapped_keys)
                        sample_name = str(payload.get("student_full_name") or sample_name)[:120]
                        sample_reason = str(payload.get("interview_reason") or "")[:160]
                        sample_diag = str(payload.get("diagnosis_detail") or "")[:160]

                        store = AnamnesisClass(db).store(payload)
                        if isinstance(store, dict) and store.get("status") == "error":
                            raise RuntimeError(store.get("message") or "Error store anamnesis")
                        anamnesis_id = str(store.get("id") or "")
                        version = str(store.get("version") or "")

                        period_year = "2026"
                        drive_meta = _resolve_drive_meta(
                            db, student_id=student_id, period_year=period_year
                        )
                        pdf_filename = f"{student_id}_{ANAMNESIS_DOCUMENT_ID}_anamnesis_drive.pdf"
                        target = _student_files_dir() / pdf_filename
                        target.write_bytes(content)

                        folder_store = FolderClass(db).store(
                            student_id=student_id,
                            document_id=ANAMNESIS_DOCUMENT_ID,
                            file_path=pdf_filename,
                            school_id=drive_meta["school_id"],
                            course_id=drive_meta.get("course_id"),
                            period_year=period_year,
                        )
                        if isinstance(folder_store, dict) and folder_store.get("status") == "error":
                            status = "partial"
                            message = (
                                f"Form OK id={anamnesis_id} pero PDF local falló: "
                                f"{folder_store.get('message')}"
                            )
                        else:
                            folder_id = str(folder_store.get("id") or "")
                            folder_row = (
                                db.query(FolderModel)
                                .filter(FolderModel.id == int(folder_id))
                                .first()
                            )
                            if folder_row and anamnesis_id:
                                folder_row.detail_id = int(anamnesis_id)
                                db.commit()

                            # Subir al árbol Drive igual que al cargar un documento en PIE360
                            drive_status = "pending"
                            drive_path = ""
                            try:
                                drive_payload = upload_student_document_tree(
                                    db=db,
                                    customer_id=drive_meta["customer_id"],
                                    school_name=drive_meta["school_name"],
                                    year=drive_meta["year"],
                                    course_name=drive_meta["course_name"],
                                    student_rut=drive_meta["student_rut"],
                                    document_type_name=drive_meta["document_type_name"],
                                    data=content,
                                    file_extension="pdf",
                                    mime_type="application/pdf",
                                )
                                drive_status = "ok"
                                drive_path = drive_payload.get("drive_path") or ""
                                sync = StudentDriveSyncClass(db)
                                job = sync.enqueue(
                                    folder_id=int(folder_id),
                                    student_id=student_id,
                                    document_id=ANAMNESIS_DOCUMENT_ID,
                                    file_path=f"system/students/{pdf_filename}",
                                    mime_type="application/pdf",
                                )
                                job.status = "completed"
                                job.drive_file_id = drive_payload.get("file_id")
                                job.drive_path = drive_path
                                job.last_error = None
                                db.commit()
                            except Exception as drive_exc:
                                drive_status = "error"
                                try:
                                    StudentDriveSyncClass(db).enqueue(
                                        folder_id=int(folder_id),
                                        student_id=student_id,
                                        document_id=ANAMNESIS_DOCUMENT_ID,
                                        file_path=f"system/students/{pdf_filename}",
                                        mime_type="application/pdf",
                                    )
                                except Exception:
                                    try:
                                        db.rollback()
                                    except Exception:
                                        pass
                                message_drive = str(drive_exc)[:180]
                            else:
                                message_drive = drive_path

                            status = "ok" if drive_status == "ok" else "partial"
                            message = (
                                f"Anamnesis v{version} id={anamnesis_id}; "
                                f"folder={folder_id}; mapped={mapped_n}; "
                                f"drive={drive_status} {message_drive}; match={match_by}"
                            )
                        counts["ok"] += 1
                        counts["applied"] += 1
            except Exception as exc:
                status = "error"
                message = f"{type(exc).__name__}: {exc}"[:400]
                counts["error"] += 1
                try:
                    db.rollback()
                except Exception:
                    db = _new_db()

            row = {
                "n": i,
                "status": status,
                "message": message,
                "drive_file_id": drive_id,
                "archivo": name,
                "ruta_drive": path,
                "nombre_archivo": file_person,
                "curso_archivo": course_label,
                "match_by": match_by,
                "rut_digits": rut_digits or "",
                "student_id": student_id or "",
                "ya_tiene_anamnesis": ya_tiene,
                "extractable": "si" if extractable else "no",
                "text_len": text_len,
                "acro_fields": acro_n,
                "campos_mapeados": mapped_n,
                "sample_student_full_name": sample_name,
                "sample_interview_reason": sample_reason,
                "sample_diagnosis_detail": sample_diag,
                "anamnesis_id": anamnesis_id,
                "version": version,
                "folder_id": folder_id,
                "pdf_filename": pdf_filename,
            }
            rows_out.append(row)
            if i % 50 == 0 or i == len(pdfs) or i <= 5:
                print(
                    f"[{i}/{len(pdfs)}] {status} {name} curso={course_label or '-'} "
                    f"match={match_by} student={student_id} mapped={mapped_n}",
                    flush=True,
                )
    finally:
        try:
            db.close()
        except Exception:
            pass

    out_csv = APPLY_CSV if apply else DRY_CSV
    fields = APPLY_FIELDS if apply else DRY_FIELDS
    _write_csv(out_csv, fields, rows_out)
    print(f"CSV: {out_csv}", flush=True)
    print("counts", counts, flush=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar anamnesis Drive → PIE360")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Solo inventario/match (default si no hay --apply)",
    )
    parser.add_argument("--apply", action="store_true", help="Escribe en BD")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de PDFs")
    parser.add_argument(
        "--download",
        action="store_true",
        help="En dry-run también descarga PDF para medir texto/OCR",
    )
    args = parser.parse_args()
    apply = bool(args.apply)
    print(
        f"mode={'APPLY' if apply else 'DRY-RUN'} limit={args.limit} "
        f"download={apply or args.download} db={_db_url().split('@')[-1]}",
        flush=True,
    )
    process(apply=apply, limit=args.limit, download=bool(args.download))


if __name__ == "__main__":
    main()
