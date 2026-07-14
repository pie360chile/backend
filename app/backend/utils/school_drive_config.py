"""Configuración Google Drive por colegio (tabla schools_settings)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import SchoolsSettingModel


@dataclass(frozen=True)
class DriveSchoolConfig:
    school_id: int
    root_folder_id: str
    service_account_info: dict[str, Any]
    source: str  # "db" | "agents_settings" | "env"

    @property
    def cache_key(self) -> str:
        return f"{self.school_id}:{self.source}:{hash(json.dumps(self.service_account_info, sort_keys=True))}"


def _parse_service_account_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("google_service_account_json está vacío.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("google_service_account_json no es JSON válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("google_service_account_json debe ser un objeto JSON.")
    if data.get("type") != "service_account":
        raise ValueError("Se espera JSON de cuenta de servicio Google (type=service_account).")
    if not data.get("private_key") or not data.get("client_email"):
        raise ValueError("El JSON debe incluir private_key y client_email.")
    return data


def _service_account_info_from_env_file() -> dict[str, Any] | None:
    cred_path = (settings.google_drive_credentials_path or "").strip()
    if not cred_path:
        return None
    path = Path(cred_path).expanduser().resolve()
    if not path.is_file():
        return None
    info = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(info, dict):
        return None
    return info


def _load_from_env(school_id: int) -> DriveSchoolConfig | None:
    root = (settings.google_drive_root_folder_id or "").strip()
    info = _service_account_info_from_env_file()
    if not root or not info:
        return None
    return DriveSchoolConfig(
        school_id=school_id,
        root_folder_id=root,
        service_account_info=info,
        source="env",
    )


def _load_from_agents_settings(db: Session, school_id: int) -> DriveSchoolConfig | None:
    from app.backend.db.models.agents_app_settings import AgentsAppSettingModel

    row = db.query(AgentsAppSettingModel).filter(AgentsAppSettingModel.id == 1).first()
    if not row:
        return None
    root = (row.google_drive_root_folder_id or "").strip()
    if not root:
        return None

    # Prefer JSON legado en BD; si no, archivo de credenciales en el servidor (.env).
    sa_json = (row.google_service_account_json or "").strip()
    if sa_json:
        info = _parse_service_account_json(sa_json)
        source = "agents_settings"
    else:
        info = _service_account_info_from_env_file()
        if not info:
            return None
        source = "agents_settings+env_file"

    return DriveSchoolConfig(
        school_id=school_id,
        root_folder_id=root,
        service_account_info=info,
        source=source,
    )


def load_agents_global_drive_config(db: Session) -> DriveSchoolConfig:
    """Drive exclusivo de Agentes (carpetas cliente/agente). No afecta colegios."""
    cfg = _load_from_agents_settings(db, school_id=0)
    if cfg:
        return cfg
    raise ValueError(
        "Google Drive de Agentes incompleto. Guarda el ID de carpeta raíz y el "
        "JSON de la cuenta de servicio en Agentes → Configuraciones."
    )


def load_drive_config(db: Session | None, school_id: int) -> DriveSchoolConfig:
    """Drive por colegio (schools_settings / .env). No usa la config de Agentes."""
    if school_id < 1:
        raise ValueError("school_id inválido.")

    if db is not None:
        row = (
            db.query(SchoolsSettingModel)
            .filter(SchoolsSettingModel.school_id == school_id)
            .first()
        )
        if row:
            root = (row.google_drive_root_folder_id or "").strip()
            sa_json = (row.google_service_account_json or "").strip()
            if root and sa_json:
                return DriveSchoolConfig(
                    school_id=school_id,
                    root_folder_id=root,
                    service_account_info=_parse_service_account_json(sa_json),
                    source="db",
                )

    env_cfg = _load_from_env(school_id)
    if env_cfg:
        return env_cfg

    raise ValueError(
        f"Google Drive no configurado para el colegio {school_id}. "
        "Agrega google_drive_root_folder_id y google_service_account_json en schools_settings, "
        "o GOOGLE_DRIVE_* en el .env."
    )


def drive_configured(db: Session | None, school_id: int) -> bool:
    try:
        load_drive_config(db, school_id)
        return True
    except ValueError:
        return False
