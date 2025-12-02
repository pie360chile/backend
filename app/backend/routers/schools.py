from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, SchoolList, StoreSchool, UpdateSchool
from app.backend.classes.school_class import SchoolClass
from app.backend.auth.auth_user import get_current_active_user

schools = APIRouter(
    prefix="/schools",
    tags=["Schools"]
)

@schools.post("/")
def index(school_item: SchoolList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if school_item.page is None else school_item.page
    result = SchoolClass(db).get_all(
        page=page_value, 
        items_per_page=school_item.per_page, 
        school_name=school_item.school_name,
        customer_id=school_item.customer_id
    )

    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("message", "Error")
        lower_message = error_message.lower() if isinstance(error_message, str) else ""

        if "no data" in lower_message or "no se encontraron datos" in lower_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": error_message,
                    "data": []
                }
            )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": error_message,
                "data": None
            }
        )

    message = "Complete schools list retrieved successfully" if school_item.page is None else "Schools retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@schools.post("/totals")
def totals(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    rol_id = session_user.rol_id if session_user else None
    result = SchoolClass(db).get_totals(customer_id=customer_id, school_id=school_id, rol_id=rol_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error getting totals"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Schools totals retrieved successfully",
            "data": result
        }
    )

@schools.post("/store")
def store(
    school_item: StoreSchool,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Obtener customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    
    if not customer_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "Customer ID not found in session",
                "data": None
            }
        )
    
    school_inputs = school_item.dict()
    school_inputs['customer_id'] = customer_id
    result = SchoolClass(db).store(school_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating school"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "School created successfully",
            "data": result
        }
    )

@schools.get("/edit")
def edit(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    
    if not customer_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "Customer ID not found in session",
                "data": None
            }
        )
    
    # Obtener escuela directamente por customer_id usando get()
    result = SchoolClass(db).get(customer_id=customer_id)

    # Si no hay escuela, devolver 200 con data null
    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "No school found for this customer",
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "School retrieved successfully",
            "data": result
        }
    )

@schools.put("/update")
def update(
    school_item: UpdateSchool,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Obtener customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    
    if not customer_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "Customer ID not found in session",
                "data": None
            }
        )
    
    # Obtener la escuela del customer para obtener su ID
    existing_school = SchoolClass(db).get(customer_id=customer_id)
    
    if isinstance(existing_school, dict) and (existing_school.get("error") or existing_school.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": "School not found for this customer",
                "data": None
            }
        )
    
    school_id = existing_school.get('school_data', {}).get('id')
    school_inputs = school_item.dict()
    school_inputs['customer_id'] = customer_id
    result = SchoolClass(db).update(school_id, school_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating school"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "School updated successfully",
            "data": result
        }
    )

@schools.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    school_service = SchoolClass(db)
    
    # Obtener customer_id del usuario en sesión para validar que pertenece al customer
    customer_id = session_user.customer_id if session_user else None
    
    if not customer_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "Customer ID not found in session",
                "data": None
            }
        )
    
    # Validar que la escuela pertenece al customer
    existing = school_service.get(customer_id=customer_id)

    if isinstance(existing, dict) and existing.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": existing.get("message", "School not found"),
                "data": None
            }
        )

    if isinstance(existing, dict) and existing.get("error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": existing.get("error"),
                "data": None
            }
        )

    result = school_service.delete(id)
 
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "School not found"),
                "data": None
            }
        )
 
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "School deleted successfully",
            "data": result
        }
    )
