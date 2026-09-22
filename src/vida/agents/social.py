"""Relaciones sociales actualizadas por resultados objetivos (secciones 20 y 29).

Este módulo sólo lee ``ActionOutcome``: nunca ``proposal.rationale`` ni la
clave ``details["_world"]``. Así, una mentira no daña la confianza cuando se
dice, sino cuando su consecuencia se manifiesta (el agente engañado actúa sobre
la información y fracasa).
"""

from __future__ import annotations

from vida.agents.agent import AgentState
from vida.world.actions import ActionOutcome

FORBIDDEN_KEYS = {"_world"}


def _pair(a: str, b: str) -> str:
    return f"{a}->{b}"


def update_relationships(agent: AgentState, outcome: ActionOutcome, agents: dict[str, AgentState]) -> dict[str, dict[str, float]]:
    """Ajusta relaciones de ambos participantes y devuelve los deltas por par."""
    deltas: dict[str, dict[str, float]] = {}
    details = {k: v for k, v in outcome.details.items() if k not in FORBIDDEN_KEYS}
    tick = outcome.tick

    def apply(src: AgentState, dst_id: str, **kw: float) -> None:
        """Cambios asintóticos: los incrementos se atenúan al acercarse a 1 y los descensos al acercarse a 0."""
        rel = src.relationship_with(dst_id)
        scaled = {}
        for name, delta in kw.items():
            current = getattr(rel, name)
            scaled[name] = round(delta * ((1.0 - current) if delta > 0 else current) * 2.0, 6)
        changed = rel.adjust(**scaled)
        rel.last_interaction_tick = tick
        if changed:
            deltas[_pair(src.id, dst_id)] = changed

    other_id = outcome.target_agent
    other = agents.get(other_id) if other_id else None

    if outcome.action == "socialize" and other is not None:
        if outcome.success:
            apply(agent, other.id, familiarity=0.05, affection=0.05, trust=0.02)
            apply(other, agent.id, familiarity=0.05, affection=0.04, trust=0.02)
        else:
            apply(agent, other.id, familiarity=0.01, affection=-0.03)
            apply(other, agent.id, familiarity=0.01)

    elif outcome.action == "ask_info" and other is not None:
        if details.get("responded"):
            apply(agent, other.id, familiarity=0.03, trust=0.01)
            apply(other, agent.id, familiarity=0.03)
            agent.beliefs.model_of(other.id).helpfulness_estimate = min(
                1.0, agent.beliefs.model_of(other.id).helpfulness_estimate + 0.05)
        else:
            apply(agent, other.id, familiarity=0.02, affection=-0.01)
            model = agent.beliefs.model_of(other.id)
            model.helpfulness_estimate = max(0.0, model.helpfulness_estimate - 0.05)

    elif outcome.action == "share_info" and other is not None:
        apply(agent, other.id, familiarity=0.03)
        apply(other, agent.id, familiarity=0.03, affection=0.02)

    elif outcome.action == "acquire":
        source_id = details.get("attributed_source_agent")
        if source_id and source_id in agents:
            model = agent.beliefs.model_of(source_id)
            if outcome.success:
                apply(agent, source_id, trust=0.10, affection=0.02)
                model.honesty_estimate = min(1.0, round(model.honesty_estimate + 0.10, 6))
            elif outcome.kind == "resource_absent":
                apply(agent, source_id, trust=-0.15, affection=-0.05)
                model.honesty_estimate = max(0.0, round(model.honesty_estimate - 0.20, 6))

    return deltas


def update_after_disproved_info(agent: AgentState, informant_id: str, agents: dict[str, AgentState]) -> dict[str, dict[str, float]]:
    """Quien prometió algo que no estaba pierde confianza y estima de honestidad (sólo por el hecho observado)."""
    if informant_id not in agents:
        return {}
    rel = agent.relationship_with(informant_id)
    changed = rel.adjust(trust=-0.15 * rel.trust * 2.0, affection=-0.05 * rel.affection * 2.0)
    model = agent.beliefs.model_of(informant_id)
    model.honesty_estimate = max(0.0, round(model.honesty_estimate - 0.20, 6))
    return {_pair(agent.id, informant_id): changed} if changed else {}
