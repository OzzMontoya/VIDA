"""Registro canónico de eventos (sección 28 del documento).

Cada acción de un agente produce un ``EventRecord`` con: tiempo simulado,
percepción, estado previo, memorias recuperadas, decisión (con todos los
puntajes), propuesta, resultado objetivo, memorias creadas, cambios sociales y
de preferencias, estado posterior y cambios en el mundo. Muertes, cambios de
etapa y eventos exógenos del mundo también se registran.

``hash_payload`` excluye ``run_id`` para que dos corridas con la misma semilla
produzcan hashes idénticos aunque tengan identificadores distintos.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from vida.agents.agent import AgentStateSummary
from vida.world.actions import ActionOutcome, ActionProposal, PerceptionSnapshot

EventType = Literal["action", "death", "stage_change", "world_event"]


class DecisionRecord(BaseModel):
    engine: str
    chosen: str
    scores: dict[str, float] = Field(default_factory=dict)
    n_candidates: int = 0
    rationale: str = ""


class EventRecord(BaseModel):
    event_id: str
    run_id: str
    seq: int
    tick: int
    day: int
    hour: int
    event_type: EventType
    agent_id: str
    perception: PerceptionSnapshot | None = None
    state_before: AgentStateSummary | None = None
    retrieved_memory_ids: list[str] = Field(default_factory=list)
    decision: DecisionRecord | None = None
    proposal: ActionProposal | None = None
    outcome: ActionOutcome | None = None
    memories_created: list[str] = Field(default_factory=list)
    relationship_deltas: dict[str, dict[str, float]] = Field(default_factory=dict)
    reputation_deltas: dict[str, float] = Field(default_factory=dict)
    preference_deltas: dict[str, float] = Field(default_factory=dict)
    belief_changes: list[str] = Field(default_factory=list)
    state_after: AgentStateSummary | None = None
    world_delta: dict[str, Any] = Field(default_factory=dict)
    note: str = ""

    def to_json_line(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)

    def hash_payload(self) -> str:
        data = self.model_dump(mode="json", exclude={"run_id"})
        return json.dumps(data, sort_keys=True, ensure_ascii=False)


def events_digest(events: list[EventRecord]) -> str:
    """SHA-256 acumulado sobre los payloads (sin run_id) en orden de secuencia."""
    h = hashlib.sha256()
    for ev in events:
        h.update(ev.hash_payload().encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def make_event_id(tick: int, agent_id: str, seq: int) -> str:
    """Identificador determinista: no depende del run_id ni del reloj real."""
    return f"e{seq:07d}_t{tick:06d}_{agent_id}"
