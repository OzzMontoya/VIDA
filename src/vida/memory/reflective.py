"""Memoria reflexiva (sección 14, fase posterior): conclusiones derivadas de varias experiencias.

Al cierre de cada día el agente agrupa sus episodios recientes por acción y
objetivo (lugar, recurso o persona) y, cuando hay evidencia suficiente,
escribe o actualiza una conclusión del tipo "comprar en market salió bien 2 de
5 veces". Estas conclusiones tienen alta importancia, no se olvidan con los
episodios que las originaron y pesan en la expectativa del motor de decisión.
Así, lo vivido cambia lo que el agente hace aunque los episodios concretos se
hayan olvidado.
"""

from __future__ import annotations

from collections import defaultdict

from vida.agents.agent import AgentState
from vida.memory.base import AgentMemory, MemoryRecord

MIN_EVIDENCE = 3
WINDOW_DAYS = 3
TARGET_PREFIXES = ("loc:", "res:", "agent:")

ACTION_LABELS = {
    "acquire": "comprar", "work": "trabajar", "socialize": "conversar", "ask_info": "pedir información",
    "share_info": "compartir información", "study": "estudiar", "seek_care": "buscar atención", "rest": "descansar",
    "move": "ir", "consume": "comer",
}


def _key_tags(record: MemoryRecord) -> tuple[str, tuple[str, ...]] | None:
    """Clave de agrupación: la acción y todas sus etiquetas de objetivo (lugar, recurso, persona)."""
    action = next((t for t in record.tags if t.startswith("action:")), None)
    if action is None:
        return None
    targets = tuple(sorted(t for t in record.tags if t.startswith(TARGET_PREFIXES) and not t.startswith("loc:home")))
    return (action, targets)


def reflect(memory: AgentMemory, agent: AgentState, tick: int, ticks_per_day: int) -> list[MemoryRecord]:
    """Genera o actualiza conclusiones reflexivas a partir de los episodios de los últimos días."""
    horizon = tick - WINDOW_DAYS * ticks_per_day
    groups: dict[tuple[str, str], list[MemoryRecord]] = defaultdict(list)
    for record in memory.by_kind("episodic"):
        if record.tick < horizon:
            continue
        key = _key_tags(record)
        if key is not None:
            groups[key].append(record)

    written: list[MemoryRecord] = []
    for (action_tag, target_tags), records in sorted(groups.items()):
        if len(records) < MIN_EVIDENCE:
            continue
        successes = sum(1 for r in records if "outcome:ok" in r.tags)
        mean_valence = round(sum(r.valence for r in records) / len(records), 6)
        action = action_tag.split(":", 1)[1]
        label = ACTION_LABELS.get(action, action)
        target = ", ".join(t.split(":", 1)[1] for t in target_tags)
        where = f" ({target})" if target else ""
        verdict = "salió bien" if successes >= len(records) / 2 else "salió mal"
        content = f"Últimos días: {label}{where} {verdict} {successes} de {len(records)} veces"
        tags = {"reflection", action_tag} | set(target_tags)
        existing = memory.find(tags, kind="reflective")
        if existing:
            rec = existing[0]
            rec.content, rec.valence, rec.tick = content, mean_valence, tick
            rec.confirmations = len(records)
            rec.importance = min(1.0, round(0.6 + 0.05 * len(records), 6))
        else:
            rec = memory.add("reflective", tick, content, importance=min(1.0, 0.6 + 0.05 * len(records)),
                             valence=mean_valence, tags=tags)
            rec.confirmations = len(records)
        written.append(rec)
    return written
