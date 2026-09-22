"""Análisis de linaje y transmisión cultural (sección 18).

Para cada agente nacido en la corrida compara, con el ICI, su estado final con
el de su progenitor y con el de los demás adultos de la generación anterior.
Si la semejanza con el progenitor supera sistemáticamente la semejanza con los
otros, hubo transmisión (personalidad heredada, creencias contadas, vínculo);
si no, la vida propia borró la herencia.
"""

from __future__ import annotations

from typing import Any

from vida.agents.agent import AgentState
from vida.evaluation.metrics import continuity_index
from vida.memory.base import AgentMemory
from vida.simulation.events import EventRecord


def lineage_report(agents: dict[str, AgentState], memories: dict[str, AgentMemory], events: list[EventRecord]) -> dict[str, Any]:
    children = [a for a in agents.values() if a.parent_id]
    rows: list[dict[str, Any]] = []
    for child in sorted(children, key=lambda a: a.id):
        parent = agents.get(child.parent_id or "")
        if parent is None:
            continue
        with_parent = continuity_index(parent, memories[parent.id], events, child, memories[child.id], events)
        others = [a for a in agents.values() if a.generation == parent.generation and a.id != parent.id]
        sims = [continuity_index(o, memories[o.id], events, child, memories[child.id], events) for o in others]
        mean_other = {k: round(sum(s[k] for s in sims) / len(sims), 6) for k in with_parent} if sims else {}
        inherited_beliefs = sum(1 for r in child.beliefs.resources.values() for b in r.values() if b.source_agent == parent.id)
        rows.append({
            "child": child.id, "parent": parent.id, "generation": child.generation, "alive": child.alive,
            "ici_parent": with_parent["ici"], "ici_others": mean_other.get("ici"),
            "personality_parent": with_parent["personality"], "personality_others": mean_other.get("personality"),
            "preferences_parent": with_parent["preferences"], "preferences_others": mean_other.get("preferences"),
            "decisions_parent": with_parent["decisions"], "decisions_others": mean_other.get("decisions"),
            "beliefs_from_parent_remaining": inherited_beliefs,
            "trust_in_parent": round(child.relationship_with(parent.id).trust, 3),
        })
    n = len(rows)
    summary = {
        "children": n,
        "generations": max((a.generation for a in agents.values()), default=0),
        "closer_to_parent_than_others": sum(1 for r in rows if r["ici_others"] is not None and r["ici_parent"] > r["ici_others"]),
        "mean_ici_parent": round(sum(r["ici_parent"] for r in rows) / n, 6) if n else None,
        "mean_ici_others": round(sum(r["ici_others"] for r in rows if r["ici_others"] is not None) / n, 6) if n and all(r["ici_others"] is not None for r in rows) else None,
    }
    return {"rows": rows, "summary": summary}


def render_lineage(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [f"Hijos: {s['children']} · generaciones: {s['generations']} · más parecidos a su progenitor que a los demás: "
             f"{s['closer_to_parent_than_others']}/{s['children']} · ICI medio con progenitor {s['mean_ici_parent']} vs otros {s['mean_ici_others']}",
             f"{'hijo':<6}{'padre':<6}{'gen':>4}{'ICI padre':>11}{'ICI otros':>11}{'person. p/o':>14}{'prefs p/o':>12}{'decis. p/o':>12}{'creencias':>10}{'confianza':>10}"]
    for r in report["rows"]:
        o = r["ici_others"] if r["ici_others"] is not None else float("nan")
        lines.append(f"{r['child']:<6}{r['parent']:<6}{r['generation']:>4}{r['ici_parent']:>11.3f}{o:>11.3f}"
                     f"{r['personality_parent']:>7.2f}/{(r['personality_others'] or 0):<6.2f}{r['preferences_parent']:>6.2f}/{(r['preferences_others'] or 0):<5.2f}"
                     f"{r['decisions_parent']:>6.2f}/{(r['decisions_others'] or 0):<5.2f}{r['beliefs_from_parent_remaining']:>10}{r['trust_in_parent']:>10.2f}")
    return "\n".join(lines)
