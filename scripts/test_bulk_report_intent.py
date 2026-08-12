"""Detección masivo vs uno a uno (RUT) en el chat de agentes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.utils.agents_bulk_reports import looks_like_bulk_request

ASK_HISTORY = [
    {
        "role": "assistant",
        "content": (
            "Para continuar con los informes del curso de **Liceo Mixto**. "
            "Indica el **año** y el **curso**."
        ),
    }
]


def main() -> int:
    cases: list[tuple[str, list | None, bool]] = [
        ("haz el informe de isabella diaz", None, False),
        ("genera el informe psicopedagógico de 12.345.678-9", None, False),
        ("realiza el informe a la familia", None, False),
        ("Dame los informes a la familia del Liceo Mixto Los Andes Media", None, True),
        ("informes psicopedagógicos del colegio San José", None, True),
        ("necesito los informes del curso 1 medio A", None, True),
        ("1 medio A 2026", ASK_HISTORY, True),
        ("2026", ASK_HISTORY, True),
        ("sí", ASK_HISTORY, True),
        ("ok gracias", None, False),
    ]
    failed = 0
    for message, history, expected in cases:
        got = looks_like_bulk_request(message, history)
        status = "OK" if got == expected else "FALLO"
        if got != expected:
            failed += 1
        print(f"{status}: {message!r} -> {got} (esperado {expected})")
    if failed:
        print(f"\n{failed} prueba(s) fallaron")
        return 1
    print("\nTodas las pruebas pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
