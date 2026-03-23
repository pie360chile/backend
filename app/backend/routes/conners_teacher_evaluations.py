"""Document 29 – Conners Teacher Abbreviated + Conduct Questionnaire."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreConnersTeacherEvaluation, UpdateConnersTeacherEvaluation
from app.backend.classes.conners_teacher_evaluation_class import ConnersTeacherEvaluationClass
from sqlalchemy.orm import Session

conners_teacher_evaluations = APIRouter(
    prefix="/conners_teacher_evaluations",
    tags=["Conners Teacher Evaluation (Document 29)"],
)


@conners_teacher_evaluations.get("/by_student/{student_id}")
def get_by_student_id(
    student_id: int,
    latest_only: bool = Query(True, description="True = only latest; False = all"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get Conners evaluation(s) for a student (with scores and conduct_responses)."""
    try:
        result = ConnersTeacherEvaluationClass(db).get_by_student_id(
            student_id=student_id, latest_only=latest_only
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@conners_teacher_evaluations.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a Conners evaluation by id (includes scores and conduct_responses)."""
    try:
        result = ConnersTeacherEvaluationClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Not found"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@conners_teacher_evaluations.post("/store")
def store(
    data: StoreConnersTeacherEvaluation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new Conners teacher evaluation (with scores and conduct_responses)."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = ConnersTeacherEvaluationClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error saving"), "data": None},
            )
        data_out = result.get("data") if result.get("data") else {"id": result.get("id")}
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Evaluation created"),
                "data": data_out,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@conners_teacher_evaluations.put("/{id}")
def update(
    id: int,
    data: UpdateConnersTeacherEvaluation,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a Conners evaluation by id."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict()
        result = ConnersTeacherEvaluationClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Not found"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Updated"), "data": result.get("data")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
