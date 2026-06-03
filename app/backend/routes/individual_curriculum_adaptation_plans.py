"""Document 21 – Individual Curriculum Adaptation Plan (ICAP / PACI)."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.individual_curriculum_adaptation_plan_class import (
    IndividualCurriculumAdaptationPlanClass,
)
from app.backend.db.database import get_db
from app.backend.schemas import (
    StoreIndividualCurriculumAdaptationPlan,
    UpdateIndividualCurriculumAdaptationPlan,
    UserLogin,
)

individual_curriculum_adaptation_plans = APIRouter(
    prefix="/individual_curriculum_adaptation_plans",
    tags=["Individual Curriculum Adaptation Plans"],
)


def _body_to_dict(body) -> dict:
    return body.model_dump(exclude_unset=False) if hasattr(body, "model_dump") else body.dict()


@individual_curriculum_adaptation_plans.get("/semesters")
async def list_icap_semesters(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        data = IndividualCurriculumAdaptationPlanClass(db).get_semesters()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": data},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@individual_curriculum_adaptation_plans.get("/by_student/{student_id}")
async def get_icap_by_student(
    student_id: int,
    latest_only: bool = Query(True),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = IndividualCurriculumAdaptationPlanClass(db).get_by_student_id(
            student_id, latest_only=latest_only
        )
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "ICAP encontrado" if result else "Sin ICAP para este estudiante",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@individual_curriculum_adaptation_plans.get("/{plan_id}")
async def get_icap_by_id(
    plan_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = IndividualCurriculumAdaptationPlanClass(db).get(plan_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "ICAP encontrado", "data": result},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@individual_curriculum_adaptation_plans.post("/store")
async def store_icap(
    body: StoreIndividualCurriculumAdaptationPlan,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        data = _body_to_dict(body)
        if data.get("school_id") is None and getattr(session_user, "school_id", None):
            data["school_id"] = session_user.school_id
        result = IndividualCurriculumAdaptationPlanClass(db).store(data)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "ICAP guardado"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@individual_curriculum_adaptation_plans.put("/{plan_id}")
async def update_icap(
    plan_id: int,
    body: UpdateIndividualCurriculumAdaptationPlan,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        data = _body_to_dict(body)
        if data.get("school_id") is None and getattr(session_user, "school_id", None):
            data["school_id"] = session_user.school_id
        result = IndividualCurriculumAdaptationPlanClass(db).update(plan_id, data)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "ICAP actualizado"), "data": None},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
