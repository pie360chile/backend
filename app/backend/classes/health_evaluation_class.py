from typing import Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.backend.db.models import HealthEvaluationModel, FolderModel


class HealthEvaluationClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """
        Obtiene una evaluación de salud por su ID.
        """
        try:
            evaluation = self.db.query(HealthEvaluationModel).filter(
                HealthEvaluationModel.id == id
            ).first()

            if evaluation:
                return {
                    "id": evaluation.id,
                    "student_id": evaluation.student_id,
                    "gender_id": evaluation.gender_id,
                    "nationality_id": evaluation.nationality_id,
                    "consultation_reason_id": evaluation.consultation_reason_id,
                    "profesional_id": evaluation.profesional_id,
                    "procedence_id": evaluation.procedence_id,
                    "full_name": evaluation.full_name,
                    "identification_number": evaluation.identification_number,
                    "born_date": evaluation.born_date.strftime("%Y-%m-%d") if evaluation.born_date else None,
                    "age": evaluation.age,
                    "native_language": evaluation.native_language,
                    "language_usually_used": evaluation.language_usually_used,
                    "consultation_reason_detail": evaluation.consultation_reason_detail,
                    "professional_identification_number": evaluation.professional_identification_number,
                    "professional_registration_number": evaluation.professional_registration_number,
                    "professional_specialty": evaluation.professional_specialty,
                    "procedence_other": evaluation.procedence_other,
                    "professional_contact": evaluation.professional_contact,
                    "evaluation_date": evaluation.evaluation_date.strftime("%Y-%m-%d") if evaluation.evaluation_date else None,
                    "reevaluation_date": evaluation.reevaluation_date.strftime("%Y-%m-%d") if evaluation.reevaluation_date else None,
                    "general_assessment": evaluation.general_assessment,
                    "diagnosis": evaluation.diagnosis,
                    "indications": evaluation.indications,
                    "added_date": evaluation.added_date.strftime("%Y-%m-%d %H:%M:%S") if evaluation.added_date else None,
                    "updated_date": evaluation.updated_date.strftime("%Y-%m-%d %H:%M:%S") if evaluation.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para la evaluación de salud especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de evaluaciones de salud almacenadas.
        Puede filtrarse por student_id.
        """
        try:
            query = self.db.query(HealthEvaluationModel)

            if student_id is not None:
                query = query.filter(HealthEvaluationModel.student_id == student_id)

            evaluations = query.order_by(HealthEvaluationModel.id.desc()).all()

            return [
                {
                    "id": eval.id,
                    "student_id": eval.student_id,
                    "gender_id": eval.gender_id,
                    "nationality_id": eval.nationality_id,
                    "consultation_reason_id": eval.consultation_reason_id,
                    "profesional_id": eval.profesional_id,
                    "procedence_id": eval.procedence_id,
                    "full_name": eval.full_name,
                    "identification_number": eval.identification_number,
                    "born_date": eval.born_date.strftime("%Y-%m-%d") if eval.born_date else None,
                    "age": eval.age,
                    "native_language": eval.native_language,
                    "language_usually_used": eval.language_usually_used,
                    "consultation_reason_detail": eval.consultation_reason_detail,
                    "professional_identification_number": eval.professional_identification_number,
                    "professional_registration_number": eval.professional_registration_number,
                    "professional_specialty": eval.professional_specialty,
                    "procedence_other": eval.procedence_other,
                    "professional_contact": eval.professional_contact,
                    "evaluation_date": eval.evaluation_date.strftime("%Y-%m-%d") if eval.evaluation_date else None,
                    "reevaluation_date": eval.reevaluation_date.strftime("%Y-%m-%d") if eval.reevaluation_date else None,
                    "general_assessment": eval.general_assessment,
                    "diagnosis": eval.diagnosis,
                    "indications": eval.indications,
                    "added_date": eval.added_date.strftime("%Y-%m-%d %H:%M:%S") if eval.added_date else None,
                    "updated_date": eval.updated_date.strftime("%Y-%m-%d %H:%M:%S") if eval.updated_date else None
                }
                for eval in evaluations
            ]

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, evaluation_data: dict) -> Any:
        """
        Almacena una nueva evaluación de salud.
        """
        try:
            # Convertir fechas de string a date/datetime si vienen como string
            born_date_obj = None
            if evaluation_data.get('born_date'):
                if isinstance(evaluation_data.get('born_date'), str):
                    try:
                        born_date_obj = datetime.strptime(evaluation_data.get('born_date'), "%Y-%m-%d").date()
                    except:
                        born_date_obj = None
                else:
                    born_date_obj = evaluation_data.get('born_date')

            evaluation_date_obj = None
            if evaluation_data.get('evaluation_date'):
                if isinstance(evaluation_data.get('evaluation_date'), str):
                    try:
                        evaluation_date_obj = datetime.strptime(evaluation_data.get('evaluation_date'), "%Y-%m-%d").date()
                    except:
                        evaluation_date_obj = None
                else:
                    evaluation_date_obj = evaluation_data.get('evaluation_date')

            reevaluation_date_obj = None
            if evaluation_data.get('reevaluation_date'):
                if isinstance(evaluation_data.get('reevaluation_date'), str):
                    try:
                        reevaluation_date_obj = datetime.strptime(evaluation_data.get('reevaluation_date'), "%Y-%m-%d").date()
                    except:
                        reevaluation_date_obj = None
                else:
                    reevaluation_date_obj = evaluation_data.get('reevaluation_date')

            # Crear el nuevo registro
            new_evaluation = HealthEvaluationModel(
                student_id=evaluation_data.get('student_id'),
                gender_id=evaluation_data.get('gender_id'),
                nationality_id=evaluation_data.get('nationality_id'),
                consultation_reason_id=evaluation_data.get('consultation_reason_id'),
                profesional_id=evaluation_data.get('profesional_id'),
                procedence_id=evaluation_data.get('procedence_id'),
                full_name=evaluation_data.get('full_name'),
                identification_number=evaluation_data.get('identification_number'),
                born_date=born_date_obj,
                age=evaluation_data.get('age'),
                native_language=evaluation_data.get('native_language'),
                language_usually_used=evaluation_data.get('language_usually_used'),
                consultation_reason_detail=evaluation_data.get('consultation_reason_detail'),
                professional_identification_number=evaluation_data.get('professional_identification_number'),
                professional_registration_number=evaluation_data.get('professional_registration_number'),
                professional_specialty=evaluation_data.get('professional_specialty'),
                procedence_other=evaluation_data.get('procedence_other'),
                professional_contact=evaluation_data.get('professional_contact'),
                evaluation_date=evaluation_date_obj,
                reevaluation_date=reevaluation_date_obj,
                general_assessment=evaluation_data.get('general_assessment'),
                diagnosis=evaluation_data.get('diagnosis'),
                indications=evaluation_data.get('indications'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_evaluation)
            self.db.flush()  # Para obtener el ID sin hacer commit aún
            
            # Guardar también en la tabla folders
            try:
                # document_id siempre es 4 para health evaluations
                document_id = 4
                
                # Buscar la última versión para este estudiante y documento
                last_version = self.db.query(FolderModel).filter(
                    FolderModel.student_id == new_evaluation.student_id,
                    FolderModel.document_id == document_id
                ).order_by(FolderModel.version_id.desc()).first()
                
                # Determinar el nuevo version_id
                if last_version:
                    new_version_id = last_version.version_id + 1
                else:
                    new_version_id = 1
                
                # Crear el registro en folders
                new_folder = FolderModel(
                    student_id=new_evaluation.student_id,
                    document_id=document_id,
                    version_id=new_version_id,
                    detail_id=new_evaluation.id,  # El ID de la evaluación de salud
                    file=None,  # No hay archivo asociado inicialmente
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                
                self.db.add(new_folder)
                self.db.flush()  # Asegurar que el folder también se guarde
                
            except Exception as folder_error:
                # Si hay error al guardar en folders, hacer rollback de todo
                self.db.rollback()
                return {
                    "status": "error",
                    "message": f"Error guardando en tabla folders: {str(folder_error)}"
                }
            
            self.db.commit()
            self.db.refresh(new_evaluation)

            return {
                "status": "success",
                "message": "Evaluación de salud creada exitosamente",
                "id": new_evaluation.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
