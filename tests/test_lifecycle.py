"""Ciclo de vida: etapas por edad, muerte por necesidad crítica y exclusión de los muertos."""

from vida.simulation import lifecycle
from vida.simulation.engine import SimulationEngine


def test_stage_thresholds(cfg):
    assert lifecycle.stage_for_days(cfg, 0) == "infancy"
    assert lifecycle.stage_for_days(cfg, 12) == "adolescence"
    assert lifecycle.stage_for_days(cfg, 18) == "youth"
    assert lifecycle.stage_for_days(cfg, 30) == "adulthood"
    assert lifecycle.stage_for_days(cfg, 65) == "old_age"


def test_advance_changes_stage_at_threshold(cfg, small_world):
    _, agents, _ = small_world
    agent = agents["a01"]
    agent.age_ticks = cfg.lifecycle.stage_thresholds_days.old_age * 24 - 1
    agent.life_stage = "adulthood"
    update = lifecycle.advance(agent, cfg, 24)
    assert update.stage_change == "old_age" and agent.life_stage == "old_age"
    assert lifecycle.health_decay_factor(agent, cfg) == cfg.lifecycle.old_age_health_factor


def test_death_by_sustained_critical_hunger(cfg, small_world):
    _, agents, _ = small_world
    agent = agents["a01"]
    agent.needs["hunger"].level = 0.0
    reasons = [lifecycle.advance(agent, cfg, 24).death_reason for _ in range(cfg.lifecycle.critical_ticks)]
    assert reasons[:-1] == [None] * (cfg.lifecycle.critical_ticks - 1)
    assert reasons[-1] == "critical_need:hunger"
    assert not agent.alive and agent.life_stage == "dead"
    assert lifecycle.advance(agent, cfg, 24).death_reason is None  # los muertos no vuelven a morir


def test_death_by_health_and_max_age(cfg, small_world):
    _, agents, _ = small_world
    a, b = agents["a01"], agents["a02"]
    a.needs["health"].level = 0.0
    assert lifecycle.advance(a, cfg, 24).death_reason == "health_exhausted"
    b.age_ticks = (cfg.lifecycle.max_age_days + 1) * 24
    b.life_stage = "old_age"
    assert lifecycle.advance(b, cfg, 24).death_reason == "old_age"


def test_engine_removes_dead_agents_and_logs_death(small_cfg):
    engine = SimulationEngine(small_cfg, run_id="test", sha="test")
    victim = engine.agents["a01"]
    victim.needs["health"].level = 0.001
    victim.needs["hunger"].level = 0.0
    witness = engine.agents["a02"]
    witness.relationship_with("a01").familiarity = 0.5
    events = engine.step()
    deaths = [e for e in events if e.event_type == "death"]
    assert len(deaths) == 1 and deaths[0].agent_id == "a01"
    assert engine.deaths == {"a01": deaths[0].note}
    assert engine.world.location_of("a01") is None
    assert any("murió" in m.content for m in engine.memories["a02"].all())
    # En el siguiente tick el muerto ya no actúa.
    events = engine.step()
    assert all(e.agent_id != "a01" for e in events)
