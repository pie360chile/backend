"""Document 20 – Community Education Support Program (CESP)."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin, StoreCespDocument, UpdateCespDocument
from app.backend.classes.cesp_class import CespClass

cesp = APIRouter(
    prefix="/cesp",
    tags=["CESP (Document 20 – Community Education Support Program)"],
)


@cesp.get("/period_types")
def list_period_types(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista tipos de período (ej. Anual) para CESP."""
    try:
        data = CespClass(db).get_period_types()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": "OK", "data": data},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@cesp.get("")
def list_cesp(
    student_id: Optional[int] = Query(None, description="Filtrar por estudiante"),
    include_deleted: bool = Query(False, description="Incluir eliminados (soft)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista documentos CESP; opcionalmente por student_id."""
    try:
        result = CespClass(db).get(student_id=student_id, include_deleted=include_deleted)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": 500, "message": result.get("message", "Error"), "data": []},
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


@cesp.get("/by_student/{student_id}")
def get_cesp_by_student(
    student_id: int,
    latest_only: bool = Query(True, description="Solo el más reciente"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene CESP(s) por student_id. Si latest_only=True devuelve solo el más reciente."""
    try:
        result = CespClass(db).get_by_student_id(student_id=student_id, latest_only=latest_only)
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


@cesp.get("/{id}")
def get_cesp(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un CESP por id (con guardians, participant_professional, support_team_members)."""
    try:
        result = CespClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado"), "data": None},
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


@cesp.post("/store")
def store_cesp(
    data: StoreCespDocument,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un documento CESP (opcionalmente con guardians, participant_professional, support_team_members)."""
    try:
        payload = data.model_dump()
        if payload.get("guardians") is not None:
            payload["guardians"] = [g.model_dump() for g in (data.guardians or [])]
        if payload.get("participant_professional") is not None:
            payload["participant_professional"] = data.participant_professional.model_dump() if data.participant_professional else None
        if payload.get("support_team_members") is not None:
            payload["support_team_members"] = [m.model_dump() for m in (data.support_team_members or [])]
        result = CespClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": 400, "message": result.get("message", "Error al crear"), "data": None},
            )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": 201, "message": result.get("message", "Creado"), "data": result.get("data"), "id": result.get("id")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@cesp.put("/{id}")
def update_cesp(
    id: int,
    data: UpdateCespDocument,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un CESP por id (guardians/participant/support_team se reemplazan si se envían)."""
    try:
        payload = data.model_dump(exclude_unset=True)
        if "guardians" in payload and payload["guardians"] is not None:
            payload["guardians"] = [g.model_dump() for g in (data.guardians or [])]
        if "participant_professional" in payload and payload["participant_professional"] is not None:
            payload["participant_professional"] = data.participant_professional.model_dump() if data.participant_professional else None
        if "support_team_members" in payload and payload["support_team_members"] is not None:
            payload["support_team_members"] = [m.model_dump() for m in (data.support_team_members or [])]
        result = CespClass(db).update(id, payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Actualizado"), "id": result.get("id")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )


@cesp.delete("/{id}")
def delete_cesp(
    id: int,
    soft: bool = Query(True, description="True = soft delete (deleted_date)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Elimina un CESP por id (soft o físico)."""
    try:
        result = CespClass(db).delete(id, soft=soft)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": result.get("message", "No encontrado")},
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": 200, "message": result.get("message", "Eliminado")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
