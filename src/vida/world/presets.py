"""Mundos y poblaciones iniciales predefinidos.

``village_small``: 12 lugares (5 casas, 2 plazas, mercado, escuela, hospital y
dos centros de trabajo) conectados a través de la plaza central. Los agentes
nacen con conocimiento común sobre qué vende cada lugar (creencias ``prior``),
pero no sobre el stock real: eso sólo lo aprenden observando o preguntando.
"""

from __future__ import annotations

import random

from vida.agents.agent import AgentState, KnowledgeItem
from vida.agents.needs import build_needs
from vida.agents.personality import Personality
from vida.simulation.config import RunConfig
from vida.simulation.lifecycle import stage_for_days
from vida.world.locations import Location
from vida.world.world import World, WorldEvent, WorldState

AGENT_NAMES = ["Ana", "Luis", "Sofía", "Mateo", "Valentina", "Diego", "Camila", "Andrés", "Lucía", "Javier"]

COMMON_KNOWLEDGE: dict[str, list[tuple[str, float]]] = {
    # recurso -> [(ubicación, confianza inicial)]
    "bread": [("market", 0.8)],
    "fruit": [("market", 0.6), ("farm", 0.5)],
}


def village_small(cfg: RunConfig) -> WorldState:
    homes = [Location(id=f"home_{i}", name=f"Casa {i}", type="home", adjacent=["plaza"]) for i in range(1, 6)]
    public = [
        Location(id="plaza", name="Plaza central", type="plaza",
                 adjacent=[h.id for h in homes] + ["park", "market", "school", "hospital", "farm", "workshop"]),
        Location(id="park", name="Parque", type="plaza", adjacent=["plaza"]),
        Location(id="market", name="Mercado", type="market", resources={"bread": 30, "fruit": 20},
                 restock={"bread": 30, "fruit": 20}, open_hours=(6, 20), adjacent=["plaza", "farm"]),
        Location(id="school", name="Escuela", type="school", capacity=6, open_hours=(8, 16), adjacent=["plaza"]),
        Location(id="hospital", name="Hospital", type="hospital", resources={"care": 5}, restock={"care": 5},
                 adjacent=["plaza"]),
        Location(id="farm", name="Granja", type="workplace", resources={"fruit": 10}, restock={"fruit": 10},
                 open_hours=(6, 18), adjacent=["plaza", "market"]),
        Location(id="workshop", name="Taller", type="workplace", open_hours=(8, 18), adjacent=["plaza"]),
    ]
    locations = {loc.id: loc for loc in homes + public}
    factor = cfg.world.restock_factor
    for loc in locations.values():
        loc.restock = {r: max(0, int(round(v * factor))) for r, v in loc.restock.items()}
        loc.resources = {r: max(0, int(round(v * factor))) for r, v in loc.resources.items()}
    days = cfg.run.ticks_per_day
    scheduled = []
    for i, day in enumerate(sorted(cfg.world.shortage_days)):
        payload = {"bread": 3} if i % 2 == 0 else {"bread": 0, "fruit": 5}
        scheduled.append(WorldEvent(tick=day * days + 6, kind="shortage", location_id="market", payload=payload))
    return WorldState(
        locations=locations,
        scheduled_events=scheduled,
        economy={"price:bread": 2.0, "price:fruit": 1.0, "price:care": 5.0, "wage": 3.0},
    )


def spawn_agents(cfg: RunConfig, world: World, rng: random.Random) -> dict[str, AgentState]:
    """Crea ``n_agents`` agentes comparables pero distintos, colocados en sus casas."""
    homes = sorted(loc.id for loc in world.locations.values() if loc.type == "home")
    agents: dict[str, AgentState] = {}
    for i in range(cfg.agents.n_agents):
        agent_id = f"a{i + 1:02d}"
        name = AGENT_NAMES[i] if i < len(AGENT_NAMES) else f"Agente {i + 1}"
        home = homes[i % len(homes)]
        age_days = rng.randint(cfg.agents.initial_age_days.min, cfg.agents.initial_age_days.max)
        levels = {need: round(rng.uniform(0.6, 1.0), 3) for need in sorted(cfg.needs)}
        agent = AgentState(
            id=agent_id, name=name,
            age_ticks=age_days * cfg.run.ticks_per_day,
            life_stage=stage_for_days(cfg, age_days),
            personality=Personality.random(rng),
            needs=build_needs(cfg, levels),
            location_id=home, home_id=home,
            money=cfg.agents.starting_money,
            knowledge={
                "job": KnowledgeItem(level=round(rng.uniform(0.0, 0.3), 3), source="initial"),
                "general": KnowledgeItem(level=round(rng.uniform(0.0, 0.3), 3), source="initial"),
            },
        )
        if cfg.agents.initial_honesty is not None:
            agent.identity.core_values["honesty"] = float(cfg.agents.initial_honesty)
        agent.beliefs.known_locations = sorted(
            loc.id for loc in world.locations.values() if loc.type != "home" or loc.id == home
        )
        for resource, places in sorted(COMMON_KNOWLEDGE.items()):
            for location_id, confidence in places:
                agent.beliefs.prior(resource, location_id, confidence)
        world.place_agent(agent_id, home)
        agents[agent_id] = agent
    return agents


PRESETS = {"village_small": village_small}


def build_world(cfg: RunConfig) -> World:
    try:
        factory = PRESETS[cfg.world.preset]
    except KeyError as exc:
        raise ValueError(f"Preset de mundo desconocido: {cfg.world.preset}") from exc
    return World(factory(cfg), ticks_per_day=cfg.run.ticks_per_day)
