"""Experimento de decisión (sección 19): historias distintas ante la misma situación.

Tras ``ticks`` de vida, se clona el mundo y se coloca a todos los agentes en
una situación idéntica (mismo lugar, hora, necesidades, dinero e inventario).
Cada uno decide con su historia intacta; después decide de nuevo con la
*misma personalidad* pero sin historia (memoria, preferencias, relaciones,
creencias y automodelo en blanco). Se mide:

- diversidad de elecciones entre agentes con historia frente a sin ella
  (entropía y número de elecciones distintas);
- fracción de agentes cuya elección cambia al quitarles la historia: cuánto de
  lo que hacen se debe a lo vivido y no a la personalidad ni a la situación.
"""

from __future__ import annotations

import copy
import math
import random
from collections import Counter
from typing import Any

from vida.agents.agent import AgentState
from vida.experiments.runner import summarize
from vida.experiments.transfer import fresh_mind
from vida.memory.base import AgentMemory
from vida.simulation.config import RunConfig
from vida.simulation.engine import SimulationEngine

SCENARIOS: dict[str, dict[str, Any]] = {
    "plaza_mediodia": {"location": "plaza", "hour": 12, "money": 15.0,
                       "needs": {"hunger": 0.45, "energy": 0.7, "social": 0.5, "health": 0.9, "safety": 0.9, "knowledge": 0.8}},
    "mercado_hambre": {"location": "market", "hour": 10, "money": 10.0,
                       "needs": {"hunger": 0.2, "energy": 0.8, "social": 0.7, "health": 0.9, "safety": 0.9, "knowledge": 0.8}},
    "casa_noche": {"location": None, "hour": 22, "money": 15.0,  # None = su propia casa
                   "needs": {"hunger": 0.7, "energy": 0.3, "social": 0.3, "health": 0.9, "safety": 0.9, "knowledge": 0.8}},
}
KEY_METRICS = ["entropy_history", "entropy_blank", "distinct_history", "distinct_blank", "share_changed", "majority_share_history"]


def blank_mind(agent: AgentState, world_locations: dict[str, Any], rng: random.Random) -> AgentState:
    """Misma personalidad, sin historia: aísla el efecto de lo vivido."""
    new = fresh_mind(agent, world_locations, rng)
    new.personality = agent.personality.model_copy()
    return new


def _entropy(counter: Counter) -> float:
    total = sum(counter.values())
    return round(-sum((c / total) * math.log2(c / total) for c in counter.values() if c), 6) if total else 0.0


def _stage(engine: SimulationEngine, scenario: dict[str, Any]) -> None:
    """Coloca a todos los agentes vivos en la situación del escenario."""
    engine.clock.tick = engine.clock.day * engine.cfg.run.ticks_per_day + scenario["hour"]
    for aid in engine.alive_ids():
        a = engine.agents[aid]
        for need, level in scenario["needs"].items():
            a.needs[need].level = level
        a.money = scenario["money"]
        a.inventory = {}
        loc = scenario["location"] or a.home_id
        engine.world.place_agent(aid, loc)
        a.location_id = loc


def run_decision(cfg: RunConfig, *, seed: int, ticks: int, scenarios: dict[str, dict[str, Any]] | None = None,
                 progress: Any = None) -> list[dict[str, Any]]:
    if cfg.decision.engine != "rules_v1":
        raise ValueError("El experimento de decisión requiere el motor por reglas (clonación determinista)")
    scenarios = scenarios or SCENARIOS
    c = cfg.model_copy(deep=True)
    c.run.seed = seed
    c.run.ticks = ticks
    engine = SimulationEngine(c, run_id=f"exp_decision_{seed}", sha="experiment")
    engine.run(ticks=ticks)
    rows: list[dict[str, Any]] = []
    for name, scenario in sorted(scenarios.items()):
        if progress:
            progress(f"decision: semilla {seed}, escenario {name}")
        with_history = copy.deepcopy(engine)
        _stage(with_history, scenario)
        blank = copy.deepcopy(engine)
        rng = blank.hub.sub("blank")
        for aid in blank.alive_ids():
            blank.agents[aid] = blank_mind(blank.agents[aid], blank.world.locations, rng)
            blank.memories[aid] = AgentMemory(aid, c.memory)
        _stage(blank, scenario)
        choices_h: dict[str, str] = {}
        choices_b: dict[str, str] = {}
        for clone, store in ((with_history, choices_h), (blank, choices_b)):
            for aid in clone.alive_ids():
                ctx = clone._context_for(clone.agents[aid])
                proposal, _ = clone.decision_engine.decide(ctx, random.Random(0))
                store[aid] = proposal.key()
        ch, cb = Counter(choices_h.values()), Counter(choices_b.values())
        changed = [aid for aid in choices_h if choices_h[aid] != choices_b.get(aid)]
        rows.append({
            "variant": name, "seed": seed, "n_agents": len(choices_h),
            "entropy_history": _entropy(ch), "entropy_blank": _entropy(cb),
            "distinct_history": len(ch), "distinct_blank": len(cb),
            "share_changed": round(len(changed) / len(choices_h), 6) if choices_h else 0.0,
            "majority_share_history": round(ch.most_common(1)[0][1] / len(choices_h), 6) if choices_h else 0.0,
            "majority_share_blank": round(cb.most_common(1)[0][1] / len(choices_b), 6) if choices_b else 0.0,
            "choices_history": dict(sorted(choices_h.items())), "choices_blank": dict(sorted(choices_b.items())),
        })
    return rows


def run_decision_experiment(cfg: RunConfig, *, seeds: list[int], ticks: int, progress: Any = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        rows.extend(run_decision(cfg, seed=seed, ticks=ticks, progress=progress))
    return {"name": "decision", "seeds": seeds, "ticks": ticks, "rows": rows, "summary": summarize(rows)}
