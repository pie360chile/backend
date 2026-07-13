"""Ensure agents_openai_models + agents_app_settings and seed DeepSeek-V3.2.

Run from backend/:
  python migrations/apply_agents_llm_models.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import SessionLocal, engine
from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass

CREATE_MODELS_SQL = """
CREATE TABLE IF NOT EXISTS agents_openai_models (
  id INT NOT NULL AUTO_INCREMENT,
  model_code VARCHAR(64) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  input_per_1m_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  output_per_1m_usd DECIMAL(12, 6) NOT NULL DEFAULT 0,
  cached_input_per_1m_usd DECIMAL(12, 6) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_selected TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agents_openai_models_model_code (model_code),
  INDEX ix_agents_openai_models_sort (sort_order),
  INDEX ix_agents_openai_models_selected (is_selected)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

CREATE_SETTINGS_SQL = """
CREATE TABLE IF NOT EXISTS agents_app_settings (
  id INT NOT NULL,
  default_agent_id VARCHAR(64) NULL,
  llm_api_key TEXT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

ALTER_SETTINGS_LLM_KEY_SQL = """
ALTER TABLE agents_app_settings
  ADD COLUMN llm_api_key TEXT NULL
"""


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_MODELS_SQL))
        print("ok: agents_openai_models table")
        conn.execute(text(CREATE_SETTINGS_SQL))
        print("ok: agents_app_settings table")
        cols = {
            c["name"]
            for c in inspect(engine).get_columns("agents_app_settings")
        }
        if "llm_api_key" not in cols:
            conn.execute(text(ALTER_SETTINGS_LLM_KEY_SQL))
            print("ok: added agents_app_settings.llm_api_key")
        else:
            print("ok: agents_app_settings.llm_api_key already exists")

    db = SessionLocal()
    try:
        svc = AgentsLlmModelsClass(db)
        svc.ensure_seeded()
        svc.force_select_default_model()
        data = svc.get_settings()
        print(
            f"ok: models={len(data['models'])}; "
            f"selected={data['selected_model_code']}; "
            f"default_agent={data['default_agent_id']}"
        )
    finally:
        db.close()

    tables = set(inspect(engine).get_table_names())
    print("has models:", "agents_openai_models" in tables)
    print("has settings:", "agents_app_settings" in tables)


if __name__ == "__main__":
    main()
