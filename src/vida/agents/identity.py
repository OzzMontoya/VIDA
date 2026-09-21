"""Identidad como representación dinámica (sección 15).

La identidad no es un objeto almacenado sino una síntesis periódica de hábitos
(contadores de acciones), valores (que derivan con la conducta) y preferencias
fuertes. Las etiquetas describen conducta observada, no estados internos.
"""

from __future__ import annotations

from vida.agents.agent import AgentState


def _ratio(agent: AgentState, key: str, total: int) -> float:
    return agent.counters.get(key, 0) / total if total else 0.0


def refresh(agent: AgentState) -> list[str]:
    """Recalcula etiquetas de autodescripción y ajusta valores; devuelve las etiquetas."""
    total = sum(v for k, v in agent.counters.items() if k.startswith("action:") and k != "action:idle")
    tags: list[str] = []
    if total >= 10:
        if _ratio(agent, "action:work", total) >= 0.25:
            tags.append("trabajador")
        if _ratio(agent, "action:socialize", total) >= 0.20:
            tags.append("sociable")
        if _ratio(agent, "action:study", total) >= 0.15:
            tags.append("estudioso")
        if _ratio(agent, "action:rest", total) >= 0.35:
            tags.append("hogareño")
        if _ratio(agent, "action:move", total) >= 0.40:
            tags.append("andariego")

    replies = agent.counters.get("reply:truth", 0) + agent.counters.get("reply:lie", 0) + agent.counters.get("reply:partial", 0)
    lies = agent.counters.get("reply:lie", 0) + agent.counters.get("share:lie", 0)
    if replies + agent.counters.get("share:truth", 0) >= 3:
        if lies == 0:
            tags.append("honesto")
        elif lies / (replies + agent.counters.get("share:truth", 0) + agent.counters.get("share:lie", 0)) >= 0.3:
            tags.append("engañoso")

    close = [oid for oid, rel in sorted(agent.relationships.items()) if rel.familiarity >= 0.3 and rel.affection >= 0.6]
    if close:
        tags.append(f"cercano_a:{','.join(close[:3])}")

    strong = sorted(
        (p for p in agent.preferences.values() if p.strength >= 0.3 and abs(p.valence) >= 0.3),
        key=lambda p: (-abs(p.valence) * p.strength, p.subject),
    )
    if strong:
        best = strong[0]
        tags.append(("prefiere:" if best.valence > 0 else "evita:") + best.subject)

    # Valores: derivan con la conducta, lentamente.
    values = agent.identity.core_values
    if replies:
        honesty_signal = 1.0 - lies / max(1, replies + agent.counters.get("share:truth", 0) + agent.counters.get("share:lie", 0))
        values["honesty"] = round(values["honesty"] + 0.1 * (honesty_signal - values["honesty"]), 6)
    if total >= 10:
        values["ambition"] = round(values["ambition"] + 0.1 * (min(1.0, _ratio(agent, "action:work", total) * 2.5) - values["ambition"]), 6)
        repeat = max((rel.familiarity for rel in agent.relationships.values()), default=0.0)
        values["loyalty"] = round(values["loyalty"] + 0.1 * (repeat - values["loyalty"]), 6)

    agent.identity.self_description_tags = tags
    return tags
