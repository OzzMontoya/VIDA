"""Configuración tipada de una corrida (``config/default.yaml``).

Todo parámetro que influya en el resultado de la simulación debe vivir aquí.
``config_hash`` produce un identificador estable del contenido canonizado y se
guarda con cada corrida para poder reproducirla.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

NeedName = Literal["hunger", "energy", "health", "social", "safety", "knowledge"]
NEED_NAMES: tuple[NeedName, ...] = ("hunger", "energy", "health", "social", "safety", "knowledge")


class RunSection(BaseModel):
    seed: int = 42
    ticks: int = 720
    ticks_per_day: int = 24
    snapshot_every_ticks: int = 24


class WorldSection(BaseModel):
    preset: str = "village_small"


class AgeRange(BaseModel):
    min: int = 20
    max: int = 40


class AgentsSection(BaseModel):
    n_agents: int = 10
    initial_age_days: AgeRange = Field(default_factory=AgeRange)
    starting_money: float = 20.0


class NeedConfig(BaseModel):
    decay_per_tick: float
    critical_below: float = 0.1


class StageThresholds(BaseModel):
    """Día simulado en el que empieza cada etapa (la infancia empieza en 0)."""

    adolescence: int = 12
    youth: int = 18
    adulthood: int = 30
    old_age: int = 65


class LifecycleSection(BaseModel):
    stage_thresholds_days: StageThresholds = Field(default_factory=StageThresholds)
    max_age_days: int = 85
    critical_ticks: int = 12
    old_age_health_factor: float = 3.0


class MemoryWeights(BaseModel):
    recency: float = 1.0
    importance: float = 1.0
    relevance: float = 1.0


class MemorySection(BaseModel):
    retrieve_k: int = 8
    weights: MemoryWeights = Field(default_factory=MemoryWeights)
    recency_decay: float = 0.99
    forget_below: float = 0.2
    forget_after_days: int = 7


class DecisionSection(BaseModel):
    engine: str = "rules_v1"
    epsilon: float = 0.01


class RunConfig(BaseModel):
    run: RunSection = Field(default_factory=RunSection)
    world: WorldSection = Field(default_factory=WorldSection)
    agents: AgentsSection = Field(default_factory=AgentsSection)
    needs: dict[NeedName, NeedConfig]
    lifecycle: LifecycleSection = Field(default_factory=LifecycleSection)
    memory: MemorySection = Field(default_factory=MemorySection)
    decision: DecisionSection = Field(default_factory=DecisionSection)

    @model_validator(mode="after")
    def _all_needs_present(self) -> "RunConfig":
        missing = [n for n in NEED_NAMES if n not in self.needs]
        if missing:
            raise ValueError(f"Faltan necesidades en la configuración: {missing}")
        return self


def load_config(path: str | Path) -> RunConfig:
    """Carga y valida un YAML de configuración."""
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return RunConfig.model_validate(raw)


def canonical_json(cfg: RunConfig) -> str:
    return json.dumps(cfg.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def config_hash(cfg: RunConfig) -> str:
    """SHA-256 del contenido canonizado. Cambia si cambia cualquier parámetro."""
    return hashlib.sha256(canonical_json(cfg).encode("utf-8")).hexdigest()
