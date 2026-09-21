"""Memoria: orden de recuperación, empates por id, olvido y codificación por tipo."""

from vida.memory import autobiographical, episodic, procedural, semantic
from vida.memory.base import AgentMemory
from vida.world.actions import ActionOutcome


def _mem(cfg, agent_id="a01"):
    return AgentMemory(agent_id, cfg.memory)


def test_retrieval_orders_by_recency_importance_relevance(cfg):
    m = _mem(cfg)
    old_relevant = m.add("episodic", 0, "viejo relevante", importance=0.2, tags={"loc:market", "res:bread"})
    recent_irrelevant = m.add("episodic", 95, "reciente irrelevante", importance=0.2, tags={"loc:school"})
    important = m.add("episodic", 50, "importante", importance=1.0, tags={"agent:a02"})
    got = m.retrieve({"loc:market", "res:bread"}, tick=100, k=3)
    assert got[0].id == important.id
    assert {got[1].id, got[2].id} == {old_relevant.id, recent_irrelevant.id}
    # Recuperar registra el acceso y refresca la recencia.
    assert important.access_count == 1 and important.last_access_tick == 100


def test_ties_break_by_id_deterministically(cfg):
    m = _mem(cfg)
    ids = [m.add("episodic", 10, f"m{i}", importance=0.5, tags={"x"}).id for i in range(5)]
    got = [r.id for r in m.retrieve({"x"}, tick=10, k=5)]
    assert got == sorted(ids)


def test_consolidation_forgets_only_old_unimportant_episodes(cfg):
    m = _mem(cfg)
    day = cfg.run.ticks_per_day
    old_trivial = m.add("episodic", 0, "trivial", importance=0.1)
    old_important = m.add("episodic", 0, "importante", importance=0.9)
    recent_trivial = m.add("episodic", 9 * day, "reciente", importance=0.1)
    old_semantic = m.add("semantic", 0, "hecho", importance=0.1)
    forgotten = m.consolidate(tick=10 * day, ticks_per_day=day)
    assert forgotten == [old_trivial.id]
    assert {r.id for r in m.all()} == {old_important.id, recent_trivial.id, old_semantic.id}


def test_episodic_encoding_uses_outcome_not_rationale(small_world):
    world, agents, hub = small_world
    cfg_mem = AgentMemory("a01", __import__("vida.simulation.config", fromlist=["MemorySection"]).MemorySection())
    out = ActionOutcome(tick=5, agent_id="a01", action="acquire", kind="resource_absent", success=False,
                        location_id="market", resource="bread", valence=-0.7,
                        details={"attributed_source_agent": "a02"})
    rec = episodic.encode_outcome(cfg_mem, agents["a01"], out, "e1", {"a02": "Luis"})
    assert "Luis" in rec.content and "No había bread" in rec.content
    assert rec.importance >= 0.7 and rec.valence == -0.7
    assert set(rec.tags) >= {"action:acquire", "res:bread", "loc:market", "outcome:resource_absent"}
    idle = ActionOutcome(tick=5, agent_id="a01", action="idle", kind="ok", success=True, location_id="plaza")
    assert episodic.encode_outcome(cfg_mem, agents["a01"], idle, "e2", {}) is None


def test_semantic_facts_accumulate_evidence(cfg):
    m = _mem(cfg)
    r1 = semantic.record_availability(m, "bread", "market", True, tick=1)
    r2 = semantic.record_availability(m, "bread", "market", True, tick=2)
    r3 = semantic.record_availability(m, "bread", "market", False, tick=3)
    assert r1.id == r2.id == r3.id
    assert r3.confirmations == 2 and r3.refutations == 1
    assert r3.valence == round(1 / 3, 6) and "suele haber" in r3.content
    assert len(m.by_kind("semantic")) == 1


def test_procedural_and_autobiographical(cfg, small_world):
    _, agents, _ = small_world
    m = _mem(cfg)
    agent = agents["a01"]
    agent.knowledge["job"].level = 0.5
    p1 = procedural.encode_skill_gain(m, agent, "job", 0.02, tick=1, event_id="e1")
    p2 = procedural.encode_skill_gain(m, agent, "job", 0.02, tick=2, event_id="e2")
    assert p1.id == p2.id and p2.confirmations == 2 and "0.50" in p2.content
    outcomes = [
        ActionOutcome(tick=t, agent_id="a01", action="work", kind="ok", success=True, location_id="farm", valence=0.3)
        for t in range(3)
    ] + [
        ActionOutcome(tick=5, agent_id="a01", action="socialize", kind="ok", success=True, location_id="plaza",
                      target_agent="a02", valence=0.5),
        ActionOutcome(tick=6, agent_id="a01", action="acquire", kind="resource_absent", success=False,
                      location_id="market", resource="bread", valence=-0.7),
    ]
    summary = autobiographical.daily_summary(m, agent, day=0, tick=23, outcomes=outcomes, names={"a02": "Luis"})
    assert summary.kind == "autobiographical"
    assert "trabajé 3 veces" in summary.content and "Luis" in summary.content
    assert "acquire terminó en resource_absent" in summary.content
    assert autobiographical.daily_summary(m, agent, 1, 47, [], {}) is None
