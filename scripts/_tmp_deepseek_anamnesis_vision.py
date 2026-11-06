"""Piloto: leer anamnesis escaneada con DeepSeek-flash (visión) + registrar uso.

Usa DEEPSEEK_API_KEY / agents_llm_client como el chat de Agentes.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.utils.agents_llm_client import (
    DEFAULT_MODEL_CODE,
    llm_chat_completions_url,
    normalize_usage,
    resolve_llm_api_key,
)

os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

PDF = ROOT / "scripts" / "output" / "ocr_dafnika" / "dafnika.pdf"
OUT = ROOT / "scripts" / "output" / "ocr_dafnika" / "deepseek_vision.json"
CUSTOMER_ID = 2  # San Felipe / Drive customer
STUDENT_ID = 1851
ANAMNESIS_ID = 98

PROMPT = """Eres un extractor de formularios clínicos chilenos (Decreto 170 / Anamnesis PIE).
Lee la(s) imagen(es) del formulario escaneado (puede haber manuscrito).

Devuelve SOLO un JSON válido (sin markdown) con estas claves si las ves.
Usa null si no se lee con certeza. Sí/No → 1=Sí, 2=No.
No inventes. Si la casilla no está marcada claramente, null.

{
  "student_full_name": string|null,
  "interview_reason": string|null,
  "diagnosis_has": 1|2|null,
  "diagnosis_detail": string|null,
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
  "health_vaccines_up_to_date": 1|2|null,
  "health_epilepsy": 1|2|null,
  "health_heart_problems": 1|2|null,
  "health_paraplegia": 1|2|null,
  "health_hearing_loss": 1|2|null,
  "health_vision_loss": 1|2|null,
  "health_motor_disorder": 1|2|null,
  "health_bronchorespiratory": 1|2|null,
  "health_infectious_disease": 1|2|null,
  "health_emotional_disorder": 1|2|null,
  "health_behavioral_disorder": 1|2|null,
  "health_other_specify": string|null,
  "health_problems_treatment": string|null,
  "health_diet": "Normal"|"Malo"|"Bueno"|"Otro"|null,
  "health_weight": "Normal"|"Bajo peso"|"Obesidad"|null,
  "health_sleep_pattern": "Normal"|"Tranquilo"|"Inquieto"|null,
  "health_sleep_hours": string|null,
  "health_sleeps_alone": "Solo"|"Acompañado"|null,
  "health_mood_behavior": string|null,
  "health_current_observations": string|null,
  "family_health_history": string|null,
  "household_members": [{"name":string,"relationship":string,"age":string|null,"schooling":string|null,"occupation":string|null}],
  "native_language": string|null,
  "native_language_domain": ["understand"|"speak"|"read"|"write"],
  "language_used": string|null,
  "language_used_domain": ["understand"|"speak"|"read"|"write"],
  "notes": string|null
}
"""


def _page_crops_jpeg(pdf_path: Path, *, zoom: float = 2.2, quality: int = 85) -> list[tuple[int, str, bytes]]:
    """(page_idx, part, jpeg_bytes) part in {full,top,bottom} — crops para compensar downscale DeepSeek."""
    import fitz
    from PIL import Image
    import io

    out: list[tuple[int, str, bytes]] = []
    doc = fitz.open(pdf_path)
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # full resized max side 1600 keeps more detail before API downscale
            img.thumbnail((1600, 2200))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            out.append((i, "full", buf.getvalue()))
            # top / bottom halves at higher effective res
            w, h = img.size
            for part, box in (("top", (0, 0, w, h // 2 + 40)), ("bottom", (0, h // 2 - 40, w, h))):
                crop = img.crop(box)
                crop.thumbnail((1600, 1400))
                b2 = io.BytesIO()
                crop.save(b2, format="JPEG", quality=quality, optimize=True)
                out.append((i, part, b2.getvalue()))
    finally:
        doc.close()
    return out


def _b64_data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


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


def _call_vision(api_key: str, images: list[bytes], *, model: str) -> tuple[str, dict[str, int] | None]:
    content: list[dict[str, Any]] = [{"type": "text", "text": PROMPT}]
    for jpeg in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": _b64_data_url(jpeg), "detail": "high"},
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
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    text = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        or ""
    )
    usage = normalize_usage(data.get("usage") if isinstance(data.get("usage"), dict) else None)
    return text, usage


def _merge_dicts(base: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (new or {}).items():
        if v is None or v == "" or v == []:
            continue
        if k == "household_members" and isinstance(v, list):
            if not out.get(k):
                out[k] = v
            continue
        if k.endswith("_domain") and isinstance(v, list):
            out[k] = v
            continue
        if out.get(k) in (None, "", []):
            out[k] = v
    return out


def main() -> None:
    if not PDF.exists():
        raise SystemExit(f"Falta PDF {PDF}")

    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    api_key = resolve_llm_api_key(db)
    if not api_key:
        raise SystemExit("Sin DEEPSEEK_API_KEY")
    model = DEFAULT_MODEL_CODE
    print(f"model={model} pdf={PDF}", flush=True)

    crops = _page_crops_jpeg(PDF)
    # priorizar páginas con salud/familia: últimas 2 páginas full+top+bottom
    by_page: dict[int, list[tuple[str, bytes]]] = {}
    for i, part, jpeg in crops:
        by_page.setdefault(i, []).append((part, jpeg))
    pages = sorted(by_page.keys())
    print(f"pages={pages}", flush=True)

    merged: dict[str, Any] = {}
    total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 0,
    }
    raw_replies: list[dict[str, Any]] = []

    # Enviar por página: full + top + bottom (mejor para formulario denso)
    for page in pages:
        parts = by_page[page]
        # orden: full, top, bottom
        order = {"full": 0, "top": 1, "bottom": 2}
        parts = sorted(parts, key=lambda x: order.get(x[0], 9))
        images = [b for _, b in parts]
        print(f"DeepSeek page {page+1}/{len(pages)} images={len(images)}...", flush=True)
        text, usage = _call_vision(api_key, images, model=model)
        parsed = _extract_json(text)
        print(f"  keys={list(parsed.keys())[:12]} usage={usage}", flush=True)
        raw_replies.append({"page": page + 1, "raw": text[:4000], "parsed": parsed, "usage": usage})
        merged = _merge_dicts(merged, parsed)
        if usage:
            for k in total_usage:
                total_usage[k] += int(usage.get(k) or 0)

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
            input_text=f"anamnesis vision student={STUDENT_ID} page={page+1}",
            output_text=text[:5000],
            request_kind="anamnesis_ocr",
        )

    OUT.write_text(
        json.dumps(
            {"merged": merged, "total_usage": total_usage, "pages": raw_replies},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("===== MERGED =====", flush=True)
    print(json.dumps(merged, ensure_ascii=False, indent=2)[:4000], flush=True)
    print("===== USAGE =====", flush=True)
    print(total_usage, flush=True)
    print(f"saved {OUT}", flush=True)

    # Aplicar al formulario (solo claves no nulas)
    from app.backend.classes.anamnesis_class import AnamnesisClass

    cls = AnamnesisClass(db)
    current = cls.get(ANAMNESIS_ID) or {}
    upd: dict[str, Any] = {}
    for k, v in merged.items():
        if k in {"notes"} or v is None or v == "":
            continue
        if k == "household_members" and isinstance(v, list) and v:
            upd[k] = [
                {
                    "sort_order": i,
                    "name": m.get("name"),
                    "relationship": m.get("relationship"),
                    "age": m.get("age"),
                    "schooling": m.get("schooling"),
                    "occupation": m.get("occupation"),
                }
                for i, m in enumerate(v)
                if isinstance(m, dict) and (m.get("name") or m.get("relationship"))
            ]
            continue
        upd[k] = v
    for k in ("informants", "interviewers"):
        if current.get(k) is not None and k not in upd:
            upd[k] = current[k]
    if "household_members" not in upd and current.get("household_members"):
        upd["household_members"] = current["household_members"]

    print(f"updating anamnesis {ANAMNESIS_ID} fields={list(upd.keys())}", flush=True)
    res = cls.update(ANAMNESIS_ID, upd)
    print(res, flush=True)
    db.close()


if __name__ == "__main__":
    main()
