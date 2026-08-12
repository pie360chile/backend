"""Consumo de tokens LLM por consulta de agentes."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.db.models.agents_openai_models import AgentsOpenAIModel
from app.backend.db.models.agents_usage import AgentsTokenUsageModel
from app.backend.db.models.pie_core import CustomerModel


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    return start, end


def _estimate_cost_usd(
    *,
    model_code: str,
    prompt_tokens: int,
    completion_tokens: int,
    db: Session,
    prompt_cache_hit_tokens: int = 0,
    prompt_cache_miss_tokens: int = 0,
) -> Decimal:
    row = (
        db.query(AgentsOpenAIModel)
        .filter(AgentsOpenAIModel.model_code == model_code)
        .first()
    )
    # Default ≈ deepseek-v4-pro (cache miss / output) de la tabla pública DeepSeek
    in_price = Decimal(str(row.input_per_1m_usd)) if row else Decimal("0.435")
    out_price = Decimal(str(row.output_per_1m_usd)) if row else Decimal("0.870")
    cached_price = (
        Decimal(str(row.cached_input_per_1m_usd))
        if row and row.cached_input_per_1m_usd is not None
        else None
    )

    hit = max(0, int(prompt_cache_hit_tokens or 0))
    miss = max(0, int(prompt_cache_miss_tokens or 0))
    prompt = max(0, int(prompt_tokens or 0))
    if hit + miss <= 0 and prompt > 0:
        miss = prompt
    elif hit + miss > 0 and hit + miss != prompt and prompt > 0:
        # Preferir desglose del proveedor; ajustar miss al resto del prompt
        miss = max(0, prompt - hit)

    if cached_price is not None and (hit > 0 or miss > 0):
        input_cost = (Decimal(hit) / Decimal(1_000_000)) * cached_price + (
            Decimal(miss) / Decimal(1_000_000)
        ) * in_price
    else:
        input_cost = (Decimal(prompt) / Decimal(1_000_000)) * in_price

    cost = input_cost + (Decimal(completion_tokens) / Decimal(1_000_000)) * out_price
    return cost.quantize(Decimal("0.000001"))


def _clip(text: str | None, max_len: int = 20000) -> str | None:
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


class AgentsUsageClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_chat(
        self,
        *,
        customer_id: int,
        school_id: int | None,
        user_id: int | None,
        agent_id: str | None,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int | None = None,
        prompt_cache_hit_tokens: int = 0,
        prompt_cache_miss_tokens: int = 0,
        input_text: str | None = None,
        output_text: str | None = None,
    ) -> dict[str, Any]:
        pt = max(0, int(prompt_tokens or 0))
        ct = max(0, int(completion_tokens or 0))
        hit = max(0, int(prompt_cache_hit_tokens or 0))
        miss = max(0, int(prompt_cache_miss_tokens or 0))
        if hit + miss <= 0 and pt > 0:
            miss = pt
        elif pt > 0 and hit > 0 and miss <= 0:
            miss = max(0, pt - hit)
        tt = int(total_tokens) if total_tokens is not None else pt + ct
        cost = _estimate_cost_usd(
            model_code=model,
            prompt_tokens=pt,
            completion_tokens=ct,
            prompt_cache_hit_tokens=hit,
            prompt_cache_miss_tokens=miss,
            db=self.db,
        )
        row = AgentsTokenUsageModel(
            customer_id=int(customer_id),
            school_id=int(school_id) if school_id else None,
            user_id=int(user_id) if user_id else None,
            agent_id=agent_id,
            request_kind="chat",
            model=(model or "").strip() or "unknown",
            prompt_tokens=pt,
            prompt_cache_hit_tokens=hit,
            prompt_cache_miss_tokens=miss,
            completion_tokens=ct,
            total_tokens=tt,
            estimated_cost_usd=cost,
            input_text=_clip(input_text),
            output_text=_clip(output_text),
            created_at=_now(),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return {"status": "success", "id": row.id}

    def list_report(
        self,
        *,
        customer_id: int | None = None,
        day: date | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        page = max(1, int(page or 1))
        per_page = min(200, max(1, int(per_page or 50)))

        q = self.db.query(AgentsTokenUsageModel)
        if customer_id is not None and int(customer_id) > 0:
            q = q.filter(AgentsTokenUsageModel.customer_id == int(customer_id))
        if day is not None:
            start, end = _day_bounds(day)
            q = q.filter(
                AgentsTokenUsageModel.created_at >= start,
                AgentsTokenUsageModel.created_at <= end,
            )

        total_items = q.count()
        totals = q.with_entities(
            func.coalesce(func.sum(AgentsTokenUsageModel.prompt_tokens), 0),
            func.coalesce(func.sum(AgentsTokenUsageModel.completion_tokens), 0),
            func.coalesce(func.sum(AgentsTokenUsageModel.total_tokens), 0),
            func.coalesce(func.sum(AgentsTokenUsageModel.estimated_cost_usd), 0),
            func.coalesce(func.sum(AgentsTokenUsageModel.prompt_cache_hit_tokens), 0),
            func.coalesce(func.sum(AgentsTokenUsageModel.prompt_cache_miss_tokens), 0),
        ).one()

        rows = (
            q.order_by(AgentsTokenUsageModel.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        customer_ids = {int(r.customer_id) for r in rows if r.customer_id}
        names: dict[int, str] = {}
        if customer_ids:
            for c in (
                self.db.query(CustomerModel)
                .filter(CustomerModel.id.in_(list(customer_ids)))
                .all()
            ):
                label = (c.company_name or "").strip()
                if not label:
                    label = f"{(c.names or '').strip()} {(c.lastnames or '').strip()}".strip()
                names[int(c.id)] = label or f"Cliente {c.id}"

        items = []
        for r in rows:
            items.append(
                {
                    "id": r.id,
                    "customer_id": r.customer_id,
                    "customer_name": names.get(int(r.customer_id), f"Cliente {r.customer_id}"),
                    "school_id": r.school_id,
                    "user_id": r.user_id,
                    "agent_id": r.agent_id,
                    "request_kind": r.request_kind,
                    "model": r.model,
                    "prompt_tokens": r.prompt_tokens,
                    "prompt_cache_hit_tokens": int(
                        getattr(r, "prompt_cache_hit_tokens", 0) or 0
                    ),
                    "prompt_cache_miss_tokens": int(
                        getattr(r, "prompt_cache_miss_tokens", 0) or 0
                    ),
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                    "estimated_cost_usd": float(r.estimated_cost_usd or 0),
                    "input_text": r.input_text,
                    "output_text": r.output_text,
                    "created_at": r.created_at.isoformat(sep=" ", timespec="seconds")
                    if r.created_at
                    else None,
                }
            )

        total_pages = max(1, (total_items + per_page - 1) // per_page)
        return {
            "status": "success",
            "data": {
                "items": items,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "items_per_page": per_page,
                "summary": {
                    "prompt_tokens": int(totals[0] or 0),
                    "completion_tokens": int(totals[1] or 0),
                    "total_tokens": int(totals[2] or 0),
                    "estimated_cost_usd": float(totals[3] or 0),
                    "prompt_cache_hit_tokens": int(totals[4] or 0),
                    "prompt_cache_miss_tokens": int(totals[5] or 0),
                },
            },
        }
