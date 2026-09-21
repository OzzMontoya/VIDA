"""Persistencia: ida y vuelta de eventos, memorias y snapshots de estado en SQLite."""

from vida.database.repository import RunRepository
from vida.simulation.engine import SimulationEngine


def _engine_with_repo(cfg, tmp_path, ticks=48):
    c = cfg.model_copy(deep=True)
    c.run.seed = 7
    c.agents.n_agents = 3
    repo = RunRepository(tmp_path / "vida.sqlite")
    engine = SimulationEngine(c, run_id="run_db", repo=repo, sha="deadbeef")
    summary = engine.run(ticks=ticks)
    return engine, repo, summary


def test_run_metadata_and_agents(cfg, tmp_path):
    engine, repo, summary = _engine_with_repo(cfg, tmp_path)
    meta = repo.run_meta("run_db")
    assert meta["seed"] == 7 and meta["git_sha"] == "deadbeef"
    assert meta["n_ticks"] == 48 and meta["n_events"] == summary.n_events
    assert meta["events_sha256"] == summary.events_sha256
    assert meta["finished_at"] is not None
    agents = repo.agents_meta("run_db")
    assert list(agents) == ["a01", "a02", "a03"]
    assert agents["a01"]["name"] == "Ana"
    assert repo.list_run_ids() == ["run_db"]


def test_events_roundtrip_in_order(cfg, tmp_path):
    engine, repo, _ = _engine_with_repo(cfg, tmp_path)
    for aid in engine.agents:
        stored = repo.events_for_agent("run_db", aid)
        original = [e for e in engine.events if e.agent_id == aid]
        assert [e.model_dump() for e in stored] == [e.model_dump() for e in original]
        assert [e.seq for e in stored] == sorted(e.seq for e in stored)
    assert len(repo.all_events("run_db")) == len(engine.events)


def test_memories_and_state_history(cfg, tmp_path):
    engine, repo, _ = _engine_with_repo(cfg, tmp_path, ticks=cfg.run.ticks_per_day * 9)
    mem = engine.memories["a01"]
    stored = repo.memories_for("run_db", "a01")
    assert [m.model_dump() for m in stored] == [m.model_dump() for m in mem.all()]
    assert repo.forgotten_count("run_db", "a01") == len(mem.forgotten)
    history = repo.state_history("run_db", "a01")
    ticks = [t for t, _ in history]
    assert ticks[0] == 0 and ticks[-1] == 9 * cfg.run.ticks_per_day
    assert all(b > a for a, b in zip(ticks, ticks[1:]))
    assert history[-1][1].model_dump() == engine.agents["a01"].model_dump()
    repo.close()
