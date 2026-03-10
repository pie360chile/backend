"""Document 29: Conners Teacher Abbreviated + Conduct Questionnaire."""

from datetime import datetime, date
from typing import Optional, Any, List
from sqlalchemy.orm import Session
from app.backend.db.models import (
    ConnersTeacherEvaluationModel,
    ConnersTeacherScoreModel,
    ConnersConductResponseModel,
)


def _serialize_date(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v) if v else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _eval_to_dict(row: ConnersTeacherEvaluationModel) -> dict:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "evaluation_date": _serialize_date(row.evaluation_date),
        "evaluator_name": (row.evaluator_name or "").strip() or None,
        "evaluation_type": (row.evaluation_type or "ingreso").strip(),
        "comments_observations": (row.comments_observations or "").strip() or None,
        "total_score": row.total_score,
        "created_at": _serialize_date(row.created_at),
        "updated_at": _serialize_date(row.updated_at),
    }


class ConnersTeacherEvaluationClass:
    def __init__(self, db: Session):
        self.db = db

    def _get_scores(self, evaluation_id: int) -> List[dict]:
        rows = (
            self.db.query(ConnersTeacherScoreModel)
            .filter(ConnersTeacherScoreModel.evaluation_id == evaluation_id)
            .order_by(ConnersTeacherScoreModel.item_index)
            .all()
        )
        return [{"item_index": r.item_index, "score": r.score} for r in rows]

    def _get_conduct_responses(self, evaluation_id: int) -> List[dict]:
        rows = (
            self.db.query(ConnersConductResponseModel)
            .filter(ConnersConductResponseModel.evaluation_id == evaluation_id)
            .order_by(ConnersConductResponseModel.item_index)
            .all()
        )
        return [{"item_index": r.item_index, "response": (r.response or "").lower()} for r in rows]

    def get_by_id(self, id: int) -> Any:
        """Get evaluation by id (includes scores and conduct_responses)."""
        try:
            row = (
                self.db.query(ConnersTeacherEvaluationModel)
                .filter(ConnersTeacherEvaluationModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Evaluation not found.", "data": None}
            data = _eval_to_dict(row)
            data["scores"] = self._get_scores(row.id)
            data["conduct_responses"] = self._get_conduct_responses(row.id)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_student_id(self, student_id: int, latest_only: bool = True) -> Any:
        """Get evaluation(s) for student. If latest_only=True returns only the most recent."""
        try:
            q = (
                self.db.query(ConnersTeacherEvaluationModel)
                .filter(ConnersTeacherEvaluationModel.student_id == student_id)
                .order_by(ConnersTeacherEvaluationModel.id.desc())
            )
            if latest_only:
                row = q.first()
                if not row:
                    return {"status": "success", "data": None}
                data = _eval_to_dict(row)
                data["scores"] = self._get_scores(row.id)
                data["conduct_responses"] = self._get_conduct_responses(row.id)
                return {"status": "success", "data": data}
            rows = q.all()
            result = []
            for row in rows:
                d = _eval_to_dict(row)
                d["scores"] = self._get_scores(row.id)
                d["conduct_responses"] = self._get_conduct_responses(row.id)
                result.append(d)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def _save_scores(self, evaluation_id: int, scores: List[dict]) -> None:
        self.db.query(ConnersTeacherScoreModel).filter(
            ConnersTeacherScoreModel.evaluation_id == evaluation_id,
        ).delete(synchronize_session=False)
        for s in scores or []:
            item_index = int(s.get("item_index", 0))
            score = int(s.get("score", 0))
            if 1 <= item_index <= 10 and 0 <= score <= 3:
                self.db.add(
                    ConnersTeacherScoreModel(
                        evaluation_id=evaluation_id,
                        item_index=item_index,
                        score=score,
                    )
                )

    def _save_conduct_responses(self, evaluation_id: int, conduct_responses: List[dict]) -> None:
        self.db.query(ConnersConductResponseModel).filter(
            ConnersConductResponseModel.evaluation_id == evaluation_id,
        ).delete(synchronize_session=False)
        valid_responses = ("n", "p", "b", "m")
        for r in conduct_responses or []:
            item_index = int(r.get("item_index", 0))
            response = (r.get("response") or "").strip().lower()[:1]
            if 1 <= item_index <= 18 and response in valid_responses:
                self.db.add(
                    ConnersConductResponseModel(
                        evaluation_id=evaluation_id,
                        item_index=item_index,
                        response=response,
                    )
                )

    def store(self, data: dict) -> Any:
        """Create a new Conners teacher evaluation with scores and conduct responses."""
        try:
            student_id = int(data.get("student_id"))
            if not student_id:
                return {"status": "error", "message": "student_id is required.", "data": None}

            evaluation_date = _parse_date(data.get("evaluation_date"))
            if not evaluation_date:
                return {"status": "error", "message": "evaluation_date is required (YYYY-MM-DD).", "data": None}

            evaluator_name = (data.get("evaluator_name") or "").strip() or ""
            evaluation_type = (data.get("evaluation_type") or "ingreso").strip()
            if evaluation_type not in ("ingreso", "reevaluacion"):
                evaluation_type = "ingreso"
            total_score = data.get("total_score")
            if total_score is not None:
                total_score = int(total_score)

            row = ConnersTeacherEvaluationModel(
                student_id=student_id,
                evaluation_date=evaluation_date,
                evaluator_name=evaluator_name,
                evaluation_type=evaluation_type,
                comments_observations=(data.get("comments_observations") or "").strip() or None,
                total_score=total_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.flush()

            self._save_scores(row.id, data.get("scores") or [])
            self._save_conduct_responses(row.id, data.get("conduct_responses") or [])

            self.db.commit()
            self.db.refresh(row)
            return {
                "status": "success",
                "message": "Conners evaluation created.",
                "data": _eval_to_dict(row),
                "id": row.id,
                "created": True,
            }
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> Any:
        """Update an existing Conners evaluation."""
        try:
            row = (
                self.db.query(ConnersTeacherEvaluationModel)
                .filter(ConnersTeacherEvaluationModel.id == id)
                .first()
            )
            if not row:
                return {"status": "error", "message": "Evaluation not found.", "data": None}

            if "evaluation_date" in data and data.get("evaluation_date"):
                row.evaluation_date = _parse_date(data["evaluation_date"]) or row.evaluation_date
            if "evaluator_name" in data:
                row.evaluator_name = (data.get("evaluator_name") or "").strip() or ""
            if "evaluation_type" in data and data.get("evaluation_type"):
                et = (data["evaluation_type"] or "").strip()
                if et in ("ingreso", "reevaluacion"):
                    row.evaluation_type = et
            if "comments_observations" in data:
                row.comments_observations = (data.get("comments_observations") or "").strip() or None
            if "total_score" in data:
                row.total_score = int(data["total_score"]) if data.get("total_score") is not None else None

            row.updated_at = datetime.utcnow()

            if "scores" in data and data["scores"] is not None:
                self._save_scores(row.id, data["scores"])
            if "conduct_responses" in data and data["conduct_responses"] is not None:
                self._save_conduct_responses(row.id, data["conduct_responses"])

            self.db.commit()
            self.db.refresh(row)
            out = _eval_to_dict(row)
            out["scores"] = self._get_scores(row.id)
            out["conduct_responses"] = self._get_conduct_responses(row.id)
            return {"status": "success", "message": "Conners evaluation updated.", "data": out}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}
