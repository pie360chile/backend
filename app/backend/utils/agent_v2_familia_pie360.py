"""Contexto PIE360 para Informe a la Familia (document_id=7): respaldo si Files/LLM no traen datos."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.classes.student_class import StudentClass
from app.backend.db.models import FamilyReportModel
from app.backend.db.models.pie_core import (
    CareerTypeModel,
    CourseModel,
    FamilyMemberModel,
    ProfessionalModel,
    ProfessionalTeachingCourseModel,
    SchoolModel,
    StudentGuardianModel,
    StudentProfessionalModel,
)
from app.backend.utils.professional_display import professional_display_fields

FAMILIA_DOCUMENT_ID = 7


def is_familia_document(document_id: int | None) -> bool:
    return document_id is not None and int(document_id) == FAMILIA_DOCUMENT_ID


def _calc_age(born: Any) -> str:
    if not born:
        return ""
    try:
        if isinstance(born, date):
            bd = born
        elif hasattr(born, "date"):
            bd = born.date()
        else:
            raw = str(born).strip()[:10]
            bd = datetime.strptime(raw, "%Y-%m-%d").date()
        today = date.today()
        years = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        if years > 0:
            return f"{years} año{'s' if years != 1 else ''}"
        months = (today.year - bd.year) * 12 + today.month - bd.month
        if months < 0:
            months = 0
        return f"{months} mes{'es' if months != 1 else ''}"
    except Exception:
        return ""


def _fmt_birth_date(born: Any) -> str:
    if not born:
        return ""
    try:
        if isinstance(born, date):
            return born.strftime("%d/%m/%Y")
        if hasattr(born, "strftime"):
            return born.strftime("%d/%m/%Y")
        raw = str(born).strip()[:10]
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(born).strip()


def _career_label(db: Session, career_type_id: int | None) -> str:
    if not career_type_id:
        return ""
    row = db.query(CareerTypeModel).filter(CareerTypeModel.id == career_type_id).first()
    return (row.career_type or "").strip() if row else ""


def _guardian_from_row(db: Session, g: StudentGuardianModel) -> dict[str, str]:
    full = f"{g.names or ''} {g.father_lastname or ''} {g.mother_lastname or ''}".strip()
    relation = ""
    if g.family_member_id:
        fm = db.query(FamilyMemberModel).filter(FamilyMemberModel.id == g.family_member_id).first()
        if fm and fm.family_member:
            relation = (fm.family_member or "").strip()
    return {
        "person_full_name": full,
        "receiver_full_name": full,
        "person_identification_number": (g.identification_number or "").strip(),
        "receiver_identification_number": (g.identification_number or "").strip(),
        "person_phone": (g.celphone or "").strip(),
        "receiver_phone": (g.celphone or "").strip(),
        "person_email": (g.email or "").strip(),
        "receiver_email": (g.email or "").strip(),
        "person_relation_student": relation,
        "receiver_relationship": relation,
    }


def _professional_from_id(db: Session, professional_id: int | None) -> dict[str, str]:
    if not professional_id:
        return {}
    prof = db.query(ProfessionalModel).filter(ProfessionalModel.id == professional_id).first()
    if not prof:
        return {}
    display = professional_display_fields(db, prof)
    role = _career_label(db, getattr(prof, "career_type_id", None))
    phone = (display.phone or "").strip()
    email = (display.email or "").strip()
    contact = f"{phone} / {email}".strip(" / ")
    return {
        "professional_id": professional_id,
        "professional_full_name": (display.full_name or "").strip(),
        "professional_social_name": (display.full_name or "").strip(),
        "professional_identification_number": (display.rut or "").strip(),
        "professional_rut": (display.rut or "").strip(),
        "professional_role": role,
        "professional_job_position": role,
        "professional_phone": phone,
        "professional_email": email,
        "professional_phone_email": contact,
    }


def _family_report_snapshot(db: Session, student_id: int) -> dict[str, str]:
    report = (
        db.query(FamilyReportModel)
        .filter(FamilyReportModel.student_id == student_id)
        .order_by(FamilyReportModel.id.desc())
        .first()
    )
    if not report:
        return {}
    out: dict[str, str] = {}
    mapping = {
        "student_full_name": report.student_full_name,
        "student_identification_number": report.student_identification_number,
        "student_course": report.student_course,
        "student_school": report.student_school,
        "person_full_name": report.receiver_full_name,
        "receiver_full_name": report.receiver_full_name,
        "person_identification_number": report.receiver_identification_number,
        "receiver_identification_number": report.receiver_identification_number,
        "person_phone": report.receiver_phone,
        "receiver_phone": report.receiver_phone,
        "person_email": report.receiver_email,
        "receiver_email": report.receiver_email,
        "person_relation_student": report.receiver_relationship,
        "receiver_relationship": report.receiver_relationship,
        "person_presence": report.receiver_presence_of,
        "receiver_presence_of": report.receiver_presence_of,
        "professional_full_name": report.professional_social_name,
        "professional_social_name": report.professional_social_name,
        "professional_identification_number": report.professional_identification_number,
        "professional_role": report.professional_role,
        "professional_phone": report.professional_phone,
        "professional_email": report.professional_email,
        "evaluation_type": report.evaluation_type,
    }
    for key, val in mapping.items():
        text = str(val or "").strip()
        if text:
            out[key] = text
    if report.professional_id:
        out["professional_id"] = int(report.professional_id)
    ph = out.get("professional_phone", "")
    em = out.get("professional_email", "")
    if ph or em:
        out["professional_phone_email"] = f"{ph} / {em}".strip(" / ")
    return out


def build_familia_pie360_context(db: Session, student_id: int) -> dict[str, Any]:
    """
    Datos de ficha PIE360 para Informe Familia.
    Orden de respaldo: estudiante → apoderado (student_guardians) → profesional (students_professionals / curso).
    """
    ctx: dict[str, Any] = {"student_id": student_id}
    fr_snap = _family_report_snapshot(db, student_id)
    for key, val in fr_snap.items():
        if val:
            ctx[key] = val

    student_result = StudentClass(db).get(student_id)
    if isinstance(student_result, dict) and student_result.get("student_data"):
        sd = student_result["student_data"]
        personal = sd.get("personal_data") or {}
        academic = sd.get("academic_info") or {}

        names = (personal.get("names") or "").strip()
        father = (personal.get("father_lastname") or "").strip()
        mother = (personal.get("mother_lastname") or "").strip()
        full = f"{names} {father} {mother}".strip()

        ctx.setdefault("student_fullname", full)
        ctx.setdefault("student_full_name", full)
        ctx.setdefault("student_social_name", (personal.get("social_name") or "").strip())
        rut = (personal.get("identification_number") or sd.get("identification_number") or "").strip()
        ctx.setdefault("identification_number", rut)
        ctx.setdefault("student_identification_number", rut)
        born = personal.get("born_date")
        if born:
            ctx.setdefault("student_birth_date", _fmt_birth_date(born))
            ctx.setdefault("student_born_date", _fmt_birth_date(born))
            ctx.setdefault("student_age", _calc_age(born))

        ctx.setdefault("school_id", sd.get("school_id"))
        ctx.setdefault("course_id", academic.get("course_id"))
        ctx.setdefault("period_year", sd.get("period_year"))

        school_id = sd.get("school_id")
        if school_id and not ctx.get("student_school"):
            school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
            if school and school.school_name:
                ctx["student_school"] = (school.school_name or "").strip()

        course_id = academic.get("course_id")
        if course_id and not ctx.get("student_course"):
            course = (
                db.query(CourseModel)
                .filter(CourseModel.deleted_status_id == 0, CourseModel.id == course_id)
                .first()
            )
            if course and course.course_name:
                ctx["student_course"] = (course.course_name or "").strip()

    guardian = (
        db.query(StudentGuardianModel)
        .filter(StudentGuardianModel.student_id == student_id)
        .order_by(StudentGuardianModel.id.desc())
        .first()
    )
    if guardian:
        g_data = _guardian_from_row(db, guardian)
        for key, val in g_data.items():
            if val and not ctx.get(key):
                ctx[key] = val

    prof_id: int | None = ctx.get("professional_id")
    if not prof_id:
        sp = (
            db.query(StudentProfessionalModel)
            .filter(
                StudentProfessionalModel.student_id == student_id,
                StudentProfessionalModel.deleted_date.is_(None),
            )
            .order_by(StudentProfessionalModel.id.desc())
            .first()
        )
        if sp:
            prof_id = sp.professional_id

    if not prof_id and ctx.get("course_id"):
        ptc = (
            db.query(ProfessionalTeachingCourseModel)
            .filter(
                ProfessionalTeachingCourseModel.course_id == ctx["course_id"],
                ProfessionalTeachingCourseModel.deleted_status_id == 0,
            )
            .order_by(ProfessionalTeachingCourseModel.id.desc())
            .first()
        )
        if ptc:
            prof_id = ptc.professional_id

    if prof_id and not ctx.get("professional_full_name"):
        prof_data = _professional_from_id(db, prof_id)
        for key, val in prof_data.items():
            if val and not ctx.get(key):
                ctx[key] = val

    return ctx


# Clave plantilla → claves alternativas en contexto PIE360
_FAMILIA_PIE360_FALLBACK: dict[str, tuple[str, ...]] = {
    "student_full_name": ("student_full_name", "student_fullname"),
    "student_social_name": ("student_social_name",),
    "student_identification_number": ("student_identification_number", "identification_number"),
    "student_birth_date": ("student_birth_date", "student_born_date"),
    "student_born_date": ("student_born_date", "student_birth_date"),
    "student_age": ("student_age",),
    "student_course": ("student_course",),
    "student_school": ("student_school",),
    "professional_full_name": ("professional_full_name", "professional_social_name"),
    "professional_social_name": ("professional_social_name", "professional_full_name"),
    "professional_identification_number": (
        "professional_identification_number",
        "professional_rut",
    ),
    "professional_role": ("professional_role", "professional_job_position"),
    "professional_job_position": ("professional_job_position", "professional_role"),
    "professional_phone": ("professional_phone",),
    "professional_email": ("professional_email",),
    "professional_phone_email": ("professional_phone_email",),
    "person_full_name": ("person_full_name", "receiver_full_name"),
    "receiver_full_name": ("receiver_full_name", "person_full_name"),
    "person_identification_number": (
        "person_identification_number",
        "receiver_identification_number",
    ),
    "receiver_identification_number": (
        "receiver_identification_number",
        "person_identification_number",
    ),
    "person_phone": ("person_phone", "receiver_phone"),
    "receiver_phone": ("receiver_phone", "person_phone"),
    "person_email": ("person_email", "receiver_email"),
    "receiver_email": ("receiver_email", "person_email"),
    "person_relation_student": ("person_relation_student", "receiver_relationship"),
    "receiver_relationship": ("receiver_relationship", "person_relation_student"),
    "person_presence": ("person_presence", "receiver_presence_of"),
    "receiver_presence_of": ("receiver_presence_of", "person_presence"),
    "evaluation_type": ("evaluation_type",),
}


def merge_pie360_fallback_into_replacements(
    merged: dict[str, str],
    pie360_ctx: dict[str, Any],
) -> dict[str, str]:
    """Archivos/LLM primero; PIE360 solo completa campos vacíos."""
    out = dict(merged)
    for target_key, sources in _FAMILIA_PIE360_FALLBACK.items():
        if (out.get(target_key) or "").strip():
            continue
        for src in sources:
            val = pie360_ctx.get(src)
            if val is not None and str(val).strip():
                out[target_key] = str(val).strip()
                break
    return out


def familia_pie360_hint_lines(pie360_ctx: dict[str, Any]) -> list[str]:
    """Líneas breves para el system prompt del chat (solo informe familia)."""
    lines: list[str] = []
    if (pie360_ctx.get("person_full_name") or pie360_ctx.get("receiver_full_name") or "").strip():
        lines.append(
            f"Apoderado/a (PIE360): "
            f"{(pie360_ctx.get('person_full_name') or pie360_ctx.get('receiver_full_name') or '').strip()}"
        )
    g_rut = (pie360_ctx.get("person_identification_number") or "").strip()
    if g_rut:
        lines.append(f"RUT apoderado (PIE360): {g_rut}")
    g_phone = (pie360_ctx.get("person_phone") or "").strip()
    if g_phone:
        lines.append(f"Teléfono apoderado (PIE360): {g_phone}")
    g_email = (pie360_ctx.get("person_email") or "").strip()
    if g_email:
        lines.append(f"Email apoderado (PIE360): {g_email}")
    prof = (pie360_ctx.get("professional_full_name") or "").strip()
    if prof:
        lines.append(f"Profesional (PIE360): {prof}")
    p_rut = (pie360_ctx.get("professional_identification_number") or "").strip()
    if p_rut:
        lines.append(f"RUT profesional (PIE360): {p_rut}")
    role = (pie360_ctx.get("professional_role") or "").strip()
    if role:
        lines.append(f"Cargo/especialidad (PIE360): {role}")
    p_phone = (pie360_ctx.get("professional_phone") or "").strip()
    if p_phone:
        lines.append(f"Teléfono profesional (PIE360): {p_phone}")
    p_email = (pie360_ctx.get("professional_email") or "").strip()
    if p_email:
        lines.append(f"Email profesional (PIE360): {p_email}")
    return lines
