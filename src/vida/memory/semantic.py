"""Memoria semántica: hechos generales del tipo "en X hay Y", con confirmaciones y refutaciones.

Se mantiene un solo registro por hecho; cada nueva evidencia actualiza su
importancia y valencia en lugar de duplicarlo.
"""

from __future__ import annotations

from vida.memory.base import AgentMemory, MemoryRecord


def fact_tags(resource: str, location_id: str) -> set[str]:
    return {"fact:availability", f"res:{resource}", f"loc:{location_id}"}


def record_availability(
    memory: AgentMemory, resource: str, location_id: str, available: bool, tick: int,
    source_event_id: str | None = None,
) -> MemoryRecord:
    """Registra o actualiza el hecho "hay/no hay `resource` en `location_id`"."""
    existing = memory.find(fact_tags(resource, location_id), kind="semantic")
    if existing:
        record = existing[0]
        if available:
            record.confirmations += 1
        else:
            record.refutations += 1
        total = record.confirmations + record.refutations
        record.valence = round((record.confirmations - record.refutations) / total, 6)
        record.importance = min(1.0, round(0.3 + 0.1 * total, 6))
        record.tick = tick
        record.content = _content(resource, location_id, record.confirmations, record.refutations)
        return record
    record = memory.add(
        "semantic", tick, _content(resource, location_id, int(available), int(not available)),
        importance=0.4, valence=1.0 if available else -1.0,
        tags=fact_tags(resource, location_id), source_event_id=source_event_id,
    )
    record.confirmations = int(available)
    record.refutations = int(not available)
    return record


def _content(resource: str, location_id: str, confirmations: int, refutations: int) -> str:
    if confirmations >= refutations:
        return f"En {location_id} suele haber {resource} ({confirmations} veces sí, {refutations} no)"
    return f"En {location_id} no suele haber {resource} ({confirmations} veces sí, {refutations} no)"
