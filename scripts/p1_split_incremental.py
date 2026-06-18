"""
P1 incremental: divide models.py y schemas.py en paquetes por dominio.

- erp_legacy / pedagogical: sin referencias cruzadas a PIE.
- pie_core: resto (UserModel, Student, documentos, etc.).
- Shim: from app.backend.db.models import X sigue funcionando vía __init__.py.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"

MODELS_HEADER = """from app.backend.db.database import Base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, Time, ForeignKey, Float, Boolean, Text, Numeric, Enum, UniqueConstraint, select
from sqlalchemy.orm import column_property
from datetime import datetime

"""

SCHEMAS_HEADER = """from pydantic import BaseModel, Field, EmailStr, validator, field_validator, ConfigDict, AliasChoices
from typing import Union, List, Dict, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
import json

from app.backend.schemas.helpers import _empty_str_to_none  # noqa: F401

"""

ERP_LEGACY_MODELS = frozenset(
    {
        "AccountTypeModel",
        "SettingModel",
        "ShoppingModel",
        "ShoppingProductModel",
        "SupplierModel",
        "UnitMeasureModel",
        "SaleModel",
        "SaleProductModel",
        "LocationModel",
        "CategoryModel",
        "LiterFeatureModel",
        "PreInventoryStockModel",
        "UnitFeatureModel",
        "ProductModel",
        "CustomerProductDiscountModel",
        "InventoryModel",
        "LotModel",
        "LotItemModel",
        "InventoryLotItemModel",
        "MovementTypeModel",
        "InventoryMovementModel",
        "InventoryAuditModel",
        "SupplierCategoryModel",
        "KardexValuesModel",
    }
)


def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    if path.exists() and not bak.exists():
        shutil.copy2(path, bak)


def _split_classes(body: str) -> dict[str, str]:
    pattern = re.compile(r"^class (\w+)", re.M)
    matches = list(pattern.finditer(body))
    chunks: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        name = m.group(1)
        chunks[name] = body[start:end].rstrip() + "\n\n"
    return chunks


def _write_module(path: Path, header: str, parts: list[str]) -> None:
    path.write_text(header + "".join(parts), encoding="utf-8")


def split_models() -> None:
    src = BACKEND / "db" / "models.py"
    pkg = BACKEND / "db" / "models"
    _backup(src)
    text = src.read_text(encoding="utf-8")
    first_class = re.search(r"^class \w+", text, re.M)
    if not first_class:
        raise RuntimeError("No classes in models.py")
    body = text[first_class.start() :]
    classes = _split_classes(body)

    erp_parts: list[str] = []
    ped_parts: list[str] = []
    core_parts: list[str] = []

    for name, chunk in classes.items():
        if name in ERP_LEGACY_MODELS:
            erp_parts.append(chunk)
        elif name.startswith("PedagogicalEvaluationClassroom"):
            ped_parts.append(chunk)
        else:
            core_parts.append(chunk)

    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    _write_module(pkg / "erp_legacy.py", MODELS_HEADER, erp_parts)
    _write_module(pkg / "pie_core.py", MODELS_HEADER, core_parts)
    _write_module(pkg / "pedagogical.py", MODELS_HEADER, ped_parts)

    init = '''"""Modelos SQLAlchemy por dominio — import compatible con el monolito anterior."""

from app.backend.db.models.erp_legacy import *  # noqa: F401,F403
from app.backend.db.models.pie_core import *  # noqa: F401,F403
from app.backend.db.models.pedagogical import *  # noqa: F401,F403
'''
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    src.unlink()
    print(
        f"models: erp_legacy={len(erp_parts)}, pie_core={len(core_parts)}, pedagogical={len(ped_parts)}"
    )


def split_schemas() -> None:
    src = BACKEND / "schemas.py"
    pkg = BACKEND / "schemas"
    _backup(src)
    text = src.read_text(encoding="utf-8")
    first_class = re.search(r"^class \w+", text, re.M)
    if not first_class:
        raise RuntimeError("No classes in schemas.py")
    preamble = text[: first_class.start()]
    body = text[first_class.start() :]
    classes = _split_classes(body)

    ped_parts: list[str] = []
    core_parts: list[str] = []

    for name, chunk in classes.items():
        if "PedagogicalEvaluationClassroom" in name:
            ped_parts.append(chunk)
        else:
            core_parts.append(chunk)

    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    (pkg / "helpers.py").write_text(preamble, encoding="utf-8")
    _write_module(pkg / "pedagogical.py", SCHEMAS_HEADER, ped_parts)
    _write_module(pkg / "pie_core.py", SCHEMAS_HEADER, core_parts)

    init = '''"""Schemas Pydantic por dominio — import compatible con schemas.py monolítico."""

from app.backend.schemas.helpers import *  # noqa: F401,F403
from app.backend.schemas.pie_core import *  # noqa: F401,F403
from app.backend.schemas.pedagogical import *  # noqa: F401,F403
'''
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    src.unlink()
    print(f"schemas: pie_core={len(core_parts)}, pedagogical={len(ped_parts)}")


if __name__ == "__main__":
    split_models()
    split_schemas()
    print("P1 split done. Run: python -c \"from main import app; print(len(app.routes))\"")
