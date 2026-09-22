"""Automodelo predictivo del agente (criterio 1 de ``docs/criterios_consciencia.md``).

Antes de actuar, el agente predice la probabilidad de éxito de la acción
elegida a partir de su **propia experiencia en contexto**: qué acción, sobre
qué objetivo, a qué hora del día y con qué estado de necesidades. El mundo
resuelve el resultado y se registra el error de predicción junto con el de un
modelo externo de referencia que conoce el mismo contexto pero con los datos de
toda la población. Con ello se miden:

- **calibración**: 1 − error absoluto medio de la predicción propia;
- **ventaja del automodelo**: error del modelo externo − error propio. Si es
  positiva, la historia individual aporta información predictiva que la
  población con el mismo contexto no tiene.

La tabla de contexto es jerárquica: si no hay evidencia suficiente en el
contexto más específico, retrocede a uno más general (acción+objetivo+hora →
acción+objetivo → acción → prior). El error reciente amplía la exploración
del agente (metacognición mínima, medible). Nada de esto afirma un estado
interno; es un mecanismo cuantificable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from vida.memory.base import AgentMemory

if TYPE_CHECKING:
    from vida.agents.agent import AgentState

PRIOR_SUCCESS = 0.7
PRIOR_WEIGHT = 2.0
MIN_EVIDENCE = 3  # intentos necesarios en un nivel de contexto para usarlo sin retroceder


def _bucket(level: float) -> str:
    return "crit" if level < 0.3 else "low" if level < 0.6 else "ok"


def context_levels(action: str, target: str | None, hour: int, ticks_per_day: int, needs: dict[str, float]) -> list[str]:
    """Claves de contexto de lo más específico a lo más general."""
    period = f"p{int(hour * 4 // max(1, ticks_per_day))}"  # cuatro franjas del día
    hunger = _bucket(needs.get("hunger", 1.0))
    energy = _bucket(needs.get("energy", 1.0))
    tgt = target or "-"
    return [
        f"{action}|{tgt}|{period}|h={hunger}|e={energy}",
        f"{action}|{tgt}|{period}",
        f"{action}|{tgt}",
        f"{action}",
    ]


def own_context_levels(agent: "AgentState", action: str, target: str | None, hour: int, ticks_per_day: int) -> list[str]:
    """Niveles del automodelo propio: conocimiento privado (relación, habilidad) delante del contexto público.

    El observador externo (``PopulationModel``) sólo ve el contexto público; lo que
    el agente sabe de sí mismo y de su relación con el otro es información
    individual genuina.
    """
    needs = {n: agent.needs[n].level for n in agent.needs}
    public = context_levels(action, target, hour, ticks_per_day, needs)
    private: list[str] = []
    if action == "socialize" and target:
        rel = agent.relationships.get(target)
        trust = _bucket(rel.trust if rel else 0.5)
        affection = _bucket(rel.affection if rel else 0.5)
        private.append(f"{action}|{target}|trust={trust}|aff={affection}|rep={_bucket(agent.reputation)}")
    elif action == "work":
        private.append(f"{action}|{target or '-'}|skill={_bucket(agent.knowledge_level('job'))}|e={_bucket(needs.get('energy', 1.0))}")
    return private + public


class ContextTable(BaseModel):
    """Conteos de éxito/intento por clave de contexto, con retroceso jerárquico."""

    counts: dict[str, list[int]] = Field(default_factory=dict)  # clave -> [éxitos, intentos]

    def predict(self, levels: list[str]) -> float:
        for key in levels:
            s, n = self.counts.get(key, [0, 0])
            if n >= MIN_EVIDENCE:
                return round((s + PRIOR_SUCCESS * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT), 6)
        # Sin evidencia suficiente en ningún nivel: prior suavizado con lo poco que haya del nivel más general.
        s, n = self.counts.get(levels[-1], [0, 0]) if levels else (0, 0)
        return round((s + PRIOR_SUCCESS * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT), 6)

    def update(self, levels: list[str], success: bool) -> None:
        for key in levels:
            cell = self.counts.setdefault(key, [0, 0])
            cell[0] += 1 if success else 0
            cell[1] += 1

    def total_attempts(self) -> int:
        return sum(n for _, n in self.counts.values()) // 4 if self.counts else 0

    def has_evidence(self, key: str) -> bool:
        return self.counts.get(key, [0, 0])[1] >= MIN_EVIDENCE


class SelfModelState(BaseModel):
    table: ContextTable = Field(default_factory=ContextTable)
    n: int = 0
    abs_error_sum: float = 0.0
    baseline_error_sum: float = 0.0
    recent_errors: list[float] = Field(default_factory=list)  # ventana móvil (último día)
    # Comparación emparejada: sólo predicciones donde el agente ya tenía evidencia en el contexto más específico.
    matched_n: int = 0
    matched_abs_error_sum: float = 0.0
    matched_baseline_error_sum: float = 0.0

    def predict(self, levels: list[str]) -> float:
        return self.table.predict(levels)

    def learn(self, levels: list[str], success: bool) -> None:
        self.table.update(levels, success)

    def record(self, predicted: float, baseline: float, actual: bool, window: int = 24, matched: bool = False) -> tuple[float, float]:
        y = 1.0 if actual else 0.0
        own = abs(predicted - y)
        base = abs(baseline - y)
        self.n += 1
        self.abs_error_sum = round(self.abs_error_sum + own, 6)
        self.baseline_error_sum = round(self.baseline_error_sum + base, 6)
        if matched:
            self.matched_n += 1
            self.matched_abs_error_sum = round(self.matched_abs_error_sum + own, 6)
            self.matched_baseline_error_sum = round(self.matched_baseline_error_sum + base, 6)
        self.recent_errors.append(round(own, 6))
        del self.recent_errors[:-window]
        return own, base

    def calibration(self) -> float:
        return round(1.0 - self.abs_error_sum / self.n, 6) if self.n else 0.0

    def advantage(self) -> float:
        return round((self.baseline_error_sum - self.abs_error_sum) / self.n, 6) if self.n else 0.0

    def advantage_matched(self) -> float:
        """Ventaja sólo donde la experiencia propia era específica: aísla la información individual."""
        return round((self.matched_baseline_error_sum - self.matched_abs_error_sum) / self.matched_n, 6) if self.matched_n else 0.0

    def recent_error(self) -> float:
        return round(sum(self.recent_errors) / len(self.recent_errors), 6) if self.recent_errors else 0.0


def predict_success(memory: AgentMemory, action_tags: set[str]) -> float:
    """Tasa de éxito propia según la memoria episódica (sin contexto). Se conserva como referencia simple."""
    records = [r for r in memory.by_kind("episodic") if action_tags.issubset(r.tags)]
    successes = sum(1 for r in records if "outcome:ok" in r.tags)
    return round((successes + PRIOR_SUCCESS * PRIOR_WEIGHT) / (len(records) + PRIOR_WEIGHT), 6)


class PopulationModel:
    """Modelo externo de referencia: misma tabla de contexto, alimentada por toda la población."""

    def __init__(self) -> None:
        self.table = ContextTable()

    def predict(self, levels: list[str]) -> float:
        return self.table.predict(levels)

    def update(self, levels: list[str], success: bool) -> None:
        self.table.update(levels, success)

    # Compatibilidad con la versión sin contexto.
    def rate(self, action: str) -> float:
        return self.table.predict([action])
