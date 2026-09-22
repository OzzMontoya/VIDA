"""Experimentos configurables (sección 19): memoria, entorno, engaño y transferencia.

Uso: ``python -m vida experiment <nombre> --seeds 1,2,3 --ticks 240``.
Cada experimento de variantes vive en su módulo con ``VARIANTS`` (nombre →
función que modifica la configuración) y ``KEY_METRICS`` (columnas del resumen).
El experimento de transferencia tiene su propio flujo (clonación del mundo).
"""

from __future__ import annotations

from vida.experiments import deception, environment, memory, transfer

VARIANT_EXPERIMENTS = {
    "memory": (memory.VARIANTS, memory.KEY_METRICS),
    "environment": (environment.VARIANTS, environment.KEY_METRICS),
    "deception": (deception.VARIANTS, deception.KEY_METRICS),
}
EXPERIMENT_NAMES = sorted(VARIANT_EXPERIMENTS) + ["transfer"]

__all__ = ["VARIANT_EXPERIMENTS", "EXPERIMENT_NAMES", "transfer"]
