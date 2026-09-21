"""Motor de decisión por reglas: elecciones sensatas, determinismo y respuestas informativas."""

import random

from vida.agents.decision import DecisionContext, RuleBasedEngine, build_engine
from vida.memory.base import AgentMemory
from vida.world.actions import InfoRequest


def _ctx(world, agents, cfg, agent_id, tick=8):
    agent = agents[agent_id]
    perception = world.perceive(agent, agents, tick)
    memory = AgentMemory(agent_id, cfg.memory)
    return DecisionContext(
        agent=agent, perception=perception, memories=[], memory=memory,
        available_actions=world.legal_actions(agent, perception),
        location_info=world.public_location_info(),
        prices={r: world.price(r) for r in ("bread", "fruit", "care")},
        distance=world.distance, tick=tick, ticks_per_day=cfg.run.ticks_per_day,
    )


def _place(world, agents, agent_id, loc):
    world.place_agent(agent_id, loc)
    agents[agent_id].location_id = loc


def test_hungry_agent_with_bread_eats(small_world, small_cfg):
    world, agents, hub = small_world
    agent = agents["a01"]
    agent.needs["hunger"].level = 0.1
    agent.inventory["bread"] = 1
    engine = build_engine(small_cfg.decision)
    proposal, record = engine.decide(_ctx(world, agents, small_cfg, "a01"), hub.sub("decision", "a01"))
    assert proposal.kind == "consume" and proposal.resource == "bread"
    assert record.chosen == "consume:bread" and record.engine == "rules_v1"
    assert record.scores[record.chosen] == max(record.scores.values())


def test_hungry_agent_without_food_heads_to_market(small_world, small_cfg):
    world, agents, hub = small_world
    agent = agents["a01"]
    agent.needs["hunger"].level = 0.1
    for need in ("energy", "social", "knowledge", "health", "safety"):
        agent.needs[need].level = 1.0
    proposal, _ = RuleBasedEngine(small_cfg.decision).decide(_ctx(world, agents, small_cfg, "a01"), hub.sub("d"))
    assert proposal.kind == "move" and proposal.target_location == "market"


def test_tired_agent_at_home_rests(small_world, small_cfg):
    world, agents, hub = small_world
    agent = agents["a01"]
    agent.needs["energy"].level = 0.05
    for need in ("hunger", "social", "knowledge", "health", "safety"):
        agent.needs[need].level = 1.0
    proposal, _ = RuleBasedEngine(small_cfg.decision).decide(_ctx(world, agents, small_cfg, "a01"), hub.sub("d"))
    assert proposal.kind == "rest"


def test_decision_is_deterministic_for_same_seed(small_world, small_cfg):
    world, agents, _ = small_world
    engine = RuleBasedEngine(small_cfg.decision)
    a = [engine.decide(_ctx(world, agents, small_cfg, "a01"), random.Random(3))[0].key() for _ in range(5)]
    b = [engine.decide(_ctx(world, agents, small_cfg, "a01"), random.Random(3))[0].key() for _ in range(5)]
    assert a == b


def test_negative_memories_lower_expectation(small_world, small_cfg):
    world, agents, hub = small_world
    agent = agents["a01"]
    _place(world, agents, "a01", "plaza")
    agent.needs["hunger"].level = 0.2
    ctx = _ctx(world, agents, small_cfg, "a01")
    engine = RuleBasedEngine(small_cfg.decision)
    _, before = engine.decide(ctx, hub.sub("d"))
    ctx.memories = [ctx.memory.add("episodic", 1, "mal", importance=0.8, valence=-1.0, tags={"loc:market"})
                    for _ in range(3)]
    _, after = engine.decide(ctx, hub.sub("d"))
    assert after.scores["move@market"] < before.scores["move@market"]


def test_reply_honest_agent_tells_truth_and_dishonest_may_lie(small_world, small_cfg):
    world, agents, hub = small_world
    engine = RuleBasedEngine(small_cfg.decision)
    honest = agents["a01"]
    honest.personality.agreeableness = 0.95
    honest.identity.core_values["honesty"] = 0.95
    req = InfoRequest(asker_id="a02", responder_id="a01", resource="bread", tick=8)
    kinds = {engine.decide_reply(_ctx(world, agents, small_cfg, "a01"), req, random.Random(i)).kind for i in range(30)}
    assert "lie" not in kinds and "truth" in kinds
    liar = agents["a02"]
    liar.personality.agreeableness = 0.0
    liar.identity.core_values["honesty"] = 0.0
    liar.needs["hunger"].level = 0.0
    req2 = InfoRequest(asker_id="a01", responder_id="a02", resource="bread", tick=8)
    replies = [engine.decide_reply(_ctx(world, agents, small_cfg, "a02"), req2, random.Random(i)) for i in range(30)]
    lies = [r for r in replies if r.kind == "lie"]
    assert len(lies) >= 10
    assert all(r.claimed_location not in ("market", "home_2") for r in lies)


def test_reply_omits_when_nothing_is_believed(small_world, small_cfg):
    world, agents, hub = small_world
    agents["a01"].beliefs.resources.clear()
    req = InfoRequest(asker_id="a02", responder_id="a01", resource="bread", tick=8)
    reply = RuleBasedEngine(small_cfg.decision).decide_reply(_ctx(world, agents, small_cfg, "a01"), req, random.Random(0))
    assert reply.kind == "omit" and reply.claimed_location is None
