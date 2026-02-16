from typing import Optional, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
from app.backend.db.models import IndividualSupportPlanModel, IndividualSupportPlanProfessionalModel

# Mapeo period_id -> etiqueta: 1=1er Trimestre, 2=2do Trimestre, 3=1er Semestre, 4=2do Semestre
PERIOD_LABELS = {
    1: "1er Trimestre",
    2: "2do Trimestre",
    3: "1er Semestre",
    4: "2do Semestre",
}


def _period_label(period_id: Optional[int]) -> Optional[str]:
    return PERIOD_LABELS.get(period_id) if period_id is not None else None


class IndividualSupportPlanClass:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Any:
        """
        Obtiene un Plan de Apoyo Individual por su ID.
        """
        try:
            isp = self.db.query(IndividualSupportPlanModel).filter(
                IndividualSupportPlanModel.id == id,
                IndividualSupportPlanModel.deleted_date == None
            ).first()

            if isp:
                # Obtener profesionales asociados
                professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                    IndividualSupportPlanProfessionalModel.individual_support_plan_id == id,
                    IndividualSupportPlanProfessionalModel.deleted_date == None
                ).all()
                
                professionals_list = []
                for prof in professionals:
                    professionals_list.append({
                        "id": prof.id,
                        "professional_id": prof.professional_id,
                        "career_type_id": prof.career_type_id,
                        "registration_number": prof.registration_number,
                        "days_hours": prof.days_hours,
                        "from_date": prof.from_date.strftime("%Y-%m-%d") if prof.from_date else None,
                        "to_date": prof.to_date.strftime("%Y-%m-%d") if prof.to_date else None,
                        "support_modality": prof.support_modality
                    })
                
                return {
                    "id": isp.id,
                    "student_id": isp.student_id,
                    "document_type_id": isp.document_type_id,
                    "school_id": isp.school_id,
                    "period_id": isp.period_id,
                    "period_label": _period_label(isp.period_id),
                    "student_full_name": isp.student_full_name,
                    "student_identification_number": isp.student_identification_number,
                    "student_born_date": isp.student_born_date.strftime("%Y-%m-%d") if isp.student_born_date else None,
                    "student_age": isp.student_age,
                    "student_nee_id": isp.student_nee_id,
                    "student_school": isp.student_school,
                    "student_course_id": isp.student_course_id,
                    "elaboration_date": isp.elaboration_date.strftime("%Y-%m-%d") if isp.elaboration_date else None,
                    "social_affective_strengths": isp.social_affective_strengths,
                    "cognitive_strengths": isp.cognitive_strengths,
                    "curricular_strengths": isp.curricular_strengths,
                    "family_strengths": isp.family_strengths,
                    "intervention_ed_diferencial": isp.intervention_ed_diferencial,
                    "intervention_ed_diferencial_strategies": isp.intervention_ed_diferencial_strategies,
                    "intervention_psicopedagogia": isp.intervention_psicopedagogia,
                    "intervention_psicopedagogia_strategies": isp.intervention_psicopedagogia_strategies,
                    "intervention_fonoaudiologia": isp.intervention_fonoaudiologia,
                    "intervention_fonoaudiologia_strategies": isp.intervention_fonoaudiologia_strategies,
                    "intervention_psicologia": isp.intervention_psicologia,
                    "intervention_psicologia_strategies": isp.intervention_psicologia_strategies,
                    "intervention_terapia_ocupacional": isp.intervention_terapia_ocupacional,
                    "intervention_terapia_ocupacional_strategies": isp.intervention_terapia_ocupacional_strategies,
                    "intervention_kinesiologia": isp.intervention_kinesiologia,
                    "intervention_kinesiologia_strategies": isp.intervention_kinesiologia_strategies,
                    "intervention_coeducador_sordo": isp.intervention_coeducador_sordo,
                    "intervention_coeducador_sordo_strategies": isp.intervention_coeducador_sordo_strategies,
                    "intervention_int_lengua_senas": isp.intervention_int_lengua_senas,
                    "intervention_int_lengua_senas_strategies": isp.intervention_int_lengua_senas_strategies,
                    "follow_up_pai": isp.follow_up_pai,
                    "professionals": professionals_list,
                    "added_date": isp.added_date.strftime("%Y-%m-%d %H:%M:%S") if isp.added_date else None,
                    "updated_date": isp.updated_date.strftime("%Y-%m-%d %H:%M:%S") if isp.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el Plan de Apoyo Individual especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_student_id(self, student_id: int) -> Any:
        """
        Obtiene un Plan de Apoyo Individual por el ID del estudiante.
        """
        try:
            isp = self.db.query(IndividualSupportPlanModel).filter(
                IndividualSupportPlanModel.student_id == student_id,
                IndividualSupportPlanModel.deleted_date == None
            ).order_by(IndividualSupportPlanModel.id.desc()).first()

            if isp:
                # Asegurar que la sesión esté sincronizada con la base de datos
                self.db.expire_all()
                
                # Obtener profesionales asociados usando ORM
                all_professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                    IndividualSupportPlanProfessionalModel.individual_support_plan_id == isp.id
                ).all()
                # Filtrar en Python los que no están eliminados
                professionals = [p for p in all_professionals if p.deleted_date is None or (hasattr(p.deleted_date, '__bool__') and not bool(p.deleted_date))]
                
                professionals_list = []
                for prof in professionals:
                    professionals_list.append({
                        "id": prof.id,
                        "professional_id": prof.professional_id,
                        "career_type_id": prof.career_type_id,
                        "registration_number": prof.registration_number,
                        "days_hours": prof.days_hours,
                        "from_date": prof.from_date.strftime("%Y-%m-%d") if prof.from_date else None,
                        "to_date": prof.to_date.strftime("%Y-%m-%d") if prof.to_date else None,
                        "support_modality": prof.support_modality
                    })
                
                return {
                    "id": isp.id,
                    "student_id": isp.student_id,
                    "document_type_id": isp.document_type_id,
                    "school_id": isp.school_id,
                    "period_id": isp.period_id,
                    "period_label": _period_label(isp.period_id),
                    "student_full_name": isp.student_full_name,
                    "student_identification_number": isp.student_identification_number,
                    "student_born_date": isp.student_born_date.strftime("%Y-%m-%d") if isp.student_born_date else None,
                    "student_age": isp.student_age,
                    "student_nee_id": isp.student_nee_id,
                    "student_school": isp.student_school,
                    "student_course_id": isp.student_course_id,
                    "elaboration_date": isp.elaboration_date.strftime("%Y-%m-%d") if isp.elaboration_date else None,
                    "social_affective_strengths": isp.social_affective_strengths,
                    "cognitive_strengths": isp.cognitive_strengths,
                    "curricular_strengths": isp.curricular_strengths,
                    "family_strengths": isp.family_strengths,
                    "intervention_ed_diferencial": isp.intervention_ed_diferencial,
                    "intervention_ed_diferencial_strategies": isp.intervention_ed_diferencial_strategies,
                    "intervention_psicopedagogia": isp.intervention_psicopedagogia,
                    "intervention_psicopedagogia_strategies": isp.intervention_psicopedagogia_strategies,
                    "intervention_fonoaudiologia": isp.intervention_fonoaudiologia,
                    "intervention_fonoaudiologia_strategies": isp.intervention_fonoaudiologia_strategies,
                    "intervention_psicologia": isp.intervention_psicologia,
                    "intervention_psicologia_strategies": isp.intervention_psicologia_strategies,
                    "intervention_terapia_ocupacional": isp.intervention_terapia_ocupacional,
                    "intervention_terapia_ocupacional_strategies": isp.intervention_terapia_ocupacional_strategies,
                    "intervention_kinesiologia": isp.intervention_kinesiologia,
                    "intervention_kinesiologia_strategies": isp.intervention_kinesiologia_strategies,
                    "intervention_coeducador_sordo": isp.intervention_coeducador_sordo,
                    "intervention_coeducador_sordo_strategies": isp.intervention_coeducador_sordo_strategies,
                    "intervention_int_lengua_senas": isp.intervention_int_lengua_senas,
                    "intervention_int_lengua_senas_strategies": isp.intervention_int_lengua_senas_strategies,
                    "follow_up_pai": isp.follow_up_pai,
                    "professionals": professionals_list,
                    "added_date": isp.added_date.strftime("%Y-%m-%d %H:%M:%S") if isp.added_date else None,
                    "updated_date": isp.updated_date.strftime("%Y-%m-%d %H:%M:%S") if isp.updated_date else None
                }
            else:
                return {"status": "error", "message": "No se encontraron datos para el Plan de Apoyo Individual del estudiante especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, student_id: Optional[int] = None, school_id: Optional[int] = None) -> Any:
        """
        Obtiene la lista de Planes de Apoyo Individual almacenados.
        Puede filtrarse por student_id y school_id.
        """
        try:
            query = self.db.query(IndividualSupportPlanModel).filter(
                IndividualSupportPlanModel.deleted_date == None
            )

            if student_id is not None:
                query = query.filter(IndividualSupportPlanModel.student_id == student_id)
            
            if school_id is not None:
                query = query.filter(IndividualSupportPlanModel.school_id == school_id)

            isps = query.order_by(IndividualSupportPlanModel.id.desc()).all()

            result = []
            for isp in isps:
                # Obtener profesionales asociados
                professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                    IndividualSupportPlanProfessionalModel.individual_support_plan_id == isp.id,
                    IndividualSupportPlanProfessionalModel.deleted_date.is_(None)
                ).all()
                
                professionals_list = []
                for prof in professionals:
                    professionals_list.append({
                        "id": prof.id,
                        "professional_id": prof.professional_id,
                        "career_type_id": prof.career_type_id,
                        "registration_number": prof.registration_number,
                        "days_hours": prof.days_hours,
                        "from_date": prof.from_date.strftime("%Y-%m-%d") if prof.from_date else None,
                        "to_date": prof.to_date.strftime("%Y-%m-%d") if prof.to_date else None,
                        "support_modality": prof.support_modality
                    })
                
                result.append({
                    "id": isp.id,
                    "student_id": isp.student_id,
                    "document_type_id": isp.document_type_id,
                    "school_id": isp.school_id,
                    "period_id": isp.period_id,
                    "period_label": _period_label(isp.period_id),
                    "student_full_name": isp.student_full_name,
                    "student_identification_number": isp.student_identification_number,
                    "student_born_date": isp.student_born_date.strftime("%Y-%m-%d") if isp.student_born_date else None,
                    "student_age": isp.student_age,
                    "student_nee_id": isp.student_nee_id,
                    "student_school": isp.student_school,
                    "student_course_id": isp.student_course_id,
                    "elaboration_date": isp.elaboration_date.strftime("%Y-%m-%d") if isp.elaboration_date else None,
                    "social_affective_strengths": isp.social_affective_strengths,
                    "cognitive_strengths": isp.cognitive_strengths,
                    "curricular_strengths": isp.curricular_strengths,
                    "family_strengths": isp.family_strengths,
                    "intervention_ed_diferencial": isp.intervention_ed_diferencial,
                    "intervention_ed_diferencial_strategies": isp.intervention_ed_diferencial_strategies,
                    "intervention_psicopedagogia": isp.intervention_psicopedagogia,
                    "intervention_psicopedagogia_strategies": isp.intervention_psicopedagogia_strategies,
                    "intervention_fonoaudiologia": isp.intervention_fonoaudiologia,
                    "intervention_fonoaudiologia_strategies": isp.intervention_fonoaudiologia_strategies,
                    "intervention_psicologia": isp.intervention_psicologia,
                    "intervention_psicologia_strategies": isp.intervention_psicologia_strategies,
                    "intervention_terapia_ocupacional": isp.intervention_terapia_ocupacional,
                    "intervention_terapia_ocupacional_strategies": isp.intervention_terapia_ocupacional_strategies,
                    "intervention_kinesiologia": isp.intervention_kinesiologia,
                    "intervention_kinesiologia_strategies": isp.intervention_kinesiologia_strategies,
                    "intervention_coeducador_sordo": isp.intervention_coeducador_sordo,
                    "intervention_coeducador_sordo_strategies": isp.intervention_coeducador_sordo_strategies,
                    "intervention_int_lengua_senas": isp.intervention_int_lengua_senas,
                    "intervention_int_lengua_senas_strategies": isp.intervention_int_lengua_senas_strategies,
                    "follow_up_pai": isp.follow_up_pai,
                    "professionals": professionals_list,
                    "added_date": isp.added_date.strftime("%Y-%m-%d %H:%M:%S") if isp.added_date else None,
                    "updated_date": isp.updated_date.strftime("%Y-%m-%d %H:%M:%S") if isp.updated_date else None
                })

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, isp_data: dict) -> Any:
        """
        Almacena un nuevo Plan de Apoyo Individual.
        Si ya existe un registro con los mismos student_id, school_id y document_type_id, lo actualiza.
        """
        try:
            # Convertir fechas de string a date si vienen como string
            student_born_date_obj = None
            if isp_data.get('student_born_date'):
                if isinstance(isp_data.get('student_born_date'), str):
                    try:
                        student_born_date_obj = datetime.strptime(isp_data.get('student_born_date'), "%Y-%m-%d").date()
                    except:
                        student_born_date_obj = None
                else:
                    student_born_date_obj = isp_data.get('student_born_date')

            elaboration_date_obj = None
            if isp_data.get('elaboration_date'):
                if isinstance(isp_data.get('elaboration_date'), str):
                    try:
                        elaboration_date_obj = datetime.strptime(isp_data.get('elaboration_date'), "%Y-%m-%d").date()
                    except:
                        elaboration_date_obj = None
                else:
                    elaboration_date_obj = isp_data.get('elaboration_date')

            student_id = isp_data.get('student_id')
            school_id = isp_data.get('school_id')
            document_type_id = isp_data.get('document_type_id')
            period_id = isp_data.get('period_id')
            
            # Buscar si ya existe un registro con estos criterios
            existing_isp = None
            if student_id is not None and school_id is not None and document_type_id is not None:
                q = self.db.query(IndividualSupportPlanModel).filter(
                    IndividualSupportPlanModel.student_id == student_id,
                    IndividualSupportPlanModel.school_id == school_id,
                    IndividualSupportPlanModel.document_type_id == document_type_id,
                    IndividualSupportPlanModel.deleted_date == None
                )
                if period_id is not None:
                    q = q.filter(IndividualSupportPlanModel.period_id == period_id)
                existing_isp = q.first()
            
            # Si existe un registro, hacer update
            if existing_isp:
                # Actualizar campos
                if 'student_id' in isp_data:
                    existing_isp.student_id = isp_data.get('student_id')
                if 'document_type_id' in isp_data:
                    existing_isp.document_type_id = isp_data.get('document_type_id')
                if 'school_id' in isp_data:
                    existing_isp.school_id = isp_data.get('school_id')
                existing_isp.period_id = isp_data.get('period_id')
                if 'student_full_name' in isp_data:
                    existing_isp.student_full_name = isp_data.get('student_full_name')
                if 'student_identification_number' in isp_data:
                    existing_isp.student_identification_number = isp_data.get('student_identification_number')
                if 'student_born_date' in isp_data:
                    existing_isp.student_born_date = student_born_date_obj
                if 'student_age' in isp_data:
                    existing_isp.student_age = isp_data.get('student_age')
                if 'student_nee_id' in isp_data:
                    existing_isp.student_nee_id = isp_data.get('student_nee_id')
                if 'student_school' in isp_data:
                    existing_isp.student_school = isp_data.get('student_school')
                if 'student_course_id' in isp_data:
                    existing_isp.student_course_id = isp_data.get('student_course_id')
                if 'elaboration_date' in isp_data:
                    existing_isp.elaboration_date = elaboration_date_obj
                if 'social_affective_strengths' in isp_data:
                    existing_isp.social_affective_strengths = isp_data.get('social_affective_strengths')
                if 'cognitive_strengths' in isp_data:
                    existing_isp.cognitive_strengths = isp_data.get('cognitive_strengths')
                if 'curricular_strengths' in isp_data:
                    existing_isp.curricular_strengths = isp_data.get('curricular_strengths')
                if 'family_strengths' in isp_data:
                    existing_isp.family_strengths = isp_data.get('family_strengths')
                if 'intervention_ed_diferencial' in isp_data:
                    existing_isp.intervention_ed_diferencial = isp_data.get('intervention_ed_diferencial')
                if 'intervention_ed_diferencial_strategies' in isp_data:
                    existing_isp.intervention_ed_diferencial_strategies = isp_data.get('intervention_ed_diferencial_strategies')
                if 'intervention_psicopedagogia' in isp_data:
                    existing_isp.intervention_psicopedagogia = isp_data.get('intervention_psicopedagogia')
                if 'intervention_psicopedagogia_strategies' in isp_data:
                    existing_isp.intervention_psicopedagogia_strategies = isp_data.get('intervention_psicopedagogia_strategies')
                if 'intervention_fonoaudiologia' in isp_data:
                    existing_isp.intervention_fonoaudiologia = isp_data.get('intervention_fonoaudiologia')
                if 'intervention_fonoaudiologia_strategies' in isp_data:
                    existing_isp.intervention_fonoaudiologia_strategies = isp_data.get('intervention_fonoaudiologia_strategies')
                if 'intervention_psicologia' in isp_data:
                    existing_isp.intervention_psicologia = isp_data.get('intervention_psicologia')
                if 'intervention_psicologia_strategies' in isp_data:
                    existing_isp.intervention_psicologia_strategies = isp_data.get('intervention_psicologia_strategies')
                if 'intervention_terapia_ocupacional' in isp_data:
                    existing_isp.intervention_terapia_ocupacional = isp_data.get('intervention_terapia_ocupacional')
                if 'intervention_terapia_ocupacional_strategies' in isp_data:
                    existing_isp.intervention_terapia_ocupacional_strategies = isp_data.get('intervention_terapia_ocupacional_strategies')
                if 'intervention_kinesiologia' in isp_data:
                    existing_isp.intervention_kinesiologia = isp_data.get('intervention_kinesiologia')
                if 'intervention_kinesiologia_strategies' in isp_data:
                    existing_isp.intervention_kinesiologia_strategies = isp_data.get('intervention_kinesiologia_strategies')
                if 'intervention_coeducador_sordo' in isp_data:
                    existing_isp.intervention_coeducador_sordo = isp_data.get('intervention_coeducador_sordo')
                if 'intervention_coeducador_sordo_strategies' in isp_data:
                    existing_isp.intervention_coeducador_sordo_strategies = isp_data.get('intervention_coeducador_sordo_strategies')
                if 'intervention_int_lengua_senas' in isp_data:
                    existing_isp.intervention_int_lengua_senas = isp_data.get('intervention_int_lengua_senas')
                if 'intervention_int_lengua_senas_strategies' in isp_data:
                    existing_isp.intervention_int_lengua_senas_strategies = isp_data.get('intervention_int_lengua_senas_strategies')
                if 'follow_up_pai' in isp_data:
                    existing_isp.follow_up_pai = isp_data.get('follow_up_pai')
                
                existing_isp.updated_date = datetime.now()
                
                # Manejar profesionales: comparar y actualizar existentes o crear nuevos
                # Solo procesar profesionales si se envía explícitamente el campo
                if 'professionals' in isp_data:
                    professionals_data = isp_data.get('professionals', [])
                    
                    if professionals_data:
                        # Obtener profesionales existentes
                        existing_professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                            IndividualSupportPlanProfessionalModel.individual_support_plan_id == existing_isp.id,
                            IndividualSupportPlanProfessionalModel.deleted_date.is_(None)
                        ).all()
                        
                        # Convertir fechas de los nuevos profesionales
                        processed_professionals = []
                        for prof_data in professionals_data:
                            from_date_obj = None
                            if prof_data.get('from_date'):
                                if isinstance(prof_data.get('from_date'), str):
                                    try:
                                        from_date_obj = datetime.strptime(prof_data.get('from_date'), "%Y-%m-%d").date()
                                    except:
                                        from_date_obj = None
                                else:
                                    from_date_obj = prof_data.get('from_date')

                            to_date_obj = None
                            if prof_data.get('to_date'):
                                if isinstance(prof_data.get('to_date'), str):
                                    try:
                                        to_date_obj = datetime.strptime(prof_data.get('to_date'), "%Y-%m-%d").date()
                                    except:
                                        to_date_obj = None
                                else:
                                    to_date_obj = prof_data.get('to_date')
                            
                            processed_professionals.append({
                                'professional_id': prof_data.get('professional_id'),
                                'career_type_id': prof_data.get('career_type_id'),
                                'registration_number': prof_data.get('registration_number'),
                                'days_hours': prof_data.get('days_hours'),
                                'from_date': from_date_obj,
                                'to_date': to_date_obj,
                                'support_modality': prof_data.get('support_modality')
                            })
                        
                        # Lista de profesionales nuevos que ya fueron procesados (actualizados o creados)
                        processed_existing_ids = []
                        
                        # Para cada profesional nuevo, buscar si existe uno igual
                        for new_prof in processed_professionals:
                            found_match = False
                            
                            for existing_prof in existing_professionals:
                                # Comparar todos los campos para ver si es el mismo profesional
                                if (existing_prof.professional_id == new_prof['professional_id'] and
                                    existing_prof.career_type_id == new_prof['career_type_id'] and
                                    existing_prof.registration_number == new_prof['registration_number'] and
                                    existing_prof.days_hours == new_prof['days_hours'] and
                                    existing_prof.from_date == new_prof['from_date'] and
                                    existing_prof.to_date == new_prof['to_date'] and
                                    existing_prof.support_modality == new_prof['support_modality']):
                                    
                                    # Si todos los campos coinciden, actualizar el existente
                                    existing_prof.professional_id = new_prof['professional_id']
                                    existing_prof.career_type_id = new_prof['career_type_id']
                                    existing_prof.registration_number = new_prof['registration_number']
                                    existing_prof.days_hours = new_prof['days_hours']
                                    existing_prof.from_date = new_prof['from_date']
                                    existing_prof.to_date = new_prof['to_date']
                                    existing_prof.support_modality = new_prof['support_modality']
                                    existing_prof.updated_date = datetime.now()
                                    existing_prof.deleted_date = None  # Asegurar que no esté eliminado
                                    
                                    processed_existing_ids.append(existing_prof.id)
                                    found_match = True
                                    break
                            
                            # Si no se encontró coincidencia, crear nuevo profesional
                            if not found_match:
                                new_professional = IndividualSupportPlanProfessionalModel(
                                    individual_support_plan_id=existing_isp.id,
                                    professional_id=new_prof['professional_id'],
                                    career_type_id=new_prof['career_type_id'],
                                    registration_number=new_prof['registration_number'],
                                    days_hours=new_prof['days_hours'],
                                    from_date=new_prof['from_date'],
                                    to_date=new_prof['to_date'],
                                    support_modality=new_prof['support_modality'],
                                    added_date=datetime.now(),
                                    updated_date=datetime.now()
                                )
                                self.db.add(new_professional)
                        
                        # Eliminar (soft delete) los profesionales existentes que no están en la lista nueva
                        for existing_prof in existing_professionals:
                            if existing_prof.id not in processed_existing_ids:
                                existing_prof.deleted_date = datetime.now()
                                existing_prof.updated_date = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing_isp)
                
                return {
                    "status": "success",
                    "message": "Plan de Apoyo Individual actualizado exitosamente",
                    "id": existing_isp.id
                }
            
            # Si no existe, crear nuevo registro
            new_isp = IndividualSupportPlanModel(
                student_id=isp_data.get('student_id'),
                document_type_id=isp_data.get('document_type_id'),
                school_id=isp_data.get('school_id'),
                period_id=isp_data.get('period_id'),
                student_full_name=isp_data.get('student_full_name'),
                student_identification_number=isp_data.get('student_identification_number'),
                student_born_date=student_born_date_obj,
                student_age=isp_data.get('student_age'),
                student_nee_id=isp_data.get('student_nee_id'),
                student_school=isp_data.get('student_school'),
                student_course_id=isp_data.get('student_course_id'),
                elaboration_date=elaboration_date_obj,
                social_affective_strengths=isp_data.get('social_affective_strengths'),
                cognitive_strengths=isp_data.get('cognitive_strengths'),
                curricular_strengths=isp_data.get('curricular_strengths'),
                family_strengths=isp_data.get('family_strengths'),
                intervention_ed_diferencial=isp_data.get('intervention_ed_diferencial'),
                intervention_ed_diferencial_strategies=isp_data.get('intervention_ed_diferencial_strategies'),
                intervention_psicopedagogia=isp_data.get('intervention_psicopedagogia'),
                intervention_psicopedagogia_strategies=isp_data.get('intervention_psicopedagogia_strategies'),
                intervention_fonoaudiologia=isp_data.get('intervention_fonoaudiologia'),
                intervention_fonoaudiologia_strategies=isp_data.get('intervention_fonoaudiologia_strategies'),
                intervention_psicologia=isp_data.get('intervention_psicologia'),
                intervention_psicologia_strategies=isp_data.get('intervention_psicologia_strategies'),
                intervention_terapia_ocupacional=isp_data.get('intervention_terapia_ocupacional'),
                intervention_terapia_ocupacional_strategies=isp_data.get('intervention_terapia_ocupacional_strategies'),
                intervention_kinesiologia=isp_data.get('intervention_kinesiologia'),
                intervention_kinesiologia_strategies=isp_data.get('intervention_kinesiologia_strategies'),
                intervention_coeducador_sordo=isp_data.get('intervention_coeducador_sordo'),
                intervention_coeducador_sordo_strategies=isp_data.get('intervention_coeducador_sordo_strategies'),
                intervention_int_lengua_senas=isp_data.get('intervention_int_lengua_senas'),
                intervention_int_lengua_senas_strategies=isp_data.get('intervention_int_lengua_senas_strategies'),
                follow_up_pai=isp_data.get('follow_up_pai'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_isp)
            self.db.flush()  # Para obtener el ID del nuevo registro

            # Agregar profesionales si se proporcionan
            professionals_data = isp_data.get('professionals', [])
            if professionals_data:
                for prof_data in professionals_data:
                    from_date_obj = None
                    if prof_data.get('from_date'):
                        if isinstance(prof_data.get('from_date'), str):
                            try:
                                from_date_obj = datetime.strptime(prof_data.get('from_date'), "%Y-%m-%d").date()
                            except:
                                from_date_obj = None
                        else:
                            from_date_obj = prof_data.get('from_date')

                    to_date_obj = None
                    if prof_data.get('to_date'):
                        if isinstance(prof_data.get('to_date'), str):
                            try:
                                to_date_obj = datetime.strptime(prof_data.get('to_date'), "%Y-%m-%d").date()
                            except:
                                to_date_obj = None
                        else:
                            to_date_obj = prof_data.get('to_date')

                    new_professional = IndividualSupportPlanProfessionalModel(
                        individual_support_plan_id=new_isp.id,
                        professional_id=prof_data.get('professional_id'),
                        career_type_id=prof_data.get('career_type_id'),
                        registration_number=prof_data.get('registration_number'),
                        days_hours=prof_data.get('days_hours'),
                        from_date=from_date_obj,
                        to_date=to_date_obj,
                        support_modality=prof_data.get('support_modality'),
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    self.db.add(new_professional)

            self.db.commit()
            self.db.refresh(new_isp)

            return {
                "status": "success",
                "message": "Plan de Apoyo Individual creado exitosamente",
                "id": new_isp.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, id: int, isp_data: dict) -> Any:
        """
        Actualiza un Plan de Apoyo Individual existente.
        """
        try:
            isp = self.db.query(IndividualSupportPlanModel).filter(
                IndividualSupportPlanModel.id == id,
                IndividualSupportPlanModel.deleted_date == None
            ).first()

            if not isp:
                return {
                    "status": "error",
                    "message": "Plan de Apoyo Individual no encontrado"
                }

            # Actualizar campos del Plan de Apoyo Individual
            if 'student_id' in isp_data:
                isp.student_id = isp_data.get('student_id')
            if 'document_type_id' in isp_data:
                isp.document_type_id = isp_data.get('document_type_id')
            if 'school_id' in isp_data:
                isp.school_id = isp_data.get('school_id')
            if 'period_id' in isp_data:
                isp.period_id = isp_data.get('period_id')
            if 'student_full_name' in isp_data:
                isp.student_full_name = isp_data.get('student_full_name')
            if 'student_identification_number' in isp_data:
                isp.student_identification_number = isp_data.get('student_identification_number')
            if 'student_born_date' in isp_data:
                if isinstance(isp_data.get('student_born_date'), str):
                    try:
                        isp.student_born_date = datetime.strptime(isp_data.get('student_born_date'), "%Y-%m-%d").date()
                    except:
                        pass
                else:
                    isp.student_born_date = isp_data.get('student_born_date')
            if 'student_age' in isp_data:
                isp.student_age = isp_data.get('student_age')
            if 'student_nee_id' in isp_data:
                isp.student_nee_id = isp_data.get('student_nee_id')
            if 'student_school' in isp_data:
                isp.student_school = isp_data.get('student_school')
            if 'student_course_id' in isp_data:
                isp.student_course_id = isp_data.get('student_course_id')
            if 'elaboration_date' in isp_data:
                if isinstance(isp_data.get('elaboration_date'), str):
                    try:
                        isp.elaboration_date = datetime.strptime(isp_data.get('elaboration_date'), "%Y-%m-%d").date()
                    except:
                        pass
                else:
                    isp.elaboration_date = isp_data.get('elaboration_date')
            if 'social_affective_strengths' in isp_data:
                isp.social_affective_strengths = isp_data.get('social_affective_strengths')
            if 'cognitive_strengths' in isp_data:
                isp.cognitive_strengths = isp_data.get('cognitive_strengths')
            if 'curricular_strengths' in isp_data:
                isp.curricular_strengths = isp_data.get('curricular_strengths')
            if 'family_strengths' in isp_data:
                isp.family_strengths = isp_data.get('family_strengths')
            if 'intervention_ed_diferencial' in isp_data:
                isp.intervention_ed_diferencial = isp_data.get('intervention_ed_diferencial')
            if 'intervention_ed_diferencial_strategies' in isp_data:
                isp.intervention_ed_diferencial_strategies = isp_data.get('intervention_ed_diferencial_strategies')
            if 'intervention_psicopedagogia' in isp_data:
                isp.intervention_psicopedagogia = isp_data.get('intervention_psicopedagogia')
            if 'intervention_psicopedagogia_strategies' in isp_data:
                isp.intervention_psicopedagogia_strategies = isp_data.get('intervention_psicopedagogia_strategies')
            if 'intervention_fonoaudiologia' in isp_data:
                isp.intervention_fonoaudiologia = isp_data.get('intervention_fonoaudiologia')
            if 'intervention_fonoaudiologia_strategies' in isp_data:
                isp.intervention_fonoaudiologia_strategies = isp_data.get('intervention_fonoaudiologia_strategies')
            if 'intervention_psicologia' in isp_data:
                isp.intervention_psicologia = isp_data.get('intervention_psicologia')
            if 'intervention_psicologia_strategies' in isp_data:
                isp.intervention_psicologia_strategies = isp_data.get('intervention_psicologia_strategies')
            if 'intervention_terapia_ocupacional' in isp_data:
                isp.intervention_terapia_ocupacional = isp_data.get('intervention_terapia_ocupacional')
            if 'intervention_terapia_ocupacional_strategies' in isp_data:
                isp.intervention_terapia_ocupacional_strategies = isp_data.get('intervention_terapia_ocupacional_strategies')
            if 'intervention_kinesiologia' in isp_data:
                isp.intervention_kinesiologia = isp_data.get('intervention_kinesiologia')
            if 'intervention_kinesiologia_strategies' in isp_data:
                isp.intervention_kinesiologia_strategies = isp_data.get('intervention_kinesiologia_strategies')
            if 'intervention_coeducador_sordo' in isp_data:
                isp.intervention_coeducador_sordo = isp_data.get('intervention_coeducador_sordo')
            if 'intervention_coeducador_sordo_strategies' in isp_data:
                isp.intervention_coeducador_sordo_strategies = isp_data.get('intervention_coeducador_sordo_strategies')
            if 'intervention_int_lengua_senas' in isp_data:
                isp.intervention_int_lengua_senas = isp_data.get('intervention_int_lengua_senas')
            if 'intervention_int_lengua_senas_strategies' in isp_data:
                isp.intervention_int_lengua_senas_strategies = isp_data.get('intervention_int_lengua_senas_strategies')
            if 'follow_up_pai' in isp_data:
                isp.follow_up_pai = isp_data.get('follow_up_pai')

            isp.updated_date = datetime.now()

            # Actualizar profesionales si se proporcionan
            if 'professionals' in isp_data:
                # Eliminar profesionales existentes (soft delete)
                existing_professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                    IndividualSupportPlanProfessionalModel.individual_support_plan_id == id,
                    IndividualSupportPlanProfessionalModel.deleted_date == None
                ).all()
                
                for existing_prof in existing_professionals:
                    existing_prof.deleted_date = datetime.now()

                # Agregar nuevos profesionales
                professionals_data = isp_data.get('professionals', [])
                for prof_data in professionals_data:
                    from_date_obj = None
                    if prof_data.get('from_date'):
                        if isinstance(prof_data.get('from_date'), str):
                            try:
                                from_date_obj = datetime.strptime(prof_data.get('from_date'), "%Y-%m-%d").date()
                            except:
                                from_date_obj = None
                        else:
                            from_date_obj = prof_data.get('from_date')

                    to_date_obj = None
                    if prof_data.get('to_date'):
                        if isinstance(prof_data.get('to_date'), str):
                            try:
                                to_date_obj = datetime.strptime(prof_data.get('to_date'), "%Y-%m-%d").date()
                            except:
                                to_date_obj = None
                        else:
                            to_date_obj = prof_data.get('to_date')

                    new_professional = IndividualSupportPlanProfessionalModel(
                        individual_support_plan_id=id,
                        professional_id=prof_data.get('professional_id'),
                        career_type_id=prof_data.get('career_type_id'),
                        registration_number=prof_data.get('registration_number'),
                        days_hours=prof_data.get('days_hours'),
                        from_date=from_date_obj,
                        to_date=to_date_obj,
                        support_modality=prof_data.get('support_modality'),
                        added_date=datetime.now(),
                        updated_date=datetime.now()
                    )
                    self.db.add(new_professional)

            self.db.commit()
            self.db.refresh(isp)

            return {
                "status": "success",
                "message": "Plan de Apoyo Individual actualizado exitosamente",
                "id": isp.id
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, id: int) -> Any:
        """
        Elimina lógicamente un Plan de Apoyo Individual (soft delete).
        También elimina los profesionales asociados.
        """
        try:
            isp = self.db.query(IndividualSupportPlanModel).filter(
                IndividualSupportPlanModel.id == id,
                IndividualSupportPlanModel.deleted_date == None
            ).first()

            if not isp:
                return {
                    "status": "error",
                    "message": "Plan de Apoyo Individual no encontrado"
                }

            # Soft delete del Plan de Apoyo Individual
            isp.deleted_date = datetime.now()
            isp.updated_date = datetime.now()

            # Soft delete de profesionales asociados
            professionals = self.db.query(IndividualSupportPlanProfessionalModel).filter(
                IndividualSupportPlanProfessionalModel.individual_support_plan_id == id,
                IndividualSupportPlanProfessionalModel.deleted_date == None
            ).all()

            for prof in professionals:
                prof.deleted_date = datetime.now()
                prof.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Plan de Apoyo Individual eliminado exitosamente"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
