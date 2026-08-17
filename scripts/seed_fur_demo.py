# -*- coding: utf-8 -*-
"""Carga un FUR (documento 6) de demostración con datos inventados.

Uso:
    python -m scripts.seed_fur_demo [student_id] [fur_variant]

Pensado para dejar el formulario al 100% en ambientes de prueba. No escribe
datos de identidad del estudiante: el frontend los rellena desde su ficha, y
sobrescribirlos con texto inventado los borraría al abrir el formulario.
"""

from __future__ import annotations

import sys
from datetime import date

from sqlalchemy import text

from app.backend.classes.fur_form_class import FurFormClass
from app.backend.classes.professional_class import ProfessionalClass
from app.backend.db.database import SessionLocal
from app.backend.db.models.pie_core import FurFormModel

STUDENT_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 5453
FUR_VARIANT = sys.argv[2] if len(sys.argv) > 2 else "dea"
DOCUMENT_TYPE_ID = 6

# Claves que el formulario deriva de la ficha del estudiante. Si viajan en el
# payload, applyFurResponse() las sobrescribe con lo que guardemos aquí.
# establishment_name y director_name no entran aquí: el endpoint de estudiantes
# no devuelve el nombre del establecimiento, así que son propias del FUR.
STUDENT_OWNED_KEYS = frozenset(
    {
        "full_name",
        "born_date",
        "age",
        "identification_number",
        "current_course",
    }
)


def demo_professional_rows(db, school_id: int | None, period_year: str, wanted: int = 4) -> list[dict]:
    """Filas de profesionales usando IDs reales del selector, con contacto ficticio."""
    rows: list[dict] = []
    try:
        result = ProfessionalClass(db).get_all(
            page=1,
            items_per_page=50,
            school_id=school_id,
            period_year=period_year,
        )
        candidates = result.get("data", []) if isinstance(result, dict) else (result or [])
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] no se pudo listar profesionales: {exc}")
        candidates = []

    for index, item in enumerate(candidates[:wanted]):
        rows.append(
            {
                "professional_id": item.get("id"),
                "profession_id": item.get("career_type_id") or ((index % 5) + 1),
                "phone_email": f"+56 9 5555 10{index + 10} / demo.pie{index + 1}@ejemplo.cl",
                "professional_registration": f"REG-DEMO-{4100 + index}",
            }
        )

    while len(rows) < wanted:
        rows.append(
            {
                "professional_id": None,
                "profession_id": None,
                "phone_email": "",
                "professional_registration": "",
            }
        )
    return rows


def school_header(db, school_id: int | None) -> dict:
    """Nombre y director del establecimiento: el FUR los guarda, la ficha no los entrega."""
    if school_id is None:
        return {}
    row = db.execute(
        text("SELECT school_name, director_name FROM schools WHERE id = :i"),
        {"i": school_id},
    ).mappings().first()
    if not row:
        return {}
    return {
        "establishment_name": row["school_name"] or "",
        "director_name": row["director_name"] or "",
    }


def build_demo_form_data(lead_professional_id: int | None, lead_profession_id: int | None) -> dict:
    year = date.today().year
    return {
        # --- Identificación del proceso ---
        "in_pie_since": year - 3,
        "current_year": year,
        "revaluation_type": "proceso",
        "registration_date": date.today().strftime("%d/%m/%Y"),
        # --- Profesional responsable ---
        "professional_id": lead_professional_id,
        "profession_specialty_id": lead_profession_id,
        "professional_identification_number": "16.482.375-9",
        "contact_phone": "+56 9 5555 1010",
        "contact_email": "coordinacion.pie@ejemplo.cl",
        "professional_signature": "Coordinación PIE – Equipo de revaluación",
        # --- Diagnóstico y síntesis ---
        "nee_is_dea": True,
        "current_diagnosis_issue_date": f"{year - 1}-11-18",
        "current_revaluation_date": f"{year}-07-29",
        "diagnosis_changed_from_admission": "no",
        "new_evaluations_revaluations": (
            "Durante el período se aplicó revaluación psicopedagógica completa (EVALÚA y pruebas "
            "informales de lectura, escritura y cálculo), revaluación psicológica con foco en "
            "funciones ejecutivas y una evaluación pedagógica de aula. Se sumó informe de la "
            "profesora jefe y entrevista de seguimiento a la familia. El diagnóstico de DEA se "
            "mantiene, sin modificaciones respecto del ingreso; las evidencias quedan adjuntas en "
            "la carpeta del estudiante."
        ),
        "new_diagnosis_professional_data": (
            "Revaluación realizada por la educadora diferencial del equipo PIE, con apoyo de "
            "psicología del establecimiento. Registro profesional vigente."
        ),
        "student_educational_progress_sen": (
            "El estudiante muestra avances sostenidos en el período. Pasó de una lectura silábica "
            "vacilante a una lectura fluida en textos de su nivel, con comprensión literal "
            "consolidada e inferencial en desarrollo. En escritura organiza párrafos con inicio y "
            "cierre, aunque persisten errores ortográficos de regla. En matemática resuelve "
            "problemas de dos operaciones con apoyo de material concreto. Participa con mayor "
            "iniciativa en trabajos grupales y solicita ayuda cuando lo necesita."
        ),
        "main_difficulty_areas_summary": (
            "Las principales dificultades persisten en la velocidad y precisión de la lectura de "
            "palabras poco frecuentes, en la ortografía reglada y en la memoria de trabajo cuando "
            "debe sostener varias instrucciones a la vez. En matemática requiere apoyo para el "
            "cálculo mental y para la interpretación de enunciados extensos. Estas dificultades se "
            "expresan sobre todo en evaluaciones escritas con tiempo acotado."
        ),
        "nee_synthesis_observations": (
            "Se mantiene la necesidad de apoyos en aula común, con énfasis en tiempo adicional y "
            "mediación lectora. La familia acompaña el proceso de manera constante."
        ),
        "nee_maintained": "si",
        "requires_specialized_support": "si",
        # --- Evidencias ---
        "evidence_anamnesis": True,
        "evidence_family_interview": True,
        "evidence_observation_guideline": True,
        "evidence_evaluation_protocols": True,
        "evidence_report_school": True,
        "evidence_report_psychological": True,
        "evidence_report_pedagogical": True,
        "evidence_report_psychopedagogical": True,
        "evidence_learning_evaluation": True,
        "evidence_general_health_exam": True,
        "evidence_documents_count": "9",
        # --- Revaluación especializada (psicoeducativa) ---
        "specialized_curriculum_participation_evolution": (
            "Durante el período aumentó progresivamente su participación en las actividades "
            "curriculares. Actualmente inicia las tareas con mayor autonomía, sostiene el trabajo "
            "por más tiempo y utiliza los apoyos visuales y organizadores gráficos de manera "
            "funcional. Requiere mediación principalmente ante textos extensos y problemas de "
            "varios pasos."
        ),
        "specialized_curricular_achievements": (
            "Logró los objetivos priorizados de Lenguaje en comprensión de textos narrativos e "
            "informativos breves, y en producción de textos con estructura básica. En Matemática "
            "consolidó adición y sustracción con reserva, y avanzó en multiplicación. En Ciencias e "
            "Historia alcanza los aprendizajes con apoyo de organizadores gráficos."
        ),
        "specialized_unachieved_learning": (
            "Mantiene dificultades en ortografía literal y acentual, en la lectura de textos "
            "extensos sin mediación y en la resolución de problemas matemáticos de varios pasos. "
            "La escritura autónoma de textos largos continúa siendo un desafío."
        ),
        "specialized_learning_participation_progress": (
            "Presenta avances en la planificación de tareas, la solicitud oportuna de ayuda y la "
            "participación en actividades grupales. Sigue instrucciones segmentadas, respeta "
            "turnos y comunica sus dudas con mayor seguridad tanto en el aula común como en el "
            "aula de recursos."
        ),
        "specialized_context_participation": (
            "Participa activamente en clases y en actividades del curso. Se relaciona bien con sus "
            "pares y ha asumido roles de responsabilidad en trabajos grupales. En el hogar cumple "
            "con las rutinas de estudio acordadas, con supervisión de su madre."
        ),
        "specialized_barriers_reduction": (
            "El curso trabaja con instrucciones visuales y rutinas estables. El establecimiento "
            "habilitó tiempo adicional en evaluaciones y co-enseñanza en Lenguaje y Matemática, lo "
            "que redujo significativamente las barreras de acceso."
        ),
        "specialized_family_participation": (
            "La familia asiste a todas las entrevistas, refuerza la lectura diaria en casa y "
            "mantiene comunicación permanente con la educadora diferencial."
        ),
        "specialized_next_period_emphasis": (
            "Dar énfasis a la ortografía reglada, a la autonomía en la lectura de textos extensos y "
            "a estrategias de autorregulación para evaluaciones escritas."
        ),
        "specialized_dea_literacy_math_progress": (
            "En lectura aumentó su fluidez y hoy lee textos de su nivel sin apoyo silábico. En "
            "escritura mejoró la estructura y la legibilidad, con ortografía aún en proceso. En "
            "matemática comprende el valor posicional y resuelve problemas de dos pasos con "
            "material concreto."
        ),
        "specialized_next_period_reading": (
            "Continuar el trabajo de fluidez con lectura repetida y ampliar la comprensión "
            "inferencial mediante preguntas guiadas."
        ),
        "specialized_next_period_writing": (
            "Reforzar ortografía reglada y revisión autónoma del propio texto con pauta de cotejo."
        ),
        "specialized_next_period_math": (
            "Afianzar cálculo mental y el análisis de enunciados con apoyo de esquemas."
        ),
        "specialized_next_period_other": (
            "Fortalecer hábitos de estudio, organización de materiales y autorregulación del tiempo."
        ),
        "specialized_tab_observations": (
            "El estudiante responde muy bien a la mediación individual breve. Se sugiere mantener el "
            "apoyo en aula común y las adecuaciones de acceso ya implementadas."
        ),
        "specialized_revaluation_date": f"{year}-07-29",
        "specialized_revaluation_synthesis": (
            "La revaluación confirma progresos significativos en lectura y en participación escolar, "
            "con dificultades persistentes en ortografía y en resolución de problemas matemáticos "
            "complejos. Se mantiene el diagnóstico de DEA y la necesidad de apoyos especializados "
            "en aula común para el próximo período."
        ),
        "specialized_revaluation_conclusions": (
            "Se recomienda continuidad en el PIE con apoyo de educación diferencial en Lenguaje y "
            "Matemática, manteniendo las adecuaciones de acceso vigentes."
        ),
        "specialized_revaluation_observations": (
            "Todos los instrumentos aplicados y sus protocolos quedan archivados en la carpeta del "
            "estudiante."
        ),
        "psychological_revaluation_date": f"{year}-07-15",
        "psychological_revaluation_results": (
            "Capacidad intelectual en rango promedio. Atención sostenida mejorada respecto de la "
            "evaluación anterior; memoria de trabajo en rango bajo el promedio."
        ),
        "psychological_revaluation_instruments": "WISC-V, entrevista clínica, pauta de observación en aula.",
        "psychological_revaluation_recommendations": (
            "Mantener instrucciones segmentadas, apoyos visuales y refuerzo positivo frente al logro."
        ),
        "pedagogical_revaluation_date": f"{year}-07-22",
        "pedagogical_revaluation_results": (
            "Alcanza los objetivos priorizados de su nivel con apoyo de mediación y tiempo "
            "adicional en evaluaciones escritas."
        ),
        "pedagogical_revaluation_instruments": "Pruebas de nivel, portafolio de trabajos, registro de aula.",
        "pedagogical_revaluation_recommendations": (
            "Continuar con co-enseñanza en Lenguaje y Matemática, y evaluación diferenciada."
        ),
        "other_evaluations": (
            "No se requirieron evaluaciones de terapia ocupacional ni kinesiología en este período."
        ),
        # --- Áreas de apoyo ---
        "support_area_curricular_general": True,
        "support_area_specific_subjects": True,
        "support_area_affective_social": True,
        "support_area_cognitive_functions": True,
        "support_area_executive_functions": True,
        # --- Tabla de evaluación de apoyos (celdas <= 100 caracteres) ---
        "support_personal_specific": "Apoyo de educadora diferencial en aula, 6 horas semanales",
        "support_personal_effectiveness": "Alta: mejora sostenida en lectura y participación",
        "support_personal_continuity": "si",
        "support_personal_observations": "Mantener mediación individual breve antes de cada evaluación",
        "support_curricular_specific": "Adecuaciones de acceso y priorización de objetivos",
        "support_curricular_effectiveness": "Alta: alcanza los objetivos priorizados del nivel",
        "support_curricular_continuity": "si",
        "support_curricular_observations": "Revisar priorización al inicio del próximo semestre",
        "support_materials_specific": "Textos adaptados, organizadores gráficos y material concreto",
        "support_materials_effectiveness": "Media-alta: mejor comprensión con apoyo visual",
        "support_materials_continuity": "si",
        "support_materials_observations": "Incorporar audiolibros para textos extensos",
        "support_organizational_specific": "Tiempo adicional y ubicación preferente en la sala",
        "support_organizational_effectiveness": "Alta: disminuye la ansiedad ante pruebas escritas",
        "support_organizational_continuity": "si",
        "support_organizational_observations": "Coordinar calendario de evaluaciones con el equipo de aula",
        "support_family_specific": "Entrevistas mensuales y plan de lectura diaria en casa",
        "support_family_effectiveness": "Alta: la familia cumple el plan acordado",
        "support_family_continuity": "si",
        "support_family_observations": "Mantener la frecuencia mensual de entrevistas",
        "support_social_specific": "Trabajo colaborativo en parejas y tutoría entre pares",
        "support_social_effectiveness": "Alta: mejor integración con el grupo curso",
        "support_social_continuity": "si",
        "support_social_observations": "Rotar las parejas de trabajo para ampliar vínculos",
        "support_other_specific": "Taller de hábitos de estudio en jornada alterna",
        "support_other_effectiveness": "Media: asistencia irregular por transporte",
        "support_other_continuity": "no",
        "support_other_observations": "Evaluar horario alternativo para el próximo año",
        "support_work_strategies": (
            "El equipo de aula trabajó con co-enseñanza en Lenguaje y Matemática, planificación "
            "compartida semanal y monitoreo con pautas de cotejo. Resultaron especialmente "
            "efectivas la anticipación de instrucciones, la segmentación de tareas en pasos, el uso "
            "de organizadores gráficos y la retroalimentación inmediata. La tutoría entre pares y el "
            "apoyo de la asistente de aula permitieron sostener el trabajo autónomo del estudiante."
        ),
        "support_family_strategies_effectiveness": (
            "Las estrategias hacia la familia fueron efectivas: el plan de lectura diaria y las "
            "entrevistas mensuales generaron rutinas estables en el hogar y mayor autonomía en las "
            "tareas. Para el período siguiente se recomienda mantener la lectura diaria, incorporar "
            "revisión conjunta de la agenda escolar y reforzar el uso de una pauta simple de "
            "autocorrección ortográfica."
        ),
        "support_new_needs_required": (
            "El estudiante requiere nuevos apoyos focalizados en ortografía reglada y en la lectura "
            "autónoma de textos extensos: acceso a audiolibros, una pauta de autocorrección y "
            "trabajo sistemático de reglas ortográficas en grupos pequeños. En matemática necesita "
            "apoyo específico para el análisis de enunciados de varios pasos. No se requieren "
            "apoyos nuevos en el área social ni de autonomía."
        ),
        "support_next_period_comments": (
            "El estudiante será promovido de curso considerando el logro de los objetivos "
            "priorizados y sus progresos sostenidos en lectura, escritura y matemática. Se propone "
            "su continuidad en el PIE por un período más, manteniendo el apoyo de educación "
            "diferencial en aula común y las adecuaciones de acceso vigentes, con revisión al "
            "término del primer semestre."
        ),
        # --- Revaluación de egreso o continuidad ---
        "exit_dea_deficit_evaluation": (
            "Se aplicaron pruebas de lectura (fluidez y comprensión), escritura al dictado y "
            "espontánea, y cálculo, junto a pruebas informales de conciencia fonológica. Los "
            "resultados muestran mejoría en fluidez lectora y comprensión literal, con desempeño "
            "bajo lo esperado en ortografía y en resolución de problemas de varios pasos. El perfil "
            "es consistente con una dificultad específica del aprendizaje que persiste, aunque con "
            "menor impacto funcional que en la evaluación de ingreso. Todas las evidencias y "
            "protocolos quedan adjuntos."
        ),
        "decision_school_year": year,
        "exit_team_decision_period": "anual",
        "decision_type": "continuidad",
        "decision_date": f"{year}-08-05",
        "decision_rationale": (
            "El equipo fundamenta la continuidad en el PIE en que, si bien el estudiante presenta "
            "progresos significativos en lectura, participación y autonomía, persisten dificultades "
            "en ortografía reglada, en la lectura autónoma de textos extensos y en la resolución de "
            "problemas matemáticos de varios pasos que continúan requiriendo apoyos especializados "
            "para acceder al currículum en igualdad de condiciones. La revaluación psicopedagógica, "
            "psicológica y pedagógica converge en este diagnóstico, y el retiro de los apoyos en "
            "esta etapa pondría en riesgo los logros alcanzados. Se acuerda revisar la decisión al "
            "término del primer semestre del próximo año."
        ),
        "decision_recommendations": (
            "Mantener apoyo de educación diferencial en aula común, adecuaciones de acceso y "
            "evaluación diferenciada."
        ),
        "next_evaluation_date": f"{year + 1}-07-15",
        "guardian_informed_date": f"{year}-08-08",
        "decision_observations": (
            "La decisión fue informada al apoderado, quien manifiesta su acuerdo y compromiso de "
            "continuar con el plan de lectura en el hogar. Se entregó copia del acta y se explicaron "
            "los apoyos que recibirá el estudiante durante el próximo período escolar, así como los "
            "hitos de seguimiento acordados por el equipo."
        ),
    }


def main() -> None:
    db = SessionLocal()
    try:
        existing = (
            db.query(FurFormModel)
            .filter(
                FurFormModel.student_id == STUDENT_ID,
                FurFormModel.fur_variant == FUR_VARIANT,
            )
            .order_by(FurFormModel.id.desc())
            .first()
        )

        school_id = existing.school_id if existing and existing.school_id else None
        if school_id is None:
            row = db.execute(
                text("SELECT school_id, period_year FROM students WHERE id = :i"),
                {"i": STUDENT_ID},
            ).mappings().first()
            if not row:
                raise SystemExit(f"El estudiante {STUDENT_ID} no existe.")
            school_id = row["school_id"]
            period_year = str(row["period_year"] or date.today().year)
        else:
            period_year = str(date.today().year)

        professional_rows = demo_professional_rows(db, school_id, period_year)
        lead = next((r for r in professional_rows if r["professional_id"]), None)

        form_data = build_demo_form_data(
            lead["professional_id"] if lead else None,
            lead["profession_id"] if lead else None,
        )
        form_data.update(school_header(db, school_id))
        form_data = {k: v for k, v in form_data.items() if v is not None and k not in STUDENT_OWNED_KEYS}
        form_data["participating_professionals"] = professional_rows
        form_data["exit_revaluation_professionals"] = [dict(r) for r in professional_rows]

        payload = {
            "student_id": STUDENT_ID,
            "school_id": school_id,
            "document_type_id": DOCUMENT_TYPE_ID,
            "fur_variant": FUR_VARIANT,
            **form_data,
        }

        klass = FurFormClass(db)
        if existing:
            result = klass.update(existing.id, payload)
            action = f"actualizado (id={existing.id})"
        else:
            result = klass.store(payload)
            action = f"creado (id={result.get('id')})"

        if result.get("status") != "success":
            raise SystemExit(f"Error al guardar: {result.get('message')}")

        filled_professionals = sum(1 for r in professional_rows if r["professional_id"])
        print(
            f"FUR {FUR_VARIANT} {action} para el estudiante {STUDENT_ID} "
            f"(school_id={school_id}, {len(form_data)} campos, "
            f"{filled_professionals} profesionales con ID real)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
