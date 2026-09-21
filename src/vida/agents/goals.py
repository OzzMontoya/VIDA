"""Objetivos y preferencias del agente.

Las preferencias se aprenden por consecuencias: cada resultado observado
desplaza la valencia hacia lo vivido y refuerza la fuerza de la preferencia.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GoalKind = Literal["satisfy_need", "acquire", "learn", "bond"]


class Goal(BaseModel):
    id: str
    kind: GoalKind
    target: str  # nombre de necesidad, recurso, habilidad o id de agente
    priority: float = Field(0.5, ge=0.0, le=1.0)
    created_tick: int = 0
    achieved_tick: int | None = None

    @property
    def active(self) -> bool:
        return self.achieved_tick is None


class Preference(BaseModel):
    """Preferencia sobre un sujeto como ``"loc:market"``, ``"res:bread"`` o ``"action:work"``."""

    subject: str
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    strength: float = Field(0.0, ge=0.0, le=1.0)

    def update(self, observed_valence: float, rate: float = 0.2) -> float:
        """Acerca la valencia a lo observado y devuelve el cambio aplicado."""
        before = self.valence
        self.valence = max(-1.0, min(1.0, self.valence + rate * (observed_valence - self.valence)))
        self.strength = min(1.0, self.strength + 0.05)
        return round(self.valence - before, 6)
