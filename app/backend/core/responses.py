"""Respuestas HTTP estándar del API PIE 360."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import status
from fastapi.responses import JSONResponse


def api_response(
    *,
    status_code: int = status.HTTP_200_OK,
    message: str = "OK",
    data: Any = None,
) -> JSONResponse:
    """Envelope `{ status, message, data }` consumido por el admin-frontend."""
    return JSONResponse(
        status_code=status_code,
        content={"status": status_code, "message": message, "data": data},
    )


def api_error(
    *,
    status_code: int,
    message: str,
    data: Optional[Any] = None,
) -> JSONResponse:
    return api_response(status_code=status_code, message=message, data=data)
