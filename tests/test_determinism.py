"""Reproducibilidad: misma semilla → mismo historial de eventos; semilla distinta → distinto."""

from vida.simulation.engine import SimulationEngine
from vida.simulation.events import events_digest
from vida.simulation.logging import JsonlEventLogger, read_events


def _run(cfg, seed, ticks, run_id):
    c = cfg.model_copy(deep=True)
    c.run.seed = seed
    c.agents.n_agents = 4
    engine = SimulationEngine(c, run_id=run_id, sha="test")
    return engine.run(ticks=ticks), engine


def test_same_seed_same_digest_even_with_different_run_ids(cfg):
    s1, e1 = _run(cfg, 7, 100, "run_a")
    s2, e2 = _run(cfg, 7, 100, "run_b")
    assert s1.events_sha256 == s2.events_sha256
    assert s1.n_events == s2.n_events > 300
    assert [e.event_id for e in e1.events] == [e.event_id for e in e2.events]
    assert e1.agents["a01"].model_dump() == e2.agents["a01"].model_dump()


def test_different_seed_different_digest(cfg):
    s1, _ = _run(cfg, 7, 60, "run_a")
    s2, _ = _run(cfg, 8, 60, "run_b")
    assert s1.events_sha256 != s2.events_sha256


def test_agents_diverge_from_comparable_starts(cfg):
    _, engine = _run(cfg, 7, 240, "run")
    histories = {aid: [e.proposal.kind for e in engine.events if e.agent_id == aid and e.proposal] for aid in engine.agents}
    assert len({tuple(h) for h in histories.values()}) == len(histories), "cada vida debe ser distinta"
    assert all(len(engine.memories[aid].all()) > 20 for aid in engine.agents)


def test_jsonl_roundtrip_preserves_digest(cfg, tmp_path):
    c = cfg.model_copy(deep=True)
    c.run.seed = 7
    c.agents.n_agents = 3
    logger = JsonlEventLogger(tmp_path / "events.jsonl")
    engine = SimulationEngine(c, run_id="run_x", logger=logger, sha="test")
    summary = engine.run(ticks=48)
    loaded = read_events(tmp_path / "events.jsonl")
    assert len(loaded) == summary.n_events
    assert events_digest(loaded) == summary.events_sha256
