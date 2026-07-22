# MCP Agentes PIE360

URL pública: `{API_PUBLIC_BASE}/mcp`  
Auth: `secret` = `MCP_SECRET` (o Bearer / `X-MCP-Secret` en REST).

## Estructura

```
app/backend/mcp/
├── auth.py / server.py
└── tools/
    ├── create_document.py   # genera Word + carpeta estudiante + ficha
    ├── store_data.py
    └── search_agent_files.py
```

Negocio: `classes/agents_mcp_class.py`  
Generación física: `classes/agents_document_service.py` (`generate_and_save_document`)  
Chat auto: `classes/agents_chat_class.py`

## Asociación Documentos (importante)

En el agente, **Documentos**:

1. Se elige un **tipo de documento** del catálogo PIE360 (`document_id`).
2. Se sube el **modelo/plantilla** (.docx/.pdf) para ese tipo.
3. Ese mismo `document_id` es el del **formulario** que se rellena al generar.

`create_document(document_id=…)` usa exactamente esa plantilla y actualiza ese formulario
(ej. familia → `family_reports`). Sin plantilla para ese `document_id` → error claro.


## Tools

| Tool | REST |
|------|------|
| `create_document` | `POST /api/agents/mcp/create_document` |
| `store_data` | `POST /api/agents/mcp/store_data` |
| `search_agent_files` | `POST /api/agents/mcp/search_files` |

## Qué se eliminó (legado)

- Generación directa OpenAI en el chat (sin MCP)
- Trigger Workspace ChatGPT (`/workspace-agent/chat`)
- Tool `save_agent_analisis_json` + validación de análisis
- Subida local `files/agents` vía MCP upload token
