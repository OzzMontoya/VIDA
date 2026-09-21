"""Memoria social: registros de interacciones con otros agentes, para ambos participantes."""

from __future__ import annotations

from vida.memory.base import AgentMemory, MemoryRecord
from vida.world.actions import ActionOutcome

SOCIAL_ACTIONS = {"socialize", "ask_info", "share_info"}


def encode_for_initiator(memory: AgentMemory, outcome: ActionOutcome, event_id: str, names: dict[str, str]) -> MemoryRecord | None:
    if outcome.action not in SOCIAL_ACTIONS or not outcome.target_agent:
        return None
    other = names.get(outcome.target_agent, outcome.target_agent)
    if outcome.action == "socialize":
        content = f"Pasé un rato con {other}" if outcome.success else f"{other} me rechazó"
        importance = 0.3 if outcome.success else 0.5
    elif outcome.action == "ask_info":
        content = f"{other} me ayudó con información sobre {outcome.resource}" if outcome.success else f"{other} no quiso ayudarme"
        importance = 0.3 if outcome.success else 0.45
    else:
        content = f"Compartí información con {other}"
        importance = 0.25
    return memory.add(
        "social", outcome.tick, content, importance=importance, valence=outcome.valence,
        tags={f"agent:{outcome.target_agent}", f"action:{outcome.action}", f"outcome:{outcome.kind}"},
        source_event_id=event_id,
    )


def encode_for_partner(memory: AgentMemory, outcome: ActionOutcome, initiator_name: str, event_id: str) -> MemoryRecord | None:
    """Memoria del otro participante: lo que le hicieron, no lo que pretendían."""
    if outcome.action not in SOCIAL_ACTIONS or not outcome.target_agent:
        return None
    if outcome.action == "socialize":
        content = f"{initiator_name} conversó conmigo" if outcome.success else f"Rechacé conversar con {initiator_name}"
        valence = 0.4 if outcome.success else -0.1
    elif outcome.action == "ask_info":
        content = f"{initiator_name} me preguntó por {outcome.resource}"
        valence = 0.1
    else:
        content = f"{initiator_name} me dijo dónde hay {outcome.resource}"
        valence = 0.2
    return memory.add(
        "social", outcome.tick, content, importance=0.25, valence=valence,
        tags={f"agent:{outcome.agent_id}", f"action:{outcome.action}", "role:partner"},
        source_event_id=event_id,
    )


def encode_death_of(memory: AgentMemory, deceased_name: str, deceased_id: str, tick: int, event_id: str) -> MemoryRecord:
    return memory.add(
        "social", tick, f"{deceased_name} murió", importance=0.9, valence=-0.8,
        tags={f"agent:{deceased_id}", "event:death"}, source_event_id=event_id,
    )
