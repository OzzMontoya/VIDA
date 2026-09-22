"""VIDA-2.0: precios dinámicos, reputación pública, escala poblacional y ablaciones de identidad."""

from vida.experiments.transfer import ABLATIONS, run_transfer
from vida.simulation.engine import SimulationEngine
from vida.world.presets import build_world


def test_dynamic_prices_follow_local_stock(cfg):
    world = build_world(cfg)
    market = world.locations["market"]
    assert world.base_price("bread", "market") == 2.0
    assert world.price("bread", "market") == 2.0  # stock lleno = precio base
    market.resources["bread"] = 3  # queda un décimo
    assert world.price("bread", "market") > 2.5
    market.resources["bread"] = 60  # el doble de la reposición
    assert world.price("bread", "market") < 1.5
    c = cfg.model_copy(deep=True)
    c.world.dynamic_prices = False
    assert build_world(c).price("bread", "market") == 2.0


def test_population_scale_and_public_reputation(cfg):
    c = cfg.model_copy(deep=True)
    c.agents.n_agents = 100
    c.world.n_homes = 25
    world = build_world(c)
    assert world.locations["market"].restock["bread"] == 300  # ×10 por población
    engine = SimulationEngine(c, run_id="soc", sha="test")
    events = engine.step()
    perceived = [e.perception for e in events if e.perception and e.perception.visible_agents]
    assert perceived and all(set(p.visible_reputations) == set(p.visible_agents) for p in perceived)


def test_ablations_remove_single_components(small_cfg):
    cfg = small_cfg.model_copy(deep=True)
    cfg.agents.n_agents = 3
    rows = run_transfer(cfg, seed=3, split_ticks=48, horizon_ticks=24, agent_id="a01", conditions=["completa"] + ABLATIONS)
    by = {r["variant"]: r for r in rows}
    assert set(by) == {"completa", *ABLATIONS}
    assert by["completa"]["ici_vs_referencia"] == 1.0
    assert all(0.0 < by[a]["ici_vs_referencia"] <= 1.0 for a in ABLATIONS)
    assert by["sin_preferencias"]["memory"] > by["sin_preferencias"]["preferences"] - 1.0  # sanidad: dimensiones acotadas


def test_society_report_and_cli(small_cfg, tmp_path, capsys):
    from vida.cli import main
    from vida.evaluation.society import gini, pearson, render_society, society_report

    assert pearson([1, 2, 3], [2, 4, 6]) == 1.0 and pearson([1, 2], [1, 2]) is None and pearson([1, 1, 1], [1, 2, 3]) is None
    assert gini([1, 1, 1, 1]) == 0.0 and gini([0, 0, 0, 10]) > 0.7
    cfg = small_cfg.model_copy(deep=True)
    cfg.agents.n_agents = 5
    cfg.lifecycle.population_cap = 5  # sin nacimientos: la población se mantiene en 5
    engine = SimulationEngine(cfg, run_id="soc", sha="test")
    engine.run(ticks=96)
    report = society_report(engine.agents, engine.events)
    assert report["summary"]["alive"] == 5 and len(report["rows"]) == 5
    assert report["summary"]["bread_price_min"] is not None
    assert "Criterio 3" in render_society(report)
    data = tmp_path / "data"
    assert main(["--data-dir", str(data), "run", "--config", "config/default.yaml", "--seed", "8", "--ticks", "48",
                 "--run-id", "soccli", "--log-dir", str(tmp_path / "logs")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", str(data), "society", "--run", "soccli"]) == 0
    assert "sociedad" in capsys.readouterr().out
