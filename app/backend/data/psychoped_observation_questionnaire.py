"""Cuestionario de observación en aula (informe psicopedagógico)."""

from __future__ import annotations

SCALE_OPTIONS = [
    {"label": "LOGRADO", "value": "LOGRADO"},
    {"label": "EN PROCESO", "value": "EN PROCESO"},
    {"label": "REQUIERE APOYO", "value": "REQUIERE APOYO"},
    {"label": "NO OBSERVADO", "value": "NO OBSERVADO"},
]

FORM_NAME = "Cuestionario de observación en aula"
FORM_DESCRIPTION = (
    "Pauta de observación de habilidades cognitivas-comunicativas, "
    "socioemocionales y motoras/sensoriales (LOGRADO / EN PROCESO / REQUIERE APOYO)."
)

_COG = "Habilidades cognitivas y comunicativas"
_SOC = "Habilidades Personales, Socioemocionales y de Aproximación al Aprendizaje"
_MOT = "Habilidades motoras, de autonomía y sensoriales"

COGNITIVE_ITEMS = [
    "El o la estudiante mantiene la atención en una actividad durante periodos acordes a su nivel de desarrollo, logrando finalizar tareas con apoyo mínimo",
    "Logra seguir instrucciones simples",
    "Recuerda información relevante de actividades recientes y logra aplicarla en tareas posteriores",
    "Retiene y reproduce secuencias simples de información (palabras, instrucciones, pasos de una actividad)",
    "Planifica los pasos de una tarea antes de ejecutarla y logra completarla siguiendo una secuencia",
    "Regula impulsos durante el trabajo en aula esperando turnos o respetando normas establecidas.",
    "Propone distintas alternativas para resolver situaciones problemáticas en actividades académicas o de juego",
    "Demuestra iniciativa y flexibilidad al enfrentar nuevas tareas o actividades",
    "Construye oraciones con mayor coherencia y claridad para expresar ideas, opiniones o necesidades",
    "Aplica aprendizajes adquiridos en actividades nuevas o en diferentes asignaturas",
    "Identifica información relevante en textos breves o narraciones escuchadas",
    "Comunica ideas por escrito utilizando palabras, frases o textos breves",
    "Reconoce números, letras o palabras trabajadas en actividades pedagógicas",
]

SOCIOEMOTIONAL_ITEMS = [
    "El o la estudiante demuestra mayor seguridad al participar en actividades de aula y expresar sus ideas frente a otros",
    "Se enfrenta a nuevas tareas mostrando disposición a intentarlo",
    "Se involucra activamente en propuestas que resultan significativas para su aprendizaje",
    "Identifica y expresa intereses personales en distintas áreas",
    "Utiliza sus fortalezas personales para involucrarse en experiencias de aprendizaje",
    "Participa con entusiasmo en actividades relacionadas con sus intereses",
    "Utiliza estrategias aprendidas para regular su estado emocional frente a situaciones desafiantes",
    "Enfrenta errores o dificultades manteniendo disposición a continuar la actividad",
    "Desarrolla estrategias para manejar la frustración en situaciones de aprendizaje",
    "Participa en actividades grupales respetando turnos y acuerdos establecidos",
    "Colabora con sus pares en la realización de tareas compartidas",
    "Reconoce y respeta las opiniones, emociones y características de sus compañeros",
    "Busca alternativas de solución mediante el diálogo o la mediación del adulto",
    "Solicita ayuda cuando enfrenta dificultades en una actividad",
]

MOTOR_ITEMS = [
    "El o la estudiante realiza desplazamientos dentro del espacio escolar con coordinación y seguridad acordes a su nivel de desarrollo",
    "Participa en juegos o actividades físicas demostrando coordinación general y control corporal progresivo",
    "Realiza trazos, dibujos o escritura acordes a su nivel, mostrando avances en control y organización del movimiento.",
    "Participa en actividades que requieren destreza manual, como recortar, ensartar, armar o clasificar objetos",
    "Realiza acciones básicas de higiene personal dentro del contexto escolar",
    "Reconoce y responde adecuadamente a estímulos visuales y auditivos presentes en el entorno escolar",
    "Tolera y se adapta progresivamente a distintos estímulos del entorno del aula",
    "Regula su respuesta frente a estímulos sensoriales propios del ambiente escolar",
    "Utiliza ayudas técnicas como lentes, audífonos u otros dispositivos",
    "Integra el uso de ayudas técnicas para facilitar su participación en actividades de aprendizaje.",
]


def _field(field_id: str, domain: str, item: str) -> dict:
    return {
        "id": field_id,
        "section": domain,
        "question": item,
        "fieldType": "radio",
        "options": [dict(o) for o in SCALE_OPTIONS],
        "required": False,
    }


def questionnaire_fields() -> list[dict]:
    fields: list[dict] = []
    for i, item in enumerate(COGNITIVE_ITEMS, start=1):
        fields.append(_field(f"f_cog_{i:02d}", _COG, item))
    for i, item in enumerate(SOCIOEMOTIONAL_ITEMS, start=1):
        fields.append(_field(f"f_soc_{i:02d}", _SOC, item))
    for i, item in enumerate(MOTOR_ITEMS, start=1):
        fields.append(_field(f"f_mot_{i:02d}", _MOT, item))
    return fields


# Simón Ignacio González Gallardo — 2° F — 17/03/2026 (fonoaudiología)
SIMON_GONZALEZ_ANSWERS = [
    # cognitivas (13)
    "EN PROCESO",
    "LOGRADO",
    "REQUIERE APOYO",
    "LOGRADO",
    "REQUIERE APOYO",
    "REQUIERE APOYO",
    "EN PROCESO",
    "EN PROCESO",
    "REQUIERE APOYO",
    "EN PROCESO",
    "EN PROCESO",
    "LOGRADO",
    "LOGRADO",
    # socioemocionales (14)
    "REQUIERE APOYO",
    "EN PROCESO",
    "EN PROCESO",
    "EN PROCESO",
    "EN PROCESO",
    "LOGRADO",
    "EN PROCESO",
    "EN PROCESO",
    "REQUIERE APOYO",
    "EN PROCESO",
    "LOGRADO",
    "LOGRADO",
    "EN PROCESO",
    "LOGRADO",
    # motoras (10)
    "LOGRADO",
    "LOGRADO",
    "LOGRADO",
    "LOGRADO",
    "LOGRADO",
    "LOGRADO",
    "LOGRADO",
    "EN PROCESO",
    "LOGRADO",
    "LOGRADO",
]


def answers_for_scale_row(values: list[str]) -> dict[str, str]:
    fields = questionnaire_fields()
    if len(values) != len(fields):
        raise ValueError(f"Se esperaban {len(fields)} respuestas, hay {len(values)}")
    return {field["id"]: value for field, value in zip(fields, values)}
