"""Motor LLM: elección validada contra candidatos, degradación a reglas, respuestas y caché (sin red)."""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("anthropic")
import anthropic  # noqa: E402

from vida.agents.decision import DecisionContext, build_engine  # noqa: E402
from vida.agents.llm_decision import LLMCache, LLMEngine  # noqa: E402
from vida.memory.base import AgentMemory  # noqa: E402
from vida.simulation.engine import SimulationEngine  # noqa: E402
from vida.world.actions import InfoRequest  # noqa: E402


class FakeMessages:
    """Simula ``client.messages`` / ``client.beta.messages`` devolviendo JSON preparado o lanzando errores."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        reply = self.replies.pop(0) if self.replies else {"choice": "__sin_respuesta__", "rationale": ""}
        if isinstance(reply, Exception):
            raise reply
        stop = "refusal" if reply == "REFUSE" else "end_turn"
        text = "" if reply == "REFUSE" else json.dumps(reply)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], stop_reason=stop,
            usage=SimpleNamespace(input_tokens=1500, output_tokens=40, cache_read_input_tokens=0),
        )


class FakeClient:
    def __init__(self, replies):
        self.messages = FakeMessages(replies)
        self.beta = SimpleNamespace(messages=self.messages)


def _ctx(world, agents, cfg, agent_id, tick=8):
    agent = agents[agent_id]
    perception = world.perceive(agent, agents, tick)
    return DecisionContext(
        agent=agent, perception=perception, memories=[], memory=AgentMemory(agent_id, cfg.memory),
        available_actions=world.legal_actions(agent, perception), location_info=world.public_location_info(),
        prices={r: world.price(r) for r in ("bread", "fruit", "care")}, distance=world.distance,
        tick=tick, ticks_per_day=cfg.run.ticks_per_day,
    )


def _llm_cfg(cfg, tmp_path, **overrides):
    c = cfg.model_copy(deep=True)
    c.decision.engine = "llm_v1"
    c.decision.llm.cache_path = str(tmp_path / "cache.sqlite")
    for k, v in overrides.items():
        setattr(c.decision.llm, k, v)
    return c


def test_llm_choice_is_taken_when_valid(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path)
    client = FakeClient([{"choice": "move@market", "rationale": "tengo hambre y quiero comprar pan"}])
    engine = LLMEngine(cfg.decision, client=client)
    proposal, record = engine.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))
    assert proposal.kind == "move" and proposal.target_location == "market"
    assert record.engine == "llm_v1" and record.chosen == "move@market"
    assert proposal.rationale == "tengo hambre y quiero comprar pan"
    request = client.messages.requests[0]
    assert request["model"] == "claude-opus-5"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert request["output_config"]["effort"] == "low"
    assert request["betas"] == ["server-side-fallback-2026-07-01"] and request["fallbacks"] == "default"
    assert "move@market" in request["messages"][0]["content"]
    assert engine.stats["calls"] == 1 and engine.estimated_cost_usd() > 0


def test_invalid_choice_refusal_and_api_errors_fall_back_to_rules(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path, cache_path=None)  # sin caché: cada llamada consume una respuesta
    fake_response = SimpleNamespace(status_code=500, headers={}, request=None)
    replies = [
        {"choice": "fly@moon", "rationale": "acción inexistente"},
        "REFUSE",
        anthropic.APIStatusError("boom", response=fake_response, body=None),
        anthropic.APIConnectionError(request=SimpleNamespace()),
    ]
    engine = LLMEngine(cfg.decision, client=FakeClient(replies))
    for _ in range(4):
        proposal, record = engine.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))
        assert proposal.kind in {"rest", "move", "idle"}
        assert record.engine == "llm_v1/fallback:rules_v1"
    assert engine.stats["fallbacks"] == 4 and engine.stats["refusals"] == 1 and engine.stats["invalid"] == 1


def test_fallback_can_be_disabled(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path, fallback_to_rules=False)
    engine = LLMEngine(cfg.decision, client=FakeClient([{"choice": "nope", "rationale": ""}]))
    with pytest.raises(RuntimeError):
        engine.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))


def test_only_listed_agents_use_llm(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path, agents=["a02"])
    client = FakeClient([{"choice": "rest", "rationale": "descanso"}])
    engine = LLMEngine(cfg.decision, client=client)
    _, r1 = engine.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))
    _, r2 = engine.decide(_ctx(world, agents, cfg, "a02"), hub.sub("d"))
    assert r1.engine == "rules_v1" and r2.engine == "llm_v1"
    assert len(client.messages.requests) == 1


def test_cache_replays_without_calling_api(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path)
    cache = LLMCache(tmp_path / "cache.sqlite")
    engine = LLMEngine(cfg.decision, client=FakeClient([{"choice": "rest", "rationale": "cansancio"}]), cache=cache)
    p1, _ = engine.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))
    engine2 = LLMEngine(cfg.decision, client=FakeClient([]), cache=cache)  # sin respuestas: sólo puede usar la caché
    p2, r2 = engine2.decide(_ctx(world, agents, cfg, "a01"), hub.sub("d"))
    assert p1.key() == p2.key() == "rest" and r2.engine == "llm_v1"
    assert engine2.stats["cache_hits"] == 1 and engine2.stats["calls"] == 0


def test_reply_and_share_are_validated_against_known_locations(small_world, small_cfg, tmp_path):
    world, agents, hub = small_world
    cfg = _llm_cfg(small_cfg, tmp_path, cache_path=None)
    engine = LLMEngine(cfg.decision, client=FakeClient([
        {"kind": "lie", "claimed_location": "school", "rationale": "quiero el pan para mí"},
        {"kind": "lie", "claimed_location": "narnia", "rationale": "lugar inventado"},
        {"kind": "omit", "claimed_location": None, "rationale": ""},
        {"truthful": False, "claimed_location": "hospital", "rationale": "engaño"},
    ]))
    req = InfoRequest(asker_id="a02", responder_id="a01", resource="bread", tick=8)
    lie = engine.decide_reply(_ctx(world, agents, cfg, "a01"), req, hub.sub("d"))
    assert lie.kind == "lie" and lie.claimed_location == "school"
    fixed = engine.decide_reply(_ctx(world, agents, cfg, "a01"), req, hub.sub("d"))
    assert fixed.claimed_location == "market" and fixed.kind == "truth"  # lugar inventado → se corrige a lo creído
    assert engine.decide_reply(_ctx(world, agents, cfg, "a01"), req, hub.sub("d")).kind == "omit"
    share = engine.decide_share(_ctx(world, agents, cfg, "a01"), "a02", "bread", hub.sub("d"))
    assert share == {"claimed_location": "hospital", "truthful": False}


def test_build_engine_and_full_run_with_fake_llm(small_cfg, tmp_path):
    cfg = _llm_cfg(small_cfg, tmp_path, agents=["a01"])
    assert build_engine(cfg.decision).name == "llm_v1"
    engine = LLMEngine(cfg.decision, client=FakeClient([]))  # todo recurre a reglas
    sim = SimulationEngine(cfg, run_id="llm_test", decision_engine=engine, sha="test")
    summary = sim.run(ticks=24)
    assert summary.decision_engine == "llm_v1"
    assert summary.llm_stats["calls"] == 24 and summary.llm_stats["fallbacks"] == 24
    assert summary.llm_cost_usd > 0.0  # el cliente simulado reporta tokens aunque la elección sea inválida
    engines = {e.decision.engine for e in sim.events if e.decision}
    assert engines == {"rules_v1", "llm_v1/fallback:rules_v1"}
