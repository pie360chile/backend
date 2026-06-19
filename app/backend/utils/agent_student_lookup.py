"""Resuelve datos del estudiante y apoderado en BD para el agente."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.family_report_class import FamilyReportClass
from app.backend.classes.professional_class import ProfessionalClass
from app.backend.classes.student_class import StudentClass
from app.backend.classes.student_guardian_class import StudentGuardianClass
from app.backend.classes.student_professional_class import StudentProfessionalClass
from app.backend.db.models import (
    CourseModel,
    FamilyMemberModel,
    ProfessionalModel,
    SchoolModel,
    StudentModel,
    StudentPersonalInfoModel,
)
from app.backend.utils.agent_file_selection import _message_intent, _message_name_tokens

_RUT_RE = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"(?:\d{1,2}[\.\s])?\d{3}[\.\s]\d{3}[\-\s][\dkK]"
    r"|"
    r"\d{7,8}[\-\s][\dkK]"
    r")"
    r"(?!\d)",
    re.IGNORECASE,
)


_IDENTIFICATION_KEYS = (
    "student_full_name",
    "student_identification_number",
    "student_social_name",
    "student_born_date",
    "student_age",
    "student_course",
    "student_school",
    "professional_identification_number",
    "professional_social_name",
    "professional_role",
    "professional_phone",
    "professional_email",
    "report_delivery_date",
    "receiver_full_name",
    "receiver_identification_number",
    "receiver_social_name",
    "receiver_phone",
    "receiver_email",
    "receiver_relationship",
)


def _normalize_rut(raw: str | None) -> str | None:
    if not raw:
        return None
    s = "".join(c for c in str(raw).strip().lower() if c.isalnum())
    return s or None


def _format_rut_display(raw: str) -> str:
    n = _normalize_rut(raw)
    if not n or len(n) < 2:
        return (raw or "").strip()
    return f"{n[:-1]}-{n[-1].upper()}"


def extract_rut_from_message(message: str) -> str | None:
    """Extrae el primer RUT chileno válido del mensaje."""
    for match in _RUT_RE.finditer(message or ""):
        candidate = match.group(0).strip()
        normalized = _normalize_rut(candidate)
        if normalized and len(normalized) >= 8:
            return _format_rut_display(candidate)
    return None


def _rut_matches_stored(target: str, *values: str | None) -> bool:
    if not target:
        return False
    for val in values:
        if val and _normalize_rut(val) == target:
            return True
    return False


def _rut_search_terms(rut: str) -> set[str]:
    """Variantes de texto para LIKE en BD (con/sin puntos, guión, DV)."""
    target = _normalize_rut(rut)
    if not target or len(target) < 8:
        return set()

    body = target[:-1]
    dv = target[-1]
    terms = {
        body,
        target,
        f"{body}-{dv}",
        f"{body}-{dv.upper()}",
        _format_rut_display(rut),
    }
    if len(body) == 8:
        dotted = f"{body[:2]}.{body[2:5]}.{body[5:]}"
        terms.add(f"{dotted}-{dv.upper()}")
        terms.add(f"{dotted}-{dv.lower()}")
        terms.add(dotted)
    return {t.strip() for t in terms if t and t.strip()}


def _student_row_ruts(row: dict[str, Any]) -> tuple[str | None, str | None]:
    personal = row.get("personal_data") or {}
    return (
        row.get("identification_number"),
        personal.get("identification_number"),
    )


def find_student_id_by_rut(db: Session, rut: str) -> int | None:
    """Busca estudiante por RUT en students y student_personal_data."""
    target = _normalize_rut(rut)
    if not target or len(target) < 8:
        return None

    service = StudentClass(db)
    candidates: dict[int, dict[str, Any]] = {}

    for term in _rut_search_terms(rut):
        for kwargs in (
            {"rut": term},
            {"identification_number": term},
        ):
            result = service.get_all(page=1, items_per_page=50, **kwargs)
            rows = result.get("data", []) if isinstance(result, dict) else []
            for row in rows:
                sid = row.get("id")
                if sid is not None:
                    candidates[int(sid)] = row

    exact: list[int] = []
    for sid, row in candidates.items():
        st_rut, pi_rut = _student_row_ruts(row)
        if _rut_matches_stored(target, st_rut, pi_rut):
            exact.append(sid)

    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return max(exact)

    # Respaldo: comparación normalizada en SQL (RUT solo en personal_data u otro formato)
    body = target[:-1]
    if len(body) >= 7:
        from sqlalchemy import or_

        from app.backend.db.models import StudentPersonalInfoModel

        pattern = f"%{body}%"
        rows = (
            db.query(
                StudentModel.id,
                StudentModel.identification_number,
                StudentPersonalInfoModel.identification_number,
            )
            .outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id,
            )
            .filter(
                StudentModel.deleted_status_id == 0,
                or_(
                    StudentModel.identification_number.like(pattern),
                    StudentPersonalInfoModel.identification_number.like(pattern),
                ),
            )
            .limit(80)
            .all()
        )
        direct: list[int] = []
        for sid, st_rut, pi_rut in rows:
            if _rut_matches_stored(target, st_rut, pi_rut):
                direct.append(int(sid))
        if len(direct) == 1:
            return direct[0]
        if len(direct) > 1:
            return max(direct)

    if len(candidates) == 1:
        sid, row = next(iter(candidates.items()))
        st_rut, pi_rut = _student_row_ruts(row)
        if _rut_matches_stored(target, st_rut, pi_rut):
            return sid

    return None


def check_familia_rut_requirement(db: Session, message: str) -> str | None:
    """
    Si el mensaje pide informe a la familia, exige RUT y estudiante en BD.
    Devuelve texto de respuesta al usuario si falta algo; None si puede continuar.
    """
    if _message_intent(message) != "familia":
        return None

    rut = extract_rut_from_message(message)
    if not rut:
        return (
            "Para generar el Informe para la Familia necesito el RUT del estudiante "
            "(por ejemplo: 12.345.678-9).\n\n"
            "Escribe tu solicitud incluyendo el RUT. Ejemplo:\n"
            "«Hazme el informe a la familia del estudiante RUT 12.345.678-9»"
        )

    student_id = find_student_id_by_rut(db, rut)
    if not student_id:
        return (
            f"No encontré un estudiante en PIE360 con el RUT {rut}.\n\n"
            "Verifica que el RUT esté correcto y que el estudiante esté registrado en la plataforma."
        )

    context = build_student_context(db, student_id)
    if not context:
        return (
            f"Encontré el RUT {rut} pero no pude cargar la ficha del estudiante en PIE360.\n\n"
            "Revisa que el estudiante tenga datos personales completos en la plataforma."
        )

    return None


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _full_name_from_parts(
    names: str | None,
    father_lastname: str | None,
    mother_lastname: str | None,
) -> str:
    return " ".join(
        p
        for p in (
            (names or "").strip(),
            (father_lastname or "").strip(),
            (mother_lastname or "").strip(),
        )
        if p
    ).strip()


def _fmt_date(val: Any) -> str | None:
    if not val:
        return None
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, datetime):
        return val.date().strftime("%d/%m/%Y")
    if isinstance(val, str):
        raw = val.strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt).date().strftime("%d/%m/%Y")
            except ValueError:
                continue
        return val.strip()
    return str(val)


def _calculate_age(born_date: Any) -> str | None:
    if not born_date:
        return None
    try:
        if isinstance(born_date, str):
            born = datetime.strptime(born_date.strip()[:10], "%Y-%m-%d").date()
        elif isinstance(born_date, datetime):
            born = born_date.date()
        elif isinstance(born_date, date):
            born = born_date
        else:
            return None
        today = date.today()
        years = today.year - born.year
        months = today.month - born.month
        if today.day < born.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12
        if years < 0:
            return None
        if months:
            return f"{years} años, {months} meses"
        return f"{years} años"
    except (ValueError, TypeError):
        return None


def _student_name_score(student: dict[str, Any], tokens: list[str]) -> int:
    personal = student.get("personal_data") or {}
    haystack = _normalize(
        _full_name_from_parts(
            personal.get("names"),
            personal.get("father_lastname"),
            personal.get("mother_lastname"),
        )
    )
    return sum(1 for token in tokens if token in haystack)


def find_student_id_by_message(db: Session, message: str) -> int | None:
    tokens = _message_name_tokens(message)
    if len(tokens) < 2:
        return None

    student_service = StudentClass(db)
    candidates: dict[int, dict[str, Any]] = {}

    for token in tokens[:3]:
        result = student_service.get_all(page=1, items_per_page=40, names=token)
        rows = result.get("data", []) if isinstance(result, dict) else []
        for row in rows:
            sid = row.get("id")
            if sid is not None:
                candidates[int(sid)] = row

    # Búsqueda adicional por apellido en personal_data
    for token in tokens:
        if len(token) < 3:
            continue
        q = (
            db.query(StudentModel.id)
            .join(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id,
            )
            .filter(
                StudentModel.deleted_status_id == 0,
                (
                    StudentPersonalInfoModel.father_lastname.ilike(f"%{token}%")
                    | StudentPersonalInfoModel.mother_lastname.ilike(f"%{token}%")
                    | StudentPersonalInfoModel.names.ilike(f"%{token}%")
                ),
            )
            .limit(40)
        )
        for (sid,) in q.all():
            if sid not in candidates:
                detail = StudentClass(db).get(int(sid))
                sd = detail.get("student_data") if isinstance(detail, dict) else None
                if sd:
                    candidates[int(sid)] = sd

    if not candidates:
        return None

    best_id, best_row = max(
        candidates.items(),
        key=lambda item: (_student_name_score(item[1], tokens), item[0]),
    )
    if _student_name_score(best_row, tokens) < 2:
        return None
    return best_id


def _guardian_rows(db: Session, student_id: int) -> list[dict[str, Any]]:
    result = StudentGuardianClass(db).get_all(page=0, student_id=student_id)
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
    return []


def _family_member_label(db: Session, family_member_id: int | None) -> str | None:
    if not family_member_id:
        return None
    row = (
        db.query(FamilyMemberModel)
        .filter(FamilyMemberModel.id == family_member_id)
        .first()
    )
    if row and row.family_member:
        return str(row.family_member).strip()
    return None


def _course_label(db: Session, course_id: int | None) -> str | None:
    if not course_id:
        return None
    row = db.query(CourseModel).filter(CourseModel.id == course_id).first()
    if row and row.course_name:
        return str(row.course_name).strip()
    return None


def _school_label(db: Session, school_id: int | None) -> str | None:
    if not school_id:
        return None
    row = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
    if row and row.school_name:
        return str(row.school_name).strip()
    return None


def _professional_for_student(
    db: Session,
    student_id: int,
    school_id: int | None,
) -> dict[str, Any]:
    links = StudentProfessionalClass(db).get(student_id=student_id).get("data") or []
    if not links:
        return {}
    profile_id = links[0].get("professional_id")
    if not profile_id:
        return {}
    profile = (
        db.query(ProfessionalModel)
        .filter(ProfessionalModel.id == profile_id)
        .first()
    )
    if not profile or not profile.user_id:
        return {}
    prof = ProfessionalClass(db).get(profile.user_id, school_id=school_id)
    data = prof.get("professional_data") if isinstance(prof, dict) else None
    if not data:
        return {}
    full_name = " ".join(
        p for p in (data.get("names"), data.get("lastnames")) if (p or "").strip()
    ).strip()
    rol_name = None
    listed = ProfessionalClass(db).get_all(
        page=1,
        items_per_page=1,
        school_id=school_id,
        only_professional_id=profile.user_id,
    )
    if isinstance(listed, dict):
        rows = listed.get("data") or []
        if rows:
            rol_name = rows[0].get("rol_name")
    return {
        "professional_id": data.get("id"),
        "professional_identification_number": data.get("identification_number"),
        "professional_social_name": full_name or None,
        "professional_role": rol_name,
        "professional_phone": data.get("phone"),
        "professional_email": data.get("email"),
    }


def build_student_context(db: Session, student_id: int) -> dict[str, Any] | None:
    raw = StudentClass(db).get(student_id)
    student = raw.get("student_data") if isinstance(raw, dict) else None
    if not student:
        return None

    personal = student.get("personal_data") or {}
    academic = student.get("academic_info") or {}
    school_id = student.get("school_id")
    course_id = academic.get("course_id")

    ctx: dict[str, Any] = {
        "student_id": student_id,
        "student_full_name": _full_name_from_parts(
            personal.get("names"),
            personal.get("father_lastname"),
            personal.get("mother_lastname"),
        ),
        "student_identification_number": (
            personal.get("identification_number")
            or student.get("identification_number")
        ),
        "student_social_name": personal.get("social_name"),
        "student_born_date": _fmt_date(personal.get("born_date")),
        "student_age": _calculate_age(personal.get("born_date")),
        "student_course": _course_label(db, course_id),
        "student_school": _school_label(db, school_id),
        "report_delivery_date": date.today().strftime("%d/%m/%Y"),
    }

    guardians = _guardian_rows(db, student_id)
    if not guardians:
        single = StudentGuardianClass(db).get(student_id)
        if isinstance(single, dict) and single.get("status") != "error" and "error" not in single:
            guardians = [single]
    if guardians:
        guardian = guardians[0]
        receiver_name = _full_name_from_parts(
            guardian.get("names"),
            guardian.get("father_lastname"),
            guardian.get("mother_lastname"),
        )
        ctx.update(
            {
                "receiver_full_name": receiver_name or None,
                "receiver_identification_number": guardian.get("identification_number"),
                "receiver_social_name": guardian.get("social_name"),
                "receiver_phone": guardian.get("celphone"),
                "receiver_email": guardian.get("email"),
                "receiver_relationship": _family_member_label(
                    db, guardian.get("family_member_id")
                ),
            }
        )

    ctx.update(_professional_for_student(db, student_id, school_id))

    fr = FamilyReportClass(db).get_by_student_id(student_id)
    if isinstance(fr, dict) and fr.get("status") != "error":
        _fr_skip = {
            "id",
            "student_id",
            "document_type_id",
            "version",
            "added_date",
            "updated_date",
            "status",
        }
        for key, value in fr.items():
            if key in _fr_skip or value in (None, ""):
                continue
            if key.endswith("_date") or "born_date" in key:
                ctx[key] = _fmt_date(value)
            else:
                ctx[key] = value

    if not ctx.get("student_identification_number"):
        from app.backend.db.models import StudentModel, StudentPersonalInfoModel

        student_row = (
            db.query(StudentModel.identification_number)
            .filter(StudentModel.id == student_id)
            .first()
        )
        if student_row and student_row[0]:
            ctx["student_identification_number"] = student_row[0]
        else:
            personal_row = (
                db.query(StudentPersonalInfoModel.identification_number)
                .filter(StudentPersonalInfoModel.student_id == student_id)
                .first()
            )
            if personal_row and personal_row[0]:
                ctx["student_identification_number"] = personal_row[0]

    _mirror_identification_tags_for_template(ctx)

    return {k: v for k, v in ctx.items() if v not in (None, "")}


def _mirror_identification_tags_for_template(ctx: dict[str, Any]) -> None:
    """Expone claves con el mismo nombre que los w:tag de family_report.docx."""
    if ctx.get("student_born_date") and not ctx.get("student_birth_date"):
        ctx["student_birth_date"] = ctx["student_born_date"]
    if ctx.get("professional_social_name") and not ctx.get("professional_full_name"):
        ctx["professional_full_name"] = ctx["professional_social_name"]
    if ctx.get("professional_role") and not ctx.get("professional_job_position"):
        ctx["professional_job_position"] = ctx["professional_role"]
    if ctx.get("report_delivery_date") and not ctx.get("professional_delivered_date_inform"):
        ctx["professional_delivered_date_inform"] = ctx["report_delivery_date"]
    ph = str(ctx.get("professional_phone") or "").strip()
    em = str(ctx.get("professional_email") or "").strip()
    if (ph or em) and not ctx.get("professional_phone_email"):
        ctx["professional_phone_email"] = f"{ph} / {em}".strip(" / ")
    if ctx.get("receiver_full_name") and not ctx.get("person_full_name"):
        ctx["person_full_name"] = ctx["receiver_full_name"]
    if ctx.get("receiver_identification_number") and not ctx.get("person_identification_number"):
        ctx["person_identification_number"] = ctx["receiver_identification_number"]
    if ctx.get("receiver_relationship") and not ctx.get("person_relation_student"):
        ctx["person_relation_student"] = ctx["receiver_relationship"]
    if ctx.get("receiver_presence_of") and not ctx.get("person_presence"):
        ctx["person_presence"] = ctx["receiver_presence_of"]


def resolve_student_context_for_agent(db: Session, message: str) -> dict[str, Any] | None:
    """Busca estudiante por RUT en el mensaje y arma datos para el informe familia."""
    if _message_intent(message) != "familia":
        return None
    rut = extract_rut_from_message(message)
    if not rut:
        return None
    student_id = find_student_id_by_rut(db, rut)
    if not student_id:
        return None
    return build_student_context(db, student_id)


def format_student_context_block(context: dict[str, Any]) -> str:
    lines = [
        "=== DATOS DEL ESTUDIANTE EN BASE DE DATOS (OBLIGATORIO USAR ANTES DE ARMAR EL .DOCX) ===",
        "Consulta autoritativa de PIE360. Usa estos valores para rellenar identificación del estudiante, "
        "profesional y apoderado/receptor. No inventes RUT, nombres, relación ni fechas.",
        f"student_id: {context.get('student_id')}",
    ]
    labels = {
        "student_full_name": "student_full_name",
        "student_identification_number": "student_identification_number",
        "student_birth_date": "student_birth_date",
        "student_age": "student_age",
        "student_course": "student_course",
        "student_school": "student_school",
        "professional_full_name": "professional_full_name",
        "professional_identification_number": "professional_identification_number",
        "professional_job_position": "professional_job_position",
        "professional_phone_email": "professional_phone_email",
        "professional_delivered_date_inform": "professional_delivered_date_inform",
        "person_full_name": "person_full_name",
        "person_identification_number": "person_identification_number",
        "person_relation_student": "person_relation_student",
        "person_presence": "person_presence",
        "diagnosis": "diagnosis (narrativa)",
        "applied_instruments": "applied_instruments",
        "evaluation_date_1": "evaluation_date_1",
        "evaluation_date_2": "evaluation_date_2",
        "evaluation_date_3": "evaluation_date_3",
    }
    date_keys = ("evaluation_date_1", "evaluation_date_2", "evaluation_date_3")
    id_missing_keys = (
        "student_identification_number",
        "person_full_name",
        "person_identification_number",
        "person_relation_student",
    )
    for key, tag in labels.items():
        val = context.get(key)
        if val:
            lines.append(f"- {tag}: {val}")
        elif key in date_keys:
            lines.append(
                f"- {tag}: (sin dato en BD — dejar celda de fecha vacía; NO inventar texto)"
            )
        elif key in id_missing_keys:
            lines.append(f"- {tag}: (sin dato en BD — escribir «No informado»)")

    lines.append(
        "- Identificación: rellena SOLO los content controls con esos w:tag exactos. "
        "No uses otros nombres ni muevas datos entre campos."
    )
    return "\n".join(lines)
