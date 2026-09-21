# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es VIDA

VIDA (Vida Artificial, Identidad y Desarrollo de Agentes) es una plataforma experimental de simulación multiagente para estudiar cómo memoria, experiencia, aprendizaje, relaciones sociales y entorno forman y preservan una identidad individual. Proyecto de investigación académica (UTMA); el rigor científico y la reproducibilidad pesan más que la velocidad. El documento de diseño completo es `Proyecto_VIDA_Documento_Completo_v2_1.pdf` (en español; léelo con `pdftotext -layout <pdf> -`, la herramienta Read no puede renderizarlo).

Estado: **VIDA-0.1, núcleo jugable implementado** (10 agentes, mundo textual de 12 lugares, memoria de cinco tipos, decisiones por reglas deterministas, consecuencias causales, SQLite + JSONL, CLI con biografías). Pendiente para cerrar 0.1: dashboard Streamlit, motor de decisión LLM y experimentos configurables en `src/vida/experiments/`.

Habla con el usuario en español. Identificadores, archivos y logs en inglés; docstrings, README, comentarios y textos de memoria/biografía en español.

## Comandos

```bash
.venv\Scripts\python -m pytest                     # suite completa (~25 s; incluye corridas cortas reales)
.venv\Scripts\python -m pytest tests/test_actions.py -k acquire   # un test
.venv\Scripts\python -m vida run --config config/default.yaml [--seed N] [--ticks N] [--run-id ID]
.venv\Scripts\python -m vida runs                  # listar corridas en data/runs/
.venv\Scripts\python -m vida life a01 --run <run_id> [--json]     # biografía de un agente
```

Entorno: `.venv` creado con `python -m venv .venv && .venv\Scripts\pip install -e ".[dev]"`. Sin uv ni ruff instalados. Una corrida de 30 días con 10 agentes tarda ~45 s y genera ~7000 eventos.

Git: el repositorio de VIDA vive en esta carpeta, pero `C:\Users\Montoya\Documents` (el padre) también es un repo con cientos de archivos ajenos. Ejecuta git siempre desde `VIDA/` y añade rutas explícitas.

## Principios de arquitectura (no negociables, del documento)

1. **El simulador es la autoridad.** `WorldState` (`world/world.py`) es la verdad; `WorldModel` (`agents/beliefs.py`) es lo que el agente cree. Sólo `World.resolve` (vía `world/rules.py`) muta el mundo.
2. **El motor de decisión propone; el mundo resuelve.** `DecisionEngine.decide` devuelve una `ActionProposal`; `World.resolve` devuelve el `ActionOutcome` objetivo. Cualquier motor nuevo (LLM) implementa el `Protocol` de `agents/decision.py` y se registra en `ENGINES`.
3. **Las relaciones cambian por resultados, no por palabras.** `agents/social.py` y `agents/learning.py` sólo leen `ActionOutcome`; nunca `proposal.rationale` ni `details["_world"]`. La clave `_world` guarda lo que sólo el mundo sabe (si una respuesta fue mentira) y alimenta reputación y evaluación.
4. **Reproducibilidad.** Todo azar sale de `RngHub.sub(...)` (`simulation/rng.py`); nunca `random` global. Nada depende del orden de iteración de un `set` (usar `sorted`). El hash de eventos excluye `run_id`, así dos corridas con la misma semilla dan hash idéntico (`tests/test_determinism.py`).
5. **Lenguaje científico.** Nada en código, logs, memorias ni biografías afirma conciencia o sentimientos; se describen conductas observadas.

## Flujo de un tick (`simulation/engine.py`)

Por agente, en orden barajado con semilla: `World.perceive` → `learning.observe` (creencias) → `AgentMemory.retrieve` → `DecisionEngine.decide` (si es `ask_info`, el otro agente responde en el mismo tick con `decide_reply`) → `World.resolve` → `AgentState.apply_outcome` (único punto que actualiza `location_id`) → memoria episódica/social/semántica/procedimental → `learning.learn` → `social.update_relationships` → `World.update_reputation` → `EventRecord` a JSONL y SQLite. Al final del tick: decaen necesidades y `lifecycle.advance` (etapas, muerte). Al final del día: resumen autobiográfico, `consolidate` (olvido) e `identity.refresh`.

## Mecanismo de engaño (sección 20)

`ask_info`/`share_info` llevan una ubicación afirmada. El mundo compara con la verdad y anota intención y veracidad en `WorldState.info_ledger[event_id]`. El receptor guarda una creencia `told` con `source_agent` y `source_event_id`. Cuando actúa sobre ella (`acquire`) y fracasa, `rules._acquire` atribuye el fallo a la fuente: la confianza cae (`social.py`) y, si el libro dice que fue mentira, la reputación de la fuente baja (`World.update_reputation`). Las creencias nunca se borran, sólo se debilitan hasta `MIN_CONFIDENCE`, para que el agente pueda volver a comprobar un lugar.

## Dónde tocar qué

- Nueva acción: `ActionKind` en `world/actions.py`, resolver + legalidad en `world/rules.py`, puntuación en `RuleBasedEngine._local_scores`/`_move_scores`, plantilla en `memory/episodic.describe`, etiqueta en `memory/autobiographical.ACTION_LABELS`.
- Parámetros de corrida: sólo en `config/default.yaml` + `simulation/config.py` (el hash de config forma parte de la reproducibilidad).
- Mundo o población inicial: `world/presets.py` (`village_small`, `spawn_agents`, `COMMON_KNOWLEDGE`).
- Persistencia: `database/models.py` guarda JSON completo por evento/memoria/estado; consultas en `database/repository.py`. Biografías en `evaluation/biography.py`.

## Tests

`tests/conftest.py` da `cfg` (YAML por defecto), `small_cfg` (2 agentes, semilla 7) y `small_world` = `(world, agents, hub)`. Los tests de motor/CLI ejecutan simulaciones reales de 48-240 ticks. Si cambias reglas o puntuaciones, revisa `test_determinism.py` (hash) y vuelve a correr `python -m vida run` 30 días para comprobar que nadie muere de hambre con la configuración por defecto (criterio de aceptación usado hasta ahora).
