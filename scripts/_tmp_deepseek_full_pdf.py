"""DeepSeek visión: lee TODAS las páginas del PDF anamnesis y extrae TODOS los campos.

Uso:
  python scripts/_tmp_deepseek_full_pdf.py
  python scripts/_tmp_deepseek_full_pdf.py --pdf path.pdf --anamnesis-id 98 --student-id 1851
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass
# Forzar túnel DESPUÉS de dotenv (el .env apunta a host remoto)
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

import fitz
import requests
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.classes.anamnesis_class import AnamnesisClass
from app.backend.utils.agents_llm_client import (
    DEFAULT_MODEL_CODE,
    llm_chat_completions_url,
    normalize_usage,
    resolve_llm_api_key,
)

OUT_DIR = ROOT / "scripts" / "output" / "ocr_dafnika"

# Prompts por página: cada uno cubre las secciones que suelen estar en esa hoja del Decreto 170.
# DeepSeek ve la imagen completa; el schema acota qué devolver para no truncar JSON.
PAGE_PROMPTS: dict[int, str] = {
    0: """Eres extractor de anamnesis Decreto 170 (Chile). Lee TODA la imagen (página 1: identificación, informantes, entrevistadores, motivo).
Devuelve SOLO JSON. 1=Sí 2=No. null si no seguro. No inventes. No copies basura OCR.
{
  "student_full_name": string|null,
  "born_date": "YYYY-MM-DD"|null,
  "age": string|null,
  "address": string|null,
  "phone": string|null,
  "native_language": string|null,
  "native_language_domain": ["understand"|"speak"|"read"|"write"],
  "language_used": string|null,
  "language_used_domain": ["understand"|"speak"|"read"|"write"],
  "current_schooling": string|null,
  "school_name": string|null,
  "informants": [{"name":string,"relationship":string,"presence":string|null,"interview_date":"YYYY-MM-DD"|null}],
  "interviewers": [{"name":string|null,"role":string|null,"interview_date":"YYYY-MM-DD"|null}],
  "interview_reason": string|null,
  "diagnosis_has": 1|2|null,
  "diagnosis_detail": string|null,
  "specialists": [{"name":"Pediatra"|"Kinesiología"|"Genética"|"Fonoaudiología"|"Neurología"|"Psicología"|"Psiquiatría"|"Psicopedagogía"|"Terapia ocupacional"|"Otro","status":string|null}]
}
""",
    1: """Eres extractor de anamnesis Decreto 170. Lee TODA la imagen (página 2: 5.1 primer año + 5.2 sensorio-motriz).
Devuelve SOLO JSON. 1=Sí 2=No. null si no seguro. No inventes.
Edades/meses: solo si el manuscrito es legible (ej "3 meses", "1 año"). Si ilegible → null.
{
  "first_year_notes": string|null,
  "birth_type": "normal"|"cesarea"|"inducido"|"forceps"|null,
  "birth_reason": string|null,
  "birth_medical_assistance": 1|2|null,
  "birth_weight": string|null,
  "birth_height": string|null,
  "first_year_conditions": {
    "desnutricion":1|2|null,"obesidad":1|2|null,"fiebre_alta":1|2|null,"asma":1|2|null,
    "traumatismos":1|2|null,"intoxicacion":1|2|null,"enfermedad_respiratoria":1|2|null,
    "hospitalizaciones":1|2|null,"encefalitis":1|2|null,"meningitis":1|2|null,
    "convulsiones":1|2|null,"otro":1|2|null
  },
  "first_year_conditions_other_specify": string|null,
  "first_year_periodic_health_checkups": 1|2|null,
  "first_year_vaccines": 1|2|null,
  "first_year_observations": string|null,
  "sm_head_control": string|null,
  "sm_sits_alone": string|null,
  "sm_walks_without_support": string|null,
  "sm_first_words": string|null,
  "sm_first_phrases": string|null,
  "sm_dresses_alone": string|null,
  "sm_bladder_day": string|null,
  "sm_bladder_night": string|null,
  "sm_bowel_day": string|null,
  "sm_bowel_night": string|null,
  "sm_observations_1": string|null,
  "sm_motor_activity": "Normal"|"Activo"|"Hiperactivo"|"Hipoactivo"|null,
  "sm_muscle_tone": "Normal"|"Hipertónico"|"Hipotónico"|null,
  "sm_walking_stability": 1|2|null,
  "sm_frequent_falls": 1|2|null,
  "sm_lateral_dominance": "Der"|"Izq"|null,
  "sm_fine_grab": 1|2|null,
  "sm_fine_grip": 1|2|null,
  "sm_fine_pinch": 1|2|null,
  "sm_fine_draw": 1|2|null,
  "sm_fine_write": 1|2|null,
  "sm_fine_thread": 1|2|null,
  "sm_cog_reacts_familiar": 1|2|null,
  "sm_cog_demands_company": 1|2|null,
  "sm_cog_smiles_babbles": 1|2|null,
  "sm_cog_manipulates_explores": 1|2|null,
  "sm_cog_understands_prohibitions": 1|2|null,
  "sm_cog_poor_eye_hand": 1|2|null,
  "sm_observations_2": string|null
}
""",
    2: """Eres extractor de anamnesis Decreto 170. Lee TODA la imagen (página 3: 5.3 visión-audición, 5.4 lenguaje, 5.5 social).
Devuelve SOLO JSON. 1=Sí 2=No. null si no seguro. No inventes.
{
  "vision_interested_stimuli":1|2|null,"vision_irritated_eyes":1|2|null,"vision_headaches":1|2|null,
  "vision_squints":1|2|null,"vision_follows_movement":1|2|null,"vision_abnormal_movements":1|2|null,
  "vision_erroneous_behaviors":1|2|null,"vision_diagnosis":1|2|null,
  "hearing_interested_stimuli":1|2|null,"hearing_recognizes_voices":1|2|null,"hearing_turns_head":1|2|null,
  "hearing_ears_to_tv":1|2|null,"hearing_covers_ears":1|2|null,"hearing_earaches":1|2|null,
  "hearing_pronunciation_adequate":1|2|null,"hearing_diagnosis":1|2|null,
  "vision_hearing_observations": string|null,
  "language_communication_method": "Oral"|"Gestual"|"Mixto"|"Otro"|null,
  "language_communication_other": string|null,
  "language_exp_babbles":1|2|null,"language_exp_vocalizes_gestures":1|2|null,
  "language_exp_emits_words":1|2|null,"language_exp_emits_phrases":1|2|null,
  "language_exp_relates_experiences":1|2|null,"language_exp_clear_pronunciation":1|2|null,
  "language_comp_identifies_objects":1|2|null,"language_comp_identifies_people":1|2|null,
  "language_comp_understands_abstract":1|2|null,"language_comp_responds_coherently":1|2|null,
  "language_comp_follows_simple_instructions":1|2|null,"language_comp_follows_complex_instructions":1|2|null,
  "language_comp_follows_group_instructions":1|2|null,"language_comp_understands_stories":1|2|null,
  "language_oral_loss": string|null,
  "language_observations": string|null,
  "social_relates_spontaneously":1|2|null,"social_explains_behaviors":1|2|null,
  "social_participates_groups":1|2|null,"social_prefers_individual":1|2|null,
  "social_echolalic_language":1|2|null,"social_difficulty_adapting":1|2|null,
  "social_relates_collaboratively":1|2|null,"social_respects_social_norms":1|2|null,
  "social_respects_school_norms":1|2|null,"social_shows_humor":1|2|null,
  "social_stereotyped_movements":1|2|null,"social_frequent_tantrums":1|2|null,
  "social_reaction_lights":"Natural"|"Desmesurada"|null,
  "social_reaction_sounds":"Natural"|"Desmesurada"|null,
  "social_reaction_strange_people":"Natural"|"Desmesurada"|null,
  "social_observations": string|null
}
""",
    3: """Eres extractor de anamnesis Decreto 170. Lee TODA la imagen (página 4: 5.6 salud actual + 6 familiares).
Devuelve SOLO JSON. 1=Sí 2=No. null si no seguro. No inventes.
{
  "health_vaccines_up_to_date":1|2|null,"health_epilepsy":1|2|null,"health_heart_problems":1|2|null,
  "health_paraplegia":1|2|null,"health_hearing_loss":1|2|null,"health_vision_loss":1|2|null,
  "health_motor_disorder":1|2|null,"health_bronchorespiratory":1|2|null,
  "health_infectious_disease":1|2|null,"health_emotional_disorder":1|2|null,
  "health_behavioral_disorder":1|2|null,"health_other":1|2|null,
  "health_other_specify": string|null,
  "health_problems_treatment": string|null,
  "health_diet":"Normal"|"Malo"|"Bueno"|"Otro"|null,
  "health_diet_other": string|null,
  "health_weight":"Normal"|"Bajo peso"|"Obesidad"|null,
  "health_sleep_pattern":"Normal"|"Tranquilo"|"Inquieto"|null,
  "health_sleep_insomnia":0|1,"health_sleep_nightmares":0|1,"health_sleep_terrors":0|1,
  "health_sleep_sleepwalking":0|1,"health_sleep_good_mood":0|1,
  "health_sleep_hours": string|null,
  "health_sleeps_alone":"Solo"|"Acompañado"|null,
  "health_sleeps_specify": string|null,
  "health_mood_behavior": string|null,
  "health_mood_other": string|null,
  "health_current_observations": string|null,
  "household_members":[{"name":string,"relationship":string,"age":string|null,"schooling":string|null,"occupation":string|null}],
  "family_health_history": string|null,
  "family_health_observations": string|null
}
""",
    4: """Eres extractor de anamnesis Decreto 170. Lee TODA la imagen (página 5: sección 7 antecedentes escolares y apoyo familia).
Devuelve SOLO JSON. 1=Sí 2=No. null si no seguro. No inventes. No pongas 'satisfactorio' en family_attitude.
{
  "school_entry_age": string|null,
  "attended_kindergarten":1|2|null,
  "schools_count": string|null,
  "teaching_modality":"regular"|"especial"|"tecnica"|null,
  "changes_reason": string|null,
  "repeated_grade":1|2|null,
  "repeated_courses": string|null,
  "repeated_reason": string|null,
  "current_level": string|null,
  "learning_difficulty":1|2|null,
  "participation_difficulty":1|2|null,
  "disruptive_behavior":1|2|null,
  "attends_regularly":1|2|null,
  "attends_gladly":1|2|null,
  "family_support_homework":1|2|null,
  "friends":1|2|null,
  "family_attitude": string|null,
  "performance_assessment":"satisfactorio"|"insatisfactorio"|null,
  "performance_reasons": string|null,
  "response_difficulties":["Apoyo"|"Castigo"|"Indiferencia"|"Compasión"|"Tensión"|"Otra"]|null,
  "response_difficulties_other": string|null,
  "response_success":["Apoyo"|"Indiferencia"|"Otra"]|null,
  "response_success_other": string|null,
  "rewards":["Expresiones afectivas"|"Alimentos preferidos"|"Ver TV"|"Juguetes"|"Tiempo libre"|"Otros"]|null,
  "rewards_other": string|null,
  "supporters":["Madre"|"Padre"|"Hermanos/as"|"Otros familiares"|"Otros profesionales"]|null,
  "supporters_other_professionals": string|null,
  "expectations":"alta"|"mediana"|"baja"|null,
  "environment":"ambos"|"fisico"|"emocional"|null,
  "final_comments": string|null
}
""",
}

BIRTH_TYPE_MAP = {
    "normal": 1,
    "cesarea": 2,
    "cesárea": 2,
    "inducido": 3,
    "asistido": 3,
    "forceps": 4,
    "fórceps": 4,
}


def _page_images(pdf: Path, page_idx: int, *, zoom: float = 2.5) -> list[bytes]:
    """full + top + bottom de una página."""
    doc = fitz.open(pdf)
    try:
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        w, h = img.size
        out: list[bytes] = []
        full = img.copy()
        full.thumbnail((1800, 2400))
        b = io.BytesIO()
        full.save(b, format="JPEG", quality=88, optimize=True)
        out.append(b.getvalue())
        for box in ((0, 0, w, h // 2 + 80), (0, h // 2 - 80, w, h)):
            crop = img.crop(box)
            crop.thumbnail((1800, 1600))
            b2 = io.BytesIO()
            crop.save(b2, format="JPEG", quality=88, optimize=True)
            out.append(b2.getvalue())
        return out
    finally:
        doc.close()


def _extract_json(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except Exception:
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


def _call_vision(api_key: str, model: str, prompt: str, images: list[bytes]) -> tuple[str, dict | None]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for jpeg in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"),
                    "detail": "high",
                },
            }
        )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    resp = requests.post(
        llm_chat_completions_url(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:600]}")
    data = resp.json()
    msg = ((data.get("choices") or [{}])[0].get("message") or {})
    text = (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
    usage = normalize_usage(data.get("usage") if isinstance(data.get("usage"), dict) else None)
    return text, usage


def _merge(base: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (new or {}).items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, dict):
            cur = out.get(k) if isinstance(out.get(k), dict) else {}
            out[k] = _merge(cur, v)
            continue
        if k in ("household_members", "informants", "interviewers", "specialists") and isinstance(v, list):
            if not out.get(k):
                out[k] = v
            continue
        if k.endswith("_domain") and isinstance(v, list):
            out[k] = v
            continue
        if out.get(k) in (None, "", []):
            out[k] = v
    return out


def _sanitize(merged: dict[str, Any]) -> dict[str, Any]:
    out = dict(merged)
    # edades con "m" sola: "5 m"/"6m"/"10 m" → "N meses"
    age_keys = (
        "school_entry_age",
        "sm_head_control",
        "sm_sits_alone",
        "sm_walks_without_support",
        "sm_first_words",
        "sm_first_phrases",
        "sm_dresses_alone",
        "sm_bladder_day",
        "sm_bladder_night",
        "sm_bowel_day",
        "sm_bowel_night",
        "age",
    )
    for ak in age_keys:
        raw = str(out.get(ak) or "").strip().lower()
        if not raw:
            continue
        m_age = re.fullmatch(r"(\d+)\s*m(?:eses?)?", raw)
        if m_age:
            out[ak] = f"{m_age.group(1)} meses"
        elif ak == "school_entry_age" and (raw == "m" or (len(raw) <= 2 and not raw.isdigit())):
            out[ak] = None
    if out.get("family_attitude") in ("satisfactorio", "insatisfactorio"):
        out["family_attitude"] = None
    # birth_type → birth_type_id
    bt = out.pop("birth_type", None)
    if bt and out.get("birth_type_id") is None:
        key = str(bt).strip().lower().replace("á", "a").replace("é", "e")
        if key in BIRTH_TYPE_MAP:
            out["birth_type_id"] = BIRTH_TYPE_MAP[key]
    # tía cuidadora → otros profesionales
    other = out.get("supporters_other_professionals")
    if other:
        sup = list(out.get("supporters") or [])
        if "Otros familiares" in sup and "Otros profesionales" not in sup:
            sup = ["Otros profesionales" if x == "Otros familiares" else x for x in sup]
        if "Otros profesionales" not in sup:
            sup.append("Otros profesionales")
        out["supporters"] = sup
    # listas anidadas con sort_order
    for key in ("household_members", "informants"):
        if isinstance(out.get(key), list):
            out[key] = [
                {**m, "sort_order": i}
                for i, m in enumerate(out[key])
                if isinstance(m, dict) and any(m.get(x) for x in ("name", "relationship", "role"))
            ]
    if isinstance(out.get("interviewers"), list):
        out["interviewers"] = [
            {**m, "sort_order": i}
            for i, m in enumerate(out["interviewers"])
            if isinstance(m, dict) and (m.get("role") or m.get("professional_id"))
        ]
    # observaciones genéricas
    for k in list(out):
        if isinstance(out[k], str):
            t = out[k].strip()
            low = re.sub(r"\s+", "", t.lower())
            if "sinantec" in low or low in ("sinantecedentes", "sinantecedentes."):
                out[k] = "Sin antecedentes."
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=OUT_DIR / "dafnika.pdf")
    ap.add_argument("--anamnesis-id", type=int, default=98)
    ap.add_argument("--student-id", type=int, default=1851)
    ap.add_argument("--customer-id", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    if not args.pdf.exists():
        raise SystemExit(f"Falta PDF {args.pdf}")

    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    api_key = resolve_llm_api_key(db)
    if not api_key:
        raise SystemExit("Sin DEEPSEEK_API_KEY")
    model = DEFAULT_MODEL_CODE

    doc = fitz.open(args.pdf)
    n_pages = len(doc)
    doc.close()
    print(f"model={model} pdf={args.pdf} pages={n_pages}", flush=True)

    merged: dict[str, Any] = {}
    pages_raw: list[dict[str, Any]] = []
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
    }

    for i in range(n_pages):
        prompt = PAGE_PROMPTS.get(i, PAGE_PROMPTS[min(4, max(PAGE_PROMPTS))])
        images = _page_images(args.pdf, i)
        print(f"page {i+1}/{n_pages} images={len(images)} bytes={[len(x) for x in images]}...", flush=True)
        text, usage = _call_vision(api_key, model, prompt, images)
        parsed = _extract_json(text)
        print(f"  keys={len(parsed)} usage={usage}", flush=True)
        pages_raw.append({"page": i + 1, "parsed": parsed, "usage": usage, "raw": text[:6000]})
        merged = _merge(merged, parsed)
        if usage:
            for k in total_usage:
                total_usage[k] += int(usage.get(k) or 0)

        # registrar uso con sesión fresca (evita drop de túnel a mitad)
        os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
        try:
            AgentsUsageClass(db).record_chat(
                customer_id=args.customer_id,
                school_id=None,
                user_id=None,
                agent_id="anamnesis_import_ocr",
                model=model,
                prompt_tokens=int((usage or {}).get("prompt_tokens") or 0),
                completion_tokens=int((usage or {}).get("completion_tokens") or 0),
                total_tokens=int((usage or {}).get("total_tokens") or 0),
                prompt_cache_hit_tokens=int((usage or {}).get("prompt_cache_hit_tokens") or 0),
                prompt_cache_miss_tokens=int((usage or {}).get("prompt_cache_miss_tokens") or 0),
                input_text=f"anamnesis full-pdf student={args.student_id} page={i+1}/{n_pages}",
                output_text=text[:5000],
                request_kind="anamnesis_ocr",
            )
        except Exception as e:
            print(f"  WARN usage record failed: {e}", flush=True)
            db.rollback()
            db.close()
            eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
            db = sessionmaker(bind=eng)()

    merged = _sanitize(merged)
    out_path = OUT_DIR / "deepseek_full.json"
    out_path.write_text(
        json.dumps(
            {"merged": merged, "total_usage": total_usage, "pages": pages_raw},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("===== MERGED KEYS =====", flush=True)
    print(sorted(merged.keys()), flush=True)
    print("===== USAGE =====", total_usage, flush=True)
    print(f"saved {out_path}", flush=True)

    if args.dry_run:
        print(json.dumps(merged, ensure_ascii=False, indent=2)[:8000], flush=True)
        db.close()
        return

    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    db.close()
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()
    cls = AnamnesisClass(db)
    cur = cls.get(args.anamnesis_id) or {}
    upd = {k: v for k, v in merged.items() if v not in (None, "", [])}
    # no pisar gender/nationality/born desde PDF si ya vienen del alumno
    for keep in ("gender_id", "nationality_id", "born_date", "student_full_name", "age", "address", "phone"):
        if cur.get(keep) and keep in upd:
            # permitir overwrite de name/age si DeepSeek leyó bien; name sí actualizar
            if keep in ("gender_id", "nationality_id"):
                upd.pop(keep, None)
    for k in ("informants", "interviewers", "household_members"):
        if k not in upd and cur.get(k):
            upd[k] = cur[k]
    print(f"updating anamnesis {args.anamnesis_id} n_fields={len(upd)}", flush=True)
    print(cls.update(args.anamnesis_id, upd), flush=True)

    d = cls.get(args.anamnesis_id) or {}
    filled = sum(1 for k, v in d.items() if v not in (None, "", [], {}, 0) and not k.startswith("_"))
    print(f"get() non-empty-ish fields≈{filled}", flush=True)
    for k in (
        "interview_reason",
        "diagnosis_has",
        "sm_head_control",
        "health_vaccines_up_to_date",
        "family_health_history",
        "current_level",
        "learning_difficulty",
        "expectations",
        "final_comments",
    ):
        print(f"  {k}={d.get(k)!r}", flush=True)
    print("household=", json.dumps(d.get("household_members"), ensure_ascii=False)[:400], flush=True)
    db.close()


if __name__ == "__main__":
    main()
