"""Prueba E2E del stream de chat de un agente."""

from __future__ import annotations

import json
import sys
import time
import urllib.request

AGENT_ID = "agent-1781746469526"
MESSAGE = "haz el informe la familia de isabella diaz"
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/api"


def main() -> int:
    url = f"{BASE_URL.rstrip('/')}/agents/{AGENT_ID}/chat/stream"
    payload = json.dumps({"message": MESSAGE, "topK": 5}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )

    print(f"POST {url}")
    print(f"Mensaje: {MESSAGE!r}\n")

    started = time.time()
    steps: list[str] = []
    heartbeats = 0
    text_parts: list[str] = []
    done_data: dict | None = None

    with urllib.request.urlopen(req, timeout=900) as response:
        buffer = ""
        while True:
            chunk = response.read(4096)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                for line in block.splitlines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    event = json.loads(raw)
                    etype = event.get("type")
                    if etype == "step":
                        msg = event.get("message", "")
                        steps.append(msg)
                        print(f"[step] {msg}")
                    elif etype == "heartbeat":
                        heartbeats += 1
                        if heartbeats == 1 or heartbeats % 5 == 0:
                            print(f"[heartbeat] x{heartbeats}")
                    elif etype == "text_delta":
                        text_parts.append(event.get("delta", ""))
                    elif etype == "done":
                        done_data = event.get("data") or {}
                    elif etype == "error":
                        print(f"[error] {event.get('message')}")
                        return 1

    elapsed = time.time() - started
    print(f"\n--- Resultado ({elapsed:.1f}s) ---")
    print("Pasos:", len(steps), "| Heartbeats:", heartbeats)
    if done_data:
        print("Reply:", (done_data.get("reply") or "")[:500])
        print("openaiFilesUsed:", done_data.get("openaiFilesUsed"))
        print("responseFiles:", done_data.get("responseFiles"))
        print("responseFilesWarning:", done_data.get("responseFilesWarning"))
        print("containerId:", done_data.get("containerId"))
        if done_data.get("responseFiles"):
            return 0
        return 2
    print("Sin evento done")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
