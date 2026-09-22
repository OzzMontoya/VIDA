"""Motor de simulación: reloj discreto y ciclo canónico por agente (sección 12).

Por cada agente y tick:
percepción → recuperación de memoria → decisión (propuesta) → resolución por el
mundo → aplicación del resultado → memoria → aprendizaje → relaciones y
reputación → registro del evento.

Al final de cada tick decaen las necesidades y avanza el ciclo de vida; al
final de cada día se consolida la memoria, se escribe el resumen
autobiográfico y se refresca la identidad.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vida import __version__
from vida.agents import identity, learning, social
from vida.agents.agent import AgentState
from vida.agents.decision import DecisionContext, DecisionEngine, build_engine
from vida.agents.selfmodel import PopulationModel, predict_success
from vida.database.repository import RunRepository
from vida.memory import autobiographical, episodic, procedural, reflective, semantic
from vida.memory import social as social_memory
from vida.memory.base import AgentMemory
from vida.simulation import lifecycle
from vida.simulation.clock import SimClock
from vida.simulation.config import RunConfig, canonical_json, config_hash
from vida.simulation.events import EventRecord, events_digest, make_event_id
from vida.simulation.logging import JsonlEventLogger
from vida.simulation.rng import RngHub
from vida.world.actions import ActionOutcome, InfoRequest
from vida.world.presets import build_world, spawn_agents
from vida.world.rules import PURCHASABLE
from vida.world.world import World


class RunSummary(BaseModel):
    run_id: str
    seed: int
    config_hash: str
    git_sha: str
    code_version: str
    ticks: int
    n_agents: int
    n_events: int
    events_sha256: str
    deaths: dict[str, str] = Field(default_factory=dict)
    alive: list[str] = Field(default_factory=list)
    decision_engine: str = "rules_v1"
    llm_stats: dict[str, float] | None = None
    llm_cost_usd: float | None = None


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def make_run_id(seed: int, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{seed}"


class SimulationEngine:
    def __init__(
        self, cfg: RunConfig, run_id: str, *, world: World | None = None,
        agents: dict[str, AgentState] | None = None, decision_engine: DecisionEngine | None = None,
        repo: RunRepository | None = None, logger: JsonlEventLogger | None = None,
        sha: str | None = None,
    ) -> None:
        self.cfg = cfg
        self.run_id = run_id
        self.hub = RngHub(cfg.run.seed)
        self.world = world or build_world(cfg)
        self.agents = agents if agents is not None else spawn_agents(cfg, self.world, self.hub.sub("spawn"))
        self.decision_engine = decision_engine or build_engine(cfg.decision)
        self.repo = repo
        self.logger = logger
        self.sha = sha or git_sha()
        self.clock = SimClock(ticks_per_day=cfg.run.ticks_per_day)
        self.memories = {aid: AgentMemory(aid, cfg.memory) for aid in sorted(self.agents)}
        self.names = {aid: a.name for aid, a in self.agents.items()}
        self.events: list[EventRecord] = []
        self.deaths: dict[str, str] = {}
        self._seq = 0
        self._day_outcomes: dict[str, list[ActionOutcome]] = {aid: [] for aid in self.agents}
        self._observed_today: set[tuple[str, str, int]] = set()
        self._location_info = self.world.public_location_info()
        self.population_model = PopulationModel()
        self._prices = {r: self.world.price(r) for r in sorted(PURCHASABLE | {"care"})}

    # --- utilidades --------------------------------------------------------
    def _next_event(self, event_type: str, agent_id: str, **fields: Any) -> EventRecord:
        self._seq += 1
        return EventRecord(
            event_id=make_event_id(self.clock.tick, agent_id, self._seq), run_id=self.run_id, seq=self._seq,
            tick=self.clock.tick, day=self.clock.day, hour=self.clock.hour, event_type=event_type,
            agent_id=agent_id, **fields,
        )

    def _emit(self, event: EventRecord) -> None:
        self.events.append(event)
        if self.logger is not None:
            self.logger.write(event)
        if self.repo is not None:
            self.repo.save_event(event)

    def alive_ids(self) -> list[str]:
        return sorted(aid for aid, a in self.agents.items() if a.alive)

    def _context_for(self, agent: AgentState, retrieve: bool = True) -> DecisionContext:
        tick = self.clock.tick
        perception = self.world.perceive(agent, self.agents, tick)
        legal = self.world.legal_actions(agent, perception)
        memory = self.memories[agent.id]
        memories = []
        if retrieve:
            ctx_tags = {f"loc:{perception.location_id}"} | {f"agent:{o}" for o in perception.visible_agents}
            ctx_tags |= {f"action:{k}" for k in legal}
            memories = memory.retrieve(ctx_tags, tick)
        return DecisionContext(
            agent=agent, perception=perception, memories=memories, memory=memory, available_actions=legal,
            location_info=self._location_info, prices=self._prices, distance=self.world.distance,
            tick=tick, ticks_per_day=self.cfg.run.ticks_per_day,
        )

    # --- ciclo por agente --------------------------------------------------
    def _agent_turn(self, agent: AgentState) -> EventRecord:
        tick = self.clock.tick
        memory = self.memories[agent.id]
        ctx = self._context_for(agent)
        perception = ctx.perception

        # Percepción directa: creencias y hechos semánticos sobre lo observado (una vez por lugar y día).
        learning.observe(agent, perception.location_id, perception.visible_resources, perception.visible_agents, tick)
        loc = self.world.locations[perception.location_id]
        key = (agent.id, perception.location_id, self.clock.day)
        if loc.restock and key not in self._observed_today:
            self._observed_today.add(key)
            for resource in sorted(PURCHASABLE):
                if resource in loc.restock:
                    semantic.record_availability(memory, resource, loc.id, loc.stock(resource) > 0, tick)

        state_before = agent.summary()
        proposal, decision = self.decision_engine.decide(ctx, self.hub.sub("decision", agent.id))

        # Petición de información: el otro agente decide su respuesta en este mismo tick.
        if proposal.kind == "ask_info" and proposal.target_agent in self.agents and proposal.resource:
            responder = self.agents[proposal.target_agent]
            request = InfoRequest(asker_id=agent.id, responder_id=responder.id, resource=proposal.resource, tick=tick)
            reply = self.decision_engine.decide_reply(
                self._context_for(responder, retrieve=False), request, self.hub.sub("decision", responder.id))
            proposal.payload["reply"] = reply.model_dump()
            responder.bump_counter(f"reply:{reply.kind}")
        if proposal.kind == "share_info" and "truthful" in proposal.payload:
            agent.bump_counter("share:truth" if proposal.payload["truthful"] else "share:lie")

        # Automodelo: el agente predice su propio éxito antes de actuar; el mundo decide después.
        pred_tags = {f"action:{proposal.kind}"} | ({f"res:{proposal.resource}"} if proposal.resource else set()) \
            | ({f"agent:{proposal.target_agent}"} if proposal.target_agent else set())
        predicted = predict_success(memory, pred_tags)
        baseline = self.population_model.rate(proposal.kind)

        event = self._next_event("action", agent.id, perception=perception, state_before=state_before,
                                 retrieved_memory_ids=[m.id for m in ctx.memories], decision=decision, proposal=proposal)
        outcome = self.world.resolve(agent, proposal, self.agents, self.hub.sub("world"), tick, event.event_id)
        agent.apply_outcome(outcome)
        own_err, base_err = agent.self_model.record(predicted, baseline, outcome.success, window=self.cfg.run.ticks_per_day)
        self.population_model.update(proposal.kind, outcome.success)
        event.prediction = {"p_success": predicted, "baseline": baseline, "actual": 1.0 if outcome.success else 0.0,
                            "error": round(own_err, 6), "baseline_error": round(base_err, 6)}
        for other_id, deltas in sorted(outcome.other_need_deltas.items()):
            if other_id in self.agents:
                self.agents[other_id].apply_need_deltas(deltas)

        # Memoria.
        created: list[str] = []
        rec = episodic.encode_outcome(memory, agent, outcome, event.event_id, self.names)
        if rec:
            created.append(rec.id)
        rec = social_memory.encode_for_initiator(memory, outcome, event.event_id, self.names)
        if rec:
            created.append(rec.id)
        if outcome.target_agent in self.memories and outcome.action in social_memory.SOCIAL_ACTIONS:
            social_memory.encode_for_partner(self.memories[outcome.target_agent], outcome, agent.name, event.event_id)
        if outcome.action == "acquire" and outcome.resource and outcome.kind in {"ok", "resource_absent"}:
            rec = semantic.record_availability(memory, outcome.resource, outcome.location_id, outcome.success, tick, event.event_id)
            created.append(rec.id)

        # Aprendizaje, relaciones, reputación.
        pref_deltas, belief_changes = learning.learn(agent, outcome, event.event_id)
        skill, gain = outcome.details.get("skill"), outcome.details.get("skill_gain")
        if skill and gain:
            rec = procedural.encode_skill_gain(memory, agent, skill, float(gain), tick, event.event_id)
            if rec:
                created.append(rec.id)
        if outcome.action == "share_info" and outcome.success and outcome.target_agent in self.agents:
            belief_changes += learning.receive_shared_info(self.agents[outcome.target_agent], outcome, event.event_id)
        rel_deltas = social.update_relationships(agent, outcome, self.agents)
        rep_deltas = self.world.update_reputation(agent, outcome, self.agents)

        agent.decision_history.append(event.event_id)
        self._day_outcomes[agent.id].append(outcome)
        event.outcome = outcome
        event.memories_created = created
        event.relationship_deltas = rel_deltas
        event.reputation_deltas = rep_deltas
        event.preference_deltas = pref_deltas
        event.belief_changes = belief_changes
        event.state_after = agent.summary()
        event.world_delta = outcome.world_delta
        self._emit(event)
        return event

    # --- fin de tick / día -------------------------------------------------
    def _end_of_tick(self) -> None:
        tick = self.clock.tick
        for aid in self.alive_ids():
            agent = self.agents[aid]
            agent.decay_needs(lifecycle.health_decay_factor(agent, self.cfg))
            update = lifecycle.advance(agent, self.cfg, self.cfg.run.ticks_per_day)
            if update.stage_change:
                self._emit(self._next_event("stage_change", aid, state_after=agent.summary(), note=update.stage_change))
            if update.death_reason:
                self._on_death(agent, update.death_reason)
        if self.clock.hour == self.cfg.run.ticks_per_day - 1:
            self._end_of_day()
        if self.repo is not None and (tick + 1) % self.cfg.run.snapshot_every_ticks == 0:
            self.repo.snapshot_states(self.run_id, tick + 1, self.agents)

    def _on_death(self, agent: AgentState, reason: str) -> None:
        tick = self.clock.tick
        self.deaths[agent.id] = reason
        self.world.remove_agent(agent.id)
        event = self._next_event("death", agent.id, state_after=agent.summary(), note=reason)
        for other_id in self.alive_ids():
            other = self.agents[other_id]
            rel = other.relationships.get(agent.id)
            if rel is not None and rel.familiarity > 0.3:
                social_memory.encode_death_of(self.memories[other_id], agent.name, agent.id, tick, event.event_id)
        if self.repo is not None:
            self.repo.record_death(self.run_id, agent.id, tick, reason)
        self._emit(event)

    def _end_of_day(self) -> None:
        tick, day = self.clock.tick, self.clock.day
        for aid in sorted(self.agents):
            agent = self.agents[aid]
            memory = self.memories[aid]
            autobiographical.daily_summary(memory, agent, day, tick, self._day_outcomes[aid], self.names)
            self._day_outcomes[aid] = []
            if agent.alive:
                reflective.reflect(memory, agent, tick, self.cfg.run.ticks_per_day)
            before = set(memory.records)
            memory.consolidate(tick, self.cfg.run.ticks_per_day)
            # Las creencias dependen de la memoria: olvidar un hecho semántico debilita la creencia asociada.
            for rec in memory.forgotten:
                if rec.id in before and rec.kind == "semantic":
                    res = next((t[4:] for t in rec.tags if t.startswith("res:")), None)
                    loc = next((t[4:] for t in rec.tags if t.startswith("loc:")), None)
                    if res and loc:
                        agent.beliefs.refute(res, loc)
            if agent.alive:
                identity.refresh(agent)
        self._observed_today.clear()

    # --- API pública -------------------------------------------------------
    def step(self) -> list[EventRecord]:
        start = len(self.events)
        for delta in self.world.apply_scheduled_events(self.clock.tick):
            self._emit(self._next_event("world_event", "world", world_delta=delta, note=delta["kind"]))
        order = self.alive_ids()
        self.hub.sub("turn_order").shuffle(order)
        for aid in order:
            agent = self.agents[aid]
            if agent.alive:
                self._agent_turn(agent)
        self._end_of_tick()
        self.clock.advance()
        return self.events[start:]

    def run(self, ticks: int | None = None) -> RunSummary:
        ticks = self.cfg.run.ticks if ticks is None else ticks
        if self.repo is not None:
            self.repo.create_run(self.run_id, seed=self.cfg.run.seed, config_hash=config_hash(self.cfg),
                                 config_json=canonical_json(self.cfg), git_sha=self.sha, code_version=__version__)
            self.repo.save_agents(self.run_id, self.agents)
            self.repo.snapshot_states(self.run_id, 0, self.agents)
        for _ in range(ticks):
            self.step()
        summary = RunSummary(
            run_id=self.run_id, seed=self.cfg.run.seed, config_hash=config_hash(self.cfg), git_sha=self.sha,
            code_version=__version__, ticks=ticks, n_agents=len(self.agents), n_events=len(self.events),
            events_sha256=events_digest(self.events), deaths=dict(sorted(self.deaths.items())), alive=self.alive_ids(),
            decision_engine=getattr(self.decision_engine, "name", "unknown"),
            llm_stats=dict(getattr(self.decision_engine, "stats", {})) or None,
            llm_cost_usd=self.decision_engine.estimated_cost_usd() if hasattr(self.decision_engine, "estimated_cost_usd") else None,
        )
        if self.repo is not None:
            for aid, memory in sorted(self.memories.items()):
                self.repo.save_memories(self.run_id, aid, memory.all(), memory.forgotten)
            if self.clock.tick % self.cfg.run.snapshot_every_ticks != 0:
                self.repo.snapshot_states(self.run_id, self.clock.tick, self.agents)
            self.repo.finish_run(self.run_id, n_ticks=ticks, n_events=len(self.events),
                                 events_sha256=summary.events_sha256, summary=summary.model_dump(mode="json"))
        if self.logger is not None:
            self.logger.close()
        return summary
