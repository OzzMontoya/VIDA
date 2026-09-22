"""Carga de una corrida VIDA (SQLite) en DataFrames para el dashboard.

Todo se lee de ``data/runs/<run_id>/vida.sqlite``: metadatos, agentes, eventos
(JSON completo por evento), memorias, snapshots de relaciones y estados. La
carga se cachea por ruta y fecha de modificación del archivo.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from vida.agents.agent import AgentState
from vida.simulation.config import RunConfig
from vida.world.presets import PRESETS

# Agrupación de las 11 acciones en 8 familias (límite de la paleta categórica).
ACTION_GROUPS: dict[str, str] = {
    "rest": "descanso", "idle": "descanso", "work": "trabajo", "acquire": "compra", "consume": "comida",
    "socialize": "conversación", "move": "desplazamiento", "ask_info": "información", "share_info": "información",
    "study": "estudio/salud", "seek_care": "estudio/salud",
}
ACTION_GROUP_ORDER = ["descanso", "trabajo", "compra", "comida", "conversación", "desplazamiento", "información", "estudio/salud"]
NEED_ORDER = ["hunger", "energy", "health", "social", "safety", "knowledge"]
NEED_LABELS = {"hunger": "hambre", "energy": "energía", "health": "salud", "social": "social", "safety": "seguridad", "knowledge": "conocimiento"}
LOCATION_TYPE_LABELS = {"home": "casa", "plaza": "plaza", "market": "mercado", "school": "escuela", "hospital": "hospital", "workplace": "trabajo"}
MEMORY_KIND_LABELS = {"episodic": "episódica", "semantic": "semántica", "social": "social", "autobiographical": "autobiográfica", "procedural": "procedimental", "reflective": "reflexiva"}


@dataclass
class RunData:
    run_id: str
    meta: dict[str, Any]
    config: RunConfig
    agents: pd.DataFrame            # agent_id, name, home_id, death_tick, death_reason
    events: pd.DataFrame            # una fila por evento con columnas planas
    memories: pd.DataFrame
    relationships: pd.DataFrame     # snapshots: tick, from_id, to_id, trust, affection, familiarity
    final_states: dict[str, AgentState]
    initial_states: dict[str, AgentState]
    resources: pd.DataFrame         # tick, location_id, resource, stock
    location_types: dict[str, str]
    names: dict[str, str] = field(default_factory=dict)

    @property
    def ticks_per_day(self) -> int:
        return self.config.run.ticks_per_day

    @property
    def n_days(self) -> int:
        return int(self.meta.get("n_ticks") or 0) // self.ticks_per_day


def list_runs(data_dir: Path) -> list[tuple[str, Path]]:
    if not data_dir.exists():
        return []
    runs = [(p.name, p / "vida.sqlite") for p in data_dir.iterdir() if (p / "vida.sqlite").exists()]
    return sorted(runs, key=lambda r: r[1].stat().st_mtime, reverse=True)


def _flatten_event(payload: dict[str, Any]) -> dict[str, Any]:
    outcome = payload.get("outcome") or {}
    after = payload.get("state_after") or {}
    proposal = payload.get("proposal") or {}
    details = outcome.get("details") or {}
    world_info = details.get("_world") or {}
    row: dict[str, Any] = {
        "seq": payload["seq"], "tick": payload["tick"], "day": payload["day"], "hour": payload["hour"],
        "agent_id": payload["agent_id"], "event_type": payload["event_type"], "note": payload.get("note", ""),
        "action": outcome.get("action") or proposal.get("kind"),
        "outcome_kind": outcome.get("kind"), "success": outcome.get("success"),
        "valence": outcome.get("valence"), "location": outcome.get("location_id") or after.get("location_id"),
        "new_location": outcome.get("new_location"), "target_agent": outcome.get("target_agent") or proposal.get("target_agent"),
        "resource": outcome.get("resource") or proposal.get("resource"),
        "money_delta": outcome.get("money_delta", 0.0), "money": after.get("money"),
        "reputation": after.get("reputation"), "emotion": after.get("emotion_valence"),
        "life_stage": after.get("life_stage"),
        "decision_key": (payload.get("decision") or {}).get("chosen"),
        "n_candidates": (payload.get("decision") or {}).get("n_candidates"),
        "reply_intent": world_info.get("intent"),
        "share_truthful": world_info.get("intent_truthful"),
        "was_true": world_info.get("was_true"),
        "attributed_source": details.get("attributed_source_agent"),
        "n_relationship_deltas": len(payload.get("relationship_deltas") or {}),
        "n_preference_deltas": len(payload.get("preference_deltas") or {}),
        "n_belief_changes": len(payload.get("belief_changes") or []),
        "memories_created": len(payload.get("memories_created") or []),
        "world_delta": payload.get("world_delta") or {},
    }
    for need in NEED_ORDER:
        row[f"need_{need}"] = (after.get("needs") or {}).get(need)
    return row


def _preset_world(cfg: RunConfig):
    try:
        return PRESETS[cfg.world.preset](cfg)
    except KeyError as exc:
        raise ValueError(
            f"Preset de mundo '{cfg.world.preset}' desconocido en esta versión del código. "
            "Si acabas de añadirlo, reinicia el servidor de Streamlit (no recarga los módulos importados)."
        ) from exc


def _resource_timeline(cfg: RunConfig, events: list[dict[str, Any]]) -> pd.DataFrame:
    world = _preset_world(cfg)
    stock: dict[tuple[str, str], int] = {}
    rows: list[dict[str, Any]] = []
    for loc in world.locations.values():
        for res, amount in loc.resources.items():
            stock[(loc.id, res)] = amount
            rows.append({"tick": 0, "location_id": loc.id, "resource": res, "stock": amount})
    for ev in events:
        delta = ev.get("world_delta") or {}
        tick = ev["tick"]
        if ev["event_type"] == "world_event":
            loc_id = delta.get("location_id")
            kind = delta.get("kind")
            if kind == "restock":
                for res, change in delta.get("changes", {}).items():
                    stock[(loc_id, res)] = stock.get((loc_id, res), 0) + int(change)
                    rows.append({"tick": tick, "location_id": loc_id, "resource": res, "stock": stock[(loc_id, res)]})
            elif kind == "shortage":
                for res, amount in delta.get("set", {}).items():
                    stock[(loc_id, res)] = int(amount)
                    rows.append({"tick": tick, "location_id": loc_id, "resource": res, "stock": int(amount)})
            elif kind == "bonus":
                for res, amount in delta.get("added", {}).items():
                    stock[(loc_id, res)] = stock.get((loc_id, res), 0) + int(amount)
                    rows.append({"tick": tick, "location_id": loc_id, "resource": res, "stock": stock[(loc_id, res)]})
        else:
            for loc_id, resources in (delta.get("resources") or {}).items():
                for res, amount in resources.items():
                    stock[(loc_id, res)] = int(amount)
                    rows.append({"tick": tick, "location_id": loc_id, "resource": res, "stock": int(amount)})
    return pd.DataFrame(rows)


def load_run(db_path: Path) -> RunData:
    con = sqlite3.connect(str(db_path))
    try:
        runs = pd.read_sql("SELECT * FROM runs", con)
        if runs.empty:
            raise ValueError(f"La base {db_path} no contiene corridas")
        meta = runs.iloc[0].to_dict()
        run_id = meta["run_id"]
        cfg = RunConfig.model_validate(json.loads(meta["config_json"]))
        agents = pd.read_sql("SELECT agent_id, name, home_id, initial_age_ticks, death_tick, death_reason FROM agents WHERE run_id = ? ORDER BY agent_id", con, params=(run_id,))
        raw_events = pd.read_sql("SELECT payload_json FROM events WHERE run_id = ? ORDER BY seq", con, params=(run_id,))
        payloads = [json.loads(s) for s in raw_events["payload_json"]]
        events = pd.DataFrame([_flatten_event(p) for p in payloads])
        memories = pd.read_sql("SELECT memory_id, agent_id, kind, tick, content, importance, valence, forgotten, payload_json FROM memories WHERE run_id = ? ORDER BY memory_id", con, params=(run_id,))
        if not memories.empty:
            memories["tags"] = memories["payload_json"].map(lambda s: ", ".join(json.loads(s).get("tags", [])))
            memories["access_count"] = memories["payload_json"].map(lambda s: json.loads(s).get("access_count", 0))
            memories = memories.drop(columns=["payload_json"])
            memories["forgotten"] = memories["forgotten"].astype(bool)
        relationships = pd.read_sql("SELECT tick, from_id, to_id, trust, affection, familiarity FROM relationships WHERE run_id = ? ORDER BY tick, from_id, to_id", con, params=(run_id,))
        history = pd.read_sql("SELECT agent_id, tick, state_json FROM agent_state_history WHERE run_id = ? ORDER BY agent_id, tick, id", con, params=(run_id,))
    finally:
        con.close()

    final_states: dict[str, AgentState] = {}
    initial_states: dict[str, AgentState] = {}
    for aid, group in history.groupby("agent_id"):
        initial_states[aid] = AgentState.model_validate_json(group.iloc[0]["state_json"])
        final_states[aid] = AgentState.model_validate_json(group.iloc[-1]["state_json"])

    world = _preset_world(cfg)
    location_types = {loc.id: loc.type for loc in world.locations.values()}
    if not events.empty:
        events["action_group"] = events["action"].map(ACTION_GROUPS)
        events["location_type"] = events["location"].map(location_types)
        events["day_label"] = events["day"].map(lambda d: f"día {d}")
    names = dict(zip(agents["agent_id"], agents["name"]))
    return RunData(
        run_id=run_id, meta=meta, config=cfg, agents=agents, events=events, memories=memories,
        relationships=relationships, final_states=final_states, initial_states=initial_states,
        resources=_resource_timeline(cfg, payloads), location_types=location_types, names=names,
    )


def alive_per_tick(data: RunData) -> pd.DataFrame:
    """Número de agentes vivos al inicio de cada tick."""
    n_ticks = int(data.meta.get("n_ticks") or data.events["tick"].max() + 1)
    deaths = data.agents.dropna(subset=["death_tick"])
    ticks = pd.Series(range(n_ticks + 1), name="tick")
    alive = [len(data.agents) - int((deaths["death_tick"] < t).sum()) for t in ticks]
    return pd.DataFrame({"tick": ticks, "day": ticks / data.ticks_per_day, "vivos": alive})


def occupancy_by_type(data: RunData) -> pd.DataFrame:
    """Agentes por tipo de lugar, promediados por día (la suma es la población viva)."""
    ev = data.events[data.events["event_type"] == "action"].copy()
    ev["where"] = ev["new_location"].fillna(ev["location"])
    ev["where_type"] = ev["where"].map(data.location_types).map(LOCATION_TYPE_LABELS)
    per_tick = ev.groupby(["tick", "where_type"]).size().unstack(fill_value=0)
    per_tick["day"] = per_tick.index // data.ticks_per_day
    occ = per_tick.groupby("day").mean()
    occ.index = occ.index + 0.5
    return occ


def deception_summary(data: RunData) -> pd.DataFrame:
    """Intención registrada por el mundo en respuestas e información compartida, por agente."""
    ev = data.events
    asks = ev[(ev["action"] == "ask_info") & ev["reply_intent"].notna()]
    rows = []
    for _, r in asks.iterrows():
        rows.append({"agent_id": r["target_agent"], "intent": r["reply_intent"]})
    shares = ev[(ev["action"] == "share_info") & ev["share_truthful"].notna()]
    for _, r in shares.iterrows():
        rows.append({"agent_id": r["agent_id"], "intent": "truth" if r["share_truthful"] else "lie"})
    if not rows:
        return pd.DataFrame(columns=["agent_id", "intent", "n"])
    df = pd.DataFrame(rows)
    return df.groupby(["agent_id", "intent"]).size().reset_index(name="n")
