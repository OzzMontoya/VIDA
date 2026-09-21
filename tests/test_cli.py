"""CLI: corrida corta, listado y biografías con las siete secciones."""

import json

import pytest

from vida.cli import main
from vida.database.repository import RunRepository

CONFIG = "config/default.yaml"
SECTIONS = ["1) QUÉ VIVIÓ", "2) QUÉ RECUERDA", "3) QUÉ APRENDIÓ", "4) QUÉ PREFIERE",
            "5) A QUIÉN CONOCE", "6) QUÉ DECISIONES TOMÓ", "7) QUÉ EXPERIENCIAS LO MODIFICARON"]


@pytest.fixture
def run_dirs(tmp_path):
    data, logs = tmp_path / "data", tmp_path / "logs"
    rc = main(["--data-dir", str(data), "run", "--config", CONFIG, "--seed", "11", "--ticks", "72",
               "--run-id", "cli_test", "--log-dir", str(logs)])
    assert rc == 0
    return data, logs


def test_run_creates_db_and_jsonl(run_dirs, capsys):
    data, logs = run_dirs
    assert (data / "cli_test" / "vida.sqlite").exists()
    jsonl = logs / "cli_test" / "events.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 700  # 10 agentes × 72 ticks más eventos del mundo
    first = json.loads(lines[0])
    assert first["run_id"] == "cli_test"
    # Segunda corrida con la misma semilla: mismo hash de eventos (reproducibilidad de extremo a extremo).
    rc = main(["--data-dir", str(data), "run", "--config", CONFIG, "--seed", "11", "--ticks", "72",
               "--run-id", "cli_test_2", "--log-dir", str(logs), "--json"])
    assert rc == 0
    second = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    repo = RunRepository(data / "cli_test" / "vida.sqlite")
    first_meta = repo.run_meta("cli_test")
    repo.close()
    assert second["run_id"] == "cli_test_2"
    assert second["events_sha256"] == first_meta["events_sha256"]
    lines2 = (logs / "cli_test_2" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines2) == len(lines)


def test_runs_lists_the_run(run_dirs, capsys):
    data, _ = run_dirs
    assert main(["--data-dir", str(data), "runs"]) == 0
    out = capsys.readouterr().out
    assert "cli_test" in out and " 11 " in out


def test_life_prints_seven_sections_for_every_agent(run_dirs, capsys):
    data, _ = run_dirs
    non_empty_days = 0
    for i in range(1, 11):
        aid = f"a{i:02d}"
        assert main(["--data-dir", str(data), "life", aid, "--run", "cli_test"]) == 0
        out = capsys.readouterr().out
        assert f"({aid})" in out
        for section in SECTIONS:
            assert section in out, f"{aid} sin sección {section}"
        if "Día 0:" in out or "Día 1:" in out:
            non_empty_days += 1
    assert non_empty_days == 10


def test_life_json_and_errors(run_dirs, capsys):
    data, _ = run_dirs
    assert main(["--data-dir", str(data), "life", "a01", "--run", "cli_test", "--json"]) == 0
    bio = json.loads(capsys.readouterr().out)
    assert bio["agent_id"] == "a01" and bio["name"] == "Ana"
    assert bio["decisions"] and bio["lived_days"]
    assert main(["--data-dir", str(data), "life", "zz", "--run", "cli_test"]) == 1
    assert main(["--data-dir", str(data), "life", "a01", "--run", "nope"]) == 1
