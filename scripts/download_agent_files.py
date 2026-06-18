"""Descarga archivos de un agente desde producción para pruebas locales."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AGENT_ID = "agent-1781746469526"
BASE_URL = "https://pie360backend.cl/api"
ROOT = Path(__file__).resolve().parents[1] / "files" / "agents" / AGENT_ID


def main() -> None:
    with urllib.request.urlopen(f"{BASE_URL}/agents/{AGENT_ID}", timeout=60) as response:
        agent_data = json.loads(response.read().decode())["data"]

    ROOT.mkdir(parents=True, exist_ok=True)
    for item in agent_data.get("files") or []:
        name = item.get("name") or ""
        upper = name.upper()
        if "ISABELLA" not in upper and "FAMILIA" not in upper and "FORMATO_INFORME" not in upper.replace(" ", "_"):
            continue
        file_id = item["id"]
        url = f"{BASE_URL}/agent-files/{AGENT_ID}/download/{urllib.parse.quote(file_id, safe='')}"
        print(f"Descargando {name} ...")
        with urllib.request.urlopen(url, timeout=120) as response:
            content = response.read()
        (ROOT / file_id).write_bytes(content)
        print(f"  OK {len(content)} bytes -> {file_id}")


if __name__ == "__main__":
    main()
