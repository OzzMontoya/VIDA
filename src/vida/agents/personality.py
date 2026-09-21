"""Personalidad del agente: cinco rasgos continuos en [0, 1] (modelo Big Five).

Los rasgos modulan el peso de las acciones en el motor de decisión y la
propensión a engañar en las respuestas informativas. No cambian durante
VIDA-0.1; en fases posteriores podrán derivar lentamente con la experiencia.
"""

from __future__ import annotations

import random

from pydantic import BaseModel, Field


class Personality(BaseModel):
    openness: float = Field(0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(0.5, ge=0.0, le=1.0)
    extraversion: float = Field(0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(0.5, ge=0.0, le=1.0)

    @classmethod
    def random(cls, rng: random.Random) -> "Personality":
        """Personalidad aleatoria evitando extremos (0.1 a 0.9)."""
        return cls(
            openness=round(rng.uniform(0.1, 0.9), 3),
            conscientiousness=round(rng.uniform(0.1, 0.9), 3),
            extraversion=round(rng.uniform(0.1, 0.9), 3),
            agreeableness=round(rng.uniform(0.1, 0.9), 3),
            neuroticism=round(rng.uniform(0.1, 0.9), 3),
        )

    def dominant_traits(self, threshold: float = 0.7) -> list[str]:
        """Rasgos por encima del umbral, en orden estable."""
        return [name for name, value in sorted(self.model_dump().items()) if value >= threshold]
