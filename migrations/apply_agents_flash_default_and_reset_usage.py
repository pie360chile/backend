"""Deja DeepSeek-V4.1-Flash (deepseek-flash), borra modelos viejos y limpia uso.

Run from backend/:
  python migrations/apply_agents_flash_default_and_reset_usage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import text

from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass
from app.backend.db.database import SessionLocal, engine


def main() -> None:
    db = SessionLocal()
    try:
        svc = AgentsLlmModelsClass(db)
        svc.ensure_seeded()
        svc.force_select_default_model()

        # Soft-delete / desactivar Pro y cualquier otro no-Flash
        now_sql = "UTC_TIMESTAMP()"
        with engine.begin() as conn:
            deleted_models = conn.execute(
                text(
                    """
                    DELETE FROM agents_openai_models
                    WHERE model_code <> 'deepseek-flash'
                    """
                )
            )
            print(f"ok: deleted old models rows={deleted_models.rowcount}")
            conn.execute(
                text(
                    f"""
                    UPDATE agents_openai_models
                    SET is_active = 1, is_selected = 1,
                        display_name = 'DeepSeek-V4.1-Flash',
                        input_per_1m_usd = 0.150000,
                        output_per_1m_usd = 0.600000,
                        cached_input_per_1m_usd = 0.003000,
                        updated_at = {now_sql}
                    WHERE model_code = 'deepseek-flash'
                    """
                )
            )

            # Borrar historial de informe / estadísticas para partir de 0
            for table in (
                "agents_token_usage",
                "agents_openai_cost_syncs",
                "agents_budget_alerts",
                "agents_budget_reservations",
                "agents_rate_limit_hits",
            ):
                try:
                    r = conn.execute(text(f"DELETE FROM {table}"))
                    print(f"ok: cleared {table} rows={r.rowcount}")
                except Exception as exc:
                    print(f"skip: {table}: {exc}")

        data = svc.get_settings()
        print(
            f"ok: selected={data.get('selected_model_code')} "
            f"models={[m.get('model_code') for m in (data.get('models') or [])]}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
