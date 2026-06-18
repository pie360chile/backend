# División de `models.py` / `schemas.py`

## Estado actual (P1 incremental — aplicado)

Los monolitos se dividieron en paquetes con **shim de import compatible**:

```
app/backend/db/models/
  __init__.py      # re-exporta todo (from app.backend.db.models import X)
  erp_legacy.py    # 24 modelos inventario/ERP (sin refs PIE)
  pie_core.py      # 127 modelos PIE (User, Student, documentos, …)
  pedagogical.py   # 10 modelos evaluación pedagógica (docs 31–40)

app/backend/schemas/
  __init__.py
  helpers.py       # _empty_str_to_none y utilidades
  pie_core.py      # 244 schemas
  pedagogical.py   # 20 schemas (Store/Update × 10 grados)
```

Backups: `models.py.bak`, `schemas.py.bak`.

## Comando de split / re-split

```bash
cd backend
python scripts/p1_split_incremental.py
python -c "from main import app; print(len(app.routes))"  # debe ser 597
```

## Próximos pasos (opcional)

1. Subdividir `pie_core.py` por dominio (auth, students, documents, …) usando grafo de dependencias.
2. Resolver `ProfessionalModel` → `UserModel` (`column_property`) al mover auth antes de professional.
3. Agrupar schemas ICAP (`IcapCurricularAdaptationSubjectSchema` → `IcapLearningObjectiveSchema`) en el mismo módulo.

## Script legacy

`scripts/split_models_schemas.py` — heurística por regex de nombre; **no usar** (preferir `p1_split_incremental.py`).
