"""Authz + rate limits for agents chat (no public OpenAI proxy)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models import RolModel
from app.backend.db.models.agents_usage import (
    AgentsRateLimitHitModel,
    AgentsTokenUsageModel,
)


def can_use_agents_chat(session_user: Any, db: Session) -> bool:
    """Superadmin, coordinador o evaluador (alineado al frontend)."""
    rid = int(getattr(session_user, "rol_id", 0) or 0)
    if rid == 1:
        return True
    if not getattr(session_user, "rol_id", None):
        return False
    rol = db.query(RolModel).filter(RolModel.id == session_user.rol_id).first()
    if not rol or not rol.rol:
        return False
    n = str(rol.rol).lower()
    return "coordinador" in n or "evaluador" in n


def _day_start_utc() -> datetime:
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class AgentsRateLimitClass:
    def __init__(self, db: Session):
        self.db = db

    def _purge_old_hits(self, older_than: datetime) -> None:
        (
            self.db.query(AgentsRateLimitHitModel)
            .filter(AgentsRateLimitHitModel.created_at < older_than)
            .delete(synchronize_session=False)
        )

    def _count_hits(
        self,
        *,
        since: datetime,
        user_id: int | None = None,
        customer_id: int | None = None,
        school_id: int | None = None,
    ) -> int:
        q = self.db.query(func.count(AgentsRateLimitHitModel.id)).filter(
            AgentsRateLimitHitModel.created_at >= since
        )
        if user_id is not None:
            q = q.filter(AgentsRateLimitHitModel.user_id == int(user_id))
        if customer_id is not None:
            q = q.filter(AgentsRateLimitHitModel.customer_id == int(customer_id))
        if school_id is not None:
            q = q.filter(AgentsRateLimitHitModel.school_id == int(school_id))
        return int(q.scalar() or 0)

    def _tokens_today(
        self,
        *,
        user_id: int | None = None,
        customer_id: int | None = None,
        school_id: int | None = None,
    ) -> int:
        q = self.db.query(
            func.coalesce(func.sum(AgentsTokenUsageModel.total_tokens), 0)
        ).filter(AgentsTokenUsageModel.created_at >= _day_start_utc())
        if user_id is not None:
            q = q.filter(AgentsTokenUsageModel.user_id == int(user_id))
        if customer_id is not None:
            q = q.filter(AgentsTokenUsageModel.customer_id == int(customer_id))
        if school_id is not None:
            q = q.filter(AgentsTokenUsageModel.school_id == int(school_id))
        return int(q.scalar() or 0)

    def check_and_register_chat(
        self,
        *,
        user_id: int | None,
        customer_id: int | None,
        school_id: int | None,
    ) -> dict[str, Any]:
        """
        Enforce requests/min and tokens/day for user and customer (and school if present).
        Registers a hit only when allowed.
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)
        req_user = max(1, int(settings.agents_rate_requests_per_min_user or 10))
        req_customer = max(1, int(settings.agents_rate_requests_per_min_customer or 30))
        tok_user = max(1000, int(settings.agents_rate_tokens_per_day_user or 200000))
        tok_customer = max(1000, int(settings.agents_rate_tokens_per_day_customer or 2000000))

        try:
            self._purge_old_hits(now - timedelta(minutes=10))

            if user_id:
                user_hits = self._count_hits(since=window_start, user_id=int(user_id))
                if user_hits >= req_user:
                    return {
                        "ok": False,
                        "code": "rate_limit_requests",
                        "message": (
                            f"Demasiadas solicitudes. Límite: {req_user} por minuto "
                            "por usuario. Espera un momento e inténtalo de nuevo."
                        ),
                    }
                user_tokens = self._tokens_today(user_id=int(user_id))
                if user_tokens >= tok_user:
                    return {
                        "ok": False,
                        "code": "rate_limit_tokens",
                        "message": (
                            f"Alcanzaste el límite diario de tokens por usuario "
                            f"({tok_user:,}). Intenta mañana o contacta al administrador."
                        ),
                    }

            if customer_id:
                cust_hits = self._count_hits(
                    since=window_start, customer_id=int(customer_id)
                )
                if cust_hits >= req_customer:
                    return {
                        "ok": False,
                        "code": "rate_limit_requests",
                        "message": (
                            f"Demasiadas solicitudes en este cliente. Límite: "
                            f"{req_customer} por minuto. Espera un momento."
                        ),
                    }
                cust_tokens = self._tokens_today(customer_id=int(customer_id))
                if cust_tokens >= tok_customer:
                    return {
                        "ok": False,
                        "code": "rate_limit_tokens",
                        "message": (
                            f"El cliente alcanzó el límite diario de tokens "
                            f"({tok_customer:,}). Intenta mañana o contacta al administrador."
                        ),
                    }

            if school_id and customer_id:
                # Soft school cap: same as customer requests/min if configured path is busy
                school_hits = self._count_hits(
                    since=window_start,
                    customer_id=int(customer_id),
                    school_id=int(school_id),
                )
                school_cap = max(req_user, min(req_customer, req_user * 3))
                if school_hits >= school_cap:
                    return {
                        "ok": False,
                        "code": "rate_limit_requests",
                        "message": (
                            f"Demasiadas solicitudes en este colegio. Límite: "
                            f"{school_cap} por minuto. Espera un momento."
                        ),
                    }

            self.db.add(
                AgentsRateLimitHitModel(
                    user_id=int(user_id) if user_id else None,
                    customer_id=int(customer_id) if customer_id else None,
                    school_id=int(school_id) if school_id else None,
                    created_at=now,
                )
            )
            self.db.commit()
            return {"ok": True, "code": None, "message": None}
        except Exception as exc:
            self.db.rollback()
            return {
                "ok": False,
                "code": "rate_limit_error",
                "message": f"No se pudo validar el rate limit: {exc}",
            }
