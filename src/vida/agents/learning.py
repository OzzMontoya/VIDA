"""Aprendizaje por consecuencias: preferencias, conocimiento y creencias.

Sólo lee el ``ActionOutcome`` (sin ``details["_world"]``). La información que el
agente recibe de otros entra como creencia ``told`` con su procedencia, para
que un fracaso posterior pueda atribuirse a quien la dio.
"""

from __future__ import annotations

from vida.agents.agent import AgentState, KnowledgeItem
from vida.world.actions import ActionOutcome

FORBIDDEN_KEYS = {"_world"}


def learn(agent: AgentState, outcome: ActionOutcome, event_id: str) -> tuple[dict[str, float], list[str]]:
    """Actualiza preferencias, habilidades y creencias. Devuelve (deltas de preferencia, cambios de creencia)."""
    details = {k: v for k, v in outcome.details.items() if k not in FORBIDDEN_KEYS}
    pref_deltas: dict[str, float] = {}
    belief_changes: list[str] = []

    def prefer(subject: str, valence: float, rate: float = 0.2) -> None:
        delta = agent.preference_for(subject).update(valence, rate)
        if delta:
            pref_deltas[subject] = round(pref_deltas.get(subject, 0.0) + delta, 6)

    if outcome.action == "idle":
        return pref_deltas, belief_changes

    # Preferencias: acción, lugar donde ocurrió, recurso y persona implicada.
    prefer(f"action:{outcome.action}", outcome.valence)
    if outcome.action in {"acquire", "work", "study", "seek_care", "rest", "socialize"}:
        prefer(f"loc:{outcome.location_id}", outcome.valence, rate=0.15)
    if outcome.resource and outcome.action in {"consume", "acquire"}:
        prefer(f"res:{outcome.resource}", outcome.valence, rate=0.15)
    if outcome.target_agent and outcome.action in {"socialize", "ask_info", "share_info"}:
        prefer(f"agent:{outcome.target_agent}", outcome.valence, rate=0.15)

    # Conocimiento (habilidades).
    skill, gain = details.get("skill"), details.get("skill_gain")
    if skill and gain:
        item = agent.knowledge.get(skill) or KnowledgeItem(level=0.0, source="experience")
        item.level = min(1.0, round(item.level + float(gain), 6))
        item.tick = outcome.tick
        agent.knowledge[skill] = item

    # Creencias sobre recursos.
    if outcome.action == "acquire" and outcome.resource:
        if outcome.success:
            agent.beliefs.confirm(outcome.resource, outcome.location_id)
            belief_changes.append(f"confirm:{outcome.resource}@{outcome.location_id}")
        elif outcome.kind == "resource_absent":
            agent.beliefs.refute(outcome.resource, outcome.location_id)
            belief_changes.append(f"refute:{outcome.resource}@{outcome.location_id}")
    if outcome.action == "ask_info" and outcome.success and outcome.resource:
        claimed = details.get("claimed_location")
        informant = details.get("informant")
        if claimed and informant:
            honesty = agent.beliefs.model_of(informant).honesty_estimate
            standing = float(details.get("informant_reputation", 0.5))
            confidence = round(min(0.95, 0.3 + 0.4 * honesty + 0.2 * standing) * float(details.get("claimed_confidence", 1.0)), 6)
            agent.beliefs.told(outcome.resource, claimed, by=informant, event_id=event_id,
                               tick=outcome.tick, confidence=confidence)
            belief_changes.append(f"told:{outcome.resource}@{claimed} by {informant}")
    return pref_deltas, belief_changes


def receive_shared_info(receiver: AgentState, outcome: ActionOutcome, event_id: str) -> list[str]:
    """El destinatario de ``share_info`` incorpora la afirmación como creencia ``told``."""
    details = {k: v for k, v in outcome.details.items() if k not in FORBIDDEN_KEYS}
    claimed = details.get("claimed_location")
    if not (outcome.action == "share_info" and outcome.success and outcome.resource and claimed):
        return []
    honesty = receiver.beliefs.model_of(outcome.agent_id).honesty_estimate
    confidence = round(min(0.95, 0.4 + 0.5 * honesty), 6)
    receiver.beliefs.told(outcome.resource, claimed, by=outcome.agent_id, event_id=event_id,
                          tick=outcome.tick, confidence=confidence)
    return [f"told:{outcome.resource}@{claimed} by {outcome.agent_id}"]


def observe(agent: AgentState, location_id: str, resources: dict[str, int], visible_agents: list[str], tick: int) -> list[tuple[str, str, str | None]]:
    """Percepción directa: lo observado sobrescribe rumores.

    Devuelve las creencias *contadas por otro* que la observación desmiente
    (recurso, informante, id del evento en que se contó): llegar a un lugar
    donde prometieron comida y no hallarla es el momento en que se descubre
    un engaño (sección 20), aunque no se llegue a intentar comprar.
    """
    disproved: list[tuple[str, str, str | None]] = []
    for resource in sorted(agent.beliefs.resources):
        belief = agent.beliefs.belief_at(resource, location_id)
        if belief is not None and belief.source == "told" and belief.source_agent and resources.get(resource, 0) <= 0:
            disproved.append((resource, belief.source_agent, belief.source_event_id))
    agent.beliefs.observe_resources(location_id, resources, tick)
    for other in visible_agents:
        agent.beliefs.observe_agent(other, location_id, tick)
    return disproved
