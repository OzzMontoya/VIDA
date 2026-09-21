"""Ciclo de vida artificial (sección 17): etapas por edad y muerte.

La muerte ocurre por salud agotada, por una necesidad crítica sostenida durante
``critical_ticks`` o por edad máxima. En VIDA-0.1 no hay generaciones.
"""

from __future__ import annotations

from dataclasses import dataclass

from vida.agents.agent import STAGE_ORDER, AgentState, LifeStage
from vida.simulation.config import RunConfig


@dataclass
class LifecycleUpdate:
    stage_change: LifeStage | None = None
    death_reason: str | None = None


def stage_for_days(cfg: RunConfig, days: int) -> LifeStage:
    t = cfg.lifecycle.stage_thresholds_days
    if days >= t.old_age:
        return "old_age"
    if days >= t.adulthood:
        return "adulthood"
    if days >= t.youth:
        return "youth"
    if days >= t.adolescence:
        return "adolescence"
    return "infancy"


def health_decay_factor(agent: AgentState, cfg: RunConfig) -> float:
    return cfg.lifecycle.old_age_health_factor if agent.life_stage == "old_age" else 1.0


def advance(agent: AgentState, cfg: RunConfig, ticks_per_day: int) -> LifecycleUpdate:
    """Avanza un tick de edad; aplica cambio de etapa y comprueba muerte."""
    update = LifecycleUpdate()
    if not agent.alive:
        return update
    agent.age_ticks += 1
    days = agent.age_days(ticks_per_day)

    new_stage = stage_for_days(cfg, days)
    if STAGE_ORDER.index(new_stage) > STAGE_ORDER.index(agent.life_stage):
        agent.life_stage = new_stage
        update.stage_change = new_stage

    critical = sorted(name for name, need in agent.needs.items() if need.is_critical())
    if critical:
        agent.critical_streak += 1
    else:
        agent.critical_streak = 0

    reason: str | None = None
    if agent.needs["health"].level <= 0.0:
        reason = "health_exhausted"
    elif agent.critical_streak >= cfg.lifecycle.critical_ticks:
        reason = f"critical_need:{critical[0]}"
    elif days > cfg.lifecycle.max_age_days:
        reason = "old_age"

    if reason is not None:
        agent.physical.alive = False
        agent.life_stage = "dead"
        update.death_reason = reason
    return update
