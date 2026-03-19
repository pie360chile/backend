from fastapi import APIRouter, Depends, status, UploadFile, File, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StudentList, StoreStudent, UpdateStudent
from app.backend.classes.student_class import StudentClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.school_class import SchoolClass
from app.backend.db.models import ProfessionalModel, ProfessionalTeachingCourseModel, CourseModel, SchoolModel
from pathlib import Path
from datetime import datetime

students = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@students.get("/by_school_course_with_sen")
def list_by_school_course_with_sen(
    school_id: int = Query(..., description="ID del establecimiento"),
    course_id: int = Query(..., description="ID del curso"),
    page: Optional[int] = Query(0, description="Página (0 = sin paginación)"),
    per_page: Optional[int] = Query(100, description="Registros por página"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista estudiantes con NEE o NEET (tipo 1 o 2), ordenados por nombre de la NEE/NEET y luego por nombre del estudiante."""
    result = StudentClass(db).get_by_school_course_with_sen(
        school_id=school_id,
        course_id=course_id,
        page=page or 0,
        items_per_page=per_page if per_page and per_page > 0 else 100,
    )
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST if "requeridos" in (result.get("message") or "") else status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 400 if "requeridos" in (result.get("message") or "") else 500, "message": result.get("message", "Error"), "data": result.get("data", [])},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result},
    )


@students.get("/list")
def list_students(
    course_id: Optional[int] = Query(None, description="Filtrar por curso (-1 o omitir = no filtrar)"),
    page: Optional[int] = Query(0, description="Página (0-based)"),
    per_page: Optional[int] = Query(20, description="Registros por página"),
    rut: Optional[str] = Query(None, description="Filtrar por RUT"),
    names: Optional[str] = Query(None, description="Filtrar por nombres"),
    identification_number: Optional[str] = Query(None, description="Filtrar por número de identificación"),
    period_year: Optional[int] = Query(None, description="Filtrar por año (ej. 2026)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista estudiantes. Filtro opcional por course_id, rut, names, identification_number, period_year."""
    customer_id = session_user.customer_id if session_user else None
    school_id = session_user.school_id if session_user else None
    if customer_id and not school_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get("id")
    page_value = 0 if page is None else page
    per_page_value = 20 if per_page is None else per_page
    result = StudentClass(db).get_all(
        page=page_value,
        items_per_page=per_page_value,
        school_id=school_id,
        rut=rut,
        names=names,
        identification_number=identification_number,
        course_id=course_id if course_id is not None and course_id != -1 else None,
        period_year=period_year,
    )
    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("message", "Error")
        lower_message = error_message.lower() if isinstance(error_message, str) else ""
        if "no data" in lower_message or "no se encontraron datos" in lower_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": 200, "message": error_message, "data": []},
            )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": error_message, "data": None},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result},
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
        course_id=student_item.course_id,
        period_year=student_item.period_year,
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

@students.get("/counts_by_sen_type_and_pie_years")
def counts_by_sen_type_and_pie_years(
    school_id: Optional[int] = Query(None, description="Filter by school (optional; uses session school if not provided)"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Count of students by course and NEE type, split by years in PIE (one_year / more_than_one_year).
    Returns by_course: each course has by_type and totals.
    """
    customer_id = session_user.customer_id if session_user else None
    school_id_resolved = school_id if school_id is not None else (session_user.school_id if session_user else None)
    if customer_id and not school_id_resolved:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id_resolved = schools_list[0].get("id")
    result = StudentClass(db).get_counts_by_sen_type_and_pie_years(school_id=school_id_resolved)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error fetching counts"),
                "data": None
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Counts by NEE type and years in PIE",
            "data": result
        },
    )


@students.get("/counts_by_sen_type_and_pie_years_by_school")
def counts_by_sen_type_and_pie_years_by_school(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Same as counts_by_sen_type_and_pie_years but grouped by school (colegio).
    Returns by_school: each school has school_id, school_name, by_course (same structure as the other endpoint), total_one_year, total_more_than_one_year.
    Schools are filtered by the session customer_id.
    """
    customer_id = session_user.customer_id if session_user else None
    result = StudentClass(db).get_counts_by_sen_type_and_pie_years_by_school(customer_id=customer_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error fetching counts by school"),
                "data": None
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Counts by NEE type and years in PIE, grouped by school",
            "data": result
        },
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

    # Obtener nombre del curso y nombre del colegio
    student_data = result.get("student_data", {}) if isinstance(result, dict) else {}
    academic_info = student_data.get("academic_info", {}) if student_data else {}
    course_id = academic_info.get("course_id") if academic_info else None
    school_id = student_data.get("school_id") if student_data else None
    
    course_name = None
    school_name = None
    
    # Obtener nombre del curso
    if course_id:
        course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
        if course:
            course_name = course.course_name
    
    # Obtener nombre del colegio
    if school_id:
        school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
        if school:
            school_name = school.school_name
    
    # Agregar course_name y school_name al resultado
    if isinstance(result, dict) and result.get("student_data"):
        if result["student_data"].get("academic_info"):
            result["student_data"]["academic_info"]["course_name"] = course_name
        else:
            result["student_data"]["academic_info"] = {"course_name": course_name}
        result["student_data"]["school_name"] = school_name

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
                           'address', 'region_id', 'commune_id', 'nationality_id', 
                           'native_language', 'proficiency_native_language_id', 
                           'language_usually_used', 'proficiency_language_used_id']
    
    # Campos que van a academic_info (student_academic_data)
    academic_fields = ['special_educational_need_id', 'course_id', 'sip_admission_year', 'diagnostic_date']
    
    for field_key, value in student_inputs.items():
        # Si el campo va a personal_data
        if field_key in personal_data_fields:
            personal_data[field_key] = value
        # Si el campo va a academic_info
        elif field_key in academic_fields:
            academic_info[field_key] = value
        # Campos que van directo a la tabla students
        elif field_key == 'identification_number':
            mapped_inputs['identification_number'] = value
        elif field_key == 'period_year':
            mapped_inputs['period_year'] = value
    
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

@students.post("/photo/{student_id}")
async def upload_photo(
    student_id: int,
    file: UploadFile = File(...),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sube una foto para un estudiante específico.
    Guarda la foto en files/system/students.
    """
    try:
        # Obtener el estudiante usando la clase
        student_service = StudentClass(db)
        student_result = student_service.get(student_id)
        
        if isinstance(student_result, dict) and (student_result.get("error") or student_result.get("status") == "error"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": student_result.get("error") or student_result.get("message", "Estudiante no encontrado"),
                    "data": None
                }
            )
        
        # Obtener la extensión del archivo original
        file_extension = Path(file.filename).suffix.lower() if file.filename else ''
        
        # Validar que sea una imagen
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        if file_extension not in allowed_extensions:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": 400,
                    "message": f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(allowed_extensions)}",
                    "data": None
                }
            )
        
        # Generar fecha y hora en formato YYYYMMDDHHMMSS
        date_hour = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generar nombre del archivo: {student_id}_photo_{date_hour}{extension}
        unique_filename = f"{student_id}_1_1_{date_hour}{file_extension}"
        
        # Crear directorio si no existe
        upload_dir = Path("files/system/students")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / unique_filename
        
        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": 201,
                "message": "Foto subida exitosamente",
                "data": {
                    "student_id": student_id,
                    "filename": unique_filename,
                    "file_path": str(file_path),
                    "file_size": len(content)
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"Error subiendo foto: {str(e)}",
                "data": None
            }
        )
