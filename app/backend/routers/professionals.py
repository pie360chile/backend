from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import ProfessionalList, StoreProfessional, UpdateProfessional, UserLogin
from app.backend.classes.professional_class import ProfessionalClass
from app.backend.classes.school_class import SchoolClass
from app.backend.auth.auth_user import get_current_active_user

professionals = APIRouter(
    prefix="/professionals",
    tags=["Professionals"]
)

@professionals.post("/")
def index(professional_list: ProfessionalList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if professional_list.page is None else professional_list.page
    
    # Obtener school_id del customer_id de la sesión
    customer_id = session_user.customer_id if hasattr(session_user, 'customer_id') else None
    school_id = None
    if customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    result = ProfessionalClass(db).get_all(
        page=page_value,
        items_per_page=professional_list.per_page,
        identification_number=professional_list.identification_number,
        names=professional_list.names,
        school_id=school_id
    )
        
    message = "Complete professionals list retrieved successfully" if professional_list.page is None else "Professionals retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@professionals.post("/list")
def list_professionals(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    school_id = session_user.school_id if session_user else None
    result = ProfessionalClass(db).get_all(page=0, school_id=school_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professionals list retrieved successfully",
            "data": result
        }
    )

@professionals.get("/list")
def get_all_list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener school_id del usuario en sesión
    school_id = session_user.school_id if session_user else None
    
    # Si no hay school_id, devolver array vacío
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Professionals list retrieved successfully",
                "data": []
            }
        )
    
    result = ProfessionalClass(db).get_all(page=0, school_id=school_id)

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
            "message": "Professionals list retrieved successfully",
            "data": result
        }
    )

@professionals.post("/totals")
def totals(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    rol_id = session_user.rol_id if session_user else None
    result = ProfessionalClass(db).get_totals(customer_id=customer_id, school_id=school_id, rol_id=rol_id)

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
            "message": "Professionals totals retrieved successfully",
            "data": result
        }
    )

@professionals.post("/store")
def store(professional: StoreProfessional, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    professional_inputs = professional.dict()
    
    # Obtener school_id de la sesión del usuario
    school_id = session_user.school_id if session_user else None
    
    result = ProfessionalClass(db).store(professional_inputs, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating professional"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Professional and user created successfully",
            "data": result
        }
    )

@professionals.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = ProfessionalClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Professional not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional retrieved successfully",
            "data": result
        }
    )

@professionals.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = ProfessionalClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Professional not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional deleted successfully",
            "data": result
        }
    )

@professionals.put("/update/{id}")
def update(id: int, professional: UpdateProfessional, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    professional_inputs = professional.dict(exclude_unset=True)
    
    # Agregar school_id de la sesión si no viene en el input
    if 'school_id' not in professional_inputs:
        professional_inputs['school_id'] = session_user.school_id if session_user else None
    
    result = ProfessionalClass(db).update(id, professional_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating professional"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Professional updated successfully",
            "data": result
        }
    )
