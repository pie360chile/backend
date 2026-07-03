"""Configuración centralizada (12-factor). Valores sensibles vía variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def backend_env_path() -> Path:
    """Ruta absoluta a backend/.env (independiente del cwd al arrancar uvicorn)."""
    return Path(__file__).resolve().parents[3] / ".env"


def load_backend_env() -> None:
    """Carga backend/.env con override para que reinicios reflejen cambios del archivo."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = backend_env_path()
    if env_file.is_file():
        load_dotenv(env_file, override=True)


load_backend_env()


def _split_origins(raw: str | None) -> List[str]:
    if not raw or not str(raw).strip():
        return ["*"]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


_DEFAULT_CORS_RAW = ",".join(
    [
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://agent-8ceae.web.app",
        "https://agent-8ceae.firebaseapp.com",
        "https://newerp-ghdegyc9cpcpc6gq.eastus-01.azurewebsites.net",
    ]
)

# Si CORS_ORIGINS incluye "*", se agregan estos orígenes de desarrollo local.
_DEV_CORS_ORIGINS = (
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def resolve_cors_origins(origins: List[str]) -> tuple[list[str], bool]:
    """Con allow_credentials=True, '*' no es válido: usamos orígenes explícitos."""
    merged: list[str] = []
    allow_all = "*" in origins
    for origin in origins:
        if origin and origin != "*" and origin not in merged:
            merged.append(origin)
    if allow_all:
        for dev_origin in _DEV_CORS_ORIGINS:
            if dev_origin not in merged:
                merged.append(dev_origin)
    if merged:
        return merged, True
    return ["*"], False


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://admin:pie360chile@103.138.188.160:3306/pie360",
        )
    )
    secret_key: str = field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY",
            "7de4c36b48fce8dcb3a4bb527ba62d789ebf3d3a7582472ee49d430b01a7f868",
        )
    )
    algorithm: str = field(default_factory=lambda: os.getenv("ALGORITHM", "HS256"))
    files_dir: str = field(
        default_factory=lambda: os.getenv(
            "FILES_DIR", "/var/www/pie360backend.cl/public_html/files"
        )
    )
    cors_origins: List[str] = field(
        default_factory=lambda: _split_origins(
            os.getenv("CORS_ORIGINS", _DEFAULT_CORS_RAW)
        )
    )
    api_root_path: str = field(default_factory=lambda: os.getenv("API_ROOT_PATH", "/api"))
    workspace_agent_id: str = field(
        default_factory=lambda: os.getenv(
            "WORKSPACE_AGENT_ID",
            "agtch_6a35d3014cbc8191911eed3847b3e8fe",
        )
    )
    workspace_agent_name: str = field(
        default_factory=lambda: os.getenv("WORKSPACE_AGENT_NAME", "Redactor de Informes PIE")
    )
    workspace_agent_api_base: str = field(
        default_factory=lambda: os.getenv(
            "WORKSPACE_AGENT_API_BASE",
            "https://api.chatgpt.com/v1/workspace_agents",
        )
    )
    agent_access_token: str = field(
        default_factory=lambda: os.getenv("AGENT_ACCESS_TOKEN", "")
    )
    mcp_secret: str = field(default_factory=lambda: os.getenv("MCP_SECRET", ""))
    api_public_base: str = field(
        default_factory=lambda: os.getenv(
            "API_PUBLIC_BASE",
            "https://pie360backend.cl/api",
        )
    )
    google_drive_credentials_path: str = field(
        default_factory=lambda: os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "")
    )
    google_drive_root_folder_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    agent_v2_model: str = field(default_factory=lambda: os.getenv("AGENT_V2_MODEL", "gpt-5.5"))


settings = Settings()


def apply_settings_to_process_env() -> None:
    """Compatibilidad con código que lee os.environ directamente."""
    os.environ.setdefault("SECRET_KEY", settings.secret_key)
    os.environ.setdefault("ALGORITHM", settings.algorithm)
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
