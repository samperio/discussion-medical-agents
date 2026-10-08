# Discussion Medical Agents — BIRADS 4B

Workflow n8n multi-agente para **comité tumoral multidisciplinario de mama** con casos BIRADS 4B.  
Ejecuta localmente sobre **LiteLLM + Ollama** sin dependencias de APIs externas.

---

## Arquitectura general

```
Webhook (caso clínico)
    │
    ▼
Pre-Validación ── gemma3:270m
    │
    ▼
─────────────────── RONDA 1 (paralelo) ────────────────────
  Radióologa       Cirujano       Oncóloga       Patólogo       Ginecóloga
  qwen3:14b     llama3.1:8b   qwen3.5:9b    lfm2.5-inst    llama3.2
─────────────────────────────────────────────────────────────
    │
    ▼
Merge R1 → Formatear → Preparar Bodies R2
    │
    ▼
─────────────────── RONDA 2 (paralelo) ────────────────────
  (historial completo: system + user R1 + assistant R1 + user R2)
─────────────────────────────────────────────────────────────
    │
    ▼
Merge R2 → Síntesis Final (lfm2.5-thinking)
    │
    ▼
Reporte JSON final → Webhook Response
```

---

## Especialistas simulados

| Agente | Modelo | Rol |
|--------|--------|-----|
| Dra. Ana Valverde | `qwen3:14b` | Radióologa de Mama — Moderadora |
| Dr. Carlos Mendoza | `llama3.1:8b-local` | Cirujano Oncólogo |
| Dra. Patricia Roldán | `qwen3.5:9b-local` | Oncóloga Médica |
| Dr. Rubén Castillo | `tomng/lfm2.5-instruct:latest` | Patólogo Especialista |
| Dra. Sofía Herrera | `llama3.2-local` | Ginecóloga Mastóloga |
| Director de Comité | `lfm2.5-thinking:latest` | Síntesis Final |

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `birads4b_discussion_v1.json` | Workflow n8n importable (versión corregida) |
| `resultado.txt` | Ejemplo de reporte JSON generado por el workflow |

---

## Requisitos

- **n8n** ≥ 1.x  
- **LiteLLM** corriendo en `localhost:4000` (o configurable por env `LITELLM_URL`)  
- **Ollama** con los modelos listados descargados  
- Variable de entorno `LITELLM_API_KEY` (default: `sk-local`)

---

## Cómo importar

1. Abrir n8n → **Workflows → Import from file**
2. Seleccionar `birads4b_discussion_v1.json`
3. Activar el workflow
4. Hacer POST al webhook:

```bash
curl -X POST http://localhost:5678/webhook/birads4b-discussion \
  -H "Content-Type: application/json" \
  -d '{
    "caso_clinico": "Paciente femenina de 48 años. Lesión espiculada de 1.2cm...",
    "paciente_nombre": "Paciente Ejemplo"
  }'
```

---

## Resumen de desarrollo (conversación con Claude Code)

### Problema inicial
El workflow tenía los **5 nodos de Ronda 2** con el `jsonBody` hardcodeado de la Ronda 1.  
Esto causaba que cada especialista respondiera sin ver las opiniones de sus colegas — ignorando completamente el nodo **"Preparar Bodies R2"** que construye el historial multi-turno correcto.

Adicionalmente, el nodo **"Síntesis Final"** no tenía ningún body configurado.

### Correcciones aplicadas

**Causa raíz:** `specifyBody: "json"` con `jsonBody` estático en vez de usar los bodies pre-construidos con `JSON.stringify` en el nodo Code previo.

**Regla n8n+LiteLLM:** cuando el body del LLM se construye en un nodo Code con `JSON.stringify(...)`, el nodo HTTP Request debe usar `specifyBody: "string"` + `body: ={{ $json.body_xxx }}`. Usar `specifyBody: "json"` con `jsonBody` dinámico provoca doble-serialización o pérdida del historial.

| Nodo corregido | Antes | Después |
|---|---|---|
| R2 - Radiologa | `jsonBody` R1 copiado | `body: ={{ $json.body_radiologo }}` |
| R2 - Cirujano | `jsonBody` R1 copiado | `body: ={{ $json.body_cirujano }}` |
| R2 - Oncologa | `jsonBody` R1 copiado | `body: ={{ $json.body_oncologo }}` |
| R2 - Patologo | `jsonBody` R1 copiado | `body: ={{ $json.body_patologo }}` |
| R2 - Ginecologa | `jsonBody` R1 copiado | `body: ={{ $json.body_ginecologo }}` |
| Sintesis Final | sin body | `body: ={{ $json.body_sintesis }}` |

### Flujo multi-turno correcto (Ronda 2)

Cada llamada LLM en R2 incluye historial completo:
```
messages: [
  { role: "system",    content: <perfil del especialista> },
  { role: "user",      content: <pregunta R1 + caso clínico> },
  { role: "assistant", content: <respuesta R1 del especialista> },
  { role: "user",      content: <pregunta R2 con contexto de colegas> }
]
```

### Nota sobre /no_think
El modelo `qwen3.5:9b-local` (Oncóloga) recibe el prefijo `/no_think` tanto en el system prompt como en el user message de R1 y R2, para suprimir el bloque `<think>` interno y obtener respuestas directas.

---

## Disclaimer

Reporte generado por agentes de IA local (LiteLLM + Ollama).  
**No reemplaza el juicio médico profesional.** Debe ser revisado y validado por médicos especialistas certificados antes de su aplicación clínica.

---

## Stack en Docker (v2)

Ollama + LiteLLM + n8n corren juntos en la red `birads-net`.

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d   # con GPU NVIDIA
docker compose up -d                                                   # solo CPU
```

| Servicio | URL host | URL interna |
|----------|----------|-------------|
| n8n | http://localhost:5678 | — |
| LiteLLM | http://localhost:4000 (key `sk-local`) | http://litellm:4000 |
| Ollama | http://localhost:11434 | http://ollama:11434 |

- Los modelos se montan en solo lectura desde `OLLAMA_MODELS_PATH` (no se descargan de nuevo).
- Alias de modelos en `litellm/config.yaml`; n8n recibe `LITELLM_URL` y `LITELLM_API_KEY` por entorno.
- Importar/publicar el workflow (usar `MSYS_NO_PATHCONV=1` en Git Bash):
  ```bash
  docker exec birads-n8n n8n import:workflow --input=/workflows/birads4b_discussion_v2.json
  docker exec birads-n8n n8n publish:workflow --id=5GfZMChnzMznWhY2 && docker restart birads-n8n
  ```
- Webhook de producción: `POST http://localhost:5678/webhook/birads4b-discussion` con `{"caso_clinico": "..."}`.
