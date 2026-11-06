"""Prueba: importa anamnesis de Dafnika desde Excel TRANSCRITO + PDF Drive."""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_TUNNEL_DB_URL = (
    "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.backend.classes.anamnesis_class import ANAMNESIS_DOCUMENT_ID, AnamnesisClass
from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
from app.backend.db.models import AnamnesisModel, FolderModel
from app.backend.utils.google_drive_storage import upload_student_document_tree
from scripts.import_drive_anamnesis import (
    _access_token,
    _download_drive_file,
    _resolve_drive_meta,
    _student_files_dir,
    _truncate_payload_strings,
)

os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or DEFAULT_TUNNEL_DB_URL

STUDENT_ID = 1851
DRIVE_FILE_ID = "1KVUTB9W91Z3IfB7G_24RTTnc3V5X3miR"
XLSX = Path(
    r"C:\Users\jesus\Downloads\Dafnika_Saint-Fort_Albert_2C_Basica_Liceo_Mixto_San_Felipe.xlsx"
)


def _yn(val: str | None) -> int | None:
    if not val:
        return None
    s = val.strip().lower()
    if s in {"si", "sí", "yes", "s"}:
        return 1
    if s in {"no", "n"}:
        return 2
    return None


def _parse_date(val: str | None) -> str | None:
    if not val:
        return None
    s = val.strip()
    months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
        "noviembre": 11, "diciembre": 12,
    }
    m = re.match(r"(\d{1,2})/([A-Za-zÁÉÍÓÚáéíóú]+)/(\d{4})", s)
    if m:
        d = int(m.group(1))
        mo = months.get(m.group(2).lower())
        y = int(m.group(3))
        if mo:
            try:
                return date(y, mo, d).isoformat()
            except ValueError:
                return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _domain(val: str | None) -> list[str]:
    if not val:
        return []
    mapping = {
        "comprende": "understand",
        "habla": "speak",
        "lee": "read",
        "escribe": "write",
    }
    out = []
    for part in re.split(r"[;,/]", val):
        key = part.strip().lower()
        if key in mapping:
            out.append(mapping[key])
    return out


def _load_qa(path: Path) -> dict[str, str]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Preguntas_respuestas"]
    qa: dict[str, str] = {}
    household: dict[int, dict[str, str]] = {}
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if i == 1 or not row or not row[0]:
            continue
        pregunta = str(row[0]).strip()
        respuesta = "" if row[1] is None else str(row[1]).strip()
        estado = "" if row[2] is None else str(row[2]).strip()
        if estado != "TRANSCRITO":
            continue
        # household person fields share same pregunta prefix; keep last by attribute in full key
        qa[pregunta] = respuesta
        m = re.match(
            r"Persona (\d+) que vive con el/la estudiante o es responsable de su cuidado - (.+)$",
            pregunta,
            re.I,
        )
        if m:
            idx = int(m.group(1))
            attr = m.group(2).strip().lower()
            household.setdefault(idx, {})
            if "nombre" in attr:
                household[idx]["name"] = respuesta
            elif "parentesco" in attr:
                household[idx]["relationship"] = respuesta
            elif "edad" in attr:
                household[idx]["age"] = respuesta
            elif "escolaridad" in attr:
                household[idx]["schooling"] = respuesta
            elif "ocupacion" in attr or "ocupación" in attr:
                household[idx]["occupation"] = respuesta
    qa["__household__"] = household  # type: ignore[assignment]
    return qa


def _get(qa: dict[str, str], *keys: str) -> str | None:
    for k in keys:
        if k in qa and qa[k]:
            return qa[k]
        # fuzzy contains
        for pk, pv in qa.items():
            if pk.startswith("__"):
                continue
            if k.lower() in pk.lower() and pv:
                return pv
    return None


def build_payload(qa: dict[str, Any]) -> dict[str, Any]:
    g = lambda *ks: _get(qa, *ks)  # noqa: E731

    birth_type = {"normal": 1, "cesárea": 2, "cesarea": 2, "asistido": 3, "fórceps": 4, "forceps": 4}
    bt = g("Tipo de parto")
    birth_type_id = birth_type.get((bt or "").strip().lower())

    fyc = {}
    for label, key in [
        ("Desnutrición", "desnutricion"),
        ("Obesidad", "obesidad"),
        ("Fiebre alta", "fiebre_alta"),
        ("Convulsiones", "convulsiones"),
        ("Hospitalizaciones", "hospitalizaciones"),
        ("Traumatismos", "traumatismos"),
        ("Intoxicación", "intoxicacion"),
        ("Enfermedad respiratoria", "enfermedad_respiratoria"),
        ("Asma", "asma"),
        ("Encefalitis", "encefalitis"),
        ("Meningitis", "meningitis"),
    ]:
        yn = _yn(g(f"Durante los doce primeros meses de vida presentó - {label}"))
        if yn is not None:
            fyc[key] = yn

    # household
    hh_raw = qa.get("__household__") or {}
    household_members = []
    for idx in sorted(hh_raw.keys()):
        item = hh_raw[idx]
        if any(item.values()):
            household_members.append(
                {
                    "sort_order": idx - 1,
                    "name": item.get("name"),
                    "relationship": item.get("relationship"),
                    "age": item.get("age"),
                    "schooling": item.get("schooling"),
                    "occupation": item.get("occupation"),
                }
            )

    informants = []
    inf_date = g("Informante 1 - Fecha de la entrevista")
    inf_rel = g("Informante 1 - Relación con el/la estudiante")
    if inf_date or inf_rel:
        informants.append(
            {
                "sort_order": 0,
                "name": None,  # REVISAR en excel
                "relationship": inf_rel,
                "presence": None,
                "interview_date": _parse_date(inf_date),
            }
        )

    interviewers = []
    int_date = g("Entrevistador 1 - Fecha de la entrevista")
    int_role = g("Entrevistador 1 - Rol/cargo")
    if int_date or int_role:
        interviewers.append(
            {
                "sort_order": 0,
                "professional_id": None,
                "role": int_role,
                "interview_date": _parse_date(int_date),
            }
        )

    modality = (g("Modalidad de enseñanza") or "").strip().lower()
    modality_map = {"regular": "regular", "especial": "especial", "técnica": "tecnica", "tecnica": "tecnica"}
    expectations = (g("¿Qué expectativas muestra la familia frente al futuro escolar del estudiante?") or "").strip().lower()
    exp_map = {"alta": "alta", "mediana": "mediana", "baja": "baja"}
    env = (g("¿Ofrece la familia un ambiente físico y emocional adecuado para el aprendizaje?") or "").strip().lower()
    env_map = {"ambos": "ambos", "fisico": "fisico", "físico": "fisico", "emocional": "emocional"}
    perf = (g("¿Cómo evalúa la familia el desempeño escolar del estudiante?") or "").strip().lower()
    perf_map = {"satisfactorio": "satisfactorio", "insatisfactorio": "insatisfactorio"}

    diet = (g("Alimentación") or "").strip()
    weight = (g("Peso (apreciación del informante)") or "").strip()
    sleep = (g("Sueño") or "").strip()
    sleeps = (g("Duerme") or "").strip()
    motor = (g("En su actividad motora general se aprecia") or "").strip()
    tone = (g("Su tono muscular general se aprecia") or g("tono muscular") or "").strip()
    # Dominancia: excel says No oddly — skip if No
    lat = (g("Dominancia lateral") or "").strip()
    lat_val = None
    if lat.lower() in {"der", "derecha"}:
        lat_val = "Der"
    elif lat.lower() in {"izq", "izquierda"}:
        lat_val = "Izq"

    lang_method = (g("El niño(a) se comunica preferentemente en forma") or "").strip()
    if lang_method:
        lang_method = lang_method.capitalize() if lang_method.lower() != "mixto" else "Mixto"

    response_diff = g("¿Cuál es la respuesta de la familia frente a las dificultades escolares")
    response_ok = g("¿Cuál es la respuesta de la familia frente a los éxitos escolares")
    supporters = g("¿Quiénes apoyan el proceso de aprendizaje y desarrollo del estudiante?")
    rewards = g("Especifique el tipo de refuerzos o premios")

    payload: dict[str, Any] = {
        "student_id": STUDENT_ID,
        "student_full_name": g("Nombre"),
        "born_date": _parse_date(g("Fecha Nacimiento")),
        "age": g("Edad actual - años"),
        "address": g("Domicilio actual"),
        "phone": g("Teléfono"),
        "native_language": g("Lengua materna"),
        "native_language_domain": _domain(g("Lengua materna - grado de dominio")),
        "language_used": g("Lengua de uso"),
        "language_used_domain": _domain(g("Lengua de uso - grado de dominio")),
        "current_schooling": g("Escolaridad actual"),
        "school_name": g("Establecimiento"),
        "interview_reason": g("Definición del problema o situación que motiva la entrevista"),
        "diagnosis_has": _yn(g("¿El o la estudiante tiene algún diagnóstico previo?")),
        "diagnosis_detail": (
            "; ".join(
                f"{label}: {val}"
                for label in (
                    "Pediatría",
                    "Kinesiología",
                    "Genético",
                    "Fonoaudiología",
                    "Neurología",
                    "Psicología",
                    "Psiquiatría",
                    "Psicopedagogía",
                    "Terapia Ocupacional",
                    "Otro",
                )
                if (val := g(f"Diagnóstico previo - {label}"))
            )
            or None
        ),
        "birth_type_id": birth_type_id,
        "birth_medical_assistance": _yn(g("¿Tuvo asistencia médica durante el parto?")),
        "birth_weight": g("Peso"),
        "birth_height": g("Talla"),
        "first_year_notes": g("Señale antecedentes relevantes del Embarazo y Parto"),
        "first_year_conditions": fyc or None,
        "first_year_periodic_health_checkups": _yn(g("Se realizaron controles periódicos de salud")),
        "first_year_vaccines": _yn(g("Vacunas")),
        "first_year_observations": "Sin antecedentes.",
        "sm_head_control": g("Edad en que fija la cabeza"),
        "sm_sits_alone": g("Edad en que se sienta sólo/a"),
        "sm_walks_without_support": g("Edad en que camina sin apoyo"),
        "sm_first_words": g("Edad de primeras palabras"),
        "sm_first_phrases": g("Edad de primeras frases"),
        "sm_dresses_alone": g("Edad en que se viste solo/a"),
        "sm_bladder_day": g("Controla esfínter vesical - Diurno"),
        "sm_bladder_night": g("Controla esfínter vesical - Nocturno"),
        "sm_bowel_day": g("Controla esfínter anal - Diurno"),
        "sm_bowel_night": g("Controla esfínter anal - Nocturno"),
        "sm_observations_1": g("Observaciones sobre edades de desarrollo"),
        "sm_motor_activity": motor or None,
        "sm_muscle_tone": tone or None,
        "sm_walking_stability": _yn(g("Estabilidad al caminar")),
        "sm_frequent_falls": _yn(g("Caídas frecuentes")),
        "sm_lateral_dominance": lat_val,
        "sm_fine_grab": _yn(g("En relación con su motricidad fina el niño(a) logra - Garra")),
        "sm_fine_grip": _yn(g("En relación con su motricidad fina el niño(a) logra - Prensión")),
        "sm_fine_pinch": _yn(g("En relación con su motricidad fina el niño(a) logra - Pinza")),
        "sm_fine_thread": _yn(g("En relación con su motricidad fina el niño(a) logra - Ensarta")),
        "sm_fine_draw": _yn(g("En relación con su motricidad fina el niño(a) logra - Dibuja")),
        "sm_fine_write": _yn(g("En relación con su motricidad fina el niño(a) logra - Escribe")),
        "sm_cog_reacts_familiar": _yn(g("Reacciona a voces o caras familiares")),
        "sm_cog_demands_company": _yn(g("Demanda objetos y compañía")),
        "sm_cog_smiles_babbles": _yn(g("Sonríe, balbucea, grita, llora, indica o señala")),
        "sm_cog_manipulates_explores": _yn(g("Manipula y explora objetos")),
        "sm_cog_understands_prohibitions": _yn(g("Comprende prohibiciones")),
        "sm_cog_poor_eye_hand": _yn(g("Posee evidente descoordinación ojo-mano")),
        "sm_observations_2": g("Observaciones sobre actividad motora y signos cognitivos"),
        "vision_interested_stimuli": _yn(g("Se interesa por los estímulos visuales")),
        "vision_irritated_eyes": _yn(g("En ocasiones tiene los ojos irritados o llorosos")),
        "vision_headaches": _yn(g("Presenta dolores frecuentes de cabeza")),
        "vision_squints": _yn(g("Se acerca o aleja demasiado los objetos a la vista")),
        "vision_follows_movement": _yn(g("Sigue con la vista el desplazamiento")),
        "vision_abnormal_movements": _yn(g("Presenta movimientos oculares anormales")),
        "vision_erroneous_behaviors": _yn(g("Manifiesta conductas erróneas")),
        "vision_diagnosis": _yn(g("Presenta diagnóstico médico de miopía")),
        "hearing_interested_stimuli": _yn(g("Se interesa por los estímulos auditivos")),
        "hearing_recognizes_voices": _yn(g("Reacciona o reconoce voces o sonidos familiares")),
        "hearing_turns_head": _yn(g("Gira la cabeza cuando se le llama")),
        "hearing_ears_to_tv": _yn(g("Acerca los oídos a la TV")),
        "hearing_covers_ears": _yn(g("En ocasiones se tapa o golpea los oídos")),
        "hearing_earaches": _yn(g("Presenta frecuentes dolores de oídos")),
        "hearing_pronunciation_adequate": _yn(g("La pronunciación oral es adecuada")),
        "hearing_diagnosis": _yn(g("Presenta diagnóstico médico de otitis crónica")),
        "vision_hearing_observations": "Sin antecedentes.",
        "language_communication_method": lang_method,
        "language_exp_babbles": _yn(g("Balbucea (oral o señas)/emite sonidos")),
        "language_exp_vocalizes_gestures": _yn(g("Vocaliza/realiza gestos o señas aisladas")),
        "language_exp_emits_words": _yn(g("Emite palabras/produce señas")),
        "language_exp_emits_phrases": _yn(g("Emite/produce frases")),
        "language_exp_relates_experiences": _yn(g("Relata experiencias")),
        "language_exp_clear_pronunciation": _yn(g("La emisión/pronunciación/producción es clara")),
        "language_comp_identifies_objects": _yn(g("Identifica objetos")),
        "language_comp_identifies_people": _yn(g("Identifica personas")),
        "language_comp_understands_abstract": _yn(g("Comprende conceptos abstractos")),
        "language_comp_responds_coherently": _yn(g("Responde en forma coherente preguntas de la vida diaria")),
        "language_comp_follows_simple_instructions": _yn(g("Sigue instrucciones simples")),
        "language_comp_follows_complex_instructions": _yn(g("Sigue instrucciones complejas")),
        "language_comp_follows_group_instructions": _yn(g("Sigue instrucciones grupales")),
        "language_observations": "Sin antecedentes.",
        "social_relates_spontaneously": _yn(g("Se relaciona espontáneamente con las personas de su entorno natural")),
        "social_participates_groups": _yn(g("Participa en actividades grupales")),
        "social_echolalic_language": _yn(g("Presenta lenguaje ecolálico")),
        "social_difficulty_adapting": _yn(g("Exhibe dificultad para adaptarse a situaciones nuevas")),
        "social_relates_collaboratively": _yn(g("Se relaciona en forma colaborativa")),
        "social_respects_social_norms": _yn(g("Respeta normas sociales")),
        "social_respects_school_norms": _yn(g("Respeta normas escolares")),
        "social_shows_humor": _yn(g("Muestra sentido del humor")),
        "social_stereotyped_movements": _yn(g("Movimientos estereotipados")),
        "social_frequent_tantrums": _yn(g("Pataletas frecuentes")),
        "social_reaction_lights": (g("Ante las luces su reacción es") or "").capitalize() or None,
        "social_reaction_sounds": (g("Ante los sonidos su reacción es") or "").capitalize() or None,
        "social_reaction_strange_people": (g("Ante personas extrañas su reacción es") or "").capitalize() or None,
        "social_observations": "Sin antecedentes.",
        "health_vaccines_up_to_date": _yn(g("Vacunas al día")),
        "health_epilepsy": _yn(g("Epilepsia")),
        "health_heart_problems": _yn(g("Problemas cardíacos")),
        "health_paraplegia": _yn(g("Paraplejia")),
        "health_hearing_loss": _yn(g("Pérdida auditiva")),
        "health_vision_loss": _yn(g("Pérdida visual")),
        "health_motor_disorder": _yn(g("Trastorno motor")),
        "health_bronchorespiratory": _yn(g("Problema bronco-respiratorio")),
        "health_infectious_disease": _yn(g("Enfermedad infecto-contagiosa")),
        "health_emotional_disorder": _yn(g("Trastorno emocional")),
        "health_behavioral_disorder": _yn(g("Trastorno conductual")),
        "health_problems_treatment": g("El o los problemas de salud reciben control/tratamiento (especifique)"),
        "health_diet": diet if diet in {"Normal", "Malo", "Bueno", "Otro"} else diet,
        "health_weight": weight if weight else None,
        "health_sleep_pattern": sleep if sleep else None,
        "health_sleep_hours": g("Horas que duerme"),
        "health_sleeps_alone": sleeps if sleeps in {"Solo", "Acompañado"} else sleeps,
        "health_mood_behavior": g("Humor/comportamiento habitual"),
        "health_current_observations": "Sin antecedentes.",
        "family_health_history": g("Antecedentes de Salud de la Familia relevantes"),
        "school_entry_age": g("Edad de ingreso al sistema escolar"),
        "attended_kindergarten": _yn(g("Asistió a jardín infantil")),
        "schools_count": g("N° de colegios en que ha estudiado"),
        "teaching_modality": modality_map.get(modality),
        "repeated_grade": _yn(g("Ha repetido curso/s")),
        "current_level": g("Nivel/curso actual"),
        "learning_difficulty": _yn(g("Dificultad de aprendizaje")),
        "participation_difficulty": _yn(g("Dificultad para participar")),
        "disruptive_behavior": _yn(g("Conducta disruptiva")),
        "attends_regularly": _yn(g("Asiste regularmente")),
        "attends_gladly": _yn(g("Asiste con agrado")),
        "family_support_homework": _yn(g("Apoyo familiar en tareas")),
        "friends": _yn(g("Amigos(as)")),
        "performance_assessment": perf_map.get(perf),
        "response_difficulties": [response_diff] if response_diff else None,
        "response_success": [response_ok] if response_ok else None,
        "rewards": [rewards] if rewards else None,
        "supporters": [s.strip() for s in re.split(r"[;]", supporters or "") if s.strip()] or None,
        "expectations": next((v for k, v in exp_map.items() if k in expectations), None),
        "environment": env_map.get(env) or ("ambos" if env == "ambos" else None),
        "final_comments": g("Comentarios u otras observaciones relevantes que no se han registrado"),
        "informants": informants or None,
        "interviewers": interviewers or None,
        "household_members": household_members or None,
    }
    # gender F
    sexo = (g("Sexo") or "").strip().upper()
    if sexo.startswith("F"):
        payload["gender_id"] = 2
    elif sexo.startswith("M"):
        payload["gender_id"] = 1

    # clean Nones
    return {k: v for k, v in payload.items() if v is not None and v != ""}


def purge_student(db, student_id: int) -> None:
    folders = (
        db.query(FolderModel)
        .filter(
            FolderModel.student_id == student_id,
            FolderModel.document_id == ANAMNESIS_DOCUMENT_ID,
            FolderModel.file.like("%anamnesis_drive.pdf"),
        )
        .all()
    )
    detail_ids = {int(f.detail_id) for f in folders if f.detail_id}
    for f in folders:
        db.execute(text("DELETE FROM student_drive_sync_jobs WHERE folder_id = :fid"), {"fid": int(f.id)})
        path = _student_files_dir() / (f.file or "")
        if path.is_file():
            path.unlink(missing_ok=True)
        db.delete(f)
    # también anamnesis recientes del estudiante si vienen de import
    rows = db.query(AnamnesisModel).filter(AnamnesisModel.student_id == student_id).all()
    for r in rows:
        if detail_ids and int(r.id) not in detail_ids and len(rows) > 1:
            # borrar todas las del estudiante en esta prueba limpia
            pass
        for table in ("anamnesis_informants", "anamnesis_interviewers", "anamnesis_household_members"):
            try:
                db.execute(text(f"DELETE FROM {table} WHERE anamnesis_id = :aid"), {"aid": int(r.id)})
            except Exception:
                pass
        db.delete(r)
    db.commit()
    print(f"purged student={student_id} folders={len(folders)} anamnesis={len(rows)}")


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    purge_student(db, STUDENT_ID)

    qa = _load_qa(XLSX)
    payload = _truncate_payload_strings(build_payload(qa))
    filled = [k for k, v in payload.items() if v not in (None, "", [], {}) and k != "student_id"]
    print(f"payload fields={len(filled)}")

    store = AnamnesisClass(db).store(payload)
    if isinstance(store, dict) and store.get("status") == "error":
        raise RuntimeError(store.get("message"))
    anamnesis_id = store.get("id")
    version = store.get("version")
    print(f"stored anamnesis id={anamnesis_id} v={version}")

    token = _access_token(db)
    content = _download_drive_file(token, DRIVE_FILE_ID)
    meta = _resolve_drive_meta(db, student_id=STUDENT_ID, period_year="2026")
    pdf_filename = f"{STUDENT_ID}_{ANAMNESIS_DOCUMENT_ID}_anamnesis_drive.pdf"
    target = _student_files_dir() / pdf_filename
    target.write_bytes(content)

    folder_store = FolderClass(db).store(
        student_id=STUDENT_ID,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=pdf_filename,
        school_id=meta["school_id"],
        course_id=meta.get("course_id"),
        period_year="2026",
    )
    if isinstance(folder_store, dict) and folder_store.get("status") == "error":
        raise RuntimeError(folder_store.get("message"))
    folder_id = folder_store.get("id") if isinstance(folder_store, dict) else folder_store
    folder_row = db.query(FolderModel).filter(FolderModel.id == int(folder_id)).first()
    if folder_row and anamnesis_id:
        folder_row.detail_id = int(anamnesis_id)
        db.commit()

    drive_payload = upload_student_document_tree(
        db=db,
        customer_id=meta["customer_id"],
        school_name=meta["school_name"],
        year=meta["year"],
        course_name=meta["course_name"],
        student_rut=meta["student_rut"],
        document_type_name=meta["document_type_name"],
        data=content,
        file_extension="pdf",
        mime_type="application/pdf",
    )
    sync = StudentDriveSyncClass(db)
    job = sync.enqueue(
        folder_id=int(folder_id),
        student_id=STUDENT_ID,
        document_id=ANAMNESIS_DOCUMENT_ID,
        file_path=f"system/students/{pdf_filename}",
        mime_type="application/pdf",
    )
    job.status = "completed"
    job.drive_file_id = drive_payload.get("file_id")
    job.drive_path = drive_payload.get("drive_path")
    job.last_error = None
    db.commit()

    data = AnamnesisClass(db).get(int(anamnesis_id))
    filled2 = {
        k: v
        for k, v in (data or {}).items()
        if v not in (None, "", [], {}) and k not in {"status", "message"}
    }
    print(f"drive={drive_payload.get('drive_path')}")
    print(f"drive_file_id={drive_payload.get('file_id')}")
    print(f"campos_con_valor={len(filled2)}")
    for k in sorted(filled2):
        print(f"  {k}={filled2[k]!r}"[:160])
    db.close()


if __name__ == "__main__":
    main()
