from typing import Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.backend.db.models import ProgressStatusStudentModel, StudentGuardianModel, FamilyMemberModel


class ProgressStatusStudentClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """
        Obtiene un estado de avance por su ID.
        """
        try:
            progress_status = self.db.query(ProgressStatusStudentModel).filter(
                ProgressStatusStudentModel.id == id,
                ProgressStatusStudentModel.deleted_date == None
            ).first()

            if progress_status:
                # Obtener información del guardian si existe guardian_relationship_id
                guardian_name = None
                guardian_lastname = None
                guardian_relationship = None
                if progress_status.guardian_relationship_id:
                    guardian = self.db.query(StudentGuardianModel).filter(
                        StudentGuardianModel.id == progress_status.guardian_relationship_id
                    ).first()
                    if guardian:
                        guardian_name = guardian.names
                        guardian_lastname = f"{guardian.father_lastname or ''} {guardian.mother_lastname or ''}".strip()
                        # Obtener la relación (family_member)
                        if guardian.family_member_id:
                            family_member = self.db.query(FamilyMemberModel).filter(
                                FamilyMemberModel.id == guardian.family_member_id
                            ).first()
                            if family_member:
                                guardian_relationship = family_member.family_member
                
                return {
                    "id": progress_status.id,
                    "version_id": progress_status.version_id,
                    "student_id": progress_status.student_id,
                    "school_id": progress_status.school_id,
                    "document_id": progress_status.document_id,
                    "nee_id": progress_status.nee_id,
                    "course_id": progress_status.course_id,
                    "guardian_relationship_id": progress_status.guardian_relationship_id,
                    "period_id": progress_status.period_id,
                    "guardian_name": guardian_name,
                    "guardian_lastname": guardian_lastname,
                    "guardian_relationship": guardian_relationship,
                    "responsible_professionals": progress_status.responsible_professionals,
                    "progress_date": progress_status.progress_date.strftime("%Y-%m-%d") if progress_status.progress_date else None,
                    "pedagogical_language": progress_status.pedagogical_language,
                    "pedagogical_mathematics": progress_status.pedagogical_mathematics,
                    "psychopedagogical": progress_status.psychopedagogical,
                    "speech_therapy": progress_status.speech_therapy,
                    "psychological": progress_status.psychological,
                    "kinesiology": progress_status.kinesiology,
                    "occupational_therapy": progress_status.occupational_therapy,
                    "deaf_co_educator": progress_status.deaf_co_educator,
                    "synthesis_comments": progress_status.synthesis_comments,
                    "suggestions_family": progress_status.suggestions_family,
                    "suggestions_establishment": progress_status.suggestions_establishment,
                    "file": progress_status.file,
                    "added_date": progress_status.added_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.added_date else None,
                    "updated_date": progress_status.updated_date.strftime("%Y-%m-%d %H:%M:%S") if progress_status.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el estado de avance especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, student_id: Optional[int] = None, school_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de estados de avance almacenados.
        Puede filtrarse por student_id y school_id.
        """
        try:
            query = self.db.query(ProgressStatusStudentModel).filter(
                ProgressStatusStudentModel.deleted_date == None
            )

            if student_id is not None:
                query = query.filter(ProgressStatusStudentModel.student_id == student_id)
            
            if school_id is not None:
                query = query.filter(ProgressStatusStudentModel.school_id == school_id)

            progress_statuses = query.order_by(ProgressStatusStudentModel.id.desc()).all()

            result = []
            for ps in progress_statuses:
                # Obtener información del guardian si existe guardian_relationship_id
                guardian_name = None
                guardian_lastname = None
                guardian_relationship = None
                if ps.guardian_relationship_id:
                    guardian = self.db.query(StudentGuardianModel).filter(
                        StudentGuardianModel.id == ps.guardian_relationship_id
                    ).first()
                    if guardian:
                        guardian_name = guardian.names
                        guardian_lastname = f"{guardian.father_lastname or ''} {guardian.mother_lastname or ''}".strip()
                        # Obtener la relación (family_member)
                        if guardian.family_member_id:
                            family_member = self.db.query(FamilyMemberModel).filter(
                                FamilyMemberModel.id == guardian.family_member_id
                            ).first()
                            if family_member:
                                guardian_relationship = family_member.family_member
                
                result.append({
                    "id": ps.id,
                    "version_id": ps.version_id,
                    "student_id": ps.student_id,
                    "school_id": ps.school_id,
                    "document_id": ps.document_id,
                    "nee_id": ps.nee_id,
                    "course_id": ps.course_id,
                    "guardian_relationship_id": ps.guardian_relationship_id,
                    "period_id": ps.period_id,
                    "guardian_name": guardian_name,
                    "guardian_lastname": guardian_lastname,
                    "guardian_relationship": guardian_relationship,
                    "responsible_professionals": ps.responsible_professionals,
                    "progress_date": ps.progress_date.strftime("%Y-%m-%d") if ps.progress_date else None,
                    "pedagogical_language": ps.pedagogical_language,
                    "pedagogical_mathematics": ps.pedagogical_mathematics,
                    "psychopedagogical": ps.psychopedagogical,
                    "speech_therapy": ps.speech_therapy,
                    "psychological": ps.psychological,
                    "kinesiology": ps.kinesiology,
                    "occupational_therapy": ps.occupational_therapy,
                    "deaf_co_educator": ps.deaf_co_educator,
                    "synthesis_comments": ps.synthesis_comments,
                    "suggestions_family": ps.suggestions_family,
                    "suggestions_establishment": ps.suggestions_establishment,
                    "file": ps.file,
                    "added_date": ps.added_date.strftime("%Y-%m-%d %H:%M:%S") if ps.added_date else None,
                    "updated_date": ps.updated_date.strftime("%Y-%m-%d %H:%M:%S") if ps.updated_date else None
                })

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, progress_status_data: dict) -> Any:
        """
        Almacena un nuevo estado de avance.
        """
        try:
            # Convertir progress_date de string a date si viene como string
            progress_date_obj = None
            if progress_status_data.get('progress_date'):
                if isinstance(progress_status_data.get('progress_date'), str):
                    try:
                        progress_date_obj = datetime.strptime(progress_status_data.get('progress_date'), "%Y-%m-%d").date()
                    except:
                        progress_date_obj = None
                else:
                    progress_date_obj = progress_status_data.get('progress_date')

            # responsible_professionals viene como texto (ej: "1,2,3")
            responsible_professionals_text = progress_status_data.get('responsible_professionals')

            # Determinar version_id si no se proporciona
            version_id = progress_status_data.get('version_id')
            student_id = progress_status_data.get('student_id')
            school_id = progress_status_data.get('school_id')
            document_id = progress_status_data.get('document_id', 18)
            
            # Buscar si ya existe un registro con estos criterios
            existing_progress_status = None
            if student_id is not None and school_id is not None:
                query = self.db.query(ProgressStatusStudentModel).filter(
                    ProgressStatusStudentModel.student_id == student_id,
                    ProgressStatusStudentModel.school_id == school_id,
                    ProgressStatusStudentModel.document_id == document_id,
                    ProgressStatusStudentModel.deleted_date == None
                )
                
                if version_id is not None:
                    # Si se proporciona version_id, buscar por ese específico
                    query = query.filter(ProgressStatusStudentModel.version_id == version_id)
                    existing_progress_status = query.first()
                else:
                    # Si no se proporciona version_id, buscar la última versión
                    existing_progress_status = query.order_by(ProgressStatusStudentModel.version_id.desc()).first()
                    if existing_progress_status:
                        version_id = existing_progress_status.version_id
            
            # Si existe un registro, hacer update
            if existing_progress_status:
                # Actualizar campos
                if 'nee_id' in progress_status_data:
                    existing_progress_status.nee_id = progress_status_data.get('nee_id')
                if 'course_id' in progress_status_data:
                    existing_progress_status.course_id = progress_status_data.get('course_id')
                if 'guardian_relationship_id' in progress_status_data:
                    existing_progress_status.guardian_relationship_id = progress_status_data.get('guardian_relationship_id')
                if 'period_id' in progress_status_data:
                    existing_progress_status.period_id = progress_status_data.get('period_id')
                
                existing_progress_status.responsible_professionals = responsible_professionals_text
                existing_progress_status.progress_date = progress_date_obj
                
                if 'pedagogical_language' in progress_status_data:
                    existing_progress_status.pedagogical_language = progress_status_data.get('pedagogical_language')
                if 'pedagogical_mathematics' in progress_status_data:
                    existing_progress_status.pedagogical_mathematics = progress_status_data.get('pedagogical_mathematics')
                if 'psychopedagogical' in progress_status_data:
                    existing_progress_status.psychopedagogical = progress_status_data.get('psychopedagogical')
                if 'speech_therapy' in progress_status_data:
                    existing_progress_status.speech_therapy = progress_status_data.get('speech_therapy')
                if 'psychological' in progress_status_data:
                    existing_progress_status.psychological = progress_status_data.get('psychological')
                if 'kinesiology' in progress_status_data:
                    existing_progress_status.kinesiology = progress_status_data.get('kinesiology')
                if 'occupational_therapy' in progress_status_data:
                    existing_progress_status.occupational_therapy = progress_status_data.get('occupational_therapy')
                if 'deaf_co_educator' in progress_status_data:
                    existing_progress_status.deaf_co_educator = progress_status_data.get('deaf_co_educator')
                
                if 'synthesis_comments' in progress_status_data:
                    existing_progress_status.synthesis_comments = progress_status_data.get('synthesis_comments')
                if 'suggestions_family' in progress_status_data:
                    existing_progress_status.suggestions_family = progress_status_data.get('suggestions_family')
                if 'suggestions_establishment' in progress_status_data:
                    existing_progress_status.suggestions_establishment = progress_status_data.get('suggestions_establishment')
                
                if 'file' in progress_status_data:
                    existing_progress_status.file = progress_status_data.get('file')
                
                existing_progress_status.updated_date = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing_progress_status)
                
                return {
                    "status": "success",
                    "message": "Estado de avance actualizado exitosamente",
                    "id": existing_progress_status.id
                }
            
            # Si no existe, crear nuevo registro
            if version_id is None and student_id is not None:
                # Buscar la última versión para este estudiante y documento en progress_status_students
                last_version = self.db.query(ProgressStatusStudentModel).filter(
                    ProgressStatusStudentModel.student_id == student_id,
                    ProgressStatusStudentModel.document_id == document_id,
                    ProgressStatusStudentModel.deleted_date == None
                ).order_by(ProgressStatusStudentModel.version_id.desc()).first()
                
                if last_version:
                    version_id = last_version.version_id + 1
                else:
                    version_id = 1
            elif version_id is None:
                version_id = 1  # Si no hay student_id, usar versión 1 por defecto

            # Crear el nuevo registro
            new_progress_status = ProgressStatusStudentModel(
                version_id=version_id,
                student_id=student_id,
                school_id=school_id,
                document_id=document_id,
                nee_id=progress_status_data.get('nee_id'),
                course_id=progress_status_data.get('course_id'),
                guardian_relationship_id=progress_status_data.get('guardian_relationship_id'),
                period_id=progress_status_data.get('period_id'),
                responsible_professionals=responsible_professionals_text,
                progress_date=progress_date_obj,
                pedagogical_language=progress_status_data.get('pedagogical_language'),
                pedagogical_mathematics=progress_status_data.get('pedagogical_mathematics'),
                psychopedagogical=progress_status_data.get('psychopedagogical'),
                speech_therapy=progress_status_data.get('speech_therapy'),
                psychological=progress_status_data.get('psychological'),
                kinesiology=progress_status_data.get('kinesiology'),
                occupational_therapy=progress_status_data.get('occupational_therapy'),
                deaf_co_educator=progress_status_data.get('deaf_co_educator'),
                synthesis_comments=progress_status_data.get('synthesis_comments'),
                suggestions_family=progress_status_data.get('suggestions_family'),
                suggestions_establishment=progress_status_data.get('suggestions_establishment'),
                file=progress_status_data.get('file'),
                added_date=datetime.now(),
                updated_date=datetime.now(),
                deleted_date=None
            )

            self.db.add(new_progress_status)
            self.db.commit()
            self.db.refresh(new_progress_status)

            return {
                "status": "success",
                "message": "Estado de avance creado exitosamente",
                "id": new_progress_status.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, id: int, progress_status_data: dict) -> Any:
        """
        Actualiza un estado de avance existente.
        """
        try:
            progress_status = self.db.query(ProgressStatusStudentModel).filter(
                ProgressStatusStudentModel.id == id,
                ProgressStatusStudentModel.deleted_date == None
            ).first()

            if not progress_status:
                return {"status": "error", "message": "Estado de avance no encontrado"}

            # Actualizar campos si se proporcionan (permitir None explícitamente)
            if 'version_id' in progress_status_data:
                progress_status.version_id = progress_status_data['version_id']
            if 'student_id' in progress_status_data:
                progress_status.student_id = progress_status_data['student_id']
            if 'school_id' in progress_status_data:
                progress_status.school_id = progress_status_data['school_id']
            if 'document_id' in progress_status_data:
                progress_status.document_id = progress_status_data['document_id']
            if 'nee_id' in progress_status_data:
                progress_status.nee_id = progress_status_data['nee_id']
            if 'course_id' in progress_status_data:
                progress_status.course_id = progress_status_data['course_id']
            if 'guardian_relationship_id' in progress_status_data:
                progress_status.guardian_relationship_id = progress_status_data['guardian_relationship_id']
            if 'period_id' in progress_status_data:
                progress_status.period_id = progress_status_data['period_id']
            
            # Actualizar responsible_professionals (viene como texto: "1,2,3")
            if 'responsible_professionals' in progress_status_data:
                progress_status.responsible_professionals = progress_status_data['responsible_professionals']

            # Actualizar progress_date
            if 'progress_date' in progress_status_data:
                if progress_status_data['progress_date']:
                    if isinstance(progress_status_data['progress_date'], str):
                        try:
                            progress_status.progress_date = datetime.strptime(progress_status_data['progress_date'], "%Y-%m-%d").date()
                        except:
                            pass
                    else:
                        progress_status.progress_date = progress_status_data['progress_date']
                else:
                    progress_status.progress_date = None

            # Actualizar áreas
            if 'pedagogical_language' in progress_status_data:
                progress_status.pedagogical_language = progress_status_data['pedagogical_language']
            if 'pedagogical_mathematics' in progress_status_data:
                progress_status.pedagogical_mathematics = progress_status_data['pedagogical_mathematics']
            if 'psychopedagogical' in progress_status_data:
                progress_status.psychopedagogical = progress_status_data['psychopedagogical']
            if 'speech_therapy' in progress_status_data:
                progress_status.speech_therapy = progress_status_data['speech_therapy']
            if 'psychological' in progress_status_data:
                progress_status.psychological = progress_status_data['psychological']
            if 'kinesiology' in progress_status_data:
                progress_status.kinesiology = progress_status_data['kinesiology']
            if 'occupational_therapy' in progress_status_data:
                progress_status.occupational_therapy = progress_status_data['occupational_therapy']
            if 'deaf_co_educator' in progress_status_data:
                progress_status.deaf_co_educator = progress_status_data['deaf_co_educator']
            
            # Actualizar síntesis y sugerencias
            if 'synthesis_comments' in progress_status_data:
                progress_status.synthesis_comments = progress_status_data['synthesis_comments']
            if 'suggestions_family' in progress_status_data:
                progress_status.suggestions_family = progress_status_data['suggestions_family']
            if 'suggestions_establishment' in progress_status_data:
                progress_status.suggestions_establishment = progress_status_data['suggestions_establishment']
            
            # Actualizar archivo
            if 'file' in progress_status_data:
                progress_status.file = progress_status_data['file']

            progress_status.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(progress_status)

            return {
                "status": "success",
                "message": "Estado de avance actualizado exitosamente",
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
        Elimina lógicamente un estado de avance (soft delete).
        """
        try:
            progress_status = self.db.query(ProgressStatusStudentModel).filter(
                ProgressStatusStudentModel.id == id,
                ProgressStatusStudentModel.deleted_date == None
            ).first()

            if not progress_status:
                return {"status": "error", "message": "Estado de avance no encontrado"}

            # Soft delete
            progress_status.deleted_date = datetime.now()
            progress_status.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Estado de avance eliminado exitosamente"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
