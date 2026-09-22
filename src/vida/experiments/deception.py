"""Experimento de engaño (sección 20): poblaciones con distinta honestidad inicial.

Mide tasa de engaño, confianza media, reputación, intercambios de información
y fracasos de compra atribuibles a información falsa. La verdad de cada
mensaje la registra el mundo; los agentes sólo descubren el engaño por sus
consecuencias.
"""

from __future__ import annotations

from vida.simulation.config import RunConfig

KEY_METRICS = ["deception_rate", "deception_rate_early", "deception_rate_late", "lies_discovered", "mean_trust", "reputation",
               "social_acceptance_rate"]


def honestos(cfg: RunConfig) -> RunConfig:
    cfg.agents.initial_honesty = 0.9
    return cfg


def neutros(cfg: RunConfig) -> RunConfig:
    cfg.agents.initial_honesty = 0.5
    return cfg


def deshonestos(cfg: RunConfig) -> RunConfig:
    cfg.agents.initial_honesty = 0.1
    return cfg


def deshonestos_con_escasez(cfg: RunConfig) -> RunConfig:
    """La competencia por recursos escasos eleva la probabilidad de mentir en el motor por reglas."""
    cfg.agents.initial_honesty = 0.1
    cfg.world.restock_factor = 0.4
    return cfg


VARIANTS = {"honestos": honestos, "neutros": neutros, "deshonestos": deshonestos, "deshonestos_con_escasez": deshonestos_con_escasez}
