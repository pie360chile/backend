from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StudentList, StoreStudent, UpdateStudent
from app.backend.classes.student_class import StudentClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.school_class import SchoolClass
from app.backend.db.models import ProfessionalModel, ProfessionalTeachingCourseModel

students = APIRouter(
    prefix="/students",
    tags=["Students"]
)

@students.post("/")
def index(student_item: StudentList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if student_item.page is None else student_item.page
    
    # Obtener school_id del customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    
    if customer_id and not school_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    result = StudentClass(db).get_all(
        page=page_value, 
        items_per_page=student_item.per_page,
        school_id=school_id,
        rut=student_item.rut,
        names=student_item.names,
        identification_number=student_item.identification_number,
        course_id=student_item.course_id
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

    message = "Complete students list retrieved successfully" if student_item.page is None else "Students retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@students.post("/totals")
def totals(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    rol_id = session_user.rol_id if session_user else None
    result = StudentClass(db).get_totals(customer_id=customer_id, school_id=school_id, rol_id=rol_id)

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
            "message": "Students totals retrieved successfully",
            "data": result
        }
    )

@students.post("/store")
def store(
    student_item: StoreStudent,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    student_inputs = student_item.dict()
    
    # Obtener school_id del customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = None
    if customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    # Agregar school_id a student_inputs
    student_inputs['school_id'] = school_id
    
    result = StudentClass(db).store(student_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating student"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Student created successfully",
            "data": result
        }
    )

@students.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = StudentClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Student not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Student retrieved successfully",
            "data": result
        }
    )

@students.put("/update/{id}")
def update(
    id: int,
    student_item: UpdateStudent,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    student_inputs = student_item.dict(exclude_unset=True)
    
    # Organizar campos: separar por tablas
    mapped_inputs = {}
    personal_data = {}
    academic_info = {}
    
    # Campos que van a personal_data (student_personal_info)
    personal_data_fields = ['names', 'father_lastname', 'mother_lastname', 'social_name', 
                           'gender_id', 'born_date', 'email', 'identification_number', 'phone', 
                           'address', 'region_id', 'commune_id', 'nationality', 
                           'native_language', 'proficiency_native_language_id', 
                           'language_usually_used', 'proficiency_language_used_id']
    
    # Campos que van a academic_info (student_academic_data)
    academic_fields = ['special_educational_need_id', 'course_id', 'sip_admission_year']
    
    for field_key, value in student_inputs.items():
        # Si el campo va a personal_data
        if field_key in personal_data_fields:
            personal_data[field_key] = value
        # Si el campo va a academic_info
        elif field_key in academic_fields:
            academic_info[field_key] = value
        # Si es identification_number, va directo a la tabla students
        elif field_key == 'identification_number':
            mapped_inputs['identification_number'] = value
    
    # Agregar personal_data si hay campos
    if personal_data:
        mapped_inputs['personal_data'] = personal_data
    
    # Agregar academic_info si hay campos
    if academic_info:
        mapped_inputs['academic_info'] = academic_info
    
    result = StudentClass(db).update(id, mapped_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating student"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Student updated successfully",
            "data": result
        }
    )

@students.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    student_service = StudentClass(db)
    existing = student_service.get(id)

    if isinstance(existing, dict) and existing.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": existing.get("message", "Student not found"),
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

    result = student_service.delete(id)
 
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Student not found"),
                "data": None
            }
        )
 
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Student deleted successfully",
            "data": result
        }
    )
