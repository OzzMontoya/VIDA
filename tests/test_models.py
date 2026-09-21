"""Modelos de dominio: construcción reproducible de mundo y agentes."""

from vida.simulation.rng import RngHub
from vida.world.presets import build_world, spawn_agents


def test_village_small_has_twelve_connected_locations(cfg):
    world = build_world(cfg)
    assert len(world.locations) == 12
    types = {loc.type for loc in world.locations.values()}
    assert types == {"home", "plaza", "market", "school", "hospital", "workplace"}
    for loc_id in world.locations:
        assert world.distance("plaza", loc_id) <= 2, loc_id


def test_spawn_ten_distinct_agents_deterministically(cfg):
    w1, w2 = build_world(cfg), build_world(cfg)
    a1 = spawn_agents(cfg, w1, RngHub(cfg.run.seed).sub("spawn"))
    a2 = spawn_agents(cfg, w2, RngHub(cfg.run.seed).sub("spawn"))
    assert list(a1) == [f"a{i:02d}" for i in range(1, 11)]
    assert [a.model_dump() for a in a1.values()] == [a.model_dump() for a in a2.values()]
    personalities = {a.personality.model_dump_json() for a in a1.values()}
    assert len(personalities) == 10, "agentes inicialmente comparables pero no idénticos"
    for agent in a1.values():
        assert w1.location_of(agent.id) == agent.home_id
        assert agent.life_stage in {"adulthood", "youth"}
        assert agent.beliefs.best_location("bread").location_id == "market"
        assert "market" in agent.beliefs.known_locations
        assert all(h not in agent.beliefs.known_locations for h in w1.locations
                   if w1.locations[h].type == "home" and h != agent.home_id)


def test_different_seed_gives_different_population(cfg):
    a1 = spawn_agents(cfg, build_world(cfg), RngHub(1).sub("spawn"))
    a2 = spawn_agents(cfg, build_world(cfg), RngHub(2).sub("spawn"))
    assert a1["a01"].personality != a2["a01"].personality


def test_agent_summary_and_helpers(small_world):
    _, agents, _ = small_world
    agent = agents["a01"]
    s = agent.summary()
    assert s.agent_id == "a01" and s.location_id == agent.home_id
    assert set(s.needs) == set(agent.needs)
    rel = agent.relationship_with("a02")
    deltas = rel.adjust(trust=0.2, familiarity=0.05)
    assert deltas == {"trust": 0.2, "familiarity": 0.05}
    assert rel.adjust(trust=5.0) == {"trust": round(1.0 - 0.7, 6)}  # acotado en 1.0
    before = agent.needs["hunger"].level
    agent.decay_needs()
    assert agent.needs["hunger"].level < before
