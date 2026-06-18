from pydantic import BaseModel, Field, EmailStr, validator, field_validator, ConfigDict, AliasChoices
from typing import Union, List, Dict, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
import json

from app.backend.schemas.helpers import _empty_str_to_none  # noqa: F401

class StorePedagogicalEvaluationClassroomFirstGrade(BaseModel):
    """Document 31 – Pauta de evaluación pedagógica - Docente de aula - 1º Básico (first grade)."""
    student_id: int
    document_type_id: Optional[int] = 31
    # IV. Lenguaje – varios valores separados por coma (checkboxes)
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomFirstGrade(BaseModel):
    """Document 31 – Actualización. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"


# Document 32 – Pauta de evaluación pedagógica - Docente de aula - 2º Básico (second grade)

class StorePedagogicalEvaluationClassroomSecondGrade(BaseModel):
    """Document 32 – Pauta de evaluación pedagógica - Docente de aula - 2º Básico."""
    student_id: int
    document_type_id: Optional[int] = 32
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomSecondGrade(BaseModel):
    """Document 32 – Actualización. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomThirdGrade(BaseModel):
    """Document 33 – Pauta de evaluación pedagógica - Docente de aula - 3º Básico."""
    student_id: int
    document_type_id: Optional[int] = 33
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomThirdGrade(BaseModel):
    """Document 33 – Actualización. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomFourthGrade(BaseModel):
    """Document 34 - Pauta de evaluacion pedagogica - Docente de aula - 4to Basico."""
    student_id: int
    document_type_id: Optional[int] = 34
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomFourthGrade(BaseModel):
    """Document 34 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomFifthGrade(BaseModel):
    """Document 35 - Pauta de evaluacion pedagogica - Docente de aula - 5to Basico."""
    student_id: int
    document_type_id: Optional[int] = 35
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomFifthGrade(BaseModel):
    """Document 35 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomSixthGrade(BaseModel):
    """Document 36 - Pauta de evaluacion pedagogica - Docente de aula - 6to Basico."""
    student_id: int
    document_type_id: Optional[int] = 36
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomSixthGrade(BaseModel):
    """Document 36 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomSeventhGrade(BaseModel):
    """Document 37 - Pauta de evaluacion pedagogica - Docente de aula - 7mo Basico."""
    student_id: int
    document_type_id: Optional[int] = 37
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomSeventhGrade(BaseModel):
    """Document 37 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomEighthGrade(BaseModel):
    """Document 38 - Pauta de evaluacion pedagogica - Docente de aula - 8vo Basico."""
    student_id: int
    document_type_id: Optional[int] = 38
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomEighthGrade(BaseModel):
    """Document 38 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomFirstGradeSecondary(BaseModel):
    """Document 39 - Pauta de evaluacion pedagogica - Docente de aula - 1ero Medio."""
    student_id: int
    document_type_id: Optional[int] = 39
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomFirstGradeSecondary(BaseModel):
    """Document 39 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class StorePedagogicalEvaluationClassroomSecondGradeSecondary(BaseModel):
    """Document 40 - Pauta de evaluacion pedagogica - Docente de aula - 2do Medio."""
    student_id: int
    document_type_id: Optional[int] = 40
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

class UpdatePedagogicalEvaluationClassroomSecondGradeSecondary(BaseModel):
    """Document 40 - Actualizacion. Acepta todos los campos del formulario."""
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    reading_type: Optional[str] = None
    comprehension_level: Optional[str] = None
    writing_level: Optional[str] = None

    class Config:
        extra = "allow"

