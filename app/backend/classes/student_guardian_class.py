from datetime import datetime
from app.backend.db.models import StudentGuardianModel

class StudentGuardianClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, student_id=None, names=None):
        try:
            query = self.db.query(StudentGuardianModel)

            # Filtrar por student_id si se proporciona
            if student_id:
                query = query.filter(StudentGuardianModel.student_id == student_id)

            # Aplicar filtro de búsqueda por nombres
            if names and names.strip():
                query = query.filter(StudentGuardianModel.names.like(f"%{names.strip()}%"))

            query = query.order_by(StudentGuardianModel.id.desc())

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
                    "id": guardian.id,
                    "student_id": guardian.student_id,
                    "family_member_id": guardian.family_member_id,
                    "gender_id": guardian.gender_id,
                    "identification_number": guardian.identification_number,
                    "names": guardian.names,
                    "father_lastname": guardian.father_lastname,
                    "mother_lastname": guardian.mother_lastname,
                    "born_date": guardian.born_date.strftime("%Y-%m-%d") if guardian.born_date else None,
                    "email": guardian.email,
                    "celphone": guardian.celphone,
                    "city": guardian.city,
                    "added_date": guardian.added_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.added_date else None,
                    "updated_date": guardian.updated_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.updated_date else None
                } for guardian in data]

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
                    "id": guardian.id,
                    "student_id": guardian.student_id,
                    "family_member_id": guardian.family_member_id,
                    "gender_id": guardian.gender_id,
                    "identification_number": guardian.identification_number,
                    "names": guardian.names,
                    "father_lastname": guardian.father_lastname,
                    "mother_lastname": guardian.mother_lastname,
                    "born_date": guardian.born_date.strftime("%Y-%m-%d") if guardian.born_date else None,
                    "email": guardian.email,
                    "celphone": guardian.celphone,
                    "city": guardian.city,
                    "added_date": guardian.added_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.added_date else None,
                    "updated_date": guardian.updated_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.updated_date else None
                } for guardian in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, student_id):
        try:
            guardian = self.db.query(StudentGuardianModel).filter(
                StudentGuardianModel.student_id == student_id
            ).first()

            if guardian:
                return {
                    "id": guardian.id,
                    "student_id": guardian.student_id,
                    "family_member_id": guardian.family_member_id,
                    "gender_id": guardian.gender_id,
                    "identification_number": guardian.identification_number,
                    "names": guardian.names,
                    "father_lastname": guardian.father_lastname,
                    "mother_lastname": guardian.mother_lastname,
                    "born_date": guardian.born_date.strftime("%Y-%m-%d") if guardian.born_date else None,
                    "email": guardian.email,
                    "celphone": guardian.celphone,
                    "city": guardian.city,
                    "added_date": guardian.added_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.added_date else None,
                    "updated_date": guardian.updated_date.strftime("%Y-%m-%d %H:%M:%S") if guardian.updated_date else None
                }
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            error_message = str(e)
            return {"error": error_message}

    def store(self, guardian_inputs):
        try:
            student_id = guardian_inputs.get('student_id')
            
            # Buscar si ya existe un guardian para este estudiante
            existing_guardian = self.db.query(StudentGuardianModel).filter(
                StudentGuardianModel.student_id == student_id
            ).first()
            
            # Convertir born_date de string a date si viene como string
            born_date = None
            if 'born_date' in guardian_inputs and guardian_inputs['born_date']:
                if isinstance(guardian_inputs['born_date'], str):
                    born_date = datetime.strptime(guardian_inputs['born_date'], '%Y-%m-%d').date()
                else:
                    born_date = guardian_inputs['born_date']

            if existing_guardian:
                # Actualizar el guardian existente - solo campos que no estén vacíos
                if 'family_member_id' in guardian_inputs and guardian_inputs['family_member_id'] is not None:
                    existing_guardian.family_member_id = guardian_inputs['family_member_id']
                if 'gender_id' in guardian_inputs and guardian_inputs['gender_id'] is not None:
                    existing_guardian.gender_id = guardian_inputs['gender_id']
                if 'identification_number' in guardian_inputs and guardian_inputs['identification_number']:
                    existing_guardian.identification_number = guardian_inputs['identification_number']
                if 'names' in guardian_inputs and guardian_inputs['names']:
                    existing_guardian.names = guardian_inputs['names']
                if 'father_lastname' in guardian_inputs and guardian_inputs['father_lastname']:
                    existing_guardian.father_lastname = guardian_inputs['father_lastname']
                if 'mother_lastname' in guardian_inputs and guardian_inputs['mother_lastname']:
                    existing_guardian.mother_lastname = guardian_inputs['mother_lastname']
                if 'born_date' in guardian_inputs and guardian_inputs['born_date']:
                    existing_guardian.born_date = born_date
                if 'email' in guardian_inputs and guardian_inputs['email']:
                    existing_guardian.email = guardian_inputs['email']
                if 'celphone' in guardian_inputs and guardian_inputs['celphone']:
                    existing_guardian.celphone = guardian_inputs['celphone']
                if 'city' in guardian_inputs and guardian_inputs['city']:
                    existing_guardian.city = guardian_inputs['city']
                existing_guardian.updated_date = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing_guardian)
                
                return {
                    "status": "success",
                    "message": "Guardian updated successfully",
                    "guardian_id": existing_guardian.id
                }
            else:
                # Crear nuevo guardian
                new_guardian = StudentGuardianModel(
                    student_id=student_id,
                    family_member_id=guardian_inputs.get('family_member_id'),
                    gender_id=guardian_inputs.get('gender_id'),
                    identification_number=guardian_inputs.get('identification_number'),
                    names=guardian_inputs.get('names'),
                    father_lastname=guardian_inputs.get('father_lastname'),
                    mother_lastname=guardian_inputs.get('mother_lastname'),
                    born_date=born_date,
                    email=guardian_inputs.get('email'),
                    celphone=guardian_inputs.get('celphone'),
                    city=guardian_inputs.get('city'),
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )

                self.db.add(new_guardian)
                self.db.commit()
                self.db.refresh(new_guardian)

                return {
                    "status": "success",
                    "message": "Guardian created successfully",
                    "guardian_id": new_guardian.id
                }

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, guardian_inputs):
        try:
            existing_guardian = self.db.query(StudentGuardianModel).filter(
                StudentGuardianModel.id == id
            ).one_or_none()

            if not existing_guardian:
                return {"status": "error", "message": "No data found"}

            # Actualizar campos si están presentes
            if 'student_id' in guardian_inputs:
                existing_guardian.student_id = guardian_inputs['student_id']
            if 'family_member_id' in guardian_inputs:
                existing_guardian.family_member_id = guardian_inputs['family_member_id']
            if 'gender_id' in guardian_inputs:
                existing_guardian.gender_id = guardian_inputs['gender_id']
            if 'identification_number' in guardian_inputs:
                existing_guardian.identification_number = guardian_inputs['identification_number']
            if 'names' in guardian_inputs:
                existing_guardian.names = guardian_inputs['names']
            if 'father_lastname' in guardian_inputs:
                existing_guardian.father_lastname = guardian_inputs['father_lastname']
            if 'mother_lastname' in guardian_inputs:
                existing_guardian.mother_lastname = guardian_inputs['mother_lastname']
            if 'born_date' in guardian_inputs and guardian_inputs['born_date']:
                if isinstance(guardian_inputs['born_date'], str):
                    existing_guardian.born_date = datetime.strptime(guardian_inputs['born_date'], '%Y-%m-%d').date()
                else:
                    existing_guardian.born_date = guardian_inputs['born_date']
            if 'email' in guardian_inputs:
                existing_guardian.email = guardian_inputs['email']
            if 'celphone' in guardian_inputs:
                existing_guardian.celphone = guardian_inputs['celphone']
            if 'city' in guardian_inputs:
                existing_guardian.city = guardian_inputs['city']

            existing_guardian.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_guardian)

            return {"status": "success", "message": "Guardian updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            guardian = self.db.query(StudentGuardianModel).filter(
                StudentGuardianModel.id == id
            ).first()

            if guardian:
                self.db.delete(guardian)
                self.db.commit()
                return {"status": "success", "message": "Guardian deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_totals(self, customer_id=None, school_id=None, rol_id=None):
        try:
            from app.backend.db.models import StudentModel, SchoolModel
            
            query = self.db.query(StudentGuardianModel)
            
            # Si rol_id = 1 (administrador), devolver todos sin filtrar
            # Si es rol_id = 2, filtrar por customer_id
            # Si es cualquier otro rol, filtrar por school_id
            if rol_id == 2 and customer_id:
                query = query.join(StudentModel, StudentGuardianModel.student_id == StudentModel.id)
                query = query.join(SchoolModel, StudentModel.school_id == SchoolModel.id)
                query = query.filter(StudentModel.deleted_status_id == 0)
                query = query.filter(SchoolModel.customer_id == customer_id)
            elif rol_id not in [1, 2] and school_id:
                query = query.join(StudentModel, StudentGuardianModel.student_id == StudentModel.id)
                query = query.filter(StudentModel.deleted_status_id == 0)
                query = query.filter(StudentModel.school_id == school_id)
            
            total = query.count()
            
            return {"total": total}

        except Exception as e:
            return {"status": "error", "message": str(e)}

