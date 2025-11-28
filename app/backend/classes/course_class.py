from datetime import datetime
from sqlalchemy import func
from app.backend.db.models import CourseModel, TeachingModel, ProfessionalTeachingCourseModel, StudentModel, StudentAcademicInfoModel

class CourseClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, school_id=None, course=None, teaching_id=None):
        try:
            query = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name,
                func.count(StudentModel.id).label('total_students')
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            ).outerjoin(
                StudentAcademicInfoModel, CourseModel.id == StudentAcademicInfoModel.course_id
            ).outerjoin(
                StudentModel, 
                (StudentAcademicInfoModel.student_id == StudentModel.id) & 
                (StudentModel.deleted_status_id == 0)
            )

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(CourseModel.school_id == school_id)

            # Aplicar filtro de búsqueda si se proporciona course
            if course and course.strip():
                query = query.filter(CourseModel.course_name.like(f"%{course.strip()}%"))
            
            # Aplicar filtro por teaching_id si se proporciona
            if teaching_id is not None:
                query = query.filter(CourseModel.teaching_id == teaching_id)

            query = query.group_by(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).order_by(CourseModel.id)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0

                if total_items == 0:
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                if page < 1 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": course.id,
                    "teaching_id": course.teaching_id,
                    "course_name": course.course_name,
                    "teaching_name": course.teaching_name,
                    "total_students": course.total_students,
                    "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                    "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
                } for course in data]

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
                    "id": course.id,
                    "school_id": course.school_id,
                    "teaching_id": course.teaching_id,
                    "course_name": course.course_name,
                    "teaching_name": course.teaching_name,
                    "total_students": course.total_students,
                    "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                    "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
                } for course in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_all_list(self, school_id=None, teaching_id=None):
        """Retorna todos los courses sin paginación ni búsqueda"""
        try:
            query = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            )

            # Filtrar por school_id si se proporciona
            if school_id:
                query = query.filter(CourseModel.school_id == school_id)
            
            # Filtrar por teaching_id si se proporciona
            if teaching_id:
                query = query.filter(CourseModel.teaching_id == teaching_id)

            query = query.order_by(CourseModel.id)
            
            data = query.all()

            serialized_data = [{
                "id": course.id,
                "school_id": course.school_id,
                "teaching_id": course.teaching_id,
                "course_name": course.course_name,
                "teaching_name": course.teaching_name,
                "added_date": course.added_date.strftime("%Y-%m-%d %H:%M:%S") if course.added_date else None,
                "updated_date": course.updated_date.strftime("%Y-%m-%d %H:%M:%S") if course.updated_date else None
            } for course in data]

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(
                CourseModel.id,
                CourseModel.school_id,
                CourseModel.teaching_id,
                CourseModel.course_name,
                CourseModel.added_date,
                CourseModel.updated_date,
                TeachingModel.teaching_name
            ).join(
                TeachingModel, CourseModel.teaching_id == TeachingModel.id
            ).filter(CourseModel.id == id).first()

            if data_query:
                course_data = {
                    "id": data_query.id,
                    "school_id": data_query.school_id,
                    "teaching_id": data_query.teaching_id,
                    "course_name": data_query.course_name,
                    "teaching_name": data_query.teaching_name,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"course_data": course_data}

            else:
                return {"error": "No se encontraron datos para el course especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, course_inputs):
        try:
            new_course = CourseModel(
                school_id=course_inputs.get('school_id'),
                teaching_id=course_inputs['teaching_id'],
                course_name=course_inputs['course_name'],
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_course)
            self.db.commit()
            self.db.refresh(new_course)

            return {
                "status": "success",
                "message": "Course created successfully",
                "course_id": new_course.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(CourseModel).filter(CourseModel.id == id).first()
            if data:
                # Marcar como eliminado en professionals_teachings_courses
                self.db.query(ProfessionalTeachingCourseModel).filter(
                    ProfessionalTeachingCourseModel.course_id == id
                ).update({
                    "deleted_status_id": 1,
                    "updated_date": datetime.now()
                })
                
                self.db.delete(data)
                self.db.commit()
                return {"status": "success", "message": "Course deleted successfully"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, course_inputs):
        try:
            existing_course = self.db.query(CourseModel).filter(CourseModel.id == id).one_or_none()

            if not existing_course:
                return {"status": "error", "message": "No data found"}

            for key, value in course_inputs.items():
                setattr(existing_course, key, value)

            existing_course.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_course)

            return {"status": "success", "message": "Course updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}