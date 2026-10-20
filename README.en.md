# VIDA

English translation of `README.md` (Spanish original is canonical).

**Vida Artificial, Identidad y Desarrollo de Agentes** (Artificial Life, Identity and Agent Development).

An experimental multi-agent simulation platform for studying how memory, experience, learning, social relationships and the environment form, modify and preserve an individual identity. Research project by Oziel Atlahi Montoya Mares (UTMA). The complete design document is `Proyecto_VIDA_Documento_Completo_v2_1.pdf`.

Status: **VIDA-2.0 in development** (society): on top of the full lives with generations from 1.0, prices that respond to scarcity, public reputation, restocking proportional to the population (100 agents in `config/society.yaml`) and identity ablations in the transfer experiment. 10 agents live 30 simulated days in a textual town of 12 places: they work, buy, eat, rest, study, converse, ask for and share information (sometimes false), and each one accumulates episodic, semantic, social, autobiographical and procedural memory. Decisions are made by seeded deterministic rules, or by a language model (Claude) for all or some agents. It includes configurable experiments (memory, environment, deception and transfer between substrates) with scientific metrics and the Individual Continuity Index. VIDA-0.2 adds reflective memory (conclusions derived from several experiences), strong coupling between what is lived and what is decided, a predictive self-model with calibration metrics and advantage over an external model, beliefs that weaken when forgotten, and scaling to 100 agents (`world.n_homes`).

What the system can answer today about any agent (success criterion of 0.1): what it lived through, what it remembers, what it learned, what it prefers, whom it knows, which decisions it took and which experiences modified it. See `python -m vida life`.

## Architecture principles

1. **The simulator is the authority over the world.** The objective state (`WorldState`) is separate from what each agent believes (`WorldModel`).
2. **The decision engine proposes; the world resolves.** `World.resolve` is the only function that mutates the world.
3. **Relationships change through outcomes, not words.** Trust and reputation are adjusted according to the objective consequence of each interaction.
4. **Full reproducibility.** Seed, configuration hash, code version and event hash are recorded in every run.
5. **Scientific language.** Observation, interpretation and hypothesis are kept distinct. Nothing in the code asserts consciousness.

## Installation

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"     # Windows
# source .venv/bin/activate && pip install -e ".[dev]"   # Linux/macOS
```

## Usage

```bash
pytest                                                # tests (~25 s)
python -m vida run --config config/default.yaml       # 30-day run with 10 agents (~45 s)
python -m vida run --seed 7 --ticks 240 --run-id demo # explicit seed and duration
python -m vida runs                                   # list runs
python -m vida life a01 --run <run_id>                # biography of an agent (add --json for data)
```

## LLM decision engine

```bash
.venv\Scripts\pip install anthropic                      # once
copy .env.example .env                                     # and write your ANTHROPIC_API_KEY
.venv\Scripts\python -m vida run --config config/llm.yaml           # Ana and Diego decide with claude-opus-5, the rest by rules
.venv\Scripts\python -m vida run --engine llm_v1 --llm-agents a01 --llm-model claude-haiku-4-5 --ticks 120
```

The LLM receives the agent's profile, its perception, its beliefs (which may be false), its relevant memories and the list of legal actions, and chooses one by its key. The world still resolves the outcome. If the response is invalid, the API fails or the model declines, the agent decides by rules and the event records it (`decision.engine = "llm_v1/fallback:rules_v1"`). Every response is stored in `data/llm_cache.sqlite`: repeating the run with the same seed does not call the API again and reproduces the same event hash.

Indicative cost with `claude-opus-5`: about 1,700 input tokens and 60 output tokens per decision, close to 1 US cent each. A 30-day run with all 10 agents is ~7,200 decisions, about 70 dollars; with `claude-haiku-4-5` about 14. For that reason `config/llm.yaml` limits the LLM to two agents and 10 days (about 5 dollars). The summary of each run prints calls, cache hits, tokens and estimated cost.

### Local, free LLM (Ollama)

```bash
ollama pull llama3.2                                       # 2 GB, once
.venv\Scripts\python -m vida run --config config/llm_local.yaml
.venv\Scripts\python -m vida run --engine llm_v1 --llm-provider ollama --llm-model llama3.1 --llm-agents a01 --ticks 48
```

No per-token cost. On this machine (CPU; the AMD GPU via Vulkan produces corrupt text, hence `num_gpu: 0`) each decision takes about 35 s with `llama3.2`; 2 agents over 10 days are ~5 hours. The cache makes repeating the run immediate. In the real 12-tick test, Ana chose valid actions in every decision and her justifications were coherent with her needs and relationships.

## Experiments and metrics

```bash
python -m vida experiment memory      --seeds 1,2,3 --ticks 240   # completa / limitada / ausente / sin_olvido (full / limited / absent / no forgetting)
python -m vida experiment environment --seeds 1,2,3 --ticks 240   # abundancia / normal / escasez (abundance / normal / scarcity)
python -m vida experiment deception   --seeds 1,2,3 --ticks 240   # honestos / neutros / deshonestos / deshonestos_con_escasez (honest / neutral / dishonest / dishonest with scarcity)
python -m vida experiment transfer    --seeds 1,2,3 --split 240 --horizon 120 --agent a01
python -m vida experiment decision    --seeds 1,2,3 --ticks 240   # different histories facing the same situation
python -m vida experiment memory      --seeds 1,2,3 --ticks 360 --effects completa:ausente   # effect sizes between two variants
```

Each experiment runs its variants with each seed, computes the section 30 metrics per agent (memory, behavioural consistency, preference stability, trust, deception, learning, decision entropy, survival) and stores `results.json`, `summary.json` and `manifest.json` in `data/experiments/<name>/<date>/`.

The **decision** experiment (section 19) places all agents, after ten days of life, in the same situation (same place, time, needs and money) and compares what each one chooses with its history against what it would choose with the same personality but no history: `share_changed` is the fraction whose choice changes when what they lived is removed.

The **transfer** experiment simulates a life up to a cut-off tick, clones the whole world and in each clone replaces the mind of the studied agent according to the condition (full, memory only, knowledge only, personality only, partial, memory erased at 50 %, none) while keeping the body. All clones live the same horizon with the same random streams. The **Individual Continuity Index** (`evaluation/metrics.py`) compares each clone with the continuation without intervention and with the agent prior to the cut in eight dimensions: memory, preferences, personality, knowledge, relationships, decisions, autobiography and self-representation. It is a similarity between states; it does not measure consciousness.

### Predictive self-model (VIDA-0.2)

Before each action the agent predicts, from its own experience **in context** (action, target, time of day, hunger and energy state, with fallback to more general contexts when evidence is lacking), the probability of success; the world resolves and the error is recorded together with that of an external model that knows the same context but with data from the whole population. Per-agent metrics: `self_model_calibration` (1 − mean error) and `self_model_advantage` (external error − own error; positive if the agent predicts itself better than an observer with the information of the whole population). It is the first instrument for criterion 1 of `docs/criterios_consciencia.md`. Recent error widens the agent's exploration (minimal, measurable metacognition).

### Worlds

- `village_small` (default): 12 places, one market, two jobs with the same wage. Forced routine; useful for reproducibility and tests.
- `town` (`config/town.yaml`): an expensive, nearby market versus a cheap, distant bazaar; farm, workshop and mine with different wages and wear (2.5/0.06, 3.5/0.08, 5.5/0.14); two squares. Choosing has consequences, so individuality is more visible. Prices and wages are public knowledge (`World.public_location_info`); stock is not.

### Society (VIDA-2.0)

- **Dynamic prices**: the price of a resource in a place is its base price × (1 + 0.8·(1 − stock/restock)), bounded between 0.6 and 2.0: local scarcity raises prices and surplus lowers them (`world.dynamic_prices`).
- **Public reputation**: each agent sees the reputation of those in front of it (`PerceptionSnapshot.visible_reputations`) and uses it to choose whom to talk to, whom to ask and how much to believe.
- **Scale**: daily restocking is multiplied by n_agents/10; `config/society.yaml` runs 100 agents in `town` with 25 homes.
- **Society analysis**: `python -m vida society --run <id>` measures criterion 3 of `docs/criterios_consciencia.md` (correlation between the emotional valence the agent reports and the trust others have in it, which it cannot read), the relation between public reputation and social acceptance, inequality (Gini) and the observed price range.
- **Metacognition**: `python -m vida metacognition --run <id>` measures criterion 4 (is the agent more accurate when it declares more confidence in its own prediction, and is that confidence more informative than an external observer's?) and criterion 5 (does the confidence declared when informing another track the truth of what is said?).
- **Integration (Φ proxy)**: `python -m vida integration --run <id>` measures criterion 6. Each action records the state of six components of the mind at decision time (body, retrieved memory, self-model, relationships, identity, beliefs); the mutual information between those states and the chosen action is computed, for the whole set and for every bipartition of the components. Φ = information of the whole − information of the partition that loses the least. Positive: behaviour depends on conjunctions that no division of the mind preserves. Zero: the modules decide separately. None of this shows evidence of experience.
- **Identity ablations** (phase 4): `vida experiment transfer --conditions completa,sin_relaciones,sin_preferencias,sin_automodelo,sin_identidad,sin_creencias,ninguna` removes a single component of the mind and measures how much continuity is lost.

### Generations (VIDA-1.0)

When the living population falls below the cap, every `birth_check_days` a child is born to a living adult: it inherits part of the personality (`inheritance`), is born in adolescence in the parent's home with a third of the parent's money, receives as *told* beliefs what the parent remembers having found (true or not) and starts with a mutual family bond. While dependent (childhood and adolescence) it receives a daily allowance from the parent; if the parent dies, the adult with the most affection for the child takes the role of guardian (`guardian_id`). Each agent carries `parent_id` and `generation`; the `birth` event remains in the log. `python -m vida lineage --run <id>` compares, with the ICI, each child with its parent and with the other adults of the previous generation: if it resembles its parent more, there was transmission.

### Self-model with private knowledge

The agent's own self-model places a private level before the public context levels: for conversing, the trust and affection the agent has toward that person and its own reputation; for working, its real skill. The external reference model only sees the public context. Thus the advantage measures exactly what the individual knows about itself and its relationships.

## Research objectives

See `docs/objetivos.md`: artificial consciousness → identity and continuity → continuity when changing substrate → indefinite preservation. VIDA-0.1 builds the experimental object; it does not answer any of those questions yet. The operational criteria for the first objective (which observations would count as evidence and with which instruments) are in `docs/criterios_consciencia.md`.

## Dashboard

```bash
.venv\Scripts\pip install -e ".[dashboard]"          # streamlit, plotly, pandas (once)
.venv\Scripts\python -m streamlit run dashboard/app.py
```

Open `http://localhost:8501`. In the sidebar you choose run, agent and view:

- **Run**: living agents, mean population needs (with scarcities marked), what each agent did and world events.
- **Agent**: observed identity, smoothed needs, actions per day, money, relationships (final and evolution of trust), learned preferences, skills, values, filterable memories and the full biography.
- **Society**: heat maps of trust and familiarity among all agents, where they spend the day, the world's real stocks and each agent's truth/lie/omission record.
- **Events**: table filterable by agent, action, outcome and day range.

Each run leaves `data/runs/<run_id>/vida.sqlite` (events, memories, state snapshots, relationships) and `logs/<run_id>/events.jsonl` (one line per event). The summary includes the SHA-256 hash of the events: two runs with the same seed and configuration produce the same hash.

Example biography (real fragment from the acceptance run; output is in Spanish):

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

## Structure

```
config/default.yaml   run parameters (everything that affects the result)
src/vida/agents       agent state, personality, needs, beliefs, decision, learning, identity
src/vida/memory       episodic, semantic, social, autobiographical and procedural memory
src/vida/world        places, resources, actions and resolution rules
src/vida/simulation   configuration, RNG, clock, events, engine, life cycle, logging
src/vida/database     SQLAlchemy models and repository (SQLite per run)
src/vida/evaluation   biographies and metrics
tests/                pytest
data/runs/<run_id>/   SQLite database of each run (ignored by git)
logs/<run_id>/        JSONL events of each run (ignored by git)
```
