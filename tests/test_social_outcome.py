"""Relaciones, aprendizaje e identidad se mueven por resultados, no por palabras."""

from vida.agents import identity, learning, social
from vida.world.actions import ActionOutcome, ActionProposal


def _place(world, agents, agent_id, loc):
    world.place_agent(agent_id, loc)
    agents[agent_id].location_id = loc


def test_false_share_lowers_trust_only_after_acting_on_it(small_world):
    world, agents, hub = small_world
    a, b = agents["a01"], agents["a02"]
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    world.locations["market"].resources["bread"] = 0
    world.locations["market"].resources["fruit"] = 5

    # B comparte (mintiendo) que hay pan en el mercado. Decir la mentira no cambia la confianza de A.
    share = ActionProposal(kind="share_info", target_agent="a01", resource="bread",
                           payload={"claimed_location": "market", "truthful": False},
                           rationale="voy a decir una mentira para que se vaya")
    out = world.resolve(b, share, agents, hub.sub("world"), 8, "ev_share")
    social.update_relationships(b, out, agents)
    learning.receive_shared_info(a, out, "ev_share")
    trust_before = a.relationship_with("a02").trust
    assert trust_before == 0.5
    belief = a.beliefs.belief_at("bread", "market")
    assert belief.source == "told" and belief.source_agent == "a02" and belief.source_event_id == "ev_share"

    # A actúa sobre la información y fracasa: ahora sí cae la confianza y la reputación de B.
    _place(world, agents, "a01", "market")
    out = world.resolve(a, ActionProposal(kind="acquire", resource="bread"), agents, hub.sub("world"), 9, "ev_buy")
    assert out.kind == "resource_absent"
    deltas = social.update_relationships(a, out, agents)
    assert deltas["a01->a02"]["trust"] == -0.15
    assert a.relationship_with("a02").trust == 0.35
    assert a.beliefs.model_of("a02").honesty_estimate == 0.3
    rep = world.update_reputation(a, out, agents)
    assert rep == {"a02": -0.05}
    prefs, changes = learning.learn(a, out, "ev_buy")
    assert "refute:bread@market" in changes
    assert a.beliefs.belief_at("bread", "market") is None or a.beliefs.belief_at("bread", "market").confidence < 0.5


def test_true_share_raises_trust_after_success(small_world):
    world, agents, hub = small_world
    a, b = agents["a01"], agents["a02"]
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    share = ActionProposal(kind="share_info", target_agent="a01", resource="bread",
                           payload={"claimed_location": "market", "truthful": True})
    out = world.resolve(b, share, agents, hub.sub("world"), 8, "ev_share")
    learning.receive_shared_info(a, out, "ev_share")
    _place(world, agents, "a01", "market")
    out = world.resolve(a, ActionProposal(kind="acquire", resource="bread"), agents, hub.sub("world"), 9, "ev_buy")
    assert out.success
    deltas = social.update_relationships(a, out, agents)
    assert deltas["a01->a02"]["trust"] == 0.10
    assert world.update_reputation(a, out, agents) == {"a02": 0.02}


def test_rationale_text_never_matters(small_world):
    world, agents, hub = small_world
    a, b = agents["a01"], agents["a02"]
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    b.relationship_with("a01").trust = 1.0  # aceptación casi segura
    p1 = ActionProposal(kind="socialize", target_agent="a02", rationale="mentira engaño traición")
    p2 = ActionProposal(kind="socialize", target_agent="a02", rationale="amistad sincera")
    o1 = world.resolve(a, p1, agents, hub.sub("w1"), 8, "e1")
    o2 = world.resolve(a, p2, agents, hub.sub("w1"), 8, "e2")
    assert o1.model_dump(exclude={"details"}) == o2.model_dump(exclude={"details"})
    assert o1.success
    d = social.update_relationships(a, o1, agents)
    # Ajustes asintóticos: desde 0.5 el delta nominal se aplica tal cual; desde 0.0 se duplica.
    assert d["a01->a02"] == {"trust": 0.02, "affection": 0.05, "familiarity": 0.1}
    assert d["a02->a01"]["affection"] == 0.04
    # Repetir la interacción acerca a 1.0 sin saturar de golpe.
    for _ in range(30):
        social.update_relationships(a, o1, agents)
    rel = a.relationship_with("a02")
    assert 0.9 < rel.familiarity < 1.0 and rel.trust < 1.0


def test_learning_updates_preferences_and_skills(small_world):
    _, agents, _ = small_world
    a = agents["a01"]
    work = ActionOutcome(tick=3, agent_id="a01", action="work", kind="ok", success=True, location_id="farm",
                         money_delta=2.0, valence=0.3, details={"skill": "job", "skill_gain": 0.02})
    level_before = a.knowledge["job"].level
    prefs, _ = learning.learn(a, work, "e1")
    assert a.knowledge["job"].level == round(level_before + 0.02, 6)
    assert prefs["action:work"] > 0 and prefs["loc:farm"] > 0
    rejected = ActionOutcome(tick=4, agent_id="a01", action="socialize", kind="rejected", success=False,
                             location_id="plaza", target_agent="a02", valence=-0.4)
    prefs, _ = learning.learn(a, rejected, "e2")
    assert prefs["agent:a02"] < 0


def test_ask_info_learning_ignores_world_only_details(small_world):
    _, agents, _ = small_world
    a = agents["a01"]
    out = ActionOutcome(tick=4, agent_id="a01", action="ask_info", kind="ok", success=True, location_id="plaza",
                        target_agent="a02", resource="bread", valence=0.2,
                        details={"responded": True, "claimed_location": "school", "claimed_confidence": 0.9,
                                 "informant": "a02", "_world": {"intent": "lie", "was_true": False}})
    _, changes = learning.learn(a, out, "ev_ask")
    assert changes == ["told:bread@school by a02"]
    belief = a.beliefs.belief_at("bread", "school")
    assert belief.source == "told" and belief.source_event_id == "ev_ask"
    deltas = social.update_relationships(a, out, agents)
    assert deltas["a01->a02"]["trust"] == 0.01  # confiar un poco por responder; la verdad se juzga después


def test_identity_tags_follow_behaviour(small_world):
    _, agents, _ = small_world
    a = agents["a01"]
    assert identity.refresh(a) == []
    a.counters.update({"action:work": 8, "action:rest": 2, "action:move": 2, "reply:truth": 4, "share:truth": 1})
    a.relationship_with("a02").familiarity = 0.5
    a.relationship_with("a02").affection = 0.8
    a.preference_for("loc:farm").valence = 0.6
    a.preference_for("loc:farm").strength = 0.5
    tags = identity.refresh(a)
    assert tags == ["trabajador", "honesto", "cercano_a:a02", "prefiere:loc:farm"]
    assert a.identity.core_values["honesty"] > 0.5 and a.identity.core_values["ambition"] > 0.5
    a.counters["reply:lie"] = 4
    assert "engañoso" in identity.refresh(a)


def test_lie_is_discovered_on_arrival_without_buying(small_world, small_cfg):
    """Llegar donde prometieron pan y no verlo basta para desconfiar del informante (sección 20)."""
    from vida.simulation.engine import SimulationEngine

    engine = SimulationEngine(small_cfg, run_id="disc", sha="test")
    a, b = engine.agents["a01"], engine.agents["a02"]
    engine.world.state.info_ledger["ev_lie"] = {"deceptive": True}
    a.beliefs.told("bread", "school", by="a02", event_id="ev_lie", tick=0)
    engine.world.place_agent("a01", "school"); a.location_id = "school"
    trust_before = a.relationship_with("a02").trust
    rep_before = b.reputation
    event = engine._agent_turn(a)
    assert any(c.startswith("disproved:bread@school by a02") for c in event.belief_changes)
    assert a.relationship_with("a02").trust < trust_before
    assert a.beliefs.model_of("a02").honesty_estimate == 0.3
    assert b.reputation < rep_before and event.reputation_deltas.get("a02", 0) < 0
    assert a.counters.get("discovered_lie") == 1
    assert any("no había" in m.content for m in engine.memories["a01"].by_kind("social"))
    # Una promesa honesta pero desmentida por el mundo no toca la reputación (el libro no la marca engañosa).
    engine.world.state.info_ledger["ev_ok"] = {"deceptive": False}
    a.beliefs.told("fruit", "school", by="a02", event_id="ev_ok", tick=1)
    rep_mid = b.reputation
    engine._agent_turn(a)
    assert b.reputation == rep_mid
