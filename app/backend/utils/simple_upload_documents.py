"""Shared list of catalog document IDs that use file-upload only (no long form)."""

# Keep in sync with admin-frontend/src/constants/simpleUploadDocuments.ts
SIMPLE_UPLOAD_DOCUMENT_IDS: tuple[int, ...] = (
    41,  # Kinesio evaluación informal
    44,  # Fono PEFE
    45,  # Fono STSG/TECAL/TEPROSIF
    46,  # Kinesio Vitor Da Fonseca
    47,  # ABAS II
    48,  # ICAP
    49,  # WAIS IV
    50,  # WISC V
    51,  # TO Evaluación Informal
    52,  # TO Perfil Sensorial
    53,  # TO SPM-2
)

# Preferred display order (names as stored in `documents.document`)
SIMPLE_UPLOAD_DOC_ORDER: tuple[str, ...] = (
    "Informe Fonoaudiológico - PEFE",
    "Informe Fonoaudiológico - STSG, TECAL y TEPROSIF",
    "Informe kinesiológico - Evaluación informal",
    "Informe Kinesiológica - Vitor Da Fonseca",
    "Informe de conducta adaptativa – ABAS II",
    "Informe de conducta adaptativa – ICAP",
    "Informe Psicológico – WAIS IV",
    "Informe Psicológico – WISC V",
    "Informe Terapia Ocupacional - Evaluación Informal",
    "Informe Terapia Ocupacional - Perfil Sensorial",
    "Informe Terapia Ocupacional - SPM-2",
)
