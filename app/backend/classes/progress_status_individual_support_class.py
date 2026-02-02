from typing import Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
import json
from app.backend.db.models import ProgressStatusIndividualSupportModel


class ProgressStatusIndividualSupportClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """
        Obtiene un estado de avance PAI por su ID.
        """
        try:
            progress_status = self.db.query(ProgressStatusIndividualSupportModel).filter(
                ProgressStatusIndividualSupportModel.id == id,
                ProgressStatusIndividualSupportModel.deleted_date == None
            ).first()

            if progress_status:
                # Parsear pai_objectives si existe
                pai_objectives = None
                if progress_status.pai_objectives:
                    try:
                        pai_objectives = json.loads(progress_status.pai_objectives)
                    except:
                        pai_objectives = progress_status.pai_objectives
                
                return {
                    "id": progress_status.id,
                    "student_id": progress_status.student_id,
                    "school_id": progress_status.school_id,
                    "document_type_id": progress_status.document_type_id,
                    "student_full_name": progress_status.student_full_name,
                    "student_identification_number": progress_status.student_identification_number,
                    "student_born_date": progress_status.student_born_date.strftime("%Y-%m-%d") if progress_status.student_born_date else None,
                    "student_age": progress_status.student_age,
                    "student_nee_id": progress_status.student_nee_id,
                    "student_school": progress_status.student_school,
                    "student_course_id": progress_status.student_course_id,
                    "progress_date": progress_status.progress_date.strftime("%Y-%m-%d") if progress_status.progress_date else None,
                    "period_id": progress_status.period_id,
                    "guardian_relationship_id": progress_status.guardian_relationship_id,
                    "guardian_name": progress_status.guardian_name,
                    "responsible_professionals": progress_status.responsible_professionals,
                    "selected_pai_id": progress_status.selected_pai_id,
                    "pai_objectives": pai_objectives,
                    "pai_observations": progress_status.pai_observations,
                    "suggestions_family": progress_status.suggestions_family,
                    "suggestions_establishment": progress_status.suggestions_establishment,
                    "added_date": progress_status.added_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.added_date else None,
                    "updated_date": progress_status.updated_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el estado de avance PAI especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_student_id(self, student_id: int) -> Any:
        """
        Obtiene el último estado de avance PAI por el ID del estudiante.
        """
        try:
            progress_status = self.db.query(ProgressStatusIndividualSupportModel).filter(
                ProgressStatusIndividualSupportModel.student_id == student_id,
                ProgressStatusIndividualSupportModel.deleted_date == None
            ).order_by(ProgressStatusIndividualSupportModel.id.desc()).first()

            if progress_status:
                # Parsear pai_objectives si existe
                pai_objectives = None
                if progress_status.pai_objectives:
                    try:
                        pai_objectives = json.loads(progress_status.pai_objectives)
                    except:
                        pai_objectives = progress_status.pai_objectives
                
                return {
                    "id": progress_status.id,
                    "student_id": progress_status.student_id,
                    "school_id": progress_status.school_id,
                    "document_type_id": progress_status.document_type_id,
                    "student_full_name": progress_status.student_full_name,
                    "student_identification_number": progress_status.student_identification_number,
                    "student_born_date": progress_status.student_born_date.strftime("%Y-%m-%d") if progress_status.student_born_date else None,
                    "student_age": progress_status.student_age,
                    "student_nee_id": progress_status.student_nee_id,
                    "student_school": progress_status.student_school,
                    "student_course_id": progress_status.student_course_id,
                    "progress_date": progress_status.progress_date.strftime("%Y-%m-%d") if progress_status.progress_date else None,
                    "period_id": progress_status.period_id,
                    "guardian_relationship_id": progress_status.guardian_relationship_id,
                    "guardian_name": progress_status.guardian_name,
                    "responsible_professionals": progress_status.responsible_professionals,
                    "selected_pai_id": progress_status.selected_pai_id,
                    "pai_objectives": pai_objectives,
                    "pai_observations": progress_status.pai_observations,
                    "suggestions_family": progress_status.suggestions_family,
                    "suggestions_establishment": progress_status.suggestions_establishment,
                    "added_date": progress_status.added_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.added_date else None,
                    "updated_date": progress_status.updated_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el estado de avance PAI del estudiante especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, student_id: Optional[int] = None, school_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de estados de avance PAI almacenados.
        Puede filtrarse por student_id y school_id.
        """
        try:
            query = self.db.query(ProgressStatusIndividualSupportModel).filter(
                ProgressStatusIndividualSupportModel.deleted_date == None
            )

            if student_id is not None:
                query = query.filter(ProgressStatusIndividualSupportModel.student_id == student_id)
            
            if school_id is not None:
                query = query.filter(ProgressStatusIndividualSupportModel.school_id == school_id)

            progress_statuses = query.order_by(ProgressStatusIndividualSupportModel.id.desc()).all()

            result = []
            for ps in progress_statuses:
                # Parsear pai_objectives si existe
                pai_objectives = None
                if ps.pai_objectives:
                    try:
                        pai_objectives = json.loads(ps.pai_objectives)
                    except:
                        pai_objectives = ps.pai_objectives
                
                result.append({
                    "id": ps.id,
                    "student_id": ps.student_id,
                    "school_id": ps.school_id,
                    "document_type_id": ps.document_type_id,
                    "student_full_name": ps.student_full_name,
                    "student_identification_number": ps.student_identification_number,
                    "student_born_date": ps.student_born_date.strftime("%Y-%m-%d") if ps.student_born_date else None,
                    "student_age": ps.student_age,
                    "student_nee_id": ps.student_nee_id,
                    "student_school": ps.student_school,
                    "student_course_id": ps.student_course_id,
                    "progress_date": ps.progress_date.strftime("%Y-%m-%d") if ps.progress_date else None,
                    "period_id": ps.period_id,
                    "guardian_relationship_id": ps.guardian_relationship_id,
                    "guardian_name": ps.guardian_name,
                    "responsible_professionals": ps.responsible_professionals,
                    "selected_pai_id": ps.selected_pai_id,
                    "pai_objectives": pai_objectives,
                    "pai_observations": ps.pai_observations,
                    "suggestions_family": ps.suggestions_family,
                    "suggestions_establishment": ps.suggestions_establishment,
                    "added_date": ps.added_date.strftime("%Y-%m-%d %H:%M:%S") if ps.added_date else None,
                    "updated_date": ps.updated_date.strftime("%Y-%m-%d %H:%M:%S") if ps.updated_date else None
                })

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, data: dict) -> Any:
        """
        Almacena un nuevo estado de avance PAI.
        Si ya existe un registro con los mismos student_id, school_id, document_type_id y period_id, lo actualiza.
        """
        try:
            # Convertir fechas de string a date si vienen como string
            student_born_date_obj = None
            if data.get('student_born_date'):
                if isinstance(data.get('student_born_date'), str):
                    try:
                        student_born_date_obj = datetime.strptime(data.get('student_born_date'), "%Y-%m-%d").date()
                    except:
                        student_born_date_obj = None
                else:
                    student_born_date_obj = data.get('student_born_date')

            progress_date_obj = None
            if data.get('progress_date'):
                if isinstance(data.get('progress_date'), str):
                    try:
                        progress_date_obj = datetime.strptime(data.get('progress_date'), "%Y-%m-%d").date()
                    except:
                        progress_date_obj = None
                else:
                    progress_date_obj = data.get('progress_date')

            # Convertir pai_objectives a JSON si es una lista
            pai_objectives_json = None
            if data.get('pai_objectives'):
                if isinstance(data.get('pai_objectives'), list):
                    # Convertir objetos PaiObjectiveSchema a diccionarios si es necesario
                    objectives_list = []
                    for obj in data.get('pai_objectives'):
                        if hasattr(obj, 'dict'):
                            objectives_list.append(obj.dict())
                        elif isinstance(obj, dict):
                            objectives_list.append(obj)
                        else:
                            objectives_list.append(obj)
                    pai_objectives_json = json.dumps(objectives_list)
                elif isinstance(data.get('pai_objectives'), str):
                    pai_objectives_json = data.get('pai_objectives')

            student_id = data.get('student_id')
            school_id = data.get('school_id')
            document_type_id = data.get('document_type_id', 19)
            period_id = data.get('period_id')
            
            # Buscar si ya existe un registro con estos criterios
            existing = None
            if student_id is not None and school_id is not None and document_type_id is not None and period_id is not None:
                existing = self.db.query(ProgressStatusIndividualSupportModel).filter(
                    ProgressStatusIndividualSupportModel.student_id == student_id,
                    ProgressStatusIndividualSupportModel.school_id == school_id,
                    ProgressStatusIndividualSupportModel.document_type_id == document_type_id,
                    ProgressStatusIndividualSupportModel.period_id == period_id,
                    ProgressStatusIndividualSupportModel.deleted_date == None
                ).first()
            
            # Si existe un registro, hacer update
            if existing:
                if 'student_id' in data:
                    existing.student_id = data.get('student_id')
                if 'school_id' in data:
                    existing.school_id = data.get('school_id')
                if 'document_type_id' in data:
                    existing.document_type_id = data.get('document_type_id')
                if 'student_full_name' in data:
                    existing.student_full_name = data.get('student_full_name')
                if 'student_identification_number' in data:
                    existing.student_identification_number = data.get('student_identification_number')
                if 'student_born_date' in data:
                    existing.student_born_date = student_born_date_obj
                if 'student_age' in data:
                    existing.student_age = data.get('student_age')
                if 'student_nee_id' in data:
                    existing.student_nee_id = data.get('student_nee_id')
                if 'student_school' in data:
                    existing.student_school = data.get('student_school')
                if 'student_course_id' in data:
                    existing.student_course_id = data.get('student_course_id')
                if 'progress_date' in data:
                    existing.progress_date = progress_date_obj
                if 'period_id' in data:
                    existing.period_id = data.get('period_id')
                if 'guardian_relationship_id' in data:
                    existing.guardian_relationship_id = data.get('guardian_relationship_id')
                if 'guardian_name' in data:
                    existing.guardian_name = data.get('guardian_name')
                if 'responsible_professionals' in data:
                    existing.responsible_professionals = data.get('responsible_professionals')
                if 'selected_pai_id' in data:
                    existing.selected_pai_id = data.get('selected_pai_id')
                if 'pai_objectives' in data:
                    existing.pai_objectives = pai_objectives_json
                if 'pai_observations' in data:
                    existing.pai_observations = data.get('pai_observations')
                if 'suggestions_family' in data:
                    existing.suggestions_family = data.get('suggestions_family')
                if 'suggestions_establishment' in data:
                    existing.suggestions_establishment = data.get('suggestions_establishment')
                
                existing.updated_date = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing)
                
                return {
                    "status": "success",
                    "message": "Estado de avance PAI actualizado exitosamente",
                    "id": existing.id
                }
            
            # Si no existe, crear nuevo registro
            new_progress_status = ProgressStatusIndividualSupportModel(
                student_id=data.get('student_id'),
                school_id=data.get('school_id'),
                document_type_id=data.get('document_type_id', 19),
                student_full_name=data.get('student_full_name'),
                student_identification_number=data.get('student_identification_number'),
                student_born_date=student_born_date_obj,
                student_age=data.get('student_age'),
                student_nee_id=data.get('student_nee_id'),
                student_school=data.get('student_school'),
                student_course_id=data.get('student_course_id'),
                progress_date=progress_date_obj,
                period_id=data.get('period_id'),
                guardian_relationship_id=data.get('guardian_relationship_id'),
                guardian_name=data.get('guardian_name'),
                responsible_professionals=data.get('responsible_professionals'),
                selected_pai_id=data.get('selected_pai_id'),
                pai_objectives=pai_objectives_json,
                pai_observations=data.get('pai_observations'),
                suggestions_family=data.get('suggestions_family'),
                suggestions_establishment=data.get('suggestions_establishment'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_progress_status)
            self.db.commit()
            self.db.refresh(new_progress_status)

            return {
                "status": "success",
                "message": "Estado de avance PAI creado exitosamente",
                "id": new_progress_status.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, id: int, data: dict) -> Any:
        """
        Actualiza un estado de avance PAI existente.
        """
        try:
            progress_status = self.db.query(ProgressStatusIndividualSupportModel).filter(
                ProgressStatusIndividualSupportModel.id == id,
                ProgressStatusIndividualSupportModel.deleted_date == None
            ).first()

            if not progress_status:
                return {
                    "status": "error",
                    "message": "Estado de avance PAI no encontrado"
                }

            # Actualizar campos
            if 'student_id' in data:
                progress_status.student_id = data.get('student_id')
            if 'school_id' in data:
                progress_status.school_id = data.get('school_id')
            if 'document_type_id' in data:
                progress_status.document_type_id = data.get('document_type_id')
            if 'student_full_name' in data:
                progress_status.student_full_name = data.get('student_full_name')
            if 'student_identification_number' in data:
                progress_status.student_identification_number = data.get('student_identification_number')
            if 'student_born_date' in data:
                if isinstance(data.get('student_born_date'), str):
                    try:
                        progress_status.student_born_date = datetime.strptime(data.get('student_born_date'), "%Y-%m-%d").date()
                    except:
                        pass
                else:
                    progress_status.student_born_date = data.get('student_born_date')
            if 'student_age' in data:
                progress_status.student_age = data.get('student_age')
            if 'student_nee_id' in data:
                progress_status.student_nee_id = data.get('student_nee_id')
            if 'student_school' in data:
                progress_status.student_school = data.get('student_school')
            if 'student_course_id' in data:
                progress_status.student_course_id = data.get('student_course_id')
            if 'progress_date' in data:
                if isinstance(data.get('progress_date'), str):
                    try:
                        progress_status.progress_date = datetime.strptime(data.get('progress_date'), "%Y-%m-%d").date()
                    except:
                        pass
                else:
                    progress_status.progress_date = data.get('progress_date')
            if 'period_id' in data:
                progress_status.period_id = data.get('period_id')
            if 'guardian_relationship_id' in data:
                progress_status.guardian_relationship_id = data.get('guardian_relationship_id')
            if 'guardian_name' in data:
                progress_status.guardian_name = data.get('guardian_name')
            if 'responsible_professionals' in data:
                progress_status.responsible_professionals = data.get('responsible_professionals')
            if 'selected_pai_id' in data:
                progress_status.selected_pai_id = data.get('selected_pai_id')
            if 'pai_objectives' in data:
                pai_objectives = data.get('pai_objectives')
                if isinstance(pai_objectives, list):
                    objectives_list = []
                    for obj in pai_objectives:
                        if hasattr(obj, 'dict'):
                            objectives_list.append(obj.dict())
                        elif isinstance(obj, dict):
                            objectives_list.append(obj)
                        else:
                            objectives_list.append(obj)
                    progress_status.pai_objectives = json.dumps(objectives_list)
                elif isinstance(pai_objectives, str):
                    progress_status.pai_objectives = pai_objectives
            if 'pai_observations' in data:
                progress_status.pai_observations = data.get('pai_observations')
            if 'suggestions_family' in data:
                progress_status.suggestions_family = data.get('suggestions_family')
            if 'suggestions_establishment' in data:
                progress_status.suggestions_establishment = data.get('suggestions_establishment')

            progress_status.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(progress_status)

            return {
                "status": "success",
                "message": "Estado de avance PAI actualizado exitosamente",
                "id": progress_status.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, id: int) -> Any:
        """
        Elimina lógicamente un estado de avance PAI (soft delete).
        """
        try:
            progress_status = self.db.query(ProgressStatusIndividualSupportModel).filter(
                ProgressStatusIndividualSupportModel.id == id,
                ProgressStatusIndividualSupportModel.deleted_date == None
            ).first()

            if not progress_status:
                return {
                    "status": "error",
                    "message": "Estado de avance PAI no encontrado"
                }

            # Soft delete
            progress_status.deleted_date = datetime.now()
            progress_status.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Estado de avance PAI eliminado exitosamente"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
