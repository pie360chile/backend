"""Configuración centralizada (12-factor). Valores sensibles vía variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


def _split_origins(raw: str | None) -> List[str]:
    if not raw or not str(raw).strip():
        return ["*"]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


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
            os.getenv(
                "CORS_ORIGINS",
                "*,https://newerp-ghdegyc9cpcpc6gq.eastus-01.azurewebsites.net",
            )
        )
    )
    api_root_path: str = field(default_factory=lambda: os.getenv("API_ROOT_PATH", "/api"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_agent_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_AGENT_MODEL", "gpt-5.5")
    )


settings = Settings()


def apply_settings_to_process_env() -> None:
    """Compatibilidad con código que lee os.environ['SECRET_KEY'] directamente."""
    os.environ.setdefault("SECRET_KEY", settings.secret_key)
    os.environ.setdefault("ALGORITHM", settings.algorithm)
