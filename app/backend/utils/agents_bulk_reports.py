"""Informes masivos por curso desde el chat de agentes."""

from __future__ import annotations

import re
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models.pie_core import (
    CourseModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentModel,
    StudentPersonalInfoModel,
)

MAX_BULK_STUDENTS = 45
PSYCHOPED_DOCUMENT_ID = 27
FAMILIA_DOCUMENT_ID = 7

_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_PLACE_RE = re.compile(
    r"\b(liceo|colegio|escuela|establecimiento|unidad\s+educativa)\b",
    re.IGNORECASE,
)
_COURSE_WORD_RE = re.compile(r"\b(curso|cursos)\b", re.IGNORECASE)
_INFORME_RE = re.compile(r"\b(informe|informes|documento|documentos)\b", re.IGNORECASE)
_RUT_RE = re.compile(
    r"\b(\d{1,2}[.\s]?\d{3}[.\s]?\d{3}[-\s]?[\dkK]|\d{7,8}[-\s]?[\dkK])\b",
    re.IGNORECASE,
)
# «informe de Isabella» (un alumno) vs «informes del liceo / del curso» (masivo)
_SINGLE_STUDENT_RE = re.compile(
    r"\b(informe|informde|documento)\s+"
    r"(a\s+la\s+familia\s+|psicopedag\w*\s+)?"
    r"(de|del|para)\s+"
    r"(?!liceo|colegio|escuela|establecimiento|curso|todos\b)",
    re.IGNORECASE,
)
_ASK_MARKER = "Para continuar con los informes del curso"
_CONFIRM_MARKER = "Confirma para generar los informes del curso"
_CONFIRM_RE = re.compile(
    r"^\s*(s[ií]|ok|okay|dale|adelante|confirmo|confirma|continuar|contin[uú]a|"
    r"genera|generar|procede|de acuerdo)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

_ORDINAL_RE = re.compile(r"[°º.]")


def _fold(value: str) -> str:
    raw = unicodedata.normalize("NFKD", value or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = raw.lower().replace("°", " ").replace("º", " ")
    raw = _ORDINAL_RE.sub(" ", raw)
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _conversation_text(message: str, history: list[dict[str, str]] | None) -> str:
    parts = [message or ""]
    for item in history or []:
        parts.append(item.get("content") or "")
    return "\n".join(parts)


def _user_blob(message: str, history: list[dict[str, str]] | None) -> str:
    parts: list[str] = []
    for item in history or []:
        if (item.get("role") or "") == "user":
            parts.append(item.get("content") or "")
    parts.append(message or "")
    return "\n".join(parts)


def _last_assistant(history: list[dict[str, str]] | None) -> str:
    for item in reversed(history or []):
        if (item.get("role") or "") == "assistant":
            return item.get("content") or ""
    return ""


def _looks_like_single_student(message: str) -> bool:
    """Pedido de un solo estudiante (nombre o RUT): no es masivo."""
    text = (message or "").strip()
    if not text:
        return False
    if _RUT_RE.search(text):
        return True
    return bool(_SINGLE_STUDENT_RE.search(text))


def user_confirmed_bulk(message: str) -> bool:
    return bool(_CONFIRM_RE.match((message or "").strip()))


def looks_like_bulk_request(
    message: str, history: list[dict[str, str]] | None = None
) -> bool:
    """True si el usuario pide informes de un liceo/curso (no de un alumno)."""
    text = (message or "").strip()
    low = text.lower()
    if not text:
        return False

    assistant = _last_assistant(history)
    in_bulk_flow = _ASK_MARKER.lower() in assistant.lower()
    if in_bulk_flow:
        return True

    # Uno a uno: RUT o «informe de <nombre>» → el chat pide RUT como siempre.
    if _looks_like_single_student(text):
        return False

    has_informe = bool(_INFORME_RE.search(text))
    has_place = bool(_PLACE_RE.search(text))
    has_curso = bool(_COURSE_WORD_RE.search(text))
    if has_informe and (has_place or has_curso):
        return True
    if has_place and ("familia" in low or "psicoped" in low):
        return True
    blob = _conversation_text(text, history).lower()
    if _ASK_MARKER.lower() in blob and (
        _YEAR_RE.search(text)
        or _looks_like_course_reply(text)
        or user_confirmed_bulk(text)
    ):
        return True
    return False


def _looks_like_course_reply(text: str) -> bool:
    folded = _fold(text)
    if not folded:
        return False
    if re.search(r"\b\d{1,2}\s*(medio|basico|básico|basica|básica|kinder|prekinder)\b", folded):
        return True
    if re.search(r"\b(prekinder|kinder|medio|basico|basica)\b", folded) and len(folded) < 40:
        return True
    return False


def extract_year(message: str, history: list[dict[str, str]] | None = None) -> int | None:
    blob = _user_blob(message, history)
    years = [int(y) for y in _YEAR_RE.findall(blob)]
    if not years:
        return None
    return years[-1]


def _extract_school_query(text: str) -> str | None:
    folded_src = text or ""
    m = re.search(
        r"((?:liceo|colegio|escuela|establecimiento)\s+(?:de\s+|del\s+|la\s+|el\s+)?(.+))$",
        folded_src,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        tail = m.group(1)
        tail = re.split(
            r"\b(curso|año|ano|familia|psicoped|informe|document)\b",
            tail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        q = tail.strip(" .,;:-")
        if len(_fold(q)) >= 3:
            return q.strip()
    return None


@dataclass
class BulkPlan:
    active: bool
    school_id: int | None = None
    school_name: str | None = None
    year: int | None = None
    course_id: int | None = None
    course_name: str | None = None
    ask: str | None = None
    students: list[dict[str, Any]] = field(default_factory=list)


def _schools_for_customer(db: Session, customer_id: int) -> list[SchoolModel]:
    q = db.query(SchoolModel).filter(SchoolModel.customer_id == int(customer_id))
    try:
        q = q.filter(SchoolModel.deleted_status_id == 0)
    except Exception:
        pass
    return q.order_by(SchoolModel.school_name.asc()).all()


def match_school(
    db: Session, customer_id: int, query: str | None
) -> tuple[SchoolModel | None, list[SchoolModel]]:
    schools = _schools_for_customer(db, customer_id)
    if not schools:
        return None, []
    q = _fold(query or "")
    if not q:
        return None, schools
    scored: list[tuple[int, SchoolModel]] = []
    for school in schools:
        name = _fold(school.school_name or "")
        if not name:
            continue
        score = 0
        if q == name or q in name or name in q:
            score = 100 if q == name else 80
        else:
            tokens = [t for t in q.split() if len(t) >= 3]
            if tokens and all(t in name for t in tokens):
                score = 50 + 5 * len(tokens)
        if score:
            scored.append((score, school))
    if not scored:
        return None, schools
    scored.sort(key=lambda x: -x[0])
    best = scored[0][0]
    top = [s for sc, s in scored if sc == best]
    if len(top) == 1:
        return top[0], schools
    return None, top


def _courses_for_school(db: Session, school_id: int, year: int | None) -> list[CourseModel]:
    q = db.query(CourseModel).filter(CourseModel.school_id == int(school_id))
    try:
        q = q.filter(CourseModel.deleted_status_id == 0)
    except Exception:
        pass
    if year:
        q = q.filter(CourseModel.period_year == int(year))
    return q.order_by(CourseModel.course_name.asc()).all()


def match_course(
    db: Session, school_id: int, year: int | None, query: str | None
) -> tuple[CourseModel | None, list[CourseModel]]:
    courses = _courses_for_school(db, school_id, year)
    if not courses:
        return None, []
    q = _fold(query or "")
    if not q:
        return None, courses
    # quitar ruido
    q = re.sub(r"\b(curso|del|de|el|la|los|las|año|ano|20\d{2})\b", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    scored: list[tuple[int, CourseModel]] = []
    for course in courses:
        name = _fold(course.course_name or "")
        if not name:
            continue
        score = 0
        if q == name or q in name or name in q:
            score = 100 if q == name else 85
        else:
            qt = [t for t in q.split() if t]
            nt = [t for t in name.split() if t]
            if qt and all(t in name for t in qt):
                score = 60 + 8 * len(qt)
            elif qt and nt and qt[0] == nt[0]:
                score = 40
        if score:
            scored.append((score, course))
    if not scored:
        return None, courses
    scored.sort(key=lambda x: -x[0])
    best = scored[0][0]
    top = [c for sc, c in scored if sc == best]
    if len(top) == 1:
        return top[0], courses
    return None, top


def _course_query_from_text(text: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    m = re.search(
        r"(?:curso\s+)?(\d{1,2}\s*°?\s*(?:medio|b[aá]sico|b[aá]sica)[^\n,]{0,40})",
        raw,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    if _looks_like_course_reply(raw):
        cleaned = re.sub(r"\b20\d{2}\b", " ", raw).strip()
        return cleaned or None
    return None


def list_course_students(
    db: Session, *, school_id: int, course_id: int, year: int
) -> list[dict[str, Any]]:
    rows = (
        db.query(StudentModel, StudentPersonalInfoModel)
        .outerjoin(
            StudentPersonalInfoModel,
            StudentPersonalInfoModel.student_id == StudentModel.id,
        )
        .join(
            StudentAcademicInfoModel,
            StudentAcademicInfoModel.student_id == StudentModel.id,
        )
        .filter(
            StudentModel.deleted_status_id == 0,
            StudentModel.school_id == int(school_id),
            StudentAcademicInfoModel.course_id == int(course_id),
            StudentModel.period_year == str(int(year)),
        )
        .order_by(
            StudentPersonalInfoModel.father_lastname.asc(),
            StudentPersonalInfoModel.names.asc(),
        )
        .all()
    )
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for student, personal in rows:
        sid = int(student.id)
        if sid in seen:
            continue
        seen.add(sid)
        names = (getattr(personal, "names", None) or "").strip() if personal else ""
        father = (getattr(personal, "father_lastname", None) or "").strip() if personal else ""
        mother = (getattr(personal, "mother_lastname", None) or "").strip() if personal else ""
        full = " ".join(p for p in (names, father, mother) if p).strip() or f"Estudiante {sid}"
        rut = (
            (getattr(personal, "identification_number", None) or "").strip()
            if personal
            else ""
        ) or (getattr(student, "identification_number", None) or "").strip()
        out.append({"id": sid, "name": full, "rut": rut})
    return out


def _doc_label(document_id: int | None, agent_name: str | None) -> str:
    if document_id == PSYCHOPED_DOCUMENT_ID or (
        agent_name and "psicoped" in (agent_name or "").lower()
    ):
        return "Informe de Evaluación Psicopedagógica"
    if document_id == FAMILIA_DOCUMENT_ID or (
        agent_name and "familia" in (agent_name or "").lower()
    ):
        return "Informe a la Familia"
    return "informe"


def _format_course_list(courses: list[CourseModel]) -> str:
    names = [(c.course_name or "").strip() or f"Curso {c.id}" for c in courses[:40]]
    if not names:
        return "(sin cursos)"
    return ", ".join(names)


def files_mention_student(files_block: str, name: str, rut: str | None) -> bool:
    """True si el contexto de Files parece corresponder a ese estudiante."""
    blob = _fold(files_block or "")
    if not blob or "sin trozos relevantes" in blob:
        return False
    rut_digits = re.sub(r"[^0-9kK]", "", rut or "").lower()
    blob_digits = re.sub(r"[^0-9k]", "", blob)
    if len(rut_digits) >= 8 and rut_digits in blob_digits:
        return True
    tokens = [t for t in _fold(name).split() if len(t) >= 3]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in blob)
    return hits >= min(2, len(tokens))


def resolve_bulk_plan(
    db: Session,
    *,
    customer_id: int,
    message: str,
    history: list[dict[str, str]] | None,
    document_id: int | None,
    agent_name: str | None,
    default_year: int | None = None,
    session_school_id: int | None = None,
) -> BulkPlan | None:
    if not looks_like_bulk_request(message, history):
        return None

    label = _doc_label(document_id, agent_name)
    user_text = _user_blob(message, history)
    year = extract_year(message, history) or (
        int(default_year) if default_year and 2000 <= int(default_year) <= 2100 else None
    )
    school_q = _extract_school_query(user_text) or _extract_school_query(message)
    school, school_opts = match_school(db, customer_id, school_q)

    if school is None and session_school_id and not school_q:
        for opt in school_opts or _schools_for_customer(db, customer_id):
            if int(opt.id) == int(session_school_id):
                school = opt
                break

    if school is None:
        if len(school_opts) == 1:
            school = school_opts[0]
        elif school_opts and school_q:
            names = ", ".join((s.school_name or "").strip() for s in school_opts[:12])
            return BulkPlan(
                active=True,
                year=year,
                ask=(
                    f"{_ASK_MARKER}. Hay varios establecimientos que coinciden. "
                    f"Indica el nombre exacto: {names}."
                ),
            )
        else:
            names = ", ".join(
                (s.school_name or "").strip() for s in _schools_for_customer(db, customer_id)[:15]
            )
            return BulkPlan(
                active=True,
                year=year,
                ask=(
                    f"{_ASK_MARKER}. Indica el liceo o colegio (nombre) para elaborar "
                    f"el {label}. Establecimientos: {names}."
                ),
            )

    if year is None:
        courses_preview = _courses_for_school(db, int(school.id), None)
        years = sorted(
            {
                int(c.period_year)
                for c in courses_preview
                if c.period_year
            },
            reverse=True,
        )
        year_hint = ", ".join(str(y) for y in years[:6]) if years else "2026"
        return BulkPlan(
            active=True,
            school_id=int(school.id),
            school_name=school.school_name,
            ask=(
                f"{_ASK_MARKER} de **{(school.school_name or '').strip()}**. "
                f"Indica el **año** (ej. {year_hint}) y el **curso** "
                f"(ej. 1° Medio A)."
            ),
        )

    course_q = _course_query_from_text(message)
    if not course_q:
        course_q = _course_query_from_text(user_text)
    course, course_opts = match_course(db, int(school.id), year, course_q)
    if course is None:
        listed = _format_course_list(course_opts)
        return BulkPlan(
            active=True,
            school_id=int(school.id),
            school_name=school.school_name,
            year=year,
            ask=(
                f"{_ASK_MARKER} de **{(school.school_name or '').strip()}**, año **{year}**. "
                f"Indica el curso. Cursos {year}: {listed}."
            ),
        )

    students = list_course_students(
        db, school_id=int(school.id), course_id=int(course.id), year=int(year)
    )
    if not students:
        return BulkPlan(
            active=True,
            school_id=int(school.id),
            school_name=school.school_name,
            year=year,
            course_id=int(course.id),
            course_name=course.course_name,
            ask=(
                f"No hay estudiantes activos en **{(course.course_name or '').strip()}** "
                f"({(school.school_name or '').strip()}, {year}). "
                "Verifica el curso y el año."
            ),
        )

    return BulkPlan(
        active=True,
        school_id=int(school.id),
        school_name=school.school_name,
        year=year,
        course_id=int(course.id),
        course_name=course.course_name,
        students=students,
    )


def bulk_document_label(document_id: int | None, agent_name: str | None) -> str:
    return _doc_label(document_id, agent_name)


def bulk_confirm_ask(
    *,
    course_name: str,
    school_name: str,
    year: int,
    total: int,
) -> str:
    return (
        f"{_ASK_MARKER}. {_CONFIRM_MARKER}. "
        f"El curso **{course_name}** ({school_name}, {year}) tiene **{total}** estudiantes. "
        f"El tope por tanda es {MAX_BULK_STUDENTS}. "
        f"Responde **sí** para generar los primeros {MAX_BULK_STUDENTS}."
    )


def zip_generated_files(filenames: list[str]) -> dict[str, str] | None:
    """Empaqueta Word/PDF generados en files/system/students. Devuelve name + downloadUrl."""
    names = [n for n in filenames if n and Path(n).name == n]
    if not names:
        return None
    root = Path(settings.files_dir) / "system" / "students"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_name = f"informes_curso_{stamp}_{uuid.uuid4().hex[:6]}.zip"
    zip_path = root / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            src = root / name
            if src.is_file():
                zf.write(src, arcname=name)
    if not zip_path.is_file() or zip_path.stat().st_size < 20:
        return None
    return {
        "id": zip_name,
        "name": zip_name,
        "documentName": "Informes del curso (ZIP)",
        "downloadUrl": f"/files/system/students/{zip_name}",
    }
