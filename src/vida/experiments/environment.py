"""Experimento de entorno (sección 19): abundancia, normalidad y escasez.

Compara cómo la disponibilidad de recursos modifica supervivencia, engaño,
confianza, fracasos de compra y consistencia conductual.
"""

from __future__ import annotations

from vida.simulation.config import RunConfig

KEY_METRICS = ["alive", "failed_acquires", "deception_rate", "mean_trust", "money", "behavioural_consistency",
               "mean_need_level"]


def abundancia(cfg: RunConfig) -> RunConfig:
    cfg.world.restock_factor = 2.0
    cfg.world.shortage_days = []
    return cfg


def normal(cfg: RunConfig) -> RunConfig:
    return cfg


def escasez(cfg: RunConfig) -> RunConfig:
    cfg.world.restock_factor = 0.4
    days = cfg.run.ticks // cfg.run.ticks_per_day
    cfg.world.shortage_days = list(range(3, max(4, days), 4))
    return cfg


VARIANTS = {"abundancia": abundancia, "normal": normal, "escasez": escasez}
