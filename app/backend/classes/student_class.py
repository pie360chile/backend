from datetime import datetime
from app.backend.db.models import StudentModel, StudentAcademicInfoModel, StudentPersonalInfoModel
from sqlalchemy.orm import aliased


def _date_str(v, fmt="%Y-%m-%d %H:%M:%S"):
    """Convierte fecha/datetime a string; si ya es str lo devuelve tal cual."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "strftime"):
        return v.strftime(fmt)
    return str(v)


class StudentClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_id=None, rut=None, names=None, identification_number=None, course_id=None):
        try:
            query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.sip_admission_year,
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).outerjoin(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(StudentModel.deleted_status_id == 0)

            # Filtrar por school_id solo si NO se proporciona course_id
            # Si hay course_id, el profesional debe ver todos los estudiantes de ese curso sin importar la escuela
            if school_id and not course_id:
                query = query.filter(StudentModel.school_id == school_id)

            # Aplicar filtros de búsqueda
            if rut and rut.strip():
                query = query.filter(StudentModel.identification_number.like(f"%{rut.strip()}%"))
            
            if names and names.strip():
                query = query.filter(StudentPersonalInfoModel.names.like(f"%{names.strip()}%"))
            
            if identification_number and identification_number.strip():
                query = query.filter(StudentPersonalInfoModel.identification_number.like(f"%{identification_number.strip()}%"))
            
            if course_id:
                query = query.filter(StudentAcademicInfoModel.course_id == course_id)

            query = query.order_by(StudentModel.id.desc())

            if page > 0:
                if page < 1:
                    page = 1

                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0

                if total_items == 0 or total_pages == 0 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": student.id,
                    "deleted_status_id": student.deleted_status_id,
                    "school_id": student.school_id,
                    "identification_number": student.student_identification_number,
                    "added_date": student.added_date.strftime("%Y-%m-%d %H:%M:%S") if student.added_date else None,
                    "updated_date": student.updated_date.strftime("%Y-%m-%d %H:%M:%S") if student.updated_date else None,
                    "academic_info": {
                        "id": student.academic_id,
                        "special_educational_need_id": student.special_educational_need_id,
                        "course_id": student.course_id,
                        "sip_admission_year": student.sip_admission_year
                    } if student.academic_id else None,
                    "personal_data": {
                        "id": student.personal_id,
                        "region_id": student.region_id,
                        "commune_id": student.commune_id,
                        "gender_id": student.gender_id,
                        "proficiency_native_language_id": student.proficiency_native_language_id,
                        "proficiency_language_used_id": student.proficiency_language_used_id,
                        "identification_number": student.identification_number,
                        "names": student.names,
                        "father_lastname": student.father_lastname,
                        "mother_lastname": student.mother_lastname,
                        "social_name": student.social_name,
                        "born_date": student.born_date,
                        "nationality": student.nationality,
                        "address": student.address,
                        "phone": student.phone,
                        "email": student.email,
                        "native_language": student.native_language,
                        "language_usually_used": student.language_usually_used
                    } if student.personal_id else None
                } for student in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": student.id,
                    "deleted_status_id": student.deleted_status_id,
                    "school_id": student.school_id,
                    "identification_number": student.student_identification_number,
                    "added_date": student.added_date.strftime("%Y-%m-%d %H:%M:%S") if student.added_date else None,
                    "updated_date": student.updated_date.strftime("%Y-%m-%d %H:%M:%S") if student.updated_date else None,
                    "academic_info": {
                        "id": student.academic_id,
                        "special_educational_need_id": student.special_educational_need_id,
                        "course_id": student.course_id,
                        "sip_admission_year": student.sip_admission_year
                    } if student.academic_id else None,
                    "personal_data": {
                        "id": student.personal_id,
                        "region_id": student.region_id,
                        "commune_id": student.commune_id,
                        "gender_id": student.gender_id,
                        "proficiency_native_language_id": student.proficiency_native_language_id,
                        "proficiency_language_used_id": student.proficiency_language_used_id,
                        "identification_number": student.identification_number,
                        "names": student.names,
                        "father_lastname": student.father_lastname,
                        "mother_lastname": student.mother_lastname,
                        "social_name": student.social_name,
                        "born_date": student.born_date,
                        "nationality": student.nationality,
                        "address": student.address,
                        "phone": student.phone,
                        "email": student.email,
                        "native_language": student.native_language,
                        "language_usually_used": student.language_usually_used
                    } if student.personal_id else None
                } for student in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_school_course_with_sen(self, school_id, course_id, page=0, items_per_page=100):
        """Lista estudiantes filtrados por school_id, course_id y con special_educational_need_id no nulo."""
        try:
            if not school_id or not course_id:
                return {"status": "error", "message": "school_id y course_id son requeridos.", "data": []}
            query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.sip_admission_year,
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).join(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(
                StudentModel.deleted_status_id == 0,
                StudentModel.school_id == school_id,
                StudentAcademicInfoModel.course_id == course_id,
                StudentAcademicInfoModel.special_educational_need_id.isnot(None)
            )
            query = query.order_by(StudentModel.id.desc())
            if page > 0 and items_per_page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0
                if page < 1 or page > max(1, total_pages):
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages or 1,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }
                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
            else:
                data = query.all()
                total_items = len(data)
                total_pages = 1
            serialized_data = [{
                "id": student.id,
                "deleted_status_id": student.deleted_status_id,
                "school_id": student.school_id,
                "identification_number": student.student_identification_number,
                "added_date": _date_str(student.added_date),
                "updated_date": _date_str(student.updated_date),
                "academic_info": {
                    "id": student.academic_id,
                    "special_educational_need_id": student.special_educational_need_id,
                    "course_id": student.course_id,
                    "sip_admission_year": student.sip_admission_year
                } if student.academic_id else None,
                "personal_data": {
                    "id": student.personal_id,
                    "region_id": student.region_id,
                    "commune_id": student.commune_id,
                    "gender_id": student.gender_id,
                    "proficiency_native_language_id": student.proficiency_native_language_id,
                    "proficiency_language_used_id": student.proficiency_language_used_id,
                    "identification_number": student.identification_number,
                    "names": student.names,
                    "father_lastname": student.father_lastname,
                    "mother_lastname": student.mother_lastname,
                    "social_name": student.social_name,
                    "born_date": _date_str(student.born_date, "%Y-%m-%d"),
                    "nationality": student.nationality,
                    "address": student.address,
                    "phone": student.phone,
                    "email": student.email,
                    "native_language": student.native_language,
                    "language_usually_used": student.language_usually_used
                } if student.personal_id else None
            } for student in data]
            if page > 0 and items_per_page > 0:
                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }
            return serialized_data
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id):
        try:
            data_query = self.db.query(
                StudentModel.id,
                StudentModel.deleted_status_id,
                StudentModel.school_id,
                StudentModel.identification_number.label('student_identification_number'),
                StudentModel.added_date,
                StudentModel.updated_date,
                StudentAcademicInfoModel.id.label('academic_id'),
                StudentAcademicInfoModel.special_educational_need_id,
                StudentAcademicInfoModel.course_id,
                StudentAcademicInfoModel.sip_admission_year,
                StudentPersonalInfoModel.id.label('personal_id'),
                StudentPersonalInfoModel.region_id,
                StudentPersonalInfoModel.commune_id,
                StudentPersonalInfoModel.gender_id,
                StudentPersonalInfoModel.proficiency_native_language_id,
                StudentPersonalInfoModel.proficiency_language_used_id,
                StudentPersonalInfoModel.identification_number,
                StudentPersonalInfoModel.names,
                StudentPersonalInfoModel.father_lastname,
                StudentPersonalInfoModel.mother_lastname,
                StudentPersonalInfoModel.social_name,
                StudentPersonalInfoModel.born_date,
                StudentPersonalInfoModel.nationality,
                StudentPersonalInfoModel.address,
                StudentPersonalInfoModel.phone,
                StudentPersonalInfoModel.email,
                StudentPersonalInfoModel.native_language,
                StudentPersonalInfoModel.language_usually_used
            ).outerjoin(
                StudentAcademicInfoModel,
                StudentModel.id == StudentAcademicInfoModel.student_id
            ).outerjoin(
                StudentPersonalInfoModel,
                StudentModel.id == StudentPersonalInfoModel.student_id
            ).filter(
                StudentModel.id == id,
                StudentModel.deleted_status_id == 0
            ).first()

            if data_query:
                student_data = {
                    "id": data_query.id,
                    "deleted_status_id": data_query.deleted_status_id,
                    "school_id": data_query.school_id,
                    "identification_number": data_query.student_identification_number,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None,
                    "academic_info": {
                        "id": data_query.academic_id,
                        "special_educational_need_id": data_query.special_educational_need_id,
                        "course_id": data_query.course_id,
                        "sip_admission_year": data_query.sip_admission_year
                    } if data_query.academic_id else None,
                    "personal_data": {
                        "id": data_query.personal_id,
                        "region_id": data_query.region_id,
                        "commune_id": data_query.commune_id,
                        "gender_id": data_query.gender_id,
                        "proficiency_native_language_id": data_query.proficiency_native_language_id,
                        "proficiency_language_used_id": data_query.proficiency_language_used_id,
                        "identification_number": data_query.identification_number,
                        "names": data_query.names,
                        "father_lastname": data_query.father_lastname,
                        "mother_lastname": data_query.mother_lastname,
                        "social_name": data_query.social_name,
                        "born_date": data_query.born_date,
                        "nationality": data_query.nationality,
                        "address": data_query.address,
                        "phone": data_query.phone,
                        "email": data_query.email,
                        "native_language": data_query.native_language,
                        "language_usually_used": data_query.language_usually_used
                    } if data_query.personal_id else None
                }

                return {"student_data": student_data}

            else:
                return {"error": "No se encontraron datos para el estudiante especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, student_inputs):
        try:
            # Crear el estudiante principal
            new_student = StudentModel(
                deleted_status_id=0,
                school_id=student_inputs.get('school_id'),
                identification_number=student_inputs.get('identification_number'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_student)
            self.db.commit()
            self.db.refresh(new_student)

            # Crear información personal con los campos enviados
            new_personal = StudentPersonalInfoModel(
                student_id=new_student.id,
                identification_number=student_inputs.get('identification_number'),
                names=student_inputs.get('names'),
                father_lastname=student_inputs.get('father_lastname'),
                mother_lastname=student_inputs.get('mother_lastname')
            )
            self.db.add(new_personal)

            # Crear información académica si viene course_id
            course_id = student_inputs.get('course_id')
            if course_id:
                new_academic = StudentAcademicInfoModel(
                    student_id=new_student.id,
                    course_id=course_id,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_academic)

            self.db.commit()

            return {
                "status": "success",
                "message": "Student created successfully",
                "student_id": new_student.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(StudentModel).filter(StudentModel.id == id).first()
            if data and data.deleted_status_id == 0:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "Student deleted successfully"}
            elif data:
                return {"status": "error", "message": "No data found"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, student_inputs):
        try:
            existing_student = self.db.query(StudentModel).filter(
                StudentModel.id == id
            ).one_or_none()

            if not existing_student:
                return {"status": "error", "message": "No data found"}

            # Actualizar school_id si está presente
            if 'school_id' in student_inputs and student_inputs['school_id']:
                existing_student.school_id = student_inputs['school_id']

            # Actualizar identification_number si está presente
            if 'identification_number' in student_inputs and student_inputs['identification_number']:
                existing_student.identification_number = student_inputs['identification_number']

            existing_student.updated_date = datetime.now()

            # Actualizar información académica
            if 'academic_info' in student_inputs and student_inputs['academic_info']:
                academic_info = student_inputs['academic_info']
                existing_academic = self.db.query(StudentAcademicInfoModel).filter(
                    StudentAcademicInfoModel.student_id == id
                ).first()

                if existing_academic:
                    # Actualizar registro existente
                    if 'special_educational_need_id' in academic_info:
                        existing_academic.special_educational_need_id = academic_info['special_educational_need_id']
                    if 'course_id' in academic_info:
                        existing_academic.course_id = academic_info['course_id']
                    if 'sip_admission_year' in academic_info:
                        existing_academic.sip_admission_year = academic_info['sip_admission_year']
                    existing_academic.updated_date = datetime.now()
                else:
                    # Crear nuevo registro
                    new_academic = StudentAcademicInfoModel(
                        student_id=id,
                        special_educational_need_id=academic_info.get('special_educational_need_id'),
                        course_id=academic_info.get('course_id'),
                        sip_admission_year=academic_info.get('sip_admission_year'),
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    self.db.add(new_academic)

            # Actualizar información personal
            if 'personal_data' in student_inputs and student_inputs['personal_data']:
                personal_data = student_inputs['personal_data']
                
                existing_personal = self.db.query(StudentPersonalInfoModel).filter(
                    StudentPersonalInfoModel.student_id == id
                ).first()

                if existing_personal:
                    # Actualizar registro existente
                    if 'region_id' in personal_data:
                        existing_personal.region_id = personal_data['region_id']
                    if 'commune_id' in personal_data:
                        existing_personal.commune_id = personal_data['commune_id']
                    if 'gender_id' in personal_data:
                        existing_personal.gender_id = personal_data['gender_id']
                    if 'proficiency_native_language_id' in personal_data:
                        existing_personal.proficiency_native_language_id = personal_data['proficiency_native_language_id']
                    if 'proficiency_language_used_id' in personal_data:
                        existing_personal.proficiency_language_used_id = personal_data['proficiency_language_used_id']
                    if 'identification_number' in personal_data:
                        existing_personal.identification_number = personal_data['identification_number']
                    if 'names' in personal_data:
                        existing_personal.names = personal_data['names']
                    if 'father_lastname' in personal_data:
                        existing_personal.father_lastname = personal_data['father_lastname']
                    if 'mother_lastname' in personal_data:
                        existing_personal.mother_lastname = personal_data['mother_lastname']
                    if 'social_name' in personal_data:
                        existing_personal.social_name = personal_data['social_name']
                    if 'born_date' in personal_data:
                        existing_personal.born_date = personal_data['born_date']
                    if 'nationality' in personal_data:
                        existing_personal.nationality = personal_data['nationality']
                    if 'address' in personal_data:
                        existing_personal.address = personal_data['address']
                    if 'phone' in personal_data:
                        existing_personal.phone = personal_data['phone']
                    if 'email' in personal_data:
                        existing_personal.email = personal_data['email']
                    if 'native_language' in personal_data:
                        existing_personal.native_language = personal_data['native_language']
                    if 'language_usually_used' in personal_data:
                        existing_personal.language_usually_used = personal_data['language_usually_used']
                else:
                    # Crear nuevo registro
                    new_personal = StudentPersonalInfoModel(
                        student_id=id,
                        region_id=personal_data.get('region_id'),
                        commune_id=personal_data.get('commune_id'),
                        gender_id=personal_data.get('gender_id'),
                        proficiency_native_language_id=personal_data.get('proficiency_native_language_id'),
                        proficiency_language_used_id=personal_data.get('proficiency_language_used_id'),
                        identification_number=personal_data.get('identification_number'),
                        names=personal_data.get('names'),
                        father_lastname=personal_data.get('father_lastname'),
                        mother_lastname=personal_data.get('mother_lastname'),
                        social_name=personal_data.get('social_name'),
                        born_date=personal_data.get('born_date'),
                        nationality=personal_data.get('nationality'),
                        address=personal_data.get('address'),
                        phone=personal_data.get('phone'),
                        email=personal_data.get('email'),
                        native_language=personal_data.get('native_language'),
                        language_usually_used=personal_data.get('language_usually_used')
                    )
                    self.db.add(new_personal)

            self.db.commit()
            self.db.refresh(existing_student)

            return {"status": "success", "message": "Student updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def get_totals(self, customer_id=None, school_id=None, rol_id=None):
        try:
            from app.backend.db.models import SchoolModel
            
            query = self.db.query(StudentModel).filter(StudentModel.deleted_status_id == 0)
            
            # Si rol_id = 1 (administrador), devolver todos sin filtrar
            # Si es rol_id = 2, filtrar por customer_id
            # Si es cualquier otro rol, filtrar por school_id
            if rol_id == 2 and customer_id:
                query = query.join(SchoolModel, StudentModel.school_id == SchoolModel.id)
                query = query.filter(SchoolModel.customer_id == customer_id)
            elif rol_id not in [1, 2] and school_id:
                query = query.filter(StudentModel.school_id == school_id)
            
            total = query.count()
            
            return {"total": total}

        except Exception as e:
            return {"status": "error", "message": str(e)}
