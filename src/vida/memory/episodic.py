"""Memoria episódica: un registro por acción resuelta, con importancia según su impacto.

El contenido se genera por plantilla a partir del ``ActionOutcome`` (hechos
objetivos), nunca a partir de la ``rationale`` del agente.
"""

from __future__ import annotations

from vida.agents.agent import AgentState
from vida.memory.base import AgentMemory, MemoryRecord
from vida.world.actions import ActionOutcome

# Peso extra de importancia por resultado adverso: los fracasos graves se recuerdan más.
NEGATIVE_WEIGHT = {"resource_absent": 0.5, "rejected": 0.4, "insufficient_funds": 0.3, "blocked": 0.2, "no_reply": 0.15}
NEGATIVE_KINDS = set(NEGATIVE_WEIGHT)


def outcome_tags(outcome: ActionOutcome) -> set[str]:
    tags = {f"action:{outcome.action}", f"loc:{outcome.location_id}", f"outcome:{outcome.kind}"}
    if outcome.resource:
        tags.add(f"res:{outcome.resource}")
    if outcome.target_agent:
        tags.add(f"agent:{outcome.target_agent}")
    if outcome.new_location:
        tags.add(f"loc:{outcome.new_location}")
    return tags


def importance_of(outcome: ActionOutcome) -> float:
    impact = sum(abs(v) for v in outcome.need_deltas.values()) + abs(outcome.money_delta) / 10.0
    impact += NEGATIVE_WEIGHT.get(outcome.kind, 0.0)
    if outcome.details.get("attributed_source_agent"):
        impact += 0.2
    return min(1.0, round(impact, 6))


def describe(agent: AgentState, outcome: ActionOutcome, names: dict[str, str]) -> str:
    other = names.get(outcome.target_agent or "", outcome.target_agent or "")
    loc = outcome.location_id
    a, k = outcome.action, outcome.kind
    if a == "move":
        return f"Fui a {outcome.new_location}" if outcome.success else f"No pude entrar a {loc} ({k})"
    if a == "acquire":
        if outcome.success:
            return f"Compré {outcome.resource} en {loc}"
        if k == "resource_absent":
            src = outcome.details.get("attributed_source_agent")
            hint = f", aunque {names.get(src, src)} me había dicho que habría" if src else ""
            return f"No había {outcome.resource} en {loc}{hint}"
        return f"No pude comprar {outcome.resource} en {loc} ({k})"
    if a == "consume":
        return f"Comí {outcome.resource}"
    if a == "work":
        return f"Trabajé en {loc} y gané {outcome.money_delta:.2f}"
    if a == "rest":
        return "Descansé en casa" if outcome.details.get("at_home") else f"Descansé en {loc}"
    if a == "socialize":
        return f"Conversé con {other} en {loc}" if outcome.success else f"{other} no quiso conversar conmigo en {loc}"
    if a == "ask_info":
        if outcome.success:
            return f"{other} me dijo que hay {outcome.resource} en {outcome.details.get('claimed_location')}"
        return f"Pregunté a {other} por {outcome.resource} y no me respondió"
    if a == "share_info":
        return f"Le dije a {other} dónde encontrar {outcome.resource}"
    if a == "study":
        return f"Estudié en {loc}"
    if a == "seek_care":
        return f"Recibí atención en {loc}" if outcome.success else f"No pude pagar la atención en {loc}"
    return f"{a}:{k}"


def encode_outcome(
    memory: AgentMemory, agent: AgentState, outcome: ActionOutcome, event_id: str,
    names: dict[str, str],
) -> MemoryRecord | None:
    """Crea la memoria episódica del resultado; ``idle`` no deja rastro."""
    if outcome.action == "idle":
        return None
    return memory.add(
        "episodic", outcome.tick, describe(agent, outcome, names),
        importance=importance_of(outcome), valence=outcome.valence,
        tags=outcome_tags(outcome), source_event_id=event_id,
    )
