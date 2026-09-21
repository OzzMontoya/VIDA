"""Necesidades del agente.

Cada necesidad tiene un nivel en [0, 1] (1 = satisfecha, 0 = crítica) que decae
cada tick. La *urgencia* ``(1 - level)^2`` crece de forma no lineal para que las
necesidades casi críticas dominen la decisión.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from vida.simulation.config import NEED_NAMES, NeedName, RunConfig


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


class Need(BaseModel):
    level: float = Field(1.0, ge=0.0, le=1.0)
    decay_per_tick: float = Field(..., ge=0.0)
    critical_below: float = Field(0.1, ge=0.0, le=1.0)

    def is_critical(self) -> bool:
        return self.level < self.critical_below

    def urgency(self) -> float:
        return (1.0 - self.level) ** 2

    def decay(self, factor: float = 1.0) -> None:
        self.level = clamp01(self.level - self.decay_per_tick * factor)

    def apply(self, delta: float) -> None:
        self.level = clamp01(self.level + delta)


def build_needs(cfg: RunConfig, levels: dict[str, float] | None = None) -> dict[NeedName, Need]:
    """Construye el diccionario de necesidades desde la configuración."""
    levels = levels or {}
    return {
        name: Need(
            level=clamp01(levels.get(name, 1.0)),
            decay_per_tick=cfg.needs[name].decay_per_tick,
            critical_below=cfg.needs[name].critical_below,
        )
        for name in NEED_NAMES
    }
