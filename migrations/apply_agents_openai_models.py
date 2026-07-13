"""Apply agents_openai_models table and seed 10 OpenAI models.

Run from backend/:
  python migrations/apply_agents_openai_models.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import SessionLocal, engine
from app.backend.classes.agents_openai_models_class import AgentsOpenAIModelsClass

CREATE_SQL = """
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


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        print("ok: agents_openai_models table")

    db = SessionLocal()
    try:
        AgentsOpenAIModelsClass(db).ensure_seeded()
        data = AgentsOpenAIModelsClass(db).list_models()
        print(f"ok: seeded {len(data['models'])} models; selected={data['selected_model_code']}")
    finally:
        db.close()

    tables = set(inspect(engine).get_table_names())
    print("has table:", "agents_openai_models" in tables)


if __name__ == "__main__":
    main()
