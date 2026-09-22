"""Experimento de memoria (sección 19): completa, limitada, ausente y sin olvido.

Pregunta secundaria del documento: ¿qué cantidad y tipos de memoria son
necesarios para mantener continuidad conductual? Se comparan las métricas de
consistencia conductual, estabilidad de preferencias, fracasos de compra y
supervivencia entre variantes de recuperación y olvido.
"""

from __future__ import annotations

from vida.simulation.config import RunConfig

# Métricas donde la memoria muestra efecto (tamaños de efecto d > 1.5 en la corrida de 2026-09-22):
# hábito (entropía y elecciones distintas), dependencia de otros (intercambios de información),
# vínculo social (confianza, familiaridad) y calidad del automodelo.
KEY_METRICS = ["decision_entropy", "distinct_choices", "info_exchanges", "mean_trust", "mean_familiarity",
               "self_model_calibration", "memory_retained", "alive"]


def completa(cfg: RunConfig) -> RunConfig:
    return cfg


def limitada(cfg: RunConfig) -> RunConfig:
    cfg.memory.retrieve_k = 2
    cfg.memory.forget_below = 0.5
    cfg.memory.forget_after_days = 1
    return cfg


def ausente(cfg: RunConfig) -> RunConfig:
    """Sin recuperación al decidir y olvido total diario de episodios y hechos."""
    cfg.memory.retrieve_k = 0
    cfg.memory.forget_below = 1.01
    cfg.memory.forget_after_days = 0
    cfg.memory.forget_kinds = ["episodic", "semantic", "social", "procedural"]
    return cfg


def sin_olvido(cfg: RunConfig) -> RunConfig:
    cfg.memory.forget_below = 0.0
    cfg.memory.retrieve_k = 16
    return cfg


VARIANTS = {"completa": completa, "limitada": limitada, "ausente": ausente, "sin_olvido": sin_olvido}
