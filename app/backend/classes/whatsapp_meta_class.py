"""
WhatsApp Cloud API (Meta / Facebook Graph).
Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api

Variables de entorno:
  WHATSAPP_CLOUD_ACCESS_TOKEN  — token de acceso permanente de la app
  WHATSAPP_PHONE_NUMBER_ID     — ID del número de negocio (no el número en sí)
  WHATSAPP_TEMPLATE_NAME       — nombre exacto de la plantilla aprobada en Meta
  WHATSAPP_TEMPLATE_LANG       — código idioma (ej. es, es_CL)
  WHATSAPP_GRAPH_VERSION       — opcional, default v21.0

La plantilla debe existir en Meta Business y coincidir con los parámetros enviados.
Si el cuerpo tiene {{1}} y {{2}}, pase body_texts con 2 strings [nombre_estudiante, nombre_formulario].
Si la plantilla no tiene variables, deje body_texts vacío o None.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


def normalize_whatsapp_e164(raw: Optional[str]) -> Optional[str]:
    """Convierte celular chileno típico a dígitos E.164 sin + (Meta espera solo dígitos)."""
    if raw is None or not str(raw).strip():
        return None
    digits = "".join(c for c in str(raw) if c.isdigit())
    if not digits:
        return None
    # 9xxxxxxxx (9 dígitos móvil CL)
    if len(digits) == 9 and digits[0] == "9":
        digits = "56" + digits
    elif len(digits) == 11 and digits.startswith("56"):
        pass
    elif len(digits) == 10 and digits.startswith("56"):
        pass
    elif len(digits) == 8 and digits[0] == "9":
        digits = "569" + digits
    if len(digits) < 11:
        return None
    return digits


class WhatsAppMetaClass:
    @staticmethod
    def _config() -> tuple[str, str, str, str, str]:
        token = (os.environ.get("WHATSAPP_CLOUD_ACCESS_TOKEN") or "").strip()
        phone_id = (os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        template = (os.environ.get("WHATSAPP_TEMPLATE_NAME") or "").strip()
        lang = (os.environ.get("WHATSAPP_TEMPLATE_LANG") or "es").strip()
        version = (os.environ.get("WHATSAPP_GRAPH_VERSION") or "v21.0").strip()
        return token, phone_id, template, lang, version

    @staticmethod
    def is_configured() -> bool:
        token, phone_id, template, _, _ = WhatsAppMetaClass._config()
        return bool(token and phone_id and template)

    @staticmethod
    def send_template(
        to_e164: str,
        body_texts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Envía un mensaje de plantilla. body_texts: valores para variables del cuerpo en orden.
        """
        token, phone_id, template, lang, version = WhatsAppMetaClass._config()
        if not token or not phone_id or not template:
            logger.warning("WhatsApp Meta: faltan variables de entorno; no se envía mensaje.")
            return {
                "ok": False,
                "skipped": True,
                "reason": "missing_env",
                "detail": "Configure WHATSAPP_CLOUD_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TEMPLATE_NAME",
            }

        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        tpl: Dict[str, Any] = {
            "name": template,
            "language": {"code": lang},
        }
        if body_texts:
            params = []
            for t in body_texts:
                text = (t or "")[:1024]
                params.append({"type": "text", "text": text})
            tpl["components"] = [{"type": "body", "parameters": params}]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_e164,
            "type": "template",
            "template": tpl,
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=45)
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:500]}
            if r.status_code >= 400:
                logger.warning("WhatsApp Meta error %s: %s", r.status_code, body)
                return {
                    "ok": False,
                    "skipped": False,
                    "status_code": r.status_code,
                    "response": body,
                }
            return {"ok": True, "skipped": False, "response": body}
        except requests.RequestException as e:
            logger.exception("WhatsApp Meta request failed")
            return {"ok": False, "skipped": False, "error": str(e)}


def notify_guardians_for_form(
    db,
    student_ids: List[int],
    form_name: str,
    student_label_fn,
    guardian_phone_fn,
) -> Dict[str, Any]:
    """
    student_label_fn(sid) -> str nombre estudiante
    guardian_phone_fn(sid) -> Optional[str] celular apoderado
    """
    if not student_ids:
        return {"attempted": 0, "sent": 0, "failed": [], "skipped_config": not WhatsAppMetaClass.is_configured()}

    if not WhatsAppMetaClass.is_configured():
        return {
            "attempted": len(student_ids),
            "sent": 0,
            "failed": [{"student_id": sid, "reason": "whatsapp_not_configured"} for sid in student_ids],
            "skipped_config": True,
            "hint": "Defina WHATSAPP_CLOUD_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID y WHATSAPP_TEMPLATE_NAME en el servidor.",
        }

    sent = 0
    failed: List[Dict[str, Any]] = []
    for sid in student_ids:
        phone_raw = guardian_phone_fn(sid)
        to = normalize_whatsapp_e164(phone_raw)
        if not to:
            failed.append({"student_id": sid, "reason": "invalid_or_missing_phone", "raw": phone_raw})
            continue
        st_name = student_label_fn(sid) or "Estudiante"
        fn = (form_name or "Formulario")[:200]
        # Plantilla típica con 2 variables: nombre estudiante, nombre formulario
        result = WhatsAppMetaClass.send_template(to, body_texts=[st_name, fn])
        if result.get("ok"):
            sent += 1
        else:
            failed.append(
                {
                    "student_id": sid,
                    "reason": result.get("reason") or "send_failed",
                    "detail": result.get("response") or result.get("error"),
                }
            )

    return {
        "attempted": len(student_ids),
        "sent": sent,
        "failed": failed,
        "skipped_config": False,
    }
