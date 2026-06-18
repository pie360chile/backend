"""Extrae indicadores de los 10 Vue pedagógicos → constants/pedagogicalEvaluationGrades.ts"""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "admin-frontend"
COMPONENTS = ROOT / "src" / "views" / "project" / "components"
OUT = ROOT / "src" / "constants" / "pedagogicalEvaluationGrades.ts"

FILES = {
    "firstGrade": "PedagogicalEvaluationClassroomFirstGrade.vue",
    "secondGrade": "PedagogicalEvaluationClassroomSecondGrade.vue",
    "thirdGrade": "PedagogicalEvaluationClassroomThirdGrade.vue",
    "fourthGrade": "PedagogicalEvaluationClassroomFourthGrade.vue",
    "fifthGrade": "PedagogicalEvaluationClassroomFifthGrade.vue",
    "sixthGrade": "PedagogicalEvaluationClassroomSixthGrade.vue",
    "seventhGrade": "PedagogicalEvaluationClassroomSeventhGrade.vue",
    "eighthGrade": "PedagogicalEvaluationClassroomEighthGrade.vue",
    "firstGradeSecondary": "PedagogicalEvaluationClassroomFirstGradeSecondary.vue",
    "secondGradeSecondary": "PedagogicalEvaluationClassroomSecondGradeSecondary.vue",
}

RESOURCE_BY_KEY = {
    "firstGrade": "pedagogical_evaluation_classroom_first_grade",
    "secondGrade": "pedagogical_evaluation_classroom_second_grade",
    "thirdGrade": "pedagogical_evaluation_classroom_third_grade",
    "fourthGrade": "pedagogical_evaluation_classroom_fourth_grade",
    "fifthGrade": "pedagogical_evaluation_classroom_fifth_grade",
    "sixthGrade": "pedagogical_evaluation_classroom_sixth_grade",
    "seventhGrade": "pedagogical_evaluation_classroom_seventh_grade",
    "eighthGrade": "pedagogical_evaluation_classroom_eighth_grade",
    "firstGradeSecondary": "pedagogical_evaluation_classroom_first_grade_secondary",
    "secondGradeSecondary": "pedagogical_evaluation_classroom_second_grade_secondary",
}

DOC_ID_BY_KEY = {
    "firstGrade": 31,
    "secondGrade": 32,
    "thirdGrade": 33,
    "fourthGrade": 34,
    "fifthGrade": 35,
    "sixthGrade": 36,
    "seventhGrade": 37,
    "eighthGrade": 38,
    "firstGradeSecondary": 39,
    "secondGradeSecondary": 40,
}


def extract_const_array(text: str, name: str) -> list[str]:
    m = re.search(rf"const {name}\s*=\s*\[(.*?)\]\s*as const", text, re.S)
    if not m:
        m = re.search(rf"const {name}\s*=\s*\[(.*?)\];", text, re.S)
    if not m:
        return []
    return re.findall(r"'((?:\\'|[^'])*)'|\"((?:\\\"|[^\"])*)\"", m.group(1))


def extract_grade_title(text: str) -> str:
    m = re.search(r"Document \d+[^*]*-\s*([^\.\n]+)", text)
    if m:
        return m.group(1).strip()
    return ""


def extract_language_section_title(text: str) -> str:
    if "Lengua y literatura" in text:
        return "IV. Lengua y literatura"
    return "IV. Lenguaje y comunicación"


def extract_course_placeholder(text: str) -> str:
    m = re.search(r'placeholder="([^"]*curso[^"]*)"', text, re.I)
    return m.group(1) if m else "Ej: 1º Básico A"


configs = {}
for key, fname in FILES.items():
    text = (COMPONENTS / fname).read_text(encoding="utf-8")
    att = extract_const_array(text, "ATTITUDE_INDICATORS")
    lang = extract_const_array(text, "LANGUAGE_INDICATORS")
    math = extract_const_array(text, "MATH_INDICATORS")
    att = [a or b for a, b in att]
    lang = [a or b for a, b in lang]
    math = [a or b for a, b in math]
    configs[key] = {
        "documentId": DOC_ID_BY_KEY[key],
        "resourcePath": RESOURCE_BY_KEY[key],
        "gradeTitle": extract_grade_title(text),
        "languageSectionTitle": extract_language_section_title(text),
        "coursePlaceholder": extract_course_placeholder(text),
        "attitudeIndicators": att,
        "languageIndicators": lang,
        "mathIndicators": math,
        "pdfSlug": RESOURCE_BY_KEY[key].replace("pedagogical_evaluation_classroom_", ""),
    }

lines = [
    '/** Config por grado — docs 31–40 (pauta evaluación pedagógica docente de aula). */',
    "import type { PedagogicalEvaluationApiService } from '@/shared/api/pedagogicalEvaluationClassroomApi';",
    "import { createPedagogicalEvaluationClassroomService } from '@/shared/api/pedagogicalEvaluationClassroomApi';",
    "",
    "export type PedagogicalGradeKey = keyof typeof PEDAGOGICAL_GRADE_CONFIGS;",
    "",
    "export interface PedagogicalGradeConfig {",
    "  key: PedagogicalGradeKey;",
    "  documentId: number;",
    "  resourcePath: string;",
    "  gradeTitle: string;",
    "  languageSectionTitle: string;",
    "  coursePlaceholder: string;",
    "  attitudeIndicators: readonly string[];",
    "  languageIndicators: readonly string[];",
    "  mathIndicators: readonly string[];",
    "  pdfSlug: string;",
    "  service: PedagogicalEvaluationApiService;",
    "}",
    "",
    "const rawConfigs = ",
    json.dumps(configs, ensure_ascii=False, indent=2),
    " as const;",
    "",
    "export const PEDAGOGICAL_GRADE_CONFIGS = Object.fromEntries(",
    "  Object.entries(rawConfigs).map(([key, cfg]) => [",
    "    key,",
    "    {",
    "      ...cfg,",
    "      key: key as PedagogicalGradeKey,",
    "      service: createPedagogicalEvaluationClassroomService(cfg.resourcePath),",
    "    },",
    "  ])",
    ") as Record<PedagogicalGradeKey, PedagogicalGradeConfig>;",
    "",
    "export const PEDAGOGICAL_GRADE_BY_DOCUMENT_ID: Record<number, PedagogicalGradeKey> = {",
]
for key, cfg in configs.items():
    lines.append(f"  {cfg['documentId']}: '{key}',")
lines += [
    "};",
    "",
    "export function getPedagogicalGradeConfig(documentTypeId: number): PedagogicalGradeConfig | null {",
    "  const key = PEDAGOGICAL_GRADE_BY_DOCUMENT_ID[documentTypeId];",
    "  return key ? PEDAGOGICAL_GRADE_CONFIGS[key] : null;",
    "}",
    "",
]

OUT.write_text("\n".join(lines), encoding="utf-8")
print("Wrote", OUT, "grades:", len(configs))
