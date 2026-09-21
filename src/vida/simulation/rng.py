"""Generación de números aleatorios reproducible.

Regla del proyecto: ningún módulo usa ``random`` global ni ``numpy.random`` sin
semilla. Cada subsistema (y cada agente dentro de él) obtiene su propio flujo a
partir de ``RngHub.sub(...)``, derivado determinísticamente de la semilla de la
corrida. Así, añadir consumo aleatorio en un subsistema no altera los demás.
"""

from __future__ import annotations

import hashlib
import random


class RngHub:
    """Fábrica de generadores ``random.Random`` derivados de una semilla raíz.

    ``sub("decision", "a01")`` devuelve siempre el mismo objeto dentro de una
    corrida (se cachea), por lo que el flujo continúa entre ticks en lugar de
    reiniciarse.
    """

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._streams: dict[tuple[str, ...], random.Random] = {}

    def sub(self, *keys: object) -> random.Random:
        key = tuple(str(k) for k in keys)
        stream = self._streams.get(key)
        if stream is None:
            material = f"{self.seed}:{'/'.join(key)}".encode("utf-8")
            digest = hashlib.sha256(material).digest()
            stream = random.Random(int.from_bytes(digest[:8], "big"))
            self._streams[key] = stream
        return stream

    def derive_seed(self, *keys: object) -> int:
        """Semilla entera derivada, útil para librerías externas."""
        material = f"{self.seed}:{'/'.join(str(k) for k in keys)}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
