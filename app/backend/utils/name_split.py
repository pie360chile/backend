"""Parte nombre completo en nombre + apellidos (primera palabra / resto)."""


def split_full_name(full_name):
    fn = (full_name or "").strip()
    if not fn:
        return "", ""
    parts = fn.split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")
