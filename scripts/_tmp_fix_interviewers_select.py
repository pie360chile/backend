"""Extrae nombre de entrevistadores del PDF, matchea professional_id (user id) y actualiza anamnesis."""
from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TUNNEL = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"
os.environ["DATABASE_URL"] = TUNNEL
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL

import fitz
import requests
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.classes.agents_usage_class import AgentsUsageClass
from app.backend.classes.anamnesis_class import AnamnesisClass
from app.backend.classes.professional_class import ProfessionalClass
from app.backend.utils.agents_llm_client import (
    DEFAULT_MODEL_CODE,
    llm_chat_completions_url,
    normalize_usage,
    resolve_llm_api_key,
)

PDF = ROOT / "scripts" / "output" / "ocr_dafnika" / "dafnika.pdf"
ANAMNESIS_ID = 98
SCHOOL_ID = 4


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _score(a: str, b: str) -> float:
    ta = set(_norm(a).split())
    tb = set(_norm(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / max(len(ta), len(tb))


def main() -> None:
    os.environ["DATABASE_URL"] = os.environ.get("IMPORT_DATABASE_URL") or TUNNEL
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    db = sessionmaker(bind=eng)()

    pros = ProfessionalClass(db).get_all(page=1, items_per_page=200, school_id=SCHOOL_ID)
    items = (pros or {}).get("data") or []
    print(f"professionals school={SCHOOL_ID} n={len(items)}", flush=True)
    for p in items:
        print(
            f"  {p['id']} | {(p.get('names') or '')} {(p.get('lastnames') or '')}".strip(),
            "|",
            p.get("rol_name"),
            flush=True,
        )

    doc = fitz.open(PDF)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.8, 2.8), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    w, h = img.size
    crops: list[bytes] = []
    for box in (
        (0, int(h * 0.35), w, int(h * 0.75)),
        (0, int(h * 0.45), w, int(h * 0.85)),
        (0, 0, w, h),
    ):
        c = img.crop(box)
        c.thumbnail((1800, 1600))
        buf = io.BytesIO()
        c.save(buf, format="JPEG", quality=90, optimize=True)
        crops.append(buf.getvalue())
    doc.close()

    prompt = """Lee SOLO la sección 3 IDENTIFICACIÓN DE EL O LOS ENTREVISTADORES.
Devuelve SOLO JSON. Incluye el nombre manuscrito completo.
{
  "interviewers":[{"name":string|null,"role":string|null,"interview_date":"YYYY-MM-DD"|null}]
}
No inventes. Si el nombre es dudoso, mejor lectura posible.
"""
    key = resolve_llm_api_key(db)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for jpeg in crops:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(),
                    "detail": "high",
                },
            }
        )
    resp = requests.post(
        llm_chat_completions_url(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": DEFAULT_MODEL_CODE,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.1,
            "max_tokens": 800,
            "stream": False,
            "thinking": {"type": "disabled"},
        },
        timeout=180,
    )
    print(f"status={resp.status_code}", flush=True)
    if resp.status_code >= 400:
        raise SystemExit(resp.text[:500])
    data = resp.json()
    msg = ((data.get("choices") or [{}])[0].get("message") or {})
    text = (msg.get("content") or "").strip()
    print(text[:1500], flush=True)
    usage = normalize_usage(data.get("usage") if isinstance(data.get("usage"), dict) else None)
    m = re.search(r"\{[\s\S]*\}", text)
    parsed = json.loads(m.group(0)) if m else {}

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
        input_text="anamnesis interviewers name student=1851",
        output_text=text[:3000],
        request_kind="anamnesis_ocr",
    )

    interviewers = []
    for inv in parsed.get("interviewers") or []:
        name = (inv.get("name") or "").strip()
        best = None
        best_s = 0.0
        for p in items:
            full = f"{p.get('names') or ''} {p.get('lastnames') or ''}".strip()
            s = _score(name, full)
            if _norm(name) and _norm(name) in _norm(full):
                s = max(s, 0.85)
            # apellido principal
            parts = [x for x in _norm(name).split() if len(x) > 2]
            for part in parts:
                if part in _norm(full):
                    s = max(s, 0.5)
            if s > best_s:
                best_s = s
                best = p
        print(
            f"match '{name}' -> "
            f"{best['id'] if best else None} "
            f"{(best.get('names')+' '+best.get('lastnames')).strip() if best else '-'} "
            f"score={best_s:.2f}",
            flush=True,
        )
        interviewers.append(
            {
                "sort_order": len(interviewers),
                "professional_id": int(best["id"]) if best and best_s >= 0.4 else None,
                "role": inv.get("role") or "Ed. diferencial",
                "interview_date": inv.get("interview_date") or "2026-03-16",
            }
        )

    if not interviewers:
        interviewers = [
            {
                "sort_order": 0,
                "professional_id": None,
                "role": "Ed. diferencial",
                "interview_date": "2026-03-16",
            }
        ]

    cur = AnamnesisClass(db).get(ANAMNESIS_ID) or {}
    upd = {"interviewers": interviewers}
    for k in ("informants", "household_members"):
        if cur.get(k) is not None:
            upd[k] = cur[k]
    print("UPD", interviewers, flush=True)
    print(AnamnesisClass(db).update(ANAMNESIS_ID, upd), flush=True)
    print("verify", AnamnesisClass(db).get(ANAMNESIS_ID).get("interviewers"), flush=True)
    db.close()


if __name__ == "__main__":
    main()
