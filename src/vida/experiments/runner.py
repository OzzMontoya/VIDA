"""Ejecutor de experimentos: variantes × semillas → métricas por agente → resumen por variante.

Cada experimento define variantes como funciones que modifican una copia de la
configuración base. El ejecutor corre cada variante con cada semilla (sin base
de datos, en memoria), calcula las métricas por agente y guarda:

- ``results.json``: una fila por (variante, semilla, agente) con todas las métricas.
- ``summary.json``: media y desviación por variante y métrica.
- ``manifest.json``: configuración base, hash, versión de código y semillas.

Reproducibilidad: las corridas son deterministas por semilla; el manifiesto
permite repetir el experimento exactamente.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from vida import __version__
from vida.evaluation.metrics import agent_metrics
from vida.simulation.config import RunConfig, canonical_json, config_hash
from vida.simulation.engine import SimulationEngine, git_sha

Variant = Callable[[RunConfig], RunConfig]


def run_variant(cfg: RunConfig, seed: int, ticks: int, run_id: str) -> tuple[SimulationEngine, list[dict[str, Any]]]:
    """Corre una configuración y devuelve el motor y las métricas por agente."""
    c = cfg.model_copy(deep=True)
    c.run.seed = seed
    c.run.ticks = ticks
    engine = SimulationEngine(c, run_id=run_id, sha="experiment")
    initial = {aid: a.model_copy(deep=True) for aid, a in engine.agents.items()}
    engine.run(ticks=ticks)
    rows = []
    for aid in sorted(engine.agents):
        metrics = agent_metrics(engine.agents[aid], engine.memories[aid], engine.events, initial[aid], c.run.ticks_per_day)
        rows.append({"agent_id": aid, **metrics})
    return engine, rows


def summarize(rows: list[dict[str, Any]], group_key: str = "variant") -> dict[str, dict[str, dict[str, float]]]:
    """Media y desviación estándar de cada métrica numérica por grupo."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(str(r[group_key]), []).append(r)
    summary: dict[str, dict[str, dict[str, float]]] = {}
    for name, items in groups.items():
        metrics = sorted(k for k in items[0] if isinstance(items[0][k], (int, float)) and k not in {"seed"})
        summary[name] = {}
        for k in metrics:
            values = [float(r[k]) for r in items if isinstance(r.get(k), (int, float))]
            if not values:
                continue
            summary[name][k] = {
                "mean": round(statistics.fmean(values), 6),
                "sd": round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0,
                "n": len(values),
            }
    return summary


def run_experiment(name: str, base_cfg: RunConfig, variants: dict[str, Variant], *, seeds: list[int], ticks: int,
                   out_dir: Path | None = None, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for variant_name, make in sorted(variants.items()):
        for seed in seeds:
            if progress:
                progress(f"{name}: variante {variant_name}, semilla {seed}")
            cfg = make(base_cfg.model_copy(deep=True))
            _, agent_rows = run_variant(cfg, seed, ticks, run_id=f"exp_{name}_{variant_name}_{seed}")
            for r in agent_rows:
                rows.append({"variant": variant_name, "seed": seed, **r})
    result = {
        "name": name, "seeds": seeds, "ticks": ticks, "variants": sorted(variants),
        "rows": rows, "summary": summarize(rows),
    }
    if out_dir is not None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = out_dir / name / stamp
        target.mkdir(parents=True, exist_ok=True)
        (target / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        (target / "summary.json").write_text(json.dumps(result["summary"], ensure_ascii=False, indent=1), encoding="utf-8")
        (target / "manifest.json").write_text(json.dumps({
            "name": name, "seeds": seeds, "ticks": ticks, "variants": sorted(variants), "code_version": __version__,
            "git_sha": git_sha(), "base_config_hash": config_hash(base_cfg), "base_config": json.loads(canonical_json(base_cfg)),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        result["path"] = str(target)
    return result


def render_summary(summary: dict[str, dict[str, dict[str, float]]], metrics: list[str]) -> str:
    """Tabla de texto: filas = variantes, columnas = métricas (media ± sd)."""
    variants = list(summary)
    width = max(12, max(len(v) for v in variants) + 2) if variants else 12
    header = f"{'variante':<{width}}" + "".join(f"{m[:22]:>24}" for m in metrics)
    lines = [header, "-" * len(header)]
    for v in variants:
        cells = []
        for m in metrics:
            cell = summary[v].get(m)
            cells.append(f"{cell['mean']:.3f} ± {cell['sd']:.3f}" if cell else "—")
        lines.append(f"{v:<{width}}" + "".join(f"{c:>24}" for c in cells))
    return "\n".join(lines)
