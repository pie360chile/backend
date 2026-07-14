# MCP Agentes — store_data (ChatGPT Workspace)

Cómo conectar ChatGPT al MCP de PIE360 y usar `store_data` para generar documentos desde el chat de Agentes.

## URL y autenticación

| Dato | Valor |
|------|--------|
| URL MCP | `{API_PUBLIC_BASE}/mcp` — p. ej. `https://pie360backend.cl/api/mcp` |
| Secret | Variable de entorno `MCP_SECRET` (mismo valor en ChatGPT connector / parámetro `secret` de la tool) |
| REST de prueba | `POST {API_PUBLIC_BASE}/agents/mcp/store_data` con header `Authorization: Bearer {MCP_SECRET}` o `X-MCP-Secret: {MCP_SECRET}` |

En ChatGPT (connector / custom MCP): pega la URL pública `/api/mcp` y el access token / API key = `MCP_SECRET`.

## Tools disponibles

1. **`store_data`** (nueva) — guarda campos de plantilla del agente en `agents_mcp_saves` (`origin=agent`, `status=pending`). El chat del panel hace poll cada 5s y genera el Word/PDF.
2. **`save_agent_analisis_json`** (legado) — JSON de análisis en `files/agents/`. Sigue disponible.

### Parámetros `store_data`

- `agent_id` — UUID del agente
- `customer_id` — cliente dueño
- `student_id` — estudiante
- `document_id` — plantilla (`agents_document_templates`)
- `fields_json` — JSON string `{ "nombre_campo": "valor", ... }` (nombres = `detected_fields`)
- `meta_json` — opcional
- `secret` — `MCP_SECRET`

### Ejemplo REST

```http
POST /api/agents/mcp/store_data
Authorization: Bearer <MCP_SECRET>
Content-Type: application/json

{
  "agent_id": "<uuid>",
  "customer_id": 1,
  "student_id": 123,
  "document_id": 2,
  "fields": {
    "diagnostico": "…",
    "resultados_evaluacion": "…"
  }
}
```

## Trigger Workspace

El endpoint de chat inyecta en el input del trigger:

1. Prompt del agente (`role_instructions`)
2. Instrucciones MCP + esquema de campos de la(s) plantilla(s)
3. Ruta Drive `{customer_id}/{agent_name}/`
4. Contexto `student_id` / `document_id` si vienen del chat

La URL del trigger sigue siendo por agente (`workspace_trigger_url`). El token Workspace global está en Agentes → Configuraciones.

## Flujo chat → documento

1. Usuario envía mensaje en el chat de Agentes.
2. Workspace ChatGPT llama `store_data` vía MCP.
3. El front consulta `GET /agents/{id}/mcp/saves/pending` cada 5s.
4. Al encontrar un save pending: `POST /agents/{id}/mcp/saves/{save_id}/generate`.
5. Se muestra el archivo descargable en el mensaje del asistente.

## Migración

```bash
cd backend
python migrations/apply_agents_mcp_saves.py
```
