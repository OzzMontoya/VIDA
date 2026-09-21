"""Biografía de un agente reconstruida desde la base de datos de una corrida.

Responde las siete preguntas del criterio de éxito de VIDA-0.1 (sección 33):
qué vivió, qué recuerda, qué aprendió, qué prefiere, a quién conoce, qué
decisiones tomó y qué experiencias modificaron su comportamiento. Todo se
deriva de hechos registrados; el texto describe conducta, no estados internos.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from vida.agents.agent import AgentState
from vida.database.repository import RunRepository
from vida.memory.base import MemoryRecord
from vida.simulation.events import EventRecord


class Biography(BaseModel):
    run_id: str
    agent_id: str
    name: str
    ticks_per_day: int
    initial_age_days: int
    final_age_days: int
    stages: list[tuple[int, str]] = Field(default_factory=list)  # (día, etapa)
    death: tuple[int, str] | None = None
    identity_tags: list[str] = Field(default_factory=list)
    core_values: dict[str, float] = Field(default_factory=dict)
    reputation: float = 0.5
    lived_days: list[str] = Field(default_factory=list)
    notable_events: list[str] = Field(default_factory=list)
    remembers: list[str] = Field(default_factory=list)
    forgotten_count: int = 0
    learned_skills: dict[str, tuple[float, float]] = Field(default_factory=dict)
    learned_facts: list[str] = Field(default_factory=list)
    prefers: list[tuple[str, float]] = Field(default_factory=list)
    avoids: list[tuple[str, float]] = Field(default_factory=list)
    knows: list[dict[str, Any]] = Field(default_factory=list)
    decisions: dict[str, int] = Field(default_factory=dict)
    honesty_record: dict[str, int] = Field(default_factory=dict)
    turning_points: list[str] = Field(default_factory=list)


def _label(subject: str) -> str:
    kind, _, value = subject.partition(":")
    return {"action": "hacer", "loc": "lugar", "res": "recurso", "agent": "persona"}.get(kind, kind) + " " + value


def build_biography(repo: RunRepository, run_id: str, agent_id: str, names: dict[str, str] | None = None) -> Biography:
    meta = repo.run_meta(run_id)
    if meta is None:
        raise KeyError(f"Corrida no encontrada: {run_id}")
    agents_meta = repo.agents_meta(run_id)
    if agent_id not in agents_meta:
        raise KeyError(f"Agente {agent_id} no existe en la corrida {run_id}")
    names = names or {aid: m["name"] for aid, m in agents_meta.items()}
    cfg = json.loads(meta["config_json"])
    tpd = int(cfg["run"]["ticks_per_day"])

    history = repo.state_history(run_id, agent_id)
    if not history:
        raise RuntimeError("La corrida no tiene snapshots de estado")
    first: AgentState = history[0][1]
    final: AgentState = history[-1][1]
    events = repo.events_for_agent(run_id, agent_id)
    memories = repo.memories_for(run_id, agent_id)

    bio = Biography(
        run_id=run_id, agent_id=agent_id, name=final.name, ticks_per_day=tpd,
        initial_age_days=first.age_days(tpd), final_age_days=final.age_days(tpd),
        identity_tags=list(final.identity.self_description_tags),
        core_values={k: round(v, 3) for k, v in sorted(final.identity.core_values.items())},
        reputation=round(final.reputation, 3), forgotten_count=repo.forgotten_count(run_id, agent_id),
    )
    bio.stages = [(0, first.life_stage)] + [(e.day, e.note) for e in events if e.event_type == "stage_change"]
    death = agents_meta[agent_id].get("death_tick")
    if death is not None:
        bio.death = (death // tpd, agents_meta[agent_id]["death_reason"] or "")

    _fill_lived(bio, events, memories)
    _fill_memory(bio, memories)
    _fill_learning(bio, first, final, memories)
    _fill_preferences(bio, final)
    _fill_relationships(bio, final, names)
    _fill_decisions(bio, events, final)
    _fill_turning_points(bio, events, memories, names)
    return bio


def _fill_lived(bio: Biography, events: list[EventRecord], memories: list[MemoryRecord]) -> None:
    bio.lived_days = [m.content for m in sorted(memories, key=lambda m: m.tick) if m.kind == "autobiographical"]
    episodic = {m.id: m for m in memories if m.kind == "episodic"}
    notable = sorted(
        (e for e in events if e.event_type == "action" and e.outcome is not None and e.outcome.action != "idle"),
        key=lambda e: (-max((episodic[m].importance for m in e.memories_created if m in episodic), default=0.0), e.seq),
    )[:8]
    for e in sorted(notable, key=lambda e: e.seq):
        text = next((episodic[m].content for m in e.memories_created if m in episodic), e.outcome.key())
        bio.notable_events.append(f"día {e.day}, hora {e.hour:02d}: {text}")


def _fill_memory(bio: Biography, memories: list[MemoryRecord]) -> None:
    ranked = sorted((m for m in memories if m.kind != "autobiographical"),
                    key=lambda m: (-m.importance, -m.access_count, m.id))[:10]
    bio.remembers = [f"[{m.kind}] {m.content} (importancia {m.importance:.2f})" for m in ranked]


def _fill_learning(bio: Biography, first: AgentState, final: AgentState, memories: list[MemoryRecord]) -> None:
    for skill in sorted(set(first.knowledge) | set(final.knowledge)):
        bio.learned_skills[skill] = (round(first.knowledge_level(skill), 3), round(final.knowledge_level(skill), 3))
    bio.learned_facts = [m.content for m in sorted(memories, key=lambda m: (-m.importance, m.id)) if m.kind == "semantic"][:6]


def _fill_preferences(bio: Biography, final: AgentState) -> None:
    prefs = sorted(final.preferences.values(), key=lambda p: (-p.valence * p.strength, p.subject))
    bio.prefers = [(_label(p.subject), round(p.valence, 3)) for p in prefs if p.valence > 0.05 and p.strength >= 0.1][:5]
    bio.avoids = [(_label(p.subject), round(p.valence, 3)) for p in reversed(prefs) if p.valence < -0.05 and p.strength >= 0.1][:3]


def _fill_relationships(bio: Biography, final: AgentState, names: dict[str, str]) -> None:
    for other_id, rel in sorted(final.relationships.items(), key=lambda kv: (-kv[1].familiarity, kv[0])):
        if rel.familiarity <= 0.0 and rel.trust == 0.5 and rel.affection == 0.5:
            continue
        model = final.beliefs.others.get(other_id)
        bio.knows.append({
            "agent_id": other_id, "name": names.get(other_id, other_id),
            "familiarity": round(rel.familiarity, 3), "trust": round(rel.trust, 3), "affection": round(rel.affection, 3),
            "honesty_estimate": round(model.honesty_estimate, 3) if model else None,
        })


def _fill_decisions(bio: Biography, events: list[EventRecord], final: AgentState) -> None:
    counts = Counter(e.proposal.kind for e in events if e.event_type == "action" and e.proposal is not None)
    bio.decisions = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    bio.honesty_record = {k: v for k, v in sorted(final.counters.items()) if k.startswith(("reply:", "share:"))}


def _fill_turning_points(bio: Biography, events: list[EventRecord], memories: list[MemoryRecord], names: dict[str, str]) -> None:
    episodic = {m.id: m for m in memories if m.kind == "episodic"}

    def magnitude(e: EventRecord) -> float:
        rel = sum(abs(v) for pair, d in e.relationship_deltas.items() if pair.startswith(e.agent_id) for v in d.values())
        return rel + sum(abs(v) for v in e.preference_deltas.values()) + 0.3 * len(e.belief_changes)

    ranked = sorted((e for e in events if e.event_type == "action"), key=lambda e: (-magnitude(e), e.seq))[:6]
    for e in sorted(ranked, key=lambda e: e.seq):
        if magnitude(e) <= 0.05:
            continue
        text = next((episodic[m].content for m in e.memories_created if m in episodic), e.outcome.key() if e.outcome else "")
        effects = []
        for pair, d in sorted(e.relationship_deltas.items()):
            if pair.startswith(e.agent_id) and "trust" in d:
                other = pair.split("->")[1]
                effects.append(f"confianza en {names.get(other, other)} {d['trust']:+.2f}")
        for subject, delta in sorted(e.preference_deltas.items(), key=lambda kv: -abs(kv[1]))[:2]:
            effects.append(f"preferencia por {_label(subject)} {delta:+.2f}")
        bio.turning_points.append(f"día {e.day}: {text} → " + "; ".join(effects))


def render(bio: Biography) -> str:
    L: list[str] = []
    L.append(f"=== {bio.name} ({bio.agent_id}) — corrida {bio.run_id} ===")
    stages = " → ".join(f"{s} (día {d})" for d, s in bio.stages)
    L.append(f"Edad: {bio.initial_age_days} → {bio.final_age_days} días. Etapas: {stages}.")
    if bio.death:
        L.append(f"Murió el día {bio.death[0]} ({bio.death[1]}).")
    L.append(f"Identidad observada: {', '.join(bio.identity_tags) or 'sin rasgos destacados aún'}. "
             f"Valores: {bio.core_values}. Reputación: {bio.reputation}.")

    L.append("\n1) QUÉ VIVIÓ")
    L.extend(f"  - {d}" for d in bio.lived_days)
    if not bio.lived_days:
        L.append("  (sin días completos)")
    if bio.notable_events:
        L.append("  Momentos notables:")
        L.extend(f"    · {t}" for t in bio.notable_events)

    L.append(f"\n2) QUÉ RECUERDA (memorias más importantes; olvidó {bio.forgotten_count})")
    L.extend(f"  - {m}" for m in bio.remembers)
    if not bio.remembers:
        L.append("  (nada)")

    L.append("\n3) QUÉ APRENDIÓ")
    for skill, (a, b) in sorted(bio.learned_skills.items()):
        L.append(f"  - {skill}: {a:.2f} → {b:.2f}")
    L.extend(f"  - {f}" for f in bio.learned_facts)

    L.append("\n4) QUÉ PREFIERE")
    L.extend(f"  + {s} ({v:+.2f})" for s, v in bio.prefers)
    if not bio.prefers:
        L.append("  (sin preferencias marcadas)")
    L.extend(f"  - evita {s} ({v:+.2f})" for s, v in bio.avoids)

    L.append("\n5) A QUIÉN CONOCE")
    for k in bio.knows:
        honesty = f", honestidad estimada {k['honesty_estimate']}" if k["honesty_estimate"] is not None else ""
        L.append(f"  - {k['name']} ({k['agent_id']}): familiaridad {k['familiarity']}, confianza {k['trust']}, afecto {k['affection']}{honesty}")
    if not bio.knows:
        L.append("  (a nadie todavía)")

    L.append("\n6) QUÉ DECISIONES TOMÓ")
    L.append("  " + ", ".join(f"{k}×{v}" for k, v in bio.decisions.items()))
    if bio.honesty_record:
        L.append(f"  Respuestas e información compartida: {bio.honesty_record}")

    L.append("\n7) QUÉ EXPERIENCIAS LO MODIFICARON")
    L.extend(f"  - {t}" for t in bio.turning_points)
    if not bio.turning_points:
        L.append("  (ninguna con efecto medible)")
    return "\n".join(L)
