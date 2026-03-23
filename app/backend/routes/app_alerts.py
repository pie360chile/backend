"""API tabla `alerts`: listar, contar no leídas, marcar revisada, backfill desde asignaciones."""

from typing import Optional, Set, Tuple

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.app_alert_class import AppAlertClass
from app.backend.db.database import get_db
from app.backend.db.models import ProfessionalDocumentAssignmentModel
from app.backend.schemas import UserLogin

alerts = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts.get("/unread-count")
def alerts_unread_count(
    professional_id: int = Query(..., description="ID del profesional"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    svc = AppAlertClass(db)
    result = svc.count_unread(professional_id)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": result.get("message", "Error"), "data": {"count": 0}},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "OK",
            "data": {"count": int(result.get("count", 0))},
        },
    )


@alerts.post("/mark-all-reviewed")
def mark_all_alerts_reviewed(
    professional_id: int = Query(..., description="Profesional dueño de las alertas"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Marca todas las alertas pendientes como revisadas (al abrir el panel de la campana)."""
    svc = AppAlertClass(db)
    result = svc.mark_all_reviewed_for_professional(professional_id)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": result.get("message", "Error")},
        )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "OK",
            "data": {"updated": int(result.get("updated", 0))},
        },
    )


@alerts.get("")
def list_alerts(
    professional_id: int = Query(...),
    status_id: Optional[int] = Query(None, description="Filtrar: 0 pendiente, 1 revisada"),
    limit: int = Query(100, ge=1, le=500),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    svc = AppAlertClass(db)
    result = svc.list_alerts(professional_id=professional_id, status_id=status_id, limit=limit)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": result.get("message", "Error"), "data": []},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": result.get("data", [])},
    )


@alerts.patch("/{alert_id}/reviewed")
def mark_alert_reviewed(
    alert_id: int,
    professional_id: int = Query(..., description="Debe coincidir con el dueño de la alerta"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    svc = AppAlertClass(db)
    result = svc.mark_reviewed(alert_id, professional_id)
    if result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": result.get("message", "No encontrado")},
        )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": result.get("message", "OK")},
    )


@alerts.post("/backfill-from-assignments")
def backfill_alerts_from_assignments(
    professional_id: Optional[int] = Query(
        None,
        description="Si se omite, procesa todas las asignaciones pendientes (puede ser pesado)",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Sincroniza una alerta resumen por (período, curso, profesional) según asignaciones pendientes."""
    try:
        q = db.query(ProfessionalDocumentAssignmentModel).filter(
            ProfessionalDocumentAssignmentModel.status_id == 0
        )
        if professional_id is not None:
            q = q.filter(ProfessionalDocumentAssignmentModel.professional_id == int(professional_id))
        rows = q.all()
        svc = AppAlertClass(db)
        seen: Set[Tuple[int, int, int]] = set()
        for row in rows:
            key = (int(row.period_year), int(row.course_id), int(row.professional_id))
            if key in seen:
                continue
            seen.add(key)
            svc.sync_scope_summary_from_assignments(
                period_year=key[0],
                course_id=key[1],
                professional_id=key[2],
            )
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": 200,
                "message": "OK",
                "data": {
                    "scopes_synced": len(seen),
                    "pending_assignment_rows": len(rows),
                },
            },
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": str(e)},
        )
