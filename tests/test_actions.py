"""Acciones: precondiciones, resolución y consecuencias objetivas."""

import pytest

from vida.world.actions import ActionProposal, InfoReply


def _place(world, agents, agent_id, loc):
    world.place_agent(agent_id, loc)
    agents[agent_id].location_id = loc


def _resolve(world, agents, hub, agent_id, proposal, tick=8, event_id="e1"):
    return world.resolve(agents[agent_id], proposal, agents, hub.sub("world"), tick, event_id)


def test_illegal_action_is_rejected_without_side_effects(small_world):
    world, agents, hub = small_world
    # Trabajar en casa no es legal.
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="work"))
    assert out.kind == "illegal" and not out.success
    assert out.money_delta == 0 and out.need_deltas == {}


def test_move_updates_world_position_and_costs_energy(small_world):
    world, agents, hub = small_world
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="move", target_location="market"))
    assert out.success and out.new_location == "market"
    assert world.location_of("a01") == "market"
    assert out.need_deltas["energy"] == pytest.approx(-0.02 * 2)
    # La caché del agente NO cambia hasta apply_outcome: el mundo es la autoridad.
    assert agents["a01"].location_id == agents["a01"].home_id


def test_cannot_enter_someone_elses_home(small_world):
    world, agents, hub = small_world
    other_home = agents["a02"].home_id
    assert other_home != agents["a01"].home_id
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="move", target_location=other_home))
    assert out.kind == "illegal"
    assert world.location_of("a01") == agents["a01"].home_id


def test_acquire_consumes_stock_and_money(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "market")
    before_stock = world.locations["market"].stock("bread")
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="acquire", resource="bread"))
    assert out.success and out.inventory_deltas == {"bread": 1}
    assert out.money_delta == -2.0
    assert world.locations["market"].stock("bread") == before_stock - 1


def test_acquire_closed_market_is_illegal(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "market")
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="acquire", resource="bread"), tick=2)
    assert out.kind == "illegal"


def test_acquire_without_money_fails(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "market")
    agents["a01"].money = 0.5
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="acquire", resource="bread"))
    assert out.kind == "insufficient_funds" and not out.success


def test_consume_requires_inventory(small_world):
    world, agents, hub = small_world
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="consume", resource="bread"))
    assert out.kind == "illegal"
    agents["a01"].inventory["bread"] = 1
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="consume", resource="bread"))
    assert out.success and out.need_deltas["hunger"] == 0.4 and out.inventory_deltas == {"bread": -1}


def test_work_pays_according_to_skill_and_energy(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "farm")
    agent = agents["a01"]
    agent.knowledge["job"].level = 1.0
    agent.needs["energy"].level = 1.0
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="work"), tick=10)
    assert out.success and out.money_delta == pytest.approx(3.0)  # habilidad y energía plenas: éxito seguro
    assert out.details["p_success"] == 1.0
    agent.knowledge["job"].level = 0.0
    agent.needs["energy"].level = 0.0
    results = [_resolve(world, agents, hub, "a01", ActionProposal(kind="work"), tick=10) for _ in range(40)]
    assert all(r.details["p_success"] == pytest.approx(0.45) for r in results)
    assert {r.kind for r in results} == {"ok", "poor_performance"}, "sin habilidad ni energía, a veces sale mal"
    assert all(r.money_delta == pytest.approx(0.75) for r in results if r.success)
    assert all(r.money_delta == pytest.approx(0.45) for r in results if not r.success)


def test_rest_is_better_at_home(small_world):
    world, agents, hub = small_world
    home = _resolve(world, agents, hub, "a01", ActionProposal(kind="rest"))
    _place(world, agents, "a01", "plaza")
    away = _resolve(world, agents, hub, "a01", ActionProposal(kind="rest"))
    assert home.need_deltas["energy"] > away.need_deltas["energy"]
    assert "safety" in home.need_deltas and "safety" not in away.need_deltas


def test_socialize_needs_presence_and_acceptance_depends_on_trust(small_world):
    world, agents, hub = small_world
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="socialize", target_agent="a02"))
    assert out.kind == "illegal"  # no están en el mismo lugar
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    agents["a02"].relationship_with("a01").trust = 1.0
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="socialize", target_agent="a02"))
    assert 0.7 <= out.details["p_accept"] <= 1.0  # confianza plena + reputación media + afinidad
    accepted = [
        _resolve(world, agents, hub, "a01", ActionProposal(kind="socialize", target_agent="a02")).success
        for _ in range(40)
    ]
    assert sum(accepted) >= 30
    agents["a02"].relationship_with("a01").trust = 0.0
    rejected = [
        not _resolve(world, agents, hub, "a01", ActionProposal(kind="socialize", target_agent="a02")).success
        for _ in range(40)
    ]
    assert sum(rejected) >= 20


def test_ask_info_records_truth_in_world_ledger_only(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    reply = InfoReply(responder_id="a02", resource="bread", kind="lie", claimed_location="school")
    prop = ActionProposal(kind="ask_info", target_agent="a02", resource="bread", payload={"reply": reply.model_dump()})
    out = _resolve(world, agents, hub, "a01", prop, event_id="ev_ask")
    assert out.success and out.details["claimed_location"] == "school"
    assert out.details["_world"] == {"intent": "lie", "was_true": False}
    assert world.state.info_ledger["ev_ask"]["deceptive"] is True
    omitted = ActionProposal(kind="ask_info", target_agent="a02", resource="bread",
                             payload={"reply": InfoReply(responder_id="a02", resource="bread", kind="omit").model_dump()})
    out = _resolve(world, agents, hub, "a01", omitted, event_id="ev_omit")
    assert out.kind == "no_reply" and out.details == {"responded": False}


def test_share_info_truthfulness_is_judged_by_world_state(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "plaza")
    _place(world, agents, "a02", "plaza")
    prop = ActionProposal(kind="share_info", target_agent="a02", resource="bread",
                          payload={"claimed_location": "market", "truthful": True})
    out = _resolve(world, agents, hub, "a01", prop, event_id="ev_share")
    assert out.success and out.details["_world"]["was_true"] is True
    world.locations["market"].resources["bread"] = 0
    out = _resolve(world, agents, hub, "a01", prop, event_id="ev_share2")
    # Intención honesta pero afirmación falsa: el mundo lo registra tal cual.
    assert out.details["_world"] == {"intent_truthful": True, "was_true": False}
    assert world.state.info_ledger["ev_share2"]["deceptive"] is False


def test_seek_care_and_study(small_world):
    world, agents, hub = small_world
    _place(world, agents, "a01", "hospital")
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="seek_care"))
    assert out.success and out.need_deltas["health"] == 0.3 and out.money_delta == -5.0
    assert world.locations["hospital"].stock("care") == 4
    _place(world, agents, "a01", "school")
    agents["a01"].personality.openness = 0.9
    out = _resolve(world, agents, hub, "a01", ActionProposal(kind="study"), tick=10)
    assert out.details["skill"] == "general" and out.kind in {"ok", "distracted"}


def test_scheduled_restock_and_shortage(small_world):
    world, agents, hub = small_world
    world.locations["market"].resources["bread"] = 1
    assert world.apply_scheduled_events(tick=7) == []
    deltas = world.apply_scheduled_events(tick=6)
    assert any(d["kind"] == "restock" and d["location_id"] == "market" for d in deltas)
    assert world.locations["market"].stock("bread") == 30
    shortage_tick = 10 * 24 + 6
    deltas = world.apply_scheduled_events(tick=shortage_tick)
    assert any(d["kind"] == "shortage" for d in deltas)
    assert world.locations["market"].stock("bread") == 3
