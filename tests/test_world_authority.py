"""Principio de arquitectura: el mundo es la autoridad; el agente puede creer cosas falsas."""

from vida.world.actions import ActionProposal


def _place(world, agents, agent_id, loc):
    world.place_agent(agent_id, loc)
    agents[agent_id].location_id = loc


def test_false_belief_yields_resource_absent_and_world_stays_intact(small_world):
    world, agents, hub = small_world
    agent = agents["a01"]
    # El agente cree que hay pan en el mercado porque se lo dijeron; el mercado está vacío.
    world.locations["market"].resources["bread"] = 0
    world.locations["market"].resources["fruit"] = 5  # el mercado sigue abierto y con algo en venta
    agent.beliefs.told("bread", "market", by="a02", event_id="ev_lie", tick=1)
    world.state.info_ledger["ev_lie"] = {"deceptive": True}
    _place(world, agents, "a01", "market")

    snapshot = world.state.model_dump()
    out = world.resolve(agent, ActionProposal(kind="acquire", resource="bread"), agents, hub.sub("world"), 8, "e1")

    assert out.kind == "resource_absent" and not out.success
    assert out.details["attributed_source_agent"] == "a02"
    assert out.details["_world"]["attributed_lie"] is True
    assert out.inventory_deltas == {} and out.money_delta == 0
    assert world.state.model_dump() == snapshot, "un fallo no muta el mundo"
    # La creencia del agente sigue intacta hasta que el módulo de aprendizaje la corrija.
    assert agent.beliefs.belief_at("bread", "market") is not None


def test_perception_only_shows_current_location(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "market")
    p = world.perceive(agents["a01"], agents, tick=8)
    assert p.location_id == "plaza" and p.visible_agents == [] and p.visible_resources == {}
    _place(world, agents, "a02", "plaza")
    p = world.perceive(agents["a01"], agents, tick=8)
    assert p.visible_agents == ["a02"]
    p2 = world.perceive(agents["a02"], agents, tick=8)
    assert p2.visible_agents == ["a01"]


def test_dead_agents_are_not_visible(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    agents["a02"].physical.alive = False
    assert world.perceive(agents["a01"], agents, 8).visible_agents == []
    world.remove_agent("a02")
    assert world.location_of("a02") is None


def test_beliefs_are_refuted_and_confirmed_independently_of_truth(small_world):
    _, agents, _ = small_world
    beliefs = agents["a01"].beliefs
    b = beliefs.best_location("bread")
    assert b is not None and b.source == "prior" and b.confidence == 0.8
    beliefs.refute("bread", "market")
    assert beliefs.belief_at("bread", "market").confidence == 0.24
    beliefs.refute("bread", "market")
    assert beliefs.belief_at("bread", "market").confidence == 0.1  # se debilita, nunca desaparece
    beliefs.told("bread", "school", by="a02", event_id="e9", tick=5)
    assert beliefs.best_location("bread").location_id == "school"
    # Una observación directa domina sobre lo contado: ver que no hay pan debilita el rumor.
    beliefs.observe_resources("school", {"fruit": 2}, tick=6)
    weakened = beliefs.belief_at("bread", "school")
    assert weakened.confidence == 0.35 and weakened.source == "observed" and weakened.source_agent is None
    assert beliefs.belief_at("fruit", "school").source == "observed"
    # Si el rumor y el mercado real ya están débiles, el agente sigue sabiendo dónde buscar.
    assert beliefs.best_location("bread").location_id == "school"
