"""Interfaz de línea de comandos.

    python -m vida run  --config config/default.yaml [--seed N] [--ticks N]
    python -m vida life <agent_id> --run <run_id>
    python -m vida runs
"""

from __future__ import annotations

import argparse
import json
import os
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


def load_dotenv(path: Path = Path(".env")) -> None:
    """Carga KEY=VALUE de un .env local sin pisar variables ya definidas (sin dependencias)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def cmd_run(args: argparse.Namespace) -> int:
    load_dotenv()
    cfg = load_config(args.config)
    if args.seed is not None:
        cfg.run.seed = args.seed
    if args.ticks is not None:
        cfg.run.ticks = args.ticks
    if args.engine:
        cfg.decision.engine = args.engine
    if args.llm_provider:
        cfg.decision.llm.provider = args.llm_provider
    if args.llm_model:
        cfg.decision.llm.model = args.llm_model
    if args.llm_agents:
        cfg.decision.llm.agents = [a.strip() for a in args.llm_agents.split(",") if a.strip()]
    if cfg.decision.engine == "llm_v1" and cfg.decision.llm.provider == "anthropic" and not (
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("Aviso: no hay ANTHROPIC_API_KEY en el entorno ni en .env; el motor LLM sólo funcionará con respuestas en caché "
              "y recurrirá a las reglas en el resto.", file=sys.stderr)
    run_id = args.run_id or make_run_id(cfg.run.seed)
    data_dir, log_dir = Path(args.data_dir), Path(args.log_dir)
    repo = RunRepository(_db_path(data_dir, run_id))
    logger = JsonlEventLogger(log_dir / run_id / "events.jsonl")
    engine = SimulationEngine(cfg, run_id, repo=repo, logger=logger)
    llm_txt = ""
    if cfg.decision.engine == "llm_v1":
        who = ", ".join(cfg.decision.llm.agents) if cfg.decision.llm.agents else "todos los agentes"
        llm_txt = f" · LLM {cfg.decision.llm.provider}/{cfg.decision.llm.model} para {who}"
    print(f"VIDA {__version__} · corrida {run_id} · semilla {cfg.run.seed} · {cfg.run.ticks} ticks "
          f"({cfg.run.ticks // cfg.run.ticks_per_day} días) · {cfg.agents.n_agents} agentes · motor {cfg.decision.engine}{llm_txt}")
    summary = engine.run()
    repo.close()
    if args.json:
        print(summary.model_dump_json(indent=2))
    else:
        print(f"Eventos: {summary.n_events} · hash: {summary.events_sha256[:16]}… · config: {summary.config_hash[:12]}…")
        print(f"Vivos: {', '.join(summary.alive) or 'ninguno'}")
        if summary.deaths:
            print("Muertes: " + ", ".join(f"{aid} ({reason})" for aid, reason in summary.deaths.items()))
        if summary.births:
            print(f"Nacimientos: {summary.births} · generación máxima: {summary.max_generation}")
        if summary.llm_stats:
            st = summary.llm_stats
            print(f"LLM: {int(st['calls'])} llamadas, {int(st['cache_hits'])} desde caché, {int(st['fallbacks'])} recurrieron a reglas, "
                  f"{int(st['refusals'])} negativas · tokens {int(st['input_tokens']):,} entrada / {int(st['output_tokens']):,} salida "
                  f"· costo estimado ${summary.llm_cost_usd:.2f}")
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


def cmd_experiment(args: argparse.Namespace) -> int:
    import json as _json
    from datetime import datetime

    from vida.experiments import VARIANT_EXPERIMENTS, decision, transfer
    from vida.experiments.runner import effect_sizes, render_effects, render_summary, run_experiment

    cfg = load_config(args.config)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    out_dir = Path(args.out_dir)
    progress = (lambda msg: print(f"  · {msg}", flush=True)) if not args.quiet else None
    print(f"VIDA {__version__} · experimento {args.name} · semillas {seeds}")
    if args.name == "transfer":
        result = transfer.run_transfer_experiment(
            cfg, seeds=seeds, split_ticks=args.split, horizon_ticks=args.horizon, agent_id=args.agent,
            conditions=[c.strip() for c in args.conditions.split(",")] if args.conditions else None, progress=progress)
        metrics = transfer.KEY_METRICS
        target = out_dir / "transfer" / datetime.now().strftime("%Y%m%d_%H%M%S")
        target.mkdir(parents=True, exist_ok=True)
        (target / "results.json").write_text(_json.dumps(result["rows"], ensure_ascii=False, indent=1), encoding="utf-8")
        (target / "summary.json").write_text(_json.dumps(result["summary"], ensure_ascii=False, indent=1), encoding="utf-8")
        result["path"] = str(target)
        print(f"Corte en tick {args.split}, horizonte {args.horizon} ticks, agente {args.agent}. "
              "ICI = semejanza entre estados (1 = idéntico); no mide conciencia.")
    elif args.name == "decision":
        result = decision.run_decision_experiment(cfg, seeds=seeds, ticks=args.ticks, progress=progress)
        metrics = decision.KEY_METRICS
        target = out_dir / "decision" / datetime.now().strftime("%Y%m%d_%H%M%S")
        target.mkdir(parents=True, exist_ok=True)
        (target / "results.json").write_text(_json.dumps(result["rows"], ensure_ascii=False, indent=1), encoding="utf-8")
        (target / "summary.json").write_text(_json.dumps(result["summary"], ensure_ascii=False, indent=1), encoding="utf-8")
        result["path"] = str(target)
        print(f"Tras {args.ticks} ticks de vida, todos los agentes en la misma situación: con su historia y con la misma "
              "personalidad sin historia. share_changed = fracción cuya elección cambia al quitar la historia.")
    else:
        variants, metrics = VARIANT_EXPERIMENTS[args.name]
        result = run_experiment(args.name, cfg, variants, seeds=seeds, ticks=args.ticks, out_dir=out_dir, progress=progress)
    print()
    print(render_summary(result["summary"], metrics))
    if args.effects:
        a, _, b = args.effects.partition(":")
        eff = effect_sizes(result["rows"], a.strip(), b.strip())
        if eff:
            print()
            print(f"Tamaños de efecto {a} vs {b} (d de Cohen, |d| mayores):")
            print(render_effects(eff, a.strip(), b.strip()))
        else:
            print(f"No hay filas para comparar {a} y {b}", file=sys.stderr)
    print()
    print(f"Resultados: {result['path']}")
    return 0


def cmd_selfmodel(args: argparse.Namespace) -> int:
    from vida.evaluation.selfmodel_analysis import advantage_by_evidence, render_selfmodel_analysis

    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        meta = repo.run_meta(args.run)
        if meta is None:
            print(f"Corrida no encontrada: {args.run}", file=sys.stderr)
            return 1
        tpd = int(json.loads(meta["config_json"])["run"]["ticks_per_day"])
        events = repo.all_events(args.run)
    finally:
        repo.close()
    result = advantage_by_evidence(events, tpd, min_own_for_actions=args.min_own)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print(f"Corrida {args.run} · criterio 1: ¿la historia propia predice mejor que la población con el mismo contexto?")
        print(render_selfmodel_analysis(result))
    return 0


def cmd_lineage(args: argparse.Namespace) -> int:
    from vida.evaluation.lineage import lineage_report, render_lineage
    from vida.memory.base import AgentMemory
    from vida.simulation.config import RunConfig

    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        meta = repo.run_meta(args.run)
        if meta is None:
            print(f"Corrida no encontrada: {args.run}", file=sys.stderr)
            return 1
        cfg = RunConfig.model_validate(json.loads(meta["config_json"]))
        agents, memories = {}, {}
        for aid in repo.agents_meta(args.run):
            hist = repo.state_history(args.run, aid)
            if not hist:
                continue
            agents[aid] = hist[-1][1]
            mem = AgentMemory(aid, cfg.memory)
            for rec in repo.memories_for(args.run, aid):
                mem.records[rec.id] = rec
            memories[aid] = mem
        events = repo.all_events(args.run)
    finally:
        repo.close()
    report = lineage_report(agents, memories, events)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"Corrida {args.run} · linaje y transmisión cultural")
        print(render_lineage(report) if report["rows"] else "No hubo nacimientos en esta corrida.")
    return 0


def _load_final_states(repo: RunRepository, run_id: str) -> dict:
    agents = {}
    for aid in repo.agents_meta(run_id):
        hist = repo.state_history(run_id, aid)
        if hist:
            agents[aid] = hist[-1][1]
    return agents


def cmd_society(args: argparse.Namespace) -> int:
    from vida.evaluation.society import render_society, society_report

    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        if repo.run_meta(args.run) is None:
            print(f"Corrida no encontrada: {args.run}", file=sys.stderr)
            return 1
        agents = _load_final_states(repo, args.run)
        events = repo.all_events(args.run)
        history = {aid: repo.state_history(args.run, aid) for aid in repo.agents_meta(args.run)}
    finally:
        repo.close()
    from vida.evaluation.society import criterion3_over_time

    report = society_report(agents, events)
    report["criterion3_over_time"] = criterion3_over_time(history)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"Corrida {args.run} · análisis de sociedad y criterio 3")
        print(render_society(report))
        c3 = report["criterion3_over_time"]
        within = "—" if c3["corr_within_agent_mean"] is None else f"{c3['corr_within_agent_mean']:+.3f}"
        pooled = "—" if c3["corr_pooled"] is None else f"{c3['corr_pooled']:+.3f}"
        print(f"Criterio 3 en el tiempo · {c3['pairs']} pares (agente, día): r agrupada = {pooled} · r media dentro de cada agente = {within} "
              f"({c3['agents_with_positive_within']}/{c3['agents_measured']} agentes con r > 0)")
    return 0


def cmd_metacognition(args: argparse.Namespace) -> int:
    from vida.evaluation.metacognition import communicated_uncertainty, metacognition_report, render_metacognition

    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        if repo.run_meta(args.run) is None:
            print(f"Corrida no encontrada: {args.run}", file=sys.stderr)
            return 1
        events = repo.all_events(args.run)
    finally:
        repo.close()
    report = metacognition_report(events)
    comm = communicated_uncertainty(events)
    if args.json:
        print(json.dumps({"metacognition": report, "communicated_uncertainty": comm}, ensure_ascii=False, indent=1))
    else:
        print(f"Corrida {args.run} · metacognición e incertidumbre comunicada")
        print(render_metacognition(report, comm))
    return 0


def cmd_integration(args: argparse.Namespace) -> int:
    from vida.evaluation.integration import integration_report, render_integration

    db = _db_path(Path(args.data_dir), args.run)
    if not db.exists():
        print(f"No existe la corrida {args.run} en {db.parent}", file=sys.stderr)
        return 1
    repo = RunRepository(db)
    try:
        if repo.run_meta(args.run) is None:
            print(f"Corrida no encontrada: {args.run}", file=sys.stderr)
            return 1
        events = repo.all_events(args.run)
    finally:
        repo.close()
    report = integration_report(events, k=args.bins, n_features=args.features, n_shuffles=args.shuffles)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"Corrida {args.run} · integración informacional de la mente (criterio 6)")
        print(render_integration(report))
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
    run.add_argument("--engine", choices=["rules_v1", "llm_v1"], help="motor de decisión (sobrescribe la config)")
    run.add_argument("--llm-provider", choices=["anthropic", "ollama"], help="anthropic (API de Claude) u ollama (modelo local gratuito)")
    run.add_argument("--llm-model", help="modelo para llm_v1, p. ej. claude-opus-5, claude-haiku-4-5 o llama3.2")
    run.add_argument("--llm-agents", help="agentes que deciden con el LLM, separados por coma (los demás usan reglas)")
    run.set_defaults(func=cmd_run)

    life = sub.add_parser("life", help="reconstruir la biografía de un agente")
    life.add_argument("agent_id")
    life.add_argument("--run", required=True)
    life.add_argument("--json", action="store_true")
    life.set_defaults(func=cmd_life)

    runs = sub.add_parser("runs", help="listar corridas")
    runs.set_defaults(func=cmd_runs)

    exp = sub.add_parser("experiment", help="ejecutar un experimento (memory, environment, deception, transfer)")
    exp.add_argument("name", choices=["memory", "environment", "deception", "transfer", "decision"])
    exp.add_argument("--config", default="config/default.yaml")
    exp.add_argument("--seeds", default="1,2,3", help="semillas separadas por coma")
    exp.add_argument("--ticks", type=int, default=240, help="duración de cada corrida (experimentos de variantes)")
    exp.add_argument("--split", type=int, default=240, help="transfer: tick de corte")
    exp.add_argument("--horizon", type=int, default=120, help="transfer: ticks después del corte")
    exp.add_argument("--agent", default="a01", help="transfer: agente estudiado")
    exp.add_argument("--conditions", help="transfer: condiciones separadas por coma")
    exp.add_argument("--out-dir", default=str(Path("data") / "experiments"))
    exp.add_argument("--effects", help="comparar dos variantes con tamaños de efecto, p. ej. completa:ausente")
    exp.add_argument("--quiet", action="store_true")
    exp.set_defaults(func=cmd_experiment)

    sm = sub.add_parser("selfmodel", help="ventaja del automodelo por evidencia propia y por acción (criterio 1)")
    sm.add_argument("--run", required=True)
    sm.add_argument("--min-own", type=int, default=6, help="intentos propios mínimos para el desglose por acción")
    sm.add_argument("--json", action="store_true")
    sm.set_defaults(func=cmd_selfmodel)

    ln = sub.add_parser("lineage", help="semejanza hijo–progenitor frente a hijo–otros (transmisión cultural)")
    ln.add_argument("--run", required=True)
    ln.add_argument("--json", action="store_true")
    ln.set_defaults(func=cmd_lineage)

    so = sub.add_parser("society", help="análisis de sociedad: criterio 3, reputación, desigualdad, precios")
    so.add_argument("--run", required=True)
    so.add_argument("--json", action="store_true")
    so.set_defaults(func=cmd_society)

    mc = sub.add_parser("metacognition", help="criterio 4 (sabe cuándo sabe) y criterio 5 (incertidumbre comunicada)")
    mc.add_argument("--run", required=True)
    mc.add_argument("--json", action="store_true")
    mc.set_defaults(func=cmd_metacognition)

    ig = sub.add_parser("integration", help="criterio 6: información del todo vs. mejor partición de la mente (proxy de Φ)")
    ig.add_argument("--run", required=True)
    ig.add_argument("--bins", type=int, default=2, help="niveles por variable al discretizar")
    ig.add_argument("--features", type=int, default=1, help="variables por componente (1 o 2)")
    ig.add_argument("--shuffles", type=int, default=20, help="permutaciones para corregir el sesgo")
    ig.add_argument("--json", action="store_true")
    ig.set_defaults(func=cmd_integration)
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
