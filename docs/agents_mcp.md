# MCP Agentes PIE360

URL pública: `{API_PUBLIC_BASE}/mcp`  
Auth: `secret` = `MCP_SECRET` (o Bearer / `X-MCP-Secret` en REST).

## Estructura

```
app/backend/mcp/
├── auth.py / server.py
└── tools/
    ├── create_document.py              # genera + ficha + sube a Drive
    ├── save_document_to_google_drive.py # re-sube a Drive (árbol colegio)
    ├── get_student_psychopedagogical_evaluation.py  # lee doc 27 desde ficha
    ├── get_student_psychopedagogical_form_answers.py  # respuestas Formularios PIE360
    ├── store_data.py
    └── search_agent_files.py
```

Negocio: `classes/agents_mcp_class.py`  
Generación física: `classes/agents_document_service.py` (`generate_and_save_document`)  
Chat auto: `classes/agents_chat_class.py`  
Si Files del agente no trae el psicopedagógico del estudiante, el chat inyecta el de la ficha (document_id=27).  
Si el cuestionario/Excel de Files no trae la fila del estudiante, el chat llama MCP `get_student_psychopedagogical_form_answers` e inyecta las respuestas de Formularios.

## Asociación Documentos (importante)

En el agente, **Documentos**:

1. Se elige un **tipo de documento** del catálogo PIE360 (`document_id`).
2. Se sube el **modelo/plantilla** (.docx/.pdf) para ese tipo.
3. Ese mismo `document_id` es el del **formulario** que se rellena al generar.

`create_document(document_id=…)` usa exactamente esa plantilla y actualiza ese formulario
(ej. familia → `family_reports`). Sin plantilla para ese `document_id` → error claro.

## Google Drive (por customer)

Tras generar, el archivo se sube al Drive del cliente (si está conectado):

```
{carpeta raíz del cliente}/
  {Nombre del liceo}/
    {Año}/
      {Curso}/
        {RUT numérico}/
          {RUT}_{Tipo de documento}.docx
```

Ejemplo: `Liceo Demo/2026/1° Medio A/274309032/274309032_Informe a la Familia.docx`

Las carpetas se crean si no existen. Si el archivo ya está, se reemplaza.

## Tools

| Tool | REST |
|------|------|
| `create_document` | `POST /api/agents/mcp/create_document` |
| `save_document_to_google_drive` | `POST /api/agents/mcp/save_document_to_google_drive` |
| `get_student_psychopedagogical_evaluation` | `POST /api/agents/mcp/get_student_psychopedagogical_evaluation` |
| `get_student_psychopedagogical_form_answers` | `POST /api/agents/mcp/get_student_psychopedagogical_form_answers` |
| `store_data` | `POST /api/agents/mcp/store_data` |
| `search_agent_files` | `POST /api/agents/mcp/search_files` |

## Qué se eliminó (legado)

- Generación directa OpenAI en el chat (sin MCP)
- Trigger Workspace ChatGPT (`/workspace-agent/chat`)
- Tool `save_agent_analisis_json` + validación de análisis
- Subida local `files/agents` vía MCP upload token
