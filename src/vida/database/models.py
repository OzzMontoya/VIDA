"""Modelos SQLAlchemy 2.0 para la base SQLite de cada corrida.

Las entidades ricas (evento, memoria, estado) se guardan como JSON completo
junto a columnas indexables. Así la base sirve tanto para reconstruir
biografías como para análisis con Pandas sin acoplar el esquema a cada campo.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RunORM(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seed: Mapped[int] = mapped_column(Integer)
    config_hash: Mapped[str] = mapped_column(String(64))
    config_json: Mapped[str] = mapped_column(Text)
    git_sha: Mapped[str] = mapped_column(String(64))
    code_version: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[str] = mapped_column(String(32))
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    n_ticks: Mapped[int] = mapped_column(Integer, default=0)
    n_events: Mapped[int] = mapped_column(Integer, default=0)
    events_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentORM(Base):
    __tablename__ = "agents"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    home_id: Mapped[str] = mapped_column(String(32))
    initial_age_ticks: Mapped[int] = mapped_column(Integer)
    personality_json: Mapped[str] = mapped_column(Text)
    death_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    death_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EventORM(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_run_agent_tick", "run_id", "agent_id", "tick"),)

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer)
    tick: Mapped[int] = mapped_column(Integer)
    agent_id: Mapped[str] = mapped_column(String(16))
    event_type: Mapped[str] = mapped_column(String(16))
    action_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    outcome_kind: Mapped[str | None] = mapped_column(String(24), nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)


class MemoryORM(Base):
    __tablename__ = "memories"
    __table_args__ = (Index("ix_memories_run_agent", "run_id", "agent_id"),)

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    memory_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(20))
    tick: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float)
    valence: Mapped[float] = mapped_column(Float)
    forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_json: Mapped[str] = mapped_column(Text)


class RelationshipORM(Base):
    __tablename__ = "relationships"
    __table_args__ = (Index("ix_rel_run_from_tick", "run_id", "from_id", "tick"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64))
    tick: Mapped[int] = mapped_column(Integer)
    from_id: Mapped[str] = mapped_column(String(16))
    to_id: Mapped[str] = mapped_column(String(16))
    trust: Mapped[float] = mapped_column(Float)
    affection: Mapped[float] = mapped_column(Float)
    familiarity: Mapped[float] = mapped_column(Float)


class AgentStateHistoryORM(Base):
    __tablename__ = "agent_state_history"
    __table_args__ = (Index("ix_hist_run_agent_tick", "run_id", "agent_id", "tick"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64))
    agent_id: Mapped[str] = mapped_column(String(16))
    tick: Mapped[int] = mapped_column(Integer)
    state_json: Mapped[str] = mapped_column(Text)
