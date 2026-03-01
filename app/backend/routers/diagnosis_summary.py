from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import (
    UserLogin,
    DiagnosisSummaryList,
    StoreDiagnosisSummary,
    UpdateDiagnosisSummary,
)
from app.backend.classes.diagnosis_summary_class import DiagnosisSummaryClass
from app.backend.classes.school_class import SchoolClass
from app.backend.auth.auth_user import get_current_active_user

diagnosis_summary = APIRouter(
    prefix="/diagnosis_summary",
    tags=["Diagnosis Summary"],
)


@diagnosis_summary.post("/")
def index(
    body: DiagnosisSummaryList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista resúmenes por diagnóstico con filtros opcionales (paginado si page > 0)."""
    page_value = 0 if body.page is None else body.page
    result = DiagnosisSummaryClass(db).get_all(
        page=page_value,
        items_per_page=body.per_page,
        school_id=body.school_id,
        special_educational_need_id=body.special_educational_need_id,
        course_id=body.course_id,
        year_index=body.year_index,
    )
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result},
    )


@diagnosis_summary.get("/list")
def list_all(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista todos los resúmenes sin paginación."""
    result = DiagnosisSummaryClass(db).get_all(page=0, items_per_page=None)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result},
    )


@diagnosis_summary.post("/store")
def store(
    body: StoreDiagnosisSummary,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza resumen por diagnóstico (NEE, curso, año). Si existe la misma clave única, update; si no, store. school_id de sesión."""
    school_id = session_user.school_id if session_user else None
    if not school_id and session_user and session_user.customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=session_user.customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get("id")
    inputs = body.dict()
    inputs["school_id"] = school_id
    result = DiagnosisSummaryClass(db).store_or_update(inputs)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al crear/actualizar"),
                "data": None,
            },
        )
    created = result.get("created", True)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        content={
            "status": 201 if created else 200,
            "message": result.get("message", "Creado" if created else "Actualizado"),
            "data": {"id": result.get("id"), "created": created},
        },
    )


@diagnosis_summary.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un resumen por id."""
    result = DiagnosisSummaryClass(db).get(id)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "No encontrado"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result},
    )


@diagnosis_summary.put("/update/{id}")
def update(
    id: int,
    body: UpdateDiagnosisSummary,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un resumen por id."""
    result = DiagnosisSummaryClass(db).update(id, body.dict(exclude_unset=True))
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error al actualizar"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": result.get("message", "Actualizado"), "data": None},
    )


@diagnosis_summary.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un resumen por id."""
    result = DiagnosisSummaryClass(db).delete(id)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "No encontrado"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": result.get("message", "Eliminado"), "data": None},
    )
