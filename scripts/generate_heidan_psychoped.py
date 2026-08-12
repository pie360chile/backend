"""Genera el Informe Psicopedagógico (doc 27) de Heidan Mauna."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.classes.agents_chat_class import AgentsChatClass
from app.backend.classes.agents_class import AgentsClass
from app.backend.classes.agents_llm_models_class import AgentsLlmModelsClass
from app.backend.db.database import SessionLocal

AGENT_ID = "5d8e556263d14ca183b7da1639c1b9fb"
CUSTOMER_ID = 2
SCHOOL_ID = 5
PERIOD_YEAR = 2026
STUDENT_ID = 1593
DOCUMENT_ID = 27


def main() -> None:
    db = SessionLocal()
    try:
        agent = AgentsClass(db)._get_agent(AGENT_ID, CUSTOMER_ID)
        if not agent:
            raise SystemExit("agente no encontrado")
        name, rut = None, "22.820.618-0"
        from app.backend.classes.agents_chat_class import _load_student_name_rut

        name, rut_db = _load_student_name_rut(db, STUDENT_ID)
        rut = rut_db or rut
        model = AgentsLlmModelsClass(db).get_selected_model_code()
        chat = AgentsChatClass(
            db,
            customer_id=CUSTOMER_ID,
            school_id=SCHOOL_ID,
            period_year=PERIOD_YEAR,
        )
        print("generating", name, rut, "model", model, flush=True)
        result = chat._generate_one_bulk_document(
            agent_id=AGENT_ID,
            agent_row=agent,
            student_id=STUDENT_ID,
            student_name=name or "Heidan Emiliano Mauna Ramos",
            student_rut=rut,
            document_id=DOCUMENT_ID,
            label="Informe de Evaluación Psicopedagógica",
            model_code=model,
        )
        print(repr(result), flush=True)
        if not result.get("ok"):
            raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
