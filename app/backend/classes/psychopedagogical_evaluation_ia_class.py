"""
IA synthesis for Document 27 – Informe de Evaluación Psicopedagógica.
One prompt configuration per question (section); calls OpenAI to generate
a professional synthesis from instruments applied and current field content.
"""

import os
from typing import Optional, List

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Question keys (snake_case) matching DB columns and frontend field names
VALID_QUESTION_KEYS = {
    "cognitive_analysis",
    "personal_analysis",
    "motor_analysis",
    "cognitive_synthesis",
    "personal_synthesis",
    "motor_synthesis",
    "suggestions_to_school",
    "suggestions_to_classroom_team",
    "suggestions_to_student",
    "suggestions_to_family",
    "other_suggestions",
    "conclusion",
}

# Human-readable label and short instruction per question (for the prompt)
QUESTION_PROMPTS = {
    "cognitive_analysis": {
        "label": "IV.a) Análisis de Habilidades Cognitivas y Comunicativas",
        "instruction": "Redacta un análisis profesional y sintetizado sobre habilidades cognitivas y comunicativas (atención, memoria, funciones ejecutivas, razonamiento, lenguaje, comprensión lectora, etc.) basándote en los instrumentos aplicados y el contexto proporcionado.",
    },
    "personal_analysis": {
        "label": "IV.b) Análisis de Habilidades Personales, Socioemocionales y de Aproximación al Aprendizaje",
        "instruction": "Redacta un análisis profesional sobre habilidades personales, socioemocionales y de aproximación al aprendizaje (autoestima, motivación, autorregulación, trabajo en equipo, persistencia, etc.) basándote en los instrumentos aplicados y el contexto.",
    },
    "motor_analysis": {
        "label": "IV.c) Análisis de Habilidades motoras, de autonomía y sensoriales",
        "instruction": "Redacta un análisis profesional sobre habilidades motoras, de autonomía y sensoriales (motricidad gruesa y fina, autonomía funcional, integración sensorial, etc.) basándote en los instrumentos aplicados y el contexto.",
    },
    "cognitive_synthesis": {
        "label": "V.a) Síntesis en Habilidades Cognitivas y Comunicativas",
        "instruction": "Redacta una síntesis profesional que integre fortalezas, desafíos y progresos en el área cognitiva y comunicativa, basándote en los instrumentos aplicados y el contexto.",
    },
    "personal_synthesis": {
        "label": "V.b) Síntesis en Habilidades Personales, Socioemocionales y de Aproximación al Aprendizaje",
        "instruction": "Redacta una síntesis profesional que integre fortalezas, desafíos y progresos en el área personal y socioemocional, basándote en los instrumentos aplicados y el contexto.",
    },
    "motor_synthesis": {
        "label": "V.c) Síntesis en Habilidades motoras, de autonomía y sensoriales",
        "instruction": "Redacta una síntesis profesional que integre fortalezas, desafíos y progresos en el área motora, de autonomía y sensorial, basándote en los instrumentos aplicados y el contexto.",
    },
    "suggestions_to_school": {
        "label": "VI.1 Sugerencias al establecimiento educacional",
        "instruction": "Redacta sugerencias concretas y profesionales dirigidas al establecimiento educacional, basándote en los instrumentos aplicados y el contexto del informe.",
    },
    "suggestions_to_classroom_team": {
        "label": "VI.2 Sugerencias al equipo de aula",
        "instruction": "Redacta sugerencias concretas y profesionales para el equipo de aula, basándote en los instrumentos aplicados y el contexto del informe.",
    },
    "suggestions_to_student": {
        "label": "VI.3 Sugerencias al estudiante",
        "instruction": "Redacta sugerencias concretas y profesionales dirigidas al estudiante, basándote en los instrumentos aplicados y el contexto del informe.",
    },
    "suggestions_to_family": {
        "label": "VI.4 Sugerencias a la familia",
        "instruction": "Redacta sugerencias concretas y profesionales para la familia, basándote en los instrumentos aplicados y el contexto del informe.",
    },
    "other_suggestions": {
        "label": "VI.5 Otras sugerencias",
        "instruction": "Redacta otras sugerencias relevantes (recursos, derivaciones, seguimiento, etc.) basándote en los instrumentos aplicados y el contexto del informe.",
    },
    "conclusion": {
        "label": "Conclusión del informe",
        "instruction": "Redacta una conclusión profesional del informe de evaluación psicopedagógica que integre los hallazgos principales y proyecciones, basándote en los instrumentos aplicados y el contexto.",
    },
}


class PsychopedagogicalEvaluationIAClass:
    """
    Generates IA synthesis for a given question/section of the psychopedagogical
    evaluation form (Document 27). Uses OpenAI with instruments_applied and
    the current field value as context.
    """

    def __init__(self, openai_client=None):
        self.client = openai_client

    def generate_synthesis(
        self,
        question_key: str,
        instruments_applied: Optional[str],
        current_field_value: Optional[str],
        previous_responses: Optional[List[str]] = None,
        knowledge_documents_content: Optional[str] = None,
    ) -> dict:
        """
        Genera síntesis con OpenAI. Incluye opcionalmente respuestas de otros
        estudiantes (previous_responses) y contenido de knowledge_documents.
        """
        if question_key not in VALID_QUESTION_KEYS:
            return {
                "status": "error",
                "message": f"question_key no válido. Debe ser uno de: {sorted(VALID_QUESTION_KEYS)}",
                "synthesis": None,
            }
        if not OPENAI_AVAILABLE:
            return {
                "status": "error",
                "message": "OpenAI no está disponible. Instala: pip install openai",
                "synthesis": None,
            }
        api_key = os.getenv("OPENAI_API_KEY2")
        if not api_key:
            return {
                "status": "error",
                "message": "OPENAI_API_KEY no configurada en el entorno.",
                "synthesis": None,
            }
        client = self.client
        if client is None:
            client = openai.OpenAI(api_key=api_key)

        config = QUESTION_PROMPTS.get(question_key, {})
        label = config.get("label", question_key)
        instruction = config.get("instruction", "Redacta una síntesis profesional para esta sección.")

        context_parts = []
        if instruments_applied and instruments_applied.strip():
            context_parts.append(f"Instrumentos aplicados:\n{instruments_applied.strip()}")
        if current_field_value and current_field_value.strip():
            context_parts.append(f"Contenido actual de la sección (puedes usarlo como base o reemplazarlo):\n{current_field_value.strip()}")
        if previous_responses:
            ejemplos = "\n\n---\n\n".join(f"Ejemplo {i+1}:\n{r}" for i, r in enumerate(previous_responses[:20], 1))
            context_parts.append(
                f"Respuestas de otros informes de evaluación (máximo 20) para esta misma sección. "
                "Léelas para saber el estilo y el tipo de contenido que se espera; úsalas como referencia para redactar tu respuesta:\n\n"
                f"{ejemplos}"
            )
        if knowledge_documents_content and knowledge_documents_content.strip():
            context_parts.append(
                "Documentos de la base de conocimiento (normativa, manuales, procedimientos PIE). "
                "Usa este contenido como referencia para que tu respuesta sea coherente con la normativa y buenas prácticas:\n\n"
                f"{knowledge_documents_content.strip()}"
            )
        if not context_parts:
            context_parts.append("(No hay instrumentos aplicados ni contenido previo registrado para este estudiante en esta sección.)")

        user_content = f"""Sección del informe: {label}

{"\n\n".join(context_parts)}

Instrucción: {instruction}
Responde únicamente con el texto de la síntesis o respuesta, en español, listo para pegar en el informe. No incluyas títulos ni metatexto."""

        system_instruction = (
            "Eres un profesional de la psicopedagogía redactando un Informe de Evaluación Psicopedagógica. "
            "Tu respuesta debe ser clara, profesional, en español y lista para insertar en el documento."
        )

        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=user_content,
                instructions=system_instruction,
            )
            synthesis = response.output_text.strip() if response.output_text else ""
            return {"status": "success", "synthesis": synthesis}
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "synthesis": None,
            }
