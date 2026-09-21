"""Interfaz de línea de comandos.

    python -m vida run  --config config/default.yaml [--seed N] [--ticks N]
    python -m vida life <agent_id> --run <run_id>
    python -m vida runs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vida import __version__
from vida.database.repository import RunRepository
from vida.evaluation.biography import build_biography, render
from vida.simulation.config import load_config
from vida.simulation.engine import SimulationEngine, make_run_id
from vida.simulation.logging import JsonlEventLogger

DEFAULT_DATA_DIR = Path("data") / "runs"
DEFAULT_LOG_DIR = Path("logs")


def _db_path(data_dir: Path, run_id: str) -> Path:
    return data_dir / run_id / "vida.sqlite"


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.seed is not None:
        cfg.run.seed = args.seed
    if args.ticks is not None:
        cfg.run.ticks = args.ticks
    run_id = args.run_id or make_run_id(cfg.run.seed)
    data_dir, log_dir = Path(args.data_dir), Path(args.log_dir)
    repo = RunRepository(_db_path(data_dir, run_id))
    logger = JsonlEventLogger(log_dir / run_id / "events.jsonl")
    engine = SimulationEngine(cfg, run_id, repo=repo, logger=logger)
    print(f"VIDA {__version__} · corrida {run_id} · semilla {cfg.run.seed} · {cfg.run.ticks} ticks "
          f"({cfg.run.ticks // cfg.run.ticks_per_day} días) · {cfg.agents.n_agents} agentes")
    summary = engine.run()
    repo.close()
    if args.json:
        print(summary.model_dump_json(indent=2))
    else:
        print(f"Eventos: {summary.n_events} · hash: {summary.events_sha256[:16]}… · config: {summary.config_hash[:12]}…")
        print(f"Vivos: {', '.join(summary.alive) or 'ninguno'}")
        if summary.deaths:
            print("Muertes: " + ", ".join(f"{aid} ({reason})" for aid, reason in summary.deaths.items()))
        print(f"Base de datos: {_db_path(data_dir, run_id)}")
        print(f"Eventos JSONL: {log_dir / run_id / 'events.jsonl'}")
        print(f"Biografías: python -m vida life <agent_id> --run {run_id}")
    return 0


def cmd_life(args: argparse.Namespace) -> int:
    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        bio = build_biography(repo, args.run, args.agent_id)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        repo.close()
    print(bio.model_dump_json(indent=2) if args.json else render(bio))
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print("No hay corridas.")
        return 0
    rows = []
    for run_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        db = run_dir / "vida.sqlite"
        if not db.exists():
            continue
        repo = RunRepository(db)
        meta = repo.run_meta(run_dir.name)
        repo.close()
        if meta is None:
            continue
        summary = json.loads(meta["summary_json"]) if meta.get("summary_json") else {}
        rows.append((run_dir.name, meta["seed"], meta["n_ticks"], meta["n_events"],
                     len(summary.get("deaths", {})), (meta.get("events_sha256") or "")[:12]))
    if not rows:
        print("No hay corridas.")
        return 0
    print(f"{'run_id':<24} {'seed':>6} {'ticks':>6} {'eventos':>8} {'muertes':>8}  hash")
    for r in rows:
        print(f"{r[0]:<24} {r[1]:>6} {r[2]:>6} {r[3]:>8} {r[4]:>8}  {r[5]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vida", description="VIDA: simulador de vidas artificiales")
    parser.add_argument("--version", action="version", version=f"vida {__version__}")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="directorio de bases SQLite por corrida")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="ejecutar una corrida")
    run.add_argument("--config", default="config/default.yaml")
    run.add_argument("--seed", type=int)
    run.add_argument("--ticks", type=int)
    run.add_argument("--run-id", help="identificador explícito (por defecto fecha_hora_semilla)")
    run.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    run.add_argument("--json", action="store_true", help="imprimir el resumen como JSON")
    run.set_defaults(func=cmd_run)

    life = sub.add_parser("life", help="reconstruir la biografía de un agente")
    life.add_argument("agent_id")
    life.add_argument("--run", required=True)
    life.add_argument("--json", action="store_true")
    life.set_defaults(func=cmd_life)

    runs = sub.add_parser("runs", help="listar corridas")
    runs.set_defaults(func=cmd_runs)
    return parser


def _force_utf8_stdout() -> None:
    """En consolas Windows con página de códigos heredada, evita mojibake en los acentos."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
