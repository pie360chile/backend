from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.db.models import (
    CurriculumSubjectLevelModel,
    CurriculumSubjectModel,
    EducationLevelModel,
    LearningObjectiveModel,
)


class LearningObjectiveClass:
    def __init__(self, db: Session):
        self.db = db

    def list_education_levels(self) -> Any:
        try:
            rows = (
                self.db.query(EducationLevelModel)
                .filter(EducationLevelModel.deleted_date.is_(None))
                .filter(EducationLevelModel.is_active == 1)
                .order_by(EducationLevelModel.sort_order.asc())
                .all()
            )
            data = [
                {
                    "id": r.id,
                    "name": r.name,
                    "name_es": r.name_es,
                    "education_stage": r.education_stage,
                    "grade_number": r.grade_number,
                    "oa_level_code": r.oa_level_code,
                    "sort_order": r.sort_order,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def list_by_subject_and_level(
        self, subject_name_es: str, education_level_id: int
    ) -> Any:
        try:
            name = (subject_name_es or "").strip()
            if not name:
                return {"status": "error", "message": "Nombre de asignatura requerido.", "data": []}

            curriculum_subject = (
                self.db.query(CurriculumSubjectModel)
                .filter(CurriculumSubjectModel.deleted_date.is_(None))
                .filter(CurriculumSubjectModel.is_active == 1)
                .filter(CurriculumSubjectModel.name_es == name)
                .first()
            )
            if not curriculum_subject:
                curriculum_subject = (
                    self.db.query(CurriculumSubjectModel)
                    .filter(CurriculumSubjectModel.deleted_date.is_(None))
                    .filter(CurriculumSubjectModel.is_active == 1)
                    .filter(CurriculumSubjectModel.name_es.ilike(f"%{name}%"))
                    .order_by(CurriculumSubjectModel.sort_order.asc())
                    .first()
                )
            if not curriculum_subject:
                return {
                    "status": "success",
                    "data": [],
                    "message": "No hay catálogo curricular para esta asignatura.",
                }

            subject_level = (
                self.db.query(CurriculumSubjectLevelModel)
                .filter(CurriculumSubjectLevelModel.deleted_date.is_(None))
                .filter(CurriculumSubjectLevelModel.is_active == 1)
                .filter(CurriculumSubjectLevelModel.curriculum_subject_id == curriculum_subject.id)
                .filter(CurriculumSubjectLevelModel.education_level_id == education_level_id)
                .first()
            )
            if not subject_level:
                return {
                    "status": "success",
                    "data": [],
                    "message": "No hay objetivos para esta asignatura y nivel.",
                }

            rows = (
                self.db.query(LearningObjectiveModel)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .filter(LearningObjectiveModel.is_active == 1)
                .filter(LearningObjectiveModel.curriculum_subject_level_id == subject_level.id)
                .order_by(LearningObjectiveModel.sort_order.asc())
                .all()
            )
            data = [
                {
                    "id": r.id,
                    "code": r.code,
                    "description": r.description,
                    "is_priority": bool(r.is_priority),
                    "sort_order": r.sort_order,
                }
                for r in rows
            ]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}
