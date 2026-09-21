"""Modelo del mundo *creído* por el agente.

Este módulo nunca contiene la verdad del mundo. Las creencias provienen de la
observación directa (``observed``, confianza 1.0) o de lo que otros agentes le
dijeron (``told``). El agente actúa sobre ellas y el mundo puede refutarlas.
Rastrear ``source_agent`` y ``source_event_id`` permite atribuir el resultado de
una acción a la información recibida y ajustar la confianza en quien la dio.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BeliefSource = Literal["observed", "told", "prior"]


class ResourceBelief(BaseModel):
    resource: str
    location_id: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    source: BeliefSource = "observed"
    source_agent: str | None = None
    source_event_id: str | None = None
    tick: int = 0


class OtherAgentModel(BaseModel):
    """Lo que el agente cree sobre otro agente (no lo que el otro es)."""

    agent_id: str
    honesty_estimate: float = Field(0.5, ge=0.0, le=1.0)
    helpfulness_estimate: float = Field(0.5, ge=0.0, le=1.0)
    last_seen_tick: int | None = None
    last_seen_location: str | None = None


class WorldModel(BaseModel):
    # recurso -> ubicación -> creencia
    resources: dict[str, dict[str, ResourceBelief]] = Field(default_factory=dict)
    others: dict[str, OtherAgentModel] = Field(default_factory=dict)
    known_locations: list[str] = Field(default_factory=list)

    # --- observación -------------------------------------------------------
    def observe_resources(self, location_id: str, resources: dict[str, int], tick: int) -> None:
        """Lo observado sobrescribe lo contado. Ausencia observada borra la creencia."""
        for resource, stock in sorted(resources.items()):
            if stock > 0:
                self.resources.setdefault(resource, {})[location_id] = ResourceBelief(
                    resource=resource, location_id=location_id, confidence=1.0,
                    source="observed", tick=tick,
                )
        for resource in sorted(self.resources):
            if location_id in self.resources[resource] and resources.get(resource, 0) <= 0:
                del self.resources[resource][location_id]

    def observe_agent(self, other_id: str, location_id: str, tick: int) -> None:
        model = self.model_of(other_id)
        model.last_seen_tick = tick
        model.last_seen_location = location_id

    # --- información recibida ----------------------------------------------
    def told(
        self, resource: str, location_id: str, *, by: str, event_id: str | None,
        tick: int, confidence: float = 0.7,
    ) -> ResourceBelief:
        current = self.resources.get(resource, {}).get(location_id)
        if current is not None and current.source == "observed" and current.tick >= tick:
            return current  # una observación igual de reciente pesa más que un rumor
        belief = ResourceBelief(
            resource=resource, location_id=location_id, confidence=confidence,
            source="told", source_agent=by, source_event_id=event_id, tick=tick,
        )
        self.resources.setdefault(resource, {})[location_id] = belief
        return belief

    def prior(self, resource: str, location_id: str, confidence: float, tick: int = 0) -> None:
        """Conocimiento común inicial (p. ej. "el mercado vende pan")."""
        self.resources.setdefault(resource, {})[location_id] = ResourceBelief(
            resource=resource, location_id=location_id, confidence=confidence,
            source="prior", tick=tick,
        )

    # --- consulta y corrección ---------------------------------------------
    def best_location(self, resource: str) -> ResourceBelief | None:
        candidates = self.resources.get(resource, {})
        if not candidates:
            return None
        return max(candidates.values(), key=lambda b: (b.confidence, b.tick, b.location_id))

    def belief_at(self, resource: str, location_id: str) -> ResourceBelief | None:
        return self.resources.get(resource, {}).get(location_id)

    def refute(self, resource: str, location_id: str) -> None:
        belief = self.belief_at(resource, location_id)
        if belief is None:
            return
        belief.confidence = round(belief.confidence * 0.3, 6)
        if belief.confidence < 0.15:
            del self.resources[resource][location_id]

    def confirm(self, resource: str, location_id: str) -> None:
        belief = self.belief_at(resource, location_id)
        if belief is not None:
            belief.confidence = min(1.0, round(belief.confidence + 0.2, 6))

    def model_of(self, other_id: str) -> OtherAgentModel:
        model = self.others.get(other_id)
        if model is None:
            model = OtherAgentModel(agent_id=other_id)
            self.others[other_id] = model
        return model
