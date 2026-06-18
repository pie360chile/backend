"""Factory genérico para evaluaciones pedagógicas docente de aula (docs 31–42)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Sequence, Type

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin


def _parse_date(val):
    if val is None or val == "":
        return None
    if hasattr(val, "isoformat"):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


class PedagogicalEvaluationClassroomService:
    """Servicio CRUD parametrizado por modelo SQLAlchemy y columnas."""

    def __init__(
        self,
        db: Session,
        *,
        model: Type,
        field_names: Sequence[str],
        default_document_type_id: int,
    ):
        self.db = db
        self.model = model
        self.field_names = list(field_names)
        self.default_document_type_id = default_document_type_id
        self._date_fields = {"student_born_date", "report_date"}

    def _row_to_dict(self, row) -> dict:
        out = {"id": row.id, "student_id": row.student_id, "document_type_id": row.document_type_id}
        for name in self.field_names:
            if name in ("student_id", "document_type_id"):
                continue
            val = getattr(row, name, None)
            if val is not None and name in self._date_fields and hasattr(val, "isoformat"):
                val = val.isoformat()
            out[name] = val
        return out

    def _payload_to_row_values(self, payload: dict) -> dict:
        data = {}
        for name in self.field_names:
            if name not in payload:
                continue
            val = payload.get(name)
            if name in self._date_fields:
                val = _parse_date(val)
            data[name] = val
        return data

    def get(self, id: int) -> Any:
        try:
            row = self.db.query(self.model).filter(self.model.id == id).first()
            if row:
                return self._row_to_dict(row)
            return {"status": "error", "message": "Informe no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            row = (
                self.db.query(self.model)
                .filter(self.model.student_id == student_id)
                .order_by(self.model.id.desc())
                .first()
            )
            if row:
                return self._row_to_dict(row)
            return {"status": "error", "message": "No hay informe para este estudiante."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, payload: dict) -> Any:
        try:
            data = self._payload_to_row_values(payload)
            student_id = data.get("student_id") or payload.get("student_id")
            document_type_id = (
                data.get("document_type_id")
                if data.get("document_type_id") is not None
                else payload.get("document_type_id", self.default_document_type_id)
            )
            if not student_id:
                return {"status": "error", "message": "Falta student_id."}
            data["student_id"] = student_id
            data["document_type_id"] = document_type_id
            row = self.model(**{k: v for k, v in data.items() if k in self.field_names})
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe guardado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, payload: dict) -> Any:
        try:
            row = self.db.query(self.model).filter(self.model.id == id).first()
            if not row:
                return {"status": "error", "message": "Informe no encontrado."}
            data = self._payload_to_row_values(payload)
            for name, value in data.items():
                if name in ("student_id", "document_type_id") and value is None:
                    continue
                if hasattr(row, name):
                    setattr(row, name, value)
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Informe actualizado.", "id": row.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}


def build_pedagogical_evaluation_router(
    *,
    prefix: str,
    tag: str,
    model: Type,
    field_names: Iterable[str],
    default_document_type_id: int,
    store_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])
    fields = list(field_names)

    def _service(db: Session) -> PedagogicalEvaluationClassroomService:
        return PedagogicalEvaluationClassroomService(
            db,
            model=model,
            field_names=fields,
            default_document_type_id=default_document_type_id,
        )

    @router.get("/student/{student_id}")
    async def get_by_student(
        student_id: int,
        session_user: UserLogin = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        try:
            result = _service(db).get_by_student_id(student_id)
            if isinstance(result, dict) and result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"status": 404, "message": result.get("message", "Informe no encontrado."), "data": None},
                )
            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": result})
        except Exception as e:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})

    @router.post("/store")
    async def store(
        data: store_schema,
        session_user: UserLogin = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        try:
            result = _service(db).store(data.dict())
            if isinstance(result, dict) and result.get("status") == "error":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"status": 500, "message": result.get("message", "Error guardando informe."), "data": None},
                )
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={"status": 201, "message": result.get("message", "Informe guardado."), "data": {"id": result.get("id")}},
            )
        except Exception as e:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e), "data": None})

    @router.put("/{id}")
    async def update(
        id: int,
        data: update_schema,
        session_user: UserLogin = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        try:
            result = _service(db).update(id, data.dict(exclude_unset=True))
            if isinstance(result, dict) and result.get("status") == "error":
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"status": 404, "message": result.get("message", "Informe no encontrado.")})
            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": result.get("message", "OK")})
        except Exception as e:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": 500, "message": str(e)})

    return router
