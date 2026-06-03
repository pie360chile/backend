from datetime import datetime
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

    def _resolve_curriculum_subject(self, subject_name_es: str) -> Optional[CurriculumSubjectModel]:
        name = (subject_name_es or "").strip()
        if not name:
            return None
        curriculum_subject = (
            self.db.query(CurriculumSubjectModel)
            .filter(CurriculumSubjectModel.deleted_date.is_(None))
            .filter(CurriculumSubjectModel.is_active == 1)
            .filter(CurriculumSubjectModel.name_es == name)
            .first()
        )
        if curriculum_subject:
            return curriculum_subject
        return (
            self.db.query(CurriculumSubjectModel)
            .filter(CurriculumSubjectModel.deleted_date.is_(None))
            .filter(CurriculumSubjectModel.is_active == 1)
            .filter(CurriculumSubjectModel.name_es.ilike(f"%{name}%"))
            .order_by(CurriculumSubjectModel.sort_order.asc())
            .first()
        )

    def _get_or_create_subject_level(
        self, curriculum_subject_id: int, education_level_id: int
    ) -> Optional[CurriculumSubjectLevelModel]:
        subject_level = (
            self.db.query(CurriculumSubjectLevelModel)
            .filter(CurriculumSubjectLevelModel.deleted_date.is_(None))
            .filter(CurriculumSubjectLevelModel.is_active == 1)
            .filter(CurriculumSubjectLevelModel.curriculum_subject_id == curriculum_subject_id)
            .filter(CurriculumSubjectLevelModel.education_level_id == education_level_id)
            .first()
        )
        if subject_level:
            return subject_level

        subject = (
            self.db.query(CurriculumSubjectModel)
            .filter(CurriculumSubjectModel.id == curriculum_subject_id)
            .filter(CurriculumSubjectModel.deleted_date.is_(None))
            .first()
        )
        level = (
            self.db.query(EducationLevelModel)
            .filter(EducationLevelModel.id == education_level_id)
            .filter(EducationLevelModel.deleted_date.is_(None))
            .first()
        )
        if not subject or not level:
            return None

        ministry_code = (level.oa_level_code or "OA").strip()[:16] or "OA"
        now = datetime.utcnow()
        subject_level = CurriculumSubjectLevelModel(
            curriculum_subject_id=curriculum_subject_id,
            education_level_id=education_level_id,
            ministry_subject_code=ministry_code,
            is_active=1,
            added_date=now,
            updated_date=now,
        )
        self.db.add(subject_level)
        self.db.flush()
        return subject_level

    def list_by_subject_and_level(self, subject_name_es: str, education_level_id: int) -> Any:
        try:
            curriculum_subject = self._resolve_curriculum_subject(subject_name_es)
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
                .order_by(LearningObjectiveModel.sort_order.asc(), LearningObjectiveModel.code.asc())
                .all()
            )
            data = [self._row_to_dict(r) for r in rows]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def _row_to_dict(self, row: LearningObjectiveModel) -> dict:
        csl = (
            self.db.query(CurriculumSubjectLevelModel)
            .filter(CurriculumSubjectLevelModel.id == row.curriculum_subject_level_id)
            .first()
        )
        subject_name_es = None
        education_level_name_es = None
        curriculum_subject_id = None
        education_level_id = None
        if csl:
            curriculum_subject_id = csl.curriculum_subject_id
            education_level_id = csl.education_level_id
            subj = (
                self.db.query(CurriculumSubjectModel)
                .filter(CurriculumSubjectModel.id == csl.curriculum_subject_id)
                .first()
            )
            level = (
                self.db.query(EducationLevelModel)
                .filter(EducationLevelModel.id == csl.education_level_id)
                .first()
            )
            if subj:
                subject_name_es = subj.name_es
            if level:
                education_level_name_es = level.name_es
        return {
            "id": row.id,
            "code": row.code,
            "description": row.description,
            "is_priority": bool(row.is_priority),
            "sort_order": row.sort_order,
            "is_active": bool(row.is_active),
            "curriculum_subject_level_id": row.curriculum_subject_level_id,
            "curriculum_subject_id": curriculum_subject_id,
            "education_level_id": education_level_id,
            "subject_name_es": subject_name_es,
            "education_level_name_es": education_level_name_es,
        }

    def admin_get(self, objective_id: int) -> Any:
        try:
            row = (
                self.db.query(LearningObjectiveModel)
                .filter(LearningObjectiveModel.id == objective_id)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .first()
            )
            if not row:
                return {"status": "error", "message": "Objetivo de aprendizaje no encontrado."}
            return {"status": "success", "data": self._row_to_dict(row)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def admin_store(self, data: dict) -> Any:
        try:
            curriculum_subject_id = int(data["curriculum_subject_id"])
            education_level_id = int(data["education_level_id"])
            code = (data.get("code") or "").strip()
            description = (data.get("description") or "").strip()
            if not code:
                return {"status": "error", "message": "El código del OA es obligatorio."}
            if not description:
                return {"status": "error", "message": "La descripción del OA es obligatoria."}

            subject_level = self._get_or_create_subject_level(
                curriculum_subject_id, education_level_id
            )
            if not subject_level:
                return {"status": "error", "message": "Asignatura o nivel educativo no válido."}

            duplicate = (
                self.db.query(LearningObjectiveModel)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .filter(LearningObjectiveModel.curriculum_subject_level_id == subject_level.id)
                .filter(LearningObjectiveModel.code == code)
                .first()
            )
            if duplicate:
                return {
                    "status": "error",
                    "message": f"Ya existe el código {code} para esta asignatura y nivel.",
                }

            max_sort = (
                self.db.query(LearningObjectiveModel.sort_order)
                .filter(LearningObjectiveModel.curriculum_subject_level_id == subject_level.id)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .order_by(LearningObjectiveModel.sort_order.desc())
                .first()
            )
            next_sort = (max_sort[0] if max_sort and max_sort[0] is not None else 0) + 1
            sort_order = data.get("sort_order")
            if sort_order is None:
                sort_order = next_sort

            now = datetime.utcnow()
            row = LearningObjectiveModel(
                curriculum_subject_level_id=subject_level.id,
                code=code[:32],
                description=description,
                is_priority=1 if data.get("is_priority") else 0,
                sort_order=int(sort_order),
                is_active=1,
                added_date=now,
                updated_date=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {
                "status": "success",
                "message": "Objetivo de aprendizaje creado.",
                "id": row.id,
                "data": self._row_to_dict(row),
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def admin_update(self, objective_id: int, data: dict) -> Any:
        try:
            row = (
                self.db.query(LearningObjectiveModel)
                .filter(LearningObjectiveModel.id == objective_id)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .first()
            )
            if not row:
                return {"status": "error", "message": "Objetivo de aprendizaje no encontrado."}

            if "code" in data and data["code"] is not None:
                code = str(data["code"]).strip()
                if not code:
                    return {"status": "error", "message": "El código no puede estar vacío."}
                duplicate = (
                    self.db.query(LearningObjectiveModel)
                    .filter(LearningObjectiveModel.id != objective_id)
                    .filter(LearningObjectiveModel.deleted_date.is_(None))
                    .filter(
                        LearningObjectiveModel.curriculum_subject_level_id
                        == row.curriculum_subject_level_id
                    )
                    .filter(LearningObjectiveModel.code == code)
                    .first()
                )
                if duplicate:
                    return {
                        "status": "error",
                        "message": f"Ya existe el código {code} en esta asignatura y nivel.",
                    }
                row.code = code[:32]

            if "description" in data and data["description"] is not None:
                description = str(data["description"]).strip()
                if not description:
                    return {"status": "error", "message": "La descripción no puede estar vacía."}
                row.description = description

            if "is_priority" in data and data["is_priority"] is not None:
                row.is_priority = 1 if data["is_priority"] else 0

            if "sort_order" in data and data["sort_order"] is not None:
                row.sort_order = int(data["sort_order"])

            if "is_active" in data and data["is_active"] is not None:
                row.is_active = 1 if data["is_active"] else 0

            row.updated_date = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return {
                "status": "success",
                "message": "Objetivo de aprendizaje actualizado.",
                "data": self._row_to_dict(row),
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def admin_delete(self, objective_id: int) -> Any:
        try:
            row = (
                self.db.query(LearningObjectiveModel)
                .filter(LearningObjectiveModel.id == objective_id)
                .filter(LearningObjectiveModel.deleted_date.is_(None))
                .first()
            )
            if not row:
                return {"status": "error", "message": "Objetivo de aprendizaje no encontrado."}
            now = datetime.utcnow()
            row.deleted_date = now
            row.updated_date = now
            row.is_active = 0
            self.db.commit()
            return {"status": "success", "message": "Objetivo de aprendizaje eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
