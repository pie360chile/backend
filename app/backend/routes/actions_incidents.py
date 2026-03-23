from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import ActionIncidentList, StoreActionIncident, UpdateActionIncident, UserLogin
from app.backend.classes.action_incident_class import ActionIncidentClass
from app.backend.classes.action_incident_pdf_class import ActionIncidentPDFClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.models import StudentModel, StudentPersonalInfoModel, StudentAcademicInfoModel, SchoolModel, ProfessionalModel, CourseModel, SpecialEducationalNeedModel
from datetime import datetime, date

# Catálogos en duro
STATUS_OPTIONS = {
    1: 'En curso',
    2: 'Pendiente',
    3: 'Por revisar',
    4: 'Resuelto'
}

TYPE_OPTIONS = {
    1: 'Desregulación emocional/conductal',
    2: 'Otra incidencia',
    3: 'Otro'
}

actions_incidents = APIRouter(
    prefix="/actions_incidents",
    tags=["Actions Incidents"]
)

@actions_incidents.post("/")
def index(action_list: ActionIncidentList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if action_list.page is None else action_list.page
    school_id = session_user.school_id if session_user else None
    
    result = ActionIncidentClass(db).get_all(
        page=page_value,
        items_per_page=action_list.per_page,
        student_id=action_list.student_id,
        title=action_list.title,
        school_id=school_id
    )

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Internal server error"),
                "data": None
            }
        )

    message = "Complete actions incidents list retrieved successfully" if action_list.page is None else "Actions incidents retrieved successfully"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@actions_incidents.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = ActionIncidentClass(db).get(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Action incident not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Action incident data retrieved successfully",
            "data": result
        }
    )

@actions_incidents.post("/store")
def store(action: StoreActionIncident, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action_inputs = action.dict()
    
    # Obtener school_id de la sesión
    school_id = session_user.school_id if session_user else None
    
    result = ActionIncidentClass(db).store(action_inputs, school_id=school_id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error saving action incident"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Action incident created successfully",
            "data": result
        }
    )

@actions_incidents.delete("/{id}")
@actions_incidents.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = ActionIncidentClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Action incident not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Action incident deleted successfully",
            "data": result
        }
    )

@actions_incidents.put("/update/{id}")
def update(id: int, action: UpdateActionIncident, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    action_inputs = action.dict(exclude_unset=True)
    
    result = ActionIncidentClass(db).update(id, action_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Action incident not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Action incident updated successfully",
            "data": result
        }
    )

@actions_incidents.get("/pdf/{id}")
def generate_pdf(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Obtener el action incident
    action_result = ActionIncidentClass(db).get(id)
    
    if isinstance(action_result, dict) and action_result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": action_result.get("message", "Action incident not found"),
                "data": None
            }
        )
    
    # Obtener información adicional para el PDF
    student_personal = db.query(StudentPersonalInfoModel).filter(StudentPersonalInfoModel.student_id == action_result['student_id']).first()
    student_academic = db.query(StudentAcademicInfoModel).filter(StudentAcademicInfoModel.student_id == action_result['student_id']).first()
    school = db.query(SchoolModel).filter(SchoolModel.id == action_result['school_id']).first()
    professional = db.query(ProfessionalModel).filter(ProfessionalModel.id == action_result['professional_id']).first() if action_result.get('professional_id') else None
    course = db.query(CourseModel).filter(CourseModel.id == student_academic.course_id).first() if student_academic and student_academic.course_id else None
    nee = db.query(SpecialEducationalNeedModel).filter(SpecialEducationalNeedModel.id == student_academic.special_educational_need_id).first() if student_academic and student_academic.special_educational_need_id else None
    
    # Calcular edad
    age = ""
    if student_personal and student_personal.born_date:
        birth_date = student_personal.born_date
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        age = str(age)
    
    # RUT del estudiante (ya viene formateado de la BD)
    student_rut = student_personal.identification_number if student_personal and student_personal.identification_number else ""
    
    # RUT del profesional (ya viene formateado de la BD)
    professional_rut = professional.identification_number if professional and professional.identification_number else ""
    
    # Formatear fecha
    formatted_date = ""
    if action_result.get('incident_date'):
        incident_date = action_result.get('incident_date')
        if isinstance(incident_date, str):
            incident_date = datetime.strptime(incident_date, '%Y-%m-%d').date()
        formatted_date = incident_date.strftime('%d/%m/%Y')
    
    # Preparar datos para el PDF
    pdf_data = {
        'title': action_result.get('title', ''),
        'school_name': school.school_name if school else '',
        'student_name': f"{student_personal.names} {student_personal.father_lastname} {student_personal.mother_lastname}" if student_personal else '',
        'student_rut': student_rut,
        'birth_date': student_personal.born_date.strftime('%d/%m/%Y') if student_personal and student_personal.born_date else '',
        'age': age,
        'nee': nee.special_educational_needs if nee else '',
        'course_name': course.course_name if course else 'Sin curso',
        'incident_date': formatted_date,
        'incident_time': str(action_result.get('incident_time', '')),
        'action_type_name': TYPE_OPTIONS.get(action_result.get('action_incident_type_id'), ''),
        'status_name': STATUS_OPTIONS.get(action_result.get('status_id'), ''),
        'background': action_result.get('background', ''),
        'conduct': action_result.get('conduct', ''),
        'consequences': action_result.get('consequences', ''),
        'recommendations': action_result.get('recommendations', ''),
        'professional_name': f"{professional.names} {professional.lastnames}" if professional else '',
        'professional_position': 'Asistente Técnico Diferencial',
        'professional_rut': professional_rut,
        'professional_secreduc': professional.identification_number if professional else '',
    }
    
    # Generar PDF
    pdf_generator = ActionIncidentPDFClass()
    pdf_content = pdf_generator.generate_pdf(pdf_data)
    
    # Nombre del archivo
    filename = f"Ficha de registro - {action_result.get('title', 'documento')} - {pdf_data['student_name']}.pdf"
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
