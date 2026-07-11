"""Token usage persistence and summaries for agents (per customer)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.core.config import settings
from app.backend.db.models.agents_usage import AgentsTokenUsageModel
from app.backend.db.models.pie_core import CustomerModel
from app.backend.utils.agents_pricing import estimate_cost_usd, pricing_for_model


class AgentsUsageClass:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        customer_id: int | None,
        school_id: int | None,
        user_id: int | None,
        agent_id: str | None,
        request_kind: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int | None = None,
    ) -> AgentsTokenUsageModel | None:
        if not customer_id:
            return None
        prompt = max(0, int(prompt_tokens or 0))
        completion = max(0, int(completion_tokens or 0))
        total = int(total_tokens) if total_tokens is not None else prompt + completion
        cost = estimate_cost_usd(prompt, completion, model)
        row = AgentsTokenUsageModel(
            customer_id=int(customer_id),
            school_id=int(school_id) if school_id else None,
            user_id=int(user_id) if user_id else None,
            agent_id=agent_id,
            request_kind=request_kind,
            model=model or settings.agents_model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            estimated_cost_usd=Decimal(str(round(cost, 6))),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _pricing_payload(self) -> dict[str, Any]:
        pricing = pricing_for_model(settings.agents_model)
        return {
            "input_per_1m_usd": pricing.input_per_1m_usd,
            "output_per_1m_usd": pricing.output_per_1m_usd,
            "cached_input_per_1m_usd": pricing.cached_input_per_1m_usd,
        }

    def summary_for_customer(self, customer_id: int) -> dict[str, Any]:
        q = (
            self.db.query(
                func.coalesce(func.sum(AgentsTokenUsageModel.prompt_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.completion_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.total_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.estimated_cost_usd), 0),
                func.count(AgentsTokenUsageModel.id),
            )
            .filter(AgentsTokenUsageModel.customer_id == customer_id)
            .one()
        )
        return {
            "customer_id": customer_id,
            "model": settings.agents_model,
            "prompt_tokens": int(q[0] or 0),
            "completion_tokens": int(q[1] or 0),
            "total_tokens": int(q[2] or 0),
            "estimated_cost_usd": round(float(q[3] or 0), 6),
            "request_count": int(q[4] or 0),
            "pricing": self._pricing_payload(),
        }

    def summary_by_customer(self) -> dict[str, Any]:
        """Superadmin control panel: usage grouped by client."""
        rows = (
            self.db.query(
                AgentsTokenUsageModel.customer_id,
                func.coalesce(func.sum(AgentsTokenUsageModel.prompt_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.completion_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.total_tokens), 0),
                func.coalesce(func.sum(AgentsTokenUsageModel.estimated_cost_usd), 0),
                func.count(AgentsTokenUsageModel.id),
            )
            .group_by(AgentsTokenUsageModel.customer_id)
            .order_by(func.sum(AgentsTokenUsageModel.estimated_cost_usd).desc())
            .all()
        )

        customer_ids = [int(r[0]) for r in rows if r[0] is not None]
        names: dict[int, str] = {}
        if customer_ids:
            customers = (
                self.db.query(CustomerModel)
                .filter(CustomerModel.id.in_(customer_ids))
                .all()
            )
            for c in customers:
                label = (c.company_name or "").strip()
                if not label:
                    label = " ".join(
                        part
                        for part in [(c.names or "").strip(), (c.lastnames or "").strip()]
                        if part
                    ).strip()
                names[int(c.id)] = label or f"Customer {c.id}"

        clients = []
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        total_cost = 0.0
        total_requests = 0
        for row in rows:
            cid = int(row[0])
            prompt = int(row[1] or 0)
            completion = int(row[2] or 0)
            tokens = int(row[3] or 0)
            cost = float(row[4] or 0)
            requests = int(row[5] or 0)
            total_prompt += prompt
            total_completion += completion
            total_tokens += tokens
            total_cost += cost
            total_requests += requests
            clients.append(
                {
                    "customer_id": cid,
                    "customer_name": names.get(cid, f"Customer {cid}"),
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "total_tokens": tokens,
                    "estimated_cost_usd": round(cost, 6),
                    "request_count": requests,
                }
            )

        return {
            "model": settings.agents_model,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "request_count": total_requests,
            "pricing": self._pricing_payload(),
            "clients": clients,
        }
