# Anamnesis (documento tipo 3)
from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from app.backend.classes.anamnesis_class import AnamnesisClass
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, StoreAnamnesis, UpdateAnamnesis, AnamnesisList
from typing import Optional
from sqlalchemy.orm import Session

anamnesis_router = APIRouter(
    prefix="/anamnesis",
    tags=["Anamnesis"],
)

@anamnesis_router.post("/store")
async def store_anamnesis(
    data: StoreAnamnesis,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva anamnesis (documento tipo 3) para un estudiante."""
    try:
        service = AnamnesisClass(db)
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = service.store(payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": result.get("message", "Error al guardar anamnesis"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Anamnesis creada correctamente"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@anamnesis_router.put("/{anamnesis_id}")
async def update_anamnesis(
    anamnesis_id: int,
    data: UpdateAnamnesis,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza una anamnesis existente."""
    try:
        service = AnamnesisClass(db)
        payload = data.model_dump(exclude_none=True) if hasattr(data, "model_dump") else data.dict(exclude_none=True)
        result = service.update(anamnesis_id, payload)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Anamnesis no encontrada"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Anamnesis actualizada correctamente"),
                "data": {"id": result.get("id")},
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@anamnesis_router.get("/id/{student_id}")
async def get_anamnesis_by_student_id(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene la anamnesis más reciente de un estudiante por student_id (incluye informantes, entrevistadores y miembros del hogar)."""
    try:
        service = AnamnesisClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "No se encontró anamnesis para este estudiante"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Anamnesis encontrada",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@anamnesis_router.get("/student/{student_id}")
async def get_anamnesis_by_student(
    student_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene la anamnesis más reciente de un estudiante por student_id."""
    try:
        service = AnamnesisClass(db)
        result = service.get_by_student_id(student_id)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "No se encontró anamnesis para este estudiante"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Anamnesis encontrada",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )


@anamnesis_router.get("/list")
async def list_anamnesis(
    student_id: Optional[int] = None,
    page: Optional[int] = None,
    per_page: int = 10,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista anamnesis; opcionalmente filtrada por student_id y paginada."""
    try:
        service = AnamnesisClass(db)
        result = service.get_all(student_id=student_id, page=page, per_page=per_page)

        if isinstance(result, dict) and result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al listar anamnesis"),
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Listado de anamnesis",
                "data": result,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": None,
            },
        )
