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
