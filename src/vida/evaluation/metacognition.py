"""Metacognición (criterio 4) y calibración de la incertidumbre comunicada (criterio 5).

Criterio 4 · sensibilidad metacognitiva: un agente no sólo predice si su
acción saldrá bien; también estima cuánta confianza tiene en esa predicción.
Si acierta más cuando dice estar seguro, "sabe cuándo sabe". Se mide como la
diferencia de precisión entre las predicciones de confianza alta y baja
(mediana propia) y como la correlación confianza–precisión. Se compara con la
confianza del observador externo sobre las mismas predicciones.

Criterio 5 · incertidumbre comunicada: al informar a otro, el agente declara
una confianza. Si esa confianza declarada rastrea la verdad de lo que dice
(según el libro del mundo), la comunicación de incertidumbre es informativa;
si los mentirosos declaran confianza alta, deja de serlo.

Ninguna de las dos medidas afirma vivencia: son propiedades funcionales.
"""

from __future__ import annotations

from typing import Any

from vida.evaluation.society import pearson
from vida.simulation.events import EventRecord


def _sensitivity(pairs: list[tuple[float, float]]) -> dict[str, float | None]:
    """``pairs`` = (confianza, precisión = 1 − error)."""
    if len(pairs) < 6:
        return {"n": len(pairs), "sensitivity": None, "calibration_r": None}
    confs = sorted(c for c, _ in pairs)
    median = confs[len(confs) // 2]
    high = [a for c, a in pairs if c > median]
    low = [a for c, a in pairs if c <= median]
    if not high or not low:
        return {"n": len(pairs), "sensitivity": None, "calibration_r": pearson([c for c, _ in pairs], [a for _, a in pairs])}
    return {
        "n": len(pairs),
        "sensitivity": round(sum(high) / len(high) - sum(low) / len(low), 6),
        "calibration_r": pearson([c for c, _ in pairs], [a for _, a in pairs]),
    }


def metacognition_report(events: list[EventRecord]) -> dict[str, Any]:
    own_by_agent: dict[str, list[tuple[float, float]]] = {}
    base_by_agent: dict[str, list[tuple[float, float]]] = {}
    for e in events:
        if e.event_type != "action" or not e.prediction or "confidence" not in e.prediction:
            continue
        p = e.prediction
        own_by_agent.setdefault(e.agent_id, []).append((p["confidence"], 1.0 - p["error"]))
        base_by_agent.setdefault(e.agent_id, []).append((p["baseline_confidence"], 1.0 - p["baseline_error"]))
    rows = []
    for aid in sorted(own_by_agent):
        own = _sensitivity(own_by_agent[aid])
        base = _sensitivity(base_by_agent[aid])
        rows.append({"agent_id": aid, "n": own["n"], "own_sensitivity": own["sensitivity"], "own_calibration_r": own["calibration_r"],
                     "external_sensitivity": base["sensitivity"], "external_calibration_r": base["calibration_r"]})
    valid = [r for r in rows if r["own_sensitivity"] is not None]
    pooled_own = _sensitivity([pr for prs in own_by_agent.values() for pr in prs])
    pooled_base = _sensitivity([pr for prs in base_by_agent.values() for pr in prs])
    summary = {
        "agents": len(rows),
        "agents_with_positive_sensitivity": sum(1 for r in valid if r["own_sensitivity"] > 0),
        "mean_own_sensitivity": round(sum(r["own_sensitivity"] for r in valid) / len(valid), 6) if valid else None,
        "mean_external_sensitivity": round(sum(r["external_sensitivity"] for r in valid if r["external_sensitivity"] is not None)
                                           / max(1, sum(1 for r in valid if r["external_sensitivity"] is not None)), 6) if valid else None,
        "pooled_own": pooled_own, "pooled_external": pooled_base,
    }
    return {"rows": rows, "summary": summary}


def communicated_uncertainty(events: list[EventRecord]) -> dict[str, Any]:
    """Confianza declarada al responder una pregunta frente a la verdad de la respuesta (libro del mundo)."""
    claimed: list[float] = []
    truth: list[float] = []
    by_intent: dict[str, list[float]] = {}
    for e in events:
        o = e.outcome
        if e.event_type != "action" or o is None or o.action != "ask_info" or not o.success:
            continue
        w = o.details.get("_world") or {}
        if "was_true" not in w or w["was_true"] is None:
            continue
        c = float(o.details.get("claimed_confidence", 1.0))
        claimed.append(c); truth.append(1.0 if w["was_true"] else 0.0)
        intent = w.get("intent", "?")
        cell = by_intent.setdefault(intent, [0, 0.0, 0.0])
        cell[0] += 1; cell[1] += c; cell[2] += 1.0 if w["was_true"] else 0.0
    return {
        "n": len(claimed),
        "calibration_r": pearson(claimed, truth),
        "by_intent": {k: {"n": v[0], "mean_claimed_confidence": round(v[1] / v[0], 6), "share_true": round(v[2] / v[0], 6)}
                      for k, v in sorted(by_intent.items())},
    }


def render_metacognition(report: dict[str, Any], comm: dict[str, Any]) -> str:
    s = report["summary"]

    def f(v):
        return "—" if v is None else f"{v:+.3f}"

    lines = [
        f"Criterio 4 · sensibilidad metacognitiva (precisión con confianza alta − baja): propia {f(s['mean_own_sensitivity'])} "
        f"vs observador externo {f(s['mean_external_sensitivity'])} · agentes con sensibilidad > 0: "
        f"{s['agents_with_positive_sensitivity']}/{s['agents']}",
        f"   agrupado · propia {f(s['pooled_own']['sensitivity'])} (r conf–precisión {f(s['pooled_own']['calibration_r'])}) · "
        f"externa {f(s['pooled_external']['sensitivity'])} (r {f(s['pooled_external']['calibration_r'])}) · n = {s['pooled_own']['n']}",
        f"Criterio 5 · confianza declarada al informar vs verdad: r = {f(comm['calibration_r'])} (n = {comm['n']})",
    ]
    for intent, v in comm["by_intent"].items():
        lines.append(f"   {intent:<8} n={v['n']:<5} confianza declarada media {v['mean_claimed_confidence']:.2f} · verdaderas {v['share_true']:.2f}")
    return "\n".join(lines)
