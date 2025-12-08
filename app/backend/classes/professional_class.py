from datetime import datetime
from app.backend.db.models import ProfessionalModel, UserModel, SchoolModel, ProfessionalTeachingCourseModel, RolModel
from app.backend.auth.auth_user import generate_bcrypt_hash
import json

class ProfessionalClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, identification_number=None, names=None, school_id=None):
        try:
            query = self.db.query(
                ProfessionalModel.id,
                ProfessionalModel.school_id,
                ProfessionalModel.rol_id,
                ProfessionalModel.career_type_id,
                ProfessionalModel.identification_number,
                ProfessionalModel.names,
                ProfessionalModel.lastnames,
                ProfessionalModel.email,
                ProfessionalModel.birth_date,
                ProfessionalModel.address,
                ProfessionalModel.phone,
                ProfessionalModel.added_date,
                ProfessionalModel.updated_date,
                RolModel.rol.label('rol_name')
            ).outerjoin(
                RolModel, ProfessionalModel.rol_id == RolModel.id
            )

            # Filtrar por school_id si se proporciona
            if school_id is not None:
                query = query.filter(ProfessionalModel.school_id == school_id)

            # Aplicar filtros de búsqueda
            if identification_number and str(identification_number).strip():
                query = query.filter(ProfessionalModel.identification_number == identification_number)
            
            if names and names.strip():
                query = query.filter(ProfessionalModel.names.like(f"%{names.strip()}%"))

            query = query.order_by(ProfessionalModel.id.desc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if total_items == 0 or (page < 1 or page > total_pages):
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": professional.id,
                    "school_id": professional.school_id,
                    "rol_id": professional.rol_id,
                    "rol_name": professional.rol_name,
                    "career_type_id": professional.career_type_id,
                    "identification_number": professional.identification_number,
                    "names": professional.names,
                    "lastnames": professional.lastnames,
                    "email": professional.email,
                    "birth_date": professional.birth_date.strftime("%Y-%m-%d") if professional.birth_date else None,
                    "address": professional.address,
                    "phone": professional.phone,
                    "added_date": professional.added_date.strftime("%Y-%m-%d %H:%M:%S") if professional.added_date else None,
                    "updated_date": professional.updated_date.strftime("%Y-%m-%d %H:%M:%S") if professional.updated_date else None
                } for professional in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                if not data:
                    return []

                serialized_data = [{
                    "id": professional.id,
                    "school_id": professional.school_id,
                    "rol_id": professional.rol_id,
                    "rol_name": professional.rol_name,
                    "career_type_id": professional.career_type_id,
                    "identification_number": professional.identification_number,
                    "names": professional.names,
                    "lastnames": professional.lastnames,
                    "email": professional.email,
                    "birth_date": professional.birth_date.strftime("%Y-%m-%d") if professional.birth_date else None,
                    "address": professional.address,
                    "phone": professional.phone,
                    "added_date": professional.added_date.strftime("%Y-%m-%d %H:%M:%S") if professional.added_date else None,
                    "updated_date": professional.updated_date.strftime("%Y-%m-%d %H:%M:%S") if professional.updated_date else None
                } for professional in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == id).first()

            if data_query:
                professional_data = {
                    "id": data_query.id,
                    "school_id": data_query.school_id,
                    "rol_id": data_query.rol_id,
                    "course_id": data_query.course_id,
                    "teaching_id": data_query.teaching_id,
                    "career_type_id": data_query.career_type_id,
                    "identification_number": data_query.identification_number,
                    "names": data_query.names,
                    "lastnames": data_query.lastnames,
                    "email": data_query.email,
                    "birth_date": data_query.birth_date.strftime("%Y-%m-%d") if data_query.birth_date else None,
                    "address": data_query.address,
                    "phone": data_query.phone,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"professional_data": professional_data}

            else:
                return {"error": "No se encontraron datos para el profesional especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, professional_inputs, school_id=None):
        try:
            # Convertir birth_date de string a date
            birth_date_obj = None
            if professional_inputs.get('birth_date'):
                try:
                    birth_date_obj = datetime.strptime(professional_inputs.get('birth_date'), "%Y-%m-%d").date()
                except:
                    pass

            # Obtener los arrays para crear registros en professionals_teachings_courses
            teaching_ids = professional_inputs.get('teaching_id', [])
            course_ids = professional_inputs.get('course_id', [])

            # Crear el profesional
            new_professional = ProfessionalModel(
                school_id=school_id,
                rol_id=professional_inputs.get('rol_id'),
                career_type_id=professional_inputs.get('career_type_id'),
                identification_number=professional_inputs.get('identification_number'),
                names=professional_inputs.get('names'),
                lastnames=professional_inputs.get('lastnames'),
                email=professional_inputs.get('email'),
                birth_date=birth_date_obj,
                address=professional_inputs.get('address'),
                phone=professional_inputs.get('phone'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_professional)
            self.db.flush()  # Obtener el ID del profesional antes de commit

            # Crear el usuario correspondiente
            # Obtener customer_id desde school_id
            customer_id = None
            if school_id:
                school = self.db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
                if school:
                    customer_id = school.customer_id
            
            full_name = f"{professional_inputs.get('names')} {professional_inputs.get('lastnames')}"
            new_user = UserModel(
                customer_id=customer_id,
                school_id=school_id,
                rol_id=professional_inputs.get('rol_id'),
                deleted_status_id=0,
                rut=professional_inputs.get('identification_number'),
                full_name=full_name,
                email=professional_inputs.get('email'),
                phone=professional_inputs.get('phone'),
                hashed_password=generate_bcrypt_hash(professional_inputs.get('password')),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_user)
            self.db.flush()

            # Crear registros en professionals_teachings_courses para cada combinación
            if teaching_ids and course_ids:
                for teaching_id in teaching_ids:
                    for course_id in course_ids:
                        new_ptc = ProfessionalTeachingCourseModel(
                            professional_id=new_professional.id,
                            teaching_id=teaching_id,
                            course_id=course_id,
                            deleted_status_id=0,
                            added_date=datetime.now(),
                            updated_date=datetime.now()
                        )
                        self.db.add(new_ptc)

            self.db.commit()
            self.db.refresh(new_professional)
            self.db.refresh(new_user)

            return {
                "status": "success",
                "message": "Professional and user created successfully",
                "professional_id": new_professional.id,
                "user_id": new_user.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            data = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == id).first()
            if data:
                # Marcar como eliminado en professionals_teachings_courses
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.professional_id == id
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                })
                
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Professional deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, professional_inputs):
        try:
            existing_professional = self.db.query(ProfessionalModel).filter(ProfessionalModel.id == id).one_or_none()

            if not existing_professional:
                return {"status": "error", "message": "No data found"}

            # Guardar valores para actualizar user
            identification_number = professional_inputs.get('identification_number', existing_professional.identification_number)
            names = professional_inputs.get('names', existing_professional.names)
            lastnames = professional_inputs.get('lastnames', existing_professional.lastnames)
            email = professional_inputs.get('email', existing_professional.email)
            phone = professional_inputs.get('phone', existing_professional.phone)
            rol_id = professional_inputs.get('rol_id', existing_professional.rol_id)

            for key, value in professional_inputs.items():
                if value is not None:
                    setattr(existing_professional, key, value)

            existing_professional.updated_date = datetime.now()

            # Actualizar usuario correspondiente
            existing_user = self.db.query(UserModel).filter(
                UserModel.rut == identification_number
            ).first()

            if existing_user:
                existing_user.full_name = f"{names} {lastnames}"
                existing_user.email = email
                existing_user.phone = phone
                existing_user.rol_id = rol_id
                existing_user.school_id = professional_inputs.get('school_id', existing_user.school_id)
                existing_user.updated_date = datetime.now()

            # Actualizar professionals_teachings_courses
            teaching_ids = professional_inputs.get('teaching_id', [])
            course_ids = professional_inputs.get('course_id', [])
            
            # Si se proporcionan teaching_ids y course_ids, actualizar la tabla de relaciones
            if teaching_ids is not None and course_ids is not None:
                # Marcar todos los registros existentes como eliminados
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.professional_id == id,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                }, synchronize_session=False)
                
                # Crear nuevos registros para cada combinación
                if teaching_ids and course_ids:
                    for teaching_id in teaching_ids:
                        for course_id in course_ids:
                            new_ptc = ProfessionalTeachingCourseModel(
                                professional_id=id,
                                teaching_id=teaching_id,
                                course_id=course_id,
                                deleted_status_id=0,
                                added_date=datetime.now(),
                                updated_date=datetime.now()
                            )
                            self.db.add(new_ptc)

            self.db.commit()
            self.db.refresh(existing_professional)

            return {"status": "success", "message": "Professional updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def get_totals(self, customer_id=None, school_id=None, rol_id=None):
        try:
            from app.backend.db.models import SchoolModel
            
            query = self.db.query(ProfessionalModel)
            
            # Si rol_id = 1 (administrador), devolver todos sin filtrar
            # Si es rol_id = 2, filtrar por customer_id
            # Si es cualquier otro rol, filtrar por school_id
            if rol_id == 2 and customer_id:
                query = query.join(SchoolModel, ProfessionalModel.school_id == SchoolModel.id)
                query = query.filter(SchoolModel.customer_id == customer_id)
            elif rol_id not in [1, 2] and school_id:
                query = query.filter(ProfessionalModel.school_id == school_id)
            
            total = query.count()
            
            return {"total": total}

        except Exception as e:
            return {"status": "error", "message": str(e)}

