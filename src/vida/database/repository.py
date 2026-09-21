"""Repositorio de corridas: escritura durante la simulación y lectura para evaluación.

Un archivo SQLite por corrida en ``data/runs/<run_id>/vida.sqlite``. Los
eventos se acumulan en memoria y se escriben por lotes (``flush``) para no
pagar un commit por evento.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from vida.agents.agent import AgentState
from vida.database.models import (
    AgentORM, AgentStateHistoryORM, Base, EventORM, MemoryORM, RelationshipORM, RunORM,
)
from vida.memory.base import MemoryRecord
from vida.simulation.events import EventRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sqlite_url(path: str | Path) -> str:
    return f"sqlite:///{Path(path).as_posix()}"


class RunRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(sqlite_url(self.db_path), future=True)
        Base.metadata.create_all(self.engine)
        self._pending_events: list[EventORM] = []

    def close(self) -> None:
        self.flush()
        self.engine.dispose()

    # --- escritura ---------------------------------------------------------
    def create_run(self, run_id: str, *, seed: int, config_hash: str, config_json: str,
                   git_sha: str, code_version: str) -> None:
        with Session(self.engine) as s:
            s.merge(RunORM(run_id=run_id, seed=seed, config_hash=config_hash, config_json=config_json,
                           git_sha=git_sha, code_version=code_version, started_at=utc_now()))
            s.commit()

    def save_agents(self, run_id: str, agents: dict[str, AgentState]) -> None:
        with Session(self.engine) as s:
            for aid in sorted(agents):
                a = agents[aid]
                s.merge(AgentORM(run_id=run_id, agent_id=aid, name=a.name, home_id=a.home_id,
                                 initial_age_ticks=a.age_ticks, personality_json=a.personality.model_dump_json()))
            s.commit()

    def record_death(self, run_id: str, agent_id: str, tick: int, reason: str) -> None:
        with Session(self.engine) as s:
            row = s.get(AgentORM, (run_id, agent_id))
            if row is not None:
                row.death_tick, row.death_reason = tick, reason
                s.commit()

    def save_event(self, event: EventRecord) -> None:
        outcome = event.outcome
        self._pending_events.append(EventORM(
            run_id=event.run_id, event_id=event.event_id, seq=event.seq, tick=event.tick,
            agent_id=event.agent_id, event_type=event.event_type,
            action_kind=outcome.action if outcome else None,
            outcome_kind=outcome.kind if outcome else None,
            success=outcome.success if outcome else None,
            payload_json=event.to_json_line(),
        ))
        if len(self._pending_events) >= 500:
            self.flush()

    def flush(self) -> None:
        if not self._pending_events:
            return
        with Session(self.engine) as s:
            s.add_all(self._pending_events)
            s.commit()
        self._pending_events = []

    def save_memories(self, run_id: str, agent_id: str, records: list[MemoryRecord], forgotten: list[MemoryRecord]) -> None:
        with Session(self.engine) as s:
            for rec, gone in [(r, False) for r in records] + [(r, True) for r in forgotten]:
                s.merge(MemoryORM(run_id=run_id, memory_id=rec.id, agent_id=agent_id, kind=rec.kind, tick=rec.tick,
                                  content=rec.content, importance=rec.importance, valence=rec.valence,
                                  forgotten=gone, payload_json=rec.model_dump_json()))
            s.commit()

    def snapshot_states(self, run_id: str, tick: int, agents: dict[str, AgentState]) -> None:
        with Session(self.engine) as s:
            for aid in sorted(agents):
                a = agents[aid]
                s.add(AgentStateHistoryORM(run_id=run_id, agent_id=aid, tick=tick, state_json=a.model_dump_json()))
                for other, rel in sorted(a.relationships.items()):
                    s.add(RelationshipORM(run_id=run_id, tick=tick, from_id=aid, to_id=other, trust=rel.trust,
                                          affection=rel.affection, familiarity=rel.familiarity))
            s.commit()

    def finish_run(self, run_id: str, *, n_ticks: int, n_events: int, events_sha256: str, summary: dict[str, Any]) -> None:
        self.flush()
        with Session(self.engine) as s:
            row = s.get(RunORM, run_id)
            if row is None:
                raise KeyError(run_id)
            row.finished_at = utc_now()
            row.n_ticks, row.n_events, row.events_sha256 = n_ticks, n_events, events_sha256
            row.summary_json = json.dumps(summary, sort_keys=True, ensure_ascii=False)
            s.commit()

    # --- lectura -----------------------------------------------------------
    def run_meta(self, run_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as s:
            row = s.get(RunORM, run_id)
            if row is None:
                return None
            return {c.name: getattr(row, c.name) for c in RunORM.__table__.columns}

    def list_run_ids(self) -> list[str]:
        with Session(self.engine) as s:
            return sorted(s.scalars(select(RunORM.run_id)).all())

    def agents_meta(self, run_id: str) -> dict[str, dict[str, Any]]:
        with Session(self.engine) as s:
            rows = s.scalars(select(AgentORM).where(AgentORM.run_id == run_id).order_by(AgentORM.agent_id)).all()
            return {r.agent_id: {c.name: getattr(r, c.name) for c in AgentORM.__table__.columns} for r in rows}

    def events_for_agent(self, run_id: str, agent_id: str) -> list[EventRecord]:
        self.flush()
        with Session(self.engine) as s:
            rows = s.scalars(
                select(EventORM).where(EventORM.run_id == run_id, EventORM.agent_id == agent_id).order_by(EventORM.seq)
            ).all()
            return [EventRecord.model_validate_json(r.payload_json) for r in rows]

    def all_events(self, run_id: str) -> list[EventRecord]:
        self.flush()
        with Session(self.engine) as s:
            rows = s.scalars(select(EventORM).where(EventORM.run_id == run_id).order_by(EventORM.seq)).all()
            return [EventRecord.model_validate_json(r.payload_json) for r in rows]

    def memories_for(self, run_id: str, agent_id: str, include_forgotten: bool = False) -> list[MemoryRecord]:
        with Session(self.engine) as s:
            stmt = select(MemoryORM).where(MemoryORM.run_id == run_id, MemoryORM.agent_id == agent_id)
            if not include_forgotten:
                stmt = stmt.where(MemoryORM.forgotten.is_(False))
            rows = s.scalars(stmt.order_by(MemoryORM.memory_id)).all()
            return [MemoryRecord.model_validate_json(r.payload_json) for r in rows]

    def forgotten_count(self, run_id: str, agent_id: str) -> int:
        with Session(self.engine) as s:
            rows = s.scalars(select(MemoryORM.memory_id).where(
                MemoryORM.run_id == run_id, MemoryORM.agent_id == agent_id, MemoryORM.forgotten.is_(True))).all()
            return len(rows)

    def state_history(self, run_id: str, agent_id: str) -> list[tuple[int, AgentState]]:
        with Session(self.engine) as s:
            rows = s.scalars(select(AgentStateHistoryORM).where(
                AgentStateHistoryORM.run_id == run_id, AgentStateHistoryORM.agent_id == agent_id,
            ).order_by(AgentStateHistoryORM.tick, AgentStateHistoryORM.id)).all()
            return [(r.tick, AgentState.model_validate_json(r.state_json)) for r in rows]
