"""Reloj simulado: tiempo discreto en ticks, acelerado y configurable (sección 17)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SimClock(BaseModel):
    tick: int = 0
    ticks_per_day: int = Field(24, ge=1)

    @property
    def day(self) -> int:
        return self.tick // self.ticks_per_day

    @property
    def hour(self) -> int:
        return self.tick % self.ticks_per_day

    def is_day_start(self) -> bool:
        return self.hour == 0

    def advance(self) -> None:
        self.tick += 1
