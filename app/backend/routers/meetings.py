from fastapi import APIRouter, Body, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.meeting_class import MeetingClass
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.auth.auth_user import get_current_user
from app.backend.schemas import MeetingList, StoreMeeting, UpdateMeeting
from typing import Annotated

meetings = APIRouter(
    prefix="/meetings",
    tags=["Meetings"]
)

# Listado de reuniones
@meetings.post("/")
async def get_meetings(
    meeting_list: MeetingList = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Obtener reuniones
        meeting_class = MeetingClass(db)
        meetings = meeting_class.get_all(
            page=meeting_list.page,
            items_per_page=meeting_list.per_page,
            schedule_id=meeting_list.schedule_id,
            names=meeting_list.names
        )

        return meetings

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Obtener una reunión
@meetings.get("/edit/{meeting_id}")
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Obtener reunión
        meeting_class = MeetingClass(db)
        meeting = meeting_class.get(meeting_id)

        return meeting

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Crear reunión
@meetings.post("/store")
async def store_meeting(
    store_meeting: StoreMeeting = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Crear reunión
        meeting_class = MeetingClass(db)
        meeting_data = {
            "schedule_id": store_meeting.schedule_id,
            "names": store_meeting.names,
            "lastnames": store_meeting.lastnames,
            "email": store_meeting.email,
            "celphone": store_meeting.celphone,
            "reason": store_meeting.reason
        }

        result = meeting_class.store(meeting_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Actualizar reunión
@meetings.put("/update/{meeting_id}")
async def update_meeting(
    meeting_id: int,
    update_meeting: UpdateMeeting = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Actualizar reunión
        meeting_class = MeetingClass(db)
        meeting_data = {}

        if update_meeting.schedule_id is not None:
            meeting_data["schedule_id"] = update_meeting.schedule_id
        if update_meeting.names is not None:
            meeting_data["names"] = update_meeting.names
        if update_meeting.lastnames is not None:
            meeting_data["lastnames"] = update_meeting.lastnames
        if update_meeting.email is not None:
            meeting_data["email"] = update_meeting.email
        if update_meeting.celphone is not None:
            meeting_data["celphone"] = update_meeting.celphone
        if update_meeting.reason is not None:
            meeting_data["reason"] = update_meeting.reason

        result = meeting_class.update(meeting_id, meeting_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Eliminar reunión
@meetings.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Eliminar reunión
        meeting_class = MeetingClass(db)
        result = meeting_class.delete(meeting_id)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
