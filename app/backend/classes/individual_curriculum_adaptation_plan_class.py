"""Document 21 – Individual Curriculum Adaptation Plan (ICAP / PACI)."""

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.db.models import (
    IndividualCurriculumAdaptationPlanModel,
    IndividualCurriculumAdaptationPlanProfessionalModel,
    IndividualCurriculumAdaptationPlanFamilyMemberModel,
)


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _serialize_date(value: Any) -> Optional[str]:
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10] if value else None


def _json_dump(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def _json_load(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


class IndividualCurriculumAdaptationPlanClass:
    def __init__(self, db: Session):
        self.db = db

    def _prof_to_dict(self, row: IndividualCurriculumAdaptationPlanProfessionalModel) -> dict:
        return {
            "id": row.id,
            "professional_id": row.professional_id,
            "professional_role": row.professional_role,
            "support_roles": row.support_roles,
            "phone": row.phone,
            "email": row.email,
        }

    def _family_to_dict(self, row: IndividualCurriculumAdaptationPlanFamilyMemberModel) -> dict:
        return {
            "id": row.id,
            "guardian_id": row.guardian_id,
            "name": row.name,
            "identification_number": row.identification_number,
            "family_member_id": row.family_member_id,
            "address": row.address,
            "phone": row.phone,
            "email": row.email,
            "is_emergency_contact": bool(row.is_emergency_contact),
            "is_guardian": bool(row.is_guardian),
        }

    def _plan_to_dict(self, plan: IndividualCurriculumAdaptationPlanModel) -> dict:
        professionals = (
            self.db.query(IndividualCurriculumAdaptationPlanProfessionalModel)
            .filter(
                IndividualCurriculumAdaptationPlanProfessionalModel.individual_curriculum_adaptation_plan_id
                == plan.id,
                IndividualCurriculumAdaptationPlanProfessionalModel.deleted_date.is_(None),
            )
            .all()
        )
        family_members = (
            self.db.query(IndividualCurriculumAdaptationPlanFamilyMemberModel)
            .filter(
                IndividualCurriculumAdaptationPlanFamilyMemberModel.individual_curriculum_adaptation_plan_id
                == plan.id,
                IndividualCurriculumAdaptationPlanFamilyMemberModel.deleted_date.is_(None),
            )
            .all()
        )
        subjects = _json_load(plan.curricular_adaptation_subjects, [])
        if not isinstance(subjects, list):
            subjects = []
        return {
            "id": plan.id,
            "student_id": plan.student_id,
            "document_type_id": plan.document_type_id,
            "school_id": plan.school_id,
            "semester_id": plan.semester_id,
            "report_date": _serialize_date(plan.report_date),
            "student_full_name": plan.student_full_name,
            "student_identification_number": plan.student_identification_number,
            "student_born_date": _serialize_date(plan.student_born_date),
            "student_age": plan.student_age,
            "student_nee_id": plan.student_nee_id,
            "student_nee": plan.student_nee,
            "student_school": plan.student_school,
            "student_course_id": plan.student_course_id,
            "student_course": plan.student_course,
            "school_background": plan.school_background,
            "evaluation_background": plan.evaluation_background,
            "nee_diagnosis": plan.nee_diagnosis,
            "curricular_adaptations": plan.curricular_adaptations,
            "curricular_adaptation_subjects": subjects,
            "support_resources": plan.support_resources,
            "evaluation_criteria": plan.evaluation_criteria,
            "progress_state": plan.progress_state,
            "professionals": [self._prof_to_dict(p) for p in professionals],
            "family_members": [self._family_to_dict(f) for f in family_members],
            "added_date": plan.added_date.strftime("%Y-%m-%d %H:%M:%S") if plan.added_date else None,
            "updated_date": plan.updated_date.strftime("%Y-%m-%d %H:%M:%S") if plan.updated_date else None,
        }

    def get_semesters(self) -> List[Dict[str, Any]]:
        return [
            {"id": 1, "name": "1° semestre"},
            {"id": 2, "name": "2° semestre"},
        ]

    def get(self, plan_id: int) -> Any:
        try:
            plan = (
                self.db.query(IndividualCurriculumAdaptationPlanModel)
                .filter(
                    IndividualCurriculumAdaptationPlanModel.id == plan_id,
                    IndividualCurriculumAdaptationPlanModel.deleted_date.is_(None),
                )
                .first()
            )
            if not plan:
                return {"status": "error", "message": "ICAP no encontrado."}
            return self._plan_to_dict(plan)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int, latest_only: bool = True) -> Any:
        try:
            q = (
                self.db.query(IndividualCurriculumAdaptationPlanModel)
                .filter(
                    IndividualCurriculumAdaptationPlanModel.student_id == student_id,
                    IndividualCurriculumAdaptationPlanModel.deleted_date.is_(None),
                )
                .order_by(IndividualCurriculumAdaptationPlanModel.id.desc())
            )
            if latest_only:
                plan = q.first()
                if not plan:
                    return None
                return self._plan_to_dict(plan)
            return [self._plan_to_dict(p) for p in q.all()]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _find_existing(self, data: dict) -> Optional[IndividualCurriculumAdaptationPlanModel]:
        student_id = data.get("student_id")
        school_id = data.get("school_id")
        document_type_id = data.get("document_type_id") or 21
        semester_id = data.get("semester_id")
        if student_id is None:
            return None
        q = self.db.query(IndividualCurriculumAdaptationPlanModel).filter(
            IndividualCurriculumAdaptationPlanModel.student_id == student_id,
            IndividualCurriculumAdaptationPlanModel.document_type_id == document_type_id,
            IndividualCurriculumAdaptationPlanModel.deleted_date.is_(None),
        )
        if school_id is not None:
            q = q.filter(IndividualCurriculumAdaptationPlanModel.school_id == school_id)
        if semester_id is not None:
            q = q.filter(IndividualCurriculumAdaptationPlanModel.semester_id == semester_id)
        return q.order_by(IndividualCurriculumAdaptationPlanModel.id.desc()).first()

    def _apply_plan_fields(self, plan: IndividualCurriculumAdaptationPlanModel, data: dict) -> None:
        if "student_id" in data and data["student_id"] is not None:
            plan.student_id = data["student_id"]
        if "document_type_id" in data and data["document_type_id"] is not None:
            plan.document_type_id = int(data["document_type_id"])
        if "school_id" in data:
            plan.school_id = data.get("school_id")
        if "semester_id" in data:
            plan.semester_id = data.get("semester_id")
        if "report_date" in data:
            plan.report_date = _parse_date(data.get("report_date"))
        for field in (
            "student_full_name",
            "student_identification_number",
            "student_age",
            "student_nee",
            "student_school",
            "student_course",
            "school_background",
            "evaluation_background",
            "nee_diagnosis",
            "curricular_adaptations",
            "support_resources",
            "evaluation_criteria",
            "progress_state",
        ):
            if field in data:
                setattr(plan, field, data.get(field))
        if "student_born_date" in data:
            plan.student_born_date = _parse_date(data.get("student_born_date"))
        if "student_nee_id" in data:
            plan.student_nee_id = data.get("student_nee_id")
        if "student_course_id" in data:
            plan.student_course_id = data.get("student_course_id")
        if "curricular_adaptation_subjects" in data:
            subjects = data.get("curricular_adaptation_subjects")
            if subjects is not None:
                plan.curricular_adaptation_subjects = _json_dump(subjects)
            elif data.get("curricular_adaptations"):
                plan.curricular_adaptation_subjects = None

    def _sync_professionals(self, plan_id: int, professionals: Optional[List[dict]]) -> None:
        if professionals is None:
            return
        now = datetime.utcnow()
        rows = (
            self.db.query(IndividualCurriculumAdaptationPlanProfessionalModel)
            .filter(
                IndividualCurriculumAdaptationPlanProfessionalModel.individual_curriculum_adaptation_plan_id
                == plan_id,
                IndividualCurriculumAdaptationPlanProfessionalModel.deleted_date.is_(None),
            )
            .all()
        )
        for row in rows:
            row.deleted_date = now
        for item in professionals:
            if not isinstance(item, dict) or not item.get("professional_id"):
                continue
            self.db.add(
                IndividualCurriculumAdaptationPlanProfessionalModel(
                    individual_curriculum_adaptation_plan_id=plan_id,
                    professional_id=int(item["professional_id"]),
                    professional_role=(item.get("professional_role") or "").strip() or None,
                    support_roles=item.get("support_roles"),
                    phone=(item.get("phone") or "").strip() or None,
                    email=(item.get("email") or "").strip() or None,
                    added_date=now,
                    updated_date=now,
                )
            )

    def _sync_family_members(self, plan_id: int, family_members: Optional[List[dict]]) -> None:
        if family_members is None:
            return
        now = datetime.utcnow()
        rows = (
            self.db.query(IndividualCurriculumAdaptationPlanFamilyMemberModel)
            .filter(
                IndividualCurriculumAdaptationPlanFamilyMemberModel.individual_curriculum_adaptation_plan_id
                == plan_id,
                IndividualCurriculumAdaptationPlanFamilyMemberModel.deleted_date.is_(None),
            )
            .all()
        )
        for row in rows:
            row.deleted_date = now
        for item in family_members:
            if not isinstance(item, dict):
                continue
            self.db.add(
                IndividualCurriculumAdaptationPlanFamilyMemberModel(
                    individual_curriculum_adaptation_plan_id=plan_id,
                    guardian_id=item.get("guardian_id"),
                    name=(item.get("name") or "").strip() or None,
                    identification_number=(item.get("identification_number") or "").strip() or None,
                    family_member_id=item.get("family_member_id"),
                    address=(item.get("address") or "").strip() or None,
                    phone=(item.get("phone") or "").strip() or None,
                    email=(item.get("email") or "").strip() or None,
                    is_emergency_contact=1 if item.get("is_emergency_contact") else 0,
                    is_guardian=0 if item.get("is_guardian") is False else 1,
                    added_date=now,
                    updated_date=now,
                )
            )

    def store(self, data: dict) -> Any:
        try:
            existing = self._find_existing(data)
            if existing:
                return self.update(existing.id, data)

            now = datetime.utcnow()
            plan = IndividualCurriculumAdaptationPlanModel(
                student_id=int(data["student_id"]),
                document_type_id=int(data.get("document_type_id") or 21),
                school_id=data.get("school_id"),
                added_date=now,
                updated_date=now,
            )
            self._apply_plan_fields(plan, data)
            self.db.add(plan)
            self.db.flush()
            self._sync_professionals(plan.id, data.get("professionals"))
            self._sync_family_members(plan.id, data.get("family_members"))
            self.db.commit()
            self.db.refresh(plan)
            return {
                "status": "success",
                "message": "Plan de Adecuación Curricular Individual creado exitosamente.",
                "id": plan.id,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, plan_id: int, data: dict) -> Any:
        try:
            plan = (
                self.db.query(IndividualCurriculumAdaptationPlanModel)
                .filter(
                    IndividualCurriculumAdaptationPlanModel.id == plan_id,
                    IndividualCurriculumAdaptationPlanModel.deleted_date.is_(None),
                )
                .first()
            )
            if not plan:
                return {"status": "error", "message": "ICAP no encontrado."}
            self._apply_plan_fields(plan, data)
            plan.updated_date = datetime.utcnow()
            self._sync_professionals(plan.id, data.get("professionals"))
            self._sync_family_members(plan.id, data.get("family_members"))
            self.db.commit()
            return {
                "status": "success",
                "message": "Plan de Adecuación Curricular Individual actualizado exitosamente.",
                "id": plan.id,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
