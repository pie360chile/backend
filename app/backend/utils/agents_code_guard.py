"""Bloquea HTML y código de programación en el chat de agentes."""

from __future__ import annotations

import re

CODE_REJECT_REPLY = (
    "No puedo aceptar HTML ni código de programación en este chat. "
    "Los agentes PIE360 solo trabajan con texto en lenguaje natural para informes. "
    "Reformula tu solicitud sin etiquetas HTML y sin código."
)

_HTML_TAG_RE = re.compile(
    r"</?(?:html|head|body|script|style|iframe|object|embed|svg|link|meta|form|"
    r"input|button|textarea|div|span|p|br|img|a|table|tr|td|ul|ol|li|h[1-6])"
    r"\b[^>]*>",
    re.IGNORECASE,
)
_DANGEROUS_HTML_RE = re.compile(
    r"<\s*(?:script|style|iframe|object|embed|svg|link)\b|javascript\s*:|on\w+\s*=\s*['\"]",
    re.IGNORECASE,
)
_CODE_FENCE_LANG_RE = re.compile(
    r"```\s*(html|xml|javascript|typescript|tsx|jsx|js|ts|python|py|php|sql|"
    r"css|java|c\+\+|cpp|c|go|rust|bash|sh|powershell|ruby|swift|kotlin)\b",
    re.IGNORECASE,
)
_CODE_PATTERN_RE = re.compile(
    r"(?:"
    r"<\?php"
    r"|#!/usr/bin"
    r"|\bfunction\s*\("
    r"|\bdef\s+[A-Za-z_]\w*\s*\("
    r"|\bclass\s+[A-Za-z_]\w*\s*[\{:]"
    r"|\bimport\s+(?:[\w\{]|requests|os|sys|java)"
    r"|\bfrom\s+\w+\s+import\b"
    r"|\bconsole\.log\s*\("
    r"|\bdocument\.(?:write|querySelector|getElementById)\s*\("
    r"|\beval\s*\("
    r"|\bSELECT\s+.+\s+FROM\b"
    r"|\bDROP\s+TABLE\b"
    r"|\bINSERT\s+INTO\b"
    r"|\bconst\s+[A-Za-z_]\w*\s*="
    r"|\blet\s+[A-Za-z_]\w*\s*="
    r"|=>\s*\{"
    r"|public\s+static\s+void"
    r"|#include\s*<"
    r")"
    r"|<\?php",
    re.IGNORECASE | re.DOTALL,
)


def message_is_html_or_code(text: str) -> bool:
    """True si el mensaje del usuario trae HTML o código (no lenguaje natural)."""
    raw = text or ""
    if not raw.strip():
        return False
    if _DANGEROUS_HTML_RE.search(raw):
        return True
    if len(_HTML_TAG_RE.findall(raw)) >= 2:
        return True
    if _HTML_TAG_RE.search(raw) and ("</" in raw or "/>" in raw):
        return True
    if _CODE_FENCE_LANG_RE.search(raw):
        return True
    if _CODE_PATTERN_RE.search(raw):
        return True
    return False


_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_FENCE_RE = re.compile(r"```[\w+-]*\n?[\s\S]*?```", re.IGNORECASE)


def strip_html_tags(text: str) -> str:
    return _TAG_RE.sub("", text or "")


def strip_html_and_code_blocks(text: str) -> str:
    """Quita etiquetas HTML y bloques de código del texto visible del chat."""
    cleaned = _FENCE_RE.sub("", text or "")
    cleaned = strip_html_tags(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
