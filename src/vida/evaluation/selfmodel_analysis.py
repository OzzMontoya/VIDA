"""Análisis del automodelo por evidencia propia y por acción (criterio 1).

Reconstruye, a partir de los eventos de una corrida y en su orden de secuencia,
la tabla de contexto de cada agente y la poblacional, y agrupa el error de
predicción por cuántos intentos propios tenía el agente en el contexto exacto
al momento de predecir. Así se separa la falta de muestra (ruido) de la falta
de señal individual.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from vida.agents.selfmodel import ContextTable, context_levels
from vida.simulation.events import EventRecord

EVIDENCE_BINS: list[tuple[int, int]] = [(0, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 10**9)]


def advantage_by_evidence(events: list[EventRecord], ticks_per_day: int, min_own_for_actions: int = 6) -> dict[str, Any]:
    own: dict[str, ContextTable] = defaultdict(ContextTable)
    pop = ContextTable()
    by_bin: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0, 0.0, 0.0])
    by_action: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0.0])
    for e in sorted(events, key=lambda e: e.seq):
        if e.event_type != "action" or e.outcome is None or e.proposal is None or e.state_before is None:
            continue
        p, o = e.proposal, e.outcome
        target = p.resource or p.target_agent or p.target_location
        levels = context_levels(p.kind, target, e.hour, ticks_per_day, e.state_before.needs)
        n_own = own[e.agent_id].counts.get(levels[0], [0, 0])[1]
        err_own = abs(own[e.agent_id].predict(levels) - (1.0 if o.success else 0.0))
        err_pop = abs(pop.predict(levels) - (1.0 if o.success else 0.0))
        for lo, hi in EVIDENCE_BINS:
            if lo <= n_own <= hi:
                cell = by_bin[(lo, hi)]
                cell[0] += 1; cell[1] += err_own; cell[2] += err_pop
        if n_own >= min_own_for_actions:
            cell = by_action[p.kind]
            cell[0] += 1; cell[1] += err_own; cell[2] += err_pop
        own[e.agent_id].update(levels, o.success)
        pop.update(levels, o.success)

    def rows(table: dict) -> list[dict[str, Any]]:
        out = []
        for key, (n, eo, ep) in table.items():
            if n:
                out.append({"key": key, "n": n, "own_error": round(eo / n, 6), "population_error": round(ep / n, 6),
                            "advantage": round((ep - eo) / n, 6)})
        return out

    bins = rows(by_bin)
    for r in bins:
        lo, hi = r["key"]
        r["key"] = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
    actions = sorted(rows(by_action), key=lambda r: -r["n"])
    return {"by_evidence": bins, "by_action": actions, "min_own_for_actions": min_own_for_actions}


def render_selfmodel_analysis(result: dict[str, Any]) -> str:
    lines = ["Ventaja del automodelo (error poblacional − error propio) por evidencia propia en el contexto exacto",
             f"{'intentos propios':<18}{'n':>8}{'err propio':>12}{'err pobl.':>12}{'ventaja':>10}"]
    for r in result["by_evidence"]:
        lines.append(f"{r['key']:<18}{r['n']:>8}{r['own_error']:>12.3f}{r['population_error']:>12.3f}{r['advantage']:>+10.3f}")
    lines.append(f"Por acción (≥{result['min_own_for_actions']} intentos propios):")
    for r in result["by_action"]:
        lines.append(f"{r['key']:<18}{r['n']:>8}{r['own_error']:>12.3f}{r['population_error']:>12.3f}{r['advantage']:>+10.3f}")
    return "\n".join(lines)
