from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from app.backend.db.database import Base


class AgentsTokenUsageModel(Base):
    """Consumo de tokens LLM por consulta (por cliente)."""

    __tablename__ = "agents_token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    school_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True)
    agent_id = Column(String(64), nullable=True)
    request_kind = Column(String(32), nullable=False, default="chat")
    model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    input_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)


class AgentsCustomerBudgetModel(Base):
    """Tope de gasto mensual estimado por cliente (+ margen % por imprecisión)."""

    __tablename__ = "agents_customer_budgets"
    __table_args__ = (
        UniqueConstraint("customer_id", name="uq_agents_customer_budgets_customer_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    monthly_budget_usd = Column(Numeric(12, 4), nullable=False, default=0)
    buffer_percent = Column(Numeric(5, 2), nullable=False, default=10)
    updated_at = Column(DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)


class AgentsBudgetReservationModel(Base):
    """Hold estimado mientras un chat/extract corre (uso paralelo sin pasarse del tope)."""

    __tablename__ = "agents_budget_reservations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    reservation_key = Column(String(64), nullable=False, unique=True)
    amount_usd = Column(Numeric(12, 6), nullable=False, default=0)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(), nullable=False, index=True)


class AgentsRateLimitHitModel(Base):
    """Intentos de chat para rate limit por minuto (usuario / cliente / colegio)."""

    __tablename__ = "agents_rate_limit_hits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    school_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow, index=True)


class AgentsOpenAICostSyncModel(Base):
    """Últimos syncs de reconciliación OpenAI Costs vs estimado PIE360."""

    __tablename__ = "agents_openai_cost_syncs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synced_at = Column(DateTime(), nullable=False, default=datetime.utcnow, index=True)
    month_start = Column(DateTime(), nullable=False, index=True)
    openai_cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    pie_cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    delta_usd = Column(Numeric(12, 6), nullable=False, default=0)
    adjustment_usd = Column(Numeric(12, 6), nullable=False, default=0)
    status = Column(String(32), nullable=False, default="ok")
    message = Column(String(512), nullable=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)


class AgentsBudgetAlertModel(Base):
    """Alertas 50/80/100% del tope mensual de Agents (admin / coord / evaluador)."""

    __tablename__ = "agents_budget_alerts"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "user_id",
            "month_start",
            "threshold_percent",
            name="uq_agents_budget_alerts_user_month_threshold",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    month_start = Column(DateTime(), nullable=False)
    threshold_percent = Column(Integer, nullable=False)
    spent_usd = Column(Numeric(12, 6), nullable=False, default=0)
    budget_usd = Column(Numeric(12, 4), nullable=False, default=0)
    title = Column(String(255), nullable=False)
    message = Column(String(1024), nullable=False)
    status_id = Column(Integer, nullable=False, default=0)  # 0 pendiente, 1 revisada
    email_sent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(), nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime(), nullable=True)
