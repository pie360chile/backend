"""
Router `/external_api`: Inspection API integration (configurable base URL).

Routes:
  GET  /external_api/inspection/status
  GET/POST /external_api/inspection/student  (?rut= or JSON {"rut"})
  GET/POST /external_api/student
  GET/POST /external_api/inspection/professional  — Inspection getDatosFuncionario (staff by RUT)
  GET/POST /external_api/professional

Env: INSPECTION_API_BASE_URL, INSPECTION_API_USERNAME, INSPECTION_API_PASSWORD
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.inspection_api_client import InspectionApiClient
from app.backend.schemas import UserLogin

external_api = APIRouter(
    prefix="/external_api",
    tags=["External API"],
)


class RutBody(BaseModel):
    rut: str
    anio: int | None = None


def _not_configured_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": 503,
            "message": "Inspection API not configured (INSPECTION_API_USERNAME / INSPECTION_API_PASSWORD)",
            "data": None,
        },
    )


def _json_from_inspection_result(result: dict) -> JSONResponse:
    http_ok = status.HTTP_200_OK if result.get("ok") else status.HTTP_502_BAD_GATEWAY
    return JSONResponse(
        status_code=http_ok,
        content={
            "status": 200 if result.get("ok") else 502,
            "message": result.get("message", "OK"),
            "data": result,
        },
    )


def _fetch_inspection_student_response(rut: str, anio: int | None = None) -> JSONResponse:
    client = InspectionApiClient()
    if not client.is_configured():
        return _not_configured_response()
    return _json_from_inspection_result(client.fetch_student_data(rut, anio))


def _fetch_inspection_professional_response(rut: str) -> JSONResponse:
    client = InspectionApiClient()
    if not client.is_configured():
        return _not_configured_response()
    return _json_from_inspection_result(client.fetch_professional_data(rut))


@external_api.get("/inspection/status")
def inspection_status(session_user: UserLogin = Depends(get_current_active_user)):
    """Whether Inspection credentials are set (no secrets)."""
    c = InspectionApiClient()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "OK",
            "data": {
                "configured": c.is_configured(),
                "base_url": c.base_url,
            },
        },
    )


@external_api.get("/inspection/student")
def inspection_student_get(
    rut: str = Query(..., description="Student RUT (with or without formatting)"),
    anio: int | None = Query(None, description="Año/período para consulta de inspección"),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Fetch student data from Inspection API (Bearer + remote student endpoint)."""
    return _fetch_inspection_student_response(rut, anio)


@external_api.post("/inspection/student")
def inspection_student_post(
    body: RutBody,
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Same as GET with JSON body: {\"rut\": \"12.345.678-9\"}."""
    return _fetch_inspection_student_response(body.rut, body.anio)


@external_api.get("/student")
def student_short_get(
    rut: str = Query(..., description="Student RUT (with or without formatting)"),
    anio: int | None = Query(None, description="Año/período para consulta de inspección"),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Short alias for GET /external_api/inspection/student."""
    return _fetch_inspection_student_response(rut, anio)


@external_api.post("/student")
def student_short_post(
    body: RutBody,
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Short alias for POST /external_api/inspection/student."""
    return _fetch_inspection_student_response(body.rut, body.anio)


@external_api.get("/inspection/professional")
def inspection_professional_get(
    rut: str = Query(..., description="Professional/staff RUT (with or without formatting)"),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Fetch staff/professional data from Inspection API (remote POST getDatosFuncionario)."""
    return _fetch_inspection_professional_response(rut)


@external_api.post("/inspection/professional")
def inspection_professional_post(
    body: RutBody,
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Same as GET with JSON body: {\"rut\": \"7.432.906-3\"}."""
    return _fetch_inspection_professional_response(body.rut)


@external_api.get("/professional")
def professional_short_get(
    rut: str = Query(..., description="Professional/staff RUT (with or without formatting)"),
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Short alias for GET /external_api/inspection/professional."""
    return _fetch_inspection_professional_response(rut)


@external_api.post("/professional")
def professional_short_post(
    body: RutBody,
    session_user: UserLogin = Depends(get_current_active_user),
):
    """Short alias for POST /external_api/inspection/professional."""
    return _fetch_inspection_professional_response(body.rut)
