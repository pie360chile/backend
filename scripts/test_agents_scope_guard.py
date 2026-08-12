"""Los agentes solo atienden consultas de PIE Chile."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.utils.agents_scope_guard import message_is_off_topic

CASES: list[tuple[str, bool]] = [
    ("haz el informe psicopedagógico de Simón González", False),
    ("genera el informe a la familia de 23.012.603-8", False),
    ("Stefany Barraza", False),
    ("23.497.351-7", False),
    ("hola", False),
    ("sí", False),
    ("gracias", False),
    ("cuestionario de observación en aula", False),
    ("reescribe los campos narrativos", False),
    ("informes del curso 2F", False),
    ("qué es el decreto 170", False),
    ("qué receta de empanadas me recomiendas", True),
    ("cómo está el clima en Santiago", True),
    ("quién ganó el partido de fútbol", True),
    ("escríbeme un poema", True),
    ("hazme un poema", True),
    ("traduce esto al inglés", True),
    ("capital de Francia", True),
    ("explícame qué es bitcoin", True),
    ("receta de pie de limón", True),
    ("consulta del PIE Chile", False),
    ("1 medio A 2026", False),
    ("2F", False),
]


def main() -> int:
    failed = 0
    for message, expected in CASES:
        got = message_is_off_topic(message)
        if got != expected:
            failed += 1
            print(f"FAIL: {message!r} off_topic={got} expected={expected}")
        else:
            print(f"ok: {message!r} off_topic={got}")
    if failed:
        print(f"{failed} failed")
        return 1
    print("all ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
