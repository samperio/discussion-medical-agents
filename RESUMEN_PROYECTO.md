# Resumen del Proyecto: Discussion Medical Agents — BIRADS 4B

## Objetivo

Workflow n8n que simula un **comité tumoral multidisciplinario de mama** para casos BIRADS 4B, ejecutado completamente de forma local con LiteLLM + Ollama, sin dependencias de APIs externas.

---

## Arquitectura

5 agentes especialistas en **2 rondas de discusión** + síntesis final:

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

| Ronda | Dinámica |
|-------|----------|
| **R1** | Cada especialista evalúa el caso de forma independiente (paralelo) |
| **R2** | Cada especialista debate con las opiniones de sus 4 colegas (historial multi-turno) |
| **Síntesis** | Director de comité consolida consenso y plan de acción |

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

## Bug crítico corregido

### Problema
Los **5 nodos de Ronda 2** tenían el `jsonBody` de Ronda 1 hardcodeado.  
Cada especialista respondía en R2 sin ver las opiniones de sus colegas, ignorando completamente el nodo **"Preparar Bodies R2"**.  
Adicionalmente, el nodo **"Síntesis Final"** no tenía body configurado.

### Causa raíz
Uso de `specifyBody: "json"` con `jsonBody` estático en los nodos HTTP Request de R2, en lugar de referenciar los bodies pre-construidos con `JSON.stringify` en el nodo Code previo.

### Corrección aplicada

| Nodo | Antes | Después |
|------|-------|---------|
| R2 - Radiologa | `jsonBody` R1 copiado | `body: ={{ $json.body_radiologo }}` |
| R2 - Cirujano | `jsonBody` R1 copiado | `body: ={{ $json.body_cirujano }}` |
| R2 - Oncologa | `jsonBody` R1 copiado | `body: ={{ $json.body_oncologo }}` |
| R2 - Patologo | `jsonBody` R1 copiado | `body: ={{ $json.body_patologo }}` |
| R2 - Ginecologa | `jsonBody` R1 copiado | `body: ={{ $json.body_ginecologo }}` |
| Sintesis Final | sin body | `body: ={{ $json.body_sintesis }}` |

### Regla aplicada (n8n + LiteLLM)
Cuando el body del LLM se construye en un nodo Code con `JSON.stringify(...)`, el nodo HTTP Request debe usar:

```
specifyBody: "string"
body: ={{ $json.body_xxx }}
```

Usar `specifyBody: "json"` con `jsonBody` dinámico provoca doble-serialización o pérdida del historial.

### Patrón correcto del historial multi-turno (R2)

```json
"messages": [
  { "role": "system",    "content": "<perfil del especialista>" },
  { "role": "user",      "content": "<pregunta R1 + caso clínico>" },
  { "role": "assistant", "content": "<respuesta R1 del especialista>" },
  { "role": "user",      "content": "<pregunta R2 con contexto de colegas>" }
]
```

---

## Archivos del proyecto

| Archivo | Descripción |
|---------|-------------|
| `birads4b_discussion_v1.json` | Workflow n8n importable (versión corregida) |
| `resultado.txt` | Ejemplo de reporte JSON generado con caso real de biopsia de mama |
| `README.md` | Documentación de uso e importación |
| `RESUMEN_PROYECTO.md` | Este documento |

---

## Repositorio

**https://github.com/samperio/discussion-medical-agents**

---

## Disclaimer

Reporte generado por agentes de IA local (LiteLLM + Ollama).  
**No reemplaza el juicio médico profesional.** Debe ser revisado y validado por médicos especialistas certificados antes de su aplicación clínica.
