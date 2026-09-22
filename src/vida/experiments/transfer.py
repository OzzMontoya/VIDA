"""Experimento de continuidad y transferencia (secciones 19, 21 y 23).

Se simula una vida hasta un tick de corte. En ese punto se clona el mundo
entero (agentes, memorias, reloj y flujos aleatorios) y, en cada clon, se
sustituye la *mente* del agente estudiado por una versión transferida según la
condición, conservando el *cuerpo* (id, edad, necesidades, dinero, inventario,
posición, reputación). Todos los clones viven después exactamente el mismo
horizonte con los mismos flujos aleatorios, así que las diferencias finales se
deben sólo a lo que se transfirió.

El Índice de Continuidad Individual compara cada clon con (a) la continuación
sin intervención (``completa``) y (b) el agente justo antes del corte. Una
similitud alta es continuidad conductual o informacional, no continuidad
subjetiva (sección 21).
"""

from __future__ import annotations

import copy
import random
from typing import Any

from vida.agents.agent import AgentState, Identity
from vida.agents.selfmodel import SelfModelState
from vida.agents.beliefs import WorldModel
from vida.agents.personality import Personality
from vida.evaluation.metrics import continuity_index
from vida.experiments.runner import summarize
from vida.memory.base import AgentMemory
from vida.simulation.config import RunConfig
from vida.simulation.engine import SimulationEngine
from vida.simulation.events import EventRecord
from vida.world.presets import COMMON_KNOWLEDGE

CONDITIONS = ["completa", "solo_memoria", "solo_conocimientos", "solo_personalidad", "parcial", "memoria_borrada_50", "ninguna"]
# Ablaciones (fase 4): quitar un solo componente y medir cuánta continuidad se pierde.
ABLATIONS = ["sin_relaciones", "sin_preferencias", "sin_automodelo", "sin_identidad", "sin_creencias"]
KEY_METRICS = ["ici_vs_referencia", "ici_vs_previo", "memory", "preferences", "relationships", "decisions", "self_representation"]


def _fresh_beliefs(agent: AgentState, world_locations: dict[str, Any]) -> WorldModel:
    beliefs = WorldModel()
    beliefs.known_locations = sorted(
        loc.id for loc in world_locations.values() if loc.type != "home" or loc.id == agent.home_id
    )
    for resource, places in sorted(COMMON_KNOWLEDGE.items()):
        for location_id, confidence in places:
            if location_id in world_locations:
                beliefs.prior(resource, location_id, confidence)
    return beliefs


def fresh_mind(agent: AgentState, world_locations: dict[str, Any], rng: random.Random) -> AgentState:
    """Mismo cuerpo, mente nueva: personalidad aleatoria, sin recuerdos, preferencias, relaciones ni hábitos."""
    new = agent.model_copy(deep=True)
    new.personality = Personality.random(rng)
    new.preferences = {}
    new.knowledge = {k: v.model_copy(update={"level": 0.0, "source": "reset"}) for k, v in agent.knowledge.items()}
    new.relationships = {}
    new.beliefs = _fresh_beliefs(agent, world_locations)
    new.identity = Identity()
    new.goals = []
    new.decision_history = []
    new.counters = {}
    new.self_model = SelfModelState()
    return new


def apply_transfer(engine: SimulationEngine, agent_id: str, condition: str, rng: random.Random) -> None:
    """Sustituye la mente de ``agent_id`` en ``engine`` según la condición (sección 21)."""
    src = engine.agents[agent_id]
    src_memory = engine.memories[agent_id]
    locations = engine.world.locations
    if condition == "completa":
        return
    if condition == "memoria_borrada_50":
        ids = sorted(src_memory.records)
        for rid in rng.sample(ids, k=len(ids) // 2):
            src_memory.forgotten.append(src_memory.records.pop(rid))
        return
    if condition in ABLATIONS:
        if condition == "sin_relaciones":
            src.relationships = {}
            src.beliefs.others = {}
        elif condition == "sin_preferencias":
            src.preferences = {}
        elif condition == "sin_automodelo":
            src.self_model = SelfModelState()
        elif condition == "sin_identidad":
            src.identity = Identity()
            src.counters = {k: v for k, v in src.counters.items() if k.startswith("visit:")}
        elif condition == "sin_creencias":
            src.beliefs = _fresh_beliefs(src, locations)
        return
    new = fresh_mind(src, locations, rng)
    new_memory = AgentMemory(agent_id, engine.cfg.memory)
    if condition in {"solo_memoria", "parcial"}:
        new_memory = copy.deepcopy(src_memory)
    if condition in {"solo_conocimientos", "parcial"}:
        new.knowledge = copy.deepcopy(src.knowledge)
        new.self_model = copy.deepcopy(src.self_model)  # saber hacer: incluye lo que sabe de sí mismo
    if condition == "solo_personalidad":
        new.personality = src.personality.model_copy()
    if condition == "parcial":
        new.preferences = copy.deepcopy(src.preferences)
    if condition == "ninguna":
        pass
    engine.agents[agent_id] = new
    engine.memories[agent_id] = new_memory


def _events_for(events: list[EventRecord], agent_id: str, start_seq: int) -> list[EventRecord]:
    return [e for e in events if e.agent_id == agent_id and e.seq > start_seq]


def run_transfer(cfg: RunConfig, *, seed: int, split_ticks: int, horizon_ticks: int, agent_id: str = "a01",
                 conditions: list[str] | None = None, progress: Any = None) -> list[dict[str, Any]]:
    """Devuelve una fila por condición con las dimensiones del ICI y los dos índices agregados."""
    if cfg.decision.engine != "rules_v1":
        raise ValueError("El experimento de transferencia requiere el motor por reglas (clonación determinista del mundo)")
    conditions = conditions or CONDITIONS
    c = cfg.model_copy(deep=True)
    c.run.seed = seed
    c.run.ticks = split_ticks + horizon_ticks
    engine = SimulationEngine(c, run_id=f"exp_transfer_{seed}", sha="experiment")
    for _ in range(split_ticks):
        engine.step()
    split_seq = engine._seq
    pre_state = engine.agents[agent_id].model_copy(deep=True)
    pre_memory = copy.deepcopy(engine.memories[agent_id])
    pre_window = [e for e in engine.events if e.agent_id == agent_id and e.tick >= split_ticks - horizon_ticks]
    base = copy.deepcopy(engine)

    outcomes: dict[str, tuple[AgentState, AgentMemory, list[EventRecord]]] = {}
    for condition in conditions:
        if progress:
            progress(f"transfer: semilla {seed}, condición {condition}")
        clone = copy.deepcopy(base)
        apply_transfer(clone, agent_id, condition, clone.hub.sub("transfer", condition))
        for _ in range(horizon_ticks):
            clone.step()
        outcomes[condition] = (clone.agents[agent_id], clone.memories[agent_id], _events_for(clone.events, agent_id, split_seq))

    ref_state, ref_mem, ref_events = outcomes.get("completa") or outcomes[conditions[0]]
    rows = []
    for condition in conditions:
        state, mem, events = outcomes[condition]
        vs_ref = continuity_index(ref_state, ref_mem, ref_events, state, mem, events)
        vs_pre = continuity_index(pre_state, pre_memory, pre_window, state, mem, events)
        rows.append({
            "variant": condition, "seed": seed, "agent_id": agent_id,
            "ici_vs_referencia": vs_ref["ici"], "ici_vs_previo": vs_pre["ici"],
            **{k: v for k, v in vs_ref.items() if k != "ici"},
            **{f"previo_{k}": v for k, v in vs_pre.items() if k != "ici"},
            "alive": 1.0 if state.alive else 0.0,
        })
    return rows


def run_transfer_experiment(cfg: RunConfig, *, seeds: list[int], split_ticks: int, horizon_ticks: int,
                            agent_id: str = "a01", conditions: list[str] | None = None, progress: Any = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        rows.extend(run_transfer(cfg, seed=seed, split_ticks=split_ticks, horizon_ticks=horizon_ticks,
                                 agent_id=agent_id, conditions=conditions, progress=progress))
    return {"name": "transfer", "seeds": seeds, "split_ticks": split_ticks, "horizon_ticks": horizon_ticks,
            "agent_id": agent_id, "rows": rows, "summary": summarize(rows)}
