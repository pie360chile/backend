from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import (
    UserLogin,
    StoreMeetingSchedualingRegisterProfessional,
    UpdateMeetingSchedualingRegisterProfessional,
    SyncMeetingSchedualingRegisterProfessionals,
)
from app.backend.classes.meeting_schedualing_register_professional_class import (
    MeetingSchedualingRegisterProfessionalClass,
)
from sqlalchemy.orm import Session
from typing import Optional

meeting_schedualing_register_professionals = APIRouter(
    prefix="/meeting_schedualing_register_professionals",
    tags=["Meeting Schedualing Register Professionals"],
)


@meeting_schedualing_register_professionals.get("")
def get_list(
    meeting_schedualing_register_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    professional_id: Optional[int] = Query(None, description="-1 o omitir = no filtrar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista registros activos (deleted_date is None). Filtros opcionales."""
    try:
        result = MeetingSchedualingRegisterProfessionalClass(db).get(
            meeting_schedualing_register_id=meeting_schedualing_register_id,
            professional_id=professional_id,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al listar"),
                    "data": result.get("data", []),
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data", []),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": str(e),
                "data": [],
            },
        )


@meeting_schedualing_register_professionals.get("/by_meeting/{meeting_schedualing_id}")
def get_by_meeting_schedualing_id(
    meeting_schedualing_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene la lista de profesionales para un meeting_schedualing_register_id (en la ruta se usa meeting_schedualing_id como nombre del parámetro)."""
    try:
        result = MeetingSchedualingRegisterProfessionalClass(db).get(
            meeting_schedualing_register_id=meeting_schedualing_id,
            professional_id=None,
        )
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
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data", []),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": []},
        )


@meeting_schedualing_register_professionals.delete("/by_meeting/{meeting_schedualing_register_id}/professional/{professional_id}")
def delete_by_register_and_professional(
    meeting_schedualing_register_id: int,
    professional_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Quita un profesional de la lista: borrado lógico del registro con ese meeting_schedualing_register_id y professional_id."""
    try:
        result = MeetingSchedualingRegisterProfessionalClass(db).delete_by_register_and_professional(
            meeting_schedualing_register_id=meeting_schedualing_register_id,
            professional_id=professional_id,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Registro eliminado"),
                "data": None,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@meeting_schedualing_register_professionals.put("/by_meeting/{meeting_schedualing_register_id}/sync")
def sync_professionals(
    meeting_schedualing_register_id: int,
    data: SyncMeetingSchedualingRegisterProfessionals,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Sincroniza la lista: envía professional_ids y el backend deja solo esos (borra lógico los que no estén, añade los que falten)."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        professional_ids = payload.get("professional_ids") or []
        result = MeetingSchedualingRegisterProfessionalClass(db).sync_professionals(
            meeting_schedualing_register_id=meeting_schedualing_register_id,
            professional_ids=professional_ids,
        )
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al sincronizar"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Lista actualizada"),
                "data": None,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@meeting_schedualing_register_professionals.get("/{id}")
def get_by_id(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene un registro por id (pk)."""
    try:
        result = MeetingSchedualingRegisterProfessionalClass(db).get_by_id(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": result.get("data"),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e), "data": None},
        )


@meeting_schedualing_register_professionals.post("/store")
def store(
    data: StoreMeetingSchedualingRegisterProfessional,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crea un registro en meeting_schedualing_register_professionals."""
    try:
        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        result = MeetingSchedualingRegisterProfessionalClass(db).store(payload)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": result.get("message", "Error al guardar"),
                    "data": None,
                },
            )
        created = result.get("data")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": result.get("message", "Registro creado"),
                "data": created if created is not None else {"id": result.get("id")},
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


@meeting_schedualing_register_professionals.put("/{id}")
def update(
    id: int,
    data: UpdateMeetingSchedualingRegisterProfessional,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza un registro por id. Enviar en el body al menos un campo: meeting_schedualing_register_id y/o professional_id."""
    try:
        payload = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {k: v for k, v in data.dict().items() if v is not None}
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": "Envíe al menos un campo para actualizar (meeting_schedualing_register_id o professional_id).",
                    "data": None,
                },
            )
        result = MeetingSchedualingRegisterProfessionalClass(db).update(id, payload)
        if result.get("status") == "error":
            msg = result.get("message", "Error")
            not_found = msg == "Registro no encontrado."
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 404 if not_found else 500,
                    "message": msg,
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Registro actualizado"),
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


@meeting_schedualing_register_professionals.delete("/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Borrado lógico: setea deleted_date."""
    try:
        result = MeetingSchedualingRegisterProfessionalClass(db).delete(id)
        if result.get("status") == "error":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": result.get("message", "Registro no encontrado"),
                    "data": None,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": result.get("message", "Registro eliminado"),
                "data": None,
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
