"""Pasada DeepSeek: sección 7 Antecedentes escolares (última página)."""
from __future__ import annotations

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
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = (
    os.environ.get("IMPORT_DATABASE_URL")
    or "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
)

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

PDF = ROOT / "scripts" / "output" / "ocr_dafnika" / "dafnika.pdf"
OUT = ROOT / "scripts" / "output" / "ocr_dafnika" / "deepseek_school.json"
ANAMNESIS_ID = 98
CUSTOMER_ID = 2
STUDENT_ID = 1851

PROMPT = """Lee SOLO la sección 7 del formulario: ANTECEDENTES ESCOLARES Y APOYO DE LA FAMILIA.
Devuelve SOLO JSON válido (sin markdown). 1=Sí, 2=No. null si no se lee con certeza. No inventes.

{
  "school_entry_age": string|null,
  "attended_kindergarten": 1|2|null,
  "schools_count": string|null,
  "teaching_modality": "regular"|"especial"|"tecnica"|null,
  "changes_reason": string|null,
  "repeated_grade": 1|2|null,
  "repeated_courses": string|null,
  "repeated_reason": string|null,
  "current_level": string|null,
  "learning_difficulty": 1|2|null,
  "participation_difficulty": 1|2|null,
  "disruptive_behavior": 1|2|null,
  "attends_regularly": 1|2|null,
  "attends_gladly": 1|2|null,
  "family_support_homework": 1|2|null,
  "friends": 1|2|null,
  "family_attitude": string|null,
  "performance_assessment": "satisfactorio"|"insatisfactorio"|null,
  "performance_reasons": string|null,
  "response_difficulties": ["Apoyo"|"Castigo"|"Indiferencia"|"Compasión"|"Tensión"|"Otra"]|null,
  "response_difficulties_other": string|null,
  "response_success": ["Apoyo"|"Indiferencia"|"Otra"]|null,
  "response_success_other": string|null,
  "rewards": ["Expresiones afectivas"|"Alimentos preferidos"|"Ver TV"|"Juguetes"|"Tiempo libre"|"Otros"]|null,
  "rewards_other": string|null,
  "supporters": ["Madre"|"Padre"|"Hermanos/as"|"Otros familiares"|"Otros profesionales"]|null,
  "supporters_other_professionals": string|null,
  "expectations": "alta"|"mediana"|"baja"|null,
  "environment": "ambos"|"fisico"|"emocional"|null,
  "final_comments": string|null
}

Lee casillas marcadas (X/✓) y manuscrito. Si el nivel aparece como "2°" o similar, ponlo en current_level.
"""


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


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    key = resolve_llm_api_key(db)
    if not key:
        raise SystemExit("Sin DEEPSEEK_API_KEY")
    model = DEFAULT_MODEL_CODE

    doc = fitz.open(PDF)
    images: list[bytes] = []
    mat = fitz.Matrix(2.6, 2.6)
    # última página = sección 7
    page = doc[len(doc) - 1]
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    w, h = img.size
    # full + tercios verticales (formulario denso)
    full = img.copy()
    full.thumbnail((1800, 2400))
    buf = io.BytesIO()
    full.save(buf, format="JPEG", quality=90, optimize=True)
    images.append(buf.getvalue())
    for y0, y1 in ((0, h // 2 + 60), (h // 3, 2 * h // 3 + 60), (h // 2 - 60, h)):
        crop = img.crop((0, y0, w, y1))
        crop.thumbnail((1800, 1600))
        b2 = io.BytesIO()
        crop.save(b2, format="JPEG", quality=90, optimize=True)
        images.append(b2.getvalue())
    doc.close()
    print(f"model={model} images={len(images)} sizes={[len(x) for x in images]}", flush=True)

    content: list[dict] = [{"type": "text", "text": PROMPT}]
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
        "max_tokens": 3000,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    resp = requests.post(
        llm_chat_completions_url(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise SystemExit(f"DeepSeek HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    usage = normalize_usage(data.get("usage") if isinstance(data.get("usage"), dict) else None)
    parsed = _extract_json(text)
    print("usage", usage, flush=True)
    print(json.dumps(parsed, ensure_ascii=False, indent=2), flush=True)

    AgentsUsageClass(db).record_chat(
        customer_id=CUSTOMER_ID,
        school_id=None,
        user_id=None,
        agent_id="anamnesis_import_ocr",
        model=model,
        prompt_tokens=int((usage or {}).get("prompt_tokens") or 0),
        completion_tokens=int((usage or {}).get("completion_tokens") or 0),
        total_tokens=int((usage or {}).get("total_tokens") or 0),
        prompt_cache_hit_tokens=int((usage or {}).get("prompt_cache_hit_tokens") or 0),
        prompt_cache_miss_tokens=int((usage or {}).get("prompt_cache_miss_tokens") or 0),
        input_text=f"anamnesis vision school page student={STUDENT_ID}",
        output_text=text[:5000],
        request_kind="anamnesis_ocr",
    )

    OUT.write_text(
        json.dumps({"parsed": parsed, "usage": usage, "raw": text[:8000]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    cls = AnamnesisClass(db)
    current = cls.get(ANAMNESIS_ID) or {}
    upd: dict[str, Any] = {}
    for k, v in parsed.items():
        if v is None or v == "" or v == []:
            continue
        upd[k] = v
    # no pisar comentario genérico OCR si DeepSeek no trajo uno útil
    if upd.get("final_comments") and "sin antec" in str(upd["final_comments"]).lower().replace(" ", ""):
        upd["final_comments"] = "Sin antecedentes."
    for k in ("informants", "interviewers", "household_members"):
        if current.get(k) is not None and k not in upd:
            upd[k] = current[k]
    print(f"updating anamnesis {ANAMNESIS_ID} fields={list(upd.keys())}", flush=True)
    print(cls.update(ANAMNESIS_ID, upd), flush=True)
    db.close()
    print(f"saved {OUT}", flush=True)


if __name__ == "__main__":
    main()
