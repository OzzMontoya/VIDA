"""Generaciones (sección 18): nacimientos, herencia parcial y transmisión cultural.

Cuando la población viva está por debajo del tope y toca día de revisión, nace
un hijo de un adulto vivo elegido con el RNG de la corrida. El hijo:

- hereda parte de la personalidad del progenitor (mezcla con azar, ``inheritance``);
- nace con la edad de inicio configurada (adolescencia por defecto: puede
  moverse, estudiar y trabajar a media paga) en la casa del progenitor;
- recibe un tercio del dinero del progenitor;
- recibe como creencias *contadas por el progenitor* los hechos semánticos que
  éste recuerda (transmisión cultural: pueden ser ciertos o no);
- empieza con un vínculo familiar mutuo (familiaridad, afecto y confianza altos).

Todo queda registrado con un evento ``birth``; ``parent_id`` y ``generation``
permiten medir después qué se transmite y qué no.
"""

from __future__ import annotations

import random

from vida.agents.agent import AgentState, KnowledgeItem
from vida.agents.needs import build_needs
from vida.agents.personality import Personality
from vida.memory.base import AgentMemory
from vida.simulation.config import RunConfig
from vida.simulation.lifecycle import stage_for_days
from vida.world.presets import COMMON_KNOWLEDGE
from vida.world.world import World

CHILD_NAMES = ["Nova", "Iker", "Zoe", "Bruno", "Mía", "Leo", "Alba", "Gael", "Nora", "Dani", "Vera", "Tomás",
               "Iris", "Adrián", "Luna", "Hugo", "Sara", "Pablo", "Elena", "Marco"]


def _blend(parent: float, rng: random.Random, inheritance: float) -> float:
    return round(max(0.05, min(0.95, inheritance * parent + (1.0 - inheritance) * rng.uniform(0.1, 0.9))), 3)


def inherited_personality(parent: Personality, rng: random.Random, inheritance: float) -> Personality:
    return Personality(**{k: _blend(v, rng, inheritance) for k, v in parent.model_dump().items()})


def eligible_parents(agents: dict[str, AgentState], min_money: float) -> list[str]:
    return sorted(aid for aid, a in agents.items()
                  if a.alive and a.life_stage in {"youth", "adulthood"} and a.money >= min_money)


def make_child(cfg: RunConfig, world: World, parent: AgentState, parent_memory: AgentMemory, child_id: str,
               name: str, tick: int, rng: random.Random) -> AgentState:
    lc = cfg.lifecycle
    age_days = lc.birth_age_days
    levels = {need: 1.0 for need in cfg.needs}
    child = AgentState(
        id=child_id, name=name, age_ticks=age_days * cfg.run.ticks_per_day,
        life_stage=stage_for_days(cfg, age_days),
        personality=inherited_personality(parent.personality, rng, lc.inheritance),
        needs=build_needs(cfg, levels), location_id=parent.home_id, home_id=parent.home_id,
        money=round(max(parent.money / 3, min(lc.birth_min_money, parent.money)), 6),
        knowledge={
            "job": KnowledgeItem(level=0.0, source="birth"),
            "general": KnowledgeItem(level=round(parent.knowledge_level("general") * 0.3, 6), source="parent"),
        },
        parent_id=parent.id, generation=parent.generation + 1, birth_tick=tick,
    )
    child.beliefs.known_locations = sorted(
        loc.id for loc in world.locations.values() if loc.type != "home" or loc.id == parent.home_id
    )
    for resource, places in sorted(COMMON_KNOWLEDGE.items()):
        for location_id, confidence in places:
            if location_id in world.locations:
                child.beliefs.prior(resource, location_id, confidence)
    # Transmisión cultural: lo que el progenitor "sabe" pasa como algo contado, verdadero o no.
    for rec in parent_memory.by_kind("semantic"):
        res = next((t[4:] for t in rec.tags if t.startswith("res:")), None)
        loc = next((t[4:] for t in rec.tags if t.startswith("loc:")), None)
        if res and loc and rec.valence > 0:
            child.beliefs.told(res, loc, by=parent.id, event_id=None, tick=tick, confidence=0.6)
    child.relationship_with(parent.id).adjust(familiarity=0.5, affection=0.3, trust=0.2)
    parent.relationship_with(child.id).adjust(familiarity=0.5, affection=0.3, trust=0.2)
    parent.money = round(parent.money - child.money, 6)
    return child


def next_child_id(agents: dict[str, AgentState]) -> str:
    n = max(int(aid[1:]) for aid in agents) + 1
    return f"a{n:02d}"


def child_name(agents: dict[str, AgentState], parent: AgentState) -> str:
    used = {a.name for a in agents.values()}
    for base in CHILD_NAMES:
        if base not in used:
            return base
    return f"{parent.name} II"
