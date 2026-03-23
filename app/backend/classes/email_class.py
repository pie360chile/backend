"""
Servicio de correo reutilizable (HTML / texto plano vía SMTP).

Variables de entorno (opcionales; si faltan host/from no se envía y se registra en log):
  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
  SMTP_FROM, SMTP_USE_TLS (default true), SMTP_USE_SSL (default false; p.ej. puerto 465),
  EMAIL_LOGO_URL (URL absoluta del logo; si vacío se usa texto Pie360),
  FRONTEND_PUBLIC_URL (base del front, p.ej. https://app.pie360.cl)
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Optional, Sequence, Union

logger = logging.getLogger(__name__)

# Marca Pie360 (alineado con landing / admin)
BRAND_PRIMARY = "#1593D5"
BRAND_ACCENT = "#F7B033"
BRAND_BG = "#f4f7fb"


def _default_logo_url() -> str:
    explicit = (os.getenv("EMAIL_LOGO_URL") or "").strip()
    if explicit:
        return explicit
    base = (os.getenv("FRONTEND_PUBLIC_URL") or "http://localhost:5173").rstrip("/")
    return f"{base}/favicon.svg"


class EmailServiceClass:
    """
    Envío de correos por SMTP. Instanciable con parámetros o leyendo el entorno.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_address: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
    ) -> None:
        self.host = (host if host is not None else (os.getenv("SMTP_HOST") or "")).strip()
        p = port if port is not None else os.getenv("SMTP_PORT", "587")
        try:
            self.port = int(p)
        except (TypeError, ValueError):
            self.port = 587
        self.username = (
            (username if username is not None else os.getenv("SMTP_USER")) or ""
        ).strip() or None
        self.password = (
            (password if password is not None else os.getenv("SMTP_PASSWORD")) or ""
        ).strip() or None
        self.from_address = (
            (from_address if from_address is not None else os.getenv("SMTP_FROM")) or ""
        ).strip()

        if use_tls is not None:
            self.use_tls = use_tls
        else:
            self.use_tls = (os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"))

        if use_ssl is not None:
            self.use_ssl = use_ssl
        else:
            self.use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")

    def is_configured(self) -> bool:
        return bool(self.host and self.from_address)

    def wrap_branded_layout(
        self,
        *,
        title: str,
        inner_html: str,
        preheader: str = "",
        logo_url: Optional[str] = None,
        footer_note: str = "",
    ) -> str:
        """Plantilla HTML con cabecera de marca; reutilizable para otros correos."""
        safe_title = escape(title)
        logo = (logo_url or _default_logo_url()).strip()
        pre = escape(preheader) if preheader else ""
        foot = escape(footer_note) if footer_note else ""

        logo_block = ""
        if logo:
            safe_logo = escape(logo, quote=True)
            logo_block = (
                f'<img src="{safe_logo}" alt="Pie360" width="160" height="auto" '
                'style="max-width:200px;height:auto;display:block;margin:0 auto 8px auto;border:0;" />'
            )
        else:
            logo_block = (
                f'<p style="margin:0;font-size:22px;font-weight:700;color:{BRAND_PRIMARY};">Pie360</p>'
            )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
</head>
<body style="margin:0;padding:0;background-color:{BRAND_BG};font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <span style="display:none;font-size:1px;color:{BRAND_BG};max-height:0;overflow:hidden;">{pre}</span>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:{BRAND_BG};padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(21,147,213,0.12);">
          <tr>
            <td style="padding:28px 28px 8px 28px;text-align:center;background:linear-gradient(135deg,{BRAND_PRIMARY} 0%,#0d6ba8 100%);">
              {logo_block}
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 28px 28px;color:#333333;font-size:16px;line-height:1.55;">
              <h1 style="margin:16px 0 12px 0;font-size:20px;color:{BRAND_PRIMARY};">{safe_title}</h1>
              {inner_html}
            </td>
          </tr>
          <tr>
            <td style="padding:0 28px 24px 28px;font-size:13px;color:#6b7280;text-align:center;border-top:1px solid #e5e7eb;">
              <p style="margin:16px 0 8px 0;">{foot if foot else "Pie360 — Plataforma educativa"}</p>
              <p style="margin:0;color:{BRAND_ACCENT};font-weight:600;">© Pie360</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    def password_reset_email_html(
        self,
        *,
        reset_url: str,
        user_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        expires_minutes: int = 60,
    ) -> str:
        """HTML del correo de recuperación de contraseña."""
        safe_url = escape(reset_url, quote=True)
        greeting = ""
        if user_name:
            greeting = f"<p style=\"margin:0 0 16px 0;\">Hola <strong>{escape(user_name)}</strong>,</p>"
        inner = f"""
{greeting}
<p style="margin:0 0 16px 0;">Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>Pie360</strong>.</p>
<p style="margin:0 0 20px 0;">Haz clic en el botón para elegir una nueva contraseña (el enlace vence en aproximadamente <strong>{int(expires_minutes)}</strong> minutos):</p>
<p style="margin:0 0 24px 0;text-align:center;">
  <a href="{safe_url}" style="display:inline-block;padding:14px 28px;background:{BRAND_ACCENT};color:#1f2937;text-decoration:none;font-weight:700;border-radius:8px;font-size:16px;">Restablecer contraseña</a>
</p>
<p style="margin:0 0 12px 0;font-size:14px;color:#6b7280;">Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
<p style="margin:0 0 20px 0;word-break:break-all;font-size:13px;color:{BRAND_PRIMARY};">{safe_url}</p>
<p style="margin:0;font-size:14px;color:#6b7280;">Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
"""
        return self.wrap_branded_layout(
            title="Restablecer contraseña",
            inner_html=inner,
            preheader="Instrucciones para restablecer tu contraseña en Pie360.",
            logo_url=logo_url,
            footer_note="Este es un correo automático; no respondas a este mensaje.",
        )

    def send_html(
        self,
        to_addresses: Union[str, Sequence[str]],
        subject: str,
        html_body: str,
        text_plain: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Envía un correo multipart (HTML + opcional texto plano).
        Retorna True si se envió, False si SMTP no está configurado o falló el envío.
        """
        if isinstance(to_addresses, str):
            recipients: list[str] = [to_addresses.strip()]
        else:
            recipients = [a.strip() for a in to_addresses if a and str(a).strip()]

        if not recipients:
            logger.warning("EmailServiceClass.send_html: no hay destinatarios")
            return False

        if not self.is_configured():
            logger.warning(
                "EmailServiceClass: SMTP no configurado (SMTP_HOST / SMTP_FROM). "
                "No se envía el correo."
            )
            return False

        plain = text_plain or "Este mensaje requiere un cliente de correo compatible con HTML."

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(recipients)
        if reply_to:
            msg["Reply-To"] = reply_to.strip()

        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as server:
                    if self.username and self.password is not None:
                        server.login(self.username, self.password)
                    server.sendmail(self.from_address, recipients, msg.as_string())
            else:
                with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    if self.username and self.password is not None:
                        server.login(self.username, self.password)
                    server.sendmail(self.from_address, recipients, msg.as_string())
            return True
        except Exception:
            logger.exception("EmailServiceClass: error al enviar correo a %s", recipients)
            return False
