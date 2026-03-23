"""Document 31 – Pauta de evaluación pedagógica - Docente de aula - first grade."""
from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StorePedagogicalEvaluationClassroomFirstGrade, UpdatePedagogicalEvaluationClassroomFirstGrade
from app.backend.classes.pedagogical_evaluation_classroom_first_grade_class import PedagogicalEvaluationClassroomFirstGradeClass

pedagogical_evaluation_classroom_first_grade = APIRouter(
    prefix="/pedagogical_evaluation_classroom_first_grade",
    tags=["Pedagogical Evaluation Classroom First Grade (Document 31)"],
)


@pedagogical_evaluation_classroom_first_grade.get("/student/{student_id}")
async def get_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el último informe de evaluación pedagógica (doc 31) por estudiante."""
    try:
        service = PedagogicalEvaluationClassroomFirstGradeClass(db)
        result = service.get_by_student_id(student_id)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe no encontrado."), "data": None},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result})
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@pedagogical_evaluation_classroom_first_grade.post("/store")
async def store(
    data: StorePedagogicalEvaluationClassroomFirstGrade,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo informe de evaluación pedagógica (Documento 31 - first grade)."""
    try:
        payload = data.dict()
        service = PedagogicalEvaluationClassroomFirstGradeClass(db)
        result = service.store(payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error guardando informe."), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Informe guardado."), "data": {"id": result.get("id")}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@pedagogical_evaluation_classroom_first_grade.put("/{id}")
async def update(
    id: int,
    data: UpdatePedagogicalEvaluationClassroomFirstGrade,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un informe de evaluación pedagógica (Documento 31 - first grade)."""
    try:
        payload = data.dict(exclude_unset=True)
        service = PedagogicalEvaluationClassroomFirstGradeClass(db)
        result = service.update(id, payload)
        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "Informe no encontrado.")},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message", "OK")})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})
