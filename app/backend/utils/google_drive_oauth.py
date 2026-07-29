"""OAuth Web de Google Drive por customer (Aplicación web)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

from app.backend.core.config import settings

DRIVE_OAUTH_SCOPES = ("https://www.googleapis.com/auth/drive",)


def oauth_redirect_configured() -> bool:
    return bool((settings.google_drive_oauth_redirect_uri or "").strip())


def oauth_web_configured() -> bool:
    """True si hay redirect URI (client_id/secret van por customer)."""
    return oauth_redirect_configured()


def platform_oauth_client() -> tuple[str, str] | None:
    cid = (settings.google_drive_oauth_client_id or "").strip()
    secret = (settings.google_drive_oauth_client_secret or "").strip()
    if cid and secret:
        return cid, secret
    return None


def _sign_state(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(
        (settings.secret_key or "pie360").encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    import base64

    body = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{body}.{sig}"


def _verify_state(state: str) -> dict[str, Any]:
    import base64

    if not state or "." not in state:
        raise ValueError("state OAuth inválido.")
    body, sig = state.rsplit(".", 1)
    pad = "=" * (-len(body) % 4)
    raw = base64.urlsafe_b64decode(body + pad).decode("utf-8")
    expected = hmac.new(
        (settings.secret_key or "pie360").encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("state OAuth no verificado.")
    data = json.loads(raw)
    if int(data.get("exp") or 0) < int(time.time()):
        raise ValueError("El enlace OAuth expiró. Vuelve a pulsar Conectar Drive.")
    return data


def verify_oauth_state(state: str) -> dict[str, Any]:
    return _verify_state(state)


def build_authorize_url(
    *,
    customer_id: int,
    client_id: str,
    client_secret: str,
) -> dict[str, str]:
    redirect = (settings.google_drive_oauth_redirect_uri or "").strip()
    if not redirect:
        raise ValueError(
            "Falta GOOGLE_DRIVE_OAUTH_REDIRECT_URI en el .env del servidor PIE360 "
            "(solo el redirect; cada cliente usa su propio client_id/secret)."
        )
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if not client_id or not client_secret:
        raise ValueError(
            "Guarda primero el client_id y client_secret OAuth Web de este cliente."
        )
    if int(customer_id) < 1:
        raise ValueError("customer_id inválido.")

    state = _sign_state(
        {
            "customer_id": int(customer_id),
            "client_id": client_id,
            "exp": int(time.time()) + 600,
        }
    )
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(DRIVE_OAUTH_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"authorize_url": url, "state": state}


def exchange_code_for_credentials(
    *,
    code: str,
    state: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """Intercambia code por tokens y devuelve {customer_id, credentials_json}."""
    redirect = (settings.google_drive_oauth_redirect_uri or "").strip()
    if not redirect:
        raise ValueError("Falta GOOGLE_DRIVE_OAUTH_REDIRECT_URI en el servidor.")
    data = _verify_state(state)
    customer_id = int(data["customer_id"])
    expected_client = str(data.get("client_id") or "").strip()
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if expected_client and client_id and expected_client != client_id:
        raise ValueError("El client_id no coincide con el inicio OAuth.")
    if not client_id or not client_secret:
        raise ValueError("Faltan client_id/client_secret del cliente para el callback.")
    code = (code or "").strip()
    if not code:
        raise ValueError("Falta el code de Google.")

    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise ValueError(
            "Falta google-auth-oauthlib. Instala: pip install google-auth-oauthlib"
        ) from exc

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=list(DRIVE_OAUTH_SCOPES))
    flow.redirect_uri = redirect
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        raise ValueError(
            "Google no devolvió refresh_token. Revoca el acceso de la app en "
            "https://myaccount.google.com/permissions y vuelve a conectar con prompt=consent."
        )

    credentials_obj = {
        "type": "authorized_user",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": creds.refresh_token,
        "token": creds.token,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return {
        "customer_id": customer_id,
        "credentials_json": json.dumps(credentials_obj, ensure_ascii=False),
    }


def frontend_return_url(*, ok: bool, customer_id: int | None, message: str = "") -> str:
    base = (
        settings.google_drive_oauth_success_url
        or "https://pie-360-chile.web.app/agents/settings"
    ).strip()
    sep = "&" if "?" in base else "?"
    q = {
        "drive_oauth": "ok" if ok else "error",
        "customer_id": str(customer_id or ""),
        "message": message[:200],
    }
    return f"{base}{sep}{urlencode(q)}"
