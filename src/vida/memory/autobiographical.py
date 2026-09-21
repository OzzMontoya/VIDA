"""Memoria autobiográfica: un resumen por día simulado, generado por plantilla.

Es la base de la "historia personal" del agente (sección 15) y del criterio de
éxito de VIDA-0.1: reconstruir qué vivió cada agente.
"""

from __future__ import annotations

from collections import Counter

from vida.agents.agent import AgentState
from vida.memory.base import AgentMemory, MemoryRecord
from vida.world.actions import ActionOutcome

ACTION_LABELS = {
    "work": "trabajé", "study": "estudié", "rest": "descansé", "socialize": "conversé",
    "acquire": "compré", "consume": "comí", "move": "me desplacé", "ask_info": "pregunté",
    "share_info": "compartí información", "seek_care": "fui al hospital", "idle": "no hice nada",
}


def daily_summary(
    memory: AgentMemory, agent: AgentState, day: int, tick: int, outcomes: list[ActionOutcome],
    names: dict[str, str],
) -> MemoryRecord | None:
    if not outcomes:
        return None
    counts = Counter(o.action for o in outcomes if o.success)
    failures = [o for o in outcomes if not o.success and o.kind != "illegal"]
    partners = sorted({names.get(o.target_agent, o.target_agent) for o in outcomes
                       if o.target_agent and o.success and o.action == "socialize"})
    parts = [f"{ACTION_LABELS.get(a, a)} {n} veces" if n > 1 else ACTION_LABELS.get(a, a)
             for a, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
    text = f"Día {day}: " + ", ".join(parts) if parts else f"Día {day}: un día sin logros"
    if partners:
        text += f"; hablé con {', '.join(partners)}"
    if failures:
        worst = min(failures, key=lambda o: (o.valence, o.tick))
        text += f"; lo peor: {worst.action} terminó en {worst.kind}"
    valence = round(sum(o.valence for o in outcomes) / len(outcomes), 6)
    tags = {"autobio:day", f"day:{day}"} | {f"action:{a}" for a in counts}
    tags |= {f"agent:{o.target_agent}" for o in outcomes if o.target_agent}
    return memory.add("autobiographical", tick, text, importance=0.7, valence=valence, tags=tags)
