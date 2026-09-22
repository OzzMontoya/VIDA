"""Memoria del agente (sección 14).

Un único almacén por agente con registros etiquetados por tipo. La recuperación
combina recencia, importancia y relevancia (solapamiento de etiquetas), al
estilo de Park et al. (2023) pero sin modelos de lenguaje: el contenido es texto
generado por plantillas a partir de hechos objetivos.

Determinismo: los empates se rompen por ``id`` y las etiquetas se guardan
ordenadas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from vida.simulation.config import MemorySection

MemoryKind = Literal["episodic", "semantic", "social", "autobiographical", "procedural"]
MEMORY_KINDS: tuple[MemoryKind, ...] = ("episodic", "semantic", "social", "autobiographical", "procedural")


class MemoryRecord(BaseModel):
    id: str
    agent_id: str
    kind: MemoryKind
    tick: int
    content: str
    importance: float = Field(0.5, ge=0.0, le=1.0)
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source_event_id: str | None = None
    access_count: int = 0
    last_access_tick: int = 0
    confirmations: int = 0
    refutations: int = 0

    def has_tags(self, required: set[str]) -> bool:
        return required.issubset(self.tags)


class AgentMemory:
    """Almacén de memorias de un agente con recuperación puntuada y olvido."""

    def __init__(self, agent_id: str, cfg: MemorySection) -> None:
        self.agent_id = agent_id
        self.cfg = cfg
        self.records: dict[str, MemoryRecord] = {}
        self.forgotten: list[MemoryRecord] = []  # se conservan para evaluación, no para el agente
        self._seq = 0

    # --- escritura ---------------------------------------------------------
    def add(
        self, kind: MemoryKind, tick: int, content: str, *, importance: float, valence: float = 0.0,
        tags: set[str] | list[str] = (), source_event_id: str | None = None,
    ) -> MemoryRecord:
        self._seq += 1
        record = MemoryRecord(
            id=f"{self.agent_id}_m{self._seq:06d}", agent_id=self.agent_id, kind=kind, tick=tick,
            content=content, importance=max(0.0, min(1.0, importance)),
            valence=max(-1.0, min(1.0, valence)), tags=sorted(set(tags)),
            source_event_id=source_event_id, last_access_tick=tick,
        )
        self.records[record.id] = record
        return record

    # --- lectura -----------------------------------------------------------
    def all(self) -> list[MemoryRecord]:
        return [self.records[k] for k in sorted(self.records)]

    def by_kind(self, kind: MemoryKind) -> list[MemoryRecord]:
        return [r for r in self.all() if r.kind == kind]

    def find(self, tags: set[str], kind: MemoryKind | None = None) -> list[MemoryRecord]:
        return [r for r in self.all() if (kind is None or r.kind == kind) and r.has_tags(tags)]

    def score(self, record: MemoryRecord, ctx_tags: set[str], tick: int) -> float:
        w = self.cfg.weights
        recency = self.cfg.recency_decay ** max(0, tick - record.last_access_tick)
        union = set(record.tags) | ctx_tags
        relevance = len(set(record.tags) & ctx_tags) / len(union) if union else 0.0
        return round(w.recency * recency + w.importance * record.importance + w.relevance * relevance, 9)

    def retrieve(self, ctx_tags: set[str], tick: int, k: int | None = None) -> list[MemoryRecord]:
        """Devuelve las ``k`` memorias más relevantes y registra el acceso."""
        k = self.cfg.retrieve_k if k is None else k
        if k <= 0:
            return []
        ranked = sorted(self.all(), key=lambda r: (-self.score(r, ctx_tags, tick), r.id))
        chosen = ranked[:k]
        for record in chosen:
            record.access_count += 1
            record.last_access_tick = tick
        return chosen

    def expectation(self, tags: set[str]) -> float | None:
        """Valencia media de las memorias que contienen todas las etiquetas (o None)."""
        matching = self.find(tags)
        if not matching:
            return None
        return round(sum(r.valence for r in matching) / len(matching), 6)

    # --- consolidación / olvido --------------------------------------------
    def consolidate(self, tick: int, ticks_per_day: int) -> list[str]:
        """Olvida episodios poco importantes y antiguos. Devuelve los ids olvidados."""
        horizon = tick - self.cfg.forget_after_days * ticks_per_day
        kinds = set(self.cfg.forget_kinds)
        forgotten = [
            r.id for r in self.all()
            if r.kind in kinds and r.importance < self.cfg.forget_below and r.tick < horizon
        ]
        for rid in forgotten:
            self.forgotten.append(self.records.pop(rid))
        return forgotten
