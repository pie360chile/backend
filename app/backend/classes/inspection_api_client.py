"""
HTTP client for Inspection API (configurable base URL).
Login: POST multipart form-data → Bearer token.
Remote endpoints (multipart field `rut`): /getDatosAlumno, /getDatosFuncionario.

Env:
  INSPECTION_API_BASE_URL  (default: https://liceomixto.inspection.cl/api)
  INSPECTION_API_USERNAME
  INSPECTION_API_PASSWORD
  INSPECTION_API_TIMEOUT   (seconds, default 30)
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None and str(v).strip() != "" else default


class InspectionApiClient:
    """Token en memoria por worker (gunicorn); se renueva al expirar o ante 401."""

    _lock = threading.Lock()
    _token: Optional[str] = None
    _expires_at: Optional[datetime] = None

    def __init__(self):
        self.base_url = (_env("INSPECTION_API_BASE_URL") or "https://liceomixto.inspection.cl/api").rstrip("/")
        self.username = _env("INSPECTION_API_USERNAME")
        self.password = _env("INSPECTION_API_PASSWORD")
        try:
            self.timeout = float(_env("INSPECTION_API_TIMEOUT") or "30")
        except ValueError:
            self.timeout = 30.0

    def is_configured(self) -> bool:
        return bool(self.username and self.password)

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        if not self._expires_at:
            return True
        now = datetime.now(timezone.utc)
        exp = self._expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now < exp

    def _parse_expires(self, raw: Any) -> Optional[datetime]:
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
        try:
            # "2026-03-23 18:30:00" sin zona → asumir local del servidor o UTC
            if "T" in s:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc) + timedelta(hours=7)

    def login(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "message": "INSPECTION_API_USERNAME / INSPECTION_API_PASSWORD not set", "data": None}

        url = f"{self.base_url}/login"
        # multipart/form-data (per Inspection API docs)
        files = {
            "username": (None, str(self.username)),
            "password": (None, str(self.password)),
        }
        try:
            r = requests.post(url, files=files, timeout=self.timeout)
            try:
                body = r.json()
            except Exception:
                return {"ok": False, "message": f"Non-JSON response: {r.text[:200]}", "data": None}

            if r.status_code >= 400 or not body.get("ok"):
                return {"ok": False, "message": body.get("message") or f"HTTP {r.status_code}", "data": body.get("data")}

            data = body.get("data") or {}
            token = data.get("token")
            if not token:
                return {"ok": False, "message": "Login response missing data.token", "data": None}

            with self._lock:
                self.__class__._token = token
                exp = self._parse_expires(data.get("expires_at"))
                self.__class__._expires_at = exp or (datetime.now(timezone.utc) + timedelta(hours=7))

            return {"ok": True, "message": body.get("message") or "OK", "data": data}
        except requests.RequestException as e:
            return {"ok": False, "message": str(e), "data": None}

    def get_bearer_token(self) -> Optional[str]:
        with self._lock:
            if self._token_valid():
                return self._token
        if not self.is_configured():
            return None
        res = self.login()
        if not res.get("ok"):
            return None
        with self._lock:
            return self._token

    def _post_multipart_rut(self, remote_path: str, rut: str, anio: int | None = None) -> Dict[str, Any]:
        """
        POST {base}/{remote_path} with form field rut (multipart). Used for getDatosAlumno, getDatosFuncionario, etc.
        """
        rut = (rut or "").strip()
        if not rut:
            return {"ok": False, "message": "RUT is required", "data": None}

        token = self.get_bearer_token()
        if not token:
            return {"ok": False, "message": "Inspection API authentication failed (check credentials)", "data": None}

        remote_path = remote_path.lstrip("/")
        url = f"{self.base_url}/{remote_path}"
        headers = {"Authorization": f"Bearer {token}"}
        files = {
            "rut": (None, rut),
            **({"anio": (None, str(anio))} if anio is not None else {}),
        }

        try:
            r = requests.post(url, headers=headers, files=files, timeout=self.timeout)
            try:
                body = r.json()
            except Exception:
                return {"ok": False, "message": f"Non-JSON response: {r.text[:200]}", "data": None}

            if r.status_code == 401:
                with self._lock:
                    self.__class__._token = None
                    self.__class__._expires_at = None
                token2 = self.get_bearer_token()
                if token2:
                    r = requests.post(
                        url,
                        headers={"Authorization": f"Bearer {token2}"},
                        files=files,
                        timeout=self.timeout,
                    )
                    try:
                        body = r.json()
                    except Exception:
                        return {"ok": False, "message": "Retry after 401 failed", "data": None}

            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": body.get("message") or f"HTTP {r.status_code}",
                    "data": body.get("data"),
                }

            return body if isinstance(body, dict) else {"ok": False, "message": "Invalid response body", "data": None}
        except requests.RequestException as e:
            return {"ok": False, "message": str(e), "data": None}

    def _get_with_bearer(self, remote_path: str) -> Dict[str, Any]:
        token = self.get_bearer_token()
        if not token:
            return {"ok": False, "message": "Inspection API authentication failed (check credentials)", "data": None}

        remote_path = remote_path.lstrip("/")
        url = f"{self.base_url}/{remote_path}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            r = requests.get(url, headers=headers, timeout=self.timeout)
            try:
                body = r.json()
            except Exception:
                return {"ok": False, "message": f"Non-JSON response: {r.text[:200]}", "data": None}

            if r.status_code == 401:
                with self._lock:
                    self.__class__._token = None
                    self.__class__._expires_at = None
                token2 = self.get_bearer_token()
                if token2:
                    r = requests.get(
                        url,
                        headers={"Authorization": f"Bearer {token2}"},
                        timeout=self.timeout,
                    )
                    try:
                        body = r.json()
                    except Exception:
                        return {"ok": False, "message": "Retry after 401 failed", "data": None}

            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": body.get("message") or f"HTTP {r.status_code}",
                    "data": body.get("data"),
                }

            return body if isinstance(body, dict) else {"ok": False, "message": "Invalid response body", "data": None}
        except requests.RequestException as e:
            return {"ok": False, "message": str(e), "data": None}

    def fetch_student_data(self, rut: str, anio: int | None = None) -> Dict[str, Any]:
        """POST /getDatosAlumno — remote path fixed by Inspection."""
        return self._post_multipart_rut("getDatosAlumno", rut, anio)

    def fetch_professional_data(self, rut: str) -> Dict[str, Any]:
        """POST /getDatosFuncionario — staff/professional by RUT (remote path fixed by Inspection)."""
        return self._post_multipart_rut("getDatosFuncionario", rut)

    def fetch_communes_list(self) -> Dict[str, Any]:
        """GET /listado/comunas — catálogo remoto de comunas."""
        return self._get_with_bearer("listado/comunas")

    def fetch_regions_list(self) -> Dict[str, Any]:
        """GET /listado/provincias — catálogo remoto (provincias/regiones según API Inspection)."""
        return self._get_with_bearer("listado/provincias")


def _first_value(data: Dict[str, Any], keys: tuple) -> Optional[str]:
    for k in keys:
        v = data.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def merge_inspection_into_student_inputs(student_inputs: Dict[str, Any], api_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge fields returned by the remote student endpoint onto student_inputs (keeps existing keys if no match).
    api_payload: full remote JSON { ok, message, data }.
    """
    out = dict(student_inputs)
    if not api_payload.get("ok"):
        return out

    raw = api_payload.get("data")
    if raw is None:
        return out
    if isinstance(raw, list) and len(raw) > 0:
        data = raw[0] if isinstance(raw[0], dict) else {}
    elif isinstance(raw, dict):
        data = raw
    else:
        return out

    # Nombres (varias claves posibles según la API)
    nv = _first_value(
        data,
        (
            "nombres",
            "nombre",
            "nombre_alumno",
            "nombres_alumno",
            "names",
        ),
    )
    if nv:
        out["names"] = nv

    ap = _first_value(
        data,
        (
            "apellido_paterno",
            "apellidoPaterno",
            "apellido_p",
            "father_lastname",
            "primer_apellido",
        ),
    )
    if ap:
        out["father_lastname"] = ap

    am = _first_value(
        data,
        (
            "apellido_materno",
            "apellidoMaterno",
            "apellido_m",
            "mother_lastname",
            "segundo_apellido",
        ),
    )
    if am:
        out["mother_lastname"] = am

    rut = _first_value(data, ("rut", "identification_number", "identificacion"))
    if rut:
        out["identification_number"] = rut

    email = _first_value(data, ("email", "correo", "correo_electronico", "mail"))
    if email:
        out["email"] = email

    phone = _first_value(
        data,
        ("telefono", "teléfono", "phone", "celular", "movil", "móvil"),
    )
    if phone:
        out["phone"] = phone

    born = _first_value(
        data,
        (
            "fecha_nacimiento",
            "fechaNacimiento",
            "born_date",
            "birth_date",
            "fecha_nac",
        ),
    )
    if born:
        out["born_date"] = born

    return out
