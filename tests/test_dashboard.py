"""Dashboard: la capa de datos carga una corrida real y las cuatro vistas se renderizan sin excepciones."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
pd = pytest.importorskip("pandas")

from streamlit.testing.v1 import AppTest  # noqa: E402

from vida.cli import main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(ROOT / "config" / "default.yaml")


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("dash")
    data, logs = base / "data", base / "logs"
    rc = main(["--data-dir", str(data), "run", "--config", CONFIG, "--seed", "5", "--ticks", "72",
               "--run-id", "dash_test", "--log-dir", str(logs)])
    assert rc == 0
    return data


def test_data_layer_loads_run(run_dir):
    import sys
    sys.path.insert(0, str(ROOT))
    from dashboard.data import alive_per_tick, deception_summary, list_runs, load_run, occupancy_by_type

    runs = list_runs(run_dir)
    assert [r[0] for r in runs] == ["dash_test"]
    data = load_run(runs[0][1])
    assert data.run_id == "dash_test" and data.n_days == 3
    assert len(data.events) == int(data.meta["n_events"])
    assert set(data.final_states) == set(data.initial_states) == set(data.names)
    assert {"need_hunger", "action_group", "location_type"} <= set(data.events.columns)
    alive = alive_per_tick(data)
    assert alive["vivos"].iloc[0] == len(data.agents)
    occ = occupancy_by_type(data)
    assert abs(occ.iloc[0].sum() - len(data.agents)) < 1e-6
    assert set(deception_summary(data).columns) == {"agent_id", "intent", "n"}
    assert not data.resources.empty and data.resources["stock"].min() >= 0


@pytest.mark.parametrize("view", ["🌍 Corrida", "🧍 Agente", "🤝 Sociedad", "🌳 Linaje", "📋 Eventos"])
def test_every_view_renders_without_errors(run_dir, view):
    at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=120)
    at.run()
    at.sidebar.text_input[0].set_value(str(run_dir)).run()
    at.sidebar.radio[0].set_value(view).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "VIDA · corrida dash_test"
    assert len(at.metric) >= 5
