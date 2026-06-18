# Migraciones Alembic

Ver `alembic.ini` y `docs/MODELS_SCHEMAS_SPLIT.md`.

## BD existente

La base de datos ya está poblada vía scripts SQL en `sql/` y `migrations/`.
Para adoptar Alembic sin re-ejecutar DDL:

```bash
cd backend
pip install -r requirements-alembic.txt
alembic stamp head
```

## Nuevas migraciones

```bash
alembic revision -m "add_column_x" --autogenerate
alembic upgrade head
```

`env.py` lee `DATABASE_URL` desde `app.backend.core.config.settings`.
