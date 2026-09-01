"""Worker periódico para la cola persistente de documentos en Google Drive."""

from __future__ import annotations

import asyncio
import logging

from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
from app.backend.db.database import SessionLocal


logger = logging.getLogger(__name__)


def drain_student_drive_sync_queue(batch_size: int = 10) -> int:
    processed = 0
    for _ in range(max(1, int(batch_size))):
        db = SessionLocal()
        try:
            service = StudentDriveSyncClass(db)
            job_id = service.claim_due_job()
            if job_id is None:
                break
            service.process(job_id)
            processed += 1
        except Exception:
            db.rollback()
            logger.exception(
                "No se pudo procesar la cola Drive; verifica que la migración 0017 esté aplicada."
            )
            break
        finally:
            db.close()
    return processed


async def run_student_drive_sync_worker(
    stop_event: asyncio.Event,
    *,
    interval_seconds: int = 60,
) -> None:
    while not stop_event.is_set():
        await asyncio.to_thread(drain_student_drive_sync_queue)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
