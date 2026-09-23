"""VIDA-0.2: memoria reflexiva, automodelo predictivo, acoplamiento memoria→decisión y escala de 100 agentes."""

from vida.agents.decision import DecisionContext, RuleBasedEngine
from vida.agents.selfmodel import PopulationModel, SelfModelState, predict_success
from vida.memory import reflective
from vida.memory.base import AgentMemory
from vida.simulation.engine import SimulationEngine
from vida.world.presets import build_world, spawn_agents
from vida.simulation.rng import RngHub


def _ctx(world, agents, cfg, agent_id, memory, tick=8):
    agent = agents[agent_id]
    perception = world.perceive(agent, agents, tick)
    return DecisionContext(
        agent=agent, perception=perception, memories=memory.retrieve({"loc:market"}, tick), memory=memory,
        available_actions=world.legal_actions(agent, perception), location_info=world.public_location_info(),
        prices={r: world.price(r) for r in ("bread", "fruit", "care")}, distance=world.distance,
        tick=tick, ticks_per_day=cfg.run.ticks_per_day,
    )


def test_reflection_summarises_repeated_episodes(small_world, small_cfg):
    _, agents, _ = small_world
    memory = AgentMemory("a01", small_cfg.memory)
    for t in range(5):
        ok = t < 2
        memory.add("episodic", t, "compra", importance=0.5, valence=0.5 if ok else -0.7,
                   tags={"action:acquire", "res:bread", "loc:market", "outcome:ok" if ok else "outcome:resource_absent"})
    written = reflective.reflect(memory, agents["a01"], tick=23, ticks_per_day=24)
    assert len(written) >= 1
    rec = next(r for r in written if "res:bread" in r.tags)
    assert rec.kind == "reflective" and "salió mal 2 de 5" in rec.content and rec.valence < 0
    # Repetir la reflexión actualiza el mismo registro en lugar de duplicarlo.
    reflective.reflect(memory, agents["a01"], tick=47, ticks_per_day=24)
    assert len(memory.by_kind("reflective")) == len(written)


def test_experience_now_changes_decisions(small_world, small_cfg):
    """Con la misma situación, un agente escaldado evita el mercado y uno con buenos recuerdos lo prefiere."""
    world, agents, hub = small_world
    agent = agents["a01"]
    agent.needs["hunger"].level = 0.3
    for need in ("energy", "social", "knowledge", "health", "safety"):
        agent.needs[need].level = 1.0
    engine = RuleBasedEngine(small_cfg.decision)

    bad = AgentMemory("a01", small_cfg.memory)
    for t in range(6):
        bad.add("episodic", t, "sin pan", importance=0.8, valence=-0.7,
                tags={"action:move", "loc:market", "outcome:resource_absent"})
        bad.add("episodic", t, "sin pan", importance=0.8, valence=-0.7,
                tags={"action:acquire", "res:bread", "loc:market", "outcome:resource_absent"})
    reflective.reflect(bad, agent, tick=7, ticks_per_day=24)
    _, rec_bad = engine.decide(_ctx(world, agents, small_cfg, "a01", bad), hub.sub("d"))

    good = AgentMemory("a01", small_cfg.memory)
    for t in range(6):
        good.add("episodic", t, "pan", importance=0.5, valence=0.5, tags={"action:move", "loc:market", "outcome:ok"})
        good.add("episodic", t, "pan", importance=0.5, valence=0.5, tags={"action:acquire", "res:bread", "loc:market", "outcome:ok"})
    reflective.reflect(good, agent, tick=7, ticks_per_day=24)
    _, rec_good = engine.decide(_ctx(world, agents, small_cfg, "a01", good), hub.sub("d"))

    assert rec_good.scores["move@market"] > rec_bad.scores["move@market"] * 1.5
    assert rec_good.chosen == "move@market"


def test_self_model_prediction_and_calibration():
    cfg_mem = __import__("vida.simulation.config", fromlist=["MemorySection"]).MemorySection()
    memory = AgentMemory("a01", cfg_mem)
    assert predict_success(memory, {"action:work"}) == 0.7  # prior sin experiencia
    for t in range(4):
        memory.add("episodic", t, "w", importance=0.3, tags={"action:work", "outcome:ok"})
    memory.add("episodic", 5, "w", importance=0.3, tags={"action:work", "outcome:illegal"})
    assert predict_success(memory, {"action:work"}) == round((4 + 1.4) / 7, 6)
    sm = SelfModelState()
    sm.record(0.9, 0.5, True)
    sm.record(0.9, 0.5, True)
    assert sm.n == 2 and sm.calibration() == 0.9 and sm.advantage() == 0.4
    sm.record(0.9, 0.5, False)
    assert sm.recent_error() == round((0.1 + 0.1 + 0.9) / 3, 6)
    pop = PopulationModel()
    pop.update(["work"], True); pop.update(["work"], False)
    assert pop.rate("work") == round((1 + 1.4) / 4, 6)


def test_context_table_backs_off_to_general_levels():
    from vida.agents.selfmodel import ContextTable, context_levels
    table = ContextTable()
    needs = {"hunger": 0.2, "energy": 0.9}
    levels = context_levels("acquire", "bread", hour=9, ticks_per_day=24, needs=needs)
    assert levels[0] == "acquire|bread|p1|h=crit|e=ok" and levels[-1] == "acquire"
    assert table.predict(levels) == 0.7  # sin evidencia: prior
    for _ in range(3):
        table.update(["acquire|bread|p3", "acquire|bread", "acquire"], False)  # otra franja: fracasos
    # El contexto específico de la mañana no tiene evidencia; retrocede a acquire|bread (3 fracasos).
    assert table.predict(levels) == round(1.4 / 5, 6)
    for _ in range(3):
        table.update(levels, True)
    assert table.predict(levels) == round((3 + 1.4) / 5, 6)  # ahora manda el contexto específico


def test_town_preset_offers_real_alternatives(cfg):
    from vida.world.presets import build_world, spawn_agents
    from vida.world.actions import ActionProposal
    c = cfg.model_copy(deep=True)
    c.world.preset = "town"
    world = build_world(c)
    assert {"market", "bazaar", "mine", "workshop", "farm"} <= set(world.locations)
    assert world.price("bread", "bazaar") == 1.2 and world.price("bread", "market") == 2.0 and world.price("bread") == 2.0
    assert world.wage("mine") == 5.5 and world.wage("farm") == 2.5 and world.wage() == 3.0
    info = world.public_location_info()
    assert info["bazaar"]["prices"]["bread"] == 1.2 and info["mine"]["wage"] == 5.5
    agents = spawn_agents(c, world, RngHub(3).sub("spawn"))
    a = agents["a01"]
    assert a.beliefs.belief_at("bread", "bazaar") is not None
    world.place_agent("a01", "bazaar"); a.location_id = "bazaar"
    out = world.resolve(a, ActionProposal(kind="acquire", resource="bread"), agents, RngHub(1).sub("w"), 10, "e1")
    assert out.success and out.money_delta == -1.2
    world.place_agent("a01", "mine"); a.location_id = "mine"
    a.knowledge["job"].level = 1.0; a.needs["energy"].level = 1.0  # éxito seguro: p_success = 1
    out = world.resolve(a, ActionProposal(kind="work"), agents, RngHub(1).sub("w"), 8, "e2")
    assert out.success and out.need_deltas["energy"] == -0.14 and out.money_delta > 2.0
    engine = SimulationEngine(c, run_id="town", sha="test")
    summary = engine.run(ticks=48)
    assert summary.alive and summary.n_events > 400


def test_engine_records_predictions_and_reflections(small_cfg):
    engine = SimulationEngine(small_cfg, run_id="v02", sha="test")
    engine.run(ticks=72)
    actions = [e for e in engine.events if e.event_type == "action"]
    assert all(e.prediction is not None and 0.0 <= e.prediction["p_success"] <= 1.0 for e in actions)
    for agent in engine.agents.values():
        assert agent.self_model.n == sum(1 for e in actions if e.agent_id == agent.id)
        assert 0.0 <= agent.self_model.calibration() <= 1.0
    assert any(engine.memories[aid].by_kind("reflective") for aid in engine.agents), "tras 3 días debe haber reflexiones"


def test_forgetting_facts_weakens_beliefs(small_cfg):
    cfg = small_cfg.model_copy(deep=True)
    cfg.memory.forget_below = 1.01
    cfg.memory.forget_after_days = 0
    cfg.memory.forget_kinds = ["episodic", "semantic"]
    engine = SimulationEngine(cfg, run_id="forget", sha="test")
    engine.run(ticks=48)
    a = engine.agents["a01"]
    belief = a.beliefs.belief_at("bread", "market")
    assert belief is None or belief.confidence <= 0.8
    assert engine.memories["a01"].by_kind("semantic") == []


def test_hundred_agents_scale(cfg):
    c = cfg.model_copy(deep=True)
    c.agents.n_agents = 100
    c.world.n_homes = 25
    world = build_world(c)
    agents = spawn_agents(c, world, RngHub(1).sub("spawn"))
    assert len(agents) == 100 and len([l for l in world.locations.values() if l.type == "home"]) == 25
    assert len({a.home_id for a in agents.values()}) == 25
    engine = SimulationEngine(c, run_id="scale", world=world, agents=agents, sha="test")
    summary = engine.run(ticks=12)
    assert summary.n_agents == 100 and summary.n_events >= 1200


def test_selfmodel_analysis_and_cli(small_cfg, tmp_path, capsys):
    from vida.cli import main
    from vida.evaluation.selfmodel_analysis import advantage_by_evidence, render_selfmodel_analysis

    engine = SimulationEngine(small_cfg, run_id="sm", sha="test")
    engine.run(ticks=96)
    result = advantage_by_evidence(engine.events, 24)
    assert result["by_evidence"] and all(-1.0 <= r["advantage"] <= 1.0 for r in result["by_evidence"])
    assert sum(r["n"] for r in result["by_evidence"]) == sum(1 for e in engine.events if e.event_type == "action")
    text = render_selfmodel_analysis(result)
    assert "intentos propios" in text
    data = tmp_path / "data"
    assert main(["--data-dir", str(data), "run", "--config", "config/default.yaml", "--seed", "3", "--ticks", "48",
                 "--run-id", "smcli", "--log-dir", str(tmp_path / "logs")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", str(data), "selfmodel", "--run", "smcli"]) == 0
    assert "criterio 1" in capsys.readouterr().out


def test_surprise_and_affection_raise_memory_importance(small_cfg):
    cfg = small_cfg.model_copy(deep=True)
    cfg.lifecycle.population_cap = 2
    engine = SimulationEngine(cfg, run_id="couple", sha="test")
    engine.run(ticks=72)
    a = engine.agents["a01"]
    a.relationships["a02"].affection = 1.0
    ev = engine._agent_turn(a)
    # cada episodio nuevo lleva al menos la sorpresa del automodelo o el afecto sumados a su importancia base
    mems = [m for m in engine.memories["a01"].all() if m.id in ev.memories_created and m.kind == "episodic"]
    if mems and ev.outcome.target_agent == "a02":
        assert mems[0].importance >= 0.3
    cfg2 = cfg.model_copy(deep=True)
    cfg2.memory.surprise_weight = 0.0
    cfg2.memory.affection_weight = 0.0
    e2 = SimulationEngine(cfg2, run_id="couple0", sha="test")
    e2.run(ticks=72)
    mean_coupled = sum(m.importance for m in engine.memories["a01"].by_kind("episodic")) / max(1, len(engine.memories["a01"].by_kind("episodic")))
    mean_plain = sum(m.importance for m in e2.memories["a01"].by_kind("episodic")) / max(1, len(e2.memories["a01"].by_kind("episodic")))
    assert mean_coupled > mean_plain
