"""Resuelve datos del estudiante y apoderado en BD para el agente."""

from __future__ import annotations

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
        for key, value in fr.items():
            if not value:
                continue
            if key in _IDENTIFICATION_KEYS:
                if not ctx.get(key):
                    if key.endswith("_date") or key == "student_born_date":
                        ctx[key] = _fmt_date(value)
                    else:
                        ctx[key] = value
            else:
                ctx[key] = value

    return {k: v for k, v in ctx.items() if v not in (None, "")}


def resolve_student_context_for_agent(db: Session, message: str) -> dict[str, Any] | None:
    """Busca estudiante por nombre en el mensaje y arma datos para el informe."""
    if _message_intent(message) != "familia":
        return None
    student_id = find_student_id_by_message(db, message)
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
        "student_full_name": "Nombre estudiante",
        "student_identification_number": "RUN/RUT estudiante",
        "student_social_name": "Nombre social estudiante",
        "student_born_date": "Fecha nacimiento",
        "student_age": "Edad",
        "student_course": "Curso/Nivel",
        "student_school": "Establecimiento",
        "professional_social_name": "Nombre profesional",
        "professional_identification_number": "RUT profesional",
        "professional_role": "Rol/cargo profesional",
        "professional_phone": "Teléfono profesional",
        "professional_email": "E-mail profesional",
        "report_delivery_date": "Fecha entrega informe",
        "receiver_full_name": "Nombre apoderado/receptor",
        "receiver_identification_number": "RUT apoderado",
        "receiver_phone": "Teléfono apoderado",
        "receiver_email": "E-mail apoderado",
        "receiver_relationship": "Relación con estudiante",
        "diagnosis": "Diagnóstico (informe guardado)",
        "applied_instruments": "Instrumentos (informe guardado)",
        "evaluation_date_1": "Fecha seguimiento 1",
        "evaluation_date_2": "Fecha seguimiento 2",
        "evaluation_date_3": "Fecha seguimiento 3",
    }
    date_keys = ("evaluation_date_1", "evaluation_date_2", "evaluation_date_3")
    id_missing_keys = (
        "student_identification_number",
        "receiver_full_name",
        "receiver_identification_number",
        "receiver_relationship",
    )
    for key, label in labels.items():
        val = context.get(key)
        if val:
            lines.append(f"- {label}: {val}")
        elif key in date_keys:
            lines.append(
                f"- {label}: (sin dato en BD — dejar celda de fecha vacía; NO inventar texto)"
            )
        elif key in id_missing_keys:
            lines.append(f"- {label}: (sin dato en BD — escribir «No informado»)")

    lines.append(
        "- Antes de generar el Word: copia estos datos a los campos del formulario/plantilla "
        "(Nombres y Apellidos, RUN, Rut, Rol/cargo, receptor, etc.). "
        "Si un dato de identificación no aparece aquí ni en los archivos, indica «No informado». "
        "Si faltan fechas de seguimiento, deja las celdas vacías."
    )
    return "\n".join(lines)
