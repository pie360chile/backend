from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.curriculum_subject_class import CurriculumSubjectClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

curriculum_subjects = APIRouter(
    prefix="/curriculum_subjects",
    tags=["Curriculum Subjects"],
)


@curriculum_subjects.get("")
def list_curriculum_subjects(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        result = CurriculumSubjectClass(db).get_list()
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al listar"),
                    "data": [],
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": result.get("data", [])},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )
