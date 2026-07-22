from app.backend.utils.agents_mcp_fields import (
    extract_fields_from_reply,
    strip_fields_json_from_reply,
)
from app.backend.classes.agents_mcp_class import AgentsMcpClass

sample = 'Listo el informe.\n```json\n{"fields": {"diagnostico": "texto"}}\n```'
print(extract_fields_from_reply(sample))
print(repr(strip_fields_json_from_reply(sample)))
assert hasattr(AgentsMcpClass, "create_document")
print("ok")
