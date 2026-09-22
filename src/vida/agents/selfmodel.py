"""Automodelo predictivo del agente (criterio 1 de ``docs/criterios_consciencia.md``).

Antes de actuar, el agente predice con su propia memoria la probabilidad de
que la acción elegida tenga éxito. El mundo resuelve el resultado y se registra
el error de predicción, junto con el de un modelo externo de referencia (la
tasa de éxito poblacional de esa acción). Con ello se miden:

- **calibración**: 1 − error absoluto medio de la predicción propia;
- **ventaja del automodelo**: error del modelo externo − error propio. Si es
  positiva, el agente se predice a sí mismo mejor que un observador con la
  información poblacional.

El error reciente también modula la exploración: un agente cuyo automodelo
falla amplía el margen de acciones casi empatadas entre las que elige.
Nada de esto afirma un estado interno; es un mecanismo medible.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from vida.memory.base import AgentMemory

PRIOR_SUCCESS = 0.7
PRIOR_WEIGHT = 2.0


class SelfModelState(BaseModel):
    n: int = 0
    abs_error_sum: float = 0.0
    baseline_error_sum: float = 0.0
    recent_errors: list[float] = Field(default_factory=list)  # ventana móvil (último día)

    def record(self, predicted: float, baseline: float, actual: bool, window: int = 24) -> tuple[float, float]:
        y = 1.0 if actual else 0.0
        own = abs(predicted - y)
        base = abs(baseline - y)
        self.n += 1
        self.abs_error_sum = round(self.abs_error_sum + own, 6)
        self.baseline_error_sum = round(self.baseline_error_sum + base, 6)
        self.recent_errors.append(round(own, 6))
        del self.recent_errors[:-window]
        return own, base

    def calibration(self) -> float:
        return round(1.0 - self.abs_error_sum / self.n, 6) if self.n else 0.0

    def advantage(self) -> float:
        return round((self.baseline_error_sum - self.abs_error_sum) / self.n, 6) if self.n else 0.0

    def recent_error(self) -> float:
        return round(sum(self.recent_errors) / len(self.recent_errors), 6) if self.recent_errors else 0.0


def predict_success(memory: AgentMemory, action_tags: set[str]) -> float:
    """Tasa de éxito propia para acciones con esas etiquetas, con prior suavizado."""
    records = [r for r in memory.by_kind("episodic") if action_tags.issubset(r.tags)]
    successes = sum(1 for r in records if "outcome:ok" in r.tags)
    return round((successes + PRIOR_SUCCESS * PRIOR_WEIGHT) / (len(records) + PRIOR_WEIGHT), 6)


class PopulationModel:
    """Modelo externo de referencia: tasa de éxito de cada acción en toda la población."""

    def __init__(self) -> None:
        self.attempts: dict[str, int] = {}
        self.successes: dict[str, int] = {}

    def rate(self, action: str) -> float:
        n = self.attempts.get(action, 0)
        return round((self.successes.get(action, 0) + PRIOR_SUCCESS * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT), 6)

    def update(self, action: str, success: bool) -> None:
        self.attempts[action] = self.attempts.get(action, 0) + 1
        if success:
            self.successes[action] = self.successes.get(action, 0) + 1
