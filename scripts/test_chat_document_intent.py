"""Prueba: no regenerar Word en cada turno del chat."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.utils.agents_chat_context import wants_document_generation

HISTORY_WITH_GENERATE = [
    {"role": "user", "content": "genera el informe de familia para isabella"},
    {
        "role": "assistant",
        "content": "Listo, generé el informe Word. Puedes descargarlo.",
    },
]


def main() -> int:
    cases = [
        ("genera el informe de familia", True),
        ("Generar el documento por favor", True),
        ("genera informe isabella", True),
        ("realiza el informe de familia", True),
        ("realizar el informe para isabella", True),
        ("elabora el documento por favor", True),
        ("completa el informe", True),
        ("prepara el word", True),
        ("gracias", False),
        ("ok", False),
        ("¿qué datos faltan del apoderado?", False),
        ("cuéntame del informe de familia", False),
        ("el informe de isabella tiene el rut correcto?", False),
    ]

    failed = 0
    for message, expected in cases:
        got = wants_document_generation(message, HISTORY_WITH_GENERATE)
        status = "OK" if got == expected else "FALLO"
        if got != expected:
            failed += 1
        print(f"{status}: {message!r} -> {got} (esperado {expected})")

    # Historial con petición previa no debe forzar generación en mensaje de cierre
    if wants_document_generation("perfecto, gracias", HISTORY_WITH_GENERATE):
        print("FALLO: historial previo disparó generación en mensaje de cierre")
        failed += 1
    else:
        print("OK: mensaje de cierre sin regenerar pese a historial")

    if failed:
        print(f"\n{failed} prueba(s) fallaron")
        return 1
    print("\nTodas las pruebas pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
