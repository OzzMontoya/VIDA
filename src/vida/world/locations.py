"""Lugares del mundo textual (sección 16).

``Location.resources`` es la **verdad objetiva** sobre el stock. Los agentes
sólo la conocen cuando la perciben en el lugar o cuando alguien se la cuenta.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LocationType = Literal["home", "plaza", "market", "school", "hospital", "workplace"]


class Location(BaseModel):
    id: str
    name: str
    type: LocationType
    resources: dict[str, int] = Field(default_factory=dict)
    restock: dict[str, int] = Field(default_factory=dict)  # reposición diaria por recurso
    capacity: int | None = None
    prices: dict[str, float] = Field(default_factory=dict)  # sobrescribe el precio global por recurso
    wage: float | None = None  # salario por tick si es lugar de trabajo (None = economía global)
    work_energy: float | None = None  # energía gastada por tick de trabajo (None = valor por defecto)
    open_hours: tuple[int, int] | None = None  # [apertura, cierre) en horas; None = siempre abierto
    adjacent: list[str] = Field(default_factory=list)

    def is_open(self, hour: int) -> bool:
        if self.open_hours is None:
            return True
        start, end = self.open_hours
        return start <= hour < end

    def stock(self, resource: str) -> int:
        return self.resources.get(resource, 0)

    def take(self, resource: str, amount: int = 1) -> int:
        """Retira hasta ``amount`` unidades y devuelve cuántas retiró realmente."""
        available = self.stock(resource)
        taken = min(available, amount)
        if taken > 0:
            self.resources[resource] = available - taken
        return taken

    def apply_restock(self) -> dict[str, int]:
        """Repone recursos hasta el nivel de reposición diario; devuelve los cambios."""
        changes: dict[str, int] = {}
        for resource, target in sorted(self.restock.items()):
            current = self.stock(resource)
            if current < target:
                self.resources[resource] = target
                changes[resource] = target - current
        return changes
