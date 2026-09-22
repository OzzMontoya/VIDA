"""Análisis a nivel de sociedad (VIDA-2.0) y criterio 3 de ``docs/criterios_consciencia.md``.

Criterio 3: que el agente reporte estados internos que correlacionen con
variables que **no** le fueron dadas. En VIDA cada agente conoce su propio
estado emocional simulado (valencia), pero no la confianza que los demás le
tienen: sólo vive sus consecuencias (aceptaciones, rechazos). Se mide la
correlación, entre agentes, de la valencia emocional con la confianza media
entrante (oculta). Una correlación alta no prueba vivencia; muestra que el
estado reportado rastrea una variable social que el agente no puede leer.

También: estructura de reputación (¿la reputación pública predice la
aceptación social?), desigualdad económica y dinámica de precios.
"""

from __future__ import annotations

import math
from typing import Any

from vida.agents.agent import AgentState
from vida.simulation.events import EventRecord


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy), 6)


def incoming_trust(agents: dict[str, AgentState], agent_id: str) -> float | None:
    values = [a.relationships[agent_id].trust for a in agents.values()
              if a.id != agent_id and a.alive and agent_id in a.relationships and a.relationships[agent_id].familiarity > 0.1]
    return round(sum(values) / len(values), 6) if values else None


def gini(values: list[float]) -> float:
    xs = sorted(max(0.0, v) for v in values)
    n = len(xs)
    total = sum(xs)
    if n == 0 or total == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * total) - (n + 1) / n, 6)


def society_report(agents: dict[str, AgentState], events: list[EventRecord]) -> dict[str, Any]:
    alive = {aid: a for aid, a in agents.items() if a.alive}
    rows = []
    for aid, a in sorted(alive.items()):
        soc = [e for e in events if e.event_type == "action" and e.agent_id == aid and e.outcome and e.outcome.action == "socialize"]
        rows.append({
            "agent_id": aid, "emotion_valence": round(a.emotion.valence, 6), "incoming_trust": incoming_trust(agents, aid),
            "reputation": round(a.reputation, 6), "money": round(a.money, 6), "generation": a.generation,
            "acceptance_rate": round(sum(1 for e in soc if e.outcome.success) / len(soc), 6) if soc else None,
            "social_need": round(a.needs["social"].level, 6),
        })
    with_trust = [r for r in rows if r["incoming_trust"] is not None]
    with_acc = [r for r in rows if r["acceptance_rate"] is not None]
    prices = [e.perception.prices for e in events if e.event_type == "action" and e.perception and e.perception.prices]
    bread = [p["bread"] for p in prices if "bread" in p]
    summary = {
        "alive": len(alive),
        # Criterio 3: estado reportado (valencia) vs variable oculta (confianza entrante).
        "corr_emotion_vs_incoming_trust": pearson([r["emotion_valence"] for r in with_trust], [r["incoming_trust"] for r in with_trust]),
        # Control: el mismo estado frente a una variable que el agente SÍ conoce (su necesidad social).
        "corr_emotion_vs_social_need": pearson([r["emotion_valence"] for r in rows], [r["social_need"] for r in rows]),
        # Estructura social y económica.
        "corr_reputation_vs_acceptance": pearson([r["reputation"] for r in with_acc], [r["acceptance_rate"] for r in with_acc]),
        "corr_incoming_trust_vs_reputation": pearson([r["incoming_trust"] for r in with_trust], [r["reputation"] for r in with_trust]),
        "money_gini": gini([r["money"] for r in rows]),
        "money_mean": round(sum(r["money"] for r in rows) / len(rows), 6) if rows else None,
        "bread_price_min": round(min(bread), 4) if bread else None,
        "bread_price_max": round(max(bread), 4) if bread else None,
        "bread_price_mean": round(sum(bread) / len(bread), 4) if bread else None,
        "generations": max((a.generation for a in agents.values()), default=0),
    }
    return {"rows": rows, "summary": summary}


def render_society(report: dict[str, Any]) -> str:
    s = report["summary"]

    def fmt(v: float | None) -> str:
        return "—" if v is None else f"{v:+.3f}"

    return "\n".join([
        f"Vivos: {s['alive']} · generaciones: {s['generations']} · dinero medio {s['money_mean']} · Gini {s['money_gini']}",
        f"Criterio 3 · valencia emocional vs confianza entrante (oculta para el agente): r = {fmt(s['corr_emotion_vs_incoming_trust'])}",
        f"Control · valencia emocional vs necesidad social (conocida por el agente):      r = {fmt(s['corr_emotion_vs_social_need'])}",
        f"Reputación pública vs tasa de aceptación social: r = {fmt(s['corr_reputation_vs_acceptance'])}",
        f"Confianza entrante vs reputación pública:        r = {fmt(s['corr_incoming_trust_vs_reputation'])}",
        f"Precio del pan visto por los agentes: mín {s['bread_price_min']} · medio {s['bread_price_mean']} · máx {s['bread_price_max']}",
    ])
