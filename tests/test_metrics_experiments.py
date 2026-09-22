"""Métricas, ICI, ejecutor de experimentos y transferencia entre soportes."""

from collections import Counter

from vida.evaluation.metrics import agent_metrics, continuity_index, cosine, entropy, jaccard, js_similarity
from vida.experiments import VARIANT_EXPERIMENTS
from vida.experiments.runner import effect_sizes, render_effects, render_summary, run_experiment, summarize
from vida.experiments.transfer import CONDITIONS, run_transfer
from vida.simulation.engine import SimulationEngine


def test_similarity_helpers():
    assert js_similarity([0.5, 0.5], [0.5, 0.5]) == 1.0
    assert js_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert jaccard(set(), set()) == 1.0 and jaccard({1, 2}, {2, 3}) == round(1 / 3, 6)
    assert cosine({"a": 1.0}, {"a": 1.0}) == 1.0 and cosine({"a": 1.0}, {"b": 1.0}) == 0.0
    assert entropy(Counter({"x": 2, "y": 2})) == 1.0 and entropy(Counter()) == 0.0


def test_agent_metrics_and_ici_on_a_real_run(small_cfg):
    cfg = small_cfg.model_copy(deep=True)
    cfg.agents.n_agents = 3
    engine = SimulationEngine(cfg, run_id="m", sha="test")
    initial = {aid: a.model_copy(deep=True) for aid, a in engine.agents.items()}
    engine.run(ticks=72)
    m = agent_metrics(engine.agents["a01"], engine.memories["a01"], engine.events, initial["a01"], 24)
    for key in ("memory_retained", "behavioural_consistency", "preference_stability", "mean_trust", "decision_entropy",
                "success_rate", "alive", "skill_gain_job"):
        assert key in m
    assert 0.0 <= m["behavioural_consistency"] <= 1.0 and m["alive"] == 1.0 and m["memory_retained"] > 0
    a, b = engine.agents["a01"], engine.agents["a02"]
    same = continuity_index(a, engine.memories["a01"], engine.events, a, engine.memories["a01"], engine.events)
    assert same["ici"] == 1.0 and all(v == 1.0 for v in same.values())
    other = continuity_index(a, engine.memories["a01"], engine.events, b, engine.memories["a02"], engine.events)
    assert other["ici"] < 1.0 and other["memory"] < 0.5 and 0.0 <= other["personality"] <= 1.0


def test_variant_experiment_runs_and_writes_files(small_cfg, tmp_path):
    cfg = small_cfg.model_copy(deep=True)
    cfg.agents.n_agents = 3
    variants, metrics = VARIANT_EXPERIMENTS["memory"]
    subset = {k: variants[k] for k in ("completa", "ausente")}
    result = run_experiment("memory", cfg, subset, seeds=[1], ticks=48, out_dir=tmp_path)
    assert len(result["rows"]) == 6  # 2 variantes × 1 semilla × 3 agentes
    assert set(result["summary"]) == {"completa", "ausente"}
    assert result["summary"]["ausente"]["memory_retained"]["mean"] < result["summary"]["completa"]["memory_retained"]["mean"]
    table = render_summary(result["summary"], metrics)
    assert "completa" in table and "ausente" in table
    path = tmp_path / "memory"
    assert any((p / "results.json").exists() and (p / "manifest.json").exists() for p in path.iterdir())


def test_environment_and_deception_variants_change_config(cfg):
    env_variants, _ = VARIANT_EXPERIMENTS["environment"]
    c = env_variants["escasez"](cfg.model_copy(deep=True))
    assert c.world.restock_factor == 0.4 and c.world.shortage_days
    dec_variants, _ = VARIANT_EXPERIMENTS["deception"]
    assert dec_variants["deshonestos"](cfg.model_copy(deep=True)).agents.initial_honesty == 0.1
    assert summarize([{"variant": "x", "seed": 1, "v": 1.0}, {"variant": "x", "seed": 2, "v": 3.0}])["x"]["v"] == {"mean": 2.0, "sd": 1.0, "n": 2}


def test_transfer_conditions_order_continuity(small_cfg):
    cfg = small_cfg.model_copy(deep=True)
    cfg.agents.n_agents = 3
    rows = run_transfer(cfg, seed=3, split_ticks=48, horizon_ticks=24, agent_id="a01")
    by = {r["variant"]: r for r in rows}
    assert set(by) == set(CONDITIONS)
    assert by["completa"]["ici_vs_referencia"] == 1.0, "la continuación sin intervención es la referencia"
    assert by["ninguna"]["ici_vs_referencia"] < by["completa"]["ici_vs_referencia"]
    assert by["ninguna"]["memory"] < by["solo_memoria"]["memory"]
    assert by["ninguna"]["personality"] < 1.0 and by["solo_personalidad"]["personality"] == 1.0
    assert by["solo_conocimientos"]["knowledge"] >= by["ninguna"]["knowledge"]
    assert 0.0 < by["memoria_borrada_50"]["ici_vs_referencia"] <= 1.0
    # El clon "completa" reproduce exactamente la continuación original: mismo mundo, mismos flujos aleatorios.
    assert by["completa"]["ici_vs_previo"] <= 1.0 and by["completa"]["alive"] == 1.0


def test_effect_sizes_rank_metrics_by_difference():
    rows = [
        {"variant": "a", "seed": 1, "x": 1.0, "y": 5.0}, {"variant": "a", "seed": 2, "x": 1.2, "y": 5.1},
        {"variant": "b", "seed": 1, "x": 3.0, "y": 5.0}, {"variant": "b", "seed": 2, "x": 3.2, "y": 5.1},
    ]
    eff = effect_sizes(rows, "a", "b")
    assert [e["metric"] for e in eff] == ["x", "y"]
    assert eff[0]["d"] < -1.5 and eff[1]["d"] == 0.0
    assert "x" in render_effects(eff, "a", "b")
    assert effect_sizes(rows, "a", "zzz") == []
