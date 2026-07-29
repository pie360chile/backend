"""Configuración Google Drive por customer (cada cliente su propia nube OAuth/SA)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.backend.core.config import settings

GOOGLE_DRIVE_ENABLED = True
GOOGLE_DRIVE_DISABLED_MESSAGE = (
    "Google Drive está desactivado temporalmente. Los archivos se guardan solo en el servidor."
)

CredKind = Literal["service_account", "oauth"]


def assert_google_drive_enabled() -> None:
    if not GOOGLE_DRIVE_ENABLED:
        raise ValueError(GOOGLE_DRIVE_DISABLED_MESSAGE)


@dataclass(frozen=True)
class DriveCustomerConfig:
    """Credenciales Drive de un customer (nube propia)."""

    customer_id: int
    root_folder_id: str
    source: str  # "customer:{id}" | "agents_settings" | "env" | "school_legacy"
    service_account_info: dict[str, Any] | None = None
    oauth_info: dict[str, Any] | None = None

    @property
    def kind(self) -> CredKind:
        if self.oauth_info:
            return "oauth"
        return "service_account"

    @property
    def cache_key(self) -> str:
        payload = {
            "kind": self.kind,
            "customer_id": self.customer_id,
            "sa": self.service_account_info,
            "oauth": {
                "client_id": (self.oauth_info or {}).get("client_id"),
                "refresh_token": (self.oauth_info or {}).get("refresh_token"),
            }
            if self.oauth_info
            else None,
        }
        return f"c{self.customer_id}:{self.source}:{hash(json.dumps(payload, sort_keys=True, default=str))}"


# Alias de compatibilidad (código antiguo importaba DriveSchoolConfig)
DriveSchoolConfig = DriveCustomerConfig


def _parse_oauth_info(data: dict[str, Any], *, require_token: bool = True) -> dict[str, Any]:
    client_id = str(data.get("client_id") or "").strip()
    client_secret = str(data.get("client_secret") or "").strip()
    refresh_token = str(data.get("refresh_token") or "").strip()
    token = str(data.get("token") or data.get("access_token") or "").strip() or None
    token_uri = str(
        data.get("token_uri") or "https://oauth2.googleapis.com/token"
    ).strip()

    if not client_id or not client_secret:
        for key in ("installed", "web"):
            block = data.get(key)
            if isinstance(block, dict):
                client_id = client_id or str(block.get("client_id") or "").strip()
                client_secret = client_secret or str(block.get("client_secret") or "").strip()
                break

    if not client_id or not client_secret:
        raise ValueError(
            "OAuth incompleto: falta client_id o client_secret. "
            "Pega el JSON OAuth (client_id, client_secret, refresh_token)."
        )
    if require_token and not refresh_token and not token:
        raise ValueError(
            "OAuth incompleto: falta refresh_token (recomendado) o access_token."
        )

    return {
        "type": "authorized_user",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token or None,
        "token": token,
        "token_uri": token_uri,
    }


def parse_oauth_client_pair(raw: str) -> dict[str, str]:
    """Extrae client_id/secret aunque aún no haya refresh_token."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Credenciales vacías.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("El JSON de Google Drive no es válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("Las credenciales deben ser un objeto JSON.")
    info = _parse_oauth_info(data, require_token=False)
    return {
        "client_id": str(info["client_id"]),
        "client_secret": str(info["client_secret"]),
    }


def parse_drive_credentials_json(raw: str) -> tuple[CredKind, dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Credenciales de Google Drive vacías.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("El JSON de Google Drive no es válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("Las credenciales deben ser un objeto JSON.")

    ctype = str(data.get("type") or "").strip().lower()
    if ctype == "service_account":
        if not data.get("private_key") or not data.get("client_email"):
            raise ValueError(
                "El JSON de cuenta de servicio debe incluir private_key y client_email."
            )
        return "service_account", data

    if (
        ctype in {"authorized_user", "oauth", "user"}
        or data.get("refresh_token")
        or data.get("client_secret")
        or isinstance(data.get("installed"), dict)
        or isinstance(data.get("web"), dict)
    ):
        return "oauth", _parse_oauth_info(data)

    raise ValueError(
        "JSON no reconocido. Usa OAuth "
        '(client_id, client_secret, refresh_token) o type="service_account".'
    )


def _parse_service_account_json(raw: str) -> dict[str, Any]:
    kind, info = parse_drive_credentials_json(raw)
    if kind != "service_account":
        raise ValueError('Se espera JSON type="service_account".')
    return info


def _service_account_info_from_env_file() -> dict[str, Any] | None:
    cred_path = (settings.google_drive_credentials_path or "").strip()
    if not cred_path:
        return None
    path = Path(cred_path).expanduser().resolve()
    if not path.is_file():
        return None
    kind, info = parse_drive_credentials_json(path.read_text(encoding="utf-8"))
    if kind != "service_account":
        return None
    return info


def _oauth_info_from_env() -> dict[str, Any] | None:
    client_id = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    refresh_token = (os.getenv("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN") or "").strip()
    if not (client_id and client_secret and refresh_token):
        cred_path = (settings.google_drive_credentials_path or "").strip()
        if cred_path:
            path = Path(cred_path).expanduser().resolve()
            if path.is_file():
                try:
                    kind, info = parse_drive_credentials_json(
                        path.read_text(encoding="utf-8")
                    )
                    if kind == "oauth":
                        return info
                except ValueError:
                    pass
        return None
    return _parse_oauth_info(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    )


def _config_from_parts(
    *,
    customer_id: int,
    root: str,
    raw_json: str | None,
    source: str,
    allow_env_fallback: bool = True,
) -> DriveCustomerConfig | None:
    root = (root or "").strip()
    if not root:
        return None

    if raw_json and raw_json.strip():
        kind, info = parse_drive_credentials_json(raw_json)
        if kind == "oauth":
            return DriveCustomerConfig(
                customer_id=int(customer_id),
                root_folder_id=root,
                oauth_info=info,
                source=source,
            )
        return DriveCustomerConfig(
            customer_id=int(customer_id),
            root_folder_id=root,
            service_account_info=info,
            source=source,
        )

    if not allow_env_fallback:
        return None

    oauth = _oauth_info_from_env()
    if oauth:
        return DriveCustomerConfig(
            customer_id=int(customer_id),
            root_folder_id=root,
            oauth_info=oauth,
            source=f"{source}+env_oauth",
        )

    sa = _service_account_info_from_env_file()
    if sa:
        return DriveCustomerConfig(
            customer_id=int(customer_id),
            root_folder_id=root,
            service_account_info=sa,
            source=f"{source}+env_file",
        )
    return None


def load_customer_drive_config(db: Session, customer_id: int) -> DriveCustomerConfig:
    """Carga el Drive del customer (tabla customer_drive_settings)."""
    assert_google_drive_enabled()
    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")

    from app.backend.db.models.customer_drive_settings import CustomerDriveSettingModel

    row = (
        db.query(CustomerDriveSettingModel)
        .filter(CustomerDriveSettingModel.customer_id == int(customer_id))
        .first()
    )
    if not row or not bool(getattr(row, "enabled", True)):
        raise ValueError(
            f"Google Drive no está activo para el cliente {customer_id}. "
            "Conéctalo en la ficha del cliente (OAuth + carpeta raíz)."
        )

    root = (row.root_folder_id or "").strip()
    raw = (row.credentials_json or "").strip() or None
    cfg = _config_from_parts(
        customer_id=int(customer_id),
        root=root,
        raw_json=raw,
        source=f"customer:{int(customer_id)}",
        allow_env_fallback=False,
    )
    if cfg:
        return cfg
    raise ValueError(
        f"Google Drive incompleto para el cliente {customer_id}. "
        "Guarda carpeta raíz + JSON OAuth (client_id, client_secret, refresh_token)."
    )


def customer_drive_configured(db: Session, customer_id: int) -> bool:
    try:
        load_customer_drive_config(db, customer_id)
        return True
    except ValueError:
        return False


def load_agents_global_drive_config(
    db: Session, customer_id: int | None = None
) -> DriveCustomerConfig:
    """Drive de Agentes: siempre por customer cuando hay customer_id."""
    assert_google_drive_enabled()
    if customer_id is not None and int(customer_id) > 0:
        return load_customer_drive_config(db, int(customer_id))
    raise ValueError(
        "Indica customer_id: cada cliente PIE360 usa su propio Google Drive."
    )


def load_drive_config(db: Session | None, school_id: int) -> DriveCustomerConfig:
    """
    Compatibilidad: flujos por school_id resuelven al Drive del customer dueño.
    (Ya no se usa una nube por colegio como fuente principal.)
    """
    assert_google_drive_enabled()
    if school_id < 1:
        raise ValueError("school_id inválido.")
    if db is None:
        raise ValueError("Se requiere db para resolver Drive del customer.")

    from app.backend.db.models.pie_core import SchoolModel

    school = db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
    if not school or not getattr(school, "customer_id", None):
        raise ValueError(
            f"No hay customer para el colegio {school_id}; no se puede cargar Drive."
        )
    return load_customer_drive_config(db, int(school.customer_id))


def drive_configured(db: Session | None, school_id: int) -> bool:
    try:
        load_drive_config(db, school_id)
        return True
    except ValueError:
        return False


def test_drive_connection(config: DriveCustomerConfig) -> dict[str, Any]:
    from app.backend.utils import google_drive_storage as gdrive

    service = gdrive._service_for_config(config)
    meta = (
        service.files()
        .get(
            fileId=config.root_folder_id,
            fields="id,name,mimeType",
            supportsAllDrives=True,
        )
        .execute()
    )
    children = (
        service.files()
        .list(
            q=f"'{config.root_folder_id}' in parents and trashed = false",
            spaces="drive",
            fields="files(id,name,mimeType)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = children.get("files") or []
    return {
        "ok": True,
        "auth": config.kind,
        "customer_id": config.customer_id,
        "root": {
            "id": meta.get("id"),
            "name": meta.get("name"),
            "mimeType": meta.get("mimeType"),
        },
        "sample_children": [
            {"id": f.get("id"), "name": f.get("name"), "mimeType": f.get("mimeType")}
            for f in files
        ],
        "children_count_sample": len(files),
    }
