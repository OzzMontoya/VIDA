"""Memoria procedimental: registro de habilidades adquiridas y su progreso."""

from __future__ import annotations

from vida.agents.agent import AgentState
from vida.memory.base import AgentMemory, MemoryRecord

SKILL_LABELS = {"job": "oficio", "general": "conocimientos generales"}


def encode_skill_gain(
    memory: AgentMemory, agent: AgentState, skill: str, gain: float, tick: int, event_id: str | None,
) -> MemoryRecord | None:
    """Actualiza (o crea) el registro de progreso de una habilidad."""
    if gain <= 0:
        return None
    level = agent.knowledge_level(skill)
    label = SKILL_LABELS.get(skill, skill)
    existing = memory.find({"skill:" + skill}, kind="procedural")
    if existing:
        record = existing[0]
        record.confirmations += 1
        record.tick = tick
        record.content = f"Mi nivel de {label} es {level:.2f} tras {record.confirmations} prácticas"
        record.importance = min(1.0, round(0.3 + 0.02 * record.confirmations, 6))
        return record
    record = memory.add(
        "procedural", tick, f"Mi nivel de {label} es {level:.2f} tras 1 práctica",
        importance=0.3, valence=0.2, tags={"skill:" + skill}, source_event_id=event_id,
    )
    record.confirmations = 1
    return record
