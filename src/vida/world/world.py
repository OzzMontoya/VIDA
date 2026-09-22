"""El mundo artificial: estado objetivo y operaciones de autoridad.

``WorldState`` es la verdad. ``World`` la envuelve y ofrece las tres
operaciones que usa el motor: ``perceive`` (qué ve un agente), ``legal_actions``
(qué puede intentar) y ``resolve`` (qué ocurre realmente). Nada fuera de este
paquete muta ``WorldState``.

``info_ledger`` guarda, por evento, la intención y veracidad de cada mensaje
entre agentes. Es conocimiento del mundo, no del agente: se usa para
reputación y evaluación, nunca para decidir.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from pydantic import BaseModel, Field

from vida.agents.agent import AgentState
from vida.world import rules
from vida.world.actions import ActionKind, ActionOutcome, ActionProposal, PerceptionSnapshot
from vida.world.locations import Location


class WorldEvent(BaseModel):
    """Evento exógeno programado (escasez, reposición extraordinaria...)."""

    tick: int
    kind: str
    location_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WorldState(BaseModel):
    tick: int = 0
    locations: dict[str, Location]
    agent_locations: dict[str, str] = Field(default_factory=dict)
    scheduled_events: list[WorldEvent] = Field(default_factory=list)
    economy: dict[str, float] = Field(default_factory=dict)  # "price:bread", "wage"
    info_ledger: dict[str, dict[str, Any]] = Field(default_factory=dict)
    restock_hour: int = 6


class World:
    def __init__(self, state: WorldState, ticks_per_day: int = 24) -> None:
        self.state = state
        self.ticks_per_day = ticks_per_day
        self._distances: dict[tuple[str, str], int] = {}

    # --- consultas ---------------------------------------------------------
    @property
    def locations(self) -> dict[str, Location]:
        return self.state.locations

    def location_of(self, agent_id: str) -> str | None:
        return self.state.agent_locations.get(agent_id)

    def agents_at(self, location_id: str) -> list[str]:
        return sorted(a for a, loc in self.state.agent_locations.items() if loc == location_id)

    def price(self, resource: str, location_id: str | None = None) -> float:
        """Precio del recurso en un lugar (los lugares pueden sobrescribir la economía global)."""
        if location_id is not None:
            loc = self.locations.get(location_id)
            if loc is not None and resource in loc.prices:
                return float(loc.prices[resource])
        return float(self.state.economy.get(f"price:{resource}", 0.0))

    def wage(self, location_id: str | None = None) -> float:
        if location_id is not None:
            loc = self.locations.get(location_id)
            if loc is not None and loc.wage is not None:
                return float(loc.wage)
        return float(self.state.economy.get("wage", 1.0))

    def truth_locations(self, resource: str) -> list[str]:
        """Ubicaciones donde el recurso existe realmente ahora mismo."""
        return sorted(loc.id for loc in self.locations.values() if loc.stock(resource) > 0)

    def public_location_info(self) -> dict[str, dict[str, Any]]:
        """Conocimiento común: tipo y horario de cada lugar (no su stock)."""
        return {
            loc_id: {
                "type": loc.type, "open_hours": loc.open_hours,
                "prices": {r: self.price(r, loc_id) for r in sorted(set(loc.restock) | set(loc.prices))},
                "wage": self.wage(loc_id) if loc.type == "workplace" else None,
                "work_energy": loc.work_energy,
            }
            for loc_id, loc in sorted(self.locations.items())
        }

    def distance(self, a: str, b: str) -> int:
        if a == b:
            return 0
        key = (a, b)
        if key in self._distances:
            return self._distances[key]
        seen = {a}
        queue: deque[tuple[str, int]] = deque([(a, 0)])
        result = 10_000
        while queue:
            node, d = queue.popleft()
            if node == b:
                result = d
                break
            for nxt in sorted(self.locations[node].adjacent):
                if nxt not in seen and nxt in self.locations:
                    seen.add(nxt)
                    queue.append((nxt, d + 1))
        self._distances[key] = result
        self._distances[(b, a)] = result
        return result

    # --- percepción --------------------------------------------------------
    def perceive(self, agent: AgentState, agents: dict[str, AgentState], tick: int) -> PerceptionSnapshot:
        loc_id = self.location_of(agent.id)
        if loc_id is None:
            raise KeyError(f"El agente {agent.id} no está colocado en el mundo")
        loc = self.locations[loc_id]
        hour = tick % self.ticks_per_day
        visible = [
            other for other in self.agents_at(loc_id)
            if other != agent.id and other in agents and agents[other].alive
        ]
        resources = {r: s for r, s in sorted(loc.resources.items())}
        prices = {r: self.price(r, loc_id) for r in resources if self.price(r, loc_id) > 0}
        return PerceptionSnapshot(
            tick=tick, hour=hour, location_id=loc_id, location_type=loc.type,
            is_open=loc.is_open(hour), visible_agents=visible,
            visible_resources=resources, prices=prices,
        )

    def legal_actions(self, agent: AgentState, perception: PerceptionSnapshot) -> list[ActionKind]:
        return rules.legal_actions(self, agent, perception)

    # --- resolución (única mutación del mundo por acción) -------------------
    def resolve(
        self, agent: AgentState, proposal: ActionProposal, agents: dict[str, AgentState],
        rng: random.Random, tick: int, event_id: str,
    ) -> ActionOutcome:
        ctx = rules.ResolveContext(
            agents=agents, tick=tick, hour=tick % self.ticks_per_day, event_id=event_id, rng=rng,
        )
        return rules.resolve(self, agent, proposal, ctx)

    # --- eventos exógenos --------------------------------------------------
    def apply_scheduled_events(self, tick: int) -> list[dict[str, Any]]:
        """Reposición diaria y eventos programados. Devuelve los cambios aplicados."""
        deltas: list[dict[str, Any]] = []
        self.state.tick = tick
        if tick % self.ticks_per_day == self.state.restock_hour:
            for loc_id, loc in sorted(self.locations.items()):
                changes = loc.apply_restock()
                if changes:
                    deltas.append({"kind": "restock", "location_id": loc_id, "changes": changes})
        for ev in [e for e in self.state.scheduled_events if e.tick == tick]:
            if ev.kind == "shortage" and ev.location_id in self.locations:
                loc = self.locations[ev.location_id]
                for resource, amount in sorted(ev.payload.items()):
                    loc.resources[resource] = int(amount)
                deltas.append({"kind": "shortage", "location_id": ev.location_id, "set": dict(ev.payload)})
            elif ev.kind == "bonus" and ev.location_id in self.locations:
                loc = self.locations[ev.location_id]
                for resource, amount in sorted(ev.payload.items()):
                    loc.resources[resource] = loc.stock(resource) + int(amount)
                deltas.append({"kind": "bonus", "location_id": ev.location_id, "added": dict(ev.payload)})
        return deltas

    # --- reputación (campo del agente escrito por el mundo) ----------------
    def update_reputation(self, agent: AgentState, outcome: ActionOutcome, agents: dict[str, AgentState]) -> dict[str, float]:
        """Ajusta reputaciones según hechos objetivos y devuelve los deltas por agente."""
        deltas: dict[str, float] = {}

        def bump(target: AgentState, delta: float) -> None:
            before = target.reputation
            target.reputation = max(0.0, min(1.0, target.reputation + delta))
            real = round(target.reputation - before, 6)
            if real:
                deltas[target.id] = round(deltas.get(target.id, 0.0) + real, 6)

        world_info = outcome.details.get("_world", {})
        if outcome.action == "work" and outcome.success:
            bump(agent, 0.01)
        source_id = outcome.details.get("attributed_source_agent")
        if outcome.action == "acquire" and source_id in agents:
            source = agents[source_id]
            if outcome.success:
                bump(source, 0.02)
            elif outcome.kind == "resource_absent" and world_info.get("attributed_lie"):
                # Engaño descubierto por sus consecuencias: la reputación cae.
                bump(source, -0.05)
        return deltas

    def penalize_disproved(self, informant_id: str, source_event_id: str | None, agents: dict[str, AgentState]) -> dict[str, float]:
        """Si el libro de información registra que el mensaje fue engañoso, cae la reputación de la fuente."""
        ledger = self.state.info_ledger.get(source_event_id or "", {})
        source = agents.get(informant_id)
        if source is None or not ledger.get("deceptive"):
            return {}
        before = source.reputation
        source.reputation = max(0.0, min(1.0, source.reputation - 0.05))
        real = round(source.reputation - before, 6)
        return {source.id: real} if real else {}

    # --- colocación --------------------------------------------------------
    def place_agent(self, agent_id: str, location_id: str) -> None:
        if location_id not in self.locations:
            raise KeyError(location_id)
        self.state.agent_locations[agent_id] = location_id

    def remove_agent(self, agent_id: str) -> None:
        self.state.agent_locations.pop(agent_id, None)
