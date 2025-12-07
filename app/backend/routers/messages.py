from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import MessageList, StoreMessage, UpdateMessage, UserLogin
from app.backend.classes.message_class import MessageClass
from app.backend.auth.auth_user import get_current_active_user

messages = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

@messages.post("/")
def index(message_list: MessageList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if message_list.page is None else message_list.page
    customer_id = session_user.customer_id if session_user else None
    rol_id = session_user.rol_id if session_user else None
    result = MessageClass(db).get_all(page=page_value, items_per_page=message_list.per_page, subject=message_list.subject, message_type_id=message_list.message_type_id, customer_id=customer_id, rol_id=rol_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Internal server error"),
                "data": None
            }
        )

    message = "Complete messages list retrieved successfully" if message_list.page is None else "Messages retrieved successfully"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@messages.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = MessageClass(db).get(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Message not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Message data retrieved successfully",
            "data": result
        }
    )

@messages.post("/store")
def store(message: StoreMessage, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    message_inputs = message.dict()
    
    # Agregar customer_id de la sesión
    customer_id = session_user.customer_id if session_user else None
    message_inputs['customer_id'] = customer_id
    
    # Establecer response_id y message_response_id según el rol
    if session_user.rol_id == 2:
        message_inputs['response_id'] = 0
        message_inputs['message_response_id'] = 0
    elif session_user.rol_id == 1:
        message_inputs['response_id'] = 1
        # message_response_id debe venir en el request cuando es rol 1 (admin respondiendo)
        # Si no viene, se establece en 0
        if 'message_response_id' not in message_inputs or message_inputs['message_response_id'] is None:
            message_inputs['message_response_id'] = 0
    
    result = MessageClass(db).store(message_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error saving message"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Message created successfully",
            "data": result
        }
    )

@messages.post("/reply")
def reply(message: StoreMessage, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    message_inputs = message.dict()
    
    # Agregar customer_id de la sesión
    customer_id = session_user.customer_id if session_user else None
    message_inputs['customer_id'] = customer_id
    
    # Para reply, response_id siempre es 1 (es una respuesta del admin)
    message_inputs['response_id'] = 1
    
    # message_response_id debe venir en el request (ID del mensaje al que se está respondiendo)
    if 'message_response_id' not in message_inputs or message_inputs['message_response_id'] is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "message_response_id is required for replies",
                "data": None
            }
        )
    
    result = MessageClass(db).store(message_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error saving reply"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Reply created successfully",
            "data": result
        }
    )

@messages.delete("/{id}")
@messages.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = MessageClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Message not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Message deleted successfully",
            "data": result
        }
    )

@messages.put("/update/{id}")
def update(id: int, message: UpdateMessage, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    message_inputs = message.dict(exclude_unset=True)
    
    result = MessageClass(db).update(id, message_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Message not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Message updated successfully",
            "data": result
        }
    )
