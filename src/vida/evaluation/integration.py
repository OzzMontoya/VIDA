"""Integración informacional de la mente de un agente (criterio 6, proxy de Φ).

Las teorías de integración de información asocian la consciencia a información
que el sistema genera *como un todo* y que ninguna partición en partes
independientes reproduce. Aquí se mide una versión conductual y observacional:

* Cada evento de acción registra el estado de seis componentes de la mente en
  el momento de decidir (``EventRecord.mind``): cuerpo (necesidades), memoria
  recuperada, automodelo, relaciones, identidad y creencias.
* Cada componente se discretiza en pocos niveles y se calcula la información
  mutua entre su estado y la acción elegida: ``I(acción; componente)``.
* La información del **todo** es ``I(acción; todos los componentes)``.
* Para cada bipartición de los componentes se calcula la información de las
  partes por separado ``I(acción; P1) + I(acción; P2)``. La partición de
  información mínima (MIP) es la que menos pierde; ``phi = I_todo − I_MIP``.
  Un valor positivo significa que la acción depende de conjunciones entre las
  partes que ninguna bipartición conserva; cero o negativo, que las partes
  se explican por separado (redundancia).
* ``synergy`` = ``I_todo − max_i I(acción; componente_i)``: cuánto añade
  el conjunto sobre el mejor componente aislado.

Las estimaciones de información mutua con muestras finitas están sesgadas al
alza; se corrige restando la media de ``n_shuffles`` permutaciones de la
acción (información espuria). Todo se calcula en bits.

Lectura obligada: un phi positivo muestra que la *conducta* del agente es
irreducible a sus módulos tomados por separado. No muestra vivencia. Y la
medida depende de las variables elegidas para resumir cada componente. Ninguna
variable registrada puede depender de la acción elegida: la predicción del
automodelo *para la acción escogida* daría información circular, por eso el
automodelo se resume por su error reciente y su experiencia acumulada.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from itertools import combinations
from typing import Any

from vida.simulation.events import EventRecord

COMPONENTS = ["body", "memory", "selfmodel", "relations", "identity", "beliefs"]

# Variables que resumen cada componente (se registran en ``EventRecord.mind``); la primera es la principal.
FEATURES: dict[str, list[str]] = {
    "body": ["hunger", "energy"],
    "memory": ["memory_valence", "memory_n"],
    "selfmodel": ["self_error", "self_n"],
    "relations": ["affection_here", "trust_here"],
    "identity": ["ambition", "honesty"],
    "beliefs": ["food_belief", "known_locations"],
}


def _entropy(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c > 0)


def mutual_information(xs: list[Any], ys: list[Any]) -> float:
    """I(X;Y) en bits, estimador de conteo (plug-in)."""
    if not xs:
        return 0.0
    return _entropy(Counter(xs)) + _entropy(Counter(ys)) - _entropy(Counter(zip(xs, ys)))


def _bins(values: list[float], k: int) -> list[int]:
    """Discretización por cuantiles en ``k`` niveles (los valores constantes caen en un solo nivel)."""
    ordered = sorted(values)
    cuts = [ordered[int(len(ordered) * i / k)] for i in range(1, k)]
    out = []
    for v in values:
        level = 0
        for c in cuts:
            if v >= c:
                level += 1
        out.append(level)
    return out


def _component_states(minds: list[dict[str, float]], component: str, k: int, n_features: int) -> list[tuple[int, ...]]:
    columns = []
    for feature in FEATURES[component][:n_features]:
        columns.append(_bins([m.get(feature, 0.0) for m in minds], k))
    return list(zip(*columns))


def _joint(states: list[list[tuple[int, ...]]]) -> list[tuple[Any, ...]]:
    return list(zip(*states))


def integration_from_samples(minds: list[dict[str, float]], actions: list[str], *, k: int = 2, n_features: int = 1,
                             n_shuffles: int = 20, seed: int = 0) -> dict[str, Any]:
    """Φ conductual para una muestra de decisiones (ver el módulo).

    Con ``k`` niveles y ``n_features`` variables por componente, el estado
    conjunto tiene ``k**(6·n_features)`` celdas: con una variable binaria por
    componente son 64, medibles con unos cientos de decisiones. Más variables
    exigen muchas más muestras (el estimador de conteo se sesga al alza y la
    corrección por permutación deja de bastar).
    """
    n = len(actions)
    if n < 20:
        return {"n": n, "phi_bits": None}
    rng = random.Random(seed)
    per_component = {c: _component_states(minds, c, k, n_features) for c in COMPONENTS}

    def corrected(states: list[Any]) -> float:
        raw = mutual_information(states, actions)
        shuffled = []
        for _ in range(n_shuffles):
            perm = actions[:]
            rng.shuffle(perm)
            shuffled.append(mutual_information(states, perm))
        return round(raw - sum(shuffled) / len(shuffled), 6)

    parts = {c: corrected(per_component[c]) for c in COMPONENTS}
    whole = corrected(_joint([per_component[c] for c in COMPONENTS]))
    best_partition, best_sum = None, None
    for r in range(1, len(COMPONENTS) // 2 + 1):
        for left in combinations(COMPONENTS, r):
            right = tuple(c for c in COMPONENTS if c not in left)
            if r == len(COMPONENTS) / 2 and left > right:
                continue  # cada bipartición una sola vez
            total = corrected(_joint([per_component[c] for c in left])) + corrected(_joint([per_component[c] for c in right]))
            if best_sum is None or total > best_sum:
                best_partition, best_sum = (list(left), list(right)), total
    action_entropy = round(_entropy(Counter(actions)), 6)
    return {
        "n": n,
        "action_entropy_bits": action_entropy,
        "information_whole_bits": whole,
        "information_parts_bits": parts,
        "sum_of_parts_bits": round(sum(parts.values()), 6),
        "mip": best_partition,
        "information_mip_bits": round(best_sum, 6) if best_sum is not None else None,
        "phi_bits": round(whole - best_sum, 6) if best_sum is not None else None,
        "phi_normalized": round((whole - best_sum) / action_entropy, 6) if best_sum is not None and action_entropy > 0 else None,
        "synergy_bits": round(whole - max(parts.values()), 6),
        "explained_fraction": round(whole / action_entropy, 6) if action_entropy > 0 else None,
    }


def integration_report(events: list[EventRecord], *, k: int = 2, n_features: int = 1, n_shuffles: int = 20,
                       min_events: int = 200) -> dict[str, Any]:
    rows = [(e.agent_id, e.mind, e.proposal.kind) for e in events
            if e.event_type == "action" and e.mind and e.proposal is not None]
    by_agent: dict[str, tuple[list[dict[str, float]], list[str]]] = {}
    for aid, mind, action in rows:
        minds, actions = by_agent.setdefault(aid, ([], []))
        minds.append(mind)
        actions.append(action)
    per_agent = {}
    for aid in sorted(by_agent):
        minds, actions = by_agent[aid]
        if len(actions) >= min_events:
            per_agent[aid] = integration_from_samples(minds, actions, k=k, n_features=n_features, n_shuffles=n_shuffles, seed=len(actions))
    pooled = integration_from_samples([m for _, m, _ in rows], [a for _, _, a in rows], k=k, n_features=n_features, n_shuffles=n_shuffles)
    phis = [r["phi_bits"] for r in per_agent.values() if r.get("phi_bits") is not None]
    return {
        "pooled": pooled,
        "per_agent": per_agent,
        "summary": {
            "agents_measured": len(phis),
            "agents_with_positive_phi": sum(1 for p in phis if p > 0),
            "phi_mean_bits": round(sum(phis) / len(phis), 6) if phis else None,
            "phi_min_bits": round(min(phis), 6) if phis else None,
            "phi_max_bits": round(max(phis), 6) if phis else None,
        },
    }


def render_integration(report: dict[str, Any]) -> str:
    p, s = report["pooled"], report["summary"]

    def fmt(v: float | None) -> str:
        return "—" if v is None else f"{v:+.3f}"

    if p.get("phi_bits") is None:
        return f"Muestras insuficientes para medir integración (n={p['n']})."
    parts = " · ".join(f"{c} {fmt(v)}" for c, v in p["information_parts_bits"].items())
    mip = p["mip"]
    lines = [
        f"Decisiones: {p['n']} · entropía de la acción {p['action_entropy_bits']:.3f} bits",
        f"Criterio 6 · información del todo sobre la acción: {fmt(p['information_whole_bits'])} bits "
        f"({p['explained_fraction']:.1%} de la entropía)",
        f"Por componente (bits): {parts}",
        f"Partición de información mínima: {'+'.join(mip[0])} | {'+'.join(mip[1])} → {fmt(p['information_mip_bits'])} bits",
        f"Φ conductual = todo − MIP: {fmt(p['phi_bits'])} bits (normalizado {fmt(p['phi_normalized'])}) · "
        f"sinergia sobre el mejor componente: {fmt(p['synergy_bits'])} bits",
        f"Por agente: {s['agents_measured']} medidos, {s['agents_with_positive_phi']} con Φ > 0 · "
        f"media {fmt(s['phi_mean_bits'])} · mín {fmt(s['phi_min_bits'])} · máx {fmt(s['phi_max_bits'])}",
    ]
    return "\n".join(lines)
