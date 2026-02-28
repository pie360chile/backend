"""Router unificado: Plan de Apoyo Individual por curso (4. Ajustes + b) Adecuaciones + Apoyo individual)."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
from app.backend.classes.course_adjustment_class import CourseAdjustmentClass
from app.backend.classes.course_curricular_adequacy_class import CourseCurricularAdequacyClass
from app.backend.classes.course_individual_support_class import CourseIndividualSupportClass
from sqlalchemy.orm import Session

plan_apoyo_individual = APIRouter(
    prefix="/plan_apoyo_individual",
    tags=["Plan de Apoyo Individual"],
)


@plan_apoyo_individual.get("/by_course/{course_id}")
def get_full_by_course_id(
    course_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Devuelve en una sola respuesta todo el Plan de Apoyo Individual del curso:
    - adjustments: 4. Ajustes (aspectos con value, other_aspect_text, student_ids)
    - curricular_adequacies: b) Adecuaciones curriculares (tipos con applied, scope_text, strategies_text, subject_ids, student_ids)
    - individual_supports: Apoyo individual (lista de apoyos con área, horario, fechas, student_ids)
    """
    try:
        adj = CourseAdjustmentClass(db).get_by_course_id(course_id)
        adeq = CourseCurricularAdequacyClass(db).get_by_course_id(course_id)
        supp = CourseIndividualSupportClass(db).get_by_course_id(course_id, include_deleted=False)

        adjustments = adj.get("data", []) if adj.get("status") == "success" else []
        curricular_adequacies = adeq.get("data", []) if adeq.get("status") == "success" else []
        individual_supports = supp.get("data", []) if supp.get("status") == "success" else []

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": {
                    "adjustments": adjustments,
                    "curricular_adequacies": curricular_adequacies,
                    "individual_supports": individual_supports,
                },
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )
