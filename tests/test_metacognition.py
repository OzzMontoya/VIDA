"""Criterios 4 y 5: metacognición e incertidumbre comunicada."""

from vida.agents.selfmodel import ContextTable
from vida.evaluation.metacognition import communicated_uncertainty, metacognition_report, render_metacognition
from vida.simulation.engine import SimulationEngine


def test_confidence_grows_with_evidence_and_specificity():
    table = ContextTable()
    levels = ["a|x|p1|h=ok|e=ok", "a|x|p1", "a|x", "a"]
    p0, c0 = table.predict_with_confidence(levels)
    assert p0 == 0.7 and c0 < 0.05
    for _ in range(3):
        table.update(["a"], True)
    p1, c1 = table.predict_with_confidence(levels)  # sólo el nivel general tiene evidencia
    for _ in range(12):
        table.update(levels, True)
    p2, c2 = table.predict_with_confidence(levels)  # el nivel específico, con mucha evidencia
    assert c0 < c1 < c2 and p2 > 0.9


def test_engine_records_confidence_and_reports(small_cfg, tmp_path, capsys):
    from vida.cli import main

    cfg = small_cfg.model_copy(deep=True)
    cfg.lifecycle.population_cap = 2  # sin nacimientos
    engine = SimulationEngine(cfg, run_id="mc", sha="test")
    engine.run(ticks=96)
    preds = [e.prediction for e in engine.events if e.event_type == "action"]
    assert all("confidence" in p and 0.0 <= p["confidence"] <= 1.0 for p in preds)
    report = metacognition_report(engine.events)
    assert report["summary"]["agents"] == 2 and report["summary"]["pooled_own"]["n"] == len(preds)
    comm = communicated_uncertainty(engine.events)
    assert comm["n"] >= 0 and "Criterio 4" in render_metacognition(report, comm)
    data = tmp_path / "data"
    assert main(["--data-dir", str(data), "run", "--config", "config/default.yaml", "--seed", "9", "--ticks", "48",
                 "--run-id", "mccli", "--log-dir", str(tmp_path / "logs")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", str(data), "metacognition", "--run", "mccli"]) == 0
    assert "metacognición" in capsys.readouterr().out
