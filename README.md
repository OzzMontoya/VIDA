# VIDA

**Vida Artificial, Identidad y Desarrollo de Agentes.**

Plataforma experimental de simulación multiagente para estudiar cómo la memoria, la experiencia, el aprendizaje, las relaciones sociales y el entorno forman, modifican y preservan una identidad individual. Proyecto de investigación de Oziel Atlahi Montoya Mares (UTMA). El documento de diseño completo está en `Proyecto_VIDA_Documento_Completo_v2_1.pdf`.

Estado: **VIDA-0.1, núcleo jugable.** 10 agentes viven 30 días simulados en un pueblo textual de 12 lugares: trabajan, compran, comen, descansan, estudian, conversan, piden y comparten información (a veces falsa), y cada uno acumula memoria episódica, semántica, social, autobiográfica y procedimental. Las decisiones son por reglas deterministas con semilla, o bien con un modelo de lenguaje (Claude) para todos o algunos agentes. Pendiente para cerrar 0.1: experimentos configurables.

Qué puede responder hoy el sistema sobre cualquier agente (criterio de éxito de 0.1): qué vivió, qué recuerda, qué aprendió, qué prefiere, a quién conoce, qué decisiones tomó y qué experiencias lo modificaron. Ver `python -m vida life`.

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
pytest                                                # pruebas (~25 s)
python -m vida run --config config/default.yaml       # corrida de 30 días con 10 agentes (~45 s)
python -m vida run --seed 7 --ticks 240 --run-id demo # semilla y duración explícitas
python -m vida runs                                   # listar corridas
python -m vida life a01 --run <run_id>                # biografía de un agente (añade --json para datos)
```

## Motor de decisión con LLM

```bash
.venv\Scripts\pip install anthropic                      # una sola vez
copy .env.example .env                                     # y escribe tu ANTHROPIC_API_KEY
.venv\Scripts\python -m vida run --config config/llm.yaml           # Ana y Diego deciden con claude-opus-5, el resto por reglas
.venv\Scripts\python -m vida run --engine llm_v1 --llm-agents a01 --llm-model claude-haiku-4-5 --ticks 120
```

El LLM recibe la ficha del agente, su percepción, sus creencias (que pueden ser falsas), sus recuerdos relevantes y la lista de acciones legales, y elige una por su clave. El mundo sigue resolviendo el resultado. Si la respuesta no es válida, la API falla o el modelo declina, el agente decide por reglas y el evento lo registra (`decision.engine = "llm_v1/fallback:rules_v1"`). Cada respuesta se guarda en `data/llm_cache.sqlite`: repetir la corrida con la misma semilla no vuelve a llamar a la API y reproduce el mismo hash de eventos.

Costo orientativo con `claude-opus-5`: unos 1.700 tokens de entrada y 60 de salida por decisión, cerca de 1 centavo de dólar cada una. Una corrida de 30 días con los 10 agentes son ~7.200 decisiones, unos 70 dólares; con `claude-haiku-4-5` unos 14. Por eso `config/llm.yaml` limita el LLM a dos agentes y 10 días (unos 5 dólares). El resumen de cada corrida imprime llamadas, aciertos de caché, tokens y costo estimado.

## Dashboard

```bash
.venv\Scripts\pip install -e ".[dashboard]"          # streamlit, plotly, pandas (una sola vez)
.venv\Scripts\python -m streamlit run dashboard/app.py
```

Abre `http://localhost:8501`. En la barra lateral eliges corrida, agente y vista:

- **Corrida**: agentes vivos, necesidades medias de la población (con las escaseces marcadas), qué hizo cada agente y eventos del mundo.
- **Agente**: identidad observada, necesidades suavizadas, acciones por día, dinero, relaciones (final y evolución de la confianza), preferencias aprendidas, habilidades, valores, memorias filtrables y la biografía completa.
- **Sociedad**: mapas de calor de confianza y familiaridad entre todos, dónde pasan el día, existencias reales del mundo y el registro de verdad/mentira/omisión de cada agente.
- **Eventos**: tabla filtrable por agente, acción, resultado y rango de días.

Cada corrida deja `data/runs/<run_id>/vida.sqlite` (eventos, memorias, snapshots de estado, relaciones) y `logs/<run_id>/events.jsonl` (una línea por evento). El resumen incluye el hash SHA-256 de los eventos: dos corridas con la misma semilla y configuración producen el mismo hash.

Ejemplo de biografía (fragmento real de la corrida de aceptación):

```
=== Diego (a06) — corrida accept_v2 ===
Edad: 25 → 55 días. Etapas: youth (día 0) → adulthood (día 4).
Identidad observada: sociable, engañoso, cercano_a:a01,a02,a03, prefiere:action:acquire.
Valores: {'ambition': 0.355, 'honesty': 0.351, 'loyalty': 0.958}. Reputación: 1.0.
...
5) A QUIÉN CONOCE
  - Ana (a01): familiaridad 1.0, confianza 0.989, afecto 0.942, honestidad estimada 0.5
  - Andrés (a08): familiaridad 1.0, confianza 0.981, afecto 0.966, honestidad estimada 0.5
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
