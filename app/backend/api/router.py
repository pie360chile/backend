"""Registro centralizado de routers (evita que main.py crezca sin límite)."""

from __future__ import annotations

from fastapi import FastAPI

from app.backend.routes.actions_incidents import actions_incidents
from app.backend.routes.anamnesis import anamnesis
from app.backend.routes.app_alerts import alerts
from app.backend.routes.audits import audits
from app.backend.routes.authentications import authentications
from app.backend.routes.bank_descriptions import bank_descriptions
from app.backend.routes.career_types import career_types
from app.backend.routes.cesp import cesp
from app.backend.routes.collaborative_works import collaborative_works
from app.backend.routes.communes import communes
from app.backend.routes.conners_teacher_evaluations import conners_teacher_evaluations
from app.backend.routes.contacts import contacts
from app.backend.routes.coordinators_courses import coordinators_courses
from app.backend.routes.course_activity_records import course_activity_records
from app.backend.routes.course_adjustments import course_adjustments
from app.backend.routes.course_curricular_adequacies import course_curricular_adequacies
from app.backend.routes.course_diversity_responses import course_diversity_responses
from app.backend.routes.course_eval_diversity import course_eval_diversity
from app.backend.routes.course_family_community import course_family_community
from app.backend.routes.course_individual_supports import course_individual_supports
from app.backend.routes.course_learning_achievements import course_learning_achievements
from app.backend.routes.course_record_supports import course_record_supports
from app.backend.routes.course_teacher_record_activities import course_teacher_record_activities
from app.backend.routes.course_teacher_record_observations import course_teacher_record_observations
from app.backend.routes.courses import courses
from app.backend.routes.curriculum_subjects import curriculum_subjects
from app.backend.routes.customers import customers
from app.backend.routes.diagnosis_summary import diagnosis_summary
from app.backend.routes.document_41_reports import document_41_reports
from app.backend.routes.differentiated_strategies_implementations import (
    differentiated_strategies_implementations,
)
from app.backend.routes.diversified_strategies import diversified_strategies
from app.backend.routes.diversity_criteria import diversity_criteria
from app.backend.routes.diversity_strategy_options import diversity_strategy_options
from app.backend.routes.document_alerts import document_alerts
from app.backend.routes.document_evalua_result_reports import document_evalua_result_reports
from app.backend.routes.document_types import document_types
from app.backend.routes.documents import documents
from app.backend.routes.downloads import downloads
from app.backend.routes.dynamic_forms import dynamic_forms
from app.backend.routes.external_api import external_api
from app.backend.routes.family_members import family_members
from app.backend.routes.family_reports import family_reports
from app.backend.routes.faqs import faqs
from app.backend.routes.folders import folders
from app.backend.routes.fonoaudiological_reports import fonoaudiological_reports
from app.backend.routes.fur_forms import fur_forms
from app.backend.routes.genders import genders
from app.backend.routes.guardian_attendance_certificates import guardian_attendance_certificates
from app.backend.routes.health_evaluations import health_evaluations
from app.backend.routes.idtel_reports import idtel_reports
from app.backend.routes.individual_curriculum_adaptation_plans import (
    individual_curriculum_adaptation_plans,
)
from app.backend.routes.individual_support_plans import individual_support_plans
from app.backend.routes.informal_test_templates import informal_test_templates
from app.backend.routes.interconsultations import interconsultations
from app.backend.routes.kpi_document_assignments import kpi_document_assignments
from app.backend.routes.kpi_documentation_progress import kpi_documentation_progress
from app.backend.routes.learning_objectives import learning_objectives
from app.backend.routes.meeting_schedualing_agreements import meeting_schedualing_agreements
from app.backend.routes.meeting_schedualing_register_professionals import (
    meeting_schedualing_register_professionals,
)
from app.backend.routes.meeting_schedualings import meeting_schedualings
from app.backend.routes.messages import messages
from app.backend.routes.nationalities import nationalities
from app.backend.routes.native_language_proficiencies import native_language_proficiencies
from app.backend.routes.news import news
from app.backend.routes.packages import packages
from app.backend.routes.pedagogical_evaluation_classroom_eighth_grade import (
    pedagogical_evaluation_classroom_eighth_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_fifth_grade import (
    pedagogical_evaluation_classroom_fifth_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_first_grade import (
    pedagogical_evaluation_classroom_first_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_first_grade_secondary import (
    pedagogical_evaluation_classroom_first_grade_secondary,
)
from app.backend.routes.pedagogical_evaluation_classroom_fourth_grade import (
    pedagogical_evaluation_classroom_fourth_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_second_grade import (
    pedagogical_evaluation_classroom_second_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_second_grade_secondary import (
    pedagogical_evaluation_classroom_second_grade_secondary,
)
from app.backend.routes.pedagogical_evaluation_classroom_seventh_grade import (
    pedagogical_evaluation_classroom_seventh_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_sixth_grade import (
    pedagogical_evaluation_classroom_sixth_grade,
)
from app.backend.routes.pedagogical_evaluation_classroom_third_grade import (
    pedagogical_evaluation_classroom_third_grade,
)
from app.backend.routes.permissions import permissions
from app.backend.routes.plan_apoyo_individual import plan_apoyo_individual
from app.backend.routes.professional_document_assignments import professional_document_assignments
from app.backend.routes.professional_teaching_courses import professional_teaching_courses
from app.backend.routes.professionals import professionals
from app.backend.routes.progress_status_individual_supports import progress_status_individual_supports
from app.backend.routes.progress_status_students import progress_status_students
from app.backend.routes.provinces import provinces
from app.backend.routes.psychomotor_evaluation_reports import psychomotor_evaluation_reports
from app.backend.routes.psychopedagogical_evaluations import psychopedagogical_evaluations
from app.backend.routes.regions import regions
from app.backend.routes.regular_teacher_diversified_strategies import (
    regular_teacher_diversified_strategies,
)
from app.backend.routes.rols import rols
from app.backend.routes.school_integration_program_exit_certificates import (
    school_integration_program_exit_certificates,
)
from app.backend.routes.schools import schools
from app.backend.routes.settings import settings
from app.backend.routes.special_educational_needs import special_educational_needs
from app.backend.routes.agent_files import agent_files
from app.backend.routes.agents import agents
from app.backend.routes.student_document_files import student_document_files
from app.backend.routes.student_guardians import student_guardians
from app.backend.routes.students import students
from app.backend.routes.students_professionals import students_professionals
from app.backend.routes.subjects import subjects
from app.backend.routes.support_areas import support_areas
from app.backend.routes.support_organizations import support_organizations
from app.backend.routes.teachings import teachings
from app.backend.routes.users import users
from app.backend.routes.videos import videos
from app.backend.routes.events import events


def register_routers(app: FastAPI) -> None:
    """Monta todos los routers de dominio. Mantener orden estable para diffs legibles."""
    routers = (
        authentications,
        rols,
        permissions,
        settings,
        users,
        teachings,
        courses,
        communes,
        regions,
        provinces,
        native_language_proficiencies,
        documents,
        family_members,
        news,
        external_api,
        nationalities,
        genders,
        schools,
        students,
        students_professionals,
        document_alerts,
        customers,
        professionals,
        packages,
        student_guardians,
        special_educational_needs,
        document_types,
        messages,
        actions_incidents,
        downloads,
        videos,
        career_types,
        faqs,
        contacts,
        student_document_files,
        agent_files,
        agents,
        folders,
        health_evaluations,
        events,
        bank_descriptions,
        progress_status_students,
        individual_support_plans,
        individual_curriculum_adaptation_plans,
        progress_status_individual_supports,
        fonoaudiological_reports,
        school_integration_program_exit_certificates,
        audits,
        anamnesis,
        family_reports,
        interconsultations,
        guardian_attendance_certificates,
        professional_teaching_courses,
        professional_document_assignments,
        alerts,
        kpi_document_assignments,
        kpi_documentation_progress,
        coordinators_courses,
        meeting_schedualings,
        meeting_schedualing_agreements,
        meeting_schedualing_register_professionals,
        diversified_strategies,
        regular_teacher_diversified_strategies,
        subjects,
        learning_objectives,
        curriculum_subjects,
        collaborative_works,
        support_organizations,
        diversity_criteria,
        diversity_strategy_options,
        course_diversity_responses,
        course_adjustments,
        course_curricular_adequacies,
        course_individual_supports,
        plan_apoyo_individual,
        course_eval_diversity,
        course_family_community,
        support_areas,
        dynamic_forms,
        differentiated_strategies_implementations,
        course_teacher_record_observations,
        course_teacher_record_activities,
        course_activity_records,
        course_record_supports,
        course_learning_achievements,
        psychopedagogical_evaluations,
        conners_teacher_evaluations,
        diagnosis_summary,
        document_41_reports,
        cesp,
        idtel_reports,
        fur_forms,
        psychomotor_evaluation_reports,
        pedagogical_evaluation_classroom_first_grade,
        pedagogical_evaluation_classroom_second_grade,
        pedagogical_evaluation_classroom_third_grade,
        pedagogical_evaluation_classroom_fourth_grade,
        pedagogical_evaluation_classroom_fifth_grade,
        pedagogical_evaluation_classroom_sixth_grade,
        pedagogical_evaluation_classroom_seventh_grade,
        pedagogical_evaluation_classroom_eighth_grade,
        pedagogical_evaluation_classroom_first_grade_secondary,
        pedagogical_evaluation_classroom_second_grade_secondary,
        informal_test_templates,
        document_evalua_result_reports,
    )

    for router in routers:
        app.include_router(router)

    # Rutas duplicadas bajo /api (front con VITE_API_URL = http://host:port/api)
    app.include_router(documents, prefix="/api")
    app.include_router(individual_curriculum_adaptation_plans, prefix="/api")
    app.include_router(document_evalua_result_reports, prefix="/api")
    app.include_router(agent_files, prefix="/api")
    app.include_router(agents, prefix="/api")
