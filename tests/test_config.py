"""Configuración y RNG: carga, validación, hash estable y flujos aislados."""

from pathlib import Path

import pytest

from vida.simulation.config import RunConfig, config_hash, load_config
from vida.simulation.rng import RngHub

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.yaml"


def test_default_config_loads():
    cfg = load_config(CONFIG_PATH)
    assert cfg.run.seed == 42
    assert cfg.agents.n_agents == 10
    assert set(cfg.needs) == {"hunger", "energy", "health", "social", "safety", "knowledge"}


def test_config_hash_is_stable_and_sensitive():
    a = load_config(CONFIG_PATH)
    b = load_config(CONFIG_PATH)
    assert config_hash(a) == config_hash(b)
    c = a.model_copy(deep=True)
    c.run.seed = 7
    assert config_hash(c) != config_hash(a)


def test_missing_need_is_rejected():
    with pytest.raises(ValueError):
        RunConfig.model_validate({"needs": {"hunger": {"decay_per_tick": 0.1}}})


def test_rng_streams_are_isolated_and_reproducible():
    hub1, hub2 = RngHub(123), RngHub(123)
    a1 = [hub1.sub("decision", "a01").random() for _ in range(5)]
    a2 = [hub2.sub("decision", "a01").random() for _ in range(5)]
    assert a1 == a2
    # Consumir otro flujo no altera el primero.
    hub3 = RngHub(123)
    hub3.sub("world").random()
    a3 = [hub3.sub("decision", "a01").random() for _ in range(5)]
    assert a3 == a1
    # Flujos distintos producen secuencias distintas.
    assert hub1.sub("decision", "a02").random() != RngHub(123).sub("decision", "a01").random()
    # El flujo persiste entre llamadas (no se reinicia).
    assert hub1.sub("decision", "a01") is hub1.sub("decision", "a01")
