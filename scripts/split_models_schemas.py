"""Divide models.py y schemas.py en paquetes por dominio."""
import re
import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"

DOMAIN_RULES = [
    ("auth", re.compile(r"(User|Rol|Permission|Authentication|Login)", re.I)),
    ("students", re.compile(r"(Student|Guardian|FamilyMember|Nationalit|Gender)", re.I)),
    ("schools", re.compile(r"(School|Course|Teaching|Subject|Coordinator|Period)", re.I)),
    ("documents", re.compile(r"(Document|Fur|Anamnesis|Psychoped|Psychomotor|Authorization|Interconsult|Idtel|Conners|Diagnosis|Cesp|Informal|Meeting|Progress|BankDescription)", re.I)),
    ("pedagogical", re.compile(r"PedagogicalEvaluation", re.I)),
    ("professional", re.compile(r"Professional", re.I)),
    ("calendar", re.compile(r"(Calendar|Event|Holiday|News|Message|Faq|Package)", re.I)),
    ("erp_legacy", re.compile(r".*", re.I)),
]

HEADER_MODELS = """from app.backend.db.database import Base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, Time, ForeignKey, Float, Boolean, Text, Numeric, Enum, UniqueConstraint, select
from sqlalchemy.orm import column_property
from datetime import datetime

"""

HEADER_SCHEMAS = """from pydantic import BaseModel, Field, EmailStr, validator, field_validator, ConfigDict, AliasChoices
from typing import Union, List, Dict, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
import json

from app.backend.schemas.helpers import _empty_str_to_none  # noqa: F401

"""


def split_file(src: Path, dest_pkg: Path, is_model: bool) -> None:
    text = src.read_text(encoding="utf-8")
    header = HEADER_MODELS if is_model else HEADER_SCHEMAS

    first_class = re.search(r"^class \w+", text, re.M)
    if not first_class:
        raise RuntimeError(f"No classes in {src}")
    preamble = text[: first_class.start()]
    body = text[first_class.start() :]

    if dest_pkg.exists():
        shutil.rmtree(dest_pkg)
    dest_pkg.mkdir(parents=True)

    if not is_model:
        helpers_path = dest_pkg / "helpers.py"
        helpers_path.write_text(preamble, encoding="utf-8")

    pattern = re.compile(r"^class \w+", re.M)
    matches = list(pattern.finditer(body))
    chunks: dict[str, list[str]] = {d: [] for d, _ in DOMAIN_RULES}

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end].rstrip() + "\n\n"
        class_name = re.match(r"class (\w+)", chunk).group(1)
        domain = "erp_legacy"
        for d, rx in DOMAIN_RULES:
            if rx.search(class_name):
                domain = d
                break
        chunks[domain].append(chunk)

    init_lines = [
        '"""Paquete dividido por dominio — import compatible con models/schemas monolíticos."""',
        "",
    ]

    for domain, parts in chunks.items():
        if not parts:
            continue
        fname = f"{domain}.py"
        (dest_pkg / fname).write_text(header + "".join(parts), encoding="utf-8")
        pkg = "db.models" if is_model else "schemas"
        init_lines.append(f"from app.backend.{pkg}.{domain} import *  # noqa: F401,F403")

    (dest_pkg / "__init__.py").write_text("\n".join(init_lines) + "\n", encoding="utf-8")

    backup = src.with_suffix(src.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(src, backup)
    src.unlink()
    print(f"Split {src.name} -> {dest_pkg.name}/ ({sum(1 for p in chunks.values() if p)} domain files)")


if __name__ == "__main__":
    split_file(BACKEND / "db" / "models.py", BACKEND / "db" / "models", is_model=True)
    split_file(BACKEND / "schemas.py", BACKEND / "schemas", is_model=False)
