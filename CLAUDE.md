# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado actual

Este directorio contiene **solo el documento de diseño** (`Proyecto_VIDA_Documento_Completo_v2_1.pdf`, en español). Todavía no hay código, `pyproject.toml`, tests ni README. Todo lo que sigue proviene de ese PDF y describe lo que el proyecto *debe* ser; verifica contra el código real conforme aparezca.

Para leer el PDF desde la terminal: `pdftotext -layout Proyecto_VIDA_Documento_Completo_v2_1.pdf -` (pdftotext está disponible en `/mingw64/bin`; `pypdf` también está instalado en Python 3.13). `pdftoppm` no está instalado, así que la herramienta Read no puede renderizar el PDF.

Nota: el repositorio git raíz es `C:\Users\Montoya\Documents` (no esta carpeta), y tiene cientos de archivos sin relación. No hagas `git add -A` ni commits amplios desde aquí; añade rutas explícitas dentro de `VIDA/`.

Habla con el usuario en español.

## Qué es VIDA

VIDA (Vida Artificial, Identidad y Desarrollo de Agentes) es una plataforma experimental de simulación multiagente para estudiar cómo memoria, experiencia, aprendizaje, relaciones sociales y entorno forman y preservan una identidad individual. Es un proyecto de investigación académica (UTMA); el rigor científico y la reproducibilidad pesan más que la velocidad.

Existe un MVP previo en TypeScript/Node (`vida-mvp.zip`, no incluido aquí) con dos agentes (Ana/Luis). La decisión oficial es **reconstruir el núcleo en Python**; el MVP es solo referencia conceptual y sus heurísticas (ubicación pseudoaleatoria, efectos sociales por palabras clave) están marcadas para ser reemplazadas.

## Principios de arquitectura no negociables

Estos vienen del documento (secciones 12, 20, 29, 37 y Apéndice D) y deben respetarse en cualquier código nuevo:

1. **El simulador es la autoridad sobre el mundo.** El estado objetivo del mundo se mantiene separado de lo que cada agente cree o declara. Esto es lo que permite estudiar error, engaño, incertidumbre y reputación.
2. **El LLM propone, no decide el resultado.** Un modelo de lenguaje es un componente cognitivo dentro del estado del agente, nunca "la mente completa". Puede proponer una acción; el motor de simulación resuelve la consecuencia objetiva. La interfaz de decisión debe permitir intercambiar LLM externo, modelo local o reglas.
3. **Separar decisión de ejecución.** Ciclo canónico: percepción → recuperación de memoria → evaluación de necesidades/objetivos → decisión → acción → consecuencia real del mundo → nueva memoria → aprendizaje → actualización de relaciones/identidad → registro.
4. **Causalidad real, no narración.** Las relaciones y la reputación cambian por el resultado objetivo de una interacción, no por palabras clave en el texto de la acción.
5. **Reproducibilidad.** Cada experimento conserva semilla, configuración YAML, versión del código, versión del modelo, parámetros, historial de eventos y métricas. Preferir determinismo cuando sea posible.
6. **Lenguaje científico.** Distinguir siempre observación → interpretación → hipótesis → conclusión. Nunca describir en código, logs, docs o dashboard a un agente como "consciente"; frases como "tengo miedo" son datos conductuales. El Índice de Continuidad Individual (ICI) es una métrica de semejanza entre estados, no una medida de conciencia ni identidad metafísica.

## Stack objetivo

Python como único lenguaje del núcleo. Pydantic/dataclasses para modelos; motor de simulación propio con reloj simulado y eventos discretos; SQLite en VIDA-0.1 (PostgreSQL después); logs JSONL por corrida; configuración en YAML; FastAPI para API; Streamlit + Plotly para dashboard; pytest; NumPy/Pandas; PyTorch/scikit-learn según experimento; venv o uv (Docker más adelante). La Fase 0 debe correr en una PC sin GPU.

## Estructura de código prevista (Apéndice C)

```
VIDA/
  pyproject.toml
  .env.example
  config/default.yaml
  src/vida/
    agents/      agent, personality, goals, identity, decision
    memory/      base, episodic, semantic, social, autobiographical (procedural y reflexiva después)
    world/       world, locations, events, rules
    simulation/  engine, clock, lifecycle
    database/    models, repository
    experiments/
    evaluation/
  dashboard/app.py
  tests/
  data/
```

Subsistemas conceptuales: agentes, mundo, memoria, sociedad, tiempo/ciclo de vida, motor de decisiones y evaluación científica. Entidades principales del modelo de datos: Agent, Memory, Event, Action, Decision, Relationship, Goal, Preference, KnowledgeItem, LifeStage, WorldState, Experiment, AgentStateHistory. Cada evento registra como mínimo: timestamp simulado, agente, percepción, estado relevante, decisión, acción, consecuencias objetivas, memoria creada, cambios sociales y estado del mundo.

## Primer hito: VIDA-0.1 (Apéndice B)

10 agentes, ≤20 lugares en un mundo textual (vivienda, plaza, mercado, escuela, hospital, trabajo), reloj configurable, cinco tipos de memoria, necesidades/objetivos/personalidad/preferencias, relaciones con confianza y afecto, eventos objetivos, consecuencias causales, historial de estados, SQLite, JSONL, semillas reproducibles, experimentos configurables y dashboard básico. Criterio de éxito: poder reconstruir la vida completa de cualquier agente (qué vivió, recuerda, aprendió, prefiere, a quién conoce, qué decidió y qué lo modificó). No añadir entorno 3D hasta que la simulación textual produzca historias reproducibles y métricas útiles.

Ciclo de vida configurable: nacimiento → infancia → adolescencia → juventud → adultez → vejez → muerte, con generaciones posteriores. Fases siguientes (VIDA-0.2 a 7.0) escalan a 100+ agentes, sociedad, generaciones, identidad, transferencia y cuerpo artificial.

## Comandos

No hay comandos todavía. Cuando se cree el proyecto Python, la expectativa del documento es `pytest` para pruebas, `streamlit run dashboard/app.py` para el dashboard y scripts/notebooks reproducibles para experimentos. Actualiza esta sección cuando exista `pyproject.toml`.
