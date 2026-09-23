"""Criterio 6: integración informacional (proxy de Φ) sobre el registro de eventos."""

import random

from vida.evaluation.integration import COMPONENTS, integration_from_samples, integration_report, mutual_information, render_integration
from vida.simulation.engine import SimulationEngine


def test_mutual_information_basic():
    assert mutual_information([0, 1, 0, 1], ["a", "b", "a", "b"]) == 1.0
    assert abs(mutual_information([0, 1, 0, 1], ["a", "a", "b", "b"])) < 1e-9


def _minds(n, rng):
    return [{f: rng.random() for c in COMPONENTS for f in ("hunger", "energy", "memory_valence", "memory_n", "self_error",
             "self_n", "affection_here", "trust_here", "ambition", "honesty", "food_belief", "known_locations")}
            for _ in range(n)]


def test_phi_detects_irreducible_conjunctions():
    rng = random.Random(3)
    minds = _minds(4000, rng)
    # Paridad de los seis componentes: ningún subconjunto propio informa; toda bipartición pierde el bit entero.
    keys = ["hunger", "memory_valence", "self_error", "affection_here", "ambition", "food_belief"]
    parity = ["x" if sum(m[k] > 0.5 for k in keys) % 2 else "y" for m in minds]
    r = integration_from_samples(minds, parity, n_shuffles=5)
    assert r["phi_bits"] > 0.6 and r["synergy_bits"] > 0.6
    # Paridad de tres: sinergia alta, pero la bipartición que deja los tres juntos no pierde nada → Φ ≈ 0.
    three = ["x" if sum(m[k] > 0.5 for k in keys[:3]) % 2 else "y" for m in minds]
    r0 = integration_from_samples(minds, three, n_shuffles=5)
    assert r0["synergy_bits"] > 0.6 and abs(r0["phi_bits"]) < 0.1
    # XOR de dos componentes: hay sinergia sobre cualquier componente aislado, pero la bipartición que los
    # deja juntos no pierde nada, así que Φ ≈ 0 (irreducible sólo dentro de una parte).
    xor = ["x" if (m["hunger"] > 0.5) != (m["ambition"] > 0.5) else "y" for m in minds]
    r1 = integration_from_samples(minds, xor, n_shuffles=5)
    assert r1["synergy_bits"] > 0.8 and abs(r1["phi_bits"]) < 0.1
    # Un solo componente decide: el todo no añade nada.
    single = ["x" if m["hunger"] > 0.5 else "y" for m in minds]
    r2 = integration_from_samples(minds, single, n_shuffles=5)
    assert abs(r2["phi_bits"]) < 0.05 and r2["information_parts_bits"]["body"] > 0.9
    # Acción aleatoria: la corrección por permutación deja la información cerca de cero.
    noise = [rng.choice("xy") for _ in minds]
    r3 = integration_from_samples(minds, noise, n_shuffles=5)
    assert abs(r3["information_whole_bits"]) < 0.05


def test_engine_records_mind_and_cli(small_cfg, tmp_path, capsys):
    from vida.cli import main

    cfg = small_cfg.model_copy(deep=True)
    cfg.lifecycle.population_cap = 2
    engine = SimulationEngine(cfg, run_id="phi", sha="test")
    engine.run(ticks=72)
    minds = [e.mind for e in engine.events if e.event_type == "action"]
    assert minds and all(set(m) >= {"hunger", "self_error", "affection_here", "ambition", "food_belief", "memory_n"} for m in minds)
    report = integration_report(engine.events, n_shuffles=3, min_events=50)
    assert report["pooled"]["n"] == len(minds) and report["pooled"]["phi_bits"] is not None
    assert "Criterio 6" in render_integration(report)
    data = tmp_path / "data"
    assert main(["--data-dir", str(data), "run", "--config", "config/default.yaml", "--seed", "4", "--ticks", "48",
                 "--run-id", "phicli", "--log-dir", str(tmp_path / "logs")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", str(data), "integration", "--run", "phicli", "--shuffles", "3"]) == 0
    assert "integración" in capsys.readouterr().out
