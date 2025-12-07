from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, CourseList, StoreCourse, UpdateCourse
from app.backend.classes.course_class import CourseClass
from app.backend.classes.school_class import SchoolClass
from app.backend.db.models import CourseModel
from app.backend.auth.auth_user import get_current_active_user

courses = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

@courses.post("/")
def index(course: CourseList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener school_id del customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = None
    if customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    # Si el usuario es profesional y tiene course_id en sesión, filtrar solo ese curso
    course_id_filter = None
    if hasattr(session_user, 'course_id') and session_user.course_id:
        course_id_filter = session_user.course_id
        # Obtener el curso usando CourseClass para incluir teaching_name y total_students
        page_value = 0 if course.page is None else course.page
        all_courses = CourseClass(db).get_all(page=page_value, items_per_page=course.per_page, school_id=school_id)
        
        # Filtrar solo el curso del profesional
        if isinstance(all_courses, list):
            course_data = [c for c in all_courses if c.get('id') == course_id_filter]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": "Courses retrieved successfully",
                    "data": course_data
                }
            )
        elif isinstance(all_courses, dict) and 'data' in all_courses:
            course_data = [c for c in all_courses['data'] if c.get('id') == course_id_filter]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": 200,
                    "message": "Courses retrieved successfully",
                    "data": {
                        "total_items": len(course_data),
                        "total_pages": 1 if len(course_data) > 0 else 0,
                        "current_page": all_courses.get('current_page', 1),
                        "items_per_page": course.per_page,
                        "data": course_data
                    }
                }
            )
    
    # Si no hay school_id, devolver array vacío
    if school_id is None:
        message = "Complete courses list retrieved successfully" if course.page is None else "Courses retrieved successfully"
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": message,
                "data": [] if course.page is None else {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": course.page if course.page else 1,
                    "items_per_page": course.per_page,
                    "data": []
                }
            }
        )
    
    page_value = 0 if course.page is None else course.page
    result = CourseClass(db).get_all(page=page_value, items_per_page=course.per_page, course=course.course_name, teaching_id=course.teaching_id, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
        
    message = "Complete courses list retrieved successfully" if course.page is None else "Courses retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@courses.get("/list")
def get_all_list(teaching_id: int = None, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener school_id del usuario en sesión
    school_id = session_user.school_id if session_user else None
    
    # Si no hay school_id, devolver array vacío
    if school_id is None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "Courses list retrieved successfully",
                "data": []
            }
        )
    
    result = CourseClass(db).get_all_list(school_id=school_id, teaching_id=teaching_id)

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
            "message": "Courses list retrieved successfully",
            "data": result
        }
    )

@courses.post("/store")
def store(course: StoreCourse, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    course_inputs = course.dict()
    
    # Obtener school_id del customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = None
    if customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    # Agregar school_id a course_inputs
    course_inputs['school_id'] = school_id
    
    result = CourseClass(db).store(course_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating course"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Course created successfully",
            "data": result
        }
    )

@courses.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CourseClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Course not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Course retrieved successfully",
            "data": result
        }
    )

@courses.put("/update/{id}")
def update(id: int, course: UpdateCourse, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    course_inputs = course.dict(exclude_unset=True)
    
    # Obtener school_id del customer_id del usuario en sesión
    customer_id = session_user.customer_id if session_user else None
    school_id = None
    if customer_id:
        schools_list = SchoolClass(db).get_all(page=0, customer_id=customer_id)
        if isinstance(schools_list, list) and len(schools_list) > 0:
            school_id = schools_list[0].get('id')
    
    # Agregar school_id a course_inputs si no está presente
    if 'school_id' not in course_inputs:
        course_inputs['school_id'] = school_id
    
    result = CourseClass(db).update(id, course_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating course"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Course updated successfully",
            "data": result
        }
    )

@courses.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CourseClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Course not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Course deleted successfully",
            "data": result
        }
    )
