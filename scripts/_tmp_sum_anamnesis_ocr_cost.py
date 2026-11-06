import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
os.environ["DATABASE_URL"] = "mysql+pymysql://admin:ChileChile2026!!!@127.0.0.1:3307/pie360"

from sqlalchemy import create_engine, text

eng = create_engine(os.environ["DATABASE_URL"])
with eng.connect() as conn:
    rows = conn.execute(
        text(
            """
            SELECT id, prompt_tokens, completion_tokens, total_tokens,
                   estimated_cost_usd, created_at, request_kind
            FROM agents_token_usage
            WHERE request_kind = 'anamnesis_ocr'
               OR agent_id = 'anamnesis_import_ocr'
            ORDER BY id
            """
        )
    ).mappings().all()
    total = 0.0
    print("id  prompt  compl  total   cost_usd     created_at")
    for r in rows:
        c = float(r["estimated_cost_usd"] or 0)
        total += c
        print(
            f"{r['id']:>4} {r['prompt_tokens']:>7} {r['completion_tokens']:>6} "
            f"{r['total_tokens']:>7} {c:10.6f}  {r['created_at']}"
        )
    print(f"rows={len(rows)} TOTAL_USD={total:.6f}")
