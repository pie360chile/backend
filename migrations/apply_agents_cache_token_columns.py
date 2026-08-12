"""Add DeepSeek cache hit/miss columns to agents_token_usage.

Run from backend/:
  python migrations/apply_agents_cache_token_columns.py
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.backend.db.database import engine


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    if column in cols:
        print(f"ok: {table}.{column} already exists")
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    print(f"ok: added {table}.{column}")


def main() -> None:
    tables = set(inspect(engine).get_table_names())
    if "agents_token_usage" not in tables:
        raise SystemExit("agents_token_usage table missing; run apply_agents_token_usage_details.py first")

    with engine.begin() as conn:
        _add_column_if_missing(
            conn,
            "agents_token_usage",
            "prompt_cache_hit_tokens",
            "prompt_cache_hit_tokens INT NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            conn,
            "agents_token_usage",
            "prompt_cache_miss_tokens",
            "prompt_cache_miss_tokens INT NOT NULL DEFAULT 0",
        )

    cols = {c["name"] for c in inspect(engine).get_columns("agents_token_usage")}
    print(
        "has columns:",
        "prompt_cache_hit_tokens" in cols,
        "prompt_cache_miss_tokens" in cols,
    )


if __name__ == "__main__":
    main()
