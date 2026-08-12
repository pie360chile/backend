# -*- coding: utf-8 -*-
"""Carga respuestas de Heidan Mauna (Excel especialistas) al formulario PIE360."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.backend.data.psychoped_observation_questionnaire import (
    FORM_DESCRIPTION,
    FORM_NAME,
    questionnaire_fields,
)
from app.backend.db.database import SessionLocal
from app.backend.db.models.pie_core import DynamicFormModel, DynamicFormSubmissionModel

STUDENT_ID = 1593
SCHOOL_ID = 5
COURSE_ID = 1690
PERIOD_YEAR = 2026

EXCEL = next(
    Path(r"C:/Users/jesus/Downloads").glob("*(E) Cuestionario*Especialistas*respuestas*.xlsx")
)


def fold(s: str) -> str:
    raw = unicodedata.normalize("NFKD", s or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", raw).strip()


def normalize_scale(v: str) -> str:
    mapping = {
        "logrado": "LOGRADO",
        "en proceso": "EN PROCESO",
        "requiere apoyo": "REQUIERE APOYO",
        "no observado": "NO OBSERVADO",
    }
    key = fold(v)
    return mapping.get(key, (v or "").strip().upper() or "NO OBSERVADO")


def field_keys(field: dict) -> list[str]:
    section = (field.get("section") or "").strip()
    q = (field.get("question") or "").strip()
    keys = [fold(q)]
    if section and q:
        keys.append(fold(f"{section}: [{q}]"))
        keys.append(fold(f"{section} [{q}]"))
        keys.append(fold(f"{section}: {q}"))
    return [k for k in keys if k]


def map_row_to_answers(row: pd.Series, fields: list[dict]) -> dict[str, str]:
    col_fold = {fold(str(c)): str(c) for c in row.index}
    answers: dict[str, str] = {}
    for field in fields:
        fid = str(field["id"])
        found = None
        for key in field_keys(field):
            if key in col_fold:
                found = col_fold[key]
                break
        if found is None:
            # fuzzy: header contains question snippet
            q = fold(field.get("question") or "")
            snippet = q[:48]
            for hk, original in col_fold.items():
                if snippet and snippet in hk:
                    found = original
                    break
        raw = str(row.get(found, "") if found else "").strip()
        answers[fid] = normalize_scale(raw) if raw else "NO OBSERVADO"
    return answers


def main() -> None:
    df = pd.read_excel(EXCEL, dtype=str).fillna("")
    mask = df.apply(
        lambda r: r.astype(str).str.contains("heidan", case=False, regex=True).any(),
        axis=1,
    )
    hits = df[mask]
    if hits.empty:
        raise SystemExit("No hay filas de Heidan en el Excel")

    fields = questionnaire_fields()
    db = SessionLocal()
    try:
        form = (
            db.query(DynamicFormModel)
            .filter(DynamicFormModel.deleted_date.is_(None))
            .filter(DynamicFormModel.school_id == SCHOOL_ID)
            .filter(DynamicFormModel.course_id == COURSE_ID)
            .filter(DynamicFormModel.period_year == PERIOD_YEAR)
            .filter(DynamicFormModel.name == FORM_NAME)
            .first()
        )
        now = datetime.now()
        if not form:
            form = DynamicFormModel(
                school_id=SCHOOL_ID,
                course_id=COURSE_ID,
                period_year=PERIOD_YEAR,
                name=FORM_NAME,
                description=FORM_DESCRIPTION,
                fields_json=json.dumps(fields, ensure_ascii=False),
                added_date=now,
                updated_date=now,
            )
            db.add(form)
            db.commit()
            db.refresh(form)
            print("created form", form.id)
        else:
            form.fields_json = json.dumps(fields, ensure_ascii=False)
            form.updated_date = now
            db.commit()
            print("updated form", form.id)

        for _, row in hits.iterrows():
            specialty = str(row.get("Especialidad") or "").strip()
            respondent = str(row.get("Nombre especialista") or "").strip()
            answers = map_row_to_answers(row, fields)
            # sanity: keep same length as questionnaire
            if len(answers) != len(fields):
                print("warn field count", len(answers), len(fields))

            existing = (
                db.query(DynamicFormSubmissionModel)
                .filter(DynamicFormSubmissionModel.dynamic_form_id == form.id)
                .filter(DynamicFormSubmissionModel.student_id == STUDENT_ID)
                .filter(DynamicFormSubmissionModel.specialty == specialty)
                .filter(DynamicFormSubmissionModel.respondent_name == respondent)
                .first()
            )
            payload = json.dumps(answers, ensure_ascii=False)
            if existing:
                existing.answers_json = payload
                existing.updated_date = now
                existing.period_year = PERIOD_YEAR
                print("updated submission", existing.id, specialty, respondent)
            else:
                sub = DynamicFormSubmissionModel(
                    dynamic_form_id=form.id,
                    student_id=STUDENT_ID,
                    school_id=SCHOOL_ID,
                    period_year=PERIOD_YEAR,
                    specialty=specialty or None,
                    respondent_name=respondent or None,
                    answers_json=payload,
                    submitted_by_user_id=None,
                    added_date=now,
                    updated_date=now,
                )
                db.add(sub)
                db.flush()
                print("created submission", sub.id, specialty, respondent)
        db.commit()

        n = (
            db.query(DynamicFormSubmissionModel)
            .filter(DynamicFormSubmissionModel.dynamic_form_id == form.id)
            .filter(DynamicFormSubmissionModel.student_id == STUDENT_ID)
            .count()
        )
        print("ok form_id", form.id, "heidan_submissions", n)
    finally:
        db.close()


if __name__ == "__main__":
    main()
