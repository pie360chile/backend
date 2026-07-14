"""Catálogo de modelos LLM para Agentes (modelo activo global en la web)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.backend.db.models.agent import AgentModel
from app.backend.db.models.agents_app_settings import AgentsAppSettingModel
from app.backend.db.models.agents_openai_models import AgentsOpenAIModel

# Catálogo: un solo modelo activo para todos los agentes.
_DEFAULT_MODEL_CODE = "deepseek-chat"
_DEFAULT_MODEL_NAME = "DeepSeek-V3.2"

_SEED_MODELS: list[dict[str, Any]] = [
    {
        "model_code": _DEFAULT_MODEL_CODE,
        "display_name": _DEFAULT_MODEL_NAME,
        "input_per_1m_usd": Decimal("0.280000"),
        "output_per_1m_usd": Decimal("0.420000"),
        "cached_input_per_1m_usd": Decimal("0.028000"),
        "sort_order": 10,
        "is_selected": True,
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_model(row: AgentsOpenAIModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "model_code": row.model_code,
        "display_name": row.display_name,
        "input_per_1m_usd": float(row.input_per_1m_usd or 0),
        "output_per_1m_usd": float(row.output_per_1m_usd or 0),
        "cached_input_per_1m_usd": (
            float(row.cached_input_per_1m_usd) if row.cached_input_per_1m_usd is not None else None
        ),
        "sort_order": row.sort_order,
        "is_selected": bool(row.is_selected),
        "is_active": bool(row.is_active),
    }


class AgentsLlmModelsClass:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_seeded(self) -> None:
        now = _now()
        existing = {m.model_code: m for m in self.db.query(AgentsOpenAIModel).all()}
        for spec in _SEED_MODELS:
            row = existing.get(spec["model_code"])
            if row is None:
                self.db.add(
                    AgentsOpenAIModel(
                        model_code=spec["model_code"],
                        display_name=spec["display_name"],
                        input_per_1m_usd=spec["input_per_1m_usd"],
                        output_per_1m_usd=spec["output_per_1m_usd"],
                        cached_input_per_1m_usd=spec["cached_input_per_1m_usd"],
                        sort_order=spec["sort_order"],
                        is_selected=bool(spec["is_selected"]),
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                row.display_name = spec["display_name"]
                row.input_per_1m_usd = spec["input_per_1m_usd"]
                row.output_per_1m_usd = spec["output_per_1m_usd"]
                row.cached_input_per_1m_usd = spec["cached_input_per_1m_usd"]
                row.sort_order = spec["sort_order"]
                row.is_active = True
                row.updated_at = now

        self.db.flush()
        # Solo el modelo por defecto activo y seleccionado; el resto queda inactivo.
        default_row = (
            self.db.query(AgentsOpenAIModel)
            .filter(AgentsOpenAIModel.model_code == _DEFAULT_MODEL_CODE)
            .first()
        )
        for m in self.db.query(AgentsOpenAIModel).all():
            is_default = default_row is not None and m.id == default_row.id
            m.is_active = is_default
            m.is_selected = is_default
            if is_default:
                m.display_name = _DEFAULT_MODEL_NAME
            m.updated_at = now

        self._ensure_app_settings_row()
        self.db.commit()

    def force_select_default_model(self) -> None:
        """Usado por la migración: deja el modelo por defecto como único global."""
        self.ensure_seeded()

    def _ensure_app_settings_row(self) -> AgentsAppSettingModel:
        row = self.db.query(AgentsAppSettingModel).filter(AgentsAppSettingModel.id == 1).first()
        if row:
            return row
        now = _now()
        row = AgentsAppSettingModel(
            id=1,
            default_agent_id=None,
            llm_api_key=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_workspace_access_token(self) -> str:
        """Token Workspace ChatGPT: primero BD (Configuraciones), luego AGENT_ACCESS_TOKEN."""
        app = self._ensure_app_settings_row()
        key = (app.llm_api_key or "").strip()
        if key:
            return key
        from app.backend.core.config import settings

        return (settings.agent_access_token or "").strip()

    def get_llm_api_key(self) -> str:
        """Compat: misma clave usada ahora como token Workspace."""
        return self.get_workspace_access_token()

    def get_selected_model_code(self) -> str:
        return "workspace-chatgpt"

    def get_settings(self, *, customer_id: int | None = None) -> dict[str, Any]:
        self.ensure_seeded()
        from app.backend.core.config import settings

        models = (
            self.db.query(AgentsOpenAIModel)
            .filter(AgentsOpenAIModel.is_active.is_(True))
            .order_by(AgentsOpenAIModel.sort_order.asc(), AgentsOpenAIModel.id.asc())
            .all()
        )
        app = self._ensure_app_settings_row()
        agents_q = self.db.query(AgentModel)
        if customer_id is not None:
            agents_q = agents_q.filter(AgentModel.customer_id == customer_id)
        agents = agents_q.order_by(AgentModel.name.asc()).all()
        stored_key = (app.llm_api_key or "").strip()
        base = (settings.workspace_agent_api_base or "").rstrip("/")
        agent_id = (settings.workspace_agent_id or "").strip()
        trigger_url = f"{base}/{agent_id}/trigger" if base and agent_id else ""
        sa_raw = (getattr(app, "google_service_account_json", None) or "").strip()
        from app.backend.utils.school_drive_config import _service_account_info_from_env_file

        env_sa = _service_account_info_from_env_file()
        creds_ok = bool(sa_raw) or bool(env_sa)
        creds_hint = None
        if env_sa and env_sa.get("client_email"):
            creds_hint = str(env_sa.get("client_email"))
        elif sa_raw:
            try:
                import json

                email = str(json.loads(sa_raw).get("client_email") or "").strip()
                creds_hint = email or "Credenciales en BD"
            except Exception:
                creds_hint = "Credenciales en BD"
        root_id = (getattr(app, "google_drive_root_folder_id", None) or "").strip() or None
        return {
            "selected_model_code": "workspace-chatgpt",
            "default_agent_id": app.default_agent_id,
            "has_llm_api_key": bool(stored_key),
            "llm_api_key_hint": (f"****{stored_key[-4:]}" if len(stored_key) >= 4 else None),
            "llm_api_key_value": stored_key or None,
            "workspace_agent_id": agent_id or None,
            "workspace_trigger_url": trigger_url or None,
            "provider": "workspace-chatgpt",
            "google_drive_root_folder_id": root_id,
            "has_google_drive_credentials": creds_ok,
            "google_drive_credentials_hint": creds_hint,
            "models": [_serialize_model(m) for m in models],
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "customer_id": a.customer_id,
                }
                for a in agents
            ],
        }

    def update_settings(
        self,
        *,
        selected_model_code: str | None = None,
        selected_model_name: str | None = None,
        default_agent_id: str | None = None,
        clear_default_agent: bool = False,
        llm_api_key: str | None = None,
        clear_llm_api_key: bool = False,
        google_drive_root_folder_id: str | None = None,
        google_service_account_json: str | None = None,
        clear_google_drive: bool = False,
    ) -> dict[str, Any]:
        self.ensure_seeded()
        now = _now()

        if selected_model_code is not None:
            code = selected_model_code.strip()
            if not code:
                return {"status": "error", "message": "Indica el código del modelo."}
            name = (selected_model_name or "").strip() or code
            target = (
                self.db.query(AgentsOpenAIModel)
                .filter(AgentsOpenAIModel.model_code == code)
                .first()
            )
            if not target:
                target = AgentsOpenAIModel(
                    model_code=code,
                    display_name=name,
                    input_per_1m_usd=Decimal("0"),
                    output_per_1m_usd=Decimal("0"),
                    cached_input_per_1m_usd=None,
                    sort_order=0,
                    is_selected=True,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(target)
                self.db.flush()
            else:
                target.display_name = name
                target.is_active = True
                target.updated_at = now

            for m in self.db.query(AgentsOpenAIModel).all():
                m.is_selected = m.id == target.id
                m.updated_at = now

        app = self._ensure_app_settings_row()
        if clear_default_agent:
            app.default_agent_id = None
            app.updated_at = now
        elif default_agent_id is not None:
            aid = default_agent_id.strip()
            if not aid:
                app.default_agent_id = None
            else:
                agent = self.db.query(AgentModel).filter(AgentModel.id == aid).first()
                if not agent:
                    return {"status": "error", "message": f"Agente no encontrado: {aid}"}
                app.default_agent_id = aid
            app.updated_at = now

        if clear_llm_api_key:
            app.llm_api_key = None
            app.updated_at = now
        elif llm_api_key is not None:
            key = llm_api_key.strip()
            if key:
                app.llm_api_key = key
                app.updated_at = now

        if clear_google_drive:
            app.google_drive_root_folder_id = None
            app.google_service_account_json = None
            app.updated_at = now
        else:
            if google_drive_root_folder_id is not None:
                root = google_drive_root_folder_id.strip()
                app.google_drive_root_folder_id = root or None
                app.updated_at = now
            if google_service_account_json is not None:
                raw = google_service_account_json.strip()
                if raw:
                    try:
                        from app.backend.utils.school_drive_config import _parse_service_account_json

                        _parse_service_account_json(raw)
                    except ValueError as exc:
                        return {"status": "error", "message": str(exc)}
                    app.google_service_account_json = raw
                    app.updated_at = now

        self.db.commit()
        return {
            "status": "success",
            "message": "Configuración de Agentes guardada.",
            "data": self.get_settings(),
        }
