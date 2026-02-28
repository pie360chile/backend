from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    DiversityCriterionModel,
    DiversityStrategyOptionModel,
    CourseDiversityResponseModel,
    CourseDiversityResponseStudentModel,
    CourseDiversityObservationModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _response_to_dict(r: CourseDiversityResponseModel) -> dict:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "diversity_criterion_id": r.diversity_criterion_id,
        "criterion_selected": r.criterion_selected,
        "diversity_strategy_option_id": r.diversity_strategy_option_id,
        "how_text": r.how_text,
        "added_date": _serialize_date(r.added_date),
        "updated_date": _serialize_date(r.updated_date),
        "deleted_date": _serialize_date(r.deleted_date),
    }


class CourseDiversityResponseClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, course_id: Optional[int] = None, include_deleted: bool = False) -> Any:
        """Lista respuestas. Filtro opcional por course_id (-1 o None = no filtrar). include_deleted=True devuelve todos (incl. borrados)."""
        try:
            q = self.db.query(CourseDiversityResponseModel)
            if not include_deleted:
                q = q.filter(CourseDiversityResponseModel.deleted_date.is_(None))
            if course_id is not None and course_id != -1:
                q = q.filter(CourseDiversityResponseModel.course_id == course_id)
            rows = q.order_by(CourseDiversityResponseModel.course_id, CourseDiversityResponseModel.diversity_criterion_id).all()
            return {"status": "success", "data": [_response_to_dict(r) for r in rows]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> Any:
        """Obtiene una respuesta por id e incluye student_ids."""
        try:
            row = (
                self.db.query(CourseDiversityResponseModel)
                .filter(CourseDiversityResponseModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado.", "data": None}
            data = _response_to_dict(row)
            student_ids = (
                self.db.query(CourseDiversityResponseStudentModel.student_id)
                .filter(CourseDiversityResponseStudentModel.course_diversity_response_id == id)
                .all()
            )
            data["student_ids"] = [s[0] for s in student_ids]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_course_id(self, course_id: int) -> Any:
        """Estructura completa para el curso: criterios, opciones, respuesta por criterio y student_ids."""
        try:
            criteria = (
                self.db.query(DiversityCriterionModel)
                .filter(DiversityCriterionModel.deleted_date.is_(None))
                .order_by(DiversityCriterionModel.sort_order)
                .all()
            )
            responses = (
                self.db.query(CourseDiversityResponseModel)
                .filter(
                    CourseDiversityResponseModel.course_id == course_id,
                    CourseDiversityResponseModel.deleted_date.is_(None),
                )
                .all()
            )
            response_by_criterion = {r.diversity_criterion_id: r for r in responses}
            result = []
            for c in criteria:
                options = (
                    self.db.query(DiversityStrategyOptionModel)
                    .filter(
                        DiversityStrategyOptionModel.diversity_criterion_id == c.id,
                        DiversityStrategyOptionModel.deleted_date.is_(None),
                    )
                    .order_by(DiversityStrategyOptionModel.sort_order)
                    .all()
                )
                resp = response_by_criterion.get(c.id)
                student_ids = []
                if resp:
                    student_ids = [
                        s[0]
                        for s in self.db.query(CourseDiversityResponseStudentModel.student_id)
                        .filter(CourseDiversityResponseStudentModel.course_diversity_response_id == resp.id)
                        .all()
                    ]
                result.append({
                    "criterion": {
                        "id": c.id,
                        "key": c.key,
                        "label": c.label,
                        "sort_order": c.sort_order,
                    },
                    "options": [
                        {"id": o.id, "label": o.label, "sort_order": o.sort_order}
                        for o in options
                    ],
                    "response": _response_to_dict(resp) if resp else None,
                    "student_ids": student_ids,
                })
            obs_row = (
                self.db.query(CourseDiversityObservationModel)
                .filter(CourseDiversityObservationModel.course_id == course_id)
                .first()
            )
            observations = obs_row.observations if obs_row else None
            return {"status": "success", "data": result, "observations": observations}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_observations(self, course_id: int) -> Any:
        """Devuelve las observaciones de diversidad del curso (tabla course_diversity_observations)."""
        try:
            row = (
                self.db.query(CourseDiversityObservationModel)
                .filter(CourseDiversityObservationModel.course_id == course_id)
                .first()
            )
            return {"status": "success", "data": {"observations": row.observations if row else None}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def set_observations(self, course_id: int, observations: Optional[str]) -> Any:
        """Crea o actualiza las observaciones del curso (una fila por course_id)."""
        try:
            row = (
                self.db.query(CourseDiversityObservationModel)
                .filter(CourseDiversityObservationModel.course_id == course_id)
                .first()
            )
            now = datetime.now()
            text = (observations or "").strip() if observations is not None else ""
            if row:
                row.observations = text or None
                row.updated_date = now
            else:
                self.db.add(CourseDiversityObservationModel(
                    course_id=course_id,
                    observations=text or None,
                    added_date=now,
                    updated_date=now,
                ))
            self.db.commit()
            return {"status": "success", "message": "Observaciones guardadas."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        """Por cada envío del front (course_id, diversity_criterion_id, criterion_selected, ...):
        - criterion_selected == 1: si existe registro activo → solo actualizar estudiantes, opción y how_text; si no existe → crear (store) con added_date.
        - criterion_selected == 0: actualizar ese criterio poniendo deleted_date y borrando sus estudiantes."""
        try:
            course_id = data.get("course_id")
            diversity_criterion_id = data.get("diversity_criterion_id")
            if course_id is None or diversity_criterion_id is None or course_id == "" or diversity_criterion_id == "":
                return {"status": "error", "message": "course_id y diversity_criterion_id son requeridos."}
            course_id = int(course_id)
            diversity_criterion_id = int(diversity_criterion_id)
            # Aceptar True/1/"1" como seleccionado; todo lo demás (False, 0, "0", None) como no seleccionado
            cs_val = data.get("criterion_selected")
            criterion_selected = 1 if cs_val in (True, 1, "1") else 0
            now = datetime.now()
            # Buscar cualquier registro para (course_id, diversity_criterion_id), con o sin deleted_date (evita duplicate key al re-marcar)
            row = (
                self.db.query(CourseDiversityResponseModel)
                .filter(
                    CourseDiversityResponseModel.course_id == course_id,
                    CourseDiversityResponseModel.diversity_criterion_id == diversity_criterion_id,
                )
                .first()
            )
            if criterion_selected == 0:
                # Al desmarcar: row ya es el registro (con o sin deleted_date)
                if row:
                    response_id = row.id
                    row.criterion_selected = 0
                    row.deleted_date = now
                    row.updated_date = now
                    row.diversity_strategy_option_id = None
                    row.how_text = None
                    self.db.query(CourseDiversityResponseStudentModel).filter(
                        CourseDiversityResponseStudentModel.course_diversity_response_id == response_id,
                    ).delete(synchronize_session=False)
                    self.db.commit()
                    if "observations" in data:
                        self.set_observations(course_id, data.get("observations"))
                    return {"status": "success", "message": "Registro desmarcado (deleted_date) y estudiantes eliminados.", "id": response_id, "data": None}
                if "observations" in data:
                    self.set_observations(course_id, data.get("observations"))
                return {"status": "success", "message": "Sin registro que borrar.", "id": None, "data": None}

            # criterion_selected == 1: crear o actualizar
            diversity_strategy_option_id = data.get("diversity_strategy_option_id")
            how_text = data.get("how_text")
            student_ids = data.get("student_ids") or []

            if row:
                row.criterion_selected = 1
                row.diversity_strategy_option_id = diversity_strategy_option_id
                row.how_text = how_text
                row.updated_date = now
                row.deleted_date = None  # restaurar si estaba borrado
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Registro actualizado."
            else:
                row = CourseDiversityResponseModel(
                    course_id=course_id,
                    diversity_criterion_id=diversity_criterion_id,
                    criterion_selected=1,
                    diversity_strategy_option_id=diversity_strategy_option_id,
                    how_text=how_text,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                )
                self.db.add(row)
                self.db.commit()
                self.db.refresh(row)
                response_id = row.id
                msg = "Registro creado."

            self._sync_students(response_id, student_ids)
            self.db.commit()
            if "observations" in data:
                self.set_observations(course_id, data.get("observations"))
            return {"status": "success", "message": msg, "id": response_id, "data": _response_to_dict(row)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def _sync_students(self, course_diversity_response_id: int, student_ids: List[int]) -> None:
        """Reemplaza los estudiantes asociados a la respuesta por student_ids."""
        self.db.query(CourseDiversityResponseStudentModel).filter(
            CourseDiversityResponseStudentModel.course_diversity_response_id == course_diversity_response_id,
        ).delete(synchronize_session=False)
        now = datetime.now()
        for sid in student_ids:
            if not sid:
                continue
            self.db.add(CourseDiversityResponseStudentModel(
                course_diversity_response_id=course_diversity_response_id,
                student_id=int(sid),
                added_date=now,
            ))

    def update(self, id: int, data: dict) -> Any:
        """Actualiza una respuesta por id. Opcional: student_ids para reemplazar."""
        try:
            row = (
                self.db.query(CourseDiversityResponseModel)
                .filter(CourseDiversityResponseModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            if "criterion_selected" in data:
                row.criterion_selected = 1 if data["criterion_selected"] else 0
            if "diversity_strategy_option_id" in data:
                row.diversity_strategy_option_id = data["diversity_strategy_option_id"]
            if "how_text" in data:
                row.how_text = data["how_text"]
            row.updated_date = datetime.now()
            if "student_ids" in data:
                self._sync_students(id, data["student_ids"] or [])
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Registro actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        """Borrado lógico: setea deleted_date."""
        try:
            row = self.db.query(CourseDiversityResponseModel).filter(CourseDiversityResponseModel.id == id).first()
            if not row:
                return {"status": "error", "message": "Registro no encontrado."}
            row.deleted_date = datetime.now()
            row.updated_date = datetime.now()
            self.db.commit()
            return {"status": "success", "message": "Registro eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
