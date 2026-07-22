"""Regenera textos derivados (_derived/) de archivos de agentes.

Uso:
  python scripts/rebuild_agent_derived.py --customer-id 1 --agent-name mi_agente
  python scripts/rebuild_agent_derived.py --customer-id 1 --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.db.database import SessionLocal
from app.backend.db.models.agent import AgentModel
from app.backend.utils import agents_derived_storage as derived


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild agent derived text files")
    parser.add_argument("--customer-id", type=int, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent-name", type=str, help="Nombre del agente")
    group.add_argument("--all", action="store_true", help="Todos los agentes del customer")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(AgentModel).filter(AgentModel.customer_id == int(args.customer_id))
        if args.agent_name:
            q = q.filter(AgentModel.name == args.agent_name.strip())
        agents = q.all()
        if not agents:
            print("No se encontraron agentes.")
            return 1

        total_ok = 0
        total_err = 0
        for agent in agents:
            name = (agent.name or "").strip()
            if not name:
                continue
            print(f"== {name} ==")
            result = derived.rebuild_all_derived(name, int(args.customer_id))
            ok = int(result.get("derivedOk") or 0)
            errs = result.get("derivedErrors") or []
            total_ok += ok
            total_err += len(errs)
            print(
                f"  processed={result.get('processed')} derivedOk={ok} errors={len(errs)}"
            )
            for err in errs[:20]:
                print(f"  - {err}")
            if len(errs) > 20:
                print(f"  … y {len(errs) - 20} más")

        print(f"Done. derivedOk={total_ok} errors={total_err}")
        return 0 if total_err == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
