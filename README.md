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

# Resumen de Desarrollo: Discussion Medical Agents — BIRADS 4B

## Objetivo

Workflow n8n que simula un **comité tumoral multidisciplinario de mama** para casos BIRADS 4B, ejecutado completamente de forma local con LiteLLM + Ollama, sin dependencias de APIs externas.

---

## Arquitectura

```
Webhook (caso clínico)
    │
    ▼
Pre-Validación ── gemma3:270m
    │
    ▼
─────────────── RONDA 1 (paralelo) ───────────────
  Radióologa     Cirujano     Oncóloga     Patólogo     Ginecóloga
  qwen3:14b   llama3.1:8b  qwen3.5:9b  lfm2.5-inst  llama3.2
──────────────────────────────────────────────────
    │
    ▼
Merge R1 → Formatear → Preparar Bodies R2
    │
    ▼
─────────────── RONDA 2 (paralelo) ───────────────
  (historial completo: system + user R1 + assistant R1 + user R2)
──────────────────────────────────────────────────
    │
    ▼
Merge R2 → Síntesis Final (lfm2.5-thinking)
    │
    ▼
Reporte JSON → Webhook Response
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

## Dinámica de rondas

| Ronda | Descripción |
|-------|-------------|
| **Pre-validación** | `gemma3:270m` verifica que el caso clínico tenga los elementos mínimos requeridos |
| **Ronda 1** | Cada especialista evalúa el caso de forma independiente en paralelo |
| **Ronda 2** | Cada especialista debate con las opiniones de sus 4 colegas usando historial multi-turno |
| **Síntesis** | `lfm2.5-thinking` consolida el consenso final con plan de acción jerarquizado |

---

## Stack tecnológico

- **n8n** — orquestación del workflow
- **LiteLLM** — proxy unificado para todos los modelos (`localhost:4000`)
- **Ollama** — ejecución local de los modelos
- **Webhook** — entrada del caso clínico vía HTTP POST

---

## Repositorio

**https://github.com/samperio/discussion-medical-agents**


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
