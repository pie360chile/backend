from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import EventList, StoreEvent, UpdateEvent, UserLogin
from app.backend.classes.event_class import EventClass
from app.backend.auth.auth_user import get_current_active_user

events = APIRouter(
    prefix="/events",
    tags=["Events"]
)

@events.post("/")
def index(event_list: EventList = EventList(), session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Si page es None, usar 0 para obtener todos sin paginación
    page = event_list.page if event_list.page is not None else 0
    per_page = event_list.per_page if event_list.per_page else 10
    result = EventClass(db).get_all(page, per_page)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Events retrieved successfully",
            "data": result
        }
    )

@events.get("/list")
def list_events_get(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = EventClass(db).get_all(page=0, items_per_page=None)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error retrieving events"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Events list retrieved successfully",
            "data": result
        }
    )

@events.get("/all")
def get_all_events_by_month(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Obtiene todos los eventos agrupados por mes.
    Retorna un objeto donde cada clave es 'YYYY-MM' y contiene una lista de eventos de ese mes.
    """
    result = EventClass(db).get_all_by_month()

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error retrieving events by month"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Events retrieved successfully grouped by month",
            "data": result
        }
    )

@events.post("/store")
def store(event: StoreEvent, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    event_inputs = event.dict()
    result = EventClass(db).store(event_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating event"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Event created successfully",
            "data": {"id": result.get("id")}
        }
    )

@events.get("/{id}")
def get(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = EventClass(db).get(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Event not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Event retrieved successfully",
            "data": result
        }
    )

@events.put("/{id}")
def update(id: int, event: UpdateEvent, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    event_inputs = event.dict(exclude_unset=True)
    result = EventClass(db).update(id, event_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error updating event"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Event updated successfully",
            "data": {"id": result.get("id")}
        }
    )

@events.delete("/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = EventClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error deleting event"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Event deleted successfully",
            "data": None
        }
    )
