"""Segunda pasada DeepSeek: solo salud 5.6 + familiares (páginas finales)."""
from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
from pathlib import Path

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
from app.backend.utils.agents_deepseek_pricing import DEEPSEEK_OFF_PEAK, estimate_token_cost_usd
from app.backend.utils.agents_llm_client import (
    DEFAULT_MODEL_CODE,
    llm_chat_completions_url,
    normalize_usage,
    resolve_llm_api_key,
)

PDF = ROOT / "scripts" / "output" / "ocr_dafnika" / "dafnika.pdf"
PROMPT = """Lee este formulario anamnesis Decreto 170 (secciones 5.6 Estado Actual de Salud y 6 Familiares si aparecen).
Devuelve SOLO JSON. 1=Si 2=No. null si no seguro. No inventes.
{
  "health_vaccines_up_to_date": 1,
  "health_epilepsy": 2,
  "health_heart_problems": null,
  "health_paraplegia": null,
  "health_hearing_loss": null,
  "health_vision_loss": null,
  "health_motor_disorder": null,
  "health_bronchorespiratory": null,
  "health_infectious_disease": null,
  "health_emotional_disorder": null,
  "health_behavioral_disorder": null,
  "health_problems_treatment": null,
  "health_diet": null,
  "health_weight": null,
  "health_sleep_pattern": null,
  "health_sleep_hours": null,
  "health_sleeps_alone": null,
  "health_mood_behavior": null,
  "health_current_observations": null,
  "family_health_history": null,
  "household_members": [],
  "sm_head_control": null,
  "sm_sits_alone": null,
  "sm_walks_without_support": null,
  "sm_first_words": null,
  "sm_first_phrases": null,
  "sm_dresses_alone": null
}
Usa los mismos nombres de claves. health_diet: Normal|Malo|Bueno|Otro.
health_weight: Normal|Bajo peso|Obesidad. health_sleep_pattern: Normal|Tranquilo|Inquieto.
health_sleeps_alone: Solo|Acompanado.
"""


def main() -> None:
    eng = create_engine(os.environ["DATABASE_URL"])
    db = sessionmaker(bind=eng)()
    key = resolve_llm_api_key(db)
    doc = fitz.open(PDF)
    images: list[bytes] = []
    mat = fitz.Matrix(2.5, 2.5)
    for i in [3, 4]:
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        w, h = img.size
        for y0, y1 in ((0, h // 2 + 80), (h // 2 - 80, h)):
            crop = img.crop((0, y0, w, y1))
            crop.thumbnail((1800, 1600))
            buf = io.BytesIO()
            crop.save(buf, format="JPEG", quality=88, optimize=True)
            images.append(buf.getvalue())
    doc.close()
    print(f"images={len(images)} sizes={[len(x) for x in images]}", flush=True)

    content: list[dict] = [{"type": "text", "text": PROMPT}]
    for jpeg in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(),
                    "detail": "high",
                },
            }
        )
    payload = {
        "model": DEFAULT_MODEL_CODE,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
        # sin chain-of-thought: si no, se come el max_tokens y content queda vacío
        "thinking": {"type": "disabled"},
    }
    resp = requests.post(
        llm_chat_completions_url(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    print(f"status={resp.status_code}", flush=True)
    data = resp.json()
    if resp.status_code >= 400:
        print(resp.text[:500], flush=True)
        raise SystemExit(1)
    msg = ((data.get("choices") or [{}])[0].get("message") or {})
    text = (msg.get("content") or "").strip()
    print(
        f"content_len={len(text)} reasoning_len={len(msg.get('reasoning_content') or '')}",
        flush=True,
    )
    if not text:
        text = (msg.get("reasoning_content") or "").strip()
    usage = normalize_usage(data.get("usage") if isinstance(data.get("usage"), dict) else None)
    print(f"usage={usage}", flush=True)
    parsed: dict = {}
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        raw_json = m.group(0)
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            # intentar objeto más interno / truncado
            for cand in re.findall(r"\{[^{}]*\}", text):
                try:
                    parsed = json.loads(cand)
                    if isinstance(parsed, dict) and len(parsed) > 3:
                        break
                except json.JSONDecodeError:
                    continue
    print(json.dumps(parsed, ensure_ascii=False, indent=2)[:3500], flush=True)

    AgentsUsageClass(db).record_chat(
        customer_id=2,
        school_id=None,
        user_id=None,
        agent_id="anamnesis_import_ocr",
        model=DEFAULT_MODEL_CODE,
        prompt_tokens=int((usage or {}).get("prompt_tokens") or 0),
        completion_tokens=int((usage or {}).get("completion_tokens") or 0),
        total_tokens=int((usage or {}).get("total_tokens") or 0),
        prompt_cache_hit_tokens=int((usage or {}).get("prompt_cache_hit_tokens") or 0),
        prompt_cache_miss_tokens=int((usage or {}).get("prompt_cache_miss_tokens") or 0),
        input_text="anamnesis vision health pages student=1851",
        output_text=text[:5000],
        request_kind="anamnesis_ocr",
    )
    cat = DEEPSEEK_OFF_PEAK["deepseek-flash"]
    cost = estimate_token_cost_usd(
        off_peak_input=cat["input"],
        off_peak_output=cat["output"],
        off_peak_cached=cat["cached_input"],
        prompt_tokens=int((usage or {}).get("prompt_tokens") or 0),
        completion_tokens=int((usage or {}).get("completion_tokens") or 0),
        cache_hit_tokens=int((usage or {}).get("prompt_cache_hit_tokens") or 0),
        cache_miss_tokens=int((usage or {}).get("prompt_cache_miss_tokens") or 0),
    )
    print(f"cost_usd_this_call={cost}", flush=True)

    cls = AnamnesisClass(db)
    cur = cls.get(98) or {}
    upd = {k: v for k, v in parsed.items() if v not in (None, "", [])}
    if isinstance(upd.get("household_members"), list):
        upd["household_members"] = [
            {**m, "sort_order": i}
            for i, m in enumerate(upd["household_members"])
            if isinstance(m, dict) and (m.get("name") or m.get("relationship"))
        ]
    for k in ("informants", "interviewers"):
        if cur.get(k) is not None:
            upd[k] = cur[k]
    if "household_members" not in upd and cur.get("household_members"):
        upd["household_members"] = cur["household_members"]
    print("update", list(upd.keys()), flush=True)
    print(cls.update(98, upd), flush=True)
    d = cls.get(98)
    yn = {1: "Si", 2: "No", None: "-"}
    for k in sorted(
        x
        for x in d
        if x.startswith("health_")
        or x in {"diagnosis_has", "interview_reason", "family_health_history"}
    ):
        v = d.get(k)
        print(f"{k}={yn.get(v, v) if isinstance(v, int) or v is None else repr(v)[:90]}", flush=True)
    print("household=", json.dumps(d.get("household_members"), ensure_ascii=False)[:500], flush=True)
    db.close()


if __name__ == "__main__":
    main()
