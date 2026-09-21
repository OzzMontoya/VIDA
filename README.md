# VIDA

**Vida Artificial, Identidad y Desarrollo de Agentes.**

Plataforma experimental de simulación multiagente para estudiar cómo la memoria, la experiencia, el aprendizaje, las relaciones sociales y el entorno forman, modifican y preservan una identidad individual. Proyecto de investigación de Oziel Atlahi Montoya Mares (UTMA). El documento de diseño completo está en `Proyecto_VIDA_Documento_Completo_v2_1.pdf`.

Estado: **VIDA-0.1 en desarrollo** (núcleo jugable: 10 agentes, mundo textual, memoria, decisiones por reglas, consecuencias causales, SQLite y logs JSONL).

## Principios de arquitectura

1. **El simulador es la autoridad sobre el mundo.** El estado objetivo (`WorldState`) está separado de lo que cada agente cree (`WorldModel`).
2. **El motor de decisión propone; el mundo resuelve.** `World.resolve` es la única función que muta el mundo.
3. **Las relaciones cambian por resultados, no por palabras.** Confianza y reputación se ajustan según la consecuencia objetiva de cada interacción.
4. **Reproducibilidad total.** Semilla, hash de configuración, versión de código y hash de eventos se registran en cada corrida.
5. **Lenguaje científico.** Se distingue observación, interpretación e hipótesis. Nada en el código afirma conciencia.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"     # Windows
# source .venv/bin/activate && pip install -e ".[dev]"   # Linux/macOS
```

## Uso

```bash
pytest                                                # pruebas
python -m vida run --config config/default.yaml       # corrida de 30 días con 10 agentes
python -m vida runs                                   # listar corridas
python -m vida life a01 --run <run_id>                # biografía de un agente
```

## Estructura

```
config/default.yaml   parámetros de la corrida (todo lo que afecta al resultado)
src/vida/agents       estado del agente, personalidad, necesidades, creencias, decisión, aprendizaje, identidad
src/vida/memory       memoria episódica, semántica, social, autobiográfica y procedimental
src/vida/world        lugares, recursos, acciones y reglas de resolución
src/vida/simulation   configuración, RNG, reloj, eventos, engine, ciclo de vida, logging
src/vida/database     modelos SQLAlchemy y repositorio (SQLite por corrida)
src/vida/evaluation   biografías y métricas
tests/                pytest
data/runs/<run_id>/   base SQLite de cada corrida (ignorado por git)
logs/<run_id>/        eventos JSONL de cada corrida (ignorado por git)
```
