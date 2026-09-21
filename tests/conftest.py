"""Fixtures compartidas: configuración por defecto, mundo pequeño y agentes."""

from pathlib import Path

import pytest

from vida.simulation.config import RunConfig, load_config
from vida.simulation.rng import RngHub
from vida.world.presets import build_world, spawn_agents

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.yaml"


@pytest.fixture
def cfg() -> RunConfig:
    return load_config(CONFIG_PATH)


@pytest.fixture
def small_cfg(cfg: RunConfig) -> RunConfig:
    """Configuración corta: 2 agentes, 48 ticks, semilla fija."""
    c = cfg.model_copy(deep=True)
    c.run.seed = 7
    c.run.ticks = 48
    c.agents.n_agents = 2
    return c


@pytest.fixture
def small_world(small_cfg: RunConfig):
    """Devuelve (world, agents, hub) con dos agentes colocados en sus casas."""
    hub = RngHub(small_cfg.run.seed)
    world = build_world(small_cfg)
    agents = spawn_agents(small_cfg, world, hub.sub("spawn"))
    return world, agents, hub
