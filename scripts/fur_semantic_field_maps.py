"""Ordinal → semantic key maps for the 11 official FUR Word templates.

Indexes are 1-based FormField positions from Word COM. Enum-like checkboxes
share one semantic key and differ by ``value``.
"""

from __future__ import annotations

from typing import Any


def _t(key: str) -> dict[str, Any]:
    return {"key": key, "kind": "text"}


def _c(key: str, value: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"key": key, "kind": "checkbox"}
    if value is not None:
        item["value"] = value
    return item


def _participating(start: int, rows: int = 5) -> dict[int, dict[str, Any]]:
    fields = (
        "professional_id",
        "profession_id",
        "phone_email",
        "professional_registration",
    )
    out: dict[int, dict[str, Any]] = {}
    for row in range(rows):
        base = start + row * 4
        for offset, field in enumerate(fields):
            out[base + offset] = _t(f"participating_professionals[{row}].{field}")
    return out


def _exit_professionals(start: int, rows: int = 4) -> dict[int, dict[str, Any]]:
    fields = (
        "professional_id",
        "profession_id",
        "phone_email",
        "professional_registration",
    )
    out: dict[int, dict[str, Any]] = {}
    for row in range(rows):
        base = start + row * 4
        for offset, field in enumerate(fields):
            out[base + offset] = _t(f"exit_revaluation_professionals[{row}].{field}")
    return out


def _support_block(
    start: int,
    prefixes: tuple[str, ...],
    *,
    include_specific: bool,
    include_effectiveness: bool,
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    cursor = start
    for prefix in prefixes:
        if include_specific:
            out[cursor] = _t(f"{prefix}_specific")
            cursor += 1
        if include_effectiveness:
            out[cursor] = _t(f"{prefix}_effectiveness")
            cursor += 1
        out[cursor] = _c(f"{prefix}_continuity", "si")
        out[cursor + 1] = _c(f"{prefix}_continuity", "no")
        out[cursor + 2] = _t(f"{prefix}_observations")
        cursor += 3
    return out


def _area_block(start: int, prefix: str) -> dict[int, dict[str, Any]]:
    return {
        start: _c(f"{prefix}_family_interview"),
        start + 1: _c(f"{prefix}_school_observation"),
        start + 2: _t(f"{prefix}_school_observation_detail"),
        start + 3: _c(f"{prefix}_instrument"),
        start + 4: _t(f"{prefix}_instrument_detail"),
        start + 5: _t(f"{prefix}_progress"),
        start + 6: _t(f"{prefix}_emphasis"),
    }


def _func_block(start: int, prefix: str) -> dict[int, dict[str, Any]]:
    return {
        start: _c(f"{prefix}_family_interview"),
        start + 1: _c(f"{prefix}_school_observation"),
        start + 2: _t(f"{prefix}_school_observation_detail"),
        start + 3: _c(f"{prefix}_instrument"),
        start + 4: _t(f"{prefix}_instrument_detail"),
        start + 5: _t(f"{prefix}_achieved"),
        start + 6: _t(f"{prefix}_unachieved"),
        start + 7: _t(f"{prefix}_context_participation"),
    }


def _evidence_classic(start: int) -> dict[int, dict[str, Any]]:
    return {
        start: _c("evidence_anamnesis"),
        start + 1: _c("evidence_family_interview"),
        start + 2: _c("evidence_observation_guideline"),
        start + 3: _c("evidence_evaluation_protocols"),
        start + 4: _c("evidence_report_school"),
        start + 5: _c("evidence_report_social"),
        start + 6: _c("evidence_report_psychological"),
        start + 7: _c("evidence_report_fonoaudiological"),
        start + 8: _c("evidence_report_pedagogical"),
        start + 9: _c("evidence_report_psychopedagogical"),
        start + 10: _c("evidence_learning_evaluation"),
        start + 11: _c("evidence_general_health_exam"),
        start + 12: _c("evidence_specialized_health_exam"),
        start + 13: _t("evidence_specialized_health_detail"),
        start + 14: _c("evidence_other"),
        start + 15: _t("evidence_other_detail"),
    }


def _evidence_specialized(start: int, *, with_kinesiology: bool = False) -> dict[int, dict[str, Any]]:
    keys = [
        "evidence_observation_guideline",
        "evidence_school_context_observation",
        "evidence_report_school",
        "evidence_report_social",
        "evidence_neurological",
        "evidence_report_psychological",
        "evidence_report_fonoaudiological",
        "evidence_report_pedagogical",
        "evidence_report_psychopedagogical",
        "evidence_health_assessment",
    ]
    if with_kinesiology:
        keys.append("evidence_report_kinesiological")
    keys.extend(
        [
            "evidence_specialized_health_exam",
            "evidence_specialized_health_detail",
            "evidence_other",
            "evidence_other_detail",
            "evidence_documents_count",
        ]
    )
    out: dict[int, dict[str, Any]] = {}
    for offset, key in enumerate(keys):
        out[start + offset] = (
            _t(key) if key.endswith("_detail") or key.endswith("_count") else _c(key)
        )
    return out


def _evidence_sensorial(start: int) -> dict[int, dict[str, Any]]:
    return {
        start: _c("evidence_school_context_observation"),
        start + 1: _c("evidence_observation_guideline"),
        start + 2: _c("evidence_checklist"),
        start + 3: _c("evidence_general_other"),
        start + 4: _t("evidence_general_other_detail"),
        start + 5: _c("evidence_report_school"),
        start + 6: _c("evidence_report_social"),
        start + 7: _c("evidence_neurological"),
        start + 8: _c("evidence_report_psychological"),
        start + 9: _c("evidence_report_fonoaudiological"),
        start + 10: _c("evidence_report_pedagogical"),
        start + 11: _c("evidence_report_psychopedagogical"),
        start + 12: _c("evidence_health_assessment"),
        start + 13: _c("evidence_specialized_health_exam"),
        start + 14: _t("evidence_specialized_health_detail"),
        start + 15: _c("evidence_other"),
        start + 16: _t("evidence_other_detail"),
        start + 17: _t("evidence_documents_count"),
    }


def _common_extended_header() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("born_date"),
        3: _t("age"),
        4: _t("identification_number"),
        5: _c("educational_option", "escuela_especial"),
        6: _c("educational_option", "pie"),
        7: _t("educational_option_other_detail"),
        8: _t("current_course"),
        9: _c("communication_way", "oral"),
        10: _c("communication_way", "lengua_senas"),
        11: _c("communication_way", "otra"),
        12: _t("communication_way_other_detail"),
        13: _t("establishment_name"),
        14: _t("rbd"),
        15: _t("director_signature"),
        16: _t("professional_id"),
        17: _t("professional_identification_number"),
        18: _t("profession_specialty_id"),
        19: _t("position_id"),
        20: _t("contact_phone"),
        21: _t("contact_email"),
        22: _t("registration_date"),
    }
    m.update(_participating(23))
    return m


def _apoyos_no_specific(start: int) -> dict[int, dict[str, Any]]:
    return _support_block(
        start,
        (
            "support_personal",
            "support_curricular",
            "support_materials",
            "support_organizational",
            "support_family",
            "support_other",
        ),
        include_specific=False,
        include_effectiveness=True,
    )


def _map_fur1() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("born_date"),
        3: _t("age"),
        4: _t("identification_number"),
        5: _c("revaluation_type", "proceso"),
        6: _c("tel_revaluation_scope", "proceso_escuela_lenguaje"),
        7: _c("tel_revaluation_scope", "proceso_pie"),
        8: _t("in_pie_since"),
        9: _t("current_year"),
        10: _t("current_course"),
        11: _c("revaluation_type", "egreso"),
        12: _c("tel_revaluation_scope", "egreso_escuela_lenguaje"),
        13: _c("tel_revaluation_scope", "egreso_pie"),
        14: _t("establishment_name"),
        15: _t("director_name"),
        16: _t("rbd"),
        17: _t("professional_id"),
        18: _t("professional_identification_number"),
        19: _t("profession_specialty_id"),
        20: _t("position_id"),
        21: _t("contact_phone"),
        22: _t("contact_email"),
        23: _t("registration_date"),
    }
    m.update(_participating(24))
    m.update(
        {
            44: _c("nee_is_tel_expresivo"),
            45: _c("nee_is_tel_mixto"),
            46: _t("current_diagnosis_issue_date"),
            47: _c("diagnosis_changed_from_admission", "si"),
            48: _c("diagnosis_changed_from_admission", "no"),
            49: _t("new_evaluations_revaluations"),
            50: _t("new_diagnosis_professional_data"),
            51: _t("student_educational_progress_sen"),
            52: _t("main_difficulty_areas_summary"),
            53: _c("nee_maintained", "si"),
            54: _c("nee_maintained", "no"),
            55: _c("requires_specialized_support", "si"),
            56: _c("requires_specialized_support", "no"),
            57: _t("nee_synthesis_observations"),
            58: _t("evidence_documents_count"),
        }
    )
    m.update(_evidence_classic(59))
    m.update(
        {
            75: _t("specialized_curriculum_participation_evolution"),
            76: _t("specialized_curricular_achievements"),
            77: _t("specialized_unachieved_learning"),
            78: _t("specialized_learning_participation_progress"),
            79: _t("specialized_context_participation"),
            80: _t("specialized_barriers_reduction"),
            81: _t("specialized_family_participation"),
            82: _t("specialized_next_period_emphasis"),
            83: _t("specialized_dea_literacy_math_progress"),
            84: _t("specialized_next_period_reading"),
            85: _t("specialized_next_period_writing"),
            86: _t("specialized_next_period_math"),
            87: _t("specialized_next_period_other"),
            88: _t("specialized_tab_observations"),
            89: _c("support_area_oral_language"),
            90: _c("support_area_curricular_general"),
            91: _c("support_area_specific_subjects"),
            92: _c("support_area_affective_social"),
            93: _c("support_area_adaptive_functioning"),
            94: _c("support_area_autonomy"),
            95: _c("support_area_cognitive_functions"),
            96: _c("support_area_executive_functions"),
            97: _c("support_area_communication"),
            98: _c("support_area_social_adaptation"),
            99: _c("support_area_other"),
            100: _t("support_area_other_detail"),
        }
    )
    m.update(
        _support_block(
            101,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=True,
        )
    )
    m.update(
        {
            131: _t("support_work_strategies"),
            132: _t("support_family_strategies_effectiveness"),
            133: _t("support_new_needs_required"),
            134: _t("support_next_period_comments"),
            135: _c("exit_in_pie"),
            136: _c("exit_in_escuela_lenguaje"),
            137: _t("full_name"),
            138: _t("identification_number"),
        }
    )
    m.update(_exit_professionals(139))
    m.update(
        {
            155: _t("exit_dea_deficit_evaluation"),
            156: _t("exit_dea_deficit_evaluation"),
            157: _t("exit_dea_deficit_evaluation"),
            158: _t("exit_dea_deficit_evaluation"),
            159: _t("exit_dea_deficit_evaluation"),
            160: _t("decision_school_year"),
            161: _c("tel_decision_outcome", "egreso"),
            162: _c("tel_decision_outcome", "egreso_pie"),
            163: _c("tel_decision_outcome", "egreso_escuela_lenguaje"),
            164: _c("tel_decision_outcome", "continuidad"),
            165: _c("tel_decision_outcome", "continuidad_pie"),
            166: _c("tel_decision_outcome", "continuidad_escuela_lenguaje"),
            167: _t("decision_date"),
            168: _t("decision_rationale"),
            169: _t("decision_observations"),
        }
    )
    return m


def _map_fur2() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("born_date"),
        3: _t("age"),
        4: _t("identification_number"),
        5: _t("in_pie_since"),
        6: _t("current_year"),
        7: _t("current_course"),
        8: _c("revaluation_type", "proceso"),
        9: _c("revaluation_type", "egreso"),
        10: _t("establishment_name"),
        11: _t("director_name"),
        12: _t("rbd"),
        13: _t("professional_id"),
        14: _t("professional_identification_number"),
        15: _t("profession_specialty_id"),
        16: _t("position_id"),
        17: _t("contact_phone"),
        18: _t("contact_email"),
        19: _t("registration_date"),
    }
    m.update(_participating(20))
    m.update(
        {
            40: _c("nee_is_dea"),
            41: _t("current_diagnosis_issue_date"),
            42: _c("diagnosis_changed_from_admission", "si"),
            43: _c("diagnosis_changed_from_admission", "no"),
            44: _t("new_evaluations_revaluations"),
            45: _t("new_diagnosis_professional_data"),
            46: _t("student_educational_progress_sen"),
            47: _t("main_difficulty_areas_summary"),
            48: _c("nee_maintained", "si"),
            49: _c("nee_maintained", "no"),
            50: _c("requires_specialized_support", "si"),
            51: _c("requires_specialized_support", "no"),
            52: _t("nee_synthesis_observations"),
            53: _t("evidence_documents_count"),
        }
    )
    m.update(_evidence_classic(54))
    m.update(
        {
            70: _t("specialized_curriculum_participation_evolution"),
            71: _t("specialized_curricular_achievements"),
            72: _t("specialized_unachieved_learning"),
            73: _t("specialized_learning_participation_progress"),
            74: _t("specialized_context_participation"),
            75: _t("specialized_barriers_reduction"),
            76: _t("specialized_family_participation"),
            77: _t("specialized_next_period_emphasis"),
            78: _t("specialized_dea_literacy_math_progress"),
            79: _t("specialized_next_period_reading"),
            80: _t("specialized_next_period_writing"),
            81: _t("specialized_next_period_math"),
            82: _t("specialized_next_period_other"),
            83: _t("specialized_tab_observations"),
            84: _c("support_area_curricular_general"),
            85: _c("support_area_specific_subjects"),
            86: _c("support_area_oral_language"),
            87: _c("support_area_affective_social"),
            88: _c("support_area_adaptive_functioning"),
            89: _c("support_area_autonomy"),
            90: _c("support_area_cognitive_functions"),
            91: _c("support_area_executive_functions"),
            92: _c("support_area_communication"),
            93: _c("support_area_social_adaptation"),
            94: _c("support_area_other"),
            95: _t("support_area_other_detail"),
        }
    )
    m.update(
        _support_block(
            96,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=True,
        )
    )
    m.update(
        {
            126: _t("support_work_strategies"),
            127: _t("support_family_strategies_effectiveness"),
            128: _t("support_new_needs_required"),
            129: _t("support_next_period_comments"),
            130: _t("full_name"),
            131: _t("identification_number"),
        }
    )
    m.update(_exit_professionals(132))
    m.update(
        {
            148: _t("exit_dea_deficit_evaluation"),
            149: _t("exit_dea_deficit_evaluation"),
            150: _t("exit_dea_deficit_evaluation"),
            151: _t("exit_dea_deficit_evaluation"),
            152: _t("exit_dea_deficit_evaluation"),
            153: _t("decision_school_year"),
            154: _c("exit_team_decision_period", "anual"),
            155: _c("exit_team_decision_period", "dos_anos"),
            156: _c("decision_type", "egreso"),
            157: _c("decision_type", "continuidad"),
            158: _t("decision_date"),
            159: _t("decision_rationale"),
            160: _t("decision_observations"),
        }
    )
    return m


def _map_fur3() -> dict[int, dict[str, Any]]:
    m = _map_fur2()
    for key in [k for k in m if k >= 40]:
        del m[key]
    m.update(
        {
            40: _c("nee_is_tda_sin_hiperkinesia"),
            41: _c("nee_is_tda_con_hiperkinesia"),
            42: _t("current_diagnosis_issue_date"),
            43: _c("diagnosis_changed_from_admission", "si"),
            44: _c("diagnosis_changed_from_admission", "no"),
            45: _t("new_evaluations_revaluations"),
            46: _t("new_diagnosis_professional_data"),
            47: _t("student_educational_progress_sen"),
            48: _t("main_difficulty_areas_summary"),
            49: _c("nee_maintained", "si"),
            50: _c("nee_maintained", "no"),
            51: _c("requires_specialized_support", "si"),
            52: _c("requires_specialized_support", "no"),
            53: _t("evidence_documents_count"),
        }
    )
    m.update(_evidence_classic(54))
    m.update(
        {
            70: _t("specialized_curriculum_participation_evolution"),
            71: _t("specialized_curricular_achievements"),
            72: _t("specialized_unachieved_learning"),
            73: _t("specialized_learning_participation_progress"),
            74: _t("specialized_context_participation"),
            75: _t("specialized_barriers_reduction"),
            76: _t("specialized_family_participation"),
            77: _t("specialized_next_period_emphasis"),
            78: _t("specialized_dea_literacy_math_progress"),
            79: _t("specialized_next_period_reading"),
            80: _t("specialized_next_period_writing"),
            81: _t("specialized_next_period_math"),
            82: _t("specialized_next_period_other"),
            83: _t("specialized_tab_observations"),
            84: _c("support_area_curricular_general"),
            85: _c("support_area_specific_subjects"),
            86: _c("support_area_oral_language"),
            87: _c("support_area_affective_social"),
            88: _c("support_area_adaptive_functioning"),
            89: _c("support_area_autonomy"),
            90: _c("support_area_cognitive_functions"),
            91: _c("support_area_executive_functions"),
            92: _c("support_area_communication"),
            93: _c("support_area_social_adaptation"),
            94: _c("support_area_other"),
            95: _t("support_area_other_detail"),
        }
    )
    m.update(
        _support_block(
            96,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=True,
        )
    )
    m.update(
        {
            126: _t("support_work_strategies"),
            127: _t("support_family_strategies_effectiveness"),
            128: _t("support_new_needs_required"),
            129: _t("support_next_period_comments"),
            130: _t("full_name"),
            131: _t("identification_number"),
        }
    )
    m.update(_exit_professionals(132))
    m.update(
        {
            148: _t("exit_dea_deficit_evaluation"),
            149: _t("exit_dea_deficit_evaluation"),
            150: _t("exit_dea_deficit_evaluation"),
            151: _t("exit_dea_deficit_evaluation"),
            152: _t("exit_dea_deficit_evaluation"),
            153: _t("decision_school_year"),
            154: _c("decision_type", "egreso"),
            155: _c("decision_type", "continuidad"),
            156: _t("decision_date"),
            157: _t("decision_rationale"),
            158: _t("decision_observations"),
        }
    )
    return m


def _map_fur4() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("born_date"),
        3: _t("age"),
        4: _t("identification_number"),
        5: _t("in_pie_since"),
        6: _t("current_year"),
        7: _t("current_course"),
        8: _c("revaluation_type", "proceso"),
        9: _c("revaluation_type", "egreso"),
        10: _t("establishment_name"),
        11: _t("director_name"),
        12: _t("rbd"),
        13: _t("professional_id"),
        14: _t("professional_identification_number"),
        15: _t("profession_specialty_id"),
        16: _t("position_id"),
        17: _t("contact_phone"),
        18: _t("contact_email"),
        19: _t("registration_date"),
    }
    m.update(_participating(20))
    m.update(
        {
            40: _c("nee_is_fil"),
            41: _t("current_diagnosis_issue_date"),
            42: _c("diagnosis_changed_from_admission", "si"),
            43: _c("diagnosis_changed_from_admission", "no"),
            44: _t("new_evaluations_revaluations"),
            45: _t("new_diagnosis_professional_data"),
            46: _t("student_educational_progress_sen"),
            47: _t("main_difficulty_areas_summary"),
            48: _c("nee_maintained", "si"),
            49: _c("nee_maintained", "no"),
            50: _c("requires_specialized_support", "si"),
            51: _c("requires_specialized_support", "no"),
            52: _t("evidence_documents_count"),
        }
    )
    m.update(_evidence_classic(53))
    m.update(
        {
            69: _t("specialized_curriculum_participation_evolution"),
            70: _t("specialized_curricular_achievements"),
            71: _t("specialized_unachieved_learning"),
            72: _t("specialized_learning_participation_progress"),
            73: _t("specialized_context_participation"),
            74: _t("specialized_barriers_reduction"),
            75: _t("specialized_family_participation"),
            76: _t("specialized_next_period_emphasis"),
            77: _t("specialized_dea_literacy_math_progress"),
            78: _t("specialized_next_period_other"),
            79: _t("specialized_tab_observations"),
            80: _c("support_area_curricular_general"),
            81: _c("support_area_specific_subjects"),
            82: _c("support_area_oral_language"),
            83: _c("support_area_affective_social"),
            84: _c("support_area_adaptive_functioning"),
            85: _c("support_area_autonomy"),
            86: _c("support_area_cognitive_functions"),
            87: _c("support_area_executive_functions"),
            88: _c("support_area_communication"),
            89: _c("support_area_social_adaptation"),
            90: _c("support_area_other"),
            91: _t("support_area_other_detail"),
        }
    )
    m.update(
        _support_block(
            92,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_social",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=True,
        )
    )
    m.update(
        {
            127: _t("support_work_strategies"),
            128: _t("support_family_strategies_effectiveness"),
            129: _t("support_new_needs_required"),
            130: _t("support_next_period_comments"),
            131: _t("full_name"),
            132: _t("identification_number"),
        }
    )
    m.update(_exit_professionals(133))
    m.update(
        {
            149: _t("exit_dea_deficit_evaluation"),
            150: _t("exit_dea_deficit_evaluation"),
            151: _t("exit_dea_deficit_evaluation"),
            152: _t("exit_dea_deficit_evaluation"),
            153: _t("exit_dea_deficit_evaluation"),
            154: _t("decision_school_year"),
            155: _c("decision_type", "egreso"),
            156: _c("decision_type", "continuidad"),
            157: _t("decision_date"),
            158: _t("decision_rationale"),
            159: _t("decision_observations"),
        }
    )
    return m


def _map_fur5() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("born_date"),
        3: _t("age"),
        4: _t("identification_number"),
        5: _c("educational_option", "escuela_especial"),
        6: _c("educational_option", "pie"),
        7: _t("current_course"),
        8: _t("educational_option_other_detail"),
        9: _c("communication_way", "oral"),
        10: _c("communication_way", "lengua_senas"),
        11: _c("communication_way", "otra"),
        12: _t("communication_way_other_detail"),
        13: _t("establishment_name"),
        14: _t("rbd"),
        15: _t("director_signature"),
        16: _t("professional_id"),
        17: _t("professional_identification_number"),
        18: _t("profession_specialty_id"),
        19: _t("contact_phone"),
        20: _t("contact_email"),
        21: _t("professional_signature"),
        22: _t("registration_date"),
    }
    m.update(_participating(23))
    m.update(
        {
            43: _c("nee_is_intellectual_disability"),
            44: _c("nee_disability_grade", "leve"),
            45: _c("nee_disability_grade", "moderado"),
            46: _c("nee_disability_grade", "grave"),
            47: _c("nee_disability_grade", "profundo"),
            48: _t("current_diagnosis_issue_date"),
            49: _t("current_revaluation_date"),
            50: _t("new_evaluations_revaluations"),
            51: _c("diagnosis_changed_from_admission", "si"),
            52: _c("diagnosis_changed_from_admission", "no"),
            53: _t("diagnosis_modifications_detail"),
            54: _t("new_diagnosis_professional_data"),
            55: _t("diagnosis_change_emphasis"),
            56: _t("student_educational_progress_sen"),
            57: _t("main_difficulty_areas_summary"),
            58: _t("evidence_documents_count"),
        }
    )
    m.update(_evidence_classic(59))
    m.update(
        {
            75: _t("identification_number"),
            76: _t("specialized_curricular_achievements"),
            77: _t("specialized_unachieved_learning"),
            78: _t("specialized_learning_participation_progress"),
            79: _t("specialized_context_participation"),
            80: _t("specialized_barriers_reduction"),
            81: _t("specialized_family_participation"),
            82: _t("specialized_next_period_emphasis"),
            83: _t("specialized_dea_literacy_math_progress"),
            84: _t("specialized_tab_observations"),
            85: _t("identification_number"),
            86: _c("support_area_communication"),
            87: _c("support_area_self_care"),
            88: _c("support_area_domestic_life"),
            89: _c("support_area_social_skills"),
            90: _c("support_area_functional_academic"),
            91: _c("support_area_community_use"),
            92: _c("support_area_self_direction"),
            93: _c("support_area_health_safety"),
            94: _c("support_area_leisure"),
            95: _c("support_area_work"),
            96: _c("support_area_curricular_general"),
            97: _c("support_area_specific_subjects"),
            98: _c("support_area_affective_social"),
            99: _c("support_area_other"),
            100: _t("support_area_other_detail"),
        }
    )
    m.update(
        _support_block(
            101,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_social",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=True,
        )
    )
    m.update(
        {
            136: _t("support_work_strategies"),
            137: _t("support_family_strategies_effectiveness"),
            138: _t("support_new_needs_required"),
            139: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur6() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("identification_number"),
        3: _t("born_date"),
        4: _t("age"),
        5: _t("current_course"),
        6: _c("communication_way", "oral"),
        7: _c("communication_way", "lengua_senas"),
        8: _c("communication_way", "otra"),
        9: _t("communication_way_other_detail"),
        10: _t("establishment_name"),
        11: _t("rbd"),
        12: _t("director_signature"),
        13: _t("professional_id"),
        14: _t("professional_identification_number"),
        15: _t("profession_specialty_id"),
        16: _t("contact_phone"),
        17: _t("contact_email"),
        18: _t("professional_signature"),
        19: _t("registration_date"),
    }
    m.update(_participating(20))
    m.update(
        {
            40: _t("motora_admission_diagnosis"),
            41: _c("diagnosis_changed_from_admission", "si"),
            42: _c("diagnosis_changed_from_admission", "no"),
            43: _t("diagnosis_modifications_detail"),
            44: _t("current_diagnosis_issue_date"),
            45: _t("new_diagnosis_professional_data"),
            46: _t("nee_synthesis_observations"),
        }
    )
    m.update(_evidence_specialized(47, with_kinesiology=True))
    m.update(
        {
            63: _t("identification_number"),
            64: _c("motora_area_psychoeducative_family_interview"),
            65: _c("motora_area_psychoeducative_school_observation"),
            66: _t("motora_area_psychoeducative_school_observation_detail"),
            67: _c("motora_area_psychoeducative_instrument"),
            68: _t("motora_area_psychoeducative_instrument_detail"),
            69: _t("motora_psychoeducative_achieved"),
            70: _t("motora_psychoeducative_unachieved"),
            71: _t("motora_psychoeducative_context_participation"),
        }
    )
    m.update(_area_block(72, "motora_area_social"))
    m.update(_area_block(79, "motora_area_family"))
    m.update(_area_block(86, "motora_area_communication"))
    m[93] = _t("identification_number")
    m.update(_area_block(94, "motora_area_motor"))
    m.update(
        _support_block(
            100,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=False,
        )
    )
    m.update(
        {
            124: _t("support_work_strategies"),
            125: _t("support_family_strategies_effectiveness"),
            126: _t("support_new_needs_required"),
            127: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur7() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("identification_number"),
        3: _t("born_date"),
        4: _t("age"),
        5: _t("current_course"),
        6: _c("communication_way", "oral"),
        7: _c("communication_way", "lengua_senas"),
        8: _c("communication_way", "otra"),
        9: _t("communication_way_other_detail"),
        10: _t("establishment_name"),
        11: _t("rbd"),
        12: _t("director_signature"),
        13: _t("professional_id"),
        14: _t("professional_identification_number"),
        15: _t("profession_specialty_id"),
        16: _t("contact_phone"),
        17: _t("contact_email"),
        18: _t("professional_signature"),
        19: _t("registration_date"),
    }
    m.update(_participating(20))
    m.update(
        {
            40: _t("position_id"),
            41: _t("current_diagnosis_issue_date"),
            42: _c("visual_diagnosis_low_vision"),
            43: _c("visual_diagnosis_blindness"),
            44: _c("visual_var_prognosis"),
            45: _t("visual_var_prognosis_detail"),
            46: _c("visual_var_auditory_functionality"),
            47: _c("visual_var_spatial_orientation"),
            48: _c("visual_var_displacement"),
            49: _c("visual_var_optical_implementation"),
            50: _t("visual_var_optical_implementation_detail"),
            51: _c("visual_var_classroom_visual_function"),
            52: _c("visual_var_learning_style"),
            53: _c("visual_var_signography"),
            54: _c("visual_var_reading_level"),
            55: _c("visual_var_self_care"),
            56: _c("visual_var_autonomy"),
            57: _c("visual_var_money_management"),
            58: _c("visual_support_replanned_personal"),
            59: _c("visual_support_replanned_curricular"),
            60: _c("visual_support_replanned_materials"),
            61: _c("visual_support_replanned_organizational"),
            62: _c("visual_support_replanned_family"),
            63: _c("visual_support_replanned_other"),
            64: _t("visual_support_replanned_other_detail"),
            65: _t("visual_general_progress_summary"),
        }
    )
    m.update(_evidence_sensorial(66))
    m.update(
        {
            84: _t("identification_number"),
            85: _t("visual_school_learning_achieved"),
            86: _t("visual_school_learning_unachieved"),
            87: _t("visual_school_context_achievements"),
            88: _t("visual_school_barrier_reduction"),
            89: _t("specialized_family_participation"),
            90: _t("specialized_next_period_emphasis"),
            91: _t("visual_specific_vision_progress"),
            92: _t("visual_specific_orientation_progress"),
            93: _t("visual_specific_mobility_progress"),
            94: _t("visual_specific_orientation_mobility_emphasis"),
            95: _t("visual_specific_adl_progress"),
            96: _t("visual_specific_adl_emphasis"),
            97: _t("visual_specific_functional_vision"),
            98: _t("visual_specific_signography"),
            99: _t("visual_specific_learning_motivation"),
            100: _t("visual_specific_learning_emphasis"),
            101: _t("identification_number"),
        }
    )
    m.update(
        _support_block(
            102,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=False,
        )
    )
    m.update(
        {
            126: _t("support_work_strategies"),
            127: _t("support_family_strategies_effectiveness"),
            128: _t("support_new_needs_required"),
            129: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur8() -> dict[int, dict[str, Any]]:
    m: dict[int, dict[str, Any]] = {
        1: _t("full_name"),
        2: _t("identification_number"),
        3: _t("born_date"),
        4: _t("age"),
        5: _t("current_course"),
        6: _c("communication_way", "oral"),
        7: _c("communication_way", "lengua_senas"),
        8: _c("communication_way", "otra"),
        9: _t("communication_way_other_detail"),
        10: _t("establishment_name"),
        11: _t("rbd"),
        12: _t("director_signature"),
        13: _t("professional_id"),
        14: _t("professional_identification_number"),
        15: _t("profession_specialty_id"),
        16: _t("contact_phone"),
        17: _t("contact_email"),
        18: _t("professional_signature"),
        19: _t("registration_date"),
    }
    m.update(_participating(20))
    m.update(
        {
            40: _t("current_diagnosis_issue_date"),
            41: _c("auditiva_diagnosis_moderate"),
            42: _c("auditiva_diagnosis_severe"),
            43: _c("auditiva_diagnosis_deafness"),
            44: _c("auditiva_criterion_40db"),
            45: _c("auditiva_criterion_auditory_processing"),
            46: _c("auditiva_criterion_activity_limitation"),
            47: _c("auditiva_criterion_deaf_community"),
            48: _c("auditiva_criterion_sign_language_user"),
            49: _c("auditiva_var_auditory_implementation"),
            50: _c("auditiva_var_auditory_functionality"),
            51: _c("auditiva_support_replanned_personal"),
            52: _c("auditiva_support_replanned_curricular"),
            53: _c("auditiva_support_replanned_materials"),
            54: _c("auditiva_support_replanned_organizational"),
            55: _c("auditiva_support_replanned_family"),
            56: _c("auditiva_support_replanned_other"),
            57: _t("auditiva_support_replanned_other_detail"),
            58: _c("auditiva_var_expression"),
            59: _c("auditiva_var_expression_oral"),
            60: _c("auditiva_var_expression_signs"),
            61: _c("auditiva_var_comprehension"),
            62: _c("auditiva_var_cognitive_skills"),
            63: _c("auditiva_var_pragmatic_skills"),
            64: _c("auditiva_var_perceptual_visual"),
            65: _c("auditiva_var_learning_style"),
            66: _c("auditiva_var_reading_level"),
            67: _t("auditiva_general_progress_summary"),
        }
    )
    m.update(_evidence_sensorial(68))
    m.update(
        {
            86: _t("identification_number"),
            87: _t("auditiva_school_learning_achieved"),
            88: _t("auditiva_school_learning_unachieved"),
            89: _t("auditiva_school_context_achievements"),
            90: _t("auditiva_school_barrier_reduction"),
            91: _t("specialized_family_participation"),
            92: _t("specialized_next_period_emphasis"),
            93: _t("auditiva_specific_audition"),
            94: _t("auditiva_specific_expression"),
            95: _t("auditiva_specific_comprehension"),
            96: _t("auditiva_specific_pragmatic"),
            97: _t("auditiva_specific_communication_emphasis"),
            98: _t("auditiva_specific_perceptual_visual"),
            99: _t("auditiva_specific_learning_motivation"),
            100: _t("auditiva_specific_learning_emphasis"),
            101: _t("identification_number"),
        }
    )
    m.update(
        _support_block(
            102,
            (
                "support_personal",
                "support_curricular",
                "support_materials",
                "support_organizational",
                "support_family",
                "support_other",
            ),
            include_specific=True,
            include_effectiveness=False,
        )
    )
    m.update(
        {
            126: _t("support_work_strategies"),
            127: _t("support_family_strategies_effectiveness"),
            128: _t("support_new_needs_required"),
            129: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur9() -> dict[int, dict[str, Any]]:
    m = _common_extended_header()
    m.update(
        {
            43: _c("multiple_nee_intellectual_disability"),
            44: _c("multiple_nee_motor_disability"),
            45: _c("multiple_nee_auditiva"),
            46: _c("multiple_nee_visual"),
            47: _c("multiple_nee_disfasia"),
            48: _c("multiple_nee_tea"),
            49: _c("multiple_nee_tgd"),
            50: _c("multiple_nee_other"),
            51: _t("multiple_nee_other_detail"),
            52: _c("diagnosis_changed_from_admission", "si"),
            53: _c("diagnosis_changed_from_admission", "no"),
            54: _t("diagnosis_modifications_detail"),
            55: _t("current_diagnosis_issue_date"),
            56: _t("new_diagnosis_professional_data"),
            57: _t("nee_synthesis_observations"),
            58: _c("evidence_observation_guideline"),
            59: _c("evidence_school_context_observation"),
            60: _c("evidence_report_school"),
            61: _c("evidence_report_social"),
            62: _c("evidence_neurological"),
            63: _c("evidence_report_psychological"),
            64: _c("evidence_report_fonoaudiological"),
            65: _c("evidence_report_pedagogical"),
            66: _c("evidence_report_psychopedagogical"),
            67: _c("evidence_health_assessment"),
            68: _c("evidence_specialized_health_exam"),
            69: _t("evidence_specialized_health_detail"),
            70: _c("evidence_other"),
            71: _t("evidence_other_detail"),
            72: _t("evidence_documents_count"),
            73: _t("identification_number"),
        }
    )
    m.update(_area_block(74, "dm_area_vision"))
    m.update(_area_block(81, "dm_area_hearing"))
    m.update(_area_block(88, "dm_area_communication"))
    m.update(_area_block(95, "dm_area_cognitive"))
    m[102] = _t("identification_number")
    m.update(_area_block(103, "dm_area_motor"))
    m.update(_func_block(110, "dm_area_functional_academic"))
    m.update(_area_block(118, "dm_area_personal_social"))
    m.update(_area_block(125, "dm_area_family_context"))
    m[132] = _t("identification_number")
    m.update(_apoyos_no_specific(133))
    m.update(
        {
            157: _t("support_work_strategies"),
            158: _t("support_family_strategies_effectiveness"),
            159: _t("support_new_needs_required"),
            160: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur10() -> dict[int, dict[str, Any]]:
    m = _common_extended_header()
    m.update(
        {
            43: _c("nee_is_tea"),
            44: _c("nee_is_gdd_unspecified"),
            45: _c("nee_is_asperger"),
            46: _c("diagnosis_changed_from_admission", "si"),
            47: _c("diagnosis_changed_from_admission", "no"),
            48: _t("diagnosis_modifications_detail"),
            49: _t("current_diagnosis_issue_date"),
            50: _t("new_diagnosis_professional_data"),
            51: _t("nee_synthesis_observations"),
            52: _c("evidence_observation_guideline"),
            53: _c("evidence_school_context_observation"),
            54: _c("evidence_report_school"),
            55: _c("evidence_report_social"),
            56: _c("evidence_neurological"),
            57: _c("evidence_report_psychological"),
            58: _c("evidence_report_fonoaudiological"),
            59: _c("evidence_report_pedagogical"),
            60: _c("evidence_report_psychopedagogical"),
            61: _c("evidence_health_assessment"),
            62: _c("evidence_specialized_health_exam"),
            63: _t("evidence_specialized_health_detail"),
            64: _c("evidence_other"),
            65: _t("evidence_other_detail"),
            66: _t("evidence_documents_count"),
            67: _t("identification_number"),
        }
    )
    m.update(_area_block(68, "tea_area_social"))
    m.update(_area_block(75, "tea_area_language"))
    m.update(_area_block(82, "tea_area_cognitive"))
    m.update(_area_block(89, "tea_area_sensory"))
    m[96] = _t("identification_number")
    m.update(_area_block(97, "tea_area_motor"))
    m.update(_func_block(104, "tea_area_functional_academic"))
    m.update(_area_block(112, "tea_area_personal_social"))
    m.update(_area_block(119, "tea_area_family_context"))
    m[126] = _t("identification_number")
    m.update(_apoyos_no_specific(127))
    m.update(
        {
            151: _t("support_work_strategies"),
            152: _t("support_family_strategies_effectiveness"),
            153: _t("support_new_needs_required"),
            154: _t("support_next_period_comments"),
        }
    )
    return m


def _map_fur11() -> dict[int, dict[str, Any]]:
    m = _common_extended_header()
    m.update(
        {
            43: _t("disfasia_admission_diagnosis"),
            44: _c("diagnosis_changed_from_admission", "si"),
            45: _c("diagnosis_changed_from_admission", "no"),
            46: _t("diagnosis_modifications_detail"),
            47: _t("current_diagnosis_issue_date"),
            48: _t("new_diagnosis_professional_data"),
            49: _t("nee_synthesis_observations"),
            50: _c("evidence_observation_guideline"),
            51: _c("evidence_school_context_observation"),
            52: _c("evidence_report_school"),
            53: _c("evidence_report_social"),
            54: _c("evidence_neurological"),
            55: _c("evidence_report_psychological"),
            56: _c("evidence_report_fonoaudiological"),
            57: _c("evidence_report_pedagogical"),
            58: _c("evidence_report_psychopedagogical"),
            59: _c("evidence_health_assessment"),
            60: _c("evidence_specialized_health_exam"),
            61: _t("evidence_specialized_health_detail"),
            62: _c("evidence_other"),
            63: _t("evidence_other_detail"),
            64: _t("evidence_documents_count"),
            65: _t("identification_number"),
            66: _t("disfasia_language_phonological_receptive"),
            67: _t("disfasia_language_phonological_expressive"),
            68: _t("disfasia_language_lexical_receptive"),
            69: _t("disfasia_language_lexical_expressive"),
            70: _t("disfasia_language_morphological_receptive"),
            71: _t("disfasia_language_morphological_expressive"),
            72: _t("disfasia_language_syntactic_receptive"),
            73: _t("disfasia_language_syntactic_expressive"),
            74: _t("disfasia_language_semantic_pragmatic_receptive"),
            75: _t("disfasia_language_semantic_pragmatic_expressive"),
            76: _t("disfasia_language_written_communication"),
            77: _t("disfasia_language_next_period_emphasis"),
        }
    )
    m.update(_area_block(78, "disfasia_area_social"))
    m[85] = _t("identification_number")
    m.update(_area_block(86, "disfasia_area_cognitive"))
    m.update(_area_block(93, "disfasia_area_sensory"))
    m.update(_area_block(100, "disfasia_area_motor"))
    m.update(_func_block(107, "disfasia_area_functional_academic"))
    m[115] = _t("identification_number")
    m.update(_area_block(116, "disfasia_area_personal_social"))
    m.update(_area_block(123, "disfasia_area_family_context"))
    m.update(_apoyos_no_specific(130))
    m.update(
        {
            154: _t("support_work_strategies"),
            155: _t("support_family_strategies_effectiveness"),
            156: _t("support_new_needs_required"),
            157: _t("support_next_period_comments"),
        }
    )
    return m


# Correcciones verificadas contra el texto que rodea a cada control en el Word
# (scripts/audit_fur_control_labels.py). El recuento ordinal original no
# contemplaba los encabezados "RUN estudiante:" que se repiten al inicio de las
# secciones II y III, lo que corría un bloque completo de campos en FUR 1 a 4.
# En FUR 5 el orden de las evidencias del Word difiere del de los demás, y en
# FUR 9, 10 y 11 el curso y el detalle de "Otra" opción educativa estaban
# invertidos.
_CORRECTIONS: dict[str, dict[int, dict[str, Any]]] = {
    "fur1_tel.doc": {
        75: _t("identification_number"),
        78: _t("specialized_context_participation"),
        79: _t("specialized_barriers_reduction"),
        80: _t("specialized_family_participation"),
        81: _t("specialized_next_period_emphasis"),
        82: _t("specialized_dea_literacy_math_progress"),
        83: _t("specialized_next_period_reading"),  # Nivel Expresivo
        84: _t("specialized_next_period_writing"),  # Nivel Comprensivo
        85: _t("specialized_next_period_math"),  # Nivel Comunicativo
        86: _t("specialized_next_period_other"),
        87: _t("specialized_tab_observations"),
        88: _t("identification_number"),
    },
    "fur2_dep.doc": {
        70: _t("identification_number"),
        73: _t("specialized_context_participation"),
        74: _t("specialized_barriers_reduction"),
        75: _t("specialized_family_participation"),
        76: _t("specialized_next_period_emphasis"),
        77: _t("specialized_dea_literacy_math_progress"),
        78: _t("specialized_next_period_reading"),
        79: _t("specialized_next_period_writing"),
        80: _t("specialized_next_period_math"),
        81: _t("specialized_next_period_other"),
        82: _t("specialized_tab_observations"),
        83: _t("identification_number"),
    },
    "fur3_tda.doc": {
        70: _t("identification_number"),
        73: _t("specialized_context_participation"),
        74: _t("specialized_barriers_reduction"),
        75: _t("specialized_family_participation"),
        76: _t("specialized_next_period_emphasis"),
        77: _t("specialized_dea_literacy_math_progress"),
        78: _t("specialized_next_period_reading"),  # Atención
        79: _t("specialized_next_period_writing"),  # Impulsividad
        80: _t("specialized_next_period_math"),  # Inquietud / hiperactividad
        81: _t("specialized_next_period_other"),
        82: _t("specialized_tab_observations"),
        83: _t("identification_number"),
    },
    "fur4_ci_t.doc": {
        69: _t("identification_number"),
        72: _t("specialized_context_participation"),
        73: _t("specialized_barriers_reduction"),
        74: _t("specialized_family_participation"),
        75: _t("specialized_next_period_emphasis"),
        76: _t("specialized_dea_literacy_math_progress"),
        77: _t("specialized_next_period_other"),
        78: _t("specialized_tab_observations"),
        79: _t("identification_number"),
    },
    "fur5_ci_p.doc": {
        63: _c("evidence_learning_evaluation"),
        64: _c("evidence_report_school"),
        65: _c("evidence_report_social"),
        66: _c("evidence_report_psychological"),
        67: _c("evidence_report_fonoaudiological"),
        68: _c("evidence_report_pedagogical"),
        69: _c("evidence_report_psychopedagogical"),
    },
    "fur6_dm.doc": {
        # El área motora no tiene recuadro para el detalle del instrumento.
        98: _t("motora_area_motor_progress"),
        99: _t("motora_area_motor_emphasis"),
    },
    "fur9_dmu.doc": {
        7: _t("current_course"),
        8: _t("educational_option_other_detail"),
    },
    "fur10_tea.doc": {
        7: _t("current_course"),
        8: _t("educational_option_other_detail"),
    },
    "fur11_dstc.doc": {
        7: _t("current_course"),
        8: _t("educational_option_other_detail"),
    },
}


def _corrected(source: str, mapping: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    mapping.update(_CORRECTIONS.get(source, {}))
    return mapping


FUR_SEMANTIC_MAPS: dict[str, dict[int, dict[str, Any]]] = {
    "fur1_tel.doc": _corrected("fur1_tel.doc", _map_fur1()),
    "fur2_dep.doc": _corrected("fur2_dep.doc", _map_fur2()),
    "fur3_tda.doc": _corrected("fur3_tda.doc", _map_fur3()),
    "fur4_ci_t.doc": _corrected("fur4_ci_t.doc", _map_fur4()),
    "fur5_ci_p.doc": _corrected("fur5_ci_p.doc", _map_fur5()),
    "fur6_dm.doc": _corrected("fur6_dm.doc", _map_fur6()),
    "fur7_dv.doc": _map_fur7(),
    "fur8_da.doc": _map_fur8(),
    "fur9_dmu.doc": _corrected("fur9_dmu.doc", _map_fur9()),
    "fur10_tea.doc": _corrected("fur10_tea.doc", _map_fur10()),
    "fur11_dstc.doc": _corrected("fur11_dstc.doc", _map_fur11()),
}


EXPECTED_COUNTS = {
    "fur1_tel.doc": 169,
    "fur2_dep.doc": 160,
    "fur3_tda.doc": 158,
    "fur4_ci_t.doc": 159,
    "fur5_ci_p.doc": 139,
    "fur6_dm.doc": 127,
    "fur7_dv.doc": 129,
    "fur8_da.doc": 129,
    "fur9_dmu.doc": 160,
    "fur10_tea.doc": 154,
    "fur11_dstc.doc": 157,
}
