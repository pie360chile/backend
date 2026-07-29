"""CRUD de Google Drive OAuth por customer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.customer_drive_settings import CustomerDriveSettingModel
from app.backend.db.models.pie_core import CustomerModel
from app.backend.core.config import settings
from app.backend.utils.customer_drive_config import (
    customer_drive_configured,
    load_customer_drive_config,
    parse_drive_credentials_json,
    parse_oauth_client_pair,
    test_drive_connection,
)
from app.backend.utils import google_drive_oauth as drive_oauth


def _now() -> datetime:
    return datetime.utcnow()


def _mask_secret(value: str | None, head: int = 8) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) <= head:
        return "••••••••"
    return f"{text[:head]}••••••••"


class CustomerDriveClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _ensure_customer(self, customer_id: int) -> CustomerModel | None:
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == int(customer_id))
            .first()
        )

    def _row(self, customer_id: int) -> CustomerDriveSettingModel | None:
        return (
            self.db.query(CustomerDriveSettingModel)
            .filter(CustomerDriveSettingModel.customer_id == int(customer_id))
            .first()
        )

    def _oauth_client_for(self, customer_id: int) -> tuple[str, str] | None:
        row = self._row(customer_id)
        raw = (row.credentials_json or "").strip() if row else ""
        if raw:
            try:
                pair = parse_oauth_client_pair(raw)
                return pair["client_id"], pair["client_secret"]
            except ValueError:
                pass
        return drive_oauth.platform_oauth_client()

    def get(self, customer_id: int) -> dict[str, Any]:
        row = self._row(customer_id)
        raw = (row.credentials_json or "").strip() if row else ""
        hint = None
        auth_kind = None
        has_oauth_client = False
        has_refresh = False
        if raw:
            try:
                pair = parse_oauth_client_pair(raw)
                has_oauth_client = True
                hint = (
                    f"OAuth Web · …{pair['client_id'][-12:]}"
                    if len(pair["client_id"]) > 12
                    else f"OAuth Web · {pair['client_id']}"
                )
                auth_kind = "oauth"
            except ValueError:
                pass
            try:
                kind, info = parse_drive_credentials_json(raw)
                auth_kind = kind
                if kind == "oauth":
                    has_refresh = bool(info.get("refresh_token") or info.get("token"))
                    cid = str(info.get("client_id") or "")
                    hint = f"OAuth · …{cid[-12:]}" if len(cid) > 12 else f"OAuth · {cid}"
                else:
                    hint = str(info.get("client_email") or "service_account")
            except ValueError:
                if not hint:
                    hint = "Credenciales parciales (falta conectar Google)"
        configured = customer_drive_configured(self.db, int(customer_id))
        can_start = drive_oauth.oauth_redirect_configured() and has_oauth_client
        client_id_preview = None
        client_secret_preview = None
        refresh_token_preview = None
        if raw:
            try:
                pair = parse_oauth_client_pair(raw)
                client_id_preview = _mask_secret(pair["client_id"])
                client_secret_preview = _mask_secret(pair["client_secret"])
            except ValueError:
                pass
            try:
                kind, info = parse_drive_credentials_json(raw)
                if kind == "oauth":
                    client_id_preview = _mask_secret(str(info.get("client_id") or ""))
                    client_secret_preview = _mask_secret(str(info.get("client_secret") or ""))
                    if info.get("refresh_token"):
                        refresh_token_preview = _mask_secret(str(info.get("refresh_token") or ""))
            except ValueError:
                pass
        return {
            "customer_id": int(customer_id),
            "enabled": bool(row.enabled) if row else False,
            "root_folder_id": (row.root_folder_id or None) if row else None,
            "has_credentials": bool(raw) and has_refresh,
            "has_oauth_client": has_oauth_client,
            "credentials_hint": hint,
            "client_id_preview": client_id_preview,
            "client_secret_preview": client_secret_preview,
            "refresh_token_preview": refresh_token_preview,
            "auth_kind": auth_kind,
            "configured": configured,
            "oauth_web_ready": can_start,
            "oauth_redirect_uri": (settings.google_drive_oauth_redirect_uri or "").strip()
            or None,
            "credentials_json_value": None,
        }

    def start_oauth(self, customer_id: int) -> dict[str, Any]:
        if not self._ensure_customer(customer_id):
            return {"status": "error", "message": f"Cliente {customer_id} no encontrado."}
        pair = self._oauth_client_for(customer_id)
        if not pair:
            return {
                "status": "error",
                "message": (
                    "Guarda primero client_id y client_secret OAuth Web de este cliente, "
                    "luego pulsa Conectar con Google."
                ),
            }
        try:
            data = drive_oauth.build_authorize_url(
                customer_id=int(customer_id),
                client_id=pair[0],
                client_secret=pair[1],
            )
            return {"status": "success", "message": "OK", "data": data}
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

    def complete_oauth(self, *, code: str, state: str) -> dict[str, Any]:
        try:
            # customer_id va en state; validamos tras un peek mínimo
            peek = drive_oauth.verify_oauth_state(state)
            customer_id = int(peek["customer_id"])
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        pair = self._oauth_client_for(customer_id)
        if not pair:
            return {
                "status": "error",
                "message": "No hay client_id/secret guardados para este cliente.",
            }
        try:
            exchanged = drive_oauth.exchange_code_for_credentials(
                code=code,
                state=state,
                client_id=pair[0],
                client_secret=pair[1],
            )
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        customer_id = int(exchanged["customer_id"])
        result = self.upsert(
            customer_id,
            credentials_json=exchanged["credentials_json"],
            enabled=True,
        )
        if result.get("status") == "error":
            return result
        return {
            "status": "success",
            "message": "Google Drive conectado para este cliente.",
            "data": {"customer_id": customer_id, **(result.get("data") or {})},
        }

    def upsert(
        self,
        customer_id: int,
        *,
        root_folder_id: str | None = None,
        credentials_json: str | None = None,
        enabled: bool | None = None,
        clear: bool = False,
    ) -> dict[str, Any]:
        if not self._ensure_customer(customer_id):
            return {"status": "error", "message": f"Cliente {customer_id} no encontrado."}

        row = (
            self.db.query(CustomerDriveSettingModel)
            .filter(CustomerDriveSettingModel.customer_id == int(customer_id))
            .first()
        )
        now = _now()

        if clear:
            if row:
                self.db.delete(row)
                self.db.commit()
            return {
                "status": "success",
                "message": "Google Drive desconectado para este cliente.",
                "data": self.get(customer_id),
            }

        if row is None:
            row = CustomerDriveSettingModel(
                customer_id=int(customer_id),
                enabled=True,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)

        if enabled is not None:
            row.enabled = bool(enabled)
        if root_folder_id is not None:
            row.root_folder_id = root_folder_id.strip() or None
        if credentials_json is not None:
            raw = credentials_json.strip()
            if raw:
                # Permite guardar solo client_id+secret (antes de Conectar con Google)
                try:
                    parse_oauth_client_pair(raw)
                except ValueError:
                    try:
                        parse_drive_credentials_json(raw)
                    except ValueError as exc:
                        return {"status": "error", "message": str(exc)}
                else:
                    # Si trae refresh, valida OAuth completo; si no, guarda parcial
                    try:
                        parse_drive_credentials_json(raw)
                    except ValueError:
                        pass
                row.credentials_json = raw
        row.updated_at = now
        self.db.commit()
        return {
            "status": "success",
            "message": "Google Drive del cliente guardado.",
            "data": self.get(customer_id),
        }

    def test(self, customer_id: int) -> dict[str, Any]:
        try:
            cfg = load_customer_drive_config(self.db, int(customer_id))
            data = test_drive_connection(cfg)
            return {
                "status": "success",
                "message": "Conexión OK con el Drive del cliente.",
                "data": data,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
