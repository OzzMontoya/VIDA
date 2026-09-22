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
    restock_factor: float = 1.0  # multiplica la reposición diaria (abundancia > 1, escasez < 1)
    shortage_days: list[int] = Field(default_factory=lambda: [10, 20])  # días con escasez programada en el mercado


class AgeRange(BaseModel):
    min: int = 20
    max: int = 40


class AgentsSection(BaseModel):
    n_agents: int = 10
    initial_age_days: AgeRange = Field(default_factory=AgeRange)
    starting_money: float = 20.0
    initial_honesty: float | None = None  # valor inicial de honestidad (None = 0.5); experimento de engaño


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
    retrieve_k: int = 8  # 0 = el agente no recupera memorias al decidir (condición "sin memoria")
    weights: MemoryWeights = Field(default_factory=MemoryWeights)
    recency_decay: float = 0.99
    forget_below: float = 0.2
    forget_after_days: int = 7
    forget_kinds: list[str] = Field(default_factory=lambda: ["episodic"])  # tipos sujetos a olvido


class LLMSection(BaseModel):
    """Parámetros del motor de decisión basado en LLM (``engine: llm_v1``).

    ``agents`` limita qué agentes deciden con el LLM (los demás usan reglas);
    ``None`` significa todos. ``cache_path`` guarda cada respuesta por hash del
    prompt para poder repetir una corrida sin volver a llamar a la API.
    """

    provider: Literal["anthropic", "ollama"] = "anthropic"  # ollama = modelo local gratuito (http://localhost:11434)
    base_url: str | None = None  # para ollama; por defecto http://localhost:11434
    num_gpu: int | None = 0  # ollama: capas en GPU; 0 fuerza CPU (las GPU AMD viejas vía Vulkan generan texto corrupto)
    model: str = "claude-opus-5"
    effort: str | None = "low"  # low | medium | high | xhigh | max; None omite el parámetro (sólo anthropic)
    max_tokens: int = 1024
    agents: list[str] | None = None
    cache_path: str | None = "data/llm_cache.sqlite"
    fallback_to_rules: bool = True
    server_fallbacks: bool = True  # fallbacks="default" del servidor ante una negativa de seguridad
    include_heuristic_scores: bool = False  # mostrar al LLM el puntaje de las reglas como orientación
    max_memories: int = 6
    timeout_seconds: float = 60.0


class DecisionSection(BaseModel):
    engine: str = "rules_v1"
    epsilon: float = 0.01
    llm: LLMSection = Field(default_factory=LLMSection)


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
