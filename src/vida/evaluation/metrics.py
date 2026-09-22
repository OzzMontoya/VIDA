"""Métricas científicas (sección 30) e Índice de Continuidad Individual (sección 23).

Todas las métricas se calculan sobre objetos en memoria (eventos, estado del
agente, almacén de memoria) para poder usarse dentro de experimentos sin pasar
por la base de datos. Cada valor está en una escala documentada; ninguna
métrica pretende medir conciencia: el ICI es una **semejanza entre estados**.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from vida.agents.agent import AgentState
from vida.memory.base import AgentMemory
from vida.simulation.events import EventRecord

ACTION_KINDS = ["move", "acquire", "consume", "work", "rest", "socialize", "ask_info", "share_info", "study", "seek_care", "idle"]


# --- utilidades ---------------------------------------------------------------

def _distribution(counter: Counter, keys: list[str]) -> list[float]:
    total = sum(counter.get(k, 0) for k in keys)
    return [counter.get(k, 0) / total if total else 0.0 for k in keys]


def js_similarity(p: list[float], q: list[float]) -> float:
    """1 - divergencia de Jensen-Shannon (base 2), en [0, 1]; 1 = distribuciones idénticas."""
    if not any(p) or not any(q):
        return 1.0 if p == q else 0.0
    m = [(a + b) / 2 for a, b in zip(p, q)]

    def kl(x: list[float], y: list[float]) -> float:
        return sum(xi * math.log2(xi / yi) for xi, yi in zip(x, y) if xi > 0 and yi > 0)

    return round(1.0 - (kl(p, m) + kl(q, m)) / 2, 6)


def jaccard(a: set[Any], b: set[Any]) -> float:
    if not a and not b:
        return 1.0
    return round(len(a & b) / len(a | b), 6)


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 1.0 if na == nb else 0.0
    return round(max(0.0, dot / (na * nb)), 6)


def entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return round(-sum((c / total) * math.log2(c / total) for c in counter.values() if c), 6)


# --- métricas por agente -------------------------------------------------------

def agent_metrics(agent: AgentState, memory: AgentMemory, events: list[EventRecord], initial: AgentState | None,
                  ticks_per_day: int) -> dict[str, float]:
    """Métricas de memoria, identidad, social, aprendizaje, decisiones y supervivencia de un agente."""
    actions = [e for e in events if e.event_type == "action" and e.agent_id == agent.id and e.outcome is not None]
    m: dict[str, float] = {}

    # Memoria
    records = memory.all()
    m["memory_retained"] = len(records)
    m["memory_forgotten"] = len(memory.forgotten)
    m["memory_retention"] = round(len(records) / (len(records) + len(memory.forgotten)), 6) if records or memory.forgotten else 0.0
    m["memory_semantic_facts"] = sum(1 for r in records if r.kind == "semantic")
    m["memory_mean_importance"] = round(sum(r.importance for r in records) / len(records), 6) if records else 0.0
    m["memory_recall_rate"] = round(sum(1 for r in records if r.access_count > 0) / len(records), 6) if records else 0.0
    m["memory_reflections"] = sum(1 for r in records if r.kind == "reflective")

    # Automodelo predictivo (criterio 1 de docs/criterios_consciencia.md)
    m["self_model_calibration"] = agent.self_model.calibration()
    m["self_model_advantage"] = agent.self_model.advantage()
    m["self_model_n"] = agent.self_model.n

    # Identidad y consistencia conductual
    half = len(actions) // 2
    first = Counter(e.outcome.action for e in actions[:half])
    second = Counter(e.outcome.action for e in actions[half:])
    m["behavioural_consistency"] = js_similarity(_distribution(first, ACTION_KINDS), _distribution(second, ACTION_KINDS))
    third = max(1, len(actions) // 3)
    early = sum(sum(abs(v) for v in e.preference_deltas.values()) for e in actions[:third])
    late = sum(sum(abs(v) for v in e.preference_deltas.values()) for e in actions[-third:])
    m["preference_volatility_early"] = round(early / third, 6)
    m["preference_volatility_late"] = round(late / third, 6)
    m["preference_stability"] = round(1.0 - min(1.0, late / third), 6)
    m["identity_tags"] = len(agent.identity.self_description_tags)

    # Social
    soc = [e for e in actions if e.outcome.action == "socialize"]
    m["social_attempts"] = len(soc)
    m["social_acceptance_rate"] = round(sum(1 for e in soc if e.outcome.success) / len(soc), 6) if soc else 0.0
    rels = [r for r in agent.relationships.values() if r.familiarity > 0.1]
    m["known_agents"] = len(rels)
    m["mean_trust"] = round(sum(r.trust for r in rels) / len(rels), 6) if rels else 0.5
    m["mean_familiarity"] = round(sum(r.familiarity for r in rels) / len(rels), 6) if rels else 0.0
    lies = agent.counters.get("reply:lie", 0) + agent.counters.get("share:lie", 0)
    honest = agent.counters.get("reply:truth", 0) + agent.counters.get("reply:partial", 0) + agent.counters.get("share:truth", 0)
    m["deception_rate"] = round(lies / (lies + honest), 6) if lies + honest else 0.0
    m["info_exchanges"] = sum(1 for e in actions if e.outcome.action in {"ask_info", "share_info"})
    m["reputation"] = round(agent.reputation, 6)

    # Aprendizaje
    for skill in sorted(agent.knowledge):
        base = initial.knowledge_level(skill) if initial else 0.0
        m[f"skill_gain_{skill}"] = round(agent.knowledge_level(skill) - base, 6)
    m["belief_corrections"] = sum(1 for e in actions for c in e.belief_changes if c.startswith("refute"))
    m["failed_acquires"] = sum(1 for e in actions if e.outcome.action == "acquire" and e.outcome.kind == "resource_absent")

    # Decisiones
    kinds = Counter(e.outcome.action for e in actions)
    m["decision_entropy"] = entropy(kinds)
    m["distinct_choices"] = len({e.decision.chosen for e in actions if e.decision})
    m["success_rate"] = round(sum(1 for e in actions if e.outcome.success) / len(actions), 6) if actions else 0.0
    m["llm_fallback_rate"] = round(sum(1 for e in actions if e.decision and "/fallback" in e.decision.engine) / len(actions), 6) if actions else 0.0

    # Supervivencia y bienestar
    m["alive"] = 1.0 if agent.alive else 0.0
    m["age_days"] = agent.age_days(ticks_per_day)
    m["money"] = round(agent.money, 6)
    m["mean_need_level"] = round(sum(n.level for n in agent.needs.values()) / len(agent.needs), 6)
    return m


# --- Índice de Continuidad Individual -----------------------------------------

def _relationship_vector(agent: AgentState) -> dict[str, float]:
    vec: dict[str, float] = {}
    for other, rel in agent.relationships.items():
        vec[f"{other}:trust"] = rel.trust
        vec[f"{other}:affection"] = rel.affection
        vec[f"{other}:familiarity"] = rel.familiarity
    return vec


def _action_distribution(events: list[EventRecord], agent_id: str) -> list[float]:
    counter = Counter(e.outcome.action for e in events if e.event_type == "action" and e.agent_id == agent_id and e.outcome)
    return _distribution(counter, ACTION_KINDS)


def _choice_similarity(ev_a: list[EventRecord], id_a: str, ev_b: list[EventRecord], id_b: str) -> float:
    """Semejanza de las elecciones concretas (clave de decisión: acción + objetivo), no sólo del tipo de acción.

    El tipo de acción lo impone en gran parte el mundo (horarios, necesidades);
    la individualidad se ve en con quién se conversa, a dónde se va y qué se compra.
    """
    ca = Counter(e.decision.chosen for e in ev_a if e.event_type == "action" and e.agent_id == id_a and e.decision)
    cb = Counter(e.decision.chosen for e in ev_b if e.event_type == "action" and e.agent_id == id_b and e.decision)
    keys = sorted(set(ca) | set(cb))
    if not keys:
        return 1.0
    return js_similarity(_distribution(ca, keys), _distribution(cb, keys))


def continuity_index(a: AgentState, mem_a: AgentMemory, ev_a: list[EventRecord],
                     b: AgentState, mem_b: AgentMemory, ev_b: list[EventRecord]) -> dict[str, float]:
    """ICI: semejanza por dimensión entre dos estados de agente, en [0, 1], y su media.

    No mide conciencia ni identidad metafísica: mide cuánto se parecen dos
    estados en memoria, preferencias, personalidad, conocimientos, relaciones,
    patrón de decisiones, historia autobiográfica y autorrepresentación.
    """
    dims: dict[str, float] = {}
    non_auto_a = {r.content for r in mem_a.all() if r.kind != "autobiographical"}
    non_auto_b = {r.content for r in mem_b.all() if r.kind != "autobiographical"}
    dims["memory"] = jaccard(non_auto_a, non_auto_b)
    dims["preferences"] = cosine({k: p.valence * p.strength for k, p in a.preferences.items()},
                                 {k: p.valence * p.strength for k, p in b.preferences.items()})
    pa, pb = a.personality.model_dump(), b.personality.model_dump()
    dims["personality"] = round(1.0 - sum(abs(pa[k] - pb[k]) for k in pa) / len(pa), 6)
    skills = set(a.knowledge) | set(b.knowledge)
    dims["knowledge"] = round(1.0 - sum(abs(a.knowledge_level(s) - b.knowledge_level(s)) for s in skills) / len(skills), 6) if skills else 1.0
    ra, rb = _relationship_vector(a), _relationship_vector(b)
    keys = set(ra) | set(rb)
    dims["relationships"] = round(1.0 - sum(abs(ra.get(k, 0.5 if not k.endswith("familiarity") else 0.0) -
                                                rb.get(k, 0.5 if not k.endswith("familiarity") else 0.0)) for k in keys) / len(keys), 6) if keys else 1.0
    dims["decisions"] = _choice_similarity(ev_a, a.id, ev_b, b.id)
    auto_a = {r.content for r in mem_a.all() if r.kind == "autobiographical"}
    auto_b = {r.content for r in mem_b.all() if r.kind == "autobiographical"}
    dims["autobiography"] = jaccard(auto_a, auto_b)
    tags = jaccard(set(a.identity.self_description_tags), set(b.identity.self_description_tags))
    values = set(a.identity.core_values) | set(b.identity.core_values)
    vdiff = sum(abs(a.identity.core_values.get(v, 0.5) - b.identity.core_values.get(v, 0.5)) for v in values) / len(values)
    dims["self_representation"] = round((tags + (1.0 - vdiff)) / 2, 6)
    dims["ici"] = round(sum(dims.values()) / len(dims), 6)
    return dims
