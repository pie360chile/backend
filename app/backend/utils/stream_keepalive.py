"""Emite heartbeats mientras un generador bloqueante tarda en producir eventos."""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterator
from typing import Any


def iter_with_keepalive(
    source: Iterator[dict[str, Any]],
    *,
    interval_seconds: float = 12.0,
    message: str = "Sigo trabajando en tu solicitud…",
) -> Iterator[dict[str, Any]]:
    event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

    def worker() -> None:
        try:
            for item in source:
                event_queue.put(("item", item))
        except Exception as exc:
            event_queue.put(("error", exc))
        finally:
            event_queue.put(("end", None))

    threading.Thread(target=worker, daemon=True).start()

    while True:
        try:
            kind, payload = event_queue.get(timeout=interval_seconds)
        except queue.Empty:
            yield {"type": "heartbeat", "message": message}
            continue

        if kind == "end":
            break
        if kind == "error":
            raise payload
        yield payload
