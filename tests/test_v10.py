"""VIDA-1.0: generaciones (nacimientos, herencia, transmisión cultural) y automodelo con conocimiento privado."""

from vida.agents.selfmodel import own_context_levels
from vida.simulation import generations
from vida.simulation.engine import SimulationEngine


def _long_cfg(cfg, n_agents=4, seed=5):
    c = cfg.model_copy(deep=True)
    c.run.seed = seed
    c.agents.n_agents = n_agents
    c.lifecycle.birth_check_days = 1
    return c


def test_child_inherits_and_receives_culture(small_world, small_cfg):
    world, agents, hub = small_world
    parent = agents["a01"]
    parent.money = 30.0
    parent.identity.core_values["honesty"] = 0.9
    from vida.memory.base import AgentMemory
    from vida.memory import semantic
    mem = AgentMemory("a01", small_cfg.memory)
    semantic.record_availability(mem, "bread", "market", True, tick=5)
    semantic.record_availability(mem, "fruit", "farm", False, tick=6)
    child = generations.make_child(small_cfg, world, parent, mem, "a03", "Nova", tick=48, rng=hub.sub("births"))
    assert child.parent_id == "a01" and child.generation == 1 and child.home_id == parent.home_id
    assert child.life_stage == "adolescence" and child.money == 12.0 and parent.money == 18.0  # mínimo al nacer
    for trait in ("openness", "extraversion", "agreeableness"):
        p, k = getattr(parent.personality, trait), getattr(child.personality, trait)
        assert abs(k - p) <= 0.5 * abs(p - 0.1) + 0.5 * abs(0.9 - p) + 1e-9  # dentro del rango de mezcla
    told = child.beliefs.belief_at("bread", "market")
    assert told is not None and told.source == "told" and told.source_agent == "a01"
    assert child.beliefs.belief_at("fruit", "farm").source == "prior"  # hechos negativos no se transmiten
    assert child.relationship_with("a01").affection > 0.5 and parent.relationship_with("a03").familiarity >= 0.5


def test_births_fill_population_after_deaths(cfg):
    c = _long_cfg(cfg)
    c.lifecycle.population_cap = c.agents.n_agents
    engine = SimulationEngine(c, run_id="gen", sha="test")
    engine.step()
    # Matamos a un agente al inicio del día 1 y comprobamos que nace un sustituto.
    victim = engine.agents["a02"]
    victim.needs["health"].level = 0.0
    while engine.clock.day < 3:
        engine.step()
    assert "a02" in engine.deaths
    assert engine.births, "con hueco en la población debe haber nacimientos"
    child = engine.agents[engine.births[0]]
    assert child.generation == 1 and child.parent_id in engine.agents
    births = [e for e in engine.events if e.event_type == "birth"]
    assert births and births[0].agent_id == engine.births[0] and "parent=" in births[0].note
    assert births[0].state_after.location_id == child.home_id  # nace en casa del progenitor (luego puede moverse)
    assert any("nací" in m.content for m in engine.memories[child.id].all())


def test_no_births_when_population_full_or_disabled(cfg):
    c = _long_cfg(cfg)
    c.lifecycle.population_cap = c.agents.n_agents  # tope = población inicial: sin hueco
    engine = SimulationEngine(c, run_id="full", sha="test")
    engine.run(ticks=72)
    assert engine.births == []
    c2 = _long_cfg(cfg)
    c2.lifecycle.births = False
    engine2 = SimulationEngine(c2, run_id="off", sha="test")
    engine2.agents["a01"].needs["health"].level = 0.0
    engine2.run(ticks=72)
    assert engine2.births == []


def test_births_keep_determinism(cfg):
    c = _long_cfg(cfg)
    outs = []
    for run_id in ("g1", "g2"):
        e = SimulationEngine(c, run_id=run_id, sha="test")
        e.agents["a03"].needs["health"].level = 0.0
        s = e.run(ticks=96)
        outs.append((s.events_sha256, s.births))
    assert outs[0] == outs[1] and outs[0][1] >= 1


def test_own_context_levels_add_private_knowledge(small_world):
    _, agents, _ = small_world
    a = agents["a01"]
    a.relationship_with("a02").trust = 0.9
    a.knowledge["job"].level = 0.8
    social = own_context_levels(a, "socialize", "a02", 9, 24)
    assert social[0].startswith("socialize|a02|trust=ok|aff=") and len(social) == 5
    work = own_context_levels(a, "work", None, 9, 24)
    assert work[0].startswith("work|-|skill=ok|e=")
    assert own_context_levels(a, "rest", None, 9, 24)[0].startswith("rest|-|p1")  # sin nivel privado


def test_lineage_report_and_cli(cfg, tmp_path, capsys):
    from vida.cli import main
    from vida.evaluation.lineage import lineage_report, render_lineage

    c = _long_cfg(cfg)
    engine = SimulationEngine(c, run_id="lin", sha="test")
    engine.agents["a03"].needs["health"].level = 0.0
    engine.run(ticks=120)
    report = lineage_report(engine.agents, engine.memories, engine.events)
    assert report["summary"]["children"] >= 1
    row = report["rows"][0]
    assert 0.0 <= row["ici_parent"] <= 1.0 and row["generation"] == 1
    assert "hijo" in render_lineage(report)
    data = tmp_path / "data"
    assert main(["--data-dir", str(data), "run", "--config", "config/default.yaml", "--seed", "5", "--ticks", "48",
                 "--run-id", "lincli", "--log-dir", str(tmp_path / "logs")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", str(data), "lineage", "--run", "lincli"]) == 0
    assert "linaje" in capsys.readouterr().out


def test_default_cap_allows_early_births_from_young_adults(cfg):
    c = _long_cfg(cfg)
    engine = SimulationEngine(c, run_id="early", sha="test")
    engine.run(ticks=24 * 4)
    assert len(engine.births) == 2, "tope por defecto = población + 2: dos nacimientos sin necesidad de muertes"
    assert all(engine.agents[b].generation == 1 for b in engine.births)


def test_dependent_children_receive_allowance_and_survive(cfg):
    c = _long_cfg(cfg)
    engine = SimulationEngine(c, run_id="allow", sha="test")
    engine.run(ticks=24 * 12)  # los hijos nacen en adolescencia y llegan a juventud el día 6 tras nacer
    assert len(engine.births) == 2
    allowances = [e for e in engine.events if e.event_type == "world_event" and e.note == "allowance"]
    assert allowances, "los progenitores deben pasar asignación a los hijos dependientes"
    for b in engine.births:
        child = engine.agents[b]
        assert child.alive, f"el hijo {b} debería sobrevivir con la asignación familiar"
        assert any(e.world_delta.get("to") == b for e in allowances)


def test_orphans_get_a_guardian(cfg):
    c = _long_cfg(cfg)
    engine = SimulationEngine(c, run_id="orphan", sha="test")
    engine.run(ticks=24 * 2)
    assert engine.births
    child = engine.agents[engine.births[0]]
    engine.agents[child.parent_id].needs["health"].level = 0.0  # muere el progenitor
    engine.run(ticks=24 * 3)
    assert child.parent_id in engine.deaths
    assert child.guardian_id and engine.agents[child.guardian_id].alive
    guardian_allowances = [e for e in engine.events if e.note == "allowance" and e.world_delta.get("to") == child.id
                           and e.world_delta.get("guardian")]
    assert guardian_allowances and child.alive
    assert any("se hizo cargo" in m.content for m in engine.memories[child.id].all())
