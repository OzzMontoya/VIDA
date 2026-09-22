"""Reglas causales del mundo: legalidad y resolución de cada acción.

Cada resolvedor recibe la propuesta del agente y devuelve un ``ActionOutcome``
con la consecuencia objetiva. Aquí se muta el estado del mundo (stock,
posiciones, libro de información). Reglas de diseño:

- Nunca se lee ``proposal.rationale``.
- La información que sólo el mundo conoce (si una respuesta fue mentira, si
  una afirmación era cierta) va bajo ``details["_world"]``. Los módulos del
  agente (aprendizaje, relaciones) no deben leer esa clave.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from vida.agents.agent import WORKING_STAGES, AgentState
from vida.world.actions import ActionKind, ActionOutcome, ActionProposal, InfoReply, PerceptionSnapshot

if TYPE_CHECKING:
    from vida.world.world import World

FOOD_EFFECTS: dict[str, dict[str, float]] = {
    "bread": {"hunger": 0.40, "health": 0.02},
    "fruit": {"hunger": 0.25, "health": 0.04},
}
PURCHASABLE: frozenset[str] = frozenset(FOOD_EFFECTS)
MOVE_ENERGY_PER_STEP = 0.02
REST_ENERGY = 0.15
REST_HOME_BONUS = 0.15
WORK_ENERGY = -0.08
WORK_HUNGER = -0.02
WORK_SKILL_GAIN = 0.02
STUDY_KNOWLEDGE = 0.20
STUDY_SKILL_GAIN = 0.03
STUDY_ENERGY = -0.03
CARE_HEALTH = 0.30
SOCIAL_GAIN = 0.25
SOCIAL_BASE_ACCEPT = 0.15
SOCIAL_TRUST_WEIGHT = 0.45
SOCIAL_REPUTATION_WEIGHT = 0.25
SOCIAL_AFFINITY_WEIGHT = 0.15
WORK_BASE_SUCCESS = 0.35  # p_éxito = base + 0.5·habilidad + 0.15·energía: quién eres cambia cómo te va
STUDY_BASE_SUCCESS = 0.40


@dataclass
class ResolveContext:
    agents: dict[str, AgentState]
    tick: int
    hour: int
    event_id: str
    rng: random.Random


# --- legalidad ------------------------------------------------------------

def legal_actions(world: "World", agent: AgentState, perception: PerceptionSnapshot) -> list[ActionKind]:
    loc = world.locations[perception.location_id]
    kinds: list[ActionKind] = ["idle", "rest"]
    if len(agent.beliefs.known_locations) > 1:
        kinds.append("move")
    if perception.is_open and any(
        stock > 0 for r, stock in perception.visible_resources.items() if r in PURCHASABLE
    ):
        kinds.append("acquire")
    if any(agent.inventory.get(food, 0) > 0 for food in FOOD_EFFECTS):
        kinds.append("consume")
    if loc.type == "workplace" and perception.is_open and agent.life_stage in WORKING_STAGES:
        kinds.append("work")
    if loc.type == "school" and perception.is_open:
        kinds.append("study")
    if loc.type == "hospital" and perception.is_open and loc.stock("care") > 0:
        kinds.append("seek_care")
    if perception.visible_agents:
        kinds.extend(["socialize", "ask_info"])
        if agent.beliefs.resources:
            kinds.append("share_info")
    return kinds


# --- resolución -----------------------------------------------------------

def resolve(world: "World", agent: AgentState, proposal: ActionProposal, ctx: ResolveContext) -> ActionOutcome:
    perception = world.perceive(agent, ctx.agents, ctx.tick)
    base = dict(tick=ctx.tick, agent_id=agent.id, action=proposal.kind, location_id=perception.location_id)
    if proposal.kind not in legal_actions(world, agent, perception):
        return ActionOutcome(**base, kind="illegal", success=False, valence=-0.2,
                             details={"reason": "action not legal here"})
    resolver = _RESOLVERS[proposal.kind]
    return resolver(world, agent, proposal, ctx, perception, base)


def _illegal(base: dict[str, Any], reason: str, **extra: Any) -> ActionOutcome:
    return ActionOutcome(**base, kind="illegal", success=False, valence=-0.2, details={"reason": reason}, **extra)


def _move(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    target = proposal.target_location
    if target is None or target not in world.locations or target not in agent.beliefs.known_locations:
        return _illegal(base, "unknown location")
    loc = world.locations[target]
    if loc.type == "home" and target != agent.home_id:
        return _illegal(base, "private home", target_agent=None)
    if target == perception.location_id:
        return ActionOutcome(**base, kind="ok", success=True, new_location=target, valence=0.0,
                             details={"distance": 0})
    if loc.capacity is not None and len(world.agents_at(target)) >= loc.capacity:
        return ActionOutcome(**base, kind="blocked", success=False, valence=-0.3,
                             details={"distance": world.distance(perception.location_id, target)})
    dist = world.distance(perception.location_id, target)
    world.state.agent_locations[agent.id] = target
    return ActionOutcome(
        **base, kind="ok", success=True, new_location=target,
        need_deltas={"energy": round(-MOVE_ENERGY_PER_STEP * dist, 6)}, valence=0.05,
        details={"distance": dist, "arrived_open": loc.is_open(ctx.hour)},
        world_delta={"agent_locations": {agent.id: target}},
    )


def _acquire(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    resource = proposal.resource
    loc = world.locations[perception.location_id]
    if resource is None or resource not in PURCHASABLE:
        return _illegal(base, "resource not purchasable")
    details: dict[str, Any] = {}
    belief = agent.beliefs.belief_at(resource, loc.id)
    if belief is not None and belief.source == "told" and belief.source_agent:
        details["attributed_source_agent"] = belief.source_agent
        details["attributed_source_event_id"] = belief.source_event_id
        ledger = world.state.info_ledger.get(belief.source_event_id or "", {})
        details["_world"] = {"attributed_lie": bool(ledger.get("deceptive", False))}
    if loc.stock(resource) <= 0:
        return ActionOutcome(**base, kind="resource_absent", success=False, resource=resource,
                             valence=-0.7, details=details)
    price = world.price(resource, loc.id)
    if agent.money < price:
        return ActionOutcome(**base, kind="insufficient_funds", success=False, resource=resource,
                             valence=-0.4, details={**details, "price": price})
    loc.take(resource, 1)
    held_food = sum(agent.inventory.get(f, 0) for f in FOOD_EFFECTS)
    valence = 0.5 if held_food == 0 else 0.15  # comprar con reservas satisface poco
    return ActionOutcome(
        **base, kind="ok", success=True, resource=resource,
        inventory_deltas={resource: 1}, money_delta=-price, valence=valence,
        details={**details, "price": price, "held_before": held_food},
        world_delta={"resources": {loc.id: {resource: loc.stock(resource)}}},
    )


def _consume(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    resource = proposal.resource
    if resource not in FOOD_EFFECTS or agent.inventory.get(resource, 0) <= 0:
        return _illegal(base, "nothing to consume")
    return ActionOutcome(
        **base, kind="ok", success=True, resource=resource,
        need_deltas=dict(FOOD_EFFECTS[resource]), inventory_deltas={resource: -1}, valence=0.4,
    )


def _work(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    skill = agent.knowledge_level("job")
    energy = agent.needs["energy"].level
    performance = round((0.5 + 0.5 * skill) * (0.5 + 0.5 * energy), 6)
    loc = world.locations[perception.location_id]
    energy_cost = WORK_ENERGY if loc.work_energy is None else -abs(loc.work_energy)
    p_success = min(1.0, WORK_BASE_SUCCESS + 0.5 * skill + 0.15 * energy)
    if ctx.rng.random() >= p_success:
        # Jornada malograda: depende de la habilidad y la energía del individuo, no del mundo.
        earned = round(world.wage(loc.id) * performance * 0.3, 6)
        return ActionOutcome(
            **base, kind="poor_performance", success=False, money_delta=earned,
            need_deltas={"energy": energy_cost, "hunger": WORK_HUNGER}, valence=-0.2,
            details={"performance": performance, "p_success": round(p_success, 6), "skill_gain": WORK_SKILL_GAIN / 2, "skill": "job"},
        )
    earned = round(world.wage(loc.id) * performance, 6)
    return ActionOutcome(
        **base, kind="ok", success=True, money_delta=earned,
        need_deltas={"energy": energy_cost, "hunger": WORK_HUNGER, "safety": 0.02}, valence=0.3,
        details={"performance": performance, "p_success": round(p_success, 6), "skill_gain": WORK_SKILL_GAIN, "skill": "job"},
    )


def _rest(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    at_home = perception.location_id == agent.home_id
    gain = REST_ENERGY + (REST_HOME_BONUS if at_home else 0.0)
    deltas = {"energy": gain}
    if at_home:
        deltas["safety"] = 0.05
    return ActionOutcome(**base, kind="ok", success=True, need_deltas=deltas, valence=0.1,
                         details={"at_home": at_home})


def _socialize(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    other_id = proposal.target_agent
    if other_id not in perception.visible_agents:
        return _illegal(base, "target not present")
    other = ctx.agents[other_id]
    trust_in_agent = other.relationship_with(agent.id).trust
    affinity = 1.0 - abs(agent.personality.agreeableness - other.personality.agreeableness) * 0.5 \
        - abs(agent.personality.extraversion - other.personality.extraversion) * 0.5
    p_accept = (SOCIAL_BASE_ACCEPT + SOCIAL_TRUST_WEIGHT * trust_in_agent
                + SOCIAL_REPUTATION_WEIGHT * agent.reputation + SOCIAL_AFFINITY_WEIGHT * affinity)
    accepted = ctx.rng.random() < p_accept
    if not accepted:
        return ActionOutcome(**base, kind="rejected", success=False, target_agent=other_id,
                             valence=-0.4, details={"accepted": False, "p_accept": round(p_accept, 6)})
    return ActionOutcome(
        **base, kind="ok", success=True, target_agent=other_id,
        need_deltas={"social": SOCIAL_GAIN}, other_need_deltas={other_id: {"social": SOCIAL_GAIN}},
        valence=0.5, details={"accepted": True, "p_accept": round(p_accept, 6)},
    )


def _ask_info(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    other_id = proposal.target_agent
    resource = proposal.resource
    if other_id not in perception.visible_agents or not resource:
        return _illegal(base, "target not present or no resource")
    raw = proposal.payload.get("reply")
    reply = InfoReply.model_validate(raw) if raw else None
    if reply is None or reply.kind == "omit" or reply.claimed_location is None:
        world.state.info_ledger[ctx.event_id] = {
            "kind": "ask_info", "by": other_id, "to": agent.id, "resource": resource,
            "intent": reply.kind if reply else "none", "deceptive": False, "was_true": None,
        }
        return ActionOutcome(**base, kind="no_reply", success=False, target_agent=other_id, resource=resource,
                             need_deltas={"social": 0.05}, valence=-0.3,
                             details={"responded": False})
    was_true = reply.claimed_location in world.truth_locations(resource)
    world.state.info_ledger[ctx.event_id] = {
        "kind": "ask_info", "by": other_id, "to": agent.id, "resource": resource,
        "intent": reply.kind, "deceptive": reply.kind == "lie", "was_true": was_true,
    }
    return ActionOutcome(
        **base, kind="ok", success=True, target_agent=other_id, resource=resource,
        need_deltas={"social": 0.10}, other_need_deltas={other_id: {"social": 0.05}}, valence=0.2,
        details={
            "responded": True, "claimed_location": reply.claimed_location,
            "claimed_confidence": reply.claimed_confidence, "informant": other_id,
            "_world": {"intent": reply.kind, "was_true": was_true},
        },
    )


def _share_info(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    other_id = proposal.target_agent
    resource = proposal.resource
    claimed = proposal.payload.get("claimed_location")
    truthful = bool(proposal.payload.get("truthful", True))
    if other_id not in perception.visible_agents or not resource or not claimed:
        return _illegal(base, "target not present or nothing to share")
    was_true = claimed in world.truth_locations(resource)
    world.state.info_ledger[ctx.event_id] = {
        "kind": "share_info", "by": agent.id, "to": other_id, "resource": resource,
        "intent": "truth" if truthful else "lie", "deceptive": not truthful, "was_true": was_true,
    }
    return ActionOutcome(
        **base, kind="ok", success=True, target_agent=other_id, resource=resource,
        need_deltas={"social": 0.10}, other_need_deltas={other_id: {"social": 0.05}}, valence=0.2,
        details={
            "claimed_location": claimed, "received_by": other_id,
            "_world": {"intent_truthful": truthful, "was_true": was_true},
        },
    )


def _study(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    p_success = min(1.0, STUDY_BASE_SUCCESS + 0.5 * agent.personality.openness + 0.1 * agent.knowledge_level("general"))
    if ctx.rng.random() >= p_success:
        return ActionOutcome(
            **base, kind="distracted", success=False,
            need_deltas={"knowledge": STUDY_KNOWLEDGE / 4, "energy": STUDY_ENERGY}, valence=-0.1,
            details={"p_success": round(p_success, 6), "skill": "general", "skill_gain": 0.0},
        )
    return ActionOutcome(
        **base, kind="ok", success=True,
        need_deltas={"knowledge": STUDY_KNOWLEDGE, "energy": STUDY_ENERGY}, valence=0.2,
        details={"skill_gain": STUDY_SKILL_GAIN, "skill": "general", "p_success": round(p_success, 6)},
    )


def _seek_care(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    loc = world.locations[perception.location_id]
    price = world.price("care", loc.id)
    if agent.money < price:
        return ActionOutcome(**base, kind="insufficient_funds", success=False, resource="care",
                             valence=-0.4, details={"price": price})
    loc.take("care", 1)
    return ActionOutcome(
        **base, kind="ok", success=True, resource="care", money_delta=-price,
        need_deltas={"health": CARE_HEALTH, "safety": 0.05}, valence=0.4,
        details={"price": price},
        world_delta={"resources": {loc.id: {"care": loc.stock("care")}}},
    )


def _idle(world, agent, proposal, ctx, perception, base) -> ActionOutcome:
    return ActionOutcome(**base, kind="ok", success=True, valence=0.0)


_RESOLVERS = {
    "move": _move, "acquire": _acquire, "consume": _consume, "work": _work, "rest": _rest,
    "socialize": _socialize, "ask_info": _ask_info, "share_info": _share_info,
    "study": _study, "seek_care": _seek_care, "idle": _idle,
}
